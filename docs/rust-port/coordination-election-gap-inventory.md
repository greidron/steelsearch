# Coordination Election And Voting Gap Inventory

This document narrows the remaining gap inside the backlog item
`Implement pre-vote, election, and persisted voting configuration so cluster-manager selection is restart-safe and quorum-based.`

Source anchors:

- Current Steelsearch coordination runtime:
  - [`crates/os-node/src/lib.rs`](/home/ubuntu/steelsearch/crates/os-node/src/lib.rs)
- Existing coordination planning inventory:
  - [`docs/rust-port/cluster-coordination-gap-inventory.md`](/home/ubuntu/steelsearch/docs/rust-port/cluster-coordination-gap-inventory.md)
- OpenSearch coordination references:
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/CoordinationState.java`
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/ElectionSchedulerFactory.java`
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/Reconfigurator.java`

## Current Steelsearch Election Shape

Steelsearch already has small in-process coordination primitives:

- `PreVoteRequest` and `PreVoteDecision`
- `elect_cluster_manager(...)`
- quorum checks derived from `voting_configuration`
- publication acknowledgement validation against term, version, and state UUID
- persisted accepted publication state via `PersistedPublicationState`

Focused tests already cover these primitives:

- `pre_vote_and_election_require_voting_quorum`
- `publication_commit_and_acknowledgement_require_voting_quorum_and_matching_state`
- `persisted_publication_state_replays_term_and_rejects_old_acknowledgements`
- `publication_state_manifest_persists_and_restores_accepted_publication`

This means Steelsearch is no longer missing election-shaped code entirely. The
remaining gap is that these primitives are still development-local and much
smaller than OpenSearch coordination.

## What Still Differs From OpenSearch

## Gap Class 1: Pre-Vote And Election Transport Lifecycle

OpenSearch runs pre-vote and election attempts across live peers. Steelsearch
does not yet exchange pre-vote or election messages over the transport layer.

Missing behavior:

- transport-backed pre-vote request/response exchange;
- live vote collection from joined peers;
- election result derived from observed peer responses instead of local
  iteration over `joined_nodes`;
- rejection handling for peer timeouts, stale terms, and concurrent leaders.

## Gap Class 2: Election Scheduling And Backoff

OpenSearch has an election scheduler with retries, randomized delay, and
bounded backoff. Steelsearch currently increments term and elects immediately.

Missing behavior:

- repeated election attempts;
- randomized initial delay and bounded backoff;
- election duration windows;
- cancellation when leadership or quorum changes mid-attempt.

## Gap Class 3: Voting Configuration Semantics

Steelsearch currently keeps a single `voting_configuration` set and persists it
inside `PersistedPublicationState`.

Missing behavior:

- distinct last-accepted vs last-committed voting configurations;
- reconfiguration rules as cluster-manager nodes join or leave;
- voting-config exclusion handling;
- restart-safe replay of authoritative voting membership instead of one merged
  set.

## Gap Class 4: Leader And Follower Liveness

OpenSearch couples election safety to fault detection. Steelsearch still lacks
that runtime.

Missing behavior:

- follower checks;
- leader checks;
- term bump and re-election triggers on failed liveness checks;
- quorum-loss transitions that fence an isolated old manager.

## Recommended Execution Order

1. keep the existing local pre-vote/election/persisted-state primitives pinned
   by focused tests and explicit backlog items;
2. add distinct accepted/committed voting configuration state;
3. add election scheduling and backoff;
4. add transport-backed pre-vote/election vote collection;
5. add leader/follower liveness and quorum-loss triggers.
