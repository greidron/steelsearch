# Index And Metadata APIs

## Milestone Gate

- Primary gate: `Phase A` standalone replacement.
- Later extension: `Phase B` for metadata interop and migration safety against
  Java OpenSearch.
- Final extension: `Phase C` for same-cluster metadata propagation,
  allocation-sensitive state, and mixed-node lifecycle parity.

## Index/Metadata Parity Reading Rule

Read this family in three layers:

- route surfaces that are actually exposed as OpenSearch-shaped REST APIs;
- narrower internal metadata persistence or readback that may exist before full
  route parity;
- explicit fail-closed boundaries for unsupported selectors, template flows,
  data streams, and rollover lifecycle semantics.

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
- `/_data_stream/*` and `/{index}/_rollover*` are strongest on the fail-closed
  layer today: the important contract is OpenSearch-like error shape, not
  partial lifecycle support.

## Index Lifecycle

| Route | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `PUT /{index}` | Create an index with mappings, settings, aliases, and creation options. | Index creation exists for the Rust-native store. Basic mapping/settings persistence exists, but full create-index body parity is incomplete. | Partial |
| `GET /{index}` | Read index metadata, aliases, mappings, and settings for one or more targets. | A bounded metadata readback subset now has source-owned wildcard/comma selector semantics for registered indices. Current local evidence covers wildcard and comma expansion across `settings`/`mappings`/`aliases`, but not the full OpenSearch metadata surface. | Partial |
| `HEAD /{index}` | Existence check for index targets without response body. | A bounded exact-target existence probe now exists for one concrete index name at a time, with bodyless `200`/`404` semantics. Wildcards, comma lists, and `_all` still remain fail-closed outside that subset. | Partial |
| `DELETE /{index}` | Delete index metadata and shard data. | A source-owned wildcard/comma selector contract now exists alongside canonical missing-index error semantics. Local route traffic proof is still pending, so the current surface remains bounded and incomplete. | Partial |
| `POST /{index}/_open`, `POST /{index}/_close` | Transition index state without deleting it. | Not yet implemented as a complete index-state machine. | Planned |

### `HEAD /{index}` Minimum Compatibility Contract

- `Phase A` status: still `Planned`; do not imply support by silently routing
  this surface through `GET /{index}`.
- Once implemented, the minimum contract is:
  - existing supported exact index target -> `200` with no response body
  - missing exact index target -> `404` with no response body
- For this `Phase A` contract, "exact index target" means:
  - one concrete index name
  - no wildcard pattern
  - no comma-separated target list
  - no `_all`-style broad selector
- This route is an existence check, not a metadata readback route:
  - do not return the `GET /{index}` payload
  - do not synthesize partial metadata just to approximate parity
- Unsupported wildcard/comma target expansion or index-selection options should
  fail closed until Steelsearch can prove the same existence-check semantics
  for those forms.
- Fail-closed examples for this route in `Phase A`:
  - `HEAD /_all`
  - `HEAD /logs-*`
  - `HEAD /index-a,index-b`

Do not attach a separate reject-reason variant to each broad-selector example
at this stage. For `Phase A`, the important contract boundary is that all of
these forms stay in the same `unsupported broad selector` bucket. Treat that
phrase as the canonical label for this fail-closed group.

Do not shorten `unsupported broad selector` further here. Both words matter:
`unsupported` carries the fail-closed status, and `broad selector` carries the
wildcard/comma/`_all` grouping that this route still rejects as one family.

The current route work now has a source-owned exact-target anchor plus local
route proof for existing and missing concrete names:

- `HEAD /logs-000001` -> `200` with no body
- `HEAD /missing-000001` -> `404` with no body
- `HEAD /_all`, `HEAD /logs-*`, `HEAD /index-a,index-b` -> `400`
  `unsupported broad selector`

That is enough to treat the current `Phase A` surface as a bounded `Partial`
existence probe while keeping broad selectors explicitly fail closed.

### `PUT /{index}` Bounded Create-Body Contract

The current source-owned compatibility anchor for `PUT /{index}` keeps only
the body sections that Steelsearch can already explain coherently in `Phase A`:

- `settings`
- `mappings`
- `aliases`

Treat that as the runnable create-body subset for now. Do not read unsupported
create-index options, activation waits, or broader OpenSearch creation flags
into this route merely because index creation itself already exists.

Local route activation now exercises that bounded body subset by creating a new
index with `settings`, `mappings`, and `aliases`, then reading the resulting
metadata back through `GET /{index}`. That is enough to anchor the current
`Partial` surface to a concrete create-body subset, but not enough to claim
full OpenSearch create-index parity.

### `GET /{index}` Wildcard/Comma Metadata Readback Contract

The current source-owned compatibility anchor for `GET /{index}` keeps the
per-index metadata subset bounded to:

- `settings`
- `mappings`
- `aliases`

Selector handling now has local route evidence for:

- wildcard expansion such as `GET /logs-*`
- comma target expansion such as `GET /logs-000001,metrics-000001`

That is enough to anchor the current `Partial` route to bounded metadata
readback plus selector expansion, but not enough to claim the full OpenSearch
readback surface yet.

### `DELETE /{index}` Wildcard/Error-Path Contract

The current source-owned compatibility anchor for `DELETE /{index}` covers:

- wildcard selector expansion such as `DELETE /logs-*`
- comma target expansion such as `DELETE /logs-000001,metrics-000001`
- `_all` expansion across the known index set
- canonical missing-index error shape via `index_not_found_exception`

That is enough to ground the current delete-parity work in explicit selector
and error-path semantics. Local route activation now exercises wildcard delete
success plus missing-index failure, so the current `Partial` delete surface has
both a source-owned selector/error contract and concrete live-route evidence.

### `GET /_mapping`, `GET /{index}/_mapping` Bounded Readback Contract

The current source-owned compatibility anchor for mapping readback keeps the
per-index subset bounded to:

- `mappings`

Selector handling already has source-owned support for:

- global readback via `GET /_mapping`
- wildcard selection such as `GET /logs-*/_mapping`
- comma target selection such as `GET /logs-000001,metrics-000001/_mapping`

That is enough to ground mapping readback work in a concrete bounded subset,
and local route activation now exercises `GET /_mapping`,
`GET /logs-*/_mapping`, and
`GET /logs-000001,metrics-000001/_mapping` against seeded metadata. That is
enough to treat the current route family as a bounded `Partial` readback
surface, but not enough to claim full OpenSearch mapping parity.

### `PUT /{index}/_mapping` Bounded Update Contract

The current source-owned compatibility anchor for mapping updates keeps the
mutation subset bounded to:

- `properties`

That is enough to ground `PUT /{index}/_mapping` work in a concrete bounded
update surface, and local route activation now exercises a `properties` update
followed by `GET /{index}/_mapping` readback against seeded metadata. That is
enough to treat the current route family as a bounded `Partial` update
surface, but not enough to claim full merge or incompatible-update parity yet.

## Mappings And Settings

| Route family | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `GET /_mapping`, `GET /{index}/_mapping` | Returns mappings for target indices. | A bounded mapping readback subset now has local route evidence for global, wildcard, and comma-target selection. The route family is still narrower than full OpenSearch mapping readback, but it is no longer only a source-owned helper. | Partial |
| `PUT /{index}/_mapping` | Updates mappings with compatibility and merge rules. | A bounded `properties`-only update subset now has local route activation evidence. Incompatible-update failure semantics and the full OpenSearch merge surface are still pending. | Partial |
| `GET /_settings`, `GET /{index}/_settings` | Returns effective index settings. | A bounded settings readback subset now has local route evidence for global, wildcard, and comma-target selection. The route family is still narrower than full OpenSearch settings readback, but it is no longer only a source-owned helper. | Partial |
| `PUT /{index}/_settings` | Mutates mutable index settings. | A bounded mutable `index`-settings subset now has local route activation evidence for `number_of_replicas` and `refresh_interval`. Validation failure semantics and the full OpenSearch settings-update surface are still pending. | Partial |
| Field mapping inspection (`_mapping/field`) | Returns mapping info for specific fields. | Tracked in source inventory, not implemented as a complete API. | Planned |

### `GET /_settings`, `GET /{index}/_settings` Bounded Readback Contract

The current source-owned compatibility anchor for settings readback keeps the
per-index subset bounded to:

- `settings`

Selector handling already has source-owned support for:

- global readback via `GET /_settings`
- wildcard selection such as `GET /logs-*/_settings`
- comma target selection such as `GET /logs-000001,metrics-000001/_settings`

That is enough to ground settings readback work in a concrete bounded subset,
and local route activation now exercises `GET /_settings`,
`GET /logs-*/_settings`, and
`GET /logs-000001,metrics-000001/_settings` against seeded metadata. That is
enough to treat the current route family as a bounded `Partial` readback
surface, but not enough to claim full OpenSearch settings parity.

### `PUT /{index}/_settings` Bounded Update Contract

The current source-owned compatibility anchor for settings updates keeps the
mutation subset bounded to mutable `index` settings:

- `number_of_replicas`
- `refresh_interval`

That is enough to ground `PUT /{index}/_settings` work in a concrete bounded
update surface, and local route activation now exercises a bounded mutable
settings update followed by `GET /{index}/_settings` readback against seeded
metadata. That is enough to treat the current route family as a bounded
`Partial` update surface, but not enough to claim full validation or broader
OpenSearch settings parity yet.

## Aliases

| Route family | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `GET /_alias`, `GET /{index}/_alias/{name}` and related forms | Read alias definitions, wildcard matches, and index association. | Alias readback exists for dedicated alias GET and `_aliases`-style registry readback. Current coverage is useful but still narrower than OpenSearch. | Partial |
| `PUT/POST /{index}/_alias/{name}` and related forms | Create or update aliases and alias metadata such as routing/filter/write index. | Alias mutation exists in the focused development subset. Full metadata, wildcard, and failure semantics remain incomplete. | Partial |
| `POST /_aliases` | Bulk alias mutation transaction. | Alias mutation support exists in part, but full bulk alias semantics remain incomplete. | Partial |
| `DELETE /{index}/_alias/{name}` | Remove aliases from target indices. | Alias delete is still a missing REST surface in the route inventory; current alias support should not be read as including delete parity. | Planned |

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
- Within this bounded subset, each matching index returns only:
  - `aliases`
- This keeps alias read APIs aligned with the narrower source-owned contract
  already exercised by the dedicated compat fixture, while leaving broader
  OpenSearch alias metadata semantics for later work.
- Local live-route evidence now covers:
  - `GET /_alias/{name}`
  - `GET /{index}/_alias/{name}`
  - wildcard alias reads
  - `GET /_aliases`

### Alias Mutation API Bounded Contract

- The current source-owned alias mutation subset is bounded to:
  - `filter`
  - `routing`
  - `index_routing`
  - `search_routing`
  - `is_write_index`
- Dedicated route-registration anchors now exist for:
  - `PUT /{index}/_alias/{name}`
  - `POST /{index}/_alias/{name}`
  - `POST /_aliases`
  - `DELETE /{index}/_alias/{name}`
- The current source-owned mutation helpers cover:
  - single-index alias add/update expressed as bounded `actions.add`
  - bulk alias add/remove expressed as bounded `actions[]`
  - single-index alias delete expressed as bounded `actions.remove`
  - acknowledged response shape:
    - `acknowledged`
- This is still narrower than full OpenSearch alias mutation semantics. The
  broader wildcard, failure, and activation story remains follow-up work.
- Local live-route evidence now covers:
  - `PUT /{index}/_alias/{name}`
  - `POST /_aliases`
  - `DELETE /{index}/_alias/{name}`
  - `PUT` -> `GET`, bulk mutate -> `GET`, and delete -> `GET` round-trips

## Templates, Data Streams, And Rollover

| Route family | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| Component index templates (`/_component_template`) | Defines reusable template fragments for future index creation and template composition. | Source-owned CRUD/readback anchors and bounded body/readback helpers now exist, but live REST activation is still incomplete. | Planned |
| Composable index templates (`/_index_template`) | Defines higher-level index templates used for future index creation and data streams. | Source-owned CRUD/readback anchors and bounded body/readback helpers now exist, but live REST activation is still incomplete. | Planned |
| Composable template simulation (`/_index_template/_simulate`, `/_index_template/_simulate/{name}`) | Simulates composable-template resolution without committing metadata. | The named/unnamed composable-template simulation surface is still missing as a REST route family; do not treat composable-template persistence as evidence of simulation parity. | Planned |
| Composable index-template simulation (`/_index_template/_simulate_index/{name}`) | Simulates how a target index name would resolve through composable templates without committing metadata. | The index-name-specific simulation surface is also still missing as a REST route family. | Planned |
| Legacy index templates | Older template mechanism used by OpenSearch. | Source-owned CRUD/readback anchors and bounded body/readback helpers now exist, but live REST activation is still incomplete. | Planned |

Keep named and unnamed composable-template simulation in one row for now. They
share the same handler family, status, and missing-parity story, so splitting
them further would add table noise without changing the current contract.

### Component/Composable Template Bounded Contract

- The current source-owned component-template body subset is bounded to:
  - `template`
  - `version`
  - `_meta`
- The current source-owned composable-template body subset is bounded to:
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
- The current bounded selector layer covers:
  - wildcard and comma template-name selectors
- The current source-owned readback helper returns only the named template
  entries selected by that bounded layer.
- This lifts component/composable templates into a concrete source-owned route
  contract without yet claiming full live route activation or simulation parity.
- The current source-owned live hook layer now exists for:
  - component-template readback
  - composable-template readback
  - component-template acknowledged mutation
  - composable-template acknowledged mutation
- Local route-traffic proof now covers:
  - `PUT /_component_template/{name}` -> `GET /_component_template/{name}`
  - `PUT /_index_template/{name}` -> `GET /_index_template/{name}`

### Legacy Template Bounded Contract

- The current source-owned legacy-template body subset is bounded to:
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
- The current bounded selector layer covers:
  - wildcard and comma template-name selectors
- The current source-owned readback helper returns only the named template
  entries selected by that bounded layer.
- This lifts legacy templates into a concrete source-owned route contract
  without yet claiming full live route activation.
- The current source-owned live hook layer now exists for:
  - legacy-template readback
  - legacy-template acknowledged mutation
- Local route-traffic proof now covers:
  - `PUT /_template/{name}` -> `GET /_template/{name}`

### Data Stream And Rollover Fail-Closed Contract

- `Phase A` keeps `/_data_stream/*` and `/{index}/_rollover*` fail closed.
- Fail closed here still means OpenSearch-like error routing:
  - return an error envelope, not a success shell
  - do not return placeholder stats, empty data-stream lists, or synthetic
    rollover acknowledgements
- Keep the unsupported surfaces in two buckets:
  - unsupported data-stream lifecycle surface
  - unsupported rollover lifecycle surface
- Treat those two bucket names as the canonical fail-closed phrases for this
  route family. Do not replace them with looser variants such as
  `missing data-stream support` or `rollover not yet supported` unless a
  broader fail-closed wording pass changes the entire spec set.

Do not shorten these phrases further here. `data-stream` / `rollover`
identifies the family boundary, and `lifecycle surface` keeps the wording tied
to the missing route contract rather than to a vague feature gap.
- Do not claim partial readback parity for `GET /_data_stream*` or partial
  write parity for rollover just because nearby metadata routes exist.
- Dedicated source-owned fail-closed anchors now exist for:
  - `GET /_data_stream`
  - `GET /_data_stream/{name}`
  - `GET /_data_stream/_stats`
  - `PUT /_data_stream/{name}`
  - `DELETE /_data_stream/{name}`
- The current source-owned fail-closed helper returns:
  - `error.type = illegal_argument_exception`
  - `error.reason = unsupported data-stream lifecycle surface`
  - `status = 400`
- Local route-traffic evidence now covers:
  - `GET /_data_stream`
  - `GET /_data_stream/_stats`
  - `PUT /_data_stream/{name}`
  - `DELETE /_data_stream/{name}`
- Dedicated source-owned fail-closed anchors now exist for:
  - `POST /{index}/_rollover`
  - `POST /{index}/_rollover/{new_index}`
- The current source-owned fail-closed helper returns:
  - `error.type = illegal_argument_exception`
  - `error.reason = unsupported rollover lifecycle surface`
  - `status = 400`
- Local route-traffic evidence now covers:
  - `POST /{index}/_rollover`
  - `POST /{index}/_rollover/{new_index}`

## Route-Surface Alignment Rule

- For `_mapping`, `_settings`, alias delete, legacy template routes, and
  component/composable template routes, keep the route-family status aligned to
  the generated route inventory rather than to narrower internal metadata
  persistence.
- Internal development storage or readback is evidence for future route work,
  not proof of current OpenSearch REST parity.
| `/_data_stream` routes | Data stream lifecycle and backing-index management. | Explicitly fail-closed today. Steelsearch rejects data-stream APIs until lifecycle semantics exist. | Planned |
| `/{index}/_rollover` | Rolls write alias or data stream to a new backing index under conditions. | Explicitly fail-closed today. | Planned |

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
