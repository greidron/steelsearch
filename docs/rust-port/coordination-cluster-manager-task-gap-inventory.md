# Coordination Cluster-Manager Task Gap Inventory

This document narrows the remaining gap inside the backlog item
`Implement cluster-manager task queues, acknowledgments, reroute triggering, node-left handling, cluster blocks, and version or feature gates.`

Source anchors:

- Current Steelsearch coordination and cluster-manager runtime:
  - [`crates/os-node/src/lib.rs`](/home/ubuntu/steelsearch/crates/os-node/src/lib.rs)
  - [`crates/os-node/src/main.rs`](/home/ubuntu/steelsearch/crates/os-node/src/main.rs)
- Related coordination planning inventories:
  - [`docs/rust-port/cluster-coordination-gap-inventory.md`](/home/ubuntu/steelsearch/docs/rust-port/cluster-coordination-gap-inventory.md)
  - [`docs/rust-port/coordination-election-gap-inventory.md`](/home/ubuntu/steelsearch/docs/rust-port/coordination-election-gap-inventory.md)
  - [`docs/rust-port/coordination-publication-gap-inventory.md`](/home/ubuntu/steelsearch/docs/rust-port/coordination-publication-gap-inventory.md)

## Current Steelsearch Task Execution Shape

Steelsearch already has small in-process primitives for cluster-manager work:

- `ClusterManagerTaskKind`
- `ClusterManagerTask`
- `ClusterManagerTaskQueue`
- `StandaloneClusterManager`
- `StandaloneClusterManagerRuntime`

These primitives are enough for focused routing and shard-lifecycle tests:

- create-index routing
- reroute
- rebalance
- finalize relocations
- start initializing shards
- remove node

The current behavior is still development-oriented:

- tasks are kept in an in-memory FIFO queue;
- `process_next_task()` and `process_all_tasks()` apply mutations directly;
- task execution is not tied to authoritative coordination publication rounds;
- acknowledgments are modeled for publication, not for queued cluster-manager tasks;
- restart does not recover queued or partially applied cluster-manager work.

## What Still Differs From OpenSearch

### Gap Class 1: Authoritative Queued Task State

Steelsearch has a queue container, but not an authoritative task-state model.

Missing behavior:

- task identity beyond source strings and enum variants;
- queued, executing, acknowledged, failed, and applied task phases;
- task ownership by the elected cluster-manager term and publication version;
- replay fencing so old leaders cannot continue applying stale queued work.

### Gap Class 2: Publication And Acknowledgment Integration

Current queued work mutates routing and metadata inline. OpenSearch ties
cluster-manager mutations to publication and follower acknowledgment.

Missing behavior:

- task execution that produces a new cluster-state publication round;
- follower acknowledgment/apply tracking per task-derived state update;
- explicit distinction between task accepted, state published, and state
  applied;
- retry and recovery behavior for interrupted task publication.

### Gap Class 3: Reroute And Node-Left Work Submission

Steelsearch can run reroute and node removal tasks, but those paths are still
called directly from helpers and tests.

Missing behavior:

- automatic submission of reroute work when allocation state changes;
- automatic submission of node-left tasks from liveness and discovery changes;
- cluster-manager-owned sequencing between node removal, reroute, and shard
  recovery tasks;
- restart-safe bookkeeping for interrupted reroute or node-left processing.

### Gap Class 4: Cluster Blocks And Version Or Feature Gates

The queue does not currently fence unsupported mutations.

Missing behavior:

- cluster blocks that reject writes or metadata mutation under unsafe states;
- feature-gate checks before queuing or applying unsupported mutations;
- version compatibility checks for queued mutations across mixed-runtime or
  restart scenarios;
- fail-closed behavior when queued work targets unavailable features.

### Gap Class 5: Durable Recovery Coverage

Current tests exercise in-process queue behavior, but not restart recovery.

Missing behavior:

- persisted queue recovery state;
- restart replay for queued-but-unpublished work;
- restart fencing for published-but-unacknowledged task results;
- multi-node crash and node-left recovery coverage tied to queued work.

## Recommended Execution Order

1. capture the current one-shot task execution shape and its missing durable
   boundaries explicitly in the backlog;
2. introduce an explicit task queue state model with task identity and phase
   tracking;
3. persist interrupted queue state for restart recovery;
4. move reroute and node-left submission behind the queue instead of inline
   helpers;
5. add cluster blocks and version or feature gates around queued mutations.
