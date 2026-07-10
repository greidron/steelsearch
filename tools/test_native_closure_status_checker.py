import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-native-closure-status-report.py"
RUNNER_PATH = ROOT / "tools" / "run-native-closure-validation.py"
CURRENT_GROUPS = [
    "non-native-inventory",
    "e2e-required-parity",
    "e2e-search-compat-parity",
    "e2e-broad-parity",
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


def transport_release_parity_result(
    *,
    complete: bool = True,
    missing_count: int = 0,
    matched_count: int = 174,
    include_scope_counts: bool = True,
    include_claim_boundary: bool = True,
):
    summary = {
        "release_parity_evidence_complete": complete,
        "release_parity_source_missing_action_count": missing_count,
        "release_parity_source_matched_action_count": matched_count,
    }
    if include_scope_counts:
        summary["release_evidence_scope_counts"] = {
            "runtime_action_parity": matched_count,
        }
    if include_claim_boundary:
        summary["transport_execution_claim_boundary"] = (
            "source-derived transport rows have scoped runtime-action evidence; "
            "the report does not promote generic transport action execution"
        )
    return {
        "group": "transport-action-coverage-current",
        "name": "transport_action_inventory_is_reported_with_current_peer_backpressure_evidence",
        "ok": True,
        "returncode": 0,
        "status": "ok",
        "summary": summary,
    }


def rest_api_coverage_result(
    *,
    raw_delta: int = 0,
    unexplained_delta: int = 0,
    matched_count: int = 378,
    in_scope_count: int = 378,
    ratio: float = 1.0,
    include_summary: bool = True,
    include_required_breakdown: bool = True,
):
    summary = {
        "live_required_matched_source_route_count": matched_count,
        "live_required_matched_source_route_ratio": ratio,
        "in_scope_source_route_count": in_scope_count,
        "unified_required_suite_steelsearch_only_breakdown": (
            [
                {
                    "fixture_path": "tools/fixtures/runtime-stateful-probe.json",
                    "report_path": "target/runtime-stateful-probe-report.json",
                    "steelsearch_only": 10,
                    "suite": "runtime-stateful-probe",
                }
            ]
            if include_required_breakdown
            else []
        ),
        "unified_non_required_suite_steelsearch_only_breakdown": [],
    }
    if include_summary:
        summary["unified_required_suite_steelsearch_only_summary"] = {
            "breakdown_total": 10,
            "raw_total": 10,
            "effective_total": 10,
            "raw_delta": raw_delta,
            "effective_delta": 0,
            "non_required_breakdown_total": 0,
            "effective_unexplained_delta": unexplained_delta,
        }
    return {
        "group": "rest-api-coverage-current",
        "name": "rest_api_source_inventory_coverage_is_reported_for_broad_required_live_suites",
        "ok": True,
        "returncode": 0,
        "status": "ok",
        "summary": summary,
    }


def load_checker_module():
    module_name = "check_native_closure_status_report"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_runner_module():
    module_name = "run_native_closure_validation"
    spec = importlib.util.spec_from_file_location(module_name, RUNNER_PATH)
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
                "results": [
                    rest_api_coverage_result(),
                    transport_release_parity_result(),
                ],
            },
            "runtime_peer_backpressure_current": {"passed": True},
            "final_cutover": {
                "passed": False,
                "startup_manifest_items": startup,
                "readiness_attachment_items": [*startup, "load_comparison"],
                "missing_items": startup,
                "readiness_attachment_missing_items": [*startup, "load_comparison"],
                "release_record_missing_items": [
                    *startup,
                    "load_comparison",
                    "pit_e2e_coverage",
                    "promotion_gate_suite",
                ],
                "evidence_inventory": {
                    "returncode": 0,
                    "summary": {
                        "complete": False,
                        "startup_missing_items": startup,
                        "readiness_attachment_missing_items": [*startup, "load_comparison"],
                        "release_record_missing_items": [
                            *startup,
                            "load_comparison",
                            "pit_e2e_coverage",
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

    def test_current_groups_match_validation_batch_groups(self):
        runner = load_runner_module()
        batch_groups = [
            *dict.fromkeys(test.group for test in runner.CURRENT_EVIDENCE_GATE_BATCH)
        ]

        self.assertEqual(CURRENT_GROUPS, batch_groups)
        self.assertEqual(tuple(CURRENT_GROUPS), self.checker.CURRENT_EVIDENCE_GROUPS)

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

    def test_rejects_current_evidence_without_transport_release_parity_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            rest_api_coverage_result()
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results transport-action-coverage-current is missing",
            result["errors"],
        )

    def test_rejects_current_evidence_without_rest_api_coverage_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            transport_release_parity_result()
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results rest-api-coverage-current is missing",
            result["errors"],
        )

    def test_rejects_rest_api_coverage_without_steelsearch_only_summary(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            rest_api_coverage_result(include_summary=False),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST steelsearch-only summary is missing",
            result["errors"],
        )

    def test_rejects_rest_api_coverage_with_unexplained_steelsearch_only_delta(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            rest_api_coverage_result(raw_delta=1, unexplained_delta=1),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST steelsearch-only raw delta is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST steelsearch-only unexplained effective delta is not zero",
            result["errors"],
        )

    def test_rejects_rest_api_coverage_without_full_live_source_route_match(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            rest_api_coverage_result(matched_count=377, in_scope_count=378, ratio=0.997),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST live required matched source route count "
            "does not equal in-scope source route count",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST live required matched source route ratio is not 1.0",
            result["errors"],
        )

    def test_rejects_incomplete_transport_release_parity_summary(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            rest_api_coverage_result(),
            transport_release_parity_result(complete=False, missing_count=1, matched_count=0)
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results transport release parity evidence is not complete",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport release parity missing action count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport release parity matched action count is not positive",
            result["errors"],
        )

    def test_rejects_transport_release_parity_without_runtime_action_scope_counts(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            rest_api_coverage_result(),
            transport_release_parity_result(include_scope_counts=False),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results transport release evidence scope counts are missing",
            result["errors"],
        )

    def test_rejects_transport_release_parity_scope_count_mismatch(self):
        report = valid_report()
        transport = transport_release_parity_result(matched_count=174)
        transport["summary"]["release_evidence_scope_counts"]["runtime_action_parity"] = 173
        report["gates"]["current_evidence"]["results"] = [
            rest_api_coverage_result(),
            transport,
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results transport release runtime-action scope count "
            "does not match matched action count",
            result["errors"],
        )

    def test_rejects_transport_release_parity_without_claim_boundary(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            rest_api_coverage_result(),
            transport_release_parity_result(include_claim_boundary=False),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results transport execution claim boundary is missing",
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

    def test_expected_git_head_accepts_matching_metadata(self):
        result = self.checker.validate_report(valid_report(), expected_git_head="abc123")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["errors"], [])

    def test_expected_git_head_rejects_stale_metadata(self):
        result = self.checker.validate_report(valid_report(), expected_git_head="def456")

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "metadata.git_head does not match current HEAD (abc123 != def456)",
            result["errors"],
        )

    def test_rejects_passed_final_cutover_with_missing_readiness_attachment(self):
        report = valid_report()
        report["summary"]["final_cutover_ready"] = True
        report["summary"]["status"] = "ready"
        report["gates"]["final_cutover"]["passed"] = True
        report["gates"]["final_cutover"]["missing_items"] = []
        report["gates"]["final_cutover"]["readiness_attachment_missing_items"] = [
            "load_comparison"
        ]
        report["gates"]["final_cutover"]["release_record_missing_items"] = []

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
        report["gates"]["final_cutover"]["release_record_missing_items"] = [
            "promotion_gate_suite"
        ]
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
            "final_cutover passed but release_record_missing_items is not empty",
            result["errors"],
        )
        self.assertIn(
            "final_cutover passed but evidence inventory release_record_missing_items is not empty",
            result["errors"],
        )


if __name__ == "__main__":
    unittest.main()
