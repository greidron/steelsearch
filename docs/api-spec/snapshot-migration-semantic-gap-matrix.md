# Snapshot And Migration Semantic Gap Matrix

This matrix tracks semantic parity for snapshot, repository, restore, and
migration-adjacent routes beyond route existence. The goal is to separate:

- state mutation behavior,
- readback and verification behavior,
- cleanup and rollback safety,
- and the remaining gaps before stronger migration claims are made.

## Column Definitions

| Column | Meaning |
| --- | --- |
| `Family` | Snapshot or migration route family. |
| `Surface` | Concrete routes in scope. |
| `State mutation` | Whether the route mutates repository/snapshot/runtime state in a bounded, evidenced way. |
| `Readback / verification` | Whether the resulting state can be observed back through a read route or compare fixture. |
| `Failure handling` | Whether missing/duplicate/invalid cases are explicitly covered. |
| `Rollback safety` | Whether repeated cleanup/delete/restore or abort-like behavior is bounded/documented. |
| `Evidence` | Runtime tests, probes, or compare fixtures backing the claim. |
| `Code path / missing path` | Current implementation location or an explicit missing-path note. |
| `Notes / missing work` | Remaining gaps before migration-safe claims are reasonable. |

## Family Matrix

| Family | Surface | State mutation | Readback / verification | Failure handling | Rollback safety | Evidence | Code path / missing path | Notes / missing work |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| repository lifecycle | `PUT /_snapshot/{repo}`, `GET /_snapshot/{repo}`, `DELETE /_snapshot/{repo}` | partial | partial | partial | partial | existing repository route coverage in runtime tests and generated artifacts | repository handlers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Repository create/get/delete surface exists, but migration-grade durability and repeated delete safety are not yet summarized. |
| snapshot lifecycle | `PUT /_snapshot/{repo}/{snap}`, `GET /_snapshot/{repo}/{snap}`, `DELETE /_snapshot/{repo}/{snap}` | partial | partial | partial | partial | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json) now pins create/read/delete happy paths, duplicate create, missing snapshot read/delete, and missing-repository create/delete failures | snapshot handlers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Snapshot create/read/delete behavior has a bounded failure-path fixture matrix; broader manifest parity and option combinations remain bounded. |
| repository verify / cleanup | `POST /_snapshot/{repo}/_verify`, `POST /_snapshot/{repo}/_cleanup` | partial | partial | partial | partial | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json) now pins happy-path, repeated cleanup idempotency, and missing-repository failures for both routes | verify/cleanup handlers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Repository cleanup side effects remain bounded to the documented zero-deletion shape; full repository compaction semantics are not claimed. |
| restore | `POST /_snapshot/{repo}/{snap}/_restore` | partial | partial | partial | partial | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json) now pins happy-path, renamed-index document count readback, stale/corrupt/incompatible metadata fail-closed, and missing-snapshot failure; [alias-template-persistence-compat.json](/home/ubuntu/steelsearch/tools/fixtures/alias-template-persistence-compat.json) now carries restored template/index/data-stream metadata summaries | restore handler in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) plus [alias_template_persistence_compat.py](/home/ubuntu/steelsearch/tools/alias_template_persistence_compat.py) | Broader restore-time parity still needs multi-index, conflict, and option-combination materialization rows beyond the current bounded fixture. |
| migration helpers | migration-oriented helper routes and scripts | partial | partial | partial | partial | [migration-cutover-integration.json](/home/ubuntu/steelsearch/tools/fixtures/migration-cutover-integration.json) now carries explicit metadata-preservation summaries for concrete index metadata, component/index templates, aliases, and data streams in addition to bounded search/doc readback | cutover integration fixture plus existing helper scripts under `tools/` | Rollback rehearsal and restore-specific metadata continuity still need separate compare coverage. |

## Reading Rules

- `partial` means the route surface and some bounded behavior exist, but not yet
  enough evidence exists to claim migration-safe parity.
- Snapshot and restore routes should not be treated as replacement-ready until
  mutation, readback, failure handling, and rollback safety all have explicit
  fixture or harness evidence.

## Failure And Idempotency Matrix

| Scenario | Surface | Current behavior | Evidence | Code path / missing path | Remaining gap |
| --- | --- | --- | --- | --- | --- |
| repository missing | `GET /_snapshot/{repo}`, `PUT/DELETE /_snapshot/{repo}/{snap}`, `POST /_snapshot/{repo}/_verify`, `POST /_snapshot/{repo}/_cleanup` | missing repository now returns `404 repository_missing_exception` across bounded read, snapshot create/delete, verify, and cleanup routes | `get_missing_snapshot_repository_failure`, `create_snapshot_missing_repository_failure`, `delete_snapshot_missing_repository_failure`, `verify_missing_snapshot_repository_failure`, and `cleanup_missing_snapshot_repository_failure` in [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json) plus runtime matrix tests | [handle_snapshot_repository_delete_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), [handle_snapshot_repository_verify_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), [handle_snapshot_cleanup_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), [handle_snapshot_create_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), [handle_snapshot_delete_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | broader reason-string/body parity remains bounded to status/type/root-cause compare |
| snapshot missing | `GET/DELETE /_snapshot/{repo}/{snap}`, `GET /_status`, `POST /_restore` | missing snapshot returns `404 snapshot_missing_exception` across readback/status/restore/delete | existing snapshot lifecycle fixture plus restore/delete handler review | [handle_snapshot_readback_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), [handle_snapshot_status_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), [handle_snapshot_restore_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), [handle_snapshot_delete_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | exact root-cause/body parity still needs stricter compare coverage |
| duplicate create | `PUT /_snapshot/{repo}/{snap}` | repeated create with the same snapshot name now returns `400 invalid_snapshot_name_exception` like OpenSearch instead of overwriting the manifest entry | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json) | [handle_snapshot_create_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | exact root-cause/body parity can still be tightened beyond the bounded status/type compare |
| repeated delete | `DELETE /_snapshot/{repo}/{snap}` | first delete removes the snapshot and returns `200`; repeated delete returns `404 snapshot_missing_exception` | `delete_snapshot_repeated_first_delete` and `delete_snapshot_repeated_second_missing` in [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json) | [handle_snapshot_delete_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | exact reason-string parity remains intentionally bounded to status/type compare |
| repeated cleanup | `POST /_snapshot/{repo}/_cleanup` | bounded idempotent `200` response with `deleted_bytes=0` and `deleted_blobs=0` for an existing repository; missing repository now fail-closes as `404` | `cleanup_snapshot_repository_repeated_idempotent` in [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json) | [handle_snapshot_cleanup_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | cleanup side effects beyond the zero-deletion repository shape remain out of this bounded fixture |
