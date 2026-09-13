import unittest
from decimal import Decimal

from core_performance_budget import METRICS, compare_metrics


class CorePerformanceBudgetTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {key: 100 for key in METRICS}
        self.candidate = dict(self.baseline)

    def test_complete_scope_and_numeric_pass_is_not_acceptance(self):
        result = compare_metrics(self.baseline, self.candidate)
        self.assertEqual(len(result["metrics"]), 44)
        self.assertTrue(result["numeric_budget_passed"])
        self.assertFalse(result["acceptance_established"])

    def test_each_latency_boundary_independently(self):
        for key, direction in METRICS.items():
            if direction != "lower":
                continue
            for value, expected in ((104.99, True), (105, True), (105.01, False)):
                with self.subTest(key=key, value=value):
                    candidate = dict(self.baseline, **{key: value})
                    result = compare_metrics(self.baseline, candidate)
                    self.assertEqual(result["numeric_budget_passed"], expected)
                    self.assertEqual(result["failed_metrics"], [] if expected else [key])

    def test_each_throughput_boundary_independently(self):
        for topology in ("single-node", "three-node"):
            key = f"{topology}/throughput"
            for value, expected in ((95.01, True), (95, True), (94.99, False)):
                with self.subTest(key=key, value=value):
                    candidate = dict(self.baseline, **{key: value})
                    self.assertEqual(compare_metrics(self.baseline, candidate)["numeric_budget_passed"], expected)

    def test_two_three_percent_increases_fail_cumulatively(self):
        key = "three-node/sort_filter/mean"
        self.candidate[key] = Decimal("100") * Decimal("1.03") ** 2
        result = compare_metrics(self.baseline, self.candidate)
        row = next(row for row in result["metrics"] if row["metric"] == key)
        self.assertFalse(result["numeric_budget_passed"])
        self.assertEqual(Decimal(row["regression_percent"]), Decimal("6.09"))

    def test_faster_other_metrics_cannot_mask_regression(self):
        self.candidate = {key: (200 if direction == "higher" else 50)
                          for key, direction in METRICS.items()}
        key = "three-node/refresh/p99"
        self.candidate[key] = 106
        result = compare_metrics(self.baseline, self.candidate)
        self.assertEqual(result["failed_metrics"], [key])

    def test_improvements_are_negative_regressions(self):
        self.candidate["single-node/throughput"] = 110
        self.candidate["single-node/write/mean"] = 90
        result = compare_metrics(self.baseline, self.candidate)
        for row in result["metrics"]:
            if row["metric"] in ("single-node/throughput", "single-node/write/mean"):
                self.assertEqual(Decimal(row["regression_percent"]), Decimal(-10))

    def test_missing_extra_plugin_and_empty_metrics_rejected(self):
        malformed = [{}, {**self.baseline, "single-node/vector/mean": 100}]
        for key in METRICS:
            malformed.append({name: value for name, value in self.baseline.items() if name != key})
        for values in malformed:
            for side in ("baseline", "candidate"):
                with self.subTest(side=side, keys=len(values)), self.assertRaises(ValueError):
                    compare_metrics(values if side == "baseline" else self.baseline,
                                    values if side == "candidate" else self.candidate)

    def test_invalid_values_rejected_on_both_sides(self):
        values = (True, False, 0, -1, "100", None, float("nan"), float("inf"),
                  Decimal("NaN"), Decimal("Infinity"))
        for value in values:
            for side in ("baseline", "candidate"):
                with self.subTest(side=side, value=value), self.assertRaises(ValueError):
                    invalid = dict(self.baseline, **{"single-node/write/mean": value})
                    compare_metrics(invalid if side == "baseline" else self.baseline,
                                    invalid if side == "candidate" else self.candidate)

    def test_decimal_limit_does_not_round_just_over_five_to_pass(self):
        key = "single-node/write/mean"
        self.baseline[key] = Decimal("0.1")
        self.candidate[key] = Decimal("0.105000000000000001")
        self.assertFalse(compare_metrics(self.baseline, self.candidate)["numeric_budget_passed"])
        self.candidate[key] = Decimal("0.105")
        self.assertTrue(compare_metrics(self.baseline, self.candidate)["numeric_budget_passed"])

    def test_inputs_are_not_modified(self):
        before = dict(self.baseline)
        after = dict(self.candidate)
        compare_metrics(self.baseline, self.candidate)
        self.assertEqual(before, self.baseline)
        self.assertEqual(after, self.candidate)


if __name__ == "__main__":
    unittest.main()
