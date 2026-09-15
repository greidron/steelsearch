# SteelSearch v0.7.2

## Changes

Release evidence now requires native k-NN and hybrid search scenarios alongside the existing core workload. The release bundle records actual candidate, previous-release, and OpenSearch executable identities.

## Compatibility

The supported profile is `core-native-knn`: core `knn_vector` indexing, k-NN search, filtered k-NN, and lexical+k-NN bool search are covered. OpenSearch k-NN/ML plugin management and operational APIs remain outside the profile. The candidate passed the preserved non-plugin HTTP fixture 1,180/1,180 and the OpenSearch k-NN smoke comparison.

## Validation

The candidate was built from commit `295198b3c70b83aeb565a2dfff23c6e527b99b4a` in a separate target directory. The performance evidence consists of fresh 60-second 1-node and 3-node measurements for v0.7.2, v0.7.1, and OpenSearch 2.19.0, with no request errors.

## Known Limitations

The fixed v0.6.0 cumulative performance gate remains outside its per-scenario 5% budget in 20 of 44 historical comparisons; the prior approved scoped exception remains in force and is not reset by this release. The k-NN smoke proves core query shape and ranking for deterministic small vectors; full approximate-engine and plugin-management compatibility remains separately scoped.

<!-- release-performance:start -->
## Performance

- Current: `v0.7.2`; previous published release: `v0.7.1`.
- Reference: OpenSearch `2.19.0`; support: `core-native-knn`.
- Environment: Local ARM64 Linux host; Steelsearch and OpenSearch run as isolated 1-node or colocated 3-node development processes with 512 MiB OpenSearch heap per node.
- Runtime and durability settings: Development durability; security disabled for local benchmark services; 5,000 documents; deferred native writes replay on refresh; 3 primary shards; 0 replicas on one node and 1 on three nodes.
- Limits: Fresh 60-second single samples with four clients and seed 13; OpenSearch includes opensearch-knn for vector/hybrid requests. The fixed v0.6.0 cumulative gate remains an approved scoped exception with 20 of 44 historical comparisons over budget; this release does not reset or waive it.
- Workload: 5000 documents, 4 clients, 60.0 seconds per topology, 3 shards; replicas: 0 on one node, 1 on three nodes; seed 13.
- Operation weights: write=15, lexical=15, ranking=15, facet=15, sort_filter=10, nested=10, refresh=5, vector=15, hybrid=10.
- k-NN: `384` dimensions; vector and hybrid requests are included.
- Current binary SHA-256: `7ab03a3d3ab0fc664262961facc870438e00aaf1a710dd0831ea56b26aea5cbc`.
- Previous binary SHA-256: `898802f92db7e43e21b23c08450628175735e236774d29fb5a7ec90bd167d0d1`.
- Raw reports and release metadata: attached `performance-evidence.zip`.

### Throughput

Higher is better. Change = (current / previous - 1) * 100; ratio = current / OpenSearch.

| Topology | Previous ops/s | Current ops/s | Change | OpenSearch ops/s | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| single-node | 428.11 | 427.77 | -0.08% | 243.35 | 1.76x |
| three-node | 801.52 | 790.70 | -1.35% | 98.01 | 8.07x |

### Scenario Latency

Mean milliseconds, lower is better. Positive change is a regression; speedup = OpenSearch / current. Throughput is not per-operation latency.

| Topology | Scenario | Previous ms | Current ms | Change | OpenSearch ms | Speedup | Current p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single-node | write | 3.33 | 3.42 | +2.63% | 14.82 | 4.33x | 6.13 |
| single-node | lexical | 5.74 | 5.97 | +4.14% | 10.51 | 1.76x | 8.79 |
| single-node | ranking | 7.57 | 7.62 | +0.66% | 13.54 | 1.78x | 11.14 |
| single-node | facet | 6.92 | 6.51 | -5.93% | 13.15 | 2.02x | 11.00 |
| single-node | sort_filter | 6.49 | 6.36 | -1.90% | 13.49 | 2.12x | 9.97 |
| single-node | nested | 7.22 | 7.21 | -0.16% | 11.73 | 1.63x | 11.52 |
| single-node | refresh | 33.90 | 32.98 | -2.73% | 62.21 | 1.89x | 114.03 |
| single-node | vector | 17.97 | 17.67 | -1.65% | 19.30 | 1.09x | 92.03 |
| single-node | hybrid | 10.63 | 11.77 | +10.77% | 18.10 | 1.54x | 26.87 |
| three-node | write | 3.40 | 3.47 | +2.30% | 34.12 | 9.82x | 6.44 |
| three-node | lexical | 3.80 | 3.82 | +0.35% | 26.27 | 6.88x | 7.11 |
| three-node | ranking | 5.26 | 5.23 | -0.55% | 34.59 | 6.61x | 8.81 |
| three-node | facet | 4.58 | 4.69 | +2.40% | 34.19 | 7.29x | 8.20 |
| three-node | sort_filter | 4.16 | 4.26 | +2.36% | 39.66 | 9.30x | 7.69 |
| three-node | nested | 4.53 | 4.52 | -0.28% | 29.04 | 6.43x | 8.03 |
| three-node | refresh | 9.96 | 10.50 | +5.46% | 147.63 | 14.06x | 23.59 |
| three-node | vector | 6.06 | 6.13 | +1.14% | 46.60 | 7.60x | 9.46 |
| three-node | hybrid | 6.51 | 6.55 | +0.57% | 43.19 | 6.59x | 13.66 |

<!-- release-performance:end -->
