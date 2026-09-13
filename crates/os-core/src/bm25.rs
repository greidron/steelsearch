//! Shared source-scoring arithmetic. Callers own analyzer and snapshot selection.

use std::collections::{BTreeMap, BTreeSet};

pub fn source_text_tokens(text: &str) -> Vec<String> {
    text.split(|character: char| !character.is_alphanumeric())
        .filter(|token| !token.is_empty())
        .map(str::to_lowercase)
        .collect()
}

pub fn term_frequency(frequency: usize, document_length: usize, average_length: f32) -> f32 {
    if frequency == 0 || document_length == 0 || average_length == 0.0 {
        return 0.0;
    }
    let frequency = frequency as f32;
    let document_length = document_length as f32;
    let k1 = 1.2_f32;
    let b = 0.75_f32;
    frequency / (frequency + k1 * (1.0 - b + b * document_length / average_length))
}

/// Decoded byte4 length norm: 24 exact small values followed by three mantissa bits.
pub fn normalized_document_length(length: usize) -> usize {
    let length = length.min(i32::MAX as usize) as u32;
    if length < 40 {
        return length as usize;
    }
    let value = length - 24;
    let shift = (31 - value.leading_zeros()).saturating_sub(3);
    (24 + ((value >> shift) << shift)) as usize
}

pub fn normalized_term_frequency(frequency: usize, document_length: usize, average_length: f32) -> f32 {
    // Corpus average remains the uncompressed token count, only the document norm is decoded.
    term_frequency(frequency, normalized_document_length(document_length), average_length)
}

pub fn inverse_document_frequency(documents: usize, matching_documents: usize) -> f32 {
    // Preserve the existing engine's f32 count conversion before the logarithm.
    let documents = documents as f32;
    let matching_documents = matching_documents as f32;
    if documents == 0.0 || matching_documents == 0.0 {
        return 0.0;
    }
    (1.0_f64
        + (documents as f64 - matching_documents as f64 + 0.5) / (matching_documents as f64 + 0.5))
        .ln() as f32
}

#[derive(Debug, Clone)]
pub struct FieldStatistics {
    document_count: usize,
    average_length: f32,
    document_frequencies: BTreeMap<String, usize>,
}

impl FieldStatistics {
    /// Empty fields do not contribute to field-level document count or average length.
    pub fn from_documents<'a>(documents: impl IntoIterator<Item = &'a [String]>) -> Self {
        let mut document_count = 0;
        let mut total_length = 0;
        let mut document_frequencies = BTreeMap::new();
        for tokens in documents {
            if tokens.is_empty() {
                continue;
            }
            document_count += 1;
            total_length += tokens.len();
            for token in tokens.iter().collect::<BTreeSet<_>>() {
                *document_frequencies.entry(token.clone()).or_insert(0) += 1;
            }
        }
        Self {
            document_count,
            average_length: if document_count == 0 {
                0.0
            } else {
                total_length as f32 / document_count as f32
            },
            document_frequencies,
        }
    }

    pub fn term_score(&self, term: &str, frequency: usize, document_length: usize) -> f32 {
        inverse_document_frequency(
            self.document_count,
            self.document_frequencies.get(term).copied().unwrap_or(0),
        ) * normalized_term_frequency(frequency, document_length, self.average_length)
    }

    pub fn score(&self, query_tokens: &[String], document_tokens: &[String]) -> f32 {
        query_tokens
            .iter()
            .map(|term| {
                let frequency = document_tokens
                    .iter()
                    .filter(|token| *token == term)
                    .count();
                self.term_score(term, frequency, document_tokens.len())
            })
            .sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn length_norm_scores_match_live_opensearch_boundary_fixture() {
        let lengths = [1, 40, 41, 42, 1000];
        let mut docs = lengths.iter().map(|&length| {
            let mut tokens = vec!["other".to_owned(); length];
            tokens[0] = "alpha".to_owned();
            tokens
        }).collect::<Vec<_>>();
        docs.push(Vec::new());
        let stats = FieldStatistics::from_documents(docs.iter().map(Vec::as_slice));
        for (length, expected) in lengths.into_iter().zip([
            0.06672633_f32, 0.059591025, 0.059591025, 0.059266016, 0.016606808,
        ]) {
            assert!((stats.term_score("alpha", 1, length) - expected).abs() < 1e-7);
        }
        assert_eq!(normalized_document_length(41), 40);
        assert_eq!(normalized_document_length(1000), 984);
        assert_eq!(normalized_document_length(usize::MAX), 2_013_265_944);
    }

    #[test]
    fn empty_fields_and_repeated_terms_have_field_level_statistics() {
        let docs = [
            vec!["a".to_string(), "a".to_string()],
            vec![],
            vec!["b".to_string()],
        ];
        let stats = FieldStatistics::from_documents(docs.iter().map(Vec::as_slice));
        assert_eq!(stats.document_count, 2);
        assert_eq!(stats.average_length, 1.5);
        assert_eq!(stats.document_frequencies["a"], 1);
        assert_eq!(stats.term_score("missing", 1, 2), 0.0);
        assert_eq!(
            stats.score(&["a".into()], &docs[0]),
            inverse_document_frequency(2, 1) * term_frequency(2, 2, 1.5)
        );
        assert_eq!(
            stats.score(&["a".into(), "a".into()], &docs[0]),
            2.0 * stats.score(&["a".into()], &docs[0])
        );
        let empty = FieldStatistics::from_documents(std::iter::empty());
        assert_eq!(empty.score(&["a".into()], &docs[0]), 0.0);
    }

    #[test]
    fn arithmetic_matches_legacy_engine_bit_patterns() {
        for frequency in [0, 1, 3, 19, 1000] {
            for length in [0, 1, 7, 1000] {
                for average in [0.0_f32, 0.25, 1.0, 3.3333333, 10000.0] {
                    let expected = if frequency == 0 || length == 0 || average == 0.0 {
                        0.0
                    } else {
                        let f = frequency as f32;
                        f / (f + 1.2_f32 * (1.0 - 0.75_f32 + 0.75_f32 * length as f32 / average))
                    };
                    assert_eq!(
                        term_frequency(frequency, length, average).to_bits(),
                        expected.to_bits()
                    );
                }
            }
        }
        for count in [0, 1, 3, 5000, 16_777_217, 100_000_001] {
            for matched in [0, 1, count / 2, count] {
                let n = count as f32;
                let df = matched as f32;
                let expected = if n == 0.0 || df == 0.0 {
                    0.0
                } else {
                    (1.0_f64 + (n as f64 - df as f64 + 0.5) / (df as f64 + 0.5)).ln() as f32
                };
                assert_eq!(
                    inverse_document_frequency(count, matched).to_bits(),
                    expected.to_bits()
                );
            }
        }
    }
}
