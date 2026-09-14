# Current Core Performance Status

This file is generated from the latest completed, execution-verified repeated non-plugin benchmark.

- Ratio `1.000x` means equal performance. Higher is faster for every row.
- Throughput ratio = candidate/reference. Latency ratio = reference/candidate.
- Each cell is the two-run range; the lower endpoint is the conservative value.
- `took` is excluded. This is not a release approval or implementation-acceptance record.
- Source: `target/late-replay-current-full-gate-20260914/result.json`.
- Benchmark plan: 2026-09-14T03:06:52.170895+00:00; candidate SHA-256: `36bb276347baf3318212d11515043b29681662884b5df9743725c96c8a5b8b33`.
- Fixed v0.6.0 gate: 23/44 measured values have a two-run lower ratio below 0.950x.

## At A Glance

Each value is the conservative lowest ratio. `1.000x` is equal; higher is faster.
Scenario rows use the worst of mean, p95, and p99 across both repetitions.

### Single Node

| Scenario | vs v0.6.0 | vs OpenSearch |
| --- | ---: | ---: |
| throughput | 1.047x | 2.777x |
| write latency | 0.867x | 3.569x |
| lexical latency | 0.955x | 2.125x |
| ranking latency | 1.040x | 2.055x |
| facet latency | 1.352x | 2.234x |
| sort_filter latency | 0.933x | 2.560x |
| nested latency | 0.998x | 1.681x |
| refresh latency | 0.959x | 6.868x |

### 3 Nodes

| Scenario | vs v0.6.0 | vs OpenSearch |
| --- | ---: | ---: |
| throughput | 0.923x | 8.390x |
| write latency | 0.873x | 9.901x |
| lexical latency | 0.887x | 7.060x |
| ranking latency | 0.825x | 6.500x |
| facet latency | 0.969x | 7.298x |
| sort_filter latency | 0.912x | 9.528x |
| nested latency | 0.883x | 6.242x |
| refresh latency | 0.728x | 13.453x |

<details>
<summary>Detailed ranges: mean / p95 / p99</summary>

## Detailed Measurements

Rows are `mean / p95 / p99` performance ratios, all with the same higher-is-faster direction.

| Topology | Scenario | v0.6.0 ratio (mean / p95 / p99) | OpenSearch ratio (mean / p95 / p99) |
| --- | --- | ---: | ---: |
| single-node | write | 0.875-0.890x / 0.867-0.901x / 0.877-0.879x | 4.089-4.156x / 3.569-3.726x / 4.287-4.375x |
| single-node | lexical | 0.955-0.963x / 1.051x / 1.089-1.134x | 2.326-2.388x / 2.125-2.271x / 2.334-2.377x |
| single-node | ranking | 1.040-1.044x / 1.126-1.146x / 1.179-1.180x | 2.055-2.092x / 2.158-2.226x / 2.610-2.673x |
| single-node | facet | 1.352-1.371x / 1.448-1.512x / 1.388-1.401x | 2.234-2.235x / 2.276-2.298x / 2.449-2.622x |
| single-node | sort_filter | 0.933-0.950x / 0.971-1.032x / 1.018-1.087x | 2.560-2.602x / 2.571-2.620x / 2.710-2.754x |
| single-node | nested | 0.998-1.017x / 1.028-1.061x / 1.071-1.148x | 1.703-1.787x / 1.681-1.862x / 2.001-2.148x |
| single-node | refresh | 1.017x / 1.113-1.143x / 0.959-1.039x | 6.868-6.996x / 8.343-8.556x / 8.407-8.593x |
| three-node | write | 0.890-0.895x / 0.873-0.883x / 0.881-0.885x | 9.901-10.345x / 10.675-12.221x / 13.036-16.569x |
| three-node | lexical | 0.919-0.923x / 0.924-0.934x / 0.887-0.903x | 7.060-7.198x / 9.053-9.282x / 8.457-9.655x |
| three-node | ranking | 0.853x / 0.869-0.870x / 0.825-0.894x | 6.500-6.704x / 8.132-9.069x / 10.175-12.598x |
| three-node | facet | 1.031-1.033x / 1.075-1.089x / 0.969-0.991x | 7.298-7.328x / 8.701-8.934x / 9.723-10.265x |
| three-node | sort_filter | 0.933-0.943x / 0.913-0.925x / 0.912-0.939x | 9.528-9.681x / 11.724-12.683x / 11.533-11.798x |
| three-node | nested | 0.942-0.951x / 0.943-0.945x / 0.883-0.908x | 6.242-6.609x / 7.878-8.082x / 8.495-9.924x |
| three-node | refresh | 0.881-0.898x / 0.882-0.888x / 0.728-0.824x | 14.319-15.790x / 15.146-16.053x / 13.453-17.707x |

</details>
