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
                "profile": {"name": "mixed-java-rust-query-phase"},
                "results": {
                    "steelsearch": {
                        "passed": True,
                        "pool": "remote_transport",
                        "node_stats": {"rejected": 1, "completed": 1},
                    },
                    "opensearch": {
                        "passed": True,
                        "pool": "search",
                        "node_stats": {"rejected": 159, "completed": 11},
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
                "profile": {"name": "same-host-query-pressure"},
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


if __name__ == "__main__":
    unittest.main()
