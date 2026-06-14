# Tantivy Native Benchmark Report

Date: 2026-05-31 UTC

## Scope

This report records the refreshed benchmark evidence for the current Tantivy native worktree after the native-readiness fixes.

Benchmarks covered:

1. HTTP Steelsearch vs OpenSearch search benchmark matrix.
2. Single-node and three-node topology comparison.
3. Mixed workload operations: `write`, `lexical`, `ranking`, `facet`, `sort_filter`, `vector`, `hybrid`, and `refresh`.
4. Internal deterministic `os-engine-tantivy` native baseline bench.
5. Explicit report listing of metrics where Steelsearch is slower than OpenSearch.

## Artifacts

| Artifact | Path |
| --- | --- |
| Benchmark matrix summary | `target/search-benchmark-matrix-native-final-20260531/summary.json` |
| Benchmark matrix Markdown report | `target/search-benchmark-matrix-native-final-20260531/report.md` |
| Benchmark matrix execution log | `target/search-benchmark-matrix-native-final-20260531.log` |
| Deterministic native baseline log | `target/tantivy-native-benchmarks/deterministic_baselines_20260531.log` |
| Benchmark runner | `tools/run-search-benchmark-matrix.py` |
| HTTP load baseline runner | `tools/run-http-load-baseline.py` |
| Deterministic native bench | `crates/os-engine-tantivy/benchmarks/deterministic_baselines.rs` |

## Benchmark Reinforcement Added

The benchmark matrix report now includes:

1. p50, p95, p99, and mean latency comparisons for each operation.
2. Automatic `Steelsearch slower than OpenSearch` sections per topology.
3. Machine-readable slower-metric entries in `summary.json` under `steelsearch_slower_than_opensearch`.
4. Updated deterministic native bench compatibility with the current `SearchRequest` shape.

## HTTP Benchmark Configuration

Command:

```bash
python3 tools/run-search-benchmark-matrix.py \
  --output-dir target/search-benchmark-matrix-native-final-20260531 \
  --corpus-size 1000 \
  --vector-dimension 16 \
  --duration-seconds 10 \
  --clients 4 \
  --number-of-shards 3 \
  --number-of-replicas 1 \
  --timeout-seconds 10
```

Configuration:

| Field | Value |
| --- | ---: |
| Corpus size | 1000 documents |
| Vector dimension | 16 |
| Duration per scenario | 10 seconds |
| Clients | 4 |
| Shards | 3 |
| Replicas | 0 for 1-node, 1 for 3-node |
| Query mix | `write=15,lexical=15,ranking=15,facet=15,sort_filter=10,vector=15,hybrid=10,refresh=5` |

All scenarios completed with `0` errors.

## Throughput Summary

| Topology | Steelsearch ops/s | OpenSearch ops/s | Steelsearch/OpenSearch |
| --- | ---: | ---: | ---: |
| 1-node | 102.44 | 151.26 | 0.677x |
| 3-node | 100.81 | 57.67 | 1.748x |

Interpretation:

1. Single-node throughput is not improved versus OpenSearch. Steelsearch achieved about 67.7 percent of OpenSearch throughput.
2. Three-node throughput is improved versus OpenSearch. Steelsearch achieved about 174.8 percent of OpenSearch throughput.

## Single-node Latency Comparison

| Operation | Steelsearch p50 | OpenSearch p50 | Steelsearch p95 | OpenSearch p95 | Steelsearch p99 | OpenSearch p99 | Steelsearch mean | OpenSearch mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| facet | 39.86 ms | 21.96 ms | 48.93 ms | 54.95 ms | 52.08 ms | 86.05 ms | 40.56 ms | 26.13 ms |
| hybrid | 37.31 ms | 23.65 ms | 45.24 ms | 55.31 ms | 48.42 ms | 82.76 ms | 38.10 ms | 28.10 ms |
| lexical | 36.99 ms | 14.12 ms | 44.74 ms | 34.54 ms | 49.99 ms | 50.00 ms | 37.49 ms | 16.78 ms |
| ranking | 37.65 ms | 18.69 ms | 45.58 ms | 45.66 ms | 46.77 ms | 92.25 ms | 37.77 ms | 23.21 ms |
| refresh | 34.36 ms | 68.19 ms | 41.72 ms | 216.17 ms | 44.24 ms | 363.80 ms | 34.84 ms | 92.44 ms |
| sort_filter | 36.08 ms | 18.86 ms | 45.97 ms | 42.90 ms | 48.44 ms | 50.42 ms | 37.32 ms | 21.64 ms |
| vector | 41.29 ms | 23.99 ms | 49.68 ms | 54.85 ms | 52.02 ms | 78.14 ms | 41.73 ms | 27.59 ms |
| write | 39.50 ms | 15.82 ms | 46.24 ms | 32.80 ms | 47.72 ms | 42.10 ms | 39.40 ms | 17.31 ms |

### Single-node areas not improved vs OpenSearch

| Area | Evidence |
| --- | --- |
| Overall throughput | Steelsearch `102.44 ops/s` vs OpenSearch `151.26 ops/s`, ratio `0.677x` |
| Facet median/mean latency | p50 `1.815x` slower, mean `1.552x` slower |
| Hybrid median/mean latency | p50 `1.578x` slower, mean `1.356x` slower |
| Lexical p50/p95/mean latency | p50 `2.620x` slower, p95 `1.295x` slower, mean `2.234x` slower |
| Ranking median/mean latency | p50 `2.014x` slower, mean `1.627x` slower |
| Sort/filter p50/p95/mean latency | p50 `1.913x` slower, p95 `1.072x` slower, mean `1.725x` slower |
| Vector median/mean latency | p50 `1.722x` slower, mean `1.512x` slower |
| Write p50/p95/p99/mean latency | p50 `2.498x` slower, p95 `1.410x` slower, p99 `1.134x` slower, mean `2.277x` slower |

Single-node positive areas:

1. Refresh latency is substantially better than OpenSearch across p50/p95/p99/mean.
2. Tail latency for `facet`, `hybrid`, `ranking`, `sort_filter`, and `vector` is competitive or better at p99.
3. The main single-node weakness is median/mean latency and aggregate throughput, not the worst tail for most search operations.

## Three-node Latency Comparison

| Operation | Steelsearch p50 | OpenSearch p50 | Steelsearch p95 | OpenSearch p95 | Steelsearch p99 | OpenSearch p99 | Steelsearch mean | OpenSearch mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| facet | 40.82 ms | 56.27 ms | 50.52 ms | 159.93 ms | 54.92 ms | 272.61 ms | 40.97 ms | 71.74 ms |
| hybrid | 37.96 ms | 66.43 ms | 47.68 ms | 118.61 ms | 64.07 ms | 181.43 ms | 39.33 ms | 72.90 ms |
| lexical | 36.80 ms | 46.15 ms | 44.57 ms | 97.80 ms | 54.90 ms | 163.88 ms | 37.32 ms | 50.41 ms |
| ranking | 37.93 ms | 58.03 ms | 44.90 ms | 126.36 ms | 59.77 ms | 193.69 ms | 38.40 ms | 67.91 ms |
| refresh | 34.88 ms | 148.82 ms | 43.41 ms | 363.35 ms | 46.33 ms | 421.46 ms | 35.30 ms | 161.60 ms |
| sort_filter | 37.27 ms | 61.34 ms | 47.44 ms | 159.72 ms | 53.37 ms | 194.40 ms | 38.34 ms | 72.60 ms |
| vector | 41.34 ms | 61.53 ms | 51.64 ms | 151.99 ms | 62.58 ms | 237.62 ms | 42.17 ms | 73.34 ms |
| write | 40.31 ms | 43.14 ms | 50.99 ms | 100.33 ms | 63.85 ms | 120.84 ms | 40.77 ms | 49.56 ms |

### Three-node areas not improved vs OpenSearch

No slower metrics were recorded in this run for the measured three-node workload. Steelsearch beat OpenSearch on throughput, p50, p95, p99, and mean latency for every measured operation.

## Deterministic Native Baseline

Command:

```bash
cargo bench -p os-engine-tantivy --bench deterministic_baselines
```

Result: passed, status `0`.

| Benchmark | Operations | ns/op |
| --- | ---: | ---: |
| index | 128 | 4,400 |
| bulk | 128 | 2,415 |
| refresh | 128 | 85,764 |
| lexical_search | 32 | 95,828 |
| aggregation | 32 | 321,735 |
| exact_vector_search | 32 | 104,787 |
| hnsw_vector_search | 32 | 1,843,079 |
| hybrid_search | 32 | 159,822 |

Interpretation:

1. Internal lexical and hybrid native paths are sub-millisecond in the in-process deterministic bench.
2. HNSW vector search is materially slower than exact vector search in this tiny deterministic fixture, so it should not be used as proof of HNSW advantage at small corpus sizes.
3. The HTTP benchmark includes server/runtime/network/API overhead, so it should be used for OpenSearch comparison. The deterministic bench is useful for tracking native engine regressions.

## Limitations

This is stronger than the previous 5-second smoke run, but still not a full release-grade performance study.

Current limitations:

1. Duration is 10 seconds per scenario, not a long soak.
2. Corpus size is 1000 documents, not production scale.
3. Each scenario was run once; variance and confidence intervals were not measured.
4. Resource fields are still mostly unavailable in the generated benchmark output: RSS, operation-log size, disk IO, CPU, and detailed cache metrics need stronger probes.
5. Route evidence is validated separately by native-readiness artifacts, but per-request route/fallback counters are not yet embedded directly into the benchmark matrix output.
6. The three-node comparison may be influenced by local Docker/runtime overhead and should be repeated at larger scale before claiming broad cluster superiority.

## Recommended Follow-up

1. Repeat the matrix with at least 3 runs per scenario and summarize median plus variance.
2. Run longer jobs: 60 seconds minimum for CI-style performance smoke, 5-15 minutes for release confidence, and separate soak tests for operations readiness.
3. Increase corpus scale to at least 100k documents, then 1M+ for release characterization.
4. Add process/container resource probes for RSS, CPU, disk IO, operation-log growth, and vector cache pressure.
5. Add benchmark route counters so each benchmark operation records native route, fallback count, hit materialization count, and document scan count.
6. Investigate single-node median and mean latency for lexical, write, vector, sort/filter, and ranking workloads, because those are the clearest OpenSearch-relative gaps.

## Bottom Line

The current native implementation is performance-competitive in the refreshed benchmark, but the result is topology-dependent.

1. Three-node benchmark: Steelsearch is faster than OpenSearch across all measured operations and aggregate throughput.
2. Single-node benchmark: Steelsearch is slower than OpenSearch in aggregate throughput and several median/mean latency metrics, especially lexical, write, vector, sort/filter, and ranking.
3. Refresh latency is consistently better for Steelsearch.
4. A production performance claim should wait for longer, repeated, resource-instrumented runs at larger corpus sizes.
