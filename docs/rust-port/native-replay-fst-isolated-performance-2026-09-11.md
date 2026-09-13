# Native Replay FST Isolated 전체 반복 성능 (2026-09-11)

전체 6회, 12토폴로지에서 요청 오류는 0이다. `execution_inputs_verified=true`이고 모든
실행이 종료 코드 0이지만, 부모 결과는 `acceptance_established=false`,
`numeric_budget_passed=false`, 부모 exit1이다. TV1은 미완료이며 전체 계획 수락은
0/40, 릴리스는 보류한다.

후보는 이전 3a3c4023과 애플리케이션 소스가 같고 FST 의존성만 다르다.
FST patch는 별도 후보에만 적용했으며 루트 의존성으로 승격하지 않았다.

## 실행 정체성

- baseline: Steelsearch 3.7.0 (`build_hash=steelsearch-dev`),
  `/home/ubuntu/steelsearch/target/core-replacement-s01/baseline/steelsearch`,
  SHA-256 `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`.
- candidate: Steelsearch 3.7.0 (`build_hash=steelsearch-dev`),
  `/home/ubuntu/steelsearch/target/core-replacement-c06/native-replay-fst-isolated-candidate/artifacts/steelsearch`,
  SHA-256 `c224a57afbe039167ccba5bd5dd3ae648ecf444352338618dd4779499491aff9`.
- OpenSearch: 2.19.0, build hash `fd9a9d90df25bea1af2c6a85039692e815b894f5`,
  image `opensearchproject/opensearch@sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb`.
- HTTP 기능 참조는 OpenSearch 3.7.0-SNAPSHOT이고, 성능 비교 대상은 OpenSearch 2.19.0이다.
  기능 참조와 성능 참조를 동일성으로 해석하지 않는다.

고정 공개 baseline은 v0.6.0 `current.json` 그대로이며 재설정하지 않았다.
파일 SHA-256은 `d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788`이다.

## 실제 workload와 도구

5,000 documents, vector dimension 384, seed 13, 4 clients, 60초, timeout 10초,
3 shards, 단일 노드 replicas 0, 3노드 replicas 1, profile `minilm-knn`, Java heap
`-Xms512m -Xmx512m`를 사용했다. query mix는
`write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,refresh=5`이며
vector/hybrid 및 모든 fallback mix는 0이다. 두 토폴로지 모두 reset=true였다.

실제 실행 도구는 `/usr/bin/python3 tools/run-search-benchmark-matrix.py`이다.
`plan.json` SHA-256은 `7d1381e09cfbd0c9404ea27abd8a75cab6897987fd843ad82e35b86da608f258`이며,
runner/matrix 및 관련 도구 해시는 다음과 같다.

- `tools/run_core_performance_gate.py`: `ce077298ff4f6ed4c8ad6af2be1a1390f93bd4d19c21017bec0e7e00b5c5c65c`
- `tools/run-search-benchmark-matrix.py`: `ad0cbbeed326c654243904fc151fdb710209e121cd515dfae1a8ea9cdbcfff39`
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

## 실행별 처리량

| 순서 | 역할 | 단일 ops/s | 3노드 ops/s | 요청 오류 |
|---:|---|---:|---:|---:|
| 0 | baseline | 746.097 | 909.510 | 0 |
| 1 | candidate | 741.632 | 854.619 | 0 |
| 2 | opensearch | 282.157 | 110.383 | 0 |
| 3 | opensearch | 267.675 | 109.636 | 0 |
| 4 | candidate | 741.207 | 852.790 | 0 |
| 5 | baseline | 730.358 | 911.361 | 0 |

처리량 변화율은 candidate와 비교 기준의 `(candidate/reference - 1) * 100`이다.
published v0.6.0은 고정 공개 baseline, paired OpenSearch는 같은 반복의 측정 workload다.

| 반복 | 토폴로지 | published 대비 | paired OpenSearch 대비 |
|---:|---|---:|---:|
| 1 | single-node | -0.19% | +162.84% |
| 1 | three-node | -8.24% | +674.23% |
| 2 | single-node | -0.24% | +176.91% |
| 2 | three-node | -8.44% | +677.84% |

## 전체 지연

각 셀은 candidate `mean / p95 / p99` ms이다. 뒤의 두 셀은 각각 고정 공개 v0.6.0
대비와 같은 반복의 paired OpenSearch 대비 변화율이며, 양수는 지연 악화다.

| 반복 | 토폴로지/작업 | candidate ms | published 대비 | paired OS 대비 |
|---:|---|---:|---:|---:|
| 1 | single-node/write | 3.194 / 5.996 / 7.752 | +11.17% / +13.66% / +13.47% | -76.43% / -71.00% / -75.97% |
| 1 | single-node/lexical | 4.206 / 8.371 / 12.401 | +2.57% / -6.44% / -9.79% | -57.51% / -53.78% / -56.65% |
| 1 | single-node/ranking | 5.942 / 10.634 / 14.850 | -7.35% / -14.30% / -14.46% | -52.89% / -54.98% / -62.41% |
| 1 | single-node/facet | 7.386 / 14.750 / 19.183 | +0.62% / -2.69% / -5.10% | -38.26% / -36.75% / -49.06% |
| 1 | single-node/sort_filter | 4.754 / 9.069 / 12.525 | +3.98% / -2.48% / -11.49% | -61.22% / -60.75% / -62.57% |
| 1 | single-node/nested | 6.352 / 11.634 / 14.869 | +0.10% / -4.22% / -15.42% | -41.21% / -41.48% / -54.36% |
| 1 | single-node/refresh | 7.154 / 13.254 / 16.383 | -3.16% / -10.93% / -9.81% | -85.76% / -88.14% / -89.58% |
| 1 | three-node/write | 3.341 / 6.121 / 8.111 | +12.53% / +11.74% / +11.54% | -89.44% / -91.08% / -91.95% |
| 1 | three-node/lexical | 3.881 / 7.376 / 11.288 | +10.21% / +9.34% / +11.42% | -84.90% / -87.53% / -88.61% |
| 1 | three-node/ranking | 5.159 / 9.025 / 12.962 | +15.06% / +12.31% / +14.66% | -84.10% / -88.33% / -89.70% |
| 1 | three-node/facet | 5.231 / 9.879 / 13.739 | +6.04% / +4.50% / +4.71% | -84.03% / -86.48% / -89.92% |
| 1 | three-node/sort_filter | 4.217 / 7.569 / 10.803 | +6.14% / +5.26% / -1.42% | -88.35% / -91.28% / -90.51% |
| 1 | three-node/nested | 4.657 / 8.389 / 12.109 | +7.04% / +5.91% / +6.51% | -83.04% / -86.73% / -88.94% |
| 1 | three-node/refresh | 8.768 / 17.951 / 23.423 | +4.56% / +3.99% / +6.26% | -93.00% / -92.95% / -93.35% |
| 2 | single-node/write | 3.201 / 5.976 / 7.794 | +11.43% / +13.28% / +14.09% | -76.77% / -73.65% / -76.31% |
| 2 | single-node/lexical | 4.288 / 8.500 / 12.247 | +4.56% / -5.01% / -10.91% | -58.68% / -57.09% / -62.34% |
| 2 | single-node/ranking | 5.950 / 10.566 / 14.199 | -7.22% / -14.85% / -18.21% | -55.47% / -59.78% / -65.54% |
| 2 | single-node/facet | 7.346 / 14.721 / 18.458 | +0.08% / -2.88% / -8.69% | -41.52% / -38.16% / -50.50% |
| 2 | single-node/sort_filter | 4.686 / 8.722 / 12.407 | +2.49% / -6.22% / -12.33% | -64.03% / -64.19% / -67.95% |
| 2 | single-node/nested | 6.306 / 11.759 / 15.260 | -0.63% / -3.19% / -13.19% | -43.81% / -44.50% / -57.66% |
| 2 | single-node/refresh | 7.249 / 12.901 / 15.758 | -1.86% / -13.30% / -13.26% | -86.72% / -88.96% / -89.89% |
| 2 | three-node/write | 3.352 / 6.265 / 7.954 | +12.91% / +14.36% / +9.39% | -89.25% / -90.40% / -92.24% |
| 2 | three-node/lexical | 3.859 / 7.270 / 10.623 | +9.61% / +7.77% / +4.86% | -85.68% / -88.72% / -91.01% |
| 2 | three-node/ranking | 5.134 / 8.852 / 12.510 | +14.50% / +10.15% / +10.67% | -84.56% / -88.53% / -89.26% |
| 2 | three-node/facet | 5.307 / 10.058 / 14.886 | +7.58% / +6.39% / +13.45% | -83.46% / -86.63% / -87.39% |
| 2 | three-node/sort_filter | 4.202 / 7.618 / 11.175 | +5.76% / +5.95% / +1.97% | -89.07% / -91.37% / -92.30% |
| 2 | three-node/nested | 4.648 / 8.643 / 12.255 | +6.85% / +9.11% / +7.79% | -83.08% / -86.19% / -87.37% |
| 2 | three-node/refresh | 8.858 / 17.900 / 22.426 | +5.63% / +3.70% / +1.74% | -92.76% / -93.26% / -93.91% |

## 판정과 안전 확인

| 반복 | published 실패 / 44 | paired 실패 / 44 | baseline drift 실패 / 44 |
|---:|---:|---:|---:|
| 1 | 20 | 17 | 3 |
| 2 | 21 | 13 | 5 |

`result.json`의 `published`, `paired`, `baseline_drift` 실패 수를 그대로 기록했다.
고정 누적 기준은 throughput 95% 이상, latency mean/p95/p99 각각 105% 이하이며,
단일 지표 실패를 다른 지표의 개선으로 상쇄하지 않는다. baseline drift도 존재하므로
모든 candidate 결과를 단일 원인으로 귀속하지 않는다.

OpenSearch 비교는 이 문서의 실제 workload에서 측정한 상대값일 뿐 전체 API·기능·운영
패리티의 증명이 아니다. 기능 참조 3.7과 성능 참조 2.19의 차이는 별도로 남긴다.
이전 baseline의 ranking 응답 차이와 누락은 기능 및 응답량 차이로 취급하며, 이 보고서의
성능 비교는 동일 정확도·응답량을 보장하지 않는다. 이 차이는 고정 누적 5% 예산 실패를
면제하지 않는다.

안전 검사는 설정 변경 없이 읽기 전용으로 수행되었고, disk threshold를 완화하지 않았다.
측정에 기록된 OpenSearch 기본값은 `disk.threshold_enabled=true`, `low=85%`,
`high=90%`, `flood_stage=95%`, `watermark.enable_for_single_data_node=false`이다.
blocks와 settings의 관찰 결과만 기록한 것이며, 이는 포괄적인 보안·내구성·운영 안전성
인증이 아니다.

## 증거와 무결성

- `result.json` SHA-256: `496a39915dfb3811991c621dc19f03982ac30f565d54979997e22a9597b3800f`.
- `plan.json` SHA-256: `7d1381e09cfbd0c9404ea27abd8a75cab6897987fd843ad82e35b86da608f258`.
- summary SHA-256: 00 `831b9865450a3e3f490879670499f701be70baa07f3ba9ad2483172d22e71039`,
  01 `9493e02fe41e26cd72033baba95b2b144b6353194a6ca5d8d26616d1c24f03ab`,
  02 `9f5733f761bb4c6592c016a4e70bef7a3ccfa89a73e09bd4051d08d1bd94ff14`,
  03 `fc6946e1cff5cb62e42917db279e82d2fe5d52f027d6cadfe5a8c2564244a689`,
  04 `40adafa75b00760a8d44b8d61546317dd70fc32afd6a2a13686bede76810d19a`,
  05 `6a00f02d590255e399164adce66e083d1e3ccb6c5bf38d230088df30ecb7fea2`.
- 고정 공개 baseline `docs/releases/v0.6.0/current.json` SHA-256:
  `d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788`.

결론: 요청 오류0과 입력 검증은 확인했지만, 수치 예산은 실패했다. TV1은 미완료,
전체 계획 수락0/40이며 새 release를 만들지 않는다.
