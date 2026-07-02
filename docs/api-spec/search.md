# Search APIs

## Milestone Gate

- Primary gate: `Phase A` standalone replacement.
- Later extension: `Phase B` for external read-only/coordinating interop
  against Java OpenSearch, not peer-node shard execution.
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
| Query DSL | `query_string`, `simple_query_string` | Partial | Live standalone subset now supports bounded query/default-operator/minimum-should-match/field forms, with DSL/native paths preserving the same bounded options; broader syntax, analyzer, and escaping parity remain incomplete. |
| Query DSL | `wildcard`, `prefix` | Partial | Live standalone subset now supports bounded field/value forms plus `case_insensitive` keyword matching; broader rewrite and analyzer parity remain narrower than OpenSearch. |
| Query DSL | `regexp`, `fuzzy` | Partial | Live standalone subset now supports bounded field/value forms with simplified regex, `regexp.case_insensitive`, fuzzy `prefix_length`, fuzzy `transpositions`, and edit-distance semantics; broader rewrite, scoring, and analyzer parity remain narrower than OpenSearch. |
| Query DSL | `exists`, `terms_set`, `nested`, `geo_distance` | Partial | Live standalone subset now supports bounded field presence, set-membership, nested-path, and geo-distance forms; broader script-driven minimum-match, inner-hit, and geo-option parity remain narrower than OpenSearch. |
| Query DSL | `function_score`, `script_score` | Partial | Live standalone subset now supports bounded query-wrapping with constant weight or constant script score; broader function catalogs, scripts, and score-mode parity remain narrower than OpenSearch. |
| Query DSL | `span_term`, `span_or`, `span_near`, `span_multi`, `field_masking_span`, `more_like_this` | Partial | Live standalone subset now supports bounded positional term/combinator and like-text forms; broader span options and term-vector semantics remain narrower than OpenSearch. |
| Query DSL | `intervals` | Partial | Live standalone subset now supports bounded `match`, `prefix`, `wildcard`, `regexp`, `fuzzy`, nested `all_of`/`any_of`, and relation `filter` interval forms with OpenSearch-shaped `ordered`/`mode`/`max_gaps` defaults, match `standard`/`keyword` analyzer handling, regexp `flags`/`flags_value` request parsing, and match/prefix/wildcard/regexp/fuzzy `use_field`; broader analyzer coverage, Lucene-specific regexp flag semantics, script filter, and expansion-limit semantics remain narrower than OpenSearch. |
| Query DSL | Search templates | Partial | Root and targeted search-template, msearch-template, render-template, stored-template lookup, and bounded params substitution are live; full Mustache semantics remain narrower than OpenSearch. |
| Response shaping | sort / pagination / `from` / `size` | Partial | Live and covered by strict compare for the documented standalone contract. |
| Response shaping | aggregations | Partial | Live and clean-pass in the strict lexical search fixture for the documented aggregation families. |
| Response shaping | Highlight | Partial | Live on the standalone route for the documented field/tag contract. |
| Response shaping | Suggest | Partial | Live on the standalone route for term/completion/phrase suggesters. |
| Response shaping | Explain / profile / rescore / collapse / named query hits | Partial | Live on the standalone route for the documented request and response shapes, including bounded `matched_queries` array and `include_named_queries_score` map rendering. |
| Response shaping | Stored fields / docvalue fields / derived fields | Partial | Stored fields, docvalue fields, and bounded request-body `derived` fields are live; request-body `runtime_mappings` remains a Steelsearch-only extension rather than an OpenSearch parity surface. |
| Search session / traversal | Scroll | Partial | Live on the standalone route for open/follow-up/clear traversal. |
| Search session / traversal | PIT | Partial | Live on the standalone route for open/search/list/close traversal plus cat PIT segment readback. |

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
- stored fields, docvalue fields, derived fields;
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
  - `allow_partial_search_results=false` converts the currently modeled
    partial shard failure subset into an explicit search-phase failure instead
    of returning a `200` partial response; this is pinned by
    `partial_shard_failure_geo_disallow_partial_search`
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
  - `search_after` with one or more scalar sort keys for the documented field-sort subset
  - `search_after` against `missing: _last` and bounded custom `missing`
    field-sort results for the documented scalar subset
  - OpenSearch-shaped `search_after: [null]` shard failure for numeric
    field-sort values
  - `unmapped_type` field-sort admission and partial shard failure reporting for mixed mapped/unmapped wildcard targets
- The current source-owned total-hits subset is bounded to:
  - `track_total_hits = true`
  - numeric `track_total_hits` threshold
  - default total-hit accounting for the documented subset
- Current semantics gap:
  - missing sort handling outside the documented scalar subset, broader unmapped
    sort options, and exact tie-breaking beyond the documented scalar
    field-sort subset are still narrower than OpenSearch
  - deep pagination semantics remain narrower than OpenSearch beyond the
    documented scroll / PIT / bounded `search_after` subset

## Aggregations

Current Steelsearch coverage includes the aggregation families that now clean-
pass in the strict search fixture and explicit exclusion of non-parity
extension surfaces. The compatibility notes show support around:

- selected metrics, including bounded metric `missing` replacement values,
  `weighted_avg`, `percentile_ranks`, and `median_absolute_deviation`;
- filter and filters;
- top hits;
- composite;
- significant terms;
- geo bounds and geo centroid;
- selected pipeline aggregations such as `sum_bucket`.

Large remaining OpenSearch aggregation gaps include:

- more bucket families outside the currently evidenced sampler,
  diversified sampler, and variable-width histogram subsets;
- more pipeline aggregations;
- broader scripted aggregation semantics beyond the current bounded `scripted_metric` subset.

Steelsearch-specific plugin aggregations remain extension surfaces and are not
part of the OpenSearch parity target.

### Aggregation Supported-Subset Rule

- The current source-owned aggregation subset is bounded to:
  - selected metrics, including bounded `missing` replacement values for numeric
    metric aggregations
  - date histogram, including keyed bucket output, bounded day offset
    rounding, bounded fixed-step minute/hour/day bucket rounding, bounded
    calendar minute/hour/week/month/year bucket rounding, bounded day
    `extended_bounds` empty bucket expansion, bounded day `hard_bounds`
    bucket-key filtering, bounded `min_doc_count: 1` empty-bucket
    suppression, bounded `format` key string rendering
    (`epoch_millis`, `yyyy-MM-dd HH:mm:ss`,
    `basic_date_time_no_millis`, and `date`), bounded fixed-offset `time_zone`
    rounding/rendering, and bounded string date `missing` replacement values
  - auto date histogram, including bounded day-minimum buckets, bounded
    `format`, bounded fixed-offset `time_zone`, and bounded string date
    `missing` replacement values
  - histogram, including keyed bucket output, bounded numeric offset bucket
    rounding, bounded numeric `extended_bounds` empty bucket expansion, and
    bounded numeric `hard_bounds` bucket-key filtering, bounded
    `min_doc_count: 1` empty-bucket suppression, and bounded numeric `missing`
    replacement values
  - range
  - cardinality
  - weighted average
  - percentile ranks
  - median absolute deviation
  - filter / filters
  - sampler
  - diversified sampler
  - variable-width histogram
  - top hits
  - composite
  - significant terms
  - `terms.order` for `_count` / `_key`
  - bounded `terms.include` / `terms.exclude` filtering, including OpenSearch-style partition include filtering
  - bounded `terms.min_doc_count` bucket suppression
  - bounded `terms.missing` scalar replacement values for keyword buckets
  - `significant_terms.background_filter`
  - bounded `scripted_metric` with
    - `init_script = "state.count = 0"`
    - `map_script = "state.count += params.inc"`
    - `combine_script = "return state.count"`
    - `reduce_script = "double sum = 0; for (s in states) { sum += s } return sum"`
  - geo bounds
  - geo centroid
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
| Search templates | Mustache-backed templated search requests. | Root and targeted `_search/template`, `_msearch/template`, `_render/template`, stored-template lookup, and bounded params substitution are live. | Partial |
| PIT | Point-in-time snapshots for paginated or repeatable search. | PIT open/search/list/close and cat PIT-segments readback are live and covered by strict compare for the documented standalone contract. | Partial |
| Scroll | Stateful paginated search traversal. | Initial scroll search, follow-up page retrieval, and clear-scroll are live and covered by strict compare. | Partial |
| Suggest | Completion/term/phrase suggestion families. | Term/completion/phrase suggesters are live and covered by strict compare for the documented standalone contract. | Partial |
| Search execution mode | `query_then_fetch`, `dfs_query_then_fetch`, pre-filter/can-match shaping knobs. | `query_then_fetch` / `dfs_query_then_fetch` are accepted; `pre_filter_shard_size` is accepted as a no-op in the current single-shard standalone profile. | Partial |
| Highlight, rescore, collapse, profile, explain, stored fields, docvalue fields, derived fields | Advanced request/response controls. | Field highlight plus bounded explain/profile/rescore/collapse/stored-fields/docvalue-fields/request-scoped-derived-field subsets are live. Steelsearch also exposes a bounded `runtime_mappings` passthrough subset, but it is treated as a Steelsearch-only extension rather than an OpenSearch parity surface. | Partial |

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
- `derived` note:
  - OpenSearch request-scoped derived fields are supported for the bounded object-or-string script forms using `emit(doc["field"].value)` and `emit(params._source["field"])`
  - `properties`, `prefilter_field`, `format`, and `ignore_malformed` are accepted with bounded structural validation on request-scoped derived definitions
  - derived fields participate in query matching and `fields` response extraction in the standalone route
- `fields` note:
  - bounded fetch fields support mapped scalar/source extraction and documented
    date formatting behavior
  - `fields[].include_unmapped` is rejected with the OpenSearch
    `[docvalues_field] unknown field [include_unmapped]` parse error for the
    current source profile
- The current live partial response-shaping/suggestion families are:
  - `highlight`
    - top-level `fields`
    - optional `pre_tags` / `post_tags`
    - string field highlight on matched text tokens
    - bounded field-level `no_match_size` snippets for no-match highlight output
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
    - create-PIT `preference` admission in the standalone single-node profile
    - create-PIT `ignore_unavailable=true` admission for mixed existing/missing targets
    - create-PIT `allow_no_indices=true` admission for empty wildcard targets
    - create-PIT order-sensitive `expand_wildcards=none` admission for empty wildcard expansion
    - create-PIT `allow_partial_pit_creation=false` admission for all-success local shard creation
    - create-PIT `routing` admission preserves OpenSearch shard-routing semantics without document filtering
    - `_search` with `pit.id`
    - PIT searches read from the open-time document snapshot rather than later live writes
    - PIT field-sort and `_shard_doc` string/object-form pagination support `search_after`
    - `GET /_search/point_in_time/_all`
    - `DELETE /_search/point_in_time`
    - `DELETE /_search/point_in_time/_all`
    - `GET /_cat/pit_segments` and `GET /_cat/pit_segments/_all`
  - `search_after`
    - one or more scalar sort keys for the documented field-sort subset
    - matching scalar search-after values
    - `missing: _last` and bounded custom `missing` scalar field-sort pagination
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
    - closed-index wildcard expansion is promoted into the strict required set through `expand_wildcards_closed_fail_closed`
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
  - named query hit metadata
    - `_name` query clauses render hit-level `matched_queries`
    - bounded `rescore.query.rescore_query._name` clauses are included in
      hit-level `matched_queries`
    - `include_named_queries_score=true` renders the OpenSearch score-map shape
- Reading rule:
  - if one of these option families appears on the active `_search` surface,
    read it according to the documented family-specific contract rather than
    implying full OpenSearch parity
- Search templates are a bounded live surface, not a full Mustache
  completeness claim.

## Notes

- Search is one of the most mature parts of the current Steelsearch surface,
  but it is still not a claim of full production or mixed-cluster OpenSearch parity.
- The machine-readable route and action inventory is more exhaustive than this
  prose doc, but this doc should be the human entry point for deciding whether a
  search-facing OpenSearch workflow can already be migrated.
