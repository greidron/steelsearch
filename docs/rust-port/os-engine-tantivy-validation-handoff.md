# os-engine-tantivy validation handoff

Current state:
- Source-only wrapper-family and representative rebucketing coverage is broadly converged.
- Goal completion is still unproven because runtime evidence is missing.
- Use exact-name test runs to convert the current source-visible matrix into runtime evidence.

Crate:
- `os-engine-tantivy`

Command shape:
- `cargo test -p os-engine-tantivy -- --exact <test_name>`

Phase 1: malformed-wrapper sanity
- `cargo test -p os-engine-tantivy -- --exact engine_collects_placeholder_for_malformed_plugin_bucket_sort_request`
- `cargo test -p os-engine-tantivy -- --exact engine_collects_placeholder_for_malformed_plugin_derivative_request`
- `cargo test -p os-engine-tantivy -- --exact engine_collects_placeholder_for_malformed_plugin_serial_diff_request`
- `cargo test -p os-engine-tantivy -- --exact engine_collects_placeholder_for_malformed_plugin_bucket_count_request`

Phase 2: representative date_histogram rebucketing
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_sort_surface`
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_count_surface`
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_derivative_surface`
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_serial_diff_surface`

Phase 3: widening order
- `auto_date_histogram`
- `histogram`
- `variable_width_histogram`

Phase 3a: auto_date_histogram block
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_count_surface`
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_derivative_surface`
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_serial_diff_surface`
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_sort_surface`

Phase 3b: histogram block
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_count_surface`
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_histogram_reduce_feeds_derivative_surface`
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_histogram_reduce_feeds_serial_diff_surface`
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_sort_surface`

Phase 3c: variable_width_histogram block
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_count_surface`
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_derivative_surface`
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_serial_diff_surface`
- `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_sort_surface`

Failure triage order:
- Fix malformed-wrapper failures first.
- Fix `date_histogram` rebucketing failures second.
- Only then widen attention to `auto_date_histogram`, `histogram`, and `variable_width_histogram`.

Interpretation:
- If Phase 1 fails, treat it as a basic request-surface or placeholder-contract mismatch.
- If Phase 1 passes and Phase 2 fails, treat it as the highest-leverage mixed rebucketing bug.
- If Phase 1 and Phase 2 pass but Phase 3 fails, treat the first failing family as the frontier.

Completion criterion:
- Source-only evidence is not enough.
- Goal completion requires inspected runtime results for the exact-name batches above.
