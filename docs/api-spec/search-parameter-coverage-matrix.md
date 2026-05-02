# Search Parameter Coverage Matrix

This matrix tracks search-facing parameter coverage at a finer level than route
parity. The goal is to answer a narrower question:

- for a given query, ranking, aggregation, suggest, highlight, or vector
  parameter family,
- is Steelsearch implemented,
- is it covered by strict compare,
- is it covered by semantic probes,
- does unsupported behavior fail closed,
- and what is still missing before replacement claims are safe.

## Column Definitions

| Column | Meaning |
| --- | --- |
| `Family` | Parameter or DSL family being tracked. |
| `Surface` | Route family where the parameter matters, such as `/_search`, `/{index}/_search`, `_msearch`, or template-search surfaces. |
| `Implemented` | `yes`, `partial`, or `no` based on the current runtime behavior. |
| `Strict compared` | Whether the family is represented in `search-strict-compat.json` and expected to match canonicalized OpenSearch output closely. |
| `Semantic probed` | Whether the family is pinned by a lighter semantic probe or compare fixture even when strict parity is not claimed. |
| `Fail closed` | Whether unsupported or incomplete variants return an explicit failure rather than being silently ignored. |
| `Evidence` | Primary fixture, code, or artifact that currently backs the claim. |
| `Code path / missing path` | The current handler/evaluator location in `standalone_runtime.rs`, or an explicit note that no dedicated handler/evaluator exists yet. |
| `Notes / missing work` | Why the family is still partial and what remains to close it. |

## Query-String Parameters

| Family | Surface | Implemented | Strict compared | Semantic probed | Fail closed | Evidence | Code path / missing path | Notes / missing work |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `from` / `size` | `/_search`, `/{index}/_search` | partial | yes | yes | partial | `tools/fixtures/search-strict-compat.json`, `tools/fixtures/search-semantic-compat.json` | `handle_index_search_route` at [standalone_runtime.rs:5667](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5667) applies pagination after query evaluation. | Semantic smoke now pins sorted windowing; unsupported pagination combinations still need negative expansion. |
| `sort` | `/_search`, `/{index}/_search` | partial | yes | yes | partial | `tools/fixtures/search-strict-compat.json`, `tools/fixtures/search-semantic-compat.json` | `apply_search_sort` at [standalone_runtime.rs:13296](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:13296); request validation in [standalone_runtime.rs:12283](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12283). | Sorted window coverage exists in both strict and semantic suites; unsupported sort variants still need explicit audit. |
| `track_total_hits` | `/_search`, `/{index}/_search` | partial | yes | yes | partial | `tools/fixtures/search-strict-compat.json`, `tools/fixtures/search-semantic-compat.json` | handled in request validation and response shaping at [standalone_runtime.rs:12283](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12283) and [standalone_runtime.rs:5869](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5869). | `true` and threshold forms are now both pinned, but route/profile matrix expansion is still pending. |
| `allow_no_indices` | `/_search`, `/{index}/_search`, `_count` | partial | yes | yes | partial | `tools/fixtures/search-strict-compat.json`, `tools/fixtures/search-semantic-compat.json` | search target resolution in [standalone_runtime.rs:3135](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:3135) and [standalone_runtime.rs:12034](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12034); `_count` path is bounded in `handle_count_route` at [standalone_runtime.rs:5350](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5350). | Search empty-wildcard coverage exists in strict and semantic suites. `_count` now has semantic evidence for empty wildcard and `allow_no_indices=true`, both returning bounded `200 + count=0`. |
| `ignore_unavailable` | `/_search`, `/{index}/_search` | partial | yes | yes | partial | `tools/fixtures/search-strict-compat.json`, `tools/fixtures/search-semantic-compat.json` | target resolution in [standalone_runtime.rs:3135](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:3135) and [standalone_runtime.rs:12034](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12034). | Multi-target missing-index behavior is now pinned in strict and semantic suites; negative matrix expansion is still pending. |
| `q` query-string search | `_count` | no | no | yes | yes | `tools/fixtures/search-semantic-compat.json`, `crates/os-node/src/standalone_runtime.rs` | `handle_count_route` at [standalone_runtime.rs:5350](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5350) rejects `request.query_params["q"]` via `build_unsupported_search_response`. | `_count` now explicitly supports body `query` only. If `q` is present, Steelsearch returns `400 illegal_argument_exception` instead of choosing a precedence rule between `q` and body `query`. |
| `rewrite` / explain-style validate options | `/_validate/query`, `/{index}/_validate/query` | partial | no | yes | partial | `tools/fixtures/search-semantic-compat.json`, `crates/os-node/src/standalone_runtime.rs` | `handle_validate_query_route` at [standalone_runtime.rs:5470](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5470) now rejects `rewrite` via `build_unsupported_search_response`; no dedicated handling exists for any broader explain-style validate option set. | `rewrite=true` is now fail-closed and pinned on targeted wildcard validate routes. Broader explain-style validate options still remain unsupported/documented only. |

## Body Query DSL Families

| Family | Surface | Implemented | Strict compared | Semantic probed | Fail closed | Evidence | Code path / missing path | Notes / missing work |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `match_all` | `/_search`, `/{index}/_search`, `_count` | yes | partial | yes | n/a | `tools/fixtures/search-semantic-compat.json`, `crates/os-node/src/standalone_runtime.rs` | `matches_query_body` at [standalone_runtime.rs:15822](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15822); count path in [standalone_runtime.rs:5329](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5329). | Basic search/count semantics are pinned. `_count` now also pins current bounded policy that both empty wildcard targets and missing exact indices return `200 + count=0`. |
| `term` | `/_search`, `/{index}/_search`, `_count`, `_explain` | yes | yes | yes | n/a | `tools/fixtures/search-strict-compat.json`, `tools/fixtures/search-semantic-compat.json` | `matches_query_body` at [standalone_runtime.rs:15822](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15822); explain path in [standalone_runtime.rs:5496](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5496). | One of the strongest covered lexical families. |
| `match` | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | `matches_query_body` at [standalone_runtime.rs:15822](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15822). | Covered in broad compat cases, but missing dedicated semantic matrix and unsupported-option audit. |
| `multi_match` | `/_search`, `/{index}/_search` | partial | yes | no | partial | `tools/fixtures/search-strict-compat.json` | evaluated through `matches_query_body` / search path at [standalone_runtime.rs:5667](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5667) and [standalone_runtime.rs:15822](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15822). | Best-fields coverage exists; broader modes still need explicit status. |
| `match_phrase` | `/_search`, `/{index}/_search` | partial | yes | no | partial | `tools/fixtures/search-strict-compat.json` | lexical evaluation in [standalone_runtime.rs:15822](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15822). | Core phrase path is present; edge parameters still need audit. |
| `match_phrase_prefix` | `/_search`, `/{index}/_search` | partial | yes | no | partial | `tools/fixtures/search-strict-compat.json` | lexical evaluation in [standalone_runtime.rs:15822](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15822). | Prefix phrase case exists; unsupported variants still need fail-closed policy. |
| `bool` | `/_search`, `/{index}/_search` | partial | yes | no | partial | `tools/fixtures/search-strict-compat.json` | lexical evaluation in [standalone_runtime.rs:15822](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15822). | Filter/range combination is covered; larger bool matrix is still missing. |
| `range` | `/_search`, `/{index}/_search` | partial | yes | no | partial | `tools/fixtures/search-strict-compat.json` | lexical evaluation in [standalone_runtime.rs:15822](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15822). | Present through bool/range strict cases; standalone range-family row is still partial. |
| `dis_max` | `/_search`, `/{index}/_search` | partial | yes | no | partial | `tools/fixtures/search-strict-compat.json` | lexical evaluation in [standalone_runtime.rs:15822](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15822). | Strict case exists; broader tie-breaker/option coverage still missing. |
| `ids` | `/_search`, `/{index}/_search` | partial | yes | no | partial | `tools/fixtures/search-strict-compat.json` | lexical evaluation in [standalone_runtime.rs:15822](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15822). | Positive path is covered; failure-path and wildcard interactions remain undocumented. |
| `function_score` | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | no dedicated `function_score` handler; current support is routed through generic search evaluation at [standalone_runtime.rs:5667](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5667). | Broad compare exists; strict/semantic claim is not yet established. |
| `script_score` | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | no dedicated `script_score` evaluator separate from generic query handling; current support is partial at [standalone_runtime.rs:5667](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5667). | Broad compare exists; script semantics and fail-closed coverage remain incomplete. |
| invalid/unsupported query type | `/_validate/query`, `/_search`, `_count` | partial | no | yes | partial | `tools/fixtures/search-semantic-compat.json` | `_validate/query` handler at [standalone_runtime.rs:5448](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5448); `_count` validation in [standalone_runtime.rs:5350](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5350); unsupported search validation at [standalone_runtime.rs:12283](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12283). | `_validate/query` invalid/empty semantics are pinned. `_count` now fail-closes unsupported query types and malformed JSON payloads with explicit `400` envelopes. `_search` invalid DSL audit still needs to be formalized. |

## Ranking And Pagination Families

| Family | Surface | Implemented | Strict compared | Semantic probed | Fail closed | Evidence | Code path / missing path | Notes / missing work |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sorted result window | `/_search`, `/{index}/_search` | partial | yes | no | partial | `tools/fixtures/search-strict-compat.json` | `apply_search_sort` at [standalone_runtime.rs:13296](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:13296). | Happy-path sort window exists; unsupported sort keys still need explicit policy. |
| `search_after` | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | `apply_search_after` at [standalone_runtime.rs:13343](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:13343); validation at [standalone_runtime.rs:12307](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12307). | Broad compare exists, but strict/semantic matrix is not yet defined. |
| `collapse` | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | `apply_search_collapse` at [standalone_runtime.rs:13497](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:13497). | Needs explicit strict-vs-semantic classification. |
| `rescore` | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | `apply_search_rescore` at [standalone_runtime.rs:13448](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:13448); request validation at [standalone_runtime.rs:12321](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12321). | Coverage exists in broad compare only. |
| `profile` | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | no dedicated profiling subsystem; current support is bounded search response shaping inside [standalone_runtime.rs:5667](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5667). | Needs dedicated report expectations and unsupported-option audit. |
| `rank_eval` | `/_rank_eval`, `/{index}/_rank_eval` | partial | no | yes | partial | stateful probe + runtime tests | `handle_rank_eval_route` is outside the main search evaluator path; route dispatch is present but not a full ranking framework replacement. | Route and basic contract exist, but this matrix tracks only minimal semantic evidence today. |

## Highlight And Suggest Families

| Family | Surface | Implemented | Strict compared | Semantic probed | Fail closed | Evidence | Code path / missing path | Notes / missing work |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `highlight` | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | request validation at [standalone_runtime.rs:12292](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12292); rendering at [standalone_runtime.rs:14028](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:14028). | Broad compare cases exist; strict/negative coverage remains incomplete. |
| `term suggest` | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | request validation at [standalone_runtime.rs:12572](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12572); response builder at [standalone_runtime.rs:14169](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:14169). | Exists in broad compare, but no dedicated semantic matrix yet. |
| `phrase suggest` | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | request validation at [standalone_runtime.rs:12572](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12572); response builder at [standalone_runtime.rs:14169](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:14169). | Same as above. |
| `completion suggest` | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | request validation at [standalone_runtime.rs:12572](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12572); response builder at [standalone_runtime.rs:14169](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:14169). | Same as above. |

## Aggregation Families

| Family | Surface | Implemented | Strict compared | Semantic probed | Fail closed | Evidence | Code path / missing path | Notes / missing work |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| metric aggregations | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | aggregation builder at [standalone_runtime.rs:15117](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15117). | Broad compare exists; strict/semantic classification still needs to be split by aggregation family. |
| filter aggregations | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | aggregation builder at [standalone_runtime.rs:15117](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15117). | Broad compare exists; more explicit family-level matrix is pending. |

## Template Search Families

| Family | Surface | Implemented | Strict compared | Semantic probed | Fail closed | Evidence | Code path / missing path | Notes / missing work |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stored/named template render | `/_render/template`, `/_render/template/{id}` | partial | no | yes | partial | `tools/fixtures/search-semantic-compat.json`, `standalone_runtime.rs` unit tests | template resolution in `search_template_search_body` / related template helpers around [standalone_runtime.rs:5263](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5263). | Render endpoints are part of the same semantic matrix, and missing-param, extra-param ignore, malformed-source fail-closed, plus stored-script overwrite readback are now pinned. |
| stored/named template search | `/_search/template`, `/{index}/_search/template` | partial | no | yes | partial | `tools/fixtures/search-semantic-compat.json`, `standalone_runtime.rs` unit tests | `handle_search_template_route` at [standalone_runtime.rs:4709](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:4709); template expansion at [standalone_runtime.rs:5263](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5263). | Named template substitution, missing-params behavior, extra-param ignore behavior, malformed-source fail-closed, and stored-script overwrite consistency are pinned semantically; strict compare matrix is still open. |
| multi-search template | `/_msearch/template`, `/{index}/_msearch/template` | partial | no | no | partial | runtime + stateful probes | `handle_msearch_template_route` at [standalone_runtime.rs:4746](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:4746); no dedicated multi-request template semantic matrix yet. | Route exists, but parameter/multi-request semantic matrix is still missing. |

## Vector / k-NN Families

| Family | Surface | Implemented | Strict compared | Semantic probed | Fail closed | Evidence | Code path / missing path | Notes / missing work |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `knn` basic query | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | target capability validation at [standalone_runtime.rs:12177](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12177); query scoring at [standalone_runtime.rs:13953](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:13953). | Broad compare exists; ranking parity and profile-specific matrix still need work. |
| cosine / inner-product variants | `/_search`, `/{index}/_search` | partial | partial | no | partial | `tools/fixtures/search-compat.json` | vector scoring path at [standalone_runtime.rs:13953](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:13953) and [standalone_runtime.rs:15002](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15002). | Variant-specific broad compare exists. |
| unsupported method / mode / parameters | `/_search`, `/{index}/_search` | partial | partial | no | yes | `tools/fixtures/search-compat.json` | explicit negative validation in [standalone_runtime.rs:12177](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12177) and [standalone_runtime.rs:12747](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12747). | Negative vector fail-closed coverage exists, but should be pulled into a more explicit negative matrix. |


## Ignored Or Partial Body-Field Inventory

This table tracks top-level search body fields that are either:

- explicitly consumed today;
- explicitly rejected today; or
- not yet backed by a dedicated handler/evaluator path and therefore require a
  fail-closed vs documented-partial decision.

| Field | Current status | Evidence | Notes / next action |
| --- | --- | --- | --- |
| `query` | consumed | `validate_search_query_body` at [standalone_runtime.rs:12699](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12699), evaluation via [standalone_runtime.rs:5667](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5667) | Primary supported body field. |
| `aggs` | consumed | `build_search_aggregations` at [standalone_runtime.rs:15117](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:15117) | Partial aggregation family support. |
| `sort` | consumed | `apply_search_sort` at [standalone_runtime.rs:13296](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:13296) | Needs broader unsupported-option audit. |
| `from` / `size` | consumed | pagination in [standalone_runtime.rs:5878](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5878) | Supported on main search route; needs matrix expansion. |
| `terminate_after` | consumed | truncation logic at [standalone_runtime.rs:5861](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5861) | Not yet covered by dedicated compare fixture. |
| `track_total_hits` | consumed + partially validated | validation at [standalone_runtime.rs:12283](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12283), response shaping at [standalone_runtime.rs:5869](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5869) | Strict coverage exists for selected forms only. |
| `highlight` | consumed + validated | validation at [standalone_runtime.rs:12292](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12292), rendering at [standalone_runtime.rs:14028](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:14028) | Partial family support. |
| `suggest` | consumed + validated | validation at [standalone_runtime.rs:12572](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12572), rendering at [standalone_runtime.rs:14169](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:14169) | Partial family support. |
| `pit` | consumed + validated | validation at [standalone_runtime.rs:12302](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12302), PIT resolution at [standalone_runtime.rs:5705](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5705) | Supported bounded PIT path. |
| `search_after` | consumed + validated | validation at [standalone_runtime.rs:12307](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12307), application at [standalone_runtime.rs:13343](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:13343) | Partial family support. |
| `rescore` | consumed + validated | validation at [standalone_runtime.rs:12321](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12321), application at [standalone_runtime.rs:13448](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:13448) | Partial family support. |
| `collapse` | consumed + validated | validation at [standalone_runtime.rs:12331](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12331), application at [standalone_runtime.rs:13497](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:13497) | Partial family support. |
| `runtime_mappings` | consumed + validated | validation at [standalone_runtime.rs:12268](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12268), application at [standalone_runtime.rs:5800](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5800) | Bounded runtime mapping script support only. |
| `stored_fields` | consumed + validated | validation at [standalone_runtime.rs:12273](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12273), field extraction at [standalone_runtime.rs:12133](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12133) | Bounded response-field path. |
| `docvalue_fields` | consumed + validated | validation at [standalone_runtime.rs:12278](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12278), field extraction at [standalone_runtime.rs:12147](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12147) | Bounded response-field path. |
| `explain` | consumed + validated | bool-only validation at [standalone_runtime.rs:12313](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12313), response shaping at [standalone_runtime.rs:5904](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5904) | Bounded explain block in search response. |
| `profile` | consumed + validated | bool-only validation at [standalone_runtime.rs:12313](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12313), bounded shaping at [standalone_runtime.rs:5972](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:5972) | No dedicated profiling subsystem. |
| `_source` filtering | no dedicated handler/evaluator | no `body.get("_source")` path in `validate_search_request_body` or `handle_index_search_route` | Decide fail-closed vs documented-partial; current behavior returns full `_source`. |
| `fields` | no dedicated handler/evaluator | no `body.get("fields")` path in search request validation/handler; response-field support currently goes through `stored_fields` and `docvalue_fields` | Decide fail-closed vs documented-partial. |
| `post_filter` | no dedicated handler/evaluator | no `body.get("post_filter")` path in search request validation/handler | Decide fail-closed vs documented-partial. |
| `timeout` | no dedicated handler/evaluator | no top-level `body.get("timeout")` path in search request validation/handler; only unrelated query-param/runtime timeouts exist elsewhere | Decide fail-closed vs documented-partial. |
| `min_score` | no dedicated top-level handler | no top-level `body.get("min_score")` path in search request validation/handler; k-NN query-level `min_score` exists separately in validation at [standalone_runtime.rs:12747](/home/ubuntu/steelsearch/crates/os-node/src/standalone_runtime.rs:12747) | Need explicit policy for top-level `min_score`. |
| `version` | no dedicated handler/evaluator | no `body.get("version")` path in search request validation/handler | Decide fail-closed vs documented-partial. |
| `seq_no_primary_term` | no dedicated handler/evaluator | no `body.get("seq_no_primary_term")` path in search request validation/handler | Decide fail-closed vs documented-partial. |
| `stats` | no dedicated handler/evaluator | no `body.get("stats")` path in search request validation/handler | Decide fail-closed vs documented-partial. |


## Silent-Ignore Versus Fail-Closed Decision Table

This table records the current policy decision for top-level search fields that
are not yet backed by a dedicated handler/evaluator path.

| Field | Current behavior | Decision | Rationale | Follow-up |
| --- | --- | --- | --- | --- |
| `_source` filtering | full `_source` is returned; no field-level filtering path | documented partial | Source retrieval itself is core behavior and a bounded full-source fallback is still useful, but field filtering must not be claimed as supported. | Add explicit fixture proving full `_source` fallback, then decide whether unsupported filter shapes should reject. |
| `fields` | no dedicated top-level `fields` request handling | fail closed | Current bounded response-field support already uses `stored_fields` / `docvalue_fields`; accepting `fields` silently would over-claim support. | Add negative fixture and explicit `400` path for top-level `fields`. |
| `post_filter` | no post-query filter phase | fail closed | Silently ignoring a post-filter changes hit count and aggregation semantics. | Add negative fixture and explicit `400` path. |
| `timeout` | no top-level search body timeout handling | fail closed | Timeouts are behavioral controls; silent ignore is unsafe for operational expectations. | Add negative fixture and explicit `400` path unless a bounded timeout model is implemented. |
| top-level `min_score` | no top-level min-score gate; query-level k-NN `min_score` only | fail closed | Silently ignoring top-level score filtering changes hit visibility and ordering. | Add negative fixture and explicit `400` path for top-level `min_score`. |
| `version` | no search-hit version projection path | documented partial | Missing version projection does not change search matching semantics, but it must not be claimed as supported. | Document unsupported projection behavior and later decide whether to reject or implement. |
| `seq_no_primary_term` | no search-hit seq_no/primary_term projection path | documented partial | Same rationale as `version`: it is a projection gap, not a query-match semantic gap. | Document unsupported projection behavior and later decide whether to reject or implement. |
| `stats` | no request stats group handling | documented partial | Stats groups are observability metadata; missing support is lower risk than silently changing query results. | Document as unsupported metadata and revisit after core fail-closed audit. |

Decision rule used here:

- if silently ignoring the field can change matching, ranking, filtering,
  pagination, or timeout semantics, prefer `fail closed`;
- if the field is primarily about extra projection or observability metadata,
  `documented partial` is acceptable temporarily as long as the matrix and
  fixtures do not claim support.

## How To Read This Matrix

- `Implemented = partial` is expected for many families right now. It means the
  repository has live behavior and some evidence, but not enough to claim
  blanket OpenSearch replacement parity.
- `Strict compared = yes` is a stronger statement than `Semantic probed = yes`.
- `Fail closed = partial` means some unsupported variants already reject
  correctly, but the audit is not yet complete enough to assert that all
  unsupported variants reject.
- Rows should be promoted only when fixtures, runtime code, and evidence
  artifacts all align.
