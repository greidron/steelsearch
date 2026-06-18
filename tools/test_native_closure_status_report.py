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


if __name__ == "__main__":
    unittest.main()
