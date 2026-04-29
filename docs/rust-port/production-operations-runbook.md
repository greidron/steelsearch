# Steelsearch Production Operations Runbook

This runbook defines the production backup, restore, cutover, and rollback
procedure for a standalone Steelsearch cluster.

Steelsearch production cutover remains gated by the readiness checks in
`docs/rust-port/development-replacement-profile.md`. This document is the
operator procedure that must be satisfied before a production cutover can be
approved. It does not waive missing product gates.

## Scope

The runbook applies only to Steelsearch-owned data:

- Steelsearch-native shard stores;
- Steelsearch-native snapshots;
- OpenSearch data migrated through scroll or PIT export plus Steelsearch
  `_bulk` import;
- mappings, settings, aliases, templates, and data streams translated by the
  migration tooling.

It does not permit direct restore of OpenSearch snapshot bytes into the
Steelsearch shard store. Direct OpenSearch snapshot import remains a
migration-only concern as described in
`docs/rust-port/snapshot-import-policy.md`.

## Required Evidence

Collect this evidence before opening a production cutover window:

- `/_steelsearch/readiness` output from every Steelsearch node;
- cluster health, node stats, index metadata, alias, template, and data-stream
  snapshots from the source and target clusters;
- latest successful Steelsearch-native snapshot ID and repository verification;
- migration checkpoint state for each source index and slice;
- document counts and ID/source checksums for every migrated index;
- vector field validation results for each migrated `knn_vector` field;
- sample query comparison results for high-value read paths;
- signed approval for the read-only window, rollback deadline, and final
  cutover decision.

The release owner must attach this evidence to the release record. Missing
evidence blocks cutover.

## Read-Only Window

Use a read-only window whenever writes can affect the source dataset after the
final migration checkpoint.

1. Announce the planned read-only window, expected duration, rollback deadline,
   and customer impact.
2. Stop or pause all writers that target the source OpenSearch cluster.
3. Apply source-side index write blocks for every migrated index.
4. Verify that write APIs fail or are rejected by the source cluster.
5. Capture final source cluster metadata, aliases, templates, data streams,
   document counts, and checksums.
6. Run the final incremental scroll/PIT export from the last persisted
   checkpoint.
7. Import final deltas into Steelsearch with retry-safe `_bulk` import.
8. Keep the source cluster in read-only mode until either cutover succeeds or
   rollback is declared.

Do not proceed if any writer cannot be stopped, any write block cannot be
verified, or final export checkpoints cannot be persisted.

## Backup Procedure

Perform a Steelsearch-native backup before cutover and after the final import.

1. Verify repository configuration and repository health.
2. Verify no snapshot delete or cleanup operation is in progress.
3. Create a pre-cutover snapshot for the target Steelsearch cluster.
4. Wait for snapshot completion and record the snapshot ID.
5. Verify snapshot status, shard count, byte count, and manifest checksum.
6. Run repository cleanup only after the completed snapshot is verified.
7. Capture target cluster metadata after snapshot completion.

The backup is valid only if all snapshot manifests are complete, repository
verification succeeds, and no stale deletion or cleanup marker is present.

## Restore Rehearsal

Restore rehearsal is mandatory before production cutover.

1. Start an isolated Steelsearch cluster with a fresh data path.
2. Restore the latest pre-cutover snapshot into the isolated cluster.
3. Verify cluster UUID and snapshot metadata compatibility.
4. Validate index metadata, mappings, settings, aliases, templates, and data
   streams against the captured target metadata.
5. Validate document counts, ID checksums, source checksums, and representative
   sample queries.
6. Validate vector dimensions and numeric vector payloads for all migrated
   vector fields.
7. Destroy the rehearsal cluster after evidence is captured.

Restore rehearsal fails closed. Any manifest mismatch, checksum mismatch,
missing shard file, incompatible metadata version, stale cleanup marker, or
query mismatch blocks cutover.

## Cutover Readiness Gates

All gates must pass before traffic moves to Steelsearch:

- source cluster is read-only and final checkpoint export is complete;
- target Steelsearch cluster is green or has an explicitly approved degraded
  state;
- production readiness endpoint reports no unaccepted blocker for the intended
  mode;
- latest Steelsearch-native snapshot is complete and restore rehearsal passed;
- source and target document counts match for every migrated index;
- source and target ID checksums match for every migrated index;
- source and target source-body checksums match for every migrated index;
- expected aliases and data streams exist on the target cluster;
- required templates exist on the target cluster;
- vector field validation has no dimension or non-numeric payload failures;
- representative searches return matching totals and top IDs within the
  approved compatibility scope;
- rollback owner, rollback deadline, and rollback DNS or routing plan are
  confirmed.

If any gate fails, keep traffic on OpenSearch and either retry migration from
the last checkpoint or declare rollback.

## Cutover Procedure

1. Confirm all readiness gates are attached to the release record.
2. Confirm source cluster is still read-only.
3. Put Steelsearch into the approved serving mode.
4. Warm high-value indices with representative search traffic.
5. Shift a small canary percentage of read traffic to Steelsearch.
6. Compare error rates, latency, search totals, and top IDs.
7. Increase traffic in planned increments only if canary checks pass.
8. Move write traffic to Steelsearch only after read traffic is stable and the
   owner approves the write cutover.
9. Keep OpenSearch read-only and available until the rollback deadline expires.
10. Capture final post-cutover health, stats, counts, checksums, aliases,
    templates, data streams, and sample query evidence.

Traffic movement must be reversible until the rollback deadline expires.

## Rollback Procedure

Rollback returns traffic to the read-only OpenSearch source or to the last
approved OpenSearch write target.

1. Freeze Steelsearch write traffic immediately.
2. Capture Steelsearch failure evidence: health, node logs, task state,
   snapshot state, rejected requests, and recent write IDs.
3. Shift read traffic back to OpenSearch.
4. Decide whether any Steelsearch-accepted writes must be replayed to
   OpenSearch or discarded under the incident policy.
5. If replay is required, export accepted Steelsearch writes by timestamp or
   operation log and apply them to OpenSearch with idempotent IDs.
6. Remove OpenSearch write blocks only after replay is complete and validation
   passes.
7. Keep Steelsearch isolated for forensic analysis.
8. Attach the rollback decision, validation evidence, and data reconciliation
   result to the release record.

Do not delete the Steelsearch pre-cutover snapshot or target data path until the
incident owner signs off.

## Post-Cutover Validation

Run these checks immediately after traffic reaches 100 percent and again before
the rollback deadline expires:

- cluster health and node stats;
- write success rate and rejected request count;
- search error rate and p95/p99 latency;
- document counts and ID/source checksums;
- alias, template, and data-stream presence;
- vector validation for new and migrated vector fields;
- representative query totals and top IDs;
- snapshot create and restore rehearsal on the post-cutover dataset;
- audit and access-control checks once production security is enabled.

If post-cutover validation fails, stop further traffic expansion and use the
rollback procedure.

## Ownership

Each production cutover requires named owners:

- release owner;
- source OpenSearch owner;
- Steelsearch target owner;
- migration owner;
- snapshot and restore owner;
- traffic routing owner;
- rollback owner;
- incident commander.

No person should approve their own evidence for both migration correctness and
rollback readiness.
