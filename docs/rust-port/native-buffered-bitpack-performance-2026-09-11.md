# Native buffered bitpack full-repeat performance (2026-09-11)

The completed full gate is `FAIL`. `result.json` records
`execution_inputs_verified=true`, `acceptance_established=false`, and
`numeric_budget_passed=false`; all six child runs returned 0 and all request-error
counts are zero. The fixed published v0.6.0 cumulative budget failed in both
repetitions. This is not implementation acceptance: TV1 remains incomplete,
overall plan acceptance is 0/40, and there is no release or promotion.

All raw values below come from the six summaries and the final result/plan artifacts
under `target/core-replacement-c06/native-buffered-bitpack-repeated-full`. Percentiles
are individual-run values; no pooling or averaging was applied.

## Executable identities and scope

- Fixed published v0.6.0 baseline: Steelsearch 3.7.0
  (`build_hash=steelsearch-dev`), published executable identity
  `/home/ubuntu/steelsearch/target/release/steelsearch`, SHA-256
  `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`.
  The actual paired baseline executed from
  `/home/ubuntu/steelsearch/target/core-replacement-s01/baseline/steelsearch`,
  with that same SHA-256. The fixed published baseline and the actual paired
  baseline are distinct comparison concepts; neither was manually inferred from
  before/after labels.
- Candidate: Steelsearch 3.7.0 (`build_hash=steelsearch-dev`), actual executable
  `/home/ubuntu/steelsearch/target/core-replacement-c06/native-buffered-bitpack-candidate/artifacts/steelsearch`,
  SHA-256 `a5b38b4932a3386fc495800578f6d76970ca3882437b93f3c60cfc280ec6c6b8`.
- Paired performance reference: OpenSearch 2.19.0, build hash
  `fd9a9d90df25bea1af2c6a85039692e815b894f5`, image
  `opensearchproject/opensearch@sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb`.
  The HTTP functional reference was OpenSearch 3.7.0-SNAPSHOT; it is not the
  performance OpenSearch 2.19.0 identity.
- HTTP `native-buffered-bitpack-release-live` recorded 2,353 passed, 272 failed,
  skipped 0, with case statuses identical to `6d7f90e1`. The buffered experiment
  passed 176 native tests and one doc-test on each side;
  engine 966 and node 1,125 passed for the frozen server candidate. These are scoped results,
  not HTTP acceptance or completion evidence.
- The preserved source manifest SHA-256 is
  `6e4e1a6434cbd7f4cca64a3375678b62214b75bfc2b84290d5490a85bde11a47`.
  The candidate-folder release build log SHA-256 is
  `dbba35148d3a5ec59c739ee95b51f754d92d142a6528aaed2fab53d38eb57028`.

The actual runner was `/usr/bin/python3 /home/ubuntu/steelsearch/tools/run-search-benchmark-matrix.py`
on `openclaw-worker1` (`aarch64`,
`Linux-6.17.0-1019-oracle-aarch64-with-glibc2.39`): 5,000 documents, dimension
384, seed 13, four clients, 60 seconds, ten-second timeout, three shards,
single-node replicas 0, three-node replicas 1, and profile `minilm-knn`.
The mix was `write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,refresh=5`;
vector, hybrid, and fallback mixes were zero and every scenario used `reset=true`.

The gate scope is `repeated numeric and artifact checks; source build and effective runtime enforcement unverified`.
Source-build and effective runtime/security/durability/resource enforcement therefore
remain unverified by this gate; the manual build record is separate. This caveat is
not a waiver of fixed-baseline drift or a basis to attribute regression causality.

## Raw throughput

| Order | Role | single-node ops/s | three-node ops/s | request errors |
|---:|---|---:|---:|---:|
| 0 | baseline | 749.080 | 927.731 | 0 |
| 1 | candidate | 758.784 | 879.128 | 0 |
| 2 | OpenSearch | 283.527 | 112.529 | 0 |
| 3 | OpenSearch | 286.164 | 110.660 | 0 |
| 4 | candidate | 739.363 | 863.650 | 0 |
| 5 | baseline | 737.075 | 887.911 | 0 |

Throughput delta is `(candidate/reference - 1) * 100`. Published means the fixed
v0.6.0 reference; paired OpenSearch is the measured OpenSearch run for the same
repetition.

| Repetition | topology | candidate ops/s | fixed published v0.6.0 | paired OpenSearch |
|---:|---|---:|---:|---:|
| 1 | single-node | 758.784 | +2.12% | +167.62% |
| 1 | three-node | 879.128 | -5.61% | +681.24% |
| 2 | single-node | 739.363 | -0.49% | +158.37% |
| 2 | three-node | 863.650 | -7.27% | +680.45% |

## Candidate latency

Each row is candidate `mean / p95 / p99` milliseconds. Positive latency delta is
adverse. The two following cells are calculated per metric against fixed published
v0.6.0 and the paired pinned OpenSearch execution respectively.

| Repetition | topology/operation | candidate ms | fixed published v0.6.0 | paired OpenSearch |
|---:|---|---:|---:|---:|
| 1 | single-node/write | 3.163 / 5.759 / 7.584 | +10.10% / +9.16% / +11.02% | -76.45% / -73.33% / -77.42% |
| 1 | single-node/lexical | 4.134 / 7.964 / 11.471 | +0.80% / -10.99% / -16.55% | -57.59% / -55.58% / -60.97% |
| 1 | single-node/ranking | 5.923 / 10.314 / 13.783 | -7.63% / -16.87% / -20.61% | -52.51% / -54.09% / -62.92% |
| 1 | single-node/facet | 7.212 / 14.285 / 18.531 | -1.75% / -5.75% / -8.32% | -39.48% / -37.60% / -48.71% |
| 1 | single-node/sort_filter | 4.599 / 8.536 / 11.544 | +0.59% / -8.22% / -18.42% | -61.91% / -62.10% / -66.32% |
| 1 | single-node/nested | 6.173 / 11.346 / 15.096 | -2.72% / -6.59% / -14.13% | -42.25% / -40.92% / -51.81% |
| 1 | single-node/refresh | 6.631 / 12.223 / 15.402 | -10.23% / -17.86% / -15.22% | -87.02% / -88.77% / -89.80% |
| 1 | three-node/write | 3.268 / 6.053 / 7.757 | +10.07% / +10.49% / +6.68% | -89.39% / -90.81% / -93.27% |
| 1 | three-node/lexical | 3.746 / 7.033 / 9.924 | +6.39% / +4.27% / -2.04% | -84.62% / -87.54% / -90.01% |
| 1 | three-node/ranking | 5.063 / 8.659 / 11.684 | +12.91% / +7.76% / +3.36% | -84.17% / -88.54% / -90.63% |
| 1 | three-node/facet | 5.166 / 9.650 / 13.083 | +4.73% / +2.08% / -0.29% | -83.52% / -86.83% / -90.36% |
| 1 | three-node/sort_filter | 4.181 / 7.493 / 10.397 | +5.23% / +4.21% / -5.13% | -88.85% / -91.24% / -92.71% |
| 1 | three-node/nested | 4.586 / 8.194 / 11.317 | +5.42% / +3.44% / -0.46% | -83.53% / -86.94% / -90.49% |
| 1 | three-node/refresh | 7.870 / 15.841 / 20.634 | -6.15% / -8.23% / -6.39% | -93.56% / -93.62% / -95.64% |
| 2 | single-node/write | 3.263 / 5.972 / 7.872 | +13.59% / +13.20% / +15.23% | -75.97% / -72.39% / -75.11% |
| 2 | single-node/lexical | 4.206 / 8.215 / 11.460 | +2.57% / -8.19% / -16.63% | -57.30% / -54.83% / -61.06% |
| 2 | single-node/ranking | 6.023 / 10.598 / 14.248 | -6.07% / -14.59% / -17.93% | -51.55% / -53.52% / -63.66% |
| 2 | single-node/facet | 7.314 / 14.524 / 19.034 | -0.36% / -4.18% / -5.84% | -37.56% / -33.92% / -50.34% |
| 2 | single-node/sort_filter | 4.797 / 8.926 / 12.416 | +4.91% / -4.02% / -12.26% | -60.82% / -61.12% / -67.03% |
| 2 | single-node/nested | 6.448 / 12.124 / 16.393 | +1.62% / -0.18% / -6.75% | -37.60% / -34.57% / -42.06% |
| 2 | single-node/refresh | 6.903 / 12.614 / 16.165 | -6.56% / -15.23% / -11.02% | -85.97% / -87.98% / -90.10% |
| 2 | three-node/write | 3.345 / 6.235 / 8.210 | +12.67% / +13.82% / +12.91% | -89.11% / -90.01% / -92.12% |
| 2 | three-node/lexical | 3.788 / 7.145 / 9.857 | +7.57% / +5.93% / -2.70% | -85.16% / -88.27% / -91.36% |
| 2 | three-node/ranking | 5.087 / 8.882 / 11.407 | +13.43% / +10.53% / +0.91% | -84.30% / -87.99% / -90.55% |
| 2 | three-node/facet | 5.260 / 10.005 / 13.604 | +6.64% / +5.83% / +3.68% | -83.51% / -86.26% / -88.08% |
| 2 | three-node/sort_filter | 4.244 / 7.714 / 11.577 | +6.82% / +7.29% / +5.64% | -88.93% / -90.87% / -92.22% |
| 2 | three-node/nested | 4.626 / 8.428 / 12.428 | +6.34% / +6.40% / +9.31% | -83.33% / -86.32% / -88.70% |
| 2 | three-node/refresh | 8.338 / 16.782 / 21.845 | -0.57% / -2.78% / -0.89% | -93.35% / -93.28% / -94.01% |

## Gate failures

The fixed gate requires every topology throughput to be at least 95% and every
scenario latency metric to be at most 105% of v0.6.0. Each comparison covers 44
metrics. Improvements do not offset any failed metric.

| Repetition | comparison | failures / 44 | failed metrics |
|---:|---|---:|---|
| 1 | published | 12 / 44 | `three-node/throughput`, `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/ranking/mean`, `three-node/ranking/p95`, `three-node/sort_filter/mean`, `three-node/nested/mean` |
| 1 | paired | 10 / 44 | `three-node/throughput`, `single-node/write/mean`, `single-node/write/p95`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/ranking/mean`, `three-node/ranking/p95`, `three-node/nested/mean` |
| 1 | drift | 1 / 44 | `single-node/write/p99` |
| 2 | published | 19 / 44 | `three-node/throughput`, `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/lexical/p95`, `three-node/ranking/mean`, `three-node/ranking/p95`, `three-node/facet/mean`, `three-node/facet/p95`, `three-node/sort_filter/mean`, `three-node/sort_filter/p95`, `three-node/sort_filter/p99`, `three-node/nested/mean`, `three-node/nested/p95`, `three-node/nested/p99` |
| 2 | paired | 7 / 44 | `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/ranking/mean` |
| 2 | drift | 18 / 44 | `single-node/write/p95`, `single-node/write/p99`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/p95`, `three-node/lexical/p99`, `three-node/ranking/p95`, `three-node/ranking/p99`, `three-node/facet/mean`, `three-node/facet/p95`, `three-node/facet/p99`, `three-node/sort_filter/p95`, `three-node/sort_filter/p99`, `three-node/nested/p95`, `three-node/nested/p99`, `three-node/refresh/mean`, `three-node/refresh/p95`, `three-node/refresh/p99` |

`baseline_drift` compares the actual paired baseline with the fixed published
v0.6.0 baseline. It does not establish candidate regression causality, and neither
drift list waives the fixed published baseline. Likewise, paired OpenSearch figures
are workload-relative only; they do not establish API, function, accuracy, response
volume, visibility, or operational parity.

## Artifact integrity

- `result.json`: `987918aebbcc105418c43d2ecfa3091f38ccc9c48ff4df3e2d3a0fcae0eb9575`
- `plan.json`: `a99399e4dbd1a2593b541ca15fd1aab5c6bc33d969edce9547989a1e763701ca`
- `00-baseline/summary.json`: `2ca436691f47bddecc7298c8c74c2b3a235ae651c2e7764eed8030573ac10a39`
- `01-candidate/summary.json`: `d6059a4e559c1b9b988057a7a15341ee309784566d6f54282894fc9ef95bf0c1`
- `02-opensearch/summary.json`: `3501729fbb47c90d0ae0973a9e3f9708292d29dac1b322cc5c022176f83e82d0`
- `03-opensearch/summary.json`: `e968d56623009f2263f5b514b65d8c27b069da2e58fde51c3e1c9368b26c0ca2`
- `04-candidate/summary.json`: `83559311d0a0d7d5eead85ac47bca978db62485e83e96c9c006c8b2bcb85983d`
- `05-baseline/summary.json`: `6458ed353302794e264aabba55ec2f45f18706004f48d625faf879c2ae929c53`
- Fixed published baseline JSON `docs/releases/v0.6.0/current.json`:
  `d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788`

All child exit codes were `0, 0, 0, 0, 0, 0`; total request errors were zero.
The full gate still fails its fixed cumulative numeric budget. No baseline drift is
waived, no regression cause is attributed here, and no release or promotion is made.
