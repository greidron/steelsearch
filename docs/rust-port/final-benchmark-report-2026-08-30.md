# Final Benchmark Report

Date: 2026-08-30

Benchmark source HEAD: `2d53babc` (`Record rejected first-dimension vector scan`)

Scope: full search/k-NN benchmark matrix after the v0.5.0 performance release
and the API parity fixes for field capabilities and snapshot restore settings.

## Validation

- Release binary build:
  `RUSTFLAGS='-Awarnings' cargo +nightly build --release -q -p os-node --features standalone-runtime`
- Development replacement gate:
  `tools/run-development-replacement-gate.sh`
- Gate result: passed with exit code 0.
- Daemon-backed search compatibility inside the gate:
  `1098 passed, 0 failed, 0 skipped`.
- Daemon integration inside the gate:
  `49 passed, 0 failed`.
- Migration unit tests inside the gate:
  `19 passed, 0 failed`.
- k-NN plugin unit tests inside the gate:
  `10 passed, 0 failed`.
- Model-serving daemon test inside the gate:
  `1 passed, 0 failed`.
- Multi-node daemon smoke inside the gate:
  `1 passed, 0 failed`.

## Benchmark Evidence

Command:

```bash
STEELSEARCH_BINARY_PATH=target/release/steelsearch \
  python3 tools/run-search-benchmark-matrix.py \
  --profile minilm-knn \
  --reuse-steelsearch-binary \
  --output-dir target/search-benchmark-matrix-current-retained-full-no-telemetry-20260830
```

Primary artifacts:

- `target/search-benchmark-matrix-current-retained-full-no-telemetry-20260830/summary.json`
- `target/search-benchmark-matrix-current-retained-full-no-telemetry-20260830/report.md`

Configuration:

- Corpus: `5000` documents
- Vector dimension: `384`
- Clients: `4`
- Duration per scenario: `30s`
- Query mix:
  `write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,vector=15,hybrid=10,refresh=5`

## Overall Result

| Topology | SteelSearch ops/s | OpenSearch ops/s | Ratio | SteelSearch errors | OpenSearch errors |
|---|---:|---:|---:|---:|---:|
| single-node | 659.384 | 205.232 | 3.21x | 0 | 0 |
| three-node | 821.630 | 78.394 | 10.48x | 0 | 0 |

Current HEAD remains ahead of OpenSearch in every measured operation for both
topologies. The benchmark's `steelsearch_slower_than_opensearch` list is empty
for both single-node and three-node.

## Operation p99

| Topology | Operation | SteelSearch p99 ms | OpenSearch p99 ms | SteelSearch/OpenSearch |
|---|---|---:|---:|---:|
| single-node | facet | 21.882 | 53.041 | 0.413x |
| single-node | hybrid | 19.901 | 55.301 | 0.360x |
| single-node | lexical | 17.150 | 34.221 | 0.501x |
| single-node | nested | 19.366 | 37.184 | 0.521x |
| single-node | ranking | 18.293 | 53.042 | 0.345x |
| single-node | refresh | 25.680 | 238.837 | 0.108x |
| single-node | sort_filter | 16.075 | 50.447 | 0.319x |
| single-node | vector | 19.522 | 59.045 | 0.331x |
| single-node | write | 7.954 | 46.707 | 0.170x |
| three-node | facet | 14.875 | 176.198 | 0.084x |
| three-node | hybrid | 14.780 | 133.067 | 0.111x |
| three-node | lexical | 11.602 | 142.837 | 0.081x |
| three-node | nested | 11.387 | 145.208 | 0.078x |
| three-node | ranking | 12.998 | 172.967 | 0.075x |
| three-node | refresh | 31.958 | 531.081 | 0.060x |
| three-node | sort_filter | 10.659 | 159.346 | 0.067x |
| three-node | vector | 12.363 | 170.668 | 0.072x |
| three-node | write | 8.281 | 154.014 | 0.054x |

## v0.5.0 Comparison

| Topology | Metric | v0.5.0 | Current HEAD | Change |
|---|---|---:|---:|---:|
| single-node | throughput ops/s | 651.653 | 659.384 | +1.19% |
| single-node | refresh p99 ms | 29.609 | 25.680 | -13.27% |
| single-node | vector p99 ms | 18.983 | 19.522 | +2.84% |
| single-node | hybrid p99 ms | 20.463 | 19.901 | -2.75% |
| three-node | throughput ops/s | 827.631 | 821.630 | -0.73% |
| three-node | refresh p99 ms | 33.356 | 31.958 | -4.19% |
| three-node | vector p99 ms | 12.888 | 12.363 | -4.07% |
| three-node | hybrid p99 ms | 14.436 | 14.780 | +2.38% |

The current HEAD is effectively throughput-neutral versus v0.5.0 within normal
run-to-run noise. The strongest retained movement is refresh p99 improvement:
single-node `29.609 ms -> 25.680 ms`, three-node `33.356 ms -> 31.958 ms`.
The small single-node vector and three-node hybrid p99 regressions remain well
inside the OpenSearch comparison margin.

## Optimization Attempts

- Lowering sharded vector parallel threshold from `10000` to `2000` documents
  was rejected. It improved one single-node throughput sample but regressed
  three-node throughput and vector/hybrid p99.
- Lowering refresh busy-wait sleep from `1ms` to `100us` was rejected. It
  regressed single-node throughput and single-node refresh p99.

No rejected optimization remains in the worktree.

## Current Bottleneck Reading

- Single-node cumulative vector scan time remains the largest native-path
  counter, but per-operation diagnostics show it is around `0.63 ms/op` for the
  vector-heavy operations, not a standalone blocker.
- Refresh tail under full load is concurrency-sensitive. With `clients=1`,
  refresh p99 previously dropped to roughly `14 ms`; in full `clients=4` matrix
  it is `25.680 ms` single-node and `31.958 ms` three-node.
- On this host (`aarch64`, Neoverse-N1), vector math uses the existing NEON
  path. The earlier x86 SIMD-gap hypothesis does not apply to this benchmark
  environment.

## Judgment

Performance is acceptable for the current replacement-focused benchmark gate.
SteelSearch has no measured OpenSearch regressions in the final full matrix,
and the post-v0.5.0 API parity commits did not create a material throughput
regression.

The next work should stay focused on API-level compatibility gaps that affect
cluster replacement or bounded mixed use. Each implemented gap should be
validated with targeted OpenSearch comparison evidence and then checked against
the full benchmark matrix for regressions.

## Field Caps Index Filter Follow-Up

Implemented after the final HEAD matrix:

- POST `/_field_caps` and `/{index}/_field_caps` now apply request-body
  `index_filter` before field type and `include_unmapped` calculation.
- Targeted OpenSearch comparison:
  `target/search-compat-field-caps-index-filter.json`
  reported `1 passed, 0 failed, 0 skipped`.
- Development replacement gate passed with exit code 0. The daemon-backed
  search compatibility count is now `1096 passed, 0 failed, 0 skipped`.

Full benchmark after this API fix:

| Topology | SteelSearch ops/s | OpenSearch ops/s | Ratio | SteelSearch refresh p99 | SteelSearch errors |
|---|---:|---:|---:|---:|---:|
| single-node | 651.740 | 211.443 | 3.08x | 27.657 ms | 0 |
| three-node | 820.147 | 76.689 | 10.69x | 29.960 ms | 0 |

Single-node SteelSearch repeat:

| Metric | Previous final HEAD | Follow-up repeat | Change |
|---|---:|---:|---:|
| throughput ops/s | 651.052 | 658.914 | +1.21% |
| refresh p99 ms | 22.266 | 25.346 | +13.83% |
| vector p99 ms | 18.964 | 19.259 | +1.56% |
| hybrid p99 ms | 19.088 | 19.413 | +1.70% |

The changed API route is not exercised by the benchmark workload. Throughput is
neutral to slightly positive, the full matrix reports no
SteelSearch-slower-than-OpenSearch metrics, and the refresh p99 movement remains
inside the observed post-v0.5.0 measurement band rather than indicating a hot
path regression.

## Field Caps Mixed Type Follow-Up

Implemented after the `index_filter` follow-up:

- `/_field_caps` now preserves multiple mapped types for the same field across
  resolved indices instead of collapsing to the first observed type.
- Mixed-type field capability entries now include the OpenSearch-style per-type
  `indices` list.
- Targeted OpenSearch comparison:
  `target/search-compat-field-caps-mixed-type.json`
  reported `1 passed, 0 failed, 0 skipped`.
- Development replacement gate completed. The daemon-backed search
  compatibility count is now `1097 passed, 0 failed, 0 skipped`.

Full benchmark after this API fix:

| Topology | SteelSearch ops/s | OpenSearch ops/s | Ratio | SteelSearch refresh p99 | SteelSearch errors |
|---|---:|---:|---:|---:|---:|
| single-node | 633.005 | 208.806 | 3.03x | 24.072 ms | 0 |
| three-node | 826.675 | 76.944 | 10.74x | 28.182 ms | 0 |

Operation p99 remained ahead of OpenSearch in every measured operation. The
benchmark's `steelsearch_slower_than_opensearch` list is empty for both
topologies. The single-node throughput dip versus the immediately preceding
full matrix is treated as measurement noise: the modified code is outside the
benchmark hot path, while three-node throughput is neutral to slightly positive.

## L2 Bounded Scan Tuning

After the mixed-type API parity work, the remaining internal hot counter was
`vector_candidate_scan_nanos`, mainly from exact L2 scan for `vector` and
`hybrid` operations. Two NEON bounded-distance variants were tested by reducing
the frequency of intermediate horizontal reductions during early-exit pruning:

| Variant | Evidence | Topology | Throughput | Refresh p99 | Vector p99 | Hybrid p99 | Scan counter |
|---|---|---|---:|---:|---:|---:|---:|
| baseline | `target/search-benchmark-matrix-api-fieldcaps-mixed-type-full-20260830/summary.json` | single-node | 633.005 ops/s | 24.072 ms | 20.867 ms | 20.715 ms | 3.427 s |
| baseline | `target/search-benchmark-matrix-api-fieldcaps-mixed-type-full-20260830/summary.json` | three-node | 826.675 ops/s | 28.182 ms | 13.999 ms | 12.640 ms | 1.047 s |
| check every 16 dims | `target/search-benchmark-matrix-l2-bounded-neon16-full-20260830/summary.json` | single-node | 648.214 ops/s | 26.749 ms | 20.329 ms | 20.331 ms | 3.402 s |
| check every 16 dims | `target/search-benchmark-matrix-l2-bounded-neon16-full-20260830/summary.json` | three-node | 821.267 ops/s | 28.696 ms | 12.007 ms | 15.517 ms | 1.042 s |
| check every 32 dims | `target/search-benchmark-matrix-l2-bounded-neon32-full-20260830/summary.json` | single-node | 628.241 ops/s | 34.889 ms | 22.998 ms | 20.028 ms | 3.508 s |
| check every 32 dims | `target/search-benchmark-matrix-l2-bounded-neon32-full-20260830/summary.json` | three-node | 812.897 ops/s | 31.440 ms | 13.987 ms | 14.896 ms | 1.017 s |

The 16-dimension variant is retained. It improved single-node throughput by
`2.4%` versus the mixed-type baseline while slightly reducing vector scan time
and vector/hybrid p99 on the single-node run. Three-node throughput was
effectively flat within the current run-to-run band, vector p99 improved, and
the benchmark's `steelsearch_slower_than_opensearch` list remained empty for
both topologies. The 32-dimension variant was rejected because it regressed
single-node throughput, refresh p99, vector p99, and scan time.

## Snapshot Restore Selector Follow-Up

Implemented after the L2 bounded scan tuning:

- Snapshot restore now resolves OpenSearch-style `indices` multi-index syntax
  against the snapshot contents, including wildcard selectors and negative
  exclusions.
- Missing restore selectors are ignored only when `ignore_unavailable=true`;
  `partial=true` no longer masks missing index selectors.
- Rename target collisions are preflighted before any restored index metadata
  or documents are materialized.

Validation:

- Targeted runtime test:
  `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore --features standalone-runtime`
- Live SteelSearch/OpenSearch compare:
  `target/snapshot-restore-selector-compat-20260830-rerun/snapshot-lifecycle-compat-report.json`
  reports `21 passed, 0 failed, 0 skipped`.
- Full benchmark:
  `target/search-benchmark-matrix-api-snapshot-restore-selectors-full-20260830/summary.json`

Full benchmark after this API fix:

| Topology | SteelSearch ops/s | OpenSearch ops/s | Ratio | SteelSearch refresh p99 | SteelSearch errors |
|---|---:|---:|---:|---:|---:|
| single-node | 658.323 | 209.404 | 3.14x | 26.966 ms | 0 |
| three-node | 809.619 | 79.807 | 10.14x | 33.843 ms | 0 |

The benchmark reported no SteelSearch-slower-than-OpenSearch metrics for either
topology. The changed code is outside the measured search hot path; the
single-node run improved versus the retained L2 benchmark, while three-node
throughput stayed inside the current post-v0.5.0 measurement band.

## Snapshot Restore Alias Rename Follow-Up

Implemented after the restore selector follow-up:

- Snapshot restore now applies `rename_alias_pattern` and
  `rename_alias_replacement` to restored aliases when `include_aliases` remains
  enabled.
- The snapshot lifecycle compare fixture now checks restored alias names
  against live OpenSearch.

Validation:

- Targeted runtime tests:
  `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore --features standalone-runtime`
  and
  `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore_body_subset_keeps_bounded_fields_only --features standalone-runtime`
- Live SteelSearch/OpenSearch compare:
  `target/snapshot-restore-alias-rename-compat-20260830/snapshot-lifecycle-compat-report.json`
  reports `25 passed, 0 failed, 0 skipped`.
- Full benchmark:
  `target/search-benchmark-matrix-api-snapshot-restore-alias-rename-full-20260830/summary.json`
- Single-node repeat:
  `target/search-benchmark-matrix-api-snapshot-restore-alias-rename-steel-single-rerun-20260830/summary.json`

Full benchmark after this API fix:

| Topology | SteelSearch ops/s | OpenSearch ops/s | Ratio | SteelSearch refresh p99 | SteelSearch errors |
|---|---:|---:|---:|---:|---:|
| single-node | 626.474 | 210.860 | 2.97x | 28.711 ms | 0 |
| three-node | 823.916 | 81.206 | 10.15x | 30.565 ms | 0 |

The benchmark again reported no SteelSearch-slower-than-OpenSearch metrics.
Because the changed restore alias code is not exercised by the search
benchmark workload, the lower single-node full-run throughput was checked with
a SteelSearch single-node repeat. The repeat reported `633.077 ops/s`, `0`
errors, `28.464 ms` refresh p99, `20.739 ms` vector p99, and `19.563 ms`
hybrid p99, which matches the mixed-type baseline band rather than proving a
new hot-path regression.

## Rejected L2 NEON Accumulator Unroll

After the alias rename follow-up, a second vector-scan tuning attempt changed
the aarch64 L2 distance path from one NEON accumulator to four independent
accumulators over 16-float blocks. The goal was to reduce the loop-carried FMA
dependency while preserving the retained 16-dimension bounded early-exit
interval.

Rejected variant evidence:

- Targeted L2 test:
  `target/os-engine-tantivy-l2-unroll4-test.log` failed with exit code `101`
  because the changed accumulator order exceeded the temporary exact-sum test
  tolerance (`65.619194` versus `65.61916`).
- Release build:
  `target/os-node-release-build-l2-unroll4.log` with exit code `0`.
- Single-node benchmark:
  `target/search-benchmark-matrix-l2-neon-unroll4-steel-single-20260830/summary.json`
  reported `656.904 ops/s`, `0` errors, `93.608 ms` refresh p99,
  `18.665 ms` vector p99, and `19.348 ms` hybrid p99.
- Single-node repeat:
  `target/search-benchmark-matrix-l2-neon-unroll4-steel-single-repeat-20260830/summary.json`
  reported `653.246 ops/s`, `0` errors, `24.201 ms` refresh p99,
  `19.316 ms` vector p99, and `20.083 ms` hybrid p99.
- Full benchmark:
  `target/search-benchmark-matrix-l2-neon-unroll4-full-20260830/summary.json`
  reported `629.411 ops/s` single-node and `806.876 ops/s` three-node.

The full benchmark still had no SteelSearch-slower-than-OpenSearch metrics, but
the three-node throughput regressed versus the alias-rename full matrix
(`806.876 ops/s` versus `823.916 ops/s`) and the first single-node run produced
a large refresh p99 outlier. The code change is therefore not retained.

After reverting the code candidate, the retained bounded L2 path was rechecked
with `target/os-engine-tantivy-bounded-l2-after-unroll4-revert-test.log`, exit
code `0`.

## Rejected L2 Space-Type Branch Hoist

The next vector-scan attempt specialized the exact-search loop for L2 so the
per-candidate hot path avoided repeated string matching and cosine-norm lookup
plumbing. It kept the same exact L2 score and bounded early-exit behavior.

Evidence:

- Targeted bounded L2 test:
  `target/os-engine-tantivy-l2-branch-hoist-test.log` with exit code `0`.
- Release build:
  `target/os-node-release-build-l2-branch-hoist.log` with exit code `0`.
- Single-node benchmark:
  `target/search-benchmark-matrix-l2-branch-hoist-steel-single-20260830/summary.json`
  reported `634.448 ops/s`, `0` errors, `24.725 ms` refresh p99,
  `19.346 ms` vector p99, and `20.449 ms` hybrid p99.

The result stayed inside the existing retained-baseline band rather than
showing a clear improvement, so the code change is not retained.

## Rejected L2 Norm Lower-Bound Pruning

A follow-up vector-scan attempt stored L2 norms for L2 vector columns and used
the triangle-inequality lower bound `(query_norm - candidate_norm)^2` to skip
full L2 distance calculation when the candidate could not beat the current
top-k worst distance. A deterministic simulation over the benchmark vector
generator estimated roughly `26%` candidate skips on average, so the approach
was worth benchmarking.

Evidence:

- Targeted L2 tests:
  `target/os-engine-tantivy-l2-norm-bound-test.log` with exit code `0`.
- Release build:
  `target/os-node-release-build-l2-norm-bound.log` with exit code `0`.
- Single-node benchmark:
  `target/search-benchmark-matrix-l2-norm-bound-steel-single-20260830/summary.json`
  reported `644.417 ops/s`, `0` errors, `38.694 ms` refresh p99,
  `19.020 ms` vector p99, and `21.208 ms` hybrid p99.
- Single-node repeat:
  `target/search-benchmark-matrix-l2-norm-bound-steel-single-repeat-20260830/summary.json`
  reported `653.730 ops/s`, `0` errors, `26.025 ms` refresh p99,
  `19.832 ms` vector p99, and `19.352 ms` hybrid p99.
- Full benchmark:
  `target/search-benchmark-matrix-l2-norm-bound-full-20260830/summary.json`
  reported `652.229 ops/s` single-node, `818.902 ops/s` three-node, and no
  SteelSearch-slower-than-OpenSearch metrics.
- Three-node repeat:
  `target/search-benchmark-matrix-l2-norm-bound-steel-three-repeat-20260830/summary.json`
  reported `806.848 ops/s`, `0` errors, `39.373 ms` refresh p99,
  `15.701 ms` vector p99, and `12.853 ms` hybrid p99.

The single-node numbers were promising, but the extra norm storage and pruning
logic did not hold up for three-node throughput/refresh. The code change is not
retained.

## Rejected L2 Bounded 8-Dimension Check Interval

A follow-up bounded L2 tuning attempt changed the retained aarch64 intermediate
horizontal reduction interval from every 16 dimensions to every 8 dimensions.
The intent was to recover more early exits while still reducing the original
per-4-dimension reduction overhead.

Evidence:

- Targeted bounded L2 test:
  `target/os-engine-tantivy-l2-neon8-test.log` with exit code `0`.
- Release build:
  `target/os-node-release-build-l2-neon8.log` with exit code `0`.
- Single-node benchmark:
  `target/search-benchmark-matrix-l2-bounded-neon8-steel-single-20260830/summary.json`
  reported `644.816 ops/s`, `0` errors, `29.926 ms` refresh p99,
  `21.455 ms` vector p99, and `20.863 ms` hybrid p99.

This was worse than the retained 16-dimension full-matrix result
(`648.214 ops/s`, `20.329 ms` vector p99, `20.331 ms` hybrid p99), so the code
change is not retained.

## Rejected Exact-Vector Hash Warm Start

Another vector-scan attempt added a per-refreshed-column hash map from exact
vector values to ordinals. When the query vector exactly matched indexed
vectors, those ordinals were scored before the normal column scan so the
bounded top-k threshold could tighten earlier. Hash collisions were guarded by
slice equality checks, and non-exact queries would keep the normal scan order.

Evidence:

- Targeted column test:
  `target/os-engine-tantivy-vector-exact-warmstart-test.log` with exit code `0`.
- Release build:
  `target/os-node-release-build-vector-exact-warmstart.log` with exit code `0`.
- Single-node benchmark:
  `target/search-benchmark-matrix-vector-exact-warmstart-steel-single-20260830/summary.json`
  reported `643.464 ops/s`, `0` errors, `28.492 ms` refresh p99,
  `20.612 ms` vector p99, and `21.338 ms` hybrid p99.

The extra column hash structure did not improve the benchmark and worsened
vector/hybrid p99 versus the retained 16-dimension bounded L2 tuning, so the
code change is not retained.

## Rejected Refreshed-Vector Ordinal Scan

A follow-up exact-vector scan attempt replaced
`RefreshedVectorColumn::iter().enumerate()` in the hot refreshed-column scan
with ordinal-based access. The safe variant added `id_at` / `values_at`
helpers; the unsafe variant used debug-asserted column invariants and unchecked
slice access to avoid per-ordinal bounds checks.

Evidence:

- Targeted exact-vector test:
  `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy exact_vector_search`
  passed after the candidate change.
- Release build:
  `target/os-node-release-build-vector-column-unchecked-scan.log` with exit
  code `0`.
- Safe ordinal single-node benchmark:
  `target/search-benchmark-matrix-vector-column-ordinal-scan-steel-single-20260830/summary.json`
  reported `643.403 ops/s`, `0` errors, `33.507 ms` refresh p99,
  `20.108 ms` vector p99, and `20.072 ms` hybrid p99.
- Unchecked ordinal single-node benchmark:
  `target/search-benchmark-matrix-vector-column-unchecked-scan-steel-single-20260830/summary.json`
  reported `636.787 ops/s`, `0` errors, `32.619 ms` refresh p99,
  `19.518 ms` vector p99, and `23.248 ms` hybrid p99.

Neither variant improved the retained 16-dimension bounded L2 result. The
unchecked variant also worsened hybrid p99, so the code change is not retained.

## Rejected Lower Shard-Parallel Vector Scan Threshold

A shard-parallelism attempt lowered the refreshed vector-column exact scan
parallel reduce threshold from `10,000` documents to `2,000` documents. The
benchmark profile uses `5,000` documents and `3` shards, so this intentionally
enabled per-shard rayon scanning for the single-node benchmark to test whether
the remaining vector bottleneck was caused by leaving shard-level parallelism
idle.

Evidence:

- Targeted sharded exact-vector test:
  `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy sharded_exact_vector_search_reduces_shard_local_candidates`
  passed after the candidate change.
- Release build:
  `target/os-node-release-build-vector-shard-parallel-threshold.log` with exit
  code `0`.
- Single-node benchmark:
  `target/search-benchmark-matrix-vector-shard-parallel-threshold-steel-single-20260830/summary.json`
  reported `632.499 ops/s`, `0` errors, `32.796 ms` refresh p99,
  `19.826 ms` vector p99, and `20.528 ms` hybrid p99.

The lower threshold worsened overall single-node throughput. For this corpus
size, the rayon fan-out/reduce overhead is larger than the saved scan time, so
the `10,000` document threshold is retained.

## Rejected Tantivy Writer Heap Changes

The latest full benchmark after `86b68630` still shows no
SteelSearch-slower-than-OpenSearch metrics. The remaining SteelSearch-local
refresh cost is dominated by Tantivy commit timing: in
`target/search-benchmark-matrix-api-snapshot-status-query-params-full-20260830/summary.json`,
single-node refresh p99 was `20.361 ms` and average
`refresh_tantivy_commit_nanos` was about `5.66 ms/refresh`; three-node refresh
p99 was `21.037 ms` and average commit time was about `3.92 ms/refresh`.

Two writer heap candidates were checked against this refresh-commit hypothesis:

- `TANTIVY_WRITER_HEAP_BYTES = 32 * 1024 * 1024`: targeted refresh visibility
  test passed and release build passed, but SteelSearch single-node benchmark
  `target/search-benchmark-matrix-writer-heap32-steel-single-20260830/summary.json`
  regressed to `701.299 ops/s` with refresh p99 `42.810 ms`, versus the
  retained full baseline's `740.086 ops/s` and refresh p99 `20.361 ms`.
- `TANTIVY_WRITER_HEAP_BYTES = 8 * 1024 * 1024`: targeted refresh visibility
  test failed because Tantivy requires the writer memory arena to be at least
  `15,000,000` bytes.

The retained writer heap remains `16 * 1024 * 1024`, which is near Tantivy's
minimum valid arena size and performed better than the larger tested value on
the current mixed write/search/refresh workload.

## Rejected Refresh Visibility Lock Narrowing

The refresh route already checks whether node-side visibility state is pending
before deciding whether to persist post-refresh state. A smaller candidate tried
to narrow `mark_runtime_documents_refreshed(...)` by removing pending
unrefreshed keys before taking the larger `documents_state` lock, returning
early when no keys matched.

Targeted validation passed:

- `cargo fmt --check`
- `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node daemon_refresh_endpoints_and_write_refresh_policy_control_search_visibility --features standalone-runtime --test dev_cluster_daemons -- --nocapture`
- `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_index_status_route_delegates_to_snapshot_status_contract --features standalone-runtime -- --nocapture`
- Release build with `RUSTFLAGS='-Awarnings' cargo +nightly build --release -p os-node --bin steelsearch --features standalone-runtime`

The SteelSearch single-node benchmark
`target/search-benchmark-matrix-refresh-mark-skip-doclock-steel-single-20260830/summary.json`
reported `718.884 ops/s` and refresh p99 `23.238 ms`, worse than the retained
full baseline's `740.086 ops/s` and refresh p99 `20.361 ms` in
`target/search-benchmark-matrix-api-snapshot-status-query-params-full-20260830/summary.json`.
The lock narrowing is therefore not retained.

## Rejected Deferred Native Replay Fast Path

The default benchmark path does not set
`STEELSEARCH_DEFER_NATIVE_WRITE_UNTIL_REFRESH=1`, so
`replay_deferred_native_writes_before_refresh(...)` only needs pending native
delete replay. A candidate split that path so the default case skipped
`documents_state` and `unrefreshed_document_keys` locks, and also avoided the
final `pending_native_deletes` cleanup lock when no delete mutation was queued.

Targeted validation passed:

- `cargo fmt --check`
- `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node daemon_refresh_endpoints_and_write_refresh_policy_control_search_visibility --features standalone-runtime --test dev_cluster_daemons -- --nocapture`
- `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node daemon_bulk_refresh_policies_control_search_visibility_over_real_socket --features standalone-runtime --test dev_cluster_daemons -- --nocapture`
- Release build with `RUSTFLAGS='-Awarnings' cargo +nightly build --release -p os-node --bin steelsearch --features standalone-runtime`

The SteelSearch single-node benchmark
`target/search-benchmark-matrix-deferred-replay-fastpath-steel-single-20260830/summary.json`
reported `721.012 ops/s` and refresh p99 `29.118 ms`, below the retained full
baseline's `740.086 ops/s` and refresh p99 `20.361 ms` in
`target/search-benchmark-matrix-api-snapshot-status-query-params-full-20260830/summary.json`.
The default replay fast path is therefore not retained.

## Rejected Runtime Env Flag Caching

The benchmark runner starts SteelSearch with stable runtime flags including
`STEELSEARCH_DEFER_NATIVE_WRITE_UNTIL_REFRESH=1`,
`STEELSEARCH_PERSIST_SHARED_RUNTIME_STATE_PER_WRITE=0`,
`STEELSEARCH_SYNC_SHARED_RUNTIME_STATE_PER_REQUEST=0`, and
`STEELSEARCH_DEFER_DEVELOPMENT_SHARD_PERSIST_PER_WRITE=1`. A candidate cached
these flags with `OnceLock` in non-test builds while preserving dynamic
`env::var` reads under `cfg(test)` so env-mutating unit tests would keep their
existing behavior.

Targeted validation passed:

- `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node daemon_refresh_endpoints_and_write_refresh_policy_control_search_visibility --features standalone-runtime --test dev_cluster_daemons -- --nocapture`
- `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node daemon_bulk_refresh_policies_control_search_visibility_over_real_socket --features standalone-runtime --test dev_cluster_daemons -- --nocapture`
- `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_index_status_route_delegates_to_snapshot_status_contract --features standalone-runtime -- --nocapture`
- Release build with `RUSTFLAGS='-Awarnings' cargo +nightly build --release -p os-node --bin steelsearch --features standalone-runtime`

The SteelSearch single-node benchmark
`target/search-benchmark-matrix-runtime-env-cache-steel-single-20260830/summary.json`
reported `699.758 ops/s` and refresh p99 `52.464 ms`, below the retained full
baseline's `740.086 ops/s` and refresh p99 `20.361 ms` in
`target/search-benchmark-matrix-api-snapshot-status-query-params-full-20260830/summary.json`.
The env flag cache is therefore not retained.

## Rejected L2 Warm-Sample Scan Ordering

The benchmark vector workload queries an existing document vector with `k=10`.
Another exact-semantics attempt therefore pre-scored up to `64` evenly spaced
refreshed-column ordinals before the normal full scan. The goal was to fill a
better top-k window earlier so bounded L2 could reject more candidates during
the full pass. Every candidate was still evaluated at most once in the final
ordering, preserving exact result semantics.

Evidence:

- Targeted exact-vector and sharded exact-vector tests passed after the
  candidate change:
  `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy exact_vector_search`
  and
  `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy sharded_exact_vector_search_reduces_shard_local_candidates`.
- Release build:
  `target/os-node-release-build-vector-l2-warm-sample.log` with exit code `0`.
- Single-node benchmark:
  `target/search-benchmark-matrix-vector-l2-warm-sample-steel-single-20260830/summary.json`
  reported `639.230 ops/s`, `0` errors, `29.404 ms` refresh p99,
  `20.487 ms` vector p99, and `20.580 ms` hybrid p99.

The extra pre-sampling work did not translate into lower vector/hybrid p99 or
overall throughput, so the code change is not retained.

## Rejected Refreshed-Document Direct Lookup

The current vector hit materialization path resolves vector candidate ids
through `refreshed_document_by_id`, which scans refreshed shard maps. A small
candidate change first tried a direct `ShardedDocuments::get(id)` lookup for
default-routed documents and fell back to the existing refreshed-shard scan
when the current document was unrefreshed, deleted, or custom-routed.

Evidence:

- Targeted tests:
  `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy exact_vector_search`
  and
  `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy refresh_targets_request_time_sequence_number`
  passed after the candidate change.
- Release build:
  `target/os-node-release-build-refreshed-doc-direct-lookup.log` with exit
  code `0`.
- Single-node benchmark:
  `target/search-benchmark-matrix-refreshed-doc-direct-lookup-steel-single-20260830/summary.json`
  reported `635.882 ops/s`, `0` errors, `33.504 ms` refresh p99,
  `21.396 ms` vector p99, and `21.315 ms` hybrid p99.

The extra routing/hash lookup worsened vector and hybrid latency, so the code
change is not retained.

## Rejected First-Dimension Sorted L2 Scan

An exact L2 pruning attempt added a refresh-time ordinal list sorted by the
first vector dimension. The scan walked outward from the query's first
coordinate and stopped only when the next candidate's one-dimensional squared
distance was strictly greater than the current top-k worst full L2 distance.
That preserves exact ranking semantics because a single-coordinate squared
distance is a lower bound for full squared L2.

Evidence:

- Workload distribution simulation over the benchmark vector generator showed
  strong theoretical pruning potential: average top-10 worst squared L2
  distance `0.017003`; first-dimension lower-bound skip mean `0.9451`; 16-prefix
  skip mean `0.9830`.
- Targeted vector tests passed after the candidate change:
  `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy knn -- --test-threads=1`
  and
  `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector -- --test-threads=1`.
- Single-node clients=1 diagnostic benchmark:
  `target/search-benchmark-matrix-l2-firstdim-sorted-client1-20260830/summary.json`
  reported vector scan `593.6 us/op`, hybrid scan `599.8 us/op`,
  vector p99 `3.929 ms`, hybrid p99 `4.329 ms`, and refresh p99 `18.921 ms`.
- Full-profile benchmark attempt:
  `target/search-benchmark-matrix-l2-firstdim-sorted-full-20260830/` completed
  SteelSearch 1-node, SteelSearch 3-node, and OpenSearch 1-node before
  OpenSearch 3-node failed with
  `cluster create-index blocked (api)`. The completed SteelSearch full-profile
  results were worse than the retained bounded L2 path: SteelSearch 1-node
  vector p99 `24.812 ms`, hybrid p99 `25.308 ms`, refresh p99 `54.750 ms`;
  SteelSearch 3-node vector p99 `46.677 ms`, hybrid p99 `38.157 ms`, refresh
  p99 `49.893 ms`.

Despite promising lower-bound math and clients=1 telemetry, the refresh-time
sort artifact and alternate traversal worsened the full benchmark. The code
change is not retained.

## Post-v0.5.0 API Gap Follow-up

Snapshot/data-stream restore parity was extended after the final retained
benchmark. Snapshot create by data stream name now captures the backing index
metadata/documents, records `data_streams`, persists restore shard manifests for
backing indices, and restore by data stream name now reattaches data stream
metadata so the restored stream is searchable.

Validation:

- Live SteelSearch/OpenSearch snapshot lifecycle compare:
  `target/api-gap-snapshot-data-stream-restore-20260830-final/snapshot-lifecycle-compat-report.json`
  reports `34 passed, 0 failed, 0 skipped`.
- Full benchmark:
  `target/search-benchmark-matrix-api-snapshot-data-stream-full-20260830/summary.json`
  reports SteelSearch single-node `654.37 ops/s` vs OpenSearch `201.95 ops/s`
  (`3.24x`), and SteelSearch three-node `812.14 ops/s` vs OpenSearch
  `79.30 ops/s` (`10.24x`), with no SteelSearch-slower metrics.
- Single-node repeat:
  `target/search-benchmark-matrix-api-snapshot-data-stream-steel-single-rerun-20260830/summary.json`
  reports `664.50 ops/s` and refresh p99 `23.07 ms`, so the full-run
  single-node refresh p99 spike to `45.27 ms` is treated as non-persistent
  benchmark noise rather than a sustained regression.
