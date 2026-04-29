# Cluster Coordination And Membership Gap Inventory

This document scopes the remaining gap between the current `steelsearch`
development coordination path and an authoritative OpenSearch-compatible
coordination subsystem. It is a planning artifact for the backlog item
`Implement authoritative cluster coordination and membership`.

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

## Gap Class 4: Persistence And Restart Safety

The current daemon persists a production-membership manifest, but this is not
the same as an authoritative coordination gateway layer.

Missing behavior:

- persisted term and voting configuration;
- persisted last-accepted cluster state metadata;
- restart-safe gateway load before transport and REST admission;
- node-loss and quorum-loss handling that replays authoritative coordination
  state instead of reconstructing it from local config only.

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
