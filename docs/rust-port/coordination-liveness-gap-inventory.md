# Coordination Liveness Gap Inventory

## Current Steelsearch Primitives

Steelsearch already has a few pieces of the eventual fault-detection path:

- `ProductionMembershipState` can track `Live`, `Leaving`, and `Failed` node
  states, compute quorum, and surface readiness blockers.
- `ClusterCoordinationState` already fences stale publication, routing, and
  replayed membership updates once a newer authoritative state exists.
- election retry now has bounded backoff and can use live transport-backed
  pre-vote and election-vote collection.

Those pieces are necessary, but they are not a real leader or follower
 liveness runtime.

## What Is Still Missing

### Gap Class 1: Explicit Liveness State

There is no node-owned state that records:

- last successful leader check per follower;
- last successful follower check per leader;
- consecutive check failures;
- lease or heartbeat deadlines;
- whether the local node is currently fenced because quorum was lost.

Without that state, Steelsearch cannot explain why a node was declared dead or
why re-election was triggered.

### Gap Class 2: Wire-Level Leader And Follower Checks

Transport-backed discovery, pre-vote, and election vote now exist, but liveness
 traffic does not.

Missing behavior:

- explicit transport actions for leader checks;
- explicit transport actions for follower checks;
- request/response models that carry term, leader identity, and observed
  cluster-manager state;
- live TCP exchange helpers and tests for those checks.

### Gap Class 3: Runtime Scheduling And Failure Thresholds

The daemon does not yet own a periodic liveness loop.

Missing behavior:

- periodic scheduling for leader and follower checks;
- bounded retry windows and failure thresholds;
- membership status transitions driven by repeated check failure instead of
  manual `mark_failed(...)` calls only;
- cancellation or reset when leadership changes.

### Gap Class 4: Safe Re-Election And Quorum-Loss Fencing

Election can now collect live votes, but there is still no automatic trigger
 from liveness failure.

Missing behavior:

- term bump and re-election when a leader or follower liveness check fails past
  threshold;
- old leader self-fencing on quorum loss;
- follower fencing when the observed leader term regresses or disappears;
- daemon-owned restart behavior that restores liveness-related fencing state
  from authoritative coordination metadata.

## Recommended Execution Order

1. add explicit leader/follower liveness state and failure-threshold modeling;
2. add transport-framed leader and follower check wire actions;
3. execute those checks over live TCP transport;
4. wire periodic liveness scheduling into the daemon-owned coordination runtime;
5. trigger safe re-election and quorum-loss fencing from that runtime state.
