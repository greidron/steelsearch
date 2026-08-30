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
- Keep API parity as the primary objective for replacement work. Performance
  diagnostics are used to protect API-gap changes from regressions and to
  explain remaining bottlenecks; they do not justify dropping OpenSearch-visible
  behavior.
- Do not repeat rejected experiments:
  - first-dimension vector scan
  - refreshed document direct lookup
  - L2 warm sample scan
  - low-threshold vector shard parallelism
  - refresh busy-wait sleep reduction
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

## Accepted: No-op Refresh Persist Skip

- Finding: latest full benchmark had no SteelSearch-slower-than-OpenSearch
  operations, but refresh remained the highest SteelSearch p99 operation. The
  engine already skipped Tantivy work when no index had pending changes, but it
  still returned `refreshed=true`; the REST layer therefore persisted runtime
  state after every explicit refresh, including no-op refresh requests.
- Code change:
  - `TantivyEngine::refresh` now returns `RefreshResponse { refreshed: false }`
    when all requested indices are already current.
  - Standalone `_refresh` and `{index}/_refresh` routes only run after-refresh
    persistence when the native engine actually refreshed at least one index.
- Correctness surface: write visibility still marks runtime documents refreshed
  after explicit refresh. Only the no-op persistence side effect is skipped.
- Targeted validation:
  - `cargo fmt --check`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy refresh -- --nocapture`:
    `10 passed, 0 failed`.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node daemon_refresh_endpoints_and_write_refresh_policy_control_search_visibility --features standalone-runtime -- --nocapture`:
    `1 passed, 0 failed`.
- Diagnostic benchmark:
  `target/search-benchmark-matrix-refresh-noop-persist-skip-single-20260830/summary.json`
  reported SteelSearch single-node `730.51 ops/s`.
- Full matrix after the correctness guard:
  `target/search-benchmark-matrix-refresh-noop-persist-skip-fixed-full-20260830/summary.json`

| Metric | Previous full | No-op persist skip full | Change |
| --- | ---: | ---: | ---: |
| SteelSearch single-node throughput | 724.85 ops/s | 738.14 ops/s | +1.83% |
| SteelSearch three-node throughput | 881.69 ops/s | 886.68 ops/s | +0.57% |
| SteelSearch single-node refresh p99 | 20.71 ms | 19.40 ms | -6.33% |
| SteelSearch three-node refresh p99 | 23.17 ms | 24.01 ms | +3.64% |

- Three-node SteelSearch rerun:
  `target/search-benchmark-matrix-refresh-noop-persist-skip-fixed-three-rerun-20260830/summary.json`
  reported `893.20 ops/s` and refresh p99 `23.08 ms`, classifying the full
  matrix three-node refresh p99 increase as non-persistent tail noise.
- OpenSearch comparison in the final full matrix: SteelSearch single-node
  `738.14 ops/s` vs OpenSearch `219.11 ops/s`; SteelSearch three-node
  `886.68 ops/s` vs OpenSearch `88.33 ops/s`; no
  SteelSearch-slower-than-OpenSearch metrics.
- Decision: accepted. The change improves the remaining refresh tail without
  hurting overall benchmark throughput.

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

## Current HEAD Diagnostic Refresh Reading

- Current source HEAD inspected for this note: `dcb462f2`.
- Full comparison artifact:
  `target/search-benchmark-matrix-api-snapshot-status-query-params-full-20260830/summary.json`.
- Latest single-client operation-resource diagnostic:
  `target/search-benchmark-matrix-current-head-op-deltas-client1-20260830-rerun/summary.json`.

Full comparison result:

| Topology | SteelSearch throughput | OpenSearch throughput | Ratio | SteelSearch refresh p99 | OpenSearch refresh p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| single-node | 740.086 ops/s | 213.154 ops/s | 3.47x | 20.361 ms | 244.368 ms |
| three-node | 884.933 ops/s | 88.207 ops/s | 10.03x | 21.037 ms | 381.442 ms |

The full comparison reports no SteelSearch-slower-than-OpenSearch metrics for
either topology.

Single-client operation-resource deltas show the remaining SteelSearch-local
refresh cost:

| Operation | Count | Mean | p99 | Dominant telemetry |
| --- | ---: | ---: | ---: | --- |
| refresh | 109 | 5.782 ms | 17.161 ms | `refresh_tantivy_commit_nanos=867035733` |
| vector | 368 | 2.772 ms | 3.879 ms | `vector_candidate_scan_nanos=213443888` |
| hybrid | 260 | 2.807 ms | 3.914 ms | `vector_candidate_scan_nanos=151252012` |
| write | 403 | 1.070 ms | 1.278 ms | no native hot counter |

The practical conclusion is that the next functional API-gap changes should
continue to run the full benchmark matrix as a regression gate, but the
remaining refresh tail should not be chased with small lock/env/cache tweaks.
Prior rejected runs show those changes either shift variance or increase
Tantivy commit cost. A real refresh improvement likely needs a larger design
change around the refresh/commit lifecycle or shard-local writer/reader
ownership, and must preserve the `_refresh` and `refresh=false` semantics pinned
by the compatibility fixtures.
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

## Experiment: In-Place Resident Field Cache Touch

- Code change: update an existing resident field cache entry in place on cache
  hit instead of replacing the `BTreeMap` entry with `insert(...)`. This targets
  the vector graph cache hot path after the request-result cache self-disables.
- Hypothesis: avoiding tree replacement churn on every vector query would reduce
  vector-only request overhead without changing cache telemetry semantics.
- Targeted validation before benchmark:
  - `cargo fmt --check`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_cache -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy knn_result_cache -- --nocapture`: pass.
- Diagnostic artifacts:
  - `target/search-benchmark-matrix-resident-cache-touch-vector-diagnostic-20260830/summary.json`
  - `target/search-benchmark-matrix-resident-cache-touch-single-20260830/summary.json`

| Run | Throughput ops/s | Vector p99 ms |
| --- | ---: | ---: |
| vector-only baseline | 84.85 | 3.97 |
| in-place cache touch vector-only | 85.86 | 3.91 |

| Run | Single-node throughput ops/s | Single ranking p99 ms | Single lexical p99 ms | Single write p99 ms |
| --- | ---: | ---: | ---: | ---: |
| full baseline | 654.37 | 18.37 | 15.58 | 7.53 |
| in-place cache touch single mixed | 652.00 | 20.17 | 16.48 | 8.45 |

- Decision: rejected and reverted. The vector-only run improved slightly, but
  mixed single-node throughput regressed by `0.36%` and ranking, lexical, and
  write p99 all worsened. The improvement is too narrow for the current
  no-regression rule.

## Experiment: SteelSearch Binary Mimalloc Global Allocator

- Code change: set `mimalloc::MiMalloc` as the global allocator for the
  `steelsearch` binary only.
- Hypothesis: the current hot paths allocate and clone many JSON/source,
  `SearchHit`, and map objects. A lower-contention allocator should reduce
  mixed workload tail latency without changing engine semantics.
- Validation before benchmark:
  - `cargo fmt --check`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly check -q -p os-node --features standalone-runtime`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_correctness_matches_exact_hnsw_filter_and_hybrid_rankings -- --nocapture`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node --features standalone-runtime --bin steelsearch main_request_supports_local_subset -- --nocapture`: binary target compiled; filter matched `0` tests.
- Benchmark artifacts:
  - `target/search-benchmark-matrix-mimalloc-single-20260830/summary.json`
  - `target/search-benchmark-matrix-mimalloc-single-rerun-20260830/summary.json`
  - `target/search-benchmark-matrix-mimalloc-vector-diagnostic-20260830/summary.json`
  - `target/search-benchmark-matrix-mimalloc-write-diagnostic-20260830/summary.json`
  - `target/search-benchmark-matrix-mimalloc-full-20260830/summary.json`

| Run | Single-node throughput ops/s | Refresh p99 ms | Vector p99 ms | Write p99 ms |
| --- | ---: | ---: | ---: | ---: |
| full baseline | 654.37 | 45.27 | 20.47 | 7.53 |
| mimalloc single mixed | 697.23 | 50.68 | 17.48 | 7.88 |
| mimalloc single mixed rerun | 701.17 | 26.52 | 16.95 | 8.07 |
| mimalloc full single-node | 699.61 | 39.88 | 16.58 | 8.04 |

| Run | Three-node throughput ops/s | Refresh p99 ms | Vector p99 ms | Write p99 ms |
| --- | ---: | ---: | ---: | ---: |
| full baseline | 812.14 | 30.80 | 14.29 | 9.09 |
| mimalloc full three-node | 875.42 | 25.82 | 11.84 | 8.00 |

| Run | Throughput ops/s | Vector p99 ms |
| --- | ---: | ---: |
| vector-only baseline | 84.85 | 3.97 |
| mimalloc vector-only | 89.25 | 3.56 |

| Run | Throughput ops/s | Write p99 ms |
| --- | ---: | ---: |
| mimalloc write-only | 109.95 | 1.60 |

- Decision: accepted. Full-matrix throughput improved by `6.91%` on
  single-node and `7.79%` on three-node, vector-only throughput improved by
  `5.18%`, and SteelSearch remains faster than OpenSearch in every benchmarked
  operation. The single-node mixed write p99 is a watchpoint (`7.53 -> 8.04 ms`
  in the full matrix), but isolated write-only p99 is low (`1.60 ms`) and the
  three-node write p99 improved (`9.09 -> 8.00 ms`), so the mixed single-node
  write tail is not treated as a blocking allocator regression.

## Experiment: Mimalloc Local Dynamic TLS Feature

- Code change: enable the `local_dynamic_tls` feature on the `mimalloc`
  dependency used by the `steelsearch` binary global allocator.
- Hypothesis: thread-local allocator fast paths might further reduce allocation
  overhead on the Actix/Tokio worker workload.
- Validation before benchmark:
  - `cargo fmt --check`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly check -q -p os-node --features standalone-runtime`: pass.
- Benchmark artifacts:
  - `target/search-benchmark-matrix-mimalloc-localtls-single-20260830/summary.json`
  - `target/search-benchmark-matrix-mimalloc-localtls-vector-20260830/summary.json`
  - `target/search-benchmark-matrix-mimalloc-localtls-full-20260830/summary.json`

| Run | Single-node throughput ops/s | Single refresh p99 ms | Single vector p99 ms | Single write p99 ms |
| --- | ---: | ---: | ---: | ---: |
| full baseline | 654.37 | 45.27 | 20.47 | 7.53 |
| accepted plain mimalloc full | 699.61 | 39.88 | 16.58 | 8.04 |
| mimalloc local_dynamic_tls full | 691.03 | 25.28 | 18.01 | 8.07 |

| Run | Three-node throughput ops/s | Three hybrid p99 ms | Three sort_filter p99 ms |
| --- | ---: | ---: | ---: |
| accepted plain mimalloc full | 875.42 | 11.26 | 10.46 |
| mimalloc local_dynamic_tls full | 882.62 | 12.61 | 11.42 |

| Run | Vector-only throughput ops/s | Vector-only p99 ms |
| --- | ---: | ---: |
| accepted plain mimalloc | 89.25 | 3.56 |
| mimalloc local_dynamic_tls | 90.60 | 3.61 |

- Decision: rejected and reverted. The feature improved three-node throughput
  slightly and vector-only throughput, but it regressed the current accepted
  plain-mimalloc single-node full matrix by `1.23%` and worsened single-node
  vector p99 by `8.62%`. Since the comparison baseline is the current accepted
  state, this feature is not kept.

## Experiment: Refresh Busy-Wait Sleep 100us

- Code change: lower refresh contention retry sleep from `1ms` to `100us`.
- Hypothesis: concurrent `_refresh` callers that observe an in-progress
  incremental refresh pay retry latency in 1ms units. A shorter wait might
  reduce refresh p99 without changing refresh semantics.
- Benchmark artifact:
  - `target/search-benchmark-matrix-refresh-sleep100us-full-20260830/summary.json`

| Run | Single-node throughput ops/s | Single refresh p99 ms | Single vector p99 ms | Single write p99 ms |
| --- | ---: | ---: | ---: | ---: |
| accepted plain mimalloc full | 699.61 | 39.88 | 16.58 | 8.04 |
| refresh sleep 100us full | 642.62 | 29.53 | 20.44 | 8.60 |

| Run | Three-node throughput ops/s | Three refresh p99 ms | Three vector p99 ms | Three write p99 ms |
| --- | ---: | ---: | ---: | ---: |
| accepted plain mimalloc full | 875.42 | 25.82 | 11.84 | 8.00 |
| refresh sleep 100us full | 825.28 | 32.92 | 13.88 | 8.11 |

- Decision: rejected and reverted. Although the single-node refresh p99 sample
  improved versus the accepted plain-mimalloc run, single-node throughput
  regressed by `8.15%`, three-node throughput regressed by `5.73%`, and
  vector/write p99 worsened. The refresh contention retry sleep remains `1ms`.

## Experiment: Actix HTTP Worker Minimum 6

- Code change: raise the REST HTTP server worker count floor from `4` to `6`.
- Hypothesis: the benchmark host has 3 vCPUs and the mixed workload uses 4
  clients. Slight worker oversubscription might reduce head-of-line blocking
  when refresh/search work runs inside request handlers.
- Validation before benchmark:
  - `cargo fmt --check`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly check -q -p os-node --features standalone-runtime`: pass.
- Benchmark artifact:
  - `target/search-benchmark-matrix-http-workers6-single-20260830/summary.json`

| Run | Single-node throughput ops/s | Refresh p99 ms | Vector p99 ms | Write p99 ms |
| --- | ---: | ---: | ---: | ---: |
| accepted plain mimalloc full | 699.61 | 39.88 | 16.58 | 8.04 |
| HTTP worker floor 6 single mixed | 697.17 | 20.45 | 17.70 | 8.60 |

- Decision: rejected and reverted. Refresh p99 improved in the targeted run,
  but throughput regressed versus the current accepted plain-mimalloc state and
  vector/write p99 worsened. The default worker floor remains `4`.

## Post API-Gap Current Bottleneck Check

After the snapshot clone subset API-gap change, the latest full benchmark
artifact is
`target/search-benchmark-matrix-api-snapshot-clone-subset-full-20260830/summary.json`.

Full matrix result:

| Topology | SteelSearch throughput | OpenSearch throughput | Ratio | SteelSearch slower metrics |
| --- | ---: | ---: | ---: | ---: |
| single-node | 735.97 ops/s | 220.65 ops/s | 3.34x | 0 |
| three-node | 879.89 ops/s | 84.49 ops/s | 10.41x | 0 |

Relative to the preceding snapshot-status shard-count full baseline
(`target/search-benchmark-matrix-api-snapshot-status-shards-full-20260830/summary.json`),
SteelSearch throughput moved by `-0.08%` single-node and `-0.73%`
three-node. This is classified as performance-neutral for the API change.

Current clients=1 operation-delta diagnostic:
`target/search-benchmark-matrix-current-opdeltas-single-20260830-post-api/summary.json`.

| Operation | p99 | Main native counter | Per-operation cost |
| --- | ---: | --- | ---: |
| refresh | 14.08 ms | `refresh_tantivy_commit_nanos` | 8.21 ms/op |
| vector | 4.92 ms | `vector_candidate_scan_nanos` | 582.04 us/op |
| facet | 4.19 ms | `native_response_body_build_nanos` | 6.32 us/op |
| hybrid | 3.48 ms | `vector_candidate_scan_nanos` | 581.56 us/op |

Findings:

- SteelSearch is not currently slower than OpenSearch on the measured default
  benchmark operations. The old "Rust slower than Java" diagnosis no longer
  matches the retained full-matrix evidence.
- The remaining SteelSearch-local refresh tail is still dominated by Tantivy
  `IndexWriter::commit()`, not Rust execution overhead. The latest diagnostic
  reports `911.48 ms` total commit time over `111` refresh operations, versus
  `60.93 ms` document-add, `77.76 ms` doc-id lookup, and `27.62 ms` reload.
- The remaining vector/hybrid cost is exact refreshed-vector scanning. The
  latest diagnostic reports about `582 us/op` in `vector_candidate_scan_nanos`
  for both vector and hybrid.
- The default live write workload includes the `embedding` vector field, so
  preserving vector graph cache entries across refresh is not a safe win for
  this workload without field-level stale detection. Blindly retaining those
  entries risks stale k-NN results after vector writes.
- No new code change is retained from this check. The previously rejected
  short-term experiments already cover the cheap refresh/vector knobs, and a
  credible next performance step remains structural: a non-commit NRT publish
  path for refresh, or a refreshed-generation ANN/vector index that is built at
  refresh/segment creation and reused by queries.

## Experiment: Reuse Fast-Field Resident Byte Estimates

- Code change: mirror the vector resident-cache touch path for fast fields by
  reusing the existing `fast_fields_by_name` resident byte estimate when a field
  cache entry is already present, instead of recalculating
  `visible_field_value_bytes(...)` on every sort/aggregation cache touch.
- Hypothesis: sort/filter and facet requests may repeatedly scan visible
  documents only to update cache telemetry, and refresh already clears the
  resident cache, so the size estimate is stable between refreshes.
- Targeted validation before benchmark:
  - `cargo fmt --check`: pass.
  - `git diff --check`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_cache -- --nocapture`:
    `2 passed, 0 failed`.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy native_tantivy_path -- --nocapture`:
    `54 passed, 0 failed`.
  - Release build:
    `RUSTFLAGS='-Awarnings' cargo +nightly build -q --release -p os-node --bin steelsearch --features standalone-runtime`.
- Diagnostic benchmark:
  `target/search-benchmark-matrix-fastfield-resident-reuse-diagnostic-20260830/summary.json`
  reported SteelSearch single-node `97.28 ops/s` for a clients=1
  `facet=50,sort_filter=50` mix.
- Full benchmark:
  `target/search-benchmark-matrix-fastfield-resident-reuse-full-20260830/summary.json`.

| Metric | Previous full | Candidate full | Change |
| --- | ---: | ---: | ---: |
| SteelSearch single-node throughput | 735.97 ops/s | 742.61 ops/s | +0.90% |
| SteelSearch three-node throughput | 879.89 ops/s | 881.54 ops/s | +0.19% |
| SteelSearch single-node nested p99 | 13.91 ms | 15.93 ms | +14.52% |
| SteelSearch single-node write p99 | 7.25 ms | 7.54 ms | +3.99% |
| SteelSearch three-node vector p99 | 11.60 ms | 12.18 ms | +4.98% |

- OpenSearch comparison: no SteelSearch-slower-than-OpenSearch metrics in the
  full candidate matrix.
- Decision: rejected and reverted. The full matrix throughput moved up, but the
  benchmark reported zero fast-field cache hits/misses/invalidations, so the
  candidate did not prove that the intended hot path was actually exercised.
  Given the weak causal evidence and the unrelated p99 regressions, the change
  is not retained under the no-regression rule.

## Experiment: Serial Vector Shard Candidate Merge

- Code change: avoid collecting serial per-shard vector candidate vectors before
  merging them into the global top-k candidate list in `exact_vector_search`.
- Hypothesis: the default 5k-document benchmark runs below the vector shard
  parallelism threshold, so removing an intermediate serial collection could
  reduce exact vector/hybrid overhead without changing ranking semantics.
- Targeted validation before benchmark:
  - `cargo fmt --check`: pass.
  - `git diff --check`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy exact_vector_search -- --nocapture`:
    pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_correctness_matches_exact_hnsw_filter_and_hybrid_rankings -- --nocapture`:
    pass.
  - Release build:
    `RUSTFLAGS='-Awarnings' cargo +nightly build -q --release -p os-node --bin steelsearch --features standalone-runtime`.
- Diagnostic benchmark:
  `target/search-benchmark-matrix-vector-serial-merge-diagnostic-20260830/summary.json`
  reported SteelSearch single-node `91.68 ops/s` for a clients=1
  `vector=50,hybrid=50` mix.

| Operation | p99 ms | Vector scan ns/op |
| --- | ---: | ---: |
| vector | 3.22 | 491385 |
| hybrid | 3.28 | 499481 |

- Decision: rejected and reverted. The targeted vector/hybrid diagnostic did
  not demonstrate a clear improvement over the current post-API-gap bottleneck
  profile, so the code change is not retained under the no-regression rule.

## Experiment: Vector Candidate Merge Worst-Case Precheck

- Code change: add a worst-candidate precheck to
  `insert_bounded_vector_candidate(...)` so shard-local top-k merge can skip
  `Vec::insert`/shift/pop when the global candidate list is already full and the
  incoming shard candidate cannot beat the current worst candidate.
- Hypothesis: exact vector search still spends measurable time in refreshed
  vector scanning and candidate maintenance. The precheck should reduce merge
  work without changing score/id ordering semantics.
- Targeted validation before benchmark:
  - `cargo fmt --check`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy exact_vector_search -- --nocapture`:
    pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_correctness_matches_exact_hnsw_filter_and_hybrid_rankings -- --nocapture`:
    pass.
  - Release build:
    `RUSTFLAGS='-Awarnings' cargo +nightly build --release -p os-node --bin steelsearch --features standalone-runtime`.
- Diagnostic benchmark:
  `target/search-benchmark-matrix-vector-merge-precheck-diagnostic-20260830/summary.json`
  reported SteelSearch single-node `92.73 ops/s` for a clients=1
  `vector=50,hybrid=50` mix.

| Operation | p99 ms | Vector scan ns/op |
| --- | ---: | ---: |
| vector | 3.40 | 511623 |
| hybrid | 3.35 | 520057 |

- Decision: rejected and reverted. Throughput moved slightly above the prior
  serial-merge diagnostic (`91.68 ops/s`), but vector/hybrid p99 and scan
  ns/op moved worse. The improvement is too weak and not aligned with the
  target bottleneck, so the change is not retained under the no-regression rule.

## Experiment: Vector Request Result Cache Hit-Rate Gate 4x

- Code change: lower the vector request-result cache poor-hit-rate multiplier
  from `16x` to `4x`, so low-reuse vector workloads stop probing/filling the
  request-result cache earlier.
- Hypothesis: the benchmark chooses random query vectors from a 5k-document
  corpus, so request-result cache hits are rare. Earlier admission shutdown
  could avoid cache-key serialization and fill overhead while preserving cache
  behavior for repeated-query workloads.
- Targeted validation before benchmark:
  - `cargo fmt --check`: pass.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy vector_cache -- --nocapture`:
    `2 passed, 0 failed`.
  - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-engine-tantivy exact_vector_search -- --nocapture`:
    pass.
  - Release build:
    `RUSTFLAGS='-Awarnings' cargo +nightly build --release -p os-node --bin steelsearch --features standalone-runtime`.
- Diagnostic benchmark:
  `target/search-benchmark-matrix-vector-cache-gate4-diagnostic-20260830/summary.json`
  reported SteelSearch single-node `91.28 ops/s` for a clients=1
  `vector=50,hybrid=50` mix. Request-result cache misses dropped from `17` to
  `11`, but no request-result cache hits were recorded.

| Operation | p99 ms | Vector scan ns/op |
| --- | ---: | ---: |
| vector | 3.24 | 503400 |
| hybrid | 3.37 | 513038 |

- Decision: rejected and reverted. The intended cache-miss reduction happened,
  but throughput regressed versus the prior serial-merge diagnostic
  (`91.68 ops/s`) and hybrid p99 moved worse. The cache gate remains at the
  retained `16x` threshold.
