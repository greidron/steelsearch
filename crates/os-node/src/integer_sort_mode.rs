#[derive(Clone, Copy, Debug)]
pub(crate) enum IntegerSortMode {
    Avg,
    Median,
}

pub(crate) fn reduce_integer_sort_values(values: &[i64], mode: IntegerSortMode) -> Option<i64> {
    if values.is_empty() {
        return None;
    }
    match mode {
        IntegerSortMode::Avg => {
            // OpenSearch MultiValueMode uses Java long addition, including overflow.
            let sum = values
                .iter()
                .fold(0_i64, |sum, value| sum.wrapping_add(*value));
            Some(if values.len() == 1 {
                sum
            } else {
                java_round(sum as f64 / values.len() as f64)
            })
        }
        IntegerSortMode::Median => {
            let mut sorted = values.to_vec();
            sorted.sort_unstable();
            let middle = sorted.len() / 2;
            Some(if sorted.len() % 2 == 1 {
                sorted[middle]
            } else {
                java_round((sorted[middle - 1] as f64 + sorted[middle] as f64) / 2.0)
            })
        }
    }
}

fn java_round(value: f64) -> i64 {
    // Adding 0.5 before floor can round an already integral large double upward.
    let floor = value.floor();
    (if value - floor >= 0.5 {
        floor + 1.0
    } else {
        floor
    }) as i64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn half_values_round_toward_positive_infinity() {
        for (value, expected) in [
            (-2.5, -2),
            (-1.5, -1),
            (-0.5, 0),
            (0.5, 1),
            (1.5, 2),
            (2.5, 3),
        ] {
            assert_eq!(java_round(value), expected);
        }
        assert_eq!(java_round(f64::from_bits(0.5_f64.to_bits() - 1)), 0);
        assert_eq!(java_round(f64::from_bits((-0.5_f64).to_bits() + 1)), -1);
        assert_eq!(java_round(4_503_599_627_370_497.0), 4_503_599_627_370_497);
    }

    #[test]
    fn integer_extremes_and_singletons_preserve_java_semantics() {
        for mode in [IntegerSortMode::Avg, IntegerSortMode::Median] {
            assert_eq!(reduce_integer_sort_values(&[], mode), None);
            for value in [i64::MIN, i64::MAX, 9_007_199_254_740_993] {
                assert_eq!(reduce_integer_sort_values(&[value], mode), Some(value));
            }
            assert_eq!(reduce_integer_sort_values(&[-3, 8], mode), Some(3));
            assert_eq!(reduce_integer_sort_values(&[-3, 0], mode), Some(-1));
        }
        assert_eq!(
            reduce_integer_sort_values(&[i64::MAX, i64::MAX], IntegerSortMode::Avg),
            Some(-1)
        );
        assert_eq!(
            reduce_integer_sort_values(&[i64::MIN, i64::MIN], IntegerSortMode::Avg),
            Some(0)
        );
        assert_eq!(
            reduce_integer_sort_values(&[i64::MAX, i64::MAX], IntegerSortMode::Median),
            Some(i64::MAX)
        );
        assert_eq!(
            reduce_integer_sort_values(&[i64::MIN, i64::MAX], IntegerSortMode::Median),
            Some(0)
        );
    }

    #[test]
    fn unsorted_and_duplicate_values_keep_all_contributions() {
        assert_eq!(
            reduce_integer_sort_values(&[9, 2, 5], IntegerSortMode::Avg),
            Some(5)
        );
        assert_eq!(
            reduce_integer_sort_values(&[9, 2, 5], IntegerSortMode::Median),
            Some(5)
        );
        assert_eq!(
            reduce_integer_sort_values(&[9, 2, 2, 5], IntegerSortMode::Avg),
            Some(5)
        );
        assert_eq!(
            reduce_integer_sort_values(&[9, 2, 2, 5], IntegerSortMode::Median),
            Some(4)
        );
    }
}
