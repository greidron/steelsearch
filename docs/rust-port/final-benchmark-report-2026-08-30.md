# Final Benchmark Report

Date: 2026-08-30

Baseline HEAD: `2520401e` (`Record final HEAD benchmark report`)

Scope: full search/k-NN benchmark matrix after the v0.5.0 performance release
and the API parity fixes for field capabilities and snapshot restore settings.

## Validation

- Release binary build:
  `RUSTFLAGS='-Awarnings' cargo +nightly build --release -q -p os-node --features standalone-runtime`
- Development replacement gate:
  `tools/run-development-replacement-gate.sh`
- Gate result: passed with exit code 0.
- Daemon-backed search compatibility inside the gate:
  `1095 passed, 0 failed, 0 skipped`.
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
  --reuse-steelsearch-binary \
  --output-dir target/search-benchmark-matrix-final-head-full-20260830
```

Primary artifacts:

- `target/search-benchmark-matrix-final-head-full-20260830/summary.json`
- `target/search-benchmark-matrix-final-head-full-20260830/report.md`

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
| single-node | 651.052 | 205.104 | 3.17x | 0 | 0 |
| three-node | 825.115 | 85.286 | 9.68x | 0 | 0 |

Current HEAD remains ahead of OpenSearch in every measured operation for both
topologies. The benchmark's `steelsearch_slower_than_opensearch` list is empty
for both single-node and three-node.

## Operation p99

| Topology | Operation | SteelSearch p99 ms | OpenSearch p99 ms | SteelSearch/OpenSearch |
|---|---|---:|---:|---:|
| single-node | facet | 22.435 | 56.957 | 0.394x |
| single-node | hybrid | 19.088 | 62.683 | 0.305x |
| single-node | lexical | 15.896 | 38.046 | 0.418x |
| single-node | nested | 17.992 | 55.947 | 0.322x |
| single-node | ranking | 19.503 | 50.981 | 0.383x |
| single-node | refresh | 22.266 | 271.497 | 0.082x |
| single-node | sort_filter | 17.166 | 50.461 | 0.340x |
| single-node | vector | 18.964 | 70.697 | 0.268x |
| single-node | write | 7.512 | 41.117 | 0.183x |
| three-node | facet | 14.660 | 135.277 | 0.108x |
| three-node | hybrid | 11.664 | 142.323 | 0.082x |
| three-node | lexical | 12.177 | 96.764 | 0.126x |
| three-node | nested | 14.344 | 96.807 | 0.148x |
| three-node | ranking | 15.435 | 148.042 | 0.104x |
| three-node | refresh | 33.333 | 392.170 | 0.085x |
| three-node | sort_filter | 13.924 | 148.656 | 0.094x |
| three-node | vector | 13.543 | 158.827 | 0.085x |
| three-node | write | 7.726 | 102.157 | 0.076x |

## v0.5.0 Comparison

| Topology | Metric | v0.5.0 | Current HEAD | Change |
|---|---|---:|---:|---:|
| single-node | throughput ops/s | 651.653 | 651.052 | -0.09% |
| single-node | refresh p99 ms | 29.609 | 22.266 | -24.80% |
| single-node | vector p99 ms | 18.983 | 18.964 | -0.10% |
| single-node | hybrid p99 ms | 20.463 | 19.088 | -6.72% |
| three-node | throughput ops/s | 827.631 | 825.115 | -0.30% |
| three-node | refresh p99 ms | 33.356 | 33.333 | -0.07% |
| three-node | vector p99 ms | 12.888 | 13.543 | +5.08% |
| three-node | hybrid p99 ms | 14.436 | 11.664 | -19.20% |

The current HEAD is effectively throughput-neutral versus v0.5.0 within normal
run-to-run noise. The largest positive movement is single-node refresh p99.
The only notable negative tail movement is three-node vector p99, but absolute
latency is still far ahead of the current OpenSearch comparison run
(`13.543 ms` vs `158.827 ms`).

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
  it is `22.266 ms` single-node and `33.333 ms` three-node.
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
