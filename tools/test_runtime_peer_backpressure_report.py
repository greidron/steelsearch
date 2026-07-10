import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-runtime-peer-backpressure-report.py"


def load_checker_module():
    module_name = "check_runtime_peer_backpressure_report"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class RuntimePeerBackpressureReportTests(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker_module()

    def test_accepts_mixed_profile_with_positive_peer_counters(self):
        result = self.checker.validate_report(
            {
                "summary": {"passed": True, "profile": "mixed-java-rust-query-phase"},
                "profile": {
                    "name": "mixed-java-rust-query-phase",
                    "required_readbacks": [
                        "Rust receiver rejects excess query-phase remote transport work",
                        "Rust receiver exposes remote_transport rejected/completed through _cat and _nodes/stats",
                        "Java peer exposes analogous search thread-pool rejection through _cat and _nodes/stats",
                        "profile report records both surfaces through live transport and REST counter readbacks",
                    ],
                },
                "results": {
                    "steelsearch": {
                        "passed": True,
                        "pool": "remote_transport",
                        "active_row": {"active": "1"},
                        "rejected_row": {"rejected": "1"},
                        "completed_row": {"completed": "1"},
                        "node_stats": {"rejected": 1, "completed": 1},
                    },
                    "opensearch": {
                        "passed": True,
                        "pool": "search",
                        "before_row": {"rejected": "0"},
                        "after_row": {"rejected": "159"},
                        "node_stats": {"rejected": 159, "completed": 11},
                        "http_429_count": 159,
                        "error_samples": [{"status": 429}],
                    },
                },
            }
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["errors"], [])

    def test_rejects_wrong_profile_and_missing_rejections(self):
        result = self.checker.validate_report(
            {
                "summary": {"passed": True, "profile": "same-host-query-pressure"},
                "profile": {"name": "same-host-query-pressure", "required_readbacks": []},
                "results": {
                    "steelsearch": {
                        "passed": True,
                        "pool": "remote_transport",
                        "node_stats": {"rejected": 0, "completed": 1},
                    },
                    "opensearch": {
                        "passed": True,
                        "pool": "search",
                        "node_stats": {"rejected": 1, "completed": 1},
                    },
                },
            }
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "summary.profile is not mixed-java-rust-query-phase",
            result["errors"],
        )
        self.assertIn(
            "results.steelsearch.node_stats.rejected is 0, expected >= 1",
            result["errors"],
        )
        self.assertIn("profile.required_readbacks is incomplete", result["errors"])

    def test_rejects_report_without_live_readback_rows_and_429_sample(self):
        result = self.checker.validate_report(
            {
                "summary": {"passed": True, "profile": "mixed-java-rust-query-phase"},
                "profile": {
                    "name": "mixed-java-rust-query-phase",
                    "required_readbacks": [
                        "Rust receiver rejects excess query-phase remote transport work",
                        "Rust receiver exposes remote_transport rejected/completed through _cat and _nodes/stats",
                        "Java peer exposes analogous search thread-pool rejection through _cat and _nodes/stats",
                        "profile report records both surfaces through live transport and REST counter readbacks",
                    ],
                },
                "results": {
                    "steelsearch": {
                        "passed": True,
                        "pool": "remote_transport",
                        "node_stats": {"rejected": 1, "completed": 1},
                    },
                    "opensearch": {
                        "passed": True,
                        "pool": "search",
                        "before_row": {"rejected": "5"},
                        "after_row": {"rejected": "5"},
                        "node_stats": {"rejected": 1, "completed": 1},
                        "http_429_count": 0,
                        "error_samples": [],
                    },
                },
            }
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "results.steelsearch.active_row.active is missing or not an integer",
            result["errors"],
        )
        self.assertIn(
            "results.steelsearch.rejected_row.rejected is missing or not an integer",
            result["errors"],
        )
        self.assertIn(
            "results.steelsearch.completed_row.completed is missing or not an integer",
            result["errors"],
        )
        self.assertIn("results.opensearch rejected counter did not increase", result["errors"])
        self.assertIn("results.opensearch.http_429_count is 0, expected >= 1", result["errors"])
        self.assertIn("results.opensearch 429 error sample is missing", result["errors"])


if __name__ == "__main__":
    unittest.main()
