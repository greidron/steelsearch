# Coordination Multi-Node Failure Test Gap Inventory

This inventory captures the current coordination test surface after discovery,
election, liveness, publication, gateway recovery, and cluster-manager task
queue work landed. The remaining gap is not a missing primitive so much as a
missing multi-node failure matrix that proves the runtime behaves like Java
OpenSearch under crash, restart, quorum-loss, and partition conditions.

## Current Coverage

The current Rust test surface already covers focused single-process primitives:

- gateway startup restore and fail-closed replay of persisted coordination and
  metadata state;
- pre-vote, election vote, publication, leader check, follower check, and
  queue wire round trips over live TCP sockets;
- periodic liveness checks, quorum-loss fencing, and safe re-election within
  the development coordination runtime;
- restart replay of publication rounds, fault-detection state, and task queue
  recovery bookkeeping.

Representative tests live in:

- `crates/os-node/src/main.rs`
- `crates/os-node/src/lib.rs`

Those tests validate components in isolation or with a single local runtime
driving synthetic peers. They do not yet prove multi-node behavior across
independent daemons with failure and recovery sequences.

## Missing Coverage

The following multi-node behavior is still unverified against Java
OpenSearch-shaped expectations:

1. cluster-manager crash and follower crash while publication or queued work is
   in flight;
2. restart replay where a recovered node must honor persisted coordination and
   task queue state before rejoining quorum;
3. quorum-loss behavior across a real multi-node topology, including fencing of
   an isolated manager and recovery after quorum is restored;
4. network partition behavior where different node subsets keep running long
   enough to prove no unsafe dual-manager progression happens;
5. heal/rejoin behavior after partition, including queued reroute and
   publication recovery.

## Recommended Task Breakdown

Execute the remaining coverage work in this order:

1. add multi-node crash/restart replay tests around persisted coordination and
   queued publication/task state;
2. add quorum-loss fencing tests for isolated manager and isolated follower
   subsets;
3. add network-partition and heal tests that verify no unsafe publication or
   election progress happens in minority partitions;
4. add queue-aware recovery assertions so interrupted reroute/node-left work is
   replayed or fenced explicitly after restart/heal.

## Test Harness Direction

Prefer reusing the existing daemon integration harness in
`crates/os-node/src/main.rs` rather than inventing another fake coordination
driver. The missing value is concurrent daemon behavior, not more isolated unit
coverage.
