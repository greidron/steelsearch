# Search benchmark optimization handoff

Date: 2026-06-30
Workspace: `/home/ubuntu/steelsearch`

## Current status

The latest retained benchmark run is a full `minilm-knn` matrix with
single-node and three-node Steelsearch/OpenSearch scenarios.

Latest benchmark artifact:

- `target/search-benchmark-matrix-current-20260630T023334Z/summary.json`

Latest OpenSearch throughput comparison:

| Topology | Ratio |
| --- | ---: |
| 1-node | 0.054x |
| 3-node | 0.103x |

Latest RSS peak comparison:

| Topology | Ratio |
| --- | ---: |
| 1-node | 1.580x |
| 3-node | 1.243x |

Latest per-operation throughput ratios:

| Operation | 1-node ratio | 3-node ratio |
| --- | ---: | ---: |
| facet | 0.059x | 0.094x |
| hybrid | 0.031x | 0.065x |
| lexical | 0.057x | 0.128x |
| nested | 0.048x | 0.109x |
| ranking | 0.056x | 0.100x |
| refresh | 0.060x | 0.123x |
| sort_filter | 0.056x | 0.116x |
| vector | 0.061x | 0.098x |
| write | 0.055x | 0.099x |

Latest native-path follow-up benchmarks after the full matrix:

| Run | Scope | Before | After | Ratio |
| --- | --- | ---: | ---: | ---: |
| `target/search-benchmark-sort-filter-native-20260630T041058Z/summary.json` | 1-client `sort_filter=100` throughput | 4.64 ops/s | 100.87 ops/s | 21.73x |
| `target/search-benchmark-sort-filter-native-20260630T041058Z/summary.json` | 1-client `sort_filter=100` p95 latency | 238.00 ms | 13.53 ms | 0.057x |
| `target/search-benchmark-native-sort-mixed-20260630T041127Z/summary.json` | 4-client mixed non-vector throughput | 28.49 ops/s | 104.69 ops/s | 3.67x |
| `target/search-benchmark-native-sort-mixed-20260630T041127Z/summary.json` | 4-client mixed `sort_filter` p95 latency | 634.21 ms | 79.83 ms | 0.126x |

Both follow-up runs reported zero `materialized_response_fetches` and zero
`compatibility_materialized_response_fetches`.

Remaining slower-than-OpenSearch points in the latest run:

| Topology | Operation | Metric | SteelSearch | OpenSearch | Ratio |
| --- | --- | --- | ---: | ---: | ---: |
| 1-node | overall | throughput | 11.10 ops/s | 204.20 ops/s | 0.054x |
| 3-node | overall | throughput | 8.74 ops/s | 85.02 ops/s | 0.103x |

Interpretation:

- The latest full matrix is materially slower than OpenSearch on every measured
  throughput case.
- Steelsearch RSS peak is larger than OpenSearch in both measured topologies in
  this run.
- The benchmark runner now distributes three-node timed workload and seed corpus
  writes across all node HTTP URLs. The latest Steelsearch three-node run showed
  balanced node CPU during seed, so the remaining slowdown is not the previous
  single-coordinator benchmark artifact.
- The dominant observed cost in the latest full matrix is Steelsearch seed/write
  and mixed search latency at the 5,000-document corpus size.
- Current benchmark reports now include a SteelSearch materialization budget
  table for `materialized_response_fetches` and
  `compatibility_materialized_response_fetches`, normalized by successful
  operation count, so future runs can flag high-delta materialized fallback
  regressions directly in the JSON/Markdown artifacts.
- `tools/run-http-load-baseline.py --operation-resource-deltas` now records
  operation-level native telemetry deltas for the same counters. Use it with
  `--clients 1` when the goal is exact per-case materialization attribution;
  the matrix runner forwards the same flag and renders operation-level
  materialization budget rows when those deltas are present.
- The load runner also has opt-in fallback workloads for materialization
  diagnostics: `fallback_query_string`, `fallback_terms_set`,
  `fallback_distance_feature`, `fallback_rank_feature`,
  `fallback_more_like_this`, and `fallback_case_insensitive_wildcard`. They are
  not in the default comparison mix; run them explicitly with `--clients 1
  --operation-resource-deltas` for exact attribution. Current retained evidence
  shows the default broader mix at
  `target/materialization-priority-broader-current/` has zero materialized
  response fetches, while the targeted fallback matrix at
  `target/materialization-priority-targeted-current/` has removed
  `fallback_distance_feature`, `fallback_rank_feature`,
  `fallback_terms_set`, `fallback_more_like_this`, and
  `fallback_case_insensitive_wildcard` from the priority list; its priority
  report now passes with `ranked_operation_count=0`. The matrix runner clears a
  scenario output directory before a fresh run so stale gateway manifests from
  previous ports do not poison repeat local slices.
- Fresh materialization-priority diagnostic:
  `target/materialization-priority-targeted-current/materialization-priority.json`
  reports `ranked_operation_count=0` after `557` successful
  `fallback_query_string` operations, with zero materialized and compatibility
  materialized response fetch deltas. The retained gate
  `tools/run-native-closure-validation.py --batch materialization-priority-current`
  passes against that artifact.

Functional OpenSearch E2E comparison status:

- Current unified report: `target/unified-opensearch-e2e-current/unified-opensearch-e2e-report.json`
- Current audit report: `target/unified-opensearch-e2e-audit/unified-opensearch-e2e-report.json`
- Fresh PIT live subset report:
  `target/opensearch-compare-pit-current/search-compat-report.json`
- Fresh PIT operational live subset report:
  `target/opensearch-compare-pit-ops-current/search-compat-report.json`
- Fresh stats live subset report:
  `target/opensearch-compare-stats-current/rehearsal/stats-compat-report.json`
- Route parity: `ok`
- Durability parity: `ok`
- Semantic parity: `ok`
- Fresh PIT live subset: `7` passed, `0` failed, `0` skipped. Covered
  create/open, search, keep-alive extension, routing admission, snapshot after
  update/delete, explicit REST-option rejection, and multi-sort descending
  `search_after`.
- Fresh PIT operational live subset: `11` passed, `0` failed, `0` skipped.
  Covered `_cat/pit_segments` text/JSON/selected-column views, explicit PIT
  segment lookup, PIT list/clear variants, and create/search max-keep-alive
  error parity.
- Fresh stats live subset: `12` passed, `0` failed, covering `_nodes/stats`
  and related metric/index-metric error boundaries, including search
  `open_contexts` and `point_in_time_*` fields in the compared response shape.
- Current unified report status: `ok`, with `36` reported suites, `34`
  required suites, and `27` suites compared against live OpenSearch evidence.
- Current coverage summary: `canonical_equal=1433`, `strict_equal=911`,
  `semantic_equal=23`, `failed=0`, `missing=0`,
  `known_gap_or_skipped=26`, `steelsearch_only=677`,
  `steelsearch_fail_closed=2`.
- Current fail-closed cases are now listed explicitly in the unified report:
  `knn_warmup_budget_failure` and `security_writer_ml_predict_403`.
- Audit coverage summary: `canonical_equal=82`, `strict_equal=2`, `semantic_equal=14`, `failed=0`, `missing=0`, `known_gap_or_skipped=0`, `steelsearch_only=0`
- `root-cluster-node-cat-common`: `67` passed, `0` failed, `0` skipped,
  compared against live OpenSearch.
- `root-cluster-node-cat-surface`: `2` passed, `0` failed, `0` skipped,
  retained as Steelsearch-only surface evidence.
- `tier-read-surface`: `2` passed, `0` failed, `0` skipped, compared
  against live OpenSearch.
- `admin-ops-common`: `4` passed, `0` failed, `0` skipped, compared
  against live OpenSearch.
- `admin-ops-semantic`: `11` passed, `0` failed, `0` skipped, retained
  as Steelsearch-only surface evidence.
- `runtime-mappings-surface`: `2` passed, `0` failed, `0` skipped,
  compared against live OpenSearch.
- `search-compat`: `1011` passed, `0` failed, `17` skipped.
- `search-strict`: `848` passed, `0` failed, `0` skipped.
- `search-semantic`: `73` passed, `0` failed, `0` skipped.
- `runtime-stateful-probe`: `519` passed, `0` failed, `0` skipped.
- `vector-search`: `16` passed, `0` failed, `9` skipped.
- `security-authz`: `63` passed, `0` failed, `0` skipped.
- `multi-node-write-path`: `9` passed, `0` failed, `0` skipped.
- REST API source coverage gate:
  `target/rest-api-coverage-current.json` passes with `23` live-required
  matched source routes and `0` live-required fixture failures/missing cases.
- The E2E suite does compare many functional cases against live OpenSearch, but
  the current evidence does not prove broad full compatibility yet. It proves
  the covered passing cases and tracks remaining deferred evidence explicitly.
  The remaining skipped cases are covered by narrower suites, not live
  comparison failures, and there is no current top-level unified blocker.
- Release evidence inventory is complete for the current candidate:
  `target/release-evidence-inventory-current.json` reports no missing startup
  or readiness-attachment items, and
  `target/native-closure-status-final-current.json` reports
  `final_cutover_ready=true`.

Release load comparison follow-up:

- Current fixed report:
  `target/release-load-after-refresh-target-direct/http-load-comparison.json`
- Workload: `write=20,lexical=70,refresh=10`, `clients=4`,
  `corpus_size=256`, `duration_seconds=20`.
- Root cause of the earlier slow run: refresh operations chased writes that
  arrived after the refresh request while another refresh was already in
  progress. The engine now fixes the refresh target sequence number at request
  time, matching refresh visibility semantics and avoiding unbounded catch-up
  under concurrent write load.
- Overall throughput ratio improved from the earlier release-load result
  (`0.425x`) to `2.017x` Steelsearch/OpenSearch.
- Operation ratios in the fixed run:

| Operation | Success-count ratio | Mean latency ratio | p95 latency ratio |
| --- | ---: | ---: | ---: |
| lexical | 2.017x | 0.377x | 0.418x |
| refresh | 2.129x | 0.712x | 1.012x |
| write | 1.945x | 0.185x | 0.239x |

## Main files changed

Primary code changes:

- `crates/os-engine-tantivy/src/lib.rs`
- `crates/os-query-dsl/src/lib.rs`
- `crates/os-node/src/standalone_runtime.rs`

Documentation changed:

- `docs/rust-port/search-benchmark-scenarios.md`
- `docs/rust-port/search-benchmark-handoff.md`

## Retained implementation changes

### Native/runtime path

- Standalone HTTP path routes through the native engine path.
- Simple field `sort` requests now stay on the native engine path when the sort
  list contains only user fields with `asc`/`desc` order. Complex sort options,
  `_score`, `_doc`, and other metadata sorts still fail closed to the
  compatibility path.
- Engine store uses `RwLock`; search paths take read locks.
- Existing refreshed native search snapshot is preserved across `refresh=false` writes.

### Query/search correctness and performance

- `multi_match` ranking path fixes:
  - strips boost suffixes from base fields;
  - unwraps object query text;
  - supports `best_fields`;
  - uses Tantivy `Count + TopDocs` page path.
- Vector source elision avoids returning heavy vector fields in search hits when not needed.
- Vector scoring loop was explicitly unrolled.
- Native nested ordinal/page fast path was added.

### Refresh

- No-op refresh skip is retained.
- Full refresh rebuild work is performed outside the global store write lock.
- Append-only incremental refresh fast path is retained:
  - guarded by `append_only_since_refresh`;
  - appends pending docs into existing `TantivySearchState`;
  - appends nested child documents;
  - publishes only when base refreshed seq no, schema hash, target seq no, append-only guard, and in-progress flag still match.
- `incremental_refresh_in_progress` prevents concurrent refresh requests from falling back to expensive full rebuilds while incremental refresh is active.

### Aggregations/facet

- Size-0 document-backed aggregations avoid hit materialization where possible.
- String terms aggregation has a scalar string fast path.
- Scalar date histogram path avoids generic distinct bucket allocation for scalar values.
- Scalar numeric range path avoids generic distinct bucket allocation for scalar values.
- Top-level source field lookup is prechecked once per aggregation.
- Hot bucket construction for string terms/date histogram avoids `serde_json::json!` in some document-backed paths.
- `StoredDocument` now carries top-level field caches:
  - `top_level_scalar_fields: BTreeMap<String, Value>`;
  - `top_level_string_fields: BTreeMap<String, String>`;
  - `top_level_f64_fields: BTreeMap<String, f64>`;
  - `top_level_date_millis_fields: BTreeMap<String, i64>`.
- Document-backed `terms` uses `top_level_string_fields` first for top-level string fields.
- Document-backed `range` uses `top_level_f64_fields` first for top-level numeric fields.
- Document-backed `date_histogram` uses `top_level_date_millis_fields` first for top-level date fields.
- Existing JSON source lookup remains the compatibility fallback for dotted fields, arrays, mixed values, non-scalar values, and missing typed cache entries.

## Important rejected attempts

These were benchmarked and reverted. Do not reintroduce without new evidence.

### Fused single-pass facet collector

Attempt:

- A generic single-pass collector for simple `terms`, `date_histogram`, and `range` aggregation maps.

Result:

| Run | Throughput | Facet mean | Facet p95 | Facet p99 |
| --- | ---: | ---: | ---: | ---: |
| Baseline before attempt | 111.01 ops/s | 35.99 ms | 83.03 ms | 96.57 ms |
| Fused single-pass attempt | 101.62 ops/s | 39.35 ms | 93.88 ms | 121.24 ms |

Decision:

- Reverted. Enum dispatch, inner collector loop, and losing the specialized scalar string path outweighed the benefit of one document pass.

### Date histogram normalized interval helper

Attempt:

- Normalize `date_histogram` interval once per aggregation and call a normalized helper per value.

Result:

| Run | Throughput | Facet mean | Facet p95 | Facet p99 |
| --- | ---: | ---: | ---: | ---: |
| Baseline before attempt | 111.01 ops/s | 35.99 ms | 83.03 ms | 96.57 ms |
| Normalized interval helper | 104.57 ops/s | 38.20 ms | 89.69 ms | 108.21 ms |

Decision:

- Reverted. Interval normalization was not the dominant cost.

### Refresh request target snapshot

Attempt:

- Capture `next_seq_no - 1` at refresh request start and keep that fixed target through retry/wait loops.

Result:

- Refresh-only looked healthy: 785.15 ops/s, p95 6.42 ms, p99 7.97 ms.
- Mixed matrix regressed total throughput and search metrics:
  - throughput dropped to 328.51 ops/s from the retained typed scalar cache run at 333.71 ops/s;
  - facet p50 ratio worsened from 1.03x to 1.10x;
  - facet p95 ratio worsened from 0.92x to 1.04x.

Decision:

- Reverted. It improved one refresh tail run but harmed search/mixed posture.

## Benchmark commands used

Compile check:

```bash
cargo +nightly check -p os-node --features standalone-runtime
```

Focused facet check example:

```bash
python3 tools/run-search-benchmark-matrix.py --profile minilm-knn \
  --output-dir target/search-benchmark-facet-typed-scalar-cache-5000 \
  --scenarios steelsearch-single-node \
  --corpus-size 5000 --duration-seconds 30 --clients 4 \
  --timeout-seconds 900 --query-mix facet=100
```

Final full matrix with RSS sampling:

```bash
python3 tools/run-search-benchmark-matrix.py --profile minilm-knn \
  --output-dir target/search-benchmark-matrix-minilm-knn-rss-current \
  --scenarios steelsearch-single-node,opensearch-single-node,steelsearch-three-node,opensearch-three-node \
  --corpus-size 5000 --duration-seconds 30 --clients 4 --timeout-seconds 900
```

Cleanup command used after 3-node OpenSearch runs:

```bash
docker ps --format '{{.Names}}' | rg '^steelsearch-bench-opensearch-three-node-' | xargs -r docker rm -f
```

## Current best retained benchmark artifacts

- `target/search-benchmark-matrix-minilm-knn-rss-current/summary.json`
- `target/search-benchmark-matrix-minilm-knn-final-current/summary.json`
- `target/search-benchmark-matrix-minilm-knn-typed-scalar-cache/summary.json`
- `target/search-benchmark-facet-typed-scalar-cache-5000/summary.json`

Historical/rejected-attempt artifacts:

- `target/search-benchmark-facet-single-pass-fast-path-5000/summary.json`
- `target/search-benchmark-facet-date-interval-fast-path-5000/summary.json`
- `target/search-benchmark-refresh-target-snapshot-5000/summary.json`
- `target/search-benchmark-matrix-minilm-knn-refresh-target-snapshot/summary.json`

## Recommended next work

### Option 1: close current optimization phase

Recommended if the next session needs to commit/push or cut a milestone.

Rationale:

- Search critical path is mostly solved.
- Final retained matrix is clearly faster than OpenSearch overall.
- Remaining search gap is a small facet median difference.

### Option 2: NRT refresh architecture task

Recommended if continuing performance work.

Scope:

- Introduce a refreshed immutable/versioned document/source snapshot.
- Track pending mutations since last refresh, including updates and deletes.
- Publish refreshed search state and refreshed document snapshot atomically.
- Preserve old refreshed snapshot for in-flight searches.
- Avoid rebuilding or appending against the latest mutable document map without versioning semantics.

Rationale:

- Refresh p95/p99 remains the only meaningful mixed-workload tail pain point.
- Prior local refresh tweaks were either already retained or were rejected because they hurt search metrics.

### Option 3: real doc-values/columnar facet path

Recommended only if the tiny remaining facet p50 gap matters.

Scope:

- Build a refreshed-doc ordinal/doc-values style aggregation structure for top-level scalar fields.
- Avoid adding more per-document maps unless memory overhead is measured and acceptable.

Rationale:

- The retained top-level typed cache already removed most source-access overhead.
- Further improvement should be a structural columnar aggregation path, not more generic collector fusion.

## Practical notes for the next session

- Do not trust a single mixed run for refresh p95/p99; it is variable.
- If rerunning matrix, ensure no `docker build`, BuildKit, Cargo, Rustc, or stale benchmark containers are running.
- Run scenarios serially; do not keep SteelSearch and OpenSearch running together unless intentionally testing contention.
- Clean leftover `steelsearch-bench-opensearch-three-node-*` containers after 3-node runs.
- Detailed chronological evidence is in `docs/rust-port/search-benchmark-scenarios.md`.
