# Index And Metadata REST Spec

This document covers index lifecycle and metadata-facing routes.

## Semantic Summary

These APIs define what indices exist, how they are configured, and how future
indices should be created. In OpenSearch this family includes:

- index create/delete/open/close;
- mappings and settings read/update;
- aliases;
- component and composable templates;
- data streams and rollover;
- index diagnostics such as segments, recovery, shard stores, and resolve.

## Current Steelsearch Position

- Basic index create/get/delete semantics exist.
- Alias and template persistence are partially implemented.
- Data streams and rollover are explicitly fail-closed.
- Full metadata parity is still missing.

## Key Route Families

### Index lifecycle

- `PUT /{index}`
- `GET /{index}`
- `HEAD /{index}`
- `DELETE /{index}`
- open/close routes

### Mappings and settings

- `GET /_mapping`
- `GET /{index}/_mapping`
- `PUT /{index}/_mapping`
- `GET /_settings`
- `GET /{index}/_settings`
- `PUT /{index}/_settings`

### Aliases

- alias readback routes
- alias mutation routes
- bulk alias mutation under `POST /_aliases`

### Templates, data streams, rollover

- component template routes
- composable template routes
- legacy template routes
- `/_data_stream/*`
- `/{index}/_rollover`

## Replacement Gap

Steelsearch can model selected metadata for supported development flows, but it
does not yet expose the full authoritative OpenSearch metadata contract.
