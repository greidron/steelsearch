# Document And Bulk REST Spec

This document covers single-document write/read APIs, refresh, and NDJSON bulk
execution.

## Semantic Summary

In OpenSearch these APIs sit on top of shard routing and write-path invariants.
They are not only HTTP wrappers. Their semantics depend on:

- id generation and routing;
- realtime vs refreshed visibility;
- optimistic concurrency and versioning;
- primary/replica sequencing and retention leases;
- partial failure and shard failure behavior.

## Current Steelsearch Position

- Single-document CRUD, refresh, routing, optimistic concurrency, alias/data-
  stream write-target resolution, and bulk flows are live on the standalone
  surface.
- The documented write-path contract is strict-compared by the dedicated
  document-write-path profile.
- Replica/write durability and same-cluster behavior remain later-phase work.

## Key Route Families

### Single-document APIs

- `POST /{index}/_doc`
- `PUT /{index}/_doc/{id}`
- `GET /{index}/_doc/{id}`
- `DELETE /{index}/_doc/{id}`
- `POST /{index}/_update/{id}`

### Refresh

- `POST /{index}/_refresh`

### Bulk

- `POST /_bulk`
- `POST /{index}/_bulk`

## Replacement Gap

The current implementation is a real standalone write-path replacement surface.
It is not yet a full production or same-cluster OpenSearch write-path
replacement.
