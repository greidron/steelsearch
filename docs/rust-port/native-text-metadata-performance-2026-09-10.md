# Native Text Metadata 전체 반복 성능 (2026-09-10)

전체6회/12토폴로지 요청 오류0,입력 검증 true,종료 후 동결 소스 검증 통과다.
부모 exit1,numeric_budget_passed=false,구현 단위 미완료,수락0/40,릴리즈 보류다.

후보: `6086c31c434e1defd8bdb936d2326bbddfb193b12fd69d5c5693e15e3aa31d39`.
고정 v0.6.0: `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`.
공개 기준 증거 docs/releases/v0.6.0/current.json SHA-256:
`d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788`.
성능 OpenSearch2.19 이미지: `opensearchproject/opensearch@sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb`.
기능 참조3.7과 기본 scoring 규칙이 다르며,기준선의 초기 ranking 결과 누락도
[진단 기록](native-ranking-audit-2026-09-10.md)에 보존했다. 동일 정확도/응답량의 보장은 아니며 누적5% FAIL을 면제하지 않는다.

5000문서,384 source values,4클라이언트,60초,seed13,3샤드,
단일 replica0/3노드 replica1,write15/lexical15/ranking15/facet15/sort_filter10/nested10/refresh5다.
vector/hybrid 및 별도 fallback diagnostic 비중0,Java heap512MiB이며 운영 보안/내구성 인증이 아니다.
실제 실행 설정/동등 입력 검증은 plan.json/result.json 및 각 summary.json을 따른다.
측정 중 다른 빌드/시험/진단/코드 변경을 하지 않았다. 측정 전 재생성 가능한 release 캐시683.4MiB만 정리했다.

## 실행별 처리량

| 순서 | 역할 | 단일 ops/s | 3노드 ops/s | 요청 오류 |
| --- | --- | ---: | ---: | ---: |
| 0 | baseline | 741.106 | 921.061 | 0 |
| 1 | candidate | 737.868 | 853.098 | 0 |
| 2 | opensearch | 285.593 | 113.052 | 0 |
| 3 | opensearch | 279.673 | 113.698 | 0 |
| 4 | candidate | 745.210 | 844.789 | 0 |
| 5 | baseline | 738.786 | 923.135 | 0 |

## 누적 판정

반복1은00/01/02,반복2는05/04/03이다. throughput95% 이상과 각 mean/p95/p99105% 이하를 각각 적용한다.
표시는 반올림하며 판정은 원본 값으로 수행한다. 다른 지표의 개선으로 실패를 상쇄하지 않는다.

| 반복 | published 실패/44 | paired 실패/44 | baseline drift 실패/44 |
| --- | ---: | ---: | ---: |
| 1 | 22 | 20 | 2 |
| 2 | 25 | 23 | 3 |

| 반복 | 토폴로지 | 고정 v0.6.0 대비 처리량 | OpenSearch 대비 처리량 |
| --- | --- | ---: | ---: |
| 1 | single-node | -0.69% | 2.584x |
| 1 | three-node | -8.40% | 7.546x |
| 2 | single-node | +0.30% | 2.665x |
| 2 | three-node | -9.30% | 7.430x |

## 전체 지연

mean/p95/p99 순서,지연 변화율 양수는 악화다. 모든7시나리오/2토폴로지/2반복을 포함한다.

| 반복 | 토폴로지/시나리오 | 후보 ms | 고정 v0.6.0 대비 | OpenSearch 대비 |
| --- | --- | --- | --- | --- |
| 1 | single-node/write | 3.195 / 5.886 / 7.601 | +11.20% / +11.58% / +11.27% | -75.42% / -70.97% / -74.01% |
| 1 | single-node/lexical | 4.275 / 8.644 / 12.301 | +4.25% / -3.39% / -10.51% | -56.84% / -54.24% / -56.16% |
| 1 | single-node/ranking | 6.000 / 10.775 / 14.228 | -6.44% / -13.17% / -18.04% | -52.23% / -53.51% / -61.57% |
| 1 | single-node/facet | 7.453 / 15.137 / 19.599 | +1.54% / -0.13% / -3.04% | -37.67% / -32.88% / -45.86% |
| 1 | single-node/sort_filter | 4.764 / 9.040 / 12.753 | +4.21% / -2.80% / -9.88% | -61.08% / -60.17% / -65.71% |
| 1 | single-node/nested | 6.232 / 11.531 / 15.695 | -1.79% / -5.06% / -10.72% | -41.49% / -39.91% / -51.09% |
| 1 | single-node/refresh | 7.240 / 13.218 / 16.417 | -1.99% / -11.17% / -9.63% | -85.44% / -87.75% / -89.17% |
| 1 | three-node/write | 3.337 / 6.281 / 8.060 | +12.40% / +14.65% / +10.85% | -89.26% / -90.14% / -93.05% |
| 1 | three-node/lexical | 3.836 / 7.225 / 10.570 | +8.94% / +7.12% / +4.34% | -84.26% / -87.82% / -90.65% |
| 1 | three-node/ranking | 5.115 / 8.769 / 12.562 | +14.07% / +9.13% / +11.12% | -84.19% / -88.50% / -90.37% |
| 1 | three-node/facet | 5.309 / 10.217 / 13.738 | +7.62% / +8.07% / +4.71% | -83.32% / -86.12% / -90.71% |
| 1 | three-node/sort_filter | 4.232 / 7.653 / 10.983 | +6.53% / +6.44% / +0.22% | -88.59% / -90.66% / -93.08% |
| 1 | three-node/nested | 4.637 / 8.629 / 12.586 | +6.58% / +8.95% / +10.70% | -82.77% / -86.00% / -87.73% |
| 1 | three-node/refresh | 8.951 / 18.521 / 23.810 | +6.74% / +7.30% / +8.02% | -92.53% / -92.44% / -93.07% |
| 2 | single-node/write | 3.178 / 5.914 / 7.470 | +10.63% / +12.12% / +9.35% | -76.33% / -71.34% / -76.17% |
| 2 | single-node/lexical | 4.178 / 8.384 / 12.165 | +1.88% / -6.30% / -11.50% | -57.72% / -54.54% / -58.94% |
| 2 | single-node/ranking | 5.944 / 10.566 / 14.161 | -7.32% / -14.84% / -18.43% | -53.12% / -56.07% / -65.57% |
| 2 | single-node/facet | 7.349 / 14.554 / 19.030 | +0.12% / -3.98% / -5.86% | -39.08% / -38.85% / -53.28% |
| 2 | single-node/sort_filter | 4.779 / 9.167 / 12.727 | +4.53% / -1.43% / -10.06% | -61.82% / -61.19% / -67.01% |
| 2 | single-node/nested | 6.193 / 11.546 / 15.117 | -2.41% / -4.94% / -14.01% | -41.70% / -39.12% / -53.66% |
| 2 | single-node/refresh | 7.202 / 13.294 / 17.056 | -2.51% / -10.66% / -6.11% | -86.15% / -88.39% / -88.76% |
| 2 | three-node/write | 3.399 / 6.344 / 8.254 | +14.47% / +15.81% / +13.51% | -88.92% / -89.76% / -91.23% |
| 2 | three-node/lexical | 3.852 / 7.318 / 10.642 | +9.38% / +8.49% / +5.04% | -84.87% / -87.94% / -89.07% |
| 2 | three-node/ranking | 5.152 / 8.870 / 12.655 | +14.88% / +10.38% / +11.95% | -83.53% / -87.39% / -88.70% |
| 2 | three-node/facet | 5.357 / 10.104 / 14.232 | +8.61% / +6.88% / +8.47% | -82.59% / -85.62% / -87.91% |
| 2 | three-node/sort_filter | 4.264 / 7.753 / 11.527 | +7.31% / +7.83% / +5.19% | -88.19% / -90.14% / -91.52% |
| 2 | three-node/nested | 4.676 / 8.538 / 12.328 | +7.48% / +7.80% / +8.43% | -82.60% / -86.36% / -88.50% |
| 2 | three-node/refresh | 9.093 / 18.655 / 24.931 | +8.43% / +8.07% / +13.11% | -92.59% / -92.86% / -92.42% |

## 실패 및 후속 조치

반복1 published 실패: `three-node/throughput`, `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/lexical/p95`, `three-node/ranking/mean`, `three-node/ranking/p95`, `three-node/ranking/p99`, `three-node/facet/mean`, `three-node/facet/p95`, `three-node/sort_filter/mean`, `three-node/sort_filter/p95`, `three-node/nested/mean`, `three-node/nested/p95`, `three-node/nested/p99`, `three-node/refresh/mean`, `three-node/refresh/p95`, `three-node/refresh/p99`.

반복1 baseline drift 실패: `single-node/write/p99`, `three-node/sort_filter/p99`.

반복2 published 실패: `three-node/throughput`, `single-node/write/mean`, `single-node/write/p95`, `single-node/write/p99`, `three-node/write/mean`, `three-node/write/p95`, `three-node/write/p99`, `three-node/lexical/mean`, `three-node/lexical/p95`, `three-node/lexical/p99`, `three-node/ranking/mean`, `three-node/ranking/p95`, `three-node/ranking/p99`, `three-node/facet/mean`, `three-node/facet/p95`, `three-node/facet/p99`, `three-node/sort_filter/mean`, `three-node/sort_filter/p95`, `three-node/sort_filter/p99`, `three-node/nested/mean`, `three-node/nested/p95`, `three-node/nested/p99`, `three-node/refresh/mean`, `three-node/refresh/p95`, `three-node/refresh/p99`.

반복2 baseline drift 실패: `single-node/write/p95`, `single-node/write/p99`, `three-node/ranking/p99`.

단일 노드 throughput은고정 기준 대비-0.692%/+0.296%로 통과하지만 write mean/p95/p99는 두 번 모두 실패다.
3노드 throughput은-8.404%/-9.296%로 실패하며 검색/쓰기/refresh 지연도 남는다.
직전 개발 후보31281a3d의 별도 측정 단일493.412/488.200,3노드770.722/755.954ops/s보다 개선됐지만,
직전 후보는 공개 릴리즈가 아니고 최초 고정 기준을 대체하지 않는다. 별도 측정 간 차이를 단독 인과효과로 확대하지 않는다.
전체 engine955통과,HTTP2601=2351통과250실패로 상태변경0이다. 기능 실패와 누적 성능 실패를 유지한다.
다음은 남은 write 및3노드 비용 진단이며,새 수정 단위마다 전체 engine/HTTP/반복 성능 gate를 재실행한다.
단독5% 이상 미해결 구현의 제외/예외 규칙을 유지하고 누적 회귀 전체를 이번 단위에 임의 귀속하지 않는다.

## 증거

기준 디렉터리: target/core-replacement-c06/native-text-metadata-repeated-full/.

| 파일 | SHA-256 |
| --- | --- |
| result.json | c5f95b264ff03b5b4c71ffc7caa55e3ec2c854382a9681aebd29b58a04d660e0 |
| plan.json | 34aee89fa0667ff9dc7983e081c72620cf42d10748b822f7972a0230ad353e5e |
| 00-baseline/summary.json | cd5d53563758b3c08d4e49e4c282dcf4a8f21a99b4e911236a7c75f44f4941fe |
| 01-candidate/summary.json | f4c27646f9da89d3927b856b9d2e827f2db7dc7576fa1c76670919cc634159f3 |
| 02-opensearch/summary.json | 76d0dde7ff784e72afcfb01a6f32e0abe8366bb9e5e0d8b580d9414e0ca8ab44 |
| 03-opensearch/summary.json | 574868a745702d702ddd28ef3404850d246f6f2428b9b3c1d6c78bc4118b9705 |
| 04-candidate/summary.json | 47ee0cd68823eddbf3d1f5261b30f3173488235de2a26188d7932895db9123af |
| 05-baseline/summary.json | 6f49b16b3588041330facecf086a32b3161948476c73e4496dce6ed30f223f0b |

