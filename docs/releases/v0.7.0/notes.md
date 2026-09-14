# SteelSearch v0.7.0

## Changes

- Use Tantivy native minimum-should-match query composition for the proven `minimum_should_match: 1` path.
- Tighten native phrase/ranking authority checks across refresh, deletion, shard distribution, mapped values, and text option compatibility.
- Preserve scoped OpenSearch comparison semantics for execution-dependent response metadata while retaining document and search-result contracts.

## Compatibility

The supported profile remains **core-no-plugins**. k-NN and ML Commons plugin
APIs are excluded rather than treated as passing compatibility cases. The full
non-plugin HTTP comparison completed with 1,180 passes and zero failures or
skips against OpenSearch.

This release does not claim complete OpenSearch API or scoring equivalence,
production replacement readiness, or mixed-cluster support.

## Validation

The candidate executable `40830af495aadde1b922acd01ec2cb19a6ce0a9584c30b868a43e0982e807454`
passed the focused native ranking audit suite (21 tests) and the preserved
non-plugin HTTP fixture suite. The performance evidence below was captured
with distinct v0.6.0 and candidate binaries, together with pinned OpenSearch
2.19.0, under the same matrix configuration.

The repeated fixed v0.6.0 cumulative gate completed all six runs and verified
its inputs, but did not pass numerically. This evidence is recorded without
claiming normal release-gate acceptance.

## Known Limitations

- The fixed v0.6.0 5% cumulative performance budget is exceeded in both repetitions, notably for three-node throughput and write latency. This must be addressed before claiming the implementation performance goal is complete.
- OpenSearch plugin APIs, including k-NN and ML Commons, remain unsupported and were excluded from compatibility validation.
- These development benchmark ratios do not establish production-equivalent performance because durability, resource isolation, and deployment differ from OpenSearch.
- Broader production readiness, full API/scoring equivalence, mixed-cluster behavior, and operational cutover certification remain outside this release evidence.

<!-- release-performance:start -->
## Performance

- Current: `v0.7.0`; previous published release: `v0.6.0`.
- Reference: OpenSearch `2.19.0`; support: `core-no-plugins`.
- Environment: Ubuntu 24.04.3 LTS ARM64 host with 3 Neoverse-N1 CPUs and 17 GiB RAM; SteelSearch native processes and Docker OpenSearch with a 512 MiB JVM heap per node, without Docker CPU or memory quotas
- Runtime and durability settings: All SteelSearch runs used the benchmark runner development persistence settings with shared runtime persistence and per-request synchronization disabled, deferred shard persistence enabled, and native writes deferred until refresh; OpenSearch used its pinned 2.19.0 image with security/demo setup disabled and explicit refresh workload
- Limits: Measured 2026-09-14 with two 60-second repetitions per engine/topology, 5000 generated documents and identical workload settings; development durability and deployment differ from OpenSearch, so ratios are not production-equivalent speed claims. The v0.6.0 fixed cumulative 5% gate failed in both repetitions, including three-node throughput and write latency; this bundle records the regression and does not reset or waive that gate.
- Workload: 5000 documents, 4 clients, 60.0 seconds per topology, 3 shards; replicas: 0 on one node, 1 on three nodes; seed 13.
- Operation weights: write=15, lexical=15, ranking=15, facet=15, sort_filter=10, nested=10, refresh=5.
- Synthetic source embedding array: 384 numbers per document; no k-NN index or requests.
- Current binary SHA-256: `40830af495aadde1b922acd01ec2cb19a6ce0a9584c30b868a43e0982e807454`.
- Previous binary SHA-256: `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`.
- Raw reports and release metadata: attached `performance-evidence.zip`.

### Throughput

Higher is better. Change = (current / previous - 1) * 100; ratio = current / OpenSearch.

| Topology | Previous ops/s | Current ops/s | Change | OpenSearch ops/s | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| single-node | 724.17 | 746.75 | +3.12% | 273.83 | 2.73x |
| three-node | 876.70 | 821.50 | -6.30% | 114.80 | 7.16x |

### Scenario Latency

Mean milliseconds, lower is better. Positive change is a regression; speedup = OpenSearch / current. Throughput is not per-operation latency.

| Topology | Scenario | Previous ms | Current ms | Change | OpenSearch ms | Speedup | Current p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single-node | write | 3.05 | 3.41 | +11.99% | 13.96 | 4.09x | 6.42 |
| single-node | lexical | 4.24 | 4.50 | +6.24% | 10.11 | 2.25x | 9.15 |
| single-node | ranking | 6.50 | 6.48 | -0.33% | 13.09 | 2.02x | 11.58 |
| single-node | facet | 7.46 | 5.62 | -24.75% | 12.42 | 2.21x | 10.76 |
| single-node | sort_filter | 4.78 | 5.02 | +5.00% | 12.66 | 2.52x | 9.58 |
| single-node | nested | 6.37 | 6.55 | +2.86% | 11.22 | 1.71x | 12.14 |
| single-node | refresh | 7.73 | 7.75 | +0.21% | 51.01 | 6.59x | 13.99 |
| three-node | write | 3.16 | 3.48 | +9.82% | 30.75 | 8.85x | 6.63 |
| three-node | lexical | 3.70 | 3.93 | +6.19% | 24.27 | 6.17x | 7.50 |
| three-node | ranking | 4.72 | 5.55 | +17.51% | 31.27 | 5.63x | 9.73 |
| three-node | facet | 5.17 | 5.00 | -3.14% | 31.15 | 6.22x | 9.18 |
| three-node | sort_filter | 4.16 | 4.39 | +5.42% | 36.09 | 8.22x | 8.19 |
| three-node | nested | 4.57 | 4.78 | +4.49% | 27.33 | 5.72x | 8.92 |
| three-node | refresh | 9.56 | 10.28 | +7.49% | 117.26 | 11.41x | 21.68 |

<!-- release-performance:end -->
