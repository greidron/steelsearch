# Snapshot / Restore Completeness Matrix

This matrix is separate from route parity. Its purpose is to show how complete
the current repository/snapshot/restore surface is for cutover and rollback
decisions.

## Reading Rules

- `supported` means the bounded surface and its evidence are good enough for the
  current standalone cutover profile.
- `partial` means some route/evidence exists, but restore safety or metadata
  fidelity is still incomplete.
- `fail-closed only` means unsupported or invalid use is intentionally fenced,
  but successful semantics are not broad enough to claim general support.

## Completeness Matrix

| Family | Surface | Current status | Restore safety risk | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Repository registration | `PUT /_snapshot/{repo}`, `GET /_snapshot/{repo}`, `DELETE /_snapshot/{repo}` | partial | repository lifecycle exists, but broader durability and repeated-delete coverage are still bounded | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json), [snapshot-migration-semantic-gap-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/snapshot-migration-semantic-gap-matrix.md) | usable for bounded rehearsal, not yet a production-grade repository contract |
| Repository verify | `POST /_snapshot/{repo}/_verify` | partial | missing-repository failure is covered, and local `fs` repositories now perform a bounded create/write/delete verification probe instead of returning false success for inaccessible paths; full repository-byte parity, remote repository verification, and long-running verification semantics are not covered | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json), `snapshot_repository_verify_fails_closed_for_unwritable_fs_location`, `snapshot_repository_registration_verifies_fs_location_unless_disabled` | treat as bounded local admission check, not full repository health proof |
| Repository cleanup | `POST /_snapshot/{repo}/_cleanup` | partial | repeated cleanup idempotency is fixture-covered, and local cleanup now removes nested temporary blobs plus manifest-orphaned SteelSearch snapshot directories; full repository compaction and OpenSearch repository-byte parity remain shallow | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json), [snapshot-migration-semantic-gap-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/snapshot-migration-semantic-gap-matrix.md), `snapshot_cleanup_removes_orphan_snapshot_dirs_and_nested_temp_blobs` | safe for bounded local repository cleanup rehearsal, not yet full operational guarantee |
| Snapshot metadata readback | `GET /_snapshot/{repo}/{snap}`, `GET /_snapshot/{repo}/{snap}/_status`, `GET /_snapshot/_status`, `GET /_snapshot/{repo}/_status` | partial | metadata readback exists, `_status` honors `ignore_unavailable=true` for missing snapshot requests, repository-scoped collection status keeps OpenSearch running-only semantics by returning an empty `snapshots` array for `_all`, `*`, exact, and matching wildcard repository selectors, and `_status` now materializes detected repository-backed shard manifest read/parse/checksum failures instead of reporting corrupt shards as `DONE`; exact live OpenSearch parity for every shard stage is not fully proven | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json), `daemon_snapshot_restore_fails_closed_for_missing_and_corrupt_metadata`, `snapshot_index_status_route_delegates_to_snapshot_status_contract` | sufficient for bounded fixture verification, repository-selector collection polling, and local corrupt-repository status polling |
| Snapshot create/delete | `PUT /_snapshot/{repo}/{snap}`, `DELETE /_snapshot/{repo}/{snap}` | partial | duplicate create now fail-closes as `400 invalid_snapshot_name_exception`; first-delete, repeated-delete, and missing-repository create/delete behavior are fixture-covered | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json), [snapshot-migration-semantic-gap-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/snapshot-migration-semantic-gap-matrix.md) | cutover-safe only within the bounded create/delete semantics covered by fixtures |
| Restore core path | `POST /_snapshot/{repo}/{snap}/_restore` | partial | restore acknowledgement, renamed-index document materialization readback, multi-index selector wildcard/exclusion handling, `ignore_unavailable` missing-selector behavior, alias rename plus `alias_write_index_policy=strip_write_index` readback, existing open-index target collision failure shape, and missing/corrupt failure fencing are fixture-covered; the same detected shard manifest failures are now visible through `_status`; broader restore option space remains bounded | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json), [alias-template-persistence-compat.json](/home/ubuntu/steelsearch/tools/fixtures/alias-template-persistence-compat.json) | usable for bounded document, metadata-preservation, and corrupt-repository rehearsal |
| Restore metadata preservation | aliases, templates, settings, mappings, data streams after restore | partial | bounded preservation is evidenced, but full OpenSearch metadata space is not | [alias-template-persistence-compat.json](/home/ubuntu/steelsearch/tools/fixtures/alias-template-persistence-compat.json), [migration-cutover-integration.json](/home/ubuntu/steelsearch/tools/fixtures/migration-cutover-integration.json) | rely only on the documented bounded metadata families |
| Restore options | option families beyond the bounded restore path | fail-closed only | unsupported/untested restore options may not preserve source behavior; malformed/non-object restore bodies, invalid option values, unsupported body-level index option semantics, and unknown restore body parameters now fail at request parsing before restore application | current docs plus bounded fixture coverage only | do not assume broad restore-option compatibility without new evidence |

## Partial-Support Risk Notes

| Area | Risk if treated as fully supported |
| --- | --- |
| Repository cleanup/verify | operator may over-trust bounded local orphan/temp cleanup and local `fs` write-probe verification as full repository integrity proof |
| Snapshot create/delete | exact duplicate-create and repeated-delete reason-string parity may diverge outside the bounded status/type compare |
| Restore metadata preservation | unsupported metadata families may appear to restore while losing source semantics |
| Restore document materialization | document restore is pinned for renamed single-index, bounded multi-index selector fixtures, and existing open-index collision failure shape; broader conflict and option combinations still need explicit compare rows before treating restore as general-purpose |
| Restore options | wildcard/exclusion `indices`, `indices` array syntax, body-level `allow_no_indices`, `ignore_unavailable`, `include_aliases`, `rename_alias_pattern`, `rename_alias_replacement`, `alias_write_index_policy`, `include_global_state`, `index_settings`, and `ignore_index_settings` have bounded evidence, and malformed/non-object restore bodies plus invalid/unknown option values fail closed; unproven options may still create silent semantic drift if used during cutover |

## Immediate Follow-up

1. attach this matrix to Phase 1 and Phase 2 of the standalone cutover runbook.
2. extend it only when new restore options or repository-byte evidence are
   actually added.
3. treat `partial` rows as cutover risk until a stronger acceptance harness
   proves otherwise.
