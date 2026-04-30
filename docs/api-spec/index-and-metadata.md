# Index And Metadata APIs

## Milestone Gate

- Primary gate: `Phase A` standalone replacement.
- Later extension: `Phase B` for metadata interop and migration safety against
  Java OpenSearch.
- Final extension: `Phase C` for same-cluster metadata propagation,
  allocation-sensitive state, and mixed-node lifecycle parity, owned by the
  mixed-cluster join/allocation/publication profiles.

## Index/Metadata Parity Reading Rule

Read this family in three layers:

- route surfaces that are actually exposed as OpenSearch-shaped REST APIs;
- narrower internal metadata persistence or readback that may exist before full
  route parity;
- explicit later-phase or non-claimed boundaries for semantics that are still
  outside standalone replacement.

Do not upgrade an index/metadata surface from `Planned` or `Partial` only
because internal metadata storage exists. This family becomes stronger only
when the public route surface, the internal metadata capability, and the
documented fail-closed boundary all line up for the active milestone.

Examples:

- `_mapping` / `_settings` may have useful internal metadata persistence or
  readback, but they stay `Planned` until the actual REST route family exists.
- component/composable template metadata may be stored internally before the
  OpenSearch route families are exposed; keep the route status conservative
  until that surface is real.
- `/_data_stream/*` and `/{index}/_rollover*` are now live standalone route
  families; remaining work is broader lifecycle depth rather than route-shell
  existence.

## Index Lifecycle

| Route | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `PUT /{index}` | Create an index with mappings, settings, aliases, and creation options. | Live standalone route with strict fixture coverage for rich create bodies, selector semantics, and canonical create/query options. | Partial |
| `GET /{index}` | Read index metadata, aliases, mappings, and settings for one or more targets. | Live standalone route with strict fixture coverage for concrete, wildcard, comma, `_all`, and documented selector options. | Partial |
| `HEAD /{index}` | Existence check for index targets without response body. | The live standalone profile now supports bodyless exact, wildcard, comma, and `_all` existence probes with index-selector options. Broader index-option parity remains pending. | Partial |
| `DELETE /{index}` | Delete index metadata and shard data. | The live standalone profile now supports concrete, wildcard, comma, `_all`, and `ignore_unavailable`/`allow_no_indices` delete semantics for existing registered indices. Broader option coverage remains pending. | Partial |
| `POST /{index}/_open`, `POST /{index}/_close` | Transition index state without deleting it. | Not yet implemented as a complete index-state machine. | Planned |

### `HEAD /{index}` Current Standalone Profile

`HEAD /{index}` is no longer limited to exact-target existence probes.

The current live standalone profile now covers:

- exact targets such as `HEAD /logs-000001`
- wildcard targets such as `HEAD /logs-*`
- comma target lists such as `HEAD /logs-000001,metrics-000001`
- `_all`
- selector options `ignore_unavailable`, `allow_no_indices`, and
  `expand_wildcards=open|all`

The route remains a pure existence check:

- existing resolved target set -> `200` with no body
- unresolved target set -> `404` with no body

Unsupported `expand_wildcards` forms still fail closed explicitly.

### `PUT /{index}` Current Standalone Profile

The current live standalone profile keeps the top-level body focused on:

- `settings`
- `mappings`
- `aliases`

Within those sections, richer nested bodies now flow through the live runtime
path and compat fixture, including:

- index settings such as `number_of_shards`, `number_of_replicas`, and
  `refresh_interval`
- mapping flags such as `dynamic`
- multi-field `properties`
- alias metadata such as `filter`, `is_write_index`, `index_routing`, and
  `search_routing`

The current profile also accepts common create query options:

- `wait_for_active_shards`
- `timeout`
- `master_timeout`

### `GET /{index}` Current Standalone Selector Profile

The current live standalone profile still keeps the per-index readback bounded
to:

- `settings`
- `mappings`
- `aliases`

But selector handling now covers:

- concrete names
- wildcard expansion
- comma target expansion
- `_all`
- `ignore_unavailable=true`
- `allow_no_indices=true`
- `expand_wildcards=open|all`

### `DELETE /{index}` Current Standalone Selector Profile

The current live standalone profile for `DELETE /{index}` covers:

- concrete names
- wildcard selectors
- comma target lists
- `_all`
- `ignore_unavailable=true`
- `allow_no_indices=true`
- `expand_wildcards=open|all`

Canonical missing-index error semantics still use
`index_not_found_exception` when the selector is not allowed to collapse to an
empty target set.

### `GET /_mapping`, `GET /{index}/_mapping` Current Standalone Contract

The current source-owned compatibility anchor for mapping readback keeps the
per-index subset bounded to:

- `mappings`

Selector handling already has source-owned support for:

- global readback via `GET /_mapping`
- wildcard selection such as `GET /logs-*/_mapping`
- comma target selection such as `GET /logs-000001,metrics-000001/_mapping`

That contract is now owned by the standalone index/metadata strict fixture and
live route activation. The remaining non-claims are deeper OpenSearch mapping
families, not uncertainty about the current route surface.

### `PUT /{index}/_mapping` Current Standalone Profile

The current live standalone profile for mapping updates now covers:

- `properties` merge
- top-level `dynamic`
- top-level `_meta`
- incompatible field-type change rejection through
  `illegal_argument_exception`

The compat fixture now exercises create -> update -> readback with:

- new field insertion
- `dynamic` transition
- `_meta` overwrite/merge
- incompatible type update failure

## Mappings And Settings

| Route family | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `GET /_mapping`, `GET /{index}/_mapping` | Returns mappings for target indices. | The live standalone profile now covers global, wildcard, and comma-target selection for the current mapping readback surface. | Partial |
| `PUT /{index}/_mapping` | Updates mappings with compatibility and merge rules. | The live standalone profile now merges `properties`, `dynamic`, and `_meta`, and keeps incompatible field-type changes in the canonical `illegal_argument_exception` bucket. Deeper mapping-merge families still remain pending. | Partial |
| `GET /_settings`, `GET /{index}/_settings` | Returns effective index settings. | The live standalone profile now covers global, wildcard, and comma-target selection for the current settings readback surface. | Partial |
| `PUT /{index}/_settings` | Mutates mutable index settings. | The live standalone profile now merges mutable `index` settings, preserves untouched keys, and supports key-level `null` reset for the active mutable setting subset. Broader settings parity is still pending. | Partial |
| Field mapping inspection (`_mapping/field`) | Returns mapping info for specific fields. | Tracked in source inventory, not implemented as a complete API. | Planned |

### `GET /_settings`, `GET /{index}/_settings` Bounded Readback Contract

The current source-owned compatibility anchor for settings readback keeps the
per-index subset bounded to:

- `settings`

Selector handling already has source-owned support for:

- global readback via `GET /_settings`
- wildcard selection such as `GET /logs-*/_settings`
- comma target selection such as `GET /logs-000001,metrics-000001/_settings`

That contract is now owned by the standalone index/metadata strict fixture and
live route activation. The remaining non-claims are deeper OpenSearch settings
families, not uncertainty about the current route surface.

### `PUT /{index}/_settings` Current Standalone Profile

The current live standalone profile for settings updates now covers merge and
reset semantics for the active mutable `index` subset:

- `number_of_replicas`
- `refresh_interval`
- `max_result_window`
- `number_of_routing_shards`

The runtime path now:

- merges updates into existing `settings.index`
- preserves untouched keys
- removes keys when the update value is `null`
- keeps non-dynamic setting updates in the canonical
  `illegal_argument_exception` bucket

## Aliases

| Route family | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `GET /_alias`, `GET /{index}/_alias/{name}` and related forms | Read alias definitions, wildcard matches, and index association. | Live standalone route family with strict fixture coverage for global, scoped, wildcard, comma-target, and registry readback. | Partial |
| `PUT/POST /{index}/_alias/{name}` and related forms | Create or update aliases and alias metadata such as routing/filter/write index. | Live standalone route family with strict fixture coverage for selector fanout and the documented alias metadata contract. | Partial |
| `POST /_aliases` | Bulk alias mutation transaction. | Live standalone route family with strict fixture coverage for `add`, `remove`, and `remove_index`. | Partial |
| `DELETE /{index}/_alias/{name}` | Remove aliases from target indices. | The live standalone profile now supports alias deletion across concrete, wildcard, and comma index selectors. | Partial |

### Alias Read API Bounded Contract

- The current source-owned alias readback subset is bounded to:
  - `aliases`
- Dedicated route-registration anchors now exist for:
  - `GET /_alias`
  - `GET /_alias/{name}`
  - `GET /{index}/_alias`
  - `GET /{index}/_alias/{name}`
  - `GET /_aliases`
- The current bounded selector layer covers:
  - wildcard and comma index selectors
  - wildcard and comma alias selectors
- Within the current standalone contract, each matching index returns only:
  - `aliases`
- This keeps alias read APIs aligned with the narrower source-owned contract
  already exercised by the dedicated compat fixture, while leaving broader
  OpenSearch alias metadata semantics for later work.
- Local live-route evidence now covers:
  - `GET /_alias/{name}`
  - `GET /{index}/_alias/{name}`
  - wildcard alias reads
  - `GET /_aliases`

### Alias Mutation Current Standalone Profile

- The current live standalone profile keeps the active alias metadata subset at:
  - `filter`
  - `routing`
  - `index_routing`
  - `search_routing`
  - `is_write_index`
- Dedicated live route coverage now exists for:
  - `PUT /{index}/_alias/{name}`
  - `POST /{index}/_alias/{name}`
  - `POST /_aliases`
  - `DELETE /{index}/_alias/{name}`
- The current live mutation profile covers:
  - single-alias add/update across concrete, wildcard, and comma index targets
  - bulk `add`
  - bulk `remove`
  - bulk `remove_index`
  - delete fanout across concrete, wildcard, and comma index targets
  - acknowledged response shape:
    - `acknowledged`
- Live replay now covers:
  - index-scoped and multi-index wildcard alias readback
  - alias routing/write-index update
  - bulk add/remove
  - bulk `remove_index`
  - multi-index alias delete

## Templates, Data Streams, And Rollover

| Route family | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| Component index templates (`/_component_template`) | Defines reusable template fragments for future index creation and template composition. | Standalone profile now covers live CRUD/readback, wildcard/comma name selection, in-use delete failure, and named missing-template `404` semantics for the current persisted template subset. | Partial |
| Composable index templates (`/_index_template`) | Defines higher-level index templates used for future index creation and data streams. | Standalone profile now covers live CRUD/readback, comma-selected named readback, and named missing-template `404` semantics for the current persisted template subset. | Partial |
| Composable template simulation (`/_index_template/_simulate`, `/_index_template/_simulate/{name}`) | Simulates composable-template resolution without committing metadata. | The named/unnamed composable-template simulation surface is still missing as a REST route family; do not treat composable-template persistence as evidence of simulation parity. | Planned |
| Composable index-template simulation (`/_index_template/_simulate_index/{name}`) | Simulates how a target index name would resolve through composable templates without committing metadata. | The index-name-specific simulation surface is also still missing as a REST route family. | Planned |
| Legacy index templates | Older template mechanism used by OpenSearch. | Standalone profile now covers live CRUD/readback, wildcard-selected named readback, and named missing-template `404` semantics for the current persisted template subset. | Partial |

Keep named and unnamed composable-template simulation in one row for now. They
share the same handler family, status, and missing-parity story, so splitting
them further would add table noise without changing the current contract.

### Component/Composable Template Current Standalone Profile

- The current component-template body subset is bounded to:
  - `template`
  - `version`
  - `_meta`
- The current composable-template body subset is bounded to:
  - `index_patterns`
  - `template`
  - `composed_of`
  - `priority`
  - `version`
  - `_meta`
  - `data_stream`
- Dedicated route-registration anchors now exist for:
  - `GET /_component_template`
  - `GET /_component_template/{name}`
  - `PUT /_component_template/{name}`
  - `DELETE /_component_template/{name}`
  - `GET /_index_template`
  - `GET /_index_template/{name}`
  - `PUT /_index_template/{name}`
  - `DELETE /_index_template/{name}`
- The current selector layer covers:
  - wildcard and comma template-name selectors
- Current live runtime semantics cover:
  - global component-template readback
  - named component-template readback
  - wildcard-selected component-template readback
  - global index-template readback
  - named index-template readback
  - comma-selected index-template readback returns missing-template `404`
  - acknowledged `PUT`
  - component-template delete with in-use `400 illegal_argument_exception`
  - named missing-template `404 resource_not_found_exception`
- Template simulation routes remain out of scope for this family and should not
  be inferred from persistence parity.

### Legacy Template Current Standalone Profile

- The current legacy-template body subset is bounded to:
  - `index_patterns`
  - `order`
  - `version`
  - `settings`
  - `mappings`
  - `aliases`
- Dedicated route-registration anchors now exist for:
  - `GET /_template`
  - `GET /_template/{name}`
  - `PUT /_template/{name}`
  - `DELETE /_template/{name}`
- The current selector layer covers:
  - wildcard and comma template-name selectors
- Current live runtime semantics cover:
  - global legacy-template readback
  - named legacy-template readback
  - wildcard-selected legacy-template readback
  - acknowledged `PUT`
  - acknowledged delete
  - named missing-template `404 resource_not_found_exception`

### Data Stream Current Standalone Profile

- The current live `/_data_stream*` surface covers:
  - `PUT /_data_stream/{name}`
  - `GET /_data_stream`
  - `GET /_data_stream/{name}`
  - `GET /_data_stream/_stats`
  - `DELETE /_data_stream/{name}`
- Current runtime semantics are bounded to:
  - template-backed data-stream creation
  - backing-index generation starting at `.ds-{name}-000001`
  - named/global readback with `generation`, `indices`, `status`
  - top-level stats with `data_stream_count` and `backing_indices`
  - acknowledged delete
- Missing named data-stream readback/delete currently returns a live `404` error path.

### Rollover Current Standalone Profile

- The current live rollover surface is no longer fail-closed.
- Current runtime semantics cover:
  - unnamed data-stream rollover on `POST /{target}/_rollover`
  - alias-backed named rollover on `POST /{target}/_rollover/{new_index}`
  - bounded rollover response fields:
    - `acknowledged`
    - `shards_acknowledged`
    - `old_index`
    - `new_index`
    - `rolled_over`
    - `dry_run`
    - `conditions`
- The current standalone compat fixture covers both rollover target families without fail-closed fallback.

## Route-Surface Alignment Rule

- For `_mapping`, `_settings`, alias delete, legacy template routes, and
  component/composable template routes, keep the route-family status aligned to
  the generated route inventory rather than to narrower internal metadata
  persistence.
- Internal development storage or readback is evidence for future route work,
  not proof of current OpenSearch REST parity.
| `/_data_stream` routes | Data stream lifecycle and backing-index management. | Live standalone route family with strict fixture coverage for template-backed create/read/stats/delete. | Partial |
| `/{index}/_rollover` | Rolls write alias or data stream to a new backing index under conditions. | Live standalone route family with strict fixture coverage for data-stream-backed unnamed rollover and alias-backed named rollover. | Partial |

## Other Index Admin Surfaces

| Route family | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| Analyze, validate query, refresh, flush, force merge, recovery, segments, shard stores, resolve index | Index administration and diagnostics. | Refresh is supported in the development replacement surface. Most other admin routes remain incomplete or absent. | Mixed; refresh is Implemented, most others Planned |

## Notes

- The current implementation is good enough for a subset of index management in
  development mode.
- It is not yet an authoritative replacement for the full OpenSearch metadata
  model, especially around templates, data streams, rollover, and allocation-
  sensitive metadata.
