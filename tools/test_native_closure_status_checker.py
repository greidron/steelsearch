import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-native-closure-status-report.py"


def load_checker_module():
    module_name = "check_native_closure_status_report"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def valid_report():
    startup = [
        "benchmark_coverage",
        "load_test_coverage",
        "chaos_test_coverage",
        "packaging_verified",
        "rolling_upgrade_coverage",
    ]
    return {
        "summary": {
            "passed": True,
            "current_evidence_ready": True,
            "runtime_peer_backpressure_ready": True,
            "final_cutover_ready": False,
            "final_cutover_required": False,
            "status": "current-evidence-ready-final-cutover-pending",
        },
        "gates": {
            "current_evidence": {"passed": True},
            "runtime_peer_backpressure_current": {"passed": True},
            "final_cutover": {
                "passed": False,
                "startup_manifest_items": startup,
                "readiness_attachment_items": [*startup, "load_comparison"],
                "missing_items": startup,
            },
        },
    }


class NativeClosureStatusCheckerTests(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker_module()

    def test_accepts_current_evidence_ready_final_cutover_pending(self):
        result = self.checker.validate_report(valid_report())

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["summary"]["passed"])

    def test_rejects_load_comparison_in_startup_manifest_items(self):
        report = valid_report()
        report["gates"]["final_cutover"]["startup_manifest_items"].append("load_comparison")

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn("final_cutover.startup_manifest_items mismatch", result["errors"])
        self.assertIn("load_comparison must not be a startup manifest item", result["errors"])

    def test_require_final_cutover_rejects_pending_report(self):
        result = self.checker.validate_report(valid_report(), require_final_cutover=True)

        self.assertEqual(result["status"], "failed")
        self.assertIn("summary.final_cutover_ready is not true", result["errors"])
        self.assertIn("final_cutover.passed is not true", result["errors"])


if __name__ == "__main__":
    unittest.main()
