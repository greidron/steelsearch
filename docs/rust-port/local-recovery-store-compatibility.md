# Local Recovery And Store Compatibility

This document defines the staged local recovery model for Steelsearch. It
separates Rust-native Tantivy recovery from Java OpenSearch mixed-cluster store
compatibility.

The current Steelsearch engine is Rust-native and Tantivy-backed. It is not
Lucene segment compatible and must not claim Java OpenSearch local-store
recovery compatibility.

## Java Store Recovery Shape

Checked Java OpenSearch sources:

- `IndexShard.startRecovery`
- `IndexShard.recoverLocallyUpToGlobalCheckpoint`
- `StoreRecovery`
- `Store`
- `Translog`

Java store recovery dispatches by routing recovery source:

- `EMPTY_STORE` and `EXISTING_STORE`: recover from local store.
- `REMOTE_STORE`: recover from remote store metadata/files.
- `PEER`: start peer recovery over the recovery transport protocol.
- `SNAPSHOT`: recover from repository or searchable snapshot path.
- `LOCAL_SHARDS`: recover by composing local shard snapshots for shrink/split.

For local store recovery, Java validates corruption, reads the last committed
segment info, decides whether an index should already exist, creates an empty
store for new primaries, bootstraps history/translog metadata when required,
finds safe commits, and may replay local translog operations up to the global
checkpoint. Recovery completes only after the shard has consistent commit,
translog, checkpoint, and history metadata.

## Tantivy Local Recovery Flow

Steelsearch's Rust-native recovery flow should be narrower:

1. Resolve shard identity from decoded cluster state: index UUID/name, shard id,
   allocation id, primary flag, recovery source, and expected primary term.
2. Open the Steelsearch shard directory, not an OpenSearch/Lucene shard
   directory.
3. Read a Steelsearch manifest file containing:
   - engine format id and version
   - index UUID and shard id
   - allocation id that wrote the store
   - primary term
   - max sequence number
   - local checkpoint
   - committed generation
   - translog generation and UUID or Rust-native equivalent
   - schema/mapping hash
4. Validate the manifest against current cluster state. Mismatched index UUID,
   shard id, allocation id, engine format id, or incompatible schema hash must
   fail closed.
5. Open Tantivy index metadata and verify all referenced segment files exist and
   pass checksum validation.
6. Open the Rust-native translog or operation log. Validate its UUID/generation
   against the manifest.
7. Determine the safe recovery point:
   - if no manifest exists and recovery source is `EmptyStore`, create a new
     empty shard store with `max_seq_no = -1` and `local_checkpoint = -1`;
   - if no manifest exists for `ExistingStore`, fail recovery;
   - if a manifest exists, recover from the committed generation and replay
     operations after the local checkpoint.
8. Replay local operations in sequence-number order. Each replayed operation
   must preserve `_seq_no`, `_primary_term`, `_version`, and result kind.
9. Rebuild in-memory document maps, sequence-number trackers, version state, and
   refresh visibility from the recovered store.
10. Verify after replay that local checkpoint and max sequence number match the
    recovered operation history.
11. Mark the shard recovered locally but do not mark it `Started` until the
    cluster-state lifecycle transition confirms recovery completion.

## Supported Recovery Sources For Rust-Native Store

Initial Rust-native local recovery should support only:

- `EmptyStore`: create a new empty Tantivy-backed shard owned by Steelsearch.
- `ExistingStore`: reopen a Steelsearch-created Tantivy shard when the manifest
  matches cluster state and engine format.

It must reject:

- Java OpenSearch Lucene directories.
- `Peer` recovery, until the recovery transport protocol is implemented.
- `Snapshot`, until repository snapshot format support exists.
- `RemoteStore`, until remote-store metadata and file contracts are implemented.
- `LocalShards` and `InPlaceSplitShard`, until split/shrink metadata and
  segment composition semantics are implemented for the Rust engine.

## Mixed-Cluster Recovery Requirements

Mixed-cluster recovery means a Java OpenSearch node and a Steelsearch node can
act as peer recovery source or target for the same index shard. The recovery
contract is broader than "send bytes over the transport layer"; the bytes must
represent Java-compatible store metadata, segment files, translog operations,
sequence-number state, retention leases, and mapping state.

Required transport actions and request types:

- Implement the internal peer recovery actions used by Java nodes:
  `START_RECOVERY`, file info, file chunk, clean files, prepare translog,
  translog operations, finalize recovery, and primary-context handoff for
  relocation.
- Encode and decode the Java wire forms for `StartRecoveryRequest`,
  `RecoveryFilesInfoRequest`, `RecoveryFileChunkRequest`,
  `RecoveryCleanFilesRequest`,
  `RecoveryPrepareForTranslogOperationsRequest`,
  `RecoveryTranslogOperationsRequest`, `RecoveryFinalizeRecoveryRequest`, and
  `RecoveryResponse`.
- Preserve Java cancellation, retry, recovery reestablishment, chunking, and
  concurrency semantics, because recoveries can be interrupted and resumed while
  allocation state is still changing.

Required store and file compatibility:

- Produce and consume Java `Store.MetadataSnapshot` and `StoreFileMetadata`
  values, including file name, length, checksum, written-by version, hash, and
  commit metadata.
- Support Java recovery diff behavior: a source must compare source metadata
  against the target snapshot and identify identical, different, and missing
  files by Java checksum and length rules.
- Preserve commit user data used by recovery and sequence-number safety, such
  as translog UUID, local checkpoint, maximum sequence number, history UUID, and
  safe-commit identity.
- Accept Java file chunks as a target and expose files that a Java source or
  target can later open. A Tantivy segment is not a Lucene segment, so a
  Rust-native Tantivy shard cannot be a compatible peer recovery source or
  target for a Java Lucene shard without a Lucene-compatible store layer.

Required translog and history compatibility:

- Encode and decode Java `Translog.Operation` variants exactly enough for peer
  recovery, including index/delete/no-op payloads, source bytes, routing,
  sequence number, primary term, version, and operation metadata.
- Apply recovered operations with peer-recovery semantics, preserving
  `_seq_no`, `_primary_term`, `_version`, local checkpoint advancement, and
  idempotent duplicate handling.
- Track and apply `startingSeqNo`, `trimAboveSeqNo`, global checkpoint,
  max-seen auto-id timestamp, max seq no of updates or deletes, and total
  translog operation counts.
- Receive and persist retention leases before replaying operations, matching
  Java's requirement that history retention is updated before phase2 operations
  are applied.

Required shard lifecycle and cluster-state behavior:

- Only advertise data-node allocation eligibility for recovery sources that the
  Steelsearch node can satisfy.
- Validate target allocation id, recovery source, primary term, shard routing,
  and current shard state before accepting a recovery.
- Transition through the same observable recovery states as Java
  (`INITIALIZING` / `RECOVERING` to `STARTED`) and report failures in a form the
  cluster manager can use for reroute decisions.

Required mapping and index compatibility:

- Honor the mapping version supplied with translog operations. If the target
  mapping is behind, recovery must wait for the mapping update and retry rather
  than applying operations under an older schema.
- Match Java analyzer, mapping, stored source, routing, nested document,
  document id, and versioning behavior for replayed operations.

Required non-peer recovery compatibility:

- Snapshot recovery requires OpenSearch repository metadata and Lucene snapshot
  file compatibility.
- Remote-store recovery requires OpenSearch remote segment and remote translog
  metadata compatibility.
- Local-shards recovery, shrink, split, and clone paths require composing
  source shard contents in the same store format.

Until these requirements are implemented, Steelsearch should not join a Java
OpenSearch cluster as a general data node for existing Lucene-backed shards. It
may only join safely if allocation is constrained to roles and indices whose
recovery source and store format are explicitly supported.

## Compatibility Decision

Mixed-cluster data-node support requires a Lucene-compatible shard store, not
just a compatible recovery transport implementation.

Decision:

- Use a JVM Lucene/OpenSearch bridge for mixed-cluster data-node compatibility.
- Keep Tantivy as a Rust-native engine format that is eligible only for
  Steelsearch-owned indices whose allocation and recovery paths never require a
  Java node to open the shard store.
- Treat pure Rust Lucene file-format compatibility as a separate long-term
  engine project, not as the default path for the current data-node milestone.

Why the JVM bridge is the practical requirement:

- Java peer recovery uses `Store.MetadataSnapshot`, `StoreFileMetadata`,
  `SegmentInfos`, Lucene checksums, Lucene commit user data, and translog UUID
  metadata as part of the recovery contract.
- After recovery, a Java node may need to open the shard through Lucene APIs.
  File names and byte transfer alone are insufficient if the files are Tantivy
  segments or if commit metadata is not readable by Lucene.
- Segment replication, remote store, snapshots, shrink/split, corruption
  checks, and safe commit selection all assume Lucene-compatible directory and
  commit semantics.
- Reimplementing enough Lucene in Rust would mean matching Lucene codecs,
  postings, doc values, stored fields, norms, points, live docs, segment
  metadata, commit metadata, checksum validation, and OpenSearch's translog and
  sequence-number side data. That is effectively a second Lucene engine
  implementation.

Bridge boundary:

- For Java-compatible indices, route shard store operations, segment metadata,
  recovery file handling, Lucene commit handling, and translog persistence
  through the JVM bridge.
- For Rust-native Tantivy indices, reject Java Lucene peer recovery and expose
  allocation rules that prevent Java nodes from receiving those shards.
- Do not translate Tantivy segments into Lucene files during recovery. If such
  translation is ever needed, it should be modeled as reindexing into a Lucene
  shard, not as peer recovery of an existing shard.

This means the transport-layer work remains necessary but not sufficient. The
transport can move recovery messages, but the mixed-cluster data-node promise is
only valid when the target store and engine behind those messages are
Lucene/OpenSearch compatible.

## Current Gap

`os-engine-tantivy` currently keeps documents in memory and assigns simple
sequence numbers. It does not yet persist a manifest, Tantivy segment metadata,
translog boundaries, local checkpoint, global checkpoint, allocation id, or
schema hash. Therefore it can demonstrate API behavior, but it cannot yet
recover a shard after restart or participate in OpenSearch allocation.
