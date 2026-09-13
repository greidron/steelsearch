use std::cell::Cell;

use os_engine::{EngineError, EngineResult};

/// Allocation accounting for a serial collector tree, not final reduce accounting.
pub(crate) struct BucketAllocationBudget {
    limit: u32,
    consumed: Cell<u64>,
}

impl Default for BucketAllocationBudget {
    fn default() -> Self {
        Self::new(65_535)
    }
}

impl BucketAllocationBudget {
    pub(crate) fn new(limit: u32) -> Self {
        Self {
            limit,
            consumed: Cell::new(0),
        }
    }

    pub(crate) fn consume(&self, count: u64) -> EngineResult<()> {
        let total = self.consumed.get().saturating_add(count);
        self.consumed.set(total);
        if total > u64::from(self.limit) {
            return Err(EngineError::TooManyBuckets {
                max_buckets: self.limit,
                bucket_count: total,
            });
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cumulative_limit_is_inclusive_and_failure_cannot_be_cleared() {
        let budget = BucketAllocationBudget::new(5);
        budget.consume(2).unwrap();
        budget.consume(3).unwrap();
        let expected = Err(EngineError::TooManyBuckets {
            max_buckets: 5,
            bucket_count: 6,
        });
        assert_eq!(budget.consume(1), expected);
        assert_eq!(budget.consume(0), expected);
        assert!(BucketAllocationBudget::new(5).consume(5).is_ok());
    }

    #[test]
    fn zero_limit_and_overflow_do_not_disable_accounting() {
        let zero = BucketAllocationBudget::new(0);
        zero.consume(0).unwrap();
        assert!(zero.consume(1).is_err());
        let budget = BucketAllocationBudget::new(u32::MAX);
        budget.consume(u64::from(u32::MAX)).unwrap();
        assert_eq!(
            budget.consume(u64::MAX),
            Err(EngineError::TooManyBuckets {
                max_buckets: u32::MAX,
                bucket_count: u64::MAX,
            })
        );
        assert!(budget.consume(1).is_err());
    }
}
