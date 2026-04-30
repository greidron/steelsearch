# Snapshot, Migration, And Interop REST Spec

This document covers repository/snapshot APIs, migration-facing APIs, and the
REST-visible boundary of Java/OpenSearch interop.

## Semantic Summary

These surfaces matter because Steelsearch is positioned as a standalone
Rust-native replacement target. That means cutover has to happen through:

- repository and snapshot workflows;
- migration/export/import tooling;
- explicit interop boundaries, not accidental shard-store reuse.

## Current Steelsearch Position

- Snapshot repository/create/status/restore/delete/cleanup flows are live and
  strict-compared on the canonical repository-capable OpenSearch profile.
- Migration rehearsal exists as a strict-profile cutover path covering
  mappings, templates, aliases, data streams, and vector-bearing payloads.
- Java interop remains coordinating/external-client oriented, not full cluster
  membership.

## Key Route Families

### Snapshots and repositories

- `/_snapshot/*`
- repository create/get/delete/verify/cleanup
- snapshot create/status/delete/restore/clone

### Migration-adjacent

- `_reindex`
- `_delete_by_query`
- `_update_by_query`
- related task-throttling surfaces

### Interop boundary

- REST-visible compatibility shell over selected Java/OpenSearch transport-backed
  flows
- explicit fail-closed behavior for unsupported mixed-cluster semantics

## Replacement Gap

- repository-grade production parity is incomplete;
- migration tooling is still narrower than the full OpenSearch cutover space;
- Java mixed data-node compatibility is still intentionally blocked.
