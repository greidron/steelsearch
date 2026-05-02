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
- quorum checks, election, publication ownership, and liveness still read the
  accepted set directly.

Focused tests already pin that split. That means Steelsearch no longer has a
single merged voting set everywhere, but it still does not have OpenSearch-style
reconfiguration semantics.

## Replacement Blockers

The main blockers are:

- no voting-config exclusion state;
- accepted and committed sets do not yet form a true joint configuration;
- membership changes still mutate voting state too directly;
- runtime users still mostly read only the accepted set.

## Required Tests

- exclusion add/remove/replay tests;
- joint-consensus quorum tests across accepted and committed sets;
- join/remove paths proving discovered membership does not silently rewrite the
  authoritative voter set;
- publication/election/liveness tests that honor exclusions and joint-config
  transitions.

## Required Implementation

The remaining work should move in these leaves:

1. add explicit voting-config exclusion state and persist it;
2. stop mutating accepted voters directly from `join_peer(...)`;
3. introduce joint-consensus quorum helpers across accepted and committed
   configurations;
4. wire publication ownership, commit, and fencing checks through those joint
   configuration helpers;
5. add targeted tests for exclusion, reconfiguration proposal, commit, and
   rollback behavior.

## Required Implementation Order

1. exclusion state;
2. authoritative membership-to-voter separation;
3. joint-consensus quorum helpers;
4. publication/election/liveness integration.
