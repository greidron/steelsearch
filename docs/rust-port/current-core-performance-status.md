# Current Core Performance Status

This file is generated from the latest completed, execution-verified repeated non-plugin benchmark.

- Ratio `1.000x` means equal performance. Higher is faster for every row.
- Throughput ratio = candidate/reference. Latency ratio = reference/candidate.
- Each cell is the two-run range; the lower endpoint is the conservative value.
- `took` is excluded. This is not a release approval or implementation-acceptance record.
- Source: `target/native-phrase-shard-authority-full-gate-rerun-20260914/result.json`.
- Benchmark plan: 2026-09-14T08:40:38.023900+00:00; candidate SHA-256: `b38f4c5d10bf1c4917b24957f38afc113f1e4f836e1ec96dd31687692cb25d9a`.
- Fixed v0.6.0 gate: 26/44 measured values have a two-run lower ratio below 0.950x.

## At A Glance

Each value is the conservative lowest ratio. `1.000x` is equal; higher is faster.
Scenario rows use the worst of mean, p95, and p99 across both repetitions.

### Single Node

| Scenario | vs v0.6.0 | vs OpenSearch |
| --- | ---: | ---: |
| throughput | 1.032x | 2.713x |
| write latency | 0.859x | 3.585x |
| lexical latency | 0.928x | 2.040x |
| ranking latency | 1.027x | 2.027x |
| facet latency | 1.357x | 2.074x |
| sort_filter latency | 0.923x | 2.411x |
| nested latency | 0.976x | 1.581x |
| refresh latency | 0.944x | 6.580x |

### 3 Nodes

| Scenario | vs v0.6.0 | vs OpenSearch |
| --- | ---: | ---: |
| throughput | 0.904x | 7.446x |
| write latency | 0.849x | 9.043x |
| lexical latency | 0.898x | 6.616x |
| ranking latency | 0.847x | 6.016x |
| facet latency | 0.944x | 6.413x |
| sort_filter latency | 0.889x | 8.225x |
| nested latency | 0.835x | 5.706x |
| refresh latency | 0.747x | 11.485x |

<details>
<summary>Detailed ranges: mean / p95 / p99</summary>

## Detailed Measurements

Rows are `mean / p95 / p99` performance ratios, all with the same higher-is-faster direction.

| Topology | Scenario | v0.6.0 ratio (mean / p95 / p99) | OpenSearch ratio (mean / p95 / p99) |
| --- | --- | ---: | ---: |
| single-node | write | 0.869-0.874x / 0.859-0.883x / 0.862-0.881x | 4.077-4.085x / 3.585-3.620x / 4.427-4.768x |
| single-node | lexical | 0.928-0.941x / 0.995-1.039x / 1.025-1.076x | 2.240-2.289x / 2.040-2.083x / 2.184-2.347x |
| single-node | ranking | 1.027-1.029x / 1.098-1.116x / 1.113-1.134x | 2.027-2.036x / 2.100-2.129x / 2.420-2.593x |
| single-node | facet | 1.357-1.367x / 1.485-1.500x / 1.374-1.420x | 2.181-2.233x / 2.074-2.234x / 2.477-2.502x |
| single-node | sort_filter | 0.923-0.928x / 0.972-0.989x / 1.021-1.022x | 2.475-2.564x / 2.411-2.525x / 2.495-2.583x |
| single-node | nested | 0.976-0.989x / 0.994-1.028x / 1.050-1.087x | 1.645-1.651x / 1.581-1.587x / 1.811-1.859x |
| single-node | refresh | 0.964-0.985x / 1.037-1.102x / 0.944-0.991x | 6.580-6.711x / 7.755-8.025x / 7.590-8.172x |
| three-node | write | 0.873-0.895x / 0.849-0.886x / 0.880-0.904x | 9.043-9.538x / 10.159-10.863x / 13.435-13.696x |
| three-node | lexical | 0.914-0.928x / 0.898-0.943x / 0.900-0.928x | 6.616-6.693x / 7.985-8.479x / 8.630-8.917x |
| three-node | ranking | 0.847-0.864x / 0.861-0.898x / 0.863-0.881x | 6.016-6.265x / 7.878-8.266x / 9.450-9.589x |
| three-node | facet | 0.996-1.051x / 1.034-1.121x / 0.944-1.028x | 6.413-6.804x / 7.545-8.545x / 8.561-8.749x |
| three-node | sort_filter | 0.919-0.937x / 0.889-0.927x / 0.895-0.915x | 8.225-8.968x / 9.920-10.830x / 10.822-12.236x |
| three-node | nested | 0.917-0.940x / 0.896-0.940x / 0.835-0.894x | 5.706-5.981x / 6.739-7.832x / 7.578-8.726x |
| three-node | refresh | 0.849-0.869x / 0.830-0.866x / 0.747-0.755x | 12.229-12.882x / 11.935-13.457x / 11.485-12.714x |

</details>
