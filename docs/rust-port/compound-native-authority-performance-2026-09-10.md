## 2026-09-10 compound native authority 전체 반복 성능 FAIL

후보 `31281a3dbfa3007e720616ff9b36b90e77558324ab4fd2c0e44fb526fcbf1f75`의 전체 non-plugin 반복 측정을 완료했다.
입력 검증 true,6실행/12토폴로지 요청 오류0,부모 exit1,numeric_budget_passed=false다.
측정 중 빌드/시험/진단/코드 변경을 하지 않았으며 종료 후 동결 source.sha256 전체 검증도 통과했다.
전체 HTTP2601건은2351통과250실패,engine953건 통과다. 구현 단위 미완료,수락0/40,제외0,릴리즈 보류를 유지한다.

기준 실행 파일은 `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`,
고정 공개 증거는 docs/releases/v0.6.0/current.json(SHA-256 `d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788`)이다.
성능 참조는 OpenSearch2.19 이미지 `opensearchproject/opensearch@sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb`다.
HTTP 참조3.7.0-SNAPSHOT과 구분한다. 직전 개발 후보는 이전 공개 릴리즈가 아니며 고정 기준선을 대체하지 않는다.

후속 동일 요청 진단에서 v0.6.0의 ranking 결과 누락과2.19/3.7의 기본 scoring 차이를 확인했다.
초기 seed 코퍼스96조건에서 후보 total과 상위 점수는3.7과 일치하지만,
비어 있지 않은 동점 결과의 ID 선택은 다르다. 이 표는 동일 입력 부하의 측정이며
동일 정확도/동일 scoring 계약의 성능 보장이 아니다. 누적5% FAIL은 면제하지 않는다.
[버전별 explain과96조건 검증](native-ranking-audit-2026-09-10.md#참조-버전별-점수-차이와37-전체96조건-후속-검증).

5000문서/384 source values/4클라이언트/60초/seed13/3샤드,단일 replica0 및3노드 replica1 설정이다.
혼합 비중 write15/lexical15/ranking15/facet15/sort_filter10/nested10/refresh5,
vector/hybrid 및 별도 fallback diagnostic 비중0이다. Java heap512MiB이며 운영 보안/내구성 인증으로 확대하지 않는다.
실제 실행 설정과 입력 검증은 아래 plan.json/result.json 및 각 실행 summary.json을 따른다.

### 실행별 처리량

| 순서 | 실제 실행 역할 | 단일 ops/s | 3노드 ops/s | 요청 오류 |
| --- | --- | ---: | ---: | ---: |
| 0 | baseline | 737.577 | 914.417 | 0 |
| 1 | candidate | 493.412 | 770.722 | 0 |
| 2 | opensearch | 279.662 | 110.236 | 0 |
| 3 | opensearch | 277.883 | 113.211 | 0 |
| 4 | candidate | 488.200 | 755.954 | 0 |
| 5 | baseline | 735.355 | 903.483 | 0 |

### 누적 판정과 OpenSearch 비교

지연 변화율은 양수가 악화다. 처리량 변화율은 양수가 개선이며 OpenSearch 배수는 candidate/reference다.
반복1은00/01/02,반복2는05/04/03을 대조한다. 반올림 표시는 판정에 사용하지 않는다.

| 반복 | published 실패/44 | paired 실패/44 | baseline drift 실패/44 |
| --- | ---: | ---: | ---: |
| 1 | 37 | 29 | 3 |
| 2 | 38 | 34 | 5 |

| 반복 | 토폴로지 | v0.6.0 대비 처리량 | OpenSearch 대비 처리량 |
| --- | --- | ---: | ---: |
| 1 | single-node | -33.59% | 1.764x |
| 1 | three-node | -17.25% | 6.992x |
| 2 | single-node | -34.29% | 1.757x |
| 2 | three-node | -18.83% | 6.677x |

### 전체 시나리오 지연

모든 값은 mean/p95/p99 순서다. ms와 변화율을 각각 표기하며 시나리오를 생략하지 않았다.

| 반복 | 토폴로지/시나리오 | 후보 ms | 고정 v0.6.0 대비 | OpenSearch 대비 |
| --- | --- | --- | --- | --- |
| 1 | single-node/write | 3.073 / 5.799 / 7.270 | +6.97% / +9.92% / +6.41% | -76.66% / -71.99% / -77.90% |
| 1 | single-node/lexical | 7.290 / 22.030 / 29.324 | +77.76% / +146.20% / +113.33% | -26.75% / +21.19% / +5.58% |
| 1 | single-node/ranking | 14.138 / 36.689 / 98.071 | +120.47% / +195.68% / +464.89% | +12.31% / +63.35% / +164.49% |
| 1 | single-node/facet | 9.532 / 24.759 / 33.788 | +29.86% / +63.35% / +67.15% | -21.53% / +7.50% / +0.98% |
| 1 | single-node/sort_filter | 7.675 / 22.116 / 29.658 | +67.87% / +137.81% / +109.58% | -38.76% / -7.58% / -16.00% |
| 1 | single-node/nested | 6.366 / 12.886 / 18.889 | +0.33% / +6.09% / +7.45% | -41.34% / -34.64% / -33.00% |
| 1 | single-node/refresh | 7.553 / 14.099 / 17.515 | +2.25% / -5.24% / -3.58% | -85.48% / -86.77% / -89.87% |
| 1 | three-node/write | 3.156 / 5.921 / 7.649 | +6.30% / +8.09% / +5.19% | -90.15% / -91.24% / -93.59% |
| 1 | three-node/lexical | 4.281 / 10.583 / 17.563 | +21.57% / +56.89% / +73.36% | -82.88% / -81.07% / -83.08% |
| 1 | three-node/ranking | 7.391 / 19.457 / 27.954 | +64.83% / +142.12% / +147.29% | -77.52% / -74.42% / -79.69% |
| 1 | three-node/facet | 5.574 / 12.066 / 19.322 | +12.99% / +27.63% / +47.26% | -82.82% / -83.73% / -84.67% |
| 1 | three-node/sort_filter | 4.632 / 10.737 / 18.909 | +16.58% / +49.34% / +72.55% | -87.81% / -87.42% / -88.56% |
| 1 | three-node/nested | 4.356 / 7.900 / 11.066 | +0.12% / -0.26% / -2.67% | -84.04% / -88.04% / -90.85% |
| 1 | three-node/refresh | 8.861 / 18.142 / 23.279 | +5.67% / +5.10% / +5.61% | -92.80% / -92.71% / -93.12% |
| 2 | single-node/write | 3.068 / 5.789 / 7.385 | +6.81% / +9.75% / +8.11% | -77.59% / -73.61% / -78.61% |
| 2 | single-node/lexical | 7.295 / 22.259 / 29.266 | +77.88% / +148.77% / +112.91% | -26.49% / +21.13% / +4.24% |
| 2 | single-node/ranking | 14.414 / 38.478 / 102.076 | +124.77% / +210.10% / +487.97% | +12.17% / +59.59% / +169.94% |
| 2 | single-node/facet | 9.594 / 25.046 / 32.687 | +30.71% / +65.24% / +61.71% | -20.53% / +8.85% / -12.33% |
| 2 | single-node/sort_filter | 7.870 / 22.757 / 30.398 | +72.13% / +144.69% / +114.81% | -37.39% / -5.13% / -13.93% |
| 2 | single-node/nested | 6.432 / 13.452 / 20.592 | +1.36% / +10.75% / +17.14% | -41.49% / -33.93% / -37.29% |
| 2 | single-node/refresh | 7.650 / 14.171 / 18.198 | +3.56% / -4.76% / +0.18% | -85.06% / -88.14% / -89.49% |
| 2 | three-node/write | 3.220 / 6.091 / 7.984 | +8.46% / +11.19% / +9.80% | -89.42% / -90.43% / -92.45% |
| 2 | three-node/lexical | 4.253 / 10.279 / 17.932 | +20.77% / +52.38% / +77.01% | -82.34% / -81.53% / -79.82% |
| 2 | three-node/ranking | 7.453 / 19.778 / 27.592 | +66.21% / +146.13% / +144.08% | -76.80% / -72.99% / -77.59% |
| 2 | three-node/facet | 5.799 / 12.750 / 21.344 | +17.57% / +34.87% / +62.67% | -81.64% / -81.89% / -84.28% |
| 2 | three-node/sort_filter | 4.718 / 10.909 / 19.695 | +18.75% / +51.73% / +79.72% | -86.91% / -86.40% / -85.37% |
| 2 | three-node/nested | 4.435 / 8.124 / 12.039 | +1.93% / +2.56% / +5.89% | -83.36% / -85.66% / -89.16% |
| 2 | three-node/refresh | 9.283 / 19.698 / 25.892 | +10.70% / +14.11% / +17.47% | -92.51% / -92.01% / -93.71% |

### 실패 보존 및 후속 조치

반복1 published 실패: `single-node/throughput`, `three-node/throughput`, `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `single-node/lexical/mean`, `single-node/lexical/p95`, `single-node/lexical/p99`, `single-node/ranking/mean`, `single-node/ranking/p95`, `single-node/ranking/p99`, `single-node/facet/mean`, `single-node/facet/p95`, `single-node/facet/p99`, `single-node/sort_filter/mean`, `single-node/sort_filter/p95`, `single-node/sort_filter/p99`, `single-node/nested/p95`, `single-node/nested/p99`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/lexical/p95`, `three-node/lexical/p99`, `three-node/ranking/mean`, `three-node/ranking/p95`, `three-node/ranking/p99`, `three-node/facet/mean`, `three-node/facet/p95`, `three-node/facet/p99`, `three-node/sort_filter/mean`, `three-node/sort_filter/p95`, `three-node/sort_filter/p99`, `three-node/refresh/mean`, `three-node/refresh/p95`, `three-node/refresh/p99`.

반복1 baseline drift 실패: `single-node/facet/p99`, `three-node/sort_filter/p95`, `three-node/nested/p99`.

반복2 published 실패: `single-node/throughput`, `three-node/throughput`, `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `single-node/lexical/mean`, `single-node/lexical/p95`, `single-node/lexical/p99`, `single-node/ranking/mean`, `single-node/ranking/p95`, `single-node/ranking/p99`, `single-node/facet/mean`, `single-node/facet/p95`, `single-node/facet/p99`, `single-node/sort_filter/mean`, `single-node/sort_filter/p95`, `single-node/sort_filter/p99`, `single-node/nested/p95`, `single-node/nested/p99`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/lexical/p95`, `three-node/lexical/p99`, `three-node/ranking/mean`, `three-node/ranking/p95`, `three-node/ranking/p99`, `three-node/facet/mean`, `three-node/facet/p95`, `three-node/facet/p99`, `three-node/sort_filter/mean`, `three-node/sort_filter/p95`, `three-node/sort_filter/p99`, `three-node/nested/p99`, `three-node/refresh/mean`, `three-node/refresh/p95`, `three-node/refresh/p99`.

반복2 baseline drift 실패: `single-node/write/p95`, `three-node/ranking/p99`, `three-node/nested/p99`, `three-node/refresh/mean`, `three-node/refresh/p99`.

직전 개발 후보24e36d75의 별도 반복과 비교하면 ranking 평균은 단일21.867/22.047ms에서14.138/14.414ms,
3노드10.462/10.481ms에서7.391/7.453ms로 낮아졌다. 이는 별도 실행 간 관측이며 단독 인과 효과의 증명은 아니다.
고정 최초 v0.6.0 대비 누적 성능 실패는 그대로다. 기준선 변동도 면제 근거로 사용하지 않는다.
누적 회귀 전체를 이번 단위에 귀속해 제외하지 않으며,미해결 단독5% 이상 회귀가 입증되면 기존 제외/예외 규칙을 적용한다.
다음은 남은 source 점수 경로와 native 수집 경로를 진단한다. production 수정 단위마다 전체 engine/확장 HTTP/전체 반복 성능을 다시 실행해야 한다.

증거 디렉터리: `target/core-replacement-c06/native-compound-authority-repeated-full/`.

| 파일 | SHA-256 |
| --- | --- |
| result.json | b1a4800782b3e0d98b69c89ae9ed76df585d284a232e2a70fa5057d537722807 |
| plan.json | b669a1e1dbd6ae76babcd2d94ba91dce6f73ca9a2db93856dfccd03f828a98ac |
| 00-baseline/summary.json | 0d9cf0c0445ed576b1234e2c8c76153b66f246453dd56d6b8cd680f1395c2e89 |
| 01-candidate/summary.json | 06db35b74d78092f3a769b648cdf8320f362fef601e9f6c2d09fb8d3e66c9ed3 |
| 02-opensearch/summary.json | 87e8c75a1277f36bb643c8f1872bc68f786213eb9d9cc070930e6ad6d29c43d0 |
| 03-opensearch/summary.json | 601b29062b720240501ffb7f3b8903e481964d9e1f34499572c1640050ba46b0 |
| 04-candidate/summary.json | dd24742c1fe41f948ceb779dc7f2cbbaa63399791e8c6d8293ffd2707681b4ac |
| 05-baseline/summary.json | ebc6d4f4ea0e1714871d6adb67e3986e6a3607b4c80ac5d02edfc084e930c964 |
