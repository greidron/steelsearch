use crate::query::explanation::does_not_match;
use crate::query::{
    EmptyScorer, EnableScoring, Explanation, Query, ScoreCombiner, Scorer, Union, Weight,
};
use crate::{DocId, Score, SegmentReader, TantivyError, Term};

/// A disjunction requiring at least `minimum` matching children.
/// Each matching child's score is added once, including when conditions overlap.
#[derive(Debug)]
pub struct MinimumShouldMatchQuery {
    queries: Vec<Box<dyn Query>>,
    minimum: usize,
}

impl Clone for MinimumShouldMatchQuery {
    fn clone(&self) -> Self {
        Self {
            queries: self.queries.iter().map(|query| query.box_clone()).collect(),
            minimum: self.minimum,
        }
    }
}

impl MinimumShouldMatchQuery {
    /// Creates a threshold disjunction. A zero minimum is rejected by `weight`.
    pub fn new(queries: Vec<Box<dyn Query>>, minimum: usize) -> Self {
        Self { queries, minimum }
    }
}

impl Query for MinimumShouldMatchQuery {
    fn weight(&self, enable_scoring: EnableScoring<'_>) -> crate::Result<Box<dyn Weight>> {
        if self.minimum == 0 {
            return Err(TantivyError::InvalidArgument(
                "minimum must be positive".into(),
            ));
        }
        let weights = self
            .queries
            .iter()
            .map(|query| query.weight(enable_scoring))
            .collect::<crate::Result<Vec<_>>>()?;
        Ok(Box::new(MinimumShouldMatchWeight {
            weights,
            minimum: self.minimum,
            scoring: enable_scoring.is_scoring_enabled(),
        }))
    }

    fn query_terms<'a>(&'a self, visitor: &mut dyn FnMut(&'a Term, bool)) {
        for query in &self.queries {
            query.query_terms(visitor);
        }
    }
}

struct MinimumShouldMatchWeight {
    weights: Vec<Box<dyn Weight>>,
    minimum: usize,
    scoring: bool,
}

impl Weight for MinimumShouldMatchWeight {
    fn scorer(&self, reader: &SegmentReader, boost: Score) -> crate::Result<Box<dyn Scorer>> {
        if self.minimum > self.weights.len() {
            return Ok(Box::new(EmptyScorer));
        }
        let scorers = self
            .weights
            .iter()
            .map(|weight| weight.scorer(reader, boost))
            .collect::<crate::Result<Vec<_>>>()?;
        Ok(Box::new(Union::build(scorers, || ThresholdCombiner {
            minimum: self.minimum,
            scoring: self.scoring,
            ..Default::default()
        })))
    }

    fn explain(&self, reader: &SegmentReader, doc: DocId) -> crate::Result<Explanation> {
        let mut scorer = self.scorer(reader, 1.0)?;
        if scorer.seek(doc) != doc {
            return Err(does_not_match(doc));
        }
        let mut result = Explanation::new(
            "MinimumShouldMatch. sum of matching children",
            scorer.score(),
        );
        if self.scoring {
            for weight in &self.weights {
                if let Ok(detail) = weight.explain(reader, doc) {
                    result.add_detail(detail);
                }
            }
        }
        Ok(result)
    }
}

#[derive(Default, Clone, Copy)]
struct ThresholdCombiner {
    count: usize,
    // Lucene's BooleanScorer accumulates a document bucket in double precision
    // before narrowing it to a score. Preserve that rounding boundary for
    // minimum_should_match disjunctions.
    score: f64,
    minimum: usize,
    scoring: bool,
}

impl ScoreCombiner for ThresholdCombiner {
    const FILTER_MATCHES: bool = true;

    fn matches(&self) -> bool {
        self.count >= self.minimum
    }

    fn update<TScorer: Scorer>(&mut self, scorer: &mut TScorer) {
        self.count += 1;
        if self.scoring {
            self.score += f64::from(scorer.score());
        }
    }

    fn clear(&mut self) {
        self.count = 0;
        self.score = 0.0;
    }

    fn score(&self) -> Score {
        if self.scoring {
            self.score as Score
        } else {
            1.0
        }
    }
}
