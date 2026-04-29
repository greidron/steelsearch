# Write Path Compatibility Model

This document records the Rust-side model Steelsearch must satisfy before it
can safely participate in Java OpenSearch primary or replica write paths.

The current implementation must remain coordinating-only for Java cluster
writes. Matching the transport action names is not enough; write compatibility
requires the same primary sequencing, replication request shape, sequence-number
semantics, translog durability, refresh behavior, and failure handling.

## Primary Write Sequencing

Checked Java sources:

- `TransportShardBulkAction`
- `BulkPrimaryExecutionContext`
- `TransportWriteAction`
- `ReplicationOperation`
- `IndexShard`
- `Engine`

The Java primary path for bulk/index writes is:

1. Resolve the target shard and execute on the primary shard through
   `TransportWriteAction` / `TransportShardBulkAction`.
2. Maintain per-item bulk state in `BulkPrimaryExecutionContext`.
3. Translate update operations into concrete index, delete, or noop operations
   before applying them to the shard.
4. Apply index/delete operations on the primary with
   `IndexShard.applyIndexOperationOnPrimary` or the delete equivalent.
5. The primary call uses `UNASSIGNED_SEQ_NO` and the shard's current operation
   primary term. The engine assigns the actual sequence number.
6. Parse the document and prepare an engine operation. If dynamic mappings are
   required, submit a mapping update and retry the item after the relevant
   cluster-state update arrives.
7. Execute the engine operation. The engine result returns `_seq_no`,
   `_primary_term`, version, created/deleted status, failure, and translog
   location.
8. Convert the engine result into the user-facing item response. Successful
   responses carry the assigned sequence number and primary term.
9. Track the highest translog location that must be synced for the bulk request.
10. Return a `WritePrimaryResult` containing the replica request, final response,
    translog location, and primary shard.
11. After the primary operation succeeds, `ReplicationOperation` samples:
    global checkpoint, max seq no of updates/deletes, current replication group,
    and pending replication actions.
12. Replicate the primary result to the sampled replicas and recovery targets.
13. Only after replica dispatch does `WritePrimaryResult.runPostReplicationActions`
    run refresh/fsync behavior through `AsyncAfterWriteAction`.

Ordering matters. Java samples the replication group after the primary write so
recoveries that start during the primary operation still receive the operation.
It samples the global checkpoint before the replication group so replicas do not
learn a checkpoint that is invalid for the sampled group.

## Rust Primary Model Required

A Steelsearch primary implementation must expose an internal operation result
with at least:

- assigned sequence number
- operation primary term
- external version/result version
- create/update/delete/noop result kind
- translog location or equivalent durability marker
- mapping update requirement
- document-level failure with sequence/term when Java would include them

The primary engine must support this sequence:

1. Validate shard is the active primary for the current allocation and primary
   term.
2. Translate user write request into a concrete shard operation.
3. Parse and validate mappings before mutation, with an explicit
   mapping-update-required state.
4. Assign or reserve the operation sequence number using primary semantics.
5. Apply the mutation to the local engine and translog atomically enough that
   the returned durability marker identifies all writes that need fsync.
6. Build the exact replica request from the post-primary operation result, not
   from the original user request.
7. Capture replication-group state after the local primary mutation.
8. Dispatch replicas/recovery targets before completing refresh/fsync response
   work.

## Replica Apply Semantics

The Java replica path is driven from the primary result, not from independent
replica-side write decisions:

1. `ReplicationOperation` builds one proxy request per replication target with
   the target routing, primary routing, sampled global checkpoint,
   `max_seq_no_of_updates_or_deletes`, pending replication actions, the replica
   request, and the primary term.
2. The target node acquires a replica operation permit for the operation primary
   term. During permit acquisition, Java rejects operations from an older term,
   updates the replica global checkpoint, and advances
   `max_seq_no_of_updates_or_deletes`.
3. `TransportShardBulkAction.performOnReplica` iterates the bulk items and reads
   each item's primary response.
4. Failed primary responses with no assigned sequence number are skipped because
   no primary operation was generated.
5. Failed primary responses with an assigned sequence number are applied as a
   replica noop using the primary response sequence number, primary term, and
   failure message. This preserves sequence-number history even for document
   failures that consumed a sequence number.
6. Successful `NOOP` responses are skipped for replication.
7. Successful index/create responses call `IndexShard.applyIndexOperationOnReplica`
   with the primary response id, `_seq_no`, `_primary_term`, version,
   auto-generated timestamp, retry flag, and source payload.
8. Successful delete responses call the delete replica equivalent with the
   primary-assigned `_seq_no`, `_primary_term`, version, and id.
9. Replica operations use `Engine.Operation.Origin.REPLICA`. They do not perform
   primary-side version or optimistic concurrency checks; those decisions have
   already happened on the primary.
10. If the replica is missing a dynamic mapping needed for the operation, Java
    throws `RetryOnReplicaException` and waits for the mapping to arrive via
    cluster state instead of applying a divergent mutation.
11. Each applied replica result advances the local translog location to sync.
    `WriteReplicaResult.runPostReplicaActions` performs refresh/fsync behavior
    through the same async after-write path used by primaries.

The replica contract is deterministic replay of the primary result. A replica
must not reassign sequence numbers, reinterpret conflicts, change versions, or
decide that a successful primary operation is a local noop.

## Rust Replica Model Required

A Steelsearch replica implementation must support:

- operation permits keyed by primary term
- rejection of stale-term replica operations
- global checkpoint update on replica operation receipt
- `max_seq_no_of_updates_or_deletes` advancement
- index/delete replay using primary-assigned sequence number, term, and version
- noop marking for failed primary operations that consumed sequence numbers
- mapping-missing retry instead of divergent local parsing behavior
- replica translog durability marker collection
- post-replication refresh/fsync behavior

The Rust engine API must therefore distinguish primary application from replica
application. Primary application assigns sequence numbers and resolves write
conflicts; replica application accepts the already assigned operation metadata
and replays it exactly.

## Sequence Number, Primary Term, And Version Preservation

Java uses three distinct write metadata domains:

- `_seq_no`: total order assigned by the primary for operations that enter the
  shard history.
- `_primary_term`: the primary epoch that assigned or replayed the operation.
- `_version`: document version used for user-visible versioning and version
  conflict behavior.

The important sentinel values are:

| Value | Java constant | Meaning |
| --- | --- | --- |
| `-2` | `UNASSIGNED_SEQ_NO` | No sequence number assigned yet. Primary operations enter the engine with this value. |
| `-1` | `NO_OPS_PERFORMED` | Checkpoint/max-seq-no initial value. |
| `0` | `UNASSIGNED_PRIMARY_TERM` | No primary term assigned. |
| `-3` | `Versions.MATCH_ANY` | Version check accepts any current version. |
| `-1` | `Versions.NOT_FOUND` | Current document was not found. |
| `-4` | `Versions.MATCH_DELETED` | Write should succeed only if the current document is deleted/not found. |

Primary behavior:

- Incoming primary engine operations must not already have a sequence number.
  Java asserts primary operations arrive with `UNASSIGNED_SEQ_NO`.
- The primary engine generates the sequence number before indexing into Lucene.
- The operation primary term is the shard's current operation primary term.
- Optimistic concurrency checks using `if_seq_no` and `if_primary_term` are
  resolved on the primary before the operation is replicated.
- `VersionType.INTERNAL` increments from the current version or creates version
  `1` when the document is not found.
- `VersionType.EXTERNAL` and `EXTERNAL_GTE` preserve the caller-provided version
  after primary-side conflict checks.
- Successful primary results return the final sequence number, term, and
  version. Document-level failures may also return a sequence number and term if
  the failure happened after the primary consumed a sequence number.

Replica behavior:

- Non-primary engine operations must have an assigned sequence number.
- Replica index/delete operations use the sequence number, primary term, and
  version from the primary response.
- Replica operations must not rerun primary-side version conflict or
  optimistic-concurrency decisions.
- If the same sequence number has already been processed, Java may skip the
  engine mutation while preserving the operation history semantics.
- Stale or out-of-order replica operations are handled through sequence-number
  comparisons, stale-op recording, or skipped engine execution depending on
  recovery/replica state.

Rust compatibility requirements:

- Store `_seq_no`, `_primary_term`, and `_version` as first-class per-document
  metadata.
- Preserve the sentinel values above exactly at the API and wire boundary.
- Separate primary operation input from primary operation result: input has no
  sequence number, result has the primary-assigned sequence number.
- Separate primary conflict resolution from replica replay: replicas accept the
  primary-assigned metadata.
- Persist enough sequence-number history to distinguish already-processed,
  stale, skipped, noop, and normally-applied operations.
- Surface document-level failures with sequence number and term when the primary
  consumed them, so replicas can mark those operations as noops.

## Current Gap

`os-engine` currently models document metadata at the API boundary, but it does
not implement Java-compatible primary or replica sequencing. In particular, it
does not yet provide OpenSearch primary sequence-number assignment, replica
operation replay, version conflict parity, sentinel preservation, replication
request materialization, translog location tracking, mapping update retry state,
global checkpoint interaction, or post-replication refresh/fsync behavior.

Until those contracts exist, Steelsearch must not own Java-cluster primary
shards. Coordinating write routing may forward to Java nodes only behind the
existing write-path safety gate.
