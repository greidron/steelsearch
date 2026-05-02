# Metadata, Routing, and Allocation Gap Inventory

This note narrows the remaining work under
`Implement authoritative metadata, routing, and shard allocation behavior.`

Replacement profile scope:

- `standalone`
- `secure standalone`
- `external interop`
- `same-cluster peer-node`

This document matters to all profiles, but the highest-risk blockers appear in
`secure standalone` and `same-cluster peer-node` because metadata mutation and
shard ownership semantics become operationally authoritative there.

## Current Evidence

The current Rust port already has:

- gateway-backed persistence for cluster metadata and routing snapshots;
- coordination-owned fencing for publication, restart replay, and task-queue
  recovery;
- REST and daemon paths that can read and rewrite cluster metadata manifests;
- development-only routing/allocation views that preserve shard ownership data
  instead of rebuilding it only from the local node.

That means the repository already has real metadata and routing state to
protect. The remaining issue is ownership and mutation semantics, not total
absence of metadata or routing support.

## Replacement Blockers

The runtime still behaves like a snapshot decoder plus local rewrite helpers,
not an authoritative cluster-manager metadata engine.

That leaves three concrete blockers:

1. metadata mutations are not modeled as full OpenSearch state transitions;
2. shard allocation behavior is still simplified compared with OpenSearch;
3. some REST/runtime paths still succeed against a reduced metadata model where
   OpenSearch would enforce a stricter state transition or fail closed.

## Required Tests

- metadata mutation lifecycle tests for create/delete/open/close/mapping/data
  stream/view/custom metadata transitions;
- gateway replay tests showing authoritative metadata survives restart without
  falling back to local development rewrites;
- shard allocation/reroute/retention-leasing tests showing manager-owned
  routing remains authoritative under update and restart;
- fail-closed tests for REST/runtime paths that currently succeed against a
  reduced metadata model.

## Required Implementation

The remaining work should move in these leaves:

1. capture the current decode/apply metadata path and split the remaining work
   into explicit authoritative metadata-mutation leaves;
2. split authoritative metadata mutation into concrete leaves for:
   - index lifecycle;
   - alias, template, component-template, and cluster-settings mutation;
   - mapping/data-stream/view/custom metadata mutation;
   - repository, snapshot lifecycle, ingest/search pipeline, stored script,
     persistent task, decommission, weighted routing, and workload-group custom
     metadata;
3. split authoritative routing and shard-allocation behavior into concrete
   leaves for:
   - allocation-decider parity;
   - reroute planning behind cluster-manager-owned transitions;
   - cleanup of remaining local simplified allocation rewrites;
4. keep gateway-backed replay and manager-owned state continuity explicit while
   local development fallbacks are removed.

## Required Implementation Order

1. authoritative metadata mutation ownership;
2. authoritative routing/allocation ownership;
3. fail-closed cleanup of reduced local rewrite paths;
4. restart-safe replay and manager-owned state continuity.
