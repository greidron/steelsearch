# Standalone Cutover Runbook

This runbook defines the bounded OpenSearch-to-Steelsearch standalone cutover
flow currently supported by the repository. It is narrower than the production
operations runbook and exists to fix the operator procedure, evidence paths, and
rollback boundary for the standalone replacement profile.

## Scope

- source: OpenSearch cluster or bounded export flow supported by current
  migration helpers
- target: standalone Steelsearch runtime
- excluded from this runbook:
  - mixed-cluster membership
  - Java data-node interoperability
  - automatic on-startup schema migration
  - unsupported plugin-owned state without an explicit translator

## Phase 1: Pre-Cutover Validation

Checklist:

1. confirm supported route and semantic surface for the target workload;
2. confirm snapshot/repository routes used by the rehearsal are passing;
3. confirm metadata preservation evidence for aliases, templates, settings,
   mappings, and data streams;
4. confirm rollback owner and rollback window before traffic movement.

Required evidence artifacts:

- `target/search-semantic-compat-report.json`
- `target/document-write-semantic-compat-report.json`
- `target/index-metadata-semantic-compat-report.json`
- `target/admin-ops-semantic-compat-report.json`
- `target/snapshot-lifecycle-compat-report.json`
- `target/migration-cutover-integration-report.json`

Pass condition:

- all required reports exist;
- no required report shows failures in the bounded cutover path;
- unsupported feature inventory has no unwaived blocker for the workload being
  moved.
- blocker inventory reference:
  [unsupported-feature-detection-checklist.md](/home/ubuntu/steelsearch/docs/rust-port/unsupported-feature-detection-checklist.md)

## Phase 2: Cutover Execution

Checklist:

1. freeze or bound writes on the source side according to the migration plan;
2. take the bounded export/snapshot path supported by the current tooling;
3. restore/import into the standalone Steelsearch target;
4. run post-import metadata and document/readback checks before traffic moves.

Required evidence artifacts:

- `target/snapshot-lifecycle-compat-report.json`
- `target/migration-cutover-integration-report.json`
- any run-specific export/import logs captured by the operator

Pass condition:

- export/snapshot step completes without fail-closed restore/repository errors;
- target import/restore completes;
- bounded metadata preservation checks still pass after import.

## Phase 3: Post-Cutover Verification

Checklist:

1. verify representative search/read paths on the Steelsearch target;
2. verify document counts and selected metadata summaries;
3. verify alias, template, settings, mappings, and data stream continuity;
4. verify the target can still run bounded snapshot/restore after cutover.

Required evidence artifacts:

- `target/migration-cutover-integration-report.json`
- `target/alias-template-persistence-compat-report.json`
- `target/search-semantic-compat-report.json`
- `target/document-write-semantic-compat-report.json`

Pass condition:

- representative search and document readback pass;
- alias/template/index/data-stream metadata summaries match expected bounded
  preservation rules;
- no post-cutover verification report introduces a new failure in the cutover
  scope.

## Phase 4: Rollback

Checklist:

1. stop further target-side traffic expansion if verification fails;
2. return reads/writes to the source according to the rollback owner decision;
3. preserve Steelsearch-side evidence and pre-cutover snapshot artifacts for
   diagnosis;
4. do not delete target-side state until rollback review completes.

Required evidence artifacts:

- pre-cutover source snapshot/export record
- `target/migration-cutover-integration-report.json`
- rollback decision log or operator transcript

Pass condition:

- source-side service continuity is restored;
- target-side failure evidence is preserved;
- rollback reason is tied to explicit failed evidence rather than operator
  guesswork.

## Immediate Follow-up

1. unsupported-feature detection should attach directly to Phase 1.
2. snapshot/restore completeness matrix should be read alongside Phases 1 and 2:
   [snapshot-restore-completeness-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/snapshot-restore-completeness-matrix.md)
3. the acceptance harness should exercise all four phases end-to-end:
   `tools/run-migration-acceptance-harness.sh`
