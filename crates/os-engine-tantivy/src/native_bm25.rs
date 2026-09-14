use std::collections::BTreeMap;
use std::sync::{Arc, Mutex};
use tantivy::query::{Bm25StatisticsProvider, BoostQuery, EnableScoring, Query, Weight};
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
pub(super) struct FieldStatisticsCache(Arc<Mutex<BTreeMap<Field, u64>>>);

impl FieldStatisticsCache {
    pub(super) fn wrap(
        &self,
        query: Box<dyn Query>,
        field: Field,
        searcher: &Searcher,
    ) -> Box<dyn Query> {
        Box::new(NormalizedBm25Query {
            // The pinned scorer now follows Lucene's reciprocal BM25 form,
            // whose weight is IDF rather than IDF * (k1 + 1).
            query: BoostQuery::new(query, 1.0),
            field,
            generation: searcher.generation().clone(),
            cache: self.clone(),
        })
    }
}

#[derive(Clone, Debug)]
struct NormalizedBm25Query {
    query: BoostQuery,
    field: Field,
    generation: SearcherGeneration,
    cache: FieldStatisticsCache,
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
}

impl Bm25StatisticsProvider for FieldStatistics<'_> {
    fn total_num_tokens(&self, field: Field) -> tantivy::Result<u64> {
        Bm25StatisticsProvider::total_num_tokens(self.searcher, field)
    }
    fn total_num_docs(&self) -> tantivy::Result<u64> {
        Ok(self.documents)
    }
    fn doc_freq(&self, term: &Term) -> tantivy::Result<u64> {
        self.searcher.doc_freq(term)
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
        #[cfg(feature = "diagnostic-search-timing")]
        let _statistics_timer = super::diagnostic_search::start(
            &super::diagnostic_search::NATIVE_BM25_FIELD_STATISTICS,
        );
        let documents = if generation_matches {
            let mut cached = self
                .cache
                .0
                .lock()
                .expect("native BM25 statistics mutex poisoned");
            match cached.get(&self.field) {
                Some(&count) => count,
                None => {
                    let count = field_document_count(searcher, self.field)?;
                    cached.insert(self.field, count);
                    count
                }
            }
        } else {
            // A query reused with another reader must not reuse its original snapshot statistics.
            field_document_count(searcher, self.field)?
        };
        #[cfg(feature = "diagnostic-search-timing")]
        drop(_statistics_timer);
        let statistics = FieldStatistics {
            searcher,
            documents,
        };
        #[cfg(feature = "diagnostic-search-timing")]
        let _tantivy_weight_timer = super::diagnostic_search::start(
            &super::diagnostic_search::NATIVE_BM25_TANTIVY_WEIGHT,
        );
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
    use tantivy::query::Bm25Weight;
    use tantivy::collector::{Count, TopDocs};
    use tantivy::query::TermQuery;
    use tantivy::fieldnorm::FieldNormReader;
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
            )
        };
        let title_query = query_for(&cache, &original, title);
        assert_eq!(original.search(title_query.as_ref(), &Count).unwrap(), 1);
        assert!(
            cache.0.lock().unwrap().is_empty(),
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
            *cache.0.lock().unwrap(),
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
        assert_eq!(cache.0.lock().unwrap()[&title], 1);
        assert_eq!(appended_cache.0.lock().unwrap()[&title], 2);

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
}
