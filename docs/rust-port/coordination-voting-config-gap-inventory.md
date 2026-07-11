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
- quorum checks use the accepted/committed union after exclusions.

Focused tests already pin that split. That means Steelsearch no longer has a
single merged voting set everywhere, but it still does not have OpenSearch-style
reconfiguration semantics.

## Replacement Blockers

The remaining blockers are:

- accepted and committed sets do not yet form a true joint configuration;
- publication commit and fencing are not fully wired through joint-config
  transition semantics;
- reconfiguration rollback and removal paths remain bounded.

## Required Tests

- removal-path tests proving discovered membership loss does not silently
  rewrite the authoritative voter set;
- publication/election/liveness tests that honor exclusions and joint-config
  transitions.

## Required Implementation

The remaining work should move in these leaves:

1. introduce joint-consensus quorum helpers across accepted and committed
   configurations;
2. wire publication ownership, commit, and fencing checks through those joint
   configuration helpers;
3. add targeted tests for reconfiguration commit, removal, and
   rollback behavior.

## Required Implementation Order

1. joint-consensus quorum helpers;
2. publication/election/liveness integration;
3. removal and rollback behavior.
