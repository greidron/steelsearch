# Coordination Task Queue Gap Inventory

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

Authoritative coordination gaps still open:

1. Queue state is in-memory only. There is no persisted queued, in-flight,
   acknowledged, failed, or replayable task state.
2. Task execution is one-shot. Publication ownership, follower acknowledgements,
   and apply tracking are not attached to task lifecycle.
3. Reroute triggering and node-left handling mutate manager state directly after
   dequeue instead of flowing through committed cluster-manager publications.
4. Cluster blocks and version/feature gates are not evaluated as preconditions
   on queued mutations.
5. Restart recovery cannot distinguish an idle manager from interrupted task
   publication.
6. Multi-node crash, restart, quorum-loss, and partition behavior for queued
   mutations is not covered against OpenSearch-compatible expectations.

Implementation order implied by the current code:

1. Add explicit task queue state with queued/in-flight/acked/failed bookkeeping.
2. Persist that queue state in the gateway layer.
3. Route reroute and node-left transitions through the persisted queue model.
4. Gate queued mutations behind cluster blocks and version/feature checks.
5. Add multi-node recovery and fault-path coverage around the queue runtime.
