# Document Write Semantic Gap Matrix

This matrix tracks semantic parity for write-facing document APIs beyond simple
route existence. The goal is to make route-family gaps explicit before claiming
replacement readiness.

## Column Definitions

| Column | Meaning |
| --- | --- |
| `Family` | Write route family being tracked. |
| `Surface` | Concrete route shapes in scope. |
| `Conflict semantics` | Whether duplicate create/write conflict behavior is implemented and evidenced. |
| `Refresh visibility` | Whether refresh or read-after-write visibility semantics are pinned. |
| `Retry / idempotency` | Whether repeated calls or retries have bounded behavior and evidence. |
| `Overwrite / noop` | Whether overwrite or noop behavior is implemented and evidenced. |
| `Routing / conditional write` | Whether routing or optimistic-concurrency controls are implemented, partial, or unsupported. |
| `Evidence` | Primary fixture, runtime test, or compare harness backing the claim. |
| `Code path / missing path` | Current handler/helper location in `standalone_runtime.rs`, or explicit missing-path note. |
| `Notes / missing work` | Remaining semantic gaps before stronger parity claims are safe. |

## Family Matrix

| Family | Surface | Conflict semantics | Refresh visibility | Retry / idempotency | Overwrite / noop | Routing / conditional write | Evidence | Code path / missing path | Notes / missing work |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `_bulk` | `/_bulk`, `/{index}/_bulk` | partial | partial | partial | partial | no | `tools/fixtures/document-write-semantic-compat.json`, `crates/os-node/src/standalone_runtime.rs` | bulk route handler and item mutation helpers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Mixed-op envelope, duplicate create conflict, and partial-failure semantics are evidenced; routing and conditional-write controls remain undocumented or unsupported. |
| single-doc index/create | `/{index}/_doc`, `/{index}/_doc/{id}`, `/{index}/_create/{id}` | partial | partial | partial | partial | no | `tools/fixtures/runtime-stateful-probe.json`, `crates/os-node/src/standalone_runtime.rs` | single-doc put/post/create handlers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Explicit id, auto-id, create-once, and refresh visibility are partly pinned; routing and conditional concurrency controls still need explicit status. |
| `_update/{id}` | `/{index}/_update/{id}` | partial | partial | partial | partial | no | `tools/fixtures/runtime-stateful-probe.json`, `crates/os-node/src/standalone_runtime.rs` | update handler and script application helpers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Missing-doc, noop, and supported script update semantics are covered; optimistic concurrency and routing are still open. |
| `_delete_by_query` | `/{index}/_delete_by_query` | n/a | partial | partial | n/a | no | `tools/fixtures/runtime-stateful-probe.json`, `tools/fixtures/document-write-semantic-compat.json` | delete-by-query helpers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Matched/unmatched/repeated delete semantics are pinned; routing, slices, and throttled retry semantics remain open. |
| `_update_by_query` | `/{index}/_update_by_query` | n/a | partial | partial | partial | no | `tools/fixtures/runtime-stateful-probe.json` | update-by-query helpers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Basic matched/noop/script update behavior is only partially covered; broader script and retry semantics still need an audit row expansion. |
| `_reindex` | `/_reindex` | n/a | partial | partial | partial | no | `tools/fixtures/document-write-semantic-compat.json`, `crates/os-node/src/standalone_runtime.rs` | reindex handler in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Wildcard source, missing destination, and overwrite semantics are pinned; script, routing, slice, and task-mode differences remain open. |

## Family Breakdown

### `_bulk`

| Semantic axis | Current status | Evidence | Notes / missing work |
| --- | --- | --- | --- |
| item-level conflict (`create` duplicate id) | partial | `bulk_routes_surface_partial_failure_duplicate_create_and_mixed_op_semantics` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `tools/fixtures/runtime-stateful-probe.json` | Duplicate `create` conflict and mixed envelope continuation are pinned. |
| mixed success/failure envelope | partial | same as above | Partial-failure continuation is covered, but broader item error taxonomy is still open. |
| refresh visibility | partial | stateful probe coverage | Basic refresh behavior exists, but bulk-specific read-after-write matrix is not yet separated. |
| retry / repeated call | partial | semantic probe coverage | Repeated-call semantics are not yet split by op type. |
| routing / conditional metadata | no | none | `routing`, `if_seq_no`, `if_primary_term`, external version controls are not yet claimed. |

#### `_bulk` op matrix

| Bulk op | Success path | Error path | Evidence | Notes / missing work |
| --- | --- | --- | --- | --- |
| `index` | partial | partial | bulk runtime tests in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `tools/fixtures/document-write-semantic-compat.json` | Basic create/update item envelope exists; external versioning and retry semantics still need broader compare coverage. |
| `create` | partial | partial | duplicate-create conflict coverage in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), semantic fixture coverage | Duplicate id conflict is pinned; route-family retry/idempotency still needs cleaner evidence. |
| `update` | partial | partial | bounded update item path in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Supported update shapes are still narrower than OpenSearch; broader script/error taxonomy remains open. |
| `delete` | partial | partial | bulk mixed-op semantic coverage in runtime tests | Missing-doc delete path exists, but delete-specific envelope matrix still needs its own fixture row set. |

### single-doc index/create/update

| Semantic axis | Current status | Evidence | Notes / missing work |
| --- | --- | --- | --- |
| create-once vs overwrite | partial | `create_doc_routes_create_once_and_conflict_on_repeat` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | `_create` conflict-on-repeat is pinned; `_doc` overwrite semantics are only partially summarized. |
| refresh visibility | partial | single-doc semantic probes in `tools/fixtures/runtime-stateful-probe.json` | Create/update with refresh visibility are pinned; family-wide read-after-write matrix still needs consolidation. |
| noop vs update counter | partial | update semantic unit tests and probes | `_update/{id}` noop and supported script update are covered; `_doc` post/put overwrite counter semantics still need a cleaner table row. |
| retry / repeated call | partial | semantic probes | Create conflict path is covered; repeated plain `_doc` overwrites are not yet broken out separately. |
| routing / optimistic concurrency | no | none | `routing`, `if_seq_no`, `if_primary_term` remain unsupported or undocumented. |

#### single-doc id assignment matrix

| Route shape | ID mode | Current semantics | Evidence | Notes / missing work |
| --- | --- | --- | --- | --- |
| `PUT /{index}/_doc/{id}` | explicit id | partial | single-doc put helper coverage in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Explicit id create/update semantics exist; overwrite/versioning table still needs fuller family-wide compare coverage. |
| `POST /{index}/_doc/{id}` | explicit id | partial | `single_doc_post_route_indexes_explicit_id_documents` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | POST-with-id alias behavior is evidenced, but parity against all OpenSearch edge cases is not yet claimed. |
| `POST /{index}/_doc` | auto id | partial | current auto-id handler path in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Generated-id write path exists, but generated-id shape, retry semantics, and collision guarantees are not yet documented as replacement-ready. |
| `PUT|POST /{index}/_create/{id}` | explicit id create-only | partial | `create_doc_routes_create_once_and_conflict_on_repeat` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Create-once/conflict-on-repeat is pinned and is currently the strongest explicit-id write guarantee in the family. |

### by-query family

| Semantic axis | Current status | Evidence | Notes / missing work |
| --- | --- | --- | --- |
| matched / unmatched | partial | delete/update-by-query semantic tests and probes | Matched/unmatched delete semantics are pinned; update-by-query still needs a fuller compare row. |
| repeated / idempotent rerun | partial | delete-by-query repeated probe | Delete rerun idempotency is pinned; update-by-query rerun semantics still need explicit evidence. |
| noop / script behavior | partial | update-by-query handler tests | Supported script behavior exists, but broader script/noop matrix remains incomplete. |
| refresh visibility | partial | existing stateful probes | Route family visibility after mutation is not yet summarized cleanly. |
| routing / slices / throttling | no | none | No route-family claim yet for routing, slicing, or throttled retry semantics. |

#### by-query semantics matrix

| Route shape | matched | unmatched | noop | repeated call | Evidence | Notes / missing work |
| --- | --- | --- | --- | --- | --- | --- |
| `POST /{index}/_delete_by_query` | partial | partial | n/a | partial | delete-by-query semantic tests and probes in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Matched/unmatched/repeated delete semantics are pinned; routing and slice/task behavior remain open. |
| `POST /{index}/_update_by_query` | partial | partial | partial | partial | update-by-query semantic helpers and probes in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Basic matched/noop/script update behavior exists, but repeated-call and broader error-path evidence are still thinner than delete-by-query. |

### `/_reindex`

| Semantic axis | Current status | Evidence | Notes / missing work |
| --- | --- | --- | --- |
| source wildcard selection | partial | `reindex_route_surfaces_wildcard_source_missing_dest_and_overwrite_semantics` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `tools/fixtures/document-write-semantic-compat.json` | Wildcard source selection is pinned. |
| missing destination | partial | same as above | Missing `dest.index` fail-closed behavior is pinned. |
| overwrite vs create counters | partial | same as above | Overwrite increments `updated`, new target docs increment `created`. |
| retry / task-mode semantics | partial | rethrottle probes and route coverage | Task path exists, but slice/task/retry semantics are not yet summarized as replacement-ready. |
| routing / script transforms | no | none | Routing and general script transform semantics remain unsupported or undocumented. |

#### `/_reindex` semantics matrix

| Semantic axis | Current status | Evidence | Notes / missing work |
| --- | --- | --- | --- |
| source wildcard | partial | `reindex_wildcard_source_summary` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json), runtime test coverage in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Current bounded contract copies from wildcard-matched source indices into the destination. |
| destination overwrite | partial | `reindex_overwrite_summary` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Existing destination docs are overwritten and counted as `updated`; broader conflict modes are not yet documented. |
| missing destination | partial | `reindex_missing_dest_error` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Missing `dest.index` is fail-closed with a bounded validation error. |
| unsupported script semantics | no | no dedicated semantic fixture yet | Script transform parity is still unclaimed; next step should add an explicit unsupported-script negative case before any broader replacement claim. |

## Write-Path Metadata Field Status

| Field | Current status | Surface | Code path / evidence | Notes / missing work |
| --- | --- | --- | --- | --- |
| `routing` | partial | single-doc put/post/create/update/delete, bulk item metadata | single-doc handlers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) around `handle_put_doc_route`, `handle_create_doc_route`, `handle_update_doc_route`, `handle_delete_doc_route`; bulk item path in `execute_bulk_action` within [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs); request-subset docs in [single_doc_put_route_registration.rs](/home/ubuntu/steelsearch/crates/os-node/src/single_doc_put_route_registration.rs) and [bulk_route_registration.rs](/home/ubuntu/steelsearch/crates/os-node/src/bulk_route_registration.rs) | Basic routing lookup/write semantics exist and wrong-routing miss is now evidenced; route-family parity for alias routing, by-query routing, and reindex routing transforms is still incomplete. |
| `if_seq_no` | partial | single-doc put/update/delete, bulk item metadata | optimistic concurrency checks in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) around `handle_put_doc_route`, `handle_update_doc_route`, `handle_delete_doc_route`, and `execute_bulk_action`; subset docs in [optimistic_concurrency_semantics.rs](/home/ubuntu/steelsearch/crates/os-node/src/optimistic_concurrency_semantics.rs) | Stale optimistic-concurrency rejection is evidenced for single-doc writes; broader bulk and retry semantics still need a cleaner family matrix. |
| `if_primary_term` | partial | single-doc put/update/delete, bulk item metadata | same code paths and support notes as `if_seq_no` | Supported together with `if_seq_no`; replacement claims should continue to treat it as bounded rather than complete. |
| `version` + `version_type=external` | partial | single-doc put, bulk `index` item metadata | external version handling in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) inside `handle_put_doc_route` and `execute_bulk_action` | Only external-version subset is visible in current write paths; broader versioning modes are not documented as supported. |
| `refresh` | partial | single-doc put/post/create/update/delete, bulk route-level refresh | route-level request handling in single-doc helpers and bulk handler code in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | `refresh=true` / `wait_for` bounded behavior is partially evidenced; family-wide read-after-write matrix is still incomplete. |
| `pipeline` | documented partial | single-doc post, bulk route, ingest-assisted writes | request-subset docs mention `pipeline` in [single_doc_post_route_registration.rs](/home/ubuntu/steelsearch/crates/os-node/src/single_doc_post_route_registration.rs) and [bulk_route_registration.rs](/home/ubuntu/steelsearch/crates/os-node/src/bulk_route_registration.rs); limited runtime path exists for selected write handlers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Pipeline semantics are not yet replacement-ready across all document-write families; this field remains bounded/documented rather than broadly claimed. |
| `require_alias` | no | single-doc and bulk write families | no dedicated request handling path in current write helpers | Should remain unsupported until explicit fail-closed or alias-only write semantics are implemented. |

## Reading Rules

- `partial` means there is live behavior and at least some evidence, but not
  enough to claim broad OpenSearch parity.
- `no` means the semantic control is either absent, silently ignored, or not yet
  documented strongly enough to claim support.
- This matrix should be extended family-by-family before adding stronger
  replacement claims in higher-level docs.
