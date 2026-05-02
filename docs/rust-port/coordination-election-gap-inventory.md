# Coordination Election And Voting Gap Inventory

This document narrows the remaining gap inside the backlog item
`Implement pre-vote, election, and persisted voting configuration so cluster-manager selection is restart-safe and quorum-based.`

Replacement profile scope:

- `standalone`
- `secure standalone`
- `external interop`
- `same-cluster peer-node`

This document is primarily about `external interop` and `same-cluster
peer-node`, but stronger election semantics also underpin secure standalone
replacement claims.

Source anchors:

- Current Steelsearch coordination runtime:
  - [`crates/os-node/src/lib.rs`](/home/ubuntu/steelsearch/crates/os-node/src/lib.rs)
- Existing coordination planning inventory:
  - [`docs/rust-port/cluster-coordination-gap-inventory.md`](/home/ubuntu/steelsearch/docs/rust-port/cluster-coordination-gap-inventory.md)
- OpenSearch coordination references:
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/CoordinationState.java`
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/ElectionSchedulerFactory.java`
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/Reconfigurator.java`

## Current Evidence

Steelsearch already has small in-process coordination primitives:

- `PreVoteRequest` and `PreVoteDecision`;
- `elect_cluster_manager(...)`;
- quorum checks derived from `voting_configuration`;
- publication acknowledgement validation against term, version, and state UUID;
- persisted accepted publication state via `PersistedPublicationState`.

Focused tests already cover these primitives. The repository is therefore no
longer missing election-shaped code entirely. The remaining gap is that these
primitives are still development-local and much smaller than OpenSearch
coordination.

## Replacement Blockers

The main blockers are:

- no transport-backed pre-vote and election lifecycle across live peers;
- no election scheduling, randomized backoff, or cancellation semantics;
- no authoritative accepted-vs-committed voting configuration model;
- no liveness-driven re-election and fencing.

## Required Tests

- transport-backed pre-vote accept/reject harnesses;
- stale-term, timeout, concurrent-leader, and quorum-loss reject transcripts;
- accepted vs committed voting-configuration replay tests;
- liveness-triggered re-election and isolated-leader fencing coverage.

## Required Implementation

The remaining work should move in these leaves:

1. transport-backed pre-vote and election request exchange;
2. scheduler/backoff model for repeated election attempts;
3. distinct accepted/committed voting configuration state plus exclusions and
   reconfiguration;
4. liveness-driven re-election and safe fencing of isolated leaders and stale
   followers.

## Required Implementation Order

1. transport-backed pre-vote/election lifecycle;
2. scheduler/backoff and retry model;
3. authoritative accepted/committed voting configuration;
4. liveness-triggered re-election and fencing.
