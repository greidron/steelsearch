#!/usr/bin/env bash
set -euo pipefail

run() {
  cargo test -p os-engine-tantivy -- --exact "$1"
}

phase1() {
  run engine_collects_placeholder_for_malformed_plugin_bucket_sort_request
  run engine_collects_placeholder_for_malformed_plugin_derivative_request
  run engine_collects_placeholder_for_malformed_plugin_serial_diff_request
  run engine_collects_placeholder_for_malformed_plugin_bucket_count_request
}

phase2() {
  run search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_sort_surface
  run search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_count_surface
  run search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_derivative_surface
  run search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_serial_diff_surface
}

phase3a() {
  run search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_count_surface
  run search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_derivative_surface
  run search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_serial_diff_surface
  run search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_sort_surface
}

phase3b() {
  run search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_count_surface
  run search_size_zero_multi_index_plugin_histogram_reduce_feeds_derivative_surface
  run search_size_zero_multi_index_plugin_histogram_reduce_feeds_serial_diff_surface
  run search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_sort_surface
}

phase3c() {
  run search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_count_surface
  run search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_derivative_surface
  run search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_serial_diff_surface
  run search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_sort_surface
}

usage() {
  cat <<'EOF'
Usage:
  scripts/os-engine-tantivy-validation-handoff.sh phase1
  scripts/os-engine-tantivy-validation-handoff.sh phase2
  scripts/os-engine-tantivy-validation-handoff.sh phase3a
  scripts/os-engine-tantivy-validation-handoff.sh phase3b
  scripts/os-engine-tantivy-validation-handoff.sh phase3c
  scripts/os-engine-tantivy-validation-handoff.sh all
EOF
}

main() {
  local phase="${1:-}"
  case "$phase" in
    phase1) phase1 ;;
    phase2) phase2 ;;
    phase3a) phase3a ;;
    phase3b) phase3b ;;
    phase3c) phase3c ;;
    all)
      phase1
      phase2
      phase3a
      phase3b
      phase3c
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
