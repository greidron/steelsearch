# Coordination Gateway Persistence Gap Inventory

This document narrows the remaining gap inside the backlog item
`Persist authoritative coordination state and cluster metadata in a gateway layer that survives restart and node loss.`

Replacement profile scope:

- `standalone`
- `secure standalone`
- `external interop`
- `same-cluster peer-node`

This document matters to every profile because gateway durability is the line
between a development snapshot helper and a restart-safe source of truth.

Source anchors:

- Current Steelsearch coordination runtime:
  - [`crates/os-node/src/lib.rs`](/home/ubuntu/steelsearch/crates/os-node/src/lib.rs)
  - [`crates/os-node/src/main.rs`](/home/ubuntu/steelsearch/crates/os-node/src/main.rs)
- Existing coordination planning inventories:
  - [`docs/rust-port/cluster-coordination-gap-inventory.md`](/home/ubuntu/steelsearch/docs/rust-port/cluster-coordination-gap-inventory.md)
  - [`docs/rust-port/coordination-election-gap-inventory.md`](/home/ubuntu/steelsearch/docs/rust-port/coordination-election-gap-inventory.md)
  - [`docs/rust-port/coordination-publication-gap-inventory.md`](/home/ubuntu/steelsearch/docs/rust-port/coordination-publication-gap-inventory.md)
- OpenSearch gateway and metadata references:
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/gateway/GatewayMetaState.java`
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/gateway/MetaStateService.java`
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/CoordinationMetadata.java`

## Current Steelsearch Persistence Shape

Steelsearch already persists two small development-oriented artifacts:

- `PersistedPublicationState` in `coordination-state.json`
- development cluster metadata via `DevelopmentMetadataStore` in `cluster-state.json`

This is enough to restore:

- current term
- last accepted version and state UUID
- elected cluster-manager node id
- accepted/committed voting configuration
- voting configuration exclusions

It is not yet an authoritative gateway layer. The current shape is still a
development persistence helper around startup and repeated publication tests.

## Current Evidence

The repository already proves:

- persisted publication-state replay for development coordination;
- persisted gateway-style metadata artifacts;
- restart exercises around current term, state UUID, voting configuration, and
  selected metadata content;
- a documented split between coordination-state and development cluster
  metadata files.

That is enough to support development restart tests. It is not enough to claim
authoritative gateway durability across restart, corruption, and node loss.

## Replacement Blockers

The gateway blockers are:

- there is still no single authoritative manifest that owns both coordination
  and cluster metadata commit ordering;
- startup ordering is not fully gateway-first across every runtime path;
- authoritative cluster metadata replay is incomplete relative to OpenSearch
  gateway behavior;
- corruption, partial-write, and node-loss coverage is still too shallow for a
  replacement claim.

## What Still Differs From OpenSearch

### Gap Class 1: Single Authoritative Gateway Manifest

Steelsearch persists coordination state and development metadata separately.
OpenSearch persists authoritative node and cluster metadata through gateway
services with explicit load and commit boundaries.

Missing behavior:

- one authoritative gateway-owned manifest for coordination metadata plus
  cluster metadata;
- generation-based commit ordering instead of ad hoc file replacement;
- explicit compatibility and corruption fencing on startup;
- atomic persistence semantics across coordination and cluster metadata.

Required tests:

- truncated/stale manifest startup fencing tests;
- concurrent writer or generation-regression failure-path tests;
- atomicity smoke showing coordination and cluster metadata do not diverge
  after commit.

Required implementation:

- single authoritative manifest with generation ordering;
- commit boundary shared by coordination metadata and cluster metadata;
- corruption and compatibility fencing during load.

Current repo-local ownership baseline:

- [gateway-manifest-ownership.md](/home/ubuntu/steelsearch/docs/rust-port/gateway-manifest-ownership.md)
- [gateway-manifest-ownership-failures.json](/home/ubuntu/steelsearch/tools/fixtures/gateway-manifest-ownership-failures.json)

### Gap Class 2: Restart-Safe Load Ordering

Steelsearch restores persisted publication state in the development startup
path, but the broader runtime still does not have a gateway-first bootstrap
sequence.

Missing behavior:

- gateway load before discovery, publication, and routing mutation;
- startup fencing when persisted coordination metadata is stale, incompatible,
  or corrupted;
- cluster-manager/runtime ownership derived from restored gateway state instead
  of only the in-memory development view.

Required tests:

- gateway-first startup ordering transcript;
- restart with stale/incompatible gateway state reject coverage;
- startup sequencing tests showing transport/REST admission waits for gateway
  restore.

Required implementation:

- gateway load before discovery/publication/routing mutation;
- startup fencing based on restored gateway state;
- runtime ownership derived from restored authoritative metadata.

### Gap Class 3: Authoritative Cluster Metadata Replay

The current persistence layer does not yet restore authoritative cluster
metadata, routing tables, and node-loss-safe cluster state through the same
gateway boundary.

Missing behavior:

- persistent cluster metadata and routing tables under the coordination
  gateway;
- restart replay of authoritative metadata instead of reconstructing from the
  development cluster view;
- authoritative handling of node loss and cluster-state continuity after
  restart.

Required tests:

- restart replay tests that cover routing tables plus cluster metadata together;
- node-loss replay tests showing continuity or explicit fail-closed reject;
- compare artifacts against OpenSearch metadata replay where feasible.

Current repo-local durability compare baseline:

- [durability-compat-profiles.json](/home/ubuntu/steelsearch/tools/fixtures/durability-compat-profiles.json)
- [run-durability-compat.sh](/home/ubuntu/steelsearch/tools/run-durability-compat.sh)

Required implementation:

- persistent routing tables and cluster metadata under the gateway;
- replay pipeline that does not reconstruct from development-only snapshots;
- authoritative node-loss continuity handling.

### Gap Class 4: Durability And Failure Coverage

The current tests cover persisted election metadata replay, but not gateway
durability semantics under restart, corruption, or node loss.

Current repo-local replay baseline:

- [gateway-replay-recovery-policy.md](/home/ubuntu/steelsearch/docs/rust-port/gateway-replay-recovery-policy.md)
- [gateway-replay-restart-probes.json](/home/ubuntu/steelsearch/tools/fixtures/gateway-replay-restart-probes.json)

Current repo-local on-disk compatibility baseline:

- [on-disk-state-upgrade-boundary.md](/home/ubuntu/steelsearch/docs/rust-port/on-disk-state-upgrade-boundary.md)

Missing behavior:

- corruption detection and fail-closed gateway load tests;
- restart tests covering coordination plus cluster metadata replay together;
- node-loss and partial-write scenarios against the persisted gateway state.

Required tests:

- corruption detection and fail-closed startup tests;
- partial-write recovery or reject tests;
- node-loss durability tests tied to persisted gateway artifacts.

Required implementation:

- explicit corruption-fencing logic;
- recovery/reject policy for partial writes;
- durability contract documented at the manifest/file-family level.

## Recommended Execution Order

1. capture the current split persistence helpers and gateway gaps explicitly in
   the backlog;
2. introduce a gateway-owned authoritative manifest for coordination metadata;
3. move startup restore and fencing behind that gateway boundary;
4. persist and replay authoritative cluster metadata and routing state through
   the same layer;
5. add corruption, restart, and node-loss coverage for the gateway path.

## Required Implementation

For backlog purposes, the minimum implementation slices from this document are:

1. authoritative manifest ownership and generation ordering;
2. gateway-first startup restore and fencing;
3. authoritative cluster metadata and routing replay;
4. corruption, partial-write, restart, and node-loss durability coverage.
