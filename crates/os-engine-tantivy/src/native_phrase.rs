use super::native_phrase_positions::Matcher;
use std::collections::BTreeSet;
use tantivy::fieldnorm::FieldNormReader;
use tantivy::postings::SegmentPostings;
use tantivy::query::{Bm25Weight, BooleanQuery, EmptyScorer, EnableScoring, Explanation, Occur, Query, Scorer, TermQuery, Weight};
use tantivy::schema::IndexRecordOption;
use tantivy::{DocId, DocSet, Postings, Score, SegmentReader, Term, TERMINATED};

#[derive(Clone, Debug)]
pub(super) struct NativePhraseQuery {
    terms: Vec<Term>,
    offsets: Vec<u32>,
    term_ids: Vec<usize>,
    slop: u32,
}

impl NativePhraseQuery {
    pub(super) fn new(terms: Vec<(usize, Term)>, slop: u32) -> tantivy::Result<Self> {
        if terms.len() < 2 || terms.windows(2).any(|pair|
            pair[0].0 >= pair[1].0 || pair[0].1.field() != pair[1].1.field()) {
            return Err(tantivy::TantivyError::InvalidArgument(
                "phrase requires ordered distinct offsets and one field".into(),
            ));
        }
        let offsets = terms.iter().map(|(offset, _)| u32::try_from(*offset).map_err(|_|
            tantivy::TantivyError::InvalidArgument("phrase offset exceeds u32".into())))
            .collect::<tantivy::Result<Vec<_>>>()?;
        let terms = terms.into_iter().map(|(_, term)| term).collect::<Vec<_>>();
        let term_ids = terms.iter().map(|term| terms.iter().position(|other| other == term).unwrap()).collect();
        Ok(Self { terms, offsets, term_ids, slop })
    }
}

impl Query for NativePhraseQuery {
    fn weight(&self, scoring: EnableScoring<'_>) -> tantivy::Result<Box<dyn Weight>> {
        let field = self.terms[0].field();
        let record = scoring.schema().get_field_entry(field).field_type().get_index_record_option();
        if record != Some(IndexRecordOption::WithFreqsAndPositions) {
            return Err(tantivy::TantivyError::SchemaError("phrase field requires indexed positions".into()));
        }
        let similarity = match scoring {
            EnableScoring::Enabled { statistics_provider, .. } => Some(Bm25Weight::for_terms(statistics_provider, &self.terms)?),
            EnableScoring::Disabled { .. } => None,
        };
        let conjunction = BooleanQuery::new(self.terms.iter().collect::<BTreeSet<_>>().into_iter()
            .map(|term| (Occur::Must, Box::new(TermQuery::new(term.clone(), IndexRecordOption::Basic)) as Box<dyn Query>))
            .collect());
        let candidate = conjunction.weight(EnableScoring::Disabled {
            schema: scoring.schema(), searcher_opt: scoring.searcher(),
        })?;
        Ok(Box::new(PhraseWeight { query: self.clone(), candidate, similarity }))
    }

    fn query_terms<'a>(&'a self, visitor: &mut dyn FnMut(&'a Term, bool)) {
        for term in &self.terms { visitor(term, true); }
    }
}

struct PhraseWeight {
    query: NativePhraseQuery,
    candidate: Box<dyn Weight>,
    similarity: Option<Bm25Weight>,
}

impl PhraseWeight {
    fn phrase_scorer(&self, reader: &SegmentReader, boost: Score) -> tantivy::Result<Option<PhraseScorer>> {
        let field = self.query.terms[0].field();
        let inverted = reader.inverted_index(field)?;
        let mut postings = Vec::with_capacity(self.query.terms.len());
        for term in &self.query.terms {
            let Some(term_postings) = inverted.read_postings(term, IndexRecordOption::WithFreqsAndPositions)? else {
                return Ok(None);
            };
            postings.push(term_postings);
        }
        let norms = if self.similarity.is_some() {
            reader.fieldnorms_readers().get_field(field)?.unwrap_or_else(|| FieldNormReader::constant(reader.max_doc(), 1))
        } else {
            FieldNormReader::constant(reader.max_doc(), 1)
        };
        let mut scorer = PhraseScorer {
            candidate: self.candidate.scorer(reader, 1.0)?, postings,
            positions: vec![Vec::new(); self.query.terms.len()],
            matcher: Matcher::new(&self.query.term_ids, &self.query.offsets),
            slop: self.query.slop, frequency: 0.0, norms,
            similarity: self.similarity.as_ref().map(|similarity| similarity.boost_by(boost)),
        };
        scorer.find_match();
        Ok(Some(scorer))
    }
}

impl Weight for PhraseWeight {
    fn scorer(&self, reader: &SegmentReader, boost: Score) -> tantivy::Result<Box<dyn Scorer>> {
        Ok(match self.phrase_scorer(reader, boost)? {
            Some(scorer) => Box::new(scorer),
            None => Box::new(EmptyScorer),
        })
    }

    fn explain(&self, reader: &SegmentReader, doc: DocId) -> tantivy::Result<Explanation> {
        let mut scorer = self.phrase_scorer(reader, 1.0)?.ok_or_else(||
            tantivy::TantivyError::InvalidArgument("document does not match phrase".into()))?;
        if doc == TERMINATED || scorer.seek(doc) != doc || reader.is_deleted(doc) {
            return Err(tantivy::TantivyError::InvalidArgument("document does not match phrase".into()));
        }
        let mut explanation = Explanation::new("Native sloppy phrase scorer", scorer.score());
        if let Some(similarity) = &scorer.similarity {
            explanation.add_detail(similarity.explain_fractional(scorer.norms.fieldnorm_id(doc), scorer.frequency));
        }
        Ok(explanation)
    }
}

struct PhraseScorer {
    candidate: Box<dyn Scorer>,
    postings: Vec<SegmentPostings>,
    positions: Vec<Vec<u32>>,
    matcher: Matcher,
    slop: u32,
    frequency: f32,
    norms: FieldNormReader,
    similarity: Option<Bm25Weight>,
}

impl PhraseScorer {
    fn find_match(&mut self) -> DocId {
        while self.candidate.doc() != TERMINATED {
            let doc = self.candidate.doc();
            for (postings, positions) in self.postings.iter_mut().zip(&mut self.positions) {
                if postings.doc() < doc { postings.seek(doc); }
                positions.clear();
                if postings.doc() == doc { postings.positions(positions); }
            }
            self.frequency = if self.similarity.is_some() {
                self.matcher.frequency(&self.positions, self.slop)
            } else {
                f32::from(self.matcher.matches(&self.positions, self.slop))
            };
            if self.frequency > 0.0 { return doc; }
            self.candidate.advance();
        }
        self.frequency = 0.0;
        TERMINATED
    }
}

impl DocSet for PhraseScorer {
    fn advance(&mut self) -> DocId {
        if self.doc() == TERMINATED { return TERMINATED; }
        self.candidate.advance();
        self.find_match()
    }
    fn seek(&mut self, target: DocId) -> DocId {
        if self.doc() >= target { return self.doc(); }
        self.candidate.seek(target);
        self.find_match()
    }
    fn doc(&self) -> DocId { self.candidate.doc() }
    fn size_hint(&self) -> u32 { self.candidate.size_hint() }
}

impl Scorer for PhraseScorer {
    fn score(&mut self) -> Score {
        if self.doc() == TERMINATED { return 0.0; }
        self.similarity.as_ref().map_or(1.0, |similarity|
            similarity.score_fractional(self.norms.fieldnorm_id(self.doc()), self.frequency))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tantivy::collector::{Count, DocSetCollector};
    use tantivy::schema::{Schema, INDEXED, STORED, TEXT};
    use tantivy::{doc, Index, ReloadPolicy};

    #[test]
    fn native_fractional_bm25_preserves_integer_scores_and_explanation_values() {
        let weight = Bm25Weight::for_one_term(2, 10, 3.5);
        for norm in 0..=255 {
            for freq in [0, 1, 2, 10_000, u32::MAX] {
                assert_eq!(weight.score(norm, freq).to_bits(), weight.score_fractional(norm, freq as f32).to_bits());
            }
            for freq in [0.0, 0.5, 1.0 / 3.0, 1.3333334, 100.5] {
                let score = weight.score_fractional(norm, freq);
                assert!(score.is_finite() && score >= 0.0);
                assert_eq!(score.to_bits(), weight.explain_fractional(norm, freq).value().to_bits());
                assert_eq!(weight.boost_by(2.0).score_fractional(norm, freq), score * 2.0);
            }
        }
    }

    #[test]
    fn native_phrase_scorer_seeks_and_preserves_refresh_snapshots() {
        let mut schema = Schema::builder();
        let body = schema.add_text_field("body", TEXT);
        let id = schema.add_u64_field("id", INDEXED | STORED);
        let index = Index::create_in_ram(schema.build());
        let mut writer = index.writer(15_000_000).unwrap();
        writer.set_merge_policy(Box::new(tantivy::merge_policy::NoMergePolicy));
        for (ordinal, text) in ["alpha beta gamma", "alpha gamma beta", "alpha beta", "alpha gap beta gamma"].iter().enumerate() {
            writer.add_document(doc!(id => ordinal as u64, body => *text)).unwrap();
        }
        writer.commit().unwrap();
        let reader = index.reader_builder().reload_policy(ReloadPolicy::Manual).try_into().unwrap();
        let old = reader.searcher();
        let query = NativePhraseQuery::new(["alpha", "beta", "gamma"].iter().enumerate()
            .map(|(offset, text)| (offset, Term::from_field_text(body, text))).collect(), 2).unwrap();
        let weight = query.weight(EnableScoring::disabled_from_searcher(&old)).unwrap();
        let mut scorer = weight.scorer(old.segment_reader(0), 1.0).unwrap();
        assert_eq!(scorer.doc(), 0);
        assert_eq!(scorer.seek(0), 0);
        assert_eq!(scorer.advance(), 1);
        assert_eq!(scorer.seek(2), 3);
        assert_eq!(scorer.seek(3), 3);
        assert_eq!(scorer.advance(), TERMINATED);
        assert_eq!(scorer.seek(TERMINATED), TERMINATED);
        assert_eq!(scorer.advance(), TERMINATED);
        assert_eq!(scorer.score(), 0.0);
        let ids = |searcher: &tantivy::Searcher| searcher.search(&query, &DocSetCollector).unwrap()
            .into_iter().map(|address| searcher.doc(address).unwrap().get_first(id).unwrap().as_u64().unwrap())
            .collect::<BTreeSet<_>>();
        assert_eq!(ids(&old), BTreeSet::from([0, 1, 3]));
        assert_eq!(old.search(&query, &Count).unwrap(), 3);
        writer.delete_term(Term::from_field_u64(id, 1));
        writer.add_document(doc!(id => 4u64, body => "alpha beta gamma")).unwrap();
        writer.commit().unwrap();
        reader.reload().unwrap();
        assert_eq!(ids(&old), BTreeSet::from([0, 1, 3]));
        let current = reader.searcher();
        assert_eq!(ids(&current), BTreeSet::from([0, 3, 4]));
        assert_eq!(current.search(&query, &Count).unwrap(), 3);
        let scored = query.weight(EnableScoring::enabled_from_searcher(&old)).unwrap();
        for doc in [0, 1, 3] {
            let mut base = scored.scorer(old.segment_reader(0), 1.0).unwrap();
            let mut boosted = scored.scorer(old.segment_reader(0), 2.0).unwrap();
            assert_eq!(base.seek(doc), doc);
            assert_eq!(boosted.seek(doc), doc);
            assert_eq!(boosted.score(), base.score() * 2.0);
            assert_eq!(scored.explain(old.segment_reader(0), doc).unwrap().value(), base.score());
        }
        assert!(scored.explain(old.segment_reader(0), 2).is_err());
        assert!(NativePhraseQuery::new(vec![(0, Term::from_field_text(body, "alpha"))], 1).is_err());
    }
}
