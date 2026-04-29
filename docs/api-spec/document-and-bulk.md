# Document And Bulk APIs

## Milestone Gate

- Primary gate: `Phase A` standalone replacement.
- Later extension: `Phase B` for interop-oriented migration and forwarding
  behavior where Java OpenSearch still participates externally.
- Final extension: `Phase C` for same-cluster write replication, retention
  lease, and peer-node durability parity.

## Single-Document APIs

| Route | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `PUT /{index}/_doc/{id}` | Index or replace a document with explicit id. | Generated route inventory currently classifies this route as `Stubbed`: Steelsearch exposes a development-oriented shell, but not full OpenSearch index-by-id semantics. | Stubbed |
| `POST /{index}/_doc` | Index a document with generated id. | Keep this as `Partial` for now: the current generated route inventory does not cleanly separate the generated-id document-create surface from the id-bearing document-index routes, so route-surface reclassification still needs explicit reconciliation. | Partial |
| `GET /{index}/_doc/{id}` | Realtime or near-realtime single-document fetch with source controls. | Generated route inventory currently classifies this route as `Stubbed`: Steelsearch exposes a development-oriented fetch shell, but not full OpenSearch get-document semantics. | Stubbed |
| `DELETE /{index}/_doc/{id}` | Delete a single document with OpenSearch version and routing semantics. | Generated route inventory still marks the REST delete surface as missing. Internal engine delete ability should not be read as current HTTP parity. | Planned |
| `POST /{index}/_update/{id}` | Partial update with scripts, doc merge, upsert, and retry controls. | Generated route inventory still marks the HTTP update surface as missing. Internal or bulk-adjacent update flows are not proof of single-document update-route parity. | Planned |

### Delete And Update Route-Surface Rule

- For single-document delete and update, keep the public route status aligned
  to the generated REST inventory, not to narrower internal engine operations.
- Internal delete ability or bulk-adjacent update support is evidence for
  future route work, not evidence of current OpenSearch HTTP parity.

### Get And Put Route-Surface Rule

- Apply the same alignment rule to `GET /{index}/_doc/{id}` and
  `PUT /{index}/_doc/{id}`.
- A usable development shell or Rust-native engine flow is not enough to call
  these routes `Partial` when the generated REST inventory still classifies
  them as `Stubbed`.

### `PUT /{index}/_doc/{id}` Bounded Semantics Anchor

- The current source-owned request-query subset is bounded to:
  - `routing`
  - `if_seq_no`
  - `if_primary_term`
- The current source-owned response subset is bounded to:
  - `_index`
  - `_id`
  - `_version`
  - `result`
  - `_seq_no`
  - `_primary_term`
  - `forced_refresh`
- This gives the explicit-id document write surface a concrete anchor for:
  - version advancement
  - sequence number / primary term exposure
  - routing-aware request shaping
  - post-write visibility signaling
- The current source-owned live hook layer now exists for:
  - bounded request-query rendering
  - bounded version/seq_no/primary_term response rendering
- Local route-traffic proof now covers:
  - `PUT /{index}/_doc/{id}` after index creation
  - bounded `_version`, `_seq_no`, `_primary_term`, and `result` response shape
- This still does not, by itself, promote the route status above `Stubbed`.
  Full OpenSearch semantics remain separate work.

### `GET /{index}/_doc/{id}` Bounded Semantics Anchor

- The current source-owned request-query subset is bounded to:
  - `_source`
  - `_source_includes`
  - `_source_excludes`
  - `realtime`
  - `routing`
- The current source-owned response subset is bounded to:
  - `_index`
  - `_id`
  - `_version`
  - `_seq_no`
  - `_primary_term`
  - `found`
  - `_source`
- The current source-owned not-found envelope is bounded to:
  - `_index`
  - `_id`
  - `found = false`
- A source-owned live hook now reuses the same bounded query subset and bounded
  response subset for request-shaped readback.
- Local route-traffic proof now covers:
  - `GET /{index}/_doc/{id}` after index creation and document write
  - bounded `_source` filtering with `routing` and `realtime` query shaping
  - OpenSearch-shaped `404` not-found envelope with `found = false`
- This gives single-document fetch a concrete anchor for source filtering,
  realtime/routing request shaping, and not-found result-class semantics,
  without yet promoting the route status above `Stubbed`.

### `DELETE /{index}/_doc/{id}` Bounded Semantics Anchor

- The current source-owned request-query subset is bounded to:
  - `routing`
  - `if_seq_no`
  - `if_primary_term`
  - `refresh`
- The current source-owned response subset is bounded to:
  - `_index`
  - `_id`
  - `_version`
  - `result`
  - `_seq_no`
  - `_primary_term`
  - `forced_refresh`
- The current source-owned missing-result envelope is bounded to:
  - `_index`
  - `_id`
  - `result = not_found`
- The current source-owned live hook layer now exists for:
  - bounded routing/CAS/refresh request rendering
  - bounded delete result rendering
- Local route-traffic proof now covers:
  - `DELETE /{index}/_doc/{id}` after index creation and document write
  - bounded `result = deleted` response shape
  - bounded missing-result class with `result = not_found`
- This gives single-document delete a concrete anchor for routing-aware delete
  requests, compare-and-set request shaping, and bounded delete/not-found
  result-class semantics, without yet promoting the route status above
  `Planned`.

### `POST /{index}/_update/{id}` Bounded Semantics Anchor

- The current source-owned request-query subset is bounded to:
  - `routing`
  - `refresh`
  - `_source`
- The current source-owned request-body subset is bounded to:
  - `doc`
  - `upsert`
  - `doc_as_upsert`
  - `retry_on_conflict`
- The current source-owned response subset is bounded to:
  - `_index`
  - `_id`
  - `_version`
  - `result`
  - `_seq_no`
  - `_primary_term`
  - `forced_refresh`
- The current source-owned failure classes are bounded to:
  - `document_missing_exception`
  - `version_conflict_engine_exception`
- The current source-owned live hook layer now exists for:
  - bounded routing/refresh/source query rendering
  - bounded partial-update request-body rendering
  - bounded update result rendering
- Local route-traffic proof now covers:
  - `POST /{index}/_update/{id}` after index creation and document write
  - bounded `result = updated` response shape
  - bounded upsert path with `doc_as_upsert` and `result = created`
- This gives single-document update a concrete anchor for partial document
  merge, bounded upsert control, retry-on-conflict request shaping, and
  minimal update result/error class semantics, without yet promoting the route
  status above `Planned`.

### Refresh Policy And Visibility Timing Rule

- The current source-owned refresh-policy subset for single-document writes is
  bounded to:
  - `refresh=false` (default)
  - `refresh=wait_for`
- Out-of-subset policy values stay outside the Phase A bounded contract:
  - `refresh=true`
  - any non-OpenSearch token outside `false` / `wait_for`
- Visibility timing rule:
  - `refresh=false` does not, by itself, grant immediate deterministic readback
    for parity work; treat explicit `POST /{index}/_refresh` as the canonical
    boundary before asserting post-write visibility
  - `refresh=wait_for` is the bounded request-scoped visibility gate inside the
    current write-path contract

### Optimistic Concurrency Rule

- The current source-owned optimistic-concurrency subset is bounded to:
  - `if_seq_no`
  - `if_primary_term`
- This bounded compare-and-set contract applies to:
  - `PUT /{index}/_doc/{id}`
  - `DELETE /{index}/_doc/{id}`
  - bulk item metadata where the same fields are present
- Matching rule:
  - when both fields are present, both must match the current document
    coordinates for the write to proceed
  - outside that bounded pair, the current Phase A contract does not imply
    external versioning or richer concurrency controls
- The canonical bounded conflict class is:
  - `version_conflict_engine_exception`

### Routing Semantics Rule

- The current source-owned routing subset is bounded to:
  - `routing`
- Routing-token normalization rule:
  - split comma-separated routing selectors
  - trim empty segments
  - compare against the stored custom routing token
- The current custom-routed visibility rule is bounded to:
  - `index` / `get` / `delete` / `search` visibility for a custom-routed
    document requires a matching routing token in the request
  - omitting `routing` for a custom-routed document is outside the visible
    subset and should be treated as a miss in bounded parity work
- This does not yet claim shard-placement parity or richer multi-shard routing
  behavior beyond the current custom-token visibility contract.

### Generated-Id Post Reconciliation Note

- `POST /{index}/_doc` is the exception for now.
- Keep it at `Partial` until the generated inventory explicitly distinguishes
  the generated-id create surface from the id-bearing document-index routes.
- Treat that inventory split as required follow-up work rather than optional
  cleanup: without it, the single-document route table cannot fully align its
  route-surface labels to the generated source inventory.
- Draft extraction rule:
  - classify `POST /{index}/_doc` as a generated-id create surface
  - classify `PUT /{index}/_doc/{id}` and `POST /{index}/_doc/{id}` as
    id-bearing document-index surfaces
  - keep those surfaces separate in generated inventory even if they share part
    of the same source handler family
- Separation criterion for shared handler families:
  - split the surfaces when id ownership, request shape, or response contract
    changes in a way that affects compatibility labeling
  - do not keep them merged only because the upstream Java REST handler class is
    shared
- Priority order for that split:
  1. response contract
  2. request shape
  3. id ownership

Use `id ownership` as the deciding axis when the first two do not already force
the split, as with generated-id create versus id-bearing document-index flows.

Example boundary:

- `response contract` example:
  - `GET /{index}/_doc/{id}` returns a document envelope
  - `HEAD /{index}/_doc/{id}` would be a bodyless existence surface
  - current generated inventory consequence:
    - `GET /{index}/_doc/{id}` -> `Stubbed`
    - `HEAD /{index}/_doc/{id}` -> `Planned`
- `request shape` example:
  - `POST /{index}/_doc` relies on server-generated id semantics
  - `PUT /{index}/_doc/{id}` carries an explicit id in the route
  - current generated-inventory/document-table consequence:
    - `POST /{index}/_doc` stays `Partial` pending generated-id surface
      extraction
    - `PUT /{index}/_doc/{id}` is already classified as `Stubbed`

Treat that `POST /{index}/_doc` label as a provisional `Partial`, not as a
fully settled route-family status. It remains a temporary holding state until
the generated inventory can classify generated-id create independently.

Do not introduce a separate status marker just for this case. Keep the table
status at `Partial` and carry the provisional nature in prose until the route
inventory split is available.

### `POST /{index}/_doc` Generated-Id Semantics Anchor

- The current source-owned request-query subset is bounded to:
  - `routing`
  - `refresh`
- The current source-owned response subset is bounded to:
  - `_index`
  - `_id`
  - `_version`
  - `result`
  - `_seq_no`
  - `_primary_term`
  - `forced_refresh`
- This gives the generated-id create surface a concrete anchor for:
  - server-generated id exposure
  - version / sequence-number response shape
  - routing-aware request shaping
  - post-write visibility signaling
- The current source-owned live hook layer now exists for:
  - bounded request-query rendering
  - bounded generated-id response rendering
- Local route-traffic proof now covers:
  - `POST /{index}/_doc` after index creation
  - bounded generated-id `_id`, `_version`, `_seq_no`, `_primary_term`, and
    `result` response shape
- This still does not, by itself, settle the generated inventory
  reconciliation note above or prove full generated-id parity.

## Refresh

| Route | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `POST /{index}/_refresh` | Makes recent writes visible to search according to refresh policy semantics. | Implemented for the development replacement surface and covered by current docs/tests. | Implemented |

## Bulk API

| Route | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `POST /_bulk` | Executes NDJSON batches across one or more indices. | Implemented for a supported subset of index/create/update/delete bulk items. | Partial |
| `POST /{index}/_bulk` | Executes NDJSON batches with default target index. | Implemented for the same supported subset. | Partial |

Bulk semantics still missing or incomplete:

- full metadata parity for every item type;
- routing behavior;
- pipeline execution;
- shard failure reporting parity;
- external versioning;
- complete optimistic concurrency semantics;
- security-aware item authorization;
- exact retry and partial failure behavior.

### Bulk Item-Type Semantic Differences

| Bulk item type | OpenSearch meaning | Current Steelsearch difference |
| --- | --- | --- |
| `index` | Inserts or replaces a document, allowing overwrite semantics. | Closest to the current Rust-native write path, but still narrower on routing, concurrency, and shard-failure semantics. |
| `create` | Inserts only if the target id does not already exist. | Development support can approximate create-only intent, but exact conflict/error semantics are narrower than OpenSearch. |
| `update` | Applies doc merge, script, upsert, and retry controls inside bulk execution. | Bulk-adjacent update behavior exists only for a narrower subset; full OpenSearch update semantics should not be implied. |
| `delete` | Removes a document by id inside bulk execution. | Delete ability exists in the engine, but OpenSearch bulk delete semantics remain narrower on routing, versioning, and result-class parity. |

The route-level `Partial` label above is intentionally broader than any single
item-type row. It means Steelsearch exposes a usable `_bulk` surface for a
mixed supported subset, not that every bulk item type has the same maturity or
the same OpenSearch semantic depth.

### Bulk Metadata Parity Anchor

- The current source-owned action-metadata subset is bounded to:
  - `_index`
  - `_id`
  - `routing`
  - `if_seq_no`
  - `if_primary_term`
- For `POST /{index}/_bulk`, the current source-owned metadata contract applies
  the route index as the default `_index` when the action metadata omits it.
- The current source-owned top-level response subset is bounded to:
  - `took`
  - `errors`
  - `items`
- The current source-owned per-item response subset is bounded to:
  - `_index`
  - `_id`
  - `status`
  - `result`
  - `_version`
  - `_seq_no`
  - `_primary_term`
  - `error`
- This gives `_bulk` and `/{index}/_bulk` a concrete metadata/readback anchor
  without yet claiming full item-type semantics, routing parity, or partial
  failure behavior.

### Bulk Item-Type Bounded Semantics Anchor

- The current source-owned `index` item subset keeps:
  - bounded action metadata
  - raw document source payload
  - result classes: `created`, `updated`
- The current source-owned `create` item subset keeps:
  - bounded action metadata
  - raw document source payload
  - result class: `created`
- The current source-owned `update` item subset keeps:
  - bounded action metadata
  - bounded payload fields:
    - `doc`
    - `upsert`
    - `doc_as_upsert`
    - `retry_on_conflict`
  - result classes: `updated`, `created`
- The current source-owned `delete` item subset keeps:
  - bounded action metadata
  - no separate source payload body
  - result classes: `deleted`, `not_found`
- This gives bulk item types a concrete semantic split without yet claiming
  script parity, pipeline parity, full routing parity, or exact partial failure
  behavior.

## Write-Path Semantics

OpenSearch write APIs are not just route handlers. They depend on engine and
cluster invariants:

- primary term validation;
- sequence-number assignment;
- retention leases and global checkpoint sync;
- replica replay semantics;
- retry-safe mapping update behavior;
- fsync/refresh visibility guarantees after replication.

Steelsearch currently implements a development-grade write path sufficient for
single-node and Steelsearch-native multi-node rehearsal. It does not yet claim
full OpenSearch write-path parity.

The current source-owned Phase A validation checklist is bounded to four
invariants:

- `replica_apply_path`
- `retry_safe_mapping_update`
- `durability_after_ack`
- `refresh_visibility_boundary`

Validation-gate reading rule:

- `replica_apply_path` and `durability_after_ack` require multi-node evidence.
- `retry_safe_mapping_update` requires explicit proof that repeated mapping
  publication does not corrupt document acceptance or replay.
- `refresh_visibility_boundary` requires explicit refresh-boundary evidence
  rather than assuming immediate post-ack visibility.

A source-owned multi-node integration fixture now exists for:

- node A write -> refresh -> node B read visibility
- node B update -> node A readback propagation
- node A delete -> refresh -> node B missing-document visibility

## Notes

- For development replacement, document index/get/refresh/bulk are among the
  strongest parts of the current surface.
- For production replacement, single-document delete/update, routing,
  concurrency controls, and replica/write durability semantics remain major
  gaps.
