# Coordination Task Queue Gap Inventory

Replacement profile scope:

- `standalone`
- `secure standalone`
- `external interop`
- `same-cluster peer-node`

This document matters most to `same-cluster peer-node`, but even
`secure standalone` replacement claims need stronger queue ownership and restart
behavior than the current development runtime provides.

## Current Evidence

Current task-queue-related runtime is split between:

- `StandaloneClusterManager` in [crates/os-node/src/lib.rs](/home/ubuntu/steelsearch/crates/os-node/src/lib.rs)
  with an in-memory `ClusterManagerTaskQueue`;
- `StandaloneClusterManagerRuntime`, which executes popped tasks immediately on
  one of two local execution pools;
- ad hoc routing and metadata mutation helpers that directly change manager
  state once a task is dequeued;
- REST surfaces such as `GET /_cluster/pending_tasks`, which currently expose a
  development-only pending-task view rather than OpenSearch-compatible
  publication-backed task tracking.

What exists now:

- queued task submission via `submit_task(...)`;
- immediate dequeue-and-apply processing via `process_next_task(...)` /
  `process_all_tasks(...)`;
- task kinds for create-index routing, remove-node, reroute, rebalance, and
  relocation finalization;
- inline reroute and node-left effects once a task is applied;
- basic pending-task REST visibility.

## Replacement Blockers

Authoritative coordination gaps still open:

1. queue state is in-memory only;
2. task execution is one-shot and not tied to publication/apply ownership;
3. reroute triggering and node-left handling still mutate manager state too
   directly after dequeue;
4. cluster blocks and version/feature gates are not preconditions on queued
   mutations;
5. restart recovery cannot distinguish idle manager state from interrupted task
   publication;
6. multi-node crash, restart, quorum-loss, and partition behavior for queued
   mutations is not covered against OpenSearch-compatible expectations.

## Required Tests

- queued/in-flight/acked/failed phase-transition tests;
- restart replay tests for queued-but-unpublished and published-but-unacked
  work;
- reroute/node-left submission ordering and retry transcripts;
- cluster-block and version/feature-gate reject fixtures;
- multi-node crash/restart/quorum-loss coverage tied to queued mutations.

## Required Implementation

Implementation order implied by the current code:

1. add explicit task queue state with queued/in-flight/acked/failed
   bookkeeping;
2. persist that queue state in the gateway layer;
3. route reroute and node-left transitions through the persisted queue model;
4. gate queued mutations behind cluster blocks and version/feature checks;
5. add multi-node recovery and fault-path coverage around the queue runtime.

## Required Implementation Order

1. authoritative queued task state;
2. gateway-backed queue persistence and replay;
3. manager-owned reroute/node-left sequencing;
4. blocks and feature/version gates;
5. multi-node queue failure coverage.
