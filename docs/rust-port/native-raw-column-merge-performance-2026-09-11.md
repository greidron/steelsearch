# Native raw column merge 전체 반복 성능 (2026-09-11)

완료된 6회/12토폴로지의 요청 오류는 0이다. 최종 `result.json`은
`execution_inputs_verified=true`, `acceptance_established=false`,
`numeric_budget_passed=false`를 기록하며, 모든 child run의 exit code는 0이다.
부모 판정은 수치 예산 실패로 `FAIL`이다. TV1은 미완료이고 전체 계획 수락은 0/40이며,
새 release는 만들지 않는다.

이 문서의 모든 원시 수치와 delta는
`target/core-replacement-c06/native-raw-column-merge-repeated-full`의 각 summary JSON과 고정
`docs/releases/v0.6.0/current.json`에서 개별 run별로 계산했다. pooling이나 평균은 없다.

## 실행 정체성

- fixed published baseline: Steelsearch 3.7.0 (`build_hash=steelsearch-dev`),
  `/home/ubuntu/steelsearch/target/release/steelsearch`, SHA-256
  `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`.
  이 경로는 published 기록의 경로다. 이번 paired baseline 실행은
  `/home/ubuntu/steelsearch/target/core-replacement-s01/baseline/steelsearch`를 사용했으며
  동일 SHA-256이다. `target/release`의 내용을 이번 실행의 baseline으로 추정하거나
  사용하지 않았다.
- candidate: Steelsearch 3.7.0 (`build_hash=steelsearch-dev`),
  `/home/ubuntu/steelsearch/target/core-replacement-c06/native-raw-column-merge-candidate/artifacts/steelsearch`,
  SHA-256 `6d7f90e198d3f4f0c75bfa58f13e77430e8d786096c9fc8f69a563833f95635d`.
- paired OpenSearch: 2.19.0, build hash
  `fd9a9d90df25bea1af2c6a85039692e815b894f5`, image
  `opensearchproject/opensearch@sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb`.
- HTTP 기능 참조는 OpenSearch 3.7.0-SNAPSHOT이고 성능 참조는 OpenSearch 2.19.0이다.
  두 참조의 version/identity를 동등하다고 해석하지 않는다.

HTTP 실행은 37 fixtures/2,625 cases에서 2,353 passed, 272 failed, skipped 0이며,
`668365ad` 후보와 case state가 동일하다. native 166/172, engine 966, node 1,125는
`pass`다. 이는 HTTP acceptance나 구현 완료의 증명이 아니다.

고정 공개 baseline JSON의 SHA-256은
`d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788`이다.

## 실제 workload와 도구

5,000 documents, vector dimension 384, seed 13, 4 clients, 60 seconds, timeout 10 seconds,
3 shards, single-node replicas 0, three-node replicas 1, profile `minilm-knn`, Java heap
`-Xms512m -Xmx512m`를 사용했다. query mix는
`write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,refresh=5`이며 vector,
hybrid와 모든 fallback mix는 0이다. 모든 scenario는 `reset=true`다.

실제 runner는 `/usr/bin/python3 /home/ubuntu/steelsearch/tools/run-search-benchmark-matrix.py`이며,
실제 host는 `openclaw-worker1` (`aarch64`, `Linux-6.17.0-1019-oracle-aarch64-with-glibc2.39`)다.
plan의 반복 정책은 2회, 개별 run percentile만 사용, retry 없음이다.

`plan.json` SHA-256은 `951ff9a6810bdd9bbfb5ad0845b3c50264ab485419e390d72a999c74369644fa`이고, 실행 도구 해시는 다음과 같다.

- `tools/run_core_performance_gate.py`: `ce077298ff4f6ed4c8ad6af2be1a1390f93bd4d19c21017bec0e7e00b5c5c65c`
- `tools/run-search-benchmark-matrix.py`: `b260a0a3a59ee3449ea0227a65507d8bd67be16caddb7ed91ebab71ee0872f71`
- `tools/run-http-load-baseline.py`: `6bea01c1067b60bb971c312d29e68056b6edbb0c37501389753b097ffdb8ee31`
- `tools/run-steelsearch-dev.sh`: `f1f0716a854ed0722a52327da44ec4504bd9dc0f6244bc8402f75d47ea522f5f`
- `tools/run-steelsearch-cluster-dev.sh`: `0762d547bb46afb7c6ee20465c2fe0261eafd3c194068f3504757257dc137240`
- `tools/run-opensearch-vector-dev.sh`: `790aec604016b9c98e5ca359896da7b7c6e3f3eb28cd00faed81d0115c91ff90`
- `tools/run-opensearch-cluster-dev.sh`: `4aeb38234750704268f61865fe7d529bfef37c9e4533f29628557d1f58e6e040`
- `tools/benchmark_runtime_evidence.py`: `28ef67b0e839d6cf2dc3d5a00534fea68e915f45124258ad27dd33b47560923e`
- `tools/benchmark_cgroup_evidence.py`: `8fc6c910ff3aa6e9b5217e1321b8acd481efe7ae076afb3ae682ceacbbf71089`
- `tools/core_performance_reports.py`: `2edae31d99350cacc8bb123e4a8b17724ed2fad7eb512985631da4775dc2f7d0`
- `tools/benchmark_timeline.py`: `386bd5907ac490ecbaf405df041e0a140c3ca75795039387889c59d7744f45a3`
- `tools/core_performance_budget.py`: `8b575e6a90bdd62360f6fc96019a503266ec60ea75e895946dbd25a99c88a9de`
- `tools/release_notes.py`: `b26edcdf1333c98faa36bf935203168c94b78dd72ab45f3442bf15c9ee9f9522`
- `docs/releases/v0.6.0/current.json`: `d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788`

## 실행별 처리량

| 순서 | 역할 | 단일 ops/s | 3노드 ops/s | 요청 오류 |
|---:|---|---:|---:|---:|
| 0 | baseline | 745.371 | 857.845 | 0 |
| 1 | candidate | 720.822 | 876.895 | 0 |
| 2 | opensearch | 285.775 | 113.908 | 0 |
| 3 | opensearch | 283.111 | 110.374 | 0 |
| 4 | candidate | 758.555 | 872.433 | 0 |
| 5 | baseline | 738.700 | 906.109 | 0 |

처리량 delta는 `(candidate/reference - 1) * 100`이다. published는 변경하지 않은
고정 v0.6.0 baseline이고, paired OpenSearch는 같은 repetition의 별도 실제 측정이다.

| 반복 | 토폴로지 | published 대비 | paired OpenSearch 대비 |
|---:|---|---:|---:|
| 1 | single-node | -2.99% | +152.23% |
| 1 | three-node | -5.85% | +669.83% |
| 2 | single-node | +2.09% | +167.94% |
| 2 | three-node | -6.33% | +690.44% |

## 전체 지연

각 셀은 candidate `mean / p95 / p99` ms다. 뒤의 두 셀은 각각 fixed published
v0.6.0과 같은 repetition의 paired OpenSearch 대비 변화율이며, 양수는 latency 악화다.
각 28 scenario row는 독립된 원시 측정값이다.

| 반복 | 토폴로지/작업 | candidate ms | published 대비 | paired OS 대비 |
|---:|---|---:|---:|---:|
| 1 | single-node/write | 3.315 / 6.254 / 8.169 | +15.39% / +18.56% / +19.58% | -75.01% / -70.28% / -76.08% |
| 1 | single-node/lexical | 4.342 / 8.629 / 12.673 | +5.87% / -3.56% / -7.80% | -55.79% / -53.82% / -56.75% |
| 1 | single-node/ranking | 6.162 / 11.107 / 15.335 | -3.92% / -10.49% / -11.67% | -49.97% / -50.97% / -59.75% |
| 1 | single-node/facet | 7.581 / 15.524 / 20.375 | +3.28% / +2.42% / +0.80% | -35.20% / -31.24% / -44.63% |
| 1 | single-node/sort_filter | 4.917 / 9.505 / 13.574 | +7.54% / +2.20% / -4.08% | -59.16% / -58.42% / -59.24% |
| 1 | single-node/nested | 6.441 / 11.981 / 16.597 | +1.51% / -1.37% / -5.59% | -39.81% / -42.65% / -46.17% |
| 1 | single-node/refresh | 7.304 / 13.643 / 17.338 | -1.12% / -8.31% / -4.56% | -85.57% / -87.62% / -89.50% |
| 1 | three-node/write | 3.299 / 6.067 / 8.019 | +11.12% / +10.75% / +10.28% | -89.04% / -90.10% / -92.28% |
| 1 | three-node/lexical | 3.724 / 6.978 / 9.905 | +5.77% / +3.45% / -2.22% | -84.49% / -86.10% / -87.88% |
| 1 | three-node/ranking | 5.064 / 8.706 / 11.592 | +12.92% / +8.34% / +2.55% | -84.17% / -87.36% / -90.36% |
| 1 | three-node/facet | 5.203 / 9.846 / 13.259 | +5.48% / +4.15% / +1.06% | -82.74% / -85.09% / -88.32% |
| 1 | three-node/sort_filter | 4.153 / 7.495 / 10.370 | +4.52% / +4.23% / -5.37% | -88.54% / -90.48% / -91.75% |
| 1 | three-node/nested | 4.585 / 8.338 / 11.408 | +5.39% / +5.26% / +0.35% | -82.40% / -86.36% / -86.21% |
| 1 | three-node/refresh | 7.966 / 16.048 / 20.231 | -5.00% / -7.03% / -8.21% | -93.78% / -93.80% / -95.48% |
| 2 | single-node/write | 3.150 / 5.786 / 7.259 | +9.66% / +9.68% / +6.26% | -76.48% / -72.98% / -76.88% |
| 2 | single-node/lexical | 4.128 / 8.090 / 11.529 | +0.65% / -9.59% / -16.13% | -57.95% / -56.87% / -61.21% |
| 2 | single-node/ranking | 5.933 / 10.364 / 13.786 | -7.49% / -16.48% / -20.59% | -52.87% / -55.92% / -63.84% |
| 2 | single-node/facet | 7.193 / 14.211 / 18.066 | -2.01% / -6.25% / -10.63% | -39.24% / -35.55% / -47.86% |
| 2 | single-node/sort_filter | 4.628 / 8.630 / 11.521 | +1.22% / -7.20% / -18.58% | -62.45% / -61.88% / -69.52% |
| 2 | single-node/nested | 6.204 / 11.366 / 15.106 | -2.23% / -6.43% / -14.07% | -40.84% / -41.94% / -51.24% |
| 2 | single-node/refresh | 6.629 / 12.122 / 14.988 | -10.26% / -18.53% / -17.49% | -87.03% / -89.47% / -90.41% |
| 2 | three-node/write | 3.293 / 6.107 / 7.912 | +10.91% / +11.48% / +8.81% | -89.50% / -91.06% / -92.76% |
| 2 | three-node/lexical | 3.743 / 7.005 / 9.604 | +6.30% / +3.85% / -5.20% | -84.98% / -87.57% / -91.00% |
| 2 | three-node/ranking | 5.083 / 8.689 / 11.689 | +13.35% / +8.12% / +3.40% | -84.23% / -87.63% / -90.08% |
| 2 | three-node/facet | 5.207 / 9.775 / 14.065 | +5.55% / +3.40% / +7.19% | -83.64% / -85.91% / -87.55% |
| 2 | three-node/sort_filter | 4.184 / 7.560 / 10.612 | +5.32% / +5.15% / -3.16% | -88.65% / -91.19% / -91.17% |
| 2 | three-node/nested | 4.505 / 8.075 / 11.756 | +3.56% / +1.95% / +3.40% | -83.09% / -85.91% / -88.84% |
| 2 | three-node/refresh | 8.356 / 17.086 / 23.644 | -0.35% / -1.02% / +7.27% | -93.70% / -93.63% / -94.22% |

## 판정과 실패 목록

고정 누적 기준은 topology throughput 각각 95% 이상, scenario latency mean/p95/p99 각각
105% 이하다. 다른 지표의 개선은 단일 실패를 상쇄하지 않는다.

| 반복 | 비교 | 실패 수 / 44 | 실패 metric |
|---:|---|---:|---|
| 1 | published | 15 / 44 | `three-node/throughput`, `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `single-node/lexical/mean`, `single-node/sort_filter/mean`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/ranking/mean`, `three-node/ranking/p95`, `three-node/facet/mean`, `three-node/nested/mean`, `three-node/nested/p95` |
| 1 | paired | 5 / 44 | `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `single-node/lexical/mean`, `single-node/sort_filter/mean` |
| 1 | drift | 23 / 44 | `three-node/throughput`, `single-node/sort_filter/p99`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/lexical/p95`, `three-node/lexical/p99`, `three-node/ranking/mean`, `three-node/ranking/p95`, `three-node/ranking/p99`, `three-node/facet/mean`, `three-node/facet/p95`, `three-node/facet/p99`, `three-node/sort_filter/mean`, `three-node/sort_filter/p95`, `three-node/sort_filter/p99`, `three-node/nested/mean`, `three-node/nested/p95`, `three-node/nested/p99`, `three-node/refresh/mean`, `three-node/refresh/p95`, `three-node/refresh/p99` |
| 2 | published | 15 / 44 | `three-node/throughput`, `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/ranking/mean`, `three-node/ranking/p95`, `three-node/facet/mean`, `three-node/facet/p99`, `three-node/sort_filter/mean`, `three-node/sort_filter/p95`, `three-node/refresh/p99` |
| 2 | paired | 7 / 44 | `single-node/write/mean`, `single-node/write/p95`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/ranking/mean`, `three-node/ranking/p95` |
| 2 | drift | 3 / 44 | `three-node/lexical/p99`, `three-node/nested/p99`, `three-node/refresh/p99` |

`baseline_drift`는 paired baseline run과 fixed published baseline 간 비교이며 candidate
실패의 단일 원인으로 귀속할 근거가 아니다. 그러나 첫 baseline의 drift와 두 번째 baseline의
drift는 fixed v0.6.0 수치 예산의 waiver가 아니다.

OpenSearch 수치는 이 workload에서의 상대 비교일 뿐 API, 기능, 정확도, 응답량 또는 운영
parity의 증명이 아니다. 특히 baseline response/visibility semantics에는 응답 차이와 누락이
남아 있어 정확도·응답량의 동등성을 보장하지 않는다. 이 제한은 수치 예산 또는 release
판정의 waiver가 아니며, universal compatibility claim도 아니다.

## 증거와 무결성

- `result.json` SHA-256: `8e76e7327d2cd0b0e78ba6ce1c5446e56f3aef93ff012892489dcdfecdf1d306`.
- `plan.json` SHA-256: `951ff9a6810bdd9bbfb5ad0845b3c50264ab485419e390d72a999c74369644fa`.
- summary SHA-256: `00 053c64d415cc8b01dc54722d77ceb83ca5f763033b0e7c7abbe78c072e162133`, `01 f3a1ba734e1189a37834de0e72585e968a06288ea1f82aeff819a4a4381eb46d`, `02 4aa1daabcdae921c0ae8ea9eee588e021171e26c895eea7474e60756e03dfaf7`, `03 d2aea57fe5f1ee6ca1a8a1af085218a18cf38d3d2920ad65d64905c20c54b620`, `04 332dd9e2d54ce495d2d90b40698b572a05f31253b88ba29dc5e9d345663736be`, `05 233ddc3436432b85d76bf569b7683bdba605ac3bcfc961fac0198c9386a6d3ee`.
- 모든 child exit code: `0, 0, 0, 0, 0, 0`; request error 합계: 0.
- 결과 scope: `repeated numeric and artifact checks; source build and effective runtime enforcement unverified`.

결론: 입력 검증과 모든 child 실행의 정상 종료는 확인했지만, fixed cumulative numeric budget은
두 repetition 모두 실패했다. TV1은 미완료, 전체 계획 수락은 0/40이며 release를 생성하거나
게시하지 않는다.
