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

## Refresh Phase Telemetry

- Code change: expose phase counters for incremental Tantivy refresh:
  - `refresh_tantivy_document_add_nanos`
  - `refresh_tantivy_commit_nanos`
  - `refresh_tantivy_reload_nanos`
  - `refresh_tantivy_doc_id_lookup_nanos`
- Diagnostic artifact:
  `target/search-benchmark-matrix-refresh-phase-telemetry-diagnostic-client1-20260830/summary.json`
- Result over 105 refresh operations:
  - document add: `50367762 ns`
  - commit: `778595286 ns`
  - reload: `38435967 ns`
  - doc-id lookup: `94439775 ns`
- Finding: Tantivy `commit()` is the dominant refresh cost.

## Experiment: Tantivy Batch Add During Refresh

- Code change: use Tantivy `IndexWriter::run` with a batch of add operations
  instead of calling `add_document` for each pending document.
- Diagnostic artifact:
  `target/search-benchmark-matrix-refresh-batch-add-diagnostic-client1-20260830/summary.json`

| Run | Throughput ops/s | Refresh p99 ms | Add ns | Commit ns | Lookup ns |
| --- | ---: | ---: | ---: | ---: | ---: |
| phase-telemetry | 89.81 | 16.92 | 50367762 | 778595286 | 94439775 |
| batch-add | 89.86 | 14.55 | 46478241 | 924542384 | 102522221 |

- Decision: rejected and reverted. Batch add reduced document-add time, but
  increased the dominant commit cost.

## Experiment: Tantivy NoMergePolicy

- Code change: set Tantivy `NoMergePolicy` on in-memory search-state writers.
- Diagnostic artifact:
  `target/search-benchmark-matrix-refresh-no-merge-diagnostic-client1-20260830/summary.json`

| Run | Throughput ops/s | Refresh p99 ms | Facet p99 ms | Ranking p99 ms | Commit ns | Reload ns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| phase-telemetry | 89.81 | 16.92 | 5.23 | 4.82 | 778595286 | 38435967 |
| no-merge | 87.40 | 15.55 | 6.00 | 6.02 | 844102907 | 111755669 |

- Decision: rejected and reverted. Merge suppression did not reduce commit
  time and hurt the mixed search workload.

## Experiment: Tantivy Writer Heap 64 MiB

- Code change: increase `TANTIVY_WRITER_HEAP_BYTES` from `16 MiB` to `64 MiB`
  so Tantivy can use more indexing workers on the 3-vCPU benchmark host.
- Diagnostic artifact:
  `target/search-benchmark-matrix-refresh-writer-64m-diagnostic-client1-20260830/summary.json`

| Run | Throughput ops/s | RSS MiB | Refresh p99 ms | Commit ns | Reload ns | Lookup ns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| phase-telemetry | 89.81 | 553.49 | 16.92 | 778595286 | 38435967 | 94439775 |
| writer-64m | 87.26 | 567.72 | 30.40 | 1709767701 | 57577058 | 160885233 |

- Decision: rejected and reverted. Larger writer heap increased Tantivy
  commit cost and refresh tail latency.

## Experiment: Deferred Tantivy Commit Overlay

- Code change: track the seq_no visible in the Tantivy reader separately from
  the SteelSearch refreshed seq_no, defer small append-only incremental
  refresh commits, and overlay the deferred documents into native search/count
  paths from the refreshed document map.
- Targeted validation before benchmark:
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy append_only_refresh -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy refresh`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy native_tantivy_path -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node --lib --features standalone-runtime search_cache`: pass.
- Diagnostic artifact:
  `target/search-benchmark-matrix-refresh-overlay-diagnostic-client1-20260830/summary.json`

| Run | Throughput ops/s | Refresh p99 ms | Commit ns | Reload ns | Lookup ns |
| --- | ---: | ---: | ---: | ---: | ---: |
| phase-telemetry | 89.81 | 16.92 | 778595286 | 38435967 | 94439775 |
| deferred-overlay | 88.26 | 27.56 | 1631475244 | 60799530 | 169252196 |

- Decision: rejected and reverted. Deferring small commits caused larger later
  commits and worse refresh tail latency, while the overlay search work did not
  recover enough throughput to compensate.

## Experiment: L2 Coarse Vector Bucket Index

- Code change: build a small in-memory coarse pivot/bucket index for large
  refreshed L2 vector columns, use the nearest buckets for unconstrained k-NN
  query candidates, and incrementally append new vectors to the existing
  buckets on append-only refresh.
- Targeted validation before benchmark:
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy l2_coarse_vector_index -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_correctness_matches_exact_hnsw_filter_and_hybrid_rankings -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy refresh`: pass.
- Diagnostic artifacts:
  - `target/search-benchmark-matrix-vector-coarse512-diagnostic-20260830/summary.json`
  - `target/search-benchmark-matrix-vector-coarse512-mixed-diagnostic-20260830/summary.json`

| Run | Throughput ops/s | Vector p99 ms | Vector scan ns | Refresh p99 ms |
| --- | ---: | ---: | ---: | ---: |
| vector-only baseline | 84.85 | 3.97 | 948438094 | n/a |
| vector-only coarse512 | 86.29 | 3.80 | 929368313 | n/a |
| phase-telemetry mixed | 89.81 | 3.87 | 365366277 | 16.92 |
| coarse512 mixed | 88.48 | 4.08 | 362864639 | 33.25 |

- Decision: rejected and reverted. The vector-only improvement was too small
  and did not survive the mixed workload; the extra coarse-index maintenance
  increased tail latency outside the vector operation enough to reduce overall
  throughput.

## Current Structural Conclusion

- The remaining refresh bottleneck is not Rust vs Java execution speed. It is
  the current SteelSearch refresh model: explicit `_refresh` drives Tantivy
  `IndexWriter::commit()`, while OpenSearch/Lucene refresh primarily opens a
  new searcher over visible segment state and does not need to make every
  refresh pay the same durability-style commit cost.
- The remaining vector-query cost is also structural. Production k-NN search
  currently routes through `exact_vector_search`, which scans refreshed vector
  columns. The existing `hnsw_vector_search` helper constructs its graph from
  refreshed documents at query time, so it is not a reusable ANN index and
  should not be wired into the hot path as-is.
- Rejected short-term experiments now cover the cheap-looking options:
  refreshed L2 scan fast paths, lazy doc-id lookup, batch add, merge policy,
  writer heap, deferred commit overlay, and coarse buckets. The next credible
  improvement needs a real segment/refreshed-generation search structure:
  either a non-committing Tantivy reader refresh path or a persisted/incremental
  ANN graph built at refresh/segment creation and reused by k-NN queries.
