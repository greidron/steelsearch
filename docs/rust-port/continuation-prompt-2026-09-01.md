# SteelSearch Continuation Prompt - 2026-09-03

다른 세션에 그대로 붙여넣을 프롬프트입니다.

```text
너는 /home/ubuntu/steelsearch 워크스페이스에서 이어서 작업한다.

최신 사용자 목표:
"문서를 기반으로 OpenSearch API/production replacement를 완수할 때까지 수정 진행. 미비한 기능을 추가하되 성능이 기존 기준 대비 5% 이상 감소하지 않게 벤치마크와 대조하고, 회귀가 있으면 개선."

중요 해석:
- 전체 OpenSearch production replacement는 아직 완료가 아니다.
- 현재 작업은 전체 목표 중 API semantic gap을 하나씩 닫는 진행이다.
- completion claim은 금지. 문서/테스트/벤치마크 evidence가 모든 replacement class를 증명하기 전에는 goal complete 처리하지 말 것.
- 성능 기준 baseline은 최초 지정된 현재 기준:
  - `target/search-benchmark-matrix-api-snapshot-status-repository-selector-full-20260831/summary.json`
  - SteelSearch single-node throughput: `745.2692917204424 ops/s`
  - 5% floor single-node: `708.0058271344203 ops/s`
  - SteelSearch three-node throughput: `898.247911701037 ops/s`
  - 5% floor three-node: `853.3355161159851 ops/s`
  - baseline에는 `steelsearch_slower_than_opensearch` metrics 없음.

일반 제약:
- 사용자 변경사항을 되돌리지 말 것.
- destructive git 명령 금지.
- apply_patch로 수동 편집할 것.
- `rg` 우선 사용.
- 독립 파일 조회는 `multi_tool_use.parallel` 사용.
- dirty worktree가 많다. 관련 없는 파일은 무시하고, 이번 작업 관련 파일만 다룰 것.

현재 막 멈춘 작업:
`API-SNAPSHOT-RESTORE-ALIAS-WRITE-POLICY-001`

목표:
OpenSearch snapshot restore body option `alias_write_index_policy`의 bounded 지원.

OpenSearch source evidence:
- `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/action/admin/cluster/snapshots/restore/RestoreSnapshotRequest.java`
  - enum values: `PRESERVE`, `STRIP_WRITE_INDEX`
  - `fromString`은 `value.toUpperCase(Locale.ROOT)` 기반이라 case-insensitive.
  - invalid value reason:
    `Unknown alias_write_index_policy [x]. Valid values are: [PRESERVE, STRIP_WRITE_INDEX]`
- `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/snapshots/RestoreService.java`
  - `applyAliasWriteIndexPolicy`
  - `STRIP_WRITE_INDEX`이고 alias `writeIndex()`가 true면 restored alias metadata를 `writeIndex(false)`로 만든다.

이미 적용한 코드 변경:
- `crates/os-node/src/standalone_runtime.rs`
  - `apply_snapshot_restore_options`에서 body의 `alias_write_index_policy`를 파싱.
  - default는 `Preserve`.
  - `strip_write_index`는 alias rename 뒤에 적용.
  - 새 enum 추가:
    `SnapshotRestoreAliasWriteIndexPolicy::{Preserve, StripWriteIndex}`
  - 새 helper 추가:
    - `snapshot_restore_alias_write_index_policy`
    - `validate_snapshot_restore_alias_write_index_policy_body_field`
    - `snapshot_restore_unknown_alias_write_index_policy_response`
    - `apply_snapshot_restore_alias_write_index_policy`
  - 기존에는 `alias_write_index_policy`를 known field로 두고 unsupported 400을 반환했는데, 이제 `preserve`/`strip_write_index`는 지원.
  - invalid string은 400 `illegal_argument_exception`.
  - non-string은 400 `illegal_argument_exception`, reason `malformed alias_write_index_policy`.
  - `strip_write_index`는 alias object의 `is_write_index: true`를 `false`로 변경.
- 같은 파일의 테스트 `snapshot_restore_renames_aliases_when_alias_pattern_is_supplied`
  - 기존 default restore는 `is_write_index: true`가 유지되는지 확인.
  - 새 restore with `alias_write_index_policy: "strip_write_index"`는 restored alias의 `is_write_index: false` 확인.
  - invalid policy `"invalid"`와 malformed boolean policy `true`가 400으로 실패하는지 확인.
- `tools/snapshot_lifecycle_compat.py`
  - extractor `index_alias_names`가 이제 `write_indices` dict도 반환.
- `tools/fixtures/snapshot-lifecycle-compat.json`
  - `restore_snapshot_alias_rename` body에 `"alias_write_index_policy": "strip_write_index"` 추가.
  - `restore_snapshot_alias_rename_readback` compare에 `write_indices` present/equal 추가.
- `docs/api-spec/snapshot-restore-completeness-matrix.md`
  - restore core path / restore options에 `alias_write_index_policy` bounded evidence 반영.
- `docs/api-spec/snapshot-migration-semantic-gap-matrix.md`
  - restore evidence에 alias rename plus `alias_write_index_policy=strip_write_index` readback 반영.
- `docs/rust-port/opensearch-api-gap-implementation-ledger-2026-08-30.md`
  - 새 row `API-SNAPSHOT-RESTORE-ALIAS-WRITE-POLICY-001` 추가.
  - 현재 evidence는 아직 "Pending validation in this pass"로 적혀 있음. 검증 후 반드시 업데이트할 것.

이미 확인된 검증:
- `python3 -m json.tool tools/fixtures/snapshot-lifecycle-compat.json >/dev/null` 통과.
- `python3 -m py_compile tools/snapshot_lifecycle_compat.py` 통과.
- `git diff --check` 통과.

아직 확정되지 않은 검증:
- `cargo fmt --check`
- `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore_renames_aliases_when_alias_pattern_is_supplied --features standalone-runtime -- --nocapture`

주의:
- 위 두 cargo 검증은 세션 poll이 `aborted`로 끊겼고, 이후 `ps` 확인 결과 남아 있는 cargo/rustc 프로세스는 없었다.
- 실패인지 통과인지 확정되지 않았으므로 반드시 다시 실행해야 한다.

다음에 바로 할 일:
1. 현재 상태 확인:
   - `git status --short`
   - `ps -eo pid,ppid,stat,etime,cmd | rg 'cargo|rustc|snapshot_restore_renames'`
2. formatter/문법/targeted test 재실행:
   - `cargo fmt --check`
   - `python3 -m json.tool tools/fixtures/snapshot-lifecycle-compat.json >/dev/null`
   - `python3 -m py_compile tools/snapshot_lifecycle_compat.py`
   - `git diff --check`
   - `RUSTFLAGS='-Awarnings' cargo +nightly test -q -p os-node snapshot_restore_renames_aliases_when_alias_pattern_is_supplied --features standalone-runtime -- --nocapture`
3. 실패하면 수정.
4. compile gate:
   - `RUSTFLAGS='-Awarnings' cargo +nightly check -p os-node --features standalone-runtime`
5. 필요하면 focused snapshot lifecycle fixture를 SteelSearch-only로 실행해서 extractor output을 확인:
   - runner 사용법을 `rg -n "argparse|--case|snapshot-lifecycle" tools`로 확인.
6. release build:
   - `RUSTFLAGS='-Awarnings' cargo +nightly build -q --release -p os-node --bin steelsearch --features standalone-runtime`
7. 성능 판단:
   - 이번 변경은 snapshot restore admin path와 fixture extractor라 indexing/search/refresh hot path를 건드리지 않는다.
   - 그래도 사용자의 전체 목표상 full benchmark를 돌리는 것이 원칙이다.
   - 실행:
     `STEELSEARCH_BINARY_PATH=target/release/steelsearch python3 tools/run-search-benchmark-matrix.py --profile minilm-knn --reuse-steelsearch-binary --output-dir target/search-benchmark-matrix-api-snapshot-restore-alias-write-policy-full-20260903`
   - benchmark 결과가 baseline 5% floor 아래면 회귀 원인을 조사하고 수정.
   - floor:
     single-node >= 708.0058271344203 ops/s
     three-node >= 853.3355161159851 ops/s
8. ledger row의 Evidence를 pending에서 실제 통과한 명령과 benchmark artifact로 갱신.
9. 마지막:
   - `cargo fmt --check`
   - `git diff --check`
   - `git status --short`
10. 최종 보고는 한국어로 간결하게:
   - 구현한 gap: `API-SNAPSHOT-RESTORE-ALIAS-WRITE-POLICY-001`
   - 건드린 파일
   - 통과한 검증
   - benchmark 결과 및 baseline 5% floor 대비 여부
   - 전체 OpenSearch replacement는 아직 완료가 아님을 명확히 언급.

관련 파일:
- `crates/os-node/src/standalone_runtime.rs`
- `tools/snapshot_lifecycle_compat.py`
- `tools/fixtures/snapshot-lifecycle-compat.json`
- `docs/api-spec/snapshot-restore-completeness-matrix.md`
- `docs/api-spec/snapshot-migration-semantic-gap-matrix.md`
- `docs/rust-port/opensearch-api-gap-implementation-ledger-2026-08-30.md`

같은 장기 작업에서 이미 완료된 인접 항목:
1. `API-SNAPSHOT-STATUS-REPOSITORY-SELECTOR-001`
   - snapshot 이름 없는 `_status` collection은 running-only semantics.
   - `_all`, `*`, matching wildcard repo selector는 accepted.
   - exact missing repo는 404.
   - baseline artifact:
     `target/search-benchmark-matrix-api-snapshot-status-repository-selector-full-20260831/summary.json`
2. `API-SNAPSHOT-CLEANUP-ORPHAN-BLOBS-001`
3. `API-FIELD-CAPS-INDEX-FILTER-BOOL-001`
4. `API-SNAPSHOT-REPOSITORY-FS-VERIFY-PROBE-001`
5. `API-SNAPSHOT-RESTORE-MALFORMED-BODY-001`
   - malformed/non-object restore bodies, invalid option values, indices array, allow_no_indices, expand_wildcards validation, unknown params 등 bounded parsing/validation 보강.
```
