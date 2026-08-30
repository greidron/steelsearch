# Performance Optimization Ledger - 2026-08-30

## Baseline

- Commit: `e7ceed66d3a2f636690aefbb09d542eab1a85535`
- Release baseline: `v0.5.0`
- Current full benchmark artifact:
  `target/search-benchmark-matrix-api-snapshot-data-stream-full-20260830/summary.json`
- SteelSearch single-node throughput: `654.37 ops/s`
- SteelSearch three-node throughput: `812.14 ops/s`
- OpenSearch single-node throughput: `201.95 ops/s`
- OpenSearch three-node throughput: `79.30 ops/s`
- Current result: SteelSearch is not slower than OpenSearch on the benchmarked operations.

## Current Hot Spots

- Single-client diagnostic artifact:
  `target/search-benchmark-matrix-bottleneck-diagnostic-client1-20260830/report.md`
- Slowest p99 operation: `refresh` at `14.68 ms`.
- Slowest search p99 operations: `nested` at `5.28 ms`, `facet` at `5.01 ms`,
  `ranking` at `4.53 ms`.
- Largest native telemetry counter:
  `vector_candidate_scan_nanos = 386898885`.
- Response body build is small enough to ignore for now:
  `native_response_body_build_nanos = 27502821`.

## Constraints

- Keep changes only when benchmark evidence shows no regression.
- Do not repeat rejected experiments:
  - first-dimension vector scan
  - refreshed document direct lookup
  - L2 warm sample scan
  - low-threshold vector shard parallelism
- Treat vector graph cache preservation across refresh as correctness-sensitive
  when vector writes are present.

## Candidate Work

- Investigate whether refresh can invalidate only request-result caches while
  keeping reusable vector graph entries when refreshed vector columns did not
  change.
- Investigate exact vector L2 scan micro-optimizations only if they do not
  alter ranking semantics.
- Prefer targeted diagnostics before full benchmark runs.

## Experiment: L2 Refreshed Column Fast Path

- Code change: bypass generic refreshed-vector scoring for default `l2`
  refreshed vector columns and call bounded L2 scoring directly.
- Correctness surface: candidate insertion still uses the existing
  `insert_bounded_vector_candidate_by_id` path.
- Targeted validation:
  - `cargo fmt --check`: pass
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy exact_vector_search`: pass
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy bounded_l2_distance`: pass

### Diagnostic Results

| Run | Throughput ops/s | Vector scan nanos | Vector p99 ms | Hybrid p99 ms | Refresh p99 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 96.78 | 386898885 | 3.81 | 4.19 | 14.68 |
| fastpath1 | 97.85 | 357064601 | 3.70 | 4.08 | 21.39 |
| fastpath2 | 96.70 | 333061691 | 3.53 | 4.10 | 16.44 |

- Preliminary read: vector scan CPU improved by roughly 8-14%, while total
  single-client throughput is effectively flat because the workload remains
  mixed and refresh/facet/nested still dominate p99 variance.
- Full matrix result:
  `target/search-benchmark-matrix-l2-column-fastpath-full-20260830/summary.json`
- SteelSearch single-node throughput moved from `654.37` to `652.75 ops/s`.
- SteelSearch three-node throughput moved from `812.14` to `819.51 ops/s`.
- SteelSearch single-node vector p99 moved from `20.47` to `20.74 ms`.
- SteelSearch single-node rerun:
  `target/search-benchmark-matrix-l2-column-fastpath-steel-single-rerun-20260830/summary.json`
- Current single-node rerun baseline was `664.41 ops/s`; fastpath rerun was
  `656.47 ops/s`.
- Decision: rejected and reverted. The scan counter improved, but the
  user-facing 1-node workload result did not improve reliably.

## Experiment: Lazy Previous Segment Lookup

- Code change: try to reuse previous Tantivy `_id` lookup entries by segment
  ordinal before building a segment-id map during incremental refresh.
- Targeted validation:
  - `cargo fmt --check`: pass
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy refresh`: pass
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy exact_vector_search`: pass
- Diagnostic artifact:
  `target/search-benchmark-matrix-refresh-docid-fastpath-diagnostic-client1-20260830/summary.json`

| Run | Throughput ops/s | Refresh p99 ms | Vector p99 ms | Hybrid p99 ms |
| --- | ---: | ---: | ---: | ---: |
| baseline | 96.78 | 14.68 | 3.81 | 4.19 |
| refresh-fastpath | 97.93 | 16.07 | 3.96 | 5.03 |

- Decision: rejected and reverted. Throughput moved up in the diagnostic run,
  but the target refresh p99 and hybrid p99 regressed.
