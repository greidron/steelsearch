# 플러그인 제외 OpenSearch 대체 구현 계획

## 최우선 실행 순서 변경 (2026-09-11, 벤치마크 중지)

최신 사용자 지시: **기능 수정을 모두 진행해 호환성을 맞춘 뒤 벤치마크와 성능
최적화를 수행한다. 성능 최적화 중 기능 테스트가 깨지면 다시 통과하도록 수정한다.**
이 규칙은 이 문서와 연결된 조사/계획의 모든 과거 "구현 단위마다 벤치마크"
문구를 대체한다. 과거 기록은 실행 이력일 뿐 재측정 지시가 아니다.

- 기능 수정 단계: 남은205개 비교 실패와 추가 발견 결함을 native-first로 수정한다.
  각 수정의 기능 회귀 테스트와 전체 HTTP 호환성 검증은 유지한다. 성능 벤치마크,
  마이크로벤치마크, 성능 전용 최적화는 실행하지 않는다. 비교기 완화/실패 삭제 금지.
- 기능 호환성 확인 후: 전체 비플러그인 벤치마크로 병목을 확인하고 최적화한다.
  기능 테스트를 계속 실행하며, 회귀가 생긴 최적화는 수정하거나 해당 변경을 되돌린다.
- 최초v0.6.0 누적 처리량95%/시나리오 mean·p95·p99 105% 기준과 릴리즈 조건은
  유지한다. 기능 수정 확인과 성능/릴리즈 수용을 구분하며 성능 예외를 승인하지 않는다.
- native-fetch-contract-repeated-full은 사용자 지시로 중단했다. 5번째 실행 중
  SIGINT로 종료했고 상위 runner 종료2, 관련 부하 프로세스/테스트 컨테이너 잔존0을
  확인했다. 부분 결과는 보존하되 전체 성능 결과/수용 증거로 사용하지 않는다.
- 최신 기능 증거:11d91339 기능 검증용 dev 바이너리 전체2671건 중2466통과205실패skip0.
  직전132d8d6f 대비 동일 비교 조건에서75건 개선 후, 같은 바이너리에서 took 비교 오류
  8건을 별도로 정정했다. 신규 회귀0. 최초292실패 중79건 개선과8건 비교기 정정을 구분한다.
  engine975/node1145 및 비교기 테스트21건 통과. 성능 증거가 아니다.
- 후속 [native term-vector 기능 구현](native-termvectors-functional-plan-2026-09-11.md):
  공개/realtime reader 분리, native postings/통계/분석, keyword 생성과 REST 연결을
  구현했다. 배열 위치72건과 termvector 계약3건이 개선됐고, 배열 위치의 나머지8건은
  실행 시간의 잘못된 동등 비교를 수정한 뒤 통과했다. took은 형식/범위를 검증하되
  문서·검색 결과·의미 있는 상태를 그대로 비교하며 AGENTS.md에 원칙을 기록했다. Emoji 분석기
  차이, artificial 문서, 분석기 재정의, 다중 요청 옵션 등은 미완료다. 벤치마크는 중지.

작성일: 2026-09-07. 기준 릴리즈: v0.6.0.
기준 소스 구현 커밋: `d987c0677374dfd88f0d393b9ad9c486b1ace31c`.
릴리즈 커밋: `cbb5866ed32771ca326eb5d004569c4c884929ca`.

이 문서는 계획이다. 아래 40개 작업 패키지는 확인된 결함 40개를 뜻하지
않으며, 아직 완료되지 않은 구현·검증·운영 준비 작업을 구분한 것이다.
이 계획 작성으로 코드 구현, 운영 전환 또는 후속 릴리즈를 승인하거나 완료
처리하지 않는다. 성능 기준은 사용자가 확정한 최초 v0.6.0 대비 누적 회귀 5%
이내를 적용한다. 이는 구현 단위마다 새로 주어지는 5% 예산이 아니다.

반복되는 성능 손실과 그 대조 절차는
[성능 pain-point 대장](performance-pain-point-ledger-2026-09-14.md)에 별도로
기록한다. 이 계획의 구현 단위는 해당 대장을 먼저 대조하고, 원인 증거와 검증
결과를 다시 대장에 남겨야 한다.

## 1. 목표와 제외 범위

목표는 대상 서비스가 사용하는 OpenSearch 코어 기능을 데이터 안전성과
운영 성능을 유지하면서 SteelSearch로 대체할 수 있음을 입증하는 것이다.
보다 넓은 코어 대체 주장에는 서비스 사용분뿐 아니라 선언한 지원 API와
운영 프로파일 전체의 검증이 필요하다. 일부 워크로드의 성공을 전체 호환성으로
확대하지 않는다.

- 플러그인 API, 플러그인 ABI, k-NN, ML Commons, 플러그인 기반 hybrid/neural,
  Dashboard 및 플러그인 전용 운영 경로는 구현·완료율·성능 판정에서 제외한다.
- OpenSearch Security 플러그인 API 호환성도 제외한다. 단, SteelSearch 자체
  TLS·인증·권한·감사·비밀정보 보호는 운영 배포의 독립적인 요구사항이다.
- 모델 커넥터 비밀정보처럼 제외된 기능에만 필요한 보안 조건은 코어 조건과
  분리한다. 이를 통과한 것처럼 표시하거나 실제 코어 보안 조건까지 없애지 않는다.
- 단일 노드, SteelSearch 전용 다중 노드, OpenSearch와의 외부 연동,
  동일 클러스터 혼합 노드는 서로 다른 배포 프로파일이다.
- 독립 클러스터로 이전하는 서비스에 혼합 노드 가입을 필수로 강제하지 않는다.
  다만 혼합 노드 호환성을 주장하려면 I01-I03을 별도로 모두 통과해야 한다.
- 지원 대상으로 선언한 코어 옵션이 미구현이면 명시적 오류만으로 완료 처리하지
  않는다. 구현을 마치거나 사용자가 승인한 지원 범위 변경이 필요하다.

## 2. 현재 확인된 출발점

| 항목 | 확인된 사실 | 확대 해석하면 안 되는 것 |
| --- | --- | --- |
| 기존 실패 수정 | 코어 27개 실패 항목, 16개 고유 케이스 해결; 플러그인 2항목 제외 | 전체 코어 기능이 모두 완성되었다는 뜻이 아님 |
| 최종 빌드 실시간 비교 | 2026-09-07 core 1180 / strict 922 / semantic 79 / write 78 통과, 실패·skip 0 | 장애·장시간·대규모·운영 보안 인증이 아님 |
| 소스 테스트 | engine 825 / node 585 / query DSL 133, daemon 직렬 457 통과 | 병렬 플러그인 캐시 테스트 1건의 실패 이력은 그대로 남음 |
| 릴리즈 성능 | v0.5.0 소스 재빌드 대비 처리량 단일 +12.00%, 3노드 +10.02% | 개발용 내구성 설정의 60초 측정이므로 운영 성능 보장이 아님 |
| 회귀 쟁점 | 별도 개발 기준선 대비 정렬 평균 지연 +0.18% 및 장시간 혼합 부하 +0.82% 관측 | 전체 처리량 개선이나 A/A 변동으로 면제하지 않음 |
| 빌드 재현성 | 공유 캐시 오염을 제거한 소스 재빌드가 측정본 SHA-256 `db244133...`와 일치 | 실행 파일만 복원해서 의존 크레이트 캐시도 복구되었다고 간주하면 안 됨 |

근거는 [v0.6.0 검증 기록](../releases/v0.6.0/validation.md),
[빌드 출처](../releases/v0.6.0/build-provenance.json),
[진단 기록](release-diagnostic-2026-09-06.md)이다.
기존 매트릭스와 아키텍처 문서의 오래된 통과 기록은 현재 바이너리의 통과 증거로
재사용하지 않는다. 이번 계획에서는 추가 운영 하네스를 실행하지 않았다.

## 3. 상태 및 우선순위

### 기능 실패 우선 순서 (2026-09-11 사용자 요청)

292개 실패 케이스의 기능/API 불일치를 원인별로 수정한 뒤, 통과한 동작을
보존하면서 성능을 개선한다. 292는 독립 결함 수가 아니라 d8fd7ce6 후보의
40fixture/2659건 HTTP 비교에서 실패한 케이스 수다. 추가 검사로 발견한 source
노출 결함도 포함하며, 비교기를 약화하거나 실패 케이스를 삭제하지 않는다.
실제 보고서별 건수와 판정 주의사항은
[기능 실패 대장](functional-failure-ledger-2026-09-11.md)에 기록한다.

- 우선순위: fetch 응답 계약 수정 중인 단위, 배열 위치/구문 빈도/검색 점수의
  native 원인 그룹, term vectors, 집계/날짜 파싱 계약, 나머지 API 차이 순으로
  실제 실패 증거와 의존성을 확인한다. Tantivy 지원 여부는 pinned 소스/API로
  먼저 검증한다. 이 순서는 원인 조사에 따라 조정하되 성능 전용 미세 최적화가
  기능 수정 전체를 반복해서 밀어내지 않도록 한다.
- 각 구현 단위 뒤 전체 engine/node 테스트, 확장 HTTP, 전체 비플러그인
  6회/12토폴로지 벤치마크를 실행한다. 측정과 최적화의 작업 순서를 구분할 뿐
  벤치마크를 최종 시점까지 생략하지 않는다.
- 기능 수정 상태와 최종 수용 상태를 별도로 보고한다. 성능 초과 후보는 정상
  완료/릴리즈하지 않으며 최초 v0.6.0 누적 5% 기준과 제외/예외 규칙을 유지한다.
- 점수 등의 오차 허용은 항목별 근거와 명시적 합의가 먼저 필요하다. 검색 결과
  누락, 잘못된 집계, 의도하지 않은 source 노출을 수치 오차로 면제하지 않는다.

### 중간 릴리즈 요청 (2026-09-10)

사용자는 성능이 기준선 수준으로 회복되고 작업이 마무리되면 중간 릴리즈를 한 번
발행한 뒤 남은 계획을 계속 진행하도록 요청했다. 이는 해당 조건을 충족한 중간
릴리즈에 대한 승인이지 현재 FAIL 후보의 즉시 발행이나 성능 예외 승인이 아니다.
정확한 버전 번호는 아직 정하지 않았다.

- 최초 v0.6.0 고정 누적 게이트와 릴리즈 대상의 필요한 기능/호환성/안전성 검증을
  통과한 뒤 발행한다. 토폴로지 처리량뿐 아니라 각 시나리오 mean/p95/p99를 검증한다.
- docs/releases/README.md의 전체 증거 묶음과 직전 published release/OpenSearch
  시나리오별 비교 표를 생성/검사하고 tools/publish-release.py를 사용한다.
- 중간 릴리즈는 전체40패키지 완료 주장이 아니다. 미완료/제외 범위를 명시하고
  발행 뒤 나머지를 이어간다. 발행으로 누적 기준선을 재설정하지 않는다.
- 현재a5b38b49도 성능 FAIL/HTTP272실패이며 이 조건을 충족하지 않았다.

### 최신 진행 요약 (2026-09-11, native response mapping 후보 성능 FAIL)

- 다음 기능 수정 초안: [fetch REST 계약 4건](native-fetch-contract-investigation-2026-09-11.md).
  측정7d83e363을 보존하고 별도 소스에서 요청 옵션 검증·빈 fields·source-only 응답을
  수정했다. 소스 고정 후 전체 engine966/node1143 테스트 통과, 소스 해시 재검증을
  완료했다. 새 릴리즈 바이너리·전체 HTTP·6회12토폴로지 성능은 아직 미실행이므로
  기존292실패의 감소나 이 단위 완료를 주장하지 않는다.
- 진행 중 격리 수정: [fetch projection 순서](native-fetch-projection-investigation-2026-09-11.md).
  최신 전체 성능:7d83e363의6회12토폴로지 실행 완료, 하위 실행 종료0/오류0,
  입력 검증 통과이나 누적 게이트 FAIL이다. 최초v0.6.0 대비3노드 처리량
  -5.4686/-5.9706%, 단일 쓰기 평균+12.7356/+8.0665%,3노드 쓰기 평균
  +9.8756/+9.9748%다. 고정 기준 실패 지표11/15개이며 모든 시나리오 값을
  감사 JSON에 보존했다. 측정 수행은 완료했지만 구현 단위 수용/릴리즈는 보류한다.
  아래 미실행 표현은 이전 경과이며 최신 판정은 이 측정 결과다.
  보강7d83e363은 engine966/node1142 통과, 릴리즈 빌드7m50s/종료0,
  전체 HTTP41fixture/2671건 중2379통과292실패skip0이다. 새 visibility12건은
  모두 통과하고 부모 대비3건 개선/케이스 상태 신규 회귀0이며 원본 source도
  대조했다. 기존292실패는 그대로다. 이 후보의 전체6회12토폴로지 성능은 아직
  미실행이므로 단위 완료/릴리즈하지 않는다. 아래 초안 기록은 경과로 보존한다.
  기존 REST 필드 추출 전에 engine의 _source projection이 값을 제거하는 결함을
  수정한다. 필드 요청이 있을 때만 공개 source projection을 추출 뒤로 미루고,
  일반 검색/권한/reader generation은 유지한다. 이것을 native doc-values 구현으로
  주장하지 않으며 날짜 파싱/배열 포맷/집계 collector 차이는 별도 미해결 상태다.
  초안d8fd7ce6은 engine966/node1141 통과, release7m58s/종료0, HTTP40fixture/
  2659건 중2367통과292실패skip0이다. 추출 상태는4건 개선/신규 회귀0이나 원본
  source 감사에서 stored_fields만 요청할 때 기본source가 반환되는 기존 결함을
  발견해 성능 측정 전에 같은 단위의 보강 후보로 진행한다. 초안 증거는 보존한다.
  기본 source 숨김/명시적 stored _source 선택을 수정하고 비교기에 source 존재·값
  검사를 추가했다. 이후 전체 engine/node·확장 HTTP41fixture/2671건·6회12토폴로지
  성능 게이트를 실행한다. 최초v0.6.0 누적5% 기준·0/40·TV1미완료·릴리즈 보류는 유지한다.
- 다음 조사: [Tantivy 집계 collector 직접 연결](native-aggregation-collector-investigation-2026-09-11.md).
  소유권 이동/전역 페이지 선택 후 hit 생성은 이미 적용되어 있어 다시 구현하지 않는다.
  반면 collect_aggregations_native는 현재 native query 결과 문서를 source 집계기로
  넘긴다. pinned0.21.1의 fast-field 집계/분산 병합 API를 확인했고 별도 capability
  probe로 terms/range/fixed-day/date calendar 거부/버킷 한계를 먼저 검증한다.
  terms.order 제한에 관한 과거 product parser 기록을 Tantivy의 미지원으로 오해하지 않는다.
  후속 capability probe는 최종11건 중8통과3실패다. 중복 키워드뿐 아니라 숫자
  range/날짜 fixed-day도 같은 문서의 다중값을 중복 집계했다. 단일값 fast-field
  cardinality 식별, 음수 UTC 날짜 경계, native bool 필터 집계 대조군은 통과했다.
  실제 HTTP 새14건은8통과6실패, 날짜 원인 분리 새10건은0통과10실패이며 각 실행의
  기존1500건은 모두 통과했다. 기본 date 매핑의 숫자1000을 OpenSearch는 서기1000년,
  제품은 epoch1초로 해석한다. 명시적 epoch_millis에서는 날짜 key_as_string 매핑
  반영 차이가 남고, _source:false/docvalue_fields 응답 누락도 확인했다. 이는
  참조 엔진의 배열 집계 결함으로 단정할 수 없으며 C02/C05/C06 미해결 계약으로 남긴다.
  terms.order가 있는 혼합 집계의 다중값 dispatch 차이도 별도 재현 대상으로 기록했다.
  두 신규fixture는 다음 전체 HTTP에 포함한다(기존37+2,2649건). 원본 실패와
  진단 기대값을 보존했으며 이를 제품 수정 완료나 성능 향상으로 계산하지 않는다.
  분산 병합 일치가 중복 집계 정확성을 뜻하지 않으며, calendar/day 거부와 반환 버킷
  한계 동작도 별도로 확인했다. 기대값/기존 실패 로그는 보존하고 native 연결 전
  다중값·달력 변환·기존 누적 할당 보호를 검증한다. 제품 변경/새 성능 결과는 없으며,
  이후 각 구현 단위의 전체 테스트·HTTP·성능
  게이트와 최초v0.6.0 누적5% 조건은 해당 계획에 그대로 명시했다.
- 후속 격리 단위는 [native 응답 매핑 복제 생략](native-response-mapping-investigation-2026-09-11.md)이다.
  검색 후 매핑 snapshot은 정렬값 렌더링에만 소비되지만 정렬 없는 요청도 항상
  metadata_manifest_state를 잠그고 복제했다. 쓰기 경로도 같은 잠금을 사용한다.
  일반/PIT/scroll 응답에서 parsed nonempty sort가 없으면 이 snapshot만 생략한다.
  앞단 검증용 매핑/명시적 날짜 정렬/fetch 경로와 native query/scorer는 유지한다.
  이는 불필요한 작업의 확인이지 회귀 원인 전체의 입증이나 성능 개선 측정이 아니다.
  Terra가 별도 native-response-mapping-candidate에 구현/3개테스트를 추가했고
  부모 검토 후 전체 engine966/node1136건이 통과했다. source manifest SHA는
  `df27bffe3f02502e34bb5d5f8a46d6fb6cf854715712ecd643671b85fa0f8d86`다.
  release 빌드7m52s/종료0, artifact SHA는
  `4086ba72cd923c0757584af7cf58a5980ceae838084ebabb30c4b68b4d69fcc3`다.
  확장 HTTP37fixture/2625건은2353통과272실패skip0이며 이전231c65f6와 모든
  이름별 케이스 상태가 같다. 이후 전체6회12토폴로지도 실행 완료/요청 오류0이나
  성능 게이트는 FAIL이다. fixed 실패13/11,paired6/8,baseline drift7/9지표다.
  후보 처리량 단일748.909/755.700,3노드882.737/883.923ops/s이며,
  고정v0.6.0 대비3노드-5.22%/-5.09%,write mean+8.52~10.60%로 여전히 미수락이다.
  result SHA `e7ed17321f7c9e36f26b254808e1de1fa6e2059dc3b38ef28f6d598e2278c203`.
  마지막 기준선 실행 중 관찰이 중단됐으나 살아 있는 원래 세션을 이어서 완료했다.
  입력/소스/실행 파일 불변 및 재계산 판정 일치를 확인했다. root 승격/릴리즈 없음.
- 다음 격리 구현은 [HTTP 응답 인코딩](native-http-encode-investigation-2026-09-11.md)이다.
  a5b38b49에서 직렬화가 기존 web::block 바깥 Actix handler에 남는 소스/프로파일
  경로를 확인했다. 같은 serde 인코딩과 JSON 해제를 기존 blocking 작업 안으로
  이동한 별도 source 후보를 만들었고 root/runtime 및 기존 artifact는 보존한다.
  source 차이는 standalone_runtime.rs와 신규8개시험 모듈뿐이며 manifest SHA는
  `1ea09d3f99c911f3d749b5f4fcd9fcefb624936b2b185d6b54b07a5d2e55bbf3`다.
  engine966/node1133건이 모두 통과했고 source 불변을 재확인했다. 최초 node 시도의
  테스트 매크로 컴파일 실패 로그도 보존했다. 새 release 빌드7m49s/종료0이며
  artifact SHA는 `231c65f67360b27f2cd37625540a427adc01fcc5d4aeb23891cf7bec33ae4bf3`다.
  확장 HTTP37fixture/2625건은2353통과272실패skip0이고 이전 a5b38b49와 모든
  이름별 케이스 상태가 같다. count probe 및 source/binary/fixture 불변을 확인했다.
  첫 전체 non-plugin 실행은 OpenSearch 반복2의3노드 준비 timeout으로 종료2였다.
  6회 중 완료3회,4번째 실행 부분 결과를 보존했고 뒤2회는 미실행이다.
  후보 첫 단일/3노드 처리량756.406/862.328ops/s,write mean3.130/3.293ms이며
  완전한 반복 판정이 아니다. readiness 실패 증거 수집을 보강하고73개 benchmark
  도구 시험을 통과했다. 캐시 정리 후5000건 적재 포함 준비 진단을 통과했고,
  새 native-http-encode-repeated-full-fresh-20260911 전체6회/12토폴로지도 완료했다.
  모든 실행 종료0/요청 오류0, 입력 불변=true지만 최종 성능 판정은 FAIL/부모종료1이다.
  고정v0.6.0 대비 실패 지표는 반복별10/18개, paired8/7개, baseline drift11/14개다.
  후보 단일 처리량753.934/732.942,3노드886.081/871.391ops/s다.
  고정기준 대비3노드 처리량-4.86%/-6.44%,write mean+9.58~12.76%로 미수락이다.
  결과 SHA `f127daa8164e75d97830cf3dd553cc2f1ff23c6892e170c7d686424d9ae2a8fc`.
  다음은 반복 실패한 write/3노드 ranking 경로의 native 비용을 조사한다.
  기존 기준선 ranking 누락을 재도입하지 않는다. 고정5% 및 안전 조건을 완화하지 않는다.
  native 검색 의미·반환량·보안·내구성은 바꾸지 않는다.
- HTTP 단계 계측 ABBA4회 완료: 처리량 baseline1280.857/1280.992,
  candidate1193.964/1200.659ops/s,write mean baseline2.819/2.839ms,
  candidate3.044/3.027ms다. 쓰기 request_prepare/decode는 거의 같고
  urlopen 평균은 baseline2.060/2.083ms,candidate2.263/2.242ms다.
  ranking decode는 약0.017ms에서0.234ms로 증가했지만 urlopen은 감소했다.
  wall-thread CPU를 특정 원인 대기로 등치하지 않는다. 정식 부하 도구/서버 변경
  없이 격리 도구만 사용했고8개 시험,4회 요청 오류0/입력 불변/phase count 검증을
  통과했다. [계측 결과](write-interference-investigation-2026-09-11.md)는 진단이며
  고정5% 게이트/릴리즈 승인을 대체하지 않는다.
- 최신 후보의 고정 검색 응답600건을 보존했다. ranking60건에서 baseline은
  반환 hit0/평균160bytes,candidate는 hit합계230/평균10637.75bytes다.
  이는 이미 확인한 기준선 ranking 누락의 최신 후보 재확인이며 전체 correctness
  인증은 아니다. 나머지4scenario는 반환 hit합계가 같았다. offline decode ABBA에서
  ranking 평균은 baseline3.50~3.53us,candidate166.40~167.26us다.
  전체 HTTP 회귀의 기여율로 환산하거나 게이트를 면제하지 않는다. 다음은 실제
  4-client 응답 수신/JSON 해석/스레드 대기와 native 응답 비용 분리 진단이다.
  [원본 응답 및 재생 근거](write-interference-investigation-2026-09-11.md)를 보존했고
  서버 변경/수락/릴리즈는 없다.
- 동일 write_search CPU ABBA4회도 완료했다. 요청 오류0/입력 불변=true이며
  baseline 처리량1298.110/1297.379,candidate1216.329/1203.521ops/s다.
  후보 write mean2.989/3.022ms,baseline2.796/2.783ms로 회귀가 남는다.
  약20초 관측 서버 CPU 합계는 후보18.12/18.02초,baseline20.56/20.66초다.
  서버 CPU 감소를 HTTP 개선으로 해석하지 않는다. 다음은 동일 요청의 실제 응답량/
  hit/source 형태와 클라이언트 처리 경계 확인이다. 원인은 아직 확정하지 않았고
  [CPU 근거와 한계](write-interference-investigation-2026-09-11.md)에 기록했다.
- 검색/refresh 분리 진단8회가 종료됐다. 동일 a5b38b49/v0.6.0 실행 파일로
  각 조건 ABBA를 실행했고 요청 오류0, 입력 불변 및 내부 결과 검증=true다.
  write_refresh의 후보 write mean은 paired 기준선 대비+0.96%/+1.33%,
  처리량+3.40%/+1.41%다. 반면 write_search는 write mean+9.52%/+7.80%,
  처리량-7.95%/-6.89%로 explicit refresh 없이 회귀가 재현됐다.
  이는 고정 전체 게이트 합격도 특정 구현/lock 원인의 확정도 아니다.
  [8회 결과와 전체 활성 시나리오](write-interference-investigation-2026-09-11.md)를
  보존하고 다음은 해당 write_search 조건의 native 검색/응답 처리 및 공유 자원
  비용을 조사한다. 서버 변경/기능 수락/릴리즈 없음,0/40 및 전체 성능 FAIL 유지.
- 후속3노드 write-only ABBA는 db244133/a5b38b49/a5b38b49/db244133 순서로
  실행했고4회 요청 오류0/입력 불변=true다. 양쪽 write mean3.34~3.36ms로
  mixed gate의 회귀가 재현되지 않았다. 실제 env상 refresh=false 요청의 native
  적용과 per-write 저장은 지연되어 있어 native commit을 직접 PUT 비용으로
  오인하지 않는다. 서버 소스 변경 없이 검색/refresh 간섭 분리 진단을 위와 같이 완료했다.
  [근거와 한계](native-columnar-merge-investigation-2026-09-11.md)를 따르며
  write-only 결과로 기존 mixed FAIL을 면제하지 않는다.
- 후속 bitpacked 출력 버퍼 격리 실험은 양쪽 native176건+문서1건 통과 후
  ABBA4회/8조건/96개 시간과 모든 값 검증을 완료했다. 큰 병합 mean은
  before14.57~14.64ms/after12.60~12.62ms이며 이는 서버 성능 개선율이 아니다.
  `native-buffered-bitpack-candidate/source`를 별도 준비했고 source manifest SHA는
  `6e4e1a6434cbd7f4cca64a3375678b62214b75bfc2b84290d5490a85bde11a47`이다.
  동결 소스로 engine966/node1125건이 통과했고 소스 해시 불변을 확인했다.
  서버 release 빌드도 완료했고 측정 artifact SHA는
  `a5b38b4932a3386fc495800578f6d76970ca3882437b93f3c60cfc280ec6c6b8`이다.
  HTTP2353통과/272실패/skip0이며 이전6d7f90e1과2625개 케이스 상태가 동일하다.
  전체 non-plugin6회/12토폴로지 요청 오류0/입력 불변 true지만 성능 FAIL이다.
  단일 처리량758.784/739.363ops/s(고정v0.6.0+2.12%/-0.49%),
  3노드879.128/863.650(-5.61%/-7.27%)이며 쓰기 mean은 단일+10.10%/+13.59%,
  3노드+10.07%/+12.67%다. published실패12/19,paired10/7,drift1/18개를 보존한다.
  [전체 비교](native-buffered-bitpack-performance-2026-09-11.md)와
  [native 조사 기록](native-columnar-merge-investigation-2026-09-11.md)의 게이트를
  통과하기 전 완료/승격하지 않는다. 최신a5b38b49 성능 FAIL,0/40은 그대로다.
- 후속 native columnar 병합은 [격리 조사/계획](native-columnar-merge-investigation-2026-09-11.md)을 따른다.
  현재 두 바이너리의 ABBA CPU 진단에서 native merge 비용 차이를 반복 관측했다.
  기존 open_u64_lenient API를 활용하는 동일 타입 numeric Stack 격리 패치를 만들었고
  원본 native166/변경본172테스트가 통과했다. 이어 국소 ABBA4회/8조건의 모든 값
  검증이 통과했고1024행 병합16.6~18.1ms에서14.2~15.4ms로 감소했다.
  이는 서버 개선율이 아니다. 격리 서버의 engine966/node1125건과 release 빌드를
  마쳤다. HTTP2353통과/272실패로 이전 후보와2625케이스 상태가 동일하다.
  전체6회/12토폴로지도 요청 오류0/입력 불변 true지만 성능 FAIL이다.
  새6d7f90e1 처리량은 단일720.822/758.555,3노드876.895/872.433ops/s다.
  고정 v0.6.0 대비 단일-2.99%/+2.09%,3노드-5.85%/-6.33%이며 쓰기 mean은
  단일+15.39%/+9.66%,3노드+11.12%/+10.91%다. published실패15/15,
  paired실패5/7,기준선drift실패23/3개를 모두 남겼고 변동으로 예산을 면제하지 않는다.
  [새 전체 성능](native-raw-column-merge-performance-2026-09-11.md)을 따른다.
  전체0/40·TV1미완료·릴리즈 보류는 유지한다. 아래는 이전 후보의 보존 기록이다.

- 후속 초기 term 테이블 후보는별도로준비했다. native해시맵의자동확장은유지하고
  초기예약상한만4096으로줄인격리실험에서commit준비비용감소를관측했다.
  새 서버 동결 소스의 engine966/node1125건과 release 빌드는 통과했다.
  HTTP 37fixture/2625case는 2353통과/272실패이며 이전 FST 후보와 모든 케이스
  상태가 같다. 전체 성능 실행은 OpenSearch 두 번째 반복의 3노드 초기화 블록
  때문에 exit2로 중단됐다. 이는 완성된 성능 FAIL/PASS 결과가 아니라 실행 오류다.
  초기화 대기를 수정·검증한 뒤 새 출력 디렉터리에서 전체 6회/12토폴로지를
  재실행했다. 기존 부분 실행을 합쳐 전체 통과 증거로 사용하지 않는다.
  [실험및검증](native-term-table-experiment-2026-09-11.md)을따른다. 루트vendor미승격,
  구현 단위는 미완료다. 후속 `native-term-table-repeated-full-ready`는
  전체 6회/12토폴로지 요청 오류0, 입력 불변 검증 true로 종료했으나 성능 FAIL이다.
  후보 처리량은 단일741.758/746.290, 3노드873.220/869.829ops/s이며 고정
  v0.6.0 대비 단일-0.17%/+0.44%, 3노드-6.24%/-6.61%다.
  44지표 중 published14/16, paired5/10, 기준선 drift11/5개가 예산을 넘었다.
  쓰기 mean은 단일+11.90%/+10.86%, 3노드+10.38%/+11.21%다.
  [전체 비교](native-term-table-performance-2026-09-11.md)를 따른다.
  기준선 변동으로 후보 실패를 면제하지 않으며 0/40·TV1미완료·릴리즈 보류를 유지한다.

- 후보 c224a57a는 3a3c4023의 애플리케이션 소스를 유지하고 tantivy-fst local patch만
  적용한 별도 빌드다. 루트 의존성으로 승격하지 않았다. Luna에 증거 확인/문서 작성을
  위임했고 성능 원인 판단과 최종 통합 검토는 부모가 담당했다.
- engine966/node1125/FST123/eager122건 통과. HTTP2625건은2353통과272실패,
  setup/skip0이며 이전 후보와 전체 케이스 상태가 같다. TV1은 미완료다.
- 전체6회/12토폴로지가 종료됐고 입력 불변 검증은 통과했으나 성능 FAIL이다.
  단일741.632/741.207ops/s,3노드854.619/852.790ops/s로 고정 v0.6.0 대비
  각각 약-0.19%/-0.24%, -8.24%/-8.44%다. published20/21,paired17/13,
  baseline drift3/5지표 실패다. 단일 쓰기 지연과3노드 여러 시나리오 실패가 남는다.
- [전체 시나리오 표와 증거](native-replay-fst-isolated-performance-2026-09-11.md).
  FST 변경은 refresh 비용을 줄였지만 누적5% 통과나 전체 기능 완료를 뜻하지 않는다.
  측정 중 빌드/시험/수정/진단을 병행하지 않았고 종료 후 동결 소스 검증도 통과했다.
- 다음 단위: 기존 native 쓰기/refresh 프로파일 증거부터 재검토해 남은 비용을
  분리한다. 기능 정확성 차이와 비용 원인을 확인하기 전 기능을 제외하거나 safety를
  완화하지 않는다. 최적화 후보마다 전체 engine/node/HTTP 및 non-plugin6회/12토폴로지
  벤치마크를 다시 실행하고 최초 v0.6.0의 각 처리량/mean/p95/p99 누적5%를 적용한다.
  focused 진단은 대체가 아니다. 수락0/40,릴리즈 보류를 유지한다.

### 이전 진행 요약 (2026-09-11, native replay persistence 성능 FAIL)

- 새 후보3a3c4023의 전체 engine966건/node666건 통과,확장 HTTP2625건 중
  2353통과272실패,setup/skip0이다. 기존2601건 상태 변경/누락0이며
  termvectors realtime-false2건이 추가로 통과했다. TV1은 미완료다.
- 전체 반복6회/12토폴로지 요청 오류0,입력 검증 true이나 성능 FAIL이다.
  고정 v0.6.0 공개 기준 대비 단일 처리량-4.415%/-4.129%,3노드-11.074%/-11.085%다.
  published30/32,paired28/29지표 실패이며 지연 실패도 남아 있다.
- [전체 시나리오 표와 증거](native-replay-persistence-performance-2026-09-11.md)를 따른다.
  OpenSearch 차단 해제/디스크 검사 비활성화 호출을 제거한 도구로 측정했다.
  기존6086c31c의 추가 tantivy-fst 의존성 패치가 현재 작업 트리에는 없으므로,
  두 후보 차이를 기능 수정만의 비용으로 단정하지 않는다. 원인 귀속과 최적화가 필요하다.
- 수락0/40,릴리즈 보류. 최초 v0.6.0 누적5% 기준은 재설정하지 않는다.

### 이전 진행 요약 (2026-09-10, native Text metadata 성능 FAIL)

- 후속 native Text metadata 구현: 입력 호환성 정보를 색인 snapshot에 저장하고
  native authority의 source BM25 통계 재구축 호출을 제거했다. 전체 engine955건
  (935+7+4+9)통과,실패/ignore/filter0이다. 삭제 복구를 추가한 재실행도955건 통과다.
  새 release6086c31c 빌드와 동결 소스 검증을 마쳤다. 전체 HTTP2601건은2351통과250실패,
  skip/setup실패0,이전31281a3d와 케이스 상태변경/누락0이다. Count/입력 불변도 통과했다.
  전체 반복6회/12토폴로지 오류0,입력 검증 true,성능 FAIL이다.
  단일737.868/745.210ops/s로 v0.6.0 대비-0.692%/+0.296%까지 회복했지만,
  3노드853.098/844.789ops/s는-8.404%/-9.296%로 예산 초과다.
  단일 write 지연도 남으며 published22/25,paired20/23지표 실패다.
  [전체 성능 표와 증거](native-text-metadata-performance-2026-09-10.md)를 따른다.
  아래31281a3d 성능을 새 구현의 성능으로 재사용하지 않는다. 수락0/40,릴리즈 보류다.
  [구현 및 검증 단계](native-ranking-audit-2026-09-10.md#native-text-metadata-구현과-전체-engine-검증).

- 동일 seed 코퍼스의 ranking96조합을 고정 v0.6.0/후보/pinned OpenSearch2.19로 진단했다.
  v0.6.0은 전부0건,후보와 OpenSearch는66조건에서10 hits를 반환했다.
  후보 total은96/96일치하지만 비어 있지 않은 상위10 ID 집합은66조건 모두 다르다.
  기준선 결과 누락과 반환량 차이를 확인했으며,이를 누적5% FAIL의 자동 면제로 쓰지 않는다.
  [동일 요청 진단 증거](native-ranking-audit-2026-09-10.md#동일96개-ranking-요청의-반환량-차이-확인).
  후속3.7 비교는 total/상위 점수(6자리)96/96일치,비어 있지 않은66조건 모두 상위10동점이다.
  2.19의 큰 점수 차이는 explain에서 BM25 배율/keyword scoring 버전 차이로 확인했다.
  기존 strict 실패는 유지하며2.19에 맞추기 위해3.7 scorer를 임의로 변경하지 않는다.

- compound native authority를 일반 페이지/샤드 수집/Count/min_score 요청 경로에 연결했다.
  기본 Text Match/MultiMatch/Phrase, keyword Term, i64 Range의 검증 가능한 Bool 트리만
  인덱스별로 허용한다. static post-filter 판정을 전역으로 제거하지 않았다.
  전체 engine953건(933+7+4+9) 통과,동결 후보31281a3d release 빌드를 완료했다.
  전체 HTTP2601건은2351통과250실패/skip0,직전24e36d75 대비29건 해결/새 실패0이다.
  compound60건은38통과22실패,문서 집합60/60일치,min_score 페이지4건 모두 통과다.
  전체 non-plugin 반복6실행/12토폴로지 요청 오류0,입력 불변 확인,성능 FAIL이다.
  단일493.412/488.200ops/s,3노드770.722/755.954ops/s로 고정 v0.6.0 대비
  처리량33.593%/34.294%,17.249%/18.834% 감소다. published37/38,paired29/34지표 실패다.
  전체 시나리오 mean/p95/p99와 OpenSearch 비교 및 baseline drift는
  [새 후보 전체 성능 증거](compound-native-authority-performance-2026-09-10.md)에 기록했다.
  원본 Match analyzer 정보가 기존 DSL 파서에서 소실되는 별도 한계도 기록했다.
  현재 수락0/40과 릴리즈 보류를 유지하며,아래24e36d75 성능을 새 변경 결과로 재사용하지 않는다.
  [연결 범위와 증거](native-ranking-audit-2026-09-10.md#2026-09-10-compound-native-authority-연결-전체-게이트-대기).

- native MSM query 구현 진행: Bool MSM>1의 조합 열거를 기존 Tantivy Union 기반
  threshold 집계로 교체했다. Count/TopDocs/seek/삭제/구간 재사용을 검증한 전체 engine
  951건 통과, MSM12조건 기대 점수와 정확히 일치, compound60조건의 native 합산 최대
  차이2.385e-7 미만이다. source guard나 복합 native authority는 아직 변경하지 않았다.
  별도 동결 후보24e36d75 빌드를 마쳤다. 전체 HTTP2601건은2322통과279실패/skip0이며
  직전 후보와 fixture별 집계가 동일하다. Count probe/입력 불변을 확인했다.
  새 후보 전체 반복6실행/12토폴로지 요청 오류0,입력 불변,성능 FAIL이다.
  단일487.043/486.263ops/s,3노드736.687/735.571ops/s이며 최초 v0.6.0 대비
  34.450%/34.555%,20.903%/21.023% 감소다. published26/23,paired20/19지표 실패,
  baseline drift32/44 및38/44통과다. 전체 시나리오 표와 원본 출처는
  [MSM 성능 기록](#2026-09-10-native-msm-query-전체-반복-성능-fail)에 기록했다.
  구현 단위는 미완료, 수락0/40, 릴리즈 보류이며 아래 e49e5b61의 수치를 새 후보의
  결과로 재사용하지 않는다. [구현 및 증거](native-ranking-audit-2026-09-10.md#2026-09-10-native-msm-query-구현-전체-게이트-대기).
- compound MSM 후속 사전 검증: 고정 Tantivy 0.21.1의 BooleanWeight/Union/combiner와
  Count/TopDocs 진입점을 확인했다. 5개 조건의 전체 문서 조합을 1/3샤드, MSM0~5로
  검사하는 시험을 추가했고 전체 engine950건(930+7+4+9) 통과다. 이 시험은 결함 진단이며
  MSM 수정 완료가 아니다. MSM2에서 기대 점수5가30으로 중복 합산되는 문제가 재현된다.
  현재 phrase 연결 이후의 기존 compound60건도 다시 진단했다. production은 변경하지
  않았으며 HTTP/전체 benchmark를 새로 실행한 것으로 계산하지 않는다. 수락0/40과
  아래 e49e5b61 성능 FAIL은 유지한다. 세부 결과와 각 후속 구현 단위의 전체 게이트는
  [MSM 사전 검증 기록](native-ranking-audit-2026-09-10.md#2026-09-10-compound-msm-native-확장-사전-검증)에 있다.
- native sloppy phrase production scorer 후보e49e5b61의 전체 검증을 마쳤지만 수락은 미통과다.
  native Query/Weight/Scorer,세그먼트 postings/버퍼 재사용,Count 조기 종료와 fractional BM25를
  연결했다. vendor Tantivy0.21.1의 기존 정수 API는 유지하고 기본 Text 보호 조건을 보존했다.
  전체 engine949건 통과(929+7+4+9),확장 HTTP2601건은2322통과279실패/skip0이다.
  기존2481건의 실패252→238,추가 반복구문120건은79통과41실패다(이전14통과106실패).
  반복구문120건의 HTTP 문서 집합은 모두 일치한다. 잔여41건은순서24/점수만17이며
  raw 점수 최대 차이는2.581e-7 미만이다. 비교 기준을 완화하거나 통과로 바꾸지 않았다.
- e49e5b61 전체 반복6실행/12토폴로지 요청 오류0,입력 불변 확인,성능 FAIL이다.
  처리량 단일473.125/482.402ops/s,3노드743.459/730.627ops/s로 최초 v0.6.0 대비
  36.323%/35.075%,20.176%/21.553% 감소다. published44지표 중23/27실패,
  paired17/20실패,baseline drift40/44 및33/44통과다. 수락0/40,제외0,릴리즈 보류다.
  다음은 source 경로가 남은 compound ranking의 native score tree/MSM 연결이다.
  아래5a621371 및 시험 전용 matcher 기록은 이전 단계이며 새 후보 결과로 재사용하지 않는다.
- native 위치 matcher를 시험 전용으로 구현했다. 실제 Tantivy term conjunction/postings 위에서
  반복 위치 충돌과 재배열을 처리하여120조건 문서 집합과896개 문서별 f32 빈도가 참조와 일치한다.
  긴 반복 입력의 heap 상한/문서 간 reset/큰 위치값 시험을 포함한 전체 engine947건 통과다.
  Lucene 위치 순회를 Rust로 좁게 이식했고 source 재검색이나 모든 위치 조합 탐색은 하지 않는다.
  production Query/Weight/Scorer·fractional BM25·HTTP 연결은 아직 미완료다. cfg(test)만
  연결했으므로 production5a621371/전체 성능 FAIL은 그대로이며 완료율이나 릴리즈 판정을 바꾸지 않는다.
  [위치 매처 구현 기록](native-ranking-audit-2026-09-10.md#2026-09-10-native-위치-매처-구현과-참조-검증)에 근거와 다음 게이트를 기록했다.
- 반복/다중 토큰 phrase 후속 조사120건을 추가했다. 실제 HTTP1620건은1514통과106실패,
  공통1500건 통과/새120건14통과106실패다. 기존2481 전체 재실행과 합산하지 않는다.
  native 직접 비교도 문서 집합60/120만 일치하며, 반복어의 같은 위치 재사용 오탐과
  3토큰 재배열 누락을 재현했다. 빈도를 f32로 바꾸는 점수 wrapper만으로는 충분하지 않다.
  slop0의20조건 문서 집합/빈도와 sloppy 권위 경로 거부를 고정한 전체 engine945건 통과다.
  이번 변경은 시험/fixture/문서이며 production5a621371과 아래 전체 성능 FAIL은 그대로다.
  다음은 native postings의 반복 위치 충돌/재배열 matcher와 fractional scorer 확장이다.
  [반복 구문 조사 기록](native-ranking-audit-2026-09-10.md#2026-09-10-반복다중-토큰-phrase-빈도-조사)에 근거를 남겼다.
- 배열 위치 production 후보5a621371의 전체 검증을 마쳤지만 수락 기준은 미통과다.
  native tokenizer/PreTokenizedString으로 기본100/명시0·1·5/문자열100 gap을 연결했다.
  빈 문자열과 null/빈 배열, 숫자·불리언 변환을 실제 참조로 검증했다. scalar 경로는 유지한다.
  전체 engine944건 통과,80문서 native postings/norm 및55구문 membership이 참조와 같다.
  HTTP2481건은2229통과252실패/skip0이다. 새 배열 검색55건의 total/ID 집합 일치는
  28→55건이지만 점수55건과 source 기반 termvectors80건은 엄격 비교 실패로 유지한다.
- 5a621371 전체 non-plugin 반복6실행/12토폴로지 요청 오류0, 입력 불변 확인, 성능 FAIL이다.
  처리량 단일481.888/476.795ops/s,3노드745.023/733.936ops/s로 최초 v0.6.0 대비
  35.144%/35.829%,20.008%/21.198% 감소다. published44지표 중23/28실패,
  paired19/22실패, baseline drift41/44 및40/44 통과다. 정식 수락0/40, 제외0, 릴리즈 보류다.
  아래f345f41f와daede139는 이전 후보 기록이며 새 후보 수치로 재사용하지 않는다.
- 후속 compound 조사60건을 추가했다. 실제 ranking의 MultiMatch/phrase/term/range 및
  minimum_should_match0·1·2/boost/정렬/min_score·페이지를 분해했다. 별도 HTTP1560건은
  1510통과50실패/skip0이며 기존2286 전체의 재실행이나 새 실패50개의 고유 결함 수가 아니다.
  source 점수 경로에서1샤드 min_score=1.42의 repeat 문서 누락, native2-of-3 조합의
  점수3배 중복을 재현했다. 기존 DisjunctionMaxQuery로 중복 합산을 제거하는 시험이 통과했다.
  root 전체 engine942건 통과. 이 단계는 시험/fixture/문서만 변경했고 production f345f41f와
  아래 전체 성능 FAIL은 그대로다. compound guard를 제거하거나 새 성능 수치를 만들지 않았다.
- 후속 production 단위는 검증된 기본 Text/slop0 구문 검색의 native BM25 통계/boost
  연결과 source 점수 덮어쓰기 제거다. 필드 정렬에서도 native scorer로 선택 문서의 점수를
  읽는다. 기본 매핑 메타데이터의 제한적 복구 호환성, 옵션 원형 보존, refresh eligibility,
  native 점수0 보존을 시험했다. sloppy/배열 gap/갱신 후 soft-delete 통계는 미완료다.
- native-exact-phrase v1(3624be06)은 보존했으나 옵션 원형 보존 전 빌드라 최종 후보가 아니다.
  v2 f345f41f는 별도 source/artifact에서 빌드했고 후보 전용 v1 Cargo cache만 재사용했다.
  v0.6.0 기준선 빌드/실행 파일/공개 증거는 변경하지 않았다. 작은 boost의 native 점수0
  보존을 포함한 최종 전체 engine941건 통과, 확장 HTTP2286건 중2219통과67실패/skip0이다.
  기존2248건에서는1/3샤드 exact phrase2건이 해결돼 실패40→38이다. 새38건은9통과29실패다.
- f345f41f 전체 non-plugin 반복6실행/12토폴로지 오류0, 입력 불변 확인, 최종 성능 FAIL이다.
  처리량 단일478.837/486.959ops/s,3노드742.415/744.767ops/s로 최초 v0.6.0 대비
  35.555%/34.461%,20.288%/20.035% 감소다. published44지표 중21/21실패,
  paired18/20실패, baseline drift41/44 및37/44 통과다. 아래 daede139는 이전 후보다.
  이 단위는 완료로 처리하지 않는다. 정식 수락0/40, 제외0, 릴리즈 보류다.

- 선행 phrase 조사: slop7종/boost2종/1·3샤드의28건에서 실제 OpenSearch explain을
  수집했다. 거리1의freq=0.5, 거리2/역순의freq=1/3, 배열은slop100부터freq=1/101이다.
  native pre-tokenized 위치로 배열 경계를 표현하면서 term 점수/norm을 유지하는 시험이
  통과했다. 조사 당시 root engine936건 통과이며 그 단계 변경은 시험/fixture/문서뿐이었다.
  조사 시점의 전체 성능은 아래daede139였다. 조사 HTTP는 별도1528건
  (공통1500통과/새28실패), 기존2248건 전체 재실행이 아니며 합산해 통과율을 만들지 않는다.
  fractional phrase 빈도는 native scorer 확장 대상이고, 배열 gap은 native 색인 연결
  대상이다. 상세 근거와 누락된 설정 전달은 native ranking 조사 기록의 마지막 절에 있다.
- native 조사 후 minimum_should_match=1의 중복 점수를 production 연결 코드에서 수정했다.
  기존 Tantivy BooleanQuery의 optional 그룹을 한 번 필수화하며, >1/phrase/source guard는
  변경하지 않았다. engine934건 통과, 독립 native-minimum-one 후보 daede139 빌드 완료다.
  HTTP2248건 중2208통과40실패/skip0, 실행 파일/fixture 불변 확인. 무정렬 단일 결과
  재현2건은 이전439725ca의6점에서 OpenSearch와 같은3점으로 수정되어 통과했다.
  기존 ordered bool2건은 점수가 같아졌지만 동점 순서가 달라 실패 판정을 유지한다.
  전체 non-plugin 반복 측정6실행/12토폴로지 오류0, 입력 불변 확인, 최종 성능 FAIL이다.
  후보 처리량492.684/483.359ops/s(단일),742.530/744.123ops/s(3노드), 최초 v0.6.0
  대비33.691%/34.946%,20.276%/20.104% 감소다. published44지표 중20/21실패,
  paired16/19실패, 기준 drift36/44 및41/44 통과다. 구현 단위 완료로 처리하지 않는다.
  아래439725ca 수치는 직전 후보 기록이며 현재 수정본의 수치로 재사용하지 않는다.
- 후속 native 조사에서 연결 코드의 bool 점수 중복과 phrase 보정/boost 누락,
  source phrase 빈도 고정 및 배열 경계 차이를 재현했다.
  [native ranking 조사 기록](native-ranking-audit-2026-09-10.md)에 지원 API/최소 비교/
  참조 응답과 다음 구현 범위를 분리해 기록했다. 조사 단계에서는 시험 모듈만 추가했다.
  전체 engine933건 통과. 새16건 진단의 ordered HTTP는1통과15실패이며,
  그중5건은 ID별6자리 점수가 같고 동점 순서가 다른 사례다. 합격 기준은 완화하지 않았다.
- 숫자 range 중복 평가 생략 전 계약 테스트에서 `lt:i64::MIN`의 Tantivy fast-field
  overflow panic을 재현했다. `gt:i64::MAX`도 같은 경계 변환 위험이 있어 두 빈 범위를
  native EmptyQuery로 처리했다. root engine932건 통과, 독립 후보439725ca로 검증했다.
  HTTP2214건 중2197통과17실패/skip0, 새 경계12건 통과다. 전체 반복 성능 FAIL이다.
- 정수864조건 비교와 source guard 반례14조합을 추가했다. 필터 검사 생략은 아직 구현하지
  않았다. root/frozen2d50548e는 이제 다르며, 정식 수락0/40과 릴리즈 보류는 유지한다.
- 직전439725ca 후보 처리량은483.236/470.750ops/s(단일),736.911/728.465ops/s(3노드)다.
  최초 v0.6.0 대비 각각34.962%/36.643%,20.879%/21.786% 감소했다.
  published44지표 중24/27실패, paired22/25실패, 기준 drift41/44 및42/44 통과다.
  최종6실행/12토폴로지 오류0, execution_inputs_verified=true이며 성능 수락은 false다.
- 최초 시도는 OpenSearch3노드 create-index403으로 중단됐다. 증거와 바이너리를 보존하고
  Cargo cache만 정리해5.2GB를 확보한 뒤 설정 변경 없이 전체6실행을 새로 수행했다.
  두 시도의 부분 자료를 합쳐 통과시키지 않는다. 자세한 해시/표는 문서 끝에 있다.
- 다음 우선순위는 native 기능/현재 연결/의미 차이/수치 오차를 분리하는 검증이다.
  Tantivy0.21.1에는 phrase/slop, bool, boost/dismax, range 및 BM25 통계 확장 API가 있다.
  현재 source 후처리 분기 존재를 Tantivy 기능 부재로 해석하지 않는다.
  정확도 허용오차는 사용자와 검토 중이며 합격 기준이나 누적 성능5% 예산을 바꾸지 않았다.

### 이전 후보 요약 (2026-09-09, deferred bool 2d50548e)

아래는 이전 후보 기록이다. 최신439725ca의 결과로 합산하거나 재사용하지 않는다.

- 오류 없는 bool의 must 점수 평가를 필터/should 판정 뒤로 늦춘 engine930건
  통과 소스를 frozen release2d50548e로 빌드하고 전체 검증했다.
  HTTP2185통과17실패/skip0, 전체 반복 성능 FAIL이다.
  해당 측정 직후 root/frozen crates도 동일했다. 단위 완료가 아니다.
- 정식 수락 **0/40**. C02/C05/C06 및 daemon 미완료, ledger 제외0, 릴리즈 보류다.
- 당시 전체 성능 측정 실행 파일은 deferred bool frozen release `2d50548e`다.
  HTTP2202건 중2185성공/17실패/skip0이며 count probe는 통과했다.
  초기 적재 routing18건은 통과, 반복 갱신 routing18건은1성공/17실패로 남아 있다.
- 이전 고정 후보 소스 engine930건 통과. core17건은 공통 길이 norm 변경 때 통과했으며,
  node1123건은 이전 debug 검증 단계의 결과다. 현재 후보의 전체 node/daemon
  재검증을 완료했다고 합산하지 않는다. 변경별 해시와 실행 범위는 아래 기록에 있다.
- **전체 non-plugin 반복 성능 FAIL**: 최초 v0.6.0 대비 처리량이 단일 노드
  35.377%/35.323%, 3노드19.776%/20.650% 감소했다. 후보 반복의44지표 중25/27개가
  5% 한도를 넘었고, paired 기준으로도22/21개가 실패했다. 12개 토폴로지 실행 오류0이다.
- 기준 재측정은44/44 및37/44 통과했다. 후보 회귀를 기준 변동으로 면제하지 않는다.
  단일 ranking 평균22.192/22.240ms는 v0.6.0보다246.058%/246.803% 느리며,
  고정 OpenSearch 대비로도77.416%/80.220% 느리다. 전체 처리량 우위로 상쇄하지 않는다.
- 요청별 통계 재사용/페이지 이후 source 복제, native filter 비점수 처리,
  native match 통계/boost, 길이 norm 및 source shard 통계 분리를 반영했다.
  정확성용 source 후처리 guard는 유지한다. 이전 a1b8c3c3 대비 일부 회복됐지만
  최적화 불가능한 단일 기능 원인은 입증하지 않았으므로 제외나 예외는 없다.
- 다음은 ranking 후처리 비용 복구와 반복 갱신 점수 차이 진단이다. 변경마다
  확장 HTTP2202건 이상 및 전체 반복 benchmark를 유지하며 v0.6.0 기준을 재설정하지 않는다.
- `2d50548e` 서버 PID CPU 진단에서 문서별 점수 평가44.51%, 준비 경로10.69%,
  MultiMatch2.96%, phrase12.84%, source 필드 조회18.38%가 관측됐다.
  중첩된 CPU 비율이며 성능 회복 수치가 아니다.

- **미지원 확인**: 현재 코드가 해당 옵션을 명시적으로 거부함을 확인했다.
- **제한 구현**: 문서상 제한된 구현·비교 범위가 존재한다. 모든 변형의 결함을
  새로 재현했다는 뜻이 아니므로 구현 변경 전에 현재 동작을 확인한다.
- **재검증 필요**: 관련 구현·하네스는 있지만 현재 배포 프로파일의 충분한 증거가 없다.
- **검증체계 보강**: 프로파일, 출처, 실패 판정, 자동화 등의 작업이다.

P0는 데이터 손실·권한 우회·잘못된 합격 판정 방지, P1은 지원 기능·운영 완성,
P2는 확장·특수 연동 검증이다. P2도 해당 프로파일을 지원한다고 선언하면 필수다.

## 4. 상세 작업 목록

### G. 범위와 합격 판정: 4개

| ID | 우선순위 / 상태 | 구현·보강 내용 | 완료 증거 |
| --- | --- | --- | --- |
| G01 | P0 / 검증체계 보강 | 코어 지원 API·옵션·배포 프로파일 목록, 실제 사용 클라이언트와 대상 OpenSearch 버전/커밋 고정. 2.19.0 속도 참조와 3.7.0-SNAPSHOT 기능 참조를 혼동하지 않도록 분리 | 모든 지원 항목이 구현·테스트·근거 경로 또는 명시적인 미완료 항목에 연결됨 |
| G02 | P0 / 검증체계 보강 | 기존 aggregate gate에 코어 프로파일을 명시적으로 전달. 플러그인 관련 검사를 전 구간에서 분리하되 보안·내구성·분산 조건 유지 | 플러그인 누락은 excluded, 코어 누락은 실패, 미지의 프로파일·빈 테스트·전부 제외는 실패하는 회귀 테스트 |
| G03 | P0 / 검증체계 보강 | 버전별 CARGO_TARGET_DIR, 소스·lock·실행 파일 해시, 환경·원시 응답·시드·시간 기록. 증거의 최신성 및 잘못된 바이너리 선택 방지 | v0.6.0 캐시 혼입 사례를 재현하는 빌드 검증 및 변경/누락/오래된 증거 거부 테스트 |
| G04 | P0 / 검증체계 보강 | 기존 실행기·스키마를 사용해 아래 ID와 실제 실행 결과를 연결. 구현 단위별 전체 벤치마크와 고정 v0.6.0 대비 누적 5% 게이트를 자동화하고 초과 시 완료/승격 차단 | 빈/부분/오래된 결과와 잘못된 기준선 거부. 4.99%·5.00%·5.01% 경계, 두 번의 3% 증가, 시나리오 간 상쇄, 예외 오용에 대한 회귀 테스트 |

주요 수정 위치: `tools/run-native-closure-validation.py`,
`tools/report-release-evidence-inventory.py`, `tools/check-release-readiness-evidence.py`,
관련 테스트와 `replacement-claim-exit-criteria.md`.
새 독립 판정 시스템을 만들기보다 기존 판정을 프로파일별로 정합화한다.

### C. 코어 API와 의미 동작: 6개

| ID | 우선순위 / 상태 | 구현·보강 내용 | 완료 증거 |
| --- | --- | --- | --- |
| C01 | P1 / 제한 구현 | 선언한 REST 경로·메서드·필수/미지 옵션·null/배열/중복 키·오류 계층 검증. 실제 클라이언트의 sniffing, 압축, 재시도, bulk 오류 처리 포함 | 대상 클라이언트 버전별 계약 테스트와 정규화 전후 응답 보존; 무시되는 코어 옵션 없음 |
| C02 | P1 / 제한 구현 | 매핑·동적 매핑·타입 충돌·숫자 경계·날짜·nested/object·코어 analyzer의 토큰 및 검색 영향 검증 | 신규/기존 인덱스, 혼합 매핑, 문서 재색인 후 같은 결과; 플러그인 analyzer 제외 |
| C03 | P1 / 제한 구현 | 인덱스 설정·템플릿·alias·data stream·rollover의 원자적 메타데이터 변경. 지원하는 ingest processor와 실패 처리 조합 확대 | write alias 전환 및 동시 쓰기, 템플릿 우선순위, backing index 변경, ingest 실패 시 상태와 오류 비교 |
| C04 | P0 / 제한 구현 | CRUD·bulk 부분 성공·OCC·외부 버전·routing·refresh·by-query·reindex의 충돌, 취소, 재시도 의미 보강 | 작업별 성공/실패 항목과 최종 데이터가 원장과 일치; 비멱등 요청의 중복 실행 위험을 감추지 않음 |
| C05 | P1 / 제한 구현 | multi-index 검색·bool/nested·정렬·search_after·PIT/scroll·timeout·취소·부분 샤드 실패·rank/rescore 조합 검증 | 페이지 누락/중복 없음; 점수·동점 순서·오류에 대해 정의한 동등성 계약 통과; 정확 점수와 순위 동등성을 구별 |
| C06 | P1 / 제한 구현 | metric/bucket/pipeline 집계, 빈 버킷, 다중 샤드 reduce, 숫자 정밀도, highlight/suggest/term statistics 확장 | 참조 비교와 수학적 불변식 테스트; 재현 가능한 차이는 수정, 허용 오차는 측정 전에 명시 |

주요 수정 위치: `crates/os-node/src/standalone_runtime.rs`,
`crates/os-engine-tantivy/src/lib.rs`, `crates/os-query-dsl/src/lib.rs`,
`tools/search_compat.py`, 검색·문서 쓰기 fixture.
새 옵션은 파서 수용, 실제 실행, 응답, 오류, 자원 제한을 함께 구현한다.
파서가 받아들인다는 이유만으로 지원 완료로 표기하지 않는다.

### D. 데이터 내구성: 4개

| ID | 우선순위 / 상태 | 구현·보강 내용 | 완료 증거 |
| --- | --- | --- | --- |
| D01 | P0 / 재검증 필요 | 쓰기 승인 시점, journal/translog·fsync·refresh·flush 및 replica 확인의 계약 고정. 승인 이전 영속화 순서 보강 | 프로세스 종료·저장소 오류 시나리오에서 계약상 영속 승인된 쓰기 손실 0; 클라이언트 응답 원장과 재기동 데이터 비교 |
| D02 | P0 / 재검증 필요 | authoritative manifest와 재생성 가능한 캐시 구분, 원자적 파일 교체, 세대·checksum, 디스크 부족·부분 쓰기 처리 | 손상된 authoritative 파일에서 서비스 시작 차단; 허용된 캐시만 재구축하고 원인 기록 |
| D03 | P0 / 재검증 필요 | replay 도중 반복 종료, 중복 replay, 삭제/tombstone, 매핑·alias·버전·seq_no 복구 검증 | 여러 종료 지점과 시드에서 동일 최종 원장 및 메타데이터; 오래된 세대와 새 세대 혼합 없음 |
| D04 | P0 / 재검증 필요 | 디스크 포맷 버전, 업그레이드·호환 읽기·안전한 거부·복구 절차 구현/검증 | v0.6.0 데이터의 후보 버전 열기·업그레이드 성공; 지원하지 않는 downgrade는 사전 차단; 백업 기반 복구 검증 |

주요 수정 위치: engine/node 영속화 경로, gateway/manifest 소유 모듈,
`tools/run-node-restart-smoke.sh`, `tools/run-durability-compat.sh`.
`SIGKILL` 통과만으로 전원 손실 내구성을 주장하지 않는다. fsync 순서 검증과
저장소 장애 주입을 추가하고, 전원 단절 시험은 별도 승인된 격리 환경에서 수행한다.

### R. SteelSearch 전용 분산 일관성: 5개

| ID | 우선순위 / 상태 | 구현·보강 내용 | 완료 증거 |
| --- | --- | --- | --- |
| R01 | P0 / 재검증 필요 | 선거·quorum·term·오래된 manager 차단, minority partition의 쓰기 승인 금지 | 독립 3/5노드 프로세스의 분할·복구에서 두 manager의 상충 쓰기 승인 없음 |
| R02 | P0 / 재검증 필요 | cluster-state publication의 apply/ack 순서, 재전송, 오래된 버전 및 중복 상태 거부 | publication 단계별 crash/restart 후 노드 상태 수렴; 적용하지 않은 상태를 적용 완료로 보고하지 않음 |
| R03 | P0 / 제한 구현 | primary/replica 승인·checkpoint·retry·stale replica·primary 승격·부분 실패 처리 | 동시 쓰기와 노드 손실 후 승인 원장 보존; 불일치 replica를 최신본으로 승격하지 않음 |
| R04 | P0 / 재검증 필요 | 샤드 할당·이동·peer recovery 중 읽기/쓰기, 중단·재시도·checksum 검증 | 샤드 이동과 복구 실패를 반복해도 데이터 및 버전 수렴; 진행률과 실패 원인 확인 가능 |
| R05 | P1 / 재검증 필요 | 느린 노드·연결 끊김·partition heal, cluster-manager 작업 큐와 backpressure 복구 | 지연/손실 주입 후 제한 시간 내 복구 또는 명시적 비가용; 큐·FD·메모리 무한 증가 없음 |

주요 수정 위치: `crates/os-node/src/main.rs`, cluster-state/transport 경로,
`crates/os-node/tests/dev_cluster_daemons.rs`,
`tools/run-distributed-durability-convergence.sh`, `tools/generate-chaos-evidence.py`.
합성 peer 단위 테스트 외에 공유 메모리에 의존하지 않는 다중 daemon 시험을 필수로 한다.

### B. 백업·복원: 4개

| ID | 우선순위 / 상태 | 구현·보강 내용 | 완료 증거 |
| --- | --- | --- | --- |
| B01 | P0 / 재검증 필요 | 동시 쓰기 중 snapshot의 일관된 시점, 문서·매핑·설정·alias 보존 | 원본과 별도 데이터 경로의 새 클러스터에 복원 후 ID·내용·메타데이터 및 핵심 검색 결과 비교 |
| B02 | P1 / 미지원 확인 | `source_remote_store_repository`, `source_remote_translog_repository`, 비-local `storage_type` 복원 구현 | 실제 대상 저장소의 참조 fixture, 중단/손상/접근 실패 및 복원 후 읽기·쓰기 검증 |
| B03 | P1 / 미지원 확인 | `attach_to_data_stream`, 지원 범위의 `feature_states`, 비기본 `expand_wildcards`와 rename/alias/global-state 조합 구현 | backing index 연결과 write index 불변식, 선택 범위·메타데이터 충돌·롤백 검증; 플러그인 feature state 제외 |
| B04 | P1 / 제한 구현 | PARTIAL snapshot/clone, 누락·손상된 shard manifest의 실패 상세, 정리·재시도 처리 | 참조 환경에서 재현한 부분 실패 fixture와 정확한 상태·실패 샤드·원인 비교 |

B02/B03의 거부는 현재 `standalone_runtime.rs`의 snapshot restore 옵션 검증에서
확인했다. 저장소 backend가 플러그인에만 제공되는 경우 그 플러그인 자체를
구현 대상으로 다시 넣지 않는다. G01에서 대상 저장소 형식과 원격 복원 계약을
고정하고, 적용 불가능한 항목은 이유를 기록하되 미구현 기능을 통과로 세지 않는다.
주요 도구: `tools/snapshot_lifecycle_compat.py`, snapshot fixture와 promotion gate.

### S. SteelSearch 자체 운영 보안: 4개

| ID | 우선순위 / 상태 | 구현·보강 내용 | 완료 증거 |
| --- | --- | --- | --- |
| S01 | P0 / 설정 연결 수정 중, 운영 검증 미완료 | HTTP/transport TLS, 인증서 검증·만료·회전, 사용자/서비스 계정 인증. 검증된 사용자 파일과 실제 인증 경로 일치 | 공식 환경변수/CLI 사용자 파일 모두 실제 인증에 적용; 잘못된 인증서·토큰·누락 자격 증명에서 거부; 운영 모드에서 평문 우회 없음 |
| S02 | P0 / 재검증 필요 | cluster/index 권한과 alias/data stream/wildcard 해석, bulk·snapshot·admin 경로의 일관된 권한 검사 | 허용/거부 행렬과 교차 tenant 누출 검사; 필드/문서 보안이 요구되는데 미지원이면 거부 |
| S03 | P0 / 재검증 필요 | secure settings·로그·오류·snapshot의 비밀정보 제거, 감사 로그와 요청 상관관계 | 각 유출 경로의 부정 테스트, 권한 거부 및 민감 변경에 대한 감사 증거 |
| S04 | P0 / 검증체계 보강 | 코어 운영 보안 경계와 플러그인 보안 API 조건 분리, 설정 존재가 아닌 실제 enforcement로 readiness 판단 | 필수 보안 경계를 하나씩 제거하면 startup/readiness 실패; 제외 조건을 가짜 Enforced로 채우지 않음 |

기존 보안 문서는 플러그인 요구와 자체 보안 요구를 함께 포함하므로 그대로
코어 합격 기준으로 사용하지 않는다. 현재 구현을 감사한 뒤 필요한 경계만 수정한다.
주요 도구: `tools/run-security-compat-harness.sh`,
`tools/check-security-redaction-smoke.sh`, `tools/check-security-audit-correlation.py`.

### O. 운영·배포: 3개

| ID | 우선순위 / 상태 | 구현·보강 내용 | 완료 증거 |
| --- | --- | --- | --- |
| O01 | P1 / 재검증 필요 | 설치·실행·업그레이드·graceful shutdown, 설정 검증, 최소 지원 OS/아키텍처별 패키지 | 깨끗한 환경에서 설치·시작·중지·데이터 유지; 소스 릴리즈와 검증된 배포 패키지 구별 |
| O02 | P0 / 재검증 필요 | old/new 혼재 순서, drain, shard 이동, 읽기/쓰기 지속, 업그레이드 중단 및 복구 | 지원 버전 조합별 rolling 시나리오; 손실 0 및 사전에 정한 오류/지연 예산 충족 |
| O03 | P1 / 재검증 필요 | 실제 자원·큐·거절·recovery 진행·readiness 지표, 경보와 운영 runbook | 인위적 장애가 health/metrics/log에 정확히 나타나고 문서 절차만으로 복구 가능 |

주요 도구: `tools/generate-packaging-evidence.py`,
`tools/generate-rolling-upgrade-evidence.py`, `tools/run-rolling-stability-gate.sh`.
정상 응답 형태만 만드는 stats와 실제 상태를 측정한 지표를 구분한다.

### P. 성능과 자원 상한: 4개

| ID | 우선순위 / 상태 | 구현·보강 내용 | 완료 증거 |
| --- | --- | --- | --- |
| P01 | P0 / 검증체계 보강 | 동일 내구성·복제 승인·refresh·보안·자원 제한을 사용한 운영 비교 프로파일 추가 | 실제 실행 설정과 바이너리 해시를 기록; 개발용 지연 쓰기 결과와 별도 표로 보고 |
| P02 | P1 / 재검증 필요 | 7개 코어 시나리오, 혼합/고정 corpus, cold/warm, 작은/중간/실제 규모, 동시성·shard 수별 측정 | 처리량·평균·p95·p99·오류·RSS/CPU/IO/FD, 인덱스 크기와 문서 증가량을 함께 저장 |
| P03 | P0 / 재검증 필요 | 정렬 지연 쟁점 재현·프로파일링·수정, 반복 순서 균형 및 사전 정의한 통계 판정. 이후 각 구현 단위의 누적 비용을 최초 v0.6.0과 비교 | 전체 필수 시나리오에서 누적 회귀 5% 이내; 직전 단위만 비교하거나 유리한 실행만 선택하지 않음 |
| P04 | P1 / 재검증 필요 | 단계별 soak·장애 중 부하·포화점·OOM/디스크 부족·취소·과부하 거절 검증 | 제안 단계 1시간 → 6시간 → 24시간에서 누수·무한 backlog 없음; SLA와 복구 예산은 사전 확정 |

기존 `tools/run-search-benchmark-matrix.py`와 HTTP load 도구를 확장한다.
누적 회귀의 최초 비교 기준은 v0.6.0으로 고정하며 이후 릴리즈에서도 바꾸지 않는다.
릴리즈 노트의 별도 직전 공개 버전 비교만 매 릴리즈 갱신한다. 고정 OpenSearch
비교도 함께 유지한다. 기존 개발 기준선의 불리한 관측은 역사적 증거로 보존하되,
새 구현의 사용자 지정 5% 합격 기준은 v0.6.0에 적용한다.
프로파일러가 붙은 결과는 속도 판정에서 제외하고, 경쟁 빌드/부하 없이 측정한다.
평균과 percentile을 임의로 합치거나 서로 다른 부하의 결과를 pooling하지 않는다.
반복 측정 횟수·통계 절차·중단 규칙은 결과를 보기 전에 정한다.
사용자 지정 누적 회귀 한도는 5%다. 처리량과 평균/p95/p99를 각각 검사하며
개선된 지표로 다른 지표의 초과를 상쇄하지 않는다. 측정 변동성이 있다는 이유만으로
초과를 무시하지 않는다. 정확한 판정·재측정 절차는 아래 5.1절에 따른다.

### M. 실제 서비스 이전: 3개

| ID | 우선순위 / 상태 | 구현·보강 내용 | 완료 증거 |
| --- | --- | --- | --- |
| M01 | P0 / 재검증 필요 | 비식별화한 실제 매핑·데이터·요청·클라이언트 수집, snapshot 또는 재색인 이전 경로 선택 | 핵심 업무별 입력 corpus와 예상 결과, 금지된 데이터·비밀정보 유입 검사 |
| M02 | P0 / 재검증 필요 | shadow read와 독립 쓰기 원장으로 기능·정렬·집계·오류·지연 비교 | 합의한 관찰 기간에 설명되지 않은 차이 없음; 비멱등 요청을 운영 양쪽에 무분별하게 재전송하지 않음 |
| M03 | P0 / 재검증 필요 | 초기 복사·증분 반영·최종 write fence·전환·역전환 및 RPO/RTO 검증 | 승인된 격리/스테이징 환경의 전환 리허설과 데이터 검증; 운영 전환은 별도 승인 |

주요 도구: `tools/run-migration-acceptance-harness.sh`,
`tools/run-migration-rehearsal.sh`, `tools/migration_cutover_integration.py`.
OpenSearch와 SteelSearch가 같은 디스크 포맷을 직접 읽을 수 있다고 가정하지 않는다.
지원 snapshot import 형식이 없으면 문서화된 재색인/내보내기 경로를 검증한다.

### I. OpenSearch와의 연동: 3개

| ID | 우선순위 / 상태 | 구현·보강 내용 | 완료 증거 |
| --- | --- | --- | --- |
| I01 | P2 / 제한 구현 | 외부 forwarding의 allowlist, handshake/version skew, stale cache, disconnect와 재시도 | 허용하지 않은 action과 stale metadata를 명시적으로 거부; 실제 외부 노드 transcript |
| I02 | P2 / 제한 구현 | 동일 클러스터 가입, Java peer의 publication/apply/ack, 할당·복구·쓰기 복제 연결 | 지원 버전의 실제 Java 노드와 Rust 노드가 상태·데이터·승인 계약에 수렴 |
| I03 | P2 / 재검증 필요 | 혼합 노드 장애·partition·재가입·rolling 조합 | R01-R05 불변식을 혼합 토폴로지에서도 통과; happy-path handshake만으로 승인하지 않음 |

주요 도구: `tools/run-phase-b-gap-harness.sh`, `tools/run-phase-c-gap-harness.sh`,
`tools/run-phase-c-mixed-cluster-harness.sh`.
이 단계가 미완료이면 독립 클러스터 대체와 혼합 노드 대체의 판정을 분리한다.

## 5. 구현 순서와 의존관계

| 단계 | 대상 | 진입 조건 | 산출물 / 종료 조건 |
| --- | --- | --- | --- |
| A. 기준 고정 | G01-G04, P01 설계, M01 수집 계획 | 현재 소스와 릴리즈 증거 확보 | 프로파일별 실행 목록, 출처/최신성 검사, 대상 버전·부하 계약. 미지 항목은 미완료로 남김 |
| B. 데이터 안전 | D01-D04, R01-R03, B01, S01-S04 핵심 경계 | A | 승인 데이터 보존·재생·quorum·권한 부정 테스트. 재현된 실패를 먼저 수정 |
| C. 기능/분산 완성 | C01-C06, R04-R05, B02-B04, O01-O03 | 각 항목의 B 의존성 | 코어 지원 목록의 미지원·차이 항목 종결, 복원/rolling 검증. 독립 API 항목은 B와 병행 가능 |
| D. 부하/전환 검증 | P01-P04 실행, M01-M03 | 해당 프로파일의 B/C 통과 | 실제 workload, soak, 장애 부하, 전환 리허설. 안전성 실패가 나오면 B/C로 복귀 |
| E. 혼합 연동 | I01-I03 | 관련 R/D/S 완료 및 혼합 프로파일 필요성 확정 | 외부 연동/혼합 노드 별도 승격 증거 |

순수 SteelSearch 클러스터 대체의 핵심 경로는 A → B → C → D다.
혼합 노드 대체는 E까지 추가된다. 성능 검증은 마지막에만 하지 않는다.
모든 구현 단위가 끝날 때 플러그인 제외 전체 벤치마크를 실행하며,
D에서는 이에 더해 장시간 부하·장애·실제 전환 검증을 수행한다.

각 작업은 다음 단위로 나누어 PR 또는 변경 묶음을 만든다.

1. 현재 동작과 참조 차이를 재현하는 최소 실패 테스트 및 원시 응답.
2. 관련 모듈에 한정한 구현 변경과 오류/취소/재시도 처리.
3. 단위·통합·live 비교와 전체 코어 벤치마크 실행. 국소 벤치마크는 추가 진단이다.
4. 최초 v0.6.0 대비 시나리오별 누적 회귀를 판정. 초과는 원인 분석·최적화 후 전체 재실행.
5. 해당 ID 상태, 실행 명령, 바이너리 해시, 결과 및 남은 한계 갱신. 통과 또는 승인된 예외가 없으면 구현 완료로 처리하지 않음.

재현되지 않은 추정 결함에 대한 대규모 재설계는 하지 않는다. 반대로 파서 수용,
성공 코드, fixture 존재만으로 실제 실행·영속화·분산 동작을 대체하지 않는다.

### 5.1 모든 구현 단위에 적용할 누적 성능 게이트

**고정 기준선**은 최초 v0.6.0 태그와 그 실행 파일이다.
소스 태그는 `cbb5866ed32771ca326eb5d004569c4c884929ca`, 측정 실행 파일은
`db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`이다.
최초 공개 측정은 `docs/releases/v0.6.0/current.json`에 보존한다.
이후 v0.6.x/v0.7.x를 공개하더라도 누적 성능 기준선을 이동시키지 않는다.

G01-G04부터 각 구현 단위의 완료 체크리스트에 아래 실행을 포함한다.
여러 기능을 한 묶음으로 승인받지 않았다면 중간 단위의 전체 검증을 생략하지 않는다.

1. 단위·통합·live 기능 테스트를 통과시킨 최종 후보 바이너리를 고정한다.
2. v0.6.0과 후보, 고정 OpenSearch를 같은 호스트·작업량·내구성·보안·자원 조건에서
   실행한다. 버전별 빌드 디렉터리를 분리하고 실제 프로세스 해시를 확인한다.
3. **최소 전체 범위는 7개 코어 연산 × 단일/3노드**다. write, lexical, ranking,
   facet, sort_filter, nested, refresh를 모두 포함하고 plugin/vector/hybrid는 제외한다.
   세 비교 대상의 두 토폴로지를 모두 실행한다. 이후 추가한 필수 부하 프로파일도
   전체 목록에 포함하며, 변경한 기능의 벤치마크만 실행해서 대신하지 않는다.
4. 최초 공개 프로파일(5,000문서, 4클라이언트, 3shard, 0/1replica, seed 13,
   384-value source, 60초, weights 15/15/15/15/10/10/5)을 계속 유지한다.
   운영 내구성 프로파일은 별도로 양쪽을 재측정하며 개발 프로파일과 합치지 않는다.
5. 결과를 v0.6.0 대비 누적 차이로 판정한다. 직전 구현 대비 차이도 원인 추적용으로
   함께 기록하지만 합격 여부를 대체하지 않는다. 릴리즈 시에는 추가로 직전 공개
   릴리즈 대비 표를 유지한다.
6. 하나라도 5%를 초과하면 병목 분석 → 수정 → 전체 벤치마크 재실행을 한다.
   성능만 개선하려고 정합성·영속화·보안 기능을 비활성화하지 않는다.

| 지표 | 누적 악화율 | 정상 합격 조건 |
| --- | --- | --- |
| 토폴로지별 전체 처리량 T | `(T_v060 - T_current) / T_v060 * 100` | 각 토폴로지에서 `T_current >= 0.95 * T_v060` |
| 시나리오별 평균 지연 L | `(L_current / L_v060 - 1) * 100` | 14개 행 각각 `L_current <= 1.05 * L_v060` |
| 시나리오별 p95/p99 지연 | 같은 지연 계산식, percentile마다 별도 | 각 시나리오·토폴로지·percentile이 각각 5% 이내 |

성능 개선은 악화율이 음수로 나타난다. 표의 반올림 값이 아닌 원시 수치로 판정하고,
정확히 5%는 이내, 5% 초과는 실패다. 혼합 부하의 연산별 요청 수/초는 연산 선택
비율의 영향을 받으므로 독립적인 연산 처리량으로 오해하지 않는다.

예: 최초 평균 지연 10ms에서 기능 A 후 10.3ms, 기능 B 후 10.609ms라면
각 변경은 3%씩이어도 누적 6.09%이므로 실패다. 다른 시나리오가 20% 빨라졌거나
단일 노드가 개선되어도 해당 3노드/시나리오 초과를 상쇄할 수 없다.

**측정 변동과 기준선 관리**

- 최초 공개 보고서는 수정하지 않는다. 같은 v0.6.0 실행 파일의 새 paired 측정은
  별도 보존하고 기존 공개 수치와의 변동도 보고한다. 후보를 기준선으로 바꾸지 않는다.
- 기준선과 후보 실행 순서, 반복 횟수, 통계 요약과 추가 측정 조건을 사전에 고정한다.
  5% 경계에서 결과가 불확실하면 판정 보류 및 사전 규칙에 따른 재측정을 하며,
  유리한 실행만 고르거나 통과할 때까지 반복하지 않는다.
- G04 반복 실행기 `tools/run_core_performance_gate.py`의 최초 절차는
  `기준선 → 후보 → OpenSearch → OpenSearch → 후보 → 기준선`으로 고정한다.
  각 단계에서 단일/3노드 전체 코어를 실행하므로 각 대상은 2회, 총 12개 실행이다.
  첫 세 단계와 역순의 마지막 세 단계를 각각 paired 비교한다. 후보의 모든 개별
  실행을 공개 v0.6.0과 paired v0.6.0에 비교하며, 새 v0.6.0 실행의 공개 수치 대비
  변동도 별도 검사한다. 어느 검사든 5% 초과이면 수치 판정 실패다.
  percentile은 개별 실행 값만 사용한다. 수치 실패여도 예정된 실행을 모두 마치며,
  인프라 실패는 즉시 중단해 원본을 보존한다. 자동 재시도는 없고 실행 폴더 재사용을
  거부한다. 계획 JSON을 부하 전에 저장하고 실행/보고서 해시를 결과에 연결한다.
  현재 실행기는 수치/증거 정합성만 판정하며 실제 enforcement와 소스-빌드 연결이
  완성되기 전까지 구현 승인을 발급하지 않는다.
- 평균은 실제 sample count를 검증하고 percentile은 원시 샘플 또는 개별 실행 값으로
  처리한다. p95/p99를 평균 내어 가상의 percentile을 만들지 않는다.
- CPU profiler·다른 load generator·빌드와 합격용 측정을 동시에 실행하지 않는다.
- 새 하드웨어·데이터·내구성 설정을 도입하면 같은 v0.6.0도 동일 조건에서 실행한다.
  환경 변경으로 기존 회귀가 사라진 것처럼 보고하지 않고 종전 필수 프로파일을 유지한다.
- v0.6.0에 없는 신규 기능은 가짜 baseline/N/A 통과를 만들지 않는다. 공통 코어
  시나리오는 계속 5%를 검사하고, 신규 기능 자체의 비용·SLA는 별도 측정/승인한다.
- 실행 파일이 동일한 도구-only 단위에서는 동일성을 사실대로 기록한다. 허위로
  다른 해시를 만들거나 이를 최적화 효과라고 설명하지 않는다.
- 오류·timeout·결과 오류로 요청이 줄어 빨라진 실행은 성능 합격으로 인정하지 않는다.
  RSS/CPU/IO/FD와 데이터 증가량도 보고하되 메모리까지 자동으로 5% 한도로
  해석하지 않고 별도 자원/누수 예산을 적용한다.

**불가피한 기능 비용의 예외**

2026-09-07 실행 지시: 단일 구현이 5% 이상 성능 저하를 유발하고 최적화로
해결하지 못한 경우 [제외 ledger](core-replacement-exclusion-ledger-2026-09-07.md)에
근거를 등록한 뒤 해당 구현을 우선 제외한다. 단일 변경의 영향은 직전 구현 대비,
전체 누적 영향은 최초 v0.6.0 대비로 각각 기록한다. 누적 5% 초과만으로 특정
단일 변경이 5% 이상을 유발했다고 단정하지 않는다. 제외 후에도 전체 벤치마크를
재실행하며, 해당 기능은 미완료로 남긴다. 제외를 이유로 안전성 조건을 없애지 않는다.
아래 승인 절차는 초과 구현을 제외하지 않고 유지하려는 경우에 적용한다.

기능 구현에 본질적으로 필요한 비용으로 보이면, 빠른 미구현/오동작 상태를
유지하는 대신 아래 정보를 제출하고 사용자 승인을 받아 해당 범위만 예외 처리한다.

- 기능의 필요성과 비용 발생 경로, v0.6.0 대비 실제 증가량 및 영향을 받는 행.
- 동일 결과·내구성·보안을 유지하는 최적화 대안과 각각의 실험 결과.
- 기능별 비용 분리 진단과 최종 전체 벤치마크, 오류·자원 영향.
- 예외 대상 기능/프로파일/지표, 허용 상한, 완화 또는 재검토 조건.

예외는 `approved-exception`으로 표시하고 일반 `passed`로 합치지 않는다.
최초 v0.6.0 기준선과 실제 누적 증가율을 그대로 유지하며, 다른 연산/후속 변경에
예외를 자동 확장하지 않는다. 설명만으로 5% 초과를 자동 허용하지 않는다.

**단위별 필수 보고서**

`구현 ID / 소스 커밋 / 실제 바이너리 SHA / v0.6.0 SHA / 설정 fingerprint /
반복 순서 / 전체 raw reports / 기준선·후보·OpenSearch 수치 / 직전 구현 대비 /
v0.6.0 대비 누적 % / 오류 및 자원 지표 / 병목 조치 / 최종 판정 / 예외 승인 근거`를
기록한다. 자동 게이트 G04 구현 전에도 이 체크리스트를 수동으로 적용하며,
현재 릴리즈 노트 포맷 검증기가 누적 5%까지 이미 자동 차단한다고 주장하지 않는다.

## 6. 완료 판정

- 지원 범위의 모든 항목이 최신 실제 바이너리의 증거에 연결되고 필수 실패·누락이 없다.
- 플러그인 제외 항목은 별도로 표시되며 통과 건수에 포함되지 않는다.
- 승인된 내구성 계약에서 쓰기 손실·권한 우회·설명되지 않은 데이터 불일치는 0이다.
- 시작 전 readiness와 실행 중 실패 처리가 실제 상태를 반영한다.
- 해당 프로파일의 backup/restore, rolling, chaos, migration 리허설이 통과한다.
- 각 구현 단위의 전체 벤치마크가 있고, 최초 v0.6.0 대비 시나리오별 누적 회귀가
  5% 이내다. 별도 승인 예외는 일반 통과와 구별하며 자원 예산도 검증한다.
- 운영자가 복구·전환·역전환 절차를 실행할 수 있고, 명시한 RPO/RTO를 검증한다.
- 특정 서비스의 완료와 일반 코어 대체품의 완료는 서로 다른 판정으로 남긴다.

40개 패키지 수를 분모로 단순 완료율을 계산하지 않는다. 문서 작성 1건과
복제 일관성 입증 1건은 같은 양의 일이 아니다. 단계별 필수 항목 완료 여부,
실패 시나리오 수, 증거 미확보 항목, 구현 완료/검증 완료를 나누어 보고한다.

## 7. 착수 시 확정할 입력

구현 감사와 로컬 회귀 테스트는 바로 진행할 수 있다. 실제 대체 승격에는 아래
입력이 필요하며, 없는 값을 임의의 합격 조건으로 채우지 않는다.

| 입력 | 필요한 이유 | 확정 전 가능한 작업 |
| --- | --- | --- |
| 실제 OpenSearch 버전·클라이언트·사용 API/옵션 | 동등성 기준과 지원 범위 확정 | 현재 fixture와 코드 인벤토리, 버전별 차이 목록 |
| 문서 수·문서 크기·색인/조회율·동시성·shard/replica | 대표성 있는 성능/용량 시험 | 고정 synthetic profile과 측정 출처 검증 |
| 배포 프로파일·보안·저장소·백업 방식 | 필수 운영 및 저장소 항목 결정 | 자체 클러스터 안전성/기본 보안/로컬 복원 검증 |
| SLA·RPO/RTO·반복 측정 세부 계약 | 중단·복구·성능의 객관적 합격 판정; 누적 5% 한도는 이미 확정 | 데이터 보존 불변식과 고정 v0.6.0 성능 게이트 구현 |
| 비식별 운영 데이터 및 격리 시험 환경 | 실제 트래픽과 장애/전환 리허설 | 공개 fixture 기반 검증 및 하네스 보강 |

총 기간은 현재 문서만으로 확정하지 않는다. A에서 실제 미지원·구현 결함·증거
부족을 분류하고, D/R의 대표 장애 사례를 먼저 실행한 뒤 단계별 작업량을 다시
산정한다. 현재 상태를 근거 없이 며칠/몇 주면 전체 대체 가능하다고 약속하지 않는다.

## 8. 참조 문서

- [대체 프로파일 종료 기준](replacement-claim-exit-criteria.md)
- [API 구현 원장과 Open Items](opensearch-api-gap-implementation-ledger-2026-08-30.md)
- [검색 파라미터 매트릭스](../api-spec/search-parameter-coverage-matrix.md)
- [문서 쓰기 의미 매트릭스](../api-spec/document-write-semantic-gap-matrix.md)
- [snapshot/restore 매트릭스](../api-spec/snapshot-restore-completeness-matrix.md)
- [gateway replay 정책](gateway-replay-recovery-policy.md)
- [디스크 포맷 변경 경계](on-disk-state-upgrade-boundary.md)
- [다중 노드 실패 인벤토리](coordination-multi-node-failure-test-gap-inventory.md)
- [운영 보안 기준: 코어/플러그인 분리 감사 필요](production-security-baseline.md)
- [Phase C 연동 기준](phase-c-peer-node-compat.md)
- [릴리즈 성능 표 정책](../releases/README.md)

## 9. 실행 기록

### G04: 계산·보고서 검증 계층 구현 중 (2026-09-07)

- `tools/core_performance_budget.py`: 2개 처리량과 14개 시나리오의 평균/p95/p99,
  총 44개 수치를 개별 비교한다. Decimal로 5% 경계를 검사하고 상쇄하지 않는다.
- `tools/test_core_performance_budget.py`: 10개 테스트 통과. 전체 지표별 경계,
  두 번의 3% 증가, 빈/누락/플러그인 지표, 비유한 값, 입력 변경 방지를 검사한다.
- 이 계층은 수치만 검사하므로 항상 `acceptance_established=false`다.
  실제 v0.6.0 해시·원시 카운트·설정·전체 실행 증거를 검증하지 않은 숫자로
  구현 완료나 운영 승격을 승인하지 않는다.
- `tools/core_performance_reports.py`: 원시 matrix 보고서의 두 토폴로지, 7개 연산,
  실제 실행 설정, 성공/전체/지연 sample count, 처리량 계산, 실행 시간, p95/p99
  순서와 양쪽 실행 파일 해시를 검사한다. 기준선 해시는 v0.6.0으로 고정하며
  OpenSearch 2.19.0 참조 보고서도 별도로 검증한다.
- 이 CLI는 원시 파일 내용의 SHA-256을 결과에 남기며 JSON 중복 키, 누락/추가
  토폴로지, plugin 부하, diagnostic 보고서, 잘못된 후보/기준선 해시를 거부한다.
  출력 파일이 입력 파일 경로와 같은 경우에는 입력을 덮어쓰지 않고 거부한다.
- CLI 종료 코드는 0=보고서 정합성/수치 예산 통과, 1=수치 예산 초과,
  2=보고서 입력 오류다. 코드 0도 구현 완료 승인은 아니다. 실제 실행 환경,
  최신 전체 실행 provenance, 소스-실행 파일 연결 및 반복 절차는 아직 미검증으로
  명시하고 `acceptance_established=false`를 유지한다.
- 계산/보고서 테스트 합계 28개, 기존 release policy 24개, benchmark tools 30개가
  통과했다. 공개 v0.6.0 보고서의 동일 파일 비교는
  `target/core-replacement-g04/published-artifact-self-check.json`에 기록했으며,
  이는 CLI 검증이지 새로운 성능 측정이나 코드 최적화 결과가 아니다.
- 위 계산/보고서 계층 작성 시점에는 전체 벤치마크를 실행하지 않았다.
  이어서 진행한 환경 수집 및 첫 전체 측정 결과는 아래 기록과 같다.

보고서 검증 CLI 사용 예(전체 실행 승인과 별개):

```sh
python3 tools/core_performance_reports.py \
  --baseline docs/releases/v0.6.0/current.json \
  --candidate docs/releases/v0.6.0/current.json \
  --opensearch docs/releases/v0.6.0/opensearch.json \
  --candidate-sha256 db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57 \
  --output target/core-replacement-g04/published-artifact-self-check.json
```

### G04: 실행 환경 수집과 첫 전체 측정 (2026-09-07)

- `tools/benchmark_runtime_evidence.py`와 matrix의 `--capture-runtime-evidence`를
  추가했다. 부하 실행 전후에 실제 프로세스 실행 파일 SHA-256, PID/start ticks,
  선택된 내구성/보안 환경 변수와 CLI 옵션, affinity/rlimit/cgroup 소속을 기록한다.
  OpenSearch는 컨테이너 ID/image ID, 시작 시각/재시작 횟수, 선택된 보안 환경,
  요청한 heap 크기와 Docker 자원 설정을 기록한다. 전체 환경/명령행은 복사하지 않는다.
- 예상 노드 수, 중복 노드, 실행 전후 신원/선택 설정 변경은 거부한다.
  기존 결과 재사용(`--skip-existing`, `--aggregate-only`)과 환경 수집의 조합도 거부한다.
  보고서 검증기에 환경 증거가 있으면 노드 수/PID/실행 파일 또는 고정 이미지 해시,
  전후 순서/변경을 검사한다. 기존 공개 보고서에는 환경 증거가 없으므로 이것만으로
  전체 구현 승인을 주장하지 않는다. 부하 실행기 실패 코드/오류가 남은 보고서는
  수치가 정상이어도 거부하도록 보강했다.
- 첫 실행 원본: `target/core-replacement-g04/runtime-capture-first/summary.json`.
  SHA-256: `006033b33562751abcbd9bec16b1891347ecf848c862254d5e50aa515df91c02`.
  모든 7개 코어 연산을 포함한 60초 혼합 부하를 양 엔진의 단일/3노드에 실행했다.
  5,000문서, 4클라이언트, 3 shard, replica 0/1, seed 13이며 플러그인 부하는 없다.
  4개 실행 모두 요청 오류 0, 환경 증거의 전후 노드/선택 설정 동일, 실행기 종료 코드 0이다.
  실행한 서버/컨테이너 종료를 확인했고 기존 무관한 서비스는 유지했다.

| 토폴로지 | SteelSearch 처리량 (ops/s) | OpenSearch 처리량 (ops/s) |
| --- | ---: | ---: |
| 단일 노드 | 744.922 | 279.475 |
| 3노드 | 910.603 | 112.039 |

- SteelSearch 양 실행의 실제 바이너리 해시는 고정 v0.6.0의 `db244133...f1f57`과
  정확히 일치한다. 런타임 기능 변경/최적화 결과가 아니라 환경 수집 경로의 실제 실행이다.
  공개 v0.6.0 기준선과 비교한 `budget-check.json`은 보고서 정합성 통과이나
  **누적 수치 예산 실패**다. 44개 중 3노드 ranking p95는 8.035836 → 8.469208 ms
  (+5.392986%), p99는 11.304207 → 12.184490 ms (+7.787216%)로 초과했다.
  나머지 42개는 5% 예산 이내다. 초과를 잡음으로 간주해 통과 처리하지 않았다.
- 같은 바이너리의 관측이므로 특정 기능 추가가 저하를 유발했다는 인과 증거는 없다.
  최적화 불가도 입증하지 않았으므로 제외 ledger에 기능 제외를 등록하지 않는다.
  이 실패 원본을 보존하고 유리한 재실행으로 대체하지 않는다.
- 계산/보고서 테스트 33개, benchmark 도구 테스트 36개 통과.
  환경 증거가 존재해도 `acceptance_established=false`를 유지한다.
- **G04 미완료**: 실제 cgroup 상위 제한, JVM 실제 heap 및 애플리케이션 보안/내구성
  enforcement, 소스-바이너리 provenance, 사전 고정 반복 절차와 같은 시점의 기준선
  실행 연결이 남았다. 공개 측정값을 바꾸거나 5% 경계를 완화하지 않고, 반복 절차를
  먼저 고정한 뒤 현재 환경의 기준선/후보 전체 측정을 연결해야 한다.

### G04: 사전 고정 반복 실행기와 A/A 측정 (2026-09-07)

- `tools/run_core_performance_gate.py`가 5.1절의 6단계/12개 실행을 수행한다.
  부하 전에 순서/명령/바이너리 해시/호스트/도구 해시/판정 정책을 `plan.json`에
  저장한다. v0.6.0 해시가 아닌 기준선과 기존 실행 폴더는 거부한다.
  각 단계 전후에 선택 바이너리 해시를 재검사하고 원시 보고서 SHA-256과 종료
  코드를 기록한다. 수치 초과 시 자동 재시도 없이 12개 실행을 완료한 후 코드 1,
  실행/입력 오류는 코드 2로 종료한다. 코드 0도 구현 승인과는 구별한다.
- `tools/test_core_performance_gate.py`의 7개 테스트는 고정 순서/전체 부하,
  두 번째 반복의 실패 은폐 방지, paired 기준선 악화로 공개 기준을 대체하지 않음,
  누락/환경 증거 없는 결과 거부, 준비 모드 무실행/폴더 재사용 거부,
  수치 실패 후 전체 실행 유지와 인프라 실패 즉시 중단/기록 보존을 검사한다.
- 실행 명령:

```sh
env STEELSEARCH_BASE_HTTP_PORT=26280 STEELSEARCH_BASE_TRANSPORT_PORT=27280 \
  python3 tools/run_core_performance_gate.py \
  --baseline-binary target/release/steelsearch \
  --candidate-binary target/release/steelsearch \
  --output-dir target/core-replacement-g04/repeated-runtime-first
```

- 기준선과 후보 모두 실제 v0.6.0 해시의 동일 바이너리다. 전체 12개 토폴로지
  실행의 요청 오류는 0, 6개 matrix 종료 코드는 모두 0이다. 마지막 수치 판정은
  **실패(종료 코드 1)**이며 `acceptance_established=false`다.
  아래는 모든 초과 항목이며 각 행의 비교 지점은 서로 다르다.

| 반복 | 비교 지점 | 초과 지표 | 악화율 |
| --- | --- | --- | ---: |
| 1 | 같은 반복의 v0.6.0 → 후보 | 3노드 nested p99 | 9.245323% |
| 1 | 공개 v0.6.0 → 후보 | 3노드 nested p99 | 8.771999% |
| 1 | 공개 v0.6.0 → 새 v0.6.0 측정 | 3노드 lexical p99 | 5.991789% |
| 2 | 같은 반복의 v0.6.0 → 후보 | 단일 노드 nested p95 | 6.258823% |
| 2 | 같은 반복의 v0.6.0 → 후보 | 3노드 facet p99 | 6.183261% |
| 2 | 공개 v0.6.0 → 후보 | 3노드 facet p99 | 9.235848% |
| 2 | 공개 v0.6.0 → 새 v0.6.0 측정 | 단일 노드 refresh p99 | 5.884207% |
| 2 | 공개 v0.6.0 → 새 v0.6.0 측정 | 3노드 ranking p99 | 6.224706% |

- 원본/판정: `target/core-replacement-g04/repeated-runtime-first/`.
  `plan.json` SHA-256: `da46ecca5085116443b1f10bd05e0ca4fe40c3f50d741137570631e35de485e4`.
  `result.json` SHA-256: `fbf2ff3d0af57a7a7a0b6e1f3a27d7fe8d00e11cc6bcd35135a859acb5f52ea5`.
  원시 6개 summary의 경로/해시는 result의 runs에 연결했다. 앞선 첫 환경 수집
  실행의 ranking 초과 기록도 그대로 보존한다.
- 같은 바이너리의 반복 간 변동을 실제로 관측했으나 원인은 아직 미확정이다.
  특정 기능의 추가 비용/최적화 불가를 입증한 것이 아니므로 ledger 제외 항목은
  추가하지 않는다. 변동이라는 이유로 예산을 완화하거나 가상의 percentile을
  만들지 않으며, 통과할 때까지 자동 재실행하지 않는다.
- 종료 후 관련 프로세스와 소유 컨테이너가 남지 않았음을 확인했다. 기존 별도
  서비스는 유지했다. 계산/보고서/반복 실행기 40개, benchmark 도구 36개,
  release 도구 54개 테스트가 통과했다.
- **G04 미완료**: 반복 절차와 실제 전체 실행 연결은 추가했지만 소스-빌드 출처,
  실제 적용되는 자원 제한 및 보안/내구성 검증, 구현 ID/전체 필수 프로파일 연결이
  남았다. 다음 측정 전에 환경/자원 관측을 보강해 변동 원인을 조사한다.

### G04: cgroup 계층 관측 보강 (2026-09-07)

- `tools/benchmark_cgroup_evidence.py`를 환경 수집기에 연결했다. cgroup v2의
  현재 프로세스 소속부터 보이는 루트까지 CPU quota/weight, memory max/high/swap,
  pids, effective cpuset, I/O 제한을 기록한다. 상위 제한을 누락한 Docker 요청
  설정만으로 실제 자원 조건이 같다고 판단하지 않는다.
- throttling/OOM/메모리 사용량/I/O/pressure 카운터는 설정과 별도 필드에 기록한다.
  전후 카운터 증가는 허용하되 설정/소속/PID 시작 시각의 변경은 거부한다.
  수집 구간은 기존과 동일하게 부하 전후이며, 측정 중 폴링은 추가하지 않았다.
- 파일 누락/권한 오류는 값 `null`과 오류 종류로 남기며 무제한으로 바꾸지 않는다.
  v1 또는 보이는 전체 루트 mount가 없는 환경은 불충분한 관측으로 명시한다.
  경로 이탈, symlink escape, 수집 중 소속 변경은 거부한다. 네임스페이스 밖의
  숨겨진 상위 제한이나 실제 사용 가능한 자원량까지 검증했다고 주장하지 않는다.
- 실제 수집기 프로세스 진단을
  `target/core-replacement-g04/cgroup-self-observation.json`에 기록했다.
  5개 계층을 관측했고 하위에서 없는 cpuset 파일이 상위에서는 `0-2`로 존재했다.
  이는 새 수집 경로 확인이지 이전 벤치마크 당시의 제한/pressure 증거가 아니다.
  이전 실행의 p99 초과 원인은 아직 확정하지 않았다.
- benchmark 도구 테스트 42개 통과. 새 6개 테스트는 상위 제한/동적 카운터 분리,
  누락 값의 의미, 불충분한 계층, 경로 이탈, 소속 변경, 정상 카운터 증가와 설정
  변경 구별을 검사한다. 계산/보고서/반복 실행기 40개도 통과했다.
- 이번에는 전체 벤치마크를 재실행하지 않았다. 환경 수집 보강은 G04 내부의
  진행 중 변경이며 구현 단위 완료로 처리하지 않는다. 새로운 환경 증거를 갖춘
  전체 측정, 소스-빌드 출처, 실제 보안/내구성 적용 확인이 여전히 필요하다.

### G03/G04: 실행 입력 해시 고정 (2026-09-07)

- 반복 실행기의 계획에 부하 생성기, 양 엔진의 단일/클러스터 시작 스크립트,
  cgroup/런타임 수집기, 계산/보고서 판정 모듈, 공개 기준선 등 13개 입력 파일의
  SHA-256을 기록한다. 각 단계 전후 및 최종 판정 직후에 파일과 계획 JSON의
  해시를 재검사하며 변경/누락 시 종료 코드 2, 수치 승인 false로 남긴다.
- 공개 v0.6.0 보고서는 알려진 원본 SHA-256
  `d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788`에도 고정한다.
  측정 전에 바뀐 공개 기준선으로 새 계획을 만드는 것도 거부한다.
- `execution_inputs_verified`는 모든 실행 및 최종 검사 완료 시에만 true다.
  이 값은 소스에서 SteelSearch 실행 파일을 빌드했다는 증명이 아니며,
  `acceptance_established=false`를 유지한다. 검사 사이의 변경 후 원복이나
  시스템 Python/셸/라이브러리 전체의 불변성까지 증명하지 않는다.
- 테스트: 계산/보고서/반복 실행기 43개, benchmark 도구 42개,
  release 도구 54개 통과. 입력별 변경과 계획 변경 거부, 공개 보고서 고정,
  실제 실행 흐름에서 입력 변경 감지 후 중단/실패 결과 보존을 검사했다.
- 실제 바이너리를 사용한 준비 모드 결과는
  `target/core-replacement-g04/fingerprint-plan-first/plan.json`에 있다.
  이는 부하를 실행하지 않은 준비 기록이다. 새 수집기/입력 고정 경로로 전체
  벤치마크를 아직 실행하지 않았으며 G03/G04 완료로 처리하지 않는다.

### G04/P03: 새 자원 수집 경로의 전체 반복 측정 (2026-09-07)

- `run_core_performance_gate.py`를 기존과 동일한 두 바이너리 경로 및 포트 환경으로
  실행하고 출력만 `target/core-replacement-g04/repeated-cgroup-first`로 분리했다.
  고정 순서의 전체 12개 실행은 요청 오류 0, 6개 matrix 종료 코드 모두 0이다.
  cgroup 전후 설정 및 13개 실행 입력/계획 해시 검사도 통과해
  `execution_inputs_verified=true`다. 수치 판정은 코드 1, 구현 승인은 false다.
  두 역할 모두 동일한 고정 v0.6.0 바이너리이며 런타임 기능 변경은 없다.

| 반복 | 비교 지점 | 초과 지표 | 악화율 |
| --- | --- | --- | ---: |
| 1 | 같은 반복의 v0.6.0 → 후보 | 단일 노드 sort_filter p95 | 5.694025% |
| 1 | 같은 반복의 v0.6.0 → 후보 | 3노드 nested p99 | 5.568403% |
| 1 | 공개 v0.6.0 → 후보 | 3노드 nested p99 | 7.098184% |
| 1 | 공개 v0.6.0 → 새 v0.6.0 측정 | 단일 노드 refresh p99 | 6.119797% |
| 2 | 같은 반복의 v0.6.0 → 후보 | 3노드 facet p99 | 5.210516% |
| 2 | 공개 v0.6.0 → 후보 | 3노드 lexical p99 | 6.366693% |
| 2 | 공개 v0.6.0 → 후보 | 3노드 ranking p99 | 6.438792% |

- `resource-diagnostics.json`은 result에 연결된 6개 원시 보고서의 SHA-256을
  재확인한 뒤, cgroup 경로/PID별 전후 카운터 차이를 기록한 진단 산출물이다.
  104개 읽을 수 있는 관측 행에서 CPU throttling 증가는 0, 80개 읽을 수 있는
  행에서 memory.high/OOM/OOM kill 증가는 0이었다. 누락 값은 0으로 대체하지 않았다.
  상위 계층/같은 cgroup의 반복 관측을 포함하므로 이 행 수는 독립 표본 수가 아니다.
- SteelSearch 프로세스와 부하 생성기는 같은 cgroup에 속한다. 그 계층의 CPU
  pressure `some.total` 증가는 단일 노드 약 31.28~31.49초, 3노드 약
  34.25~34.73초였다. 관측 구간은 데이터 준비 포함 약 64.6~65.1초로, 60초
  부하 시간과 동일하지 않다. 같은 계층에 속한 3노드 값을 합산하지 않는다.
  해당 계층의 memory pressure 증가는 0, I/O pressure 증가는 약 0.001~0.009초다.
  OpenSearch 관측 구간은 준비 포함 약 90~116초로 별도로 취급한다.
- 이 결과는 보이는 quota throttling/OOM이 지연 초과를 일으켰다는 증거를
  제공하지 않는다. CPU 경합은 조사할 단서지만 카운터만으로 클라이언트/서버의
  비용이나 특정 연산의 p99 초과 원인을 확정할 수 없다. 기능 제외의 인과 조건과
  최적화 불가 조건도 성립하지 않아 ledger 제외 항목은 추가하지 않았다.
- 원본은 위 실행 디렉터리에 보존했다. 주요 SHA-256:
  - plan: `56c6f51e1b52bd9a42ef00dca17dfacda47ac2904059a25094fb8183d4fa50c9`
  - result: `8eb47adc5990b866ff32c3de9d993edb64bfa5e034caf1623ebc82dec3d5448e`
  - resource diagnostics: `9d92a760f36c6ca85a70022b619f204265a3f0c815cdc3ef66c228ffce330156`
- 실행 후 소유 서버/컨테이너 종료를 확인했으며 기존 무관한 서비스는 유지했다.
  이번에는 런타임/판정 코드를 수정하지 않고 새 경로의 실제 전체 실행을 검증했다.
  G03/G04는 아직 미완료다. 다음 원인 조사는 합격용 실행과 분리한 CPU 프로파일에서
  서버와 부하 생성기의 비용을 구별하는 것이다. 원래 60초/4클라이언트 프로파일과
  실패 원본을 유지하고, 진단용 부하/프로파일러 결과로 5% 합격을 대체하지 않는다.

### P03: 서버/부하 생성기 CPU 분담 진단 (2026-09-07)

- `tools/run-core-cpu-diagnostic.py`를 추가하고
  `target/core-replacement-g04/cpu-attribution-first`에서 실행했다.
  기존 matrix 실행기를 이용한 3노드/7개 코어 연산/4클라이언트/45초 부하다.
  부하 시작 후 8초 대기한 뒤 소유 서버 3개와 부하 생성기에만 20초 perf를
  연결했다. 원래 합격용 60초/두 토폴로지 전체 실행을 대체하지 않는다.
- 일반 사용자 perf는 paranoid=4로 거부됐다. 시스템 설정을 바꾸지 않고 기존
  `sudo -n perf` 실행 경로를 사용했다. `cpu-clock`, 49Hz, DWARF 8192-byte stack
  방식이며 perf와 matrix 종료 코드는 모두 0이다. 원시 보고서에는
  `diagnostic_only=true`, 진단 결과에는 `acceptance_established=false`를 남겼다.
- perf 시작/종료 비용을 포함한 `/proc/PID/stat` 관측 구간은 22.2095초다.
  PID start ticks가 전후 동일했고, 부하 생성기는 CPU 16.57초, 서버 3개는 각각
  8.07/8.24/14.29초(합계 30.60초)를 사용했다. 부하 생성기를 제외한 서버 CPU와
  전체 프로세스 CPU를 혼동하지 않는다. 이 관측은 프로파일러가 붙은 진단이다.
- perf 데이터는 1,396 sample/약 12.6MB, report의 lost sample은 0이다.
  수명이 짧은 스레드에 대한 open 실패 경고가 있어 수집이 완벽하다고 주장하지 않는다.
  전체 수집 sample 기준 self 비용에서 Python eval 7.16%, malloc 3.01%,
  서버 memcmp 3.87%, JSON f64 직렬화 2.58%, 단순 버킷 집계 2.36%가 관측됐다.
  이는 지연 기여율이나 특정 API의 CPU 백분율이 아니다.
- 원본 `perf.data`, `perf.log`, `perf-report.txt`, `perf-flat.txt`, `diagnostic.json`을
  보존했다. diagnostic SHA-256은
  `234fe1fd5bcde9d6adbcf92c2775738b85dca36b6fa8fa2d78341ea46deb9872`,
  perf.data SHA-256은
  `06b85bca96d251c9850d2a4506075dd5581578cd2d01e46cf0d595eb876717a5`다.
- CPU stat 필드/괄호가 포함된 프로세스명 해석 및 실제 소유 프로세스 관측 테스트
  2개가 통과했다. 종료 후 진단/부하/서버/perf 프로세스가 남지 않았음을 확인했다.
- `source_value_for_highlight_field`와 단순 버킷 집계 코드를 검토했으며 이미
  top-level 빠른 경로와 캐시된 필드 접근을 사용한다. 짧은 표본만으로 중복 최적화를
  추가하지 않았다. 다음 조사는 문자열 비교/집계의 호출 경로를 좁혀 재현 가능한
  서버 비용을 찾는 것이다. 아직 특정 기능의 5% 회귀/최적화 불가를 입증하지 않았고,
  P03 및 G03/G04 완료나 ledger 제외를 선언하지 않는다.

### P03: terms 카운터 자료구조 대안 검증 (2026-09-07)

- 저장한 call graph에서 전체 sample의 1.58%가 단순 버킷 집계의 memcmp 호출
  경로로 연결됐다. 해당 terms 카운터는 `BTreeMap<&str, u64>`로 집계한 뒤
  count 내림차순/key 오름차순으로 다시 정렬한다. 순회 순서가 최종 출력 순서를
  결정하지 않으므로 표준 `HashMap` 대안을 진단했다.
- `tools/bench-terms-counter.rs`: 5,000개 문자열, 500회 집계/정렬, cardinality
  3/32/1024, 교대 순서 4회 반복으로 비교했다. 두 구현의 전체 bucket 결과가
  동일한지 assertion으로 확인했다. 엔진 실행이 아닌 표준 컨테이너 진단이다.
- 첫 결과 `target/core-replacement-g04/terms-counter-comparison.csv`를 보존하고,
  3개 키를 실제 부하의 commerce/search/analytics로 바꾼 후 별도로
  `terms-counter-real-categories.csv`에 기록했다. 실제 문자열 결과:

| Cardinality | BTreeMap 500회 (ms 범위) | HashMap 500회 (ms 범위) |
| --- | ---: | ---: |
| 3 | 29.93~30.66 | 66.22~66.52 |
| 32 | 101.43~104.42 | 70.73~71.44 |
| 1024 | 301.36~302.76 | 138.74~139.77 |

- 작은 cardinality에서는 표준 HashMap이 약 2.2배 느려 무조건 교체하는 안을
  채택하지 않았다. 엔진 코드와 실제 실행 파일은 변경하지 않았다. 큰 cardinality의
  국소 개선을 전체 코어 성능 개선으로 주장하지 않는다. 이것은 기능 구현을
  적용/최적화/전체 검증한 결과가 아니므로 제외 ledger 항목으로 등록하지 않는다.
- P03은 미완료이며 전체 벤치마크를 다시 실행하지 않았다. 이번 결과로 현재
  p95/p99 초과가 해소됐다고 판정하지 않는다. 다른 선행 작업인 G02의 aggregate
  gate는 여전히 profile 인자가 없고 vector/knn-plugin/ml을 필수로 실행한다.
  성능 관측과 별개로 코어 프로파일 전파 작업을 이어갈 수 있으며, 직접 plugin
  gate 제외와 하위 복합 gate의 plugin 요구 분리를 모두 완료해야 한다.

### G02: aggregate 프로파일 선택 계층 (2026-09-07)

- `tools/check-all-promotion-gates.py`에 `--compatibility-profile`을 추가했다.
  기존 동작은 `legacy-full`이며 `core-no-plugins`는 직접 plugin gate인
  vector/knn-plugin/ml 3개를 실행하지 않고 이유와 함께 excluded로 기록한다.
  나머지 23개에는 검색, 보안, snapshot, peer/distributed 요구가 유지된다.
- excluded는 passed로 세지 않는다. 알 수 없는 프로파일, 빈/전부 제외 결과,
  필수 코어 gate 누락, 중복/알 수 없는 gate, 코어 gate의 임의 제외는 실패한다.
  기본 코어 출력은 `target/core-no-plugins-promotion-gate-suite-current.json`이며
  기존 full-profile 기본 출력으로 덮어쓰는 것을 거부한다.
- aggregate 테스트 21개와 release 도구 테스트 54개가 통과했다.
  신규 프로파일의 실제 선택 목록은 `target/core-replacement-g02/selection.json`에
  기록했다. 이 목록은 하위 gate를 실행한 증거가 아니며 acceptance는 false다.
- 검색 promotion gate의 입력 조건을 확인했다. 이미 search/aggregation 영역만
  semantic 요구로 선택하며, 18개 release plugin 제외 case(knn/ml 영역)는 해당
  요구에 포함되지 않는다. 이 지점에는 불필요한 필터를 추가하지 않았다.
- **G02 미완료**: release evidence inventory는 아직 모든 gate가 ok/returncode 0이고
  passed가 전체 check 수와 같아야 한다는 full-profile 계약을 사용하므로 새로운
  excluded 행을 승인하지 않는다. 다음 작업은 inventory의 기대 프로파일을 명시적으로
  전달하고, 다른 복합 소비자에도 코어/플러그인 조건을 전파하는 것이다. 기존 검사를
  끄거나 코어 결과를 full-profile 승격 증거로 바꿔서 우회하지 않는다.
- 이번 변경은 선택/집계 계층의 부분 구현이다. 실제 aggregate 전체 실행과 단위
  완료 후 전체 벤치마크는 아직 수행하지 않았으며 G02 완료로 보고하지 않는다.

### G02: inventory 기대 프로파일과 보고서 연결 (2026-09-07)

- `report-release-evidence-inventory.py`에 기대 compatibility profile과 명시적인
  `--promotion-gate-suite` 경로를 추가했다. 코어 모드에서는 경로가 필수이며,
  지정 파일이 없거나 실패해도 다른 최신 파일로 대체하지 않는다. 기본 full 모드에
  코어 보고서를 전달하거나, 코어 모드에 profile 없는 기존 보고서를 전달하면 거부한다.
- 코어 검증은 vector/knn-plugin/ml의 정확한 세 excluded 행과 제외 이유를 요구한다.
  excluded 행에 실행 성공 코드를 붙이거나, 플러그인을 통과로 세거나, 보안/검색 등
  코어 gate를 제외하거나 누락하면 실패한다. 중복 이름, 잘못된 count/type,
  status/count 불일치도 거부한다. 선택적 inventory 자기 검사가 실패한 경우의
  기존 순환 참조 처리에서도 코어 count 검증은 생략하지 않는다.
- aggregate는 자신이 작성한 코어 summary 경로/프로파일을 inventory 명령에
  전달한다. inventory 출력도 `core-no-plugins-release-evidence-inventory-current-check.json`으로
  분리한다. 기본 full-profile 증거 파일을 바꾸지 않는다.
- release 도구 테스트 58개, aggregate 테스트 21개 통과. producer의 실제 명령
  구성과 summary 형식을 consumer validator에 연결한 테스트도 통과했다.
  테스트에서는 하위 실행을 mock했으며 이 결과를 실제 23개 gate 통과로 세지 않는다.
- **G02 미완료**: inventory의 다른 증거 종류 및 source closure/broad e2e/REST
  coverage/harness 등 복합 gate의 코어 조건 분리가 남아 있다. 기존 내구성·보안·분산
  요구는 그대로 유지했다. 이번 부분 변경에서 실제 aggregate 전체 실행이나 구현
  단위 완료 후 전체 벤치마크를 수행하지 않았으며 운영 승격을 승인하지 않는다.

### G02: unified E2E suite 프로파일 전파 (2026-09-07)

- `unified_compatibility_scope.py`에 독립 플러그인 suite 4개와 코어/운영 suite
  30개의 명시적 목록을 정의하고 runner/checker가 공유한다. vector-search,
  vector-search-native-surface, knn-plugin-surface, ml-model-surface는 코어 모드에서
  실행/통과 집계에 넣지 않고 별도 excluded_suites에 이유를 기록한다.
- `run-unified-opensearch-e2e.py --compatibility-profile core-no-plugins`는 전체 코어
  suite를 선택한다. 부분 --suite/--case 선택, 목록 drift, 빈 결과 작성은 거부한다.
  기본 출력은 `target/unified-opensearch-e2e-core-current`로 full-profile과 분리한다.
  기존 `--profile`은 보고서 라벨이고 compatibility-profile이 검증 범위 계약이다.
- checker는 기대 프로파일 일치, 전체 코어 목록/중복/필수 suite 강등 여부,
  정확한 네 excluded suite를 검증한다. 제외 행은 실행 코드나 summary를 가질 수 없다.
  기존 fixture/classification/skip/보안·내구성·분산 검증은 계속 적용한다.
- aggregate의 broad E2E 명령 및 inventory의 해당 명령 계약도 코어 보고서 경로와
  기대 프로파일로 연결했다. full-profile 명령 계약은 그대로 유지한다.
- unified 테스트 62개, release 도구 58개, aggregate 21개 통과.
  실제 수집 모드 실행은 `target/core-replacement-g02/unified-core-first`에 보존했다.
  재귀 스캔 없이 지정 출력/직접 target 보고서만 수집했고 최대 나이는 기존과 같은
  604800초다. 코어 30개/제외 4개가 작성됐으나 필수 증거가 없어 status=missing,
  수집기/검증기 모두 코드 1이다. live suite 실행이나 기능 통과 증거가 아니다.
- **G02 미완료**: search-compat/security-authz 등 복합 suite 내부의 개별 플러그인
  사례는 아직 분리하지 않아 현재 요구에 남아 있다. source closure/REST coverage/
  harness 등 다른 소비자도 계속 분리해야 한다. 이 부분 구현에서 전체 코어 live
  E2E/aggregate 및 구현 단위 완료 후 전체 벤치마크를 실행하지 않았다.

### G02: 보안 suite의 ML API 사례 분리 (2026-09-07)

- 원본 security-authz fixture의 63개 사례 중 명시적으로 검토한 ML API 4개만
  제외하는 `core_security_fixture.py`를 추가했다. 생성 fixture에는 59개 보안 사례와
  기존 인덱스/alias/bulk/credential/policy 설정을 그대로 유지한다. restricted-index의
  이름에 plugins가 들어 있다는 이유로 권한 검사를 빼지 않는다.
- unified 코어 runner가 별도 core-fixtures/security-authz-compat.json을 생성해
  기존 보안 harness의 --fixture에 전달하고, source/projected SHA-256과 제외 목록을
  suite 결과에 기록한다. 기존 파생 fixture를 덮어쓰지 않으므로 재실행은 새 출력
  디렉터리를 사용한다. 코어 unified 재실행 안내도 부분 suite/case가 아닌 전체
  프로파일 명령과 별도 출력 디렉터리를 사용하도록 갱신했다.
- checker는 원본의 현재 내용과 기록된 해시, 파생 파일 해시, 정확한 네 제외 이름,
  원본에서 해당 사례만 제거한 전체 내용의 일치를 검사한다. 파생 파일의 해시를
  다시 계산해 붙여도 코어 사례나 준비/자격 증명 설정을 바꾸면 실패한다.
- projection 테스트 3개, unified 62개, release 58개, aggregate 21개 통과.
  실제 수집/검증 결과는 `target/core-replacement-g02/unified-security-projection-first`에
  보존했다. fixture_case_count=59와 projection 검증은 확인했으나 live 보고서가 없어
  양쪽 코드 1/status=missing이다. 보안 기능이 실제로 통과했다고 주장하지 않는다.
- 원본 SHA-256: `8d236dd657856459f8c7b31789bb7855666d323008ab8ad442d30adcdd19f26e`.
  파생 SHA-256: `cc009cd9725772da3fb119aba86208904d92d46e63771c2473806873327d94aa`.
- **G02 미완료**: search-compat는 제외할 18개 plugin case 외에도 초기 준비 단계의
  knn_vector 인덱스/alias/bulk를 가지고 있어 case 필터만으로는 완전한 분리가 안 된다.
  코어 사례가 참조하는 준비 데이터는 유지하면서 이 의존 관계를 분리해야 한다.
  나머지 복합 소비자 전파와 실제 live/aggregate/전체 성능 검증도 남아 있다.

### G02: 검색 fixture의 플러그인 준비 데이터 분리 및 live 검증 (2026-09-07)

- `core_search_fixture.py`가 승인된 release plugin 제외 목록의 18개 사례와
  vectors-compat/vectors-cosine-compat/vectors-innerproduct-compat의 초기 인덱스,
  alias, bulk 및 관련 manifest 항목을 함께 제거한 파생 fixture를 생성한다.
  제외 대상이 knn/ml 영역이 아니거나, 남은 내용이 제거한 리소스를 명시적으로
  참조하면 실패한다. 원본 fixture는 바꾸지 않는다.
- 파생 fixture를 공유하는 search-compat/tier-read-surface/runtime-mappings-surface
  세 suite에 연결했다. checker가 원본/파생 해시, 제외 사례/인덱스 목록 및 전체
  내용의 정확한 projection을 검증한다. 새 해시로 코어 사례 누락을 숨겨도 실패한다.
  최초 수집은 각각 fixture_case_count 1180/2/2를 기록했으며 live 증거 전에는
  기존과 같이 missing으로 남았다.
- 새 OpenSearch 3.7.0-SNAPSHOT과 새 SteelSearch 프로세스로 파생 검색 fixture를
  실제 실행했다. `SEARCH_COMPAT_EXCLUDE_CASES`는 비워 추가 필터 없이 실행했으며
  **1,180 passed / 0 failed / 0 skipped**, wrapper 종료 코드 0이다.
  후보 파일은 고정 v0.6.0 SHA-256이며 실행 전후 동일했다. 참조 root identity와
  명령/fixture 해시/로그를 `target/core-replacement-g02/search-projection-live-first`에
  보존했고 종료 후 관련 프로세스가 남지 않았음을 확인했다.
- 파생 fixture SHA-256:
  `8bae7742daa28a9d67e2cecc0f635eddbcea48099a8b0c89390d5a6abcae006c`.
  live report SHA-256:
  `ff8bc4beb0904b69dfe8c3876465d3bc9d8d3f04cdabc0d162f9e2bbf760bacd`.
- 같은 live report를 명시적인 report index로 unified 수집기에 연결한
  `unified-suite-indexed.json`도 status=ok이며 strict_equal=80,
  canonical_equal=1100, failed/missing/skipped=0이다. 단일 search suite의 결과이지
  전체 unified E2E 승인으로 간주하지 않는다.
- projection 테스트 6개, unified 62개, release 58개, aggregate 21개 통과.
  **G02 미완료**: 보안의 파생 fixture live 검증, 다른 복합 소비자 전파, 전체
  aggregate/live E2E와 구현 단위 완료 후 전체 성능 검증이 남아 있다.

### S01/S04: 사용자 파일 설정과 실제 인증의 연결 결함 재현 (2026-09-07)

- `main.rs`의 설정 파서는 `STEELSEARCH_AUTHENTICATION_USERS_FILE`과
  `--security.authentication_users_file`을 `authentication_users_path`에 저장하고
  production preflight 및 boundary policy에서 해당 파일을 검사한다.
  그러나 `standalone_runtime.rs::security_authentication_users_file`은 별개의
  `SECURITY_AUTHENTICATION_USERS_FILE` 또는 역할별 환경 자격 증명만 읽는다.
  설정 파일 검증 성공을 요청 인증 적용 증거로 사용할 수 없다.
- `tools/diagnose-authentication-file-wiring.py`를 추가했다. 외부 보안/노드 환경을
  제거하고 loopback에 독립 daemon을 실행해 동일한 임시 사용자 파일의 익명,
  올바른 암호, 잘못된 암호 요청을 비교한다. 종료 시 소유 프로세스를 wait하고
  임시 자격 증명을 제거하며 로그/보고서에는 암호를 기록하지 않는다.
- 고정 v0.6.0 바이너리 `db244133...f1f57`로 실제 재현한 결과:

| 설정 경로 | 익명 | 올바른 계정 | 잘못된 암호 |
| --- | --- | --- | --- |
| `STEELSEARCH_AUTHENTICATION_USERS_FILE` | 401 | **401 (결함)** | 401 |
| `SECURITY_AUTHENTICATION_USERS_FILE` | 401 | 200 | 401 |
| `--security.authentication_users_file` | 401 | **401 (결함)** | 401 |

- 최초 두 환경변수 비교 원본은
  `target/core-replacement-s01/auth-file-wiring-first/report.json`, CLI 추가 비교는
  `target/core-replacement-s01/auth-file-wiring-cli-first/report.json`에 보존했다.
  두 실행 모두 진단 도구 종료 코드 1이며 바이너리 해시는 실행 전후 동일하다.
  개발 모드 HTTP 진단이므로 TLS/운영 모드/전체 보안 fixture 통과를 의미하지 않는다.
- 수정 순서: (1) 설정 파서가 선택하고 검증한 사용자 파일 경로를 인증 런타임에
  직접 전달, (2) CLI 우선순위와 기존 레거시 경로의 명시적인 호환 규칙 검증,
  (3) 잘못된 파일에서 환경 자격 증명으로 우회하지 않는 fail-closed 검사,
  (4) 사용자와 서비스 계정 모두 공식 환경변수/CLI 경로로 live 검증,
  (5) 보안 fixture 및 운영 TLS 검증, S01 단위 완료 시 전체 벤치마크 실행.
  공식 환경변수를 추가로 조회하는 것만으로 CLI 결함까지 해결했다고 처리하지 않는다.
- 아직 런타임 수정 전이며 **S01/S04 미완료**다. 기능 추가로 인한 성능 회귀가
  아니라 기존 인증 설정 결함이므로 제외 ledger에 등록하지 않는다.

### S01: 사용자 파일 설정을 노드별 인증 경로에 전달 (2026-09-07)

- daemon이 파싱한 `authentication_users_path`를
  `SteelNode::with_authentication_users_file`로 전달한다. 인증 주체 조회와 권한
  검사를 노드 메서드로 연결해 일반 요청, root의 추가 인증, bulk가 같은 경로를
  사용한다. 요청별 전역 환경 변경이나 프로세스 전역의 단일 노드 설정을 도입하지 않았다.
- 명시적인 노드 경로가 있으면 레거시 환경 파일보다 우선한다. 명시적 파일을
  읽거나 파싱하지 못하면 오류를 반환하고 환경 계정으로 fallback하지 않는다.
  경로가 없는 기존 호출자는 기존 레거시 환경 경로/역할별 계정 동작을 유지한다.
- 회귀 테스트 `configured_authentication_file_is_node_scoped_and_fails_closed`는
  서로 다른 노드 경로, 누락된 레거시 경로보다 명시적 경로 우선, 누락/손상/빈
  사용자 파일에서 root 및 cluster health 인증 거부를 검사한다. 해당 테스트 통과,
  이어 노드 라이브러리 전체 **586 passed / 0 failed** (serial)다.
  로그: `target/core-replacement-s01/node-lib-tests.log`.
- 수정 전 바이너리는 `target/core-replacement-s01/baseline/steelsearch`에 보존했고
  SHA-256은 고정 v0.6.0의 `db244133...f1f57`이다. 후보는 릴리즈와 같은
  `RUSTFLAGS=-Awarnings cargo +nightly build --locked --release -p os-node
  --features standalone-runtime --bin steelsearch` 명령으로 빌드한다.
- 추가 확인된 미비점: 사용자 파일 파서는 `password_hash`/`token_hash`를 허용하지만
  런타임 자격 증명 수집은 평문 `password`/`token`만 선택한다. 따라서 이번 경로
  수정만으로 해시 기반 인증이나 production readiness를 입증할 수 없다.
  해시 검증 구현/지원 형식 검증/잘못된 형식의 fail-closed 검사가 S01에 남는다.
- 후보 live 진단, 전체 보안 fixture, 운영 TLS, 전체 벤치마크가 아직 남았으므로
  S01 완료 또는 성능 합격으로 처리하지 않는다.

### S01: 수정 후보 live 인증 및 첫 전체 성능 측정 (2026-09-07)

- 릴리즈 후보 빌드 종료 코드 0, 소요 3m 53s. 후보 SHA-256:
  `86281ef5aaaef76756063bacf288d0885f5a81fb8246fde702afb16d5f85acec`.
  `target/release/steelsearch`는 이제 이 수정 후보이며 최초 v0.6.0이 아니다.
  기준 실행은 앞 절의 보존 경로를 명시적으로 사용해야 한다.
- `auth-file-wiring-fixed-first/report.json` (상위 경로
  `target/core-replacement-s01`) live 진단 종료 코드 0. 공식 환경변수, 레거시
  환경변수, CLI 세 경로 각각 익명 401 / 올바른 사용자 200 / 잘못된 암호 401 /
  admin health 200 / 올바른 서비스 토큰 200 / 잘못된 토큰 401 /
  writer 서비스 계정의 health 요청 403을 확인했다. CLI에는 누락된 공식 환경
  파일을 함께 지정하고, 명시적 경로에는 누락된 레거시 파일을 함께 지정해
  우선순위도 실제 daemon에서 검사했다. 개발 모드 HTTP의 범위 제한은 유지한다.
- 후속 빌드/테스트 없이 플러그인 제외 전체 4개 시나리오를 실행했다.
  corpus 5,000 / clients 4 / 3 shards / 단일 0 및 3노드 1 replica /
  source array 384 / seed 13 / 60초 / 7개 코어 연산 혼합이며
  OpenSearch 2.19.0 고정 image digest와 512 MiB heap을 사용했다.
  모든 요청 오류 0, matrix 종료 코드 0, 후보 해시 실행 전후 동일.

| 토폴로지 | 후보 처리량 (ops/s) | v0.6.0 대비 처리량 변화 | OpenSearch 처리량 | OpenSearch 대비 |
| --- | ---: | ---: | ---: | ---: |
| 단일 노드 | 751.0328 | +1.0796% | 287.3513 | 2.6136x |
| 3노드 | 922.0195 | -1.0040% | 112.5745 | 8.1903x |

- **누적 5% 수치 게이트 실패**: 44개 중 43개 이내, 3노드 nested p99만
  11.3688903 ms → 12.0183535 ms, **+5.712634%**로 한도 11.9373348 ms 초과.
  처리량이나 다른 연산의 개선으로 상쇄하지 않는다.
- 원본: `target/core-replacement-s01/full-matrix-first/summary.json`, SHA-256
  `a46a5bd0c371738966464a6660fb568b93833893a2ee3890d9fc0324c471d4c4`.
  통합 원본을 직접 엔진별 검증기에 전달한 첫 `budget-check.json`은 입력 형식
  오류(종료 코드 2)로 보존했다. 이후 각 엔진의 두 scenario를 내용 변경 없이
  분리한 `steelsearch.json`/`opensearch.json`에는 원본 해시와 projection 정보를
  기록했다. `budget-check-engine-reports.json`은 정합성 통과, 수치 실패(코드 1),
  SHA-256 `5b90d092366aa855d7e6c745dbeca19606b017af16b7aea051902ae3cdd7951a`.
- 소유 daemon과 benchmark Docker 컨테이너는 종료 확인했다. 이 실행은 첫 전체
  측정이지 사전 고정 paired 반복 판정 완료가 아니다. 과거 동일 바이너리 A/A에서도
  nested p99 변동이 있었지만 이를 이유로 이번 실패를 통과 처리하지 않는다.
  다음은 보존 v0.6.0/후보의 사전 고정 반복 전체 비교 및 원인 분석이다.
  아직 단일 변경의 회귀 인과관계와 최적화 불가를 입증하지 않았으므로 ledger 제외는
  하지 않았다. **S01 미완료**, 전체 보안 fixture/해시 인증/운영 TLS도 계속 남는다.

### S01/G04/P03: 수정 후보의 사전 고정 반복 전체 비교 (2026-09-07)

- `target/core-replacement-s01/repeated-paired-first`에서 기존 실행기로
  baseline → candidate → OpenSearch → OpenSearch → candidate → baseline 순서,
  각 단일/3노드 총 12개 토폴로지를 1,097초 동안 실행했다. 모든 matrix 종료 코드
  0, 요청 오류 0이며 `execution_inputs_verified=true`다. 코드/빌드/테스트를
  측정과 동시에 수행하지 않았다. 최종 게이트 종료 코드 **1**, 성능 실패다.
- 기준 바이너리 `db244133...f1f57`, 후보 `86281ef5...5acec`를 실행 전후 확인했다.
  plan SHA-256: `7d76796615a795f303babec9813f2030838cc2b66f760ccb6bf2d23c28c53813`.
  result SHA-256: `59a494558e11ad414b21bd36f7961c2058806ab7b8e82018c65cfcfe17157ef0`.
  기존 최초 전체 측정 실패는 보존하며 이 결과로 대체하지 않았다.

| 반복 | 비교 | 초과 지표 (모두 3노드) | 저하율 |
| --- | --- | --- | ---: |
| 1 | 같은 반복 기준선 → 후보 | lexical p99 | 9.716984% |
| 1 | 같은 반복 기준선 → 후보 | ranking p99 | 5.946398% |
| 1 | 같은 반복 기준선 → 후보 | sort_filter p99 | 8.491571% |
| 1 | 같은 반복 기준선 → 후보 | refresh p95 | 5.621962% |
| 1 | 같은 반복 기준선 → 후보 | refresh p99 | 10.881191% |
| 1 | 공개 v0.6.0 → 후보 | lexical p99 | 6.155964% |
| 1 | 공개 v0.6.0 → 후보 | ranking p99 | 5.908461% |
| 1 | 공개 v0.6.0 → 후보 | refresh p99 | 5.941594% |
| 2 | 같은 반복 기준선 → 후보 | facet p99 | 5.137377% |
| 2 | 공개 v0.6.0 → 후보 | facet p99 | 6.383142% |
| 2 | 공개 v0.6.0 → 후보 | nested p99 | 7.437346% |
| 2 | 공개 v0.6.0 → 새 기준선 | nested p99 | 9.146775% |
| 2 | 공개 v0.6.0 → 새 기준선 | refresh p99 | 5.726229% |

- 최초 실패였던 nested p99의 같은 반복 기준선 대비 후보 차이는 반복 1에서
  +1.374531%, 반복 2에서 -1.566175%다. 반복 2의 기준선 자체가 최초 공개값보다
  +9.146775%이므로 인증 경로 수정의 단일 인과관계로 해석할 수 없다.
  그렇다고 다른 초과 항목이나 공개 기준선 대비 실패를 무시하지 않는다.
- 서버/부하 생성기가 공유하는 leaf cgroup을 native 시나리오마다 한 번씩 골라
  전후 counter 차이를 계산했다. 원본 보고서 해시와 PID/경로를 확인한
  `native-resource-diagnostics.json`에 보존했다. 8개 관측 모두 CPU throttling,
  memory high/OOM/OOM kill 증가 0이다. CPU PSI some 증가량은 단일 노드
  31.162~31.374초, 3노드 34.076~34.620초다. 관측 구간은 seed+load 약
  64.62~65.13초이며, 서버 단독 비용이나 개별 요청 지연의 비율이 아니다.
  중복 노드/ancestor를 독립 표본으로 세지 않았다.
- 소유 프로세스/벤치마크 컨테이너 종료 확인. **S01/G04/P03 미완료**.
  다음은 후보의 서버/부하 생성기 CPU 비용 프로파일링과 최적화 후보 검증이다.
  반복마다 초과 항목이 달라지는 사실만으로 잡음 통과를 만들지 않으며,
  기준선/5% 한도/전체 시나리오를 변경하지 않는다. 단일 기능의 5% 이상 회귀 및
  최적화 불가가 입증되지 않아 제외 ledger에는 추가하지 않았다.

### P03/S01: 후보 CPU 진단과 terms 카운터 대안 실험 (2026-09-07)

- `run-core-cpu-diagnostic.py`에 `--binary`와 `--expected-sha256`을 추가했다.
  기본 기대 해시는 v0.6.0으로 유지하며, 명시적인 후보 해시는 형식과 파일 내용이
  일치해야 한다. 실제 서버 `/proc/<pid>/exe`와 실행 후 선택 파일 해시도 검사한다.
  잘못된 해시/파일 변경 거부를 포함해 진단 도구 테스트 **4개 통과**.
- 후보 `86281ef5...5acec`의 3노드 프로파일링은
  `target/core-replacement-s01/candidate-cpu-first`에 보존했다. 45초 부하 안의
  20초 perf 수집이며 matrix/perf 모두 코드 0, 소유 프로세스 종료 확인.
  CPU tick 관측 구간 20.7513초 동안 부하 생성기 13.39 CPU초,
  서버 3개 합계 25.55 CPU초다. PID 시작 시각과 후보 해시가 유지됐다.
- perf 1,186 samples, lost 0. 짧게 살던 thread의 open 실패 경고는 perf.log에
  남겼다. 전체 수집 샘플에 대한 flat self 비용은 Python evaluator 7.08%,
  서버 memcmp 4.81%, 단순 bucket 집계 3.04%, float JSON 직렬화 2.45% 등이다.
  샘플 비율을 요청 지연 기여율로 간주하지 않는다. 과거 기준선 진단과 관측 기간,
  프로파일러 간섭이 달라 CPU초를 직접 나눠 수정 회귀율이라고 주장하지 않는다.
- diagnostic SHA-256:
  `d03f736210e4c6c08126293cb98ad945fe139a20609e38660d4f5e44c558b14d`.
  perf SHA-256: `2ad1a377cacdbcebcdb6753c0a728b1bf521ea8403be53e31ee9c7880115b348`.
- `bench-terms-counter.rs`에 세 진단 대안을 추가했다. 5,000개 값 × 500회,
  고유값 수 1/3/8/9/32/1024, 순서 반전 4회, 원래 카운터와 정렬된 결과의 동일성을
  모두 검사했다. 고유값 3일 때는 실제 commerce/search/analytics 문자열을 쓴다.
  이 실험은 카운터 단독이며 실제 집계의 문서 탐색/여러 집계 결합 비용을 포함하지 않는다.

| 대안 | 관측 결과 | 판단 |
| --- | --- | --- |
| 작은 배열 ≤8, 이후 BTreeMap | 첫 실험의 고유값 3에서 기존 29.91~29.96 ms, 대안 17.32~17.43 ms. 그러나 9에서 80.08~80.74 ms (기존 74.93~76.18), 32에서 108.46~108.90 ms (기존 102.47~104.47) | 저고유값 최적화 후보이나 전환 이후 비용 검증 필요 |
| 전환 후 별도 BTreeMap 루프 | 고유값 3은 17.61~17.65 ms (기존 29.37~30.07), 32는 106.96~109.10 ms (기존 101.23~102.35) | 분기 제거만으로 모든 고유값 수에서 개선되지 않음 |
| BTreeMap 내부 키를 길이 우선 비교 | 고유값 3에서 28.57~28.71 ms (기존 29.97~30.07)이나 1/8/9/32/1024에서 더 느림 | 런타임 도입하지 않음 |

- 원본 CSV는 `target/core-replacement-s01/terms-counter-hybrid.csv`,
  `terms-counter-split.csv`, `terms-counter-length.csv`다. 이전 실험 결과는 덮어쓰지 않았다.
  단독 micro 수치를 전체 서비스의 5% 회귀나 최적화 불가로 해석하지 않는다.
- 이번 진단에서는 런타임 수정이 없고 기존 성능 실패를 유지한다. 다음 최적화 후보는
  저고유값 카운터이며, 실제 집계에 연결할 경우 고유값 8/9 경계 및 고고유값/정렬
  동등성 테스트와 실제 집계 비용 비교를 먼저 수행하고, 전체 벤치마크로 판단한다.
  **P03/S01 미완료**, ledger 제외 없음.

### P03: 저고유값 terms 카운터 연결과 전체 측정 (2026-09-07)

- `os-engine-tantivy`의 `SimpleTermCounts`를 실제 단순 terms 집계 경로에 연결했다.
  최대 8개 키까지 배열에서 카운트하고 이후 기존 BTreeMap으로 전환한다.
  문자열 키는 계속 빌린 참조이며 최종 bucket의 정렬/최소 문서 수 필터/소유 응답
  생성은 그대로다. range/date histogram과 지원하지 않는 입력의 fallback은 유지한다.
- 원래 후보는 `target/core-replacement-s01/steelsearch-before-small-terms`에 보존,
  SHA-256 `86281ef5aaaef76756063bacf288d0885f5a81fb8246fde702afb16d5f85acec`.
  새 후보 `target/release/steelsearch` SHA-256:
  `d3c0282d44aaece7d09d0597d1dc5adb59525998245f7f758d9cecbd93a497a3`.
- 추가/기존 직접 테스트 3개 통과: 고유값 0/1/3/8/9/32/1024, 정방향/역방향 삽입,
  반복 카운트, 전환 여부, 실제 집계와 기존 집계 함수의 결과 동일성,
  최소 문서 수 1/3/4, 키 소유권 및 배열 입력 fallback을 검사한다.
  이어 엔진 전체 **827 passed / 0 failed** (serial), 로그는
  `target/core-replacement-s01/small-terms-engine-tests.log`에 보존했다.
  테스트 빌드 15m 24s, 같은 릴리즈 옵션의 후보 빌드 4m 08s, 모두 코드 0.
- 첫 전체 측정 `target/core-replacement-p03/small-terms-full-first`는
  SteelSearch 두 구간 및 OpenSearch 단일 노드 후, OpenSearch 3노드의 인덱스
  생성이 403 `index_create_block_exception`으로 실패했다. 종료 코드 1이며
  전체 보고서가 없으므로 부분 결과를 전체 성능 합격에 사용하지 않는다.
- 별도 새 참조 클러스터 진단 `opensearch-block-diagnostic-first`에서는 기존 설정
  해제 후 12회 관측 중 차단이 재발하지 않았고 생성 요청 3회 모두 성공했다.
  로그에는 초기화 중 DiskThresholdMonitor가 여유 4.1 GiB/4.3%와 flood-stage
  95% 초과를 감지해 cluster create-index block을 설정한 기록이 있다.
  따라서 디스크 압박 관련 초기화 차단은 확인했지만 첫 실패의 정확한 순서/경쟁
  조건까지 입증하지 않았다. 새로 안전장치를 더 끄거나 실패를 숨기지는 않았다.
- 실행기의 OpenSearch 부하 실패 경로에서 정리 전에 선택된 cluster settings,
  cluster blocks, filesystem stats를 `failure-diagnostics.json`에 보존하도록 보강했다.
  진단 수집 자체의 실패는 원래 부하 오류를 대체하지 않는다. 새 테스트 2개 포함
  benchmark 도구 테스트 **44개 통과**. 첫 실패의 상태가 사후 복원됐다고 주장하지 않는다.
- 참조 진단 후 새 디렉터리
  `target/core-replacement-p03/small-terms-full-after-reference-diagnostic`에서
  전체 4개 시나리오를 다시 실행했다. 418초, matrix 코드 0, 모든 요청 오류 0,
  실제 바이너리 해시 실행 전후 동일이다. 이전 실패/원본은 보존했다.

| 토폴로지 | 후보 처리량 (ops/s) | 공개 v0.6.0 대비 | OpenSearch 처리량 | OpenSearch 대비 |
| --- | ---: | ---: | ---: | ---: |
| 단일 노드 | 744.6824 | +0.2249% | 283.1670 | 2.6298x |
| 3노드 | 921.0074 | -1.1126% | 113.5266 | 8.1127x |

- 보고서 정합성은 통과하지만 **44개 중 3노드 nested p99가 실패**:
  11.3688903 ms → 12.3526186 ms, 공개 v0.6.0 대비 **+8.652808%**.
  다른 43개 수치는 한도 이내다. 전체 성능 합격 및 구현 단위 완료로 처리하지 않는다.
  summary SHA-256: `1df05c87e53b0a2a1980a21aac92cec3c8a688f34c404c5fb9c672a6d1e585fa`.
  budget-check SHA-256: `c4f12d9a1a2678419ce213bf04dc3848fd6f85fb773201b58a2b464e90030abc`.
- 실제 facet 평균은 단일 7.3073 ms, 3노드 5.0299 ms였다. 이전 후보의 세 실행은
  각각 7.2442/7.2952/7.3331 ms 및 5.0106/5.0648/5.0425 ms였으므로, 이 비동시
  비교만으로 전체 집계 비용이 유의미하게 개선됐다고 결론 내릴 수 없다.
  단독 카운터의 약 42% 개선을 실제 검색의 개선율로 사용하지 않는다.
- 소유 프로세스/컨테이너 종료 확인. **최적화 채택 검증 미완료**: 같은 조건에서
  직전 후보와 실제 집계 비용 비교, 고고유값 입력의 성능 영향, 반복 전체 게이트가
  남는다. 현재 카운터는 검증 중 후보이며 P03/S01을 완료로 표시하지 않는다.
  단일 변경의 5% 이상 악화와 최적화 불가를 입증하지 않았으므로 ledger 제외 없음.

### P03: 실제 HTTP terms 집계의 직전 후보 대조 (2026-09-07)

- `tools/run-terms-cardinality-diagnostic.py`를 추가했다. 직전 후보
  `86281ef5...5acec`와 저고유값 카운터 후보 `d3c0282d...97a3`를
  before → after → after → before 순서로 독립 단일 노드에 실행한다.
  파일 해시 및 실제 서버 `/proc/<pid>/exe`를 검사하고 소유 서버는 finally에서
  정리한다. 최초 v0.6.0과의 비교가 아니라 **카운터 변경 직전 후보와의 비교**다.
- 각 실행은 고유값 3/8/9/32/1024, keyword 문서 5,000개, shard 1/replica 0,
  단일 HTTP client, size=0 terms-only 집계다. 모든 응답의 전체 bucket 값/카운트/
  순서를 기대값과 비교했다. raw 요청 시간을 저장하고 진단/acceptance=false로
  표시한다. 벡터 source 배열, 혼합 부하, 3노드, 운영 보안은 이 진단 범위가 아니다.
- 첫 `terms-cardinality-http-first`는 모든 키 길이를 같게 했다. 다음
  `terms-cardinality-http-benchmark-keys`에서는 3개 카테고리를 실제
  commerce/search/analytics로 바꿨다. 각각 10회 warmup 후 100회 측정이며,
  이전 실행/당시 도구 사본을 각 결과 디렉터리에 보존했다.
  후자의 고유값 1024 두 번째 비교에서는 HTTP 평균 약 **+6.85%**가 관측됐다.
  이 단독 진단의 초과를 삭제하거나 전체 기능의 5% 회귀라고 단정하지 않았다.
- 측정 구간을 1,000회로 늘리고 서버 CPU tick 전후 값/시작 시각을 추가한
  `terms-cardinality-http-cpu-first`에서도 같은 순서와 모든 고유값 수를 실행했다.
  모든 bucket 검증 통과, 실행 완료, 소유 프로세스 종료 확인.
  기대 bucket 생성 테스트 2개 통과. 도구/공유 실행기/CPU sampler 해시는 plan에
  저장하며 CPU tick parser는 기존 프로파일러의 검증된 함수를 재사용한다.

| 고유값 수 | HTTP 평균 변화 1 | HTTP 평균 변화 2 | 서버 CPU 변화 1 | 서버 CPU 변화 2 |
| ---: | ---: | ---: | ---: | ---: |
| 3 (실제 카테고리) | -11.651% | -9.512% | -15.254% | -12.281% |
| 8 | -4.800% | -5.373% | -7.500% | -6.329% |
| 9 | -5.094% | -3.293% | -6.173% | -5.000% |
| 32 | -2.562% | -1.311% | -3.125% | -1.042% |
| 1024 | +0.131% | -1.348% | +0.727% | -1.444% |

- 표는 각각 첫 before/after와 마지막 before/after를 직접 비교한 값이다.
  HTTP 평균은 JSON 읽기까지 포함하며 서버 CPU는 `/proc`의 100 Hz tick 측정으로
  해상도 한계가 있다. 서로 다른 실행의 percentile을 평균내거나 이 비율로
  최초 v0.6.0의 5% 기준을 대체하지 않는다.
- 결과 위치는 모두 `target/core-replacement-p03` 아래다. result SHA-256:
  uniform: `755a61799fa895667912272bf6e00d3e0f83e179654ed600fbde8b34e6fe28bf`;
  benchmark 100회: `f71221cbe172eec228b86e5d13d940f283130d49680d11cf0deb622283d0acd1`;
  benchmark 1,000회/CPU:
  `ec7f91cd0cbbd623dd390d66c7d48431b90150ae9452f5fe5a8fc4cb9a581861`.
- 실제 저고유값 terms-only 경로의 국소적 개선 근거는 확보했다. 다만 앞선
  전체 벤치마크 nested p99 **+8.652808% 실패는 유지**한다. 이번 턴에는 런타임
  변경이 없으며, 이 진단을 전체 재측정으로 세지 않는다. 카운터 후보를 유지하되
  **P03 완료/전체 채택 승인은 보류**하고, 다음은 nested 요청 경로의 CPU 및
  응답 생성 비용 진단이다. ledger 제외 요건은 아직 충족하지 않았다.

### P03: nested 후보 집합 소유권 이동 검증 (2026-09-07)

- CPU 진단기에 `--operation nested`를 추가했다. 기본 mixed는 유지하며 nested
  진단은 3노드, 45초 부하, 20초 CPU sampling으로 별도 실행한다. 전체 성능
  판정에 사용하지 않는다. 실행 결과는 `target/core-replacement-p03/nested-cpu-first`.
- 수정 직전 후보 `d3c0282d...97a3`의 실행 파일 해시 및 서버 PID를 확인했다.
  20.6907초 관측에서 부하 생성기 CPU는 20.53초, 서버 합계는 16.64초였다.
  전체 프로세스 표본 중 scoped nested 후보 수집 self 비중 3.48%, float JSON
  직렬화 5.72%를 관측했다. 이는 서버 전용 비중이나 요청 지연 비중이 아니다.
- 실제 호출 경로는 `search_single_index_plain_snapshot_response`에서
  `search_hits_page_for_query_native_scoped`를 거쳐 후보 집합을 수집한다.
  다른 검색 경로의 child-ordinal 증명 중복 계산을 이 벤치마크의 병목으로
  단정하지 않는다. 부하 생성기 비용과 응답 직렬화 비용도 남아 있다.
- `native_nested_candidate_ids_scoped`에서 누적 집합이 비었으면 첫 비어 있지
  않은 샤드 집합의 소유권을 이동하고, 이후에는 기존 합집합 연산을 유지한다.
  재삽입 비용만 제거하며 응답 내용, workload 및 5% 기준은 변경하지 않는다.
- 회귀 테스트는 3개 샤드의 전체/부분/빈 선택, 중복 nested 자식 및 refresh 전
  문서 제외를 확인한다. 해당 테스트 통과 후 동일 엔진 테스트 실행 파일 전체를
  직렬 실행해 **828개 통과, 실패/skip 0개**를 확인했다.
  직전 실행 파일은 `target/core-replacement-p03/steelsearch-before-nested-set-move`에
  보존했다. CPU 진단기 테스트 5개와 `git diff --check`도 통과했다.
- release 후보 빌드 성공. SHA-256:
  `3fae5fd0239f0cff0c5291554f30378514b1f94dca3a29300737bdc594678f5e`.
  `target/release/steelsearch`는 이 후보이며, v0.6.0 및 직전 후보는 별도 보존한다.
- `target/core-replacement-p03/nested-set-move-full-first`에서 4개 전체 혼합 부하
  실행 완료(약 417초), 모든 요청 오류 0건. 실행 전후 바이너리 및 실행기/기준선
  해시 13개 동일. 엔진별 원본 필터 projection을 생성해 정합성 검사를 통과했고
  **공개 v0.6.0 대비 44개 지표 모두 5% 이내**였다.

| 토폴로지 | 후보 처리량 (ops/s) | 공개 v0.6.0 대비 | OpenSearch 처리량 | OpenSearch 대비 |
| --- | ---: | ---: | ---: | ---: |
| 단일 노드 | 750.6118 | +1.0230% | 286.0837 | 2.6237x |
| 3노드 | 926.8453 | -0.4858% | 114.0644 | 8.1256x |

- 3노드 nested p99는 11.1914165 ms, 공개 기준 11.3688903 ms 대비 **-1.5610%**.
  직전 전체 실행의 +8.652808% 실패는 삭제하지 않으며, 비동시 단일 실행 차이만으로
  변경의 인과적 효과를 확정하지 않는다.
- summary SHA-256: `9fedfc3cc4664e673dabf82fa28c80ecc3eac02090824ee176b36ff8ca062b05`;
  budget-check: `0d18549f9bf464345cfbea4aba5bc717e2dfdd5fb0cd34063689c87803bde5c7`;
  엔진 테스트 로그: `61fd817dcc78bde2b78a994e16961bb396119efb0a5bc83b4434a46abad26334`.
- 사전 정의된 12개 실행 반복 절차를
  `target/core-replacement-p03/nested-set-move-repeated-first`에서 시작했다.
  반복 검증 및 운영 보안/내구성/소스-빌드 증거는 아직 미완료이므로 이 단일 실행의
  수치 통과를 P03/S01 완료나 릴리즈 승인으로 처리하지 않는다. ledger 제외 없음.

### P03: nested 소유권 이동 후보의 반복 전체 검증 (2026-09-07)

- `nested-set-move-repeated-first`의 예정된 12개 실행을 약 1,092초에 완료했다.
  각 실행 오류 0건, 실행 입력 해시 검증 통과. **반복 수치 게이트 실패(exit 1)**.
  앞선 단일 전체 실행의 44/44 통과로 이 실패를 대체하지 않는다.

| 반복 | 비교 기준 | 5% 초과 지표 | 악화율 |
| --- | --- | --- | ---: |
| 1 | 공개 v0.6.0 → 후보 | 단일 노드 refresh p99 | 5.237048% |
| 2 | 공개 v0.6.0 → 후보 | 3노드 ranking p99 | 5.237035% |
| 2 | paired v0.6.0 → 후보 | 단일 노드 lexical p95 | 5.196121% |
| 2 | paired v0.6.0 → 후보 | 3노드 ranking p99 | 6.706036% |
| 2 | paired v0.6.0 → 후보 | 3노드 nested p99 | 8.870145% |

- 반복 1의 paired 후보 비교는 44개 모두 통과했다. 공개값 대비 후보 초과는
  refresh p99 18.166181 → 19.117553 ms 및 ranking p99 11.304207 → 11.896213 ms다.
- 기준선 자체의 공개값 대비 초과도 보존한다. 첫 기준선은 단일 refresh p99
  +6.880429%, 3노드 lexical p99 +5.262754%, ranking p99 +10.255577%, facet p95
  +5.007634%, facet p99 +7.071607%. 마지막 기준선은 3노드 lexical p99
  +7.468414%, facet p99 +6.054645%다. 변동을 근거로 한도를 완화하지 않는다.
- 단일 변경의 인과적 5% 이상 비용 및 최적화 불가가 입증되지 않았으므로
  ledger 제외 없음. 후보 채택/P03 완료는 보류한다. 측정 소유 프로세스와
  OpenSearch 컨테이너 정리를 확인했으며 기존 사용자 컨테이너는 유지했다.
- plan SHA-256: `ac3dfdcb063ef62959e34619c05c924cea57769b25db426782739c68fa7da6f8`;
  result: `05a4e9c9d3bbe207ce919c6e099d15a8bb37c1ad6dd92c4c06bfb1f7c1ebb4d1`.

### C05: nested bool 정합성 결함 live 재현 (2026-09-07)

- 성능 반복 검증 종료 후 별도의 소유 단일 노드에서 진단했다. 1 shard/0 replica,
  명시적 nested mapping에 a(payment/blocked), b(payment/accepted), c(cache/accepted)
  문서 3개를 넣고 refresh한 뒤 7개 bool 조합을 각각 size 0/10으로 검색했다.
  이는 기능 진단이며 성능 측정이나 C05 전체 완료 증거가 아니다.
- 고정 v0.6.0 `db244133...f1f57`과 후보 `3fae5fd0...78f5e`의 실제 서버 실행 파일을
  확인했다. 각각 **14개 중 10개 요청에서 문서 집합 또는 total 오류**가 재현됐다.
  기본 must 및 optional should 대조군 4개는 통과했다. 이번 소유권 이동 최적화로
  새로 생긴 오류가 아니라 공개 기준선에도 존재하는 코어 검색 결함이다.
- 동일 mapping/문서/요청을 고정 OpenSearch 2.19.0 이미지로 실행했으며 **14개 모두
  기대값과 일치**했다. 이 참조는 성능 비교에 사용한 2.19.0이며, 기존 전체 기능
  참조인 3.7.0-SNAPSHOT의 전면 검증을 대신하지 않는다.

| nested 내부 bool | 기대 ID (OpenSearch 일치) | Steelsearch 반환 ID |
| --- | --- | --- |
| must payment + must_not blocked | b | a, b |
| must payment + should accepted + minimum_should_match 1 | b | a, b |
| should payment + must_not blocked | b | a, b |
| must_not blocked만 | b, c | a, b, c |
| must payment + should payment/accepted + minimum_should_match 2 | b | a, b |

- 코드 확인 지점: `native_nested_child_ordinals_for_query`의 bool 처리는 required
  집합을 조기 반환하면서 must_not/필수 should를 반영하지 않는다. 또한
  `nested_child_source_matches_query`는 원본 자식과 경로로 감싼 자식의 판정을 OR로
  합쳐, 원본에 없는 qualified field에 대한 부정 조건이 참이 되는 경로가 있다.
  두 경로를 함께 검증해야 하며 단순히 후보 수집만 source fallback으로 돌려서는
  must_not-only 오류까지 해결했다고 볼 수 없다.
- **다음 우선 작업(C05 내부 단위)**:
  1. 위 실패를 엔진 회귀 테스트로 고정하고 shard scope, size 0/page/sort/count/
     aggregation 및 동일 부모의 여러 자식 조합을 확대한다.
  2. child ordinal bool 집합 연산에 부정 조건과 minimum_should_match를 정확히
     반영한다. 후보 상위 집합을 정확한 결과로 취급하지 않는다.
  3. source fallback의 nested 필드 평가 문맥을 OpenSearch에 맞추고, 양성/음성
     혼합 조건이 서로 다른 자식이나 다른 문맥으로 분리되어 성립하지 않게 한다.
  4. 엔진 전체 테스트 및 실제 HTTP 참조 비교를 통과한 뒤, 코어 전체 기능 fixture와
     공개 v0.6.0 대비 전체 벤치마크를 재실행한다. P03 반복 실패는 계속 미해결로 둔다.
- 재현 스크립트는 `target/core-replacement-p03/nested-bool-diagnostic.py` 및
  `nested-bool-reference.py`. 요청/응답 원본, 기대값, 실행 파일 해시를 결과에 보존했다.
  Steelsearch 결과 SHA-256:
  `958007ef3a49f3eb2fc89913097ae195b7b628f273a3d783cd21c09984926a7c`;
  OpenSearch 결과:
  `d6f79a5968711fb771e955303a038ca5c33d21fbb7ece5c062bacc6919c32c04`.
  양쪽 소유 프로세스/컨테이너 정리 확인. 아직 런타임 정합성 수정은 하지 않았으며,
  기능 결함을 성능 예외로 제외하지 않는다. 40개 전체 구현 범위는 유지한다.

### C05: nested bool 정합성 수정 후보 (2026-09-07)

- child ordinal bool 연산은 기존 `effective_bool_minimum_should_match`를 재사용한다.
  must/filter 교집합에 필수 should 집합을 결합하고 must_not 집합을 차감한다.
  2개 이상 should는 **동일 자식 ordinal별 일치 clause 수**로 판정하며, 형제 자식의
  일치를 부모 단위로 합산하지 않는다. optional should는 필터 조건으로 강제하지 않는다.
- source fallback은 경로로 감싼 nested 자식 문맥 한 곳에서만 전체 query를 평가한다.
  raw 자식과 qualified 자식의 bool 결과를 OR로 합치지 않는다. 전역 후보 fallback과
  source scan에서도 선택 샤드를 유지해 범위 밖 문서가 total/page에 섞이지 않게 했다.
- `nested_bool_candidates_and_pages_preserve_child_boolean_semantics`를 추가했다.
  13개 조합, 3샤드의 전체/부분/빈 선택, size 0/전체/부분 페이지, 형제 자식·중복 부모·
  refresh 전 문서를 확인한다. 빌드 진행 중이므로 아직 테스트 통과로 기록하지 않는다.
- 수정 직전 바이너리 `3fae5fd0...78f5e`는
  `target/core-replacement-p03/steelsearch-before-nested-bool-fix`에 보존했다.
- `target/core-replacement-c05/generate-nested-bool-fixture.py`로 별도 130개 HTTP
  케이스를 생성했다(13조합 × 1/3샤드 × total/hits/page/count/aggregation).
  `run-live.py`는 기존 `search_compat.py`로 이 fixture와 기존 1,180건 코어 검색
  fixture를 소유 후보/3.7.0-SNAPSHOT 참조에 순차 실행한다. 준비/구문 검사만 끝났고
  live 결과는 아직 없다. 새 코드가 실제 지원하는지 기능 검증과 전체 벤치마크로
  확인하기 전에는 C05/P03/S01 완료나 릴리즈 승인으로 처리하지 않는다.

### C05/C03: 경계 조건 및 수정 전 확장 참조 (2026-09-07)

- 첫 엔진 실행은 826/829 통과, 신규 경계 사례와 경로 없는 필드를 쓰는 기존
  grouped nested 테스트 2개가 실패했다. OpenSearch 3.7.0 실제 응답에서 should 1개에
  minimum_should_match 2는 결과 0건임을 확인했고, 공통 source predicate의 상한
  제한을 제거했다. 경로 없는 단일 필드를 native 로컬 필드로 오인하지 않도록
  후보 수집 진입부에서 scoped source 평가로 돌린다.
- 기존 3개 테스트의 nested 조건을 `comments.author`/`comments.tag`로 명시했다.
  목적과 기대 ID는 유지했고, 경로 없는 term의 양성/부정은 별도 회귀 사례로 추가했다.
  실제 참조에서도 `kind:payment`는 결과 없음, `must_not status:blocked`는 전체
  nested 부모를 반환한다. 기존 alias-like 축약 필드 동작을 OpenSearch 계약으로
  간주하지 않는다. 다중 필드/문자열 query 등 나머지 C05 조합 검증은 계속 필요하다.
- 두 번째 전체 엔진 실행은 827/829 통과했고 빈 bool + minimum_should_match만
  지정한 경우의 2개 테스트가 실패했다. 참조 소스 `BoolQueryBuilder.doToQuery` 및
  실제 HTTP는 빈 bool을 match_all로 먼저 처리한다. 이에 공통 effective minimum
  계산에서 모든 clause가 비었을 때 0으로 처리했다. 일반적인 개수 초과 조건은
  그대로 불일치다. 추가된 빈 bool 사례를 포함한 최종 테스트 빌드는 진행 중이다.
- 최초 `live-before`에서 추가 fixture가 남은 상태로 기존 코어 suite를 실행해
  전역 샤드 수 검사 3개가 실패했다. 원본을 보존하고 소유 추가 인덱스를 양쪽에서
  삭제한 후 suite를 실행하도록 정리했다. 이후 기존 코어 1,180건은 모두 통과했다.
  아래 설정 결함도 확인되어 이를 단순 환경 간섭만으로 설명하지 않는다.
- **C03 별도 결함 확인**: 평면 `settings.number_of_shards=3`, replica 0으로 생성하면
  Steelsearch 설정 응답에 평면 3/0과 기본 nested `settings.index` 1/1이 공존하며,
  `_search_shards`는 [0]만 반환한다. OpenSearch는 [0,1,2]다. 따라서 최초 평면 fixture의
  '3샤드'는 요청 형식일 뿐 실제 3샤드 동등성 증거가 아니다. 정규화 및 metadata/
  routing/engine 일치 여부를 C03에서 수정해야 한다.
- 중첩 `settings.index` 형식의 추가 fixture에서는 양쪽 모두 [0,1,2]를 보고했다.
  평면 실패를 삭제하거나 입력을 교체해 통과시키지 않고 **두 형식 모두 보존**한다.
  기존 성능 실행기 `run-http-load-baseline.py`는 원래 중첩 형식을 사용한다.
- 최종 fixture는 16 bool 조합 × 요청 shard 수 1/3 × total/hits/page/count/aggregation
  = 형식당 160건이다. `live-before-both-settings`에서 수정 직전 후보
  `3fae5fd0...78f5e`는 평면/중첩 각각 **62 통과, 98 실패, skip 0**;
  기존 코어는 **1,180 통과, 실패/skip 0**. 모든 요청/응답 및 설정/샤드 조회는
  결과에 보존했다. 이 기능 비교는 빌드와 병행했으므로 성능 측정에 사용하지 않는다.
- **C05 별도 미완료 경로**: nested `_count`는 노드의
  `handle_count_route` → `validate_query_payload_for_validate_route`에서
  `unsupported count query: unsupported query type` 400을 반환한다.
  count는 엔진과 별개의 `matches_query_body` 및 documents_state scan을 사용한다.
  단순히 파서 허용만 추가하지 말고 검색과 같은 의미 평가를 사용하면서
  alias filter, routing, refresh 가시성, 인증/권한, root/multi-index 및 오류 계약을
  보존하도록 구현해야 한다. count 실패는 삭제/제외하지 않고 C05 완료를 차단한다.

### C05: 엔진 회귀 검증 통과 (2026-09-07)

- 최종 16조합 회귀 테스트 통과 후 동일 실행 파일의 엔진 전체 테스트를 직렬
  실행했다. **829 통과, 실패/ignored 0**, 약 5.17초. 첫 826/829 및 다음 827/829
  실패 로그도 보존했다. 중간 한 빌드는 테스트 입력 수정으로 오래된 컴파일을
  명시적으로 중단한 것이며, 프로세스 장애나 timeout 재시도로 분류하지 않는다.
- 최종 로그: `target/core-replacement-c05/engine-final.log`, SHA-256
  `25fb1b76056b29680e983568f260bb323a8ff3333113e27cd4bf9df727224592`.
  `git diff --check` 통과. release 실행 파일 빌드는 진행 중이다.
- `live-before-both-settings`에서 수정 전 `3fae5fd0...78f5e`의 두 160건 fixture는
  각각 62 통과/98 실패였고, 격리 후 기존 코어 1,180건은 모두 통과했다.
  중첩 설정 fixture의 실제 `_search_shards`는 양쪽 모두 [0,1,2]임을 확인했다.
  평면 설정의 Steelsearch [0] 차이는 유지한다. 수정 후에도 이 설정 결함과 별도
  `_count` 400 경로가 남으면 C03/C05 전체 완료로 처리하지 않는다.

### C05/C06: 수정 후 live 및 전체 성능 결과 (2026-09-07)

- release 빌드 성공. 현재 후보 SHA-256:
  `970f28c60a66b55de25d21b11b46c17494e5c9e9123ce8eb0d3d61e13493c9f0`.
  `target/release/steelsearch`는 이 후보이며 직전 `3fae5fd0...78f5e`는 별도 보존한다.
- `target/core-replacement-c05/live-after`에서 평면/중첩 설정 160건씩과 기존 코어
  1,180건을 OpenSearch 3.7.0-SNAPSHOT에 실제 비교했다. 각 추가 fixture는
  **98 통과 / 62 실패 / skip 0**, 기존 코어는 **1,180 통과 / 실패·skip 0**.
  직전 후보의 동일 케이스 대비 형식당 36건, 총 **72건의 실패를 해결**했고,
  기존 통과 케이스가 새로 실패한 것은 없다.
- 각 형식의 검색 total/hits/page 96건은 모두 통과했다. 중첩 설정에서는 실제
  1/3샤드를 확인했다. 평면 설정의 3샤드 요청은 여전히 [0]이므로 해당 결과를
  실제 3샤드 동등성 통과로 해석하지 않는다.
- 형식당 남은 62건은 `_count` 400 **32건** 및 집계 **30건**이다. 집계는 numeric
  terms bucket이 비어 있고, 빈 bool/경로 없는 필드 일부의 value_count도 다르다.
  native `parse_terms_aggregation`이 `order`를 지원하지 않아 native request 생성이
  실패하고 node fallback으로 넘어가는 코드 경로를 확인했다. node의 terms 집계는
  `key_value.as_str()`만 받아 숫자를 건너뛴다. fallback의 nested query 판정도
  엔진과 불일치하므로 **C06 ordered numeric terms와 fallback 의미 일치**가 필요하다.
  `order` 옵션을 지우거나 숫자를 문자열로 바꿔 실패를 숨기지 않는다.
- live execution SHA-256:
  `33bc7b0d4dff17c9edb2045dfe27b91533de243c4bf6ac98b2809443f2e5e25b`;
  평면 report: `db32e55d1aceb0a70f31ed09140b1421c837ee59dea774e55574e5c372004de4`;
  중첩 report: `322213bde3ec80fe600bacc0d720f0a001950d8dfc846e543f61d773a34244c9`;
  기존 코어: `2bb2116eab5179f054b05272857d9da0fa31012ef81bb837e298b1e2deaf8893`.
- 이후 빌드/기능 테스트/프로파일러 없이 `full-matrix-first`의 4개 전체 혼합 부하를
  약 417초에 완료했다. 요청 오류 모두 0건, 실행 전후 바이너리와 실행기/기준선
  해시 동일, 보고서 정합성 통과. **수치 예산은 43/44 통과, 전체 실패(exit 1)**.

| 토폴로지 | 후보 처리량 (ops/s) | 공개 v0.6.0 대비 | OpenSearch 2.19.0 처리량 | OpenSearch 대비 |
| --- | ---: | ---: | ---: | ---: |
| 단일 노드 | 745.9851 | +0.4003% | 283.8194 | 2.6284x |
| 3노드 | 913.0922 | -1.9625% | 113.4011 | 8.0519x |

- 실패 지표는 단일 노드 refresh p99: 공개 18.166181 ms → 후보 19.241885 ms,
  **+5.921463%**, 한도 19.074490 ms 초과. 기존 후보 반복에서도 이 지표의 공개값
  초과와 기준선 자체 변동이 있었으므로, 이번 bool 변경의 단일 인과관계 및
  최적화 불가로 단정하지 않는다. 최초 기준선과 5% 한도는 그대로 유지한다.
- 전체 summary SHA-256:
  `2634127bb538dd92f90d014a446be44c44fc749ef2ad991105540ed7abd977e5`;
  budget: `11f5683f57e8c7798c857e52b257ae75cf65bc9ebcbf21482344078713d7d497`.
  기능/성능 실행의 소유 프로세스 및 컨테이너 종료 확인. ledger 제외 없음.
  **C03/C05/C06/P03 및 전체 40개 계획은 미완료**이며 릴리즈 승인도 보류한다.

### C03: 인덱스 생성 설정 정규화 진행 (2026-09-07)

- 평면/중첩/점 표기 설정을 기본값 적용 전에 공통 형식으로 정규화하고,
  동일한 최종 설정을 native engine과 manifest에 전달하도록 수정했다.
  component/index template 각 계층도 병합 전에 정규화한다.
- OpenSearch `Settings.Builder.normalizePrefix`의 동일 leaf 충돌 규칙을
  로컬 참조 소스에서 확인했다. 접두어 없는 설정의 대체를 마지막에 적용하며,
  archived 및 wildcard 키는 접두어 자동 추가에서 제외한다.
  실제 REST 혼합 표기 충돌 비교는 아직 미실행이다.
- 회귀 테스트 3개를 추가했다: leaf 보존 및 멱등성, 네 가지 생성 설정 표기의
  `_settings`/`_search_shards`/native engine 샤드 수 일치, 계층별 병합 우선순위.
  첫 컴파일의 테스트 타입명 오류를 `NodeInfo`로 수정한 뒤 3개 모두 통과했다.
- node 전체 첫 실행은 588/589 통과. 기존 nested 테스트가 경로 없는 `author`에
  2건을 기대하던 부분에서 실패했다. 앞선 C05 live 참조 결과에 맞춰 경로 없는
  필드 0건과 `comments.author` 2건을 각각 검증하도록 보강했다.
  재빌드 후 전체 **589/589 통과**, 로그 보존 재실행도 589/589 통과했다.
  `target/core-replacement-c05/node-settings-normalization-full.log`는 초기 실패
  기록이며 SHA-256 `cbf10f18230d3808a0899d2398ac9541a927738f37eb6bce7890cb0297e6e302`.
  최종 `node-settings-normalization-final.log` SHA-256은
  `80fb83be5b89f9abb55beb8bd29e85069181de998f8d9f031e7431d7a4fcf15c`.
- 수정 전 바이너리는
  `target/core-replacement-c05/steelsearch-before-settings-normalization`에 보존했다.
  SHA-256 `970f28c60a66b55de25d21b11b46c17494e5c9e9123ce8eb0d3d61e13493c9f0`.
- 남은 검증: 후보 실행 파일 빌드, 실제 component/template REST 우선순위,
  OpenSearch live 비교, 새 후보 전체 비플러그인 벤치마크 및 고정 v0.6.0
  누적 44지표 판정. 설정 변경 API의 표기별 검증, auto-create 및 기존 저장
  메타데이터 처리도 별도 확인이 필요하다. C03 완료/성능 합격/제외 판정 없음.

### C03/C04/C05: 설정 live 확인 및 routing 차이 (2026-09-07)

- 새 실행 파일 빌드 완료. SHA-256
  `a6adc8450a550ed1eb59e5bff459b254bd3c9fd91869d4fe456e72856518b9f7`.
  `target/core-replacement-c05/live-settings-normalization`에 실제 OpenSearch
  3.7.0-SNAPSHOT 비교 원시 응답과 실행 기록을 보존했다.
- 양쪽 서버의 설정 검사 **64/64 통과**: 평면/중첩/점 표기/동일 leaf 충돌,
  component 순서, index template 우선순위, 생성 요청 우선순위, 실제 샤드
  그룹과 ID, 매핑/alias 보존 및 소유 리소스 정리까지 확인했다.
  이는 설정 생성의 제한된 계약 검증이며 C03 전체 완료 증거는 아니다.
- 확장 검색은 평면 및 중첩 설정 각각 98/160 통과, 62건 실패로 이전과 같다.
  `_count` 및 집계 미구현 차이는 계속 남아 있다. 기존 코어는
  **1,179/1,180 통과**, `pit_open_routing_multishard_search` 1건이 새로 실패했다.
  OpenSearch는 doc-a/doc-b 2건, 후보는 doc-a 1건을 반환했다.
  설정 수정 전의 1,180건 통과를 현재 후보의 통과 증거로 재사용하지 않는다.
- 원인 후보: node와 engine의 `opensearch_routing_shard`가 모두
  `floorMod(hash, primary_shards)`를 사용한다. 참조 `OperationRouting`은
  `floorMod(hash, routing_num_shards) / routing_factor`를 사용하며, 참조
  `MetadataCreateIndexService.calculateNumRoutingShards`는 기본 routing shard
  수를 primary shard 수의 2의 거듭제곱 배수로 확장한다. 평면 3샤드 설정이
  이전에는 1샤드로 처리되어 가려졌던 차이로 추정한다. 실제 hash/shard 비교는
  후속 증거가 필요하며 이 단계에서 인과관계 검증 완료로 표기하지 않는다.
- 후속 구현 단위는 C04/C05 routing 계약으로 잡는다. 기본값/명시적
  `number_of_routing_shards`/partition 설정 검증, 엔진 쓰기 배치와 검색 범위,
  GET/delete/OCC, PIT, 복구 및 영속 샤드 식별을 함께 정합화해야 한다.
  기존 저장 데이터의 샤드 배치를 무조건 재해석하지 말고 호환성 정책과
  재시작 테스트를 먼저 확정한다. 응답만 바꾸거나 fixture routing을 바꿔
  실패를 숨기지 않는다. 구현 후 node/engine 전체 테스트, live 비교,
  전체 비플러그인 벤치마크와 고정 v0.6.0 누적 게이트를 다시 실행한다.

### C03: 설정 후보 전체 성능 결과 (2026-09-07)

- `target/core-replacement-c05/settings-normalization-full-first`: 새 후보와
  고정 OpenSearch 2.19.0 이미지의 단일/3노드 전체 4개 혼합 부하를 415.45초에
  완료했다. 빌드/기능 테스트/프로파일러와 겹치지 않았고 요청 오류는 모두 0건이다.
  후보 실행 파일 및 실행기/공개 기준선 파일 해시는 실행 전후 일치했다.
- 보고서 정합성 통과. 최초 공개 v0.6.0의 44개 독립 지표 중 **43개 통과,
  1개 실패**, budget exit 1이다. 단일 노드 sort_filter p99는
  14.151069 ms → 14.868118 ms, **+5.067097%**로 한도 14.858623 ms를 넘었다.
  반올림으로 통과시키거나 다른 지표 개선으로 상쇄하지 않는다.

| 토폴로지 | 후보 처리량 (ops/s) | 최초 v0.6.0 대비 | OpenSearch 2.19.0 처리량 | OpenSearch 대비 |
| --- | ---: | ---: | ---: | ---: |
| 단일 노드 | 743.7129 | +0.0945% | 277.9160 | 2.6760x |
| 3노드 | 929.4113 | -0.2103% | 112.4428 | 8.2656x |

- 위 수치는 기존 개발용 보안/내구성 프로파일의 혼합 부하이며 운영 환경
  동등성을 증명하지 않는다. 단일 변경의 성능 인과관계와 최적화 불가도
  입증되지 않았으므로 ledger 제외 없음. 정상 완료 및 릴리즈 승격은 보류한다.
- 전체 summary SHA-256:
  `56aeb070d3387e78b03da6e58ef44911a97739328447fc6feb0a559b95ad435e`;
  budget: `72dd5f8da9b6fbcb6932c2daba3812df4a833071863f30f7c4f073b6efe03228`.
  설정 live execution SHA-256:
  `d775e6385a36fa2fba9cbdef886a0638944c4fdd9ae5f021a8f449c3fb1b289c`.
  소유 프로세스/컨테이너 종료 확인. C03/C04/C05/C06/P03 및 전체 계획 미완료.

### C04/C05: routing 계약 진단 및 공통 계산 초안 (2026-09-07)

- 동일 a6adc845 후보로 별도 소유 서버의 focused live 진단을 실행했다.
  최초 `target/core-replacement-c05/live-routing-before`는 98개 비교 중
  30개 차이였다. partition 크기 3은 참조가 허용하므로 잘못된 설정으로
  분류했던 진단 이름을 보정하고, 유효한 대조군으로 쓰기/검색까지 확대했다.
  초기 결과는 덮어쓰지 않았다.
- `live-routing-expanded-before`는 **121개 비교 중 80개 일치, 41개 차이**.
  41개에는 후보만 잘못된 인덱스를 생성해 발생한 cleanup 차이 3개가 포함된다.
  실질 API 상태/결과 차이는 38개다. 각 유효 프로파일은 생성, 10개 문서 쓰기,
  refresh, 5개 routing 값의 shard ID 및 실제 검색 ID, 정리까지 23개를 비교했다.

| 프로파일 | 비교 수 | 차이 수 |
| --- | ---: | ---: |
| 기본 routing, primary 3 | 23 | 9 |
| 명시적 routing shards 3 | 23 | 0 |
| 명시적 routing shards 12 | 23 | 7 |
| routing shards 12, partition 2 | 23 | 10 |
| 기본 routing, partition 3 | 23 | 9 |
| 잘못된 routing shards 4/2 및 routing 12의 partition 13 | 6 | 6 |

- 잘못된 세 설정은 모두 후보 200, 참조 400이다. 참조에서 partition 제한은
  primary 수가 아니라 routing shard 수 기준임을 `IndexMetadata.Builder`에서도
  확인했다. URI, 요청/원시 응답, 후보 해시 및 runner/probe 해시를 보존했다.
  expanded execution SHA-256:
  `6620d200cb0999f2e50b2bf3d06e3f50e175c8faed2953324b4d9818e7bce376`.
- `crates/os-core/src/index_routing.rs`에 공통 계산 초안을 추가했다.
  유효한 layout 생성, 기본 split 정책, 명시적 배수/partition 검증,
  document ID hash partition offset, search shard 범위, 음수 floor modulo,
  Java signed 32-bit wrapping을 포함한다. 해시 입력은 기존 UTF-16LE Murmur3
  구현 결과이며, 이 모듈은 문자열 해시를 새로 중복 구현하지 않는다.
- `cargo +nightly test --locked --release -p os-core` (`RUSTFLAGS=-Awarnings`):
  새 계산 테스트 5개와 기존 통합 테스트 8개 통과. 로그:
  `target/core-replacement-c05/routing-core-tests.log`, SHA-256
  `92f7b34d9b8b15163e635898bd388e54fc6036e27dddcc684f5e792ea26b2c6b`.
- **아직 node/engine 실행 경로에 연결하지 않았다.** 현재 실행 파일과 live
  실패는 그대로이며 공통 모듈 테스트를 routing 구현 완료로 간주하지 않는다.
  다음 단계는 schema/metadata의 routing layout 저장과 기존 schema hash 보존,
  ShardedDocuments 배치/복구, node routing scope/GET/delete/PIT 연결이다.
  기존 배치 변경을 단순 hash 함수 교체로 처리하지 않는다. 원본 데이터와
  복구 로그를 보존한 migration/재시작 테스트 및 오류 응답 계약이 필요하다.
- 서버 연결 후 node/engine 전체 테스트, 확장 live 및 전체 코어 비교,
  전체 비플러그인 성능과 최초 v0.6.0 44지표 게이트를 다시 실행한다.
  공통 모듈만 추가한 단계에서 새 성능 합격을 주장하지 않는다.
  소유 진단 서버 종료 확인, ledger 제외 없음, 전체 계획 계속 미완료.

### C04/C05: engine routing 연결 초안 (2026-09-07)

- `IndexRouting` 저장 형식을 추가했다. 역직렬화는 생성 검증을 통과해야 하며
  누락 필드/잘못된 배수/partition 0/알 수 없는 필드는 거부한다.
- `TantivyIndexSchema.routing: Option<IndexRouting>`을 추가했다.
  None은 직렬화에서 생략해 기존 스키마 bytes/hash를 보존하는 설계이며,
  해당 schema의 routing은 기존 `hash % primary_shards` 배치를 유지한다.
  새 인덱스 생성은 modern 기본값 또는 명시적 routing 설정을 검증해 Some으로
  저장한다. schema와 layout의 primary shard 수가 다르면 거부한다.
- `ShardedDocuments`의 insert/get/delete 배치 계산, 검색 스냅샷 복사,
  manifest 복구의 shard 검증 및 재구성에 layout을 연결했다.
  단일 기본 생성 경로와 테스트 생성자도 보완했다. partition 1에서는
  추가 document ID 해시를 계산하지 않는다.
- 엔진 회귀 테스트 3개를 추가했다: legacy 직렬화/배치 유지와 mismatch 거부,
  앞선 live 기본/명시적 3/12 shard vectors 및 schema round-trip,
  잘못된 설정의 생성 실패와 인덱스 미생성. **아직 실행하지 않았다.**
- engine 테스트 코드는 `cargo +nightly check --locked --release
  -p os-engine-tantivy --tests` 정적 검사를 통과했다. 최초 검사에서 공통 crate
  의존성 및 두 생성 경로 누락을 발견해 보완했다. `Cargo.lock` 변경은
  os-engine-tantivy에 os-core 의존성 한 줄 추가뿐이며 새로운 외부 패키지는 없다.
- os-core 전체 실행: 단위 6개/통합 8개 통과. 로그
  `target/core-replacement-c05/routing-persistence-core-tests.log`, SHA-256
  `a1158bb26eec67dd9f39ff35c6433f7dd0133baa8f74bded680e852f8a1038a5`.
  수정 전 실행 파일은 `steelsearch-before-engine-routing`에 보존했고
  a6adc845 해시가 일치한다. target/release 실행 파일은 아직 교체하지 않았다.
- **배포 금지인 중간 상태**: node의 routing scope/dirty shard/GET/PIT 계산은
  기존 방식이다. node가 기존 metadata에서 엔진 schema를 재생성할 때 None의
  legacy 정책을 유지하는 연결도 아직 없다. 따라서 새 소스로 서버를 빌드해
  기존 데이터를 열거나 modern engine 변경만 성능 합격으로 승격하면 안 된다.
- 후속 필수: node metadata/layout 계약과 legacy 재생성 연결, routing 필수
  mapping 및 누락 routing 오류, partition의 모든 쓰기/OCC/replay 경로 검증,
  실제 legacy/new manifest 복구와 재시작 테스트, engine/node 전체 실행,
  live 코어 비교 및 전체 비플러그인 성능/고정 v0.6.0 44지표 게이트.
  이번 정적 검사와 core 테스트는 이 검증들을 대체하지 않는다. 구현 단위,
  성능 합격, 전체 계획 완료 또는 ledger 제외로 판정하지 않는다.

### C04/C05: node routing 연결 초안 (2026-09-07)

- engine에 `index_routing(index)` 조회를 추가했다. schema 전체를 clone하지 않고
  실제 문서 저장소의 검증된 layout을 Copy로 반환한다.
- node의 일반/native 검색, PIT 문서 필터, pending delete 필터, count 및
  by-query routing 필터를 같은 layout으로 변경했다. partition routing 검색은
  offset별 shard 집합을 사용하며 중복 shard는 제거한다. `_search_shards`도
  한 routing 값이 여러 shard를 선택하는 경우를 표현한다.
- dirty shard 추적, refresh 후 dirty shard 계산, operation log 조회/복구의
  shard 선택, 같은 ID의 routing별 문서 조회, fallback `_shard_doc` 계산에
  document ID partition offset을 포함한 같은 계산을 연결했다.
- node 테스트 2개를 추가했다: 앞선 live의 default/명시적 3/12/partition 2
  결과에 대한 scope와 문서 필터 검증, engine layout 조회와 partition shard
  목록/dirty shard 추적 검증. 기존 테스트의 primary 수 콜백 한 곳을 layout
  콜백으로 바꾸고 신규 인덱스용 테스트 계산 도우미도 modern 정책으로 맞췄다.
  **추가/변경 테스트는 아직 실행하지 않았다.**
- `cargo +nightly check --locked --release -p os-node --lib --tests`
  (`RUSTFLAGS=-Awarnings`) 통과. 최초 검사의 콜백 타입 오류를 수정했다.
  최종 로그 `target/core-replacement-c05/routing-node-check.log`, SHA-256
  `b65d97c967cb13bb2fd061b2f5b86011ef366acea387375a92a9808f93395384`.
  `git diff --check` 통과. 실행 파일은 여전히 a6adc845이며 교체하지 않았다.
- **기존 데이터 배포 금지 유지**: 현재 node layout 조회는 엔진을 우선하고,
  엔진이 없는 metadata-only 인덱스는 legacy 배치를 사용한다. 기존 metadata와
  새 metadata의 layout 저장 구분 및 복구 시 재생성 연결이 미완료다.
  복구 도중 기존 엔진을 참조하거나 새 layout을 legacy로 해석하지 않도록
  metadata 검증/확정 → operation log 병합 → engine 재구성 순서를 정리해야 한다.
  기존 `rebuild_native_engine_from_recovered_runtime_state`가 create/delete 오류를
  무시하는 부분도 안전한 오류 전달/시작 차단과 함께 처리해야 한다.
- 다음 필수 작업은 metadata layout 저장/legacy 보존/복구 순서와 오류 전파,
  routing 필수 mapping/쓰기 및 OCC 계약, 실제 재시작과 engine/node 전체 테스트,
  전체 live 및 비플러그인 성능 게이트이다. 이 중간 정적 검사는 실행/성능
  합격 증거가 아니며 C04/C05 완료, 릴리즈 가능, 제외로 판정하지 않는다.

### C04/C05/D02: routing metadata 재구성 연결 (2026-09-07)

- 엔진에 `create_index_from_schema`를 분리했다. 신규 생성은 설정에서 modern
  layout을 계산하고, 복구는 저장 schema의 routing Some/None을 유지할 수 있다.
- 명시적 인덱스 생성 시 내부 `_steelsearch_routing` metadata에 검증된 layout을
  저장한다. node routing 계산은 이 metadata를 기준으로 하며, 필드가 없는 구형
  metadata만 legacy 배치를 사용한다. null/잘못된 layout/primary 수 불일치는
  오류다. 매번 JSON 값을 복제하지 않고 borrowed 역직렬화로 검사한다.
- shared runtime 상태를 메모리에 적용하기 전에 각 index layout을 검증한다.
  재구성은 모든 schema를 먼저 검증한 뒤 engine index를 교체하며, 구형 schema는
  routing None으로 유지한다. engine 생성/replay/refresh 오류를 반환하도록 바꾸고
  호출자는 기존 recovery-failed 플래그에 연결했다.
- 테스트 3개 추가: legacy/modern/손상 metadata 구분, 두 layout의 혼합 재구성과
  공개 GET metadata의 내부 필드 비노출, 잘못된 schema가 기존 engine 삭제 전에
  거부되는지 검증. node 전체 정적 검사 및 실제 **594/594 테스트 통과**.
  이전 단계에 추가한 routing scope/document filter/dirty shard 테스트도 통과했다.
  `target/core-replacement-c05/routing-node-full-first.log`, SHA-256
  `cfee628c79b01b4e18860aeb5f0ebb20ada887cbff675f53bd436db224c910c5`.
  engine 자체 전체 테스트 및 실제 프로세스 재시작 검증은 아직 미실행이다.
- **남은 안전성 문제**: 기존 recovery-failed 플래그는 task submission 중심의
  제한된 차단이다. 일반 읽기/쓰기 전체 차단 및 원본 파일 보호 증거가 없고,
  `persist_shared_runtime_state_to_disk`는 저장 성공 시 플래그를 지운다.
  따라서 이번 연결을 완전한 fail-closed 시작/복구라고 주장하지 않는다.
  실패 상태의 일반 요청과 저장 경로를 차단하고 원본을 보존하는 후속 조치가
  필요하다. 일부 잘못된 문서 metadata를 skip하는 기존 replay 루프도 남아 있다.
- 자동 생성/data stream backing index, 설정 변경, snapshot/rollover/resize 및
  모든 복구 진입점에 layout 저장 계약이 적용되는지 추가 검증해야 한다.
  실제 프로세스 재시작과 engine/node 전체 테스트, live 비교 및 전체 성능
  게이트까지 마치기 전 배포 금지/미완료 상태를 유지한다. 제외 판정 없음.

### D02: 복구 실패 이후 요청·저장 차단 (2026-09-07)

- recovery-failed 상태에서 일반 REST 요청에 503을 반환하고 shared runtime 및
  development shard 저장 진입을 차단했다. 같은 프로세스의 재동기화는 실패를
  자동 해제하지 않으며, 파일 누락이나 저장 성공으로 플래그를 지우지 않는다.
  직렬화 실패 시 빈 JSON을 저장하던 fallback도 제거했다. 저장 오류는 실패
  상태로 연결한다. 오류 문구는 task submission 대신 일반 request로 변경했다.
- 새 테스트는 조회/변경 REST 차단, 인덱스·문서 미생성, 손상 원본 bytes 보존,
  shard 파일 미생성, 파일 삭제 후에도 실패 상태 유지 및 파일 미재생성을 검증한다.
- 첫 node 전체 실행은 **593/596 통과, 3개 실패**. 신규 테스트 2개는 통과했다.
  기존 테스트는 복구 실패 후 task 조회/취소 및 손상 파일 덮어쓰기 허용,
  일반 조회 허용, 이전 오류 문구를 기대했다. 새 차단 정책에 맞춰 503과
  원래 task/document 상태 및 손상 파일 bytes 보존 검증으로 수정했다.
  수정 후 전체 재실행은 아직 남아 있다. 정상 재시작 테스트는 기존 계약을 유지한다.
- 첫 전체 로그: `target/core-replacement-c05/recovery-guard-node-full-first.log`,
  SHA-256 `683b7b614c147706347d5145a2f76e18fc5182ab6dff7083d0f4d592654636bb`.
  기존 테스트 수정 중 유사한 정상 재시작 블록을 잘못 대상으로 삼은 오류를
  정적 검사에서 발견해 되돌리고 올바른 부분 복구 테스트에 적용했다.
- 차단은 실패 확인 후 시작하는 요청/저장의 순차 실행 검증이다. 이미 실행 중인
  요청·저장과 복구 사이의 경쟁, 원자적 파일 교체, cold restart 시 원본 누락,
  transport/background 경로 및 명시적인 복구 절차는 추가 검증이 필요하다.
  전체 테스트 재실행과 전체 비플러그인 성능/고정 v0.6.0 게이트도 미완료다.
  따라서 D02 완료나 운영 안전성 확보로 판정하지 않으며 배포 금지를 유지한다.

### D02: 복구 차단 전체 재검증 결과 (2026-09-07)

- 수정된 기존 테스트를 포함한 node 전체 재실행은 **596/596 통과**.
  첫 실행의 593/596 기록은 그대로 보존했다. 새 실패 차단 테스트와 기존
  task/document 비변경, 손상 파일 bytes 보존 검증이 모두 통과했다.
  로그 `target/core-replacement-c05/recovery-guard-node-full-second.log`, SHA-256
  `257ea59e37e73ce9d2fff48ea1c42fe0b4046868a51b65cdc37fa11c7fdc102b`.
- 이는 프로세스 내부의 순차 복구 차단 테스트다. engine 자체 전체 테스트,
  실제 재시작/동시성/저장 오류 주입/live 비교/전체 성능 검증은 대체하지 않는다.
- 후속 코드 점검: data stream 생성 및 rollover가 engine 생성 없이 metadata와
  created-index 상태를 먼저 바꾸는 별도 경로를 사용한다. layout 검증 및 engine
  생성 성공 후 metadata를 반영하고 실패 시 기존 generation/alias/backing index를
  보존하는 순서가 필요하다. 자동 생성도 같은 계약으로 연결해야 한다.
- 기존 gateway 임시 파일 교체 구현과 shared runtime 직접 쓰기는 파일 및
  부모 디렉터리 동기화까지 갖춘 공통 내구성 계약을 증명하지 않는다.
  D02의 원자적 저장/동시성/누락 파일 판정은 계속 미완료다. 배포 금지,
  최초 v0.6.0 누적 5% 기준, 전체 40개 계획 범위와 ledger 제외 없음은 유지한다.

### C03/C04: data stream backing index 생성 연결 (2026-09-07)

- `create_native_index_from_entry`를 추가해 명시적 index 생성과 data stream
  backing 생성의 schema/layout 검증, routing 직렬화, native engine 생성을
  공유한다. routing 직렬화는 engine 생성 전에 완료한다.
- data stream PUT은 engine 생성 성공 후 created-index/manifest를 갱신한다.
  rollover도 새 engine 생성 성공 전에는 기존 generation과 backing 목록을
  변경하지 않는다. dry-run/조건 불충족은 engine을 생성하지 않는다.
  stream 삭제 시 기존 native index도 정리해 재생성 충돌을 방지한다.
- 테스트 2개 추가: template의 primary 3/routing 12가 engine과 metadata에
  동일하게 적용되는지, dry-run과 기존 engine 이름 충돌 시 상태 유지,
  정상 rollover/삭제/재생성, 잘못된 layout 생성 실패 시 metadata 미반영.
  이 테스트들은 아직 실행 전이다. node 정적 검사는 engine 전체 빌드 뒤
  실행해 통과했다. `data-stream-routing-node-check.log` SHA-256:
  `cdcf2833b0a5dde091db39f3393dd0e53f7c8123f02b5f79f0a5ecee15e0337d`.
- engine 자체 전체 테스트는 **832/832 통과**. 빌드 중 engine 소스는 변경하지
  않았다. `target/core-replacement-c05/routing-engine-full-first.log` SHA-256:
  `686eabd28e67d5fafcb57b70b30c5fbb7152d269c3da021b19c49a49fc5c5cea`.
  기존 node 596/596은 이번 data stream 수정 이전 결과이므로 새 node 전체
  테스트의 통과 증거로 재사용하지 않는다. 두 실행 프로세스 종료 확인.
- 자동 생성 경로, 삭제 도중 예외의 전부 아니면 전무 처리, 동시 요청/저장 실패,
  실제 live 및 전체 성능 검증은 남아 있다. 이 변경을 C03/C04 전체 완료나
  운영 원자성 보장으로 해석하지 않는다. 배포 금지 및 제외 없음 유지.

### C03/C04/C05/D02: 통합 후보 실제 기능 검증 (2026-09-07)

- data stream 변경 후 node 전체 **598/598 통과**. 로그
  `target/core-replacement-c05/data-stream-routing-node-full-first.log`, SHA-256
  `b62c1d34e97ce029b2c345f136ad36370f8083fca812be4d19cb4e06eb048dd1`.
  기존 engine 832/832 결과와 함께 기록하되 둘의 검증 범위를 구분한다.
- 새 실행 파일 SHA-256:
  `894b33e68d17a487cf5b6f63e1fbc165ab12dc94eb3dd2e47e741b7d01bb11d9`.
  사용자 기존 데이터가 아닌 새 소유 서버/데이터 경로에서 OpenSearch
  3.7.0-SNAPSHOT과 실제 비교했다. 결과 경로:
  `target/core-replacement-c05/live-routing-and-stream-after`.
- 설정/data stream **84/84 통과**. 기존 설정 64개에 template 기반 3샤드
  stream 생성, 문서 쓰기/검색, rollover, generation 및 backing shard 수와
  정리 검사를 추가했다. routing **118/118 통과**. 기존 121개 중 후보에만
  잘못 생성됐던 인덱스의 cleanup 비교 3개는 양쪽이 생성 거부하면서 사라졌다.
  기존 38개 API 상태/결과 차이가 해결됐으며 실패를 필터링한 결과가 아니다.
- 기존 코어 검색 **1,180/1,180 통과**, setup 실패와 skip 0.
  `pit_open_routing_multishard_search`의 이전 doc-a 1건 vs 참조 2건 차이도
  해결됐다. core report SHA-256:
  `c7bf90488c9089eec3ef829e647a0f1d8033f1c78163c09e9f21e63294c76ac9`.
- 확장 nested fixture는 평면/중첩 설정 각각 **98/160 통과, 62건 실패**로
  이전과 같다. `_count` 32건과 집계 30건의 차이는 여전히 미해결이며
  이를 빼지 않았으므로 통합 live runner 자체는 exit 1이다.
- 실행 전후 후보/fixture 해시 동일. live execution SHA-256:
  `88b2f9cb9363efd965b46fbca7c8deabb454b8d1167a812a88607d3bd4c09e95`.
  이후 빌드/기능 실행과 분리해 `routing-and-stream-full-first`에 전체
  비플러그인 성능 4개 시나리오를 실행 중이다. 아직 성능 합격 판정 없음.
  실제 재시작/동시성/원자적 저장/자동 생성/남은 API 의미 차이 등 전체 계획은
  계속 미완료이며 배포 금지 및 ledger 제외 없음 유지.

### C03/C04/C05/D02: 통합 후보 전체 성능 결과 (2026-09-07)

- `target/core-replacement-c05/routing-and-stream-full-first`: 후보 894b33e와
  고정 OpenSearch 2.19.0 이미지의 단일/3노드 4개 전체 혼합 부하를 416.69초에
  완료했다. 빌드/기능 테스트와 겹치지 않았으며 요청 오류는 네 환경 모두 0건.
  실행 전후 바이너리와 실행기/공개 기준선 파일 해시 동일, 보고서 정합성 통과.
- 최초 v0.6.0 누적 게이트는 **43/44 통과, 전체 실패(exit 1)**.
  3노드 lexical p99: 10.130533 ms → 10.744432 ms, **+6.059890%**.
  한도 10.637060 ms를 넘었으므로 다른 지표 개선으로 상쇄하거나 반올림해
  통과로 처리하지 않는다.

| 토폴로지 | 후보 처리량 (ops/s) | 최초 v0.6.0 대비 | OpenSearch 2.19.0 처리량 | OpenSearch 대비 |
| --- | ---: | ---: | ---: | ---: |
| 단일 노드 | 755.5358 | +1.6857% | 289.9323 | 2.6059x |
| 3노드 | 928.0368 | -0.3579% | 111.6928 | 8.3088x |

- 위 수치는 기존 개발용 보안/내구성 프로파일의 측정이다. 반복 측정과 특정
  변경의 인과관계 및 최적화 불가 증거는 아직 없으므로 ledger 제외 없음.
  정상 구현 완료 및 릴리즈 승격은 보류한다. 새로운 기준선으로 바꾸지 않는다.
- summary SHA-256:
  `10bb74fdea36c98f51f12483d8cceba84f03766f62e9ba61b524cbd409008711`;
  budget: `a62215f54d9f76d703bd8ad68d76f6b5cd9bd7945423d63a4672d8d4ff7996af`.
  테스트용 프로세스/컨테이너 종료 확인. 기존 사용자 컨테이너 5개는 유지했다.
  `_count`/집계 미해결 차이와 실제 재시작/동시성/원자적 저장/자동 생성 등
  전체 40개 계획 범위는 계속 미완료다.

### C03/C05: count/search 계약 추가 live 진단 (2026-09-07)

- `target/core-replacement-c05/live-count-contract-before`에서 현재 후보
  `894b33e68d17a487cf5b6f63e1fbc165ab12dc94eb3dd2e47e741b7d01bb11d9`와
  로컬 OpenSearch 3.7.0-SNAPSHOT을 독립적인 새 클러스터에서 비교했다.
  실제 실행 파일 해시 확인 및 실행 전후 동일. 후보 **16/24**, OpenSearch
  **24/24** 통과, 진단 실행기는 실패(exit 1)를 보존했다.
- 재현 스크립트: `target/core-replacement-c05/count_probe.py`.
  실행: `env PYTHONPATH=tools python3 target/core-replacement-c05/run-live.py
  --output-dir <새 경로> --count-probe --probe-only`.
  3개 shard, replica 0, 자동 refresh 비활성화, 서로 다른 두 tenant와 nested
  문서 두 개를 사용한다. 원시 요청/응답, 설정/쓰기/refresh/cleanup 결과를
  `execution.json`에 보존한다. 이 target 진단은 정식 추적 테스트의 대체물이 아니다.

| 재현 항목 | 후보 | OpenSearch |
| --- | --- | --- |
| bool filter count | 400 | 200, count 1 |
| 빈 bool + minimum_should_match=1 count | 400 | 200, count 2 |
| 같은 nested 자식의 두 조건 count | 400 | 200, count 1 |
| filtered alias count/search | 각각 2 | 각각 1 |
| alias 필터와 query의 교집합 count/search | 각각 1 | 각각 0 |
| 일치 인덱스 없는 wildcard search | 404 | 200, total 0 |

- 같은 bool/nested 쿼리의 일반 검색은 통과했다. refresh 전 count=0,
  alias 두 개의 합집합, 직접 인덱스와 alias의 혼합 요청, 빈 wildcard count도
  이 fixture에서는 양쪽 모두 기대값과 일치했다.
- 소스에서 `handle_count_route`가 validate-route 전용 검증기와
  `matches_query_body` 문서 순회를 사용함을 확인했다. 전자는 bool/nested를
  거부하고 후자는 이를 평가하지 않는다. 해당 함수는 다른 경로도 사용하므로
  검증기 허용 목록만 넓히거나 unsupported 쿼리를 count=0으로 처리하지 않는다.
- 다음 구현은 count의 기존 URL/body 충돌 검증과 refresh/routing 의미를 유지하며
  native query 실행을 연결한다. 동시에 인덱스별 alias 필터를 검색과 count에
  적용해야 한다. 같은 인덱스의 선택된 filtered alias들은 OR, 사용자 query와는
  AND로 결합하고 직접 인덱스/무필터 alias 선택 시 필터 제한을 제거하는 계약을
  다중 인덱스 및 wildcard까지 검증한다. 검색 경로 자체에 위 실패가 있으므로
  count를 search 핸들러로 단순 위임하는 것으로 완료하지 않는다.
- 런타임 코드는 이번 진단에서 변경하지 않았다. 기능 수정 및 회귀 테스트,
  전체 비플러그인 벤치마크는 다음 검증 대상이다. 기존 누적 성능 **43/44 실패**와
  ledger 제외 없음은 그대로 유지한다. 구현 단위 완료나 릴리즈 승격이 아니다.
- execution SHA-256:
  `7c180fef1192fb0df9f8e23b277b237e98463e64f36ae87e9d9ea6aa45618bad`.

### C05/D02: native count 연결 및 노출된 회귀 수정 중 (2026-09-07)

- `_count`의 제한된 validate-route 검증기와 문서 순회를 제거하고
  `standalone_native_search_request`의 size 0 요청으로 연결했다. 기존
  IndexRead 권한 검사와 URL/body 충돌 검사는 유지하며 search thread pool에
  진입한다. routing은 기존 native shard scope를 사용하고 응답 shard 수는
  실제 선택된 shard 수를 합산한다. 빈 대상 목록을 engine의 전체 인덱스
  선택 의미로 전달하지 않고 count 0으로 처리한다.
- 신규 노드 회귀 테스트는 bool filter, 빈 bool + minimum_should_match,
  match, 같은 nested 자식의 두 조건, refresh 전후 및 routing을 검사한다.
  기존 테스트의 기대값을 낮추지 않고 전체 노드 테스트를 실행했다.
- `native-count-node-full-second.log`: **594/599**, 5건 실패.
  task 인덱스 count 404, 복원 후 count 404 3건, text range count 0/기대 2.
  SHA-256 `11e040b585c0c4c93c6fae82e21f643fac41d52acf5f3cb81f1e8e9301b54314`.
  앞선 `native-count-node-full-first.log`는 기본 1.76 toolchain 선택을 발견해
  SIGINT로 중단한 빌드(exit 130)이며 테스트 판정이 아니다. 이후 명령은
  `env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 cargo +nightly test --release
  -p os-node --lib`로 기존 검증 설정을 사용했다.
- 복원 대상 native 인덱스를 먼저 생성하고 snapshot의 routing marker를
  유지한다. marker가 없는 snapshot은 legacy layout을 유지한다.
  `native-count-node-full-third.log`: **596/599**, 기존 복원 count 404 3건은
  해결됐으나 task 404와 text range 실패가 남고, 미-refresh 문서 복원 뒤의
  명시적 refresh가 문서를 공개하지 못하는 회귀가 추가로 드러났다.
  SHA-256 `071b4290659c6c5d17a41d924217c8e8b0315f83b6e1b1cfa93150d7333b452f`.
- 추가 수정: task 인덱스의 native 생성과 쓰기를 연결했다. snapshot 문서는
  공개된 문서에 먼저 seq_no를 배정하여 재생/refresh하고, 미공개 문서는 더
  높은 seq_no로 그 뒤에 재생한다. 재생/refresh 오류는 복원 호출자에게
  반환하고 recovery 실패를 기록한다. 복원 테스트를 공개/미공개 문서가
  섞이며 문서 ID 정렬 순서가 공개 순서와 반대인 경우까지 확장했다.
- 이전 실행 파일 894b33e로 추가 live 진단:
  `live-count-range-before`의 keyword range는 count/search 모두 양쪽 2건.
  `live-count-text-range-before`의 text range는 기존 count 양쪽 2건,
  검색은 후보 0건/OpenSearch 2건으로 기존 엔진 차이를 확인했다.
  후자 execution SHA-256:
  `73f83017f76b0630e4e54a607e0be621a22740c048086e932ecdf3c08bb83c2b`.
- `build_tantivy_range_query`가 Text 필드에도 문자열 term range를 생성하도록
  수정했다. 엔진 테스트에는 분석된 토큰, 단일/3 shard, bool filter,
  size 0과 hits 반환을 추가했다. 새 테스트의 실행 결과는 별도로 확인해야 한다.
- `native-count-node-full-fourth.log`: **598/599**. task count와 공개/미공개
  혼합 복원 검사는 통과했고, 다중 인덱스 text range count만 0/기대 2로 남았다.
  SHA-256 `57102422c1dcbd018a54dcda4e4774286f4dde7eeac57febb838bf9da7d18167`.
- 추가 원인은 `reduced_candidate_ids_for_query`의 문자열 range 분기였다.
  범위 경계와 같은 토큰을 요구하는 조건을 제거하고, 지원되는 Text/Keyword는
  native range query로 후보 문서를 선택하도록 수정했다. 공개 문서가 없으면
  빈 집합을 반환하여 Tantivy TopDocs의 limit 0 panic을 방지한다.
  `native-count-node-full-fifth.log` 빌드는 이 보호 조건 추가를 위해 SIGINT로
  중단(exit 130)했으며 테스트 판정이 아니다.
- `native-count-node-full-sixth.log`도 **598/599**, 같은 text range count가
  실패했다. SHA-256:
  `65b3b08e4f43aeb51eec60cae4c10323b4a37a1344d73e978bd53998093b05af`.
  추가로 `score_document_query_with_bm25_context`의 range 평가기가 Text를
  제외함을 확인했다. Text는 실제 인덱스의 tokenizer로 분석한 토큰을 평가하고,
  shard별 검색 상태도 찾도록 수정했다. 수치/날짜/keyword 평가는 유지했다.
  엔진 회귀 테스트는 다중 인덱스와 빈 인덱스를 포함하도록 확장했다.
- `native-count-node-full-seventh.log`: **599/599 통과**, 실행 1.08초.
  노드 신규 bool/nested/match/routing/refresh count 검사와 기존 root/대상별
  count, task count 및 공개/미공개 혼합 snapshot 복원 검사를 통과했다.
  엔진 라이브러리를 재빌드해 연결했지만 **엔진 자체의 전체 unit test와
  신규 `text_range_uses_indexed_tokens_for_hits_and_count` 실행은 아직 전**이다.
  테스트 로그 SHA-256:
  `821ad1b8381339dcf3925f1fa97dd6e5c3b73d8c00fb0e1d6733be03010f040d`.
  이 검증 시 node 소스 SHA-256:
  `8e8ec9b84b87cae94b54a88d72761210a74694b97e9d7c1724c24170aa41a39b`;
  engine 소스:
  `9a43c838a161b5e33af091005769fea77184701343700685dfbb7c2e1158b35d`.
  빌드/테스트 프로세스 종료와 `git diff --check` 통과 확인.
- 아직 새 실행 바이너리를 빌드하지 않았으며 이전 live/성능 결과를 이 소스의
  검증으로 재사용하지 않는다. 새 후보 전체 비플러그인 벤치마크는 실행 전이다.
  준비된 `target/core-replacement-c05/run-count-performance.py`는 새 경로의
  전체 4환경 측정/해시 기록/44개 지표 판정을 실행하며, 아직 실행 결과는 없다.
  이전 바이너리 894b33e는 `target/core-replacement-c05/steelsearch-before-native-count`
  에 별도 보존했다. 노드 테스트 통과만으로 C05/D02 완료 또는 성능 합격을
  선언하지 않는다. 다음 순서는 알려진 task 생성 경쟁 조건 보강, 엔진 전체
  테스트 및 새 바이너리 빌드, 확장 live 비교, 전체 비플러그인 성능 검증이다.
- 미완료: alias 필터의 공통 적용, 빈 wildcard 검색, count의 min_score/
  terminate_after/expand_wildcards 및 빈 대상의 쿼리 검증 계약, 복원의
  원자성/손상 레코드 거부/동시성, task native 쓰기 실패 전파 및 동시 생성.
  특히 task 인덱스 부재 검사를 metadata lock 밖에서 수행하는 현재 코드는
  동시 생성 시 재확인이 필요하다. 중복 생성 오류로 recovery 실패를 기록하지
  않도록 lock 안의 재확인과 동시 task 완료 회귀 테스트를 다음 수정에 포함한다.
  전체 40개 범위, 최초 v0.6.0 누적 5% 한도와 ledger 제외 없음은 유지한다.

### D02: task 초기화 및 동시 refresh 소유권 (2026-09-07)

- task의 metadata/native 인덱스 초기화와 created-index 등록을 같은 metadata
  lock 안에서 처리했다. `ensure_minimal_index_exists`의 중간 상태 노출 경로를
  task 초기화에서는 사용하지 않는다. 일반 자동 인덱스 생성은 별도 미완료다.
- 신규 `concurrent_task_completions_initialize_one_searchable_tasks_index`는
  8개 worker의 동시 task 완료를 4회 반복하고 ID 고유성, 각 문서의 응답 내용,
  count, metadata/native routing 일치와 recovery 실패 여부를 확인한다.
  첫 전체 노드 실행은 **599/600**: 초기화 오류는 발생하지 않았지만 round 1의
  count가 기대 8 대신 12였다. 기대값을 바꾸거나 해당 검사를 제외하지 않았다.
  `native-count-concurrent-node-full.log` SHA-256:
  `3062e692113f7048ef3f1a3179290f710542358f75e665fe85bf4e543a3a961a`.
- task/REST 경로와 분리한 정식 엔진 integration test
  `crates/os-engine-tantivy/tests/concurrent_refresh.rs`를 추가했다. 단일/3 shard
  각각 8 worker가 3개씩 고유 문서를 쓰고 매번 refresh하며, 12회 반복한다.
  종료 제한은 worker당 10초이고 count와 전체 hit ID 목록을 모두 검사한다.
- 수정 전 엔진 단독 결과 **0/2**:
  단일 shard 첫 반복에서 고유 문서 24개에 count/hit 45개와 중복 ID가 나왔다.
  3 shard는 첫 반복에서 refresh가 10초 안에 끝나지 않았다.
  `concurrent-refresh-engine-before.log` SHA-256:
  `6163312abb727544050205fe6d28633909d65519915a86d97a06f736ca111361`.
- 전체 재구성과 증분 refresh가 서로 다른 진행 플래그를 사용하고, 일부
  Busy plan을 발견한 뒤 이미 확보한 shard 플래그를 둔 채 재시도하는 경로가
  있었다. 같은 인덱스의 refresh들이 공유 Tantivy writer를 동시에 변경하지
  않도록 `StoredIndex`별 `Arc<Mutex<()>>`를 추가했다. store lock을 놓은 뒤
  기다리며 인덱스 하나씩만 보유한다. 쓰기/검색에 이 lock을 추가하지 않았고,
  refresh 내부 shard 병렬 artifact 생성도 유지했다.
- 이 lock의 Arc identity를 계획 수립, 결과 적용 및 오류 정리에서 확인한다.
  삭제/복구/재생성으로 인스턴스가 교체되면 이전 refresh가 새 인덱스의 상태나
  진행 플래그를 변경하지 않는다. 기각된 artifact의 소유 플래그도 정리한다.
  새 인덱스/복구는 새 identity, 읽기용 검색 snapshot은 Arc를 공유한다.
  `waiting_refresh_rejects_a_recreated_index_with_the_same_name`을 추가했으며
  실제 실행 결과는 엔진 전체 단위 테스트에서 확인해야 한다.
- 수정 후 엔진 단독 회귀 검사 **2/2 통과**, 두 토폴로지의 24회 반복 모두
  정확한 24개 ID/count와 종료를 확인했다. 실행 2.03초는 기능 stress test의
  시간이며 v0.6.0 대비 성능 개선율이나 예산 합격으로 해석하지 않는다.
  `concurrent-refresh-engine-after.log` SHA-256:
  `065509d79e5fd889322dd94792c987b389ced0cb522590e833d6e5308bccb4df`.
  실행 명령: `env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 cargo +nightly test
  --release -p os-engine-tantivy --test concurrent_refresh -- --test-threads=1`.
- 노드 전체 재검증 **600/600 통과**, 실행 1.05초.
  `native-count-concurrent-node-after.log` SHA-256:
  `ef37943092626b0021a2ccd293e30bda2eb0e30810847f8f8a1f036bdce59351`.
  node 소스 SHA-256:
  `36acddaa668349f10da546027bd662287ead94e083e53d9e3096d463a5ed6ba6`;
  engine 소스:
  `332cc3175481d9a1a5af04b6cc57bac1a5286ed69abb7888955979f8ccb1785b`.
- `native-count-refresh-engine-full.log`의 엔진 전체 단위 테스트는 현재 빌드
  중이다. `--lib`는 새 integration test를 포함하지 않으므로 위 별도 실행
  기록과 구분한다. 새 실행 바이너리/live/전체 비플러그인 벤치마크는 아직 전이다.
- 동시 overwrite/delete/schema 변경, 읽는 동안의 가시성, I/O 실패·원자적
  publication 및 복구 안전성 전체를 증명한 것은 아니다. 알려진 alias/count
  옵션/집계 차이와 전체 40개 범위는 유지한다. 단위 완료·릴리즈 승격 및
  v0.6.0 누적 5% 성능 합격을 선언하지 않으며 ledger 제외도 없다.

### C05/D02: 엔진 전체 결과와 변경·삭제 회귀 범위 (2026-09-07)

- `native-count-refresh-engine-full.log` 실행이 종료했다. 엔진 전체 단위 테스트
  **832/834 통과**, 실패 2개, 실행 2.44초. 로그 SHA-256:
  `43adb78ad8f9ba53bba6943a7caef61d8667e867a1041c0d2be3c29cb313a8aa`.
  새 `text_range_uses_indexed_tokens_for_hits_and_count` 및
  `waiting_refresh_rejects_a_recreated_index_with_the_same_name`은 통과했다.
- 실패는 기존 `grouped_hybrid_bool_text_range_leaf_*` 두 검사다.
  `body >= "apple"`과 두 번째 banana/knn 조건 그룹을 모두 만족하는
  `b` (`"banana beta"`)가 실제 결과에 추가됐다. 이전 기대 `c,e`는 범위의
  하한 토큰을 포함한 문서만 인정하던 동작에 맞춰져 있었다.
  기대 membership/count를 `b,c,e`/3으로 수정했다. context의 전체 ID 집합과
  page/window의 순서 일치도 검사하며, 검사를 삭제하거나 plugin 지원 범위를
  새로 추가한 것은 아니다. 실제 재실행은 `native-count-refresh-engine-after.log`.
- integration test에 단일/3 shard의 동시 덮어쓰기·삭제 검사를 추가했다.
  각 12회, 8 worker가 기존 자기 ID를 3회 갱신하고 짝수 worker의 문서를 삭제한다.
  종료 후 정확한 홀수 ID 4개, 중복 없음, 최종 source revision을 검사한다.
  독립적인 순차 검사로 refresh 전의 기존 검색 결과 유지와 refresh 후의
  수정·삭제 반영도 추가했다. 이 추가 검사들은 아직 실행 전이다.
- 현재 단계는 검증 중이다. task native 쓰기/refresh 오류 전파, filtered alias의
  인덱스별 필터 보존, 동시 publication 및 복구 전체는 여전히 미완료다.
  새 바이너리/live/전체 비플러그인 성능 검증 전이며 완료/예산 합격/제외 없음.

### D02/C05: 쓰기 중 검색 snapshot 보존 및 삭제 refresh 수정 후보 (2026-09-07)

- 기대값 수정 후 엔진 전체 `--lib` 검사 **834/834 통과**, 실행 2.34초.
  `native-count-refresh-engine-after.log` SHA-256:
  `6a557de80b3f01595034d77c743b046d78eba598c79bb3fa9191a2e60e544c9a`.
  이 실행의 engine 소스 SHA-256은
  `044e19d66af97215402efc93cb0f51c302e21747f71776fb2e97b39e469242ea`이며,
  아래 추가 런타임 수정 전 결과다. 최신 후보의 전체 합격 증거가 아니다.
- 확대 integration 최초 실행은 **2/5 통과**, 실행 2.24초.
  단일 shard 동시 변경·삭제의 첫 반복에서 count는 4였지만 hit ID가 빈 목록이었다.
  3 shard 첫 반복에서는 기대 count 4 대신 0, hit ID도 빈 목록이었다.
  순차 가시성 검사는 단일 shard에서 refresh 전 기대 count 2 대신 0으로 실패했다.
  이 순차 검사의 3 shard 부분은 앞선 실패로 미실행이었다.
  `concurrent-refresh-mutations-first.log` SHA-256:
  `c7f6ae78281ad324d1e0be08d7bd5a521047212a68a24e6deb46fe1f1f08f9e0`.
- 원인 경로: pending update/delete/schema 변경이 공개된 검색 상태와 refreshed
  문서 맵을 지우고 진행 중인 refresh 플래그도 초기화했다. 또한 삭제 후 남은
  문서의 최대 seq_no만으로 shard refresh 필요 여부를 판단했고, artifact 적용이
  계획 이후의 추가 변경까지 append-only로 덮어쓸 수 있었다.
- 수정 후보는 기존 검색 snapshot을 refresh publication까지 보존한다.
  `StoredShard::require_full_refresh`는 전체 재구성 필요 여부와 non-append
  generation만 변경하며 검색 문서/reader 및 refresh 소유권 플래그를 지우지 않는다.
  계획에 캡처한 generation과 적용 시점의 값을 비교하여 동시 수정·삭제가 있으면
  다음 refresh에서도 전체 재구성을 유지한다. 인덱스의 append-only 상태도 각
  shard 상태로부터 계산한다. 쓰기 전체를 refresh mutex로 직렬화하지 않았다.
- 삭제 등 non-append shard의 갱신 목표는 인덱스의 seq_no를 사용한다.
  각 계획은 store lock 안에서 현재 문서 snapshot과 같은 시점의 목표를 캡처하고,
  호출 시작 시 목표를 최소 완료 조건으로 유지한다. 따라서 schema 변경 등으로
  재시도할 때 이미 덮어쓴 옛 목표만 고집하지 않는다.
- 수정 후 정식 integration **5/5 통과**, 실행 5.39초. 동일 후보 재실행도
  **5/5 통과**, 실행 5.32초. 실행마다 동시 추가/변경·삭제 4개 검사의 48회 반복과
  순차 가시성 검사의 단일/3 shard 모두 통과했다. 반복 stress 테스트 시간이며
  v0.6.0 성능 예산 판정이 아니다.
  `concurrent-refresh-mutations-after.log` SHA-256:
  `b4be9ab2f5779c3ab20ddc35384828ca78e14974ad641315feb8abca71c02d9f`;
  `concurrent-refresh-mutations-repeat.log`:
  `1e24929576f28068528569ce4672326ecd21e9f14e96d11f721e8381c452ec07`.
  명령: `env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 cargo +nightly test
  --release -p os-engine-tantivy --test concurrent_refresh -- --test-threads=1`.
- 최신 engine 소스 SHA-256:
  `638360ac77b67b4ff76cb2bee0c99d68979f308dd1a733a6cae9ca24be2c2a65`;
  integration 소스:
  `c795a33b3c18dfdf5e8d99a4c93e637ede258b4dc8a9f4ce40817f2d43b854ab`.
  `git diff --check` 통과. 최신 소스의 엔진/노드 전체 재검사, 실행 바이너리 재빌드,
  live 검증 및 전체 비플러그인 벤치마크는 아직 남아 있다. 기존 834/834,
  600/600이나 이전 후보 성능 결과를 최신 후보에 재사용하지 않는다.
- 이 회귀 검사는 마지막 결과와 순차 가시성을 확인한 것이다. 검색 요청이
  refresh publication과 동시에 실행될 때의 reader/문서 메타데이터 원자성,
  I/O 실패 rollback, 삭제·재생성·복구 전체의 안전성을 증명하지 않는다.
  단위 완료/릴리즈 가능/누적 5% 성능 합격 선언 및 ledger 제외는 없다.

### D02/C05: 동시 검색의 reader 세대 고정 및 live 가시성 진단 (2026-09-07)

- `concurrent_refresh.rs`에 단일/3 shard 동시 검색 검사를 추가했다. 각각 3회,
  writer가 고유 문서 64개를 하나씩 쓰고 refresh하는 동안 4 reader가 검색한다.
  매 응답의 count/hit 수 일치, ID 중복 없음, ID와 source ordinal 일치,
  최종 64개 문서를 확인한다. worker 완료 제한은 30초다.
- 전체 엔진 빌드 대기 중 기존 release RLIB에 새 integration 소스만 연결한
  진단을 별도로 실행했다. 최초 비-LTO 연결 실패는 테스트 결과가 아니며,
  release의 opt-level=3/lto=thin/codegen-units=1로 다시 연결해 실행했다.
  Cargo 전체 검사나 성능 측정의 대체가 아니다.
- 수정 전 검색 경쟁 검사 **0/2 통과**, 첫 반복에서 양쪽 모두 중복 hit,
  3 shard에서는 count 4/hit 3도 재현됐다. 나머지 5개 검사는 이 실행에서
  필터링됐으며 성공으로 세지 않는다.
  `concurrent-reader-diagnostic-before.log` SHA-256:
  `e90eaaaa097e514663a05fbabf9434ae18848f093cd810c9252c3165d2a9ea6c`.
- `TantivySearchState`가 공유 reader와 별도로 고정 `Searcher`를 보유하도록
  수정했다. 검색 경로 11곳이 이 searcher를 복제한다. reader reload 직후 캡처한
  동일 searcher로 ID lookup을 만들고 함께 공개하여, 이전 snapshot의 lookup과
  새 segment 주소가 섞이지 않게 했다. ID lookup 단위 검사도 명시적 searcher를
  전달한다. 검색과 쓰기 전체를 하나의 lock으로 직렬화하지 않았다.
- 수정 후보 진단 **7/7 통과**, 실행 8.81초.
  `concurrent-reader-pinned-diagnostic-after.log` SHA-256:
  `d7c3f2fdd84d5e499e9390cfb22fdc2cdcd5501a577ff9cb735614fd86217548`.
  컴파일 명령·소스/RLIB/실행 파일 해시는
  `target/core-replacement-c05/reader-pinned-diagnostic.json`에 기록했다.
  이 manifest SHA-256:
  `04ec9925c46becdb73095e9022f739cc41e6e0633afd54fa8e1e339e57523220`.
- 같은 reader 고정 소스의 정식 Cargo integration도 **7/7 통과**, 실행 7.12초.
  `reader-pinned-cargo-integration.log` SHA-256:
  `d54df10df6cb31b9f87c5c08be1da5298f8a94671d1608cbc4dbb1a91bcdd7bb`.
  당시 engine 소스 SHA-256:
  `a97ac77fcba97e9668821475c91ba57ed320bf907612ef935634e5516cf46591`.
- 앞서 시작한 `638360ac...` 소스의 전체 엔진 검사는 **833/834 통과**,
  실행 2.47초. `refresh_targets_request_time_sequence_number`가 요청 후 추가된
  문서까지 공개하여 기대 1 대신 2로 실패했다. 기존 기대값을 유지하고
  append-only 경로가 요청 시점 seq_no를 상한으로 사용하도록 복원했다.
  non-append 경로는 재구성 snapshot과 같은 시점의 목표가 필요하므로 구분한다.
  `published-view-engine-full.log` SHA-256:
  `0e0260e5e871102519e22a3941ce448a821bb481a0ca6118f108e045daff4f6e`.
- 상한 수정까지 포함한 engine 소스 SHA-256:
  `b5e04534b26095e8636e422be680b5317ba0df9c47ad82a103c62d919bc42c3c`.
  현재 `env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 cargo +nightly test --release
  -p os-engine-tantivy -p os-node --lib`를 실행 중이며
  `reader-pinned-bounded-engine-node-full.log`에 기록한다. 앞선 7/7 결과를 이 추가
  수정까지 검증한 것으로 재사용하지 않는다.
- count live probe에 명시적 refresh 전후의 count, hit/source 전체, 갱신한 term
  count 및 realtime GET/DELETE 검사를 추가했다. `py_compile` 통과.
  기존 실행 파일 `894b33e6...`과 OpenSearch 3.7.0-SNAPSHOT의 실제 HTTP 진단은
  각각 **29/39**, **39/39**였다. 새 항목 중 후보의 pending count가 기대 2 대신
  0인 실패를 확인했다. 나머지 9개는 기존 text range/bool count/nested count/
  filtered alias/missing wildcard 차이다. 최신 소스의 live 결과가 아니다.
  `live-published-view-before/execution.json` SHA-256:
  `2fd0961b41b2f831e561887239c3c2f1ff37034a99e5ffef674dcddf7d3cfb6f`;
  `count_probe.py`: `f616f0e64a287dee6671619e8dbc9bd897f399a3588c49364be0d7c3ce6b74b4`.
  진단 서버들은 종료했다. 성능 측정은 병행하지 않았다.
- 최신 후보 전체 검사·integration 재실행·실행 파일 빌드·live·전체 비플러그인
  성능 게이트가 남아 있다. 유한한 경쟁 검사로 I/O 실패/복구/분산 안전성 전체를
  증명하지 않으며 단위 완료·릴리즈·누적 5% 합격 및 ledger 제외는 없다.

### C05/D02/P03: 최신 후보 전체 기능 검사와 성능 예산 실패 (2026-09-07)

- `b5e04534...` engine 소스의 전체 엔진 **834/834**, 노드 **600/600** 통과.
  실행 시간은 각각 2.30초, 1.06초다. 기존
  `refresh_targets_request_time_sequence_number`의 기대값을 유지하고 통과했다.
  `reader-pinned-bounded-engine-node-full.log` SHA-256:
  `951643facfccead2128552e8a44ba6fd375a68632ec311b7e92e9015ab2ad937`.
- 같은 소스의 별도 integration도 **7/7 통과**, 실행 6.63초.
  `reader-pinned-bounded-integration.log` SHA-256:
  `dbacf88b4625b534daa2bfcec1a296c3f5ef6627fa6c0834e69bc37d14313fce`.
- release 실행 파일을 재빌드했다. 태그/게시 작업은 하지 않았다.
  명령: `env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 cargo +nightly build
  --release -p os-node --features standalone-runtime --bin steelsearch`.
  바이너리 SHA-256:
  `693af258fa59c932012ff07db5316dcef8f41b64b6efb83246a334d01e1f3533`;
  `reader-pinned-release-build.log`:
  `98528e32dd40dfa4706133212557a99d0baf5548e6307a7107c3584b0f519912`.
  이전 `894b33e6...` 실행 파일은 `steelsearch-before-native-count`에 보존했다.
- 최신 실행 파일의 실제 HTTP 검증
  `live-native-count-reader-pinned`에서 설정/stream **84/84**, routing **118/118**,
  코어 검색 fixture **1180/1180** 통과. 준비 실패와 skip 모두 0이다.
  nested flat/canonical fixture는 각각 **130/160**으로 이전 98/160에서 개선됐다.
  count 관련 32개 실패가 각각 해소됐고 집계 30개씩은 여전히 실패한다.
- count 계약 진단은 후보 **34/39**, 참조 **39/39**다. 최신 후보의 수정·삭제 전후
  가시성, bool/nested count, text range 검사는 통과했다. 남은 5개는 filtered
  alias의 count/search, alias-query 교집합 count/search, 빈 wildcard search다.
  결과를 제외하거나 전체 기능 합격으로 바꾸지 않는다. 참조는 기능 진단용
  OpenSearch 3.7.0-SNAPSHOT이며 성능 참조 2.19.0과 구분한다.
  live `execution.json` SHA-256:
  `f440af43720363c087f96bbf89c107f77c84e3effd320cedae80780391218476`;
  코어 `search-compat-report.json`:
  `bc0b954ddf4fd9957e317b7cef83c5ff2fb277a04e1e88bc786b3ff8c8fc131e`.
- 첫 성능 진단 `native-count-full-first`는 OpenSearch 3노드의 인덱스 생성 403으로
  중단됐다. 실패 진단에 global create-index block과 약 3.3GB의 디스크 여유가
  기록됐다. 전체 summary/예산 결과가 없으므로 일부 측정으로 합격을 계산하지 않았다.
  실행 manifest SHA-256:
  `4bffed5384c57a4830395128da51c8618ac5f93dbefe5cbe6a196551c96901dc`;
  로그: `3521957b18c04b6d09c149eb902c6fe3ace5792477cdeb59242f4bedf3b80b1f`.
- 사용 중인 프로세스와 추적 파일이 없는 `target/debug` 재생성 캐시만
  `cargo +nightly clean --profile dev`로 정리했다. 명령은 18,899개 파일,
  21.5GiB 제거를 보고했고 실제 디스크 여유는 약 3.2GB에서 22GB로 증가했다.
  소스, release 산출물, 기준 바이너리, 벤치마크 증거는 보존했고 기준/후보 해시를
  재확인했다. OpenSearch 디스크 안전 설정은 끄지 않았다.
- 진단 wrapper에 새 출력 디렉터리 인자를 추가하고 **네 시나리오 전체를 새로**
  `native-count-full-after-cache-clean`에서 실행했다. 기존 부분 결과와 합치지 않았다.
  명령: `env PYTHONPATH=tools python3 target/core-replacement-c05/run-count-performance.py
  --output-dir target/core-replacement-c05/native-count-full-after-cache-clean`.
  실행 420.99초, 네 시나리오 요청 오류 모두 0, 바이너리/실행 입력 해시 불변,
  보고서 무결성 통과. v0.6.0 최초 공개값 대비 **40/44 이내, 수치 예산 실패**다.

| 초과 지표 | v0.6.0 ms | 최신 후보 ms | 누적 악화 |
| --- | ---: | ---: | ---: |
| single-node/write/mean | 2.8727741528149027 | 3.035123701543568 | +5.651316% |
| single-node/write/p95 | 5.275249946862459 | 5.5673259776085615 | +5.536724% |
| single-node/write/p99 | 6.8314010743051785 | 7.290093367919327 | +6.714469% |
| three-node/lexical/p99 | 10.130532924085863 | 10.728764045052237 | +5.905229% |

| 혼합 부하 처리량 | v0.6.0 req/s | 후보 req/s | v0.6.0 대비 | OpenSearch req/s | 후보/OS |
| --- | ---: | ---: | ---: | ---: | ---: |
| single-node | 743.0110695130876 | 731.7730061612459 | -1.512503% | 280.3474678975356 | 2.610236x |
| three-node | 931.3700112371704 | 920.7453039460765 | -1.140761% | 115.66036459390925 | 7.960768x |

- 이 처리량이나 nested 지연 개선으로 실패 지표를 상쇄하지 않는다.
  기능 차이, fresh v0.6.0 대조 및 사전 고정 반복 절차 등의 전체 합격 요건도
  남아 있다. 위 결과는 공개 기준값과의 전체 비플러그인 부하 진단이며 단위 수락이 아니다.
  summary SHA-256:
  `203e79616f8b975d01b6d4a065ad0a2772024266ae56ae06bc232b91ec0d0b19`;
  budget: `661ee43720cc47377b2780f7a6364473afdbb3aaa09820b95eb2e763ed3919d2`;
  execution: `c71169eefd98b2bc293bde6eb493ee268eb3b48eab94f10a169b95e13cbcb3a2`.
- 다음 작업은 단일 노드 write와 3노드 lexical 경로의 원인 분리/CPU 진단,
  정합성을 유지한 최적화 및 전체 재측정이다. 현재 단일 변경의 5% 이상 기여나
  최적화 불가능성을 입증하지 않았으므로 ledger 제외는 없다.

### P03: 단일 노드 혼합 부하의 사전 고정 CPU 대조 (2026-09-07)

- 기존 CPU 진단 도구에 `--topology single-node|three-node`와 write/lexical
  단독 부하 선택을 추가했다. 기본 three-node/mixed 및 45초 실행/20초 CPU 관측은
  유지한다. 서버 발견은 고정 basename 대신 지정 바이너리 경로를 비교하여
  백업 파일명도 지원한다. 실제 `/proc/<pid>/exe` 해시 검증은 유지한다.
- 단위 검사 **7/7 통과**, `git diff --check` 통과.
  `tools/run-core-cpu-diagnostic.py` SHA-256:
  `ec44f0485da2084a59d701c5b8d84af471dbae31e203dec47ec72d1c75edd4ab`;
  `tools/test_core_cpu_diagnostic.py`:
  `542a5e007ff1df27b554de69df4c24a8b98b2604bbd5e0d7e8aa0fdb03641089`.
  write/lexical 단독 선택은 command 단위 검사를 했으며 이번 실제 실행은 mixed다.
- 실행 전에 `write-cpu-comparison-plan.json`에 순서를
  **이전 후보 -> 최신 후보 -> 최신 후보 -> 이전 후보**로 고정했다.
  이전은 `894b33e6...`, 최신은 `693af258...`이며 v0.6.0 비교가 아니다.
  계획 SHA-256:
  `52605a9a890d4e7f8f406c77a1141e95728e452b8b6f43cf4a5514bd5e0d307c`.
  실행 디렉터리는 `target/core-replacement-c05/write-cpu-{label}`이다.
  네 실행 모두 서버 1개/부하 생성기 1개를 확인했고 실제 바이너리 해시가
  유지됐다. profiler와 matrix 종료 코드 모두 0, HTTP 오류도 0이다.

| label | 혼합 req/s | write mean ms | write p95 ms | write p99 ms |
| --- | ---: | ---: | ---: | ---: |
| before-1 | 763.638377 | 2.968104 | 5.458874 | 7.049711 |
| candidate-1 | 750.367294 | 2.985697 | 5.548125 | 7.240949 |
| candidate-2 | 767.311545 | 2.960201 | 5.519125 | 7.117113 |
| before-2 | 767.073211 | 2.965536 | 5.481272 | 7.423259 |

- 위 수치는 CPU profiler가 붙은 45초 진단이다. 60초 전체 부하의 v0.6.0
  수치 예산과 비교하거나 기존 40/44 실패를 취소하는 데 쓰지 않는다.
  이번 표본에서는 최근 변경 묶음에 의한 write mean 5% 악화가 일관되게
  재현되지 않았다. 전체 회귀가 없다는 증명이나 단일 기능의 원인 분리가 아니다.
- 서버 PID로 분리한 `perf-self.txt`/`perf-children.txt`를 각 실행에 보존했다.
  memcmp의 self 비중은 이전 8.22%/8.72%, 최신 10.13%/9.55%였다.
  최신 첫 표본의 memcmp 호출 경로 중 4.09 percentage points는 단순 bucket 집계,
  2.01은 query scoring의 source field 조회, 1.64는 match 문자열 검색에서 나왔다.
  이는 서버 CPU 표본의 비중이며 write 지연 증가율이나 인과적 기여율이 아니다.
- `collect_aggregations_native`가 문서 참조를 모은 뒤
  `collect_simple_bucket_aggregations_from_documents`에서 문서별 필드 조회와
  bucket 카운팅을 수행하는 경로를 확인했다. 다음 최적화 검토 범위는 이 검색·집계
  순회 비용이며, 단순히 write 함수나 refresh mutex가 원인이라고 단정하지 않는다.
  49Hz의 유한한 표본과 불완전한 일부 unwind 경로도 고려해야 한다.
- 각 `diagnostic.json` SHA-256:
  before-1 `d9284889c254efbaa2f06df09f68df2a6aa4acee8b510a1f7d4a901466d55f05`;
  candidate-1 `8685d9794c7e44c84a13fffec8fa43952e53dab5cd225467db367d0c00db16a3`;
  candidate-2 `5d220184861a46ae0aa9a46b97650bceb0a0b18fb3f60ef6058787a64e4c9ea5`;
  before-2 `8bdfc45072c2e091491e92fbe0d526b1c33fcf54f32aa219884157d2cc258777`.
- 런타임 소스/실행 바이너리는 이번 진단에서 바꾸지 않았다. 기존 기능 차이와
  40/44 성능 예산 실패, 최적화 후 전체 재측정 요건은 그대로다. 단일 변경의
  5% 이상 기여와 최적화 불가능성이 입증되지 않아 ledger 제외도 없다.

### P03: 문자열 태그 실험과 집계 순회 후보 (2026-09-07)

- `tools/bench-terms-counter.rs`에 문자열 끝 8바이트 태그를 먼저 비교하는
  후보를 추가했다. 길이와 원문 비교를 유지하며 NUL, UTF-8, 긴 문자열의
  동일 접미사 충돌을 기존 BTreeMap 결과와 대조했다. 진단 실행은 종료 코드 0으로
  끝났고 내부 정합성 검사를 통과했다. 실제 엔진에는 태그 방식을 적용하지 않았다.
- 문서마다 독립적으로 할당한 문자열 5,000개를 대상으로 500회씩 4라운드,
  순서를 교대하여 측정했다. 기존 hybrid 대비 tag 중앙값 시간 비율은
  cardinality 1/3/8/9/32/1024에서 각각
  1.668792/1.176220/0.546235/1.025042/1.043611/1.016947이다.
  흔한 소수 키 조건의 악화 때문에 채택하지 않았다. 이 수치는 마이크로벤치마크이며
  서비스 성능 회귀율이나 기능 제외 근거가 아니다. 문자열 할당 조건이 달라진
  과거 CSV와 같은 워크로드로 비교하지 않는다.
- 도구 SHA-256: `e65cf198e5dbcfb1140a7f0bcf18f23483e6f889ba926e40892534a5095d56f5`;
  `target/core-replacement-p03/terms-counter-tag-diagnostic.csv`:
  `74343b8f3241e0fc7b7109d9f5c792441e17ffccc0de67d99658cbef34de8760`.
- 별도 후보로 `collect_simple_bucket_aggregations_from_documents`의 순회를
  문서 -> 집계에서 집계 -> 문서로 변경하여 종류 분기를 문서 반복 밖으로 옮겼다.
  카운터, 필드 검사, fallback, 날짜 계산과 결과 형식은 유지한다.
  terms/range/date_histogram을 함께 실행하여 개별 수집기와 결과를 비교하는
  회귀 검사를 추가했다. 정방향/역방향 문서 순서, 누락 필드, 9개 키,
  겹치는 범위, 시간대와 배열 fallback을 검사한다.
- 후보 엔진 소스 SHA-256:
  `89d06f9dcefa749239bf522bbebd1a2e34a1e22421248acde34e7eaffb1e4eec`.
  엔진·노드 전체 테스트 실행 로그는
  `target/core-replacement-p03/bucket-scan-engine-node-full.log`이다.
  실행 종료 코드 0, 엔진 **835/835**, 노드 **600/600** 통과(ignored/filtered 0).
  신규 복합 집계 검사도 통과했다. 빌드 14분 33초, 테스트 실행 각각 2.38초/1.03초.
  로그 SHA-256: `8e1f23728974cca2bcb855a206000e69180fa5d24d3d7b0b506b2a399761919f`.
  동시 refresh/검색 통합 검사도 종료 코드 0, **7/7 통과**했다.
  `target/core-replacement-p03/bucket-scan-integration.log` SHA-256:
  `2dec404b6549286a2fbc6c975735f23172b5eda6d99772277da0d82b31e7dee5`.
  빌드 2분 14초, 테스트 4.29초이며 ignored/filtered 0이다.
  이전 실행 바이너리 `693af258...`의 결과를 이 소스의 검증으로 재사용하지 않는다.
  통합 검사 후에도 `target/release/steelsearch` SHA-256은
  `693af258fa59c932012ff07db5316dcef8f41b64b6efb83246a334d01e1f3533`이다.
  다음 단계는 이 이전 후보를 보존한 뒤 최신 standalone 바이너리를 빌드하고,
  실시간 기능 비교와 새 출력 경로의 전체 비플러그인 부하를 실행하는 것이다.
  최신 바이너리 실시간 검사와 전체 벤치마크가 끝나기 전에는 개선 또는
  구현 단위 완료로 판정하지 않는다. 기존 40/44 예산 결과와 ledger 무제외는 유지한다.

### P03: 집계 순회 후보 실행 바이너리 검증 (2026-09-07)

- 이전 후보를 `target/core-replacement-p03/steelsearch-before-bucket-scan`에
  보존했고 SHA-256 `693af258...` 일치를 확인했다. 최신 standalone release 빌드는
  종료 코드 0, 4분 37초에 완료됐다. 실행 파일 SHA-256:
  `e094cd4109fcc3e87c32539546b87a6ccdb5ea24a0a3c116e4bf68ca75617c7c`.
  `bucket-scan-release-build.log` SHA-256:
  `3a73cad0774458738e9341cf9d383093db858551b6d2aa40790871d39c0e1586`.
- `target/core-replacement-p03/live-bucket-scan`에서 OpenSearch
  3.7.0-SNAPSHOT과 실시간 비교했다. 설정 84/84, routing 118/118,
  projected core search 1180/1180 통과. 세 fixture 모두 setup 실패/skip 0이며
  실행 바이너리와 fixture 해시 불변을 확인했다.
- nested-bool 두 fixture는 각각 130/160 통과로 기존 실패 30건씩이 남는다.
  count probe는 후보 34/39, 참조 39/39다. 후보 실패는 filtered-alias의
  count/search, alias-query-intersection의 count/search, missing-wildcard의
  search 5건이다. 전체 live 명령 종료 코드는 1이며 전체 호환성 통과가 아니다.
- live `execution.json` SHA-256:
  `002b85535412e29d601ecf34b555aa6c693e1fd2274728ed0b9924b4c9dcd482`;
  `search-compat-report.json`:
  `2f6a28007c90acba33baa2619aded015fddb851b5943e00635e2e785bea7030f`.
- 전체 비플러그인 성능 진단은 새 출력 경로
  `target/core-replacement-p03/bucket-scan-full-first`에서 완료했다.
  이 측정은 성능 참조 OpenSearch 2.19.0과 고정 공개 v0.6.0 지표를 사용한다.
  네 시나리오 실행 자체는 종료 코드 0, 총 418.32초, HTTP 오류 모두 0이다.
  실행 바이너리/실행 도구 해시 불변 및 보고서 무결성 검사는 통과했다.
  그러나 수치 예산은 **40/44**, 판정 종료 코드 1로 실패했다.

| 초과 지표 | v0.6.0 ms | 후보 ms | 누적 악화 |
| --- | ---: | ---: | ---: |
| single-node/facet/mean | 7.340244606856199 | 7.730578141912409 | +5.317718% |
| single-node/facet/p95 | 15.157528035342693 | 16.1337180645205 | +6.440298% |
| single-node/facet/p99 | 20.213827239349484 | 22.16723982011899 | +9.663744% |
| three-node/facet/p95 | 9.45385997183621 | 9.967704978771504 | +5.435293% |

- 처리량은 single-node 731.730350342362 req/s(v0.6.0 대비 -1.518244%),
  three-node 914.7709791311808 req/s(-1.782217%)다. 같은 실행의 OpenSearch는
  각각 277.175969958828, 114.05953706361963 req/s다.
  처리량 예산 통과로 위 facet 실패를 상쇄하지 않는다.
- 이전 후보의 단일 노드 facet mean/p95/p99는 각각
  7.42511374433039/15.117890213150531/20.41163960238919 ms였다.
  이번 표본은 순회 변경의 개선을 뒷받침하지 않는다. 다만 별도 시점의 단일 실행끼리
  비교한 것으로, 이 변경의 인과적 기여율이나 최적화 불가능성을 증명하지 않는다.
  이전 write/lexical 초과가 이번 실행에서 기준 이내여도 해결 확정으로 처리하지 않는다.
- summary SHA-256: `f5ab2b1a76bf1a5ed04f0a1825ae0c1e2c83858a7cdaea02645016cbe26130e0`;
  budget: `24796081b6818e83d37f70aef0d17a491c5a63e684979f241b269133ef2850da`;
  execution: `425c6adcb852f711b35d858de36dc39ab0ecb0d1ea503bd994382e89ad42e6a4`.
- 현재 순회 후보는 미수락 상태다. 다음 작업은 보존한 이전 후보와 현재 후보의
  사전 고정 반복 대조로 facet 원인을 분리하고, 불리한 최적화를 철회하거나
  수정한 뒤 전체 부하를 다시 실행하는 것이다. 기능 정합성 보호 장치는 유지한다.
  fresh v0.6.0 반복 대조와 출처/운영 프로파일 검증 요건도 여전히 남는다.
  단일 기능의 5% 이상 기여와 최적화 불가능성이 입증되지 않아 ledger 제외는 없다.

### P03: 집계 순회 ABBA 진단 및 최적화 철회 (2026-09-07)

- `target/core-replacement-p03/bucket-scan-cpu-comparison-plan.json`에 실행 전에
  이전 -> 후보 -> 후보 -> 이전 순서를 고정했다. 계획 SHA-256:
  `dfd1efe97635f4be4e29b7238bb7fa06f3ffb199fb5b1b9ac982b2d5bec98170`.
  이전 바이너리는 `693af258...`, 순회 후보는 `e094cd41...`이며 v0.6.0 비교가 아니다.
  기존 도구의 single-node/mixed, 45초 실행 중 20초 49Hz CPU 관측을 사용했다.
  실행 경로는 `target/core-replacement-p03/bucket-scan-cpu-{label}`이다.
- 네 실행 모두 profiler/matrix 종료 코드 0, HTTP 오류 0, 실제 서버 바이너리
  해시 불변을 확인했다. 서버 PID로 분리한 `perf-self.txt`를 각각 보존했다.
  네 표본 모두 perf lost samples 0이며, 유한 표본과 불완전한 unwind 한계는 남는다.

| label | 혼합 req/s | facet mean ms | facet p95 ms | facet p99 ms |
| --- | ---: | ---: | ---: | ---: |
| before-1 | 776.436470 | 6.863897 | 13.666849 | 18.306947 |
| candidate-1 | 744.150098 | 7.341818 | 14.898025 | 20.546615 |
| candidate-2 | 750.688792 | 7.217784 | 14.495537 | 19.501724 |
| before-2 | 761.159991 | 6.997696 | 14.038872 | 19.040291 |

- 후보 두 표본의 facet mean/p95/p99 모두 이전 두 표본보다 높았다.
  서버 CPU의 단순 bucket 수집기 self 비중은 이전 6.58%/6.10%, 후보 6.84%/6.99%,
  memcmp는 이전 9.07%/7.83%, 후보 9.51%/10.52%였다.
  CPU 관측 시간은 순서대로 20.782654/20.790945/20.785881/20.745531초,
  서버 CPU 시간은 31.49/30.47/30.21/30.32초다. 처리량이 다른 부하의 절대 CPU
  시간 감소를 요청당 비용 개선으로 해석하지 않는다.
- 이 45초 profiler 진단은 60초 전체 성능 게이트를 대체하지 않는다.
  다만 전체 부하의 facet 악화와 반복 진단 모두 개선 근거를 제공하지 않으므로
  **집계 -> 문서 순회 최적화만 철회**했다. 기존 문서 -> 집계 순회를 복원했고,
  새 복합 집계 회귀 검사와 count/refresh/pinned-reader 등 정합성 수정은 유지했다.
  기능 지원을 제외한 것이 아니며, 최적화 불가능성을 입증한 것도 아니므로
  ledger에 기능 제외를 등록하지 않는다.
- 철회 후 엔진 소스 SHA-256:
  `80cb54651349e9a3a312f316dd76ca5b6a23ec6347140fee29ea43f941bde1ed`.
  읽기 전용으로 신규 테스트 블록만 제외해 계산한 해시는
  `b5e04534b26095e8636e422be680b5317ba0df9c47ad82a103c62d919bc42c3c`로
  순회 변경 전 소스와 정확히 일치한다. `git diff --check` 통과.
  이는 새 소스의 테스트 실행 증거가 아니다. 재빌드/전체 테스트/실시간 비교/
  전체 성능 재측정은 아직 수행하지 않았으며 다음 단계로 남는다.
  현재 `target/release/steelsearch`는 여전히 철회 전 `e094cd41...`이므로
  철회 후 소스의 검증에 재사용하면 안 된다. 기존 40/44 실패도 취소하지 않는다.
- `diagnostic.json` SHA-256:
  before-1 `522355e47de43679a3565d56cee5e2ec5dd096fa73932c191ebe1f8e5f456596`;
  candidate-1 `ae294cfa50a29e7352376df0d94946f1959a0f9ed26bb589833c1b612ade3c9e`;
  candidate-2 `aced50d48c210bef8a95c92442cb7a000008513708a3073409c1df262558f6d1`;
  before-2 `ba7ee19cc7c73c6fd03d4369d9e49adaf5acaa980bebf804ee85c97b6f8333b4`.

### C05/C06: alias 필터 적용 범위 재현 및 수정 경계 (2026-09-07)

- 철회 후 전체 Rust 테스트를 실행하는 동안, 별도 기능 진단으로 기존
  `count_probe.py`에 무필터 alias 혼합, wildcard alias, 중복/동일 필터 alias,
  match_none 쿼리의 global 집계 검사를 추가했다. 기존 39개 검사는 유지하고
  엔진별 50개로 확장했다. 성능 측정과 병행한 것이 아니다.
- `target/core-replacement-p03/alias-scope-before-diagnostic`에서 후보 **38/50**,
  OpenSearch 3.7.0-SNAPSHOT **50/50**이었다. 종료 코드 1, 후보 바이너리는
  여전히 철회 전 `e094cd41...`이며 실행 중 해시가 유지됐다. 이 결과는
  철회 후 소스의 검증이나 전체 검색 호환성 검증이 아니다.
- 기존 실패 5개 외에 wildcard-filtered-alias, duplicate-filtered-alias,
  equivalent-filtered-aliases 각각 count/search 6건과 filtered alias의
  global 집계 1건이 추가로 재현됐다. 무필터 alias 혼합 및 union/direct-index
  global 집계 대조는 통과했다. 테스트 수 증가를 런타임 회귀 증가로 해석하지 않는다.
- probe SHA-256: `0eec44832154c584b41607dc6598da71a464820d3936e1e23ed78740f2554073`;
  execution: `46dcc0b8339e78d38079e5438598ef9495a73a3fcff75f4a4f314159aa87ee70`.
- 로컬 OpenSearch 소스 HEAD `f991609d190dfd91c8a09902053a7bbfe0c27b3e`에서
  `IndexNameExpressionResolver.indexAliases`, `ShardSearchRequest.parseAliasFilter`,
  `DefaultSearchContext.buildFilteredQuery`, `DefaultAggregationProcessor`의
  global collector 경로를 확인했다. 직접 인덱스 또는 무필터 alias는 그 인덱스의
  필터를 해제하며, 여러 필터 alias는 OR로 결합한다. 검색 쿼리와는 점수에
  기여하지 않는 FILTER로 결합하고, global 집계에도 alias 범위는 유지한다.
- 현 구현의 `resolve_search_targets`는 인덱스 이름만 반환해 필터를 잃는다.
  `handle_count_route`는 필터 없는 쿼리를 native 엔진에 전달한다.
  `handle_index_search_route`의 native/fallback 양쪽 모두 alias 범위가 없고,
  fallback은 사용자 쿼리 평가 전에 무필터 `aggregation_context_hits`를 만든다.
  따라서 query 하나에 bool.filter를 붙이는 수정만으로는 global 집계가 해결되지 않는다.
- 다음 구현 단위의 필수 경계:
  1. 동일 metadata snapshot에서 실제 인덱스, alias 필터 OR, 직접/무필터 우선 규칙,
     인덱스별 routing 범위를 함께 해석한다. wildcard와 중복 selector를 포함한다.
  2. native 검색/count에 인덱스별 필터를 전달하고 점수·total·hits·일반/global 집계에
     일관되게 적용한다. 사용자 REST 입력이 내부 범위 정보를 위조하지 못해야 한다.
  3. fallback도 후보 문서/global 문서 범위에 같은 필터를 적용한다. total만 바꾸거나
     반환 hits만 후처리하는 방식은 허용하지 않는다.
  4. PIT 생성 시 범위를 보존하고 검색/scroll/복구 경로에서 소실되지 않게 한다.
     PIT 뒤 alias 변경 시 동작은 참조로 확인한 뒤 고정한다. 복구 필드의 기본값과
     이전 데이터 호환성도 검증한다.
  5. 다중 인덱스의 서로 다른 필터, 점수 보존, 검색 페이지 누락/중복,
     일반/global 집계, routing 교집합과 실제 HTTP 응답을 참조와 비교한다.
     단일 count 진단 통과만으로 C05/C06을 완료 처리하지 않는다.
  6. 구현 후 전체 소스/통합/실시간 검사 및 전체 비플러그인 벤치마크를 실행한다.
     최초 v0.6.0 누적 5% 기준과 기존 실패 기록은 유지한다.

#### PIT 범위 및 삭제 후 GET 추가 재현

- `count_probe.py`에 PIT 생성, alias 변경 전후 PIT hits/total/global 범위,
  변경된 alias의 live 검색, alias 복원/PIT 삭제 7개 검사를 추가했다.
  `target/core-replacement-p03/alias-pit-before-diagnostic`에서 후보 **41/57**,
  참조 **57/57**, 전체 명령 종료 코드 1이었다. 후보 바이너리 `e094cd41...`의
  진단이며 Rust 컴파일과 겹친 기능 검사다. 성능 증거로 사용하지 않는다.
- OpenSearch는 alias를 tenant a에서 b로 변경한 뒤에도 기존 PIT에서 문서 one과
  global doc_count 1을 유지했고, live alias 검색은 문서 two로 바뀌었다.
  후보는 PIT 변경 전후와 live alias 검색 모두 필터 밖 문서까지 반환했다.
  로컬 `SearchContextId.aliasFilter` 및 `TransportSearchAction`의 PIT 경로도
  생성 시점 필터 보존과 일치한다. SteelSearch transport에는
  `OpenSearchSearchContextIdWire::with_alias_filters`가 이미 있지만 REST PIT 생성은
  `new(shards)`를 쓰고 `PitContext`/`PersistedPitContext`에도 alias 필터가 없다.
  새 wire 표현을 만들기 전에 기존 표현과 지원 쿼리 경계를 연결해야 한다.
- **C04/D 우선 수정 후보:** 같은 실행에서 DELETE 문서 two는 HTTP 200,
  result deleted, seq_no 3/version 2를 반환했지만 뒤따른 realtime GET은
  HTTP 200, found true, seq_no 1/version 1의 과거 source를 반환했다.
  기존 50개 진단에서는 통과했던 검사가 확장 시나리오에서 실패했다.
  단순 시간 변동으로 면제하지 않으며 alias/PIT 보강과 별도 정합성 재현으로 보존한다.
- `handle_get_doc_route`는 메모리 조회 실패 시
  `lookup_development_operation_log_document`로 fallback한다. 이 함수는 manifest의
  max seq_no 이하 `_source` 레코드를 반환하지만 현재 메모리 삭제 상태와 비교하지
  않는다. `handle_delete_doc_route`의 pending 삭제, 디스크 로그/manifest 갱신,
  fallback GET/HEAD 및 재시작 후 삭제 유지까지 함께 확인해야 한다.
  GET에서 임시로 응답만 숨기는 변경으로 완료 처리하지 않는다.
- 최신 probe SHA-256:
  `c2240bb25c1a0a50a81fbc074f6f11207d6c409b8dae4a3542c0c0d033d2d3d1`;
  execution: `ad10e60652c7879cbc830dfd5dca5714a1d3cef8d3a6addf585e8ece105c8515`.
  이 실행의 실패 16건은 기존 범위 12건, PIT/live alias 3건,
  realtime-delete 1건이다. 모든 원시 응답과 실패를 유지한다.
- 보존된 `candidate/node-1/data/shards/c05-count-contract/0/`의
  `steelsearch-operations.jsonl`에는 문서 two의 seq_no 1/version 1 원문이 남아 있다.
  로그 SHA-256: `d791feb833ac29eafa1d5f09111cc3492df1d92e6a5bdfa805d1e096d4337a1d`.
  같은 디렉터리 manifest의 max_sequence_number/local_checkpoint/
  refreshed_sequence_number는 모두 1이다. 이 파일들은 진단 종료 후 보존 상태이며
  GET 실행 순간의 디스크 스냅샷이라고 주장하지 않는다. 삭제 응답 seq_no 3보다
  오래된 디스크 fallback이 가능한 코드 경로와 일치하는 추가 근거다.

### P03: 순회 철회 후 소스 재검증 (2026-09-07)

- 엔진 `80cb5465...`, 노드 `36acddaa...` 소스로 전체 lib 테스트를 실행했다.
  종료 코드 0, 엔진 **835/835**, 노드 **600/600** 통과, ignored/filtered 0이다.
  유지한 복합 집계 회귀 검사도 통과했다. 빌드 14분 47초,
  테스트 실행 각각 2.59초/1.05초다.
- `target/core-replacement-p03/bucket-scan-withdrawn-engine-node-full.log`
  SHA-256: `bff01798b7eaa264ae1f1cd368eac0ea7fe9217bd7cc1a6250d005fd9e3c7445`.
  엔진·노드 소스는 테스트 시작 후 변경하지 않았다. `git diff --check` 통과.
- 동시 refresh/검색 통합 검사는
  `target/core-replacement-p03/bucket-scan-withdrawn-integration.log`에서
  종료 코드 0, **7/7 통과**했다(4.13초, ignored/filtered 0).
  로그 SHA-256: `2559afb635ce69bb0c35cf1a02de68ee34555987ce04b823a7f73c2c0d1f4a6e`.
  standalone 바이너리 재빌드와 전체 성능 재측정은 아직 남아 있다.
  검사 후 `target/release/steelsearch` 해시는 여전히 `e094cd41...`로 철회 전 후보다.
  위 lib 통과로 새 alias/PIT 및 디스크 fallback GET 실패를 해결된 것으로 보지 않는다.

### P03: 철회 후 바이너리 및 fresh 기준선 반복 검증 (2026-09-07)

- standalone release 재빌드는 종료 코드 0, 4분 34초에 완료됐다.
  실행 바이너리 SHA-256은 `693af258fa59c932012ff07db5316dcef8f41b64b6efb83246a334d01e1f3533`로
  보존한 순회 변경 전 후보와 정확히 일치한다. 거부된 후보는
  `target/core-replacement-p03/steelsearch-bucket-scan-rejected`에 `e094cd41...`로 보존했다.
  `bucket-scan-withdrawn-release-build.log` SHA-256:
  `4cffbcd349918af08eb422d56f159eea206b788fbaa5dc6452ee19937139369e`.
- 최신 바이너리의 `target/core-replacement-p03/live-bucket-scan-withdrawn` 결과는
  설정/routing 통과, projected core search 1180/1180, nested-bool 각각 130/160,
  확장 count/alias/PIT probe 후보 41/57, 참조 57/57이다.
  setup 실패/skip 0, binary/fixture 해시 불변이다. alias/PIT 및 realtime-delete를
  포함한 16개 probe 실패가 동일하게 남아 전체 명령은 종료 코드 1이다.
  execution SHA-256: `faaa23bb5a24961f03515081811b59b098b5cf831b0ed3d36486b16e2807e5c3`.
- 성능 판정 도구의 `test_core_performance_budget`, `test_core_performance_reports`,
  `test_core_performance_gate` 43개 Python unittest도 모두 통과했다.
  테스트의 모의 실행은 실제 성능 측정으로 계산하지 않는다.
- `tools/run_core_performance_gate.py`로 전체 반복 부하를 시작했다. 출력 경로는
  `target/core-replacement-p03/bucket-scan-withdrawn-repeated-full`이다.
  v0.6.0 바이너리 `db244133...`도 새로 실행하며, 사전 고정 순서는
  baseline/candidate/OpenSearch/OpenSearch/candidate/baseline이고 각 실행에
  단일/3노드가 포함돼 총 12개 시나리오다. 기준선을 직전 후보로 바꾸지 않는다.
  실행 계획 SHA-256: `8519c6f98a6767b7a97c5f9ce8a16806f4ca9d4ceadce575e2b054cd19126c0d`.
- 12개 시나리오 실행을 **1096.49초**에 완료했다. 6개 실행 명령 종료 코드 모두 0,
  모든 시나리오 HTTP 오류 0, execution inputs 검증 true, infrastructure error 없음이다.
  최종 **반복 수치 게이트는 실패(종료 코드 1)**했다. 결과 SHA-256:
  `1ae65d61f7a730a55ef713e56bcf7cba2eefc3a0f7dcc956fea2f22ed9ffb183`.

| 후보 실행 | 공개 v0.6.0 대비 | 같은 회차 fresh v0.6.0 대비 | fresh 기준선 자체의 공개값 대비 |
| --- | ---: | ---: | ---: |
| 01-candidate (00-baseline, 02-opensearch와 연결) | 42/44 | 44/44 | 41/44 |
| 04-candidate (05-baseline, 03-opensearch와 연결) | 44/44 | 43/44 | 43/44 |

| 실패 비교 | 지표 | 비교 기준 ms | 측정 ms | 악화 |
| --- | --- | ---: | ---: | ---: |
| 공개 v0.6.0 -> 01-candidate | single-node/refresh/p99 | 18.166180979460474 | 19.620256270281992 | +8.004298% |
| 공개 v0.6.0 -> 01-candidate | three-node/sort_filter/p95 | 7.190116588026285 | 7.570273999590427 | +5.287222% |
| 05-baseline -> 04-candidate | three-node/sort_filter/p99 | 10.360536740627149 | 11.486806906759728 | +10.870770% |

- fresh 기준선의 공개값 대비 초과도 따로 보존한다. 00-baseline은 single-node
  write p95 +5.441941%, write p99 +7.040432%, refresh p99 +5.370620%,
  05-baseline은 three-node facet p95 +5.434257%다. 이는 관측된 기준선 변동이며
  후보 실패가 모두 잡음이라는 증명이나 5% 기준을 완화할 근거가 아니다.
  04-candidate의 공개값 44/44만 선택해 전체 반복을 합격시키지 않는다.

| 후보 / 토폴로지 | 후보 req/s | 공개 v0.6.0 대비 처리량 변화 | 연결 OpenSearch req/s | OpenSearch 대비 |
| --- | ---: | ---: | ---: | ---: |
| 01 / single-node | 739.690348 | -0.446928% | 283.718591 | 2.607127x |
| 01 / three-node | 915.910252 | -1.659894% | 107.144785 | 8.548342x |
| 04 / single-node | 747.507725 | +0.605194% | 282.724905 | 2.643940x |
| 04 / three-node | 919.549174 | -1.269188% | 109.693712 | 8.382880x |

- 새 기준선 처리량은 00에서 single/three 724.980802/922.219525 req/s,
  05에서 745.947541/908.831489 req/s였다. 공개 기준값은 바꾸지 않는다.
  각 후보 실행을 공개 v0.6.0 및 동시점 v0.6.0과 개별 비교했으며 percentile을
  합치거나 평균 내어 실패를 숨기지 않았다. 숫자 통과만으로 소스 출처/실제 운영 설정/
  기능 호환성까지 증명하는 것은 아니며, 단위·릴리즈 수락은 여전히 별도다.
- 순회 철회 후 재빌드/전체 lib/통합/실시간/전체 반복 부하 실행은 끝났지만,
  기능 실패와 수치 게이트 실패 때문에 단위 수락은 안 된다. 다음 구현 우선순위는
  재현된 삭제 후 GET 정합성 문제, 이어서 인덱스별 alias/PIT/집계 범위 보강이다.
  성능은 해당 수정 후에도 전체 부하로 재검증하며, 현재 refresh/sort 지연 문제와
  기준선 변동은 미해결 관측으로 남긴다. ledger 제외는 없다.

### C04/D: 오래된 삭제 문서의 GET/복구 재등장 방지 후보 (2026-09-07)

- `DocumentDeletionSequences`를 인덱스 -> 샤드 -> 문서 ID -> 삭제 seq_no 구조로
  추가했다. 단건/bulk/by-query 삭제 시 `documents_state` 잠금 안에서 삭제 표시를
  기록한다. by-query 삭제도 sequence를 할당한다. routing이 다른 샤드의 동일 ID는
  별도로 다루며, 늦게 기록된 낮은 삭제 sequence가 기존 값을 낮추지 않는다.
- 디스크 GET fallback은 삭제 sequence 이하의 원문을 거부한다. 존재하지 않는
  인덱스의 남은 디스크 경로도 조회하지 않는다. 작업 로그 복구는 읽을 때와
  메모리 병합 직전에 삭제 표시를 검사한다. shared state의 오래된 원문도 복구 시
  표시보다 이전이면 제거한다. newer sequence의 문서는 허용한다.
- 삭제 표시는 SharedRuntimeState에 저장하고 `serde(default)`로 이전 형식의
  누락 필드를 수용한다. 이것이 이전 버전에 이미 잃어버린 삭제 이력을 복원한다는
  의미는 아니다. GC/보관 상한, 손상된 checkpoint와 메타데이터 불일치, 인덱스
  삭제/재생성 및 snapshot 조합, 동시 저장·장애 원자성의 충분한 검증은 아직 남는다.
- 삭제만 남은 인덱스의 복구 후 native sequence가 0부터 재사용되지 않도록
  `TantivyEngine::restore_next_sequence_number`를 추가했다. 음수/없는 인덱스를
  거부하고 sequence를 낮추지 않는다. 복구된 REST next sequence를 native 엔진에
  전달한 뒤 refresh하며, 일반 검색 요청 경로에는 이 작업을 추가하지 않는다.
- 신규 node 회귀 검사는 실제 오래된 shard log를 보존한 상태에서 단건/bulk/by-query
  삭제 후 GET/HEAD, 로그 병합, shared state 저장/재시작, 동일 ID 재생성을 검사한다.
  별도 검사는 삭제 표시의 샤드/인덱스 분리와 단조성을 확인한다. engine 검사는
  삭제 뒤 빈 인덱스의 sequence floor, 낮은 값 무시 및 refresh 후 새 쓰기를 확인한다.
- `cargo +nightly check --release -p os-node --tests`는 종료 코드 0, 22.97초로 통과했다.
  로그 `target/core-replacement-c05/deletion-sequences-tests-check.log` SHA-256:
  `e81eb43245f3f4bae0406b3390ed335ac8c0c3034d7e570958744b2e35ecdedc`.
  engine 신규 테스트는 이 타입 검사 뒤 추가했으므로 전체 테스트 실행으로 확인해야 한다.
- 전체 engine/node lib 테스트를
  `target/core-replacement-c05/deletion-sequences-engine-node-full.log`에서 완료했다.
  종료 코드 0, engine **836/836**, node **602/602**, ignored/filtered 0이다.
  빌드 14분 30초, 실제 테스트 실행 각각 2.48초/1.04초. 새 회귀 검사 3개도 통과했다.
  로그 SHA-256: `fff190890d064b789fba986e8ef2830c048ca8ee69149f72ce15de83a8a6102a`.
  테스트 입력 engine SHA-256 `280a6186d2a09ef59d01b3cec311a9af6aed98c556268e99965a105376a1d55d`,
  node `c977930d409351498a415ccdbf5388ad098a25b5fed97891cb24e9029fb441f1`.
  실행 후에도 두 소스 해시가 유지됐다. 동시 refresh/검색 통합 검사도
  `target/core-replacement-c05/deletion-sequences-integration.log`에서 **7/7 통과**했다.
  종료 코드 0, ignored/filtered 0, 빌드 2분 11초, 테스트 3.91초다.
  로그 SHA-256: `5a4feec750093d841040cecd3438142e53606270d2d01f97a4dee175a5ce685d`.
  검사 후 `target/release/steelsearch`는 여전히 변경 전 `693af258...`이다.
  새 바이너리/실시간/전체 성능 검증은
  아직 없으며, 후보 구현을 문제 해결 또는 단위 수락으로 선언하지 않는다.

### C04/D: 삭제 이력 후보의 실행 검증 (2026-09-07)

- standalone release 빌드는 종료 코드 0, 4분 35초에 완료됐다.
  실행 바이너리 SHA-256: `05f45ab7a6ac4d71e6d7f63797009b3adfd1f2f7690f0e2009fc3ce088d10adf`.
  이전 후보는 `target/core-replacement-c05/steelsearch-before-deletion-sequences`에
  `693af258...`로 보존했다. `deletion-sequences-release-build.log` SHA-256:
  `debabc8bff10da73ff2eedeaeeed8912fcf3c12a16564d4c561ce7ce743e7cdf`.
- `target/core-replacement-c05/live-deletion-sequences`에서 OpenSearch 3.7.0-SNAPSHOT과
  실시간 비교했다. 기존 실패였던 realtime-delete GET이 **404 / found=false**로
  바뀌어 통과했고, probe는 후보 **42/57**, 참조 **57/57**이다.
  기존 alias/PIT 및 missing-wildcard 15건은 남는다. 이 재현의 수정은 확인했지만
  삭제 이력의 모든 장애/운영 조합이 해결됐다는 주장은 아니다.
- 설정/routing 통과, projected core search **1180/1180**, nested-bool 두 fixture는
  각각 **130/160**이다. setup 실패/skip 0, 실행 바이너리/fixture 해시 불변.
  남은 실패 때문에 전체 live 명령 종료 코드는 1이다.
  execution SHA-256: `d0deaff849a42da023535530a0f4eaa8fbab2d43801fe490d2173743616f0eb9`;
  core report: `6a3e56d442345d7811f6645bfcc57df65609b6b88a721dca38233d8a924dfca3`.
- 전체 반복 성능 실행은 `target/core-replacement-c05/deletion-sequences-repeated-full`에서
  완료했다. 계획 SHA-256: `3820af7e0d87a54c81435f8e20bc823bdb52e012773e2caf16c8551719b66e43`.
  baseline/candidate/OpenSearch/OpenSearch/candidate/baseline 각 단일/3노드로 총 12개,
  최초 v0.6.0 바이너리 `db244133...` 및 공개 보고서 기준은 고정한다.
  12개 summary의 요청 오류는 모두 0이고 `execution_inputs_verified=true`이나,
  `numeric_budget_passed=false`, `acceptance_established=false`다.
  결과 SHA-256: `ff410d5187a6fed1b73b11e850d2bc5e52e27b63ac94ac23a76528cd1d74ad4f`.
- 반복별 44개 지표 통과 수는 다음과 같다. 서로 다른 반복의 통과 지표를 합치거나
  백분위수를 평균내서 통과로 바꾸지 않는다.

  | 후보 실행 | 공개 v0.6.0 대비 | 동반 실행 v0.6.0 대비 | 동반 기준선의 공개 기준 대비 |
  | --- | --- | --- | --- |
  | 01-candidate (00/01/02) | 44/44 | 43/44 | 42/44 |
  | 04-candidate (05/04/03) | 42/44 | 44/44 | 41/44 |

- 후보 초과 지표를 비교 지점별로 분리한다. 지연 단위는 ms다.

  | 후보 실행 / 비교 기준 | 지표 | 기준 | 후보 | 누적 또는 해당 쌍의 저하 |
  | --- | --- | --- | --- | --- |
  | 01 / 동반 00 기준선 | single-node lexical p95 | 8.592302 | 9.055894 | +5.395433% |
  | 04 / 공개 v0.6.0 | single-node write p95 | 5.275250 | 5.555917 | +5.320452% |
  | 04 / 공개 v0.6.0 | three-node ranking p99 | 11.304207 | 11.949474 | +5.708199% |

- 처리량은 다음과 같다. 이 혼합 부하의 ops/s이며, 기능 동등성이나 운영 환경 전체의
  우위를 뜻하지 않는다. OpenSearch 성능 참조는 고정된 2.19 이미지이며 위 기능
  probe의 3.7.0-SNAPSHOT과 다르다. 처리량 통과로 지연 실패를 상쇄하지 않는다.

  | 후보 실행 / topology | 공개 v0.6.0 | 후보 | 공개 기준 대비 처리량 저하 | 동반 OpenSearch |
  | --- | --- | --- | --- | --- |
  | 01 / single-node | 743.011070 | 741.617702 | 0.187530% | 285.803974 |
  | 01 / three-node | 931.370011 | 923.508711 | 0.844058% | 115.089843 |
  | 04 / single-node | 743.011070 | 737.922620 | 0.684842% | 288.640099 |
  | 04 / three-node | 931.370011 | 915.722257 | 1.680079% | 115.275224 |

- 동반 기준선 자체의 초과도 보존한다. 00 실행은 three-node facet p99 +5.529761%,
  refresh p99 +5.404155%; 05 실행은 single-node sort_filter p95 +5.086814%,
  three-node ranking p99 +5.174861%, nested p99 +12.001140%다.
  이 관측만으로 후보의 실패를 잡음으로 면제하거나 삭제 이력 기능에 귀속하지 않는다.
- **현재 반복 게이트는 실패이며 C04/D 단위 수락은 보류한다.** 단일 구현의 5% 이상
  저하와 최적화 불가가 입증되지 않아 ledger 제외는 없다. 기존 실패 결과를 유지하며
  통과 결과가 나올 때까지 무계획 재실행하지 않는다. 자원/실행 조건과 해당 경로의
  진단으로 원인을 좁힌 뒤 전체 반복 부하로 검증한다.

### C04/D 다음 검증 단위: 삭제 이력과 복구 sequence 일관성

- 코드 검토에서 `sync_shared_runtime_state_from_disk`가 per-index next sequence
  맵이 비어 있을 때 살아 있는 문서만으로 재계산하고, 비어 있지 않으면 그대로
  신뢰하는 것을 확인했다. 삭제 표시의 최대 sequence는 이 계산에 반영되지 않는다.
  `restore_next_sequence_number`는 전달된 값만 사용하므로 이 입력 불일치를
  독자적으로 해결하지 못한다. 아직 실행 재현으로 확정한 결함은 아니다.
- 재현 검사는 정상 삭제/저장 후 next sequence 맵 누락, 일부 인덱스 누락, 낮은
  watermark를 각각 주입하고 재시작한다. 삭제된 문서만 있는 인덱스와 살아 있는
  문서가 있는 인덱스, 서로 다른 인덱스/샤드/라우팅을 포함한다. 새 쓰기 sequence가
  기존 문서와 삭제 표시보다 반드시 커야 하며 GET/검색/재시작에서 재등장하지 않아야 한다.
- 저장 상태의 음수 삭제 sequence, 표현 범위를 넘는 next sequence, 최댓값에서의
  증가 불가를 검사한다. 복구 입력이 유효하지 않으면 상태를 부분 설치하거나
  sequence를 낮추지 말고 기존 recovery-failed 경로로 요청을 거부해야 한다.
  누락 필드의 이전 형식 호환성과 손상 상태 허용은 구별한다.
- 삭제 표시의 안전한 보관 상한/GC는 로그 및 checkpoint의 삭제 반영 증거가
  확보된 뒤에만 적용한다. 단순 TTL/개수 제한으로 오래된 로그의 재등장을 허용하지
  않는다. 삭제 집중 장기 부하의 메모리/저장 비용 검사는 기존 혼합 부하에 추가한다.
- 구현 후 engine/node 전체 lib, 동시 refresh 통합, 실제 HTTP 재시작 및 기존 live
  비교를 실행하고, **전체 비플러그인 반복 벤치마크를 반드시 실행한다.** 최초
  v0.6.0의 각 지표 5% 누적 예산은 유지한다. 이 목록은 완료 실적이 아니다.

### C04/D: 복구 watermark 보강 후보 및 수정 전 HTTP 재현 (2026-09-07)

- `recovered_next_seq_no_by_index`는 저장된 per-index watermark, 저장 문서,
  삭제 표시를 인덱스별 최대값으로 합친다. 오래된 원문을 제거하기 전에 계산하며,
  부분 누락도 보완하고 기존의 더 높은 watermark는 낮추지 않는다. global watermark는
  복구된 per-index 최대값 이상으로 유지한다. 음수 sequence, 증가할 수 없는 경계값,
  i64 범위를 벗어난 watermark는 메타데이터/문서를 설치하기 전에 기존 recovery-failed
  경로로 거부한다. 정상 요청의 sequence 할당 경로 자체를 변경한 것은 아니다.
- 신규 node 회귀 검사는 3샤드의 삭제 문서만 남은 인덱스/살아 있는 문서가 있는
  인덱스에 대해 watermark 전체 누락, 일부 누락, 낮은 값을 주입한다. 복구 후
  동일 ID 재생성 sequence와 두 번째 재시작의 GET/검색을 검사한다. 별도 검사는
  음수/최댓값/범위 초과 등 8종 입력을 거부하고 복구 전 상태를 유지하는지 확인한다.
- HTTP 진단 `target/core-replacement-c05/recovery_watermark_probe.py`는 별도 프로세스를
  정지한 상태에서 shared JSON을 변조하고 실제 재시작한다. 최초/변조 입력과 모든
  HTTP 요청/응답, `/proc/PID/exe` 해시를 남기며 마지막에 소유 프로세스를 종료한다.
  per-write persistence 활성화, deferred native/shard write 비활성화로 실행하며
  성능 수치나 전원 장애 원자성의 증거로 사용하지 않는다.
- 수정 전 후보 `05f45ab7...`의 `recovery-watermarks-http-before/result.json`에서
  **22/48 통과, 26/48 실패**로 재현했다. missing 6/14, partial 10/14, stale 6/14;
  negative/exhausted 각각 0/3이다. empty-index는 필요한 seq 4 대신 0을 재사용했고,
  두 번째 재시작에서 새 문서가 GET 404 및 검색 total 0으로 사라졌다. 살아 있는
  문서가 있는 인덱스도 missing/stale에서 새 문서가 사라졌다. 음수/증가 불가 삭제
  sequence 상태에서 쓰기를 201로 허용했다. setup 오류는 없고 바이너리 해시는 불변이다.
  결과 SHA-256 `abbff3b635720c76a4fda1d1d5f3ce3a53cb38a0c1f7b30b401a1c5e3e2d2b4a`;
  probe SHA-256 `d5be61f6fad9c255c0e833bd3bc48272b972b9638f73cb7bd2bcc4d13ac4f0df`.
- 첫 focused 빌드는 테스트 assertion의
  잘못된 초기 상태 가정을 발견해 의도적으로 중단했다(종료 130). 수정 후 전체
  테스트를 시작했으며 이 중단을 통과나 제품 실패로 세지 않는다. 첫 전체 실행은
  engine 836/836, node 602/604로 종료 101이었다. 새 테스트 2건은 데이터 경로가
  없어 기존 저장 guard가 저장을 생략한 탓에 파일 읽기에서 실패했다. 원래 로그
  `recovery-watermarks-engine-node-full.log` SHA-256:
  `89958f22cc6f45cb6d74f1b538f13daab0fd38230634b2eae24c478ceabc8c9c`.
- fixture에 실제 데이터 경로를 지정해 전체 테스트를 재실행했다. 제품의 저장
  guard나 기대 정합성을 완화하지 않았다. 현재 node 소스 SHA-256:
  `16fff962215c44ac8019c167460303a7832284e2faf610f2cac75a39ae986b77`.
  `recovery-watermarks-engine-node-full-final.log`는 종료 0, 빌드 5분 47초,
  **engine 836/836, node 604/604**, ignored/filtered 0이다. 실행 시간은 각각
  2.25초/1.20초이며 신규 회귀 검사 2건도 통과했다. 로그 SHA-256:
  `d07b4ac3953662921509f40404dc08241872c11db670dc3c21b74b222ab3a85a`.
- `recovery-watermarks-integration.log`의 동시 refresh/검색 통합 검사도 종료 0,
  **7/7 통과**, ignored/filtered 0, 4.23초다. 로그 SHA-256:
  `8cfded9b94279a82d3dadce83fcd1120d56ff49b494824f6fb117a46136cc768`.
  성능 예산/보고서/반복 실행기 Python 회귀 검사도 **43/43 통과**했다.
  아래 standalone 실행 검증으로 이어졌으며 단위 수락은 보류한다.

### C04/D: 복구 watermark 수정 후 실행 검증 (2026-09-07)

- standalone release 빌드 종료 0, 4분 37초. 새 실행 바이너리 SHA-256:
  `aebc0503bfb9bca5f825448d7a58a8656429de08864faab4dc8ccbc974edaadd`.
  `recovery-watermarks-release-build.log` SHA-256:
  `3a73cad0774458738e9341cf9d383093db858551b6d2aa40790871d39c0e1586`.
  이전 후보 `05f45ab7...`는 `steelsearch-before-recovery-watermarks`에 보존했다.
- 동일한 HTTP probe의 `recovery-watermarks-http-after/result.json`은 종료 0,
  **48/48 통과**다. missing/partial/stale 각각 14/14, negative/exhausted 각각
  3/3이며 setup 오류 0, 실행 파일 해시 불변이다. 정상 보완은 새 sequence와 두 번째
  재시작 뒤 GET/검색 보존을, 잘못된 입력은 GET/검색/쓰기 503을 확인했다.
  수정 전 26건의 실패가 모두 통과했다. 결과 SHA-256:
  `3d6b2460a39ca6a8bf6a6c5ffd3d06b11b5302a1628b559964cf849d1cfc98c6`.
- `live-recovery-watermarks`의 OpenSearch 3.7.0-SNAPSHOT 비교는 설정 84/84,
  routing 118/118, projected core search 1180/1180이다. nested-bool 두 fixture는
  각각 130/160, 확장 count/alias/PIT probe는 후보 42/57, 참조 57/57이다.
  남은 alias/PIT/missing-wildcard 15건 및 nested 집계 실패는 이전과 동일하다.
  realtime-delete GET 통과는 유지됐다. setup 오류/skip 0, 실행 바이너리/fixture
  불변이나 남은 실패로 전체 live 명령은 종료 1이다.
  execution SHA-256 `bed2b139e67b5ec2b33feed09d1e2024905d972d08a9009ae04dc3bc010fd6c7`;
  core report `2f2cbc4cbedafa9d541323e9b5863ab7dfcb2941d59fd92b6c5fad6b4f67d01f`.
- 빌드/기능 검사 프로세스 종료 확인 후
  `target/core-replacement-c05/recovery-watermarks-repeated-full`에서 전체 반복 성능
  검증을 완료했다. 고정 순서 baseline/candidate/OpenSearch/OpenSearch/candidate/baseline,
  각 단일/3노드로 총 12개이며 최초 v0.6.0 바이너리/공개 보고서 해시를 재확인했다.
  계획 SHA-256 `3bde1a613fe38da39611953a63113f207d6b54d6393bc656e73bf6f86e97e68a`.
  총 1096.82초, 6개 하위 명령 종료 0, 12개 시나리오 요청 오류 0이다.
  `execution_inputs_verified=true`이나 최종 명령은 **종료 1 / 수치 게이트 실패**다.
  결과 SHA-256 `4e5cc178e54987851235611d1d4846ca8b8f15a0565883dfe852f52eb29fcb6a`.

  | 후보 실행 | 공개 v0.6.0 대비 | 동반 v0.6.0 대비 | 동반 기준선의 공개 기준 대비 |
  | --- | --- | --- | --- |
  | 01-candidate (00/01/02) | 44/44 | 43/44 | 42/44 |
  | 04-candidate (05/04/03) | 43/44 | 43/44 | 43/44 |

- 후보 초과 지표는 아래와 같다. 지연은 ms, 비교 기준은 행별로 구별한다.

  | 후보 실행 / 비교 기준 | 지표 | 기준 | 후보 | 저하 |
  | --- | --- | --- | --- | --- |
  | 01 / 동반 00 기준선 | single-node sort_filter p99 | 13.827972 | 14.615716 | +5.696744% |
  | 04 / 동반 05 기준선 | three-node lexical p99 | 10.287185 | 10.903208 | +5.988264% |
  | 04 / 공개 v0.6.0 | three-node lexical p99 | 10.130533 | 10.903208 | +7.627194% |

- 동반 기준선 자체는 00에서 three-node ranking p99 +5.918970%, nested p99
  +8.081094%; 05에서 three-node ranking p99 +6.634531%로 공개 기준을 초과했다.
  이 관측이 후보 실패의 면제 근거나 단일 기능에 대한 귀속 증거는 아니다.
- 혼합 부하 처리량 비교는 다음과 같다. 변화는 공개 v0.6.0 대비이며 양수는
  처리량 증가다. ops/s의 개선으로 다른 지표 실패를 상쇄하지 않는다.

  | 후보 실행 / topology | 공개 v0.6.0 | 후보 | 처리량 변화 | 동반 OpenSearch 2.19 |
  | --- | --- | --- | --- | --- |
  | 01 / single-node | 743.011070 | 744.874218 | +0.250757% | 284.744705 |
  | 01 / three-node | 931.370011 | 920.906599 | -1.123443% | 113.248930 |
  | 04 / single-node | 743.011070 | 751.612310 | +1.157619% | 280.055546 |
  | 04 / three-node | 931.370011 | 922.353597 | -0.968081% | 116.317097 |

- 삭제 이력 GC, 동시 저장 장애 원자성 등 남은 범위와 별개로 watermark 재현 수정만
  확인했다. 이번 변경의 단독 5% 이상 저하와 최적화 불가가 입증되지 않았으므로
  ledger 제외는 없다. 전체 성능 게이트 실패를 보존하며 C04/D 수락은 보류한다.

### C04/D 다음 우선 수정: 인덱스 재생성의 이전 세대 오염 재현

- 전체 성능 측정 종료 후, 같은 후보 `aebc0503...`에서
  `target/core-replacement-c05/index_recreation_probe.py`를 실행했다.
  인덱스에 old/reused를 쓰고 reused를 삭제한 뒤 인덱스 자체를 삭제/재생성한다.
  reused를 새 내용으로 쓰고 실제 프로세스를 재시작하는 진단이다. shared state를
  변조하지 않고 정상 HTTP 요청만 사용했다. 결과는 **6/10 통과, 4/10 실패**, 종료 1,
  setup 오류 0, 실행 파일 해시 불변이다.
- 재생성 직후 이전 old 문서 GET이 404가 아니라 **200**이었다. 새 reused 문서는
  쓰기 201 및 재시작 전 GET 200이지만, 재시작 후 **GET 404**로 사라졌다.
  이전 old 문서는 재시작 후에도 200이었다. 검색 total 1은 통과했으나 실제 hit의
  `_id=old`, `_source.value=old`였다. 따라서 total 일치가 데이터 정합성 증거가
  아님을 명시하며, 후속 회귀 검사에는 정확한 ID/source 집합도 assertion으로 추가한다.
- `index-recreation-http-before/before-restart.json`에는 새 reused 문서 seq 0과
  이전 reused 삭제 표시 seq 2가 같은 인덱스 이름 아래 공존하고 next sequence는
  1이었다. create 경로는 sequence를 0으로 초기화하지만 delete 경로는 삭제 표시를
  정리하지 않는다. GET fallback/복구가 인덱스 이름의 이전 디스크 로그를 읽는 경로도
  함께 검증해야 한다. watermark 보강만으로 인덱스 세대 분리까지 해결되지 않는다.
- 다음 구현은 인덱스 세대 식별과 로그/삭제 이력의 수명주기를 함께 다룬다. 삭제
  표시만 비우거나 이전 세대 sequence를 계속 올려서 증상을 숨기지 않는다. 새 인덱스의
  정상 sequence 의미를 보존하면서 오래된 로그와 삭제 이력이 새 세대에 적용되지
  않게 해야 한다. 단일/다중 샤드, routing, 빈 인덱스, 재시작, 실패한 삭제/저장과
  snapshot 복구 조합을 검사한다. 구현 후 전체 기능/통합 및 전체 비플러그인 반복
  벤치마크, 최초 v0.6.0 누적 5% 게이트를 다시 적용한다.
- 결과 `target/core-replacement-c05/index-recreation-http-before/result.json` SHA-256:
  `398d90606b84e8ef54c93a1d56dc826de9bff86f80f563035ec89b871307942f`;
  probe `a0d0b234b0e8edd791dfae68fb0ab01366e4ec814672a0230814657f274f1ac4`.
  모든 소유 프로세스/벤치마크 컨테이너 종료를 확인했다. 기존 사용자 컨테이너는
  변경하지 않았다. 이 결함은 미수정이며 릴리즈/단위 수락을 차단한다.

### C04/D: 인덱스 세대 분리 후보 구현 (2026-09-07)

- 엔진의 새 인덱스 UUID를 이름/스키마 해시에서 재사용하지 않고 UUID v4로 발급한다.
  이미 lockfile에 있는 `uuid=1.8.0`을 명시 의존성으로 추가했으며 버전 갱신은 없다.
  `create_index_from_schema_with_uuid`는 저장 상태 복구 시 기존 식별자를 보존하는
  경로다. 스키마 해시는 그대로 별도 검증 값으로 유지한다.
- 단일/샤드별 로그 저장은 기존 manifest의 UUID와 shard ID가 현재 세대에 맞을 때만
  append 경로를 사용한다. 세대가 다르면 새 세대의 문서로 로그를 교체한다.
  저장/삭제는 per-index 저장 전용 잠금을 함께 사용하고, 잠금 획득 뒤에도
  동일한 인덱스 객체인지 확인한다. 다른 세대로 바뀐 작업은 거부한다. 이 변경이
  다중 프로세스의 동일 data path 공유나 모든 저장 장애의 원자성을 보장하지는 않는다.
- 노드는 새 인덱스의 UUID를 settings 및 `_steelsearch_index_uuid`에 기록한다.
  명시적 생성, 쓰기의 자동 생성, data stream backing index, snapshot 새 대상 생성에
  연결했다. 성공한 새 생성에서 이전 삭제 이력을 제거하고 per-index sequence를 0으로
  시작한다. 실패한 중복 생성은 기존 세대를 변경하지 않는다. 공유 상태 복구는 저장된
  UUID를 native 엔진에 전달한다. 내부 식별자가 없는 이전 형식은 기존 복구 경로를
  유지한다. 이전 버전에서 이미 혼합된 인덱스 세대를 복원했다는 주장은 아니다.
- GET fallback/로그 병합은 식별자가 있는 인덱스에 대해 다른 UUID 또는 shard ID의
  로그를 사용하지 않는다. 다른 세대의 유효한 manifest에 속한 오래된 로그는 현재
  인덱스의 복구 오류 검사에서도 분리한다. malformed manifest/부분 저장 및 동시
  REST 생성·삭제·쓰기의 원자성은 추가 검증이 남아 있다.
- 신규 engine 회귀 검사는 동일 이름/스키마의 재생성에서 UUID 변경, 새 sequence 0,
  기존 단일/샤드별 경로의 로그 교체, 이전 세대 객체 거부, 복구 시 UUID 보존을 검사한다.
  신규 node 검사는 1/3샤드 및 명시/자동 생성의 재시작, routing, 중복 생성 실패,
  정확한 검색 ID/source를 확인한다. 기존 settings 검사는 고정된 가짜 UUID가 아니라
  실제 native manifest UUID와 동일한 값을 읽는지 검사하도록 수정했다.
- 전체 테스트 전 타입 검사는 종료 0, 35.87초다.
  `target/core-replacement-c05/index-generation-tests-check.log` SHA-256:
  `bd12ffe43dc9ea0533cf7d1233c62926c07cf408a34028ca26f53564262c2b78`.
  첫 전체 engine/node 빌드는 아래 잠금 충돌 검토로 중단했으며 통과 실적이 아니다.
- 최초 후보는 저장/삭제에 refresh 잠금을 재사용했으나 기존
  `waiting_refresh_rejects_a_recreated_index_with_the_same_name` 검사는 refresh 잠금을
  잡은 상태의 삭제/재생성을 요구한다. 재사용하면 이 흐름이 교착하므로 빌드 중
  발견한 뒤 의도적으로 중단했다(종료 130). 원래 로그
  `index-generation-engine-node-full.log` SHA-256:
  `4ddb7d7a8107460c1a19f6e23ba78d0d858926399270a100eee9652a8672fca5`.
  테스트 기대를 삭제하지 않고 저장 전용 잠금으로 분리했다. 추가 engine 검사는
  저장 중 삭제가 기다리는 동안 refresh는 진행할 수 있고 이전 세대 객체는 거부되는지
  확인한다. cluster state의 고정 index UUID도 실제 메타데이터 UUID로 바꾸고 node
  재생성 검사에서 settings/native/cluster routing UUID의 일치를 확인한다.
- 분리 후 타입 검사는 종료 0, 34.53초다. 마지막 engine 잠금 회귀 검사는 이 검사
  뒤 추가했으므로 전체 테스트로 확인해야 한다. 로그 SHA-256:
  `d572de1d102eac53b806cc6f6c58d05712148a2bc0459f08bd1076f56ef8cf2e`.
  `index-generation-engine-node-final.log`에서 전체 lib 테스트를 실행했다. 종료 0,
  빌드 14분 37초, **engine 838/838, node 605/605**, ignored/filtered 0이다.
  실제 테스트는 2.32초/1.32초이며 기존 refresh 재생성 검사와 신규 3개 검사도 통과했다.
  로그 SHA-256 `74f4492a8486158ce421feabada4ce0cd85ebe55a7243ffdc9ce4c8ac5e30eaa`.
  입력 engine SHA-256 `29c772d607f50db241179febe00cc4d93e63a32ae6a0a106bc50c5875a6fde9d`,
  node `ecf3e33f5dba725e2140ce172e4269f71c94cf7cbccdd83147a28dcee726913e`.
- HTTP 진단을 UUID 변화/복구 보존, 정확한 검색 문서 집합, 빈 인덱스 재생성 후
  재시작과 첫 sequence까지 18개 검사로 확장했다. 이전 10개 검사 스크립트는
  `index_recreation_probe_initial.py`에 원래 해시로 보존했다. 확장 진단 SHA-256:
  `174646f8866677c8b756d103d8212481d4d91251b4ffb608cc2c8629e321dec7`.
  이전 바이너리 `aebc0503...`의 `index-generation-http-before-expanded/result.json`은
  **11/18 통과, 7/18 실패**, 종료 1이다. UUID 미변경, 이전 문서 재등장, 새 문서 소실,
  잘못된 검색 문서 및 빈 인덱스의 첫 sequence 2(기대 0)를 재현했다.
  결과 SHA-256 `43876b38436a2b1cf206e7110846b966d5824c0520111379f2e6827315aacfaf`.
- 새 바이너리의 기능/HTTP 및 전체 반복 성능 검증은 아직 없다. 구현 후보 단계이며
  C04/D 수락이나 ledger 제외를 선언하지 않는다. 각 구현 단위의 전체 비플러그인
  벤치마크 및 최초 v0.6.0 누적 5% 예산은 그대로 적용한다.

### C04/D: 인덱스 세대의 지연 상태 정리 보강

- 위 engine/node 소스의 동시 refresh 통합 검사는
  `index-generation-integration.log`에서 **7/7 통과**, 종료 0, ignored/filtered 0,
  4.35초다. 로그 SHA-256:
  `a2082b6d66f929d2ebe1d86815b604d2e3316f069c6ab598b8f72f9d0a801c8b`.
- 이후 `refresh=false` 경로를 검토해 삭제 이력 외에도 이름별 pending delete,
  unrefreshed keys, array-field 보조 상태, dirty shard 및 sequence 상태의 세대 정리가
  필요함을 확인했다. 성공한 인덱스 삭제/새 생성에서 이를 함께 정리하도록 보강했다.
  새 데이터의 쓰기·검색 경로에 일괄 초기화를 넣은 것은 아니다. 중복 생성 실패는
  기존 상태를 유지한다. 동시 REST lifecycle 원자성의 전체 보장은 별도 미완료다.
- node 재생성 검사를 1/3샤드 x 명시/자동 생성 x 삭제 refresh true/false의 8조합으로
  확장했다. 이전 문서와 새 문서의 routing도 다르게 하며, 이전 큐가 없음을 확인하고
  새 인덱스의 명시적 refresh 전후 및 재시작 후 정확한 문서를 확인한다.
  node SHA-256 `405e89537899836145bfc892fef35ec81f0ba4cc9e72df47d33ac16023f5d22b`.
  `index-generation-queues-engine-node-full.log`에서 전체 lib 테스트를 다시 실행했다.
  종료 0, 빌드 5분 43초, **engine 838/838, node 605/605**, ignored/filtered 0이다.
  실제 실행 시간 2.33초/1.42초, 로그 SHA-256:
  `28a13c3630eafa4712b5bcd4a5494c43bb43416ad4b7533f8fd94f69638ce254`.
  engine 소스는 위 `29c772d6...`에서 변경하지 않았다. 동시 refresh 통합 검사도
  `index-generation-queues-integration.log`에서 **7/7 통과**, 종료 0, ignored/filtered 0,
  4.20초다. 로그 SHA-256:
  `4b9f0ce7868c0371a9eeab664b9448ce60b7e7256a84d49e0c527c1495b540bb`.
- HTTP 진단에도 다른 routing의 지연 삭제 후 자동 재생성/refresh를 추가했다.
  이전 18개 검사 스크립트는 `index_recreation_probe_expanded.py`에 보존했다.
  최종 22개 검사 스크립트 SHA-256:
  `893410659aedfba689e180270f39a11d70813a2abcffb81d3cdd21d8577a0098`.
  이전 바이너리 `aebc0503...`의 `index-generation-http-before-queues/result.json`은
  **13/22 통과, 9/22 실패**, 종료 1, setup 오류 0이다. 기존 실패에 더해 자동 재생성의
  sequence 2(기대 0)와 UUID 미변경을 확인했다. 이 실행은 기능 진단이며 빌드와
  동시에 실행했으므로 성능 측정으로 사용하지 않는다. 결과 SHA-256:
  `d915c366c39fa3cbdeaf9ee34c3ce5adb23a7220d8f5b10fea94fdbcefc961fd`.
- standalone release 빌드는 종료 0, 4분 35초다. 최신 실행 파일 SHA-256은
  `64e9521d81599dba4110947430786518ee693e8e86102d6d05dc4f40a156cf14`다.
  `index-generation-http-after/result.json`에서 재생성 HTTP **22/22 통과**,
  `index-generation-watermark-http-after/result.json`에서 기존 복구 HTTP
  **48/48 통과**를 확인했다. 모두 실행 중 바이너리와 전후 해시를 확인했으며
  setup 오류 없이 종료 0이다. 결과 SHA-256은 각각
  `f10a4480430d38c06a1f861362b7948924ca2f788f75be61e953a5f4da568721`,
  `c53fea04dd602117df1f84e24a7261b9050b1b2c3cd7ac90e2602cfdce57e142`다.
- `live-index-generation`의 OpenSearch 3.7.0-SNAPSHOT 기능 비교에서 코어
  **1180/1180**, settings **84/84**, routing **118/118** 통과다.
  count/alias/PIT 후보 **42/57**, 참조 **57/57**이며 기존 15개 실패는 남았다.
  nested-bool-final/canonical은 각각 **130/160**으로 기존 30개 실패가 남았다.
  전체 실행 종료 1이며 바이너리/fixture 변경은 없다. 실행 결과 SHA-256:
  `705663856742b8e9e8d268791ff48be3bdcde25d37c3a44c78bc3c1c00b53238`;
  코어 보고서 SHA-256:
  `fd1a85352e36f2699207661ef86a8ebe763b0129f58013f7ced1cec72e264e90`.
- 최신 후보의 전체 반복 성능 검증을 `index-generation-repeated-full`에서 시작했다.
  baseline/candidate/OpenSearch/OpenSearch/candidate/baseline의 사전 고정 순서로
  단일/3노드 총 12개 시나리오를 실행한다. 기능 참조 3.7.0-SNAPSHOT과 성능 참조
  2.19를 구별한다. 결과 확정 전 C04/D 수락, 누적 5% 충족 또는 ledger 제외를
  선언하지 않는다. 큰 구현 단위 40개 중 최종 수락 완료는 아직 0개다.

### C04/D: 최신 인덱스 세대 후보의 전체 반복 성능 결과

- `target/core-replacement-c05/index-generation-repeated-full/result.json`:
  **수치 게이트 실패**, 종료 1. 1097.7474초, 사전 고정한 6회/12개 시나리오를
  전부 실행했다. 하위 실행은 모두 종료 0, 모든 시나리오의 요청 오류 0건이다.
  `execution_inputs_verified=true`, infrastructure error 없음이다.
  후보 `64e9521d...`, engine `29c772d6...`, node `405e8953...`는 변경하지 않았다.
  결과 SHA-256 `b2c3be0032f0704fadc836c8a3eeca71e4eaac2cd1c98df5e67ed5671262e61c`;
  사전 계획 SHA-256 `c41da2f44ea58d9e8293654200a99f345c3c4e31c44acea97e4059e8d641171d`.

| 후보 반복 | 최초 v0.6.0 대비 | 같은 실행의 v0.6.0 대비 | v0.6.0 재측정 자체의 기준 대비 |
| --- | --- | --- | --- |
| 01 | 43/44 통과 | 43/44 통과 | 43/44 통과 |
| 04 | 42/44 통과 | 43/44 통과 | 42/44 통과 |

아래 증가율은 지연시간 악화다. 반올림 전 값으로 5%를 판정했으며 반복을 평균내거나
좋은 반복만 선택하지 않았다.

| 비교 | 반복 | 기준 초과 지표 | 지연 증가 |
| --- | --- | --- | --- |
| 최초 v0.6.0 대비 후보 | 01 | single/refresh/p99 | +7.437634% |
| 최초 v0.6.0 대비 후보 | 04 | three/lexical/p99 | +12.693366% |
| 최초 v0.6.0 대비 후보 | 04 | three/refresh/mean | +5.538146% |
| 같은 실행 v0.6.0 대비 후보 | 01 | single/lexical/p99 | +5.518253% |
| 같은 실행 v0.6.0 대비 후보 | 04 | three/lexical/p99 | +9.482302% |
| 최초 대비 v0.6.0 재측정 | 00 | single/refresh/p99 | +5.039310% |
| 최초 대비 v0.6.0 재측정 | 05 | three/ranking/p99 | +5.779297% |
| 최초 대비 v0.6.0 재측정 | 05 | three/nested/p99 | +10.188634% |

| 후보 반복 / 토폴로지 | 후보 ops/s | 최초 v0.6.0 대비 처리량 변화 | 짝지은 OpenSearch 2.19 ops/s | 처리량 배율 |
| --- | --- | --- | --- | --- |
| 01 / single | 751.6141 | +1.1579% | 283.9254 | 2.6472x |
| 01 / three | 925.7080 | -0.6079% | 108.2019 | 8.5554x |
| 04 / single | 746.6896 | +0.4951% | 284.5123 | 2.6245x |
| 04 / three | 914.0598 | -1.8586% | 109.3213 | 8.3612x |

- 처리량 비교는 이 개발용 혼합 부하 프로파일에 한정된다. 운영 내구성/독립 분산
  실행의 동등성이나 OpenSearch 대체 가능성을 입증하지 않는다. 수치 통과조차 전체
  구현 수락을 뜻하지 않는 실행기의 증거 한계도 유지한다.
- 기준 바이너리 자체의 변동은 관찰 사실이지 후보 실패를 면제하는 근거가 아니다.
  이전 후보와 실패 항목이 달라 단일 기능의 원인 기여 및 최적화 불가를 입증하지
  못했다. 따라서 이번 수정은 기능 검증 통과/성능 수락 보류이며 ledger 제외는 없다.
- 후속 성능 진단은 실제 실행 설정을 먼저 확인하고, 고정 데이터/부하의 별도 진단에서
  lexical 실행과 refresh의 지연 쓰기 재생/가시성 변경 구간을 분리해 측정한다.
  코드상 matrix의 per-write persist=0, shard defer=1 조합에서는 refresh의 shared
  state 및 shard 영속화가 생략되므로 추가 manifest 검사를 바로 원인으로 단정하지
  않는다. 진단은 전체 벤치마크를 대체하지 않으며 최적화 후에는 전체 검증을 다시 한다.
- 다음 기능 수정의 남은 범위는 인덱스별 alias 필터/라우팅을 한 메타데이터 스냅샷에서
  해석하고 native/fallback 검색, count, global 집계와 PIT/scroll로 전달하는 것이다.
  PIT는 생성 시 필터를 보존해야 하며 alias 변경으로 기존 PIT의 결과가 바뀌면 안 된다.
  검색 query만 감싸거나 결과 hits를 사후 필터링하는 방식으로 완료하지 않는다.
- 실행 종료 후 benchmark SteelSearch/Java 프로세스가 없고 임시 비교 컨테이너가
  정리됐음을 확인했다. 기존 사용자 컨테이너는 변경하지 않았다. 릴리즈/승격은 보류다.

### G03/P03: CPU 진단의 서버 식별 수정과 세대 변경 대조

- 직전 전체 성능 검증 완료는 진행으로 분류했다. 이후 동일 소스/바이너리를 대상으로
  인덱스 세대 분리 전 `aebc0503...`과 후 `64e9521d...`를 비교하는 3노드 mixed CPU
  진단을 시작했다. 최초 v0.6.0과의 비교가 아니며 전체 5% 게이트를 대체하지 않는다.
- 최초 `index-generation-cpu-plan.json`의 before-1은 부하 전에 중단됐다.
  matrix의 `steelsearch_resource_pids`가 basename `steelsearch`만 찾고 실패하면
  launcher까지 반환하여, 다른 파일명으로 보관한 이전 바이너리에서 런타임 노드 수
  검증이 실패했다. 프로세스 종료를 확인했고 측정 결과를 재사용하지 않았다.
  최초 계획 SHA-256 `184b40a14256ff140de1919a526472b9d92f04f0935091295e8e3056b020397e`;
  `index-generation-cpu-before-1/matrix.log` SHA-256:
  `7b674ac2ae8805395688d6a6181ed05d0fc672cea82b93b4f5fe2400e537377b`.
- matrix에 선택 바이너리 경로를 명시적으로 전달하고, 소유 프로세스 트리에서 해당
  경로만 수집하도록 수정했다. launcher 대체 집계는 제거했다. 다른 경로의 같은
  basename, 빈 cmdline, 중복 PID, 선택 바이너리 누락 및 Docker 분기를 검사했다.
  terms 진단 호출부도 선택 바이너리를 전달한다. 실제 `/proc/PID/exe` 해시,
  시작 시각, 노드 수 및 전후 동일성 검사는 약화하지 않았다.
  matrix SHA-256 `8d39d88480ac675624d8924b305d0ee4df4699c13a36ff6b95223863c822933b`;
  terms 진단 `4c28902604ab62684baa1682d61fcb0cc3092e0e47a0483984c205a0d5763390`;
  failure diagnostics 검사 `ba4d0b8980d88c80230f32f358bbf59e1691a07921855787711d4e2b258836b1`.
- failure diagnostics, CPU, terms, repeated gate, runtime evidence, numeric budget,
  reports, cgroup evidence의 관련 unittest **68/68 통과**. 그중 gate 테스트의
  임시 디렉터리 종료 1/2는 의도한 실패 판정 회귀 검사이며 실제 벤치마크가 아니다.
- 수정한 도구의 새 계획 `index-generation-cpu-path-fixed-plan.json`에 실행 전
  **before-1 -> candidate-1 -> candidate-2 -> before-2**를 고정했다.
  계획 SHA-256 `0c29f1d5a71b0b639a7b08462d85063176ec9f304c3124b016f7c92b7a04b1a9`.
  CPU runner는 `ec44f048...` 그대로다. 45초 mixed 부하 중 20초/49Hz CPU 표본이며
  각 실행에 서버 3개와 부하 생성기 1개를 확인했다. 네 실행 모두 profiler/matrix
  종료 0, 요청 오류 0, 실제 바이너리 해시 유지다. 빌드/다른 부하와 겹치지 않았다.

| 진단 반복 | 처리량 ops/s | lexical mean ms | lexical p99 ms | refresh mean ms | refresh p99 ms |
| --- | --- | --- | --- | --- | --- |
| before-1 | 940.058895 | 3.575752 | 10.113192 | 8.582423 | 21.547995 |
| candidate-1 | 896.496734 | 3.756521 | 12.050085 | 9.272272 | 23.400093 |
| candidate-2 | 936.942062 | 3.571510 | 10.074238 | 8.627077 | 21.925373 |
| before-2 | 893.077324 | 3.676578 | 11.132427 | 9.560876 | 26.164499 |

- 각 `index-generation-cpu-path-fixed-{label}`의 `diagnostic.json` SHA-256:
  before-1 `d3b283a3b8364717c91c602eb6975cdcf0e909a6970e2b909f8b5f3ca4c0d5f8`;
  candidate-1 `ac1f41eae3161a8b24cf92c53f280681b512b8571a580cfd10ef32b6cbf5e0a9`;
  candidate-2 `aa91d43d5a40def8e00023ffda3fd5b979c592188a50c25587c660b5fc2d7b3d`;
  before-2 `c87bfed7a86b6eeb03eaafc4226a7202d7c621b881696eac2a0d5abf285446c0`.
- 서버 PID만 분리한 `perf-self.txt`/`perf-children.txt`를 네 디렉터리에 보존했다.
  memcmp self 비중은 이전 4.51%/2.84%, 후보 5.29%/5.23%다. 후보 두 번째 표본에서
  1.98 percentage points는 단순 bucket 집계, 1.34는 source 필드 조회를 거치는
  document matching/scoring 호출 경로다. 이는 서버 CPU 표본 비중이지 lexical
  지연 증가율 또는 세대 분리의 원인 기여율이 아니다. 유한한 표본과 일부 불완전한
  unwind 때문에 표본에 없는 경로가 비용 0이라고 결론내리지 않는다.
- 이번 대조에서 최신 후보의 악화가 두 짝 모두에서 재현되지는 않았다. 이를 잡음으로
  면제하거나 빠른 반복만 선택하지 않는다. 단일 변경의 5% 이상 기여 및 최적화 불가가
  입증되지 않아 ledger 제외 없음, 기존 전체 성능 실패와 0/40 최종 수락 상태 유지다.
- 다음 분석은 scoring의 source 필드 반복 조회 및 검색/집계 공유 경합이다. 이미
  기각한 집계 순회 전치 최적화를 되살리지 않는다. 도구 수정은 실제 3노드 진단으로
  확인했지만 수정된 matrix의 전체 12개 검증은 아직 없으므로 G03 완료로 표시하지
  않는다. 제품 코드 최적화 후에는 최신 도구로 전체 기능/성능 검증을 실행해야 한다.

### C05: bool 최소 일치 조건의 scoring/후보 축소 정합성

- 직전 단계는 서버 식별 도구 수정 및 CPU 대조 증거 확보로 진행에 해당한다.
  scoring 비용을 읽는 과정에서 `should` 임시 벡터 제거와 filter-first 최적화의
  기존 기각 기록을 `release-diagnostic-2026-09-06.md`에서 확인했다. 같은 실험을
  다시 도입하지 않았다.
- 별도 정합성 결함을 확인했다. 공통 source predicate는 should 개수보다 큰
  `minimum_should_match`를 불일치로 처리하지만, scoring과 후보 축소 두 경로는
  최소 일치 요구를 should 개수로 낮추고 있었다. `score_bool_query_with_bm25_context`,
  일반 bool 후보 집합 계산, candidate source predicate의 상한 제한을 제거했다.
  should가 없는 must/filter의 양수 최소 요구도 일반 후보 집합에서 빈 결과로 만든다.
  should의 평가/점수 합산/오류 전파 순서는 바꾸지 않았다. 빈 bool의 match-all
  예외는 기존 effective minimum 계산을 그대로 사용한다.
- 신규 `bool_scoring_rejects_unattainable_should_minimum`은 10개 입력에서 공통
  predicate, candidate predicate/ID, scoring을 기대값과 대조한다. 초과 최소 요구,
  must/filter/must_not만 있는 bool, 일부 should 불일치, 달성 가능한 요구, 빈 bool,
  명시적 0을 포함한다. 반대 조건의 scoring 및 후보 문서 누락 금지도 검사한다.
  보수적인 후보 축소가 여분 문서를 남기는 것은 최종 일치 판정과 구별한다.
- 실행 이력은 모두 보존했다. scoring만 수정한 첫 실행과 candidate 경로를 추가한
  두 번째 실행은 각각 **838/839**, 동일 hybrid 테스트 1개 실패였다.
  이 테스트 입력에는 should 1개/minimum 2 및 should 0개/minimum 1의 불가능
  조건이 중첩돼 있었다. 기존 기대 문서 `c`를 무조건 통과시키지 않고, 원래 입력과
  첫 조건만 해소한 입력 모두 결과 없음, 두 조건을 해소한 입력은 기존 `c`를
  반환하도록 음성/양성 대조를 추가했다. 기존 Query phase 검사도 유지했다.
- 세 번째 실행은 **837/839**였다. 두 번째 불가능 조건이 양성 대조에 남아 있었고,
  신규 후보 검사가 빈 bool 제외의 보수적 상위집합까지 정확 집합으로 요구했다.
  양성 대조의 두 조건을 명시적으로 확인/수정하고, 후보 검사는 false negative
  방지와 최종 scoring의 정확 일치를 구분했다. 기대 문서 자체를 제거하지 않았다.
- 최종 `bool-scoring-minimum-boundaries-engine-tests.log`:
  **engine 839/839 통과**, ignored/filtered 0, 종료 0. debug test 빌드 1분 33초,
  테스트 실행 8.04초다. release 성능 결과가 아니다. 최종 engine 소스 SHA-256:
  `67ce7ca21ca902d1ded2087b34569cfa7573f773c0e8de669ba59f11ace8f8d3`.
  최종 로그 SHA-256 `c2640ac10f8beb6b67f0d456f713c7e3efddffec06afe1bf49cacc265e98f085`.
  중간 실패 로그 SHA-256은 순서대로
  `52d93546a702d164847cd91ec6aa994c06e428755443d948a337173053056b10`,
  `30aa8c76a4e85eb723533b3a1f8d070fc006af63ba62bf13e6a799a07ed7bdbf`,
  `6fa48afacc5673b16b094799aafdaba35b99946fdb74c1d64407200b8b253636`다.
- 변경 전후 바이너리 비교/전체 성능 검증은 아직 없다. `target/release/steelsearch`
  `64e9521d...`는 여전히 이전 engine 소스의 실행 파일이므로 새 수정의 HTTP/성능
  근거로 사용하지 않는다. node 전체, release 재빌드, live
  참조 및 전체 12개 시나리오 검증을 거친 후에만 이 수정의 수락을 판단한다.
  kNN-seeded 후보 fast path 등 별도 후보 경로는 이번 10개 코어 검사만으로 전체
  보장을 선언하지 않는다. 플러그인은 지원 범위 밖이며 기존 관련 테스트도 숨기지 않는다.
  C05 완료/릴리즈/ledger 제외 없음, 최초 v0.6.0 누적 5% 기준 유지다.
- 동일 최종 소스의 동시 refresh 통합 검사는
  `bool-scoring-minimum-integration.log`에서 **7/7 통과**, 종료 0,
  ignored/filtered 0, debug 빌드 30.09초/실행 16.03초다. 로그 SHA-256:
  `1861d70732c07dc6205eef5a5fa336613b1e91b781b234f3c280a5120d02e010`.

### C05: bool 최소 일치 수정의 node 검증 및 HTTP 준비

- 직전 단계는 제품 scoring/후보 조건 수정과 engine 839/839, 통합 7/7 증거
  확보로 진행에 해당한다. 이어서 소스 해시 engine `67ce7ca2...`, node
  `405e8953...`가 유지됐음을 확인했다.
- `bool-scoring-minimum-node-tests.log`에서 **node 605/605 통과**, 종료 0,
  ignored/filtered 0이다. debug 빌드 2분 41초/테스트 실행 4.50초.
  로그 SHA-256 `5de8b035332ea09dbe78fa8db12d81aa7f4b75c23e6a86e191c099a6f5d4177a`.
- 수정 전 실행 파일은 `steelsearch-before-bool-minimum`에 보존했다.
  새 standalone release 프로파일 빌드를 시작했으며, 배포 릴리즈 발행이 아니다.
- `generate-bool-minimum-fixture.py`로 추가 HTTP fixture
  `bool-minimum-compat.json`을 생성했다. 10개 경계 입력 x 양성/부정 x 1/3샤드 x
  hits/scores/total/count/value_count 집계의 **200개 비교 항목**이다.
  구조 및 중복 이름 검사를 통과했지만 아직 live 실행 증거는 아니다.
  fixture SHA-256 `aa95be80587b828e84d95dd3bf8bd0def1684ee1295cd9d0ee1cb393aa83c740`.
- 기존 `run-live.py`의 PID 호출을 새 matrix API에 맞춰 선택 바이너리를 전달하도록
  수정하고 `--additional-fixture`를 추가했다. 기존 nested 2종 및 전체 코어 fixture를
  대체하지 않고 앞에 추가하며, fixture 간 인덱스 정리/해시 보존도 그대로 적용한다.
  runner SHA-256 `cd8d9d198e46ba068ddd844ab04429ba25122218a8d240e33b93c032cef829c0`.
  두 스크립트의 py_compile 통과. 새 바이너리의 live/전체 성능 결과는 아직 없다.

### C05: 실제 HTTP 비교의 순수 부정/빈 bool 예외 보강

- 위 `67ce7ca2...` 소스의 standalone release 빌드는 종료 0, 4분 49초다.
  실행 파일 SHA-256 `4a81e1bec14f6a815b5c6e1560f087f054b7fda39aec96fed6a99297728e08b4`;
  `bool-scoring-minimum-release-build.log` SHA-256
  `c7ffd90e4ca08d4203b0ed86cda3e9ec79b39e1b7b67614d6e0bf3e610cd2b0b`.
- `live-bool-minimum`에서 추가 200개와 기존 nested 2종, 코어 및 settings/routing/
  count probe를 실행했다. 실제 바이너리와 fixture의 전후 해시 유지, 실행 종료 1.
  **코어 1180/1180**, settings **84/84**, routing **118/118** 통과.
  기존 count/alias/PIT 후보 **42/57**, 참조 **57/57**, nested 각각 **130/160**은
  기존 실패를 유지했다. 새 bool fixture는 **194/200**, skipped 0이었다.
  execution SHA-256 `7daf290040e1b6124d97bc1dcb6c18a23ac5a7c21022bc16ff4dfed25f543b5e`;
  bool report `a13873837c5d8da28394b4f425ce3c25f7eb9fe56286a704b3f8df1a47e75854`;
  core report `87a94cc2a9b46321be450bffd0a10fc4c9f8bd181f5241d480ca9524dc668926`.
- 새 6개 실패는 1/3샤드 각각 순수 부정 bool의 hits/scores 2개 및 빈 bool의 scores
  1개였다. `must_not:[match_none], minimum_should_match:1`에서 참조는 total 4와
  실제 4문서/score 0, 후보는 total 4지만 hits []였다. 빈 bool은 문서 집합이
  일치하나 참조 score 1, 후보 score 0이었다. 단위 검사의 순수 부정 기대값도
  참조 계약에 비해 잘못됐음을 확인했다. 통과율을 높이기 위해 fixture를 바꾸지 않았다.
- 로컬 OpenSearch `BoolQueryBuilder.doToQuery`는 완전히 빈 bool을 즉시
  MatchAllDocsQuery로 만든다. `Queries.fixNegativeQueryIfNeeded`는 순수 부정
  BooleanQuery의 clause를 복사하고 match-all FILTER를 추가하지만 이전 최소
  should 요구는 복사하지 않는다. 실제 HTTP와 이 소스를 근거로 공통 effective
  minimum 계산에서 must/filter/should가 모두 없으면 0을 반환하도록 보강했다.
  scoring에서는 완전히 빈 bool만 점수 1을 반환한다. 비어 있지 않은 filter-only/
  pure-negative의 점수 0과 일반적인 초과 최소 요구의 불일치는 유지한다.
- 기존 10개 단위 입력의 참조 기대값을 바로잡고, 일치 여부뿐 아니라 기대 점수
  None/0/1/2의 비트값도 검사하도록 확장했다. 최종 engine 소스 SHA-256:
  `ae07858d9bb89a44549ec87730719160623b0fd48683e308c5e02012a74a1e14`.
  `bool-minimum-rewrite-engine-node-tests.log`에서 **engine 839/839, node 605/605**
  통과, 종료 0, ignored/filtered 0이다. debug 빌드 1분 43초, 실행 8.19초/4.39초.
  로그 SHA-256 `bc21904ce288c39d8e6cfad428e047374534f7a52389256b8795c5456e411d2d`.
  `bool-minimum-rewrite-integration.log`도 **7/7 통과**, 종료 0, 실행 15.88초이며
  SHA-256 `042b212a866c87350b0691c38c078b98283add671e58b5c4c864537d10f17cbc`다.
- **최신 소스의 release 재빌드/HTTP 재비교/전체 반복 성능은 아직 남아 있다.**
  현재 `target/release/steelsearch`의 `4a81e1be...`는 위 예외 보강 전 바이너리다.
  다음 실행은 최신 바이너리로 동일 200개 fixture와 기존 live 비교를 재실행하고,
  전체 12개 시나리오 및 고정 최초 v0.6.0 대비 44개 지표를 검증해야 한다.
  기존 +12.693366% 성능 실패는 이전 `64e9521d...` 후보의 결과이며 새 후보의
  수치로 옮기지 않는다. 단위 수락/릴리즈/ledger 제외 없이 전체 목표를 유지한다.

### C05: bool 예외 보강 후 실제 기능 재검증

- 최신 engine `ae07858d...`, node `405e8953...`를 유지한 standalone release
  빌드가 종료 0, 4분 45초에 완료됐다. 실행 파일 SHA-256:
  `a917c150332480df2e30145fd4701868875c178055591b8aad8e6ecb52d3f379`.
  `bool-minimum-rewrite-release-build.log` SHA-256:
  `6b83268c280729045c8c598d16515ed2868a684ccd1a6b0fe69dd85f66941eec`.
- `live-bool-minimum-rewrite`에서 동일 fixture로 실제 OpenSearch 3.7.0-SNAPSHOT과
  재비교했다. **bool 경계 200/200**, **코어 1180/1180** 통과, skipped 0이다.
  앞선 6개 실제 HTTP 차이를 해소했다. settings/routing probe도 통과했다.
  후보 count/alias/PIT **42/57**, 참조 **57/57**, nested 두 fixture 각각
  **130/160**의 기존 실패는 남았다. 전체 runner는 종료 1이다.
  setup 실패 없음, binary/fixtures unchanged true이며 실제 실행 파일 해시도 확인했다.
  execution SHA-256 `243c1f84c82ffc2edce056c9a49d53ac98c5b9d9912d7f1de5d940f9ade286ec`;
  bool report `6484c2164817b196d198c5aca3eccb48935291182f738f30a9b1ed9fe0ebdeeb`;
  core report `1e9a708df6e9812333fb36cc08b701fbee48caa5cbb431f5cf22f8b2849cae49`.
- 소유 기능 비교 프로세스가 종료된 후 `bool-minimum-rewrite-repeated-full`에서
  baseline/candidate/OpenSearch/OpenSearch/candidate/baseline의 고정 순서로
  단일/3노드 총 12개 시나리오 성능 검증을 시작했다. 측정 중 빌드/기능 부하를
  겹치지 않는다. 결과 확정 전 누적 5% 충족이나 C05 수락을 선언하지 않는다.

### C05/P03: bool 예외 보강 후보의 전체 반복 성능 결과

- `bool-minimum-rewrite-repeated-full`은 사전 계획의 6회/12개 시나리오를 모두
  실행했다. **수치 게이트 실패**, 최종 종료 1. 총 1099.5249초, 하위 실행 모두
  종료 0, 모든 시나리오 요청 오류 0이다. infrastructure error 없음,
  `execution_inputs_verified=true`. 소스 engine `ae07858d...`, node `405e8953...`,
  실행 파일 `a917c150...`를 전후 확인했다. CPU profiler/빌드/기능 부하를 겹치지 않았다.
  result SHA-256 `e469a6950e690d2bad7563f2391573456e04c6b8a998f7ed206028c5cb742c25`;
  사전 plan `4229a25fcce7f6d1f50aa94b7a04c0a7fa082b839e0dcf05f4e4456e551d9e5b`.

| 후보 반복 | 최초 v0.6.0 대비 | 같은 실행 v0.6.0 대비 | v0.6.0 재측정 자체의 기준 대비 |
| --- | --- | --- | --- |
| 01 | 42/44 통과 | 42/44 통과 | 44/44 통과 |
| 04 | 41/44 통과 | 40/44 통과 | 43/44 통과 |

아래 값은 지연시간 증가율이며 반올림 전 값으로 판정했다.

| 비교 | 반복 | 초과 지표 | 지연 증가 |
| --- | --- | --- | --- |
| 최초 v0.6.0 대비 후보 | 01 | single/refresh/p99 | +6.607269% |
| 최초 v0.6.0 대비 후보 | 01 | three/ranking/p99 | +5.098435% |
| 최초 v0.6.0 대비 후보 | 04 | single/write/p95 | +5.268775% |
| 최초 v0.6.0 대비 후보 | 04 | single/sort_filter/p95 | +5.703254% |
| 최초 v0.6.0 대비 후보 | 04 | single/refresh/p99 | +5.072660% |
| 같은 실행 v0.6.0 대비 후보 | 01 | single/refresh/p99 | +7.927079% |
| 같은 실행 v0.6.0 대비 후보 | 01 | three/nested/p99 | +5.966254% |
| 같은 실행 v0.6.0 대비 후보 | 04 | single/ranking/p99 | +6.434672% |
| 같은 실행 v0.6.0 대비 후보 | 04 | single/sort_filter/p95 | +5.755832% |
| 같은 실행 v0.6.0 대비 후보 | 04 | single/nested/p99 | +6.590298% |
| 같은 실행 v0.6.0 대비 후보 | 04 | single/refresh/mean | +5.285118% |
| 최초 대비 v0.6.0 재측정 | 05 | three/ranking/p99 | +5.604170% |

| 후보 반복 / 토폴로지 | 후보 ops/s | 최초 v0.6.0 대비 처리량 변화 | 짝지은 OpenSearch 2.19 ops/s | 처리량 배율 |
| --- | --- | --- | --- | --- |
| 01 / single | 754.1686 | +1.5017% | 291.2693 | 2.5892x |
| 01 / three | 922.5152 | -0.9507% | 115.4050 | 7.9937x |
| 04 / single | 739.8870 | -0.4205% | 282.6181 | 2.6180x |
| 04 / three | 921.7732 | -1.0304% | 114.4122 | 8.0566x |

- 위 처리량은 개발용 혼합 부하 프로파일의 결과다. 운영 내구성/분산 동등성을
  증명하지 않는다. 반복 평균이나 지표 간 상쇄로 실패를 지우지 않는다.
  이전 `64e9521d...` 후보의 최대 +12.693366%와 이번 +6.607269%를 비교해
  bool 수정이 성능을 개선했다고 단정하지 않는다. 단일 변경의 원인 기여 및
  최적화 불가를 아직 입증하지 못해 ledger 제외는 없다. 정상 수락은 계속 차단한다.
- 최신 matrix의 경로 기반 PID 탐색은 이번 전체 12개 시나리오에서도 런타임
  식별/입력 동일성 검증을 통과했다. 이는 G03 전체 요구를 완료했다는 뜻이 아니다.
  종료 후 소유 SteelSearch/Java/컴파일 프로세스와 비교 컨테이너가 정리됐음을
  확인했다. 기존 사용자 컨테이너는 변경하지 않았다.
- 후속 집계 작업 검토에서 `TermsAggregation`의 order 부재 외에도
  `bucket_sort_key`가 숫자 키를 `n:{value}` 문자열로 바꾸는 것을 확인했다.
  merge/plugin terms/bucket-sort 등 공유 정렬 경로에 영향을 줄 수 있어 `_key`
  파서 수용만으로 수락하지 않는다. 숫자 2/10, 음수, 정수 정밀도, 문자열 사전순,
  다중 샤드 reduce 후 정렬/size 적용을 검증해야 한다. 현재 코드는 변경하지 않았다.
- bool 수정은 engine 839/839, node 605/605, 통합 7/7, 실제 경계 200/200 및
  코어 1180/1180의 기능 증거를 확보했지만 전체 성능은 실패다. 큰 구현 단위
  최종 수락 0/40, 기존 alias/PIT/중첩 집계 미완료 및 릴리즈 보류를 유지한다.

### C06/P03: 버킷 키 정렬과 순서 보존 검증

- 직전 단계의 전체 성능 결과 확보는 진행이다. 정렬 경로를 확인한 결과
  `bucket_sort_key`의 `n:{value}` 문자열을 직접 비교해 숫자 10이 2보다 먼저
  정렬되는 경로를 확인했다. 식별/중복 제거용 키 표현과 정렬 계약을 구별한다.
- `generate-bucket-key-fixture.py`에서 long/double/keyword x 1/3샤드 x hits 0/10 x
  bucket size 1/3/20의 36개 HTTP fixture를 생성했다. 음수, 2/10, 2^53 초과 정수,
  i64 최대값, 소수 및 문자열을 포함한다. 수정 전 `a917c150...`의 첫
  `live-bucket-key-before`는 36/36으로 보였지만 일반 `aggregations` extractor가
  버킷을 정규화 정렬해 원시 응답의 순서 차이를 숨겼다. **정렬 합격 증거가 아니다.**
  이 보고서 SHA-256 `202e587bd808476d29b1ccd52f9deba17b591bd96388d0db9569f159c214146d`.
- 원시 응답에서 long 버킷의 참조 순서는 -10,-2,0,2,10,..., 후보는
  -10,-2,0,10,2,...였다. 기존 순서 보존 `terms_aggregation` extractor를 선택한
  별도 `bucket-key-ordered-compat.json`으로 다시 비교했다. fixture SHA-256:
  `a05ef902ebc431f97f49dcdfbbf261ea1db54b8947bdd8895056b677fb7f64ca`.
  `live-bucket-key-ordered-before`는 **28/36 통과, 숫자 순서 8개 실패**, skipped 0.
  보고서 SHA-256 `7b622f21dbfc82af5bd0ca25a3ef0396a5800e11aa13552ecf80e72ecffd3986`.
  두 실행 모두 기존 코어 1180/1180, nested 각각 130/160이었다. 기존 실패를
  지우거나 일반 집계의 정규화 정책을 전역 변경하지 않았다.
- `compare_bucket_keys`를 추가하고 문자열 키 비교 표현 15곳을 기계적으로
  교체했다. 기본 terms 동점 정렬, merge, bucket sort 및 공유 terms 계열 정렬에
  적용한다. 버킷 식별/중복 제거용 `bucket_sort_key` 호출은 유지했다.
  숫자 순서를 위해 매 비교마다 문자열을 만들지 않으며, 문자열 키는 날짜로
  재해석하지 않고 사전순을 유지한다. i64/u64는 i128로 정확 비교한다. 정수/소수
  혼합은 정수를 f64로 반올림하지 않고 소수의 정수부/소수부를 비교한다.
- 신규 검사는 2/10, 음수, 2^53 초과 정수, i64/u64 경계, 정수/소수 혼합,
  부호 있는 0, 키 문자열 및 비교의 대칭성/추이성을 포함한다.
  `bucket-key-engine-node-tests.log`: **engine 840/840, node 605/605 통과**,
  종료 0, ignored/filtered 0, debug 빌드 1분 35초/실행 7.89초와 4.44초.
  engine 소스 SHA-256 `804445c5cc16cb17ed02aad2d37b0b1a29fe38256c1431ad3ca86f818b9c0aee`;
  로그 `8a15623a39f3683958166444b5adf8cf1c3a6c621cd67350ee1aa3a1fb76bc5f`.
  동시 refresh 통합 `bucket-key-integration.log`도 **7/7 통과**, 종료 0,
  실행 15.24초, SHA-256 `d0dc630f9f0bb85bfe9895f0f0bc79f76b84442426c4ea32978aab2bfd70ad7e`.
- 수정 전 바이너리는 `steelsearch-before-bucket-key`에 원래 해시로 보존했고
  새 release 프로파일 빌드를 시작했다. 최신 실행 파일의 HTTP 및 전체 성능은
  아직 없다. typed terms의 order 파서 지원 자체는 이 정렬 수정에 포함되지
  않으며 기존 nested 집계 30개 실패가 해결됐다고 선언하지 않는다.
  C06 수락/성능 개선/릴리즈/ledger 제외를 선언하지 않는다.

### C06: 버킷 키 정렬의 실제 HTTP 재검증

- `bucket-key-release-build.log`에서 standalone release 빌드 종료 0, 4분 50초.
  실행 파일 SHA-256 `bc9155c1d046908f365eec402d1c7fc9f85718422b454ba38695e1000cc70725`;
  빌드 로그 `4d5030c056614abe70b8c68b8e0795dcd8d8a109d04a2aee56116fa939376f6b`.
- `live-bucket-key-after`에서 동일한 순서 보존 fixture **36/36**, bool 경계
  **200/200**, 기존 코어 **1180/1180** 통과, skipped 0이다. 숫자 순서 차이 8개를
  실제 OpenSearch 3.7.0-SNAPSHOT 비교로 해소했다. settings/routing도 통과했고,
  candidate count/alias/PIT 42/57(참조 57/57), nested 각각 130/160의 기존 실패는
  유지했다. 전체 runner 종료 1. setup 실패 없음, binary/fixtures unchanged true.
  execution SHA-256 `174465e400f6aba7585e2cc940abea88c59d7e1353c59c45b1a302a6935ead86`;
  ordered bucket report `381cfd093868b860041f838787957c43a198022c645b8fbb65bf7b621b022722`;
  bool report `e4429ca34154d8617fece9905c24ff408ee9c59e57928bc63d258d5f21f9362f`;
  core report `5dad7bb07af43cc3a715277d753489cc5700824f96678c431eba19f43eecfc49`.
- 정렬용 문자열 포맷 생성을 제거했지만 일부 호출부의 Value 복사는 남아 있다.
  할당 전체 제거 또는 처리량 개선으로 과장하지 않는다. 기능 비교 프로세스 종료 후
  `bucket-key-repeated-full`에서 전체 12개 성능 시나리오를 고정 순서로 시작했다.
  최신 소스/실행 파일은 측정 중 변경하지 않으며 결과 확정 전 수락은 보류한다.

### C06/P03: 버킷 키 정렬 후보의 전체 반복 성능 결과

- `bucket-key-repeated-full`의 사전 고정 6회/12개 시나리오를 모두 완료했다.
  총 1097.8189초, 하위 실행 모두 종료 0, 모든 시나리오 요청 오류 0건이다.
  최종 종료 1, **수치 게이트 실패**. `execution_inputs_verified=true`,
  infrastructure error 없음. engine `804445c5...`, node `405e8953...`, 실행 파일
  `bc9155c1...`를 전후 확인했다. 빌드/다른 부하를 측정과 겹치지 않았다.
  result SHA-256 `e83cd853c36aa9bdab945297bed8691e55d6398d4d951feaac4491b3a0f671d9`;
  plan `beef84bc020d9a16637324b6873306f58192e5b9bd6269df9cabb6d176c44afd`.

| 후보 반복 | 최초 v0.6.0 대비 | 같은 실행 v0.6.0 대비 | v0.6.0 재측정 자체의 기준 대비 |
| --- | --- | --- | --- |
| 01 | 41/44 통과 | 42/44 통과 | 44/44 통과 |
| 04 | 44/44 통과 | 44/44 통과 | 43/44 통과 |

| 비교 | 반복 | 초과 지표 | 지연 증가 |
| --- | --- | --- | --- |
| 최초 v0.6.0 대비 후보 | 01 | single/refresh/p99 | +8.433059% |
| 최초 v0.6.0 대비 후보 | 01 | three/sort_filter/p95 | +5.010479% |
| 최초 v0.6.0 대비 후보 | 01 | three/sort_filter/p99 | +12.015344% |
| 같은 실행 v0.6.0 대비 후보 | 01 | single/refresh/p99 | +10.710718% |
| 같은 실행 v0.6.0 대비 후보 | 01 | three/sort_filter/p99 | +16.054030% |
| 최초 대비 v0.6.0 재측정 | 05 | three/sort_filter/p99 | +9.219426% |

| 후보 반복 / 토폴로지 | 후보 ops/s | 최초 v0.6.0 대비 처리량 변화 | 짝지은 OpenSearch 2.19 ops/s | 처리량 배율 |
| --- | --- | --- | --- | --- |
| 01 / single | 745.1465 | +0.2874% | 289.6629 | 2.5725x |
| 01 / three | 915.2292 | -1.7330% | 111.9232 | 8.1773x |
| 04 / single | 760.4940 | +2.3530% | 287.9090 | 2.6414x |
| 04 / three | 932.3245 | +0.1025% | 116.8153 | 7.9812x |

- 증가율은 반올림 전 값으로 5%를 판정했다. 두 번째 후보의 44/44 통과를 선택해
  첫 반복의 실패를 취소하지 않는다. 기준 자체의 변동도 관찰 사실일 뿐 면제 근거가
  아니다. 위 처리량은 개발용 혼합 부하에 한정하며 운영 내구성/분산 기능 동등성이나
  정렬 변경의 성능 개선을 증명하지 않는다. 특정 변경의 5% 이상 기여와 최적화
  불가가 입증되지 않아 ledger 제외는 없다.
- 종료 후 소유 SteelSearch/Java/컴파일 프로세스가 없고 비교 컨테이너가 정리됐음을
  확인했다. 기존 사용자 컨테이너는 그대로 유지했다. 기능 증거는 engine 840/840,
  node 605/605, 통합 7/7, 순서 보존 HTTP 36/36, bool 200/200, 코어 1180/1180이다.
  성능 실패와 기존 alias/PIT/중첩 집계 미완료는 남아 있다. C06 전체 수락 또는
  릴리즈를 선언하지 않으며, 다음 terms order 지원과 성능 원인 분석을 계속해야 한다.

### P03: BM25 필드 통계 맵 공유 검증

- `CachedBm25FieldStats.term_doc_counts`를 `Arc<BTreeMap<String, usize>>`로
  변경하여 캐시 조회와 요청 문맥 복사 시 불변 빈도 맵을 공유한다. 점수 공식,
  캐시 키, refresh seq_no 검증은 유지한다. 이 변경만으로 속도 개선을 주장하지 않는다.
- 추가 회귀 테스트는 캐시/요청 문맥의 맵 공유, refresh 전후 통계 분리,
  이전 스냅샷 재조회와 새 스냅샷 요청 문맥 갱신을 확인한다.
- engine 841/841, node 605/605, concurrent_refresh 통합 7/7 통과.
  증거 디렉터리: `target/core-replacement-c05/`.
  `bm25-shared-stats-engine-node-tests.log` SHA-256:
  `aeb13a838ff6f94a39572b5c9811db20aff22bef5a458753ed49628281f25109`.
  `bm25-shared-stats-integration.log` SHA-256:
  `ca29e2e52afb88644b31281dc19ba099855017db85c6883a57bc2fd705cd5efc`.
- engine 소스 SHA-256:
  `060c9807b1b1b878366a14c79b8647f126f49924a570e7410358b65437f2f3ca`.
  직전 실행 파일 `bc9155c1...`는 `steelsearch-before-bm25-shared-stats`에
  보존했다. 새 release 빌드, 순서 보존/불리언/코어 HTTP 비교, 고정 기준 전체
  반복 성능 검증까지 완료해야 판정한다. 현재 구현 단위 수락은 보류한다.
- 새 release 실행 파일 SHA-256:
  `93cebb0a4c5894170b6ca7fa1ecd216eb69fee01894e98f4dd2d7d5b118fced2`.
  빌드 로그 `bm25-shared-stats-release-build.log` SHA-256:
  `cc11784f395db4144b749d66b90fa8bf152907de12b06abf3eef08cc3cebee99`.
- `live-bm25-shared-stats` 실제 HTTP 비교: 순서 보존 버킷 36/36,
  bool 200/200, 코어 1180/1180 통과. settings/routing probe 통과,
  count probe 실패와 nested 두 fixture 각각 130/160은 유지된다.
  setup 실패/skip 0, binary/fixtures 불변 확인. 기존 실패로 runner 종료 1이며
  전체 기능 통과로 처리하지 않는다. 기능 참조는 OpenSearch 3.7.0-SNAPSHOT,
  아래 성능 참조는 고정 OpenSearch 2.19.0으로 서로 구분한다.
  `execution.json` SHA-256:
  `d33e8ddc208a95e454e8466b820a1221047fd35cdbdec02a0f3010be78f27bb5`.
  순서 보존 보고서 `03684f95e225474dd4903c4d7a24c70f43ad3a29fffd99748f1d0eeeb37e890b`,
  bool `771d6fab67c8a818b478fc5aad11b1050233a99e1fecc8071701c166a59c0836`,
  코어 `a3e1ab6f46e1843934fa0c075bc8a61217a204aeb417e319373dd2cbcb4eb23b`.
- 기능 실행 프로세스 종료 확인 후 `bm25-shared-stats-repeated-full`에서
  고정 순서 전체 6회/12개 시나리오를 실행한다. 측정 도중 실행 입력이나
  후보 소스를 변경하지 않으며 빌드/다른 부하를 겹치지 않는다.

### P03: BM25 통계 공유 후보 전체 반복 성능 결과

- `bm25-shared-stats-repeated-full`의 사전 고정 6회/12개 시나리오 완료.
  총 1094.5061초, 하위 실행 모두 종료 0, 모든 시나리오 요청 오류 0건.
  최종 종료 1, **수치 게이트 실패**. `execution_inputs_verified=true`,
  infrastructure error 없음. engine `060c9807...`, node `405e8953...`,
  실행 파일 `93cebb0a...`의 측정 후 해시가 일치했다.
  result SHA-256 `f896b32c5c7b46042900e055e2f9ff8c4f274a3d9cee21ce4fb89591db7638a5`;
  plan `9ad8e7c8597ac89bca7855bff2c8055dcb9193b872992a69a6068a693f5f4ed0`.

| 후보 반복 | 최초 v0.6.0 대비 | 같은 실행 v0.6.0 대비 | 기준판 재측정 자체의 최초 대비 |
| --- | --- | --- | --- |
| 01 | 43/44 통과 | 43/44 통과 | 44/44 통과 |
| 04 | 44/44 통과 | 44/44 통과 | 41/44 통과 |

| 비교 | 반복 | 초과 지표 | 지연 증가 |
| --- | --- | --- | --- |
| 최초 v0.6.0 대비 후보 | 01 | three-node/lexical/p99 | +7.199103% |
| 같은 실행 v0.6.0 대비 후보 | 01 | three-node/lexical/p99 | +8.886197% |
| 최초 대비 기준판 재측정 | 05 | single-node/refresh/p99 | +9.980746% |
| 최초 대비 기준판 재측정 | 05 | three-node/sort_filter/p95 | +5.061053% |
| 최초 대비 기준판 재측정 | 05 | three-node/nested/p99 | +8.582638% |

- 첫 후보의 three-node/lexical/p99는 최초 10.130532924085863 ms,
  같은 실행 기준판 9.973569433204812 ms, 후보 10.859840419143467 ms다.
  반올림 전 값으로 판정한다. 두 번째 후보의 통과나 기준판 자체의 변동으로
  첫 후보의 실패를 면제하지 않는다.

| 후보 반복 / 토폴로지 | 후보 ops/s | 최초 v0.6.0 대비 처리량 변화 | 짝지은 OpenSearch 2.19 ops/s | 처리량 배율 |
| --- | --- | --- | --- | --- |
| 01 / single | 752.6110 | +1.2920% | 284.6389 | 2.6441x |
| 01 / three | 916.2233 | -1.6263% | 118.3428 | 7.7421x |
| 04 / single | 756.4231 | +1.8051% | 293.8670 | 2.5740x |
| 04 / three | 931.5585 | +0.0202% | 114.7370 | 8.1191x |

- 위 결과는 개발용 혼합 부하의 누적 비교이며 BM25 변경 단독의 속도 개선이나
  저하 기여를 증명하지 않는다. 직전 후보와 이번 후보의 서로 다른 전체 실행을
  직접 인과 비교하지 않는다. 최적화 불가도 입증되지 않아 ledger 제외는 없다.
- 종료 후 소유 SteelSearch/Java/컴파일 프로세스와 비교 컨테이너 정리 확인.
  기존 사용자 컨테이너는 유지했다. 전체 단위 최종 수락은 **0/40**이며 이는
  구현량 0%라는 의미가 아니다. 이번 후보는 검증 중 상태로 유지하고 릴리즈하지 않는다.
- 다음 성능 진단은 고정 부하에서 보존한 직전 `bc9155c1...`와 이번
  `93cebb0a...`를 사전 고정 균형 순서로 대조해 변경 단독의 기여를 조사한다.
  단일 진단은 전체 게이트를 대신하지 않는다. 추가 최적화 후 전체 비플러그인
  벤치마크를 다시 수행하며 최초 v0.6.0 기준을 유지한다. 별도 기능 작업으로는
  `terms.order` 파싱/실행/샤드 병합과 alias/count/global/PIT 범위 보강이 남아 있다.

### P03: BM25 공유 변경의 ABBA 대조 및 lexical CPU 진단

- 직전 goal turn은 전체 12개 측정과 기능 검증 결과를 확정한 progress다.
  이번에는 실행 중인 소유 프로세스가 없음을 확인하고 보존된 직전 실행 파일
  `bc9155c1...`와 공유 후보 `93cebb0a...`의 해시를 재확인했다.
- `target/core-replacement-c05/run-bm25-paired-diagnostic.py`가
  `bm25-sharing-abba/plan.json`에 직전/공유/공유/직전 순서와 모든 명령,
  실행 도구 및 바이너리 해시를 실행 전에 고정했다. 기존 matrix를 사용해
  각 60초, 5000문서, 384벡터 소스, 4클라이언트, seed 13, 3노드/3샤드/
  replica 1, 기존 7종 혼합 부하를 프로파일러 없이 실행했다.
  각 실행 전후 입력 불변 확인, 실제 3개 서버의 전후 SHA-256 모두 일치.
  4회 모두 종료 0, 요청 오류 0, 총 264.4983초. 전체 성능 게이트가 아닌
  변경 단독 기여의 보조 진단이며 원래 v0.6.0 기준은 변경하지 않는다.

| 실행 | 후보 | 처리량 ops/s | lexical mean ms | lexical p95 ms | lexical p99 ms |
| --- | --- | --- | --- | --- | --- |
| 00 | 직전 | 933.5991 | 3.529274 | 6.764721 | 9.794993 |
| 01 | 공유 | 933.8006 | 3.532690 | 6.747075 | 10.259272 |
| 02 | 공유 | 929.8781 | 3.521400 | 6.689128 | 10.285782 |
| 03 | 직전 | 936.9779 | 3.524265 | 6.762915 | 10.054579 |

- 사전 순서의 인접 쌍 00→01, 03→02에서 공유판 처리량 변화는 각각
  +0.021574%, -0.757730%, lexical p99 변화는 +4.739960%, +2.299477%다.
  첫 쌍의 21개 지연 지표는 모두 5% 미만 증가지만 sort_filter p99가
  +4.994463%로 한도에 근접한다. 둘째 쌍은 facet p99 +9.629744%
  (12.774440→14.004586 ms), nested p99 +5.733894%
  (10.941775→11.569165 ms)다. 두 쌍을 평균 내거나 좋은 쌍만 선택하지 않는다.
  유의한 개선을 입증하지 못했고, 단일 기능의 최적화 불가도 입증하지 못했다.
  후보 최종 수락 및 ledger 제외는 보류하며 기존 누적 게이트 실패를 유지한다.
- ABBA result SHA-256:
  `7a4ef1bc460b792cd06fbb2c5db965b311da0a53babba38513af4bb94e138f10`;
  plan `2760fba04cde873f3d2a5caaa297fe32fbd6952f1c65688aae7dcd1df0ef53d0`.
  각 원본 보고서 해시는 result에 보존했다. 실행 도중 소스/도구 변경이나
  빌드/프로파일러/기능 부하를 겹치지 않았고 실패를 대체하는 재실행도 없다.
- 대조가 종료된 후 기존 `tools/run-core-cpu-diagnostic.py`로 별도
  `bm25-shared-lexical-cpu` 진단을 실행했다. 공유판, lexical 100%, 3노드,
  45초 부하 중 20.8315초 구간을 cpu-clock 49Hz로 관찰했다.
  perf/matrix 모두 종료 0, 샘플 유실 0, 바이너리 전후 해시 일치.
  CPU 시간은 부하 생성기 22.15초, 서버 각각 3.61/4.37/8.16초(합계 16.14초).
  프로파일러가 붙은 수치는 정식 처리량/지연 비교에 합치지 않는다.
- 서버 스택에는 `search_hit_for_document_with_score`의 JSON 배열/맵 복사,
  `rest_response_to_actix_response`의 f64/JSON 직렬화, 할당과 작업 스케줄링이
  관찰됐다. 샘플에서 BM25 통계 복사가 주된 비용이라는 근거는 얻지 못했다.
  샘플 부재는 해당 함수가 실행되지 않는다는 증거가 아니며, CPU 점유율만으로
  HTTP p99 회귀 기여를 환산하지 않는다. 다음 분석은 이 응답 생성 경로에서
  중복 복사 여부를 확인하고, 의미 보존이 가능한 변경만 실제 대조 검증한다.
  부하 생성기를 바꿔 기존 회귀를 통과시키는 방식은 사용하지 않는다.
- CPU diagnostic SHA-256:
  `b67d2cb7bbec3ad3f11a43aa1f4b91528a45e549e890772bf981f02c0e50aec4`;
  perf.data `2d20784a45d4f69667c104ee02fc198b1540ed819b7a3a6ac7d9f3d9c842f29c`;
  server-self.txt `fce22ad8ec7069cc0e181d23e2e34ec512526ae2b3ed108cb1154d8de0473756`.
- 소유 프로세스/비교 컨테이너 종료 확인, 사용자 컨테이너 유지.
  이번에는 런타임 구현을 변경하지 않았고 새 전체 벤치마크를 수행한 것으로
  표시하지 않는다. 정식 최신 결과는 위 BM25 전체 12개 측정의 실패다.

### P03: 응답 소유권 회귀 검사 및 샤드 페이지 복사 경계

- 직전 turn은 ABBA와 CPU 진단을 완료해 다음 조사 대상을 정한 progress다.
  현재 worktree를 재확인했으며 사용자 변경은 되돌리지 않았다.
- native REST 경로는 이미 `native_search_response_to_rest_response`에서
  `SearchResponse::into_opensearch_body`를 사용한다. `SearchHit`의 owned 변환은
  source/optional section을 이동하며, 최종 HTTP 변환은 JSON을 바이트로 직렬화한다.
  따라서 이 경로에 이미 없는 source 복사를 제거하는 최적화를 추가하지 않는다.
  fallback의 `apply_search_source_projection_to_hits`에는 별도 복사가 있지만
  이번 native lexical 프로파일의 직접 원인으로 단정하거나 혼동하지 않는다.
- `crates/os-engine/src/lib.rs`에
  `owned_search_response_preserves_shape_and_moves_source_buffers` 테스트를 추가했다.
  선택 section 5개의 유무 조합 32가지, 384차원 JSON 벡터, 중첩 source,
  null/음의 0 점수, 집계 및 빈 응답에 대해 borrowed/owned 변환 결과를 비교한다.
  owned 변환 전후 source 벡터와 집계 버킷의 allocation 주소가 같음도 확인한다.
  선택 section 값은 opaque JSON 이동 검사이며 각 section DSL 유효성 검사가 아니다.
- `cargo +nightly test -p os-engine --lib` **13/13 통과**, 실행 0.01초.
  초기 두 번의 테스트 컴파일 오류는 비트마스크 정수 타입 추론 문제였으며
  u8을 명시해 수정했다. 초기 로그 두 개는 별도로 보존했다.
  최종 로그 `target/core-replacement-c05/owned-response-engine-tests.log` SHA-256:
  `4c9d741343d3ba36cd8668e5172761e247f9357af076c985eafb00ed6cb858a7`.
  os-engine 소스 SHA-256:
  `e0ff8ef2b6c383f7b41d649ae11ebd3d5fbcada0458dca8e7a9b6253d9881797`.
- `search_hits_page_for_query_native_sharded_tantivy`는 각 샤드에서
  `from + size` 후보를 구한 뒤 모든 후보의 source를 SearchHit로 복사하고,
  전역 정렬 후 `skip(from).take(size)`로 나머지를 버린다. 여기에는 최종 페이지에
  들지 못할 문서의 source 복사 비용이 있다. 기본 관련도 비교는 점수 내림차순과
  index/id 동점 순서만 사용하므로 source가 필요하지 않다. 명시적 필드/스크립트/
  geo 정렬은 source를 사용하므로 같은 가정으로 바꾸면 안 된다.
- 다음 구현 단위:
  1. 기본 관련도 경로에서 snapshot에 묶인 borrowed document와 최종 score를
     샤드 후보로 유지하고 전역 페이지 선택 후 SearchHit를 만든다. 명시적 `_score`
     desc가 기존 기본 관련도 판정에 포함된다는 점도 유지한다.
  2. 기존 점수 정규화 시점, source 기반 재점수, BM25 재점수, 동점 index/id 순서,
     오류 전파, selected_shards, size 0, 포화 덧셈과 페이지 경계를 보존한다.
     특수 쿼리의 기존 fallback이나 안전 검사를 제거하지 않는다.
  3. 1/3샤드, 병렬 기준 2048문서 전후, from/size, 명시적 정렬, 동점/점수 0,
     routing과 refresh snapshot에 대해 이전 구현을 oracle로 비교한다.
     최종 페이지 외 source를 복사하지 않는다는 구조적 증거도 추가한다.
  4. engine/node 전체 단위·통합·실제 HTTP 기능 비교 후 고정 v0.6.0 기준
     전체 비플러그인 벤치마크를 실행한다. 진단이나 source 복사 감소만으로
     성능 개선/수락을 선언하지 않고 누적 5% 규칙을 유지한다.
- 이번 변경은 테스트뿐이며 런타임 구현/바이너리는 변경하지 않았다.
  release SHA-256은 `93cebb0a...`로 동일하다. 새 전체 성능 측정을 수행한 것으로
  표시하지 않으며, 최신 정식 성능 실패와 0/40 최종 수락 보류를 유지한다.

### P03: 샤드 페이지 선택 후 source 복사 후보

- 직전 turn은 응답 이동 회귀 검사와 실제 샤드 후보 복사 경계를 확인한 progress다.
  실행 중인 소유 프로세스가 없음을 확인한 뒤 이번 런타임 수정을 시작했다.
- `search_hits_page_for_query_native_sharded_tantivy`의 샤드 수집 결과를
  `Vec<(&StoredDocument, f32)>`로 바꿨다. 참조 수명은 동일 snapshot과 선택 샤드
  범위에 묶인다. 기본 관련도는 정규화된 점수와 문서 ID로 전역 정렬하고,
  `skip(from).take(size)` 뒤에만 `search_hit_for_document_with_score`를 호출한다.
  모든 후보가 같은 index_name을 사용하므로 기존 index/id 동점 비교와 같다.
- source 기반 재점수와 BM25 재점수 후의 0→1 정규화를 그대로 유지한다.
  명시적 필드 정렬은 모든 후보를 SearchHit로 만든 다음 기존 `sort_hits`를
  적용한다. 기존 지원 검사, 특수 쿼리 fallback, size 0, total 누적/first-pass
  포화 덧셈, 오류 전파와 병렬 처리 기준은 유지했다. 기존 함수는 이름만 바꿔
  `#[cfg(test)]` eager reference로 보존했으며 release에 포함하지 않는다.
- `deferred_sharded_pages_match_eager_reference_across_snapshots`는 총 2016개
  조합에서 기존/새 반환 값을 직접 비교한다. 1샤드 32문서, 3샤드 2047/2048문서,
  refresh 전후 snapshot, 7개 쿼리, 기본/명시적 score/필드 정렬, 전체/빈/부분
  샤드 선택, size 0 및 앞/중간/범위 밖 페이지를 포함한다. native와 fallback
  사례 모두 존재함을 확인하고 반환 score의 to_bits도 비교했다. 1샤드는
  이 함수의 기존 None 반환 보존 검사이며 단일 샤드 실행 전체 증명은 아니다.
- 초기 cargo check의 참조 수명 오류는 selected_shards에도 동일 lifetime을
  명시해 수정했다. 전체 단위 검사 **engine 842/842, node 605/605 통과**,
  build 1m47s, 실행 10.96/4.45초. refresh 통합 **7/7**, 15.58초.
  증거: `target/core-replacement-c05/deferred-page-engine-node-tests.log`
  SHA-256 `70d14bf2c2e7b732376d752a78437d5575b270eca9d78e1aa0077f94dc2376e7`;
  `deferred-page-integration.log`
  `40c11bbdef9b0f73d34443f6f85994fdb0c345f7e1cd3579c256b7e52a36e853`.
- engine 소스 SHA-256:
  `d780eb4c5e10b5f7562fd42c4d5ad01e1dd0f30357219299f101c59dc73ad68f`.
  직전 실행 파일 `93cebb0a...`는 `steelsearch-before-deferred-page`에 보존했다.
  새 release 빌드 및 전체 실제 HTTP 비교, 고정 v0.6.0 전체 반복 성능 측정이
  남아 있다. 복사 감소만으로 성능 개선이나 구현 단위 수락을 선언하지 않는다.
- 새 release build 5m20s 완료. 실행 파일 SHA-256:
  `cbed6b365768b54e7686af2b1f8b6f2a0865602d66a9ad0e025833a7d2fe12bc`;
  `deferred-page-release-build.log`
  `3d2b91c99ee6ce49eea88c5abdb8dc2a65b031f8c15e95512192b3ae975e151a`.
- `live-deferred-page` 실제 HTTP 비교에서 순서 보존 버킷 36/36,
  bool 200/200, 코어 1180/1180 통과. settings/routing probe 통과,
  기존 count 실패와 nested 두 fixture 각각 130/160은 유지된다.
  setup 실패/skip 0, 실행 파일/fixture 불변 확인. 기존 실패로 runner 종료 1.
  기능 참조는 OpenSearch 3.7.0-SNAPSHOT으로, 성능 참조 2.19.0과 구분한다.
  execution SHA-256 `e771ac0429fdf1b100d323f0bc9c5d8eb64cf93a2c53d79da38b495da743fd6a`;
  버킷 보고서 `a003273cbb3549db66a238a68aa896b99af805d68d0f4e0d7451b884e1f49362`;
  bool `158b67afd909496c91b071b1116ef4d5f554803fb550804eea36e4c371f3f0b4`;
  코어 `c9cdd5880b352aadc4a152f7e59e6c8d4dbb6dfb2fabeef8e2828da75bde77b7`.
- 기능/컴파일 프로세스 종료 후 `deferred-page-repeated-full`에서 고정 순서
  6회/12개 전체 성능 시나리오를 시작했다. 기준을 직전 후보로 바꾸지 않으며
  측정 결과가 확정되기 전까지 이번 구현 단위의 수락을 보류한다.

### P03: 지연된 페이지 복사 후보 전체 반복 성능 결과

- `deferred-page-repeated-full`의 사전 고정 6회/12개 시나리오 완료.
  총 1098.1934초, 하위 실행 모두 종료 0, 12개 모두 요청 오류 0건.
  최종 종료 1, **수치 게이트 실패**, `execution_inputs_verified=true`,
  infrastructure error 없음. 측정 후 engine `d780eb4c...`, node `405e8953...`,
  실행 파일 `cbed6b36...` 해시가 일치했다. 실행 도구/소스 변경 및 다른 부하를
  측정과 겹치지 않았다. 테스트용 eager reference는 수정 전 원본과 함수 이름
  이외의 코드가 정확히 일치함을 추가 확인했다.
  result SHA-256 `2ce509601f6f80515ab67573dc903a945d8f5aae929aaa9b9462ce4650099675`;
  plan `50e930ebc1436b757a1cf71097d5b997a8e2be88ab8b747fd53c2bbaf26c6bb7`.

| 후보 반복 | 최초 v0.6.0 대비 | 같은 실행 v0.6.0 대비 | 기준판 재측정 자체의 최초 대비 |
| --- | --- | --- | --- |
| 01 | 44/44 통과 | 44/44 통과 | 44/44 통과 |
| 04 | 37/44 통과 | 41/44 통과 | 43/44 통과 |

| 비교 | 반복 | 초과 지표 | 지연 증가 |
| --- | --- | --- | --- |
| 최초 v0.6.0 대비 후보 | 04 | three-node/lexical/p99 | +5.039275% |
| 최초 v0.6.0 대비 후보 | 04 | three-node/ranking/p99 | +5.251537% |
| 최초 v0.6.0 대비 후보 | 04 | three-node/facet/p99 | +7.841016% |
| 최초 v0.6.0 대비 후보 | 04 | three-node/sort_filter/p99 | +11.510836% |
| 최초 v0.6.0 대비 후보 | 04 | three-node/nested/p99 | +9.193941% |
| 최초 v0.6.0 대비 후보 | 04 | three-node/refresh/mean | +5.522664% |
| 최초 v0.6.0 대비 후보 | 04 | three-node/refresh/p99 | +5.881412% |
| 같은 실행 v0.6.0 대비 후보 | 04 | three-node/lexical/p99 | +5.049586% |
| 같은 실행 v0.6.0 대비 후보 | 04 | three-node/sort_filter/p99 | +8.831427% |
| 같은 실행 v0.6.0 대비 후보 | 04 | three-node/nested/p99 | +7.071512% |
| 최초 대비 기준판 재측정 | 05 | three-node/nested/p95 | +5.237004% |

| 후보 반복 / 토폴로지 | 후보 ops/s | 최초 v0.6.0 대비 처리량 변화 | 짝지은 OpenSearch 2.19 ops/s | 처리량 배율 |
| --- | --- | --- | --- | --- |
| 01 / single | 765.3792 | +3.0105% | 286.2268 | 2.6740x |
| 01 / three | 933.1995 | +0.1964% | 116.8370 | 7.9872x |
| 04 / single | 749.3803 | +0.8572% | 289.8687 | 2.5852x |
| 04 / three | 915.3140 | -1.7239% | 116.2140 | 7.8761x |

- 한도 근처 값도 반올림 전 판정한다. lexical p99는 최초
  10.130532924085863 ms에서 10.641038366593452 ms로 증가했고,
  105% 한도 10.63705957029015615 ms를 넘었다. 첫 반복의 완전 통과로
  둘째 반복 실패를 취소하지 않는다. 기준 자체의 변동도 면제 근거가 아니다.
- 최종 페이지 외 source 복사가 제거됐다는 코드/기능 증거와 전체 지연 개선은
  별개다. 서로 다른 실행의 직전 후보와 비교해 이번 변경 단독의 효과를 단정하지
  않는다. 전체 누적 실패는 정상 수락을 막지만, 단일 변경의 5% 이상 원인 기여와
  최적화 불가가 아직 입증되지 않았으므로 ledger 제외는 없다.
- 소유 프로세스/비교 컨테이너 정리 확인, 기존 사용자 컨테이너 유지.
  engine 842/842, node 605/605, 통합 7/7, HTTP 버킷 36/36, bool 200/200,
  코어 1180/1180이라는 기능 증거는 유지한다. 기존 alias/PIT/중첩 집계 실패와
  전체 0/40 최종 수락 보류도 유지한다. 릴리즈/태그 생성은 하지 않는다.
- 다음은 보존된 직전 `93cebb0a...`와 현재 `cbed6b36...`의 사전 고정 대조로
  이번 복사 변경의 비용을 분리하고, 특히 명시적 정렬 경로의 추가 후보 벡터가
  영향을 주는지 확인한다. 필요한 최적화 뒤 전체 비플러그인 벤치마크를 다시
  실행하며, 최초 v0.6.0 기준과 기존 기능 보강 범위를 그대로 유지한다.

### P03: 지연된 페이지 복사의 사전 고정 ABBA 대조

- 직전 turn은 실제 구현, 2016개 oracle 조합 및 전체 기능/12개 성능 측정을
  완료한 progress다. 이번에는 실행 중 소유 프로세스가 없고 수정 전 `93cebb0a...`,
  수정 후 `cbed6b36...` 바이너리가 보존됐음을 재확인했다.
- `target/core-replacement-c05/run-deferred-page-paired-diagnostic.py`는 이전
  진단을 보존한 별도 실행 사본이다. `deferred-page-abba`에 수정 전/후/후/전
  순서, 바이너리와 실행 도구 해시, 명령을 실행 전에 고정했다. 기존 matrix의
  3노드 혼합 부하(각 60초, 5000문서, 384벡터 소스, 4클라이언트, seed 13,
  3샤드/replica 1, 기존 7종 작업)를 프로파일러 없이 실행했다.
- 총 264.6175초, 4회 모두 종료 0, 모든 요청 오류 0건, 입력 전후 불변 확인.
  각 실행에서 실제 3개 서버의 전후 SHA-256도 해당 후보와 일치했다.

| 실행 | 후보 | 처리량 ops/s | lexical mean ms | lexical p99 ms | sort_filter p99 ms |
| --- | --- | --- | --- | --- | --- |
| 00 | 수정 전 | 928.3726 | 3.567710 | 10.502090 | 10.806902 |
| 01 | 수정 후 | 931.2552 | 3.411400 | 10.000342 | 11.453255 |
| 02 | 수정 후 | 927.1258 | 3.443536 | 10.576029 | 11.269216 |
| 03 | 수정 전 | 935.8050 | 3.526928 | 9.951634 | 10.867941 |

| 사전 순서의 비교 쌍 | 처리량 변화 | lexical mean 변화 | lexical p95 변화 | lexical p99 변화 | sort_filter p99 변화 |
| --- | --- | --- | --- | --- | --- |
| 00→01 | +0.310508% | -4.381215% | -5.272235% | -4.777604% | +5.980924% |
| 03→02 | -0.927453% | -2.364447% | -0.182855% | +6.274297% | +3.692275% |

- 21개 지연 지표 중 첫 쌍의 5% 이상 증가는 sort_filter p99 한 개,
  둘째 쌍은 lexical p99 한 개다. 나머지 지연 지표와 원본 보고서도 보존했다.
  평균 lexical 비용 감소가 두 쌍에서 관찰됐지만 p99는 일관되지 않다.
  두 쌍을 평균 내거나 유리한 반복만 선택해 전체 수락으로 바꾸지 않는다.
  이는 직전 후보 대비 보조 대조이며 최초 v0.6.0 누적 기준을 대신하지 않는다.
- 실제 부하의 sort_filter는 latency asc/price desc의 명시적 필드 정렬이다.
  현재 구현은 해당 경로에서도 borrowed 후보 Vec를 모은 뒤 SearchHit Vec를
  새로 만들기 때문에, 관련도 경로와 달리 source 복사 절감 없이 중간 벡터를
  추가한다. 이 비용 제거를 다음 최적화 후보로 삼되 위 HTTP p99 증가 전체가
  이 벡터 때문이라고 단정하지 않는다.
- 다음 수정은 공통 샤드 수집을 typed materializer로 재사용하여 관련도 경로는
  borrowed document/score, 명시적 정렬 경로는 즉시 SearchHit를 반환하게 한다.
  별도 복제된 두 런타임 수집기를 만들거나 문서당 동적 dispatch를 추가하지 않는다.
  기존 eager oracle/2016개 조합과 전체 engine/node/통합/HTTP 검사를 유지하고,
  구현 후 전체 비플러그인 벤치마크를 반드시 재실행한다.
- 자원 기록에서 모든 관찰 CPU cgroup level의 nr_throttled/throttled_usec는
  전후 0이었다. 읽을 수 있는 4개 memory.events 범위도 각 실행 전후 동일했다.
  root의 읽을 수 없는 메모리 카운터는 관찰하지 못한 것으로 남기며, 공유 cgroup
  카운터로 서버 단독 비용이나 host 간섭 부재를 증명하지 않는다. 과거 누적 OOM
  kill 값은 이번 실행에서 증가하지 않았으므로 새 실패로 세지 않는다.
- result SHA-256 `97c347e7944888d8c60c08826959aef4bcd015b69d78458f80e45fd0b39db586`;
  plan `29903946fc76c21e3a7e46ae0cd343513f07a9df78b5347c2a86de6fa552e97d`.
  보고서 순서별 SHA-256:
  `7e9e3be8235509252abe9a5cead0f101c21096f06cfb67d147c9d69bb14dddac`,
  `7b200d5093bfb3f3fdaa3d1b2ae5ab5999a28dd4a25a38bfa91ea259f71e2a1a`,
  `6128cbc4f35b4eb57897ec625132e995d91aab53bb093fc4d19b3006a02e736f`,
  `c601dc8518b55168a13b5fe260be7953a0f33844c19f3b03dff8c5ebd3dd526e`.
- 이번 turn에는 런타임 코드를 변경하거나 새 전체 게이트를 실행하지 않았다.
  정식 최신 결과는 위 deferred-page 전체 반복의 실패다. 최적화 불가가 입증되지
  않아 ledger 제외는 없으며 전체 0/40 수락 보류를 유지한다. 소유 프로세스와
  비교 컨테이너는 종료됐고 기존 사용자 컨테이너는 유지했다.

### P03: 정렬 방식별 샤드 후보 타입 분리

- 직전 turn은 ABBA 대조를 완료해 명시적 정렬의 중간 벡터를 다음 수정 대상으로
  확인한 progress다. 현재 소스 및 실행 프로세스 상태를 재확인한 뒤 수정했다.
- 샤드 검색/지원 검사/재점수/점수 정규화/병합을
  `collect_sharded_page_candidates<Hit, Materialize>`로 추출했다.
  관련도 경로는 document reference/score를 반환하여 전역 페이지 선택 뒤 복사하고,
  명시적 필드 정렬은 즉시 SearchHit를 반환한다. 후자의 참조 Vec→SearchHit Vec
  변환을 제거했으며, 공통 검색 로직을 두 런타임 함수에 복제하지 않았다.
  generic Fn을 사용해 문서당 동적 dispatch를 추가하지 않았다.
- 기존 eager reference는 변경하지 않았다. 2016개 조합의 반환 값/score bits
  oracle 검사와 기존 전체 단위 검사를 그대로 유지했다. engine **842/842**,
  node **605/605** 통과, build 1m32s, 실행 9.78/4.41초.
  concurrent_refresh 통합 **7/7** 통과, 15.50초.
- 증거 `target/core-replacement-c05/typed-page-engine-node-tests.log` SHA-256:
  `e9cfe9e57139e176243a76ceeb1ed6e71811501ec2f1915a546043fbaf0563d4`;
  `typed-page-integration.log`
  `2518c006e3eeb64f625e902e3da5ea93c8c2cae6d29a575415166cd7bb0cd54b`.
  engine 소스 `38cce4693f5363e36523024b9510988af27751e52a2fc46deeccf9bef3cbe806`.
- 직전 실행 파일 `cbed6b36...`를 `steelsearch-before-typed-page`에 보존했다.
  새 release 빌드/실제 HTTP 비교/전체 반복 성능 검증이 남아 있다. 구조적으로
  중간 벡터가 제거됐다는 사실만으로 p99 개선이나 단위 수락을 선언하지 않는다.
- 새 release build 4m51s 완료. 실행 파일 SHA-256:
  `18c1bb3e21214b9ab94645b6cd4ce6ee9472b9dae73921a2a88a0b7cc06bd102`;
  `typed-page-release-build.log`
  `7ba9ed226ce4d4b5fc377bd5360aa50741e509f7ad4bc47ecd06e9ae8b7d78b4`.
- `live-typed-page` 실제 HTTP 비교: 버킷 순서 36/36, bool 200/200,
  코어 1180/1180 통과. settings/routing probe 통과, 기존 count 실패와 nested
  두 fixture 각각 130/160 유지. setup 실패/skip 0, 바이너리/fixture 불변 확인.
  runner 종료 1은 기존 실패를 유지한 결과이며 전체 기능 통과로 표시하지 않는다.
  execution SHA-256 `ff2df59f0436c298f3c9d3380174f35373fd2c03dcde07cdb5c9f8b8cd8ff628`;
  버킷 `977743e4fbbe73005f6e5b29f2b3c12f3629d56394f20684e8837083a3c26695`;
  bool `e354915c6bbda348f1bfc843e9100948dd665be34ed2f75821c7c21b14e1ba7f`;
  코어 `34cdf3ef80f415d86733ee399679c49927aa42ecfa0bc760f1895d1137143ace`.
- 기능/컴파일 프로세스 종료 후 `typed-page-repeated-full`에서 사전 고정 6회/
  12개 전체 성능 시나리오를 시작했다. 기능 참조 3.7.0-SNAPSHOT과 성능 참조
  고정 OpenSearch 2.19.0을 구분하며 최초 v0.6.0 누적 기준을 유지한다.

### P03: 후보 타입 분리 후 전체 반복 성능 결과

- `typed-page-repeated-full`의 사전 고정 6회/12개 시나리오 완료.
  총 1095.6698초, 하위 실행 모두 종료 0, 12개 요청 오류 모두 0건.
  최종 종료 1, **수치 게이트 실패**, execution_inputs_verified=true,
  infrastructure error 없음. engine `38cce469...`, node `405e8953...`,
  실행 파일 `18c1bb3e...`의 측정 후 해시가 일치했다. 측정과 다른 부하를 겹치지 않았다.
  result SHA-256 `aa4de9e9592282f21c19526b67261771314bd1f53fc4aec961a4a27dcab1e81f`;
  plan `ac61c79b20b9aa577adf6c92840dd5efc4f60c81bf08f68c308ad8527db4d291`.

| 후보 반복 | 최초 v0.6.0 대비 | 같은 실행 v0.6.0 대비 | 기준판 재측정 자체의 최초 대비 |
| --- | --- | --- | --- |
| 01 | 43/44 통과 | 42/44 통과 | 42/44 통과 |
| 04 | 39/44 통과 | 36/44 통과 | 44/44 통과 |

| 비교 | 반복 | 초과 지표 | 지연 증가 |
| --- | --- | --- | --- |
| 최초 v0.6.0 대비 후보 | 01 | three-node/sort_filter/p99 | +7.750046% |
| 최초 v0.6.0 대비 후보 | 04 | single-node/write/p95 | +6.088320% |
| 최초 v0.6.0 대비 후보 | 04 | single-node/write/p99 | +5.073546% |
| 최초 v0.6.0 대비 후보 | 04 | single-node/refresh/p99 | +7.046710% |
| 최초 v0.6.0 대비 후보 | 04 | three-node/ranking/p99 | +5.292256% |
| 최초 v0.6.0 대비 후보 | 04 | three-node/refresh/p95 | +5.027267% |
| 같은 실행 v0.6.0 대비 후보 | 01 | three-node/sort_filter/p99 | +6.998943% |
| 같은 실행 v0.6.0 대비 후보 | 01 | three-node/refresh/p99 | +5.713739% |
| 같은 실행 v0.6.0 대비 후보 | 04 | single-node/lexical/p99 | +5.157678% |
| 같은 실행 v0.6.0 대비 후보 | 04 | three-node/write/p99 | +5.643364% |
| 같은 실행 v0.6.0 대비 후보 | 04 | three-node/ranking/p95 | +6.072274% |
| 같은 실행 v0.6.0 대비 후보 | 04 | three-node/ranking/p99 | +8.015463% |
| 같은 실행 v0.6.0 대비 후보 | 04 | three-node/nested/p99 | +6.141008% |
| 같은 실행 v0.6.0 대비 후보 | 04 | three-node/refresh/mean | +6.425880% |
| 같은 실행 v0.6.0 대비 후보 | 04 | three-node/refresh/p95 | +8.440513% |
| 같은 실행 v0.6.0 대비 후보 | 04 | three-node/refresh/p99 | +6.088960% |
| 최초 대비 기준판 재측정 | 00 | single-node/sort_filter/p99 | +5.327863% |
| 최초 대비 기준판 재측정 | 00 | single-node/refresh/p99 | +5.614050% |

| 후보 반복 / 토폴로지 | 후보 ops/s | 최초 v0.6.0 대비 처리량 변화 | 짝지은 OpenSearch 2.19 ops/s | 처리량 배율 |
| --- | --- | --- | --- | --- |
| 01 / single | 754.0602 | +1.4871% | 285.5721 | 2.6405x |
| 01 / three | 920.2141 | -1.1978% | 117.2034 | 7.8514x |
| 04 / single | 743.5067 | +0.0667% | 291.9152 | 2.5470x |
| 04 / three | 925.1866 | -0.6639% | 116.8681 | 7.9165x |

- 반올림 전 값으로 5%를 판정했다. 최초 대비 최대 초과인 sort_filter p99는
  10.95857448875904→11.807869002223015 ms다. 기준판 자체 변동은 면제 근거가
  아니며, 같은 실행 비교/공개 기준 비교 중 유리한 값만 선택하지 않는다.
  이전 후보의 다른 전체 실행과 직접 비교해 타입 분리 단독의 속도 개선을
  주장하지 않는다. 중간 벡터 제거만으로 누적 성능 문제가 해결되지 않았다.
- 종료 후 소유 프로세스/비교 컨테이너 정리 확인, 사용자 컨테이너 유지.
  기능 증거는 engine 842/842, node 605/605, 통합 7/7, HTTP 버킷 36/36,
  bool 200/200, 코어 1180/1180이다. 기존 alias/PIT/중첩 집계 실패와 전체
  0/40 최종 수락 보류는 유지한다. 단일 변경의 원인 기여/최적화 불가가
  입증되지 않아 ledger 제외는 없으며 릴리즈하지 않는다.
- 다음 성능 작업에서는 최초/직전/현재 바이너리의 사전 고정 정렬 부하 대조로
  후보 타입 분리 효과와 기존 누적 정렬 비용을 구분한다. 결과 없이 중간 벡터나
  공유 캐시를 전체 회귀 원인으로 단정하지 않으며, 추가 구현 후 전체 비플러그인
  게이트를 재실행한다. 기존 기능 보강 계획과 최초 v0.6.0 기준은 바꾸지 않는다.

### P03: 세 버전 정렬 전용 대조와 CPU 진단

- 직전 turn은 타입 분리 구현 및 전체 기능/성능 검증을 완료한 progress다.
  이번에는 최초 v0.6.0 `db244133...`, 직전 `cbed6b36...`, 현재 `18c1bb3e...`
  바이너리와 실행 중인 소유 프로세스가 없음을 재확인했다.
- `target/core-replacement-c05/run-sort-versions-diagnostic.py`는
  `sort-versions-abccba/plan.json`에 최초/직전/현재/현재/직전/최초 순서와
  바이너리/실행 입력 해시, 모든 명령을 실행 전에 고정했다. 기존 matrix에서
  3노드, 각 60초, 5000문서, 384벡터 소스, 4클라이언트, 3샤드/replica 1,
  seed 13을 유지하고 작업만 sort_filter=100으로 한 별도 진단이다.
  전체 혼합 부하 게이트나 공개 v0.6.0 보고서를 변경한 것이 아니다.
- 총 397.1831초, 6회 모두 종료 0, 모든 요청 오류 0건.
  execution_inputs_verified=true, infrastructure error 없음.
  각 실행의 실제 3개 서버 전후 해시가 해당 바이너리와 일치했다.

| 실행 | 버전 | 처리량 ops/s | mean ms | p95 ms | p99 ms |
| --- | --- | --- | --- | --- | --- |
| 00 | 최초 v0.6.0 | 1421.9178 | 2.802755 | 4.867613 | 5.972351 |
| 01 | 직전 | 1433.1759 | 2.780796 | 4.803694 | 5.936260 |
| 02 | 현재 | 1433.5000 | 2.780203 | 4.796380 | 5.915172 |
| 03 | 현재 | 1428.1976 | 2.790419 | 4.830386 | 5.968965 |
| 04 | 직전 | 1427.9461 | 2.790861 | 4.813286 | 5.919985 |
| 05 | 최초 v0.6.0 | 1411.5702 | 2.823139 | 4.869375 | 5.996231 |

| 비교 쌍 | 처리량 변화 | mean 변화 | p95 변화 | p99 변화 |
| --- | --- | --- | --- | --- |
| 00→01 최초 대비 직전 | +0.791754% | -0.783487% | -1.313153% | -0.604296% |
| 00→02 최초 대비 현재 | +0.814550% | -0.804645% | -1.463408% | -0.957394% |
| 01→02 직전 대비 현재 | +0.022617% | -0.021324% | -0.152255% | -0.355244% |
| 05→04 최초 대비 직전 | +1.160122% | -1.143346% | -1.151873% | -1.271558% |
| 05→03 최초 대비 현재 | +1.177937% | -1.159003% | -0.800690% | -0.454715% |
| 04→03 직전 대비 현재 | +0.017611% | -0.015838% | +0.355275% | +0.827364% |

- 정렬 단독 조건에서는 최근 후보의 5% 이상 악화가 재현되지 않았고, 타입 분리
  전후 차이는 작다. 두 반복과 불리한 지표를 모두 보존했다. 이 관찰로 기존 혼합
  부하의 실패를 취소하거나 단일 변경 효과가 없다고 단정하지 않는다. 쓰기/refresh와
  다른 작업이 함께 있을 때의 상호작용을 다음 원인 분석 대상으로 좁힌다.
- plan SHA-256 `d4bd61215cb11a35c33bc77b2f45d706c7245e687c23610839335127d3c12307`;
  result `4b1bf7f1e7f204bacf5db7d29acb04ad1fb099cf06e42ed562ebf89eaf164de5`.
  6개 원본 보고서 해시는 result에 보존했다.
- 대조 종료 후 CPU 도구에 sort_filter 전용 선택을 추가했다. 기존 mixed 기본값과
  고정 workload/토폴로지/바이너리 확인은 유지한다. 도구 회귀 테스트를 추가했고
  `test_core_cpu_diagnostic.py` 및 `test_benchmark_failure_diagnostics.py` 총
  **12/12 통과**. 실행 로그 `sort-cpu-tool-tests.log` SHA-256:
  `a4c3352ba626bfd7c056ab4b7d7f35b98bd9ac851dad48df2cebe4c81fcab442`.
  도구 `15674028922ec9f8f8bac4cc8f6af584aa48f7380508a6719128bcf31b9a10e0`,
  테스트 `925f1e4995c861cba1a758e51df77dc6bca192b5840894a98feef07bfa804c06`.
- 별도 `typed-page-sort-cpu`에서 현재 바이너리로 45초 정렬 부하 중 20.7359초를
  cpu-clock 49Hz로 관찰했다. perf/matrix 종료 0, 유실 샘플 0, 바이너리 불변.
  부하 생성기 CPU 21.40초, 서버 4.43/4.42/8.23초(합계 17.08초)다.
  서버 샘플에 할당/해제, JSON 배열 복사, f64/JSON 직렬화가 나타났다.
  정렬 comparator가 주원인이라는 증거는 부족하며, 샘플 비율을 HTTP p99
  기여율로 환산하거나 프로파일러 측정치를 비프로파일 측정과 합치지 않는다.
- CPU diagnostic SHA-256:
  `2fafb427d396e2b0cbbe81abe48129e73a895e948d436dd3c3d90ecdb2281e90`;
  perf.data `ca0fb3d8fff09114e19d4cf84223d39cccbf25ad0ee5c5ab75aa01d5ae3f155f`;
  server-self.txt `a1684ad62494fcac8bd960c092fd0f012cf55b8304713ddbf1eab60cf52887dc`.
- 다음 진단은 정렬+쓰기 및 정렬+쓰기+refresh 조합을 사전 고정하고, 원래 혼합
  부하의 비율(정렬10/쓰기15/refresh5)을 유지한 조건에서 최초/현재 후보를
  균형 순서로 대조한다. refresh 단독 무변경 인덱스의 no-op 결과로 실제
  쓰기 후 refresh 비용을 설명하지 않는다. 진단은 정식 게이트를 대신하지 않는다.
- 이번 turn에는 런타임 코드를 바꾸지 않았다. 최신 정식 전체 성능 실패와
  0/40 최종 수락 보류를 유지한다. 최적화 불가가 입증되지 않아 ledger 제외는
  없다. 소유 프로세스/비교 컨테이너 종료 확인, 사용자 컨테이너 유지.

### P03: 정렬·쓰기·refresh 상호작용 대조

- 직전 turn은 정렬 전용 세 버전 비교와 CPU 진단을 완료한 progress다.
  이번에는 현재 `18c1bb3e...` 및 고정 v0.6.0 `db244133...` 바이너리,
  실행 중 소유 프로세스가 없음을 재확인했다.
- `target/core-replacement-c05/run-sort-write-interaction.py`가
  `sort-write-interaction/plan.json`에 8회 순서/조건/비교 쌍과 실행 입력 해시를
  사전 고정했다. 정렬10/쓰기15 조건의 비교는 00→01, 07→06;
  정렬10/쓰기15/refresh5 조건은 03→02, 04→05다. 각 쌍은 기준판→현재다.
  3노드, 3샤드/replica 1, 5000문서, 384벡터 소스, 4클라이언트, seed 13,
  각 60초와 기존 matrix 설정을 유지했고 프로파일러/빌드/다른 부하를 겹치지 않았다.
- 8회 모두 종료 0, 모든 요청 오류 0건. 총 528.5569초,
  execution_inputs_verified=true, infrastructure error 없음.
  모든 실행에서 실제 3개 서버의 전후 해시도 해당 바이너리와 일치했다.

| 실행 | 버전 | refresh | 처리량 ops/s | 정렬 p99 ms | 쓰기 p99 ms | refresh p99 ms |
| --- | --- | --- | --- | --- | --- | --- |
| 00 | v0.6.0 | 없음 | 1266.5904 | 6.670013 | 5.916770 | 해당 없음 |
| 01 | 현재 | 없음 | 1271.9882 | 6.563741 | 5.837199 | 해당 없음 |
| 02 | 현재 | 포함 | 797.1449 | 16.433839 | 8.546616 | 25.284776 |
| 03 | v0.6.0 | 포함 | 809.3089 | 16.528286 | 8.316247 | 24.612755 |
| 04 | v0.6.0 | 포함 | 818.4606 | 15.562866 | 8.355989 | 24.022934 |
| 05 | 현재 | 포함 | 809.4516 | 15.820645 | 8.519510 | 25.505731 |
| 06 | 현재 | 없음 | 1285.7538 | 6.500738 | 5.793051 | 해당 없음 |
| 07 | v0.6.0 | 없음 | 1277.6411 | 6.553527 | 5.883955 | 해당 없음 |

| 비교 쌍 | 작업 | mean 변화 | p95 변화 | p99 변화 |
| --- | --- | --- | --- | --- |
| 00→01 | sort_filter | -0.524928% | -0.687188% | -1.593276% |
| 00→01 | write | -0.351717% | -0.734743% | -1.344840% |
| 07→06 | sort_filter | -0.755391% | -0.776085% | -0.805498% |
| 07→06 | write | -0.540284% | -1.126959% | -1.544947% |
| 03→02 | sort_filter | +1.347103% | +0.226076% | -0.571422% |
| 03→02 | write | +1.402030% | +1.960658% | +2.770100% |
| 03→02 | refresh | +1.791460% | +1.906688% | +2.730379% |
| 04→05 | sort_filter | +0.567446% | -0.886720% | +1.656373% |
| 04→05 | write | +1.938455% | +2.809686% | +1.956928% |
| 04→05 | refresh | +0.815299% | +0.767804% | +6.172422% |

- 각 쌍의 처리량 변화는 순서대로 +0.426170%, +0.634977%, -1.503016%,
  -1.100716%다. 5% 이상 악화는 04→05 refresh p99 한 항목이며
  24.02293398045003→25.505730791483074 ms다. 좋은 반복을 선택하거나 평균으로
  실패를 상쇄하지 않는다. refresh 요청은 실제 쓰기와 함께 발생했으며
  현재 후보의 두 실행에서 각각 7956/8072건 수행됐다.
- 정렬+쓰기만 있는 조건은 현재 후보가 약간 빨랐고, refresh 추가 시 두 버전
  모두 정렬 지연이 증가했다. 그러나 작업 비율/검색 가능 데이터/완료 요청 수가
  달라지므로 두 조건의 차이를 refresh 자체의 고유 비용으로 환산하지 않는다.
  현재 후보의 정렬 p99 누적 5% 초과는 이 축소 조합에서도 재현되지 않았다.
  기존 전체 혼합 부하 실패를 취소하지 않으며 단일 변경을 원인으로 확정하지 않는다.
- 코드상 plain 검색 snapshot 생성은 store read lock을, refresh 계획 수립은
  같은 store의 write lock을 사용한다. 이는 조사할 경계일 뿐 관찰된 HTTP p99의
  원인 증명이 아니다. 다음 성능 분석은 전체 혼합 부하에서 refresh 계획/게시
  및 검색 snapshot 락 대기 시간을 분리해 관찰하는 방향으로 제한한다.
  계측 오버헤드가 있는 실행은 진단으로만 표시하고, 안전한 snapshot 게시나
  세대/삭제 보호를 완화하는 방식은 사용하지 않는다.
- plan SHA-256 `7f1f4dc314e6e9e4a7a66d42695ce73ec5b6c23be95f7cb83806e5d0f300aebc`;
  result `09612171903a07f66ceb0a598eb30866baeca7d741c5878047c0bc34fd11e8a1`.
  8개 원본 보고서 및 각각의 SHA-256은 result에 보존했다.
- 이번 turn은 진단만 수행했으며 런타임 수정/새 전체 게이트는 없다.
  정식 최신 결과는 typed-page 전체 반복의 실패다. 최적화 불가와 단일 기능의
  원인 기여가 입증되지 않아 ledger 제외는 없고 전체 0/40 수락 보류를 유지한다.
  기능 보강 범위도 축소하지 않는다. 소유 프로세스/비교 컨테이너는 종료했고
  사용자 컨테이너는 유지했다.

### P03: futex 추적 시도와 계측 한계

- 진행률 보고 후 검색/refresh 락 경로 조사를 이어갔다. 제품 코드와 바이너리는
  변경하지 않았고, 현재 후보는 `18c1bb3e...`를 유지한다. 전체 수락은 0/40이며
  이는 구현량 0%가 아니라 단위별 전체 수락 조건 미충족을 뜻한다.
- `tools/run-core-cpu-diagnostic.py`에 소유 서버만 대상으로 하는 futex 프로파일을
  추가했다. 부하 생성기는 제외하고 전역 추적은 사용하지 않는다. CPU 모드의
  기존 대상과 49Hz 설정은 유지한다. 진단 도구/실패 진단 테스트 15/15 통과,
  `git diff --check` 통과. 제품 런타임 변경이나 새 전체 게이트는 없다.
- 현재 후보/3노드/전체 혼합 비율/5000문서/384벡터/4클라이언트 조건에서
  아래 세 진단을 시도했다. 모두 수락 근거에서 제외한다.

| 경로 (target/core-replacement-c05 아래) | 추적 조건 | 결과 |
| --- | --- | --- |
| typed-page-mixed-futex | WAIT/WAIT_BITSET 커널 필터 | 필터 설정 EPERM, perf 255; matrix 0 |
| typed-page-mixed-futex-all | 전체 futex, 이벤트 주기 1 | 35초 timeout; 약 1.5G 불완전 기록 |
| typed-page-mixed-futex-sampled | 전체 futex, 이벤트 주기 100 지정 | 35초 timeout; 약 1.3G 불완전 기록 |

- 이벤트 자체는 별도 `perf stat` 점검에서 수집 가능했다. 따라서 첫 실패를
  futex 이벤트 전체 접근 불가로 일반화하지 않는다. 이후 기록량이 컸지만
  timeout의 정확한 원인은 확정하지 않는다. 주기 100을 지정했더라도 실제
  기대한 비율로 샘플링되었다고 검증한 것은 아니다. 불완전 기록의 스택/횟수로
  락 병목이나 회귀 원인을 주장하지 않는다. futex 진입은 wait/wake를 포함하며
  정상 수집하더라도 실제 blocked duration 또는 HTTP p99를 직접 뜻하지 않는다.
- 두 번째 실행 후 남은 소유 perf를 명시적으로 종료했다. 도구에는 별도
  프로파일러 세션과 timeout 시 해당 세션 종료, diagnostic.json의 오류 기록을
  추가했다. 세 번째 실행은 정리 경로를 거쳤으며 종료 후 perf/steelsearch/java
  프로세스가 없음을 확인했다. 실패 원본은 보존한다.
- 코드 검토상 `refresh`의 계획 수립과 결과 게시가 store write lock을 사용하고,
  게시 구간에는 증분 문서/벡터 인덱스 갱신이 포함된다. plain 검색 snapshot은
  같은 store의 read lock에서 생성된다. 이는 조사할 후보 경계일 뿐 병목 증명이
  아니다. 다음 단계는 별도 진단 빌드에서 이 세 구간의 락 획득 대기 시간과
  보유 시간을 분리 계측하고 오버헤드를 명시하는 것이다. 정식 릴리즈 바이너리와
  분리하며 세대/삭제 검증 및 snapshot 보호를 완화하지 않는다.
- 세 diagnostic.json SHA-256은 표 순서대로
  `1497060484b6235534e3575de7ba23c0374e08e6cabcf65555f79b624b92b769`,
  `cf97fe1462a65f2555cfe2ca255f9d043384c0d0b25545c15429322aaa47e063`,
  `a1334612c2617fe8454eec89b645317e3b56d8eaadfae9c77177a747b50a95ce`.
- 최신 정식 판정은 typed-page 전체 반복 실패 그대로다. 진단 실패를 기능 제외
  근거로 사용하지 않으며 ledger는 비어 있다. 릴리즈/태그/커밋/푸시는 하지 않았다.

### P03: 분리 빌드의 직접 락 계측

- 직전 turn은 추적 실패 범위를 확인하고 도구를 보강한 progress다. 이번에는
  perf 추적을 반복하지 않고 `os-engine-tantivy/diagnostic-lock-timing` feature로
  직접 계측했다. 기본 standalone 의존성 트리의 engine features=[]를 확인했다.
  기본 경로는 기존 lock 획득 코드를 유지하고 진단 모듈은 cfg로 제외된다.
  기본 바이너리를 재빌드해 바이트 동일성을 검증한 것은 아니다.
- `diagnostic_lock.rs`는 search_snapshot, refresh_plan, refresh_publish,
  refresh_owner 각각의 64번째마다 한 호출을 계측한다(최초 호출 포함).
  획득 호출 소요와 획득 후 해제 직전까지의 시간을 구분한다. 기록 대상 락을
  해제한 뒤 stderr를 출력한다. refresh_owner 안의 계획/게시 계측 출력은
  바깥 owner 보유 시간에 영향을 줄 수 있다. 원자 카운터/시계/출력 비용과
  주기적 샘플링 편향을 인정하며 운영 성능 수치로 사용하지 않는다.
- 가드 테스트 3/3(샘플 주기, 변경/해제, early return, poison 전파) 통과;
  feature를 켠 엔진 전체 845/845, ignored=0, 9.28초. 로그 집계 테스트 3/3
  통과(노드/구간 분리, 부정확한 값/중복/빈 표본 거부, 미계측 호출 추정 금지).
  `git diff --check` 통과. 기존 엔진 안전 검증/세대/삭제/refresh 의미는 완화하지 않았다.
- 별도 빌드 명령:
  `env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 cargo +nightly build --release --target-dir target/lock-diagnostic -p os-node --bin steelsearch --features standalone-runtime,os-engine-tantivy/diagnostic-lock-timing`.
  7분 39초에 성공. 진단 바이너리 SHA-256은
  `b8345d2bdf499cc5e8f1a9031acabb991209cc312e839f65c588bb2c346367f4`.
  기존 candidate `18c1bb3e...`, 고정 v0.6.0 `db244133...` 해시는 그대로다.
- `target/core-replacement-c05/run-lock-timing.py`가 `lock-timing-mixed/plan.json`에
  입력/명령/진단 바이너리 해시를 고정했다. 3노드, 3샤드/replica 1,
  5000문서/384벡터 소스/4클라이언트/seed 13/기존 전체 혼합 비율, 60초.
  실행 중 빌드/다른 벤치마크/perf는 없었다. 총 66.106949초, matrix 종료 0,
  요청 55,923건 모두 성공, 입력 전후 검증 및 실제 3개 서버 전후 해시 검증 성공.
  계측된 처리량 932.009525 ops/s는 진단 참고값일 뿐 이전 릴리즈와의 개선율로
  사용하지 않는다. 이 한 토폴로지의 계측 실행은 전체 성능 게이트가 아니다.

| 계측 구간 | 샘플 수 (3노드 합) | 표본 평균 대기 us | 표본 최대 대기 us | 표본 평균 보유 ms | 표본 최대 보유 ms |
| --- | --- | --- | --- | --- | --- |
| refresh_owner | 54 | 0.058519 | 0.120 | 6.288852 | 25.303720 |
| refresh_plan | 54 | 0.055556 | 0.200 | 0.021763 | 0.355963 |
| refresh_publish | 40 | 0.074000 | 0.240 | 0.119817 | 0.707646 |
| search_snapshot | 668 | 0.075150 | 0.440 | 0.011555 | 0.096841 |

- 총 816개 표본과 노드별 합/최대/원본 로그 해시는 result에 보존했다. 표에는
  준비 단계가 포함되며, HTTP 작업별 p99나 모든 호출의 분포가 아니다.
  이 표본에서 ms 단위 락 획득 대기는 관찰되지 않았다. 표본 밖 드문 경합 또는
  계측하지 않은 상위 락/스케줄링 대기의 부재를 증명한 것은 아니다.
  refresh_owner는 refresh 전체 작업을 보호하므로 긴 보유 시간 자체가
  이 mutex에서 대기 중인 요청이 있었다는 뜻도 아니다.
- 기존 resource_usage의 refresh 누적 타이머 delta는 commit 11,771,217,669 ns,
  doc_id_lookup 911,572,032 ns, document_add 335,582,575 ns,
  reload 337,566,345 ns였다. `/_nodes/stats`의 같은 이름 숫자 필드를 재귀 합산하는
  수집기이므로 집계 범위/중복 및 병렬 샤드 시간을 먼저 확인해야 한다.
  이 합을 HTTP 경과 시간 비율로 환산하거나 단일 기능 회귀 원인으로 단정하지 않는다.
- 다음 단계는 해당 타이머의 노드/인덱스 집계 범위를 검증한 뒤 refresh commit
  및 artifact 생성 경로를 우선 조사하는 것이다. 기존 store 락을 제거하는 작업은
  근거가 없어 진행하지 않는다. 실제 최적화 후에는 고정 v0.6.0 대비 전체 반복
  게이트와 기능 검증을 다시 수행한다. 이번 진단으로 기존 실패를 취소하지 않는다.
- plan SHA-256 `6b08cef97fa474b2ec1911e159fd6672a9a6c922392e46fce6b81e26305c2a02`;
  result `c3f88125601685e0abfd1182ee0d947ace03b9d3f9d007222ecba62304125acf`;
  엔진 테스트 로그 `18b1ecd762fa831d0c5634b37953863b7c01a13cb14b6fa47737af40c7162733`.
  engine lib 소스 `b7146ec18312e004fa01bb21b9512680ed27d3511028c2b69d7189fda9420197`;
  진단 모듈 `a64863e7ba737a133b3f724d77319ed434328a7c8e0d617e3f8094d31c09fd8d`.
- 전체 수락 0/40 및 빈 ledger를 유지한다. 진단 전용 변경이며 새로운 정식
  전체 성능 판정/릴리즈/태그/커밋/푸시는 없다. 종료 후 소유
  cargo/rustc/steelsearch/java/perf 프로세스가 없음을 확인했다.

### P03: refresh 타이머 범위 검증과 commit 경로 조사

- 직전 turn은 직접 계측으로 락 조사 방향을 좁힌 progress다. 이번에는
  `nodes_stats_body` 및 engine의 `search_cache_telemetry_snapshot`을 확인했다.
  응답한 로컬 노드의 engine 인덱스별 카운터를 한 번씩 더한 값이 로컬 노드의
  `steelsearch.search_cache`에 들어간다. cluster view의 다른 노드들은 같은
  자리에 빈 객체를 받는다. 이 경로는 원격 노드 통계를 수집하지 않는다.
- 따라서 직전 진단의 commit 11,771,217,669 ns는 응답 로컬 노드의 값이며
  3노드 전체 commit 합계가 아니다. 로컬 카운터가 cluster view의 노드 수만큼
  복제된 값도 아니다. 이 응답에서 refresh 네 카운터가 배치되는 경로는 하나다.
  수집기의 일반적인 재귀 합산 방식은 다른 응답 구조에서 여전히 주의가 필요하다.
- `nodes_stats_refresh_counters_are_local_index_totals_not_cluster_totals`를 추가했다.
  두 인덱스에 실제 쓰기/refresh를 수행해 commit 카운터가 양수임을 확인한 다음,
  로컬 노드가 사전순 첫 번째가 아닌 3노드 view에서 네 refresh 카운터가 로컬
  engine snapshot과 같고 두 원격 노드는 빈 객체임을 REST 응답으로 검증한다.
  통계의 현재 한계를 고정하는 테스트이며, 원격 통계 지원을 구현했다는 뜻이 아니다.
- 처음 `--bin steelsearch`로 실행한 필터는 해당 테스트를 포함하지 않아 0건이었다.
  이를 통과 근거로 사용하지 않고 `--lib`로 바로잡았다. 새 테스트 1/1 통과,
  이후 `env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 cargo +nightly test -p os-node --lib --features standalone-runtime`
  전체 606/606 통과, ignored=0, 실행 4.50초. `git diff --check` 통과.
- engine의 네 타이머는 `TantivySearchState::append_documents`에서만 측정한다.
  full artifact는 기본값(0) timing을 기록하고 `build_from_documents`의 commit은
  이 타이머로 측정하지 않는다. 성공적으로 적용된 artifact의 시간이 합산되며
  병렬 샤드 구간은 서로 겹칠 수 있다. 따라서 refresh 전체 비용이나 HTTP 요청당
  commit 평균/비중으로 직접 해석하지 않는다.
- 로컬에 설치된 Tantivy 0.21.1 소스의 `IndexWriter::prepare_commit`은 문서
  채널을 교체하고 기존 indexing worker를 join한 뒤 새 worker를 만든다.
  `Index::writer`는 총 메모리를 작업자당 최소 15,000,000 bytes로 나누므로
  현재 16 MiB 설정은 이미 샤드당 indexing worker 1개다. 작업자 수를 1로
  명시하는 변경은 이 환경에서 작업자 수를 줄이지 않는다. 이 코드 경로의 존재가
  관찰된 p99 회귀 원인 또는 최적화 불가를 증명하지는 않는다.
- 현재 근거로 commit/refresh 횟수나 가시성 경계를 변경하지 않는다. 이미 빈
  pending_documents의 증분 commit은 건너뛴다. 단순한 작업자 수 조정이나
  안전 보호 제거도 하지 않는다. 무근거 성능 조정 대신 다음 C05 작업은 기존
  실패가 재현된 alias 필터 범위 전달을 다룬다: resolver가 이름만 반환하며
  count/search에서 필터 범위가 소실되는 경계를 먼저 고정하고, hits/count/집계의
  global 범위/PIT 생성 시점 필터를 함께 보존하는 계약으로 구현한다.
  query wrapper 또는 결과 후처리만으로 범위를 축소해 완료 처리하지 않는다.
  해당 구현 후에는 기존 5% 초과 항목을 포함한 전체 반복 게이트를 재실행한다.
- 새 테스트 로그 SHA-256
  `f21fd6bbc7d66e3e2b4c2713057ef4f3b117dfc91a255b88958a5b515bae4d0d`;
  전체 노드 테스트 로그
  `6226ec6a12257e45799a0f2ddd9dc844717745701b308bd5a28733cec33164c6`.
  standalone 소스(테스트만 추가)
  `b861d47a82e4bdbb2cbe231317c9ecf2d7ad885b9cfa96f61033e701cd9cd159`.
- 제품 동작 변경/새 성능 실행은 없다. 후보 바이너리 `18c1bb3e...`를 재확인했다.
  최신 정식 전체 게이트 실패, 전체 수락 0/40, 빈 ledger를 유지하며
  소유 cargo/rustc/steelsearch/java/perf 프로세스가 없음을 확인했다.

### C05: alias 필터 범위 resolver 준비

- 직전 turn은 refresh 통계 경계를 검증한 progress다. 이번에는 재현된 alias
  필터 누락의 앞단을 구현했다. 기존 resolver는 이름만 반환하고 count는 그 이름으로
  엔진 요청을 만들며 PIT context도 현재 인덱스 목록만 저장한다. 따라서 count만
  query wrapper로 바꾸는 작업은 검색/집계/PIT 전체 계약을 충족하지 못한다.
- `ResolvedSearchTargets`는 인덱스 목록과 인덱스별 필터 map을 보존한다.
  map에 없는 인덱스는 unrestricted다. `resolve_search_targets_with_alias_filters`는
  이름과 필터를 같은 metadata lock 안에서 읽는다. alias 이름별로 중복을 제거하고
  정렬한 뒤 OR(`minimum_should_match: 1`)로 결합한다. 직접 인덱스/데이터 스트림,
  무필터 또는 null 필터 alias는 선택 순서와 무관하게 해당 인덱스 제한을 해제한다.
  다른 인덱스의 필터는 합치지 않는다. 미지원 query 원문도 보존하며 파싱 실패를
  unrestricted로 바꾸지 않는다. 실제 query 검증/오류 응답 연결은 다음 단계다.
- 기존 이름 전용 resolver는 공통 `resolve_search_targets_recording::<false>`를
  사용한다. 이 경로에서는 필터 기록 분기와 필터 clone이 꺼져 있다. 실제
  릴리즈 성능이 동일하다고 검증한 것은 아니며 새 바이너리/전체 게이트는 아직 없다.
- 새 테스트 3/3 통과: 필터 OR/alias 반복/선택 순서, 직접·무필터 우선권,
  인덱스별 분리, 메타데이터 변경 후 이전 결과의 필터 보존, 미지원 query 원문 유지,
  160개 selector/options 조합에서 이름·오류 응답 경로 일치. 이 옵션 비교는
  기존 의미 보존 검사이며 OpenSearch 전체 옵션 정합성을 새로 증명한 것은 아니다.
  필터 소유권 테스트도 PIT 수명/삭제·재생성 계약의 end-to-end 증명은 아니다.
- 로컬 OpenSearch 참조 소스의 `IndexNameExpressionResolver.indexAliases`,
  `AliasMetadata.filteringRequired`, `ShardSearchRequest.parseAliasFilter`에서
  직접 인덱스/무필터 우선권 및 OR 결합 규칙을 확인했다. 새 HTTP 참조 실행은 없다.
- `env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 cargo +nightly test -p os-node --lib --features standalone-runtime`
  전체 609/609 통과, ignored=0, 4.61초. `git diff --check` 통과.

#### 남은 연결 및 수락 조건

1. 준비된 resolver 결과를 count/search 및 PIT 생성 시점에 연결한다. 서버가 해석한
   필터를 전달하고 클라이언트 본문 필드로 범위를 대체하거나 해제할 수 없게 한다.
   PIT는 생성 시점 필터를 소유하고 이후 alias 변경/삭제와 분리해야 한다.
2. 엔진의 인덱스별 문서 범위로 적용한다. native 및 fallback의 hits/total/count,
   일반·global 집계, 점수/BM25 모집단, 정렬·페이지네이션, query/post_filter와의
   관계를 함께 검증한다. global이 query는 무시해도 alias 범위는 벗어나지 않아야 한다.
   filtered snapshot으로 BM25 모집단을 무조건 축소하는 방식도 동등성 확인 없이 쓰지 않는다.
3. multi-index·alias 조합, PIT alias 변경, transport·scroll 경로까지 참조 HTTP
   fixture와 회귀 테스트로 검증한다. 결과 후처리 또는 count만 수정한 상태를
   전체 구현으로 수락하지 않는다.
4. 연결된 구현 단위마다 기본 release를 재빌드하고 전체 non-plugin 반복 벤치마크를
   실행한다. 최초 v0.6.0 대비 각 항목 누적 5% 조건을 적용하며 기존 실패도 유지한다.
   초과는 원인 조사/최적화 후 전체 재실행; 단일 구현의 5% 이상 악화와 최적화 불가가
   입증된 경우에만 ledger 등록·제외한다. 현재 resolver 준비를 완료 단위로 세지 않는다.

- 테스트 로그 SHA-256
  `a6372eaf489f7f6d2116a1fb59c82914c1d805a2efa813520d72dd6157d48ebd`;
  전체 노드 테스트 로그
  `2184ec7f0fedcb2863d0c1fbbff04c9c0deb5076a1899371f3ed58497c4e940c`;
  standalone 소스
  `99107254c203d296a2117c9e89d41dda61d04e0689ab211b7059335825017d88`.
- 실제 REST 검색 호출은 아직 이름 전용 resolver를 사용한다. 따라서 기존 alias
  필터 실패가 해결됐다는 주장은 하지 않는다. 후보 바이너리는 `18c1bb3e...`로
  보존했고 새 소스 빌드/전체 성능 판정은 남아 있다. 전체 수락 0/40 및 빈 ledger,
  기존 정식 게이트 실패를 유지한다. 릴리즈/태그/커밋/푸시는 하지 않았다.

### C05: 엔진 alias 범위와 global 입력 연결 (진행 중)

- 직전 turn은 resolver와 범위 계약을 준비한 progress다. 이번에는 기존 내부
  shard-scope envelope 패턴을 따라 `_steelsearch_alias_filters`를 엔진에 추가했다.
  인덱스별 query를 엄격히 파싱하고 잘못된 map/query는 오류로 반환한다.
  scoped 요청은 무필터 request cache와 plain snapshot 빠른 경로를 사용하지 않고
  기존 request-filter 수집 경로에서 문서별 alias 조건을 먼저 적용한다.
  원본 index/reader와 BM25 모집단을 필터로 잘라 새로 만들지 않는다.
- 이 엔진 경로는 hits/total/count를 alias 범위 안에서 수집한다. query/min_score
  적용 문서는 일반 집계로, alias와 slice 범위의 전체 문서는 global 입력으로
  구분하며 post_filter는 hits에만 적용한다. 반환된 페이지를 사후 필터링하는
  방식이 아니다. scoped 경로는 현재 문서 순회/소스 materialization 비용이 있으며
  native 빠른 경로와의 비용 동등성 또는 누적 5% 충족은 검증하지 않았다.
- 최초 새 테스트 0/3 실패를 보존했다. global 실패는 REST 원문을 엔진 직접
  호출에 사용한 테스트 형식 오류였다. 엔진의 기존 내부 `plugin(kind=global)`
  집계 표현으로 고쳤으며 이는 외부 플러그인 지원을 추가한 것이 아니다.
  실제 REST 정규화와 연결되는 검증은 아직 남아 있다.
- 3샤드 텍스트 점수 차이는 실제 결함이었다. `field_is_text`가 단일 search_state만
  조회해 다중 샤드 request-filter 경로에서 BM25 보정을 건너뛰었다. shard search
  state도 조회하도록 고쳤고, alias 적용 전후 해당 문서의 점수 비트가 같은지
  1/3샤드에서 확인했다. 모든 query/분산 scoring 조합의 동등성 증명은 아니다.
- 수정 후 2/3 통과, 남은 테스트는 명시적 빈 shard 집합이 제한 없음으로
  소실되는 문제를 드러냈다. parser가 유효한 빈 배열을 빈 집합으로 보존하도록
  수정해 alias 범위와의 교집합이 0 hits/0 global 문서가 되게 했다.
  malformed shard-scope 전체 형식의 fail-closed 검증을 완료한 것은 아니다.
- 최종 새 테스트는 4개이며 전체 엔진 846/846 통과, ignored=0, 9.52초다.
  일반/global 집계와 query/post_filter, size=0/10, 1/3샤드, 인덱스별 alias 조건,
  무필터 인덱스 혼합, 빈 shard 범위, 잘못된 alias filter 거부, 기존 텍스트 점수,
  match_none에서도 유지되는 global 범위, slice 분할 및 red/blue/red 요청 간
  범위 격리를 검사한다. 전체 노드 609/609 통과, ignored=0, 6.26초.
  `git diff --check` 통과.
- 참조 소스 `DefaultAggregationProcessor`는 global을 match-all에
  `DefaultSearchContext.buildFilteredQuery`를 적용해 실행하며, 그 안에서 alias와
  slice 조건을 유지한다. 이를 따라 global 입력을 slice 뒤에서 수집했다.

#### 수락 전 남은 필수 경계

- `SignificanceLookup`의 기본 background는 alias 제한된 global 입력과 다르며
  index reader 모집단과 선택적 background_filter를 사용한다. 현재 엔진의
  `all_hits` 인자를 global과 significant_terms 계열이 함께 사용하므로, 이번의
  alias 제한 scope_hits만으로 significance 배경 통계까지 구현했다고 볼 수 없다.
  다음 단계는 global 문서 범위와 significance 배경 모집단을 분리하고 혼합/중첩
  집계 fixture로 검증하는 것이다. 이 알려진 미완성 경계를 해결하기 전 전체
  집계 정합성이나 alias 기능 완료를 주장하지 않는다.
- 이어서 resolver의 서버 유래 범위를 REST count/search, transport/fallback 및
  PIT 생성 시점에 연결해야 한다. 원문 본문에서 내부 범위를 신뢰하거나
  클라이언트 값으로 서버 범위를 덮어쓰지 않는다. alias 변경 이후 PIT의 범위
  유지, nested/rescore/scroll 및 일반 native 경로의 동등성도 검증 대상이다.
- 연결된 C05 구현 단위를 완료하기 전 기본 release 재빌드, 참조 HTTP 실행,
  전체 non-plugin 반복 벤치마크가 필수다. 현재 단계는 그 단위의 진행 중 작업이며
  집중 테스트를 전체 게이트 대신 사용하지 않는다. 기존 누적 5% 초과 항목도
  새 전체 게이트에서 다시 비교한다. 기능 제외/예외는 아직 없다.

- 엔진 소스 SHA-256
  `3c3da5f91fc0562f453a4f34e55e6134f65cec92632126e0ad533ecc861369fe`;
  전체 엔진 테스트 로그
  `c4de0bb6c0d23639b1e68eff504c8eade104f20d65ac3dfbc6a98a211cdb3891`;
  전체 노드 테스트 로그
  `2fa8dc1a86cea9d2d47c27627089ae6723326046a6a7d4335c8995893ddd8a00`.
  최초/중간 실패 로그는 각각 `alias-filter-engine-tests.log`,
  `alias-filter-engine-corrected-tests.log`로 보존했다.
- 기본 release 바이너리는 기존 `18c1bb3e...`이며 이번 소스를 반영한 release
  빌드/전체 성능 실행은 아직 없다. 실제 REST alias 실패가 해결됐다고 주장하지
  않는다. 전체 수락 0/40, 빈 ledger, 기존 정식 게이트 실패를 유지한다.

### C05: significance 기본 배경과 global 범위 분리 (진행 중)

- 직전 turn은 엔진 alias 범위/회귀 수정을 추가한 progress다. 이번에는 global
  입력과 significance 배경을 같은 all_hits로 전달하던 경계를 분리했다.
  request-filter 경로는 significance 계열이 있는 경우에만 별도 background_hits를
  수집한다. 이 문서들은 선택된 인덱스·샤드의 refreshed view이며 alias/user query/
  post_filter/slice 적용 전이다. global 입력은 기존 alias·slice 범위를 유지한다.
- 집계 수집기와 내부 bucket 수집기에 선택적 배경 문서 참조를 추가했다. 기존
  비범위 호출부는 원래 시그니처의 wrapper와 None을 사용한다. 범위 호출은
  typed SignificantTerms 및 내부 significant_terms/significant_text carrier의
  배경으로 별도 문서를 사용하고, 두 집계 재귀 지점과 14개 bucket 하위 집계
  재귀 지점으로 같은 참조를 전달한다. 하위 버킷 문서가 배경으로 대체되지 않는다.
  기본 배경 변경을 모든 native/document 집계 경로로 확대했다고 주장하지 않는다.
- 새 회귀 테스트는 1/3샤드 및 slice 유무에서 root significant_terms, 내부
  significant_terms carrier, global 하위 significance, terms 하위 significance,
  terms→filter→significance를 함께 확인한다. alias 범위 2문서, query 결과 1문서,
  배경 3문서와 red bucket 배경 빈도 2를 서로 구별한다. slice가 foreground/global을
  제한해도 배경 수는 3으로 유지되는지 검사한다. 기존 alias 테스트 포함 5/5 통과.
- 전체 엔진 847/847 통과(ignored=0, 9.23초), 전체 노드 609/609 통과
  (ignored=0, 4.79초), `git diff --check` 통과. 소유 실행 프로세스가 없음을 확인했다.
- 현재 배경은 visible StoredDocument 기반이다. OpenSearch SignificanceLookup의
  reader.maxDoc/docFreq와 삭제된 문서·nested 문서·분산 reduce까지 정확히 같다는
  증거는 아니다. 명시적 background_filter도 이번에 구현하지 않았다. 해당 옵션의
  파싱/적용/오류 처리와 reader 통계 차이를 검증하는 작업이 다음 필수 경계다.
  typed/내부 carrier의 전체 significance 기능 수락으로 범위를 축소하지 않는다.
- 이어서 서버 유래 alias 범위의 REST count/search, PIT 생성 시점, transport/
  fallback 연결 및 HTTP 참조 검증이 필요하다. 현재 REST resolver 호출은 아직
  이름 전용이므로 기존 end-to-end alias 실패가 해결됐다는 주장은 하지 않는다.
- 소스 SHA-256 `c426bc2648019524687348adfc9cffee64c9939c223cbbb7236a9155683dd3a4`;
  범위 테스트 로그 `fc3eecb9d7e54044b22dd437d3eab4cdea8f3e9b9fb34a21c7c81f8631e0bb5f`;
  전체 엔진 로그 `380f8273542d1830e141eb83b78375e7bfedf90d92127196600c08382bda932a`;
  전체 노드 로그 `647ad1f0755c1ffac8e991c1e3105d7cabdf363c29bf8bb650a2202e00354b94`.
- release 바이너리는 `18c1bb3e...`로 보존했다. 이번 소스의 release 재빌드/전체
  성능 실행은 아직 없고 C05 구현 단위는 미완료다. 연결된 단위를 수락하기 전
  전체 non-plugin 반복 게이트와 고정 v0.6.0 대비 누적 5% 검증을 수행한다.
  기존 전체 게이트 실패, 수락 0/40 및 빈 ledger를 유지한다. 릴리즈/태그/커밋/
  푸시는 하지 않았다.

### C05: REST count의 서버 유래 alias 범위 연결 (진행 중)

- 직전 turn은 기본 significance 배경을 분리한 progress다. 이번에는 집계를
  수행하지 않는 `_count`부터 서버 유래 alias 범위를 연결했다. significance의
  명시적 background_filter 및 reader 통계 검증을 생략하거나 수락한 것은 아니다.
- count는 인덱스 목록과 필터를 같은 metadata lock에서 해석한 결과를 사용한다.
  기존 count의 selector별 빈 와일드카드 허용 및 최종 empty 처리 차이는 공통
  resolver의 count 전용 모드로 유지한다. 이름 전용 검색 및 일반 scoped resolver는
  기존 모드를 유지한다. 36개 selector/options 조합을 기존 count 해석 절차와
  비교했다. 이 검사는 기존 동작 보존이지 OpenSearch 전체 옵션 정합성 증명이 아니다.
- `standalone_native_search_request_with_alias_filters`는 필터를 별도 인자로 받는다.
  서버 필터가 있으면 새 내부 query envelope를 구성하고 서버 map을 넣는다.
  요청 본문의 예약 이름 필드를 필터 원본으로 사용하지 않는다. 기존 요청 생성기는
  빈 필터 map으로 위임하며 일반 검색 경로는 아직 alias 범위를 전달하지 않는다.
- 새 REST handler 테스트 3/3 통과. 1/3샤드에서 filtered alias, 여러 인덱스에 걸친
  alias, alias 와일드카드, 중복/선택 순서, 직접 인덱스·무필터 alias 우선권,
  직접 인덱스와 filtered alias 혼합, match query와의 교집합, 라우팅 결과를 검증했다.
  root 본문의 위조 내부 필터는 서버 범위를 해제하지 못하며 query 내부의 위조
  envelope는 400이다. refresh 전후 문서 가시성과 잘못된 저장 alias query의 400도
  확인했다. 이는 in-process REST handler 테스트이며 새 live HTTP 참조 실행은 아니다.
- 전체 노드 612/612 통과, ignored=0, 4.60초. `git diff --check` 통과.
  source SHA-256 `43056c51ffcbc53703933cfd724e078b4fc980b5cba8c27b04e476cd4cdfea3f`;
  집중 테스트 로그 `ced1cc14f02bead8c9eaa9312bd854c07ac7cc3bb2ec4b958defb3160b7139da`;
  전체 노드 로그 `8074a210bbb494e7e8e78687e7d603ab2046e222a1f1615cf5451a292f6fac55`.
- 일반 search/global/transport/fallback/PIT 및 scroll 연결은 남아 있다. count만
  연결한 현재 상태를 alias 기능 전체 완료로 세지 않는다. count의 scoped 엔진
  경로도 materialization 비용 검증/최적화 대상이다. 새 source의 release 빌드와
  참조 HTTP, 전체 non-plugin 반복 벤치마크는 구현 단위 수락 전에 반드시 수행한다.
  기존 후보 `18c1bb3e...` 해시는 그대로이며 성능 개선이나 5% 충족 주장은 없다.
- 전체 수락 0/40, 빈 ledger, 기존 정식 성능 게이트 실패를 유지한다. 소유
  cargo/rustc/steelsearch/java/perf 프로세스가 없음을 확인했다. 릴리즈/태그/커밋/
  푸시는 하지 않았다.

### C05: 일반 검색과 scroll의 alias 범위 연결 (진행 중)

- 직전 turn은 REST count 연결을 추가한 progress다. 이번에는 일반 검색에서
  scoped resolver의 이름/필터 결과를 사용하고 alias query를 검증하도록 했다.
  native 검색과 slice-scroll의 엔진 요청 생성기에 같은 서버 유래 map을 전달한다.
  fallback은 query 평가와 aggregation_context_hits 생성 전에 alias 조건을 적용한다.
  해석할 수 없는 fallback alias 조건은 무필터 결과 대신 오류를 반환한다.
- fallback의 candidate_sources는 필터로 잘라 새 모집단을 만들지 않는다. global
  문서 입력에는 alias/slice 제한이 적용되고 일반 집계는 query/min_score에 따라,
  hits는 추가 post_filter에 따라 결정되는 기존 순서를 유지한다. 기존 legacy
  집계 구현 전체나 텍스트 scoring 전체의 참조 동등성을 증명한 것은 아니다.
- 새 REST handler 테스트 2/2 통과. 1/3샤드에서 filtered alias, multi-index alias,
  alias wildcard, 직접 인덱스/무필터 우선권과 혼합 인덱스 결과를 기본 요청 및
  ignore_unavailable 옵션으로 강제한 fallback 요청에서 비교했다. native helper를
  직접 호출해 scoped native 경로가 실제 응답하는 것도 확인했다.
- query에 맞는 sum=10, post_filter 이후 hits=0, global 범위 doc_count=2 및 sum=30을
  함께 확인했다. 시작한 scroll은 alias를 red에서 blue로 변경해도 남은 red 문서를
  반환하고 새 검색은 blue 1문서를 반환한다. 잘못된 alias query는 기본/fallback
  요청 모두 400이다. slice-scroll에는 범위를 전달했지만 그 전용 live 분산 흐름을
  새로 검증한 것은 아니다. 테스트는 in-process handler 기준이며 새 OpenSearch
  live HTTP 비교가 아니다.
- 전체 노드 614/614 통과, ignored=0, 4.53초. `git diff --check` 통과.
  source SHA-256 `bef7b914a7635a4df29e6a1e7f02dd005b3ce18e1b939ae01e00872bb9cc0cf2`;
  집중 로그 `40971ddc2cce2bea59057c8fd7e3aa47639c1e66d5b2173001abec3f16661e61`;
  전체 노드 로그 `3b3b30defdd00ac6a4e72aa2c30c137ffd35d39e6f4119650fee47721445db6e`.
- PIT는 아직 indices만 가진 기존 context/영속화 표현을 사용한다. 현재 PIT 검색
  분기는 빈 alias map으로 기존 동작을 유지하므로 filtered-alias PIT는 미완료다.
  다음 연결은 생성 시점 범위를 runtime/persisted context에 보존하고 native snapshot,
  fallback 및 transport 복원까지 전달하는 것이다. alias 변경·삭제 후 범위 유지,
  이전 저장 형식과의 호환/불명확한 범위 처리도 함께 검증한다.
- 명시적 background_filter, reader 통계와 legacy significance 배경, nested/rescore/
  suggest 및 다중 노드 전송의 동등성 검증은 계속 남아 있다. 이번 테스트 범위를
  alias 전체 기능 수락으로 확대하지 않는다. C05 연결 단위가 끝나기 전에 기본
  release 재빌드, 참조 HTTP 및 전체 non-plugin 반복 게이트를 실행해야 한다.
- release 바이너리는 여전히 `18c1bb3e...`로 보존했다. 새 release/전체 성능
  실행은 없으며 기존 누적 5% 초과 판정, 전체 수락 0/40과 빈 ledger를 유지한다.

### C05: PIT 대상 해석과 생성 전 필터 검증 (진행 중)

- PIT 생성의 selector별 메타데이터 재조회 대신 한 manifest lock 안에서 인덱스와
  alias 필터를 함께 해석한다. 공통 resolver의 manifest 입력 경로를 분리하여
  count/search와 기존 이름 해석 규칙을 재사용한다. 인덱스별 여러 필터는 OR,
  직접 인덱스/비필터 alias/data stream 선택은 unrestricted 우선으로 합친다.
- `allow_no_indices` 미지정/false/true를 구별하고 wildcard 및 ignore_unavailable의
  기존 PIT 처리 순서를 보존했다. 10개 대상 x ignore 2종 x allow 3종 x
  expand 5종 = **300개** 조합을 이전 per-selector 호출 방식과 비교했다.
  공통 resolver를 공유하는 회귀 비교이며 OpenSearch 독립 oracle 검증은 아니다.
- 생성 route는 해석한 필터를 검증하고 잘못된 query는 문서 snapshot/PIT ID/context
  할당 전에 400으로 거부한다. 직접 인덱스를 함께 선택해 해당 필터가 실제로
  사용되지 않는 경우까지 거부하지 않는다. 테스트에서 ID 증가 및 context/native
  snapshot 누수가 없음을 확인했다.
- union, selector 순서, 직접 인덱스/비필터 alias/data stream 우선순위, multi-index
  필터 분리 및 해석 후 alias 변경에도 소유한 Value가 유지되는 테스트를 추가했다.
  **이는 PIT 수명 전체의 범위 보존 증명이 아니다.** runtime/persisted PitContext와
  PIT 검색은 여전히 필터를 보존하지 않는다. 유효한 filtered-alias PIT의 검색
  범위 문제는 남아 있으며 이번 변경을 해결 또는 단위 완료로 계산하지 않는다.
- 다음 연결 전 확인 사항: transport SearchContextIdWire는 UUID별 alias_filters를
  이미 지원하고 transport 검색은 PIT ID의 wire 필터를 적용한다. REST ID 생성은
  현재 빈 필터를 인코딩하며 REST query-to-wire 변환은 match_all만 지원한다.
  runtime/persisted context, REST native/fallback, transport ID/reader 복원 사이에서
  필터가 소실되지 않도록 함께 변경해야 한다. 이전 저장 형식의 필터 미기록을
  무조건 unrestricted로 간주하지 않는 정책과 회귀 테스트도 필요하다.
- 검증: 첫 테스트 컴파일의 mappings/반환 타입 호출 오류를 수정한 뒤 추가 테스트
  **3/3**, node lib 전체 **617/617**, 실패/ignored 0, 전체 실행 4.65초였다.
  `git diff --check`도 통과했다. 증거는 `target/core-replacement-c05/` 아래:
  - `alias-pit-resolution-tests.log`: SHA-256
    `c95ebfe2d7b936fefbc3f2f95ae1e0195e34da6cd811a3f11764c12b7380fdb5`.
  - `alias-pit-resolution-node-tests.log`: SHA-256
    `10530dd796d15581668aee3a4e46314cf94474be623c8621dc3403526ae7a465`.
  - standalone source SHA-256:
    `c5fc0ec3c3c9f1980654b9def800bd0f89b524f61e4e26c1bd58e7abf9655544`.
- C05 미완료 중간 작업으로 새 참조 HTTP/전체 성능 실행은 아직 없다. 연결 단위가
  끝나면 최초 v0.6.0 고정 누적 5% 기준의 전체 non-plugin 반복 벤치마크를 반드시
  실행한다. 보존 release `18c1bb3e...`, 기존 정식 게이트 FAIL, 최종 수락 0/40,
  빈 exclusion ledger 및 릴리즈 보류를 유지한다. 커밋/태그/게시하지 않았다.

### C05: 새 REST PIT ID의 alias 필터 보존 및 검색 연결 (진행 중)

- 직전 turn은 대상 해석/생성 전 검증과 617개 회귀 테스트를 추가한 progress였다.
  이번에는 기존 SearchContextIdWire의 UUID별 alias_filters에 생성 시점 JSON query를
  WrapperQueryBuilderWire로 인코딩한다. 필터가 있을 때 인코딩 실패를 필터 없는
  local ID로 대체하지 않는다. 전체 문서 snapshot은 그대로 보존한다.
- REST PIT 검색은 서버가 소유한 context를 찾은 뒤 ID에서 필터를 읽어 기존
  fallback alias 평가/global 범위에 연결한다. native PIT snapshot 요청도 동일한
  내부 alias map envelope를 사용한다. 원문 요청의 내부 필드로 범위를 대체하지
  않으며, alias 변경/삭제 후 현재 alias metadata를 다시 읽어 필터를 결정하지 않는다.
- runtime/persisted PitContext에 별도 JSON map을 중복 추가하지 않았다. 기존 영속
  BTreeMap의 키인 PIT ID가 필터 payload를 보존한다. 직전 계획의 context 필드 추가
  방향을 이 기존 표현의 재사용으로 구체화했다. 직렬화/역직렬화 및 runtime 변환
  왕복 테스트는 통과했지만 실제 프로세스 재시작/다중 노드 복원 증명은 아직 아니다.
- REST wire-to-query 경로는 이번 생성 형식인 JSON wrapper와 match_all/match_none을
  처리한다. 그 외 wire query는 unsupported 오류로 반환하며 unrestricted로 바꾸지
  않는다. malformed JSON/unknown JSON query/알 수 없는 ID decode 실패도 오류다.
  이전 local v1 ID는 기존 동작을 유지하므로 **구형 필터 미기록 PIT의 이력 복구 및
  fail-closed migration은 미완료**다. 이전 REST wire ID의 빈 alias map도 구분할
  version/provenance 정책이 필요하다. 이번 수정으로 legacy 문제를 해결했다고 하지 않는다.
- transport 검색에는 wrapper JSON 평가 및 PIT ID alias 적용 코드가 이미 있음을
  확인했다. 하지만 REST와 transport의 query evaluator 지원/오류 계약은 같지 않을
  수 있다. transport 생성/reader 복원/REST 상호 검색의 실제 회귀 검증과 unsupported
  query 처리 보강은 남아 있다. 전체 transport 동등성을 코드 존재만으로 주장하지 않는다.
- 새 테스트: 1/3 shards에서 red alias PIT 생성 후 blue로 변경한 live 검색은 1건,
  기존 PIT는 alias 삭제 및 영속 표현 왕복 후에도 red 범위를 유지한다. query hits
  1건, global doc_count 2/sum 30, 전체 snapshot 문서 3건을 확인했다. native 2개 slice
  합계 2건 및 모두 red임을 검증했다. 별도로 multi-index/alias wildcard/직접 인덱스/
  비필터 alias 우선순위 6개 조합과 잘못된 wire payload의 오류 처리를 검증했다.
- node lib 전체 **620/620**, 실패/ignored 0, 최종 실행 4.84초. `git diff --check`
  통과. `target/core-replacement-c05/alias-pit-id-validated-node-tests.log` SHA-256:
  `9e4e25a709694c4b2fa4d567df4157d483768fb6527d3fbcb5bed4f5ab934f5d`.
  standalone source SHA-256:
  `89246dba47ee64ea3f9914ed429854db776f187a619e67c9f7d3d97e55359d3d`.
- 연결 단위는 아직 미완료이며 새 release 빌드/참조 HTTP/전체 성능 실행은 없다.
  transport와 복원 경계를 마무리하고 참조 검증 및 최초 v0.6.0 고정 누적 5% 전체
  non-plugin 반복 게이트를 통과하기 전에는 C05를 완료하지 않는다. 기본 release는
  `18c1bb3e...`로 보존했고 기존 FAIL, 최종 수락 0/40, 빈 ledger와 릴리즈 보류를
  유지한다. 커밋/태그/게시하지 않았다.

### C05: 실제 디스크 경로 확인 및 재시작 PIT ID 재사용 수정

- 직전 turn은 새 REST PIT ID의 필터 보존과 검색 연결, 620개 회귀 테스트를 추가한
  progress였다. 이번에는 운영 디스크 경로를 읽어 앞선 복원 설명의 경계를 수정했다.
  `persist_shared_runtime_state_to_disk`는 pit_contexts를 빈 map으로 저장하고,
  `sync_shared_runtime_state_from_disk`는 파일의 PIT를 복원하지 않고 runtime PIT를
  지운다. `runtime_pit_contexts_from_persisted`/반대 변환은 현재 운영 호출이 없다.
  따라서 직전 JSON 왕복 테스트는 표현 보존만 증명하며 실제 재시작 복원 증거가 아니다.
- 로컬 참조 `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/search/SearchService.java`
  의 activeReaders와 doStop/doClose를 확인했다. 서비스 종료 시 reader context를
  해제한다. 재시작 시 구형 필터 미기록 PIT를 임의로 unrestricted 복원하는 변경은
  하지 않는다. 파일에 구형 context가 있더라도 만료시키는 기존 정책을 검증한다.
  transport의 reader 업데이트/원격 소유자 경로 검증은 이 프로세스 종료 정책과
  별개로 계속 필요하다.
- **실패 재현**: 같은 node 이름과 복구된 index UUID, alias 필터로 PIT를 다시
  생성하면 next_pit_id가 1로 돌아가 이전 ID와 새 ID가 완전히 같았다. 새 snapshot이
  오래된 PIT ID에 연결될 수 있는 문제다. 파일 기반 node 재생성 테스트가 ID
  비동일성 assertion에서 실패했으며 실패 로그를 보존했다.
- REST와 transport wire PIT 생성 시 각각의 기존 session prefix/sequence 뒤에
  v4 UUID를 추가한다. 한 PIT의 모든 shards는 동일한 session UUID를 사용하고,
  다른 생성은 같은 sequence/index/node라도 다른 session을 사용한다. repo 엔진이
  이미 사용하는 uuid 1.8.0/v4를 node 직접 의존성으로 추가했다. 검색/refresh 루프,
  문서 보호 및 index generation 검증은 변경하지 않았다.
- 파일 기반 테스트는 실제 shared.json의 PIT map이 비어 있음을 확인하고, 구형 파일을
  모사해 context를 넣은 뒤 새 SteelNode로 읽어도 복원되지 않음을 검증한다. 새 PIT
  생성 후 이전 ID는 404, 새 ID는 red 필터의 2건을 반환한다. 이는 같은 테스트
  프로세스에서 node를 재생성한 검증이며 강제 프로세스 종료/분산 failover 시험은 아니다.
- transport 생성 테스트는 같은 입력/sequence의 두 ID가 다르고, 3개 shard가 PIT별
  단일 session을 공유하며 두 PIT의 reader context ID 집합이 겹치지 않음을 확인했다.
  기존 local v1 fallback ID 생성 및 비정상 wire 인코딩 실패 시 정책은 별도 점검
  대상이며 이번 wire session 수정으로 모든 ID 경계를 증명했다고 하지 않는다.
- 검증: node lib **621/621**(4.86초), transport PIT 필터 **57/57**(0.09초),
  standalone binary 전체 **458/458**(21.54초), 실패/ignored 0. `git diff --check`
  통과. 테스트 후 steelsearch/java 프로세스가 남아 있지 않음을 확인했다.
  증거는 `target/core-replacement-c05/` 아래이며 SHA-256은 다음과 같다.
  - `alias-pit-restart-before-tests.log`(수정 전 실패):
    `57b2c9f63c50e75ccf0e9f45dd454d939602b5a7d31473eee2db6ba61f9fc6c6`.
  - `alias-pit-restart-node-tests.log`:
    `9ceab764dafe9e9760dfee1bbe84b028c3ebcdfb99f0b0b7246a9d27dc1b3831`.
  - `alias-pit-restart-transport-suite.log`:
    `8558b90c55ea184e689d1ac2ffb00d575b9da66af21866726381f0c86d94f20f`.
  - `alias-pit-restart-binary-tests.log`:
    `3a7b9ae14a376fdcd740371984a5e00fa945f2987f8fbd4a81ec88893512da65`.
  - standalone source:
    `721941b7559061a14292f12cc6b6d0958d93607e09b1bf3c85109caa1a24c865`.
  - main source:
    `81e0c8af05da1480429ea43db7ba8dce2bbd5a2ab7df9f6c6ebe160b51c1b5f8`.
- C05 단위 완료는 아니다. alias의 REST/transport 상호 검색·오류 동등성, 원격/reader
  경계 및 참조 HTTP 검증을 마무리한 뒤 전체 non-plugin 반복 벤치마크를 실행해야
  한다. 최초 v0.6.0 고정 누적 5% 기준, 기본 release `18c1bb3e...` 보존,
  최신 정식 게이트 FAIL, 최종 수락 0/40, 빈 ledger 및 릴리즈 보류를 유지한다.

### C05: REST PIT의 transport 부정 alias 필터 누출 수정

- 직전 turn은 재시작 ID 재사용 실패를 수정하고 lib 621/binary 458개를 검증한
  progress였다. 이번에는 REST 생성 PIT를 실제 transport request/response frame
  경로로 검색하는 교차 프로토콜 테스트를 추가했다. 1/3 shards에서 term alias,
  alias OR, 직접 인덱스 우선순위 및 부정 prefix 필터를 검사한다.
- **실패 재현**: `must_not(match_bool_prefix(tenant=blu))` alias의 PIT를 만들고
  alias metadata를 삭제한 뒤 REST는 red 2건인데 transport는 blue까지 3건을
  반환했다. 별도 JSON evaluator가 지원하지 않는 내부 query를 false로 처리하여
  must_not에서 필터 범위를 넓힌 문제다. 수정 전 실패 로그를 보존했다.
- transport PIT의 JSON wrapper alias 필터를 요청당 한 번 파싱/검증하고 REST와
  같은 mapping-aware evaluator로 평가한다. 일반 transport query 및 다른 wire
  query variant는 이번 변경 범위가 아니다. 필터가 없으면 새 mapping clone/lock
  경로에 들어가지 않는다. 필터 파싱은 빈 문서/timeout 조기 응답 전에도 수행한다.
- alias 해석/평가 실패를 Result로 전달하고 search/stream/search-model/msearch
  응답 생성에서 transport IllegalArgumentException으로 전파한다. **msearch의
  항목별 실패 표현은 기존 wire 타입에 없으므로 현재 배치 전체 오류다.** 항목별
  성공/오류 혼합 계약은 남아 있으며 이번 안전 처리로 msearch 전체 동등성을
  주장하지 않는다. JSON 이외 PIT wire 필터의 REST 변환 지원도 계속 남아 있다.
- 교차 프로토콜 8개 조합의 totals/ID 집합/PIT ID가 일치했다. malformed JSON 및
  must_not 내부 unknown query는 문서 유무 두 경우 모두 오류 frame이고 성공 hits로
  바뀌지 않음을 확인했다. native engine 경로와 모든 query/집계 조합의 동등성 또는
  실제 OpenSearch HTTP 비교를 이 테스트로 대체하지 않는다.
- 검증: node lib **621/621**(4.83초), standalone binary **459/459**(17.49초),
  실패/ignored 0, `git diff --check` 통과. `target/core-replacement-c05/` 아래:
  - `alias-pit-cross-protocol-before-tests.log`(수정 전 실패):
    `f9de6ca7ac3fce8497a3fde72e6ff9bd2f87f55e2e0e6995789cb69fc150a8eb`.
  - `alias-pit-cross-protocol-node-tests.log`:
    `ddbe7aa7318363c3826db0cb51673ca480801c23c223902061104896f6173fbf`.
  - `alias-pit-cross-protocol-binary-tests.log`:
    `ec3f8cb07ff87eea47f7dad4b794ce8ec7b2c0d57fb1f6afec50213261de4c3c`.
  - standalone source:
    `658b5c4bcaef1c423b1c0efd4f0b8798818f9cd6de6f4de92475b7c6fd981b19`.
  - main source:
    `411d3fd54b1e9ce1e8d7ec55a767cfc8038cb661d52c4d0bc83f5e6e469c3b38`.
- 검색 경로 변경이 누적되어 C05 최종 수락과 별개로 release 재빌드 및 전체 반복
  성능 재측정을 진행한다. 이전 `18c1bb3e...` 바이너리는
  `target/core-replacement-c05/steelsearch-before-alias-scope`로 보존하고 해시 일치를
  확인했다. `alias-scope-build-inputs.sha256`에 주요 빌드 입력을 기록했다. 기능 및
  전체 성능 결과는 실행 후 별도 기록하며, 시작만으로 통과나 수락을 주장하지 않는다.

### C05: alias 연결 후보의 live 비교 및 전체 반복 게이트

- release 빌드가 종료 0으로 완료됐다(4분 47초). 현재 기본 release 후보 SHA-256:
  `75cd0d4505f3d0379c098e5d7948e628aeebcd9bf78f571d395b1b353707ba00`.
  `alias-scope-release-build.log` SHA-256:
  `58164d09022386573f7370ce03fb7faefc48c49d44eed218d729ba8e95b7325d`.
  이전 후보 `18c1bb3e...`는 `steelsearch-before-alias-scope`에 그대로 보존했다.
  주요 빌드 입력의 전후 해시 검사도 통과했다. 새 릴리즈를 게시한 것은 아니다.
- live runner의 첫 호출은 PYTHONPATH 누락으로 import 단계에서 종료됐다. 서버나
  측정을 시작하지 않았으며 `PYTHONPATH=tools`를 지정한 실행으로 진행했다.
  `target/core-replacement-c05/live-alias-scope`에서 기능 참조는 실제 로컬
  OpenSearch **3.7.0-SNAPSHOT**, 후보는 위 실행 파일이며 `/proc/.../exe` 검증,
  fixture 및 바이너리 해시 불변 검증이 통과했다.
- settings/routing 통과, bucket order **36/36**, bool **200/200**, projected core
  **1180/1180**을 유지했다. nested 두 fixture는 각각 **130/160**으로 기존 30개
  실패씩 남았다. skip/setup 실패로 정상 결과를 대체하지 않았다.
- 동일 count/alias/PIT probe에서 후보는 이전 **42/57 -> 56/57**, 참조는 **57/57**이다.
  두 실행의 probe SHA-256이
  `c2240bb25c1a0a50a81fbc074f6f11207d6c409b8dae4a3542c0c0d033d2d3d1`로 같다.
  남은 후보 실패는 `0/missing-wildcard/_search`: 없는 wildcard의 검색이 빈 hits
  total 0 대신 index_not_found 404를 반환한다. live runner 전체 종료 1은 이 실패와
  nested 실패를 보존한 결과이며, alias 기능 전체 수락을 뜻하지 않는다.
  `live-alias-scope/execution.json` SHA-256:
  `5fcfd3307010085f34684df2b4094df59ba35e075dc30e5237c1925277b6fd68`.
- 기능 실행의 서버를 종료한 뒤 `alias-scope-repeated-full` 전체 반복 게이트를 실행했다.
  순서는 baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/baseline05이며
  각 실행은 단일/3노드, 5,000문서, 384차원 source, 4 clients, 60초, shard 3,
  replica 0/1, seed 13, timeout 10초 및 기존 7-operation query mix를 유지했다.
  성능 참조는 pinned **OpenSearch 2.19.0** 이미지/512MB heap이며 위 기능 참조와 다르다.
  총 1101.99초, 여섯 run 종료 0, 12개 topology error_count 합계 0,
  execution_inputs_verified=true다. 전체 runner는 **종료 1 / numeric FAIL**이다.

| 후보 반복 | 공개 v0.6.0 대비 | paired v0.6.0 대비 | baseline 자체 drift |
| --- | --- | --- | --- |
| candidate01 | 43/44 | 44/44 | 41/44 |
| candidate04 | 41/44 | 39/44 | 42/44 |

- 공개 v0.6.0 대비 예산 초과(양수는 지연 증가): candidate01의 3노드 refresh p99
  **+8.025%**. candidate04의 3노드 ranking p99 **+7.011%**, refresh p95
  **+6.383%**, refresh p99 **+7.196%**. 다른 지표 개선으로 상쇄하지 않는다.
- paired 초과는 candidate04의 3노드 ranking p99 +5.196%, sort_filter p99 +5.439%,
  refresh mean +5.220%, p95 +7.426%, p99 +8.736%다. candidate01 paired는 44/44이나
  이를 공개 기준 실패나 다른 반복을 지우는 근거로 사용하지 않는다.
- baseline00도 공개 기준 대비 3노드 lexical p99 +7.806%, facet p99 +6.725%,
  refresh mean +5.717% 초과였다. baseline05는 단일 refresh p99 +5.926%, 3노드
  nested p99 +9.106% 초과였다. 환경/변동 원인 분리가 필요하지만 이를 임의 면제,
  percentile 평균, 기준 재설정 또는 유리한 반복 선택에 사용하지 않는다.

| 후보 반복/토폴로지 | 후보 ops/s | 공개 v0.6.0 대비 처리량 변화 | paired OpenSearch 대비 처리량 |
| --- | ---: | ---: | ---: |
| candidate01 / 단일 | 758.74 | +2.118% | 2.611배 |
| candidate01 / 3노드 | 928.82 | -0.273% | 7.694배 |
| candidate04 / 단일 | 756.69 | +1.841% | 2.620배 |
| candidate04 / 3노드 | 917.92 | -1.444% | 7.907배 |

- 위 처리량 변화는 공개 최초 v0.6.0 기준이고, 직전 개발 후보 `18c1bb3e...` 대비가
  아니다. OpenSearch 비율은 각각 run02/run03과의 동일 혼합 부하 개발 설정 비교이며
  운영 내구성/보안/모든 기능의 동등성 또는 배포 적합성을 뜻하지 않는다.
- `alias-scope-repeated-full/plan.json` SHA-256:
  `eed080bb4ef9e354b949d62caabbfc922542e9361cb1696adde8b166b8b3603c`.
  `alias-scope-repeated-full/result.json` SHA-256:
  `c4dfc64d7dceb5dec8a0ea5c998c2b0c78ec836898031dc2cf530a82a69bf17f`.
  원본 report의 모든 시나리오/반복은 보존한다. 종료 후 steelsearch/java/rustc 프로세스가
  없고 기존 사용자 컨테이너 5개만 유지됨을 확인했다. `git diff --check` 통과.
- 다음 기능 수정은 위 missing-wildcard 검색과 남은 alias wire/reader/error 경계다.
  성능은 3노드 ranking/refresh tail 및 baseline 변동을 별도 진단으로 분리해야 한다.
  이 묶음의 결과만으로 특정 단일 변경의 5% 이상 기여 또는 최적화 불가를 입증할 수
  없으므로 exclusion ledger는 비워둔다. 최신 정식 성능 FAIL, C05 미완료,
  최종 수락 **0/40**, 릴리즈 보류를 유지한다. 커밋/태그/게시하지 않았다.

### C05: missing-wildcard 검색 옵션 수정 및 독립 HTTP 비교

- 직전 turn은 alias 범위 누출 수정, 실제 probe 56/57 및 전체 반복 성능 FAIL을
  확인한 progress였다. 이번에는 남은 `missing-wildcard/_search` 404 실패를 수정했다.
- 로컬 OpenSearch SearchRequest.DEFAULT_INDICES_OPTIONS와 IndicesOptions의
  STRICT_EXPAND_OPEN_FORBID_CLOSED_IGNORE_THROTTLED를 확인했다. 검색 기본값은
  allow_no_indices=true다. IndexNameExpressionResolver의 wildcard/명시적 이름
  처리 및 확장이 비활성화된 concrete resolver 경로도 확인했다.
- REST 검색 전용 resolver 분기를 두고 기본 allow_no_indices=true를 적용한다.
  확장된 wildcard의 누락은 allow_no_indices, 명시적 이름의 누락은 ignore_unavailable로
  판단한다. expand_wildcards=none에서 wildcard가 하나라도 있으면 대상 전체를 비우던
  route shortcut도 제거하고 원래 표현의 단일/복수 concrete 처리 규칙을 적용한다.
  alias 필터 합집합/직접 인덱스 우선순위는 유지한다. count/PIT 생성/기존 names-only
  호출부는 기존 generic 분기를 유지하며 이 옵션 변경을 적용하지 않는다.
- 23개 조합의 단위 테스트를 추가했다. 첫 두 실행은 `?` wildcard를 테스트 URL에
  그대로 쓰거나 요청 path를 덮어쓴 구성 때문에 정규화에서 query 구분자로 해석되어
  실패했다. 실제 URL처럼 `%3F` 인코딩한 요청으로 수정했고 실패 로그를 보존했다.
  해당 실패를 제품 resolver의 회귀 또는 참조 통과 증거로 해석하지 않는다.
- 재사용 가능한 `tools/fixtures/search-index-options-compat.json`을 추가했다.
  literal/wildcard/혼합/alias/allow/ignore/no-expansion의 23개 HTTP 사례에서 status와
  hits total/relation을 비교한다. 모든 오류 envelope, hidden/closed/data stream 조합
  또는 모든 API의 옵션 동등성을 이 fixture로 증명했다고 하지 않는다.
- 소유 live 진단 runner에 `--candidate-binary`를 추가했다. 기본값은 기존 release로
  유지하고, 명시한 바이너리의 해시 및 실제 PID/exe 검증을 그대로 수행한다. 이번에는
  기능 검증용 debug 빌드(59.75초, 종료 0)를 사용했고 성능을 측정하지 않았다.
  `run-live.py` SHA-256:
  `4a14e12a662017e2d18edf7fc1a2e1cf26a065c4ed9a7fe6c33d298e17f39bc1`.
- `live-search-wildcard-debug`에서 실제 OpenSearch **3.7.0-SNAPSHOT**과 비교했다.
  새 fixture **23/23**, 기존 count/alias/PIT probe는 후보/참조 모두 **57/57**,
  projected core **1180/1180**이다. nested 두 fixture는 각각 **130/160**으로 기존
  실패가 남아 전체 runner 종료 1이다. skip 없이 바이너리/fixture 해시 불변 검증이
  통과했다. 디버그 결과를 release 성능 또는 C05 전체 수락으로 확대하지 않는다.
- 최종 node lib **622/622**(4.89초), standalone binary **459/459**(17.64초),
  실패/ignored 0, `git diff --check` 통과. 종료 후 steelsearch/java/rustc 프로세스가
  없음을 확인했다. 증거는 `target/core-replacement-c05/` 아래다.
  - `search-wildcard-options-final-node-tests.log`:
    `23c9fdde980c3aa18cc5bea0281c67f3a7443ddddd3cd287c273a2ddbbc7aaa4`.
  - `search-wildcard-options-binary-tests.log`:
    `ba386b1115aad1f02841a863c3039759f6b5b5becdad7d52bfa994730acc75b5`.
  - `live-search-wildcard-debug/execution.json`:
    `105e44bf4d085c80d3ceb68a18d48120c0581b11b750f6bdf4697c565f4f9323`.
  - debug executable:
    `216b74deec571f959db71c40b40b0af4690c3ce01c7fc80cc103adfbce655ae0`.
  - standalone source:
    `e8f1067205ceae9d217d8820b8750f62864567394317234f04787839ae7c4879`.
  - new fixture:
    `8dfccb868808560e48e08382e93d3e74af68b186a43017165fb11756b79d66dc`.
- 기본 release `75cd0d45...` 및 그 전체 반복 FAIL 증거는 변경하지 않았다. 이
  release에는 이번 wildcard 수정이 아직 없다. 새 소스의 release 재빌드/기능 확인과
  최초 v0.6.0 고정 누적 5% 전체 non-plugin 반복 게이트는 수락 전 필수로 남는다.
  다음 기능 범위는 nested 집계 실패와 alias wire/reader/error 경계다. 성능은 기존
  3노드 ranking/refresh tail 및 baseline 변동의 원인 분리가 계속 필요하다.
  C05 미완료, 최종 수락 0/40, 빈 ledger와 릴리즈 보류를 유지한다.

### C06: REST fallback 숫자 terms 키와 정렬 수정 (진행 중)

- nested 집계 실패의 공통 원인은 `terms.order`가 native parser에서 지원되지 않아
  fallback으로 이동한 뒤 문자열이 아닌 bucket 키를 버리는 처리였다. REST fallback이
  숫자 JSON 키를 보존하고, 숫자/문자열 배열을 문서별 중복 제거해 집계하도록 수정했다.
  빈 배열과 null-only 배열은 missing을 적용한다. `_key` 정렬 및 `_count` 동률 정렬은
  기존 정수 우선 scalar 비교기를 사용해 2^53 초과 정수의 순서를 보존한다.
- native terms.order 구현 완료가 아니다. 매핑 기반 숫자 coercion, 1/1.0 혼합 키,
  boolean terms 의미, 일반 bucket 하위 집계와 잘못된 order 옵션 처리는 별도 미완료다.
  기존 `terms_aggregation` HTTP 비교기는 순서 있는 key/doc_count를 비교하며,
  sum_other/error-bound 메타데이터까지 참조 검증했다고 주장하지 않는다.
- 새 `tools/fixtures/search-numeric-terms-compat.json`은 key/count 오름·내림차순,
  큰 정수, 배열 중복/missing, include/exclude, min_doc_count/size, nested query 및
  숫자처럼 보이는 문자열 키를 검증한다. 실제 OpenSearch 3.7.0-SNAPSHOT과 debug
  비교에서 **8/8** 통과했다. 결과는 `target/core-replacement-c05/live-numeric-terms-debug`.
- 같은 실행에서 검색 옵션 **23/23**, count/alias/PIT 양쪽 **57/57**, core **1180/1180**.
  nested flat/canonical은 각각 **130/160 -> 152/160**으로 개선됐다. 남은 각각 8건은
  1/3샤드의 empty-bool, empty-positive-limit, unqualified-must, unqualified-not 집계다.
  fallback 빈 bool이 match-all로 끝나지 않는 문제와 nested child의 무접두어 필드를
  허용하는 차이를 확인했다. 이번 숫자 terms 변경과 분리해 후속 수정한다.
  전체 runner 종료 1이며 skip 0, 바이너리/fixture 불변 확인은 통과했다.
- node lib **623/623**(5.01초), standalone binary **459/459**(18.18초), 실패/ignored 0,
  `git diff --check` 통과. debug 빌드 완료(29.58초). 증거 SHA-256:
  - standalone source: `7b171db29fad543a45d7d782b36c1655868eaf8919bdac85a77fab2f44497222`
  - fixture: `30e0e2430a4d0a170fd02e9624e5be75cdcd453e384244cf73262978c7ac5b6c`
  - `numeric-terms-final-node-tests.log`: `e588d210d767627c5cff851f06b123567d9adfea2a87152791b7aef94fad5166`
  - live `execution.json`: `4856254f003ac304ce849f06604dca741c7702c56b35ab05dd8bf2e2406b82d7`
- 직전 release `75cd0d45...`는 `target/core-replacement-c05/steelsearch-before-numeric-terms`에
  보존했다. wildcard 및 숫자 terms를 포함하는 release 빌드를 시작했으며, 완료 후
  release 기능 확인과 고정 v0.6.0 누적 5% 전체 반복 게이트를 실행한다. 기존 정식
  게이트 FAIL, 최종 수락 0/40, 빈 ledger와 릴리즈 보류를 유지한다.

### C06: 숫자 terms release 재검증 및 전체 반복 측정 (2026-09-08)

- release 빌드 완료(4분 36초, 종료 0). 기본 release에는 위 wildcard/숫자 terms
  수정이 포함된다. 이전 `75cd0d45...` 보존본의 해시도 확인했다.
  - 새 release: `edbfad5b256fd924ef94d18fa58d08bbc6588571ec0241807fb5a92943a86a52`
  - `numeric-terms-release-build.log`: `22d8e03ff1f0a0b3840276101ba522a6931ca2eb90831b1aa01dfdb3bc9b5ad2`
  - `numeric-terms-binary-tests.log`: `6c75eb58d038510cb2f91277dd2f4eee31a644e72e23b00bcc97315dda64ddc2`
- `target/core-replacement-c05/live-numeric-terms-release`에서 동일한 실제 참조와
  HTTP 재검증했다. 숫자 terms 8/8, 검색 옵션 23/23, count/alias/PIT 양쪽 57/57,
  core 1180/1180, nested 두 fixture 각각 152/160이다. debug와 같은 잔여 실패로
  runner 종료 1, skip 0, 바이너리/fixture 불변 확인 true다.
  execution SHA-256: `f4cc3ac4d662c136514e305c166d027d4996372a123fc2d3f7c73f14a67603bf`.
- 전체 반복 게이트는 `target/core-replacement-c05/numeric-terms-repeated-full`에서
  실행했으나 4회차 OpenSearch 3노드 준비 중 중단됐다. baseline/candidate/OpenSearch/OpenSearch/candidate/baseline 순서와
  기존 전체 workload 및 최초 v0.6.0 고정 기준을 유지했다. 빌드/기능 테스트 종료 후
  시작했고 측정 중 추가 빌드/프로파일러는 실행하지 않는다. 일부 회차의 결과만으로
  통과 처리하지 않으며, 전체 결과와 실행 입력 검증을 확인한 뒤 판정한다.
  plan SHA-256: `824464e58b3ebfc530f0c8e3d73d9141a728b024a458c45ee05798a5132592e6`.
- 종료 2, `planned run 3 failed with exit 1`: OpenSearch의 인덱스 생성이 403
  `cluster create-index blocked (api)`로 거부됐다. failure-diagnostics의 global block 10과
  세 노드 각각 약 2.22GB available / 102.89GB total을 보존했다. 완료된 앞 3회차는
  요청 오류 0이지만 전체 반복이 없으므로 numeric 판정 증거로 승격하지 않는다.
  `execution_inputs_verified=false`, `acceptance_established=false`이며 제품 회귀에 의한
  numeric FAIL과 구별한다. result SHA-256:
  `6d427da2fa01680255f380c9f79cf7ced83518423845722a0db8e650f979bf9a`.
- 디스크 임계값/보호 설정을 완화하지 않았다. 빌드/서버 종료를 확인하고 재생성 가능한
  `target/debug/incremental` 및 `cargo +nightly clean --profile dev` 산출물을 정리했다.
  여유 공간은 약 2.1GB에서 17GB(사용률 83%)로 늘었다. 소스, 전체 측정/테스트 로그,
  고정 v0.6.0 및 모든 보존 release 바이너리는 유지하고 해시를 재확인했다.
  debug 실행 파일도 `target/core-replacement-c05/steelsearch-numeric-terms-debug`에
  보존했다(SHA-256 `e0b931784b8e71f36aac2b61cec1a8872f7d2a250c1895d97ad05dfcbc68d0e5`).
- 환경 조치 후 `numeric-terms-repeated-full-disk-recovered` 새 디렉터리에서 동일
  소스/바이너리/설정의 여섯 회차 전체를 재시작했다. 중단 실행의 일부 결과를 새 결과와
  합치거나 실패 회차만 골라 재측정하지 않는다. 이전 증거는 그대로 유지한다.

### C06: 디스크 공간 확보 후 전체 반복 게이트 결과 (2026-09-08)

- `target/core-replacement-c05/numeric-terms-repeated-full-disk-recovered`의 여섯 회차
  전체가 완료됐다. 총 1093.35초(18분 13초), 각 회차 종료 0, 12개 토폴로지의
  요청 오류 합계 0이다. runner 종료 1은 **numeric FAIL**이며 인프라 오류가 아니다.
  `execution_inputs_verified=true`, error 없음, `acceptance_established=false`.
- workload는 단일/3노드, 토폴로지당 60초, 5000문서, 4클라이언트, 3샤드,
  replica 0/1, seed 13, timeout 10초 및 기존 7개 시나리오 혼합을 유지했다.
  참조 성능 이미지는 고정 OpenSearch 2.19.0이고 heap 512MB다. 기존 개발용
  durability 설정의 비교이며 운영 내구성 동등성이나 기능 전체 대체를 증명하지 않는다.

| 후보 회차 | 공개 v0.6.0 대비 | 대응 재측정 v0.6.0 대비 | 기준 자체의 공개 대비 변동 |
| --- | --- | --- | --- |
| 01 | 44/44 | 44/44 | 44/44 |
| 04 | 43/44 | 43/44 | 41/44 |

- 후보 04의 **3노드 sort_filter p99**는 공개 10.95857449ms 대비 11.72651064ms,
  **+7.007628%**이며 허용 상한 11.50650321ms를 넘었다. 대응 baseline 05 대비도
  **+11.267545%**다. 후보 01의 통과나 다른 개선으로 이 실패를 상쇄하지 않는다.
- baseline 05 자체도 공개 대비 single refresh p99 **+7.538397%**, three facet p99
  **+5.743991%**, three nested p99 **+7.067486%**로 변동했다. 환경/실행 변동의 별도
  조사 근거이며 후보 sort_filter 초과를 면제하는 근거가 아니다.

| 후보 회차 | 토폴로지 | 후보 ops/s | 공개 v0.6.0 대비 처리량 | 대응 OpenSearch ops/s | 후보/참조 |
| --- | --- | --- | --- | --- | --- |
| 01 | 단일 | 754.2553 | +1.513327% | 286.2737 | 2.634734x |
| 01 | 3노드 | 933.2328 | +0.200007% | 111.1335 | 8.397407x |
| 04 | 단일 | 749.7096 | +0.901533% | 289.7137 | 2.587760x |
| 04 | 3노드 | 921.3298 | -1.078008% | 107.1963 | 8.594792x |

- 위 표는 회차별 값이며 percentile 평균이나 서로 다른 실행의 결과 병합을 하지 않았다.
  공개 기준 처리량은 최초 v0.6.0의 단일 743.0110695 / 3노드 931.3700112 ops/s다.
  각 시나리오 mean/p95/p99의 전체 44개 지표와 참조 값은 result.json에 보존했다.
- plan SHA-256: `6bb1f5b3188120af75f2c4315621cbe5659882ccc4f0aea6741ff85fbfa74b74`.
  result SHA-256: `c3e3ea81266cd5f28620b92c3590fd63eb9bc043c745584c9bdaa7939cfa545e`.
  종료 후 source `7b171db2...` 및 release `edbfad5b...`의 해시를 재확인했다.
  소유 cargo/rustc/steelsearch/java 및 벤치마크 컨테이너는 남아 있지 않고,
  기존 사용자 컨테이너 5개는 유지했다.
- 숫자 terms의 제한된 기능 개선은 검증됐지만 C05/C06 전체 완료가 아니다.
  다음 작업은 남은 nested fallback 의미 8건씩과 sort_filter tail/기준 변동 원인
  분리다. 단일 구현의 5% 이상 기여 및 최적화 불가를 입증하지 않았으므로 ledger
  제외는 없다. 최종 수락 **0/40**, 릴리즈 보류를 유지한다. 커밋/태그/게시 없음.

### C05: fallback bool 및 nested child 경로 의미 수정 (2026-09-08)

- 직전 턴은 숫자 terms 기능 개선과 전체 성능 증거를 확보한 progress다. 다음으로
  남은 nested 집계 실패를 수정했다. OpenSearch BoolQueryBuilder.doRewrite의 빈 bool
  match-all 처리를 확인해 fallback도 네 절이 모두 비면 minimum과 관계없이 match-all로
  처리한다. `must: []`를 실제 필수 절로 간주하던 should 기본 판정도 고쳤다.
- bool-only 단계: node lib 624/624(10.74초), debug 빌드 52.11초, 실제 OpenSearch
  3.7.0-SNAPSHOT 비교에서 새 bool 10/10, 기존 bool 200/200, 숫자 terms 8/8,
  검색 옵션 23/23, count/alias/PIT 양쪽 57/57, core 1180/1180. nested는 각각
  152/160 -> 156/160으로 개선됐고 무접두어 필드 집계 4건씩이 남아 runner 종료 1.
  `live-fallback-empty-bool-debug/execution.json` SHA-256:
  `e2acecc1ab7380d1774fcc16c6644b7324edae0acf29704800b073ddd9d133c2`.
  당시 source `c7d14316297981d571898b3a76ae52ccf85ebc66911a783f069e56529ccc59c0`,
  debug `461a48010c7ee8981501a0238cf7bc84eb02132e79462f6a810e38c20ed0e644`.
- nested fallback은 child를 무접두어 객체로 평가하지 않고 원래 전체 path 아래에
  놓아 평가한다. 부모/형제 child가 보이지 않으며 필드 접미어만 같은 다른 경로도
  일치하지 않는다. 기존 `extract_source_path_value`를 재사용해 단일 객체, null,
  배열 및 배열을 가로지르는 다단계 nested path를 지원한다. 추출한 child를 이동해
  경로를 복원하므로 그 단계에서 child를 다시 clone하지 않는다.
- 기존 nested score 및 knn 회귀 테스트가 무접두어 필드를 사용하던 부분은 전체
  경로로 보정했다. nested 변경 후 첫 세 전체 테스트는 knn 테스트의 서로 다른
  비정규 경로 요청에서 각 1건 실패했고 로그를 보존했다. 기대 건수/점수/문서 ID는
  낮추지 않았다. 이는 플러그인 지원 확대나 플러그인 참조 검증 주장이 아니다.
- 최종 node lib **625/625**(10.67초), 실패/ignored 0. debug 빌드 45.72초 완료.
  `tools/fixtures/search-fallback-bool-compat.json`(10건)은 status/total/relation을,
  `tools/fixtures/search-fallback-nested-paths-compat.json`(10건)은 rank 정렬 문서 ID와
  source/total을 참조 비교한다. 부모/형제 격리, 다른 접두어, 단일 객체/null,
  직접 다단계 path 및 nested 안의 nested를 포함한다.
- `target/core-replacement-c05/live-fallback-nested-path-debug`에서 실제 참조 비교가
  **runner 종료 0**으로 완료됐다. 새 fixture 각각 **10/10**, 기존 bool **200/200**,
  숫자 terms **8/8**, 옵션 **23/23**, nested flat/canonical 각각 **160/160**,
  core **1180/1180**, count/alias/PIT 양쪽 **57/57**. 이 사례들의 일치이며 nested
  전체 옵션/매핑 오류/점수/inner_hits 등 모든 계약의 완료로 확대하지 않는다.
- 증거 SHA-256:
  - source: `d85c710de978f6de6d0b6cc722dd365e9876e86282a156ff6e7adb15abcf0858`
  - bool fixture: `c51b0c4de3a5c2a25322fb8ccd4454578252dce3efd91bd0b6ab677f5821c4cc`
  - nested fixture: `c16f0d998771b7c28d8706fbb30b60eb698f1b692a21bf3e6e9cffbfc2c153f4`
  - `fallback-nested-path-complete-node-tests.log`: `203a93cd1d4e1c291073cb3b357f93f0c61baf91d5fed11159aa91d051f9611e`
  - live execution: `56faee18aaf96a367f697d584107942fcdd4b1e8a6f9472fb959c3109a08a57a`
  - debug binary: `9855b984f0b934de9ba2626127c980c8b70cab90c678e19c1d2444ced9433189`
- binary 회귀 **459/459**(17.71초), 실패/ignored 0. log SHA-256:
  `0143ff9568e0c0b2cde28c128677d377ae9cadc7033bd0e213d62d29837b6a40`.
- release 빌드 4분 45초, 종료 0. 새 release는
  `e6b49b8357783bf30f354ab8a696eab828123b09c502d4aea95ab7c79d30526d`이고 빌드 로그는
  `a563e1ad9d5dfba8f9b55ef8b1a74f7a0879068954bda6dfdf3feb4edbdb0e65`다.
  직전 `edbfad5b...`는 `steelsearch-before-fallback-nested`, debug는
  `steelsearch-fallback-nested-debug`로 보존했다. 빌드/테스트 종료 후 dev 산출물만
  정리해 여유 약 17GB(사용률 84%)를 확보했고, 바이너리와 증거는 유지했다.
- `live-fallback-nested-path-release`에서 실제 참조 재검증도 위 debug와 동일하게
  모든 fixture 통과/runner 종료 0이다. 바이너리/fixture 불변 검증 true, 참조는
  OpenSearch 3.7.0-SNAPSHOT. execution SHA-256:
  `ce5764c56f79ac8f45c58db9f6a58645158e440989d2573a6ab842c7f85e40cc`.
- `target/core-replacement-c05/fallback-nested-repeated-full`에서 최초 v0.6.0 고정
  전체 반복 성능 게이트를 실행 중이다. 빌드/기능 검증 종료 후 시작했고 동일 workload,
  고정 OpenSearch 2.19.0, baseline/candidate/OpenSearch/OpenSearch/candidate/baseline
  순서를 유지한다. plan SHA-256:
  `4fbe79bb1204bf8fefe63dc3d1b00a3bf6bffbd36dd5f0a7d78e939aa963bb80`.
  전체 판정 전 기존 numeric FAIL, 최종 수락 0/40 및 빈 ledger를 유지한다.

### C05: bool/nested release 전체 반복 게이트와 경합 관찰 (2026-09-08)

- `fallback-nested-repeated-full` 여섯 회차 전체 완료, 1098.68초(18분 19초).
  각 회차 종료 0, 12개 토폴로지 요청 오류 합계 0이다. runner 종료 1은 numeric
  FAIL이며 인프라 오류가 아니다. execution_inputs_verified=true, error 없음,
  acceptance_established=false. source `d85c710d...`와 release `e6b49b83...` 해시 불변.
  result SHA-256: `b046e79c2e590158e68a1d28f08f03960b940107a6638d273631ed166851c227`.

| 후보 회차 | 공개 v0.6.0 대비 | 대응 v0.6.0 재측정 대비 | 기준 자체 공개 대비 변동 |
| --- | --- | --- | --- |
| 01 | 24/44 | 24/44 | 39/44 |
| 04 | 41/44 | 43/44 | 41/44 |

- 후보 01은 단일 노드 22개 지표는 통과했지만 3노드 20개 지표가 초과했다.
  공개 대비 처리량 **-8.028852%**, refresh p99 **+55.613107%**가 대표적이다.
  대응 baseline 00 대비도 처리량 **-5.931111%**, refresh p99 **+46.717143%**다.
  write/lexical/ranking/facet/sort_filter/nested/refresh 전반의 mean 또는 tail 초과가
  동반됐다. 개별 20개 지표 및 절대값/상한은 result.json의 첫 check에 모두 보존했다.
- 후보 04는 3노드 22개 지표가 공개 기준 이내였고, 단일 write p95 **+6.293447%**,
  write p99 **+5.726937%**, sort_filter p95 **+6.357429%**가 초과했다. 대응 baseline 05
  대비는 단일 refresh p99 **+5.161886%**가 유일한 초과다. 회차를 평균내거나
  양호한 회차만 선택하지 않으며 두 후보 결과 모두 정상 수락을 막는다.
- baseline 00 자체도 공개 대비 단일 write p95 +5.744590%, 3노드 ranking p99
  +7.899888%, facet p99 +8.633536%, nested p99 +8.199547%, refresh p99 +6.063344%.
  baseline 05는 3노드 lexical p99 +6.745918%, ranking p99 +5.735775%, nested p99
  +6.200638%로 변동했다. 이는 별도 진단 근거이며 후보 초과 면제 근거가 아니다.

| 후보 회차 | 토폴로지 | 후보 ops/s | 공개 v0.6.0 대비 처리량 | 대응 OpenSearch ops/s | 후보/참조 |
| --- | --- | --- | --- | --- | --- |
| 01 | 단일 | 758.1322 | +2.035117% | 281.4718 | 2.693457x |
| 01 | 3노드 | 856.5917 | -8.028852% | 115.8724 | 7.392542x |
| 04 | 단일 | 744.5895 | +0.212436% | 286.9829 | 2.594543x |
| 04 | 3노드 | 922.8379 | -0.916076% | 116.1985 | 7.941909x |

- 고정 workload/개발용 durability/OpenSearch 2.19.0 비교이며 운영 동등성 주장이
  아니다. nested fixture 통과와 고정 성능 시나리오를 서로 대체 증거로 사용하지 않는다.
- 종료 후 3노드 후보의 runtime_evidence 전후 cgroup 카운터를 대조했다. 세 PID가
  공유하는 동일 tmux scope이므로 첫 PID의 동일 경로를 한 번만 비교했고 합산하지 않았다.
  후보 01의 관찰 구간 65.012774초에서 CPU full-pressure total은
  700309989 -> 703353278us(**+3.043289초**), CPU usage는 +124.814782초다.
  후보 04의 65.057992초 구간은 full-pressure 719432147 -> 720094317us
  (**+0.662170초**), CPU usage +135.646051초다. 양쪽 nr_throttled/throttled_usec는
  0 -> 0이다. 관찰 구간은 부하 준비를 포함하며 정확히 timed 60초만의 측정이 아니다.
- 공유 scope에는 후보 외 프로세스도 포함된다. 위 차이는 CPU 경합/스케줄링 조사의
  우선순위 근거이지 외부 간섭, 코드 무관성, 단일 구현 원인을 입증하지 않는다.
  다음은 보존 직전 후보 `steelsearch-before-fallback-nested`와 현재 후보의 동일 조건
  진단, 실제 경로별 작업량 및 CPU pressure 동시 비교다. 진단이 전체 게이트를 대신하지
  않으며 최적화 후에는 최초 v0.6.0 고정 전체 반복을 다시 실행한다.
- 소유 cargo/rustc/steelsearch/java와 벤치마크 컨테이너 종료 확인, 기존 사용자
  컨테이너 5개 유지, `git diff --check` 통과. C05 전체 수락과 릴리즈는 보류한다.
  최종 수락 **0/40**, 빈 ledger 유지. 단일 구현의 5% 이상 기여 및 최적화 불가를
  입증하지 않아 제외하지 않았다. 커밋/태그/게시 없음.

### C05: 직전/현재 후보 CPU 진단과 host 관측 보강 (2026-09-08)

- 직전 턴은 nested 의미 수정 및 release 전체 반복 증거를 확보한 progress다.
  이번에는 제품 코드/바이너리를 변경하지 않고 직전 후보 `edbfad5b...`와 현재
  `e6b49b83...`의 원인을 분리했다. 기존 `run-core-cpu-diagnostic.py`를 재사용해
  직전/현재/현재/직전 순으로 3노드 mixed workload를 각 45초 실행하고, 실행 내부의
  20초 동안 49Hz CPU-clock/DWARF 샘플을 수집했다. 각 실행은 diagnostic_only이며
  전체 게이트의 대체 증거나 릴리즈 수치가 아니다. CPU 샘플은 off-CPU 지연을 설명하지 않는다.

| 순서 | 후보/디렉터리 접미어 | 진단 ops/s | refresh p99 ms | 관찰 CPU초: 부하 생성기 / 서버 합계 |
| --- | --- | --- | --- | --- |
| 1 | 직전 / `fallback-cpu-before` | 950.6966 | 20.8974 | 16.02 / 29.15 |
| 2 | 현재 / `fallback-cpu-after` | 904.1972 | 25.2020 | 13.54 / 25.27 |
| 3 | 현재 / `fallback-cpu-after-second` | 909.4684 | 24.0233 | 13.66 / 25.45 |
| 4 | 직전 / `fallback-cpu-before-second` | 902.8513 | 25.4498 | 13.45 / 25.14 |

- 모든 matrix/perf 종료 0, 요청 오류 0, 실제 서버/부하 생성기 PID와 start_ticks,
  선택 바이너리 및 실행 후 해시를 검증했다. 위 CPU초는 각 약 20.8~20.9초 관찰
  구간이고 ops/s는 45초 전체 값이라 나누어 요청당 CPU 비용으로 간주하지 않는다.
  직전 후보 자체도 두 번째 실행에서 낮아졌으므로 첫 쌍의 차이를 새 bool/nested
  변경 하나에 귀속할 수 없다. 시간 변동/실행 상태/프로파일 영향의 원인 분리는 남는다.
- 첫 쌍의 CPU 상위 독립 심볼은 Python 프레임 평가/할당, memcmp, 기존 집계 수집,
  mimalloc, JSON 숫자 직렬화였다. 집계 수집의 샘플 비중은 2.86%/3.01%였다.
  현재 후보의 독립 심볼 목록에 새 fallback 평가/경로 추출 함수는 관찰되지 않았지만,
  인라이닝과 표본 누락 때문에 미실행 또는 비용 부재를 증명하지는 않는다.
- 공유 cgroup pressure만으로 guest CPU steal과 내부 CPU 경합을 구분할 수 없어
  `tools/benchmark_runtime_evidence.py`에 host aggregate CPU 관측을 추가했다.
  `/proc/stat` 첫 cpu 행의 raw ticks, SC_CLK_TCK, boot_id, 관찰 시작/종료 시각을
  기록한다. guest는 user/nice에 중복 포함되고 iowait는 감소할 수 있음을 명시하며,
  누락/잘못된 형식은 null/error로 남긴다. 기존 runtime 설정 불변 검사는 바꾸지 않았고
  관측값 변화는 정상이다. 이전 증거에 새 필드를 소급 추가하지 않았다.
- 통합 smoke `fallback-host-cpu-smoke`도 같은 현재 바이너리의 진단 실행이다.
  종료 0, 오류 0, 944.1551 ops/s이며 다른 네 실행과 함께 보존했다. 새 host 필드는
  실제 수집됐고 동일 boot_id/100Hz에서 steal 1072061 -> 1072084 ticks,
  즉 **+0.23 CPU초**였다. 관찰 구간 약 50.027초는 준비와 45초 부하를 함께 포함한다.
  과거 느린 회차에는 host ticks가 없어 이 값으로 과거 원인을 단정하지 않는다.
- runtime/cgroup/performance-gate/CPU-diagnostic/failure-diagnostic/report 회귀
  **64/64** 통과(0.415초). 음수/비정수/짧거나 예상 밖 cpu 행, 선택 필드 누락,
  파일 누락, guest 보존, host counter 변동 허용 및 실제 capture 연결을 확인했다.
  제품 변경은 없어 새 제품 전체 게이트를 실행하지 않았고 기존 정식 FAIL을 유지한다.
  향후 전체 측정은 새 수집기 해시를 사전 고정해야 한다.
- 증거 SHA-256(디렉터리는 모두 `target/core-replacement-c05/` 아래):
  - before diagnostic: `3b5dee46a5e4960fa05745f52f6530cc6a9eb9961ebf6274637abe6dbbe5fea4`
  - after diagnostic: `c6861eaee884043e3d36ef6e2d11647d9a206f3f41da753b8574dba7f497babe`
  - after-second diagnostic: `6f1aeb85fc78f6f3161c7c2e7a00283cfe754e1da43db8bc95b2064612d34909`
  - before-second diagnostic: `13ead08c2116234e95effe7a4e3e3538ff6f974aafdde68fbfc0a673495d76d2`
  - host smoke diagnostic: `83e3578916d697db40b1970359d2c63dc1c864e40928942dbe8946e0e0b5280e`
  - host smoke summary: `c13f699df97c67f549c8556a6443a721ef97e407a944ed22d37168fd20a66521`
  - runtime collector: `28ef67b0e839d6cf2dc3d5a00534fea68e915f45124258ad27dd33b47560923e`
  - runtime tests: `ea01f731ed883f8b47dce27dd221a3a4f5cf008e05a4a33a02c23d3e1c03869a`
- 다음 작업은 host CPU/pressure를 포함한 동일 조건의 비프로파일 진단과
  실제 fallback 실행 경로 확인이다. 최종 수락 0/40 및 빈 ledger 유지. 단일 구현의
  5% 이상 기여와 최적화 불가가 입증되지 않아 제외하지 않는다. 릴리즈/커밋/태그 없음.

### C05: 비프로파일 순서 반전 진단 (2026-09-08)

- 직전 턴은 CPU 진단 및 host 관측 보강을 확보한 progress다. 새 host 관측으로
  프로파일 없는 직전/현재/현재/직전 순서의 진단을 실행했다. 조건은
  `target/core-replacement-c05/fallback-unprofiled/plan.json`에 먼저 고정했다.
  제품 코드와 바이너리, 수집기 해시는 변경하지 않았다. 각 3노드 60초, 5000문서,
  384차원 source, 4클라이언트, 3샤드/replica 1, seed 13, timeout 10초,
  기존 7개 시나리오 혼합이며 단일 노드/OpenSearch를 포함한 전체 게이트가 아니다.

| 순서/디렉터리 | 후보 | ops/s | refresh p99 ms | host steal 증가 CPU초 | 공유 cgroup full-pressure 증가 초 |
| --- | --- | --- | --- | --- | --- |
| 00-before | 직전 edbfad5b | 913.9517 | 23.4540 | 0.28 | 0.579298 |
| 01-after | 현재 e6b49b83 | 925.0692 | 22.2729 | 0.26 | 0.623352 |
| 02-after | 현재 e6b49b83 | 928.0758 | 22.9236 | 0.26 | 1.028887 |
| 03-before | 직전 edbfad5b | 942.7976 | 21.4208 | 0.27 | 0.614513 |

- 네 실행 모두 종료 0/요청 오류 0, 실제 바이너리 식별 일치, 관찰 전후 boot_id
  동일이다. host 값은 SC_CLK_TCK=100, cgroup은 세 PID의 공유 scope를 한 번만
  비교했다. 두 카운터의 관찰 구간은 준비 단계도 포함하므로 timed 60초와 동일하지 않다.
- 00/01 쌍은 직전 대비 3노드 22개 지표 모두 5% 이내였다. 03/02 역순 쌍은
  18/22이며 lexical p99 **+7.311758%**, write p99 **+6.628745%**, refresh p95
  **+5.892517%**, refresh p99 **+7.015532%**가 초과했다. 평균/percentile 병합 없이
  모든 회차를 남겼다. 진단 22개만으로 정식 44개 게이트를 통과 처리하지 않는다.
- 이번에는 5% 이상 처리량 저하가 재현되지 않았다. host steal의 규모도 네 회차가
  비슷해 단독 원인으로 볼 근거가 없다. 02의 full-pressure 증가가 더 컸지만 공유
  scope/구간 집계이므로 개별 tail 요청과의 인과관계는 아직 증명하지 못했다.
  과거의 큰 3노드 저하나 현재 남은 tail 초과를 면제하지 않는다.
- 정적 경로 확인: 고정 nested 요청은 events.kind/status의 bool must이며
  native 허용 조건에 맞는다. REST handler는 native 응답 생성에 성공하면 반환하고,
  실패 시 fallback으로 갈 수 있으므로 정적 코드만으로 실제 미진입을 증명하지 않는다.
  다음 원인 분리에는 요청 지연과 CPU/refresh 작업의 동시 관측 및 실제 경로 확인이
  필요하다. 독립 비교에서 재현되지 않은 처리량 저하를 이유로 기능을 제외하지 않는다.
- SHA-256:
  - plan: `c9e017919dd2cbcc6229696f9eaaa1014ad1cf9e618360ef9d58f8fab12e08f7`
  - 00 summary: `c2bd42adbcd058ade6b8fd693e70eae5723ccb4c7a11c5fe424b2ca3988ccac7`
  - 01 summary: `c45dfb5a9ef2ec988c6d779d0b6ebc630d8615dc72260310c0670a1be9edeb2f`
  - 02 summary: `ab8b2719c5343b95624427fcfc32413da1f641b7af3a3a8975066aa63bbdeeba`
  - 03 summary: `04c0452cf7d94792caf8dbdbd3bb83fab1415747ccda54031b7bf4b3d589cafd`
- 제품 변경 없이 진단을 진행했으므로 새 제품 전체 게이트는 실행하지 않았다.
  기존 정식 numeric FAIL, 최종 수락 0/40, 빈 ledger 및 릴리즈 보류를 유지한다.

### C05: 요청/CPU 타임라인 진단 (2026-09-08)

- `tools/benchmark_timeline.py`와 부하 생성기/matrix에 기본 비활성
  `--diagnostic-timeline`을 추가했다. 요청 종류, 클라이언트 번호, 시작/소요 시간,
  HTTP 상태만 기록하며 본문/URL/예외 메시지는 남기지 않는다. 요청 100000건,
  CPU 표본 4096개로 제한하고 초과 건수는 명시한다. host CPU/pressure는 250ms
  간격과 시작/종료 시점에 수집한다. 이는 공유 host 관측이며 요청별 CPU 귀속이 아니다.
- 원시 타임라인은 별도 `baseline.timeline.json`에 배타적으로 생성한다. summary에는
  경로/크기/SHA-256/건수만 남겨 대량 표준 출력 중복을 방지했다. 기존 첫 진단의
  원시 inline 증거는 변경하지 않았다. 새 의존성은 전체 게이트의 실행 파일 해시
  고정 목록에 추가했다. 진단 플래그 또는 timeline이 있는 보고서는 정식 검증에서
  거부하며, 바깥 diagnostic 표시만 제거해도 통과하지 않는다.
- `target/core-replacement-c05/fallback-timeline`의 3노드 60초 진단은 요청
  **56369건**, CPU 표본 **238개**, 요청 오류/기록 누락 **0건**이다. 가장 느린
  12건 중 10건은 refresh였고 나머지 facet 2건도 refresh와 겹쳤다. 긴 요청은
  원래 다른 작업과 겹칠 확률이 높으므로 이것만으로 인과관계를 주장하지 않는다.
  250ms CPU 표본은 20~30ms 개별 tail 원인 구분에는 너무 거칠다.
- 최종 sidecar smoke `fallback-timeline-final-smoke`는 3노드 10초, 요청
  **10545건 전부 성공**, CPU 표본 **41개**, 누락 **0건**이다. 첫 표본부터
  마지막 표본까지 모든 요청 구간을 포함하는지와 sidecar 해시 일치를 확인했다.
  짧고 계측된 실행이므로 처리량을 릴리즈 지표나 5% 합격 근거로 사용하지 않는다.
- timeline/report/gate/runtime/CPU/failure/load evidence 회귀 **72/72** 통과
  (0.557초). 저장 한도, 오류 정보 제한, 별도 파일 덮어쓰기 거부, 기본 비활성,
  성공/실패 요청 수집, 종료 후 thread 회수, 중복 종료 및 재시작 금지,
  시작/종료 표본의 요청 구간 포함을 검증했다.
- refresh 정적 조사: 엔진은 인덱스별 `refresh_lock` 획득 후 목표 sequence 번호를
  읽는다. 따라서 대기 중 추가된 쓰기도 목표에 포함될 수 있다. 기존
  `refresh_targets_request_time_sequence_number` 테스트는 Busy 계획 대기를 검사하며
  owner lock 대기 상황의 병합 동작을 직접 검증하지 않는다. 다음 작업은 이 경계의
  결정적 동시성 테스트 및 실제 비용 확인이다. 락 앞에서 목표를 읽는 최적화는
  쓰기 가시성, 비 append 변경, 동일 이름 재생성, REST fallback 가시성 경계까지
  검증한 뒤 판단한다. 현재 제품 동작은 변경하지 않았다.
- SHA-256:
  - 최종 smoke summary: `5eacd2b044b4a33a3c835df0aba4c987f84e807f3ede44495b01b4b62d57162d`
  - 최종 smoke timeline: `c53d20dd3d403c6b09dc3137d149baf5e1b92b99daeff03ed68564a1f2bed1de`
  - 수집기: `386bd5907ac490ecbaf405df041e0a140c3ca75795039387889c59d7744f45a3`
  - 제품 바이너리(변경 없음): `e6b49b8357783bf30f354ab8a696eab828123b09c502d4aea95ab7c79d30526d`
- 이번에는 진단 도구만 변경했다. 새 제품 전체 게이트는 실행하지 않았으며,
  기존 정식 FAIL, 최종 수락 **0/40**, 빈 제외 ledger와 릴리즈 보류를 유지한다.
  향후 제품 구현 단위의 완료 전에는 초기 v0.6.0 대비 전체 반복 게이트를 실행한다.

### C05/C04: refresh owner 대기 경계 검증 (2026-09-08)

- 직전 타임라인 진단은 실제 요청/CPU 증거와 도구 변경을 확보한 progress다.
  이번에는 제품 최적화 전에 engine의 owner lock 경계를 결정적 테스트로 검증했다.
  `queued_refreshes_coalesce_and_include_writes_before_owner_acquisition`은
  테스트가 owner lock을 점유한 상태에서 두 refresh가 같은 index identity를
  확보했음을 확인하고 변경을 넣은 뒤 락을 해제한다. 일정 시간 잠들었다는
  사실만으로 대기 시작을 추정하지 않으며 identity 대기는 5초로 제한한다.
- 단일/3샤드 각각에 대해 대기 중 변경 없음, append, 기존 문서 update, delete의
  **8개 조합**을 실행했다. 두 응답 중 정확히 하나만 `refreshed=true`이고 후속
  refresh는 false였다. 검색 ID/건수/문서 내용과 최종 sequence watermark가
  일치했다. 따라서 새 쓰기가 없는 동일 목표 refresh의 병합은 이미 작동한다.
  단순한 중복 refresh 제거를 새 최적화로 추가할 근거는 확보되지 않았다.
- 전체 engine 회귀 **848/848** 통과(10.03초), 로그를 보존한 재실행도
  **848/848** 통과(9.61초)했다. 기존 request-time Busy 대기 및 동일 이름의
  index 재생성 거부 테스트도 포함한다. 기존 플러그인 관련 회귀가 같이 실행됐다는
  사실을 플러그인 지원 범위 확대 또는 코어 패키지 완료로 해석하지 않는다.
- 이번 테스트는 owner 획득 전후의 기능 경계 증거이지, 실부하 tail 비용 귀속
  증거가 아니다. 대기 중 계속 유입되는 쓰기와 실제 REST 경로의 중복 replay 비용은
  여전히 분리해야 한다. 현재 구현은 owner 획득 후 목표를 읽으므로 대기 중 들어온
  쓰기를 포함하며, 이 경계를 앞당기는 변경은 적용하지 않았다.
- 다음 C04 검증 지점: REST의 `replay_deferred_native_writes_before_refresh`는
  pending snapshot을 처리한 뒤 index별 pending delete 목록을 제거하고,
  `mark_runtime_documents_refreshed`는 당시의 unrefreshed 목록 전체를 공개 표시한다.
  snapshot 이후의 동시 쓰기/삭제가 처리되지 않은 채 목록에서 제거되는지
  단계별 재현이 필요하다. 아직 이 정적 관찰만으로 실시간 결함 확정을 주장하지 않는다.
  전역/대상 refresh, deferred/non-deferred 쓰기, 동일 ID update/delete/recreate,
  native/fallback 검색 및 다음 refresh 이후 가시성을 함께 검사해야 한다.
  재현 시 처리한 문서/삭제의 세대와 일치하는 항목만 완료 처리하도록 수정하고,
  오류 전파 및 index 재생성 경계를 보존한 뒤 전체 반복 성능 게이트를 실행한다.
- 증거:
  - 로그: `target/core-replacement-c05/queued-refresh-engine-tests.log`
  - 로그 SHA-256: `93b1ea4e614deaf514e37a7bcfa333da99cb43c17e3b81b24f9c765cf8041b7c`
  - engine source SHA-256(테스트 추가): `9c8d5cc9002aadddd5052a21bb2d4b1dd7ac70920a57b570079f50682caa39d9`
  - 제품 바이너리 SHA-256(변경 없음): `e6b49b8357783bf30f354ab8a696eab828123b09c502d4aea95ab7c79d30526d`
- 제품 실행 코드는 변경하지 않았고 새 전체 성능 게이트도 실행하지 않았다.
  최신 정식 FAIL, 최종 수락 **0/40**, 빈 제외 ledger를 유지한다. 단일 구현의
  5% 이상 기여와 최적화 불가가 입증되지 않았으므로 기능을 임의로 제외하지 않는다.

### C04: refresh 완료 시 새 쓰기의 pending 상태 보존 (2026-09-08)

- 직전 owner 경계 테스트는 중복 refresh 병합을 확인한 progress다. 이번에는
  엔진 공개 후 REST 완료 전 새 문서를 넣는 단계별 테스트로 결함을 재현했다.
  수정 전 `refresh_completion_keeps_later_runtime_writes_pending`은 단일 샤드에서
  실패했다. 새 문서가 엔진에는 공개되지 않았는데 runtime에서는 refreshed=true가
  되어 다음 deferred replay 대상에서도 빠질 수 있는 경로다. 수정 전 로그를 보존했다.
- 전역/대상 refresh는 시작 시 pending 문서의 Arc 참조를 포착한다. 완료 시 현재
  문서가 그 참조와 동일할 때만 공개 표시하고 pending key를 제거한다. 나중에 추가된
  문서 및 update/delete-recreate/index-recreate로 바뀐 세대는 남긴다. 소스 전체를
  snapshot용으로 복제하지 않는다. 엔진 refresh가 Err이면 REST 오류를 반환하며
  문서를 공개 완료로 표시하지 않는다. 기존 crash-hook flush는 새 helper 서명에
  맞췄으며 이 특수 경로의 기존 순서는 바꾸지 않았다.
- 단일/3샤드 append 경계, 동일 문서 update, 문서 delete/recreate, 인덱스
  delete/recreate를 검증했다. 다음 전역/대상 refresh 뒤 native 및 강제 fallback
  검색의 건수/문서 내용이 맞는다. 지연 쓰기 환경변수 1에서도 새 테스트 2개가
  통과했다. 이는 결정적 단계별 재현이며 실제 병렬 HTTP 스트레스 전체를 대신하지 않는다.
- 테스트: node lib **627/627** (4.93초, 로그 재실행 5.66초), binary 직렬
  **459/459** (17.63초, 로그 재실행 17.21초), deferred focused **2/2** (0.12초).
  최초 binary 명령은 standalone-runtime feature 누락으로 실행 전 거부됐으며
  기능을 지정한 실제 실행은 모두 통과했다.
- 아직 남은 범위: pending delete snapshot 처리 후 신규 삭제가 일괄 제거되는지,
  replay 실패/동시 재생성의 세대 경계, 기존 버전의 fallback 검색 가시성,
  refresh 오류 주입과 실제 병렬 HTTP 원장 비교는 이 수정만으로 완료되지 않았다.
  특히 이번 변경을 전체 C04 완료 또는 분산 refresh 원자성 보장으로 확대하지 않는다.
- 증거 SHA-256 (`target/core-replacement-c05/`):
  - 수정 전 실패 로그 `refresh-visibility-before.log`: `71a10a4ea459dc7d2246fbba637c85bf4db2fb4ec20e88832143cfbc7a0a5f88`
  - node 로그 `refresh-visibility-node-tests.log`: `51839f3f8e77b0862a8c46578244d7d83916382a4dd1161c3f1df1fbe8d131de`
  - binary 로그 `refresh-visibility-binary-tests.log`: `ee569d2a3d8af8731337b6e7f1abe9012a3bdfc90eed108e37c15a1d9210b648`
  - deferred 로그 `refresh-visibility-deferred-tests.log`: `1db9df7e3304a9a93882896dcd664a4268248bd2648bbf06e14e201f107b2621`
  - standalone source: `e910ee8ed827749eed8bb28d6b6f359516281eedf7d265a3f8220b6901652baf`
  - 보존한 직전 바이너리 `steelsearch-before-refresh-visibility`: `e6b49b8357783bf30f354ab8a696eab828123b09c502d4aea95ab7c79d30526d`
- 릴리즈 빌드/실시간 기능 비교/초기 v0.6.0 대비 전체 반복 성능 게이트는 이 기록
  시점에 미완료다. 완료 승인, 릴리즈, 제외 ledger 추가는 하지 않는다. 최종 수락 0/40.

#### 빌드/실시간 비교 및 전체 반복 실행 결과

- 릴리즈 빌드 완료(4분 56초). 현재 실행 파일 SHA-256은
  `6c4c3d0d3dd948657075eee35499e144f35091bb0be6718ef3f49e16e2e21300`이다.
  빌드 로그 SHA-256: `e8e72be5846c25eaa35f8f119321b9b6e26d7bdb5d19fd9baf97a3fdc52926e7`.
- `live-refresh-visibility-release` 실시간 비교 종료 0. OpenSearch 3.7.0-SNAPSHOT
  대비 core 1180, 추가 fixture 571 (10+10+23+8+200+160+160) 통과, 실패/skip 0.
  count/alias/PIT probe도 passed=true. 실제 바이너리 식별과 실행 후 바이너리/fixture
  불변 확인 완료. execution SHA-256:
  `ddb363966f5a5421512f33d56f4bd0be474025143bbb8594c54e07499a28e7c5`.
- `refresh-visibility-repeated-full` 전체 6회/12토폴로지 실행 완료
  (1096.929초, 약 18분 17초), 모든 하위 실행 종료 0 및 요청 오류 합계 0.
  기존 고정 7시나리오/60초/5000문서/4클라이언트/3샤드 조건과
  OpenSearch 2.19.0 이미지/512MB heap을 사용했다. profiler/timeline은 비활성이다.
- 최종 runner는 **종료 2, execution_inputs_verified=false**로 거부됐다.
  오류는 `executed configurations differ`다. 신규 부하 생성기의 실행 config에는
  `diagnostic_timeline=false`가 있고 최초 v0.6.0 보고서에는 필드가 없었다.
  원시 보고서와 실패한 result/plan을 수정하거나 성공으로 바꾸지 않았다.
- `core_performance_reports.py`는 이제 해당 옵션의 누락과 literal false만
  동일한 비활성 상태로 정규화한다. true, null, 숫자 0, 빈 문자열/배열/객체 및
  timeline payload는 거부한다. 다른 미지의 실행 옵션 차이도 계속 거부하며
  입력 보고서는 변경하지 않는다. 관련 전체 Python 회귀 **75/75** 통과(0.569초).
- 새 검증기로 기존 6회 중 후보 두 회차를 published/paired 기준에 각각 별도
  재평가했다. 아래는 **보존된 artifact의 사후 수치 평가**이며 원래 runner의
  실패 상태를 승격하거나 수정된 검증기의 새 전체 실행을 대신하지 않는다.

| 후보 회차 | published 기준 5% 이내 | paired 기준 5% 이내 | 단일 refresh 평균: published 대비 | 단일 refresh 평균: paired 대비 |
| --- | --- | --- | --- | --- |
| 01 | 41/44 | 37/44 | +9.067187% | +11.431351% |
| 04 | 33/44 | 36/44 | +10.441104% | +9.141523% |

- 01 published 실패는 single refresh mean/p99와 three ranking p99다.
  04 published 실패는 single ranking/facet/sort_filter p95/p99, refresh
  mean/p95/p99, three ranking/nested p99다. paired 실패 목록을 포함한 모든
  지표는 별도 revalidated JSON에 보존했다. 처리량 개선으로 지연 초과를 상쇄하지 않는다.
- 다음 최적화는 capture와 deferred replay의 중복 순회/문서 복제 비용을
  분리하는 것이다. 시작 시 포착한 문서를 replay에서도 공유할 수 있는지 확인하되,
  새 쓰기를 pending에서 누락시키는 기존 동작으로 되돌리지 않는다. 수정 전
  `e6b49b83...`와의 독립 비교가 없으므로 위 누적 초과 전체를 이번 변경 하나에
  귀속하지 않는다. 최적화 불가도 입증되지 않았으므로 제외 ledger는 비워 둔다.
  다음 제품 변경 뒤에는 새 검증기 해시를 고정한 새 전체 반복 실행이 필요하다.
- 증거 SHA-256 (`target/core-replacement-c05/`):
  - 원래 full plan: `0f58043cd183c997f708abe353f5020c6cab27bbdde3fb460d337021fd4a9d03`
  - 원래 full result: `a6922c2a36c74d89c80cf64add419141062f5760ccd21946dcf878308256ba37`
  - `refresh-visibility-published-01-revalidated.json`: `530c680ce4b273493688b60503d8b2dedaaf893c8a2a686945c7a38f44486aab`
  - `refresh-visibility-published-04-revalidated.json`: `28fac6b2abf736beef6e15e8c5932fde9838bd2aaf2f0014674c28ae7177240c`
  - `refresh-visibility-paired-01-revalidated.json`: `a45f53b564f035dc292d791d80faa60ac45cbb87f3e5d90095fb65e86b0d4509`
  - `refresh-visibility-paired-04-revalidated.json`: `7a03bf3a0277d6470d69d341606f370b69db555fe25fe24507f111bbeeffaf57`
  - 새 report validator: `2edae31d99350cacc8bb123e4a8b17724ed2fad7eb512985631da4775dc2f7d0`
  - validator tests: `733d57d2aaecc73488787f56deacf0d3c85f880cf36b1a39b90e28d2bc45c4c2`
- 최종 수락 **0/40**, 릴리즈 보류 유지. 이번에는 실제 결함 수정과 전체 측정,
  검증기 오류 수정까지 진행했지만 성능 합격이나 C04 완료를 선언하지 않는다.

### C04: refresh 문서 복제 비용 절감 (2026-09-08)

- 직전 턴은 가시성 결함 수정/전체 측정/검증기 오류 수정을 확보한 progress다.
  이번에는 문서를 포착하는 시점과 세대 판별 조건을 그대로 두고 복제 비용을 줄였다.
  deferred replay의 임시 mutation 목록은 StoredDocument 전체 복제 대신 기존
  SharedStoredDocument(Arc)를 공유한다. 엔진의 소유 값 API에 전달할 source 복제는
  유지한다. capture와 replay의 순회/포착 시점 통합은 적용하지 않았다.
- 완료 helper는 captured map을 소유권으로 받아 동일 Arc 세대인지 검사한 뒤
  해당 captured 참조를 해제한다. 이후 `Arc::make_mut`으로 refreshed 표시를 바꿔
  유일 소유 문서는 재할당하지 않고, 기존 독자/다른 refresh가 보유한 문서는 COW로
  분리한다. 새 쓰기를 pending에서 누락시키던 동작으로 되돌리지 않는다.
- 새 테스트는 독자 없음/있음 양쪽에서 문서 주소 유지 또는 COW 분리, 기존 독자의
  refreshed=false 유지, 384개 숫자 배열을 포함한 source 불변을 검사한다.
  node **628/628**(4.92초), binary 직렬 **459/459**(17.78초), deferred 모드의
  refresh 완료 경계 테스트 **3/3**(0.11초) 통과.
- 지난 6회 보고서에 수정된 assessor 전체를 사전 적용해 두 비교 묶음이
  형식 오류 없이 수치 판정까지 진행됨을 확인했다. 이는 기존 보고서 검증기
  점검일 뿐 새 후보의 성능 합격이나 새 전체 실행이 아니다.
- `target/core-replacement-c05/` 증거 SHA-256:
  - node 로그 `refresh-copy-node-tests.log`: `93e2392eb67d04e10f62118a4098937970c09d08a275cb8e4c9cd3e64251cf61`
  - binary 로그 `refresh-copy-binary-tests.log`: `8a9020d9271a78187a0bf618807e6f053c25de83622b25d877f15469f2910119`
  - deferred 로그 `refresh-copy-deferred-tests.log`: `f3f3fb6f7984c9cb4cee133b096eece9bc0b0373eb47b6a90bd5da0f8aadda28`
  - standalone source: `ff1bfa3221cbb4ef494b4aaeda1b4a3321b747eb282db48697259c8452f5c259`
  - 보존한 직전 후보 `steelsearch-before-refresh-copy-reduction`: `6c4c3d0d3dd948657075eee35499e144f35091bb0be6718ef3f49e16e2e21300`
- 이 기록 시점에 릴리즈 빌드가 진행 중이다. 새 실제 기능 비교 및 수정된
  검증기 해시를 고정한 전체 반복 성능 게이트 전에는 완료 처리하지 않는다.

#### 새 바이너리 검증 및 전체 성능 결과

- 릴리즈 빌드 완료(4분 41초), 바이너리 SHA-256
  `9fd8e71a324f378471c1b17a22a6262ca21c8ea99741f609f5b87ede8863b93c`.
  빌드 로그 SHA-256: `bba1df071e82ed6ec164be0aa19eeaf587ca86293e0863438f6ca69f6e85313c`.
- `live-refresh-copy-release` 실시간 기능 비교 종료 0. core 1180 및 추가
  fixture 571 모두 통과, 실패/skip 0. count/alias/PIT probe도 passed=true이며
  실행 전후 바이너리/fixture 불변 확인 완료. execution SHA-256:
  `8ba8e0314ac1f3d18104a68aff34ef5550e2b439d94fb21f65921a6a82953129`.
- `refresh-copy-repeated-full`은 수정된 report validator를 사전 고정한 **새**
  전체 실행이다. 6회/12토폴로지 모두 종료 0, 요청 오류 합계 0, 총 1096.182초
  (18분 16초). 최종 runner **종료 1, numeric FAIL**,
  `execution_inputs_verified=true`, error 없음. 이전 형식 오류는 재발하지 않았다.
  고정 v0.6.0/7시나리오/단일 및 3노드 조건을 유지했고 계측 timeline/profiler는 껐다.

| 후보 회차 | published 기준 5% 이내 | paired 기준 5% 이내 | baseline drift 5% 이내 | 단일 refresh 평균: published 대비 | 3노드 refresh 평균: published 대비 |
| --- | --- | --- | --- | --- | --- |
| 01 | 37/44 | 37/44 | 43/44 | +9.032232% | +0.846363% |
| 04 | 37/44 | 35/44 | 44/44 | +10.871273% | +2.595032% |

- 01 published 실패: single ranking p95/p99, facet p99, sort_filter p95,
  refresh mean/p95/p99. 04 published 실패: single facet p99, sort_filter p95/p99,
  refresh mean/p95/p99 및 three ranking p99. 각 paired 실패와 baseline drift도
  result.json에 보존했다. 첫 baseline drift는 three nested p99만 초과했고 두 번째는
  전부 이내였다. 따라서 후보 초과를 환경 변동만으로 면제하지 않는다.
- 처리량: 01 single 728.1525 ops/s (-1.999775%), three 935.1627 (+0.407221%);
  04 single 727.9831 (-2.022574%), three 923.5812 (-0.836278%). 괄호는
  최초 published v0.6.0 대비 변화다. 처리량의 통과로 지연 초과를 상쇄하지 않는다.
- 복제 제거의 소유권/불변성 테스트는 통과했지만 실제 단일 refresh 평균 초과는
  해결되지 않았다. 이전 후보의 사후 평가 9.07~10.44%와 새 측정 9.03~10.87%를
  실행 조건 변동을 무시한 최적화 효과로 주장하지 않는다. 다음은 누락 방지 수정 전
  `e6b49b83...`와 현재 후보의 실제 공개 문서 수, pending/replay 작업량 및 기존
  refresh 내부 시간 카운터를 동일 부하에서 비교하는 것이다. 이전에 누락됐던 문서의
  실제 처리량 증가가 원인인지 아직 증명하지 않았다. copy 비용만으로 원인을 단정하지 않는다.
- 새 full plan SHA-256:
  `a6a0beefbce7b02ae6ed5c90eae94e97f22acde538a85f836e2d341347b6e884`.
  새 full result SHA-256:
  `c4b529259ab9f8da740d5e87bec207122cac6ed2a82bea91d3e162e13a194f7d`.
- 최종 수락 **0/40**, 릴리즈 보류 유지. 단일 구현의 5% 이상 기여 및 최적화 불가가
  입증되지 않아 ledger 제외를 선언하지 않는다. 누락 방지나 독자 불변성 보장을
  성능 때문에 제거하지 않는다. pending delete 동시성 등 남은 C04 범위도 그대로 남는다.

### C04/P02: 실제 공개 문서 수와 refresh 작업량 비교 (2026-09-08)

- 직전 턴은 COW/Arc 최적화와 전체 성능 재검증을 확보한 progress다. 이번에는
  `run-core-refresh-work-diagnostic.py`로 기존 matrix의 cluster/load/runtime helper를
  재사용했다. 고정 단일 노드/3샤드/4클라이언트/5000문서/384차원 source/7시나리오,
  seed 13, 동일 개발용 deferred 설정으로 수정 전/현재/현재/수정 전 순서를 고정했다.
  모든 결과는 diagnostic_only이며 전체 게이트나 구현 수락 자료를 대신하지 않는다.
- 예상 문서 수는 fresh seed 5000 + 성공한 고유 `live-{client}-{counter}` 쓰기 수다.
  부하 종료 직후, 추가 refresh 1회 후, 2회 후의 native/강제 fallback 검색 total과
  raw stats를 기록한다. 정확한 total(eq), timeout 없음, failed shard 0을 요구한다.
  추가 관측/refresh는 timed 구간 밖이다. cardinality 확인이며 ID/본문 전수 검증은 아니다.
- 최초 smoke는 명시적 부하 실행 환경변수 누락으로 부하 시작 전 거부됐다.
  실행기에서 RUN_HTTP_LOAD_TESTS=1을 설정한 새 디렉터리의 smoke는 완료됐다.
  수정 전 e6b49b83 후보는 2초 smoke 두 회차에서 native 46/33개 부족 상태가
  두 추가 refresh 뒤에도 남았고, 현재 9fd8e71a 후보는 부족 0이었다.
- `refresh-work-abba`의 각 60초 진단 4회 모두 완료했다. 실제 바이너리 PID/해시,
  runtime 전후 불변성 및 실행 도구/계획 해시를 확인했다. 결과:

| 순서/후보 | 예상 문서 수 | 추가 refresh 2회 뒤 native | fallback | native 부족 | 진단 ops/s | refresh 평균 ms | commit 누적 초 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 00 / 수정 전 e6b49b83 | 13096 | 12150 | 13096 | 946 | 758.0607 | 7.1891 | 14.1453 |
| 01 / 현재 9fd8e71a | 12796 | 12796 | 12796 | 0 | 728.4698 | 8.0174 | 16.0318 |
| 02 / 현재 9fd8e71a | 12806 | 12806 | 12806 | 0 | 729.9171 | 8.0855 | 16.1441 |
| 03 / 수정 전 e6b49b83 | 13044 | 12087 | 13044 | 957 | 752.8007 | 7.4082 | 14.6316 |

- 현재 후보는 두 회차 모두 첫 추가 refresh 뒤 예상 total에 도달했다. 수정 전은
  fallback만 예상 수를 보고했고 native 부족은 두 추가 refresh 뒤에도 해소되지 않았다.
  따라서 빠른 수정 전 후보가 실제로 더 적은 문서를 검색에 반영했다는 차이가 있다.
  다만 commit 등 resource 누적값은 corpus 준비도 포함하므로 timed 요청당 비용으로
  단순 나누지 않는다. 지연 증가 전부의 인과관계나 최적화 불가까지 입증한 것은 아니다.
- 최초 v0.6.0의 정확한 db244133 바이너리도 별도 `refresh-work-v060-smoke`로
  2초/4회 순서 반전 확인했다. v0.6.0 두 회차의 예상/native 최종 수는
  5317/5280 및 5321/5289로 **37/32개 부족**했고 fallback은 예상 수를 보고했다.
  현재 후보 두 회차는 5309/5310개가 각각 native/fallback 모두 일치했다.
  이는 원래 published 60초 실행의 정확한 누락 수를 소급 측정한 것이 아니다.
  릴리즈 검증 문서에 역사적 속도 비교만으로 동등한 검색 작업량을 입증할 수 없음을
  추가했고, 원시 성능 보고서/아카이브/기준선은 변경하지 않았다.
- 도구/기존 gate/report/runtime 등 회귀 **78/78** 통과(0.564초).
  생산 코드/바이너리는 이번 턴에 변경하지 않았다. 최신 정식 전체 게이트 FAIL,
  최종 수락 0/40 및 빈 제외 ledger를 유지한다. 다음 최적화는 commit/refresh
  작업량과 공개 경계를 함께 검증해야 하며, 문서를 덜 공개하는 동작으로 되돌리지 않는다.
- SHA-256 (`target/core-replacement-c05/`):
  - 새 실행기: `5c19af87a0334136db0cc9b708964f3c1da8b2d011cadf1a5c5ca69a81daaae1`
  - 새 테스트: `87d39a02f0b9fb7d2ec3d20a2699c4d7bc85114932cdbd626fe3576664fbf6f5`
  - ABBA plan: `7aef0b8442898c455e8b9a22fc1a88d5f138fa2d782d848531c515ae9121f34a`
  - ABBA result: `13fc716f8a67c30547fe8b4b5121013feda815fdefeae380d8c2e18bb5c3d817`
  - v0.6.0 smoke plan: `bc3e106dcf2e8ec37a0a3f8dc7ed5bbe0f7721bd759604d64cee05b0e4638927`
  - v0.6.0 smoke result: `883f46b6a00af5ea7d4d8577759a52bc8ad0a0df8b8fc7135dd2a112c6e08ce5`
  - 도구 테스트 로그: `1087b30cb662d2123218f2897cbd8425ec431547046f44cb55e2c462c58ce9a9`

### C04: owner 대기 전 refresh 목표 포착 (2026-09-08)

- 직전 턴은 공개 문서 수 차이와 v0.6.0의 검색 누락을 실제 바이너리로 확인한
  progress다. 이번에는 인덱스 identity와 요청 목표 sequence를 같은 최초 store
  read에서 포착하도록 옮겼다. owner 대기 뒤 추가된 append가 요청 목표를
  계속 늘리지 않게 한다. 계획 수립/공개 단계의 index 세대 검사는 유지한다.
  non-append 변경의 full-refresh 및 generation 보호도 제거하지 않았다.
- 기존 owner 대기 테스트는 당시 동작의 characterization이었다. 이를
  `queued_refreshes_bound_append_work_at_request_time`으로 확장해 요청 전 문서
  공개, 두 대기 요청 병합, 대기 중 append의 다음 refresh 처리, 최종 ID/source/
  watermark를 확인한다. 단일/3샤드와 none/append/update/delete 8조합이다.
  수정 전에는 append 목표가 1에서 2로 늘어나 실패했고 수정 후 통과했다.
  이는 기존 구현의 목표 포착 위치를 바꾸는 최적화이지, OpenSearch의 동시 요청
  완료 시점을 정확히 재현했다는 주장은 아니다.
- engine **848/848**(9.68초), node **628/628**(11.53초), binary **459/459**
  (27.26초) 통과. node/binary는 직렬 실행했다. deferred 모드의 완료/세대/COW
  경계 **3/3**(0.11초)도 통과. 기존 Busy 대기와 같은 이름의 index 재생성 거부
  테스트를 포함한다. 실제 공개 문서 수 및 전체 성능 재검증은 별도로 필요하다.
- 증거 SHA-256 (`target/core-replacement-c05/`):
  - 수정 전 실패 `refresh-request-boundary-before.log`: `913efd06dc02792d2fb9ff599f39b450e5134556d16afecf1e03932f6032e79e`
  - engine `refresh-request-boundary-engine-tests.log`: `c42122d3ce7f15e234655d62580b7f42d8df4b7a3f09f70fb39ccc8c187af806`
  - node/binary `refresh-request-boundary-node-binary-tests.log`: `1df322402809ff2ce1907c185a03dcc7c408f8522dd6f9b72ef70f045ab1d7ff`
  - deferred `refresh-request-boundary-deferred-tests.log`: `f3f3fb6f7984c9cb4cee133b096eece9bc0b0373eb47b6a90bd5da0f8aadda28`
  - engine source: `debb247d42b427b0f85db0b5d9648fb3e9bff29d3874a0dd113bc56bf80ee708`
  - 보존한 직전 후보 `steelsearch-before-refresh-request-boundary`: `9fd8e71a324f378471c1b17a22a6262ca21c8ea99741f609f5b87ede8863b93c`
- 릴리즈 빌드는 4분 51초에 완료했다. 후보 바이너리는
  `82b88a0023785735b94a30f2f7897bbc9488a017aeea961fb307b30ccba38ffe`다.
  `live-refresh-request-boundary-release`에서 호환성 **1751/1751**, 실패/skip 0,
  count probe 통과 및 바이너리/fixture 불변성을 확인했다.
- `refresh-request-boundary-work-abba`의 단일 노드 60초 진단 4회는 모두
  오류 없이 완료했다. 수정 전/후/후/전의 예상 문서 수는 각각
  12787/12792/12656/12688이며, 첫 추가 refresh 뒤 native/fallback 모두
  예상 수에 도달했고 두 번째 refresh 뒤에도 일치했다.
  처리량은 순서대로 727.4391/727.7999/713.8900/717.5197 ops/s,
  refresh 평균은 8.1671/8.2813/8.2201/8.2943 ms다.
  이번 변경의 뚜렷한 속도 개선을 입증하지 못했으며, 이 진단은 전체 성능
  게이트나 ID/내용의 완전성 검증을 대체하지 않는다.
- 추가 증거 SHA-256 (`target/core-replacement-c05/`):
  - build `refresh-request-boundary-release-build.log`: `7ba9ed226ce4d4b5fc377bd5360aa50741e509f7ad4bc47ecd06e9ae8b7d78b4`
  - live `live-refresh-request-boundary-release/execution.json`: `3f07fc8be4faa35f0b381d339d7676d9b3ece0dd631c90b849ef7e212559c048`
  - ABBA `refresh-request-boundary-work-abba/result.json`: `8a74958db53184b38b69d11c3930583efdad729ba3a2b0a6d0909680da05b443`
- `refresh-request-boundary-repeated-full`에서 고정 v0.6.0/후보/OpenSearch의
  전체 6회 반복 측정을 완료했다. 1090.885초(18분 11초), 12개 토폴로지의
  요청 오류 합계 0, 모든 하위 실행 exit 0이다. 실행 입력 검증은 통과했지만
  성능 예산 FAIL로 실행기 exit 1, implementation acceptance=false다.
  전체 수락 0/40, 릴리즈 보류 및 빈 제외 ledger를 유지한다. 문서 누락을
  허용하거나 고정 v0.6.0 성능 예산을 완화하지 않는다.

| 후보 회차 | 공개 v0.6.0 대비 예산 이내 | 같은 실행 묶음의 v0.6.0 대비 | 재측정 기준선의 공개 기준 대비 |
| --- | --- | --- | --- |
| 01 | 40/44 | 37/44 | 44/44 |
| 04 | 40/44 | 41/44 | 43/44 |

- 공개 기준 대비 실패 지표(양수는 지연 증가):
  - 01: single ranking p99 +5.942838%, facet p99 +5.098965%,
    sort_filter p99 +5.020749%, refresh mean +9.696239%.
  - 04: single sort_filter p95 +8.672159%, p99 +6.562374%,
    refresh mean +5.990446%; three ranking p99 +5.903419%.
- 같은 실행 묶음의 기준선 대비 실패:
  01은 single lexical p95/p99, ranking p99, facet p95/p99,
  refresh mean 및 three refresh p95다. 04는 single sort_filter p95/p99와
  refresh mean이다. 마지막 기준선도 three lexical p99가 공개 기준 대비
  예산을 초과했지만, 후보의 다른 실패를 전부 환경 탓으로 돌릴 근거는 아니다.
- 후보 처리량과 공개 기준 대비 변화(여기는 양수가 처리량 증가):
  01 single 739.4965 ops/s (-0.473013%), three 941.0508 (+1.039418%);
  04 single 742.4933 (-0.069679%), three 930.8999 (-0.050473%).
  처리량은 예산 이내여도 시나리오별 지연 실패를 상쇄하지 않는다.
- 정식 측정 plan SHA-256:
  `6de6c573794e626c8b72282f67feb3bf293209369211181a59cb3d5977927700`.
  result SHA-256:
  `933f65dd50e8f4961ba2fc4c479784fcf5856d6ce2312214157545e00e01b58d`.
  소스/후보 해시는 앞서 기록한 값과 동일하다. 성능 참조는 고정 OpenSearch
  2.19.0 이미지이며 기능 참조 3.7.0-SNAPSHOT과 구별한다. 개발용 지연 쓰기
  프로파일이므로 운영 내구성 동등성 검증으로 확대 해석하지 않는다.

#### 다음 수정과 검증 순서 (아직 미구현)

1. refresh owner를 기다리는 요청들의 목표 sequence가 서로 다른 경우를
   결정적으로 재현한다. 실제 요청된 목표의 최대치만 고정된 batch 목표로
   공유해 commit 수를 줄일 수 있는지 검토한다. owner 보유 중 무한히 새
   목표를 따라가지 않으며, 새 index 세대는 이전 대기 요청과 공유하지 않는다.
2. 해당 최적화를 채택한다면 단일/3샤드, 서로 같은/다른 목표, 요청 이후 append,
   update/delete, Busy 재시도, index 삭제/재생성에서 문서 ID/source와 watermark,
   실제 refresh 횟수를 검증한다. 집중 ABBA 문서 수/작업량 진단 뒤 반드시
   전체 반복 벤치마크를 실행하고 최초 v0.6.0의 모든 지표에 누적 5%를 적용한다.
3. 별도 C04 수정 단위로 deferred delete 재생 후 인덱스 전체 대기 목록을
   지우는 경로를 보강한다. 재생 도중 추가/교체된 삭제를 보존하고 성공한
   동일 세대 항목만 완료 처리하도록 하며, 재생 오류를 성공으로 감추지 않는다.
   같은 ID 재생성 및 인덱스 재생성도 시험한다. 이 단위도 기능 회귀/실제 원장
   검증 후 전체 반복 벤치마크를 별도로 실행해야 하며, 앞 단위 결과를 재사용해
   완료 처리하지 않는다.

### C04: 대기 refresh 요청의 목표 병합 (2026-09-08)

- 직전 턴은 전체 반복 게이트를 완료하고 실패 지표를 확정한 progress다.
  목표를 축소하지 않고 위 다음 수정 순서의 첫 항목을 진행했다.
- `queued_refreshes_share_different_requested_targets`는 owner를 잠근 동안
  목표 1/2/3의 요청이 각각 등록되도록 동기화하고, 그 뒤 요청에 포함되지 않은
  문서를 추가한다. owner 획득 순서를 가정하지 않고 공개 작업 1회, 목표 3까지의
  정확한 ID/source/total과 최종 drain 후 목표 4를 검증한다. 단일/3샤드 대상이다.
  수정 전 실행은 단일 샤드에서 실제 공개 3회, 기대 1회로 실패했다.
- 인덱스별 `requested_refresh_seq_no` atomic 최대값에 요청 목표를 등록하고
  owner 획득 직후 한 번 읽어 append batch 목표로 고정한다. Busy 재시도 중
  새 append 요청을 계속 따라가지 않는다. 요청 자체의 완료 판정과 non-append
  generation/full-refresh 및 index identity 보호는 유지한다.
  새 생성/복구 인덱스는 독립 atomic을 갖고 검색 스냅샷은 같은 세대의 값을 공유한다.
- engine **849/849**(9.89초), node **628/628**(15.42초), binary **459/459**
  (22.71초), deferred 완료/세대/COW **3/3**(0.20초) 통과했다.
  릴리즈 빌드 4분 51초 완료, 새 후보 해시는
  `1ff7eac2f0e76df6806ae7f41587051e70d841979a40fef2a6449ce7e6b5f559`다.
  live 호환성 **1751/1751**, 실패/skip 0, count probe 및 바이너리/fixture
  불변성도 통과했다. 전체 수락 0/40, 직전 정식 게이트 FAIL 및 빈 제외
  ledger를 유지한다.
- 증거 SHA-256 (`target/core-replacement-c05/`):
  - engine source: `137e32b017fbaf7b79053f6db1d7072166c05499a0d4c4eab0b51074c0100465`
  - red `refresh-target-batch-before.log`: `b7cb8229db4e04d75c7c5442194126af55782837b7d549f2710968fc25ddf3c1`
  - engine `refresh-target-batch-engine-tests.log`: `2fa6cc7caf503d29974a922b6de587e65bf2ba5f303b15248afbb338db6edd54`
  - 보존 직전 후보 `steelsearch-before-refresh-target-batch`: `82b88a0023785735b94a30f2f7897bbc9488a017aeea961fb307b30ccba38ffe`
  - node/binary `refresh-target-batch-node-binary-tests.log`: `27d3d9d8f7a8eba269acf003dfd10e141084a40f0a242f7662d0bd0480636b47`
  - deferred `refresh-target-batch-deferred-tests.log`: `415002d088e18dc98cc9f619dd091f23a3133bbb563c13677e71a27567de914c`
  - build `refresh-target-batch-release-build.log`: `7ba9ed226ce4d4b5fc377bd5360aa50741e509f7ad4bc47ecd06e9ae8b7d78b4`
  - live `live-refresh-target-batch-release/execution.json`: `c71539abb090e3a86147b7969ec7d2430eb04e6b90c1b4338306f26bc439d5e3`
- `refresh-target-batch-work-abba` 단일 노드 60초 진단 4회 모두 오류 없이
  완료했다. 전/후/후/전 예상 문서 수 12771/12851/12868/12838은 첫 추가
  refresh 뒤 native/fallback 모두 일치했고, 두 번째 refresh 뒤에도 일치했다.
  처리량 725.5325/733.7331/735.0954/732.4045 ops/s,
  refresh 평균 8.1043/8.1128/7.8020/8.0557 ms다. 평균 지연 개선은 두 후보
  회차에 일관되게 나타나지 않아 병목 해결로 판정하지 않는다.
  이 문서 수 중심 진단은 ID/source 원장 검증이나 전체 게이트를 대체하지 않는다.
  진단 plan SHA-256 `92f1d638c1772407820d88fdec35895d966363d3254529c614660ee0892292f7`,
  result SHA-256 `e402ce3ccb1a2d4ad8503463abd02b519690ade2bd760cfef94070a3212164b7`.
- 진단의 commit 누적 초는 전/후/후/전 16.454834/16.010696/15.695422/16.194441다.
  corpus 준비를 포함한 값이고 commit 횟수 자체를 측정한 카운터가 아니므로
  요청당 비용이나 지연 차이 전부의 인과관계로 해석하지 않는다.
- `refresh-target-batch-repeated-full`의 전체 6회 반복 게이트를 완료했다.
  1090.542초(18분 11초), 모든 하위 실행 exit 0, 12개 토폴로지 요청 오류 0이다.
  execution_inputs_verified=true, error=null이지만 numeric_budget_passed=false,
  실행기 exit 1, implementation acceptance=false다. 소스/후보 해시는 불변이다.

| 후보 회차 | 공개 v0.6.0 대비 예산 이내 | 같은 묶음의 v0.6.0 대비 | 재측정 기준선의 공개 기준 대비 |
| --- | --- | --- | --- |
| 01 | 31/44 | 28/44 | 43/44 |
| 04 | 38/44 | 34/44 | 42/44 |

- 공개 기준 대비 실패 지표(양수는 지연 증가):
  - 01 single: write p95 +7.373565%, p99 +12.377146%; ranking mean +7.930601%,
    p95 +11.175876%, p99 +14.111560%; facet mean +6.355381%, p95 +7.646167%,
    p99 +8.878969%; sort_filter p99 +8.677636%; refresh mean +13.882640%,
    p95 +8.124307%, p99 +14.318439%. three nested p99 +5.138721%.
  - 04 single: ranking p99 +8.076835%; facet p99 +7.245163%; sort_filter p99
    +8.352653%; refresh mean +9.222053%, p95 +5.833254%, p99 +9.427453%.
- 처리량과 공개 기준 대비 변화(양수는 처리량 증가):
  01 single 705.9909 ops/s (-4.982457%), three 932.0965 (+0.078003%);
  04 single 733.1712 (-1.324325%), three 928.9464 (-0.260225%).
  공개 기준의 처리량 예산은 충족하지만 01 single은 paired 처리량 예산에 실패한다.
  각 paired 실패의 전체 이름/값은 result.json의 checks[].paired에 보존했다.
- 기준선 자체도 00 three nested p99, 05 single write p99와 three nested p99가
  공개 기준을 초과했다. 후보의 다른 실패까지 모두 환경 변동으로 돌릴 근거는 아니다.
  목표 병합의 중복 공개 감소 테스트는 통과했지만, 정식 성능 병목 해결은 입증하지
  못했다. 직전 후보와의 ABBA에서도 지연 개선이 일관되지 않았다. 단일 변경이
  5% 이상 저하를 유발했고 최적화 불가라는 조건은 아직 입증되지 않아 제외는 없다.
- 정식 plan SHA-256 `45b7aee357aca23f8fb1827cc141dccbf1eb4dc713bbf46c98c80d7f7c3b6052`,
  result SHA-256 `ebaab32d1150ce2af357ec2e7662aaabe800eca312816bdcada8da4807b51e5f`.
  전체 수락 **0/40**, 릴리즈 보류, 빈 제외 ledger를 유지한다. 커밋/태그/게시 없음.

- 후속 C04 삭제 재생 검증을 위한 읽기 조사:
  `replay_deferred_native_writes_before_refresh`는 캡처한 삭제를 sequence 조건 없는
  native delete로 재생하고 오류를 무시한 뒤 인덱스 전체 대기 목록을 제거한다.
  완료 정리의 세대 검증뿐 아니라 오래된 삭제의 실제 적용이 같은 ID의 새 문서를
  지우지 않는지도 재현/검증해야 한다. 이미 삭제된 상태의 멱등 처리와 진짜 재생
  오류를 구별해야 하며, 단순히 모든 DocumentNotFound를 새 오류로 바꾸지 않는다.
  같은 메타데이터를 재사용하는 delete/recreate와 index recreate도 포함한다.
  이 삭제 경로는 이번 턴에 수정하지 않았으며, 다음 수정 단위 역시 기능 검증 후
  전체 반복 벤치마크와 고정 v0.6.0 누적 5% 판정을 별도로 실행해야 한다.

### C04: 대기 삭제 재생의 identity와 실패 보존 (2026-09-08)

- 직전 턴은 목표 병합 구현과 전체 게이트 실행을 마친 progress다. 이번에는
  삭제 재생 실패가 성공으로 응답되는 결함을 먼저 재현했다. runtime에는 인덱스와
  대기 삭제를 남기고 native 인덱스만 제거하는 fault injection에서 기존 global
  refresh는 200을 반환했다. 기대 404와 대기 작업 보존을 검사한 red 로그를 보존했다.
- `PendingNativeDelete`에 복사 시 공유되는 `Arc<()>` identity를 추가했다.
  `replay_pending_native_delete`는 documents/pending-delete 잠금을 유지한 채
  캡처 identity와 현재 대기 항목을 비교한다. 새 문서가 runtime에 이미 들어온
  경우에도 오래된 삭제를 적용하지 않는다. 성공한 동일 항목만 제거하고, 다른
  시점의 삭제나 다른 key의 대기 작업은 인덱스 단위로 일괄 제거하지 않는다.
- native 삭제의 DocumentNotFound는 이미 적용된 삭제의 멱등 성공으로 처리한다.
  그 외 오류는 대기 항목을 보존하고 반환하며, global/index refresh REST 경로에서
  성공 응답/문서 완료 처리를 진행하지 않는다. 이 수정은 삭제 재생 경계다.
  기존 문서 Index 재생 분기의 무시되는 오류와 잘못된 메타데이터 skip은 여전히
  별도 보강 대상이며, 전체 deferred replay가 완성됐다는 의미가 아니다.
- 새 테스트 4개: global/index 실패 및 재시도, 이미 적용된 삭제, 서로 다른 목표의
  대기 삭제 보존과 쓰기 staging 경계, 새 문서/새 삭제/index recreate.
  세대 교체는 단일/3샤드 및 routing 생략/tenant의 12조합을 검사하고 인덱스
  재생성에서는 같은 sequence가 재사용됨도 확인한다. 오래된 재생 전후 native
  실시간 상태와 최종 native/fallback 검색을 구분해 검사한다.
- node **632/632**(11.81초), binary **459/459**(28.13초), deferred 삭제 경계
  **4/4** 통과. `git diff --check` 통과. engine 제품 소스는 직전과 동일하다.
  릴리즈 빌드는 4분 41초에 완료했고 새 후보 SHA-256은
  `c6623c34bb4036d8a9bd682190010b50db2efda109257d39ed8dcf1c2cce34e0`다.
  `live-delete-replay-identity-release` 실제 호환성 **1751/1751**, 실패/skip 0,
  count probe 및 바이너리/fixture 불변성 검증을 통과했다.
  `delete-replay-identity-repeated-full` 전체 6회 반복 게이트도 완료했다.
  1093.499초(18분 13초), 12개 토폴로지 요청 오류 합계 0, 모든 하위 실행 exit 0.
  execution_inputs_verified=true, error=null이나 numeric_budget_passed=false,
  실행기 exit 1, implementation acceptance=false다.
  전체 수락 0/40, 직전 정식 성능 FAIL, 빈 제외 ledger 및 릴리즈 보류를 유지한다.
- 추가 발견을 누락시키지 않는다: 테스트 초기의 명시적 `routing=`는 routing 생략과
  다르게 동작해 삭제 후 검색 문서가 남는 경우를 재현했다. 생략/tenant 테스트는
  이를 통과로 간주하지 않는다. 로컬 OpenSearch commit
  `f991609d190dfd91c8a09902053a7bbfe0c27b3e`의
  `server/src/main/java/org/opensearch/action/index/IndexRequest.java:294`와
  `action/delete/DeleteRequest.java:166`은 빈 문자열을 null로 정규화한다.
  Rust write 경로의 Some("")와 delete 경로의 None 차이를 추가 조사/수정해야 한다.
  원래 실패 로그 `delete-replay-focused-tests.log` 및
  `delete-replay-generation-diagnostic.log`를 보존했다. 빈 routing의 실제 REST
  참조 fixture와 alias 조합 검증, 수정 후 전체 게이트는 후속 미완료 항목이다.
- 증거 SHA-256 (`target/core-replacement-c05/`):
  - node source: `52e5d4dbc683c25ef17361a6b587e69efa4ef23a7b2d6f2ee80587bc6a1ef870`
  - red `delete-replay-before.log`: `99ed295dc59251d2e5f7acc2c9844a438682ccb7e24c693f8b3c76122097eb97`
  - node/binary `delete-replay-node-binary-tests.log`: `e4c5720cf691af690268e6891182853dabd9f56bac8b984ac9d73200dbb94884`
  - deferred `delete-replay-deferred-tests.log`: `8cf03c38460eeb114e12f9442cbf8d0ba5fa555ad518782cd66ccc800763b01e`
  - 보존 직전 후보 `steelsearch-before-delete-replay-identity`: `1ff7eac2f0e76df6806ae7f41587051e70d841979a40fef2a6449ce7e6b5f559`
  - build `delete-replay-release-build.log`: `bba1df071e82ed6ec164be0aa19eeaf587ca86293e0863438f6ca69f6e85313c`
  - live `live-delete-replay-identity-release/execution.json`: `92e0a2c883895c86453fb243c7212997a595b03576a7105e662c30b0fb2f3b0f`
- 기존 전체 혼합 부하의 write는 문서 추가 중심이다. 이번 삭제 경계의 잠금 비용은
  삭제/재생성 집중 부하에서도 별도 측정해야 한다. 전체 혼합 게이트 실행으로
  삭제 집중 성능까지 입증했다고 간주하지 않으며 P02/C04 후속 검증에 포함한다.

| 후보 회차 | 공개 v0.6.0 대비 예산 이내 | 같은 묶음의 v0.6.0 대비 | 재측정 기준선의 공개 기준 대비 |
| --- | --- | --- | --- |
| 01 | 39/44 | 39/44 | 43/44 |
| 04 | 37/44 | 36/44 | 44/44 |

- 공개 기준 대비 실패(양수는 지연 증가):
  01 single facet p99 +6.915381%, sort_filter p99 +5.875644%,
  refresh mean +10.310741%, refresh p99 +5.709311%; three nested p99 +5.986816%.
  04 single lexical p99 +7.833248%, ranking p95 +5.780947%, p99 +6.297278%,
  facet p99 +5.397039%, sort_filter p95 +7.957503%, refresh mean +9.708762%,
  refresh p99 +7.793956%.
- 처리량과 공개 기준 대비 변화(양수는 처리량 증가):
  01 single 730.2213 ops/s (-1.721337%), three 931.8747 (+0.054185%);
  04 single 723.3135 (-2.651044%), three 931.3173 (-0.005657%).
  모든 공개 기준 처리량은 예산 이내지만 지연 실패를 상쇄하지 않는다.
  각 paired 실패의 이름/값은 result.json checks[].paired에 전부 보존했다.
  00 기준선은 single refresh p99만 예산을 초과했고 05는 44/44 통과했다.
  후보 실패를 모두 환경 문제로 돌리거나, 이번 삭제 변경의 단일 기여가 5% 이상이고
  최적화 불가라고 판단할 근거는 없다. 기존 실패와 빈 제외 ledger를 유지한다.
- 정식 plan SHA-256 `99a0e50f42ebdd65172d5b8f2f6a8bcc464fc6856aa36e2c846215700eabe8af`,
  result SHA-256 `1a23799784fd94193cfbac126b26fd109fb6e743017ac2d42e5a848417cf3b7f`.

#### C01/C04 후속: 빈 routing 실제 참조 재현

- 기존 실행기를 사용하는 `tools/fixtures/search-empty-routing-compat.json`을 추가했다.
  3샤드에서 빈 쓰기/빈 삭제/둘 다 빈 값/빈 alias 값 및 정상 alias 대조군을
  native/fallback으로 나눈 12개 case다. 순차 쓰기/GET/삭제/refresh 상태와
  최종 검색 ID/source를 비교한다. alias default/명시 tenant 대조군을 포함한다.
- 첫 `live-empty-routing-before`는 필수 `bulk` 목록 누락으로 setup 중 중단됐다.
  이는 제품 비교 실패가 아니다. `bulk: []`를 보완하고 새 디렉터리
  `live-empty-routing-before-v2`에서 완료한 결과는 **9 passed / 3 failed / 0 skipped**다.
  setup 실패 0, 바이너리/fixture 불변성 true이며 추가 기본 nested/core **1500/1500**
  통과했다. 최종 helper exit 1은 새 fixture의 실제 호환성 차이 때문이다.
- 실패는 `empty-routing-write-empty-native`, `empty-routing-both-empty-native`,
  `empty-routing-alias-empty-native`다. 모든 요청 상태는 양쪽 기대값과 같지만,
  삭제/refresh 뒤 OpenSearch는 total=0, SteelSearch native는 total=1이며
  ID `one`과 원래 source를 반환했다. 대응 fallback과 정상 alias 대조군은 통과했다.
  따라서 기존 1751건 통과를 전체 routing 호환성 보장으로 해석하지 않는다.
- 이 빈 routing 제품 결함은 아직 수정하지 않았다. 다음 단위에서 쓰기/삭제/GET/
  bulk/update 및 alias routing의 입력 정규화 위치를 확인하고 위 fixture와
  단위 회귀로 수정한 뒤 전체 반복 벤치마크를 실행한다. 삭제 identity 개선을
  빈 routing 문제 해결이나 C04 전체 완료로 표시하지 않는다.
- fixture SHA-256 `73b7c6469cec96fbb2a7b23d6e15b5fe6ca28926154f23b66c3a81030f1bc1ee`,
  live execution SHA-256 `d53e1290012037ea9cbf7ff8fd2301bdc62674e614502c6ecf439a782fcb0bf9`,
  fixture report SHA-256 `e35695b51686f67455963beee5ebcefbe2b11aa0b64c7e44ab3639ab40d7c5e3`.
  전체 수락 **0/40**, 릴리즈 보류, 빈 제외 ledger를 유지한다. 커밋/태그/게시 없음.

### C01/C04: 빈 쓰기 routing과 alias 기본값 수정 (2026-09-08)

- 직전 턴은 삭제 재생 수정, 전체 성능 게이트 및 빈 routing 실제 참조 재현을
  완료한 progress다. 이번에는 입력과 alias 해석 경계를 확인하고 수정했다.
- Index/Create/Update 및 Delete의 빈 query routing을 alias 해석 전에 None으로
  정규화한다. 로컬 OpenSearch IndexRequest/DeleteRequest/UpdateRequest의 setter와
  같은 처리다. 공백이나 비어 있지 않은 문자열은 바꾸지 않는다. bulk metadata는
  기존 effective_routing 분기가 이미 빈 값을 alias/default로 처리하므로 유지했다.
- GetRequest/MultiGetRequest/ExplainRequest/TermVectorsRequest setter는 같은 빈 값
  정규화를 하지 않음을 로컬 참조 코드에서 확인했다. 조회를 포함한 전역 정규화는
  하지 않았다. 이들의 명시적 빈 routing 및 alias 충돌 REST 비교는 별도 미완료다.
- 새 테스트는 index/create/upsert x 단일/3샤드 x alias 유무의 12조합에서 저장 key와
  StoredDocument.routing, GET, 빈 routing DELETE 후 native/fallback 검색을 검사한다.
  수정 전에는 Some("")가 저장되어 실패했다. 네 입력 경로 수정 뒤에는 일반 alias
  routing 누락도 드러났다: alias=true/index/1샤드가 `empty-write:one:tenant` 대신
  `empty-write:one:`에 저장됐다. 원래 실패/중간 실패 로그를 모두 보존했다.
- `resolve_alias_write_routing`/문서 read는 index_routing 또는 일반 routing을 쓰고,
  `resolve_alias_search_routing`은 search_routing 또는 일반 routing을 쓰도록 수정했다.
  기존의 search_routing -> write 및 index_routing -> search 교차 fallback을 제거했다.
  로컬 Metadata.resolveIndexRouting과 IndexNameExpressionResolver의 searchRoutingValues
  경로에 근거한다. 일반/쓰기 전용/검색 전용/분리 alias 및 실제 인덱스의 기본값
  독립성도 단위 테스트로 검사했다. 명시적 routing 충돌/다중 인덱스 alias 전체 계약이
  완료됐다는 뜻은 아니다.
- node **634/634**(11.96초), binary **459/459**(17.56초), deferred 모드 새 routing
  테스트 통과. engine 제품 소스는 변경하지 않았다. 릴리즈 빌드는 4분 38초에
  완료했고 후보 SHA-256은 `f498917a191f88bf0209a7912333f0e87c5754ff6fe6f17c347b0b91901969cf`다.
  `live-empty-routing-after` 실제 참조 재검증은 **1763/1763**, 실패/skip 0,
  count probe와 바이너리/fixture 불변성도 통과했다. 강화 routing fixture 12개가
  모두 통과해 이전 native 삭제 잔류 3건 및 alias 실제 저장 위치를 확인했다.
  `empty-routing-repeated-full` 전체 6회 게이트도 완료했다. 1097.566초(18분 18초),
  모든 하위 실행 exit 0, 12개 토폴로지 요청 오류 0, execution_inputs_verified=true,
  error=null이나 numeric_budget_passed=false, 실행기 exit 1이다.
  implementation acceptance=false이며 전체 수락 0/40, 최신 FAIL,
  빈 제외 ledger 및 릴리즈 보류를 유지한다.
- 기존 routing fixture는 alias 이름 조회만으로 실제 저장 routing을 입증하지 못했다.
  alias 6개 case에 실제 인덱스 GET `routing=tenant`를 추가해 이 간접 검증을 보강했다.
  이전 fixture는 `target/core-replacement-c05/search-empty-routing-before-explicit-reads.json`
  으로 보존했다. case 수는 12개로 동일하며, 예전 9/12 결과를 강화 fixture의
  검증 결과로 재사용하지 않는다.
- 증거 SHA-256 (`target/core-replacement-c05/`):
  - node source: `3df4547a7f0763cc4ef15862e2c509254d6b6ce57e7c94de0ec6f29cfbfc72e9`
  - red `empty-routing-before.log`: `75f3ed12002aa672dac4ea8cc9b28434c102277f5a9df6fd8d93a7378ce7e5a3`
  - alias red `empty-routing-alias-diagnostic.log`: `0369f6aedc417d94c09f9c4b23773a193ca44931ed2fc41a4c3f45e5c1ef37a1`
  - node/binary `empty-routing-alias-node-binary-tests.log`: `974b857ba662661a60e87a052b4f07293e847a3fcdb1948556c43a1c5d64d0e1`
  - deferred `empty-routing-deferred-test.log`: `a1562f4112f36f8fa06be8e9d4d0db104bf970a749aa7bc8a84051ca8e35b5e0`
  - 강화 fixture: `34b33d1fc7caac19b665135dd1a831365819de266146f00fe106d5013e365304`
  - 보존 후보 `steelsearch-before-empty-write-routing`: `c6623c34bb4036d8a9bd682190010b50db2efda109257d39ed8dcf1c2cce34e0`
  - build `empty-routing-release-build.log`: `25a46267aa0e4de9342d081856d620b873b1f31132004e75e21efc43a89d07e2`
  - live `live-empty-routing-after/execution.json`: `5275da5279e515e2fd8a3876347476109f61daddd169f14e54a3fa2caf558dc1`
  - routing report `live-empty-routing-after/search-empty-routing-compat-report.json`: `873e1aa82a7aa7d734cdda370b1ab49db46da0a9ecc62ca509f9529851b4a914`

| 후보 회차 | 공개 v0.6.0 대비 예산 이내 | 같은 묶음의 v0.6.0 대비 | 재측정 기준선의 공개 기준 대비 |
| --- | --- | --- | --- |
| 01 | 40/44 | 41/44 | 42/44 |
| 04 | 35/44 | 38/44 | 42/44 |

- 공개 기준 대비 실패 지표(양수는 지연 증가):
  01 single ranking p95 +5.151754%, sort_filter p99 +7.606807%,
  refresh mean +6.752692%, p99 +6.611284%.
  04 single lexical p95 +5.172142%, p99 +7.769587%; ranking p99 +5.013216%;
  sort_filter p95 +6.392988%, p99 +8.210898%; refresh mean +9.874446%,
  p95 +5.396294%, p99 +5.629879%; three facet p99 +6.673811%.
- 후보 처리량과 공개 기준 대비 변화(양수는 처리량 증가):
  01 single 733.7745 ops/s (-1.243133%), three 935.6637 (+0.461011%);
  04 single 731.8389 (-1.503633%), three 928.4099 (-0.317822%).
  처리량 통과는 지연 실패를 상쇄하지 않는다. paired 실패는 result.json에 모두
  보존했다. 기준선 00은 single write/sort_filter p99, 05는 single write p95와
  three ranking p99가 공개 기준 대비 실패했다. 후보의 모든 실패를 환경 탓으로
  돌리거나 이번 routing 변경이 단독으로 5% 이상 저하를 유발했고 최적화 불가라고
  판단할 근거는 아니다. 빈 제외 ledger와 전체 수락 0/40을 유지한다.
- 정식 plan SHA-256 `318124d0f990b9dc3cf41704f523fc4da01c00e16d292c835f27e2bc1fb851fd`,
  result SHA-256 `add31bc16a9851e93a0e9a99cdf7777f4cf38b0ef2aaa688e543bd6422df2d91`.

#### C01/C03/C04 후속: alias routing 충돌과 거부 후 데이터 보존

- `tools/fixtures/document-alias-routing-contract.json`에 충돌 요청 8개와 각 요청
  뒤 검색 ID/source 보존 검사 8개를 추가했다. 같은 alias의 index_routing=tenant에
  other를 지정한 index/create/update/delete/GET/source GET, 명시적 빈 값을 지정한
  GET/source GET을 실제 참조와 비교한다. 각 시나리오는 독립 인덱스를 사용한다.
- 전체 성능 측정 종료 뒤 `live-alias-routing-contract-before`에서 실행했다.
  setup 실패 0, 바이너리/fixture 불변성 true, **6 passed / 10 failed / 0 skipped**.
  강화 빈 routing fixture 12/12 및 기본 nested/core 1500/1500은 계속 통과했다.
  최종 helper exit 1은 새 계약 fixture의 실패를 반영한다.
- OpenSearch는 8개 충돌 요청 모두 illegal_argument_exception/400으로 거부했다.
  SteelSearch는 index/create에 201을 반환했고, 각 후속 검색은 같은 ID `one`의
  source=changed/seed 두 문서를 보고한 반면 참조에는 seed 한 문서만 남았다.
  update/delete/GET/source GET의 other는 404, GET/source GET의 빈 값은 200을
  반환했다. 오류 형태 차이 8건과 데이터 변경 2건으로 합계 10건이다.
- 이 충돌 검증은 아직 수정하지 않았다. 다음 단위는 입력 정규화 후 alias의
  고정 index routing과 명시적 routing의 일치 여부를 검사하고, 쓰기/seq_no 할당
  전에 거부해야 한다. 조회의 명시적 빈 값은 쓰기와 달리 보존해 검사한다.
  bulk 부분 실패와 multi-index/write-index alias 계약도 함께 확인하되,
  단일-index fixture 통과만으로 그 범위까지 완료 처리하지 않는다.
  단위/실제 참조/거부 후 원장 검증 후 전체 반복 벤치마크와 고정 v0.6.0 누적
  5% 게이트를 다시 실행해야 한다.
- fixture SHA-256 `32fa2c9833e308103a1dcf83fce73c9e6f29436a67d3534efc834e8e306455be`,
  live execution SHA-256 `17375d6c8cd7f675e62d729fb67d396ef1b6762c167be7cf13a18b0679340c56`,
  report SHA-256 `3c720445d570ebf19da8f5631f53e716193eff8913833e570d971a0d2a8fb7dd`.
  전체 수락 **0/40**, 릴리즈 보류, 빈 제외 ledger 유지. 커밋/태그/게시 없음.

#### C01/C03/C04 진행: alias routing 충돌 검사 구현

- 2026-09-08: 앞 절의 미수정 상태에서 이어서 구현했다. 새 회귀 테스트는
  변경 전 3개 중 2개 실패를 재현했다. 충돌 PUT이 400 대신 201을 반환했고,
  multi-index alias가 선택된 write index 대신 첫 인덱스의 routing을 사용했다.
  원시 로그: `target/core-replacement-c05/alias-conflict-before.log`.
- `resolve_document_routing`이 실제 선택된 인덱스의 alias metadata를 사용해
  고정 routing 충돌과 복수 routing을 검사한다. concrete index는 추가 metadata
  잠금 없이 반환한다. index/create/update/delete 및 bulk에 적용했고,
  GET/source GET은 명시적 빈 routing을 보존하며 다중 인덱스 alias를 거부한다.
  DELETE와 bulk delete도 write target resolver를 사용한다.
- 거부된 단일 요청 8개는 documents의 Arc identity, metadata, 인덱스별/전역
  sequence를 보존한다. bulk의 충돌 index/create/update/delete는 항목별 400,
  뒤의 유효 항목은 201이며 sequence는 한 번만 증가함을 테스트했다.
- 수정 후 `alias_routing_` 3/3, 전체 node **636/636** (11.72초),
  binary **459/459** (18.15초), `git diff --check` 통과.
  전체 로그는 `target/core-replacement-c05/alias-conflict-node-tests.log` 및
  `alias-conflict-binary-tests.log`에 보존했다.
- 이 시점 node source SHA-256:
  `6e6ae2311db42521effaf7f5b7ec63a46aa28302e73661445f5c4bb3150eff60`.
  이전 후보는 `target/core-replacement-c05/steelsearch-before-alias-routing-conflict`에
  보존했고 SHA-256은 `f498917a191f88bf0209a7912333f0e87c5754ff6fe6f17c347b0b91901969cf`다.
  `target/release/steelsearch`도 아직 그 이전 후보다. 새 소스의 release 빌드,
  실제 OpenSearch 재비교, 전체 반복 성능 게이트는 **미실행**이다.
- 다음 검증은 release 재빌드 후 alias 충돌 fixture 16개와 기존 전체 호환성
  검사를 실행하고, 빌드/호환성 부하 종료 뒤 전체 반복 벤치마크를 실행하는 것이다.
  고정 v0.6.0의 시나리오별 누적 5% 기준은 그대로 적용한다. 직전 gate FAIL을
  이번 변경의 결과로 재사용하지 않으며 테스트 통과를 성능 통과로 보지 않는다.
- sole alias의 `is_write_index=false`, 복수 write index metadata 거부,
  alias 변경과 동시 쓰기의 원자성, MGET/explain/termvectors의 routing 경로는
  이 수정의 완료 범위가 아니다. C01/C03/C04 전체 완료를 주장하지 않는다.
  전체 수락 **0/40**, 제외 ledger 비어 있음, 릴리즈 보류를 유지한다.

#### C01/C03/C04 실제 비교: routing 충돌 통과와 오류 응답 후속 수정

- 2026-09-08: 직전 턴은 실제 소스 변경과 테스트 증거를 남긴 진행으로 분류한다.
  시작 시 cargo/호환성/성능 실행 프로세스가 없고 source/release 해시가 직전
  기록과 일치함을 확인했다. release 재빌드는 4분 42초에 성공했다.
  후보 SHA-256: `c056eb38db85ad106b802ee8e8f16fd5c85ac82aa7893e630cfa4eda39e16445`.
  로그: `target/core-replacement-c05/alias-conflict-release-build.log`.
- `live-alias-routing-contract-after`에서 기존 충돌 fixture **16/16** 및 기존
  호환성 **1763/1763**이 통과했다. 추가한 bulk fixture는 필수 `area` 누락으로
  실행기가 중단됐다. 이 실행 오류는 제품 실패와 구분하며 원시 기록을 보존했다.
- 필드를 수정한 `live-alias-routing-contract-after-v2`는 **1785 passed / 4 failed /
  0 skipped**, setup 실패 0, count probe true, binary/fixtures 불변성 true다.
  기존 충돌 16/16과 기존 1763/1763은 통과했고 새 bulk 계약은 6/10이다.
  새 fixture는 충돌 bulk의 항목별 오류/sequence, 유효 항목의 후속 처리와
  실제 routing readback, 원본 보존, multi-index write 선택 및 GET/source 거부,
  DELETE 충돌과 기본 routing을 비교한다.
- 실패 원인을 구분했다:
  1. bulk의 충돌 4항목이 `_index`에 alias를 반환했다. 참조는 선택된 실제
     인덱스를 반환하며, 상태/오류 사유/정상 항목 sequence는 이미 일치한다.
  2. multi-index GET/source 오류 2개는 후보가 `Alias`와 이중 괄호를 사용했다.
     실제 참조 REST 경로는 Metadata.resolveIndexRouting보다 앞선
     IndexNameExpressionResolver의 소문자 `alias`, 단일 괄호 오류를 반환한다.
  3. 최종 검색은 양쪽 모두 원본 seed와 정상 good만 보존했으나 동점 문서의
     순서가 달랐다. 저장 문서 손실/추가가 아니라 명시적 정렬 없는 비교였다.
- 후속 소스 수정: bulk 오류 `_index`를 resolved_index로 변경하고, 다중 alias
  오류를 실제 REST 경로의 문구로 맞췄다. Rust 회귀 테스트에 실제 인덱스명과
  전체 오류 사유 단언을 추가했다. node 전체 **636/636**, 12.05초 통과.
  로그: `target/core-replacement-c05/alias-error-envelope-node-tests.log`.
- fixture 검색에 `value.keyword` 오름차순을 지정했다. 새 extractor
  `alias_single_index_error`는 정확한 오류 문구를 보존한 채 인덱스 목록의
  순서만 정규화한다. 대소문자/이중 괄호/다른 alias/누락 또는 중복 인덱스/
  상태/오류 타입 차이를 숨기지 않는 Python 회귀 테스트를 추가했고,
  `python3 -m unittest tools.test_search_compat` **16/16** 통과했다.
- 현재 node source SHA-256:
  `59ec57bc244ac856d3e7d9a29c7c7dde9443457f906487117a9ee0d5a76fd580`.
  현재 bulk fixture SHA-256:
  `31328eaf9dc82157a8fb43302aff4d88aaf9f253dc91653f326c26ab2c361883`.
  v2 execution SHA-256:
  `b3c88146da358a4a4921a6e24b7b4dd38d370f96db523530e29d134451708031`;
  bulk report SHA-256:
  `3ef365486a078d4f61f53eff62287862821487cff8266f04f6a086cee036329a`.
  v2에는 정렬/extractor 변경 전 fixture 해시와 원시 응답이 보존돼 있다.
- `steelsearch-before-alias-error-envelope`에 c056 후보를 보존했다.
  `target/release/steelsearch`도 아직 c056이다. **후속 오류 응답 수정 후 binary
  테스트/release 재빌드/실제 비교 및 alias 단위 전체 반복 성능 게이트는 남아 있다.**
  다음은 binary 테스트, release 재빌드, 새 디렉터리에서 전체 실제 비교,
  모든 빌드/호환성 프로세스 종료 후 전체 반복 성능 게이트 순서다.
  단위 수락 전 고정 v0.6.0 대비 누적 5% 게이트를 생략할 수 없다.
  전체 수락 **0/40**, 빈 제외 ledger, 릴리즈 보류 유지. 커밋/태그/게시 없음.

#### C01/C03/C04 alias 수정본: 실제 비교 및 전체 성능 재검증

- 2026-09-08: 시작 시 실행 프로세스가 없고 source/c056 binary/fixture 해시가
  직전 기록과 일치함을 확인했다. 직전 턴은 소스 변경과 실제 실패 근거를 남긴
  진행이었다. binary 전체 **459/459** (17.50초), release 빌드 **4분 40초** 성공.
  로그: `target/core-replacement-c05/alias-error-envelope-binary-tests.log`,
  `alias-error-envelope-release-build.log`.
  현재 후보 SHA-256 `615ee1473bbc38a20998ccf481b8fc47adf3a1e0897ced93831f16ae44cb14b3`,
  node source `59ec57bc244ac856d3e7d9a29c7c7dde9443457f906487117a9ee0d5a76fd580`.
- `live-alias-error-envelope-after`에서는 bulk/다중 alias 오류 차이가 해결돼
  alias bulk fixture가 9/10이었다. 남은 검색은 참조 200/2문서, 후보 400,
  `No mapping found for [value.keyword] in order to sort on`이었다.
  이는 단순 동점 순서 문제가 아니라 새 정렬이 드러낸 multi-field 검색 결함이다.
- 이 실패를 삭제하거나 통과 처리하지 않았다. alias 데이터 보존 검사는 명시적
  keyword 매핑과 `value` 정렬로 분리하고, 원래 동적 문자열/`value.keyword` 정렬을
  `tools/fixtures/dynamic-string-mapping-contract.json`의 독립 실패로 보존했다.
  `live-alias-error-envelope-after-v2`는 **1789 passed / 1 failed / 0 skipped**,
  alias 충돌 16/16, bulk/선택 write index 계약 10/10, 기존 1763/1763 통과다.
  유일한 실패는 새 동적 multi-field 검색이며 setup 실패 0, count probe true,
  binary/fixture 불변성 true다. 전체 기능 검증을 통과했다고 표현할 수 없다.
- 읽기 전용 소스 조사에서 `infer_dynamic_mapping_for_value`는 이미 text 및
  keyword subfield를 생성하며 기존 테스트도 metadata readback을 검사함을 확인했다.
  `lookup_mapping_property`는 `properties`를 따라가지만 multi-field의 `fields`를
  따라가지 않는다. 생성 누락으로 단정하지 말고 실제 metadata readback, 매핑
  조회, 원본에서 정렬값을 읽는 경로를 함께 검증하는 C02 후속 작업이 필요하다.
  이 함수는 정렬 외 stored fields/field capabilities 등에도 쓰이므로 회귀 범위를
  해당 호출 경로까지 넓혀야 한다. 현재 소스에는 이 후속 수정은 적용하지 않았다.
- 실제 비교 종료 및 cargo/호환성 프로세스 종료 확인 후
  `alias-routing-repeated-full`의 사전 지정 6회/12토폴로지를 전부 실행했다.
  **1099.3605초 (18분 19초)**, 모든 subrun exit 0, 요청 오류 합계 0,
  execution_inputs_verified=true, error=null이다. 최종 numeric_budget_passed=false,
  runner exit 1, acceptance_established=false로 **FAIL**이다.
  빌드/테스트/실제 호환성 부하와 겹치지 않았고 실행 중 입력을 변경하지 않았다.

| 후보 회차 | 공개 v0.6.0 한도 내 | 같은 실행 v0.6.0 한도 내 | 기준선 자체 공개 한도 내 |
| --- | --- | --- | --- |
| 01 | 34/44 | 36/44 | 43/44 |
| 04 | 40/44 | 38/44 | 44/44 |

- 공개 기준 대비 실패 지연(양수는 증가):
  01 single ranking p95 +6.813768%, p99 +10.465481%; facet p99 +5.291470%;
  sort_filter p95 +12.377117%, p99 +9.852072%; nested p99 +5.696829%;
  refresh mean +10.012340%, p95 +6.994228%, p99 +6.002333%;
  three ranking p99 +5.619542%.
  04 single sort_filter p95 +6.481017%, p99 +13.395896%;
  refresh mean +9.342564%, p99 +6.030122%.
- 처리량 및 공개 기준 대비 변화(양수는 처리량 증가):
  01 single 726.9921 ops/s (-2.155947%), three 924.1711 (-0.772936%);
  04 single 730.8309 (-1.639295%), three 924.6061 (-0.726235%).
  처리량 통과로 지연 실패를 상쇄하지 않는다.
- paired 실패는 01 single ranking p95/p99, sort_filter p95/p99, nested p99,
  refresh mean/p95/p99; 04 single facet p99, sort_filter p95/p99, nested p95/p99,
  refresh mean이다. 원시 result에 수치를 모두 보존했다. baseline drift는
  00 single write p99 +6.827496%이며 05는 44개 모두 한도 이내다.
  후보의 반복적인 refresh/sort_filter 실패를 기준선 변동으로 면제하지 않는다.
  누적 실패만으로 이번 alias 변경의 단독 5% 영향/최적화 불가를 입증하지도 못하므로
  제외 ledger는 비어 있다. 고정 기준을 유지하고 refresh/sort_filter 병목 진단과
  정확성을 보존하는 최적화가 계속 필요하다.
- SHA-256:
  성능 plan `f2f8268964ddddcf3adef758405571db0fa0e28b71e99c68fa20bed3f721343e`;
  성능 result `0bb70b685bd30ad0de65cce69368ea09a54cc272f37bfbe583e8431f06742ff1`;
  v2 live execution `e10d0986969a22c765bde65df11e50ec858270b336e5952b907198fc13220125`;
  명시적 매핑 bulk fixture `eeea7cf628e3846b7922dfc3a5d37b3e47420e05f889de1f593579a33af1a24b`;
  동적 multi-field fixture `7ad7536100c30df8bc8aafdd0472cde7014eed1e61546e695672ae1c8f9c9d0c`.
- 전체 수락 **0/40**, 릴리즈 보류. alias의 남은 write-index/원자성 계약,
  C02 multi-field 결함과 누적 성능 실패를 해결하기 전 해당 패키지를 완료하지 않는다.
  커밋/태그/게시 없음. 모든 이번 빌드/호환성/성능 세션은 종료됐다.

#### C02 multi-field: 실패 경로 분리와 부분 수정 기각

- 2026-09-08: 직전 턴은 전체 반복 성능 근거와 독립 기능 실패를 확보한 진행이다.
  이번 턴 시작 시 실행 중인 빌드/벤치마크가 없음을 확인했다.
- 노드 회귀 테스트 2개를 추가했다. `multi_field_mapping_lookup_resolves_fields_without_confusing_objects`
  는 명시적 `value.raw`와 `object.value.raw`의 서로 다른 mapping을 조회한다.
  `multi_field_sort_uses_parent_values_and_preserves_source`는 명시적 raw/동적 keyword,
  native 허용/강제 fallback 경로에서 ID 정렬 순서, 반환 sort 값, 원본 source를
  검사하도록 작성했다. 처음 실행은 0/2 통과: 조회 None 및 명시적 raw 정렬 400.
  두 번째 테스트는 첫 명시적/native 조합에서 실패했으므로 나머지 조합의 실행
  결과까지 확보했다고 주장하지 않는다.
- `lookup_mapping_property`에 `fields` 탐색만 추가한 실험을 실행했다.
  매핑 조회 테스트는 통과했지만 실제 정렬은 200이면서 ID 순서가 틀렸다.
  value=alpha인 z가 먼저여야 하는데 value=zulu인 a가 먼저 반환됐다.
  오류 검증만 제거하는 부분 수정은 정확한 multi-field 구현이 아니므로 **기각**하고
  해당 제품 코드 변경만 복원했다. 새 회귀 테스트와 실험 로그는 유지했다.
  성능 저하에 따른 제외가 아니므로 exclusion ledger 항목을 만들지 않는다.
- 엔진 회귀 테스트 `multi_field_schema_keeps_explicit_subfields`와
  `multi_field_schema_adds_dynamic_keyword_subfield`도 추가/실행했다. **0/2 통과**:
  명시적 value.raw 누락, 동적 value.keyword 누락을 각각 재현했다.
  기존 engine 849개는 이 focused 명령에서 실행하지 않았다.
- 확인된 경로:
  REST `infer_dynamic_mapping_for_value`는 text/keyword metadata를 생성하지만,
  engine `read_field_mappings_from_properties`는 `fields`를 처리하지 않고,
  `ensure_dynamic_scalar_mapping`도 부모 필드만 등록한다.
  `TantivyIndexedField`에는 부모 source 경로/ignore_above가 없으며
  `build_tantivy_document`는 하위 필드 이름 그대로 source를 찾는다.
  engine `search_hit_sort_values_for_specs`/`source_sort_value`와 runtime
  `extract_sort_value` 역시 mapping 기반 부모 값 해석이 없다.
  따라서 metadata 조회 변경만으로 색인/정렬/반환 값 일치가 성립하지 않는다.

다음 C02 구현 단위는 이 연결을 함께 완료해야 한다. 아래는 수락 범위를 줄이는
별도 완료 항목이 아니라 하나의 end-to-end 구현 단위 내부 순서다.

1. 기존 schema 구조와 serde 호환성을 유지하면서 multi-field의 부모 source 경로,
   실제 타입, index/doc_values/store, ignore_above, normalizer를 표현한다.
   명시적 임의 이름의 하위 필드와 동적 keyword를 같은 계약으로 구성한다.
   `.keyword` 접미사를 임의로 제거하거나 source에 가짜 필드를 저장하지 않는다.
2. 명시적/동적 schema 생성, nested/object 경로, 배열/null/기존 필드 갱신을 연결한다.
   schema/readback 및 재시작 복원에서 하위 필드 정보가 사라지거나 중복되지 않아야 한다.
3. native 색인/fast field 및 source 기반 실행 경로가 같은 mapping-aware 값을
   사용하도록 연결한다. REST metadata lookup도 이때 함께 수정한다. 쿼리/정렬/
   search_after/집계/docvalue·stored fields의 공용 호출 경로를 확인하고, 지원
   옵션의 누락을 정상 결과로 숨기지 않는다. 원본 source/projection은 불변이다.
4. OpenSearch KeywordFieldMapper.parseKeywordValue의 순서처럼 ignore_above는
   normalizer 적용 전에 검사한다. Java String.length 기준과 다국어/보조 평면
   문자, 경계 255/256/257, 배열 일부 값 초과, null/missing도 실제 참조로 검증한다.
   잘못된 custom normalizer나 index/doc_values 설정을 무시하지 않는다.
5. 위 4개 red 테스트, 독립 live fixture 및 명시적 raw/동적 keyword/중첩 객체/
   native·fallback/refresh 전후/재시작/페이지 연속성 회귀를 통과시킨다. 기존
   node/engine/binary 전체 테스트와 실제 코어 호환성 검사를 다시 실행한다.
6. 구현 단위 완료 전에 새 release binary를 고정해 **전체 반복 벤치마크**를 실행한다.
   v0.6.0 최초 기준의 시나리오별 누적 5% 한도는 유지한다. multi-field 자체의
   신규 workload 진단은 전체 기존 workload의 누적 게이트를 대신하지 않는다.
   기존 refresh/sort_filter 초과를 해결하거나 정당한 별도 처리 근거를 확보하기
   전 단위를 수락하지 않는다. 의미 동작을 줄여 성능을 맞추지 않는다.

- 현재 제품 동작은 직전 615ee147 후보와 동일하며 추가된 것은 테스트다.
  테스트 소스 포함 node SHA-256 `153331ba0d66250aefc6bf28308f9e25f9b2794f82915428f0b94dd737ca18f7`,
  engine `c202f32728db19777d85458c6b9db0663faa80dcefdce8090390d9d1973f0ef6`.
  `target/release/steelsearch`는 `615ee1473bbc38a20998ccf481b8fc47adf3a1e0897ced93831f16ae44cb14b3`.
  debug node 실행 파일은 기각 실험 시점 빌드이므로 다음 테스트는 cargo로 재빌드한다.
- 로그/SHA-256:
  `multi-field-node-before.log`: `f37337a58c8e98844028647361bc1be41a009c82d89d0ea8cef4074d0d4bdb31`;
  `multi-field-node-after-lookup.log`: `14f1ca485a0cf9ee10ae47534ca5d1846652f1d314bee262493deee60d3bac22`;
  `multi-field-engine-schema-before.log`: `519196aa669fd6d03d36fa69beee8764771fbe4417c28d73055cda08f831c87b`.
  모두 `target/core-replacement-c05/` 아래이며 실제 실패를 보존한다.
  이번에는 제품 구현 단위 완료나 새 성능 측정을 주장하지 않는다.
  전체 수락 **0/40**, 마지막 정식 성능 gate FAIL, 빈 ledger, 릴리즈 보류를 유지한다.

#### C02 진행: 부모 source 메타데이터의 저장 계약

- 2026-09-08: 직전 턴은 4개 red 테스트와 부분 수정 기각 증거를 확보한 진행이다.
  실행 중인 cargo/성능 프로세스가 없음을 확인한 뒤 기존 스키마 구조를 읽고 수정했다.
- `TantivyFieldMapping`에 선택적 `multi_field_source: Option<MultiFieldSource>`를
  추가했다. descriptor는 부모 source `path`, 선택적 `ignore_above`와 `normalizer`
  이름을 보존한다. index/store/doc_values는 기존 필드 속성에 그대로 남는다.
  일반 필드는 None이며 serde default/skip_serializing_if를 사용해 기존 저장
  형식과 읽기 호환성을 유지한다. 기존 모든 생성 위치는 None으로 초기화했다.
- 새 테스트 2개로 이전 일반 필드 JSON의 정확한 round trip 및 새 descriptor의
  부모 경로/옵션/기존 필드 속성 round trip, 선택 옵션 생략을 검증했다.
  이 테스트는 normalizer 실행 지원이나 값 변환까지 입증하지 않는다.
- engine 전체 실행: **851 passed / 2 failed / 0 ignored / 0 filtered**, 23.91초.
  기존 849개와 새 metadata 테스트 2개는 통과했다. 실패는 명시적 하위 필드 등록과
  동적 keyword 등록의 기존 red 테스트이며 숨기거나 skip하지 않았다.
  로그: `target/core-replacement-c05/multi-field-source-metadata-engine-tests.log`,
  SHA-256 `76142902eceb9af78273fc1edb105740bcaab7381beed1cfc43e6a5b1cdc748c`.
- 현재 engine source SHA-256:
  `75ee54b411480f9ea851b81d56d0d5ac735e3bd53e2a1b97cdf59a67212571f4`.
  다음은 명시적/동적 스키마 생성에서 descriptor를 채우고 native 값 해석과
  source 기반 조회에 연결하는 작업이다. 단순 필드 등록만으로 정상 정렬이나
  전체 multi-field 지원을 주장하지 않는다. 위 C02 end-to-end 내부 순서 1-6은
  여전히 전체 범위이며 이번 저장 계약만을 별도 완료 단위로 대체하지 않는다.
- node/binary 전체 재검증, release 재빌드, 실제 참조 및 전체 반복 성능 검증은
  아직 실행하지 않았다. release binary는 여전히 615ee147 후보이며 마지막 정식
  성능 gate는 FAIL이다. 구현 단위 수락 전 고정 v0.6.0 누적 5% gate가 필요하다.
  전체 수락 **0/40**, 빈 ledger, 릴리즈 보류. 이번 테스트 세션은 종료됐다.

#### C02 진행: 명시적·동적 multi-field 스키마 등록

- 2026-09-08: 직전 턴은 descriptor 구현 및 전체 엔진 검증을 남긴 진행이다.
  시작 시 실행 중인 cargo/성능 프로세스가 없음을 확인했다.
- `read_field_mappings_from_properties`에 원본 source 경로를 전달해 명시적
  `fields`를 재귀적으로 등록한다. 중첩 객체 아래 필드와 하위 필드 안의 추가
  fields도 실제 루트 source 경로를 유지하며 하위 필드별 타입/index/store/
  doc_values/ignore_above/normalizer 이름을 독립적으로 보존한다.
  OpenSearch TypeParsers.parseMultiField를 참조해 빈 fields 배열을 허용하고
  점을 포함하는 하위 이름, 누락 타입, object/nested/alias 하위 타입, 비객체
  fields 및 잘못된 옵션 타입을 거부하도록 했다. REST 오류 포맷 전체의
  동등성까지 검증한 것은 아니며 normalizer 실행 연결도 아직 남아 있다.
- `ensure_dynamic_scalar_mapping`은 새 문자열 부모에 keyword 하위 필드를 추가하고
  부모 source 경로와 ignore_above=256을 기록한다. 이미 등록된 부모는 다시
  생성하지 않는다. 일반 비문자열 필드의 등록은 기존 경로를 유지한다.
- 부모 경로/하위 옵션 독립성과 잘못된 children/options 검증 2개를 추가했다.
  focused 실행 5/5(관련 4개와 기존 다중 sort tuple 테스트 1개) 이후
  전체 engine **855/855**, 23.05초 통과. 기존 명시적/동적 등록 red 2개 해결.
  전체 node는 **636 passed / 2 failed**, 12.16초다. 실패는 여전히 metadata
  lookup None 및 실제 raw 정렬 400인 기존 두 multi-field 테스트이며 skip하지 않았다.
- 실제 native 값 색인과 source 기반 조회/정렬/응답은 descriptor를 아직 사용하지
  않는다. 따라서 스키마 등록 통과를 end-to-end multi-field 지원으로 확대하지 않는다.
  다음은 `TantivyIndexedField`/`build_tantivy_document`로 부모 정보와 값 처리 옵션을
  전달하고, native 및 fallback의 sort 값/쿼리/집계/fetch가 같은 의미를 사용하도록
  연결하는 것이다. 원본 source 불변성과 UTF-16 길이 기준 ignore_above 경계,
  normalizer 처리 순서도 실제 참조로 검증해야 한다. 앞의 C02 내부 순서 1-6 유지.
- 로그는 `target/core-replacement-c05/multi-field-schema-registration-tests.log`,
  `multi-field-schema-registration-engine-full.log`, `multi-field-schema-registration-node-full.log`.
  engine full SHA-256 `5b7c9ec567012337a12df59bbdf0b10e9d9cf6a47e5a53a9190b18216ba53b8e`.
  현재 engine source SHA-256 `567dab6010c66390f33e8390cfca87f73f8444eef3fca607682bab68d3b1334e`.
  release binary는 여전히 615ee147이며 이번 소스로 재빌드하지 않았다.
- binary 테스트/실제 비교/전체 반복 성능 gate는 아직 실행하지 않았다. 동적 keyword
  추가는 스키마·색인·refresh 비용을 바꾸므로 완성본에서 전체 벤치마크 및 고정
  v0.6.0 누적 5% gate를 반드시 재실행한다. 이번 내부 단계로 구현 단위를 완료
  처리하지 않는다. 전체 수락 **0/40**, 마지막 성능 FAIL, 빈 ledger, 릴리즈 보류.

#### C02 진행: native 문서의 부모 값 색인

- 2026-09-08: 직전 턴은 스키마 등록과 engine/node 전체 검증을 남긴 진행이다.
  이번 턴 시작 시 실행 중인 빌드/성능 프로세스가 없음을 확인했다.
- `TantivyIndexedField`에 source descriptor를 전달하고 `build_tantivy_document`가
  하위 필드명 대신 부모 source 경로를 읽도록 연결했다. geo component도 부모
  경로를 사용한다. source 자체를 수정하거나 가짜 하위 필드를 삽입하지 않는다.
- keyword multi-field 값은 배열을 순회하고 null을 생략하며 문자열/숫자/불리언을
  처리한다. ignore_above는 UTF-16 code unit 수로 검사하고 초과 값만 제외한다.
  객체 값은 오류로 반환한다. 함수가 Result를 반환하도록 하여 native 변환 오류를
  호출자에게 전달한다. 연결되지 않은 normalizer는 원문을 조용히 색인하는 대신
  명시적 미구현 오류를 반환한다. 이는 지원 범위 제외나 normalizer 완료 처리가
  아니며 설정 검증/실행/검색 값 일치 및 정확한 오류 시점·형식은 계속 구현 대상이다.
- append에서 multi-field가 있는 배치는 writer 변경 전에 전체 native 문서 변환을
  완료하도록 했다. 없는 배치는 기존 순차 변환 경로를 유지한다. 변환 비용은
  document_add timing에 포함한다. 변환 실패 후 재시도/중복 방지에 대한 별도
  배치 fault-injection 테스트는 아직 필요하며 이번 scalar/encoding 테스트로
  전체 C04 원자성 계약까지 검증됐다고 보지 않는다.
- 새 테스트 2개는 실제 engine에 저장한 source에서 Tantivy 문서를 생성해 부모
  필드 값과 독립적인 하위 ignore_above를 검사한다. ASCII 255/256/257자,
  보조 평면 문자 128/129개, null/빈 문자열, 배열과 숫자/불리언 및 객체 거부를
  확인한다. 원본 source 일치와 가짜 `value.raw` 필드 부재도 검사한다.
- 전체 engine **857/857** (22.93초) 통과. 전체 node **636 passed / 2 failed**
  (12.64초), skip/filtered 0. 실패는 기존 metadata lookup None 및 raw sort 400이다.
  REST 조회/정렬/fallback 연결이 아직 없으므로 이 결과는 end-to-end 완료가 아니다.
  keyword 하위 옵션의 native index/store/doc_values 동작, normalizer 처리,
  쿼리/정렬/집계/fetch의 값 해석 및 원본 source 보존도 기존 C02 범위에 남는다.
- 로그: `target/core-replacement-c05/multi-field-native-wiring-tests.log` (focused 7/7),
  `multi-field-native-parent-engine-full.log`, `multi-field-native-parent-node-full.log`.
  engine full SHA-256 `089826f2aaf19ea1d62ce814aca8253824dca02f54593cd0659c48b2efe705a1`;
  node full `611c05c6d7a43b0218cee8b7e6c87960d80c31d538a2ebc170de8a5c671da9a8`;
  engine source `1d1e40886e2cd79aec348fb73030e099f2b4bb940587217d24837c15e268f814`.
- release binary는 여전히 615ee147이다. 새 source의 binary 테스트/release 빌드/
  실제 참조/전체 반복 성능 gate는 미실행이다. 하위 필드 추가와 배치 선변환의
  비용을 완성본에서 측정하고 고정 v0.6.0 누적 5% gate를 통과해야 한다.
  전체 수락 **0/40**, 마지막 성능 FAIL, 빈 ledger, 릴리즈 보류. 테스트 세션 종료.

#### C02/C04 검증: multi-field 배치 변환 실패와 재시도

- 2026-09-08: 직전 턴은 native 부모 값 색인과 engine/node 전체 회귀 근거를
  확보한 진행이다. 이번에는 실행 중인 빌드가 없음을 확인하고, 새로 추가된
  배치 선변환의 오류 경계를 검증했다. 제품 코드는 변경하지 않았고 테스트를 추가했다.
- `multi_field_append_conversion_failure_does_not_queue_partial_documents`는 두 번째
  문서만 keyword 객체 변환에 실패하도록 native 계층에 fault를 주입한다.
  실패 후 기존 searcher/doc-id lookup을 유지하는지 확인하고 writer를 강제로
  commit/reload해 첫 문서가 숨은 작업으로 남지 않았음을 검사한다(실제 문서 수 0).
  정상 배치 재시도 뒤 문서 수 2, ID one/two 각각 존재, alpha/beta 하위 필드
  TermQuery postings 각각 1, 이전 searcher 문서 수 0을 검증했다.
- focused **1/1**, 전체 engine **858/858** (23.30초) 통과. 로그는
  `target/core-replacement-c05/multi-field-append-failure-test.log`와
  `multi-field-append-failure-engine-full.log`다. 이는 native 변환 실패에 대한
  국소 검증이며 REST 입력 검증/refresh wrapper의 상태 복원/디스크 장애/
  분산 쓰기/프로세스 재시작 전체 원자성까지 통과했다는 뜻이 아니다.
- 조회 경로는 여전히 원본 source를 직접 사용하는 곳이 있어 색인 값과 응답
  source를 구분한 mapping-aware 연결이 필요하다. 노드의 기존 multi-field
  lookup/sort red 2개, normalizer와 옵션별 동작은 미완료로 유지한다.
- 이번 턴에 node/binary/live/전체 성능 gate는 새로 실행하지 않았다. 제품 코드
  변경이 없는 회귀 보강을 C02 구현 단위 완료로 대체하지 않는다. end-to-end
  구현 후 전체 반복 벤치마크 및 고정 v0.6.0 누적 5% gate 요구는 그대로다.
  전체 수락 **0/40**, 마지막 성능 FAIL, 빈 ledger, 릴리즈 보류. 테스트 세션 종료.

#### C02 진행: keyword multi-field의 엔진 조회 값 연결

- 2026-09-08: 직전 턴은 배치 변환 오류/재시도 회귀 증거를 확보한 진행이다.
  시작 시 실행 중인 빌드/성능 프로세스가 없음을 확인했다.
- keyword 값 변환을 `visit_multi_field_keyword_values`로 분리해 native 문서 색인과
  조회가 배열/null/scalar 변환 및 UTF-16 ignore_above 처리를 공유한다.
  `StoredIndex`는 선언된 keyword multi-field의 descriptor를 찾아 부모 경로에서
  실제 색인 대상 값만 읽는다. normalizer 미연결 상태는 오류로 유지한다.
- term/terms/exists의 source 기반 판정을 이 값 해석에 연결했다. term의 query
  scalar도 기존 query text 변환 API를 사용하고 대소문자 옵션을 유지한다.
  literal source key를 읽는 fast candidate shortcut은 multi-field term/match에
  사용하지 않도록 해 잘못된 빈 후보를 고정하지 않는다. 일반 필드의 기존
  shortcut은 유지한다. 이것은 전체 검색을 fallback으로 대체한 구현이 아니다.
- 공개 엔진 검색 회귀 1개를 추가했다. case-sensitive/insensitive term, terms,
  exists, ignore_above로 제외된 값에 대해 source 판정과 공개 엔진 검색 결과를
  함께 검사했다. total/ID 및 원본 source 불변성도 확인했다.
  이 검증은 기본 옵션의 해당 5개 query 사례이며 bool/nested 조합, 모든 옵션,
  정렬/페이지 연속성, 집계/fetch의 전체 호환성을 의미하지 않는다.
- 최초 컴파일에서 이미 EngineResult인 query text 변환 결과를 다시 오류 변환한
  타입 오류를 수정했다. 첫 로그 `multi-field-query-wiring-compile.log`를 보존한다.
  이후 focused **11/11**, 전체 engine **859/859** (23.76초), 전체 node
  **636 passed / 2 failed** (12.35초)다. 실패는 기존 REST mapping lookup과
  raw sort 400이며 skip/filtered 0이다. 추가 회귀는 관측되지 않았다.
- REST fallback의 `evaluate_search_query_source_with_mappings`는 여전히 원본의
  `value.raw`를 직접 찾으므로 엔진 수정이 자동 적용되지 않는다. 다음은 같은
  값 해석을 REST fallback과 정렬에 연결하고, 원본 source와 색인용 값을 구분해
  sort/search_after/반환 값이 일치하도록 하는 작업이다. normalizer, 옵션별 동작,
  나머지 쿼리 및 기존 C02 내부 순서 1-6의 범위는 축소하지 않는다.
- 로그는 `target/core-replacement-c05/multi-field-keyword-query-tests.log`,
  `multi-field-keyword-query-engine-full.log`, `multi-field-keyword-query-node-full.log`.
  focused SHA-256 `4700854684240a1dee22af817b20c898630acd56880c6f1fde145843e3e5945b`;
  engine full `33b5229a80e9e5ac48d0591efd43724c2fdc951de919c5ff6894e8bdaed68ca1`;
  engine source `e6c0586a3c2e2ffc7adb0dcb21808d4cac8fdf0fea4c8f7374fbbc7a8688ae7d`.
- release binary는 615ee147 그대로다. 새 binary 테스트/release 빌드/실제 참조/
  전체 반복 성능 gate는 미실행이며, 구현 단위 수락 전 고정 v0.6.0 누적 5%
  gate를 생략하지 않는다. 전체 수락 **0/40**, 마지막 성능 FAIL, 빈 ledger,
  릴리즈 보류. 이번 테스트 세션은 모두 종료됐다.

#### C02 진행: 오류를 보존하는 공용 keyword 값 API

- 2026-09-08 진행률 보고 후 계속 작업했다. 기존 v0.6.0 코어 실패 27개 항목
  해결 기록과 후속 대체 계획 40개 패키지의 최종 수락 수를 구분한다.
  후자는 **0/40**이며 내부 구현 진척을 최종 수락률로 환산하지 않는다.
- `MultiFieldSource::keyword_values`를 공개하고 기존 엔진 term/terms/exists
  판정을 이 API에 위임했다. native 색인의 scalar/배열/null/UTF-16 길이 변환
  visitor를 재사용하며 원본 source에 가상의 하위 필드를 삽입하지 않는다.
  잘못된 객체 값과 아직 구현되지 않은 normalizer는 `EngineResult` 오류로
  유지한다. normalizer 지원 완료 또는 지원 범위 제외를 뜻하지 않는다.
- 외부 크레이트 관점의 통합 테스트 파일
  `crates/os-engine-tantivy/tests/multi_field_values.rs`를 추가했다. 공개 스키마
  변환으로 얻은 descriptor에 대해 다단계 multi-field의 최초 부모 경로,
  독립적인 자식 ignore_above, 객체 배열/중첩 값 배열, 숫자/불리언/null,
  UTF-16 경계, 가짜 source 키 무시, source 불변성, 오류와 값 부재 구분을
  검증했다. 새 테스트 **2/2**, 전체 engine lib **859/859** (9.89초) 통과.
  테스트 시간은 벤치마크 성능 지표가 아니다.
- REST evaluator는 `Option`을 반환하고 일반 query/post_filter 경로가 None을
  불일치로 처리한다. 공용 API 오류를 `.ok()?`로 연결하면 잘못된 입력이
  HTTP 200 빈 결과로 숨을 수 있어 그런 연결은 하지 않았다. 다음 작업은
  query/alias filter/post_filter 및 재귀 쿼리의 오류 전달을 먼저 정리한 뒤
  참조하는 multi-field 값만 해석하도록 연결하는 것이다. 무관한 필드의
  normalizer 때문에 모든 쿼리를 거부하거나 임의 JSON을 쿼리로 순회하지 않는다.
- REST 조회 연결/정렬/페이지 연속성/집계/fetch/normalizer 및 옵션은 여전히
  C02 내부 구현 범위다. 기존 node **636 passed / 2 failed**는 이전 실행
  기록이며 이번에는 node를 재실행하지 않았다. 매핑 검증만 완화하지 않았다.
- 로그: `target/core-replacement-c05/multi-field-public-values-engine-full.log`,
  `multi-field-public-values-tests.log`. 이번 변경은 내부 진행이며 end-to-end
  구현 단위 완료가 아니다. release 바이너리 재빌드/live/전체 성능 gate는
  미실행이다. 구현 단위 수락 전 전체 반복 벤치마크와 고정 v0.6.0 대비 누적
  5% gate를 실행해야 한다. 마지막 성능 FAIL, 빈 ledger, 릴리즈 보류를 유지한다.

#### C02 진행: REST fallback keyword 조회와 오류 전달

- 2026-09-08: 직전 턴은 공용 값 API와 테스트를 추가한 구현 진척이다.
  이번에는 `MultiFieldSource::for_keyword_field`로 properties/fields를 구분해
  keyword multi-field의 최초 부모 경로와 자식 옵션을 찾도록 했다. 이름이 같은
  임의 leaf로 대체하지 않는다. 기존 정렬용 매핑 조회는 아직 완화하지 않았다.
- REST fallback term/terms/exists가 공용 keyword 값 변환을 사용한다. keyword
  비교를 text 토큰 비교와 구분하고 query 숫자/불리언은 기존 scalar-to-text
  변환을 사용한다. ignore_above 대상 값 제외와 원본 source 보존을 유지한다.
- `SourceQueryEvaluator`가 재귀 평가의 변환 오류를 보존하고 checked 응답 경계가
  이를 EngineError로 반환한다. bool filter가 내부 None을 false로 바꾸더라도
  변환 오류는 없어지지 않는다. dis_max/boosting/constant_score/wrapper/
  function_score(함수 filter 포함)/script_score/nested/bool 재귀 호출은 같은
  컨텍스트를 사용한다. REST query/alias filter/post_filter 및 `_field_caps`
  index_filter가 이 오류를 응답으로 전달한다. PIT alias filter helper도
  평가 오류를 Result 오류로 변환한다.
- query/alias filter/post_filter 및 field_caps의 참조 필드 옵션은 문서 순회 전
  검증한다. 따라서 빈 인덱스나 bool/function_score 단락 평가에서도 참조한
  미지원 normalizer가 정상 빈 결과로 숨지 않는다. 기존 쿼리 자식 순회와
  wrapper decode, function filter만 사용하며 script params 등 임의 JSON은
  순회하지 않는다. 무관한 multi-field 옵션 때문에 일반 필드를 거부하지 않는다.
  이것은 normalizer 실행 구현이 아니며 정확한 OpenSearch 오류 envelope/
  전체 옵션/다른 API 경계의 호환성 수락을 의미하지 않는다.
- 노드 회귀 3개를 추가했다. term/case-insensitive/terms/exists와 길이 제외,
  재귀 쿼리 변환 오류, REST query/post_filter의 ID/total/source, 빈 인덱스의
  참조 옵션 오류, script params 비순회, wrapper와 field_caps 오류를 검사했다.
  API lookup 통합 회귀 1개도 추가했다. 이번 REST 조회 fixture는 명시적 raw
  사례이며 동적 keyword와 모든 nested/alias/PIT 조합의 실제 참조 검증은 남는다.
- focused REST **2/2**, 전체 engine lib **859/859** (10.38초), 공개 API 통합
  **3/3** 통과. 전체 node는 첫 실행 **639 passed / 2 failed** (5.67초),
  field_caps 보강 후 **639 passed / 2 failed** (5.70초), skip/filtered 0이다.
  실패는 기존 매핑 lookup None과 raw sort 400이며 정렬을 해결했다고 표시하지 않는다.
- binary 병렬 **458 passed / 1 failed** (11.99초):
  `clear_cache_transport_route_resets_local_knn_runtime_cache_state`의 local subset
  predicate가 false였다. 단독 **1/1**, 전체 직렬 **459/459** (17.41초) 통과.
  predicate가 공유 manifest 기반 k-NN shard 조회를 사용하므로 병렬 공유 상태
  간섭이 의심되지만 인과관계를 확정한 진단은 아니다. 플러그인 수정은 제외하고
  원본 실패 로그를 보존한다. 직렬 결과로 병렬 실패를 통과로 덮어쓰지 않는다.
- 로그 위치는 `target/core-replacement-c05/` 아래
  `multi-field-rest-fallback-focused.log`, `multi-field-rest-fallback-engine-full.log`,
  `multi-field-rest-fallback-node-full.log`, `multi-field-rest-fallback-node-full-v2.log`,
  `multi-field-rest-fallback-binary-full.log`, `multi-field-rest-fallback-binary-cache-focused.log`,
  `multi-field-rest-fallback-binary-serial.log`다.
  node source SHA-256 `ee8bea8e313fedd7ecf2a34821aa9a00d976dde72221e05b1f3e25d43ae51283`;
  engine source `39917815c1b5a0bbaea0b51e24cb19e2bd7f802b63b1f12a1f63354eaeec988d`;
  node v2 log `48f1b4586af066dadc77ba818dbb256a5de34cc538a4309dc41a77dfaffe84f2`;
  engine log `e83983149efc13780ef4b7eea1ddd431e0cc2cea7db35f986f30e8cbe205a0cc`.
- C02 end-to-end 구현 단위는 여전히 진행 중이다. 다음은 source를 변조하지 않는
  mapping-aware 정렬 값 연결이며 sort/search_after/반환 sort 값과 native/fallback
  순서를 함께 맞춰야 한다. 집계/fetch/normalizer/옵션 및 내부 순서 1-6의 범위를
  줄이지 않는다. release 바이너리는 SHA-256 `615ee147...` 그대로이며 이번 소스의
  release 재빌드/live/전체 반복 성능 gate는 미실행이다. 구현 단위 수락 전에
  전체 벤치마크와 고정 v0.6.0 대비 누적 5% gate를 반드시 실행한다.
  전체 수락 **0/40**, 마지막 성능 FAIL, 빈 ledger, 릴리즈 보류. 테스트 세션 종료.

#### C02 진행: REST fallback의 매핑 기반 정렬 값 연결

- 2026-09-08: 직전 턴의 REST 조회/오류 전달 구현과 테스트는 진척이다.
  이번에는 `MappedSearchSort`로 요청 정렬의 keyword multi-field descriptor를
  인덱스별로 해석하고 fallback 정렬/search_after/반환 sort 값에 연결했다.
  공용 keyword 값 API와 기존 배열 reducer를 사용해 부모 경로, ignore_above,
  min/max를 동일하게 적용한다. 매핑마다 ignore_above가 달라도 구분한다.
- 정렬 비교 전에 hit와 해석된 값 tuple을 별도로 만들며 `_source`에 가상 키를
  넣지 않는다. 기존 sort 값도 재사용하지 않아 다른 정렬 사양의 오래된 값에
  의존하지 않는다. search_after와 응답 값은 같은 descriptor로 재계산한다.
  일반 정렬의 누락 위치/사용자 지정 missing 비교 함수를 분리해 공유했고,
  multi-field가 없는 요청은 기존 정렬 경로를 유지한다.
- 변환 오류/미지원 normalizer/keyword의 비수치 min/max 이외 모드가 묵시적
  missing으로 바뀌지 않게 오류를 전달한다. 정확한 오류 envelope, mode 대소문자,
  numeric_type/사용자 지정 missing의 전체 coercion, 다른 sort 타입과의 조합은
  아직 전체 옵션 호환성 검증 대상이다. normalizer 지원 범위를 제외하지 않는다.
- 회귀 3개를 추가했다. asc/desc/명시적 max, 배열/null/길이 제외,
  missing `_first`/기본 `_last`/문자열 대체, 각 위치의 search_after, 반환 sort와
  source 불변성, 객체 배열 부모 경로, 인덱스별 옵션과 오류를 검사했다.
  실제 REST 테스트에서는 명시적 raw와 동적 keyword 각각 1건씩 두 페이지를
  조회해 ID/source/sort/전체 건수가 유지되는지 확인했다.
- REST 테스트는 `pre_filter_shard_size=1`로 fallback을 선택하고
  `unmapped_type: keyword`를 명시해 현재 허용된 요청 경로를 검증한다.
  이 옵션이 없는 기본/native 매핑 lookup 및 sort red 테스트는 그대로 남겼다.
  엔진 정렬이 미연결인 상태에서 검증만 완화하거나 모든 native 정렬을 fallback으로
  대체하지 않았다. 따라서 기본 경로까지 multi-field 정렬이 완료됐다는 증거가 아니다.
- 첫 focused 결과 **2 passed / 1 failed**는 desc 기대값에서 beta/alpha 순서를
  잘못 적은 테스트 오류였다. 기대값을 zulu/beta/alpha로 수정했고 원본 로그를
  보존했다. 이후 전체 node **642 passed / 2 failed** (5.69초), 신규 3개 모두
  통과, skip/filtered 0이다. 기존 실패는 매핑 lookup None과 raw sort 400이다.
  binary 전체 직렬 **459/459** (17.54초), `git diff --check` 통과.
  이전 턴의 binary 병렬 플러그인 실패 기록은 삭제하거나 통과로 바꾸지 않는다.
- 로그: `target/core-replacement-c05/multi-field-mapped-sort-focused.log`,
  `multi-field-mapped-sort-node-full.log`, `multi-field-mapped-sort-binary-serial.log`.
  node source SHA-256 `462060ed86f02b396a214bb6fcd25bc79ed759673cc69c64669fcff03e5ed97f`;
  node full log `42f461e253724afe3825019f0f2a729d62426ea700e251a2f5c2c59ad4f6e534`.
- 다음은 엔진의 정렬 비교/페이지 병합/반환 값에 mapping context를 연결하는
  작업이다. segment별 keyword term ordinal을 그대로 비교해서는 안 되며,
  기존 numeric fast path와 source 불변성을 유지해야 한다. 기본 REST 매핑
  검증 연결, scroll/PIT/집계/fetch/나머지 옵션과 실제 OpenSearch 비교도 남는다.
  이번에는 engine 소스 변경/engine 재실행/release 빌드/live/전체 성능 gate를
  하지 않았다. release 바이너리 SHA-256은 `615ee147...` 그대로다.
  C02 end-to-end 구현 단위는 진행 중이며 수락 전에 전체 반복 벤치마크와
  고정 v0.6.0 대비 누적 5% gate를 실행해야 한다. 전체 수락 **0/40**,
  마지막 성능 FAIL, 빈 ledger, 릴리즈 보류. 테스트 세션 종료.

#### C02 진행: 정렬 옵션 보강과 공개 엔진 정렬 재현

- 2026-09-08: 직전 턴은 fallback 정렬 연결과 회귀 증거를 추가한 진척이다.
  로컬 OpenSearch `search/sort/SortMode.java`의 fromString과
  `FieldSortBuilder.java`의 비수치 필드 검증을 확인했다. 이를 따라
  `MappedSearchSort`가 MIN/mIn/MAX/mAx를 허용하고 keyword multi-field의
  numeric_type을 거부하도록 수정했다. 기존 테스트에 혼합 대소문자 4사례와
  long/double/date/date_nanos 거부 4사례를 추가했다. 오류 envelope 전체를
  실제 참조 서버와 비교한 결과는 아직 아니다.
- 전체 node **642 passed / 2 failed** (5.90초), skip/filtered 0이다.
  실패는 기존 mapping lookup None과 raw sort 400으로 동일하다.
  `target/core-replacement-c05/multi-field-sort-options-node-full.log`에 보존했다.
- 엔진 연결의 독립적인 실패 기준을 만들기 위해 공개 API 통합 테스트
  `multi_field_public_engine_sort_pages_use_parent_values`를 추가했다.
  a=zulu/z=alpha/m=beta를 각각 쓰고 refresh한 후 asc/desc의 1건 페이지,
  전체 건수/ID/반환 sort/source를 검사한다. 현재 **asc 첫 페이지에서 a를
  반환해 기대 z와 불일치**한다. 이후 페이지/desc/반환 값 검사는 이 실패로
  실행되지 않았으므로 통과를 주장하지 않는다. 이는 REST 매핑 검증과 독립적인
  엔진 정렬 결함이며, REST lookup만 완화해서는 해결되지 않음을 확인한 증거다.
- 공개 API 통합 전체 **3 passed / 1 failed** (0.09초), skip/filtered 0,
  로그 `target/core-replacement-c05/multi-field-public-engine-sort-red.log`.
  새 테스트는 해결되지 않은 기존 동작의 재현이며 엔진 제품 코드는 이번에
  변경하지 않았다. 기존 엔진 lib 859 통과 기록을 이 새 실패까지 포함한
  전체 엔진 통과로 해석하지 않는다.
- 다음은 엔진의 source 기반 정렬 비교/페이지 병합/반환 값에 mapping context를
  연결하는 작업이다. 이 재현 테스트를 삭제하거나 기대 ID 순서로 바꾸지 않는다.
  기본 REST 정렬, 나머지 옵션, scroll/PIT/집계/fetch 및 C02 전체 범위는 남는다.
  이번에는 binary 테스트/release 빌드/live/전체 성능 gate를 새로 실행하지 않았다.
  C02 수락 전 전체 반복 벤치마크와 최초 v0.6.0 대비 누적 5% 기준을 유지한다.
  전체 수락 **0/40**, 마지막 성능 FAIL, 빈 ledger, 릴리즈 보류. 실행 세션 종료.

#### C02 진행: 엔진 요청 필터 경로의 매핑 기반 정렬

- 2026-09-08: 직전 턴의 옵션 수정과 공개 엔진 정렬 재현은 진척이다.
  `MappedEngineSort`를 추가해 target index/정렬 필드별 descriptor를 보관하고
  keyword 부모 값 변환, 배열 min/max, 누락 값 순서, 반환 sort 값을 연결했다.
  값 tuple을 source와 분리해 정렬하며 기존 hit.sort를 다른 정렬의 입력으로
  신뢰하지 않는다. 오류를 EngineResult로 전달하고 원본 source를 변조하지 않는다.
- `search_response_index_aware_with_request_filters`의 정렬/search_after/최종
  페이지 선택에 컨텍스트를 연결했다. post_filter 또는 search_after가 있는
  기존 경로에 대한 구현이며 일반 native 요청을 이 경로로 강제 우회하지 않는다.
  keyword multi-field가 없는 요청은 기존 정렬과 페이지 처리를 유지한다.
  keyword 누락 값은 asc/desc 모두 뒤로 보내고 일반 열 비교는 기존 규칙을 쓴다.
- 공개 API 테스트를 보강했다. 기존 일반 경로 red는 유지하고 같은 fixture의
  post_filter 경로에서 asc/desc 각 3페이지와 asc search_after 2건을 검증했다.
  추가 fixture는 배열/null/ignore_above, 기본 min/max 및 명시적 min/max,
  asc/desc의 누락 값 경계와 마지막 빈 페이지, 반환 sort/전체 건수/원본 source
  전체 불변성을 검증했다. multi-index 타입 충돌, nested sort 옵션, 혼합 sort,
  집계/fetch/normalizer 전체 호환성까지 입증한 테스트는 아니다.
- 전체 engine lib **859/859** (9.90초), 전체 node **642 passed / 2 failed**
  (5.80초), skip/filtered 0. 공개 API 통합은 최종 **5 passed / 1 failed**
  (0.10초), skip/filtered 0이다. 실패는 일반 native 경로의 asc 첫 페이지가
  여전히 a=zulu를 반환하는 재현이며, node의 기존 매핑 lookup/raw sort 400도
  남는다. 필터 경로 통과로 일반 경로 실패를 덮어쓰지 않는다.
- 로그는 `target/core-replacement-c05/` 아래
  `multi-field-engine-filtered-sort-tests.log`, `multi-field-engine-filtered-sort-tests-v2.log`,
  `multi-field-engine-filtered-sort-tests-v3.log`, `multi-field-engine-filtered-sort-engine-full.log`,
  `multi-field-engine-filtered-sort-node-full.log`다.
  engine source SHA-256 `29edb2c5b93e1956a5988598b8d6ccd207d066f0a2cd0b5773a7617e1ecd4fb0`;
  engine full log `02469efb6b5093b504917c8a4e9949e02a5c989ecd962e66bb633daa94a2199e`;
  node full log `931c9d8d02b826f4c99d08a26bd54cd265aa0ca99e8eac5c3a3558c88dda4a0f`.
- 다음 연결 대상은 일반 snapshot 검색이 호출하는
  `search_hits_page_for_query_index_aware_scoped`/`search_hits_page_for_query_native_scoped`와
  shard/index 페이지 병합이다. 이미 잘린 후보를 나중에 재정렬하는 것으로는
  정확성을 보장할 수 없으므로 페이지 자르기 전 매핑 값을 적용해야 한다.
  segment별 keyword ordinal을 그대로 비교하지 않고 numeric fast path를 유지한다.
- C02 내부 범위와 전체 40개 계획은 유지한다. 이번 binary 테스트/release 빌드/
  실제 참조/live/전체 성능 gate는 미실행이다. end-to-end 구현 단위 수락 전
  전체 반복 벤치마크와 최초 v0.6.0 대비 누적 5% 기준을 적용한다.
  전체 수락 **0/40**, 마지막 성능 FAIL, 빈 ledger, 릴리즈 보류. 실행 세션 종료.

#### C02 진행: 일반 정렬 연결 및 실제 비교에서 드러난 두 경로

- 2026-09-08: 일반 엔진 source materialization과 full-native-sort 경로에도
  `MappedEngineSort`를 페이지 선택 전에 연결했다. 1/3 shard, 1/2 index,
  asc/desc, 보조 `_id` 정렬 유무를 공개 API 테스트로 검증했다.
  REST mapping lookup은 `.fields`도 탐색하며 엔진/REST 모두 keyword
  multi-field의 `doc_values: false` 정렬 요청을 거부하도록 보강했다.
- 이 시점 로컬 결과는 engine lib **859/859** (9.85초), 공개 API **7/7**
  (0.26초), node **645/645** (5.76초), binary **459/459** (18.01초,
  `--test-threads=1`)다. 로그는 `target/core-replacement-c05/`의
  `multi-field-general-sort-engine-full.log`, `multi-field-general-sort-node-full.log`,
  `multi-field-general-sort-binary-serial.log`에 있다. 이 통과가 아래 실제
  비교 실패를 대체하지 않는다.
- 새 6사례 fixture `tools/fixtures/multi-field-query-sort-contract.json`은
  명시적 child keyword의 asc/desc, fallback, search_after, post_filter,
  exists 및 배열/null/ignore_above를 포함하며 ID/source/sort 값을 비교한다.
  SHA-256 `e0019776660f19f8be3232117d691237cfd1a68b9724472873df35404c1dcdc2`.
- 후보를 release profile로 빌드했다(4분52초). 이는 배포/태그 생성이 아니다.
  후보 SHA-256 `5ffc7c6901ded3ef27e7e04d6399f9296c9e5b1679e4f79505f512d037e86bfa`.
  이전 후보는 `target/core-replacement-c05/steelsearch-before-multi-field-615ee147`에
  보존했다. 마지막 정식 성능 FAIL은 이전 615ee147 후보에 대한 기록이지
  새 5ffc7c 후보의 성능 측정 결과가 아니다.
- 실제 OpenSearch 3.7.0-SNAPSHOT 비교는 **1,794 passed / 2 failed / 0 skipped**.
  `target/core-replacement-c05/live-multi-field-general-sort/execution.json`에서
  count probe 통과, 모든 setup 실패 없음, binary/fixture 불변을 확인했다.
  동적 `value.keyword` 정렬은 기대 two/one 대신 one/two와 sort null을 반환했다.
  명시적 multi-field exists+정렬은 기대 array/z/a 대신 a/array/z와 sort null을
  반환했다. 두 실패는 상태 코드가 아니라 실제 순서/값 불일치이며 원문을 유지한다.
- 지연 쓰기는 `replay_document_with_routing`으로 반영되는데 이 경로에는
  동적 매핑 갱신이 없었다. 또한 source-candidate-post-filter의 두 분기에는
  기존 source-only 정렬이 남아 있었다. 공개 API에 두 회귀 테스트를 추가해
  **7 passed / 2 failed**로 먼저 재현했다
  (`multi-field-replay-exists-red.log`). 1/3 shard, asc/desc 페이지와 반환 값,
  exists 및 bool+exists를 검증하며 실패 기대치를 완화하지 않았다.
- 수정은 유효한 신규 replay 문서의 매핑 갱신(메타데이터/중복 검증 후)과
  source-candidate-post-filter의 페이지 선택 전 매핑 기반 정렬에 적용했다.
  수정 후 engine lib **859/859** (10.22초), 공개 API **9/9** (0.32초),
  node **645/645** (17.13초), binary **459/459** (21.56초)가 통과했다.
  node/binary는 `--test-threads=1`, 모두 ignored/filtered 0이다.
  로그는 `multi-field-replay-exists-engine-full.log` (SHA-256
  `de96f6bbf9ad753ffb525799dd5ec984ef3ee5c70e7037c206e4eae82bc6ca95`)와
  `multi-field-replay-exists-node-binary-full.log` (SHA-256
  `f3e7dc01aaa72822c06fc05f78951c2b5655c8eaac99e20826de1532ce54fbe5`)다.
  engine source SHA-256
  `7456b4aa1dbddb7bc17d16b9c2fc33deb953cc9f2b450bd0cc92dcea6687abc4`.
  이후 검증용 release profile 재빌드와 live/전체 반복 성능 측정을 완료했다.
  아래 후속 결과를 적용하며, 이 로컬 테스트 통과를 성능 통과로 해석하지 않는다.
  C02 normalizer/집계/fetch/기타 query 및 sort 옵션 범위는 남으며 단위 수락은
  전체 반복 벤치마크와 최초 v0.6.0 누적 5% gate 이후다. 전체 수락 **0/40**,
  마지막 정식 성능 FAIL, ledger 비어 있음, 릴리즈 보류를 유지한다.

#### C02 후속 검증: 실제 정렬 실패 해소, 새 후보의 큰 성능 회귀

- 2026-09-08: 검증용 release build는 **4분55초**, exit 0.
  `target/release/steelsearch` SHA-256은
  `5f578c2e58e1d9b211960ad4af3277547e8b5394f798fa61d2ff64021ba9dfd7`이다.
  빌드/검증 전후 engine source 해시 7456b4aa 및 node source 해시
  `684f23be90ae87108e5492221061ca6a0498c4ffe3824699294d69be3b6c51cd`가 일치했다.
  직전 5ffc7c 후보는
  `target/core-replacement-c05/steelsearch-before-replay-exists-5ffc7c69`에 보존했다.
- 동일한 실제 비교 fixture **1,796 passed / 0 failed / 0 skipped**.
  동적 keyword 정렬과 exists+정렬의 기존 실패가 모두 해소됐다. count probe 통과,
  setup 실패 없음, binary/fixtures unchanged true, helper exit 0이다.
  `target/core-replacement-c05/live-multi-field-replay-exists/execution.json`
  SHA-256 `03678917f82eade0bd159bc3e8ba5a182d52b3fb7677e4f98370fc930ec75952`.
  참조는 기능 검사용 OpenSearch **3.7.0-SNAPSHOT**이며 아래 성능용 2.19와 다르다.
- 같은 후보를 고정해 전체 반복 성능 gate를 새 디렉터리
  `target/core-replacement-c05/multi-field-replay-exists-repeated-full`에서 실행했다.
  baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/baseline05 순서,
  단일/3노드 **6회/12개 구성**, **1,093.4225초(18분13초)** 완료.
  하위 실행 exit 모두 0, 모든 구성 요청 오류 0, execution_inputs_verified true,
  error 없음. 최종 **numeric_budget_passed false**, gate exit 1,
  acceptance_established false다. 성능 측정 중 코드 변경/빌드/테스트는 하지 않았다.
- 최초 공개 v0.6.0 보고서를 기준으로 한 처리량 결과다. 반복을 평균하거나 합치지 않았다.

| 후보 실행 | 구성 | 처리량 ops/s | 최초 v0.6.0 대비 감소 |
| --- | --- | ---: | ---: |
| 01 | 단일 노드 | 515.5681 | 30.610984% |
| 01 | 3노드 | 810.8428 | 12.940851% |
| 04 | 단일 노드 | 529.1510 | 28.782886% |
| 04 | 3노드 | 818.2629 | 12.144166% |

- 최초 v0.6.0 대비 지연시간 증가율(%), 각 셀은 **mean / p95 / p99**다.
  표는 표시용 반올림이며 판정은 원본 정밀도로 각 항목을 독립 비교했다.

| 구성/시나리오 | 후보 01 증가율 | 후보 04 증가율 |
| --- | --- | --- |
| 단일/write | 12.61 / 19.37 / 28.40 | 7.95 / 12.75 / 22.27 |
| 단일/lexical | 50.23 / 76.13 / 305.29 | 44.78 / 71.68 / 290.43 |
| 단일/ranking | 38.60 / 92.04 / 241.37 | 31.74 / 57.49 / 239.18 |
| 단일/facet | 29.91 / 56.99 / 199.97 | 25.78 / 45.37 / 193.07 |
| 단일/sort_filter | 47.45 / 72.07 / 294.81 | 51.25 / 82.51 / 309.19 |
| 단일/nested | 28.35 / 79.85 / 236.74 | 28.93 / 64.78 / 244.56 |
| 단일/refresh | 152.64 / 296.20 / 293.57 | 146.02 / 287.75 / 293.74 |
| 3노드/write | 4.45 / 8.64 / 12.18 | 2.69 / 7.82 / 6.78 |
| 3노드/lexical | 5.32 / 3.83 / 60.60 | 2.20 / 1.39 / 35.58 |
| 3노드/ranking | 8.11 / 11.63 / 45.75 | 8.95 / 13.54 / 43.54 |
| 3노드/facet | 8.42 / 10.60 / 48.94 | 9.01 / 14.52 / 52.10 |
| 3노드/sort_filter | 8.93 / 9.95 / 44.40 | 4.48 / 5.23 / 37.98 |
| 3노드/nested | 2.84 / 3.26 / 42.14 | 2.61 / 4.39 / 45.93 |
| 3노드/refresh | 77.41 / 142.17 / 175.88 | 76.46 / 148.08 / 154.85 |

- 공개 기준 44개 지표 중 예산 이내는 후보01 **4/44**, 후보04 **6/44**다.
  같은 반복의 새 v0.6.0 기준으로도 각각 **5/44**, **8/44**만 이내다.
  기준선 자체 drift는 00에서 단일 refresh p99 +6.942137%, 05에서 3노드
  ranking p99 +5.038979%, sort_filter p95 +5.112723%, refresh p99 +6.489953%가
  초과했다. 이 변동으로 후보의 반복적인 큰 회귀 전체를 환경 탓으로 돌리지 않는다.
- 성능용 고정 OpenSearch **2.19** 처리량은 실행02 단일 288.9652/3노드112.0157,
  실행03 단일292.6868/3노드107.2677 ops/s다. 모든 시나리오 mean/p95/p99
  원본은 result.json의 checks[].published.opensearch_metrics와 각 summary에 있다.
  후보가 전체 처리량에서 더 빠르더라도 단일 노드 검색 p99는 OpenSearch보다
  느린 항목이 있으며, OpenSearch 대비 우위는 최초 v0.6.0 gate 실패를 상쇄하지 않는다.
  개발용 deferred-write/persistence 설정의 측정이며 운영 내구성 동등성까지 입증하지 않는다.
- plan SHA-256 `e4c96e868f20583ab10eff0479be8a73c885852a92409f95b305c6f709477dcd`;
  result SHA-256 `beb2b4ab4d547ac1b84a66ec9f8888f2fc2d6ce730b46e6f27819588419aeaee`.
  원본 v0.6.0/이전 후보/실패 live/이번 실패 성능 결과는 덮어쓰지 않았다.

다음 병목 진단 순서(아직 원인 확정이나 최적화 완료가 아님):

1. 보존한 5ffc7c 후보와 현재 5f578c 후보를 같은 입력/조건으로 비교해 replay
   매핑 갱신의 영향을 분리한다. 정렬 수정은 벤치마크의 일반 numeric 정렬에서
   조기 반환하지만, 이것만으로 replay 단일 변경의 성능 영향이 입증된 것은 아니다.
2. `document_for`는 비벡터 작업에도 384개 숫자의 embedding 배열을 넣지만
   `prepare_index`는 vector/hybrid 작업이 있을 때만 embedding을 명시적으로 매핑한다.
   새 replay 매핑 갱신이 이 필드를 동적 F64 색인 대상으로 만드는지 실제 schema/
   indexed value 수/refresh·writer·merge 비용을 측정해 확인한다. 이것은 현재
   유력한 코드 기반 가설이며 독립 실행으로 인과관계를 확정하지 않았다.
3. 이미 매핑된 scalar/array에 대한 반복 탐색, 숫자 다중값 색인과 refresh의
   할당/잠금/merge 비용을 분리해 최적화한다. 문서/필드를 벤치마크에서 삭제하거나
   정상 동적 매핑을 건너뛰어 기능을 줄이는 것으로 5%를 맞추지 않는다.
4. 의미 동작/전체 로컬/동일 live 회귀와 전체 반복 성능 gate를 다시 수행한다.
   단일 변경의 5% 이상 기여와 최적화 불가능성이 입증된 경우에만 ledger에
   등록하고 해당 기능을 제외한다. 현재는 그 조건이 충족되지 않아 ledger는 비어 있다.

- C02 전체 범위와 정식 수락 **0/40**을 유지한다. 최신 성능 결과는 이제
  **5f578c 후보의 FAIL**이며, 과거 615ee147 후보 결과가 아니다.
  목표는 진행 중이고 수락/릴리즈는 보류한다. 태그/커밋/배포를 하지 않았으며
  이번 검증 세션은 모두 종료했다.

#### C02 병목 분리: replay 전후 비교와 F64 저장 복사 제거

- 2026-09-08: 직전 턴은 실제 정렬 실패 수정 및 전체 반복 성능 실패 확인으로
  다음 진단 대상을 바꾼 진척이다. 현재 소스/바이너리/계획을 재확인한 뒤
  보존한 5ffc7c 후보와 5f578c 후보를 전/후/후/전 순서로 진단했다.
  `tools/run-core-refresh-work-diagnostic.py`, 각 30초, 단일 노드/3 shard,
  기존 5,000문서/384차원 source/4 clients/혼합 작업을 사용했다.
  진단은 `target/core-replacement-c05/replay-mapping-refresh-work`에 보존했다.
  전체 gate가 아니며 최초 v0.6.0 기준을 새 전 후보로 바꾸지 않는다.

| 실행 | 후보 | ops/s | refresh mean/p95/p99 ms | 추가 refresh 후 기대/native/fallback 건수 |
| --- | --- | ---: | --- | --- |
| 00 | 전 5ffc7c | 781.1226 | 7.8324 / 14.4608 / 18.3997 | 9257 / 9257 / 9257 |
| 01 | 후 5f578c | 581.1167 | 16.3480 / 48.1249 / 55.2273 | 8188 / 8188 / 8188 |
| 02 | 후 5f578c | 587.6615 | 15.7961 / 45.4699 / 53.3492 | 8219 / 8219 / 8219 |
| 03 | 전 5ffc7c | 749.7446 | 8.1587 / 15.9413 / 20.3304 | 9103 / 9103 / 9103 |

- 모든 요청 오류 0, 추가 refresh 두 번 모두 기대 건수와 일치했다.
  이는 건수 검증이지 전체 ID/source 일치 증거는 아니다. 00/01 및 03/02
  비교의 처리량 감소는 각각 **25.604940%, 21.618433%**다. 두 바이너리 사이
  변경 묶음의 회귀 재현이며, 이 진단만으로 모든 비용을 단일 함수에 귀속하지 않는다.
  plan SHA-256 `7d8cf411d54a5489308da684d1f199f31ce0c87dc3ae2307816bcfba5e3d5312`;
  result SHA-256 `3419a24c088e14633984cc5dc0e31a10173d5593de589d683b43c0bde79f5430`.
- 이어 두 후보를 `tools/run-core-cpu-diagnostic.py --operation mixed --topology single-node`로
  각각 프로파일링했다. 45초 작업 중 20초 CPU 표본, CPU/off-CPU 한계 및
  도구 오버헤드를 갖는 진단이며 수락용 성능 값이 아니다. 두 perf/matrix exit 0,
  binary 해시 불변, lost samples 0이다. 결과는
  `target/core-replacement-c05/replay-mapping-cpu-before` 및 `replay-mapping-cpu-after`의
  `diagnostic.json`, `perf.data`, `symbol-report.txt`에 있다.
  diagnostic SHA-256은 전
  `815cd45edf368bc1594b2f02e374d334099f6e8467da6f5f3cf2e47797477109`, 후
  `6c467fbe77003953115af629fc43eb68dc2278056d11399d0885d83130b74a60`이다.
- 표시된 self 비율 합산으로 merge_thread_0 표본 비중이 약 **4.77% -> 25.59%**였다.
  후 후보에서 숫자 columnar iterator/statistics/serialization과 postings 병합이
  두드러졌고, 문서 역직렬화 iterator도 4.14%를 차지했다. 이는 전체 표본에서의
  상대 비중이며, 절대 HTTP 지연 기여율이나 무손실 인과 분해로 해석하지 않는다.
- `build_tantivy_schema`는 F64의 mapping.stored가 false여도 항상 set_stored를
  적용했다. 반면 document ID lookup은 저장 문서 전체를 읽는다. 실제 replay로
  384개 숫자 배열을 동적 F64로 매핑하는 회귀 테스트를 추가했고, 기대 저장 값 0개
  대신 **384개**를 읽어 실패했다(`dynamic-numeric-storage-red.log`, 1 failed).
  명시적으로 store=true인 별도 F64 필드도 같은 fixture에 넣었다.
- F64의 내부 stored 설정만 mapping.stored를 따르게 수정했다. indexed/fast 설정과
  모든 실제 색인 값, 동적 매핑 갱신 및 source는 유지했다. 다른 타입의 저장 옵션,
  index/doc_values 전체 계약까지 이 변경으로 완료했다고 주장하지 않는다.
  회귀 테스트는 384개 fast-field 값 전체, 첫/중간/마지막 값의 native TermQuery,
  저장 배열 0개/store=true 필드 2개/ID 보존, 공개 검색 원본 source를 검증한다.
- 수정 후 전체 engine lib **860/860** (9.85초), 공개 API **9/9** (0.31초),
  ignored/filtered 0. 로그 `dynamic-numeric-storage-engine-full.log` SHA-256
  `b6e249f84717c5e5f0705dda279e78ba968b23fc5e354019ba431950b891d2c7`;
  engine source SHA-256 `2538096271037e26cd5194a091b9b58882adde76415200076b74c0a131a85d40`.
  node **645/645** (14.36초), binary **459/459** (22.03초)도 통과했다.
  두 실행은 `--test-threads=1`, ignored/filtered 0이며 로그는
  `dynamic-numeric-storage-node-binary-full.log`, SHA-256
  `c9e7609cb16a916b3c1a1f3106b5de9c4c597dd77c4311379ac1476f06a19fd0`이다.
  git diff --check도 통과했다. 제품 변경 후 새 release build/live/전체 반복
  성능 gate는 아직 미실행이며 성능 개선을 주장하지 않는다. 현재 release
  바이너리는 저장 옵션 수정 전 5f578c 후보다. 이번 진단/검증 세션은 모두 종료했다.
- 다음은 전체 로컬 회귀 확인 후 수정 후보를 빌드해 같은 실제 호환성 및
  전후 refresh 진단을 수행하는 것이다. 남는 숫자 컬럼 병합 비용을 줄이되
  index/doc_values를 끄거나 입력 배열을 삭제하지 않는다. C02 end-to-end 수락 전
  전체 반복 gate와 최초 v0.6.0 누적 5% 기준은 유지한다. 정식 수락 **0/40**,
  최신 정식 성능은 여전히 5f578c FAIL, ledger 비어 있음, 릴리즈 보류다.

#### C02 후속: F64 저장 최적화의 효과와 숫자 doc values 배열 조회

- 2026-09-08: 직전 턴의 저장 옵션 수정/전체 로컬 검증을 진척으로 분류했다.
  source 해시 25380962, 기존 binary 5f578c 및 실행 세션 없음을 재확인하고
  저장 수정 전 binary를 `steelsearch-before-f64-storage-5f578c2e`에 보존했다.
  4분54초 release build 후 후보는
  `e796e2c4591370d2a59a1746e2e0e1ec6d3afc75eef0ddb0dc63bae117aed138`이다.
- `tools/fixtures/dynamic-numeric-storage-contract.json`을 추가했다. 첫 버전 6건은
  동적 F64 배열 native/fallback term-source, stored_fields, docvalue_fields를
  검사한다. fixture SHA-256
  `af935952241fabeb20ce38841172901a23694382165582139a8accdb9464befd`.
  기존 전체 비교에 추가한 실제 결과는 **1,800 passed / 2 failed / 0 skipped**.
  두 실패는 docvalue_fields의 이중 배열이다. 참조는 `[0.25,12.25,200.25,383.25]`,
  후보는 `[[0.25,12.25,200.25,383.25]]`를 반환했다. native/fallback 모두 동일하며
  별도 store=true 필드도 같은 오류다. term/source와 stored_fields는 통과했다.
  `target/core-replacement-c05/live-dynamic-numeric-storage/execution.json` SHA-256
  `930c38471cf8131a85da5dc9d662997acdc430d1e41af22a2096fc46ffe9889f`.
  count probe, binary/fixture 불변 검사 통과, helper exit 1이며 실패를 보존했다.
- 저장 복사 제거만의 효과를 분리하기 위해 e796e2 후보를 그대로 고정한 채
  `run-core-refresh-work-diagnostic.py`의 전/후/후/전 30초 진단을 수행했다.
  전 후보 5f578c, 후 후보 e796e2다. 그동안 코드 변경/빌드/테스트를 하지 않았다.
  결과 디렉터리 `target/core-replacement-c05/f64-storage-refresh-work`:

| 실행 | 후보 | ops/s | refresh mean/p95/p99 ms |
| --- | --- | ---: | --- |
| 00 | 전 5f578c | 579.4412 | 16.3985 / 46.3458 / 55.5329 |
| 01 | 후 e796e2 | 696.7359 | 9.6130 / 18.3428 / 24.5419 |
| 02 | 후 e796e2 | 680.8947 | 10.1459 / 19.2844 / 24.7309 |
| 03 | 전 5f578c | 594.9565 | 15.3613 / 45.4321 / 54.4740 |

- 대응 쌍 처리량 개선은 **20.242732%, 14.444437%**다. 모든 요청 오류 0,
  추가 refresh 두 번 뒤 기대/native/fallback 건수는 실행별
  8175/8809/8725/8253으로 각각 일치했다. 이는 ID/source 전체 검사가 아니라 건수
  진단이다. docvalue_fields 실패가 있는 후보의 국소 진단이므로 수락 근거가 아니며
  전체 반복 게이트나 최초 v0.6.0 기준 비교를 대신하지 않는다.
  plan SHA-256 `fda4a4a23b55ca4af9e79d9b5a4969cbba8aec1962221bcb158c513370101b1f`;
  result SHA-256 `8753fa20750e2c7dbf938406262ce5ba027057ec81d19bd959afd2d7eaf47089`.
- `build_search_hit_fields`의 숫자 docvalue_fields 처리에 배열 평탄화/null 제외/
  오름차순 정렬을 연결했다. 숫자 중복은 유지하며 원본 source를 변경하지 않는다.
  저장 옵션 최적화는 그대로 유지했다. 문자열/날짜/boolean/multi-field doc values,
  숫자 coercion/format/null_value 옵션 전체까지 완료한 변경은 아니다.
- 회귀는 native/fallback 각각 중첩 배열/null/중복, 단일 scalar, 값 없는 배열,
  2^53 초과 정수의 정밀 순서, 원본 source 및 총건수를 검사한다.
  node **646/646** (12.86초), binary **459/459** (17.46초), serial,
  ignored/filtered 0. 로그 `numeric-docvalue-array-node-binary-full.log` SHA-256
  `a0d78176ace5ded7e42a6bd825e6f8c7fe8ff89c5f3d2c168c3fb773789cf7df`.
  엔진 소스는 이전 860/860+공개 API9/9 검증 때와 동일하다.
- fixture를 native/fallback의 배열 정렬·중복·null·중첩 배열 2건으로 보강했다.
  새 8건 버전 SHA-256
  `b2551522cb1a9d1f306e55e17948ad67d867d3988977bfe9af450a326ce88663`.
  실패한 이전 실행의 fixture 해시/응답을 새 버전으로 덮어쓰지 않았다.
  e796e2 후보는 `steelsearch-before-numeric-docvalue-fetch-e796e2c4`에 보존했고,
  이후 숫자 조회 수정 포함 release build/실제 비교/전체 반복 성능을 완료했다.
  아래 결과를 적용하며, 국소 진단의 개선을 전체 gate 통과로 해석하지 않는다.
  C02 end-to-end 수락 전 전체 반복 gate와 최초
  v0.6.0 누적 5% 기준, 정식 수락 **0/40**, 빈 ledger와 릴리즈 보류를 유지한다.

#### C02 숫자 저장·조회 후속 검증: 호환성 통과, 누적 성능 초과 유지

- 2026-09-08: 최종 release build **4분43초**, exit 0, 후보 SHA-256
  `72f204eb107a53acf28fb6418cada11d780fccf0766849229a0124b9da89d6ef`.
  node source `a9c119d6eab9af7a6736223f75a2249ce530439e0b5a73af450ad18843e89c14`,
  engine source 25380962 해시는 빌드/검증 전후 동일하다. 배포용 태그를 만든 것은 아니다.
- 실제 OpenSearch 3.7.0-SNAPSHOT 비교 **1,804 passed / 0 failed / 0 skipped**.
  숫자 배열 전용 8건과 기존 전체 1,796건이 통과했다. count probe 및
  binary/fixture 불변 확인도 통과했고 helper exit 0이다. 이중 배열 실패와
  추가한 native/fallback 정렬·중복·null·중첩 배열 사례가 실제로 해소됐다.
  `target/core-replacement-c05/live-numeric-docvalue-array/execution.json` SHA-256
  `d21eeedb4d04855074f61f3978eb44d96e94efbe3adc689dcde85b65247cd456`.
- 후보를 고정해 `target/core-replacement-c05/numeric-storage-fetch-repeated-full`에서
  **6회/12개 구성 전체 반복 gate**를 실행했다. 기존 고정 순서/설정/최초 v0.6.0
  기준을 유지했으며 측정 중 코드/실행 도구 변경, 빌드/테스트는 하지 않았다.
  **1,097.2544초(18분17초)** 완료, 하위 exit 모두 0, 모든 구성 요청 오류 0,
  execution_inputs_verified true, error 없음. 최종 **numeric_budget_passed false**,
  gate exit 1, acceptance_established false다.

| 후보 실행 | 구성 | 처리량 ops/s | 최초 공개 v0.6.0 대비 감소 |
| --- | --- | ---: | ---: |
| 01 | 단일 노드 | 624.1829 | 15.992792% |
| 01 | 3노드 | 843.7721 | 9.405274% |
| 04 | 단일 노드 | 625.3366 | 15.837515% |
| 04 | 3노드 | 859.7857 | 7.685913% |

- 아래는 최초 공개 v0.6.0 대비 지연시간 증가율(%), 셀 순서는 **mean/p95/p99**다.
  표시만 반올림하며 원본 정밀도로 지표별 한도를 적용한다.

| 구성/시나리오 | 후보 01 증가율 | 후보 04 증가율 |
| --- | --- | --- |
| 단일/write | 15.20 / 23.54 / 29.83 | 14.81 / 22.44 / 27.23 |
| 단일/lexical | 16.58 / 32.67 / 38.76 | 16.46 / 31.59 / 35.72 |
| 단일/ranking | 18.21 / 33.43 / 33.52 | 18.92 / 32.55 / 35.46 |
| 단일/facet | 19.00 / 26.80 / 38.17 | 18.28 / 28.10 / 38.67 |
| 단일/sort_filter | 22.70 / 43.46 / 40.61 | 20.66 / 41.61 / 43.26 |
| 단일/nested | 9.32 / 20.14 / 25.74 | 9.95 / 23.86 / 33.39 |
| 단일/refresh | 42.64 / 38.23 / 53.29 | 42.40 / 39.22 / 52.12 |
| 3노드/write | 6.97 / 12.28 / 13.89 | 5.96 / 10.70 / 8.88 |
| 3노드/lexical | 4.70 / 7.61 / 23.86 | 3.48 / 5.63 / 21.05 |
| 3노드/ranking | 10.11 / 14.82 / 23.48 | 7.39 / 12.64 / 22.59 |
| 3노드/facet | 10.57 / 15.85 / 27.26 | 7.91 / 12.98 / 17.28 |
| 3노드/sort_filter | 6.04 / 10.09 / 30.93 | 4.57 / 7.40 / 20.60 |
| 3노드/nested | 3.66 / 7.00 / 24.68 | 2.15 / 8.26 / 17.08 |
| 3노드/refresh | 32.37 / 35.71 / 43.43 | 29.35 / 34.94 / 45.71 |

- 공개 기준 44개 지표 중 예산 이내는 후보01 **2/44**, 후보04 **3/44**,
  같은 반복의 새 v0.6.0 기준으로도 **3/44**, **5/44**다. 처리량 및 큰 p99
  회귀는 앞선 5f578c 대비 완화됐지만 모든 지표가 개선되거나 예산을 통과한 것은 아니다.
  반복을 평균하거나 좋은 실행만 선택하지 않는다.
- 기준선 자체 drift 초과도 유지한다: 실행00 단일 sort_filter p95 +5.609688%,
  p99 +5.157666%, refresh p99 +7.961663%; 3노드 nested p99 +10.237152%,
  refresh p99 +5.065280%. 실행05 단일 refresh p99 +5.969342%,
  3노드 nested p99 +8.813040%. 기준선 변동으로 후보의 전체 초과를 설명하지 않는다.
- 고정 성능 참조 OpenSearch 2.19의 처리량은 02 단일287.0948/3노드113.1171,
  03 단일283.7919/3노드114.6514 ops/s다. 모든 시나리오의 비교 원본은
  result.json의 checks[].published.opensearch_metrics와 각 summary에 있다.
  기능 참조 3.7.0-SNAPSHOT과 구분하며, 개발용 persistence/deferred-write 조건의
  결과를 운영 내구성 동등성 증거로 사용하지 않는다.
- plan SHA-256 `f6cbc6bacec2f447b289ad7a37379ca7ef14bc4a71d9d5013c6ce523c75cb60f`;
  result SHA-256 `75f616073b8f4fd9b6e1de4038b033fadeb7f02de465dfe3e9661d748ddb2d40`.
- 다음 진단은 숫자 컬럼의 반복 병합 비용이다. 현재 Tantivy 0.21.1 기본
  LogMergePolicy는 min_layer_size=10,000, min_num_segments=8이다. 작은 refresh
  세그먼트와 수천 문서의 큰 숫자 컬럼이 같은 구간에서 반복 병합되는지
  실제 segment 크기/병합 횟수/CPU로 확인한다. 아직 정책은 변경하지 않았다.
  정책을 조정할 경우 세그먼트 수의 상한 동작과 검색/삭제/스냅샷/페이지 일관성을
  함께 검증하고 전체 반복 gate를 다시 실행한다. NoMerge로 무한 누적시키거나
  숫자 index/doc_values를 비활성화하는 것은 대안이 아니다.
- C02의 normalizer/옵션/다중 필드 집계·조회 등 전체 범위는 그대로 남는다.
  목표는 진행 중이며 정식 수락 **0/40**, 최신 정식 성능은 **72f204 후보 FAIL**이다.
  최적화 불가능성이 입증되지 않아 ledger는 비어 있고 릴리즈는 보류한다.
  태그/커밋/배포를 하지 않았으며 이번 빌드/진단/live/성능 실행 세션은 모두 종료했다.

#### C02 병합 정책 최적화 진행

- 2026-09-08: 직전 실제 호환성/전체 성능 결과는 진척이다. 현재 후보 72f204와
  engine source 25380962를 재확인하고 Tantivy 0.21.1의 실제 MergePolicy API로
  작은 refresh 세그먼트 병합을 재현했다. 새 `tests/merge_policy.rs`의 모델은
  seed 1000/1667/5000문서, batch 1/4/16문서, 768회 refresh를 사용한다.
  비동기 실행이나 지연시간 측정이 아니라 메타데이터 재작성량 모델이다.
- 기본 floor 10000은 seed 1667문서와 작은 4문서 세그먼트 8개를 함께 병합했다.
  floor 512는 작은 8개만 병합했다. 9개 모델 조합 모두 재작성 문서 수가 절반
  미만으로 줄었으며, 조정 정책도 108~109회 병합을 계속 수행했다.
  병합 완료 시점의 세그먼트 최대치는 모델에서 8~16개였다. 이를 임의 작업량의
  전역 상한이나 실제 CPU 절감률로 주장하지 않는다.
- `TantivySearchState::build_from_documents` writer에 LogMergePolicy의
  min_layer_size만 **512**로 설정했다. min_num_segments=8 및 다른 정책 설정은
  유지했다. NoMerge, 필드/문서 제외, index/doc_values 비활성화는 하지 않았다.
  실제 엔진 writer에서 정책을 꺼내 병합 후보를 검사하는 회귀도 추가했다.
- 실제 Tantivy writer 테스트는 숫자32값/doc, 초기1024문서, 24회 4문서 append와
  refresh, doc-0 삭제를 거쳤다. 병합을 기다린 후 실제 segment 크기는
  **[1023,88,4,4]**, 현재1119/이전reader1024건이었다. 모든 살아 있는 문서의
  숫자 fast-field 값, ID, 삭제된 값의 term 검색, 이전 reader 보존을 검증했다.
  최종 세그먼트 수 <=16 검증도 통과했다. 이는 유한 fixture의 검사다.
- 전체 engine lib **861/861** (10.00초), 공개 multi-field API **9/9** (0.35초),
  병합 통합 **3/3** (0.88초); 보강한 병합 통합 재실행 **3/3** (0.81초) 통과.
  node **646/646** (15.61초), binary **459/459** (21.98초), 둘은 serial,
  모두 ignored/filtered 0. 로그는 `target/core-replacement-c05/`의
  `merge-floor-engine-full.log` (SHA-256
  `e92e7fe1716ae783142ffa455e51ec4fe3530e4b0292484f85f8664efb887e58`),
  `merge-floor-actual-and-model.log` (SHA-256
  `0a393311bb0ac423ad4c963bfc39582758d88e8335e3f57d0730665584441600`),
  `merge-floor-node-binary-full.log` (SHA-256
  `7e873277a650e33c779c88a22fe5ea5053add965a99df3de24f5e0105a0a0eef`)다.
- engine source SHA-256
  `79b67daa7dd690d71d26152bd54d4140dc7ab0cbb5d46e9697eec0c3d4f0dbb5`.
  이전 후보를 `steelsearch-before-merge-floor-72f204eb`에 보존했다.
  아래 후속 검증으로 빌드/공개 API/live/전체 성능 실행을 완료했다.

#### C02 병합 정책 후속 검증: 처리량 회복, 누적 예산 미통과

- 2026-09-08: 최적화 빌드 4분54초, 후보 SHA-256
  `bc56f6f88ce0a0b7bf97a15babe04bc2bd4477ab6727c17538cbcdaa84651e18`.
  공개 API 회귀(3168문서, 1/3shard, refresh/삭제/페이지 경계)를 포함한
  병합 통합 테스트 **4/4** 통과(3.00초). 로그
  `target/core-replacement-c05/merge-floor-public-paging.log` SHA-256
  `5db013d1e25f7d5f171e6d51f07e1dbdfee425463d47b45aaa44065607922155`.
- `target/core-replacement-c05/live-merge-floor/execution.json`:
  호환성 **1804 passed / 0 failed / 0 skipped**, count probe 통과,
  binary/fixture 불변 확인. SHA-256
  `a8e41a140c1342b15ca2a930f60657c4b5554563e876d25f34e181d2688d7a19`.
  기능 참조는 OpenSearch 3.7.0-SNAPSHOT이며 성능 참조 2.19와 구분한다.
- `target/core-replacement-c05/merge-floor-repeated-full/` 전체 반복:
  기준선00/후보01/OpenSearch02/OpenSearch03/후보04/기준선05 모두 정상 종료,
  12개 구성 요청 오류 **0**, 총1095.00초. 입력 검증 true, 실행 오류 null,
  **numeric_budget_passed=false**. 최초 공개 v0.6.0 기준을 변경하지 않았다.

| 처리량 (ops/s) | v0.6.0 고정 기준 | 후보01 | 누적 저하 | 후보04 | 누적 저하 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 단일 노드 | 743.0111 | 719.7475 | 3.13% | 721.1085 | 2.95% |
| 3노드 | 931.3700 | 861.2086 | 7.53% | 889.8372 | 4.46% |

시나리오별 지연시간 누적 증가율(%), 각 셀은 mean / p95 / p99다.
음수는 개선이다. 처리량과 각 지연 지표를 따로 판정한다.

| 시나리오 | 후보01 | 후보04 |
| --- | ---: | ---: |
| 단일/write | 1.30 / 4.41 / 4.42 | 1.50 / 3.42 / 3.62 |
| 단일/lexical | 1.77 / -0.37 / -0.73 | 1.92 / -1.00 / -3.04 |
| 단일/ranking | 4.69 / 3.88 / 0.59 | 3.83 / 2.37 / -0.90 |
| 단일/facet | 3.88 / 2.99 / 1.33 | 2.27 / 0.11 / -2.29 |
| 단일/sort_filter | 5.54 / 5.45 / 3.36 | 7.20 / 7.75 / 1.75 |
| 단일/nested | -2.13 / -0.08 / -3.98 | -1.62 / 0.45 / -9.03 |
| 단일/refresh | 8.94 / -3.38 / -0.89 | 9.80 / -4.66 / 2.83 |
| 3노드/write | 5.90 / 9.79 / 9.13 | 1.48 / 1.68 / -1.60 |
| 3노드/lexical | 3.73 / 5.58 / 17.69 | 0.45 / 0.65 / 13.40 |
| 3노드/ranking | 7.50 / 10.26 / 21.85 | 4.67 / 6.59 / 13.96 |
| 3노드/facet | 7.98 / 11.25 / 17.52 | 5.15 / 6.23 / 16.18 |
| 3노드/sort_filter | 7.65 / 12.40 / 21.05 | 4.12 / 6.33 / 11.64 |
| 3노드/nested | 2.65 / 5.08 / 15.99 | -0.15 / 0.78 / 12.26 |
| 3노드/refresh | 23.64 / 22.18 / 23.27 | 18.03 / 19.25 / 20.55 |

- 공개 기준 44개 지표 중 예산 이내는 **21/44**, **29/44**다.
  직전 후보의 2/44, 3/44보다 늘었으나, 반복 평균이나 좋은 실행 선택으로
  실패를 지우지 않는다. 단일 처리량은 회복했지만 일부 지연은 여전히 초과한다.
- 기준선 drift 초과: 실행00 단일 write p95 +6.473497%, p99 +7.586612%,
  refresh p99 +8.479594%; 3노드 ranking p99 +7.814154%.
  실행05 단일 write p99 +7.864696%. 이를 후보 회귀 전체의 원인으로 단정하지 않는다.
- 모든 원시 지표와 OpenSearch 시나리오 비교는 각 summary 및
  `result.json`의 `checks[].published.opensearch_metrics`에 보존했다.
  개발용 persistence/deferred-write 조건이므로 운영 내구성 동등성을 주장하지 않는다.
  plan SHA-256 `66876e2bf51ca2d0b46e5af8a3ccc15ff3ec4fbaf642537bc0c5ffb48f32f282`;
  result SHA-256 `fda336945c76d00a7de4ac7b6d6f4d28bb4250b07f8e311e448229998e5200d3`.
- 후속 3노드 혼합 CPU 진단도 완료했다:
  `target/core-replacement-c05/merge-floor-three-node-cpu/diagnostic.json`.
  45초 부하 중 20.76초 관찰, 49Hz CPU 표본, perf/matrix 종료0, 요청 오류0,
  후보 바이너리 불변. 서버 CPU 합28.30초, 부하 생성기12.02초였다.
  전체 표본(부하 생성기 포함)에서 IndexMerger::write inclusive 13.84%,
  write_fast_fields inclusive 8.51%, 집계 collect_simple_bucket_aggregations
  self 1.92%가 관찰됐다. inclusive 수치는 중첩되므로 더하지 않는다.
  상대 CPU 표본은 off-CPU 대기나 HTTP 지연 기여율이 아니며 성능 gate를 대신하지 않는다.
- 다음 작업은 실제 refresh의 add/commit/reload/doc-ID 조회 시간 및 병합 세그먼트
  변화와 CPU 진단을 연결해 숫자 컬럼 재작성과 검색 비용을 분리하는 것이다.
  정책을 추가 조정하면 장시간 refresh/삭제/이전 reader/페이지 일관성 검증과
  전체 반복 gate를 다시 수행한다. 기능 누락으로 예산을 맞추지 않는다.
- C02 normalizer/옵션/다중 필드 집계·조회 등은 아직 남아 있다.
  정식 수락 **0/40**, 최신 정식 성능 **bc56f6 후보 FAIL**, 릴리즈 보류다.
  최적화 불가능성이 입증되지 않아 제외 ledger는 비어 있다.
  태그/커밋/배포 없이 이번 빌드/live/전체 성능/CPU 진단은 모두 종료했다.

#### C02 3노드 refresh 비용 분리 진단

- 2026-09-08: 직전 전체 gate/CPU 진단 완료는 진척으로 분류한다. 이번에는
  프로덕션 바이너리를 변경하지 않고 `run-core-refresh-work-diagnostic.py`에
  명시적인 single-node/three-node 선택과 선택형 노드별 refresh 카운터를 추가했다.
  기존 단일 노드 기본값은 유지한다. 3노드는 replica=1, 실제 서버3개 신원 검증을
  사용한다. 각 엔드포인트의 로컬 카운터만 수집하고 원격 placeholder/중복 node ID/
  누락 또는 음수·bool 카운터는 거부한다. 원시 응답과 URL을 함께 보존한다.
- 최초 확장 실행 `target/core-replacement-c05/merge-floor-three-node-refresh-work/`
  은 노드 카운터를 얻었으나 가시성 관측이 첫 엔드포인트에 한정됐다.
  result SHA-256 `48064336dbc7bb4f274f4e0c25c39244aea6d0b6088382d89ab6ee4aa27d0e8e`.
  이를 전체 문서 가시성/유실 증거로 사용하지 않는다. 부하 도구는 seed를
  doc_id별, 이후 쓰기를 client_id별 엔드포인트로 분배한다.
- 모든 엔드포인트를 drain한 뒤 각각 native/fallback 검색하도록 보강했다.
  endpoint별 원본과 이전 첫 엔드포인트 관측 필드를 함께 유지했다.
  전용 테스트8개 및 CPU/gate 도구 회귀를 합해 **29/29 통과**했다.
  도구 SHA-256 `ff6bbb97f8478ee4767b67601ba7c88f629ca2eb35524a9b51896f048c9f43c3`;
  테스트 SHA-256 `3ef650669a0ef4186bbcff3b3d02c3b64711f5c2095293013b4a61aec3c492c3`.
- 새 `target/core-replacement-c05/merge-floor-three-node-refresh-endpoints/`에서
  72f204(변경 전)/bc56f6(변경 후)/bc56f6/72f204 순서로 각각30초 혼합 부하,
  5000문서/384차원 원본/4클라이언트/3shard/replica1/seed13 실행 완료.
  4회 모두 요청 오류0, 바이너리/도구 불변 및 런타임 신원 검증 통과.
  성능 gate가 아닌 추가 진단이며 최신 정식 결과를 대체하지 않는다.

| 실행 | 처리량 ops/s | refresh mean / p99 ms | add / commit / reload / doc-ID 누적 초 |
| --- | ---: | ---: | ---: |
| 00 변경 전 | 912.3776 | 10.3591 / 27.7064 | 0.4771 / 18.4455 / 0.3678 / 0.5491 |
| 01 변경 후 | 934.5964 | 9.8101 / 25.5060 | 0.5209 / 18.1279 / 0.3928 / 0.3105 |
| 02 변경 후 | 919.0476 | 10.0220 / 25.7244 | 0.4844 / 18.1992 / 0.3988 / 0.3266 |
| 03 변경 전 | 910.4486 | 10.2954 / 27.2480 | 0.4344 / 18.3870 / 0.3646 / 0.5313 |

- 시간 카운터는 측정 후 순차 수집한 3노드 합계다. 준비 단계와 별도 요청의
  영향 및 계측하지 않은 구간이 있어 HTTP 지연시간의 완전한 분해가 아니다.
  `append_documents`에서 document_add는 문서 변환/큐 삽입이고 실제 비동기
  색인 비용은 commit 대기에 포함될 수 있다. writer lock 대기도 별도다.
  Tantivy 0.21.1 `IndexWriter::prepare_commit`은 워커 join 후 워커를 재생성한다.
  따라서 commit 카운터를 병합 CPU 시간과 동일시하거나 병합만 원인으로 단정하지 않는다.
- 마지막 drain 후 endpoint별 native/fallback 수는 모두 일치했다:
  00 [3970,2959,3025], 01 [4039,2973,3046],
  02 [3999,2962,3025], 03 [3969,2955,3022].
  합계는 각각 성공한 쓰기+seed의 9954/10058/9986/9946과 같다.
  ID/내용의 전역 유일성 또는 클러스터 전역 검색 동등성을 증명한 것은 아니다.
  첫 엔드포인트의 부분 count를 전체 count로 주장하지 않는다.
- plan SHA-256 `11ae246b22fa8bf120f438500013c982eeed9e11985acf116a6e71196cf2b2e0`;
  result SHA-256 `ee19e2d0a4c87fd063368165232345832ed0dce01012f36e46eb90002c3fba6e`.
- 다음 최적화 우선순위는 doc-ID lookup보다 commit의 실제 색인/세그먼트 확정/
  워커 재생성 비용 분리다. 현재 정책은 유지하고 작은 refresh 배치의 commit
  호출 스택과 워커 작업을 비교한다. 수치를 맞추려고 refresh 가시성이나 숫자
  index/doc_values를 생략하지 않는다. 코드 변경 후에는 기능 검증과 전체 반복
  gate를 다시 실행해야 하며 이번 진단으로 구현 단위를 완료 처리하지 않는다.
- 정식 수락 **0/40**, C02 미완료, 최신 정식 성능 **bc56f6 FAIL**, ledger 비어 있음,
  릴리즈 보류를 유지한다. 이번 진단 실행은 모두 종료했고 태그/커밋/배포는 없다.

#### C02 RAM 메타데이터 잠금 알림 구현 및 독립 검증

- 2026-09-08: 직전 3노드 카운터 진단은 commit 비용으로 다음 조사 범위를
  좁힌 진척이다. `examples/refresh_commit_diagnostic.rs`를 추가해 실제 Tantivy
  writer의 add / prepare_commit / PreparedCommit::commit / reader.reload 시간을
  각각 측정했다. seed1667, batch4, refresh256회, 숫자384값/doc이며 숫자 생성식은
  HTTP 부하 도구 vector_for의 1000개 값 반복 분포와 같다. ID는 순차적이다.
  HTTP/원본 fetch/엔진 라우팅/동시 검색이 없는 독립 진단이다.
- floor10000/512/512/10000 각각에 indexed+fast, indexed만, fast만, 둘 다 없는
  네 대조군을 실행한다. 기능을 끈 대조군은 원인 분석용일 뿐 후보가 아니다.
  매 refresh 정확한 count, 최종 모든 ID의 유일성/누락, 활성 fast-field의 전체
  숫자 값, 활성 색인의 term count, 숫자 비저장 및 이전 reader 보존을 검증한다.
  final merge drain도 따로 기록하며 검증/최종 drain 시간은 단계 표본에서 제외한다.
- 첫 독립 실행은 정상 종료: `target/core-replacement-c05/refresh-commit-components.jsonl`
  SHA-256 `2fc6c15d74c8acd8825aaa920642168f91c925e6bcbd0b47f786e3dac57b75ff`.
  원본 실행 파일은 `refresh-commit-diagnostic-d1500e43`에 보존했다(SHA-256
  `d1500e436cb74af3a4c6088dc3b40d28250a0c3cddbd7de20534f65efc0ffe2c`).
  prepare_commit가 크게 나타났고 일부 prepare/reload 표본에 약100ms 대기가 있었다.
- 로컬 Tantivy 0.21.1 소스의 `directory/directory.rs`는 blocking 파일 잠금
  충돌 시 **100ms씩 최대100회** 재시도한다. `reader/mod.rs::open_segment_readers`
  는 GC로부터 세그먼트를 보호하려고 META_LOCK을 획득한다.
  이를 bypass하지 않고 RAM 경로의 잠금 해제 알림으로 대기 방식을 바꿨다.
- 새 `src/refresh_directory.rs`는 RamDirectory의 파일/원자적 쓰기/watch API를
  위임한다. 실제 잠금 파일 획득은 기존 nonblocking acquire_lock으로 처리하며,
  blocking 충돌만 공유 Mutex+Condvar로 대기한다. 잠금 파일을 해제한 후 notify_all,
  대기 등록과 해제는 같은 mutex를 사용해 알림 유실을 방지한다. clone도 같은
  wake 상태를 공유하고, 비차단 LockBusy/IO 오류 및 최대10초 대기 한도를 유지한다.
  `TantivySearchState::build_from_documents`의 RAM index 생성에 연결했다.
  merge floor512/숫자 index·doc_values/refresh 가시성은 유지한다.
- 잠금 회귀3건(복제본 배타성/독립 lock path/해제, timeout 시 타인 잠금 보존,
  8스레드 총512회 배타적 획득·해제) 통과. 전체 engine **864/864** (23.68초),
  concurrent refresh **7/7** (17.65초), merge **4/4** (3.86초), multi-field **9/9**
  (0.55초), node **646/646** (17.06초), binary **459/459** (22.27초) 통과했다.
  모두 serial, ignored/filtered0이다. 로그 SHA-256:
  `notified-lock-engine-tests.log` = `a52004bfb596569a289d89599a3d9fbebf5a358ceeeb0dfa38cf0a3c987f3993`;
  `notified-lock-node-binary-tests.log` = `94f8317f1a586d37c911978dabb123439aa8fe5328fcfd906615888a8e755c72`.
- 진단 예제는 `--notified-locks`로 동일 production 모듈을 포함한다. 같은 최적화
  실행 파일 SHA-256 `5b0873570674980eff3cadbf204edb8f971c72a557e80cb4a832fe836a692311`로
  기존/알림/알림/기존 순서4회 실행, 모두 정상 종료했다. 각 방식32개 대조 사례,
  8192개 refresh 단계 표본과 사례별2691문서 검증이 있다. 기존 방식의100ms 이상
  prepare64건/reload8건이 알림 방식에서는 각각0건이었다. 독립 진단에서의 관측이며
  전체 HTTP 지연 기여율, 무한 작업량의 보장 또는 정식 성능 통과를 의미하지 않는다.

숫자 index+fast 모두 활성, 현재 floor512의 모든 반복 결과(ms 누적):

| 실행 / 내부 반복 | prepare | commit 확정 | reload |
| --- | ---: | ---: | ---: |
| 00 기존 / 1 | 805.4947 | 33.7372 | 38.2001 |
| 00 기존 / 2 | 810.3723 | 35.2819 | 39.1502 |
| 01 알림 / 1 | 512.4908 | 32.4929 | 42.1129 |
| 01 알림 / 2 | 499.7215 | 37.5313 | 42.5302 |
| 02 알림 / 1 | 513.5981 | 31.1901 | 44.0466 |
| 02 알림 / 2 | 503.0008 | 37.6805 | 47.0521 |
| 03 기존 / 1 | 495.2711 | 35.4315 | 38.6346 |
| 03 기존 / 2 | 909.8824 | 31.5684 | 43.8935 |

- 기존03/1보다 알림 방식이 모든 항목에서 빠른 것은 아니다. 위 결과를 평균해
  고정 v0.6.0 예산과 비교하거나 좋은 반복만 선택하지 않는다. 모든 floor/대조군의
  원시 표본, segment 크기 및 final drain을 보존했다. 파일은
  `target/core-replacement-c05/refresh-commit-notification-` 접두사이며 SHA-256은:
  `00-before.jsonl` = `d38bc39042179eb7135e6b3413ddafbaff8058293339ce6b9b3c539f8940e8a0`;
  `01-after.jsonl` = `bcd476474065f3c91067c1506b5cd93a2ffa90155cb4e62c6c0e66d37e76ad49`;
  `02-after.jsonl` = `cee76452c568dd636c3daf391e4c6140eb3db6fc191a68cfeb0666e8eb1aeca1`;
  `03-before.jsonl` = `ee9705be947a115508ff3632e55ae21192c2939d662b5500e2100221f5d3fdbb`.
- source SHA-256: engine lib `aa7a897145f46a35bdda1c59b27a0f3f63a7d0c848896efd2d1fdce98dde657d`;
  refresh_directory `b979808d3328dce6393147c10a21faf416e76ab44a174405077f23b732cd484f`;
  example `d33ecd3c8ec12661d0091dd5914fcaffe1aaa94f6a8218d7a41ca061ce002962`.
- 다음 단계는 새 실제 서버 release build, live1804 호환성/count probe, 고정 v0.6.0와
  OpenSearch를 포함한 전체6회 반복 gate다. **아직 새 서버 빌드/live/전체 성능을
  실행하지 않았다.** `target/release/steelsearch`는 이전 bc56f6이며 이를
  `steelsearch-before-notified-lock-bc56f6f8`에도 보존하고 해시를 확인했다.
  정식 수락0/40, C02 미완료, 최신 정식 성능 bc56f6 FAIL, ledger 비어 있음,
  릴리즈 보류다. 이번 빌드/테스트/독립 진단은 모두 종료했고 태그/커밋/배포는 없다.

#### C02 RAM 잠금 알림 실제 서버 검증: 호환성 통과, 누적 성능 실패

- 2026-09-08: 직전 구현/독립 진단을 진척으로 확인하고 source hash 및 보존된
  bc56f6 후보를 재검증했다. 새 실제 서버 release build는 **4분50초**에 완료,
  SHA-256 `937e333fe012729fc9bc4e46e7d31558c2d6f1f0a7201846edb468572c88cf18`.
  `target/core-replacement-c05/notified-lock-release-build.log` SHA-256
  `4d5030c056614abe70b8c68b8e0795dcd8d8a109d04a2aee56116fa939376f6b`.
- `target/core-replacement-c05/live-notified-lock/execution.json`:
  **1804 passed / 0 failed / 0 skipped**, count probe 통과, failed_setup=[];
  실제 바이너리와 fixture 불변 확인. SHA-256
  `cba4418ba8e22e8a98c8bd765ec02a138bebfc1e179dc1befe3d01ef3fc5a358`.
  기능 참조 OpenSearch 3.7.0-SNAPSHOT과 성능 참조2.19는 계속 구분한다.
- `target/core-replacement-c05/notified-lock-repeated-full/` 전체 gate는
  기준선00/후보01/OpenSearch02/OpenSearch03/후보04/기준선05의6회,
  단일/3노드 총12개 구성 모두 정상 종료했다. 요청 오류0, 입력 검증true,
  실행 오류null, 소요1093.98초. **numeric_budget_passed=false**, gate 종료1이다.
  측정 중 코드 변경/빌드/추가 부하를 실행하지 않았다.

| 처리량 ops/s | 최초 v0.6.0 | 후보01 | 누적 저하 | 후보04 | 누적 저하 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 단일 노드 | 743.0111 | 711.4493 | 4.25% | 724.0241 | 2.56% |
| 3노드 | 931.3700 | 873.8066 | 6.18% | 886.5963 | 4.81% |

시나리오별 지연시간 누적 증가율(%), mean / p95 / p99 순서, 음수는 개선이다.

| 시나리오 | 후보01 | 후보04 |
| --- | ---: | ---: |
| 단일/write | 2.13 / 5.50 / 5.65 | 1.76 / 3.82 / 6.83 |
| 단일/lexical | 1.95 / 4.16 / -0.44 | 1.40 / 3.16 / -2.75 |
| 단일/ranking | 5.89 / 5.96 / -0.39 | 3.34 / 1.99 / -1.59 |
| 단일/facet | 5.12 / 6.02 / 2.01 | 4.17 / 4.16 / 0.32 |
| 단일/sort_filter | 7.03 / 6.33 / 6.15 | 4.49 / 2.34 / -2.34 |
| 단일/nested | 0.74 / 3.61 / 1.45 | -3.62 / -1.57 / -6.34 |
| 단일/refresh | 9.10 / -1.13 / -2.80 | 7.63 / -5.23 / -2.52 |
| 3노드/write | 4.23 / 6.26 / 7.75 | 3.23 / 4.93 / 5.01 |
| 3노드/lexical | 2.06 / 3.03 / 18.87 | 0.54 / 0.37 / 10.66 |
| 3노드/ranking | 6.80 / 9.12 / 11.91 | 4.74 / 5.07 / 12.84 |
| 3노드/facet | 6.34 / 9.26 / 17.20 | 4.83 / 8.02 / 12.81 |
| 3노드/sort_filter | 5.62 / 7.28 / 24.72 | 4.83 / 8.14 / 18.37 |
| 3노드/nested | 1.01 / 3.81 / 19.34 | 1.07 / 4.27 / 22.09 |
| 3노드/refresh | 21.65 / 19.07 / 18.20 | 17.86 / 16.67 / 14.15 |

- 공개 기준44개 지표 중 예산 이내는 **17/44**, **30/44**이고 같은 반복의
  새 기준선 대비는24/44,31/44다. 직전 bc56f6의21/44,29/44보다 전반적으로
  개선됐다고 주장하지 않는다. 독립 진단에서100ms 잠금 대기를 줄였지만 전체
  혼합 부하의 누적 성능 초과는 해소하지 못했다. 좋은 반복 선택/평균/상쇄는 없다.
- 기준선 drift: 실행00은 초과 없음, 실행05는3노드 nested p99 +7.787794% 초과.
  후보의 나머지 회귀를 기준선 변동으로 설명하지 않는다. 후보01 최대 초과는
  3노드 sort_filter p99 +24.720512%, 후보04는3노드 nested p99 +22.085982%다.
- 고정 OpenSearch2.19 처리량은02 단일279.9666/3노드115.9499,
  03 단일289.0914/3노드117.7533 ops/s다. 모든 시나리오별 원시값과 비교는
  summary 및 result의 checks[].published.opensearch_metrics에 있다.
  개발용 persistence/deferred-write 조건을 운영 내구성 동등성 증거로 사용하지 않는다.
- plan SHA-256 `7b94472ded1cb32c2ccb1c50c9dd89fbbd4b76be2db0999db8f80829aea73ba6`;
  result SHA-256 `78613c833b56f74998d23abfd53d04466a2448cec7d5682e22c190c379d60e80`.
- 다음 조사 지점: ensure_dynamic_mapping_for_value의 배열 순회는 이미 등록된
  숫자 배열에도 각 scalar마다 ensure_dynamic_scalar_mapping을 호출하고,
  후자는 매번 schema.fields.iter().any로 필드 이름을 선형 검색한다.
  현재384값 배열에는 불필요한 반복 탐색이 있지만, 이것의 CPU/HTTP 기여율은
  아직 입증하지 않았다. 기존 scalar 매핑의 반복 조회를 줄이되 nested array/object의
  새 하위 필드 탐색, null/빈 배열, dynamic=false 오류, 첫 scalar의 타입 선택 및
  매핑 변경에 따른 full refresh 무효화를 보존하는 회귀를 먼저 마련한다.
  개선 후 실제 서버 호환성과 전체 반복 gate를 다시 실행한다.
- 정식 수락 **0/40**, C02 normalizer/옵션/다중 필드 집계·조회 등은 미완료다.
  최신 정식 성능은 **937e333 후보 FAIL**이며 최적화 불가능성이 입증되지 않아
  제외 ledger는 비어 있다. 릴리즈 보류, 태그/커밋/배포 없음.
  이번 빌드/live/전체 성능 세션은 모두 종료했다.

#### C02 동적 scalar 배열 매핑 조회 최적화

- 2026-09-08: 직전 전체 gate는 요청 오류 없이 성능 예산 실패를 확인한 진척이다.
  다음 조사 지점의 코드를 재확인하고 ensure_dynamic_mapping_for_value의 배열
  처리에 배열 수명 내 scalar_mapping_known 상태를 추가했다. 첫 유효 scalar는
  기존 ensure_dynamic_scalar_mapping으로 처리하고 성공했을 때만 true로 바꾼다.
  이후 scalar는 같은 필드의 선형 검색을 반복하지 않는다. 재귀 처리는 매핑을
  추가할 뿐 제거하지 않으므로 이 상태는 배열 처리 동안 유효하다.
- 처음에는 배열 시작 시 선행 필드 조회를 했으나 최종 소스에서는 제거했다.
  빈 배열/null-only/객체-only 배열에 새 조회 비용을 추가하지 않는다.
  이미 등록된384개 숫자의 flat 배열은 필드 존재 검색384회 대신 첫 scalar의
  1회만 수행한다. 숫자 값 순회/색인/doc_values/원본/타입 변환을 생략하지 않는다.
  객체와 중첩 배열은 계속 재귀 탐색하고 오류는 원래 순서대로 전파한다.
  이 작업량 감소를 실제 HTTP 성능 개선률로 주장하지 않는다.
- 새 참조 비교 회귀는 변경 전 재귀/원소별 조회 알고리즘을 테스트 안에 보존했다.
  dynamic true/false, 초기 미매핑/숫자/텍스트/자식 매핑, null/정수/소수/문자열/bool/
  빈 배열·객체/중첩 배열·객체/keyword 이름 충돌의 **1936개 조합**을 비교한다.
  반환 changed 플래그, 오류 상태·내용, 오류 후 부분 상태까지 포함한 최종 스키마가
  일치했다. 이는 기존 동작 보존 검사이지 미완료 OpenSearch 매핑 계약의 완성 증거가 아니다.
- 별도 회귀는384값 배열의 최초 F64 매핑 생성/재호출 무변경을 검증하고,
  뒤에 추가된 중첩 객체의 values.new_child 및 .keyword 매핑 탐색을 검증했다.
  초기 집중2/2와 초기 전체 검증은 각각 dynamic-array-mapping-focused.log,
  dynamic-array-engine-full.log에 보존했으며 최종 lazy 상태로 전체 테스트를 다시 실행했다.
- 최종 source SHA-256
  `e00019a699513ddeb5dab9f2f8c6864dc6f9c0e8da90c72728ae1180167071af`.
  engine **866/866** (23.78초), concurrent refresh **7/7** (17.94초),
  merge **4/4** (3.82초), multi-field **9/9** (0.53초), node **646/646** (15.01초),
  binary **459/459** (22.71초), 총**1991건** 통과, 모두 serial/ignored0/filtered0.
  `target/core-replacement-c05/dynamic-array-lazy-engine-full.log` SHA-256
  `f6bf64bb4250e550c6c7f3fdd888501c17b61107341d03be4e4c834b6175a7fe`;
  `dynamic-array-node-binary-full.log` SHA-256
  `f85edf7f5193bb9a8be019db6e0af142f0c793093fce1fcf09d87f44e4618ad7`.
- 이전 실제 후보는 `steelsearch-before-dynamic-array-937e333f`에 보존했고
  SHA-256 `937e333fe012729fc9bc4e46e7d31558c2d6f1f0a7201846edb468572c88cf18` 확인.
  target/release/steelsearch도 아직 이 이전 후보다. 새 서버 release build,
  live1804/count probe, 고정 v0.6.0 및 OpenSearch 전체6회 반복 gate는 다음 필수 단계로
  남아 있다. 이 변경의 실제 성능 통과를 주장하거나 구현 단위를 완료 처리하지 않는다.
- 정식 수락0/40, C02 전체 범위 미완료, 최신 정식 성능937e333 FAIL,
  ledger 비어 있음, 릴리즈 보류를 유지한다. 최적화 불가능성이 입증되지 않았다.
  이번 테스트 세션은 모두 종료했고 태그/커밋/배포는 없다.

#### C02 동적 배열 실제 서버 검증 및 색인 워커 관측

- 2026-09-08: 최종 source e00019a6과 이전937e333 후보 보존을 재확인했다.
  실제 서버 release build는4분53초에 완료, 새 바이너리 SHA-256
  `b03643a4d23fb88015d455c2e9707e5a5e0d7d3051dfd498292a3277e13c9858`.
  `target/core-replacement-c05/dynamic-array-release-build.log` SHA-256
  `72741f7493c9a4197c4728088ddcfc2a08e0a3598d10dad08a1a225f25d11d62`.
- `target/core-replacement-c05/live-dynamic-array/execution.json`:
  **1804 passed / 0 failed / 0 skipped**, count probe 통과, failed_setup=[],
  바이너리/fixture 불변 확인. SHA-256
  `8ad9931f4490ff43af1fed1948efd4eeb2a6b6869824dccb85e35e8018cdb455`.
- `target/core-replacement-c05/dynamic-array-repeated-full/`: 기준선00/후보01/
  OpenSearch02/OpenSearch03/후보04/기준선05의6회, 단일/3노드 총12개 구성 모두
  정상 종료. 요청 오류0, 입력 검증true, 실행 오류null, 소요1093.12초.
  **numeric_budget_passed=false**, 종료1. 측정 중 소스 수정/빌드/추가 부하는 없었다.

| 처리량 ops/s | 최초 v0.6.0 | 후보01 | 누적 저하 | 후보04 | 누적 저하 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 단일 노드 | 743.0111 | 719.7294 | 3.13% | 727.0121 | 2.15% |
| 3노드 | 931.3700 | 882.4084 | 5.26% | 892.2579 | 4.20% |

시나리오별 지연시간 누적 증가율(%), mean / p95 / p99 순서, 음수는 개선이다.

| 시나리오 | 후보01 | 후보04 |
| --- | ---: | ---: |
| 단일/write | 1.66 / 4.42 / 3.66 | 0.64 / 2.64 / 4.71 |
| 단일/lexical | 1.90 / 3.29 / -1.40 | -0.04 / 0.34 / -2.66 |
| 단일/ranking | 5.13 / 5.04 / 0.77 | 3.98 / 5.11 / 3.75 |
| 단일/facet | 3.64 / 4.33 / 0.62 | 2.58 / 1.38 / 0.20 |
| 단일/sort_filter | 7.07 / 6.00 / 1.57 | 5.32 / 6.52 / 0.40 |
| 단일/nested | -3.95 / -4.51 / -5.85 | -3.34 / -2.84 / -8.88 |
| 단일/refresh | 8.89 / -4.66 / -1.41 | 7.85 / -2.22 / -0.81 |
| 3노드/write | 3.51 / 4.97 / 6.47 | 2.74 / 4.07 / 4.07 |
| 3노드/lexical | 0.98 / 1.23 / 10.81 | 0.40 / -0.10 / 7.65 |
| 3노드/ranking | 5.70 / 8.09 / 20.42 | 4.10 / 6.15 / 10.02 |
| 3노드/facet | 5.62 / 7.72 / 11.74 | 4.03 / 5.82 / 12.95 |
| 3노드/sort_filter | 5.06 / 8.79 / 16.26 | 4.14 / 7.09 / 11.33 |
| 3노드/nested | 0.87 / 2.15 / 8.93 | -0.28 / 1.52 / 9.92 |
| 3노드/refresh | 18.47 / 14.65 / 16.98 | 17.20 / 13.45 / 11.67 |

- 공개 기준44개 지표 중 예산 이내는 **23/44**, **29/44**이고 같은 반복의 새
  기준선 대비는29/44,37/44다. 직전937e333의17/44,30/44보다 모든 지표가
  개선됐다고 주장하지 않는다. 반복 평균/선택/반올림으로 예산을 통과시키지 않는다.
- 기준선 drift 초과: 실행00 단일 write p99 +6.708188%.
  실행05 단일 write p95 +7.085410%, p99 +8.503270%, ranking p99 +8.832177%,
  facet p95 +6.193650%, p99 +8.591213%, nested p95 +8.014948%, p99 +5.900209%,
  refresh p99 +8.264441%; 3노드 lexical p99 +13.761170%, ranking p99 +5.994009%,
  sort_filter p99 +5.641848%, nested p99 +18.514779%, refresh mean +5.326379%.
  이 변동으로 후보의 전체 회귀를 설명하지 않는다. 후보01 최대 초과는3노드
  ranking p99 +20.417681%, 후보04는3노드 refresh mean +17.197136%다.
- OpenSearch2.19 처리량은02 단일291.1746/3노드117.1385,
  03 단일289.1206/3노드115.5897 ops/s. 모든 시나리오 원본과 비교는 각 summary 및
  result의 checks[].published.opensearch_metrics에 있다. 기능 참조3.7.0-SNAPSHOT과
  구분하며 개발용 결과를 운영 내구성/클러스터 전역 검색 동등성 증거로 사용하지 않는다.
  plan SHA-256 `f625509f3f564b3c48e07a5dbedc9cb9ccdd752dd47dc4507e9c9ff695ba61a8`;
  result SHA-256 `18aa08a3ba10ab684998bf19332b4b4f8d863e555af3f6d3ad1e9e5fe7d744cd`.
- 전체 gate 종료 후 CPU 진단 도구에 `--cpu-frequency-hz`를 추가했다.
  기본49Hz 유지, 정수1-2000Hz 허용, futex의 비기본 주파수 지정 및 잘못된 값은
  실행 전 거부한다. 주파수와 한계를 보고서에 기록하고 소유 PID/실제 바이너리
  검증을 유지한다. CPU/refresh/gate 도구 회귀 **31/31 통과**.
  runner SHA-256 `9000abc8b2b6e8050f0d769acf260145c54006bd5a66c7fdaf317cf58d35156e`;
  test SHA-256 `ec66e8c3e9b0524f69154daa5dbc7eef07845907cc3b70d5827f5ca9b6b410bb`.
- 같은 b03643a 실제 서버에3노드 혼합45초 부하/20초 perf capture를997Hz와49Hz로
  순차 실행했다. 두 진단 모두 perf/matrix 종료0, 요청 오류0, 바이너리 불변.
  각 observation_seconds는28.10초/20.77초로 perf 시작·종료 처리까지 포함하므로
  프로세스 누적 CPU를 정확히20초 perf 표본과 동일 구간으로 취급하지 않는다.
  높은 주파수의 오버헤드와 짧은 워커 표본의 민감도 때문에 주파수 간 비중을
  성능 개선률/전체 지연 기여율로 변환하지 않는다. 부하 생성기 표본도 포함된다.
- 997Hz의 SegmentWriter::finalize inclusive8.48%, new_field self2.65%,
  FST Registry drop self1.23%, IndexMerger::write inclusive14.00%가 관측됐다.
  49Hz의 finalize inclusive는0.34%였다. inclusive 항목은 중첩되므로 합산하지 않는다.
  997Hz 보고서는 out-of-order event1 경고를 표시했으며 lost samples는0이었다.
  낮은 주파수의 표본 비중만으로 짧은 색인 워커 비용이 작다고 판단하지 않는다.
- 진단 경로는 `target/core-replacement-c05/dynamic-array-cpu-997hz/diagnostic.json`
  (SHA-256 `d72dcc694e5fb6e162031d7ce8c2db886755876aaea53ae32d8b0ff63bb2862d`),
  `dynamic-array-cpu-49hz/diagnostic.json`
  (SHA-256 `f8cf94b687c57b4d3d58012629399014a1a5ce6b05a78272df53e463d329ffb5`).
- 다음 실험 대상은 작은 refresh 세그먼트의 term dictionary 생성·해제 비용이다.
  로컬 tantivy-fst raw/build.rs의 Builder는 Registry::new(10000,2)를 호출하고,
  raw/registry.rs는20000개 RegistryCell을 vec 초기화한다. 새 필드의 고정 비용을
  실제 작은/큰 사전으로 분리 측정하고 검색 결과·사전 크기·메모리·병합 영향을
  검증한 뒤 변경 여부를 판단한다. 라이브러리/캐시 크기는 아직 변경하지 않았다.
- 정식 수락 **0/40**, C02 미완료, 최신 정식 성능 **b03643a FAIL**, ledger 비어 있음,
  릴리즈 보류를 유지한다. 최적화 불가능성은 입증되지 않았다.
  이번 빌드/live/전체 성능/추가 CPU 진단 세션은 모두 종료했고 태그/커밋/배포는 없다.

#### C02 term dictionary 생성 비용 기준 측정

- 2026-09-08: 직전 전체 gate/CPU 프로파일은 사전 생성·해제의 고정 비용으로
  조사 범위를 좁힌 진척이다. 이번에는 실제 서버/라이브러리/Cargo 의존성을 바꾸지
  않고 `examples/term_dictionary_diagnostic.rs`를 추가했다. 실제 Tantivy 공개
  TermDictionaryBuilder/TermDictionary를 사용하며 생성·삽입·finish를 분리 측정한다.
- GlobalAlloc을 통해 System 할당을 그대로 위임하면서 할당 횟수/요청 바이트/
  유지 payload 변화/추가 peak payload를 계측한다. 이는 단일 스레드 진단이며
  원자 카운터 비용을 포함한다. RSS/allocator 내부 메타데이터/재할당 중 내부 임시
  메모리는 측정하지 않는다. 서버의 mimalloc과 다르므로 HTTP 기여율이나 운영
  메모리 절감률로 환산하지 않는다. 키 생성·검증·JSON 보고서 생성은 단계 측정 밖이다.
- 첫 회귀는 가짜 posting 범위 사이 간격 때문에 실패했다. TermInfo 저장 형식이
  인접 시작 위치로 끝을 복원하는 계약에 맞게 연속 posting/position 범위로 고쳤다.
  수정 후 테스트1/1 통과(0.05초): 숫자 BE/공통 접두사/분산된 binary 키,
  각0/1/4/257항목에서 전체 get/term_ord/ord_to_term/순회/범위/없는 키를 검사했다.
  실패를 실제 엔진 회귀나 성능 결과로 취급하지 않는다.
- 최적화 예제 빌드1분25초 후, 항목 수0/1/4/16/64/384/1000/10000/100000과
  3개 키 모양을 정방향·역방향 순회해 **54개 조건, 2148회** 생성·검증을 완료했다.
  각 생성 결과의 모든 항목과 TermInfo를 확인했다. 프로세스 종료0.
  작은 사전은64회, 384/1000은16회, 10000은4회, 100000은2회 반복이다.
- 생성 단계의 요청량은 모든 조건/반복에서 **974360바이트**로 같았다.
  생성 단계 추가 peak payload는974352바이트였다. 이는 builder 전체 생성량이며
  전부를 FST Registry 한 구조체에 귀속시키지 않는다. 로컬 FST builder의
  Registry::new(10000,2), 20000셀 선행 초기화와 함께 고정 초기화 실험의 근거로 삼는다.

아래는 조건별 반복 평균 시간(마이크로초), 각 셀은 정방향 / 역방향 실행이다.
이는 독립 진단 요약이며 고정 v0.6.0 성능 gate의 평균 판정이 아니다.

| 키 모양 / 항목 수 | 생성 | 삽입 | finish | 사전 바이트 |
| --- | ---: | ---: | ---: | ---: |
| 숫자 / 4 | 39.40 / 39.75 | 0.41 / 0.43 | 24.73 / 24.97 | 138 |
| 접두사 / 4 | 39.77 / 39.82 | 2.91 / 2.82 | 29.83 / 29.08 | 165 |
| 분산 / 4 | 40.00 / 41.03 | 7.13 / 6.84 | 27.07 / 27.36 | 245 |
| 숫자 / 384 | 42.62 / 45.31 | 32.76 / 32.09 | 30.06 / 30.92 | 3148 |
| 접두사 / 384 | 41.48 / 43.77 | 243.93 / 243.42 | 33.03 / 32.95 | 1618 |
| 분산 / 384 | 46.05 / 45.65 | 922.39 / 911.12 | 326.72 / 320.52 | 14969 |
| 숫자 / 100000 | 122.04 / 126.08 | 6354.08 / 6312.76 | 94.88 / 122.72 | 369300 |
| 접두사 / 100000 | 221.70 / 133.40 | 64680.86 / 64024.50 | 120.20 / 127.14 | 365530 |
| 분산 / 100000 | 127.32 / 134.24 | 236342.36 / 234153.48 | 1821.36 / 1654.38 | 3705222 |

- 큰/분산 사전까지 초기화가 지배한다고 일반화하지 않는다. 전체 조건의 원시
  반복/할당/출력 크기는 `target/core-replacement-c05/term-dictionary-allocation-baseline.jsonl`
  에 보존했다(SHA-256 `9810c9bbb47573c86d355cb443216db9884ecb9f63e5c0064b547897105a9ef1`).
  예제 source SHA-256 `c8e74748149e1118cf912436b8f5218f3cbcb0044054429225443c1463134451`;
  실행 파일 SHA-256 `1dfdd9aab924ad57951aaf356d5ccec1caf5742195a3974887b126724dded675`.
- 다음 실험은 캐시 용량/해시/MRU 정책을 유지한 지연 초기화다. 캐시를 줄여
  압축률을 희생하기 전에 방문한 bucket만 초기화하는 방식의 생성·해제 비용을
  비교한다. 먼저 독립 실험 대상으로 격리하고 기존/수정 사전의 전체 byte 일치,
  작은/큰 사전의 조회/범위/ordinal, 요청 메모리와 생성·삽입·해제 시간을 확인한다.
  실제 의존성 채택은 이 근거를 검토한 뒤 결정하며, 채택 시 엔진/노드 회귀와
  live 호환성/전체6회 성능 gate를 다시 실행한다. Registry/Cargo 설정은 아직 그대로다.
- 실제 서버 SHA-256 `b03643a4d23fb88015d455c2e9707e5a5e0d7d3051dfd498292a3277e13c9858`
  불변 확인. 이번에는 진단 예제만 추가했으며 정식 수락0/40, C02 미완료,
  최신 정식 성능b03643a FAIL, ledger 비어 있음, 릴리즈 보류를 유지한다.
  테스트/빌드/진단 세션은 모두 종료했고 태그/커밋/배포는 없다.

#### C02 FST bucket 지연 초기화 독립 실험

- 2026-09-08: 진행 상태는 정식 수락 **0/40**이다. 현재 서버의 엔진/노드
  테스트1991개 및 live1804개 통과와 구현 단위의 전체 수락은 구분한다.
  최신 전체 gate는 b03643a FAIL이며 이번 독립 실험으로 갱신하지 않는다.
- `target/core-replacement-c05/fst-lazy-experiment/`에 upstream tantivy-fst0.4.0을
  라이선스와 함께 복사하고 별도 Cargo workspace/target으로 격리했다.
  루트 의존성이나 전역 Cargo registry는 수정하지 않았다. feature-off/on으로
  동일 진단 소스를 빌드했다. 기준본은 이번 실험의 원본 FST이지 v0.6.0 서버가 아니다.
- 캐시10000 bucket, bucket당2셀, 해시/MRU를 유지하되 셀의 capacity만 예약하고
  최초 방문한 bucket의 셀을 append한다. bucket별 offset 배열을 추가하므로
  초기화/해제는 줄어도 메모리 요청이 감소하는 설계는 아니다.
  크기0의 캐시는 기존처럼 Rejected를 반환한다. 이 경계의 독립 단위 테스트와
  충돌/MRU 세부 회귀는 아직 추가하지 않았으므로 전체 FST 검증 완료가 아니다.
- 진단 예제에 `--dictionary-output-dir PATH`를 추가했다. 각 조건 첫 반복의
  사전 bytes를 측정 밖에서 저장하며 기존 디렉터리/파일은 덮어쓰지 않는다.
  기존/수정/수정/기존 순서로 네 프로세스를 순차 실행했다. 각54조건/2148회,
  총8592개 사전의 모든 항목/TermInfo/ordinal/순회/범위/없는 키 검증 통과,
  네 프로세스 종료0. 조건별54파일은 세 번의 `diff -qr`에서 모두 완전 일치했다.
  수정 feature의 진단 단위 테스트도1/1 통과했다.
- 생성 요청량은 모든 조건에서974360 -> 1054360바이트, **80000바이트 증가**다.
  아래 시간은 생성+삽입+finish의 조건별 반복 평균(마이크로초), 각 셀은
  정방향/역방향이다. HTTP 처리량/지연 또는 RSS로 환산하지 않는다.

| 키 / 항목 수 | 기존00 | 수정01 | 수정02 | 기존03 |
| --- | ---: | ---: | ---: | ---: |
| 숫자 / 4 | 66.61 / 67.09 | 5.13 / 5.17 | 5.06 / 5.13 | 67.31 / 67.39 |
| 접두사 / 4 | 73.17 / 73.41 | 11.47 / 11.81 | 22.77 / 11.72 | 73.90 / 73.75 |
| 분산 / 4 | 76.75 / 76.45 | 13.53 / 13.87 | 14.19 / 13.97 | 76.01 / 75.67 |
| 숫자 / 384 | 107.08 / 107.58 | 50.90 / 39.38 | 41.47 / 39.41 | 108.72 / 108.63 |
| 접두사 / 384 | 318.37 / 319.21 | 249.46 / 246.90 | 246.52 / 252.44 | 320.04 / 320.35 |
| 분산 / 384 | 1303.04 / 1294.59 | 1045.79 / 1035.68 | 1055.38 / 1049.90 | 1299.21 / 1291.05 |
| 숫자 / 100000 | 6713.82 / 6665.78 | 6371.18 / 6381.82 | 6312.26 / 6306.68 | 6599.56 / 6647.36 |
| 접두사 / 100000 | 65089.48 / 65132.90 | 65151.78 / 64369.77 | 65262.04 / 64163.95 | 64964.56 / 64875.50 |
| 분산 / 100000 | 243571.33 / 239280.70 | 263504.60 / 252178.65 | 256402.19 / 257092.81 | 240176.29 / 237889.99 |

- 100000개 분산 키는 기존00의 같은 순회 조건 대비 수정01에서+8.18%/+5.39%,
  수정02에서+5.27%/+7.44% 느려졌다. 기존03 대비도 모두5% 초과다.
  10000개 분산 키 역방향은 수정01에서 기존00 대비+4.57%/기존03 대비+5.15%,
  수정02에서 각각+9.75%/+10.36%다. 좋은 작은 사전 결과로 이 회귀를 상쇄하지 않는다.
  나머지 조건도 원시 파일에 보존했으며 최선 반복 선택이나 percentile pooling은 없다.
- **현재 offset 방식은 서버에 채택하지 않는다.** 다음은 대형 분산 사전의
  삽입 경로에서 offset 간접 접근/분기/물리 셀 배치의 영향을 분리하고, 직접 bucket
  주소 접근을 유지하는 대안을 검토한다. 원인 귀속은 아직 가설이다. 추가 후보도
  같은 byte/조회/메모리/작은·큰 사전 검증을 거쳐야 하며, 실제 채택 시에는
  엔진/노드 회귀, live 호환성, 전체6회 gate를 다시 실행한다.
  독립 진단 회귀는 기능 한 단위의 HTTP5% 저하나 최적화 불가능성 증거가 아니므로
  ledger는 비어 있다. C02 미완료/릴리즈 보류를 유지한다.
- 원시 파일은 위 실험 디렉터리의 `00-baseline.jsonl`, `01-lazy.jsonl`,
  `02-lazy.jsonl`, `03-baseline.jsonl`이며 SHA-256은 순서대로:
  `46d293cfb87317f61ecca5c55564ebf84a266db75a4a652e630dbd86d9568954`,
  `254bbb2882e76c64f8830b0a03bb6e2121eee010e3ca498458d659b3b3be75b9`,
  `13dabe29481985944a370a8d8bbba0f1a60b5ea498c5e0bf6c49c48bdac3c452`,
  `b81789909c2da83e9f71d608847a13627ccc0656ee81f0f841cf3364688b83b3`.
  실행 파일 `baseline`/`lazy` SHA-256은 각각
  `cd82f9f74cf01afc04267507366f7246e587bd11e49dfeaf2eeb2805ff99316f`,
  `0d2a4ac2140970bdee7da8f06161bc6b3dd1b016b9e4ced43ae251938190e990`.
  진단 예제 source는 `4fbba3ff226a92af7358bdfe8f56a7b4580d0cc497bd70ebda3f5a2ccea25a45`,
  실험 Registry source는 `1ec80a6ebdc594af347405687421073f5397f3c90453ee9e2412886fcfcda7f1`.
  실제 서버는 `b03643a4d23fb88015d455c2e9707e5a5e0d7d3051dfd498292a3277e13c9858` 불변.
  이번 빌드/진단/테스트 세션은 모두 종료했고 태그/커밋/배포는 없다.

#### C02 FST 지연 초기화의 dense 전환 실험

- 2026-09-08: 앞선 offset 실험은 대형 분산 사전 회귀를 확인한 진척이다.
  같은 격리 디렉터리에서512개 bucket 방문 후 기존 직접 주소 배열로 전환하는
  후보를 추가했다. 기존 셀을 bucket/MRU 순서 그대로 swap 이동하며 unsafe는 없다.
  원래 offset source는 `registry-offset.rs`, 실행 파일은 `lazy`로 보존했다.
  새 후보 실행 파일은 `hybrid`다. 루트 서버/의존성 변경은 없다.
- 기존04/수정05/수정06/기존07 순서로 순차 실행했다. 각54조건/2148회,
  총8592개 사전의 전체 값/ordinal/순회/범위 검증 통과, 프로세스 모두 종료0.
  기존04의54개 출력 파일과 나머지 세 실행의 파일은 `diff -qr` 모두 종료0으로
  byte 일치했다. 아래는 생성+삽입+finish 반복 평균 마이크로초, 정방향/역방향이다.

| 키 / 항목 수 | 기존04 | 수정05 | 수정06 | 기존07 |
| --- | ---: | ---: | ---: | ---: |
| 숫자 / 4 | 66.68 / 65.91 | 5.30 / 5.12 | 5.10 / 4.95 | 67.55 / 65.20 |
| 숫자 / 384 | 107.48 / 108.04 | 41.22 / 40.20 | 41.24 / 40.37 | 108.57 / 107.74 |
| 분산 / 384 | 1297.37 / 1285.02 | 1643.90 / 1361.80 | 1569.74 / 1274.35 | 1301.09 / 1289.65 |
| 분산 / 100000 | 241712.23 / 238839.73 | 242338.78 / 243102.83 | 230060.72 / 227529.38 | 243209.27 / 239277.87 |

- 대형 사전만으로 성공 판정하지 않는다. 분산384 정방향은 기존04 대비
  수정05 +26.71%, 수정06 +20.99% 회귀했다. 분산64 정방향은 각각+131.81%/
  +130.10%, 역방향은+12.04%/+7.29%다. 분산1000 정방향도 수정05에서+10.98%,
  수정06에서+4.89%이며, 후자는 기존07 대비+6.21%다. 분산384 역방향 수정05도
  기존04 대비+5.97%다. 전환 비용이 작은·중간 사전의 새 회귀 지점이므로
  **dense 전환 후보도 서버에 채택하지 않는다.**
- 생성 요청량은 이전 offset 방식과 같은1054360바이트다. 분산384 삽입 단계의
  추가 peak payload는 기존535296 -> 수정1013120바이트다. 단계 시작 시점 대비
  계측값이며 전체 RSS가 아니다. 두 배열을 동시에 보유하는 전환 비용을 숨기지 않는다.
  원자 할당 카운터를 포함한 System 기반 독립 진단으로 HTTP gate와 구분한다.
- 실험 FST 자체 테스트는 처음 workspace 경계 오류, 다음 offline proptest 미확보로
  실행 전에 실패했다. 복사본에만 독립 workspace를 명시하고 개발 의존성을 내려받아
  해결했다. 루트 lock/manifest는 변경하지 않았다. 크기0 회귀와 전환 전후 캐시
  결과 비교를 추가했다. 후자는1/2/4셀 MRU에서20000회씩 접근하여 원본 dense
  참조와 hit/miss/address, 최종 모든 셀을 비교하고 실제 전환 발생도 확인한다.
  registry7/7 통과 후 **전체 FST unit123/123 통과**, 실패/skip/filter0, 5.09초.
  integration/doc tests 또는 실제 서버 전체 검증 완료로 확대하지 않는다.
- 다음 후보는 직접 bucket 주소를 유지하면서 전환/offset 간접 접근을 없애는
  지연 초기화다. 초기화 상태와 해제의 안전성, 메모리 및 전체 사전 검증이 필요하다.
  실제 채택 전 엔진/노드/live/전체6회 gate 조건은 그대로다. 이 실험만으로 기능
  한 단위의 HTTP 회귀와 최적화 불가능성이 입증되지 않아 ledger는 비어 있다.
- 증거 경로는 `target/core-replacement-c05/fst-lazy-experiment/`이며
  `04-baseline.jsonl` SHA-256 `8bb7e4b682fbeed40a4eb1a8013e2972034c19a5e3fc63795032824f1a5e62a5`,
  `05-hybrid.jsonl` `a32b42763b9407bf9fd5b2df91b20f9346adc5e1fc7fdcc53cdbb216efbd6687`,
  `06-hybrid.jsonl` `cf664baa6ca151af014020a4aa0e31974903dfe94fffdd5c2ddab6aa255cec15`,
  `07-baseline.jsonl` `d3016b81da9ea9a9b4bff19cc8783d9e5eac7e7ec5926b014c31eae829431958`.
  hybrid 실행 파일은 `037bac6b73ae4c3b76fd81e2252e7ca42fcf81382e07320b010e3c9c3b27a1bd`.
  측정 당시 Registry source는 `4b4f6765b78fb398c6bbeadd393c38d0df69dc24a1908dc1407569f9db7668f0`,
  테스트 추가 후 source는 `8b0d40f969f55b77e70e6c5481c325c072467e05c27438406a991298e316e84b`.
  테스트 로그는 `hybrid-registry-test-online.log`, `hybrid-fst-full-test.log`다.
- 서버 SHA-256 `b03643a4d23fb88015d455c2e9707e5a5e0d7d3051dfd498292a3277e13c9858` 불변.
  정식 수락0/40, C02 미완료, 최신 전체 gate FAIL, 릴리즈 보류다.
  이번 빌드/측정/테스트 세션 모두 종료했고 태그/커밋/배포는 없다.

#### C02 FST 직접 주소 지연 초기화 실험

- 2026-09-08: 이전 dense 전환 후보는 작은·중간 사전의 회귀를 확인한 진척이다.
  다음 후보는 `Vec<MaybeUninit<RegistryCell>>`의 고정 bucket 위치와 초기화 표시를
  사용한다. 방문한 row 전체를 초기화한 뒤에만 RegistryCell slice로 접근하고,
  Drop은 표시가 있는 row만 해제한다. offset/전환 복사는 없다. 캐시 용량/해시/MRU는
  그대로다. unsafe slice 변환과 assume_init_drop의 불변식을 코드에 명시했다.
  기본 빈 셀 생성은 빈 Vec와 스칼라만 사용한다. 복사본에서만 실험 중이며
  서버 의존성에 채택하지 않았다. 이전 source는 `registry-hybrid.rs`로 보존했다.
- 전체 FST unit123/123 통과(5.72초), 실패/skip/filter0. 캐시 결과 비교는
  lazy와 미리 초기화한 참조를1/2/4셀에서 각각20000회 비교하고 마지막에는
  전체 셀을 비교한다. 단위 테스트 통과가 모든 unsafe 실행의 안전성 증명은 아니다.
- 기존08/수정09/수정10/기존11 순서로 각54조건/2148회, 총8592개 사전을 검증했다.
  네 프로세스 종료0, 모든 조회/TermInfo/ordinal/순회/범위 검증 통과.
  조건별54개 출력 파일도 기존08과 나머지 세 실행에서 byte 일치했다.
  아래 시간은 생성+삽입+finish 평균 마이크로초이며 정방향/역방향 순서다.

| 키 / 항목 수 | 기존08 | 수정09 | 수정10 | 기존11 |
| --- | ---: | ---: | ---: | ---: |
| 숫자 / 4 | 66.49 / 60.27 | 10.73 / 10.54 | 10.66 / 10.68 | 67.96 / 59.70 |
| 숫자 / 384 | 100.68 / 99.99 | 44.63 / 44.69 | 45.26 / 45.22 | 138.96 / 100.02 |
| 분산 / 384 | 1220.76 / 1217.04 | 1217.11 / 1219.48 | 1285.41 / 1291.74 | 1307.16 / 1226.64 |
| 분산 / 100000 | 226068.69 / 223014.36 | 227520.00 / 224573.56 | 242274.31 / 238563.63 | 224463.23 / 224216.55 |

- 생성 요청량은974360 ->984360바이트로10000바이트 증가다. 작은 사전 개선만으로
  채택하지 않는다. 수정10의 분산100000은 기존08 대비+7.17%/+6.97%, 기존11 대비
  +7.93%/+6.40%다. 분산1000도 기존08 대비+8.53%/+7.32%, 분산10000은+6.86%/
  +9.99%, 분산384는+5.30%/+6.14%다. 수정09에서는 두 기준 실행 대비5% 초과
  조건이 없었으나 이를 선택해 수정10의 회귀를 삭제하지 않는다.
  다음 비교는 한 CPU에 고정해 스케줄링 이동 영향을 줄이는 독립 진단이다.
  환경 변동이 원인이라고 확정하지 않았으며 기존 실패를 면제하지 않는다.
- 실험 경로는 `target/core-replacement-c05/fst-lazy-experiment/`다.
  direct 실행 파일 SHA-256 `d28b9ccaf95413697858074ccbd79d49c8564283575275a97a8bc884c8636f20`,
  Registry source `9f332316ba58f1f37d9b63e5c8da789ac6d3e6ad4bdf47019c4f95f37146b3f0`.
  원시 결과 SHA-256은 `08-baseline.jsonl`
  `6c8769799530e1c87f72202c53df4899a1e73181fd4a2141ff8b7b8ad789a82d`,
  `09-direct.jsonl` `aa80e713af6a9b85e5282a12e77cd02d16d33302db7a386f3a9aa83d724157b9`,
  `10-direct.jsonl` `834451dd35b6ea20bb88d54371639c9aa523d2177268935b56290f8b8ca7e6f1`,
  `11-baseline.jsonl` `92018fe7063cae5e4ce1728f7e2370c12fb5fbcce315935f493c3d0b45897181`.
- Miri/rust-src를 nightly에 설치하고 strict provenance로 registry7/7 검사를
  완료했다(301.89초, 실패/skip0, 나머지116개는 filter). 접근/해제/캐시 비교를
  포함한 해당 실행에서 오류가 없었으며 모든 unsafe 경로의 형식 증명은 아니다.
  로그 `direct-miri.log` SHA-256은
  `54f49fe86749fdc03b03fafbbeff36f10543866b44252f731fd68251c6f5991e`다.
- Miri 종료 후 CPU1에 `taskset -c 1`로 고정해 기존12/수정13/수정14/기존15를
  순차 실행했다. 이전 바이너리 그대로, 각54조건/2148회 검증과 프로세스 종료0,
  기존12와 세 실행의54개 사전 파일도 byte 일치했다. CPU affinity를 추가한
  독립 실험이므로 비고정 실행의 실패를 대체하지 않는다. 두 수정 실행 각각의
  모든54조건을 두 기준 실행의 같은 조건과 비교한216개 생성+삽입+finish 평균
  비교에서5% 초과는0개였다. 전체 HTTP gate 통과를 뜻하지 않는다.

| 키 / 항목 수 | 기존12 | 수정13 | 수정14 | 기존15 |
| --- | ---: | ---: | ---: | ---: |
| 숫자 / 4 | 65.69 / 66.69 | 10.53 / 10.28 | 10.50 / 10.85 | 66.28 / 66.29 |
| 숫자 / 384 | 128.88 / 109.49 | 47.77 / 45.17 | 47.78 / 44.83 | 127.29 / 108.47 |
| 분산 / 384 | 1541.78 / 1284.49 | 1283.96 / 1264.24 | 1263.98 / 1280.47 | 1288.23 / 1304.79 |
| 분산 / 100000 | 240940.95 / 238324.11 | 241943.88 / 237811.57 | 240222.61 / 236672.57 | 240091.17 / 239807.88 |

- 위 표도 마이크로초/정방향·역방향이다. CPU 고정이 비고정 회귀의 원인을
  확정하지는 않는다. 다음은 기존 `refresh_commit_diagnostic.rs`를 격리 workspace의
  기존/수정 FST에 연결하여 실제 refresh/merge/reader/정확한 문서값 검증과
  시간·메모리 영향을 비교한다. 서버 반영 여부는 그 결과와 추가 안전성 검토 후
  판단한다. 반영 시 엔진/노드/live와 전체6회 HTTP gate를 반드시 재실행한다.
- CPU 고정 원시 파일 SHA-256은 `12-pinned-baseline.jsonl`
  `02616e61a3134f491beac1b2ec1e23c85236381cb0aa7e558900c00bc8f9790c`,
  `13-pinned-direct.jsonl` `4ec070e2d5088fa5593b1ce602a33d81e8001b7f1e3e98f40dadb9946a6c55ad`,
  `14-pinned-direct.jsonl` `39ee04cd12e0e2f4e4f42f1243d567c4febe6a54cd5a7ad3054f7827d842380a`,
  `15-pinned-baseline.jsonl` `d4e98e3976a76e6dd80df54ef81e01a9d1783a9792feaa2886c502b38b3b0673`.
  정식 수락0/40, C02 미완료, 최신 서버 전체 gate FAIL, ledger 비어 있음,
  릴리즈 보류다. 서버와 루트 의존성은 변경하지 않았다.
  서버 SHA-256 `b03643a4d23fb88015d455c2e9707e5a5e0d7d3051dfd498292a3277e13c9858`
  불변 확인. 이번 설치/빌드/테스트/측정 세션은 모두 종료했고 태그/커밋/배포는 없다.

#### C02 FST 직접 주소 방식의 refresh/merge 진단

- 2026-09-08: 직전 직접 주소 방식의 Miri/CPU 고정 진단은 실제 refresh 경로
  검증으로 넘어갈 근거를 확보한 진척이다. 같은 격리 Cargo workspace에 기존
  `refresh_commit_diagnostic.rs`를 `refresh-experiment` bin으로 연결했다.
  feature-off 기준본과 feature-on 후보를 각각 빌드/보존했다. 루트 서버나
  의존성은 여전히 변경하지 않았으며 독립 진단이지 정식 구현 수락이 아니다.
- 최초 실행은 `/usr/bin/time` 부재로 프로세스 시작 전에 종료127이었다.
  이를 결과로 사용하지 않았다. 별도 `run_refresh.py`가 새 디렉터리를 만들고
  stdout/stderr, 종료 코드, 실행 전후 SHA-256, child CPU/max RSS를 기록한다.
  같은 디렉터리를 덮어쓰지 않는다. max RSS는 Linux 프로세스 전체 최고값으로
  모든 조건과 검증을 포함하며 개별 조건/운영 서버 메모리가 아니다.
- 기준00/수정01/수정02/기준03을 순차 실행, CPU affinity는 제한하지 않았다.
  모두 `--notified-locks`로 현재 서버의 알림형 RAM 잠금을 사용했다.
  각16조건/4096 refresh, 총64조건/16384 refresh, 프로세스 모두 종료0이고
  실행 파일 해시는 전후 일치했다. 각 조건의 최종2691개 문서 ID/중복/누락,
  fast field 값(활성 조건), indexed term의 예상 문서 수(활성 조건),
  이전 reader1667개 유지와 merge drain 후 전체 문서 검증을 통과했다.
- 아래는 현재 서버와 같은 min_layer_size512, indexed=true, fast=true의
  두 독립 관측이다. 시간은 add+prepare+publish+reload의 마이크로초이며
  percentile은 각256개 표본의 nearest rank다. 반복을 합치거나 최선값을 고르지 않는다.
  원시16조건 모두 보존하며 필드 비활성 조건은 성능 후보가 아닌 분석 대조군이다.

| 실행 | 첫 관측 mean / p95 / p99 | 둘째 관측 mean / p95 / p99 | 프로세스 max RSS KiB |
| --- | ---: | ---: | ---: |
| 기준00 | 2354.47 / 3913.76 / 5321.45 | 2311.99 / 3718.04 / 5529.37 | 220232 |
| 수정01 | 2222.92 / 3659.36 / 5466.85 | 2197.71 / 3143.83 / 6699.06 | 187836 |
| 수정02 | 2175.88 / 3257.31 / 4378.68 | 2181.34 / 2893.39 / 4749.89 | 179652 |
| 기준03 | 2298.16 / 3132.59 / 5819.34 | 2340.65 / 3323.19 / 4760.21 | 202508 |

- 평균 시간은 양쪽 기준보다 작지만 수정01의 둘째 관측 p99는5529.37 ->
  6699.06으로 악화했다(기준03의4760.21 대비로도 악화). 첫 관측 p95도 기준03
  대비 악화다. floor10000의 indexed/fast 활성 첫 관측 평균은 기준00 2623.30,
  수정01 2725.66, 수정02 2757.28, 기준03 2658.71이다. tail/조건별 회귀를
  평균 개선이나 RSS 관측으로 면제하지 않는다. 전체 검증 제외 시간과
  마지막 merge drain은 원시 자료에 별도 남아 있어 시간 합산 시 구분해야 한다.
- **최적화 합격이나 서버 채택 확정이 아니다.** 작은 필드 생성 비용과 현재
  refresh 평균의 개선 근거가 확보됐으므로 다음은 별도 재현 가능한 실제 서버
  후보 빌드/엔진·노드 회귀/live/전체6회 gate에서 검증한다. root lock/cache가
  기존 서버/기준선과 혼입되지 않도록 실제 의존성과 소스·실행 파일 출처를 기록한다.
  비고정 사전 회귀와 이번 tail 회귀는 미해결 관측으로 유지한다.
- 증거 디렉터리는 `target/core-replacement-c05/fst-lazy-experiment/`다.
  기준/수정 refresh 실행 파일 SHA-256은 각각
  `144e9313caae60a1ad05741261f486def44cb2947a7a8b812e16972f3326bf23`,
  `535bdd0d3e37c68f0b77ea576b2704a40e1e07af86944ef5b7df894727d5030f`.
  `refresh-00-baseline/raw.jsonl` SHA-256
  `25e6c30bd539bf0c0ce3842997cb558d2765a3066beebc4a181e60c08c0d3ce6`,
  `refresh-01-direct/raw.jsonl` `95e5193f99f1b2ab46d57c742dd8a2ec8de07627ae1f933d9a67690d89c0872c`,
  `refresh-02-direct/raw.jsonl` `78058bdab209c85b90f261f4aa4ed46de974e8c81de67d26007316cf6c339ed5`,
  `refresh-03-baseline/raw.jsonl` `176587b1fbf0fc8073bc1722aadf9f7c2af17bdd7a549dc919bd92003738a7d0`.
  각 디렉터리의 execution.json에 CPU/RSS/시간/종료/바이너리 출처를 보존했다.
  refresh 예제 source는 `d33ecd3c8ec12661d0091dd5914fcaffe1aaa94f6a8218d7a41ca061ce002962`,
  run_refresh.py는 `fd52d2027e500c590dab24f486bf6e42ef314bf7c1f4e58f452daf5cc591632f`다.
- 서버 SHA-256 `b03643a4d23fb88015d455c2e9707e5a5e0d7d3051dfd498292a3277e13c9858` 불변.
  정식 수락0/40, C02 미완료, 최신 전체 gate FAIL, ledger 비어 있음, 릴리즈 보류다.
  단일 기능의 최적화 불가능성은 입증되지 않았다. 이번 빌드/진단 세션은 모두
  종료했고 태그/커밋/배포는 없다.

#### C02 FST 직접 주소 실제 서버 후보 빌드와 엔진/live 검증

- 2026-09-08: 직전 refresh/merge 실험은 실제 서버 후보를 검증할 근거를 확보한
  진척이다. `target/core-replacement-c05/fst-server-candidate/`에 현재 Cargo 파일,
  crates/docs/tools/fixtures/scripts를 복제했다. 원본/복제본의 모든 해당 일반 파일을
  `source-original.sha256`으로 확인했고 서버 빌드 후에도 양쪽 일치를 재확인했다.
  이 문서의 후속 journal 추가 이전 시점의 스냅샷이다. 원본 작업 파일을 되돌리거나
  기존 서버/기준선 캐시를 재사용하지 않았다.
- 복제본에만 `vendor/tantivy-fst`와 crates.io patch를 추가하고 lazy-registry를
  default feature로 활성화했다. 기존 실험의 라이선스/소스를 보존했다.
  lock 변경은 tantivy-fst0.4.0의 registry source/checksum을 로컬 path로 바꾼
  한 항목뿐이며 다른 버전은 변경되지 않았다. Cargo fingerprint에서도
  `["default", "lazy-registry"]` 활성화를 확인했다. 플러그인 관련 기존 크레이트가
  의존성으로 빌드되지만 플러그인 지원 범위/수락에는 포함하지 않는다.
- 새 `build/` 디렉터리, `RUSTFLAGS=-Awarnings`, `CARGO_BUILD_JOBS=2`,
  `CARGO_INCREMENTAL=0`, nightly rustc1.97.0(ad3a598ca, 2026-05-03),
  thin LTO/codegen-units1 release로 실제 standalone-runtime 서버 빌드 완료(7분49초).
  실행 파일은 `build/release/steelsearch`, SHA-256
  **`dada63998f5a59053255c10bfec1189fa52454edc689ec1ab1f2058f6057077b`**.
  원본 `target/release/steelsearch` b03643a 및 최초 v0.6.0 db244133은 불변이다.
- 같은 후보 의존성에서 `--locked --release -p os-engine-tantivy --lib
  --test concurrent_refresh --test merge_policy --test multi_field_values
  -- --test-threads=1`을 실행했다. 테스트 실행 파일 최적화 빌드15분39초 후
  unit866/866(5.36초), concurrent7/7(5.26초), merge4/4(0.75초),
  multi-field9/9(0.11초), **총886/886 통과**, 실패/skip/filter0, 명령 종료0.
  테스트 후에도 실제 서버 실행 파일 해시 불변을 확인했다.
- 같은 dada6399 서버로 기존 full projected core와 추가 계약 fixture 전체 및
  count probe를 live 실행했다. OpenSearch 기능 참조3.7.0-SNAPSHOT에 대해
  **1804/1804 통과**, 실패/skip0, failed_setup 전부 빈 배열, 모든 실행 종료0,
  count probe true, binary_unchanged/fixtures_unchanged true다.
  기존 b03643a의 통과 기록을 새 후보에 재사용한 것이 아니다.
- 출처: 복제본 `source-original.sha256` 해시
  `4266c4566f138715b600c348c6e19c5d2969b59055f7d5426627ba8c65703f70`;
  복제본 Cargo.toml `dc834bb19e95325468a2507b3d99d422ac5ab58fd89af1797b05e287a4a67e8d`,
  Cargo.lock `02468eb6f05b3ca9456093d2ddfd2a9d7f3f921e35c71587daa82efe569a749c`;
  vendor Registry `9f332316ba58f1f37d9b63e5c8da789ac6d3e6ad4bdf47019c4f95f37146b3f0`,
  vendor Cargo.toml `5ce901915e07086a0978385f1c2e1423ff88ef195171ca40b5fbc75b4059df13`.
  원본 Cargo.toml `a233b8cc4c915f51b17725f2b4c6e5a898289c0f0efcf9909082a10f6b9dea83`,
  Cargo.lock `bb8e02a8d2110232050e66273235393950042613af9541bb9795099736a001f2` 불변.
  후보 `candidate-build.log`는
  `b87bf4efbcddc029f5948226a8f0f2519203b2a0cfd858ffa2299293c7484a0c`,
  `candidate-engine-tests.log`는
  `7770c975162ea449dbc88891b221af98f90a330ac869451199e8948eec072c5c`다.
  live는 `target/core-replacement-c05/live-fst-direct/execution.json`, SHA-256
  `9c01b3f03c637236f49f3e30b9e8f15ae0392370a1b3770c72915c98cb852881`이다.
- **남은 필수 검증:** 후보의 node lib/steelsearch bin unit 회귀, 실제 후보를
  지정한 전체6회 성능 gate. 독립 FST/refresh의 비고정·tail 회귀도 미해결 관측이다.
  이후 gate에는 baseline `target/core-replacement-s01/baseline/steelsearch`,
  candidate `target/core-replacement-c05/fst-server-candidate/build/release/steelsearch`
  를 명시하며 원본 b03643a를 후보로 잘못 선택하지 않는다. 새 결과 디렉터리를 사용한다.
  측정 중 코드 변경/빌드/다른 부하는 금지한다. 통과 전 루트 의존성 채택이나
  C02 완료로 간주하지 않는다. 정식 수락0/40, C02 미완료, 최신 전체 gate는
  여전히 b03643a FAIL이며 dada6399의 정식 성능은 아직 미측정이다.
  ledger는 비어 있고 릴리즈 보류다. 이번 빌드/테스트/live 세션은 모두 종료했으며
  태그/커밋/배포는 없다.

#### C02 dada6399 노드 검증과 전체 성능 gate

- 2026-09-08: 직전 후보 빌드/엔진886/live1804 통과는 새 실행 파일을 검증한
  진척이다. 이어 같은 복제본에서 node lib/steelsearch bin 테스트를 직렬 실행했다.
  `RUSTFLAGS=-Awarnings`, jobs2/incremental0, debug 심볼0인 비최적화 test
  프로파일을 사용했다. unit 테스트와 성능 바이너리의 프로파일은 구분한다.
  빌드2분34초 후 lib646/646(11.64초), bin459/459(17.49초) 통과,
  실패/skip/filter0. 앞선 엔진과 합쳐1991개 통과다. 소스 manifest 재검증과
  실제 release 서버 dada6399 해시 불변도 확인했다.
  `candidate-node-tests.log` SHA-256은
  `f3384cd76379ca05f7890c74157de1b87cc26ba04c9867c8b70bf895ddbc30e3`이다.
- `tools/run_core_performance_gate.py`에 최초 v0.6.0 db244133과 복제본 release
  dada6399를 명시하고 전체6회를 실행했다. 순서는 baseline00/candidate01/
  OpenSearch02/OpenSearch03/candidate04/baseline05, 각 단일/3노드60초,
  문서5000/숫자384/클라이언트4/샤드3/replica0 또는1/seed13/timeout10,
  혼합 write15/lexical15/ranking15/facet15/sort_filter10/nested10/refresh5다.
  기존 dev persistence/sync0/deferred native writes1 프로파일을 유지했다.
  부하 중 빌드/테스트/코드 변경은 없었다.
- **결과 FAIL**: 1094.57초,6실행 모두 종료0,12토폴로지 요청 오류0,
  execution_inputs_verified=true, error=null, numeric_budget_passed=false.
  후보01은 공개 v0.6.0 기준41/44, 같은 실행의 기준00 대비41/44가 예산 내다.
  후보04는 공개 기준40/44, 같은 실행의 기준05 대비43/44다. 둘 다 실패다.
  이전 b03643a의23/44·29/44보다 예산 내 지표가 늘었지만 다른 측정 간 비교이며
  FST 하나의 정확한 기여율이나 구현 완료율로 환산하지 않는다.

| 후보 실행 | 단일 처리량 req/s / v0.6.0 대비 | 3노드 처리량 req/s / v0.6.0 대비 | OpenSearch 단일 / 3노드 req/s |
| --- | ---: | ---: | ---: |
| 01 | 747.6846 / +0.6290% | 908.7472 / -2.4290% | 279.9376 / 116.2431 |
| 04 | 743.4461 / +0.0585% | 906.8131 / -2.6366% | 275.3284 / 116.5944 |

아래는 공개 최초 v0.6.0 대비 지연 변화율(%), mean/p95/p99 순서다.
양수는 악화이며 처리량 개선으로 상쇄하지 않는다. 원시 정밀도로 판정한다.

| 토폴로지 / 시나리오 | 후보01 | 후보04 |
| --- | ---: | ---: |
| 단일 / write | -0.29 / +0.46 / +1.69 | +2.27 / +3.43 / -1.50 |
| 단일 / lexical | -3.57 / -9.45 / -15.61 | -2.46 / -8.08 / -14.48 |
| 단일 / ranking | +1.74 / -2.97 / -6.85 | +1.14 / -3.54 / -7.22 |
| 단일 / facet | +1.78 / +1.54 / -1.09 | +1.17 / +0.78 / -3.34 |
| 단일 / sort_filter | +3.00 / -1.82 / -6.93 | +3.66 / -2.93 / -9.39 |
| 단일 / nested | -5.61 / -8.04 / -16.12 | -3.34 / -5.27 / -12.18 |
| 단일 / refresh | -5.54 / -14.63 / -9.75 | -4.79 / -12.45 / -13.19 |
| 3노드 / write | +3.32 / +5.72 / +2.26 | +2.79 / +4.13 / +2.19 |
| 3노드 / lexical | -0.04 / +0.11 / -1.95 | +0.20 / +1.51 / -1.12 |
| 3노드 / ranking | +4.69 / +5.32 / +5.58 | +4.69 / +4.90 / +5.94 |
| 3노드 / facet | +4.58 / +3.83 / +3.07 | +4.23 / +5.03 / +4.78 |
| 3노드 / sort_filter | +2.06 / +3.06 / -5.23 | +3.82 / +6.77 / +4.42 |
| 3노드 / nested | +0.66 / -0.14 / +0.59 | +0.35 / +0.00 / -0.10 |
| 3노드 / refresh | -0.00 / +0.50 / -0.06 | +1.53 / +3.04 / +8.39 |

- 공개 기준 초과: 후보01의3노드 write p95+5.718658%, ranking p95+5.318305%,
  ranking p99+5.580135%. 후보04는 ranking p99+5.935425%, facet p95+5.028909%,
  sort_filter p95+6.771605%, refresh p99+8.389184%다. 가장 큰 refresh p99는
  기준22.04181ms ->23.89094ms로, 허용23.14390ms를 초과했다.
- 같은 실행의 기준 대비 후보01 초과는 write p95+6.011145%, ranking p95+5.677023%,
  ranking p99+6.872725%. 후보04는 refresh p99+11.967759%만 초과했다.
  기준00 drift는 초과0개, 기준05는3노드 ranking p99+5.069339%가 초과했다.
  기준선 변동을 기록하되 후보의 모든 회귀를 환경 탓으로 면제하지 않는다.
- OpenSearch 처리량 비율은 후보01 단일2.6709배/3노드7.8176배,
  후보04 단일2.7002배/3노드7.7775배다. 참조는 고정된 OpenSearch2.19 이미지이며
  모든 시나리오 mean/p95/p99 원시 값은 result.json의 opensearch_metrics에 보존했다.
  이 dev 부하의 결과이지 운영 내구성/전역 검색 의미가 같은 서비스의 배수 주장이 아니다.
- 성능 증거 `target/core-replacement-c05/fst-direct-repeated-full/plan.json`
  SHA-256 `6828c21017623ce62b92c26e8ceaff916089f4377adcfb69602d86194eb8e1fb`,
  `result.json` `f1028d20ae558a39c3df24a7635adb09df0e2273a306d9b338f945e094dcdab4`.
- 전체 gate 종료 후 dada6399의3노드 혼합 부하45초에서 CPU997Hz 진단을 별도
  실행했다. perf/matrix 종료0, 요청 오류0, 바이너리 전후 일치, 표본 약35K,
  lost samples0. 명령상20초 capture의 전후 관측28.46초에는 시작/종료/flush 비용이
  포함되며 gate 성능이나 다른 주파수 대비 속도 향상 근거로 사용하지 않는다.
  new_field inclusive0.20%/self0.02%, FST Registry drop0.53%/0.45%,
  SegmentWriter::finalize5.08%/1.58%, IndexMerger::write13.69%/1.23%,
  write_fast_fields inclusive6.44%, simple bucket aggregation4.54%/2.38%,
  tokio worker memcmp4.20%/4.16%가 관측됐다. 분모에는 부하 생성기 표본도 포함된다.
- memcmp caller 보고서에서 집계 경로1.49%, BM25 scoring -> document_matches_query
  -> source_value_for_highlight_field 경로0.61%가 관측됐다. 원인 확정이 아니라
  다음 조사 지점이다. 후보 source의 해당 필드 조회(22256행)는 JSON object.get과
  dotted path 순회를 사용한다. 다음에는 점수 계산/집계에서 중복 조회 횟수와
  조회 재사용 가능성을 확인하고, source 의미·다중 필드·배열·nested·정밀도 계약을
  유지하는 최적화만 검토한다. 병합 비용과 refresh tail도 따로 유지한다.
  초기 perf 보고서의 head 파이프는 SIGPIPE141로 끝났으나 capture 실패가 아니며,
  전체 입력을 소비하는 필터와 caller 보고서는 종료0으로 재확인했다.
  CPU 증거 `target/core-replacement-c05/fst-direct-cpu-997hz/diagnostic.json`
  SHA-256 `64be56c1443f10527e4f230e8b9a9f6314bdabed96d7ce795cca48b03f2f5537`.
- 정식 수락0/40, C02 미완료, **최신 실제 후보 전체 성능 dada6399 FAIL**이다.
  루트 서버는b03643a, 루트 의존성은 불변이며 dada6399는 별도 실험 후보로 보존한다.
  단일 기능의5% 이상 저하 귀속/최적화 불가능성은 입증되지 않아 ledger는 비어 있다.
  기능 제외/예산 완화/기준선 재설정/릴리즈 승인으로 해석하지 않는다.
  이번 노드 테스트/전체 성능/CPU 진단 세션은 모두 종료했고 태그/커밋/배포는 없다.

#### C02 날짜 집계 설정 준비와 C06 자원 제어 위험

- 2026-09-08~09: 직전 dada6399 전체 gate/CPU 진단은 남은 회귀 경로를 좁힌 진척이다.
  bool should 임시 Vec 제거를 다시 검토했지만, release-diagnostic-2026-09-06.md의
  기각 기록을 확인하여 재적용하지 않았다. 실제 새 변경은 날짜 집계에 한정한다.
- 루트 engine source에 PreparedDateHistogramRounding을 추가했다. interval 정규화,
  시간대 해석, 고정 간격 선택을 simple bucket 집계 요청의 상태 준비 시 한 번 수행하고
  문서별 계산은 준비된 값을 재사용한다. 일반 날짜 집계 함수도 같은 반올림 계산을
  사용한다. checked 연산, offset 처리, 음수 시간, 주/월/년 계산은 기존대로 유지한다.
  invalid timezone은 기존처럼 유효한 bucket을 만들지 않으며 이를 지원 완료로
  해석하지 않는다. 이 변경은 FST 복제본이나 기존 실행 파일에 아직 반영하지 않았다.
- 최초 경계값 테스트 포함 날짜 집계28개는 통과했다. 추가한 일반 집계와의 비교
  테스트는1969년부터2024년까지의 문서를 한 번에 넣고 기본 min_doc_count0으로
  분 단위 빈 버킷을 생성하여 메모리가 과도하게 증가했다. 전체 테스트를 통과했다고
  기록하지 않는다. 커널은2026-09-08 16:41:22 UTC에 테스트 PID2781364를 global OOM으로
  종료했다고 기록했다(anon-rss14962796KiB). 서비스 HTTP 경로가 아니라 내부 collector
  unit 테스트에서 발생한 사건이다. 메모리 무제한 대규모 재현은 반복하지 않는다.
  증거: `target/core-replacement-c05/prepared-date-histogram-engine-full.log`,
  `prepared-date-histogram-oom-evidence.log`.
- 재개 시 해당 프로세스 부재와 메모리 회복을 확인했다. min_doc_count1로 바꾼
  첫 수정도 빈 구간을 순회하여 지나치게 오래 걸렸다. 코드에서 날짜별 while 루프가
  마지막 doc_count 필터 전 모든 빈 구간을 방문하는 것을 확인하고, 소유 테스트
  PID2803122에 SIGTERM을 보내 종료했다(명령101, signal15). 단순 관측 timeout을
  종료로 오인하거나 재시작한 것이 아니다. 기록은 `prepared-date-histogram-bounded-tests.log`.
- 최종 비교 입력은 epoch 경계의1초 구간과 leap day의 별도 묶음으로 분리했다.
  결측 문서 포함,12개 interval 표기 x4개 시간대 입력 x3개 offset x4개 문서/최소 개수
  조합으로 **576개 비교**를 수행한다. min_doc_count0/1 모두 검사하며 제품 기본값은
  바꾸지 않았다. 넓은 범위 자원 문제를 해결하거나 검증한 테스트로 표시하지 않는다.
  별도 경계값 테스트는 음수 시각, 시간대, offset, 주/월/년, i64 오버플로와
  미지원 interval/timezone을 확인한다.
- 수정 후 전체 engine unit868/868(23.82초), concurrent7/7(18.41초),
  merge4/4(3.74초), multi-field9/9(0.54초), **888/888 통과**, 실패/skip/filter0,
  명령 종료0. 빌드1분42초, 기존 debug 프로파일/직렬 테스트다.
  로그 `target/core-replacement-c05/prepared-date-histogram-engine-bounded-full.log`
  SHA-256 `b843dadf6b94817c0fea4f8699752cd62602c9df083f48e198dc99d4ef59a97c`.
  현재 engine source SHA-256
  `6f95a411625d7ca07526ed2b3a1c371fd88adecc974187b933452ad100824d47`.
- **새로 확인한 C06 자원 제어 위험(우선 보강 대상):**
  date_histogram_bucket_values_from_counts의 고정 간격 while 루프는 큰 시간 범위의
  빈 버킷을 생성/순회한다. min_doc_count 양수에서도 순회 비용이 남는다. crates 검색에서
  max_buckets/TooManyBuckets는 transport 예외 디코딩만 확인했으며 집계 생성 한도
  적용은 아직 확인하지 못했다. 공개 HTTP를 통한 OOM 재현은 수행하지 않았다.
  로컬 OpenSearch MultiBucketConsumerService.java는 search.max_buckets의 기본값65535,
  동적 node 범위 설정과 bucket consumer를 갖는다. 이 로컬 참조의 계약을 확인해 구현한다.
- 다음 작업은 C06 자원 제한 적용 위치와 오류 전파를 먼저 확인한다. 단일 날짜 함수의
  임의 잘라내기나 조용한 결과 누락 대신, 여러 집계/샤드 reduce의 요청 전체 한도와
  사전 생성 제한, 응답 오류 계약을 검증해야 한다. 양수 min_doc_count의 빈 구간 건너뛰기도
  기존 key 정렬/격자/extended·hard bounds 의미를 유지하는지 별도 대조한다.
  넓은 범위 회귀는 메모리/시간 제한을 둔 자식 프로세스에서만 재현한다. 기능 자원 안전성
  문제를 성능 exclusion ledger로 면제하지 않는다.
- 날짜 준비 변경은 아직 새 서버 빌드/node/live/전체6회 gate가 남아 있으며 성능 개선은
  미입증이다. 검증 전 완료로 표시하지 않는다. dada6399 후보와 b03643a 원본 서버는
  기존 SHA-256 불변, 최신 전체 성능은 여전히 dada6399 FAIL이다. 원본 Cargo 의존성도
  변경하지 않았다. 정식 수락0/40, C02/C06 미완료, ledger 비어 있음, 릴리즈 보류다.
  이번 테스트 세션은 모두 종료했으며 태그/커밋/배포는 없다.

#### C02 양수 최소 개수의 희소 날짜 집계와 C06 오류 전파 조사

- 2026-09-09: `date_histogram_bucket_values_from_counts`에서 양수
  `min_doc_count`는 실제 count map만 순회하도록 수정했다. 고정 간격의 기존
  시작점(extended bounds 포함)과 격자를 유지하고 hard bounds 및 최소 개수로
  필터링한다. 격자 거리 계산은 i128을 사용해 i64 양 끝 사이의 뺄셈 오버플로를
  피한다. 월/년의 기존 실제 버킷 순회와 min_doc_count0의 빈 버킷 생성은 유지한다.
  **양수 최소 개수의 빈 구간 CPU 문제에 대한 수정이지, 기본값0의 OOM 해결이 아니다.**
- 최초 희소/밀집 대조는288개 조합을 통과했다. i64 양 끝에 가까운 두 key의
  극단 범위 검사도 통과했다. 두 테스트는 각각 주소 공간512MiB, CPU10초,
  wall15초(종료 유예2초)의 자식 프로세스에서 먼저 실행했다. 증거는
  `target/core-replacement-c05/sparse-date-reference-bounded.log`와
  `sparse-date-extreme-bounded.log`다. 실행 시간은 성능 벤치마크 증거가 아니다.
- 그 상태의 전체 engine 테스트 로그 `sparse-date-engine-full.log`에는
  unit870/870(24.24초), concurrent7/7(17.65초), merge4/4(3.85초),
  multi-field9/9(0.54초), 총890개 성공 및 실패/skip/filter0이 기록됐다.
  재개 후 세션 핸들은 소멸했으므로 명령 종료 코드를 재확인했다고 주장하지 않는다.
  시간대/offset 조합을 추가한 후 별도의 제한 실행과 전체 테스트를 재검증한다.
- 시간대/offset 네 조합으로 대조를 확장한 최종1152개 비교와 극단 범위 검사는
  제한 자식 프로세스에서2/2 성공, 종료0이었다. 잘못된 시간대에 대한 기존 동작도
  대조하며 올바른 OpenSearch 호환성을 새로 보장하는 테스트로 해석하지 않는다.
  `sparse-date-zones-bounded.log` SHA-256
  `70dd7b164f7c241e4a7afaaeb3c70726244fc2cb0390f4c646e6df934096ac54`.
  이어 전체 engine unit870/870(24.06초), concurrent7/7(18.58초),
  merge4/4(3.85초), multi-field9/9(0.54초), **890/890 성공**, 실패/skip/filter0,
  빌드1분39초, 명령 종료0을 확인했다. 실행 중인 테스트 세션은 남지 않았다.
  `target/core-replacement-c05/sparse-date-zones-engine-full.log` SHA-256
  `980d5dd377eec8800f73437866dbfbe2b08d54e6eacee58311ba382ce68ae0f8`.
  최종 engine source SHA-256
  `4d6dd51559bcafecbfa934eea44a62ae0b9f2d72b2c30678a2d415cb88da35c3`.
- C06 오류 전파 조사: engine의 문서 기반 `collect_aggregations_from_documents`와
  hit 기반 집계 모두 날짜 collector 오류를 `unwrap_or_else`로 빈 버킷으로 바꾼다.
  내부 확장 집계 경로에도 같은 fallback이 있다. `Aggregation::Plugin`으로 표현된
  코어 기능을 외부 플러그인 제외 범위로 잘못 처리하지 않는다.
  simple collector는 Option, 일반 collector는 Value 반환이므로 helper에만 Result를
  추가하면 fatal 오류가 숨겨지거나 다른 fallback으로 우회할 수 있다.
- node의 `engine_error_to_rest_response`는 현재 type/reason/status만 직렬화한다.
  native search 경로는 InvalidRequest/IndexNotFound를 None으로 바꾸어 fallback하므로,
  자원 한도 초과를 InvalidRequest로 표현하면 제한을 우회할 수 있다. 전용 fatal 오류와
  검색/PIT 등 각 fallback 경계 테스트가 필요하다.
  transport 예외149 decoder는 max_buckets 정수를 읽지만 버린다. 제한값 메타데이터,
  HTTP 상태, 원격 샤드 오류의 전달 계약까지 함께 보강해야 한다.
  로컬 OpenSearch `MultiBucketConsumerService.java`의 기본값65535, 초과 시503과
  `max_buckets` 메타데이터를 확인했다. `InternalDateHistogram.reduce`는
  addEmptyBuckets 이후 consumeBucketsAndMaybeBreak를 호출한다. 따라서 이 참조가
  날짜 빈 버킷의 사전 할당 방지까지 보장한다고 주장하지 않는다.
- 다음 C06 구현 순서와 수락 조건:
  1. 타입이 있는 자원 한도 오류를 collector부터 engine, node, 원격 reduce까지
     전파한다. 미지원 최적화의 None과 fatal 오류를 구분하고 빈 결과 fallback을
     차단한다. HTTP503, 오류 type, max_buckets와 직렬화 왕복 테스트를 추가한다.
  2. 동적 search.max_buckets 설정의 기본값/0/잘못된 값/업데이트 계약을 확인하고
     요청에서 일관된 한도를 사용한다. 여러 최상위 집계, nested 하위 집계, 여러
     샤드와 최종 reduce의 계산 범위를 명시한다. 중복 샤드 bucket의 최종 병합을
     단순 합산으로 오인하지 않으며, 출력 개수 한도와 중간 메모리 보호를 구분한다.
  3. 날짜 빈 버킷을 생성하기 전에 checked 산술과 bounds로 생성 범위를 제한한다.
     결과의 조용한 잘라내기, min_doc_count 기본값 변경, 안전 제어 완화는 금지한다.
     경계 limit-1/limit/limit+1, 빈 입력과 extended bounds, 극단 날짜, 다중 집계,
     nested 및 다중 샤드 실패를 메모리/시간 제한 자식 프로세스에서 검증한다.
  4. 위 각 구현 단위는 기능 테스트와 별개로 전체 non-plugin 벤치마크를 실행하고
     반복 측정 및 실제 실행 파일 식별 증거를 남겨야 완료할 수 있다. 동일 workload,
     내구성, 보안, 자원 설정과 별도 build directory를 사용한다. 최초 v0.6.0 대비
     topology별 throughput >=95%, scenario별 mean/p95/p99 <=105%를 각각 적용한다.
     초과 시 최적화 후 전체 재실행하며 다른 개선으로 상쇄하거나 기준선을 바꾸지 않는다.
- 준비/희소 날짜 수정은 아직 측정된 dada6399 서버 후보에 포함되지 않았다.
  새 서버/node/live/반복 전체 gate는 미완료이며, 최신 실제 전체 성능 판정은 여전히
  dada6399 FAIL이다. 정식 수락0/40, C02/C06 미완료, 성능 exclusion ledger 비어 있음.
  자원 안전성 문제는 성능 제외로 면제하지 않으며 릴리즈는 보류한다.

#### C06 버킷 한도 오류의 engine/REST 표현 기반

- 2026-09-09: 이전 단계는 희소 날짜 집계 코드 및1152개 대조/890개 테스트 증거를
  추가한 진척이었다. 이번에는 현행 오류 enum과 node fallback 경계를 다시 확인하고
  `EngineError::TooManyBuckets { max_buckets, bucket_count }`를 추가했다.
  HTTP503, `too_many_buckets_exception`, 제한값과 실제 개수가 포함된 reason을
  제공한다. max_buckets는 u32, bucket_count는 u64로 보존한다. 동적 설정의
  유효 범위 검증은 아직 연결하지 않았으며 OpenSearch의 int 범위를 넓힌 설정으로
  수락했다는 의미가 아니다.
- `EngineError::opensearch_error_body`로 type/reason을 구성하고 이 전용 오류에만
  `max_buckets`를 넣는다. node의 `engine_error_to_rest_response`가 이를 사용한다.
  기존 InvalidRequest/IndexNotFound fallback 분기는 변경하지 않았고 새 variant는
  일반 fatal 오류 분기로 전달되는 구조다. 실제 검색 요청에서의 발생/전파 검증은
  collector 연결 후 필요하며, converter 테스트만으로 fallback 우회 방지가 검증됐다고
  표시하지 않는다.
- engine 단위 테스트15/15 성공, 실패/skip/filter0, 종료0. 새 테스트는 limit0,
  기본값65535, u64 최대 실제 개수의 오류 표현과 기존6종 오류 JSON 형태를 검사한다.
  로그 `target/core-replacement-c05/bucket-error-engine-tests.log` SHA-256
  `a5b5090422cd5edd6608c817a23e6810d0c0c36d0a1adcc77e2d657ebbb7a9ac`.
  engine abstraction source SHA-256
  `6f7b48bd9e62428ce39a35060332ac47687c5561fc6a77404a169fd58c6f8793`.
  node standalone source SHA-256
  `7a3cc325bf554f212470a2a61bc13766c1ed655671910b07ac8c63c4ad4a309a`.
- node 전체 lib647/647(11.75초), steelsearch bin459/459(18.27초),
  **1106개 성공**, 실패/skip/filter0, 명령 종료0. 새 REST converter 테스트 포함이다.
  nightly, RUSTFLAGS=-Awarnings, jobs2, incremental0,
  DEV_DEBUG/TEST_DEBUG=0의 비최적화 프로파일과 직렬 테스트를 사용했다.
  빌드2분37초. `target/core-replacement-c05/bucket-error-node-full.log` SHA-256
  `6060bfbc89631756af3c7ae37ee62ffac847c8daf55c1a5c297519612a162825`.
- 같은 비최적화 debug0 프로파일의 Tantivy 전체 unit870/870(21.98초),
  concurrent7/7(17.01초), merge4/4(3.33초), multi-field9/9(0.49초),
  890개 성공, 실패/skip/filter0, 빌드1분50초, 종료0.
  `target/core-replacement-c05/bucket-error-tantivy-full.log` SHA-256
  `57dfae3f09fdc9e103df35544b37dbdcac1cac78402e8037b6e9604f1c54c99e`.
  이번 engine/node/Tantivy 합계2011개 성공이며 실행 중인 세션은 없다.
  새 릴리즈 서버 빌드/live/전체 성능 실행은 하지 않았고 태그/커밋/배포도 없다.
- **아직 자원 보호 구현이 아니다.** collector가 이 오류를 발생시키는 한도 검사,
  Option/Value 반환 경로의 Result 전파, transport 예외149의 max_buckets 보존과
  송수신, 동적 설정, 다중 집계/샤드 reduce 및 사전 생성 제한이 남아 있다.
  transport는 현행 decode 시 값을 버리는 상태를 그대로 두었다. 메모리 무제한
  OOM 재현이나 한도 초과 결과의 조용한 잘라내기는 하지 않는다.
- C06 구현 단위 완료 전 전체 non-plugin 반복 벤치마크와 고정 v0.6.0의 누적
  throughput/mean/p95/p99 각5% gate가 필수다. 이번 기반 변경은 정식 완료로
  집계하지 않으며 이전 릴리즈/OpenSearch 비교도 대체하지 않는다.
  최신 측정 후보 dada6399 FAIL, 정식0/40, ledger 비어 있음, 릴리즈 보류를 유지한다.

#### C06 transport 버킷 한도 메타데이터 보존

- 2026-09-09: 이전 전용 engine/REST 오류와2011개 테스트는 기반 구현의 진척이다.
  현행 transport에서 예외149의 확장 int를 버리는 것을 재확인하고,
  `TransportError.max_buckets: Option<i32>`에 보존하도록 변경했다. 기존 JVM/기타
  예외와 SearchContextMissing 생성자는 None을 사용한다. 기존 PIT 샤드 실패
  생성자의 변경도 필드 초기화에 한정했다.
- `write_supported_exception`과 사전 validator에 TooManyBucketsException을
  추가했다. OpenSearch 예외 key0/id149, message/cause, 빈 stack/header/metadata,
  big-endian int 한도 순서로 쓴다. 한도 없음/음수는 쓰기 전에 거부한다.
  decoder는 wire의 signed int를 그대로 보존하며 동적 설정 검증을 대신하지 않는다.
  로컬 참조는 `OpenSearchServerException.java`의149 등록과
  `MultiBucketConsumerService.java`의 readInt/writeInt다.
- 새 테스트3개: 고정14바이트 payload에서65535 복원 및 잘린 payload 거부;
  한도0/65535/i32::MAX x 직접/중첩 원인의 일반 예외·샤드 실패·검색 응답·실패 노드
  응답 왕복; 한도 누락/-1/i32::MIN의 사전 거부 및 출력 바이트 없음 확인.
  고정 바이트는 로컬 소스 기반 fixture이며 실제 Java 실행에서 채취한 캡처가 아니다.
  검색 컨테이너는 OPENSEARCH_3_7_0_TRANSPORT로 검사했고 실패 status 문자열
  SERVICE_UNAVAILABLE 및 total/successful shard 개수 보존을 확인한다.
- 최종 transport 전체707/707 성공, 실패/skip/filter0, 빌드15.19초, 테스트0.35초,
  명령 종료0. 앞선 컨테이너 확장 전 전체707개 성공 로그도 별도로 보존한다.
  `target/core-replacement-c05/bucket-error-transport-search-full.log` SHA-256
  `4415f76cc94f6381ef7e0c97aeea37f79c4611f9dd7e92534104b49ec5639fed`.
  source SHA-256: transport error
  `99883aa77ff90047f28a676ddc20f6cead235087a0fa403347151cb34f9b7abb`,
  transport action `f739fd474600286d79ab40d9702f994bd659390171d7fc87339bfce28025e344`,
  node main `c8a4a83f0e13e458dad47314ee6a244d13bdd43bc93faf6b863bc535133ad155`.
- node 전체 lib647/647(11.46초), bin459/459(17.40초),1106개 성공,
  실패/skip/filter0, 빌드1분04초, 종료0. transport와 합계1813개 성공이다.
  nightly/RUSTFLAGS=-Awarnings/jobs2/incremental0/DEV_DEBUG=0/TEST_DEBUG=0,
  비최적화 및 직렬 테스트다. 로그
  `target/core-replacement-c05/bucket-error-transport-node-full.log` SHA-256
  `edf94f382652b1dd6093c47eb66a4063b709e3f77350e098d24f55d45c89b491`.
  이번 세션은 모두 종료했으며 git diff --check 성공이다. 새 release 서버 빌드,
  live/전체 성능 gate, 태그/커밋/배포는 하지 않았다.
- 이 단계는 wire 표현 보존이지 실제 검색 자원 제어 완료가 아니다. collector 한도
  발생과 Result 전파, 원격 오류의 engine/REST fatal 분류, 동적 설정 및 생성 전
  메모리 보호는 남아 있다. wire 왕복 성공을 Java 상호운용/live 증거나 OOM 방지
  증거로 바꾸어 기록하지 않는다. 다음에는 Value/Option collector 경계를 Result로
  연결하고 미지원 fast path와 fatal 오류를 구분해야 한다.
- C06 각 구현 단위의 정식 완료 전 전체 non-plugin 반복 벤치마크를 실행한다.
  최초 v0.6.0 고정 기준의 topology throughput >=95%, 각 scenario mean/p95/p99
  <=105%를 각각 만족해야 하며 기준선 재설정/개선 상쇄는 금지한다. 실행 파일 식별,
  동일 실제 설정과 별도 build directory, 기존 발표 증거 보존 규칙을 유지한다.
  현재 정식0/40, 최신 측정 후보 dada6399 FAIL, ledger 비어 있음, 릴리즈 보류다.

#### C06 native 검색 fallback 경계 고정

- 2026-09-09: 이전 transport 메타데이터 보존/1813개 테스트는 진척이다.
  내부 collector 연결 조사 후, 먼저 실제 native 검색/PIT/scroll의 세 오류 분기를
  `native_search_error_response`로 공통화했다. 기존 InvalidRequest/IndexNotFound만
  None으로 반환하고 나머지는 engine 오류의 status/body를 보존한다. 기존 허용
  분류 자체를 바꾸지 않았으며 자원 오류를 새로 발생시키는 변경은 아니다.
- 새 테스트는 기존 재시도 대상2종과 fatal6개 입력(한도0/65535, backend,
  version conflict, 중복 index, missing document)을 검사한다. 세 제품 경로가
  같은 helper를 호출함을 source에서 확인했다. 오류를 직접 주입한 helper 테스트이지
  실제 집계 limit 초과를 발생시킨 HTTP/E2E 검증은 아니다.
- node 전체 lib648/648(11.85초), bin459/459(17.30초), **1107개 성공**,
  실패/skip/filter0, 빌드51.04초, 종료0. nightly/RUSTFLAGS=-Awarnings/jobs2/
  incremental0/DEV_DEBUG=0/TEST_DEBUG=0, 비최적화 직렬 테스트다.
  `target/core-replacement-c05/bucket-error-fallback-node-full.log` SHA-256
  `25566180631643be328d23e03943d9b64db8b323c07c26f8cc6db2cac4a1bb9f`.
  standalone source SHA-256
  `872531750ea8a5393cab079067dd8a6ab4137d5722940a7c2edfa5d6be73098b`.
- collector 내부 변경은 아직 착수하지 않았다. 문서 collector의 직접 호출27곳은
  native 상위 경로와 global/significant terms 및 내부 확장 하위 집계를 포함한다.
  문서/hit/확장 collector를 함께 fallible하게 만들고 map closure의 Result 수집과
  Option<Result> 전파를 연결해야 한다. 한 함수에만 cap을 넣고 기존 unwrap fallback을
  남기면 빈 성공 결과가 나올 수 있어 금지한다. 내부 확장 enum을 외부 플러그인
  제외 범위로 오인하지 않는다.
- 추가 조사: `collect_single_aggregation_native`는 rg에서 정의만 확인됐고,
  `collect_aggregations_for_query_index_aware_with_context` 호출은 테스트 구간에서만
  확인됐다. 이들 함수의 .ok().flatten()만 수정하고 실제 집계 오류 전파가 개선됐다고
  주장하지 않는다. 현재 실사용 collector 호출 경계를 기준으로 변경해야 한다.
  `search_response_wire_to_rest_response`는 shard failure 개수만 넣고 상세 원인을
  내보내지 않는다. 원격 오류 연결 시 상세 원인/한도 정보, partial failure와 전체
  요청 실패 의미를 함께 확인해야 하며 무조건 HTTP503으로 바꾸지 않는다.
- 정식 완료 전 각 구현 단위마다 전체 non-plugin 반복 벤치마크를 실행하고
  최초 v0.6.0 대비 throughput >=95%, 각 scenario mean/p95/p99 <=105%를
  독립적으로 만족해야 한다. 이번에는 새 서버/live/전체 gate를 실행하지 않았다.
  정식0/40, C06 미완료, 최신 dada6399 FAIL, ledger 비어 있음, 릴리즈 보류다.
  테스트 세션은 모두 종료했고 태그/커밋/배포는 없다.

#### C06 원격 검색 REST 실패 상세 보존

- 2026-09-09: 이전 native 오류 분류/1107개 테스트는 경계 고정의 진척이었다.
  현행 `search_response_wire_to_rest_response`는 실패 개수만 렌더링함을 확인하고,
  실패가 있을 때 `_shards.failures`에 shard/index/node와 오류 원인을 추가했다.
  `transport_error_rest_reason`은 현재 wire adapter가 지원하는4개 예외 이름을
  REST type으로 매핑하고 message, caused_by, max_buckets를 보존한다.
  매핑 외의 class는 원래 이름을 유지하며 일반 Java 예외 전체의 명명 호환성을
  구현했다고 주장하지 않는다.
- 부분 실패 응답의 기존 HTTP200을 유지하고 실패 없는 응답에는 failures 필드를
  추가하지 않는다. 검색의 전체 실패/allow_partial_search_results 정책을 새로
  구현하거나 한도 오류를 발생시키는 변경이 아니다. 상위 fatal 전파는 별도 작업이다.
- 로컬 참조 `ShardSearchFailure.toXContent`와 wire 생성자,
  `SearchShardTarget.getFullyQualifiedIndexName`,
  `RemoteClusterAware.buildRemoteIndexName`을 확인했다. target이 없으면
  shard-1/index null, target이 있으면 node를 전달한다. 비어 있지 않은 cluster alias는
  alias:index 형식이며 null/빈 alias는 원래 index다.
- 새 REST 변환 테스트는 중첩 TooManyBuckets cause/65535 한도, 부분 실패200,
  실패 없는 응답, target node/shard, null/빈/remote alias와 integer total을 확인한다.
  이는 로컬 변환 테스트이며 실제 HTTP/Java 상호운용이나 원격 limit 초과 재현은 아니다.
  최종 standalone source SHA-256
  `5f4264048d0988a1e3010ef75ad693e147ef31e68297f60f3ba29d731e26cb56`.
- 최종 node 전체 lib650/650(11.78초), bin459/459(17.63초),1109개 성공,
  실패/skip/filter0, 빌드50.07초, 명령 종료0. nightly/RUSTFLAGS=-Awarnings/
  jobs2/incremental0/DEV_DEBUG=0/TEST_DEBUG=0, 비최적화 직렬 테스트다.
  `target/core-replacement-c05/bucket-error-remote-rest-target-node-full.log` SHA-256
  `bda6b5e64d54ce6cabd225abaa9fcce91b2077d08205d804eb8114256081a294`.
  alias 보강 전 전체1108개 성공 로그도 별도로 보존했다. 실행 세션은 모두 종료했다.
  새 release 서버/live/전체 gate나 태그/커밋/배포는 실행하지 않았다.
- collector Result 전파, 요청 전체 버킷 예산, 동적 설정 및 생성 전 메모리 보호는
  남아 있다. C06 완료 전 각 구현 단위의 전체 non-plugin 반복 벤치마크와 최초
  v0.6.0 고정 기준 throughput >=95%, 각 scenario mean/p95/p99 <=105% gate가
  필수다. 다른 개선으로 상쇄하거나 기준선을 변경하지 않는다.
  정식0/40, 최신 측정 dada6399 FAIL, ledger 비어 있음, 릴리즈 보류를 유지한다.

#### C06 문서 collector의 fallible 연결

- 2026-09-09: 이전 원격 REST 실패 상세 보존/1109개 테스트는 진척이다.
  이번에는 `collect_simple_bucket_aggregations_from_documents`를
  EngineResult<Option<Value>>로, 일반 문서 collector와 문서 확장 collector를
  EngineResult<Value>로 변경했다. 미지원 fast path의 Ok(None)과 실패 Err를 분리하고
  native 상위 집계 경계 및 재귀 하위 집계에 ?로 전달한다.
- 하위 집계 iterator는 collect::<EngineResult<Vec<_>>>()?로 첫 오류에서 중단한다.
  선택적 하위 집계는 Option<Result>의 transpose()?로 오류를 보존한다.
  adjacency matrix는 fallible callback을 받는 공통 계산을 추가하고 아직 infallible인
  hit 경로는 Infallible adapter로 기존 계산을 사용한다. 오류를 빈 map으로 치환하지 않는다.
- 변경 전 engine source를
  `target/core-replacement-c05/before-fallible-document-collectors.rs`에 보존했다
  (SHA-256 4d6dd51559bcafecbfa934eea44a62ae0b9f2d72b2c30678a2d415cb88da35c3).
  `target/core-replacement-c05/fallible-rewrite`의 syn 기반 임시 도구로 함수/호출/
  closure 경계196곳에 기계적 삽입을 적용했다. 전체 파일 포맷을 재생성하지 않았다.
  첫 check의 adjacency callback 타입 오류2개를 수동 연결하고, 구문 트리 방문이
  확장하지 않는 assert! 내부 두 호출도 수정했다. 두 번째 cargo check는 종료0이었다.
  임시 도구 의존성은 별도 workspace이며 제품 Cargo 의존성은 바꾸지 않았다.
- 문서 날짜 집계의 직접/자동/내부 확장 경로 세 곳에서 Err를 빈 버킷으로 바꾸던
  unwrap_or_else를 제거했다. hit 기반 collector의 동종 지점은 아직 남아 있다.
  새 테스트는 유효한 DSL을 파싱한 후 내부 interval을 잘못된 값으로 바꿔,
  fast path 미지원 이후 일반 collector가 원래 오류를 전달하는지 검사한다.
  HTTP parser나 실제 bucket limit을 통한 오류 재현으로 해석하지 않는다.
  adjacency 테스트는 callback1/2/3번째에 TooManyBuckets를 반환하고 정확히 그
  지점에서 중단하는지, 성공 결과는 기존 helper와 같은지 확인한다.
- 최종 engine source SHA-256
  `1fb6a9c7d2d6d5885346b38b1f0dacb041614dbe46656b11d09d8ca941db4656`.
  세 번째 오류 무시 지점 제거 전 전체 engine872+7+4+9=892개 성공 로그는
  `target/core-replacement-c05/fallible-document-engine-full.log`에 보존했다.
- 세 지점 모두 제거한 최종 전체 engine unit872/872(21.91초), concurrent7/7(17.03초),
  merge4/4(3.28초), multi-field9/9(0.49초),892개 성공, 실패/skip/filter0,
  빌드1분21초, 명령 종료0. nightly/RUSTFLAGS=-Awarnings/jobs2/incremental0/
  DEV_DEBUG=0/TEST_DEBUG=0, 비최적화 직렬 테스트다.
  `target/core-replacement-c05/fallible-document-final-engine-full.log` SHA-256
  `6cfb325bbe579ae181c019d812e4650c57c74834a766c91b25b34586b06208de`.
- 같은 프로파일의 node lib650/650(11.73초), bin459/459(17.64초),1109개 성공,
  실패/skip/filter0, 빌드1분06초, 종료0. 최종 engine/node 합계2001개 성공이다.
  `target/core-replacement-c05/fallible-document-node-full.log` SHA-256
  `021979d9ee61cfba6c494bad4b0a04d9f64fd17bc7ed582c8d9cc8c6a61e9c15`.
  전체 실행 세션이 종료됐고 git diff --check도 성공했다. 새 release 서버 빌드,
  live/전체 성능 gate, 태그/커밋/배포는 수행하지 않았다.
- 다음에는 hit 기반 네 collector의 같은 Result 연결과 오류 무시 제거를 수행한다.
  그 뒤 요청 전체 예산/동적 설정/생성 전 한도를 연결해 단일·중첩·다중 집계와
  다중 샤드 계약을 메모리/시간 제한 하에서 검사한다. 현재 실제 버킷 생성 한도를
  적용한 상태가 아니며 OOM 보호나 C06 완료로 표시하지 않는다.
- 각 구현 단위 완료 전 전체 non-plugin 반복 벤치마크가 필수다. 최초 v0.6.0의
  실제 동일 설정/별도 build directory/실행 파일 식별/원본 증거를 유지하고,
  topology throughput >=95%, scenario별 mean/p95/p99 <=105%를 독립 적용한다.
  기준선 재설정과 개선 상쇄는 금지한다. 최신 측정 dada6399 FAIL, 정식0/40,
  C06 미완료, ledger 비어 있음, 릴리즈 보류를 유지한다.

#### C06 hit collector의 fallible 연결

- 2026-09-09: 이전 문서 collector Result 전파/2001개 테스트는 진척이었다.
  이번에는 hit 기반 일반 집계 및 background 지원 함수, hit 확장 collector와
  wrapper의 네 반환형을 EngineResult<Value>로 변경했다. 단일/다중 인덱스 상위
  집계, global/significant terms 및 재귀 하위 집계에 ?를 연결하고, 선택적 하위
  집계는 transpose()?, iterator는 collect::<EngineResult<Vec<_>>>()?로 수집한다.
- 변경 전 source를 `target/core-replacement-c05/before-fallible-hit-collectors.rs`에
  보존했다(1fb6a9c7d2d6d5885346b38b1f0dacb041614dbe46656b11d09d8ca941db4656).
  임시 syn 도구의 대상 함수를 hit 네 함수로 변경해134개 기계적 삽입을 적용했다.
  첫 check에서 확인된 adjacency callback 타입 오류2개는 기존 fallible helper에
  연결해 수정했다. 단순 wrapper의 불필요한 Ok/물음표는 제거했다. 기존 infallible
  adjacency helper는 이제 테스트 전용이며 제품의 두 경로는 fallible 계산을 사용한다.
- hit 날짜 collector 오류를 빈 버킷으로 바꾸던 두 지점을 제거했다. 문서 경로의
  세 지점과 합쳐 해당 날짜 collector 호출 다섯 지점 모두 오류를 전달한다.
  기존 오류 전파 테스트를 문서와 hit의 CallerFinal/NeedsExplicitSort 및
  background None/Some(empty)로 확대했다. 내부 invalid interval 오류가 대상이며,
  실제 버킷 한도나 HTTP 요청으로 오류를 발생시킨 테스트가 아니다.
- engine 전체 unit872/872(22.59초), concurrent7/7(16.01초), merge4/4(3.54초),
  multi-field9/9(0.48초),892개 성공, 실패/skip/filter0, 빌드1분24초, 종료0.
  nightly/RUSTFLAGS=-Awarnings/jobs2/incremental0/DEV_DEBUG=0/TEST_DEBUG=0,
  비최적화 직렬 테스트다. `target/core-replacement-c05/fallible-hit-engine-full.log`
  SHA-256 `93283cad434167c8a8492812dd7378cb76a5fe2fb30fc770688592f6d90c3b4a`.
  engine source SHA-256
  `d03b952b9be733fd91da77b94ec64a002beba16c0298bc0100584165809145d9`.
- 동일 프로파일 node lib650/650(11.74초), bin459/459(17.43초),1109개 성공,
  실패/skip/filter0, 빌드1분05초, 종료0. 최종 engine/node 합계2001개 성공이다.
  `target/core-replacement-c05/fallible-hit-node-full.log` SHA-256
  `efb702d28a435ee4e1c7200f55254201bb0ca0e1dc76e9fa94b915ab6ce64073`.
  모든 실행 세션이 종료됐으며 새 release 서버/live/전체 gate, 태그/커밋/배포는 없다.
- 다음 단계는 요청 전체의 동일한 예산을 두 collector와 하위 집계/reduce에 전달하고,
  동적 search.max_buckets 및 생성 전 제한을 연결하는 것이다. 각 집계에서 예산을
  초기화하거나 검색 본문으로 설정을 우회하게 하지 않는다. 중간 자원 사용과 최종
  출력 bucket 수를 구분하고 같은 key의 shard 병합을 무조건 합산하지 않는다.
  실제 생성 제한/OOM 보호는 아직 미구현이며 C06 완료로 집계하지 않는다.
- 각 구현 단위 완료 전 전체 non-plugin 반복 벤치마크를 실행한다. 최초 v0.6.0
  고정 기준의 topology throughput >=95%, scenario별 mean/p95/p99 <=105%를
  독립 적용하며 동일 실제 설정/실행 파일 식별/별도 build directory/발표 증거 보존,
  기준선 재설정·개선 상쇄 금지 규칙을 유지한다. 최신 측정 dada6399 FAIL,
  정식0/40, ledger 비어 있음, 릴리즈 보류다.

#### C06 날짜 버킷 생성 전 지역 보호

- 2026-09-09: 이전 문서/hit 오류 전파/2001개 테스트는 진척이다. 이번에는
  date_histogram_bucket_values_from_counts를 EngineResult로 바꾸고 세 호출자가
  오류를 전달하도록 연결했다. 기본 참조 한도65535를 넘는 날짜 결과는 생성 전에
  TooManyBuckets로 거부한다. **현재는 날짜 collector별 지역 할당 보호이며,
  요청 전체 누적 예산이나 동적 search.max_buckets 구현을 대체하지 않는다.**
- 고정 간격/min_doc_count0에서는 extended bounds와 기존 key 범위에 hard bounds를
  교차시키고, 원래 시작점 격자에 맞는 첫 key와 전체 개수를 i128로 계산한다.
  거부할 결과를 먼저 Vec/JSON으로 생성하지 않는다. hard bounds 밖의 광대한 앞 구간도
  순회하지 않는다. 양수 min_doc_count 및 기존 month/year 실제-key 경로는 출력 조건을
  만족하는 개수를 먼저 확인하고 그 후 결과를 만든다. count map 자체의 누적 메모리와
  다른 bucket family, 여러 collector 합계는 아직 보호하지 않는다.
- 최초 제한 실행은 두 테스트가 실패했다. 숫자 bounds는 native DSL이 문자열을
  요구하며 거부했고, 숫자 문자열은 date_histogram_bucket의 날짜 파싱에서 무시됐다.
  `date-bucket-guard-bounded.log`를 보존한다. 로컬 OpenSearch LongBounds는
  VALUE_NUMBER를 지원하므로 **숫자 bounds/format 해석은 C02 호환성 미비로 남긴다.**
  이 실패를 성능 exclusion이나 기능 완료로 바꾸지 않는다.
- ISO bounds로 바꾼 제한 실행에서 preflight는 성공했다. public engine 테스트의
  global/terms 하위 집계는 HTTP 원형을 engine API에 직접 넣어 파싱 실패했다
  (`date-bucket-guard-iso-bounded.log`). 이는 해당 기능이 없는 증거가 아니라 테스트
  계층 오류다. 기존 engine 테스트와 같은 core plugin/params/aggregations 표현으로
  수정했다. 내부 core 표현을 외부 플러그인 지원으로 집계하지 않는다.
- 최종 제한 실행에서 두 테스트 모두 성공, 종료0,0.06초다. 주소 공간1GiB,
  CPU20초, wall30초/종료 유예2초를 적용했다. min0/65534/65535 허용 및65536 거부,
  광대한 i64 날짜 범위의 사전 거부, ISO hard bounds로 제한된 두 빈 버킷, 역전 범위의
  빈 결과를 검사한다. 실제 engine.search에서 일반/global/terms 하위 집계 x size0/10
  여섯 요청은 정확히65536개의 날짜 버킷에 대해 TooManyBuckets/상태503을 전달했다.
  서버 HTTP 요청이나 전체 요청 누적 한도 검증으로 확대 해석하지 않는다.
  `target/core-replacement-c05/date-bucket-guard-core-bounded.log` SHA-256
  `95904f854107ed500bf83be335a85ba7cdb662bd47620e64b1f5f1d04a9e7645`.
- 기존 희소 대조1152개 조합의 bounds도 ISO로 바꿔 실제 필터를 검사하도록 했다.
  이전 숫자 문자열 대조만으로 bounds 지원이 증명됐다고 보지 않는다.
  극단 범위 포함 두 테스트가 같은 제한 실행에서 성공/종료0이었다.
  `date-bucket-guard-sparse-iso-bounded.log` SHA-256
  `d88807d1a4125400199ce7999a44db4afeed0822685c9cdf0a150a04ad29caae`.
- engine 전체 unit874/874(21.85초), concurrent7/7(17.02초), merge4/4(3.26초),
  multi-field9/9(0.49초),894개 성공, 실패/skip/filter0, 빌드20.17초, 종료0.
  nightly/RUSTFLAGS=-Awarnings/jobs2/incremental0/DEV_DEBUG=0/TEST_DEBUG=0,
  비최적화 직렬 실행이다. `target/core-replacement-c05/date-bucket-guard-engine-full.log`
  SHA-256 `9f291e444fa8bdd18e0804cc3592652bc299f731363ce00d3d0788f8ee932a33`.
  source SHA-256 `9510f6e151006ffb0c665e30075acdda5a7d2f78ed3b753a44eec43d48d1a587`.
- 같은 프로파일 node lib650/650(11.49초), bin459/459(17.44초),1109개 성공,
  실패/skip/filter0, 빌드1분06초, 종료0. 최종 engine/node 합계2003개 성공이다.
  `target/core-replacement-c05/date-bucket-guard-node-full.log` SHA-256
  `af5aea1c76ff5a111a164f37b0f16a85f2bb6b1d996245d14d4d4018b66a9643`.
  모든 세션이 종료됐고 git diff --check 성공이다. 새 release 서버/live/전체 gate,
  태그/커밋/배포는 실행하지 않았다.
- 다음 단계는 지역 보호를 요청/하위 집계/reduce의 공유 예산과 동적 설정에 연결하고,
  날짜 이외 bucket family와 중간 메모리까지 제어하는 것이다. 지역65535 한도를
  요청 전체의 한도로 오인하거나 각 collector에서 누적 예산을 재시작하지 않는다.
  C06 단위 완료 전 전체 non-plugin 반복 벤치마크 및 최초 v0.6.0 대비 throughput
  >=95%, scenario별 mean/p95/p99 <=105% gate가 필수다. 동일 실제 설정과 실행 파일
  식별/별도 build directory/원본 증거 보존, 기준선 재설정·개선 상쇄 금지를 유지한다.
  정식0/40, C02/C06 미완료, 최신 측정 dada6399 FAIL, ledger 비어 있음, 릴리즈 보류다.

#### C02 숫자 날짜 경계와 C06 사전 제한 연결

- 2026-09-09: 직전 지역 보호 검증에서 발견한 숫자 bounds 거부를 수정했다.
  DateHistogramBounds는 문자열로 강제 변환하지 않고 JSON 숫자/문자열 구분을
  유지한다. extended_bounds/hard_bounds 모두 signed i64 정수와 문자열을 받고,
  null은 경계 없음으로 유지한다. 정수로 손실 없이 변환되는 실수 표기도 허용한다.
  소수 부분, 범위 초과, bool/array/object는 거부한다. i64 최대값을 f64로 바꾼
  2^63은 허용하지 않는다. 로컬 OpenSearch LongBounds.java의 longValue(false)와
  AbstractXContentParser.java의 ensureNumberConversion을 대조했다.
- 날짜 경계 전용 helper는 숫자를 epoch milliseconds로 직접 rounding한다.
  명시적 format: epoch_millis의 숫자 문자열도 처리하고 기존 ISO 경로를 유지한다.
  extended/hard bounds 및 생성 전 개수 계산이 같은 helper를 사용한다.
  이는 전체 날짜 형식 지원이 아니다. mapping format, 복합 format/date math,
  잘못된 날짜 형식의 일관된 거부, 극단 calendar rounding은 별도 검증이 남는다.
  기본 형식의 숫자 문자열을 모두 milliseconds로 해석하지 않는다.
- DSL 전체134/134 성공, 실패/skip/filter0, 종료0, 빌드4.40초/테스트0.02초다.
  i64 양 끝값과 문자열의 타입/serde 왕복, null, 정수형 실수 정규화 및 잘못된
  타입/소수/범위 초과 거부를 검사했다.
  `target/core-replacement-c05/numeric-date-bounds-final-dsl-full.log` SHA-256
  `6ee45bf7fdc3a1ec0ded85d6c3e7875cc5a57b25d43da67046d1455017b32003`.
  `crates/os-query-dsl/src/lib.rs` SHA-256
  `ecd1c9831078dbc5632d01452854c476a82f2aaa5a1449d6c5c5210e38ad4db9`.
- 제한 실행 두 테스트 성공, 종료0,0.06초, 주소 공간1GiB/CPU20초/wall30초와
  종료 유예2초를 적용했다. ISO/숫자/명시적 epoch_millis 문자열 hard bounds가
  동일한 두 버킷으로 제한됨을 검사했다. engine.search의 일반/global/terms 하위
  집계 및 size0/10 조합 총14요청은65536개 생성 전에 정확한 TooManyBuckets와
  상태503을 반환했다. 실수 정규화는 별도 DSL 테스트이며,14요청에 포함되지 않는다.
  이는 engine API 증거이지 실제 서버 HTTP/Java 상호운용 증거는 아니다.
  `target/core-replacement-c05/numeric-date-bounds-bounded.log` SHA-256
  `95904f854107ed500bf83be335a85ba7cdb662bd47620e64b1f5f1d04a9e7645`.
- 최종 engine 전체 unit874/874(22.22초), concurrent7/7(16.33초),
  merge4/4(3.31초), multi-field9/9(0.49초), 총894개 성공, 실패/skip/filter0,
  종료0, 빌드1분26초다. nightly/RUSTFLAGS=-Awarnings/jobs2/incremental0,
  DEV_DEBUG=0/TEST_DEBUG=0, 비최적화 직렬 실행이다.
  `target/core-replacement-c05/numeric-date-bounds-final-engine-full.log` SHA-256
  `d4b9f1a4c00bb9eb27078b816fe490f4be8aa2360b184b62cbe6c05e729a0859`.
  `crates/os-engine-tantivy/src/lib.rs` SHA-256
  `228ea8ec204ceb374a739b2f62bb271471aa273d1f85adf376cd97a995eca5cc`.
- 같은 프로파일 node lib650/650(11.77초), bin459/459(17.44초), 총1109개
  성공, 실패/skip/filter0, 종료0, 빌드1분08초다. 최종 DSL/engine/node 합계
  2137개 성공이다. 모든 검증 세션이 정상 종료됐고 git diff --check도 성공했다.
  `target/core-replacement-c05/numeric-date-bounds-node-full.log` SHA-256
  `171ee53add221b97aabe010793b6baa57e75c9bce318b3329f8d52cc5fe0ed85`.
- 다음 C06 작업은 검색 실행 시 신뢰된 설정을 한 번 읽고, root/하위 집계가
  같은 예산을 공유하도록 document/hit collector에 전달하는 것이다. 검색 본문에서
  한도를 올리거나 재귀 호출마다 초기화하지 않는다. 중간 할당과 최종 reduce의
  bucket 수는 구분하고, 같은 shard key 병합을 무조건 합산하지 않는다.
  cluster settings PUT의 기존 persistent/transient 병합 및 검증 경로에 유효성
  검사를 연결하되, 값 저장만으로 실행 중 제한이 구현됐다고 보지 않는다.
  여러 형제/중첩 집계의 합산 초과, 경계값, 설정 변경/재설정/재시작, 오류 전파,
  다른 bucket family와 reduce 경로를 검증해야 한다.
- 이 변경은 C02/C06 진행 중 부분 수정이다. 각 구현 단위를 완료하기 전에
  전체 non-plugin 반복 벤치마크를 반드시 실행한다. 최초 v0.6.0 고정 기준의
  topology throughput >=95%, 각 scenario mean/p95/p99 <=105%를 독립 적용한다.
  동일 실제 workload/durability/security/resource 설정, 실행 파일 식별,
  별도 build directory와 원본 발표 증거 보존을 요구한다. 직전 릴리즈와 고정
  OpenSearch 비교도 유지하며 기준선 재설정이나 다른 개선으로 상쇄하지 않는다.
  새 release 서버/live/전체 gate는 아직 실행하지 않았다. 최신 측정 dada6399 FAIL,
  정식0/40, ledger 비어 있음, 릴리즈 보류다.

#### C06 날짜 버킷의 collector 트리 공유 예산

- 2026-09-09: 날짜 collector별65535 지역 검사를 BucketAllocationBudget으로
  교체했다. 한 직렬 collector 트리의 문서/hit/root/하위 집계가 동일한 객체를
  참조한다. Cell 기반 누적값과 고정 limit을 사용하며 재귀 호출에서 초기화하지
  않는다. 합산은 포화 연산으로 overflow 우회를 막고, 초과 후 consume(0)으로
  실패 상태를 지울 수 없다. 외부 collector 진입 wrapper에서 기본65535를 만든다.
- 날짜 생성 helper의 희소/고정 간격 두 사전 검사에서 공유 예산을 소비한다.
  두 번째 형제 집계가 누적 한도를 넘으면 그 집계의 결과 Vec/JSON을 만들기 전에
  거부한다. 기존 typed TooManyBuckets 오류를 유지한다. 내부 core plugin 표현의
  global/terms 등 재귀 경로도 예산을 전달하며 외부 플러그인 지원으로 집계하지 않는다.
  기본 오류/구조를 유지하는 열 함수의 서명과 호출 변경은 syn AST 기반132개 삽입으로
  수행했다. 재실행 방지된 도구는 target/core-replacement-c05/fallible-rewrite의
  src/bin/bucket-budget.rs이며 runtime 의존성을 추가하지 않았다.
- **아직 날짜 출력 할당의 collector 트리별 보호다.** terms/range 등 다른 family의
  부모 버킷, 중간 count map/문서 배열, 샤드 간 전체 요청 합계와 최종 reduce는
  이 예산에 포함되지 않는다. 동적 search.max_buckets도 아직 연결하지 않았다.
  참조 MultiBucketConsumerService의 최종 reduce bucket count와 중간 자원 breaker를
  같은 개념으로 취급하지 않는다. 동일 key의 샤드 병합을 무조건 합산하지 않는다.
  특히 finalize_terms_aggregation_value는 중간 carrier를 보존하면서 visible만
  size로 자른다. 이후 버려질 부모 아래 날짜 버킷도 현재 할당 예산에는 포함된다.
  따라서 현재 보호를 OpenSearch search.max_buckets와 정확히 같은 허용 범위라고
  주장하지 않는다. 높은 cardinality/작은 size/하위 집계에서 최종 결과가 한도
  이내인 경우를 참조와 대조하고, 중간 메모리 breaker와 최종 개수 제한을 분리하는
  검증이 남는다. terms의 모든 중간 key를 기본65535로 제한하는 확장은 하지 않는다.
- 제한 실행 두 테스트 성공, 종료0,1.30초다. 주소 공간1GiB/CPU20초/wall30초와
  종료 유예2초를 적용했다. 두 날짜 집계 각각2개에서 limit3 거부/limit4 허용을
  문서 및 hit의 두 정렬 모드/배경 유무, 일반/global 조합에서 검사했다.
  engine.search 여섯 요청은 일반 형제/global 하위 형제/terms의 서로 다른 두 부모
  아래 각각32768개 날짜 버킷을 size0/10으로 생성할 때 합계65536에서 거부했다.
  이는 실제 서버 HTTP나 다중 샤드 reduce 검증이 아니다.
  `target/core-replacement-c05/shared-date-budget-bounded.log` SHA-256
  `3aac716b608e97133f03a36186a823b4281c48bb20a992ae06f4d905bc09ed56`.
- engine 전체 unit878/878(23.02초), concurrent7/7(17.05초), merge4/4(3.46초),
  multi-field9/9(0.47초), 총898개 성공, 실패/skip/filter0, 종료0, 빌드20.55초다.
  단위 테스트에는 예산 경계값/실패 유지/독립 객체/zero/overflow 검사도 포함한다.
  nightly/RUSTFLAGS=-Awarnings/jobs2/incremental0/DEV_DEBUG=0/TEST_DEBUG=0,
  비최적화 직렬 실행이다. `target/core-replacement-c05/shared-date-budget-engine-full.log`
  SHA-256 `008498cc27dd57c23ec080a8bdf43e2ade6ed3ec394feefcccdd0276bcb8ea85`.
  lib.rs SHA-256 `17a295311b897a87f8d8b6be8850c203a0feea00366400071c49b28b6c2e2312`,
  bucket_budget.rs SHA-256 `12b252d0950a39f85eb9b0ebe2996861dc810ee284470f126d10441311b4afc2`.
- 같은 프로파일 node lib650/650(11.73초), bin459/459(17.53초), 총1109개 성공,
  실패/skip/filter0, 종료0, 빌드1분05초다. 이번 engine/node 합계2007개 성공이며
  DSL 소스는 바꾸거나 재검증하지 않았다. 모든 검증 세션은 정상 종료됐다.
  `target/core-replacement-c05/shared-date-budget-node-full.log` SHA-256
  `e82fe2faf94a7dd76f3ebe1226b61f41cce44e6846474d38dcc52e11bcf7f18d`.
  최종 소스 해시는 위 기록과 같고 git diff --check 성공이다.
- 다음 작업은 다른 bucket family의 생성 전 차감, 신뢰된 동적 설정 snapshot,
  중간 자원 제어와 최종 reduce 제한의 분리다. 트리별 보호를 전체 요청 보호로
  간주하지 않는다. C06 각 구현 단위 완료 전 전체 non-plugin 반복 벤치마크를
  실행하고, 최초 v0.6.0 고정 누적 기준의 topology throughput >=95% 및 각 scenario
  mean/p95/p99 <=105%를 독립 적용한다. 동일 실제 workload/durability/security/resource,
  실행 파일 식별/별도 build directory/원본 발표 증거 보존, 기준선 재설정·개선 상쇄
  금지를 유지한다. 새 release 서버/live/전체 gate는 미실행, 최신 dada6399 FAIL,
  C02/C06 미완료, 정식 수락0/40, ledger 비어 있음, 릴리즈 보류다.

#### C06 실제 REST fallback pipeline 순서 회귀 검증

- 2026-09-09: native-bucket-pipeline-candidate의 별도 source/build에서 release
  서버를 빌드했다(7분45초, 종료0). 실행 파일 SHA-256은
  `78ed990c315be187f3fb3d4c22111a98ef1ea16a4134ea32e0137a49c0b26530`이다.
  source.sha256 manifest 해시는
  `7f9b760522351246efe5a82346416f5777a5733ddf251a61d9d6e624541aa4f5`이며,
  빌드 전후 검증했다. 이전 dada6399의 실험용 FST 패치는 포함하지 않는다.
- 실제 OpenSearch 3.7.0-SNAPSHOT과 전체 projected core 및 추가 fixture를 실행해
  1808건 성공, 4건 실패, skip0을 확인했다. count probe 성공, 실행 파일/fixture
  불변 검증도 성공이다. 이는 기능 비교이며 성능 기준 OpenSearch 2.19와 구분한다.
  `target/core-replacement-c06/native-bucket-pipeline-live/execution.json` SHA-256
  `a6c69a3480351fd34be38bc85e349cd3252494e8efaf1929b47a0105346a3156`.
- 실패는 새 pipeline-selection-compat fixture의 global 집계 네 요청이다.
  단일/복수 인덱스, size0/10 모두 선택된 terms bucket은 맞지만 이름이 먼저 오는
  a_total은 -0.0, 뒤에 오는 z_total은 기대값2/4였다. native 내부 API 테스트만으로
  REST fallback 경로의 호환성을 증명할 수 없음을 확인했다. 해당 report SHA-256은
  `dc8e41c49c47cf1c2aa6a3b33ee93b9199f699659a458057c2e676929f902c93`이다.
- build_search_aggregations가 일반 집계를 먼저 수집하고 지원하는 일곱 bucket-metric
  pipeline을 나중에 계산하도록 순회 순서를 수정했다. 선택된 terms 결과를 사용하며
  요청 복제나 집계 본문 중복은 없다. 일반 pipeline 의존성 정렬, 모든 buckets_path,
  fallback 버킷 한도 구현까지 완료했다는 뜻은 아니다.
- 일곱 종류의 plain/global 직접 테스트와 실제 in-process REST 여덟 요청을 추가했다.
  node 전체 lib654/654(11.74초), bin459/459(17.33초), 총1113건 성공,
  실패/skip/filter0, 종료0이다. nightly/RUSTFLAGS=-Awarnings/jobs2/incremental0/
  DEV_DEBUG=0/TEST_DEBUG=0 비최적화 직렬 실행이다. 로그
  `target/core-replacement-c06/fallback-pipeline-order-node-full.log` SHA-256
  `a58c688977cb9e18815190ae292a72078269ad1f8e978b238ac3b255791ad410`.
  standalone_runtime.rs SHA-256
  `df0e92bb1f2bfa1ee65eed8484dbfb6c5f9787095d83e6a620f39323bd9ad04f`.
- 실패 후보/로그를 보존하고 수정 후보를 별도 source/build에서 다시 빌드한 뒤 전체
  live 검증을 재실행한다. 통과 후 전체 non-plugin 반복 성능 suite를 실행하며 그 전에는
  구현 단위를 완료 처리하지 않는다. 최초 v0.6.0 고정 누적 기준 topology 처리량95%
  이상, 각 scenario mean/p95/p99 지연105% 이하를 독립 적용한다. 동일 실제 설정과
  실행 파일 식별, 원본 증거 보존, 기준선 재설정/개선 상쇄 금지도 유지한다.
  현재 새 성능 gate는 미실행, 최신 dada6399 FAIL, C02/C06 미완료, 정식 수락0/40이다.

#### C06 최종 출력 버킷 합산 검사

- 2026-09-09: finalize_checked_aggregation_response를 추가해 native 최종 응답의
  여덟 진입 지점에서 기존 finalize 후 기본65535 출력 한도를 검사하고 오류를
  전달한다. 재귀 중간 finalize에 독립 한도를 반복 적용하지 않는다.
  DSL 집계 종류를 기준으로 visible buckets의 배열/키 기반 객체를 세고,
  다중 버킷의 하위 집계 및 global/filter 등 단일 버킷 wrapper의 하위 집계를
  같은 누적값으로 순회한다. 단일 버킷 wrapper 자체는 다중 버킷 수에 더하지 않는다.
  내부 _merge_buckets와 metric/top_hits 문서 payload는 세지 않는다.
- 이 검사는 최종 출력 상한 보호다. 생성 전 할당/중간 메모리 breaker를 대체하지
  않으며 앞서 추가한 날짜 공유 할당 보호도 제거하지 않았다. terms.size로 버려질
  부모 아래 날짜 생성이 중간 한도를 소모하는 기존 의미 차이는 아직 남아 있다.
  참조 InternalTerms.java는 최종 선택에서 제거한 bucket의 하위 개수를 차감한다.
  InternalAggregations.topLevelReduce는 기본 reduce 후 pipeline reduce를 실행한다.
  현재 finalize 이후 검사만으로 참조의 pipeline 이전 한도 적용 순서까지 같다고
  주장하지 않는다. pipeline 경계, 원격 coordinator/reduce, 동적 설정, 모든 family의
  생성 전 자원 제어는 계속 미완료다.
- 추가 테스트는 terms.size1의 visible 부모1+날짜2=3을 허용하고 limit2에서
  거부하며, carrier에 남은 두 번째 부모는 세지 않는지 검사한다. keyed filters
  아래 terms의 합산, global 자체 미가산, metric 이름/값이나 top_hits 문서 안의
  buckets를 집계로 오인하지 않는지도 검사한다. engine.search에서는 두 range
  집계 각각32768개, 합계65536개를 단일/두 인덱스 x size0/10 네 요청에서 거부한다.
  이는 engine API 결과이며 실제 HTTP/분산 클러스터 상호운용 증거는 아니다.
- 첫 제한 실행은 선택/carrier 테스트 성공 후 engine 테스트에서 주소 공간1GiB
  제한에 걸려 할당 실패/종료134였다. 무제한 실행하지 않았다.
  `target/core-replacement-c05/final-bucket-budget-bounded.log` SHA-256
  `c38abd79a7d6bde9f28784a7ad5a63d0c199211ed1813c22d1e4a78bb0f2b406`.
  /usr/bin/time 계측 시도는 도구 부재로 종료127이며 별도 bounded-2g.log에 보존했다.
- Python subprocess/resource 계측과 주소 공간2GiB/CPU35초/wall45초/종료 유예2초의
  재실행은 세 테스트 모두 성공, 종료0,2.28초였다. 자식 최대 RSS233376KiB를
  기록했다. 첫 실패를 호스트 OOM으로 단정하거나 두 실행의 주소 공간 설정이 같다고
  보고하지 않는다. `target/core-replacement-c05/final-bucket-budget-bounded-2g-measured.log`
  SHA-256 `810197eda799400413408c1b2339efdd0c8bf31336d1ae6f1b54a30cdf2df931`.
  lib.rs SHA-256 `3cd7dcae6b72eb4ded658440588c61f242d82df9ee6c6bd5fdddaf3763824670`.
- engine 전체 unit881/881(25.76초), concurrent7/7(16.04초), merge4/4(3.32초),
  multi-field9/9(0.49초), 총901개 성공, 실패/skip/filter0, 종료0, 빌드20.41초다.
  nightly/RUSTFLAGS=-Awarnings/jobs2/incremental0/DEV_DEBUG=0/TEST_DEBUG=0,
  비최적화 직렬 실행이다. `target/core-replacement-c05/final-bucket-budget-engine-full.log`
  SHA-256 `e97d082d65e99004124776cb53214510a39c64aa1b474267ee1f1972d4630b0c`.
- 같은 프로파일 node lib650/650(11.61초), bin459/459(17.61초), 총1109개 성공,
  실패/skip/filter0, 종료0, 빌드1분05초다. engine/node 합계2010개 성공이다.
  `target/core-replacement-c05/final-bucket-budget-node-full.log` SHA-256
  `7d9007088428997968c8ace7b7ce72acb63d75f34131a1c9528c1029d3d74c1a`.
  모든 검증 세션은 종료됐고 최종 lib.rs 해시는 위 기록과 같다.
  git diff --check 성공, 새 서버 빌드/태그/커밋/배포는 실행하지 않았다.
- C06 구현 단위 완료 전 전체 non-plugin 반복 벤치마크를 실행한다. 최초 v0.6.0
  고정 누적 기준 topology throughput >=95%, 각 scenario mean/p95/p99 <=105%를
  독립 적용하고 동일 실제 workload/durability/security/resource, 실행 파일 식별,
  별도 build directory/원본 증거 보존을 요구한다. 기준선 재설정이나 개선 상쇄는
  허용하지 않는다. 새 release 서버/live/전체 gate는 미실행, 최신 dada6399 FAIL,
  C02/C06 미완료, 정식 수락0/40, ledger 비어 있음, 릴리즈 보류다.

#### C06 선택된 버킷에 대한 pipeline 계산

- 2026-09-09: 기존 finalize는 pipeline을 먼저 계산한 후 terms.size/하위 집계를
  finalize했고, pipeline_bucket_surface도 visible보다 _merge_buckets를 우선했다.
  따라서 최종 선택에서 제외된 버킷이 sum_bucket 등의 입력에 포함될 수 있었다.
  로컬 OpenSearch InternalTerms의 최종 size 선택, InternalAggregations.topLevelReduce의
  기본 reduce 후 pipeline 처리, BucketMetricsPipelineAggregator.doReduce의
  getBuckets() 순회를 대조했다. 실행 중인 OpenSearch와의 HTTP 비교 증거는 아니다.
- 기존 finalize의 bucket 선택/하위 finalize를 pipeline 계산 앞으로 옮겼다.
  구조를 syn AST로 확인해 세 statement 순서를 바꿨으며 다른 함수의 순서는
  변경하지 않았다. 도구는 target/core-replacement-c05/fallible-rewrite의
  src/bin/pipeline-order.rs다. pipeline_bucket_surface는 이제 buckets가 있으면
  그것을 우선하고, 없는 경우에만 _merge_buckets로 fallback한다. 빈 visible 배열을
  내부 carrier로 채우지 않으며 실제 merge carrier 자체는 보존한다.
- 신규 테스트는 native terms와 core 표현 terms 각각 size1에서 selected doc_count2,
  discarded doc_count1일 때 sum_bucket이3이 아니라2인지 검사한다. pipeline 이름을
  원본 terms보다 앞/뒤에 두어 두 경우를 검사하고, visible1/carrier2 보존도 확인한다.
  keyed visible, 빈 visible, carrier-only 입력도 검사한다. 이는 finalize helper 검증이며
  이 새 시나리오의 실제 서버 HTTP/Java 상호운용을 검증했다고 확대하지 않는다.
- engine 전체 unit882/882(25.24초), concurrent7/7(16.78초), merge4/4(3.39초),
  multi-field9/9(0.49초), 총902개 성공, 실패/skip/filter0, 종료0, 빌드1분23초다.
  nightly/RUSTFLAGS=-Awarnings/jobs2/incremental0/DEV_DEBUG=0/TEST_DEBUG=0,
  비최적화 직렬 실행이다. `target/core-replacement-c05/pipeline-selection-engine-full.log`
  SHA-256 `86736455bcdeb24c3b062f07e6d004efa50a9214cdaa999977c3e251650c3567`.
  lib.rs SHA-256 `56c25ec79e7c837e6c4b38c2a2a58afd4967d81a42bb00f6fa0b227ac8063d33`.
- 같은 프로파일 node lib650/650(11.72초), bin459/459(17.39초), 총1109개 성공,
  실패/skip/filter0, 종료0, 빌드1분06초다. engine/node 합계2011개 성공이다.
  `target/core-replacement-c05/pipeline-selection-node-full.log` SHA-256
  `7fd3f7d57b766673973f8b2bfad65e536dcc046a6477c545ca7a3c9c18946f14`.
  모든 검증 세션은 종료됐고 최종 소스 해시는 위 기록과 같다.
  git diff --check 성공, 새 서버 빌드/태그/커밋/배포는 실행하지 않았다.
- 최종 한도 검사는 여전히 전체 finalize 뒤에 있다. pipeline 전 한도 적용 순서,
  pipeline 간 의존성 순서 전체, 중간 자원 breaker와 동적 search.max_buckets는
  계속 미완료다. 일부 pipeline 입력 의미 수정만으로 C06을 완료 처리하지 않는다.
  각 구현 단위 완료 전 전체 non-plugin 반복 벤치마크, 최초 v0.6.0 고정 누적 기준
  topology throughput >=95%와 각 scenario mean/p95/p99 <=105% gate가 필수다.
  동일 실제 workload/durability/security/resource 및 실행 파일 식별/별도 build directory,
  원본 발표 증거 보존, 기준선 재설정·개선 상쇄 금지를 유지한다.
  새 release 서버/live/전체 gate는 미실행, 최신 dada6399 FAIL, C02/C06 미완료,
  정식 수락0/40, ledger 비어 있음, 릴리즈 보류다.

#### C06 native pipeline 전 누적 한도 적용

- 2026-09-09: native finalize를 버킷 선택/하위 선택과 pipeline 실행으로 분리했다.
  checked 진입점은 전체 visible tree 선택, 누적 한도 검사, pipeline 실행 순서다.
  하위 선택 helper 세 곳은 pipeline을 실행하지 않는다. 한도를 통과한 뒤에는
  visible 배열/키 기반 버킷 및 single-bucket wrapper만 재귀 순회한다.
  선택에서 제외된 carrier 버킷에 pipeline 결과를 생성하지 않는다.
- 단계 분리만으로 충분하지 않았다. 문서/hit collector의 선행 pipeline 계산 두
  루프와 중간 merge의 하위 pipeline 호출19곳을 추가 확인해 제거/선택 전용으로
  바꿨다. 한도 없이 selection+pipeline을 수행하던 전체 finalize wrapper도 제거했다.
  pipeline 실행 helper의 production 호출은 checked 진입점과 visible 하위 재귀에
  한정된다. 이는 이 native engine 경로의 감사 결과이며 node fallback/원격
  coordinator 전체가 같은 제한을 적용한다고 확대하지 않는다.
- 변경은 syn AST 도구 pipeline-phases.rs, defer-collector-pipelines.rs,
  defer-merge-pipelines.rs로 대상 구조와 호출 개수를 확인해 적용했다.
  도구 위치는 target/core-replacement-c05/fallible-rewrite/src/bin이며 runtime
  의존성은 추가하지 않았다. lib.rs SHA-256
  `5d4bc12411958347ac2ee966b45f9f0b0314353f5768ab7ce8fd3a0e3bd65beb`.
- 단계 분리 테스트는 global/filters/terms의 전체 누적 한도에서 하나 모자라면
  어느 visible 하위 집계에도 computed pipeline 값이 생성되지 않는지, 경계값이면
  selected terms의 doc_count2를 계산하는지 검사한다. carrier의 pipeline 미실행도
  확인한다. 문서 및 두 정렬 모드 hit collector는 finalize 전 pipeline 결과가
  없고 finalize 후에만 결과가 생기는지 검사한다.
- 실제 engine.search 여덟 요청은 단일/두 인덱스 x size0/10 x 일반/global 하위
  조합이다. 각 인덱스의 a2/b1 문서에서 terms.size1을 적용하고 이름이 앞/뒤인
  두 sum_bucket이 각각2 또는4를 반환하는지 확인했다. 이 시나리오는 collector
  선행 계산 제거 단계의 전체905개 회귀 테스트에서 통과했다.
  `target/core-replacement-c05/pipeline-deferred-engine-full.log` SHA-256
  `e4a4b156ecc5aacc814abfebdf1321337719b0135de152a6cf5d1c20e23af6d6`.
  그 이전 단계 분리 전체903개 성공 로그 pipeline-phases-engine-full.log도 보존한다
  (SHA-256 `cfe2d2b98831e2d450758c4ecd2564eb366bab36f3b2171cc9a3ca6b88a92cbc`).
- 최종 변경에는 중간 merge 두 번 뒤에도 pipeline 값이 없고, limit0 거부 시에도
  계산되지 않으며 limit1 허용 시에만 합계2가 되는 검사도 추가했다.
  실제 HTTP/Java 상호운용 증거는 아직 아니며 동적 search.max_buckets,
  pipeline 간 의존성 순서 전체, 중간 메모리 breaker, 날짜 할당 예산과 최종 선택의
  의미 차이는 계속 남아 있다. 기존 날짜 할당 보호를 제거하거나 안전성을 면제하지 않는다.
- 최종 engine 전체 unit886/886(25.56초), concurrent7/7(16.66초), merge4/4(3.26초),
  multi-field9/9(0.48초), 총906개 성공, 실패/skip/filter0, 종료0, 빌드1분24초다.
  nightly/RUSTFLAGS=-Awarnings/jobs2/incremental0/DEV_DEBUG=0/TEST_DEBUG=0,
  비최적화 직렬 실행이다. 중간 merge 및 실제 검색 여덟 요청도 최종 상태에서
  다시 통과했다. `target/core-replacement-c05/pipeline-gated-engine-full.log` SHA-256
  `b471da4da8ab18b8cd2cca55d987b89d9cdbba0c17d34574a693fcfd32a1ab45`.
- 같은 프로파일 node lib650/650(11.77초), bin459/459(17.78초), 총1109개 성공,
  실패/skip/filter0, 종료0, 빌드1분05초다. 최종 engine/node 합계2015개 성공이다.
  `target/core-replacement-c05/pipeline-gated-node-full.log` SHA-256
  `3f4c9c55e527c20b741c574f08fe978d061d5a113b30d729d8c84da831137978`.
  모든 검증 세션은 종료됐다. 최종 소스 해시는 위 기록과 같고 git diff --check 성공,
  새 서버 빌드/태그/커밋/배포는 실행하지 않았다.
- 각 C06 구현 단위 완료 전 전체 non-plugin 반복 벤치마크를 실행한다.
  최초 v0.6.0 고정 누적 기준 topology throughput >=95%, 각 scenario mean/p95/p99
  <=105%를 독립 적용하며 동일 실제 workload/durability/security/resource와 실행 파일
  식별/별도 build directory/원본 발표 증거 보존, 기준선 재설정·개선 상쇄 금지를
  유지한다. 새 release 서버/live/전체 gate는 미실행, 최신 dada6399 FAIL,
  C02/C06 미완료, 정식 수락0/40, ledger 비어 있음, 릴리즈 보류다.

#### C06 버킷 설정 변경의 값 검증

- 2026-09-09: cluster settings PUT에서 search.max_buckets를 저장하기 전 원본
  persistent/transient와 병합 후 두 영역 모두를 검사한다. 다른 영역의 유효한 값에
  가려진 잘못된 값도 거부한다. dotted/nested 두 표현을 원본에서 먼저 검사하여
  잘못된 object 값이 평탄화 중 사라지는 경우를 막았다. 실패는 상태400과
  illegal_argument_exception이며 기존 설정을 바꾸기 전에 반환한다.
- 현재 허용 범위는0..i32::MAX의 JSON 정수 또는 Rust i32 parser가 받는 ASCII
  정수 문자열이다. null 초기화를 허용한다. 음수/범위 초과/실수/bool/array/object,
  빈 문자열/소수 문자열/공백 포함 문자열은 거부한다. 로컬 OpenSearch의
  MultiBucketConsumerService.MAX_BUCKET_SETTING과 Setting.parseInt의 범위를 대조했다.
  Java의 비ASCII 숫자 문자열 호환성 및 정확한 오류 문구/메타데이터 동등성은 남아 있다.
- 테스트는 잘못된 값15개 x persistent/transient x dotted/nested의60개 PUT에서
  동반한 cluster.info.update.interval까지 포함해 상태가 그대로인지 검사한다.
  허용 경계/문자열/null8종 x 두 영역의 seed/update32개 PUT도 통과했다.
  유효한 dotted 값과 잘못된 nested 값이 함께 있을 때 검증을 우회하지 않는지도
  helper에서 검사했다. 이는 동일 요청의 부분 저장 방지 검증이며 동시 변경 간
  linearizability나 재시작/클러스터 전파를 증명한 것은 아니다.
- node 전체 lib652/652(11.80초), bin459/459(17.31초), 총1111개 성공,
  실패/skip/filter0, 종료0, 빌드51.74초다. nightly/RUSTFLAGS=-Awarnings/jobs2/
  incremental0/DEV_DEBUG=0/TEST_DEBUG=0, 비최적화 직렬 실행이다.
  `target/core-replacement-c05/bucket-setting-validation-node-full.log` SHA-256
  `319d8c3f11a28f89baae5990954784a1ab3be70c17da870091cb0df631f94001`.
  standalone_runtime.rs SHA-256
  `b5c391ff71fb1843072b6d4ba0593d89ffc2e3de793b02e2b0dfcbfb63303ba1`.
- **값 저장 검증은 동적 실행 한도 구현이 아니다.** native 한도는 아직 기본65535이며,
  신뢰된 설정 snapshot을 검색/하위 집계/reduce에 전달하는 작업이 남아 있다.
  검색 본문에서 한도를 올릴 수 있게 하지 않는다. fallback/원격 경로, 복원된 설정
  검증, 중간 메모리 보호도 미완료다. engine/DSL 소스는 이번에 바꾸거나 재검증하지
  않았으며 새 서버/live/전체 성능 gate는 실행하지 않았다. 모든 검증 세션은 종료됐고
  git diff --check 성공이다. 태그/커밋/배포는 하지 않았다.
- 각 구현 단위 완료 전 전체 non-plugin 반복 벤치마크와 최초 v0.6.0 고정 누적
  topology throughput >=95%, 각 scenario mean/p95/p99 <=105% gate를 유지한다.
  동일 실제 workload/durability/security/resource, 실행 파일 식별/별도 build directory/
  원본 증거 보존, 기준선 재설정·개선 상쇄 금지가 필수다. 최신 dada6399 FAIL,
  C02/C06 미완료, 정식 수락0/40, ledger 비어 있음, 릴리즈 보류다.

#### C06 fallback 수정 후보의 전체 live 재검증

- 2026-09-09: `target/core-replacement-c06/fallback-pipeline-candidate/source`와
  별도 build에서 수정 후보 release 빌드 성공(7분42초, 종료0). nightly ad3a598ca,
  RUSTFLAGS=-Awarnings/jobs2/incremental0/--locked/standalone-runtime을 사용했다.
  실행 파일 SHA-256
  `a1a5372713c805558a694b9fa779ed22632aff7781bf529d29c30f6980542dda`.
  source.sha256 manifest 해시
  `eec7ecebe35cbd5719781a434caea20c1412aae7860e4f6f38700169f60e4186`이며
  빌드 전후 전체 파일 검증 성공이다. candidate-build.log 해시는
  `61ac461ad00b759555463719f5008ccdcecc104aa92267bde3b86634ad97830e`.
- 같은 전체 live 범위를 새 디렉터리에서 재실행해1812/1812 성공, 실패/skip0,
  count probe 성공, binary/fixtures unchanged=true, 종료0을 확인했다.
  이전 실패 네 요청을 포함한 pipeline-selection-compat8/8이 모두 통과했다.
  기능 참조는 OpenSearch3.7.0-SNAPSHOT이며 운영/혼합 노드 전체 인증은 아니다.
  `target/core-replacement-c06/fallback-pipeline-live/execution.json` SHA-256
  `9fc60c1945a780ec3a89a572c6b0c8f2579ab6d3065f2af522b49c4593e80a3c`.
  pipeline-selection-compat-report.json 해시는
  `7f27050abac2c50bf99f114000edc0525c71f82cfc954d20d76066ee2a4b1731`.
- 빌드/live 프로세스 종료 후 위 실행 파일을 고정하여
  tools/run_core_performance_gate.py로
  `target/core-replacement-c06/fallback-pipeline-repeated-full`에 전체 non-plugin
  반복 측정을 실행한다. 기준선db244133, 최초 발표 보고서d2fdabfa 불변을 확인했다.
  기준선/후보/고정 OpenSearch2.19/역순 반복, 각 단일/3노드와7연산 전체를 유지하며
  각 실행의 v0.6.0 누적5% 판정 및 paired/기준선 변동을 모두 보존한다.
  이 기록 시점에는 성능 판정 전이며 완료/승격/릴리즈 승인을 의미하지 않는다.

#### C06 a1a53727 전체 반복 성능 결과: FAIL

- 2026-09-09: 위 후보의 전체 non-plugin 반복 gate 완료. 여섯 하위 실행 모두 종료0,
  단일/3노드 총12개 실행의 요청 오류0, 1096.14초(18분16초), 실행 입력 불변 검증
  true, 인프라 error 없음. 수치 판정 false로 최종 종료1이며 정상 완료/승격은 차단한다.
  최신 전체 측정은 이제 dada6399가 아니라 **a1a53727 FAIL**이다.
- 최초 공개 v0.6.0의44개 독립 지표 중 후보01은25개 통과/19개 초과,
  후보04는33개 통과/11개 초과다. 같은 실행 내 paired v0.6.0 대비는 각각
  29개 통과/15개 초과, 32개 통과/12개 초과다. 개선으로 초과를 상쇄하지 않는다.

| 실행 / 토폴로지 | 후보 처리량(req/s) | 최초 v0.6.0 대비 변화 | OpenSearch 대비 배수 |
| --- | ---: | ---: | ---: |
| 01 / 단일 | 720.2500 | -3.0634% | 2.5031 |
| 01 / 3노드 | 885.6080 | -4.9134% | 7.7671 |
| 04 / 단일 | 729.7028 | -1.7911% | 2.4957 |
| 04 / 3노드 | 892.7646 | -4.1450% | 7.8933 |

최초 공개 v0.6.0 대비 지연 초과 목록(%, 양수는 악화; '-'는 해당 회에서 한도 이내):

| 지표 | 후보01 | 후보04 |
| --- | ---: | ---: |
| single-node/ranking/mean | 5.1726 | - |
| single-node/ranking/p95 | 5.0758 | - |
| single-node/sort_filter/mean | 6.4144 | - |
| single-node/sort_filter/p95 | 7.5121 | - |
| single-node/refresh/mean | 9.6940 | 6.8393 |
| three-node/write/p95 | 5.3542 | - |
| three-node/lexical/p99 | 11.8166 | 13.4147 |
| three-node/ranking/mean | 5.5668 | - |
| three-node/ranking/p95 | 6.8207 | 7.4403 |
| three-node/ranking/p99 | 13.2293 | 11.0692 |
| three-node/facet/mean | 6.0791 | - |
| three-node/facet/p95 | 7.4718 | - |
| three-node/facet/p99 | 16.7784 | 8.4049 |
| three-node/sort_filter/p95 | 7.6357 | 5.5484 |
| three-node/sort_filter/p99 | 16.9460 | 14.9366 |
| three-node/nested/p99 | 7.1361 | 12.7817 |
| three-node/refresh/mean | 18.5680 | 16.7146 |
| three-node/refresh/p95 | 14.4784 | 15.6313 |
| three-node/refresh/p99 | 9.8940 | 15.0878 |

- 기준선00 자체의3노드 ranking p99+5.4265%, 기준선05의단일 refresh p99+6.7502%
  변동도 실패로 보존한다. 후보 초과를 전부 환경으로 면제하거나 유리한 회만 고르지 않는다.
  3노드 refresh 평균은 공개8.385483ms -> 후보9.942497/9.787081ms다.
- OpenSearch2.19 처리량은02 단일287.7411/3노드114.0204, 03 단일292.3808/
  3노드113.1047이다. 모든 시나리오의 평균/p95/p99 원시 값과 paired 비교도
  result.json에 보존했다. dev 내구성의60초 혼합 부하이며 운영 대체 성능 주장이 아니다.
- `target/core-replacement-c06/fallback-pipeline-repeated-full/result.json` SHA-256
  `889ad0d957aba8d8f7b55c237ebed68e9ec6e87df26ce7d332904169318b1c6f`.
  plan.json SHA-256
  `b3ce1d83040f75a7fe172db941d81e97d4a4f197ac0345a6faa52187512386fd`.
- 다음 진단은 같은 후보의3노드 혼합 부하 CPU 표본에서 refresh/segment 생성/병합 비용을
  확인하는 것이다. dada6399는 FST 실험 패치가 있는 다른 후보이므로 차이를 이번
  fallback 수정 하나에 귀속할 수 없다. 소스 변경의 인과 관계와 최적화 불가능성은
  아직 입증하지 못했으므로 ledger는 비어 있다. 버킷 안전 제어나 오류 전파를 제거해
  수치만 회복하지 않는다. 최적화 후에는 전체 non-plugin suite를 다시 실행하며 최초
  v0.6.0 누적5% 기준은 그대로다. 정식 수락0/40, C02/C06 미완료, 릴리즈 보류다.

#### C06 a1a53727 CPU 진단과 다음 비교 단위

- 전체 gate 종료 후 같은 후보의3노드 혼합 부하45초에서499Hz CPU 진단을 실행했다.
  perf/matrix 종료0, 요청 오류0, 실제 서버 실행 파일 전후 일치, 약19K 표본,
  lost samples0. 명령상20초 capture의 전후 관측26.51초에는 시작/종료 비용도
  포함된다. 부하 생성기 표본이 분모에 포함되며 off-CPU 지연을 설명하지 못한다.
- new_field inclusive3.64%/self3.25%, FST Registry drop1.75%/1.67%,
  SegmentWriter::finalize7.32%/0.61%, IndexMerger::write12.59%/1.20%,
  write_fast_fields inclusive5.57%, simple bucket aggregation4.48%/2.34%,
  memcmp self3.95%가 관측됐다. 이전 dada6399의997Hz와 표본 비중 차이를
  속도 향상/악화의 정량 증거로 사용하지 않는다. 동일 소스의 의존성 차이를
  분리한 비교가 필요하며 이번 fallback 수정의 인과 효과는 아직 미확정이다.
- 증거: `target/core-replacement-c06/fallback-pipeline-cpu/diagnostic.json`
  SHA-256 `f92485a7fa9c0ab51a07cabe919830436f010c427ae7963d2cb0ca60f39acd11`.
  self-report.txt SHA-256
  `ad98a9f9a9ebcbd9f2a299a2d20328939bac47e5f1af87b76ca6e9e88061680a`,
  selected-callers.txt SHA-256
  `ceb456b08d4de394d24668879bd085ede70588af0e0a362284fea3ba02293be0`.
- 다음 단위: 기존 FST 실험의 테스트/Miri 근거와 패치를 다시 검토하고,
  a1a53727과 동일한 기능 소스에 그 의존성 변경만 적용한 별도 후보를 만든다.
  기존 measured source/build는 변경하지 않는다. 기능 회귀 및 메모리 안전 검증 후
  동일 조건 비교로 인과 효과를 확인한다. 국소 진단으로 완료를 선언하지 않으며
  **해당 단위 완료 전 전체 non-plugin 반복 벤치마크를 반드시 재실행**한다.
  최초 v0.6.0의 토폴로지 처리량95% 이상/각 시나리오 mean,p95,p99 지연105%
  이하를 독립 판정하고 paired/기준선 변동/고정 OpenSearch 비교도 유지한다.
  이것은 아직 실행하지 않은 다음 실험 계획이며 FST 패치 승격이나 실패 면제가 아니다.
- 현재 모든 빌드/live/전체 gate/CPU 진단 프로세스 종료, 사용자 컨테이너 유지.
  최신 전체 gate a1a53727 FAIL, 단위 수락0/40, ledger 비어 있음, 릴리즈 보류.

#### C06 최신 기능 소스에서 FST 의존성 분리 후보 검증

- 2026-09-09: 이전 회차는 fallback4건 수정/live1812건 통과/전체 성능 FAIL과 CPU
  진단을 완료한 progress다. 이어서
  `target/core-replacement-c06/fst-isolated-candidate/source`에 a1a53727의 고정
  source를 복사했다. crates 전체 diff 일치이며 root Cargo.toml의 patch.crates-io와
  Cargo.lock의 tantivy-fst source/checksum 제거, vendor 추가만 다르다.
  루트 작업 트리 의존성이나 기존 측정 source/build는 수정하지 않았다.
- vendor의 registry.rs 해시는 기존 Miri 검증 대상과 동일한
  `9f332316ba58f1f37d9b63e5c8da789ac6d3e6ad4bdf47019c4f95f37146b3f0`이다.
  원본 registry package와 비교한 라이브러리 소스 차이도 이 한 파일뿐이다.
  행 전체 초기화 후 flag 설정, 초기화된 행만 접근/단일 해제, checked 크기 곱,
  영 차원 거부를 검토했다. 기본 BuilderNode는 빈 Vec만 만들어 행 초기화 중
  별도 heap 할당을 요구하지 않는다. 동시 접근은 &mut self로 제한된다.
- 기존 strict-provenance Miri7건 성공 로그
  `target/core-replacement-c05/fst-lazy-experiment/direct-miri.log` SHA-256
  `54f49fe86749fdc03b03fafbbeff36f10543866b44252f731fd68251c6f5991e`를 연결한다.
  **이번에 Miri를 새로 실행한 것은 아니다.** 동일 production source의 이전
  메모리 안전 검사 근거이며 모든 입력/환경에서의 안전성 증명으로 확대하지 않는다.
- 새 디렉터리의 FST 전체 lib123/123(7.10초), eager 방식
  --no-default-features122/122(7.18초), 실패/skip/filter0, 종료0이다.
  독립 vendor 테스트는 별도 생성 Cargo.lock을 보존하며 서버 workspace lock과
  혼동하지 않는다. 로그 fst-tests.log SHA-256
  `655b87e2edcb64b66d130361eee84a953ad2496274847c958d3b5053d0b91377`,
  fst-eager-tests.log
  `e783616c806709b5d7eed6b9a9abe79e177fdeff1b13546a3b4efb91df0abf38`.
- 실제 패치를 선택한 엔진 전체 unit886/886(25.09초), concurrent7/7(16.04초),
  merge4/4(3.36초), multi-field9/9(0.50초), 총906개 성공, 종료0, 빌드2분16초.
  node lib654/654(11.36초), bin459/459(17.42초), 총1113개 성공, 종료0,
  빌드2분05초. 실패/skip/filter0, nightly/RUSTFLAGS=-Awarnings/jobs2/incremental0/
  DEV_DEBUG=0/TEST_DEBUG=0/--locked/직렬 테스트, 별도 target-dir ../build다.
  cargo tree에서도 tantivy-fst lazy-registry가 활성화됨을 확인했다.
  engine-tests.log SHA-256
  `ad11f2cd6409ef96810a269bf4b1b9550485385c96f22d22da6d019b90c52277`,
  node-tests.log
  `34b2c591191902242ae48c19bcd5b6d90a668b57c73f9ee6ae9026505fdaf7e3`.
- source.sha256 manifest 해시는
  `900013b0fec619451d8f535b111e565e29e96c2781c1e8fac447aa3ce75ebadf`이며
  테스트 후 검증 성공이다. 같은 고정 source/build에서 release 빌드를 진행한다.
  이후 실제 live 전체 비교와 전체 non-plugin 반복 벤치마크가 필수이며 이 단위는
  아직 완료가 아니다. 최초 v0.6.0 처리량95%/시나리오별 mean,p95,p99 지연105%
  누적 한도와 paired/기준선 변동/고정 OpenSearch 비교를 그대로 적용한다.
  FST 변경의 효과는 같은 기능 소스 a1a53727과의 진단 비교로 별도 구분한다.

#### C06 adc3660b 빌드 및 live 검증

- FST 분리 후보 release 빌드7분42초, 종료0. RUSTFLAGS=-Awarnings/jobs2/
  incremental0/--locked/standalone-runtime, 별도 source/build를 사용했다.
  실행 파일 SHA-256
  `adc3660b3235eef2e549de5a7e100f3cfa19c3dd2e81fe9cd5f1b84af29743d7`,
  candidate-build.log SHA-256
  `e0063a0bf9432b45b126be1d1aa12fbbda246912c8adbd1f85d409d000c1233e`.
  고정 source.sha256 빌드 전후 검증 성공이다.
- `target/core-replacement-c06/fst-isolated-live`에 전체 projected core 및 추가
  fixture를 실행해1812/1812 성공, 실패/skip0, count probe 성공, 종료0.
  binary/fixtures unchanged=true다. 기능 참조는 OpenSearch3.7.0-SNAPSHOT이며
  운영/혼합 노드 전체 호환성 인증은 아니다. execution.json SHA-256
  `5df6d216b5f677c3532d2955715ab52ebbb06324d66ba8f61f940bd7c8dffdba`.
- 다음은 tools/run_core_performance_gate.py로 위 실행 파일과 최초 v0.6.0
  db244133을 비교하는 전체 non-plugin 반복 측정이다. 새 출력은
  `target/core-replacement-c06/fst-isolated-repeated-full`이며
  기준선/후보/OpenSearch/OpenSearch/후보/기준선, 각 단일/3노드7연산을 유지한다.
  공개 기준 및 paired 대비 개별 지표5%와 기준선 변동을 모두 검사하고 모든 결과를
  보존한다. 이 기록 시점에는 실행 전이며 기존 a1a53727 FAIL을 대체하지 않는다.

#### C06 adc3660b 전체 반복 성능 결과: FAIL

- 전체 non-plugin 반복 측정 완료: 여섯 하위 실행 모두 종료0, 총12개 토폴로지
  요청 오류0, 1092.52초(18분13초), execution_inputs_verified=true, 인프라 오류 없음.
  수치 gate false로 최종 종료1. 최신 실제 전체 결과는 **adc3660b FAIL**이다.
  이전 a1a53727의19/11개 초과보다 적게 관측됐지만 다른 시간대의 전체 측정만으로
  FST 단일 변경의 인과 효과를 확정하지 않는다.
- 공개 v0.6.0의44개 독립 지표 중 후보01은38개 통과/6개 초과, 후보04는42개
  통과/2개 초과다. 같은 실행 내 paired 비교는 각각42개 통과/2개 초과,
  43개 통과/1개 초과다. 어느 검사든 초과하면 정상 완료를 차단한다.

| 실행 / 토폴로지 | 후보 처리량(req/s) | 최초 v0.6.0 대비 변화 | OpenSearch 대비 배수 |
| --- | ---: | ---: | ---: |
| 01 / 단일 | 736.9291 | -0.8186% | 2.5258 |
| 01 / 3노드 | 911.2643 | -2.1587% | 7.7550 |
| 04 / 단일 | 756.9469 | +1.8756% | 2.6558 |
| 04 / 3노드 | 923.0296 | -0.8955% | 7.9620 |

최초 공개 기준 지연 초과(%, 양수는 악화, '-'는 해당 회에서 한도 이내):

| 지표 | 후보01 | 후보04 |
| --- | ---: | ---: |
| single-node/write/p95 | 5.3442 | - |
| single-node/write/p99 | 6.0177 | - |
| three-node/ranking/p95 | 5.0691 | - |
| three-node/facet/p95 | - | 5.2976 |
| three-node/facet/p99 | 5.8691 | 6.4779 |
| three-node/sort_filter/p99 | 5.4628 | - |
| three-node/refresh/p99 | 5.1465 | - |

- paired 초과는 후보01의3노드 facet p99+7.5920%, sort_filter p99+5.5607%,
  후보04의3노드 write p99+8.6109%다. 기준선00 자체의3노드 ranking p99+7.2667%,
  refresh p99+5.4112% 변동도 실패로 보존한다. 기준선05는 초과0개다.
  기준선 변동을 후보 회귀 면제나 기준선 재설정에 사용하지 않는다.
- 3노드 refresh 평균은 후보01 8.496451ms(+1.3233%), 후보04 8.365639ms(-0.2366%)다.
  첫 회 p99 23.176193ms는 허용23.143900ms를 초과하므로 근소해도 통과가 아니다.
  모든 시나리오와 OpenSearch의 mean/p95/p99 원시 값은 result.json에 보존했다.
  이 dev 내구성60초 혼합 부하 결과는 운영 배포 성능 보증이 아니다.
- `target/core-replacement-c06/fst-isolated-repeated-full/result.json` SHA-256
  `3e3d7c21e433e6224882e62c53cb9ab2053403f91b8ecffcb222ac65c2970c8d`,
  plan.json SHA-256
  `02e61797e75ef2fa997bc3a30449cec5d7f31a53b36dc14675aa2bdc52cf7295`.
- 전체 측정 종료 후 a1a53727/adc3660b의 동일 기능 소스에서 FST 차이를 좁히기 위해
  별도3노드 refresh-work ABBA 진단을 실행한다. 각60초7연산 혼합 부하, 두 차례 drain,
  native/fallback 문서 수와 노드별 refresh 단계 카운터를 수집한다. 출력은
  `target/core-replacement-c06/fst-isolated-refresh-abba`다. 이 진단은 전체 gate를
  대체하거나 실패를 면제하지 않는다. 단위 수락0/40, C02/C06 미완료, ledger 비어 있음,
  루트 의존성 미승격, 릴리즈 보류다. 최적화 후 최초 v0.6.0 누적5% 전체 검사를 재실행한다.

#### C06 FST 단일 의존성 차이의 refresh ABBA 진단

- 2026-09-09: 동일 기능 소스 a1a53727(전)/adc3660b(후)/후/전 순서로3노드
  혼합 부하60초씩 실행 완료. 네 회 요청 오류0, 종료0, 실행 파일/도구 불변 및
  실제 런타임 신원 검증 성공. 각 실행 후 모든 endpoint를 두 번 drain했다.
  성능 합격용 전체 gate가 아니라 FST 차이를 분리하는 추가 진단이다.

| 회 / 후보 | 처리량(req/s) | refresh mean / p95 / p99(ms) | add / commit / reload / doc-ID 누적 초 |
| --- | ---: | ---: | ---: |
| 00 / 전 | 881.2393 | 10.1682 / 20.8317 / 25.5318 | 0.9084 / 36.7042 / 0.8547 / 0.5171 |
| 01 / 후 | 923.6528 | 8.4036 / 17.5788 / 23.7109 | 0.9524 / 28.4746 / 0.8844 / 0.5148 |
| 02 / 후 | 910.1914 | 8.5393 / 17.4717 / 23.0656 | 0.9423 / 28.3437 / 0.8734 / 0.5273 |
| 03 / 전 | 902.8380 | 9.6441 / 19.3262 / 24.0197 | 0.9960 / 35.4263 / 0.8617 / 0.5374 |

- 쌍00→01 처리량+4.8129%, refresh 평균-17.3539%, p99-7.1318%, commit 누적-22.4214%.
  역순 쌍03→02 처리량+0.8145%, refresh 평균-11.4548%, p99-3.9722%, commit-19.9926%.
  두 쌍에서 같은 개선 방향을 확인했지만 표본 두 쌍의 차이도 보존한다. percentile을
  평균 내거나 전체 회귀가 해소됐다고 하지 않는다. 시간 카운터는 준비 단계를 포함한
  노드별 순차 관측 합계이며 HTTP 지연의 완전한 분해가 아니다. commit에는 비동기
  색인/워커 대기 등이 포함될 수 있어 순수 병합 CPU 시간과 동일시하지 않는다.
- 마지막 drain 후 native/fallback 수는 각 endpoint에서 일치:
  00 [6016,4120,4283], 01 [6275,4237,4330], 02 [6177,4217,4315], 03 [6144,4192,4310].
  산술 합계14419/14842/14709/14646은 각각 seed+성공 쓰기 수와 같지만,
  **각 endpoint는 전체 수가 아닌 부분 수를 반환한다.** 합계만으로 ID/내용의 전역
  유일성이나 클러스터 전역 검색 동등성을 입증하지 않는다. 이는 기존 개발용3노드
  진단의 한계이며 FST 변경으로 해결된 기능으로 세지 않는다. R/C 검색·분산 검증은
  별도 미완료다. 이 수치로 OpenSearch 운영 대체 성능을 주장하지 않는다.
- `target/core-replacement-c06/fst-isolated-refresh-abba/result.json` SHA-256
  `45c9b1ca687204509154dc28259d7de57593003d7282b9f5db2154f85ee47a8b`,
  plan.json SHA-256
  `8a36f8bb69f9023721a5ad59c3ed121807c72fcbfb0fdf3241a95bb4e3aee0ea`.
- FST 최적화의 refresh 비용 감소를 지지하는 근거는 얻었으나 최신 전체 gate의
  facet p95/p99 등 초과는 남았다. 다음에는 adc3660b를 고정한 CPU/집계 진단에서
  선택된 bucket 처리와 실제 필드 조회/정렬/병합의 비용을 확인하고, 의미를 유지하는
  수정만 별도 후보에 적용한다. 변경 후 기능 테스트/live 및 **전체 non-plugin 반복
  벤치마크**를 실행하기 전에는 해당 단위를 완료 처리하지 않는다. 최초 v0.6.0의
  처리량95% 이상/각 scenario mean,p95,p99 지연105% 이하, paired 및 기준선 변동
  판정, OpenSearch 비교를 그대로 유지한다. 성능 때문에 전역 검색·버킷 안전성·내구성
  요구를 줄이지 않는다. 전역 검색 동등성은 위 비용 진단과 별개로 반드시 구현/검증한다.
- 모든 테스트/빌드/live/전체 gate/ABBA 진단 프로세스 종료. 최신 adc3660b FAIL,
  정식 수락0/40, C02/C06 미완료, ledger 비어 있음, root FST 의존성 미승격,
  커밋/태그/배포 없음. 이 단위는 최종 완료가 아니라 검증 중 상태다.

#### C06 adc3660b 집계 CPU 경로 재확인

- 2026-09-09: 이전 회차는 FST 분리 후보 기능 검사/전체 gate/ABBA 진단 완료로
  progress다. 기존 프로세스 종료와 최신 상태를 확인한 뒤 같은 adc3660b를 진단했다.
  facet 단독 요청은 도구의 허용 operation이 아니어서 argparse 종료2, 측정 전
  거부됐다. 도구를 변경하지 않고 지원하는 mixed 모드로 별도 출력에서 실행했다.
- `target/core-replacement-c06/fst-mixed-cpu`: 3노드 혼합45초/CPU499Hz,
  perf/matrix 종료0, 실행 파일 전후 일치, 약17K 표본/lost0. 명령상20초 capture의
  전후 관측24.24초에는 시작/종료 비용이 포함된다. new_field inclusive0.13%/self0.01%,
  simple bucket collector4.69%/2.47%, IndexMerger::write14.06%/1.49%,
  source_value_for_highlight_field1.78%/1.01%, memcmp self4.40%다.
  부하 생성기 표본 포함/off-CPU 제외이며 CPU 비중으로 지연의 인과 효과를 단정하지 않는다.
  diagnostic.json SHA-256
  `b4cc377010e01d6ef978554c8e7d2d0b8592b37afb3e9d0be76f4d693d677b85`.
- 호출 경로 검토 중 terms.missing이 실제 배열보다 우선되는 의미 오류를 발견해
  먼저 재현했다. 이는 CPU 표본으로 발견한 성능 병목 확정이 아니라 코드 검토에서
  찾은 별도 기능 오류다. 기존 facet 성능 초과를 이 오류에 귀속하지 않는다.

#### C06 terms.missing의 실제 배열 값 보존

- 단일 문자열 캐시에 값이 없을 때 즉시 missing 문자열을 넣는 분기가
  실제 배열을 누락으로 처리했다. 원본 값 확인 뒤 기존 일반 집계기로 전환하도록
  그 조기 대체 분기를 제거했다. missing은 실제 값이 없거나 일반 집계기의
  기존 empty-value 규칙에 해당할 때 적용된다. 새 변환 규칙이나 집계기를 추가하지 않았다.
- keyword service에 [api,worker,api], api, 누락, null, [], [null,null]의6문서를
  넣었다. 기대unknown4/api2/worker1 대신 수정 전unknown5/api1을 반환했다.
  root engine 회귀 테스트가 실제 실패(종료101)했고, red 로그 SHA-256은
  `65f5a9e47280485c16e12b3ed1dfebb9dbdeb97344a364040086498273c5d28b`이다.
- 새 영구 fixture `tools/fixtures/search-terms-missing-arrays-compat.json`은
  단일 노드3shard에서 native/fallback x size0/10의4개 HTTP 요청을 검사한다.
  해시는 `b329ec1fc770eccc2d0faa81d7a1e8ab6e73c054d7d8ffb04972f7430d7dfafd`.
  기존 adc3660b와 OpenSearch3.7.0-SNAPSHOT 비교에서 native2건 실패/fallback2건
  성공을 재현했다. 함께 실행한 projected core 및 nested bool1500건은 통과했다.
  `target/core-replacement-c06/terms-missing-arrays-before-live/execution.json`
  SHA-256 `01ad2752f15598d9699b708bf225c1798a3f50a9d1ffe7a2009577288cb6983c`,
  search-terms-missing-arrays-compat-report.json
  `e0bd3297157893fda6e05fd04c5a81028aa886e4602c968c3860a5929644dbfd`.
- 테스트는 수학적 기대 버킷을 직접 검사하고6가지 문서 순서 x 기본/include/exclude/
  min_doc_count의24조합에서 기존 일반 집계기와도 비교한다. 문자열 캐시의 선행
  집계 후 일반 경로로 전환될 때 중복/누락하지 않는지 확인했다. 이는 keyword 배열
  계약 검증이며 숫자 매핑 coercion, 모든 null_value/ignore 옵션까지 완료한 것은 아니다.
- 수정 후 engine 전체 unit887/887(25.23초), concurrent7/7(15.67초), merge4/4(3.22초),
  multi-field9/9(0.48초), 총907건 성공, 종료0, 빌드1분20초다.
  node lib654/654(11.63초), bin459/459(17.43초), 총1113건 성공, 종료0, 빌드1분04초다.
  실패/skip/filter0, nightly/RUSTFLAGS=-Awarnings/jobs2/incremental0/DEV_DEBUG=0/
  TEST_DEBUG=0, 비최적화 직렬 실행이다. root FST 의존성은 미변경이다.
  terms-missing-arrays-engine-full.log SHA-256
  `268564c30ba81406b1be08384be9ce5a06672258d41d6a7c5759cb88a17f29cf`,
  terms-missing-arrays-node-full.log
  `45f4de92442232b51045aefbb4e561ff017b39b8e46aaaa620719c6751d7044e`.
  engine lib.rs SHA-256
  `71f8a74f52c6c55e8a4e299f8ee6219ab969a42f991cfab69ab6e85d12783af9`.
- 진단용 dev 빌드38.81초 종료0, --locked/standalone-runtime 사용. 실행 파일을
  `target/core-replacement-c06/terms-missing-arrays-debug/steelsearch`에 고정했다.
  SHA-256 `954a527bb20940c369aa7963af0322ec1a13d539339f3a0f998d2e2b7c0825e3`,
  terms-missing-arrays-debug-build.log 해시
  `ef8d7aad4f3da27d38e7140e69d4f2cc091fd92f67d0fb9c03f33b3b9defea13`.
  **비최적화 기능 진단용이며 release 성능 후보가 아니다.** FST 실험 패치도 포함하지 않는다.
- 이 파일로 기존1812건과 새4건을 모두 실행해1816/1816 성공, 실패/skip0,
  count probe 성공, binary/fixtures unchanged=true, 종료0을 확인했다.
  기존 native 두 오류도 수정 후 실제 OpenSearch와 일치했다.
  `target/core-replacement-c06/terms-missing-arrays-after-debug-live/execution.json`
  SHA-256 `9be2ded5bac36430ee2ba69b0d22ba2c41cb8b57c8bb959902d3818468d78eb2`,
  search-terms-missing-arrays-compat-report.json
  `9936b941ec839f964b713feee12396e310a1ce943ec784c31667538dbe0f8875`.
- 다음은 최신 기능 수정과 검증 중인 FST 패치를 명시적으로 결합한 별도 source/build
  release 후보를 만들고, 동일1816건 live 검증 및 전체 non-plugin 반복 벤치마크를
  실행하는 것이다. 최초 v0.6.0 처리량95% 이상/각 scenario mean,p95,p99 지연105%
  이하의 고정 누적 gate, paired/기준선 변동/고정 OpenSearch 비교를 모두 유지한다.
  새 오류 수정의 비용도 이 전체 검사 전에 완료 처리하지 않는다. 기존 measured
  source/build와 최초 발표 증거는 변경하지 않는다. 정합성/버킷 안전/내구성을 낮추거나
  진단용 dev 빌드를 성능 기준으로 사용하지 않는다.
- 현재 모든 테스트/빌드/live/CPU 진단 프로세스 종료. 새 release/전체 성능 gate는
  미실행이므로 최신 adc3660b FAIL을 유지한다. 정식 수락0/40, C02/C06 미완료,
  ledger 비어 있음, root FST 의존성 미승격, 커밋/태그/배포 없음.

#### C06 terms.missing 수정과 FST 결합 release 후보

- 2026-09-09: 이전 회차는 배열 missing 오류 재현/수정/소스 테스트 및 진단용 live
  완료로 progress다. 새 source를
  `target/core-replacement-c06/terms-missing-fst-candidate/source`에 준비했다.
  adc3660b의 고정 source 대비 crates 차이는 engine lib.rs의11줄 조기 대체 제거와
  회귀 테스트뿐이며, 새 HTTP fixture도 복사했다. FST 패치/lock과 나머지 기능 소스는
  그대로다. source.sha256 manifest SHA-256
  `34fe40fd2f887300ad1a8c8ec7df0a6f448b46ea04c348bc50bfb960f3cf4af6`.
- 디스크 여유1.7GiB 때문에 이 후보의 컴파일 캐시만 새 RAM 기반 전용 경로
  `/run/user/1001/steelsearch-terms-missing-build-20260909`에 두었다. 소스/로그/최종
  실행 파일은 작업 디스크에 보존했다. nightly ad3a598ca/RUSTFLAGS=-Awarnings/jobs2/
  incremental0/--release/--locked/standalone-runtime, 빌드7분38초, 종료0.
  빌드 전후 source manifest 검증 성공이다. candidate-build.log SHA-256
  `23f322f10501b7a6ce8667afb2a9a0760a5113efda344ff889a5674dc217cd67`.
- 원본과 `artifacts/steelsearch` 복사본 모두 SHA-256
  `fbe381d9e04663c671c95d587c5984b8f0a9e3e87dd8a27359239e92d054ff0b`로 일치한다.
  이 디스크 복사본을 실제 실행한다. Cargo clean은 CACHEDIR.TAG 누락으로 종료101,
  삭제 전 거부했다. 강제 삭제/표식 위조 없이 임시 캐시 약637MiB를 그대로 보존했다.
  temporary-cache-clean.log SHA-256
  `158fb3f608f066aa7165fb13262b67f842bfd4e51c30c60ed452736900d1cff3`.
  빌드 프로세스는 종료됐고 측정 전 메모리 available 약13GiB, swap0이다.
  임시 캐시는 모든 비교 실행 동안 그대로 유지하며 이 환경 차이를 감추지 않는다.
  기존 measured source/build 및 최초 발표 증거는 변경하지 않았다.
- release fbe381d9와 OpenSearch3.7.0-SNAPSHOT live에서1816/1816 성공,
  실패/skip0, count probe 성공, binary/fixtures unchanged=true, 종료0.
  새 missing-array4건도 모두 통과했다.
  `target/core-replacement-c06/terms-missing-fst-live/execution.json` SHA-256
  `b539924592430e7c5be9c4e1593f26762be8ae933ac1fac21159f1fbe12187f4`.
- 이제 tools/run_core_performance_gate.py로
  `target/core-replacement-c06/terms-missing-fst-repeated-full`에 전체 non-plugin
  반복 측정을 실행한다. 최초 v0.6.0 db244133/후보 fbe381d9/고정 OpenSearch2.19를
  동일 실제 설정에서 기준선/후보/OS/OS/후보/기준선 순서로 단일·3노드7연산 모두
  측정한다. 공개 기준/paired/기준선 변동을 각각 검사하고 처리량95% 이상,
  각 scenario mean,p95,p99 지연105% 이하의 고정 누적 gate를 유지한다.
  이 기록 시점은 성능 판정 전이므로 최신 adc3660b FAIL 및 단위 미완료를 유지한다.

#### C06 fbe381d9 전체 반복 성능 결과: FAIL

- 2026-09-09: 전체 non-plugin 반복 suite 완료. 여섯 하위 실행 모두 종료0,
  단일/3노드 총12개 실행의 요청 오류0, 1091.18초(18분11초),
  execution_inputs_verified=true, 인프라 error 없음. 수치 gate false로 최종 종료1.
  최신 실제 전체 결과는 **fbe381d9 FAIL**이다. 임시 RAM 캐시는 측정 동안 그대로
  유지했으며 빌드/live/별도 테스트를 병행하지 않았다.
- 공개 v0.6.0의44개 지표 중 후보01은41개 통과/3개 초과, 후보04는43개 통과/
  1개 초과다. 같은 회의 paired v0.6.0 대비는32개 통과/12개 초과와42개 통과/
  2개 초과다. 공개 기준 초과 개수만 줄었다고 전체 성능이 개선됐다고 결론 내리지 않는다.

| 실행 / 토폴로지 | 후보 처리량(req/s) | 최초 v0.6.0 대비 변화 | OpenSearch 대비 배수 |
| --- | ---: | ---: | ---: |
| 01 / 단일 | 731.9119 | -1.4938% | 2.5002 |
| 01 / 3노드 | 916.3359 | -1.6142% | 8.6282 |
| 04 / 단일 | 753.9456 | +1.4717% | 2.5863 |
| 04 / 3노드 | 929.6435 | -0.1854% | 8.7318 |

최초 공개 기준 지연 초과(%, 양수는 악화, '-'는 해당 회에서 한도 이내):

| 지표 | 후보01 | 후보04 |
| --- | ---: | ---: |
| single-node/write/p95 | 5.7864 | - |
| three-node/sort_filter/p99 | 8.4028 | - |
| three-node/refresh/p99 | 8.8699 | - |
| three-node/facet/p99 | - | 6.0096 |

- paired 후보01 초과: 단일 write p95+6.2914%, ranking mean+5.3234%, facet mean
  +5.3784%/p95+5.0240%, sort_filter mean+5.4626%; 3노드 ranking mean+5.3228%/
  p95+6.3538%/p99+7.1440%, sort_filter p95+5.1689%/p99+9.6829%, nested p99
  +5.6587%, refresh p99+10.3690%다. 후보04는3노드 facet p99+6.6168%,
  sort_filter p99+7.7494%가 초과했다. 기준선00 drift 초과0개, 기준선05의
  단일 sort_filter p99+5.1597%는 실패로 보존한다. 기준선 재설정/회귀 면제는 없다.
- 3노드 refresh p99는 공개22.041810ms -> 후보01 23.996897ms(허용23.143900ms),
  facet p99는 공개13.120877ms -> 후보04 13.909386ms다. 모든 시나리오 원시
  mean/p95/p99와 OpenSearch 비교는 result.json에 보존한다. dev 내구성60초 부하와
  기존3노드 전역 검색 미검증의 한계는 유지되며 운영 대체 성능 주장이 아니다.
- `target/core-replacement-c06/terms-missing-fst-repeated-full/result.json` SHA-256
  `4c8411bcb65ba538326621498bacd97a5fcfc2fb6dec84357dba6063f0bc544c`,
  plan.json SHA-256
  `e9d107761a00c877d3def84f42ac01fd110113e71cbd2e2a38c592ad69c67413`.
- 측정 종료 후 workspace 범위의 Cargo clean --dry-run도 캐시 표식 누락으로
  종료101/삭제 전 거부했다. 임시 캐시는 그대로이며 강제 삭제나 표식 위조는 하지 않았다.
  정리 실패를 부하 실행 실패로 혼동하지 않는다. 사용자가 운영 중인 컨테이너와
  기존 측정 source/build, 최초 발표 증거를 변경하지 않았다.
- 후속 코드 확인에서 native 응답은 standalone_runtime.rs의
  response.into_opensearch_body(1)를 이미 사용하고 있었다. os-engine의 borrowed
  serializer에 source.clone이 있다는 사실만으로 native 경로의 불필요한 복제를
  단정하거나 새 serializer를 추가하지 않는다. 실제 호출 경로와 소유권을 먼저 확인한다.
- 다음은 고정 fbe381d9에서 집계 수집의 필드 조회/선택된 bucket 처리 및 검색·refresh
  경쟁 구간을 좁히는 진단이다. 국소 비교는 원인 분석용이며 수정 후 기능 검사/live와
  **전체 non-plugin 반복 벤치마크**를 다시 실행하기 전에는 해당 단위를 완료 처리하지
  않는다. 최초 v0.6.0 처리량95%/각 scenario mean,p95,p99 지연105% 고정 누적 gate,
  paired/기준선 변동/고정 OpenSearch 비교를 모두 유지한다. 이번 결과만으로 특정
  기능의 단일5% 저하 또는 최적화 불가능성을 입증하지 못했으므로 ledger는 비어 있다.
- 모든 빌드/live/전체 gate 프로세스 종료. 정식 수락0/40, C02/C06 미완료,
  root FST 패치 미승격, 릴리즈 보류. 커밋/태그/배포는 하지 않았다.

#### C06 facet 단독 CPU 진단과 기준선 대조 (2026-09-09)

- 진단 도구의 연산 선택에 ranking/facet/refresh를 추가했다. mixed 기본값과
  실제 부하/실행 파일 식별 검사는 유지하고 플러그인 연산은 계속 거부한다.
  두 토폴로지에서 선택 연산 이외 설정이 바뀌지 않는 검사와 플러그인 거부 검사를
  추가했다. 관련 도구 테스트33건 재검증 성공, 종료0이다.
  `target/core-replacement-c06/core-operation-diagnostics-tests-confirmed.log`에 보존했다.
  테스트 로그의 임시 gate exit1/2는 mock 검사이며 새 전체 벤치마크 결과가 아니다.
- 후보 fbe381d9와 최초 v0.6.0 db244133를 순차 실행했다. 각각 facet=100,
  3노드/3shards/1replica/5000문서/384차원 원문/4clients/seed13/45초,
  CPU499Hz/20초 capture이며 실행 중 빌드나 테스트를 병행하지 않았다.
  profiler와 matrix 모두 종료0, 실행 전후 binary SHA-256 일치, 요청 오류0이다.
  원래 공개 기준선은 변경하지 않았다. refresh 단독 선택에는 seed 이후 쓰기가
  없으므로 미반영 쓰기의 commit 비용이나 혼합 refresh tail 검증으로 쓰지 않는다.

| 진단 실행 | 성공 요청 | facet mean(ms) | p95(ms) | p99(ms) | 집계 함수 self CPU(%) |
| --- | ---: | ---: | ---: | ---: | ---: |
| fbe381d9 | 64905 | 2.762414 | 4.748069 | 6.000254 | 10.19 |
| v0.6.0 db244133 | 64665 | 2.772770 | 4.828221 | 6.241427 | 10.27 |

- CPU 비율 분모에는 load-generator와 kernel 표본도 포함된다. PID 필터 보고서도
  기본 absolute 비율을 유지하므로 이를 서버만의 정규화된 비율로 읽지 않는다.
  후보의 집계 함수 self 표본2243개를 disassembly로 확인했다. 문자열 키 BTreeMap
  조회 주변에 샘플이 집중된다. 명령어별 샘플에는 skid가 있으므로 특정 load의
  stall 시간이나 cache miss 수라고 단정하지 않는다. memcmp 전체 self는 후보6.59%,
  기준선7.04%이며 모두 집계에서 발생한 비용이라는 뜻은 아니다.
- 이 순차 단독 진단은 ABBA/전체 혼합 부하가 아니다. 샘플 비중 차이와 지연 표를
  개선율, 회귀 해소 또는 원인 입증으로 사용하지 않는다. 공통의 비싼 집계 경로를
  확인했지만 새 기능의 단일5% 악화를 입증하지 못했다. 기존 루프 전치와 문자열
  태그 실험을 근거 없이 반복하지 않는다. 런타임 수정이나 기능 제외는 하지 않았다.
- 증거: `target/core-replacement-c06/{fbe-facet-cpu,v060-facet-cpu}/`의
  diagnostic.json/plan.json/matrix/summary.json/perf.data/self-report.txt.
  후보 diagnostic SHA-256
  `3343c4b76bf8c2a1959d96c4023406fe706d8c7938bbe9b99f33b9363fdcd5ca`,
  기준선 diagnostic SHA-256
  `3b1d6c2f7521a7ffd50f94dd2c38a0ad67c1a6ee553db518617467c32c846639`.
  후보 collector-annotate.txt SHA-256
  `ac0a1a9417e370239ac9bec9260cb887dceb0c9c401489e51457776ee7932c8a`.
- 다음 구현 검토는 문서별 필드 캐시 조회의 의미 보존과 혼합 검색/refresh 경쟁이다.
  배열/null/누락/필드 순서 차이의 generic fallback, 다중 필드와 날짜 예산을 유지해야
  한다. 후보를 수정하면 기능 회귀/live, 원인 분리용 국소 비교에 이어 **전체 non-plugin
  반복 벤치마크를 실행한 후에만 구현 단위 완료를 판단**한다. 최초 v0.6.0 누적
  처리량95%/각 시나리오 mean,p95,p99 지연105%와 paired/기준선 변동 검사는 유지한다.
  이번 진단 도구 변경도 완료 승인하지 않는다. 최신 전체 gate는 fbe381d9 FAIL,
  정식 수락0/40, C02/C06 미완료, ledger 제외0, 릴리즈 보류다. 진단 프로세스 종료.

#### C06 작은 필드 캐시 후보: 생성 비용 보완 필요 (2026-09-09)

- 직전 턴의 기준선 대조는 공통 집계 비용이라는 새 증거를 확보한 진행으로 분류한다.
  이번에는 immutable 문자열/숫자/날짜 캐시의 생성과 get 사용처를 확인했다.
  `tools/bench-field-cache-lookup.rs`에서 독립 소유 문자열5000문서, 필드 수
  0/1/3/8/9/16/64/256, 일부 누락 필드, 고정 hit/miss 질의, 16회 순회,
  네 라운드 순서 반전으로 tree/sorted/small_linear/hash를 비교했다.
  각 결과를 원문 필드 검색과 대조하고 checksum도 검사했다. 이는 서비스 부하가
  아니며 건수별 조회/생성 비용 진단이다. 소수 고정 질의의 locality 한계가 있다.
- root에 `field_cache.rs`를 추가했다. 고유 키8개 이하에서는 작은 Vec의 정확한
  문자열 비교, 그 이상은 BTreeMap을 사용한다. FromIterator는 중복 키의 마지막
  값을 유지하고 작은 배열을 정렬하여 입력 순서에 따른 PartialEq 차이를 막는다.
  세 캐시의 타입과 extractor 반환 타입만 연결했다. 값 추출, 배열/null/누락
  fallback, 날짜 예산, 보안/내구성 설정은 변경하지 않았다. FST root 패치는 없다.
- 캐시 모듈 SHA-256
  `062d5f26f8f0e08d5e8b772ac901adc9ff5b750b7b06b0d2ff7b3199b8ea66ee`,
  engine lib.rs SHA-256
  `72cede397cd19038e6f56a7fd7ef3e245ac01a324b518a5cb4518e277f2e93db`.
  전체 engine909건(889+7+4+9) 성공, 종료0, 빌드1분22초.
  `target/core-replacement-c06/field-cache-engine-full.log` SHA-256
  `bbc543b41225b0fda33751bec7fbf0b1e26e364ae9921a56703875a149afa75c`.
- node를 standalone-runtime 포함 전체 검사했다. 단위654+459 성공이나 daemon
  통합49성공/4실패, 최종 종료101이다. 첫 실패는 dev_cluster_daemons.rs:453의
  recovery-failed 이후 extension shutdown 기대200/실제503이고 나머지3건은
  공유 mutex poison이다. 이전 fbe381d9 실행 파일을 CARGO_BIN_EXE_steelsearch로
  지정한 독립 동일 테스트도 같은 위치에서 종료101이었다. 플러그인 지원을 추가하거나
  safety admission을 완화하지 않았으며, node 전체 성공으로 표시하지 않는다.
- mutex poison3건을 별도 프로세스로 격리하자 cluster formation smoke가45초 동안
  applied=true에 도달하지 못했다. 남은2건은 다시 poison으로 미검증이다.
  이전 fbe381d9에 smoke만 실행해도 같은 대기 조건에서45초 후 실패했다.
  캐시 변경에만 발생한 실패는 아니지만, core 클러스터 형성의 미해결 검사로 남긴다.
  기능 대체 완성을 입증하지 못하며 기존1816 live 성공으로 이 검사를 상쇄하지 않는다.
  로그는 같은 디렉터리의 field-cache-node-full.log, field-cache-before-lifecycle.log,
  field-cache-cluster-isolated.log, field-cache-before-cluster-smoke.log에 보존했다.
- debug 실행 파일을 `target/core-replacement-c06/field-cache-debug-candidate/steelsearch`에
  보존했다. SHA-256
  `fbf849b2174d9849fae75c9caaf71c2aaf35ece8e92563272194f04ad9e18be3`.
  이는 FST 없는 비최적화 진단 바이너리이며 성능 후보가 아니다.
- 진단 도구에 실제 field_cache.rs를 직접 포함한 adaptive 비교를 추가했다.
  독립 검사3건 성공, 측정 종료0이다. 4회 산술평균의 tree -> adaptive 조회 ms는
  필드3:2.603->1.256, 8:4.314->2.583, 64:24.666->28.348이다.
  생성 ms는16:9.943->13.185, 64:33.811->57.634, 256:128.418->258.814로
  악화했다. 큰 캐시의 점진 insert/extend가 기존 collect 일괄 생성보다 비싼 경로다.
  조회 개선만으로 채택하지 않는다. 엔진 전체 지연의 악화율이나 원인 기여율은 아니다.
  `field-cache-adaptive-lookup.csv` SHA-256
  `e99fccfdfd793e9b8d3b604ad543ef04582259afc961be77d336873e38df0466`.
- 다음은 큰 캐시 전환을 일괄 collect로 수정하고 동일 진단/기능 회귀를 재검증하는
  작업이다. 생성 비용 문제를 남긴 상태로 release 후보를 만들지 않는다. 수정 후
  별도 소스/빌드 및 실행 파일 식별을 보존하고 live와 **전체 non-plugin 반복 suite**를
  실행하기 전에는 이 구현 단위를 완료 처리하지 않는다. v0.6.0 고정 누적 처리량95%
  및 각 시나리오 mean/p95/p99 지연105%, paired/기준선 변동/고정 OpenSearch 비교를
  그대로 유지한다. 전체 성능 최신 결과는 fbe381d9 FAIL이며 새 후보의 전체 성능은
  미측정이다. 단일 기능의 서비스5% 악화와 최적화 불가가 입증되지 않아 ledger 제외0,
  정식 수락0/40, C02/C06 미완료, 릴리즈 보류다. 이번 실행 프로세스 모두 종료.

#### C06 필드 캐시 일괄 생성 수정과 고정 후보 (2026-09-09)

- 직전 턴은 후보 구현과 생성 비용/별도 daemon 실패 증거를 확보한 진행이다.
  이번에는 큰 캐시 전환의 insert/extend를 앞선8개 항목과 남은 iterator를 연결한
  BTreeMap collect로 교체했다. 작은 캐시의 정확한 비교, 고유 키 전환 기준,
  중복 키의 마지막 값 유지와 fallback은 그대로다. 전환 이후 iterator에 중복 키가
  여러 번 나오는 검사도 추가했다. 별도 진단 검사4건 성공이다.
- field_cache.rs SHA-256
  `f1340566ddfdcd2f56cec3982f0426964d1d1444b65b635854c5241940dcf1a0`.
  `target/core-replacement-c06/field-cache-bulk-tests.log` SHA-256
  `9e8139b6ff1cc912639132499b0258b53742ca0dbfb1fb548001b8d46e1f4282`.
- 같은 4라운드 진단의 생성 평균 ms(tree -> adaptive)는16:10.124->11.990,
  64:35.361->36.675, 256:133.302->130.459이다. 이전 점진 생성 후보의 큰
  생성 비용은 줄었지만 모든 조건에서 유리하다는 뜻은 아니다. 조회 평균 ms는
  빈 캐시0.478->0.772, 3필드2.884->1.583, 8필드4.801->3.273,
  16필드10.647->12.304, 64필드25.440->25.920, 256필드50.551->52.474다.
  불리한 조건도 보존하며 마이크로벤치마크 비율을 서비스 지연 회귀율로 쓰지 않는다.
  `field-cache-bulk-lookup.csv` SHA-256
  `83a68ac0fce49c826c6e3b24548ba05fe74493d5dacd1498d79f310ea8999620`.
- 수정 후 root 전체 engine910건(890+7+4+9) 통과, 종료0, 빌드1분23초.
  `target/core-replacement-c06/field-cache-bulk-engine-full.log`에 보존했다.
  root는 FST 미패치이며 이 검사를 FST 결합 후보 전체 검사라고 부르지 않는다.
  이번 수정 후 node/live는 아직 재실행하지 않았다. 앞선 daemon lifecycle와
  cluster applied 상태 실패 및 poison으로 미검증인2건은 여전히 열려 있다.
- `target/core-replacement-c06/field-cache-bulk-candidate/source`를 fbe381d9의
  보존 소스에서 복사하고 engine lib.rs와 새 field_cache.rs만 반영했다.
  crates 전체 diff로 두 파일 이외 앱 소스 차이 없음을 확인했다. 기존 vendor FST,
  Cargo.lock/Cargo.toml은 fbe381d9와 같으며 root에 FST를 승격하지 않았다.
  전체 source.sha256 검사 성공, manifest SHA-256
  `0a10b35eed50725cafb4c7ddaa215f699ae558234733e73e54928e0a88ed7a70`.
- 이 스냅샷의 release 빌드/실행 파일 식별/기능 live 및 **전체 non-plugin 반복
  벤치마크**는 다음 필수 작업이다. 별도 build 디렉터리를 사용하고 원래 증거를
  덮어쓰지 않는다. 단위 완료 전 최초 v0.6.0 고정 누적 처리량95%/각 시나리오
  mean,p95,p99 지연105%, paired/기준선 변동/고정 OpenSearch 비교를 모두 검사한다.
  새 후보 성능 미측정, 최신 전체 fbe381d9 FAIL, 정식 수락0/40, C02/C06 미완료,
  ledger 제외0, 릴리즈 보류를 유지한다. 이번 테스트/진단 프로세스 모두 종료했다.

#### C06 45c54895 release 빌드와 live 검증 (2026-09-09)

- 앞선 일괄 생성 수정/910건 engine 검사/고정 소스 확보는 진행이다. 이번에는
  field-cache-bulk-candidate/source의 전체 manifest를 다시 검사한 뒤 release를
  빌드했다. nightly/--locked/RUSTFLAGS=-Awarnings/jobs2/incremental0/
  standalone-runtime이며 새 전용 target 디렉터리는
  `/run/user/1001/steelsearch-field-cache-bulk-build-20260909`이다.
  기존 fbe381d9 빌드/소스/최초 v0.6.0 증거는 변경하거나 삭제하지 않았다.
- 빌드7분39초, 종료0. 빌드 전후 source manifest 검사 성공.
  `target/core-replacement-c06/field-cache-bulk-candidate/candidate-build.log` SHA-256
  `f3ddee6c3b9c861d30b4fe9d0bb636a86ad5628e02dbcc8d6ee157cf9fd84dac`.
  최종 파일은 같은 디렉터리의 `artifacts/steelsearch`에 복사했으며 RAM 원본과
  디스크 복사본 SHA-256 모두
  `45c5489591040445213edea3b763ace5e1c591eed8fb9fbfda6e3c211149a4cc`다.
  이후 실제 검증은 디스크 복사본을 사용한다. 빌드 캐시는 유지되어 있으며
  측정 중 정리/빌드/소스 변경을 하지 않는다. 디스크 여유가 적은 환경을 유지한다.
- `target/core-replacement-c06/field-cache-bulk-live`에서 고정 바이너리와
  OpenSearch3.7.0-SNAPSHOT live 비교1816/1816 성공, 실패/skip0, 하위16실행 모두
  종료0, 전체 종료0이다. count probe=true, binary_unchanged=true,
  fixtures_unchanged=true. 새 캐시와 FST를 결합한 실제 바이너리의 결과이며
  이전 바이너리나 root 미패치 실행의 결과를 재사용하지 않았다.
  execution.json SHA-256
  `fe255926d0c2ca38f56d6879f640fb61e883c51793c8da1eb3a7896d5613135e`.
  이 비교는 기존 daemon lifecycle/cluster applied 실패를 없애거나 전체 기능
  대체를 입증하지 않는다. 성능 비교의 고정 OpenSearch2.19와도 구분한다.
- 다음 필수 실행은 tools/run_core_performance_gate.py에 최초 db244133 바이너리와
  이번 artifacts/steelsearch를 전달하여 새
  `target/core-replacement-c06/field-cache-bulk-repeated-full`에 기록하는 전체
  non-plugin 반복 suite다. baseline/candidate/OS/OS/candidate/baseline 순서의
  단일/3노드7연산, 최초 공개 v0.6.0 누적 처리량95%/각 시나리오 mean,p95,p99
  지연105%, paired와 기준선 drift를 모두 검사한다. 그 전에는 단위 완료가 아니다.
  최신 전체 성능은 여전히 fbe381d9 FAIL, 45c54895 성능 미측정, 정식 수락0/40,
  C02/C06 미완료, ledger 제외0, 릴리즈 보류다. 빌드/live 프로세스 모두 종료했다.

#### C06 45c54895 전체 반복 성능 결과: FAIL (2026-09-09)

- 직전 빌드와 실제1816건 live 성공은 진행이다. 이번에는 고정 db244133/45c54895/
  OpenSearch2.19로 전체 non-plugin 반복 suite를 실행했다. 여섯 실행 모두 종료0,
  총12개 토폴로지 실행의 요청 오류0, 입력 검증true, 1098.28초(18분18초)다.
  수치 gate false/acceptance false로 전체 종료1. 최신 전체 결과는 **45c54895 FAIL**.
  측정 중 소스 편집/빌드/테스트/캐시 정리/재시작을 하지 않았다.
- 공개 v0.6.0 기준은 후보01/04 각각37/44 통과,7개 초과다. 같은 회 paired
  기준에서는 각각40/44 통과,4개 초과와36/44 통과,8개 초과다. 모든 공개 기준
  초과는3노드 지연이다. 공개 기준 실패 개수는 이전 fbe381d9의3/1보다 많지만,
  서로 다른 시간의 실행을 단일 변경의 인과 효과라고 단정하지 않는다.

| 실행 / 토폴로지 | 후보 처리량(req/s) | 최초 공개 v0.6.0 대비 | 고정 OpenSearch 대비 배수 |
| --- | ---: | ---: | ---: |
| 01 / 단일 | 763.4849 | +2.7555% | 2.6660 |
| 01 / 3노드 | 909.5925 | -2.3382% | 8.1360 |
| 04 / 단일 | 757.9702 | +2.0133% | 2.7299 |
| 04 / 3노드 | 913.0587 | -1.9661% | 8.0888 |

최초 공개 기준 지연 한도 초과(%, 양수는 악화, '-'는 해당 회 한도 이내):

| 3노드 지표 | 후보01 | 후보04 |
| --- | ---: | ---: |
| write p95 | - | 5.3076 |
| write p99 | - | 6.3967 |
| ranking mean | 5.1941 | 5.0783 |
| ranking p95 | 5.8166 | 6.8382 |
| ranking p99 | 9.3819 | 7.3369 |
| facet p99 | - | 6.9511 |
| sort_filter p95 | 6.4550 | - |
| sort_filter p99 | 8.8786 | - |
| nested p99 | 9.0834 | - |
| refresh p99 | 7.6583 | 7.1972 |

- paired 후보01 초과는3노드 ranking p99+6.7452%, sort_filter p99+13.1551%,
  nested p99+5.5683%, refresh p99+7.6322%다. 후보04 초과는3노드 write p99
  +9.0673%, ranking p95+7.5311%/p99+7.2491%, facet p99+10.2354%,
  sort_filter p99+7.8159%, nested p99+6.8417%, refresh p95+6.6428%/
  p99+7.0137%다. 공개 기준과 paired 중 유리한 쪽을 선택하지 않는다.
- 기준선00 drift 초과0개, 기준선05는 단일 write p95+6.0315%/p99+6.0802%,
  3노드 lexical p99+9.1976%로3개 초과다. 변동을 이유로 실패를 면제하거나
  기준선을 재설정하지 않는다. 모든 시나리오 mean/p95/p99와 OpenSearch 수치는
  result.json에 보존했다. dev 내구성/3노드 전역 검색 미검증 한계도 유지한다.
- `target/core-replacement-c06/field-cache-bulk-repeated-full/result.json` SHA-256
  `6e426011b9f1ec1b2e0cbd560a27b21b7a5f8695a3c376b15cb9e2d778c0da49`,
  plan.json SHA-256
  `304c2f69e138659cfe3280c8345b65d87416cb7e98ecc17e4611065d4b98a18c`.
- 작은 필드 캐시는 아직 채택하지 않는다. 다음 원인 분리는 실제 변경 전 fbe381d9와
  변경 후45c54895를 같은 조건에서 사전 고정한 ABBA 혼합 부하로 대조하는 것이다.
  특히3노드 ranking/refresh tail과 문서 레이아웃/캐시 생성 비용을 조사한다.
  이 국소 비교는 진단용이며 합격 대체물이 아니다. 수정 시 기능 회귀/live와
  **전체 non-plugin 반복 suite**를 다시 완료하고 v0.6.0 고정 누적5% gate를 만족하기
  전에는 단위를 완료 처리하지 않는다. 단일 기능의5% 악화 및 최적화 불가가 아직
  입증되지 않아 ledger 제외0이다. 안전장치 완화나 초과 예외 승인은 없다.
- 전체 benchmark 프로세스 종료. 정식 수락0/40, C02/C06 미완료, 앞선 daemon
  lifecycle/cluster applied 검사 실패도 미해결이다. root 후보 코드는 미승인 실험이며
  FST root 승격/커밋/태그/릴리즈는 하지 않았다.

#### C06 캐시 ABBA와 레이아웃 원인 분리 (2026-09-09)

- 직전 전체 suite 실패는 새 증거를 얻은 진행이다. 이번에는 변경 전 fbe381d9와
  변경 후45c54895를 고정한 before/after/after/before 순서로 3노드60초7연산
  혼합 진단을 실행했다. 5000문서/384원문값/4clients/3shards/1replica/seed13,
  실제 실행 파일과 실행 입력 불변 검사, node counters, 부하 후 refresh2회를
  사용했다. 실행 중 편집/빌드/테스트를 하지 않았고 네 실행 모두 오류0/최종 종료0이다.
  진단은 tools/run-core-refresh-work-diagnostic.py이며 전체 gate를 대체하지 않는다.

| 실행 | 바이너리 | req/s | refresh mean(ms) | refresh p99(ms) | commit 누적(s) |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | fbe381d9 | 923.2726 | 8.2341 | 23.0842 | 27.9523 |
| 1 | 45c54895 | 930.0110 | 8.2637 | 22.1525 | 28.1391 |
| 2 | 45c54895 | 930.1390 | 8.3458 | 22.3530 | 28.1936 |
| 3 | fbe381d9 | 913.1266 | 8.5167 | 22.9358 | 28.8449 |

- 0->1/3->2 대응 쌍의 처리량은+0.7298%/+1.8631%, facet mean은
  -2.0528%/-4.5127%, facet p99는-4.8165%/-4.9999%다. 반면 nested p99는
  **+6.1098%/+5.1533%**로 두 쌍 모두5% 이상 증가했다. 이 현상을 다른 개선으로
  상쇄하지 않는다. ranking mean은-0.4744%/-1.2670%, p99는+0.6378%/-6.3556%,
  refresh p99는-4.0360%/-2.5411%다. 따라서 전체 gate의 ranking/refresh 초과를
  캐시 변경 하나의 악화라고 단정하는 근거는 이번 진단에서 얻지 못했다.
  각 연산 mean/p95/p99는 네 baseline.json에 모두 남아 있다. commit counter는
  준비 작업과 worker join을 포함한 노드별 누적 합이며 순수 merge CPU 시간이 아니다.
- 마지막 drain 이후 endpoint별 native/fallback count는 모두 서로 일치했다.
  각 실행의 값은[6256,4241,4337], [6279,4262,4351], [6253,4257,4394],
  [6179,4233,4330]이다. 합계14834/14892/14904/14742는 seed+성공 쓰기 건수와
  일치하지만 전역 ID/content 고유성 증명은 아니다. 콘솔의 observed3개는 첫 endpoint의
  시간별 관측이며 세 endpoint가 아니다. 앞선 진행 설명의 혼동을 이 기록에서 바로잡는다.
- `target/core-replacement-c06/field-cache-bulk-abba/result.json` SHA-256
  `597ce0706556ac46ab722e84147ff6fac7ea426ae2301e7d1ac0a64ec4409ccd`,
  plan.json SHA-256
  `ed705337abfdb0b030bc4527bee3c86380d4d832c15ae1d849d6f11bb5ae06f5`.
- 측정 후 진단 도구에 size_of 보고를 추가했다. 현재 문자열/f64/i64 캐시는 각각
  BTreeMap24바이트 -> FieldCache32바이트다. 이 크기 증가만으로 StoredDocument의
  정확한 배치나 nested 지연 인과관계를 입증하지 않는다. 작은 Vec는 유지하고 큰
  Tree만 Box에 두는 별도 CompactLayout 타입은 세 타입 모두24바이트로 확인됐다.
  `field-cache-compact-layout.log`와 해당 lookup CSV를 보존했다. CompactLayout은
  크기 검사용으로만 존재하고 엔진에 적용하지 않았다. CSV의 시간은 여전히 기존
  adaptive 구현이며 compact 형태의 실행 성능이 아니다. 진단은 정상 종료했다.
- 다음은 큰 Tree만 Box에 두는 후보의 의미/생성·조회·할당 비용과 nested 경로를
  검사하는 작업이다. 의미 보존 검사, 실제 바이너리 live, 원인 분리 진단 및 **전체
  non-plugin 반복 suite**를 완료하기 전까지 단위 미완료다. v0.6.0 고정 누적
  처리량95%/각 시나리오 mean,p95,p99 지연105%, paired/기준선 drift 검사를 유지한다.
  nested 악화는 재현됐지만 최적화 불가를 입증하지 못했으므로 ledger 제외0이다.
  최신 전체45c54895 FAIL, 정식 수락0/40, 릴리즈 보류를 유지한다. 모든 실행 종료.

#### C06 boxed 큰 캐시 후보 구현과 회귀 검사 (2026-09-09)

- 앞선 ABBA의 nested p99 두 쌍5% 이상 증가와 크기 진단은 다음 행동을 좁힌
  진행이다. 이번에는 FieldCache::Tree를 Box<BTreeMap>으로 변경하고 일괄 생성
  결과만 Box::new로 감쌌다. 작은 Vec, 전환 기준8개, 정확한 키 비교, 중복 키의
  마지막 값 유지, fallback/보안/내구성/bucket 예산은 그대로다.
- 문자열/f64/i64 세 캐시 모두 size_of24바이트로 확인했다. 세 타입의 컨테이너
  크기가 기존 BTreeMap보다 커지지 않는 회귀 검사를 추가했다. 독립 진단 검사5건
  성공, 실제 모듈을 포함한 마이크로벤치마크도 종료0이다. 큰 캐시는 별도 할당과
  간접 참조 비용을 추가하므로 크기 감소만으로 성능 개선을 주장하지 않는다.
- 같은 진단 내 생성 평균 ms(tree -> boxed adaptive)는3필드2.295->1.528,
  8필드4.362->4.158, 16필드9.859->11.631, 64필드33.995->35.705,
  256필드131.628->129.822다. 조회 평균 ms는 빈 캐시0.474->0.776,
  3필드2.641->1.459, 8필드4.282->2.777, 16필드9.742->12.822,
  64필드22.922->22.055, 256필드47.681->50.136이다. 불리한 조건도 보존한다.
  이 값은 HTTP 지연 회귀율이 아니며 nested tail 개선은 아직 검증하지 않았다.
  `target/core-replacement-c06/field-cache-boxed-lookup.csv` SHA-256
  `f62682d07f046261e6e58853dd45b3b67fa8e72e1824e42916146df25a0c2133`.
- root 전체 engine911건(891+7+4+9) 성공, 종료0, 빌드1분21초다.
  field-cache-boxed-engine-full.log SHA-256
  `e240963868d2fedbb45fb97658f14bae0e95ad2f0b80021af831997bdfdb5144`.
  root는 여전히 FST 미패치다. 이번 boxed 수정 후 node/live/전체 성능 suite는
  미실행이며 이전 결과를 새 소스의 검증으로 재사용하지 않는다.
- field_cache.rs SHA-256
  `a03c0671a93aab98ff7b3763c7e73f98cd967c87c6c67727f9e9f4cd625a7af8`.
  `target/core-replacement-c06/field-cache-boxed-candidate/source`를 직전 bulk
  스냅샷에서 복사했다. 전체 diff에서 field_cache.rs만 다르며 FST/lock/다른
  소스는 동일하다. source.sha256 검증 성공, manifest SHA-256
  `d4f1eb62b30a45f637b04303bcd58544c83668d42b47e3762be49a82f67af43c`.
- RAM 여유 확보를 위해 이번 작업에서 만든 직전 bulk 컴파일 target에만
  cargo clean --release를 실행했다. 유효한 CACHEDIR.TAG를 확인했고 정상 종료0,
  1790파일/680.6MiB를 정리했다. 경로는
  `/run/user/1001/steelsearch-field-cache-bulk-build-20260909`다. 측정 중 정리하지
  않았으며 기존 v0.6.0/fbe 자료와 원래 terms-missing 임시 캐시는 건드리지 않았다.
  bulk 소스/manifest/빌드 로그/ABBA/전체 gate/디스크 artifacts 바이너리45c54895는
  보존했고 정리 후 바이너리 해시도 일치한다. cache-clean.log는 bulk 후보 폴더에
  있다. 이제 bulk 중간 컴파일 캐시는 보존되어 있다고 말하지 않는다.
- 다음 필수 작업은 boxed 고정 소스의 별도 release 빌드, 실행 파일 식별, 기능
  live/회귀, nested 원인 분리 진단 및 **전체 non-plugin 반복 suite**다. 단위 완료
  전에 최초 v0.6.0 고정 누적 처리량95%/각 시나리오 mean,p95,p99 지연105%,
  paired/기준선 drift/고정 OpenSearch 비교를 모두 유지한다. boxed 후보 성능은
  아직 미측정이며 최신 전체45c54895 FAIL을 취소하지 않는다. 정식 수락0/40,
  C02/C06 및 daemon lifecycle/cluster applied 검사 미완료, ledger 제외0,
  릴리즈 보류를 유지한다. 이번 검사와 정리 프로세스는 모두 종료했다.

#### C06 34458c17 boxed 후보 release/live (2026-09-09)

- 직전 boxed 구현/911건 engine 검사/고정 소스 확보는 진행이다. 이번에는
  boxed-candidate/source의 전체 manifest를 재검증하고 별도 target
  `/run/user/1001/steelsearch-field-cache-boxed-build-20260909`에서 release를 빌드했다.
  nightly/--locked/standalone-runtime/RUSTFLAGS=-Awarnings/jobs2/incremental0,
  7분41초, 종료0이다. 빌드 전후 소스 manifest 검증 성공이며 원래 발표 증거와
  이전 후보의 보존 소스/실행 파일을 변경하지 않았다.
- `target/core-replacement-c06/field-cache-boxed-candidate/candidate-build.log`
  SHA-256 `fb66401a665488a7adfa4590617d7060aed3117674575b622b73fd28d83c73a8`.
  RAM 원본과 같은 후보 폴더의 `artifacts/steelsearch` 복사본 모두 SHA-256
  `34458c179f4a7f521bfdef7e515bfbeb9c0974d8c7422d7d0504b909fce5f587`다.
  실제 검증은 디스크 복사본을 사용한다. 새 컴파일 캐시는 유지했고 측정 중 정리나
  다른 빌드/테스트를 하지 않았다. root에는 FST를 승격하지 않았다.
- `target/core-replacement-c06/field-cache-boxed-live`의 실제 OpenSearch3.7.0-SNAPSHOT
  비교는1816/1816 성공, 실패/skip0, 하위16실행과 전체 종료0이다. count probe=true,
  binary_unchanged=true, fixtures_unchanged=true. boxed 캐시와 FST를 결합한
  34458c17 실제 실행 파일의 결과다. execution.json SHA-256
  `b306d662627ffe30b2c134a6d25ddc8ba8e2b7b02ebe44bb46056ff1904e2245`.
  기존 daemon lifecycle/cluster applied 실패나 전역 검색 한계를 해결했다는 뜻은
  아니며, 성능 비교의 고정 OpenSearch2.19와도 구분한다.
- 다음은 최초 v0.6.0 db244133과 이 artifacts/steelsearch의 **전체 non-plugin
  반복 suite**다. 새 `target/core-replacement-c06/field-cache-boxed-repeated-full`
  경로에서 baseline/candidate/OS/OS/candidate/baseline 순서, 단일/3노드7연산,
  공개 고정 누적 처리량95%/각 시나리오 mean,p95,p99 지연105%, paired/기준선 drift를
  모두 검사한다. 필요 시 nested 변경 전후 ABBA 진단도 추가하되 전체 gate를 대신하지
  않는다. 완료 승인 전 전체 검증이 필수이며 최신 전체45c54895 FAIL은 유지한다.
  34458c17 성능 미측정, 정식 수락0/40, C02/C06 미완료, ledger 제외0,
  릴리즈 보류다. 이번 빌드/live 프로세스 모두 종료했다.

#### C06 34458c17 전체 반복 성능 결과: FAIL (2026-09-09)

- 직전 release 빌드와1816건 실제 live 성공은 진행이다. 이번에는 최초 db244133/
  boxed 후보34458c17/고정 OpenSearch2.19의 전체 non-plugin 반복 suite를 실행했다.
  여섯 실행 모두 종료0, 총12토폴로지 실행 요청 오류0, execution_inputs_verified=true,
  1094.76초(18분15초)다. numeric_budget_passed=false/acceptance=false, 전체 종료1.
  최신 실제 전체 결과는 **34458c17 FAIL**이다. 실행 중 편집/빌드/다른 테스트/캐시
  정리/재시작을 하지 않았으며 이전 실패 증거와 최초 발표 기준선을 그대로 보존했다.
- 공개 v0.6.0 기준은 후보01이43/44 통과(1초과), 후보04가38/44 통과(6초과)다.
  paired 기준은 각각40/44 통과(4초과),42/44 통과(2초과)다. 이전45c54895보다
  공개 실패 개수가 줄었다는 사실만으로 단일 변경의 인과적 개선을 단정하지 않는다.

| 실행 / 토폴로지 | 후보 처리량(req/s) | 최초 공개 v0.6.0 대비 | 고정 OpenSearch 대비 배수 |
| --- | ---: | ---: | ---: |
| 01 / 단일 | 746.7208 | +0.4993% | 2.5786 |
| 01 / 3노드 | 923.1245 | -0.8853% | 8.3113 |
| 04 / 단일 | 762.3849 | +2.6075% | 2.7115 |
| 04 / 3노드 | 919.6053 | -1.2632% | 8.2256 |

최초 공개 기준 지연 초과(%, 양수 악화, '-'는 해당 회 한도 이내):

| 3노드 지표 | 후보01 | 후보04 |
| --- | ---: | ---: |
| ranking p95 | - | 5.1656 |
| ranking p99 | - | 6.0638 |
| sort_filter p95 | 5.5393 | 5.1339 |
| sort_filter p99 | - | 8.9156 |
| nested p99 | - | 7.8344 |
| refresh p99 | - | 6.5758 |

- paired 후보01 초과는3노드 sort_filter mean+5.0569%/p95+6.7940%/
  p99+8.0073%, nested p99+6.3544%다. 후보04는3노드 ranking p99+5.8531%,
  nested p99+9.1906%다. 따라서 컨테이너 크기를24바이트로 줄인 것만으로
  nested 회귀가 해소됐다고 볼 수 없다. 공개/paired 중 유리한 결과를 선택하지 않는다.
- baseline00 drift 초과0개, baseline05는 단일 write p95+5.3357%/p99+7.2469%,
  facet p99+5.8177%, 3노드 sort_filter p99+5.8546%로4개 초과다. 이를 핑계로
  후보 실패를 면제하거나 기준선을 바꾸지 않는다. 모든 시나리오 mean/p95/p99와
  OpenSearch 비교는 result.json에 보존했다. dev 내구성과3노드 전역 검색 한계도
  유지하며 처리량 배수를 운영 대체 성능으로 해석하지 않는다.
- `target/core-replacement-c06/field-cache-boxed-repeated-full/result.json` SHA-256
  `46fbf266865abd0be09ac14d9d3ee7c9983086e846db1df980b3cd0aaad1a1be`,
  plan.json SHA-256
  `126a29831f4da5bacf0aad75485ed7a740abad73035c37deefe69446aa51e355`.
- 다음 원인 분리는 캐시 도입 전 fbe381d9와 boxed 후보34458c17의 같은 조건 ABBA다.
  이전 unboxed ABBA에서 nested p99가 두 쌍5% 이상 증가한 현상이 boxed에서도
  재현되는지 확인하고 실제 nested 호출 경로/필드 조회 비용을 조사한다. 국소 비교는
  진단이며 전체 gate의 대체물이 아니다. 추가 수정 시 기능 회귀/live와 **전체
  non-plugin 반복 suite**를 재실행하고 v0.6.0 고정 누적 처리량95%/각 시나리오
  mean,p95,p99 지연105%, paired/기준선 drift를 만족하기 전에는 단위 미완료다.
  최적화 불가를 입증하지 못해 ledger 제외0을 유지한다. 안전장치 완화/초과 예외는 없다.
- 모든 benchmark 프로세스 종료. 정식 수락0/40, C02/C06 및 기존 daemon 검사 실패
  미해결, root 후보 미승인, FST root 미승격, 커밋/태그/릴리즈 보류다.

#### C06 boxed 캐시 직접 ABBA: nested 초과 미재현, 다른 tail 초과 (2026-09-09)

- 직전 전체 gate는 실패 증거를 얻은 진행이다. 이번에는 캐시 도입 전 fbe381d9와
  boxed34458c17의 before/after/after/before3노드60초 혼합 ABBA를 실행했다.
  앞선 진단과 같은7연산/5000문서/384원문값/4clients/3shards/1replica/seed13,
  node counters 및 부하 후 refresh2회를 사용했다. 실행 파일/입력/실제 process
  검증을 유지하고 측정 중 변경/빌드/다른 테스트를 하지 않았다. 네 실행 요청 오류0,
  최종 종료0, 진단 error 없음이다. 전체 gate는 아니며 합격을 부여하지 않는다.

| 실행 | 바이너리 | req/s | refresh mean(ms) | refresh p99(ms) | commit 누적(s) |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | fbe381d9 | 919.6790 | 8.3081 | 23.0424 | 28.1156 |
| 1 | 34458c17 | 924.7358 | 8.4380 | 22.7881 | 28.7271 |
| 2 | 34458c17 | 917.7568 | 8.5282 | 23.8786 | 28.4453 |
| 3 | fbe381d9 | 924.6300 | 8.3083 | 22.6523 | 28.1314 |

- 0->1/3->2 대응 쌍의 처리량 변화는+0.5498%/-0.7433%다. nested p99는
  +0.9965%/+3.9938%로, unboxed ABBA의 두 쌍5% 이상 증가 현상은 이번 boxed
  직접 비교에서 재현되지 않았다. 이것이 v0.6.0 전체 gate의 nested 초과를 취소하거나
  크기 변경의 인과 효과를 단독 입증하는 것은 아니다.
- 첫 쌍에서5% 이상 증가한 지연 지표는 없었다. 두 번째 쌍에서는 lexical p99
  +5.5418%, ranking p99+6.5399%, refresh p95+5.1816%/p99+5.4135%,
  write p99+10.1183%가 증가했다. facet mean은-1.9837%/-0.7185%,
  facet p99는-5.1771%/-2.6045%였지만 다른 악화와 상쇄하지 않는다.
  refresh mean은+1.5638%/+2.6469%다. 모든7연산 mean/p95/p99는 baseline.json에
  보존한다. commit 누적은 준비 작업/worker join을 포함한 비원자적 노드 합이며
  순수 merge CPU 시간이나 HTTP 지연 기여율로 해석하지 않는다.
- 모든 endpoint/time 관측의 native/fallback count가 일치했다. 마지막 drain의
  endpoint 값은[6240,4241,4317], [6259,4252,4336], [6215,4232,4334],
  [6240,4252,4348]이다. 합계14798/14847/14781/14840는 seed+성공 쓰기 수와
  일치하지만 전역 ID/content 고유성 검증은 아니다. 콘솔 observed는 첫 endpoint의
  시간별 관측이라는 구분도 유지한다.
- `target/core-replacement-c06/field-cache-boxed-abba/result.json` SHA-256
  `d60d17587c7d5e0e440776a4f5d52925b6e94f1467d88c2c54d666d8f292a0d9`,
  plan.json SHA-256
  `a536a49f51931c97bae04d6792b8c53c5edcba1e8265faaf90f3793d310a7d24`.
- 코드와 기존 P03 기록을 대조했다. 실제 nested 페이지 경로는
  search_hits_page_for_query_native_scoped -> native_nested_candidate_ids_scoped,
  child ordinals/parent ID 조회/페이지 hit 생성이다. NestedChildDocument는 source와
  parent 식별자만 가지며 새 최상위 FieldCache를 직접 조회하지 않는다.
  별도 full-hit 경로의 child-ordinal 증명 중복 계산을 현재 벤치마크 병목이라고
  단정하지 않는다. shared document 배치/할당/혼합 경쟁과 직접 조회를 구분한다.
- 다음 검토 대상은 FieldCache 생성의 반복 키 비교와 할당이다. 작은 캐시 생성 때의
  중복 탐색과 큰 캐시 전환 작업을 줄일 수 있는지 원문 값/중복 키 last-wins 의미를
  유지한 독립 검사로 먼저 확인한다. 임의 hash/잘못된 prefix shortcut/안전장치 완화는
  도입하지 않는다. 런타임 수정 시 기능 회귀/live 및 **전체 non-plugin 반복 suite**를
  다시 실행하고 최초 v0.6.0 고정 누적 처리량95%/각 시나리오 mean,p95,p99 지연105%,
  paired/기준선 drift를 만족하기 전에는 단위 미완료다. 이번에는 런타임 수정이 없다.
- 최신 전체34458c17 FAIL, 정식 수락0/40, C02/C06 및 daemon 검사 미해결,
  최적화 불가 미입증/ledger 제외0, 릴리즈 보류다. 모든 진단 프로세스 종료했다.

#### C06 캐시 생성의 일괄 중복 처리 후보 (2026-09-09)

- 직전 boxed ABBA와 실제 nested 호출 경로 확인은 진행이다. 이번에는 FieldCache
  생성의 항목별 선형 중복 탐색을 제거했다. 입력을 Vec로 모아8개 이하는 안정 정렬과
  dedup_by로 마지막 값을 유지한다. 큰 입력은 BTreeMap 일괄 생성으로 넘기고,
  중복 제거 후 고유 키8개 이하인 경우 Small로 정규화한다. 24바이트 컨테이너,
  조회 방식, key 정확 비교, 원문 추출/fallback/보안/내구성/bucket 예산은 유지한다.
  입력 전체를 일시 Vec에 모으므로 생성 중 메모리 동작이 같다고 주장하지 않는다.
- 중복이 많은 입력의 고유 키1/2/8/9/16, 입력 수1/7/8/9/17/64 조합에서
  BTreeMap과 값/정규화 표현을 대조하고 owned String clone 후 원본 drop도 검사했다.
  독립 검사6건 성공, 실제 root engine 전체912건(892+7+4+9) 성공, 종료0이다.
  빌드1분22초. `target/core-replacement-c06/field-cache-construction-engine-full.log`
  SHA-256 `5df626d675ea55e0db76f03d7cf58b6db3b195049fbc2cf31d77d58cf452918a`.
  root는 FST 미패치이며 이번 수정 후 node/live/서비스 성능은 미검증이다.
- 동일 tools/bench-field-cache-lookup.rs로 수정 전후 독립 진단 바이너리를 빌드하고
  before/after/after/before 순서로 실행했다. 각 실행은 기존5000문서/8필드 수 조건/
  4라운드 순서 반전/16회 조회이며 네 실행 모두 종료0, 값/checksum 검사 성공이다.
  결과는 `target/core-replacement-c06/field-cache-construction-diagnostic/`에 있다.
  아래 범위는 각 실행 내부4회 생성 시간 평균의 두 실행 범위(ms)이며 서비스 성능이 아니다.

| 필드 수 | 수정 전 생성(ms) | 수정 후 생성(ms) |
| --- | ---: | ---: |
| 0 | 0.042 | 0.054~0.057 |
| 1 | 0.690~0.708 | 0.495~0.509 |
| 3 | 1.539~1.622 | 1.427~1.442 |
| 8 | 4.269~4.360 | 3.628~3.665 |
| 9 | 5.065~5.126 | 4.377~4.413 |
| 16 | 11.628~11.801 | 9.611~10.732 |
| 64 | 35.092~35.311 | 33.747~34.144 |
| 256 | 126.687~128.478 | 125.097~125.469 |

- 조회는16필드 전12.313~14.069ms/후13.088~13.885ms,64필드 전23.694~24.200/
  후24.422~25.936,256필드 전49.450~53.067/후51.920~56.435로 불리한 관측도
  있다. 생성 개선만으로 채택하지 않는다. 변경된 할당/코드 배치와 노이즈를 구분할
  필요가 있으며 이 마이크로벤치마크는 HTTP latency gate를 대신하지 않는다.
- 위 진단 디렉터리에 전후 실행 파일/수정 후 소스/4개 CSV/레이아웃 로그를 보존했다.
  전 binary SHA-256 `88e5acf1957710d02f31be5a27b41e6c6f3623675e0f9ca26800837544665a75`,
  후 binary SHA-256 `4b9436511b97f8b4926ef22c9f55e379163e75f8c3acf42dd66c4f63f920cd93`.
  이는 진단 도구 바이너리이며 steelsearch 실행 파일이 아니다. runtime field_cache.rs
  SHA-256 `07ca48bd93120f9cd7e02312d59387b50331db4ceaa987e142f78854331a11ab`.
- `target/core-replacement-c06/field-cache-construction-candidate/source`는 boxed
  보존 스냅샷에서 field_cache.rs만 교체했다. 전체 diff와 manifest 검증 성공,
  source.sha256 SHA-256
  `1eec44a17dc9264a8260dcfd1f2085e23f7c8d93182cc0c7d16b7ae1210739ad`.
- 다음 빌드 RAM 공간 확보를 위해 유효한 CACHEDIR.TAG가 있는 본 작업의 boxed
  전용 target `/run/user/1001/steelsearch-field-cache-boxed-build-20260909`에만
  cargo clean --release를 실행했다. 종료0,1790파일/680.6MiB 정리. 측정 후 실행이며
  원래 v0.6.0/fbe 자료와 기존 terms-missing 캐시는 그대로다. boxed 소스/빌드 로그/
  live/ABBA/전체 gate 및 디스크34458c17 바이너리는 보존했고 해시를 재확인했다.
  boxed 중간 컴파일 캐시는 더 이상 보존됐다고 말하지 않는다.
- 다음 필수 작업은 고정 후보의 별도 release 빌드, 실제 바이너리 기능 live 및 **전체
  non-plugin 반복 suite**다. 최초 v0.6.0 누적 처리량95%/각 시나리오 mean,p95,p99
  지연105%, paired/기준선 drift/고정 OpenSearch 비교를 모두 만족하기 전에는 단위
  미완료다. 새 후보 서비스 성능 미측정, 최신 전체34458c17 FAIL, 정식 수락0/40,
  C02/C06 및 daemon 검사 미해결, ledger 제외0, 릴리즈 보류. 모든 실행 종료했다.

#### C06 일괄 생성 후보 d162d500 live 및 전체 성능 결과 (2026-09-09)

- 위 고정 source를 별도 RAM target
  `/run/user/1001/steelsearch-field-cache-construction-build-20260909`에서
  nightly release/locked/standalone-runtime, jobs2, incremental0으로 빌드했다.
  7분40초, 종료0. 빌드 후 source.sha256 검증 성공. 보존 실행 파일은
  `target/core-replacement-c06/field-cache-construction-candidate/artifacts/steelsearch`,
  SHA-256 `d162d500ffdae5f1b5c175875f322ea26ab91a9f3550ca78596060d1086db44b`.
  RAM 원본과 디스크 사본 해시가 일치한다. candidate-build.log SHA-256
  `514d2569a5b39c500f568d5c0d86cfb7bc6381eb554d73bf5d51b102d7611a98`.
  root FST는 미패치이며 이 실행 파일은 기존 고정 FST 패치를 포함한 실험이다.
- `target/core-replacement-c06/field-cache-construction-live`에서 실제 보존 실행
  파일로16개 fixture,1816건 성공/실패0/skip0, 모든 하위 실행 종료0이다.
  count probe 성공, binary/fixtures unchanged=true. 기능 참조는 OpenSearch
  3.7.0-SNAPSHOT이며 아래 성능 참조2.19와 구분한다. execution.json SHA-256
  `d23e617b48af3f2831a3e474bcb162dafee8646ea3ee648c6b02d566168a13f8`.
- **전체 non-plugin 반복 suite**를
  `target/core-replacement-c06/field-cache-construction-repeated-full`에서 실행했다.
  최초 v0.6.0 db244133, 후보 d162d500, 고정 OpenSearch2.19를
  baseline/candidate/OpenSearch/OpenSearch/candidate/baseline 순서로 측정했다.
  기존5000문서/384 source values/4clients/7연산 혼합/각 topology60초/seed13,
  단일 및3노드, 기존 내구성/보안/자원 설정을 유지했다. 측정 중 빌드/테스트/수정은 없다.
  1092.6042초(18분13초),6개 하위 실행 종료0,12개 topology 요청 오류0,
  execution_inputs_verified=true. 최종 종료1, numeric_budget_passed=false,
  acceptance_established=false다. 최신 전체 성능 판정은 **d162d500 FAIL**이다.

| 후보 회차 | topology | 처리량 ops/s | 최초 v0.6.0 대비 처리량 | 해당 OpenSearch 회차 대비 |
| --- | --- | ---: | ---: | ---: |
| 01 | single-node | 750.5355 | +1.0127% | 2.5981배 |
| 01 | three-node | 915.3940 | -1.7153% | 7.9016배 |
| 04 | single-node | 762.4083 | +2.6106% | 2.6037배 |
| 04 | three-node | 927.1339 | -0.4548% | 8.0735배 |

- published 비교는 각 회차43/44통과,1실패다. 01의 three-node sort_filter p99는
  원래10.9585745ms ->11.5351910ms(+5.2617843%, 허용11.5065032ms),
  04의 three-node facet p99는13.1208765ms ->13.8039441ms
  (+5.2059604%, 허용13.7769203ms)다. 작은 초과라도 반올림/평균/상쇄로 통과시키지 않는다.
- fresh paired 비교는01의44/44통과,04의43/44통과다. 04 three-node write p99는
  7.0944726ms ->7.4740616ms(+5.3504892%)로 실패다. published FAIL을 paired의
  좋은 회차로 대체하지 않는다. 모든 시나리오 mean/p95/p99 및 OpenSearch 값은
  result.json과 각 summary.json에 보존하며 위 표는 처리량 요약이다.
- baseline00 자체 drift도6개 실패했다. single refresh p99+9.9663%,
  three lexical p99+7.4932%, ranking p99+6.9490%, facet p99+8.1595%,
  nested p99+11.3515%, refresh p99+5.1283%다. baseline05 drift 실패0.
  이 변동을 근거로 후보 실패를 면제하거나 통과할 때까지 전체 suite를 재시도하지 않는다.
- result.json SHA-256
  `a440b9e8965441d3f0a0b1e07e93c889824a64bc3cd6efd4219147ebf17e5b18`,
  plan.json SHA-256
  `9d355d906cf1b5fe611d8bfc71e4c7d26624fa5548756aca1dab19b92c781a28`.
- 다음 진단은 생성 변경 전34458c17과 후d162d500의 사전 고정 mixed3node ABBA다.
  쓰기/refresh 작업량과 모든7연산 지연을 함께 보존하여 생성 최적화의 영향과
  기준선 변동을 구분한다. 이 직접 비교는 아직 실행하지 않았으며 채택/제외 근거로
  선취하지 않는다. 실제 병목이 확인된 경로만 수정하고 기능/안전장치는 유지한다.
  이후 런타임 변경마다 기능 회귀/live 및 **전체 non-plugin 반복 suite**를 실행해야
  단위 완료를 판단할 수 있다. 최초 v0.6.0 고정 누적 처리량95%/각 시나리오
  mean,p95,p99 지연105% 기준과 반복/paired/drift 판정은 그대로 유지한다.
- 정식 수락0/40, C02/C06 및 기존 daemon 검사 미해결, ledger 제외0, 릴리즈 보류다.
  이 최적화가 단독으로 >=5% 저하를 유발하며 최적화 불가능하다고 입증하지 않았으므로
  기능 제외로 처리하지 않는다. 이번 빌드/live/전체 gate 프로세스는 모두 종료했다.

#### C06 생성 변경 직접 ABBA와 정렬 CPU 진단 (2026-09-09)

- 직전 turn은 d162d500 빌드/live/전체 suite 결과를 확보한 progress다.
  이번 시작 시 두 보존 바이너리 해시와 실행 중인 빌드/부하가 없음을 확인했다.
  `field-cache-construction-abba`에서34458c17 ->d162d500을 전/후/후/전으로
  고정해3노드60초 혼합 부하4회 및 node counters/post-load refresh2회를 실행했다.
  기존5000문서/384 source values/4clients/3shards/replica1/seed13을 유지했다.
  모든 실행 요청 오류0, 최종 종료0, 도구/실행 파일/소유 프로세스 확인 성공이다.

| 실행 | 후보 | 처리량 ops/s | refresh mean ms | refresh p99 ms | commit 누적 초 |
| --- | --- | ---: | ---: | ---: | ---: |
| 00 | 변경 전34458c17 | 905.6856 | 8.5215 | 23.1513 | 28.1328 |
| 01 | 변경 후d162d500 | 926.2164 | 8.3394 | 23.5042 | 28.6524 |
| 02 | 변경 후d162d500 | 932.6518 | 8.2636 | 21.9791 | 28.2869 |
| 03 | 변경 전34458c17 | 922.5296 | 8.5000 | 22.8836 | 29.3143 |

- 사전 쌍00->01/03->02 처리량+2.2669%/+1.0972%, facet mean
  -2.1697%/-2.5720%, facet p99-1.9295%/-4.7220%, nested p99
  -7.1061%/-2.1103%다. 첫 쌍 sort_filter p99는 **+6.8684%**로 악화했고
  두 번째는-3.4535%다. 첫 쌍 ranking p99+0.8165%, refresh p99+1.5244%,
  두 번째 lexical mean+0.2484%/p99+0.3138%, nested p95+1.3563%,
  write mean+0.1688%도 누락하지 않는다. 두 번째 쌍의 >=5% 지연 악화는 없다.
  모든7연산 mean/p95/p99 원본은 각 baseline.json에 보존했다.
  이번 결과는 생성 변경의 일관된 >=5% 악화나 최적화 불가를 입증하지 않는다.
- 모든 endpoint/time의 native/fallback count는 일치했다. 마지막 drain 값은
  [6179,4205,4279], [6239,4252,4371], [6312,4255,4351],
  [6216,4264,4345]이며 합계14663/14862/14918/14825는 seed+성공 쓰기다.
  합계는 전역 ID/content 고유성 증거가 아니다. 콘솔 observed3개는 첫 endpoint의
  시간별 관측이다. commit 누적은 준비 과정/worker join을 포함한 비원자적 노드 합이며
  순수 merge CPU 또는 HTTP 지연 분해가 아니다.
- `target/core-replacement-c06/field-cache-construction-abba/result.json`
  SHA-256 `a5840d35b8d28ee9ac495b86165f52f9d2cbfe657b7afef97ee151fd61f2c868`,
  plan.json `1bcb01192d58072d8fe7457d1f9a51228118ca443d29901d101c7d1627df99d8`.
- 후속 `construction-sort-cpu`는 같은d162d500/3노드/45초 sort_filter=100에
  cpu-clock499Hz/20초 capture를 수행했다. perf/matrix 종료0, lost samples0,
  실행 파일 불변,62580요청 오류0. 관측24.1456초, 부하 생성기CPU24.31초,
  서버5.03/4.99/9.41초다. 프로파일 부하mean2.8657/p954.9919/p996.2626ms,
  1390.6337ops/s는 혼합 부하나 비프로파일 결과와 합치지 않는다.
- 서버 PID 필터 self 표본은 _mi_page_malloc_zero2.97%, f64직렬화2.51%,
  Value배열복사1.43%, mi_free1.00%, Value직렬화0.94%다. 이는 전체 capture 분모이며
  서버 정규화 비율이나 HTTP p99 기여율이 아니다. CPU 측정은 off-CPU 대기를 제외한다.
  children 표본과 실제 코드를 대조해 search_hits_page_for_query_native_sharded_tantivy
  ->collect_sharded_page_candidates 경로를 확인했다. 별도 full_native_sort를
  이번 정렬 부하의 주경로라고 단정하지 않는다. 응답은 기존 into_opensearch_body다.
- `target/core-replacement-c06/construction-sort-cpu/diagnostic.json` SHA-256
  `3a1fa0973a517fbecc77be235b4c41bb0c7efa79b41b4103756553de8eb4f460`,
  perf.data `fe0a73593b2a3f451eb7ce8a274c9690615b984f59751c9a1cb80fcb944702ba`.
- 다음 구현 검토 지점은 위 sharded 함수의 명시적 필드 정렬 분기다. 현재 모든 샤드
  후보의 원문을 SearchHit로 복사한 뒤 sort_hits와 최종 페이지 선택을 수행한다.
  관련도 경로는 이미 선택 후 materialize하므로 다시 구현하지 않는다. 필드 정렬에도
  불필요한 원문 복사를 줄일 수 있는지 기존 comparator/배열/null/missing/동점/offset/
  sort 값 계약과 eager reference를 먼저 대조한다. 기존 typed materializer를 재사용하고
  지원 옵션을 축소하거나 별도 부정확한 정렬을 도입하지 않는다. 실제 수정 후에는
  기능 회귀/live 및 **전체 non-plugin 반복 suite**를 필수 실행한다. 최초 v0.6.0 고정
  누적 처리량95%/각 시나리오 mean,p95,p99 지연105%, paired/drift 기준을 유지한다.
- 이번에는 런타임 수정 없이 원인 분석 근거를 확보했다. 전체d162d500 FAIL은 유지하며
  정식 수락0/40, C02/C06 및 daemon 검사 미완료, ledger 제외0, 릴리즈 보류다.
  모든 ABBA/프로파일 프로세스가 종료했다.

#### C06 필드 정렬의 페이지 선택 후 원문 생성 및 배열 회귀 수정 (2026-09-09)

- 직전 turn은 직접 ABBA/현재 실행 경로 프로파일 근거를 확보한 progress다.
  현재 root에서 sharded 명시적 정렬 분기를 수정했다. collect_sharded_page_candidates의
  기존 typed materializer로 (&StoredDocument, score)를 반환하고, 전역 정렬과
  skip(from).take(size) 후에만 SearchHit/원문을 생성한다. 기본 관련도 분기는 유지한다.
- 기존 compare_hits_by_sort와 missing 판정은 내부 SortHitInput(id,score,&source)을
  받도록 분리하고 기존 SearchHit 호출자는 wrapper로 연결했다. 실제 비교 본문은
  그대로 재사용한다. 동일 인덱스 후보의 ID 동점, 점수 bits, null/missing 방향,
  script/geo 분기, source 기반 재점수, 샤드 범위, native 지원/fallback 조건을 유지한다.
  최종 페이지의 sort 값은 기존 materialize 함수로 생성한다. 모든 후보 원문을
  복사한 뒤 버리는 비용은 제거했지만 comparator의 값 추출 비용은 남아 있다.
- eager 대조 테스트를2016 ->4704개 조합으로 확장했다. 기존1/3샤드 및2047/2048문서,
  old/new refresh snapshot,7쿼리,4범위,4페이지 조건에7정렬을 조합한다.
  다중 필드/asc/desc/max/정수 missing/_id/_score를 추가하고 nullable/빈 배열/
  숫자 배열/스칼라 source를 섞었다. nonempty 명시적 native 페이지 사례도 별도 집계한다.
- 첫 테스트 명령은 --exact에 모듈 접두사가 없어0건 실행됐다. 성공 근거로 쓰지 않는다.
  그다음 필터 없는 엔진 전체는891성공/1실패, 종료101이었다. 확장 테스트가
  eager reference의 sort_hits에서 total-order 위반으로 panic했다. 백트레이스가
  새 지연 생성 분기 이전의 실패를 확인한다. 보존d162d500 source에도 최상위 값을
  그대로 반환하는 source_sort_value가 있다. 이전 실행 파일의 HTTP panic까지
  재현한 것은 아니다. eager와 새 경로는 comparator를 공유하므로 완전히 독립된
  OpenSearch 의미 oracle이라고 주장하지 않는다.
- 최상위 source_sort_value는 배열/Null을 그대로 반환하지만 중첩 값 선택은
  정렬용 scalar를 고르고 null을 건너뛰는 불일치를 확인했다. 기존 중첩 reducer를
  select_source_sort_value로 추출하여 최상위 배열에도 재사용했다. null은 missing,
  빈 배열/all-null은 값 없음, 기본 asc min/desc max 및 min/max/avg/sum을 적용한다.
  최상위 스칼라 빠른 경로와 실제 dotted key 우선순위는 유지한다. 최소 테스트에서
  위 값 선택을 직접 기대값과 비교한다. 이 기능 수정은 최적화와 구분해 HTTP 검증한다.
- 수정 후 첫 재빌드는 디스크 ENOSPC로 rustc 종료101이었다. 측정 중이 아니며
  관련 프로세스 종료를 확인한 뒤 유효 CACHEDIR.TAG가 있는 본 작업 전용
  `target/core-replacement-c06/fst-isolated-candidate/build`에 cargo clean --profile dev를
  실행했다. 종료0,2118파일/1.3GiB debug 캐시 정리. source/원본 테스트 로그/성능 자료와
  release/steelsearch는 보존했고 adc3660b 해시를 전후 재확인했다. 과거 FST debug
  중간 산출물이 계속 보존됐다고 말하지 않는다. 다른 target/사용자 파일은 정리하지 않았다.
- 동일 수정 소스로 엔진 전체를 재실행해 **913건(893+7+4+9) 성공**, 실패/skip0,
  종료0이다. 빌드1분40초, 실행14.71/14.67/3.19/0.32초. 확장 eager 및 최소 배열
  회귀 테스트 모두 성공이다. root는 여전히 FST 미패치이며 node/live/새 release 성능은
  아직 검증하지 않았다. 최신 전체 서비스 판정은 이전d162d500 FAIL로 유지한다.
- root engine SHA-256 `ce766d34ad67a42227a65e457b5126af26f005ce4cc0c61bc640b2b2a2681ff5`.
  `target/core-replacement-c06/`의 증거:
  - deferred-field-sort-engine-full.log:
    `e7398e7dfedeb2b077560ff1e57f91cbf68383474a2af0efa06afe8f4e181305`.
  - deferred-field-sort-failure-trace.log:
    `2ba71cc6493b513cde9eff707fc5dd9f2edbed379fa4095ebbb2815165163f84`.
  - deferred-field-sort-engine-full-fixed.log(ENOSPC):
    `d2ffd2ea574168c048813c66a7abfcdff328c9992888d5a4132aae524244d75f`.
  - deferred-field-sort-engine-full-fixed-recovered.log:
    `fe1008ae6d866299eff2eb15c471104223446c90892e26d8f4adc7defced2c4a`.
  - fst-isolated-candidate/debug-cache-clean.log:
    `17a9fda1adf0a6e863d4934bf0a53b81a407f1db976f7841c4a7635099e4166c`.
- 다음 필수 검증은 배열/null/missing/모드/페이지 및 native/fallback HTTP fixture,
  별도 고정 source/release 빌드, node 및 확장 live, **전체 non-plugin 반복 suite**다.
  fixture는 공유 comparator와 독립적인 실제 OpenSearch 응답을 비교해야 한다.
  최초 v0.6.0 누적 처리량95%/각 시나리오 mean,p95,p99 지연105%, paired/drift와
  고정 OpenSearch 비교를 유지한다. 실패하면 원인 분석/최적화/전체 재검증하며,
  이번 unit test 통과나 복사 감소를 기능 단위 완료로 세지 않는다.
- 정식 수락0/40, C02/C06 및 daemon 검사 미해결, ledger 제외0, 릴리즈 보류.
  이번 테스트/빌드 프로세스 모두 종료했고 git diff --check 성공이다.

#### C06 배열 정렬 HTTP 대조 및 REST null 처리 수정 (2026-09-09)

- 직전 turn은 원문 지연 생성/배열 정렬 수정과 엔진913건 성공 근거를 확보한
  progress다. 현재 engine ce766d34와 소유 빌드/부하 부재를 확인했다.
- `tools/fixtures/search-source-array-sort-compat.json`을 추가했다. 1/3샤드에
  동일8문서(숫자 배열+null/스칼라/null/빈 배열/all-null/누락/음수)를 넣고,
  asc/desc/min/max/avg/sum/median/missing-first/custom-missing/from/size0/
  범위 밖 페이지/search_after를 일반 요청과 ignore_unavailable=false 요청으로
  비교하는52건이다. ID 순서뿐 아니라 원문/total/실제 sort 값도 대조한다.
  경로 이름의 native/fallback은 요청 형태 라벨이며 native 실행을 입증하는 계측이
  아니다. 배열 정렬의 기존 fallback 선택은 유지했다. fixture SHA-256
  `e3bad9175af19c8a118998f6e519a494a25da61c14e026a25d4a3a211c540099`.
- 먼저 현재 root의 debug standalone-runtime을 빌드했다(1분18초, 종료0).
  `target/core-replacement-c06/deferred-field-sort-debug/steelsearch` SHA-256
  `9c84c10b6c738e8cf8c9db624d07c6d95be2d818e066721dfc4308c71fc0da6b`.
  `deferred-field-sort-array-live`는 새52건 중20성공/32실패/skip0,
  기존 nested160+160 및 core1180 모두 성공, 최종 종료1이다.
  execution.json `791f6e891e5a60da0782518dfea8199349ee42d50766ff2647e138d6e90963f9`.
- 32실패는 모두 양쪽HTTP200의 내용 차이였다. REST reduce_sort_values_by_mode의
  min은 null을 최솟값으로 고르고 sum은 all-null을0으로 반환했다. engine 수정만으로
  이 fallback 결과는 해결되지 않았다. REST min/max에서 null을 제외하고 sum을
  유효 숫자가 없으면 None을 반환하는 reduce로 변경했다. 유효 합0은0으로 보존한다.
  빈/all-null에 모든5mode가 None인지, 혼합 배열의 각 기대값을 직접 검사하는 회귀 추가.
- 정수 매핑 avg/median 차이는 별도다. 실제 OpenSearch3.7.0-SNAPSHOT은
  [-3,8]의 평균/중앙값2.5를3, [null,9,2,5]의 평균5.333...을5로 렌더링했다.
  현재 REST는 소수 값을 유지한다. 이번에는 이 차이를 수정하거나 지원 제외하지 않았다.
  median은 REST에서 이미 처리되므로 미지원 오류라고 잘못 분류하지 않는다.
- node library 전체 **655건 성공**, 실패/skip0, 종료0(빌드59.58초, 실행6.28초).
  main 바이너리 단위 테스트나 daemon 통합 전체 성공을 뜻하지 않는다.
  `sort-null-node-lib.log` SHA-256
  `2f50908428a646fd269884f7b6a2c3cbf25388bf627c9efb570afa81935b32fa`.
  standalone_runtime.rs SHA-256
  `ba3776fc6a067584a473d183003126808cf6218121a3b0378736498eff55882f`.
- 재빌드46.41초 종료0. `target/core-replacement-c06/sort-null-debug/steelsearch`
  SHA-256 `bf48cf9739701da576d5891807cc4ef2f2c936d9c59d614a0bb888b7ed17bbf6`.
  이전 debug 실행 파일/실패 보고서를 보존했다. 같은 fixture 그대로 실행한
  `sort-null-array-live`는 **44/52성공,8실패**, 기존 핵심1500건 모두 성공이다.
  합계1544성공/8실패/skip0, 최종 종료1, binary/fixtures unchanged=true.
  기능 참조3.7.0-SNAPSHOT이며 성능 참조2.19와 다르다. execution.json SHA-256
  `2a9c247b4ba5ca6447aa205a2c0ce2bbf4906abc2e695342903203175980d624`.
  24개 차이가 해결됐고 남은8개는1/3샤드 avg/median 일반/fallback 요청이다.
- 다음은 매핑 기반 avg/median 정수 계산을 정렬/after/rendering에 일관되게 적용하는
  수정이다. MappedSearchSort의 기존 values/compare/after/append_values 경계를 검토하며,
  출력만 반올림하는 부분 수정을 피한다. 음수/양수 half, 동점, 범위, double 유지,
  혼합 인덱스와 search_after를 독립 OpenSearch fixture로 검증해야 한다.
  수정 후 node/engine 관련 회귀와 확장 live, 별도 고정 release 빌드 및 **전체
  non-plugin 반복 suite**를 실행하기 전 단위 완료로 세지 않는다. 최초 v0.6.0 고정
  누적 처리량95%/각 시나리오 mean,p95,p99 지연105%, paired/drift 기준을 유지한다.
- 새 release/전체 성능은 미실행이며 최신 전체d162d500 FAIL이다. 정식 수락0/40,
  C02/C06 및 daemon 미완료, ledger 제외0, 릴리즈 보류. 이번 실행 프로세스 모두 종료,
  git diff --check 성공이다.

#### C06 정수 avg/median 계산의 JVM 대조 (2026-09-09)

- 직전 turn은 REST null 처리로 HTTP 차이24건을 해결한 progress다. 이번에는
  로컬 OpenSearch MultiValueMode.java의 실제 정수 AVG/MEDIAN을 확인했다.
  소스 checkout HEAD는 f991609d190dfd91c8a09902053a7bbfe0c27b3e,
  파일 SHA-256 `6ee0e94e2ee2b6a04db1076dea469c3e3d5d2af1ab01c1d31f61abc1d1991364`다.
  AVG는 Java long 합산(overflow 포함) 뒤 다중 값만 Math.round, MEDIAN은 정렬된
  중앙 원소를 그대로 반환하거나 짝수 개일 때 두 중앙 값의 double 평균을 Math.round한다.
  double 필드는 이 정수 규칙과 다르다. checkout HEAD만으로 실행 JVM의 source 동일성을
  증명하지 않으며 기존 실제 OpenSearch HTTP 관측과 구분한다.
- `crates/os-node/src/integer_sort_mode.rs`에 계산 후보를 추가했다. 아직 lib.rs에
  등록하거나 REST 서버에 연결하지 않았다. i64 wrapping 합산, 홀수 중앙값/단일 값
  정밀도, 음수 half의 양의 방향 반올림, double->long 포화를 보존한다.
  floor(x+0.5)는 큰 정수에서 잘못 반올림할 수 있어 floor와 소수부를 분리한다.
  독립 rustc 테스트3건 성공: half 경계 인접 double,2^52+1,2^53+1,i64 MIN/MAX,
  empty/중복/비정렬 입력과 overflow를 포함한다. 성능 개선 증거는 아니다.
- `target/core-replacement-c06/IntegerSortReference.java`는 확인한 Java 산술을
  Math.round로 실행하고 integer-sort-reference.rs는 새 helper를 호출한다.
  동일 xorshift64 seed, 길이1..17 각각256회인4352배열의 avg/median8704값을
  순차 실행했다. JVM21.0.12, 두 실행 종료0, cmp 종료0,4352행 전체 일치다.
  이 Java 도구는 OpenSearch 전체 실행이 아니며 매핑/coercion/누락/HTTP를 검증하지 않는다.
- helper SHA-256 `1008e9ef6fe508ad47264c02b60df61fd5282d2de819a7d2923f2dfad0d4464a`.
  integer-sort-mode-tests.log `96b0dfa07d42462b46edf59f4bfff6ddb092eedb6dce153b5b101ba1f6d92a84`.
  integer-sort-rust.tsv/java.tsv 동일 SHA-256
  `50b9bd1a35e40d9b3bbb02d961f58c5e588ea72b4133b2fe2d39aa3c06b31940`.
- 다음은 기존 MappedSearchSort의 values/compare/after/append_values에 매핑별 정수
  계산을 연결하는 작업이다. double/numeric_type/혼합 인덱스/원문 값 변환과 missing을
  별도 검증하며 출력만 반올림하지 않는다. 독립 HTTP fixture의 음수 half/동점/
  search_after도 확장한다. 연결 후 node/engine 회귀/live와 별도 release의 **전체
  non-plugin 반복 suite**를 필수 실행한다. 최초 v0.6.0 고정 누적 처리량95% 및
  각 시나리오 mean,p95,p99 지연105%, paired/drift 판정을 유지한다.
- 서버 미연결이므로 HTTP avg/median8건 미해결, 최신 runtime bf48cf97 기능44/52,
  최신 전체 성능d162d500 FAIL을 유지한다. 정식 수락0/40, ledger 제외0, 릴리즈 보류.
  이번 독립 실행 모두 종료했다.

#### C06 정수 모드 매핑 연결 및 52건 HTTP 통과 (2026-09-09)

- 직전 turn은 계산 helper와 JVM4352입력 대조를 확보한 progress다. 이번에는
  lib.rs에 integer_sort_mode를 등록하고 MappedSearchSort에 연결했다.
  descriptor를 Keyword/IntegerMode로 구분하며 정수 유효 타입의 avg/median에만
  새 계산을 적용한다. numeric_type이 있으면 매핑보다 우선하고 double은 기존 경로다.
  일반 정렬에는 descriptor를 만들지 않는 빠른 진입 조건을 유지한다.
- values의 동일 결과가 order_hits/after/append_values에 쓰인다. 원문 경로 조회와
  기존 숫자 docvalue 배열 평탄화를 사용하고, 유효 값 전체가 i64일 때 정수 reducer를
  호출한다. null/빈 배열은 missing으로 유지한다. 문자열/소수 원문은 기존 계산으로
  돌아가며 mapping-aware coercion을 완료한 것이 아니다. 이 제한을 지원 제외나
  오류로 대체하지 않았고 후속 검증/구현 대상이다. null_value/ignore_malformed,
  numeric_type 변환, 혼합 매핑의 missing도 전체 지원으로 주장하지 않는다.
- 새 통합 테스트는 avg/median의 음수 half, 반올림 후 동점, long/double 혼합,
  search_after 및 렌더링 값 일치를 검사한다. numeric_type=double에서 정수 descriptor를
  만들지 않는 것도 확인한다. 기존 keyword descriptor 검증과 안전 조건은 유지한다.
- 첫 node library 전체는658성공/1실패였다. 기존 long scores=[2,9] 평균 테스트가
  5.5를 기대했으나 새 결과는6이었다. 실제 매핑long과 확인한 OpenSearch/JVM 규칙에
  맞춰 이 기대값 및 정수 표현만 수정했다. 이전 실패 로그는 보존했다.
  이후 전체 **659건 성공**, 실패/skip0, 종료0(빌드53.54초, 실행5.69초).
  main/daemon 전체 검사 성공을 뜻하지 않는다.
- 공간220MB에서 빌드 전 valid target/CACHEDIR.TAG와 별도 보존 bf48cf97/9c84c10b
  실행 파일 해시를 확인하고 cargo clean -p os-node --profile dev를 실행했다.
  종료0,109파일/2.8GiB debug 캐시 정리. 소스/보존 debug 서버/로그/릴리즈/측정 자료는
  유지한다. root의 과거 os-node debug 테스트 실행 파일은 더 이상 남아 있다고
  가정하지 않는다. integer-sort-node-cache-clean.log에 정리 결과를 보존했다.
- debug 빌드44.10초 종료0. `target/core-replacement-c06/integer-sort-debug/steelsearch`
  SHA-256 `8056a58a921f403c8361c57a56830dddb1a0c1879ea382eadac5ba0815a0398e`.
  같은52건 fixture를 변경 없이 실제 OpenSearch3.7.0-SNAPSHOT과 대조했다.
  **52/52성공**, 남았던 avg/median8건 해결. 기존 nested160+160/core1180도 성공,
  합계1552성공/실패0/skip0, 종료0, binary/fixtures unchanged=true다.
  이52건이 coercion/혼합 인덱스/음수 경계의 모든 HTTP 계약까지 포함하지는 않는다.
- 증거 SHA-256:
  - node lib.rs: `d7cc3855f5064b088a7aba98d6cbaca67b165be3337e0b98cd98c165ad529fe3`.
  - standalone_runtime.rs: `5131491fee071fe569cce572125c0741a0f133216d5854fec9b999fa8676a02d`.
  - integer-sort-node-lib.log(최초 실패):
    `6cdfa665596c4186699d1fdde82053a7529f5ad8af798d02145e3de10b665499`.
  - integer-sort-node-lib-fixed.log:
    `d1f6f15c07bbfcbcea4ea454afde4c175afeaa01b911ddd2a296d3e94e8b7355`.
  - integer-sort-array-live/execution.json:
    `868a9c7a74d65d30705cc880a6e1cfa0d8764ff7b2560c0d8fb4c2dcf375d857`.
- 다음은 음수 half/정수 동점/혼합 매핑/numeric_type/after의 HTTP fixture 확장과
  원문 coercion 경계 확인이다. 런타임 추가 수정은 관련 전체 회귀/live로 확인하고,
  고정 source/별도 release 빌드 및 **전체 non-plugin 반복 suite**를 실행해야 단위
  완료를 판정한다. 최초 v0.6.0 누적 처리량95%/각 시나리오 mean,p95,p99 지연105%,
  paired/drift 및 pinned OpenSearch 비교를 유지한다. 새 성능 측정 없이 채택하지 않는다.
- 최신 기능 서버8056a58a, 최신 전체 성능d162d500 FAIL로 분리한다. 정식 수락0/40,
  C02/C06/daemon 미완료, ledger 제외0, 릴리즈 보류. 이번 빌드/테스트/live 모두 종료했다.

#### C06 정수 모드 확장 경계의 실제 실패 분류 (2026-09-09)

- 직전 turn은 매핑 연결 및 기존52건 HTTP 통과를 확보한 progress다. 현재8056a58a
  실행 파일과 기존 fixture 해시, 실행 중인 소유 프로세스 부재를 재확인했다.
  이번에는 런타임을 바꾸지 않고 별도
  `tools/fixtures/search-integer-sort-boundaries-compat.json`을 추가했다.
- 1/3샤드 각각 long/double/coerce6개 인덱스,30문서다. 음수 half/반올림 동점/
  양수 half/null을 포함한다. coerce 매핑은 long/coerce=true/null_value=7이며
  문자열 배열,소수 배열,명시적 null 및 [null,2]를 포함한다. 각 topology의
  long/double/coerce/long+double 혼합 선택에 avg/median, 일반/fallback 요청,
  asc/desc/page/after/numeric_type=double/long을 조합해192건이다.
  ID/원문/total/sort 값 모두 실제 OpenSearch3.7.0-SNAPSHOT과 비교한다.
  기존52건 fixture는 수정하지 않았다. fixture SHA-256
  `cd067c4d6e2dc4905cfc802fe57f69ebe224481c6c3cdbd98fa95a10ebe71c47`.
- `target/core-replacement-c06/integer-sort-boundary-live` 결과는
  **72성공/120실패/skip0**이며 모든 실패는 양쪽HTTP200 내용 차이다.
  기존 nested160+160/core1180는 모두 성공, 전체1572성공/120실패/skip0,
  최종 종료1, binary/fixtures unchanged=true다. 기능 검사의 실패이며 서버 장애나
  성능 회귀로 분류하지 않는다.

| 선택 | 통과 | 실패 |
| --- | ---: | ---: |
| long | 40 | 8 |
| double | 16 | 32 |
| coerce | 0 | 48 |
| long+double 혼합 | 16 | 32 |

- long의 numeric_type=double 요청은 값 있는 문서의 평균/중앙값이 같지만,
  OpenSearch의 missing sort 값 "Infinity" 대신null을 반환한다. mixed asc 사례는
  ID 순서는 같지만 각 인덱스의 long missing=9223372036854775807,
  double missing="Infinity" 대신null을 반환했다. 이것이 모든120건의 유일한
  원인이라는 뜻은 아니다. 모든 원본 diff를 보고서에 보존했다.
- coerce avg 대표 관측: 문자열[-3,0] 및 소수[-3.9,0.9]는 OpenSearch에서-1,
  [null,2]는 null_value7을 반영해5, 문자열[2,9]는6, 명시적 null은7이다.
  현재는 문자열을missing으로 취급하고 소수평균-1.5, [null,2]의2를 반환한다.
  기존 원문 fallback을 유지한 구현이 mapping-aware coercion을 해결하지 못한다는
  직접 증거이며 이를 지원 제외로 바꾸지 않는다.
- 로컬 OpenSearch LongValuesComparatorSource의 loadDocValues -> sortMode.select ->
  FieldData.replaceMissing 순서를 확인했다. FieldData.castToLong은 별도 docvalue
  변환이다. 따라서 원문 평균의 출력만 반올림하거나 null 문자열만 바꾸는 방식으로
  전체 계산/정렬/search_after 의미가 맞는다고 가정하지 않는다.
- execution.json SHA-256
  `fe0c05d1f8cd84f66d7053acc55aa0345d95bcb83f79cdb19470b921cb2437e7`,
  search-integer-sort-boundaries-compat-report.json SHA-256
  `78a9e2cb9552fa7930ba61383c03a00826e48b318277cf0e61b42e07cd63ca35`.
- 다음 구현은 MappedSearchSort의 인덱스별 numeric descriptor에서 source 매핑 타입,
  coerce/null_value, effective numeric_type을 구분하는 것이다. 원문 보존 상태에서
  유효 indexed 값 변환 -> 모드 선택 -> 타입별 missing 순서를 적용하고,
  order/after/rendering이 같은 resolved 값을 사용하도록 한다. 정수 극값 정밀도와
  Infinity의 숫자 정렬 의미를 보존하며 keyword 문자열과 혼동하지 않는다.
  malformed/coerce=false/ignore_malformed 등 미검증 옵션을 묵시적으로 완료 처리하지 않는다.
  새 기능 회귀와192건/기존 fixture 재검증, 별도 고정 release 빌드 및 **전체 non-plugin
  반복 suite**를 실행하기 전에는 단위 미완료다. 최초 v0.6.0 누적 처리량95% 및
  각 시나리오 mean,p95,p99 지연105%, paired/drift/pinned OpenSearch 기준을 유지한다.
- 최신 기능8056a58a는 기존52건 통과/확장192건 중120실패, 최신 전체 성능d162d500 FAIL.
  정식 수락0/40, C02/C06/daemon 미완료, ledger 제외0, 릴리즈 보류다.
  이번 live 프로세스는 종료했고 이전 증거와 실패를 보존했다.

#### C06 숫자 원문 매핑 변환 및 coercion 48건 해결 (2026-09-09)

- 직전 turn은 확장192건에서120실패를 확보한 progress다. 현재 MappedSearchSort의
  IntegerMode를 NumericMode descriptor로 확장했다. 원래 source 타입과 요청의
  effective numeric_type을 분리하여 avg/median 값을 계산한다. 매핑의 coerce,
  ignore_malformed,null_value를 descriptor에 보존한다. 기본 정렬의 빠른 진입은 유지한다.
- 배열을 재귀 순회하며 명시적 null에만 null_value를 적용한다. 필드 누락/빈 배열은
  값을 추가하지 않는다. 원문 스칼라는 먼저 source 매핑 타입으로 정규화한 뒤 요청
  타입으로 변환하고 모드 계산한다. 정수 문자열은 i64 파싱을 먼저 시도해 정밀도를
  유지하고, coerce 소수는 범위를 검사한 뒤 정수화한다. byte/short/integer 범위와
  유한 숫자를 확인한다. float source는 f32 표현을 거친다. 유효하지 않은 값은
  ignore_malformed일 때만 건너뛰며 그 외는 오류로 반환한다. 원문은 수정하지 않는다.
  malformed와 indexing admission 전체의 동등성은 아직 HTTP 증명하지 않았다.
- 공통 values 결과가 order/after/rendering에 사용된다. double 대상도 이제 numeric
  descriptor를 사용하므로 기존 테스트의 descriptor 없음 기대는 실제 소수 계산값
  기대 검사로 바꿨다. source long의[-3.9,0.9]를 먼저[-3,0]으로 변환한 뒤
  target double 평균-1.5를 얻는 순서, 명시적 null7/누락/빈 배열 차이를 검사한다.
  coerce=false,ignore_malformed,byte 범위 및 i64 MAX 단일 값도 회귀에 추가했다.
- node library 전체 **661성공**, 실패/skip0, 종료0. 빌드53.38초/실행5.87초.
  main/daemon 전체 성공은 아니다. standalone_runtime.rs SHA-256
  `0bd04e97d1b9f5542e6c23a0b106e29524b7125e66d955565cfd7447d31bfc10`.
  mapped-numeric-mode-node-lib.log SHA-256
  `0885c1d3bfa1a432d23fbda9dadd28796a543ff9e3cc70e1fd965c10bf088f35`.
- debug 빌드44.10초 종료0. 보존 서버
  `target/core-replacement-c06/mapped-numeric-mode-debug/steelsearch` SHA-256
  `da8d342429be1ae65b94065e86fcf2cf7fadcf07ff46f5611aa225f073881a7c`.
  동일 fixture들을 그대로 OpenSearch3.7.0-SNAPSHOT과 대조한
  `mapped-numeric-mode-live`는 기존52건 전부 성공, 확장192건 중120성공/72실패,
  기존 핵심1500건 성공이다. 합계1672성공/72실패/skip0, 종료1,
  binary/fixtures unchanged=true. execution.json SHA-256
  `e28d2f69faf1dce1ad8db879a212e5d29dde20cff9e0970d01060a6396aa2f58`.
- coerce 그룹48건 모두 성공으로 바뀌었다. long40/48, double16/48,
  mixed16/48은 그대로다. 남은72건은 이번 fixture에서 ID 순서/원문/total이 같고
  sort 값이 다르다. 이 관측만으로 누락 값의 정렬/search_after 의미 전체가 맞다고
  단정하지 않는다. 이전120실패 보고서는 보존한다.
- 다음은 인덱스별 유효 숫자 타입의 missing을 해결하는 작업이다. long 극값과
  double Infinity를 구분하고, 사용자 지정 missing/first/last와 내부 sentinel을
  혼동하지 않아야 한다. JSON 문자열 Infinity는 keyword 문자열과 같은 전역 비교
  규칙으로 처리하지 않는다. 원래 sort 요청과 내부 보정된 요청의 소유 경계를
  확인하고 order/after/rendering을 함께 검증한다. 경계 fixture 및 관련 전체 회귀,
  확장 live, 별도 고정 release 빌드의 **전체 non-plugin 반복 suite**를 완료하기
  전에는 단위 미완료다. 최초 v0.6.0 누적 처리량95% 및 각 시나리오 mean,p95,p99
  지연105%, paired/drift/pinned OpenSearch 기준은 그대로다.
- 이번 새 release/성능은 미측정, 최신 전체d162d500 FAIL이다. 정식 수락0/40,
  C02/C06/daemon 미완료, ledger 제외0, 릴리즈 보류. 실행 프로세스 모두 종료,
  git diff --check 성공이다.

#### C06 숫자 missing의 공통 비교와 HTTP 308건 통과 (2026-09-09)

- 직전 turn은 coercion48건을 해결한 progress다. 이번에는 MappedSearchSort를
  원래 sort 요청으로 생성하여 내부 전역 정수 missing 보정과 사용자 옵션을 구분했다.
  numeric descriptor는 인덱스별 effective 타입으로 missing을 해석한다.
  다른 열은 기존 mapping-aware 실행 옵션을 유지한다. long은 방향에 따른 i64 극값,
  floating은 Infinity/-Infinity를 사용하며 사용자 지정 missing은 별도로 처리한다.
- descriptor의 values 단계에서 missing을 해석하므로 order/after/rendering이 같은
  값을 사용한다. Infinity 비교는 숫자 모드 열에만 한정하고 전역 compare_json_scalars나
  keyword 문자열 규칙은 바꾸지 않는다. 정수끼리 비교할 때 기존 정밀도를 유지한다.
  테스트에 실제 i64MAX와 long missing의 동점, double Infinity의 상대 순서,
  after 극값/Infinity, asc/desc+first/last 및 keyword 문자열 비교를 추가했다.
- node library 전체 **662성공**, 실패/skip0, 종료0(빌드54.74초, 실행5.86초).
  standalone_runtime.rs SHA-256
  `bf5d358c4b7765313e7f9575060aede068ac4e741b91558b1a57212c88d43ac2`.
  numeric-missing-node-lib.log SHA-256
  `93184054266d23575a9f9bad3e74aa211f55e3c421f81389633b3cbc69ae4d15`.
- `tools/fixtures/search-numeric-missing-after-compat.json`은1/3샤드의 double 단독/
  long+double(numeric_type=double) 검색에서 asc/desc,first/last,일반/fallback,
  전체 결과/Infinity after를 조합한64건이다. fixture SHA-256
  `dc0e8e0e0bb014f1c86443f95fec7b94ec72a521a297e039f2cb6f7bfd6ead90`.
  기존52/192 fixture는 변경하지 않았다.
- debug 빌드52.58초 종료0. 보존 서버
  `target/core-replacement-c06/numeric-missing-debug/steelsearch` SHA-256
  `ab746025dd5b4a3f44815016123997f17b9d8de3faf58b7eed97d327b151dc6f`.
  `numeric-missing-live`의 실제 OpenSearch3.7.0-SNAPSHOT 대조는
  **52+192+64=308건 모두 성공**, 기존 핵심1500건도 성공이다.
  합계1808성공/실패0/skip0, 종료0, binary/fixtures unchanged=true.
  이전72실패가 해결됐고 Infinity를 HTTP search_after에 넣은64건도 통과했다.
  execution.json SHA-256
  `e3e8a9a85b0717f49a99eda3cf4b60e50130f87099aa61ac8cdf7c529d1228fa`.
- 다음 성능 후보를 `target/core-replacement-c06/numeric-sort-candidate/source`에
  고정했다. d162d500 source에서 engine lib, node lib/standalone_runtime 및 새
  integer_sort_mode, fixture3개만 변경했음을 전체 diff로 확인했다. 기존 FST 패치/
  vendor/lock는 유지하며 root FST는 여전히 미패치다. source.sha256 검증 성공,
  manifest SHA-256 `166df88936ee6e4a0c5f292ebf17f71a49b1f8feef8fd3248cd27c1be77dffd7`.
  이 snapshot의 release 빌드는 아직 실행하지 않았다.
- 다음 필수 작업은 별도 target의 고정 release 빌드, 실제 새 실행 파일 전체 확장 live,
  **전체 non-plugin 반복 suite**다. 최초 v0.6.0 고정 누적 처리량95% 및 각 시나리오
  mean,p95,p99 지연105%, paired/drift 및 pinned OpenSearch 기준을 유지한다.
  범위 밖 숫자/스크립트/날짜/비활성 doc_values/전체 indexing admission 계약을
  이번308건으로 모두 증명했다고 주장하지 않는다. 기존 daemon 문제도 미해결이다.
- 최신 기능 서버ab746025는 위1808건 성공이나 최신 전체 성능은 d162d500 FAIL이다.
  새 최적화/기능을 아직 정식 수락하지 않았다.0/40, ledger 제외0, 릴리즈 보류.
  이번 빌드/테스트/live 모두 종료했다.

#### C06 고정 release 2124건 통과와 전체 반복 성능 미통과 (2026-09-09)

- 직전 단계의 고정 source로 별도 RAM target
  `/run/user/1001/steelsearch-numeric-sort-build-20260909`에서 nightly release,
  locked, standalone-runtime 빌드를 실행했다. jobs=2, incremental=0,
  RUSTFLAGS=-Awarnings, 7분38초, 종료0이다. 빌드 전 기존 construction RAM
  target의 유효 CACHEDIR.TAG와 보존 d162d500 실행 파일을 확인하고 cargo clean
  --release로1790파일680.4MiB를 정리했다. 이전 source/artifact/측정 근거는
  보존했다. 로그는 field-cache-construction-candidate/cache-clean.log다.
- 새 보존 실행 파일은
  `target/core-replacement-c06/numeric-sort-candidate/artifacts/steelsearch`,
  SHA-256 `8a31868ec9de791da94e38c48a190eba96a4c058777f02735c128bd9371964c9`.
  RAM 원본과 복사본 해시가 같다. candidate-build.log SHA-256
  `65e9cb01f428c5b5ab9f10a4ae376daa53328b49775e5217dcc4e9b9841a977f`.
  source.sha256는 기존166df889 manifest 그대로이며 빌드 전/후 검증 성공이다.
  기존 FST 패치를 포함한 frozen source이며 root FST는 여전히 미패치다.
- `numeric-sort-live`는 실제 새 release 실행 파일과 OpenSearch3.7.0-SNAPSHOT을
  대조했다. 기존1816건과 새 숫자 정렬308건을 합친 **2124성공/실패0/skip0**,
  19개 subrun 모두 종료0, count probe=true, binary/fixtures unchanged=true다.
  execution.json SHA-256
  `34bbc3bc6a525802c05436c8d1dc3160887966beae7f6c1b3490b86ecaee0e5a`.
  범위 밖 숫자/날짜/스크립트/indexing admission 및 daemon 계약까지 통과했다는
  뜻은 아니다. 과거 실패 보고서는 그대로 보존한다.
- `numeric-sort-repeated-full`에서 사전 고정 전체 non-plugin suite를 실행했다.
  순서는 baseline00,candidate01,OpenSearch02,OpenSearch03,candidate04,baseline05,
  각 single/three-node 60초, 기존5000문서/384 source값/4clients/3shards/seed13
  및 workload/durability/security/resource 설정을 유지했다. 성능 reference는
  기존 pinned OpenSearch2.19 digest로, 위 기능 대조 reference와 구분한다.
  총1095.4999초, 6개 subrun 모두 종료0, 12개 topology 요청 오류0이다.
  execution_inputs_verified=true이나 numeric_budget_passed=false,
  acceptance_established=false, 최종 종료1이다.
- result.json SHA-256
  `1d7c0753869e86ead515a7a93990e1aab767e6af08f5e8f808638ff120bb3a59`,
  plan.json SHA-256
  `42cba694c881253f20b80a14563a65213d2a53338dd9ef2a8e13c8232165683c`.
  최초 v0.6.0 실행 파일db244133 및 published current.json d2fdabfa 해시도
  재확인했다. 원본 evidence와 누적 비교 기준은 변경하지 않았다.

| 후보 반복 | v0.6.0 published 판정 | 초과 지표 | 기준 -> 후보 (ms) | 누적 지연 증가 |
| --- | --- | --- | --- | --- |
| 01 | 43/44 | three-node/ranking/p99 | 11.304207379 -> 11.938902582 | +5.614681% |
| 04 | 43/44 | three-node/facet/p99 | 13.120876516 -> 14.010822857 | +6.782674% |

- paired01은42/44로 single-node/ranking/mean +6.155413%,
  three-node/ranking/p99 +8.773237%가 초과했다. paired04는43/44로
  three-node/facet/p99 +5.805839%가 초과했다. baseline00 drift는44/44,
  baseline05 drift는42/44로 single-node/write/p99 +5.172527%,
  three-node/lexical/p99 +6.125842%가 초과했다. drift 관측을 후보 실패의
  면제 근거로 사용하지 않는다. 모든 시나리오의 원래 값은 result.json에 보존했다.
- 후보01 throughput은 single742.3417233(-0.090086%),
  three925.6853161(-0.610358%); 후보04는 single758.0654411(+2.026130%),
  three925.3640656(-0.644851%)다. 괄호는 최초 v0.6.0 대비 처리량 변화다.
  OpenSearch02는 single278.6856160/three109.9951291,
  OpenSearch03은 single285.0523214/three112.5526513 ops/s다.
- sort_filter의 mean/p95/p99는 두 topology, 두 후보 반복 모두 published 한도
  안이다. three-node p99는01 -8.034635%,04 -2.972970%다. 개선 관측은
  ranking/facet 실패를 상쇄하지 않으며, 직전 후보와 통제된 직접 A/B로 이번
  변경 하나의 인과 효과를 증명한 것은 아니다. 평균/최고 실행 선택/통과까지
  반복 없이 사전 지정한 전체 결과를 미통과로 유지한다.

#### C06 ranking 실행 경로 CPU 진단과 다음 작업 (2026-09-09)

- 전체 suite 종료 후 동일8a31868e 실행 파일로 `numeric-sort-ranking-cpu`를
  실행했다. three-node, ranking=100,45초 부하 중20초 CPU capture,199Hz,
  실제 소유 server3개와 load-generator1개의 PID/실행 파일을 확인했다.
  perf/matrix 모두 종료0, lost samples0, 실행 파일 해시 유지, 요청 오류0이다.
  observation22.7061초의 CPU 시간은 generator17.79초,
  server9.84/9.83/14.84초다. 프로파일링된 처리량1635.9412 ops/s는 진단값이며
  혼합 workload 전체 gate 또는 비프로파일링 서비스 성능으로 인용하지 않는다.
- diagnostic.json SHA-256
  `fb5bd343b44fad6b7a763bc9b78c68cb07672279054d1e8abe2b5903267f3ab8`,
  perf.data SHA-256
  `2ed5d1992cd51302f22bf6be2b30b3e6b19b28a5a9d0d8080385faf1e129ef27`.
  server PID 필터, 전체 capture 분모의 self 비중은 memcmp5.32%,
  source_value_for_highlight_field4.12%, malloc3.23%, Rayon bridge2.41%,
  score_document_query_with_bm25_context1.83%다. CPU 비중은 p99의 기여율이나
  off-CPU 대기 시간, 주파수가 다른 이전 진단 대비 속도 개선이 아니다.
- 실제 stack은 search_single_index_plain_snapshot_response ->
  search_response_index_aware_with_optional_reusable ->
  search_hits_page_for_query_native_scoped -> score_document_query_with_bm25_context
  -> document_matches_query -> source_value_for_highlight_field다. 해당 helper는
  이름과 달리 점수 계산에서도 쓰인다. 이미 top-level direct get 경로가 있으므로
  같은 최적화를 다시 추가하지 않는다. 기존에 기각한 bool should Vec 제거도
  단순 반복하지 않는다. ranking 요청은 multi_match best_fields, phrase/term should,
  minimum_should_match=1, numeric range filter, size10이다.
- 다음은 이 실제 점수 계산 경로에서 반복되는 필드 조회/쿼리 해석의 원인을
  확인하고 facet의 별도 CPU/대기 경로를 진단하는 작업이다. 변경이 필요하면
  배열/null/dotted/multi-field/boost/최소 should/오류 전달/동점 및 페이지 계약을
  유지하는 작은 구현 단위로 제한한다. 각 단위 종료 전 관련 전체 기능 회귀와
  고정 release live, **전체 non-plugin 반복 suite**를 다시 실행해야 한다.
  누적 기준은 최초 v0.6.0 처리량95%, 각 시나리오 mean/p95/p99 지연105% 그대로다.
- 이번에는 build/live/전체 성능/진단 근거를 추가했으며 후속 runtime 코드는 아직
  바꾸지 않았다. 정식 수락0/40, C02/C06/daemon 미완료, ledger 제외0이다.
  단일 기능의 최적화 불가능한5% 이상 인과 저하가 아직 입증되지 않아 임의 제외나
  예외 승인을 하지 않았다. 모든 실행이 종료됐고 릴리즈/태그/게시 작업은 하지 않았다.

#### C06 facet CPU 경로와 검증된 위치 힌트 진단 (2026-09-09)

- 직전 단계는 새 release 전체 live/성능 및 ranking 진단을 확보한 progress다.
  이번 시작 시 실행 프로세스가 없고 후보8a31868e 해시가 유지됨을 확인했다.
  `numeric-sort-facet-cpu`에서 같은 후보의 three-node,facet=100,45초 부하 중
  20초199Hz CPU capture를 실행했다. perf/matrix 종료0, lost samples0,
  실제 소유 server3개+generator1개 확인, 실행 파일 해시 유지다.
  observation22.6522초 CPU 시간은 generator17.82초, servers9.19/9.07/15.15초다.
  diagnostic.json SHA-256
  `02c424a462ff9aaab2acd407e0c124c018692afc4c101ecf84078ad104e97906`,
  perf.data SHA-256
  `104f237673a0b3de8637f69ab24a0e30ab1a09efa55814ea04e7fe2f13ad6477`.
- server PID 필터, 전체 capture 분모의 self 비중은 memcmp7.16%,
  FieldCache<String>::get3.42%, Rayon bridge2.94%, malloc2.93%,
  FieldCache<f64>::get1.79%, 집계 collector1.31%다. memcmp caller는
  collect_aggregations_native -> collect_aggregations_from_documents_with_budget ->
  collect_simple_bucket_aggregations_from_documents_with_budget이고,
  String/i64 FieldCache 조회 경유 샘플도 확인했다. CPU 비중은 HTTP p99 또는
  off-CPU 대기 시간의 기여율이 아니다. 이 진단은 전체 gate를 대체하지 않는다.
- 런타임을 바꾸기 전에 별도 `tools/bench-field-cache-hint.rs` prototype을 만들었다.
  Small 캐시의 이전 조회 위치를 다음 문서에서 재사용하되 매번 정확한 key를
  검증하고 불일치/범위 초과 시 기존 선형 검색으로 돌아간다. Tree는 기존 get이다.
  unsafe/영구 문서 상태/배열 및 null 의미 변경 없이 비용 가설을 시험한다.
  테스트는 stale 위치, 변경된 query key, 빈/누락/Unicode/dotted/NUL 키,
  Small/Tree 전환을 기존 BTreeMap 조회와 비교한다. 기존 캐시5개+새2개,
  **7성공**, 실패/skip0, 종료0이다. final-tests.log SHA-256
  `6db293306214659a6ce622cc4c6adb3ffcd84dc55e7b79d42973edd8839f173f`.
- 첫 합성 진단은0/1/3/8/9/16/64/256필드,5000문서, 고정/필드 누락 배치,
  5개 query,16회 순회, 사전 ABBA 두 블록의128행 전부를 보존했다.
  checksum과 기존 get 비교 모두 성공이다. 3/8필드는 개선됐지만1필드 및
  Tree에서 일관된 개선은 아니다. Tree는 동일 알고리즘이므로 그 시간 차이를
  위치 힌트의 인과 효과로 주장하지 않는다. 첫 진단 binary SHA-256
  `dc921ea816b03ff0bb635d07c646a3447a2d74b26c292ceda3ea1d3bc123173d`,
  field-cache-hint-abba.csv SHA-256
  `7effaf6ffafc79070103035c6bfc31255a91292cf06d8aef092012c4086ea13d`.
- 합성 공통 접두어의 영향을 구분하려고 document_for에서 확인한 실제 문자열
  cache7필드(category,event_time,message,service,status,tenant,title)와 실제
  terms 조회2개(category,service)의 추가 모드를 만들었다. 값은 합성 문자열이며
  문서 전체/서비스 부하를 재현한 것은 아니다. 고정 배치는 current3.0335~3.3500ms,
  hinted2.6098~2.6235ms; 누락 배치는 current2.7415~2.7686ms,
  hinted2.7311~2.7647ms다. 각각 사전 ABBA 두 블록, 전16행/checksum 일치다.
  누락 배치나 날짜/숫자 캐시까지 일반화된 개선을 주장하지 않는다.
  최종 source SHA-256
  `e047a9ee6cea0223ea7291e5f55317067e811451ef6227e09ff2b181f1f8bc55`,
  추가 모드 binary SHA-256
  `89d987b1a6a0f7c5b5d781ee944ebe8708e53f55acfa61a620702747d6aea8e0`,
  field-cache-hint-facet-abba.csv SHA-256
  `e4c941344fdbdcbc05242eb9a62a12aca209c98bcf6dcf04c2b2b42f5b041f90`.
- 다음 구현 후보는 terms 집계의 요청별 검증된 위치 힌트로 범위를 제한한다.
  힌트가 틀리거나 필드가 누락/배열/null이면 기존 조회 및 source fallback 판단을
  유지해야 한다. cache 생성/문서 크기/전역 get/숫자 및 날짜 조회는 근거 없이
  바꾸지 않는다. 실제 집계 결과의 eager 대조, 관련 전체 회귀 및 고정 release live,
  **전체 non-plugin 반복 suite**가 끝나기 전에는 단위 완료가 아니다.
  최초 v0.6.0 누적 처리량95%, 각 시나리오 mean/p95/p99 지연105%를 유지한다.
- 이번에는 진단 도구/근거만 추가했고 runtime 구현과 새 성능 gate는 아직 없다.
  최신 전체8a31868e FAIL, 정식 수락0/40, C02/C06/daemon 미완료,
  제외 ledger0, 릴리즈 보류다. 모든 진단/테스트 프로세스는 종료했다.

#### C06 terms 위치 힌트 구현과 엔진 전체 회귀 통과 (2026-09-09)

- 직전 단계는 실제 facet stack 및 별도 위치 힌트 진단을 확보한 progress다.
  이번에는 FieldCache::get_with_hint를 추가하고 simple bucket collector의
  Terms 상태마다 요청 범위의 usize 힌트를 두었다. Small은 매 문서에서 인덱스
  범위와 정확한 key를 검증한 뒤에만 재사용한다. 실패하면 기존 선형 검색으로
  돌아가며 Tree는 기존 BTreeMap::get이다. 일반 get, cache 생성/크기, Range/
  DateHistogram, source fallback, bucket budget, 원문 및 보안/내구성은 그대로다.
- cache 단위 테스트는 오래된 위치, query key 변경, 빈/누락/NUL/Unicode/dotted
  키, Small/Tree 전환을 BTreeMap과 대조한다. 기존 집계 대조 테스트는80문서에서
  filler0~16개로 필드 위치/캐시 표현을 변화시키고 terms2개와 range/date를 함께
  검증하도록 확장했다. 정/역순 결과를 개별 collector와 비교하며 배열/빈 배열/
  null이 나타나면 기존 simple collector fallback(None)이 유지됨을 확인한다.
- 디스크159MiB 상태에서 root target의 유효 CACHEDIR.TAG와 보존된
  debug ab746025/release8a31868e 해시를 확인한 뒤 cargo clean -p os-node
  --profile dev로21파일1.3GiB를 정리했다. 로그는
  `target/core-replacement-c06/terms-hint-node-cache-clean.log`다.
  node 이전 test executable/cache는 더 이상 존재한다고 가정하지 않는다.
  기존 source/artifact/live/성능 근거와 최초 v0.6.0은 보존했다.
- `RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 cargo +nightly
  test --locked -p os-engine-tantivy` 전체 종료0이다. 빌드1분48초,
  lib894 + concurrent7 + merge4 + multi-field9 = **914성공**, 실패/skip0이다.
  실행시간은14.20/16.49/2.87/0.31초다. doctest0이며 기존 괄호 경고13개는
  별도 수정하지 않았다. root FST는 미패치 상태이므로 combined patched FST
  전체 테스트까지 새로 통과했다는 주장이 아니다.
  terms-hint-engine-full.log SHA-256
  `19f4f149033e21ae8860dba86834f9d5006c3d916d8c04d4c0d66b2a1bbaa1f3`.
- engine lib SHA-256
  `30a07936e1e97682cf82d55632f89c123ae850996d2652fba1572579aa86f24b`,
  field_cache.rs SHA-256
  `cdfb5e8c4c98e484d2f8584824391d2785d353feb3f412c6b79e0083fba62731`.
  `target/core-replacement-c06/terms-hint-candidate/source`를 직전 numeric-sort
  frozen source에서 복제하고 이 두 파일만 바뀐 것을 전체 diff로 확인했다.
  기존 FST patch/vendor/lock/node/fixtures는 그대로다. source.sha256 검증 성공,
  manifest SHA-256
  `833b62fdbdc73ec884e9e7aec8532f100f2480d143bfbf6b90326f80144e7790`.
- 이 후보의 release 빌드/HTTP live/성능은 아직 실행하지 않았다. 다음 필수 작업은
  별도 target의 frozen release 빌드, 실제 실행 파일 해시 확인과 확장2124건 live,
  **전체 non-plugin 반복 suite**다. 통과 전에는 구현 단위를 완료로 표시하지 않는다.
  최초 v0.6.0 누적 처리량95%, 각 시나리오 mean/p95/p99 지연105%, paired/drift,
  pinned OpenSearch와 이전 published release 비교 원칙을 유지한다.
  일반화된 개선이나 ranking 문제 해결을 이번 엔진 검사로 주장하지 않는다.
- 최신 전체8a31868e FAIL, 정식 수락0/40, C02/C06/daemon 미완료, ledger 제외0,
  릴리즈 보류다. 실행 프로세스 모두 종료했고 git diff --check 성공이다.

#### C06 terms 힌트 release와 전체 반복 성능 결과 (2026-09-09)

- 직전 단계는 runtime 구현과 엔진914건 회귀 통과 및 frozen source를 확보한
  progress다. 이번에는 manifest833b62fd를 재검증한 뒤 별도 RAM target
  `/run/user/1001/steelsearch-terms-hint-build-20260909`에서 nightly release,
  locked, standalone-runtime, jobs2, incremental0, RUSTFLAGS=-Awarnings로
  빌드했다.7분41초 종료0이다. 기존 numeric-sort RAM target의 유효 tag와
  보존8a31868e를 확인한 후 cargo clean --release로1790파일680.6MiB를
  정리했다. 이전 source/artifact/실패 보고서는 보존했다. 정리 로그는
  numeric-sort-candidate/cache-clean.log다.
- 새 보존 실행 파일은 `target/core-replacement-c06/terms-hint-candidate/artifacts/steelsearch`,
  SHA-256 `af048d738efbe98ee0acd1cdddd3797504e7a957594be968b0ed5cd3fa1ea040`.
  RAM 원본과 보존본 해시가 같고 source manifest도 빌드/측정 후 검증 성공이다.
  candidate-build.log SHA-256
  `368cad4f67f00ccab6160b52332d77292104515c207ba2cda223dce36a42c344`.
- `terms-hint-live`에서 실제 af048d73과 OpenSearch3.7.0-SNAPSHOT 대조
  **2124성공/실패0/skip0**,19개 subrun 모두 종료0, count probe=true,
  binary/fixtures unchanged=true다. execution.json SHA-256
  `5a4788b388f98cba6de1c3afca2f68fee60fa2cafa4f6639659dc229a4c0be16`.
  기존 범위 밖 기능과 daemon 문제까지 검증됐다는 주장은 아니다.
- `terms-hint-repeated-full`에서 전체 non-plugin suite를 사전 순서
  baseline00,candidate01,OpenSearch02,OpenSearch03,candidate04,baseline05로
  실행했다. 각 single/three-node60초, 기존5000문서/384 source값/4clients/
  3shards/replicas0 또는1/seed13/mixed workload와 durability/security/resource
  설정을 유지했고 성능 reference는 기존 pinned OpenSearch2.19 digest다.
  총1096.7703초,6개 subrun 모두 종료0,12개 topology 요청 오류0이다.
  execution_inputs_verified=true, numeric_budget_passed=false,
  acceptance_established=false, 최종 종료1이다. 실행 중 빌드/코드 변경은 없었다.
  result.json SHA-256
  `4bc4c1028c398e2f04ee98d79886f94db2dc72c2eb665b614fbc5f3ebc7a134c`,
  plan.json SHA-256
  `c8558ff9c90640b71387be960bbf5580453ab44754cec47e4c160201f2108d30`.

| 후보 반복 | v0.6.0 published 판정 | 초과 지표 | 기준 -> 후보 (ms) | 누적 지연 증가 |
| --- | --- | --- | --- | --- |
| 01 | 43/44 | three-node/ranking/p99 | 11.304207379 -> 12.041102021 | +6.518764% |
| 04 | 43/44 | single-node/write/p99 | 6.831401074 -> 7.205426821 | +5.475096% |

- paired01은42/44로 three-node/nested/p99 +8.660590%,
  three-node/refresh/p99 +5.103560%가 초과했다. paired04는44/44다.
  baseline00 drift는43/44(single-node/write/p95 +5.263355%),
  baseline05 drift는42/44(three-node/lexical/p99 +6.619496%,
  three-node/facet/p99 +6.776766%)다. drift를 후보 실패의 면제 근거로
  사용하지 않고, 모든 원래 시나리오와 수치를 result.json에 보존한다.
- 후보01 throughput은 single764.3669107(+2.874229%),
  three928.3674827(-0.322378%); 후보04는 single763.3177368(+2.733024%),
  three940.4107388(+0.970691%)다. 괄호는 최초 v0.6.0 대비 처리량 변화다.
  OpenSearch02는 single294.1479673/three114.5451484,
  OpenSearch03은 single292.3130509/three114.5784633 ops/s다.
- facet의 mean/p95/p99는 두 topology와 두 후보 반복 모두 published 한도 안이다.
  three-node p99는01 12.9610204ms(-1.218334%),04 13.3525559ms(+1.765731%),
  single-node p99는01 -8.233073%,04 -11.215418%다. 이 관측은 남은 실패를
  상쇄하지 않는다. 직전8a31868e와 통제된 직접 A/B가 아니므로 변경 하나의
  인과 개선을 확정하지 않는다. 좋은 반복 선택/평균/통과까지 재실행은 하지 않았다.
- 최초 v0.6.0 실행 파일db244133과 published current.json d2fdabfa 해시를
  재확인했다. 다음은 기존 ranking profile에서 확인한 실제 점수 계산 경로의
  반복 조회/해석 및 write 경로를 분리 조사하는 작업이다. 이 결과만으로 terms
  기능 하나가5% 이상 저하를 유발했고 최적화 불가능하다고 결론내리지 않는다.
  후속 구현 단위마다 전체 기능 회귀/live 및 **전체 non-plugin 반복 suite**를
  실행하고 최초 v0.6.0 누적 처리량95%/각 mean,p95,p99 지연105%를 유지한다.
- 최신 전체af048d73 FAIL, 정식 수락0/40, C02/C06/daemon 미완료,
  ledger 제외0, 릴리즈 보류다. 모든 실행이 종료됐고 태그/게시 작업은 하지 않았다.

#### C06 write CPU 진단과 ranking 정확성 신규 실패 (2026-09-09)

- 직전 단계는 af048d73의 전체 성능 미통과 근거를 확보한 progress다.
  후보 해시와 실행 프로세스 부재를 재확인하고 `terms-hint-write-cpu`를 실행했다.
  single-node,write=100,45초 부하 중20초199Hz CPU capture, perf/matrix 종료0,
  lost samples0, 요청 오류0, 실제 소유 프로세스/실행 파일 해시 유지다.
  observation21.4687초에서 generator CPU24.69초,server6.71초다.
  server PID 필터/전체 capture 분모 self는 eventfd_write0.99%,malloc0.70%,
  JSON number parse0.64%,Value deserialize0.64%다. 이 샘플로 혼합 부하의
  write p99 원인 또는 off-CPU 대기를 확정하지 않는다. profiled1204.3487ops/s는
  진단값이며 전체 성능 gate의 대체 근거가 아니다.
  diagnostic.json SHA-256
  `65ca8093cd84ad359a355da670dcc8bbd479a69794ffb84feb7e3443ad6424f7`,
  perf.data SHA-256
  `53eed20705dac7b2d3580ba85be8bcf9aa8ff471aac2051e805a1a5dd8e987c5`.
- 기존 ranking stack과 코드에서 multi_match의 base-field 처리와 bool 후처리
  점수 경로를 확인했다. 추정으로 최적화하기 전에
  `tools/fixtures/search-multi-match-bool-scores-compat.json`을 추가했다.
  single shard3문서, title 빈도/길이를 다르게 하고 title^2+message best_fields를
  단독/bool must/phrase should+keyword should+range filter+minimum_should_match1/
  ignore_unavailable=false 요청으로 비교한다. 기존 search_scores extractor는
  total/ID 순서/소수6자리 점수를 비교하며 새로운 완화 규칙은 추가하지 않았다.
  fixture SHA-256
  `80d5d137e3ac36a15264ec7d68a379310db68b54497647d4f42691a73f12f304`.
- 실제 af048d73와 OpenSearch3.7.0-SNAPSHOT의 `terms-hint-ranking-score-live`는
  신규4건 모두 실패, 기존 핵심1500건 성공, skip0, 최종 종료1이다.
  binary/fixtures unchanged=true, count probe=true다. execution.json SHA-256
  `cbb3ddb726274b40b203a6c816f89b28fd825c0810c3f52061bae5fe52fed11d`,
  신규 report SHA-256
  `e049ee888e4f6680fed58eab8986439097b5c7137c00925c3f1f921d48fe9acc`.

| 사례 | OpenSearch | 후보 af048d73 |
| --- | --- | --- |
| 단독 boosted best_fields | z,m,a; 0.194936/0.145143/0.100778 | 같은 ID 순서; 0.097468/0.072571/0.050389 |
| bool must best_fields | z,m,a; 0.194936/0.145143/0.100778 | 같은 ID 순서; 0.214430/0.159657/0.110856 |
| minimum_should_match 후처리 | total3; z,m,a; 1.194936/1.145143/1.100778 | total0; 결과 없음 |
| ignore_unavailable=false | total3; z,m,a; 1.194936/1.145143/1.100778 | total3; a,m,z; 모두2.0 |

- 반올림 차이만이 아니라 누락된 hit와 순위 오류가 확인됐다. 기존2124건 통과는
  이4건을 포함하지 않았으므로 ranking 전체 정확성 증거로 일반화할 수 없다.
  이번4건은 삭제/skip/expected 수정하지 않고 후속 전체 확장 live에 포함한다.
  기존2124+신규4=2128건이 다음 최소 확장 범위다. 이전1500건 재실행은
  전체2128건 검증을 대체하지 않는다. 이전 후보 대비 원인 도입 시점은 미확정이다.
- 다음 우선 구현 단위는 ranking 정확성 수정이다. field boost의 파싱/기본 필드명,
  native/source/bool/fallback 점수 의미와 BM25 정규화 차이를 분리 확인하고,
  단독/중첩 bool, boost/tie_breaker, phrase/term should, minimum_should_match,
  필터의 비점수 의미, 빈 결과/동점/페이지/샤드/배열/multi-field 계약을 검증한다.
  그 과정에서 반복 해석/조회 비용을 줄이더라도 기존의 잘못된 순위나 빠진 hit를
  보존하는 최적화로 목표를 대체하지 않는다. 관련 전체 엔진/node 회귀, 고정
  release의 확장 live 및 **전체 non-plugin 반복 suite** 전에는 단위 미완료다.
  최초 v0.6.0 누적 처리량95%, 각 mean/p95/p99 지연105% 기준은 유지한다.
- 이번에는 진단과 실패 fixture/근거만 추가했고 runtime 수정은 아직 없다.
  최신 전체af048d73 FAIL, 신규 기능4실패, 정식 수락0/40, ledger 제외0,
  C02/C06/daemon 미완료, 릴리즈 보류다. 모든 실행은 종료했다.

#### C06 multi_match 필드 boost와 후처리 결과 누락 수정 (2026-09-09)

- 직전 단계는 실제 ranking4실패를 확보한 progress다. 기존 base-field helper는
  유효한 ^boost를 제거하면서 값을 버렸고, 원문 multi_match 매칭은 반대로
  title^2 전체를 필드명으로 찾았다. multi_match_field_and_boost로 기존 유효
  suffix 판별을 공유하고 native field query와 원문 BM25 field score에 boost를
  적용했다. 원문 matches_multi_match_query/matched_value_count는 base field를
  사용한다. 잘못된 suffix의 기존 literal-field 해석은 유지하며, 전반적인
  boost 입력 validation/모든 query 유형 호환성까지 해결했다고 주장하지 않는다.
- score_document_query_with_bm25_context의 MultiMatch를 기존 Match 계열의
  BM25 경로에 연결했다. 지원되는 계산은 field boost를 적용한 점수를 사용하고,
  기존 fallback 및 query-level boost 적용 패턴을 공유한다. bool 전체의 native
  정규화 및 별도 fallback 점수 경로는 이 연결만으로 해결되지 않는다.
- 새 multi_match_field_tests.rs는 suffix 규칙, scalar/array/null/누락/dotted/_id
  원문 매칭, best_fields/most_fields/phrase/phrase_prefix의 native 및 원문 field
  boost 배율과 후처리 점수 일치를 검사한다. 원문 매칭에는 bool_prefix도 포함한다.
  첫 field 수정 전체917건 성공(빌드1분43초), 후처리 연결 후 전체도
  **897+7+4+9=917성공**, 실패/skip0, 종료0(빌드1분41초,
  실행14.08/16.33/3.08/0.32초)이다. root FST는 미패치이며 doctest0,
  기존 괄호 경고13개는 그대로다. source-score-engine-full.log SHA-256
  `b0006b2691f59d10930b584b1d4fa8db5b78c96b45ec87a81127adbc20f0b48e`.
- 최종 engine lib SHA-256
  `bd3d492cad55cf6d56ca369cc1662ca8fdfb47bedcf8329c87122fb19a4c6187`,
  새 tests SHA-256
  `c65c71fb5b60c572189d0e8dd639d9edfb32c604e8b060b4341f25e7c2a4f19c`.
  디스크 사용을 줄이기 위해 dev package.os-node.debug=0만 지정해 diagnostic
  server를 빌드했다.51.88초 종료0이며 보존 실행 파일은
  `target/core-replacement-c06/multi-match-source-debug/steelsearch`, SHA-256
  `947dbbeb32f54cfea1e213ba93f432af3eec5ca975b6bb61386cf18240bfa12c`.
  이것은 성능 비교용 release가 아니고 root FST도 여전히 미패치다.
- 실제 새 binary와 OpenSearch3.7.0-SNAPSHOT의 `multi-match-source-live`는
  기존2124건 전부 성공, 신규4건 중2성공/2실패다. 합계**2126성공/2실패/skip0**,
  count probe=true, binary/fixtures unchanged=true, 종료1이다.
  execution.json SHA-256
  `4c1b0e0a942c4f73332383fd878aae74b36ccd65af6dd6dade54243ed73da79e`.
- 해결된 사례는 standalone boosted best_fields와 minimum_should_match 후처리다.
  후자는 기존 total0에서 OpenSearch와 동일한 total3, z/m/a 순서,
  1.194936/1.145143/1.100778 점수로 바뀌었다. 남은 native bool must는 ID/total은
  같지만 후보0.428860/0.319314/0.221713 대 reference0.194936/0.145143/0.100778이다.
  ignore_unavailable=false는 여전히 a/m/z 순서와 모두2.0으로 다르다.
  실패 fixture/기대값은 바꾸지 않았고 과거4실패 근거도 보존했다.
- 다음 필수 수정은 native bool의 점수 정규화와 fallback의 mapping-aware 점수
  일치다. 단순 상수 배율이나 최종 top-k 재정렬만으로 대응하면 혼합 clause와
  후보 window 밖의 순위가 틀릴 수 있으므로 관련 query 구성과 수집 범위를 함께
  확인해야 한다. 결과 누락을 유지하는 빠른 구현으로 되돌리지 않는다.
  관련 전체 엔진/node 회귀, 고정 release 확장 live 최소2128건,
  **전체 non-plugin 반복 suite** 완료 전에는 이 ranking 단위는 미완료다.
  최초 v0.6.0 누적 처리량95%/각 시나리오 mean,p95,p99 지연105%는 그대로다.
- 새 release/성능은 미측정, 최신 전체af048d73 FAIL이다. 정식 수락0/40,
  C02/C06/daemon 미완료, ledger 제외0, 릴리즈 보류. 모든 실행이 종료됐다.

#### C06 native bool multi_match의 페이지 이전 점수 계산 (2026-09-09)

- 직전 단계는 field boost/후처리 연결과 HTTP 신규2건 해결을 확보한 progress다.
  이번에는 남은 경로를 확인했다. REST fallback은 handle_index_search_route의
  candidate_documents 순회에서 evaluate_search_query_source_checked를 쓰며,
  엔진의 score_document_query_with_bm25_context 연결만으로는 바뀌지 않는다.
  ignore_unavailable 플래그를 제거해 native로 우회하는 식으로 fallback 문제를
  해결했다고 처리하지 않는다. PIT/routing/alias/runtime fields/가시성 경계를
  유지하는 mapping-aware 점수 문맥이 별도로 필요하다.
- native bool의 raw Tantivy 점수를 최종 top-k에서만 바꾸면 mixed clause의
  상대 가중치와 window 밖 순위가 틀릴 수 있다. bool must/should에 원문 BM25
  지원 형태의 MultiMatch가 있으면 기존 candidate post-filter 경로를 사용하도록
  했다. 후보를 점수 계산한 뒤 정렬/페이지 선택한다. predicate는
  best_fields/most_fields/phrase/phrase_prefix, analyzer/fuzziness/minimum 없음,
  operator 미지정 또는 or인 구문을 식별한다. 모든 mapping/다른 MultiMatch 모드의
  정확성을 이 predicate만으로 증명했다는 뜻은 아니다. filter/must_not만의
  비점수 절에는 이 추가 조건을 적용하지 않는다.
- multi_match_field_tests의 새 회귀는1/3샤드,40문서, 서로 다른 제목 빈도/길이,
  title^8와 keyword should, 일반/중첩 bool을 사용한다. 전체 원문 점수의 eager
  순서와 실제 native 페이지를 from/size=(0,1),(1,3),(7,10),(40,5),(0,0)에서
  비교하며 total/ID/점수까지 검사한다. 이는 현재 source scorer와의 일치 검사이며
  모든 shard별 OpenSearch BM25 의미를 독립 증명하는 검사는 아니다.
- 첫 전체 테스트 컴파일은 ENOSPC로 종료101, 테스트 실행 전 인프라 실패다.
  실패 로그 SHA-256 `d2ffd2ea574168c048813c66a7abfcdff328c9992888d5a4132aae524244d75f`.
  root target의 유효 CACHEDIR.TAG와 보존947dbbeb 서버 해시를 확인하고
  cargo clean -p os-node --profile dev로15파일677.8MiB를 정리했다.
  node cache/test executable이 남아 있다고 가정하지 않는다. 기존 artifact와
  실패 보고서는 유지했으며 multi-match-bool-page-node-cache-clean.log에 기록했다.
- 동일 전체 명령 재실행은 빌드1분43초, **898+7+4+9=918성공**, 실패/skip0,
  종료0이다. 실행14.07/15.05/2.94/0.36초, doctest0, 기존 괄호 경고13개다.
  root FST는 미패치이며 combined FST 전체 테스트를 새로 통과했다는 뜻은 아니다.
  multi-match-bool-page-engine-full-recovered.log SHA-256
  `b899d3657d00014c2efa4772e59a68876bf9340b040ef31a6f4212b2367285b0`.
- engine lib SHA-256
  `03c4c75cee02e670dc0e1b1b08b198efeaaad35c67baccf3972a6b58fe812ae0`,
  multi_match_field_tests.rs SHA-256
  `b2b92452ad8f7f6cca4f9896d23c94e18b1d2673213ef7f993d0cfdfc9e14409`.
- 이번 native bool 변경의 새 서버/HTTP/성능은 아직 미검증이다. 최신 실제 HTTP는
  이전947dbbeb의2126성공/2실패 그대로다. 다음은 이 변경의 HTTP 확인과 REST
  fallback 점수 문맥 수정이다. corpus 통계와 snapshot/routing/alias 범위를
  보존하고, 마지막 결과 배열만 임의 정규화하는 방식으로 대체하지 않는다.
  관련 전체 engine/node 회귀, 고정 release 확장 live 최소2128건,
  **전체 non-plugin 반복 suite** 완료 전에는 ranking 단위 미완료다.
  최초 v0.6.0 누적 처리량95% 및 각 mean/p95/p99 지연105% 한도는 유지한다.
- 최신 전체af048d73 FAIL, 정식 수락0/40, C02/C06/daemon 미완료, ledger 제외0,
  릴리즈 보류다. 모든 실행이 종료됐으며 별도 release/tag/publish는 하지 않았다.

#### C06 native bool 점수 HTTP 확인과 fallback 문맥 경계 (2026-09-09)

- 직전 단계는 native bool 페이지 이전 점수 계산과 엔진918건 성공을 확보한
  progress다. engine lib03c4c75c를 재확인하고 dev package.os-node.debug=0,
  RUSTFLAGS=-Awarnings,jobs2,incremental0,locked,standalone-runtime으로
  diagnostic server를 빌드했다.54.77초 종료0이다. build log SHA-256
  `bac27621d3b14a5a595048588651e624739f11c30a22f3552dbbcde771d5828f`.
- 보존 서버는 `target/core-replacement-c06/multi-match-bool-page-debug/steelsearch`,
  SHA-256 `dcc600a9e249fba92fc3c6e11edae0a0dd8edc84eb5392765926bd1d0a093473`.
  디스크 여유191MiB 상태여서 복사 대신 Cargo top-level 실행 파일을 이동하고
  node dev cache14파일372.6MiB를 cargo clean으로 정리했다. 보존본의 이동 전/
  정리 후 해시가 같음을 확인했다. 로그는 multi-match-bool-page-debug-cache-clean.log다.
  이전 보존 binary와 원본 v0.6.0/실패 evidence는 유지했다. 이 서버는 root FST
  미패치 debug 빌드이며 성능 비교용 release로 사용하지 않는다.
- 실제 dcc600a9와 OpenSearch3.7.0-SNAPSHOT의 `multi-match-bool-page-live`는
  신규4건 중**3성공/1실패**, 기존 핵심1500건 성공, skip0, 최종 종료1이다.
  합계1503성공/1실패이며 count probe=true, binary/fixtures unchanged=true다.
  execution.json SHA-256
  `d8d233d81fcf9ed83566572034af017a574bbf6b57d9493c57cd9c72121468b2`.
  이번 범위는1504건으로 전체 확장2128건 재검증을 대체하지 않는다.
- standalone field boost와 minimum_should_match 후처리는 계속 통과했고,
  native bool must도 OpenSearch의 z/m/a 및0.194936/0.145143/0.100778 점수와
  일치했다. 남은 ignore_unavailable=false 경로는 여전히 a/m/z,모두2.0이며,
  reference는 z/m/a,1.194936/1.145143/1.100778이다. 원래4실패 중3건은
  실제 HTTP에서 해결됐지만 전반적인 ranking 호환성 완료는 아니다.
- fallback의 SourceQueryEvaluator는 mappings와 오류 상태를 갖고 재귀 평가를
  공유한다. 현재 evaluate_search_query_source_checked는 매 문서 평가기를
  새로 만들며 corpus 텍스트 통계가 없다. candidate_documents 생성 시 이미
  PIT/refresh 가시성/라우팅/실패 index 처리가 적용되고, alias/slice는 후속
  순회에서 처리된다. pending delete도 가시성을 유지하려고 별도로 포함한다.
  최신 native engine 점수 맵을 나중에 덮어쓰면 이 snapshot과 일치하지 않을 수 있다.
- 다음 구현은 기존 재귀 평가기에 요청별 immutable 텍스트 점수 문맥을 연결하는
  방향으로 검토한다. query의 텍스트 필드/boost를 준비하고 같은 가시성 snapshot의
  mapping 및 적절한 shard corpus 통계를 사용해야 한다. alias/slice/최종 hits만으로
  통계를 만들거나 서로 다른 시점의 engine snapshot을 결합하지 않는다.
  기존 BM25 계산을 공유할 경계를 확인하여 별도 수식/정규화 구현의 분기를 줄인다.
  매 hit 전체 corpus 스캔, 마지막 top-k에 상수 배율 적용, ignore_unavailable
  guard 제거만으로 fallback 오류를 숨기는 방식은 사용하지 않는다.
- mapping/analyzer/arrays/boost/tie_breaker/bool 비점수 절/오류 전달과
  PIT/refresh/routing/alias 통계 범위의 회귀가 필요하다. 관련 전체 engine/node
  테스트, 실제 고정 release의 확장 live 최소2128건 및 **전체 non-plugin 반복
  suite** 전에는 ranking 단위 미완료다. 최초 v0.6.0 누적 처리량95%, 각 시나리오
  mean/p95/p99 지연105% 및 반복/paired/drift 기준은 그대로다.
- 이번에는 build/live 근거를 추가했고 후속 runtime 수정은 아직 없다.
  최신 전체af048d73 FAIL, 정식 수락0/40, C02/C06/daemon 미완료, ledger 제외0,
  릴리즈 보류다. 모든 실행은 종료했다.

#### C06 fallback 연결을 위한 공통 BM25 계산과 통계 준비 (2026-09-09)

- 직전 단계는 native bool의 실제 HTTP 점수 일치를 확보한 progress다.
  이번에는 기존 엔진의 BM25 TF/IDF 산술을 os-core::bm25로 옮기고 엔진이 같은
  함수를 호출하도록 했다. f32 연산 순서와 IDF의 f32 count 변환 후 f64 로그를
  유지한다. 분석기/문서 선택/기존 점수 정규화 의미를 새로 정의하지 않는다.
- FieldStatistics는 호출자가 선택하고 토큰화한 문서들로 필드별 문서 수,
  평균 길이, term document frequency를 한 번 준비한다. 빈 필드는 문서 수와
  평균에서 제외하고 문서 내 중복 토큰은 document frequency에 한 번만 기여한다.
  이후 query/document tokens로 점수를 계산한다. 입력 snapshot/analyzer/shard
  선택은 호출부 책임이며 이 타입 자체가 해당 범위의 정확성을 증명하지 않는다.
  아직 REST fallback에 연결하지 않았고 최신 HTTP 남은1실패는 그대로다.
- 테스트는 기존 엔진 산술과 비트 단위 비교(큰 document count 포함),
  빈 필드/문서 내 반복/쿼리 반복 토큰/빈 corpus/없는 term을 확인한다.
  FieldStatistics 도입만으로 사용자 지정 분석기/phrase 위치/norm 압축 등
  전체 OpenSearch 점수 계약이 검증됐다고 주장하지 않는다.
- 첫 core+engine 전체 빌드는 엔진 test 바이너리 생성 중 ENOSPC로 종료101했다.
  테스트 실패가 아니라 컴파일 인프라 실패이며 원래 log를 보존한다.
  유효 root CACHEDIR.TAG와 v0.6.0 db244133 및 보존 dcc600a9 해시 확인 후
  cargo clean -p os-engine-tantivy --profile dev로134파일2.1GiB를 정리했다.
  source/artifacts/기존 테스트와 성능 보고서는 유지했다. 정리 로그는
  shared-bm25-engine-cache-clean.log다. 이전 engine test executable 존재를
  가정하지 않는다.
- 같은 `RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 cargo
  +nightly test --locked -p os-core -p os-engine-tantivy` 재실행은 빌드1분48초,
  core16 + engine(898+7+4+9)=918, **합계934성공**, 실패/skip0, 종료0이다.
  engine 실행14.76/15.24/3.03/0.31초, doctest0이며 기존 괄호 경고13개다.
  root FST는 미패치다. shared-bm25-core-engine-full-recovered.log SHA-256
  `4629acba669758bdd16a8816acfdd9b8740ff6a36b0ec3a919776677a328ea8c`.
- bm25.rs SHA-256
  `e971f2471d1684b97702c7f613ef5f77e3339adbd7030cb01d53a140f4f91ba0`,
  core lib SHA-256
  `ec4e5e57d772d1d2119669b5303a076ae8b905db5781eae46ece0ee4b5744489`,
  engine lib SHA-256
  `6f93d8e28f3cf3408ab6abc4dc4870bb23ccba4a0aaa3dafe7487f6a152e45e5`.
- 다음은 SourceQueryEvaluator에 요청별 점수 문맥을 전달하는 연결 작업이다.
  candidate snapshot과 같은 가시성의 적절한 shard corpus로 통계를 준비하고
  alias/slice/최종 hit 필터 이후의 일부 문서만으로 통계를 만들지 않는다.
  기존 재귀 bool/mapping 변환/오류 전달을 유지하고 per-hit corpus 재스캔을
  피해야 한다. 관련 전체 core/engine/node 회귀, 고정 release 확장 live 최소
  2128건과 **전체 non-plugin 반복 suite** 전에는 ranking 단위 미완료다.
  최초 v0.6.0 누적 처리량95% 및 각 mean/p95/p99 지연105% 기준은 유지한다.
- 새 서버/HTTP/release/성능은 미측정이다. 최신 실제 HTTP는 dcc600a9의
  핵심1500+신규4 중1503성공/1실패, 최신 전체 성능af048d73 FAIL이다.
  정식 수락0/40, C02/C06/daemon 미완료, ledger 제외0, 릴리즈 보류.
  모든 실행이 종료됐으며 release/tag/publish는 하지 않았다.

#### C05/C06 REST fallback BM25 연결 및 실제 HTTP 2136건 통과 (2026-09-09)

- `os-node/src/source_bm25.rs`를 추가해 기존 fallback의 candidate_documents
  snapshot으로 요청별 `(index, shard, field)` 통계를 준비했다. alias/slice 및
  최종 hits 필터 이전에 준비하고 같은 요청의 재귀 평가기에 전달한다.
  최신 native snapshot을 뒤늦게 결합하거나 매 hit 전체 corpus를 재스캔하지 않는다.
  필드 boost, best_fields tie_breaker, most_fields 합산을 공통 BM25로 계산한다.
- engine의 기존 Unicode alphanumeric/lowercase source tokenizer를 os-core로
  옮겨 공유한다. node는 기존 워크스페이스 os-query-dsl 파서를 직접 사용한다.
  첫 컴파일은 직접 의존성 누락으로101했고 Cargo.toml/lock에 의존성을 추가했다.
  `source-bm25-node-focused.log`에 실패를 보존했다.
- 재실행 focused2건 중1건은 기존 bool filter-only 점수가1이어서 실패했다.
  `source-bm25-node-focused-recovered.log`는 이 실패 기록이다. 기대값을 바꾸지
  않고 filter-only 점수를0으로 수정하고 bool 합산의 최소1점 clamp도 제거했다.
  점수 절의 bool boost를 반영한다. 순수 negative/empty bool 의미를 이 변경으로
  모두 검증했다고 주장하지 않는다. checked evaluator의 오류 저장 경로는 유지한다.
- 새 scorer는 기본 text mapping의 match 및 best_fields/most_fields 기본 옵션에
  한정한다. custom analysis 설정, 명시적 field analyzer/similarity/norm/index
  옵션, nested text, request derived, DFS 경로는 기존 평가기로 남겨둔다.
  이는 해당 기능의 완료/성능상 제외가 아니며 미완료 범위를 축소하지 않는다.
  query analyzer/fuzziness/minimum_should_match 등 새 scorer가 처리하지 않는
  옵션도 기존 평가기로 전달한다. Lucene norm 압축/분석기 전체 등가성 증거는 아니다.
- node 라이브러리 전체는664성공, 실패/skip0, 빌드47.64초/실행6.44초, 종료0.
  `RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 cargo +nightly
  test --locked --config profile.dev.package.os-node.debug=0 -p os-node --lib`.
  `target/core-replacement-c06/source-bm25-node-lib-full.log` SHA-256
  `f463830604c08b7058cb78578b572314803b61b2ae3b52acddd3a885b7d90f70`.
  같은 설정의 `--features standalone-runtime --bin steelsearch` 테스트459성공,
  실패/skip0, 빌드41.03초/실행11.85초, 종료0. 합계1123성공이며 daemon 제외다.
  `source-bm25-node-bin-full.log` SHA-256
  `136d509ad77708938e003e76c5f6360e3465c2cdebed56850a950af401d2c081`.
- 디스크 부족 예방을 위해 유효 Cargo tag와 보존 baseline/server 해시를 확인한
  뒤 `cargo clean -p os-engine-tantivy --profile dev`로54파일1.5GiB를 정리했다.
  새 debug build는 같은 RUSTFLAGS/jobs/incremental/node debug 설정,
  `build --locked -p os-node --features standalone-runtime --bin steelsearch`,
  50.32초/종료0이다. 빌드 로그 `source-bm25-debug-build.log` SHA-256
  `fc6c2259d01a6d0a9faa77b77455e462a618c70ad69d0f6f89af48e391a495b2`.
  root FST는 미패치이며 FST 패치가 포함된 별도 release 검증을 대신하지 않는다.
- 새 실행 파일을 복사 대신 `target/core-replacement-c06/source-bm25-debug/steelsearch`
  로 이동해 보존했다. SHA-256
  `d72aa81ff138e9d17b1d75097243d195aff45064e887fe4385c9790a34893c8f`.
  이후 node dev 캐시36파일1.0GiB를 정리했고 보존 서버와 최초 v0.6.0
  `db244133` 해시가 그대로임을 확인했다. cache-clean 로그2개, 원본 성능 보고서,
  과거 실행 파일은 보존한다. 이전 Cargo test executable 존재는 가정하지 않는다.
- 실제 HTTP 실행은 기존 run-live.py의 core1500 및 추가fixture628건에 신규
  `tools/fixtures/search-fallback-bm25-scores-compat.json`8건을 더했다.
  신규8건은 subunit bool 점수/filter-only/boost0.5/field boost0/most_fields/
  tie_breaker/from-size/alias 통계 범위를 검증한다. 원래4건 fixture는 바꾸지 않았다.
  신규 fixture SHA-256
  `c00fda7ad27c3937d9185634ac3c46883f0db7de0c28e6fff68c56db42850a7e`.
- `target/core-replacement-c06/source-bm25-expanded-live/execution.json`:
  **21 subrun, 2136성공, 실패/skip0, 종료0**, count probe=true,
  binary/fixtures unchanged=true. 기능 참조는 실제 **3.7.0-SNAPSHOT**이며
  성능 참조 pinned2.19와 구분한다. 기록 SHA-256
  `216de1f6a8d1e5cad11fe94c2915424e04a7faccfd30c6fb472e49cc768c0329`.
- source_bm25.rs SHA-256
  `a06565624115920d42d713b88ecb4807e9c26cc989376e4c14ea256ce5cd850e`,
  core bm25.rs SHA-256
  `dadc090f8a7d0a988beebb2cca16097bf093e9d34d798844212b0811df3e07ca`,
  standalone runtime SHA-256
  `ed9fcb4ee35a7a47caa1f336b8f1ac8e18ff50a80b95187585112e74f73f5025`.
- 남은 검증: PIT/refresh/pending-delete/routing/실패 index의 통계 snapshot,
  사용자 지정 분석기·norm·긴 문서·nested·DFS, malformed 옵션 오류, 매 hit
  query parse와 shard 조회 및 corpus 토큰 보관 비용을 확인해야 한다.
  다음 release 후보는 현재 ranking 코드와 FST 패치를 별도 source/build로
  고정하고 확장 live 및 **전체 non-plugin 반복 benchmark suite**를 실행한다.
  최초 v0.6.0 누적 throughput95% 이상 및 각 scenario mean/p95/p99 105% 이하,
  반복/paired/drift 기준 모두 통과 전에는 이 구현 단위를 완료로 세지 않는다.
- 최신 전체 성능은 여전히 이전 `af048d73` FAIL이다. 이번 debug HTTP 성공은
  성능 통과/새 release 준비 완료를 뜻하지 않는다. 정식 수락0/40,
  C02/C05/C06/daemon 미완료, ledger 제외0, release/tag/publish 없음.
- 후속 core/engine 전체 재검증의 기본 debug 빌드는 linker ENOSPC로101했다.
  테스트 실행 이전 인프라 실패이며 `source-bm25-core-engine-full.log`를 보존한다.
  engine dev 캐시66파일1.6GiB를 Cargo로 정리한 로그는
  `source-bm25-engine-recovery-clean.log`다. 동일 전체 테스트에
  `--config profile.dev.package.os-engine-tantivy.debug=0`만 추가해 debug 심볼
  용량을 줄였으며 테스트를 제외하거나 release 성능 설정을 변경하지 않았다.
  명령은 `RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 cargo
  +nightly test --locked --config profile.dev.package.os-engine-tantivy.debug=0
  -p os-core -p os-engine-tantivy`다. 빌드1분26초, **core16 + engine918 =934성공**,
  실패/skip0, 종료0. engine898/7/4/9건 실행13.93/14.30/2.98/0.31초,
  doctest0, 기존 unused_parens 경고13개다. node와 합계2057성공이다.
  `source-bm25-core-engine-full-recovered.log` SHA-256
  `2f39d4770d996315008b79ba0b9a02092ff9c6cf9e7aadbf2f0d5facecc30506`.
  모든 실행이 종료됐으며 새 release 빌드/전체 성능은 아직 미실행이다.

#### C05/C06 ranking release 전체 반복 FAIL 및 CPU 병목 진단 (2026-09-09)

- 직전 단계는 fallback BM25와 bool 점수 수정 및 debug HTTP2136건/소스
  테스트2057건 통과 근거를 추가한 progress다. 이번에는 전체 성능을 실제로
  실행했고 큰 회귀가 확인됐다. 기능 통과를 단위 완료나 릴리즈 승인으로 세지 않는다.
- `target/core-replacement-c06/ranking-bm25-candidate/source`를 직전 terms-hint
  frozen source에서 복제했다. 현재 root와 crate 전체 diff0이며 기존 FST vendor
  patch를 유지한다. Cargo.lock 차이는 vendor FST 출처뿐이다. node의 직접
  os-query-dsl 의존성을 반영했고 ranking fixture2개도 포함했다.
  source.sha256 manifest SHA-256
  `57336afd17453dc8c429a280a52ef8c9eb330600973bfbd73b0e0dc0601206ea`.
  빌드 전후와 측정 후 manifest 검증 성공이다.
- 유효 Cargo tag 및 보존 af048d73 해시 확인 후 이전 terms-hint RAM release
  캐시1790파일680.6MiB만 Cargo로 정리했다. 새 target은
  `/run/user/1001/steelsearch-ranking-bm25-build-20260909`이며 baseline과 분리했다.
  nightly/locked/release/standalone-runtime, RUSTFLAGS=-Awarnings, jobs2,
  incremental0으로7분47초 빌드/종료0이다. build log SHA-256
  `3c524c15ba6faa87fd7b3b4d2ac52b169b3ead124c25895cba9b154b61a7a60e`.
  보존 실행 파일 `ranking-bm25-candidate/artifacts/steelsearch` SHA-256
  `a1b8c3c3f6bff3c60e36871c76ba87cacb8947c975ef4535575223f9baee462e`.
  RAM 원본과 보존본 해시가 같다. 새 combined FST 전체 source 테스트 증거는
  아니며 직전2057건은 root FST 미패치 테스트임을 구분한다.
- `ranking-bm25-release-live`: 실제 a1b8c3c3 대 OpenSearch3.7.0-SNAPSHOT,
  기존 projected core1500 + 기존추가628 + 신규fallback8 = **2136성공**,
  실패/skip0, 21 subrun 종료0이다. count probe 및 binary/fixture unchanged가
  true다. execution.json SHA-256
  `f143810feaafd7301aca086aa1676e88dfbad59c4e87a92720922feacdaaa25b`.
- 측정 전에 root engine dev 캐시47파일889.4MiB를 Cargo로 정리했다.
  `ranking-bm25-candidate/root-dev-cache-clean.log`와 이전 cache-clean 로그,
  보존 binary/source/기존 원시 보고서는 유지한다. timed suite 및 CPU capture
  도중 코드 수정/빌드/캐시 정리는 하지 않았다.
- 전체 명령은 `python3 tools/run_core_performance_gate.py --baseline-binary
  target/core-replacement-s01/baseline/steelsearch --candidate-binary
  target/core-replacement-c06/ranking-bm25-candidate/artifacts/steelsearch
  --output-dir target/core-replacement-c06/ranking-bm25-repeated-full`이다.
  baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/baseline05,
  각 single/three-node60초, 5000문서/384 source values/4clients/3shards,
  replicas0/1, seed13/timeout10, 기존7개 non-plugin query mix와 개발 내구성,
  Java512MiB 조건을 유지한다. 성능 참조는 기존 pinned OpenSearch2.19 digest다.
- **1101.211초, 6 subrun 종료0, 12 topology error_count0**,
  execution_inputs_verified=true, 최종 종료1/numeric_budget_passed=false,
  acceptance_established=false다. result.json SHA-256
  `e8e00eb432bd0682901534fe7387bd46f25fed1bc6035ea19f2d03050208bcc9`,
  plan.json SHA-256
  `d79e88440d24f5661fe0c94fbc3bf7e7b446689ca69321e20b3d29d62d787858`.
- 공개 v0.6.0 대비01은16/44통과(28초과),04는13/44통과(31초과)다.
  당일 paired는각17/44와13/44통과다. baseline drift00는single write p99
  +5.559041%, three nested p99 +6.777229%로42/44이며05는44/44다.
  drift를 이유로 후보의 큰 회귀를 면제하거나 baseline을 변경하지 않는다.

| topology 처리량 | 최초 v0.6.0 ops/s | 후보01 ops/s (감소율) | 후보04 ops/s (감소율) | OpenSearch02/03 ops/s |
| --- | ---: | ---: | ---: | ---: |
| single-node | 743.011070 | 310.078812 (-58.27%) | 296.917037 (-60.04%) | 281.867621 / 289.829870 |
| three-node | 931.370011 | 676.868135 (-27.33%) | 676.294355 (-27.39%) | 111.026138 / 106.849396 |

아래는 **최초 공개 v0.6.0 대비** 지연 변화율(%), 각 칸은 mean/p95/p99다.
모든7시나리오와 두 topology/반복을 포함한다. 양수가 저하이며 각 값이
독립적으로5% 이하여야 한다. 실제 ms와 OpenSearch 시나리오별 수치는
result.json의 metrics/opensearch_metrics와6개 summary.json에 보존한다.

| topology/scenario | 후보01 mean/p95/p99 (%) | 후보04 mean/p95/p99 (%) |
| --- | --- | --- |
| single/write | -1.71 / +1.68 / +7.47 | +1.49 / +6.17 / +11.84 |
| single/lexical | +37.27 / +34.65 / +135.01 | +54.14 / +41.90 / +210.11 |
| single/ranking | +601.91 / +1168.80 / +2076.02 | +635.64 / +1304.80 / +1998.49 |
| single/facet | +13.55 / +12.98 / +101.76 | +14.12 / +10.33 / +143.22 |
| single/sort_filter | +32.07 / +34.89 / +177.46 | +37.71 / +44.41 / +173.45 |
| single/nested | +13.60 / +17.59 / +164.83 | +11.78 / +15.08 / +102.57 |
| single/refresh | +13.07 / +8.00 / +9.23 | +15.83 / +12.59 / +20.85 |
| three/write | +1.78 / +5.88 / +1.78 | +3.27 / +8.92 / +10.21 |
| three/lexical | -0.43 / +0.63 / -3.83 | +0.54 / +2.00 / +9.54 |
| three/ranking | +203.84 / +294.66 / +264.95 | +201.37 / +292.67 / +268.50 |
| three/facet | -0.03 / -2.11 / +1.32 | +0.44 / +0.62 / +4.93 |
| three/sort_filter | -1.98 / -0.40 / -5.07 | -0.51 / +3.70 / +3.49 |
| three/nested | -3.07 / -2.43 / +2.23 | -4.28 / -2.92 / -2.67 |
| three/refresh | +10.33 / +10.48 / +12.45 | +11.54 / +12.74 / +14.11 |

- 단일 기능의 인과 분리가 아니라, 직전 terms-hint 이후의 ranking 변경군을 포함한
  후보의 누적 비교다. 큰 회귀를 관측했지만 아직 최적화 불가를 입증하지 않았다.
  ledger 제외0을 유지하고 이 후보는 릴리즈/정식 완료에서 차단한다.
- 후속 `ranking-bm25-cpu`: 같은 a1b8c3c3, single-node ranking100,45초 부하 중
  cpu-clock199Hz/20초 DWARF capture다. perf/matrix 종료0, lost samples0,
  실행 파일 해시 불변이다. 관측21.920679초에서 generator CPU7.63초,
  server CPU47.71초다. diagnostic.json SHA-256
  `1b80e6e1e5e1fd37a47753c85829865f79b5a09d5983bbea3cc5ae1b7adcc558`,
  perf.data SHA-256
  `09e4c8b0af7b0a7b524d3e7e815a24092ea48cb91234e059d602611c438e2de1`.
- 전체 capture 분모의 self는 JSON Value vector clone8.00%, malloc7.77%,
  tokenizer iterator6.04%, memcmp6.01%, source field lookup5.57%, Value drop5.41%다.
  inclusive는 native scoped page71.01%, BM25 query scoring47.35%, multi_match
  scorer27.72%, tokenizer16.59%, hit materialization13.35%다. inclusive 비율은
  중첩되므로 합산하지 않는다. CPU 비율이 p99 원인의 비율/속도 개선 증거는 아니다.
- 코드에서 `query_requires_native_candidate_post_filter`의 새 bool multi_match
  조건이 source 후보 경로로 보내고, `search_hits_page_for_source_candidate_post_filter`
  는 각 후보에 `score_document_query`를 호출하며 페이지 적용 전에 SearchHit/source를
  복제함을 확인했다. 다음은 native leaf 점수 정규화로 정확한 bool 점수/순서를
  유지할 수 있는지 확인하고, 필요한 후처리에는 요청별 BM25 문맥 및 선택된
  페이지에 한정한 materialization을 적용하는 최적화 조사다. 단순 guard 제거나
  최종 top-k 상수배, 오류 은폐로 통과시키지 않는다.
- 최적화마다 정확 점수/순서/total/pagination/alias/routing 및 오류 계약을 검증하고,
  별도 frozen release의 확장 live2136건 이상과 **전체 non-plugin 반복 suite**를
  다시 실행한다. 최초 v0.6.0 누적5% 및 시나리오별 판정을 유지한다.
  최적화 불가능한 단일 기능 원인이 입증될 때만 ledger 절차로 제외한다.
  현재 C02/C05/C06/daemon 미완료, 정식 수락0/40, 릴리즈 보류다.
  모든 실행이 종료됐으며 release/tag/publish는 하지 않았다.

#### C05/C06 후처리 BM25 문맥 재사용과 페이지 이후 source 복제 (2026-09-09)

- 직전 단계는 a1b8c3c3의 전체 반복 FAIL과 CPU 진단을 확보한 progress다.
  이번에는 `search_hits_page_for_source_candidate_post_filter`의 불필요한
  materialization 및 문서별 BM25 문맥 재생성을 줄였다. 지원 범위를 줄이거나
  native/source guard를 제거하지 않았으며 정확 점수 계약을 완화하지 않았다.
- 기존 required bool native 후보를 얻는 경우와 전체 source 후보를 쓰는 경우를
  동일한 후처리 루프로 연결했다. candidate 선택과 selected shard 의미는 유지한다.
  요청마다 한 BTreeMap 문맥을 만들고 `score_document_query_with_bm25_context`로
  같은 snapshot의 필드 통계를 재사용한다. 캐시가 다른 요청/refresh를 넘지 않는다.
- 기본 relevance 정렬은 `(&StoredDocument, f32)`를 보관하고 기존 score 비교와
  ID 동점 순서로 정렬한다. 단일 index 호출이므로 모든 hit의 index는 같다.
  from/size 적용 후에만 SearchHit/source를 복제한다. size0/범위 밖 페이지도
  전체 matching/score 평가와 total은 유지하고 응답 문서 복제는 하지 않는다.
  명시적 정렬은 기존 mapped/general sort 및 오류 전달을 유지한다.
  기존 zero-score 변환은 이번 성능 변경에서 별도로 바꾸지 않았다.
- 최초 focused4건 성공 후 기존 bool page 회귀를288조합으로 확장했다:
  1/3shards, must/nested-bool/should-only3형태, selected None/empty/[0]/all,
  relevance/keyword desc2정렬,6페이지(0/범위밖/usize::MAX 포함)다.
  독립 per-document 기존 scorer로 eager SearchHit를 만들고 ID/score/source/total을
  대조한다. 이는 이전 eager 구현과의 등가성이지 다중 shard OpenSearch 점수의
  독립 검증은 아니다. 후속 실제 참조 fixture를 유지/확장해야 한다.
- 첫 전체 테스트는897성공/1실패였다. 확장 테스트가 일반 keyword 정렬에도
  MappedEngineSort가 있다고 가정한 None unwrap이며 참조 코드의 전제 오류다.
  실제 분기처럼 mapped 정렬기 부재 시 general sort를 적용하도록 테스트를
  수정했다. 기대 점수/정렬/지원 조건은 완화하지 않았다.
  `ranking-borrowed-engine-full.log`의 실패와 focused 로그는 보존한다.
- `RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 cargo +nightly
  test --locked --config profile.dev.package.os-engine-tantivy.debug=0
  -p os-engine-tantivy` 전체 재실행은 빌드1분22초/종료0,
  **898+7+4+9=918성공**, 실패/skip0이다. 실행13.93/14.23/2.90/0.33초,
  doctest0, 기존 괄호 경고13개다. root FST 미패치 테스트이며 별도 FST 패치 후보
  검증을 대신하지 않는다. `ranking-borrowed-engine-full-recovered.log` SHA-256
  `a4803b15deec1f554e397af99cc25b2d6ffeaef09f43c94aa3d3d7863835ca61`.
  engine lib SHA-256
  `132ebc1cbabfc5dac6ff5d3df6e606f21ae36f1cc8774293367d3c4d600fde7d`,
  multi_match_field_tests.rs SHA-256
  `b794e8cb79a79e640e85d49bb3ad644aef3594b6f7ebc9c9283df3f183fc5384`.
- 아직 이 최적화의 release/HTTP/전체 성능은 미실행이다. clone 감소만으로
  a1b8c3c3의 큰 ranking 회귀가 해결됐다고 주장하지 않는다. 다음은 불필요한
  source 후처리를 피할 수 있는 native leaf BM25 정규화 경계 확인이다.
  field/query boost, bool의 비점수 절, norm, shard 통계, phrase 및 오류 계약을
  실제 OpenSearch와 비교해야 한다. 기존3shard eager 점수가 참조와 같다고
  가정하거나 마지막 top-k에 배율을 적용해 후보 순서 문제를 숨기지 않는다.
- 최적화 단위 완료 전에 별도 frozen release의 확장 HTTP2136건 이상과
  **전체 non-plugin 반복 benchmark**를 실행한다. 최초 v0.6.0 누적 처리량95%
  이상/각 시나리오 mean/p95/p99 105% 이하, 반복/paired/drift 조건을 유지한다.
  최신 실제 전체 성능은 여전히 a1b8c3c3 FAIL, 정식 수락0/40,
  C02/C05/C06/daemon 미완료, ledger 제외0, 릴리즈 보류다.
  모든 실행이 종료됐으며 release/tag/publish는 하지 않았다.

#### C05/C06 native filter 점수와 필드 통계 경계 (2026-09-09)

- 직전 사용자 응답은 상태 설명만 제공한 no-progress였다. 기존 테스트 세션47012를
  재확인하여 종료0/집중 테스트1건 성공을 회수했고, 실제 코드/로그를 읽고 이어갔다.
- `build_tantivy_query`의 bool filter를 ConstScoreQuery(0)로 감싸 matching은
  유지하되 관련도 점수 기여를 제거했다. minimum_should_match 분기의 required
  조건도 must/filter를 합치지 않고 내부 bool로 보존한다. required가 없으면
  빈 목록을 유지한다. 기존 source 후처리 guard는 제거하지 않았다.
- 기존 native filter 전체 테스트 로그 `native-filter-score-engine-full.log`는
  899+7+4+9=919성공, 종료0이다. SHA-256:
  `fc98688a519a5dfe6028dc10b4e00b42ec7bc90eeb53b101c670deabb4d92f2e`.
  minimum_should_match 0/1/2에서 filter 추가 전후 점수 불변, 불일치 filter의
  결과 없음, filter-only 점수0을 검사한다. should 조합 중복에 따른 전체 점수의
  정확성까지 증명하는 테스트는 아니다.
- Tantivy 0.21.1의 Bm25StatisticsProvider/EnableScoring API로 별도 필드 통계를
  주입하는 재현 테스트를 확인했다. 짧은 title 문서 a/b와 title null/값 문서 c에서
  기본 native/source 배율은 sparse일 때 문서마다 달랐다. 필드별 문서 수와
  scorer boost 1/2.2를 적용하면 두 경우 모두 source 점수와 오차1e-6 이내였다.
  기존 집중 로그 `native-field-statistics-focused.log` SHA-256:
  `16ac71a453f2073fb1f9e36a8e4523e14a50ec3f6b90f0fa22626aeb4cb6ad3b`.
- 이번에는 fixture 상수 대신 실제 searcher의 각 segment fieldnorm이 0이 아닌
  문서 수를 합산하여 통계 제공자에 전달하도록 테스트를 강화했다. fixture의
  dense3/sparse2와 일치함도 독립 확인했다. 삭제 없는 단일 shard/짧은 필드의
  API 재현이며 production 통계 구현이나 모든 analyzer/삭제 상태의 증거는 아니다.
- 전체 재실행 명령:
  `RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 cargo +nightly test
  --locked --config profile.dev.package.os-engine-tantivy.debug=0 -p os-engine-tantivy`.
  빌드1분22초, 세션28700 종료0, **899+7+4+9=919성공**, 실패/skip0.
  실행14.34/15.04/2.82/0.30초, doctest0, 기존 괄호 경고13개다.
  `target/core-replacement-c06/native-snapshot-statistics-engine-full.log` SHA-256:
  `ca89642919ad68f44442e3ecb67af6cbce1473aadde960b7ed6cc5915ee4b3a3`.
  engine lib SHA-256:
  `51fc5535ab2ebc2066f226336c09cf11d08821262c42efa79bee2230312962de`.
  multi_match_field_tests.rs SHA-256:
  `34d1ef0ded9beb71ee1dd9b9ce3a7616bc34b4b13929480bb55396b497c06ad8`.
- 남은 적용 전 검증: native fieldnorm은 길이41을40으로 압축하지만 source BM25는
  원래 토큰 길이를 쓴다. 긴 문서, 삭제/refresh/merge, field/query boost, analyzer,
  phrase, minimum_should_match 점수 및 shard별 통계를 실제 참조와 비교해야 한다.
  필드별 통계 제공자의 total_num_docs에는 field 인자가 없으므로 다중 필드 전체에
  하나의 문서 수를 주입하지 않는다. leaf별 정확성을 확보한 뒤 native top-k 전에
  적용해야 하며, 최종 선택 hit에만 배율을 적용해 순위 차이를 숨기지 않는다.
- 최적화 단위는 아직 진행 중이다. 별도 frozen release/확장 HTTP2136건 이상 및
  **전체 non-plugin 반복 benchmark**를 실행하기 전 완료 처리하지 않는다.
  v0.6.0 고정 누적 처리량95%/각 시나리오 mean/p95/p99 105%와 반복/paired/drift
  조건을 유지한다. 이번 테스트는 성능 회복 증거가 아니며 최신 전체 측정은
  여전히 a1b8c3c3 FAIL이다. 정식 수락0/40, 제외0, 릴리즈 보류를 유지한다.
  모든 실행이 종료됐으며 release/tag/publish는 하지 않았다.

#### C05/C06 긴 문서 길이 norm 재현 및 공통 계산 수정 (2026-09-09)

- 직전 단계는 스냅샷 통계 재현/engine919건과 계획 갱신을 완료한 progress다.
  이번에는 실제 OpenSearch 참조와 긴 문서 점수 차이를 확인한 뒤 수정했다.
- `tools/fixtures/search-bm25-length-norms-compat.json`을 추가했다. 단일 shard,
  title 길이1/40/41/42/1000 및 missing 문서를 두고 match/bool match/multi_match/
  bool multi_match와 명시적 index 옵션으로 선택한 fallback2경로의 점수를 비교한다.
  fixture SHA-256 `f708ad9dc9ccdd7e080cdf7c9d9998467635cc22fbf6ef6a3b53032315e9c30d`.
- `env PYTHONPATH=tools python3 target/core-replacement-c05/run-live.py
  --output-dir target/core-replacement-c06/length-norms-ranking-release-live
  --candidate-binary target/core-replacement-c06/ranking-bm25-candidate/artifacts/steelsearch
  --additional-fixture tools/fixtures/search-bm25-length-norms-compat.json`을 실행했다.
  세션13240 종료1. 실제 executable a1b8c3c3, 참조3.7.0-SNAPSHOT,
  binary_unchanged/fixtures_unchanged=true. 기존 core1500건 성공, 신규6건 실패,
  skip0이다. 기존2136건 성공이 새 길이 fixture까지 보장하지 않음을 명시한다.
  execution.json SHA-256
  `e3fc5d63a2c9a64bf3f45fef3012ea6779cafe68f1d4b6968196f0c412a76880`.
- match의 41토큰 점수는 참조0.059591025, 기존 후보 약0.059428이고,
  1000토큰은 참조0.016606808, 기존 후보 약0.016406이었다. 일반 bool match는
  41토큰 약0.355560으로 길이 norm 외에도 native 통계/배율 차이가 남는다.
  HTTP6건 모두 해결됐다고 주장하지 않는다. 원본 실패 보고서를 보존한다.
- `os_core::bm25`에 decoded byte4 문서 길이와 normalized_term_frequency를
  추가했다. 41은40, 1000은984이며 signed32 최대 범위를 넘으면 최대 norm으로
  포화한다. 기존 raw term_frequency의 산술 계약/테스트는 유지한다.
  FieldStatistics와 engine의 opensearch_bm25_tf가 정규화된 함수를 사용한다.
  평균 필드 길이와 문서 빈도는 압축하지 않는다. node SourceScoring도 기존 공통
  FieldStatistics 호출을 통해 같은 계산을 사용하며 node 파일 자체는 변경하지 않았다.
- 참조 HTTP의 실제 점수5개를 core 회귀 테스트로 추가했다(오차1e-7).
  engine은 길이0..65536, native norm256개 각각의 전후 경계, u32::MAX를
  Tantivy FieldNormReader와 대조한다. 필드별 통계 주입 재현도 길이5/41/1000과
  dense/sparse6조합으로 확장하여 score 오차1e-6 이내임을 확인했다.
  이 검증으로 production native leaf 통계 주입/guard 제거까지 수락하지 않는다.
- `RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 cargo +nightly
  test --locked --config profile.dev.package.os-engine-tantivy.debug=0
  -p os-core -p os-engine-tantivy` 실행은 빌드1분28초/세션21812 종료0,
  core17 + engine(900+7+4+9)920 = **937성공**, 실패/skip0이다.
  engine 실행14.31/14.87/2.90/0.31초, doctest0, 기존 괄호 경고13개다.
  `target/core-replacement-c06/length-norms-core-engine-full.log` SHA-256
  `ff0d34247aa847ab2fcd813b72e8f98180d219f946d889b570bc6b872a236f32`.
  core bm25.rs SHA-256
  `c8daddbe2492a6eeea244d26a6890be903e62b49b97f5d4a10d974c22cbee1b7`,
  engine lib SHA-256
  `4fa9a7167fc34248f771dfa3936632900d5f1ef2580a54841442f53ef4734cd8`,
  multi_match_field_tests.rs SHA-256
  `4b5aa72d71e8260185e574e9bc117f251a6c1a762d1573b9d85b4d26d1a869fd`.
- 다음 검증은 node 재검증, native leaf 통계와 bool match 차이 수정, 별도로
  보존한 후보에서 기존2136건+신규6건 이상의 HTTP 비교 및 **전체 non-plugin
  반복 benchmark**다. 최적화 단위를 이 검증 전에 완료 처리하지 않는다.
  v0.6.0 고정 누적 처리량95% 이상/각 시나리오 mean/p95/p99 105% 이하와
  반복/paired/drift 조건을 유지한다. 단일 기능의 최적화 불가능한5% 이상
  저하는 아직 입증되지 않았으므로 ledger 제외0, 정식 수락0/40이다.
  모든 실행이 종료됐으며 release/tag/publish는 하지 않았다.

#### C05/C06 native match의 필드별 BM25 통계 적용 (2026-09-09)

- 직전 단계는 긴 문서 HTTP6건 실패 재현과 공통 길이 norm 수정/core17+engine920
  검증을 수행한 progress다. 이번에는 text match의 native 점수 생성 경로를 수정했다.
- `native_bm25.rs`에 필드 통계 제공자와 Query wrapper를 추가했다. weight 생성 시
  실제 searcher의 필드별 문서 수를 전달하고 Tantivy BoostQuery(1/2.2)를 사용한다.
  보정은 leaf weight에서 이뤄져 bool 조합 및 top-k 선택보다 앞선다.
  최종 반환 hit만 재배율하는 방식은 사용하지 않았다.
- `TantivySearchState`는 스냅샷별 Arc/Mutex 필드 통계 캐시를 가진다. 최초 scoring
  요청에 해당 필드의 segment fieldnorm을 조회하며 이후 동일 스냅샷에서 재사용한다.
  append refresh가 searcher를 교체할 때 새 캐시를 발행한다. 이전 snapshot clone은
  이전 캐시를 유지한다. count 등 점수 없는 weight는 통계 조회 없이 기존 경로로 간다.
  이전 query를 다른 generation에 사용하면 캐시를 쓰지 않고 실제 searcher를 조회한다.
- 문서 수/토큰 수/term 빈도는 native segment 기준이다. 삭제 문서가 merge 전까지
  토큰 총계/빈도에 포함되므로 필드 문서 수도 max_doc 중 nonzero norm을 센다.
  서로 다른 field에 단일 문서 수를 주입하지 않는다. fieldnorm 없는 경우의 오류를
  임의 숫자로 대체하지 않는다. 이 적용은 현재 text match parser 분기에 한정된다.
- 기존 dense/sparse 및 길이5/41/1000 재현에서 raw Tantivy 점수와 실제 보정 경로를
  분리했다. 실제 보정 경로와 source 점수의 오차1e-6 이내를 검사한다. 기존 filter
  비점수 계약과 minimum_should_match filter 추가 전후 점수 불변 검증도 유지한다.
- 최초 연결 후 전체 engine920건 통과, 로그
  `target/core-replacement-c06/native-leaf-bm25-engine-full.log` SHA-256
  `47b395a8d62cb75a631a1390a78c65755bd8b75dfd493d6555f2e639b21249ef`.
  이후 직접 native index 테스트로 필드 문서 수1/2의 분리, count의 캐시 미생성,
  append 후 통계 변경, 이전 query를 새 searcher에 사용한 결과의 신선한 query와
  일치, 이전 searcher 결과 유지, 삭제 전후 및 명시적 merge 후 필드 문서 수를
  확인했다. 이는 Tantivy lifecycle 검증이며 실제 OpenSearch 삭제 점수 비교는 남는다.
- 전체 명령 `RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0
  cargo +nightly test --locked --config profile.dev.package.os-engine-tantivy.debug=0
  -p os-engine-tantivy`는 빌드1분24초/세션70660 종료0,
  **901+7+4+9=921성공**, 실패/skip0이다. 실행14.00/14.45/2.92/0.30초,
  doctest0, 기존 괄호 경고13개다. snapshot 전체 로그 SHA-256:
  `39c5b287e28c94dd3b3d586a17dc4a5b37c300dcc89c41df25e0a7bf270d1a1d`.
  파일: `target/core-replacement-c06/native-leaf-bm25-snapshot-engine-full.log`.
  native_bm25.rs SHA-256
  `ecc4cdf260fad796617e5f0985bac6a0d6047026c9677dc3c8d943c0fc8adb87`,
  engine lib SHA-256
  `62b05b2ca04b33a8f5b9a7515d34db32869157ca4240b3042f9786163b5ed68b`,
  multi_match_field_tests.rs SHA-256
  `b7855215ad55ee7cc0ac28db0a7bf9ce79efe4ac238be8a311a64a485a67e6f5`.
- 남은 범위: node 재검증 및 새 binary의 기존2136+길이6건 이상 HTTP 비교,
  query boost/phrase/다중 field parser 문법/삭제/샤드별 점수 검증이다. 일반 bool
  match의 실제 HTTP 차이 해소는 아직 재측정하지 않았다. 기존 multi_match source
  후처리 guard를 유지하므로 큰 성능 회귀가 해결됐다는 증거도 아직 없다.
- 최적화 단위 완료 전 별도 frozen release의 **전체 non-plugin 반복 benchmark**를
  실행한다. v0.6.0 고정 누적 처리량95% 이상, 각 시나리오 mean/p95/p99 105% 이하와
  반복/paired/drift 조건을 유지한다. 최신 실제 성능은 a1b8c3c3 FAIL이며 정식 수락0/40,
  제외0, 릴리즈 보류다. 모든 실행이 종료됐으며 release/tag/publish는 하지 않았다.

#### C05/C06 native BM25 node 및 확장 HTTP 재검증 (2026-09-09)

- 직전 단계는 native leaf 통계 적용과 engine921건 검증을 수행한 progress다.
  이번에는 코드 추가 없이 현재 node 계층과 실제 HTTP 계약을 재검증했다.
- `RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 cargo +nightly
  test --locked --config profile.dev.package.os-engine-tantivy.debug=0
  --config profile.dev.package.os-node.debug=0 -p os-node --features standalone-runtime
  --lib --bin steelsearch`는 빌드1분21초/세션27208 종료0,
  **664+459=1123성공**, 실패/skip0이다. 실행5.99/11.94초다.
  daemon 통합 테스트와 benchmark는 이 명령에 포함되지 않는다.
  `target/core-replacement-c06/native-leaf-bm25-node-full.log` SHA-256
  `97f51f7099f1f28bf1335f29c83206574a4cef7e1c557fdcc4072ff95ca8423d`.
- 같은 설정으로 `build --bin steelsearch`를 실행한 최초 세션71915는 os-node
  rlib 생성 중 디스크 부족으로 종료101이었다. 실패 로그 SHA-256
  `ba2e5fcd42b6f1e75a1c52361f23ad3263268c2fb0436366d48eae30e3023907`.
  로그 `native-leaf-bm25-debug-build.log`를 보존했다. target/CACHEDIR.TAG와
  종료된 테스트의 실제 경로를 확인한 뒤 node/steelsearch/engine 테스트 실행 파일을
  `/run/user/1001/steelsearch-completed-test-cache-20260909`로 이동했다.
  보존된 a1b8c3c3 release 해시와 RAM build CACHEDIR.TAG를 확인한 뒤
  `cargo +nightly clean --release --target-dir
  /run/user/1001/steelsearch-ranking-bm25-build-20260909`로1790파일/681.4MiB의
  재생성 가능한 캐시만 정리했다. baseline/후보 실행 파일/검증 증거는 삭제하지 않았다.
- 재빌드 세션81734는33.41초/종료0이었다. recovered build 로그 SHA-256
  `742d1c6edc70f790fdeaf4453703155c1d39308a0efb4caac91ca5e863612b5c`.
  `target/core-replacement-c06/native-leaf-bm25-debug/steelsearch`로 보존했다.
  실제 SHA-256 `4f1fbc48a5302d399e75e8188b7fa45749a50dc9c7d5814e455debe9d16ed46a`.
  root FST 미패치 debug executable이며 별도 frozen release의 성능 증거가 아니다.
- 기존 확장 HTTP2136건 명령의 candidate를 이 파일로 바꾸고
  `--additional-fixture tools/fixtures/search-bm25-length-norms-compat.json`을 추가했다.
  출력 `target/core-replacement-c06/native-leaf-bm25-debug-live`, count probe 활성화,
  세션22363 종료0. 실제 참조3.7.0-SNAPSHOT과22개 subrun에서
  **2142성공, 실패/skip0**, count probe=true,
  binary_unchanged/fixtures_unchanged=true다. fixture 목록과 해시는 plan.json 및
  execution.json에 있고 개별 보고서와 원본 응답을 보존한다.
  execution.json SHA-256
  `5ab1c61a9935e7b20562046a12e19ab577e25ef9c7f5daa87c84cbb4ca09e126`.
- 길이 norm6건은 모두 통과했고 일반 bool match도 참조와 같은 점수/ID/total이었다.
  비교기는 점수를 소수6자리로 반올림한다. 41토큰0.059591, 1000토큰0.016607이며,
  field boost2의 multi_match는 각각0.119182/0.033214다.
  이는 해당 fixture의 불일치 해소이지 모든 query boost/phrase/parser/삭제/다중 shard
  조합의 정확성 증명은 아니다. 기존 실패한 a1b8c3c3 보고서는 그대로 보존한다.
- 다음은 남은 native/source 경계 검증과 후처리 비용 복구, 별도 frozen release의
  확장 HTTP2142건 이상 및 **전체 non-plugin 반복 benchmark**다. 이 검증 전에는
  최적화 단위를 완료 처리하지 않는다. v0.6.0 고정 누적 처리량95% 이상 및 각
  시나리오 mean/p95/p99 105% 이하, 반복/paired/drift 조건을 유지한다.
  최신 실제 전체 성능은 여전히 a1b8c3c3 FAIL이다. 정식 수락0/40, ledger 제외0,
  릴리즈 보류이며 모든 실행이 종료됐다. release/tag/publish는 하지 않았다.

#### C05/C06 native bool 조합 점수와 match boost (2026-09-09)

- 직전 단계는 node1123건/실제 HTTP2142건 검증을 수행한 progress다.
  현재 전체 후보 후처리 guard를 조사하면서 native Query::Match의 boost가
  전달되지 않음을 확인했다. 기존 maybe_boost_tantivy_query 헬퍼를 사용하도록
  수정했다. field boost와 query boost를 혼동하거나 후처리 조건을 제거하지 않았다.
- 새 테스트는 단일 shard40문서, 두 text 필드(하나는 일부 null), 긴 필드 길이,
  keyword service를 사용한다. best_fields/most_fields2모드와 match boost0/0.5/2를
  조합하고 title^8/body^2, tie_breaker0.3, must/should/filter를 함께 검사한다.
  native top40 후보 모두에 대해 독립 source scorer와 오차1e-5 이내를 확인했다.
  240개 후보 점수 대조이며, 다중 shard의 ID 동점 순서나 page 경계까지 증명하지 않는다.
- 최초 빌드는 f64 boost를 Tantivy f32 인수에 직접 전달한 컴파일 오류로 종료101.
  기존 헬퍼를 사용해 수정했고 원본 `native-bool-ranking-engine-full.log`를 보존했다.
  SHA-256 `a729c155e26f46d94c6cb5eaa3b9a267faa379074910b48c3f5c7a84b6ac83cb`.
- `RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 cargo +nightly
  test --locked --config profile.dev.package.os-engine-tantivy.debug=0
  -p os-engine-tantivy` 재실행은 빌드1분29초/세션71935 종료0,
  **902+7+4+9=922성공**, 실패/skip0이다. 실행14.37/14.85/2.91/0.32초,
  doctest0, 기존 괄호 경고13개다.
  `target/core-replacement-c06/native-bool-ranking-engine-full-recovered.log` SHA-256
  `bce1dcb976ec1aecc989dbf00cfa9c27b3bf525bc9dafd285de14b7b33426d07`.
  engine lib SHA-256
  `f84c06713dc9c8d1ab797ea2e88dad04c9a78b15175ff7f0457606075b1bbdb8`,
  multi_match_field_tests.rs SHA-256
  `140c67438892cbff1fb4e73b61e8c76476c7b013af2c387537747f5d44c92a75`.
- 빌드 공간 확보를 위해 종료된 node dev 캐시만 cargo clean으로 정리했다
  (31파일/371.9MiB). 별도 보존된 debug 4f1fbc48의 해시가 그대로임을 확인했다.
  baseline/실행 증거는 보존했으며 새 변경의 node/HTTP 재검증은 아직 없다.
- 다음은 다중 shard 통계/순위 및 page 경계를 검증하고 후처리 비용을 복구하는
  단계다. 단순 guard 제거로 정확성을 우회하지 않는다. 최적화 단위 완료 전에
  별도 frozen release의 확장 HTTP2142건 이상과 **전체 non-plugin 반복 benchmark**를
  실행한다. v0.6.0 고정 누적 처리량95% 이상 및 각 시나리오 mean/p95/p99 105% 이하,
  반복/paired/drift 조건을 유지한다. 최신 실제 성능은 a1b8c3c3 FAIL이며
  정식 수락0/40, 제외0, 릴리즈 보류다. 모든 실행이 종료됐고 release/tag/publish는 없다.

#### C05/C06 3-shard 기본 관련도 점수 차이 재현 (2026-09-09)

- 직전 단계는 native match boost 수정과 engine922건 검증을 수행한 progress다.
  이번에는 production 코드를 바꾸지 않고 3-shard HTTP 증거를 추가했다.
- 명시적 score desc/order asc 정렬 fixture
  `tools/fixtures/search-bm25-shard-statistics-compat.json`을 추가했다.
  길이1/40/41/42/1000 및 missing 문서, shard3/replica0, match/bool match/
  multi_match/bool multi_match/fallback2형태 각각 전체 및 from1/size2 페이지다.
  SHA-256 `1f3a986016642789dedfd56847c7becee5dc4976875e4800d8fccb38c1e1dfbb`.
- 기존 run-live.py에 candidate 4f1fbc48과 위 additional-fixture를 전달하고
  `target/core-replacement-c06/native-bm25-shard-statistics-live`에 기록했다.
  세션44727 종료0, 기존 core1500+신규12=1512성공, 실패/skip0이다.
  execution.json SHA-256
  `5c09ab30fe6b79c56067c614b0806591933c5495f06460b82ad9487f5d75b94b`.
- 정렬 옵션으로 실행 경로가 달라질 수 있어 기본 관련도 fixture를 별도로 추가했다.
  `tools/fixtures/search-bm25-shard-native-compat.json`은 score 동점 혼동을 줄이기
  위해 길이41 대신44를 사용하고 sort/track_scores 옵션 없이 동일6형태/2페이지를
  비교한다. ID도 len-44로 달라져 shard 배치가 다르므로 두 fixture의 점수를
  서로 직접 비교하지 않는다. SHA-256
  `7c3c3bab7c4147e751b024c4038d73b67186487b4cdbec77e06e4bcf40d45d41`.
- 같은 helper/candidate에 이 fixture를 전달하고
  `target/core-replacement-c06/native-bm25-shard-default-live`에 기록했다.
  세션92952 종료1, 기존1500+신규6성공/신규6실패, skip0이다.
  execution.json SHA-256
  `35adcdcc973323e845426b23759a37cd0f672fb94c6479f11d87630216d24d47`.
  실제 참조3.7.0-SNAPSHOT, binary/fixtures unchanged=true.
  보존 후보 SHA-256
  `4f1fbc48a5302d399e75e8188b7fa45749a50dc9c7d5814e455debe9d16ed46a`이며
  후속 match boost 수정 전 파일이다. 이번 fixture에는 match boost 옵션이 없다.
- 기본 match/multi_match/bool multi_match의 전체/페이지6건이 실패했다.
  bool match와 명시적 index 옵션 fallback2형태의6건은 통과했다.
  예: match len-40 점수는 참조0.130765, 후보0.059608;
  len-1000은 참조0.059399, 후보0.016640이다. 이 fixture에서 ID/total은 같지만
  점수가 다르다. 순위가 언제나 같다는 뜻은 아니며 재정렬/페이지 검증을 유지한다.
- 코드에서 opensearch_bm25_field_stats가 refreshed_documents_iter 전체를 합산하고
  native hit 경로가 opensearch_text_bm25_score로 점수를 덮어쓰는 것을 확인했다.
  native bool match가 통과하고 source 점수 경로가 실패한 관측과 부합한다.
  다음 수정은 source 통계 캐시의 shard 범위 분리와 문서 routing/alias 통계 범위
  검증이다. 최종 top-k 점수만 수정해 후보 순서 차이를 숨기지 않는다.
- 수정 후 기존2142건+신규24건 이상 HTTP와 별도 frozen release의 **전체 non-plugin
  반복 benchmark**를 실행하기 전 최적화 단위를 완료 처리하지 않는다.
  v0.6.0 고정 누적 처리량95%/각 시나리오 mean/p95/p99 105% 및 반복/paired/drift
  조건을 유지한다. 이번은 기능 차이 재현이며 최적화 불가능한 성능 저하의
  입증이 아니므로 ledger 제외0이다. 정식 수락0/40, 최신 성능 a1b8c3c3 FAIL,
  릴리즈 보류를 유지한다. 모든 실행이 종료됐으며 release/tag/publish는 없다.

#### C05/C06 source BM25 통계의 shard 분리 (2026-09-09)

- 직전 단계는 실제 3-shard HTTP 기본 관련도6건 실패를 재현한 progress다.
  이번에는 source BM25 통계의 범위를 수정했다.
- 공유 bm25_stats_cache와 요청별 문맥을 Bm25Context로 통일했다:
  `BTreeMap<u32, BTreeMap<String, CachedBm25FieldStats>>`다. 문자열에 shard를
  이어 붙이지 않고 구조화된 key를 사용한다. 기존 field 빈도 Arc 공유와
  refreshed_seq_no 기반 snapshot 구분은 유지한다.
- match/phrase의 직접 점수 및 요청별 문맥 경로에 실제 StoredDocument를 전달한다.
  저장된 ID/routing과 기존 shard_id_for_write로 shard를 선택하고 해당 shard의
  refreshed_values만 집계한다. alias filter나 요청 selected_shards로 통계 모집단을
  축소하지 않는다. multi_match는 각 field scorer를 통해 같은 범위를 사용한다.
  이 변경은 후보 평가 시점의 source 점수에도 적용하며 최종 hit만 수정하지 않는다.
- 기존 snapshot/Arc 재사용 테스트는 shard0을 명시하고 실제 문서를 전달하도록
  갱신했다. 첫 전체 실행은922성공/실패0/종료0이었다.
  `target/core-replacement-c06/source-bm25-shard-engine-full.log` SHA-256
  `1f534b89ff445c4430d1ea97ff1794b93b6e0bc0bc79e0621156e418717fa71c`.
- 독립 회귀 테스트가 search-bm25-shard-native-compat.json의 실제 문서를 사용한다.
  이전 OpenSearch 참조에서 얻은5문서 점수를 고정하여 source scorer를 대조하고,
  각 query의 전체 및 from1/size2 native page의 total/ID/score를 확인한다.
  점수 오차2e-6이며 참조값의 소수6자리 반올림과 field boost2를 고려한다.
  요청별 캐시에 shard3개가 분리되고 title 문서 수 합계가5임도 검사한다.
  fixture의 HTTP 옵션은 이 engine API 테스트에 전달되지 않으므로 fallback
  HTTP 경로까지 통과했다는 증거로 해석하지 않는다.
- 전체 재실행 명령은 `RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0
  cargo +nightly test --locked --config profile.dev.package.os-engine-tantivy.debug=0
  -p os-engine-tantivy`다. 빌드1분25초/세션54888 종료0,
  **903+7+4+9=923성공**, 실패/skip0. 실행13.92/14.10/2.80/0.33초,
  doctest0, 기존 괄호 경고13개다.
  `target/core-replacement-c06/source-bm25-shard-pages-engine-full.log` SHA-256
  `ee1cbe34c915992ec33c4114a4cce501e51199301703886dfaf20cf0b223a595`.
  engine lib SHA-256
  `1447353c3471485bde33c6d322e4d4a2b15f6c365d61efcfd24b94414ca66a7f`,
  multi_match_field_tests.rs SHA-256
  `ea295b27753086dfa3704828fafc6b6c313d8904b9af9993d98f956113f51769`.
- node/HTTP 재검증은 미실행이다. alias/명시적 routing의 shard 통계 범위도
  추가 검증한다. 최적화 단위 완료 전에 별도 frozen release의 HTTP2166건 이상과
  **전체 non-plugin 반복 benchmark**를 실행한다. v0.6.0 고정 누적 처리량95% 이상,
  각 시나리오 mean/p95/p99 105% 이하 및 반복/paired/drift 조건을 유지한다.
  최신 실제 성능은 a1b8c3c3 FAIL이고, 이번 테스트는 성능 회복의 증거가 아니다.
  정식 수락0/40, ledger 제외0, 릴리즈 보류다. 모든 실행이 종료됐으며
  release/tag/publish는 하지 않았다.

#### C05/C06 shard BM25 frozen release 및 갱신 경계 (2026-09-09)

- 직전 단계는 source 통계 shard 분리와 engine923건 검증을 수행한 progress다.
  이번에는 별도 release 후보를 만들고 실제 HTTP 범위를 확장했다.
- `target/core-replacement-c06/shard-bm25-candidate/source`에 이전 후보의 build 설정을
  복제한 뒤 현재 crates를 반영했다. rsync가 없어 cp를 사용했고 `diff -qr crates`
  결과가 동일함을 확인했다. Cargo.toml/lock 차이는 기존 vendor tantivy-fst 패치와
  그 registry 항목뿐이다. root 소스와 frozen build 설정을 혼동하지 않는다.
  source.sha256 SHA-256:
  `9fd59fc8a3c61d2faa62aab430206dcf3d7950a000d7e8f4905034274b796169`.
  빌드 및 HTTP 종료 후 manifest 전체 검증을 통과했다.
- `RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0
  CARGO_TARGET_DIR=/run/user/1001/steelsearch-shard-bm25-build-20260909 cargo +nightly
  build --release --locked --manifest-path
  target/core-replacement-c06/shard-bm25-candidate/source/Cargo.toml
  -p os-node --features standalone-runtime --bin steelsearch`는 세션48879 종료0,
  7분50초였다. build log SHA-256
  `aaf5bf630d424bfde6e596b3c514987cf8bd23be2e1fd5413afe1e964257f7a0`.
  `target/core-replacement-c06/shard-bm25-candidate/artifacts/steelsearch`로 보존했으며
  RAM 원본/보존본 SHA-256은 모두
  `1fa59b13e4270458d5a154db0e94c342d2c165bd7ff0573581bd8cd219aea23f`다.
  release profile 빌드이지 tag 또는 GitHub release 발행은 아니다.
- 신규 `search-bm25-routing-scope-compat.json`은 shard3, 명시적 저장 routing,
  alias filter와 search_routing alias, match/boost0.5/bool multi_match,
  전체/중간 페이지18건이다. 각 case에서6문서를 덮어쓰고 refresh한다.
  fixture SHA-256 `ae3a43b7772d3b091347dff7063a2e8eff29343fe43c61d8a3a63e9294d4c6e6`.
- 기존 run-live.py의 확장 fixture 목록에 길이/3-shard2종/routing을 포함하고
  새 candidate와 --count-probe를 사용했다. 출력 `shard-bm25-release-live`,
  세션99283 종료1. 실제 참조3.7.0-SNAPSHOT,25개 subrun,
  **2167성공/17실패/skip0**, count probe=true,
  binary_unchanged/fixtures_unchanged=true다. 기존2166건은 모두 통과했고,
  이전 기본 관련도3-shard6건도 해소됐다. 새18건 중 첫 항목만 통과했다.
  execution.json SHA-256
  `d7fd033f5cda040532ec51c1f5bf07e797f08a13f6414a7e8d5180fe56727d36`.
- 실패 항목의 PUT/refresh/search 상태 검증은 성공했다. 예를 들어 두 번째 적재 후
  routing match의 문서 a는 참조0.052047/후보0.093782이고, 다음 alias 검색에서
  참조0.036024/후보0.093782다. 삭제된 이전 문서와 merge 시점의 통계 영향이
  의심되지만 아직 이를 단독 원인이나 결함으로 확정하지 않았다. 설명 통계와
  갱신/삭제/merge 전후 검증이 필요하며 실패17건을 제외/통과 처리하지 않는다.
- 이를 분리하기 위해 `search-bm25-routing-initial-compat.json`을 추가했다.
  첫 case에서만 적재/refresh하고 이후 같은18개 query를 수행한다. 원래 반복 갱신
  fixture와 실패 증거는 그대로 유지했다. initial fixture SHA-256
  `d354cb7e9d69178e3c33920a8fecdd6352acddb0238d60c183f55866ff83a9f6`.
  같은 candidate로 `shard-bm25-routing-initial-live`에서 재실행한 세션58332는
  종료0, core1500+신규18=1518성공/실패·skip0이다. 실행 기록 SHA-256
  `ab94660a89711b7449d3574e103885659a9c3dd31360e852c6fb059b57c60577`.
  이 결과는 초기 적재 routing/alias 범위가 맞음을 지지하지만 갱신 이후까지
  증명하지 않는다. 새 fixture들은 frozen production source와 별도 해시로 기록됐다.
- 빌드 전 이전에 옮겨 둔 종료된 테스트 실행 파일3개만 정리했다. HTTP 종료 후
  target/CACHEDIR.TAG 확인과 `cargo +nightly clean --profile dev`로 재생성 가능한
  dev 캐시6222파일/3.7GiB를 정리해 root 여유3.6GB를 확보했다. release 후보와
  v0.6.0 baseline의 해시, frozen source manifest, 이전 로그는 모두 보존했다.
- 다음 즉시 실행은 이1fa59b13 후보의 **전체 non-plugin 반복 benchmark**다.
  baseline은 최초 v0.6.0으로 고정하며 처리량95% 이상 및 각 시나리오 mean/p95/p99
  105% 이하, 반복/paired/drift 조건을 적용한다. timed 실행 중 build/test/edit를
  병행하지 않는다. 성능이 통과하더라도 갱신17건과 나머지 계획 검증 전에는
  최적화 단위를 완료 처리하지 않는다. 이후 확장 HTTP 범위는 신규 initial18건까지
  합쳐2202건 이상이며 어느 실패 fixture도 빼지 않는다.
- 최신 실제 성능은 여전히 a1b8c3c3 FAIL이다. 정식 수락0/40, ledger 제외0,
  릴리즈 보류를 유지한다. 모든 실행이 종료됐으며 tag/push/publish는 하지 않았다.

#### C05/C06 shard BM25 후보 전체 반복 성능 판정 (2026-09-09)

- 직전 단계는 frozen release와 실제 HTTP 검증을 수행한 progress다. 이번에는
  약속한 전체 non-plugin 반복 benchmark를 실행했고 source/build/test를 병행하지 않았다.
- 명령: `python3 tools/run_core_performance_gate.py
  --baseline-binary target/core-replacement-s01/baseline/steelsearch
  --candidate-binary target/core-replacement-c06/shard-bm25-candidate/artifacts/steelsearch
  --output-dir target/core-replacement-c06/shard-bm25-repeated-full`.
  세션58828은 종료1, 총1097.833초(첫 시작~마지막 종료),6개 subrun은 모두 종료0이다.
  baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/baseline05 순서이며
  12개 topology의 error_count는 모두0이다. 실행 오류 없이 수치 예산을 초과한 FAIL이다.
- candidate SHA-256
  `1fa59b13e4270458d5a154db0e94c342d2c165bd7ff0573581bd8cd219aea23f`,
  v0.6.0 executable SHA-256
  `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`.
  원본 published baseline current.json SHA-256
  `d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788`.
  OpenSearch는 pinned image
  `opensearchproject/opensearch@sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb`다.
- corpus5000/384차원 source,4clients,각 topology60초,3shards,단일/3노드,
  seed13/timeout10초, write15/lexical15/ranking15/facet15/sort_filter10/nested10/refresh5
  전체 비플러그인 mix를 사용했다. Java heap512MiB와 기존 dev durability/resource
  설정을 유지했고 실제 runtime/executable 증거가 검증됐다.
  `execution_inputs_verified=true`, `numeric_budget_passed=false`,
  `acceptance_established=false`다. 종료 후 frozen source manifest 전체 검증도 통과했다.
- result.json SHA-256
  `d9714f354acdcbb85003eac0366d2f2071a5634fbc3fd631dabeb2fd6964d644`,
  plan.json SHA-256
  `5c13111e780bab50e51cd98b7a6eba809162cdf0070ed69bd8db297d9fbf0f6a`.
  모든 원본 summary/report/runtime 증거는 출력 디렉터리에 보존한다.
- published 판정: candidate01은22/44통과(22실패), candidate04는27/44통과(17실패).
  paired 판정: 각각22/44통과(22실패),26/44통과(18실패)다.
  baseline drift는00이44/44통과,05가35/44통과다. 마지막 drift 초과 항목:
  three-node/lexical/p99 +9.93%, three-node/ranking/p99 +6.09%, three-node/facet/p99 +8.59%, three-node/sort_filter/p95 +5.71%, three-node/sort_filter/p99 +5.77%, three-node/nested/p95 +5.77%, three-node/nested/p99 +8.39%, three-node/refresh/p95 +7.40%, three-node/refresh/p99 +5.49%.
  이 변동으로 후보의 큰 회귀를 숨기거나 반복을 골라내지 않는다.

| 실행 파일/반복 | 단일 throughput ops/s | 3노드 throughput ops/s |
| --- | ---: | ---: |
| v0.6.0 published | 743.011070 | 931.370011 |
| v0.6.0 재측정00 | 747.630153 | 919.225760 |
| 1fa59b13 후보01 | 472.676701 (-36.38%) | 729.034341 (-21.72%) |
| pinned OpenSearch02 | 285.874350 | 114.792545 |
| pinned OpenSearch03 | 285.446953 | 112.300467 |
| 1fa59b13 후보04 | 473.896729 (-36.22%) | 734.568117 (-21.13%) |
| v0.6.0 재측정05 | 750.404756 | 901.829686 |

- 아래는 원본 published v0.6.0 대비 후보의 모든 시나리오 지연 변화율이다.
  양수는 악화, 음수는 개선, 별표는 해당 반복에서5% 초과를 뜻한다.
  반올림 표시와 별개로 판정은 원본 정밀값을 사용했다. 서로 상쇄하거나 평균내지 않는다.

| topology/scenario | 01 mean/p95/p99 변화율(%) | 04 mean/p95/p99 변화율(%) |
| --- | ---: | ---: |
| single-node/write | +2.54 / +5.47* / +5.26* | +0.41 / +4.40 / +3.62 |
| single-node/lexical | +10.59* / +13.20* / +76.87* | +10.85* / +16.32* / +71.67* |
| single-node/ranking | +264.19* / +282.08* / +226.03* | +263.82* / +279.75* / +224.35* |
| single-node/facet | -2.45 / -1.49 / +22.25* | -1.85 / -1.35 / +28.48* |
| single-node/sort_filter | +10.62* / +18.37* / +67.34* | +11.62* / +20.81* / +67.69* |
| single-node/nested | -1.22 / +9.95* / +53.41* | -3.57 / +1.98 / +43.77* |
| single-node/refresh | +5.61* / -3.87 / +1.67 | +4.61 / -3.13 / -0.39 |
| three-node/write | +2.42 / +6.65* / +4.18 | +2.35 / +4.33 / +2.28 |
| three-node/lexical | +0.13 / +1.19 / -0.29 | -0.64 / -0.61 / -4.73 |
| three-node/ranking | +151.47* / +242.31* / +214.78* | +148.66* / +232.57* / +212.33* |
| three-node/facet | -0.86 / -3.64 / -0.59 | -0.93 / -1.83 / -3.22 |
| three-node/sort_filter | -1.90 / -0.01 / -6.11 | -2.12 / -0.96 / -6.91 |
| three-node/nested | -1.48 / +0.72 / +5.24* | -4.11 / -3.54 / -6.09 |
| three-node/refresh | +4.08 / +4.65 / +4.50 | +4.09 / +4.45 / +10.43* |

- 단일 ranking mean/p95/p99 원본은6.412787/12.408246/17.360882ms,
  후보01은23.354477/47.408920/56.601142ms,
  후보04는23.331142/47.119986/56.310753ms다.
  3노드 ranking 원본은4.484282/8.035836/11.304207ms,
  후보01은11.276616/27.507820/35.583309ms,
  후보04는11.150494/26.724815/35.306010ms다.
- 이전 a1b8c3c3의 단일 처리량 약297~310에서 현재 약473으로 회복됐지만,
  이는 고정 v0.6.0 예산 통과가 아니다. 기존 CPU 진단과 함께 ranking 전체 후보
  후처리를 다음 최적화 대상으로 유지한다. 정확한 점수/순위/페이지/alias/routing과
  반복 갱신 계약을 검증하면서 불필요한 후처리를 줄여야 한다.
- 갱신 후 점수17건은 미해결이다. 이번 수치 실패만으로 단일 기능의 최적화
  불가능함을 입증하지 않았으므로 ledger 제외0이다. 코드 변경 후 확장 HTTP2202건
  이상과 전체 non-plugin 반복 benchmark를 다시 실행하고, v0.6.0 고정 누적
  처리량95%/각 시나리오 mean/p95/p99 105% 및 반복/drift 조건을 유지한다.
  정식 수락0/40, C02/C05/C06/daemon 미완료, 릴리즈 보류다.
  모든 실행이 종료됐으며 tag/push/publish는 하지 않았다.

#### C05/C06 요청별 검색어 토큰 재사용 (2026-09-09, 검증 중)

- 실제 작업 트리를 확인하고 request-local Bm25Context를 전역 field 통계
  캐시와 분리했다. Match/phrase/prefix 및 MultiMatch의 source BM25 경로에서
  동일 검색어 토큰을 요청 안에서 공유한다. 원문 토큰, 점수, matching 결과를
  전역에 저장하지 않으며 요청 종료 때 검색어 캐시도 해제한다.
- 숫자/불리언/빈 문자열과 잘못된 값, 요청 간 비공유, 반복 토큰 및
  phrase slop/prefix의 직접 계산 대비 정확한 점수 동일성 테스트를 추가했다.
  기존 shard 통계, bool minimum_should_match, 페이지/동점 테스트를 유지한다.
- 최초 전체 engine 테스트는 기존 테스트 호출부 세 곳의 컨텍스트 타입 오류로
  컴파일 실패했다. `target/core-replacement-c06/query-token-cache-engine-full.log`를
  보존하고 호출부 수정 후 `query-token-cache-engine-full-rerun.log`로 재실행했다.
  재실행 종료0, 905+7+4+9=925건 통과, 실패/ignored/filtered0이다.
  컴파일1분25초, 실행14.59/14.86/2.91/0.31초이며 신규2건도 통과했다.
  로그 SHA-256
  `9ccdf647d7cd702f45637b57b29187e1bc3c70e3a9fc18382877907abf84abf7`.
  실행 후 아래 소스 해시가 동일함을 확인했다. 현재 실행 중인 테스트는 없다.
- 구현 파일 SHA-256: lib.rs
  `ce2f84adb5667b236b2295f7cfeba159d74adeec95f539318e009b8c0156ced5`,
  multi_match_field_tests.rs
  `b3b895e03968ec501c7795e1137d999f9f258bd60e0e3348633e341a6f930afd`.
- 이 변경은 native leaf 점수 재사용을 대체하는 최종 해결책이 아니다.
  실제 ranking 쿼리는 multi_match must, phrase slop1 및 term should,
  minimum_should_match1과 range filter를 함께 사용한다. native bool의
  조합별 점수 중복과 phrase 점수 차이를 검증하지 않고 전체 점수를 재사용하지 않는다.
- 완료 전 별도 source/build 디렉터리의 frozen 후보로 HTTP2202건 이상,
  전체 non-plugin 반복 benchmark를 실행해야 한다. 최초 v0.6.0 누적
  처리량95%/시나리오별 mean/p95/p99 105% 및 paired/drift 조건은 불변이다.
  반복 갱신17건과 node/daemon 재검증도 남아 있다. 이 단위는 미완료이며
  수락0/40, 제외0, 릴리즈 보류를 유지한다. 성능 개선 수치는 아직 없다.

#### C05/C06 현재 후보의 ranking CPU 재진단 (2026-09-09)

- 직전 단계는 전체 반복 성능 FAIL과 모든 시나리오 수치를 확보한 progress다.
  이번에는 이전 후보의 CPU 비율을 재사용하지 않고 현재1fa59b13을 재수집했다.
- 명령: `python3 tools/run-core-cpu-diagnostic.py
  --output-dir target/core-replacement-c06/shard-bm25-ranking-cpu
  --binary target/core-replacement-c06/shard-bm25-candidate/artifacts/steelsearch
  --expected-sha256 1fa59b13e4270458d5a154db0e94c342d2c165bd7ff0573581bd8cd219aea23f
  --operation ranking --profile cpu --cpu-frequency-hz 199 --topology single-node`.
  세션34503 종료0, perf/matrix 종료0, lost samples0, 실행 전후 binary 해시 동일.
  5000문서/4clients/ranking100/45초 workload 중20초 cpu-clock DWARF를 수집했다.
  관측22.072345초에 server CPU41.85초, generator CPU10.35초다.
  프로파일링 중 다른 build/test/edit는 실행하지 않았다.
- 전체 캡처의 inclusive 비율은 score_document_query_with_bm25_context56.62%,
  source_text_tokens22.05%다. 이 분모에는 Python 부하 생성기가 포함된다.
  단순 --pid 필터만 적용한 보고서도 기본 absolute 분모를 유지하므로 서버 전용
  상대 비율로 혼동하지 않는다.
- `perf report --pid 487565 --percentage relative --sort=symbol`로 서버 표본만
  분모로 삼은 보고서를 별도로 보존했다. inclusive 비율은 문서별 점수 계산70.77%,
  text BM2549.79%, multi_match BM2540.25%, source 토큰화27.56%다.
  self 비율은 tokenizer iterator11.56%, source 필드 조회9.13%, memcmp8.42%,
  mi_free4.95%, match BM254.84%, 소문자 변환4.74%다.
  inclusive 호출 경로 비율은 중첩되며 합산할 수 없다. off-CPU 및 HTTP 지연의
  원인 비율이나 개선 가능 속도의 직접 추정치도 아니다.
- 출력 디렉터리의 diagnostic.json SHA-256
  `6f241b6fd046e3013ee86734c7549cbf3e837f7a2d9caa9d56ee2518ea6bf755`,
  perf.data SHA-256
  `78f44ca1957c94068a66b8944b5c8390d89815e8666b6af6f353ffbc93f4a793`.
  server-self-relative.txt SHA-256
  `67c1084a72b02d10bb8f54f055aea9ddbaa5cf816b03083b53c9304104aa09c0`,
  server-children-relative.txt SHA-256
  `9c15b43d7667322f4ec269eb75f08b3aa8d8b0582b23be18617522cf8366c172`.
- 다음 구현은 정규화된 native leaf 점수와 source 점수가 일치하는 조건에서
  중복 source 점수 평가를 줄이는 것이다. query 옵션/field mapping/분석기 조건과
  score 비기여 filter를 구분하고, 미검증 형태는 기존 정확성 경로를 유지한다.
  기능 지원 범위를 축소하거나 전체 guard를 무조건 제거하지 않는다.
  후보 순서가 정해진 뒤 점수만 바꾸지 않으며 shard/routing/alias 범위와 동점,
  전체/중간/범위 밖 페이지를 검증한다. source 캐시 추가만으로 해결됐다고 가정하지 않는다.
- 각 최적화 단위 완료 전에 확장 HTTP2202건 이상과 별도 frozen release의
  **전체 non-plugin 반복 benchmark**를 실행한다. 최초 v0.6.0 누적 처리량95% 이상,
  각 시나리오 mean/p95/p99 105% 이하 및 반복/paired/drift 조건을 유지한다.
  갱신 후 점수17건과 daemon 검증도 여전히 미완료다. 현재 진단은 성능 통과나
  단일 기능의 최적화 불가 증거가 아니며, 정식 수락0/40·ledger 제외0·릴리즈 보류다.
  모든 실행이 종료됐으며 tag/push/publish는 하지 않았다.

#### C05/C06 query token cache 고정 빌드 및 전체 검증 (2026-09-09, FAIL)

- 직전 턴은 요청별 토큰 재사용 구현과 engine925건 통과로 progress였다.
  이번 턴은 같은 소스를 고정 빌드하고 HTTP 및 전체 반복 성능 증거를 추가했다.
- 고정 소스/빌드/실행 파일:
  `target/core-replacement-c06/query-token-cache-candidate/{source,build,artifacts/steelsearch}`.
  빌드 전후 및 성능 실행 후 root crates와 고정 crates가 같고 source manifest 검사가 통과했다.
  Cargo.toml/lock 차이는 앞선 고정 후보와 같은 vendored tantivy-fst patch뿐이다.
  baseline 빌드 디렉터리와 캐시를 공유하지 않았다.
- 빌드 명령은 RUSTFLAGS=-Awarnings, CARGO_BUILD_JOBS=2, CARGO_INCREMENTAL=0,
  위 build를 CARGO_TARGET_DIR로 지정한
  `cargo +nightly build --release --locked --manifest-path target/core-replacement-c06/query-token-cache-candidate/source/Cargo.toml -p os-node --features standalone-runtime --bin steelsearch`다.
  종료0, 7분47초. candidate-build.log SHA-256
  `db6b0c2fb2272036f7b53a3c0a746d590fac8c2d9fe6cff86c4c20fe7a9d52ae`.
  source.sha256의 SHA-256
  `d41f74898350cd60d68198605b6034c26560e25b21d6f0325faa3769ff6cab76`.
  실행 파일 SHA-256
  `b5a2579a47fdc4a1b53b7711e3e7a2b33d3e6717d94218733565cc820116ffb7`.
- HTTP: `target/core-replacement-c06/query-token-cache-release-live/execution.json`,
  SHA-256 `4bba83684c07d84d94859a5f2d86d4981341043e1624c8963b47bbc364f0c5d3`.
  기존 run-live.py에 위 candidate-binary, --count-probe 및 기존 추가 fixture22개와
  search-bm25-routing-initial-compat.json을 함께 지정했다. 실행 JSON의26개
  command 배열이 실제 전체 fixture 목록을 기록한다.
  OpenSearch3.7.0-SNAPSHOT, 2185통과/17실패/skip0, count probe=true, 종료1.
  binary_unchanged/fixtures_unchanged=true. 반복 갱신17건은 그대로 남고
  초기 적재18건은 통과했다. 이번 캐시가 이 점수 차이를 해결했다고 주장하지 않는다.
- 디스크 여유를 위해 HTTP 종료 후 root Cargo dev 캐시만 공식 cargo clean으로
  정리했다(1033files/1.5GiB 출력, dev-cache-clean.log). 기준 바이너리/공개 보고서,
  고정 소스/실행 파일, 이전 실패 로그는 보존했다. 측정 중에는 정리/빌드/테스트/편집하지 않았다.
- 성능 명령:
  `python3 tools/run_core_performance_gate.py --baseline-binary target/core-replacement-s01/baseline/steelsearch --candidate-binary target/core-replacement-c06/query-token-cache-candidate/artifacts/steelsearch --output-dir target/core-replacement-c06/query-token-cache-repeated-full`.
  5000docs/384차원 source/4clients/60초, 3shards, replica0/1,
  write15/lexical15/ranking15/facet15/sort_filter10/nested10/refresh5,
  seed13/timeout10, dev durability sync0/deferred native writes1,
  Java512MiB 및 기존 고정 OpenSearch2.19 이미지 설정을 유지했다.
  이는 운영 보안/내구성 프로파일 합격 증거가 아니다.
- 전체 elapsed1098.934초, 6개 하위 실행 종료0, 12개 토폴로지 error_count0.
  실행기 최종 종료1, execution_inputs_verified=true, numeric_budget_passed=false,
  acceptance_established=false다. 실제 runtime evidence는 각 summary에 있으며
  숫자/무결성 검사 통과와 전체 enforcement 수락을 혼동하지 않는다.
  result.json SHA-256
  `6222e3254eb1175d4efe0a9d2416ea212448ec5db3c81c73ec7d281cd8e0d953`;
  plan.json SHA-256
  `eb82c06667a402723de1495ec4c64182a15cd838728435374d1b95c640c27174`.
- 공개 v0.6.0 대비 후보01은21/44통과·23실패, 후보04는20/44통과·24실패다.
  paired는 각각23/44통과·21실패,19/44통과·25실패다.
  baseline00 drift는43/44통과(single-node/write/p99 +5.054673%),
  baseline05는44/44통과다. 후보 ranking의 큰 회귀는 이 변동으로 면제하지 않는다.

처리량 ops/s 원시 보고서에서 생성한 표시값:

| 실행 | 단일 노드 | 3노드 |
| --- | ---: | ---: |
| 공개 v0.6.0 | 743.011070 | 931.370011 |
| 00-baseline | 744.817944 | 936.724032 |
| 01-candidate | 474.695311 | 744.003717 |
| 02-opensearch | 283.142061 | 111.550207 |
| 03-opensearch | 287.807086 | 114.854341 |
| 04-candidate | 473.970509 | 733.786397 |
| 05-baseline | 746.569278 | 935.025632 |

후보01/04의 공개 v0.6.0 대비 처리량 변화는 단일 -36.111946%/-36.209496%,
3노드 -20.117278%/-21.214298%다. 고정 OpenSearch 대비 처리량 배율은
단일1.676527x/1.646834x, 3노드6.669676x/6.388843x다.
이 전체 처리량 배율로 느린 개별 시나리오를 숨기지 않는다.

아래 표는 result.json metrics에서 생성한 **공개 v0.6.0 대비 지연 변화율(%)**이다.
각 셀은 mean / p95 / p99 순서, 양수는 악화이며 모든14개 시나리오를 포함한다.
반올림 전 원시 값으로 판정하고 percentile을 반복 간 평균 내지 않았다.

| 시나리오 | 후보01 | 후보04 |
| --- | ---: | ---: |
| single-node/write | +3.043 / +8.512 / +5.421 | +3.950 / +9.241 / +9.785 |
| single-node/lexical | +12.701 / +21.230 / +69.323 | +12.731 / +19.117 / +65.841 |
| single-node/ranking | +261.822 / +288.613 / +223.769 | +259.698 / +280.237 / +221.917 |
| single-node/facet | -4.437 / -5.186 / +32.879 | -2.476 / -0.328 / +26.785 |
| single-node/sort_filter | +10.789 / +19.152 / +71.619 | +10.315 / +17.268 / +65.075 |
| single-node/nested | -2.571 / +3.256 / +31.914 | -1.753 / +3.853 / +54.218 |
| single-node/refresh | +8.191 / +2.736 / +5.055 | +8.076 / +1.014 / +3.112 |
| three-node/write | +0.623 / +5.057 / +2.453 | +3.914 / +8.774 / +5.149 |
| three-node/lexical | -1.687 / -2.042 / -10.646 | -0.761 / +0.484 / -2.367 |
| three-node/ranking | +141.957 / +229.401 / +211.660 | +145.570 / +234.550 / +216.255 |
| three-node/facet | -1.731 / -3.298 / -1.365 | +0.431 / -0.946 / -0.594 |
| three-node/sort_filter | -1.849 / -0.644 / -0.955 | -2.384 / +0.574 / -5.760 |
| three-node/nested | -3.835 / -3.347 / +4.725 | -3.168 / -2.073 / -7.400 |
| three-node/refresh | +4.197 / +5.647 / +6.094 | +6.045 / +7.343 / +11.031 |

동일 실행의 **고정 OpenSearch 대비 지연 변화율(%)**도 누락 없이 기록한다.
각 셀은 mean / p95 / p99 순서이며 음수는 후보가 빠르다.
단일 ranking은 평균뿐 아니라 p95/p99도 OpenSearch보다 느리다.

| 시나리오 | 후보01 / OpenSearch02 | 후보04 / OpenSearch03 |
| --- | ---: | ---: |
| single-node/write | -77.729 / -72.120 / -75.766 | -77.216 / -72.446 / -76.879 |
| single-node/lexical | -52.793 / -41.177 / -14.533 | -52.341 / -41.071 / -23.113 |
| single-node/ranking | +85.582 / +113.165 / +55.065 | +85.240 / +99.859 / +48.344 |
| single-node/facet | -40.744 / -36.048 / -23.358 | -39.346 / -34.644 / -30.561 |
| single-node/sort_filter | -58.191 / -50.597 / -32.201 | -59.757 / -54.301 / -46.060 |
| single-node/nested | -41.836 / -37.850 / -26.518 | -40.708 / -35.276 / -1.449 |
| single-node/refresh | -84.570 / -86.361 / -87.624 | -83.585 / -85.549 / -87.912 |
| three-node/write | -90.551 / -91.115 / -92.312 | -89.926 / -90.751 / -93.148 |
| three-node/lexical | -86.022 / -87.853 / -90.035 | -85.493 / -87.620 / -87.855 |
| three-node/ranking | -66.190 / -63.920 / -72.058 | -65.750 / -64.057 / -73.965 |
| three-node/facet | -84.531 / -86.625 / -88.709 | -83.801 / -86.453 / -87.152 |
| three-node/sort_filter | -89.587 / -91.483 / -91.364 | -89.220 / -91.406 / -91.508 |
| three-node/nested | -84.599 / -86.797 / -89.568 | -84.068 / -86.904 / -90.800 |
| three-node/refresh | -93.069 / -93.213 / -94.116 | -92.478 / -92.472 / -93.786 |

- 결론: 검색어 토큰 캐시만으로 회귀가 해소되지 않았다. 이전 후보와의
  비동시 실행 수치 차이를 캐시의 확정적 인과 효과로 해석하지 않는다.
  다음 구현은 BM25 점수와 matching이 입증된 native leaf를 source bool 평가에서
  재사용해 문서 원문 재분석을 줄이는 것이다. 전체 native bool 점수를 그대로
  사용하지 않으며 phrase/slop, minimum_should_match, boost, 분석기/파서,
  shard/routing/alias 및 top-k 이전 점수 계약을 보존해야 한다.
- 반복 갱신17건의 Lucene 통계/삭제 문서/merge 경계 원인도 별도 입증이 필요하다.
  다음 구현 후 engine/node/daemon과 확장 HTTP2202건 이상을 검증하고,
  별도 고정 빌드로 **전체 non-plugin 반복 benchmark**를 다시 실행한다.
  최초 v0.6.0 누적 처리량95%, 각 mean/p95/p99 105% 기준은 재설정하지 않는다.
- 현재 단일 기능의 >=5% 인과 손실 및 최적화 불가 증거는 없다.
  제외 ledger에 추정 원인을 등록하거나 미구현 기능을 완료로 세지 않는다.
  수락0/40, 제외0, 릴리즈 보류다. 모든 실행이 종료됐으며 tag/push/publish하지 않았다.

#### C05/C06 역색인 기반 source BM25 재사용 (2026-09-09, 성능 검증 전)

- 사용자의 진행률 보고 후 계속 지시에 따라 위 전체 성능 실패를 보고하고,
  원문 재토큰화를 줄이는 실제 구현을 이어갔다. 지원 API/기능은 제외하지 않았다.
- native 최종 점수를 그대로 재사용하면 source 점수와 f32 연산 순서 차이로
  동점 순서가 달라질 수 있다. 새 native_bm25::source_ordered_term_scores는
  역색인의 term frequency와 fieldnorm만 읽고 기존 source BM25 수식,
  검색어 순서 및 반복 검색어 합산을 유지한다. 삭제된 문서는 건너뛴다.
  QueryParser 구문이나 bool minimum_should_match 조합 점수를 재사용하지 않는다.
- source 후보 평가 시작 시 Match 및 BestFields/MostFields MultiMatch의
  적격 field/query 점수를 준비하고 요청 컨텍스트에 shard/id별로 저장한다.
  Bool must/should를 순회하되 nested/phrase 등 미검증 절은 기존 경로다.
  결과를 자르기 전에 기존 bool/phrase/filter/boost 및 페이지 정렬을 그대로 실행한다.
  같은 ID가 다른 shard에 있는 경우를 섞지 않으며 선택된 shard의 점수만 준비한다.
- 준비된 shard의 점수 map에 ID가 없으면 해당 leaf는 매칭하지 않는다.
  준비하지 않은 shard/field/query는 source 계산으로 돌아간다. ID 주소 캐시가
  완전하지 않은 shard도 부분 map을 채택하지 않고 source 계산을 유지한다.
- 현재 적격 조건은 dotted/multi-field 경로가 아닌 기본 Text 필드이며,
  해당 shard의 전체 source 필드가 ASCII이고 모든 token 길이가40byte 미만인 경우다.
  Tantivy 기본 RemoveLongFilter(40)와 source tokenizer의 차이를 숨기지 않는다.
  Unicode/긴 token/다중 필드 경로는 기능 거부 없이 기존 점수 계산을 사용한다.
  적격 flag는 기존 refreshed_seq_no 기반 field 통계 캐시에 포함해 갱신한다.
- MAX_PREPARED_SOURCE_BM25_SCORES=16384로 요청별 저장 점수와 임시 segment
  배열에 필요한 문서 슬롯을 제한한다. 상한을 초과하면 점수/후보를 잘라내지 않고
  기존 source 평가로 돌아간다. 큰 corpus의 성능 개선까지 입증한 것은 아니다.
- 검증: 단일/3shard, 배열 필드, 검색어 반복/순서/대문자/OR 문자열/매칭 없음,
  BestFields/MostFields, field boost 및 query boost, phrase/slop1, should 최소1의
  source 직접 계산과3200개 문서 점수를 f32 bit 단위로 비교했다.
  ASCII token39/40byte, 비ASCII, 캐시 상한 시 fallback, 삭제/merge 및 이전 reader
  유지 검증을 포함한다. 기존288개 페이지/정렬/선택 shard 비교도 완화하지 않았다.
- 엔진 전체 테스트는
  `env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 cargo +nightly test --locked --config profile.dev.package.os-engine-tantivy.debug=0 -p os-engine-tantivy`로 실행했다.
  최종 `target/core-replacement-c06/postings-bm25-boundaries-engine-full.log` 종료0,
  907+7+4+9=927통과/실패0/ignored0/filtered0. 컴파일1분22초,
  실행14.83/14.75/3.11/0.32초. 로그 SHA-256
  `65588c30945004647d6559393f6edb0077851f3fa36d32575878646c12d608cb`.
- 단계별 앞선 실행도 보존한다. postings-bm25-engine-full.log는926통과이며
  SHA-256 `387655dda6ce1c688a7520d36664c7e1281ab2ce3dcdafe42fa599816f24e162`,
  상한 추가 후 postings-bm25-bounded-engine-full.log는927통과이며
  SHA-256 `074d3e7da6d6139f172e0e055e24e1ca78566351f2dd145b427da64e583fe9fb`다.
  최종 경계 테스트까지 반영한 현재 소스 검증은 위 boundaries 로그를 사용한다.
- 최종 테스트 전후 소스 SHA-256 동일:
  lib.rs `359b2ce90c80b02af293625d81a4b94720f9688ddbf981eabbc37305d1ee6d13`,
  native_bm25.rs `dbafa9ca22a83099974a1e2c53915384f65e6ba71169c522d4effd1629ebc8ed`,
  multi_match_field_tests.rs `a33f7bbaa15f841dd53f27bca026731b45766881f296393bdf502a5ce90d7fac`.
  git diff --check도 통과했다. 현재 빌드/테스트/성능 세션은 모두 종료됐다.
- 다음은 **이 소스의 별도 frozen release 빌드 → HTTP2202건 이상 → 전체 non-plugin
  반복 benchmark**다. 최초 v0.6.0 대비 누적 처리량95% 이상과 각 mean/p95/p99
  105% 이하, paired/drift 규칙은 유지한다. 초과하면 최적화 후 전체 재실행한다.
  node/daemon 재검증 및 반복 갱신17건의 OpenSearch 통계 차이도 미완료다.
  이 구현의 속도 개선 수치는 아직 없으며 단위 완료/수락 처리하지 않는다.
  전체 수락0/40, ledger 제외0, 릴리즈 보류다.

#### C05/C06 postings 고정 후보 전체 검증 (2026-09-09, FAIL)

- 앞 절의 927건 통과 소스를 독립 source/build 디렉터리에서 release 빌드했다.
  경로: target/core-replacement-c06/postings-bm25-candidate.
  artifacts/steelsearch SHA-256:
  ec16945467e0b047736a2e8b510e56dd48d2087e786d9224470b8fbbe53345a4.
  source.sha256 파일 해시:
  5c1330f0350b3b617295d8d914d4274bc8e349940b49fff31083546500bca09a.
  candidate-build.log 해시:
  ac41835714226a94661e3f50c3f97978a936d23e472214a951b7b81f379b08fc.
  빌드 종료0, 7분48초. 원본 기준 실행 파일과 공개 증거는 변경하지 않았다.
- HTTP: target/core-replacement-c06/postings-bm25-release-live/execution.json.
  26회 하위 실행, 2202건 중2185통과/17실패/skip0, count probe 성공.
  실행 파일/fixture 불변 검증 통과. 기능 참조는 OpenSearch3.7.0-SNAPSHOT이다.
  반복 갱신 routing18건 중17건 실패, 초기 적재 routing18건 전부 통과.
  이 suite에서 이전 후보 대비 추가 실패는 없지만 미해결 실패를 면제하지 않는다.
  execution.json SHA-256:
  5e74cf061d0e32beaa2c3dac75e6f21aa418442c690ffcc991678560ee67618e.
- 전체 non-plugin 반복 실행:
  target/core-replacement-c06/postings-bm25-repeated-full.
  baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/baseline05 순서,
  6개 하위 실행 종료0, 12개 토폴로지 error_count0, 총1095.163초.
  실행 입력 검증 true, numeric_budget_passed=false, acceptance=false, runner 종료1.
  result.json SHA-256:
  4814837b80d437fd0acd63350cf5c2c8ecc85a4b54c15ca526e0108a8b627282.
  plan.json SHA-256:
  9e4b2abc84ceeed22de2222d0d42702a16f458e60dc7aa5b08051df5cff73f1f.
- 기존 전체 suite 설정을 유지했다: 5000문서/384 source values, 4clients/60초,
  3shards, replicas0/1, seed13, timeout10, write15/lexical15/ranking15/facet15/
  sort_filter10/nested10/refresh5, 개발 sync0/deferred native writes1, Java512MiB.
  속도 참조는 pinned OpenSearch2.19 이미지이며 기능 참조와 다르다:
  opensearchproject/opensearch@sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb.
  운영 보안/내구성 합격이나 runner의 미검증 요구사항 해소를 주장하지 않는다.
- 공개 v0.6.0 대비44지표 중 후보01은21통과23실패, 후보04는19통과25실패.
  fresh paired는25통과19실패 /19통과25실패.
  기준00은41통과3실패: 단일 refresh/p99 +5.405617%,
  3노드 ranking/p99 +7.875109%, nested/p99 +9.312464%.
  기준05는44통과0실패. 후보의 큰 손실을 drift로 무효화하지 않는다.

| 실행 | 단일 처리량 ops/s | 3노드 처리량 ops/s |
| --- | ---: | ---: |
| 공개 v0.6.0 | 743.011070 | 931.370011 |
| baseline00 | 749.126849 | 920.873286 |
| candidate01 ec169454 | 469.750801 | 731.268497 |
| OpenSearch02 | 287.491615 | 114.697602 |
| OpenSearch03 | 286.872927 | 112.203784 |
| candidate04 ec169454 | 466.568012 | 726.912970 |
| baseline05 | 747.364612 | 920.145827 |

처리량 누적 변화는 단일 -36.777415%/-37.205779%, 3노드 -21.484642%/-21.952290%.
OpenSearch 대비 처리량 비율은 단일1.633963x/1.626393x, 3노드6.375621x/6.478507x다.
처리량 우위가 지연 실패를 상쇄하지 않는다. 아래 표는 result.json에서 계산한
모든 시나리오의 지연 변화율(%, mean/p95/p99)이며 양수는 악화다.

| v0.6.0 대비 시나리오 | candidate01 | candidate04 |
| --- | --- | --- |
| single-node/write | +1.750 / +5.059 / +2.163 | +3.307 / +7.753 / +10.382 |
| single-node/lexical | +11.403 / +16.183 / +74.346 | +12.156 / +17.354 / +60.097 |
| single-node/ranking | +270.758 / +297.333 / +236.506 | +271.770 / +296.221 / +236.799 |
| single-node/facet | -5.386 / -3.858 / +23.624 | -1.320 / +1.702 / +29.433 |
| single-node/sort_filter | +10.988 / +21.720 / +63.775 | +11.713 / +18.711 / +84.584 |
| single-node/nested | +0.305 / +10.024 / +49.605 | -1.851 / +5.801 / +40.366 |
| single-node/refresh | +6.118 / +0.497 / +2.425 | +5.556 / -0.657 / +0.227 |
| three-node/write | +3.002 / +7.101 / +3.903 | +3.599 / +7.258 / +4.559 |
| three-node/lexical | -0.675 / +0.932 / -1.274 | +1.361 / +3.412 / +3.870 |
| three-node/ranking | +148.612 / +249.759 / +227.670 | +149.055 / +247.763 / +220.581 |
| three-node/facet | -0.835 / -2.957 / -4.340 | -0.352 / -1.142 / +2.578 |
| three-node/sort_filter | -2.026 / +0.327 / -8.402 | -0.828 / +2.032 / -0.467 |
| three-node/nested | -2.352 / -1.523 / +3.936 | -2.281 / -1.307 / +5.452 |
| three-node/refresh | +6.587 / +7.135 / +13.230 | +7.176 / +13.202 / +15.171 |

| OpenSearch 대비 시나리오 | candidate01 / OpenSearch02 | candidate04 / OpenSearch03 |
| --- | --- | --- |
| single-node/write | -77.707 / -73.354 / -77.696 | -77.455 / -72.242 / -74.450 |
| single-node/lexical | -52.698 / -42.565 / -16.953 | -52.680 / -42.024 / -30.256 |
| single-node/ranking | +92.940 / +124.279 / +66.470 | +94.113 / +119.990 / +58.094 |
| single-node/facet | -40.141 / -33.630 / -30.712 | -37.640 / -29.314 / -23.711 |
| single-node/sort_filter | -57.912 / -49.160 / -34.741 | -57.864 / -50.154 / -22.318 |
| single-node/nested | -39.941 / -28.669 / -12.739 | -39.851 / -31.649 / -12.921 |
| single-node/refresh | -84.566 / -86.167 / -87.510 | -84.817 / -86.757 / -88.029 |
| three-node/write | -89.938 / -90.563 / -92.517 | -90.279 / -90.908 / -92.420 |
| three-node/lexical | -85.819 / -87.573 / -90.212 | -85.702 / -87.978 / -88.705 |
| three-node/ranking | -63.640 / -58.029 / -65.186 | -65.701 / -62.354 / -73.246 |
| three-node/facet | -84.443 / -87.327 / -90.989 | -84.207 / -86.471 / -88.165 |
| three-node/sort_filter | -89.073 / -90.533 / -92.290 | -89.292 / -91.510 / -91.685 |
| three-node/nested | -84.242 / -86.787 / -88.145 | -84.373 / -87.882 / -88.295 |
| three-node/refresh | -92.550 / -92.861 / -92.959 | -92.610 / -91.987 / -92.728 |

#### C05/C06 준비 비용과 phrase 중복 평가 최적화 (2026-09-09, 전체 성능 대기)

- 위 모든 측정 종료 후 동일 ec169454 실행 파일의 ranking CPU 진단을 실행했다.
  경로 target/core-replacement-c06/postings-bm25-ranking-cpu.
  ranking100/45초, cpu-clock199Hz/DWARF20초의 진단이며 전체 게이트 대체가 아니다.
  perf/matrix 종료0, lost samples0, 실행 파일 전후 동일.
  서버 PID713892에 --percentage relative를 적용해 부하 생성기 샘플을 분모에서 제외했다.
- inclusive CPU: score_document_query_with_bm25_context51.64%,
  prepare_source_bm25_matches15.33%, source_ordered_term_scores10.57%,
  document_matches_query15.89%, source_text_tokens13.79%, phrase matcher10.54%.
  중첩되는 호출 경로이므로 합산하거나 HTTP 지연 감소율로 해석하지 않는다.
  postings 경로가 비활성이라는 가설과 달리 실제 실행된다.
- diagnostic.json SHA-256:
  a8690bd00a8039305b53281775d6a0237569ad3705415f3ee183bc56cc388837.
  perf.data SHA-256:
  9fefc3d6816156dcfb818d2d1c6123125292e700bb429a3e099096c03b4211ea.
  server-children-relative.txt SHA-256:
  c09632554a28d4c48291b123921133b34d303ec997d7958ae372492a27cc6738.
  server-self-relative.txt SHA-256:
  26c5002cb70ba89812f98ce7dc87f5f7af957f4c34c607c73749a24b40125e08.
- 측정/프로파일 종료 후 다음 작업 트리 수정을 반영했다.
  IDF를 문서마다 재계산하지 않고 query/field/shard별 사전 계산한다.
  f32 값, query 순서와 중복 term 누적 순서는 유지한다.
  요청별 native 점수의 내부 ID 조회를 HashMap으로 변경했다.
  순위는 이 map의 순회 순서로 결정하지 않으며 16384 상한도 유지한다.
- 기본 Text 필드의 기본 분석기, 비어 있지 않은 문자열 검색어이고
  zero_terms_query=all이 아닌 phrase/prefix에 한해 source BM25가 미매칭을
  확정하면 generic matcher를 재호출하지 않는다. 명시 분석기/keyword 필드/
  빈 검색어/비문자열/zero_terms_query=all은 기존 fallback을 유지한다.
  native phrase 점수로 대체하지 않으며 bool must/should 밖으로 적용을 확대하지 않는다.
- 새 회귀 테스트는 phrase/prefix, Text/Keyword, slop0/1/3, 기본/keyword 분석기,
  zero_terms 설정, Unicode/배열/null/숫자/bool을 포함해3456개 문서 점수를
  기존 source 계산과 f32 bit 단위로 비교한다. 기존3200개 postings 점수와
  288개 페이지 비교 및 fallback 상한 검증도 유지한다.
- 엔진 전체 실행은 앞 절과 같은 nightly/locked/jobs2/debug0 명령으로 종료0.
  908+7+4+9=928통과, 실패/ignored/filtered0. 테스트 실행14.20/14.40/2.99/0.32초.
  target/core-replacement-c06/postings-bm25-preparation-engine-full.log SHA-256:
  50816e3768f2db3550649357e493a0f5790aa94f492360a9c5e1d43ae107d55f.
  최신 작업 트리 해시:
  lib.rs c7e0ab7ee34cb2a0cb4e6a688df5dda663e7a6f3623a8847bda596a455072585,
  native_bm25.rs 62dba40aeabf76a823ac114619646af8790a6c6abaf4b87c53b123f1eade0657,
  multi_match_field_tests.rs d8efc6c50ca562a7d9f6354c88babd3e38ffcfaead79410d0160fc597419aa30.
- 다음 단위 검증: 이 소스의 독립 frozen release 빌드와 실행 파일 출처를 고정하고,
  HTTP2202건 이상 및 전체 non-plugin 반복 benchmark를 실행한다.
  최초 v0.6.0의 처리량95% 이상, 각 mean/p95/p99 105% 이하를 개별 적용하며
  fresh paired/drift도 확인한다. 초과하면 최적화 후 전체 suite를 재실행한다.
  focused/engine 테스트만으로 완료 처리하지 않는다. node/daemon 및 반복 갱신
  routing17건 진단도 남았다. 최신 추가 수정의 성능은 아직 측정하지 않았다.
- 수락0/40, ledger 제외0, 릴리즈 보류. 단일 기능의 최적화 불가능한 손실을
  입증하지 않았으므로 기능을 제외하거나 5% 예산을 재설정하지 않는다.

#### C05/C06 BM25 준비 최적화 고정 후보 검증 (2026-09-09, FAIL)

- 앞 절의 928건 통과 소스를 target/core-replacement-c06/bm25-preparation-candidate/
  source에 고정하고, 별도 build에서 nightly release/locked/jobs2/incremental0/
  RUSTFLAGS=-Awarnings, os-node standalone-runtime steelsearch를 빌드했다.
  빌드 종료0, 7분48초. 측정 후 root crates와 frozen crates의 diff도 동일했다.
- 빌드 공간 확보를 위해 Cargo CACHEDIR.TAG를 확인한 이전 query-token-cache/
  postings-bm25 후보의 build만 cargo clean --release --target-dir로 정리했다.
  각1790파일/681.8MiB 및682.0MiB 캐시였다. 두 후보의 artifacts 실행 파일,
  소스, HTTP/성능/CPU 원시 자료, 최초 v0.6.0 및 공개 기준 자료는 보존했다.
  앞선 실행 파일2개와 v0.6.0/공개 current.json 해시도 기존 값과 일치했다.
- artifacts/steelsearch SHA-256:
  23230fa877b656536f83092e0d8639d1caf75d057296adca99404adce3114959.
  source.sha256 파일 해시:
  e2cb0f714399d8785d179d9bce20d0d4bc02048facb5a3a9b88d0829662b0a35.
  candidate-build.log 해시:
  844994144c47e58cd58bcd9262bfe52ea95e717a13e5ddcf7261767c4753523e.
  소스 manifest 검증 종료0. Cargo 설정의 vendored tantivy-fst patch는 이전과 동일하다.
- HTTP: target/core-replacement-c06/bm25-preparation-release-live/execution.json.
  26회 하위 실행, 2202건 중2185통과/17실패/skip0. count probe 성공,
  binary_unchanged/fixtures_unchanged=true. 기능 참조3.7.0-SNAPSHOT.
  초기 적재 routing18건은 모두 통과, 반복 갱신18건은1통과17실패다.
  기존 결과 대비 이 suite의 새 실패는 관측되지 않았다. 전체 실행 종료1.
  execution.json SHA-256:
  3ce067d87c4b9442c741b62c88ff10773fc75ba9524097656d3b98ee22ebc9ed.
- 전체 non-plugin 반복: target/core-replacement-c06/bm25-preparation-repeated-full.
  baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/baseline05,
  6회 하위 실행 종료0, 12개 토폴로지 오류0, 총1096.012초.
  앞 절과 동일한 전체 workload/durability/security/resource 설정 및 pinned
  OpenSearch2.19 이미지를 사용했다. 실제 입력 검증 true,
  numeric_budget_passed=false, acceptance=false, 최종 종료1.
  result.json SHA-256:
  f0b90ef5eebe46023eeaf5456b930ab14be5b4a015d9b329225689bb3ebe22ef.
  plan.json SHA-256:
  b4236ecede15e564f3a9783cda33619995a9f1ef338a990d8b408f3f07bdf3e0.
- 공개 v0.6.0 대비44지표 중 후보01은16통과28실패, 후보04는21통과23실패.
  fresh paired는22통과22실패 /25통과19실패.
  기준 재측정은 두 번 모두44통과0실패다. 큰 후보 손실을 drift로 면제하지 않는다.
  개발 설정의 짧은 실행이며 전체 운영 승인이나 미검증 요구사항 해소는 아니다.

| 실행 | 단일 처리량 ops/s | 3노드 처리량 ops/s |
| --- | ---: | ---: |
| 공개 v0.6.0 | 743.011070 | 931.370011 |
| baseline00 | 735.808544 | 931.367827 |
| candidate01 23230fa8 | 480.628679 | 726.814266 |
| OpenSearch02 | 286.147619 | 108.006320 |
| baseline05 | 744.676952 | 914.284410 |
| candidate04 23230fa8 | 479.628644 | 741.977995 |
| OpenSearch03 | 284.660420 | 107.356009 |

처리량 누적 감소는 단일35.313389%/35.447981%, 3노드21.962887%/20.334777%.
OpenSearch 대비 비율은 단일1.679653x/1.684915x, 3노드6.729368x/6.911378x다.
아래는 result.json의 전체 시나리오 지연 변화율(%, mean/p95/p99), 양수는 악화다.
다른 지표의 개선으로 실패 지표를 상쇄하지 않는다.

| v0.6.0 대비 시나리오 | candidate01 | candidate04 |
| --- | --- | --- |
| single-node/write | +3.307 / +8.356 / +5.968 | +2.673 / +6.865 / +9.080 |
| single-node/lexical | +10.948 / +13.212 / +64.704 | +12.006 / +15.045 / +66.923 |
| single-node/ranking | +251.307 / +288.400 / +227.469 | +252.703 / +283.944 / +220.480 |
| single-node/facet | -3.213 / -2.912 / +24.312 | -3.131 / -0.645 / +31.867 |
| single-node/sort_filter | +11.759 / +20.434 / +65.144 | +11.722 / +16.624 / +70.198 |
| single-node/nested | -1.747 / +4.994 / +38.829 | -2.366 / +0.597 / +32.126 |
| single-node/refresh | +6.030 / -0.573 / +2.957 | +6.688 / -3.256 / +1.531 |
| three-node/write | +7.376 / +11.701 / +10.360 | +3.888 / +6.517 / +5.432 |
| three-node/lexical | +2.283 / +2.062 / +5.119 | +0.120 / +0.312 / +0.424 |
| three-node/ranking | +137.964 / +240.181 / +218.700 | +136.195 / +234.189 / +230.092 |
| three-node/facet | +2.162 / -0.555 / -0.020 | -0.321 / -2.075 / -0.100 |
| three-node/sort_filter | +2.360 / +5.282 / +5.452 | -0.987 / +1.311 / -1.420 |
| three-node/nested | -0.089 / +1.248 / -4.391 | -1.782 / -0.283 / +1.788 |
| three-node/refresh | +9.555 / +9.119 / +10.007 | +4.959 / +7.028 / +5.368 |

| OpenSearch 대비 시나리오 | candidate01 / OpenSearch02 | candidate04 / OpenSearch03 |
| --- | --- | --- |
| single-node/write | -77.599 / -73.180 / -78.763 | -77.722 / -72.997 / -76.643 |
| single-node/lexical | -53.170 / -42.924 / -17.780 | -52.915 / -41.740 / -21.057 |
| single-node/ranking | +83.432 / +109.051 / +55.864 | +80.619 / +105.656 / +42.740 |
| single-node/facet | -39.809 / -34.191 / -31.755 | -40.108 / -33.379 / -28.743 |
| single-node/sort_filter | -58.132 / -51.843 / -32.799 | -59.109 / -51.959 / -36.002 |
| single-node/nested | -39.835 / -31.805 / -20.321 | -42.584 / -37.983 / -30.311 |
| single-node/refresh | -84.598 / -86.288 / -88.525 | -84.099 / -86.642 / -87.488 |
| three-node/write | -90.325 / -91.543 / -93.547 | -90.590 / -91.534 / -94.023 |
| three-node/lexical | -85.703 / -88.428 / -88.387 | -86.589 / -88.791 / -89.369 |
| three-node/ranking | -67.840 / -65.438 / -69.381 | -67.547 / -64.544 / -66.402 |
| three-node/facet | -84.548 / -87.670 / -89.539 | -85.155 / -87.221 / -89.483 |
| three-node/sort_filter | -89.236 / -90.792 / -91.031 | -90.107 / -91.890 / -92.220 |
| three-node/nested | -84.579 / -88.419 / -90.579 | -84.429 / -86.566 / -88.063 |
| three-node/refresh | -92.988 / -92.494 / -94.364 | -93.239 / -93.343 / -93.766 |

- 전체 측정 종료 후 같은23230fa8 후보의 CPU 진단도 완료했다.
  target/core-replacement-c06/bm25-preparation-ranking-cpu.
  ranking100/45초 중20초 cpu-clock199Hz/DWARF, 서버 PID810510만 상대 분모로 분석.
  perf/matrix 종료0, lost samples0, binary 전후 동일. 관측21.861762초,
  서버 CPU36.82초, 생성기12.80초. 진단이며 전체 벤치마크 대체가 아니다.
- inclusive CPU: 문서별 점수 평가48.61%, source 필드 조회14.11%(self9.86%),
  MultiMatch14.90%, phrase11.83%, 준비11.86%, postings2.84%,
  generic matching6.20%, source 토큰화7.08%, routing hash4.14%.
  HashMap reserve/rehash도2.96%다. inclusive 비율은 중첩되며 합산할 수 없다.
  ec169454 진단보다 postings/generic 경로 비율은 작지만, 샘플 분모와 부하가
  달라졌으므로 비율 차이를 확정적인 속도 개선률로 해석하지 않는다.
- diagnostic.json SHA-256:
  726c08bebdc3bb073aef2bfdd59f269cdaef5cd5ae8c8db26334480dfb85d348.
  perf.data SHA-256:
  c2877f0014c742fd29cb959466ea4a0003ebf8aef687f85261ba825838ddaa01.
  server-children-relative.txt SHA-256:
  d851c03d296ad7dcc01a276caf164cb94dd64ed09ae3b915b7b56aba9f6106cb.
  server-self-relative.txt SHA-256:
  d032db9c041f542746999268145f44c31c9d6ae6caed18be08d6bfdcd1929b6b.
- 다음 구현 단위는 반복 source 필드 조회 및 후보별 점수 평가 비용 축소다.
  먼저 실제 ranking query와 호출 경로를 연결하고, top-k 이전 bool/phrase/slop/
  boost/분석기/배열/갱신/routing 계약을 유지하는 재사용 지점을 찾는다.
  준비 map의 재할당도 측정된 보조 비용이므로 초기 용량 예약을 검토한다.
  변경 후 engine/node/daemon, HTTP2202건 이상 및 **전체 non-plugin 반복 benchmark**를
  실행하고 최초 v0.6.0 처리량95%/각 mean,p95,p99 105% 및 paired/drift를 확인한다.
  초과하면 최적화 후 전체를 재실행하며, 집중 진단만으로 단위를 완료하지 않는다.
- 반복 갱신17건의 통계 원인은 아직 가설이며 별도 explain/삭제/merge 경계 입증이
  필요하다. 단일 기능의 최적화 불가능한 >=5% 인과 손실도 입증되지 않았다.
  수락0/40, ledger 제외0, 릴리즈 보류. 전체 범위와 최초 기준선을 유지한다.
  이번 빌드/HTTP/전체 성능/CPU 세션은 모두 종료됐고 tag/push/publish하지 않았다.

#### C05/C06 문서별 점수 임시 할당 축소 (2026-09-09, 전체 성능 대기)

- 이전 turn은23230fa8 전체 HTTP/성능/CPU 검증과 기록을 완료한 진행이었다.
  그 결과를 현재 코드 및 tools/run-http-load-baseline.py의 ranking 요청과 연결했다.
  실제 요청은 title^2/message BestFields must, message phrase/slop1 및 service term
  should, latency range filter, minimum_should_match1이다. workload는 변경하지 않았다.
- 준비 점수 map은 postings 결과 개수로 HashMap::with_capacity를 호출한 뒤 채운다.
  ID 주소가 하나라도 누락되면 해당 shard map 전체를 버리는 기존 fallback 계약과
  16384 점수 상한은 유지한다. 부분 map을 검색 결과로 채택하지 않는다.
- MultiMatch는 최대2필드일 때 점수 배열을 스택에 두고, 더 많은 필드는 기존 Vec
  경로를 유지한다. 필드 매칭 순서, boost, 빈 결과, MostFields의 입력 순서 합산,
  BestFields/Phrase/Prefix의 내림차순 정렬과 remainder/tie-breaker 연산은 동일하다.
  2필드 제한은 최적화 경계이지 지원 기능 제외가 아니다.
- Bool should는 문서별 Option 점수 Vec를 만들지 않고 개수와 점수를 순서대로
  누적한다. must 합산과 should 합산은 분리하고 마지막에 더해 f32 반올림을 유지한다.
  로컬 nightly core/src/iter/traits/accum.rs에서 f32::Sum의 초기값 -0.0 및
  왼쪽부터의 fold를 확인하고 그대로 사용했다. minimum_should_match 및 오류 전파는 유지한다.
- compact_ranking_scores_preserve_heap_accumulation_bits 회귀 테스트를 추가했다.
  3shards/9문서, null/매칭 없음/중복 필드/boost0/필드0~4개,
  BestFields/MostFields/Phrase/Prefix, tie0/0.3/1/2, 검색어5종을 기존 heap 수식과
  4320개 점수의 f32 bit 단위로 비교한다. Bool은 must boost0/0.5/1e8,
  should0~8개, 최소 매칭0~개수+1을 포함해1458개 점수를 이전 Vec 합산식과 비교한다.
  기존 prepared postings/phrase/page 및 메모리 상한 테스트도 유지한다.
- 전체 engine 명령:
  `env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 cargo +nightly test --locked --config profile.dev.package.os-engine-tantivy.debug=0 -p os-engine-tantivy`.
  target/core-replacement-c06/compact-ranking-engine-full.log 종료0,
  909+7+4+9=929통과/실패0/ignored0/filtered0, 실행14.66/14.56/2.89/0.39초.
  로그 SHA-256:
  fd7da4e8cad453d7b54493d87588c403c467573818700ae895db80f982ba5956.
  lib.rs SHA-256:
  3dd702a93119dae303f70ea624315753748d899f8533d8e6acae992449ca4784.
  multi_match_field_tests.rs SHA-256:
  efea3d0fe361162683d1fd316f1d646348c9b81f15130ff04ae05791ea2c4953.
- 다음은 이 소스의 독립 frozen release 빌드, HTTP2202건 이상 및 **전체 non-plugin
  반복 benchmark**다. 최초 v0.6.0 대비 누적 처리량95% 이상, 각 mean/p95/p99 105%
  이하를 개별 적용하고 fresh paired/drift를 확인한다. 초과하면 최적화 후 전체를
  재실행한다. node/daemon 및 반복 갱신17건의 통계 원인 진단도 미완료다.
  focused/engine 테스트를 전체 성능 대체로 사용하거나 완료로 세지 않는다.
- 성능 개선은 아직 미측정이다. 수락0/40, ledger 제외0, 릴리즈 보류이며
  단일 기능의 최적화 불가능한 손실은 입증하지 않았다. 전체 범위와 최초 기준선은 유지한다.

#### C05/C06 compact ranking 후보와 갱신 점수 설명 (2026-09-09)

- engine929건 통과 소스 해시를 재확인한 뒤 독립 source/build를 생성했다.
  target/core-replacement-c06/compact-ranking-candidate의 frozen crates는 root와
  diff 동일, source.sha256 전체 검증 종료0이다. 빌드 전 실행 중인 cargo/rustc/
  steelsearch/java가 없음을 확인했다. 원본 release 및 기존 측정 자료는 보존했다.
- 이전 bm25-preparation-candidate/build의 Cargo cache tag를 확인하고
  cargo clean --release --target-dir로1790파일/682.0MiB 재생성 가능 캐시만 정리했다.
  이전 artifacts/steelsearch와 source/HTTP/전체 성능/CPU 증거는 삭제하지 않았다.
- nightly release/locked/jobs2/incremental0/RUSTFLAGS=-Awarnings,
  os-node standalone-runtime steelsearch 빌드 종료0, 7분59초.
  artifacts/steelsearch SHA-256:
  f4b7e31ef03aa3dd29ea74a47a73669944b1ce9f142b2ad5857755ce3bc8325e.
  candidate-build.log SHA-256:
  ab5a78d501af4f59407962a02ce7517ea150de5bbfcd5f5806659f1737e0005d.
  source.sha256 파일 해시:
  8586abbebb76392b894c6cc95b1990db81eafcb886563721e5e8e9f92d9d8e0c.
- HTTP: target/core-replacement-c06/compact-ranking-release-live/execution.json.
  기존26회 하위 실행, 2202건 중2185통과17실패/skip0, count probe 성공.
  binary_unchanged/fixtures_unchanged=true, 참조 OpenSearch3.7.0-SNAPSHOT.
  반복 갱신 routing18건 중17실패, 초기 적재18건 전부 통과.
  기존 suite 대비 새 실패는 관측되지 않았으나 미해결 실패를 면제하지 않는다.
  실행 종료1, execution.json SHA-256:
  546bff554528e7b858d1362377b0b7c5dd2ddb4102f0753b48626fcee933ff85.
- 빌드 중 별도 기능 진단을 기존23230fa8 후보로 실행했다. 이는 성능 측정이 아니며
  f4b7e31e 후보의 검증으로 재사용하지 않는다. 원래 routing fixture는 변경하지 않았다.
  target/core-replacement-c06/routing-score-explain-diagnostic.json은 원래18개
  반복 갱신 사례에 진단 이름과 검색 explain:true만 추가한 사본이다.
  fixture SHA-256:
  1bdefda610f886e439f5011a9198f25c45d273702a1873a42944612b599f407c.
- 진단 실행은 target/core-replacement-c06/routing-score-explain-live.
  진단18건1통과17실패, helper의 기존 core1180/nested160+160은 통과,
  합계1518건 중1501통과17실패/skip0, 4회 하위 실행, 종료1.
  binary_unchanged/fixtures_unchanged=true. 이 범위는 확장2202건 전체를 대체하지 않는다.
  execution.json SHA-256:
  4fca60195aa4469b2dcfa3b8021dffa4b78dcec8791d670897a48b6b039fdd86.
  routing-score-explain-diagnostic-report.json SHA-256:
  62a3b4a18735eb533f82989aea934372eff45461ba9ea9ae8e2b62e81a84741e.
- OpenSearch raw _explanation에서 동일 shard의 alpha term 빈도 n과 field 문서 수 N이
  초기3/3, 다음 갱신6/6, 그다음9/9로 증가하고 마지막 사례54/54가 됨을 확인했다.
  평균 필드 길이는36.333332로 유지됐다. 문서a의 초기 점수0.09378171,
  다음 갱신0.05204748, 그다음0.036024284이며 후보는0.09378170967102051을 유지했다.
  두 번째 사례의 참조 IDF0.074107975와 TF0.70231956은 이 점수 감소를 설명한다.
  따라서 페이지 from만의 문제로 볼 수 없고 갱신 이력에 따른 통계 수명 차이가 확인된다.
- 현재 source 통계는 refreshed_values의 살아 있는 문서만 계산한다.
  native append_documents는 신규 문서를 추가하지만 non-append refresh의 Full 계획은
  현재 documents로 TantivySearchState::build_from_documents를 호출해 새 reader를 만든다.
  실제 reader의 삭제/merge 전후 통계 계약까지 검증하기 전에는 단순 누적 카운터로
  OpenSearch 숫자를 흉내 내거나 실패17건을 해결했다고 표시하지 않는다.
  merge 후 수렴 및 갱신 실패/이전 snapshot의 통계 격리 검증은 아직 필요하다.
- 다음 필수 단계는 f4b7e31e 후보의 **전체 non-plugin 반복 benchmark**다.
  최초 v0.6.0 고정 실행 파일과 공개 증거를 기준으로 처리량95% 이상,
  모든 mean/p95/p99 105% 이하를 개별 적용하고 paired/drift 및 실제 입력을 확인한다.
  초과하면 최적화 후 전체를 다시 실행하며 engine/HTTP/진단만으로 단위를 완료하지 않는다.
  이후 reader 갱신 통계 수정도 engine/node/daemon, HTTP2202건 이상, 전체 non-plugin
  반복 benchmark를 거쳐야 한다. 기존 실패나 성능 한도를 임의로 제외하지 않는다.
- 빌드/HTTP/별도 진단은 모두 종료됐다. 전체 성능은 미측정이며 수락0/40,
  ledger 제외0, 릴리즈 보류. tag/push/publish하지 않았고 최초 기준선과 전체 범위는 유지한다.

#### C05/C06 compact ranking 전체 반복 성능 판정 (2026-09-09, FAIL)

- 앞 절의 실제 f4b7e31e 실행 파일, 최초 v0.6.0 실행 파일 db244133 및 공개
  current.json d2fdabfa 해시를 재확인했다. root/frozen crates의 diff 동일,
  실행 전 cargo/rustc/steelsearch/java 프로세스 없음도 확인했다.
- target/core-replacement-c06/compact-ranking-repeated-full에 기존 전체 non-plugin
  suite를 실행했다. baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/
  baseline05의6회 하위 실행 종료0, 12개 토폴로지 error_count 합계0,
  총1099.032초. 실제 입력 검증 true, numeric_budget_passed=false,
  acceptance=false, runner 종료1. timed 실행 중 빌드/편집/다른 테스트는 하지 않았다.
- 기존5000문서/384source values/4clients/60초/seed13,3shards 및 replicas0/1,
  write15/lexical15/ranking15/facet15/sort_filter10/nested10/refresh5,
  개발 sync0/deferred native writes1/Java512MiB 설정을 유지했다.
  pinned OpenSearch2.19 참조도 동일하며 기능 참조3.7.0-SNAPSHOT과 혼동하지 않는다.
  운영 프로파일 합격이나 미검증 요구사항 해소로 해석하지 않는다.
- result.json SHA-256:
  c626965a8536c0be56427c0f89fad620a557b648e87452438c4c58a23e21d12d.
  plan.json SHA-256:
  f4ba9c60fbb2ff034d20a4eaadc8485190c1cc29de161abcf0116535ec02f59f.
- 공개 v0.6.0 대비44지표 중 후보01은23통과21실패, 후보04는25통과19실패.
  fresh paired는22통과22실패 /27통과17실패.
  기준00은43통과1실패(single refresh/p99 +6.154257%),
  기준05는42통과2실패(three facet/p99 +5.323187%, nested/p99 +6.026276%).
  이 변동을 큰 후보 회귀의 면제 사유로 사용하지 않는다.

| 실행 | 단일 처리량 ops/s | 3노드 처리량 ops/s |
| --- | ---: | ---: |
| 공개 v0.6.0 | 743.011070 | 931.370011 |
| baseline00 | 744.122594 | 916.514823 |
| candidate01 f4b7e31e | 470.303161 | 738.363992 |
| OpenSearch02 | 287.650393 | 111.347184 |
| baseline05 | 740.611489 | 909.134954 |
| candidate04 f4b7e31e | 486.743293 | 750.311923 |
| OpenSearch03 | 282.902171 | 114.617601 |

최초 v0.6.0 대비 처리량 감소는 단일36.703075%/34.490439%,
3노드20.722808%/19.439974%다. OpenSearch 대비 처리량 비율은
단일1.634982x/1.720536x, 3노드6.631187x/6.546219x다.
아래는 result.json에서 계산한 전체 지연 변화율(%, mean/p95/p99)이며 양수는 악화다.
처리량이나 다른 시나리오의 개선으로 실패를 상쇄하지 않는다.

| v0.6.0 대비 시나리오 | candidate01 | candidate04 |
| --- | --- | --- |
| single-node/write | +1.037 / +4.675 / +3.834 | +1.722 / +7.168 / +7.778 |
| single-node/lexical | +15.903 / +24.744 / +94.793 | +11.592 / +12.828 / +71.355 |
| single-node/ranking | +265.363 / +305.691 / +240.042 | +245.235 / +283.423 / +222.134 |
| single-node/facet | -3.622 / -3.235 / +29.606 | -4.238 / -4.324 / +28.482 |
| single-node/sort_filter | +12.557 / +20.607 / +78.111 | +9.828 / +19.613 / +44.304 |
| single-node/nested | +0.540 / +9.649 / +56.611 | -2.941 / +2.783 / +38.871 |
| single-node/refresh | +4.146 / -5.861 / +3.449 | +4.172 / -5.728 / -2.397 |
| three-node/write | +4.438 / +6.982 / +4.652 | +2.756 / +4.519 / +1.374 |
| three-node/lexical | -0.616 / -0.164 / -4.744 | -0.793 / -2.508 / -5.284 |
| three-node/ranking | +136.713 / +247.280 / +224.737 | +130.022 / +231.514 / +207.676 |
| three-node/facet | +0.687 / -0.611 / +0.863 | -0.418 / -2.863 / -1.025 |
| three-node/sort_filter | -0.186 / +2.360 / -7.905 | +0.242 / +1.532 / +0.189 |
| three-node/nested | -1.861 / -2.072 / +2.819 | -1.860 / -0.554 / +1.062 |
| three-node/refresh | +7.605 / +7.986 / +11.686 | +3.909 / +4.528 / +6.852 |

| OpenSearch 대비 시나리오 | candidate01 / OpenSearch02 | candidate04 / OpenSearch03 |
| --- | --- | --- |
| single-node/write | -77.913 / -73.309 / -77.257 | -78.091 / -73.275 / -77.149 |
| single-node/lexical | -51.294 / -37.868 / -7.492 | -54.095 / -44.516 / -21.194 |
| single-node/ranking | +89.038 / +117.095 / +57.954 | +76.899 / +97.705 / +47.816 |
| single-node/facet | -38.871 / -34.909 / -27.912 | -40.630 / -36.775 / -32.913 |
| single-node/sort_filter | -57.864 / -51.814 / -33.640 | -59.788 / -53.739 / -48.166 |
| single-node/nested | -39.290 / -29.188 / -3.385 | -42.434 / -37.408 / -21.854 |
| single-node/refresh | -84.599 / -87.667 / -88.225 | -84.720 / -87.214 / -89.371 |
| three-node/write | -89.813 / -90.487 / -91.951 | -89.943 / -90.682 / -92.590 |
| three-node/lexical | -86.332 / -88.980 / -90.365 | -85.512 / -88.704 / -89.688 |
| three-node/ranking | -66.657 / -59.872 / -66.980 | -67.562 / -63.514 / -72.032 |
| three-node/facet | -84.552 / -87.011 / -88.482 | -83.874 / -86.563 / -88.642 |
| three-node/sort_filter | -89.338 / -91.101 / -92.259 | -88.930 / -91.566 / -91.798 |
| three-node/nested | -84.527 / -87.940 / -89.344 | -84.358 / -86.785 / -90.084 |
| three-node/refresh | -92.818 / -92.840 / -93.361 | -92.781 / -93.574 / -93.412 |

- 전체 측정 종료 후 같은 실행 파일을 CPU 진단했다.
  target/core-replacement-c06/compact-ranking-cpu,
  ranking100/45초 중20초 cpu-clock199Hz/DWARF, 서버 PID906851,
  생성기906871. 서버 PID에 --percentage relative를 적용해 분모를 분리했다.
  관측21.900886초, 서버 CPU35.95초/생성기13.09초,
  perf/matrix 종료0, lost samples0, 실행 파일 전후 동일.
- inclusive CPU: 문서별 점수 평가48.66%, source 필드 조회14.55%(self10.04%),
  MultiMatch13.66%, phrase12.71%, 준비9.29%, postings3.22%,
  generic matching5.70%, source 토큰화7.27%, routing hash4.15%.
  호출 경로는 중첩되므로 합산하거나 과거 진단 대비 비율 차이를 속도 개선률로
  해석하지 않는다. 작은 임시 할당 제거만으로 성능 예산을 회복하지 못했다.
- diagnostic.json SHA-256:
  80e746bfea52e58c80300b9c1a598d7e52daf00cd0d26dd1a27365be962d0dcd.
  perf.data SHA-256:
  9032a8ab367e244dbe990fc66672e138c715ad4064659e8edf99310a6769ac3a.
  server-children-relative.txt SHA-256:
  e9514695c00501414bdc058a18044722e33cd8e211a585f2358bb7e0f5f7a0d8.
  server-self-relative.txt SHA-256:
  57210f5af8d41711d0c1a3761033231fd7ff172357c8e2cf70dc7095fb8ef050.
- 다음은 탈락 후보의 비싼 점수 평가를 줄일 수 있는 bool 평가 경계 검토다.
  filter/should 최소 매칭을 확정할 수 있는 경우에도 점수 누적 순서, boost,
  오류 발생 여부와 오류 우선순위, nested/routing/배열 의미를 보존해야 한다.
  기본 query 구조를 일반적으로 검증하며 benchmark 쿼리 문자열이나 문서 수로 분기하지 않는다.
  원래 source 후처리 guard를 무조건 제거하거나 검증하지 않은 native 점수로 대체하지 않는다.
- 별도로 반복 갱신17건의 reader/통계 수명 차이 및 merge 후 수렴 검증도 유지한다.
  다음 구현 단위마다 engine/node/daemon, HTTP2202건 이상 및 **전체 non-plugin
  반복 benchmark**를 실행하고 최초 v0.6.0 처리량95%/각 mean,p95,p99 105%와
  fresh paired/drift를 확인한다. 초과 시 최적화 후 전체 재실행하며 단위 완료를 막는다.
- 새 단일 기능의 최적화 불가능한 >=5% 인과 손실은 아직 입증하지 않았다.
  수락0/40, ledger 제외0, 릴리즈 보류. 측정/CPU 세션은 모두 종료됐고
  코드/기준선/기능 범위를 바꾸거나 tag/push/publish하지 않았다.

#### C05/C06 오류 없는 bool의 must 평가 지연 (2026-09-09, 전체 성능 대기)

- 직전 전체 성능/CPU 검증은 실제 실패 근거와 다음 조치 대상을 남긴 진행이었다.
  현재 점수 함수의 오류 반환 경로를 읽고, 오류가 없는 것으로 확인한 query tree에만
  bool 평가 순서 최적화를 적용했다. 전체 기능 범위와 source 의미는 유지한다.
- prepare_source_bm25_matches에서 must가 존재하고 filter/must_not 또는 양의
  minimum_should_match로 탈락할 수 있는 bool의 적격성을 요청별로 기록한다.
  source_score_query_is_infallible은 현재 점수 함수의 MatchAll/None, 텍스트 match
  계열, 일반 Term/Terms/Exists, 비Text range 및 재귀 bool만 허용한다.
  다중 필드 keyword의 값 변환과 Text range 분석기 조회는 오류를 낼 수 있어 제외한다.
  vector/nested/wrapper 등 확인하지 않은 종류도 기존 순서를 유지한다.
  이 제외는 평가 순서 최적화의 적격 경계이며 지원 기능 ledger 제외가 아니다.
- 적격 bool은 filter, must_not, should를 기존 내부 순서대로 계산하고 최소 매칭
  조건에 실패하면 must 점수를 계산하지 않는다. 통과하면 must를 원래 순서로 계산한다.
  must 점수와 should 점수는 여전히 각각 별도로 누적한 뒤 더해 f32 반올림을 유지한다.
  최소 매칭 실패, 0점 보정, boost 및 top-k 이전 평가 계약은 변경하지 않는다.
  적격성 기록이 없는 호출은 원래 must-first 경로다. 오류가 가능한 tree의 평가 순서와
  오류 가시성을 바꾸지 않는다. 향후 점수 함수에 오류 경로를 추가하면 이 분류도 재검토해야 한다.
- 회귀 테스트 deferred_bool_must_preserves_scores_and_error_visibility 추가:
  1/3shards, 12문서, 배열/null, field/query boost, 최소 should0~3,
  range 선택성, must_not 및 중첩 bool 조합2304개 점수를 기존 must-first 경로와
  f32 bit 단위로 비교한다. 다중 필드 keyword의 잘못된 query 값이 must에서 오류를
  내야 하는 경우 및 먼저 탈락한 must 뒤 filter/should의 오류를 숨겨야 하는 경우도 비교한다.
  Text range는 비적격임을 확인하며, MatchNone filter에서 탈락한 후보가 must의 검색어
  토큰 캐시를 채우지 않음을 검사해 실제 점수 계산 생략을 확인한다.
- 전체 engine 명령:
  `env RUSTFLAGS=-Awarnings CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0 cargo +nightly test --locked --config profile.dev.package.os-engine-tantivy.debug=0 -p os-engine-tantivy`.
  target/core-replacement-c06/deferred-bool-engine-full.log 종료0,
  910+7+4+9=930통과/실패0/ignored0/filtered0, 실행14.99/14.32/2.98/0.33초.
  로그 SHA-256:
  86bb0f7893783855aa44a28f48cdf6262e0a6ecb12eaed73be68b182e39d9d99.
  lib.rs SHA-256:
  e0c452eb7dcb7d20fccbfcd36cfda239c446fc56dad7e59dc618eb19725ab20b.
  multi_match_field_tests.rs SHA-256:
  edf952d938d03fba37519faadd6987ce876c338dc73838bc96d0155e65083724.
- 다음은 이 소스의 별도 frozen release 빌드, HTTP2202건 이상 및 **전체 non-plugin
  반복 benchmark**다. 최초 v0.6.0 처리량95% 이상, 각 mean/p95/p99 105% 이하를
  개별 적용하고 fresh paired/drift 및 실제 입력을 확인한다. 초과하면 최적화 후
  전체를 재실행하며 focused/engine 테스트만으로 완료 처리하지 않는다.
  node/daemon 재검증과 반복 갱신17건의 reader/통계 수명 수정도 미완료다.
- 전체 성능은 아직 미측정이다. 수락0/40, ledger 제외0, 릴리즈 보류다.
  실행 중인 테스트는 없으며 tag/push/publish하지 않았다. 최초 기준선과 전체 범위를 유지한다.

#### C05/C06 deferred bool 고정 후보 및 merge 경계 진단 (2026-09-09)

- engine930건의 root 소스 해시를 재확인하고 독립 source/build를 생성했다.
  target/core-replacement-c06/deferred-bool-candidate의 frozen crates는 root와
  diff 동일, source.sha256 전체 검증 종료0이다. 빌드 전 cargo/rustc/steelsearch/java
  실행 없음도 확인했다. 이전 compact-ranking-candidate/build의 Cargo cache tag를
  확인한 뒤 cargo clean --release --target-dir로1790파일/681.9MiB 캐시만 정리했다.
  이전 artifacts 실행 파일, source, HTTP/성능/CPU 및 최초 기준 자료는 보존했다.
- nightly release/locked/jobs2/incremental0/RUSTFLAGS=-Awarnings,
  os-node standalone-runtime steelsearch 빌드 종료0, 8분02초.
  artifacts/steelsearch SHA-256:
  2d50548e03d59d7da5ecf6427150bc51f0e8b5da879667d25907503f8d4bdb2b.
  source.sha256 파일 해시:
  40e9042dd32e020273326b6a2e3e4e39a4ea5fe9873fac4fa46f52297ba55ba8.
  candidate-build.log SHA-256:
  78abadbcce9cbf248ad1bcdefa2c2ab423be1f2fa1559911a10293af2b31ee33.
- HTTP: target/core-replacement-c06/deferred-bool-release-live/execution.json.
  기존26회 하위 실행, 2202건 중2185통과17실패/skip0, count probe 성공,
  binary_unchanged/fixtures_unchanged=true, 기능 참조3.7.0-SNAPSHOT.
  반복 갱신 routing18건은1통과17실패, 초기 적재18건은 모두 통과다.
  이 suite에서 평가 순서 변경에 따른 새 실패는 관측되지 않았다. 전체 실행 종료1.
  execution.json SHA-256:
  0035978829429eb7f8859cc241fcb93f2ab188a01ca3fa53d95c6f8932997e78.
- 빌드와 병행한 별도 기능 진단은 기존 f4b7e31e 실행 파일을 사용했다.
  target/core-replacement-c06/routing-score-merge-diagnostic.json은 이전 explain
  진단18건을 보존하고, 쓰기 없이 forcemerge?max_num_segments=1 및 refresh 후
  같은18개 검색을 다시 수행한다. 원래 HTTP suite fixture는 변경하지 않았다.
  fixture SHA-256:
  f55bd63ff2871f8c537561ba5f69a60f5a8bbeab2da36e9a9a625eb115c15c1a.
- target/core-replacement-c06/routing-score-merge-live 진단은36건 중1통과35실패다.
  기존17실패에 merge 후18검색 모두 차이가 유지됐다. helper의 core1180 및
  nested160+160은 통과, 합계1536건 중1501통과35실패/skip0, 종료1.
  binary_unchanged/fixtures_unchanged=true. 이 진단을 새2d50548e 후보의 추가 실패나
  확장2202건 전체 검증으로 혼동하지 않는다. 성능 측정도 아니다.
  execution.json SHA-256:
  da8fdb21c6c6561872391721578b25e0d6a25eb7afe2e364026c9263e95daa4c.
  routing-score-merge-diagnostic-report.json SHA-256:
  b6c8a0e97160893dfc09554f2b68276ffb880878e38ab0b954285487fb507240.
- forcemerge 및 refresh 요청은 양쪽200이었지만 참조 _explanation의 n=N=54는
  유지됐다. merge 후 문서a의 참조 점수0.006413922, 후보0.09378170967102051이며,
  참조 IDF0.009132484, TF0.70231956이다. 따라서 단순히 merge하면 즉시 초기
  통계로 수렴한다는 가정은 이 실행으로 지지되지 않는다.
- 후보 handle_forcemerge_route는 maintenance_shard_counts를 응답할 뿐 실제
  엔진 merge를 호출하지 않는다. HTTP200을 merge 구현의 완료 증거로 사용하지 않는다.
  StoredShard::insert/remove는 이전 문서가 있으면 require_full_refresh를 호출하고,
  현재 문서로 reader를 재구축하는 Full refresh 경로로 연결된다.
- 로컬 OpenSearch InternalEngine.java는 softUpdateDocument(s)를 사용하며,
  SoftDeletesPolicy.java는 safe commit의 local checkpoint, global checkpoint,
  retention operations/lease 및 retention lock에 따라 merge 보존 범위를 결정한다.
  소스 해시:
  InternalEngine.java c1ca3f0adcba5eca7b16885c45034097d4202a934688d718f63457ae9083644e,
  SoftDeletesPolicy.java 3d33b4de582ba3e6919bf4e207e67bc557d8b052a4a63ab42dfaa8b16be7668e.
  이는 보존 정책 진단의 근거이며 해당 Java 소스와 실행 배포물의 완전한 출처 일치나
  이번 실행에서 어떤 checkpoint/lease가 보존을 유발했는지까지 입증한 것은 아니다.
  다음 경계 진단에는 실제 shard checkpoint/segment/보존 상태를 기록해야 한다.
  복구 이력을 강제로 버리거나 안전 조건을 완화해 점수만 맞추지 않는다.
- 다음 필수 단계는2d50548e의 **전체 non-plugin 반복 benchmark**다.
  최초 v0.6.0 처리량95% 이상 및 각 mean/p95/p99 105% 이하를 개별 적용하고
  fresh paired/drift, 동일 실제 workload/durability/security/resource 설정을 검증한다.
  초과하면 최적화 후 전체를 다시 실행하며 engine/HTTP만으로 단위를 완료하지 않는다.
  node/daemon 및 reader/통계 수명 수정도 각각 전체 비플러그인 성능 게이트를 거쳐야 한다.
- 빌드/HTTP/별도 진단은 모두 종료됐다. 새 후보 전체 성능은 미측정이며
  수락0/40, ledger 제외0, 릴리즈 보류다. 최초 기준선과 전체 범위를 유지했고
  tag/push/publish하지 않았다.

#### C05/C06 deferred bool 전체 반복 성능 판정 (2026-09-09, FAIL)

- 앞 절의2d50548e 실행 파일, 최초 v0.6.0 db244133 및 공개 current.json d2fdabfa
  해시를 재확인했다. root/frozen crates diff 동일, 실행 전 cargo/rustc/steelsearch/java
  없음도 확인했다. 모든 timed 실행이 끝날 때까지 편집/빌드/다른 테스트를 하지 않았다.
- target/core-replacement-c06/deferred-bool-repeated-full.
  baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/baseline05 순서,
  6회 하위 실행 종료0, 12개 토폴로지 오류0, 총1098.806초.
  실제 입력 검증 true, numeric_budget_passed=false, acceptance=false, 최종 종료1.
  기존 전체 non-plugin workload/durability/security/resource 설정과 pinned OpenSearch2.19를
  그대로 사용했다. 운영 프로파일 승인이나 미검증 요구사항 해소를 주장하지 않는다.
- result.json SHA-256:
  3d7b2e89d2a97a10f16e68f6f072f38a3ee6197c6c46496e62a3d5d811f1f604.
  plan.json SHA-256:
  b77150a1f03030d2ffe9ff2be2a1558d066556b8d7a0848ea986cedf1b498bd2.
- 공개 v0.6.0 대비44지표 중 후보01은19통과25실패, 후보04는17통과27실패.
  fresh paired는22통과22실패 /23통과21실패.
  기준00은44통과0실패, 기준05는37통과7실패다.
  기준05 실패는 single sort_filter/p99 +7.381931%, refresh/p99 +5.911032%,
  three facet/p95 +6.788805%, facet/p99 +6.018387%, nested/p99 +6.261090%,
  refresh/p95 +6.367187%, refresh/p99 +8.031661%다.
  마지막 기준의 변동을 후보의 큰 손실을 면제하는 근거로 사용하지 않는다.

| 실행 | 단일 처리량 ops/s | 3노드 처리량 ops/s |
| --- | ---: | ---: |
| 공개 v0.6.0 | 743.011070 | 931.370011 |
| baseline00 | 745.984307 | 922.430426 |
| candidate01 2d50548e | 480.153469 | 747.180603 |
| OpenSearch02 | 285.346696 | 113.437050 |
| baseline05 | 741.288433 | 902.180159 |
| candidate04 2d50548e | 480.554701 | 739.039668 |
| OpenSearch03 | 288.162542 | 108.252498 |

처리량 누적 감소는 단일35.377347%/35.323346%, 3노드19.776180%/20.650262%.
OpenSearch 대비 처리량 비율은 단일1.682702x/1.667652x, 3노드6.586742x/6.826999x다.
아래는 result.json에서 계산한 전체 지연 변화율(%, mean/p95/p99), 양수는 악화다.
다른 지표의 개선으로 실패를 상쇄하지 않는다.

| v0.6.0 대비 시나리오 | candidate01 | candidate04 |
| --- | --- | --- |
| single-node/write | +4.807 / +8.254 / +9.157 | +5.271 / +8.493 / +11.349 |
| single-node/lexical | +13.613 / +18.740 / +54.153 | +11.471 / +15.204 / +60.660 |
| single-node/ranking | +246.058 / +280.579 / +220.807 | +246.803 / +286.568 / +226.671 |
| single-node/facet | -2.234 / -1.696 / +29.290 | -1.322 / +0.101 / +37.533 |
| single-node/sort_filter | +14.697 / +20.963 / +76.925 | +12.724 / +26.339 / +61.815 |
| single-node/nested | +0.342 / +6.989 / +36.700 | -0.063 / +10.503 / +48.085 |
| single-node/refresh | +6.375 / +1.406 / +3.807 | +5.832 / -2.689 / -2.818 |
| three-node/write | +4.978 / +7.248 / +6.687 | +6.127 / +10.689 / +6.837 |
| three-node/lexical | +0.757 / -0.701 / -0.029 | +1.458 / +2.176 / -1.834 |
| three-node/ranking | +128.728 / +236.258 / +203.965 | +133.357 / +232.104 / +210.730 |
| three-node/facet | -0.049 / -1.882 / +1.158 | +1.392 / -0.185 / -1.358 |
| three-node/sort_filter | +0.136 / +1.025 / -5.141 | -0.352 / +0.451 / -4.874 |
| three-node/nested | -0.995 / -0.622 / -0.421 | -2.695 / -1.708 / -8.000 |
| three-node/refresh | +5.138 / +6.835 / +16.401 | +7.337 / +7.766 / +9.428 |

| OpenSearch 대비 시나리오 | candidate01 / OpenSearch02 | candidate04 / OpenSearch03 |
| --- | --- | --- |
| single-node/write | -77.234 / -72.773 / -78.186 | -77.379 / -72.964 / -78.322 |
| single-node/lexical | -52.901 / -43.002 / -32.153 | -52.481 / -43.185 / -21.252 |
| single-node/ranking | +77.416 / +100.729 / +44.083 | +80.220 / +111.990 / +61.694 |
| single-node/facet | -38.361 / -33.239 / -28.137 | -37.860 / -30.040 / -18.460 |
| single-node/sort_filter | -57.718 / -50.481 / -34.182 | -57.847 / -49.389 / -36.028 |
| single-node/nested | -40.116 / -34.727 / -19.717 | -40.019 / -29.544 / -15.050 |
| single-node/refresh | -84.269 / -86.176 / -88.239 | -84.066 / -86.752 / -88.847 |
| three-node/write | -89.979 / -90.857 / -91.675 | -90.198 / -90.845 / -92.340 |
| three-node/lexical | -85.593 / -88.496 / -89.831 | -85.871 / -88.593 / -89.375 |
| three-node/ranking | -67.359 / -62.547 / -72.450 | -68.344 / -65.748 / -72.642 |
| three-node/facet | -84.549 / -87.535 / -89.214 | -84.661 / -87.491 / -88.487 |
| three-node/sort_filter | -89.116 / -91.543 / -92.036 | -89.810 / -92.156 / -93.012 |
| three-node/nested | -84.457 / -87.720 / -90.177 | -85.092 / -87.756 / -89.163 |
| three-node/refresh | -92.522 / -92.134 / -91.994 | -93.061 / -92.677 / -93.141 |

- 전체 측정 종료 후 동일 후보를 target/core-replacement-c06/deferred-bool-cpu에서
  CPU 진단했다. ranking100/45초 중20초 cpu-clock199Hz/DWARF,
  서버 PID1002474에 --percentage relative, 생성기1002494와 분모를 분리했다.
  관측21.892729초, 서버 CPU35.18초/생성기13.50초, perf/matrix 종료0,
  lost samples0, 실행 파일 전후 동일. 전체 성능 게이트 대체가 아니다.
- inclusive CPU: 문서별 점수 평가44.51%, source 필드 조회18.38%(self13.12%),
  phrase12.84%, 준비10.69%, source 토큰화7.43%, generic matching6.43%,
  postings3.29%, must 점수 helper3.06%, MultiMatch2.96%, BoolQuery 동등 비교2.88%.
  중첩 비율이므로 합산하지 않는다. 이전 MultiMatch 비중보다 작아졌지만
  서로 다른 진단의 비율 차이를 HTTP 속도 개선률로 해석하지 않는다.
- source-lookup-callers.txt에서 필드 조회의 상위 호출 경로가 bool 점수 평가,
  document_matches_query 및 phrase 점수 평가임을 확인했다.
  symbol 제한 report는 분모가 달라 전체 CPU 비율로 재사용하지 않는다.
- diagnostic.json SHA-256:
  40c8c4b71839fdc9b9860de4803608722f5493980cc5b7228128c10b881ad870.
  perf.data SHA-256:
  cf3037ac044530a12e2e3db10a0a5aef417609264d5858a95c5b301d9d58a973.
  server-children-relative.txt SHA-256:
  000febe1c15eaf2f5dfd6b47f8079c723306a729e14483e5e41a85212a03df1c.
  server-self-relative.txt SHA-256:
  733163b4c8bbfa8752b56762a8925eb9aefa65e08bf19fd2fb0905505015f387.
  source-lookup-callers.txt SHA-256:
  79dc0873272ff4d52283841fe603bc2874a51eaa842c4056b51a6ec26c2adb13.
- 다음 구현 검토는 native 후보 선별에서 이미 판정한 filter의 재검사 비용이다.
  재사용은 native/source의 정확한 동등성이 입증된 filter와 실제 선별된 후보에만 허용한다.
  mapping coercion, 배열/null/missing, 정수2^53/i64 경계, range 포함/제외,
  선택 shard, alias 및 오류 가시성을 비교하고 비적격 조건은 기존 source 검사로 돌아간다.
  Bool should/minimum_should_match나 phrase를 무조건 native 결과로 대체하지 않는다.
  후보 선별 없이 전체 source를 순회한 경로에 선별 완료 표시를 남기지 않는다.
- 변경 후 engine/node/daemon, HTTP2202건 이상 및 **전체 non-plugin 반복 benchmark**를
  실행하고 최초 v0.6.0 처리량95%/각 mean,p95,p99 105%, fresh paired/drift와
  실제 동일 입력을 검증한다. 초과하면 최적화 후 전체 재실행하며 완료를 막는다.
  soft-delete/checkpoint/retention 및 실제 forcemerge 계약 진단도 계속 필요하다.
- 단일 기능의 최적화 불가능한 >=5% 인과 손실은 아직 입증하지 않았다.
  수락0/40, ledger 제외0, 릴리즈 보류. 모든 측정/CPU 세션은 종료됐고,
  이번 검증 중 코드/기준선/기능 범위를 바꾸거나 tag/push/publish하지 않았다.

#### C05/C06 정수 range 경계 계약 및 panic 수정 (2026-09-10, 검증 중)

- native filter 재검사 생략을 구현하기 전에 실제 후보 집합과 source 판정을 비교했다.
  새 `native_integer_range_candidates_match_source_for_exact_values`는 1/3샤드와
  doc_values true/false의4조합에서 각각216개 범위, 총864개 후보 집합을 비교한다.
  단일/양쪽 포함·제외 경계, null/missing/빈 배열/중첩 숫자 배열, 2^53 인접 정수,
  i64 최솟값/최댓값과 인접 값을 포함한다.
- 최초 실행은1통과1실패/910filtered, 종료101이었다.
  Tantivy0.21.1의 range_query_u64_fastfield.rs:121에서 `lt:i64::MIN`의 unsigned
  제외 경계 -1 계산이 panic을 발생시켰다. lower 제외 경계 +1도 gt:i64::MAX에서
  overflow 위험이다. dependency를 수정하지 않고 build_tantivy_range_query의 I64
  분기에서 이 두 빈 범위만 EmptyQuery로 반환한다. 일반 경계 변환/점수는 그대로다.
- `native_integer_range_candidates_still_need_source_guard`의7조건 x1/3샤드가
  내부 경로 차이를 재현했다. u64::MAX source의 wrap, u64::MAX bound의 wrap,
  gt+gte 및 lt+lte 중복 경계, object 배열을 거치는 dotted path는 native true/source false다.
  float source/정수 mapping과 무경계 null은 native false/source true다.
  앞의5조건은 실제 source post-filter 페이지에서 잘못된 후보를 제거하는 것도 확인했다.
  뒤의2조건은 후보 누락을 source 후처리만으로 복구할 수 없다는 위험을 보여준다.
  이 반례들은 OpenSearch live 호환성 인증이나 정상화할 의도적 API 계약이 아니다.
  이를 무조건 native/source 동등한 것으로 취급하는 최적화는 금지한다.
- 수정 후 전체 engine932건(912+7+4+9) 통과, 실패/ignore/filter0, 종료0이다.
  test별16.65/15.30/3.10/0.32초이며, doc-test0건/기존 경고13건을 별도 유지한다.
  최초 실패 증거 target/core-replacement-c06/integer-range-contract-focused.log SHA-256:
  a43823d9a39b0c18c18b42c6694391dbeaf0750af12a2926ecd150b0e766af04.
  전체 로그 target/core-replacement-c06/integer-range-boundary-engine-full.log SHA-256:
  3f9099634ad25347333032176a9e0a8242f47122b9be305d7103daa8bcc4c308.
  root lib.rs SHA-256:
  c55915bdeadef1c653ec7210a4a299f1375baa21bd34aad02b8d0783d154c949.
  multi_match_field_tests.rs SHA-256:
  3bd36b4230d5d42f88c39f283e3967a0c357c4721b2ebfa1273566a1644c43fe.
- 독립 source/build는 target/core-replacement-c06/integer-range-boundary-candidate다.
  crates는 root와 diff 동일, 이전 frozen vendor/lock 조건을 그대로 보존했다.
  source.sha256 manifest SHA-256:
  8b17acc8dce68eaba2ab1f0c9b12be44df49a717ce499875f7c351454a7745dc.
  디스크 확보는 이전 deferred-bool build의 Cargo cache tag를 확인한 뒤
  cargo clean --release --target-dir로1790파일/682.0MiB만 정리했다.
  이전 source/artifacts 및 모든 검증 기록과 최초 v0.6.0 증거는 보존했다.
- 이 정수 경계 수정 단위도 확장 HTTP와 **전체 non-plugin 반복 benchmark**를 마치기
  전에는 완료하지 않는다. 최초 v0.6.0 대비 처리량95% 이상 및 시나리오별 mean/p95/p99
  105% 이하를 각각 적용하고, 실제 입력/실행 파일 해시 및 반복 paired/drift를 검증한다.
  다른 시나리오 개선으로 상쇄하거나 직전 후보로 기준을 재설정하지 않는다.
- 이후 필터 생략 계획: (1) top-level I64/no multi-field의 reader 세대별 source 정확성
  증거를 생성하고 append/full refresh/old-reader 격리를 검증한다. (2) 실제 native 선별이
  수행된 경로에서만, i64 범위의 단일 유효 경계와 source 의미가 같은 필터를 재사용한다.
  float/unsigned overflow/중복 경계/dotted object 배열/무경계는 보수적으로 제외한다.
  selected-shard source 전체 순회 경로에 native 판정 완료 표시를 남기지 않는다.
  각 구현 단위 뒤 전체 benchmark를 실행하며 정확성 guard를 비용 때문에 완화하지 않는다.
- 정수 경계 수정 외 runtime 변경과 필터 생략은 아직 없다. node/daemon 및 반복 갱신
  점수17건도 미완료다. 수락0/40, ledger 제외0, 릴리즈 보류다.

#### C05/C06 정수 경계 후보 전체 검증 결과 (2026-09-10, FAIL)

- 독립 빌드7분48초/종료0, 고정 source manifest 전후 검증0이다.
  artifacts/steelsearch SHA-256:
  439725ca6e346978bea1ca761d3ff7763cdf016d3105b621764b1d76aa1967fe.
  candidate-build.log SHA-256:
  4e073ecf331e992f1b41fe21177a3160edaab718adf66d47638d7b090d1c016b.
  측정 후 root/frozen crates diff도 동일하다.
- HTTP는 target/core-replacement-c06/integer-range-boundary-release-live/execution.json.
  27하위 실행/2214건 중2197통과17실패/skip0, count probe 성공,
  binary_unchanged/fixtures_unchanged=true, 전체 종료1이다.
  새 search-integer-range-extremes-compat.json의12건이3샤드 fast/postings,
  gt MAX/lt MIN 빈 범위와 gte MAX/lte MIN 포함 경계, bool filter/must_not을 통과했다.
  여러 결과의 동점 순서는 명시적인 keyword tie 정렬로 비교했다.
  기능 참조는3.7.0-SNAPSHOT이며 속도 참조2.19와 다르다.
  반복 갱신 routing17실패는 유지됐다. 전반적인 코어 호환성 완료 주장이 아니다.
  execution.json SHA-256:
  a619bc491b249e27e0e8b6f7631899c744e7f23d745151426023cce7cccce6f0.
  새 fixture SHA-256:
  d6c0b43d8db7a3ef196b231a4bfd5d30aaa4be43a62ca478a3bfbe1edea533d9.
- 최초 전체 시도 integer-range-boundary-repeated-full은 기준/후보 실행0 뒤
  OpenSearch3노드 인덱스 생성403으로 중단, 실행기 종료2였다.
  전체6개 중3번째에서 중단됐으므로 부분 성능을 전체 판정으로 사용하지 않는다.
  failure-diagnostics는 global create-index block10과 노드당 약610MB available을 기록했다.
  낮은 용량은 유력 관련 조건이지만, settings filter 응답{}만으로 원인을 확정하지 않는다.
  기존 실행기는 시작 때 clear_opensearch_cluster_blocks를 호출하는 개발 프로파일이며,
  이번에 그 설정을 추가 완화하거나 차단을 반복 해제하는 우회는 하지 않았다.
  최초 result.json SHA-256:
  ae23f91c2b126aafd43b2dc263b066f4ad695cdf724244508fd3c7278d594717.
  failure-diagnostics.json SHA-256:
  048086d67a229416ceff1f37ca43a323d3085ce006cd5ebf48a1ef3bd92a6e69.
- 캐시 정리는 측정 프로세스 종료 후 Cargo cache tag를 확인한 경로에만 실시했다.
  새 candidate build682.0MiB, lock-diagnostic677.3MiB, sort-native-build641.5MiB,
  bench-release1.3GiB, snapshot-release606.9MiB, root dev1.5GiB를 cargo clean으로 정리했다.
  기존3개 release 실행 파일/depfile은 integer-range-boundary-cache-preservation에 보존하고
  원래 release 경로에도 복원했다. root debug examples도 보존했다.
  lock-diagnostic 실행 파일 b8345d2b..., sort-native c53ed756..., bench-release67e8ae6d...
  보존 사본과 정리 전 해시는 일치했다. 최초 기준/새 후보/원래 릴리즈 증거와
  source/로그/실패 자료는 삭제하지 않았다. 재실행 직전 여유5.2GB였다.
- 최종 전체 실행은 integer-range-boundary-repeated-full-after-cache-clean이다.
  baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/baseline05,
  총1097.376초,6하위 실행 종료0,12토폴로지 operation 오류0, 실행기 종료1이다.
  execution_inputs_verified=true, numeric_budget_passed=false, acceptance_established=false.
  최초 v0.6.0 기준 및 원래 workload/security/durability/resource 설정은 변경하지 않았다.
  이 개발 프로파일이 실제 운영 보안/내구성 인증을 뜻하지 않는다.
  result.json SHA-256:
  62661158868f8a62a56a35f5fd9d06afa2ec57ab34c2a54a02a6c061aff7d698.
  plan.json SHA-256:
  7186725a5c1e29a44fae9ac4014ab2d28504f2c3551fcd71ccd5c76ee19e43f1.
- published44지표 중24/27실패, paired22/25실패다. 기준 drift는41/44 및42/44 통과:
  baseline00 single write p99/refresh p99 및 three facet p99,
  baseline05 single refresh p99 및 three ranking p99가 실패했다.
  후보 회귀를 이 변동으로 면제하지 않는다.

| 처리량 ops/s | published v0.6.0 | baseline00 / 05 | candidate01 / 04 | OpenSearch02 / 03 |
| --- | --- | --- | --- | --- |
| single-node | 743.011 | 741.518 / 739.133 | 483.236 / 470.750 | 285.789 / 289.451 |
| three-node | 931.370 | 916.892 / 920.490 | 736.911 / 728.465 | 113.975 / 110.023 |

- 후보 처리량 누적 손실: 단일34.962%/36.643%,3노드20.879%/21.786%.
  OpenSearch 대비 처리량 배수: 단일1.691/1.626,3노드6.466/6.621.
  단일 ranking 평균22.239/23.043ms는 v0.6.0 대비246.793%/259.323% 증가이며,
  OpenSearch 대비로도79.671%/87.660% 증가했다. 총 처리량 우위로 상쇄하지 않는다.
- 아래는 실행기 원시 지표로 생성한 모든14시나리오의 mean/p95/p99 변화율(%)이다.
  지연에서 양수는 악화, 음수는 개선이다. 후보01/04를 평균내거나 좋은 반복만 선택하지 않는다.

| 시나리오 | v0.6.0 대비 01 | v0.6.0 대비 04 | OpenSearch 대비 01/02 | OpenSearch 대비 04/03 |
| --- | --- | --- | --- | --- |
| single-node/write | +2.597 / +6.818 / +10.390 | +4.309 / +9.500 / +6.309 | -77.991 / -72.474 / -77.694 | -77.027 / -71.742 / -75.686 |
| single-node/lexical | +11.877 / +16.868 / +65.987 | +14.988 / +19.388 / +85.795 | -53.297 / -41.522 / -18.396 | -50.987 / -38.802 / -9.588 |
| single-node/ranking | +246.793 / +292.354 / +230.463 | +259.323 / +304.303 / +236.746 | +79.671 / +109.711 / +60.511 | +87.660 / +127.461 / +62.381 |
| single-node/facet | -2.995 / -0.579 / +25.655 | +0.005 / +0.797 / +41.919 | -38.936 / -30.643 / -26.479 | -36.772 / -30.491 / -17.024 |
| single-node/sort_filter | +13.298 / +22.963 / +84.963 | +12.011 / +15.130 / +82.765 | -57.579 / -49.879 / -23.721 | -57.106 / -50.791 / -27.153 |
| single-node/nested | -1.729 / +7.805 / +44.075 | +0.477 / +3.493 / +40.872 | -40.994 / -30.284 / -8.220 | -38.619 / -30.006 / -17.193 |
| single-node/refresh | +4.319 / -3.589 / -0.563 | +5.681 / -3.587 / +0.400 | -84.675 / -87.178 / -88.344 | -84.453 / -87.237 / -87.288 |
| three-node/write | +4.057 / +7.847 / +5.436 | +7.284 / +11.613 / +8.212 | -89.841 / -90.068 / -92.530 | -89.861 / -90.321 / -93.038 |
| three-node/lexical | +1.707 / +2.021 / -4.096 | +2.412 / +4.249 / +5.186 | -85.217 / -87.860 / -89.335 | -85.800 / -88.887 / -88.785 |
| three-node/ranking | +134.924 / +244.122 / +218.706 | +137.348 / +239.506 / +222.353 | -65.432 / -59.192 / -65.932 | -67.696 / -61.818 / -71.630 |
| three-node/facet | +0.811 / -1.187 / -1.836 | +2.415 / +0.600 / +4.140 | -84.147 / -86.195 / -87.747 | -84.203 / -86.657 / -87.786 |
| three-node/sort_filter | +1.342 / +2.844 / +0.121 | +1.182 / +6.748 / +3.970 | -89.141 / -91.031 / -91.630 | -88.933 / -90.189 / -90.755 |
| three-node/nested | -0.732 / -0.715 / -0.490 | -0.334 / -0.222 / +0.822 | -83.993 / -86.219 / -89.077 | -84.526 / -87.852 / -89.075 |
| three-node/refresh | +7.647 / +8.995 / +11.649 | +9.184 / +12.017 / +15.602 | -92.658 / -92.773 / -92.687 | -92.879 / -92.834 / -93.806 |

- 위 결과는 전체 후보의 누적 성능이다. 이번6줄 정수 경계 처리의 단독 손실이나
  최적화 불가능한 특정 기능의 비용으로 인과 분해한 자료가 아니다.
  이번 수정 전2d50548e도 이미 단일약35%/3노드약20% 처리량 회귀가 있었다.
  수락0/40, ledger 제외0, 릴리즈 보류다. 모든 측정/빌드/테스트 세션은 종료됐다.
  tag/push/publish하지 않았다.

#### 다음 우선순위: native 활용 및 정확도 계약 재검토 (2026-09-10, 조사 진행)

최소 비교와 참조 실행을 시작했다. 결과와 구현 전제는
[native ranking 조사 기록](native-ranking-audit-2026-09-10.md)을 따른다.
production native 전환은 아직 하지 않았다.

- 사용자 작업 원칙: **native로 처리하지 못하면 성능 문제 해결이 어렵다.**
  native 실행을 성능 예산 달성의 우선 경로로 삼고, source 재평가는 기본 해법이 아닌
  고위험 fallback으로 취급한다. 직접 구현 전에 고정 Tantivy 버전의 소스/API/확장 지점을
  조사하고 최소 재현 비교로 실제 부족함을 입증한다. 기존 fallback의 미세 최적화보다
  native 대체 가능성 검증을 먼저 한다. 별도 구현은 native 조합이나 좁은 확장으로
  요구 계약을 충족하지 못하는 이유를 기록한 뒤 진행한다. 이 원칙은 AGENTS.md에도
  반영했으며, 정확성·안전 조건과 단위별 전체 벤치마크·v0.6.0 누적5% 기준은 유지한다.
- 사용자 질문에 따라 설명을 바로잡는다. 현재 사용하는 Tantivy0.21.1 소스에는
  PhraseQuery::new_with_offset_and_slop, BooleanQuery, BoostQuery, DisjunctionMaxQuery,
  RangeQuery, Bm25StatisticsProvider 및 EnableScoring::enabled_from_statistics_provider가 있다.
  SteelSearch도 이 쿼리들을 이미 조합한다. 후처리 목록은 라이브러리 미지원 목록이 아니다.
  특히 bool의 multi_match/match-family 조건은 native 쿼리를 만들 수 있어도 현재
  query_requires_native_candidate_post_filter에서 후처리 대상으로 분류한다.
  모든 후처리가 필요한지, 통계 주입만으로 동등해지는지는 아직 입증하지 않았다.
- 다음 검증/구현 단위 순서를 우선 적용한다.
  1. ranking 쿼리를 leaf와 bool 조합으로 분리하고 동일 shard/reader에서 native 후보 집합,
     점수 및 source 결과를 비교한다. 실제 native 지원/현재 연결 누락/매칭 의미 차이/
     점수 수치 차이/reader 통계 수명 차이를 각각 기록한다. 단순 지원 심볼의 존재를
     OpenSearch 전체 의미의 동등성 증거로 삼지 않는다.
  2. 점수는 절대+상대 오차, near-zero, 거의 동점인 순위 및 top-k 영향을 검토한다.
     현재 HTTP search_scores의6자리 반올림과 최적화 회귀 테스트의 f32 bit 동일성은
     서로 다른 목적이다. 비트 동일성을 OpenSearch 호환성의 보편적 요구로 확대하지 않는다.
     수치 허용한도는 아직 확정하지 않았으며, 실패한17건을 자동 면제하지 않는다.
     min_score/점수 기반 필터/페이지 경계/오류/권한/문서 누락은 별도 의미 계약을 유지한다.
     cardinality처럼 원래 근사적인 집계는 기능별 정확도 계약으로 구분한다.
  3. 동등하거나 합의한 정확도 계약을 만족하는 경로부터 native scorer/collector를
     재사용하고 source 재평가를 제거한다. 필요한 경우 통계 provider 또는 scorer만
     보정한다. custom provider API가 있다는 사실만으로 field 통계/길이 norm/
     soft-delete 수명 차이가 자동 해결된다고 가정하지 않는다.
  4. source fallback이 실제 필요한 경로만 남긴 뒤 기존 숫자 필터 재검사 최적화와
     갱신 통계 수명 보강을 진행한다. fallback 전체를 삭제하거나 미지원 조건을 누락하지 않는다.
- 각 구현 단위는 집중 테스트/확장 HTTP에 더해 **전체 non-plugin benchmark**를 실행한 뒤
  판정한다. 최초 v0.6.0 대비 누적 throughput>=95%, 각 mean/p95/p99<=105%,
  반복 측정 및 동일 실제 입력/실행 파일 출처 조건을 그대로 유지한다.
  정확도 허용오차와 성능5% 예산은 별개이며, 이번 논의로 어느 합격 기준도 완화하지 않았다.

#### C05/C06 native minimum-one 전체 검증 (2026-09-10, 누적 성능 FAIL)

- 구현/테스트/정렬 경로 진단은 [native ranking 조사 기록](native-ranking-audit-2026-09-10.md)
  후속 절에 있다. Tantivy BooleanQuery의 optional 그룹을 한 번 Must로 연결해 중복 합산을
  제거했다. engine934건 통과, HTTP2248건 중2208통과40실패/skip0다.
  영구 회귀 fixture tools/fixtures/search-native-bool-minimum-one-scores-compat.json은
  실제 통과한 single-hit fixture와 동일한 바이트다. 기존 ordered 판정은 완화하지 않았다.
- 고정 후보 target/core-replacement-c06/native-minimum-one-candidate/artifacts/steelsearch:
  daede1396c497aa217fb16b68a7bd5d844c045fd5f590799464b06b9c8c92e7f.
  최초 기준 db244133, published 보고서 d2fdabfa 및 pinned OpenSearch 이미지1f8b8824를
  그대로 사용했다. 독립 source/build, source manifest 검증, 입력 해시 불변을 확인했다.
  빌드8분04초/종료0 이후 실행 파일을 보존하고 release 캐시682MiB만 정리했다.
- 전체 실행 target/core-replacement-c06/native-minimum-one-repeated-full:
  baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/baseline05,
  1101.790초,6하위 실행 종료0,12토폴로지 요청 오류0, 최종 종료1이다.
  execution_inputs_verified=true, numeric_budget_passed=false, acceptance_established=false.
  동일 workload/security/durability/resource 조건을 유지했다. 개발 프로파일 결과이며,
  실제 운영 보안/내구성 인증으로 확대하지 않는다.
  result.json SHA-256:
  a54f65c538d38343902eb9e0b9b27beb71f3af04d6df4bdc2a9d3e631b305a63.
  plan.json SHA-256:
  e382c85d3598f70129591cc30d48d48aaaf912e24470ee8c7774001a4a476d1e.
- published44지표 중20/21실패, paired16/19실패, 기준 drift36/44 및41/44 통과다.
  baseline00 drift 실패는 single write p99/refresh p99, three ranking p99/facet p99/
  sort_filter p99/refresh mean/p95/p99다.
  baseline05는 single write p95/p99와 three ranking p99다. 후보 회귀를 변동으로 면제하지 않는다.

| 처리량 ops/s | published v0.6.0 | baseline00 / 05 | candidate01 / 04 | OpenSearch02 / 03 |
| --- | --- | --- | --- | --- |
| single-node | 743.011 | 734.135 / 732.535 | 492.684 / 483.359 | 288.766 / 285.656 |
| three-node | 931.370 | 910.810 / 919.530 | 742.530 / 744.123 | 113.577 / 110.233 |

- 후보 처리량 누적 손실: 단일33.691%/34.946%,3노드20.276%/20.104%.
  OpenSearch 대비 배수는 단일1.706/1.692,3노드6.538/6.750이다.
  단일 ranking 평균21.712/22.096ms는 v0.6.0 대비238.570%/244.569% 증가,
  OpenSearch 대비76.468%/78.617% 증가다. 총 처리량 우위로 지연 실패를 상쇄하지 않는다.
- 아래 모든14시나리오 mean/p95/p99 변화율(%)은 실행기 결과의 actual metric에서 생성했다.
  양수는 지연 악화, 음수는 개선이다. 반복을 평균내거나 좋은 쪽만 선택하지 않는다.

| 시나리오 | v0.6.0 대비 01 | v0.6.0 대비 04 | OpenSearch 대비 01/02 | OpenSearch 대비 04/03 |
| --- | --- | --- | --- | --- |
| single-node/write | +2.106 / +4.712 / +3.456 | +3.126 / +6.694 / +4.870 | -77.909 / -73.257 / -79.353 | -78.214 / -74.611 / -80.690 |
| single-node/lexical | +10.484 / +12.893 / +72.149 | +12.972 / +16.849 / +58.424 | -52.943 / -43.823 / -20.665 | -52.588 / -42.897 / -22.753 |
| single-node/ranking | +238.570 / +279.967 / +220.262 | +244.569 / +282.454 / +226.879 | +76.468 / +103.266 / +43.984 | +78.617 / +98.557 / +49.953 |
| single-node/facet | -3.996 / -3.028 / +34.563 | -2.347 / -0.308 / +40.042 | -38.777 / -34.907 / -26.084 | -38.421 / -31.836 / -22.029 |
| single-node/sort_filter | +8.393 / +13.591 / +49.096 | +14.357 / +25.130 / +89.198 | -58.544 / -53.820 / -40.271 | -56.550 / -47.929 / -21.561 |
| single-node/nested | -4.179 / -0.245 / +34.902 | -2.852 / +1.657 / +38.702 | -41.242 / -37.302 / -18.540 | -40.654 / -35.371 / -18.040 |
| single-node/refresh | +2.127 / -3.890 / +0.083 | +4.622 / -2.060 / +3.541 | -84.999 / -86.918 / -87.736 | -84.719 / -86.538 / -88.117 |
| three-node/write | +3.948 / +5.850 / +4.725 | +3.731 / +5.293 / +2.023 | -90.004 / -91.094 / -93.149 | -89.896 / -90.622 / -92.113 |
| three-node/lexical | +1.034 / +1.320 / -4.364 | +0.361 / +1.103 / +1.353 | -85.506 / -87.798 / -90.232 | -86.187 / -88.666 / -89.038 |
| three-node/ranking | +133.009 / +238.195 / +216.681 | +130.076 / +233.214 / +213.248 | -66.852 / -62.700 / -70.433 | -68.212 / -63.457 / -70.006 |
| three-node/facet | +0.586 / -2.113 / +1.247 | +1.210 / -1.111 / +4.950 | -84.306 / -86.916 / -89.426 | -84.927 / -88.066 / -88.572 |
| three-node/sort_filter | -0.985 / +1.652 / -6.285 | +0.238 / +2.254 / +0.435 | -89.591 / -91.870 / -93.047 | -89.199 / -90.797 / -91.080 |
| three-node/nested | -0.885 / -0.343 / +6.127 | -2.525 / -3.041 / -0.202 | -83.461 / -85.911 / -87.808 | -83.820 / -86.367 / -86.496 |
| three-node/refresh | +6.012 / +4.945 / +11.680 | +8.482 / +11.233 / +14.128 | -92.611 / -92.804 / -92.317 | -92.990 / -92.665 / -92.689 |

- 전체 후보의 누적 회귀이며 이번 bool 수정의 단독 비용으로 인과 분해하지 않는다.
  이전439725ca부터 큰 회귀가 남아 있었다. 최적화 불가능한 특정 구현으로 입증된 것도
  아니므로 임의 제외나 예외 승인을 기록하지 않는다. 수락0/40, ledger 제외0, 릴리즈 보류다.
- 다음 단위는 native phrase 통계/boost/빈도 연결과 검증된 native 점수의 source 덮어쓰기
  제거를 함께 다룬다. 단일/샤드 및 정렬별 경로를 검증하고, 실제 의미 차이가 남은
  sloppy phrase/배열 위치는 native API/확장과 참조 explain 확인을 선행한다.
  eligibility, min_score/페이지 경계/오류/권한을 우회하지 않는다.
  이 단위도 집중 테스트/확장 HTTP와 전체 non-plugin 반복 benchmark를 실행하고,
  최초 v0.6.0 누적5% 기준을 통과하기 전에는 완료하지 않는다.
- 현재 측정/빌드/테스트 세션은 모두 종료됐다. tag/push/publish하지 않았다.

## Native Exact Phrase 반복 전체 검증 (2026-09-10)

- 조사 결과에 따라 native PhraseQuery/TermQuery의 BM25 통계 및 boost를 연결하고,
  검증된 top-level slop0의 source 점수 덮어쓰기를 제거했다. 필드 정렬의 선택 문서도
  native scorer로 채점한다. 원형 text 옵션/기본 메타데이터 복구/refresh eligibility와
  score0 보존 시험을 포함한다. 상세는 native-ranking-audit-2026-09-10.md 마지막 절이다.
- 최종 root engine941건(921+7+4+9), 실패/ignore/filter0, 종료0이다.
  engine-sixth.log SHA-256:
  93a2b89c9d9db28835296f8f9f744e3045f472af1b09e5e59d2d6fb5222368e7.
- 후보 경로: target/core-replacement-c06/native-exact-phrase-v2-candidate/artifacts/steelsearch.
  실제 실행 파일 SHA-256:
  f345f41f31f7aa640960bb2d9adf2d43586b49e2cd6552be08c525aac33e6da4.
  source.sha256: 838c6f3b3b8c17e12402c57427ca2bd4794963ac460bd7aae729644d37dbb667.
  candidate-build.log: b39a5422d640bb1f150a161d506a56c4bf33f51308cb72c8f619d29477c29f95.
  release 빌드5분47초/종료0. v1 후보 전용 Cargo cache를 v2 build로 옮겨 재사용했으며,
  root crates를 새 source에 동결했다. workspace/vendor/lock는 이전 독립 후보 설정을 유지했다.
  root 시험과 독립 release의 모든 의존 소스가 동일하다고 주장하지 않는다.
- v1 3624be06 실행 파일/소스/로그는 보존했다. benchmark 전 디스크 확보를 위해 이전
  fallback-pipeline/fst-isolated/native-bucket-pipeline 후보 실행 파일을 artifacts에
  복사·대조하고 cargo clean --release로 중간 캐시만 정리한 뒤 원 실행 경로에 복원했다.
  root dev cache도 최종 시험 종료 뒤 cargo clean --profile dev로 정리했다.
  공개 v0.6.0 기준선과 기존 검증 증거는 변경하지 않았다. 측정 중 빌드/시험/편집은 없었다.

### 전체 HTTP

- native-exact-phrase-v2-release-live: 33하위 비교, 총2286건 중2219통과67실패, skip0,
  count probe=true, binary_unchanged=true, fixtures_unchanged=true, 최종 종료1이다.
  참조는 actual 3.7.0-SNAPSHOT이며 성능의 pinned OpenSearch2.19와 별개다.
- 기존2248건에서1-phrase-exact/3-phrase-exact 두 건이 점수/순서까지 일치해 통과했다.
  기존 실패40건은38건이 됐다. 새38건은9통과29실패이며 이전 focused 실행과 합산하지 않는다.
- 실패 분포: 갱신 후 routing BM2517, 기존 native audit13, stable audit8,
  새 phrase explain26, 새 exact phrase3. 옵션 문자열2건과 공통1500건은 모두 통과다.
- exact phrase 새8건 중5통과3실패다. 세 실패 모두 total/ID/정렬은 같고 boost2의
  raw 점수 최대 차이1.507e-7 미만이6자리 반올림 경계를 넘는다.
  1샤드 exact/sparse: 0.13149941 vs0.1314995139837265,
  3샤드 repeat: 0.2926715 vs0.29267165064811707이다(참조 vs후보).
  허용오차 승인을 가정하지 않고 원 판정을 유지했다. sloppy의 실제 의미 차이는 별개다.
- execution.json: 207d3cb8422844a854d82c714272cf02945cac8686a57c9d47d69c488c7f6683.
  exact phrase report: a87a424f1f4ceba428802279e6e08ec9c29e395f40b3c37877e5c51c13d6e18a.
  phrase explain report: 31c11c719151532ae665cf3f14722628f5909cac69e3eb83f38149c3521d5f7a.

### 전체 성능

- target/core-replacement-c06/native-exact-phrase-v2-repeated-full:
  baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/baseline05.
  1104.196초,6하위 실행 종료0,12토폴로지 요청 오류0, 최종 종료1.
  execution_inputs_verified=true, numeric_budget_passed=false, acceptance_established=false.
  최초 v0.6.0 고정 baseline db244133 및 공개 current.json을 유지했다.
  같은5000문서/384 source values/4클라이언트/60초/seed13/3샤드/replica0·1,
  기존 non-plugin7종 혼합 부하와 개발용 보안·내구성·자원 설정이다.
  Java512MiB, pinned image sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb.
  실제 운영 보안/내구성/전체 자원 강제 인증으로 확대하지 않는다.
- published44지표 중21/21실패, paired18/20실패, 기준 drift41/44 및37/44 통과다.
  baseline00 drift 실패: single refresh p99, three ranking p99/nested p99.
  baseline05: three ranking p95/p99, facet p95/p99, nested p99, refresh mean/p99.
  이 변동으로 후보 회귀를 면제하거나 반복 일부를 버리지 않는다.
- result.json: 93fe00d38b2e6ce022c4d9b5f5b7e2749284199c296e5fb5902edd86bb41ebf5.
  plan.json: 7ab5d37b2587c6bba66ec1e16484fb47926ed6c8bc1f883a1b96983b4568c57f.

| 처리량 ops/s | published v0.6.0 | baseline00 / 05 | candidate01 / 04 | OpenSearch02 / 03 |
| --- | --- | --- | --- | --- |
| single-node | 743.011 | 737.909 / 750.348 | 478.837 / 486.959 | 273.467 / 270.259 |
| three-node | 931.370 | 913.024 / 898.642 | 742.415 / 744.767 | 109.600 / 113.383 |

- 누적 처리량 손실: 단일35.555%/34.461%,3노드20.288%/20.035%.
  OpenSearch 대비 처리량1.751/1.802배 및6.774/6.569배다.
  단일 ranking mean22.498/21.883ms, p9547.561/47.404ms, p9956.837/55.033ms.
  mean은 v0.6.0 대비250.837%/241.243%, OpenSearch 대비73.238%/68.832% 증가다.
  전체 처리량 우위로 ranking 지연 실패를 상쇄하지 않는다.
- 아래14시나리오는 실제 실행기 metric으로 생성한 mean/p95/p99 변화율(%)이다.
  양수는 지연 악화, 음수는 개선이며 두 반복을 평균내지 않는다.

| 시나리오 | v0.6.0 대비 01 | v0.6.0 대비 04 | OpenSearch 대비 01/02 | OpenSearch 대비 04/03 |
| --- | --- | --- | --- | --- |
| single-node/write | +2.969 / +6.008 / +3.664 | +2.068 / +5.019 / +5.538 | -78.220 / -74.618 / -79.425 | -78.877 / -75.924 / -79.925 |
| single-node/lexical | +12.857 / +16.782 / +59.721 | +12.317 / +20.368 / +56.533 | -54.359 / -44.327 / -25.853 | -55.323 / -42.902 / -26.878 |
| single-node/ranking | +250.837 / +283.303 / +227.384 | +241.243 / +282.035 / +216.992 | +73.238 / +95.926 / +43.627 | +68.832 / +98.285 / +51.606 |
| single-node/facet | -2.220 / -2.125 / +28.506 | -2.346 / +0.002 / +36.489 | -42.396 / -38.841 / -35.114 | -43.307 / -36.567 / -26.520 |
| single-node/sort_filter | +13.150 / +20.236 / +79.648 | +11.377 / +18.125 / +59.111 | -59.605 / -54.439 / -36.280 | -60.329 / -54.005 / -37.681 |
| single-node/nested | +0.249 / +5.123 / +53.544 | -2.711 / +2.430 / +25.090 | -42.867 / -38.275 / -23.123 | -44.944 / -36.663 / -21.104 |
| single-node/refresh | +4.022 / -3.296 / +4.588 | +3.931 / -4.959 / +2.295 | -85.295 / -87.350 / -87.019 | -85.596 / -87.889 / -88.101 |
| three-node/write | +2.692 / +4.910 / +1.781 | +3.211 / +4.973 / +3.980 | -90.244 / -91.071 / -91.944 | -89.875 / -90.215 / -92.848 |
| three-node/lexical | +0.479 / -1.435 / -5.042 | +0.155 / +0.771 / -3.677 | -85.811 / -88.228 / -88.696 | -85.474 / -87.419 / -90.164 |
| three-node/ranking | +136.656 / +249.129 / +230.274 | +132.955 / +236.522 / +220.887 | -67.804 / -62.475 / -67.825 | -66.739 / -65.751 / -68.191 |
| three-node/facet | -1.036 / -2.410 / -1.710 | -0.808 / -1.102 / +4.386 | -85.064 / -86.943 / -87.684 | -84.141 / -86.274 / -86.774 |
| three-node/sort_filter | +0.195 / +0.499 / -0.842 | +0.012 / +0.341 / -5.541 | -89.445 / -91.146 / -92.287 | -88.763 / -90.853 / -91.777 |
| three-node/nested | -2.143 / -2.866 / -2.324 | -1.708 / -1.604 / +4.413 | -84.022 / -86.510 / -87.919 | -84.684 / -86.694 / -89.211 |
| three-node/refresh | +5.386 / +7.260 / +11.703 | +6.710 / +6.319 / +15.451 | -93.243 / -92.978 / -93.514 | -93.026 / -93.167 / -93.657 |

### 미완료와 다음 경계

- 이번 누적 회귀를 exact phrase 단위만의 비용이라고 인과 분해하지 않는다.
  이전 후보에도 큰 회귀가 남아 있었고 최적화 불가능한 특정 구현으로 확정한 증거가 없다.
  임의 제외/예외 승인/기준선 재설정은 하지 않는다. 수락0/40, ledger 제외0, 릴리즈 보류다.
- 다음은 full ranking의 Bool/MultiMatch/필터 조합이 source 점수 경로로 남는 이유와
  native scorer 연결 가능 범위를 우선 확인한다. leaf의 native 정확성을 compound 전체로
  추정하지 않고 must/should/filter/minimum_should_match/boost/정렬/선택 샤드를 검증한다.
- sloppy fractional frequency와 배열 gap은 이미 확인한 native postings/scorer 및
  PreTokenizedString API를 우선한다. 반복·다중 토큰/분석기/명시 gap/explain/reader 수명을
  실제 참조와 비교하고 지원 범위를 숨기지 않는다. raw score 작은 차이를 맞추려고
  source scorer를 새로 구현하지 않는다.
- 각 후속 구현 단위도 전체 engine 및 확장 HTTP 후 full non-plugin 반복 benchmark를
  실행해야 한다. v0.6.0 throughput>=95%, 시나리오별 mean/p95/p99<=105%를 넘으면
  조사·최적화·전체 재측정 전 완료하지 않는다. 불가피한 제외/예외는 원래 정책을 따른다.
- 모든 빌드/시험/HTTP/성능 세션이 종료됐다. tag/push/publish하지 않았다.

## 2026-09-10 후속 단위: native array positions

### 구현 범위와 정확성

- pinned Tantivy0.21.1의 tokenizer_for_field/PreTokenizedString/add_pre_tokenized_text를
  연결했다. source를 다시 검색하는 엔진을 추가하지 않았다. scalar 문자열은 기존 add_text다.
  배열은 실제 native analyzer 토큰의 위치/offset을 연결하며 fieldnorm은 토큰 수를 유지한다.
- 실제 OpenSearch3.7.0-SNAPSHOT(f991609d190dfd91c8a09902053a7bbfe0c27b3e,
  Lucene10.4.0)에서 기본 gap100, 명시0/1/5, 문자열100을 비교했다.
  기본 ["alpha","beta"]의 위치0/101, 중간 빈 문자열이나 무토큰 문자열은 beta201,
  null/빈 배열은 beta101이다. 숫자12와 true는 위치101의 토큰이며 beta202가 된다.
  이 참조는 성능용 pinned OpenSearch2.19와 별개다.
- 참조80문서의 native postings/norm,55구문 hit 집합, 이전 refresh reader40문서,
  인덱스별 총 토큰32를 시험했다. token 위치 상한2147483519는 실제 Lucene 상수다.
  fallible 변환을 shared writer 변경 전에 준비하여 실패 batch의 앞 문서가 큐에 남지 않게 했다.
  engine 전체944건(924+7+4+9) 통과, 실패/ignore/filter0, 종료0이다.
- 첫 전체942건 통과 뒤 새2개 시험을 추가했다. 두 번째 실행은 시험 helper의 역방향
  postings.seek 때문에923통과1실패였다. helper를 수정한 세 번째 전체 실행944건이 최종이다.
  실패 로그를 보존했으며 테스트 실행 시간은 빌드와 겹쳐 성능 증거로 사용하지 않는다.
- raw mapping 옵션의 음수/소수/초과 범위 검증, 모든 analyzer 호환성, 객체 입력 거부,
  쓰기 API 단계의 overflow 거부 시점 및 복구 전체 계약은 이번 검증으로 인증하지 않는다.
  숫자/불리언 source BM25 캐시는 native와 동등하지 않아 eligibility를 보수적으로 제한했다.
  source phrase guard를 확대하거나 점수 오차 허용 기준을 변경하지 않았다.

### 후보와 전체 HTTP

- 최종 candidate: target/core-replacement-c06/native-array-positions-v2-candidate.
  frozen source/build/artifacts를 분리했다. v1 production 빌드6분17초 뒤 test-only seek 수정본을
  v2에 반영했고 후보 전용 Cargo cache를 이동해0.17초 빌드가 종료0으로 끝났다.
  v1/v2 실행 파일은 실제 SHA-256 비교로 동일한5a621371이다. v1 실패 시험 소스도 보존했다.
  cfg(test) 수정이므로 production 산출물은 변하지 않았다. 기준선 cache는 공유하지 않았다.
- root engine 시험과 frozen release 빌드의 의존 환경이 모두 같다고 주장하지 않는다.
  최종 production lib.rs는 root/frozen 동일이며 전체 HTTP와 성능은 아래 실제 artifact로 실행했다.
- native-array-positions-release-live:35하위 비교,2481건 중2229통과252실패, skip0,
  count probe=true, binary_unchanged=true, fixtures_unchanged=true, 종료1.
  이전2286건에 compound60건과 array135건을 추가한 범위다. 다른 실행의 성공 수를 합산하지 않았다.
- 실패: routing17, native audit13, stable audit8, phrase explain26, exact phrase3,
  compound50, array135. 공통1500건은 통과다.
- array135건은 termvectors80건/phrase scores55건 모두 엄격 비교 실패다.
  이전 f345f41f와 새5a621371의 실제 HTTP에서 phrase total/ID 집합 일치는28/55→55/55다.
  점수/순서까지 통과한 것으로 바꾸지 않는다. _termvectors는 여전히 source 기반 응답으로
  native 토큰 위치/통계를 노출하지 않는다. native postings 시험 통과와 API 실패는 별개다.

### 전체 반복 성능

- target/core-replacement-c06/native-array-positions-repeated-full:
  baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/baseline05.
  1100.047초,6하위 실행 종료0,12토폴로지 요청 오류0.
  execution_inputs_verified=true, numeric_budget_passed=false, acceptance_established=false.
- 최초 v0.6.0 db244133와 원본 공개 current.json은 해시 불변이다.
  동일5000문서/384 source values/4클라이언트/60초/seed13/3샤드/replica0·1,
  write15/lexical15/ranking15/facet15/sort_filter10/nested10/refresh5 혼합 부하다.
  dev sync0/deferred native writes1/Java512MiB 등 기존 개발 프로파일을 유지했다.
  OpenSearch image sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb.
  운영 보안·내구성·전체 자원 강제 인증으로 확대하지 않는다.
- published44지표 중23/28실패, paired19/22실패다. baseline drift41/44 및40/44 통과다.
  baseline00 drift 실패: single refresh p99, three sort_filter p99/nested p99.
  baseline05 drift 실패: single write p95/p99, sort_filter p95, refresh p99.
  변동으로 후보 회귀를 면제하거나 반복을 버리지 않는다.

| 처리량 ops/s | published v0.6.0 | baseline00 / 05 | candidate01 / 04 | OpenSearch02 / 03 |
| --- | --- | --- | --- | --- |
| single-node | 743.011 | 741.514 / 730.825 | 481.888 / 476.795 | 271.927 / 277.702 |
| three-node | 931.370 | 916.787 / 915.046 | 745.023 / 733.936 | 102.550 / 102.218 |

- 누적 처리량 손실은 단일35.144%/35.829%,3노드20.008%/21.198%다.
  OpenSearch 대비 처리량은 단일1.772/1.717배,3노드7.265/7.180배다.
- ranking mean은 단일22.178/22.524ms,3노드10.442/10.477ms다.
  단일 p9547.685/47.895ms,p9955.152/56.674ms이며,3노드 p9526.873/27.424ms,
  p9936.505/36.749ms다. 단일 mean은 v0.6.0 대비245.833%/251.230%,
  OpenSearch 대비69.669%/76.888% 증가했다. 전체 처리량으로 이를 상쇄하지 않는다.
- 다음 표는 실제 실행 metric에서 생성한 mean/p95/p99 변화율(%)이다.
  양수는 지연 악화, 음수는 개선이며 반복을 평균내지 않는다.

| 시나리오 | v0.6.0 대비 01 | v0.6.0 대비 04 | OpenSearch 대비 01/02 | OpenSearch 대비 04/03 |
| --- | --- | --- | --- | --- |
| single-node/write | +3.133 / +7.669 / +8.206 | +5.027 / +9.537 / +7.020 | -78.048 / -74.116 / -79.083 | -77.639 / -73.543 / -78.508 |
| single-node/lexical | +13.640 / +17.718 / +74.738 | +13.846 / +20.211 / +71.775 | -54.329 / -47.064 / -21.816 | -53.351 / -41.877 / -24.274 |
| single-node/ranking | +245.833 / +284.304 / +217.678 | +251.230 / +285.991 / +226.446 | +69.669 / +82.137 / +25.508 | +76.888 / +100.630 / +49.734 |
| single-node/facet | -1.050 / +0.216 / +24.391 | -2.670 / -1.364 / +23.974 | -41.927 / -42.137 / -48.416 | -40.873 / -33.873 / -25.546 |
| single-node/sort_filter | +10.849 / +18.843 / +57.751 | +16.029 / +27.947 / +92.601 | -60.517 / -54.330 / -43.871 | -57.628 / -49.878 / -25.195 |
| single-node/nested | -1.792 / +2.777 / +49.317 | -1.908 / +4.549 / +42.366 | -43.035 / -39.136 / -18.519 | -42.909 / -34.668 / -23.282 |
| single-node/refresh | +6.066 / +1.053 / +5.270 | +8.253 / -1.092 / +2.809 | -85.444 / -86.856 / -88.952 | -84.655 / -86.894 / -87.096 |
| three-node/write | +3.202 / +4.582 / +3.939 | +5.445 / +10.769 / +8.660 | -90.902 / -91.967 / -92.461 | -90.531 / -91.067 / -93.399 |
| three-node/lexical | +0.085 / +0.208 / -2.180 | +1.406 / +1.331 / -1.054 | -87.140 / -89.421 / -90.421 | -86.666 / -88.901 / -90.686 |
| three-node/ranking | +132.848 / +234.416 / +222.931 | +133.634 / +241.267 / +225.092 | -70.208 / -66.795 / -75.582 | -69.989 / -67.703 / -73.509 |
| three-node/facet | -0.440 / -2.757 / -1.756 | +2.176 / +0.377 / +7.598 | -85.688 / -88.030 / -89.818 | -85.537 / -88.032 / -89.723 |
| three-node/sort_filter | -0.094 / +2.743 / -3.766 | +1.843 / +5.497 / +3.798 | -89.897 / -91.338 / -93.472 | -90.067 / -91.439 / -91.699 |
| three-node/nested | -1.922 / +0.254 / -2.643 | -0.675 / -0.318 / +3.694 | -85.045 / -87.384 / -88.967 | -85.423 / -89.108 / -88.847 |
| three-node/refresh | +6.299 / +5.980 / +7.273 | +10.131 / +13.780 / +17.108 | -93.828 / -93.380 / -94.731 | -93.558 / -93.200 / -93.621 |

### 증거와 미완료

경로 기준: target/core-replacement-c06/. 새 artifact와 불변 기준선은 아래와 같다.

| 파일 | SHA-256 |
| --- | --- |
| native-array-positions-v2-candidate/artifacts/steelsearch | 5a621371baf2714124ebd8dad71f8cf0e07b3e476720daa4558792b657326375 |
| native-array-positions-v2-candidate/source.sha256 | ba5b3bd042669bfe668f78fd3d75e7b17ef88fcc03a5042dd190c0a6c8ad33cb |
| native-array-positions-v2-candidate/candidate-build.log | a50f4a953f17e887d3844be51c0df233623b83d4462c96d5392c2671458d7fef |
| native-array-positions/engine-third.log | ee4e333484518b16d64c10f67f4cc8724950119166983f4cc02118b1e99dcac8 |
| native-array-positions-release-live/execution.json | a3b1e2140ce479378ec1e37e34d535d8954fd75c1eafe03a3430243c55cb1d86 |
| native-array-positions-release-live/search-native-array-positions-compat-report.json | 60cd693283795a3f80828e87df9c74e4e19cbf224eab37ccfdf41085ac4a194e |
| native-array-positions-repeated-full/result.json | 1a21ea3818d316830fed70c98f48a087947006897c9eaf751417467517e69e94 |
| native-array-positions-repeated-full/plan.json | e7f5dc6b617136113c199861f82771b58e096a65067f364c3f434c44f6140a30 |
| ../core-replacement-s01/baseline/steelsearch | db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57 |

- root lib.rs:9fc17c0c4de670d8119cf9a19845da58d0905a8222705c806178132289aad785.
  native_array_position_tests.rs:9c44a48b6fc93809421795c2e0e36e669ca292ccb1182ea9ec3f6aa2a7e444b5.
  fixture:3945d7aeb1110e3eff69227421a71007e22684af0516196b7d345f8a1497efe1.
  reference fixture:dd1402d233868cbf708bf03dc28cc6ec228551abe00aa7bd146cbab87f503aa1.
  docs/releases/v0.6.0/current.json:d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788.
- 누적 회귀 전체를 이번 배열 구현의 단독 비용으로 단정하지 않는다. 선행 후보에도 큰 회귀가
  있었으며 최적화 불가능하다고 확정한 단독 구현은 아직 없다. 임의 제외나 예외 승인은 없다.
  수락0/40, ledger 제외0, 릴리즈 보류이며 이 단위를 완료로 처리하지 않는다.
- 다음 우선순위는 native sloppy phrase의 fractional 빈도와 compound score tree 연결이다.
  pinned PhraseScorer::phrase_count와 Bm25Weight::score는 u32 빈도이며, 내부 tf cache는
  비공개다. 기존 native postings/docset과 좁은 dependency 확장을 우선 검증한다.
  반복/다중 토큰/역순/boost/explain을 실제 참조와 비교하기 전 guard를 제거하지 않는다.
- 다음 구현 단위도 전체 engine/확장 HTTP 후 전체 non-plugin 반복 benchmark가 필수다.
  고정 v0.6.0 throughput>=95%, 각 mean/p95/p99<=105% 통과 전 완료하지 않는다.
  이 기록은 다음 단위의 검증을 대신하지 않는다. 모든 현재 시험/빌드/측정은 종료됐고
  tag/push/publish하지 않았다.

## 2026-09-10 후속 단위: native phrase scorer production 연결

### 구현과 시험

- native_phrase.rs에 Tantivy Query/Weight/Scorer를 연결했다. 문서 후보는 native unique-term
  conjunction이고 위치는 세그먼트별 SegmentPostings/재사용 Vec에서 읽는다.
  기존 sloppy PhraseScorer의 누락된 후보를 후처리로 복구하는 방식이 아니다.
- native_phrase_positions의 반복 위치 충돌/재배열 matcher를 사용한다.
  점수 없는 Count는 첫 매치에서 종료하며 BM25 통계/fieldnorm scoring을 생략한다.
  advance/seek/종료 cursor,삭제/refresh snapshot,Count/TopDocs/선택 문서 재채점을 시험했다.
- 원본 Tantivy0.21.1을 vendor/tantivy에 고정했다. crate SHA-256은
  d6083cd777fa94271b8ce0fe4533772cb8110c3044bab048d20f70108329a1f2,
  upstream VCS722b6c5205f61da2ca62ac62b1457b18a47b519c이다.
  원본 대조에서 코드 차이는 src/query/bm25.rs 하나뿐이며 score_fractional/explain_fractional을
  추가했다. 기존 정수 메서드/IDF/fieldnorm cache 계산은 변경하지 않았다.
  추가 STEELSEARCH.md와 제외한 Cargo cache marker .cargo-ok는 출처 문서에 구분했다.
- fractional API는 기존 native weight/cache를 사용한다.256개 norm과 정수 빈도5종에서
  기존 정수 score와 bit 단위 일치를 검증했고,실수 빈도/boost/explain도 시험했다.
  비공개 cache를 점수에서 역산하거나 source 문서 통계를 다시 만들지 않았다.
- production의 slop>0 다중 토큰 phrase를 연결하고 native_phrase_score_is_authoritative로
  권위 검사 이름을 정리했다. 기본 Text/ASCII 짧은 토큰/양수 유한 boost/기존 mapping·값·샤드
  호환성 조건을 유지했다. slop의u32 변환 한계도 검사한다.
  slop0/단일 토큰 기존 경로와 비기본 설정의 보호 조건은 유지했다.
- 전체 engine949건(929+7+4+9) 통과,실패/ignore/filter0,종료0이다.
  구문 slop0/1/3,반복어,1/3샤드,필드 정렬/페이지 및 매우 작은 양수 boost의 native score0
  보존을 포함한다.120조건의 scorer 문서 집합/896빈도/Count/선택 주소 재채점도 통과했다.
- 이번 시험은 native explain이다. HTTP explain 응답 전체를 native explain으로 교체하거나
  _termvectors,모든 analyzer/동일 위치 multi-term phrase,비기본 설정을 완료한 것은 아니다.
  query analyzer의 일반화된 위치/offset 전달과 미지원 옵션은 후속 검증이 필요하다.

### Frozen 후보와 HTTP

- target/core-replacement-c06/native-phrase-scorer-candidate에서5분28초 release 빌드,
  종료0이다. source/artifacts를 별도 고정했고 실제 실행 파일은
  e49e5b616f9312c1e41e05fa6dffded65c270d2c2d93c57a0c0b701e86cdc5ae다.
- 이전 array 후보의 source/artifact/증거를 보존하고 후보 전용 build cache만 이동했다.
  기준선 cache는 공유하지 않았다. root는 vendor Tantivy/registry FST, frozen은 vendor
  Tantivy/기존 frozen FST patch이므로 의존 환경이 모두 같다고 주장하지 않는다.
  각 lock 변경은 해당 패키지만 offline 갱신했고 frozen source manifest를 재검증했다.
- native-phrase-scorer-release-live:36하위 비교,2601건 중2322통과279실패/skip0,
  count probe=true,binary_unchanged=true,fixtures_unchanged=true,종료1이다.
  참조는 실제3.7.0-SNAPSHOT f991609d190dfd91c8a09902053a7bbfe0c27b3e/Lucene10.4.0이다.
  성능용 pinned OpenSearch2.19와 구분한다.
- 이전2481건에서 native audit2건과 phrase explain12건이 해결돼 실패252→238이다.
  추가 반복구문120건은79통과41실패(이전 frozen5a621371은14통과106실패)다.
  서로 다른 실행의 총 건수를 합산하지 않는다.
- 반복구문120건의 HTTP total/ID 집합은 모두 일치하고 동일 순서는96건이다.
  엄격 실패41건은 순서 차이24건/동일 순서 점수 차이17건이다.
  전체896개 ID별 raw 점수 최대 차이2.5803222647446944e-7이다.
  작은 점수 차이 또는 순서 차이를 임의 허용오차로 통과시키지 않았다.
- 실패 분포는 routing17,native audit11,stable audit8,phrase explain14,exact phrase3,
  compound50,array135,repeated phrase41이다. 공통1500건은 통과다.
  array135에는 source 기반 termvectors80건과 숫자/불리언 등이 섞인 phrase score55건이
  남아 있다. 네이티브 내부 위치/빈도 검증으로 이 API 실패를 덮어쓰지 않는다.

### 전체 반복 성능

- target/core-replacement-c06/native-phrase-scorer-repeated-full:
  baseline00/candidate01/OpenSearch02/OpenSearch03/candidate04/baseline05.
  1095.108초,6하위 실행 종료0,12토폴로지 요청 오류0,최종 종료1이다.
  execution_inputs_verified=true,numeric_budget_passed=false,acceptance_established=false.
- 동일5000문서/384 source values/4클라이언트/60초/seed13/3샤드/replica0·1,
  write15/lexical15/ranking15/facet15/sort_filter10/nested10/refresh5다.
  기존 dev sync0/deferred native writes1/Java512MiB 설정을 유지했고,
  OpenSearch image sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb다.
  운영 보안·내구성·자원 강제 인증으로 확대하지 않는다.
- published44지표 중23/27실패,paired17/20실패,baseline drift40/44와33/44통과다.
  baseline00 drift 실패:single refresh p99,three lexical p99/nested p99/refresh p99.
  baseline05 drift 실패:single write p95/facet p99/sort_filter p99/refresh p99,
  three write p95/ranking p95·p99/sort_filter p99/nested p95·p99/refresh p95.
  이 변동으로 후보 회귀를 면제하거나 반복을 버리지 않는다.

| 처리량 ops/s | published v0.6.0 | baseline00 / 05 | candidate01 / 04 | OpenSearch02 / 03 |
| --- | --- | --- | --- | --- |
| single-node | 743.011 | 740.863 / 727.572 | 473.125 / 482.402 | 284.777 / 287.966 |
| three-node | 931.370 | 914.704 / 906.346 | 743.459 / 730.627 | 106.431 / 109.480 |

- v0.6.0 누적 처리량 손실은 단일36.323%/35.075%,3노드20.176%/21.553%다.
  OpenSearch 대비 처리량은 단일1.661/1.675배,3노드6.985/6.674배다.
- 단일 ranking mean23.076/22.282ms,p9549.711/48.419ms,p9959.449/57.554ms다.
  3노드 mean10.396/10.504ms,p9526.960/27.327ms,p9935.594/36.894ms다.
  단일 mean은 v0.6.0 대비259.840%/247.457%,OpenSearch 대비83.556%/81.578% 느리다.
  전체 처리량으로 특정 시나리오의 지연 실패를 상쇄하지 않는다.
- 다음 표는 실제 executable metric으로 생성한 mean/p95/p99 변화율(%)이다.
  양수는 지연 악화,음수는 개선이며 두 반복은 별도로 유지한다.

| 시나리오 | v0.6.0 대비 01 | v0.6.0 대비 04 | OpenSearch 대비 01/02 | OpenSearch 대비 04/03 |
| --- | --- | --- | --- | --- |
| single-node/write | +3.817 / +8.720 / +4.641 | +4.250 / +6.706 / +4.612 | -77.170 / -71.468 / -76.668 | -77.161 / -72.224 / -76.712 |
| single-node/lexical | +12.824 / +19.694 / +75.670 | +10.637 / +11.735 / +67.793 | -53.271 / -41.523 / -17.011 | -53.035 / -43.148 / -16.489 |
| single-node/ranking | +259.840 / +300.626 / +242.433 | +247.457 / +290.217 / +231.514 | +83.556 / +110.053 / +60.269 | +81.578 / +110.282 / +53.577 |
| single-node/facet | -2.083 / -1.322 / +31.114 | -2.462 / -1.243 / +30.429 | -40.218 / -34.710 / -29.186 | -39.116 / -33.682 / -26.008 |
| single-node/sort_filter | +12.954 / +21.347 / +80.996 | +11.449 / +18.522 / +59.359 | -58.264 / -52.904 / -29.986 | -57.569 / -52.136 / -31.266 |
| single-node/nested | -0.161 / +6.456 / +57.216 | -1.644 / +4.923 / +38.300 | -40.265 / -33.324 / -8.626 | -40.153 / -31.203 / -19.455 |
| single-node/refresh | +5.143 / -1.541 / +5.176 | +6.359 / -2.411 / +2.558 | -84.389 / -86.142 / -86.273 | -84.417 / -87.239 / -88.451 |
| three-node/write | +4.443 / +6.954 / +5.627 | +5.844 / +9.581 / +11.474 | -90.426 / -90.984 / -92.443 | -89.756 / -90.528 / -91.101 |
| three-node/lexical | +1.558 / +1.271 / +2.144 | +2.112 / +3.352 / +4.345 | -86.237 / -89.107 / -89.797 | -85.986 / -87.925 / -88.759 |
| three-node/ranking | +131.822 / +235.497 / +214.872 | +134.237 / +240.058 / +226.378 | -68.716 / -63.121 / -73.505 | -68.055 / -65.026 / -69.515 |
| three-node/facet | -0.220 / -2.868 / -1.334 | +2.661 / +3.350 / +6.969 | -85.481 / -88.231 / -89.539 | -84.467 / -86.171 / -87.630 |
| three-node/sort_filter | +0.843 / +2.294 / -0.689 | +1.277 / +2.351 / -1.901 | -89.747 / -91.539 / -91.995 | -89.363 / -90.897 / -91.350 |
| three-node/nested | -1.750 / -0.853 / -0.860 | +1.142 / +5.914 / +8.821 | -85.362 / -89.121 / -88.337 | -83.851 / -85.393 / -85.741 |
| three-node/refresh | +5.492 / +4.923 / +1.550 | +10.473 / +13.779 / +15.263 | -93.282 / -93.280 / -94.063 | -92.878 / -92.767 / -94.407 |

### 미완료와 증거

- 성능 예산 초과로 이 단위를 완료하지 않는다. 선행 후보에도 큰 회귀가 있었으므로 이번
  누적 회귀를 새 phrase scorer만의 단독 비용이라고 단정하지 않는다.
  최적화 불가능한 특정 단독 구현으로 확정하지 않았으며 임의 제외/예외/기준 재설정은 없다.
  수락0/40,ledger 제외0,릴리즈 보류다. tag/push/publish하지 않았다.
- 다음은 source 경로가 남은 compound ranking의 검증된 leaf/score tree/MSM 연결이다.
  min_score/정렬/페이지/선택 샤드/옵션/권한/오류 조건을 유지하고 MSM>1의 조합 폭발과
  중복 점수를 native 경로에서 처리한다. native의 작은 점수 차이를 맞추려고 source scorer를
  새로 만들지 않는다.
- 후속 production 단위도 전체 engine/확장 HTTP2601건 이상과 전체 non-plugin 반복
  benchmark가 필수다. 고정 v0.6.0 throughput95%/각 mean·p95·p99105%를 통과하기 전
  완료하지 않는다. 앞 단위 측정이나 focused 검증으로 대체하지 않는다.
- 기준 실행 파일 db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57와
  docs/releases/v0.6.0/current.json d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788은 불변이다.

target/core-replacement-c06/ 기준:

| 파일 | SHA-256 |
| --- | --- |
| native-phrase-scorer-candidate/source.sha256 | 4ab71bb8244f4d557309dd4b946253f7a7c612e64353704cfefb2fa9e6e716bd |
| native-phrase-scorer-candidate/candidate-build.log | b545ca62b5be20fb15667abcb648c473ad6e394fd8a7750a430de3f8b742656e |
| native-phrase-scorer/engine-production.log | 9bcbde2643c303dc7d22ee54d47a0cacf8467e3b09e824127b446f0ff4913eb9 |
| native-phrase-scorer/production-diagnostic.json | 1e547f82e86ddedee20852fb91f075b22da5034e1c138cfc765644ad4841b80f |
| native-phrase-scorer-release-live/execution.json | 236ab017ddb54f31ee4692cb39c29673168521b66d3c8f3d9c56018c7cc4a3b2 |
| native-phrase-scorer-repeated-full/result.json | 287ec2dd185b5ae2f7180d4ce643a2f7a633bd3644be52891872edcc5395b110 |
| native-phrase-scorer-repeated-full/plan.json | c512c43c58262c3a239e9b4827d7518d9e5ffa2cee4534ea4b7f635496dc9931 |

production lib.rs:44eb00b14c7ac6ca6fb0720c0310f5442bffb58014de63f2179aea06aa4636ec.
native_phrase.rs:329eaa8a330cd7d037ae6bacd7beecc7186abc5aab8c41a2f4ae205bd15623b5.
native_phrase_positions.rs:9c2e1b8e3032909b7d9377bee58f48ef588ffc93156c7bcc103e4d4fd9a07a3f.
vendor BM25:4bdcee4f6a765357f064801db3874eef1c8415cf9517adde08b0086038bb4fe2.

## 2026-09-10 native MSM query 전체 반복 성능 FAIL

### 구현 및 실행 식별자

- Bool MSM>1의 조합 열거를 vendor Tantivy Union 기반 threshold query로 연결했다.
  native score 합산12조건은 정확히 일치하며 compound60조건의 최대 합산 차이는2.385e-7 미만이다.
  전체 engine951건 통과,전체 HTTP2601건은2322통과279실패/skip0이다.
  HTTP fixture별 집계는 직전 후보와 동일하며 source guard/compound authority는 아직 보존했다.
  [구현과 엔진/HTTP 증거](native-ranking-audit-2026-09-10.md#2026-09-10-native-msm-query-구현-전체-게이트-대기)를 참고한다.
- 이번 실제 후보는24e36d758fc43f99d491d2bcc29bea39dc678f1d2c28cc6c4ae3d5cdc45d3a0d이며
  경로는 target/core-replacement-c06/native-msm-query-candidate/artifacts/steelsearch 이다.
  기준 실행 파일은 최초 v0.6.0 db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57,
  published 원본은 docs/releases/v0.6.0/current.json
  SHA-256 d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788 이다.
- 성능 참조는 pinned OpenSearch2.19 이미지
  opensearchproject/opensearch@sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb 이다.
  HTTP 비교에 쓴3.7.0-SNAPSHOT/Lucene10.4와 별개다. 후보24e36d75 결과에 e49e5b61 수치를 섞지 않는다.
- 전체6실행/12토폴로지는1095.685초에 종료했다. 모든 자식 returncode0,요청 오류0,
  execution_inputs_verified=true,최종 numeric_budget_passed=false,acceptance_established=false,
  부모 exit1이다. 측정 중 빌드/시험/코드 변경은 없었으며 종료 후 frozen source.sha256도 통과했다.

### 전체 처리량

| 실행 | 역할 | 단일 ops/s | 3노드 ops/s | 요청 오류 |
| --- | --- | --- | --- | --- |
| 00 | baseline | 716.608 | 913.847 | 0 |
| 01 | candidate | 487.043 | 736.687 | 0 |
| 02 | opensearch | 280.178 | 101.185 | 0 |
| 03 | opensearch | 280.275 | 112.549 | 0 |
| 04 | candidate | 486.263 | 735.571 | 0 |
| 05 | baseline | 738.494 | 905.175 | 0 |

- 고정 published 처리량은 단일743.011,3노드931.370ops/s다. 후보01/04의 단일 감소율은
  34.450%/34.555%,3노드는20.903%/21.023%로 모두 누적5% 예산 초과다.
- 같은 반복의 OpenSearch 대비 후보 처리량 배수는 단일1.738/1.735,3노드7.281/6.536이다.
  전체 처리량 우위로 ranking 지연이나 v0.6.0 회귀를 상쇄하지 않는다.
- published44지표 중26/23개 실패,paired20/19개 실패다.
  기준선 자체 drift는32/44 및38/44통과로 둘 다 전체 통과가 아니다.
  drift 또는 별도 실행 사이의 개선을 근거로 실패 지표를 면제하지 않는다.
- baseline00 drift 실패: single-node/write/mean, single-node/write/p95, single-node/write/p99, single-node/ranking/p99, single-node/facet/p95, single-node/facet/p99, single-node/sort_filter/mean, single-node/sort_filter/p95, single-node/sort_filter/p99, single-node/refresh/p99, three-node/ranking/p99, three-node/sort_filter/p99.
- baseline05 drift 실패: three-node/write/p95, three-node/write/p99, three-node/facet/p95, three-node/facet/p99, three-node/sort_filter/p99, three-node/nested/p99.

### 모든 시나리오 지연

각 셀은 mean / p95 / p99 순서다. ms 열은 실제 지연이며,변화율의 양수는 더 느림이다.
후보01은 OS02와,후보04는 OS03과 비교한다. v0.6.0은 매번 최초 published 값을 사용한다.
표시는 반올림했지만 게이트는 원본 정밀도로 계산했다. 어떤 시나리오나 반복도 생략하지 않았다.

| 토폴로지 | 시나리오 | v0.6.0 ms | 후보01 ms | 후보04 ms | v0.6.0 대비01 | v0.6.0 대비04 | OS02 대비01 | OS03 대비04 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-node | write | 2.873 / 5.275 / 6.831 | 2.954 / 5.631 / 7.207 | 2.965 / 5.548 / 7.124 | +2.84% / +6.75% / +5.50% | +3.21% / +5.17% / +4.28% | -77.99% / -73.32% / -79.86% | -77.90% / -73.43% / -79.87% |
| single-node | lexical | 4.101 / 8.948 / 13.746 | 4.636 / 10.308 / 24.169 | 4.690 / 10.701 / 24.456 | +13.05% / +15.20% / +75.83% | +14.36% / +19.60% / +77.92% | -53.06% / -43.38% / -16.96% | -52.78% / -42.94% / -18.43% |
| single-node | ranking | 6.413 / 12.408 / 17.361 | 21.867 / 47.834 / 57.835 | 22.047 / 46.970 / 56.001 | +241.00% / +285.50% / +233.13% | +243.80% / +278.54% / +222.57% | +73.79% / +104.29% / +51.56% | +73.14% / +100.23% / +41.50% |
| single-node | facet | 7.340 / 15.158 / 20.214 | 7.124 / 15.033 / 25.058 | 7.060 / 14.943 / 25.253 | -2.94% / -0.82% / +23.96% | -3.82% / -1.42% / +24.93% | -41.23% / -37.10% / -30.67% | -41.46% / -36.37% / -32.90% |
| single-node | sort_filter | 4.572 / 9.300 / 14.151 | 4.996 / 11.127 / 21.918 | 5.028 / 10.762 / 21.749 | +9.26% / +19.65% / +54.88% | +9.97% / +15.72% / +53.69% | -59.94% / -52.88% / -45.90% | -59.39% / -52.85% / -47.61% |
| single-node | nested | 6.346 / 12.147 / 17.580 | 6.221 / 12.319 / 25.111 | 6.172 / 12.442 / 25.296 | -1.96% / +1.42% / +42.84% | -2.74% / +2.43% / +43.89% | -42.40% / -37.60% / -21.86% | -42.21% / -35.51% / -19.73% |
| single-node | refresh | 7.387 / 14.880 / 18.166 | 7.803 / 14.833 / 19.105 | 7.546 / 14.005 / 17.666 | +5.63% / -0.31% / +5.17% | +2.15% / -5.88% / -2.75% | -84.78% / -87.02% / -87.72% | -85.29% / -87.65% / -88.49% |
| three-node | write | 2.969 / 5.478 / 7.272 | 3.113 / 5.957 / 7.830 | 3.145 / 5.960 / 8.122 | +4.85% / +8.73% / +7.68% | +5.93% / +8.79% / +11.69% | -90.75% / -92.02% / -93.39% | -89.76% / -90.59% / -91.50% |
| three-node | lexical | 3.521 / 6.745 / 10.131 | 3.557 / 6.803 / 9.847 | 3.588 / 6.891 / 10.360 | +1.01% / +0.86% / -2.80% | +1.89% / +2.16% / +2.26% | -87.25% / -89.89% / -91.42% | -86.02% / -88.71% / -90.77% |
| three-node | ranking | 4.484 / 8.036 / 11.304 | 10.462 / 27.082 / 36.109 | 10.481 / 27.243 / 36.023 | +133.30% / +237.02% / +219.43% | +133.72% / +239.02% / +218.67% | -70.38% / -68.14% / -71.63% | -67.77% / -62.87% / -72.31% |
| three-node | facet | 4.933 / 9.454 / 13.121 | 5.019 / 9.586 / 13.730 | 5.038 / 9.468 / 13.280 | +1.75% / +1.40% / +4.64% | +2.13% / +0.14% / +1.21% | -86.40% / -88.73% / -90.56% | -83.93% / -85.97% / -88.41% |
| three-node | sort_filter | 3.973 / 7.190 / 10.959 | 4.035 / 7.476 / 10.936 | 3.992 / 7.335 / 10.478 | +1.57% / +3.97% / -0.20% | +0.49% / +2.02% / -4.39% | -90.11% / -92.21% / -92.80% | -89.13% / -91.10% / -92.70% |
| three-node | nested | 4.350 / 7.921 / 11.369 | 4.332 / 7.960 / 12.499 | 4.297 / 7.675 / 11.062 | -0.43% / +0.49% / +9.94% | -1.22% / -3.11% / -2.70% | -85.17% / -88.37% / -88.71% | -83.67% / -87.52% / -89.18% |
| three-node | refresh | 8.385 / 17.262 / 22.042 | 9.107 / 18.795 / 24.292 | 9.059 / 19.445 / 24.480 | +8.61% / +8.88% / +10.21% | +8.04% / +12.65% / +11.06% | -93.41% / -92.97% / -94.59% | -92.62% / -93.01% / -93.52% |


### 판정과 다음 조치

- 단일 ranking mean21.867/22.047ms는 고정 v0.6.0 대비240.995%/243.796% 느리며,
  같은 반복 OpenSearch12.583/12.734ms 대비73.788%/73.141% 느리다.
  3노드 ranking mean10.462/10.481ms도 v0.6.0 대비133.295%/133.717% 회귀다.
- MSM native score 중복은 엔진에서 해결했지만 source guard가 남은 compound ranking의
  비용은 해결하지 않았다. 직전 e49e5b61에도 큰 누적 회귀가 있었으므로 이번 회귀 전체를
  MSM 단독 비용이라고 단정하지 않는다. 이 측정은 직전 구현과의 단독 A/B 실험이 아니다.
- 수락0/40,제외0,릴리즈 보류다. 전체 suite 실행을 마쳤다는 것과 수락 완료는 다르다.
  5% 초과 상태에서 구현 단위를 정상 완료로 표시하지 않는다. 기준선 변경/허용오차 완화/
  안전 제어 해제/예외 승인은 없다.
- 다음은 누적 회귀 해소를 위한 compound native authority 연결이다. 기존 native leaf,
  실제 필드 옵션/샤드 통계가 증명되는 트리만 허용하고 min_score/페이지/정렬/오류/권한을
  보존한다. source 재평가의 추가 미세 최적화 대신 검증된 native score tree를 연결한다.
  다음 production 변경도 전체 engine/확장 HTTP2601건 이상/전체 non-plugin 반복 suite를
  별도로 실행한다. 고정 v0.6.0 throughput95%/각 mean,p95,p99 105% 통과 전 완료하지 않는다.
  단독5% 이상 미해결 구현의 제외 또는 명시적 예외는 기존 계획과 ledger 규칙을 따른다.
- 실제 mix는 write15/lexical15/ranking15/facet15/sort_filter10/nested10/refresh5,
  5000문서,384 source values,4clients,60초,seed13,3shards,단일replica0/3노드replica1이다.
  profile 명칭은 minilm-knn이지만 vector/hybrid 및 개별 fallback 진단 mix는0이다.
  이는 계획의 non-plugin suite 범위이며 별도 운영 보안/내구성/리소스 강제 인증은 아니다.
  Java512MiB와 실행 전후 runtime evidence는 원본 보고서에 보존했다.

### 증거

target/core-replacement-c06/ 기준:

| 파일 | SHA-256 |
| --- | --- |
| native-msm-query-candidate/source.sha256 | 15bb39ebe6f167b2dab01b04a6282aee9ff1d907fb4703186350c38cf86ee482 |
| native-msm-query-candidate/candidate-build.log | 0112a3def61e12fe61c916045082b3fa0a0ac6c21adc390666cebaa31da5818f |
| native-msm-query/engine-v2.log | 702069c77c43670bf5397ecb0320fe06a44b8b17bb80b618863b24ee0816e292 |
| native-msm-query-release-live/execution.json | 652dae27501422ac8ae5832d7760d06b651c966756b65f2eb9b23188dba14294 |
| native-msm-query-repeated-full/result.json | fb3e669d0a11be06eb6c66207843c9d3d9e16d3afa24a62e5321fd25a417abdf |
| native-msm-query-repeated-full/plan.json | 408538465cee459f5a609c0f0cac517d60b4aa9cab34e9b1eb837b186bdac667 |

6개 실제 summary.json의 경로/SHA-256,모든 paired/published/drift 원본 지표와
실패 목록은 result.json에 포함한다. frozen 빌드와 v0.6.0 빌드 디렉터리는 분리돼 있다.
