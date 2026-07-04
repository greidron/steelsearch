# Compatibility Promotion Ledger

This ledger tracks which source-compatibility rows are eligible for official
promotion, which profile the promotion targets, and what still blocks the
promotion from being reflected in the top-level matrix.

## Purpose

The repository now contains broad implementation, fixture, harness, and report
coverage across standalone, secure, interop, distributed, and optional Java
tracks.

What still remains is not only runtime work. It is also promotion work:

- deciding which rows can move from conservative `Partial` bookkeeping to
  stronger official compatibility claims;
- ensuring every promoted row has explicit parity-class evidence;
- blocking any promotion that would overstate readiness.

## Promotion Buckets

| Bucket | Meaning |
| --- | --- |
| `promoted` | The official matrix row has already been upgraded and must stay tied to explicit parity evidence. |
| `promotion-ready` | Evidence appears sufficient to re-evaluate the official matrix row now. |
| `promotion-blocked` | The row has substantial evidence, but one or more parity classes are still missing or not aggregated. |
| `optional-track` | The row belongs to an explicitly optional track and must not be promoted into general replacement readiness. |

## Current Promotion Ledger

| Source area | Target profile | Promotion bucket | Remaining blocker |
| --- | --- | --- | --- |
| Root and basic node identity | `standalone` | `promoted` | Official matrix row now points at runtime-backed root route and secure auth-envelope evidence. |
| Cluster health, state, allocation, and node stats | `standalone` | `promoted` | Official matrix row now uses a bounded standalone admin-route gate plus a separate distributed-required field allowlist. |
| Index create/get/delete and mappings/settings | `standalone` | `promoted` | Official matrix row now uses a unified index-metadata promotion gate, while restricted-target behavior remains owned by the secure gate. |
| Document write/read and refresh | `standalone` | `promoted` | Official matrix row now uses a single write/read/refresh gate plus a required multi-node durability report. |
| REST `_bulk` | `standalone` | `promoted` | Official matrix row now uses a bulk promotion gate that requires metadata/error/replay, secure authz, and durability evidence together. |
| REST `_search` | `standalone` | `promoted` | Official matrix row now uses a search promotion gate that requires DSL/session/aggregation/partial-failure evidence, secure read gates, and explicit unsupported-option deny coverage. |
| k-NN vector indexing and query search | `standalone` | `promoted` | Official matrix row now uses a vector promotion gate plus an explicit reject ledger for unsupported vector capabilities. |
| k-NN plugin REST and model APIs | `standalone` | `promoted` | Official matrix row now uses a standalone plugin gate and keeps secure clustered lifecycle explicitly out of scope for this claim. |
| ML Commons, neural search, and model serving | `standalone` | `promoted` | Official matrix row now uses an ML promotion gate that requires lifecycle, connector-authz, and isolation evidence together. |
| Snapshot and restore | `standalone` | `promoted` | Official matrix row now uses a snapshot promotion gate that requires lifecycle, restore-safety failures, and migration linkage together. |
| Migration and replacement tooling | `standalone` | `promoted` | Official matrix row now uses a migration promotion gate that requires translation/export/resume/vector evidence, approval/rollback automation, unsupported-feature preflight, and a final cutover go/no-go report together. |
| Steelsearch multi-node runtime | `standalone` | `promoted` | Official matrix row now uses a peer-node promotion gate that requires phase-C mixed-cluster failure handling, rolling stability, and durability convergence evidence together. |
| Native transport frame and OpenSearch probe compatibility | `external interop` | `promoted` | Official matrix row now uses an external interop promotion gate that requires phase-B failure harness evidence, named-writeable and diff-apply proofs, plus explicit binary dispatch allow/reject ledgers. |
| Security and access control | `secure standalone` | `promoted` | Official matrix row now uses the final secure claim gate, and real redaction-smoke plus secure durability/restart artifacts are wired into the claim report path. |
| OpenSearch comparison harness | all profiles | `promoted` | Official matrix row now uses a top-level harness promotion gate that requires suite manifests, unified schema, baseline aggregation completeness, and fail-closed smoke evidence together. |
| Java OpenSearch data-node compatibility | optional | `optional-track` | Official matrix row is now reclassified as an in-progress optional track backed by the scope matrix and binary harness profiles, but it remains outside core replacement readiness. |
| Java plugin ABI compatibility | optional | `optional-track` | Official matrix row is now reclassified as an in-progress optional track backed by the ABI scope matrix and compat-layer harness profiles, but it remains outside core replacement readiness. |

## Promotion Follow-Up

1. Keep the reclassified `promotion-ready` rows in
   [source-compatibility-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/source-compatibility-matrix.md)
   tied to explicit parity evidence.
2. Keep `promoted` rows tied to explicit route, semantic, and secure gate
   artifacts so later drift is fail-closed.
3. Keep the two Java rows out of the core replacement-ready path even after
   harness coverage improves.
