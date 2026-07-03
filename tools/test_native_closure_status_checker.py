import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-native-closure-status-report.py"
CURRENT_GROUPS = [
    "non-native-inventory",
    "e2e-required-parity",
    "e2e-search-compat-parity",
    "broad-e2e-parity-current",
    "rest-api-coverage-current",
    "transport-action-coverage-current",
    "mixed-cluster-coverage-current",
    "materialization-priority-current",
    "production-security-current",
    "startup-bootstrap-current",
    "runtime-controls-current",
    "release-evidence-inventory-current",
    "release-readiness-tooling",
]


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
        "metadata": {
            "generated_at_epoch_seconds": 1,
            "git_head": "abc123",
            "git_clean": True,
            "git_status_short": "",
        },
        "summary": {
            "passed": True,
            "current_evidence_ready": True,
            "runtime_peer_backpressure_ready": True,
            "final_cutover_ready": False,
            "final_cutover_required": False,
            "status": "current-evidence-ready-final-cutover-pending",
        },
        "gates": {
            "current_evidence": {
                "passed": True,
                "required_groups": CURRENT_GROUPS,
                "groups": {
                    group: {"ok": True, "status": "ok", "returncode": 0}
                    for group in CURRENT_GROUPS
                },
            },
            "runtime_peer_backpressure_current": {"passed": True},
            "final_cutover": {
                "passed": False,
                "startup_manifest_items": startup,
                "readiness_attachment_items": [*startup, "load_comparison"],
                "missing_items": startup,
                "readiness_attachment_missing_items": [*startup, "load_comparison"],
                "evidence_inventory": {
                    "returncode": 0,
                    "summary": {
                        "complete": False,
                        "startup_missing_items": startup,
                        "readiness_attachment_missing_items": [*startup, "load_comparison"],
                        "release_record_missing_items": [
                            *startup,
                            "load_comparison",
                            "promotion_gate_suite",
                        ],
                    }
                },
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

    def test_rejects_missing_current_evidence_group(self):
        report = valid_report()
        del report["gates"]["current_evidence"]["groups"]["mixed-cluster-coverage-current"]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.groups.mixed-cluster-coverage-current is missing",
            result["errors"],
        )

    def test_rejects_failed_current_evidence_group(self):
        report = valid_report()
        report["gates"]["current_evidence"]["groups"]["transport-action-coverage-current"]["ok"] = False

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.groups.transport-action-coverage-current.ok is not true",
            result["errors"],
        )

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

    def test_accepts_dirty_worktree_metadata_without_clean_requirement(self):
        report = valid_report()
        report["metadata"]["git_clean"] = False
        report["metadata"]["git_status_short"] = " M tools/check-native-closure-status-report.py"

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["errors"], [])

    def test_require_clean_worktree_accepts_clean_metadata(self):
        result = self.checker.validate_report(valid_report(), require_clean_worktree=True)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["errors"], [])

    def test_require_clean_worktree_rejects_dirty_metadata(self):
        report = valid_report()
        report["metadata"]["git_clean"] = False
        report["metadata"]["git_status_short"] = " M tools/check-native-closure-status-report.py"

        result = self.checker.validate_report(report, require_clean_worktree=True)

        self.assertEqual(result["status"], "failed")
        self.assertIn("metadata.git_clean is not true", result["errors"])
        self.assertIn("metadata.git_status_short is not empty", result["errors"])

    def test_rejects_passed_final_cutover_with_missing_readiness_attachment(self):
        report = valid_report()
        report["summary"]["final_cutover_ready"] = True
        report["summary"]["status"] = "ready"
        report["gates"]["final_cutover"]["passed"] = True
        report["gates"]["final_cutover"]["missing_items"] = []
        report["gates"]["final_cutover"]["readiness_attachment_missing_items"] = [
            "load_comparison"
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "final_cutover passed but readiness_attachment_missing_items is not empty",
            result["errors"],
        )

    def test_rejects_passed_final_cutover_with_incomplete_evidence_inventory(self):
        report = valid_report()
        report["summary"]["final_cutover_ready"] = True
        report["summary"]["status"] = "ready"
        report["gates"]["final_cutover"]["passed"] = True
        report["gates"]["final_cutover"]["missing_items"] = []
        report["gates"]["final_cutover"]["readiness_attachment_missing_items"] = []
        report["gates"]["final_cutover"]["evidence_inventory"]["summary"] = {
            "complete": False,
            "startup_missing_items": [],
            "readiness_attachment_missing_items": ["load_comparison"],
            "release_record_missing_items": ["promotion_gate_suite"],
        }

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "final_cutover passed but evidence inventory is not complete",
            result["errors"],
        )
        self.assertIn(
            "final_cutover passed but evidence inventory readiness_attachment_missing_items is not empty",
            result["errors"],
        )
        self.assertIn(
            "final_cutover passed but evidence inventory release_record_missing_items is not empty",
            result["errors"],
        )


if __name__ == "__main__":
    unittest.main()
