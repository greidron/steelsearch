# SteelSearch v0.7.1

## Changes

- Allow admitted REST searches to proceed during an active refresh while retaining maintenance priority.
- Reduce the deferred native replay critical section by releasing the runtime document map before Tantivy replay.
- Add diagnostic-only refresh attribution for artifact execution, plan capture, publishing, and lock ownership.

## Compatibility

The supported profile remains **core-no-plugins**. k-NN and ML Commons plugin
APIs are excluded rather than treated as passing compatibility cases. The full
non-plugin HTTP comparison completed with 1,180 passes and zero failures or
skips against OpenSearch.

This release does not claim complete OpenSearch API or scoring equivalence,
production replacement readiness, or mixed-cluster support.

## Validation

The candidate executable `898802f92db7e43e21b23c08450628175735e236774d29fb5a7ec90bd167d0d1`
was built from a clean detached worktree and measured with a freshly rerun
v0.7.0 binary and pinned OpenSearch 2.19.0 under the same matrix configuration.

The fixed v0.6.0 cumulative gate remains outside its numeric budget. This is a
user-approved scoped release exception and does not claim normal release-gate
acceptance or reset the fixed baseline.

## Known Limitations

- The fixed v0.6.0 5% cumulative performance budget remains exceeded, notably for write, refresh, and three-node ranking latency. This must be addressed before claiming the implementation performance goal is complete.
- OpenSearch plugin APIs, including k-NN and ML Commons, remain unsupported and were excluded from compatibility validation.
- These development benchmark ratios do not establish production-equivalent performance because durability, resource isolation, and deployment differ from OpenSearch.
- Broader production readiness, full API/scoring equivalence, mixed-cluster behavior, and operational cutover certification remain outside this release evidence.

<!-- release-performance:start -->
## Performance

- Current: `v0.7.1`; previous published release: `v0.7.0`.
- Reference: OpenSearch `2.19.0`; support: `core-no-plugins`.
- Environment: Ubuntu 24.04.3 LTS ARM64 host with 3 Neoverse-N1 CPUs and 17 GiB RAM; SteelSearch native processes and Docker OpenSearch with a 512 MiB JVM heap per node, without Docker CPU or memory quotas
- Runtime and durability settings: All SteelSearch runs used the benchmark runner development persistence settings with shared runtime persistence and per-request synchronization disabled, deferred shard persistence enabled, and native writes deferred until refresh; OpenSearch used its pinned 2.19.0 image with security/demo setup disabled and explicit refresh workload
- Limits: Measured 2026-09-15 with one fresh 60-second matrix per engine/topology, 5000 generated documents and identical workload settings; development durability and deployment differ from OpenSearch, so ratios are not production-equivalent speed claims. The fixed v0.6.0 cumulative 5% gate remains failed; this user-approved v0.7.1 release records that scoped exception and does not reset or waive the gate.
- Workload: 5000 documents, 4 clients, 60.0 seconds per topology, 3 shards; replicas: 0 on one node, 1 on three nodes; seed 13.
- Operation weights: write=15, lexical=15, ranking=15, facet=15, sort_filter=10, nested=10, refresh=5.
- Synthetic source embedding array: 384 numbers per document; no k-NN index or requests.
- Current binary SHA-256: `898802f92db7e43e21b23c08450628175735e236774d29fb5a7ec90bd167d0d1`.
- Previous binary SHA-256: `40830af495aadde1b922acd01ec2cb19a6ce0a9584c30b868a43e0982e807454`.
- Raw reports and release metadata: attached `performance-evidence.zip`.

### Throughput

Higher is better. Change = (current / previous - 1) * 100; ratio = current / OpenSearch.

| Topology | Previous ops/s | Current ops/s | Change | OpenSearch ops/s | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| single-node | 767.90 | 792.65 | +3.22% | 270.02 | 2.94x |
| three-node | 866.37 | 867.97 | +0.18% | 115.40 | 7.52x |

### Scenario Latency

Mean milliseconds, lower is better. Positive change is a regression; speedup = OpenSearch / current. Throughput is not per-operation latency.

| Topology | Scenario | Previous ms | Current ms | Change | OpenSearch ms | Speedup | Current p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single-node | write | 3.30 | 3.30 | +0.01% | 14.09 | 4.27x | 6.11 |
| single-node | lexical | 4.34 | 3.85 | -11.44% | 10.35 | 2.69x | 7.11 |
| single-node | ranking | 6.43 | 6.04 | -6.08% | 13.22 | 2.19x | 10.17 |
| single-node | facet | 5.47 | 5.14 | -6.00% | 12.69 | 2.47x | 9.29 |
| single-node | sort_filter | 4.88 | 4.44 | -9.03% | 13.18 | 2.97x | 7.75 |
| single-node | nested | 6.43 | 6.14 | -4.43% | 11.51 | 1.87x | 11.33 |
| single-node | refresh | 7.19 | 9.46 | +31.55% | 50.69 | 5.36x | 18.26 |
| three-node | write | 3.32 | 3.35 | +0.84% | 29.22 | 8.73x | 6.18 |
| three-node | lexical | 3.83 | 3.75 | -2.11% | 24.71 | 6.59x | 7.05 |
| three-node | ranking | 5.35 | 5.37 | +0.36% | 31.80 | 5.92x | 9.17 |
| three-node | facet | 4.73 | 4.74 | +0.17% | 30.21 | 6.37x | 8.48 |
| three-node | sort_filter | 4.25 | 4.19 | -1.46% | 36.45 | 8.70x | 7.53 |
| three-node | nested | 4.63 | 4.55 | -1.74% | 26.15 | 5.75x | 8.10 |
| three-node | refresh | 8.79 | 9.00 | +2.35% | 120.66 | 13.41x | 18.00 |

<!-- release-performance:end -->
