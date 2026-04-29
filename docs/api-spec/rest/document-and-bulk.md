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

- Basic document index/get and bulk flows exist.
- Refresh exists and is part of the current development replacement profile.
- Full delete/update, routing, conflict, and replica/write parity are still
  incomplete.

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

The current implementation is good enough for a supported development subset.
It is not yet a full OpenSearch write-path replacement.
