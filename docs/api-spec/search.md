# Search APIs

## Milestone Gate

- Primary gate: `Phase A` standalone replacement.
- Later extension: `Phase B` for read-only or coordinating interop against Java
  OpenSearch.
- Final extension: `Phase C` for same-cluster search routing and shard-phase
  behavior that depends on mixed-node participation.

## Core Search Routes

| Route | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `GET /_search`, `POST /_search` | Search across all or selected targets, supporting Query DSL, aggregation, sorting, pagination, and response controls. | Implemented for a supported subset of query, sort, pagination, aggregation, alias/wildcard expansion, and error-shape compatibility. | Partial |
| `GET /{index}/_search`, `POST /{index}/_search` | Same as above, constrained to explicit targets. | Implemented for the same supported subset. | Partial |

## `Phase A` Search Support Matrix

| Search surface | Query family / option family | `Phase A` posture | Current contract |
| --- | --- | --- | --- |
| Core `_search` execution | Route shell | Partial | Rust-native lexical/vector/hybrid search for the documented subset. |
| Query DSL | `term` | Partial | Bounded exact-match lexical request/response subset only. |
| Query DSL | `match` | Partial | Bounded analyzed-text request/response subset only. |
| Query DSL | `bool` | Partial | Bounded composition over already supported child queries only. |
| Query DSL | `range` | Partial | Bounded numeric/date range subset only. |
| Query DSL | `k-NN` / hybrid | Partial | Present for the documented Rust-native vector/hybrid subset, not full OpenSearch parity. |
| Query DSL | `multi_match`, phrase, dis-max, ids, query-string | Explicit fail-closed | Live `_search` query families outside the current proven subset; reject on the active route surface. |
| Query DSL | wildcard / prefix / regexp / fuzzy full parity | Explicit fail-closed | Do not imply wider text-query parity beyond the documented bounded subset. |
| Query DSL | nested / geo / span / intervals / function-score / script-score | Explicit fail-closed | Advanced query families remain outside the current live `_search` contract. |
| Query DSL | Search templates | Planned | Present in OpenSearch inventory, not exposed by Steelsearch today. |
| Response shaping | sort / pagination / `from` / `size` | Partial | Supported only for the documented bounded subset. |
| Response shaping | aggregations | Partial | Supported only for the documented aggregation families and bounded response shapes. |
| Response shaping | Highlight | Explicit fail-closed | Advanced `_search` response-shaping option; reject it on the live `_search` surface outside a proven subset. |
| Response shaping | Suggest | Explicit fail-closed | `_search` option family, not a separate planned route; reject it on the live `_search` surface. |
| Response shaping | Explain / profile / rescore / collapse | Explicit fail-closed | Advanced response-shaping and scoring controls remain outside the current supported subset. |
| Response shaping | Stored fields / docvalue fields / runtime fields | Explicit fail-closed | Do not imply partial field-shaping parity unless a narrower subset is documented separately. |
| Search session / traversal | Scroll | Explicit fail-closed | Continuation semantics on the live `_search` surface; reject until explicitly supported. |
| Search session / traversal | PIT | Explicit fail-closed | Point-in-time option on the live `_search` surface; reject until explicitly supported. |

Use `Explicit fail-closed` when Steelsearch already needs to reject that
request-shape family as part of the current `_search` surface. Use `Planned`
when the surface is still only tracked from OpenSearch inventory and is not yet
part of the active Steelsearch `_search` contract at all.

## Query DSL

Current Steelsearch support is a subset. OpenSearch source and replacement plan
show many query families still missing or only partially modeled.

### Supported Direction

Current implementation includes:

- basic lexical search over the Rust-native engine;
- selected bool/term/match-style query behavior;
- selected sort, pagination, and wildcard/alias target expansion;
- selected k-NN and hybrid search integration.

### Current Supported-Subset Semantics Gaps

- `term`
  - bounded exact-match request/response contract exists
  - analyzer, keyword-normalization, and field-mapping edge semantics are still
    narrower than OpenSearch
- `match`
  - bounded analyzed-text request/response contract exists
  - fuzziness, operator, minimum-should-match, and analyzer override semantics
    are still narrower than OpenSearch
- `bool`
  - bounded composition over supported child queries exists
  - nested bool rewriting, clause explosion limits, and subtle scoring/coord
    interactions remain narrower than OpenSearch
- `range`
  - bounded numeric/date range request subset exists
  - full date-math, format, time-zone, relation, and inclusive-boundary edge
    semantics remain narrower than OpenSearch
- `k-NN` / hybrid
  - bounded vector/hybrid request subset exists
  - exact score fusion, tie-breaking, and mixed lexical/vector ranking behavior
    remain narrower than OpenSearch

### Major Remaining Query Families

Still incomplete relative to OpenSearch:

- phrase and multi-match families;
- dis-max;
- ids;
- query-string;
- fuzzy, regexp, prefix, wildcard parity;
- nested;
- function score and script score;
- geo queries;
- spans;
- intervals;
- templates;
- plugin query extension points.

## Search Response And Search Phases

OpenSearch search compatibility also requires:

- can-match and DFS/query-then-fetch semantics;
- fetch subphases;
- highlighting;
- explain and profiling;
- collapse and rescore;
- search-after;
- PIT and scroll;
- slicing;
- timeout and terminate-after;
- track-total-hits parity;
- stored fields, docvalue fields, runtime fields;
- shard failure reporting.

Steelsearch currently implements a narrower development-compatible subset and
fail-closes many advanced options.

### Shard Failure And Partial Failure Rule

- The current source-owned search failure subset is bounded to:
  - top-level `error` envelope for request-level failures
  - `_shards.total`
  - `_shards.successful`
  - `_shards.failed`
- Current partial-failure reading rule:
  - a bounded `hits` / `aggregations` response may still need `_shards.failed`
    accounting preserved when execution is only partially successful
  - the current Phase A contract does not yet imply full OpenSearch parity for
    shard-level reason text, remote-shard attribution, or mixed-cluster phase
    failure propagation
- Do not treat a `200` search response as proof of full shard-phase parity
  unless `_shards` accounting and documented partial-failure semantics also
  match the bounded contract.

## Sort, Pagination, And Total-Hits Rule

- The current source-owned `sort` subset is bounded to:
  - field sort on documented scalar fields
  - `_score` ordering for supported query families
- The current source-owned pagination subset is bounded to:
  - `from`
  - `size`
- The current source-owned total-hits subset is bounded to:
  - `track_total_hits = true`
  - default total-hit accounting for the documented subset
- Current semantics gap:
  - multi-key sort parity, missing/unmapped handling, and exact tie-breaking are
    still narrower than OpenSearch
  - deep pagination and search-after style traversal remain outside the current
    bounded subset
  - non-default `track_total_hits` forms remain narrower than OpenSearch unless
    documented separately

## Aggregations

Current Steelsearch coverage includes selected implemented families and explicit
fail-closed behavior for unsupported ones. The compatibility notes show
implemented or partially implemented support around:

- selected metrics;
- filter and filters;
- top hits;
- composite;
- significant terms;
- geo bounds;
- selected pipeline aggregations such as `sum_bucket`.

Large remaining OpenSearch aggregation gaps include:

- histogram and date histogram parity;
- range families;
- cardinality and broader metrics parity;
- more bucket families;
- more pipeline aggregations;
- scripted aggregations;
- plugin aggregations and exact option parity.

### Aggregation Supported-Subset Rule

- The current source-owned aggregation subset is bounded to:
  - selected metrics
  - filter / filters
  - top hits
  - composite
  - significant terms
  - geo bounds
  - selected pipeline aggregations such as `sum_bucket`
- The current bounded response-shape contract keeps:
  - stable aggregation names
  - bucket keys
  - `doc_count`
  - metric `value`
  - documented nested bucket/value structures for the supported families
- Current numeric semantics gap:
  - floating-point formatting and exact rounding parity remain narrower than
    OpenSearch
  - histogram/date-histogram bucket boundary semantics remain outside the
    current supported subset
  - scripted and plugin aggregation numeric behavior is not implied by this
    bounded family list

## Search Templates, PIT, Scroll, Suggest, And Advanced Options

| API family | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| Search templates | Mustache-backed templated search requests. | Present in OpenSearch source inventory, not implemented in Steelsearch replacement surface. | Planned |
| PIT | Point-in-time snapshots for paginated or repeatable search. | Present in OpenSearch source inventory. Not complete in Steelsearch. | Planned |
| Scroll | Stateful paginated search traversal. | Present in OpenSearch source inventory. Not complete in Steelsearch. | Planned |
| Suggest | Completion/term/phrase suggestion families. | Not a complete Steelsearch surface today. | Planned |
| Highlight, rescore, collapse, profile, explain, stored fields, docvalue fields | Advanced request/response controls. | Many are explicitly fail-closed today. | Planned |

### Advanced Search Option Fail-Closed Rule

- The current live `_search` fail-closed option families are:
  - `highlight`
  - `suggest`
  - `scroll`
  - `pit`
  - `profile`
  - `explain`
  - `rescore`
  - `collapse`
  - `stored_fields`
  - `docvalue_fields`
  - `runtime_mappings`
- Reading rule:
  - if one of these option families appears on the active `_search` surface,
    treat it as a bounded fail-closed contract rather than as implied partial
    support
  - do not silently degrade these options into a success-path subset unless a
    narrower family-specific contract is documented separately
- Search templates remain a separate `Planned` surface, not a live `_search`
  option family inside the current Phase A route contract.

## Notes

- Search is one of the most mature parts of the current Steelsearch surface,
  but it is still a subset implementation.
- The machine-readable route and action inventory is more exhaustive than this
  prose doc, but this doc should be the human entry point for deciding whether a
  search-facing OpenSearch workflow can already be migrated.
