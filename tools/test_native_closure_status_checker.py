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


def pit_e2e_coverage_result(
    *,
    required_count: int = 17,
    compared_count: int = 17,
    non_passed_count: int = 0,
    suite_count: int = 3,
    pit_case_count: int = 232,
    include_summary: bool = True,
):
    result = {
        "group": "e2e-search-compat-parity",
        "name": "pit_e2e_reports_have_required_opensearch_compared_cases_without_skips",
        "ok": True,
        "returncode": 0,
        "status": "ok",
    }
    if include_summary:
        result["summary"] = {
            "required_pit_case_count": required_count,
            "required_pit_compared_case_count": compared_count,
            "non_passed_pit_case_count": non_passed_count,
            "suite_count": suite_count,
            "pit_case_count": pit_case_count,
        }
    return result


def search_required_parity_result(
    *,
    semantic_suite_count: int = 3,
    semantic_report_path_count: int | None = None,
    passed: bool = True,
):
    report_path_count = (
        semantic_suite_count
        if semantic_report_path_count is None
        else semantic_report_path_count
    )
    return search_parity_result(
        group="e2e-required-parity",
        name="search_semantic_and_vector_search_e2e_reports_have_no_failed_missing_or_skipped_cases",
        semantic_suite_count=semantic_suite_count,
        semantic_report_path_count=report_path_count,
        passed=passed,
    )


def search_compat_parity_result(
    *,
    semantic_suite_count: int = 5,
    semantic_report_path_count: int | None = None,
    passed: bool = True,
):
    report_path_count = (
        semantic_suite_count
        if semantic_report_path_count is None
        else semantic_report_path_count
    )
    return search_parity_result(
        group="e2e-search-compat-parity",
        name="search_compat_and_strict_e2e_reports_have_no_failed_or_missing_cases",
        semantic_suite_count=semantic_suite_count,
        semantic_report_path_count=report_path_count,
        passed=passed,
    )


def search_parity_result(
    *,
    group: str,
    name: str,
    semantic_suite_count: int,
    semantic_report_path_count: int,
    passed: bool,
):
    suite_counts = {
        "distributed_parity": 0,
        "durability_parity": 0,
        "route_parity": 0,
        "security_parity": 0,
        "semantic_parity": semantic_suite_count,
    }
    report_path_counts = dict(suite_counts)
    report_path_counts["semantic_parity"] = semantic_report_path_count
    return {
        "group": group,
        "name": name,
        "ok": passed,
        "returncode": 0 if passed else 1,
        "status": "ok" if passed else "failed",
        "summary": {
            "passed": passed,
            "required_sections": [],
            "required_section_count": 0,
            "required_section_suite_counts": suite_counts,
            "required_section_report_path_counts": report_path_counts,
        },
    }


def broad_e2e_section_result(
    *,
    required_sections: list[str] | None = None,
    suite_counts: dict[str, int] | None = None,
    report_path_counts: dict[str, int] | None = None,
):
    sections = required_sections or [
        "route_parity",
        "semantic_parity",
        "durability_parity",
        "security_parity",
        "distributed_parity",
    ]
    counts = suite_counts or {section: 1 for section in sections}
    path_counts = report_path_counts or dict(counts)
    return {
        "group": "e2e-broad-parity",
        "name": "broad_unified_opensearch_e2e_report_has_no_failed_missing_or_drifted_required_suites",
        "ok": True,
        "returncode": 0,
        "status": "ok",
        "summary": {
            "passed": True,
            "required_sections": sections,
            "required_section_count": len(sections),
            "required_section_suite_counts": counts,
            "required_section_report_path_counts": path_counts,
        },
    }


def mixed_cluster_coverage_result(
    *,
    opensearch_to_steelsearch_passed: bool = True,
    steelsearch_to_opensearch_passed: bool = True,
    missing_required_phase_count: int = 0,
    phase_assertion_error_count: int = 0,
    include_claim_boundary: bool = True,
):
    summary = {
        "checkpoint_drift_ok": True,
        "checkpoint_monotonicity_ok": True,
        "failure_node_loss_passed_report_count": 3,
        "failure_node_loss_report_count": 3,
        "opensearch_to_steelsearch_passed": opensearch_to_steelsearch_passed,
        "passed": True,
        "phase_c_fresh_report_count": 13,
        "phase_c_passed_report_count": 13,
        "phase_c_report_count": 13,
        "retention_lease_metadata_ok": True,
        "shard_movement_fresh": True,
        "shard_movement_missing_required_phase_count": missing_required_phase_count,
        "shard_movement_passed": True,
        "shard_movement_phase_assertion_error_count": phase_assertion_error_count,
        "shard_movement_phase_count": 13,
        "shard_movement_required_interruption_phase_count": 6,
        "shard_movement_required_phase_count": 7,
        "steelsearch_to_opensearch_passed": steelsearch_to_opensearch_passed,
        "transport_log_ok": True,
        "unsupported_allocation_explain_ok": True,
    }
    if include_claim_boundary:
        summary["claim_boundary"] = (
            "representative mixed-cluster join, movement, recovery, failure, "
            "publication, allocation, write-replication, and interrupted shard "
            "movement evidence is present"
        )
    return {
        "group": "mixed-cluster-coverage-current",
        "name": "mixed_cluster_join_and_movement_coverage_is_reported_with_scope_boundary",
        "ok": True,
        "returncode": 0,
        "status": "ok",
        "summary": summary,
    }


def mixed_cluster_remote_pit_result(
    *,
    remote_pit_case_count: int = 5,
    failed_count: int = 0,
    remote_pit_required: bool = True,
):
    return {
        "group": "mixed-cluster-coverage-current",
        "name": "multi_node_transport_admin_report_requires_remote_pit_forwarding_cases",
        "ok": True,
        "returncode": 0,
        "status": "ok",
        "summary": {
            "failed_count": failed_count,
            "passed": failed_count == 0,
            "remote_pit_case_count": remote_pit_case_count,
            "remote_pit_required": remote_pit_required,
        },
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
                    broad_e2e_section_result(),
                    mixed_cluster_coverage_result(),
                    mixed_cluster_remote_pit_result(),
                    pit_e2e_coverage_result(),
                    rest_api_coverage_result(),
                    search_required_parity_result(),
                    search_compat_parity_result(),
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
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
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
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            transport_release_parity_result()
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results rest-api-coverage-current is missing",
            result["errors"],
        )

    def test_rejects_current_evidence_without_pit_e2e_coverage_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results PIT E2E coverage result is missing",
            result["errors"],
        )

    def test_rejects_current_evidence_without_search_required_parity_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            search_compat_parity_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results required search semantic/vector E2E result is missing",
            result["errors"],
        )

    def test_rejects_search_compat_with_low_semantic_suite_count(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(semantic_suite_count=4),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results search compat/strict E2E semantic parity suite count is below 5",
            result["errors"],
        )

    def test_rejects_current_evidence_without_broad_e2e_section_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results broad E2E section result is missing",
            result["errors"],
        )

    def test_rejects_broad_e2e_section_missing_required_section(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(required_sections=["semantic_parity"]),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results broad E2E required sections mismatch",
            result["errors"],
        )

    def test_rejects_broad_e2e_section_without_positive_suite_count(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(suite_counts={"route_parity": 0}),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results broad E2E route_parity suite count is not positive",
            result["errors"],
        )

    def test_rejects_pit_e2e_coverage_without_compared_required_cases(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(required_count=17, compared_count=16),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results PIT compared case count does not equal required case count",
            result["errors"],
        )

    def test_rejects_pit_e2e_coverage_with_non_passed_case_count(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(non_passed_count=1),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results PIT non-passed case count is not zero",
            result["errors"],
        )

    def test_rejects_pit_e2e_coverage_with_low_suite_or_case_count(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(suite_count=2, pit_case_count=16),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results PIT suite count is below 3",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results PIT case count is below required case count",
            result["errors"],
        )

    def test_rejects_rest_api_coverage_without_steelsearch_only_summary(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
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
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
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
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
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
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
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
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
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
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
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
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(include_claim_boundary=False),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results transport execution claim boundary is missing",
            result["errors"],
        )

    def test_rejects_current_evidence_without_mixed_cluster_coverage_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results mixed-cluster coverage result is missing",
            result["errors"],
        )

    def test_rejects_current_evidence_without_mixed_cluster_remote_pit_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results mixed-cluster remote PIT result is missing",
            result["errors"],
        )

    def test_rejects_mixed_cluster_without_both_shard_movement_directions(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(opensearch_to_steelsearch_passed=False),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results mixed-cluster opensearch_to_steelsearch_passed is not true",
            result["errors"],
        )

    def test_rejects_mixed_cluster_missing_required_shard_movement_phase(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(missing_required_phase_count=1),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results mixed-cluster missing required shard movement phase count is not zero",
            result["errors"],
        )

    def test_rejects_mixed_cluster_without_remote_pit_cases(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(remote_pit_case_count=0),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results mixed-cluster remote PIT case count is not positive",
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
