# Native HTTP Response Encoding

상태: 격리 구현 후보, 미수락. 전체0/40,성능 FAIL,릴리즈 보류를 유지한다.

## 근거와 범위

- [쓰기 간섭 조사](write-interference-investigation-2026-09-11.md)에서 write_search
  회귀를 확인했다. client phase의 wall time만으로 서버/GIL 원인을 확정하지 않는다.
- a5b38b49 동결 `standalone_runtime.rs:1184`의 web::block은 handle_rest_request만
  감싸며, 응답 serde_json::to_vec는 이후 Actix handler에서 수행한다.
  보존 CPU `native-buffered-write-search-cpu-abba/01-candidate/server-relative-self-report.txt`
  에도 serde JSON/float 직렬화 -> rest_response_to_actix_response -> Actix handler
  경로가 있다. 이는 실행 위치의 증거이지 회귀 기여율의 증명은 아니다.
- native query/scorer/collector, 결과 수/source/점수/문서 가시성은 변경하지 않는다.
  기존 serde serializer와 기존 web::block을 재사용한다. 별도 검색 구현은 없다.

## 구현 단위

1. a5b38b49의 보존 source를
   `target/core-replacement-c06/native-http-encode-candidate/source`로 복사한다.
   root source와 기존 후보/실행 파일/기준선 증거는 변경하지 않는다.
2. 부모가 기존 response body encoding을 EncodedRestResponse로 분리하고 기존
   blocking closure 안에서 호출한다. JSON tree는 그 작업 안에서 해제한다.
   Actix 쪽은 status/header/body bytes만 조립한다. raw Vec는 복사하지 않는다.
3. Terra는 별도 http_encode_tests.rs에서 raw 우선순위/빈 raw/null/text/JSON
   정확한 bytes와 헤더/status,Send 계약을 검증한다. URI/body/security/오류처리
   의미는 유지한다. panic 직렬화 경계가 blocking task 안으로 이동한다는 점도
   전체 HTTP/오류 시험에서 검토한다. 직렬화 실패의 기존 {} 처리는 변경하지 않는다.
4. 두 파일 외 source 차이가 없는지 확인하고 source manifest를 고정한다.
   별도 build 디렉터리에서 engine 전체와 node lib/bin(standalone-runtime) 전체를
   실행한다. 단독 helper 시험은 추가 진단이지 전체 게이트를 대체하지 않는다.
5. 별도 locked/offline release를 빌드해 실행 파일 identity를 기록한다.
   확장 HTTP37fixture/2625건 이상과 전체 non-plugin6실행/12토폴로지를
   실행한 뒤에만 단위 완료를 판단한다. 계측 없는 정식 부하 도구를 사용한다.
   직전 a5b38b49와의 차이도 보존하지만 이는 최초 기준선이 아니다.

## 수락 조건

최초 v0.6.0 db244133과 원본 published current.json을 고정한다. 같은 실제 부하/
내구성/보안/자원 설정에서 각 topology 처리량>=95%,모든 scenario mean/p95/p99<=105%
조건을 개별 판정한다. 다른 개선으로 초과를 상쇄하거나 기준선을 재설정하지 않는다.
초과 시 조사/최적화/전체 재측정하며 상위 core-replacement 계획의 제외/예외 규칙을
따른다. 미해결5% 이상 단일 구현의 귀속이 입증되면 제외 ledger를 적용하되 안전성/
정확성을 제거하지 않는다. 유지 예외는 명시적 승인 없이는 허용하지 않는다.
릴리즈 시 직전 published release와 pinned OpenSearch 시나리오 표도 포함한다.
이 후보를 준비했다는 사실이나 기존 시험의 통과는 릴리즈 승인이 아니다.

## 검증 이력

- 초기 node 전체 실행은 새 테스트의 `actix_web::test` 매크로가 현재 feature에
  없어 컴파일 단계에서 종료101이었다. 시험 실행/통과로 세지 않는다.
  기존 System::new().block_on 패턴으로 테스트만 수정했으며 dependency/features는
  변경하지 않았다. 실패 로그 `node-tests-compile-failed.log` SHA는
  `98cd4af6a1b2ab8faea9bd8bfbeb8abdb4150ca0b0a4c7bb0810daf88cfd4431`이다.
- 수정 전 manifest는 source-before-test-fix.sha256으로 보존했다. 현재 source.sha256
  SHA는 `1ea09d3f99c911f3d749b5f4fcd9fcefb624936b2b185d6b54b07a5d2e55bbf3`다.
  노드 전체는 `--locked --offline -j 2 -p os-node --features standalone-runtime
  --lib --bin steelsearch`로 재실행한다. standalone 이외 integration 대상의
  광범위 빌드를 실행하거나 그 범위까지 통과했다고 주장하지 않는다.
- 수정 후 node 전체674+459=1133건 통과,실패/ignored/filtered0,종료0이다.
  신규 인코딩8건도 모두 통과했다. 빌드42.30초,실행4.33/11.87초다.
  node-tests.log SHA `31fe1dffdb14a2fd30504f11107499d7f9f3fa0d3489f9f6d4206eee002d9fc2`.
- engine 전체946+7+4+9=966건 통과,실패/ignored/filtered0,문서시험0건,종료0이다.
  `cargo +nightly test --locked --offline -j 2 -p os-engine-tantivy`를 같은 격리
  build 디렉터리에서 실행했다. 빌드1m52s,실행14.16/8.54/2.27/0.18초다.
  engine-tests.log SHA `3c11bdd88be0ea98e669092b67fb9ade6b723867c6f1da2b6fdd97bc5811e77f`.
- 두 실행 모두 DEV/TEST DEBUG=0,INCREMENTAL=0이며 완료 후 source manifest 검증이
  통과했다. dependency lock/vendor/native 검색 소스는 이전 a5b38b49와 같다.
  전체 source 차이는 standalone_runtime.rs와 http_encode_tests.rs뿐이다.
- 다음 필수 단계는 새 release 실행 파일 identity 확보,확장 HTTP37fixture/2625건
  이상 및 계측 없는 전체 non-plugin6회/12토폴로지 gate다. 아직 실행하지 않았고
  성능 효과는 미검증이다. 최신 유효 전체 성능 판정은 기존 a5b38b49 FAIL 그대로다.

## Release 빌드

- 동결 source에서 `cargo +nightly build --release --locked --offline -j 2
  -p os-node --features standalone-runtime --bin steelsearch`를 별도 build 경로로
  실행했다. 종료0,7m49s이며빌드 후 source.sha256 전체 검증이 통과했다.
- rustc1.97.0-nightly,commit ad3a598ca4bc7c68bcbbce3e0d3be9a7618df190,
  aarch64-unknown-linux-gnu,LLVM22.1.4다. 기존 후보와 같은 도구체인이다.
- 실행 파일은 artifacts/steelsearch로 별도 보존했다. SHA는
  `231c65f67360b27f2cd37625540a427adc01fcc5d4aeb23891cf7bec33ae4bf3`다.
  candidate-build.log SHA는
  `196df006c816c3c7d89e7a4758241a384544ef3a870e705aaf73a23565b64366`이다.
- Luna가 이전 실행의37fixture 해시 불변을 확인했다. HTTP 실행 명령은
  artifacts/http-invocation.json에 보존하고 새 native-http-encode-release-live
  경로에 실행한다. 빌드 성공은 HTTP/성능 검증 통과나 태그/릴리즈 발행이 아니다.

## 확장 HTTP 완료

- native-http-encode-release-live 실행은37fixture/2625건,
  2353통과272실패skip0,종료1이다. count probe=true,실행 파일/fixture 불변=true다.
  기능 참조는3.7.0-SNAPSHOT/build f991609d190dfd91c8a09902053a7bbfe0c27b3e,
  Lucene10.4.0이며 성능 참조2.19와 구분한다.
- 기존 a5b38b49 실행과37fixture 해시가 같고,각 report SHA를 검증했다.
  중복 이름 없이 `(report filename,case name)->status`2625개가 전부 동일했다.
  이는 케이스 상태의 동등성이지 모든 원본 응답 bytes의 동등성 인증은 아니다.
- execution.json SHA는
  `9a8d29dad2142608866902070bda54c61626a5223384d792586923e9bc61bc32`다.
  종료 후 source manifest와 artifact231c65f6 해시도 그대로임을 확인했다.
- 다음은 `tools/run_core_performance_gate.py --baseline-binary
  target/core-replacement-s01/baseline/steelsearch --candidate-binary
  target/core-replacement-c06/native-http-encode-candidate/artifacts/steelsearch
  --output-dir target/core-replacement-c06/native-http-encode-repeated-full`이다.
  전체6실행/12토폴로지,모든 요청 시나리오/반복을 보존한다. 이 전체 성능 단계는
  아직 미실행이며 고정v0.6.0/직전published/OpenSearch 비교를 생략하지 않는다.
  HTTP272실패를 제거하거나 전체 구현 수락으로 세지 않는다. 릴리즈 보류 유지.

## 첫 전체 성능 실행 중단

- native-http-encode-repeated-full은4번째 실행(OpenSearch 반복2)의3노드 준비
  timeout으로 부모종료2다. 00baseline/01candidate/02OpenSearch는 종료0이며
  03OpenSearch의 단일노드 결과도 보존하지만 뒤의 후보/기준선 반복은 미실행이다.
  실행 전체의 inputs_verified=false,numeric_budget_passed=false,acceptance=false다.
  이것을 완료된 반복 성능 게이트나 후보의 최종 성능으로 보고하지 않는다.
- plan SHA `10399179ec342b06ae98cec4cfc77ffef4aa24c67c2839916dbbc3bd90862f93`,
  result SHA `673cf400f4b64826741e483c6ab49e666a1d3e011550f4195bf0d814a85d7f39`.
- 완료된 첫 측정의 단일/3노드 처리량은 baseline753.238/920.389,
  candidate756.406/862.328,OpenSearch277.395/126.606ops/s다. 요청 오류0이다.
  write mean은 baseline2.848/2.958ms,candidate3.130/3.293ms다.
  모든 summary와 원래 report hash를 보존하며,유리한 단일노드 값만 선택하지 않는다.
- 실패 단계 로그는3노드 발견,yellow,primary2/active2/unassigned4를 보인다.
  정확한 미할당 원인을 보여주는 allocation explain은 당시 수집되지 않았다.
  디스크 부족은 가능성이지 이 로그만으로 확정한 원인이 아니다.

## 준비 실패 진단 보강과 공간 확보

- Terra가 matrix의 readiness 호출을 기존 실패-capture 범위 안으로 옮겼다.
  health/allocation explain을 추가 수집하고 기존 오류를 전파한다.
  green/node count/빈blocks/180초 deadline 및 보안·디스크 설정은 변경하지 않았다.
  부모 재검증으로 failure/readiness18시험 통과다. 이전 matrix는
  target/core-replacement-c06/matrix-before-readiness-diagnostics.py에 보존했다.
  새 matrix SHA `046630f1fa54f0c5f83ca752fc6d18b1cb25abaf4601e0f42a906a016cf3274b`.
- 현재 후보의 재생성 가능한 build cache는 cargo clean으로2.1GiB 정리했다.
  root release cache 중 ring/zstd-sys/libmimalloc-sys와 tantivy/serde_json/tokio/
  actix-http/actix-web도 cargo clean의 package 범위로 정리했다.
  직접 rm -rf 방식의 정리는 환경에서 거부되어 실행되지 않았다.
  현재 후보 artifact231c65f6와 root target/release/steelsearch
  SHA b03643a4d23fb88015d455c2e9707e5a5e0d7d3051dfd498292a3277e13c9858은 보존했다.
- 완료된41개 CPU trace는 gzip 압축 후 원본 SHA와 압축 해제 stream SHA가 같음을
  확인한 다음 원본 perf.data만 제거했다. perf.data.gz와 텍스트 보고서는 유지한다.
  원본/압축/복원 해시와 경로는 pre-http-encode-profile-archives.json에 있다.
  ledger SHA `c722324d46f4baefb2d08793006f11a915e7c0448e703e093962c162ee7c874e`.
  논리 파일 크기 기준 절감451432338bytes이며 hardlink 등으로 실제 fs 증가량과
  같다고 주장하지 않는다. 마지막 df available은15538503680/102888095744bytes다.
- 다음은 준비 상태의 실제 재확인 후 새로운 전체6회/12토폴로지 실행이다.
  이번 불완전 실행을 이어붙이거나 입력 해시를 바꿔 덮어쓰지 않는다.
  원본v0.6.0 게이트와 정식 워크로드/안전 설정은 그대로 유지한다.

## 적재 포함 준비 재검증

- `target/core-replacement-c06/check-opensearch-readiness.py`로 새 독립 진단
  `native-http-encode-opensearch-readiness`를 실행했다. 종료0이며 초기 readiness,
  동일 config의5000건 적재/refresh 후 readiness, 전후 안전 설정 검증을 통과했다.
  최종3노드 green, 미할당/초기화/이동 샤드0, pending task0이다.
  이는 비측정 진단으로 acceptance=false이며 전체 성능 재실행을 대체하지 않는다.
- 실제 참조 identity는 OpenSearch2.19.0,
  build `fd9a9d90df25bea1af2c6a85039692e815b894f5`다.
  런처에는 digest-only 이미지 이름을 전달했다. Docker inspect로 실제 image ID가
  정식 repository@digest와 동일한
  `sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb`
  임을 확인했다. heap512MiB 및 readiness/안전 조건은 변경하지 않았다.
- 실행 입력 불변=true. plan SHA
  `51bca1aa5cb8af1e808d869849c9607636fcfe06d32841b2e9b13623e7f2e9be`,
  result SHA `2be6a5bcd944814aaf673bce9273d3d987bc44a7f3bd846d5a846607d6730192`.
  health/filesystem/settings/blocks는 종료 전에 보존했다. 미할당 샤드가 없어
  allocation explain의 오류는 진단 수집 결과로 남으며 준비 실패를 뜻하지 않는다.
- 적재 후 각 노드 filesystem available=15464226816/102888095744bytes다.
  공간 여유가 작으므로 이번 성공만으로 반복 실행의 안정성을 보장하지 않는다.
  이전 timeout의 원인도 확정하지 않는다. 모든 진단 서버는 종료했다.
- Luna가 다음 전체 게이트 명령, baseline/candidate 실행 권한과 해시를 확인했다.
  timed 측정 전에 해당 에이전트를 종료했다. 새 전체 실행은 아직 시작하지 않았다.
  다음은 공간 여유 확인 후 새 디렉터리에서6실행/12토폴로지 전체 재측정이다.
  기존 불완전 실행을 이어붙이지 않으며 현재0/40, TV1 미완료, 릴리즈 보류다.

## 새 전체 성능 게이트 완료: FAIL

- 실행: `native-http-encode-repeated-full-fresh-20260911`. 기존 중단 실행을 재사용하지
  않은6회/12토폴로지 전체 실행이다. 각 실행 종료0, 모든 토폴로지 요청 오류0,
  execution_inputs_verified=true, numeric_budget_passed=false, acceptance=false,
  부모 종료1이다. OpenSearch 두 반복 모두 완료했으며 준비 timeout은 재발하지 않았다.
- 실행 전 root Cargo의 serde/serde_core/ahash/libc/zerocopy/proc-macro2/quote/syn/
  rustversion/getrandom/httparse/crossbeam-utils/crc32fast/rayon-core/parking_lot_core/
  crunchy/rustix/zmij 패키지 캐시만 cargo clean --release로 정리했다.
  Cargo 보고325.7MiB, 실제 available15530283008→15756038144bytes다.
  기준선/후보/root 실행 파일 해시가 그대로임을 확인했다. 측정 중 동시 작업은 없었다.
- plan SHA `bcb42a1ccd963c7f8a6a8fda20ac8e0d5beb087df1aaff1028bd401d4be2f4f8`,
  result SHA `f127daa8164e75d97830cf3dd553cc2f1ff23c6892e170c7d686424d9ae2a8fc`.
  실행 후 source manifest 전체 검증, 도구 fingerprint/plan 검증을 통과했다.
  원본 reports로 assess를 다시 계산하여 기록된 모든 판정 필드와 동일함을 확인했다.

처리량은 ops/s이며 각 반복을 평균내지 않았다.

| 실행 | 실제 역할/식별 | 단일 | 3노드 |
| --- | --- | ---: | ---: |
| 00 | v0.6.0 db244133 | 733.855 | 915.707 |
| 01 | HTTP encode 231c65f6 | 753.934 | 886.081 |
| 02 | OpenSearch2.19 fd9a9d90 | 280.142 | 115.362 |
| 03 | OpenSearch2.19 fd9a9d90 | 288.153 | 112.480 |
| 04 | HTTP encode 231c65f6 | 732.942 | 871.391 |
| 05 | v0.6.0 db244133 | 733.962 | 896.934 |

| 판정 | 반복1 | 반복2 |
| --- | ---: | ---: |
| 고정 published v0.6.0 실패/44지표 | 10 | 18 |
| 동일 실행 paired v0.6.0 실패/44지표 | 8 | 7 |
| v0.6.0 재측정 baseline drift 실패/44지표 | 11 | 14 |
| 단일 처리량 고정기준 대비 변화 | +1.47% | -1.36% |
| 3노드 처리량 고정기준 대비 변화 | -4.86% | -6.44% |
| 단일 write mean 고정기준 대비 변화 | +10.41% | +12.76% |
| 3노드 write mean 고정기준 대비 변화 | +9.58% | +9.70% |
| 단일 처리량 / paired OpenSearch | 2.691x | 2.544x |
| 3노드 처리량 / paired OpenSearch | 7.681x | 7.747x |

- 모든 시나리오 mean/p95/p99 및 throughput의 원시값·한계·개별 판정은 result.json의
  checks와6개 summary.json에 보존했다. 위 표는 요약이며 실패 지표를 삭제하지 않았다.
  고정기준에서 두 반복 모두 write 전 토폴로지 mean/p95/p99와3노드 ranking
  mean/p95/p99,3노드 refresh p99가 실패한다. 반복2는 추가로3노드 throughput,
  단일 sort_filter mean,3노드 lexical mean/p95,facet mean,sort_filter p95,
  nested p95/p99가 실패한다. 기준선 drift로 후보 실패를 면제하지 않는다.
- 동일 시점 paired 비교에서도 write mean은 단일+7.60%/+9.08%,
  3노드+9.70%/+7.04%,3노드 ranking mean은+11.19%/+8.74%다.
  OpenSearch 처리량 우위는 이 개발 프로파일의 관측값이지 운영 대체 인증이 아니다.
- 이전 a5b38b49와 다른 시점의 처리량 차이를 HTTP encode 단일 변경의 인과적 개선으로
  단정하지 않는다. 이 변경만으로 기존 회귀가 해결되지 않았다는 점은 확인됐다.
  원래 ranking 누락을 재도입하거나 결과량/보안/내구성/정밀도를 낮추지 않는다.
  다음 조사 범위는 반복 실패한 write/3노드 ranking 경로의 native 실행·결과 생성 비용이다.
  pinned Tantivy 지원과 기존 진단을 먼저 확인하며 동일 누락 원인 재조사를 반복하지 않는다.
  후속 구현 단위도 전체 engine/node/확장 HTTP/6회12토폴로지 게이트가 필수다.
- 후보는 격리 상태이며 root 제품 코드로 승격하지 않았다. 수락0/40,TV1 미완료,
  HTTP272실패와 릴리즈 보류를 유지한다. 단일 기능의 귀속이 입증되지 않은 누적 회귀를
  근거로 임의 제외 처리하지 않으며, 태그/릴리즈를 발행하지 않았다.
