# Steelsearch Replacement Gap Roadmap

## Goal

Steelsearch is intended to replace OpenSearch for supported workloads, not just
mirror selected REST routes. The roadmap therefore needs to describe the
remaining gaps that block real replacement rather than phase labels that imply
capability closure.

This document supersedes earlier `Phase A`, `Phase B`, and `Phase C` milestone
framing. Those names were useful while building acceptance harnesses and report
families, but they are too coarse to describe what still blocks replacement.
The active question is simpler:

- what is already evidenced;
- what is partially implemented but not replacement-safe;
- what is still missing for standalone production use, migration, external
  interop, and same-cluster participation.

## Current State Summary

The repository now has strong evidence for two things:

- broad REST route availability and response-shape parity for the standalone
  daemon;
- growing semantic probe coverage for selected write, search, metadata, and
  admin families.

That evidence is necessary, but it is not sufficient to claim full OpenSearch
replacement. The remaining work is dominated by runtime semantics, durability,
security, distributed behavior, and migration safety rather than route listing.

## Replacement Gap Categories

### 1. Standalone Semantic Gaps

The standalone daemon still needs deeper coverage and, in some families, deeper
implementation parity for:

- full search DSL parameter behavior;
- write-path concurrency, conflict, refresh, and failure semantics;
- metadata overwrite, merge, and invalid mutation behavior;
- admin/session lifecycle consistency across repeated and mixed operations.

The canonical detailed backlog for this category lives in:

- [source-compatibility-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/source-compatibility-matrix.md)
- [node-runtime-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/node-runtime-gap-inventory.md)

### 2. Security And Access-Control Gaps

A production replacement claim requires more than unsecured route parity.
Remaining work includes:

- authentication and authorization enforcement;
- `401`/`403` error-envelope parity;
- role and index-permission checks;
- restricted/system-index access control;
- TLS and secret-handling expectations.

Canonical detail lives in:

- [production-security-baseline.md](/home/ubuntu/steelsearch/docs/rust-port/production-security-baseline.md)

### 3. Node Runtime And Bootstrap Gaps

The current daemon is still easier to classify as a compatibility-oriented
runtime than a production-equivalent OpenSearch node. Missing or partial areas
include:

- bootstrap/preflight checks;
- task and thread-pool runtime controls;
- authoritative startup ordering;
- operator-facing runtime lifecycle guarantees.

Canonical detail lives in:

- [node-runtime-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/node-runtime-gap-inventory.md)

### 4. Persistence, Gateway, And Restart-Safety Gaps

Replacement requires durable, restart-safe behavior under node loss and
corruption pressure, not only in-memory parity during a clean run. Remaining
work includes:

- authoritative gateway manifest ownership;
- restart-safe metadata replay ordering;
- corruption fencing and recovery policy;
- node-loss-safe continuity for cluster metadata and shard state.

Canonical detail lives in:

- [coordination-gateway-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/coordination-gateway-gap-inventory.md)
- [coordination-metadata-persistence-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/coordination-metadata-persistence-gap-inventory.md)

### 5. Migration And Cutover Gaps

Route parity alone does not make migration safe. A credible OpenSearch
replacement still needs:

- export/import and cutover procedures with rollback evidence;
- snapshot/restore completeness for supported workloads;
- compatibility boundaries for unsupported features;
- operator guidance for safe migration sequencing.

Canonical detail lives in:

- [source-compatibility-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/source-compatibility-matrix.md)

### 6. External Java OpenSearch Interop Gaps

The repository already has accepted evidence and harnesses for external
coordination/interop scenarios, but the gap question is not closed. Remaining
work is now described as concrete interop gaps rather than a milestone stage.

Canonical detail lives in:

- [phase-b-safe-interop.md](/home/ubuntu/steelsearch/docs/rust-port/phase-b-safe-interop.md)
- [interop-mode.md](/home/ubuntu/steelsearch/docs/rust-port/interop-mode.md)

### 7. Same-Cluster Peer-Node Gaps

The hardest replacement claim is same-cluster participation with Java
OpenSearch. The canonical question is no longer whether a "phase" exists, but
whether the following are evidenced and safe:

- join validation;
- publication receive/apply/ack;
- shard allocation and routing convergence;
- peer recovery and relocation;
- mixed-cluster write replication;
- failure, restart, and rejection semantics.

Canonical detail lives in:

- [phase-c-peer-node-compat.md](/home/ubuntu/steelsearch/docs/rust-port/phase-c-peer-node-compat.md)
- [cluster-coordination-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/cluster-coordination-gap-inventory.md)

## Why Gaps Still Exist Even With OpenSearch Source And API Inventory

Two inputs are already available:

- the OpenSearch source tree;
- a broad API inventory plus route-parity ledger.

Those inputs help identify what exists, but they do not automatically prove or
implement replacement-level behavior.

The reasons are concrete:

- API inventory proves endpoint surface, not full semantics.
- Side-by-side route compare proves selected request/response behavior, not
  full runtime safety under restart, concurrency, failure, or distribution.
- Source availability shows what OpenSearch does, but the Rust runtime still
  needs equivalent execution paths, persistence rules, security checks,
  coordination behavior, and failure handling.
- Mixed-cluster and peer-node compatibility depend on transport, publication,
  allocation, recovery, and replication contracts that are much broader than
  REST surface parity.

## Search-Test Coverage Status

Search testing is not limited to a handful of route checks.

The repository already contains parameter-level and family-level search tests,
including:

- lexical DSL cases such as `term`, `match_all`, `bool`, `range`,
  `multi_match`, `match_phrase`, and `match_phrase_prefix`;
- pagination and ranking-related cases such as `sort`, `search_after`,
  `rescore`, `collapse`, `function_score`, `script_score`, and `profile`;
- highlight and suggest coverage;
- aggregation coverage;
- k-NN and vector search compatibility cases, including fail-closed behavior
  for unsupported methods and modes.

The gap is therefore not "there are no search tests." The gap is that search
coverage is still uneven across the full supported OpenSearch surface, and the
remaining unsupported or partially supported parameter sets need explicit audit,
strict compare, or fail-closed evidence before replacement claims are safe.

## Replacement Claim Exit Criteria

Steelsearch should not be described as a full OpenSearch replacement until all
of the following are true for the declared production profile:

- standalone semantic coverage is broad enough to justify workload cutover;
- security/authz behavior is enforced and evidenced;
- runtime/bootstrap and persistence gaps are closed;
- migration and rollback procedures are documented and rehearsed;
- external interop and, where claimed, same-cluster peer participation are
  evidenced with failure-path coverage;
- remaining unsupported features are explicit, fail closed, and documented as
  out of scope.
