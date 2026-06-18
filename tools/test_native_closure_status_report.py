import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "tools" / "report-native-closure-status.py"


def load_report_module():
    module_name = "report_native_closure_status"
    spec = importlib.util.spec_from_file_location(module_name, REPORT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class NativeClosureStatusReportTests(unittest.TestCase):
    def setUp(self):
        self.reporter = load_report_module()

    def test_status_is_pending_when_current_evidence_passes_without_final_cutover(self):
        report = self.reporter.build_status_report(
            current_evidence={"passed": True},
            peer_backpressure={"passed": True},
            final_cutover={"passed": False, "status": "pending"},
            require_final_cutover=False,
        )

        self.assertTrue(report["summary"]["passed"])
        self.assertTrue(report["summary"]["current_evidence_ready"])
        self.assertFalse(report["summary"]["final_cutover_ready"])
        self.assertEqual(
            report["summary"]["status"],
            "current-evidence-ready-final-cutover-pending",
        )

    def test_status_fails_when_final_cutover_is_required_but_missing(self):
        report = self.reporter.build_status_report(
            current_evidence={"passed": True},
            peer_backpressure={"passed": True},
            final_cutover={"passed": False, "status": "pending"},
            require_final_cutover=True,
        )

        self.assertFalse(report["summary"]["passed"])
        self.assertEqual(report["summary"]["status"], "final-cutover-missing")

    def test_status_is_ready_when_all_gates_pass(self):
        report = self.reporter.build_status_report(
            current_evidence={"passed": True},
            peer_backpressure={"passed": True},
            final_cutover={"passed": True, "status": "ok"},
            require_final_cutover=True,
        )

        self.assertTrue(report["summary"]["passed"])
        self.assertEqual(report["summary"]["status"], "ready")

    def test_missing_manifest_lists_required_final_cutover_items(self):
        final_cutover = self.reporter.inspect_release_readiness(None)

        self.assertEqual(final_cutover["status"], "pending")
        self.assertEqual(
            final_cutover["missing_items"],
            [
                "benchmark_coverage",
                "load_test_coverage",
                "chaos_test_coverage",
                "packaging_verified",
                "rolling_upgrade_coverage",
            ],
        )

    def test_missing_release_items_reports_only_failed_or_missing_items(self):
        missing = self.reporter.missing_release_items(
            {
                "items": {
                    "benchmark_coverage": {"passed": True, "errors": []},
                    "load_test_coverage": {"passed": False, "errors": ["blocked"]},
                    "chaos_test_coverage": {"passed": True, "errors": []},
                    "packaging_verified": {"passed": True, "errors": []},
                }
            }
        )

        self.assertEqual(missing, ["load_test_coverage", "rolling_upgrade_coverage"])


if __name__ == "__main__":
    unittest.main()
