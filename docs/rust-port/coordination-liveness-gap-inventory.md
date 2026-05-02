# Coordination Liveness Gap Inventory

Replacement profile scope:

- `standalone`
- `secure standalone`
- `external interop`
- `same-cluster peer-node`

This document is primarily about `external interop` and `same-cluster
peer-node`, because authoritative liveness is what turns coordination
primitives into a fault-tolerant cluster runtime.

## Current Evidence

Steelsearch already has a few pieces of the eventual fault-detection path:

- `ProductionMembershipState` can track `Live`, `Leaving`, and `Failed` node
  states, compute quorum, and surface readiness blockers;
- `ClusterCoordinationState` already fences stale publication, routing, and
  replayed membership updates once a newer authoritative state exists;
- election retry now has bounded backoff and can use live transport-backed
  pre-vote and election-vote collection.

Those pieces are necessary, but they are not a real leader or follower
liveness runtime.

## Replacement Blockers

The main blockers are:

- no explicit node-owned liveness state with deadlines, counters, and fencing
  flags;
- no transport-backed leader and follower check actions;
- no periodic liveness scheduler with thresholds and reset behavior;
- no automatic re-election or quorum-loss fencing driven by liveness failure.

## Required Tests

- leader/follower liveness-state transition tests;
- leader-check and follower-check transport fixtures;
- periodic scheduling cadence and failure-threshold tests;
- liveness failure triggering re-election and isolated-leader fencing;
- restart replay of fenced/degraded liveness state where applicable.

## Required Implementation

The remaining work should move in these leaves:

1. explicit node-owned liveness state with failure counters and deadlines;
2. transport-backed leader/follower check wire actions;
3. periodic scheduler and threshold model;
4. re-election and quorum-loss fencing driven by liveness runtime state.

## Required Implementation Order

1. explicit liveness state;
2. transport-backed leader/follower checks;
3. periodic scheduling and thresholds;
4. re-election and quorum-loss fencing.
