import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location("terms_cardinality_diagnostic", Path(__file__).with_name("run-terms-cardinality-diagnostic.py"))
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class TermsCardinalityDiagnosticTests(unittest.TestCase):
    def test_benchmark_values_counts_and_order(self):
        self.assertEqual(diagnostic.expected_buckets(3, pattern="benchmark"), [
            {"key": "commerce", "doc_count": 1667},
            {"key": "search", "doc_count": 1667},
            {"key": "analytics", "doc_count": 1666},
        ])

    def test_all_cardinalities_preserve_totals_and_tie_order(self):
        for cardinality in diagnostic.CARDINALITIES:
            buckets = diagnostic.expected_buckets(cardinality)
            self.assertEqual(len(buckets), cardinality)
            self.assertEqual(sum(bucket["doc_count"] for bucket in buckets), 5000)
            self.assertEqual(buckets, sorted(buckets, key=lambda bucket: (-bucket["doc_count"], bucket["key"])))
            self.assertEqual({bucket["key"] for bucket in buckets}, {f"key-{i:04}" for i in range(cardinality)})


if __name__ == "__main__":
    unittest.main()
