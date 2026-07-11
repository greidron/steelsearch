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
RELEASE_READINESS_TOOLING_COMMAND_NAMES = (
    "tools/test_replacement_gate_scripts.py",
    "tools/check-e2e-doc-current-counts.py",
    "tools/check-source-compatibility-drift.sh",
)


def non_native_inventory_result(
    *,
    missing_category_count: int = 0,
    missing_family_count: int = 0,
    missing_probe_count: int = 0,
    family_count: int = 20,
    evidenced_family_count: int = 20,
    probe_count: int = 12,
    matched_probe_count: int = 12,
    required_categories: list[str] | None = None,
    covered_categories: list[str] | None = None,
):
    required = required_categories or [
        "source-backed query",
        "materialization",
        "vector-hybrid",
        "mixed-cluster",
        "runtime",
        "security",
    ]
    covered = covered_categories or [
        "materialization",
        "mixed-cluster",
        "runtime",
        "security",
        "source-backed execution",
        "source-backed query",
        "vector-hybrid",
    ]
    return {
        "group": "non-native-inventory",
        "name": "non_native_path_inventory_has_no_missing_probe_or_family",
        "ok": True,
        "returncode": 0,
        "status": "ok",
        "summary": {
            "covered_categories": covered,
            "evidenced_family_count": evidenced_family_count,
            "family_count": family_count,
            "matched_probe_count": matched_probe_count,
            "missing_categories": [],
            "missing_category_count": missing_category_count,
            "missing_family_count": missing_family_count,
            "missing_probe_count": missing_probe_count,
            "passed": (
                missing_category_count == 0
                and missing_family_count == 0
                and missing_probe_count == 0
            ),
            "probe_count": probe_count,
            "required_categories": required,
        },
    }


def materialization_priority_result(
    *,
    passed: bool = True,
    ranked_operation_count: int = 0,
    priority_rows: int = 0,
    observed_operation_count: int = 1,
    successful_operation_count: int = 1,
    counter_observed_operation_count: int = 1,
):
    return {
        "group": "materialization-priority-current",
        "name": "targeted_materialization_priority_report_has_zero_ranked_operations",
        "ok": passed,
        "returncode": 0 if passed else 1,
        "status": "ok" if passed else "failed",
        "summary": {
            "allow_empty": True,
            "counter_observed_operation_count": counter_observed_operation_count,
            "observed_operation_count": observed_operation_count,
            "passed": passed,
            "priority_rows": priority_rows,
            "ranked_operation_count": ranked_operation_count,
            "successful_operation_count": successful_operation_count,
            "top_family": None,
            "top_operation": None,
        },
    }


def production_security_result(
    *,
    passed: bool = True,
    batch: str = "production-security",
    test_count: int = 34,
    failed_count: int = 0,
):
    return {
        "group": "production-security-current",
        "name": "production_security_batch_has_no_authn_authz_tls_or_fail_closed_regressions",
        "ok": passed,
        "returncode": 0 if passed else 1,
        "status": "ok" if passed else "failed",
        "summary": {
            "batch": batch,
            "failed_count": failed_count,
            "passed": passed,
            "test_count": test_count,
        },
    }


def startup_bootstrap_result(
    *,
    passed: bool = True,
    preflight_test_count: int = 35,
    preflight_failed_count: int = 0,
    preflight_zero_test_count: int = 0,
    readiness_test_count: int = 3,
    readiness_failed_count: int = 0,
    readiness_zero_test_count: int = 0,
):
    return {
        "group": "startup-bootstrap-current",
        "name": (
            "startup_preflight_and_readiness_batches_have_no_bootstrap_or_readiness_regressions"
        ),
        "ok": passed,
        "returncode": 0 if passed else 1,
        "status": "ok" if passed else "failed",
        "summary": {
            "passed": passed,
            "batches": {
                "startup-preflight": {
                    "failed_count": preflight_failed_count,
                    "test_count": preflight_test_count,
                    "zero_test_count": preflight_zero_test_count,
                },
                "startup-readiness": {
                    "failed_count": readiness_failed_count,
                    "test_count": readiness_test_count,
                    "zero_test_count": readiness_zero_test_count,
                },
            },
        },
    }


def release_evidence_inventory_result(
    *,
    passed: bool = True,
    batch: str = "release-evidence-inventory-current",
    test_count: int = 3,
    failed_count: int = 0,
    zero_test_count: int = 0,
    promotion_checks: int = 25,
    promotion_failed: int = 0,
    inventory_complete: bool = True,
    inventory_release_record_ready_item_count: int = 8,
    inventory_release_record_missing_items: list[str] | None = None,
    readiness_ready_items: int = 5,
    readiness_required_items: int = 5,
    readiness_error_count: int = 0,
):
    return {
        "group": "release-evidence-inventory-current",
        "name": "release_evidence_inventory_current_batch_has_complete_startup_and_readiness_artifacts",
        "ok": passed,
        "returncode": 0 if passed else 1,
        "status": "ok" if passed else "failed",
        "summary": {
            "batch": batch,
            "failed_count": failed_count,
            "inventory_complete": inventory_complete,
            "inventory_release_record_missing_items": (
                inventory_release_record_missing_items
                if inventory_release_record_missing_items is not None
                else []
            ),
            "inventory_release_record_ready_item_count": inventory_release_record_ready_item_count,
            "passed": passed,
            "promotion_checks": promotion_checks,
            "promotion_failed": promotion_failed,
            "readiness_error_count": readiness_error_count,
            "readiness_ready_items": readiness_ready_items,
            "readiness_required_items": readiness_required_items,
            "test_count": test_count,
            "zero_test_count": zero_test_count,
        },
    }


def release_readiness_tooling_result(
    *,
    passed: bool = True,
    commands: int = 3,
    command_names: list[str] | None = None,
):
    return {
        "group": "release-readiness-tooling",
        "name": "release_readiness_writer_and_manifest_checker_contract",
        "ok": passed,
        "returncode": 0 if passed else 1,
        "status": "ok" if passed else "failed",
        "summary": {
            "command_names": (
                command_names
                if command_names is not None
                else list(RELEASE_READINESS_TOOLING_COMMAND_NAMES)
            ),
            "commands": commands,
            "passed": passed,
        },
    }


RUNTIME_CONTROL_BATCH_COUNTS = {
    "runtime-tasks": 28,
    "runtime-queue": 6,
    "runtime-backpressure": 28,
    "runtime-fairness": 13,
    "runtime-throttle": 15,
    "runtime-task-metadata": 4,
    "runtime-task-headers": 2,
    "runtime-task-children": 10,
    "runtime-lifecycle": 5,
    "module-registration": 13,
}


def runtime_controls_result(
    *,
    passed: bool = True,
    failed_batches: list[str] | None = None,
    overrides: dict[str, dict] | None = None,
):
    batches = {
        batch: {
            "failed_cases": [],
            "failed_count": 0,
            "returncode": 0,
            "test_count": test_count,
            "zero_test_count": 0,
        }
        for batch, test_count in RUNTIME_CONTROL_BATCH_COUNTS.items()
    }
    for batch, patch in (overrides or {}).items():
        batches[batch] = {**batches[batch], **patch}
    return {
        "group": "runtime-controls-current",
        "name": "runtime_control_batches_have_no_queue_backpressure_fairness_or_lifecycle_regressions",
        "ok": passed,
        "returncode": 0 if passed else 1,
        "status": "ok" if passed else "failed",
        "summary": {
            "batches": batches,
            "failed_batches": failed_batches if failed_batches is not None else [],
            "passed": passed,
        },
    }


def runtime_peer_backpressure_gate(
    *,
    passed: bool = True,
    batch: str = "runtime-peer-backpressure-current",
    test_count: int = 1,
    failed_count: int = 0,
    zero_test_count: int = 0,
    profile: str = "mixed-java-rust-query-phase",
    steelsearch_rejected: int = 1,
    steelsearch_completed: int = 1,
    opensearch_rejected: int = 1,
    opensearch_completed: int = 1,
    opensearch_http_429_count: int = 1,
):
    return {
        "name": "runtime-peer-backpressure-current",
        "passed": passed,
        "returncode": 0 if passed else 1,
        "summary": {
            "batch": batch,
            "failed_count": failed_count,
            "passed_count": 1 if passed else 0,
            "test_count": test_count,
            "zero_test_count": zero_test_count,
        },
        "groups": {
            "runtime-fairness-peer-backpressure-current": {
                "ok": passed,
                "returncode": 0 if passed else 1,
                "status": "ok" if passed else "failed",
            }
        },
        "results": [
            {
                "group": "runtime-fairness-peer-backpressure-current",
                "name": "runtime_peer_backpressure_current_report_preserves_profile_and_counters",
                "ok": passed,
                "returncode": 0 if passed else 1,
                "status": "ok" if passed else "failed",
                "summary": {
                    "opensearch_completed": opensearch_completed,
                    "opensearch_http_429_count": opensearch_http_429_count,
                    "opensearch_rejected": opensearch_rejected,
                    "passed": passed,
                    "profile": profile,
                    "steelsearch_completed": steelsearch_completed,
                    "steelsearch_rejected": steelsearch_rejected,
                },
            }
        ],
    }


def transport_release_parity_result(
    *,
    complete: bool = True,
    missing_count: int = 0,
    matched_count: int = 174,
    partial_count: int = 0,
    planned_count: int = 0,
    stubbed_count: int = 0,
    out_of_scope_count: int = 0,
    include_scope_counts: bool = True,
    include_claim_boundary: bool = True,
):
    summary = {
        "release_parity_evidence_complete": complete,
        "transport_action_count": matched_count,
        "implemented_action_count": matched_count,
        "inventory_action_count": matched_count,
        "release_parity_action_count": matched_count,
        "release_parity_source_missing_action_count": missing_count,
        "release_parity_source_matched_action_count": matched_count,
        "accepted_evidence_action_count": matched_count,
        "accepted_evidence_inventory_matched_action_count": matched_count,
        "accepted_evidence_inventory_missing_action_count": 0,
        "accepted_evidence_inventory_extra_action_count": 0,
        "source_implemented_inventory_matched_action_count": matched_count,
        "source_implemented_inventory_missing_action_count": 0,
        "source_implemented_evidence_missing_action_count": 0,
        "release_evidence_inventory_matched_action_count": matched_count,
        "release_evidence_inventory_missing_action_count": 0,
        "release_evidence_inventory_extra_action_count": 0,
        "release_accepted_evidence_drift_error_count": 0,
        "partial_action_count": partial_count,
        "planned_action_count": planned_count,
        "stubbed_action_count": stubbed_count,
        "out_of_scope_action_count": out_of_scope_count,
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
    source_route_count: int = 389,
    ratio: float = 1.0,
    include_summary: bool = True,
    include_required_breakdown: bool = True,
    source_status_counts: dict[str, int] | None = None,
):
    summary = {
        "live_required_matched_source_route_count": matched_count,
        "live_required_matched_source_route_ratio": ratio,
        "in_scope_source_route_count": in_scope_count,
        "source_route_count": source_route_count,
        "source_status_counts": (
            source_status_counts
            if source_status_counts is not None
            else {"implemented": 378, "out-of-scope": 11}
        ),
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
            **e2e_clean_classification_summary(),
        },
    }


def e2e_clean_classification_summary():
    return {
        "case_classification": {
            "canonical_equal": 1,
            "failed": 0,
            "known_gap_or_skipped": 0,
            "missing": 0,
            "semantic_equal": 0,
            "steelsearch_fail_closed": 0,
            "steelsearch_only": 0,
            "strict_equal": 0,
        },
        "effective_case_classification": {
            "canonical_equal": 1,
            "failed": 0,
            "known_gap_or_skipped": 0,
            "missing": 0,
            "semantic_equal": 0,
            "steelsearch_fail_closed": 0,
            "steelsearch_only": 0,
            "strict_equal": 0,
        },
        "skipped_case_resolution": {
            "resolved_by_other_suite_count": 0,
            "total_count": 0,
            "unresolved_count": 0,
        },
    }


def broad_e2e_section_result(
    *,
    required_sections: list[str] | None = None,
    suite_counts: dict[str, int] | None = None,
    report_path_counts: dict[str, int] | None = None,
    required_opensearch_suites: list[str] | None = None,
    required_opensearch_missing_suites: list[str] | None = None,
):
    sections = required_sections or [
        "route_parity",
        "semantic_parity",
        "durability_parity",
        "security_parity",
        "distributed_parity",
    ]
    counts = suite_counts or {
        "distributed_parity": 1,
        "durability_parity": 2,
        "route_parity": 14,
        "security_parity": 1,
        "semantic_parity": 15,
    }
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
            "required_opensearch_suites": required_opensearch_suites
            if required_opensearch_suites is not None
            else ["security-authz"],
            "required_opensearch_suite_count": len(
                required_opensearch_suites
                if required_opensearch_suites is not None
                else ["security-authz"]
            ),
            "required_opensearch_missing_suites": required_opensearch_missing_suites
            if required_opensearch_missing_suites is not None
            else [],
            **e2e_clean_classification_summary(),
        },
    }


def mixed_cluster_coverage_result(
    *,
    opensearch_to_steelsearch_passed: bool = True,
    steelsearch_to_opensearch_passed: bool = True,
    phase_c_report_count: int = 13,
    failure_node_loss_report_count: int = 3,
    shard_movement_phase_count: int = 13,
    shard_movement_required_phase_count: int = 7,
    shard_movement_required_interruption_phase_count: int = 6,
    missing_required_phase_count: int = 0,
    phase_assertion_error_count: int = 0,
    include_claim_boundary: bool = True,
):
    summary = {
        "checkpoint_drift_ok": True,
        "checkpoint_monotonicity_ok": True,
        "failure_node_loss_passed_report_count": failure_node_loss_report_count,
        "failure_node_loss_report_count": failure_node_loss_report_count,
        "opensearch_to_steelsearch_passed": opensearch_to_steelsearch_passed,
        "passed": True,
        "phase_c_fresh_report_count": phase_c_report_count,
        "phase_c_passed_report_count": phase_c_report_count,
        "phase_c_report_count": phase_c_report_count,
        "publication_executed_test_count": 6,
        "publication_missing_required_executed_test_count": 0,
        "publication_missing_required_stage_count": 0,
        "publication_passed_report_count": 6,
        "publication_report_count": 6,
        "publication_required_executed_test_count": 6,
        "publication_required_stage_count": 17,
        "publication_stage_count": 17,
        "retention_lease_metadata_ok": True,
        "shard_movement_fresh": True,
        "shard_movement_missing_required_phase_count": missing_required_phase_count,
        "shard_movement_passed": True,
        "shard_movement_phase_assertion_error_count": phase_assertion_error_count,
        "shard_movement_phase_count": shard_movement_phase_count,
        "shard_movement_required_interruption_phase_count": (
            shard_movement_required_interruption_phase_count
        ),
        "shard_movement_required_phase_count": shard_movement_required_phase_count,
        "steelsearch_to_opensearch_passed": steelsearch_to_opensearch_passed,
        "transport_admin_fresh": True,
        "transport_admin_passed": True,
        "transport_admin_publication_transcript_count": 2,
        "transport_admin_publication_validation_event_count": 12,
        "transport_admin_remote_pit_case_count": 5,
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
    publication_validation_events_required: bool = True,
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
            "publication_validation_events_required": publication_validation_events_required,
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
                    non_native_inventory_result(),
                    broad_e2e_section_result(),
                    mixed_cluster_coverage_result(),
                    mixed_cluster_remote_pit_result(),
                    pit_e2e_coverage_result(),
                    rest_api_coverage_result(),
                    search_required_parity_result(),
                    search_compat_parity_result(),
                    materialization_priority_result(),
                    production_security_result(),
                    startup_bootstrap_result(),
                    runtime_controls_result(),
                    release_evidence_inventory_result(),
                    release_readiness_tooling_result(),
                    transport_release_parity_result(),
                ],
            },
            "runtime_peer_backpressure_current": runtime_peer_backpressure_gate(),
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


def mark_final_cutover_complete(report):
    startup = [
        "benchmark_coverage",
        "load_test_coverage",
        "chaos_test_coverage",
        "packaging_verified",
        "rolling_upgrade_coverage",
    ]
    readiness = [*startup, "load_comparison"]
    release_record = [*readiness, "pit_e2e_coverage", "promotion_gate_suite"]
    report["summary"]["final_cutover_ready"] = True
    report["summary"]["final_cutover_required"] = True
    report["summary"]["status"] = "ready"
    report["gates"]["final_cutover"]["passed"] = True
    report["gates"]["final_cutover"]["returncode"] = 0
    report["gates"]["final_cutover"]["errors"] = []
    report["gates"]["final_cutover"]["summary"] = {
        "checked_items": len(startup),
        "ready_items": len(startup),
        "required_items": len(startup),
    }
    report["gates"]["final_cutover"]["missing_items"] = []
    report["gates"]["final_cutover"]["required_item_inputs"] = {}
    report["gates"]["final_cutover"]["readiness_attachment_missing_items"] = []
    report["gates"]["final_cutover"]["readiness_attachment_errors"] = []
    report["gates"]["final_cutover"]["release_record_missing_items"] = []
    report["gates"]["final_cutover"]["evidence_inventory"] = {
        "returncode": 0,
        "summary": {
            "complete": True,
            "startup_item_count": len(startup),
            "startup_ready_item_count": len(startup),
            "startup_missing_items": [],
            "startup_ready_items": startup,
            "readiness_attachment_item_count": len(readiness),
            "readiness_attachment_ready_item_count": len(readiness),
            "readiness_attachment_missing_items": [],
            "readiness_attachment_ready_items": readiness,
            "release_record_item_count": len(release_record),
            "release_record_ready_item_count": len(release_record),
            "release_record_missing_items": [],
            "release_record_ready_items": release_record,
        },
    }
    return report


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

    def test_rejects_runtime_peer_backpressure_without_result_summary(self):
        report = valid_report()
        report["gates"]["runtime_peer_backpressure_current"] = {
            "passed": True,
            "summary": {
                "batch": "runtime-peer-backpressure-current",
                "failed_count": 0,
                "test_count": 1,
                "zero_test_count": 0,
            },
            "results": [],
        }

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.runtime_peer_backpressure_current result is missing",
            result["errors"],
        )

    def test_rejects_runtime_peer_backpressure_with_failed_or_missing_counters(self):
        report = valid_report()
        report["gates"]["runtime_peer_backpressure_current"] = runtime_peer_backpressure_gate(
            passed=False,
            test_count=0,
            failed_count=1,
            zero_test_count=1,
            profile="wrong-profile",
            steelsearch_rejected=0,
            steelsearch_completed=0,
            opensearch_rejected=0,
            opensearch_completed=0,
            opensearch_http_429_count=0,
        )

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn("gates.runtime_peer_backpressure_current.passed is not true", result["errors"])
        self.assertIn(
            "gates.runtime_peer_backpressure_current.summary.test_count is not 1",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current.summary.failed_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current.summary.zero_test_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current result did not pass",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current profile mismatch",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current steelsearch_rejected is not positive",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current opensearch_http_429_count is not positive",
            result["errors"],
        )

    def test_rejects_current_evidence_without_non_native_inventory_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            result
            for result in report["gates"]["current_evidence"]["results"]
            if result["group"] != "non-native-inventory"
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results non-native-inventory is missing",
            result["errors"],
        )

    def test_rejects_non_native_inventory_with_missing_family_or_probe(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            non_native_inventory_result(
                missing_family_count=1,
                missing_probe_count=1,
                evidenced_family_count=19,
                matched_probe_count=11,
            ),
            broad_e2e_section_result(),
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
            "gates.current_evidence.results non-native inventory missing_family_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results non-native inventory missing_probe_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results non-native inventory evidenced family count mismatch",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results non-native inventory matched probe count mismatch",
            result["errors"],
        )

    def test_rejects_non_native_inventory_below_current_baseline_counts(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            non_native_inventory_result(
                family_count=19,
                evidenced_family_count=19,
                probe_count=11,
                matched_probe_count=11,
            ),
            broad_e2e_section_result(),
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
            "gates.current_evidence.results non-native inventory family count is not 20",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results non-native inventory probe count is not 12",
            result["errors"],
        )

    def test_rejects_non_native_inventory_missing_required_category_coverage(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            non_native_inventory_result(covered_categories=["runtime"]),
            broad_e2e_section_result(),
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
            "gates.current_evidence.results non-native inventory covered categories miss required categories",
            result["errors"],
        )

    def test_rejects_current_evidence_without_materialization_priority_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            result
            for result in report["gates"]["current_evidence"]["results"]
            if result["group"] != "materialization-priority-current"
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results materialization priority result is missing",
            result["errors"],
        )

    def test_rejects_materialization_priority_with_ranked_operations(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            non_native_inventory_result(),
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(),
            materialization_priority_result(ranked_operation_count=1, priority_rows=1),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results materialization priority ranked operation count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results materialization priority row count is not zero",
            result["errors"],
        )

    def test_rejects_materialization_priority_without_observed_operations(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            non_native_inventory_result(),
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(),
            materialization_priority_result(
                observed_operation_count=0,
                successful_operation_count=0,
                counter_observed_operation_count=0,
            ),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results materialization priority observed_operation_count is not positive",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results materialization priority successful_operation_count is not positive",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results materialization priority counter_observed_operation_count is not positive",
            result["errors"],
        )

    def test_rejects_materialization_priority_below_current_observed_baseline(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            non_native_inventory_result(),
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(),
            materialization_priority_result(
                observed_operation_count=2,
                successful_operation_count=1,
                counter_observed_operation_count=1,
            ),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results materialization priority observed_operation_count is not 1",
            result["errors"],
        )

    def test_rejects_current_evidence_without_production_security_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            result
            for result in report["gates"]["current_evidence"]["results"]
            if result["group"] != "production-security-current"
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results production security result is missing",
            result["errors"],
        )

    def test_rejects_production_security_with_failed_or_low_test_count(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            production_security_result(passed=False, test_count=33, failed_count=1)
            if result["group"] == "production-security-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results production security did not pass",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results production security test count is not 34",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results production security failed count is not zero",
            result["errors"],
        )

    def test_rejects_current_evidence_without_startup_bootstrap_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            result
            for result in report["gates"]["current_evidence"]["results"]
            if result["group"] != "startup-bootstrap-current"
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results startup bootstrap result is missing",
            result["errors"],
        )

    def test_rejects_startup_bootstrap_with_preflight_regressions(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            startup_bootstrap_result(
                passed=False,
                preflight_test_count=34,
                preflight_failed_count=1,
                preflight_zero_test_count=1,
            )
            if result["group"] == "startup-bootstrap-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results startup bootstrap did not pass",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-preflight test count is not 35",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-preflight failed count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-preflight zero-test count is not zero",
            result["errors"],
        )

    def test_rejects_startup_bootstrap_with_readiness_regressions(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            startup_bootstrap_result(
                passed=False,
                readiness_test_count=2,
                readiness_failed_count=1,
                readiness_zero_test_count=1,
            )
            if result["group"] == "startup-bootstrap-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-readiness test count is not 3",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-readiness failed count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-readiness zero-test count is not zero",
            result["errors"],
        )

    def test_rejects_current_evidence_without_runtime_controls_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            result
            for result in report["gates"]["current_evidence"]["results"]
            if result["group"] != "runtime-controls-current"
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results runtime controls result is missing",
            result["errors"],
        )

    def test_rejects_runtime_controls_with_failed_batch_summary(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            runtime_controls_result(
                passed=False,
                failed_batches=["runtime-queue"],
                overrides={
                    "runtime-queue": {
                        "failed_cases": ["queue_regression"],
                        "failed_count": 1,
                        "returncode": 1,
                        "test_count": 5,
                        "zero_test_count": 1,
                    }
                },
            )
            if result["group"] == "runtime-controls-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results runtime controls did not pass",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results runtime controls failed_batches is not empty",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results runtime controls runtime-queue returncode is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results runtime controls runtime-queue test count is not 6",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results runtime controls runtime-queue failed count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results runtime controls runtime-queue zero-test count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results runtime controls runtime-queue failed_cases is not empty",
            result["errors"],
        )

    def test_rejects_runtime_controls_below_current_backpressure_baseline(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            runtime_controls_result(
                overrides={
                    "runtime-backpressure": {
                        "test_count": 27,
                    }
                },
            )
            if result["group"] == "runtime-controls-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results runtime controls runtime-backpressure test count is not 28",
            result["errors"],
        )

    def test_runtime_control_fixture_counts_match_checker_baselines(self):
        self.assertEqual(RUNTIME_CONTROL_BATCH_COUNTS, self.checker.RUNTIME_CONTROL_BATCH_COUNTS)

    def test_rejects_runtime_controls_below_each_current_batch_baseline(self):
        for batch, expected_count in self.checker.RUNTIME_CONTROL_BATCH_COUNTS.items():
            with self.subTest(batch=batch):
                report = valid_report()
                report["gates"]["current_evidence"]["results"] = [
                    runtime_controls_result(
                        overrides={
                            batch: {
                                "test_count": expected_count - 1,
                            }
                        },
                    )
                    if result["group"] == "runtime-controls-current"
                    else result
                    for result in report["gates"]["current_evidence"]["results"]
                ]

                result = self.checker.validate_report(report)

                self.assertEqual(result["status"], "failed")
                self.assertIn(
                    "gates.current_evidence.results runtime controls "
                    f"{batch} test count is not {expected_count}",
                    result["errors"],
                )

    def test_rejects_runtime_controls_with_missing_required_batch_summary(self):
        report = valid_report()
        runtime_result = runtime_controls_result()
        del runtime_result["summary"]["batches"]["module-registration"]
        report["gates"]["current_evidence"]["results"] = [
            runtime_result if result["group"] == "runtime-controls-current" else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results runtime controls module-registration summary is missing",
            result["errors"],
        )

    def test_rejects_current_evidence_without_release_evidence_inventory_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            result
            for result in report["gates"]["current_evidence"]["results"]
            if result["group"] != "release-evidence-inventory-current"
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results release evidence inventory result is missing",
            result["errors"],
        )

    def test_rejects_release_evidence_inventory_with_failed_or_low_test_count(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            release_evidence_inventory_result(
                passed=False,
                test_count=2,
                failed_count=1,
                zero_test_count=1,
                promotion_checks=22,
                promotion_failed=1,
                inventory_complete=False,
                inventory_release_record_ready_item_count=7,
                inventory_release_record_missing_items=["promotion_gate_suite"],
                readiness_ready_items=4,
                readiness_required_items=5,
                readiness_error_count=1,
            )
            if result["group"] == "release-evidence-inventory-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results release evidence inventory did not pass",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory test count is not 3",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory failed count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory zero-test count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory promotion check count is not 25",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory promotion failed count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory inventory is not complete",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory release record ready item count mismatch",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory release record missing items is not empty",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory readiness ready item count mismatch",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory readiness error count is not zero",
            result["errors"],
        )

    def test_rejects_current_evidence_without_release_readiness_tooling_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            result
            for result in report["gates"]["current_evidence"]["results"]
            if result["group"] != "release-readiness-tooling"
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results release readiness tooling result is missing",
            result["errors"],
        )

    def test_rejects_release_readiness_tooling_with_failed_or_missing_command(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            release_readiness_tooling_result(passed=False, commands=0)
            if result["group"] == "release-readiness-tooling"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results release readiness tooling did not pass",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release readiness tooling command count is not 3",
            result["errors"],
        )

    def test_rejects_release_readiness_tooling_with_wrong_command_names(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            release_readiness_tooling_result(
                command_names=[
                    "tools/test_replacement_gate_scripts.py",
                    "tools/check-e2e-doc-current-counts.py",
                    "tools/unrelated.py",
                ],
            )
            if result["group"] == "release-readiness-tooling"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results release readiness tooling command names "
            "do not match required current gate scripts",
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
            "gates.current_evidence.results search compat/strict E2E semantic parity suite count is not 5",
            result["errors"],
        )

    def test_rejects_search_compat_with_failed_or_missing_classification(self):
        report = valid_report()
        search = search_compat_parity_result()
        search["summary"]["case_classification"]["failed"] = 1
        search["summary"]["case_classification"]["missing"] = 1
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search,
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results search compat/strict E2E failed classification is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results search compat/strict E2E missing classification is not zero",
            result["errors"],
        )

    def test_rejects_search_required_with_unresolved_effective_skip(self):
        report = valid_report()
        search = search_required_parity_result()
        search["summary"]["effective_case_classification"]["known_gap_or_skipped"] = 1
        search["summary"]["skipped_case_resolution"]["unresolved_count"] = 1
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            search,
            search_compat_parity_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results required search semantic/vector E2E effective skipped classification is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results required search semantic/vector E2E unresolved skipped count is not zero",
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
            "gates.current_evidence.results broad E2E route_parity suite count is not 14",
            result["errors"],
        )

    def test_rejects_broad_e2e_section_without_security_authz_opensearch_evidence(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(
                required_opensearch_suites=["security-authz"],
                required_opensearch_missing_suites=["security-authz"],
            ),
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
            "gates.current_evidence.results broad E2E required OpenSearch suite evidence is missing",
            result["errors"],
        )

    def test_rejects_broad_e2e_section_with_unresolved_skip(self):
        report = valid_report()
        broad = broad_e2e_section_result()
        broad["summary"]["effective_case_classification"]["known_gap_or_skipped"] = 1
        broad["summary"]["skipped_case_resolution"]["unresolved_count"] = 1
        report["gates"]["current_evidence"]["results"] = [
            broad,
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
            "gates.current_evidence.results broad E2E effective skipped classification is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results broad E2E unresolved skipped count is not zero",
            result["errors"],
        )

    def test_rejects_broad_e2e_section_with_skip_resolution_count_drift(self):
        report = valid_report()
        broad = broad_e2e_section_result()
        broad["summary"]["case_classification"]["known_gap_or_skipped"] = 3
        broad["summary"]["effective_case_classification"]["known_gap_or_skipped"] = 0
        broad["summary"]["skipped_case_resolution"] = {
            "resolved_by_other_suite_count": 2,
            "total_count": 3,
            "unresolved_count": 0,
        }
        report["gates"]["current_evidence"]["results"] = [
            broad,
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
            "gates.current_evidence.results broad E2E skipped resolution counts do not add up",
            result["errors"],
        )

    def test_rejects_broad_e2e_section_when_effective_skip_does_not_match_unresolved_count(self):
        report = valid_report()
        broad = broad_e2e_section_result()
        broad["summary"]["case_classification"]["known_gap_or_skipped"] = 3
        broad["summary"]["effective_case_classification"]["known_gap_or_skipped"] = 0
        broad["summary"]["skipped_case_resolution"] = {
            "resolved_by_other_suite_count": 2,
            "total_count": 3,
            "unresolved_count": 1,
        }
        report["gates"]["current_evidence"]["results"] = [
            broad,
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
            "gates.current_evidence.results broad E2E effective skipped classification does not match unresolved count",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results broad E2E unresolved skipped count is not zero",
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
            "gates.current_evidence.results PIT suite count is not 3",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results PIT case count is not 232",
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
            "gates.current_evidence.results REST live required matched source route count "
            "is not 378",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST live required matched source route ratio is not 1.0",
            result["errors"],
        )

    def test_rejects_rest_api_coverage_with_low_source_route_count(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(source_route_count=388),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST source route count is not 389",
            result["errors"],
        )

    def test_rejects_rest_api_coverage_with_non_closed_source_status(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(
                source_status_counts={
                    "implemented": 377,
                    "out-of-scope": 11,
                    "planned": 1,
                }
            ),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST source status counts contain "
            "non-closed statuses: planned=1",
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
        self.assertIn(
            "gates.current_evidence.results transport release parity matched action count is not 174",
            result["errors"],
        )

    def test_rejects_transport_release_parity_below_current_action_baseline(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(matched_count=173),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results transport release parity matched action count is not 174",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport transport_action_count is not 174",
            result["errors"],
        )

    def test_rejects_transport_release_parity_with_inventory_coverage_drift(self):
        report = valid_report()
        transport = transport_release_parity_result()
        transport["summary"]["accepted_evidence_inventory_matched_action_count"] = 173
        transport["summary"]["accepted_evidence_inventory_missing_action_count"] = 1
        transport["summary"]["source_implemented_evidence_missing_action_count"] = 1
        transport["summary"]["release_evidence_inventory_extra_action_count"] = 1
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
            "gates.current_evidence.results transport accepted_evidence_inventory_matched_action_count is not 174",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport accepted_evidence_inventory_missing_action_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport source_implemented_evidence_missing_action_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport release_evidence_inventory_extra_action_count is not zero",
            result["errors"],
        )

    def test_rejects_transport_release_parity_with_non_closed_action_statuses(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(planned_count=1, partial_count=1),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results transport planned_action_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport partial_action_count is not zero",
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

    def test_rejects_mixed_cluster_below_current_phase_baselines(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(
                phase_c_report_count=12,
                failure_node_loss_report_count=2,
                shard_movement_phase_count=12,
                shard_movement_required_phase_count=6,
                shard_movement_required_interruption_phase_count=5,
            ),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results mixed-cluster phase C report count is not 13",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster failure node-loss report count is not 3",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster shard movement phase count is not 13",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster required shard movement phase count is not 7",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster required interruption phase count is not 6",
            result["errors"],
        )

    def test_rejects_mixed_cluster_missing_publication_evidence_counts(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["publication_stage_count"] = 16
        coverage["summary"]["publication_missing_required_stage_count"] = 1
        coverage["summary"]["transport_admin_publication_validation_event_count"] = 6
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            coverage,
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results mixed-cluster publication_stage_count does not equal 17",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster publication_missing_required_stage_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster transport_admin_publication_validation_event_count does not equal 12",
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
            "gates.current_evidence.results mixed-cluster remote PIT case count does not equal current baseline",
            result["errors"],
        )

    def test_rejects_mixed_cluster_when_remote_pit_result_drifts_from_transport_admin_summary(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["transport_admin_remote_pit_case_count"] = 5
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            coverage,
            mixed_cluster_remote_pit_result(remote_pit_case_count=4),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results mixed-cluster remote PIT case count does not equal current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster remote PIT case count "
            "does not match transport admin summary",
            result["errors"],
        )

    def test_rejects_mixed_cluster_without_publication_validation_requirement(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(publication_validation_events_required=False),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results mixed-cluster publication validation events are not required",
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

    def test_require_final_cutover_accepts_complete_release_inventory_counts(self):
        report = mark_final_cutover_complete(valid_report())

        result = self.checker.validate_report(report, require_final_cutover=True)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["errors"], [])

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

    def test_rejects_passed_final_cutover_with_incomplete_inventory_counts(self):
        report = mark_final_cutover_complete(valid_report())
        summary = report["gates"]["final_cutover"]["evidence_inventory"]["summary"]
        summary["startup_ready_item_count"] = 4
        summary["readiness_attachment_ready_item_count"] = 5
        summary["release_record_ready_item_count"] = 7
        summary["release_record_ready_items"] = summary["release_record_ready_items"][:-1]

        result = self.checker.validate_report(report, require_final_cutover=True)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "final_cutover evidence inventory startup_ready_item_count does not equal 5",
            result["errors"],
        )
        self.assertIn(
            "final_cutover evidence inventory readiness_attachment_ready_item_count does not equal 6",
            result["errors"],
        )
        self.assertIn(
            "final_cutover evidence inventory release_record_ready_item_count does not equal 8",
            result["errors"],
        )
        self.assertIn(
            "final_cutover evidence inventory release_record_ready_items mismatch",
            result["errors"],
        )

    def test_rejects_passed_final_cutover_with_failed_release_readiness_summary(self):
        report = mark_final_cutover_complete(valid_report())
        final = report["gates"]["final_cutover"]
        final["returncode"] = 1
        final["errors"] = ["benchmark_coverage.passed is false"]
        final["readiness_attachment_errors"] = ["readiness report path is not configured"]
        final["required_item_inputs"] = {"benchmark_coverage": {"attach_argument": "--benchmark-report"}}
        final["summary"] = {
            "checked_items": 4,
            "ready_items": 4,
            "required_items": 5,
        }

        result = self.checker.validate_report(report, require_final_cutover=True)

        self.assertEqual(result["status"], "failed")
        self.assertIn("final_cutover passed but returncode is not zero", result["errors"])
        self.assertIn("final_cutover passed but errors is not empty", result["errors"])
        self.assertIn(
            "final_cutover passed but readiness_attachment_errors is not empty",
            result["errors"],
        )
        self.assertIn(
            "final_cutover passed but required_item_inputs is not empty",
            result["errors"],
        )
        self.assertIn(
            "final_cutover.summary.checked_items does not equal 5",
            result["errors"],
        )
        self.assertIn(
            "final_cutover.summary.ready_items does not equal 5",
            result["errors"],
        )

    def test_rejects_passed_final_cutover_with_failed_inventory_returncode(self):
        report = mark_final_cutover_complete(valid_report())
        report["gates"]["final_cutover"]["evidence_inventory"]["returncode"] = 1

        result = self.checker.validate_report(report, require_final_cutover=True)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "final_cutover passed but evidence inventory returncode is not zero",
            result["errors"],
        )


if __name__ == "__main__":
    unittest.main()
