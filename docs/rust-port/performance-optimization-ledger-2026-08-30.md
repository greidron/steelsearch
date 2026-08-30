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

## Feasibility Check: Tantivy Non-Commit Refresh

- Source checked: local Tantivy `0.21.1` crate under
  `~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/tantivy-0.21.1`.
- Relevant implementation:
  - `IndexWriter::prepare_commit()` recreates the document channel, joins
    indexing workers, and flushes pending documents into segments.
  - `PreparedCommit::commit()` schedules `SegmentUpdater::schedule_commit(...)`.
  - `SegmentUpdater::schedule_commit(...)` purges deletes, commits the segment
    manager state, writes `meta.json` through `save_metas(...)`, runs garbage
    collection, and considers merges.
  - `IndexReader::reload()` explicitly documents and implements reload of the
    last committed state; it opens `index.searchable_segments()`, which depends
    on committed metadata.
- Decision: no small public-API patch is available in Tantivy `0.21.1` to make
  SteelSearch `_refresh` publish newly indexed documents without paying the
  commit/meta path. Matching OpenSearch/Lucene NRT refresh semantics would
  require a deeper engine change: fork/extend Tantivy internals or introduce a
  SteelSearch-owned refreshed generation that can publish immutable segment-like
  state independently of Tantivy durability commits.

## Experiment: Bounded L2 NEON Check Interval 64

- Code change: increase the `squared_l2_distance_bounded_neon(...)` partial
  horizontal reduction interval from 16 lanes to 64 lanes to reduce NEON
  reduction overhead in the 384-dimensional vector scan path.
- Targeted validation before benchmark:
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy bounded_l2_distance -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_correctness_matches_exact_hnsw_filter_and_hybrid_rankings -- --nocapture`: pass.
- Diagnostic artifact:
  `target/search-benchmark-matrix-vector-bounded64-diagnostic-client1-20260830/summary.json`

| Run | Throughput ops/s | Vector p99 ms | Vector scan ns/op | Hit materialization ns/op |
| --- | ---: | ---: | ---: | ---: |
| vector-only baseline | 84.85 | 3.97 | 558891 | 119033 |
| bounded64 | 86.55 | 4.07 | 614690 | 112403 |

- Decision: rejected and reverted. Overall throughput moved up slightly, but
  the target vector scan cost and vector p99 regressed, so the result is more
  likely noise or shifted work than a durable hot-path improvement.

## Experiment: KNN Request Result Cache 1 MiB Per Field

- Code change: increase `MAX_KNN_CACHE_BYTES_PER_FIELD` from `256 KiB` to
  `1 MiB` so the vector-only benchmark's query variants can stay resident with
  fewer byte-limit evictions.
- Targeted validation before benchmark:
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy knn_cache -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_cache -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node --lib --features standalone-runtime search_cache -- --nocapture`: pass.
- Diagnostic artifacts:
  - `target/search-benchmark-matrix-knn-cache-1m-vector-diagnostic-20260830/summary.json`
  - `target/search-benchmark-matrix-knn-cache-1m-mixed-diagnostic-client1-20260830/summary.json`
  - `target/search-benchmark-matrix-knn-cache-1m-mixed-rerun-client1-20260830/summary.json`
  - `target/search-benchmark-matrix-knn-cache-1m-full-20260830/summary.json`

| Run | Throughput ops/s | Vector p99 ms | Refresh p99 ms | Request cache capacity evictions |
| --- | ---: | ---: | ---: | ---: |
| vector-only baseline | 84.85 | 3.97 | n/a | 10 |
| vector-only cache1m | 87.01 | 3.82 | n/a | 1 |
| mixed client1 baseline | 89.81 | 3.87 | 16.92 | 0 |
| mixed client1 cache1m rerun | 89.74 | 3.58 | 13.23 | 0 |
| full single-node baseline | 654.37 | 20.47 | 45.27 | n/a |
| full single-node cache1m | 626.47 | 21.08 | 30.13 | n/a |
| full three-node baseline | 812.14 | 14.29 | 30.80 | n/a |
| full three-node cache1m | 826.02 | 14.11 | 30.11 | n/a |

- Decision: rejected and reverted. The targeted vector-only workload improved,
  but the full single-node benchmark regressed by about 4.3% overall and vector
  p99 also worsened. The three-node gain is not enough to justify hurting the
  single-node target.

## Experiment: KNN Request Result Cache 32 Entries And 1 MiB

- Code change: increase `MAX_KNN_CACHE_ENTRIES_PER_FIELD` from `16` to `32`
  and `MAX_KNN_CACHE_BYTES_PER_FIELD` from `256 KiB` to `1 MiB`, attempting to
  keep the vector-only benchmark's query variants resident without admission
  shutdown from capacity eviction.
- Targeted validation before benchmark:
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy knn_cache -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_cache -- --nocapture`: pass.
- Diagnostic artifact:
  `target/search-benchmark-matrix-knn-cache-32-1m-vector-diagnostic-20260830/summary.json`

| Run | Throughput ops/s | Vector p99 ms | Request cache misses | Request cache capacity evictions |
| --- | ---: | ---: | ---: | ---: |
| vector-only baseline | 84.85 | 3.97 | 17 | 10 |
| cache 32/1m | 86.65 | 3.81 | 29 | 1 |
| cache 16/1m | 87.01 | 3.82 | 17 | 1 |

- Decision: rejected and reverted. The combined entry/byte increase did not
  improve on the smaller 16-entry/1MiB experiment, still left capacity eviction
  in place, and increased request-result cache misses.

## Experiment: Disable Pure KNN Request Result Cache

- Code change: make `vector_request_result_cache_supported(...)` return true
  only for hybrid/bool k-NN queries, not pure top-level `knn` queries, because
  the full benchmark showed pure vector request-result cache misses and
  invalidations without useful hits.
- Targeted validation:
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_correctness_matches_exact_hnsw_filter_and_hybrid_rankings -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy knn_result_cache_is -- --nocapture`: failed because the existing API-level cache behavior test expects pure k-NN requests to populate the cache.
- Decision: rejected and reverted before benchmark. Disabling the cache would
  remove existing tested behavior rather than optimize it.

## Experiment: Non-Vector Sharded Tantivy Parallel Threshold 10k

- Code change: raise the per-request non-vector sharded Tantivy reduce
  parallelism gate from `self.documents.len() >= 2_048` to `>= 10_000` in
  `search_hits_for_query_native_sharded(...)` and
  `search_hits_page_for_query_native_sharded_tantivy(...)`.
- Hypothesis: for the current 5k-document, 3-shard, 4-client benchmark shape,
  per-request Rayon fan-out over shards may oversubscribe the 3-vCPU runner and
  push p99 tail latency. Serial shard reduce below 10k documents might improve
  single-node tail behavior.
- Targeted validation before benchmark:
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy multi_shard -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy native_tantivy_path -- --nocapture`: pass.
- Diagnostic artifacts:
  - `target/search-benchmark-matrix-shard-parallel-threshold-10k-single-20260830/summary.json`
  - `target/search-benchmark-matrix-shard-parallel-threshold-10k-full-20260830/summary.json`

| Run | Single-node throughput ops/s | Single refresh p99 ms | Single ranking p99 ms | Single lexical p99 ms | Single write p99 ms | Three-node throughput ops/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 654.37 | 45.27 | 18.37 | 15.58 | 7.53 | 812.14 |
| threshold 10k | 652.39 | 24.84 | 20.25 | 16.59 | 7.97 | 815.45 |

- Decision: rejected and reverted. The experiment improved single-node refresh
  p99 materially and slightly improved three-node throughput, but single-node
  overall throughput regressed by about 0.30% and ranking, lexical, and write
  p99 all worsened. The result is mixed rather than a clean improvement.

## Experiment: Segment Doc-ID Lookup Arc Reuse

- Code change: store Tantivy `_id` lookup tables as per-segment
  `Arc<Vec<Option<String>>>` values so incremental refresh can reuse unchanged
  segment lookup tables by cloning an `Arc` instead of cloning the whole vector
  of document IDs.
- Hypothesis: `refresh_tantivy_doc_id_lookup_nanos` is smaller than commit
  cost but still visible in refresh telemetry. Avoiding full-table clones for
  reused segments should reduce refresh p99 without changing search semantics.
- Targeted validation before benchmark:
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy native_tantivy_path -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy refresh -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy multi_shard -- --nocapture`: pass.
- Diagnostic artifacts:
  - `target/search-benchmark-matrix-docid-arc-telemetry-client1-20260830/summary.json`
  - `target/search-benchmark-matrix-docid-arc-full-20260830/summary.json`
  - `target/search-benchmark-matrix-docid-arc-single-rerun-20260830/summary.json`

| Run | Throughput ops/s | Refresh p99 ms | Refresh doc-id lookup nanos |
| --- | ---: | ---: | ---: |
| client1 telemetry baseline | 89.81 | 16.92 | 94439775 |
| client1 telemetry doc-id Arc | 90.27 | 13.75 | 81983343 |

| Run | Single-node throughput ops/s | Single refresh p99 ms | Three-node throughput ops/s |
| --- | ---: | ---: | ---: |
| full baseline | 654.37 | 45.27 | 812.14 |
| full doc-id Arc | 657.85 | 24.09 | 826.09 |
| single-node rerun doc-id Arc | 643.51 | 29.05 | n/a |

- Decision: rejected and reverted. The direct client1 telemetry moved in the
  expected direction and the first full matrix improved throughput, but the
  single-node rerun regressed throughput to `643.51 ops/s`. Because the
  acceptance rule rejects changes with reproduced throughput regression, this
  remains documentation-only evidence and no code from the experiment is kept.

## Experiment: L2 Norm Lower-Bound Skip For Refreshed Vector Columns

- Code change: store L2 norms for `l2` vector columns, compute the query L2
  norm, and skip a full vector distance calculation when
  `abs(query_norm - document_norm)^2` is already worse than the current
  bounded top-k window. This preserves exact top-k semantics by using the
  triangle-inequality lower bound.
- Hypothesis: after the top-k candidate window is full, the lower bound can
  avoid some 384-dimensional L2 distance calculations in exact vector search.
- Pre-check: the benchmark vector generator showed query-dependent skip
  potential from `0%` to about `37%`, so the branch was plausible but data
  dependent.
- Targeted validation before benchmark:
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy bounded_l2_distance -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_correctness_matches_exact_hnsw_filter_and_hybrid_rankings -- --nocapture`: pass.
- Diagnostic artifact:
  `target/search-benchmark-matrix-vector-l2-norm-bound-diagnostic-20260830/summary.json`

| Run | Throughput ops/s | Vector p99 ms | Vector scan ns/op |
| --- | ---: | ---: | ---: |
| vector-only baseline | 84.85 | 3.97 | 558891 |
| L2 norm bound | 86.03 | 4.10 | 597576 |

- Decision: rejected and reverted. Throughput improved slightly, but the target
  scan cost and vector p99 both regressed, meaning the extra norm branch and
  memory load cost more than the skipped distances for this benchmark shape.

## Experiment: NEON Full-Distance Four-Accumulator Unroll

- Code change: unroll the aarch64 NEON full-distance helpers
  `squared_l2_distance_neon(...)` and `dot_product_neon(...)` from one
  accumulator over 4 floats per loop to four accumulators over 16 floats per
  loop. The bounded early-exit L2 helper was not changed because prior
  check-interval tuning already regressed the target vector path.
- Hypothesis: on the Neoverse-N1 benchmark host, reducing the FMA dependency
  chain in the 384-dimensional vector distance loop might improve exact vector
  scan throughput.
- Environment check: the benchmark host is `aarch64`, `Neoverse-N1`, 3 vCPU,
  with `asimd`/NEON available.
- Targeted validation before benchmark:
  - `cargo fmt --check`: pass. `cargo +nightly fmt --check` could not run
    because `rustfmt` is not installed for the nightly toolchain.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy bounded_l2_distance -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_correctness_matches_exact_hnsw_filter_and_hybrid_rankings -- --nocapture`: pass.
- Diagnostic artifact:
  `target/search-benchmark-matrix-vector-neon-unroll-diagnostic-20260830/summary.json`

| Run | Throughput ops/s | Vector p99 ms | Vector scan ns/op |
| --- | ---: | ---: | ---: |
| vector-only baseline | 84.85 | 3.97 | 558891 |
| NEON unroll | 83.11 | 4.11 | 584665 |

- Decision: rejected and reverted. The unroll increased scan cost and worsened
  vector p99, so the current compiler/CPU combination performs better with the
  simpler single-accumulator NEON loop.

## Experiment: Source-Less Vector Result Cache Entries

- Code change: store cached vector search hits without `_source`, then hydrate
  `_source` from the refreshed document map on cache hits.
- Hypothesis: previous request-result cache capacity increases improved a
  targeted vector-only run but regressed the full matrix. Reducing each cached
  entry's resident payload might preserve the vector-only benefit without
  increasing total cache capacity.
- Targeted validation before benchmark:
  - `cargo fmt --check`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_correctness_matches_exact_hnsw_filter_and_hybrid_rankings -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy source_projection -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy knn_result_cache -- --nocapture`: pass.
- Diagnostic artifacts:
  - `target/search-benchmark-matrix-source-less-vector-cache-diagnostic-20260830/summary.json`
  - `target/search-benchmark-matrix-source-less-vector-cache-full-20260830/summary.json`
  - `target/search-benchmark-matrix-source-less-vector-cache-single-rerun-20260830/summary.json`

| Run | Throughput ops/s | Vector p99 ms | Request cache capacity evictions |
| --- | ---: | ---: | ---: |
| vector-only baseline | 84.85 | 3.97 | 10 |
| source-less vector cache | 85.81 | 3.73 | 1 |

| Run | Single-node throughput ops/s | Single refresh p99 ms | Single lexical p99 ms | Three-node throughput ops/s |
| --- | ---: | ---: | ---: | ---: |
| full baseline | 654.37 | 45.27 | 15.58 | 812.14 |
| full source-less cache | 661.36 | 27.76 | 17.42 | 807.57 |
| single-node rerun source-less cache | 654.39 | 24.64 | 16.96 | n/a |

- Decision: rejected and reverted. The targeted vector-only run improved
  throughput, vector p99, and cache capacity evictions, but the full matrix was
  mixed and the single-node rerun lost the throughput gain while keeping lexical
  p99 above baseline. Because this is not a clear no-regression improvement, the
  code is not kept.
