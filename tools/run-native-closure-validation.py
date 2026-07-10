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
    ValidationTest(
        "search_cache_telemetry_tracks_wired_runtime_cache_surfaces",
        "vector-runtime-cache-telemetry",
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
        "native_nested_child_ordinals_support_query_string_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_simple_query_string_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_more_like_this_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_geo_distance_leaf_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_dis_max_wrapper_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_score_wrappers_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_boosting_wrapper_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_span_term_and_or_without_source_validation",
        "source-backed-native-query",
    ),
    ValidationTest(
        "native_nested_child_ordinals_support_span_near_and_multi_without_source_validation",
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
        "span_first_text_leaf_uses_source_candidate_native_page",
        "source-backed-native-query",
    ),
    ValidationTest(
        "span_containing_mixed_shape_uses_source_candidate_native_page",
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

MATERIALIZATION_PRIORITY_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "targeted_materialization_priority_report_has_zero_ranked_operations",
        "materialization-priority-current",
        (
            "python3",
            "tools/check-materialization-priority-report.py",
            "target/materialization-priority-targeted-current/materialization-priority.json",
            "--require-passed",
            "--require-zero-ranked",
        ),
        timeout_seconds=60,
    ),
)

NON_NATIVE_INVENTORY_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "non_native_path_inventory_has_no_missing_probe_or_family",
        "non-native-inventory",
        (
            "python3",
            "tools/report-non-native-paths.py",
            "--format",
            "json",
        ),
        timeout_seconds=60,
    ),
)

E2E_REQUIRED_PARITY_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "search_semantic_and_vector_search_e2e_reports_have_no_failed_missing_or_skipped_cases",
        "e2e-required-parity",
        (
            "python3",
            "-c",
            "import subprocess, sys; output_dir = 'target/unified-opensearch-e2e-audit'; collect = [sys.executable, 'tools/run-unified-opensearch-e2e.py', '--output-dir', output_dir, '--max-report-age-seconds', '604800', '--suite', 'search-semantic', '--suite', 'vector-search', '--suite', 'vector-search-native-surface']; check = [sys.executable, 'tools/check-unified-opensearch-e2e-report.py', f'{output_dir}/unified-opensearch-e2e-report.json', '--require-no-unresolved-skips']; first = subprocess.run(collect, stdout=subprocess.DEVNULL); sys.exit(first.returncode) if first.returncode else sys.exit(subprocess.run(check).returncode)",
        ),
        timeout_seconds=120,
    ),
)

E2E_SEARCH_COMPAT_PARITY_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "search_compat_and_strict_e2e_reports_have_no_failed_or_missing_cases",
        "e2e-search-compat-parity",
        (
            "python3",
            "-c",
            "import subprocess, sys; output_dir = 'target/unified-opensearch-e2e-current'; report = f'{output_dir}/unified-opensearch-e2e-report.json'; collect = [sys.executable, 'tools/run-unified-opensearch-e2e.py', '--output-dir', output_dir, '--max-report-age-seconds', '604800', '--suite', 'search-compat', '--suite', 'search-strict', '--suite', 'vector-search-native-surface', '--suite', 'knn-plugin-surface', '--suite', 'ml-model-surface']; check = [sys.executable, 'tools/check-unified-opensearch-e2e-report.py', report, '--require-no-unresolved-skips']; first = subprocess.run(collect, stdout=subprocess.DEVNULL); sys.exit(first.returncode) if first.returncode else sys.exit(subprocess.run(check).returncode)",
        ),
        timeout_seconds=120,
    ),
    ExternalValidation(
        "pit_e2e_reports_have_required_opensearch_compared_cases_without_skips",
        "e2e-search-compat-parity",
        (
            "python3",
            "-c",
            "import subprocess, sys; output_dir = 'target/unified-opensearch-e2e-pit-current'; report = f'{output_dir}/unified-opensearch-e2e-report.json'; collect = [sys.executable, 'tools/run-unified-opensearch-e2e.py', '--output-dir', output_dir, '--max-report-age-seconds', '604800', '--suite', 'search-compat', '--suite', 'search-strict', '--suite', 'search-semantic', '--suite', 'vector-search-native-surface', '--suite', 'knn-plugin-surface', '--suite', 'ml-model-surface']; pit_check = [sys.executable, 'tools/check-pit-e2e-coverage.py', report, '--require-all-pit-passed']; skip_check = [sys.executable, 'tools/check-unified-opensearch-e2e-report.py', report, '--require-no-unresolved-skips']; first = subprocess.run(collect, stdout=subprocess.DEVNULL); sys.exit(first.returncode) if first.returncode else sys.exit(subprocess.run(pit_check).returncode or subprocess.run(skip_check).returncode)",
        ),
        timeout_seconds=120,
    ),
)

BROAD_E2E_PARITY_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "broad_unified_opensearch_e2e_report_has_no_failed_missing_or_drifted_required_suites",
        "e2e-broad-parity",
        (
            "python3",
            "-c",
            "import subprocess, sys; output_dir = 'target/unified-opensearch-e2e-broad-current'; collect = [sys.executable, 'tools/run-unified-opensearch-e2e.py', '--output-dir', output_dir, '--max-report-age-seconds', '604800']; check = [sys.executable, 'tools/check-unified-opensearch-e2e-report.py', f'{output_dir}/unified-opensearch-e2e-report.json', '--require-no-unresolved-skips', '--require-section', 'route_parity', '--require-section', 'semantic_parity', '--require-section', 'durability_parity', '--require-section', 'security_parity', '--require-section', 'distributed_parity']; first = subprocess.run(collect, stdout=subprocess.DEVNULL); sys.exit(first.returncode) if first.returncode else sys.exit(subprocess.run(check).returncode)",
        ),
        timeout_seconds=180,
    ),
)

REST_API_COVERAGE_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "rest_api_source_inventory_coverage_is_reported_for_broad_required_live_suites",
        "rest-api-coverage-current",
        (
            "python3",
            "-c",
            "import subprocess, sys; output_dir = 'target/unified-opensearch-e2e-broad-current'; collect = [sys.executable, 'tools/run-unified-opensearch-e2e.py', '--output-dir', output_dir, '--max-report-age-seconds', '604800']; coverage = [sys.executable, 'tools/report-rest-api-coverage.py', '--unified-report', f'{output_dir}/unified-opensearch-e2e-report.json', '--require-live-required-suites', '--min-live-required-matched-source-route-count', '378', '--min-live-required-matched-source-route-ratio', '1.0', '--min-source-route-count', '389', '--output', 'target/rest-api-coverage-current.json']; first = subprocess.run(collect, stdout=subprocess.DEVNULL); sys.exit(first.returncode) if first.returncode else sys.exit(subprocess.run(coverage).returncode)",
        ),
        timeout_seconds=120,
    ),
)

TRANSPORT_ACTION_COVERAGE_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "transport_action_inventory_is_reported_with_current_peer_backpressure_evidence",
        "transport-action-coverage-current",
        (
            "python3",
            "tools/report-transport-action-coverage.py",
            "--require-peer-backpressure",
            "--require-release-parity",
            "--max-report-age-seconds",
            "604800",
            "--output",
            "target/transport-action-coverage-current.json",
        ),
        timeout_seconds=60,
    ),
)

MIXED_CLUSTER_COVERAGE_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "mixed_cluster_join_and_movement_coverage_is_reported_with_scope_boundary",
        "mixed-cluster-coverage-current",
        (
            "python3",
            "tools/report-mixed-cluster-coverage.py",
            "--require-passed",
            "--max-report-age-seconds",
            "5184000",
            "--output",
            "target/mixed-cluster-coverage-current.json",
        ),
        timeout_seconds=60,
    ),
    ExternalValidation(
        "multi_node_transport_admin_report_requires_remote_pit_forwarding_cases",
        "mixed-cluster-coverage-current",
        (
            "python3",
            "tools/check-multi-node-transport-admin-report.py",
            "target/dev-pit-transport-current/multi-node-transport-admin-report.json",
            "--require-remote-pit",
        ),
        timeout_seconds=30,
    ),
)

RELEASE_READINESS_TOOLING_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "release_readiness_writer_and_manifest_checker_contract",
        "release-readiness-tooling",
        (
            "python3",
            "-c",
            "import json, subprocess, sys; result = subprocess.run([sys.executable, '-m', 'unittest', 'tools/test_replacement_gate_scripts.py']); passed = result.returncode == 0; print(json.dumps({'summary': {'passed': passed, 'commands': 1}})); sys.exit(0 if passed else 1)",
        ),
        timeout_seconds=60,
    ),
)

PRODUCTION_SECURITY_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "production_security_batch_has_no_authn_authz_tls_or_fail_closed_regressions",
        "production-security-current",
        (
            "python3",
            "-c",
            "import json, subprocess, sys; command = [sys.executable, 'tools/run-native-closure-validation.py', '--batch', 'production-security', '--format', 'json']; result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True); payload = json.loads(result.stdout[result.stdout.find('{'):]); summary = payload.get('summary', {}); passed = result.returncode == 0 and summary.get('failed_count') == 0 and summary.get('test_count', 0) > 0 and summary.get('zero_test_count') == 0; print(json.dumps({'summary': {'passed': passed, 'batch': summary.get('batch'), 'test_count': summary.get('test_count'), 'failed_count': summary.get('failed_count')}})); sys.exit(0 if passed else 1)",
        ),
        timeout_seconds=240,
    ),
)

STARTUP_BOOTSTRAP_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "startup_preflight_and_readiness_batches_have_no_bootstrap_or_readiness_regressions",
        "startup-bootstrap-current",
        (
            "python3",
            "-c",
            "import json, subprocess, sys; batches = ['startup-preflight', 'startup-readiness']; summaries = {}; passed = True\nfor batch in batches:\n    command = [sys.executable, 'tools/run-native-closure-validation.py', '--batch', batch, '--format', 'json']\n    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)\n    payload = json.loads(result.stdout[result.stdout.find('{'):])\n    summary = payload.get('summary', {})\n    summaries[batch] = {'test_count': summary.get('test_count'), 'failed_count': summary.get('failed_count'), 'zero_test_count': summary.get('zero_test_count')}\n    passed = passed and result.returncode == 0 and summary.get('failed_count') == 0 and summary.get('test_count', 0) > 0 and summary.get('zero_test_count') == 0\nprint(json.dumps({'summary': {'passed': passed, 'batches': summaries}}))\nsys.exit(0 if passed else 1)",
        ),
        timeout_seconds=360,
    ),
)

RUNTIME_CONTROLS_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "runtime_control_batches_have_no_queue_backpressure_fairness_or_lifecycle_regressions",
        "runtime-controls-current",
        (
            "python3",
            "tools/run-validation-batch-group.py",
            "runtime-tasks",
            "runtime-queue",
            "runtime-backpressure",
            "runtime-fairness",
            "runtime-throttle",
            "runtime-task-metadata",
            "runtime-task-headers",
            "runtime-task-children",
            "runtime-lifecycle",
            "module-registration",
        ),
        timeout_seconds=1200,
    ),
)

RELEASE_EVIDENCE_INVENTORY_GATE_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "release_evidence_inventory_current_batch_has_complete_startup_and_readiness_artifacts",
        "release-evidence-inventory-current",
        (
            "python3",
            "-c",
            "import json, subprocess, sys; command = [sys.executable, 'tools/run-native-closure-validation.py', '--batch', 'release-evidence-inventory-current', '--format', 'json']; result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True); payload = json.loads(result.stdout[result.stdout.find('{'):]); summary = payload.get('summary', {}); passed = result.returncode == 0 and summary.get('failed_count') == 0 and summary.get('test_count', 0) > 0 and summary.get('zero_test_count') == 0; print(json.dumps({'summary': {'passed': passed, 'batch': summary.get('batch'), 'test_count': summary.get('test_count'), 'failed_count': summary.get('failed_count')}})); sys.exit(0 if passed else 1)",
        ),
        timeout_seconds=120,
    ),
)

CURRENT_EVIDENCE_GATE_BATCH: tuple[ExternalValidation, ...] = (
    *NON_NATIVE_INVENTORY_BATCH,
    *E2E_REQUIRED_PARITY_BATCH,
    *E2E_SEARCH_COMPAT_PARITY_BATCH,
    *BROAD_E2E_PARITY_BATCH,
    *REST_API_COVERAGE_CURRENT_BATCH,
    *TRANSPORT_ACTION_COVERAGE_CURRENT_BATCH,
    *MIXED_CLUSTER_COVERAGE_CURRENT_BATCH,
    *MATERIALIZATION_PRIORITY_CURRENT_BATCH,
    *PRODUCTION_SECURITY_CURRENT_BATCH,
    *STARTUP_BOOTSTRAP_CURRENT_BATCH,
    *RUNTIME_CONTROLS_CURRENT_BATCH,
    *RELEASE_EVIDENCE_INVENTORY_GATE_BATCH,
    *RELEASE_READINESS_TOOLING_BATCH,
)

RELEASE_READINESS_CURRENT_COMMAND = (
    "import json, subprocess, sys\n"
    "attach_command = [\n"
    "    sys.executable, 'tools/attach-release-readiness-evidence.py',\n"
    "    '--readiness-report', 'target/release-readiness/readiness-report.json',\n"
    "    '--create-readiness-report',\n"
    "    '--benchmark-report', 'target/release-benchmarks/deterministic-benchmark-baselines.jsonl',\n"
    "    '--load-report', 'target/release-load-current/http-load-baseline.json',\n"
    "    '--load-comparison-report', 'target/release-load-comparison/http-load-comparison.json',\n"
    "    '--chaos-report', 'target/release-chaos/chaos-report.json',\n"
    "    '--packaging-report', 'target/release-packaging/packaging-report.json',\n"
    "    '--rolling-upgrade-report', 'target/release-rolling-upgrade/rolling-upgrade-report.json',\n"
    "    '--release-readiness-file', 'target/release-readiness/release-readiness.json',\n"
    "    '--max-age-seconds', '604800',\n"
    "]\n"
    "check_command = [\n"
    "    sys.executable, 'tools/check-release-readiness-evidence.py',\n"
    "    'target/release-readiness/release-readiness.json', '--require-passed',\n"
    "]\n"
    "attach = subprocess.run(attach_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)\n"
    "check = subprocess.run(check_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)\n"
    "payload = None\n"
    "try:\n"
    "    payload = json.loads(check.stdout[check.stdout.find('{'):]) if '{' in check.stdout else None\n"
    "except json.JSONDecodeError:\n"
    "    payload = None\n"
    "summary = payload.get('summary', {}) if isinstance(payload, dict) else {}\n"
    "errors = payload.get('errors', []) if isinstance(payload, dict) else ['missing checker payload']\n"
    "passed = attach.returncode == 0 and check.returncode == 0 and payload is not None and payload.get('status') == 'ok' and not errors\n"
    "print(json.dumps({'summary': {\n"
    "    'passed': passed,\n"
    "    'attach_returncode': attach.returncode,\n"
    "    'check_returncode': check.returncode,\n"
    "    'checker_status': payload.get('status') if isinstance(payload, dict) else None,\n"
    "    'error_count': len(errors),\n"
    "    'ready_items': summary.get('ready_items'),\n"
    "    'required_items': summary.get('required_items'),\n"
    "}}))\n"
    "sys.exit(0 if passed else 1)"
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
        "tasks_cancel_root_route_without_selectors_cancels_all_cancellable_tasks_like_opensearch",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_list_honors_node_action_and_parent_filters_like_opensearch",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_get_unknown_task_uses_opensearch_not_found_shape",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_cancel_rejects_task_id_with_node_selectors_like_opensearch",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_cancel_task_id_honors_action_and_parent_selectors_like_opensearch",
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
        "tasks_cancel_by_parent_task_id_honors_node_and_action_selectors_like_opensearch",
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
        "tier_routes_are_not_registered_by_default_after_restart",
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
            "--output",
            "target/runtime-peer-backpressure-current.json",
        ),
        timeout_seconds=600,
    ),
)

RUNTIME_PEER_BACKPRESSURE_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "runtime_peer_backpressure_current_report_preserves_profile_and_counters",
        "runtime-fairness-peer-backpressure-current",
        (
            "python3",
            "tools/check-runtime-peer-backpressure-report.py",
            "target/runtime-peer-backpressure-current.json",
        ),
        timeout_seconds=60,
    ),
)

NATIVE_CLOSURE_STATUS_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "native_closure_status_report_writes_final_cutover_ready_artifact",
        "native-closure-status-current",
        (
            "python3",
            "tools/report-native-closure-status.py",
            "--release-readiness-file",
            "target/release-readiness/release-readiness.json",
            "--readiness-report",
            "target/release-readiness/readiness-report.json",
            "--release-evidence-max-age-seconds",
            "604800",
            "--require-final-cutover",
            "--output",
            "target/native-closure-status-current.json",
        ),
        timeout_seconds=1200,
    ),
    ExternalValidation(
        "native_closure_status_report_preserves_required_gate_contract",
        "native-closure-status-current",
        (
            "python3",
            "tools/check-native-closure-status-report.py",
            "target/native-closure-status-current.json",
            "--require-final-cutover",
            "--require-current-head",
            "--require-clean-worktree",
        ),
        timeout_seconds=60,
    ),
)

RELEASE_EVIDENCE_INVENTORY_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "release_evidence_inventory_generates_promotion_gate_suite_artifact",
        "release-evidence-inventory-current",
        (
            "python3",
            "-c",
            "import json, subprocess, sys; command = [sys.executable, 'tools/check-all-promotion-gates.py', '--output', 'target/promotion-gate-suite-current.json']; result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True); payload = json.loads(result.stdout[result.stdout.find('{'):]); passed = result.returncode == 0 and payload.get('status') == 'ok' and payload.get('failed') == 0 and payload.get('passed') == len(payload.get('checks', [])); print(json.dumps({'summary': {'passed': passed, 'checks': len(payload.get('checks', [])), 'failed': payload.get('failed')}})); sys.exit(0 if passed else 1)",
        ),
        timeout_seconds=120,
    ),
    ExternalValidation(
        "release_evidence_inventory_reports_current_candidate_artifacts",
        "release-evidence-inventory-current",
        (
            "python3",
            "tools/report-release-evidence-inventory.py",
            "--root",
            "target",
            "--max-age-seconds",
            "604800",
            "--require-complete",
            "--output",
            "target/release-evidence-inventory-current.json",
        ),
        timeout_seconds=60,
    ),
    ExternalValidation(
        "release_evidence_inventory_writes_and_checks_final_cutover_manifest",
        "release-evidence-inventory-current",
        (
            "python3",
            "-c",
            RELEASE_READINESS_CURRENT_COMMAND,
        ),
        timeout_seconds=60,
    ),
)

PACKAGING_EVIDENCE_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "packaging_evidence_builds_release_steelsearch_binary",
        "packaging-evidence-current",
        (
            "python3",
            "tools/generate-packaging-evidence.py",
            "--output",
            "target/release-packaging/packaging-report.json",
        ),
        timeout_seconds=900,
    ),
)

BENCHMARK_EVIDENCE_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "benchmark_evidence_runs_deterministic_tantivy_baselines",
        "benchmark-evidence-current",
        (
            "python3",
            "tools/generate-benchmark-evidence.py",
            "--output",
            "target/release-benchmarks/deterministic-benchmark-baselines.jsonl",
            "--report",
            "target/release-benchmarks/benchmark-report.json",
        ),
        timeout_seconds=600,
    ),
)

LOAD_EVIDENCE_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "load_evidence_runs_release_steelsearch_http_baseline",
        "load-evidence-current",
        (
            "python3",
            "tools/generate-load-evidence.py",
            "--output",
            "target/release-load-current/http-load-baseline.json",
        ),
        timeout_seconds=240,
    ),
)

LOAD_COMPARISON_EVIDENCE_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "load_comparison_evidence_runs_steelsearch_opensearch_http_baseline",
        "load-comparison-evidence-current",
        (
            "python3",
            "tools/generate-load-comparison-evidence.py",
            "--output",
            "target/release-load-comparison/http-load-comparison.json",
            "--query-mix",
            "write=25,lexical=25,ranking=20,facet=15,sort_filter=10,refresh=5",
        ),
        timeout_seconds=420,
    ),
)

ROLLING_UPGRADE_EVIDENCE_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "rolling_upgrade_evidence_runs_ordered_transcript_fixture",
        "rolling-upgrade-evidence-current",
        (
            "python3",
            "tools/generate-rolling-upgrade-evidence.py",
            "--output",
            "target/release-rolling-upgrade/rolling-upgrade-report.json",
        ),
        timeout_seconds=120,
    ),
)

CHAOS_EVIDENCE_CURRENT_BATCH: tuple[ExternalValidation, ...] = (
    ExternalValidation(
        "chaos_evidence_runs_mixed_cluster_failure_fixture",
        "chaos-evidence-current",
        (
            "python3",
            "tools/generate-chaos-evidence.py",
            "--work-dir",
            "target/release-chaos",
            "--output",
            "target/release-chaos/chaos-report.json",
        ),
        timeout_seconds=300,
    ),
)


BATCHES: dict[str, tuple[ValidationCase, ...]] = {
    "compact": COMPACT_BATCH,
    "rebucketing-wide": REBUCKETING_WIDE_BATCH,
    "vector-knn": VECTOR_KNN_BATCH,
    "source-backed-query": SOURCE_BACKED_QUERY_BATCH,
    "non-native-inventory": NON_NATIVE_INVENTORY_BATCH,
    "e2e-required-parity": E2E_REQUIRED_PARITY_BATCH,
    "e2e-search-compat-parity": E2E_SEARCH_COMPAT_PARITY_BATCH,
    "e2e-broad-parity": BROAD_E2E_PARITY_BATCH,
    "rest-api-coverage-current": REST_API_COVERAGE_CURRENT_BATCH,
    "transport-action-coverage-current": TRANSPORT_ACTION_COVERAGE_CURRENT_BATCH,
    "mixed-cluster-coverage-current": MIXED_CLUSTER_COVERAGE_CURRENT_BATCH,
    "benchmark-telemetry": BENCHMARK_TELEMETRY_BATCH,
    "materialization-priority-current": MATERIALIZATION_PRIORITY_CURRENT_BATCH,
    "release-readiness-tooling": RELEASE_READINESS_TOOLING_BATCH,
    "current-evidence-gate": CURRENT_EVIDENCE_GATE_BATCH,
    "mixed-shard-movement": MIXED_SHARD_MOVEMENT_BATCH,
    "startup-preflight": STARTUP_PREFLIGHT_BATCH,
    "startup-readiness": STARTUP_READINESS_BATCH,
    "production-security": PRODUCTION_SECURITY_BATCH,
    "runtime-controls-current": RUNTIME_CONTROLS_CURRENT_BATCH,
    "runtime-tasks": RUNTIME_TASKS_BATCH,
    "runtime-queue": RUNTIME_QUEUE_BATCH,
    "runtime-backpressure": RUNTIME_BACKPRESSURE_BATCH,
    "runtime-fairness": RUNTIME_FAIRNESS_BATCH,
    "runtime-peer-backpressure": RUNTIME_PEER_BACKPRESSURE_BATCH,
    "runtime-peer-backpressure-current": RUNTIME_PEER_BACKPRESSURE_CURRENT_BATCH,
    "native-closure-status-current": NATIVE_CLOSURE_STATUS_CURRENT_BATCH,
    "release-evidence-inventory-current": RELEASE_EVIDENCE_INVENTORY_CURRENT_BATCH,
    "packaging-evidence-current": PACKAGING_EVIDENCE_CURRENT_BATCH,
    "benchmark-evidence-current": BENCHMARK_EVIDENCE_CURRENT_BATCH,
    "load-evidence-current": LOAD_EVIDENCE_CURRENT_BATCH,
    "load-comparison-evidence-current": LOAD_COMPARISON_EVIDENCE_CURRENT_BATCH,
    "rolling-upgrade-evidence-current": ROLLING_UPGRADE_EVIDENCE_CURRENT_BATCH,
    "chaos-evidence-current": CHAOS_EVIDENCE_CURRENT_BATCH,
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
