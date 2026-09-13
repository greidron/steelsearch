use serde::{Deserialize, Serialize};

use crate::fieldnorm::FieldNormReader;
use crate::query::Explanation;
use crate::schema::Field;
use crate::{Score, Searcher, Term};

const K1: Score = 1.2;
const B: Score = 0.75;

/// An interface to compute the statistics needed in BM25 scoring.
///
/// The standard implementation is a [Searcher] but you can also
/// create your own to adjust the statistics.
pub trait Bm25StatisticsProvider {
    /// The total number of tokens in a given field across all documents in
    /// the index.
    fn total_num_tokens(&self, field: Field) -> crate::Result<u64>;

    /// The total number of documents in the index.
    fn total_num_docs(&self) -> crate::Result<u64>;

    /// The number of documents containing the given term.
    fn doc_freq(&self, term: &Term) -> crate::Result<u64>;
}

impl Bm25StatisticsProvider for Searcher {
    fn total_num_tokens(&self, field: Field) -> crate::Result<u64> {
        let mut total_num_tokens = 0u64;

        for segment_reader in self.segment_readers() {
            let inverted_index = segment_reader.inverted_index(field)?;
            total_num_tokens += inverted_index.total_num_tokens();
        }
        Ok(total_num_tokens)
    }

    fn total_num_docs(&self) -> crate::Result<u64> {
        let mut total_num_docs = 0u64;

        for segment_reader in self.segment_readers() {
            total_num_docs += u64::from(segment_reader.max_doc());
        }
        Ok(total_num_docs)
    }

    fn doc_freq(&self, term: &Term) -> crate::Result<u64> {
        self.doc_freq(term)
    }
}

pub(crate) fn idf(doc_freq: u64, doc_count: u64) -> Score {
    assert!(doc_count >= doc_freq, "{doc_count} >= {doc_freq}");
    // Lucene computes IDF in double precision, then narrows it to float.
    // Keep that rounding point so native Tantivy scoring emits the same f32.
    let x = ((doc_count - doc_freq) as f64 + 0.5) / (doc_freq as f64 + 0.5);
    (1.0 + x).ln() as Score
}

fn cached_tf_inverse(fieldnorm: u32, average_fieldnorm: Score) -> Score {
    1.0 / (K1 * (1.0 - B + B * fieldnorm as Score / average_fieldnorm))
}

fn compute_tf_cache(average_fieldnorm: Score) -> [Score; 256] {
    let mut cache: [Score; 256] = [0.0; 256];
    for (fieldnorm_id, cache_mut) in cache.iter_mut().enumerate() {
        let fieldnorm = FieldNormReader::id_to_fieldnorm(fieldnorm_id as u8);
        *cache_mut = cached_tf_inverse(fieldnorm, average_fieldnorm);
    }
    cache
}

#[derive(Clone, PartialEq, Debug, Serialize, Deserialize)]
pub struct Bm25Params {
    pub idf: Score,
    pub avg_fieldnorm: Score,
}

/// A struct used for computing BM25 scores.
#[derive(Clone)]
pub struct Bm25Weight {
    idf_explain: Explanation,
    weight: Score,
    cache: [Score; 256],
    average_fieldnorm: Score,
}

impl Bm25Weight {
    /// Increase the weight by a multiplicative factor.
    pub fn boost_by(&self, boost: Score) -> Bm25Weight {
        Bm25Weight {
            idf_explain: self.idf_explain.clone(),
            weight: self.weight * boost,
            cache: self.cache,
            average_fieldnorm: self.average_fieldnorm,
        }
    }

    /// Construct a [Bm25Weight] for a phrase of terms.
    pub fn for_terms(
        statistics: &dyn Bm25StatisticsProvider,
        terms: &[Term],
    ) -> crate::Result<Bm25Weight> {
        assert!(!terms.is_empty(), "Bm25 requires at least one term");
        let field = terms[0].field();
        for term in &terms[1..] {
            assert_eq!(
                term.field(),
                field,
                "All terms must belong to the same field."
            );
        }

        let total_num_tokens = statistics.total_num_tokens(field)?;
        let total_num_docs = statistics.total_num_docs()?;
        let average_fieldnorm = (total_num_tokens as f64 / total_num_docs as f64) as Score;

        if terms.len() == 1 {
            let term_doc_freq = statistics.doc_freq(&terms[0])?;
            Ok(Bm25Weight::for_one_term(
                term_doc_freq,
                total_num_docs,
                average_fieldnorm,
            ))
        } else {
            let mut idf_sum = 0.0_f64;
            for term in terms {
                idf_sum += f64::from(idf(statistics.doc_freq(term)?, total_num_docs));
            }
            let idf_explain = Explanation::new("idf", idf_sum as Score);
            Ok(Bm25Weight::new(idf_explain, average_fieldnorm))
        }
    }

    /// Construct a [Bm25Weight] for a single term.
    pub fn for_one_term(
        term_doc_freq: u64,
        total_num_docs: u64,
        avg_fieldnorm: Score,
    ) -> Bm25Weight {
        let idf = idf(term_doc_freq, total_num_docs);
        let mut idf_explain =
            Explanation::new("idf, computed as log(1 + (N - n + 0.5) / (n + 0.5))", idf);
        idf_explain.add_const(
            "n, number of docs containing this term",
            term_doc_freq as Score,
        );
        idf_explain.add_const("N, total number of docs", total_num_docs as Score);
        Bm25Weight::new(idf_explain, avg_fieldnorm)
    }

    pub(crate) fn new(idf_explain: Explanation, average_fieldnorm: Score) -> Bm25Weight {
        let weight = idf_explain.value();
        Bm25Weight {
            idf_explain,
            weight,
            cache: compute_tf_cache(average_fieldnorm),
            average_fieldnorm,
        }
    }

    /// Compute the BM25 score of a single document.
    #[inline]
    pub fn score(&self, fieldnorm_id: u8, term_freq: u32) -> Score {
        self.score_with_frequency(fieldnorm_id, term_freq as Score)
    }

    /// Score a non-negative, finite fractional phrase frequency with the native norm cache.
    #[inline]
    pub fn score_fractional(&self, fieldnorm_id: u8, term_freq: Score) -> Score {
        self.score_with_frequency(fieldnorm_id, term_freq)
    }

    /// Explain a fractional phrase frequency without changing integer-term scoring.
    pub fn explain_fractional(&self, fieldnorm_id: u8, term_freq: Score) -> Explanation {
        let mut tf = Explanation::new(
            "freq / (freq + k1 * (1 - b + b * dl / avgdl))",
            self.tf_factor_with_frequency(fieldnorm_id, term_freq),
        );
        tf.add_const("phraseFreq", term_freq);
        tf.add_const("k1, term saturation parameter", K1);
        tf.add_const("b, length normalization parameter", B);
        tf.add_const("dl, length of field", FieldNormReader::id_to_fieldnorm(fieldnorm_id) as Score);
        tf.add_const("avgdl, average length of field", self.average_fieldnorm);
        let mut explanation = Explanation::new("PhraseQuery, product of...", self.score_fractional(fieldnorm_id, term_freq));
        explanation.add_detail(Explanation::new("(K1+1)", K1 + 1.0));
        explanation.add_detail(self.idf_explain.clone());
        explanation.add_detail(tf);
        explanation
    }

    /// Compute the maximum possible BM25 score given this weight.
    pub fn max_score(&self) -> Score {
        self.score(255u8, 2_013_265_944)
    }

    #[inline]
    pub(crate) fn tf_factor(&self, fieldnorm_id: u8, term_freq: u32) -> Score {
        self.tf_factor_with_frequency(fieldnorm_id, term_freq as Score)
    }

    #[inline]
    fn score_with_frequency(&self, fieldnorm_id: u8, term_freq: Score) -> Score {
        let reciprocal = 1.0 + term_freq * self.cache[fieldnorm_id as usize];
        self.weight - self.weight / reciprocal
    }

    #[inline]
    fn tf_factor_with_frequency(&self, fieldnorm_id: u8, term_freq: Score) -> Score {
        1.0 - 1.0 / (1.0 + term_freq * self.cache[fieldnorm_id as usize])
    }

    /// Produce an [Explanation] of a BM25 score.
    pub fn explain(&self, fieldnorm_id: u8, term_freq: u32) -> Explanation {
        // The explain format is directly copied from Lucene's.
        // (So, Kudos to Lucene)
        let score = self.score(fieldnorm_id, term_freq);

        let term_freq = term_freq as Score;
        let right_factor = self.tf_factor_with_frequency(fieldnorm_id, term_freq);

        let mut tf_explanation = Explanation::new(
            "freq / (freq + k1 * (1 - b + b * dl / avgdl))",
            right_factor,
        );

        tf_explanation.add_const("freq, occurrences of term within document", term_freq);
        tf_explanation.add_const("k1, term saturation parameter", K1);
        tf_explanation.add_const("b, length normalization parameter", B);
        tf_explanation.add_const(
            "dl, length of field",
            FieldNormReader::id_to_fieldnorm(fieldnorm_id) as Score,
        );
        tf_explanation.add_const("avgdl, average length of field", self.average_fieldnorm);

        let mut explanation = Explanation::new("TermQuery, product of...", score);
        explanation.add_detail(Explanation::new("(K1+1)", K1 + 1.0));
        explanation.add_detail(self.idf_explain.clone());
        explanation.add_detail(tf_explanation);
        explanation
    }
}

#[cfg(test)]
mod tests {

    use super::{idf, Bm25Weight};
    use crate::fieldnorm::FieldNormReader;
    use crate::{assert_nearly_equals, Score};

    #[test]
    fn test_idf() {
        let score: Score = 2.0;
        assert_nearly_equals!(idf(1, 2), score.ln());
    }

    #[test]
    fn matches_lucene_10_bm25_rounding() {
        // OpenSearch 3.7.0-SNAPSHOT / Lucene 10.4, verified with BM25Similarity.
        assert_eq!(idf(5, 7).to_bits(), 0x3eb2_1642);
        let weight = Bm25Weight::for_one_term(5, 7, (8.0_f64 / 7.0) as Score);
        assert_eq!(
            weight
                .score(FieldNormReader::fieldnorm_to_id(2), 1)
                .to_bits(),
            0x3e05_74be
        );
    }
}
