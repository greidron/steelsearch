import importlib.util
import sys
import unittest
from copy import deepcopy
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
    "source-compatibility-current",
]
CURRENT_RESULTS = (
    ("non-native-inventory", "non_native_path_inventory_has_no_missing_probe_or_family"),
    (
        "e2e-required-parity",
        "search_semantic_and_vector_search_e2e_reports_have_no_failed_missing_or_skipped_cases",
    ),
    (
        "e2e-search-compat-parity",
        "search_compat_and_strict_e2e_reports_have_no_failed_or_missing_cases",
    ),
    (
        "e2e-search-compat-parity",
        "pit_e2e_reports_have_required_opensearch_compared_cases_without_skips",
    ),
    (
        "e2e-broad-parity",
        "broad_unified_opensearch_e2e_report_has_no_failed_missing_or_drifted_required_suites",
    ),
    (
        "rest-api-coverage-current",
        "rest_api_source_inventory_coverage_is_reported_for_broad_required_live_suites",
    ),
    (
        "transport-action-coverage-current",
        "transport_action_inventory_is_reported_with_current_peer_backpressure_evidence",
    ),
    (
        "mixed-cluster-coverage-current",
        "mixed_cluster_join_and_movement_coverage_is_reported_with_scope_boundary",
    ),
    (
        "mixed-cluster-coverage-current",
        "multi_node_transport_admin_report_requires_remote_pit_forwarding_cases",
    ),
    (
        "materialization-priority-current",
        "targeted_materialization_priority_report_has_zero_ranked_operations",
    ),
    (
        "production-security-current",
        "production_security_batch_has_no_authn_authz_tls_or_fail_closed_regressions",
    ),
    (
        "startup-bootstrap-current",
        "startup_preflight_and_readiness_batches_have_no_bootstrap_or_readiness_regressions",
    ),
    (
        "runtime-controls-current",
        "runtime_control_batches_have_no_queue_backpressure_fairness_or_lifecycle_regressions",
    ),
    (
        "release-evidence-inventory-current",
        "release_evidence_inventory_current_batch_has_complete_startup_and_readiness_artifacts",
    ),
    (
        "release-readiness-tooling",
        "release_readiness_writer_and_manifest_checker_contract",
    ),
    (
        "source-compatibility-current",
        "source_compatibility_matrix_has_no_open_or_unmapped_gaps",
    ),
)
RELEASE_READINESS_TOOLING_COMMAND_NAMES = (
    "tools/test_replacement_gate_scripts.py",
    "tools/check-e2e-doc-current-counts.py",
    "tools/check-source-compatibility-drift.sh",
)
RELEASE_READINESS_TOOLING_COMMAND_SPECS = (
    "python -m unittest tools/test_replacement_gate_scripts.py",
    "python tools/check-e2e-doc-current-counts.py",
    "tools/check-source-compatibility-drift.sh",
)
RELEASE_READINESS_TOOLING_COMMAND_SPEC_DIGEST = (
    "6caeb0ed7743852c9412e005953370dabb141f6604b07d344d0ceecf9e95a0a2"
)
MATERIALIZATION_PRIORITY_OPERATION_NAMES = ("fallback_query_string",)
TRANSPORT_SOURCE_IMPLEMENTED_ACTION_NAME_DIGEST = (
    "5450a12b7cdad6e631ff87a953b7779c4e65e0800d79b672812a65de7336e290"
)
TRANSPORT_EVIDENCE_ACTION_NAME_DIGEST = (
    "9e3236a43431ed6ed6098d7f14c8deada7c6aaf060d914f0d47041ed88fdca17"
)
REST_SOURCE_ROUTE_KEY_DIGEST = (
    "37eb92f02b22dff2148de748707e601534e365d81302211534a6e0d41e5333e2"
)
REST_IN_SCOPE_SOURCE_ROUTE_KEY_DIGEST = (
    "86fc1075a36e70dc38a22e4ccfa897113871c2b1524f205d26965e7e79fa5a74"
)
PIT_CASE_NAME_DIGEST = (
    "3ffad0a3ed3007c6c7d82339681afc153fc802554536947788ba11a18601d1ad"
)
PIT_REQUIRED_CASE_NAME_DIGEST = (
    "b5bf252eddbd24c84ebb13ee5a5e6f23c6dd2a6328ca4475398c816a9888743d"
)
SOURCE_COMPATIBILITY_MATRIX_ROW_COUNT = 768
SOURCE_COMPATIBILITY_CLOSED_ROW_COUNT = 768
SOURCE_COMPATIBILITY_MATRIX_ROW_DIGEST = (
    "381be535a30339e76540ab05b5b62c99ecff6be587dbd7e8788c62cec46f3808"
)
NON_NATIVE_PROBE_NAME_DIGEST = (
    "bcb9e4edbae52a4c3109dcc02c14bda169024f8a916757c5953a96771be2ff52"
)
NON_NATIVE_FAMILY_NAME_DIGEST = (
    "bc936653bc5aeddf726b27a558e215afc2ef53d08b1eed4e1caafd824c87dec7"
)
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
MIXED_CLUSTER_MAX_AGE_SECONDS = 5184000.0
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
MIXED_PHASE_C_REQUIRED_EXECUTED_TESTS_BY_NAME = {
    "allocation": (
        "mixed_cluster_allocation_fail_closed_fixture_matches_validator_behavior",
        "mixed_cluster_allocation_routing_convergence_probe",
    ),
    "bounded_recovery_probe": ("bounded_peer_recovery_wire_round_trip_probe",),
    "failure": (
        "daemon_point_in_time_contexts_do_not_survive_restart",
        "daemon_transport_point_in_time_contexts_do_not_survive_restart",
        "multi_daemon_get_all_pits_fans_out_to_seed_peers",
    ),
    "join": (
        "mixed_cluster_join_reject_fixture_matches_validator_behavior",
        "mixed_cluster_live_join_probe",
    ),
    "live_join_probe": ("mixed_cluster_live_join_probe",),
    "publication": (
        "periodic_liveness_catches_up_reachable_lagging_publication_follower_before_retry",
        "periodic_liveness_schedules_node_left_publication_retry_before_fencing_manager",
        "publication_diff_apply_acknowledges_only_after_successful_apply",
        "publication_full_state_receive_apply_replaces_local_cache",
        "publication_reject_integration_preserves_cache_and_withholds_ack",
        "repeated_publication_diff_apply_requires_monotonic_versions_before_ack",
    ),
    "recovery": (
        "bounded_peer_recovery_wire_round_trip_probe",
        "mixed_cluster_recovery_fail_closed_fixture_matches_validator_behavior",
    ),
    "write_replication": (
        "mixed_cluster_write_replication_fail_closed_fixture_matches_validation_behavior",
        "replica_operation_tcp_round_trip_preserves_replication_progress_metadata",
    ),
}
MIXED_FAILURE_NODE_LOSS_REPORT_NAMES = (
    "failure_java_node_loss",
    "failure_steelsearch_node_loss_publication",
    "failure_steelsearch_node_loss_recovery",
)
RELEASE_EVIDENCE_INVENTORY_RESULT_NAMES = (
    "release_evidence_inventory_generates_promotion_gate_suite_artifact",
    "release_evidence_inventory_reports_current_candidate_artifacts",
    "release_evidence_inventory_writes_and_checks_final_cutover_manifest",
)
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
PROMOTION_GATE_CHECK_NAMES = (
    "source-compatibility-drift",
    "source-compatibility-closure",
    "root-identity",
    "index-metadata",
    "document-write",
    "bulk",
    "cluster-admin",
    "search",
    "pit-e2e-coverage",
    "snapshot",
    "vector",
    "knn-plugin",
    "ml",
    "benchmark-evidence",
    "peer-node",
    "security-row-reclassification",
    "transport-action-coverage",
    "broad-unified-e2e-sections",
    "rest-api-live-source-coverage",
    "e2e-doc-current-counts",
    "runtime-control-surface-inventory",
    "mixed-cluster-coverage",
    "external-interop",
    "migration",
    "harness",
    "release-evidence-inventory",
)
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
REST_SOURCE_STATUS_COUNTS = {
    "implemented": 378,
    "out-of-scope": 11,
}
REST_FIXTURE_ROUTE_COUNT = 3629
REST_LIVE_REQUIRED_FIXTURE_ROUTE_COUNT = 3489
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
E2E_CLASSIFICATION_CASE_NAME_DIGESTS = {
    "required": "a6cf27ff0f18840ae46e325675fc5b9ce1be2f6e0eed5c27bc1f3284fbcf7b96",
    "compat": "f45ddf92470930a0036ce7bc1849952049d7c7fffb1a3371213e205513cf59fa",
    "broad": "f6ea96092a9195ef2a071e5da6e6085c7f3955d0a6389d92ea0a191b1e18453d",
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
E2E_CLASSIFICATION_BASELINES = {
    "required": {
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
    "compat": {
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
TRANSPORT_ACCEPTED_EVIDENCE_SCOPE_COUNTS = {
    "bounded_local_subset": 170,
    "bounded_seed_peer_fanout_subset": 4,
}
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
PRODUCTION_SECURITY_TEST_NAME_DIGEST = (
    "033eee3de6d210231e3ce189c55ba7e30bd1955aaa519bf6f3a58dadb046c2bf"
)
STARTUP_PREFLIGHT_TEST_NAME_DIGEST = (
    "115b9c703a9875d1088bc39e4476231b1aa7f145355075ac116cfc398e911d3b"
)
STARTUP_READINESS_TEST_NAME_DIGEST = (
    "4efc36ef2d95571b641aa09bad1e100342c86c59c57a6e84df440a430bb1ab1a"
)


def non_native_inventory_result(
    *,
    ok: bool = True,
    status: str = "ok",
    returncode: int = 0,
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
    required = (
        list(NON_NATIVE_REQUIRED_CATEGORIES)
        if required_categories is None
        else required_categories
    )
    covered = (
        list(NON_NATIVE_COVERED_CATEGORIES)
        if covered_categories is None
        else covered_categories
    )
    return {
        "group": "non-native-inventory",
        "name": "non_native_path_inventory_has_no_missing_probe_or_family",
        "ok": ok,
        "returncode": returncode,
        "status": status,
        "summary": {
            "covered_categories": covered,
            "evidenced_family_count": evidenced_family_count,
            "evidenced_family_name_digest": NON_NATIVE_FAMILY_NAME_DIGEST,
            "family_count": family_count,
            "family_name_digest": NON_NATIVE_FAMILY_NAME_DIGEST,
            "matched_probe_count": matched_probe_count,
            "matched_probe_name_digest": NON_NATIVE_PROBE_NAME_DIGEST,
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
            "probe_name_digest": NON_NATIVE_PROBE_NAME_DIGEST,
            "required_categories": required,
        },
    }


def materialization_priority_result(
    *,
    passed: bool = True,
    ok: bool | None = None,
    status: str | None = None,
    returncode: int | None = None,
    ranked_operation_count: int = 0,
    priority_rows: int = 0,
    observed_operation_count: int = 1,
    successful_operation_count: int = 1,
    counter_observed_operation_count: int = 1,
    operation_names: tuple[str, ...] = MATERIALIZATION_PRIORITY_OPERATION_NAMES,
):
    return {
        "group": "materialization-priority-current",
        "name": "targeted_materialization_priority_report_has_zero_ranked_operations",
        "ok": passed if ok is None else ok,
        "returncode": (0 if passed else 1) if returncode is None else returncode,
        "status": ("ok" if passed else "failed") if status is None else status,
        "summary": {
            "allow_empty": True,
            "counter_observed_operation_count": counter_observed_operation_count,
            "counter_observed_operation_names": list(operation_names),
            "observed_operation_count": observed_operation_count,
            "observed_operation_names": list(operation_names),
            "passed": passed,
            "priority_rows": priority_rows,
            "ranked_operation_count": ranked_operation_count,
            "successful_operation_count": successful_operation_count,
            "successful_operation_names": list(operation_names),
            "top_family": None,
            "top_operation": None,
        },
    }


def production_security_result(
    *,
    passed: bool = True,
    ok: bool | None = None,
    status: str | None = None,
    returncode: int | None = None,
    batch: str = "production-security",
    test_count: int = 34,
    failed_count: int = 0,
    test_name_count: int = 34,
    test_name_digest: str = PRODUCTION_SECURITY_TEST_NAME_DIGEST,
    group_counts: dict[str, int] | None = None,
    group_count: int | None = None,
):
    counts = group_counts if group_counts is not None else PRODUCTION_SECURITY_GROUPS
    return {
        "group": "production-security-current",
        "name": "production_security_batch_has_no_authn_authz_tls_or_fail_closed_regressions",
        "ok": passed if ok is None else ok,
        "returncode": (0 if passed else 1) if returncode is None else returncode,
        "status": ("ok" if passed else "failed") if status is None else status,
        "summary": {
            "batch": batch,
            "failed_count": failed_count,
            "group_count": len(counts) if group_count is None else group_count,
            "group_counts": counts,
            "passed": passed,
            "test_count": test_count,
            "test_name_count": test_name_count,
            "test_name_digest": test_name_digest,
        },
    }


def startup_bootstrap_result(
    *,
    passed: bool = True,
    ok: bool | None = None,
    status: str | None = None,
    returncode: int | None = None,
    preflight_test_count: int = 35,
    preflight_failed_count: int = 0,
    preflight_zero_test_count: int = 0,
    preflight_test_name_count: int = 35,
    preflight_test_name_digest: str = STARTUP_PREFLIGHT_TEST_NAME_DIGEST,
    preflight_group_counts: dict[str, int] | None = None,
    preflight_group_count: int | None = None,
    readiness_test_count: int = 3,
    readiness_failed_count: int = 0,
    readiness_zero_test_count: int = 0,
    readiness_test_name_count: int = 3,
    readiness_test_name_digest: str = STARTUP_READINESS_TEST_NAME_DIGEST,
    readiness_group_counts: dict[str, int] | None = None,
    readiness_group_count: int | None = None,
):
    preflight_counts = preflight_group_counts if preflight_group_counts is not None else {
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
    readiness_counts = readiness_group_counts if readiness_group_counts is not None else {
        "startup-readiness-shared-blockers": 2,
        "startup-readiness-terminology": 1,
    }
    return {
        "group": "startup-bootstrap-current",
        "name": (
            "startup_preflight_and_readiness_batches_have_no_bootstrap_or_readiness_regressions"
        ),
        "ok": passed if ok is None else ok,
        "returncode": (0 if passed else 1) if returncode is None else returncode,
        "status": ("ok" if passed else "failed") if status is None else status,
        "summary": {
            "passed": passed,
            "batches": {
                "startup-preflight": {
                    "failed_count": preflight_failed_count,
                    "group_count": len(preflight_counts)
                    if preflight_group_count is None
                    else preflight_group_count,
                    "group_counts": preflight_counts,
                    "test_count": preflight_test_count,
                    "test_name_count": preflight_test_name_count,
                    "test_name_digest": preflight_test_name_digest,
                    "zero_test_count": preflight_zero_test_count,
                },
                "startup-readiness": {
                    "failed_count": readiness_failed_count,
                    "group_count": len(readiness_counts)
                    if readiness_group_count is None
                    else readiness_group_count,
                    "group_counts": readiness_counts,
                    "test_count": readiness_test_count,
                    "test_name_count": readiness_test_name_count,
                    "test_name_digest": readiness_test_name_digest,
                    "zero_test_count": readiness_zero_test_count,
                },
            },
        },
    }


def release_evidence_inventory_result(
    *,
    passed: bool = True,
    ok: bool | None = None,
    status: str | None = None,
    returncode: int | None = None,
    batch: str = "release-evidence-inventory-current",
    test_count: int = 3,
    failed_count: int = 0,
    zero_test_count: int = 0,
    promotion_checks: int = 26,
    promotion_failed: int = 0,
    promotion_check_names: list[str] | None = None,
    promotion_passed_check_names: list[str] | None = None,
    promotion_failed_check_names: list[str] | None = None,
    inventory_complete: bool = True,
    inventory_startup_ready_items: list[str] | None = None,
    inventory_readiness_attachment_ready_items: list[str] | None = None,
    inventory_release_record_ready_items: list[str] | None = None,
    inventory_release_record_ready_item_count: int = 8,
    inventory_release_record_missing_items: list[str] | None = None,
    readiness_ready_items: int = 5,
    readiness_ready_item_names: list[str] | None = None,
    readiness_required_items: int = 5,
    readiness_error_count: int = 0,
    result_names: list[str] | None = None,
):
    return {
        "group": "release-evidence-inventory-current",
        "name": "release_evidence_inventory_current_batch_has_complete_startup_and_readiness_artifacts",
        "ok": passed if ok is None else ok,
        "returncode": (0 if passed else 1) if returncode is None else returncode,
        "status": ("ok" if passed else "failed") if status is None else status,
        "summary": {
            "batch": batch,
            "failed_count": failed_count,
            "inventory_complete": inventory_complete,
            "inventory_release_record_missing_items": (
                inventory_release_record_missing_items
                if inventory_release_record_missing_items is not None
                else []
            ),
            "inventory_startup_ready_items": (
                inventory_startup_ready_items
                if inventory_startup_ready_items is not None
                else list(STARTUP_MANIFEST_ITEMS)
            ),
            "inventory_readiness_attachment_ready_items": (
                inventory_readiness_attachment_ready_items
                if inventory_readiness_attachment_ready_items is not None
                else list(READINESS_ATTACHMENT_ITEMS)
            ),
            "inventory_release_record_ready_items": (
                inventory_release_record_ready_items
                if inventory_release_record_ready_items is not None
                else list(RELEASE_RECORD_ITEMS)
            ),
            "inventory_release_record_ready_item_count": inventory_release_record_ready_item_count,
            "passed": passed,
            "promotion_checks": promotion_checks,
            "promotion_failed": promotion_failed,
            "promotion_check_names": (
                promotion_check_names
                if promotion_check_names is not None
                else list(PROMOTION_GATE_CHECK_NAMES)
            ),
            "promotion_passed_check_names": (
                promotion_passed_check_names
                if promotion_passed_check_names is not None
                else list(PROMOTION_GATE_CHECK_NAMES)
            ),
            "promotion_failed_check_names": (
                promotion_failed_check_names
                if promotion_failed_check_names is not None
                else []
            ),
            "readiness_error_count": readiness_error_count,
            "readiness_ready_item_names": (
                readiness_ready_item_names
                if readiness_ready_item_names is not None
                else list(STARTUP_MANIFEST_ITEMS)
            ),
            "readiness_ready_items": readiness_ready_items,
            "readiness_required_items": readiness_required_items,
            "result_names": (
                result_names
                if result_names is not None
                else list(RELEASE_EVIDENCE_INVENTORY_RESULT_NAMES)
            ),
            "test_count": test_count,
            "zero_test_count": zero_test_count,
        },
    }


def release_readiness_tooling_result(
    *,
    passed: bool = True,
    ok: bool | None = None,
    status: str | None = None,
    returncode: int | None = None,
    commands: int = 3,
    command_names: list[str] | None = None,
    command_specs: list[str] | None = None,
    command_spec_digest: str = RELEASE_READINESS_TOOLING_COMMAND_SPEC_DIGEST,
):
    return {
        "group": "release-readiness-tooling",
        "name": "release_readiness_writer_and_manifest_checker_contract",
        "ok": passed if ok is None else ok,
        "returncode": (0 if passed else 1) if returncode is None else returncode,
        "status": ("ok" if passed else "failed") if status is None else status,
        "summary": {
            "command_names": (
                command_names
                if command_names is not None
                else list(RELEASE_READINESS_TOOLING_COMMAND_NAMES)
            ),
            "command_spec_digest": command_spec_digest,
            "command_specs": (
                command_specs
                if command_specs is not None
                else list(RELEASE_READINESS_TOOLING_COMMAND_SPECS)
            ),
            "commands": commands,
            "passed": passed,
        },
    }


def source_compatibility_result(
    *,
    passed: bool = True,
    ok: bool | None = None,
    status: str | None = None,
    returncode: int | None = None,
    matrix_row_count: int = SOURCE_COMPATIBILITY_MATRIX_ROW_COUNT,
    closed_row_count: int = SOURCE_COMPATIBILITY_CLOSED_ROW_COUNT,
    open_gap_row_count: int = 0,
    unmapped_gap_count: int = 0,
    open_gap_counts: dict[str, dict[str, int]] | None = None,
):
    return {
        "group": "source-compatibility-current",
        "name": "source_compatibility_matrix_has_no_open_or_unmapped_gaps",
        "ok": passed if ok is None else ok,
        "returncode": (0 if passed else 1) if returncode is None else returncode,
        "status": ("ok" if passed else "failed") if status is None else status,
        "summary": {
            "closed_row_count": closed_row_count,
            "closed_row_digest": SOURCE_COMPATIBILITY_MATRIX_ROW_DIGEST,
            "matrix_row_count": matrix_row_count,
            "matrix_row_digest": SOURCE_COMPATIBILITY_MATRIX_ROW_DIGEST,
            "open_gap_counts": {} if open_gap_counts is None else open_gap_counts,
            "open_gap_row_count": open_gap_row_count,
            "passed": passed,
            "unmapped_gap_count": unmapped_gap_count,
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
RUNTIME_CONTROL_BATCH_NAME_DIGESTS = {
    "runtime-tasks": "bc7d4dd06e0791aa982ab3b978cbab2b51e9c694d3b2df7b98ec847d41854ad2",
    "runtime-queue": "16ae1f1caca6565be1fa6e8b2185013986cfacb071569fe988374e158d37be04",
    "runtime-backpressure": "ba9efcc7c16feccb1387a1a32f44355608e0b0c9223cd3c56061821b60245ed0",
    "runtime-fairness": "7ef52d43b751adaac8f797c301067f75545c960e15204939f702d75208ec2963",
    "runtime-throttle": "0581bc50e4980f5533222db40a2f31bd9a751a10788d3dadb2ac4541bd3537c0",
    "runtime-task-metadata": "e36d9ce9f1717becaf2a7cb360ddbbddc93819c2f8b2aec4f1c31ca12f6ec7fc",
    "runtime-task-headers": "ed397b78ae77258e15cae109ca1b695b8c9c4a0c0bad25d29b5ca795551f2796",
    "runtime-task-children": "e669f7d2e27416db0827df1d5f93760ceecf7d3fa0402285c4ae271d0d1328a2",
    "runtime-lifecycle": "40cc49b883558a990d9011bfd089e5510603967a52274fb9db405ef63d70f624",
    "module-registration": "71ae54d9c77deacf7b88ff5fddf8fa91a8dbf8864804f7d48963d6706ab78d22",
}


def runtime_controls_result(
    *,
    passed: bool = True,
    ok: bool | None = None,
    status: str | None = None,
    returncode: int | None = None,
    failed_batches: list[str] | None = None,
    overrides: dict[str, dict] | None = None,
):
    batches = {
        batch: {
            "failed_cases": [],
            "failed_count": 0,
            "returncode": 0,
            "test_count": test_count,
            "test_name_count": test_count,
            "test_name_digest": RUNTIME_CONTROL_BATCH_NAME_DIGESTS[batch],
            "zero_test_count": 0,
        }
        for batch, test_count in RUNTIME_CONTROL_BATCH_COUNTS.items()
    }
    for batch, patch in (overrides or {}).items():
        batches[batch] = {**batches[batch], **patch}
    return {
        "group": "runtime-controls-current",
        "name": "runtime_control_batches_have_no_queue_backpressure_fairness_or_lifecycle_regressions",
        "ok": passed if ok is None else ok,
        "returncode": (0 if passed else 1) if returncode is None else returncode,
        "status": ("ok" if passed else "failed") if status is None else status,
        "summary": {
            "batches": batches,
            "failed_batches": failed_batches if failed_batches is not None else [],
            "passed": passed,
        },
    }


def runtime_peer_backpressure_gate(
    *,
    passed: bool = True,
    command: list[str] | None = None,
    top_returncode: int | None = None,
    group_ok: bool | None = None,
    group_status: str | None = None,
    group_returncode: int | None = None,
    result_ok: bool | None = None,
    result_status: str | None = None,
    result_returncode: int | None = None,
    batch: str = "runtime-peer-backpressure-current",
    test_count: int = 1,
    passed_count: int | None = None,
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
        "command": (
            command
            if command is not None
            else [
                "/usr/bin/python3",
                "tools/run-native-closure-validation.py",
                "--batch",
                "runtime-peer-backpressure-current",
                "--format",
                "json",
            ]
        ),
        "returncode": (0 if passed else 1) if top_returncode is None else top_returncode,
        "summary": {
            "batch": batch,
            "failed_count": failed_count,
            "passed_count": (1 if passed else 0) if passed_count is None else passed_count,
            "test_count": test_count,
            "zero_test_count": zero_test_count,
        },
        "groups": {
            "runtime-fairness-peer-backpressure-current": {
                "ok": passed if group_ok is None else group_ok,
                "returncode": (
                    0 if passed else 1
                ) if group_returncode is None else group_returncode,
                "status": ("ok" if passed else "failed") if group_status is None else group_status,
            }
        },
        "results": [
            {
                "group": "runtime-fairness-peer-backpressure-current",
                "name": "runtime_peer_backpressure_current_report_preserves_profile_and_counters",
                "ok": passed if result_ok is None else result_ok,
                "returncode": (
                    0 if passed else 1
                ) if result_returncode is None else result_returncode,
                "status": ("ok" if passed else "failed") if result_status is None else result_status,
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
    ok: bool = True,
    status: str = "ok",
    returncode: int = 0,
    passed: bool = True,
    peer_backpressure_passed: bool = True,
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
        "passed": passed,
        "peer_backpressure_passed": peer_backpressure_passed,
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
        "source_implemented_action_name_digest": TRANSPORT_SOURCE_IMPLEMENTED_ACTION_NAME_DIGEST,
        "accepted_evidence_action_name_digest": TRANSPORT_EVIDENCE_ACTION_NAME_DIGEST,
        "release_evidence_action_name_digest": TRANSPORT_EVIDENCE_ACTION_NAME_DIGEST,
        "accepted_evidence_action_binding_error_count": 0,
        "accepted_evidence_pointer_test_error_count": 0,
        "accepted_evidence_request_semantic_error_count": 0,
        "accepted_evidence_response_semantic_error_count": 0,
        "accepted_evidence_shared_pointer_error_count": 0,
        "release_evidence_action_binding_error_count": 0,
        "release_evidence_pointer_test_error_count": 0,
        "release_evidence_request_semantic_error_count": 0,
        "release_evidence_response_semantic_error_count": 0,
        "release_evidence_shared_pointer_error_count": 0,
        "partial_action_count": partial_count,
        "planned_action_count": planned_count,
        "stubbed_action_count": stubbed_count,
        "out_of_scope_action_count": out_of_scope_count,
        "action_coverage_claim": (
            "OpenSearch ActionModule transport coverage includes implemented adapters "
            "with scoped execution evidence; inspect release_parity_evidence before "
            "making broad transport claims"
        ),
    }
    if include_scope_counts:
        summary["accepted_evidence_scope_counts"] = TRANSPORT_ACCEPTED_EVIDENCE_SCOPE_COUNTS
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
        "ok": ok,
        "returncode": returncode,
        "status": status,
        "summary": summary,
    }


def rest_api_coverage_result(
    *,
    ok: bool = True,
    status: str = "ok",
    returncode: int = 0,
    raw_delta: int = 0,
    unexplained_delta: int = 0,
    matched_count: int = 378,
    in_scope_count: int = 378,
    source_route_count: int = 389,
    ratio: float = 1.0,
    passed: bool = True,
    fixture_route_count: int = REST_FIXTURE_ROUTE_COUNT,
    fixture_matched_count: int = 378,
    fixture_ratio: float = 1.0,
    fixture_uncovered_count: int = 0,
    live_required_fixture_route_count: int = REST_LIVE_REQUIRED_FIXTURE_ROUTE_COUNT,
    live_required_uncovered_count: int = 0,
    unified_report_fresh: bool = True,
    unified_report_max_age_seconds: float | None = 604800.0,
    unified_report_age_seconds: float | int | None = 1.0,
    include_summary: bool = True,
    include_required_breakdown: bool = True,
    source_status_counts: dict[str, int] | None = None,
):
    steelsearch_only_summary = dict(REST_STEELSEARCH_ONLY_SUMMARY)
    steelsearch_only_summary["raw_delta"] = raw_delta
    steelsearch_only_summary["effective_unexplained_delta"] = unexplained_delta
    summary = {
        "passed": passed,
        "fixture_route_count": fixture_route_count,
        "fixture_matched_source_route_count": fixture_matched_count,
        "fixture_matched_source_route_ratio": fixture_ratio,
        "fixture_uncovered_in_scope_route_count": fixture_uncovered_count,
        "live_required_fixture_route_count": live_required_fixture_route_count,
        "live_required_matched_source_route_count": matched_count,
        "live_required_matched_source_route_ratio": ratio,
        "live_required_uncovered_in_scope_route_count": live_required_uncovered_count,
        "in_scope_source_route_count": in_scope_count,
        "source_route_count": source_route_count,
        "source_route_key_digest": REST_SOURCE_ROUTE_KEY_DIGEST,
        "in_scope_source_route_key_digest": REST_IN_SCOPE_SOURCE_ROUTE_KEY_DIGEST,
        "fixture_matched_source_route_key_digest": REST_IN_SCOPE_SOURCE_ROUTE_KEY_DIGEST,
        "live_required_matched_source_route_key_digest": REST_IN_SCOPE_SOURCE_ROUTE_KEY_DIGEST,
        "source_status_counts": (
            source_status_counts
            if source_status_counts is not None
            else REST_SOURCE_STATUS_COUNTS
        ),
        "unified_report_fresh": unified_report_fresh,
        "unified_report_max_age_seconds": unified_report_max_age_seconds,
        "unified_report_age_seconds": unified_report_age_seconds,
        "unified_required_suite_status": "ok",
        "unified_required_suite_classification": deepcopy(
            REST_UNIFIED_REQUIRED_SUITE_CLASSIFICATION
        ),
        "unified_required_suite_effective_classification": deepcopy(
            REST_UNIFIED_REQUIRED_SUITE_EFFECTIVE_CLASSIFICATION
        ),
        "unified_required_suite_skip_resolution": deepcopy(
            REST_UNIFIED_REQUIRED_SUITE_SKIP_RESOLUTION
        ),
        "unified_required_suite_steelsearch_only_breakdown": [],
        "unified_non_required_suite_steelsearch_only_breakdown": [],
    }
    if include_required_breakdown is False:
        summary.pop("unified_required_suite_steelsearch_only_breakdown")
    if include_summary:
        summary["unified_required_suite_steelsearch_only_summary"] = steelsearch_only_summary
    return {
        "group": "rest-api-coverage-current",
        "name": "rest_api_source_inventory_coverage_is_reported_for_broad_required_live_suites",
        "ok": ok,
        "returncode": returncode,
        "status": status,
        "summary": summary,
    }


def pit_e2e_coverage_result(
    *,
    ok: bool = True,
    status: str = "ok",
    returncode: int = 0,
    required_count: int = 17,
    compared_count: int = 17,
    non_passed_count: int = 0,
    suite_count: int = 3,
    pit_case_count: int = 232,
    unified_report_fresh: bool = True,
    unified_report_max_age_seconds: float | None = 604800.0,
    unified_report_age_seconds: float | int | None = 1.0,
    include_summary: bool = True,
):
    result = {
        "group": "e2e-search-compat-parity",
        "name": "pit_e2e_reports_have_required_opensearch_compared_cases_without_skips",
        "ok": ok,
        "returncode": returncode,
        "status": status,
    }
    if include_summary:
        result["summary"] = {
            "required_pit_case_count": required_count,
            "required_pit_compared_case_count": compared_count,
            "non_passed_pit_case_count": non_passed_count,
            "suite_count": suite_count,
            "pit_case_count": pit_case_count,
            "pit_case_name_digest": PIT_CASE_NAME_DIGEST,
            "required_pit_case_name_digest": PIT_REQUIRED_CASE_NAME_DIGEST,
            "required_pit_compared_case_name_digest": PIT_REQUIRED_CASE_NAME_DIGEST,
            "unified_report_fresh": unified_report_fresh,
            "unified_report_max_age_seconds": unified_report_max_age_seconds,
            "unified_report_age_seconds": unified_report_age_seconds,
        }
    return result


def search_required_parity_result(
    *,
    semantic_suite_count: int = 3,
    semantic_report_path_count: int | None = None,
    passed: bool = True,
    ok: bool | None = None,
    status: str | None = None,
    returncode: int | None = None,
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
        ok=ok,
        status=status,
        returncode=returncode,
        classification_kind="required",
    )


def search_compat_parity_result(
    *,
    semantic_suite_count: int = 5,
    semantic_report_path_count: int | None = None,
    passed: bool = True,
    ok: bool | None = None,
    status: str | None = None,
    returncode: int | None = None,
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
        ok=ok,
        status=status,
        returncode=returncode,
        classification_kind="compat",
    )


def search_parity_result(
    *,
    group: str,
    name: str,
    semantic_suite_count: int,
    semantic_report_path_count: int,
    passed: bool,
    ok: bool | None,
    status: str | None,
    returncode: int | None,
    classification_kind: str,
):
    suite_counts = {
        "distributed_parity": 0,
        "durability_parity": 0,
        "route_parity": 0,
        "security_parity": 0,
        "semantic_parity": semantic_suite_count,
    }
    semantic_suite_names = (
        SEARCH_REQUIRED_SEMANTIC_SUITE_NAMES
        if classification_kind == "required"
        else SEARCH_COMPAT_SEMANTIC_SUITE_NAMES
    )
    suite_names = {
        "distributed_parity": [],
        "durability_parity": [],
        "route_parity": [],
        "security_parity": [],
        "semantic_parity": list(semantic_suite_names),
    }
    report_path_counts = dict(suite_counts)
    report_path_counts["semantic_parity"] = semantic_report_path_count
    return {
        "group": group,
        "name": name,
        "ok": passed if ok is None else ok,
        "returncode": (0 if passed else 1) if returncode is None else returncode,
        "status": ("ok" if passed else "failed") if status is None else status,
        "summary": {
            "passed": passed,
            "required_sections": [],
            "required_section_count": 0,
            "required_section_suite_counts": suite_counts,
            "required_section_suite_names": suite_names,
            "required_section_report_path_counts": report_path_counts,
            **e2e_classification_summary(classification_kind),
        },
    }


def e2e_classification_summary(kind: str):
    baseline = E2E_CLASSIFICATION_BASELINES[kind]
    summary = {key: dict(value) for key, value in baseline.items()}
    summary["classification_case_name_digest"] = E2E_CLASSIFICATION_CASE_NAME_DIGESTS[kind]
    return summary


def broad_e2e_section_result(
    *,
    ok: bool = True,
    status: str = "ok",
    returncode: int = 0,
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
    suite_names = {
        section: list(names)
        for section, names in BROAD_E2E_SECTION_SUITE_NAMES.items()
    }
    return {
        "group": "e2e-broad-parity",
        "name": "broad_unified_opensearch_e2e_report_has_no_failed_missing_or_drifted_required_suites",
        "ok": ok,
        "returncode": returncode,
        "status": status,
        "summary": {
            "passed": True,
            "required_sections": sections,
            "required_section_count": len(sections),
            "required_section_suite_counts": counts,
            "required_section_suite_names": suite_names,
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
            **e2e_classification_summary("broad"),
        },
    }


def mixed_cluster_coverage_result(
    *,
    ok: bool = True,
    status: str = "ok",
    returncode: int = 0,
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
        "failure_node_loss_passed_report_names": list(
            MIXED_FAILURE_NODE_LOSS_REPORT_NAMES
        ),
        "failure_node_loss_report_count": failure_node_loss_report_count,
        "failure_node_loss_report_names": list(MIXED_FAILURE_NODE_LOSS_REPORT_NAMES),
        "opensearch_to_steelsearch_passed": opensearch_to_steelsearch_passed,
        "passed": True,
        "phase_c_fresh_report_count": phase_c_report_count,
        "phase_c_fresh_report_names": list(MIXED_PHASE_C_REPORT_NAMES),
        "phase_c_stale_report_names": [],
        "phase_c_age_checked_report_names": list(MIXED_PHASE_C_REPORT_NAMES),
        "phase_c_max_age_seconds_by_name": {
            name: MIXED_CLUSTER_MAX_AGE_SECONDS
            for name in MIXED_PHASE_C_REPORT_NAMES
        },
        "phase_c_passed_report_count": phase_c_report_count,
        "phase_c_passed_report_names": list(MIXED_PHASE_C_REPORT_NAMES),
        "phase_c_report_count": phase_c_report_count,
        "phase_c_report_names": list(MIXED_PHASE_C_REPORT_NAMES),
        "phase_c_required_summary_reports": list(
            MIXED_PHASE_C_REQUIRED_SUMMARY_REPORTS
        ),
        "phase_c_required_check_names": {
            name: list(checks)
            for name, checks in MIXED_PHASE_C_REQUIRED_CHECK_NAMES.items()
        },
        "phase_c_passed_check_names": {
            name: list(checks)
            for name, checks in MIXED_PHASE_C_REQUIRED_CHECK_NAMES.items()
        },
        "phase_c_required_executed_tests_by_name": {
            name: list(tests)
            for name, tests in MIXED_PHASE_C_REQUIRED_EXECUTED_TESTS_BY_NAME.items()
        },
        "phase_c_executed_tests_by_name": {
            name: list(tests)
            for name, tests in MIXED_PHASE_C_REQUIRED_EXECUTED_TESTS_BY_NAME.items()
        },
        "phase_c_missing_required_executed_test_count": 0,
        "phase_c_missing_child_executed_test_count": 0,
        "phase_c_executed_tests_child_mismatch_count": 0,
        "publication_executed_test_count": 6,
        "publication_missing_required_executed_test_count": 0,
        "publication_missing_required_stage_count": 0,
        "publication_passed_report_count": 6,
        "publication_passed_report_names": list(MIXED_PUBLICATION_REPORT_NAMES),
        "publication_report_count": 6,
        "publication_report_names": list(MIXED_PUBLICATION_REPORT_NAMES),
        "publication_required_executed_test_count": 6,
        "publication_required_executed_tests": list(
            MIXED_PUBLICATION_REQUIRED_EXECUTED_TESTS
        ),
        "publication_required_stage_count": 17,
        "publication_required_stages": list(MIXED_PUBLICATION_REQUIRED_STAGES),
        "publication_stage_count": 17,
        "retention_lease_metadata_ok": True,
        "shard_movement_fresh": True,
        "shard_movement_age_checked": True,
        "shard_movement_max_age_seconds": MIXED_CLUSTER_MAX_AGE_SECONDS,
        "shard_movement_missing_required_phase_count": missing_required_phase_count,
        "shard_movement_passed": True,
        "shard_movement_phase_assertion_error_count": phase_assertion_error_count,
        "shard_movement_phase_count": shard_movement_phase_count,
        "shard_movement_phase_names": list(MIXED_SHARD_MOVEMENT_PHASE_NAMES),
        "shard_movement_duplicate_required_phase_count": 0,
        "shard_movement_required_interruption_phase_count": (
            shard_movement_required_interruption_phase_count
        ),
        "shard_movement_required_interruption_phases": list(
            MIXED_SHARD_MOVEMENT_REQUIRED_INTERRUPTION_PHASES
        ),
        "shard_movement_required_phase_count": shard_movement_required_phase_count,
        "shard_movement_required_phases": list(
            MIXED_SHARD_MOVEMENT_REQUIRED_PHASES
        ),
        "shard_movement_required_phase_fields": {
            name: list(fields)
            for name, fields in MIXED_SHARD_MOVEMENT_REQUIRED_PHASE_FIELDS.items()
        },
        "shard_movement_required_summary_flags": list(
            MIXED_SHARD_MOVEMENT_REQUIRED_SUMMARY_FLAGS
        ),
        "shard_movement_failed_required_summary_flag_count": 0,
        "steelsearch_to_opensearch_passed": steelsearch_to_opensearch_passed,
        "transport_admin_fresh": True,
        "transport_admin_age_checked": True,
        "transport_admin_max_age_seconds": MIXED_CLUSTER_MAX_AGE_SECONDS,
        "transport_admin_passed": True,
        "transport_admin_publication_transcript_count": 2,
        "transport_admin_publication_validation_event_count": 12,
        "transport_admin_publication_validation_observed_events": list(
            MIXED_TRANSPORT_ADMIN_PUBLICATION_VALIDATION_EVENTS
        ),
        "transport_admin_remote_pit_case_count": 5,
        "transport_admin_remote_pit_cases": list(
            MIXED_TRANSPORT_ADMIN_REMOTE_PIT_CASES
        ),
        "transport_admin_remote_pit_semantic_error_count": 0,
        "transport_log_ok": True,
        "unsupported_allocation_explain_ok": True,
        "mixed_cluster_stale_evidence_names": [],
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
        "ok": ok,
        "returncode": returncode,
        "status": status,
        "summary": summary,
    }


def mixed_cluster_remote_pit_result(
    *,
    ok: bool = True,
    status: str = "ok",
    returncode: int = 0,
    remote_pit_case_count: int = 5,
    remote_pit_cases: list[str] | None = None,
    failed_count: int = 0,
    remote_pit_required: bool = True,
    publication_validation_events_required: bool = True,
):
    return {
        "group": "mixed-cluster-coverage-current",
        "name": "multi_node_transport_admin_report_requires_remote_pit_forwarding_cases",
        "ok": ok,
        "returncode": returncode,
        "status": status,
        "summary": {
            "failed_count": failed_count,
            "passed": failed_count == 0,
            "publication_validation_events_required": publication_validation_events_required,
            "remote_pit_case_count": remote_pit_case_count,
            "remote_pit_cases": (
                remote_pit_cases
                if remote_pit_cases is not None
                else list(MIXED_TRANSPORT_ADMIN_REMOTE_PIT_CASES)
            ),
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
                "command": [
                    "/usr/bin/python3",
                    "tools/run-native-closure-validation.py",
                    "--batch",
                    "current-evidence-gate",
                    "--format",
                    "json",
                ],
                "summary": {
                    "batch": "current-evidence-gate",
                    "failed_count": 0,
                    "passed_count": 16,
                    "test_count": 16,
                    "zero_test_count": 0,
                },
                "required_groups": CURRENT_GROUPS,
                "groups": {
                    group: {"ok": True, "status": "ok", "returncode": 0}
                    for group in CURRENT_GROUPS
                },
                "results": [
                    non_native_inventory_result(),
                    search_required_parity_result(),
                    search_compat_parity_result(),
                    pit_e2e_coverage_result(),
                    broad_e2e_section_result(),
                    rest_api_coverage_result(),
                    transport_release_parity_result(),
                    mixed_cluster_coverage_result(),
                    mixed_cluster_remote_pit_result(),
                    materialization_priority_result(),
                    production_security_result(),
                    startup_bootstrap_result(),
                    runtime_controls_result(),
                    release_evidence_inventory_result(),
                    release_readiness_tooling_result(),
                    source_compatibility_result(),
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
    report["gates"]["final_cutover"]["status"] = "ok"
    report["gates"]["final_cutover"]["returncode"] = 0
    report["gates"]["final_cutover"]["command"] = [
        "/usr/bin/python3",
        "tools/check-release-readiness-evidence.py",
        "target/release-readiness/release-readiness.json",
        "--require-passed",
    ]
    report["gates"]["final_cutover"]["manifest_command_template"] = [
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
    ]
    report["gates"]["final_cutover"][
        "readiness_report_path"
    ] = "target/release-readiness/readiness-report.json"
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
        "command": [
            "/usr/bin/python3",
            "tools/report-release-evidence-inventory.py",
            "--root",
            "/home/ubuntu/steelsearch/target",
            "--max-age-seconds",
            "604800.0",
        ],
        "attach_command_template": [
            "python3",
            "tools/attach-release-readiness-evidence.py",
            "--readiness-report",
            "<readiness-report.json>",
            "--benchmark-report",
            "/home/ubuntu/steelsearch/target/release-benchmarks/deterministic-benchmark-baselines.jsonl",
            "--benchmark-comparison-summary",
            "target/search-benchmark-matrix-current-20260630T023334Z/summary.json",
            "--load-report",
            "/home/ubuntu/steelsearch/target/release-load-current/http-load-baseline.json",
            "--load-comparison-report",
            "/home/ubuntu/steelsearch/target/release-load-comparison/http-load-comparison.json",
            "--chaos-report",
            "/home/ubuntu/steelsearch/target/release-chaos/chaos-report.json",
            "--packaging-report",
            "/home/ubuntu/steelsearch/target/release-packaging/packaging-report.json",
            "--rolling-upgrade-report",
            "/home/ubuntu/steelsearch/target/release-rolling-upgrade/rolling-upgrade-report.json",
            "--release-readiness-file",
            "<release-readiness.json>",
        ],
        "summary": {
            "complete": True,
            "passed": True,
            "require_complete": False,
            "max_age_seconds": 604800.0,
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
        batch_results = tuple(
            (test.group, test.name) for test in runner.CURRENT_EVIDENCE_GATE_BATCH
        )

        self.assertEqual(CURRENT_GROUPS, batch_groups)
        self.assertEqual(tuple(CURRENT_GROUPS), self.checker.CURRENT_EVIDENCE_GROUPS)
        self.assertEqual(CURRENT_RESULTS, batch_results)
        self.assertEqual(CURRENT_RESULTS, self.checker.CURRENT_EVIDENCE_RESULTS)

    def test_rejects_missing_current_evidence_group(self):
        report = valid_report()
        del report["gates"]["current_evidence"]["groups"]["mixed-cluster-coverage-current"]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.groups.mixed-cluster-coverage-current is missing",
            result["errors"],
        )

    def test_rejects_extra_current_evidence_group(self):
        report = valid_report()
        report["gates"]["current_evidence"]["groups"]["unexpected-current-group"] = {
            "ok": True,
            "status": "ok",
            "returncode": 0,
        }

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.groups contains unexpected groups: unexpected-current-group",
            result["errors"],
        )

    def test_rejects_failed_current_evidence_group(self):
        report = valid_report()
        report["gates"]["current_evidence"]["groups"]["transport-action-coverage-current"]["ok"] = False
        report["gates"]["current_evidence"]["groups"]["runtime-controls-current"]["status"] = "failed"
        report["gates"]["current_evidence"]["groups"]["runtime-controls-current"]["returncode"] = 1

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.groups.transport-action-coverage-current.ok is not true",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.groups.runtime-controls-current.status is not ok",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.groups.runtime-controls-current.returncode is not zero",
            result["errors"],
        )

    def test_rejects_current_evidence_result_name_drift(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"][0]["name"] = "unexpected_result"

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results names do not match current baseline",
            result["errors"],
        )

    def test_rejects_current_evidence_command_and_summary_drift(self):
        report = valid_report()
        current = report["gates"]["current_evidence"]
        current["command"] = [
            "/usr/bin/python3",
            "tools/run-native-closure-validation.py",
            "--batch",
            "current-evidence-gate",
        ]
        current["summary"] = {
            "batch": "old-current-evidence-gate",
            "failed_count": 1,
            "passed_count": 14,
            "test_count": 14,
            "zero_test_count": 1,
        }

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.command does not match current baseline",
            result["errors"],
        )
        self.assertIn("gates.current_evidence.summary batch mismatch", result["errors"])
        self.assertIn(
            "gates.current_evidence.summary.test_count does not equal result count",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.summary.passed_count does not equal result count",
            result["errors"],
        )
        self.assertIn("gates.current_evidence.summary.failed_count is not zero", result["errors"])
        self.assertIn(
            "gates.current_evidence.summary.zero_test_count is not zero",
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
            command=["/usr/bin/python3", "tools/run-native-closure-validation.py"],
            top_returncode=1,
            group_ok=False,
            group_status="failed",
            group_returncode=1,
            result_ok=False,
            result_status="failed",
            result_returncode=1,
            test_count=0,
            passed_count=0,
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
            "gates.runtime_peer_backpressure_current.command does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current.returncode is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current runtime fairness group is not ok",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current runtime fairness group status is not ok",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current runtime fairness group returncode is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current.summary.test_count is not 1",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current.summary.passed_count is not 1",
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
            "gates.runtime_peer_backpressure_current result is not ok",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current result status is not ok",
            result["errors"],
        )
        self.assertIn(
            "gates.runtime_peer_backpressure_current result returncode is not zero",
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

    def test_rejects_non_native_inventory_with_name_digest_drift(self):
        report = valid_report()
        inventory = non_native_inventory_result()
        inventory["summary"]["probe_name_digest"] = "wrong"
        inventory["summary"]["matched_probe_name_digest"] = "wrong"
        inventory["summary"]["family_name_digest"] = "wrong"
        inventory["summary"]["evidenced_family_name_digest"] = "wrong"
        report["gates"]["current_evidence"]["results"] = [
            inventory,
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
            "gates.current_evidence.results non-native inventory probe_name_digest "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results non-native inventory matched_probe_name_digest "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results non-native inventory family_name_digest "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results non-native inventory evidenced_family_name_digest "
            "does not match current baseline",
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
            "gates.current_evidence.results non-native inventory covered categories "
            "do not match current baseline",
            result["errors"],
        )

    def test_rejects_non_native_inventory_category_baseline_drift(self):
        report = valid_report()
        required = list(NON_NATIVE_REQUIRED_CATEGORIES)
        required[-1] = "replacement-security-category"
        covered = list(NON_NATIVE_COVERED_CATEGORIES)
        covered[-1] = "replacement-source-category"
        report["gates"]["current_evidence"]["results"] = [
            non_native_inventory_result(required_categories=required, covered_categories=covered),
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
            "gates.current_evidence.results non-native inventory required categories "
            "do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results non-native inventory covered categories "
            "do not match current baseline",
            result["errors"],
        )

    def test_rejects_inventory_rest_and_transport_result_envelope_drift(self):
        report = valid_report()
        replacements = {
            (
                "non-native-inventory",
                "non_native_path_inventory_has_no_missing_probe_or_family",
            ): non_native_inventory_result(ok=False, status="failed", returncode=1),
            (
                "rest-api-coverage-current",
                "rest_api_source_inventory_coverage_is_reported_for_broad_required_live_suites",
            ): rest_api_coverage_result(ok=False, status="failed", returncode=1),
            (
                "transport-action-coverage-current",
                "transport_action_inventory_is_reported_with_current_peer_backpressure_evidence",
            ): transport_release_parity_result(ok=False, status="failed", returncode=1),
        }
        report["gates"]["current_evidence"]["results"] = [
            replacements.get((result["group"], result["name"]), result)
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        for label in (
            "non-native inventory",
            "REST coverage",
            "transport coverage",
        ):
            self.assertIn(
                f"gates.current_evidence.results {label} result is not ok",
                result["errors"],
            )
            self.assertIn(
                f"gates.current_evidence.results {label} status is not ok",
                result["errors"],
            )
            self.assertIn(
                f"gates.current_evidence.results {label} returncode is not zero",
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

    def test_rejects_remaining_current_evidence_result_envelope_drift(self):
        report = valid_report()
        replacements = {
            (
                "materialization-priority-current",
                "targeted_materialization_priority_report_has_zero_ranked_operations",
            ): materialization_priority_result(ok=False, status="failed", returncode=1),
            (
                "release-readiness-tooling",
                "release_readiness_writer_and_manifest_checker_contract",
            ): release_readiness_tooling_result(ok=False, status="failed", returncode=1),
            (
                "e2e-required-parity",
                "search_semantic_and_vector_search_e2e_reports_have_no_failed_missing_or_skipped_cases",
            ): search_required_parity_result(ok=False, status="failed", returncode=1),
            (
                "e2e-search-compat-parity",
                "search_compat_and_strict_e2e_reports_have_no_failed_or_missing_cases",
            ): search_compat_parity_result(ok=False, status="failed", returncode=1),
            (
                "e2e-search-compat-parity",
                "pit_e2e_reports_have_required_opensearch_compared_cases_without_skips",
            ): pit_e2e_coverage_result(ok=False, status="failed", returncode=1),
            (
                "e2e-broad-parity",
                "broad_unified_opensearch_e2e_report_has_no_failed_missing_or_drifted_required_suites",
            ): broad_e2e_section_result(ok=False, status="failed", returncode=1),
        }
        report["gates"]["current_evidence"]["results"] = [
            replacements.get((result["group"], result["name"]), result)
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        for label in (
            "materialization priority",
            "release readiness tooling",
            "required search semantic/vector E2E",
            "search compat/strict E2E",
            "PIT E2E coverage",
            "broad E2E section",
        ):
            self.assertIn(
                f"gates.current_evidence.results {label} result is not ok",
                result["errors"],
            )
            self.assertIn(
                f"gates.current_evidence.results {label} status is not ok",
                result["errors"],
            )
            self.assertIn(
                f"gates.current_evidence.results {label} returncode is not zero",
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
                operation_names=("fallback_terms_set",),
            ),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results materialization priority observed_operation_count is not 1",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results materialization priority observed_operation_names does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results materialization priority successful_operation_names does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results materialization priority counter_observed_operation_names does not match current baseline",
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

    def test_rejects_current_gate_result_envelope_drift(self):
        report = valid_report()
        replacements = {
            "production-security-current": production_security_result(
                ok=False, status="failed", returncode=1
            ),
            "startup-bootstrap-current": startup_bootstrap_result(
                ok=False, status="failed", returncode=1
            ),
            "runtime-controls-current": runtime_controls_result(
                ok=False, status="failed", returncode=1
            ),
            "release-evidence-inventory-current": release_evidence_inventory_result(
                ok=False, status="failed", returncode=1
            ),
        }
        report["gates"]["current_evidence"]["results"] = [
            replacements.get(result["group"], result)
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        for label in (
            "production security",
            "startup bootstrap",
            "runtime controls",
            "release evidence inventory",
        ):
            self.assertIn(
                f"gates.current_evidence.results {label} result is not ok",
                result["errors"],
            )
            self.assertIn(
                f"gates.current_evidence.results {label} status is not ok",
                result["errors"],
            )
            self.assertIn(
                f"gates.current_evidence.results {label} returncode is not zero",
                result["errors"],
            )

    def test_rejects_production_security_without_required_group_coverage(self):
        report = valid_report()
        group_counts = {
            "production-security-audit": 1,
            "production-security-auth-subjects": 2,
            "production-security-authentication": 1,
            "production-security-authorization": 22,
            "production-security-fail-closed": 1,
            "production-security-http-tls": 1,
            "production-security-permission-evaluator": 1,
            "production-security-secret-redaction": 1,
            "production-security-service-account": 1,
            "production-security-tenant-isolation": 1,
        }
        report["gates"]["current_evidence"]["results"] = [
            production_security_result(group_counts=group_counts, group_count=len(group_counts))
            if result["group"] == "production-security-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results production security group count is not 11",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results production security groups are missing: "
            "production-security-transport-tls",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results production security grouped test count is not 34",
            result["errors"],
        )

    def test_rejects_production_security_with_shifted_group_distribution(self):
        report = valid_report()
        group_counts = dict(PRODUCTION_SECURITY_GROUPS)
        group_counts["production-security-authorization"] = 22
        group_counts["production-security-audit"] = 2
        report["gates"]["current_evidence"]["results"] = [
            production_security_result(group_counts=group_counts)
            if result["group"] == "production-security-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results production security group counts "
            "do not match current baseline: production-security-audit, "
            "production-security-authorization",
            result["errors"],
        )

    def test_rejects_production_security_with_test_name_digest_drift(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            production_security_result(test_name_count=33, test_name_digest="wrong")
            if result["group"] == "production-security-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results production security test_name_count is not 34",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results production security test_name_digest "
            "does not match current baseline",
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

    def test_rejects_startup_bootstrap_with_group_coverage_drift(self):
        report = valid_report()
        preflight_counts = {
            "bind-preflight": 1,
            "config-parse-preflight": 3,
            "daemon-bind-preflight": 1,
            "daemon-data-path-preflight": 1,
            "data-path-preflight": 4,
            "identity-preflight": 1,
            "production-gate-preflight": 4,
            "role-preflight": 1,
            "security-bootstrap-preflight": 14,
            "security-bootstrap-redaction": 1,
        }
        readiness_counts = {
            "startup-readiness-shared-blockers": 2,
        }
        report["gates"]["current_evidence"]["results"] = [
            startup_bootstrap_result(
                preflight_group_counts=preflight_counts,
                preflight_group_count=len(preflight_counts),
                readiness_group_counts=readiness_counts,
                readiness_group_count=len(readiness_counts),
            )
            if result["group"] == "startup-bootstrap-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-preflight group count is not 11",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-preflight groups mismatch: "
            "production-gate-preflight, startup-preflight-production-release-evidence",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-preflight grouped test count is not 35",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-readiness group count is not 2",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-readiness groups mismatch: "
            "startup-readiness-terminology",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-readiness grouped test count is not 3",
            result["errors"],
        )

    def test_rejects_startup_bootstrap_with_test_name_digest_drift(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            startup_bootstrap_result(
                preflight_test_name_count=34,
                preflight_test_name_digest="wrong",
                readiness_test_name_count=2,
                readiness_test_name_digest="wrong",
            )
            if result["group"] == "startup-bootstrap-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-preflight "
            "test_name_count is not 35",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-preflight "
            "test_name_digest does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-readiness "
            "test_name_count is not 3",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results startup bootstrap startup-readiness "
            "test_name_digest does not match current baseline",
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
        self.assertEqual(
            RUNTIME_CONTROL_BATCH_NAME_DIGESTS,
            self.checker.RUNTIME_CONTROL_BATCH_NAME_DIGESTS,
        )

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

    def test_rejects_runtime_controls_with_test_name_digest_drift(self):
        for batch, expected_count in self.checker.RUNTIME_CONTROL_BATCH_COUNTS.items():
            with self.subTest(batch=batch):
                report = valid_report()
                report["gates"]["current_evidence"]["results"] = [
                    runtime_controls_result(
                        overrides={
                            batch: {
                                "test_name_count": expected_count - 1,
                                "test_name_digest": "wrong",
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
                    f"{batch} test_name_count is not {expected_count}",
                    result["errors"],
                )
                self.assertIn(
                    "gates.current_evidence.results runtime controls "
                    f"{batch} test_name_digest does not match current baseline",
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
            "gates.current_evidence.results release evidence inventory promotion check count is not 26",
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

    def test_rejects_release_evidence_inventory_with_wrong_result_names(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            release_evidence_inventory_result(result_names=["release_evidence_inventory_reports_current_candidate_artifacts"])
            if result["group"] == "release-evidence-inventory-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results release evidence inventory result names "
            "do not match required current gate scripts",
            result["errors"],
        )

    def test_rejects_release_evidence_inventory_with_wrong_promotion_check_names(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            release_evidence_inventory_result(
                promotion_check_names=list(PROMOTION_GATE_CHECK_NAMES[:-1]),
                promotion_passed_check_names=list(PROMOTION_GATE_CHECK_NAMES[:-1]),
                promotion_failed_check_names=["release-evidence-inventory"],
            )
            if result["group"] == "release-evidence-inventory-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results release evidence inventory promotion check names "
            "do not match required promotion gate suite",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory promotion passed check names "
            "do not match required promotion gate suite",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory promotion failed check names is not empty",
            result["errors"],
        )

    def test_rejects_release_evidence_inventory_with_wrong_ready_item_names(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            release_evidence_inventory_result(
                inventory_startup_ready_items=list(STARTUP_MANIFEST_ITEMS[:-1]),
                inventory_readiness_attachment_ready_items=list(READINESS_ATTACHMENT_ITEMS[:-1]),
                inventory_release_record_ready_items=list(RELEASE_RECORD_ITEMS[:-1]),
                readiness_ready_item_names=list(STARTUP_MANIFEST_ITEMS[:-1]),
            )
            if result["group"] == "release-evidence-inventory-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results release evidence inventory startup ready items mismatch",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory readiness attachment ready items mismatch",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory release record ready items mismatch",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release evidence inventory readiness ready item names mismatch",
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

    def test_rejects_release_readiness_tooling_with_wrong_command_specs(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            release_readiness_tooling_result(
                command_specs=[
                    "python -m unittest tools/test_replacement_gate_scripts.py",
                    "python tools/check-e2e-doc-current-counts.py",
                    "python tools/unrelated.py",
                ],
                command_spec_digest="wrong",
            )
            if result["group"] == "release-readiness-tooling"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results release readiness tooling command specs "
            "do not match required current gate commands",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results release readiness tooling command_spec_digest "
            "does not match current baseline",
            result["errors"],
        )

    def test_rejects_current_evidence_without_source_compatibility_result(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            result
            for result in report["gates"]["current_evidence"]["results"]
            if result["group"] != "source-compatibility-current"
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results source compatibility result is missing",
            result["errors"],
        )

    def test_rejects_source_compatibility_with_open_or_unmapped_gaps(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            source_compatibility_result(
                passed=False,
                ok=False,
                status="failed",
                returncode=1,
                matrix_row_count=767,
                closed_row_count=766,
                open_gap_row_count=1,
                unmapped_gap_count=1,
                open_gap_counts={"rest_route": {"partial": 1}},
            )
            if result["group"] == "source-compatibility-current"
            else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results source compatibility result is not ok",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results source compatibility did not pass",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results source compatibility matrix_row_count is not 768",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results source compatibility closed_row_count is not 768",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results source compatibility open_gap_row_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results source compatibility unmapped_gap_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results source compatibility open_gap_counts is not empty",
            result["errors"],
        )

    def test_rejects_source_compatibility_with_matrix_digest_drift(self):
        report = valid_report()
        source = source_compatibility_result()
        source["summary"]["matrix_row_digest"] = "wrong"
        source["summary"]["closed_row_digest"] = "wrong"
        report["gates"]["current_evidence"]["results"] = [
            source if result["group"] == "source-compatibility-current" else result
            for result in report["gates"]["current_evidence"]["results"]
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results source compatibility matrix_row_digest "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results source compatibility closed_row_digest "
            "does not match current baseline",
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

    def test_rejects_pit_e2e_without_fresh_age_gate(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(
                unified_report_fresh=False,
                unified_report_max_age_seconds=None,
            ),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results PIT unified report is not fresh",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results PIT unified report max age is not 604800.0",
            result["errors"],
        )

    def test_rejects_pit_e2e_with_invalid_or_stale_report_age(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(unified_report_age_seconds=604801.0),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results PIT unified report age exceeds max age",
            result["errors"],
        )

        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(unified_report_age_seconds=None),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results PIT unified report age is not valid",
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

    def test_rejects_search_compat_with_low_semantic_report_path_count(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(semantic_report_path_count=4),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results search compat/strict E2E semantic parity report path count is not 5",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results search compat/strict E2E semantic parity suite/report path count mismatch",
            result["errors"],
        )

    def test_rejects_search_compat_without_section_report_path_counts(self):
        report = valid_report()
        search = search_compat_parity_result()
        del search["summary"]["required_section_report_path_counts"]
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
            "gates.current_evidence.results search compat/strict E2E section report path counts are missing",
            result["errors"],
        )

    def test_rejects_search_compat_with_semantic_suite_name_drift(self):
        report = valid_report()
        search = search_compat_parity_result()
        search["summary"]["required_section_suite_names"]["semantic_parity"] = [
            "search-compat",
            "search-strict",
            "vector-search-native-surface",
            "unexpected-suite",
            "ml-model-surface",
        ]
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
            "gates.current_evidence.results search compat/strict E2E semantic parity suite names do not match current baseline",
            result["errors"],
        )

    def test_rejects_search_compat_with_classification_case_name_digest_drift(self):
        report = valid_report()
        search = search_compat_parity_result()
        search["summary"]["classification_case_name_digest"] = "wrong"
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
            "gates.current_evidence.results search compat/strict E2E classification case-name digest "
            "does not match current baseline",
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

    def test_rejects_search_compat_with_equal_classification_baseline_drift(self):
        report = valid_report()
        search = search_compat_parity_result()
        search["summary"]["case_classification"]["canonical_equal"] = 1001
        search["summary"]["effective_case_classification"]["strict_equal"] = 919
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
            "gates.current_evidence.results search compat/strict E2E case classification "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results search compat/strict E2E effective case classification "
            "does not match current baseline",
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

    def test_rejects_broad_e2e_section_with_low_report_path_count(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(report_path_counts={"route_parity": 13}),
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
            "gates.current_evidence.results broad E2E route_parity report path count is not 14",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results broad E2E route_parity suite/report path count mismatch",
            result["errors"],
        )

    def test_rejects_broad_e2e_section_without_report_path_counts(self):
        report = valid_report()
        broad = broad_e2e_section_result()
        del broad["summary"]["required_section_report_path_counts"]
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
            "gates.current_evidence.results broad E2E section report path counts are missing",
            result["errors"],
        )

    def test_rejects_broad_e2e_section_with_suite_name_drift(self):
        report = valid_report()
        broad = broad_e2e_section_result()
        broad["summary"]["required_section_suite_names"]["route_parity"] = [
            "alias-read",
            "unexpected-suite",
        ]
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
            "gates.current_evidence.results broad E2E route_parity suite names do not match current baseline",
            result["errors"],
        )

    def test_rejects_broad_e2e_section_with_classification_case_name_digest_drift(self):
        report = valid_report()
        broad = broad_e2e_section_result()
        broad["summary"]["classification_case_name_digest"] = "wrong"
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
            "gates.current_evidence.results broad E2E classification case-name digest "
            "does not match current baseline",
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

    def test_rejects_broad_e2e_section_with_equal_classification_baseline_drift(self):
        report = valid_report()
        broad = broad_e2e_section_result()
        broad["summary"]["case_classification"]["canonical_equal"] = 2136
        broad["summary"]["effective_case_classification"]["semantic_equal"] = 2
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
            "gates.current_evidence.results broad E2E case classification "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results broad E2E effective case classification "
            "does not match current baseline",
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

    def test_rejects_pit_e2e_coverage_with_case_name_digest_drift(self):
        report = valid_report()
        pit = pit_e2e_coverage_result()
        pit["summary"]["pit_case_name_digest"] = "wrong"
        pit["summary"]["required_pit_case_name_digest"] = "wrong"
        pit["summary"]["required_pit_compared_case_name_digest"] = "wrong"
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit,
            rest_api_coverage_result(),
            search_required_parity_result(),
            search_compat_parity_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results PIT pit_case_name_digest "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results PIT required_pit_case_name_digest "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results PIT required_pit_compared_case_name_digest "
            "does not match current baseline",
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

    def test_rejects_rest_api_coverage_without_steelsearch_only_required_breakdown(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(include_required_breakdown=False),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST steelsearch-only required breakdown is missing",
            result["errors"],
        )

    def test_rejects_rest_api_coverage_without_steelsearch_only_non_required_breakdown(self):
        report = valid_report()
        rest = rest_api_coverage_result()
        del rest["summary"]["unified_non_required_suite_steelsearch_only_breakdown"]
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest,
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST steelsearch-only non-required breakdown is missing",
            result["errors"],
        )

    def test_rejects_rest_api_coverage_with_unexpected_steelsearch_only_breakdowns(self):
        report = valid_report()
        rest = rest_api_coverage_result()
        rest["summary"]["unified_required_suite_steelsearch_only_breakdown"] = [
            {"suite": "unexpected-required"}
        ]
        rest["summary"]["unified_non_required_suite_steelsearch_only_breakdown"] = [
            {"suite": "unexpected-non-required"}
        ]
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest,
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST steelsearch-only required breakdown is not empty",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST steelsearch-only non-required breakdown is not empty",
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

    def test_rejects_rest_api_coverage_with_route_digest_drift(self):
        report = valid_report()
        rest = rest_api_coverage_result()
        rest["summary"]["source_route_key_digest"] = "wrong"
        rest["summary"]["in_scope_source_route_key_digest"] = "wrong"
        rest["summary"]["fixture_matched_source_route_key_digest"] = "wrong"
        rest["summary"]["live_required_matched_source_route_key_digest"] = "wrong"
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest,
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST source_route_key_digest "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST in_scope_source_route_key_digest "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST fixture_matched_source_route_key_digest "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST live_required_matched_source_route_key_digest "
            "does not match current baseline",
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

    def test_rejects_rest_api_coverage_with_shifted_source_status_distribution(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(
                source_status_counts={
                    "implemented": 377,
                    "out-of-scope": 12,
                }
            ),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST source status counts "
            "do not match current baseline",
            result["errors"],
        )

    def test_rejects_rest_api_coverage_with_unified_classification_drift(self):
        report = valid_report()
        rest = rest_api_coverage_result()
        rest["summary"]["unified_required_suite_classification"]["canonical_equal"] = 2127
        rest["summary"]["unified_required_suite_effective_classification"]["total_equal"] = 3076
        rest["summary"]["unified_required_suite_skip_resolution"]["resolved_by_other_suite_count"] = 20
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest,
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST unified required suite classification "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST unified required suite effective classification "
            "does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST unified required suite skip resolution "
            "does not match current baseline",
            result["errors"],
        )

    def test_rejects_rest_api_coverage_with_fixture_baseline_drift(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(
                passed=False,
                fixture_route_count=3628,
                fixture_matched_count=377,
                fixture_ratio=0.997,
                fixture_uncovered_count=1,
                live_required_fixture_route_count=3488,
                live_required_uncovered_count=1,
                unified_report_fresh=False,
                unified_report_max_age_seconds=None,
            ),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST coverage summary did not pass",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST fixture route count is not 3629",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST fixture matched source route count is not 378",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST fixture matched source route ratio is not 1.0",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST fixture uncovered in-scope route count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST live required fixture route count is not 3489",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST live required uncovered in-scope route count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST unified report is not fresh",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results REST unified report max age is not 604800.0",
            result["errors"],
        )

    def test_rejects_rest_api_coverage_with_invalid_or_stale_report_age(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(unified_report_age_seconds=604801.0),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST unified report age exceeds max age",
            result["errors"],
        )

        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(unified_report_age_seconds=-1.0),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results REST unified report age is not valid",
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
        transport = transport_release_parity_result(matched_count=173)
        transport["summary"]["source_implemented_action_name_digest"] = "wrong"
        transport["summary"]["accepted_evidence_action_name_digest"] = "wrong"
        transport["summary"]["release_evidence_action_name_digest"] = "wrong"
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
            "gates.current_evidence.results transport release parity matched action count is not 174",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport transport_action_count is not 174",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport source_implemented_action_name_digest does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport accepted_evidence_action_name_digest does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport release_evidence_action_name_digest does not match current baseline",
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

    def test_rejects_transport_release_parity_with_execution_evidence_error_drift(self):
        report = valid_report()
        transport = transport_release_parity_result(
            passed=False,
            peer_backpressure_passed=False,
        )
        transport["summary"]["accepted_evidence_request_semantic_error_count"] = 1
        transport["summary"]["accepted_evidence_response_semantic_error_count"] = 1
        transport["summary"]["release_evidence_pointer_test_error_count"] = 1
        transport["summary"]["release_evidence_shared_pointer_error_count"] = 1
        transport["summary"].pop("action_coverage_claim")
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
            "gates.current_evidence.results transport coverage did not pass",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport peer backpressure did not pass",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport "
            "accepted_evidence_request_semantic_error_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport "
            "accepted_evidence_response_semantic_error_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport "
            "release_evidence_pointer_test_error_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport "
            "release_evidence_shared_pointer_error_count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results transport action coverage claim is missing",
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

    def test_rejects_transport_release_parity_accepted_scope_count_drift(self):
        report = valid_report()
        transport = transport_release_parity_result()
        transport["summary"]["accepted_evidence_scope_counts"] = {
            "bounded_local_subset": 169,
            "bounded_seed_peer_fanout_subset": 5,
        }
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
            "gates.current_evidence.results transport accepted evidence scope counts "
            "do not match current baseline",
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

    def test_rejects_mixed_cluster_result_envelope_drift(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(ok=False, status="failed", returncode=1),
            mixed_cluster_remote_pit_result(ok=False, status="failed", returncode=1),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results mixed-cluster coverage result is not ok",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster coverage status is not ok",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster coverage returncode is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster remote PIT result is not ok",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster remote PIT status is not ok",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster remote PIT returncode is not zero",
            result["errors"],
        )

    def test_rejects_mixed_cluster_with_narrow_claim_boundary(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["claim_boundary"] = "representative mixed-cluster evidence is present"
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
            "gates.current_evidence.results mixed-cluster claim boundary is missing",
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

    def test_rejects_mixed_cluster_required_phase_name_drift(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["shard_movement_required_phases"] = [
            "cluster_formed",
            "initial_primary_on_java1",
        ]
        coverage["summary"]["shard_movement_required_interruption_phases"] = [
            "interrupt_java_to_steelsearch_recovery"
        ]
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
            "gates.current_evidence.results mixed-cluster required shard movement phases do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster required interruption phases do not match current baseline",
            result["errors"],
        )

    def test_rejects_mixed_cluster_actual_phase_name_drift(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["shard_movement_phase_names"] = [
            "cluster_formed",
            "initial_primary_on_java1",
        ]
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
            "gates.current_evidence.results mixed-cluster shard movement phase names do not match current baseline",
            result["errors"],
        )

    def test_rejects_mixed_cluster_duplicate_required_phase_count(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["shard_movement_duplicate_required_phase_count"] = 1
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
            "gates.current_evidence.results mixed-cluster duplicate required shard movement phase count is not zero",
            result["errors"],
        )

    def test_rejects_mixed_cluster_required_phase_field_drift(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["shard_movement_required_phase_fields"] = {
            "cluster_formed": ["node_count"]
        }
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
            "gates.current_evidence.results mixed-cluster required shard movement phase fields do not match current baseline",
            result["errors"],
        )

    def test_rejects_mixed_cluster_required_summary_flag_drift(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["shard_movement_required_summary_flags"] = [
            "checkpoint_drift_ok"
        ]
        coverage["summary"]["shard_movement_failed_required_summary_flag_count"] = 1
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
            "gates.current_evidence.results mixed-cluster required shard movement summary flags do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster failed required shard movement summary flag count is not zero",
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

    def test_rejects_mixed_cluster_phase_c_report_inventory_drift(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["phase_c_report_names"] = ["join"]
        coverage["summary"]["phase_c_passed_report_names"] = ["join"]
        coverage["summary"]["phase_c_fresh_report_names"] = ["join"]
        coverage["summary"]["phase_c_required_summary_reports"] = [
            "mixed-cluster-join-report.json"
        ]
        coverage["summary"]["phase_c_required_check_names"] = {
            "join": ["live_join_probe_passed"]
        }
        coverage["summary"]["phase_c_passed_check_names"] = {
            "join": ["live_join_probe_passed"]
        }
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
            "gates.current_evidence.results mixed-cluster phase C report names do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster phase C passed report names do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster phase C fresh report names do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster phase C required summary reports do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster phase C required check names do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster phase C passed check names do not match current baseline",
            result["errors"],
        )

    def test_rejects_mixed_cluster_phase_c_executed_test_drift(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["phase_c_required_executed_tests_by_name"] = {
            "join": ["mixed_cluster_live_join_probe"]
        }
        coverage["summary"]["phase_c_executed_tests_by_name"] = {
            "join": ["mixed_cluster_live_join_probe"]
        }
        coverage["summary"]["phase_c_missing_required_executed_test_count"] = 1
        coverage["summary"]["phase_c_missing_child_executed_test_count"] = 1
        coverage["summary"]["phase_c_executed_tests_child_mismatch_count"] = 1
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
            "gates.current_evidence.results mixed-cluster phase C required executed tests do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster phase C executed tests do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster phase C missing required executed test count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster phase C missing child executed test count is not zero",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster phase C executed tests child mismatch count is not zero",
            result["errors"],
        )

    def test_rejects_mixed_cluster_freshness_envelope_drift(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["phase_c_stale_report_names"] = ["join"]
        coverage["summary"]["phase_c_age_checked_report_names"] = ["join"]
        coverage["summary"]["phase_c_max_age_seconds_by_name"] = {"join": 1.0}
        coverage["summary"]["mixed_cluster_stale_evidence_names"] = ["phase_c:join"]
        coverage["summary"]["shard_movement_age_checked"] = False
        coverage["summary"]["transport_admin_age_checked"] = False
        coverage["summary"]["shard_movement_max_age_seconds"] = 1.0
        coverage["summary"]["transport_admin_max_age_seconds"] = 1.0
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
            "gates.current_evidence.results mixed-cluster phase C stale report names is not empty",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster phase C age-checked report names do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster phase C max age seconds by name does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster stale evidence names is not empty",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster shard_movement_age_checked is not true",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster transport_admin_age_checked is not true",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster shard_movement_max_age_seconds is not 5184000.0",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster transport_admin_max_age_seconds is not 5184000.0",
            result["errors"],
        )

    def test_rejects_mixed_cluster_failure_node_loss_report_name_drift(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["failure_node_loss_report_names"] = [
            "failure_java_node_loss"
        ]
        coverage["summary"]["failure_node_loss_passed_report_names"] = [
            "failure_java_node_loss"
        ]
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
            "gates.current_evidence.results mixed-cluster failure node-loss report names do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster failure node-loss passed report names do not match current baseline",
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

    def test_rejects_mixed_cluster_publication_name_drift(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["publication_required_executed_tests"] = [
            "publication_full_state_receive_apply_replaces_local_cache"
        ]
        coverage["summary"]["publication_required_stages"] = ["full_state_decode"]
        coverage["summary"]["publication_report_names"] = [
            "publication-full-state-report.json"
        ]
        coverage["summary"]["publication_passed_report_names"] = [
            "publication-full-state-report.json"
        ]
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
            "gates.current_evidence.results mixed-cluster required publication executed tests do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster required publication stages do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster publication report names do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster publication passed report names do not match current baseline",
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

    def test_rejects_mixed_cluster_transport_admin_remote_pit_case_name_drift(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["transport_admin_remote_pit_cases"] = [
            "node_a_open_pit"
        ]
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
            "gates.current_evidence.results mixed-cluster transport admin remote PIT cases do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster remote PIT case names "
            "do not match transport admin summary",
            result["errors"],
        )

    def test_rejects_mixed_cluster_remote_pit_result_case_name_drift(self):
        report = valid_report()
        report["gates"]["current_evidence"]["results"] = [
            broad_e2e_section_result(),
            mixed_cluster_coverage_result(),
            mixed_cluster_remote_pit_result(remote_pit_cases=["node_a_open_pit"]),
            pit_e2e_coverage_result(),
            rest_api_coverage_result(),
            transport_release_parity_result(),
        ]

        result = self.checker.validate_report(report)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gates.current_evidence.results mixed-cluster remote PIT case names do not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "gates.current_evidence.results mixed-cluster remote PIT case names "
            "do not match transport admin summary",
            result["errors"],
        )

    def test_rejects_mixed_cluster_transport_admin_remote_pit_semantic_errors(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["transport_admin_remote_pit_semantic_error_count"] = 1
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
            "gates.current_evidence.results mixed-cluster transport admin remote PIT semantic error count is not zero",
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

    def test_rejects_mixed_cluster_transport_admin_validation_event_name_drift(self):
        report = valid_report()
        coverage = mixed_cluster_coverage_result()
        coverage["summary"]["transport_admin_publication_validation_observed_events"] = [
            "proposal.connect.passed"
        ]
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
            "gates.current_evidence.results mixed-cluster transport admin publication validation events do not match current baseline",
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

    def test_rejects_passed_final_cutover_with_metadata_drift(self):
        report = mark_final_cutover_complete(valid_report())
        final = report["gates"]["final_cutover"]
        final["status"] = "failed"
        final["readiness_report_path"] = "target/old-readiness/readiness-report.json"
        inventory_summary = final["evidence_inventory"]["summary"]
        inventory_summary["passed"] = False
        inventory_summary["require_complete"] = True
        inventory_summary["max_age_seconds"] = 1.0

        result = self.checker.validate_report(report, require_final_cutover=True)

        self.assertEqual(result["status"], "failed")
        self.assertIn("final_cutover passed but status is not ok", result["errors"])
        self.assertIn(
            "final_cutover readiness_report_path does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "final_cutover passed but evidence inventory summary did not pass",
            result["errors"],
        )
        self.assertIn(
            "final_cutover passed but evidence inventory require_complete is not false",
            result["errors"],
        )
        self.assertIn(
            "final_cutover passed but evidence inventory max_age_seconds is not 604800.0",
            result["errors"],
        )

    def test_rejects_passed_final_cutover_with_command_drift(self):
        report = mark_final_cutover_complete(valid_report())
        final = report["gates"]["final_cutover"]
        final["command"] = [
            "/usr/bin/python3",
            "tools/check-release-readiness-evidence.py",
            "target/release-readiness/release-readiness.json",
        ]
        final["manifest_command_template"] = ["python3", "tools/attach-release-readiness-evidence.py"]
        inventory = final["evidence_inventory"]
        inventory["command"] = [
            "/usr/bin/python3",
            "tools/report-release-evidence-inventory.py",
            "--root",
            "/home/ubuntu/steelsearch/target",
            "--max-age-seconds",
            "1.0",
        ]
        inventory["attach_command_template"] = [
            "python3",
            "tools/attach-release-readiness-evidence.py",
            "--readiness-report",
            "<readiness-report.json>",
        ]

        result = self.checker.validate_report(report, require_final_cutover=True)

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "final_cutover command does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "final_cutover manifest command template does not match current baseline",
            result["errors"],
        )
        self.assertIn(
            "final_cutover evidence inventory command max age is not 604800.0",
            result["errors"],
        )
        self.assertIn(
            "final_cutover evidence inventory attach command template missing flags: "
            "--benchmark-report, --benchmark-comparison-summary, --load-report, "
            "--load-comparison-report, --chaos-report, --packaging-report, "
            "--rolling-upgrade-report, --release-readiness-file",
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
