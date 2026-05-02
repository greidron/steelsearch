# Cluster Coordination And Membership Gap Inventory

This document scopes the remaining gap between the current `steelsearch`
development coordination path and an authoritative OpenSearch-compatible
coordination subsystem. It is a planning artifact for the backlog item
`Implement authoritative cluster coordination and membership`.

Replacement profile scope:

- `standalone`
- `secure standalone`
- `external interop`
- `same-cluster peer-node`

This document is primarily about the last two profiles. `standalone` and
`secure standalone` still depend on a stronger local coordination story, but
the highest-risk blockers here are mixed membership, publication, and
restart-safe cluster authority.

Source anchors:

- Current Steelsearch daemon coordination path:
  - [`crates/os-node/src/main.rs`](/home/ubuntu/steelsearch/crates/os-node/src/main.rs)
- Coordination requirements already called out by design docs:
  - [`docs/rust-port/cluster-state.md`](/home/ubuntu/steelsearch/docs/rust-port/cluster-state.md)
  - [`docs/rust-port/interop-mode.md`](/home/ubuntu/steelsearch/docs/rust-port/interop-mode.md)
  - [`docs/rust-port/architecture.md`](/home/ubuntu/steelsearch/docs/rust-port/architecture.md)

## Current Steelsearch Coordination Shape

The current daemon has a development-only coordination path.

`apply_development_coordination()` builds a synthetic cluster view from local
config, converts configured peers into `DiscoveryPeer` values, bootstraps a
`ClusterCoordinationState`, joins every discovered seed peer immediately, elects
a cluster-manager once, and publishes a single committed state.

This path is useful for:

- surfacing coordination-shaped status in development;
- exercising local decode and status plumbing;
- producing a production-membership manifest from a known local cluster view.

It is not an authoritative coordination subsystem.

## Current Evidence

The repository already proves a small but real coordination-shaped baseline:

- Steelsearch can materialize a synthetic cluster view from local configuration;
- seed peers are represented and surfaced through development coordination
  state;
- a cluster-manager can be elected from that synthetic local view;
- a single committed state can be published and persisted for development
  coordination and membership reporting;
- separate inventories already exist for election, publication, liveness,
  voting configuration, and task-queue subproblems.

This is enough to support development replacement work and selected compare
artifacts. It is not enough to claim OpenSearch-compatible authoritative
membership or same-cluster peer-node behavior.

## Replacement Blockers

The main blockers are:

- discovery and membership are still rooted in trusted local configuration
  rather than authoritative cluster participation;
- election and voting configuration are not persisted and replayed with the
  same semantics as OpenSearch coordination;
- publication, commit, and apply semantics are still development-shaped rather
  than quorum-shaped;
- restart and node-loss safety still depends on broader gateway durability work;
- cluster-manager runtime behavior under retry, failure, and partition is not
  yet proven.

## What OpenSearch-Compatible Coordination Still Requires

The existing design docs already call out the missing publish path pieces:

- pre-vote;
- join validation;
- publication;
- commit;
- follower checks;
- leader checks;
- persisted term and voting configuration.

The interop-mode decision also explicitly says Steelsearch must not yet:

- join cluster coordination as a real node;
- participate in elections;
- acknowledge publications as a joined node;
- persist real voting configuration as authoritative membership state.

## Gap Class 1: Discovery And Join Semantics

Steelsearch currently treats configured peers as trusted development inputs.

Missing behavior:

- probe-based discovery lifecycle instead of static local expansion only;
- join validation against cluster UUID, term, version, and compatibility rules;
- duplicate-node and stale-identity rejection beyond local config hygiene;
- authoritative membership updates when nodes appear, leave, or fail;
- separation between bootstrap configuration and joined cluster membership.

Required tests:

- join-accept and join-reject harnesses for cluster UUID, term, version, and
  duplicate-node mismatch;
- node-join/node-leave transcript artifacts showing authoritative membership
  change instead of local config replay;
- mixed-cluster reject transcript coverage for unsupported join situations.

Required implementation:

- probe-based or transport-backed discovery lifecycle;
- real join validation against authoritative coordination metadata;
- explicit membership store separated from bootstrap config.

## Gap Class 2: Election And Voting Configuration

The current daemon elects a cluster-manager once from the synthetic local view.

Missing behavior:

- pre-vote rounds;
- election retries and backoff;
- persisted term;
- persisted last-accepted and last-committed voting configuration;
- quorum checks tied to authoritative joined membership rather than the local
  development node list;
- leader and follower liveness checks that can trigger re-election safely.

Required tests:

- persisted term replay tests across restart;
- pre-vote and election retry/backoff harnesses;
- quorum-loss and stale-voting-configuration reject coverage.

Required implementation:

- persisted election metadata owned by coordination rather than synthetic local
  state;
- authoritative joined-membership-based quorum checks;
- leader/follower liveness transitions that can drive safe re-election.

## Gap Class 3: Publication, Commit, And Apply

The current daemon publishes a single development state and marks it applied
once the synthetic acknowledgements are collected.

Missing behavior:

- publication pipeline for repeated cluster-state updates;
- follower acknowledgement semantics for joined nodes;
- commit gating tied to authoritative quorum;
- distinct last-accepted vs last-committed state handling;
- apply ordering and failure handling when publication succeeds but local apply
  fails;
- diff/full-state publication handling tied to coordination state rather than
  decode-only support.

Required tests:

- repeated publication harnesses with full/delta/reject cases;
- apply-failure coverage where publication succeeds but local apply fails;
- quorum-based ack ordering artifacts.

Required implementation:

- publication pipeline with repeated updates;
- authoritative ack/commit gating;
- separate last-accepted vs last-committed handling and replay.

## Gap Class 4: Persistence And Restart Safety

The current daemon persists a production-membership manifest, but this is not
the same as an authoritative coordination gateway layer.

Missing behavior:

- persisted term and voting configuration;
- persisted last-accepted cluster state metadata;
- restart-safe gateway load before transport and REST admission;
- node-loss and quorum-loss handling that replays authoritative coordination
  state instead of reconstructing it from local config only.

Required tests:

- restart with persisted term/voting config replay;
- node-loss and quorum-loss restart harnesses;
- stale or corrupted coordination-state startup fencing tests.

Required implementation:

- authoritative persisted term and voting-configuration storage;
- gateway-first startup restore before coordination admission;
- restart-safe replay that does not rebuild from local config as source of
  truth.

## Gap Class 5: Cluster-Manager Runtime Behavior

OpenSearch-compatible coordination also requires runtime behavior around the
elected cluster-manager role.

Missing behavior:

- cluster-manager task queues tied to authoritative publication;
- node-left handling and publication retries;
- cluster blocks and version/feature gates applied through the coordination
  path;
- reroute triggers coupled to committed metadata changes;
- multi-node crash, restart, and partition behavior validated against Java
  OpenSearch semantics.

Required tests:

- cluster-manager task-queue and retry artifacts;
- publication retry under node-left and partition scenarios;
- mixed-node crash/restart/partition harness coverage.

Required implementation:

- cluster-manager-owned task queues and reroute triggers;
- publication retry and node-left handling wired to committed coordination
  state;
- explicit failure-mode handling for partition, restart, and stale follower
  situations.

## Recommended Task Breakdown

The current top-level backlog item should execute in this order:

1. discovery and join validation;
2. pre-vote, election, and persisted voting configuration;
3. publication, commit, and apply semantics;
4. gateway persistence and restart-safe recovery of coordination state;
5. cluster-manager runtime queues and multi-node failure testing.

That ordering matches the current code shape: Steelsearch already has a small
development coordination status path, but it does not yet have an authoritative
membership lifecycle to build the later publication and persistence work on.

## Required Implementation

For backlog purposes, the minimum implementation slices from this document are:

1. authoritative discovery and join validation;
2. persisted election and voting configuration;
3. repeated publication/commit/apply pipeline;
4. gateway-backed restart-safe coordination replay;
5. cluster-manager runtime queues plus failure harnesses.
