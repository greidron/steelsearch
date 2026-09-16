use std::collections::BTreeMap;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use tantivy::query::{Bm25StatisticsProvider, EnableScoring, Query, Weight};
use tantivy::schema::Field;
use tantivy::{Searcher, SearcherGeneration, Term};

pub(super) fn score_addresses(
    searcher: &Searcher,
    query: &dyn Query,
    addresses: Vec<tantivy::DocAddress>,
) -> tantivy::Result<Vec<(f32, tantivy::DocAddress)>> {
    use tantivy::DocSet;
    if addresses.is_empty() {
        return Ok(Vec::new());
    }
    let weight = query.weight(EnableScoring::enabled_from_searcher(searcher))?;
    let mut ordered = addresses.iter().copied().enumerate().collect::<Vec<_>>();
    ordered.sort_unstable_by_key(|(_, address)| (address.segment_ord, address.doc_id));
    let mut result = addresses
        .into_iter()
        .map(|address| (0.0, address))
        .collect::<Vec<_>>();
    let mut cursor = 0;
    while cursor < ordered.len() {
        let segment = ordered[cursor].1.segment_ord;
        let mut scorer = weight.scorer(searcher.segment_reader(segment), 1.0)?;
        while cursor < ordered.len() && ordered[cursor].1.segment_ord == segment {
            let (original, address) = ordered[cursor];
            if scorer.seek(address.doc_id) != address.doc_id {
                return Err(tantivy::TantivyError::InvalidArgument(
                    "native collector returned a document outside its query".into(),
                ));
            }
            result[original].0 = scorer.score();
            cursor += 1;
        }
    }
    Ok(result)
}

pub(super) fn source_ordered_term_scores(
    searcher: &Searcher,
    field: Field,
    tokens: &[String],
    score_term: impl Fn(usize, usize, usize) -> f32,
) -> tantivy::Result<Vec<(tantivy::DocAddress, f32)>> {
    use tantivy::{DocSet, Postings, TERMINATED};
    let mut result = Vec::new();
    for (segment_ord, segment) in searcher.segment_readers().iter().enumerate() {
        let inverted = segment.inverted_index(field)?;
        let norms = segment.get_fieldnorms_reader(field)?;
        let mut scores = vec![0.0_f32; segment.max_doc() as usize];
        // Keep query order and duplicate terms, matching the source scorer's f32 sum.
        for (token_index, token) in tokens.iter().enumerate() {
            let term = Term::from_field_text(field, token);
            let Some(mut postings) =
                inverted.read_postings(&term, tantivy::schema::IndexRecordOption::WithFreqs)?
            else {
                continue;
            };
            while postings.doc() != TERMINATED {
                let doc = postings.doc();
                if !segment.is_deleted(doc) {
                    scores[doc as usize] += score_term(
                        token_index,
                        postings.term_freq() as usize,
                        norms.fieldnorm(doc) as usize,
                    );
                }
                postings.advance();
            }
        }
        result.extend(scores.into_iter().enumerate().filter_map(|(doc, score)| {
            (score > 0.0).then_some((
                tantivy::DocAddress::new(segment_ord as u32, doc as u32),
                score,
            ))
        }));
    }
    Ok(result)
}

#[derive(Clone, Debug, Default)]
pub(super) struct FieldStatisticsCache {
    statistics: Arc<Mutex<BTreeMap<Field, CachedFieldStatistics>>>,
    native_statistics_exact: Arc<Mutex<BTreeMap<Field, Arc<AtomicBool>>>>,
}

#[derive(Clone, Debug, Default)]
struct CachedFieldStatistics {
    documents: Option<u64>,
    total_num_tokens: Option<u64>,
    term_doc_freqs: BTreeMap<Term, u64>,
}

impl FieldStatisticsCache {
    pub(super) fn wrap(
        &self,
        query: Box<dyn Query>,
        field: Field,
        searcher: &Searcher,
        historical_searchers: Arc<Vec<Searcher>>,
    ) -> Box<dyn Query> {
        let native_statistics_exact = self
            .native_statistics_exact
            .lock()
            .expect("native BM25 exact-statistics mutex poisoned")
            .entry(field)
            .or_insert_with(|| Arc::new(AtomicBool::new(false)))
            .clone();
        Box::new(NormalizedBm25Query {
            query,
            field,
            generation: searcher.generation().clone(),
            cache: self.clone(),
            native_statistics_exact,
            historical_searchers,
        })
    }
}

#[derive(Debug)]
struct NormalizedBm25Query {
    query: Box<dyn Query>,
    field: Field,
    generation: SearcherGeneration,
    cache: FieldStatisticsCache,
    native_statistics_exact: Arc<AtomicBool>,
    historical_searchers: Arc<Vec<Searcher>>,
}

impl Clone for NormalizedBm25Query {
    fn clone(&self) -> Self {
        Self {
            query: self.query.box_clone(),
            field: self.field,
            generation: self.generation.clone(),
            cache: self.cache.clone(),
            native_statistics_exact: Arc::clone(&self.native_statistics_exact),
            historical_searchers: Arc::clone(&self.historical_searchers),
        }
    }
}

pub(super) fn field_document_count(searcher: &Searcher, field: Field) -> tantivy::Result<u64> {
    let mut count = 0;
    for segment in searcher.segment_readers() {
        let norms = segment.get_fieldnorms_reader(field)?;
        // Token totals and document frequencies include deletions until segment merging.
        count += (0..segment.max_doc())
            .filter(|&doc| norms.fieldnorm(doc) != 0)
            .count() as u64;
    }
    Ok(count)
}

pub(super) fn field_total_num_tokens(searcher: &Searcher, field: Field) -> tantivy::Result<u64> {
    Bm25StatisticsProvider::total_num_tokens(searcher, field)
}

struct FieldStatistics<'a> {
    searcher: &'a Searcher,
    documents: u64,
    historical_searchers: &'a [Searcher],
    cache: Option<&'a FieldStatisticsCache>,
}

impl Bm25StatisticsProvider for FieldStatistics<'_> {
    fn total_num_tokens(&self, field: Field) -> tantivy::Result<u64> {
        let cached_total = self.cache.and_then(|cache| {
            cache
                .statistics
                .lock()
                .expect("native BM25 statistics mutex poisoned")
                .get(&field)
                .and_then(|cached| cached.total_num_tokens)
        });
        if let Some(total) = cached_total
        {
            return Ok(total);
        }
        let total = self.historical_searchers.iter().try_fold(
            Bm25StatisticsProvider::total_num_tokens(self.searcher, field)?,
            |total, searcher| {
                total.checked_add(Bm25StatisticsProvider::total_num_tokens(searcher, field)?)
                    .ok_or_else(|| tantivy::TantivyError::InvalidArgument(
                        "historical BM25 token count overflow".into(),
                    ))
            },
        )?;
        if let Some(cache) = self.cache {
            cache
                .statistics
                .lock()
                .expect("native BM25 statistics mutex poisoned")
                .entry(field)
                .or_default()
                .total_num_tokens = Some(total);
        }
        Ok(total)
    }
    fn total_num_docs(&self) -> tantivy::Result<u64> {
        Ok(self.documents)
    }
    fn doc_freq(&self, term: &Term) -> tantivy::Result<u64> {
        let cached_count = self.cache.and_then(|cache| {
            cache
                .statistics
                .lock()
                .expect("native BM25 statistics mutex poisoned")
                .get(&term.field())
                .and_then(|cached| cached.term_doc_freqs.get(term).copied())
        });
        if let Some(count) = cached_count
        {
            return Ok(count);
        }
        let count = self.historical_searchers.iter().try_fold(
            self.searcher.doc_freq(term)?,
            |total, searcher| {
                total.checked_add(searcher.doc_freq(term)?)
                    .ok_or_else(|| tantivy::TantivyError::InvalidArgument(
                        "historical BM25 document frequency overflow".into(),
                    ))
            },
        )?;
        let field = term.field();
        if let Some(cache) = self.cache {
            cache
                .statistics
                .lock()
                .expect("native BM25 statistics mutex poisoned")
                .entry(field)
                .or_default()
                .term_doc_freqs
                .insert(term.clone(), count);
        }
        Ok(count)
    }
}

impl Query for NormalizedBm25Query {
    fn weight(&self, scoring: EnableScoring<'_>) -> tantivy::Result<Box<dyn Weight>> {
        #[cfg(feature = "diagnostic-search-timing")]
        let _timer = super::diagnostic_search::start(&super::diagnostic_search::NATIVE_BM25_WEIGHT);
        if !scoring.is_scoring_enabled() {
            return self.query.weight(scoring);
        }
        let searcher = scoring
            .searcher()
            .expect("enabled scoring requires a searcher");
        #[cfg(feature = "diagnostic-search-timing")]
        let generation_matches = {
            let _generation_timer = super::diagnostic_search::start(
                &super::diagnostic_search::NATIVE_BM25_GENERATION_CHECK,
            );
            searcher.generation() == &self.generation
        };
        #[cfg(not(feature = "diagnostic-search-timing"))]
        let generation_matches = searcher.generation() == &self.generation;
        // Tantivy's default provider is exact when every document in the
        // current snapshot has this field and no retained reader contributes
        // to OpenSearch-compatible statistics. The first normalized weight
        // establishes that equality in the per-snapshot cache; later queries
        // can use Tantivy's direct, allocation-free statistics provider.
        let native_statistics_are_exact = generation_matches
            && self.historical_searchers.is_empty()
            && self.native_statistics_exact.load(Ordering::Acquire);
        if native_statistics_are_exact {
            return self.query.weight(scoring);
        }
        #[cfg(feature = "diagnostic-search-timing")]
        let _statistics_timer = super::diagnostic_search::start(
            &super::diagnostic_search::NATIVE_BM25_FIELD_STATISTICS,
        );
        let documents = if generation_matches {
            let cached_documents = self
                .cache
                .statistics
                .lock()
                .expect("native BM25 statistics mutex poisoned")
                .get(&self.field)
                .and_then(|cached| cached.documents);
            if let Some(count) = cached_documents {
                count
            } else {
                let count = self.historical_searchers.iter().try_fold(
                    field_document_count(searcher, self.field)?,
                    |total, historical| {
                        total.checked_add(field_document_count(historical, self.field)?)
                            .ok_or_else(|| tantivy::TantivyError::InvalidArgument(
                                "historical BM25 document count overflow".into(),
                            ))
                    },
                )?;
                self.cache
                    .statistics
                    .lock()
                    .expect("native BM25 statistics mutex poisoned")
                    .entry(self.field)
                    .or_default()
                    .documents = Some(count);
                count
            }
        } else {
            // A query reused with another reader must not reuse its original snapshot statistics.
            self.historical_searchers.iter().try_fold(
                field_document_count(searcher, self.field)?,
                |total, historical| {
                    total.checked_add(field_document_count(historical, self.field)?)
                        .ok_or_else(|| tantivy::TantivyError::InvalidArgument(
                            "historical BM25 document count overflow".into(),
                        ))
                },
            )?
        };
        if generation_matches
            && self.historical_searchers.is_empty()
            && Bm25StatisticsProvider::total_num_docs(searcher)
                .is_ok_and(|native_documents| documents == native_documents)
        {
            self.native_statistics_exact.store(true, Ordering::Release);
        }
        #[cfg(feature = "diagnostic-search-timing")]
        drop(_statistics_timer);
        let statistics = FieldStatistics {
            searcher,
            documents,
            historical_searchers: &self.historical_searchers,
            cache: generation_matches.then_some(&self.cache),
        };
        #[cfg(feature = "diagnostic-search-timing")]
        let _tantivy_weight_timer =
            super::diagnostic_search::start(&super::diagnostic_search::NATIVE_BM25_TANTIVY_WEIGHT);
        self.query
            .weight(EnableScoring::enabled_from_statistics_provider(
                &statistics,
                searcher,
            ))
    }

    fn query_terms<'a>(&'a self, visitor: &mut dyn FnMut(&'a Term, bool)) {
        self.query.query_terms(visitor);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tantivy::collector::{Count, TopDocs};
    use tantivy::fieldnorm::FieldNormReader;
    use tantivy::query::Bm25Weight;
    use tantivy::query::TermQuery;
    use tantivy::schema::{IndexRecordOption, Schema, INDEXED, TEXT};
    use tantivy::{doc, Index, ReloadPolicy};

    #[test]
    fn pinned_bm25_matches_lucene_10_rounding() {
        // OpenSearch 3.7.0-SNAPSHOT / Lucene 10.4 BM25Similarity reference.
        let weight = Bm25Weight::for_one_term(5, 7, (8.0_f64 / 7.0) as f32);
        assert_eq!(
            weight
                .score(FieldNormReader::fieldnorm_to_id(2), 1)
                .to_bits(),
            0x3e05_74be
        );
    }

    #[test]
    fn field_statistics_follow_snapshots_and_segment_deletions() {
        let mut schema = Schema::builder();
        let title = schema.add_text_field("title", TEXT);
        let body = schema.add_text_field("body", TEXT);
        let id = schema.add_u64_field("id", INDEXED);
        let index = Index::create_in_ram(schema.build());
        let mut writer = index.writer(15_000_000).unwrap();
        writer.set_merge_policy(Box::new(tantivy::merge_policy::NoMergePolicy));
        writer
            .add_document(doc!(id=>0u64, title=>"alpha", body=>"alpha"))
            .unwrap();
        writer.add_document(doc!(id=>1u64, body=>"alpha")).unwrap();
        writer.commit().unwrap();
        let reader = index
            .reader_builder()
            .reload_policy(ReloadPolicy::Manual)
            .try_into()
            .unwrap();
        let original = reader.searcher();
        let source_scores = |searcher: &Searcher| {
            source_ordered_term_scores(
                searcher,
                title,
                &["alpha".to_string()],
                |_, frequency, length| (frequency + length) as f32,
            )
            .unwrap()
        };
        assert_eq!(source_scores(&original).len(), 1);
        assert_eq!(source_scores(&original)[0].1, 2.0);
        let cache = FieldStatisticsCache::default();
        let query_for = |cache: &FieldStatisticsCache, searcher: &Searcher, field| {
            cache.wrap(
                Box::new(TermQuery::new(
                    Term::from_field_text(field, "alpha"),
                    IndexRecordOption::WithFreqs,
                )),
                field,
                searcher,
                Arc::new(Vec::new()),
            )
        };
        let title_query = query_for(&cache, &original, title);
        assert_eq!(original.search(title_query.as_ref(), &Count).unwrap(), 1);
        assert!(
            cache.statistics.lock().unwrap().is_empty(),
            "count must not scan scoring statistics"
        );
        let scores = |searcher: &Searcher, query: &dyn Query| {
            searcher
                .search(query, &TopDocs::with_limit(10))
                .unwrap()
                .into_iter()
                .map(|(score, _)| score)
                .collect::<Vec<_>>()
        };
        let original_scores = scores(&original, title_query.as_ref());
        let body_query = query_for(&cache, &original, body);
        let body_scores = scores(&original, body_query.as_ref());
        assert!(original_scores[0] > body_scores[0]);
        assert_eq!(
            cache
                .statistics
                .lock()
                .unwrap()
                .iter()
                .map(|(field, cached)| (*field, cached.documents.unwrap()))
                .collect::<BTreeMap<_, _>>(),
            BTreeMap::from([(title, 1), (body, 2)])
        );

        writer
            .add_document(doc!(id=>2u64, title=>"other", body=>"other"))
            .unwrap();
        writer.commit().unwrap();
        reader.reload().unwrap();
        let appended = reader.searcher();
        let appended_cache = FieldStatisticsCache::default();
        let appended_query = query_for(&appended_cache, &appended, title);
        let appended_scores = scores(&appended, appended_query.as_ref());
        assert_ne!(appended_scores, original_scores);
        assert_eq!(scores(&appended, title_query.as_ref()), appended_scores);
        assert_eq!(scores(&original, title_query.as_ref()), original_scores);
        assert_eq!(cache.statistics.lock().unwrap()[&title].documents, Some(1));
        assert_eq!(appended_cache.statistics.lock().unwrap()[&title].documents, Some(2));

        writer.delete_term(Term::from_field_u64(id, 0));
        writer.commit().unwrap();
        reader.reload().unwrap();
        let deleted = reader.searcher();
        assert!(source_scores(&deleted).is_empty());
        assert_eq!(source_scores(&original).len(), 1);
        assert_eq!(field_document_count(&deleted, title).unwrap(), 2);
        assert_eq!(deleted.search(title_query.as_ref(), &Count).unwrap(), 0);
        let segments = index.searchable_segment_ids().unwrap();
        writer.merge(&segments).wait().unwrap();
        reader.reload().unwrap();
        assert_eq!(field_document_count(&reader.searcher(), title).unwrap(), 1);
        assert!(source_scores(&reader.searcher()).is_empty());
        assert_eq!(source_scores(&original).len(), 1);
        assert_eq!(field_document_count(&original, title).unwrap(), 1);
        assert_eq!(scores(&original, title_query.as_ref()), original_scores);
    }

    #[test]
    fn dense_field_reuses_tantivy_native_bm25_statistics() {
        let mut schema = Schema::builder();
        let title = schema.add_text_field("title", TEXT);
        let index = Index::create_in_ram(schema.build());
        let mut writer = index.writer(15_000_000).unwrap();
        writer.add_document(doc!(title=>"alpha beta")).unwrap();
        writer.add_document(doc!(title=>"alpha gamma")).unwrap();
        writer.commit().unwrap();
        let reader = index
            .reader_builder()
            .reload_policy(ReloadPolicy::Manual)
            .try_into()
            .unwrap();
        let searcher = reader.searcher();
        let cache = FieldStatisticsCache::default();
        let wrapped_query = || {
            cache.wrap(
                Box::new(TermQuery::new(
                    Term::from_field_text(title, "alpha"),
                    IndexRecordOption::WithFreqs,
                )),
                title,
                &searcher,
                Arc::new(Vec::new()),
            )
        };
        let collector = TopDocs::with_limit(10);
        let first_scores = searcher.search(wrapped_query().as_ref(), &collector).unwrap();
        assert_eq!(cache.statistics.lock().unwrap()[&title].documents, Some(2));
        let native_scores = searcher
            .search(
                &TermQuery::new(
                    Term::from_field_text(title, "alpha"),
                    IndexRecordOption::WithFreqs,
                ),
                &collector,
            )
            .unwrap();
        assert_eq!(first_scores, native_scores);
        assert_eq!(
            searcher.search(wrapped_query().as_ref(), &collector).unwrap(),
            native_scores
        );
    }
}
