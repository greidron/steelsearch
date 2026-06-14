# Search benchmark optimization handoff

Date: 2026-06-14
Workspace: `/home/ubuntu/steelsearch`

## Current status

The search benchmark optimization pass is complete for the current scope.

Final verified benchmark artifact:

- `target/search-benchmark-matrix-minilm-knn-final-current/summary.json`

Final current-state OpenSearch comparison:

| Topology | SteelSearch throughput | OpenSearch throughput | Ratio |
| --- | ---: | ---: | ---: |
| 1-node | 336.39 ops/s | 223.27 ops/s | 1.51x |
| 3-node | 336.24 ops/s | 98.01 ops/s | 3.43x |

Remaining slower-than-OpenSearch points in the final current-state run:

| Topology | Operation | Metric | SteelSearch | OpenSearch | Ratio |
| --- | --- | --- | ---: | ---: | ---: |
| 1-node | facet | p50 | 13.94 ms | 13.14 ms | 1.06x |
| 1-node | refresh | p95 | 162.22 ms | 131.56 ms | 1.23x |
| 1-node | refresh | p99 | 233.96 ms | 221.77 ms | 1.05x |
| 3-node | none | none | - | - | - |

Interpretation:

- Search critical paths are materially faster than OpenSearch in the final retained state.
- The only remaining search-path gap is a small 1-node facet median gap.
- Refresh tail remains variable in mixed workloads and should be treated as a separate NRT architecture task.
- Local 3-node results show SteelSearch faster than OpenSearch on all measured metrics, but SteelSearch 3-node throughput is close to 1-node throughput. Treat this as local OpenSearch comparison evidence, not proof of horizontal scaling.

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
  - `top_level_f64_fields: BTreeMap<String, f64>`.
- Document-backed `terms` uses `top_level_string_fields` first for top-level string fields.
- Document-backed `range` uses `top_level_f64_fields` first for top-level numeric fields.
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

Final full matrix:

```bash
python3 tools/run-search-benchmark-matrix.py --profile minilm-knn \
  --output-dir target/search-benchmark-matrix-minilm-knn-final-current \
  --scenarios steelsearch-single-node,opensearch-single-node,steelsearch-three-node,opensearch-three-node \
  --corpus-size 5000 --duration-seconds 30 --clients 4 --timeout-seconds 900
```

Cleanup command used after 3-node OpenSearch runs:

```bash
docker ps --format '{{.Names}}' | rg '^steelsearch-bench-opensearch-three-node-' | xargs -r docker rm -f
```

## Current best retained benchmark artifacts

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
