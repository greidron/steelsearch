#!/usr/bin/env python3
"""Validate a native-closure status report artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


STARTUP_MANIFEST_ITEMS = (
    "benchmark_coverage",
    "load_test_coverage",
    "chaos_test_coverage",
    "packaging_verified",
    "rolling_upgrade_coverage",
)
READINESS_ATTACHMENT_ITEMS = (*STARTUP_MANIFEST_ITEMS, "load_comparison")
RELEASE_RECORD_ITEMS = (
    *READINESS_ATTACHMENT_ITEMS,
    "pit_e2e_coverage",
    "promotion_gate_suite",
)
PROMOTION_GATE_CHECK_COUNT = 26
RELEASE_EVIDENCE_MAX_AGE_SECONDS = 604800.0
RELEASE_READINESS_REPORT_PATH = "target/release-readiness/readiness-report.json"
RELEASE_READINESS_FILE_PATH = "target/release-readiness/release-readiness.json"
FINAL_CUTOVER_COMMAND_TAIL = (
    "tools/check-release-readiness-evidence.py",
    RELEASE_READINESS_FILE_PATH,
    "--require-passed",
)
FINAL_CUTOVER_MANIFEST_COMMAND_TEMPLATE = (
    "python3",
    "tools/attach-release-readiness-evidence.py",
    "--readiness-report",
    "<readiness-report.json>",
    "--benchmark-report",
    "<benchmark.jsonl>",
    "--benchmark-comparison-summary",
    "<benchmark-comparison-summary.json>",
    "--load-report",
    "<load.json>",
    "--load-comparison-report",
    "<load-comparison.json>",
    "--chaos-report",
    "<chaos.json>",
    "--packaging-report",
    "<packaging.json>",
    "--rolling-upgrade-report",
    "<rolling-upgrade.json>",
    "--release-readiness-file",
    "<release-readiness.json>",
)
FINAL_CUTOVER_INVENTORY_COMMAND_TAIL = (
    "tools/report-release-evidence-inventory.py",
    "--root",
)
FINAL_CUTOVER_ATTACH_TEMPLATE_FLAGS = (
    "--readiness-report",
    "--benchmark-report",
    "--benchmark-comparison-summary",
    "--load-report",
    "--load-comparison-report",
    "--chaos-report",
    "--packaging-report",
    "--rolling-upgrade-report",
    "--release-readiness-file",
)
CURRENT_EVIDENCE_COMMAND = (
    "/usr/bin/python3",
    "tools/run-native-closure-validation.py",
    "--batch",
    "current-evidence-gate",
    "--format",
    "json",
)
RUNTIME_PEER_BACKPRESSURE_COMMAND = (
    "/usr/bin/python3",
    "tools/run-native-closure-validation.py",
    "--batch",
    "runtime-peer-backpressure-current",
    "--format",
    "json",
)
RUNTIME_PEER_BACKPRESSURE_GROUP = "runtime-fairness-peer-backpressure-current"
MIXED_PUBLICATION_REPORT_COUNT = 6
MIXED_PUBLICATION_EXECUTED_TEST_COUNT = 6
MIXED_PUBLICATION_STAGE_COUNT = 17
MIXED_TRANSPORT_ADMIN_REMOTE_PIT_CASE_COUNT = 5
MIXED_TRANSPORT_ADMIN_PUBLICATION_TRANSCRIPT_COUNT = 2
MIXED_TRANSPORT_ADMIN_PUBLICATION_VALIDATION_EVENT_COUNT = 12
MIXED_PHASE_C_REPORT_COUNT = 13
MIXED_PHASE_C_REPORT_NAMES = (
    "allocation",
    "bounded_recovery_probe",
    "failure",
    "failure_java_node_loss",
    "failure_steelsearch_node_loss_publication",
    "failure_steelsearch_node_loss_recovery",
    "join",
    "join_reject",
    "live_join_probe",
    "phase_c_summary",
    "publication",
    "recovery",
    "write_replication",
)
MIXED_PHASE_C_REQUIRED_SUMMARY_REPORTS = (
    "mixed-cluster-allocation-report.json",
    "mixed-cluster-failure-report.json",
    "mixed-cluster-join-report.json",
    "mixed-cluster-publication-report.json",
    "mixed-cluster-recovery-report.json",
    "mixed-cluster-write-replication-report.json",
)
MIXED_PHASE_C_REQUIRED_CHECK_NAMES = {
    "allocation": ("allocation_reject_passed", "routing_convergence_probe_passed"),
    "bounded_recovery_probe": ("wire_round_trip_passed",),
    "failure": (
        "failure_ledger_passed",
        "failure_topology_probe_passed",
        "pit_multi_daemon_lifecycle_passed",
        "pit_restart_lifecycle_passed",
        "pit_transport_restart_lifecycle_passed",
    ),
    "join": ("join_reject_passed", "live_join_probe_passed"),
    "live_join_probe": (
        "advertised_roles_match_fixture",
        "cluster_uuid_present",
        "handshake_cluster_name_matches_state",
        "node_name_present",
        "remote_transport_version_matches_fixture",
        "required_attributes_present",
        "response_header_matches_min_compat",
        "single_local_node_visible",
        "transport_address_present",
        "transport_payload_matches_fixture",
    ),
    "publication": (
        "publication-diff-ack-report.json",
        "publication-full-state-report.json",
        "publication-reachable-catch-up-report.json",
        "publication-reject-report.json",
        "publication-repeated-diff-monotonicity-report.json",
        "publication-scheduled-catch-up-report.json",
    ),
    "recovery": ("bounded_peer_recovery_probe_passed", "recovery_reject_passed"),
    "write_replication": (
        "write_replication_happy_path_passed",
        "write_replication_reject_passed",
    ),
}
MIXED_FAILURE_NODE_LOSS_REPORT_COUNT = 3
MIXED_FAILURE_NODE_LOSS_REPORT_NAMES = (
    "failure_java_node_loss",
    "failure_steelsearch_node_loss_publication",
    "failure_steelsearch_node_loss_recovery",
)
MIXED_SHARD_MOVEMENT_PHASE_COUNT = 13
MIXED_SHARD_MOVEMENT_REQUIRED_PHASE_COUNT = 7
MIXED_SHARD_MOVEMENT_REQUIRED_INTERRUPTION_PHASE_COUNT = 6
MIXED_SHARD_MOVEMENT_PHASE_NAMES = (
    "cluster_formed",
    "unsupported_allocation_explain",
    "initial_primary_on_java1",
    "interrupt_java_to_steelsearch_recovery",
    "resume_or_restart_java_to_steelsearch_recovery",
    "replica_on_rust",
    "finalize_java_to_steelsearch_recovery",
    "opensearch_to_steelsearch",
    "interrupt_steelsearch_to_opensearch_recovery",
    "resume_or_restart_steelsearch_to_opensearch_recovery",
    "java1_rejoined_as_replica",
    "finalize_steelsearch_to_opensearch_recovery",
    "steelsearch_to_opensearch",
)
MIXED_PUBLICATION_REQUIRED_EXECUTED_TESTS = (
    "periodic_liveness_catches_up_reachable_lagging_publication_follower_before_retry",
    "periodic_liveness_schedules_node_left_publication_retry_before_fencing_manager",
    "publication_diff_apply_acknowledges_only_after_successful_apply",
    "publication_full_state_receive_apply_replaces_local_cache",
    "publication_reject_integration_preserves_cache_and_withholds_ack",
    "repeated_publication_diff_apply_requires_monotonic_versions_before_ack",
)
MIXED_PUBLICATION_REPORT_NAMES = (
    "publication-diff-ack-report.json",
    "publication-full-state-report.json",
    "publication-reachable-catch-up-report.json",
    "publication-reject-report.json",
    "publication-repeated-diff-monotonicity-report.json",
    "publication-scheduled-catch-up-report.json",
)
MIXED_PUBLICATION_REQUIRED_STAGES = (
    "ack_withheld",
    "apply_ack",
    "apply_ack_after_success",
    "cache_preserved",
    "catch_up_scheduled_with_backoff",
    "diff_apply",
    "diff_decode",
    "full_state_decode",
    "lagging_follower_detected",
    "local_cache_replace",
    "monotonic_version_required",
    "node_left_retry_after_backoff",
    "reachable_catch_up_applied",
    "reject_detected",
    "repeated_diff_decode",
    "retry_suppressed",
    "stale_round_rejected",
)
MIXED_SHARD_MOVEMENT_REQUIRED_PHASES = (
    "cluster_formed",
    "initial_primary_on_java1",
    "java1_rejoined_as_replica",
    "opensearch_to_steelsearch",
    "replica_on_rust",
    "steelsearch_to_opensearch",
    "unsupported_allocation_explain",
)
MIXED_SHARD_MOVEMENT_REQUIRED_INTERRUPTION_PHASES = (
    "finalize_java_to_steelsearch_recovery",
    "finalize_steelsearch_to_opensearch_recovery",
    "interrupt_java_to_steelsearch_recovery",
    "interrupt_steelsearch_to_opensearch_recovery",
    "resume_or_restart_java_to_steelsearch_recovery",
    "resume_or_restart_steelsearch_to_opensearch_recovery",
)
MIXED_SHARD_MOVEMENT_REQUIRED_PHASE_FIELDS = {
    "cluster_formed": ("node_count",),
    "finalize_java_to_steelsearch_recovery": (
        "checkpoint_drift",
        "cluster_health",
        "placement",
        "recovery",
    ),
    "finalize_steelsearch_to_opensearch_recovery": (
        "checkpoint_drift",
        "cluster_health",
        "placement",
        "recovery",
    ),
    "initial_primary_on_java1": ("placement", "search_count", "shards"),
    "interrupt_java_to_steelsearch_recovery": (
        "checkpoint_drift",
        "placement",
        "recovery",
    ),
    "interrupt_steelsearch_to_opensearch_recovery": (
        "checkpoint_drift",
        "placement",
        "recovery",
    ),
    "java1_rejoined_as_replica": ("cluster_health", "placement"),
    "opensearch_to_steelsearch": ("passed", "placement", "search_count", "shards"),
    "replica_on_rust": ("cluster_health", "placement", "search_count", "shards"),
    "resume_or_restart_java_to_steelsearch_recovery": (
        "checkpoint_drift",
        "placement",
        "recovery",
    ),
    "resume_or_restart_steelsearch_to_opensearch_recovery": (
        "checkpoint_drift",
        "placement",
        "recovery",
    ),
    "steelsearch_to_opensearch": ("passed", "placement", "search_count", "shards"),
    "unsupported_allocation_explain": ("allocation_explain",),
}
MIXED_SHARD_MOVEMENT_REQUIRED_SUMMARY_FLAGS = (
    "checkpoint_drift_ok",
    "checkpoint_monotonicity_ok",
    "interruption_evidence_ok",
    "interruption_evidence_required",
    "opensearch_to_steelsearch_passed",
    "retention_lease_metadata_ok",
    "steelsearch_to_opensearch_passed",
    "transport_log_ok",
    "unsupported_allocation_explain_ok",
)
MIXED_TRANSPORT_ADMIN_PUBLICATION_VALIDATION_EVENTS = (
    "apply.action_frame.passed",
    "apply.connect.passed",
    "apply.publication_semantics.passed",
    "proposal.action_frame.passed",
    "proposal.connect.passed",
    "proposal.publication_semantics.passed",
)
MIXED_TRANSPORT_ADMIN_REMOTE_PIT_CASES = (
    "node_a_list_pits_after_node_b_close",
    "node_a_open_pit",
    "node_b_close_node_a_pit",
    "node_b_search_node_a_pit",
    "node_b_search_node_a_pit_after_close",
)
REST_LIVE_REQUIRED_MATCHED_SOURCE_ROUTE_COUNT = 378
REST_FIXTURE_ROUTE_COUNT = 3629
REST_LIVE_REQUIRED_FIXTURE_ROUTE_COUNT = 3489
REST_SOURCE_ROUTE_COUNT = 389
REST_SOURCE_STATUS_COUNTS = {
    "implemented": 378,
    "out-of-scope": 11,
}
REST_UNIFIED_REQUIRED_SUITE_CLASSIFICATION = {
    "canonical_equal": 2128,
    "failed": 0,
    "known_gap_or_skipped": 21,
    "missing": 0,
    "passed": 0,
    "semantic_equal": 3,
    "steelsearch_fail_closed": 0,
    "steelsearch_only": 0,
    "strict_equal": 937,
    "total_equal": 3068,
}
REST_UNIFIED_REQUIRED_SUITE_EFFECTIVE_CLASSIFICATION = {
    "canonical_equal": 2137,
    "failed": 0,
    "known_gap_or_skipped": 0,
    "missing": 0,
    "passed": 0,
    "semantic_equal": 3,
    "steelsearch_fail_closed": 0,
    "steelsearch_only": 0,
    "strict_equal": 937,
    "total_equal": 3077,
}
REST_UNIFIED_REQUIRED_SUITE_SKIP_RESOLUTION = {
    "resolved_by_other_suite_count": 21,
    "total_count": 21,
    "unresolved_count": 0,
}
REST_STEELSEARCH_ONLY_SUMMARY = {
    "breakdown_total": 0,
    "effective_delta": 0,
    "effective_total": 0,
    "effective_unexplained_delta": 0,
    "non_required_breakdown_total": 0,
    "raw_delta": 0,
    "raw_total": 0,
}
SEARCH_REQUIRED_SEMANTIC_SUITE_COUNT = 3
SEARCH_COMPAT_SEMANTIC_SUITE_COUNT = 5
SEARCH_REQUIRED_SEMANTIC_SUITE_NAMES = (
    "search-semantic",
    "vector-search",
    "vector-search-native-surface",
)
SEARCH_COMPAT_SEMANTIC_SUITE_NAMES = (
    "knn-plugin-surface",
    "ml-model-surface",
    "search-compat",
    "search-strict",
    "vector-search-native-surface",
)
E2E_CLASSIFICATION_BASELINES = {
    "required search semantic/vector": {
        "case_classification": {
            "canonical_equal": 108,
            "failed": 0,
            "known_gap_or_skipped": 0,
            "missing": 0,
            "semantic_equal": 0,
            "steelsearch_fail_closed": 0,
            "steelsearch_only": 0,
            "strict_equal": 17,
        },
        "effective_case_classification": {
            "canonical_equal": 108,
            "failed": 0,
            "known_gap_or_skipped": 0,
            "missing": 0,
            "semantic_equal": 0,
            "steelsearch_fail_closed": 0,
            "steelsearch_only": 0,
            "strict_equal": 17,
        },
        "skipped_case_resolution": {
            "resolved_by_other_suite_count": 0,
            "total_count": 0,
            "unresolved_count": 0,
        },
    },
    "search compat/strict": {
        "case_classification": {
            "canonical_equal": 1002,
            "failed": 0,
            "known_gap_or_skipped": 21,
            "missing": 0,
            "semantic_equal": 0,
            "steelsearch_fail_closed": 0,
            "steelsearch_only": 0,
            "strict_equal": 920,
        },
        "effective_case_classification": {
            "canonical_equal": 1002,
            "failed": 0,
            "known_gap_or_skipped": 0,
            "missing": 0,
            "semantic_equal": 0,
            "steelsearch_fail_closed": 0,
            "steelsearch_only": 0,
            "strict_equal": 920,
        },
        "skipped_case_resolution": {
            "resolved_by_other_suite_count": 21,
            "total_count": 21,
            "unresolved_count": 0,
        },
    },
    "broad": {
        "case_classification": {
            "canonical_equal": 2137,
            "failed": 0,
            "known_gap_or_skipped": 21,
            "missing": 0,
            "semantic_equal": 3,
            "steelsearch_fail_closed": 0,
            "steelsearch_only": 0,
            "strict_equal": 937,
        },
        "effective_case_classification": {
            "canonical_equal": 2137,
            "failed": 0,
            "known_gap_or_skipped": 0,
            "missing": 0,
            "semantic_equal": 3,
            "steelsearch_fail_closed": 0,
            "steelsearch_only": 0,
            "strict_equal": 937,
        },
        "skipped_case_resolution": {
            "resolved_by_other_suite_count": 21,
            "total_count": 21,
            "unresolved_count": 0,
        },
    },
}
PIT_REQUIRED_CASE_COUNT = 17
PIT_CASE_COUNT = 232
PIT_SUITE_COUNT = 3
MATERIALIZATION_PRIORITY_OBSERVED_OPERATION_COUNT = 1
PRODUCTION_SECURITY_TEST_COUNT = 34
PRODUCTION_SECURITY_GROUPS = {
    "production-security-audit": 1,
    "production-security-auth-subjects": 2,
    "production-security-authentication": 1,
    "production-security-authorization": 23,
    "production-security-fail-closed": 1,
    "production-security-http-tls": 1,
    "production-security-permission-evaluator": 1,
    "production-security-secret-redaction": 1,
    "production-security-service-account": 1,
    "production-security-tenant-isolation": 1,
    "production-security-transport-tls": 1,
}
STARTUP_PREFLIGHT_TEST_COUNT = 35
STARTUP_READINESS_TEST_COUNT = 3
STARTUP_PREFLIGHT_GROUPS = {
    "bind-preflight": 1,
    "config-parse-preflight": 3,
    "daemon-bind-preflight": 1,
    "daemon-data-path-preflight": 1,
    "data-path-preflight": 4,
    "identity-preflight": 1,
    "production-gate-preflight": 5,
    "role-preflight": 1,
    "security-bootstrap-preflight": 14,
    "security-bootstrap-redaction": 1,
    "startup-preflight-production-release-evidence": 3,
}
STARTUP_READINESS_GROUPS = {
    "startup-readiness-shared-blockers": 2,
    "startup-readiness-terminology": 1,
}
RELEASE_EVIDENCE_INVENTORY_TEST_COUNT = 3
RELEASE_EVIDENCE_INVENTORY_RESULT_NAMES = (
    "release_evidence_inventory_generates_promotion_gate_suite_artifact",
    "release_evidence_inventory_reports_current_candidate_artifacts",
    "release_evidence_inventory_writes_and_checks_final_cutover_manifest",
)
RELEASE_READINESS_TOOLING_COMMAND_COUNT = 3
RELEASE_READINESS_TOOLING_COMMAND_NAMES = (
    "tools/test_replacement_gate_scripts.py",
    "tools/check-e2e-doc-current-counts.py",
    "tools/check-source-compatibility-drift.sh",
)
BROAD_E2E_SECTION_SUITE_COUNTS = {
    "distributed_parity": 1,
    "durability_parity": 2,
    "route_parity": 14,
    "security_parity": 1,
    "semantic_parity": 15,
}
BROAD_E2E_SECTION_SUITE_NAMES = {
    "distributed_parity": (
        "multi-node-transport-admin",
    ),
    "durability_parity": (
        "alias-template-persistence",
        "snapshot-lifecycle",
    ),
    "route_parity": (
        "alias-read",
        "allocation-explain",
        "cluster-health",
        "cluster-state",
        "data-stream-rollover",
        "index-lifecycle",
        "mapping",
        "root-cluster-node",
        "root-cluster-node-cat-common",
        "settings",
        "stats",
        "tasks",
        "template",
        "tier-read-surface",
    ),
    "security_parity": (
        "security-authz",
    ),
    "semantic_parity": (
        "admin-ops-common",
        "bulk",
        "document-write-semantic",
        "knn-plugin-surface",
        "ml-model-surface",
        "refresh",
        "routing",
        "runtime-mappings-surface",
        "runtime-stateful-probe",
        "search-compat",
        "search-semantic",
        "search-strict",
        "single-doc-crud",
        "vector-search",
        "vector-search-native-surface",
    ),
}
TRANSPORT_RELEASE_PARITY_ACTION_COUNT = 174
TRANSPORT_ACCEPTED_EVIDENCE_SCOPE_COUNTS = {
    "bounded_local_subset": 170,
    "bounded_seed_peer_fanout_subset": 4,
}
CURRENT_EVIDENCE_GROUPS = (
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
    "source-compatibility-current",
)
SOURCE_COMPATIBILITY_MATRIX_ROW_COUNT = 768
SOURCE_COMPATIBILITY_CLOSED_ROW_COUNT = 768
NON_NATIVE_INVENTORY_FAMILY_COUNT = 20
NON_NATIVE_INVENTORY_PROBE_COUNT = 12
NON_NATIVE_REQUIRED_CATEGORIES = (
    "source-backed query",
    "materialization",
    "vector-hybrid",
    "mixed-cluster",
    "runtime",
    "security",
)
NON_NATIVE_COVERED_CATEGORIES = (
    "materialization",
    "mixed-cluster",
    "runtime",
    "security",
    "source-backed execution",
    "source-backed query",
    "vector-hybrid",
)
VALID_STATUSES = {
    "ready",
    "current-evidence-ready-final-cutover-pending",
    "final-cutover-missing",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--require-final-cutover", action="store_true")
    parser.add_argument("--require-clean-worktree", action="store_true")
    parser.add_argument("--require-current-head", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.report.read_text(encoding="utf-8"))
    result = validate_report(
        payload,
        require_final_cutover=args.require_final_cutover,
        require_clean_worktree=args.require_clean_worktree,
        expected_git_head=(current_git_head() if args.require_current_head else None),
    )
    print(json.dumps({"report": str(args.report), **result}, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


def validate_report(
    payload: dict[str, Any],
    *,
    require_final_cutover: bool = False,
    require_clean_worktree: bool = False,
    expected_git_head: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
    current = gate(gates, "current_evidence")
    peer = gate(gates, "runtime_peer_backpressure_current")
    final = gate(gates, "final_cutover")

    if not isinstance(metadata.get("generated_at_epoch_seconds"), int):
        errors.append("metadata.generated_at_epoch_seconds is missing or not an integer")
    if not isinstance(metadata.get("git_head"), str) or not metadata.get("git_head"):
        errors.append("metadata.git_head is missing or not a string")
    if expected_git_head is not None and metadata.get("git_head") != expected_git_head:
        errors.append(
            "metadata.git_head does not match current HEAD "
            f"({metadata.get('git_head')} != {expected_git_head})"
        )
    if not isinstance(metadata.get("git_clean"), bool):
        errors.append("metadata.git_clean is missing or not a boolean")
    if not isinstance(metadata.get("git_status_short"), str):
        errors.append("metadata.git_status_short is missing or not a string")
    if require_clean_worktree and metadata.get("git_clean") is not True:
        errors.append("metadata.git_clean is not true")
    if require_clean_worktree and metadata.get("git_status_short") != "":
        errors.append("metadata.git_status_short is not empty")

    if summary.get("current_evidence_ready") is not True:
        errors.append("summary.current_evidence_ready is not true")
    if summary.get("runtime_peer_backpressure_ready") is not True:
        errors.append("summary.runtime_peer_backpressure_ready is not true")
    if summary.get("status") not in VALID_STATUSES:
        errors.append(f"summary.status is invalid: {summary.get('status')}")
    if require_final_cutover and summary.get("final_cutover_ready") is not True:
        errors.append("summary.final_cutover_ready is not true")
    if bool(summary.get("final_cutover_required")) != require_final_cutover:
        errors.append("summary.final_cutover_required does not match checker mode")

    if current.get("passed") is not True:
        errors.append("gates.current_evidence.passed is not true")
    if tuple(current.get("command") or ()) != CURRENT_EVIDENCE_COMMAND:
        errors.append("gates.current_evidence.command does not match current baseline")
    current_required_groups = tuple(current.get("required_groups") or ())
    if current_required_groups != CURRENT_EVIDENCE_GROUPS:
        errors.append("gates.current_evidence.required_groups mismatch")
    current_summary = current.get("summary")
    result_count = len(current.get("results") or [])
    if not isinstance(current_summary, dict):
        errors.append("gates.current_evidence.summary is missing or not an object")
    else:
        if current_summary.get("batch") != "current-evidence-gate":
            errors.append("gates.current_evidence.summary batch mismatch")
        for field in ("test_count", "passed_count"):
            if current_summary.get(field) != result_count:
                errors.append(
                    f"gates.current_evidence.summary.{field} does not equal result count"
                )
        for field in ("failed_count", "zero_test_count"):
            if current_summary.get(field) != 0:
                errors.append(f"gates.current_evidence.summary.{field} is not zero")
    current_groups = current.get("groups")
    if not isinstance(current_groups, dict):
        errors.append("gates.current_evidence.groups is missing or not an object")
    else:
        for group in CURRENT_EVIDENCE_GROUPS:
            group_status = current_groups.get(group)
            if not isinstance(group_status, dict):
                errors.append(f"gates.current_evidence.groups.{group} is missing")
            elif group_status.get("ok") is not True:
                errors.append(f"gates.current_evidence.groups.{group}.ok is not true")
            else:
                if group_status.get("status") != "ok":
                    errors.append(f"gates.current_evidence.groups.{group}.status is not ok")
                if group_status.get("returncode") != 0:
                    errors.append(
                        f"gates.current_evidence.groups.{group}.returncode is not zero"
                    )
    non_native_errors = non_native_inventory_errors(current)
    errors.extend(non_native_errors)
    transport_release_errors = transport_release_parity_errors(current)
    errors.extend(transport_release_errors)
    rest_coverage_errors = rest_api_coverage_explanation_errors(current)
    errors.extend(rest_coverage_errors)
    search_coverage_errors = search_e2e_coverage_errors(current)
    errors.extend(search_coverage_errors)
    pit_coverage_errors = pit_e2e_coverage_errors(current)
    errors.extend(pit_coverage_errors)
    broad_coverage_errors = broad_e2e_section_errors(current)
    errors.extend(broad_coverage_errors)
    mixed_cluster_errors = mixed_cluster_coverage_errors(current)
    errors.extend(mixed_cluster_errors)
    materialization_errors = materialization_priority_errors(current)
    errors.extend(materialization_errors)
    production_security_errors = production_security_errors_for_current(current)
    errors.extend(production_security_errors)
    startup_bootstrap_errors_for_current = startup_bootstrap_errors(current)
    errors.extend(startup_bootstrap_errors_for_current)
    runtime_control_errors = runtime_controls_errors(current)
    errors.extend(runtime_control_errors)
    release_evidence_errors = release_evidence_inventory_errors(current)
    errors.extend(release_evidence_errors)
    release_tooling_errors = release_readiness_tooling_errors(current)
    errors.extend(release_tooling_errors)
    source_compatibility_errors = source_compatibility_errors_for_current(current)
    errors.extend(source_compatibility_errors)
    if peer.get("passed") is not True:
        errors.append("gates.runtime_peer_backpressure_current.passed is not true")
    peer_errors = runtime_peer_backpressure_errors(peer)
    errors.extend(peer_errors)

    startup_items = tuple(final.get("startup_manifest_items") or ())
    attachment_items = tuple(final.get("readiness_attachment_items") or ())
    if startup_items != STARTUP_MANIFEST_ITEMS:
        errors.append("final_cutover.startup_manifest_items mismatch")
    if attachment_items != READINESS_ATTACHMENT_ITEMS:
        errors.append("final_cutover.readiness_attachment_items mismatch")
    if "load_comparison" in startup_items:
        errors.append("load_comparison must not be a startup manifest item")
    if "load_comparison" not in attachment_items:
        errors.append("load_comparison must be a readiness attachment item")

    missing_items = final.get("missing_items")
    readiness_attachment_missing_items = final.get("readiness_attachment_missing_items")
    release_record_missing_items = final.get("release_record_missing_items")
    if not isinstance(release_record_missing_items, list):
        errors.append("final_cutover.release_record_missing_items is missing")
    if final.get("passed") is True and missing_items != []:
        errors.append("final_cutover passed but missing_items is not empty")
    if final.get("passed") is True and readiness_attachment_missing_items != []:
        errors.append(
            "final_cutover passed but readiness_attachment_missing_items is not empty"
        )
    if final.get("passed") is True and release_record_missing_items != []:
        errors.append(
            "final_cutover passed but release_record_missing_items is not empty"
        )
    if final.get("passed") is True:
        errors.extend(final_cutover_release_readiness_errors(final))
        errors.extend(final_cutover_command_errors(final))
    if require_final_cutover and final.get("passed") is not True:
        errors.append("final_cutover.passed is not true")

    inventory = final.get("evidence_inventory")
    if not isinstance(inventory, dict):
        errors.append("final_cutover.evidence_inventory is missing or not an object")
    else:
        if not isinstance(inventory.get("returncode"), int):
            errors.append("final_cutover.evidence_inventory.returncode is missing or not an integer")
        elif final.get("passed") is True and inventory.get("returncode") != 0:
            errors.append("final_cutover passed but evidence inventory returncode is not zero")
        if final.get("passed") is True:
            errors.extend(final_cutover_inventory_command_errors(inventory))
        inventory_summary = inventory.get("summary")
        if not isinstance(inventory_summary, dict):
            errors.append("final_cutover.evidence_inventory.summary is missing or not an object")
        else:
            startup_missing = inventory_summary.get("startup_missing_items")
            attachment_missing = inventory_summary.get("readiness_attachment_missing_items")
            release_record_missing = inventory_summary.get("release_record_missing_items")
            if not isinstance(startup_missing, list):
                errors.append("final_cutover.evidence_inventory.summary.startup_missing_items is missing")
            if not isinstance(attachment_missing, list):
                errors.append(
                    "final_cutover.evidence_inventory.summary.readiness_attachment_missing_items is missing"
                )
            if not isinstance(release_record_missing, list):
                errors.append(
                    "final_cutover.evidence_inventory.summary.release_record_missing_items is missing"
                )
            if final.get("passed") is True and inventory_summary.get("complete") is not True:
                errors.append("final_cutover passed but evidence inventory is not complete")
            if final.get("passed") is True and inventory_summary.get("passed") is not True:
                errors.append("final_cutover passed but evidence inventory summary did not pass")
            if final.get("passed") is True and inventory_summary.get("require_complete") is not False:
                errors.append(
                    "final_cutover passed but evidence inventory require_complete is not false"
                )
            if (
                final.get("passed") is True
                and inventory_summary.get("max_age_seconds")
                != RELEASE_EVIDENCE_MAX_AGE_SECONDS
            ):
                errors.append(
                    "final_cutover passed but evidence inventory max_age_seconds "
                    f"is not {RELEASE_EVIDENCE_MAX_AGE_SECONDS}"
                )
            if final.get("passed") is True and startup_missing != []:
                errors.append("final_cutover passed but evidence inventory startup_missing_items is not empty")
            if final.get("passed") is True and attachment_missing != []:
                errors.append(
                    "final_cutover passed but evidence inventory readiness_attachment_missing_items is not empty"
                )
            if final.get("passed") is True and release_record_missing != []:
                errors.append(
                    "final_cutover passed but evidence inventory release_record_missing_items is not empty"
                )
            if final.get("passed") is True:
                errors.extend(final_cutover_inventory_summary_errors(inventory_summary))

    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "passed": not errors,
            "status": summary.get("status"),
            "current_evidence_ready": summary.get("current_evidence_ready"),
            "runtime_peer_backpressure_ready": summary.get("runtime_peer_backpressure_ready"),
            "final_cutover_ready": summary.get("final_cutover_ready"),
            "missing_items": missing_items,
            "readiness_attachment_missing_items": readiness_attachment_missing_items,
            "release_record_missing_items": release_record_missing_items,
        },
    }


def current_git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return completed.stdout.strip()


def final_cutover_release_readiness_errors(final: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if final.get("status") != "ok":
        errors.append("final_cutover passed but status is not ok")
    if final.get("returncode") != 0:
        errors.append("final_cutover passed but returncode is not zero")
    if final.get("readiness_report_path") != RELEASE_READINESS_REPORT_PATH:
        errors.append("final_cutover readiness_report_path does not match current baseline")
    if final.get("errors") != []:
        errors.append("final_cutover passed but errors is not empty")
    if final.get("readiness_attachment_errors") != []:
        errors.append("final_cutover passed but readiness_attachment_errors is not empty")
    if final.get("required_item_inputs") != {}:
        errors.append("final_cutover passed but required_item_inputs is not empty")

    summary = final.get("summary")
    if not isinstance(summary, dict):
        errors.append("final_cutover.summary is missing or not an object")
        return errors
    for field in ("required_items", "checked_items", "ready_items"):
        if summary.get(field) != len(STARTUP_MANIFEST_ITEMS):
            errors.append(
                f"final_cutover.summary.{field} does not equal {len(STARTUP_MANIFEST_ITEMS)}"
            )
    return errors


def final_cutover_command_errors(final: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    command = final.get("command")
    if not isinstance(command, list) or len(command) < 2:
        errors.append("final_cutover command is missing")
    elif tuple(command[1:]) != FINAL_CUTOVER_COMMAND_TAIL:
        errors.append("final_cutover command does not match current baseline")

    manifest_template = final.get("manifest_command_template")
    if tuple(manifest_template or ()) != FINAL_CUTOVER_MANIFEST_COMMAND_TEMPLATE:
        errors.append("final_cutover manifest command template does not match current baseline")
    return errors


def final_cutover_inventory_command_errors(inventory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    command = inventory.get("command")
    if not isinstance(command, list) or len(command) < 6:
        errors.append("final_cutover evidence inventory command is missing")
    else:
        if tuple(command[1:3]) != FINAL_CUTOVER_INVENTORY_COMMAND_TAIL:
            errors.append(
                "final_cutover evidence inventory command does not match current baseline"
            )
        if "--max-age-seconds" not in command:
            errors.append("final_cutover evidence inventory command is missing max age")
        else:
            index = command.index("--max-age-seconds")
            value = command[index + 1] if index + 1 < len(command) else None
            if value != str(RELEASE_EVIDENCE_MAX_AGE_SECONDS):
                errors.append(
                    "final_cutover evidence inventory command max age "
                    f"is not {RELEASE_EVIDENCE_MAX_AGE_SECONDS}"
                )

    attach_template = inventory.get("attach_command_template")
    if not isinstance(attach_template, list) or len(attach_template) < 2:
        errors.append("final_cutover evidence inventory attach command template is missing")
    else:
        if attach_template[:2] != ["python3", "tools/attach-release-readiness-evidence.py"]:
            errors.append(
                "final_cutover evidence inventory attach command template tool mismatch"
            )
        missing_flags = [
            flag for flag in FINAL_CUTOVER_ATTACH_TEMPLATE_FLAGS if flag not in attach_template
        ]
        if missing_flags:
            errors.append(
                "final_cutover evidence inventory attach command template missing flags: "
                + ", ".join(missing_flags)
            )
    return errors


def final_cutover_inventory_summary_errors(summary: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_counts = (
        ("startup_item_count", len(STARTUP_MANIFEST_ITEMS)),
        ("startup_ready_item_count", len(STARTUP_MANIFEST_ITEMS)),
        ("readiness_attachment_item_count", len(READINESS_ATTACHMENT_ITEMS)),
        ("readiness_attachment_ready_item_count", len(READINESS_ATTACHMENT_ITEMS)),
        ("release_record_item_count", len(RELEASE_RECORD_ITEMS)),
        ("release_record_ready_item_count", len(RELEASE_RECORD_ITEMS)),
    )
    for field, expected in expected_counts:
        if summary.get(field) != expected:
            errors.append(
                f"final_cutover evidence inventory {field} does not equal {expected}"
            )

    expected_items = (
        ("startup_ready_items", STARTUP_MANIFEST_ITEMS),
        ("readiness_attachment_ready_items", READINESS_ATTACHMENT_ITEMS),
        ("release_record_ready_items", RELEASE_RECORD_ITEMS),
    )
    for field, expected in expected_items:
        value = summary.get(field)
        if tuple(value or ()) != expected:
            errors.append(f"final_cutover evidence inventory {field} mismatch")
    return errors


def gate(gates: dict[str, Any], name: str) -> dict[str, Any]:
    value = gates.get(name)
    return value if isinstance(value, dict) else {}


def non_native_inventory_errors(current: dict[str, Any]) -> list[str]:
    inventory_result = None
    for result in current.get("results") or []:
        if isinstance(result, dict) and result.get("group") == "non-native-inventory":
            inventory_result = result
            break
    if inventory_result is None:
        return ["gates.current_evidence.results non-native-inventory is missing"]
    summary = inventory_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results non-native-inventory.summary is missing"]

    errors: list[str] = []
    errors.extend(current_result_envelope_errors(inventory_result, "non-native inventory"))
    if summary.get("passed") is not True:
        errors.append("gates.current_evidence.results non-native inventory did not pass")
    for field in ("missing_category_count", "missing_family_count", "missing_probe_count"):
        if summary.get(field) != 0:
            errors.append(f"gates.current_evidence.results non-native inventory {field} is not zero")
    family_count = summary.get("family_count")
    evidenced_family_count = summary.get("evidenced_family_count")
    if not isinstance(family_count, int) or family_count <= 0:
        errors.append("gates.current_evidence.results non-native inventory family count is not positive")
    elif family_count != NON_NATIVE_INVENTORY_FAMILY_COUNT:
        errors.append(
            "gates.current_evidence.results non-native inventory family count "
            f"is not {NON_NATIVE_INVENTORY_FAMILY_COUNT}"
        )
    if evidenced_family_count != family_count:
        errors.append("gates.current_evidence.results non-native inventory evidenced family count mismatch")
    probe_count = summary.get("probe_count")
    matched_probe_count = summary.get("matched_probe_count")
    if not isinstance(probe_count, int) or probe_count <= 0:
        errors.append("gates.current_evidence.results non-native inventory probe count is not positive")
    elif probe_count != NON_NATIVE_INVENTORY_PROBE_COUNT:
        errors.append(
            "gates.current_evidence.results non-native inventory probe count "
            f"is not {NON_NATIVE_INVENTORY_PROBE_COUNT}"
        )
    if matched_probe_count != probe_count:
        errors.append("gates.current_evidence.results non-native inventory matched probe count mismatch")
    required_categories = summary.get("required_categories")
    covered_categories = summary.get("covered_categories")
    if tuple(required_categories or ()) != NON_NATIVE_REQUIRED_CATEGORIES:
        errors.append(
            "gates.current_evidence.results non-native inventory required categories "
            "do not match current baseline"
        )
    if tuple(covered_categories or ()) != NON_NATIVE_COVERED_CATEGORIES:
        errors.append(
            "gates.current_evidence.results non-native inventory covered categories "
            "do not match current baseline"
        )
    if summary.get("missing_categories") != []:
        errors.append("gates.current_evidence.results non-native inventory missing categories is not empty")
    return errors


def transport_release_parity_errors(current: dict[str, Any]) -> list[str]:
    transport_result = None
    for result in current.get("results") or []:
        if isinstance(result, dict) and result.get("group") == "transport-action-coverage-current":
            transport_result = result
            break
    if transport_result is None:
        return ["gates.current_evidence.results transport-action-coverage-current is missing"]
    summary = transport_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results transport-action-coverage-current.summary is missing"]

    errors: list[str] = []
    errors.extend(current_result_envelope_errors(transport_result, "transport coverage"))
    if summary.get("passed") is not True:
        errors.append("gates.current_evidence.results transport coverage did not pass")
    if summary.get("peer_backpressure_passed") is not True:
        errors.append(
            "gates.current_evidence.results transport peer backpressure did not pass"
        )
    if summary.get("release_parity_evidence_complete") is not True:
        errors.append(
            "gates.current_evidence.results transport release parity evidence is not complete"
        )
    if summary.get("release_parity_source_missing_action_count") != 0:
        errors.append(
            "gates.current_evidence.results transport release parity missing action count is not zero"
        )
    for field in (
        "partial_action_count",
        "planned_action_count",
        "stubbed_action_count",
        "out_of_scope_action_count",
    ):
        if summary.get(field) != 0:
            errors.append(f"gates.current_evidence.results transport {field} is not zero")
    matched = summary.get("release_parity_source_matched_action_count")
    if not isinstance(matched, int) or matched <= 0:
        errors.append(
            "gates.current_evidence.results transport release parity matched action count is not positive"
        )
    if matched != TRANSPORT_RELEASE_PARITY_ACTION_COUNT:
        errors.append(
            "gates.current_evidence.results transport release parity matched action count "
            f"is not {TRANSPORT_RELEASE_PARITY_ACTION_COUNT}"
        )
    for field in (
        "transport_action_count",
        "implemented_action_count",
        "inventory_action_count",
        "release_parity_action_count",
        "accepted_evidence_action_count",
        "accepted_evidence_inventory_matched_action_count",
        "source_implemented_inventory_matched_action_count",
        "release_evidence_inventory_matched_action_count",
    ):
        if summary.get(field) != TRANSPORT_RELEASE_PARITY_ACTION_COUNT:
            errors.append(
                f"gates.current_evidence.results transport {field} "
                f"is not {TRANSPORT_RELEASE_PARITY_ACTION_COUNT}"
            )
    for field in (
        "accepted_evidence_inventory_missing_action_count",
        "accepted_evidence_inventory_extra_action_count",
        "source_implemented_inventory_missing_action_count",
        "source_implemented_evidence_missing_action_count",
        "release_evidence_inventory_missing_action_count",
        "release_evidence_inventory_extra_action_count",
        "release_accepted_evidence_drift_error_count",
        "accepted_evidence_action_binding_error_count",
        "accepted_evidence_pointer_test_error_count",
        "accepted_evidence_request_semantic_error_count",
        "accepted_evidence_response_semantic_error_count",
        "accepted_evidence_shared_pointer_error_count",
        "release_evidence_action_binding_error_count",
        "release_evidence_pointer_test_error_count",
        "release_evidence_request_semantic_error_count",
        "release_evidence_response_semantic_error_count",
        "release_evidence_shared_pointer_error_count",
    ):
        if summary.get(field) != 0:
            errors.append(f"gates.current_evidence.results transport {field} is not zero")
    action_claim = summary.get("action_coverage_claim")
    if not isinstance(action_claim, str) or "implemented adapters" not in action_claim:
        errors.append(
            "gates.current_evidence.results transport action coverage claim is missing"
        )
    accepted_scope_counts = summary.get("accepted_evidence_scope_counts")
    if not isinstance(accepted_scope_counts, dict):
        errors.append(
            "gates.current_evidence.results transport accepted evidence scope counts are missing"
        )
    elif accepted_scope_counts != TRANSPORT_ACCEPTED_EVIDENCE_SCOPE_COUNTS:
        errors.append(
            "gates.current_evidence.results transport accepted evidence scope counts "
            "do not match current baseline"
        )
    release_scope_counts = summary.get("release_evidence_scope_counts")
    if not isinstance(release_scope_counts, dict):
        errors.append(
            "gates.current_evidence.results transport release evidence scope counts are missing"
        )
    else:
        runtime_action_parity_count = release_scope_counts.get("runtime_action_parity")
        if not isinstance(runtime_action_parity_count, int) or runtime_action_parity_count != matched:
            errors.append(
                "gates.current_evidence.results transport release runtime-action scope count "
                "does not match matched action count"
            )
    claim_boundary = summary.get("transport_execution_claim_boundary")
    if not isinstance(claim_boundary, str) or "does not promote generic transport action execution" not in claim_boundary:
        errors.append(
            "gates.current_evidence.results transport execution claim boundary is missing"
        )
    return errors


def rest_api_coverage_explanation_errors(current: dict[str, Any]) -> list[str]:
    rest_result = None
    for result in current.get("results") or []:
        if isinstance(result, dict) and result.get("group") == "rest-api-coverage-current":
            rest_result = result
            break
    if rest_result is None:
        return ["gates.current_evidence.results rest-api-coverage-current is missing"]
    summary = rest_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results rest-api-coverage-current.summary is missing"]

    errors: list[str] = []
    errors.extend(current_result_envelope_errors(rest_result, "REST coverage"))
    if summary.get("passed") is not True:
        errors.append("gates.current_evidence.results REST coverage summary did not pass")
    coverage_count = summary.get("live_required_matched_source_route_count")
    in_scope_count = summary.get("in_scope_source_route_count")
    coverage_ratio = summary.get("live_required_matched_source_route_ratio")
    fixture_route_count = summary.get("fixture_route_count")
    fixture_matched_count = summary.get("fixture_matched_source_route_count")
    fixture_ratio = summary.get("fixture_matched_source_route_ratio")
    fixture_uncovered_count = summary.get("fixture_uncovered_in_scope_route_count")
    live_required_fixture_count = summary.get("live_required_fixture_route_count")
    live_required_uncovered_count = summary.get(
        "live_required_uncovered_in_scope_route_count"
    )
    if not isinstance(coverage_count, int) or coverage_count <= 0:
        errors.append(
            "gates.current_evidence.results REST live required matched source route count is not positive"
        )
    if not isinstance(in_scope_count, int) or in_scope_count <= 0:
        errors.append(
            "gates.current_evidence.results REST in-scope source route count is not positive"
        )
    if coverage_count != in_scope_count:
        errors.append(
            "gates.current_evidence.results REST live required matched source route count "
            "does not equal in-scope source route count"
        )
    if coverage_count != REST_LIVE_REQUIRED_MATCHED_SOURCE_ROUTE_COUNT:
        errors.append(
            "gates.current_evidence.results REST live required matched source route count "
            f"is not {REST_LIVE_REQUIRED_MATCHED_SOURCE_ROUTE_COUNT}"
        )
    if in_scope_count != REST_LIVE_REQUIRED_MATCHED_SOURCE_ROUTE_COUNT:
        errors.append(
            "gates.current_evidence.results REST in-scope source route count "
            f"is not {REST_LIVE_REQUIRED_MATCHED_SOURCE_ROUTE_COUNT}"
        )
    source_route_count = summary.get("source_route_count")
    if source_route_count != REST_SOURCE_ROUTE_COUNT:
        errors.append(
            "gates.current_evidence.results REST source route count "
            f"is not {REST_SOURCE_ROUTE_COUNT}"
        )
    if coverage_ratio != 1.0:
        errors.append(
            "gates.current_evidence.results REST live required matched source route ratio is not 1.0"
        )
    if fixture_route_count != REST_FIXTURE_ROUTE_COUNT:
        errors.append(
            "gates.current_evidence.results REST fixture route count "
            f"is not {REST_FIXTURE_ROUTE_COUNT}"
        )
    if fixture_matched_count != REST_LIVE_REQUIRED_MATCHED_SOURCE_ROUTE_COUNT:
        errors.append(
            "gates.current_evidence.results REST fixture matched source route count "
            f"is not {REST_LIVE_REQUIRED_MATCHED_SOURCE_ROUTE_COUNT}"
        )
    if fixture_ratio != 1.0:
        errors.append(
            "gates.current_evidence.results REST fixture matched source route ratio is not 1.0"
        )
    if fixture_uncovered_count != 0:
        errors.append(
            "gates.current_evidence.results REST fixture uncovered in-scope route count is not zero"
        )
    if live_required_fixture_count != REST_LIVE_REQUIRED_FIXTURE_ROUTE_COUNT:
        errors.append(
            "gates.current_evidence.results REST live required fixture route count "
            f"is not {REST_LIVE_REQUIRED_FIXTURE_ROUTE_COUNT}"
        )
    if live_required_uncovered_count != 0:
        errors.append(
            "gates.current_evidence.results REST live required uncovered in-scope route count is not zero"
        )
    if summary.get("unified_report_fresh") is not True:
        errors.append("gates.current_evidence.results REST unified report is not fresh")
    source_status_counts = summary.get("source_status_counts")
    if not isinstance(source_status_counts, dict):
        errors.append("gates.current_evidence.results REST source status counts are missing")
    else:
        if source_status_counts != REST_SOURCE_STATUS_COUNTS:
            errors.append(
                "gates.current_evidence.results REST source status counts "
                "do not match current baseline"
            )
        unexpected_statuses = {
            status: count
            for status, count in source_status_counts.items()
            if status not in {"implemented", "out-of-scope"}
        }
        if unexpected_statuses:
            details = ", ".join(
                f"{status}={count}" for status, count in sorted(unexpected_statuses.items())
            )
            errors.append(
                "gates.current_evidence.results REST source status counts contain "
                f"non-closed statuses: {details}"
            )
    if summary.get("unified_required_suite_status") != "ok":
        errors.append("gates.current_evidence.results REST unified required suite status is not ok")
    if (
        summary.get("unified_required_suite_classification")
        != REST_UNIFIED_REQUIRED_SUITE_CLASSIFICATION
    ):
        errors.append(
            "gates.current_evidence.results REST unified required suite classification "
            "does not match current baseline"
        )
    if (
        summary.get("unified_required_suite_effective_classification")
        != REST_UNIFIED_REQUIRED_SUITE_EFFECTIVE_CLASSIFICATION
    ):
        errors.append(
            "gates.current_evidence.results REST unified required suite effective classification "
            "does not match current baseline"
        )
    if (
        summary.get("unified_required_suite_skip_resolution")
        != REST_UNIFIED_REQUIRED_SUITE_SKIP_RESOLUTION
    ):
        errors.append(
            "gates.current_evidence.results REST unified required suite skip resolution "
            "does not match current baseline"
        )

    steelsearch_only_summary = summary.get(
        "unified_required_suite_steelsearch_only_summary"
    )
    if not isinstance(steelsearch_only_summary, dict):
        errors.append(
            "gates.current_evidence.results REST steelsearch-only summary is missing"
        )
        return errors
    if steelsearch_only_summary != REST_STEELSEARCH_ONLY_SUMMARY:
        errors.append(
            "gates.current_evidence.results REST steelsearch-only summary "
            "does not match current baseline"
        )
    if steelsearch_only_summary.get("raw_delta") != 0:
        errors.append(
            "gates.current_evidence.results REST steelsearch-only raw delta is not zero"
        )
    if steelsearch_only_summary.get("effective_unexplained_delta") != 0:
        errors.append(
            "gates.current_evidence.results REST steelsearch-only unexplained effective delta is not zero"
        )
    raw_total = steelsearch_only_summary.get("raw_total")
    required_breakdown = summary.get(
        "unified_required_suite_steelsearch_only_breakdown"
    )
    if not isinstance(required_breakdown, list):
        errors.append(
            "gates.current_evidence.results REST steelsearch-only required breakdown is missing"
        )
    elif isinstance(raw_total, int) and raw_total > 0 and not required_breakdown:
        errors.append(
            "gates.current_evidence.results REST steelsearch-only required breakdown is empty"
        )
    if not isinstance(
        summary.get("unified_non_required_suite_steelsearch_only_breakdown"), list
    ):
        errors.append(
            "gates.current_evidence.results REST steelsearch-only non-required breakdown is missing"
        )
    return errors


def search_e2e_coverage_errors(current: dict[str, Any]) -> list[str]:
    required_result = None
    compat_result = None
    for result in current.get("results") or []:
        if not isinstance(result, dict):
            continue
        if (
            result.get("group") == "e2e-required-parity"
            and result.get("name")
            == "search_semantic_and_vector_search_e2e_reports_have_no_failed_missing_or_skipped_cases"
        ):
            required_result = result
        if (
            result.get("group") == "e2e-search-compat-parity"
            and result.get("name")
            == "search_compat_and_strict_e2e_reports_have_no_failed_or_missing_cases"
        ):
            compat_result = result

    errors: list[str] = []
    errors.extend(
        search_e2e_result_errors(
            required_result,
            "required search semantic/vector",
            semantic_suite_count=SEARCH_REQUIRED_SEMANTIC_SUITE_COUNT,
            semantic_suite_names=SEARCH_REQUIRED_SEMANTIC_SUITE_NAMES,
        )
    )
    errors.extend(
        search_e2e_result_errors(
            compat_result,
            "search compat/strict",
            semantic_suite_count=SEARCH_COMPAT_SEMANTIC_SUITE_COUNT,
            semantic_suite_names=SEARCH_COMPAT_SEMANTIC_SUITE_NAMES,
        )
    )
    return errors


def search_e2e_result_errors(
    result: dict[str, Any] | None,
    label: str,
    *,
    semantic_suite_count: int,
    semantic_suite_names: tuple[str, ...],
) -> list[str]:
    if result is None:
        return [f"gates.current_evidence.results {label} E2E result is missing"]
    summary = result.get("summary")
    if not isinstance(summary, dict):
        return [f"gates.current_evidence.results {label} E2E summary is missing"]

    errors: list[str] = []
    errors.extend(current_result_envelope_errors(result, f"{label} E2E"))
    if summary.get("passed") is not True:
        errors.append(f"gates.current_evidence.results {label} E2E did not pass")
    errors.extend(e2e_result_classification_errors(summary, label))
    suite_counts = summary.get("required_section_suite_counts")
    suite_names = summary.get("required_section_suite_names")
    report_path_counts = summary.get("required_section_report_path_counts")
    if not isinstance(suite_counts, dict):
        errors.append(f"gates.current_evidence.results {label} E2E section suite counts are missing")
    if not isinstance(suite_names, dict):
        errors.append(f"gates.current_evidence.results {label} E2E section suite names are missing")
    if not isinstance(report_path_counts, dict):
        errors.append(f"gates.current_evidence.results {label} E2E section report path counts are missing")
    if isinstance(suite_counts, dict) and isinstance(report_path_counts, dict):
        suite_count = suite_counts.get("semantic_parity")
        report_path_count = report_path_counts.get("semantic_parity")
        if suite_count != semantic_suite_count:
            errors.append(
                f"gates.current_evidence.results {label} E2E semantic parity suite count "
                f"is not {semantic_suite_count}"
            )
        if report_path_count != semantic_suite_count:
            errors.append(
                f"gates.current_evidence.results {label} E2E semantic parity report path count "
                f"is not {semantic_suite_count}"
            )
        if isinstance(suite_count, int) and isinstance(report_path_count, int) and suite_count != report_path_count:
            errors.append(
                f"gates.current_evidence.results {label} E2E semantic parity suite/report path count mismatch"
            )
    if isinstance(suite_names, dict):
        actual_names = tuple(suite_names.get("semantic_parity") or ())
        if actual_names != semantic_suite_names:
            errors.append(
                f"gates.current_evidence.results {label} E2E semantic parity suite names do not match current baseline"
            )
    return errors


def pit_e2e_coverage_errors(current: dict[str, Any]) -> list[str]:
    pit_result = None
    for result in current.get("results") or []:
        if not isinstance(result, dict):
            continue
        if (
            result.get("group") == "e2e-search-compat-parity"
            and result.get("name")
            == "pit_e2e_reports_have_required_opensearch_compared_cases_without_skips"
        ):
            pit_result = result
            break
    if pit_result is None:
        return ["gates.current_evidence.results PIT E2E coverage result is missing"]
    summary = pit_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results PIT E2E coverage summary is missing"]

    errors: list[str] = []
    errors.extend(current_result_envelope_errors(pit_result, "PIT E2E coverage"))
    required_count = summary.get("required_pit_case_count")
    compared_count = summary.get("required_pit_compared_case_count")
    if required_count != PIT_REQUIRED_CASE_COUNT:
        errors.append(
            f"gates.current_evidence.results PIT required case count is not {PIT_REQUIRED_CASE_COUNT}"
        )
    if compared_count != PIT_REQUIRED_CASE_COUNT:
        errors.append(
            f"gates.current_evidence.results PIT compared case count is not {PIT_REQUIRED_CASE_COUNT}"
        )
    if required_count != compared_count:
        errors.append(
            "gates.current_evidence.results PIT compared case count does not equal required case count"
        )
    if summary.get("non_passed_pit_case_count") != 0:
        errors.append(
            "gates.current_evidence.results PIT non-passed case count is not zero"
        )
    suite_count = summary.get("suite_count")
    if suite_count != PIT_SUITE_COUNT:
        errors.append(
            f"gates.current_evidence.results PIT suite count is not {PIT_SUITE_COUNT}"
        )
    pit_case_count = summary.get("pit_case_count")
    if pit_case_count != PIT_CASE_COUNT:
        errors.append(
            f"gates.current_evidence.results PIT case count is not {PIT_CASE_COUNT}"
        )
    if summary.get("unified_report_fresh") is not True:
        errors.append("gates.current_evidence.results PIT unified report is not fresh")
    if summary.get("unified_report_max_age_seconds") != RELEASE_EVIDENCE_MAX_AGE_SECONDS:
        errors.append(
            "gates.current_evidence.results PIT unified report max age "
            f"is not {RELEASE_EVIDENCE_MAX_AGE_SECONDS}"
        )
    return errors


def broad_e2e_section_errors(current: dict[str, Any]) -> list[str]:
    broad_result = None
    for result in current.get("results") or []:
        if not isinstance(result, dict):
            continue
        if (
            result.get("group") == "e2e-broad-parity"
            and result.get("name")
            == "broad_unified_opensearch_e2e_report_has_no_failed_missing_or_drifted_required_suites"
        ):
            broad_result = result
            break
    if broad_result is None:
        return ["gates.current_evidence.results broad E2E section result is missing"]
    summary = broad_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results broad E2E section summary is missing"]

    errors: list[str] = []
    errors.extend(current_result_envelope_errors(broad_result, "broad E2E section"))
    expected_sections = set(BROAD_E2E_SECTION_SUITE_COUNTS)
    required_sections = summary.get("required_sections")
    if set(required_sections or []) != expected_sections:
        errors.append("gates.current_evidence.results broad E2E required sections mismatch")
    if summary.get("required_section_count") != len(expected_sections):
        errors.append("gates.current_evidence.results broad E2E required section count mismatch")
    required_opensearch_suites = summary.get("required_opensearch_suites")
    if not isinstance(required_opensearch_suites, list) or "security-authz" not in required_opensearch_suites:
        errors.append(
            "gates.current_evidence.results broad E2E required OpenSearch suites missing security-authz"
        )
    if summary.get("required_opensearch_suite_count") != 1:
        errors.append(
            "gates.current_evidence.results broad E2E required OpenSearch suite count mismatch"
        )
    if summary.get("required_opensearch_missing_suites") != []:
        errors.append(
            "gates.current_evidence.results broad E2E required OpenSearch suite evidence is missing"
        )
    suite_counts = summary.get("required_section_suite_counts")
    suite_names = summary.get("required_section_suite_names")
    report_path_counts = summary.get("required_section_report_path_counts")
    if not isinstance(suite_counts, dict):
        errors.append("gates.current_evidence.results broad E2E section suite counts are missing")
    if not isinstance(suite_names, dict):
        errors.append("gates.current_evidence.results broad E2E section suite names are missing")
    if not isinstance(report_path_counts, dict):
        errors.append("gates.current_evidence.results broad E2E section report path counts are missing")
    errors.extend(e2e_result_classification_errors(summary, "broad"))
    if isinstance(suite_counts, dict) and isinstance(report_path_counts, dict):
        for section in sorted(expected_sections):
            suite_count = suite_counts.get(section)
            report_path_count = report_path_counts.get(section)
            expected_count = BROAD_E2E_SECTION_SUITE_COUNTS[section]
            if suite_count != expected_count:
                errors.append(
                    f"gates.current_evidence.results broad E2E {section} suite count "
                    f"is not {expected_count}"
                )
            if report_path_count != expected_count:
                errors.append(
                    f"gates.current_evidence.results broad E2E {section} report path count "
                    f"is not {expected_count}"
                )
            if isinstance(suite_count, int) and isinstance(report_path_count, int) and suite_count != report_path_count:
                errors.append(
                    f"gates.current_evidence.results broad E2E {section} suite/report path count mismatch"
                )
    if isinstance(suite_names, dict):
        for section in sorted(expected_sections):
            if tuple(suite_names.get(section) or ()) != BROAD_E2E_SECTION_SUITE_NAMES[section]:
                errors.append(
                    f"gates.current_evidence.results broad E2E {section} suite names do not match current baseline"
                )
    return errors


def e2e_result_classification_errors(summary: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    classification = summary.get("case_classification")
    effective = summary.get("effective_case_classification")
    skipped = summary.get("skipped_case_resolution")
    if not isinstance(classification, dict):
        errors.append(f"gates.current_evidence.results {label} E2E case classification is missing")
    else:
        if classification.get("failed") != 0:
            errors.append(f"gates.current_evidence.results {label} E2E failed classification is not zero")
        if classification.get("missing") != 0:
            errors.append(f"gates.current_evidence.results {label} E2E missing classification is not zero")
    if not isinstance(effective, dict):
        errors.append(
            f"gates.current_evidence.results {label} E2E effective case classification is missing"
        )
    elif effective.get("known_gap_or_skipped") != 0:
        errors.append(
            f"gates.current_evidence.results {label} E2E effective skipped classification is not zero"
        )
    if not isinstance(skipped, dict):
        errors.append(f"gates.current_evidence.results {label} E2E skipped resolution is missing")
    else:
        total_count = skipped.get("total_count")
        resolved_count = skipped.get("resolved_by_other_suite_count")
        unresolved_count = skipped.get("unresolved_count")
        if not all(
            isinstance(value, int) and value >= 0
            for value in (total_count, resolved_count, unresolved_count)
        ):
            errors.append(
                f"gates.current_evidence.results {label} E2E skipped resolution counts are invalid"
            )
        else:
            if total_count != resolved_count + unresolved_count:
                errors.append(
                    f"gates.current_evidence.results {label} E2E skipped resolution counts do not add up"
                )
            if isinstance(classification, dict) and classification.get("known_gap_or_skipped") != total_count:
                errors.append(
                    f"gates.current_evidence.results {label} E2E skipped total does not match raw classification"
                )
            if isinstance(effective, dict) and effective.get("known_gap_or_skipped") != unresolved_count:
                errors.append(
                    f"gates.current_evidence.results {label} E2E effective skipped classification does not match unresolved count"
                )
        if unresolved_count != 0:
            errors.append(
                f"gates.current_evidence.results {label} E2E unresolved skipped count is not zero"
            )
    baseline = E2E_CLASSIFICATION_BASELINES.get(label)
    if baseline is not None:
        if classification != baseline["case_classification"]:
            errors.append(
                f"gates.current_evidence.results {label} E2E case classification "
                "does not match current baseline"
            )
        if effective != baseline["effective_case_classification"]:
            errors.append(
                f"gates.current_evidence.results {label} E2E effective case classification "
                "does not match current baseline"
            )
        if skipped != baseline["skipped_case_resolution"]:
            errors.append(
                f"gates.current_evidence.results {label} E2E skipped resolution "
                "does not match current baseline"
            )
    return errors


def mixed_cluster_coverage_errors(current: dict[str, Any]) -> list[str]:
    coverage_result = None
    remote_pit_result = None
    for result in current.get("results") or []:
        if not isinstance(result, dict):
            continue
        if (
            result.get("group") == "mixed-cluster-coverage-current"
            and result.get("name")
            == "mixed_cluster_join_and_movement_coverage_is_reported_with_scope_boundary"
        ):
            coverage_result = result
        if (
            result.get("group") == "mixed-cluster-coverage-current"
            and result.get("name")
            == "multi_node_transport_admin_report_requires_remote_pit_forwarding_cases"
        ):
            remote_pit_result = result

    errors: list[str] = []
    if coverage_result is None:
        errors.append("gates.current_evidence.results mixed-cluster coverage result is missing")
        coverage_summary = None
    else:
        if coverage_result.get("ok") is not True:
            errors.append("gates.current_evidence.results mixed-cluster coverage result is not ok")
        if coverage_result.get("status") != "ok":
            errors.append("gates.current_evidence.results mixed-cluster coverage status is not ok")
        if coverage_result.get("returncode") != 0:
            errors.append("gates.current_evidence.results mixed-cluster coverage returncode is not zero")
        coverage_summary = coverage_result.get("summary")
        if not isinstance(coverage_summary, dict):
            errors.append("gates.current_evidence.results mixed-cluster coverage summary is missing")
            coverage_summary = None
        else:
            errors.extend(mixed_cluster_coverage_summary_errors(coverage_summary))

    if remote_pit_result is None:
        errors.append("gates.current_evidence.results mixed-cluster remote PIT result is missing")
    else:
        if remote_pit_result.get("ok") is not True:
            errors.append("gates.current_evidence.results mixed-cluster remote PIT result is not ok")
        if remote_pit_result.get("status") != "ok":
            errors.append("gates.current_evidence.results mixed-cluster remote PIT status is not ok")
        if remote_pit_result.get("returncode") != 0:
            errors.append("gates.current_evidence.results mixed-cluster remote PIT returncode is not zero")
        remote_pit_summary = remote_pit_result.get("summary")
        if not isinstance(remote_pit_summary, dict):
            errors.append("gates.current_evidence.results mixed-cluster remote PIT summary is missing")
        else:
            if remote_pit_summary.get("passed") is not True:
                errors.append("gates.current_evidence.results mixed-cluster remote PIT did not pass")
            if remote_pit_summary.get("remote_pit_required") is not True:
                errors.append("gates.current_evidence.results mixed-cluster remote PIT is not required")
            if remote_pit_summary.get("publication_validation_events_required") is not True:
                errors.append(
                    "gates.current_evidence.results mixed-cluster publication validation events are not required"
                )
            remote_pit_case_count = remote_pit_summary.get("remote_pit_case_count")
            if remote_pit_case_count != MIXED_TRANSPORT_ADMIN_REMOTE_PIT_CASE_COUNT:
                errors.append(
                    "gates.current_evidence.results mixed-cluster remote PIT case count does not equal current baseline"
                )
            if remote_pit_summary.get("failed_count") != 0:
                errors.append(
                    "gates.current_evidence.results mixed-cluster remote PIT failed count is not zero"
                )
            if (
                isinstance(coverage_summary, dict)
                and coverage_summary.get("transport_admin_remote_pit_case_count")
                != remote_pit_case_count
            ):
                errors.append(
                    "gates.current_evidence.results mixed-cluster remote PIT case count "
                    "does not match transport admin summary"
                )

    return errors


def mixed_cluster_coverage_summary_errors(summary: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if summary.get("passed") is not True:
        errors.append("gates.current_evidence.results mixed-cluster coverage did not pass")
    phase_c_report_count = summary.get("phase_c_report_count")
    phase_c_passed_count = summary.get("phase_c_passed_report_count")
    phase_c_fresh_count = summary.get("phase_c_fresh_report_count")
    if not isinstance(phase_c_report_count, int) or phase_c_report_count <= 0:
        errors.append("gates.current_evidence.results mixed-cluster phase C report count is not positive")
    if phase_c_report_count != MIXED_PHASE_C_REPORT_COUNT:
        errors.append(
            "gates.current_evidence.results mixed-cluster phase C report count "
            f"is not {MIXED_PHASE_C_REPORT_COUNT}"
        )
    if tuple(summary.get("phase_c_report_names") or ()) != MIXED_PHASE_C_REPORT_NAMES:
        errors.append(
            "gates.current_evidence.results mixed-cluster phase C report names do not match current baseline"
        )
    if phase_c_passed_count != phase_c_report_count:
        errors.append("gates.current_evidence.results mixed-cluster phase C passed count mismatch")
    if tuple(summary.get("phase_c_passed_report_names") or ()) != MIXED_PHASE_C_REPORT_NAMES:
        errors.append(
            "gates.current_evidence.results mixed-cluster phase C passed report names do not match current baseline"
        )
    if phase_c_fresh_count != phase_c_report_count:
        errors.append("gates.current_evidence.results mixed-cluster phase C fresh count mismatch")
    if tuple(summary.get("phase_c_fresh_report_names") or ()) != MIXED_PHASE_C_REPORT_NAMES:
        errors.append(
            "gates.current_evidence.results mixed-cluster phase C fresh report names do not match current baseline"
        )
    if tuple(summary.get("phase_c_stale_report_names") or ()) != ():
        errors.append(
            "gates.current_evidence.results mixed-cluster phase C stale report names is not empty"
        )
    if tuple(summary.get("phase_c_age_checked_report_names") or ()) != MIXED_PHASE_C_REPORT_NAMES:
        errors.append(
            "gates.current_evidence.results mixed-cluster phase C age-checked report names do not match current baseline"
        )
    if tuple(summary.get("mixed_cluster_stale_evidence_names") or ()) != ():
        errors.append(
            "gates.current_evidence.results mixed-cluster stale evidence names is not empty"
        )
    if tuple(summary.get("phase_c_required_summary_reports") or ()) != MIXED_PHASE_C_REQUIRED_SUMMARY_REPORTS:
        errors.append(
            "gates.current_evidence.results mixed-cluster phase C required summary reports do not match current baseline"
        )
    expected_check_names = {
        name: list(checks)
        for name, checks in MIXED_PHASE_C_REQUIRED_CHECK_NAMES.items()
    }
    if summary.get("phase_c_required_check_names") != expected_check_names:
        errors.append(
            "gates.current_evidence.results mixed-cluster phase C required check names do not match current baseline"
        )
    if summary.get("phase_c_passed_check_names") != expected_check_names:
        errors.append(
            "gates.current_evidence.results mixed-cluster phase C passed check names do not match current baseline"
        )

    failure_node_loss_count = summary.get("failure_node_loss_report_count")
    failure_node_loss_passed_count = summary.get("failure_node_loss_passed_report_count")
    if not isinstance(failure_node_loss_count, int) or failure_node_loss_count <= 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster failure node-loss report count is not positive"
        )
    if failure_node_loss_count != MIXED_FAILURE_NODE_LOSS_REPORT_COUNT:
        errors.append(
            "gates.current_evidence.results mixed-cluster failure node-loss report count "
            f"is not {MIXED_FAILURE_NODE_LOSS_REPORT_COUNT}"
        )
    if failure_node_loss_passed_count != failure_node_loss_count:
        errors.append(
            "gates.current_evidence.results mixed-cluster failure node-loss passed count mismatch"
        )
    if tuple(summary.get("failure_node_loss_report_names") or ()) != MIXED_FAILURE_NODE_LOSS_REPORT_NAMES:
        errors.append(
            "gates.current_evidence.results mixed-cluster failure node-loss report names do not match current baseline"
        )
    if tuple(summary.get("failure_node_loss_passed_report_names") or ()) != MIXED_FAILURE_NODE_LOSS_REPORT_NAMES:
        errors.append(
            "gates.current_evidence.results mixed-cluster failure node-loss passed report names do not match current baseline"
        )

    required_true_flags = (
        "shard_movement_passed",
        "shard_movement_fresh",
        "shard_movement_age_checked",
        "checkpoint_drift_ok",
        "checkpoint_monotonicity_ok",
        "opensearch_to_steelsearch_passed",
        "retention_lease_metadata_ok",
        "steelsearch_to_opensearch_passed",
        "transport_log_ok",
        "unsupported_allocation_explain_ok",
    )
    for flag in required_true_flags:
        if summary.get(flag) is not True:
            errors.append(f"gates.current_evidence.results mixed-cluster {flag} is not true")

    shard_phase_count = summary.get("shard_movement_phase_count")
    required_phase_count = summary.get("shard_movement_required_phase_count")
    required_interruption_count = summary.get("shard_movement_required_interruption_phase_count")
    if not isinstance(shard_phase_count, int) or shard_phase_count <= 0:
        errors.append("gates.current_evidence.results mixed-cluster shard movement phase count is not positive")
    if shard_phase_count != MIXED_SHARD_MOVEMENT_PHASE_COUNT:
        errors.append(
            "gates.current_evidence.results mixed-cluster shard movement phase count "
            f"is not {MIXED_SHARD_MOVEMENT_PHASE_COUNT}"
        )
    if not isinstance(required_phase_count, int) or required_phase_count <= 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster required shard movement phase count is not positive"
        )
    elif required_phase_count != MIXED_SHARD_MOVEMENT_REQUIRED_PHASE_COUNT:
        errors.append(
            "gates.current_evidence.results mixed-cluster required shard movement phase count "
            f"is not {MIXED_SHARD_MOVEMENT_REQUIRED_PHASE_COUNT}"
        )
    elif isinstance(shard_phase_count, int) and shard_phase_count < required_phase_count:
        errors.append(
            "gates.current_evidence.results mixed-cluster shard movement phase count is below required count"
        )
    if not isinstance(required_interruption_count, int) or required_interruption_count <= 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster required interruption phase count is not positive"
        )
    elif required_interruption_count != MIXED_SHARD_MOVEMENT_REQUIRED_INTERRUPTION_PHASE_COUNT:
        errors.append(
            "gates.current_evidence.results mixed-cluster required interruption phase count "
            f"is not {MIXED_SHARD_MOVEMENT_REQUIRED_INTERRUPTION_PHASE_COUNT}"
        )
    if summary.get("shard_movement_missing_required_phase_count") != 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster missing required shard movement phase count is not zero"
        )
    if summary.get("shard_movement_phase_assertion_error_count") != 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster shard movement phase assertion error count is not zero"
        )
    if tuple(summary.get("shard_movement_phase_names") or ()) != MIXED_SHARD_MOVEMENT_PHASE_NAMES:
        errors.append(
            "gates.current_evidence.results mixed-cluster shard movement phase names do not match current baseline"
        )
    if summary.get("shard_movement_duplicate_required_phase_count") != 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster duplicate required shard movement phase count is not zero"
        )
    if tuple(summary.get("shard_movement_required_phases") or ()) != MIXED_SHARD_MOVEMENT_REQUIRED_PHASES:
        errors.append(
            "gates.current_evidence.results mixed-cluster required shard movement phases do not match current baseline"
        )
    if tuple(summary.get("shard_movement_required_interruption_phases") or ()) != MIXED_SHARD_MOVEMENT_REQUIRED_INTERRUPTION_PHASES:
        errors.append(
            "gates.current_evidence.results mixed-cluster required interruption phases do not match current baseline"
        )
    if summary.get("shard_movement_required_phase_fields") != {
        name: list(fields)
        for name, fields in MIXED_SHARD_MOVEMENT_REQUIRED_PHASE_FIELDS.items()
    }:
        errors.append(
            "gates.current_evidence.results mixed-cluster required shard movement phase fields do not match current baseline"
        )
    if tuple(summary.get("shard_movement_required_summary_flags") or ()) != MIXED_SHARD_MOVEMENT_REQUIRED_SUMMARY_FLAGS:
        errors.append(
            "gates.current_evidence.results mixed-cluster required shard movement summary flags do not match current baseline"
        )
    if summary.get("shard_movement_failed_required_summary_flag_count") != 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster failed required shard movement summary flag count is not zero"
        )
    if tuple(summary.get("publication_required_executed_tests") or ()) != MIXED_PUBLICATION_REQUIRED_EXECUTED_TESTS:
        errors.append(
            "gates.current_evidence.results mixed-cluster required publication executed tests do not match current baseline"
        )
    if tuple(summary.get("publication_report_names") or ()) != MIXED_PUBLICATION_REPORT_NAMES:
        errors.append(
            "gates.current_evidence.results mixed-cluster publication report names do not match current baseline"
        )
    if tuple(summary.get("publication_passed_report_names") or ()) != MIXED_PUBLICATION_REPORT_NAMES:
        errors.append(
            "gates.current_evidence.results mixed-cluster publication passed report names do not match current baseline"
        )
    if tuple(summary.get("publication_required_stages") or ()) != MIXED_PUBLICATION_REQUIRED_STAGES:
        errors.append(
            "gates.current_evidence.results mixed-cluster required publication stages do not match current baseline"
        )
    if tuple(summary.get("transport_admin_publication_validation_observed_events") or ()) != MIXED_TRANSPORT_ADMIN_PUBLICATION_VALIDATION_EVENTS:
        errors.append(
            "gates.current_evidence.results mixed-cluster transport admin publication validation events do not match current baseline"
        )
    if tuple(summary.get("transport_admin_remote_pit_cases") or ()) != MIXED_TRANSPORT_ADMIN_REMOTE_PIT_CASES:
        errors.append(
            "gates.current_evidence.results mixed-cluster transport admin remote PIT cases do not match current baseline"
        )
    if summary.get("transport_admin_remote_pit_semantic_error_count") != 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster transport admin remote PIT semantic error count is not zero"
        )

    expected_counts = (
        ("publication_report_count", MIXED_PUBLICATION_REPORT_COUNT),
        ("publication_passed_report_count", MIXED_PUBLICATION_REPORT_COUNT),
        ("publication_executed_test_count", MIXED_PUBLICATION_EXECUTED_TEST_COUNT),
        ("publication_required_executed_test_count", MIXED_PUBLICATION_EXECUTED_TEST_COUNT),
        ("publication_stage_count", MIXED_PUBLICATION_STAGE_COUNT),
        ("publication_required_stage_count", MIXED_PUBLICATION_STAGE_COUNT),
        ("transport_admin_remote_pit_case_count", MIXED_TRANSPORT_ADMIN_REMOTE_PIT_CASE_COUNT),
        (
            "transport_admin_publication_transcript_count",
            MIXED_TRANSPORT_ADMIN_PUBLICATION_TRANSCRIPT_COUNT,
        ),
        (
            "transport_admin_publication_validation_event_count",
            MIXED_TRANSPORT_ADMIN_PUBLICATION_VALIDATION_EVENT_COUNT,
        ),
    )
    for field, expected in expected_counts:
        if summary.get(field) != expected:
            errors.append(
                f"gates.current_evidence.results mixed-cluster {field} does not equal {expected}"
            )
    zero_counts = (
        "publication_missing_required_executed_test_count",
        "publication_missing_required_stage_count",
    )
    for field in zero_counts:
        if summary.get(field) != 0:
            errors.append(f"gates.current_evidence.results mixed-cluster {field} is not zero")
    if summary.get("transport_admin_passed") is not True:
        errors.append("gates.current_evidence.results mixed-cluster transport_admin_passed is not true")
    if summary.get("transport_admin_fresh") is not True:
        errors.append("gates.current_evidence.results mixed-cluster transport_admin_fresh is not true")
    if summary.get("transport_admin_age_checked") is not True:
        errors.append("gates.current_evidence.results mixed-cluster transport_admin_age_checked is not true")

    claim_boundary = summary.get("claim_boundary")
    required_claim_terms = (
        "mixed-cluster",
        "join",
        "movement",
        "publication",
        "allocation",
        "write-replication",
    )
    if not isinstance(claim_boundary, str) or any(
        term not in claim_boundary for term in required_claim_terms
    ):
        errors.append("gates.current_evidence.results mixed-cluster claim boundary is missing")
    return errors


def materialization_priority_errors(current: dict[str, Any]) -> list[str]:
    priority_result = None
    for result in current.get("results") or []:
        if not isinstance(result, dict):
            continue
        if (
            result.get("group") == "materialization-priority-current"
            and result.get("name")
            == "targeted_materialization_priority_report_has_zero_ranked_operations"
        ):
            priority_result = result
            break
    if priority_result is None:
        return ["gates.current_evidence.results materialization priority result is missing"]
    summary = priority_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results materialization priority summary is missing"]

    errors: list[str] = []
    errors.extend(current_result_envelope_errors(priority_result, "materialization priority"))
    if summary.get("passed") is not True:
        errors.append("gates.current_evidence.results materialization priority did not pass")
    if summary.get("ranked_operation_count") != 0:
        errors.append(
            "gates.current_evidence.results materialization priority ranked operation count is not zero"
        )
    if summary.get("priority_rows") != 0:
        errors.append(
            "gates.current_evidence.results materialization priority row count is not zero"
        )
    for field in (
        "observed_operation_count",
        "successful_operation_count",
        "counter_observed_operation_count",
    ):
        value = summary.get(field)
        if not isinstance(value, int) or value <= 0:
            errors.append(
                f"gates.current_evidence.results materialization priority {field} is not positive"
            )
        elif value != MATERIALIZATION_PRIORITY_OBSERVED_OPERATION_COUNT:
            errors.append(
                f"gates.current_evidence.results materialization priority {field} "
                f"is not {MATERIALIZATION_PRIORITY_OBSERVED_OPERATION_COUNT}"
            )
    return errors


def production_security_errors_for_current(current: dict[str, Any]) -> list[str]:
    security_result = None
    for result in current.get("results") or []:
        if not isinstance(result, dict):
            continue
        if (
            result.get("group") == "production-security-current"
            and result.get("name")
            == "production_security_batch_has_no_authn_authz_tls_or_fail_closed_regressions"
        ):
            security_result = result
            break
    if security_result is None:
        return ["gates.current_evidence.results production security result is missing"]
    summary = security_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results production security summary is missing"]

    errors: list[str] = []
    errors.extend(current_result_envelope_errors(security_result, "production security"))
    if summary.get("passed") is not True:
        errors.append("gates.current_evidence.results production security did not pass")
    if summary.get("batch") != "production-security":
        errors.append("gates.current_evidence.results production security batch mismatch")
    test_count = summary.get("test_count")
    if test_count != PRODUCTION_SECURITY_TEST_COUNT:
        errors.append(
            "gates.current_evidence.results production security test count "
            f"is not {PRODUCTION_SECURITY_TEST_COUNT}"
        )
    if summary.get("failed_count") != 0:
        errors.append("gates.current_evidence.results production security failed count is not zero")
    group_counts = summary.get("group_counts")
    if not isinstance(group_counts, dict):
        errors.append("gates.current_evidence.results production security group counts are missing")
    else:
        if summary.get("group_count") != len(PRODUCTION_SECURITY_GROUPS):
            errors.append(
                "gates.current_evidence.results production security group count "
                f"is not {len(PRODUCTION_SECURITY_GROUPS)}"
            )
        missing_groups = [group for group in PRODUCTION_SECURITY_GROUPS if group not in group_counts]
        if missing_groups:
            errors.append(
                "gates.current_evidence.results production security groups are missing: "
                + ", ".join(missing_groups)
            )
        mismatched_groups = [
            group
            for group, count in PRODUCTION_SECURITY_GROUPS.items()
            if group_counts.get(group) != count
        ]
        if mismatched_groups:
            errors.append(
                "gates.current_evidence.results production security group counts "
                "do not match current baseline: "
                + ", ".join(mismatched_groups)
            )
        counted_tests = sum(
            count for count in group_counts.values() if isinstance(count, int) and count > 0
        )
        if counted_tests != PRODUCTION_SECURITY_TEST_COUNT:
            errors.append(
                "gates.current_evidence.results production security grouped test count "
                f"is not {PRODUCTION_SECURITY_TEST_COUNT}"
            )
    return errors


def startup_bootstrap_errors(current: dict[str, Any]) -> list[str]:
    bootstrap_result = None
    for result in current.get("results") or []:
        if not isinstance(result, dict):
            continue
        if (
            result.get("group") == "startup-bootstrap-current"
            and result.get("name")
            == "startup_preflight_and_readiness_batches_have_no_bootstrap_or_readiness_regressions"
        ):
            bootstrap_result = result
            break
    if bootstrap_result is None:
        return ["gates.current_evidence.results startup bootstrap result is missing"]
    summary = bootstrap_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results startup bootstrap summary is missing"]

    errors: list[str] = []
    errors.extend(current_result_envelope_errors(bootstrap_result, "startup bootstrap"))
    if summary.get("passed") is not True:
        errors.append("gates.current_evidence.results startup bootstrap did not pass")
    batches = summary.get("batches")
    if not isinstance(batches, dict):
        errors.append("gates.current_evidence.results startup bootstrap batches are missing")
        return errors
    errors.extend(
        startup_batch_summary_errors(
            batches,
            "startup-preflight",
            STARTUP_PREFLIGHT_TEST_COUNT,
            STARTUP_PREFLIGHT_GROUPS,
        )
    )
    errors.extend(
        startup_batch_summary_errors(
            batches,
            "startup-readiness",
            STARTUP_READINESS_TEST_COUNT,
            STARTUP_READINESS_GROUPS,
        )
    )
    return errors


def startup_batch_summary_errors(
    batches: dict[str, Any],
    batch: str,
    expected_test_count: int,
    expected_group_counts: dict[str, int],
) -> list[str]:
    batch_summary = batches.get(batch)
    if not isinstance(batch_summary, dict):
        return [f"gates.current_evidence.results startup bootstrap {batch} summary is missing"]

    errors: list[str] = []
    test_count = batch_summary.get("test_count")
    if test_count != expected_test_count:
        errors.append(
            f"gates.current_evidence.results startup bootstrap {batch} test count "
            f"is not {expected_test_count}"
        )
    if batch_summary.get("failed_count") != 0:
        errors.append(
            f"gates.current_evidence.results startup bootstrap {batch} failed count is not zero"
        )
    if batch_summary.get("zero_test_count") != 0:
        errors.append(
            f"gates.current_evidence.results startup bootstrap {batch} zero-test count is not zero"
        )
    group_counts = batch_summary.get("group_counts")
    if not isinstance(group_counts, dict):
        errors.append(
            f"gates.current_evidence.results startup bootstrap {batch} group counts are missing"
        )
    else:
        if batch_summary.get("group_count") != len(expected_group_counts):
            errors.append(
                f"gates.current_evidence.results startup bootstrap {batch} group count "
                f"is not {len(expected_group_counts)}"
            )
        missing_groups = [
            group for group, count in expected_group_counts.items() if group_counts.get(group) != count
        ]
        if missing_groups:
            errors.append(
                f"gates.current_evidence.results startup bootstrap {batch} groups mismatch: "
                + ", ".join(missing_groups)
            )
        counted_tests = sum(
            count for count in group_counts.values() if isinstance(count, int) and count > 0
        )
        if counted_tests != expected_test_count:
            errors.append(
                f"gates.current_evidence.results startup bootstrap {batch} grouped test count "
                f"is not {expected_test_count}"
            )
    return errors


def release_evidence_inventory_errors(current: dict[str, Any]) -> list[str]:
    release_result = current_result(
        current,
        "release-evidence-inventory-current",
        "release_evidence_inventory_current_batch_has_complete_startup_and_readiness_artifacts",
    )
    if release_result is None:
        return ["gates.current_evidence.results release evidence inventory result is missing"]
    summary = release_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results release evidence inventory summary is missing"]

    errors: list[str] = []
    errors.extend(current_result_envelope_errors(release_result, "release evidence inventory"))
    if summary.get("passed") is not True:
        errors.append("gates.current_evidence.results release evidence inventory did not pass")
    if summary.get("batch") != "release-evidence-inventory-current":
        errors.append("gates.current_evidence.results release evidence inventory batch mismatch")
    test_count = summary.get("test_count")
    if test_count != RELEASE_EVIDENCE_INVENTORY_TEST_COUNT:
        errors.append(
            "gates.current_evidence.results release evidence inventory test count "
            f"is not {RELEASE_EVIDENCE_INVENTORY_TEST_COUNT}"
        )
    if tuple(summary.get("result_names") or ()) != RELEASE_EVIDENCE_INVENTORY_RESULT_NAMES:
        errors.append(
            "gates.current_evidence.results release evidence inventory result names "
            "do not match required current gate scripts"
        )
    if summary.get("failed_count") != 0:
        errors.append("gates.current_evidence.results release evidence inventory failed count is not zero")
    if summary.get("zero_test_count") != 0:
        errors.append("gates.current_evidence.results release evidence inventory zero-test count is not zero")
    if summary.get("promotion_checks") != PROMOTION_GATE_CHECK_COUNT:
        errors.append(
            "gates.current_evidence.results release evidence inventory promotion check count "
            f"is not {PROMOTION_GATE_CHECK_COUNT}"
        )
    if summary.get("promotion_failed") != 0:
        errors.append("gates.current_evidence.results release evidence inventory promotion failed count is not zero")
    if summary.get("inventory_complete") is not True:
        errors.append("gates.current_evidence.results release evidence inventory inventory is not complete")
    if summary.get("inventory_release_record_ready_item_count") != len(RELEASE_RECORD_ITEMS):
        errors.append(
            "gates.current_evidence.results release evidence inventory release record ready item count mismatch"
        )
    if summary.get("inventory_release_record_missing_items") != []:
        errors.append(
            "gates.current_evidence.results release evidence inventory release record missing items is not empty"
        )
    if summary.get("readiness_ready_items") != len(STARTUP_MANIFEST_ITEMS):
        errors.append("gates.current_evidence.results release evidence inventory readiness ready item count mismatch")
    if summary.get("readiness_required_items") != len(STARTUP_MANIFEST_ITEMS):
        errors.append(
            "gates.current_evidence.results release evidence inventory readiness required item count mismatch"
        )
    if summary.get("readiness_error_count") != 0:
        errors.append("gates.current_evidence.results release evidence inventory readiness error count is not zero")
    return errors


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


def runtime_controls_errors(current: dict[str, Any]) -> list[str]:
    runtime_result = current_result(
        current,
        "runtime-controls-current",
        "runtime_control_batches_have_no_queue_backpressure_fairness_or_lifecycle_regressions",
    )
    if runtime_result is None:
        return ["gates.current_evidence.results runtime controls result is missing"]
    summary = runtime_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results runtime controls summary is missing"]

    errors: list[str] = []
    errors.extend(current_result_envelope_errors(runtime_result, "runtime controls"))
    if summary.get("passed") is not True:
        errors.append("gates.current_evidence.results runtime controls did not pass")
    if summary.get("failed_batches") != []:
        errors.append("gates.current_evidence.results runtime controls failed_batches is not empty")
    batches = summary.get("batches")
    if not isinstance(batches, dict):
        errors.append("gates.current_evidence.results runtime controls batches are missing")
        return errors
    for batch, expected_test_count in RUNTIME_CONTROL_BATCH_COUNTS.items():
        errors.extend(runtime_control_batch_errors(batches, batch, expected_test_count))
    return errors


def runtime_control_batch_errors(
    batches: dict[str, Any],
    batch: str,
    expected_test_count: int,
) -> list[str]:
    batch_summary = batches.get(batch)
    if not isinstance(batch_summary, dict):
        return [f"gates.current_evidence.results runtime controls {batch} summary is missing"]

    errors: list[str] = []
    if batch_summary.get("returncode") != 0:
        errors.append(
            f"gates.current_evidence.results runtime controls {batch} returncode is not zero"
        )
    test_count = batch_summary.get("test_count")
    if test_count != expected_test_count:
        errors.append(
            f"gates.current_evidence.results runtime controls {batch} test count "
            f"is not {expected_test_count}"
        )
    if batch_summary.get("failed_count") != 0:
        errors.append(
            f"gates.current_evidence.results runtime controls {batch} failed count is not zero"
        )
    if batch_summary.get("zero_test_count") != 0:
        errors.append(
            f"gates.current_evidence.results runtime controls {batch} zero-test count is not zero"
        )
    failed_cases = batch_summary.get("failed_cases")
    if not isinstance(failed_cases, list) or failed_cases:
        errors.append(
            f"gates.current_evidence.results runtime controls {batch} failed_cases is not empty"
        )
    return errors


def release_readiness_tooling_errors(current: dict[str, Any]) -> list[str]:
    tooling_result = current_result(
        current,
        "release-readiness-tooling",
        "release_readiness_writer_and_manifest_checker_contract",
    )
    if tooling_result is None:
        return ["gates.current_evidence.results release readiness tooling result is missing"]
    summary = tooling_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results release readiness tooling summary is missing"]

    errors: list[str] = []
    errors.extend(current_result_envelope_errors(tooling_result, "release readiness tooling"))
    if summary.get("passed") is not True:
        errors.append("gates.current_evidence.results release readiness tooling did not pass")
    commands = summary.get("commands")
    if commands != RELEASE_READINESS_TOOLING_COMMAND_COUNT:
        errors.append(
            "gates.current_evidence.results release readiness tooling command count "
            f"is not {RELEASE_READINESS_TOOLING_COMMAND_COUNT}"
        )
    command_names = summary.get("command_names")
    if tuple(command_names or ()) != RELEASE_READINESS_TOOLING_COMMAND_NAMES:
        errors.append(
            "gates.current_evidence.results release readiness tooling command names "
            "do not match required current gate scripts"
        )
    return errors


def current_result(current: dict[str, Any], group: str, name: str) -> dict[str, Any] | None:
    for result in current.get("results") or []:
        if not isinstance(result, dict):
            continue
        if result.get("group") == group and result.get("name") == name:
            return result
    return None


def current_result_envelope_errors(result: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    if result.get("ok") is not True:
        errors.append(f"gates.current_evidence.results {label} result is not ok")
    if result.get("status") != "ok":
        errors.append(f"gates.current_evidence.results {label} status is not ok")
    if result.get("returncode") != 0:
        errors.append(f"gates.current_evidence.results {label} returncode is not zero")
    return errors


def source_compatibility_errors_for_current(current: dict[str, Any]) -> list[str]:
    source_result = current_result(
        current,
        "source-compatibility-current",
        "source_compatibility_matrix_has_no_open_or_unmapped_gaps",
    )
    if source_result is None:
        return ["gates.current_evidence.results source compatibility result is missing"]
    summary = source_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results source compatibility summary is missing"]

    errors = current_result_envelope_errors(source_result, "source compatibility")
    if summary.get("passed") is not True:
        errors.append("gates.current_evidence.results source compatibility did not pass")
    expected_counts = (
        ("matrix_row_count", SOURCE_COMPATIBILITY_MATRIX_ROW_COUNT),
        ("closed_row_count", SOURCE_COMPATIBILITY_CLOSED_ROW_COUNT),
    )
    for field, expected in expected_counts:
        if summary.get(field) != expected:
            errors.append(
                f"gates.current_evidence.results source compatibility {field} "
                f"is not {expected}"
            )
    for field in ("open_gap_row_count", "unmapped_gap_count"):
        if summary.get(field) != 0:
            errors.append(
                f"gates.current_evidence.results source compatibility {field} is not zero"
            )
    if summary.get("open_gap_counts") != {}:
        errors.append(
            "gates.current_evidence.results source compatibility open_gap_counts is not empty"
        )
    return errors


def runtime_peer_backpressure_errors(peer: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if tuple(peer.get("command") or ()) != RUNTIME_PEER_BACKPRESSURE_COMMAND:
        errors.append("gates.runtime_peer_backpressure_current.command does not match current baseline")
    if peer.get("returncode") != 0:
        errors.append("gates.runtime_peer_backpressure_current.returncode is not zero")
    peer_groups = peer.get("groups")
    if not isinstance(peer_groups, dict):
        errors.append("gates.runtime_peer_backpressure_current.groups is missing")
    else:
        group_status = peer_groups.get(RUNTIME_PEER_BACKPRESSURE_GROUP)
        if not isinstance(group_status, dict):
            errors.append(
                "gates.runtime_peer_backpressure_current runtime fairness group is missing"
            )
        else:
            if group_status.get("ok") is not True:
                errors.append(
                    "gates.runtime_peer_backpressure_current runtime fairness group is not ok"
                )
            if group_status.get("status") != "ok":
                errors.append(
                    "gates.runtime_peer_backpressure_current runtime fairness group status is not ok"
                )
            if group_status.get("returncode") != 0:
                errors.append(
                    "gates.runtime_peer_backpressure_current runtime fairness group returncode is not zero"
                )
    summary = peer.get("summary")
    if not isinstance(summary, dict):
        errors.append("gates.runtime_peer_backpressure_current.summary is missing")
    else:
        if summary.get("batch") != "runtime-peer-backpressure-current":
            errors.append("gates.runtime_peer_backpressure_current.summary.batch mismatch")
        if summary.get("test_count") != 1:
            errors.append("gates.runtime_peer_backpressure_current.summary.test_count is not 1")
        if summary.get("passed_count") != 1:
            errors.append("gates.runtime_peer_backpressure_current.summary.passed_count is not 1")
        if summary.get("failed_count") != 0:
            errors.append("gates.runtime_peer_backpressure_current.summary.failed_count is not zero")
        if summary.get("zero_test_count") != 0:
            errors.append("gates.runtime_peer_backpressure_current.summary.zero_test_count is not zero")

    peer_result = current_result(
        peer,
        "runtime-fairness-peer-backpressure-current",
        "runtime_peer_backpressure_current_report_preserves_profile_and_counters",
    )
    if peer_result is None:
        errors.append("gates.runtime_peer_backpressure_current result is missing")
        return errors
    if peer_result.get("ok") is not True:
        errors.append("gates.runtime_peer_backpressure_current result is not ok")
    if peer_result.get("status") != "ok":
        errors.append("gates.runtime_peer_backpressure_current result status is not ok")
    if peer_result.get("returncode") != 0:
        errors.append("gates.runtime_peer_backpressure_current result returncode is not zero")
    result_summary = peer_result.get("summary")
    if not isinstance(result_summary, dict):
        errors.append("gates.runtime_peer_backpressure_current result summary is missing")
        return errors
    if result_summary.get("passed") is not True:
        errors.append("gates.runtime_peer_backpressure_current result did not pass")
    if result_summary.get("profile") != "mixed-java-rust-query-phase":
        errors.append("gates.runtime_peer_backpressure_current profile mismatch")
    for field in (
        "steelsearch_rejected",
        "steelsearch_completed",
        "opensearch_rejected",
        "opensearch_completed",
        "opensearch_http_429_count",
    ):
        value = result_summary.get(field)
        if not isinstance(value, int) or value < 1:
            errors.append(f"gates.runtime_peer_backpressure_current {field} is not positive")
    return errors


if __name__ == "__main__":
    sys.exit(main())
