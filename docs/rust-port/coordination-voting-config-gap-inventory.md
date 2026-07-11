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
- publication rounds filter excluded voters out of target, acknowledged, and
  applied node sets before commit evaluation and state exposure.
- pending voting-configuration additions and removals can be rolled back without
  mutating the authoritative accepted or committed voter sets.
- stale publication attempts at or below the last accepted version are fenced
  without replacing the active publication round, including during joint
  accepted/committed voting-configuration transitions with exclusions.
- voting-configuration reconfiguration proposals update the accepted voter set
  first; the committed voter set catches up only after a committed publication
  round, and failed publications leave the committed voter set unchanged.
- publication apply acknowledgements now start empty and only record committed
  target nodes; excluded, missing, failed, or non-target nodes cannot be marked
  applied.
- completed publication round persistence now requires a fully applied committed
  target set; partially applied reconfiguration rounds remain active across
  capture/restore and are not promoted to completed state on retry.
- rollback now distinguishes pending-only proposal discard from already-applied
  uncommitted reconfiguration rollback; failed publication retries do not carry
  rolled-back voter additions or removals into the next target set.

Focused tests already pin that split. That means Steelsearch no longer has a
single merged voting set everywhere, but it still does not have OpenSearch-style
reconfiguration semantics.

## Replacement Blockers

No focused blockers remain in this narrow voting-configuration inventory. The
broader replacement work still depends on the surrounding coordination,
transport, shard-routing, recovery, and failure-path inventories.

## Required Tests

- no additional targeted tests are required inside this inventory at the current
  source level.

## Required Implementation

No additional targeted implementation remains in this inventory at the current
source level.

## Required Implementation Order

Move next coordination work to the broader peer-node, publication transport,
shard-routing, recovery, and failure-path inventories.
