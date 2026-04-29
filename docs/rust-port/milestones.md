# Steelsearch Milestones

## Goal

Steelsearch is intended to replace OpenSearch, not merely imitate selected
development routes. Milestones therefore need to distinguish:

- standalone replacement of an OpenSearch deployment by a Steelsearch-only
  cluster;
- mixed-cluster interoperability with Java OpenSearch;
- eventual same-cluster participation as a peer node.

These phases are cumulative. A later phase does not weaken an earlier one.

## Phase A: Standalone Replacement

Phase A is the first real replacement gate. A Steelsearch-only cluster must be
able to take over workloads that currently run on OpenSearch for the supported
surface area, with comparable externally visible behavior.

### Definition of Done

- OpenSearch-shaped REST APIs exist for the replacement surface and return
  compatible status codes, JSON fields, and error shapes for both happy-path and
  failure cases.
- Index, document, bulk, search, metadata, cluster, and snapshot APIs work with
  production-oriented semantics for the declared supported subset, not just
  development stubs.
- Multi-node Steelsearch cluster behavior is stable enough for shard
  allocation, cluster health/state, metadata propagation, task tracking, and
  operational administration required by the supported subset.
- Unsupported APIs fail closed with explicit, OpenSearch-shaped responses rather
  than silent partial behavior.
- Side-by-side compatibility tests compare Steelsearch and OpenSearch behavior
  for the supported subset, including golden success cases and representative
  error cases.

### Required Capability Areas

- REST surface parity for root, cluster, node, task, index, mapping, settings,
  alias, template, document, bulk, search, snapshot, and selected vector/ML
  APIs.
- Write-path semantics for `_version`, `_seq_no`, `_primary_term`, refresh
  visibility, optimistic concurrency, routing, and replica-safe state changes.
- Search semantics for the declared Query DSL subset, pagination, sorting,
  aggregations, alias and wildcard target expansion, and shard failure
  reporting.
- Snapshot, restore, cleanup, and migration flows sufficient for cutover and
  rollback rehearsal.
- Test evidence showing Steelsearch and OpenSearch behave compatibly on the
  supported subset.

### Non-Goals for Completion

- Java OpenSearch node membership.
- Binary plugin ABI compatibility.
- Full parity for every OpenSearch plugin or every route in the source
  inventory.

## Phase B: Mixed-Cluster Interop

Phase B is the safe interop stage between standalone replacement and true
same-cluster membership. Steelsearch must be able to interact with a Java
OpenSearch cluster in controlled ways without pretending to be a full peer node.

### Definition of Done

- Steelsearch can safely connect to Java OpenSearch transport, decode cluster
  state and publication diffs, and maintain a compatibility-aware local view.
- Steelsearch can run read-only or coordinating interop flows against Java
  OpenSearch without corrupting cluster state or acknowledging unsupported
  semantics.
- Transport request and response compatibility is broadened beyond handshake and
  probing into the action families needed for read-only and coordinating
  workflows.
- Mixed-mode tests prove fail-closed behavior when Java OpenSearch emits unknown
  actions, named writeables, or unsupported state transitions.

### Required Capability Areas

- Broader transport action request/response compatibility.
- Safe forwarding or read-only execution for selected cluster, metadata, and
  search-oriented actions.
- Compatibility ledgers for unknown named writeables, custom metadata, and
  version-gated state transitions.
- Integration tests with a live Java OpenSearch cluster covering both accepted
  and intentionally rejected mixed-mode behaviors.

## Phase C: Same-Cluster Participation

Phase C is full peer-node compatibility. Steelsearch must be able to join the
same cluster as Java OpenSearch nodes and participate without violating OpenSearch
coordination, publication, shard lifecycle, or recovery contracts.

### Definition of Done

- Steelsearch discovery, join validation, voting, publication acknowledgement,
  and cluster-manager interaction are compatible with Java OpenSearch.
- Cluster-state publication, named diffs, shard allocation, recovery,
  relocation, retention leases, and write replication semantics are compatible
  enough for mixed-node operation.
- Same-cluster rolling operations, recovery, and failure scenarios are proven by
  integration tests involving both Steelsearch and Java OpenSearch nodes.
- Any still-unsupported mixed-cluster behavior is explicitly rejected before it
  can damage cluster state or shard contents.

### Required Capability Areas

- Discovery and cluster coordination protocol parity.
- Publication diff and acknowledgement parity.
- Primary/replica write-path replication parity.
- Recovery, relocation, retention lease, and task lifecycle parity.
- Same-cluster integration harnesses that exercise steady-state, restart,
  relocation, failure, and recovery scenarios.

## Evidence Rules Across All Phases

- New compatibility claims require tests, fixtures, or live interop transcripts.
- OpenSearch comparison tests should prefer side-by-side assertions over
  narrative claims whenever practical.
- When exact parity is not yet available, Steelsearch must either document the
  narrower contract or fail closed with an OpenSearch-shaped error.
