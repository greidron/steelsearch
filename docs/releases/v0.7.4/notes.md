# SteelSearch v0.7.4

## Changes

This release retains only the verified implementation. Rejected refresh, merge-worker, and tokenizer performance experiments are not included. Diagnostic-only native commit phase instrumentation is available behind its diagnostic feature and does not alter the normal release execution path.

## Compatibility

The preserved non-plugin HTTP compatibility fixture passed 1,198/1,198 cases with no failures or skips using the release candidate executable. The supported profile remains `core-native-knn`: native vector indexing, k-NN search, filtered k-NN, and lexical plus k-NN bool search are covered; k-NN and ML plugin management remain outside scope.

## Validation

The candidate was independently built with `standalone-runtime`. Fresh 60-second matrices cover both node topologies, all nine operations, v0.7.3 as the immediate predecessor, and OpenSearch 2.19.0 with no request errors. The release table is generated directly from the three captured matrices.

## Known Limitations

The fixed v0.6.0 cumulative 5% performance gate remains outside budget under the prior scoped exception and is not reset by this release. Native Tantivy refresh commit preparation remains the measured write and refresh bottleneck; this release makes no unsupported performance-improvement claim.

<!-- release-performance:start -->
## Performance

- Current: `v0.7.4`; previous published release: `v0.7.3`.
- Reference: OpenSearch `2.19.0`; support: `core-native-knn`.
- Environment: Local ARM64 Linux host; Steelsearch and OpenSearch run as isolated 1-node or colocated 3-node development processes with 512 MiB OpenSearch heap per node.
- Runtime and durability settings: Development durability; security disabled for local benchmark services; 5,000 documents; deferred native writes replay on refresh; 3 primary shards; 0 replicas on one node and 1 on three nodes.
- Limits: Fresh 60-second single samples with four clients and seed 13; OpenSearch includes opensearch-knn for vector and hybrid requests. The fixed v0.6.0 cumulative gate remains a prior scoped exception and is not reset or waived by this release; rejected performance experiments are excluded.
- Workload: 5000 documents, 4 clients, 60.0 seconds per topology, 3 shards; replicas: 0 on one node, 1 on three nodes; seed 13.
- Operation weights: write=15, lexical=15, ranking=15, facet=15, sort_filter=10, nested=10, refresh=5, vector=15, hybrid=10.
- k-NN: `384` dimensions; vector and hybrid requests are included.
- Current binary SHA-256: `add5d84dd458714b7f597cdeb9b3f9db92134e49007900f6fd01255888e52bec`.
- Previous binary SHA-256: `535a2c0786ea228562765d6ea3b6e8db2d57472ea36ed80fd39161a0376854a5`.
- Raw reports and release metadata: attached `performance-evidence.zip`.

### Throughput

Higher is better. Change = (current / previous - 1) * 100; ratio = current / OpenSearch.

| Topology | Previous ops/s | Current ops/s | Change | OpenSearch ops/s | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| single-node | 424.68 | 442.76 | +4.26% | 231.62 | 1.91x |
| three-node | 774.49 | 793.23 | +2.42% | 97.63 | 8.12x |

### Scenario Latency

Mean milliseconds, lower is better. Positive change is a regression; speedup = OpenSearch / current. Throughput is not per-operation latency.

| Topology | Scenario | Previous ms | Current ms | Change | OpenSearch ms | Speedup | Current p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single-node | write | 3.51 | 3.45 | -1.95% | 15.90 | 4.62x | 6.38 |
| single-node | lexical | 5.78 | 5.84 | +1.03% | 11.08 | 1.90x | 9.24 |
| single-node | ranking | 7.56 | 7.34 | -2.86% | 14.62 | 1.99x | 11.16 |
| single-node | facet | 7.19 | 6.88 | -4.29% | 13.68 | 1.99x | 11.81 |
| single-node | sort_filter | 6.66 | 6.56 | -1.53% | 14.27 | 2.18x | 10.84 |
| single-node | nested | 7.19 | 7.42 | +3.16% | 12.29 | 1.66x | 12.10 |
| single-node | refresh | 32.24 | 30.66 | -4.88% | 62.59 | 2.04x | 105.73 |
| single-node | vector | 17.88 | 16.51 | -7.66% | 20.46 | 1.24x | 86.66 |
| single-node | hybrid | 11.57 | 10.79 | -6.74% | 18.88 | 1.75x | 26.17 |
| three-node | write | 3.51 | 3.45 | -1.48% | 35.31 | 10.22x | 6.32 |
| three-node | lexical | 3.89 | 3.82 | -1.79% | 26.60 | 6.97x | 7.06 |
| three-node | ranking | 5.36 | 5.25 | -2.16% | 35.69 | 6.80x | 8.99 |
| three-node | facet | 4.76 | 4.57 | -3.98% | 35.16 | 7.69x | 7.94 |
| three-node | sort_filter | 4.29 | 4.24 | -1.07% | 39.51 | 9.32x | 7.56 |
| three-node | nested | 4.56 | 4.58 | +0.51% | 26.57 | 5.79x | 8.14 |
| three-node | refresh | 10.32 | 10.04 | -2.71% | 147.17 | 14.66x | 22.94 |
| three-node | vector | 6.38 | 6.23 | -2.29% | 46.03 | 7.38x | 9.63 |
| three-node | hybrid | 6.93 | 6.59 | -4.83% | 42.44 | 6.44x | 13.62 |

<!-- release-performance:end -->
