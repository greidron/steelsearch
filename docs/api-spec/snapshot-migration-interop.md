# Snapshot, Migration, And Interop APIs

## Milestone Gate

- Primary gate: `Phase A` standalone replacement, including Steelsearch-native
  snapshot, restore, and migration cutover flows.
- Later extension: `Phase B` for Java OpenSearch transport interop and
  read-only/coordinating migration rehearsal.
- Final extension: `Phase C` for same-cluster recovery, relocation, and mixed
  snapshot/repository semantics.

## Snapshot And Restore

| Surface | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| Repository registration and verification | Declares and validates snapshot repositories. | Development-oriented snapshot support exists, but full repository parity is incomplete. | Partial |
| Create, status, restore | Creates snapshots, checks status, and restores into a target cluster. | Development snapshot and restore flows exist for supported Steelsearch-native repositories. | Partial |
| Delete and cleanup | Deletes snapshots and cleans orphaned repository state. | Not yet full parity. | Planned |
| Corruption handling and fail-closed restore | Rejects stale/corrupt/incompatible snapshot metadata. | Some fail-closed testing exists, but full repository-grade parity is incomplete. | Partial |

Important boundary:

- direct OpenSearch snapshot-byte reuse is not currently part of the first
  replacement gate;
- Steelsearch-native snapshot semantics are the current focus.

### Repository Registration / Readback / Verification Bounded Anchor

Current source-owned bounded repository surface is limited to:

- registration body subset:
  - `type`
  - `settings`
- readback subset:
  - repository name keyed object
  - bounded `type`
  - bounded `settings`
- verification subset:
  - top-level `nodes`

Current route-family anchor covers:

- `GET /_snapshot`
- `GET /_snapshot/{repository}`
- `PUT /_snapshot/{repository}`
- `POST /_snapshot/{repository}`
- `POST /_snapshot/{repository}/_verify`

This is a bounded repository CRUD/readback/verification anchor, not yet a claim
of full repository lifecycle parity. Actual route-traffic proof remains a
separate step.

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

- the local `snapshot-migration` acceptance scope now exits cleanly;
- repository-grade OpenSearch comparison is currently degraded-source when the
  local OpenSearch launcher does not allow the fixture repository path via
  `path.repo`;
- in that environment, Steelsearch runtime proof remains live while
  OpenSearch-side snapshot cases are reported as explicit skips rather than
  false mismatches.

### Snapshot Create / Status / Restore Bounded Anchor

Current source-owned snapshot lifecycle surface is limited to:

- create request subset:
  - `indices`
  - `include_global_state`
  - `metadata`
- create/readback response subset:
  - `snapshot`
  - `uuid`
  - `state`
  - `indices`
- status response subset:
  - `snapshot`
  - `repository`
  - `state`
  - `shards_stats`
- restore request subset:
  - `indices`
  - `include_global_state`
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

This is a bounded Phase A lifecycle anchor, not a claim of full repository-byte
or full restore-option parity.

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

Transcript-based comparison note:

- representative stale/corrupt/incompatible restore failures now have a
  canonical comparison sheet in
  [snapshot-restore-failure-transcript.md](/home/ubuntu/steelsearch/docs/api-spec/snapshot-restore-failure-transcript.md:1)
- Phase A comparison preserves status, `error.type`, and boundary noun phrase
  before comparing wider prose.

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

- mappings/settings translation for supported subsets;
- bulk import;
- search and behavior comparison through local rehearsal tools;
- development cutover rehearsal for supported workloads.

Major remaining gaps:

- broader mappings/template/alias translation;
- data-stream translation;
- scroll/PIT export coverage;
- vector migration validation depth;
- resumability and checkpointing;
- production rollback runbooks and evidence archives.

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

- a dedicated cutover integration runner now seeds an OpenSearch source index,
  replays bounded mappings/settings/documents into Steelsearch, and compares the
  final search summary (`status`, `total`, ordered `_id` set) across source and
  target.

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
