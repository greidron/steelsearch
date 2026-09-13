# Native ArenaHashMap term table 실험 기록

작성일: 2026-09-11

## 판정

이 문서는 `native-term-table`의 격리된 native 실험만 기록한다. 실험 결과는
`diagnostic_only=true`, `acceptance_established=false`, `inputs_verified=true`이다.
따라서 구현 완료나 성능 합격을 주장하지 않는다. 현재 목표 진척은 `0/40`,
`TV1`은 미완료다.

고정 최초 `v0.6.0` 누적 게이트의 기존 `FAIL(c224a57a)` 판정은 그대로이며,
이 실험으로 기준선을 재설정하지 않는다. 서버 후보의 전체 engine966건과
node1125건은 통과했다. 서버 전체 성능은 아직 측정하지 않았다.

## 구현 범위

후보 소스는 frozen `c224a57a`를 기반으로 하며 애플리케이션 소스는 유지하고
`vendor/tantivy/src/indexer/segment_writer.rs`만 변경했다. root Tantivy는
변경하지 않았다. 변경은 term table을 native `ArenaHashMap`으로 사용하며,
자동 성장을 보존하고 초기 용량의 상한을 `4096`으로 둔다. 원래 memory-budget 계산을
그대로 사용하는 방식과 비교한 격리 실험이다.

lock, dependency, FST, merge 경로는 양 변형에서 동일하다.

## 실행 조건

계획: [`plan.json`](../../target/core-replacement-c06/native-term-table-experiment/measurement/plan.json)
  (SHA-256 `07a6d1f02d1a24de867fe376ca623660d6fb7a4b85456f03e9a61066679609c8`)

- ABBA 실행 4회, 전체 8조건(각 실행 2조건), 순서 `before, after, after, before`
- 문서/배치 `2`, refresh `256`, seed `1667`, numeric `384`, indexed-fast enabled
- 각 조건 validated documents `2179`
- 인자: `--notified-locks --indexed-fast-only --floor=512 --batch-docs=2 --refreshes=256`
- runner SHA-256 `ae3f22d1d6a7065bcf6eda2c4d15bab0c2cfb158da81e3e6a58a67d7507c70ad`

계획에 기록된 실제 실행 파일 identity:

| 변형 | 실행 파일 | binary SHA-256 | source manifest SHA-256 |
|---|---|---|---|
| before | `before-build/release/refresh-experiment` | `33fb0f3bf5b4bbc9b39decc8bcc7738ba0dbeca4698619b5171ee7f807a586af` | `3a316e1cf12e75a2e92b5e9fee692de73f8b26797a20ed8fe7f1b47dc1087c44` |
| after | `after-build/release/refresh-experiment` | `8107fdd2a0d45924b4d8c20416324b8f6bcead5a8fefb8e7e8317264645c40f6` | `ab5bb7e65dd9668a7ae34b0bef3f478521b1fc6c8d1217a63a8af1c4de483cbd` |

## 원시 측정

결과: [`result.json`](../../target/core-replacement-c06/native-term-table-experiment/measurement/result.json)
  (`plan_sha256` 동일, `inputs_verified=true`). 원시 실행 파일은
  [`00-before.jsonl`](../../target/core-replacement-c06/native-term-table-experiment/measurement/00-before.jsonl),
  [`03-before.jsonl`](../../target/core-replacement-c06/native-term-table-experiment/measurement/03-before.jsonl),
  [`01-after.jsonl`](../../target/core-replacement-c06/native-term-table-experiment/measurement/01-after.jsonl),
  [`02-after.jsonl`](../../target/core-replacement-c06/native-term-table-experiment/measurement/02-after.jsonl)이다.

아래는 JSON의 `mean_us` 값을 8조건 각각에 대해 기록한 표다. 키 이름에
`_ns`가 들어 있지만 값 자체가 이미 microseconds이므로 단위 변환은 하지 않았다.
percent 변화율은 계산하거나 주장하지 않는다.

| 실행/조건 | 변형 | add us | prepare us | publish us | reload us |
|---|---|---:|---:|---:|---:|
| 0/1 | before | 22.012 | 2098.776 | 191.788 | 156.641 |
| 0/2 | before | 25.236 | 1948.361 | 204.454 | 190.483 |
| 1/1 | after | 21.357 | 1317.069 | 162.013 | 176.447 |
| 1/2 | after | 23.247 | 1302.159 | 161.634 | 170.832 |
| 2/1 | after | 21.049 | 1271.957 | 179.766 | 163.918 |
| 2/2 | after | 21.026 | 1289.709 | 148.603 | 180.947 |
| 3/1 | before | 18.838 | 1614.324 | 113.349 | 156.519 |
| 3/2 | before | 21.220 | 1659.535 | 112.857 | 152.169 |

## 소스 증거와 검증

- [`before-source.sha256`](../../target/core-replacement-c06/native-term-table-experiment/before-source.sha256)
  및 [`after-source.sha256`](../../target/core-replacement-c06/native-term-table-experiment/after-source.sha256)는
  입력 manifest로 보존했다.
- `segment_writer.rs` SHA-256: before
  `f45c2247be55a79adeb86767e20145aa1cdea60c7521139cda52a078d4fe8e22`; after 및
  후보 `b3740e057b2fbef57d28452b74f9a634256f20181a3992a62ff247fb447fbd4c`.
- 후보 source digest: `f5f551642c78b5b21283ec02b69d2be1956134b8daa7f6074b4544d8f898ccad`.
- [`before-tests.log`](../../target/core-replacement-c06/native-term-table-experiment/before-tests.log)
  및 [`after-tests.log`](../../target/core-replacement-c06/native-term-table-experiment/after-tests.log):
  각 변형 example test 10개 passed, failed 0.
- example 검증 범위는 docID uniqueness/missing, old reader, fast values,
  sampled numeric term counts다. 이는 전체 서버 또는 전체 correctness 검증이 아니다.

## 다음 단계

전체 engine966건(946+7+4+9)은 실패/ignore/filter0으로 통과했다.
engine-tests.log SHA-256은 `c5ef4cc79d76afff335f36eed7175994fd6f15cdb50da03ef36f39856e872f7d`다.
전체 node1125건(666+459)도 실패/ignore/filter0으로 통과했다.
node-tests.log SHA-256은 `ff1a3e6086f9ddb0a090be8586fdea43c882f298fc2a7a25362c5460aa9dbcbc`다.
시험 후 동결 source manifest 검증도 통과했다.
release 빌드와 HTTP 검증은 아래에 기록한 대로 완료되었다. 이후 full non-plugin
suite를 동일 조건으로 6회, 12개 topology에서 실행한다. 완료 조건은 각 topology와 각 scenario에서
고정 `v0.6.0` 대비 처리량 `>=95%`, mean/p95/p99 latency `<=105%`이며,
기준선은 절대 재설정하지 않는다.

## Release 빌드와 HTTP 검증

후보 release 빌드는 완료되었다. 후보 artifact는
[`artifacts/steelsearch`](../../target/core-replacement-c06/native-term-table-candidate/artifacts/steelsearch)이며,
`candidate-build.log`의 release 빌드가 성공적으로 종료되었다. artifact SHA-256은
`668365ad0524a4ede6be85503665babc5884c493ee514120082aa900f458b721`이며,
[`execution.json`](../../target/core-replacement-c06/native-term-table-release-live/execution.json)의
`binary_sha256`와 일치한다. HTTP runner SHA-256은
`4a14e12a662017e2d18edf7fc1a2e1cf26a065c4ed9a7fe6c33d298e17f39bc1`이다.

동일한 [`execution.json`](../../target/core-replacement-c06/native-term-table-release-live/execution.json)의
HTTP 검증 실행은 37개 fixture에 대해 기록되었다. 요약은 passed `2353`, failed
`272`, skipped `0`이며, 실행 return code는 `0`이 28회, `1`이 9회이다.
파일에 `acceptance_established=false`가 기록되어 있으므로 이 검증을 HTTP
acceptance 또는 구현 완료로 해석하지 않는다.

첫 full non-plugin benchmark 시도인
[`native-term-table-repeated-full/result.json`](../../target/core-replacement-c06/native-term-table-repeated-full/result.json)은
baseline, candidate, 첫 OpenSearch 실행만 return code `0`으로 완료했고,
planned run `3`에서 terminal error `exit 1`로 종료되었다. 따라서 이는 불완전한
실행이며 full performance result나 수락 근거가 아니다. 성능 수치, regression,
또는 최종 acceptance를 추론하지 않는다.

이후 초기화 대기 수정과 하네스119건 검증을 거쳐 새 출력 디렉터리
`native-term-table-repeated-full-ready`에서 전체6회/12토폴로지를 재실행했다.
자식 exit0/요청 오류0/입력 불변 확인이나 최종 성능은 FAIL, 부모 exit1이다.
3노드 처리량은 고정 v0.6.0 대비-6.24%/-6.61%, 쓰기 평균 지연은 두 토폴로지
모두+10% 이상으로 누적 예산을 넘었다. 원본 정밀도의 각 반복·시나리오 비교는
[전체 성능 기록](native-term-table-performance-2026-09-11.md)을 따른다.
앞선 미완료 실행을 숨기거나 결과를 혼합하지 않았다. 이 실험의 국소 준비시간
개선을 구현 단위 완료로 환산하지 않으며 루트vendor 승격 및 릴리즈는 보류한다.
