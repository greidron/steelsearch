# Native ranking 경로 조사

작성일: 2026-09-10. 정식 구현 수락0/40, 릴리즈 보류.

## 범위와 원칙

native 처리를 먼저 검토한다. source fallback의 존재를 Tantivy 기능 부재로
해석하지 않는다. 기존 API 재조합과 통계 확장을 검증한 뒤, 실제 부족함이
입증된 부분만 별도 구현한다. 정확도 허용오차와 성능 예산은 임의로 바꾸지 않는다.

아래 조사 단계의 변경은 `cfg(test)` 진단 모듈과 문서뿐이었다. production 검색 경로,
후처리 guard, 성능 workload, 참조 버전, 합격 기준은 변경하지 않았다.
시험 경로의 수치 개선은 성능 개선률이나 OpenSearch 전체 호환성 증거가 아니다.

- 고정 의존성: Tantivy0.21.1. registry 소스와 실제 연결 코드를 직접 읽었다.
- 진단: 8문서,8쿼리,1/3샤드의16조합. 모든 문서를 수집해 ID별로 점수를 비교했다.
- 경로: 현재 native 쿼리 / 순수 source scorer / 기존 native API 재조합 시험 경로.
- 참조: 동일 입력으로 OpenSearch3.7.0-SNAPSHOT에 HTTP 검색했다.
- HTTP 후보: 기존 고정439725ca. 시험 경로는 서버에 반영하지 않았다.
- 검사 대상은 작은 초기 적재 자료다. 갱신/삭제/merge/대규모/전체 분석기/권한/
  min_score/페이지 경계 또는 전체 query DSL 동등성을 증명하지 않는다.

## 라이브러리와 연결 코드 구분

| 기능 | 고정 버전에서 확인한 지원 | 현재 연결의 쟁점 |
| --- | --- | --- |
| match, multi-match | TermQuery, BooleanQuery, DisjunctionMaxQuery, BoostQuery | 조합은 이미 사용 중. bool에 포함되면 source 재평가 대상으로 분류될 수 있음 |
| BM25 통계 | Bm25StatisticsProvider, EnableScoring::enabled_from_statistics_provider | native_bm25.rs에서 이미 사용. field 문서 수와1/2.2 보정은 match에는 적용되지만 phrase에는 누락 |
| phrase/slop | PhraseQuery::new_with_offset_and_slop | phrase 생성 자체는 native. boost 누락 및 점수 보정 불일치가 있음 |
| minimum_should_match=1 | 중첩 BooleanQuery로 optional 그룹을 한 번 필수화 가능 | 현재 조합 전개가 겹치는 분기의 점수를 중복 합산함 |
| 배열 위치 | postings POSITION_GAP=1, Document::add_pre_tokenized_text 지원 | 기본 위치 간격은 참조와 다름. source 문자열 순회가 유일한 해결책인 것은 아님 |
| sloppy phrase 점수 | PhraseScorer의 phrase_count는u32, BM25에 전달 | 위치 매칭 지원과 거리별 점수 동등성은 별개. 실제 점수 차이를 아래에서 관측 |

소스 위치:

- `crates/os-engine-tantivy/src/lib.rs`: build_tantivy_query,
  build_tantivy_minimum_should_match_query, build_tantivy_match_phrase_query,
  query_requires_native_candidate_post_filter, opensearch_phrase_bm25_score_with_bm25_context.
- `crates/os-engine-tantivy/src/native_bm25.rs`: FieldStatisticsCache::wrap,
  NormalizedBm25Query::weight. 통계 provider를 새로 발명해야 하는 상황이 아니다.
- Tantivy0.21.1: query/boolean_query/boolean_query.rs, query/bm25.rs,
  query/phrase_query/phrase_scorer.rs, postings/postings_writer.rs,
  schema/document.rs, tokenizer/tokenized_string.rs.
- 로컬 OpenSearch TextFieldMapper.java의 기본 position_increment_gap은100이다.
  로컬 Java 소스가 실행 중인 snapshot 바이너리와 동일 빌드임을 인증한 것은 아니다.
  실행 서버의 배열 경계 차이는 별도의 HTTP 결과로 확인했다.

## 실제 관측

| 항목 | 실제 결과 | 판정 |
| --- | --- | --- |
| match/title, match/body, multi-match | 1/3샤드 모두 native와 참조의 문서 집합 동일, 최대 절대 점수 차이 약1.20e-7, ID별6자리 반올림 동일 | 작은 수치 차이. 전면 source 재계산 필요성은 이 자료로 입증되지 않음 |
| bool-overlap | 참조 exact/gap/repeat는3점, 현재 native와 HTTP는6점 | 현재 bool 조합의 실제 오류. native optional 그룹을 한 번 필수화한 시험 경로는 문서 집합/점수 정확히 일치 |
| phrase/slop0 | 참조 repeat:0.071189076(1샤드),0.14633575(3샤드). 현재 HTTP:0.049147565/0.100778401 | source의 고정freq=1 계산은 반복 phrase를 제대로 반영하지 못함 |
| 보정한 native phrase/slop0 | 문서 집합 일치, 최대 절대 차이 약7.46e-8, ID별6자리 반올림 동일 | 기존 통계/boost wrapper를 native PhraseQuery에 적용하는 것으로 이 사례 해결 가능 |
| phrase/slop1, gap 문서 | 참조0.035959877/0.06822772, 보정 native 약0.056249216/0.108688384 | 거리별 점수 차이 잔존. 단순 float 반올림 오차가 아님. 정확한 freq/거리 가중 계약은 explain 등으로 후속 검증 |
| phrase boost=2 | 참조 exact 점수2배, 현재 HTTP는 boost 없는 점수 | HTTP와 native 연결 양쪽의 boost 적용 경로를 점검해야 함 |
| 배열 [alpha,beta], slop1 | 참조는 불일치, 현재 HTTP 및 보정 native 시험 경로는 일치 | 위치 간격/매칭 의미 차이. 점수 허용오차로 면제 불가 |
| full-ranking | 현재/시험 경로 모두 array 문서를 잘못 추가. 시험 경로도 공통 문서에서 최대 상대 차이 약1.45%/3.28% 잔존 | bool 중복 수정과 phrase 정규화만으로 전체 native 전환을 완료할 수 없음 |

순수 source helper의 slop0은 array 문서를 잘못 매칭하지만 실제 HTTP slop0은
native 후보 선별에서 제거한다. 순수 helper 관측과 실제 HTTP 응답을 혼동하지 않는다.
반면 slop1 및 full-ranking에서는 실제 HTTP에서도 array가 잘못 반환됐다.

## 오차와 동점

- 원래 ordered HTTP 판정은16건 중1통과15실패/skip0이다. 원본 판정을 변경하지 않았다.
- 그중1-match-title/body/multi-match,3-match-title/multi-match의5건은 문서 집합과
  ID별6자리 점수가 같고 동점 문서 순서가 다르다. 이것을 새 합격 정책으로 자동 면제하지 않는다.
- 나머지10건에는 실제 점수 또는 문서 집합 차이가 있다. 전체15건을 미세 오차로
  설명하거나 모두 신규 runtime 변경으로 발생한 회귀라고 부르지 않는다.
- ID별 진단은 모든 hit를 수집한 이 자료의 원인 분리다. top-k 잘림/순위 품질 검증을
  대체하지 않는다. 원시 OpenSearch 점수를f32로 환산한 차이와6자리 비교를 별도 기록했다.
- 절대/상대 허용오차, 동점 처리 및 top-k 기준은 아직 확정하지 않았다. f32 비트 동일성을
  보편적 OpenSearch 호환성 기준으로 강제하지도, 의미 차이를 수치 오차로 덮지도 않는다.

## 증거와 재현

테스트: `crates/os-engine-tantivy/src/native_ranking_audit_tests.rs`.
원래 bool 중복 assertion은 진단용이었으며 의도한 API 계약이 아니다.
아래 후속 production 수정에서 같은 사례를 올바른3점 회귀 테스트로 전환했다.

```sh
mkdir -p target/native-ranking-audit-new
env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 \
  STEELSEARCH_NATIVE_RANKING_AUDIT_OUTPUT="$PWD/target/native-ranking-audit-new/diagnostic.json" \
  cargo +nightly test --locked --config profile.dev.package.os-engine-tantivy.debug=0 \
  -p os-engine-tantivy native_ranking_leaf_and_bool_audit -- --nocapture
jq '.reference_fixture' target/native-ranking-audit-new/diagnostic.json \
  > target/native-ranking-audit-new/reference-fixture.json
```

진단 출력 파일은 create_new로 생성하므로 재실행에는 새 파일 경로를 사용한다.
실제 사용한 HTTP 명령과 fixture/바이너리 해시는 reference-live/execution.json에 있다.
기존 run-live.py가 기본3개 공통 fixture1500건도 함께 실행한 결과는1501통과15실패다.
이는 확장2214건 전체 비교를 대체하는 실행이 아니다.

`target/core-replacement-c06/native-ranking-audit/` 아래 증거 SHA-256:

| 파일 | SHA-256 |
| --- | --- |
| diagnostic.json | 7059f6790efc9814764312484586f7c585a94ae5f06eb7bde9b5e529942a0960 |
| reference-comparison.json | 7c722ffb174aa32cd3400e100bf9e976e0cb4587fab72608d6720f0af069ebef |
| reference-fixture.json | 8a9112d3186ae5bb7c0bee6018fa231bb81260a9210f15bd9aefbdafaa7fd9ad |
| reference-live/execution.json | 3f1f08c60c246a11f7d6ea0be9cf32125029d75e6bd2903b2c39235abd6579a0 |
| reference-live/reference-fixture-report.json | e8e1c3cd1e74f5bdb8fc835d8507babc63cc170a642fbd1e2b79bd809f5c1334 |
| engine-full.log | 6ae8f88c32f979922fa8ddff1ceabe7b2f0c7e62e067cd2bef0c17fd92fa46c0 |
| focused.log | 07949b815dee9e9936f1491175803609becc7cd3d2f58e2b045a1d609e407034 |

집중 진단1건 통과/932filtered, 전체 engine933건(913+7+4+9) 통과/실패·ignore·filter0.
전체 시험 시간15.05/14.91/2.94/0.33초, 종료0. source lib.rs는 시험 모듈 선언2줄만
439725ca 고정 소스와 다르다. lib.rs SHA-256:
e05d3bfb97cf00a1408331ab5ddceeeea2129973d7b77b2b325187b1d811dc5b.
진단 모듈 SHA-256:
cbd10a9a89a443725a465dccc6744a971f49a5d1fb8e77a611b050d981957d4a.

## 다음 구현 순서

1. native bool의 minimum_should_match=1을 중첩 optional 그룹으로 표현하고,
   중복 점수 방지/필터0점/중복 should/boost/빈 조건/오류 가시성을 검증한다.
   >1 조건은 별도 조합 계약이므로1의 검증으로 완료 처리하지 않는다.
2. exact phrase의 통계·빈도·boost 연결을 native scorer 기반으로 정합화한다.
   term 및 multi-match와 함께 source 재평가가 정말 필요한 eligibility 조건을 검증한다.
   현재 진단은 승인된 정확도 계약이나 production native 전환 자체가 아니다.
3. sloppy phrase의 explain/거리별 빈도와 배열 위치 gap 계약을 확인한다.
   위치를 제공하는 native 색인 API와 scorer 확장부터 검토한다. source 전체 순회를
   기본 대안으로 삼지 않는다. 매칭 오류를 허용오차로 면제하지 않는다.
4. 동등성이 확인된 경로만 native 처리로 전환하고 나머지는 명시적인 미완료로 남긴다.
   갱신 통계/soft-delete 수명 문제도 별도 검증하며 초기 적재 결과로 완료하지 않는다.

각 production 구현 단위 뒤 집중 테스트/확장 HTTP와 **전체 non-plugin 반복 benchmark**를
실행한 뒤 판정한다. 최초 v0.6.0 대비 누적 throughput>=95%, 각 시나리오 mean/p95/p99<=105%,
동일 실제 입력과 실행 파일 출처/별도 빌드/paired/drift 기준을 유지한다.
이번에는 시험 모듈만 추가했고 새 production 후보나 성능 수치를 만들지 않았다.
최신 전체 성능 판정은439725ca의 FAIL 그대로이며 수락0/40, 제외0, 릴리즈 보류다.

## 후속 native minimum-one 수정: 정확성 개선, 전체 성능 FAIL

- 2026-09-10: production build_tantivy_minimum_should_match_query에minimum=1 경로를
  추가했다. required/excluded를 한 번 구성하고, should만 담은 native BooleanQuery를
  한 번 Must로 연결한다. 기존 조합 전개는>1에만 남긴다. source scorer나 새 custom
  scorer를 구현하지 않았다. phrase/정확도 기준/후처리 guard는 변경하지 않았다.
- 진단의 native6점 assertion을 올바른3점 회귀 assertion으로 전환했다.
  추가 테스트 native_minimum_one_preserves_matches_and_scores_across_overlapping_shoulds는
  1/3샤드, should1..4(중복 포함), required/filter/excluded 유무의64조합을
  각16문서에 적용해 source와 native 후보/점수를 비교한다.
- 전체 engine934건(914+7+4+9) 통과, 실패/ignore/filter0, 종료0.
  각15.37/15.27/2.88/0.38초. 아직 구현 단위 완료가 아니다.
  target/core-replacement-c06/native-minimum-one/engine-full.log SHA-256:
  2ed01f2e5912efe8e9248983ce49f8a610edfb40e8b08fe7e48195861867e9d7.
  root lib.rs SHA-256:
  81071cc23b63628f8597f65d1dd87cee0aa9a04cde72849a6cf2c2d6d44b031b.
  native_ranking_audit_tests.rs SHA-256:
  7c1fbbb0a72cd18bf4cb810b2806f829221a212d5f02943c36e2dca69a99456c.
- 독립 source/build/artifacts는 target/core-replacement-c06/native-minimum-one-candidate.
  source crates는 root와 동일하고, 이전 frozen vendor/lock 조건을 유지했다.
  source.sha256 manifest SHA-256:
  faabf2adce8d5777c2254e9e67f6f4eee3aae251e201cb0c405fad6868ad1899.
- HTTP는 기존2214건과 원래16건 진단, 명시적 동점 정렬16건, 무정렬 단일 결과2건을
  비교했다. 명시적 정렬은 기존 latency의 유일한 값을_score 다음 키로 지정한다.
  이 정렬은 source 처리 경로를 선택하므로 이전439725ca도 bool2건을 통과했다.
  따라서 명시적 정렬만으로 native 수정 효과를 주장하지 않는다.
  단일 결과2건은 원래 bool에 latency=0 필터만 추가해 동점 없이 native 경로를 검증한다.
  이전439725ca는6점으로 실패했고 현재daede139는 OpenSearch와 같은3점으로 통과했다.
  원래 ordered bool2건은 ID별 점수는 같아졌지만 동점 순서가 달라 실패를 유지한다.
  허용오차나 기존 ordered 판정을 바꾸지 않았다.
- 독립 release 빌드8분04초/종료0, artifacts/steelsearch SHA-256:
  daede1396c497aa217fb16b68a7bd5d844c045fd5f590799464b06b9c8c92e7f.
  candidate-build.log SHA-256:
  875a7f908ab0e00a40ee784f5bbd07aefc694741580f232168d68251b1cad001.
  source manifest 전체 검증 통과. artifacts 보존 후 후보 release 캐시682MiB만 정리했다.
- target/core-replacement-c06/native-minimum-one-release-live: 30실행,
  HTTP2248건 중2208통과40실패/skip0, count probe 통과,
  binary_unchanged/fixtures_unchanged=true, 최종 종료1이다.
  실패는 반복 갱신 routing17건, 원래 native 진단15건, 명시적 정렬 진단8건이다.
  execution.json SHA-256:
  c72997b88c2613a54c8a0745e3a9f6c1d8eb7388aebf93278f9afbedfeae5583.
  single-hit-reference-fixture-report.json SHA-256:
  74261282acd91948249051b69a69bfa5a46846164a02ca58d01a6f638fcdf5d6.
- target/core-replacement-c06/native-minimum-one/single-hit-reference-fixture.json SHA-256:
  ce308bb6c57ffa8493be5097ba043b7b33514ebebc3b9d902face73d1c58b19b.
  previous-single-hit-live/execution.json SHA-256:
  e3381e10322a3d5ba9b1bc7454de1e0f5a090f400a0ac28e291d09751ba37b1a.
  previous-stable-live/execution.json SHA-256:
  58ee9ac98bda6b4b9eb4c48acd8442bb7b28bb2a2121559855d80b8246befd66.
- 동일 내용의 영구 회귀 fixture:
  tools/fixtures/search-native-bool-minimum-one-scores-compat.json.
  위 single-hit fixture와 바이트/해시가 동일하며, 원래 실행 증거의 경로를 바꾸지 않았다.
- 전체 non-plugin 반복 benchmark는 native-minimum-one-repeated-full에서 수행했다.
  1101.790초,6하위 실행 종료0/12토폴로지 요청 오류0, 최종 종료1이다.
  execution_inputs_verified=true, numeric_budget_passed/acceptance_established=false.
  후보 처리량은 단일492.684/483.359,3노드742.530/744.123ops/s다.
  최초 v0.6.0 대비 단일33.691%/34.946%,3노드20.276%/20.104% 감소했다.
  published44지표 중20/21실패, paired16/19실패이며 기준 drift도8/3지표 실패다.
  단일 ranking 평균21.712/22.096ms는 v0.6.0 대비238.570%/244.569% 증가,
  OpenSearch 대비76.468%/78.617% 증가다. 총 처리량 우위로 상쇄하지 않는다.
  모든 시나리오 mean/p95/p99 표와 반복 출처는 주 구현 계획의 후속 절에 기록했다.
  result.json SHA-256:
  a54f65c538d38343902eb9e0b9b27beb71f3af04d6df4bdc2a9d3e631b305a63.
  plan.json SHA-256:
  e382c85d3598f70129591cc30d48d48aaaf912e24470ee8c7774001a4a476d1e.
- 이 결과는 전체 후보 누적 회귀다. 이미 회귀가 있던439725ca와의 별도 단독 A/B가
  아니므로 이번 bool 수정이 회귀를 일으켰다거나 개선을 전부 만들었다고 단정하지 않는다.
  최초 v0.6.0 누적5%/시나리오별/반복/동일 실제 입력 및 출처 조건을 유지한다.
  단위 미완료, 정식 수락0/40, ledger 제외0, 릴리즈 보류다.
- 다음 native 전환은 phrase 통계/boost 생성만이 아니라 native 검색 후
  opensearch_text_bm25_score가 source 점수로 덮어쓰는 경로도 함께 다룬다.
  검증된 eligibility 조건에서만 재계산을 제거하며, 단일/샤드 검색, 명시적/기본 정렬,
  boost, 반복 phrase 빈도, min_score/페이지 경계 및 오류 가시성을 검사한다.
  sloppy phrase의 거리 가중과 배열 위치 gap은 먼저 native 확장/API 및 참조 explain으로
  검증한다. 새 source scorer를 기본 대안으로 만들지 않는다.
  이 구현 단위도 집중/HTTP 이후 전체 non-plugin 반복 benchmark로 다시 판정한다.

## Phrase explain 및 native 위치 API 검증

2026-09-10 후속 조사다. production 코드/후처리 guard/수치 허용오차는 변경하지 않았다.
기존 고정 daede139 후보의 전체 성능 FAIL이 최신 판정이다. 아래28건은 구현 완료가
아니라 native 확장과 연결 범위를 결정하는 비교 증거다.

- 영구 공통 fixture: tools/fixtures/search-native-phrase-explain-compat.json.
  기존8문서,1/3샤드,slop0/1/2/3/99/100/101,boost1/2의28조합이다.
  explain=true, 무정렬/size100을 사용하며 source 정렬 경로로 우회하지 않았다.
- native_phrase_frequency_and_position_audit는 같은 fixture를 읽어 실제 native postings
  위치, native Query::explain, 기존 통계/boost API 재조합의 explain을 수집한다.
  출력 환경변수 STEELSEARCH_NATIVE_PHRASE_AUDIT_OUTPUT는 create_new 파일만 생성한다.
  원본 진단은 focused 단계 소스의 출력이며, 이후 추가한 위치 API 시험은 별도 테스트다.
- target/core-replacement-c06/native-phrase-explain/reference-live의 참조는
  OpenSearch3.7.0-SNAPSHOT/Lucene10.4.0, build_hash f991609d190dfd91c8a09902053a7bbfe0c27b3e다.
  실제 HTTP28건 모두 실패이며 공통 fixture1500건은 모두 통과, skip0, 최종 종료1이다.
  binary_unchanged/fixtures_unchanged=true. 원래 ordered 판정을 변경하지 않았다.
  이는 기존2248건 확장 suite 전체의 재실행이 아니므로 결과를 합산하지 않는다.

| 문서 | 실제 참조 매칭/phraseFreq | 현재 native 위치/빈도 | 의미 |
| --- | --- | --- | --- |
| exact | slop0부터1 | alpha0/beta1,빈도1 | 통계/boost 연결 대상으로 확인 |
| repeat | 모든 검사 slop에서2 | alpha0,2/beta1,3,빈도2 | source의freq1 고정 대신 native 반복 빈도 사용 가능 |
| gap | slop1부터0.5 | alpha0/beta2,빈도1 | 거리 가중이 빠져 있음 |
| wide-gap | slop2부터0.33333334 | alpha0/beta3,빈도1 | 작은 수치 오차가 아님 |
| reverse | slop2부터0.33333334 | alpha1/beta0,빈도1 | 역순 비용2 및 거리 가중 검증 필요 |
| array | slop99까지 불일치,100/101에서0.00990099 | alpha0/beta2,slop1부터빈도1 | 위치 간격과 가중 빈도를 둘 다 수정해야 함 |

1/3샤드 및 boost1/2에서 위 빈도 계약은 동일하다. boost2는 빈도가 아닌 최종 점수를
두 배로 만든다. ID별 진단의 native 통계/boost probe는 exact/repeat의 점수는 근접하지만,
1샤드 gap에서 참조 대비56.422%, wide-gap123.848%, reverse98.123% 높다.
array/slop100은 약50.062배다. 이 값들을 반올림 허용오차로 면제하지 않는다.
위치는 현재 native postings에서 직접 읽었고, 참조 배열의 구체적 postings 위치를
termvectors로 읽었다고 주장하지 않는다. 참조 경계는 HTTP 매칭 및 explain으로 확인했다.

### Native 확장 경계

- Tantivy0.21.1의 PhraseScorer::phrase_count는u32이며 Bm25Weight::score도u32 빈도를
  받는다. Query/PhraseWeight의 explain도 이 정수 빈도를 확인해 준다. 위치 매칭 자체가
  없다는 뜻이 아니라, 참조의 fractional 거리 가중을 기본 scorer 그대로 얻을 수 없다는 뜻이다.
- 사용한 참조 배포 lib의 lucene-core-10.4.0.jar에서 javap로 SloppyPhraseMatcher를
  확인했다. sloppyWeight 바이트코드는1.0f/(1.0f+matchLength)다. 실제 explain과 일치한다.
  다중 단어/반복 단어의 nextMatch 열거 계약까지 단순 모든 위치 조합의 합으로 가정하지 않는다.
  JAR의 경로는 /home/ubuntu/OpenSearch/distribution/archives/linux-arm64-tar/build/install/
  opensearch-3.7.0-SNAPSHOT/lib/lucene-core-10.4.0.jar이며, 로컬 Java 소스가 동일 빌드라고
  추정한 것이 아니다. 이 기록은 디스크 JAR 검사이며 실행 중 클래스 로딩 계측은 아니다.
- native_pre_tokenized_gap_preserves_term_scores_and_norms는 기존 native tokenizer의 토큰을
  PreTokenizedString으로 공급하고 beta 위치를101로 지정한다. postings에서101을 확인했고,
  fieldnorm2/총 token6/동일 term 점수의f32비트가 유지됐다. forward5조건/reverse6조건에서
  native PhraseQuery와 Count의 경계도 통과했다. production 색인 방식은 아직 바꾸지 않았다.
- production build_tantivy_schema는 Text를 기본 TEXT로 만들며 TantivyFieldMapping과
  TantivyIndexedField에는 position_increment_gap 전달 정보가 없다. add_json_value_to_tantivy_document는
  배열의 문자열마다 add_text를 반복한다. 기본100만 무조건 주입하는 것으로 전체 설정
  호환성을 완료하지 않는다. 사용자 설정, 분석기 및 빈/누락/중첩 값의 위치 처리도 연결해야 한다.

### 검증 결과와 다음 단위

- focused native 진단1통과/934filtered, 종료0. 이후 위치 API 시험을 추가한 root 전체
  engine936건(916+7+4+9) 통과, 실패/ignore/filter0, 종료0이다.
  전체 시험16.36/15.03/2.87/0.32초, 빌드1분25초다. root production lib.rs는 daede139와 같다.
- native_ranking_audit_tests.rs는 공통 tools fixture를 include_str로 읽는다. 다음 독립 source
  snapshot에는 이 fixture도 포함해 테스트 소스 의존성을 보존해야 한다.
- 다음 production 단위는 native 통계/boost 연결 및 검증된 query의 source 점수 덮어쓰기
  제거를 함께 구현한다. 배열 위치는 native 토큰 API로 연결하며 설정·reader 수명을 검증한다.
  sloppy scoring은 native postings/docset을 유지하는 좁은 확장을 우선하며, fractional 빈도,
  반복/다중 단어/순서/boost/explain을 실제 참조로 검증한다. source 전체 순회를 새로 구현하지 않는다.
- 정확성 eligibility와 min_score/top-k/페이지/정렬/선택 샤드/갱신 통계/오류/권한을 유지한다.
  각 구현 단위 뒤 집중 테스트, 확장 HTTP, **전체 non-plugin 반복 benchmark**를 수행한다.
  최초 v0.6.0 대비 throughput>=95%, 모든 mean/p95/p99<=105%, 반복/동일 실제 설정 및
  바이너리 출처 기준을 유지한다. 이번 테스트 추가로 새로운 성능 수치나 구현 수락을 만들지 않는다.

target/core-replacement-c06/native-phrase-explain/ 증거 SHA-256:

| 파일 | SHA-256 |
| --- | --- |
| diagnostic.json | 7c175b8560806267036ec33ff2be4389bfae1576b5d2dd55408e007266360bfc |
| reference-comparison.json | 87fbaa0287130c81c585a18199c6f048ea59cae36c92dc2fa74cb45b118883a6 |
| reference-live/execution.json | c91ff1ac409329f814436164899de2dd5d90d8b603d5417a40b7a9ef7d7eb3de |
| reference-live/search-native-phrase-explain-compat-report.json | a1734f66de88deb67fa43cebda71f2d1928276626dfb3f9b8e3c94f0ab5eb053 |
| SloppyPhraseMatcher.javap.txt | 257a2a07ed98bc25ef1adca7b2e0f0e7256de6a533b266b0776ec5bddf6e7f4d |
| engine-full.log | ee92938831b91812651bd27cfd8e0e66e070fab830b49953df26debc67e84c4b |

fixture SHA-256: dd9de68f342551d857e8e51a10b4955b22acd0c841c19a71611a951be30967b9.
시험 모듈 SHA-256: 0dc0d4e8438bf05841e93020606d36537387378f4e846fa73816ea9c04599d52.
참조 Lucene JAR SHA-256: 8f894d211a8123938ccb9ff6827d136747e0eb6b1782ada6ac9086aa911b52e2.
모든 시험/HTTP 프로세스는 종료했다. 정식 수락0/40, ledger 제외0, 릴리즈 보류다.

## Native Exact Phrase Production 연결 (후속 단위, 전체 성능 FAIL)

위 조사 종료 후 production 연결을 진행했다. 이전 단계의 시험 수와 성능을 이 후보의
검증으로 재사용하지 않는다. source 순회 기반의 새 phrase scorer는 추가하지 않았다.

- PhraseQuery/단일 토큰 TermQuery에 기존 native FieldStatisticsCache를 연결하고 boost를
  전달한다. 검증된 top-level slop0 phrase는 반환 단계에서 source BM25로 덮어쓰지 않는다.
- 필드 정렬의 선택 DocAddress는 같은 native Weight/Scorer로 점수를 읽고 collector 순서로
  복원한다. segment별 forward seek를 사용한다. source 문서를 재분석하지 않는다.
- eligibility는 기본 Text, ASCII/짧은 토큰, 기본 분석기/norm/positions/BM25, slop0,
  유효 양수 boost로 제한한다. 선택 샤드의 refreshed 통계와 문자열/null/배열 값 호환성을
  확인한다. dotted/multi-field, 숫자/객체/비ASCII 또는 미확인 옵션은 기존 fallback에 남긴다.
- 매핑의 분석기/gap/norm/index_options/similarity 원형을 선택적 boxed JSON 메타데이터로
  보존한다. 기존 허용 입력을 새 타입 검사로 거부하지 않는다. 문자열 "true"/"100"도
  보존하되 이 단위에서 native eligibility를 확장하지 않는다.
- 복구 시 추가된 기본 Text 메타데이터만 제거했을 때 기존 schema hash가 정확히 일치하는
  경우에만 제한적 전환을 허용한다. 다른 필드/인덱스/비기본 옵션 변화와 checksum 검사는
  그대로다. 이는 모든 v0.6.0 저장 형식의 마이그레이션 인증이 아니다.
- native score=0을 임시 score=1로 바꾸는 보정을 해당 경로에서 끈다. 최소 양수 f32 boost,
  1/3샤드, 단일/복수 토큰, relevance/필드 정렬 및 페이지에서 native 비트 일치를 시험했다.

추가 계약 fixture와 이전 실제 daede139 비교:

| Fixture | 범위 | 이전 비교 |
| --- | --- | --- |
| search-native-exact-phrase-scores-compat.json | slop0/boost1·2/1·3샤드, 필드 정렬 및 단일 repeat 결과8건 | 8실패, 공통1500통과 |
| search-native-text-option-inputs-compat.json | 문자열 norms 및 position_increment_gap 입력2건 | 2통과, 공통1500통과 |

첫 후보 v1은 typed inline 옵션 메타데이터로 빌드했으므로 최종 후보로 사용하지 않는다.
실행 파일3624be06dac5d34a47387109d2d47000bdd5c1046692620081312f5eaa885d69과
source manifest74507c659b47fd08fff387a4bc4b15ea6b3e5a2229f0600dff4fa6cadb760637을
native-exact-phrase-candidate에 보존했다. v2는 별도 source/artifact에 동결하고 v1의
후보 전용 Cargo cache만 옮겼다. 기준선 cache/실행 파일/공개 증거와 섞지 않는다.

최종 root engine941건(921+7+4+9) 통과, 실패/ignore/filter0, 종료0이다.
engine-sixth.log SHA-256: 93a2b89c9d9db28835296f8f9f744e3045f472af1b09e5e59d2d6fb5222368e7.
v2 source.sha256: 838c6f3b3b8c17e12402c57427ca2bd4794963ac460bd7aae729644d37dbb667.
시험 중 첫 추가 시험의 arity 컴파일 오류와 legacy 복구 후 메모리 hash 갱신 누락을
수정했다. 실패 로그도 engine-second/third.log에 남겼다. 최종 시험은 전체 재실행이다.

확장 HTTP 전체와 full non-plugin 반복 성능까지 종료했다. 정확성 허용오차의 수치
계약은 승인되지 않았으며 기존 ordered ID/6자리 점수 비교를 유지한다. 동점 순서/작은
float 차이는 진단과 원 판정을 함께 남긴다. min_score/페이지 누락/실제 거리 빈도 차이나
v0.6.0 누적 성능5% 예산을 수치 허용오차로 면제하지 않는다.
sloppy fractional scoring, 배열 gap의 production 연결, soft-delete 통계, bool 내부 전체
native scoring 및 비기본 옵션의 의미 호환성은 완료로 계산하지 않는다.

### 최종 실행 결과

- 실제 v2 실행 파일 f345f41f31f7aa640960bb2d9adf2d43586b49e2cd6552be08c525aac33e6da4.
  native-exact-phrase-v2-candidate/artifacts/steelsearch이며 빌드5분47초/종료0이다.
  source manifest 불변 확인, baseline/공개 증거 불변이다.
- native-exact-phrase-v2-release-live 전체33하위 비교2286건: 2219통과67실패/skip0,
  count probe/실행 파일 불변/fixture 불변=true, 최종 종료1이다.
  기존2248건에서는1/3샤드 exact phrase2건이 해결돼 실패40→38이다.
  새38건은9통과29실패로, 다른 focused 실행과 합산하지 않는다.
- exact8건의 남은3실패는 문서/순서/total이 같고 boost2 raw 점수 차이가1.507e-7
  미만이지만6자리 반올림 경계를 넘는다. 예: 3샤드 repeat 참조0.2926715,
  후보0.29267165064811707. strict 실패를 보존하며 sloppy의 실제 의미 차이와 구분한다.
  새 옵션 문자열2건은 모두 통과했다. 누락/페이지/min_score 오류를 허용한 것이 아니다.
- 전체6회/12토폴로지1104.196초, 하위 실행 종료0/요청 오류0, 입력 검증=true,
  성능 판정 FAIL/최종 종료1이다. 수락0/40, ledger 제외0, 릴리즈 보류를 유지한다.
  단일 처리량478.837/486.959ops/s(v0.6.0 대비35.555%/34.461% 감소),
  3노드742.415/744.767ops/s(20.288%/20.035% 감소)다.
  단일 ranking mean22.498/21.883ms는 OpenSearch보다73.238%/68.832% 높다.
  published44지표 중21/21실패, paired18/20실패, baseline drift41/44 및37/44 통과다.
- 실행 조건/전체14시나리오 mean/p95/p99 표/실패 범위는
  [구현 계획 최종 검증 절](core-replacement-implementation-plan-2026-09-07.md#native-exact-phrase-반복-전체-검증-2026-09-10)에 있다.
  성능 미달은 이전 후보부터 남은 누적 회귀이며 이 구문 수정 단독 비용으로 단정하지 않는다.
  다음 조사 우선순위는 full ranking Bool/MultiMatch/필터의 native 연결 경계다.
  후속 구현 단위도 전체 시험/확장 HTTP/full non-plugin 반복 benchmark와 고정 v0.6.0
  누적5% 게이트를 통과하기 전에는 완료하지 않는다.

| 증거 | SHA-256 |
| --- | --- |
| v2 candidate-build.log | b39a5422d640bb1f150a161d506a56c4bf33f51308cb72c8f619d29477c29f95 |
| v2 HTTP execution.json | 207d3cb8422844a854d82c714272cf02945cac8686a57c9d47d69c488c7f6683 |
| v2 exact phrase report | a87a424f1f4ceba428802279e6e08ec9c29e395f40b3c37877e5c51c13d6e18a |
| v2 phrase explain report | 31c11c719151532ae665cf3f14722628f5909cac69e3eb83f38149c3521d5f7a |
| v2 full performance result.json | 93fe00d38b2e6ce022c4d9b5f5b7e2749284199c296e5fb5902edd86bb41ebf5 |
| v2 full performance plan.json | 7ab5d37b2587c6bba66ec1e16484fb47926ed6c8bc1f883a1b96983b4568c57f |

## Compound Ranking 분해와 Native 합산 경계

후속 조사에서는 production 코드를 변경하지 않았다. root lib.rs와 f345f41f 동결 소스의
lib.rs SHA-256은 모두6570b4791b2d02eb8710930e15fa2f3134b4dd97be5b38f79bfcde0da440850b이다.
추가 시험은 cfg(test) 모듈에만 있다. 아래는 새 성능 개선/완료 증거가 아니다.

### 실제 경로와 참조 계약

- tools/run-http-load-baseline.py의 ranking은 best_fields MultiMatch를 must에,
  slop1 phrase와 keyword term을 should에, minimum_should_match1과 numeric range
  filter를 둔다. top-level exact phrase가 빨라지는 것만으로 이 경로가 native가 되지 않는다.
- query_requires_native_candidate_post_filter는 scoring MultiMatch 및 최소 should1 이상의
  match-family 조합을 true로 만든다. query_allows_source_candidate_scan_for_native_post_filter와
  함께 search_hits_page_for_source_candidate_post_filter를 선택한다.
  이 정적 분기 확인을 CPU 프로파일 계측이나 모든 요청의 실제 라우팅 계측으로 확대하지 않는다.
- 새 permanent fixture search-native-compound-ranking-compat.json은 같은8문서/1·3샤드에서
  keyword/multi leaf, must/filter/required should, exact/sloppy, MSM0·1·2, must_not,
  should2-of-3 및 phrase boost를 relevance/필드 정렬로 비교한다. min_score와 페이지4건을
  더해 총60건이다. explain=true 실제 응답을 보존했다.
- 고정 f345f41f vs OpenSearch3.7.0-SNAPSHOT HTTP는 새60건 중10통과50실패, 공통1500통과,
  전체1560건 중1510통과50실패/skip0/종료1이다. count probe/fixture 불변/바이너리 불변=true.
  기존2286건과 다른 focused 실행이며 합산 통과율이나50개의 고유 결함으로 표현하지 않는다.
- 실패를 우선순위로 분류하면 문서 집합/total26건, 같은 집합에서 raw 점수 차이>1e-5인14건,
  나머지 순서8건, 반올림2건이다. 이1e-5는 진단 분류 경계일 뿐 승인된 정확성 허용오차가 아니다.
  원 strict 판정은 그대로 보존했다.

| 실제 사례 | OpenSearch | 현재 production | 의미 |
| --- | --- | --- | --- |
| 1-multi-required-exact-field | exact/repeat/sparse, repeat0.430177 | array 추가, repeat0.408135 | top-level 보정을 compound에 확대할 수 없음 |
| 1-full-sloppy-field의 gap | 1.3949475 | 약1.415237 | 거리 가중 빈도 차이 |
| 1-full-min-score-page-0 | total2, exact/repeat | total1, exact만 | 점수 오차가 실제 누락을 유발 |
| 1-full-min-score-page-1 | repeat 반환 | 빈 페이지 | min_score/페이지 기준을 완화하면 안 됨 |

참조 gap explain은 MultiMatch max0.35898772 + phrase(freq0.5)0.035959877 +
ConstantScore(service:yes)1 + range filter0이다. keyword를 BM25라고 추정하거나 filter 점수를
새로 합산하지 않는다. repeat 참조 점수1.4301767과 source1.408135는 min_score1.42의
반대편에 있다. 이 경우 작은 float 허용오차 논의와 무관하게 의미 수정이 필요하다.

### Native 합산 시험

- native_compound_ranking_decomposition_audit는 fixture의 각 query를 native로 만들고,
  must/should/filter/must_not leaf의 native 문서 집합으로 Bool membership을 독립 비교한다.
  matching scoring leaf를 한 번씩 더한 값과 compound native 점수도 비교한다.
  filter/must_not을 점수 합산에 넣지 않는다. request window/min_score는 이 native probe에
  적용하지 않았으며 HTTP 응답 검증을 대체하지 않는다.
- 현재2-of-3 builder는 C(3,2)의 matching 조합 점수를 다시 더해 exact 점수가 약3배다.
  1샤드 additive2.168429136에 native 약6.505288, 최대 차이4.336858511이며,
  3샤드 최대 차이는4.429452419다. Bool membership 자체는 같아도 점수는 틀리다.
- pinned Tantivy0.21.1 DisjunctionMaxQuery::new는 tie_breaker0으로 BooleanWeight의
  DisjunctionMaxCombiner를 사용한다. 각 matching 조합에 모든 matching should가 한 번씩
  들어가므로 이 조합들을 max로 묶으면 중복 합산을 피할 수 있다. 시험 probe는 must/filter를
  조합 바깥에 유지한다. 2-of-3에서 native leaf 합산과 probe 차이는2.385e-7 미만이었다.
  이는 native 내부 합산 순서 검증이지 참조 허용오차 승인이나 production 수정이 아니다.
- DisMax probe도 C(n,k) 조합 수 자체는 줄이지 않는다. 대규모 clause에 대한 확장 가능한
  최종 구현으로 완료 처리하지 않는다. 같은 버전은 BooleanWeight::new/ScoreCombiner를
  공개하지만 Union::build는 pub(crate)이고 SumWithCoordsCombiner의 count는 비공개다.
  직접 접근할 수 있다고 가정하지 않는다. native 상수 점수 leaf의 합산으로 match count를
  얻고 threshold DocSet을 얇게 연결하는 선형 크기 대안은 아직 시험하지 않은 다음 후보이다.
- ID별 참조 비교에서1-full-exact의 native는 문서 집합이 맞고 최대 점수 차이2.734e-7
  미만이다. full-sloppy는 native도 array 추가 및 gap 오차0.02028945가 남는다.
  DisMax probe로2-of-3 중복은 줄어도 이 leaf 의미 차이는 그대로다. 모든 Bool guard를
  일괄 제거하지 않는다. 참조 비교의 min_score4건은 native window 미적용으로 제외 표시했다.
  원 HTTP 실패4건을 검증 범위나 완료 판정에서 제외한 것이 아니다.

### 검증과 다음 구현 단위

- 최종 전체 engine942건(922+7+4+9) 통과, 실패/ignore/filter0, 종료0이다.
  최초 실행은 진단 출력의 상대 경로를 잘못 지정해 파일 생성만 실패했다. 실패 로그를 보존하고
  절대 경로로 전체 재실행했다. DisMax probe 추가 후에도 전체를 다시 실행했다.
- 다음 production 단위는 아래 순서로 분리한다. 각 단위 뒤 focused/전체 engine/확장 HTTP와
  **전체 non-plugin 반복 benchmark**를 실행하고 v0.6.0 누적5%를 통과하기 전 완료하지 않는다.
  향후 전체 HTTP에는 새60건을 포함해야 하며, 기존2286+60=2346은 예정 범위이지 측정 결과가 아니다.
1. native text 색인의 배열 position gap 연결: 기본100/명시값, 분석기와 null/빈 배열/다중값,
   fieldnorm/토큰 통계/refresh reader/복구 형식을 검증한다. scalar 전용 결과로 완료하지 않는다.
2. native phrase 거리 가중 빈도: 기존 native postings/docset을 유지하고 fractional BM25 빈도를
   지원하는 좁은 scorer 확장을 검증한다. 반복/다중 토큰/역순/boost/explain과 실제 참조 빈도를
   대조한다. 공유 registry를 수정하지 않고 필요한 의존 변경은 독립 source/vendor에 기록한다.
3. native compound 연결: MultiMatch/Bool의 검증된 score tree와 source guard의 필요 조건을
   분리한다. MSM>1의 조합 폭발 없이 한 번씩만 합산하는 native 경로를 먼저 시험한다.
   min_score/top-k/페이지/정렬/선택 샤드/오류/권한/비기본 설정을 보존하고, 위60건을 포함해
   실제 HTTP에서 검증한다. 작은 점수 차이를 없애려고 source scorer를 새로 만들지 않는다.
- 세 단위를 한꺼번에 완료했다고 하거나 마지막 한 번의 benchmark로 앞 단위 검증을 대체하지 않는다.
  각 단위의5% 이상 단독 회귀와 누적 회귀는 원 계획의 조사/최적화/제외/승인 규칙을 따른다.
  최신 production 성능은 f345f41f의 전체 FAIL 그대로다. 수락0/40, ledger 제외0, 릴리즈 보류다.

target/core-replacement-c06/native-compound-ranking/ 증거:

| 파일 | SHA-256 |
| --- | --- |
| reference-live/execution.json | 599021416c53428190d5c228575df769a29cae8201f6529cac45913eeb6f2428 |
| reference-live/search-native-compound-ranking-compat-report.json | 18054ff538f30ff6d9b672548d33f78e261ff5bb62bc8bfe18368b9afb0066a9 |
| diagnostic.json | cc905cd9072120a864bb56e360c8660e3966a741dc008da013a45fbbe12cb2e7 |
| dismax-diagnostic.json | 91a5ec0d79700d3018b8c9a1a63740132ecb9b0d2f5642d1cb15c62b428dd6d1 |
| reference-comparison.json | d3c34f266d5c2183f8d82aee1a081cd7316ac418c19c110f237b90eab95e73fa |
| engine-full-third.log | 86644f9db8096fd592076521b7fc1ec7b4d861ee1c6b568cac55c26c495aa9d1 |

fixture SHA-256: f4d57980189b606059692ce72dcce94cee1fbd898c2f3c5068094c751a57d525.
시험 모듈 SHA-256: e0fa4f0f6a9541191665c92117094d18331b5a8f2c041b7154a3678cf7adf8fc.

## 2026-09-10 native array position gap 연결과 전체 검증

### 실제 참조와 native 계약

- production은 pinned Tantivy0.21.1의 tokenizer_for_field, PreTokenizedString,
  add_pre_tokenized_text를 사용한다. 기존 native postings/phrase query를 유지한다.
  scalar 문자열은 add_text fast path이고 다중 text 값만 연결한다.
- fixture5개 인덱스/16문서씩80문서/termvectors80요청/phrase55요청을
  OpenSearch3.7.0-SNAPSHOT(f991609d190dfd91c8a09902053a7bbfe0c27b3e,
  Lucene10.4.0)와 실제 비교했다. 기본gap100, 명시0/1/5, 문자열100이다.
- 기본 ["alpha","beta"]는 alpha0/beta101, leading empty는 alpha100/beta201,
  middle empty/punctuation-only는 beta201, two empty는 beta301이다.
  null/빈 배열/중첩 배열은 빈 문자열과 달리 추가 gap을 만들지 않는다.
  숫자12와 bool true는 native 토큰으로 변환되며 alpha0/12또는true101/beta202다.
  반복 ["alpha beta","alpha beta"]는 alpha[0,102]/beta[1,103]이다.
- 인덱스별 참조 fieldstats는 doc_count14/sum_doc_freq30/sum_ttf32다.
  영구 reference fixture에80개 term 위치와55개 phrase ID 집합을 저장했다.
  native 테스트는80문서 postings/norm,55구문 membership,이전 reader40문서,
  총 토큰32를 직접 확인한다. HTTP termvectors 구현을 시험한 것으로 확대하지 않는다.
- MAX_POSITION2147483519는 실제 Lucene IndexWriter 상수를 javap로 확인했다.
  native 변환을 writer mutation 전에 준비하는 batch 시험은 실패 후 직접 commit해도
  앞 문서가 게시되지 않음을 확인한다. API의 최초 쓰기 거부 시점까지 보장한 것은 아니다.

### 검증 결과와 범위 제한

- 최종 engine944건(924+7+4+9) 통과, 실패/ignore/filter0이다.
  engine-second.log의1실패는 test helper의 역방향 postings.seek 때문이었다.
  helper 수정 뒤 engine-third.log 전체 통과를 최종으로 사용하고 실패 이력을 보존했다.
- 최종 frozen 후보는5a621371baf2714124ebd8dad71f8cf0e07b3e476720daa4558792b657326375.
  v1/v2 production artifact의 실제 해시가 같다. v2는 cfg(test) helper만 수정한 소스를
  후보 전용 build cache로 빌드했다. 기준선 빌드 디렉터리는 사용하지 않았다.
- 전체 HTTP2481건(기존2286+compound60+array135)은2229통과252실패/skip0,
  35하위 실행,count probe통과,binary/fixture불변,종료1이다.
  기존67실패와 compound50실패가 유지되고 array135실패가 추가된 범위다.
- 새 phrase55건에서 total/ID 집합 일치는 이전 f345f41f28건→새5a62137155건이다.
  하지만 점수55건은 엄격 비교 실패다. termvectors80건도 source 기반 응답 때문에 실패다.
  이135건을 native 내부 위치 시험 통과로 덮어쓰거나 허용오차를 임의 확대하지 않았다.
- raw gap 음수/소수/초과 범위 입력 검증, 모든 analyzer 옵션, object 거부,
  API overflow 거부 시점/전체 mutation·replay 계약은 미완료다.
  숫자/불리언 source BM25가 native와 다르므로 cache eligibility를 보수적으로 제한했다.
  비기본 gap/source phrase eligibility를 무조건 확대하지 않았다.
- 전체 non-plugin 반복6회/12토폴로지 요청 오류0,입력 불변,1100.047초,성능 FAIL.
  단일 처리량481.888/476.795,3노드745.023/733.936ops/s다.
  최초 v0.6.0 대비 손실35.144%/35.829%,20.008%/21.198%다.
  published44지표 중23/28실패,paired19/22실패,baseline drift41/44와40/44통과다.
  단일 ranking mean22.178/22.524ms는 v0.6.0보다245.833%/251.230% 느리다.
  전체14개 시나리오 mean/p95/p99 표와 실행 설정은
  [주 계획의 native array positions 기록](core-replacement-implementation-plan-2026-09-07.md#2026-09-10-후속-단위-native-array-positions)에 있다.
- 누적 회귀를 이번 단독 구현 비용으로 단정하지 않는다. 기준선 재설정/임의 제외/예외 승인
  없이 수락0/40,ledger 제외0,릴리즈 보류다. 배열 단위를 완료로 처리하지 않는다.

### 다음 native 확장 경계

1. 고정 버전 PhraseScorer::phrase_count는u32이고 Bm25Weight::score/explain도u32다.
   Bm25Weight의 norm cache/tf_factor 및 PhraseWeight::phrase_scorer는 비공개다.
   외부 wrapper에서 해당 내부 API에 접근할 수 있다고 가정하지 않는다.
   좁은 dependency 확장으로 fractional score/explain을 연결하되 exact/slop0와 다른 query의
   기존 동작을 보존한다. 공유 Cargo registry는 수정하지 않는다.
2. 구문 빈도는 native postings/docset 위에서 실제 Lucene 거리 가중 의미와 비교한다.
   반복어/다중 토큰/역순/겹치는 매치의 단순 위치쌍 합산을 올바른 구현으로 가정하지 않는다.
   최소 참조 fixture를 먼저 확장하고 distance1의0.5, distance2의1/3뿐 아니라
   여러 매치의 합산/advance/seek/삭제/boost/explain을 확인한다.
3. compound 연결은 위 의미가 검증된 leaf만 대상으로 한다. MSM>1 조합 폭발을 피하는
   native 대안을 시험하고 min_score/페이지/정렬/오류/권한 guard를 보존한다.
   실제 반환 문서가 누락되는 실패는 단순 점수 허용오차로 면제하지 않는다.

각 production 구현 단위 뒤 전체 engine, 확장 HTTP(현재2481건 포함), 전체 non-plugin
반복 benchmark가 필수다. v0.6.0 고정 누적 throughput95%/각 latency105% 기준을
통과하기 전 완료로 표시하지 않는다. focused 검증은 이를 대체하지 않는다.

### 증거

target/core-replacement-c06/ 기준:

| 파일 | SHA-256 |
| --- | --- |
| native-array-positions/previous-reference-live/execution.json | bfbf5f803b97756aca5f3cfd5e9b44fe3dada841132d03f29d0206eefc3d746f |
| native-array-positions/previous-reference-live/search-native-array-positions-compat-report.json | 740fa81f217d0cfe1e8aeeccadf1c5b646b26f785ab7de71802cea879f27fd66 |
| native-array-positions/engine-third.log | ee4e333484518b16d64c10f67f4cc8724950119166983f4cc02118b1e99dcac8 |
| native-array-positions-v2-candidate/source.sha256 | ba5b3bd042669bfe668f78fd3d75e7b17ef88fcc03a5042dd190c0a6c8ad33cb |
| native-array-positions-release-live/execution.json | a3b1e2140ce479378ec1e37e34d535d8954fd75c1eafe03a3430243c55cb1d86 |
| native-array-positions-release-live/search-native-array-positions-compat-report.json | 60cd693283795a3f80828e87df9c74e4e19cbf224eab37ccfdf41085ac4a194e |
| native-array-positions-repeated-full/result.json | 1a21ea3818d316830fed70c98f48a087947006897c9eaf751417467517e69e94 |

fixture SHA-256:3945d7aeb1110e3eff69227421a71007e22684af0516196b7d345f8a1497efe1.
reference fixture SHA-256:dd1402d233868cbf708bf03dc28cc6ec228551abe00aa7bd146cbab87f503aa1.

## 2026-09-10 반복/다중 토큰 phrase 빈도 조사

### 범위와 결과

- search-native-phrase-frequency-compat.json:1/3샤드,20문서씩,5구문
  (alpha beta / alpha alpha / alpha beta gamma / alpha beta alpha / alpha alpha beta),
  slop0/1/2/3/5/100,boost1/2의120조건이다. 반복/겹침/역순/배열/빈 값이 포함된다.
- 실제 참조3.7.0-SNAPSHOT(f991609d190dfd91c8a09902053a7bbfe0c27b3e,
  Lucene10.4.0)와 frozen5a621371을 비교했다. HTTP1620건은1514통과106실패/skip0,
  count probe통과,binary/fixture불변,종료1이다. 새120건은14통과106실패,
  공통1500건은 통과다. 이전2481건 전체를 다시 실행한 결과는 아니다.
- reference fixture에 실제120조건의 ID별 raw score/phraseFreq를 보존했다.
  native probe는 실제 색인의 postings 위치와 query explain을 수집한다.
  production source scorer를 정답으로 사용하지 않는다.

| 구문 종류 | HTTP 문서 집합 일치 | HTTP 엄격 통과 | 조건 수 |
| --- | --- | --- | --- |
| alpha beta | 24 | 0 | 24 |
| alpha alpha | 4 | 4 | 24 |
| alpha beta gamma | 20 | 2 | 24 |
| alpha beta alpha | 8 | 4 | 24 |
| alpha alpha beta | 4 | 4 | 24 |

- native 직접 비교도 문서 집합은60/120일치다.56조건에서 추가 문서,
  4조건에서 참조 문서 누락이 있다. 두 분류는 겹치지 않는다.
  slop0의20조건은 문서 집합과 빈도가 모두 같고, 나머지100조건은
  공통 문서 중 native 정수 빈도와 실제 참조 빈도가 다른 사례가 각각 있다.
- 오탐 최소 예: 문서 alpha beta의 alpha 위치는[0]뿐이다.
  alpha alpha/slop1에서 native는 freq1로 매치하지만 참조는 매치하지 않는다.
  alpha alpha 문서도 native freq2,참조 freq1이다. 반복어가 같은 토큰 위치를 재사용한다.
- 누락 최소 예: 문서 alpha gamma beta에 query alpha beta gamma/slop2를 주면
  참조는 freq1/3으로 매치하고 native는 누락한다(1/3샤드,boost1/2의4조건).
  native PhraseScorer를 후보 필터로 두고 점수만 다시 계산하면 이 문서를 복구할 수 없다.
- 복수 매치 예: alpha beta beta alpha에서 query alpha beta/slop3의 참조freq는
  1.3333334,native는2다. alpha gap beta gap alpha에서는 참조0.75,native1이다.
  모든 위치쌍을 독립적으로 합산하거나 정수 매치 수에 고정 계수를 곱하지 않는다.
- 이는 의미 차이이며 단순 반올림 허용오차 대상이 아니다. 점수 허용오차는 여전히 미승인이다.

### Native API와 구현 결정

- pinned Tantivy0.21.1 PhraseScorer의 PostingsWithOffset은 query offset을 적용한 위치로
  intersection을 계산한다. slop 비교에서 같은 term의 실제 위치 충돌을 별도로 배제하지 않는다.
  3토큰 carrying-slop 중간 교집합은 위 재배열 참조 매치를 보존하지 못한다.
  기존 연결 코드 문제와 구분하여 실제 source/API 및 직접 실행으로 확인한 차이다.
- [Lucene10.4.0 SloppyPhraseMatcher 원본](https://raw.githubusercontent.com/apache/lucene/releases/lucene/10.4.0/lucene/core/src/java/org/apache/lucene/search/SloppyPhraseMatcher.java)을 확인했다.
  참조 구현은 반복 term 그룹의 위치 충돌을 해소하고 priority queue로 최소 위치를 전진시킨다.
  matchLength로 거리 가중 빈도를 계산하며 효율 때문에 모든 유효 조합을 열거하지 않는다.
  따라서 별도의 완전 조합 탐색기를 더 정확한 대체라고 가정하지 않는다.
  앞선 실제 jar javap 기록과 이번 원본을 별도 증거로 보존한다.
- 다음 production 단위는 score wrapper만이 아니라 native postings matcher/scorer의 좁은 확장이다.
  native term 교집합으로 문서 후보를 만들고 반복 term 그룹/offset/위치 충돌/재배열을 처리한다.
  기존 부정확한 sloppy phrase DocSet으로 후보를 미리 잘라 누락을 고정하지 않는다.
  BM25 f32 빈도와 explain을 함께 연결하고 exact/slop0 및 다른 query 의미를 유지한다.
- 공유 registry 수정이나 source 전체 스캔을 새 구현으로 사용하지 않는다.
  독립 source/vendor의 출처·라이선스·변경 파일을 기록하고 기존 native Query/Weight/Scorer
  및 collector를 유지한다. matcher/scorer 구현 후 advance/seek,삭제/refresh reader,
  반복/다중 토큰/boost/explain을 검증해야 한다.
- compound guard는 leaf 의미가 확인되기 전 제거하지 않는다. minimum_should_match>1,
  min_score/페이지/정렬 및 권한·오류 계약도 별도로 보존한다.
- 각 production 구현 단위가 끝나면 전체 engine, 확장 HTTP(현재2481+120=2601 예정 범위),
  전체 non-plugin 반복 benchmark가 필수다.2601은 아직 실행한 전체 건수가 아니다.
  v0.6.0 고정 누적 throughput95%/각 mean·p95·p99105%를 통과하기 전 완료하지 않는다.
  focused 진단으로 대체하거나 다음 단위까지 benchmark를 미루지 않는다.

### 시험과 증거

- native_repeated_phrase_frequency_audit는120조건을 진단하고,
  slop0의20조건을 실제 reference fixture의 문서 집합/빈도와 단정 비교한다.
  slop>0에서 기존 exact-native-score 권위 경로가 거부되는 것도 확인한다.
  남은 sloppy 불일치가 통과한 것처럼 해석하지 않는다.
- 최초 전체945건 통과 후 reference/slop0/guard 검증을 추가하고 다시 전체945건
  (925+7+4+9) 통과,실패/ignore/filter0,종료0이다. 최종 빌드1분26초.
  첫/최종 native 진단 JSON은 바이트 단위로 같으며 비교 보고서도 유효하다.
- 이 단계는 cfg(test)/fixture/문서만 변경했다. production lib.rs SHA-256은
  9fc17c0c4de670d8119cf9a19845da58d0905a8222705c806178132289aad785로 그대로이고,
  frozen executable은5a621371이다. 새 production 성능 측정으로 가장하지 않는다.
  최신 full non-plugin 결과는 앞 배열 단위의 FAIL이다. 수락0/40,제외0,릴리즈 보류다.

target/core-replacement-c06/native-phrase-frequency/ 기준:

| 파일 | SHA-256 |
| --- | --- |
| reference-live/execution.json | 6fdab3dadeb4a15be36852ec936a44c1e99f629228ef6bed3d25f406776b6a69 |
| reference-live/search-native-phrase-frequency-compat-report.json | 7354c09f4f46067e734132829641700e68a921e9c2b9775404796eb3daf032eb |
| native-final-diagnostic.json | c45798d9617a764d1d58ba8f95b55b309344cba24255f267eeeebad0bd28e1e9 |
| comparison.json | f8730645c44ce018c7d3ea68172f62fd09f2b99b8084afec7622ce856c662844 |
| engine-full-final.log | eb8e5a4e3cc9a490943baefc23ba67d070cc49a84fa8bf8434dfff883752e3a6 |
| SloppyPhraseMatcher-10.4.0.java | 2f387f03bfed24d4ecc7364eca3708eb3e45fb7384fa6066944f7baf7df64d15 |

fixture SHA-256:19baa426a3062a1abf13285478f38d70addf3767f3ab4cd2aa6b41546d8c60bc.
reference fixture SHA-256:e8910b492fe727fe01a4671e716bad420b38996b667aead6b73021a17a6d54c9.
시험 모듈 SHA-256:1f46a62e5a2aa55b03ebd740fbaf14b354f1759a291db5a31add82ee0f234d79.

## 2026-09-10 native 위치 매처 구현과 참조 검증

### 구현

- native_phrase_positions.rs에 Lucene10.4.0 SloppyPhraseMatcher의 single-term phrase
  위치 순회를 Rust로 이식했다. 고정 Tantivy의 반복 위치 재사용/재배열 누락이 실제로
  확인된 범위에 대한 좁은 확장이다. source 재검색이나 새로운 역색인 엔진은 추가하지 않았다.
- query offset을 뺀 signed 위치의 최소 힙, 반복 term 그룹별 초기 위치,
  실제 term 위치 충돌 해소, matchLength 최소화와1/(1+matchLength) 빈도 누적을 구현했다.
  반복 그룹 구성은 matcher 생성 시 준비하고 문서마다 cursor/heap/end를 초기화한다.
- 표준 BinaryHeap의 오래된 항목은 cursor로 무효화한다. queued term이 충돌 해소로
  이동할 때 새 항목을 넣으며 heap 길이가2*phrase term count를 넘으면 현재 항목으로 재구성한다.
  커스텀 heap이나 모든 위치 조합 열거로 구현하지 않는다.
- 현재 모듈은 native_ranking_audit_tests에서만 불러온다. production lib.rs/native_bm25.rs,
  Cargo dependency와 native query routing은 바꾸지 않았다.
  Query/Weight/Scorer와 BM25 f32 빈도 연결 전의 시험 구현이다.

### 실제 postings 대조

- 이전120조건 fixture와 실제 reference fixture를 그대로 사용했다.
  native BooleanQuery의 unique term MUST conjunction으로 문서 후보를 구하고,
  실제 SegmentPostings::positions를 새 matcher에 전달했다.
  기존 sloppy PhraseScorer로 후보를 미리 제한하지 않아 기존 누락 문서도 검증한다.
- 1/3샤드,5구문,6slop,2boost의120조건 문서 집합이 모두 참조와 일치한다.
 896개 문서별 빈도도 reference를 f32로 읽은 값과 정확히 같다.
  새로운 점수 오차 예산은 도입하지 않았다. BM25 최종 점수가896건 통과했다는 뜻은 아니다.
- 기존 native 문서 집합 일치는60/120이었다. 새 matcher 경로는120/120이다.
  alpha alpha/slop1의 단일 alpha 문서 오탐과 alpha beta gamma/slop2의
  alpha gamma beta 누락이 새 시험 경로에서 해결됐다. production HTTP가 수정된 것은 아니다.
- native slop0 기존 문서 집합/빈도 비교20조건과 sloppy exact-score 권위 거부 시험도 유지한다.
  score/boost는 fixture에 있지만 이번 새 matcher는 빈도만 계산한다.

### 경계 시험과 결과

- alpha 위치0,2,...,19998의1만 위치 반복 입력에서 alpha alpha/slop1 빈도4999.5를
  확인하고 종료 heap 항목<=4를 확인했다. 이후 한 위치/인접/빈 문서/간격 문서를 같은
  matcher로 처리하여 문서 간 cursor/queue 상태가 남지 않음을 검증했다.
- 재배열3토큰을 base0/1/100/2147483517로 이동해 slop1 불일치,
  slop2 freq1/3의 동일 결과를 확인했다. query offset으로 음수가 되는 초기 위치와
  현재 native token 위치 상한2147483519도 포함한다.
- 첫 전체945건 통과 후 추가 경계 시험2건을 포함한 최종 전체947건
  (927+7+4+9) 통과,실패/ignore/filter0,종료0이다. 최종 빌드1분25초다.
  두 실행의120조건 진단 JSON은 SHA-256까지 동일하다.
- 생산 경로의 점수/HTTP/성능 완료로 인정하지 않는다. 최신 production은5a621371,
  전체 non-plugin 성능은 기존 배열 단위 FAIL,수락0/40,제외0,릴리즈 보류다.

### 다음 연결 단위와 완료 조건

1. Matcher를 native Query/Weight/Scorer에 연결한다. native term conjunction과 segment
   postings cursor를 유지하고 문서별 postings 객체 재생성 없이 위치 버퍼를 재사용한다.
   advance/seek/종료 상태,Count/TopDocs,삭제 문서/refresh reader를 검증한다.
2. 고정 Tantivy Bm25Weight의 u32 빈도 API 한계를 좁은 확장으로 해결한다.
   native statistics/fieldnorm cache를 그대로 사용하고 fractional score/explain/boost를 연결한다.
   비공개 cache를 우회해 점수에서 역산하거나 source 문서 통계를 다시 만드는 방식은 쓰지 않는다.
   필요 dependency 변경은 독립 source/vendor에 보존하고 공유 registry는 수정하지 않는다.
3. 실제 analyzer가 만드는 위치/offset/반복 term identity를 전달하고 non-default 옵션의
   eligibility 및 기존 보호 조건을 검증한다. 이번 single-term phrase 위치 순회를
   MultiPhrase의 동의어/동일 위치 다중 term 지원으로 확대 해석하지 않는다.
4. production 연결 단위 뒤 전체 engine/확장 HTTP2601건 예정 범위와 전체 non-plugin
   반복 benchmark를 실행한다. 고정 v0.6.0 처리량95%/각 mean·p95·p99105% 통과 전
   완료하지 않는다. focused120조건이나 마지막 단계의 benchmark 한 번으로 대체하지 않는다.

이 구현은 위 production 단위를 완료한 것이 아니며 해당 검증을 면제하지 않는다.
단위/누적 회귀의 조사·최적화·제외/승인 정책은 원 계획 그대로다.

### 출처와 증거

- Apache Lucene10.4.0 위치 순회 출처와 변경 범위는
  [라이선스 기록](../licenses/lucene/README.md)에 있다.
  upstream root LICENSE.txt/NOTICE.txt를 수정 없이 보존했다.
  다른 Lucene 구성요소나 Java runtime을 함께 vendoring했다는 뜻은 아니다.
- production lib.rs:9fc17c0c4de670d8119cf9a19845da58d0905a8222705c806178132289aad785.
  production native_bm25.rs:39a634eb5ae362edde238a49597b44ec47d91951903d68403ae0ed899ecd1e5b.
  frozen executable:5a621371baf2714124ebd8dad71f8cf0e07b3e476720daa4558792b657326375.

| 파일 | SHA-256 |
| --- | --- |
| crates/os-engine-tantivy/src/native_phrase_positions.rs | 12787d4974d8386e9bd3bcc6f6dbc336d1e3178658b569876370ff09ccc0fdac |
| crates/os-engine-tantivy/src/native_ranking_audit_tests.rs | 5204fac44a299603a91604998d565add6cf037ec8315677bf6e68d3c1e14aa77 |
| target/core-replacement-c06/native-phrase-matcher/native-final-diagnostic.json | 918a8e238f6aaa024fba6ba7d065db4d8d50157886c0c659d912f16c91d79e9c |
| target/core-replacement-c06/native-phrase-matcher/engine-first.log | 524932bac6a63e568993adfcaf45f941d5c096b226e1bd11cd3bb265ddc0be76 |
| target/core-replacement-c06/native-phrase-matcher/engine-final.log | 276a962ca901e056b185a65f51f38c4ed45fa69f76cff6f15a2946ff45d8b398 |
| docs/licenses/lucene/LICENSE.txt | a2521407b3209df7dcebfc12cd6d732b24bfa2fe44982ef613e269666482521d |
| docs/licenses/lucene/NOTICE.txt | d3b82734d5e181509c4b6b832f5d3a90c8c6a34fc195272fc8957ccb9e8e20a8 |

## 2026-09-10 native phrase scorer production 연결과 전체 게이트

### Native 구현

- native_phrase.rs의 NativePhraseQuery/Weight/Scorer는 native term conjunction과
  SegmentPostings cursor를 사용한다. 위치 버퍼와 Matcher는 세그먼트 scorer 수명 동안
  재사용한다. source 문서 재검색은 추가하지 않았다.
- Count/비점수 경로는 matcher의 첫 매치에서 종료하며 BM25 통계 계산과 scoring norm
  조회를 생략한다. 점수 경로는 fractional frequency를 기존 native weight/cache에 전달한다.
- vendor/tantivy는 crates.io0.21.1 원본을 고정한 것이다. upstream crate SHA-256
  d6083cd777fa94271b8ce0fe4533772cb8110c3044bab048d20f70108329a1f2,
  VCS722b6c5205f61da2ca62ac62b1457b18a47b519c이다.
  원본 대조에서 코드 변경은 src/query/bm25.rs 한 파일뿐이며 score_fractional과
  explain_fractional을 추가했다. 기존 정수 score/IDF/cache 계산은 유지했다.
  원본 라이선스/출처를 보존했고 공유 registry는 수정하지 않았다.
- native_phrase_score_is_authoritative는 기존 기본 Text/짧은 ASCII 토큰/양수 유한 boost/
  mapping 옵션/값/선택 샤드 조건을 유지하면서 u32 범위의 slop을 허용한다.
  native 권위가 검증된 구문 점수를 source BM25로 덮어쓰지 않는다.
  slop0/단일 토큰 경로와 미검증 비기본 옵션의 보호 조건은 유지했다.
- 일반 analyzer의 위치/offset 전달,동일 위치 multi-term phrase,HTTP explain 전체 및
  _termvectors는 이번 연결로 완료한 것이 아니다. 새 HTTP 범위는 이러한 계약 전체의
  인증이 아니며 native explain과 HTTP explain을 구분한다.

### 시험 및 실제 HTTP

- 전체 engine949건(929+7+4+9) 통과,실패/ignore/filter0,종료0이다.
  256norm×5정수 빈도의 기존 점수 bit 보존,실수 빈도/boost/explain,
  cursor seek/advance/종료,삭제/refresh snapshot을 검증했다.
 120조건 문서 집합/896빈도,Count/TopDocs/선택 주소 재채점과 구문 페이지·필드 정렬,
  subnormal 양수 boost로 native score0이 되는 경우도 포함한다.
- 최종 후보e49e5b616f9312c1e41e05fa6dffded65c270d2c2d93c57a0c0b701e86cdc5ae:
  frozen source에서5분28초 release 빌드,종료0이다.
  후보 전용 cache만 이동했고 이전5a621371 source/artifact와 v0.6.0 기준선을 보존했다.
  root와 frozen의 FST dependency 환경은 다르므로 동일하다고 주장하지 않는다.
- 전체 HTTP2601건은2322통과279실패/skip0,36하위 비교,count probe통과,
  binary/fixture불변,종료1이다. 기존2481의 실패252→238이다.
  기존 native audit2건과 phrase explain12건이 해결됐다.
- 반복구문120건은79통과41실패(이전14통과106실패)다.
  실제 HTTP total/ID 집합은120/120일치한다. 순서는96건 일치하고,
  엄격 실패는 순서 차이24건/동일 순서 점수 차이17건이다.
 896쌍 모두 유한 점수이며 ID별 최대 raw 차이는2.5803222647446944e-7이다.
  허용오차를 변경하거나 이41건을 통과 처리하지 않았다.
- 전체 실패 분포:routing17,native audit11,stable audit8,phrase explain14,exact phrase3,
  compound50,array135,repeated phrase41. 공통1500건은 통과다.
  array의 termvectors80건 및 숫자/불리언 등이 섞인 phrase score55건은 남아 있다.

### 성능과 다음 작업

- 전체 non-plugin 반복6회/12토폴로지 요청 오류0,1095.108초,입력 불변,성능 FAIL이다.
  단일473.125/482.402ops/s,3노드743.459/730.627ops/s다.
  최초 v0.6.0 대비 처리량 손실36.323%/35.075%,20.176%/21.553%다.
  published44지표 중23/27실패,paired17/20실패,baseline drift40/44 및33/44통과다.
- 단일 ranking mean23.076/22.282ms는 v0.6.0 대비259.840%/247.457% 느리다.
  OpenSearch 대비 전체 처리량 우위로 이를 상쇄하지 않는다.
  [주 계획의 전체 표와 출처](core-replacement-implementation-plan-2026-09-07.md#2026-09-10-후속-단위-native-phrase-scorer-production-연결)에
 14시나리오 mean/p95/p99,모든 반복/설정/드리프트를 기록했다.
- 이전 후보에도 큰 회귀가 남아 있어 이번 누적 회귀 전체를 이 scorer의 단독 비용으로
  단정하지 않는다. 임의 제외/예외/기준선 재설정은 없다. 수락0/40,제외0,릴리즈 보류다.
  성능 기준 미달이므로 구현 단위를 완료로 처리하지 않는다.
- 다음 production 단위는 검증된 native leaf를 compound score tree에 연결하는 작업이다.
  source guard가 필요한 옵션과 이미 native로 보존되는 조건을 분리하고,
  MSM>1의 중복 합산/조합 폭발을 native scorer/collector로 해결한다.
  min_score/페이지/정렬/선택 샤드/권한/오류 조건을 유지한다.
- 다음 단위도 전체 engine/확장 HTTP2601건 이상과 전체 non-plugin 반복 benchmark가
  필수다. 고정 v0.6.0 throughput95%/각 mean·p95·p99105% 통과 전 완료하지 않는다.
  focused 시험이나 앞 단위 성능 결과는 이를 대체하지 않는다.

### 증거

target/core-replacement-c06/ 기준:

| 파일 | SHA-256 |
| --- | --- |
| native-phrase-scorer-candidate/source.sha256 | 4ab71bb8244f4d557309dd4b946253f7a7c612e64353704cfefb2fa9e6e716bd |
| native-phrase-scorer-candidate/candidate-build.log | b545ca62b5be20fb15667abcb648c473ad6e394fd8a7750a430de3f8b742656e |
| native-phrase-scorer/engine-production.log | 9bcbde2643c303dc7d22ee54d47a0cacf8467e3b09e824127b446f0ff4913eb9 |
| native-phrase-scorer/production-diagnostic.json | 1e547f82e86ddedee20852fb91f075b22da5034e1c138cfc765644ad4841b80f |
| native-phrase-scorer-release-live/execution.json | 236ab017ddb54f31ee4692cb39c29673168521b66d3c8f3d9c56018c7cc4a3b2 |
| native-phrase-scorer-release-live/search-native-phrase-frequency-compat-report.json | ce4fac25633cfed65a0aaa732981f63dce942195f40cf3ee3e0480c54ed4313c |
| native-phrase-scorer-repeated-full/result.json | 287ec2dd185b5ae2f7180d4ce643a2f7a633bd3644be52891872edcc5395b110 |

production lib.rs:44eb00b14c7ac6ca6fb0720c0310f5442bffb58014de63f2179aea06aa4636ec.
native_phrase.rs:329eaa8a330cd7d037ae6bacd7beecc7186abc5aab8c41a2f4ae205bd15623b5.
native_phrase_positions.rs:9c2e1b8e3032909b7d9377bee58f48ef588ffc93156c7bcc103e4d4fd9a07a3f.
vendor BM25:4bdcee4f6a765357f064801db3874eef1c8415cf9517adde08b0086038bb4fe2.

## 2026-09-10 compound MSM native 확장 사전 검증

### 고정 버전 소스 확인

- 조사 대상은 현재 vendor Tantivy 0.21.1이다. `BooleanQuery`는 subqueries만 저장하며
  임의 minimum-should-match 설정 API가 없다. 이는 다른 버전까지의 부재를 뜻하지 않는다.
- `SumWithCoordsCombiner`는 매칭 scorer 개수를 이미 `num_fields`에 집계한다.
  그러나 필드는 private이고 `ScoreCombiner`의 공개 결과는 점수뿐이다.
- `Union`은 4096문서 horizon의 combiner를 사용하며 현재 문서를 꺼낼 때 score만
  저장하고 combiner를 clear한다. 따라서 외부 wrapper에서 나중에 count를 읽는 것만으로는
  해결되지 않는다. 기존 native 집계 시점에 membership 조건을 적용하는 좁은 확장이 후보다.
- `BooleanWeight`의 `scorer`뿐 아니라 `for_each`, `for_each_no_score`,
  `for_each_pruning`도 확인했다. 마지막 경로는 term union에 BlockWAND를 직접 사용한다.
  scorer 한 경로만 수정하면 Count/TopDocs에서 조건이 우회될 수 있으므로 함께 검증해야 한다.
- 우리 조합 열거는 Bool helper 외에 `build_tantivy_tokenized_field_set_query`와
  `build_tantivy_match_fuzzy_query`에도 남아 있다. 다른 두 호출부를 확인하지 않고
  `query_index_combinations`를 삭제하거나 전체 문제가 해결되었다고 주장하지 않는다.

### 다음 구현 단위와 필수 게이트

1. MSM native primitive: 기존 Union의 문서별 집계를 재사용해 임계값 미달 문서를
   제외한다. 점수 0인 매칭도 개수에 포함하고, scoring-disabled에서도 개수를 유지한다.
   required 점수는 한 번만 합산하며 filter는 0, MustNot은 기존 exclusion으로 연결한다.
   MSM 0/1 기존 경로를 보존하고 모든 collector 진입점의 membership 일치를 검증한다.
   초기화/seek/TERMINATED/삭제 문서/4096 horizon 경계/빈 세그먼트/중복 조건과
   큰 n의 구성 비용을 시험한다. DisMax 조합 열거는 진단용이지 최종 구현이 아니다.
   이 production 단위 후 전체 engine, 확장 HTTP 2601건 이상, 전체 non-plugin 반복
   benchmark를 실행하고 고정 v0.6.0 누적 게이트 전에는 완료 처리하지 않는다.
2. Compound native authority: 검증된 leaf와 실제 샤드/필드 옵션만 재귀적으로 허용하고
   미검증 analyzer/통계/오류 조건은 보존한다. min_score, 정렬, 페이지, 선택 샤드와
   보안 조건을 포함해 다시 검증한다. 이 단위도 별도 실행 파일/소스 증거와 전체 engine,
   확장 HTTP 및 전체 non-plugin 반복 benchmark가 필수이며 직전 단위 결과를 재사용하지 않는다.

두 단위 모두 최초 v0.6.0 처리량 95% 이상, 시나리오별 mean/p95/p99 105% 이하를
각각 적용한다. 초과 시 조사/최적화/전체 재실행하고, 단독 5% 이상 미해결 구현의
제외 또는 명시적 예외는 주 계획/제외 ledger 규칙을 따른다. 기준선 재설정은 없다.
이번 사전 검증은 시험/문서 변경이며 production 수정이나 성능 통과가 아니다.

### 진단 입력 분리

첫 engine 실행은 기존 929개 lib 시험이 통과하고 새 overlap 진단 1개가 실패했다.
원인은 MSM 판정 이전의 constant_score boost 전제였다. `parse_constant_score`는
boost 값을 검증하지만 `Query::ConstantScore { filter }`에 보존하지 않고,
native builder도 filter를 그대로 반환한다. boost 7인 MatchAll이 native 점수 1로
나오는 것을 확인했다. 이 기록은 native/DSL 진단이며 별도 HTTP 검증 결과는 아니다.
MSM과 혼동하지 않도록 수정된 진단은 MatchAll 필수 조건과 keyword 조건을 사용하고,
첫 optional을 filter-only Bool로 구성하여 점수 0인 매칭의 개수 포함을 확인한다.
첫 실패 로그 `target/core-replacement-c06/native-msm-overlap/engine.log`는 보존한다.
constant_score boost 보존/상수 점수 연결은 별도 미해결 사항이며 이번에 수정하지 않았다.

### 사전 검증 결과

- 수정된 전체 engine 실행은 950=930+7+4+9 통과, 실패/ignore/filter 0, exit 0이다.
  빌드 1분23초, lib 15.90초, integration 15.46/3.28/0.42초다.
- 32개 문서(5조건의 모든 조합), 1/3샤드, MSM0~5의 12개 진단에서 native 문서 집합은
  기대와 일치했다. 전 조건 매칭 문서31은 MustNot으로 제외했다. 점수 0인 optional도
  매칭 개수에 포함했다. 두 샤드 구성 모두 MSM2/3에서 중복 점수가 재현됐다.
  문서30은 additive 기대5에 비해 MSM2에서30, MSM3에서20으로 점수가 부풀었다.
  이는 각각 4개 매칭 조건의 C(4,2)=6 / C(4,3)=4개 분기에 필수 점수까지 재합산된 결과다.
  진단용 DisMax 구성은 12개 모두 기대 점수와 정확히 일치하지만 여전히 조합을 열거한다.
- 현 production 소스에 대한 기존 compound60건 재진단에서도 MSM2의 4건이 additive
  점수와 크게 달랐다(1샤드 최대4.336858511, 3샤드4.429452419).
  probe와 additive 점수의 최대 차이는2.384185792e-7 미만이다. 이 비교는 native leaf의
  합산을 기준으로 하며 새 OpenSearch HTTP 비교 또는 min_score/페이지 통과 증거가 아니다.
- 새 production 실행 파일은 만들지 않았다. 전체 HTTP/성능을 새로 실행하지 않았고
  앞 단위 e49e5b61의 FAIL과 수락0/40을 유지한다. 다음은 위 native primitive 구현이며
  완료 전 전체 non-plugin 게이트는 생략하지 않는다.

증거 경로는 `target/core-replacement-c06/native-msm-overlap/`이다.

| 파일 | SHA-256 |
| --- | --- |
| engine.log (첫 실패) | 7ce8d692f071bd03a7637d45215843f07eaf77c11566aae9a42f0a242ab7f307 |
| engine-v2.log | e77881da058ef1adf037980fc8167d53733580cdadf616478e7dbc3bf0eb6baa |
| overlap-v2.json | eb18465ba2ca61d12b43c22fa92cc199e05b23e51f883c2d3c53dcd562e8b19f |
| compound-v2.json | 796f10056aca98f6c36f19a3cb660e81aa9d05a31f620ca11e31dffdae6b88fa |

시험 소스 native_ranking_audit_tests.rs SHA-256:
270e69123a0a7149b86626078dd73650b8d2290fbe984febf52c62f46e219f27.
production lib.rs SHA-256은44eb00b14c7ac6ca6fb0720c0310f5442bffb58014de63f2179aea06aa4636ec로 불변이다.

## 2026-09-10 native MSM query 구현 (전체 게이트 대기)

### 변경과 보호 범위

- vendor Tantivy 0.21.1에 `MinimumShouldMatchQuery`/Weight를 추가했다. 기존 Union의
  horizon별 child 집계에 opt-in membership predicate를 적용하며 별도 합집합 엔진이나
  source 재검색을 만들지 않는다. 기존 combiner는 predicate 실행 없이 기존 경로를 쓴다.
- 임계값을 만족한 문서의 child score는 각각 한 번만 더한다. 점수 0인 child도 count에
  포함하고 scoring-disabled에서도 count를 보존한다. 조건을 만족하지 않는 전체 horizon은
  다음 postings 구간으로 넘긴다. Count의 bulk 버퍼 재사용 시 count/score를 초기화한다.
- 새 Weight는 기본 scorer 기반 수집 경로를 쓰므로 기존 BooleanWeight의 무제약
  term-union BlockWAND로 우회하지 않는다. 기존 Query/Weight API와 정수 BM25는 유지한다.
- Bool helper의 MSM>1 조합 열거를 새 쿼리로 교체했다. required/filter/excluded는
  기존 BooleanQuery로 조합하며 MSM0/1 경로와 unsupported-child 처리를 유지한다.
  다른 tokenized-field-set/fuzzy 조합 열거는 아직 남아 있다.
- Compound source guard, analyzer/필드/샤드 권위 조건, min_score/정렬/페이지,
  권한/오류 경로는 변경하지 않았다. 이것만으로 compound HTTP 호환성이나 source 경로의
  성능 병목이 해결되었다고 주장하지 않는다. constant_score boost 결함도 미해결이다.

### 엔진 증거와 남은 게이트

- 전체 engine 951=931+7+4+9 통과, 실패/ignore/filter 0이다. Count 버퍼 회귀 입력을
  강화한 최종 재실행도 exit 0이며 lib15.84초, integration15.86/2.74/0.29초다.
- native 직접 시험은 8200문서, 빈 horizon, 4096/4098/8193 위치, seek/종료,
  Count/TopDocs, boost, 삭제 문서, 128개 중복 조건 중100개 요구, 점수0 조건,
  없는 term/불가능한 threshold/빈 query를 포함한다. 4098 매칭 count가 다음 horizon의
  8194 문서로 누출되지 않는 입력을 별도로 고정했다.
- 1/3샤드 MSM0~5의 12조건은 native 점수가 기대와 정확히 일치한다. 이전 MSM2/3의
  기대5 대 실제30/20 중복 합산이 사라졌다. 기존 compound60조건도 native leaf 합산과
  비교한 최대 차이가2.384185792e-7 미만이다. HTTP 허용오차를 바꾸지 않았다.
- 동결 소스는 `target/core-replacement-c06/native-msm-query-candidate/source`이다.
  앞 후보의 frozen dependency 설정(tantivy-fst vendor patch 포함)을 유지하고 현재
  crates/tools/vendor Tantivy를 반영했다. root와 frozen의 의존 환경이 같다고 주장하지 않는다.
- 새 후보의 확장 HTTP2601건과 전체 non-plugin 반복6실행/12토폴로지는 아래 후속 결과처럼
  종료했지만 성능은 FAIL이다. 엔진 통과만으로 구현 단위를 완료 처리하지 않는다. 최초 v0.6.0의 누적
  throughput95%/각 mean,p95,p99 105% 조건과 예외/제외 규칙을 그대로 적용한다.
  이전 e49e5b61 FAIL을 새 구현의 측정 결과로 재사용하지 않는다. 수락0/40,릴리즈 보류다.

증거 경로는 `target/core-replacement-c06/` 기준이다.

| 파일 | SHA-256 |
| --- | --- |
| native-msm-query/engine-v2.log | 702069c77c43670bf5397ecb0320fe06a44b8b17bb80b618863b24ee0816e292 |
| native-msm-query/overlap-v2.json | ac4de1e8c8dde3d0b27f84c075ccd73e2a9f98bd1ed4ddfed78cdbb0dfdd3236 |
| native-msm-query/compound-v2.json | 80e170a68240484595005a02db80dd28b8231c179527f642aa821dab1052a463 |
| native-msm-query-candidate/source.sha256 | 15bb39ebe6f167b2dab01b04a6282aee9ff1d907fb4703186350c38cf86ee482 |

production lib.rs:2a955d1c6fa76634df13afabfd5dca142b17179e3145575b87dc81704adc1be8.
native_ranking_audit_tests.rs:8629160bdbdba5d00d66c282c71284a396ebd2fa5521bea547a66295cb7ce19f.
vendor minimum_should_match.rs:faf203b63c59ba43f6262e1ebee27b7a715a8552bfb5f4ce91352bb182d5df7a.
vendor union.rs:b34d3d739ee5b2ec6d13f24e8cf3d3167e2b8ae85d6ccdac6469a6193ad0083e.
vendor score_combiner.rs:d3b38a92c4f4b28ee66a5609a3586b307fe7d09346ca254d0dc14ecf585e6037.

후보 release build는 5분28초, exit0으로 종료했다. 실행 파일은
`target/core-replacement-c06/native-msm-query-candidate/artifacts/steelsearch`, SHA-256
24e36d758fc43f99d491d2bcc29bea39dc678f1d2c28cc6c4ae3d5cdc45d3a0d이다.
candidate-build.log SHA-256은0112a3def61e12fe61c916045082b3fa0a0ac6c21adc390666cebaa31da5818f이다.
빌드 후 source.sha256 전체 검증을 통과했다. 이전 e49e5b61 실행 파일/소스/증거는
보존했고 재사용 가능한 build cache만 새 후보 디렉터리로 이동했다.

### 새 실행 파일 전체 HTTP 비교

- `native-msm-query-release-live/execution.json`의 실제 실행 파일24e36d75는
  36 subrun,2601=2322통과279실패,skip0,setup실패0으로 종료했다(exit1).
  count probe/바이너리 불변/fixture 불변은 모두 true다.
- 참조는 OpenSearch3.7.0-SNAPSHOT, build f991609d190dfd91c8a09902053a7bbfe0c27b3e,
  Lucene10.4.0이다. 성능 비교의 pinned OpenSearch2.19 이미지와 혼동하지 않는다.
- 직전 e49e5b61과 fixture별 전체 summary가 동일하다. 실패는 routing17,native audit11,
  stable audit8,phrase explain14,exact phrase3,compound50,array135,repeated phrase41이다.
  공통1500건은 통과다. native 직접 score 합산 수정이 compound HTTP50건을 해결한 것으로
  계산하지 않는다. source guard/authority를 아직 바꾸지 않았다는 범위와 일치한다.
- 실행 증거 SHA-256:652dae27501422ac8ae5832d7760d06b651c966756b65f2eb9b23188dba14294.
  compound report SHA-256:fcf50df44321bf0f7d3e59ca82572432b58309ed80e1225530dd422129daab03.
  HTTP 종료 후 frozen source.sha256 검증도 통과했다. 아래 필수 명령도 후속 실행했고
  성능 FAIL을 기록했다. 전체 suite 실행을 수락 완료로 간주하지 않는다.

```sh
python3 tools/run_core_performance_gate.py \
  --baseline-binary target/core-replacement-s01/baseline/steelsearch \
  --candidate-binary target/core-replacement-c06/native-msm-query-candidate/artifacts/steelsearch \
  --output-dir target/core-replacement-c06/native-msm-query-repeated-full
```

측정 중 다른 빌드/시험/진단/소스 변경 없이 전체6실행을 마치고, 모든 published/paired/
baseline-drift 결과를 보존한다. v0.6.0 원본 증거/실행 파일/기준선은 변경하지 않는다.

### 24e36d75 전체 성능 결과

- 1095.685초,6실행/12토폴로지,자식 returncode0/요청 오류0,입력 불변 확인,
  numeric_budget_passed=false,acceptance_established=false,부모 exit1이다.
- 후보01/04 처리량은 단일487.043/486.263ops/s,3노드736.687/735.571ops/s다.
  최초 v0.6.0 대비 단일34.450%/34.555%,3노드20.903%/21.023% 감소로 모두 실패다.
  published44지표 중26/23,paired20/19실패이며 baseline drift32/44 및38/44통과다.
- 단일 ranking mean21.867/22.047ms는 v0.6.0보다240.995%/243.796%,같은 반복
  OpenSearch보다73.788%/73.141% 느리다. 3노드 ranking mean10.462/10.481ms도
  v0.6.0 대비133.295%/133.717% 회귀다. 다른 처리량 우위로 이를 상쇄하지 않는다.
- [주 계획의 전체 시나리오 표](core-replacement-implementation-plan-2026-09-07.md#2026-09-10-native-msm-query-전체-반복-성능-fail)에
  모든 반복/원본 지연/고정 v0.6.0 및 OpenSearch 대비 변화율/출처를 기록했다.
  result.json SHA-256:fb3e669d0a11be06eb6c66207843c9d3d9e16d3afa24a62e5321fd25a417abdf.
  plan.json SHA-256:408538465cee459f5a609c0f0cac517d60b4aa9cab34e9b1eb837b186bdac667.
  두 파일은 target/core-replacement-c06/native-msm-query-repeated-full/ 에 있다.
- 종료 후 source.sha256 검증을 통과했다. 실행 프로세스 종료를 확인했고,측정 중
  빌드/시험/진단/소스 변경을 하지 않았다. 이번 측정은 운영 내구성/보안 인증이 아니다.
- 수락0/40,제외0,릴리즈 보류다. 누적 회귀 전체를 이번 MSM 단독 비용으로 단정하지 않는다.
  source guard가 남은 compound ranking의 native authority 연결로 회귀 해소를 이어간다.
  다음 production 변경도 전체 engine/확장 HTTP/전체 non-plugin 반복 suite와 최초 v0.6.0
  누적5% 게이트를 통과해야 하며,예외/제외로 기준선을 재설정하지 않는다.

## 2026-09-10 compound native authority 연결 (전체 게이트 대기)

최신 후속 판정: 아래 빌드/HTTP 이후 전체 반복 성능도 완료했으며 FAIL이다.
후보31281a3d의 단일 처리량493.412/488.200ops/s,3노드770.722/755.954ops/s,
고정 v0.6.0 대비 감소33.593%/34.294%,17.249%/18.834%다.
published 실패37/38개,paired 실패29/34개,baseline drift 실패3/5개(각44지표)다.
실행6회/토폴로지12개 요청 오류0,입력 검증 true,종료 후 동결 소스 검증 통과다.
기존 대기 문구는 각 단계 당시 기록이며 현재 구현 단위는 성능 미통과로 미완료다.
[전체 시나리오 표와 실행 파일별 증거](compound-native-authority-performance-2026-09-10.md)를 따른다.

### 확인한 통합 결손과 변경

- 고정 Tantivy의 기존 QueryParser/BooleanQuery/DisjunctionMaxQuery와 field-statistics
  wrapper,직전 native phrase/MSM scorer는 이미 compound score tree를 만들 수 있다.
  기존 통합은 정적 post-filter 판정 때문에 이를 source 평가로 보내고,일부 경로에서는
  수집한 native score를 다시 source score로 덮어썼다. 새로운 검색 엔진을 만들지 않았다.
- StoredIndex에 인덱스/선택 샤드별 native authority 판정을 추가했다. 기본 Text의
  Match OR,BestFields/MostFields MultiMatch,기존 검증 범위의 Phrase와 keyword Term,
  i64 Range로 구성된 Bool 트리부터 연결한다. Text 조건은 기존 phrase의 필드 옵션,
  샤드별 native token/value 호환성 검사를 재사용한다. 미검증 leaf는 source 경로에 남는다.
- Match/MultiMatch의 QueryParser 문법 오해를 막기 위해 alphanumeric/ASCII whitespace
  입력만 허용하고 AND/OR/NOT 연산자 토큰을 제외한다. fuzzy/cross_fields/phrase_prefix,
  0 또는 비유한 boost,없는 필드/멀티필드,미검증 tie_breaker 등은 이 판정에서 거부한다.
  MultiMatch/Phrase에 보존된 analyzer 옵션은 검사한다. Match 원본 analyzer 한계는 아래와 같다.
- 일반/전체 native hit 수집,sharded page 수집,Count와 readonly query context에 동적 판정을
  연결했다. 정적 helper를 전역으로 완화하지 않았다. native authority가 있는 경우
  source 점수 보정과 score0을1로 바꾸는 보정을 적용하지 않는다.
- min_score를 포함한 request-filter 경로는 해당 Bool의 native 점수를 재사용한다.
  alias/slice/post_filter/aggregation/index boost 순서를 보존하며,derived 필드 요청은
  기존 평가를 유지한다. 이 경로에는 기존 전체 문서 순회와 native hit materialization이
  남아 있으며 별도 bounded min_score collector를 구현했다고 주장하지 않는다.
- 정렬을 native page collector가 지원하지 않으면 선택 샤드를 유지한 전체 native 정렬을
  사용한다. 단일 샤드의 명시적 [0] 선택과 빈 샤드 선택을 처리했고,TopDocs limit는 실제
  searcher 문서 수로 제한해 usize::MAX 페이지 오프셋의 과도한 할당을 막는다.
- _id Term은 필터/제외 subtree에서만 허용한다. scored _id 또는 그 밖의 미검증 query를
  무조건 허용하지 않는다. 권한/오류/인덱스 범위 조건을 제거하지 않았다.

### 엔진 검증과 실패 이력

- 첫 전체 실행: lib929통과3실패. 기존 source score 비트 일치 시험1건,
  새 fixture의 _id 제외 조건1건,명시적 _id 정렬의 None 반환1건이었다.
- 두 번째: lib932통과1실패. 단일 샤드 [0] 선택이 sharded 전용 함수로 분기해 None을
  반환하는 문제였고,정렬용 전체 native 수집에서도 선택 범위를 올바르게 처리하도록 수정했다.
- 최종 전체 실행: 953=933+7+4+9통과,실패/ignore/filter0,exit0.
  빌드1분26초,lib16.84초,integration15.25/2.86/0.31초다. 첫 두 로그도 보존했다.
- compound fixture의 Bool 쿼리에 대해 일반/필드 정렬,페이지0~2,min_score없음/1.42의
  total/hit 수와 native score 비트 보존을 시험했다. 기존40문서 Bool/MultiMatch 페이지 시험도
  1/3샤드,선택없음/빈선택/[0]/전체선택,여러 from/size/정렬에서 native score를 정확히 비교한다.
  이 시험의 oracle을 source 산술에서 native score로 변경했으며 점수 허용오차를 넓힌 것이 아니다.
  HTTP comparator나 참조 fixture는 변경하지 않았다.
- 미검증 leaf 거부 시험과 refresh 후 샤드별 통계 변경 시험을 추가했다. 숫자 Text 값을 가진
  샤드는 전체 authority를 거부하고,그 샤드를 제외한 선택 범위는 허용하는 것을 확인했다.

### 별도 미해결 사항

- 기존 os-query-dsl::parse_match는 query가 있는 object에서 analyzer 등 일부 옵션을
  Query::Match에 보존하지 않는다. 현재 Query IR 판정으로 소실된 원본 옵션을 구별할 수 없다.
  이번 연결은 원본 Match analyzer 지원/거부를 검증한 것이 아니며,그 옵션까지 보호한다고
  주장하지 않는다. metadata 보존/오류 처리/분석기 연결을 후속으로 해결해야 한다.
  ConstantScore boost 정보 소실도 이전 기록대로 미해결이다.
- 전체 HTTP/min_score의 OpenSearch 비교는 아래 후속 결과처럼 실행했고 성능은 아직
  측정하지 않았다. native score 보존을 HTTP 완전 호환이나 누적 성능 통과로 확대하지 않는다.

### 동결 소스와 필수 후속 게이트

후보 소스는 target/core-replacement-c06/native-compound-authority-candidate/source 이며
직전24e36d75 frozen dependency 설정을 유지하고 현재 crates/tools를 반영했다.
root와 frozen은 기존 tantivy-fst patch 차이가 있다. 후속 release 실행 파일31281a3d는 아래에 기록했다.

1. 별도 후보 디렉터리에서 release 빌드하고 실제 실행 파일 SHA-256을 기록한다.
2. Count probe와 기존36 fixture/2601건 이상의 전체 HTTP 비교를 실행하고 모든 실패를 보존한다.
3. 전체 non-plugin 반복6실행/12토폴로지를 실행한다. 고정 최초 v0.6.0 대비 각 topology
   throughput95% 이상,시나리오별 mean/p95/p99105% 이하를 각각 만족해야 한다.
   실패 시 조사/최적화/전체 재실행하며,단독5% 이상 미해결 구현의 제외/예외는 기존 규칙을 따른다.
   직전 후보나 새 릴리즈로 기준선을 재설정하지 않는다. focused 측정은 전체 suite를 대체하지 않는다.

수락0/40,제외0,릴리즈 보류다. 이번 구현 단위는 전체 게이트 대기 상태이며 미완료다.

target/core-replacement-c06/ 기준 증거:

| 파일 | SHA-256 |
| --- | --- |
| native-compound-authority/engine-first.log | 0db173689310f3012625dff29a242b5c73066f67f558d790c5a063df6c87c2a8 |
| native-compound-authority/engine-v2.log | 1f2844e6f010ad45ef5306d19449dcc5b0ec84530f25782f5c454d987b186b01 |
| native-compound-authority/engine-v3.log | b32e6b6d7486fa8057babd0391b1fa6052b90d5fbe3423fc33a673de5abff486 |
| native-compound-authority-candidate/source.sha256 | 8f9ac5a7e7ebd040343e2b978983c94f1d044c14fd3f61b8b2ea85fe79768b1f |

production lib.rs:bbe75c9ef058bc7be15fad2e4c4b66fa297073d953df8ee074a098862dcfacf7.
native_ranking_audit_tests.rs:5e03aafcc1966ac8f850a1bd506dffd870565d770e46470f9ad8711dcc955080.
multi_match_field_tests.rs:c9fb08af0327b595e084d41627c2b162656c7370f9b5c8d670a654b31b3cd5a9.

### 31281a3d 빌드와 전체 HTTP 후속 결과

- release 빌드는5분02초,exit0으로 완료했다. 실행 파일은
  target/core-replacement-c06/native-compound-authority-candidate/artifacts/steelsearch,
  SHA-256 31281a3dbfa3007e720616ff9b36b90e77558324ab4fd2c0e44fb526fcbf1f75이다.
  source.sha256은 빌드 전후 및 HTTP 종료 후 전체 검증을 통과했다.
  이전24e36d75 실행 파일/소스/증거는 보존했고 build cache만 새 후보 디렉터리로 이동했다.
- 전체36 subrun,2601=2351통과250실패,skip0,setup실패0으로 종료했다(exit1).
  Count probe/실행 파일 불변/fixture 불변은 모두 true다. 공통1500건은 모두 통과했다.
  실제 기능 참조는 OpenSearch3.7.0-SNAPSHOT,f991609d190dfd91c8a09902053a7bbfe0c27b3e,
  Lucene10.4.0이며 성능용 pinned OpenSearch2.19와 혼동하지 않는다.
- 직전24e36d75와 전체2601개 case name/status를 대조했다. 누락0,해결29,새 실패0이다.
  native audit의3-full-ranking 1건과 compound fixture28건이 해결됐다.
- 잔여 실패는 routing17,native audit10,stable audit8,phrase explain14,exact phrase3,
  compound22,array135,repeated phrase41이다. 실제 실패를 생략하거나 통과로 재분류하지 않았다.
- compound60건은38통과22실패다. total과 문서 집합60/60이 일치하고,순서는52/60일치한다.
  잔여22건은순서8/점수만14건이며 membership 실패는0이다. ID별 raw 점수 최대 차이는
  4.887207030179752e-7이다. 작은 차이라는 이유로 comparator의 six-decimal 기준을 완화하지 않았다.
- min_score1.42,1/3샤드,page0/1 네 조건이 모두 통과했다. 특히1샤드 repeat 문서가
  약1.430177로 포함되고,total2와 다음 페이지 repeat를 보존한다. 이전 source 점수의
  약1.408135 때문에 발생한 문서 누락은 이번 후보에서 해결됐다.
- 빌드와 HTTP 프로세스가 모두 종료됐음을 확인했다. 아직 새 후보의 성능 값은 없으며,
  아래 전체 반복 게이트를 실행하기 전 다음 production 변경이나 구현 완료로 넘어가지 않는다.
  수락0/40,제외0,릴리즈 보류다. 직전 후보의 성능 FAIL을 새 후보 측정값으로 재사용하지 않는다.

target/core-replacement-c06/ 기준 추가 증거:

| 파일 | SHA-256 |
| --- | --- |
| native-compound-authority-candidate/candidate-build.log | 18abb88477468e20abdfc24933f6a28675240c4064fb1b30989cd7894a1132b4 |
| native-compound-authority-release-live/execution.json | 878ca247b1f13265606d0146c16b00033afe083186516a33d805ee2653e05080 |
| native-compound-authority-release-live/search-native-compound-ranking-compat-report.json | c913ed63609625bda8c358ada1301d1a73688aa5efc3af295e5d40ffc90b6f58 |
| native-compound-authority/http-classification.json | 421182ef6494fd8379da4861c97a32d5103f2702633f6e7e9d8ad5b1c85b0556 |

필수 다음 명령:

```sh
python3 tools/run_core_performance_gate.py \
  --baseline-binary target/core-replacement-s01/baseline/steelsearch \
  --candidate-binary target/core-replacement-c06/native-compound-authority-candidate/artifacts/steelsearch \
  --output-dir target/core-replacement-c06/native-compound-authority-repeated-full
```

측정 중 다른 빌드/시험/진단/코드 변경을 하지 않고 전체6실행/12토폴로지를 유지한다.
최초 v0.6.0의 throughput95%/각 mean,p95,p99105% 누적 게이트를 그대로 적용하고,
실패 시 조사/최적화/전체 재실행 및 기존 제외/예외 규칙을 따른다. 기준선 재설정은 없다.

### 31281a3d 단일 노드 ranking CPU 후속 진단

전체 반복 종료 후 기존 tools/run-core-cpu-diagnostic.py로 동일 후보의 ranking=100,
단일 노드/3샤드/5000문서/4클라이언트/45초 부하 중49Hz/20초 CPU capture를 실행했다.
matrix/perf exit0,실행 전후 binary SHA 동일,관측21.469초 동안 서버 CPU22.12초,
부하 생성기 CPU18.75초다. 진단 프로세스는 종료했다. 성능 gate의 대체 측정이 아니다.

perf의 전체 수집 표본(서버와 부하 생성기 포함) 기준 self 비중은 JSON f64 직렬화4.69%,
Tantivy term Union build1.74%,BooleanWeight complex_scorer1.58%다.
children 포함 native sharded page9.26%,Count/TopDocs5.40%,응답 변환8.66%가 관측됐다.
inclusive 비중은 중복되므로 합산하지 않으며 서버만의 CPU 비중으로 해석하지 않는다.
ranking이 native 샤드 수집을 사용한다는 증거지만 source fallback의 전면 제거 증명은 아니다.
원인 확정을 위한 다음 비교 대상은 native scorer 구성/수집과 응답 직렬화다.
기준선의 동일 진단 없이 이 비중을 누적 회귀의 단독 원인이나 예상 개선율로 주장하지 않는다.
production 변경은 없으며 다음 수정 단위에도 전체 engine/HTTP/반복 성능 gate를 적용한다.

증거: target/core-replacement-c06/native-compound-authority-cpu-ranking-single/.
diagnostic.json SHA-256 `61daa4539af5916ce3a76d7f07aeec9e934b1469079c241449464f2a9095fdfd`.
perf.data SHA-256 `d308130cb42531e3e2f938d87441c35ab689dff5cd42faead3c031b0837616e6`.

### 고정 v0.6.0 동일 ranking CPU 비교

동일 도구/49Hz/45초/ranking=100/단일 노드 조건으로 고정 db244133 바이너리도 실행했다.
matrix/perf exit0,요청 오류0,실행 전후 SHA 일치다. 관측20.858초의 서버 CPU32.90초,
부하 생성기13.89초이며 후보의21.469초 관측과 동일 시간이라고 간주하지 않는다.
전체45초 진단 부하는 다음과 같다. 프로파일 오버헤드가 있으므로 acceptance 결과가 아니다.

| 실제 바이너리 | ops/s | ranking mean/p95/p99 ms | 성공 요청 |
| --- | ---: | --- | ---: |
| db244133 고정 v0.6.0 | 1326.307 | 3.005 / 4.750 / 5.816 | 59687 |
| 31281a3d 후보 | 826.506 | 4.827 / 7.729 / 9.391 | 37197 |

기준선 self 표본에는 source_value_for_highlight_field8.96%,
score_document_query_with_bm25_context3.66%,memcmp10.98%가 나타난다.
이는 기준선도 source 경로를 사용했음을 보여준다. native로 전환했다는 사실만으로
누적 회귀가 해결되거나 모든 비용이 감소한다고 주장할 수 없다.
현재 진단은 응답 바이트/동일 쿼리별 hit 수를 기록하지 않으므로 직렬화 비용 차이를
새 코드의 직렬화 회귀로 단정하지 않는다. 다음 비교에서 이 정보를 먼저 확보한다.

고정 Tantivy0.21.1의 collector/mod.rs tuple Collector와 BooleanWeight::for_each,
현재 search_tantivy_count_and_top_docs_with_scores도 확인했다. relevance 페이지는
이미 (Count, TopDocs) 결합 collector로 한 번 수집한다. Count와 TopDocs 중복 검색을
제거한다는 구현은 현재 근거가 없다. exact total을 없애거나 source 재평가로 되돌리지 않는다.
다음 production 수정은 동일 요청별 증거를 바탕으로 정하고,수정 단위 종료 전 전체 engine,
확장 HTTP와 전체 non-plugin 반복 벤치마크를 실행한다. 고정 v0.6.0 누적5% 기준은 유지한다.

증거: target/core-replacement-c06/native-compound-authority-cpu-ranking-baseline-single/.
diagnostic.json SHA-256 `aee0e740fbaaa15f6accd11040e41a5730fa063fac277dd8f9b028300bb74c22`.
perf.data SHA-256 `4960a8cae78460c5023335b3d2c6e4b4ff35c8bd8ec07478aacaf186768cea06`.

### 동일96개 ranking 요청의 반환량 차이 확인

기존 LoadRunner.prepare_index/seed_corpus/document_for를 재사용해5000문서,
384 source 값,3샤드/replica0의 새 단일 노드 인덱스를 각각 만들었다.
LoadRunner.run_operation의 실제 ranking 선택지4x2x4x3=96조합을 전부 생성해
동일 쿼리를 db244133,31281a3d 및 pinned OpenSearch2.19.0에 보냈다.
이것은 초기 seed 코퍼스의 순차 기능 진단이며 write/refresh 혼합 부하나 전체 gate가 아니다.

| 실제 실행 | 빈 결과 쿼리 | 10 hits 반환 쿼리 | OpenSearch와 total value/relation 일치 | 응답 전체 bytes |
| --- | ---: | ---: | ---: | ---: |
| db244133 v0.6.0 | 96 | 0 | 30/96 | 15360 |
| 31281a3d 후보 | 30 | 66 | 96/96 | 1819672 |
| pinned OpenSearch2.19.0 | 30 | 66 | 참조 | 1812344 |

OpenSearch 실제 build fd9a9d90df25bea1af2c6a85039692e815b894f5,Lucene9.12.1,
이미지 digest1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb를
container inspect로 확인했다. 두 SteelSearch 실행 파일도 실제 프로세스/종료 후 SHA를 확인했다.
세 실행의 최종96응답은 status200,timeout없음,실패 shard0이다.

v0.6.0은 이 코퍼스의66개 쿼리에서 실제 일치 문서를 누락한다. 따라서 기준선의 빠른
ranking 수치를 동일한 결과 정확도/응답량의 처리 비용으로 설명할 수 없다.
후보의 total 일치는 개선 증거지만 비어 있지 않은66쿼리의 상위10 ID 집합/순서는
OpenSearch와 모두 다르다. 나머지30개 빈 결과만 ID가 같으며 점수/동점 처리 원인은
추가 확인 대상이다. total 일치만으로 전체 ranking 호환을 주장하지 않는다.
이 증거로 성능 회귀를 자동 면제하거나 기준선을 바꾸지 않는다. 기존 누적5% FAIL,
수락0/40과 릴리즈 보류는 그대로다. 결과 누락을 재도입해 성능을 맞추지도 않는다.

첫 OpenSearch 시도는 문서4604 적재 시 disk flood-stage429로 실패했다.
불완전 코퍼스는 비교에서 제외하고 실패 result.json을 보존했다. 안전장치 변경 없이
후보의 재생성 가능한 release build cache만 cargo clean으로822.5MiB 정리한 뒤
별도 디렉터리에서 처음부터 다시 실행해96건을 완료했다. 동결 소스/실행 파일은 보존했다.
진단용 두 스크립트는 target/core-replacement-c06/compare-ranking-responses.py와
compare-ranking-reference.py다. production 코드는 변경하지 않았다.

target/core-replacement-c06/ 기준 증거:

| 파일 | SHA-256 |
| --- | --- |
| native-compound-ranking-response-comparison/result.json | 8da12fb144f4f4f8ead137e7a3184fda5d0ef18c1c386102c6e09cbdbb76f078 |
| native-compound-ranking-response-reference/result.json (실패) | d42943184119dbf5d796b97d59fd200aa6595fc78546ef696c666f4c375ceb43 |
| native-compound-ranking-response-reference-retry/result.json | e27ec2ef4fd5c9b5019e7fa41bc5d8a1d68e9530b781023c22a0f6c497830605 |

### 참조 버전별 점수 차이와3.7 전체96조건 후속 검증

첫 쿼리의 OpenSearch2.19 explain은 title 항2.8238423과 keyword service 항1.4119211을
합산해4.2357635를 반환한다. title boost4.4(필드 boost2 x2.2),keyword boost2.2가 보이며
두 필드의 n404/N1659를 사용한다. OpenSearch3.7.0-SNAPSHOT(f991609d,Lucene10.4.0)의
같은 쿼리는 title1.2835646(boost2),ConstantScore(service:checkout)1.0을 합산해
2.2835646이다. 후보 점수2.283564567565918은 후자의 규칙과 일치한다.
따라서 이번 큰 점수 차이는 keyword native wrapper의 오류로 단정할 수 없고,
기능용3.7과 성능용2.19 참조의 기본 scoring 규칙 차이로 분리해야 한다.

3.7에 기존96개 쿼리 전부를 동일5000문서/3샤드/replica0 코퍼스로 재실행했다.
96응답 모두200,timeout없음,실패 shard0이며 다음을 확인했다.

- 후보와 total value/relation96/96일치,상위 점수 배열도 소수점6자리96/96일치.
- 정렬 위치별 raw 점수 최대 차이4.695434574486512e-8이다.
- 빈30조건은 ID일치,비어 있지 않은66조건은 상위10 ID가 다르다.
  그66조건의 참조 상위10 점수는 각 조건 안에서 모두 동점이다.
  상위 점수 배열 일치가 모든 문서의 점수/전체 동점 집합 일치 증명은 아니다.
- 서로 다른 explain 실행의 최상위 ID도 달랐다. native scorer를2.19 점수로 바꾸는
  근거로 쓰지 않으며,기존 strict comparator나 잔여250개 실패를 완화하지 않는다.

이번 단계는 진단/증거 추가이며 production 변경이나 구현 단위 완료가 아니다.
고정 v0.6.0의 결과 누락과5% 누적 FAIL도 그대로 보존한다. 다음 성능 개선은
현재3.7 scoring 계약을 보존해야 하며,각 수정 단위의 전체 engine/HTTP/반복 gate가 필요하다.
성능용2.19 대비 처리량 우위는 동일 scoring 계약의 완전 대체 성능으로 확대하지 않는다.

target/core-replacement-c06/ 기준 증거:

| 파일 | SHA-256 |
| --- | --- |
| native-compound-ranking-response-reference-explain/result.json | ffaec046d9ab7dcdee2b58b9f4c044678cdbfd54d354974abf0478c9f3717bad |
| native-compound-ranking-response-reference37-explain/result.json | 45dc4fc15b8fd5cf7ab7d515db31f899cfab7d815637030af15512c877bb19c2 |
| native-compound-ranking-response-reference37-full/result.json | 8eb5874921d7e162f2250320842b5f6a2bc3dd09775e552dc7e551a78246f132 |

### 혼합 부하 native authority 사전 검사 병목

후보31281a3d의 단일 노드 mixed CPU 진단을 기존 도구로 실행했다.
45초 혼합 부하 중49Hz/20초 capture,matrix/perf exit0,실행 전후 바이너리 동일이다.
관측20.798초에 서버 CPU38.29초,부하 생성기10.03초다. production은 변경하지 않았다.
전체 수집 표본 기준 self opensearch_bm25_field_stats12.44%,source field lookup7.00%,
memcmp7.84%,source token iterator2.82%다. children 포함 authority42.45%,
opensearch_bm25_field_stats42.13%이며 inclusive 수치는 중복되므로 합산하지 않는다.

코드를 대조하면 native_phrase_score_is_authoritative가 source BM25 통계에서
두 호환성 bool을 얻는다. refresh 후 캐시 miss 때 모든 문서의 source를 토큰화하고
term_doc_counts를 재구축한다. native_score_tree에서도 같은 검사를 호출한다.
실제 점수는 native인데 사전 호환성 검사 때문에 source 통계 구축이 남아 있다.
캐시 내부 문자열 처리만 최적화하는 대신 입력 검증 정보를 색인 snapshot에 보존해야 한다.

다음 구현 단위: native Text 호환성 snapshot metadata.

1. TantivySearchState.build_from_documents에서 실제 색인하는 문서의 Text 입력
   호환성만 기록한다. native token/phrase eligibility의 기존 numeric,bool,array,
   ASCII 및40자 token 보호 조건을 유지한다. source BM25 DF 통계는 만들지 않는다.
2. append_documents에서는 신규 batch만 검사하고 searcher/doc-id lookup 성공과 함께
   metadata를 게시한다. 기존 PIT/snapshot clone의 판단이 바뀌지 않도록 소유권을 분리한다.
   삭제/교체/매핑 변경의 rebuild 경로에서도 정확히 재생성한다. 실패한 refresh는
   불완전 metadata를 게시하지 않는다.
3. native authority는 선택 shard의 native snapshot metadata를 조회한다.
   native scoring이 지원되지 않는 source 경로의 통계/오류 처리까지 제거하지 않는다.
4. 기존 source 판정과 다양한 입력의 등가성,append 전후 가시성,교체/삭제 후 복구,
   selected-shards,빈 index,PIT snapshot,매핑 옵션 보호를 시험한다.
5. 전체 engine 및 확장 HTTP를 실행하고 별도 동결 release 후보를 빌드한다.
   실제 SHA와 별도 build 경로를 기록하며 전체 non-plugin6회/12토폴로지 반복 gate를
   반드시 실행한 뒤 완료 여부를 판정한다. focused CPU 진단은 대체물이 아니다.
   고정 v0.6.0 throughput95% 이상,각 scenario mean/p95/p99105% 이하를 적용하고,
   실패 시 최적화/전체 재실행 및 기존 단독5% 제외/예외 규칙을 따른다.

수락0/40,릴리즈 보류다. 이 프로파일 비중은 기대 개선율이나 off-CPU 지연 원인의 증명이 아니다.
증거: target/core-replacement-c06/native-compound-authority-cpu-mixed-single/.
diagnostic.json SHA-256 `08ab1ee0d0a1e2ffd9e9f9455ea5474073d5c8a4aa2bc02ca1d599fbbb4916fb`.
perf.data SHA-256 `2283ce77b97f03cfb86ab7ce6b3562275cb6f8841438c65d581c04cd26899078`.

### Native Text metadata 구현과 전체 engine 검증

native_text_compatibility.rs를 추가했다. top-level Text의 기존 ASCII/40자 token,
source 값 타입/phrase 호환성 및 유효 token 존재 여부를 색인 시 저장한다.
build는 실제 색인 문서만 검사하고 append는 신규 batch만 검사한다.
metadata는 작은 소유 map으로 clone되며 searcher/doc-id lookup 성공 후에만 게시한다.
native_phrase_score_is_authoritative는 선택 shard의 native snapshot을 조회하고,
더 이상 source BM25 통계의 생성 여부에 의존하지 않는다. query/mapping guard는 유지했다.
기존 source fallback 통계 생성 함수는 지원되지 않는 경로를 위해 보존했다.

전체 engine 시험955=935+7+4+9통과,실패/ignore/filter0,명령 exit0이다.
입력13x13조합의 기존 판정 등가성/snapshot clone,append 실패 시 metadata 불변,
1/3샤드의 정상값→숫자→정상값 교체 및 refresh 복구,source 통계 cache 미생성을 확인했다.
기존 샤드 선택/동시 refresh/삭제/merge/PIT 관련 전체 engine 시험도 그대로 실행했다.
새 metadata 전용 삭제 복구 등 추가 위험 검토와 release 전체 검증은 후속 단계다.

명령: env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0
cargo +nightly test -p os-engine-tantivy --lib --tests -- --test-threads=2.
초기 compiler startup 일부를 제외한 tool 출력은
target/core-replacement-c06/native-text-metadata/engine-captured.log에 보존했다.
모든 시험 결과가 포함되며 SHA-256 de0906b30524376503970d129edb20d9582f96e0a962044434d1260a0401fa96이다.

소스 SHA-256:

| 파일 | SHA-256 |
| --- | --- |
| lib.rs | 669a75b48748bdd6144395839a817dd1a3d671cd2e48a9895368a68a7ad028c5 |
| native_text_compatibility.rs | 1ff6476e0799536b36aeaa9b1a1be31fa51f85f67d41f82722bbddee20c8eeb5 |
| native_ranking_audit_tests.rs | 4db365ad38ad6488f4db6ba7faa33a4023cad49656b409ecbdc4316cc635c875 |

아직 새 release 바이너리/전체 HTTP/반복 성능 결과는 없다. 별도 동결 소스와 build
디렉터리로 release 빌드 후 전체36 fixture 이상과 non-plugin6회/12토폴로지 gate를
실행해야 한다. 고정 v0.6.0 누적5% 기준을 그대로 적용하며 이번 단위는 미완료다.
이전31281a3d의 성능 FAIL을 새 후보 측정값으로 재사용하지 않는다. 수락0/40,릴리즈 보류다.

후속 삭제 복구 검증을 추가한 최종 전체 engine 실행도955건 모두 통과했다(exit0).
1/3샤드에서 비호환 문서 삭제 후 refresh 전에는 거부,refresh 후에는 허용하며
source BM25 cache를 만들지 않는 것을 확인했다. 전체 로그 engine-final.log의 SHA는
4300457ca1d6f03b1402b2def97fc8b5eb5b7a04e1a0534079fa3d6f2daafc20이다.
최종 native_ranking_audit_tests.rs SHA는
cbbe7114b718eaf82400ac476b794fe1e04c3f96309023043e3b80d5dfb46424이다.
새 동결 후보는 target/core-replacement-c06/native-text-metadata-candidate/source,
source.sha256 SHA는53cc4036bc0f71cc5d6cb19c89b1873070df5f09363ef96b20c5e20326288c70이다.
이전 frozen dependency 설정을 유지하므로 root와 기존 tantivy-fst patch 차이는 그대로다.
개발용 build cache1.7GiB를 정리했고 동결 source manifest 검증 후 독립 release 빌드를 시작했다.

독립 release 빌드는7분53초에 exit0으로 완료했다. 빌드 후 source manifest 전체 검증도 통과했다.
후보 실행 파일은 target/core-replacement-c06/native-text-metadata-candidate/artifacts/steelsearch,
SHA-256 `6086c31c434e1defd8bdb936d2326bbddfb193b12fd69d5c5693e15e3aa31d39`다.
candidate-build.log SHA-256은 `cf80642debbb36d42fd0d246fdcbb9767a4532d0c003b408b47e5f6fda4effb8`이다.
전체 HTTP 및 non-plugin 반복 성능은 아직 미실행이며,이번 구현 단위 완료로 계산하지 않는다.

### 6086c31c 전체 HTTP 결과

최신 후속 판정: 전체 반복 성능도 완료했으며 FAIL이다. 단일 throughput 고정 기준 대비
-0.692%/+0.296%,3노드-8.404%/-9.296%,published22/25지표 실패다.
6회/12토폴로지 요청 오류0,입력 검증/종료 후 동결 소스 검증 통과다.
[모든 시나리오 성능 및 해시](native-text-metadata-performance-2026-09-10.md)를 따른다.
아래 대기 문구는 HTTP 종료 당시 기록이며 현재 단위는 성능 미통과로 미완료다.

후속 전체36 fixture/2601건을 완료했다:2351통과250실패,skip0,setup실패0,부모 exit1.
Count probe/실행 파일 불변/fixture 불변은 모두 true이며 종료 후 동결 source manifest도 통과했다.
참조는3.7.0-SNAPSHOT/f991609d190dfd91c8a09902053a7bbfe0c27b3e/Lucene10.4.0이다.
이전31281a3d와 fixture+case name2601개를 대조해 상태 변경0,누락0,추가0을 확인했다.
따라서 이번 성능 수정의 새 HTTP 실패는0이나 기존250개 실패가 해결된 것은 아니다.
compound60건도38통과22실패를 유지한다. 전체 성능은 아직 대기이며 구현 단위는 미완료다.

증거: target/core-replacement-c06/native-text-metadata-release-live/execution.json,
SHA-256 `367ba341231681c9de2bb662af1706cdaba6a9e1b9061674ecaa8a01dc09e357`.
케이스 대조 요약: target/core-replacement-c06/native-text-metadata/http-status-delta.json.

다음은 고정 db244133 baseline과6086c31c 후보의 전체 non-plugin 반복 gate다.
빌드/HTTP 프로세스는 종료했다. 측정 중 다른 빌드/시험/진단/코드 변경은 하지 않는다.
고정 v0.6.0 누적throughput95%/각 mean,p95,p99105% 기준과 제외/예외 규칙은 유지한다.

```sh
python3 tools/run_core_performance_gate.py \
  --baseline-binary target/core-replacement-s01/baseline/steelsearch \
  --candidate-binary target/core-replacement-c06/native-text-metadata-candidate/artifacts/steelsearch \
  --output-dir target/core-replacement-c06/native-text-metadata-repeated-full
```

### 6086c31c 후속3노드 및 쓰기 진단

전체 gate 종료 후 기존 CPU 도구로 후보3노드 mixed,후보 단일 write,
고정 v0.6.0 단일 write를 각각 실행했다. 모두45초 부하/49Hz/20초 capture이며
matrix/perf exit0,실행 전후 SHA 동일이다. full gate의 대체 측정이 아니다.

후보3노드 mixed 표본에서 source BM25 통계 재구축은 self0.8%/inclusive3% 이상
출력의 주요 항목으로 나타나지 않았다. 검색 native page inclusive5.98%,
JSON 직렬화4.54%,merge의 column 순회 self1.51%가 관측됐다.
전체 표본에는 부하 생성기도 포함되며 inclusive 비중은 합산하지 않는다.
이 표본만으로 off-CPU 대기나 단독 회귀의 원인을 확정하지 않는다.
3개 서버의 CPU 합계26.35초,부하 생성기13.37초,관측20.763초다.

| 쓰기 전용 진단 | 성공 요청 | ops/s | mean/p95/p99 ms |
| --- | ---: | ---: | --- |
| 6086c31c 후보 | 54181 | 1203.986 | 3.312 / 5.071 / 6.021 |
| db244133 v0.6.0 | 54211 | 1204.657 | 3.310 / 5.080 / 6.045 |

두 쓰기 실행 모두 요청 오류0이며,관측 약20.61초 동안 서버 CPU는6.51/6.29초,
부하 생성기는23.83/23.82초다. 1회씩의 프로파일 부하로 쓰기 경로의 단독 큰 회귀가
재현되지는 않았다. 이를 정식 mixed write 실패의 면제나5% PASS로 사용하지 않는다.
다음 조사 우선순위는 혼합 부하에서 refresh/쓰기 경쟁과3노드 refresh 비용이다.
기존 run-core-refresh-work-diagnostic.py는 반복 before/after/after/before 및
입력 불변/노드별 refresh counter를 지원하므로 신규 source 스캔 진단을 만들기 전에 활용한다.
원인에 근거한 수정 단위마다 전체 engine/확장 HTTP/non-plugin 반복 gate를 실행한다.
production 변경 없음,수락0/40,누적 gate FAIL 및 릴리즈 보류 유지다.

target/core-replacement-c06/ 기준 증거:

| 파일 | SHA-256 |
| --- | --- |
| native-text-metadata-cpu-mixed-three/diagnostic.json | 9acb4b13bbfe9877a196c8f85220e2c364144f0b51a19b3b43ad6338a7daf2a4 |
| native-text-metadata-cpu-mixed-three/perf.data | d967646ccc1edcf695c2cf4a2b599087b85442467a366316a00453ed202787a7 |
| native-text-metadata-cpu-write-single/diagnostic.json | e4944abca29389b60a9d9ed0d36fd98982dc732b52d74190020988bd4a1ff6dd |
| native-text-metadata-cpu-write-baseline-single/diagnostic.json | b9e42d20e071d84ccb8dc3b1bda2fa8773102a076233ab2e4ed01afae08bef96 |

### 6086c31c 3노드 refresh 반복 가시성 진단

기존 run-core-refresh-work-diagnostic.py로 db244133/6086c31c를
before/after/after/before 순서로4회 실행했다. 각60초/5000문서/384값/4클라이언트,
3샤드/replica1 및 기존 non-plugin 혼합 비중을 사용했다. 부하 종료 후 모든 endpoint에
추가 refresh를 두 번 수행했다. 도구 exit0,모든 요청 오류0이며 실제 실행 identity와
입력 불변 검증을 통과했다. CPU 프로파일은 사용하지 않았다.

| 실행 | 실제 바이너리 | ops/s | refresh mean/p95/p99 ms | seed+성공 write |
| --- | --- | ---: | --- | ---: |
| 0 | db244133 | 923.674 | 8.431 / 17.119 / 22.308 | 14839 |
| 1 | 6086c31c | 853.983 | 9.017 / 18.264 / 23.793 | 14157 |
| 2 | 6086c31c | 864.914 | 8.803 / 17.963 / 23.885 | 14253 |
| 3 | db244133 | 920.632 | 8.511 / 17.462 / 22.463 | 14815 |

두 번째 추가 refresh 후 endpoint 순서의 native/fallback count:

| 실행 | endpoint1 | endpoint2 | endpoint3 |
| --- | --- | --- | --- |
| 0 | 6060 / 6281 | 4244 / 4244 | 4314 / 4314 |
| 1 | 5935 / 5935 | 4049 / 4049 | 4173 / 4173 |
| 2 | 5979 / 5979 | 4087 / 4087 | 4187 / 4187 |
| 3 | 6064 / 6247 | 4240 / 4240 | 4328 / 4328 |

모든 실행에서 첫 추가 refresh 이후 두 번째까지 값은 안정됐다. 후보는 각 endpoint의
native/fallback이 같지만 기준선은 첫 endpoint에221/183건 차이가 남는다.
endpoint별 관측은 global unique cardinality가 아니며 합산으로 전체 ID/내용 완전성을
증명하지 않는다. 실제 workload의 endpoint 분산과 전역 검색 지원 계약은 별도 검증 대상이다.
이 결과를 후보에서 의도적으로 문서를 덜 처리해 성능을 맞출 근거로 사용하지 않는다.

refresh 지연은 이 진단에서도 남았지만 node-counters 옵션은 사용하지 않아
document-add/commit/reload/lookup 세부 비용을 분리한 증거는 없다.
따라서 다음 수정 전에는 지원되는 후보들의 native refresh 세부 계측이나
동일 작업량의 refresh phase 비교가 필요하다. 기존 전체 gate FAIL을 면제하지 않으며
새 수정 단위마다 전체 engine/HTTP/non-plugin 반복 gate를 다시 실행한다.
이번 단계는 진단이며 production 변경 없음,수락0/40,릴리즈 보류다.

증거 디렉터리: target/core-replacement-c06/native-text-metadata-refresh-three-abba/.
result.json SHA-256 `60303c8435e58a6e2b61f19dd1c0043cbc7c4b73eea63cd321391c19897fc63a`.
plan.json SHA-256 `fbc5737cc048bc9667a77b26fcdf6ced91fd1809c97e214212f0952ff419fb4f`.

### 기존 전체 gate의 refresh 단계 카운터 재검토

추가 실행 전에 기존 native-text-metadata-repeated-full의 resource_usage에 이미 저장된
refresh 카운터를 읽었다. 아래는 before/after 차이의 누적초이며 per-request 지연이 아니다.
3노드의 metrics 수집 범위는 전체 노드 합산으로 검증되지 않았으므로 클러스터 전체 CPU나
refresh 평균으로 나눠 해석하지 않는다. workload의 실제 refresh/write 횟수도 서로 다르다.

| 실행 | 토폴로지 | add 초 | commit 초 | reload 초 | ID lookup 초 |
| --- | --- | ---: | ---: | ---: | ---: |
| 00 db244133 | 단일 | 0.514 | 14.960 | 0.627 | 2.509 |
| 01 6086c31c | 단일 | 0.681 | 15.194 | 0.790 | 0.353 |
| 04 6086c31c | 단일 | 0.671 | 15.432 | 0.791 | 0.343 |
| 05 db244133 | 단일 | 0.499 | 14.421 | 0.597 | 2.398 |
| 00 db244133 | 3노드 관측 | 0.303 | 11.855 | 0.375 | 0.846 |
| 01 6086c31c | 3노드 관측 | 0.450 | 11.363 | 0.382 | 0.202 |
| 04 6086c31c | 3노드 관측 | 0.404 | 11.247 | 0.387 | 0.213 |
| 05 db244133 | 3노드 관측 | 0.385 | 11.585 | 0.379 | 0.898 |

관측된 ID lookup 누적 비용은 후보에서 줄었고 commit이 주요 계측 구간이다.
전체 회귀를 ID lookup 재구축으로 돌리거나 add 증가량만으로 전체 지연을 설명하지 않는다.
원본은 기존 전체 gate의 각 summary.json이며 해시는 성능 문서에 보존돼 있다.

고정 native API 검토:

- Tantivy0.21.1 IndexWriter::prepare_commit은 document channel을 교체하고 기존 worker를
  join한 뒤 worker를 다시 만든다. commit 시간에는 이 준비와 segment 게시가 함께 포함된다.
  이 동작이 존재한다는 사실만으로 스레드 재생성이 회귀 원인이라고 확정하지 않는다.
- IndexBuilder::single_segment_index_writer는 thread 없는 API지만 빈 디렉터리를 전제로 하고
  GC를 수행하지 않는다. finalize는 metadata를 단일 segment로 저장하므로 기존 다중 segment
  writer의 drop-in 대체물이 아니다. 검색 가시성/삭제/merge를 깨뜨릴 방식으로 적용하지 않는다.
- IndexWriter::add_segment는 숨김 공개 API이며 delete cursor를 붙여 segment updater에
  등록한다. 별도 파일/metadata 생명주기와 commit 조건을 검증하지 않고 직접 주입하지 않는다.
- 현재 engine은 pending_documents가 비어 있으면 append/commit을 건너뛴다.
  빈 refresh에서 commit 제거를 새 최적화로 제안할 근거는 없다.

다음은 기존 native commit diagnostic을 사용해 동일 segment/batch 작업량에서 prepare와
publish 비용을 구분하는 단계다. 새 엔진을 직접 구현하거나 내구성/가시성 조건을 완화하지 않는다.
실제 production 수정 전에는 snapshot/삭제/오류 복구 계약 시험을 정하고,수정 후에는
전체 engine/HTTP/non-plugin 반복 gate를 반드시 실행한다. 누적5% FAIL 및 수락0/40 유지다.

### 기존 native commit 진단 재사용 및 CPU 후속 검증

기존 C02 격리 진단의 source와 원본 해시가 기록과 일치함을 확인했다.
refresh_commit_diagnostic.rs SHA d33ecd3c8ec12661d0091dd5914fcaffe1aaa94f6a8218d7a41ca061ce002962,
refresh-01-direct/raw.jsonl SHA95e5193f99f1b2ab46d57c742dd8a2ec8de07627ae1f933d9a67690d89c0872c다.
기존 floor512/indexed+fast 활성 두 조건의 평균 prepare는1866.304/1819.500us,
publish127.005/147.742us,reload186.258/194.701us다. 기존 원시 기록을 새 후보 성능으로 쓰지 않는다.

보존된 refresh-direct(SHA535bdd0d3e37c68f0b77ea576b2704a40e1e07af86944ef5b7df894727d5030f)에
199Hz cpu-clock/DWARF8192 프로파일을 추가해 --notified-locks 전체16조건을 실행했다.
exit0,실행 전후 SHA 동일,모든 조건의2691개 문서 검증이 완료됐다.
검증은 ID/중복/누락,활성 fast값/indexed term count,이전 reader 보존 및 merge drain을 포함한다.
이번 floor512 활성 조건의 prepare 평균1923.337/1929.859us,publish149.795/144.592us다.
프로파일 오버헤드가 있으며 기존 raw 값과의 차이는 성능 회귀 판정이 아니다.

전체 프로세스 표본의 self 상위 항목은 merge IndexMerger::write7.32%,
bitpacked column 순회6.99%,postings serializer3.99%,column stats3.91%,
index worker postings subscribe3.33%와 column record3.00%다.
표본에는16조건/검증/merge drain이 모두 포함되므로 준비 구간만의 CPU 비중이 아니다.
숨겨진 worker 생성 비용이 없다는 증명도 아니지만 worker 재사용 구현을 우선할 증거는 부족하다.
현재 서버6086c31c 실행이 아닌 과거 격리 binary이며 native numeric/segment 작업 진단으로만 사용한다.
비활성 indexed/fast 조건은 분석 대조군이지 지원 기능을 끄는 성능 후보가 아니다.

production 변경 없음,수락0/40,전체 gate FAIL 유지다. 다음 최적화는 native segment
처리/merge의 동일 기능·동일 작업량 비교를 근거로 정하고,API의 삭제·snapshot·게시 계약을
보존해야 한다. 새로운 변경마다 전체 engine/HTTP/non-plugin 반복 성능 gate는 그대로 필수다.

증거 디렉터리: target/core-replacement-c06/native-text-metadata-commit-profile/.
perf.data SHA `71116917fcf4b4160bb3520816300422eb07145da99a67c78c7b54a69a94bddf`.
raw.jsonl SHA `2f88c0a145c8f2e19bce6f513d5b53c6849a3f1d7332b6f548dd3c5c41052c80`.

### Merge floor 격리 실험: production 변경 보류

refresh_commit_diagnostic 예제에 `--indexed-fast-only`와 양수 `--floor=N`을
추가했다. 기본 조건은 유지하며 지정 floor도 두 번 측정한다. 서버 코드는 변경하지 않았다.
예제 SHA `079b115e27435c5576720ca573b4cbc7542e107e119215374c3a5028912c1f10`,
격리 binary SHA `463aad5c58fc75166153e126d56752cdf04b8e4e1894f565a4016c063989bbac`.
증거 경로는 `target/core-replacement-c06/native-merge-floor-experiment/`다.

최초 lock 없는 빌드는 zstd 의존 버전 불일치로 exit101이었다. `build.log`와
`unpinned.lock`을 보존했다. 후보 동결 Cargo.lock을 복사한 offline 빌드는
2분02초,exit0이며 `pinned-build.log`에 보존했다. 전체 feature graph 동일성을
검증한 서버 빌드가 아니라 진단용 binary다.

최초 0-512.jsonl부터 5-512.jsonl까지 여섯 실행은 orchestration 오류로 겹쳤다.
이 파일들의 시간은 비교에서 제외한다. 모든 실행의 종료를 확인한 후
`serial-0-512.jsonl`부터 `serial-5-512.jsonl`까지 하나씩 종료를 기다려 재실행했다.
순서는512/1024/2048/2048/1024/512,각 exit0이다.

| floor | 조건 수 | 조건당 refresh 수 | add+prepare+publish+reload 평균 us |
| --- | ---: | ---: | ---: |
| 512 | 4 | 256 | 2310.920 |
| 1024 | 4 | 256 | 2356.118 |
| 2048 | 4 | 256 | 2582.692 |

모든12조건에서2691개 문서 검증이 완료됐다. 평균 개선 근거가 없으므로 floor를
올리는 production 변경은 하지 않는다. 작은 격리 실험이며 서버 전체 성능이나
tail latency의 인증으로 사용하지 않는다. 완료 패키지 추가도 없다.

직렬 원본 SHA-256 (파일명 순서):

| 파일 | SHA-256 |
| --- | --- |
| serial-0-512.jsonl | `8a1b9b3d95b2cc508444b84136ac951123909ba88cd7b0958d423f09093d24da` |
| serial-1-1024.jsonl | `ea57f6b5c323be1b162764c068ced798e8e7212186955038158ef7474a4c7339` |
| serial-2-2048.jsonl | `b15ffcc37a2acd48d80c72dd78932fe4380a1ba2cd72a05d5221ee18293b638a` |
| serial-3-2048.jsonl | `7c04ef0dcb14efd121e8eddc15139a93409ed25b5c02cb633deff876da32d254` |
| serial-4-1024.jsonl | `eda583aa92f944014ff5386becd5740b2ef9c41de68cb766481897478bb8ee72` |
| serial-5-512.jsonl | `cb26306d92e724b63f4094079872fdeadfd33ecf56f8b9826269760381c30415` |

### 잔여 termvectors 실패의 구현 경계 조사

6086c31c 전체 HTTP 원본의 search-native-array-positions-compat-report.json에서
실패135건을 다시 분리했다: positions80건,ranking55건이다. positions의 첫 scalar
응답은 참조가 alpha/beta 두 토큰과 field doc_count14를 반환하는 반면 후보는
alpha beta 단일 토큰과 doc_count1을 반환한다. 수치 반올림 문제가 아니다.

standalone_runtime.rs의 termvectors_fields_from_source는 문자열 전체를 한 term으로
만들고 term_freq/field_statistics를1로 고정한다. 배열은 as_str에서 빠진다.
기존 문서와 artificial 문서 모두 이 함수를 호출한다. 검색 postings의 정확성을
termvectors HTTP 지원 완료로 확대할 수 없다.

고정 vendor Tantivy의 InvertedIndexReader에는 terms/get_term_info/read_postings가
있고 SegmentPostings는 빈도와 위치를 제공한다. 따라서 native에 토큰/위치 접근이
없다고 가정하지 않는다. postings가 tokenizer의 start/end offset까지 저장한다고
가정해서도 안 된다. offset과 realtime 문서의 계약은 별도 확인이 필요하다.

후속 구현 단위 TV1 계획 (아직 미구현, 기존 C06 범위):

1. 참조 fixture를 이용해 stored/artificial, realtime 전후, routing, 삭제/갱신,
   field/term_statistics와 positions/offsets 옵션을 분리한다. 기존80실패를 보존한다.
2. 동일 mapping analyzer와 native tokenizer로 대상 문서의 term 목록을 구하고,
   조회 가능한 snapshot의 native postings/term dictionary에서 빈도/위치/통계를
   제공하는 engine 경계를 설계한다. 전체 source 코퍼스 재검색은 구현하지 않는다.
   미refresh 문서와 shard 통계, 삭제된 postings의 의미는 참조로 먼저 고정한다.
3. offset의 저장/재분석 경계를 조사한다. 대상 한 문서의 native 재분석이 필요한 경우
   배열 gap, UTF-16 offset, analyzer override를 시험한다. byte 길이로 임의 대체하거나
   통계를 상수로 반환하지 않는다. 필요한 계약을 지원할 수 없으면 미완료로 남긴다.
4. native 단위 시험과 REST fixture를 추가하고 기존 mtermvectors 경로도 검증한다.
   전체 engine 및 영향받는 node 테스트, 확장 전체 HTTP를 실행한다.
5. 구현 단위 완료 전 전체 non-plugin6회/12토폴로지 벤치마크를 반드시 실행한다.
   고정 v0.6.0 대비 누적 처리량95% 이상,각 mean/p95/p99 105% 이하를 별도 판정한다.
   동일 실제 설정/분리 빌드/실행 파일 identity를 보존하고 기존 FAIL을 면제하지 않는다.
   초과 시 최적화 후 전체 재실행하며 해결 불가능한 단위는 계획의 제외 원칙을 따른다.

이번 조사는 production 수정이나 새 전체 gate 통과가 아니다. 후보6086c31c,
HTTP2351통과250실패,수락0/40,성능 FAIL 및 릴리즈 보류를 유지한다.

### TV1 native 필드 통계 회귀 시험

native_array_positions_match_stored_reference_across_refreshes에 필드 통계 검증을
추가했다. 각 gap 인덱스의 실제 segment term dictionary/postings에서 문서 집합,
doc frequency 합계,term frequency 합계를 구해 저장된 참조의14/30/32와 비교한다.
기존80문서 위치와55검색 membership 검증도 유지한다. 전체 postings 순회는 시험용
독립 검증이며 production 요청 알고리즘으로 옮기지 않는다. 삭제 없는 fixture이므로
삭제 이후 통계나 realtime HTTP 계약을 검증한 것으로 해석하지 않는다.

시험 파일 SHA `3b1d766f49455f3a6a38f999b1186865128291dd990631248ca4601c0210be66`.
기본 debug 빌드는 디스크 사용을 줄이기 위해 중단(exit143)했고,종료 확인 후
아래 명령으로 재빌드했다. 전체 engine955건(935+7+4+9),실패/ignore/filter0,
doc-test0,exit0이다. 빌드2분19초,각 시험15.94/13.98/2.57/0.28초다.

```sh
CARGO_PROFILE_DEV_DEBUG=0 CARGO_PROFILE_TEST_DEBUG=0 CARGO_INCREMENTAL=0 CARGO_BUILD_JOBS=2 cargo +nightly test -p os-engine-tantivy --offline
```

테스트 전용 변경이며 서버6086c31c는 그대로다. 새 HTTP/전체 성능 벤치마크를
실행한 것으로 계산하지 않고 TV1은 미완료다. native 데이터 접근 가능성을 확인했으며
offset/realtime/shard 통계 계약 및 실제 HTTP 연결은 후속 작업으로 남는다.

### TV1 native 토큰 offset 실측 비교

기존6086c31c HTTP 실행의 OpenSearch raw 응답에서 기본 gap16문서의 terms를
추출해 `tools/fixtures/search-native-termvectors-offset-reference.json`에 보존했다.
새 참조 실행을 주장하지 않으며 ASCII/기본 gap 범위다. 원본 보고서 SHA는
`38b86cb0caf0f9cb9a5146c456d54d203d2717f322a63d2c7815f2ac37ef1a9e`,
추출 fixture SHA는 `74d3e0283368d7ec65e228890e909ebc887d12c61b9f3b7db3f9b52f06681195`다.

`native_indexing_tokens_preserve_reference_termvector_offsets`는 기존
add_positioned_text_values가 생성한 native PreTokenizedString 또는 scalar의 native
tokenizer 결과를 참조와 직접 비교한다. 토큰 문자열/빈도/위치/start/end offset 모두
일치한다. 빈 문자열/null/중첩 배열/숫자/불리언/반복어를 포함한다. 새 tokenizer나
source 코퍼스 순회를 구현하지 않았다. Unicode 또는 다른 analyzer의 일반 호환성
증거가 아니며 HTTP250실패 수를 줄인 것으로 계산하지 않는다.

전체 engine 재실행956건(936+7+4+9),실패/ignore/filter0,doc-test0,exit0.
시험시간15.70/14.10/2.60/0.26초다. 명령은 위 compact debug 환경에
`cargo +nightly test -p os-engine-tantivy --offline --quiet`를 사용했다.
시험 파일 SHA `00ecf68393fca0a70ae422cd39daeee5968400b6b0ea3a2f120b7ff5a2a42377`.

로컬 OpenSearch HEAD가 실제 참조 build f991609d190dfd91c8a09902053a7bbfe0c27b3e와
일치하고 다음 두 Java 파일의 worktree 변경이 없음을 확인했다.

- TermVectorsService.java SHA `586a5c0fd034b5bc5a769d477a8d5ddd14c7d20de3ff5cca76385649b49cd8c5`:
  getTermVectors는 realtime/version 조건으로 문서를 얻고,가능하면 해당 get reader를
  필드 통계에 사용한다. 저장 term vector 조회와 selectedFields/analyzer override에
  따른 생성 경로를 구분한다. generateTermVectors는 대상 문서를 MemoryIndex와
  native analyzer로 분석한다. 전체 source 코퍼스 재검색 경로가 아니다.
- TermVectorsWriter.java SHA `bd874ed5de209bcd79350e4cceb0a506b6d90c25627d37ea69938462bd4b689e`:
  positions/offsets/payloads는 요청 flag와 실제 fieldTermVector capability 양쪽으로
  결정한다. field statistics는 top-level Terms의 sumTotalTermFreq/sumDocFreq/docCount,
  term statistics는 해당 top-level term lookup에서 구한다. 필드가 없을 때는
  EMPTY_TERMS를 사용하며 문서 통계로 임의 대체하지 않는다.

따라서 HTTP 연결은 문서 토큰 생성과 shard reader 통계 획득을 분리해야 한다.
선택하지 않은 모든 source 문자열을 무조건 노출하거나 offset flag만 보고 없는
저장 정보를 존재하는 것처럼 반환하지 않는다. 아직 production 변경/새 전체 성능
측정은 없으며 TV1 미완료,수락0/40,6086c31c 성능 FAIL을 유지한다.

### TV1 Unicode 및 realtime HTTP 계약 실측

`search-native-termvectors-contract.json`에 stored/generated 두 mapping의24조건을
추가했다. Unicode scalar/배열,fields 생략,positions/offsets/statistics 비활성,
keyword analyzer override,미refresh 문서의 realtime true/false,refresh 후 기존 문서
통계를 포함한다. routing/artificial/delete 계약은 이번24건에 포함하지 않는다.

새 `term_vectors` extractor는 실행 시간 took의 숫자 동일성 대신 비음수 정수
유효성을 비교하고 나머지 응답은 보존한다. 누락/음수/bool/float/NaN/Infinity는
유효한 took와 같게 처리하지 않는다. 기존 source_body와 과거 fixture/보고서는
그대로이며 기존80실패를 통과로 재분류하지 않았다. 도구 전체17시험 통과다.

실제6086c31c와 OpenSearch3.7.0-SNAPSHOT/build f991609d190dfd91c8a09902053a7bbfe0c27b3e를
실행했다. 총1524건 중 기존1500통과,새24실패,skip/setup실패0,parent exit1.
binary_unchanged/fixtures_unchanged true. 기존2601건 전체 재실행은 아니므로
과거250실패와 합쳐 새 전체 gate 결과로 표시하지 않는다.

확인된 계약:

- 미refresh 새 문서에 realtime=false: 참조 found=false/version0,후보 found=true.
  이는 점수 오차나 took 문제가 아니라 가시성 결함이다.
- realtime=true: 참조가 새 문서를 반환하며 이번 순서에서는 pending 두 문서를
  포함한 field doc_count8,sum_doc_freq18,sum_ttf18이었다. 검색용 기존 snapshot6/14/14를
  그대로 붙이는 구현으로는 이 요청과 일치하지 않는다.
- fields 생략: stored mapping은 저장 body vector만 반환하고,generated mapping은
  빈 term_vectors를 반환했다. 임의 source 문자열 전부를 노출하면 안 된다.
- flags 비활성: tokens/field_statistics가 빠지며 term_freq는 유지된다.
  keyword override의 문서 term은 alpha beta 하나지만 통계는 shard6/14/14다.
- Unicode offset은 UTF-16 단위다. accent 입력의 첫 term 끝은4,beta 시작5이고,
  astral 입력은 별도 supplementary 문자 토큰 위치1/offset6..8,beta 위치2/offset9..13이다.
  결합 문자는 앞 term에 포함된다. 기존 Tantivy SimpleTokenizer의 is_alphanumeric
  경계는 이 supplementary 문자/결합 문자 처리를 그대로 제공하지 않는다.
  byte offset 변환만으로 전체 analyzer 호환성이 해결된다고 주장하지 않는다.

후속은 TV1의 동일 native 문서 분석/가시성/통계 경계를 구현하는 것이다.
Unicode analyzer는 재사용 가능한 native 구현을 먼저 확인하며 source 코퍼스 재검색이나
수작업 문자 규칙 확장으로 우회하지 않는다. TV1 완료 전 전체 engine/node/확장 HTTP와
고정 v0.6.0 누적5% non-plugin 전체 반복 성능 gate를 실행한다. 아직 미완료다.

증거: `target/core-replacement-c06/native-termvectors-contract-live/`.

| 파일 | SHA-256 |
| --- | --- |
| execution.json | `7dee5e498fa631bbbce01e097127a3853016fd8bc47b3cc6ebe6654bbac8c540` |
| search-native-termvectors-contract-report.json | `9c457cf0d79dd47d95d445912d47b15ce3f61bb9a5a67da49d8b37ed7bfc30e0` |
| tools/fixtures/search-native-termvectors-contract.json | `09935b4ef2c73e7ee22cfb9dcb680d0ea0d060a641ce2ba314254f30378e4cb9` |
| tools/search_compat.py | `0465dc96155f74c5cceab7bc5d8545784ba0fa0a155d0018aefd5270ba2cfa6d` |
| tools/test_search_compat.py | `b0e97afe34d9f0f6dd74555fe51455e593b22b9f741e1ce53cb02e848c50d5df` |

실행 전 디스크 안전장치를 피하지 않도록 자체 debug cache893.1MiB와 격리
merge 실험 release cache500.3MiB를 cargo clean으로 정리했다. 서버 후보/기준선과
원본 증거는 유지했다. merge 진단 binary는 같은 디렉터리의 artifacts/refresh-experiment에
복사 보존했다. 디스크 여유5.2GiB로 실측을 시작했고 flood-stage 설정은 변경하지 않았다.

### TV1 공개 snapshot 문서 조회 API 구현

node의 기존 GET은 현재 documents_state의 refreshed bool을 필터링한다.
이 방식만 termvectors에 복사하면 미refresh overwrite/delete 전에 공개된 문서를
복원할 수 없다. 엔진에는 이미 shard별 refreshed_documents_by_id가 있으므로
`TantivyEngine::get_refreshed_document_with_routing`을 추가했다.
기존 routing 계산으로 단일 shard를 선택하고 공개 문서 map에서 ID를 조회한다.
반환 source/metadata는 소유한 값이며 새 코퍼스 복사/추가 snapshot/전체 source
순회를 만들지 않는다. 기존 get_document 및 쓰기/refresh 경로는 변경하지 않았다.

회귀 시험2건을 추가했다:

- 단일/3샤드에서 신규 문서가 refresh 전에는 없고,metadata version7/42와 primary_term3을
  replay한 뒤에도 refresh 전 이전 source/metadata가 유지된다. pending delete도
  refresh까지 이전 문서를 보존하고,그 후에는 없어지며 이미 반환한 응답은 유지된다.
- 서로 다른3개 routing shard에 같은 ID를 저장해 정확한 shard의 문서를 조회한다.
  routing 생략은 ID hash shard로 해석하고 다른 shard로 fallback하지 않는다.
  한 shard 삭제 후 나머지 두 문서는 유지되며 missing index 오류도 검사한다.

전체 engine958건(938+7+4+9),실패/ignore/filter0,doc-test0,exit0.
시험시간15.46/14.18/2.57/0.31초다. compact debug 환경의
`cargo +nightly test -p os-engine-tantivy --offline --quiet`를 실행했다.

| 파일 | SHA-256 |
| --- | --- |
| crates/os-engine-tantivy/src/lib.rs | `2b68327ee3f1f8be2e6e485c1c717494c17eaba618183dd58b62d3fa62dab0c0` |
| crates/os-engine-tantivy/src/refreshed_document_tests.rs | `28179cc79c7bf2a4f20c67d94b7104c2c9689493a6383e506079e7c6585fafc6` |

이 단계는 TV1 구현 도중이며 당시 HTTP에는 미연결이었다. node의 일반/지연/replay/
외부 version 쓰기와 engine metadata의 대응,alias/routing,realtime true 통계 검증이 남았다.
refreshed bool 추가만으로 완료 처리하지 않는다. 전체 engine/node/확장 HTTP/전체
non-plugin 반복 성능 gate를 완료 전에 실행해야 한다. 새 release binary는 미생성이고,
6086c31c 성능을 이 변경의 실측값으로 쓰지 않는다. 전체0/40,릴리즈 보류를 유지한다.

Unicode native 후보 조사에서는 [ICU4X WordSegmenter 공식 API](https://docs.rs/icu/latest/icu/segmenter/struct.WordSegmenter.html)의
UAX29 분할 및 word type API를 확인했다. 경계에는 비단어 구간도 포함된다.
Lucene의 token 종류/Unicode 버전/최대 길이와 동일한지는 미검증이며,UAX29 대응만으로
그대로 교체 가능한 구현으로 취급하지 않는다. 의존성 추가나 수제 tokenizer 변경은 없다.

### TV1 realtime=false REST 연결 및 PUT 메타데이터 전달

단일 termvectors와 mtermvectors의 realtime=false를 공개 snapshot 조회 API에
연결했다. 신규 문서는 refresh 전 보이지 않고,덮어쓰기/삭제는 refresh 전까지
기존 공개 source/version을 반환한다. 단일 요청은 engine 오류를 REST 오류로,
다중 요청은 해당 문서 오류로 반환한다. mtermvectors의 realtime query bool도 검증한다.
공개 조회 응답의 미발견 version0와 실제 경과시간 took를 추가했다.
문서별 토큰/필드 통계 생성은 아직 기존 함수이며 TV1 전체 구현 완료가 아니다.

연결 전 PUT의 node 메타데이터와 native 독립 version 증가가 불일치할 수 있음을
확인했다. 일반 PUT의 비지연 native 쓰기를 기존 replay API로 바꿔 할당된
version/seq_no/primary_term을 전달한다. 지연 replay 경로는 이미 메타데이터를 전달한다.
bulk/create/update/update-by-query 경로까지 이 변경으로 수정됐다고 주장하지 않는다.
특히 다른 native 쓰기 경로와 섞일 때 seq_no/version 차이가 남는지 다음에 검증해야 한다.
이 확인 없이 candidate를 릴리즈하거나 구현 단위를 완료 처리하지 않는다.

같은 참조 checkout의 VersionType.EXTERNAL.validateVersionForWrites는 version>=0을
허용한다. replay에서0을 거부하던 조건을 제거하고,PUT의 음수 외부 버전은 기존
owned validation-error helper로 쓰기 전에 거부한다. engine의 conditional-write
외부 버전0 검증은 별도 경로로 남아 있으며 모든 외부 버전 API가 수정됐다는 뜻은 아니다.

새 node 회귀 시험은3샤드/routing을 지정해 버전0/7/42 PUT을 수행한다. 매 단계의
refresh 전후에 native snapshot 및 단일/다중 REST handler의 found/version/source와
took 타입을 검사한다. pending delete 전후와 음수 버전 거부도 포함한다.
현재 live HTTP24실패를 새 바이너리로 재실행한 시험이 아니라 in-process REST 시험이다.

- 최종 node 라이브러리665건 통과,실패/ignore/filter0,5.70초,exit0.
- 최종 engine958건(938+7+4+9) 통과,실패/ignore/filter0,doc-test0,exit0.
  시험시간15.62/15.72/2.49/0.30초다.
- 중간 빌드는 borrowed/owned validation helper 인수 타입 불일치로 exit101이었다.
  기존 owned helper로 수정한 뒤 위 전체 시험을 재실행했다.

모두 compact debug 환경(CARGO_PROFILE_DEV_DEBUG=0,CARGO_PROFILE_TEST_DEBUG=0,
CARGO_INCREMENTAL=0,CARGO_BUILD_JOBS=2)에서 nightly/offline으로 실행했다.
명령은 각각 cargo test -p os-node --lib --quiet 및 cargo test -p os-engine-tantivy --quiet다.

| 파일 | SHA-256 |
| --- | --- |
| crates/os-node/src/standalone_runtime.rs | `dad0dc7163b140ae42918d919557892b5967d6bd5515ce209748012465e2f2a5` |
| crates/os-engine-tantivy/src/lib.rs | `66b2845474727102734d9e7216ed9d62fda9c6a8a766549e586a51c7a7f608f1` |
| crates/os-engine-tantivy/src/refreshed_document_tests.rs | `c473f85d583bfc81273b7b54bb7471353f7998c35b8b9f990a64ede8e3a422f6` |

TV1은 여전히 구현 중이다. 남은 쓰기 경로/Unicode/analyzer/통계 계약을 처리하고
daemon 및 새 후보의 확장 전체 HTTP,전체 non-plugin6회/12토폴로지 성능 gate를
실행해야 한다. 고정 v0.6.0 대비 누적5% 조건은 유지하고,미실행 검증을 기존6086c31c
보고서로 대체하지 않는다. 수락0/40,새 release binary 미생성,릴리즈 보류다.

### TV1 혼합 쓰기 메타데이터 및 순서 역전 replay

bulk/index/create/update/upsert,단일 update 및 작업 완료 문서가 사용하는 공통
native 동기화 함수에 StoredDocument를 전달하도록 변경했다. 기존 native replay API에
node의 version/seq_no/primary_term/routing을 전달하며,지연 쓰기의 불필요한 source
복사를 제거했다. 단일 create도 할당 메타데이터를 replay한다. 음수 bulk 외부 버전은
문서 변경 전에 오류를 반환한다. 전체 bulk validation 계약의 참조 인증은 아니다.

update-by-query의 script 경로는 node version/seq_no를 함께 증가시키고 native에도
동일 메타데이터를 전달한다. version overflow로 중단할 때 이미 처리한 문서들의
native 동기화와 저장은 수행한다. update-by-query 전체 script/noop/refresh/오류 계약을
이번 변경으로 완료했다고 주장하지 않는다.

새 in-process 혼합 시험은 PUT external7 -> bulk external42 -> bulk update43 ->
단일 update44 -> update-by-query45 -> 일반 PUT46을 실행한다. 각 refresh 후
GET과 native 공개 snapshot의 version/seq_no/source를 비교하고,음수 bulk 외부 버전의
쓰기 거부도 확인한다.

첫 전체 node 시험에서 concurrent_task_completions_initialize_one_searchable_tasks_index가
8문서 중5문서만 검색되는 회귀를 발견했다(665통과1실패). shard의 append-only flag만
바꾼 중간 시도도8중7문서로 실패했다. 원인은 할당 sequence와 native 도착 순서의 차이로,
공개 watermark보다 늦게 들어온 낮은 sequence 문서를 증분 refresh가 놓치는 것이다.

수정은 다음과 같다:

- replay sequence가 이전 next_seq_no보다 작으면 비증분 변경으로 기록한다.
- index/shard의 완료 판정에서 sequence뿐 아니라 append-only 상태를 확인한다.
- 같은 watermark의 full artifact도 게시한다. 이미 더 최신 watermark는 덮어쓰지 않는다.
- 같은 watermark에서 내용이 달라지면 BM25 cache를 교체한다. 기존 cache 소유자가
  보유한 통계를 지우지는 않는다.

추가 engine 시험은 sequence9를 먼저 refresh한 뒤 다른 ID의 sequence3을 replay한다.
단일/3샤드 모두 두 문서가 유지되고,새 통계 doc_count2와 이전 cache의1이 보존된다.
시험의 borrowed index 수명 오류로 중간 compile exit101이 있었으며,실제 cache Arc를
보존하도록 수정한 뒤 전체 시험을 다시 실행했다.

- 최종 node 라이브러리666통과,실패/ignore/filter0,5.98초,exit0.
- 최종 engine959통과(939+7+4+9),실패/ignore/filter0,doc-test0,exit0.
  시험시간15.64/14.78/2.55/0.30초다.
- compact debug 환경에서 nightly/offline으로 전체 node --lib 및 전체 engine 시험을 실행했다.

| 파일 | SHA-256 |
| --- | --- |
| crates/os-node/src/standalone_runtime.rs | `a3cf603bb8717b2e6526df29ac728ce73d4b2cb28d7b01d25ea79519b9bd70d2` |
| crates/os-engine-tantivy/src/lib.rs | `ad9801773c956d70f5153899fa5edcad6c1ce4fba4fabbcf2d3aa80d3617bf60` |
| crates/os-engine-tantivy/src/refreshed_document_tests.rs | `91dec330062962277f859d81b42c46ba2d6eb728e9dacd10fe459454f447d834` |

다음 필수 확인은 늦은 replay의 저장/복구다. persist_shard_state 및
persist_index_shard_state는 이전 최대 sequence보다 큰 operation만 추가하는 경로가
있다. 현재 메모리 검색 성공을 디스크 복구 성공으로 확대하면 안 된다. 이전 저장9 이후
늦은3을 저장하고 재시작하는 양쪽 persistence 경로를 시험하고 필요한 조치를 마친다.
그 후 새 독립 release 후보의 확장 전체 HTTP와 전체 non-plugin6회/12토폴로지 성능
gate를 실행한다. 늦은 replay의 full rebuild 비용을 진단만으로 면제하지 않는다.
최초 v0.6.0 누적5% 조건을 유지하며 초과 시 최적화와 전체 재실행이 필요하다.

TV1 미완료,수락0/40,새 release binary 및 새 성능 측정 없음,릴리즈 보류다.

### TV1 늦은 replay 저장/복구 실패 재현

refreshed_document_tests.rs에 양쪽 persistence API의 신규 문서 및 기존 문서 갱신
복구 시험4개를 추가했다. sequence9를 저장한 뒤 sequence3을 replay하고 다시 저장한
후 별도 엔진에서 recover_index_from_manifest 및 refresh를 실행한다. 갱신 시험은
처음 저장한 same 문서의 sequence1을 sequence3으로 바꾸므로 문서 수 증가에만
의존하는 수정도 검출한다. 임시 디렉터리는 복구 결과 assertion 전에 제거한다.

실행: compact debug 환경(CARGO_PROFILE_DEV_DEBUG=0, CARGO_PROFILE_TEST_DEBUG=0,
CARGO_INCREMENTAL=0, CARGO_BUILD_JOBS=2)에서
`cargo +nightly test -p os-engine-tantivy --lib late_replay_ --offline --quiet`.
결과는1통과4실패,ignore0,938filtered,0.13초,exit101이다. 기존 refresh 시험만 통과했다.
두 API 모두 신규 문서는 복구 후 없고,갱신 문서는 sequence3 대신 이전 sequence1로
복구된다. 이는 실제 저장/복구 실패이며 아직 production 수정은 하지 않았다.
앞 절의 engine959통과를 현재 추가된 회귀 시험까지 통과한 것으로 해석하면 안 된다.

후속 수정은 저장 이후의 변경을 최대 sequence와 별도로 추적해야 한다. 저장 경로별
checkpoint,동시 쓰기 중 snapshot/manifest 일관성,저장 실패 후 재시도와 index 세대도
검증한다. 단순 문서 수 비교,refresh 완료 flag 재사용,저장 후 무조건 dirty flag
초기화는 늦은 갱신이나 동시 쓰기를 놓칠 수 있으므로 완료 근거가 아니다.
전체 corpus를 매번 재저장하는 방식의 성능 우회는 승인하지 않는다.
이 구현 단위 완료 전 전체 engine/node,확장 HTTP 및 전체 non-plugin6회/12토폴로지
벤치마크를 다시 실행하고,최초 v0.6.0 대비 처리량95% 이상 및 각 시나리오
mean/p95/p99 지연105% 이하의 누적 조건을 적용한다. 실패 시험을 skip하지 않는다.

현재 저장/복구 데이터 유실4건은 릴리즈 차단 항목이다. TV1 미완료,수락0/40이며
새 release 후보/성능 측정/태그/발행은 없다.

### TV1 경로별 저장 checkpoint 수정

앞 절의4개 저장/복구 실패를 수정했다. 두 persistence API는 공통
persist_document_state를 사용한다. 기존 index 세대별 persistence lock 안에서
canonical 저장 경로별 checkpoint를 유지하며,index 전체/단일 shard 범위를 구분한다.
checkpoint는 저장한 최대 sequence와 shard별 persistence rewrite generation을
기록한다. manifest와 문서 operation은 동일한 store 읽기 잠금에서 확보한다.

- 늦은 sequence 삽입/갱신 및 삭제는 rewrite generation을 증가시킨다.
  다른 shard의 높은 sequence 때문에 인덱스 전체 checkpoint 아래로 들어오는 replay도
  해당 shard의 generation을 증가시킨다. refresh generation과 별도이며 refresh가
  완료돼도 저장 변경 정보는 사라지지 않는다.
- 경로의 checkpoint가 없거나 세대/범위/최대 sequence가 맞지 않으면 현재 상태를
  다시 저장한다. 이후 정상 순서의 쓰기는 기존 sequence 기반 증분 append를 사용한다.
  매 요청 전체 corpus 저장이나 새로운 검색 source scan을 추가하지 않았다.
  재시작 후 첫 저장에는 메모리 checkpoint가 없어 전체 저장이 필요하다.
- 파일 I/O 전에 이전 checkpoint를 제거하고 operation 및 manifest 저장 모두 성공한
  경우에만 캡처한 generation을 기록한다. 따라서 실패 후 재시도는 부분 append를
  신뢰하지 않는다. I/O 도중 들어온 변경의 generation을 저장 완료 표시로 덮지 않는다.
- 공개 ShardManifest 파일 포맷은 변경하지 않았다. 기존 atomic rename/sync 동작을
  사용하며,이번 시험을 power-loss/crash 원자성 인증으로 확대하지 않는다.

최초 수정본의 focused late_replay_ 시험은5통과였다. 이후4개 복구 시험을 확장해
각각 두 경로의 독립 저장,정상 갱신 후 append 복귀(로그3행),manifest 임시 경로에
디렉터리를 만들어 저장 실패를 주입한 뒤 재시도(로그2행),삭제 후 양쪽 경로 복구를
확인했다. 별도 cross-shard 시험은 전체 index 저장 로그의 replay 결과에서 낮은
sequence 문서와 routing 보존을 확인한다. 이는 legacy 전체 index 복구의 다중 shard
배치 계약 전체를 인증하는 시험은 아니다.

최종 전체 engine 시험:
`cargo +nightly test -p os-engine-tantivy --offline --quiet`
(기존 compact debug/nightly/offline 환경).
964통과(944+7+4+9),실패/ignore/filter0,doc-test0,exit0.
각 시험시간16.39/15.31/2.66/0.31초다.
이어 같은 환경에서 `cargo +nightly test -p os-node --lib --offline --quiet`를 실행해
666통과,실패/ignore/filter0,5.81초,exit0을 확인했다.

| 파일 | SHA-256 |
| --- | --- |
| crates/os-engine-tantivy/src/lib.rs | `ac8923da9cd1a5845c147c758437fe14b2870dd47a1fed841c33496f22197fa1` |
| crates/os-engine-tantivy/src/refreshed_document_tests.rs | `9641c100dab8a4d2b0bffa3bcdedc7691a77b031bc3b860a4352fba881d1f7c7` |

동시 저장/쓰기의 결정적 I/O 경계 시험과 crash 내구성 검증은 별도 남은 안전성 항목이다.
새 독립 후보 전체 HTTP 및 전체 non-plugin6회/12토폴로지 benchmark도 아직 미실행이다.
이 단위는 완료로 표시하지 않으며 고정 v0.6.0 누적5% 게이트를 면제하지 않는다.
TV1 미완료,수락0/40,릴리즈 보류다.

### TV1 저장 snapshot 이후 동시 쓰기 검증

persist_document_state_after_snapshot의 내부 콜백으로 manifest/operation 캡처 후,
파일 I/O 전에 다른 스레드의 쓰기를 끼워 넣었다. 실제 호출 경로는 빈 콜백을 사용한다.
두 API 각각 insert/replace/delete를 실행하는2개 시험(총6개 interleaving)을 추가했다.
첫 저장 복구가 캡처한 이전 문서와 정확히 같고,다음 저장 복구가 늦은 sequence3 또는
삭제를 반영하는지 확인했다. 쓰기 스레드 join은 캡처 이후 store 잠금 해제도 검증한다.
이는 임의 시점의 전원 손실/프로세스 강제 종료나 모든 동시성 순서에 대한 인증은 아니다.

전체 engine 명령은 앞 절과 같으며966통과(946+7+4+9),실패/ignore/filter0,
doc-test0,exit0이다. 시험시간16.26/15.33/2.65/0.31초다.
같은 compact debug 환경의 전체 node --lib 재실행도666통과,실패/ignore/filter0,
5.71초,exit0이다. 테스트 프로세스는 모두 종료했다.

| 파일 | SHA-256 |
| --- | --- |
| crates/os-engine-tantivy/src/lib.rs | `92c24f7769632f67f28a1d0a038f876aee319a2953f5ee9027e7b8ef186beccf` |
| crates/os-engine-tantivy/src/refreshed_document_tests.rs | `6030a03b75438bdc9ca98180e93d0f1bdafd317edb05e86c0a564006504050b9` |

독립 release 후보,확장 전체 HTTP 및 전체 non-plugin6회/12토폴로지 벤치마크는
여전히 남아 있다. v0.6.0 고정 누적5% 게이트 통과 전 단위 완료/릴리즈하지 않는다.
디스크 여유 약4GB를 확인했다. 기존 진단 실행 파일은 cache로 오인해 삭제하지 않았으며,
OpenSearch 실행 전 안전한 공간 확보가 필요하다. 기존 baseline/후보/증거는 보존했다.

### TV1 새 release 후보 및 전체 HTTP 검증

현재 작업 트리를 native-replay-persistence-candidate/source에 복사하고 모든 파일의
source.sha256을 기록했다. 과거 후보의 tantivy-fst 패치를 가져오지 않고 현재
Cargo.toml/Cargo.lock/vendor를 사용했다. 최초 명령은 standalone-runtime feature 누락으로
즉시 exit101이며 missing-feature-build.log에 보존했다. 수정한 명령은
`cargo +nightly build -p os-node --bin steelsearch --features standalone-runtime --release --locked --offline`
이고 CARGO_BUILD_JOBS=2,별도 CARGO_TARGET_DIR를 사용했다. 7분52초에 exit0이며,
빌드 및 전체 HTTP 이후 source.sha256 전체 검증이 통과했다.

경로 기준: target/core-replacement-c06/native-replay-persistence-candidate/.

| 증거 | SHA-256 |
| --- | --- |
| artifacts/steelsearch | `3a3c4023d1aeafa5bd8a824c045126752f1b7aef44e7f4d8f049db643c6ca766` |
| source.sha256 | `4a1dc626322d5b1e3e1d08fb452f7fe96291a14640c8e10530393331eca0bca4` |
| candidate-build.log | `a3960236765fe0f225d8ed7a529f0f4d0d78a84118354b7757ede03d7d2842d9` |

OpenSearch 개발 실행 스크립트의 기존 disk.threshold_enabled=false 옵션을 발견해
제거했다. bash -n을 통과했으며 실행 스크립트 SHA는
`0ebd0b8fb201aadc552b946b58cd124c31487a66cde2f834009cf559b9a1044e`다.
첫 HTTP 실행(native-replay-persistence-release-live)은 여유5GB 상태에서 실제
DiskThresholdMonitor의90% high watermark에 의해 create-index block이 발생했다.
그 이후 결과는 제품 회귀 판정에 사용하지 않는다. 원본 실행 증거는 보존했다:
execution.json SHA `fdd8f8f2fd28573237fc18324b30b316f4e5ef1cffe42110a9a3439e7ee3f2fb`.

공간 확보 후 별도 native-replay-persistence-release-live-safe에서37 fixture/2625건을
재실행했다.2353통과272실패,skip0,setup실패0,부모exit1이다. count probe,실행 파일
불변,fixture 불변이 모두 통과했다. 참조는3.7.0-SNAPSHOT,
f991609d190dfd91c8a09902053a7bbfe0c27b3e,Lucene10.4.0이다.
execution.json SHA는 `7c1cb259e46e62602f1f91f97612572305125daaeed1bc69dcdba039d423ae4f`.
filtered cluster-settings 조회는 빈 객체를 반환했으므로 이것만으로 설정값 전체를
검증했다고 주장하지 않는다. 첫 실행의 실제 차단 로그와 스크립트 변경을 함께 보존한다.

- 기존36 fixture 해시는 모두 같고,fixture+case name으로 비교한 기존2601건은
  상태 변경0/누락0이다.2351통과250실패를 유지한다.
- 새 termvectors24건 중 stored/generated의 realtime-false2건이 통과했다.
  나머지22건은 실패한다. 기존 별도24건 전부 실패한 후보 대비2건 개선이다.
- before-cases.json/after-cases.json에 케이스 식별자와 상태를 보존했다.
  raw HTTP 응답 및 setup 결과는 각 *-report.json에 있다.

공간 확보 내역: root dev 산출물1.2GiB와 새 후보 빌드 캐시683.7MiB를 Cargo로
정리했다. root release/deps 및 c05/fst-server-candidate/build의 debug/release/deps에서
중간 .rlib/.rmeta/.o 캐시3.85GiB를 정리했다. 실행 파일/소스/보고서는 삭제하지 않았다.
추가로 아래 root 소유 perf.data를 gzip -1 -k로 압축하고,압축 해제 스트림의 SHA가
원본과 일치함을 확인한 뒤 비압축 사본을 제거했다. 일반 사용자 읽기는 권한 오류였고,
sudo -n으로 읽기/압축/검증했다. 복구하려면 동일 경로 perf.data.gz를 압축 해제한다.

| 진단 경로 (target/core-replacement-c05/ 아래) | 원본 및 압축 해제 SHA-256 |
| --- | --- |
| typed-page-mixed-futex-all/perf.data.gz | `c32b0e1ce60fd978c8ccf381ee3b68d6329d88c882e63a70b3941dcc05666756` |
| typed-page-mixed-futex-sampled/perf.data.gz | `1f3e28f583a96a5042a840e7ffd65e0d809c6dcf979094d4a99edda2ef578fa5` |

여유 공간은 약12GB다. 고정 v0.6.0 db244133,기존6086c31c 실행 파일과 published
current.json d2fdabfa의 SHA를 다시 확인해 불변임을 검증했다.

다음 필수 작업: 성능 matrix의 clear_opensearch_cluster_blocks가 여전히 디스크
임계값 검사 및 create-index block을 해제하므로,이 안전장치 우회를 제거하고 검증해야
한다. 기본 low watermark에서3노드 replica 할당이 가능한 충분한 공간도 확보한다.
그 후3a3c4023 후보의 전체 non-plugin6회/12토폴로지 게이트를 실행한다.
현재 후보의 성능은 미측정이다. v0.6.0 누적5% 기준은 유지하며 TV1/전체40단위는
미완료,수락0/40,릴리즈 보류다. 이 기록은 태그/발행 승인이 아니다.

### 2026-09-11 보호 설정 유지 및 전체 성능 FAIL

성능 matrix의 clear_opensearch_cluster_blocks 및 호출을 제거했다.
require_opensearch_safety는 GET만 사용해 cluster defaults/persistent/transient,
node settings 및 cluster/index blocks를 전후 기록한다. flat/nested 설정과 우선순위를
처리하며 디스크 검사 비활성화/미확인,노드 설정 없음,활성 차단에서 실패한다.
전후 증거는 각 토폴로지 opensearch-safety-before/after.json에 남는다.
관련 failure diagnostics/core performance gate/runtime evidence unittest28건이 통과했다.
matrix SHA `73b417728bb8e20e69336ed0da06489cc3f88a0cc482c405cade60f73b5155d8`,
test_benchmark_failure_diagnostics.py SHA
`ec69bde99fa88291d8b366ab503667a4891cfb10b2dd1427d9632827e7c79bdc`다.

고정 OpenSearch2.19 이미지에서 단일/3노드 사전 안전 확인과3샤드/replica0 또는1
할당을 실행했다. 양쪽 health green 및 전후 보호 검증이 통과했고 프로세스를 종료했다.
증거는 target/core-replacement-c06/pinned-opensearch-safety/에 있다.
사용자 중단 후 기존 세션31714를 다시 조회해 exit0을 확인했으며 재시작하지 않았다.

공간 확보를 위해 재생성 가능한 중간 Rust 캐시0.57GiB를 추가 정리했다.
c06의 *-debug/steelsearch10개 및 c05의 dynamic-array-cpu-997hz/fst-direct-cpu-997hz
perf.data2개를 gzip -1 -k로 압축하고 압축 해제 SHA가 원본과 같음을 확인한 뒤
비압축 사본을 제거했다. 해당 과거 진단 실행 파일/trace는 .gz를 압축 해제해 복구한다.
기준선/현재 후보/기존 release 후보 실행 파일은 그대로 유지했다.
원본 바이트 식별 목록은 diagnostic-binaries-archive.sha256 및
cpu-diagnostics-archive.sha256이며,c06 아래에 있다. 각 목록 SHA는
`6076b1499fb3d583f87d7931bc3a0abf63eccdcb11c27ece643d167638cb0c8e`,
`f21eb8b026a294fbba7f18a34cd114a60dfea880b0f3526e0f4a8fcbfaac8004`다.

native-replay-persistence-repeated-full에서 전체6회/12토폴로지 측정을 실행했다.
6개 child returncode0,모든 요청 오류0,입력 검증 true이며 부모 exit1은 누적 성능 FAIL이다.
단일 후보710.204/712.331ops/s,3노드828.234/828.132ops/s.
고정 공개 v0.6.0 대비 단일-4.415%/-4.129%,3노드-11.074%/-11.085%다.
published 실패30/32,paired 실패28/29,baseline drift6/1건이며 전체44지표씩을 판정했다.
쓰기 mean 지연도 단일+13.276%/+12.608%,3노드+13.340%/+13.742%로 실패한다.
[전 시나리오 표](native-replay-persistence-performance-2026-09-11.md)에 모든 지연과
OpenSearch 비교를 기록했다. 결과 SHA
`9c2752cb44d2f94b048894f1c808a1788814b606dd5a49f8153f9cc3ff11c84b`,
plan SHA `5cd92fd6be67566406db2890102c0f22a7039fb9229cde93530d00744b783931`.
측정 중 코드/빌드/추가 진단 변경은 없었고 종료 후 동결 소스 검증이 통과했다.
벤치마크 세션23933은 exit1로 종료했다. docker ps에 측정용 컨테이너는 남지 않았다.

OpenSearch 전후 blocks={}와 node1/3을 확인했다. defaults의 threshold_enabled=true,
low85%/high90%/flood95%와 enable_for_single_data_node=false를 모두 보존해 기록했다.
단일 노드까지 모든 디스크 보호가 강제됐다는 인증이나 운영 안전성 인증은 아니다.
과거 OpenSearch 측정의 threshold_enabled=false와 설정이 달라졌음을 숨기지 않는다.

원인 귀속의 다음 경계: 이전6086c31c 동결 Cargo.toml에는
tantivy-fst={path="vendor/tantivy-fst"} 패치가 있지만 현재 Cargo.toml에는 없다.
현재 vendor에는 tantivy만 있다. 이를 자동 복원하거나 사용자 변경을 되돌리지 않았으며,
새 기능 비용과 의존성 차이를 분리해 조사해야 한다. 이 차이를 누적5% 면제로 삼지 않는다.
TV1 미완료,수락0/40,릴리즈 보류이며 unresolved 기능 제외도 아직 결정하지 않았다.

### 2026-09-11 위임 및 FST 원인 분리 준비

사용자 요청에 따라 문서/정형 작업은 Luna,범위가 명확한 검증 코드 보강은 Terra에
위임했다. Astra는 성능 원인 분석과 결과 검토를 담당한다. AGENTS.md에 이 선호와
작업 파일 범위 분리/시간 측정 중 병행 작업 금지를 기록했으며 자동 라우팅 강제라고
주장하지 않는다. 이번 실행에서도 위임 모델을 명시적으로 선택했다.

과거 계획을 확인한 결과 FST 패치는 루트 승격 없이 별도 후보에만 적용돼 있었다.
현재 두 Cargo registry 사본의 tantivy-fst0.4.0/src는 서로 같고,기존6086c31c의
vendor/src와 비교하면 raw/registry.rs 한 파일만 다르다. 해당 vendor 소스 SHA는
9f332316ba58f1f37d9b63e5c8da789ac6d3e6ad4bdf47019c4f95f37146b3f0이며,
기존 Miri 로그 SHA54f49fe86749fdc03b03fafbbeff36f10543866b44252f731fd68251c6f5991e도
이전 기록과 일치한다. 이번에 Miri를 새로 실행한 것은 아니다.

원본은 registry 셀 전체를 즉시 초기화하고,실험 패치는 접근한 행만 초기화한다.
기존 동일 기능 소스의 ABBA 진단에서 refresh 비용 감소 근거가 있었으므로 그 조사를
처음부터 반복하지 않는다. 다만 그 효과를 현재3a3c4023 후보의 개선율로 가져오지 않는다.

다음 비교 단위는 native-replay-fst-isolated-candidate에3a3c4023의 동결 source를
복사해 Cargo 패치/lock의 FST source·checksum/vendor 추가만 다르게 준비하는 것이다.
crates 전체 불변과 source.sha256을 확인하며 루트 의존성은 변경하지 않는다.
이 단위 완료 전 실제 FST 선택 확인,전체 engine/node 및 확장 HTTP,전체 non-plugin
6회/12토폴로지 벤치마크가 필수다. focused 진단은 추가 근거일 뿐 대체가 아니다.
최초 v0.6.0 처리량95% 이상/각 mean,p95,p99105% 이하의 누적 기준과 원본 증거를
유지한다. 원인 귀속 없이 기능 제외/안전장치 완화/릴리즈하지 않는다.

위임 결과 검토: Terra의 safety 검사 보강은 _nodes 응답의 total/successful/failed 및
실제 node 수를 대조하고,잘못된 settings/blocks 자료형을 거부한다. 검토에서 실제
OpenSearch의 blocks={}를 거부하는 초안을 발견해 수정했다. 실제 저장 응답8개 대조가
통과했다. 상시 테스트가 로컬 target 증거 파일에 의존하지 않도록 추가 수정했다.
최종 failure diagnostics/core performance gate/runtime evidence/cgroup/timeline
통합 unittest45건 통과,실패/skip0이다. 실제 차단 상태를 변경하는 PUT은 추가하지 않았다.
이 변경 뒤 실제 벤치마크를 재실행한 것은 아니며 이전 측정의 matrix 해시를 덮지 않는다.

Luna가 native-replay-fst-isolated-candidate 준비를 완료했다. 부모에서 crates 전체
diff 일치,Cargo.lock은 tantivy-fst의 registry source/checksum 제거2행뿐임을 확인했고,
source.sha256 전체 검증도 통과했다. manifest SHA는
`1e1d78b3bc5a6edd1d1e381f7a2c47f28f95ec415e529ae9d65e5db360c199c0`다.
artifacts/preparation.json에 입력/변경 범위/검증 결과를 기록했다.
metadata --offline --no-deps는 통과했다. 전체 metadata는 lock을 조정한 뒤
bumpalo3.20.2 오프라인 캐시 누락으로 중단됐다. cargo tree --offline --locked의
비개발 의존성 확인은 통과했고 불필요한 버전 변경은 없다.
새 후보의 빌드/엔진 시험/HTTP/성능 측정은 아직 하지 않았다. 준비를 구현 완료나
성능 개선으로 세지 않는다. 완료된 위임 에이전트는 종료했다.

## 2026-09-11 FST 분리 후보 빌드 및 기능 시험

native-replay-fst-isolated-candidate에서 분리 후보를 빌드하고 동결 소스의
기능 시험을 완료했다. candidate-build.log는 release profile 최적화 빌드가
7분53초에 완료됐음을 기록한다. 빌드 후 복사한 실행 파일은
`artifacts/steelsearch`이며 SHA-256은
`c224a57afbe039167ccba5bd5dd3ae648ecf444352338618dd4779499491aff9`다.
candidate-build.log SHA-256은
`1956a264f8973e13d4dfde8c62bac77310b8be4db4a9d940301d8dc156f1a4da`다.

source.sha256 manifest 자체의 실제 SHA-256은
`1e1d78b3bc5a6edd1d1e381f7a2c47f28f95ec415e529ae9d65e5db360c199c0`이며,
빌드 후 `source/`에서 `sha256sum -c ../source.sha256`를 실행해 전체 검증이
exit0으로 통과했다. 소스/lock 차이는 준비 기록대로 FST local patch와 그에
따른 `Cargo.lock` 경계뿐이며 루트 의존성은 변경하지 않았다. 아티팩트 복사 후
build/FST 시험 캐시는 정리했고 로그, 동결 소스, 아티팩트는 보존했다.

완료된 기능 시험 증거는 다음과 같다.

- `engine-tests.log`: 946+7+4+9 = 966 passed, failed0.
- `node-tests.log`: 666+459 = 1,125 passed, failed0.
- `fst-tests.log`: 123 passed, failed0.
- `fst-eager-tests.log`: 122 passed, failed0.

로그 SHA-256은 각각 engine `7da599f3a2df0595118a34fbbeca0618ceb7326ff19fa508f4eb8eea2e6413df`,
node `97a901cec48419d1ebfa083be7103735945bc092878f1e7c23e059be1b7eac32`,
FST `b964984033669d2c59768d0b282b9f5ec25eb56f3572e1b546386fc289423c82`,
FST eager `111f45781f5858792eed547d70bcdad9819de64c0748188ecbb771030f1961a6`이다.

`native-replay-fst-isolated-release-live`의 부모 집계 확인 결과 HTTP는 exit1로
종료했고 37 fixtures 중 2,353 passed, 272 failed, 0 skips, 0 failed_setup이다.
`count_probe=true`이며 `binary_unchanged=true`, `fixtures_unchanged=true`도
확인했다. 부모가 이전 native-replay-persistence-release-live-safe의 전체 보고서와
fixture/name/status를 대조한 결과 2,625건 모두 같았다(diff exit0).
HTTP execution.json SHA-256은
`592d4cab79e9cd1a445c733ed96e4fcf096873d4be6edc6ba1f20befa2ffd8b3`다.
전체 성능 벤치마크는 이 기록 시점에 아직 실행하지 않았으므로
unit acceptance나 구현/릴리즈 수락을 주장하지 않는다.
TV1은 미완료, 수락0/40, 릴리즈 보류다.

### 2026-09-11 FST 분리 후보 전체 반복 측정 종료

`native-replay-fst-isolated-repeated-full`의6회/12토폴로지가 모두 child exit0으로
종료했다. 부모 session69447은 exit1, numeric_budget_passed=false,
execution_inputs_verified=true다. 종료 후 동결 source manifest 검증도 exit0이다.
측정 중 다른 빌드/시험/진단/수정은 하지 않았고 에이전트도 모두 종료한 상태였다.
종료 후 docker ps에 측정용 컨테이너는 남지 않았다.

후보 c224a57a 처리량은 단일741.631616689/741.207176187,
3노드854.619432605/852.790181170ops/s다. 고정 v0.6.0 공개 기준 대비
단일 약-0.19%/-0.24%,3노드-8.24%/-8.44%로3노드 회귀가 반복됐다.
published 실패20/21,paired17/13,baseline drift3/5이며 각각44지표를 판정한다.
단일 쓰기 mean/p95/p99와3노드 여러 시나리오 지연도 실패하므로 처리량만으로
통과 처리하지 않는다. FST 변경을 루트에 승격하거나 기능 제외/안전 예외로
자동 전환하지 않았다. TV1/전체 계획 수락0/40,릴리즈 보류다.

result.json SHA-256:
`496a39915dfb3811991c621dc19f03982ac30f565d54979997e22a9597b3800f`.
plan.json SHA-256:
`7d1381e09cfbd0c9404ea27abd8a75cab6897987fd843ad82e35b86da608f258`.
[전체 시나리오 표](native-replay-fst-isolated-performance-2026-09-11.md)에 두 반복의
고정 v0.6.0/OpenSearch 비교를 남긴다. 이전 측정 입력/결과를 덮어쓰지 않는다.

Luna의 성능 표 초안 검토에서 published 비교 열의 잘못된 기준값을 발견했다.
부모가 고정 current.json과 실제 후보/OpenSearch summary.json에서 처리량4행과
지연28행의 모든 값을 다시 계산해 apply_patch로 교체하고 결과32행을 재대조했다.
원본 측정/판정 파일은 변경하지 않았다. 위임 결과를 검토 없이 수락하지 않았으며
최종 git diff --check도 통과했다.

### 2026-09-11 후속 노드별 refresh 진단 계획

이전 단계는 전체 측정과 FST 비교 증거를 추가한 진행으로 분류한다. 현재 c224a57a의
전체 gate에서도 ID lookup 누적 비용은 단일0.352/0.346초,3노드 관측0.223/0.218초로
낮다. commit은 단일15.081/15.128초,3노드 관측11.177/11.385초다.
이는 서로 다른 작업량의 누적값이며3노드 전체 합계나 요청당 비용으로 해석하지 않는다.

기존 run-core-refresh-work-diagnostic.py의 --node-counters를 사용해 db244133과
c224a57a를 before/after/after/before 순서로3노드 각60초 비교한다.
기존5000문서/384값/4클라이언트/3샤드/replica1/seed13/non-plugin 혼합 부하를 유지한다.
세 endpoint의 고유 local node ID와 native refresh 카운터를 확인하고 부하 후 두 번
refresh하여 native/fallback count를 기록한다. endpoint 합계를 전역 ID 완전성으로
사용하지 않는다. 카운터는 준비 단계를 포함하며 순차 수집이라 원자적 snapshot이 아니다.
도구 SHA ff6bbb97f8478ee4767b67601ba7c88f629ca2eb35524a9b51896f048c9f43c3,
해당 도구 unittest8건 통과다. 이 기록 시점에 진단은 아직 실행하지 않았다.

실제 수정은 원인 증거 후 결정하며 각 구현 단위의 전체 engine/node/HTTP 및 non-plugin
6회/12토폴로지 gate를 계속 요구한다. 최초 v0.6.0 처리량95%/각mean,p95,p99105%
누적 기준은 그대로다. 이 진단만으로 수락/기능 제외/릴리즈하지 않는다.

### 2026-09-11 세 노드 카운터 ABBA 결과

`native-replay-fst-node-counters-three-abba`의4회 진단은 session23115 exit0으로
완료됐다. 요청 오류0,실제 executable identity/runtime 및 입력 불변 검증을 통과했다.
각 실행에서 세 endpoint의 고유 local node counter를 수집했다. 측정 중 agent는
종료했으며 다른 빌드/시험/진단/코드 수정은 하지 않았다.

| 실행 | 실제 후보 | ops/s | refresh mean/p95/p99 ms | 세 노드 commit 누적 초 | 세 노드 lookup 누적 초 |
| --- | --- | ---: | --- | ---: | ---: |
| 0 | db244133 | 920.111 | 8.499 / 17.612 / 23.131 | 27.575 | 1.696 |
| 1 | c224a57a | 853.832 | 8.939 / 18.145 / 23.473 | 26.820 | 0.492 |
| 2 | c224a57a | 849.089 | 8.883 / 17.950 / 23.301 | 26.564 | 0.494 |
| 3 | db244133 | 914.363 | 8.575 / 17.070 / 21.812 | 27.926 | 1.648 |

세 노드 합산 add 시간은0.753/0.971/0.961/0.774초,reload는
0.821/0.803/0.813/0.821초다. 누적 카운터는 준비 단계를 포함하고 각 실행의
write/refresh 횟수가 다르다. 이는 per-operation 비용이나 CPU 시간의 비교가 아니다.
후보의 첫 노드 commit11.554/11.111초,다른 두 노드 합계15.265/15.453초로
단일 endpoint 관측 밖에 비용이 존재함은 확인했다. 이 사실을 회귀 원인으로
단정하지 않는다. commit 횟수/색인 문서량/대기 시간을 구분할 증거가 다음에 필요하다.

두 번 추가 refresh 이후 endpoint별 native/fallback count:

| 실행 | endpoint1 | endpoint2 | endpoint3 |
| --- | --- | --- | --- |
| 0 | 6010 / 6241 | 4246 / 4246 | 4316 / 4316 |
| 1 | 5954 / 5954 | 4044 / 4044 | 4158 / 4158 |
| 2 | 5934 / 5934 | 4039 / 4039 | 4128 / 4128 |
| 3 | 6029 / 6216 | 4216 / 4216 | 4314 / 4314 |

기준선 첫 endpoint의231/187건 차이가 재현됐고 후보는 모든 endpoint에서 일치했다.
이는 전역 ID/내용 완전성 증명이 아니며 기준선의 누락을 후보에 재현해 성능을
맞출 근거도 아니다. 기존 전체 gate FAIL과 최초 v0.6.0 누적5%는 유지한다.

Terra의 소스 검토 후 부모가 lib.rs의out_of_order 판정과full-refresh 분기를 확인했다.
정상 순서의 신규 replay는 out_of_order=false여서 이 분기로 전 샤드 재구축을
강제하지 않는다. late/replace는 전체 샤드에 영향을 줄 수 있지만 가시성 보호에
필요하다. 실제 혼합 부하에서 발생 횟수를 확인하기 전에 이 분기를 끄거나
샤드 범위를 좁히지 않는다. production 코드 변경/수락 추가/릴리즈는 없다.

result.json SHA-256:
`8110eaddac7acc19d139417a39a1b9b5bf1dba28e9a9f4a7c5581564056a3e9b`.
plan.json SHA-256:
`4296756e02956ccd674f968a1740971a7b77ddf8193d6f10ac4e277d6797f3f0`.

### 2026-09-11 append 문서량 및 writer 대기 진단 연결

기존 diagnostic-lock-timing feature에 refresh_writer mutex wait/hold site와
성공한 append의 batch/documents/commit_nanos 누적 샘플을 추가했다.
Terra는 diagnostic_lock.rs와Python 파서/시험을,부모는append_documents 연결 및
통합 검토를 담당했다. 기본 빌드에서는 새 계측 경로가 cfg로 제외된다.
writer lock 해제 후 I/O하며 batch 카운터도 mutex snapshot 후 잠금을 풀고 출력한다.
batch1/65/129/...를 기록하며 full rebuild/실패한append는 포함하지 않는다.
최종 샘플은 누적 하한이지 전체 정확한 횟수나 HTTP 지연 판정이 아니다.

검토에서 iterable 이중 소비와비객체JSON 처리를 수정했다. 로그 도착 순서는
동시성 때문에 뒤바뀔 수 있어 pid/batches로 정렬 후 중복/누적 감소를 거부한다.
기존미등록site 거부는 유지한다. Python lock/refresh 진단 시험17건 통과,
독립 Rust 모듈 시험4건 통과다.

루트 소스의 전체engine 시험은 별도 append-diagnostic-engine-tests target에서
nightly --locked --offline,CARGO_BUILD_JOBS=2,debug정보/증분빌드 비활성으로 실행했다.
diagnostic-lock-timing 활성970건(950+7+4+9),기본966건(946+7+4+9)이 모두
실패/ignore/filter0으로 통과했다. session44438/25358 모두 exit0이다.
기본 로그에는LOCK/APPEND_DIAGNOSTIC가 없었다. 활성 시험의실제 로그1225건,
4pid에서writer/append파서 연결을 확인했다. 모듈 시험전용site=test1건은 이 연결
확인에서 명시적으로 제외했으며 parser의운영identity 규칙을 완화하지 않았다.
단위시험 부하의카운터를 실제 서버 성능으로 사용하지 않는다.

로그 SHA-256:
- feature: `039c4e2d874702200c413ddc2435f0f2ef3d19ca32919329401c4366e05598ac`
- default: `d22d61ecc337a3f5e9b2363a4c9fb2daae633675d42e2306c796500f4664001a`
소스 SHA-256:
- engine lib.rs: `3bae0e73ee661284d7d5ea173119c6096aa24c442b2625fb033eda4d43b378c0`
- diagnostic_lock.rs: `37226251f4d29b8c32cbd91e62805f8df7919f971cf857defe5c201a028d0386`

실측용 native-replay-append-diagnostic-candidate/source는 기존 c224a57a 동결소스에
위 두 파일만 교체한 snapshot이다. diff로 두 파일만 다름을 확인했다.
source.sha256 자체SHA는
`7182e7a7fea2ecbd06b7a74ee4b934cb0fa7c75ee43217c533383ebe6781a2e7`.
이 snapshot은FST 패치를포함하지만 이번루트engine시험은루트의FST 미승격 의존성으로
실행됐다. snapshot 자체의빌드/실측을 이미 통과한 것처럼 쓰지 않는다.
다음 단계는 별도 build 디렉터리에서standalone-runtime 및
os-engine-tantivy/diagnostic-lock-timing으로release진단binary를빌드하고 실제identity를
기록한 뒤3노드혼합부하의writer대기/append문서량을수집하는것이다.
새최적화의구현완료전 전체engine/node/HTTP 및non-plugin6회/12토폴로지와
최초v0.6.0 누적5%를반드시재검증한다. 현재성능결과는c224a57a FAIL 그대로며
TV1미완료,수락0/40,릴리즈보류다.

### 2026-09-11 writer 대기 및 append batch 실측

고정 append 진단 source를 별도 build 디렉터리에서 nightly --release --locked
--offline,standalone-runtime 및os-engine-tantivy/diagnostic-lock-timing으로 빌드했다.
7분54초,session91584 exit0이다. 실행 파일SHA는
`ab40e172f0883b11acc437be7b1a2189deb2af179e9bd3fda45682e1d17c9f4b`,
candidate-build.log SHA는
`f4ac92859ec114af9038dd7c5884d3a51acbfee12e9c321ea82268b5bed0d05b`다.
빌드/측정 후 source manifest 검증 통과. 아티팩트 보존 후 해당 build 캐시만 정리했다.

`native-replay-append-writer-three-abba`는 c224a57a/ab40e172/ab40e172/c224a57a
순서로3노드 각60초,기존5000문서/384값/4클라이언트/non-plugin 혼합 부하를 실행했다.
이 before는 최초v0.6.0이 아니라 계측 전 후보이며,누적게이트의 기준선 변경이 아니다.
session18488 exit0,4회 요청 오류0,실제runtime/입력 불변/노드별 카운터 검증 통과다.
측정 중 다른 빌드/시험/진단/수정이나 에이전트 작업은 없었다.

| 실행 | 실제 실행 파일 | ops/s | refresh mean ms |
| --- | --- | ---: | ---: |
| 0 | c224a57a | 864.878 | 8.638 |
| 1 | ab40e172 | 859.386 | 8.785 |
| 2 | ab40e172 | 869.058 | 8.611 |
| 3 | c224a57a | 864.708 | 8.732 |

Terra가 작성한 target/core-replacement-c06/summarize-append-writer.py를 부모가
검토했다. ABBA/원본baseline 해시/각관측파일/실행파일 및세고유PID/소유node별로그를
검증하며 AFTER의모든PID에refresh_writer와append샘플을 요구한다.
비계측 과거 로그는 no lock diagnostic samples로exit2 거부했고 실제 새로그는exit0이다.
집계기와파서 자체해시도출력에보존한다. 문서수/batch수는마지막샘플까지의평균이며
전체평균의하한이아니다. full rebuild/실패append/샘플뒤의tail은추론하지않는다.

| 진단 반복/node | 마지막 batch 수 | 누적 문서 수 | 문서/batch | commit ms/batch |
| --- | ---: | ---: | ---: | ---: |
| 1/1 | 2049 | 4211 | 2.055 | 5.340 |
| 1/2 | 1217 | 2290 | 1.882 | 6.061 |
| 1/3 | 1217 | 2504 | 2.058 | 6.409 |
| 2/1 | 2113 | 4339 | 2.053 | 5.104 |
| 2/2 | 1217 | 2290 | 1.882 | 6.018 |
| 2/3 | 1217 | 2504 | 2.058 | 6.181 |

writer mutex의주기샘플 최대대기는각반복200/240ns였다. 관측범위에서이mutex경쟁을
주요병목으로볼근거는없다. 모든대기상황이없다는증명이나HTTPtail인증은아니다.
작은성공append에commit약5.1~6.4ms가소요된다는관측이확보됐으므로다음은동일작업량의
native segment 생성/commit비용을검토한다. 단순refresh생략이나안전성완화는하지않는다.
소스상HTTP는이미web::block을사용하고멀티샤드refresh는into_par_iter경로가있다.
이를미구현으로오인해중복개발하지않는다. 현재FST패치외의새성능최적화는없으며
원본c224a57a의전체게이트FAIL과수락0/40/릴리즈보류는변하지않는다.

result.json SHA-256:
`f8f2a4fbdcef93d4bee9ea767d3cff411238baf48dc11b954301b092bb5f18ff`.
plan.json SHA-256:
`e61525b5f5164d13260aa4d4536c00079e9876fc90e14fc9da24917f16cb4511`.
append-writer-summary.json SHA-256:
`c88d32882537027a723e7623d1cf6a0a9764005b8520a66ad4a5fdeaadfbd6b7`.

### 2026-09-11 native 초기 term 테이블 격리 후보

고정 Tantivy의compute_initial_table_size와tantivy-stacker0.2.0의ArenaHashMap을
확인했다. 초기 테이블은Vec으로일괄초기화하며 native구현은절반차면확장한다.
공개writer API의메모리예산을낮춰안전최소값을우회하지않고,격리한vendor에서만
초기계산결과를4096으로cap했다. native성장/해시동등성/게시/merge/내구성계약은
변경하지않았다. 루트vendor에는아직승격하지않았다.

Terra가진단예제에양수batch-docs/refreshes옵션과검증을추가했고부모가큰ID의
numeric_value연산을u64로계산해오버플로를방지했다. 기존기본4문서/256회는유지한다.
동일FST/lock/소스의두격리빌드중segment_writer.rs만다르며실제batch2를ABBA로
비교했다. 각실행2조건,전체8조건의2179문서ID/fast값/이전reader/샘플numeric term
검증이통과했다. before/after진단예제시험각10건통과,실행/입력검증도통과했다.
준비시간before1.614~2.099ms,after1.272~1.317ms이며서버개선율로환산하지않는다.
Luna의문서초안에서반복평균표와ABBA표기/plan해시누락을교정하고원본JSON에서
모든8조건표를다시생성했다.
[원본수치및입력](native-term-table-experiment-2026-09-11.md)을참조한다.

서버 native-term-table-candidate/source는c224a57a에서위vendor파일만교체했다.
source.sha256 자체SHA는
`f5f551642c78b5b21283ec02b69d2be1956134b8daa7f6074b4544d8f898ccad`다.
독립build에서nightly --locked --offline,debug/증분비활성,2build jobs로실행한
전체engine966건과node1125건은실패/ignore/filter0이다. session18986/64639 exit0,
이후소스manifest검증도통과했다. release서버빌드/HTTP/전체성능은아직미실행이다.
다음은이동결후보를빌드해37fixture2625case HTTP를이전후보와케이스별대조하고,
전체non-plugin6회/12토폴로지로고정v0.6.0 누적처리량95%/각mean,p95,p99105%를
확인하는것이다. 큰batch의재할당비용도상쇄하거나누락하지않는다.
전체단위수락/릴리즈는보류하며고정기준선과기존FAIL판정을재설정하지않는다.

### 2026-09-11 초기 term 테이블 전체 재측정: 성능 FAIL

`target/core-replacement-c06/native-term-table-repeated-full-ready`에서
baseline/candidate/OpenSearch/OpenSearch/candidate/baseline 6회/12토폴로지를
완료했다. 자식 실행은 모두 exit0, 요청 오류0, execution_inputs_verified=true다.
부모 exit1과 numeric_budget_passed=false이며 구현 수락은 여전히 false다.
수정한 시작 대기로 이전 OpenSearch 초기화 오류 구간을 통과했으며 안전성 검사는
그대로 유지했다. 바이너리668365ad와 고정 기준선db244133은 바꾸지 않았다.

단일 처리량741.758/746.290ops/s는 published v0.6.0 대비-0.17%/+0.44%,
3노드873.220/869.829ops/s는-6.24%/-6.61%다. 각 반복44지표 중 published
실패14/16, paired실패5/10, baseline drift실패11/5다. drift로 예산을 면제하지
않는다. 쓰기 mean은 단일+11.90%/+10.86%, 3노드+10.38%/+11.21%다.
모든 시나리오 및 반복은
[전체 비교 기록](native-term-table-performance-2026-09-11.md)에 별도로 보존한다.
이 결과로 초기 예약 조정이 모든 병목을 해결했다고 주장하지 않는다.

result.json SHA-256:
`da4d0dedee101e4a173e09d0a614443eee87e05cc2786ef5aa457432802b5f57`.
plan.json SHA-256:
`32f028fdf891e6f81b624af5aea6a30cf02a86c8a21b266f99405dd334a8d0a8`.

다음 최적화 전에는 현재 바이너리의 3노드 mixed CPU 진단으로 잔여 비용을
확인한다. 고정 native 소스의 SegmentWriter::for_segment는 모든 필드에 대해
TokenizerManager::get을 호출하고 get은 RwLock 읽기와 boxed analyzer clone을
수행한다. 실제 tokenizer 사용은 indexed Str/Json 경로에만 있다. 이는 조사
후보일 뿐 병목의 측정 증거는 아니며 기본 analyzer 검증/오류 계약을 생략하는
패치를 먼저 넣지 않는다. native worker commit 수명과 serializer 비용도 함께
검토하고 독립 진단 결과로 다음 격리 실험을 선택한다. 이후 구현 변경도 전체
engine/node/HTTP 및 non-plugin6회/12토폴로지를 통과하기 전 완료하지 않는다.

### 2026-09-11 term 테이블 후보와 v0.6.0 CPU 후속 관측

전체 게이트 후 서브 에이전트를 종료하고 candidate668365ad, baseline db244133
순서로 3노드 mixed 진단을 각각 실행했다. 각45초 부하 중20초 cpu-clock49Hz,
DWARF8192 샘플이며 matrix/perf/부모 모두 exit0, 요청 오류0, 실행 전후 바이너리
해시 일치다. 두 실행은 반복 측정 게이트가 아니며 소급해 사전 선언 ABBA로
표현하지 않는다. 프로파일러가 켜진 처리량825.191/875.196은 진단값일 뿐
위 전체 게이트의 수치를 대체하지 않는다.

서버 PID만 선택한 `perf report --children --sort symbol -g none`에서:

| 심볼 | candidate children/self | baseline children/self |
| --- | --- | --- |
| IndexMerger::write | 11.67% / 0.39% | 1.45% / 0.09% |
| IndexMerger::write_fast_fields | 7.81% / 0.00% | 0.09% / 0.00% |
| SegmentWriter::finalize | 0.31% / 0.00% | 1.45% / 0.09% |
| TokenizerManager::get | 0.08% / 0.08% | 0.09% / 0.00% |

candidate에서 columnar merge/serialize_u64_based_column_values가 각각
7.73%/7.65% children으로 관측됐다. children은 중복 포함되므로 합산하지 않는다.
서버 CPU 합계는 candidate26.23초, baseline25.56초이나 관측 구간과 완료 작업 수가
다르므로 작업당 회귀율로 환산하지 않는다. 잃어버린 샘플은0이지만 49Hz의 짧은
관측은 짧게 생존하는 worker, off-CPU 대기와 merge 발생 시점의 차이를 해결하지
못한다. 현 증거로 analyzer clone 패치를 먼저 넣지 않는다. 다음은 반복 관측으로
merge 차이를 확인하고 고정 native columnar merger의 기존 API/코덱 경로를
조사하는 것이다. 앞서 악화된 merge floor1024/2048 재시도나 merge 자체 생략으로
우회하지 않는다. 새 구현은 별도 소스/빌드에서 집중 검증 후 전체 게이트를 반복한다.

증거 루트는 `target/core-replacement-c06/`이며 아래 네 파일을 보존한다.

| 파일 | SHA-256 |
| --- | --- |
| native-term-table-mixed-three-cpu/diagnostic.json | 6c2e26a0e431fb88636777e6f4cb065132319ef90903af77013e6e2795a00869 |
| native-term-table-mixed-three-cpu/perf.data | b20b2d28ab14202ee8b829eb9b5b2899ca007941b06c794797077e99a8174c8f |
| native-term-table-baseline-mixed-three-cpu/diagnostic.json | 950cfed7dbd5dc704d392ded2ecb7fc4fc3660ad49cdfd3d798bea932d9e21d8 |
| native-term-table-baseline-mixed-three-cpu/perf.data | 722b31f5bcb53650f86b97f6b92811bbd0b4fbe2661331861514008981228207 |

### 2026-09-11 term 테이블 서버 검증 및 초기화 대기 오류

위 대기 상태 이후 release 빌드가 완료됐다. 측정 바이너리 SHA-256은
`668365ad0524a4ede6be85503665babc5884c493ee514120082aa900f458b721`이다.
HTTP 37fixture/2625case는 2353통과/272실패, skip/setup실패0이며 이전
c224a57a 후보와 케이스별 상태가 동일하다. 실행 기록은
`target/core-replacement-c06/native-term-table-release-live/execution.json`, SHA-256
`2b5b66048781b48fe57c45d82d77cc5405bebbcf8fdcabd9bdf8d7e9a17517c1`이다.

전체 게이트 `native-term-table-repeated-full`은 baseline/candidate/OpenSearch
첫 반복을 마쳤으나 index3 OpenSearch의 3노드 부하 시작 전 안전성 검사에서
중단됐다. 실제 블록은 global.1 `state not recovered / initialized`이며
디스크 차단으로 단정하지 않는다. 기존 `wait_for_cluster`는 노드 수만 확인해
초기화 완료를 보장하지 못했다. 부모 session63471은 terminal exit2다.
result.json SHA-256은
`37b83f932cef62b926f9901414d38c9ec53f8c4614a67421f4925854e4c6d440`이며
acceptance_established/execution_inputs_verified/numeric_budget_passed 모두 false다.
따라서 이번 실행은 미완료 증거이며 최종 성능 비교표로 승격하지 않는다.
안전성 검사와 디스크 임계값은 유지하고 초기화 대기를 보강한 뒤 전체를 새로
실행한다. 바이너리와 고정 v0.6.0 기준선은 바꾸지 않는다.

Terra가 OpenSearch 시작 대기를 green health와 빈 정상 형식의 blocks 응답까지
확인하도록 수정했다. monotonic 기한 내 초기화/영구/알 수 없는 블록이나 잘못된
응답이 남으면 준비 완료로 인정하지 않는다. Steelsearch의 기존 노드 수 대기와
`require_opensearch_safety`는 유지했다. 부모가 미완성 health와 잘못된 blocks
경계 검증을 보강했다. benchmark 관련 Python72건과 core performance 관련47건,
`git diff --check`가 통과했다. 이들은 하네스 테스트이며 실제 전체 부하 실행이 아니다.
수정 matrix SHA-256은
`b260a0a3a59ee3449ea0227a65507d8bd67be16caddb7ed91ebab71ee0872f71`이다.
다음 실제 전체 실행은 기존 디렉터리를 덮어쓰지 않고
`target/core-replacement-c06/native-term-table-repeated-full-ready`에 새로 수행한다.
전체 6회/12토폴로지 실행과 최종 입력 불변 검증 전에는 이 수정 및 후보의
실행 검증이 끝난 것으로 표시하지 않는다. Luna/Terra는 작업 검토 후 종료했다.

빌드 공간 확보를 위해 재생성 가능한 격리 빌드 캐시만 정리하고, 기존 CPU
perf.data 네 개는 gzip 무손실 보관 후 복원 SHA를 확인했다. 원본/압축 해시와
경로는 `target/core-replacement-c06/pre-table-profile-archives.json`에 남겼다.
측정 바이너리, 동결 소스, 원본 기준선, 결과와 로그는 보존했다.
