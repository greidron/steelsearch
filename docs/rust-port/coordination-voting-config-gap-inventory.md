# Coordination Voting Configuration Gap Inventory

This document narrows the remaining gap inside the backlog item
`Add voting-configuration exclusions and joint-consensus style voting updates so reconfiguration does not rely on directly mutating a single flat voter set.`

Source anchors:

- Current Steelsearch coordination runtime:
  - [`crates/os-node/src/lib.rs`](/home/ubuntu/steelsearch/crates/os-node/src/lib.rs)
- Existing coordination planning inventories:
  - [`docs/rust-port/coordination-election-gap-inventory.md`](/home/ubuntu/steelsearch/docs/rust-port/coordination-election-gap-inventory.md)
  - [`docs/rust-port/cluster-coordination-gap-inventory.md`](/home/ubuntu/steelsearch/docs/rust-port/cluster-coordination-gap-inventory.md)
- OpenSearch coordination references:
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/CoordinationState.java`
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/VotingConfiguration.java`
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/CoordinationMetadata.java`
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/Reconfigurator.java`

## Current Steelsearch Voting Configuration Shape

Steelsearch already has a smaller split than before:

- `ClusterCoordinationState.last_accepted_voting_configuration`
- `ClusterCoordinationState.last_committed_voting_configuration`
- `PersistedPublicationState` persists both sets
- quorum checks, election, publication ownership, and liveness still read the
  accepted set directly

Focused tests already pin that split:

- `accepted_and_committed_voting_configurations_are_tracked_separately`
- `publication_state_manifest_persists_and_restores_accepted_publication`
- `persisted_publication_state_replays_term_and_rejects_old_acknowledgements`

That means Steelsearch no longer has a single merged voting set everywhere,
but it still does not have OpenSearch-style reconfiguration semantics.

## What Still Differs From OpenSearch

## Gap Class 1: No Voting-Config Exclusion State

OpenSearch can temporarily exclude voters from cluster-manager elections and
publication quorum calculations. Steelsearch has no equivalent state.

Missing behavior:

- explicit exclusion records keyed by node id;
- exclusion validation and duplicate handling;
- fencing that prevents excluded nodes from continuing to count toward
  ownership and publication majority;
- persisted replay of exclusion state across restart.

## Gap Class 2: Accepted And Committed Sets Do Not Form A Joint Configuration

Steelsearch tracks accepted and committed voter sets separately, but it does
not model a transitional joint configuration where both old and new
configurations must be respected.

Missing behavior:

- joint-consensus quorum rules during reconfiguration;
- transitional publication ownership checks against both configurations;
- clear apply/commit step that moves a new configuration from accepted to
  committed only after a successful authoritative commit;
- rollback-safe behavior when reconfiguration does not commit.

## Gap Class 3: Membership Changes Mutate Voting State Too Directly

`join_peer(...)` currently inserts every admitted peer directly into the
accepted voting configuration.

Missing behavior:

- separation between discovered membership and authoritative voting membership;
- cluster-manager owned reconfiguration proposals instead of join-time mutation;
- explicit removal path for failed or excluded voters;
- tests that prove joins do not silently rewrite the authoritative voter set.

## Gap Class 4: Runtime Users Still Read Only The Accepted Set

Even after the accepted/committed split, the runtime mostly treats the accepted
set as the only authoritative quorum surface.

Missing behavior:

- election ownership checks that account for joint configuration transitions;
- liveness and quorum-loss checks that can reason about exclusions and
  committed-vs-accepted transitions;
- publication ack and commit semantics that fence against partially applied
  reconfiguration;
- JSON manifest shape for future operator-visible reconfiguration state.

## Recommended Execution Order

1. add explicit voting-config exclusion state and persist it;
2. stop mutating accepted voters directly from `join_peer(...)`;
3. introduce joint-consensus quorum helpers across accepted and committed
   configurations;
4. wire publication ownership, commit, and fencing checks through those joint
   configuration helpers;
5. add targeted tests for exclusion, reconfiguration proposal, commit, and
   rollback behavior.
