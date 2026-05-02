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
| Repository verify | `POST /_snapshot/{repo}/_verify` | partial | missing-repository failure is covered, but full repository-byte parity and long-running verification semantics are not | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json) | treat as bounded admission check, not full repository health proof |
| Repository cleanup | `POST /_snapshot/{repo}/_cleanup` | partial | repeated cleanup is bounded, but cleanup-side effects and repository compaction semantics remain shallow | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json), [snapshot-migration-semantic-gap-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/snapshot-migration-semantic-gap-matrix.md) | safe for bounded rehearsal, not yet full operational guarantee |
| Snapshot metadata readback | `GET /_snapshot/{repo}/{snap}`, `GET /_snapshot/{repo}/{snap}/_status` | partial | metadata readback exists, but exact snapshot-manifest parity is not fully proven | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json) | sufficient for bounded fixture verification |
| Snapshot create/delete | `PUT /_snapshot/{repo}/{snap}`, `DELETE /_snapshot/{repo}/{snap}` | partial | duplicate create currently overwrites rather than proving conflict parity; repeated delete fail-closes | [snapshot-migration-semantic-gap-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/snapshot-migration-semantic-gap-matrix.md) | cutover-safe only if operator accepts bounded overwrite/delete semantics |
| Restore core path | `POST /_snapshot/{repo}/{snap}/_restore` | partial | restore readback and missing/corrupt failure fencing exist, but full restore materialization parity is still incomplete | [snapshot-lifecycle-compat.json](/home/ubuntu/steelsearch/tools/fixtures/snapshot-lifecycle-compat.json), [alias-template-persistence-compat.json](/home/ubuntu/steelsearch/tools/fixtures/alias-template-persistence-compat.json) | usable for bounded metadata-preservation rehearsal |
| Restore metadata preservation | aliases, templates, settings, mappings, data streams after restore | partial | bounded preservation is evidenced, but full OpenSearch metadata space is not | [alias-template-persistence-compat.json](/home/ubuntu/steelsearch/tools/fixtures/alias-template-persistence-compat.json), [migration-cutover-integration.json](/home/ubuntu/steelsearch/tools/fixtures/migration-cutover-integration.json) | rely only on the documented bounded metadata families |
| Restore options | option families beyond the bounded restore path | fail-closed only | unsupported/untested restore options may not preserve source behavior | current docs plus bounded fixture coverage only | do not assume broad restore-option compatibility without new evidence |

## Partial-Support Risk Notes

| Area | Risk if treated as fully supported |
| --- | --- |
| Repository cleanup/verify | operator may over-trust bounded route success as full repository integrity proof |
| Snapshot create/delete | duplicate create overwrite semantics may diverge from expected source-side conflict handling |
| Restore metadata preservation | unsupported metadata families may appear to restore while losing source semantics |
| Restore options | unproven options may create silent semantic drift if used during cutover |

## Immediate Follow-up

1. attach this matrix to Phase 1 and Phase 2 of the standalone cutover runbook.
2. extend it only when new restore options or repository-byte evidence are
   actually added.
3. treat `partial` rows as cutover risk until a stronger acceptance harness
   proves otherwise.
