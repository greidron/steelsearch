# SteelSearch v0.7.3

## Changes

This release retains the verified native BM25 statistics path and parser-equivalent bounded ASCII `match` construction, along with the accumulated OpenSearch response compatibility repairs. The experimental small Tantivy writer batch was removed: its focused measurements improved slightly, but its complete fixed-v0.6.0 gate regressed required write/refresh metrics.

## Compatibility

The preserved non-plugin HTTP compatibility fixture passed 1,198/1,198 cases, with no failures or skips, using the release candidate executable. The supported profile remains `core-native-knn`: native vector indexing, k-NN search, filtered k-NN, and lexical+k-NN bool search are covered; k-NN/ML plugin management remains outside scope.

## Validation

The candidate was independently built with `standalone-runtime`. The immediately previous published v0.7.2 binary was recovered from its release asset and its SHA-256 matched the v0.7.2 evidence bundle. Fresh 60-second matrices cover both node topologies, all nine operations, and OpenSearch 2.19.0 with no request errors.

## Known Limitations

The fixed v0.6.0 cumulative 5% gate remains outside budget for the retained historical candidate path; the prior scoped exception remains recorded and is not reset by this release. This release does not claim complete OpenSearch operational or plugin API equivalence.

<!-- release-performance:start -->
## Performance

- Current: `v0.7.3`; previous published release: `v0.7.2`.
- Reference: OpenSearch `2.19.0`; support: `core-native-knn`.
- Environment: Local ARM64 Linux host; Steelsearch and OpenSearch run as isolated 1-node or colocated 3-node development processes with 512 MiB OpenSearch heap per node.
- Runtime and durability settings: Development durability; security disabled for local benchmark services; 5,000 documents; deferred native writes replay on refresh; 3 primary shards; 0 replicas on one node and 1 on three nodes.
- Limits: Fresh 60-second single samples with four clients and seed 13; OpenSearch includes opensearch-knn for vector/hybrid requests. The fixed v0.6.0 cumulative gate remains a prior scoped exception and is not reset or waived by this release. The native small writer-batch experiment was rejected after its complete fixed-baseline gate failed.
- Workload: 5000 documents, 4 clients, 60.0 seconds per topology, 3 shards; replicas: 0 on one node, 1 on three nodes; seed 13.
- Operation weights: write=15, lexical=15, ranking=15, facet=15, sort_filter=10, nested=10, refresh=5, vector=15, hybrid=10.
- k-NN: `384` dimensions; vector and hybrid requests are included.
- Current binary SHA-256: `535a2c0786ea228562765d6ea3b6e8db2d57472ea36ed80fd39161a0376854a5`.
- Previous binary SHA-256: `7ab03a3d3ab0fc664262961facc870438e00aaf1a710dd0831ea56b26aea5cbc`.
- Raw reports and release metadata: attached `performance-evidence.zip`.

### Throughput

Higher is better. Change = (current / previous - 1) * 100; ratio = current / OpenSearch.

| Topology | Previous ops/s | Current ops/s | Change | OpenSearch ops/s | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| single-node | 437.66 | 436.46 | -0.27% | 239.66 | 1.82x |
| three-node | 749.75 | 760.75 | +1.47% | 90.34 | 8.42x |

### Scenario Latency

Mean milliseconds, lower is better. Positive change is a regression; speedup = OpenSearch / current. Throughput is not per-operation latency.

| Topology | Scenario | Previous ms | Current ms | Change | OpenSearch ms | Speedup | Current p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single-node | write | 3.50 | 3.48 | -0.55% | 15.73 | 4.52x | 6.48 |
| single-node | lexical | 5.76 | 5.39 | -6.37% | 10.95 | 2.03x | 9.01 |
| single-node | ranking | 7.40 | 7.52 | +1.60% | 13.69 | 1.82x | 11.87 |
| single-node | facet | 6.63 | 6.68 | +0.78% | 13.44 | 2.01x | 11.56 |
| single-node | sort_filter | 6.48 | 6.10 | -5.79% | 13.70 | 2.25x | 9.74 |
| single-node | nested | 7.47 | 7.69 | +3.00% | 11.57 | 1.50x | 13.95 |
| single-node | refresh | 30.88 | 31.79 | +2.95% | 60.77 | 1.91x | 105.74 |
| single-node | vector | 16.85 | 17.01 | +0.95% | 19.73 | 1.16x | 86.40 |
| single-node | hybrid | 11.68 | 11.75 | +0.55% | 18.02 | 1.53x | 26.93 |
| three-node | write | 3.62 | 3.52 | -2.55% | 37.88 | 10.75x | 6.74 |
| three-node | lexical | 3.94 | 3.92 | -0.58% | 29.68 | 7.57x | 7.45 |
| three-node | ranking | 5.54 | 5.42 | -2.25% | 36.94 | 6.82x | 9.34 |
| three-node | facet | 4.95 | 4.86 | -1.81% | 39.96 | 8.22x | 8.65 |
| three-node | sort_filter | 4.42 | 4.35 | -1.54% | 43.73 | 10.05x | 7.95 |
| three-node | nested | 4.65 | 4.60 | -1.11% | 30.47 | 6.62x | 8.44 |
| three-node | refresh | 11.76 | 11.48 | -2.41% | 146.37 | 12.75x | 34.12 |
| three-node | vector | 6.47 | 6.42 | -0.85% | 51.47 | 8.02x | 10.15 |
| three-node | hybrid | 6.94 | 6.92 | -0.20% | 45.96 | 6.64x | 14.57 |

<!-- release-performance:end -->
