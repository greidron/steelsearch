# Native Columnar Merge 조사 및 격리 실험 계획

상태: 격리 패치와 서버 검증 실행 완료, 전체 성능 FAIL, 구현 단위 미수락.
고정 누적 기준선은 최초 v0.6.0이다.
출발 후보는668365ad이며 최신 후보a5b38b49의 전체 게이트도 FAIL이다.
이 계획은 예외 승인이 아니다.
플러그인 기능은 제외한다.

## 출발 증거

- 현재 전체 결과: `target/core-replacement-c06/native-term-table-repeated-full-ready`.
  전체6회/12토폴로지 요청 오류0, 입력 불변 true지만 3노드 처리량은 고정 기준선
  대비-6.24%/-6.61%, 쓰기 mean은 두 토폴로지에서+10% 이상이다.
- 첫 CPU 관측은 candidate,baseline 각각1회이며 소급 ABBA가 아니다.
  서버만 선택한 IndexMerger::write children은11.67%/1.45%,
  write_fast_fields는7.81%/0.09%다. 이는 merge 발생 시점과 샘플링의 영향을
  받으므로 원인 또는 개선율로 단정하지 않는다.
- 세부 증거와 해시는 [진단 기록](native-ranking-audit-2026-09-10.md),
  전체 수치는 [성능 비교](native-term-table-performance-2026-09-11.md)를 따른다.

## Native 조사

Cargo.lock의 `tantivy-columnar 0.2.0` checksum은
`8d85f8019af9a78b3118c11298b36ffd21c2314bd76bbcd9d12e00124cbb7e70`이다.
조사한 소스 루트는
`/home/ubuntu/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/tantivy-columnar-0.2.0`.
레지스트리 원본은 수정하지 않는다.

| 기존 native 지점 | 확인한 동작 | 실험에서 유지할 계약 |
| --- | --- | --- |
| src/columnar/merge/mod.rs: merge_columnar | 그룹 open, 빈 그룹 제거, 출력 타입 선택, coercion 후 기존 serializer 호출 | required type 우선순위와 실패, 빈 column 타입 처리 |
| 같은 파일: dynamic_column_to_u64_monotonic | F64/I64 등의 typed reader를 monotonic u64 view로 변환 | 원본 값/순서/부호/경계 표현 |
| src/dynamic_column.rs: open_u64_lenient | I64/U64/F64/Bool/DateTime을 native encoded-u64 column으로 열 수 있음 | 문자열 term ordinal과 numeric 값을 혼동하지 않음 |
| src/column_values/merge.rs: MergedColumnValues | Stack은 기존 column iterator 연결, Shuffled는 row 주소/index로 값 선택 | 누락/다중값 cardinality, 삭제 및 재배열 |
| src/column_values/u64_based/mod.rs: serialize_u64_based_column_values | 기존 codec estimator와 stats 수집 후 최소 크기 codec 선택, 두 번째 순회로 직렬화 | 기존 코덱 선택과 파일 포맷, 오류 전파 |
| src/column_values/monotonic_column.rs | typed wrapper iterator가 boxed 원본 iterator를 다시 map | get_range는 upstream 주석상 회귀 이력; 임의 vectorization을 먼저 하지 않음 |

기존 API가 없는 것으로 가정하지 않는다. native encoded-u64 API로 불필요한
typed 왕복 변환을 피할 가능성은 있으나, 현재 서버 병목 해결이나 속도 개선은
아직 입증되지 않았다. 별도 검색 엔진이나 source 순회는 추가하지 않는다.

## 실행 단위와 게이트

1. 변경 전 진단: 현재 두 바이너리를 baseline,candidate,candidate,baseline 순서로
   새 디렉터리에서3노드 mixed/45초 부하,20초49Hz CPU 관측한다. 입력·바이너리
   해시와 명령을 미리 고정하고 실패 시 중단, 모든 로그/trace를 보존한다.
   서버 PID만 분석하고 각 실행을 따로 기록한다. 이 단계는 기능 구현 단위나
   전체 성능 게이트가 아니라 다음 최적화 선택의 진단이다.
2. 반복 관측이 뒷받침하면 격리 native 실험: 동결668365ad 기반과 별도 빌드
   디렉터리에 columnar만 복사하고 기존 API를 활용하는 좁은 변경을 시험한다.
   동일 타입 numeric stack 병합만 첫 실험 대상으로 삼고 required coercion,
   혼합 타입, 삭제/재배열 등은 기존 경로를 유지한다. native grouping/serializer,
   merge 정책과 refresh 게시·내구성·보안 계약은 유지한다. 이 최적화의 적용
   범위를 좁히는 것은 기능 지원 범위나 전체 검증 범위를 줄이는 것이 아니다.
3. 정확성 검증: 기존 native columnar 시험 및 before/after 비교로 전체 행 값,
   누락/다중값/cardinality, i64/u64 경계, f64 부호 있는0/비유한값의 기존 처리,
   bool/datetime, required type 오류, 빈/혼합 column, 삭제/정렬 병합을 확인한다.
   원본 typed 경로와 결과 및 가능하면 직렬화 bytes를 대조한다. 기존 지원 계약을
   없애거나 허용 오차를 임의 확대하지 않는다. 국소 benchmark는 추가 진단이다.
4. 구현 단위 완료 전: 전체 engine/node 및 확장 HTTP37fixture/2625case 이상을
   실행하고, 이어 전체 non-plugin6회/12토폴로지를 수행한다. 고정 v0.6.0 대비
   각 topology 처리량>=95%, 모든 scenario mean/p95/p99<=105%를 원본 정밀도로
   각각 확인한다. paired baseline/OpenSearch 및 drift도 보존하며 반복을 합치거나
   유리한 결과만 선택하지 않는다. 빌드/내구성/보안/자원/실제 부하 조건을 같게 한다.
5. 예산을 넘으면 원인 조사·최적화 후 전체 게이트 재실행, 완료 금지다. 해결 못한
   단일 구현의>=5% 악화는 상위 계획의 제외 원장 규칙을 적용하며 제외 기능을
   구현했다고 세지 않는다. 예외 유지에는 명시적 승인이 필요하다. 기준선은
   재설정하지 않는다. 루트 승격이나 릴리즈는 모든 해당 조건 충족 전 보류한다.

역할: Terra는 반복 실행 하네스 같은 제한된 작업, Astra는 native 의미 보존과
성능 원인 판단 및 통합 검토를 담당한다. 측정 중 다른 빌드·테스트·진단은 하지 않는다.

## ABBA 재관측 결과

`target/core-replacement-c06/native-term-table-mixed-three-cpu-abba`의 네 실행이
모두 exit0/요청 오류0/입력 불변 true로 종료했다. 부모 수락은 false다.
아래 비율은 서버 PID만 선택한 perf children 비율이며 합산하지 않는다.

| 실행 | 역할 | merge write | merge fast fields | 서버 CPU초 | 관측초 | 프로파일 포함 ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 00 | baseline | 0.68% | 0.17% | 25.75 | 20.712 | 875.331 |
| 01 | candidate | 12.19% | 8.18% | 25.90 | 20.916 | 826.944 |
| 02 | candidate | 12.19% | 8.02% | 25.94 | 20.767 | 822.627 |
| 03 | baseline | 1.13% | 0.35% | 25.41 | 20.804 | 878.824 |

후보의 native merge 차이가 반복됐다. 그렇다고 baseline과 동일한 문서 가시성이나
merge 발생량이 증명된 것은 아니며 CPU 비율을 HTTP 개선율로 환산하지 않는다.
각 trace의 lost samples는0이다. TokenizerManager::get은 앞3회0.08%, 마지막
baseline에서는 해당 심볼이 관측되지 않았으므로0비용으로 간주하지 않는다.
이 결과는 analyzer clone 변경보다 native column 병합 격리 실험을 우선할 근거다.

result.json SHA-256:
`139d80b95105e3e684e044680b88e8eabdc1e75c470cc0568f7ac80ca402f535`.
plan.json SHA-256:
`696be6d81ce83c345736b857b7c844d259b1de05e02198d98c3e70d2e048a922`.

## 격리 구현 준비

실험 루트는 `target/core-replacement-c06/native-raw-column-merge-experiment`이다.
before/after는 기존 term-table 진단 소스를 복사했으며 양쪽에 같은 columnar0.2.0
원본을 넣었다. after만 homogeneous numeric Stack의 기존 encoded-u64 API 경로를
추가했다. 원본 typed 경로를 테스트에서 선택해 bytes를 직접 대조할 수 있게 했다.
혼합 타입, required coercion, 삭제/재배열은 기존 경로다. root vendor/레지스트리
소스/현재 서버 바이너리는 변경하지 않았다.

columnar 자체 dev-dependencies가 필요해 검증 workspace member로 추가했다.
offline에는 more-asserts가 없어 targeted cargo update와 fetch로 테스트 의존성만
확보했다. 기존 lock의 모든 비실험 package 이름/버전이 보존됐음을 검사했으며,
새18개 package만 추가했다. 같은 lock을 양쪽에 고정하고 이후 locked/offline로
검증한다. 이는 현재 후보의 의존성 업데이트나 성능 통과 증거가 아니다.

## Native 테스트 결과

원본 전체166건과 변경본 전체172건은 모두 실패/ignore/filter0으로 통과했다.
별도 before-build/after-build, nightly/locked/offline, debug정보와 증분 비활성,
2build jobs 조건이다. 원본 테스트는 최신 proptest prelude와 rand0.8 trait import
충돌로 한 차례 compile 실패했으며 양쪽의 테스트 파일에만 `use rand::Rng as _;`를
동일하게 추가했다. 변경본의 첫 compile 실패는 추가 테스트의 -0.0 타입 표기였고
f64를 명시해 수정했다. 최초 실패 로그도 보존했으며 런타임 우회는 없었다.

Terra가 추가 테스트 초안을 작성했고 부모는 bool/date 그룹 선택, f64 타입을
교정하고 비유한값 비트 보존, 잘못된 required type 오류, 전체 빈 column을
보강했다. 여섯 추가 테스트는 원본 typed 경로와 새 경로의 직렬화 bytes를
직접 비교하며, 숫자 경계/부호 있는0/NaN payload/무한대/누락/다중값/bool/date와
혼합 타입·삭제/재배열의 기존 경로를 검증했다. 이는 모든 입력에 대한 증명이나
서버 전체 검증을 대체하지 않는다.

| 보존 파일 | SHA-256 |
| --- | --- |
| before-source.sha256 | b4774aea11e66728a48b4920d5fd2e7c7bc4977e574ce8f64dc08720646151a0 |
| after-source.sha256 | a2746bcf576e32aa5e3e7e1fad3d2332a2aa53b84a37a0e203bcca3e7e30e178 |
| before-tests-v2.log | ae2f437c6c1b100ecf2de370597eda46dd0253bc3f804d072708ebe57ade7f41 |
| after-tests-v2.log | fce3b8cd9d4ff1155939d51781a9b20b51a952be7bd1f0c67e3387361d3764d6 |

위 manifest는 테스트 종료 후 현재 소스의 해시 목록으로 저장한 것이다.
다음은 동일 multi-valued numeric 입력의 별도 release 빌드 국소 성능 비교다.
효과가 확인돼도 전체 engine/node/확장 HTTP 및 전체 non-plugin6회/12토폴로지
게이트를 완료하기 전 단위 수락·루트 승격·릴리즈를 하지 않는다.

## Native raw-column merge measurement result

This is the completed `native-raw-column-merge-experiment` measurement input. It
is diagnostic-only: `execution_inputs_verified=true`, all four runs returned
exit 0, and `acceptance_established=false` in every recorded JSON. The fixed
execution order was `before, after, after, before`; no retry or pooling was
used. The table below was generated programmatically from the four per-run JSON
reports. Timings are the twelve individual measured merge durations in
milliseconds, after one warmup, in recorded order.

The native example uses the parent-corrected `vector_for` numeric distribution,
not the earlier monotonic fixture:
`(((row + 1) * 31 + offset * 17) % 1000) / 1000.0`. The workload is the native
`tantivy_columnar::merge_columnar` plus `StackMergeOrder` path for multivalued
F64 `numbers`, with 8 input segments and 384 values per document. `validation`
is `outputs / rows / values` accumulated across the 13 outputs (one warmup plus
12 measured merges) for that condition.

| Run | Role | Condition | Segments x docs | Input rows | Input values | Output bytes | Validation | Timings (ms, 12) |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| 00-before | before | eight_segments_128_docs | 8 x 128 | 1024 | 393216 | 3145861 | 13 / 13312 / 5111808 | 17.552047; 17.581207; 16.729518; 16.770159; 16.774159; 16.792559; 16.737799; 16.730278; 16.795959; 16.803160; 16.760519; 16.778479 |
| 00-before | before | eight_segments_2_docs | 8 x 2 | 16 | 6144 | 49284 | 13 / 208 / 79872 | 0.265603; 0.265043; 0.273443; 0.263603; 0.261523; 0.278283; 0.263523; 0.262123; 0.269243; 0.262403; 0.262483; 0.292883 |
| 01-after | after | eight_segments_128_docs | 8 x 128 | 1024 | 393216 | 3145861 | 13 / 13312 / 5111808 | 15.301026; 15.267385; 14.367217; 14.399536; 14.445737; 14.351016; 14.400217; 14.381617; 14.455857; 14.537178; 14.314815; 14.446217 |
| 01-after | after | eight_segments_2_docs | 8 x 2 | 16 | 6144 | 49284 | 13 / 208 / 79872 | 0.226442; 0.222803; 0.230802; 0.224282; 0.223162; 0.223762; 0.223802; 0.223563; 0.221562; 0.233882; 0.222562; 0.222322 |
| 02-after | after | eight_segments_128_docs | 8 x 128 | 1024 | 393216 | 3145861 | 13 / 13312 / 5111808 | 15.358506; 15.361506; 14.219855; 14.513258; 14.229615; 14.526778; 14.311775; 14.400456; 14.293656; 14.897982; 14.594339; 14.537177 |
| 02-after | after | eight_segments_2_docs | 8 x 2 | 16 | 6144 | 49284 | 13 / 208 / 79872 | 0.244003; 0.228322; 0.227042; 0.242002; 0.227043; 0.227562; 0.227122; 0.235722; 0.226562; 0.226242; 0.244283; 0.227202 |
| 03-before | before | eight_segments_128_docs | 8 x 128 | 1024 | 393216 | 3145861 | 13 / 13312 / 5111808 | 18.140252; 17.834090; 17.162483; 16.789160; 16.809279; 16.704279; 16.956961; 16.902800; 16.636078; 17.020202; 16.878600; 16.619478 |
| 03-before | before | eight_segments_2_docs | 8 x 2 | 16 | 6144 | 49284 | 13 / 208 / 79872 | 0.274523; 0.262803; 0.263123; 0.289363; 0.263003; 0.263723; 0.264003; 0.262043; 0.261323; 0.261243; 0.269563; 0.264403 |

The before and after numeric values were valid bitwise: each decoded F64 value
matched the expected `to_bits()` value. Encoded bytes were stable across
repetitions within each child. No across-binary encoded-byte hash was recorded;
the earlier native tests provide only limited direct byte comparisons, so equal
`output_bytes` is not reported as cross-binary byte equality.

The earlier native library suites remain unchanged: before had 166 tests and
after had 172 tests, with failure/ignore/filter counts recorded as zero. Those
tests and this microbenchmark are separate from server behavior.

## Measurement provenance

Executable identities are the full SHA-256 values recorded in the measurement
plan and checked against the files:

| Executable | SHA-256 |
| --- | --- |
| `before-build/release/examples/raw_merge_diagnostic` | `3af0039159e184bbe8e013968f9ad7e46291fbf8b851bd4be49b0a260a2eceb1` |
| `after-build/release/examples/raw_merge_diagnostic` | `a4c8364fe03cbba3a81b0871452e136bb429c5dca5db77266c82b369d4962e1f` |

The release-source manifest files and their actual file hashes are:

| Manifest | SHA-256 |
| --- | --- |
| `before-release-source.sha256` | `0c6e868e8a955fb6fa8962612e5865a78cf66119c3ec7a9cd9162a0be320ce2b` |
| `after-release-source.sha256` | `1860b7dc70e85b256adc8c35bc57f0199910bfac5ebc6bf817696dfe872d8db3` |

The result and plan file hashes are:

| File | SHA-256 |
| --- | --- |
| `measurement/result.json` | `480804721a33a283b7d7d070955973b19e40e453e62a4c526fa67929bb1db346` |
| `measurement/plan.json` | `8e2b45e6c9fe399b3e776add60891b72d4808fcdbad8e14f8edcd201df5452bf` |
| `run-comparison.py` | `3dac6b852036a24f7e74878059155e4d22513e006ceec75a9872d246e80413f4` |

Release build logs were preserved. Both finished the optimized release profile
successfully; the before log reports 1m 11s and the after log 1m 12s. Their
actual file hashes are:

| Log | SHA-256 |
| --- | --- |
| `before-release-build.log` | `4b80d12a0f36b2beb92e86f050cbb38fe49ed4608d280b1daee73f86f36ed477` |
| `after-release-build.log` | `f26c550fd8ae2a5375165015e96a3021b3dfe663583b9bf6ad7ef7b5d6025177` |

This result is not v0.6.0 server performance, is not an OpenSearch or release
comparison, establishes no acceptance, and makes no server-improvement claim.
The parent staging server candidate remains separate. No main plan or source
was changed by this documentation update.

## 서버 후보 검증 진행

별도 후보 `target/core-replacement-c06/native-raw-column-merge-candidate/source`는
현재668365ad 서버의 동결 소스를 복사하고 columnar vendor/patch 등록/lock의
source 항목만 변경했다. 기존 package 버전과 애플리케이션 코드는 그대로다.
소스 manifest SHA-256은
`087a84f6f20dcc65178780a706128933e69aca451f5bb301965429c94fd97a12`다.

독립 build에서 nightly/locked/offline, debug정보·증분 비활성,2jobs로 전체
engine966건(946+7+4+9), node1125건(666+459)이 통과했다. 실패/ignore/filter0,
부모 session95708/17259 모두 exit0이며 이후 소스 manifest 검증도 통과했다.
engine-tests.log SHA-256:
`53552f7df72ff621cf5f26615f00efd047c6b5f7739557cd7b708edc065dab1b`.
node-tests.log SHA-256:
`78073890ba8a4e69b67dd85935fe09da5843e928df44289d779b03e71b087133`.

Luna의 국소 결과표는 부모가 원본 JSON의96개 측정값과7개 증거 해시로 재검증했다.
하네스4건은 실패 시 중단, 누락 측정값 및 소스 변경 거부를 확인했다. 모든 서브
에이전트는 검토 후 종료했으며 측정과 빌드/테스트를 동시에 하지 않았다.

다음은 이 동결 소스의 release 서버를 별도로 빌드해 확장 HTTP37fixture/2625case
이상을 이전 후보와 케이스별로 대조하고, 동일 조건의 전체 non-plugin6회/12토폴로지
누적 게이트를 실행하는 것이다. 디스크 보호 임계값을 완화하지 않고 실행 전
자원을 확인한다. 새 서버 성능은 아직 미측정이고 수락0/40/TV1미완료/릴리즈 보류다.

### Release 검증 준비와 공간 확보

후보 source manifest 불변을 다시 확인하고 독립 release 빌드를 시작했다.
HTTP 준비 파일은 `native-raw-column-merge-candidate/artifacts/http-preparation.json`이다.
이전37fixture/2625case와 같은 입력이며 기록 시점에는 바이너리 해시가 pending이다.
그 pending 기록은 실제 실행 결과가 아니다. benchmark matrix 해시 차이는 이미
검증한 초기화 대기 수정(ad0cbbee -> b260a0a3)이며 HTTP runner 해시는 그대로다.

디스크 보호를 유지하기 위해 과거 완료 CPU trace10개를 gzip으로 무손실 보관했다.
각 원본/압축 SHA와 복원 검증은
`target/core-replacement-c06/pre-raw-column-profile-archives.json`에 기록했다.
ledger SHA-256은
`b359f6d3455fb062566561414505fbf4ad9844bff6d5e5058c9285b79146c665`이다.
모두 복원 SHA가 원본과 일치한 뒤 원본 perf.data만 제거했으며681754871바이트를
확보했다. 압축한 원본 경로는 ledger에 모두 남겼다. 기준선·서버 바이너리·결과·
동결 소스는 삭제하지 않았다. 국소 before/after의 debug 캐시215.0/215.2MiB도
정리했으나 측정 release 예제는 원래 경로에서 같은 SHA를 유지함을 확인했다.

### Release 빌드 및 HTTP 결과

후보 release 빌드는 nightly/locked/offline,2jobs,standalone-runtime으로7분57초에
완료했다. 빌드 전후 소스 manifest 검증도 통과했다. 보존된 서버는
`target/core-replacement-c06/native-raw-column-merge-candidate/artifacts/steelsearch`,
SHA-256 `6d7f90e198d3f4f0c75bfa58f13e77430e8d786096c9fc8f69a563833f95635d`다.
candidate-build.log SHA-256은
`092b0d2a17afce33d01290f7c2593372744f056ab68f1542b0038b6fa9742ca2`이다.
서버 artifact를 보존한 뒤 이 후보의 재생성 가능한 build 캐시2.1GiB를 정리했다.
국소 실험 build 디렉터리도 측정 release 예제를 원래 경로에 보존하고 나머지 생성
캐시만 정리했다. 두 예제와 서버의 SHA를 다시 확인했고 사용 가능한 공간은
15684493312바이트였다. 이 정리는 Cargo 빌드 캐시 복원이나 기준선 변경이 아니다.

`native-raw-column-merge-release-live/execution.json`의 HTTP37fixture/2625case는
2353통과/272실패/skip0이며 count probe=true, binary_unchanged/fixtures_unchanged=true다.
실제 실행은 exit1로 종료했고 이전668365ad와2625개 fixture/케이스명별 상태가 모두
같다. 기존 실패가 해결되었다거나 실패 케이스의 모든 응답까지 같다는 뜻은 아니다.
execution.json SHA-256은
`a917d3bcf0b8f3950bba052ba03719fe2023c98133ab9dc1455165bcd8a765e1`이다.
다음 전체 게이트 출력은 `native-raw-column-merge-repeated-full`로 구분한다.

### 전체 게이트 종료: FAIL

`native-raw-column-merge-repeated-full`의 여섯 실행과12토폴로지가 모두 종료됐다.
각 자식 exit0/요청 오류0, execution_inputs_verified=true이며 부모 exit1,
numeric_budget_passed=false다. 단일 처리량720.822/758.555ops/s는 고정v0.6.0
대비-2.99%/+2.09%,3노드876.895/872.433은-5.85%/-6.33%다.
각44지표 중 published15/15,paired5/7,baseline drift23/3개가 예산을 넘었다.
쓰기 mean은 단일+15.39%/+9.66%,3노드+11.12%/+10.91%다.

같은 실행의 baseline 3노드 처리량도857.845/906.109ops/s로 변동이 있다.
이 관측을 후보 실패 원인으로 단정하거나 fixed published 기준선 예외로 쓰지
않는다. 후보의 모든 반복과 회귀를
[전체 시나리오 비교](native-raw-column-merge-performance-2026-09-11.md)에 보존한다.
국소 병합 개선이 전체 누적 예산 통과로 이어지지는 않았다. 이번 결과만으로
새 patch가 남은 전체 회귀를 유발했다고 귀속하거나 지원 기능을 제외하지 않는다.

result.json SHA-256:
`8e76e7327d2cd0b0e78ba6ce1c5446e56f3aef93ff012892489dcdfecdf1d306`.
plan.json SHA-256:
`951ff9a6810bdd9bbfb5ad0845b3c50264ab485419e390d72a999c74369644fa`.

다음 변경은 현재 실행 파일의 잔여 native 병합/직렬화 비용과 쓰기 대기 시간을
측정해 선택한다. 국소 결과만으로 추가 패치를 승격하지 않는다. 새로운 단위도
전체 engine/node/확장 HTTP와 전체 non-plugin6회/12토폴로지 검증을 반복하며
고정 누적5%를 유지한다. root 미승격,0/40,TV1미완료,릴리즈 보류는 변하지 않는다.

### 최신 후보 잔여 CPU 진단

다음 관측은6d7f90e1을 기존 `tools/run-core-cpu-diagnostic.py`로 실행한다.
출력은 `target/core-replacement-c06/native-raw-column-merge-mixed-three-cpu`이며
3노드 mixed45초 중20초49Hz CPU 표본을 수집하고 서버 PID만 분석한다.
바이너리 SHA를 실행 전후 검증하며 다른 빌드·테스트·진단과 겹치지 않는다.
단일 관측은 최신 후보 내부의 잔여 비용 위치를 고르는 근거일 뿐, 이전 후보와의
인과 비교나 개선율 증거가 아니다. CPU 표본으로 off-CPU 대기 시간을 추정하지
않는다. 변경을 선택할 때에는 native 소스/API 및 반복 관측을 추가 확인하고,
구현 단위 완료 전에는 위 전체 정확성·성능 게이트를 모두 다시 실행한다.

관측은 exit0으로 종료됐다. matrix/perf exit0, 요청37226건/오류0이며 실행 전후
바이너리 SHA가 일치한다. 관측20.811초 동안 서버 CPU 합계25.51초,
lost samples0이다. 프로파일 포함 처리량827.176ops/s는 진단값이며 전체 게이트
수치나 이전 후보와의 개선율로 사용하지 않는다.

| 서버 PID 한정 경로 | children | self |
| --- | --- | --- |
| IndexMerger::write | 11.23% | 0.84% |
| IndexMerger::write_fast_fields | 7.26% | 0.00% |
| serialize_u64_based_column_values::<u64> | 7.10% | 0.53% |
| BitpackedCodecEstimator::serialize | 4.05% | 0.23% |
| f64 JSON formatting (zmij) | 2.98% | 2.75% |
| BlockwiseLinearEstimator::collect | 0.84% | 0.38% |
| StatsCollector::collect | 0.15% | 0.15% |

children은 겹치는 호출 비용이므로 합산하지 않는다. BitpackedReader iterator의
self는2.22%, MergedColumnValues iterator는1.07%다. native 병합/직렬화가 잔여
조사 대상으로 남았지만 CPU 표본은 write 대기 또는 HTTP 지연의 인과 증명이 아니다.

동결 소스의 `vendor/tantivy-columnar/src/column_values/u64_based/mod.rs`에서
통계와 모든 코덱 estimator를 첫 순회에 수집하고, 선택된 코덱으로 두 번째 순회에
직렬화함을 확인했다. 같은 디렉터리 `bitpacked.rs`의 serializer는 값마다 기존
BitPacker::write를 호출한다. 다음 격리 실험 선정은 이 iterator/직렬화 경로의
반복 진단과 기존 native API 검토를 우선한다. 코덱 후보 제거, 반환 source 축소,
새 검색 엔진, 가시성·내구성 완화는 이 관측으로 정당화되지 않는다.

증거는 위 진단 출력 디렉터리에 보존한다.

- diagnostic.json SHA-256:
  `78d01d4f8e0c7ff6123301532692e3241e9accd32725ec06ce644f97baf933ae`
- server-self-report.txt SHA-256:
  `fbfd5f46a9dabcf700434f91da0103f0dba2fc8b4de61dff51786de776a2824b`
- server-children-report.txt SHA-256:
  `de7195d2408b06a2edb97b7de771b9a95965ebcb3c4d3a51e151c5e0a066530e`

Luna의 별도 read-only 검토는 전체 성능 보고서의 raw 처리량6행, 지연 실측28행,
실패 목록6개 및 summary6개/result 해시가 원본과 일치함을 확인했다. Luna는
지연 비교율 열을 독립 재계산하지 못했으므로 그 부분까지 재검증했다고 주장하지
않는다. 검토 종료 후 에이전트를 닫고 CPU 관측을 시작했다.

### Native Bitpacked 출력 버퍼 격리 실험 계획

1. `native-buffered-bitpack-experiment/{before,after}`를 이전 raw-column after
   소스에서 동일 복사하고 별도 build 디렉터리를 사용한다. 변경은 after의
   bitpacked serializer 내부 표준 BufWriter 사용으로 제한한다. pinned
   tantivy-bitpacker0.5.0의 generic BitPacker::write는 최대8바이트씩 write_all을
   호출한다. 외부 ColumnSerializer/BufWriter가 있어도 동적 Write 경계는 남는다.
   이 호출 묶음의 효과는 가설이며 새로운 코덱이나 포맷은 만들지 않는다.
2. 출력 bytes/decoded values, 빈 입력·경계값·다양한 bit width와 GCD, 짧은 write,
   Interrupted/WriteZero/영구 오류 전파를 원본 serializer와 비교한다. 추가
   underlying flush, 오류 후 drop 재시도, source 축소나 내구성 완화를 금지한다.
   Terra는 별도 테스트 파일, 부모는 serializer 변경과 통합 검토를 맡는다.
3. 전체 native columnar 테스트 후 동일 raw_merge_diagnostic 예제를 독립
   release 빌드한다. 입력·실행 파일 해시와 before/after/after/before 순서를
   고정하고 두 기존 조건의 모든 측정을 보존한다. 측정 중 다른 작업을 멈춘다.
   국소 개선이 없으면 서버 승격하지 않고 실험 결과를 기록한다.
4. 유효한 실험의 서버 통합은 별도 후보로만 한다. 구현 단위 완료 전 전체
   engine/node/확장 HTTP 및 전체 non-plugin6회/12토폴로지 벤치마크를 실행한다.
   최초 v0.6.0 대비 topology 처리량>=95%, 각 scenario mean/p95/p99<=105%를
   개별 판정한다. 직전 릴리즈/OpenSearch 비교와 반복/drift도 보존한다.
   초과 시 최적화·전체 재검증하며 상위 계획의 제외/명시적 예외 규칙을 따른다.
   국소 성공은 완료나 릴리즈 승인이 아니며 기준선은 재설정하지 않는다.

#### 구현 및 native 검증

after만 bitpacked payload가8KiB 이상일 때 표준 BufWriter8KiB로 기존 native
BitPacker 출력 호출을 묶는다. 더 작은 열은 기존 경로를 유지한다. 정상 종료는
into_inner로 버퍼만 배출하며 하위 writer.flush는 추가 호출하지 않는다. 중간
write와 마지막 배출 실패 모두 into_parts로 버퍼를 분리해 drop 재시도를 막는다.
통계, 코덱 선택, 값 변환, 바이트 포맷, 외부 내구성 계약은 변경하지 않았다.

Terra가 before/after에 동일 테스트4개를 작성했고 부모가 모든 bit width의 큰
입력, GCD10, payload Interrupt 및 중간/최종 버퍼 배출 오류 검사를 보강했다.
전체 native 시험은 양쪽 모두176통과/실패0/ignore0/filter0, 문서 시험1통과다.
동일 nightly/locked/offline/2jobs, dev/test debug0/incremental0이며 양쪽 독립
build 디렉터리를 사용했다. before27.83초/after30.78초의 시험 시간은 성능 비교가
아니다. Python 반복 하네스4개 시험도 통과했다.

두 소스 간 차이는 bitpacked.rs뿐이고 Cargo.lock과 새 테스트는 동일하다.
시험 후 source manifest 불변도 확인했다. 해시는 다음과 같다.

- before-source.sha256: `e6504df5bd26d6ac3da89031fe1bb324cd9ee376839820819ee7d869bb84b4fc`
- after-source.sha256: `adfe2f7040156ba30e0805be5a54f50e5900b637759e9e5c82357797d77b82b0`
- before-tests.log: `3fe00fc75daaec4695cee985b0887cf7c66940eb6d058800cce31bb15cb15b46`
- after-tests.log: `875bb0835bb0ed4c8f84835b3f80f9ab3f015dd482e60c7d853d6a42ccb5aa1a`
- run-comparison.py: `3dac6b852036a24f7e74878059155e4d22513e006ceec75a9872d246e80413f4`

release 예제 빌드와 ABBA 국소 측정은 이 시험의 후속 단계이며 서버 수락은 아직
없다. 기존 raw-column 후보6d7f90e1과 fixed v0.6.0 증거는 변경하지 않았다.

#### 국소 ABBA 결과 및 서버 후보 준비

양쪽 release 예제 빌드는 nightly/locked/offline/2jobs로 각각1분12초에 완료했다.
이후 source manifest가 그대로임을 확인하고 모든 에이전트·빌드·테스트 종료 후
`run-comparison.py --output-dir .../native-buffered-bitpack-experiment/measurement`
를 실행했다.4회/8조건/96개 개별 시간이 모두 보존됐으며 exit0,
execution_inputs_verified=true, diagnostic_only=true, acceptance_established=false다.

| 실행 | 역할 | 조건(8segments의 docs/segment) | mean ms | min ms | max ms |
| --- | --- | --- | --- | --- | --- |
| 0 | before | 128 | 14.639693 | 14.295216 | 15.761391 |
| 0 | before | 2 | 0.226772 | 0.221602 | 0.236722 |
| 1 | after | 128 | 12.597147 | 12.331758 | 13.150526 |
| 1 | after | 2 | 0.201029 | 0.198362 | 0.209082 |
| 2 | after | 128 | 12.615341 | 12.378478 | 13.382728 |
| 2 | after | 2 | 0.202249 | 0.198121 | 0.218642 |
| 3 | before | 128 | 14.573050 | 14.324857 | 15.440348 |
| 3 | before | 2 | 0.230832 | 0.224962 | 0.248083 |

각 큰 조건은13출력/13312행/5111808값, 작은 조건은13출력/208행/79872값을
검증했다. 각 출력의 값 bit/type/cardinality 검증 및 한 실행 내부 출력 byte
안정성이 통과했다. 크기는3145861/49284바이트로 같지만 크기 일치 자체를 두
바이너리 전체 출력 byte 동일 증거로 확대하지 않는다. 별도 native reference
시험의 byte 일치 범위는 위 테스트 입력이다. 이 표는 최초 v0.6.0이나 서버
처리량/지연 비교가 아니다. 원본12개 시간은 각 JSON에 모두 남겼다.

측정 실행 파일 SHA-256:

- before: `a4c8364fe03cbba3a81b0871452e136bb429c5dca5db77266c82b369d4962e1f`
- after: `f781abf94f11a8494a1a21bc69ff33140455d1bd37558ed2be9e3c712e89baf1`

before는 이전 raw-column after 예제와 SHA가 같다. 원본 예제/소스를 수정하거나
대체한 것은 아니다. 다음 증거는 모두 새 실험 디렉터리에 보존한다.

- before-release-build.log: `415fb147246c43f85d418bf5fb8525ab59e1da810684de1c5df695f0b91f2a48`
- after-release-build.log: `f3bd09c41c234a62103261d4737f9615a4b7d9dd9b9d1f55baa208f11e2a594f`
- measurement/plan.json: `bf47841f7a50913b0aa04bb61dd9039b512a1957fd4b5386e68ebc663d472bdd`
- measurement/result.json: `4c6aaa77b72befa0165f89dabc4047aa8514445e1c66e6fdc84532df8644a46a`
- measurement/00-before.json: `7e7822017f1bb453517c405fb626b6f9c9801d25542ac88859c40b43ff09ec6d`
- measurement/01-after.json: `f5f176da2f3c8df8a1b5896bb66ed30a5d2c3b540ed691bf943fcf61d554ad77`
- measurement/02-after.json: `d18f37cd98ab54c9cf4fec6cbb5a1a616ada9a2eb70b1c58a565daf610f33458`
- measurement/03-before.json: `af29949fe8c767f9f3ee9d21b7fb1a3abdc21b9779af710a01d9a671e0b7bcf1`

국소 반복 개선에 따라 다음 서버 후보를
`target/core-replacement-c06/native-buffered-bitpack-candidate/source`에 준비했다.
6d7f90e1의 동결 소스와 비교해 bitpacked.rs와 새 buffered_bitpacked_tests.rs만
다르며 Cargo.lock, 애플리케이션 소스와 다른 vendor 파일은 동일하다.
source.sha256 자체 SHA는
`6e4e1a6434cbd7f4cca64a3375678b62214b75bfc2b84290d5490a85bde11a47`이다.
이 후보의 engine/node 검증은 아래와 같이 완료했다. 확장 HTTP/전체 non-plugin
게이트와 서버 release 빌드는 아직 실행하지 않았다. 완료·root 승격·릴리즈는
계속 보류한다.

#### Buffered Bitpack 서버 소스 검증

서버 후보의 독립 `build` 디렉터리에서 nightly/locked/offline/2jobs,
dev/test debug0/incremental0으로 engine966건(946+7+4+9)과
node1125건(666+459)이 통과했다. 실패/ignore/filter는 모두0이다.
엔진 빌드는2분19초, 각 시험은14.09/8.68/2.22/0.17초였다.
노드의 최종 명령은 `cargo +nightly test --locked --offline -j 2 -p os-node
--features standalone-runtime --lib --bin steelsearch`이며 빌드43.36초,
각 시험4.11/12.22초다. 이 시간은 벤치마크나 속도 개선 증거가 아니다.
각 검증 이후 source.sha256 불변을 확인했다.

초기 노드 명령에 --lib/--bin 제한을 빠뜨려 daemon/플러그인 통합 target도 포함된
것을 발견했다. 시험 실행 전 컴파일 단계에서 해당 cargo PID만 SIGINT로 종료했고
부모 exit130 및 cargo/rustc 종료를 확인한 뒤 올바른 명령으로 실행했다.
중단 로그에 Running/test result 항목은 없으며 통과 결과로 세지 않는다.
이는 실패 케이스를 걸러 재실행한 것이 아니라 이전1125건 target 범위 복원이다.
중단 로그는 `node-broad-build-interrupted.log`로 보존했다.

증거 SHA-256:

- engine-tests.log: `2487258445bcb43c7d211a7b5d2ff54c3de2b1338000a85c826ba02d2a6c77d1`
- node-tests.log: `a4ae0bc6b1aaeb36df6512fe112063e224489170361bb6cc063c30fbe6c6b938`
- node-broad-build-interrupted.log: `757f9529fc875e9d3ad1055656db4ecb1a6fd54dfdaae1e15e21c5583ed85473`

Luna는 `native-buffered-bitpack-candidate/artifacts/http-preparation.json`만
작성했다. 부모가37fixture 해시를 이전 실제 execution.json과 다시 대조했고,
34additional fixture를 포함한 명령은 후보/출력 경로만 바뀌었음을 검증했다.
준비 파일 SHA는 `bc1a513cbb45433edf814126216dcc744dda88a50af8a05f664fb69d14f3e8d0`이다.
37fixture/2625case/count-probe 입력이며 실제 HTTP 검사는 아직 미실행이다.
준비 파일의 executed=false/binary_available=false는 이 시점의 상태다.

완료한 국소 실험의 before-build/after-build 캐시만 정리했고 측정 예제 두 개는
기존 경로·SHA 그대로 보존했다. 소스·로그·측정 JSON·기준선은 지우지 않았다.
정리 전후 파일 크기 합은 before485194913->2170616,
after485245864->2171360바이트이며 이는 파일시스템 가용 공간 증감과 같다는
주장이 아니다. `native-buffered-bitpack-experiment/build-cache-cleanup.json`
SHA는 `dfa2193e8856585158d696914e70406ba45fd625458f74cba27e02e0fddccbd3`이다.
서버 검증 build 캐시는 아직 유지 중이다. 다음 release artifact를 보존한 뒤
재생성 캐시 정리와 실제 가용 공간 확인을 거쳐 OpenSearch 검사를 실행한다.
디스크 안전 임계치를 낮추지 않는다.

다음 순서는 동일 동결 소스의 release 빌드, 준비한 확장 HTTP 검사, 전체
non-plugin6회/12토폴로지 게이트다. 고정 v0.6.0 누적5%와 모든 시나리오
개별 판정은 그대로다. 새 서버 성능 결과는 아직 없으며0/40/릴리즈 보류다.

#### Buffered Bitpack release 검증 준비

동일 source manifest를 다시 검증한 뒤 독립 build에서
`cargo +nightly build --release --locked --offline -j 2 -p os-node
--features standalone-runtime --bin steelsearch`를 시작했다. 증분 빌드는 비활성이고
로그는 새 후보의 `candidate-build.log`에 보존한다. 빌드 시작은 완료 증거가 아니다.

OpenSearch 디스크 안전 여유 확보를 위해 과거 완료 후보
`target/core-replacement-c05/fst-server-candidate/build`의 dev 프로파일 캐시만
`cargo +nightly clean --profile dev`로 정리했다(1469파일/281.6MiB).
정리 전 테스트 로그의 완료와 해당 후보 프로세스 부재를 확인했다.
`build/release/steelsearch`는 원래 경로에 보존했고 전후 SHA는
`dada63998f5a59053255c10bfec1189fa52454edc689ec1ab1f2058f6057077b`로 같다.
과거 소스·release artifact·로그·기준선은 변경하지 않았고 안전 임계치도 유지한다.

release 빌드는7분48초에 exit0으로 완료했다. 컴파일러는
rustc1.97.0-nightly/ad3a598ca4bc7c68bcbbce3e0d3be9a7618df190,
aarch64-unknown-linux-gnu/LLVM22.1.4다. 빌드 전후 source manifest가 일치한다.
`native-buffered-bitpack-candidate/artifacts/steelsearch`에 복사한 서버 SHA는
`a5b38b4932a3386fc495800578f6d76970ca3882437b93f3c60cfc280ec6c6b8`이며
원래 build/release 실행 파일과 같았다. candidate-build.log SHA는
`dbba35148d3a5ec59c739ee95b51f754d92d142a6528aaed2fab53d38eb57028`이다.
artifact 보존 후 이 후보의 독립 build 캐시만 cargo clean으로 정리했다
(3984파일/2.2GiB). 보존 artifact SHA가 그대로이고 가용 공간은15730352128바이트였다.

확장 HTTP는37fixture/2625case,2353통과/272실패/skip0으로 exit1 종료했다.
count probe, binary_unchanged, fixtures_unchanged는 모두 true다.
이전6d7f90e1의 `(report filename, case name)`별2625개 상태와 모두 일치하며
키 중복도 없었다. 실패 응답 payload 전체 동일이나 기존 실패 해결 주장은 아니다.
실제 기능 reference는3.7.0-SNAPSHOT/build f991609d190dfd91c8a09902053a7bbfe0c27b3e다.
`native-buffered-bitpack-release-live/execution.json` SHA는
`3ab8697bd7c995d5b9acec235f25f3729102743ca51298da40d075c7090f1cad`이다.

Luna가 성능 준비 파일을 작성했고 부모가 후보 artifacts 디렉터리로 위치를
바로잡고 --prepare-only를 제거해 실제 전체 실행 명령으로 수정했다.14입력 해시와
기준선 실행 파일을 재검증했다. 이 준비 파일의 executed=false는 작성 시점의
상태이며 측정 결과가 아니다. performance-preparation.json SHA는
`778af280f2ca74a27ceb3096d8c9022799c128c3cdaddff9d57b58e6e4344862`이다.
모든 에이전트·빌드·HTTP 프로세스를 종료한 뒤 전체 게이트를
`native-buffered-bitpack-repeated-full`에 실행한다. 실제 시작 전 가용 공간은
15664861184바이트였다.6회/12토폴로지의 모든 반복·실패를 보존한다.

#### Buffered Bitpack 전체 게이트: FAIL

전체6회/12토폴로지가 완료됐다. 모든 자식 exit0/요청 오류0이며 부모 exit1,
execution_inputs_verified=true, numeric_budget_passed=false,
acceptance_established=false다. 각44지표 중 published12/19,paired10/7,
baseline drift1/18개가 예산을 넘었다. 실행 순서는 원래 계획 그대로다.

| 후보 실행 | 단일 ops/s | 고정 v0.6.0 대비 | 3노드 ops/s | 고정 v0.6.0 대비 |
| --- | --- | --- | --- | --- |
| 01 | 758.783763 | +2.12% | 879.127510 | -5.61% |
| 04 | 739.363070 | -0.49% | 863.650304 | -7.27% |

쓰기 mean은 단일3.162915/3.263121ms(고정 기준선+10.10%/+13.59%),
3노드3.268101/3.345352ms(+10.07%/+12.67%)다.
동시 baseline 대비로도 단일+9.17%/+9.11%,3노드+9.39%/+7.67%라서,
남은 쓰기 회귀를 단순 baseline 변동으로 면제하지 않는다.
동시 baseline 처리량은 단일749.080282/737.075020,3노드927.731380/887.910670이다.
두 번째 반복의 drift18개도 그대로 보존하며 유리한 첫 반복만 선택하지 않는다.

result.json SHA-256:
`987918aebbcc105418c43d2ecfa3091f38ccc9c48ff4df3e2d3a0fcae0eb9575`.
plan.json SHA-256:
`a99399e4dbd1a2593b541ca15fd1aab5c6bc33d969edce9547989a1e763701ca`.
전체 시나리오·OpenSearch 비교와 실패 목록은
[성능 기록](native-buffered-bitpack-performance-2026-09-11.md)에 남긴다.

국소 native 버퍼 실험의 개선은 서버 누적 예산 통과로 이어지지 않았다.
그러나 이 전체 비교만으로 버퍼 patch가 전체 회귀의 원인이라고 귀속하지도
않는다. 다음 조사에서는 추가 columnar 미세 변경을 바로 승격하기 전에 최신
실행 파일의 native 쓰기/commit 경로와 대기 시간을 분리해 확인한다.
기존 CPU 표본의 children 비율은 wall-clock 지연이나 off-CPU 대기의 증거가 아니다.
이미 실행한 writer lock/append 진단과 pinned native API를 먼저 검토하고,
새 진단 후보가 필요하면 기능 의미를 바꾸지 않는 계측만 별도 소스로 분리한다.
기능 제거·source fallback 추가·내구성 완화·허용 오차 확대는 하지 않는다.
후속 구현도 전체 정확성 검사와 전체 non-plugin 게이트를 거쳐 고정5%를 지킨다.
root 미승격,0/40,TV1미완료,릴리즈 보류는 변하지 않는다.

#### 기존 카운터와 실제 write 요청 재확인

새 계측을 만들기 전에 이번 summary의 `resource_usage`에 이미 보존된 native
refresh 카운터 delta를 확인했다. 아래는 해당 측정 구간의 누적 wall-time 초이며
CPU 시간이나 요청당 비용이 아니다.3노드 값은 기존 수집 endpoint 관측이고
세 노드 전체 합계로 해석하지 않는다. 수행된 write/refresh 횟수도 서로 다르다.

| 실행 | 역할/토폴로지 | write 성공 | refresh 성공 | add 초 | commit 초 | reload 초 | ID lookup 초 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | baseline/single | 8003 | 2696 | 0.500740 | 14.457052 | 0.601459 | 2.533047 |
| 0 | baseline/three | 9873 | 3329 | 0.302000 | 11.670639 | 0.383820 | 0.856441 |
| 1 | candidate/single | 8099 | 2730 | 0.618092 | 13.028841 | 0.824683 | 0.422535 |
| 1 | candidate/three | 9394 | 3152 | 0.422471 | 9.452365 | 0.395585 | 0.213767 |
| 4 | candidate/single | 7901 | 2668 | 0.654935 | 13.308115 | 0.810452 | 0.443473 |
| 4 | candidate/three | 9244 | 3101 | 0.415812 | 10.228004 | 0.392942 | 0.219961 |
| 5 | baseline/single | 7889 | 2658 | 0.463369 | 14.919131 | 0.604639 | 2.402642 |
| 5 | baseline/three | 9481 | 3175 | 0.335267 | 12.251870 | 0.364064 | 0.894403 |

관측된 candidate의 commit delta는 baseline보다 작으므로 이 값만으로
commit을 write 회귀 원인으로 단정하지 않는다.
부하 하네스의 `index_document`는 실제로 `PUT /{index}/_doc/{id}?refresh=false`
를 사용한다. native append는 add/commit/reload/lookup을 각각 계측한다.
따라서 다음 조사는 write 요청 경로와 background refresh/merge 간섭을 나누어
확인한다. 기존 native `prepare_commit`의 worker join/restart는 확인했지만
그 사실만으로 worker 재사용을 구현하지 않는다. 기존 노드 카운터 및 append
진단을 재사용할 수 있는 범위를 먼저 확인하고 source 순회나 독자 검색 구현은
추가하지 않는다.

Terra의 전체 시나리오 표는 부모가 원본 JSON으로 다시 계산해 확인했다.
고정v0.6.0 대비 throughput4행의 부호와 OpenSearch 비교1값, result 해시의
누락 문자, 오래된 native 시험 건수를 수정했다. 원본 측정 파일이나 FAIL
판정은 변경하지 않았다.

### 최신 후보 write 요청 경로 및 분리 진단 계획

이번 full gate의 baseline/candidate4실행 각각 단일/3노드 before/after runtime
snapshot(총32개 노드 관측)에서 다음 환경값이 모두 같음을 확인했다:
PERSIST_SHARED_RUNTIME_STATE_PER_WRITE=0,
SYNC_SHARED_RUNTIME_STATE_PER_REQUEST=0,
DEFER_DEVELOPMENT_SHARD_PERSIST_PER_WRITE=1,
DEFER_NATIVE_WRITE_UNTIL_REFRESH=1(모두 STEELSEARCH_ 접두사).
실제 요청은 refresh=false이므로 handle_put_doc_route의 native replay/refresh 및
per-write 디스크 저장 분기는 이 부하에서 실행되지 않는다. 설정을 바꾼 것은 아니다.
따라서 native commit을 이 PUT의 직접 호출 비용으로 보아서는 안 된다.

현재 동결 source의 standalone_runtime.rs에서 확인한 경로는 권한 검사,
write target/routing 확인, JSON/ingest 처리, documents_state mutex 아래 OCC/
버전/동적 mapping/문서 교체/가시성 추적, dirty shard 표시, 응답 직렬화다.
동적 mapping은 이미 존재하는 필드를 건너뛴다. 현재 benchmark는 실제 index명을
사용하므로 resolve_document_routing의 target==resolved_index 빠른 경로를 탄다.
v0.6.0 소스 d987c067의 동일 handler와 비교해 core 골격은 그대로이며,
추가 routing 검증/native replay metadata만으로 지연 원인을 단정하지 않는다.

Luna가 과거 진단 목록을 조사했고 부모가 기존 write-only JSON을 재확인했다.
6086c31c/고정 baseline 단일 노드 각1회는1203.986/1204.657ops/s,
write mean3.312092/3.310266ms였다. 실제 replica는0이며 과거 결과를 최신3노드
수락으로 확대하지 않는다. 혼합 CPU ABBA와 단발 관측의 수치를 혼용하지 않고,
append 표본 평균을 전체 평균의 하한으로 취급하지 않는다.

1. 기존 run-core-cpu-diagnostic.py와 term-table ABBA wrapper를 재사용한다.
   새 wrapper는 `target/core-replacement-c06/run-buffered-write-cpu-repeat.py`다.
   실제 db244133/a5b38b49 바이너리를 baseline,candidate,candidate,baseline 순서로
  3노드 write=100/45초/5000문서/384값/4클라이언트/3샤드/replica1/seed13 조건에서
   실행한다.20초49Hz CPU 표본과 모든 원본 요청 지표를 보존한다.
2. 계획·도구·실행 파일 해시를 고정하고 매 실행 전후 검증한다. 실패 시 중단,
   임의 재시도 없음. 결과는 `native-buffered-write-three-cpu-abba`에 새로 기록한다.
   측정 중 에이전트·빌드·테스트·다른 진단·편집을 하지 않는다. 서버 PID만 CPU
   분석하며 off-CPU 대기/HTTP 개별 지연 인과로 확대하지 않는다.
3. write-only 결과와 기존 mixed gate를 직접 같은 workload로 취급하지 않는다.
   간섭 가능성 또는 요청 경로 자체 조사 중 어디를 우선할지 선택하는 진단이다.
   원본 mixed gate FAIL을 면제하거나 기능 정확성/내구성을 완화하지 않는다.
4. 후속 구현 단위는 native 소스/API 확인 및 전체 engine/node/확장 HTTP,
   전체 non-plugin6회/12토폴로지 검증 후에만 완료 판단한다. 최초v0.6.0 처리량
   >=95%, 모든 mean/p95/p99<=105%의 누적 기준과 제외/명시적 예외 규칙을 유지한다.

#### 최신 write-only ABBA 결과

기존 CPU 하네스15개 시험과 새 wrapper 구문 검사를 통과했다. 기존 wrapper와의
차이는 후보 경로/해시, operation=write 및 설명뿐이다. 모든 에이전트를 종료하고
실행했으며4회 모두 exit0/요청 오류0, 실행 입력·바이너리 불변=true다.
서버 소스/실행 파일은 수정하거나 다시 빌드하지 않았다.

| 실행 | 실제 역할 | ops/s | write mean ms | p95 ms | p99 ms | max ms | 서버 CPU 초 | 관측 초 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | db244133 baseline | 1185.568027 | 3.363996 | 5.172686 | 6.104492 | 75.663791 | 7.92 | 20.619487 |
| 1 | a5b38b49 candidate | 1185.359958 | 3.364735 | 5.157342 | 6.088801 | 113.154856 | 8.14 | 20.618879 |
| 2 | a5b38b49 candidate | 1192.503876 | 3.344450 | 5.116801 | 6.016725 | 82.698404 | 7.95 | 20.619814 |
| 3 | db244133 baseline | 1190.635501 | 3.349787 | 5.128833 | 6.078567 | 97.229680 | 7.93 | 20.613574 |

요청 수는53352/53343/53664/53580이며 실제 원본 분포/최대값도 보존한다.
write-only에서는 기존 mixed gate의 mean 약+10% 차이가 재현되지 않았다.
이는 요청 경로가 모든 조건에서 동일하거나 잠금/스케줄링 문제가 없다는 증명이
아니다. 같은 write 요청이라도 동시 검색/refresh, 문서 가시성 및 작업량이 달라진다.
fixed mixed gate FAIL과 release 보류는 그대로다.

perf 표본은4회 모두 lost samples0이다. 서버 PID 필터의 기본 백분율 출력과
`--percentage relative` 출력을 별도 파일로 보존했다. 상대 출력은 선택한 서버
표본 안의 비율이므로, 기본 비율과 혼용하거나 CPU/HTTP 개선율로 환산하지 않는다.
상위 self에는 JSON 파싱/할당/atomic/eventfd 등 공통 경로가 보였으나 작은 표본으로
특정 경로를 회귀 원인으로 지목하지 않는다. off-CPU 대기는 이 관측에 없다.

- plan.json SHA: `f9a3d18daf8a2a5303c75a4b1417e64bd1bd327ff40332f1250b897e2a38638f`
- result.json SHA: `a48550754331c274c126eee12355491a613e62ae48f0a7b53a7f5ea7b7203d36`
- 00-baseline/server-relative-self-report.txt: `b0643eb22de4fad99a88bc1c6e024eac41a283395a16a27baaeeebef3200529c`
- 01-candidate/server-relative-self-report.txt: `be7095040e3060853259ceda8a429e353b5eacdbd3f93dbd9e7e67b54bdb8359`
- 02-candidate/server-relative-self-report.txt: `f2f691460b2f8c8e4c923293b8cbae668e01d54c9bd4f18984864a2d0482f286`
- 03-baseline/server-relative-self-report.txt: `ffe5b2f3848e3f3860fdc85f371f52b0c56c912e0ab2a8bba5404e1e75ce58ae`

다음 선택은 새 custom 검색이나 commit worker 재구현이 아니라, 기존 부하 도구로
검색과 refresh를 분리하여 mixed 간섭이 어느 조건에서 재현되는지 확인하는 것이다.
실제 측정에 앞서 workload/순서/해시/실패 중단을 고정하고 모든 결과를 보존한다.
이 분리 진단 또한 전체 구현 성능 게이트를 대체하지 않는다.
