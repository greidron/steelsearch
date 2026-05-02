# Snapshot, Migration, And Interop APIs

## Milestone Gate

- Primary gate: `Phase A` standalone replacement, including Steelsearch-native
  snapshot, restore, and migration cutover flows.
- Later extension: `Phase B` for Java OpenSearch transport interop and
  read-only/coordinating migration rehearsal where Java still owns cluster
  membership and recovery.
- Final extension: `Phase C` for same-cluster recovery, relocation, and mixed
  snapshot/repository semantics.

## Snapshot And Restore

| Surface | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| Repository registration and verification | Declares and validates snapshot repositories. | Live standalone route family with strict-profile compare on the canonical repository-capable OpenSearch profile. | Partial |
| Create, status, restore | Creates snapshots, checks status, and restores into a target cluster. | Live standalone route family with strict-profile compare for create/readback/status/restore. | Partial |
| Delete and cleanup | Deletes snapshots and cleans orphaned repository state. | Live standalone route family with strict-profile compare, including delete-vs-restore concurrency semantics. | Partial |
| Corruption handling and fail-closed restore | Rejects stale/corrupt/incompatible snapshot metadata. | Live strict-profile compare for restore validation and failure classes. | Partial |

Important boundary:

- direct OpenSearch snapshot-byte reuse is not currently part of the first
  replacement gate;
- Steelsearch-native snapshot semantics are the current focus.

### Repository Registration / Readback / Verification Bounded Anchor

Current source-owned bounded repository surface is limited to:

- registration body subset:
  - `type`
  - `settings.location`
  - `settings.compress`
  - `settings.readonly`
  - `settings.chunk_size`
- readback subset:
  - repository name keyed object
  - bounded `type`
  - bounded `settings.location`
  - bounded `settings.compress`
  - bounded `settings.readonly`
  - bounded `settings.chunk_size`
- verification subset:
  - normalized `node_count`
  - normalized `node_names`

Current route-family anchor covers:

- `GET /_snapshot`
- `GET /_snapshot/{repository}`
- `PUT /_snapshot/{repository}`
- `POST /_snapshot/{repository}`
- `POST /_snapshot/{repository}/_verify`

This is now a richer repository CRUD/readback/verification anchor for the current standalone profile, covering primary/secondary repository registration, global readback, named readback, and normalized verification-node summaries. Full repository lifecycle parity is still broader than this option subset.

The current live activation step is source-owned runtime registration only:

- repository readback hook
- repository acknowledged mutation hook
- repository verification hook

all flow through one runtime registration body symbol. That is stronger than a
pure route table anchor, but still not the same as local route-traffic proof.

Current runtime-connected evidence:

- `SteelNode::handle_rest_request(...)` now dispatches
  `GET /_snapshot`, `GET /_snapshot/{repository}`, `PUT/POST /_snapshot/{repository}`,
  and `POST /_snapshot/{repository}/_verify`
  through the bounded repository helpers;
- a workspace-visible main-side test now drives those routes through the actual
  runtime path and checks bounded readback/mutation/verify shapes.

Current compare note:

- the local `snapshot-migration` profile now uses the actual repository base
  admitted by the OpenSearch `gradlew run` launcher:
  - `${OPENSEARCH_ROOT}/build/testclusters/runTask-0/repo`
- degraded-source skip from `path.repo` mismatch is removed;
- the current gate now exposes real repository/readback/restore parity drift
  instead of hiding snapshot lifecycle cases behind environment skips.
- snapshot lifecycle strict compare now passes in the `snapshot-migration`
  profile;
- bounded migration/cutover replay for the current fixture now also passes in
  the `snapshot-migration` profile;
- migration breadth coverage in the current strict profile now includes:
  - templates
  - aliases
  - data streams
  - opaque vector-bearing document payloads

### Snapshot Create / Status / Restore Bounded Anchor

Current source-owned snapshot lifecycle surface is limited to:

- create request subset:
  - `indices`
  - `include_global_state`
  - `ignore_unavailable`
  - `partial`
  - `metadata`
- create/readback response subset:
  - `snapshot`
  - `uuid`
  - `state`
  - `indices`
  - `include_global_state`
  - `metadata`
  - `partial`
  - `ignore_unavailable`
- status response subset:
  - `snapshot`
  - `repository`
  - `state`
  - `shards_stats`
- restore request subset:
  - `indices`
  - `include_global_state`
  - `include_aliases`
  - `ignore_unavailable`
  - `partial`
  - `rename_pattern`
  - `rename_replacement`
- restore response subset:
  - `snapshot`
  - `indices`
  - `shards`

Current route-family anchor covers:

- `PUT /_snapshot/{repository}/{snapshot}`
- `GET /_snapshot/{repository}/{snapshot}`
- `GET /_snapshot/{repository}/{snapshot}/_status`
- `POST /_snapshot/{repository}/{snapshot}/_restore`

This is the current standalone lifecycle contract and release-gated compare
surface. Remaining non-claims are broader repository-byte and mixed-cluster
semantics, not missing route activation.

### Snapshot Delete / Cleanup Bounded Anchor

Current source-owned delete/cleanup surface is limited to:

- delete response subset:
  - `acknowledged`
  - bounded `snapshot.snapshot`
  - bounded `snapshot.repository`
- cleanup response subset:
  - `results.deleted_bytes`
  - `results.deleted_blobs`

Current route-family anchor covers:

- `DELETE /_snapshot/{repository}/{snapshot}`
- `POST /_snapshot/{repository}/_cleanup`

This is a bounded cleanup/delete anchor, not yet a claim of full repository
garbage-collection or byte-level cleanup parity.

Current live activation step is source-owned runtime registration plus local
activation harness:

- delete hook
- cleanup hook
- reusable local route activation harness for the two bounded cleanup paths

Current local activation evidence:

- a workspace-visible main-side test now drives delete and cleanup shapes
  through the extracted cleanup local route activation harness;
- that proves bounded local cleanup activation for the current Phase A subset.

### Restore Validation Fail-Closed Rule

Current source-owned restore validation distinguishes three representative
pre-restore failure classes:

- stale metadata
- corrupt metadata
- incompatible metadata

Current canonical fail-closed envelope is:

- `error.type = snapshot_restore_exception`
- `status = 400`
- reason text that keeps the specific validation class visible

Current restore failure-path wiring:

- validated restore path now routes stale/corrupt/incompatible metadata through
  the same source-owned validation helper before bounded restore semantics run;
- clean metadata continues to the bounded restore subset.

Executable comparison note:

- `snapshot-lifecycle-compat` now carries explicit restore-failure cases for:
  - stale metadata
  - corrupt metadata
  - incompatible metadata
- those cases normalize restore failures to the strict compare tuple:
  - `status`
  - `error_type`
  - `failure_class`
- `failure_class` is derived from the boundary noun phrase in `error.reason`,
  so the compare stays strict on validation class without depending on wider
  prose drift.

Transcript note:

- [snapshot-restore-failure-transcript.md](/home/ubuntu/steelsearch/docs/api-spec/snapshot-restore-failure-transcript.md:1)
  remains as a human-readable reference sheet, not the canonical Phase A-1
  comparison mechanism.

Current live activation step is source-owned runtime registration:

- create hook
- readback hook
- status hook
- restore hook

all flow through one lifecycle runtime registration body symbol.

Current local activation evidence:

- a workspace-visible main-side test drives create/readback/status/restore
  shapes through the extracted lifecycle local route activation harness;
- that proves bounded local lifecycle activation for the current Phase A
  subset.

Current local activation evidence:

- a workspace-visible main-side test now drives repository readback, mutation,
  and verify shapes through the extracted local route activation harness;
- that proves bounded local activation, while full `SteelNode` REST traffic
  proof remains a later strengthening step.

## Migration And Cutover

Migration in the current design means moving data into Steelsearch through
supported APIs, not reusing OpenSearch shard stores directly.

Current supported direction:

- mappings/settings translation for the documented standalone migration contract;
- bulk import;
- search and behavior comparison through local rehearsal tools;
- strict-profile cutover rehearsal for the current standalone migration
  workload.

Major remaining gaps are now broader depth items rather than missing baseline
migration coverage:

- wider export coverage such as scroll/PIT-heavy workloads;
- deeper vector-specific migration validation beyond opaque payload replay;
- resumability and checkpointing;
- production rollback runbooks and evidence archives.
- standalone bounded cutover procedure:
  [standalone-cutover-runbook.md](/home/ubuntu/steelsearch/docs/rust-port/standalone-cutover-runbook.md)

### Phase A migration/cutover rehearsal procedure

Canonical rehearsal order:

1. prepare bounded source data
   - create source indices/templates/aliases only from the documented Phase A
     subset
2. export through supported APIs
   - use repository snapshot or bounded API export, but do not assume direct
     shard-store reuse
3. import into Steelsearch
   - replay mappings/settings/templates/aliases/documents only through supported
     write paths
4. run side-by-side compat checks
   - search compat
   - index lifecycle / mapping / settings / alias / template compat
   - single-document / bulk / routing / refresh compat
   - snapshot lifecycle compat when repository-backed migration is in scope
5. run Steelsearch-only multi-node validation
   - verify write propagation and post-cutover visibility on the target cluster
6. record cutover evidence
   - save compare reports under the canonical Phase A compare tree
   - attach restore failure transcript notes when restore validation paths are
     exercised

Reading rule:

- do not claim successful cutover from one runner alone;
- Phase A cutover evidence is the combined result of bounded import, bounded
  readback, compat reports, and Steelsearch-side propagation checks.

Current integration evidence:

- a dedicated cutover integration runner now seeds an OpenSearch source with
  bounded component/index templates, aliases, a data stream, and vector-bearing
  document payloads, replays the same bounded resources into Steelsearch, and
  compares bounded readback/search summaries across source and target;
- the same fixture now also emits extractor-backed metadata summaries for:
  - concrete index metadata
  - component template metadata
  - index template metadata
  - alias metadata
  - data stream metadata
  so migration-helper preservation claims are not limited to raw path checks.

## Transport Interop

Steelsearch currently treats Java OpenSearch interop as an external transport
client mode, not full cluster membership.

### Current boundary

- transport frame handling: partial support;
- handshake: implemented;
- cluster-state decode and local cache: partial support;
- selected request/response compatibility scaffolding: partial support.

### Explicitly blocked today

- Java cluster membership;
- Java data-node participation;
- publication acknowledgement as a real node;
- mixed-cluster recovery;
- Java plugin ABI compatibility.

## Representative OpenSearch Transport/Admin Surfaces Still Missing

The OpenSearch action inventory still includes large unimplemented groups:

- node info/stats/usage and hot threads;
- cluster health/state/settings/reroute/search shards;
- repository and snapshot actions;
- retention lease actions;
- PIT actions;
- dangling index actions;
- decommission and tiering actions;
- search pipeline actions;
- k-NN plugin transport actions.

## Notes

- Snapshot and migration are central to replacement strategy because Steelsearch
  is positioned as a standalone Rust-native cluster.
- Java mixed data-node compatibility remains a later or optional track and must
  stay fail-closed until membership, write-path, and recovery contracts exist.
