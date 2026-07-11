# Coordination Voting Configuration Gap Inventory

This document narrows the remaining gap inside the backlog item
`Add voting-configuration exclusions and joint-consensus style voting updates so reconfiguration does not rely on directly mutating a single flat voter set.`

Replacement profile scope:

- `standalone`
- `secure standalone`
- `external interop`
- `same-cluster peer-node`

This document is primarily about `external interop` and `same-cluster
peer-node`, where reconfiguration must be authoritative and restart-safe.

## Current Evidence

Steelsearch already has a smaller split than before:

- `ClusterCoordinationState.last_accepted_voting_configuration`;
- `ClusterCoordinationState.last_committed_voting_configuration`;
- `PersistedPublicationState` persists both sets;
- `voting_config_exclusions` is explicit coordination state and is persisted;
- discovered joins, including placeholder seed replacement, stage eligible
  nodes as pending voting-configuration additions instead of immediately
  rewriting the authoritative accepted or committed voter sets;
- discovered membership removals stage eligible nodes as pending
  voting-configuration removals instead of immediately rewriting the
  authoritative accepted or committed voter sets;
- quorum checks evaluate the accepted and committed configurations separately
  after exclusions, and publication, direct election, and local-manager liveness
  use that joint quorum helper.
- failed active publication rounds are not promoted to
  `last_completed_publication_round` when a retry starts; only committed active
  rounds move to completed publication state.

Focused tests already pin that split. That means Steelsearch no longer has a
single merged voting set everywhere, but it still does not have OpenSearch-style
reconfiguration semantics.

## Replacement Blockers

The remaining blockers are:

- publication fencing still needs stronger coverage around excluded voters and
  in-flight reconfiguration rounds;
- reconfiguration rollback paths remain bounded.

## Required Tests

- publication fencing tests that honor exclusions and in-flight joint-config
  transitions.

## Required Implementation

The remaining work should move in these leaves:

1. wire publication fencing checks through in-flight joint configuration
   transitions;
2. add targeted tests for reconfiguration commit and rollback behavior.

## Required Implementation Order

1. publication fencing integration;
2. rollback behavior.
