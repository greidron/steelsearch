# Current Core Performance Status

This file is generated from the latest completed, execution-verified repeated non-plugin benchmark.

- Ratio `1.000x` means equal performance. Higher is faster for every row.
- Throughput ratio = candidate/reference. Latency ratio = reference/candidate.
- Each cell is the two-run range; the lower endpoint is the conservative value.
- `took` is excluded. This is not a release approval or implementation-acceptance record.
- Source: `target/core-replacement-c06/native-multi-sort-inline-key-repeated-full-r66-20260913/result.json`.
- Benchmark plan: 2026-09-13T09:44:16.128468+00:00; candidate SHA-256: `3583452c5f3c8688d13ba22dcecde63aa689303600049523af736a4da098c225`.
- Fixed v0.6.0 gate: 27/44 measured values have a two-run lower ratio below 0.950x.

## At A Glance

Each value is the conservative lowest ratio. `1.000x` is equal; higher is faster.
Scenario rows use the worst of mean, p95, and p99 across both repetitions.

### Single Node

| Scenario | vs v0.6.0 | vs OpenSearch |
| --- | ---: | ---: |
| throughput | 0.770x | 2.113x |
| write latency | 0.887x | 3.966x |
| lexical latency | 0.949x | 2.073x |
| ranking latency | 1.023x | 2.107x |
| facet latency | 0.824x | 1.286x |
| sort_filter latency | 0.223x | 0.574x |
| nested latency | 1.008x | 1.657x |
| refresh latency | 0.986x | 6.810x |

### 3 Nodes

| Scenario | vs v0.6.0 | vs OpenSearch |
| --- | ---: | ---: |
| throughput | 0.844x | 7.153x |
| write latency | 0.867x | 9.472x |
| lexical latency | 0.932x | 6.863x |
| ranking latency | 0.859x | 6.166x |
| facet latency | 0.824x | 5.496x |
| sort_filter latency | 0.363x | 3.956x |
| nested latency | 0.938x | 6.031x |
| refresh latency | 0.976x | 14.366x |

<details>
<summary>Detailed ranges: mean / p95 / p99</summary>

## Detailed Measurements

Rows are `mean / p95 / p99` performance ratios, all with the same higher-is-faster direction.

| Topology | Scenario | v0.6.0 ratio (mean / p95 / p99) | OpenSearch ratio (mean / p95 / p99) |
| --- | --- | ---: | ---: |
| single-node | write | 0.919-0.936x / 0.887-0.891x / 0.893-0.904x | 4.505-4.710x / 3.966-4.110x / 5.396-6.211x |
| single-node | lexical | 0.949-0.971x / 0.959-1.027x / 0.990-1.015x | 2.399-2.435x / 2.073-2.190x / 2.258-2.358x |
| single-node | ranking | 1.029-1.041x / 1.070-1.099x / 1.023-1.079x | 2.109-2.126x / 2.107-2.131x / 2.380-2.497x |
| single-node | facet | 0.824-0.841x / 0.829-0.853x / 0.825-0.886x | 1.397-1.421x / 1.286-1.332x / 1.536-1.563x |
| single-node | sort_filter | 0.296-0.315x / 0.223-0.233x / 0.273-0.291x | 0.826-0.877x / 0.574-0.590x / 0.708-0.736x |
| single-node | nested | 1.008-1.034x / 1.009-1.062x / 1.030-1.107x | 1.765-1.800x / 1.657-1.815x / 1.927-1.949x |
| single-node | refresh | 0.986-1.020x / 1.061-1.107x / 0.989-1.010x | 6.810-7.140x / 7.835-8.534x / 8.378-9.189x |
| three-node | write | 0.890-0.904x / 0.867-0.888x / 0.886-0.903x | 9.472-10.131x / 10.648-11.371x / 13.312-16.584x |
| three-node | lexical | 0.932-0.943x / 0.933-0.956x / 0.995-1.040x | 6.863-7.069x / 8.608-8.670x / 10.857-11.032x |
| three-node | ranking | 0.859-0.866x / 0.884-0.900x / 0.923-0.925x | 6.166-6.508x / 8.190-8.853x / 9.800-11.246x |
| three-node | facet | 0.837-0.840x / 0.824-0.828x / 0.833-0.866x | 5.496-5.594x / 6.216-6.500x / 6.966-8.137x |
| three-node | sort_filter | 0.565-0.570x / 0.363-0.382x / 0.426-0.443x | 5.200-5.679x / 3.956-4.855x / 4.632-6.004x |
| three-node | nested | 0.953-0.974x / 0.938-0.966x / 0.987-1.002x | 6.031-6.099x / 6.989-7.792x / 9.363-10.158x |
| three-node | refresh | 1.004-1.031x / 1.017-1.041x / 0.976-0.999x | 15.334-15.463x / 14.366-14.627x / 15.445-16.894x |

</details>
