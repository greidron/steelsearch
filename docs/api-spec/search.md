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
| `GET /_search`, `POST /_search` | Search across all or selected targets, supporting Query DSL, aggregation, sorting, pagination, and response controls. | Live standalone route family with strict common-baseline and feature-profile evidence for lexical, execution, aggregation, session, and response-shaping surfaces documented below. | Partial |
| `GET /{index}/_search`, `POST /{index}/_search` | Same as above, constrained to explicit targets. | Live standalone route family with the same profile-backed contract and target-scoped semantics. | Partial |

## `Phase A` Search Support Matrix

| Search surface | Query family / option family | `Phase A` posture | Current contract |
| --- | --- | --- | --- |
| Core `_search` execution | Route shell | Partial | Live standalone execution surface with strict lexical and execution-profile coverage. |
| Query DSL | `term` | Partial | Mapping-aware exact/token semantics are live on the standalone route. |
| Query DSL | `match` | Partial | Live analyzed-text semantics for the standalone parity profile. |
| Query DSL | `bool` | Partial | Live composition over the documented child query families, including hybrid ranking flows used by the vector profile. |
| Query DSL | `range` | Partial | Live numeric/date range semantics for the standalone parity profile. |
| Query DSL | `k-NN` / hybrid | Partial | Live and strict-profile-backed through the dedicated `vector-ml` profile. |
| Query DSL | `multi_match`, phrase, dis-max, ids | Partial | Live standalone subset is now implemented for bounded request shapes; exact scoring and edge options remain narrower than OpenSearch. |
| Query DSL | `query_string`, `simple_query_string` | Partial | Live standalone subset now supports bounded query/default-operator/field forms; broader syntax, analyzer, and escaping parity remain incomplete. |
| Query DSL | `wildcard`, `prefix` | Partial | Live standalone subset now supports bounded field/value forms; broader rewrite and analyzer parity remain narrower than OpenSearch. |
| Query DSL | `regexp`, `fuzzy` | Partial | Live standalone subset now supports bounded field/value forms with simplified regex and edit-distance semantics; broader rewrite, scoring, and analyzer parity remain narrower than OpenSearch. |
| Query DSL | `exists`, `terms_set`, `nested`, `geo_distance` | Partial | Live standalone subset now supports bounded field presence, set-membership, nested-path, and geo-distance forms; broader script-driven minimum-match, inner-hit, and geo-option parity remain narrower than OpenSearch. |
| Query DSL | `function_score`, `script_score` | Partial | Live standalone subset now supports bounded query-wrapping with constant weight or constant script score; broader function catalogs, scripts, and score-mode parity remain narrower than OpenSearch. |
| Query DSL | `span_term`, `span_or`, `span_near`, `span_multi`, `field_masking_span`, `more_like_this` | Partial | Live standalone subset now supports bounded positional term/combinator and like-text forms; broader span options and term-vector semantics remain narrower than OpenSearch. |
| Query DSL | `intervals` | Partial | Live standalone subset now supports bounded `match` and ordered `all_of` interval forms; broader filter/any_of/max_gaps semantics remain narrower than OpenSearch. |
| Query DSL | Search templates | Planned | Present in OpenSearch inventory, not exposed by Steelsearch today. |
| Response shaping | sort / pagination / `from` / `size` | Partial | Live and covered by strict compare for the documented standalone contract. |
| Response shaping | aggregations | Partial | Live and clean-pass in the strict lexical search fixture for the documented aggregation families. |
| Response shaping | Highlight | Partial | Live on the standalone route for the documented field/tag contract. |
| Response shaping | Suggest | Partial | Live on the standalone route for term/completion/phrase suggesters. |
| Response shaping | Explain / profile / rescore / collapse | Partial | Live on the standalone route for the documented request and response shapes. |
| Response shaping | Stored fields / docvalue fields / runtime fields | Partial | Stored fields and docvalue fields are live; request-body `runtime_mappings` remains a Steelsearch-only extension rather than an OpenSearch parity surface. |
| Search session / traversal | Scroll | Partial | Live on the standalone route for open/follow-up/clear traversal. |
| Search session / traversal | PIT | Partial | Live on the standalone route for open/search/close traversal. |

Use `Explicit fail-closed` when Steelsearch already needs to reject that
request-shape family as part of the current `_search` surface. Use `Planned`
when the surface is still only tracked from OpenSearch inventory and is not yet
part of the active Steelsearch `_search` contract at all.

## Query DSL

Current Steelsearch search support is now a profile-backed standalone surface.
The remaining non-claims in this document are broader semantic gaps relative to
OpenSearch, not placeholders for a still-bounded development shell.

### Supported Direction

Current implementation includes:

- basic lexical search over the Rust-native engine;
- selected bool/term/match/multi-match/phrase/dis-max/ids query behavior;
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

Steelsearch now serves these advanced controls on the live standalone route.
The remaining differences called out here are narrower semantic deltas, not a
development-only staging surface.

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
  - numeric `track_total_hits` threshold
  - default total-hit accounting for the documented subset
- Current semantics gap:
  - multi-key sort parity, missing/unmapped handling, and exact tie-breaking are
    still narrower than OpenSearch
  - deep pagination semantics remain narrower than OpenSearch beyond the
    documented scroll / PIT / single-key `search_after` subset

## Aggregations

Current Steelsearch coverage includes the aggregation families that now clean-
pass in the strict search fixture and explicit exclusion of non-parity
extension surfaces. The compatibility notes show support around:

- selected metrics;
- filter and filters;
- top hits;
- composite;
- significant terms;
- geo bounds;
- selected pipeline aggregations such as `sum_bucket`.

Large remaining OpenSearch aggregation gaps include:

- more bucket families;
- more pipeline aggregations;
- broader scripted aggregation semantics beyond the current bounded `scripted_metric` subset.

Steelsearch-specific plugin aggregations remain extension surfaces and are not
part of the OpenSearch parity target.

### Aggregation Supported-Subset Rule

- The current source-owned aggregation subset is bounded to:
  - selected metrics
  - date histogram
  - histogram
  - range
  - cardinality
  - filter / filters
  - top hits
  - composite
  - significant terms
  - `terms.order` for `_count` / `_key`
  - `significant_terms.background_filter`
  - bounded `scripted_metric` with
    - `init_script = "state.count = 0"`
    - `map_script = "state.count += params.inc"`
    - `combine_script = "return state.count"`
    - `reduce_script = "double sum = 0; for (s in states) { sum += s } return sum"`
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
    - scripted and plugin aggregation numeric behavior is not implied by this
    bounded family list

## Search Templates, PIT, Scroll, Suggest, And Advanced Options

| API family | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| Search templates | Mustache-backed templated search requests. | Present in OpenSearch source inventory, not implemented in Steelsearch replacement surface. | Planned |
| PIT | Point-in-time snapshots for paginated or repeatable search. | PIT open/search/close is live and covered by strict compare for the documented standalone contract. | Partial |
| Scroll | Stateful paginated search traversal. | Initial scroll search, follow-up page retrieval, and clear-scroll are live and covered by strict compare. | Partial |
| Suggest | Completion/term/phrase suggestion families. | Term/completion/phrase suggesters are live and covered by strict compare for the documented standalone contract. | Partial |
| Search execution mode | `query_then_fetch`, `dfs_query_then_fetch`, pre-filter/can-match shaping knobs. | `query_then_fetch` / `dfs_query_then_fetch` are accepted; `pre_filter_shard_size` is accepted as a no-op in the current single-shard standalone profile. | Partial |
| Highlight, rescore, collapse, profile, explain, stored fields, docvalue fields | Advanced request/response controls. | Field highlight plus bounded explain/profile/rescore/collapse/stored-fields/docvalue-fields subsets are live. Steelsearch also exposes a bounded `runtime_mappings` passthrough subset, but it is treated as a Steelsearch-only extension rather than an OpenSearch parity surface. | Partial |

### Advanced Search Option Reading Rule

- The current live `_search` route no longer relies on a generic "advanced
  option fail-closed bucket" for the documented standalone contract.
- Unsupported search behavior should now be read as one of:
  - an explicit later-phase non-claim;
  - a Steelsearch-only extension surface;
  - a target-expansion or environment-specific defer that is owned by another
    profile.
- `runtime_mappings` note:
  - Steelsearch implements a bounded `emit(doc['field'].value)` passthrough subset
  - current OpenSearch evidence across the local source tree plus representative `1.x`/`2.x`/`3.x` builds does not show request-body `runtime_mappings` parity support
  - therefore this surface is excluded from Phase A-1 OpenSearch fullset closure and treated as a Steelsearch-only extension
- The current live partial response-shaping/suggestion families are:
  - `highlight`
    - top-level `fields`
    - optional `pre_tags` / `post_tags`
    - string field highlight on matched text tokens
  - `suggest`
    - named term suggester entries with `text` + `term.field`
    - named completion suggester entries with `prefix` + `completion.field`
    - named phrase suggester entries with `text` + `phrase.field`
  - `scroll`
    - `_search?scroll=...`
    - `POST /_search/scroll`
    - `DELETE /_search/scroll`
  - `pit`
    - `POST /{index}/_search/point_in_time`
    - `_search` with `pit.id`
    - `DELETE /_search/point_in_time`
  - `search_after`
    - single sort key
    - single search-after scalar
  - search execution mode controls
    - `search_type=query_then_fetch`
    - `search_type=dfs_query_then_fetch`
    - `pre_filter_shard_size`
    - `search-execution` profile additionally covers:
      - multi-shard `_shards.total|successful|failed` accounting
      - mixed-mapping `geo_distance` induced shard failure with partial-success hits retained
      - true can-match pruning with `_shards.skipped > 0` via source-capable `match_none` and date-range fixtures
    - note: common-baseline single-node probing, including a 2-primary-shard index, still observed `_shards.skipped = 0`, so can-match pruning evidence remains owned by the feature profile rather than baseline parity
    - induced timeout / `timed_out=true` is no longer treated as a Phase A-1 parity blocker: representative source-build probes have not yielded a deterministic timeout profile, so any strict source compare follow-up is deferred to Phase B / feature-profile research
  - `_cat` search-adjacent operator surfaces
    - `/_cat/indices?format=json`
    - `/_cat/indices?v=true`
    - `/_cat/count?format=json`
    - `/_cat/count?v=true`
  - search strict fixture
    - `--scope search` now defaults to `tools/fixtures/search-strict-compat.json`
    - vector/development-only and root-cluster operational probe cases are excluded from the lexical strict fixture and owned by their separate profiles or deferred scopes
    - the only remaining skip in the lexical strict fixture is the explicit out-of-phase defer for closed-index wildcard expansion
  - numeric `track_total_hits`
  - `terminate_after`
  - `timeout`
  - `explain`
    - hit-level `_explanation` presence
    - bounded value/description/details shape
  - `profile`
    - top-level `profile.shards`
    - bounded query/collector tree presence
  - `rescore`
    - bounded `window_size`
    - bounded `query.rescore_query`
    - bounded query/rescore weights
  - `collapse`
    - single `field`
    - first-hit-per-group collapse over the active hit order
- Reading rule:
  - if one of these option families appears on the active `_search` surface,
    read it according to the documented family-specific contract rather than
    implying full OpenSearch parity
- Search templates remain a separate `Planned` surface, not a live `_search`
  option family inside the current Phase A route contract.

## Notes

- Search is one of the most mature parts of the current Steelsearch surface,
  but it is still not a claim of full production or mixed-cluster OpenSearch parity.
- The machine-readable route and action inventory is more exhaustive than this
  prose doc, but this doc should be the human entry point for deciding whether a
  search-facing OpenSearch workflow can already be migrated.
