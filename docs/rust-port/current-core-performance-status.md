# Current Core Performance Status

This file is generated from the latest completed, execution-verified repeated non-plugin benchmark.

- Ratio `1.000x` means equal performance. Higher is faster for every row.
- Throughput ratio = candidate/reference. Latency ratio = reference/candidate.
- Each cell is the two-run range; the lower endpoint is the conservative value.
- `took` is excluded. This is not a release approval or implementation-acceptance record.
- Source: `target/v070-core-gate-20260914/result.json`.
- Benchmark plan: 2026-09-14T15:27:54.344769+00:00; candidate SHA-256: `40830af495aadde1b922acd01ec2cb19a6ce0a9584c30b868a43e0982e807454`.
- Fixed v0.6.0 gate: 26/44 measured values have a two-run lower ratio below 0.950x.

## At A Glance

Each value is the conservative lowest ratio. `1.000x` is equal; higher is faster.
Scenario rows use the worst of mean, p95, and p99 across both repetitions.

### Single Node

| Scenario | vs v0.6.0 | vs OpenSearch |
| --- | ---: | ---: |
| throughput | 1.005x | 2.727x |
| write latency | 0.817x | 3.569x |
| lexical latency | 0.911x | 2.101x |
| ranking latency | 0.989x | 2.019x |
| facet latency | 1.307x | 2.211x |
| sort_filter latency | 0.912x | 2.475x |
| nested latency | 0.968x | 1.669x |
| refresh latency | 0.948x | 6.585x |

### 3 Nodes

| Scenario | vs v0.6.0 | vs OpenSearch |
| --- | ---: | ---: |
| throughput | 0.882x | 7.156x |
| write latency | 0.822x | 8.848x |
| lexical latency | 0.846x | 6.170x |
| ranking latency | 0.791x | 5.635x |
| facet latency | 0.936x | 6.224x |
| sort_filter latency | 0.858x | 8.223x |
| nested latency | 0.820x | 5.723x |
| refresh latency | 0.698x | 11.238x |

<details>
<summary>Detailed ranges: mean / p95 / p99</summary>

## Detailed Measurements

Rows are `mean / p95 / p99` performance ratios, all with the same higher-is-faster direction.

| Topology | Scenario | v0.6.0 ratio (mean / p95 / p99) | OpenSearch ratio (mean / p95 / p99) |
| --- | --- | ---: | ---: |
| single-node | write | 0.842-0.876x / 0.822-0.875x / 0.817-0.876x | 4.091-4.126x / 3.569-3.719x / 4.452-4.872x |
| single-node | lexical | 0.911-0.941x / 0.978-1.045x / 1.039-1.053x | 2.246-2.259x / 2.101-2.139x / 2.188-2.315x |
| single-node | ranking | 0.989-1.001x / 1.071-1.102x / 1.095-1.122x | 2.019-2.032x / 2.096-2.204x / 2.518-2.716x |
| single-node | facet | 1.307-1.363x / 1.408-1.485x / 1.329-1.395x | 2.211-2.269x / 2.281-2.290x / 2.622-2.833x |
| single-node | sort_filter | 0.912-0.934x / 0.971-0.996x / 1.027-1.029x | 2.525-2.532x / 2.475-2.538x / 2.569-2.672x |
| single-node | nested | 0.968-0.989x / 1.001-1.038x / 1.071-1.101x | 1.669-1.712x / 1.685-1.750x / 1.930-2.171x |
| single-node | refresh | 0.954-1.001x / 1.064-1.107x / 0.948-1.000x | 6.585-7.056x / 8.153-8.463x / 7.659-8.365x |
| three-node | write | 0.854-0.899x / 0.827-0.879x / 0.822-0.899x | 8.848-9.973x / 9.741-11.372x / 12.707-13.952x |
| three-node | lexical | 0.895-0.935x / 0.899-0.914x / 0.846-0.943x | 6.170-6.847x / 7.620-8.114x / 7.539-9.040x |
| three-node | ranking | 0.808-0.835x / 0.826-0.860x / 0.791-0.843x | 5.635-6.179x / 7.498-8.216x / 8.347-9.897x |
| three-node | facet | 0.986-1.023x / 1.030-1.088x / 0.936-0.939x | 6.224-6.702x / 8.275-8.691x / 7.966-8.499x |
| three-node | sort_filter | 0.905-0.943x / 0.878-0.909x / 0.858-0.910x | 8.223-9.027x / 10.227-10.299x / 10.663-11.328x |
| three-node | nested | 0.911-0.946x / 0.888-0.922x / 0.820-0.871x | 5.723-6.139x / 7.405-7.474x / 8.357-10.013x |
| three-node | refresh | 0.816-0.869x / 0.796-0.887x / 0.698-0.836x | 11.409-12.397x / 11.238-12.569x / 12.073-12.979x |

</details>
