# Java OpenSearch External Interop Gap Inventory

## Scope

This document replaces the earlier `Phase B` milestone narrative with a direct
inventory of the remaining gaps for safe external interoperability with a live
Java OpenSearch cluster.

The active operating boundary is still external interop, not peer-node
membership:

- Steelsearch may connect to Java OpenSearch transport ports as an external
  client/coordinator/observer.
- Java OpenSearch remains authoritative for cluster membership, shard
  lifecycle, and publication.
- Unsupported mixed-mode behavior must fail closed before it can corrupt
  cluster state, shard state, or write ordering.

## Already-Evidenced Ground

The repository already carries accepted harnesses, reports, and canonical
runners for external interop scenarios. That work means the interop boundary is
no longer purely aspirational.

What it does not mean:

- that every transport action is validated;
- that every metadata edge case is covered;
- that write forwarding is production-safe for arbitrary workloads;
- that same-cluster participation is solved.

## Remaining Gap Areas

### Transport Handshake And Capability Negotiation

Remaining work:

- tighten wire-version negotiation and reject behavior;
- harden unsupported transport action handling;
- audit feature/capability negotiation for partial decoders;
- add regression coverage for version-skew and malformed-frame cases.

Current repo-local handshake/version-skew baseline:

- [transport-handshake-version-skew-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/transport-handshake-version-skew-matrix.md)
- [interop-handshake-reject-cases.json](/home/ubuntu/steelsearch/tools/fixtures/interop-handshake-reject-cases.json)

### Cluster-State Decode And Cache Correctness

Remaining work:

- verify delta/full-state apply ordering under repeated updates;
- harden cache invalidation when decoded metadata is incomplete;
- add reject-path coverage for unsupported metadata shapes;
- confirm stale-cache behavior fails closed for forwarded operations.

Current repo-local stale-cache baseline:

- [decoded-cluster-state-cache-fail-closed-policy.md](/home/ubuntu/steelsearch/docs/rust-port/decoded-cluster-state-cache-fail-closed-policy.md)
- [interop-cluster-state-cache-reject-cases.json](/home/ubuntu/steelsearch/tools/fixtures/interop-cluster-state-cache-reject-cases.json)
- [interop-cluster-state-cache-transcripts.json](/home/ubuntu/steelsearch/tools/fixtures/interop-cluster-state-cache-transcripts.json)

### Read Coordination Boundaries

Remaining work:

- document which read families are authoritative locally vs forwarded;
- audit wildcard/index-resolution behavior against live Java clusters;
- add failure-path coverage for partial node visibility and missing metadata;
- ensure node-selection heuristics do not silently bypass unsupported routing.

Current repo-local allowlist baseline:

- [interop-allowlist.md](/home/ubuntu/steelsearch/docs/rust-port/interop-allowlist.md)
- [interop-unsupported-forwarded-actions.json](/home/ubuntu/steelsearch/tools/fixtures/interop-unsupported-forwarded-actions.json)

### Write Forwarding Safety Gates

Remaining work:

- keep forwarding explicitly profile-gated;
- tighten preconditions for forwarded bulk/search/admin actions;
- ensure unsupported request shapes reject before transport dispatch;
- add rollback-safe error handling for partial forwarding failures.

### Mixed-Mode Failure Behavior

Remaining work:

- stale cluster-manager identity;
- publication-version jumps;
- node-list churn;
- remote-cluster disconnects;
- incompatible metadata or shard-routing snapshots.

Each case needs explicit fail-closed behavior and harness evidence.

Current repo-local mixed-mode failure baseline:

- [phase-b-gap-harness-profiles.json](/home/ubuntu/steelsearch/tools/fixtures/phase-b-gap-harness-profiles.json)
- [run-phase-b-gap-harness.sh](/home/ubuntu/steelsearch/tools/run-phase-b-gap-harness.sh)

## What Is Still Out Of Scope Here

These remain peer-node problems, not external interop problems:

- cluster join;
- discovery participation;
- shard ownership;
- publication acknowledgement as a cluster member;
- peer recovery;
- mixed-cluster write replication.

Those are tracked in
[phase-c-peer-node-compat.md](/home/ubuntu/steelsearch/docs/rust-port/phase-c-peer-node-compat.md).

## Exit Criteria For This Category

External interop may be treated as replacement-relevant only when:

- supported transport actions are explicitly enumerated;
- unsupported actions reject deterministically and safely;
- decoded cluster state is authoritative enough for the declared forwarding
  profile;
- mixed-mode read and write forwarding paths have error-path evidence;
- interop limits are documented for operators as cutover constraints.
