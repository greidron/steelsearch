# Coordination Cluster-Manager Task Gap Inventory

This document narrows the remaining gap inside the backlog item
`Implement cluster-manager task queues, acknowledgments, reroute triggering, node-left handling, cluster blocks, and version or feature gates.`

Replacement profile scope:

- `standalone`
- `secure standalone`
- `external interop`
- `same-cluster peer-node`

This document matters most to `same-cluster peer-node`, but stronger
cluster-manager task semantics are also required for authoritative standalone
metadata and routing mutation.

## Current Evidence

Steelsearch already has small in-process primitives for cluster-manager work:

- `ClusterManagerTaskKind`;
- `ClusterManagerTask`;
- `ClusterManagerTaskQueue`;
- `StandaloneClusterManager`;
- `StandaloneClusterManagerRuntime`.

These primitives are enough for focused routing and shard-lifecycle tests such
as create-index routing, reroute, rebalance, relocation finalization, start
initializing shards, and remove-node.

The current behavior is still development-oriented:

- tasks are kept in an in-memory FIFO queue;
- `process_next_task()` and `process_all_tasks()` apply mutations directly;
- task execution is not tied to authoritative coordination publication rounds;
- acknowledgments are modeled for publication, not for queued cluster-manager
  tasks;
- restart does not recover queued or partially applied cluster-manager work.

## Replacement Blockers

The main blockers are:

- no authoritative queued task state with lifecycle phases;
- no integration between queued work and publication/ack/apply ownership;
- reroute and node-left submission still happens too directly from helpers and
  tests;
- no cluster blocks and version/feature gates around queued mutations;
- no durable recovery semantics for interrupted cluster-manager work.

## Required Tests

- task identity and phase-transition tests;
- publication-derived task acknowledgment and apply-tracking tests;
- reroute/node-left automatic submission ordering tests;
- cluster-block and feature/version-gate reject fixtures;
- restart recovery tests for queued, published, and partially applied work.

## Required Implementation

The remaining work should move in these leaves:

1. introduce an explicit task queue state model with task identity and phase
   tracking;
2. persist interrupted queue state for restart recovery;
3. move reroute and node-left submission behind the queue instead of inline
   helpers;
4. add cluster blocks and version or feature gates around queued mutations;
5. integrate queued work with publication ownership and acknowledgment.

## Required Implementation Order

1. authoritative task-state model;
2. queue persistence and replay;
3. submission ownership for reroute/node-left;
4. queue-level blocks and gates;
5. publication/ack integration.
