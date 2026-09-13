import copy
import unittest
from decimal import Decimal

from core_performance_budget import METRICS
from dump_core_performance_table import metric_indexes, minimum_label, range_label, relative_ratio


class CorePerformanceTableTests(unittest.TestCase):
    def test_all_scores_use_higher_is_faster_direction(self):
        self.assertEqual(relative_ratio("higher", "100", "80"), Decimal("0.8"))
        self.assertEqual(relative_ratio("lower", "100", "80"), Decimal("1.25"))
        self.assertEqual(range_label([Decimal("0.9504"), Decimal("0.9506")]), "0.950-0.951x")
        self.assertEqual(minimum_label([Decimal("1.2"), Decimal("0.9506")]), "0.951x")

    def test_repeated_published_comparisons_preserve_both_runs(self):
        rows = []
        reference = {}
        for metric, direction in METRICS.items():
            rows.append({"metric": metric, "baseline": "100", "candidate": "80"})
            reference[metric] = "160" if direction == "higher" else "40"
        check = {"published": {"metrics": rows, "opensearch_metrics": reference}}
        scores = metric_indexes({"checks": [check, copy.deepcopy(check)]})
        self.assertEqual(scores["single-node/throughput"]["v060"], [Decimal("0.8"), Decimal("0.8")])
        self.assertEqual(scores["single-node/write/mean"]["opensearch"], [Decimal("0.5"), Decimal("0.5")])


if __name__ == "__main__":
    unittest.main()
