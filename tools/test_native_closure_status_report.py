import importlib.util
import json
import sys
import tempfile
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
        self.assertEqual(final_cutover["startup_manifest_items"], final_cutover["missing_items"])
        self.assertIn("load_comparison", final_cutover["readiness_attachment_items"])
        self.assertNotIn("load_comparison", final_cutover["startup_manifest_items"])
        self.assertEqual(
            final_cutover["required_item_inputs"]["benchmark_coverage"]["attach_argument"],
            "--benchmark-report",
        )
        self.assertIn(
            "--release-readiness-file",
            final_cutover["manifest_command_template"],
        )
        self.assertEqual(
            final_cutover["readiness_attachment_inputs"]["load_comparison"]["attach_argument"],
            "--load-comparison-report",
        )
        self.assertIn(
            "--load-comparison-report",
            final_cutover["manifest_command_template"],
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

    def test_final_cutover_item_inputs_are_limited_to_requested_items(self):
        inputs = self.reporter.final_cutover_item_inputs(
            ["load_test_coverage", "rolling_upgrade_coverage"]
        )

        self.assertEqual(set(inputs), {"load_test_coverage", "rolling_upgrade_coverage"})
        self.assertEqual(inputs["load_test_coverage"]["attach_argument"], "--load-report")

    def test_complete_release_readiness_manifest_marks_final_cutover_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            manifest = temp_dir / "release-readiness.json"
            artifacts = {
                "benchmark_coverage": "benchmark.jsonl",
                "load_test_coverage": "load.json",
                "chaos_test_coverage": "chaos.json",
                "packaging_verified": "packaging.json",
                "rolling_upgrade_coverage": "rolling.json",
            }
            for artifact in artifacts.values():
                (temp_dir / artifact).write_text("{}\n", encoding="utf-8")
            manifest.write_text(
                json.dumps(
                    {
                        name: {
                            "passed": True,
                            "artifact_path": artifact,
                            "blockers": [],
                        }
                        for name, artifact in artifacts.items()
                    }
                ),
                encoding="utf-8",
            )

            final_cutover = self.reporter.inspect_release_readiness(manifest)
            report = self.reporter.build_status_report(
                current_evidence={"passed": True},
                peer_backpressure={"passed": True},
                final_cutover=final_cutover,
                require_final_cutover=True,
            )

            self.assertTrue(final_cutover["passed"])
            self.assertEqual(final_cutover["missing_items"], [])
            self.assertTrue(report["summary"]["passed"])
            self.assertEqual(report["summary"]["status"], "ready")


if __name__ == "__main__":
    unittest.main()
