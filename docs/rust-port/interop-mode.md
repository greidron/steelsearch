# Interop Operating Constraints And Remaining Gaps

## Decision Boundary

Steelsearch currently needs to be reasoned about using explicit operating
constraints, not milestone names.

The safe interop boundary is still this:

- standalone replacement behavior is the strongest evidenced mode;
- external Java OpenSearch interop is allowed only within explicit transport,
  decode, forwarding, and fail-closed limits;
- same-cluster peer-node participation is a separate, stricter gap category.

## What The Current Interop Mode Actually Means

In the external interop mode, Steelsearch behaves as:

- an external transport client;
- a local decoded-cluster-state observer;
- a selectively forwarding REST coordinator;
- a fail-closed compatibility layer when unsupported mixed-mode behavior is
  encountered.

It does **not** automatically imply:

- cluster membership;
- shard ownership;
- publication acknowledgement as a real node;
- peer recovery;
- mixed-cluster write replication.

## Why This Distinction Matters

The repository already contains evidence for many REST families and selected
interop scenarios. That evidence is valuable, but it is easy to over-read it.

A successful REST compare or external forwarding case proves only that the
specific request path behaved compatibly under the tested profile. It does not,
by itself, prove that Steelsearch can safely participate in Java OpenSearch
coordination, persistence, or shard lifecycle as a real peer node.

## Remaining Interop Constraints

### Metadata Trust Boundary

Steelsearch may decode and cache remote metadata, but unsupported or partially
understood metadata must still fail closed. The cache is a coordination aid, not
proof of cluster-membership correctness.

### Forwarding Trust Boundary

Forwarded requests remain subject to explicit safety gates. A route existing in
standalone mode does not automatically make the forwarded or mixed-mode variant
safe.

### Replacement Trust Boundary

Operators should read the current interop mode as:

- useful for comparison, observation, and bounded coordination;
- not yet sufficient evidence for blanket migration, rolling same-cluster
  replacement, or production peer-node claims.

## Links To Active Gap Inventories

- External interop gaps:
  [phase-b-safe-interop.md](/home/ubuntu/steelsearch/docs/rust-port/phase-b-safe-interop.md)
- Same-cluster peer-node gaps:
  [phase-c-peer-node-compat.md](/home/ubuntu/steelsearch/docs/rust-port/phase-c-peer-node-compat.md)
- Runtime and bootstrap gaps:
  [node-runtime-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/node-runtime-gap-inventory.md)
- Persistence and gateway gaps:
  [coordination-gateway-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/coordination-gateway-gap-inventory.md)
- Security baseline gaps:
  [production-security-baseline.md](/home/ubuntu/steelsearch/docs/rust-port/production-security-baseline.md)
