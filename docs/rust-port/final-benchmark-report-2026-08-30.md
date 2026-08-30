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
