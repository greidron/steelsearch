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
| snapshot lifecycle | `PUT /_snapshot/{repo}/{snap}`, `GET /_snapshot/{repo}/{snap}`, `DELETE /_snapshot/{repo}/{snap}` | partial | partial | partial | partial | current snapshot route coverage and generated artifacts | snapshot handlers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Snapshot create/read/delete behavior needs a clearer mutation/readback matrix and failure-path fixture set. |
| repository verify / cleanup | `POST /_snapshot/{repo}/_verify`, `POST /_snapshot/{repo}/_cleanup` | partial | partial | partial | partial | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json) now pins happy-path plus missing-repository failures for both routes | verify/cleanup handlers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Repeated cleanup idempotency and repository mutation/readback after cleanup still need stronger evidence. |
| restore | `POST /_snapshot/{repo}/{snap}/_restore` | partial | partial | partial | partial | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json) now pins happy-path, stale/corrupt/incompatible metadata fail-closed, and missing-snapshot failure; [alias-template-persistence-compat.json](/home/ubuntu/steelsearch/tools/fixtures/alias-template-persistence-compat.json) now carries restored template/index/data-stream metadata summaries | restore handler in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) plus [alias_template_persistence_compat.py](/home/ubuntu/steelsearch/tools/alias_template_persistence_compat.py) | Full restore-time metadata parity still depends on actual restore materialization, not just compare wiring. |
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
| repository missing | `GET/DELETE /_snapshot/{repo}`, `POST /_snapshot/{repo}/_verify`, `POST /_snapshot/{repo}/_cleanup` | missing repository now returns `404 repository_missing_exception` across delete/verify/cleanup bounded routes | current missing-repository fixture coverage plus cleanup unit test | [handle_snapshot_repository_delete_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), [handle_snapshot_repository_verify_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), [handle_snapshot_cleanup_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | broader root-cause/body parity still needs stricter compare coverage |
| snapshot missing | `GET/DELETE /_snapshot/{repo}/{snap}`, `GET /_status`, `POST /_restore` | missing snapshot returns `404 snapshot_missing_exception` across readback/status/restore/delete | existing snapshot lifecycle fixture plus restore/delete handler review | [handle_snapshot_readback_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), [handle_snapshot_status_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), [handle_snapshot_restore_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), [handle_snapshot_delete_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | exact root-cause/body parity still needs stricter compare coverage |
| duplicate create | `PUT /_snapshot/{repo}/{snap}` | repeated create with the same snapshot name overwrites the manifest entry and still returns `200`; there is no conflict envelope today | runtime handler review | [handle_snapshot_create_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | if OpenSearch-like conflict-on-duplicate is desired, create semantics need explicit fail-closed or overwrite policy tests |
| repeated delete | `DELETE /_snapshot/{repo}/{snap}` | first delete removes the snapshot and returns `200`; repeated delete returns `404 snapshot_missing_exception` | existing delete route coverage plus runtime handler review | [handle_snapshot_delete_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | repeated delete compare fixture is still missing |
| repeated cleanup | `POST /_snapshot/{repo}/_cleanup` | bounded idempotent `200` response with `deleted_bytes=0` and `deleted_blobs=0` for an existing repository; missing repository now fail-closes as `404` | runtime handler review plus missing-repository cleanup test | [handle_snapshot_cleanup_route](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | repeated cleanup compare fixture is still missing |
