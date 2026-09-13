# Native term table 전체 반복 성능 (2026-09-11)

완료된 6회/12토폴로지의 요청 오류는 0이다. 최종 `result.json`은
`execution_inputs_verified=true`, `acceptance_established=false`,
`numeric_budget_passed=false`를 기록하며, 모든 child run의 exit code는 0이다.
부모 판정은 수치 예산 실패로 exit 1이다. TV1은 미완료이고 전체 계획 수락은 0/40이며,
새 release는 만들지 않는다.

이 보고서는 이전의 불완전 실행
`target/core-replacement-c06/native-term-table-repeated-full/result.json`
(SHA-256 `37b83f932cef62b926f9901414d38c9ec53f8c4614a67421f4925854e4c6d440`,
두 번째 OpenSearch run의 초기화 전 안전 검사에서 parent exit 2)을 보존·참조한다. 그
실행의 수치나 비교표는 사용하지 않았다. 여기의 모든 원시 수치와 delta는
`native-term-table-repeated-full-ready`의 각 JSON과 고정
`docs/releases/v0.6.0/current.json`에서 개별 run별로 계산했으며 pooling이나 평균은 없다.

## 실행 정체성

- fixed published baseline: Steelsearch 3.7.0 (`build_hash=steelsearch-dev`),
  `/home/ubuntu/steelsearch/target/release/steelsearch`, SHA-256 `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`.
  이 경로는 원본 published 기록의 경로다. 이번 paired baseline 실행은
  `/home/ubuntu/steelsearch/target/core-replacement-s01/baseline/steelsearch`를
  사용했으며 동일 SHA-256이다. 현재 target/release 경로의 내용을 재측정본으로
  추정하거나 사용하지 않았다.
- candidate: Steelsearch 3.7.0 (`build_hash=steelsearch-dev`),
  `/home/ubuntu/steelsearch/target/core-replacement-c06/native-term-table-candidate/artifacts/steelsearch`, SHA-256 `668365ad0524a4ede6be85503665babc5884c493ee514120082aa900f458b721`. 후보 source는
  `c224a57a` 상태이며 term-table vendor 변경만 적용된 격리 후보이다.
- paired OpenSearch: 2.19.0, build hash
  `fd9a9d90df25bea1af2c6a85039692e815b894f5`, image `opensearchproject/opensearch@sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb`.
- HTTP 기능 참조는 OpenSearch 3.7.0-SNAPSHOT이고 성능 참조는 OpenSearch 2.19.0이다.
  두 참조의 version/identity를 동등하다고 해석하지 않는다.

HTTP 실행은 37 fixtures/2,625 cases에서 2,353 passed, 272 failed, skipped 0이며,
이전 `c224a57a` 후보와 case state가 동일하다. 이는 HTTP acceptance나 구현 완료의
증명이 아니다.

고정 공개 baseline의 SHA-256은 `d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788`이다.

## 실제 workload와 도구

5,000 documents, vector dimension 384, seed 13, 4 clients, 60 seconds, timeout 10 seconds,
3 shards, single-node replicas 0, three-node replicas 1, profile `minilm-knn`, Java heap
`-Xms512m -Xmx512m`를 사용했다. query mix는
`write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,refresh=5`이며 vector,
hybrid와 모든 fallback mix는 0이다. 모든 scenario는 `reset=true`다.

실제 runner는 `/usr/bin/python3 /home/ubuntu/steelsearch/tools/run-search-benchmark-matrix.py`이며,
실제 host는 `openclaw-worker1` (`aarch64`, `Linux-6.17.0-1019-oracle-aarch64-with-glibc2.39`)다.
plan의 반복 정책은 2회, 개별 run percentile만 사용, retry 없음이다.

`plan.json` SHA-256은 `32f028fdf891e6f81b624af5aea6a30cf02a86c8a21b266f99405dd334a8d0a8`이고, 실행 도구 해시는 다음과 같다.

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
| 0 | baseline | 741.798 | 904.378 | 0 |
| 1 | candidate | 741.758 | 873.220 | 0 |
| 2 | opensearch | 280.966 | 115.922 | 0 |
| 3 | opensearch | 285.661 | 114.271 | 0 |
| 4 | candidate | 746.290 | 869.829 | 0 |
| 5 | baseline | 744.272 | 915.816 | 0 |

처리량 delta는 `(candidate/reference - 1) * 100`이다. published는 변경하지 않은
고정 v0.6.0 baseline이고, paired OpenSearch는 동일 repetition의 별도 실제 측정이다.

| 반복 | 토폴로지 | published 대비 | paired OpenSearch 대비 |
|---:|---|---:|---:|
| 1 | single-node | -0.17% | +164.00% |
| 1 | three-node | -6.24% | +653.28% |
| 2 | single-node | +0.44% | +161.25% |
| 2 | three-node | -6.61% | +661.20% |

## 전체 지연

각 셀은 candidate `mean / p95 / p99` ms다. 뒤의 두 셀은 각각 fixed published
v0.6.0과 같은 repetition의 paired OpenSearch 대비 변화율이며, 양수는 latency 악화다.
각 28 scenario row는 독립된 원시 측정값이다.

| 반복 | 토폴로지/작업 | candidate ms | published 대비 | paired OS 대비 |
|---:|---|---:|---:|---:|
| 1 | single-node/write | 3.215 / 5.955 / 7.849 | +11.90% / +12.88% / +14.89% | -76.32% / -72.54% / -77.68% |
| 1 | single-node/lexical | 4.217 / 8.358 / 11.746 | +2.83% / -6.59% / -14.55% | -57.73% / -55.43% / -61.09% |
| 1 | single-node/ranking | 5.983 / 10.389 / 14.361 | -6.70% / -16.28% / -17.28% | -52.74% / -55.79% / -63.02% |
| 1 | single-node/facet | 7.375 / 14.599 / 18.579 | +0.48% / -3.69% / -8.09% | -37.94% / -35.85% / -50.12% |
| 1 | single-node/sort_filter | 4.786 / 8.890 / 12.367 | +4.67% / -4.41% / -12.61% | -61.66% / -61.80% / -65.41% |
| 1 | single-node/nested | 6.319 / 11.627 / 15.797 | -0.41% / -4.28% / -10.14% | -41.66% / -42.38% / -49.71% |
| 1 | single-node/refresh | 6.960 / 12.515 / 15.712 | -5.78% / -15.89% / -13.51% | -86.16% / -88.62% / -90.12% |
| 1 | three-node/write | 3.277 / 6.013 / 7.683 | +10.38% / +9.76% / +5.66% | -88.90% / -90.35% / -91.83% |
| 1 | three-node/lexical | 3.738 / 6.978 / 9.996 | +6.17% / +3.44% / -1.33% | -84.20% / -86.89% / -87.65% |
| 1 | three-node/ranking | 5.060 / 8.568 / 11.757 | +12.84% / +6.63% / +4.01% | -83.45% / -87.76% / -89.76% |
| 1 | three-node/facet | 5.218 / 9.660 / 13.437 | +5.79% / +2.18% / +2.41% | -83.19% / -86.36% / -87.59% |
| 1 | three-node/sort_filter | 4.174 / 7.644 / 10.666 | +5.06% / +6.32% / -2.67% | -88.26% / -90.15% / -90.75% |
| 1 | three-node/nested | 4.517 / 8.148 / 11.550 | +3.82% / +2.87% / +1.59% | -82.90% / -86.26% / -87.11% |
| 1 | three-node/refresh | 8.373 / 16.595 / 24.029 | -0.15% / -3.86% / +9.02% | -93.15% / -93.36% / -93.47% |
| 2 | single-node/write | 3.185 / 5.955 / 7.556 | +10.86% / +12.89% / +10.61% | -75.97% / -71.09% / -76.95% |
| 2 | single-node/lexical | 4.202 / 8.133 / 11.610 | +2.47% / -9.10% / -15.54% | -57.21% / -55.17% / -61.25% |
| 2 | single-node/ranking | 6.018 / 10.514 / 14.159 | -6.15% / -15.26% / -18.44% | -51.96% / -53.75% / -63.10% |
| 2 | single-node/facet | 7.283 / 14.404 / 18.820 | -0.79% / -4.97% / -6.89% | -37.75% / -32.65% / -45.04% |
| 2 | single-node/sort_filter | 4.736 / 8.829 / 12.373 | +3.58% / -5.06% / -12.57% | -61.61% / -61.07% / -65.95% |
| 2 | single-node/nested | 6.290 / 11.314 / 14.918 | -0.88% / -6.85% / -15.14% | -40.53% / -39.47% / -49.45% |
| 2 | single-node/refresh | 6.861 / 12.730 / 16.348 | -7.12% / -14.45% / -10.01% | -86.24% / -88.07% / -89.08% |
| 2 | three-node/write | 3.302 / 6.093 / 7.871 | +11.21% / +11.22% / +8.24% | -88.96% / -89.77% / -92.03% |
| 2 | three-node/lexical | 3.757 / 7.112 / 9.990 | +6.69% / +5.43% / -1.38% | -84.80% / -87.32% / -88.73% |
| 2 | three-node/ranking | 5.095 / 8.665 / 11.870 | +13.62% / +7.82% / +5.01% | -83.63% / -87.47% / -89.88% |
| 2 | three-node/facet | 5.222 / 9.851 / 14.001 | +5.86% / +4.20% / +6.71% | -83.32% / -86.55% / -88.00% |
| 2 | three-node/sort_filter | 4.203 / 7.618 / 10.999 | +5.78% / +5.95% / +0.37% | -88.30% / -90.05% / -91.02% |
| 2 | three-node/nested | 4.563 / 8.281 / 11.344 | +4.89% / +4.55% / -0.22% | -83.12% / -86.84% / -90.95% |
| 2 | three-node/refresh | 8.299 / 16.955 / 22.837 | -1.03% / -1.78% / +3.61% | -93.15% / -92.99% / -94.67% |

## 판정과 실패 목록

고정 누적 기준은 topology throughput 각각 95% 이상, scenario latency mean/p95/p99 각각
105% 이하다. 다른 지표의 개선은 단일 실패를 상쇄하지 않는다.

| 반복 | 비교 | 실패 수 / 44 | 실패 metric |
|---:|---|---:|---|
| 1 | published | 14 / 44 | `three-node/throughput`, `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/ranking/mean`, `three-node/ranking/p95`, `three-node/facet/mean`, `three-node/sort_filter/mean`, `three-node/sort_filter/p95`, `three-node/refresh/p99` |
| 1 | paired | 5 / 44 | `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `three-node/write/mean`, `three-node/ranking/mean` |
| 1 | drift | 11 / 44 | `single-node/refresh/p99`, `three-node/lexical/p95`, `three-node/lexical/p99`, `three-node/ranking/p95`, `three-node/ranking/p99`, `three-node/facet/p95`, `three-node/facet/p99`, `three-node/nested/p99`, `three-node/refresh/mean`, `three-node/refresh/p95`, `three-node/refresh/p99` |
| 2 | published | 16 / 44 | `three-node/throughput`, `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/lexical/p95`, `three-node/ranking/mean`, `three-node/ranking/p95`, `three-node/ranking/p99`, `three-node/facet/mean`, `three-node/facet/p99`, `three-node/sort_filter/mean`, `three-node/sort_filter/p95` |
| 2 | paired | 10 / 44 | `three-node/throughput`, `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/ranking/mean`, `three-node/facet/p99` |
| 2 | drift | 5 / 44 | `three-node/ranking/p99`, `three-node/nested/p99`, `three-node/refresh/mean`, `three-node/refresh/p95`, `three-node/refresh/p99` |

`baseline_drift`는 paired baseline run과 fixed published baseline 간 비교이며 candidate
실패의 단일 원인으로 귀속할 근거가 아니다. 그러나 drift의 존재도 fixed v0.6.0 수치 예산의
면제가 아니다.

OpenSearch 수치는 이 workload에서의 상대 비교일 뿐 API, 기능, 정확도, 응답량 또는 운영
parity의 증명이 아니다. 특히 baseline ranking visibility semantics에는 응답 차이와 누락이
남아 있어 정확도·응답량의 동등성을 보장하지 않는다. 이 제한은 수치 예산 또는 release
판정의 waiver가 아니다.

## 증거와 무결성

- `result.json` SHA-256: `da4d0dedee101e4a173e09d0a614443eee87e05cc2786ef5aa457432802b5f57`.
- `plan.json` SHA-256: `32f028fdf891e6f81b624af5aea6a30cf02a86c8a21b266f99405dd334a8d0a8`.
- summary SHA-256: `00 449b210d6a5de4fdf9c2bef66486314b5d8674fc77b94a58fcbdfdd318fdc5d5`, `01 06401ea7015ae5243ad94a5423c5184122850406a2eac93842688ac5a2fb628e`, `02 8a58c39a9323d1313a7e33e7635e6731d54fd57d2e25b1eccfd9290cc8f9a646`, `03 6905e4148b8898ff9fb35f875af92c6f7da2205055ddca5eebb9b21e85c57943`, `04 490b6e4245fbfd6ac1653791e0a39bb82a71ee82380d0cb6dcf64430b5bc1010`, `05 ec82bf4c0e20532abaee5351264dcabff5c0128dcb84d3e60b8e1cc43ad6b40c`.
- 모든 child exit code: `0, 0, 0, 0, 0, 0`; request error 합계: 0.
- 결과 scope: `repeated numeric and artifact checks; source build and effective runtime enforcement unverified`.

결론: 입력 검증과 모든 child 실행의 정상 종료는 확인했지만, fixed cumulative numeric budget은
두 repetition 모두 실패했다. TV1은 미완료, 전체 계획 수락은 0/40이며 release를 생성하거나
게시하지 않는다.
