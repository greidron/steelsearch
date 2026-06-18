#!/usr/bin/env python3
"""Run native-closure validation batches and reject zero-test matches."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ValidationTest:
    name: str
    group: str
    package: str = "os-engine-tantivy"
    target: tuple[str, ...] = ("--lib",)
    features: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExternalValidation:
    name: str
    group: str
    command: tuple[str, ...]
    timeout_seconds: int = 900


ValidationCase = ValidationTest | ExternalValidation


COMPACT_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "engine_collects_placeholder_for_malformed_plugin_bucket_sort_request",
        "malformed-wrapper",
    ),
    ValidationTest(
        "engine_collects_placeholder_for_malformed_plugin_derivative_request",
        "malformed-wrapper",
    ),
    ValidationTest(
        "engine_collects_placeholder_for_malformed_plugin_serial_diff_request",
        "malformed-wrapper",
    ),
    ValidationTest(
        "engine_collects_placeholder_for_malformed_plugin_bucket_count_request",
        "malformed-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_sort_surface",
        "date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_count_surface",
        "date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_derivative_surface",
        "date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_serial_diff_surface",
        "date-histogram-rebucketing-wrapper",
    ),
)

REBUCKETING_WIDE_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_sort_surface",
        "auto-date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_count_surface",
        "auto-date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_derivative_surface",
        "auto-date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_serial_diff_surface",
        "auto-date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_sort_surface",
        "histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_count_surface",
        "histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_histogram_reduce_feeds_derivative_surface",
        "histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_histogram_reduce_feeds_serial_diff_surface",
        "histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_sort_surface",
        "variable-width-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_count_surface",
        "variable-width-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_derivative_surface",
        "variable-width-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_serial_diff_surface",
        "variable-width-histogram-rebucketing-wrapper",
    ),
)

VECTOR_KNN_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "engine_executes_knn_query_with_filter_and_vector_scores",
        "vector-knn-filter-score",
    ),
    ValidationTest(
        "engine_bounds_and_invalidates_knn_runtime_cache_entries",
        "vector-knn-cache",
    ),
    ValidationTest(
        "single_index_knn_uses_vector_native_page_and_aggregation_fetch",
        "single-index-vector-native-page-aggregation",
    ),
    ValidationTest(
        "multi_index_knn_uses_vector_native_page_and_aggregation_reduce",
        "multi-index-vector-native-page-aggregation",
    ),
    ValidationTest(
        "multi_index_knn_uses_vector_native_page_reduce_with_id_sort",
        "multi-index-vector-native-sort",
    ),
    ValidationTest(
        "multi_index_knn_uses_vector_native_page_and_aggregation_reduce_with_score_desc",
        "multi-index-vector-native-sort",
    ),
    ValidationTest(
        "multi_index_knn_uses_vector_native_page_and_aggregation_reduce_with_fast_field_sort",
        "multi-index-vector-native-sort",
    ),
    ValidationTest(
        "single_index_hybrid_uses_vector_native_page_and_aggregation_fetch_with_fast_field_sort",
        "single-index-hybrid-vector-native-sort-aggregation",
    ),
    ValidationTest(
        "multi_index_hybrid_uses_vector_native_page_and_aggregation_reduce",
        "multi-index-hybrid-vector-native-page-aggregation",
    ),
    ValidationTest(
        "multi_index_hybrid_uses_vector_native_page_and_aggregation_reduce_with_script_sort",
        "multi-index-hybrid-vector-native-sort-aggregation",
    ),
    ValidationTest(
        "multi_index_knn_vector_cache_populates_request_result_cache_detail_entries",
        "multi-index-vector-knn-cache",
    ),
    ValidationTest(
        "multi_index_hybrid_vector_request_result_cache_is_telemetry_visible",
        "multi-index-vector-hybrid-cache",
    ),
    ValidationTest(
        "multi_index_hybrid_vector_cache_populates_request_result_cache_detail_entries",
        "multi-index-vector-hybrid-cache",
    ),
)

SOURCE_BACKED_QUERY_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "native_tantivy_path_executes_nested_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_index_avoids_flatten_tuple_false_positive",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_exists_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_string_prefix_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_range_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_terms_set_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_distance_feature_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_rank_feature_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_string_wildcard_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_string_regexp_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_string_fuzzy_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_match_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_match_phrase_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_match_phrase_prefix_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_match_bool_prefix_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_combined_fields_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_multi_match_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_tantivy_path_executes_geo_distance_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_geo_distance_bbox_candidates_are_source_validated_against_circle",
        "source-backed-fallback-boundary",
    ),
    ValidationTest(
        "native_tantivy_path_executes_distance_feature_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "distance_feature_non_numeric_field_uses_source_candidate_native_page",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_tantivy_path_executes_rank_feature_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "rank_feature_non_feature_field_uses_source_candidate_native_page",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_tantivy_path_executes_more_like_this_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "more_like_this_fieldless_uses_source_candidate_native_page",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_tantivy_path_executes_terms_set_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "terms_set_non_term_field_uses_source_candidate_native_page",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_tantivy_path_executes_query_string_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "case_insensitive_wildcard_text_field_uses_source_candidate_native_page",
        "source-backed-native-query",
    ),
    ValidationTest(
        "query_string_unsupported_field_type_uses_source_candidate_native_page",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_tantivy_path_executes_simple_query_string_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "simple_query_string_unsupported_field_type_uses_source_candidate_native_page",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_tantivy_path_executes_combined_fields_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_tantivy_path_executes_match_phrase_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_tantivy_path_executes_match_phrase_prefix_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_tantivy_path_executes_match_bool_prefix_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_tantivy_path_executes_multi_match_query",
        "source-backed-native-query",
    ),
    ValidationTest(
        "grouped_hybrid_bool_match_phrase_leaf_reduces_candidate_ids_directly",
        "source-backed-hybrid-candidate-reduction",
    ),
    ValidationTest(
        "grouped_hybrid_bool_match_phrase_prefix_leaf_reduces_candidate_ids_directly",
        "source-backed-hybrid-candidate-reduction",
    ),
    ValidationTest(
        "grouped_hybrid_bool_match_bool_prefix_leaf_reduces_candidate_ids_directly",
        "source-backed-hybrid-candidate-reduction",
    ),
    ValidationTest(
        "grouped_hybrid_bool_multi_match_leaf_reduces_candidate_ids_directly",
        "source-backed-hybrid-candidate-reduction",
    ),
    ValidationTest(
        "grouped_hybrid_bool_geo_distance_leaf_reduces_candidate_ids_directly",
        "source-backed-hybrid-candidate-reduction",
    ),
    ValidationTest(
        "grouped_hybrid_bool_terms_set_leaf_reduces_candidate_ids_directly",
        "source-backed-hybrid-candidate-reduction",
    ),
    ValidationTest(
        "grouped_hybrid_bool_rank_feature_leaf_reduces_candidate_ids_directly",
        "source-backed-hybrid-candidate-reduction",
    ),
    ValidationTest(
        "grouped_hybrid_bool_distance_feature_leaf_reduces_candidate_ids_directly",
        "source-backed-hybrid-candidate-reduction",
    ),
    ValidationTest(
        "grouped_hybrid_bool_more_like_this_leaf_reduces_candidate_ids_directly",
        "source-backed-hybrid-candidate-reduction",
    ),
    ValidationTest(
        "grouped_hybrid_bool_query_string_leaf_reduces_candidate_ids_directly",
        "source-backed-hybrid-candidate-reduction",
    ),
    ValidationTest(
        "grouped_hybrid_bool_simple_query_string_leaf_reduces_candidate_ids_directly",
        "source-backed-hybrid-candidate-reduction",
    ),
)

BENCHMARK_TELEMETRY_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "benchmark_telemetry_scripts_expose_native_counters",
        "benchmark-telemetry",
        (
            "python3",
            "-c",
            "import json, subprocess, sys; commands = [[sys.executable, '-m', 'unittest', 'tools/test_benchmark_telemetry_scripts.py'], ['cargo', 'test', '-p', 'os-node', '--features', 'standalone-runtime', '--lib', 'query_string_native_http_path_reports_zero_materialized_search_cache_stats', '--', '--nocapture']]; results = [subprocess.run(command) for command in commands]; passed = all(result.returncode == 0 for result in results); print(json.dumps({'summary': {'passed': passed, 'commands': len(commands)}})); sys.exit(0 if passed else 1)",
        ),
    ),
    ExternalValidation(
        "materialization_priority_report_ranks_operation_resource_deltas",
        "benchmark-telemetry",
        (
            "python3",
            "tools/rank-materialization-priorities.py",
            "tools/fixtures/materialization-priority-sample.json",
            "--format",
            "json",
        ),
        timeout_seconds=60,
    ),
    ExternalValidation(
        "materialization_priority_diagnostic_harness_reports_artifact_paths",
        "benchmark-telemetry",
        (
            "python3",
            "tools/run-materialization-priority-diagnostic.py",
            "--dry-run",
            "--work-dir",
            "target/materialization-priority-diagnostic.validation",
        ),
        timeout_seconds=60,
    ),
)

STARTUP_PREFLIGHT_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "production_mode_request_reports_each_missing_security_and_release_gate",
        "production-gate-preflight",
        package="os-node-rest-core",
        target=("--lib",),
    ),
    ValidationTest(
        "production_mode_request_allows_startup_only_when_all_gates_are_complete",
        "production-gate-preflight",
        package="os-node-rest-core",
        target=("--lib",),
    ),
    ValidationTest(
        "production_mode_request_keeps_release_and_security_blockers_distinct",
        "production-gate-preflight",
        package="os-node-rest-core",
        target=("--lib",),
    ),
    ValidationTest(
        "production_mode_request_tracks_http_and_transport_tls_independently",
        "production-gate-preflight",
        package="os-node-rest-core",
        target=("--lib",),
    ),
    ValidationTest(
        "authentication_users_file_parser_accepts_subjects_with_roles",
        "security-bootstrap-preflight",
        package="os-node-rest-core",
        target=("--lib",),
    ),
    ValidationTest(
        "authentication_users_file_parser_rejects_empty_and_malformed_inputs",
        "security-bootstrap-preflight",
        package="os-node-rest-core",
        target=("--lib",),
    ),
    ValidationTest(
        "authentication_users_file_parser_rejects_invalid_subject_entries",
        "security-bootstrap-preflight",
        package="os-node-rest-core",
        target=("--lib",),
    ),
    ValidationTest(
        "daemon_config_rejects_data_path_that_is_not_directory",
        "data-path-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_creates_missing_data_path_during_preflight",
        "data-path-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_locked_data_path",
        "data-path-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_readonly_data_path",
        "data-path-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_same_http_and_transport_socket",
        "bind-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_duplicate_development_node_ids",
        "identity-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_invalid_addresses",
        "config-parse-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_invalid_ports",
        "config-parse-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_opensearch_e_settings_with_explicit_contract",
        "config-parse-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_non_cluster_manager_without_seed_hosts",
        "role-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_production_mode_without_required_gates",
        "production-gate-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_reports_missing_security_bootstrap_material",
        "security-bootstrap-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_requires_runtime_security_enforcement",
        "security-bootstrap-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_accepts_security_bootstrap_files_before_policy_gate",
        "security-bootstrap-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_accepts_service_account_only_authentication_users_file",
        "security-bootstrap-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_rejects_invalid_tls_bootstrap_material",
        "security-bootstrap-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_rejects_swapped_tls_bootstrap_material_roles",
        "security-bootstrap-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_redacts_invalid_security_bootstrap_file_contents",
        "security-bootstrap-redaction",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_rejects_empty_authentication_users_file",
        "security-bootstrap-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_rejects_malformed_authentication_users_file",
        "security-bootstrap-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_rejects_authentication_users_without_roles",
        "security-bootstrap-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_rejects_invalid_secure_settings_file",
        "security-bootstrap-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_accepts_complete_release_readiness_evidence",
        "startup-preflight-production-release-evidence",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_rejects_invalid_release_readiness_evidence",
        "startup-preflight-production-release-evidence",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_rejects_missing_release_readiness_artifact",
        "startup-preflight-production-release-evidence",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_rejects_data_path_that_is_not_a_directory",
        "daemon-data-path-preflight",
        package="os-node",
        target=("--test", "dev_cluster_daemons"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_exits_when_http_port_is_occupied",
        "daemon-bind-preflight",
        package="os-node",
        target=("--test", "dev_cluster_daemons"),
        features=("standalone-runtime",),
    ),
    ExternalValidation(
        "secure_multinode_tls_handshake_matrix_fixture_is_guarded",
        "security-bootstrap-preflight",
        (
            "python3",
            "tools/check-secure-multinode-tls.py",
        ),
    ),
)

STARTUP_READINESS_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "startup_preflight_and_readiness_report_share_blocker_reasons",
        "startup-readiness-shared-blockers",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "production_startup_preflight_and_readiness_share_security_blockers",
        "startup-readiness-shared-blockers",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "startup_readiness_report_uses_steelsearch_runtime_terminology",
        "startup-readiness-terminology",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
)

PRODUCTION_SECURITY_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "secure_env_credentials_are_loaded_through_authentication_users_subjects",
        "production-security-auth-subjects",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_authentication_users_file_drives_runtime_basic_auth_and_service_accounts",
        "production-security-auth-subjects",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_root_route_requires_valid_basic_auth_credentials",
        "production-security-authentication",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_role_permission_evaluator_enforces_admin_reader_writer_matrix",
        "production-security-permission-evaluator",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_ml_routes_require_admin_role_and_connector_state_persists",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_ml_connector_create_redacts_secret_material_from_response_and_persistence",
        "production-security-secret-redaction",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_route_authn_authz_and_fail_closed_decisions_are_audited",
        "production-security-audit",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rest_http_listener_serves_root_route_over_tls_when_configured",
        "production-security-http-tls",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "transport_seed_connection_serves_keepalive_over_tls_when_configured",
        "production-security-transport-tls",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_bulk_route_surfaces_writer_partial_authz_denial_and_reader_route_denial",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_task_style_write_routes_require_writer_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_single_document_routes_require_read_or_write_roles",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_multi_document_read_routes_require_reader_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_service_account_subject_can_authorize_writer_route",
        "production-security-service-account",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_search_and_session_routes_require_read_roles",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_tenant_scoped_subjects_cannot_cross_index_tenant_boundaries",
        "production-security-tenant-isolation",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_reload_secure_settings_requires_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_cluster_admin_control_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_cluster_observability_routes_require_reader_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_snapshot_control_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_template_management_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_pipeline_management_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_stored_script_management_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_data_stream_management_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_alias_management_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_index_metadata_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_index_maintenance_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_index_structure_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_index_root_routes_require_admin_or_reader_roles",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_index_metadata_read_routes_require_reader_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_knn_operational_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_recovery_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "secure_ingestion_control_routes_require_admin_role",
        "production-security-authorization",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "opensearch_security_plugin_apis_fail_closed_with_documented_error",
        "production-security-fail-closed",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
)

RUNTIME_TASKS_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "tasks_live_route_supports_list_get_and_cancel_shapes",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_cancel_route_supports_task_id_path_variant",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_repeated_cancel_is_idempotent_with_post_cancel_readback",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_cancel_by_parent_task_id_preserves_parent_child_visibility",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_cancel_by_parent_task_id_propagates_to_same_node_descendants",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_cancel_by_parent_task_id_propagates_to_cross_node_descendants",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_cancel_by_parent_task_id_propagates_to_background_worker_descendants",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_queued_and_in_flight_cancellation_have_distinct_runtime_visibility",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "queued_cancelled_task_worker_drain_preserves_terminal_marker_and_queue_depth",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cancel_after_completion_race_does_not_create_cancelled_marker",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_terminal_states_remain_readable_without_polluting_pending_queue_depth",
        "task-terminal-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "terminal_task_retention_eviction_is_bounded_and_persisted",
        "task-terminal-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cancelled_task_terminal_completion_preserves_marker_until_eviction",
        "task-terminal-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cancelled_terminal_cancel_after_restart_sync_preserves_progress",
        "task-terminal-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cancelled_terminal_live_shutdown_preserves_progress_and_refuses_cancel",
        "task-terminal-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cancelled_terminal_node_role_transition_preserves_visibility_and_refuses_cancel",
        "task-terminal-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "terminal_task_node_role_transition_preserves_acknowledged_and_failed_readback",
        "task-terminal-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "active_task_node_role_transition_preserves_cancel_and_in_flight_refusal",
        "task-restart-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "node_role_transition_restart_smoke_preserves_queue_visibility_and_refusal",
        "task-restart-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "task_queue_state_and_cancelled_ids_persist_across_shared_runtime_restart",
        "task-restart-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cancel_request_during_restart_window_syncs_before_mutation",
        "task-restart-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "task_listing_survives_partial_shared_runtime_state_recovery_error",
        "task-restart-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
)

RUNTIME_QUEUE_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "cluster_pending_tasks_route_surfaces_task_metadata_visibility",
        "task-queue-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cluster_health_tasks_and_cat_pending_tasks_share_runtime_queue_depth",
        "task-queue-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "empty_and_non_empty_runtime_queue_visibility_transitions_are_distinct",
        "task-queue-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "multi_node_task_queue_visibility_uses_remote_node_metadata",
        "task-queue-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_queued_and_in_flight_cancellation_have_distinct_runtime_visibility",
        "task-queue-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "queued_cancelled_task_worker_drain_preserves_terminal_marker_and_queue_depth",
        "task-queue-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
)

RUNTIME_BACKPRESSURE_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "cluster_health_tasks_and_cat_pending_tasks_share_runtime_queue_depth",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "empty_and_non_empty_runtime_queue_visibility_transitions_are_distinct",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "search_and_bulk_routes_update_runtime_thread_pool_counters",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "search_and_bulk_routes_wait_and_drain_runtime_thread_pool_queue_under_concurrency",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "runtime_thread_pool_classes_drain_independently_under_mixed_backlog",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "runtime_write_and_maintenance_pools_drain_independently_under_mixed_backlog",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "remote_task_backlog_does_not_block_local_task_submission_admission",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "remote_task_backlog_does_not_block_local_search_or_write_admission",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "search_and_bulk_routes_reject_when_runtime_thread_pools_are_saturated",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "maintenance_routes_wait_drain_and_reject_when_runtime_pool_is_saturated",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "accepted_pending_and_overload_refusal_have_distinct_runtime_telemetry",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "immediate_and_queued_reroute_and_maintenance_work_have_distinct_telemetry",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "maintenance_and_control_plane_burst_submissions_surface_backlog_growth_and_drain",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "overlapping_maintenance_calls_distinguish_accepted_pending_from_completed_effect",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tier_transition_restart_smoke_preserves_readback_and_cancel",
        "maintenance-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "snapshot_restore_and_cleanup_restart_smoke_preserves_metadata_without_queue_replay",
        "maintenance-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "maintenance_work_accepted_before_shutdown_is_not_replayed_after_restart",
        "maintenance-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "snapshot_restore_to_renamed_index_preserves_source_close_state_readback",
        "maintenance-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "snapshot_restore_conflict_surfaces_rollback_readback_for_existing_target",
        "maintenance-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "snapshot_routes_wait_drain_and_reject_when_runtime_pool_is_saturated",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cluster_reroute_waits_drains_and_rejects_when_runtime_pool_is_saturated",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "task_submission_routes_wait_drain_and_reject_when_runtime_pool_is_saturated",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_does_not_consume_task_submission_backpressure_capacity",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "accepted_queued_task_submission_is_not_replayed_after_shared_runtime_restart",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "accepted_queued_task_submission_is_not_replayed_during_partial_recovery_error",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "task_submission_is_refused_during_live_shutdown_window",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "runtime_thread_pool_queue_state_resets_across_shared_runtime_restart",
        "route-backpressure-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
)

RUNTIME_FAIRNESS_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "multi_node_task_queue_visibility_uses_remote_node_metadata",
        "runtime-fairness-multi-node-metadata",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "remote_task_backlog_does_not_block_local_task_submission_admission",
        "runtime-fairness-local-admission",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "remote_task_backlog_does_not_block_local_search_or_write_admission",
        "runtime-fairness-local-admission",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "remote_task_backlog_does_not_block_local_control_plane_admission",
        "runtime-fairness-local-admission",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "runtime_thread_pool_classes_drain_independently_under_mixed_backlog",
        "runtime-fairness-independent-drain",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "runtime_write_and_maintenance_pools_drain_independently_under_mixed_backlog",
        "runtime-fairness-independent-drain",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "restarted_local_daemon_with_remote_backlog_keeps_local_search_and_write_admitted",
        "runtime-fairness-live-daemon",
        package="os-node",
        target=("--test", "dev_cluster_daemons"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "shard_search_client_and_server_round_trip_over_tcp",
        "runtime-fairness-remote-transport-execution",
        package="os-transport",
        target=("--lib",),
    ),
    ValidationTest(
        "replica_operation_client_and_server_round_trip_over_tcp",
        "runtime-fairness-remote-transport-execution",
        package="os-transport",
        target=("--lib",),
    ),
    ValidationTest(
        "shard_search_remote_transport_gate_queues_drains_and_rejects_over_tcp",
        "runtime-fairness-remote-transport-backpressure",
        package="os-transport",
        target=("--lib",),
    ),
    ValidationTest(
        "remote_transport_gate_blocking_execution_queues_drains_and_rejects",
        "runtime-fairness-remote-transport-backpressure",
        package="os-transport",
        target=("--lib",),
    ),
    ValidationTest(
        "query_phase_transport_route_uses_remote_transport_queue_gate_for_admission",
        "runtime-fairness-remote-transport-backpressure",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "live_multi_daemon_query_phase_transport_queue_rejection_is_reported_in_rest_telemetry",
        "runtime-fairness-remote-transport-backpressure",
        package="os-node",
        target=("--test", "dev_cluster_daemons"),
        features=("standalone-runtime",),
    ),
)

RUNTIME_THROTTLE_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "rethrottle_routes_support_task_id_path_variants",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "repeated_rethrottle_is_last_write_wins_with_list_and_get_readback",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_last_requested_rate_is_operator_visible_across_task_surfaces",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_rate_persists_across_shared_runtime_restart",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_request_during_restart_window_syncs_before_mutation",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_rejects_cancelled_and_terminal_tasks_without_mutating_rate",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_refuses_completion_race_without_mutating_last_rate",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_refuses_in_flight_completion_race_with_terminal_readback",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_refuses_shutdown_and_partial_recovery_without_mutating_rate",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_does_not_consume_task_submission_backpressure_capacity",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "active_throttled_task_admission_still_follows_task_submission_backpressure",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_parent_and_child_tasks_keep_independent_rate_readback",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_background_worker_child_tasks_keep_independent_rate_readback",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_cross_node_parent_and_child_tasks_keep_independent_rate_readback",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_multi_level_tasks_keep_independent_rate_readback",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
)

RUNTIME_TASK_METADATA_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "tasks_live_route_supports_list_get_and_cancel_shapes",
        "task-parent-metadata-runtime-state",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cat_tasks_route_serves_json_and_text_views",
        "task-parent-metadata-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_registry_table_describes_bounded_task_surface",
        "task-parent-metadata-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_parent_grouping_nests_child_tasks_under_existing_parent",
        "task-parent-metadata-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
)

RUNTIME_TASK_HEADERS_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "tasks_live_route_supports_list_get_and_cancel_shapes",
        "task-header-runtime-state",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cat_tasks_route_serves_json_and_text_views",
        "task-header-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
)

RUNTIME_TASK_CHILDREN_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "tasks_live_route_supports_list_get_and_cancel_shapes",
        "task-child-runtime-state",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_parent_grouping_nests_child_tasks_under_existing_parent",
        "task-child-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_cancel_by_parent_task_id_preserves_parent_child_visibility",
        "task-child-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_cancel_by_parent_task_id_propagates_to_same_node_descendants",
        "task-child-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_cancel_by_parent_task_id_propagates_to_cross_node_descendants",
        "task-child-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_cancel_by_parent_task_id_propagates_to_background_worker_descendants",
        "task-child-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_parent_and_child_tasks_keep_independent_rate_readback",
        "task-child-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_background_worker_child_tasks_keep_independent_rate_readback",
        "task-child-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_cross_node_parent_and_child_tasks_keep_independent_rate_readback",
        "task-child-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "rethrottle_multi_level_tasks_keep_independent_rate_readback",
        "task-child-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
)

RUNTIME_LIFECYCLE_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "runtime_lifecycle_hooks_describe_shutdown_and_recovery_admission_boundaries",
        "runtime-lifecycle-hooks",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cancelled_terminal_live_shutdown_preserves_progress_and_refuses_cancel",
        "runtime-lifecycle-shutdown",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cancelled_terminal_cancel_after_restart_sync_preserves_progress",
        "runtime-lifecycle-restart",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "task_submission_is_refused_during_live_shutdown_window",
        "runtime-lifecycle-task-admission",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "accepted_queued_task_submission_is_not_replayed_during_partial_recovery_error",
        "runtime-lifecycle-recovery",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
)

MODULE_REGISTRATION_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "extension_manifest_values_feed_effective_registry",
        "module-registration-boundary",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "extension_manifest_rejects_malformed_manifest_fail_closed",
        "module-registration-boundary",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "extension_manifest_rejects_java_plugin_abi_fail_closed",
        "module-registration-boundary",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "startup_extension_registry_transcript_lists_registered_components_by_profile",
        "module-registration-boundary",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cat_plugins_route_reports_extension_registry_modules",
        "module-registration-boundary",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cat_plugins_route_omits_disabled_extension_modules",
        "module-registration-boundary",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "extension_registry_registration_table_lists_enabled_routes_and_actions",
        "module-registration-boundary",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "extension_registry_uses_rust_native_extension_api_descriptors",
        "module-registration-boundary",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "extension_lifecycle_hooks_execute_for_activation_shutdown_and_recovery_boundaries",
        "module-registration-boundary",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "three_local_daemons_form_development_cluster_and_handle_index_smoke",
        "module-registration-boundary-live-daemon",
        package="os-node",
        target=("--test", "dev_cluster_daemons"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "three_local_daemons_expose_extension_shutdown_and_recovery_lifecycle_transcripts",
        "module-registration-boundary-live-daemon",
        package="os-node",
        target=("--test", "dev_cluster_daemons"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "plugin_exports_rust_native_extension_descriptor_surface",
        "module-registration-boundary",
        package="os-plugin-knn",
        target=("--lib",),
    ),
    ValidationTest(
        "plugin_exports_rust_native_extension_descriptor_surface",
        "module-registration-boundary",
        package="os-ml-commons",
        target=("--lib",),
    ),
)

MIXED_SHARD_MOVEMENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "three_node_shard_movement_exercises_both_interruption_directions",
        "mixed-shard-movement",
        (
            "python3",
            "tools/probe_three_node_shard_movement.py",
            "--work-dir",
            "/tmp/three-node-shard-movement.validation",
            "--exercise-interruption",
            "--require-interruption",
        ),
    ),
)

RUNTIME_PEER_BACKPRESSURE_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "steelsearch_remote_transport_backpressure_matches_opensearch_search_pool_rejection_readback",
        "runtime-fairness-peer-backpressure",
        (
            "python3",
            "tools/compare_remote_transport_backpressure.py",
            "--mode",
            "both",
            "--profile",
            "mixed-java-rust-query-phase",
            "--work-dir",
            "/tmp/remote-transport-backpressure-compare.validation",
        ),
        timeout_seconds=600,
    ),
)


BATCHES: dict[str, tuple[ValidationCase, ...]] = {
    "compact": COMPACT_BATCH,
    "rebucketing-wide": REBUCKETING_WIDE_BATCH,
    "vector-knn": VECTOR_KNN_BATCH,
    "source-backed-query": SOURCE_BACKED_QUERY_BATCH,
    "benchmark-telemetry": BENCHMARK_TELEMETRY_BATCH,
    "mixed-shard-movement": MIXED_SHARD_MOVEMENT_BATCH,
    "startup-preflight": STARTUP_PREFLIGHT_BATCH,
    "startup-readiness": STARTUP_READINESS_BATCH,
    "production-security": PRODUCTION_SECURITY_BATCH,
    "runtime-tasks": RUNTIME_TASKS_BATCH,
    "runtime-queue": RUNTIME_QUEUE_BATCH,
    "runtime-backpressure": RUNTIME_BACKPRESSURE_BATCH,
    "runtime-fairness": RUNTIME_FAIRNESS_BATCH,
    "runtime-peer-backpressure": RUNTIME_PEER_BACKPRESSURE_BATCH,
    "runtime-throttle": RUNTIME_THROTTLE_BATCH,
    "runtime-task-metadata": RUNTIME_TASK_METADATA_BATCH,
    "runtime-task-headers": RUNTIME_TASK_HEADERS_BATCH,
    "runtime-task-children": RUNTIME_TASK_CHILDREN_BATCH,
    "runtime-lifecycle": RUNTIME_LIFECYCLE_BATCH,
    "module-registration": MODULE_REGISTRATION_BATCH,
}

RUNNING_RE = re.compile(r"running (?P<count>\d+) tests?")
RESULT_RE = re.compile(
    r"test result: (?P<status>\w+)\. (?P<passed>\d+) passed; (?P<failed>\d+) failed;"
)


def parse_test_output(output: str) -> dict[str, Any]:
    running = 0
    passed = 0
    failed = 0
    status = "unknown"
    for line in output.splitlines():
        running_match = RUNNING_RE.search(line)
        if running_match:
            running = max(running, int(running_match.group("count")))
        result_match = RESULT_RE.search(line)
        if result_match:
            status = result_match.group("status")
            passed = int(result_match.group("passed"))
            failed = int(result_match.group("failed"))
    return {
        "running": running,
        "passed": passed,
        "failed": failed,
        "status": status,
    }


def parse_json_payload(output: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(output):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def run_cargo_test(test: ValidationTest) -> dict[str, Any]:
    command = [
        "cargo",
        "test",
        "-p",
        test.package,
    ]
    if test.features:
        command.extend(["--features", ",".join(test.features)])
    command.extend([
        *test.target,
        test.name,
    ])
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    parsed = parse_test_output(completed.stdout)
    ok = completed.returncode == 0 and parsed["running"] > 0 and parsed["failed"] == 0
    return {
        "name": test.name,
        "group": test.group,
        "command": command,
        "returncode": completed.returncode,
        "ok": ok,
        **parsed,
    }


def run_external_validation(test: ExternalValidation) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            list(test.command),
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=test.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "name": test.name,
            "group": test.group,
            "command": list(test.command),
            "returncode": None,
            "ok": False,
            "running": 1,
            "passed": 0,
            "failed": 1,
            "status": "timeout",
            "summary": {"passed": False, "timeout_seconds": test.timeout_seconds},
            "output": exc.output,
        }
    payload = parse_json_payload(completed.stdout)
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    summary_passed = bool(summary.get("passed")) if isinstance(summary, dict) else False
    ok = completed.returncode == 0 and summary_passed
    return {
        "name": test.name,
        "group": test.group,
        "command": list(test.command),
        "returncode": completed.returncode,
        "ok": ok,
        "running": 1,
        "passed": 1 if ok else 0,
        "failed": 0 if ok else 1,
        "status": "ok" if ok else "failed",
        "summary": summary,
    }


def run_test(test: ValidationCase) -> dict[str, Any]:
    if isinstance(test, ExternalValidation):
        return run_external_validation(test)
    return run_cargo_test(test)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--batch",
        choices=tuple(BATCHES),
        default="compact",
        help="validation batch to run",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format",
    )
    args = parser.parse_args()

    tests = BATCHES[args.batch]
    results = [run_test(test) for test in tests]
    summary = {
        "batch": args.batch,
        "test_count": len(results),
        "passed_count": sum(1 for result in results if result["ok"]),
        "failed_count": sum(1 for result in results if not result["ok"]),
        "zero_test_count": sum(1 for result in results if result["running"] == 0),
    }
    report = {"summary": summary, "results": results}

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "batch={batch} passed={passed_count}/{test_count} failed={failed_count} zero_tests={zero_test_count}".format(
                **summary
            )
        )
        for result in results:
            state = "ok" if result["ok"] else "failed"
            print(
                f"{state}\t{result['group']}\t{result['name']}\t"
                f"running={result['running']} passed={result['passed']} failed={result['failed']}"
            )

    return 0 if summary["failed_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
