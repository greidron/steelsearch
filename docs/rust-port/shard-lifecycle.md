# Shard Allocation And Lifecycle Model

This document defines the Rust-side model Steelsearch must preserve before it
can participate as a Java OpenSearch-compatible data node.

The current implementation is still observational. `os-cluster-state` decodes
the routing table into typed structs, and the `steelsearch` daemon (via the
`os-node` crate) uses that state for safe coordinating-client routing.
Steelsearch must not make allocation decisions or own Java-cluster shards until
the transition rules below are implemented and validated against Java
OpenSearch.

## Typed Surface

`os-cluster-state` already exposes the routing model needed by later data-node
work:

- `RoutingTable`
- `IndexRoutingTable`
- `IndexShardRoutingTable`
- `ShardRouting`
- `ShardRoutingState`
- `RecoverySourceType`
- `AllocationId`
- `UnassignedInfo`

These types are the compatibility boundary for decoded Java cluster state. Any
runtime data-node model should either reuse these types or convert from them
without losing fields that affect allocation, recovery, primary ownership, or
write safety.

## Shard States

Steelsearch must model the OpenSearch shard states as distinct lifecycle states:

| State | Meaning | Data-node implication |
| --- | --- | --- |
| `Unassigned` | The shard has no active owner. | No reads or writes may be served. Allocation explain data must come from `UnassignedInfo`. |
| `Initializing` | A target node is recovering or creating the shard. | The target may receive recovery traffic, but must not serve normal search/write traffic as started. |
| `Started` | The shard copy is active. | Search routing may target it. Write routing may target it only when it is the primary and write-path safety is validated. |
| `Relocating` | A started shard is moving to another node. | The source remains active, while relocation metadata must be preserved for handoff and recovery semantics. |
| `Splitting` | A shard is participating in split-shard lifecycle. | Treat as specialized recovery/allocation state; do not serve it as a generic started target. |

Search routing may use `Started` shard copies. Write routing must use only a
`Started` primary, and only after the write-path validation gate is enabled.

## Allocation Identity

`AllocationId` is not an implementation detail. It links cluster-state routing,
in-sync allocation ids, recovery decisions, and replica safety.

Steelsearch must preserve:

- `id`: the active allocation identity for a shard copy.
- `relocation_id`: the paired allocation identity during relocation.
- `split_child_allocation_ids_count`: split lifecycle marker.
- `parent_allocation_id`: split lifecycle parent identity.

Rules:

- A started shard without an allocation id is not safe for mixed-cluster data
  ownership.
- Relocation must keep source and target allocation ids distinct.
- In-sync allocation ids from index metadata must be compared with shard routing
  allocation ids before accepting replica write participation.

## Recovery Sources

The recovery source tells a node how a shard copy becomes usable:

| Recovery source | Required interpretation |
| --- | --- |
| `EmptyStore` | Brand-new primary creation. Safe only through cluster-manager allocation. |
| `ExistingStore` | Local store recovery. Requires store compatibility and history checks. |
| `Peer` | Recovery from another shard copy. Requires transport recovery protocol support. |
| `Snapshot` | Restore from repository snapshot metadata. Requires repository and snapshot format support. |
| `LocalShards` | Local-shard based recovery, used by operations such as shrink/split. |
| `RemoteStore` | Recovery from OpenSearch remote store metadata. Requires remote store compatibility. |
| `InPlaceSplitShard` | Split-shard recovery path. Requires split metadata and routing validation. |

Current Steelsearch behavior must stay read-only for all recovery sources. A
future data-node implementation must fail closed when it sees a recovery source
whose storage, history, or transport protocol is not implemented.

## Routing Transitions

The minimum transition model is:

- `Unassigned -> Initializing`: cluster-manager allocation selected a target
  node and recovery source.
- `Initializing -> Started`: recovery completed and the allocation id is valid.
- `Started -> Relocating`: cluster-manager selected a relocation target.
- `Relocating -> Started`: relocation completed; source and target routing are
  updated consistently.
- `Started -> Unassigned`: failure, close, delete, or allocation removal.
- `Initializing -> Unassigned`: recovery failed or allocation was cancelled.
- `Started -> Splitting` and `Splitting -> Started`: split lifecycle only, with
  parent/child allocation metadata preserved.

Illegal transitions for Steelsearch data-node participation:

- Serving search from `Initializing`, `Unassigned`, or `Splitting` shards.
- Serving writes from any non-primary or non-`Started` shard.
- Treating a missing allocation id as safe for primary or replica ownership.
- Accepting a relocation or split transition without preserving allocation id
  relationships.
- Recovering from `ExistingStore`, `Peer`, `Snapshot`, `RemoteStore`, or
  `InPlaceSplitShard` before the corresponding recovery protocol is validated.

## Validation Work Still Required

## Java OpenSearch Comparison

This comparison was checked against local Java OpenSearch sources under
`../OpenSearch/server/src/main/java/org/opensearch/cluster/routing`.

### State Encoding

Rust `os-cluster-state` matches Java `ShardRoutingState` byte values:

| Java value | Java state | Rust state |
| --- | --- | --- |
| `1` | `UNASSIGNED` | `Unassigned` |
| `2` | `INITIALIZING` | `Initializing` |
| `3` | `STARTED` | `Started` |
| `4` | `RELOCATING` | `Relocating` |
| `5` | `SPLITTING` | `Splitting` |

The important behavioral difference is helper semantics. Java `active()` is
true for `STARTED`, `RELOCATING`, and `SPLITTING`; Steelsearch coordinating
search routing currently targets only `Started` shards. That is intentionally
stricter for coordinating-only safety, but a future data-node model must treat
the relocating source as active for Java parity. `Splitting` must remain a
specialized lifecycle state rather than a generic search/write target until its
engine behavior is implemented.

### Recovery Source Encoding

Rust `RecoverySourceType` matches Java `RecoverySource.Type` ordinals:

| Java ordinal | Java type | Rust type |
| --- | --- | --- |
| `0` | `EMPTY_STORE` | `EmptyStore` |
| `1` | `EXISTING_STORE` | `ExistingStore` |
| `2` | `PEER` | `Peer` |
| `3` | `SNAPSHOT` | `Snapshot` |
| `4` | `LOCAL_SHARDS` | `LocalShards` |
| `5` | `REMOTE_STORE` | `RemoteStore` |
| `6` | `IN_PLACE_SPLIT_SHARD` | `InPlaceSplitShard` |

Matching the enum value is necessary but not sufficient for data-node
compatibility. Each non-empty-store source implies a separate recovery protocol
or storage contract that Steelsearch does not implement yet.

### Allocation Identity

Java creates allocation ids through `AllocationId.newInitializing`,
`newRelocation`, `newTargetRelocation`, `finishRelocation`, and
`cancelRelocation`. The Rust typed shape preserves the same fields, including
the transient `relocation_id` pair used to link a relocating source with its
initializing target.

The key parity requirement is that relocation uses two allocation ids:

- Source: keeps `id` and receives a new `relocation_id`.
- Target: uses the source `relocation_id` as its `id` and points back to the
  source `id`.
- Completion: target finishes relocation and keeps its target `id`.
- Cancellation: source clears `relocation_id`.

### Transition Behavior

Java `RoutingNodes` applies the core transitions this model describes:

- `initializeShard`: `Unassigned -> Initializing` and adds recovery tracking.
- `relocateShard`: `Started -> Relocating`, then creates the target
  `Initializing` relocation shard.
- `startShard`: `Initializing -> Started`; if the shard is a relocation target,
  Java removes the relocation source. If the started shard is a relocated
  primary, Java also reinitializes in-flight replica recoveries because their
  recovery source changed.
- `failShard`: failure handling is broader than the minimal Rust transition
  list. Primary failure can fail initializing replicas, active primary failure
  can promote an active replica, relocation source failure can remove or
  rewrite its target, and relocation target failure cancels the source
  relocation.

The Rust model is therefore correct as a decoded cluster-state surface, but it
is incomplete as an allocator or data-node lifecycle engine. Before Steelsearch
owns shards in a mixed cluster, it needs Java-parity tests for relocation source
activity, relocation target completion, primary promotion, replica
reinitialization, and failure side effects.

## Validation Work Still Required

The next validation step is fixture and integration coverage for:

- Cluster-state diffs that exercise allocation, relocation, unassignment, and
  split transitions.
- Java `active()` parity for relocating sources in any future data-node routing
  path.
- Allocation id pairing across relocation start, completion, and cancellation.
- Recovery-source-specific routing invariants for each implemented recovery
  protocol.
