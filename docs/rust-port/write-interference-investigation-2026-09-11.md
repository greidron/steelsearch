# Write Interference Investigation

상태: 진단 완료. 전체 게이트는 여전히 FAIL. 서버 소스 변경 및 구현 수락 없음.
플러그인은 제외한다.
상위 계획은 [core replacement](core-replacement-implementation-plan-2026-09-07.md),
출발 증거는 [native 조사](native-columnar-merge-investigation-2026-09-11.md)와
[a5b38b49 전체 게이트](native-buffered-bitpack-performance-2026-09-11.md)다.

## 확인한 사실

- a5b38b49 전체 mixed 게이트는 FAIL이다. 고정 v0.6.0 대비3노드 처리량
  -5.61%/-7.27%, write mean 약+10~14%다. 동시 기준선과 비교해도 write 회귀가 남는다.
- 같은 서버의3노드 write-only ABBA는 양쪽 mean3.34~3.36ms로 큰 차이가 없었다.
  이 진단은 mixed FAIL을 면제하거나 모든 쓰기 조건의 동등성을 증명하지 않는다.
- 실제 부하의 PUT은 refresh=false이며 baseline/candidate runtime의 native
  적용 및 per-write 저장 지연 설정이 같다. 해당 PUT에서 직접 native commit/
  per-write fsync를 실행한다고 가정하지 않는다. 설정은 변경하지 않는다.
- refresh handler는 문서 identity snapshot을 캡처하고 native replay/refresh 후
  동일 Arc identity만 refreshed 처리한다. 이 가시성 보호를 제거하지 않는다.
  documents_state mutex와 native refresh의 호출 경계는 소스에서 구분되어 있다.

## 진단 단위

1. 서버 실행 파일은 기존 artifact 그대로 사용하고 추가 빌드하지 않는다.
   baseline SHA `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`,
   candidate SHA `a5b38b4932a3386fc495800578f6d76970ca3882437b93f3c60cfc280ec6c6b8`.
2. 기존 matrix command를 재사용해3노드/45초/5000문서/384값/4클라이언트/
   3샤드/replica1/seed13/reset=true 및 runtime evidence 수집을 유지한다.
   두 query mix는 가중치다: write_refresh=`write=15,refresh=5`,
   write_search=`write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10`.
   각 조건은 baseline,candidate,candidate,baseline 순서이며 총8회다.
3. 계획·명령·도구·실행 파일 해시를 시작 전에 고정하고 매 실행 전후 검증한다.
   자식 오류/요청 오류/입력 변화/불완전 runtime 또는 결과는 중단 사유다.
   재시도하지 않고 실패 실행도 보존한다. 새 출력 디렉터리를 사용한다.
4. Terra는 격리 wrapper와 mock 시험을 작성한다. 부모는 workload/identity 검증을
   검토한다. 시험은 실제 서버 실행 없이 성공·자식 실패·입력 변조·identity/config
   오류 등을 확인한다. 측정 중 에이전트·빌드·시험·다른 진단·편집을 중단한다.
5. 조건 간 요청 비중·가시 문서 수·실제 작업량이 달라질 수 있으므로 절대 처리량을
   같은 workload의 개선율로 비교하지 않는다. 각 조건 내 후보/기준선 반복 차이로
   후속 요청 계측 또는 native 조사 위치를 선택한다. 간섭의 구체적인 lock/CPU/
   scheduler 원인은 별도 증거가 필요하며 이 결과만으로 확정하지 않는다.

## 구현 성능 게이트

이 진단은 구현 단위 완료나 릴리즈 수락이 아니다. 후속 구현마다 전체 engine/node,
확장 HTTP와 전체 non-plugin6회/12토폴로지 벤치마크를 실행한 뒤 완료를 판단한다.
최초 v0.6.0을 고정 누적 기준선으로 사용하며 각 topology 처리량>=95%, 모든
scenario mean/p95/p99<=105%를 따로 확인한다. 개선 항목으로 초과 항목을 상쇄하지
않고 비교 조건·내구성·보안·자원 설정과 실제 실행 파일 identity를 보존한다.
초과 시 최적화·전체 재실행하며 상위 계획의 제외/명시적 예외 규칙을 적용한다.
직전 published release/OpenSearch 비교도 유지하고 원본 기준선을 재설정하지 않는다.

## 완료된 진단 증거

이는 `native-buffered-write-ablation`의 완료된 3-node ABBA 진단 결과이며,
고정 v0.6.0 전체 게이트의 수락 증거가 아니다. 서버 설정이나 서버 소스는 변경하지
않았다. qps와 write latency의 원시 측정값은 다음과 같다 (latency ms).

| run | qps | write mean | write p95 | write p99 |
| --- | ---: | ---: | ---: | ---: |
| 00 write_refresh baseline | 804.627 | 3.272 | 6.282 | 8.182 |
| 01 write_refresh candidate | 832.023 | 3.303 | 6.162 | 8.186 |
| 02 write_refresh candidate | 816.256 | 3.294 | 6.310 | 8.120 |
| 03 write_refresh baseline | 804.908 | 3.251 | 6.299 | 8.297 |
| 04 write_search baseline | 1316.510 | 2.749 | 4.627 | 5.928 |
| 05 write_search candidate | 1211.834 | 3.011 | 4.951 | 6.077 |
| 06 write_search candidate | 1229.840 | 2.945 | 4.862 | 5.934 |
| 07 write_search baseline | 1320.825 | 2.732 | 4.560 | 5.644 |

아래는 각 enabled operation의 candidate/baseline latency delta (`candidate / baseline - 1`)다.
모든 조건의 모든 enabled scenario를 포함한다.

| pair | operation | mean | p95 | p99 |
| --- | --- | ---: | ---: | ---: |
| 1/0 | refresh | -7.52% | -13.32% | -10.51% |
| 1/0 | write | +0.96% | -1.90% | +0.06% |
| 2/3 | refresh | -4.16% | -9.35% | -10.92% |
| 2/3 | write | +1.33% | +0.16% | -2.14% |
| 5/4 | facet | +5.69% | +1.72% | -3.29% |
| 5/4 | lexical | +10.58% | +3.45% | +1.53% |
| 5/4 | nested | +8.73% | +6.63% | +3.33% |
| 5/4 | ranking | +8.88% | +7.65% | +3.60% |
| 5/4 | sort_filter | +9.57% | +3.18% | +2.49% |
| 5/4 | write | +9.52% | +7.00% | +2.50% |
| 6/7 | facet | +5.51% | +3.31% | +6.50% |
| 6/7 | lexical | +8.40% | +4.40% | +3.71% |
| 6/7 | nested | +7.12% | +6.81% | +8.56% |
| 6/7 | ranking | +8.14% | +10.17% | +10.59% |
| 6/7 | sort_filter | +8.13% | +5.65% | +5.09% |
| 6/7 | write | +7.80% | +6.63% | +5.13% |

`write_refresh`의 write mean은 두 pair에서 +0.96%, +1.33%로 사실상 write
회귀를 재현하지 않았다. 반면 `write_search`는 refresh를 명시하지 않은 mix에서도
write mean +9.52%, +7.80% 회귀를 재현했다. 이 결과는 정확한 CPU/lock 원인이나
단일 구현 귀속을 확정하지 않는다. 따라서 진단은 완료됐지만 전체 게이트는 계속
FAIL이며, 이를 구현 수락 또는 고정 게이트 통과로 사용하지 않는다.

처리량의 동일 pair 변화는1/0 +3.40%,2/3 +1.41%,5/4 -7.95%,6/7 -6.89%다.
8회 모두 자식 종료0/요청 오류0이며 입력 불변 및 내부 결과 검증=true다.
부모가 완료 후8개 결과를 다시 검증하고 plan/summary/실행 파일/도구 해시를 확인했다.

추가 관찰: 네 `write_search` run 모두 `scenario.resource_usage`의
`refresh_tantivy_{commit,doc_id_lookup,document_add,reload}_nanos.delta`가 0이다.
이는 관찰한 endpoint의 값일 뿐 3개 노드 전체 집계를 뜻하지 않는다. 고정된 candidate의
`standalone_runtime.rs`에서는 native dispatch(15138)가 `documents_state` fallback
snapshot(15217)보다 앞서며, native helper(15803)는 그 지점에서 `native_engine.search`를
호출하고 `documents_state`를 잡지 않는다. 따라서 공통 slowdown만으로 fallback 또는 lock을
원인으로 가정하지 않는다.

다음 진단은 정확히 이 `write_search` mix, 동일 binary/settings, ABBA 순서를 사용해야 하며
mixed 또는 write-only 결과를 동등한 대체 증거로 재사용하지 않는다. 기존
`run-core-cpu-diagnostic.py`는 `operation` 선택지만 받고 임의 `query_mix`를 받지 않으므로,
wrapper/support는 측정 전에 명시적으로 검증해야 한다.

### CPU 진단 사전 계획

- 기존 CPU 도구에 임의 문자열 대신 `write_search` 고정 preset을 추가한다.
  query mix는 위 ablation과 정확히 같으며 기존 mixed/단독 operation은 유지한다.
- `target/core-replacement-c06/run-buffered-write-search-cpu-repeat.py`는 보존된
  write-only wrapper를 재사용하되 operation만 변경한다. 동일 baseline/candidate의
  ABBA4회,3노드45초,CPU49Hz20초,DWARF8192로 고정한다. 출력은 새 경로
  `target/core-replacement-c06/native-buffered-write-search-cpu-abba`다.
- Luna가 고정 preset/기존 옵션 유지 시험을 보강하고 부모가 검증한다.
  측정 중 에이전트/편집/빌드/시험은 중단한다. 오류 실행도 보존하고 재시도하지 않는다.
  CPU 표본은 off-CPU 대기나 HTTP 지연 원인의 직접 증거가 아니며 서버 필터의
  표본 분모를 명시한다. 도구 변경 후 새 입력 해시를 기록하고 과거 증거는 유지한다.

측정 artifact SHA-256:

### CPU 진단 완료

위 CPU ABBA4회도 종료0,요청 오류0,입력 불변=true다. preset 시험을 포함한
CPU 도구16개 시험이 통과했다. 서버 소스/실행 파일 변경은 없다.

| run | qps | write mean ms | write p95 ms | write p99 ms | server CPU s | client CPU s | 관측 s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 00 baseline | 1298.110 | 2.795911 | 4.610558 | 5.752666 | 20.56 | 20.11 | 20.793 |
| 01 candidate | 1216.329 | 2.989454 | 4.857373 | 6.118658 | 18.12 | 20.54 | 20.734 |
| 02 candidate | 1203.521 | 3.022442 | 4.962496 | 6.117603 | 18.02 | 20.51 | 20.735 |
| 03 baseline | 1297.379 | 2.782596 | 4.598558 | 5.703610 | 20.66 | 20.11 | 20.797 |

CPU 시간은 약20초 관측창의 process stat delta이며 latency/qps는45초 전체다.
서버 CPU는3개 프로세스 합계다. 두 창의 실제 요청 건수를 같다고 가정하거나
이 표로 정확한 request당 CPU를 계산하지 않는다. 후보의 관측 서버 CPU가 더
작아도 HTTP latency는 크다. CPU 포화/특정 mutex/클라이언트 병목을 확정하지 않는다.

각 run의 `server-relative-self-report.txt`, `client-relative-self-report.txt`는
`perf report --stdio --no-children --percentage relative --sort symbol --pid ...`로
생성했다. 표본 분모는 각각 필터한 서버/클라이언트이며 CPU 밖 대기는 포함하지 않는다.
서버 보고서의 lost samples는4회 모두0이다. 공통 상위 경로는 memcmp/할당/JSON
직렬화/집계다. 이 표본만으로 특정 코드 변경의 회귀 귀속을 입증하지 않았다.

다음 확인은 동일 요청의 실제 응답 크기·hit 수·source 형태와 클라이언트 처리량이다.
`tools/run-http-load-baseline.py:843`은 response.read 후 decode_body를 호출하며,
decode_body는 JSON 해석을 수행한다. 아래 후속 진단에서 응답량 차이를 측정했다.
응답 내용을 줄이거나 정확도/안전성을 변경해 게이트를 맞추지 않는다.
CPU 진단도 전체 구현 성능 게이트를 대체하지 않으며0/40,성능 FAIL,릴리즈 보류다.

CPU plan SHA `faa5398ca746b52a827f4d56695211f91c1c75dfde65d2e049c869a5c6547d3c`,
result SHA `de447476e480edc86d0eea0a827abdf6f52bef0e88684cfac7660047770e76d5`.
result에는 각 diagnostic/summary 해시가 보존되어 있다.

### 원본 비프로파일 ablation 해시

| artifact | sha256 |
| --- | --- |
| plan.json | `b01e56802103e5edefe696512f5b3be455298412ff60eed969393d5b0b0d99ac` |
| result.json | `db4d075effdcfdc503cfe1e20a3184a07614cff39d873b74e50b132bc1ff4842` |
| 00-write_refresh-baseline/summary.json | `b99117d1953e3e0d2426aacd2e7c04aead81f829b43f297e471297c2e70a9c45` |
| 01-write_refresh-candidate/summary.json | `2378abfc9bba9c08f1ef4280f3fcbeb256bd17b9bbc74b810010bd7f0a2caead` |
| 02-write_refresh-candidate/summary.json | `86b3e223b8880665c6eefa6dc9e3a6e8f3a0140c72874b0dcf6c043a2a606533` |
| 03-write_refresh-baseline/summary.json | `e8bf5eaa9fa79104cb9657fb08c097f114c8fa531ef37121b40a414441386f0e` |
| 04-write_search-baseline/summary.json | `47fb7d86ee627fe1299dfe90ff2039bcefcd6620bc0e612016e7954e59f8f0b6` |
| 05-write_search-candidate/summary.json | `f5f764faa82de9c38d50562d52da37b744ba88ae290df8d2787705cb661547c4` |
| 06-write_search-candidate/summary.json | `95ddd12aaf6d7d9428487fcf388d13a3a76d1c0a4ae7df9742f123f7740160d2` |
| 07-write_search-baseline/summary.json | `650a6e09f390146d4f95d90a523b2b01e93840600fa2d15523c6d941bd00a9f2` |

### 완료된 응답 형태 증거

`target/core-replacement-c06/native-buffered-response-shapes/`의 완료된 진단은
seed된 코퍼스에 대해 고정 검색 요청을 순차 실행한 것이다. 동시 workload 재현이
아니며, live write는 실행하지 않았다. 각 type의 RNG seed13 요청20개를 reset=true
3-node에 각각 보냈으므로 아래 평균은 scenario마다60응답의 raw HTTP body bytes이고,
hit 수는 그60응답에서 실제 반환된 hit의 합계다.

| scenario | baseline 평균 bytes | candidate 평균 bytes | baseline 반환 hit 합계 | candidate 반환 hit 합계 |
| --- | ---: | ---: | ---: | ---: |
| lexical | 3798.77 | 3800.08 | 80 | 80 |
| ranking | 160.00 | 10637.75 | 0 | 230 |
| facet | 1655.42 | 1655.42 | 0 | 0 |
| sort_filter | 6085.55 | 6085.55 | 130 | 130 |
| nested | 20529.08 | 20529.08 | 450 | 450 |

ranking의 160B/0-hit baseline과10637.75B/230-hit candidate 차이는 새 발견이나
전체 a5 correctness 증명이 아니다. 기준선 ranking 결과 누락은 이미
[native ranking audit의 동일 요청 비교](native-ranking-audit-2026-09-10.md#동일96개-ranking-요청의-반환량-차이-확인)에
기록되어 있다. 이 응답 형태 차이만으로 write_search 회귀의 서버 실행 비용이나
원인을 귀속하지 않으며, parent는 별도로 보존 raw JSON의 offline decode 비용을
검사한다.

`result.json`은 baseline/candidate 각각300개, 합계600개 raw response의 파일명과
SHA-256을 보존한다. execution tool inputs verified=true이며, plan/result와 raw
response는 이 진단 출력 아래에 보존된다. 이는 latency gate도 아니고 전체 성능
gate 또는 구현 수락 증거도 아니다.

제한: type당 표본은20개뿐이고 RNG는 seed13/reset=true로 고정했으며3-node만
관측했다. live write, 동시 workload, latency 측정 및 gate 판정은 없고 모든 query
조합을 포괄하지 않는다.

| artifact | SHA-256 |
| --- | --- |
| `plan.json` | `2c479a35afda46ecaecff7683e63c95de2e1b7f73e59f072f061a97f1f243d9d` |
| `result.json` | `f62c19efbdd2a1c9f74262aba9e97cfd949dec97a15816f1c712c106b5ef8380` |

### 보존 응답 JSON 해석 진단

`measure-response-decode.py`로 파일을 미리 읽어 둔 뒤 UTF-8 decode와 json.loads만
process CPU clock으로 측정했다. baseline/candidate/candidate/baseline 순서이며
각 scenario60응답을20회 재생해 실행당1200회다. 워밍업1회는 측정에서 제외했다.
네 실행 전체24000회,입력600개 raw response 해시 및 도구 해시 불변을 확인했다.
네트워크/서버/동시 요청/GIL 경쟁은 포함하지 않는다. 측정 중 다른 작업은 중단했다.

| scenario | baseline0 평균 us | candidate1 평균 us | candidate2 평균 us | baseline3 평균 us |
| --- | ---: | ---: | ---: | ---: |
| lexical | 59.923 | 59.964 | 59.848 | 59.959 |
| ranking | 3.526 | 167.265 | 166.395 | 3.503 |
| facet | 17.024 | 16.782 | 16.820 | 16.842 |
| sort_filter | 95.911 | 95.882 | 95.800 | 95.748 |
| nested | 321.336 | 322.773 | 320.768 | 320.518 |

ranking 응답량 증가에 따른 JSON 해석 비용은 확인했지만 전체 mixed 회귀 중
기여율이나 특정 서버 구현의 비용으로 환산하지 않는다. 후속은 실제4-client 부하의
응답 수신/JSON 해석/스레드 대기를 분리 관측하고 native 응답 생성 비용과 구분하는
진단이다. 벤치마크 파서를 교체하거나 source/hit을 줄여 고정 게이트를 통과시키지 않는다.
실제 구현 변경을 정하면 전체 engine/node/HTTP/non-plugin 반복 게이트를 다시 적용한다.

증거 경로 `target/core-replacement-c06/native-buffered-response-decode/`:
plan SHA `d2057a0c8164edc017ba7dad37abac395802c94f998da726f65b04572bdd5182`,
result SHA `718334513c3b562b79ba005e70f55aa53dd5265464dd37748115190cf3cde8ab`.

### HTTP phase 진단 사전 계획

- 정식 load/matrix를 수정하지 않고 격리된 `phase-load.py`/`phase-matrix.py`로
  요청 준비, urlopen, response.read, UTF-8/JSON decode의 wall/thread CPU 합계를
  수집한다. setup은 제외하며 기존4-client worker/요청 생성/응답 처리는 유지한다.
- 같은 write_search 가중치,3노드45초,5000문서384값,3샤드replica1,seed13의
  baseline/candidate/candidate/baseline4회를 실행한다. 입력과 실행 파일은 매회
  전후 확인하며 동시 작업을 중단한다. 계측 자체의 오버헤드는 존재한다.
- `run-http-phase-abba.py`는 오류/coverage 누락/요청 수 불일치를 거부하고
  결과를 diagnostic_only로 보존한다. 새 출력은
  `target/core-replacement-c06/native-buffered-http-phases/`다.
- wall-thread CPU 차이는 스케줄링/GIL/네트워크/서버 대기 등이 섞인 값이며
  특정 원인의 대기 시간으로 명명하지 않는다. 진단을 전체 게이트로 대체하거나
  원본 기준선·내구성·보안·응답 의미를 변경하지 않는다.

### 완료된 HTTP phase 증거

`target/core-replacement-c06/native-buffered-http-phases/`의 diagnostic-only
ABBA4회가 완료됐다. 동일한 `write_search` mixed workload에서 qps와 write latency는
다음과 같다 (latency ms, qps는 전체 successful operation 기준).

| run | qps | write mean | write p95 | write p99 |
| --- | ---: | ---: | ---: | ---: |
| 00 baseline | 1280.857 | 2.819 | 4.639 | 5.786 |
| 01 candidate | 1193.964 | 3.044 | 4.924 | 5.991 |
| 02 candidate | 1200.659 | 3.027 | 4.946 | 6.074 |
| 03 baseline | 1280.992 | 2.839 | 4.663 | 5.724 |

아래 phase 값은 각 operation의 phase별 합계를 해당 operation count로 나눈
per-request 평균이다 (wall/cpu ms). `request_prepare`는 JSON 직렬화와 Request
생성, `open`은 `urllib.request.urlopen`부터 response acquisition, `read`는
`response.read`, `decode`는 UTF-8/JSON decode다.

| run | operation | request_prepare wall/cpu | open wall/cpu | read wall/cpu | decode wall/cpu |
| --- | --- | ---: | ---: | ---: | ---: |
| 00 baseline | write | 0.170/0.168 | 2.060/0.424 | 0.259/0.067 | 0.015/0.014 |
| 01 candidate | write | 0.170/0.168 | 2.263/0.438 | 0.272/0.068 | 0.015/0.014 |
| 02 candidate | write | 0.171/0.169 | 2.242/0.433 | 0.275/0.067 | 0.015/0.015 |
| 03 baseline | write | 0.170/0.168 | 2.083/0.425 | 0.255/0.066 | 0.015/0.015 |
| 00 baseline | ranking | 0.050/0.049 | 2.862/0.414 | 0.271/0.067 | 0.017/0.016 |
| 01 candidate | ranking | 0.051/0.050 | 2.792/0.425 | 0.410/0.086 | 0.235/0.227 |
| 02 candidate | ranking | 0.051/0.050 | 2.777/0.421 | 0.410/0.084 | 0.234/0.226 |
| 03 baseline | ranking | 0.050/0.049 | 2.870/0.412 | 0.265/0.067 | 0.017/0.016 |

write mean 상승은 주로 `urlopen`/`open`에서 보이며, write의 `request_prepare`와
`decode`는 사실상 변하지 않았다. ranking은 `open`이 오히려 작아졌지만 `decode`가
약 0.017 ms에서 약 0.234 ms로 증가했다. 이 phase wall 값과 thread CPU 값의
차이만으로 CPython shared-thread client waiting, GIL, 네트워크 또는 native
server time 중 어느 것도 원인이라고 주장하지 않는다.

6개 operation aggregate 모두 각 summary.json에 raw로 보존했으며, 아래는
count/exceptions 확인값이다. 이는 모든 scenario의 phase aggregate가 보존됐다는
뜻이지 고정 성능 게이트 coverage를 의미하지 않는다.

| run | facet | lexical | ranking | sort_filter | nested | write |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 00 baseline | 10861/0 | 10813/0 | 10669/0 | 7249/0 | 7195/0 | 10853/0 |
| 01 candidate | 10115/0 | 10060/0 | 9992/0 | 6760/0 | 6672/0 | 10132/0 |
| 02 candidate | 10176/0 | 10118/0 | 10039/0 | 6799/0 | 6717/0 | 10184/0 |
| 03 baseline | 10863/0 | 10824/0 | 10668/0 | 7247/0 | 7200/0 | 10846/0 |

8개 시험이 통과했고, 네 실행 모두 child exit=0, request error=0,
phase counts verified, inputs verified=true였다. 이는 reset/waiver가 아니며
진단은 전체 gate parser, query, source 또는 safety control을 대체하지 않는다.
parent는 raw evidence를 독립적으로 검증한다. 다음 diagnostic은 CPython
shared-thread client waiting과 native server time을 구분해서 관측해야 하며,
그 전까지 이 결과로 서버/GIL 인과를 확정하지 않는다.

HTTP phase artifact SHA-256:

| artifact | sha256 |
| --- | --- |
| `plan.json` | `0103b627b7e3b72ff10b8ecd9ef0db79bb372a405a870b6ba688e828364e4cbd` |
| `result.json` | `2fb64ef47c148b81a87753b22e43bdf906915f6122fbc5e5cefd8a13867c2199` |
| `00-baseline/summary.json` | `59ea78d08aa5635b5fe1fdb05ec27805481d7baed09ce15791597d67ccab55be` |
| `01-candidate/summary.json` | `96af3d0c11dc6ec09afda11c0705d34367f74fa9b6767195c66bdecb0bccfbf9` |
| `02-candidate/summary.json` | `fc305fe896d336cb6991505a6d15b683b77559e7d3fed2b78485a5bf9191d8f1` |
| `03-baseline/summary.json` | `62b0f9f1acc3b02f2ddb8a7da97bd756243d96fc32f80e132e9eb1b2c7e2428e` |
