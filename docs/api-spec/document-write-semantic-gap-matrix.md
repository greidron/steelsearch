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
| `_bulk` | `/_bulk`, `/{index}/_bulk` | partial | partial | partial | partial | partial | `tools/fixtures/document-write-semantic-compat.json`, `crates/os-node/src/standalone_runtime.rs` | bulk route handler and item mutation helpers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Mixed-op envelope, duplicate create conflict, delete existing/missing envelopes, partial-failure semantics, routing, and bounded conditional-write controls are evidenced; route-family parity remains bounded. |
| single-doc index/create | `/{index}/_doc`, `/{index}/_doc/{id}`, `/{index}/_create/{id}` | partial | partial | partial | partial | partial | `tools/fixtures/runtime-stateful-probe.json`, `crates/os-node/src/standalone_runtime.rs` | single-doc put/post/create handlers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Explicit id, auto-id, create-once, refresh visibility, routing, and bounded optimistic-concurrency validation are pinned. |
| `_update/{id}` | `/{index}/_update/{id}` | partial | partial | partial | partial | partial | `tools/fixtures/runtime-stateful-probe.json`, `crates/os-node/src/standalone_runtime.rs` | update handler and script application helpers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Missing-doc, noop, supported script update, routing miss behavior, and bounded optimistic-concurrency validation are covered. |
| `_delete_by_query` | `/{index}/_delete_by_query` | n/a | partial | partial | n/a | partial | `tools/fixtures/runtime-stateful-probe.json`, `tools/fixtures/document-write-semantic-compat.json` | delete-by-query helpers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Matched/unmatched/repeated delete semantics, bounded routing filtering, `slices=2` summary behavior, `wait_for_completion=false` task-result readback, and `requests_per_second` readback are pinned; delayed throttle/retry lifecycle remains open. |
| `_update_by_query` | `/{index}/_update_by_query` | n/a | partial | partial | partial | partial | `tools/fixtures/runtime-stateful-probe.json`, `tools/fixtures/document-write-semantic-compat.json` | update-by-query helpers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Basic matched/noop/script update behavior, repeated script update summaries, bounded routing filtering, and `wait_for_completion=false` task-result readback are covered; broader script and retry semantics remain bounded. |
| `_reindex` | `/_reindex` | n/a | partial | partial | partial | partial | `tools/fixtures/document-write-semantic-compat.json`, `crates/os-node/src/standalone_runtime.rs` | reindex handler in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Wildcard source, missing destination, overwrite semantics, destination routing, destination `require_alias`, bounded script transforms, `slices=2` summary behavior, `wait_for_completion=false` task-result readback, and `requests_per_second` readback are pinned; true async lifecycle and delayed throttling remain open. |

## Family Breakdown

### `_bulk`

| Semantic axis | Current status | Evidence | Notes / missing work |
| --- | --- | --- | --- |
| item-level conflict (`create` duplicate id) | partial | `bulk_routes_surface_partial_failure_duplicate_create_and_mixed_op_semantics` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `tools/fixtures/runtime-stateful-probe.json` | Duplicate `create` conflict and mixed envelope continuation are pinned. |
| mixed success/failure envelope | partial | same as above plus `bulk_delete_existing_and_missing_items` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Partial-failure continuation and delete missing-doc `errors:false` envelope behavior are covered, but broader item error taxonomy is still open. |
| refresh visibility | partial | stateful probe coverage | Basic refresh behavior exists, but bulk-specific read-after-write matrix is not yet separated. |
| retry / repeated call | partial | semantic probe coverage | Repeated-call semantics are not yet split by op type. |
| routing / conditional metadata | partial | `bulk_route_supports_metadata_fields_and_rejects_unsupported_pipeline_metadata` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | `routing`, `if_seq_no`, `if_primary_term`, and external version controls have bounded coverage; broader route-family retry and error taxonomy remain open. |

#### `_bulk` op matrix

| Bulk op | Success path | Error path | Evidence | Notes / missing work |
| --- | --- | --- | --- | --- |
| `index` | partial | partial | bulk runtime tests in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `tools/fixtures/document-write-semantic-compat.json` | Basic create/update item envelope exists; external versioning and retry semantics still need broader compare coverage. |
| `create` | partial | partial | duplicate-create conflict coverage in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), semantic fixture coverage | Duplicate id conflict is pinned; route-family retry/idempotency still needs cleaner evidence. |
| `update` | partial | partial | bounded update item path in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Supported update shapes are still narrower than OpenSearch; broader script/error taxonomy remains open. |
| `delete` | partial | partial | bulk mixed-op semantic coverage in runtime tests, `bulk_delete_existing_and_missing_items` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Existing-doc and missing-doc delete envelopes are OpenSearch-compared, including missing delete not setting the top-level bulk `errors` flag; broader retry/idempotency matrix remains bounded. |

### single-doc index/create/update

| Semantic axis | Current status | Evidence | Notes / missing work |
| --- | --- | --- | --- |
| create-once vs overwrite | partial | `create_doc_routes_create_once_and_conflict_on_repeat` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | `_create` conflict-on-repeat is pinned; `_doc` overwrite semantics are only partially summarized. |
| refresh visibility | partial | single-doc semantic probes in `tools/fixtures/runtime-stateful-probe.json` | Create/update with refresh visibility are pinned; family-wide read-after-write matrix still needs consolidation. |
| noop vs update counter | partial | update semantic unit tests and probes | `_update/{id}` noop and supported script update are covered; `_doc` post/put overwrite counter semantics still need a cleaner table row. |
| retry / repeated call | partial | semantic probes, `single_doc_put_repeat_*` and `single_doc_post_repeat_*` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Create conflict path and repeated plain `_doc` overwrite/readback semantics are pinned; broader retry taxonomy remains bounded. |
| routing / optimistic concurrency | partial | `single_doc_routes_surface_conflict_and_routing_negative_cases` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Routing miss, stale optimistic-concurrency rejection, missing seq/primary-term validation, create compare-and-set rejection, and update upsert/versioning restrictions are pinned. |

#### single-doc id assignment matrix

| Route shape | ID mode | Current semantics | Evidence | Notes / missing work |
| --- | --- | --- | --- | --- |
| `PUT /{index}/_doc/{id}` | explicit id | partial | single-doc put helper coverage in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `single_doc_put_repeat_*` fixture rows | Explicit id create/update and repeated overwrite/readback semantics are pinned; broader versioning/error taxonomy remains bounded. |
| `POST /{index}/_doc/{id}` | explicit id | partial | `single_doc_post_route_indexes_explicit_id_documents` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `single_doc_post_repeat_*` fixture rows | POST-with-id alias behavior and repeated overwrite/readback semantics are evidenced, but parity against all OpenSearch edge cases is not yet claimed. |
| `POST /{index}/_doc` | auto id | partial | auto-id handler path in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `post_single_doc_generated_id` in [single-doc-crud-compat.json](/home/ubuntu/steelsearch/tools/fixtures/single-doc-crud-compat.json) | Generated-id writes now use an OpenSearch-shaped 20-character URL-safe base64 id and are OpenSearch-compared for status/result/id shape; broader retry taxonomy remains bounded. |
| `PUT|POST /{index}/_create/{id}` | explicit id create-only | partial | `create_doc_routes_create_once_and_conflict_on_repeat` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Create-once/conflict-on-repeat is pinned and is currently the strongest explicit-id write guarantee in the family. |

### by-query family

| Semantic axis | Current status | Evidence | Notes / missing work |
| --- | --- | --- | --- |
| matched / unmatched | partial | delete/update-by-query semantic tests and probes, `delete_by_query_matched_summary`, `delete_by_query_unmatched_summary`, `update_by_query_matched_summary`, and `update_by_query_unmatched_summary` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Matched/unmatched delete-by-query and bounded update-by-query summary counters are OpenSearch-compared; broader query/script variants remain bounded. |
| repeated / idempotent rerun | partial | delete-by-query repeated probe, `update_by_query_repeated_update_summary` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Delete rerun idempotency and update-by-query repeated script-update summaries are pinned; broader retry taxonomy remains bounded. |
| noop / script behavior | partial | update-by-query handler tests, `update_by_query_repeated_update_summary` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Supported script behavior and repeated assignment-script update accounting are OpenSearch-compared; broader script/noop matrix remains incomplete. |
| refresh visibility | partial | existing stateful probes, `update_by_query_refresh_true_readback` and `delete_by_query_refresh_true_readback` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Update-by-query and delete-by-query `refresh=true` readback are OpenSearch-compared; broader refresh=false/visibility generation behavior remains bounded. |
| routing / slices / throttling | partial | `delete_by_query_route_surfaces_matched_unmatched_and_repeated_delete_semantics` and `update_by_query_route_surfaces_matched_unmatched_and_noop_semantics` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `update_by_query_slices_summary`, `delete_by_query_slices_summary`, `update_by_query_requests_per_second_summary`, and `delete_by_query_requests_per_second_summary` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Routing filtering is pinned for delete/update by query, bounded `slices=2` summary counters are OpenSearch-compared, and `requests_per_second` readback is pinned; delayed throttle/retry lifecycle remains open. |

#### by-query semantics matrix

| Route shape | matched | unmatched | noop | repeated call | Evidence | Notes / missing work |
| --- | --- | --- | --- | --- | --- | --- |
| `POST /{index}/_delete_by_query` | partial | partial | n/a | partial | delete-by-query semantic tests and probes in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `delete_by_query_matched_summary`, `delete_by_query_unmatched_summary`, `delete_by_query_refresh_true_readback`, `delete_by_query_slices_summary`, and `delete_by_query_task_mode_result` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Matched/unmatched/repeated delete, refresh=true readback, routing filter, bounded `slices=2` summary semantics, and task-result readback are pinned; true async cancellation behavior remains open. |
| `POST /{index}/_update_by_query` | partial | partial | partial | partial | update-by-query semantic helpers and probes in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `update_by_query_matched_summary`, `update_by_query_unmatched_summary`, `update_by_query_repeated_update_summary`, `update_by_query_refresh_true_readback`, `update_by_query_slices_summary`, and `update_by_query_task_mode_result` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Basic matched/unmatched/script update, repeated-call script update summary, refresh=true readback, routing filter behavior, bounded `slices=2` summary semantics, and task-result readback are evidenced; broader error-path evidence remains bounded. |

### `/_reindex`

| Semantic axis | Current status | Evidence | Notes / missing work |
| --- | --- | --- | --- |
| source wildcard selection | partial | `reindex_route_surfaces_wildcard_source_missing_dest_and_overwrite_semantics` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `tools/fixtures/document-write-semantic-compat.json` | Wildcard source selection is pinned. |
| missing destination | partial | same as above | Missing `dest.index` fail-closed behavior is pinned. |
| overwrite vs create counters | partial | same as above | Overwrite increments `updated`, new target docs increment `created`. |
| retry / task-mode semantics | partial | rethrottle probes and route coverage, `reindex_slices_summary`, `reindex_task_mode_result`, `reindex_task_mode_requests_per_second_result`, `update_by_query_task_mode_result`, and `delete_by_query_task_mode_result` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Bounded `slices=2` synchronous summary behavior, `wait_for_completion=false` task-result readback, and task-result `requests_per_second` readback are OpenSearch-compared; true async execution, cancellation, rethrottle, and retry lifecycle semantics are not yet summarized as replacement-ready. |
| destination routing / script transforms | partial | `reindex_route_honors_destination_routing_and_require_alias` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs), `reindex_script_transform_readback` and `reindex_script_params_transform_readback` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Destination routing supports unset/`keep`, `discard`, and `=<value>` with validation; bounded `ctx._source.<field> = ...` script transforms are OpenSearch-compared for literal and `params` values. |

#### `/_reindex` semantics matrix

| Semantic axis | Current status | Evidence | Notes / missing work |
| --- | --- | --- | --- |
| source wildcard | partial | `reindex_wildcard_source_summary` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json), runtime test coverage in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Current bounded contract copies from wildcard-matched source indices into the destination. |
| destination overwrite | partial | `reindex_overwrite_summary` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Existing destination docs are overwritten and counted as `updated`; broader conflict modes are not yet documented. |
| missing destination | partial | `reindex_missing_dest_error` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Missing `dest.index` is fail-closed with a bounded validation error. |
| destination routing | partial | `reindex_route_honors_destination_routing_and_require_alias` in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Unset/`keep` preserves source routing, `discard` clears routing, and `=<value>` forces routing. |
| source assignment script transform | partial | `reindex_script_transform_readback` and `reindex_script_params_transform_readback` in [document-write-semantic-compat.json](/home/ubuntu/steelsearch/tools/fixtures/document-write-semantic-compat.json) | Bounded `ctx._source.<field> = ...` transforms are applied during reindex and read back against OpenSearch for literal and `params` values; broader script-language parity remains bounded. |

## Write-Path Metadata Field Status

| Field | Current status | Surface | Code path / evidence | Notes / missing work |
| --- | --- | --- | --- | --- |
| `routing` | partial | single-doc put/post/create/update/delete, bulk item metadata, by-query routing filter, reindex destination routing | single-doc handlers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) around `handle_put_doc_route`, `handle_create_doc_route`, `handle_update_doc_route`, `handle_delete_doc_route`; bulk item path in `execute_bulk_action`; by-query and reindex tests in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs); request-subset docs in [single_doc_put_route_registration.rs](/home/ubuntu/steelsearch/crates/os-node/src/single_doc_put_route_registration.rs) and [bulk_route_registration.rs](/home/ubuntu/steelsearch/crates/os-node/src/bulk_route_registration.rs) | Basic routing lookup/write semantics, by-query routing filters, and reindex destination routing transforms are evidenced; broader route-family parity remains bounded rather than complete. |
| `if_seq_no` | partial | single-doc put/update/delete, bulk item metadata | optimistic concurrency checks in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) around `handle_put_doc_route`, `handle_update_doc_route`, `handle_delete_doc_route`, and `execute_bulk_action`; subset docs in [optimistic_concurrency_semantics.rs](/home/ubuntu/steelsearch/crates/os-node/src/optimistic_concurrency_semantics.rs) | Stale optimistic-concurrency rejection is evidenced for single-doc writes; broader bulk and retry semantics still need a cleaner family matrix. |
| `if_primary_term` | partial | single-doc put/update/delete, bulk item metadata | same code paths and support notes as `if_seq_no` | Supported together with `if_seq_no`; replacement claims should continue to treat it as bounded rather than complete. |
| `version` + `version_type=external` | partial | single-doc put, bulk `index` item metadata | external version handling in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) inside `handle_put_doc_route` and `execute_bulk_action` | Only external-version subset is visible in current write paths; broader versioning modes are not documented as supported. |
| `refresh` | partial | single-doc put/post/create/update/delete, bulk route-level refresh | route-level request handling in single-doc helpers and bulk handler code in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | `refresh=true` / `wait_for` bounded behavior is partially evidenced; family-wide read-after-write matrix is still incomplete. |
| `pipeline` | documented partial | single-doc post, bulk route, ingest-assisted writes | request-subset docs mention `pipeline` in [single_doc_post_route_registration.rs](/home/ubuntu/steelsearch/crates/os-node/src/single_doc_post_route_registration.rs) and [bulk_route_registration.rs](/home/ubuntu/steelsearch/crates/os-node/src/bulk_route_registration.rs); limited runtime path exists for selected write handlers in [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | Pipeline semantics are not yet replacement-ready across all document-write families; this field remains bounded/documented rather than broadly claimed. |
| `require_alias` | partial | single-doc index/create/update, bulk index/create/update, reindex destination | fail-closed concrete-target coverage in `single_doc_routes_surface_conflict_and_routing_negative_cases`, `bulk_route_supports_metadata_fields_and_rejects_unsupported_pipeline_metadata`, and `reindex_route_honors_destination_routing_and_require_alias` within [standalone_runtime.rs](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs) | `require_alias=true` now rejects concrete write targets and allows alias write targets for bounded single-doc, bulk, and reindex destination paths; broader write-family coverage remains bounded rather than complete. |

## Reading Rules

- `partial` means there is live behavior and at least some evidence, but not
  enough to claim broad OpenSearch parity.
- `no` means the semantic control is either absent, silently ignored, or not yet
  documented strongly enough to claim support.
- This matrix should be extended family-by-family before adding stronger
  replacement claims in higher-level docs.
