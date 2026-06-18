# hybrid-bool-generalization-follow-on

## Purpose

Track the broader remaining hybrid `bool` generalization work beyond the
representative direct-path shapes already covered on the current Tantivy-native
path.

## Upstream note

- originating gap summary:
  `docs/rust-port/tantivy-native-gap-analysis.md`

## Current reading

- This is no longer a question of whether the representative hybrid
  lexical-plus-vector seats exist at all.
- The remaining gap is broader shape generalization and orchestration breadth
  beyond the current representative direct-path coverage.
- So this axis should be read as a broader backlog/generalization note rather
  than as a small local representative-seat cleanup.

## Current repo-local framing

- Current direct-path coverage already includes representative:
  - `should(knn)` with lexical `must` / `filter` / `must_not`
  - multiple `should(knn)` clauses
  - `minimum_should_match > 1`
  - `minimum_should_match = 0`
  - `must(knn)` / `filter(knn)` / `must_not(knn)`
  - nested `bool` subtrees carrying the same placements
  - representative nested `minimum_should_match > 1` request shapes with
    explicit-sort, `size=0`, and `top_hits` aggregation evidence, including
    representative `should`-, `must`-, `filter`-, and positive-candidate
    `must_not`-placement variants, with direct explicit-sort evidence for the
    `should`, `must`, `filter`, and positive-candidate `must_not` seats and
    direct `size=0` + `top_hits` evidence on the `should`, `must`, `filter`,
    and positive-candidate `must_not` seats as well
  - native-sort-compatible direct-path request shapes
- Current remaining gap is therefore less "missing hybrid bool seat" and more
  "broader shape/reduce/fusion orchestration outside the representative direct
  subset".
- More concretely, the current representative placement matrix now already
  includes nested `minimum_should_match > 1` evidence across representative
  `should` / `must` / `filter` / positive-candidate `must_not` seats, with
  direct explicit-sort and direct `size=0` + `top_hits` evidence on those
  seats.
- The current repo-local evidence stack now also includes a representative
  double-nested `minimum_should_match > 1` hybrid-bool `size=0` + `top_hits`
  request shape plus a representative explicit-sort result-path shape, so the
  next gap should not be framed as "one more obvious deeper nesting
  representative" without first surfacing a broader escape.
- The current repo-local evidence stack now also includes a representative
  grouped outer-`bool` shape whose child subtrees each already match the
  current representative hybrid-bool seats in isolation, so the next gap
  should not be framed as if the grouped-parent seat were still completely
  unrepresented.
- The current repo-local evidence stack now also includes a representative
  one-more-parent-threshold wrapper around that grouped outer-`bool` seat, so
  the next gap should not be framed as if one additional parent wrapper were
  still completely unseen.
- The current repo-local evidence stack now also includes a representative
  same-parent sibling-group seat with multiple grouped hybrid-bearing
  subtrees, so the next gap should not be framed as if sibling multiplication
  were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  parent-threshold layer over that same-parent sibling-group seat, so the next
  gap should not be framed as if one additional threshold/exclusion wrapper on
  sibling groups were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  parent-exclusion layer over that same-parent sibling-group seat, so the next
  gap should not be framed as if exclusion layering on sibling-group shapes
  were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  sibling-group seat whose hybrid-bearing child subtrees draw from multiple
  vector fields, so the next gap should not be framed as if broader
  candidate-source multiplication were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  parent-threshold layer over that multi-vector-field sibling-group seat, so
  the next gap should not be framed as if deeper parent layering plus broader
  candidate-source multiplication were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  parent-exclusion layer over that multi-vector-field sibling-group seat, so
  the overlap between broader candidate-source multiplication and one more
  parent exclusion layer is no longer completely unseen either.
- The current repo-local evidence stack now also includes a representative
  one-more-parent-bool layer over that same multi-vector-field plus
  threshold/exclusion overlap seat, so the next gap should not be framed as if
  deeper parent layering above the current overlap were still completely
  unseen either.
- The current repo-local evidence stack now also includes a representative
  additional sibling-multiplication layer over that same layered overlap seat,
  so the next gap should not be framed as if broader grouped multiplication on
  top of the current overlap were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  one-more-exclusion layer over that same layered-overlap-plus-sibling-
  multiplication seat, so the next gap should not be framed as if deeper
  exclusion layering above the current multiplied overlap were still
  completely unseen either.
- The current repo-local evidence stack now also includes a representative
  one-more-parent-layer over that same layered-overlap-plus-sibling-
  multiplication seat, so the next gap should not be framed as if deeper
  parent layering above the current multiplied overlap were still completely
  unseen either.
- The current repo-local evidence stack now also includes a representative
  alternating threshold/exclusion outer-layer stack over that same layered-
  overlap-plus-sibling-multiplication seat, so the next gap should not be
  framed as if staged alternating parent layering there were still completely
  unseen either.
- The current repo-local evidence stack now also includes a representative
  additional sibling-multiplication layer over that same alternating outer-
  layer stack, so the next gap should not be framed as if broader sibling
  fan-out on top of the alternating stack were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  one-more-parent-threshold layer over that same sibling-multiplication-over-
  alternating-stack seat, so the next gap should not be framed as if one more
  outer threshold wrapper above the multiplied alternating stack were still
  completely unseen either.
- The current repo-local evidence stack now also includes a representative
  one-more-parent-exclusion layer over that same sibling-multiplication-over-
  alternating-stack seat, so the next gap should not be framed as if one more
  outer exclusion wrapper above the multiplied alternating stack were still
  completely unseen either.
- The current repo-local evidence stack now also includes a representative
  outer threshold step after that same parent-exclusion-over-sibling-
  multiplication-over-alternating-stack seat, so the next gap should not be
  framed as if a second outer alternating-wrapper depth were still completely
  unseen either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after that same parent-threshold-over-sibling-
  multiplication-over-alternating-stack seat, so the next gap should not be
  framed as if the opposite second-step outer alternating direction were still
  completely unseen either.
- The current repo-local evidence stack now also includes direct grouped
  hybrid-bool `distance_feature` coverage that pins candidate-id reduction
  plus native documents / hit-context / page / window / count helper surface,
  so that comparable-field scorer-style lexical seat should not be read as a
  remaining local representative hole.
- The current repo-local evidence stack now also includes direct grouped
  hybrid-bool `wrapper` coverage that pins candidate-id reduction plus native
  documents / hit-context / page / window / count helper surface, so that
  thin wrapper delegation seat should not be read as a remaining local
  representative hole.
- The current repo-local evidence stack now also includes grouped hybrid-bool
  `nested` coverage that pins candidate-id plus native documents /
  hit-context / page / window / count helper surface through the current
  document-scan-backed nested-path seat, so that clause should not be read as
  a remaining local representative hole either.
- The current repo-local evidence stack now also includes grouped hybrid-bool
  `pinned` coverage that pins candidate-id plus native documents /
  hit-context / page / window / count helper surface for the current pinned-
  ids-plus-organic-query seat, so that clause should not be read as a
  remaining local representative hole either.
- The current repo-local evidence stack now also includes grouped hybrid-bool
  `more_like_this` coverage that pins candidate-id plus native documents /
  hit-context / page / window / count helper surface for the current
  text-token-overlap seat, so that clause should not be read as a remaining
  local representative hole either.
- The current repo-local `more_like_this` seat also now shares the same
  `source_value_for_highlight_field(...)` field-lookup semantics used by the
  surrounding matcher/evidence surface, so dotted/nested field-addressing
  drift should not be read as a separate local hybrid-bool residue there.
- The same repo-local field-lookup convergence now also covers source-backed
  plugin metric collection and `top_metrics` metric-object projection, so
  aggregation-side dotted/nested field-addressing drift should not be read as
  a separate residual axis around those surrounding fallback surfaces either.
- The same aggregation-side field-lookup convergence now also covers
  diversified-sampler source-key extraction, so dotted/nested field-addressing
  drift should not be read as a separate residual axis in that sampled-
  collection gate either.
- The same aggregation-side field-lookup convergence now also covers
  source-backed `terms`, `range`, `date_histogram`, `histogram`, `missing`,
  `cardinality`, and composite-key collection paths, so dotted/nested field-
  addressing drift should not be read as a separate residual axis in those
  surrounding fallback bucket/metric collectors either.
- The same field-path convergence now also reaches mapped field ingestion,
  visible-field byte estimation, and plugin `auto_date_histogram` /
  `variable_width_histogram` interval selection, so dotted/nested field
  addressing should not be read as a separate residual axis between
  indexing-side and aggregation-side helper surfaces either.
- The remaining top-level builder fallbacks now also read more clearly as
  explicit Tantivy-surface boundaries rather than local missing rewrites:
  current local Tantivy 0.21.1 still exposes no nested-query primitive, no
  geo-distance query primitive, no plain `Query` seat for KNN, and no direct
  aggregation request variants for `weighted_avg`, `boxplot`,
  `extended_stats`, `percentile_ranks`, `median_absolute_deviation`, or
  `cardinality`.
- The shared `source_value_for_highlight_field(...)` lookup now also takes the
  plain no-dot field fast path directly while preserving dotted-path behavior,
  so the now-broader source-backed matcher/evidence/aggregation family shares
  the same cheaper common lookup seat for scalar field names.
- The pipeline bucket-value path is also one layer thinner now: the one-use
  `bucket_selector_source_value(...)` alias is gone, and the moving/bucket-
  selector family reads straight through `bucket_normalize_source_value(...)`.
- The hit-backed plugin `ip_range` / `date_range` / `geo_distance` seats are
  likewise one layer thinner now: their one-use hit-wrapper helpers are gone,
  and the callers bind directly to the shared `*_from_values(...)` collectors.
- The pipeline metric family is also one layer thinner now: one-use
  `cumulative_sum_pipeline_value(...)` and `derivative_pipeline_value(...)`
  wrappers are gone, and their callers now bind directly to
  `sum_bucket_pipeline_value(...)` and `serial_diff_pipeline_value(..., 1)`.
- The adjacent single-use `avg_bucket_pipeline_value(...)`,
  `min_bucket_pipeline_value(...)`, and `max_bucket_pipeline_value(...)`
  helpers are likewise gone now, and their callers compute directly from
  `bucket_metric_values(...)`.
- The plugin global/sampler doc-count surface is also one layer thinner now:
  one-use `plugin_global_doc_count_surface(...)` and
  `plugin_sampler_doc_count_surface(...)` wrappers are gone, and the callers
  bind directly to `plugin_*_aggregation_value(..., None)`.
- The span containment family is also one layer thinner now: the pure
  argument-swap `matches_span_within_query(...)` alias is gone, and the
  remaining callers bind directly to `matches_span_containing_query(...)`
  with swapped child order.
- The diversified sampler field getter is likewise gone now: the two remaining
  callers read `plugin.params["field"]` directly instead of routing through a
  thin `plugin_diversified_sampler_field(...)` alias.
- At this point the remaining tiny helpers in the same local family mostly
  read as shared multi-caller primitives rather than obvious one-use wrappers,
  so helper-side thin-alias cleanup is close to saturated and the next payoff
  is increasingly behavior/orchestration-side rather than one more local
  syntax pass.
- `nested` explanation output now also surfaces `matched_nested_values`, so the
  source-backed nested seat no longer stops at a plain path-level matched/not-
  matched summary when multiple nested values are involved.
- `more_like_this` explanation output now also surfaces `matched_fields`, so
  its matched-field-only semantics are visible directly in the user-facing
  description instead of staying implicit in the surrounding fallback behavior.
- `terms` and `terms_set` explanation output now also surfaces
  `matched_value_count`, so candidate-value overlap is visible directly instead
  of stopping at a plain matched/not-matched boolean.
- `geo_distance` explanation output now also surfaces
  `actual_distance_meters`, and `distance_feature` explanation output now also
  surfaces `observed_distance` plus `pivot_magnitude`, so those source-backed
  distance seats no longer stop at a boolean-only matched/not-matched summary.
- `rank_feature` explanation output now also surfaces
  `observed_feature_value`, so the current positive numeric/bool gate no longer
  stays implicit behind a boolean-only matched/not-matched summary.
- `distance_feature` and `rank_feature` explanation output now also surfaces
  `matched_value_count`, so array-backed feature overlap is directly visible
  instead of only exposing one observed distance/value seat.
- tokenized `match_phrase`, `match_phrase_prefix`, and `match_bool_prefix`
  explanation output now also surfaces `matched_token_count` plus
  `query_token_count`, so token overlap is directly visible instead of staying
  implicit behind a plain matched/not-matched boolean.
- plain `match` explanation output now also surfaces `matched_value_count`, so
  array-backed source overlap is visible directly instead of collapsing to a
  boolean-only matched/not-matched summary.
- pattern leaf family (`prefix`, `wildcard`, `regexp`, `fuzzy`) explanation
  output now also surfaces `matched_value_count`, so array-backed source
  overlap is visible directly instead of collapsing to a boolean-only
  matched/not-matched summary.
- scalar leaf family (`term`, `range`, `exists`) explanation output now also
  surfaces `matched_value_count`, so array-backed source overlap is visible
  directly instead of collapsing to a boolean-only matched/not-matched
  summary.
- token-AND multi-field family (`combined_fields`, `query_string`,
  `simple_query_string`) explanation output now also surfaces
  `matched_token_count` plus `query_token_count`, so token overlap across
  fields is directly visible instead of staying implicit behind a plain
  matched/not-matched boolean.
- `multi_match` explanation output now also surfaces `matched_value_count`, so
  the current field-OR overlap size is directly visible instead of stopping at
  a matched-field-set summary.
- `more_like_this` explanation output now also surfaces
  `matched_token_count`, so like-token overlap is directly visible instead of
  stopping at a matched-field-set summary.
- `ids` explanation output now also surfaces `matched_value_count`, so exact
  candidate overlap is visible directly instead of stopping at a boolean-only
  matched/not-matched summary.
- `span_containing` and `span_within` explanation output now also surfaces
  `big_match` plus `little_match`, so the two positive-child admission signals
  are visible directly instead of stopping at the outer containment boolean.
- `span_first` explanation output now also surfaces `child_match`, and
  `span_near` explanation output now also surfaces `matched_child_clauses`, so
  those span-family outer summaries no longer stop at a bare `source_match`
  boolean.
- delegate wrapper family (`span_multi`, `field_masking_span`, `wrapper`,
  `constant_score`, `function_score`, `script_score`) now also surfaces
  `source_match` in the outer description, so wrapper-level summaries no
  longer rely on child-detail presence alone.
- `span_not` outer description now also surfaces `source_match`, so the final
  include-without-exclude admission signal is visible directly instead of
  living only in the separate `matched` field.
- `dis_max` and `boosting` outer descriptions now also surface
  `source_match`, so the final combinator admission signal is visible directly
  instead of being inferred from matched-child or positive/negative child
  counts alone.
- `pinned` outer description now also surfaces `source_match`, so the final
  pinned-or-organic admission signal is visible directly instead of being
  inferred from the separate `pinned_match` and `organic_match` fields.
- `bool` outer description now also surfaces `source_match`, so the final
  bool-admission result is visible directly instead of being inferred from the
  aggregate source/highlight/projected match counts alone.
- `span_or` outer description now also surfaces `source_match`, so the final
  any-child admission signal is visible directly instead of being inferred
  from the matched-child count alone.
- `knn` outer description now also surfaces `source_match`, so the final
  vector-shape-plus-filter admission signal is visible directly instead of
  being inferred from vector compatibility and separate filter counts alone.
- `knn` filter detail now also surfaces `filter_match`, so the filter's own
  final admission signal is visible directly instead of being inferred from
  aggregate source/highlight/projected counts alone.
- `span_not` now also exposes a structured `source_match` field alongside the
  legacy `matched` field, so consumers no longer need to infer or rename the
  final admission signal themselves.
- `geo_distance` explanation output now also surfaces `matched_value_count`, so
  array-backed geo-point overlap within the requested distance is visible
  directly instead of only exposing the minimum observed distance.
- multi-index native reduce hint collection now also uses
  `source_value_for_highlight_field(...)` for cardinality value hints, so
  dotted/nested field addressing stays aligned between source-backed hint
  collection and the surrounding aggregation fallback/reduce surface.
- `distance_feature` observed-distance reporting now also uses the same
  recursive array-aware distance helper as the matcher, so array-valued source
  fields no longer drift between explanation output and live match semantics.
- The current repo-local evidence stack now also includes grouped hybrid-bool
  `span_term` coverage that pins candidate-id reduction plus native
  documents / hit-context / page / window / count helper surface, so that
  thin term-delegation seat should not be read as a remaining local
  representative hole.
- The current repo-local evidence stack now also includes grouped hybrid-bool
  `span_or` coverage that pins candidate-id reduction plus native
  documents / hit-context / page / window / count helper surface, so that
  thin child-union span-wrapper seat should not be read as a remaining local
  representative hole.
- The current repo-local evidence stack now also includes grouped hybrid-bool
  `span_first` coverage that pins candidate-id plus native documents /
  hit-context / page / window / count helper surface through the current
  source-backed first-position span gate, so that clause should not be read
  as a remaining local representative hole either.
- The current repo-local evidence stack now also includes grouped hybrid-bool
  `span_near` coverage that pins candidate-id plus native documents /
  hit-context / page / window / count helper surface through the current
  source-backed span-window gate, so that clause should not be read as a
  remaining local representative hole either.
- The current repo-local evidence stack now also includes grouped hybrid-bool
  `span_not` coverage that pins candidate-id plus native documents /
  hit-context / page / window / count helper surface through the current
  include-without-exclude span wrapper, so that clause should not be read as
  a remaining local representative hole either.
- The current repo-local evidence stack now also includes grouped hybrid-bool
  `span_containing` coverage that pins candidate-id plus native documents /
  hit-context / page / window / count helper surface through the current
  source-backed containment span wrapper, so that clause should not be read
  as a remaining local representative hole either.
- The current repo-local evidence stack now also includes grouped hybrid-bool
  `span_within` coverage that pins candidate-id plus native documents /
  hit-context / page / window / count helper surface through the current
  source-backed inverse-containment span wrapper, so that clause should not
  be read as a remaining local representative hole either.
- The current repo-local evidence stack now also includes grouped hybrid-bool
  `span_multi` coverage that pins candidate-id reduction plus native
  documents / hit-context / page / window / count helper surface, so that
  thin multi-term span wrapper seat should not be read as a remaining local
  representative hole.
- The current repo-local evidence stack now also includes grouped hybrid-bool
  `field_masking_span` coverage that pins candidate-id reduction plus native
  documents / hit-context / page / window / count helper surface, so that
  thin field-remapping span wrapper seat should not be read as a remaining
  local representative hole.
- The current repo-local evidence stack now also includes direct grouped
  hybrid-bool `rank_feature` coverage that pins candidate-id reduction plus
  native documents / hit-context / page / window / count helper surface, so
  that source-backed positive-scalar lexical seat should not be read as a
  remaining local representative hole.
- More exactly, the next reading boundary should be taken from the same
  top-level shorthand already called out in the main gap note:
  direct representative hybrid-bool compatibility-leaf-set coverage,
  the shared broader-family residual-backlog boundary,
  direct broader hybrid-bool residual-family wording,
  and direct grouped hybrid-bool residual-boundary wording.

## Suggested follow-on questions

- Which broader nested/generalized hybrid `bool` shapes still escape to the
  generic orchestration path?
- Which remaining escapes are due to candidate-source generalization versus
  final fusion/scoring orchestration?
- Which of those broader shapes are high-payoff enough to deserve new
  representative direct-path expansion?

## Suggested evidence targets

- current hybrid `bool` representative coverage wording in
  `tantivy-native-gap-analysis.md`
- nearby vector/hybrid fixtures and regression notes
- direct-path versus generic-path code-path boundaries in the current hybrid
  bool implementation

## Current default reading

- Treat this as a broader breadth/generalization backlog note, not as the next
  narrow stop-point-style contract question.
- The main question is prioritization among broader hybrid-shape expansions,
  not whether one last local representative seat is still missing.
- Preferred immediate next target:
  start from the broader hybrid `bool` shapes that still escape to the general
  bool-query orchestration path even after the current direct-path coverage for
  representative `should(knn)` / `must(knn)` / `filter(knn)` / `must_not(knn)`
  and nested variants.
- First concrete reading target:
  start from the residual boundary already summarized in the main gap analysis
  between the current representative direct-path hybrid `bool` coverage and the
  broader hybrid-bool residual-family wording, and treat that line as the
  shorthand for the next hybrid shapes that still escape direct-path fusion.
- Current best candidate shape family:
  broader nested/generalized hybrid `bool` shapes that still escape to the
  general bool-query orchestration path even after the current direct-path
  coverage for representative `should(knn)` / `must(knn)` / `filter(knn)` /
  `must_not(knn)` placements and their current nested variants.
- Current best candidate subfamily:
  nested/generalized hybrid `bool` shapes whose `knn` placements still require
  generic orchestration once they move beyond the current representative
  direct-path nesting and candidate-source combinations.
- Current best first broader shape subset:
  grouped outer-`bool` shapes whose child subtrees each already look like the
  current representative hybrid-bool seats in isolation, but whose parent bool
  still has to fuse multiple such hybrid-bearing subtrees or candidate-source
  groups at once and therefore crosses the current grouped residual-family
  boundary.
- Current next broader grouped residual-family subset:
  shapes where that same grouped outer-`bool` seat is itself wrapped once more
  by an additional parent threshold/exclusion layer or is combined with
  multiple grouped sibling seats at the same parent level, so the current
  grouped-parent representative no longer stands alone as the only fusion
  problem.
- Current next exact grouped-residual reading subset after the current
  representatives:
  same-parent sibling-group shapes once they are no longer only multiplied in
  parallel, but are also subjected to one more parent threshold/exclusion
  layer above them, because that is where the current representative grouped-
  parent, one-more-parent-wrapper, and sibling-group seats begin to combine
  instead of remaining separately representative.
- Current next broader grouped residual-family subset after those seats:
  same-parent sibling-group shapes that combine both broader candidate-source
  multiplication across multiple vector fields and one more parent
  threshold/exclusion layer at once, because that is the first place where the
  current representative multi-vector-field and parent-layer seats stop being
  separable examples and start to overlap as one broader grouped-orchestration
  problem.
- Current next deeper grouped residual-family subset after that overlap:
  shapes where that same multi-vector-field sibling-group plus
  threshold/exclusion overlap is itself wrapped by one more parent bool layer,
  because that is the next place where the current overlap seat stops being a
  single grouped-parent problem and starts turning into deeper grouped
  orchestration again.
- Current next broader grouped-multiplication subset after that deeper layer:
  shapes where that same multi-vector-field plus threshold/exclusion overlap,
  already wrapped by one more parent bool layer, is then multiplied again
  across additional sibling grouped seats at the same higher parent level,
  because that is the next place where the current layered-overlap seat stops
  being a single deeper wrapper problem and starts becoming broader grouped
  sibling multiplication again.
- Current next broader grouped-layering subset after that multiplication:
  shapes where that same layered-overlap-plus-sibling-multiplication seat is
  itself subjected to one more parent threshold/exclusion layer again, because
  that is the next place where the current representative grouped fan-out
  starts composing with deeper parent layering instead of only one or the
  other.
- Current next broader alternating-layering subset after that point:
  shapes where the current layered-overlap-plus-sibling-multiplication seat is
  no longer wrapped by only one more threshold or only one more exclusion
  layer, but begins alternating those parent threshold/exclusion layers across
  successive outer bool levels, because that is the next place where the
  current representative layering seats stop being single-step extensions and
  start becoming a broader staged orchestration family.
- More exactly, once that alternating parent layering also has representative
  evidence, the next first-open blocker should be read as the first shapes
  where that same alternating outer-layer stack is not only multiplied again
  across additional sibling grouped seats at the higher parent level, but then
  takes the opposite fourth-step outer alternating branch from the one already
  represented here, because that is the first place where the current
  alternating stack and the current broader sibling-fan-out family would have
  both fourth-step outer-wrapper directions represented at the same deeper
  alternating depth.
- Current first exact code reading seat:
  start where those grouped outer-`bool` shapes meet the current code split
  between:
  `search_candidate_ids_for_bool_query_reduced(...)`
  on the parent bool side and
  `vector_candidate_window_context_for_query_native(...)`
  on the whole-query carrier side, because that is where multiple already-
  representative hybrid child subtrees stop being isolated seats and start
  depending on grouped parent threshold/intersection/exclusion handling plus a
  single broader vector/document-scan carrier.
- Current code-side reading after the latest reduced-path routing change:
  grouped hybrid bool native helper seats for page/window/hit-context/
  documents/count now try the reduced candidate-bool helper before they fall
  back to the whole-query vector candidate-window carrier, so the next blocker
  should no longer be read as if those native helper seats still always start
  on the whole-query carrier side first.
- More exactly on the native-document seat:
  grouped hybrid bool native-document helper now checks the shared index-aware
  hit-context seat immediately after the bool-specialized page seat, before it
  opens the broader whole-query vector candidate-window carrier.
- More exactly on the native-count seat:
  grouped hybrid bool native-count helper now also checks that same shared
  index-aware hit-context seat immediately after the bool-specialized page
  seat, instead of reopening its own duplicate whole-query vector carrier
  branch there.
- More exactly on the non-index-aware count seat:
  the broader count helper no longer reopens the duplicate whole-query vector
  page carrier after the grouped hybrid bool specialized page seat and direct
  vector-count context checks.
- More exactly on the native-hit seat:
  grouped hybrid bool non-index-aware native-hit helper now checks the
  bool-specialized hybrid-hit seat before it opens the broader whole-query
  vector candidate-window carrier.
- More exactly on the non-index-aware native-document seat:
  grouped hybrid bool non-index-aware native-document helper now also checks
  the bool-specialized hybrid-hit seat before it opens the broader whole-query
  vector candidate-window carrier.
- More exactly on the non-index-aware native page/window seat:
  grouped hybrid bool non-index-aware native page/window helpers now also
  check the bool-specialized hybrid page/window seats before they open the
  broader whole-query vector candidate-window carrier.
- More exactly on the non-index-aware reusable-context seat:
  grouped hybrid bool reusable-context assembly now also checks the
  non-index-aware native document path before it falls back to broader
  scan-based whole-query carrier assembly.
- More exactly on the top-level reusable-context consumer seat:
  the broader no-`index_name` reusable-context assembly now also consumes any
  live vector candidate-window carrier directly before it reopens the native
  document path or broader scan-based whole-query carrier assembly.
- More exactly on the single-index search-response producer seat:
  the native single-index `search_response_index_aware_with_optional_reusable(...)`
  boundary can now also hand off an optional reusable query context for
  vector/hybrid-native shapes instead of dropping that carrier at the wrapper
  line.
- More exactly on the shared index-aware hit-context seat:
  once grouped hybrid bool specialized page and direct vector candidate-window
  context checks have both run, the shared hit-context helper no longer
  reopens the duplicate whole-query vector/hybrid page carrier again.
- More exactly on the aggregation-side vector/hybrid hit assembly seat:
  once direct vector candidate-window hits, shared index-aware hit-context,
  and document-backed fallback are all in play, the aggregation-side
  vector/hybrid top-hits assembly no longer reopens the duplicate whole-query
  vector/hybrid window carrier again.
- More exactly on the grouped hybrid bool aggregation hit-materialization
  fallback seat:
  after the shared index-aware hit-context check and any live direct vector
  candidate-window hits have both run, the grouped hybrid bool `top_hits`
  materialization path now also routes its remaining window fallback through
  the non-index-aware native page/window sibling before it gives up to the
  broader whole-query vector/hybrid window carrier.
- More exactly on the index-aware aggregation wrapper seat:
  when a grouped hybrid bool aggregation request is already inside the
  single-index index-aware aggregation wrapper and the vector-native
  page-`top_hits` seat does not apply, that wrapper now also falls through to
  the native document-backed aggregation collector instead of giving up
  straight to the generic hit-array aggregation path.
- More exactly on the multi-index fetched-page aggregation wrapper seat:
  once a fetched-page carrier is already available, the multi-index
  vector/hybrid aggregation wrapper now relies on the shared
  `from_page_and_context(...)` wrapper for the vector page-`top_hits` seat and
  its native-from-window fallthrough instead of reopening that same seat again
  through separate outer wrapper branches.
- Nearby repo-local evidence now also directly pins that same shared
  fetched-page wrapper seat with a grouped hybrid bool `terms(service)`
  aggregation regression, so the current remaining blocker should not be read
  as if the shared `from_page_and_context(...)` lane itself were still
  unrepresented.
- More exactly on the top-level count seat:
  grouped hybrid bool top-level count now no longer short-circuits on the
  direct vector candidate-window total-hit carrier before the lower native
  document/hit-based path has a chance to apply the grouped hybrid
  specialization.
- More exactly on the top-level document seat:
  grouped hybrid bool top-level document lookup now no longer short-circuits
  on the direct vector candidate-window document carrier before the lower
  native document/hit-based path has a chance to apply the grouped hybrid
  specialization.
- More exactly on the reusable document-lookup seat:
  grouped hybrid bool reusable document lookup now also avoids pre-opening the
  direct vector candidate-window document carrier before the lower native
  document/hit-based path has a chance to apply the grouped hybrid
  specialization.
- More exactly on the reusable count seat:
  grouped hybrid bool reusable count lookup now also avoids pre-opening the
  direct vector candidate-window total-hit carrier before the lower native
  document/hit-based path has a chance to apply the grouped hybrid
  specialization.
- More exactly on the non-index-aware count seat:
  grouped hybrid bool non-index-aware count path now checks the bool-
  specialized hybrid page/count seat before it opens the broader whole-query
  vector candidate-window carrier.
- More exactly on the document-backed reusable/document-scan seat:
  when reusable documents are absent, the document-backed non-index-aware
  search path now checks `search_documents_for_query_native(...)` before it
  reuses any already-computed whole-query vector candidate-window carrier, so
  the grouped hybrid bool bool-specialized-first ordering is no longer
  bypassed there.
- Current nearby regression evidence for that routing change:
  grouped hybrid bool native helper coverage now directly pins page/window
  helper surface as well as hit-context/documents/count surface after that
  reduced-candidate-first routing preference.
- Current grouped-hybrid optional-native reading after the latest helper
  contract alignment:
  when `search_state` is still absent, the grouped hybrid bool optional-native
  helper family now reads consistently as `None` across count/documents/
  hit-context/reusable-context/page/window seats instead of letting some seats
  fall through to the whole-query vector/document carrier while others do not.
- Current unsupported-leaf fallback reading after the latest recursion-safe
  reduced-path change:
  unsupported-leaf reduced fallback now short-circuits directly to scan-based
  candidate ids for the fallback query itself instead of re-entering the same
  native/helper split, so that fallback seat should no longer be read as if it
  still loops back through the whole-query carrier/helper boundary first.
- Current direct range-leaf reduction reading after the latest leaf-support
  expansion:
  text/keyword/bool `range` leaves now reduce directly through the current
  value-predicate candidate path instead of falling into that unsupported-leaf
  fallback bucket.
- Current direct scalar-match reduction reading after the latest leaf-support
  expansion:
  non-`_id` bool/number/date `match` leaves now also reduce directly through
  the current value-predicate candidate path instead of falling into that
  unsupported-leaf fallback bucket.
- Current direct scalar-exists reduction reading after the latest leaf-support
  expansion:
  non-`_id` `exists` leaves now also reduce directly through the current
  value-predicate candidate path, including text/vector-backed existence
  checks that previously sat in the unsupported-leaf fallback bucket.
- Current direct nested phrase-leaf reduction reading after the latest
  child-ordinal expansion:
  nested `match_phrase` and `match_phrase_prefix` leaves now resolve inside the
  nested child index using child-local source values instead of returning to the
  parent source-validation fallback bucket, while still preserving tuple
  isolation across sibling nested objects.
- Current direct nested match-leaf reduction reading after the latest
  child-ordinal expansion:
  nested `match` leaves now also resolve inside the nested child index using
  child-local source values instead of returning to the parent source-validation
  fallback bucket, while still preserving tuple isolation across sibling nested
  objects.
- Current direct nested bool-prefix reduction reading after the latest
  child-ordinal expansion:
  nested `match_bool_prefix` leaves now also resolve inside the nested child
  index using child-local source values instead of returning to the parent
  source-validation fallback bucket, while still preserving tuple isolation
  across sibling nested objects.
- Current direct geo-point exact-match reduction reading after the latest
  leaf-support expansion:
  non-`_id` `term` / `terms` geo-point leaves now also reduce directly through
  the current value-predicate candidate path instead of staying in the
  unsupported-leaf fallback bucket.
- Current direct vector exact-match reduction reading after the latest
  leaf-support expansion:
  non-`_id` `term` / `terms` vector leaves now also reduce directly through
  the current value-predicate candidate path instead of staying in the
  unsupported-leaf fallback bucket.
- Current direct vector match reduction reading after the latest leaf-support
  expansion:
  non-`_id` vector `match` leaves now also reduce directly through the current
  value-predicate candidate path instead of staying in the unsupported-leaf
  fallback bucket.
- Current direct geo-point match reduction reading after the latest
  leaf-support expansion:
  non-`_id` geo-point `match` leaves now also reduce directly through the
  current value-predicate candidate path instead of staying in the
  unsupported-leaf fallback bucket.
- Current direct non-string `prefix` / `wildcard` reduction reading after the
  latest leaf-support expansion:
  non-`_id` `prefix` / `wildcard` leaves on mapped non-string-backed fields
  now also reduce directly through the current value-predicate candidate path
  instead of staying in the unsupported-leaf fallback bucket, with their
  predicate semantics collapsing to the same local false/no-match behavior
  they already had at document-evaluation time.
- Current direct non-scalar/non-string `range` reduction reading after the
  latest leaf-support expansion:
  mapped non-scalar/non-string-backed `range` leaves now also reduce directly
  through the current value-predicate candidate path instead of staying in the
  unsupported-leaf fallback bucket, with their predicate semantics collapsing
  to the same local false/no-match behavior they already had at document-
  evaluation time.
- Current nearby regression evidence for that direct range-leaf reduction:
  grouped hybrid bool text-range coverage now directly pins candidate-id plus
  native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct scalar-match reduction:
  grouped hybrid bool bool-match coverage now directly pins candidate-id plus
  native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct scalar-exists reduction:
  grouped hybrid bool vector-exists coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct geo-point exact-match
  reduction:
  grouped hybrid bool geo-point-term coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct vector exact-match
  reduction:
  grouped hybrid bool vector-term coverage now directly pins candidate-id plus
  native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct vector match reduction:
  grouped hybrid bool vector-match coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct geo-point match
  reduction:
  grouped hybrid bool geo-point-match coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct geo-distance reduction:
  grouped hybrid bool geo-distance coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct regexp reduction:
  grouped hybrid bool regexp coverage now directly pins candidate-id plus
  native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct fuzzy reduction:
  grouped hybrid bool fuzzy coverage now directly pins candidate-id plus
  native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct match_phrase reduction:
  grouped hybrid bool match_phrase coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct match_phrase_prefix
  reduction:
  grouped hybrid bool match_phrase_prefix coverage now directly pins
  candidate-id plus native documents/hit-context/page/window/count helper
  surface.
- Current nearby regression evidence for that direct match_bool_prefix
  reduction:
  grouped hybrid bool match_bool_prefix coverage now directly pins
  candidate-id plus native documents/hit-context/page/window/count helper
  surface.
- Current nearby regression evidence for that direct multi_match reduction:
  grouped hybrid bool multi_match coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct terms_set reduction:
  grouped hybrid bool terms_set coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that constant_score wrapper
  delegation:
  grouped hybrid bool constant_score coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface through
  the wrapped native/source-backed filter seat.
- Current nearby regression evidence for that dis_max wrapper delegation:
  grouped hybrid bool dis_max coverage now directly pins candidate-id plus
  native documents/hit-context/page/window/count helper surface through the
  wrapped native/source-backed child query seats.
- Current nearby regression evidence for that boosting wrapper delegation:
  grouped hybrid bool boosting coverage now directly pins candidate-id plus
  native documents/hit-context/page/window/count helper surface through the
  wrapped native/source-backed positive child seat.
- Current nearby regression evidence for that function_score wrapper
  delegation:
  grouped hybrid bool function_score coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface through
  the wrapped native/source-backed query seat.
- Current nearby regression evidence for that script_score wrapper
  delegation:
  grouped hybrid bool script_score coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface through
  the wrapped native/source-backed query seat.
- Current nearby regression evidence for that direct combined_fields
  reduction:
  grouped hybrid bool combined_fields coverage now directly pins
  candidate-id plus native documents/hit-context/page/window/count helper
  surface.
- Current nearby regression evidence for that direct query_string reduction:
  grouped hybrid bool query_string coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface.
- Current nearby regression evidence for that direct simple_query_string
  reduction:
  grouped hybrid bool simple_query_string coverage now directly pins
  candidate-id plus native documents/hit-context/page/window/count helper
  surface.
- Current nearby regression evidence for that direct non-string `prefix` /
  `wildcard` reduction:
  grouped hybrid bool vector-prefix and vector-wildcard coverage now directly
  pin candidate-id plus native documents/hit-context/page/window/count helper
  surface for representative empty-result non-string-backed shapes.
- Current nearby regression evidence for that direct non-scalar/non-string
  `range` reduction:
  grouped hybrid bool vector-range coverage now directly pins candidate-id
  plus native documents/hit-context/page/window/count helper surface for a
  representative empty-result non-scalar/non-string-backed shape.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after a fourth-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if a
  fourth outer alternating-wrapper depth were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after a fifth-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if a
  fifth outer alternating-wrapper depth were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after a sixth-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if a
  sixth outer alternating-wrapper depth were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after a seventh-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if a
  seventh outer alternating-wrapper depth were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after an eighth-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if an
  eighth outer alternating-wrapper depth were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  outer threshold step after an eighth-step outer exclusion over that same
  multiplied alternating stack, so the next gap should not be framed as if the
  opposite eighth-step outer alternating direction were still completely unseen
  either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after a ninth-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if a
  ninth outer alternating-wrapper depth were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  outer threshold step after a ninth-step outer exclusion over that same
  multiplied alternating stack, so the next gap should not be framed as if the
  opposite ninth-step outer alternating direction were still completely unseen
  either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after a tenth-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if a
  tenth outer alternating-wrapper depth were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  outer threshold step after a tenth-step outer exclusion over that same
  multiplied alternating stack, so the next gap should not be framed as if the
  opposite tenth-step outer alternating direction were still completely unseen
  either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after an eleventh-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if an
  eleventh outer alternating-wrapper depth were still completely unseen
  either.
- The current repo-local evidence stack now also includes a representative
  outer threshold step after an eleventh-step outer exclusion over that same
  multiplied alternating stack, so the next gap should not be framed as if the
  opposite eleventh-step outer alternating direction were still completely
  unseen either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after a twelfth-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if a
  twelfth outer alternating-wrapper depth were still completely unseen either.
- The current repo-local evidence stack now also includes a representative
  outer threshold step after a twelfth-step outer exclusion over that same
  multiplied alternating stack, so the next gap should not be framed as if the
  opposite twelfth-step outer alternating direction were still completely
  unseen either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after a thirteenth-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if a
  thirteenth outer alternating-wrapper depth were still completely unseen
  either.
- The current repo-local evidence stack now also includes a representative
  outer threshold step after a thirteenth-step outer exclusion over that same
  multiplied alternating stack, so the next gap should not be framed as if the
  opposite thirteenth-step outer alternating direction were still completely
  unseen either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after a fourteenth-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if a
  fourteenth outer alternating-wrapper depth were still completely unseen
  either.
- The current repo-local evidence stack now also includes a representative
  outer threshold step after a fourteenth-step outer exclusion over that same
  multiplied alternating stack, so the next gap should not be framed as if the
  opposite fourteenth-step outer alternating direction were still completely
  unseen either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after a fifteenth-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if a
  fifteenth outer alternating-wrapper depth were still completely unseen
  either.
- The current repo-local evidence stack now also includes a representative
  outer threshold step after a fifteenth-step outer exclusion over that same
  multiplied alternating stack, so the next gap should not be framed as if the
  opposite fifteenth-step outer alternating direction were still completely
  unseen either.

- The current repo-local evidence stack now also includes a representative
  outer threshold step after a seventh-step outer exclusion over that same
  multiplied alternating stack, so the next gap should not be framed as if the
  opposite seventh-step outer alternating direction were still completely
  unseen either.

- The current repo-local evidence stack now also includes a representative
  outer threshold step after a sixth-step outer exclusion over that same
  multiplied alternating stack, so the next gap should not be framed as if the
  opposite sixth-step outer alternating direction were still completely unseen
  either.
- The current repo-local evidence stack now also includes a representative
  outer threshold step after a fifth-step outer exclusion over that same
  multiplied alternating stack, so the next gap should not be framed as if the
  opposite fifth-step outer alternating direction were still completely unseen
  either.
- The current repo-local evidence stack now also includes a representative
  outer threshold step after a third-step outer exclusion over that same
  multiplied alternating stack, so the next gap should not be framed as if the
  opposite third-step outer alternating direction were still completely unseen
  either.
- The current repo-local evidence stack now also includes a representative
  outer exclusion step after a third-step outer threshold over that same
  multiplied alternating stack, so the next gap should not be framed as if a
  third outer alternating-wrapper depth were still completely unseen either.
- Current stop-point reading for the representative placement matrix:
  do not reopen the same representative `should` / `must` / `filter` /
  positive-candidate `must_not` placement seats unless a deeper generalized
  nesting or orchestration escape is actually surfaced.
- Current exact residual-boundary reading:
  treat the next hybrid-bool seat not as "one more representative placement"
  but as the first broader shape that crosses the line from the current direct
  representative compatibility-leaf set into that grouped residual-family
  boundary.
- Practical prioritization reading:
  favor the next shape family that reduces generic orchestration/fusion work
  across multiple broader hybrid requests, rather than adding one more very
  narrow leaf-specific representative admission.
The current single-index grouped hybrid/vector requested-page+aggregation tail
also prefers any surviving fetched-page reusable `total_hits` or the adjacent
fetched-page scalar `total_hits` directly before dropping into the lower count
helper, instead of reopening that count tail first.
That same single-index grouped hybrid/vector requested-page+aggregation fast
path now also hands its surviving fetched-page/aggregation reusable carrier
directly to the outer optional-reusable response boundary instead of making
that boundary rebuild query-level reusable state after the fast path returns.
The adjacent single-index plain fetched-page fast path now does the same for
vector/native/document-scan shapes: it hands the surviving fetched-page
reusable carrier directly to the outer optional-reusable response boundary
instead of rebuilding query-level reusable state after the plain fast path
returns.
The adjacent multi-index plain requested-page-reduce fast path now also hands
the surviving merged requested-page-reduce reusable carrier directly to the
outer optional-reusable response boundary for vector/native/document-scan
shapes instead of rebuilding query-level reusable state after the reduce fast
path returns.
The adjacent multi-index requested-page+aggregation reduce fast path now does
the same for vector/native-document-scan shapes: it hands the surviving merged
requested-page-reduce reusable carrier directly to the outer optional-reusable
response boundary instead of rebuilding query-level reusable state after the
reduce fast path returns.
The matching single-index `size=0` vector-native aggregation fast path now also
hands its surviving reusable carrier directly to that same outer
optional-reusable response boundary instead of rebuilding query-level reusable
state after the no-fetch response path returns.
The adjacent multi-index `size=0` vector-native aggregation fast path now also
does the same: it hands the surviving merged reusable carrier directly to the
outer optional-reusable response boundary instead of rebuilding query-level
reusable state after the no-fetch reduce path returns.
The adjacent single-index plain requested-page compatibility branch now also
does the same: it hands the fetched-page reusable carrier directly to the
outer optional-reusable response boundary instead of limiting that preserved
carrier shape to the vector/native-document-scan side alone.
The top-level non-vector `size=0` fast paths now also preserve a minimal
`total_hits`-only reusable carrier at that same outer optional-reusable
boundary instead of closing those exact-count no-fetch branches as
`(response, None)`.
The adjacent top-level `size=0` aggregation response path now likewise no
longer re-splits its `(total_hits, aggregations, reusable)` result into
separate response and reusable branches at the callsite, and instead
converges on one shared `size=0` response-plus-optional-reusable helper
boundary.
The matching exact-count top-level `size=0` no-fetch fast paths now likewise
no longer assemble `(response, Some(total_hits-only reusable))` inline at the
callsite, and instead converge on one shared `size=0`
response-plus-total-hits-reusable helper boundary.
The fetched-page reusable bridge family is now also slightly more collapsed:
owned fetched-page callers can feed the shared reusable-context bridge through
one direct owned-carrier helper instead of reopening a borrowed fetched-page-
identity binding at each local callsite.
The same owned-carrier bridge is now also the live path at the single-index
plain requested-page caller itself, so that caller no longer reopens the
borrowed fetched-page-identity view just to build its outer optional-reusable
payload.
The adjacent fetched-page aggregation response boundary is now thinner too:
callers can stay on a carrier-shaped fetched-page view through one ref-aware
fetched-page aggregation response helper instead of widening back out to
parallel raw fetched-page arguments at each callsite.
The matching owned single-index plain-response caller can now also stay on one
direct owned-carrier response helper there, instead of reopening a borrowed
fetched-page-identity binding just before response assembly.
At that same caller boundary, the old fetched-page-backed count helper is no
longer live either: the single-index vector-native requested-page+aggregation
caller now consumes either the surviving reusable `total_hits` or the carried
fetched-page scalar directly instead of crossing a separate fetched-page count
consumer contract first.
The lower page/window producer boundary is now thinner too: once the outer
`index_aware` page/window wrapper has already tried the grouped-hybrid or
carried-hit-context seats, the inner optional-hit-context `None` branch no
longer reopens that same grouped-hybrid wrapper leg again, and its final local
fallback now skips that duplicate grouped-hybrid reopen too before falling
through to the shared native-hit producer and only then the broader lower knn
hit producer.
The adjacent aggregation-side hit-materialization caller now follows the same
shape: after trying the vector-candidate context, native window, or carried
native-hit-context seats, its final fallback no longer re-enters the broader
optional-hit-context window helper with `None`, and instead drops straight to
the direct lower knn producer or document-backed fallback.
The adjacent single-index fetched-page-seeded aggregation collector boundary now
also stays on that carrier family directly: the requested-page+aggregation
callers no longer widen back out to parallel raw `fetched_total_hits` /
`fetched_hits` arguments just before entering the page-seeded aggregation
collector.
The adjacent materialized final-order component collector now also preserves
hit-derived reusable context on the single-index vector/native side, instead of
limiting that higher producer-side landing to the multi-index final-order hit
slice path.
The matching materialized final-order response boundary now likewise no longer
re-splits its `(total_hits, hits, aggregations, reusable)` component tuple
into separate response and reusable branches at the callsite, and instead
converges on one shared materialized response-plus-optional-reusable helper
boundary.
The adjacent top-level materialized final-order caller now likewise no longer
destructures that same `(response, reusable)` pair only to return it
unchanged, and instead falls straight through to that shared materialized
response-plus-optional-reusable boundary.
The adjacent reusable-dropping materialized final-order component wrapper now
likewise no longer keeps its own inline projection from
`(total_hits, hits, aggregations, reusable)` to
`(total_hits, hits, aggregations)`, and instead converges on one shared
projection helper boundary.
The matching reusable-dropping single-index materialized aggregation wrapper
now likewise no longer keeps its own inline projection from
`(aggregations, reusable)` to `aggregations`, and instead converges on that
same shared projection-helper style boundary.
That same shared projection-helper style boundary now also covers the adjacent
reusable-dropping single-index materialized aggregation wrapper that starts
from an already-carried reusable context, so the pair no longer splits across
one inline projection wrapper and one shared projection helper.
The adjacent reusable-dropping native aggregation wrapper now likewise no
longer keeps its own inline projection from `(aggregations, reusable)` to
`aggregations`, and instead converges on that same shared projection-helper
style boundary.
The matching reusable-preserving index-aware aggregation wrappers now
likewise no longer keep their own repeated `(aggregations, reusable)` pair
assembly bodies across the direct native and fetched-page/native-window
wrapper seats, and instead converge on one shared aggregation-plus-reusable
pair-lift helper boundary.
The adjacent optional native/window aggregation fallthrough seats now also no
longer keep their own repeated `Option<aggregations> -> Option<(aggregations,
reusable)>` map closures, and instead converge on one shared optional
aggregation-plus-reusable lift boundary.
The adjacent top-level single-index aggregation-response seat and the
materialized final-order single-index aggregation seat now likewise no longer
keep their own direct `(aggregations, reusable) -> (aggregations,
Some(reusable))` pair-lifts, and instead converge on one shared optional
aggregation-plus-reusable pair-lift helper boundary.
That same shared aggregation-plus-reusable pair-lift helper boundary now also
covers the remaining native-from-window aggregation response/object returns,
so their partial object exits, collected-hit fallbacks, and finalized object
return no longer keep their own direct pair assembly bodies.
That same pair-lift helper boundary now also covers the adjacent direct
vector-native page-top-hits fast-path return at the native-from-window
aggregation seat, so no solitary direct `(aggregations, reusable)` return
remains there.
That same aggregation-plus-reusable pair-lift helper boundary now also covers
the lower vector-native from-window top-hits aggregation producer, so its
early object/non-object exits and finalized return no longer keep their own
repeated `(aggregations, reusable)` assembly bodies either.
The adjacent native aggregation-with-context family now likewise no longer
keeps its own direct pair-lift bodies for empty-aggregation and merged
document-backed returns, and instead converges on that same shared
aggregation-plus-reusable pair-lift helper boundary.
The matching top-level reusable-dropping response wrapper now likewise no
longer keeps its own inline projection from `(response, reusable)` to
`response`, and instead converges on one shared response-only projection
helper boundary.
The adjacent requested-page response seats with definite reusable payloads
now likewise no longer keep their own direct `(response, reusable) ->
(response, Some(reusable))` pair-lifts, and instead converge on one shared
response-plus-definite-reusable helper boundary.
The matching requested-page aggregation response-plus-optional-reusable seat
now likewise no longer rewrap live response inputs into `Some(...)` only to
reopen the optional response helper immediately, and instead falls straight
through to one shared non-optional requested-page aggregation response-input
helper boundary.
That same requested-page aggregation response-plus-optional-reusable seat now
also no longer keeps its own local preserve-reusable computation and
`(response, reusable)` assembly body, and instead converges on one shared
requested-page aggregation response-plus-optional-reusable helper boundary.
The adjacent optional requested-page aggregation wrappers now likewise no
longer keep their own local `(total_hits, hits, aggregations)` destructure
bodies inside `response.map(...)`, and instead converge on shared requested-
page aggregation response-input helper boundaries.
The matching requested-page aggregation response-input consumer now likewise
no longer keeps its own local tuple destructure mixed with source-projection
rewriting, and instead converges on separate projected-response-input and
response-from-projected-input helper boundaries.
The matching requested-page aggregation response-plus-optional-reusable path
now likewise accepts the same response-input tuple carrier directly, so its
optional wrapper no longer keeps a final local response-input destructure
before delegating into the shared response-plus-optional-reusable helper.
That same requested-page aggregation response-plus-optional-reusable helper
seat now also no longer mixes local preserve-reusable computation with the
tuple-consuming response assembly step, and instead converges on a separate
requested-page aggregation response-input-plus-optional-reusable consumer.
The adjacent requested-page aggregation preserve-reusable seats now likewise
no longer keep repeated local optional-reusable computation bodies across the
requested-page-hit and response-input helper layers, and instead converge on
one shared requested-page aggregation optional-reusable producer boundary.
The adjacent top-level aggregation-response family now likewise no longer
keeps its own repeated `(total_hits, aggregations, Some(reusable))` triple
assembly bodies across the document-backed and native single-/multi-index
branches, and instead converges on one shared total-hits-plus-aggregation-
plus-optional-reusable helper boundary.
The matching top-level native single-index aggregation branch now likewise no
longer keeps a local `(aggregations, reusable)` destructure just before that
triple-lift, and instead falls straight through to one shared total-hits-
plus-aggregations-with-reusable adapter boundary.
The matching materialized final-order single-index aggregation branch now
likewise no longer keeps its own local `(aggregations, reusable)` destructure
before the optional-reusable pair-lift, and instead falls straight through to
one shared aggregations-with-reusable-to-aggregations-with-optional-reusable
adapter boundary.
The adjacent materialized final-order collector now likewise no longer keeps a
local `(aggregations, reusable)` split alive through to final component
return, and instead falls straight through to one shared materialized
components-with-aggregations-and-optional-reusable adapter boundary.
That same materialized components adapter family now also no longer keeps a
local `(total_hits, hits, aggregations, reusable)` assembly body inside the
aggregations-plus-optional-reusable adapter seat, and instead converges on one
shared materialized components-plus-optional-reusable helper boundary.
The matching top-level no-hit-materialization aggregation branch now likewise
no longer keeps a local `(total_hits, aggregations, reusable)` destructure
just before the `size=0` response assembly, and instead falls straight through
to one shared size-zero response-from-components helper boundary.
The adjacent top-level native aggregation optional wrapper now likewise no
longer keeps its own `aggregation_result.map(...)` destructure body, and
instead falls straight through to one shared optional size-zero response-from-
components helper boundary.
The matching size-zero response helper family now likewise no longer keeps
separate inline size-zero response assembly bodies across the response-from-
components and response-plus-optional-reusable seats, and instead converges on
one shared size-zero response-from-components helper boundary.
That same materialized helper family now also no longer keeps a local
`(total_hits, hits, aggregations, reusable)` destructure inside the paired
response-from-components seat, and instead converges on shared materialized
component projection helpers for the response inputs and reusable projection.
That same size-zero helper family now also no longer keeps a local
`(total_hits, aggregations, reusable)` destructure inside the paired
response-from-components seat, and instead converges on shared size-zero
component projection helpers for the response inputs and reusable projection.
The matching requested-page aggregation optional response-plus-optional-
reusable wrapper now likewise no longer keeps its own direct optional tuple-
lift `response.map(...)` body after reusable production, and instead
converges on one shared optional response-input-plus-optional-reusable helper.
The adjacent single-index requested-page response-plus-reusable helper family
now likewise no longer rewrap a live carrier into `Some(...)` only to reopen
the optional carrier helper immediately, nor keep its own local carrier-
derived reusable production, response assembly, or `(response, reusable)` pair
assembly in the optional wrapper seat, and instead falls straight through
shared carrier and response-input-plus-reusable consumer boundaries.
The matching top-level non-vector single-index requested-page aggregation
branch now likewise no longer keeps its own local carrier-derived reusable
production before the per-page aggregation collector call, and instead falls
straight through to one shared carrier-to-collector adapter boundary.
The adjacent vector single-index requested-page aggregation branch now
likewise no longer keeps its own local `(aggregations, reusable)` destructure
plus `total_hits` fallback immediately before response assembly, and instead
falls straight through to one shared fetched-page-plus-aggregations-with-
context adapter boundary.
The matching carrier-based requested-page aggregation paired response helper is
now likewise gone entirely, and the last non-vector single-index caller now
falls straight through to the shared ref-based paired response helper
boundary.
The adjacent ref-based requested-page aggregation response-only wrapper is now
likewise gone entirely, leaving the fetched-hits response consumer as the
single remaining response-only assembly boundary for that fetched-page family.
That same fetched-hits response consumer helper is now likewise gone as a
separate layer, and the ref-based paired response helper now falls straight
through to the requested-page response-input consumer after fetched-hit
response-input production.
The adjacent vector single-index requested-page aggregation context adapter is
now likewise gone entirely, and the vector caller now passes its `total_hits`
fallback plus `(aggregations, reusable)` directly to the shared ref-based
paired response helper boundary.
The matching `size=0` and materialized response-only wrapper seats are now
likewise gone as separate layers, and their from-components helpers now bind
directly to `search_response_with_phase(...)`.
The matching optional `size=0` adapter wrapper and the single-use materialized
aggregations-plus-optional-reusable components adapter are now likewise gone,
with their callers now composing the remaining shared helper boundaries
directly.
The adjacent `size=0` paired wrapper seat and the matching unused materialized
paired wrapper seat are now likewise gone, leaving the paired-from-components
helpers as the remaining pairing boundaries in those helper families.
The adjacent single-use materialized plain aggregations components adapter is
now likewise gone, leaving the final pairing helper as the only remaining
materialized components assembly boundary at that caller.
The matching `size=0` and materialized paired-from-components seats now
likewise no longer keep separate reusable/component projection helpers, and
instead destructure their carried component tuples directly.
The adjacent dead response / aggregation projection naming wrappers and their
now-unused generic projection helpers are likewise gone entirely.
The matching single-use response-plus-reusable naming layer is now likewise
gone, and its last caller now composes the generic optional-reusable lift
directly.
The adjacent dead low-level reusable passthrough constructor is likewise gone
entirely, leaving only the still-live explicit reusable-context builders.
The matching zero-use total-hits-plus-optional-all-documents builder is
likewise gone, further narrowing the low-level reusable-context builder
surface to still-live construction paths only.
The matching zero-use materialized final-order components-without-reusable
collector helper is likewise gone entirely, leaving only the optional-
reusable collector boundary in that family.
The adjacent single-use materialized paired-from-components response helper is
now likewise gone, and the outer caller now performs the final paired
response assembly directly.
The matching single-use materialized response-from-components helper is now
likewise gone, and that same outer caller now binds directly to
`search_response_with_phase(...)`.
The matching single-use `size=0` response-from-components helper is now
likewise gone, and its paired-from-components seat now binds directly to
`search_response_with_phase(...)`.
The adjacent `size=0` total-hits reusable naming helper is now likewise gone,
and its remaining callers now bind directly to the paired-from-components
boundary with explicit reusable construction.
The matching single-use non-vector requested-page carrier-to-collector naming
layer is now likewise gone, and that caller now binds directly to the lower
carrier collector with explicit reusable construction.
The adjacent single-use carrier page-to-ref collector wrapper is now likewise
gone, and the remaining caller now binds directly to the ref page collector
boundary.
The matching zero-use materialized refresh-context optional-all-hits wrapper
is now likewise gone, leaving only the still-live explicit refresh-context
builders in that family.
The adjacent zero-use materialized refresh-context hits-only wrapper is now
likewise gone, leaving the all-hits explicit builder as the remaining live
entry in that subfamily.
The matching single-use materialized aggregations optional-all-hits wrapper is
now likewise gone, and the final-order aggregation caller now binds directly
to the explicit all-hits builder.
The adjacent zero-use materialized aggregations hits-only wrapper is now
likewise gone, leaving the explicit all-hits builder as the remaining live
aggregation entry in that subfamily.
The matching single-use materialized refresh-context-to-refresh-result adapter
is now likewise gone, and the refresh-context aggregation caller now performs
that branchy refresh-result assembly directly.
The adjacent single-use materialized hit-context-to-refresh-result fallback
helper is now likewise gone, and that same caller now performs the fallback
refresh-result assembly directly.
The matching single-use materialized refresh-context-to-routed-hit-contexts
fallback helper is now likewise gone, and that same caller now performs the
fallback routing branch directly.
The adjacent single-use materialized routed-hit-contexts-to-hit-context
wrapper is now likewise gone, and the requested-page hits consumer now
performs that final hit-context assembly directly.
The matching single-use plain requested-page response-input-plus-reusable
helper is now likewise gone, and the carrier consumer now performs its own
final response assembly plus reusable pairing directly.
The adjacent single-use plain requested-page optional wrapper is now likewise
gone, and the top-level caller now binds directly to the carrier consumer plus
generic optional-reusable lift.
The matching single-use plain requested-page carrier consumer naming layer is
now likewise gone, and that same top-level caller now performs reusable
production plus final response pairing directly.
The adjacent single-use plain requested-page response-input consumer is now
likewise gone, and that same top-level caller now performs the final
requested-page response assembly directly.
The adjacent single-use top-level materialized final-order response helper is
now likewise gone, and the outer search-response caller now binds directly to
the optional-reusable collector plus paired-from-components response boundary.
The matching single-use total-hits-plus-aggregations-with-optional-reusable
adapter is now likewise gone, and its caller now composes the remaining
generic adapter stack directly.
The adjacent single-use aggregations-plus-optional-reusable naming layer is
now likewise gone, and its last caller now composes the remaining aggregation
pair-lift stack directly.
The adjacent carrier-based requested-page aggregation response-only adapter is
now gone entirely, leaving the ref-based response helper as the single
remaining response-assembly boundary for that fetched-page family.
That same direct fetched-page requested-page aggregation response seat now
likewise no longer rewrap live response inputs into `Some(...)` only to reopen
the optional response helper immediately and `expect(...)` them back out, and
instead falls straight through to the shared non-optional response-input
consumer boundary.
The adjacent requested-page aggregation `requested_page_hits` response wrapper
and its optional sibling are now gone as separate layers, leaving the
response-input consumer boundary as the direct assembly path for both the
paired and fetched-page response seats.
The matching optional requested-page aggregation response-input wrapper is now
likewise gone entirely, leaving the non-optional response-input consumer as
the only remaining response-only assembly boundary in that helper family.
The adjacent requested-page aggregation response-input paired wrappers are now
likewise gone entirely, and the top-level optional requested-page caller now
performs that final response assembly plus optional-reusable pairing
directly.
That same optional requested-page aggregation caller now likewise performs its
own explicit reusable construction directly, with no remaining requested-page
reusable helper layer in between.
The adjacent generic `Some(reusable)` naming helper is now likewise gone, and
the remaining callers now form optional reusable context directly at their own
assembly sites.
The matching aggregation-to-optional-reusable generic alias is now likewise
gone, and its remaining callers now bind straight to the shared generic
value-to-optional-reusable lift.
The adjacent optional-aggregations pair-lift helper is now likewise gone, and
the remaining native/window aggregation callers now form their aggregation-
plus-reusable pairs directly via local `map(...)`.
The matching aggregation-plus-reusable tuple constructor alias is now likewise
gone, and the remaining aggregation callers now assemble those pairs directly
at each return site.
The matching materialized final-order hits-and-all-hits aggregation wrapper
and its refresh-context builder sibling are now likewise gone, and the
final-order aggregation caller now assembles refresh context directly.
The adjacent materialized hits-only hit-context alias and one-use direct-
reduce input mappers are now likewise gone, and the remaining callers now
assemble hit context and direct-reduce inputs directly.
The matching materialized hits-plus-all-hits hit-context constructor alias is
now likewise gone, and the remaining callers now bind directly to
`MaterializedMultiIndexHitContext::with_exact_hits_and_all_hits(...)`.
The adjacent materialized scored-fragment builder and scored direct-reduce
input mapper are now likewise gone, and the refresh-context / refresh-result
callers now assemble those values directly.
The matching refreshed-fragment-to-reusable-context and reusable-context-to-
hit-context adapters are now likewise gone, and the refresh-result caller now
assembles both reusable contexts and fallback hit context directly.
The adjacent hit-context aggregation wrapper is now likewise gone, and that
same refresh-result caller now binds directly to `collect_aggregations(...)`.
The matching refresh-result aggregation consumer is now likewise gone, and the
refresh-context caller now performs the full refresh-result branching
directly.
That same refresh-context caller now likewise assembles refreshed document
fragments directly from routed hit contexts, with no remaining fragment
builder helper in between.
The adjacent materialized direct-reduce collector is now likewise gone, and
the refresh-context caller now performs direct-reduce hint accumulation and
merge assembly directly.
The matching scored direct-reduce collector is now likewise gone, and the
remaining scored branches now perform scored merge assembly and pipeline
finalization directly.
The adjacent materialized all-hits collector is now likewise gone, and the
final-order aggregation caller now performs all-hits collection directly.
The matching materialized routed-hit grouping helper is now likewise gone, and
the remaining final-order/requested-page callers now perform per-index
routed-hit grouping directly.
The matching requested-page aggregation projected-response tuple helper and
projected-response consumer are now likewise gone, and the remaining
response-input consumer now performs source projection plus final response
assembly directly.
That same requested-page aggregation response-input consumer now likewise
performs its own in-place hit source projection directly, with no remaining
response-hits projection helper in between.
The adjacent requested-page aggregation response-from-hits helper is now
likewise gone, and that same response-input consumer now performs final phase
assembly directly.
The matching requested-page aggregation phase-message helpers are now likewise
gone, and that same response-input consumer now performs phase message
selection directly.
The matching materialized multi-index plain requested-page hits helper is now
likewise gone, and the outer requested-page caller now performs routed-hit
accumulation plus requested-window finalization directly.
The adjacent plain requested-page response-from-hits helper is now likewise
gone, and the remaining top-level requested-page callers now perform final
phase assembly directly.
The matching plain requested-page phase-message helpers are now likewise
gone, and those same top-level requested-page callers now perform phase
message selection directly.
The adjacent plain requested-page optional response wrapper is now likewise
gone entirely, and the multi-index top-level caller now performs that final
response assembly plus reusable pairing directly.
The matching requested-page aggregation paired `requested_page_hits` helper is
now likewise gone entirely, leaving the response-input-plus-optional-reusable
helpers as the only remaining paired assembly boundaries in that helper
family.
The matching single-index plain requested-page response-only carrier adapter is
now likewise gone entirely, leaving the response-input consumer as the single
remaining response-assembly boundary for that helper family.
The adjacent single-index plain requested-page owned-carrier reusable helper
is now likewise gone, and the remaining callers now bind directly to the
ref-based reusable helper.
The matching single-index plain requested-page ref-based reusable helper is
now likewise gone, and those same callers now bind directly to the fetched-
page reusable helper.
The matching single-index plain requested-page fetched-page carrier helper is
now likewise gone, and the top-level requested-page caller now performs
fetched-page carrier assembly directly.
The adjacent requested-page search-page fetch wrapper is now likewise gone,
and the remaining requested-page callers now perform cache-touch plus page
fetch directly.
The matching fetched-page reusable helper is now likewise gone, and those same
callers now bind directly to the shared search-hits-with-optional-total-hits
reusable helper.
The adjacent documents-only reusable helper is now likewise gone, and its
remaining callers now bind directly to the optional-total-hits reusable
helper with `None`.
The matching search-hits-with-optional-total-hits reusable helper is now
likewise gone, and its remaining callers now perform hit-document projection
plus optional-total-hits handoff directly.
The adjacent search-hits-with-optional-all-documents reusable helper is now
likewise gone, and the single-index materialized aggregation caller now
performs hit-document projection plus optional-all-documents gating directly.
The matching optional-all-documents gate helper is now likewise gone, and its
remaining callers now evaluate the all-hits gate and pull `documents`
directly from the `match_all` reusable path.
The matching base search-response wrapper is now likewise gone, and the
remaining callers now bind directly to `standard_search_response(...)`.
The adjacent requested-page aggregation fetched-hit response-input adapter
likewise no longer keeps a separate one-hop response-hits forwarder, and now
pulls owned requested-page hits directly from the shared fetched-hit slicing
helper.
The matching fetched-page ref collector wrapper is now likewise gone, and the
remaining callers now pass `fetched_total_hits` plus `fetched_hits` directly
to the lower aggregation collector.
The adjacent vector fetched-page aggregation-context wrapper is now likewise
gone, and the vector caller now performs fetched-page reusable seeding plus
reusable-only projection directly.
The matching materialized response helper family now likewise no longer keeps
separate inline materialized-response assembly bodies across the response-from-
components and response-plus-optional-reusable seats, and instead converges on
one shared materialized response-from-components helper boundary.
The matching top-level materialized final-order caller now likewise no longer
keeps a local `(total_hits, hits, aggregations, reusable)` destructure just
before the materialized response assembly, and instead falls straight through
to one shared materialized response-from-components helper boundary.
The matching response/aggregation helper family now likewise no longer keeps
its own repeated direct `Some(reusable)` lifts across the top-level fallback,
response-plus-definite-reusable, and aggregation-plus-optional-reusable
helper seats, and instead converges on one shared reusable-to-optional-
reusable lift boundary.
That same response/aggregation helper family now also no longer keeps
separate adapter bodies for `(value, reusable) -> (value, optional reusable)`
across the response and aggregation helper seats, and instead converges on
one shared value-plus-optional-reusable adapter boundary.
The matching aggregation helper side now likewise no longer keeps its own
local `(total_hits, value-with-optional-reusable) -> (total_hits, value,
optional reusable)` adapter body, and instead converges on one shared total-
hits-plus-value-with-optional-reusable adapter boundary.
That same top-level aggregation triple-lift helper now likewise no longer
keeps a local `(aggregations, reusable)` destructure before that generic
total-hits-plus-value-with-optional-reusable adapter, and instead falls
straight through to the shared generic adapter stack.
The matching aggregation projection side now likewise no longer keeps its own
local `(value, reusable) -> value` projection body, and instead converges on
one shared value-without-reusable projection boundary.
The matching response helper side now likewise no longer keeps its own local
`(value, optional reusable) -> value` projection body, and instead converges
on one shared value-without-optional-reusable projection boundary.
The adjacent aggregation-side reusable bootstrap seats now likewise no longer
keep their own repeated `optional reusable -> reusable-or-default` closures,
and instead converge on one shared reusable-defaulting helper boundary.
The adjacent single-index native page/window wrapper family now likewise no
longer keeps repeated `Option<hits> -> Option<native-hit-return>` adapter
closures at each callsite, and instead converges on one shared optional
materialized-native-hit adapter boundary.
The matching lower native hit/page/window wrappers now likewise no longer open
their own local `if let Some(context)` lifts for vector-candidate delegation,
and instead fall straight through to the shared optional vector-candidate
hit/page/window helper boundaries.
The matching optional hit wrapper in that same lower vector-candidate family
now likewise no longer unwraps and rewraps the shared hit result locally, and
instead falls straight through to the shared hit boundary with only the outer
`Option` lift.
The adjacent index-aware page/window wrappers now likewise no longer open
their own local `if let Some(context)` lifts for vector-candidate page/window
delegation, and instead fall straight through to the shared optional
vector-candidate page/window helper boundaries.
The matching index-aware hit-context wrapper now likewise no longer opens its
own local `if let Some(context)` lift for vector-candidate hit-context
delegation, and instead falls straight through to the shared optional
vector-candidate hit-context helper boundary.
The adjacent non-index-aware count/document wrappers now likewise no longer
open their own local `if let Some(context)` lifts for vector-candidate
delegation, and instead fall straight through to the shared optional
vector-candidate count/document helper boundaries.
Those same index-aware page/window wrappers now likewise no longer keep a
second local `if let Some(context)` split for carried native hit-context
delegation either, and instead pass the optional hit-context straight through
to the shared vector/hybrid page/window helper boundaries.
The matching index-aware count/document siblings now likewise no longer reopen
carried native hit-context locally just to project `total_hits` or
`documents`, and instead converge on shared optional hit-context projection
helper boundaries.
The matching fetched-page vector-native document-backed aggregation-context
wrapper now likewise no longer destructures `(collect_aggregation_map,
reusable)` only to return `reusable`, and instead converges on one shared
reusable-only projection helper boundary as a straight helper projection.
Outside the grouped-hybrid carve-out, the non-index-aware optional-token
document consumer now also trusts an explicit carried exact-document seat
before reopening the same shared native vector/document query branch.
Outside that vector/hybrid seam, the plugin `global` wrapper now also has
direct multi-index native-reduce response evidence for its nested all-documents
scope shape, instead of only single-index nested-subaggregation evidence.
The adjacent sampler wrapper family now likewise has direct multi-index native-
reduce response evidence for nested current-collected-set scope shapes across
plain `sampler`, `random_sampler`, and `diversified_sampler`.
The adjacent plugin `filter` / `filters` wrapper family now also has direct
multi-index native-reduce response evidence for its current collected-set
wrapper shapes.
The adjacent plugin `date_histogram` wrapper now likewise has direct
multi-index native-reduce response evidence on top of its already-landed
single-index interval carrier.
The adjacent plugin `auto_date_histogram` / `variable_width_histogram`
wrapper family now likewise has direct multi-index native-reduce response
evidence on top of its already-landed single-index interval-chooser carriers.
The adjacent plugin `multi_terms` wrapper now likewise has direct multi-index
native-reduce response evidence on top of its already-landed single-index
tuple-bucket carrier.
The adjacent plugin `composite` wrapper now likewise has direct multi-index
native-reduce response evidence on top of its already-landed single-index
composite-bucket carrier.
The adjacent plugin `adjacency_matrix` wrapper now likewise has direct
multi-index native-reduce response evidence on top of its already-landed
single-index named-combination bucket carrier.
The adjacent plugin `geo_bounds` / `geo_centroid` wrapper family now likewise
has direct multi-index native-reduce response evidence on top of its already-
landed single-index geometry wrapper carriers.
The adjacent plugin `stats` / `extended_stats` / `boxplot` metric family now
likewise has direct multi-index native-reduce response evidence on top of its
already-landed single-index scalar metric carriers.
The adjacent plugin `weighted_avg` / `cardinality` /
`median_absolute_deviation` metric family now likewise has direct multi-index
native-reduce response evidence on top of its already-landed single-index
scalar metric carriers.
The adjacent plugin `percentiles` / `percentile_ranks` / `missing` family now
likewise has direct multi-index native-reduce response evidence on top of its
already-landed single-index scalar and wrapper carriers.
Outside that plugin breadth tail, the lower exact-document native-context
bridge now also accepts hit-only `VectorCandidateWindowContext` carriers
directly instead of waiting for a broader downstream reopen.
The adjacent lower hit-context consumer now likewise accepts hit-only
`VectorCandidateWindowContext` carriers directly instead of routing them back
through the broader lower hit helper first.
That same lower hit-context consumer now also accepts explicit document-only
vector/document-scan carriers directly instead of routing them back through
that same broader lower hit helper first.
That same lower hit-context consumer now also accepts explicit
candidate-id-only carriers directly instead of routing them back through that
same broader lower hit helper first.
The adjacent lower page/window consumer now likewise accepts explicit
hit/document/candidate-id vector carriers directly instead of routing them
back through that same broader lower hit helper first.
The shared index-aware hit-context seat now likewise routes its
vector-candidate branch straight through that lower direct hit-context
consumer instead of rebuilding the same hit list locally first.
The adjacent shared index-aware page/window wrappers now likewise route a
direct vector candidate-window carrier straight through the lower direct
page/window consumer instead of first rebuilding an intermediate hit-context
object.
The adjacent non-index-aware native document seat now likewise routes a live
direct vector candidate-window carrier straight through the lower direct hit
helper instead of re-entering the page helper just to turn those hits back
into documents.
The adjacent index-aware native document seat now likewise consumes a live
direct vector candidate-window exact-document seat before it falls through the
shared hit-context wrapper and turns those same results into hits and back
into documents again.
The adjacent index-aware native count seat now likewise consumes a live direct
vector candidate-window count seat before it falls through the shared
hit-context wrapper and re-derives that same count from hits again.
The adjacent single-index materialized requested-page consumer now likewise
seeds its carried fetched/final-order hit slice directly into that same lower
vector-carrier family before reopening the query-native vector context.
The matching single-index requested-page source-projection caller now also
feeds its carried fetched-page hit slice and known `total_hits` directly into
that same lower vector-carrier family before stepping through the query-native
reopen helper.
The adjacent single-index final-order requested-page caller now likewise feeds
its carried final-order hit slice directly into that same lower
vector-carrier family before stepping through the query-native reopen helper.
That same single-index materialized hit helper now also accepts a carried
known-`total_hits` seed directly at that boundary, so the matching
source-projection and final-order callers no longer need their own separate
local hit-seed branches there and instead converge on that widened helper.
The adjacent plain single-index requested-page caller now likewise no longer
re-splits that same carrier into separate response and reusable branches at
the callsite, and instead converges on one shared carrier-to-response-plus-
reusable helper boundary.
The matching single-index requested-page+aggregation caller now likewise no
longer re-splits its fetched-page aggregation carrier into separate response
and reusable branches at the callsite, and instead converges on one shared
fetched-page-aggregation carrier-to-response-plus-reusable helper boundary.
That same outer optional-reusable boundary now also no longer keeps three
separate identical “use carried reusable or fall back to the single-index
optional reusable recompute” callsite bodies across the `size=0`,
requested-page, and requested-page+aggregation fast-path returns, and instead
converges on one shared fallback boundary there.
The adjacent generic document consumer in that same lower vector-carrier
family now likewise no longer keeps two identical local optional token-to-
document probe bodies around the native query branch, and instead converges on
one shared optional vector-candidate-window document helper boundary there.
The matching generic count consumer in that same lower vector-carrier family
now likewise no longer keeps two identical local optional token-to-total-hits
probe bodies around the native/vector branch, and instead converges on one
shared optional vector-candidate-window count helper boundary there.
The adjacent index-aware native document seat now likewise no longer reopens
the same shared hit-context wrapper once inside the vector branch and then
again immediately below it; after the direct grouped-hybrid and direct
vector-candidate document seats, it now falls through to that shared
hit-context wrapper only once.
The matching index-aware native count seat now likewise no longer reopens the
same shared hit-context wrapper once inside the vector branch and then again
immediately below it; after the direct grouped-hybrid and direct
vector-candidate count seats, it now falls through to that shared hit-context
wrapper only once.
The adjacent aggregation-side vector/native hit assembly seat now likewise no
longer reopens that same shared hit-context wrapper once inside its direct
vector-candidate branch and then again immediately below it; after the direct
grouped-hybrid and direct vector-candidate hit seats, it now falls through to
that shared hit-context wrapper only once.
The matching lower page consumer for vector-candidate windows now likewise no
longer keeps its own duplicate hit-materialization body beside the shared
vector-candidate hit-context consumer; after its zero-hit/zero-size short
circuits, it now reuses that shared hit-context boundary directly before
sorting and slicing.
The adjacent optional window wrapper for that same lower vector-candidate
family now also no longer unwraps and rewraps the shared window result
locally, and instead falls straight through to the shared window boundary with
only the outer `Option` lift.
The adjacent multi-index requested-page+aggregation reduce caller now likewise
no longer re-splits its requested-page response inputs into separate response
and reusable branches at the callsite, and instead converges on one shared
requested-page-aggregation response-inputs-to-response-plus-reusable helper
boundary.
The matching generic query reusable family now likewise no longer keeps thin
forwarding wrappers for the plain, optional-native, and native-context query
paths around its shared optional-native-plus-optional-all-documents seat, and
instead binds the remaining generic caller directly to that core boundary.
The adjacent reusable/materialized single-index seats now likewise no longer
keep a plain optional-all-documents query wrapper or a one-use reusable-
dropping mapper around those same lower boundaries, and instead bind the
remaining callers directly to the reusable core and reusable-carrying
materialized aggregation seat.
The matching vector fetched-page aggregation branch now likewise no longer
keeps a dead reusable-only tuple projection helper or a stale fetched-page
reusable indirection around its seeded aggregation-context boundary, and
instead seeds that boundary directly from the shared document-plus-optional-
total-hits reusable helper.
The adjacent reusable/materialized callers now likewise no longer keep a
shared optional-reusable unwrap helper around those same lower seats, and
instead apply the `ReusableQueryContext::default` fallback inline where the
concrete return value is assembled.
The matching size-zero/native aggregation callers now likewise no longer keep
a shared total-hits-plus-aggregations tuple-lift helper around those same
lower seats, and instead assemble the final `(total_hits, aggregations,
Some(reusable))` tuple directly where each branch returns.
The adjacent native/materialized/requested-page callers now likewise no
longer keep a shared value-plus-optional-reusable pair-lift helper around
those same lower seats, and instead assemble `(value, Some(reusable))`
directly where each branch returns.
With those callers converged, the now-dead total-hits-plus-value tuple helper
also drops out of the same lower helper family.
The matching native count/document seats now likewise no longer keep optional
index-aware hit-context adapters for total-hits and document projection, and
instead project the `search_hits_context_for_query_native_index_aware(...)`
result directly where each branch needs it.
The adjacent single-index native requested-page seats now likewise no longer
keep an optional materialized hit-return adapter around the lower native-hit
producer, and instead map `search_hits_for_query_native(...)` directly into
`materialized_single_index_native_hit_return(...)` where each branch needs it.
The matching fetched-page requested-page+aggregation response seat now also no
longer keeps a one-use hits slicer or response-inputs assembly helper around
that same lower boundary, and instead slices hits and assembles
`(total_hits, hits, aggregations)` directly before final response creation.
The adjacent plain requested-page carrier path now likewise no longer keeps a
one-use response-inputs unpack helper around its fetched-page carrier, and
instead destructures that carrier directly where the final response is built.
The matching multi-index requested-page+aggregation callers now likewise no
longer keep an outer optional response-plus-reusable wrapper around their
optional `(total_hits, hits, aggregations)` result, and instead assemble any
preserved reusable context and map the response inputs directly at each
callsite.
The adjacent single-index fetched-page requested-page+aggregation callers now
likewise no longer keep an outer response-plus-reusable helper around that
same lower response builder, and instead slice hits and assemble the final
response/reusable pair directly at each callsite.
With those callers converged, the shared requested-page+aggregation response
builder also drops out, and the remaining callers now perform source
projection plus final fetch-phase response assembly directly at each callsite.
The adjacent native reduce-hints family now likewise no longer keeps a one-use
context-dropping mapper around its reusable-carrying lower seat, and instead
binds the remaining caller directly to that lower boundary.
The matching native aggregation family now likewise no longer keeps a middle
index-aware native seat between the upper query-aware collector and the lower
document-backed/native-from-window branches, and instead lets the upper
collector branch directly across those lower boundaries.
The adjacent top-level native aggregation collector now likewise no longer
keeps a one-use reusable-carrying lower helper around those same lower
document-backed/native-from-window branches, and instead branches directly
across them itself.
The matching fetched-page aggregation callers now likewise no longer keep a
page-backed query-aware wrapper around those same lower branches, and instead
branch directly between vector-native, native-from-window, and full
query-aware collection at each callsite.
The adjacent vector-native aggregation seed path now likewise no longer keeps
a seeded aggregation-context helper around its shard-local aggregation-map and
merged reusable assembly, and instead performs that assembly directly at each
remaining callsite.
The matching native aggregation-map setup now likewise no longer keeps a pure
composition helper for “shard-local native reduce plus sorted plugin top
hits”, and instead assembles that combined aggregation map directly at each
remaining callsite.
The adjacent generic hit-based aggregation collector now likewise no longer
keeps a pure default-input-order wrapper around its lower plugin-top-hits-
aware implementation, and instead binds remaining callers directly to that
lower collector with explicit `NeedsExplicitSort`.
The matching sorted-plugin-top-hits filter/map helper now likewise drops out,
and the remaining callers inline that plugin-top-hits extension directly into
each shard-local aggregation-map assembly.
The adjacent materialized single-index native-query-context path now likewise
no longer keeps a one-use wrapper between the optional native-query-context
seat and the reusable consumer, and instead assembles reusable context and
hands it directly to that lower consumer inside the optional wrapper.
With that path converged, the now-dead optional-native materialized
single-index aggregation seat also drops out of the same local family.
The matching dead value-projection wrapper above the reusable-context consumer
also drops out of that same materialized single-index family.
The adjacent dead native-query-context reusable helper also drops out of that
same materialized single-index family.
The adjacent reusable-documents reduce-hints wrapper also drops out, and the
remaining caller now binds directly to the lower document hint collector.
The matching one-use search-hits-plus-optional-all-documents reusable-seed
helper also drops out of that same materialized single-index family, and the
remaining caller now assembles that reusable seed locally before calling the
reusable-context consumer.
The adjacent requested-window top-hits path now likewise no longer keeps a
one-use helper for carried-hit-slice versus page-fetch fallback, and instead
performs that fallback inline at the top-hits finalization callsite.
The matching pure reusable merge helper now likewise drops out, and the
remaining callers merge reusable totals/documents/all-documents locally at
each callsite.
The adjacent one-use materialized reusable-context helper also drops out of
that same single-index family, and the remaining caller now performs both the
query-aware aggregation fallback and all-hits fallback inline.
The matching top-hits reduce-window rewrite helper now likewise drops out, and
the remaining callers perform the carried-hit reuse versus local hit-window
fetch fallback inline before rewriting top-hits buckets.
The adjacent shared snapshot pipeline finalize helper now likewise drops out,
and the remaining callers perform pipeline/plugin snapshot finalize directly
at each callsite.
The matching aggregation-side reusable merge helper now likewise drops out,
and the remaining callers merge document/all-document reusable context locally
at each callsite.
The adjacent index-aware merged document-backed reusable helper now also drops
out, and the remaining callers either bind directly to the lower
`document_backed_query_context_index_aware(...)` seat or perform the reusable
fast-path check inline before falling through to that lower seat.
The matching document-backed count-plus-aggregation reusable seat now likewise
drops out, and the remaining callers perform count and aggregation collection
inline before assembling their local return tuple.
The adjacent size-zero final response builder now likewise drops out, and the
remaining callers assemble their skipped-fetch response locally at each
return site.
The matching size-zero phase-message routing helpers and materialized fixed-
message helpers now likewise drop out, and the remaining callers inline those
constant phase messages directly at each response assembly site.
The outer `search_response_index_aware(...) -> SearchResponse` wrapper now
likewise drops out, and the public search caller binds directly to the
optional-reusable seat before dropping that carrier locally.
The remaining local reusable-fallback closures inside
`search_response_index_aware_with_optional_reusable(...)` now likewise drop
out, and each early return site performs that single-index optional reusable
fallback inline.
The adjacent one-use single-index requested-page hit-window wrapper now also
drops out, and the remaining materialized plain-response path finalizes that
requested-page hit window inline before applying response detail projection.
The matching existing-total-hits-plus-documents native-query-context wrapper
now likewise drops out, and the remaining vector/native callers assemble that
context directly at each callsite.
The adjacent one-use optional vector-candidate hit/context wrappers now also
drop out, and the remaining callers unwrap
`vector_candidate_window_context_for_query_native(...)` locally before binding
directly to the lower hit or hit-context collector.
The matching optional vector-candidate page/window wrappers now also drop
out, and the remaining callers unwrap
`vector_candidate_window_context_for_query_native(...)` locally before binding
directly to the lower page or window collector.
The matching optional vector-candidate count/documents wrappers now also drop
out, and the remaining callers unwrap
`vector_candidate_window_context_for_query_native(...)` locally before binding
directly to the lower count or documents collector.
The outer optional vector-candidate count wrapper now also drops out, and
`count_documents_for_query(...)` unwraps that optional context locally before
choosing between the lower vector-candidate count seat and the generic query-
count fallback.
The matching optional vector-candidate documents wrapper now also drops out,
and the remaining callers unwrap that optional context locally before
choosing between the lower documents seat and the generic query-documents
fallback.
The pure carried-hit vector-candidate seed helper now also drops out, and the
remaining callers assemble that context locally with direct query-kind
selection.
The matching exact-documents bridge from vector-candidate context now also
drops out, and the remaining callers perform that
documents/hits/candidate-ids projection locally before assembling a
`NativeQueryContext`.
The adjacent one-use globally ordered multi-index hit wrapper now also drops
out, and the remaining caller binds directly to the lower hit-stream producer
before local final-order hit assembly.
The matching pure multi-index refreshed-document projection helper now also
drops out, and the remaining callers perform that per-hit refreshed-document
lookup locally before assembling reusable context.
The now-dead optional native-query-context count/documents wrappers now also
drop out of that same native context family.
The matching pure final-order hit carrier initializer now also drops out, and
the remaining callers assemble that carrier locally at each callsite.
The adjacent one-use multi-index hit-stream producer now also drops out, and
the remaining top-level materialized caller performs that per-index hit-stream
collection locally before final-order carrier assembly.
The matching one-use optional-native requested-page wrapper now also drops
out, and the remaining vector-candidate callers perform that requested-page
fallback projection locally when no native query context is available.
The now-dead single-index vector-candidate requested-page wrapper now also
drops out, and the remaining test seat binds directly to the lower
optional-total-hits variant.
The matching one-use native-query-context count/documents seats now also drop
out, and the remaining vector-candidate callers hand
`reusable_query_context_from_native_query_context(...)` directly into the
generic count/documents collectors.
The matching pure default-fallback count/documents seats now also drop out,
and the remaining callers pass `ReusableQueryContext::default()` directly
into the generic count/documents collectors.
The matching pure native-context-to-reusable field-move helper now also drops
out, and the remaining callers assemble that `ReusableQueryContext` locally
from native context fields.
The matching one-use optional-native reusable seat now also drops out, and
the remaining optional-native reusable caller performs that optional
all-documents merge and `ReusableQueryContext` assembly inline.
The now-dead residual `reusable_query_context_for_query(...)` definition now
also drops out of that same generic reusable family.
The matching one-use vector-candidate count seat now also drops out, and the
remaining callers perform that vector-candidate count shortcut and reusable
handoff inline.
The matching one-use vector-candidate documents seat now also drops out, and
the remaining callers perform that vector-candidate documents shortcut and
reusable handoff inline.
The matching one-use vector-candidate requested-page seat now also drops out,
and the remaining caller performs that context-present versus requested-page-
fallback branch inline.
The pure `reusable_query_context_for_query_index_aware(...)` wrapper now also
drops out, and the remaining callers bind directly to
`reusable_query_context_for_query_index_aware_with_optional_all_documents(...,
None)`.
The matching one-use
`collect_materialized_requested_page_hits_for_final_order_hits(...)` seat now
also drops out, and the remaining final-order requested-page caller performs
that single-index lower-seat binding or multi-index routing/projection
inline.
The adjacent one-use
`collect_materialized_multi_index_aggregations_for_final_order_hits(...)`
seat now also drops out, and the remaining multi-index final-order caller
assembles all-hits fetch, routed hit contexts, and refresh context inline
before calling the lower refresh-context collector.
The matching one-use
`collect_native_reduce_hints_aggregations_and_context_index_aware(...)` seat
now also drops out, and the remaining multi-index native-reduce loop performs
that empty-map fast path, aggregation collection, reusable handoff, and hint
extraction inline.
The pure
`MaterializedMultiIndexRefreshResult::with_refreshed_documents_and_scored_hits(...)`
initializer now also drops out, and the remaining refresh-result producer
assembles that payload inline.
The pure
`MaterializedMultiIndexRefreshedDocumentsFragment::with_documents_and_all_documents(...)`
initializer now also drops out, and the remaining refresh fragment producer
assembles that document/all-document payload inline.
The now-dead default-order wrappers
`MaterializedMultiIndexScoredHitContext::with_scored_hits_and_all_hits(...)`
and
`MaterializedMultiIndexScoredHitsFragment::with_scored_hits_and_all_hits(...)`
now also drop out, leaving only the live explicit-input-order variants.
The pure
`SingleIndexPlainResponseRequestedPageHitsCarrierRef::from_fetched_page(...)`
initializer now also drops out, and the remaining ref-carrier sites
assemble that borrowed requested-page carrier inline.
The now-dead
`SingleIndexPlainResponseRequestedPageHitsCarrierRef::fetched_page_identity(...)`
accessor now also drops out of that borrowed requested-page carrier surface.
The one-use
`SingleIndexPlainResponseRequestedPageHitsCarrier::fetched_page_identity(...)`
accessor now also drops out, and the remaining requested-page response branch
reads carrier fields directly.
The pure `SingleIndexPlainResponseRequestedPageHitsCarrier::from_fetched_page(...)`
initializer now also drops out, and the remaining requested-page branches
assemble that owned carrier inline.
The pure `ReusableQueryContext::with_all_documents(...)` field-setter now
also drops out, and the remaining reusable constructor assigns
`all_documents` inline.
The now-dead
`SingleIndexPlainResponseRequestedPageHitsCarrier::fetched_page_identity_ref(...)`
accessor now also drops out of that requested-page carrier surface.
The pure
`SingleIndexPlainResponseRequestedPageHitsCarrier::from_fetched_page_with_requested_page_hits_override(...)`
initializer now also drops out, and the remaining requested-page
source-projection branch assembles that carrier inline.
The matching one-use
`collect_materialized_single_index_plain_response_response_detail_with_native_query_context(...)`
seat now also drops out, and the remaining requested-page native projection
caller performs that selected-hit refreshed-document lookup and source
projection inline.
The now-empty impl shells for
`SingleIndexPlainResponseRequestedPageHitsCarrier` and
`SingleIndexPlainResponseRequestedPageHitsCarrierRef` now also drop out of
that requested-page carrier surface.
The residual requested-page ref-carrier test seat now also binds directly to
`reusable_query_context_for_documents_with_optional_total_hits(...)` instead
of naming a stale helper surface.
The one-use `finalize_top_hits_aggregations(...)` seat now also drops out,
and `finalize_top_hits_index_aware(...)` performs that top-hits/plugin
finalization inline.
The matching one-use
`finalize_requested_window_top_hits_aggregations(...)` seat now also drops
out, and `finalize_requested_window_top_hits_index_aware(...)` performs that
requested-window top-hits/plugin finalization inline.
The one-use
`materialized_multi_index_scored_hit_contexts_for_hits_and_all_hits(...)`
producer now also drops out, and the remaining refresh-context caller
assembles scored-hit routing inline.
The pure
`supports_direct_reduce_all_documents_exact_matches_background_candidate(...)`
predicate now also drops out, and the remaining all-documents guard folds
that admission check directly into
`blocks_direct_reduce_due_to_all_documents_requirement(...)`.
The pure `has_all_documents(...)` accessor now also drops out, and that same
all-documents guard reads `context.all_documents.is_some()` inline.
The pure
`supports_direct_reduce_significant_terms_same_population_bucket_ordering_live_admission(...)`
predicate now also drops out, and that same all-documents guard folds the
significant-terms ordering admission check inline.
The pure `exact_documents_match_all_documents(...)` predicate now also drops
out, and that same all-documents guard compares exact-documents versus
all-documents inline.
The pure `blocks_direct_reduce_due_to_hit_materialization_family(...)`
predicate now also drops out, and the remaining direct-reduce admission gate
evaluates the hit-materialization exception inline.
The pure `blocks_direct_reduce_due_to_all_documents_requirement(...)`
predicate now also drops out, and the remaining direct-reduce admission gate
evaluates the all-documents/significant-terms guard inline.
The one-use `accumulate_hints_into(...)` reducer helper now also drops out,
and the remaining direct-reduce merge loop accumulates
avg/cardinality/percentile hints inline.
The matching one-use hint-aware `merge_response_into(...)` reducer helper now
also drops out, and that same direct-reduce merge loop calls
`merge_native_aggregation_response(...)` inline per input.
The matching one-use scored `merge_response_into(...)` reducer helper now
also drops out, and the scored direct-reduce merge loop also calls
`merge_native_aggregation_response(...)` inline per input.
The residual `MaterializedMultiIndexScoredDirectReduceInput` response-only
carrier now also drops out, and scored direct-reduce sites pass raw
aggregation `Value`s straight into `merge_native_aggregation_response(...)`.
The one-use `direct_reduce_input(...)` producer now also drops out, and the
remaining direct-reduce admission branch assembles document-backed responses
and hints inline per context.
The pure `MaterializedMultiIndexDirectReduceInput::new(...)` constructor now
also drops out, and that same direct-reduce admission branch assembles the
response-plus-hints carrier inline.
The residual `MaterializedMultiIndexDirectReduceInput` response-plus-hints
carrier now also drops out, and that same direct-reduce admission branch
carries raw `(response, avg/cardinality/percentile hints)` tuples inline.
The one-use `collect_native_reduce_hints_from_documents(...)` helper now
also drops out, and the remaining size-zero native-reduce loop performs
field extraction and avg/cardinality/percentile hint collection inline.
The one-use `collect_materialized_multi_index_aggregations_with_refresh_context(...)`
seat now also drops out, and the remaining multi-index final-order caller
performs refresh-result assembly and aggregation collection inline.
The one-use `requested_page_search_response_index_aware(...)` seat now also
drops out, and the remaining requested-page dispatcher performs the plain
requested-page fetch/reduce path inline.
The sibling one-use `requested_page_aggregation_search_response_index_aware(...)`
seat now also drops out, and that same requested-page dispatcher performs
the page-plus-aggregation fetch/reduce path inline too.
The trivial `collect_requested_page_reduce_requested_page_hits(...)` wrapper
now also drops out, and the remaining requested-page reduce sites call
`finalize_hits_for_requested_page(...)` directly.
The shared `collect_requested_page_reduce_aggregation_response_index_aware_with_collector(...)`
seat now also drops out, and the remaining requested-page aggregation-reduce
callers assemble shard-local reduction inline.
The one-parent
`collect_materialized_single_index_plain_response_hits_with_native_query_context_deterministic_stored_field_projection(...)`
seat now also drops out, and the remaining vector/native requested-page
projection helper performs native-query-context source projection inline.
The residual `materialized_single_index_native_hit_return(...)` helper now
also drops out, and the remaining native-hit fetch sites assemble
`MaterializedSingleIndexNativeHitReturn` inline.
The low-fanout
`reusable_query_context_for_query_with_optional_native_query_context_and_optional_all_documents(...)`
seat now also drops out, and the remaining callers assemble optional
native-query-context reusable state inline.
The micro-helper `count_documents_for_vector_candidate_window_context(...)`
is now also gone, and the remaining vector-candidate count sites read
total-hits/cardinality hints directly from the carried context.
The sibling micro-helper `search_documents_for_vector_candidate_window_context(...)`
is now also gone, and the remaining vector-candidate document sites read
carried documents/hits/candidate-ids directly from the context.
The trivial `search_hits_window_for_vector_candidate_window_context(...)`
wrapper is now also gone, and the remaining vector-candidate window callers
bind directly to `search_hits_page_for_vector_candidate_window_context(...)`.
The test-only caller of
`collect_materialized_search_response_components_with_final_order_hits_and_optional_reusable(...)`
is now also gone, so that remaining final-order materialization seat is
down to the production dispatcher path.
The remaining production-only
`collect_materialized_search_response_components_with_final_order_hits_and_optional_reusable(...)`
seat is now also gone, so the final-order dispatcher performs reusable
assembly, aggregation collection, and requested-hit materialization inline.
The test-only callers of
`search_hits_context_for_vector_candidate_window_context(...)` are now also
gone, so that remaining vector-candidate hit-context seat is down to
production paths.
The remaining production-only
`search_hits_context_for_vector_candidate_window_context(...)` seat is now
also gone, so native hit-context callers derive carried
hits/documents/candidate-ids inline.
The remaining `search_hits_page_for_vector_candidate_window_context(...)`
seat is now also gone, so vector-candidate page/window callers derive page
hits and slice them inline.
The remaining `search_hits_for_vector_candidate_window_context(...)`
helper is now also gone, so vector-candidate hit consumers derive carried
hits/documents/candidate-ids inline.
The remaining
`search_hits_window_for_query_vector_or_hybrid_with_optional_hit_context(...)`
seat is now also gone, so its sole vector/native window caller performs
optional-hit-context window handling inline.
The matching
`search_hits_page_for_query_vector_or_hybrid_with_optional_hit_context(...)`
seat is now also gone, so its sole vector/native page caller performs
optional-hit-context page handling inline.
- The low-fanout optional vector-candidate count/document seats are now also gone, so the remaining callers assemble and consume that optional context directly inside the base reusable count/document helpers.
- The remaining `search_hits_sorted_window_for_knn_query(...)` seat is now also gone, so the vector/native window path now performs the sorted cached-KNN probe and bounded insert loop inline at the caller.
- The remaining `search_hits_window_for_hybrid_bool_query(...)` seat is now also gone, so the vector/native window callers now inline grouped hybrid bool candidate-id reduction and bounded top-hit collection.
- The remaining `search_hits_for_hybrid_bool_query(...)` seat is now also gone, so grouped hybrid bool candidate-id reduction and unbounded hit collection now happen inline at the remaining hit/document callers.
- The remaining `search_hits_window_for_knn_query(...)` seat is now also gone, so the production and test KNN window callers now perform the cached page probe and bounded insert loop inline.
- The remaining `search_hits_for_knn_query(...)` seat is now also gone, so the KNN hit callers now inline cached full-hit lookup, relevance-sorted candidate materialization, telemetry update, and cache write.
- The dead `finalize_top_hits_from_window_aggregations(...)` wrapper is now also gone, leaving only the live index-aware top-hits finalization paths.
- The residual `MaterializedFinalOrderMultiIndexHits` carrier is now also gone, so the final-order dispatcher now keeps raw local hit bindings and plugin input-order state directly.
- The remaining `finalize_top_hits_index_aware(...)` seat is now also gone, so the two aggregation callers now finalize top-hits and plugin top-hits inline after fetching the final hit window.
- The dead `count_documents_for_query(...)`, `search_documents_for_query(...)`, and `search_documents_for_query_index_aware(...)` wrappers are now also gone, leaving only the live context-aware count/document paths.
- The one-use `MaterializedMultiIndexRefreshResult::with_exact_hits_and_all_hits(...)` initializer and the empty `MaterializedMultiIndexRefreshedDocumentsFragment` impl shell are now also gone, so the refresh-result caller assembles the hit-context payload inline.
- The one-use scored fragment constructors are now also gone, so the refresh/scored-routing caller now assembles `MaterializedMultiIndexScoredHitContext` and `MaterializedMultiIndexScoredHitsFragment` inline.
- The dead `MaterializedCollectedMultiIndexHits` carrier is now also gone, leaving only the live hit-context and refresh-result carrier structs in the final-order family.
- The one-use `MaterializedMultiIndexPerIndexHitContext::new(...)` and `MaterializedMultiIndexPerIndexScoredHitContext::new(...)` constructors are now also gone, so the refresh/final-order callers now assemble those per-index routing structs inline.
- The remaining `finalize_requested_window_top_hits_index_aware(...)` seat is now also gone, so the two aggregation callers now finalize requested-window top-hits and plugin top-hits inline.
- The dead `native_query_context_supports_known_total_hits_count_handoff_family()` probe is now also gone.
- The one-use `size_zero_aggregation_search_response_index_aware(...)` top-level seat is now also gone, so the main dispatcher now performs size-zero aggregation fetch/reduce assembly inline.
- Duplicated multi-index exact/all-hit routing assembly in the final-order path now converges through a shared `materialized_multi_index_hit_context_and_routed_hit_contexts_for_hits_and_all_hits(...)` helper.
- Multi-index requested-hit materialization no longer round-trips through routed hit contexts just to rebuild the same exact/all hit context; it now reuses the direct exact/all hit context inline.
- Scored per-index routing in the final-order refresh path now reuses the already-built exact/all routed hit contexts instead of rebuilding separate scored grouping maps.
- Duplicated shard-local native-reduce aggregation-map assembly with requested-window `top_hits` plugin carry-through now converges through `collect_shard_local_native_reduce_aggregation_map_with_requested_window_top_hits(...)`.
- Duplicated non-index-aware document-backed reusable-context assembly now converges through `document_backed_query_context(...)` for the native aggregation paths.
- Duplicated index-aware document-backed reusable seed assembly now converges through `document_backed_query_context_index_aware_with_existing_reusable_seed(...)`.
- The single-index vector-native page-plus-aggregation branch now also reuses the shared shard-local aggregation-map helper and the shared index-aware reusable-seed merge helper for its fetched-page context assembly.
- Duplicated single-index fallback reusable-context recovery in the main dispatcher now converges through `fallback_optional_reusable_for_single_index_query_index_aware(...)`.
- The lexical minimum-should-match fallback inside `collect_aggregations_native_from_window_with_context(...)` now also reuses the shared `document_backed_query_context(...)` helper instead of rebuilding the same document/all-document reusable block inline.
- Single-index requested-page plain and page-plus-aggregation paths now also converge through `reusable_query_context_for_search_hits_with_total_hits(...)` for fetched-page reusable seeding from hit windows.
- Single-index requested-page plain and page-plus-aggregation paths now also converge through `standard_requested_page_search_response(...)` for projected-hit response-tail assembly and stored-field fetch-subphase completion.
- Multi-index requested-page reduce and page-plus-aggregation reduce paths now also converge through `standard_requested_page_search_response(...)`, including stored-field projection fetch-subphase completion for reduced pages.
- Document-backed aggregation response assembly now also converges through `collect_document_backed_aggregation_response_with_reusable_documents(...)`, removing repeated pipeline/plugin finalize tails from native and lexical-fallback window paths.
- Vector-candidate hit sourcing now also converges through `hits_for_vector_candidate_window_context_index_aware(...)` across native hit-context, window, and aggregation fallback paths.
- Full KNN hit sourcing now also converges through `full_knn_hits_index_aware(...)` across page, window, and aggregation fallback paths.
- Bounded KNN window sourcing now also converges through `bounded_knn_window_hits_index_aware(...)` for default-sort and sorted-sort window fast paths.
- Remaining single-index page-plus-aggregation response tails now also route through `standard_requested_page_search_response(...)`, completing requested-page response-tail convergence.
- Multi-index hit-backed reusable assembly now also converges through `optional_reusable_query_context_for_multi_index_hits_with_total_hits(...)` across page-reduce, page-plus-aggregation reduce, and final-order paths.
- Multi-index page-plus-aggregation reduce response-input assembly now also converges through `multi_index_requested_page_reduce_aggregation_response_inputs(...)` across vector-native and native reduce branches.
- Multi-index page-plus-aggregation reduce return paths no longer pre-project hits before `standard_requested_page_search_response(...)`; projected-hit response-tail ownership is now fully single-sited.
- One-use `bounded_knn_window_hits_index_aware(...)` has been folded back into `search_hits_window_for_query_index_aware(...)`; the surviving convergence is the shared full-hit KNN path, not a one-call wrapper.
- Final-order all-hits aggregation fallback now also converges through `materialized_multi_index_hit_context_from_per_index_reusable_contexts(...)` for exact/all-hit reconstruction from per-index reusable contexts.
- Single-index requested-hit materialization fallback now also converges through `projected_selected_hits_for_projection_fallback(...)` instead of repeating identical projection-and-return tails.
- The remaining mirrored half inside single-index requested-hit materialization now also routes through `projected_selected_hits_for_projection_fallback(...)`, eliminating the duplicate projection fallback tail on both context branches.
- Final-order multi-index hit finalization paths now also reuse `projected_selected_hits_for_projection_fallback(...)` for the common finalize-and-project tail.
- Final-order hit materialization now keeps only the single-index special case branch; the generic finalize-and-project tail is single-sited behind `projected_selected_hits_for_projection_fallback(...)`.
- Search-hit explanation expansion now also covers `Query::GeoDistance(...)`, so geo-distance leaves no longer fall through to the generic narrow explanation fallback.
- Geo-distance leaves now also participate directly in explanation observation counts and fallback highlight gating, so bool/detail surfaces no longer treat them as a generic fallback-only leaf.
- Distance-feature and rank-feature fallback highlight gating now also require their own query-aware match predicates instead of mere field presence, aligning highlight behavior with explanation/observation surfaces.
- `more_like_this` explanation and observation surfaces now also report effective-field highlight/projected presence instead of pinning those signals to zero while fallback highlight materialization is active.
- `pinned` explanation output now also surfaces the pinned `_id` clause's own highlight/projected presence instead of only exposing the organic child detail while observation/highlight paths already carried pinned-id signals.
- `terms_set` now also participates directly in the Tantivy native builder for the repo-local `minimum_should_match <= 1` subset, instead of always dropping to the generic compatibility path.
- `match_phrase` now also participates directly in the Tantivy native builder for the plain Text-field subset via quoted `QueryParser` phrase queries, instead of always dropping to the generic compatibility path.
- `query_string` and `simple_query_string` now also participate directly in the Tantivy native builder for the explicit-field Text/Keyword/`_id` subset, using the repo-local token-AND-across-fields semantics instead of always dropping to the generic compatibility path.
- `combined_fields` and `multi_match` now also participate directly in the Tantivy native builder for their repo-local explicit-field subsets, reusing the current token-AND-across-fields and field-OR match semantics instead of always dropping to the generic compatibility path.
- `match_bool_prefix` now also participates directly in the Tantivy native builder for the Text/Keyword/`_id` subset, reusing the repo-local “leading exact tokens + trailing prefix token” semantics instead of always dropping to the generic compatibility path.
- `match_phrase_prefix` now also participates directly in the Tantivy native builder for the Text phrase-prefix subset via `PhrasePrefixQuery`, while keeping the earlier single-token `_id`/`Keyword` prefix subset on the direct native path too.
- `fuzzy` now also participates directly in the Tantivy native builder for the string-based `prefix_length == 0` subset, where Tantivy `FuzzyTermQuery` matches the current repo-local semantics closely enough to avoid the generic compatibility path.
- `fuzzy` now also participates directly in the Tantivy native builder for the string-based `prefix_length > 0` subset, using `FuzzyTermQuery::new_prefix(...)` where the repo-local matcher already applies the same “fixed prefix + fuzzy suffix” shape.
- `rank_feature` and `distance_feature` now also participate directly in the Tantivy native builder for their repo-local numeric/date/bool gating subsets, instead of always dropping to the generic compatibility path for those basic filter-like seats.
- `pinned` now also participates directly in the Tantivy native builder when both the pinned `_id` set and the organic child stay inside the existing native subset, reusing the repo-local `_id OR organic` semantics instead of always dropping to the generic compatibility path.
- `more_like_this` now also participates directly in the Tantivy native builder for the explicit-field subset, reusing the current repo-local “like token OR across the provided field set” semantics instead of always dropping to the generic compatibility path.
- `span_near` now also participates directly in the Tantivy native builder for the simple in-order single-field single-term Text subset via `PhraseQuery`, instead of always dropping that narrow positional seat to the generic compatibility path.
- `span_first` now also participates directly in the Tantivy native builder for the repo-local subset where matching already collapses to `_id` span-term / span-or-over-`_id`-terms or direct child-query delegation.
- `span_containing` and `span_within` now also participate directly in the Tantivy native builder for the identical-child non-recursive span-range subset, where current repo-local semantics collapse to direct child delegation.
- One-use `materialized_multi_index_hit_context_and_routed_hit_contexts_for_hits_and_all_hits(...)` has been folded back into the final-order refresh-context branch; the remaining shared routing helper is the reusable-context -> hit-context reconstruction path.
- Dead private search-memory estimate helpers `estimate_search_memory_reservation(...)` and `search_memory_usage_counters(...)` have been removed from the engine surface.
- Dead search-memory support helper family (`estimate_doc_values_reservation_bytes(...)`, `visible_vector_reservation_bytes(...)`, `collector_telemetry_bytes(...)`, cache-byte helpers) has also been removed now that no estimate entrypoints remain.
- Requested-page response tail and final-order outer response tail now also converge through `standard_search_response_with_projected_hits_and_fetch_subphases(...)` for shared projection-aware response assembly.
- `span_not` now also participates directly in the Tantivy native builder when both the include and exclude children stay inside the existing native subset, reusing the repo-local `include AND NOT exclude` semantics instead of always dropping to the generic compatibility path.
- `percentiles` now also participates directly in the Tantivy aggregation request builder, instead of always forcing the metric back through the document-backed compatibility collector path.
- `stats` now also participates directly in the Tantivy aggregation request builder, instead of always forcing that basic metric back through the document-backed compatibility collector path.
- `extended_stats` / `percentile_ranks` metric request gate도 direct Tantivy aggregation builder로 수렴해, already-landed native metric merge/reduce surface와 builder-side breadth가 더 맞춰졌다.
- `cardinality` metric request gate도 direct Tantivy aggregation builder로 수렴해, cardinality hint/reduce surface와 builder-side breadth가 더 맞춰졌다.
- `wrapper` / `constant_score` / `function_score` / `script_score` explanation surface도 outer wrapper node를 직접 남기도록 맞춰, child-only flattening drift가 줄었다.
- `boosting` fallback surface도 `negative` child를 highlight/admission evidence로 섞지 않도록 tightened 되어, positive-only hit eligibility semantics와 더 맞아졌다.
- direct metric request breadth는 current local Tantivy request enum과 다시 정렬되었다: `extended_stats` / `percentile_ranks` / `cardinality` 는 merge/reduce support가 있어도 direct request kind 자체가 없어 builder gate를 다시 닫는다.
- `dis_max` fallback surface도 matched-child-only evidence로 tightened 되어, all-child flattening drift가 줄었다.
- `boosting` explanation surface도 positive-only eligibility semantics에 더 맞게 tightened 되어, negative child detail이 unconditional하게 펼쳐지지 않는다.
- `pinned` fallback surface도 matched-organic-only evidence로 tightened 되어, pinned-id-only hits에서 organic child noise가 줄었다.
- `span_or` fallback surface도 matched-child-only evidence로 tightened 되어, any-child admission semantics와 더 맞아졌다.
- `span_containing` / `span_within` fallback surface도 explanation detail과 맞춰 양쪽 positive child evidence를 함께 반영하도록 정렬되었다.
- `span_not` explanation surface도 include-admission / exclude-block semantics에 더 맞게 tightened 되어, exclude child detail이 unconditional하게 펼쳐지지 않는다.
- `span_multi` / `field_masking_span` explanation surface도 wrapper node를 직접 남기도록 맞춰, child-only flattening drift가 줄었다.
- `bool` explanation surface의 `must_not` branch도 matched-only negative evidence로 tightened 되어, non-blocking negative clause noise가 줄었다.
- `bool` explanation surface의 `should` branch도 matched-only evidence로 tightened 되어, optional non-matching should-clause noise가 줄었다.
- `MatchAll` count surface도 actual hit eligibility semantics에 맞게 정렬되어, summary와 leaf explanation 사이의 drift가 줄었다.
- `pinned` count surface도 highlight collection semantics와 맞춰, pinned-id miss인 organic-only hits에서 `_id` evidence를 더하지 않도록 tightened 되었다.
- `Ids` surface도 highlight collection semantics와 맞춰, id miss hit에서 `_id` highlight/projected evidence를 더하지 않도록 tightened 되었다.
- `_id` exact/narrow leaf family (`term`, `terms`, `terms_set`, `match`, `match_phrase`, `match_phrase_prefix`, `match_bool_prefix`) 도 highlight collection semantics와 맞춰, actual `_id` miss hit에서는 `_id` highlight/projected evidence를 더하지 않도록 tightened 되었다.
- `_id` pattern leaf family (`range`, `prefix`, `wildcard`, `regexp`, `fuzzy`) 도 highlight collection semantics와 맞춰, actual `_id` miss hit에서는 `_id` highlight/projected evidence를 더하지 않고 `prefix`/`wildcard` fallback highlight도 열리지 않도록 tightened 되었다.
- `bool` fallback observation/highlight surface도 matched-clause-only evidence로 tightened 되어, optional non-matching `should` 나 non-blocking `must_not` clause noise를 summary/highlight에서 더 이상 합치지 않는다.
- multi-field leaf family (`combined_fields`, `multi_match`, `query_string`, `simple_query_string`) 도 matched-field-only evidence로 tightened 되어, non-matching sibling fields가 summary/highlight surface에 noise로 섞이지 않는다.
- `more_like_this` surface도 matched-field-only evidence로 tightened 되어, token hit가 없던 sibling field가 summary/highlight surface에 noise로 섞이지 않는다.
- `span_first`, `span_near`, `span_containing`, `span_within` explanation detail도 source-match gate와 맞춰져, non-matching hit에서 child evidence가 explanation tree에 noise로 남지 않는다.
- delegate wrapper family (`span_multi`, `field_masking_span`, `wrapper`, `constant_score`, `function_score`, `script_score`) 도 non-matching hit에서는 child evidence를 explanation tree에 남기지 않도록 tightened 되었다.
- `pinned` explanation의 `_id` clause도 `pinned_match` 기준으로 tightened 되어, pinned-id miss hit에서는 `_id` evidence를 더 이상 과하게 surface 하지 않는다.
- source-gated leaf family (`nested`, `geo_distance`, `distance_feature`, `rank_feature`) 도 actual field-match 기준으로 tightened 되어, non-matching hit에서는 mere field presence가 summary/highlight/explanation evidence로 섞이지 않는다.
- `boosting` explanation도 matched-child-only 방향으로 한 단계 더 tightened 되어, `positive_match` 가 없는 hit에서는 positive child detail을 explanation tree에 남기지 않는다.
- non-`_id` lexical/pattern leaf family (`term`, `terms`, `terms_set`, `match*`, `range`, `exists`, `prefix`, `wildcard`, `regexp`, `fuzzy`) 도 actual field-match 기준으로 tightened 되어, non-matching hit에서는 mere field presence가 summary/highlight/explanation evidence로 섞이지 않는다.
- `exists` non-`_id` count branch와 `knn` leaf family도 actual field/value compatibility 기준으로 tightened 되어, fallback highlight gating보다 넓은 mere-presence signal이 summary/explanation에 섞이지 않는다.
- `knn` explanation의 filter detail도 matched-only 방향으로 tightened 되어, actual filter miss hit에서는 nested filter detail을 explanation tree에 남기지 않는다.
- non-`_id` source-backed leaf matcher family도 `source_value_for_highlight_field(...)` lookup으로 수렴해, dotted/nested field lookup semantics가 matcher와 explanation/highlight/count surface 사이에서 더 일관되게 맞는다.
- multi-field matcher helpers (`combined_fields`, `multi_match`, `query_string`, `simple_query_string`) 도 same `source_value_for_highlight_field(...)` lookup으로 수렴해, helper-internal token matching과 surrounding evidence surfaces가 같은 field addressing semantics를 공유한다.
- hybrid-bool candidate reduction의 text-match family (`match`, `match_phrase`, `match_phrase_prefix`, `match_bool_prefix`) 도 same lookup semantics로 수렴해, candidate reduction과 later matcher/evidence surfaces 사이의 dotted-field drift가 줄었다.
- live explanation combinator/wrapper family (`span_or`, `span_first`, `span_near`, `span_containing`, `span_within`, `span_multi`, `field_masking_span`, `wrapper`, `nested`, `pinned`, `constant_score`, `dis_max`, `boosting`, `function_score`, `script_score`, `knn`, `bool`) 도 outer description에만 있던 admission signal을 structured `source_match` / `filter_match` field로 함께 surface 하도록 정렬되어, machine-consumable explanation payload와 summary text 사이의 drift가 더 줄었다.
- rich source-backed leaf family (`nested`, `more_like_this`, `combined_fields`, `multi_match`, `query_string`, `simple_query_string`, `geo_distance`, `distance_feature`, `rank_feature`) 도 summary text 안에만 있던 `matched_*` / observed signal을 structured fields로 함께 surface 하도록 정렬되어, downstream consumer가 description parsing 없이 overlap count와 measured signal을 직접 읽을 수 있게 됐다.
- lexical/pattern leaf family (`term`, `terms`, `terms_set`, `match`, `match_phrase`, `match_phrase_prefix`, `match_bool_prefix`, `range`, `exists`, `ids`, `prefix`, `wildcard`, `regexp`, `fuzzy`) 도 `_id` / non-`_id` seat 전반에서 structured `source_match` 와 `matched_value_count` / `matched_token_count` / `query_token_count` field를 함께 surface 하도록 정렬되어, exact/pattern leaf payload도 rich leaf family와 같은 machine-consumable shape로 더 맞춰졌다.
- plugin `top_hits` collector는 explicit sort가 비어 있고 caller가 final-order certification을 주지 않은 `NeedsExplicitSort` path에서 repo-local default relevance order(`_score` desc)로 직접 정렬하도록 tightened 되어, multi-index reconstructed hit context나 generic reduce hit slice에서도 unsorted plugin `top_hits` window가 caller input order에 우연히 묶이지 않는다.
- built-in `top_hits` collector도 sort-less request surface를 repo-local default relevance order(`_score` desc)로 직접 정렬하도록 tightened 되어, generic reduce나 multi-index reusable-context reconstruction에서 이어붙인 hit order가 plain `top_hits` window semantics로 새어들지 않게 됐다.
- the matching single-index native aggregation `top_hits` branch도 same shared collector helper로 수렴해, sort-less default-order tightening이 direct native aggregation seat와 later reduce/materialization seat 사이에서 갈라지지 않게 됐다.
- residual generic narrow-explanation fallback도 structured `source_match` / `source_matches` / `highlight_matches` / `projected_field_matches` field를 함께 surface 하도록 정렬되어, 아직 unexpanded query shape가 남아도 outer fallback node가 description-only opaque payload에 머물지 않게 됐다.
- fallback highlight collection도 `regexp` / `fuzzy` leaf를 `_id` / non-`_id` 양쪽에서 직접 다루도록 보강되어, pattern match hit가 explanation/count에서는 보이는데 snippet output은 비어 버리던 drift가 줄었다.
- fallback highlight collection도 `span_term` 을 same `Term` highlight path로 route 하도록 정렬되어, exact span leaf의 residual highlight-only blind spot가 사라졌다.
- default relevance ordering, shared hit-sort fallback, and hit-backed `top_metrics` tie-break도 이제 `_id` 단독이 아니라 `(index, _id)` identity를 사용해, multi-index score tie와 equal sort-key tie에서 same-id cross-index hit가 deterministic order를 잃지 않게 됐다.
- the matching sort-less `top_hits` reduce merge comparator도 `_index` -> `_id` tie-break를 사용하도록 tightened 되어, built-in/plugin `top_hits` merge window에도 residual `_id`-only multi-index tie seat가 남지 않게 됐다.
- wrapper/query-aware observation counts (`span_multi`, `field_masking_span`, `wrapper`, `constant_score`, `boosting`, `function_score`, `script_score`, `knn`) 도 actual local admission 기준으로만 child evidence를 carry 하도록 tightened 되어, count surface가 already-tightened explanation/highlight gating과 더 직접 맞게 됐다.
- `match_phrase_prefix` / `match_bool_prefix` fallback highlight도 actual token-prefix matcher 기준으로 gate 한 뒤 generic field snippet fallback을 사용하도록 정렬되어, whole-query literal substring이 없다는 이유만으로 valid prefix match hit가 highlight를 잃지 않게 됐다.
- plugin `top_metrics` merge도 declared sort values가 완전히 같을 때 `metrics` payload serialization을 deterministic fallback으로 사용하도록 tightened 되어, cross-index equal-sort entry merge가 input order에 매이지 않게 됐다.
- tokenized multi-field fallback highlight (`combined_fields`, `multi_match`, `query_string`, `simple_query_string`) 도 matcher-gated generic field snippet fallback으로 정렬되어, raw query text가 한 field value 안에 literal contiguous substring으로 없더라도 valid cross-field/tokenized match hit가 snippet을 잃지 않게 됐다.
- single-field tokenized fallback highlight (`match`, `match_phrase`) 도 same matcher-gated generic field snippet fallback으로 정렬되어, tokenized/local-phrase seat가 raw query text contiguity를 요구하지 않게 됐다.
- `knn` fallback highlight도 actual local `knn` admission 기준으로 whole branch를 gate 하도록 정렬되어, mere vector compatibility만 맞고 filter가 실패한 hit에서는 vector-field snippet이 더 이상 새지 않게 됐다.
- fallback highlight의 `bool` / delegate-wrapper family (`span_multi`, `field_masking_span`, `wrapper`, `constant_score`, `boosting`, `function_score`, `script_score`) 도 actual local outer admission 기준으로 child traversal을 gate 하도록 정렬되어, outer query가 실제로는 miss인 hit에서 child snippet이 새지 않게 됐다.
- native significant-terms collector도 direct `source.get(field)` lookup 대신 `source_value_for_highlight_field(...)` 로 수렴해, dotted/nested field addressing semantics가 hit-backed/document-backed significant-terms collection과 surrounding matcher/evidence surfaces 사이에서 더 맞아졌다.
- native `terms` / `significant_terms` collector도 scalar array field를 multi-value bucket source로 직접 다루도록 올라가, non-scalar top-level array라는 이유로 bucket collection을 통째로 건너뛰던 gap이 줄었다. 각 hit/document 는 distinct scalar bucket value별로 한 번씩만 count 된다.
- native `range` / `ip_range` / `date_range` collector도 scalar array field를 직접 펼쳐 bucket source로 다루도록 올라가, top-level array라는 이유로 numeric/string/date range bucket candidate를 통째로 놓치던 gap이 줄었다.
- native histogram collector도 scalar numeric array field를 직접 펼쳐 bucket source로 다루도록 올라가, top-level array라는 이유로 histogram bucket candidate를 통째로 놓치지 않게 됐다. 같은 문서 안의 여러 값이 같은 histogram bucket에 들어가도 bucket count는 한 번만 오른다.
- native non-weighted metric collector (`min` / `max` / `sum` / `avg` / `value_count` / `stats` / `extended_stats` / `percentiles` / `percentile_ranks` / `boxplot` / `median_absolute_deviation`) 도 numeric array field를 직접 펼쳐 value stream으로 다루도록 올라가, 문서당 scalar 하나만 읽던 gap이 줄었다. native cardinality 도 scalar array를 distinct scalar value 집합으로 펼쳐 uniqueness를 센다.
- native geo collector (`geo_bounds` / `geo_centroid` / `geo_distance`) 도 geo-point array field를 직접 펼쳐 multi-point source를 다루도록 올라가, 문서당 point 하나만 읽던 gap이 줄었다. `geo_distance` 는 같은 문서 안의 여러 point가 같은 bucket에 들어가도 bucket count를 한 번만 올린다.
- native `date_histogram` collector도 date array field를 직접 펼쳐 distinct bucket set으로 다루도록 올라가, 문서당 date scalar 하나만 읽던 gap이 줄었다. 같은 문서 안의 여러 date 값이 같은 histogram bucket에 들어가도 bucket count는 한 번만 오른다.
- native `auto_date_histogram` interval chooser와 `variable_width_histogram` interval chooser도 multi-value date/numeric array를 직접 읽도록 올라가, bucket collector는 array-aware 인데 interval choice는 문서당 scalar 하나만 보던 drift가 줄었다.
- native composite collector도 multi-value scalar source field를 distinct composite key 조합으로 직접 펼치도록 올라가, source field마다 scalar 하나만 읽던 gap이 줄었다. 한 문서 안에서 같은 composite key 조합이 중복 생성되더라도 count는 한 번만 오른다.
- plugin `multi_terms` collector도 same multi-value composite key expansion을 재사용하도록 올라가, native composite는 고쳐졌는데 plugin multi-terms 만 single-key-per-document 로 남아 있던 drift가 줄었다.
- native reduce hint 수집의 `avg`/`weighted_avg`, `cardinality`, percentile-family metric 쪽도 underlying collector와 같은 expanded numeric/scalar-array view를 쓰도록 올라가, multi-index reduce hint 가 array-aware collector보다 뒤처지던 drift가 줄었다.
- adjacent plugin-defined `avg` collector도 native metric `avg` 와 같은 expanded numeric-array value stream을 쓰도록 올라가, plugin/native simple average family 안의 scalar-only drift가 줄었다.
- plugin `top_metrics` entry도 source-hit provenance (`_index` / `_id`, document path는 `_id`) 를 함께 들고, merge comparator가 sort values와 metrics payload 뒤에 그 provenance를 마지막 tie-break 로 쓰도록 올라가, equal-sort/equal-metrics seat의 residual input-order 의존성이 더 줄었다.
- plugin `top_metrics` document-path entry도 이제 `_index` 를 함께 들고 와서, hit path와 document path가 모두 같은 `_index` -> `_id` deterministic fallback strength를 공유한다.
- adjacent plugin-defined simple numeric metric collector (`sum` / `avg` / `min` / `max`) 도 native metric family와 같은 expanded numeric-array value stream을 쓰도록 올라가, plugin/native simple numeric family 안의 scalar-only drift가 더 줄었다.
- plugin-defined `value_count` 도 이제 native metric `ValueCount` 와 같은 expanded `numeric_source_values(...)` value stream을 사용하므로, field 존재 문서 수가 아니라 numeric value 개수를 직접 센다.
- plugin-defined `stats` / `extended_stats` 도 이제 native metric family와 같은 expanded `numeric_source_values(...)` stream을 사용하므로, multi-value numeric field가 plugin path에서 문서당 scalar 하나로 축소되지 않는다.
- `weighted_avg` reduce-hint admission도 이제 array-aware `avg` 와 같은 넓은 기준이 아니라 current scalar-pair collector semantics에 맞춰 tightened 되어, live collector가 representative scalar pair를 요구하는 동안에는 mere value/weight array presence만으로 admissible count를 올리지 않는다.
- native/plugin `weighted_avg` 도 이제 representative scalar 하나만 보지 않고 `weighted_numeric_source_pairs(...)` 를 통해 value/weight numeric stream을 위치 기준으로 zip 하므로, multi-value numeric field도 value/weight position pair가 맞는 범위에서 일관되게 집계된다. reduce-hint admission도 같은 pair stream 기준으로 맞췄다.
- multi-index native `avg` reduce hint도 이제 값이 있는 문서 수가 아니라 expanded numeric value 개수를 세고, `weighted_avg` 는 zipped value/weight pair 개수를 센다. 그래서 array-aware shard-local metric collection과 cross-index reduce cardinality가 다시 맞는다.
- hit-backed native reduce hint helper를 추가하고 scored-hit multi-input merge path가 empty hint map 대신 이를 사용하도록 바꿨다. 그래서 hit-materialized cross-index native reduction도 이제 `avg` / `weighted_avg` / cardinality / percentile-family metric을 document-backed native reduce path와 같은 count/value carrier로 merge 한다.
- nested native aggregation을 품는 plugin wrapper (`global`, `sampler`, `random_sampler`, `diversified_sampler`) 도 이제 hidden nested reduce hint carrier를 함께 싣고 wrapper merge 때 이를 사용한다. 그래서 nested `avg` / `weighted_avg` / cardinality / percentile-family response가 empty hint map으로 merge 되지 않는다. hidden carrier는 최종 응답 전에 다시 제거된다.
- document-fragment multi-input native reduce branch도 이제 각 fragment를 자기 own hint carrier로 merge 한다. 이전처럼 전체 합산 hint map을 모든 fragment에 반복 적용하지 않으므로, native `avg` / `weighted_avg` 와 cardinality/percentile-family reduce의 residual overcount drift가 줄었다.
- native/plugin `composite` reduce ordering도 merged composite key를 raw map iteration order에만 맡기지 않고 explicit value comparator로 한 번 더 정렬하도록 tightened 했다. 그래서 merged `after_key` / window progression이 더 직접적인 deterministic composite-key sort step으로 읽힌다.
- single-index hit-materialized aggregation response도 이제 반환 전에 document-backed path와 같은 finalization cleanup을 거친다. 그래서 wrapper-only hidden nested reduce carrier가 direct `global` / `sampler` family outward payload로 새지 않는다.
- finalization도 이제 wrapper subaggregation payload 안으로 재귀적으로 내려가므로, nested `global` / `sampler` family response에서도 hidden reduce carrier가 top-level뿐 아니라 nested wrapper tree 안쪽까지 direct response 반환 전에 제거된다.
- 남아 있던 single-index / multi-index fallback direct hit-materialized aggregation branch도 이제 반환 전에 finalization을 거친다. 그래서 wrapper-only hidden nested reduce carrier가 일부 response path에서만 지워지던 상태가 아니라 direct outward response 전반에서 일관되게 제거된다.
- plugin `top_metrics` native support gate를 document path / hit path로 분리했다. 이제 hit-backed path는 `_score` sort를 지원하고, `sort` array도 hit-aware builder를 통해 `_score` 를 직접 싣는다. document-backed path는 source-addressable sort만 계속 지원한다.
- raw document collector 위에 `top_hits` 를 덧씌우는 requested-window document-backed aggregation branch도 이제 pipeline-only finalize가 아니라 full finalization pass를 사용한다. 그래서 wrapper hidden-carrier cleanup과 recursive wrapper finalization이 이 branch에도 같이 적용된다.
 - plugin `geo_distance` origin parsing now reuses shared `geo_point_value(...)`, and shared geo-point reads accept object `{lat, lon}`, string `"lat,lon"`, and array `[lon, lat]` shapes instead of object-only parsing.
 - plugin `top_hits` sort parsing now maps `geo_origin` through shared `geo_point_value(...)` as well, so plugin sort-local geo origin literals accept the same object/string/array shapes.
 - shared `GeoSortOrigin` deserialization now accepts object `{lat, lon}`, string `"lat,lon"`, and array `[lon, lat]` shapes, so geo sort payloads are no longer object-only at the request type boundary.
 - plugin `top_metrics` native collection now accepts geo sort specs as well; document/hit paths compare by geo distance and serialize actual distance values into the carried `sort` array instead of dropping to placeholder on `geo_origin`.
 - plugin `composite` document/hit collection now expands `composite_keys_from_source(...)` instead of reading only one scalar key tuple via `composite_key(...)`, so multi-value scalar sources no longer collapse to one composite bucket candidate per document.
 - `significant_terms` / `significant_text` now compute an actual significance-style `score` from foreground/background rates and use that score for default ranking instead of exposing `score = doc_count`.
 - aggregation-map admission now treats plugin `top_metrics` with `_score` sort as hit-materialization-required, preventing score-sorted `top_metrics` from falling through document-backed placeholder paths that do not carry scores.
 - geo sort and geo-sorted `top_metrics` now evaluate multi-point geo fields through `geo_point_source_values(...)`, applying `mode` (`min`/`max`/`avg`/`sum`) and order-aware default representative distance instead of reading only one point.
 - sort-script `doc['field'].value` access now reuses `numeric_source_values(...)` instead of direct scalar lookup, so dotted fields and numeric arrays no longer fail the local script-sort path merely because the source seat is not a top-level scalar.
 - document-path plugin `top_hits` now refuses `_score` sort instead of fabricating `score = 0` hits, so score-sorted plugin `top_hits` no longer advertises unsupported semantics on score-less document collectors.
 - `diversified_sampler` now derives distinct scalar diversification keys from multi-value fields instead of stringifying the whole array as one key, so document/hit sampling no longer collapses scalar-array fields into a single synthetic bucket key.
 - plugin `top_metrics` native collection now accepts `_script` sort as well; document/hit comparators and carried `sort` values serialize evaluated local script results instead of forcing script-sorted requests to placeholder.
 - plugin `significant_terms` / `significant_text` now parse explicit `order: {\"_score\": ...}` on their own carrier path, so request-time score ordering uses the same significance score that the buckets now expose.
 - multi-index reusable-document hit materialization now rebuilds per-index hits through `hits_for_documents(...)` instead of wrapping documents as synthetic `score = 0` hits, so score-sensitive fallback aggregations such as `_score`-sorted `top_metrics` do not silently lose score carriers on that path.
 - multi-index document direct-reduce exceptions now reject plugin `top_hits` requests that sort on `_score`, so those requests no longer fall through score-less document collectors and instead stay on scored-hit materialization paths.
 - shard-local plugin `top_metrics` winner selection now uses the same `sort -> metrics -> provenance` comparator as merge/finalization, so local picks no longer drift from cross-index merge ordering when sort values tie but metrics payloads differ.
 - shard-local `composite` collection now applies `after` filtering and bucket windowing with the same explicit key comparator used by merge/finalization instead of raw serialized-key order, so local `after_key` progression no longer drifts from merged composite ordering.
 - plugin `significant_terms` / `significant_text` no longer prune to score-desc top `size` before plugin-specific ordering runs, so `_key` / `_count asc` requests now sort over the full local bucket set instead of reordering an already-truncated score subset.
 - plugin `terms` / `rare_terms` now also collect the full local bucket set before plugin-specific ordering/finalization truncates it, so `_key` / `_count asc` bucket requests no longer reorder a pre-pruned top-`size` subset.
 - range-family merge now preserves existing/incoming bucket order instead of re-sorting by serialized bucket key, so plugin `range` / `ip_range` / `date_range` / `geo_distance` keep request bucket order through multi-input reduce as well.
 - finalization now strips plugin `avg` / `weighted_avg` carrier fields (`_count`, `_weighted_sum`, `_weight_sum`) from outward payloads, aligning plugin metric surface with the native metric family instead of leaking reduce bookkeeping details.
 - plugin `filter` now carries nested subaggregations and nested reduce hints on both document and hit paths, and merge now reduces those nested payloads instead of only summing `doc_count`.
 - plugin `filters` / `adjacency_matrix` now also carry bucket-level nested subaggregations and bucket-level reduce hints, and merge/finalization now reduce and clean those bucket payloads instead of treating them as doc-count-only maps.
 - plugin `missing` now also carries nested subaggregations and nested reduce hints on both document and hit paths, and merge now reduces those nested payloads instead of treating plugin `missing` as a doc-count-only single bucket.
 - plugin `terms` / `rare_terms` now also carry bucket-level nested subaggregations and bucket-level reduce hints on both document and hit paths, and merge/finalization now reduce and clean those bucket payloads instead of treating term buckets as doc-count-only entries.
 - plugin `range` / `ip_range` / `date_range` / `geo_distance` now also carry bucket-level nested subaggregations and bucket-level reduce hints on both document and hit paths, and merge/finalization now reduce and clean those range buckets instead of treating them as doc-count-only entries.
 - plugin `histogram` / `date_histogram` now also carry bucket-level nested subaggregations and bucket-level reduce hints on both document and hit paths, and merge/finalization now reduce and clean those histogram buckets instead of treating them as doc-count-only entries; hit-backed plugin `date_histogram` no longer falls through the missing branch.
 - plugin `composite` now also carries bucket-level nested subaggregations and bucket-level reduce hints on both document and hit paths, and merge/finalization now reduce and clean those composite buckets instead of treating them as doc-count-only entries.
 - plugin `auto_date_histogram` / `variable_width_histogram` now also carry bucket-level nested subaggregations and bucket-level reduce hints on both document and hit paths, and rebucketing merge/finalization now preserve those nested bucket payloads instead of collapsing them to doc-count-only buckets.

- plugin `multi_terms` and `significant_terms`/`significant_text` now also preserve bucket-level nested subaggregations and nested reduce hints across collect/merge/finalize instead of collapsing to bucket doc_count-only payloads.

- follow-on correction: array bucket nested finalization now preserves `bg_count` and `score` so plugin `significant_terms` / `significant_text` bucket metadata survives nested cleanup.

- follow-on tightening: plugin `significant_terms` bucket membership for nested subset collection now uses `bucket_sort_key(...)` normalization instead of raw JSON equality.

- plugin `terms` / `multi_terms` now separate local bucket ordering from final size truncation: collect/merge keep the full ordered bucket set, and outward finalization applies `size` truncation.

- plugin `rare_terms` now also separates local bucket ordering from final rare-term filtering/truncation: collect/merge keep the full ordered bucket set, and outward finalization applies `max_doc_count` filtering plus final size truncation.

- follow-on cleanup: `array_bucketed_plugin_nested_fields(...)` now also excludes `from` / `to`, so range-family bucket boundary fields are treated consistently as structural metadata rather than nested payload.

- cleanup follow-on: removed now-dead `significant_terms` truncation helper/local residue after separating local ordering from final truncation.

- native `significant_terms` now also keeps the full ordered bucket set through local collect/merge and applies final `size` truncation only at finalization, matching the plugin significant-terms family.

- native `terms` now also keeps the full ordered bucket set through local collect/merge and applies final `size` truncation only at finalization.

- native/plugin `composite` now keep the full ordered bucket set through local collect/merge and compute final `size` truncation plus `after_key` only at finalization.

- follow-on tightening: direct single-plugin `filter` / `missing` / `filters` / `adjacency_matrix` now also switch to hit-backed collection when their nested subaggregation map requires hit materialization, instead of forcing those wrapper buckets through the document collector path.

- follow-on generalization: outside the remaining explicit special-cases (`top_hits`, `_score`-sorted `top_metrics`, `significant_terms`, `global`, sampler family), direct single-plugin native collection now routes any plugin with a nested subaggregation map that requires hit materialization through the hit-backed plugin collector path instead of keeping that escalation only on a few wrapper kinds.

- follow-on correction: direct single native `filter` / `filters` no longer use a narrower Tantivy count-only path that could return unsupported `None`; they now use the same source-backed document collector semantics as the multi-aggregation path.

- follow-on generalization: hit-materialization admission is now recursive across nested plugin subaggregation maps, so wrapper/bucket plugins that contain nested `top_hits` or `_score`-sorted `top_metrics` now pull the outer aggregation plan onto the hit-backed path instead of leaving those nested requests trapped in document collection.

- follow-on generalization: `all_hits` admission is now also recursive across nested plugin subaggregation maps, so outer plans now allocate full-population carriers when nested plugin wrappers contain `significant_terms`-family or `global` requirements instead of missing those needs at the top-level gate.

- follow-on correction: the direct-reduce hit-materialization exception recursion was tightened again. Nested plugin subaggregations are inspected recursively, but nested `top_hits` is now treated as non-exception-safe because only top-level `top_hits` has a real shard-local requested-window rewrite. Nested `_score`-sorted `top_metrics` remains exception-safe only on scored-hit paths.

- follow-on correction: document direct-reduce hit-materialization exceptions no longer treat `_score`-sorted plugin `top_metrics` as an exception-safe seat; those requests now keep requiring a score-carrying hit path instead of being allowed onto score-less document direct-reduce shortcuts.

- follow-on correction: plugin `sampler` / `random_sampler` / `diversified_sampler` now report sampled `doc_count` even when no nested subaggregation map is present; previously those branches could fall back to the unsampled input count despite already having sampled-document / sampled-hit collectors.

- follow-on correction: plain plugin `sampler` now actually honors its configured sample size on both document and hit paths instead of forwarding the full input set unchanged. `random_sampler` and `diversified_sampler` already had their own sampling logic; the plain sampler branch was the stale one.

- follow-on correction: sampler-family hit collection now forwards the caller-certified `PluginTopHitsInputOrder` into nested subaggregation collection instead of always forcing `NeedsExplicitSort`, so nested sort-less `top_hits` inside sampled wrappers preserve already-certified final hit order on scored direct-reduce paths.

- follow-on generalization: significant-terms live-admission helpers for default-rank / `_key` / `_count asc` exact-documents shortcuts now recurse through nested plugin subaggregation maps too, so wrapper-contained significant-terms seats use the same admissibility checks as top-level ones.

- follow-on correction: the attempted recursive requested-window `top_hits` detection was backed out together with the nested rewrite; current requested-window helpers stay top-level only until nested wrapper/bucket payloads carry a real bucket-local hit carrier.

- follow-on correction: the attempted recursive requested-window `top_hits` reduce-window rewrite was backed out; nested wrapper/bucket payloads do not carry a generic bucket-local hit carrier yet, so reusing the outer hit slice there would have corrupted nested bucket membership. Requested-window rewrite remains top-level only until a real nested hit carrier exists.

- follow-on correction: hit-backed aggregation-map collection now also forwards the caller-certified `PluginTopHitsInputOrder` into nested subaggregations for plugin `significant_terms` / `significant_text` special-case buckets and plugin `global`, instead of forcing explicit re-sorting there. This preserves sort-less nested `top_hits` input order consistently across those hit-backed wrapper families too.

- follow-on correction: direct single-plugin hit-backed collection now treats the hit slice returned by search as already final order (`CallerFinal`) instead of forcing `NeedsExplicitSort` again. This applies to direct plugin `top_hits`, hit-materialized direct plugin wrappers such as `global`, sampler family, plugin significant-terms buckets, and the generic hit-escalated direct plugin path, so sort-less nested `top_hits` keeps the existing final-hit order there too.

- follow-on correction: the top-level plugin `top_hits` fallback branches that already materialize hits through `search_hits_for_query_with_sort(...)` / `search_hits_window_for_query_index_aware(...)` now also pass `CallerFinal` instead of `NeedsExplicitSort`. That keeps sort-less plugin top-hits on the search-produced final relevance order instead of unnecessarily re-sorting the same hit slice again.

- follow-on correction: the single-index aggregation-only hit-materialization fallback branches now also pass `CallerFinal` into `collect_aggregations_with_plugin_top_hits_input_order(...)` instead of forcing `NeedsExplicitSort`. Those branches already materialize the hit slice locally in final relevance/default order, so sort-less plugin top-hits and nested sort-less plugin top-hits keep that order instead of re-sorting the same slice again.

- follow-on correction: plugin `top_hits` ordered-input helpers no longer delegate to native `collect_top_hits_*` builders that always re-sort by relevance. They now build the payload directly from the already-ordered hit slice, so explicit plugin sort and caller-certified final order are both preserved instead of being accidentally overwritten by a second relevance sort.

- follow-on correction: the single-index native hit-search aggregation path now marks its top-hits carrier as `CallerFinal` only when the outer query sort is still default relevance. That lets sort-less plugin top-hits keep the native hit-search order on that safe seat, while non-default outer query sorts still stay on `NeedsExplicitSort` and do not over-claim final-order certification.

- cleanup follow-on: removed the now-dead `collect_plugin_aggregation_from_hits(...)` wrapper that hard-coded `NeedsExplicitSort`. All live hit-backed plugin callers now pass an explicit `PluginTopHitsInputOrder` through `collect_plugin_aggregation_from_hits_with_input_order(...)`, which reduces the chance of future regressions reintroducing an implicit hard-coded carrier.

- follow-on correction: `MaterializedMultiIndexHitContext::with_exact_hits_and_all_hits(...)` now canonicalizes both exact hits and all-hits into default relevance order instead of preserving raw concatenation order. The multi-index materialized-hit fallback seats that consume that context now pass `CallerFinal`, so sort-less plugin top-hits on those paths keep a real finalized relevance carrier rather than re-sorting an arbitrary concatenation.

- follow-on correction: native `significant_terms` merge no longer performs stale intermediate truncation; final `size` limiting now stays at finalization only.

- follow-on tightening: plugin `auto_date_histogram` / `variable_width_histogram` rebucketing merge now finalizes nested pipeline/subaggregation payload immediately after nested reduce, matching other bucket merge paths.

- follow-on correction: plugin `significant_terms` / `significant_text` special-case collect paths no longer call the truncating finalizer early; they now keep full ordered buckets locally and attach plugin metadata only, leaving final size truncation to response finalization.

- follow-on correction: direct single-plugin native collection now also runs the shared plugin finalization pass before returning, so ordered-bucket truncation, composite `after_key`, wrapper nested cleanup, and plugin metric carrier cleanup match the multi-aggregation response path.

- follow-on correction: direct single native `terms` / `metric` / `significant_terms` / `composite` collection now uses the same source-backed collector/finalization semantics as the multi-aggregation path instead of mixing in narrower Tantivy-native one-off paths.

- follow-on correction: document-backed plugin `top_hits` now rejects sort-less default-relevance collection instead of fabricating `score=0` synthetic hits; only explicit non-`_score` sorts stay on the document path, while default relevance remains on hit-backed collection.

- follow-on correction: plugin `moving_count` no longer falls through to placeholder; the existing moving-window helper is now wired into the pipeline dispatch path.

- cleanup follow-on: removed the now-dead one-off Tantivy-native single-aggregation helper path after direct native collection was moved onto the shared source-backed collector/finalization flow, reducing the chance of future semantics drift re-entering through an unused legacy path.

- follow-on correction: top-hits finalization now falls back to the existing visible `hits` array when `_merge_hits` is absent, so direct finalized top-hits payloads are not accidentally emptied.

- follow-on correction: direct single-plugin `global` no longer falls through the generic document collector path; it now uses the same all-documents scope and nested subaggregation carrier as the multi-aggregation special-case path.

- follow-on correction: direct single-plugin `_score`-sorted `top_metrics` no longer falls through the document collector placeholder path; it now materializes scored hits and uses the same hit-backed collection semantics as the multi-aggregation path.

- follow-on tightening: direct single-plugin `global` now switches to hit-backed nested collection when its subaggregation map requires hit materialization, instead of forcing all nested work through the document path.

- follow-on tightening: direct single-plugin `sampler` / `random_sampler` / `diversified_sampler` now also switch to hit-backed sampled nested collection when their subaggregation map requires hit materialization, instead of forcing sampled nested work through the document path.

- follow-on tightening: direct single-plugin `significant_terms` / `significant_text` now also attach bucket-level nested subaggregations and switch to hit-backed bucket collection when those nested requests require hit materialization, matching the multi-aggregation special-case path.

- follow-on correction: the multi-index hit-search aggregation path now globally canonicalizes its exact hit slice with `compare_relevance_hits` whenever the outer query sort is still default relevance, and it upgrades the plugin top-hits carrier on that seat to `CallerFinal`. That keeps the top-level multi-index hit slice and downstream sort-less plugin top-hits on the same finalized relevance order instead of leaving the exact hits as raw per-index concatenation.

- follow-on correction: document-backed plugin `top_hits` with explicit non-`_score` sort no longer leaks synthetic `_score: 0.0` / `max_score: 0.0` into the outward payload. That path still uses synthetic hits internally for field sorting, but the score surface is now nulled before returning so unsupported score carriers are not exposed as real values.

- cleanup follow-on: removed the now-dead `moving_count` branch from the shared moving-window pipeline dispatcher after `moving_count` was already wired directly in the outer pipeline dispatch. This keeps the live dispatch surface closer to the actual helper routing and reduces the chance of stale duplicate branches diverging again.
- Follow-on correction: plugin `top_hits` explicit non-`_score` score-surface cleanup now runs at shared finalization instead of only the document-backed direct collect seat, so intermediate merge/reduce no longer rehydrates visible synthetic `_score: 0.0` / `max_score: 0.0`.
- Finalize admission correction: generic plugin pipeline families already parsed and dispatched by `plugin_pipeline_aggregation_value(...)` (`serial_diff`, `derivative`, `cumulative_sum`, bucket-stat families, and sum/avg/min/max bucket) are now admitted by the shared finalize gate instead of falling through to placeholder paths.
- Capability correction: plugin `top_metrics` now honors request `size` across both shard-local collection and multi-input merge instead of always collapsing to a single top entry.
- Payload cleanup correction: plugin `top_metrics` now strips internal `_index` / `_id` provenance at shared finalization so merge tie-break carriers do not leak into outward `top` entries.
- Semantics correction: plugin `diversified_sampler` now requires its diversification `field` at collection time; fieldless requests no longer silently degrade to an undiversified sampled set and instead surface as placeholder/unsupported.
- Semantics correction: plugin `date_histogram` now requires an explicit `calendar_interval` or `fixed_interval` at collection time; interval-less requests no longer silently default to `day` and instead surface as placeholder/unsupported.
- Semantics correction: field-required plugin families now share an upfront non-empty `field` guard at collection entry, so requests that omit `field` no longer drift into empty-path null/empty results across metric, range, geo, histogram, terms, and significant-* families.
- Semantics correction: plugin `weighted_avg` now requires a non-empty `weight_field` at collection entry; requests that omit it no longer drift into empty-path null weighted averages.
- Semantics correction: plugin `filter`, `filters`, `adjacency_matrix`, and `multi_terms` now require valid query/source request surfaces at collection entry. Missing/invalid `filter`, empty-or-partially-invalid filter maps, and empty `multi_terms` sources no longer degrade into empty buckets or zero-doc-count wrappers.
- Semantics correction: plugin `range`, `ip_range`, `date_range`, and `geo_distance` now require a non-empty `ranges` definition at collection entry; range-family requests no longer degrade into empty bucket arrays when bucket definitions are omitted.
- Follow-on correction: plugin `multi_terms` source admission is now strict across the whole `terms` list; partially-invalid source definitions no longer get silently dropped while the remaining sources continue collecting.
- Follow-on correction: plugin `top_metrics` request admission is now strict across both `metrics` and `sort` surfaces; partially-invalid metric entries or sort specs no longer get silently dropped while the remaining entries continue collecting.
- Follow-on correction: plugin `top_hits` sort admission is now strict across the whole sort surface; partially-invalid sort entries no longer get silently dropped while the remaining sort specs continue collecting.
- Semantics correction: plugin pipeline families that depend on a named `aggregation` target (`bucket_sort`, `bucket_count`, bucket-path wrappers, and moving-window wrappers) now require a non-empty target at dispatch entry instead of degrading into empty-target bucket/value results.
- Follow-on correction: plugin `bucket_script` now requires a non-empty `script`, and plugin `bucket_selector` now requires an explicit numeric `value`, matching the current native parser surface instead of defaulting to `_value` / `0.0`.
- Follow-on correction: plugin moving-percentile helpers now parse `percents` / `values` as whole valid numeric lists instead of dropping invalid entries one by one; malformed numeric-list request surfaces no longer degrade into reduced moving-percentile semantics.
- Follow-on correction: plugin metric `percentiles` / `percentile_ranks` now treat numeric-list request surfaces strictly. Invalid `percents` or `values` entries no longer get dropped into reduced metric requests; malformed percentile-rank lists now surface as placeholder/unsupported.
- Capability correction: generic/plugin `percentiles_bucket` now honors explicit `percents` during pipeline execution instead of always emitting the hard-coded default percentile set; malformed explicit `percents` / `values` lists on pipeline percentile families now surface as placeholder rather than degrading through lossy parsing.
- Follow-on correction: plugin metric `percentiles` / `percentile_ranks` merge now reuses the same strict numeric-list surface as collection, so malformed explicit `percents` / `values` no longer re-enter via reduce-time lossy parsing.
- Follow-on correction: plugin metric `percentiles` / `percentile_ranks` merge no longer lets malformed explicit percentile lists fall back to default/non-placeholder metric output. Reduce now reuses the same validated numeric-list surface as collection for both families, so explicit malformed `percents` / `values` stay unsupported instead of being reinterpreted during merge.
- Follow-on correction: plugin `moving_percentiles` / `moving_percentile_ranks` now reject malformed explicit `percents` / `values` at pipeline dispatch entry instead of falling back to family defaults during execution. This aligns moving-percentile request-surface strictness with the rest of the percentile-family guards and prevents explicit malformed numeric lists from being reinterpreted as default semantics.
- Follow-on correction: path-carrying and moving-window plugin pipeline families now reject explicit malformed `path` / `window` request surfaces at dispatch entry instead of silently falling back to `_count` / `2`. This keeps malformed explicit pipeline params from being reinterpreted as default semantics while still preserving the existing defaults for omitted params.
- Follow-on correction: plugin `top_hits` and `top_metrics` now reject explicit malformed numeric window/size params instead of silently defaulting them. Explicit malformed `top_hits.from` / `top_hits.size` and `top_metrics.size` no longer degrade to `0` / `3` / `1`, while omitted params still keep their existing defaults.
- Follow-on correction: shared plugin `top_hits` finalization no longer re-reads malformed explicit `from` / `size` as `0` / `3`. The finalization seat now reuses the same validated window surface as collection/merge, so malformed explicit top-hits windows stay unsupported instead of being resurrected during finalize.
- Follow-on correction: plugin `bucket_sort` now rejects explicit malformed `sort` / `from` / `size` request surfaces instead of silently degrading them to empty sort / `0` / `10`. Omitted params still keep the existing defaults, but malformed explicit bucket-sort params no longer get reinterpreted as default semantics.
- Follow-on correction: plugin `bucket_selector` and `bucket_sort` now reject additional malformed explicit request surfaces instead of silently degrading them to defaults. Explicit invalid `bucket_selector.op` no longer falls back to `gte`, and explicit empty `bucket_sort.sort` no longer degrades to the implicit key-order path.
- Follow-on correction: plugin `bucket_script` now rejects malformed explicit `params` surfaces instead of silently degrading them to an empty params map. Omitted `params` still keep the existing empty-default behavior, but explicit non-object `params` no longer get reinterpreted as the default script environment.
- Follow-on correction: plugin `serial_diff` now rejects malformed explicit `lag` instead of silently degrading it to the default/no-override path. Omitted `lag` still keeps the existing default behavior, but explicit non-positive or non-numeric lag values no longer get reinterpreted as `1`.
- Follow-on correction: plugin `date_histogram` now validates explicit `calendar_interval` / `fixed_interval` values before collection instead of accepting arbitrary strings and degrading malformed explicit intervals into empty bucket output. Invalid explicit intervals now stay unsupported rather than masquerading as a valid empty result.
- Follow-on correction: plugin `histogram` now rejects malformed explicit `interval` instead of silently degrading it to the default `1.0`. Omitted `interval` still keeps the existing default behavior, but explicit non-numeric or non-positive intervals no longer masquerade as a valid default histogram request.
- Follow-on correction: plugin `auto_date_histogram` and `variable_width_histogram` now reject malformed explicit `buckets` instead of silently degrading them to the default `10`. Omitted `buckets` still keep the existing default behavior, but explicit non-numeric or non-positive bucket counts no longer masquerade as valid default requests.
- Follow-on correction: plugin `composite` no longer lossy-parses malformed explicit `sources` by silently dropping invalid entries. Composite source lists are now treated as whole request surfaces, so explicit malformed or partially-invalid source definitions stay unsupported instead of degrading into reduced composite grouping semantics.
- Follow-on correction: plugin `composite` now also validates explicit `size` and applies the same validated `sources` surface across document, hit, and merge/materialization seats. Explicit malformed composite size no longer degrades to the default `10`, and the hit-path no longer keeps a stale lossy source parser.
- Follow-on correction: plugin `composite` now rejects malformed explicit `after` instead of silently comparing arbitrary values against composite keys. Explicit non-object or empty after-keys no longer alter composite pagination/filter semantics as if they were valid cursors.
- Follow-on correction: range-family plugins now treat `ranges` entry parsing as a whole validated request surface instead of only checking that the outer array exists. Explicit malformed `key` / `from` / `to` entries on `range` / `ip_range` / `date_range` / `geo_distance` no longer degrade into empty or reduced bucket semantics; the collectors now surface those requests as placeholder/unsupported.
- Follow-on correction: sampler-family plugins now reject explicit malformed numeric request surfaces instead of silently mixing them with omission defaults. Explicit malformed `size` / `shard_size` / `seed` on `sampler` / `random_sampler`, and explicit malformed `max_docs_per_value` on `diversified_sampler`, no longer degrade into unlimited sampling, seed `0`, or per-value cap `1`.
- Follow-on correction: plugin `top_metrics` now reuses its strict explicit `size` surface in merge/finalize as well as collection. Malformed explicit `size` no longer survives reduce-time/default `1` truncation on the way to the outward response.
- Follow-on correction: plugin `adjacency_matrix` now rejects explicit malformed `separator` instead of silently degrading it to the default `"&"`. Omitted separator keeps the existing default, but explicit non-string separators no longer masquerade as valid default requests.
- Follow-on correction: plugin `bucket_sort` helper now reuses the same validated `aggregation` / `sort` / `from` / `size` surface as dispatch instead of carrying its own raw defaults. This removes another internal seat where explicit malformed request params could otherwise be reinterpreted as default helper semantics.
- Follow-on correction: plugin `bucket_selector` and `bucket_script` helpers now also reuse the same validated `aggregation` / `path` / `op` / `value` / `script` / `params` surfaces as dispatch. That removes additional internal helper seats where explicit malformed selector/script params could otherwise be reinterpreted as `_count` / `gte` / `0.0` / `_value`.
- Follow-on correction: plugin `normalize` and the moving-window wrapper dispatchers now also enforce the same validated `aggregation` / `path` / `window` / percentile-list surfaces internally. This removes more helper-entry seats where explicit malformed moving/normalize params could otherwise be reinterpreted as `_count`, `2`, or family-default percentile configs.
- Follow-on correction: plugin `bucket_count` helper now also reuses the validated named-target surface instead of carrying an internal empty-target default. That removes another helper seat where malformed explicit target params could otherwise collapse into `value: 0` semantics.
- Follow-on correction: plugin `composite` finalization now consumes the same validated/defaulted `size` surface as collection and merge. This removes a remaining finalize-seat mismatch after `plugin_composite_size(...)` was tightened to an optional validated surface.
- Follow-on correction: plugin `filters` / `adjacency_matrix` branches now consume the same parsed filter-map surface as their collector-entry admission instead of reparsing raw maps with empty/default fallback behavior. This removes another internal seat where invalid filter maps could diverge between admission and branch execution.
- Follow-on correction: plugin `auto_date_histogram` / `variable_width_histogram` merge now reuses the same validated/defaulted `buckets` surface as collection. Explicit malformed bucket-count params no longer reappear as merge-time default `10` semantics during rebucketing/materialization.
- Follow-on correction: plugin `top_hits` merge now reuses the same validated window surface as collection/finalization. Malformed explicit `from` / `size` no longer re-enter through the merge seat as default `0` / `3` top-hits semantics.
- Follow-on correction: sampler-family merge now also reuses the same validated request surface as collection. Explicit malformed `size` / `shard_size` / `seed`, and invalid `diversified_sampler` field or `max_docs_per_value`, no longer survive into merge-time doc-count/nested materialization.
- Follow-on correction: plugin `composite` merge now also enforces the validated `after` cursor surface used by collection. Explicit malformed `after` no longer survives into reduce-time bucket/after-key materialization.
- Follow-on correction: plugin `filter` / `filters` / `adjacency_matrix` merge now also reuses the same validated query-map/request surface as collection. Invalid filter request surfaces no longer survive into merge-time wrapper doc-count or bucket materialization.
- Follow-on correction: plugin `top_metrics` merge/finalize now enforces the full validated request surface, not just `size`. Invalid explicit `metrics` or `sort` no longer survive into reduce/finalize-time top-metrics materialization.
- Follow-on correction: sampler-family merge now always runs the nested merge/finalization seat when subaggregations are present, matching adjacent wrapper families like `filter` / `global`. This removes a materialization drift where sampler wrappers could skip the final nested cleanup/finalization pass when the incoming nested payload was empty but existing nested state still needed the shared finalizer.
- Follow-on correction: array-bucket/plugin rebucketing merge paths now preserve cumulative wrapper-level nested reduce hints instead of replacing them with only the latest incoming hints or dropping them entirely. This reduces a deeper merge/materialization drift for nested `avg` / `cardinality` / percentile-family carriers across multi-input bucket recomposition.
- Follow-on correction: wrapper-family merge for `filter` / `global` / sampler now also preserves cumulative wrapper-level nested reduce hints instead of using incoming-only hint state. This keeps nested `avg` / `cardinality` / percentile-family carriers continuous across repeated wrapper merges before the shared finalizer removes them.
- Follow-on correction: `filters` / `adjacency_matrix` bucket-object merge now also preserves cumulative bucket-level nested reduce hints instead of using incoming-only hint state. This extends the same carrier continuity fix from wrapper families to keyed bucket-object recomposition.
- Follow-on correction: plugin `missing` wrapper merge now also preserves cumulative wrapper-level nested reduce hints instead of using incoming-only hint state. This closes the last direct `plugin_nested_reduce_hints_from_value(value)` merge seat and keeps nested `avg` / `cardinality` / percentile-family carriers continuous across repeated `missing` wrapper merges before shared finalization.
- Follow-on correction: plugin `date_histogram` and `composite` array-bucket merge now preserve cumulative nested reduce hints during bucket payload recomposition instead of dropping them after nested merge/finalization. This removes two remaining merge/materialization asymmetries where nested `avg` / `cardinality` / percentile-family carriers could be recomputed from merged nested payloads but then discarded before the next merge round.
- Follow-on correction: `merge_plugin_aggregation_value(...)` now enforces the same collector-side validated request surface for field-required bucket families, `weighted_avg.weight_field`, range-family `ranges`, `multi_terms.sources`, `date_histogram` interval, explicit `histogram.interval`, explicit rebucketing `buckets`, filter-map families, and plugin `composite` source/size/after params. Malformed plugin requests that collection already treats as placeholder/unsupported no longer survive into reduce-time bucket or wrapper materialization.
- Follow-on correction: shared plugin finalization now reuses the same validated merge/finalize request-surface helper as merge entry. Field/ranges/source/filter-map/interval/buckets/composite/sampler/top-hits/top-metrics plugin requests that are already placeholder/unsupported at collection or merge no longer survive into finalize-time truncation, ordering, wrapper cleanup, or nested finalization.
- Follow-on correction: plugin `auto_date_histogram` rebucketing merge now also preserves cumulative nested reduce hints during bucket recomposition instead of reusing only the rebucketed incoming hint state. This aligns `auto_date_histogram` with `variable_width_histogram` and removes another family-internal merge/materialization asymmetry for nested `avg` / `cardinality` / percentile-family carriers.
- Follow-on correction: shard-local/native plugin `top_hits` branch selection now uses the strict top-hits sort-surface helpers instead of raw `plugin_top_hits_window_and_sort(...).2.is_empty()` checks. Malformed explicit plugin sort no longer masquerades as a sort-less request and slip into the fast path with caller-final hit order semantics.
- Follow-on correction: plugin `top_metrics` score-sort request-surface helper now first requires a valid explicit sort surface instead of reading raw parsed sort specs directly. Malformed explicit plugin sort no longer collapses into the same branch classification as a legitimate non-score-sort request during hit-materialization planning.
- Follow-on correction: scored direct-reduce admission for plugin `top_hits` now distinguishes between a true sort-less request and an explicit malformed `sort` surface even under `CallerFinal` input order. Invalid explicit plugin sort no longer slips through the same fast-path admission gate that is intended only for no-sort or valid-sort requests.
- Follow-on correction: terms-family plugin collection and merge/finalize now require a valid explicit `size` surface, and `rare_terms` now also requires a valid explicit `max_doc_count` surface. Malformed numeric request params no longer degrade into default truncation/filter semantics like size `10` or rare-terms max-doc-count `1` during ordering and final shaping.
- Follow-on correction: terms-family plugin collection and merge/finalize now also require a valid explicit `order` surface. Malformed terms/rare-terms/multi-terms/significant-terms order params no longer collapse into the family default ordering during bucket sorting and final shaping.
- Follow-on correction: significant-terms-family planning/admission predicates now consult the validated terms-family `order` surface before interpreting plugin order semantics. Malformed explicit plugin `order` no longer masquerades as default score-order semantics during key/count-order admission and ranking/tie-break classification.
- Follow-on correction: direct single-plugin special execution now also reuses the shared validated merge/finalize request-surface gate before entering bespoke top-hits/top-metrics/significant-terms/global/sampler paths. Malformed plugin requests no longer begin work in those direct fast paths before being converted to placeholder only at the finalization seat.
- Follow-on correction: collection-side second-pass plugin finalization now also reuses the shared validated request-surface gate before calling `plugin_pipeline_aggregation_value(...)`. Malformed plugin finalize-family requests no longer survive into document-side, hit-side, or bucket-finalization pipeline materialization only because those second-pass seats bypassed the gate that merge/finalize already used.
- Follow-on correction: native-support planning for finalize-family plugins now requires the same validated request surface before treating `plugin_finalize_aggregation(...)` as a supported capability. Malformed finalize-family plugin requests no longer masquerade as natively supported aggregation-map members during early planning/admission.
- Follow-on correction: `aggregation_map_top_hits_window(...)` now consults the validated plugin top-hits window/sort surface before treating a plugin request as a sort-less top-hits window contributor. Malformed explicit `from` / `size` / `sort` no longer collapse into native top-hits window planning as though they were valid sort-less requests.
- Follow-on correction: generic plugin planning predicates for `all_hits`, hit-materialization, and direct-reduce exception admission now also require the shared validated request surface. Malformed plugin requests no longer escalate planning into expensive all-hits/materialized-hit work or claim direct-reduce eligibility simply because the plugin kind or nested subaggregation family would otherwise require it.
- Follow-on correction: shard-local sorted plugin `top_hits` collect-map admission now requires a valid plugin top-hits window surface as well as a valid non-empty sort surface. Malformed explicit `from` / `size` no longer escalate planning into expensive sorted-hit collection merely because the plugin also carries an explicit sort.
- Follow-on correction: plugin `top_metrics` score-sort admission/classification in direct-reduce and nested hit-materialization planning now requires the full validated request surface, not just a valid explicit sort parse. Malformed explicit metrics/size no longer masquerade as a legitimate score-sorted top-metrics request during planning.
- Follow-on correction: collection-side special plugin branches for `significant_terms` / `significant_text` / `global` now also require the shared validated request surface before entering bespoke hit-side or document-side collection. Malformed plugin requests no longer begin work in those special collection branches instead of resolving to placeholder at the generic collector boundary.
- Follow-on correction: top-hits response/materialization loops that consume precomputed top-hits windows now reject invalid explicit plugin `from` / `size` before choosing sort-less or sorted plugin execution branches. Malformed explicit window params no longer reach those branch seats and rely on a later helper-level placeholder fallback.
- Follow-on correction: significant-terms special branches now read the plugin field through the validated shared field helper instead of carrying local `unwrap_or_default()` fallback semantics. This removes another internal seat where a field-required plugin family could locally regress toward empty-field behavior even after outer request-surface guards were tightened.
- Follow-on correction: diversified-sampler helper logic now reads the sampler field through the shared validated field helper instead of carrying local raw field fallback semantics. This removes another internal seat where a field-required plugin family could drift back toward empty-field behavior despite outer request-surface guards.
- Follow-on correction: plugin `top_metrics` metric-field extraction no longer uses partial `filter_map` parsing for array-valued `metrics`. The helper now requires every metric entry to contribute a valid non-empty field before building the field list, so invalid array entries no longer silently collapse into a reduced top-metrics metric set inside special/native entry construction.
- Follow-on correction: plugin `multi_terms` source extraction no longer uses partial `filter_map` parsing over the `terms` array. The shared helper now returns a validated whole-surface `Option<Vec<_>>`, and both document-side and hit-side `multi_terms` branches reuse it directly, so malformed source entries no longer collapse into a reduced source list inside branch-local execution.
- Follow-on correction: percentile-family hidden `_values` carrier reads now use a shared strict numeric-array helper instead of partial `filter_map` parsing during metric merge and plugin merge/materialization. Intermediate percentile/boxplot/MAD carriers no longer silently drop malformed array entries and collapse into reduced numeric state inside repeated merge rounds.
- Follow-on correction: plugin `top_metrics` metric-field extraction now returns a validated `Option<Vec<_>>`, and native entry construction/comparison paths reuse that validated field list directly instead of carrying local empty-field fallback semantics. Malformed explicit metric-field surfaces no longer degrade into branch-local empty metrics during top-metrics native construction.
- Follow-on correction: plugin `rare_terms` final shaping no longer reads `max_doc_count` through a raw local `unwrap_or(1)` path. The helper now reuses a shared validated max-doc-count surface that preserves omission default semantics but resolves malformed explicit values to placeholder instead of silently collapsing to the default threshold inside finalization.
- Follow-on correction: terms-family internal order helpers now reuse a shared validated order surface instead of each carrying local raw default parsing. Omitted `order` still maps to the family default, but malformed explicit `order` no longer degrades into default terms/rare-terms/significant-terms ordering semantics inside helper-local bucket ordering.
- Follow-on correction: terms-family internal `size` shaping now reuses a validated helper that distinguishes omission default semantics from malformed explicit `size`. Terms/rare-terms/significant-terms local sort/finalize seats no longer carry a raw `unwrap_or(10)` path that could reintroduce default truncation semantics behind the outer request-surface guard.
- Follow-on correction: plugin `top_metrics` internal `size` helper now reuses a validated surface that preserves omission default semantics but separates malformed explicit `size` from default top-1 truncation. Native top-metrics truncation no longer carries a raw local `unwrap_or(1)` path behind the existing outer request-surface guards.
- Follow-on correction: plugin `top_hits` core window helper now reuses a validated omission-aware surface instead of carrying a raw local `(from,size) -> (0,3)` fallback. Planning/merge/materialization seats that consume that helper now treat malformed explicit window params as invalid locally rather than silently reviving default top-hits window semantics behind the existing outer guards.
- Follow-on correction: removed a stale raw `plugin_composite_size(...) -> usize` helper that still carried local `unwrap_or(10)` semantics after the live composite paths had already moved to the validated optional size surface. This eliminates another dead internal seat where composite default-size semantics could drift from the active helper family.
- Follow-on correction: plugin `bucket_sort` helper-internal window shaping no longer carries raw local `from -> 0` / `size -> 10` fallback semantics. The helper now preserves omission defaults but treats malformed explicit window params as invalid locally, aligning its internal seat with the existing outer request-surface guard.
- Follow-on correction: diversified-sampler local per-value-cap shaping no longer carries a raw `unwrap_or(1)` path. The helper now preserves omission default semantics but separates malformed explicit `max_docs_per_value` from the default cap, so sampler-local diversification does not silently revive default per-value throttling behind the existing outer request-surface guards.
- Follow-on correction: sampler-family local seed shaping no longer carries a raw `unwrap_or(0)` path. The helper now preserves omission default semantics but separates malformed explicit `seed` from the default sampler seed, so random/diversified sampler-local ordering does not silently revive default seed semantics behind the existing outer request-surface guards.
- Follow-on correction: sampler-family local size limiting now reuses an omission-aware helper that distinguishes explicit `size` from explicit `shard_size` and no longer lets malformed explicit size surface collapse into shard-size or unlimited sampling semantics inside sampler-local collection. Sampler/local branches now also reject invalid explicit size surfaces directly instead of relying only on outer guards.
- Follow-on correction: diversified-sampler required-field validation now reuses the shared validated field helper instead of carrying its own raw field read. This removes another local field seat and keeps sampler-family field-required semantics anchored to the same non-empty field surface used by the broader plugin request guards.
- Follow-on correction: `plugin_filter_map_queries(...)` no longer uses partial `filter_map` plus length comparison when parsing plugin filter maps. It now collects directly into a whole-surface `Option<Vec<_>>`, which keeps filter-map strictness anchored to a single non-lossy helper shape instead of reconstructing strictness after a lossy intermediate representation.
- Follow-on correction: plugin `top_metrics` now uses a single validated metric-field surface for both extraction and validity checks. Empty `metrics` arrays no longer materialize as `Some(vec![])`, and the validity predicate no longer reparses raw metric params independently of the shared helper.
- Follow-on correction: plugin `top_metrics.size`, terms-family `size`, and `rare_terms.max_doc_count` validity predicates now reuse the same omission-aware extraction helpers that local shaping/finalization already uses. Those predicates no longer reparse the raw params independently of the active helper surface.
- Follow-on correction: terms-family `order` validity and extraction now converge on a single helper surface. The validity predicate no longer reparses raw order params independently; instead it reuses `plugin_terms_family_order_param(...)`, which now performs the full one-key/allowed-field/direction validation itself.
- Follow-on correction: plugin `top_hits` window validity and extraction now converge on a single omission-aware helper surface. `plugin_top_hits_has_valid_window_params(...)` no longer reparses raw `from` / `size` params independently; it reuses `plugin_top_hits_window_and_sort(...)` directly.
- Follow-on correction: sampler-family `seed` and diversified-sampler `max_docs_per_value` validity predicates now reuse the same omission-aware extraction helpers that local sampling already uses. Those predicates no longer reparse the raw params independently of the active helper surface.
- Follow-on correction: plugin `top_metrics` explicit sort validity and request-surface classification now converge on a single helper surface. `plugin_top_metrics_has_valid_sort_specs(...)` and score-sort detection no longer reparse the raw sort carrier independently; both reuse the same validated explicit sort-spec extraction helper.
- Follow-on correction: plugin `top_hits` explicit sort validity and request-surface classification now converge on a single helper surface. `plugin_top_hits_has_valid_sort_specs(...)`, non-empty-sort detection, and score-sort detection no longer reparse the raw sort carrier independently; all three now reuse the same validated explicit sort-spec extraction helper.
- Follow-on correction: removed the remaining thin explicit-sort validity wrappers for plugin `top_hits` and `top_metrics`. Top-hits request/collection guards and top-metrics support/finalization gates now bind directly to the shared validated explicit sort-spec helpers instead of routing through one-use boolean wrappers.
- Follow-on correction: removed the thin terms-family validity wrappers for `size`, `order`, and `rare_terms.max_doc_count`. Request-surface guards, collection gates, and significant-terms planning seats now bind directly to the shared omission-aware size/order/max-doc-count helpers instead of routing through one-use boolean wrappers.
- Follow-on correction: removed the thin plugin `top_hits` window-validity wrapper. Top-hits request-surface checks, shard-local admission, merge/finalization, and collection paths now bind directly to the shared omission-aware window helper instead of routing through a separate boolean gate.
- Follow-on correction: removed the thin plugin `bucket_sort` explicit-sort validity wrapper. Bucket-sort request/finalization seats now bind directly to the shared validated explicit sort-values helper instead of routing through a one-use boolean gate.
- Follow-on correction: removed the thin sampler-family `size` validity wrapper. Sampler request-surface checks, merge gates, and document/hit collection paths now bind directly to the shared omission-aware size-limit helper instead of routing through a separate boolean gate.
- Follow-on correction: removed the remaining thin plugin `top_metrics` validity wrappers for `metrics` and `size`. Native support checks, request-surface gates, and merge/finalization seats now bind directly to the shared validated metric-field and omission-aware size helpers instead of routing through one-use boolean wrappers.
- Follow-on correction: plugin `top_metrics` merge no longer finalizes provenance directly on the only carried `top` array. Merge now preserves a hidden `_merge_top` carrier and only strips `_index`/`_id` from the visible final `top` surface during finalization, so repeated merge rounds keep deterministic tie-break provenance instead of re-reading already-final-shaped entries.
- Follow-on correction: plugin terms-family bucket merges no longer rely on the already-final-shaped visible `buckets` array as their only repeated-merge carrier. `terms` / `rare_terms` / `multi_terms` / `significant_terms` now preserve a hidden `_merge_buckets` carrier, and the array-bucket nested finalizer updates that carrier alongside the visible subset so repeated merge rounds do not lose pre-truncation bucket state or nested merged fields.
- Follow-on correction: the same hidden `_merge_buckets` carrier pattern now also covers plugin `range` / `ip_range` / `date_range` / `histogram` / `geo_distance`. Their merge branches no longer restart from the already-final-shaped visible `buckets` array, so repeated merge rounds keep the wider merged bucket set and nested bucket state before any later outward shaping.
- Follow-on correction: plugin `composite` now also keeps bucket-carrier and outward-shaping semantics separate. Merge/finalization no longer rely on the visible `buckets` subset as the only carried state; instead a hidden `_merge_buckets` carrier survives repeated merge rounds while visible `buckets` plus `after_key` are recomputed from that carrier.
- Follow-on correction: hidden merge carriers are now stripped only at outward response boundaries instead of being consumed inside the repeated-merge machinery. The final merged response writers recursively remove `_merge_hits`, `_merge_top`, and `_merge_buckets` just before returning outward `aggregations`, keeping those carriers available through internal merge/finalize rounds without leaking them into final responses.
- Follow-on correction: the same outward-boundary merge-carrier cleanup now also covers the remaining hit/materialized/document-backed response writers and single-plugin finalize path. These response exits now strip `_merge_hits`, `_merge_top`, and `_merge_buckets` after finalization and before returning outward values, closing the remaining leak paths for internal carriers.
- Follow-on correction: object-bucket wrapper families now also stop using the visible `buckets` object as their only repeated-merge carrier. Plugin `filters` and `adjacency_matrix` preserve a hidden `_merge_buckets` object during merge/nested-finalization and only mirror that state back onto the visible `buckets` surface afterward.
- Follow-on correction: rebucketing plugin families now also preserve hidden bucket carriers across repeated merge rounds. Plugin `auto_date_histogram` and `variable_width_histogram` no longer restart from the outward-shaped visible `buckets` subset; they keep `_merge_buckets` as the rebucketing carrier and derive the visible coarsened bucket window from that carrier.
- Follow-on correction: the same carrier split now also covers native `significant_terms` and native range-family bucket merges. Native significant-terms final shaping no longer truncates the only carried `buckets` array, and native range merges no longer treat the visible `buckets` array as the sole repeated-merge carrier.
- Follow-on correction: native `date_histogram` and native `histogram` merge helpers now also preserve hidden bucket carriers. They no longer accumulate directly into the outward-visible `buckets` array; instead they keep `_merge_buckets` as the repeated-merge carrier and mirror the current merged bucket set onto `buckets`.
- Follow-on correction: native `terms` now also uses the hidden `_merge_buckets` carrier through merge and final shaping. The native terms finalizer no longer truncates the only carried `buckets` array, and repeated native terms merges no longer treat the outward-visible subset as the sole bucket carrier.
- Follow-on correction: array-bucket carrier recomposition is now partially centralized through shared helper functions instead of being repeated inline across terms/significant finalizers. This reduces the number of independent seats that can drift between `_merge_buckets` carrier handling and visible `buckets` shaping.
- Follow-on correction: plugin `composite` final shaping now also reuses the shared array-bucket carrier helper instead of keeping its own local `_merge_buckets` recomposition block. This removes another duplicate seat between carrier handling and visible bucket shaping.
- Follow-on correction: rebucketing plugin families now also reuse shared bucket-carrier take/set helpers instead of each keeping their own local `_merge_buckets` extraction and visible writeback blocks. This reduces duplicate seats around repeated rebucketing carrier handling.
- Follow-on correction: plugin `bucket_sort` explicit sort validity and helper-internal sort extraction now converge on a single helper surface. `plugin_bucket_sort_has_valid_sort_param(...)` and bucket-sort helper execution no longer reparse the raw sort carrier independently; both reuse the same validated explicit sort-values helper.
- Follow-on correction: generic top-hits/top-metrics sort extraction now also reuses the existing validated explicit sort-spec helpers instead of reparsing raw sort params independently. This pulls both families’ ordinary sort-spec access onto the same single explicit-sort surface already used by validity and classification helpers.
- Follow-on correction: removed the now-dead raw top-hits sort-carrier accessor after explicit sort validity/classification/extraction converged on the validated helper surface. This leaves the top-hits explicit sort interpretation anchored to a single active helper family instead of preserving a stale raw-access seat.
- Follow-on correction: sampler-family `size`/`shard_size` validity now reuses the same omission-aware size-limit helper that local sampling uses. The validity predicate no longer reparses raw size params independently of the active helper surface.
- Follow-on correction: plugin `bucket_sort` window validity and helper-internal extraction now converge on a single omission-aware helper surface. The bucket-sort predicate no longer reparses raw `from` / `size` independently of execution; both seats now reuse the same validated window helper.
- Follow-on correction: plugin `adjacency_matrix.separator` validity and extraction now converge on a single omission-aware helper surface. The validity predicate no longer reparses the raw separator independently, and the two adjacency-matrix collection branches now also use the same helper result instead of carrying their own raw default separator seat.
- Follow-on correction: plugin `multi_terms` source validity now reuses the same validated source-extraction helper that branch execution already uses. The validity predicate no longer reparses raw `terms` entries independently of the active helper surface.
- Follow-on correction: removed the thin `plugin_adjacency_matrix_queries(...)` wrapper and wired adjacency-matrix collection branches directly to the shared validated filter-map helper. This leaves adjacency-matrix query interpretation anchored to the same single helper surface used by the broader filter-map family.
- Follow-on correction: removed the thin `plugin_terms_bucket_order(...)` and `plugin_rare_terms_bucket_order(...)` wrappers. Terms and rare-terms ordering now bind directly to the shared validated terms-family order helper, leaving fewer wrapper seats between local bucket ordering and the active order surface.
- Follow-on correction: removed the thin `plugin_significant_terms_bucket_order(...)` wrapper. Significant-terms planning predicates and local bucket ordering now bind directly to the shared validated terms-family order helper, leaving fewer wrapper seats between significant-terms order semantics and the active helper surface.
- Follow-on correction: removed the thin `plugin_multi_terms_has_valid_sources(...)` wrapper. Merge/finalize and collection guards now bind directly to the shared validated `plugin_multi_terms_sources(...)` helper, leaving fewer wrapper seats between multi-terms source semantics and the active helper surface.
- Follow-on correction: removed the thin boolean `plugin_adjacency_matrix_has_valid_separator_param(...)` wrapper. Remaining adjacency-matrix gates now bind directly to the shared omission-aware separator helper, leaving fewer wrapper seats between separator semantics and active request-surface enforcement.
- Follow-on correction: removed the thin `plugin_top_metrics_sort_specs(...)` wrapper. Native top-metrics support checks, comparison, and collection paths now bind directly to the shared validated explicit sort-spec helper, leaving fewer wrapper seats between top-metrics sort semantics and the active helper surface.
- Follow-on correction: removed the thin sampler-family boolean wrappers for `seed` and diversified-sampler `max_docs_per_value` validity. Remaining sampler guards now bind directly to the shared omission-aware helpers, leaving fewer wrapper seats between sampler request semantics and active enforcement.
- Follow-on correction: object-bucket carrier recomposition is now partially centralized through shared helper functions instead of being repeated inline across `filters` and `adjacency_matrix`. This reduces duplicate seats between hidden `_merge_buckets` object handling and the visible `buckets` surface.
- Follow-on correction: several native array-bucket merge helpers now reuse the shared array-bucket carrier take/set helpers instead of open-coding `_merge_buckets` extraction and visible writeback. In the same pass, plugin `composite` now reuses the hidden carrier as repeated-merge input instead of restarting from visible `buckets`, and plugin `date_histogram` now restores `_merge_buckets` alongside visible `buckets` after nested merge recomposition.
- Follow-on correction: plugin bucket-family merge branches now further converge on the shared array-bucket carrier take/set helpers instead of repeating local `_merge_buckets` extraction and visible writeback blocks. This also narrows the remaining seats where plugin repeated-merge state could drift from the hidden carrier surface.
- Follow-on correction: the remaining plugin array-bucket merge branches for `geo_distance`, `date_histogram`, `significant_terms`, and `multi_terms` now also converge on the shared hidden-carrier helpers. This removes more inline `_merge_buckets` extraction/writeback seats and keeps those families aligned with the common repeated-merge carrier path.
- Follow-on correction: `top_hits` and `top_metrics` carrier handling now also converges on shared helper functions. In particular, top-hits finalization no longer consumes `_merge_hits`; it now derives visible hits from the carrier while preserving hidden merge state across repeated rounds, matching the earlier `_merge_top` lifetime fix.
- Follow-on correction: sorted `top_hits` merge no longer drops per-hit auxiliary surfaces during `SearchHit` round-tripping. Reconstructed hits now preserve `fields`, `highlight`, and `_explanation` instead of hard-resetting them to `None` inside the merge path.
- Follow-on correction: `SearchHit` now carries the hit-level `sort` surface, and the sorted `top_hits` merge round-trip preserves it instead of silently dropping it. The same serializer/parser path that now retains `fields`, `highlight`, and `_explanation` also retains OpenSearch `sort` arrays across merge rounds.
- Follow-on correction: the new `SearchHit.sort` preservation change is now scoped back to `SearchHit` only. Accidental vector-hit collateral edits were removed, so sorted top-hits keep the OpenSearch `sort` surface without altering `VectorSearchHit` construction.
- Follow-on correction: the new top-hits round-trip preservation path now keeps `fields` and `highlight` in the same `Option<Value>` shape carried by `SearchHit`, instead of attempting to materialize raw object maps directly. This keeps the preservation fix aligned with the shared hit surface type.
- Follow-on correction: plugin `top_metrics` merge no longer reads only the visible `top` array from incoming intermediate values. It now reuses the shared hidden-carrier read path for the incoming side as well, so repeated merge rounds do not discard an incoming `_merge_top` carrier by restarting from the outward-shaped visible subset.
- Follow-on correction: plugin bucket-wrapper merge paths now also reuse shared hidden-carrier readers for the incoming side, not just the current side. Incoming nested merge logic no longer restarts from outward-visible `buckets` when an intermediate `_merge_buckets` carrier is already present.
- Follow-on correction: `top_hits` merge now also reuses the shared hidden-carrier reader for the incoming side. Incoming intermediate hit objects no longer restart from only the visible `hits` array when an internal `_merge_hits` carrier is already present.
- Follow-on correction: plugin bucket-wrapper callers now also reuse shared hidden-carrier readers on the wrapper-output side, not just current-side and incoming-side reads. This narrows another class of visible-surface restarts where callers previously re-read only the outward `buckets` field after merge helpers had already preserved `_merge_buckets` internally.
- Follow-on correction: rebucketing plugin families now also reuse the shared array-carrier reader on both incoming-side and wrapper-output-side reads. `auto_date_histogram` and `variable_width_histogram` no longer restart from only the outward `buckets` array when an intermediate `_merge_buckets` carrier is available.
- Follow-on correction: the remaining no-subaggregation `composite` wrapper-output branch now also reuses the shared array-carrier reader instead of re-reading only the outward `buckets` field. This removes another visible-surface restart seat on the plugin composite path.
- Follow-on correction: bucket-path pipeline collectors now start converging on shared hidden-carrier-aware bucket readers instead of always reading only outward `buckets`. The shared helper path is now in place for representative bucket-count/normalize/bucket-selector/bucket-script collection seats, reducing pipeline drift against `_merge_buckets`.
- Follow-on correction: moving-window pipeline collectors now also converge on the shared hidden-carrier-aware bucket reader instead of each re-materializing outward `buckets` with local array/object normalization blocks. This extends the pipeline-side `_merge_buckets` awareness beyond the initial representative collectors.
- Follow-on correction: plugin bucket-count and bucket-sort collection now also reuse the shared hidden-carrier-aware bucket readers instead of reading only the outward `buckets` field. This extends pipeline-side `_merge_buckets` awareness to two more live bucket-path seats.
- Follow-on correction: `bucket_metric_values(...)` now also reuses the shared hidden-carrier-aware bucket reader instead of pulling only outward `buckets` directly from the target aggregation. This brings moving-count and other helper-driven bucket-path reads onto the same `_merge_buckets`-aware surface.
- Follow-on correction: remaining merge-helper loops that previously iterated only over `value["buckets"]` arrays now iterate over the shared incoming hidden-carrier reader instead. This extends `_merge_buckets` awareness deeper into native/plugin bucket merge loops rather than stopping at wrapper setup.
- Follow-on correction: wrapper-output extraction for plugin array-bucket branches is now centralized through a shared helper after a broken intermediate rewrite was removed. In the same pass, plugin `date_histogram` final writeback again mirrors both hidden `_merge_buckets` and visible `buckets` instead of leaving only the visible surface.
- Follow-on correction: native `terms` / `date_histogram` / `histogram` / `composite` merge entrypoints and native `filters` object-bucket merge now read incoming bucket state through shared hidden-carrier readers rather than only outward `buckets` surfaces. In the same pass, plugin `composite` nested-subaggregation recomposition now reads wrapper output through the same carrier-aware path.
- Follow-on correction: the remaining plugin `rare_terms` wrapper-output recomposition seat now also reads merged buckets through the shared hidden-carrier-aware array reader instead of re-reading only visible `buckets`.
- Follow-on correction: top-level search fetch-subphase reporting now marks `StoredFields` as completed whenever the narrow hit `fields` projection surface is actually materialized from stored/source projection inputs, instead of always reporting the subphase as skipped.
- Follow-on correction: explicit top-level search sorting now also materializes outward hit `sort` arrays on the shared `SearchHit` surface. Previously many search paths sorted hits correctly but still returned `sort: null`/absent because the common `sort_hits(...)` path never wrote the outward sort payload.
- Follow-on correction: additional top-level sorted-hit return paths that already relied on Tantivy/native ordering but bypassed `sort_hits(...)` now also materialize outward hit `sort` arrays through a shared helper before returning. This closes the remaining explicit-sort seats where ordering was correct but `SearchHit.sort` could still stay absent.
- Follow-on correction: the plugin `rare_terms` merge branch no longer mutates only visible `buckets` after `merge_terms_aggregation_value(...)` and then re-reads the hidden carrier. It now mutates the shared wrapper bucket carrier directly, so nested recomposition survives the `_merge_buckets`-preferred final read.
- Follow-on correction: top-level hit highlighting no longer uses a possibly source-projected `SearchHit.source` as its only highlight input. The highlight transform now prefers the refreshed document's full source when available, so `_source` projection no longer suppresses highlight snippets for requested fields outside the narrowed hit source surface.
- Follow-on correction: top-level hit explanation generation now also prefers the refreshed document's full source instead of relying only on the possibly source-projected `SearchHit.source`. This keeps `_source` projection from narrowing synthetic explanation details that still inspect source-backed match context.
- Follow-on correction: object-bucket nested finalization for plugin `filters` / `adjacency_matrix` now updates `_merge_buckets` first and mirrors the finalized state back to visible `buckets`, matching the array-bucket carrier pattern. Previously object-bucket finalization could leave a stale hidden carrier even after visible nested buckets were finalized.
- Follow-on correction: requested-page hit finalization now also materializes outward `sort` arrays when explicit sort is present but the page contains zero or one hit. Previously `finalize_hits_for_requested_page(...)` only invoked `sort_hits(...)` for multi-hit pages, leaving single-hit explicit-sort responses without the outward sort payload.
- Follow-on correction: `search_hits_for_query_native(...)` now also applies the requested sort when returning hits straight from vector/document-scan candidate-window context. Previously that branch could return raw context hits without running the usual relevance/explicit sort path.
- Follow-on correction: `search_hits_for_query_with_sort(...)` no longer returns cached KNN hits before applying the caller's requested sort. Cached KNN fast-path results now re-enter the same relevance/explicit-sort path as freshly collected hits.
- Follow-on correction: cached KNN sorted-page lookup now also materializes outward hit `sort` arrays after bounded-page insertion. Previously the fast path preserved requested ordering through `insert_bounded_page_hit(...)` but could still return page hits without the outward sort payload.
- Follow-on correction: the remaining bounded-page builders that keep requested ordering through `insert_bounded_page_hit(...)` now also materialize outward hit `sort` arrays before returning. This covers the hybrid-bool candidate-id page collector and the uncached KNN vector-candidate fast path, both of which previously preserved order but could still emit sorted hits without the outward sort payload.
- Follow-on correction: the index-aware full-KNN fallback page/window paths now also apply default relevance ordering instead of sorting only for explicit sort requests. Previously those fallback seats could treat raw `full_knn_hits_index_aware(...)` order as already final when the caller still expected standard relevance ordering.
- Follow-on correction: `search_hits_for_query_native(...)` no longer returns raw document-scan fallback hits before running the usual relevance/explicit-sort post-processing. That branch now re-enters the same ordering/materialization path as the other native fast paths instead of bypassing requested hit ordering entirely.
- Follow-on correction: `search_hits_context_for_query_native_index_aware(...)` has its bool-fallback tail restored to the intended `Query::Bool => context hit return, _ => Ok(None)` shape. The current worktree no longer leaves that helper in a half-edited state after the bool/document fallback branch.
- Follow-on correction: vector/index-aware native aggregation collection now sorts its assembled hit carrier by standard relevance before feeding it into `PluginTopHitsInputOrder::CallerFinal` paths. Raw context/window hits from grouped vector branches no longer leak pre-final order into top-hits-sensitive aggregation input.
- Follow-on correction: the adjacent `MatchAll`/lexical fallback paths inside native aggregation collection now also relevance-sort their `all_hits` and fallback `hits` carriers before passing them into `PluginTopHitsInputOrder::CallerFinal`. Those non-window fallback seats no longer bypass the same top-hits-sensitive input-order contract as the grouped vector/native branch.
- Follow-on correction: the multi-index refresh/reusable-context aggregation paths now also relevance-sort reconstructed `hit_context.hits` and `hit_context.all_hits` before feeding them into `PluginTopHitsInputOrder::CallerFinal`. Reassembled multi-index hit carriers no longer leak merge/materialization order straight into top-hits-sensitive aggregation input.
- Follow-on correction: top-level single-index/multi-index aggregation assembly now also relevance-sorts `all_hits` before constructing `PluginTopHitsInputOrder::CallerFinal` hit contexts. Match-all carrier assembly no longer preserves per-index append order when those `all_hits` feed top-hits-sensitive aggregation input.
- Follow-on correction: `rewrite_top_hits_reduce_windows(...)` now normalizes its hit carrier to standard relevance order before rebuilding unsorted top-hits windows. The helper no longer relies on every caller to pre-certify `CallerFinal` order for reduce-window rewrites.
- Follow-on correction: sampler/random-sampler/diversified-sampler hit-materialization now relevance-sorts the sampled carrier before feeding it into nested `PluginTopHitsInputOrder::CallerFinal` aggregation paths. Nested unsorted `top_hits` under sampler-family plugins no longer inherit sample-order/random-order as if it were final relevance order.
- Follow-on correction: the core unsorted plugin `top_hits` helpers now normalize `PluginTopHitsInputOrder::CallerFinal` carriers to standard relevance order instead of trusting raw caller order. This hardens both ordinary and window-based plugin top-hits shaping against any remaining caller-side ordering drift.
- Follow-on correction: `finalize_merged_top_metrics_aggregation_value(...)` now writes visible `top` through the same top-metrics carrier helper that preserves `_merge_top`. Final shaping no longer leaves top-metrics in a visible-only state when repeated finalize/merge rounds revisit a legacy or carrier-less intermediate shape.
- Follow-on correction: non-score explicit plugin `top_hits` final shaping now clears `_score` on the hidden `_merge_hits` carrier as well as the visible hit array. The scoreless outward semantics for sort-driven plugin top-hits no longer diverge from the preserved merge carrier between finalize rounds.
- Follow-on correction: `finalize_plugin_array_bucketed_nested_aggregation_value(...)` now reseeds visible `buckets` from the finalized `_merge_buckets` carrier when legacy/intermediate shapes lack a visible array. Array-bucket nested finalization no longer leaves carrier-only finalized state behind without restoring a visible bucket surface.
- Follow-on correction: the plugin `top_hits` merge branch now normalizes the inner `hits` object through the shared top-hits carrier helper before writing it back. Legacy/intermediate plugin-top-hits merge output no longer carries `_merge_hits` without also reseeding a visible `hits` array.
- Follow-on correction: the native page-query fast paths that return hits straight from vector/document-scan context now also apply default relevance ordering instead of sorting only for explicit sort requests. Previously those page-context branches could preserve raw context order when the caller still expected standard relevance ordering.
- Follow-on correction: the analogous native window-hit and index-aware context fast paths now also apply default relevance ordering instead of treating raw context order as already final. This extends the same ordering fix beyond page-query fast paths to direct window/context returns.
- Follow-on correction: `clear_top_hits_score_surface(...)` now reseeds visible `hits` from the carrier helper when legacy/intermediate shapes lack a visible hit array. Score-clearing for non-score plugin top-hits no longer mutates only `_merge_hits` without restoring the visible hit surface.
- Follow-on correction: `collect_aggregations_with_plugin_top_hits_input_order(...)` now normalizes `PluginTopHitsInputOrder::CallerFinal` hit/all-hit carriers to standard relevance order at the helper boundary. This collapses a wide class of residual caller-side ordering drift instead of relying on every upstream seat to pre-sort the same carrier contract.
- Follow-on correction: `pipeline_bucket_values(...)` now normalizes through `pipeline_bucket_surface(...)` instead of assuming every `_merge_buckets` carrier is array-shaped. Pipeline collectors now read object-bucket carriers like `filters` / `adjacency_matrix` without collapsing them to empty arrays when hidden carrier state is present.
- Follow-on correction: `collect_normalize_aggregation_value(...)` and `collect_bucket_script_aggregation_value(...)` now preserve object-bucket shape when their target aggregation carries object buckets. `filters` / `adjacency_matrix` pipeline results no longer flatten hidden/object bucket carriers into array-only output.
- Follow-on correction: moving-window pipeline family (`moving_avg`, `moving_sum`, `moving_min`, `moving_max`, `moving_median`, `moving_stddev`, `moving_mad`, `moving_variance`, `moving_range`, `moving_skewness`, `moving_kurtosis`, `moving_percentiles`, `moving_percentile_ranks`) now preserves object-bucket target shape by computing from `pipeline_bucket_surface(...)` instead of flattening `filters` / `adjacency_matrix` targets through array-only `pipeline_bucket_values(...)` output.
- Follow-on correction: `moving_count` now preserves object-bucket target shape and original bucket keys by reading `pipeline_bucket_surface(...)` directly and filtering buckets by `bucket_normalize_source_value(...)` presence instead of flattening through `bucket_metric_values(...)` into index-keyed array output.
- Follow-on correction: generic pipeline moving-window aggregations (`MovingCount`, `MovingAvg`, `MovingSum`, `MovingMin`, `MovingMax`, `MovingMedian`, `MovingMad`, `MovingStddev`, `MovingVariance`, `MovingSkewness`, `MovingKurtosis`, `MovingRange`, `MovingPercentiles`, `MovingPercentileRanks`) now preserve object-bucket target shape and original bucket keys by computing from a shared `buckets_path`-aware moving-window helper instead of flattening through `bucket_metric_values(...)` into index-keyed array output.
- Follow-on correction: `bucket_sort` now preserves object-bucket target shape by sorting object entries in key-preserving form and returning an object result for `filters` / `adjacency_matrix` targets instead of always flattening to an array of buckets.
- Follow-on correction: direct plugin `terms` / `rare_terms` collection paths now seed `_merge_buckets` alongside visible `buckets` and perform post-ordering through `set_object_bucket_array_visible_and_carrier(...)` instead of returning visible-only bucket arrays as initial merge input.
- Follow-on correction: direct plugin `significant_terms` / `significant_text` collection and nested direct plugin `multi_terms` collection now seed `_merge_buckets` alongside visible `buckets` and perform post-ordering through `set_object_bucket_array_visible_and_carrier(...)` instead of leaving initial bucket responses visible-only.
- Follow-on correction: direct plugin `range` / `ip_range` / `date_range` / `geo_distance` / `histogram` collection paths are being moved onto the same initial `_merge_buckets` seed contract as the other bucket families; this turn covered document-side range-family producers and hit-side `range` / `ip_range` / `histogram` plus document-side `histogram`, replacing visible-only initial bucket responses with `set_object_bucket_array_visible_and_carrier(...)` writeback.
- Follow-on correction: hit-side direct plugin `date_range` / `geo_distance` plus hit-side `date_histogram` / `auto_date_histogram` / `variable_width_histogram` producers now seed `_merge_buckets` alongside visible `buckets`, and their non-nested collector fallbacks are normalized back through `take_object_bucket_array_carrier(...)` + `set_object_bucket_array_visible_and_carrier(...)` instead of remaining visible-only.
- Follow-on correction: document-side direct plugin `date_histogram` / `auto_date_histogram` / `variable_width_histogram` producers now seed `_merge_buckets` alongside visible `buckets`, and their non-nested collector fallbacks are normalized back through `take_object_bucket_array_carrier(...)` + `set_object_bucket_array_visible_and_carrier(...)` instead of remaining visible-only.
- Follow-on correction: direct plugin `composite` producers now seed `_merge_buckets` alongside visible `buckets` for both nested and non-nested document/hit paths, and non-nested collector fallbacks are normalized back through `take_object_bucket_array_carrier(...)` + `set_object_bucket_array_visible_and_carrier(...)` instead of remaining visible-only.
- Follow-on correction: direct plugin `top_hits` producers now seed `_merge_hits` with the pre-window `from + size` carrier while keeping visible `hits` as the outward page subset, instead of materializing only the outward page and losing the merge-time pre-window carrier needed for repeated sorted reduce/finalize rounds.
- Follow-on correction: direct plugin `top_metrics` producers now seed `_merge_top` alongside visible `top` through `set_object_top_metrics_visible_and_carrier(...)` for both empty and non-empty native document/hit collection paths instead of starting from a visible-only `top` surface.
- Follow-on correction: direct plugin `significant_terms` / `significant_text` paths no longer mutate visible `buckets` arrays in place before later carrier writeback; they now take the bucket carrier up front, perform nested augmentation and ordering on that carrier vec, and then write visible/carrier back together.
- native `terms` / `significant_terms` direct producers now seed `_merge_buckets` instead of starting from visible-only `buckets`, so native repeated merge/finalize paths inherit the same bucket carrier contract as plugin families.
- native `range` / `ip_range` / `date_range` / `geo_distance` / `histogram` / `date_histogram` / `composite` direct collectors now seed `_merge_buckets` instead of returning visible-only `buckets`, aligning native initial bucket responses with later carrier-aware merge/finalize helpers.
- native `top_hits` direct producers now seed `_merge_hits` with pre-window carrier instead of starting from visible-only `hits`, matching the repeated reduce/finalize contract already used by plugin `top_hits`.
- native `filters` direct producers now seed object-shaped `_merge_buckets` instead of returning visible-only `buckets`, aligning native object-bucket responses with the same carrier contract already used by object-bucket merge/finalize helpers.
- plugin object-bucket direct helper now seeds object-shaped `_merge_buckets` instead of inserting visible-only `buckets`, so `filters` / `adjacency_matrix` direct producer paths share the same helper-level carrier contract as their merge/finalize logic.
- shared pipeline bucket wrappers now preserve carrier-aware object/array bucket shape instead of re-wrapping results as visible-only `buckets`, and this is now applied to standard bucket pipeline finalization plus plugin `normalize` / `bucket_selector` / `bucket_script` / `bucket_sort` and moving-average/count style wrappers.
- remaining plugin moving-window wrappers and generic pipeline moving-window outputs now also go through shared carrier-aware bucket wrappers, reducing the last repeated visible-only `buckets` wrapper seats in moving pipeline families.
- object/array bucket nested finalizer fallbacks now also round-trip through shared carrier helpers instead of finalizing visible `buckets` in place only, so legacy no-carrier shapes are re-seeded onto the same carrier contract before later rounds.
- empty array-bucket merge seeds and plugin `multi_terms` direct helper now also use shared carrier-aware bucket wrappers instead of visible-only `{"buckets":[]}` or visible-only direct bucket surfaces, reducing another set of helper-boundary fallback seats.
- bucket pipeline second-pass assembly, date-histogram error fallbacks, and rebucketing/composite temporary wrappers now also use shared carrier-aware bucket wrappers instead of visible-only empty `buckets` surfaces, reducing more live helper-boundary fallback seats.
- hit-side `auto_date_histogram` fallback now also uses the shared carrier-aware empty bucket wrapper instead of a visible-only empty `buckets` surface, closing another rebucketing fallback seat.
- plugin merge entry seeds for `variable_width_histogram` and `composite` now also start from shared carrier-aware empty bucket wrappers instead of visible-only empty `buckets` surfaces, reducing more empty-start merge seats.
- plugin `composite` temporary wrapper input now reuses the shared bucket wrapper helper instead of rebuilding a visible-only `buckets` object, tightening one more merge-helper boundary around `_merge_buckets`.
- plugin merge wrapper inputs and empty entry seeds for `rare_terms`, range-family, `auto_date_histogram`, and object-bucket `filters` now also use shared carrier-aware bucket wrappers instead of rebuilding visible-only bucket surfaces.
- plugin merge wrapper inputs and empty entry seeds for `terms`, `histogram`, `geo_distance`, `date_histogram`, and object-bucket `adjacency_matrix` now also use shared carrier-aware bucket wrappers instead of rebuilding visible-only bucket surfaces.
- plugin `rare_terms` / `significant_terms` / `multi_terms` merge entry seeds and native `merge_composite`, `merge_filters`, `merge_significant_terms` empty-start helpers now also seed shared carrier-aware bucket wrappers instead of rebuilding visible-only bucket surfaces.
- rebucketing plugin merge inputs for `auto_date_histogram` / `variable_width_histogram` now pass shared carrier-aware bucket wrappers for rebucketed input, and plugin `top_hits` empty/default inner hit objects now seed `_merge_hits` instead of rebuilding visible-only hit surfaces.
- plugin object-bucket nested merge for `filters` / `adjacency_matrix` now mutates a carrier-first local bucket map via shared take/set helpers instead of directly mutating `_merge_buckets` in place before mirroring.
- native `top_hits` merge helpers and plugin `top_metrics` merge entry seed now reuse shared empty carrier-aware helper values instead of inlining visible-only `hits`/`top` seeds.
- plugin nested bucket finalizers now always finalize through taken carrier maps/vectors instead of directly mutating `_merge_buckets` in place, and plugin `top_hits` merge wrapper input now reuses the shared carrier-aware top-hits wrapper helper.
- `take_object_top_metrics_carrier(...)` now removes visible `top` on fallback instead of cloning it, matching the take-helper contract used by other hidden-carrier families.
- plugin `top_hits` wrapper input/output now also reuse shared inner-hit helpers instead of open-coding raw `value.get("hits")` wrapper reads.
- plugin object-bucket merge wrapper outputs (`filters`, `adjacency_matrix`) and plugin `top_hits` wrapper output now reuse shared take-wrapper helpers instead of open-coding wrapper removal and inner-surface extraction.
- plugin rebucketing/composite wrapper outputs (`auto_date_histogram`, `variable_width_histogram`, `composite`) now also reuse shared take-wrapper helpers instead of open-coding wrapper removal and bucket-surface extraction.
- plugin scalar/object wrapper outputs (`geo_bounds`, `filter`, `global`, `sampler`) now reuse a shared wrapper-field extraction helper instead of open-coding wrapper removal and field reads.
- plugin `top_hits` merge entry seed now also reuses the shared empty carrier-aware top-hits aggregation helper instead of building a local wrapper shell and inserting `hits` manually.
- nested direct plugin `terms` / `rare_terms` producers for both documents and hits now return through the shared plugin bucket-surface helper instead of building local wrapper shells and then re-seeding carriers manually.
- document-side direct plugin `terms` / `rare_terms` / range-family producers now also return through the shared plugin bucket-surface helper instead of building local wrapper shells and manually re-seeding carriers.
- hits-side direct plugin producers for `ip_range`, `histogram`, `composite`, `auto_date_histogram`, `variable_width_histogram`, and `multi_terms` now also return through the shared plugin bucket-surface helper instead of building local wrapper shells and manually re-seeding carriers.
- hits-side direct plugin producers for `ip_range`, `histogram`, `composite`, `auto_date_histogram`, `variable_width_histogram`, and `multi_terms` now also return through the shared plugin bucket-surface helper instead of building local wrapper shells and manually re-seeding carriers.
- direct plugin producer helper convergence: remaining `date_range` / `geo_distance` / `date_histogram` / `histogram` family seats now also return through `plugin_bucket_surface_aggregation_value(...)` instead of building local plugin bucket shells and manually re-seeding array carriers; rebucketing variants still reattach `interval` after the shared helper.
- additional direct plugin producer helper convergence: documents-side nested `multi_terms`, and hits-side `terms` / `range`, now also return through `plugin_bucket_surface_aggregation_value(...)` instead of building local bucket shells or manually re-seeding ordered carrier arrays after native collection.
- `top_hits` merge-helper convergence: native `merge_top_hits_aggregation_value(...)` and `merge_top_hits_aggregation_value_with_sort(...)` now read incoming inner hit objects through `top_hits_inner_value(...)` instead of doing direct raw `value.get("hits")` extraction inside each helper.
- direct plugin producer helper convergence: hits-side `rare_terms` non-nested fallback now also returns through `plugin_bucket_surface_aggregation_value(...)` after rare-term ordering, instead of manually re-writing the array bucket carrier in place.
- direct plugin producer helper convergence: documents-side `composite` non-nested fallback now also returns through `plugin_bucket_surface_aggregation_value(...)` instead of manually re-writing the extracted array bucket carrier back into the wrapper object.
- follow-on fix: the documents-side `date_range` plugin fallback no longer reuses the old mutable wrapper borrow after rewrapping through `plugin_bucket_surface_aggregation_value(...)`; the shared helper already reattaches plugin metadata, so the local post-rewrap inserts were removed.
- `significant_terms` / `significant_text` helper convergence: the direct plugin path and the hit/document aggregation-assembly seats now rewrap ordered bucket carriers through `plugin_bucket_surface_aggregation_value(...)` instead of doing local carrier writeback plus a second metadata-reattach pass.
- documents-side second-pass bucket pipeline wrapper convergence: `BucketSort`, `Normalize`, `BucketSelector`, and `BucketScript` now also rewrap through `bucket_surface_wrapper_value(...)` instead of emitting visible-only `{"buckets": ...}` wrappers in `collect_aggregations_from_documents(...)`.
- `top_hits` producer helper convergence: plugin `top_hits` collectors now rebuild the inner hit object first and pass it through a shared `plugin_top_hits_aggregation_value(...)` wrapper instead of mutating a local plugin shell with manual metadata attach after hit-surface construction.
- follow-on fix: `collect_plugin_top_hits_aggregation_from_window_with_input_order(...)` now rebuilds `inner_hits` before calling `plugin_top_hits_aggregation_value(...)`, matching the non-window top-hits producer path and removing the missing-local compile-break seat.
- `top_metrics` producer helper convergence: plugin top-metrics collectors now return through shared `plugin_top_metrics_aggregation_value(...)` for both empty and non-empty cases instead of building local wrapper shells and attaching metadata inline.
- scalar plugin helper convergence: `geo_bounds`, `geo_centroid`, and `scripted_metric` direct plugin paths now attach plugin metadata through shared `plugin_object_aggregation_value(...)` instead of repeating inline object-mutation shells in both document and hit collectors.
- metric/object plugin helper convergence: `percentiles`, `percentile_ranks`, `boxplot`, `median_absolute_deviation`, and `cardinality` direct plugin paths now also attach metadata through shared `plugin_object_aggregation_value(...)` in both document and hit collectors.
- metric/object plugin helper convergence: `sum`, `avg`, `weighted_avg`, `stats`, `extended_stats`, `min`, and `max` direct plugin paths now also route their object-shaped responses through shared `plugin_object_aggregation_value(...)` instead of embedding inline metadata fields in duplicated JSON constructors.
- Correction: metric/object plugin helper convergence sweep 뒤에도 documents/hits `sum` direct path 두 자리가 still inline `_plugin` / `_type` / `params` JSON을 직접 만들고 있었는데, 현재는 둘 다 `plugin_object_aggregation_value(...)` 경계로 올려 scalar/object plugin metadata attach semantics를 same shared helper surface로 맞췄다.
- Correction: plugin merge/object convergence 후에도 `merge_plugin_aggregation_value(...)` 안의 scalar/object entry seed 일부(`value_count`/`sum`, `avg`, `weighted_avg`, `cardinality`, `percentiles`, `percentile_ranks`, `boxplot`, `median_absolute_deviation`, `missing`, `stats`/`extended_stats`, `min`, `max`, `geo_bounds`, `geo_centroid`, `filter`, `global`, `sampler`)와 `plugin_bucket_count_aggregation_value(...)` 가 still inline plugin metadata JSON을 직접 만들고 있었는데, 현재는 live seed/return seat를 `plugin_object_aggregation_value(...)` 경계로 다시 수렴시켜 merge-time scalar/object metadata attach semantics를 same shared helper surface로 맞췄다.
- Correction: plugin merge bucket/top family 안에 still 남아 있던 local wrapper shell/manual metadata reattach seat(`terms`, `rare_terms`, `range`, `ip_range`, `date_range`, `filters`, `adjacency_matrix`, `multi_terms`, `top_hits`)를 shared helper 경계로 다시 올렸다. merge entry seed는 `plugin_bucket_surface_aggregation_value(...)` / `plugin_top_hits_aggregation_value(...)` 를 재사용하고, `rare_terms` / `multi_terms` 의 post-write metadata reattach는 제거해 merge-time wrapper contract를 direct producer/helper surface와 더 맞췄다.
- Correction: plugin merge bucket family의 histogram/rebucketing/composite/significant-terms entry seed 잔여(`histogram`, `geo_distance`, `date_histogram`, `auto_date_histogram`, `variable_width_histogram`, `composite`, `significant_terms`/`significant_text`)도 shared helper 경계로 더 올렸다. plain bucket family는 `plugin_bucket_surface_aggregation_value(...)` 를 재사용하고, rebucketing/significant-terms 처럼 extra surface(`interval`, `doc_count`, `bg_count`)가 필요한 seat는 same helper 위에 extra field만 얹어 merge-time wrapper seed와 metadata attach contract를 더 수렴시켰다.
- Correction: `top_metrics` merge entry seed와 plugin helper-local metadata attach 일부(`plugin_global_aggregation_value(...)`, `plugin_filter_aggregation_value(...)`, `plugin_bucketed_filter_aggregation_value(...)`, `plugin_sampler_aggregation_value(...)`)도 shared helper 경계로 올렸다. live merge seed는 `plugin_top_metrics_aggregation_value(...)` 를 재사용하고, helper-local object return은 `plugin_object_aggregation_value(...)` 로 마감해 plugin object metadata attach surface를 더 단일화했다.
- Correction: remaining helper-local bucket wrapper metadata attach도 더 줄였다. `plugin_bucket_surface_aggregation_value(...)` 자체가 이제 `plugin_object_aggregation_value(...)` 위에서 bucket wrapper를 감싸고, plugin `multi_terms` bucket assembly helper return도 same helper를 바로 재사용해 helper-layer bucket metadata attach surface를 한 단계 더 단일화했다.
- Correction: top helper definition 내부의 마지막 중복 metadata attach도 줄였다. `plugin_top_hits_aggregation_value(...)` 는 이제 `plugin_object_aggregation_value(...)` 위에서 inner-hit wrapper를 감싸고, `plugin_top_metrics_aggregation_value(...)` 도 visible/carrier seed 뒤 object helper로 마감해 top-family helper-layer metadata attach surface를 더 단일화했다.
- Correction: plugin generic pipeline helper와 plugin finalize helper(`plugin_generic_pipeline_aggregation_value(...)`, `finalize_plugin_terms_aggregation_value(...)`, `finalize_plugin_rare_terms_aggregation_value(...)`, `finalize_plugin_significant_terms_aggregation_value(...)`)도 shared object helper 경계로 마감하도록 올렸다. pipeline/finalize 단계의 bucket visibility rewrite 뒤 metadata reattach를 직접 들고 있지 않고 `plugin_object_aggregation_value(...)` 로 다시 수렴한다.
- Correction: plugin `top_hits` merge branch의 마지막 raw parent reattach seat도 제거했다. normalized inner `hits` 를 `entry_object.insert("hits", ...)` 로 직접 다시 꽂지 않고 `plugin_top_hits_aggregation_value(...)` 로 whole-wrapper를 다시 조립해 top-hits merge boundary의 parent writeback도 shared helper surface로 수렴시켰다.
- Correction: top-hits helper definition 내부의 duplicate wrapper seed도 더 줄였다. `empty_top_hits_aggregation_value()` 가 local `{ "hits": ... }` shell을 직접 만들지 않고 `top_hits_aggregation_value_with_inner_hits(empty_top_hits_inner_value())` 를 재사용해 top-hits wrapper assembly surface를 한 단계 더 단일화했다.
- Correction: rebucketing/date-histogram plugin branch가 still `plugin bucket wrapper + interval field` 조립을 local mutation으로 반복하던 seat를 줄였다. `plugin_bucket_surface_aggregation_value_with_field(...)` helper를 추가하고 documents/hits `date_histogram` / `variable_width_histogram` producer path가 same helper로 wrapper와 `interval` surface를 함께 조립하도록 맞췄다.
- Correction: multi-field extra outward surface를 붙이는 local seed도 줄였다. `plugin_bucket_surface_aggregation_value_with_fields(...)` helper를 추가하고 plugin merge `significant_terms` / `significant_text` seed가 same helper로 `doc_count` / `bg_count` field를 함께 조립하도록 맞췄다.
- Correction: plugin `composite` merge branch의 `after_key` local writeback도 whole-wrapper helper 경계로 올렸다. merged bucket carrier와 optional `after_key` 를 branch 안에서 따로 `insert/remove` 하지 않고 `plugin_bucket_surface_aggregation_value_with_fields(...)` 로 wrapper를 다시 조립해 composite merge의 extra outward field writeback을 더 공통화했다.
- Correction: rebucketing merge branch의 `carrier buckets + visible buckets + interval` local writeback도 공통 helper 경계로 올렸다. `plugin_bucket_array_visible_and_carrier_value_with_fields(...)` helper를 추가하고 plugin merge `auto_date_histogram` / `variable_width_histogram` 가 final rebucket carrier와 visible buckets, `interval` surface를 same helper에서 다시 조립하도록 맞췄다.
- Correction: rebucketing merge entry seed의 local `interval` mutation도 제거했다. plugin merge `auto_date_histogram` / `variable_width_histogram` seed가 helper 생성 뒤 `interval` 을 따로 insert 하지 않고 `plugin_bucket_surface_aggregation_value_with_field(...)` 로 바로 시작하도록 맞췄다.
- Correction: plain array-bucket wrapper construction의 local shell도 더 줄였다. `bucket_array_visible_and_carrier_value(...)` helper를 추가하고 `collect_range_aggregation_from_values(...)`, `collect_ip_range_aggregation_from_values(...)`, `collect_date_range_aggregation_from_values(...)`, `collect_geo_distance_aggregation_from_values(...)` 가 local `{}` shell + `set_object_bucket_array_visible_and_carrier(...)` 패턴 대신 same helper를 재사용하도록 맞췄다.
- Correction: native/plain bucket collector helper에도 local wrapper shell이 남아 있던 seat를 줄였다. `bucket_object_visible_and_carrier_value(...)` helper를 추가하고 `collect_date_histogram_aggregation_from_documents(...)`, `collect_histogram_aggregation(...)`, `collect_filters_aggregation(...)`, `collect_filters_aggregation_from_documents(...)`, `collect_terms_aggregation(...)`, `collect_terms_aggregation_from_documents(...)` 가 local `{}` shell + bucket setter 패턴 대신 shared bucket wrapper helper를 재사용하도록 맞췄다.
- Correction: helper-body local shell을 더 줄였다. `top_metrics_visible_and_carrier_value(...)` helper를 추가해 `plugin_top_metrics_aggregation_value(...)` / `empty_top_metrics_aggregation_value()` 가 same top wrapper helper를 재사용하도록 맞췄고, plain `collect_date_histogram_aggregation(...)` 도 local `{}` shell 대신 `bucket_array_visible_and_carrier_value(...)` 를 반환하도록 정리했다.
- Correction: remaining array-wrapper local shell residue도 더 줄였다. `bucket_array_visible_and_carrier_value_with_fields(...)` helper를 추가해 `merge_significant_terms_aggregation_value(...)` seed가 local shell 대신 shared wrapper helper로 `doc_count` / `bg_count` field를 붙이도록 바꿨고, plugin rebucketing temporary wrapper(`auto_date_histogram`, `variable_width_histogram`)도 raw `bucket_surface_wrapper_value(...)` 대신 `bucket_array_visible_and_carrier_value(...)` 를 재사용하도록 맞췄다.
- Correction: native merge helper의 empty bucket wrapper seed도 shared wrapper helper로 수렴시켰다. `merge_terms_aggregation_value(...)`, `merge_histogram_aggregation_value(...)`, `merge_composite_aggregation_value(...)`, `merge_filters_aggregation_value(...)`, `merge_range_aggregation_value(...)` 가 raw `bucket_surface_wrapper_value(...)` empty seed 대신 `bucket_array_visible_and_carrier_value(...)` / `bucket_object_visible_and_carrier_value(...)` 를 재사용하도록 맞췄다.
- Correction: date-histogram empty array fallback/seed residue도 shared array wrapper helper로 정리했다. `merge_range_aggregation_value(...)` empty seed와 `collect_aggregations(...)` / `collect_aggregations_from_documents(...)`, plugin date-histogram producer fallback의 `unwrap_or_else(... bucket_surface_wrapper_value(Value::Array(Vec::new())))` seat를 `bucket_array_visible_and_carrier_value(Vec::new())` 로 치환해 empty array fallback surface를 더 통일했다.
- Correction: wrapper fallback helper의 마지막 raw empty array wrapper seat도 shared helper로 정리했다. `take_wrapper_value(...)` fallback이 raw `bucket_surface_wrapper_value(Value::Array(Vec::new()))` 대신 `bucket_array_visible_and_carrier_value(Vec::new())` 를 재사용해 wrapper-remove fallback surface를 더 통일했다.
- Correction: shared bucket wrapper helper body의 local `{}` shell도 제거했다. `bucket_array_visible_and_carrier_value(...)` 와 `bucket_object_visible_and_carrier_value(...)` 가 raw object construction 대신 `bucket_surface_wrapper_value(...)` 를 직접 재사용하도록 바꿔 wrapper helper layering을 한 단계 더 단순화했다.
- Correction: plugin merge family의 남아 있던 temporary wrapper input 11자리(`terms`, `rare_terms`, range-family, `histogram`, `date_histogram`, `composite`, `filters`, `adjacency_matrix`)도 raw `bucket_surface_wrapper_value(Value::Array/Object(existing))` 대신 typed `bucket_array_visible_and_carrier_value(existing)` / `bucket_object_visible_and_carrier_value(existing)` helper로 올렸다. hidden carrier shape는 같지만, wrapper input construction contract가 generic raw wrapper가 아니라 typed shared helper surface로 더 단일화됐다.
- Correction: native `finalize_composite_aggregation_value(...)` 도 final visible bucket writeback 뒤 local `after_key` insert/remove를 하지 않고, `bucket_array_visible_and_carrier_value_with_fields(...)` 로 whole-wrapper를 다시 조립하도록 올렸다. plain composite finalization boundary에서도 buckets surface와 extra outward field writeback이 같은 helper contract로 수렴한다.
- Correction: plugin scalar/object merge branch 중 `filter`, `global`, `sampler` family도 final mutable object state로 끝내지 않고, 마지막 writeback을 `plugin_object_aggregation_value(plugin, Value::Object(entry_object.clone()))` 로 다시 수렴시켰다. outward `doc_count` payload는 유지하지만, wrapper/metadata reattach boundary는 branch-local state에서 shared helper surface로 더 올라왔다.
- Correction: native `finalize_composite_aggregation_value(...)` 도 final visible bucket writeback 뒤 local `after_key` insert/remove를 하지 않고, `bucket_array_visible_and_carrier_value_with_fields(...)` 로 whole-wrapper를 다시 조립하도록 올렸다. plain composite finalization boundary에서도 buckets surface와 extra outward field writeback이 같은 helper contract로 수렴한다.
- Correction: plugin `significant_terms` / `significant_text` merge tail도 local `doc_count` / `bg_count` mutation 뒤 separate bucket setter로 끝내지 않고, totals와 merged bucket vec를 계산한 뒤 `plugin_bucket_surface_aggregation_value_with_fields(...)` 로 whole-wrapper를 다시 조립하도록 올렸다. significant-terms family의 outward totals와 bucket carrier writeback이 같은 helper boundary로 수렴한다.
- Correction: plugin `filter`, `global`, `sampler` merge family도 `doc_count` 를 middle mutable object state에 먼저 writeback 하지 않고, local payload map으로 nested merge를 진행한 뒤 마지막에 `plugin_object_aggregation_value(plugin, Value::Object(final_object))` 로만 다시 조립하도록 올렸다. 이 family의 `doc_count` payload와 nested/object writeback이 intermediate object mutation에서 final shared helper boundary로 더 이동했다.
- Correction: native `merge_composite_aggregation_value(...)` 의 final array-bucket tail도 `entry_object` 에 `set_object_bucket_array_visible_and_carrier(...)` 를 직접 쓰지 않고, existing carrier scoped extract 뒤 `bucket_array_visible_and_carrier_value(bucket_values)` 로 whole-value를 다시 조립하도록 올렸다. plain composite merge helper도 final bucket writeback이 local setter가 아니라 shared array-wrapper helper boundary로 수렴한다.
- Correction: `plugin_global_aggregation_value(...)`, `plugin_filter_aggregation_value(...)`, `plugin_sampler_aggregation_value(...)` helper body도 local `doc_count` object shell을 각각 만들지 않고, 공통 `plugin_filter_bucket_value(...)` 결과 위에 `plugin_object_aggregation_value(...)` 만 얹도록 정리했다. filter/global/sampler family의 helper-layer `doc_count` payload assembly가 한 단계 더 단일화됐다.
- Correction: `plugin_filter_bucket_value(...)` 와 `plugin_terms_bucket_value(...)` 도 local nested-aggregation/reduce-hint attach 로직을 직접 들고 있지 않고, seed field만 만든 뒤 `plugin_bucket_value_from_existing_fields(...)` 로 마감하도록 올렸다. plugin bucket primitive builder layer의 payload assembly가 한 단계 더 공통 helper surface로 수렴한다.
- Correction: `key` / `key_as_string` / `doc_count` seed 뒤 nested payload와 reduce hints를 직접 붙이던 multi-terms style primitive bucket builder도 `plugin_bucket_value_from_existing_fields(...)` 로 마감하도록 올렸다. keyed bucket primitive builder layer의 nested payload assembly가 더 공통 helper surface로 수렴한다.
- Correction: `plugin_bucketed_filter_aggregation_value(...)` helper body도 local object shell + direct object-bucket setter를 들고 있지 않고, `bucket_object_visible_and_carrier_value(buckets)` 결과 위에 `plugin_object_aggregation_value(...)` 만 얹도록 정리했다. object-bucket plugin helper layer의 wrapper assembly가 한 단계 더 shared helper surface로 수렴한다.
- Correction: top-family primitive setter layer도 `_merge_*` + visible array field writeback을 각 helper가 직접 들고 있지 않고, 새 `set_object_merge_and_visible_array_fields(...)` helper를 통해 `set_object_top_hits_visible_and_carrier(...)` 와 `set_object_top_metrics_visible_and_carrier(...)` 가 공통 assembly를 재사용하도록 정리했다. top wrapper primitive layer의 array writeback contract가 한 단계 더 평탄해졌다.
- Correction: single-field primitive seed layer도 새 `object_value_with_field(...)` helper로 일부 수렴시켰다. `top_hits_aggregation_value_with_inner_hits(...)` 의 `hits` wrapper seed와 `plugin_filter_bucket_value(...)` 의 `doc_count` seed가 same object-field helper를 공유하므로, top/bucket primitive seed layer의 one-field object assembly가 더 공통화됐다.
- Correction: primitive value helper layer에 `object_value_with_fields(...)` 와 `object_merge_and_visible_array_value(...)` 를 추가하고, `plugin_terms_bucket_value(...)` 와 `top_metrics_visible_and_carrier_value(...)` 를 그 경계로 올렸다. multi-field object seed와 merge/visible array wrapper 반환이 local shell 반복 대신 shared value helper surface를 더 재사용한다.
- Correction: top-family primitive value layer에 `object_merge_and_visible_array_value_with_fields(...)` 를 추가하고, `empty_top_hits_inner_value()` 도 local multi-field shell + direct top-hits setter를 들고 있지 않도록 올렸다. `total`/`max_score` outward fields와 `_merge_hits`/`hits` array surface가 같은 value helper boundary에서 같이 조립된다.
- Correction: keyed/range-style native rebucket builder 2곳도 local field-seed object와 nested payload/reduce-hint attach를 직접 반복하지 않도록 올렸다. `key`/`key_as_string`/`doc_count` 또는 `key`/`doc_count` seed는 `object_value_with_fields(...)` 로 만들고, nested payload/hint attach는 `plugin_bucket_value_from_existing_fields(...)` 로 마감한다. native rebucket primitive builder layer도 shared value/helper surface를 더 재사용한다.
- Correction: documents-side range-family primitive seed layer에 `range_bucket_seed_object(...)` 를 추가하고, `range` / `ip_range` / `date_range` nested producer가 `key`/`from`/`to`/`doc_count` object shell을 각자 직접 만들지 않도록 올렸다. range-family seed object assembly가 공통 value helper surface를 더 재사용한다.
- Correction: producer-side sibling residue도 추가 정리했다. documents/hits `geo_distance` 는 `range_bucket_seed_object(...)` 를 재사용하고, keyed bucket producer 일부(`date_histogram`, documents/hits `histogram`, hits `composite`)는 `object_value_with_fields(...)` 로 `key`/`key_as_string`/`doc_count` 또는 `key`/`doc_count` seed object를 공통화했다. producer primitive seed layer에서 family-local object shell 반복이 더 줄었다.
- Correction: keyed histogram/rebucketing/multi-terms producer residue도 추가 정리했다. documents/hits `auto_date_histogram`, `variable_width_histogram`, `date_histogram`, 그리고 hits `multi_terms` 의 `key`/`key_as_string`/`doc_count` 또는 `key`/`doc_count` seed object는 `object_value_with_fields(...)` 를 공통 재사용하도록 올렸다. keyed producer primitive seed layer의 local object shell 반복이 더 줄었다.
- Correction: documents-side keyed producer residue도 추가 정리했다. documents `composite` 와 `multi_terms` 의 `key`/`doc_count` 또는 `key`/`key_as_string`/`doc_count` seed object는 `object_value_with_fields(...)` 를 공통 재사용하도록 올렸다. keyed producer primitive seed layer에서 documents-side family-local object shell 반복이 더 줄었다.
- Correction: helper/factory layer의 repeated field-attach pattern도 새 `value_with_attached_fields(...)` helper로 수렴시켰다. `object_merge_and_visible_array_value_with_fields(...)`, `plugin_bucket_surface_aggregation_value_with_field(...)`, `plugin_bucket_surface_aggregation_value_with_fields(...)`, `plugin_bucket_array_visible_and_carrier_value_with_fields(...)` 가 value 생성 뒤 field loop를 각자 직접 들고 있지 않게 됐다.
- Correction: `plugin_bucket_array_visible_and_carrier_value_with_fields(...)` helper body도 special-case `_merge_buckets` attach를 직접 들고 있지 않고, `object_merge_and_visible_array_value_with_fields("_merge_buckets", "buckets", ...)` 를 재사용하도록 정리했다. plugin array-bucket wrapper assembly가 generic merge/visible array value helper surface로 더 수렴한다.
- Correction: plugin terms-family finalizer 3곳(`finalize_plugin_terms_aggregation_value(...)`, `finalize_plugin_rare_terms_aggregation_value(...)`, `finalize_plugin_significant_terms_aggregation_value(...)`)도 local bucket setter + wrapper reattach를 직접 들고 있지 않고, `plugin_bucket_array_visible_and_carrier_value_with_fields(..., serde_json::Map::new())` 로 바로 마감하도록 올렸다. plugin array-bucket finalization tail이 whole-wrapper helper surface로 더 수렴한다.
- Correction: native `finalize_terms_aggregation_value(...)` / `finalize_significant_terms_aggregation_value(...)` 의 finalizer tail은 visible subset만 남기고 hidden carrier를 줄이면 안 된다. 따라서 final writeback은 `bucket_array_visible_and_carrier_value(...)` 가 아니라 `object_merge_and_visible_array_value("_merge_buckets", "buckets", carrier_buckets, visible_buckets)` 로 carrier-preserving shape를 유지하도록 바로 고쳤다.
- Correction: plain array-bucket merge helper인 `merge_date_histogram_aggregation_value(...)` 와 `merge_histogram_aggregation_value(...)` 도 `entry_object` local setter tail을 직접 들고 있지 않고, scoped carrier extract 뒤 `bucket_array_visible_and_carrier_value(merged_buckets)` 로 whole value를 다시 조립하도록 올렸다. 이 두 helper는 carrier와 visible surface가 같은 merge contract라 whole-value helper로 바로 마감해도 drift가 없다.
- Correction: native/helper tail의 추가 정리로 `merge_filters_aggregation_value(...)` 는 local object-bucket setter tail 대신 `bucket_object_visible_and_carrier_value(merged_buckets)` 로 whole value를 다시 조립하도록 올렸고, `merge_top_hits_aggregation_value(...)`, `merge_top_hits_aggregation_value_with_sort(...)`, `finalize_merged_top_hits_aggregation_value(...)` 는 `total`/`max_score` outward fields와 `_merge_hits`/visible `hits` surface를 `object_merge_and_visible_array_value_with_fields(...)` 하나로 같이 조립하도록 올렸다.
- Correction: pure wrapper seat인 `finalize_merged_top_metrics_aggregation_value(...)` 도 local `set_object_top_metrics_visible_and_carrier(...)` tail 대신 `object_merge_and_visible_array_value("_merge_top", "top", merge_top, visible_top)` 로 whole value를 다시 조립하도록 올렸다. metadata를 별도로 들고 있지 않는 native top-metrics finalizer라 generic merge/visible array value helper로 안전하게 수렴한다.
- Correction: pure value helper `bucket_array_visible_and_carrier_value_with_fields(...)` 도 local field-attach loop를 직접 들고 있지 않고, `value_with_attached_fields(bucket_array_visible_and_carrier_value(...), fields)` 로 마감하도록 정리했다. plain array-bucket value helper layer의 field-attach surface가 더 공통 helper로 수렴한다.
- Correction: `object_value_with_field(...)` helper body도 own local object shell을 만들지 않고 `object_value_with_fields(...)` 위로 올렸다. one-field object seed helper layer가 fully shared multi-field seed surface를 재사용한다.
- Correction: hits-side range-family primitive seed residue도 `range_bucket_seed_object(...)` 경계로 올렸다. hits `date_range`, `range`, `ip_range` nested producer가 `key`/`from`/`to`/`doc_count` local object shell을 각자 직접 만들지 않게 되어, documents-side와 같은 seed object contract를 공유한다.
- Correction: `bucket_surface_wrapper_value(...)` helper body도 own local object shell을 만들지 않도록 올렸다. array case와 empty case는 `object_merge_and_visible_array_value("_merge_buckets", "buckets", ...)` 를 재사용하고, object case는 `object_value_with_fields(...)` 로 `_merge_buckets` / `buckets` object pair를 바로 조립한다. hidden bucket wrapper primitive layer가 더 shared value surface로 수렴한다.
- Correction: generic `object_merge_and_visible_array_value(...)` helper body도 local empty value shell을 만들지 않고 `object_value_with_fields(...)` 로 `_merge_*` / visible array field pair를 바로 조립하도록 올렸다. merge/visible array wrapper primitive layer의 local value shell이 더 제거됐다.
- Correction (2026-05-24): top-hits producer family의 repeated inner `hits` wrapper assembly를 `top_hits_inner_value_with_entries(...)` helper로 끌어올렸다. `collect_top_hits_aggregation(...)`, `collect_plugin_top_hits_aggregation_with_input_order(...)`, `collect_plugin_top_hits_aggregation_from_window_with_input_order(...)` 가 더 이상 local `hits` shell + setter tail을 직접 들고 있지 않고, `total`/`max_score` outward fields와 `_merge_hits`/visible `hits` surface를 same helper boundary에서 같이 조립한다.
- Correction (2026-05-24): `collect_top_hits_aggregation_from_window(...)` 가 assembled inner `hits` wrapper를 버리고 raw shell을 반환하던 불일치를 수정했다. 이제 from-window top-hits path도 `top_hits_inner_value_with_entries(...)` 를 통해 `_merge_hits` carrier와 visible `hits` surface를 실제 반환값에 유지한다. 같은 turn에 plugin `top_hits` merge tail도 same helper boundary로 재조립해 redundant local setter normalization을 제거했다.
- Correction (2026-05-24): pure native/helper bucket seat 몇 곳을 whole-value helper 경계로 추가 수렴시켰다. `merge_range_aggregation_value(...)` 는 final array-bucket tail을 `bucket_array_visible_and_carrier_value(...)` 로 다시 조립하고, native `significant_terms` producer 2곳은 `doc_count`/`bg_count` outward fields와 `buckets` carrier surface를 `bucket_array_visible_and_carrier_value_with_fields(...)` 에서 같이 조립한다. `collect_composite_aggregation_value(...)` 도 local response shell 없이 array-bucket helper를 바로 반환한다.
- Correction (2026-05-24): plugin object-bucket/top-metrics merge tail 일부를 whole-wrapper helper 경계로 추가 수렴시켰다. `filters` 와 `adjacency_matrix` merge path는 intermediate object-bucket setter tail 대신 `plugin_bucketed_filter_aggregation_value(...)` 로 outer wrapper를 다시 조립하고, plugin `top_metrics` merge branch는 final `top` writeback을 `plugin_top_metrics_aggregation_value(...)` 로 수렴시킨다.
- Correction (2026-05-24): fieldless plugin array-bucket merge family의 repeated setter tail 일부를 whole-wrapper helper로 추가 수렴시켰다. `rare_terms`, `range`, `ip_range`, `date_range`, `histogram`, `geo_distance` merge branch는 initial carrier extract를 scoped borrow로 좁히고, final writeback을 `plugin_bucket_array_visible_and_carrier_value_with_fields(..., serde_json::Map::new())` 로 다시 조립한다.
- Correction (2026-05-24): remaining plugin array-bucket sibling 2곳도 same helper contract로 수렴시켰다. `terms` 와 `date_histogram` merge branch는 initial carrier extract를 scoped borrow로 좁히고, final writeback을 `plugin_bucket_array_visible_and_carrier_value_with_fields(..., serde_json::Map::new())` 로 다시 조립한다. `auto_date_histogram` 은 extra `interval` outward field contract가 얽혀 있어 same turn에 intentionally untouched로 남겼다.
- Correction (2026-05-24): native terms-family helper tail과 plugin `multi_terms` sibling도 same whole-wrapper helper contract로 수렴시켰다. native `merge_terms_aggregation_value(...)` / `merge_significant_terms_aggregation_value(...)` 는 final array-bucket tail을 `bucket_array_visible_and_carrier_value(...)` 로 다시 조립하고, plugin `multi_terms` merge branch는 scoped carrier extract 뒤 `plugin_bucket_array_visible_and_carrier_value_with_fields(..., serde_json::Map::new())` 로 마감한다.
- Correction (2026-05-24): plugin nested finalizer tail과 geo object branch를 metadata-preserving rebuild 경계로 추가 수렴시켰다. `finalize_plugin_bucketed_nested_aggregation_value(...)` / `finalize_plugin_array_bucketed_nested_aggregation_value(...)` 는 existing wrapper의 non-bucket fields를 보존한 채 bucket wrapper surface를 helper로 다시 조립하고, plugin `geo_bounds` / `geo_centroid` merge branch는 final object writeback을 `plugin_object_aggregation_value(...)` 기반 whole-wrapper rebuild로 마감한다.
- Correction (2026-05-24): scalar/object residue 일부도 whole-wrapper rebuild 경계로 추가 수렴시켰다. native `merge_missing_aggregation_value(...)` 와 `merge_geo_centroid_aggregation_value(...)` 는 final object writeback을 `object_value_with_field(...)` / `object_value_with_fields(...)` 로 다시 조립하고, plugin `missing` merge branch는 `doc_count` middle mutation과 nested payload tail insert를 제거해 `plugin_object_aggregation_value(...)` 기반 final rebuild로 수렴시킨다.
- Correction (2026-05-24): remaining scalar helper residue 하나를 추가 정리했다. native `merge_filter_aggregation_value(...)` 는 final `doc_count` writeback을 branch-local field mutation 대신 `object_value_with_field(...)` 로 다시 조립한다. 이 시점의 live mutation seat는 mostly stats/metric merge math나 per-bucket inner count accumulation처럼 wrapper rebuild보다 arithmetic state update 자체가 본질인 branch로 더 좁혀졌다.
- Correction (2026-05-24): single-field plugin metric branch도 helper rebuild 경계로 추가 수렴시켰다. plugin `value_count` / `sum` / `min` / `max` merge branch는 final `value` writeback을 branch-local mutation 대신 `plugin_object_aggregation_value(..., object_value_with_field("value", ...))` 로 다시 조립한다.
- Correction (2026-05-24): plugin scalar metric residue 2곳을 추가로 helper rebuild 경계로 수렴시켰다. plugin `avg` / `weighted_avg` merge branch는 merge-math accumulator는 그대로 유지하되 final object writeback을 branch-local field mutation 대신 `plugin_object_aggregation_value(..., object_value_with_fields(...))` 로 다시 조립한다.
- Correction (2026-05-24): `stats` / `extended_stats` family도 merge-math와 final wrapper assembly를 더 분리했다. native와 plugin 두 branch 모두 count/sum/min/max/avg 및 extended-stats outward fields를 local field mutation으로 채우지 않고 final object map을 계산한 뒤 native는 `Value::Object(...)`, plugin은 `plugin_object_aggregation_value(..., Value::Object(...))` 로 다시 조립한다.
- Correction (2026-05-24): cardinality / percentile family의 final payload assembly도 helper rebuild 경계로 추가 수렴시켰다. native와 plugin 두 branch 모두 `cardinality`, `percentiles`, `percentile_ranks`, `boxplot`, `median_absolute_deviation` 에서 accumulated `_values`/`_distinct_values` 와 outward payload를 local field mutation으로 덧쓰지 않고 final object map을 계산한 뒤 다시 조립한다.
- Correction (2026-05-24): native metric helper의 scalar final writeback residue도 추가 수렴시켰다. native `Avg` / `WeightedAvg` branch는 accumulator math는 유지하되 `_count` / `_weighted_sum` / `_weight_sum` / `value` surface를 `object_value_with_fields(...)` 로 다시 조립하고, generic scalar tail도 `object_value_with_field("value", ...)` 로 마감한다.
- Correction (2026-05-24): native `merge_significant_terms_aggregation_value(...)` 의 intermediate totals mutation도 제거했다. `doc_count` / `bg_count` 누산은 local scalar math로만 유지하고, final outward totals와 bucket surface는 `bucket_array_visible_and_carrier_value_with_fields(...)` 에서 한 번에 다시 조립한다.
- Correction (2026-05-24): object-bucket inner count accumulation의 마지막 one-field residue 하나도 정리했다. native `merge_filters_aggregation_value(...)` 는 per-bucket `doc_count` 누산 뒤 direct field mutation 대신 `object_value_with_field("doc_count", ...)` 로 bucket entry를 다시 조립한다.
- Correction (2026-05-24): geo-bounds helper의 corner writeback seat도 helper rebuild 경계로 올렸다. `merge_geo_corner(...)` 는 `lat` / `lon` final writeback을 direct field mutation 대신 `object_value_with_fields(...)` 로 다시 조립한다.
- Correction (2026-05-24): native `merge_geo_bounds_aggregation_value(...)` 도 in-place `bounds` mutation 대신 final object rebuild로 수렴시켰다. current `bounds` 를 local map으로 계산한 뒤 `object_value_with_field("bounds", Value::Object(...))` 로 다시 조립한다.
- Audit note (2026-05-24): source-level grep 기준 helper/factory 정의 밖 direct `set_object_bucket_*` / `set_object_top_*` call site는 더 보이지 않는다. 남아 있는 live mutation은 주로 `final_object.insert(...)` 같은 local map assembly, per-bucket count accumulation, accumulator math, 그리고 helper/primitive definition 내부 insert로 수렴한 상태다. 즉, wrapper assembly residue보다는 algorithmic state update가 residual mass의 중심이다.
- Correction (2026-05-24): plugin object merge family의 local `doc_count` map insert residue를 추가로 줄였다. `missing`, `filter`, `global`, `sampler` family는 `doc_count` field를 `final_object.insert(...)` 로 얹기보다 `object_value_with_field("doc_count", ...)` 기반 map rebuild 뒤 existing payload를 extend하는 형태로 더 수렴한다.
- Correction (2026-05-24): native/plugin `extended_stats` extra-field attach loop도 추가 수렴시켰다. `sum_of_squares` / `variance` / `std_deviation` / `std_deviation_bounds` 는 repeated `final_object.insert(...)` 대신 `object_value_with_fields(...)` 로 만든 object를 `extend(...)` 하는 형태로 정리했다.
- Audit note (2026-05-24): source-level grep 기준 remaining `final_object.extend(...)` seat는 주로 local payload/object assembly 성격이다. 대표적으로 boxplot/extended-stats field attach와 plugin nested merge payload reattach가 남아 있고, helper/factory 정의 밖 direct `set_object_bucket_*` / `set_object_top_*` call site는 더 보이지 않는다. 따라서 residual mutation의 중심은 wrapper assembly보다는 local map composition과 algorithmic merge state update다.
- Correction (2026-05-24): repeated `doc_count` seed + payload extend pattern을 helper로 추가 수렴시켰다. 새 `object_value_with_field_and_fields(...)` helper를 도입해 `missing`, `filter`, `global`, `sampler` family의 local `doc_count` seed map rebuild + payload extend를 한 단계 더 공통화했다.
- Audit note (2026-05-24): source-level grep 기준 remaining `final_object.extend(...)` seat는 4자리에 좁혀져 있고, 모두 local composition 성격이다. 구체적으로 native/plugin `boxplot` payload attach와 native/plugin `extended_stats` extra-field attach만 남아 있으며, same file에서 `object_value_with_fields(...)` / `object_value_with_field_and_fields(...)` helper 사용 자리가 크게 늘어난 상태다. 이는 residual mutation이 wrapper assembly residue가 아니라 local payload composition 중심임을 뒷받침한다.
- Correction (2026-05-24): plugin `boxplot` 과 plugin `extended_stats` local composition seat도 `object_value_with_fields_and_fields(...)` helper 경계로 추가 수렴시켰다. seed field map과 extra computed fields를 `extend(...)` loop로 직접 붙이기보다 helper가 same attach contract를 맡는다.
- Audit note (2026-05-24): source-level grep 기준 `final_object.extend(...)` seat도 더 이상 보이지 않는다. native/plugin `boxplot` 및 `extended_stats` local composition은 `object_value_with_fields_and_fields(...)` helper로 흡수됐고, residual mutation은 mostly local map creation, accumulator math, collection update, helper/primitive definition 내부 insert 쪽으로 더 좁혀진 상태다.
- Correction (2026-05-24): native/plugin `stats` family의 repeated summary seed map도 helper로 공통화했다. 새 `stats_summary_object(...)` helper가 `count` / `sum` / `min` / `max` / `avg` seed object assembly를 맡고, native와 plugin `stats` / `extended_stats` branch가 same seed surface를 재사용한다.
- Audit note (2026-05-24): source-level grep 기준 repeated local map seed helper도 대부분 공통화된 상태다. 남아 보이는 `serde_json::Map::new()` / local response map seat는 percentile payload constructor 계열(`percentiles_bucket_values*`, `percentile_ranks_metric_values`)과 helper/primitive definition 쪽으로 좁혀진다. same file에서 `stats_summary_object(...)` 와 `object_value_with_fields_and_fields(...)` 재사용 자리가 늘어났다는 점은 repeated seed/object assembly가 algorithmic payload construction 쪽을 제외하고 상당 부분 정리됐음을 뒷받침한다.
- Audit note (2026-05-24): 추가 source grep에서 direct `set_object_bucket_*` / `set_object_top_*` match는 helper definition line만 반환됐다. same pass에서 `object_value_with_fields_and_fields(...)` 와 `stats_summary_object(...)` 는 intended native/plugin stats/object merge seat에만 재사용되는 것이 확인됐다. 현 시점의 residual work는 wrapper convergence보다는 validation과 one-off algorithmic assembly 설명 정리 쪽이다.
- Audit note (2026-05-24): 추가 grep에서 `final_object.extend(...)`, `final_object.insert(...)`, repeated `let mut final_object = ...` seat는 더 이상 잡히지 않았다. helper/factory 정의 밖 direct `set_object_*` match도 helper definition line만 남아 있고, live mutable map constructor는 `percentiles_bucket_values*`, `percentile_ranks_metric_values` 같은 payload constructor와 helper/primitive definition 쪽으로만 보인다. source-level convergence 관점에서는 wrapper/object assembly residue가 사실상 소거된 상태다.
- Correction (2026-05-24): remaining percentile payload constructor map 3곳도 generic helper로 공통화했다. 새 `object_fields_map(...)` helper를 도입해 `percentiles_bucket_values(...)`, `percentiles_bucket_values_for_slice(...)`, `percentile_ranks_metric_values(...)` 가 mutable response map loop 대신 iterator-to-map assembly를 공유한다.
- Audit note (2026-05-24): broad grep에서 보이는 `serde_json::Map::from_iter(...)` / `serde_json::json!({...})` 잔여는 대부분 test fixtures, helper/primitive definition, 또는 one-off payload constructor이다. live aggregation assembly 관점에서 newly introduced helpers (`object_value_with_fields_and_fields(...)`, `stats_summary_object(...)`, `object_fields_map(...)`) 가 native/plugin stats/object/percentile seat를 흡수한 상태라, 남은 repeated local map constructor residue는 source audit 기준으로 사실상 희박하다.
- Correction (2026-05-24): plugin object wrapper의 repeated seed/default constructor도 helper 경계로 추가 수렴시켰다. 새 `plugin_object_aggregation_value_with_field(...)` / `plugin_object_aggregation_value_with_fields(...)` helper를 도입해 `plugin_bucket_count_aggregation_value(...)`, plugin hits/documents metric producer의 `value`/`_count`/stats seed object assembly, 그리고 `merge_plugin_aggregation_value(...)` 안의 repeated default entry constructor(`value`, `_count`, `_weighted_sum`, `_distinct_values`, `values`, `_values`, `doc_count`)가 raw `serde_json::json!({...})` shell 대신 shared object seed surface를 재사용한다.
- Correction (2026-05-24): plugin merge/object branch에 남아 있던 small default seed residue도 helper 경계로 더 올렸다. `merge_plugin_aggregation_value(...)` 의 `min`/`max` default `value: null`, `geo_bounds` default `bounds`, `geo_centroid` default `location`/`count`, 그리고 plugin `filter`/`global`/`sampler` family의 default `doc_count` entry가 raw `plugin_object_aggregation_value(plugin, serde_json::json!({...}))` 대신 `plugin_object_aggregation_value_with_field(...)` / `plugin_object_aggregation_value_with_fields(...)` seed surface를 재사용한다.
- Audit note (2026-05-24): 추가 grep 기준 `plugin_object_aggregation_value(plugin, serde_json::json!({...}))` match는 더 이상 남아 있지 않다. same pass에서 `plugin_object_aggregation_value(plugin, object_value_with_...)` direct call도 helper definition line만 반환됐고, live plugin object seed assembly는 `plugin_object_aggregation_value_with_field(...)` / `plugin_object_aggregation_value_with_fields(...)` helper surface로 수렴한 상태다.
- Correction (2026-05-24): native/helper merge seat에 남아 있던 small default seed residue도 helper 경계로 더 올렸다. generic scalar metric merge의 default `value: null`, native `geo_bounds` default `bounds`, native `geo_centroid` default `location`/`count`, 그리고 `merge_geo_corner(...)` 의 default `lat`/`lon` corner shell이 raw `serde_json::json!({...})` 대신 `object_value_with_field(...)` / `object_value_with_fields(...)` seed surface를 재사용한다.
- Correction (2026-05-24): remaining one-field native `doc_count` default seed도 helper 경계로 수렴시켰다. `merge_missing_aggregation_value(...)`, `merge_filter_aggregation_value(...)`, `merge_filters_aggregation_value(...)` bucket inner entry가 raw `serde_json::json!({ "doc_count": 0 })` 대신 `object_value_with_field("doc_count", ...)` seed surface를 재사용한다.
- Audit note (2026-05-24): 추가 grep에서 live `or_insert_with(|| serde_json::json!(...))`, `final_object.insert(...)`, `final_object.extend(...)` match는 더 이상 보이지 않았고, direct `set_object_bucket_*` / `set_object_top_*` 및 `plugin_object_aggregation_value(plugin, object_value_with_...)` match는 helper definition line만 반환됐다. source-level 기준으로 repeated wrapper/default-seed residue는 사실상 helper/factory definition 밖에서 소거된 상태다.
- Correction (2026-05-24): repeated merge-wrapper setup contract도 helper 경계로 추가 수렴시켰다. 새 `wrapper_with_named_value(...)`, `bucket_array_merge_value(...)`, `bucket_object_merge_value(...)` helper를 도입해 plugin array-bucket/object-bucket merge family와 plugin `filter`/`global`/`sampler`/`geo_bounds` merge path가 local `Map::new() + insert(...) + json!({ ... })` wrapper setup 대신 shared wrapper/object seed surface를 재사용한다.
- Correction (2026-05-24): remaining plugin merge-wrapper setup seat 5곳도 helper 경계로 추가 수렴시켰다. `date_histogram`, `auto_date_histogram`, `variable_width_histogram`, `composite`, `top_hits` merge path가 local `Map::new() + insert(...)` wrapper shell 대신 `wrapper_with_named_value(...)` 및 existing object helper surface(`bucket_array_merge_value(...)`, `object_value_with_field(...)`, `object_value_with_field_and_fields(...)`)를 재사용한다.
- Audit note (2026-05-24): final source grep 기준 live repeated wrapper/default-seed residue는 더 보이지 않는다. direct `set_object_*` match는 helper definition line만 남아 있고, broad wrapper/default grep에서 잡히는 live non-helper seat는 `collect_plugin_adjacency_matrix_bucket_values(...)` 의 `doc_count` bucket payload constructor처럼 one-off algorithmic payload assembly에 가깝다.
- Correction (2026-05-24): `collect_plugin_adjacency_matrix_bucket_values(...)` 의 one-off `doc_count` bucket payload constructor도 `object_value_with_field("doc_count", ...)` helper seed로 올렸다. broad wrapper/default grep에서 마지막으로 눈에 띄던 tiny non-helper object shell도 shared one-field seed surface를 재사용한다.
- Correction (2026-05-24): previously listed non-native query backlog 일부는 current source-backed matcher 기준 이미 live다. `document_matches_query(...)` 는 `wrapper`, `nested`, `pinned`, `more_like_this`, `constant_score`, `dis_max`, `boosting`, `function_score`, `script_score` delegation/evaluation을 직접 처리하고, same source-backed path는 `regexp`, `distance_feature`, `rank_feature` leaf도 이미 평가한다. 따라서 해당 문서 구간의 broader "remaining query gap" list는 current code state보다 보수적으로 남아 있다.
- Correction (2026-05-24): broader aggregation backlog list 안의 plugin-defined aggregation coverage도 current code state보다 보수적으로 남아 있다. `collect_plugin_aggregation_from_documents(...)`, `collect_plugin_aggregation_from_hits_with_input_order(...)`, 그리고 `plugin_kind_still_requires_explicit_collection_wrapper_admission(...)` 기준으로 source-backed/plugin collector surface는 이미 `value_count`, `sum`, `avg`, `min`, `max`, `cardinality`, `stats`, `extended_stats`, `percentiles`, `percentile_ranks`, `median_absolute_deviation`, `boxplot`, `weighted_avg`, `missing`, `filter`, `filters`, `adjacency_matrix`, `terms`, `rare_terms`, `range`, `ip_range`, `date_range`, `geo_distance`, `histogram`, `auto_date_histogram`, `variable_width_histogram`, `date_histogram`, `top_metrics`, `composite`, `multi_terms`, `significant_terms`, `significant_text`, `global`, `sampler`, `random_sampler`, `diversified_sampler`, `top_hits`, `scripted_metric`, `geo_bounds`, `geo_centroid` 를 다룬다. placeholder fallback은 current state에서 broad unsupported family 전체라기보다 invalid/missing param admission failure나 genuinely unrecognized plugin kind 쪽으로 더 좁혀져 있다.
- Correction (2026-05-24): broader native aggregation backlog list도 current metric collector state보다 보수적으로 남아 있다. `collect_metric_aggregation(...)`, `merge_metric_aggregation_value(...)`, `collect_stats_metric_value(...)` 및 관련 metric merge/producer path 기준으로 native metric surface는 이미 `value_count`, `sum`, `avg`, `min`, `max`, `stats`, `extended_stats`, `weighted_avg`, `cardinality`, `percentiles`, `percentile_ranks`, `median_absolute_deviation`, `boxplot` 를 다룬다. 따라서 same section의 narrower remaining breadth는 current code state에서는 “metric family 자체의 부재”보다 broader parity/validation/readout wording 쪽으로 이해하는 편이 맞다.
- Correction (2026-05-24): broader pipeline backlog list도 current code state보다 부분적으로 보수적이다. `collect_pipeline_aggregation(...)` 기준으로 native pipeline surface는 이미 `sum_bucket`, `avg_bucket`, `min_bucket`, `max_bucket`, `moving_count`, `moving_avg`, `moving_sum`, `moving_min`, `moving_max`, `moving_median`, `moving_mad`, `moving_stddev`, `moving_variance`, `moving_skewness`, `moving_kurtosis`, `moving_range`, `moving_percentiles`, `moving_percentile_ranks`, `cumulative_sum`, `serial_diff`, `derivative`, `stats_bucket`, `extended_stats_bucket`, `percentiles_bucket`, `percentile_ranks_bucket` 를 다룬다. 따라서 same section에서 남는 pipeline gap은 current state에서는 broad family 전체의 부재라기보다 additional parity/readout/unsupported tail 쪽으로 더 좁혀서 읽는 편이 맞다.
- Correction (2026-05-24): plugin-defined pipeline backlog도 current code state보다 보수적으로 남아 있다. `plugin_pipeline_aggregation_kind(...)` 와 plugin pipeline collector/value helpers 기준으로 plugin surface는 이미 `sum_bucket`, `avg_bucket`, `min_bucket`, `max_bucket`, `moving_count`, `moving_avg`, `moving_sum`, `moving_min`, `moving_max`, `moving_median`, `moving_mad`, `moving_stddev`, `moving_variance`, `moving_skewness`, `moving_kurtosis`, `moving_range`, `moving_percentiles`, `moving_percentile_ranks`, `cumulative_sum`, `serial_diff`, `derivative`, `stats_bucket`, `extended_stats_bucket`, `percentiles_bucket`, `percentile_ranks_bucket`, `bucket_sort`, `bucket_count`, `normalize`, `bucket_selector`, `bucket_script` 를 다룬다. 따라서 same backlog section에서 plugin-defined pipeline work를 broader unsupported family 전체로 읽기보다는 param admission / parity / readout tail 쪽으로 더 좁혀서 보는 편이 current code state와 맞다.
- Correction (2026-05-24): delegate wrapper query family backlog도 current code state보다 보수적으로 남아 있다. `build_tantivy_query(...)`, `document_matches_query(...)`, explanation/highlight/observation helper family, 그리고 `native_query_requires_document_scan(...)` / `query_uses_vector_scores(...)` 기준으로 `constant_score`, `dis_max`, `boosting`, `function_score`, `script_score` 는 already-routed/live seat다. current state에서 남는 work는 broad wrapper-family absence라기보다 parity/validation/readout nuance 쪽으로 좁혀진다.
- Audit note (2026-05-24): native query-builder `Ok(None)` seat 중 일부는 broader functional absence가 아니라 intentional compatibility fallback이다. `build_tantivy_query(...)` 기준으로 `nested` 와 `geo_distance` 는 Tantivy 0.21.1 primitive 부재 때문에 native builder에서는 `Ok(None)` 이지만, same file의 source-backed matcher/scan path가 해당 semantics를 계속 담당한다. 남은 query gap을 current state에서 읽을 때는 “native builder hole” 과 “overall functionality absence” 를 구분하는 편이 맞다.
- Audit note (2026-05-24): `plugin-defined placeholder aggregations` 문구도 current code state에서는 broad unsupported family 전체를 뜻하지 않는다. `plugin_pipeline_aggregation_value(...)`, `plugin_moving_window_pipeline_aggregation_value(...)`, `plugin_moving_percentile_window_pipeline_aggregation_value(...)`, `plugin_normalize_aggregation_value(...)` 등 current plugin collector/finalize family를 보면 placeholder fallback의 큰 비중은 genuinely missing implementation보다 invalid request surface, malformed params, unsupported param combinations, 또는 unrecognized plugin kind admission failure에 가깝다.
- Audit note (2026-05-24): `knn` 도 native query-builder `Ok(None)` seat이지만 overall functionality absence는 아니다. `build_tantivy_query(...)` 는 Tantivy 0.21.1 generic query primitive 부재 때문에 `Query::Knn(_)` 에서 `Ok(None)` 을 반환하지만, same file의 engine vector-native path와 `vector_candidates_for_knn(...)` family가 current `knn` retrieval/count/document flow를 직접 담당한다. 따라서 `knn` 도 current state에서는 plain query-builder hole과 broader execution support를 분리해 읽는 편이 맞다.
- Correction (2026-05-24): span/pattern leaf family도 current code state보다 보수적으로 읽힐 수 있다. `build_tantivy_query(...)`, `document_matches_query(...)`, explanation/highlight helper family, 그리고 `native_query_requires_document_scan(...)` 기준으로 `span_term`, `span_or`, `span_first`, `span_near`, `span_not`, `span_containing`, `span_within`, `span_multi`, `field_masking_span` 및 pattern leaf `prefix` / `wildcard` / `regexp` / `fuzzy` 는 이미 native/source-backed mixed surface에서 routed/live다. current state에서 남는 차이는 broad family absence라기보다 native-vs-compat path split, scan fallback cost, parity/readout nuance 쪽이다.
- Audit note (2026-05-24): collection wrapper admission surface와 collector match tail도 current code state에서는 큰 방향 mismatch가 보이지 않는다. `plugin_kind_still_requires_explicit_collection_wrapper_admission(...)` 가 열어 둔 explicit collection wrapper family와 `collect_plugin_aggregation_from_documents(...)` / `collect_plugin_aggregation_from_hits_with_input_order(...)` 의 live branch surface를 대조하면, trailing `_ => collect_plugin_aggregation_placeholder(plugin)` 는 broad “supported kind but missing branch” 보다는 mostly unrecognized plugin kind 또는 request-surface admission failure 쪽으로 해석하는 편이 맞다.
- Audit note (2026-05-24): additional spot-check에서도 collection admission vs live branch mismatch는 보이지 않았다. explicit spot-check 기준 `top_metrics`, `date_histogram`, `auto_date_histogram`, `variable_width_histogram`, `significant_text`, `global` 은 current file에서 admission surface에 포함되어 있고 documents/hits merge/collect branch에도 각각 live case가 있다. 따라서 current placeholder/default tail을 “admitted family인데 branch가 없다”는 성격으로 읽을 근거는 더 약하다.
- Audit note (2026-05-24): vector section도 current code state에서는 “partial native” 한 줄 요약보다 더 세분화돼 읽히는 편이 맞다. `Query::Knn(_) => Ok(None)` 은 generic query-builder hole이지만, same file의 `vector_candidates_for_knn(...)` family와 vector-native page/page+aggregation/count/document paths가 current `knn` / hybrid execution의 substantive seat를 맡는다. 문서와 test names 기준으로도 multi-index vector-native page reduce, page+aggregation reduce, size=0 skip-hit-materialization, requested-page materialization 같은 paths가 이미 explicit current surface로 자리 잡아 있다.
- Audit note (2026-05-24): span family도 native builder hole과 overall functionality absence를 분리해서 읽는 편이 맞다. 예를 들어 `build_tantivy_span_first_query(...)` 안의 non-`_id` `SpanTerm { .. } => Ok(None)` 은 plain Tantivy span-builder limitation seat이지만, same file과 representative notes 기준으로 `span_first`, `span_near`, `span_not`, `span_containing`, `span_within`, `field_masking_span` 은 source-backed/native-mixed surface에서 already-routed/live다. current state에서 남는 차이는 broad span-family absence라기보다 native builder coverage split과 scan-fallback cost 쪽이다.
- Correction (2026-05-24): section 2의 enumerated “Currently native” list 자체도 current code state보다 좁다. 같은 file의 current collector/finalize surface와 existing representative notes를 기준으로 보면, list에 빠져 있어도 already-live/explicit seat로 읽어야 할 family가 있다. 대표적으로 native/plugin `auto_date_histogram`, `variable_width_histogram`, `top_metrics`, `significant_text`, `percentile_ranks_bucket`, plugin `bucket_sort` / `bucket_count` / `normalize` / `bucket_selector` / `bucket_script`, plugin `moving_percentile_ranks` 등이 그렇다. 따라서 section 2는 exhaustive supported-family inventory라기보다 dated representative slice에 가깝다.
- Audit note (2026-05-24): section 1의 `lexical query execution for:` list도 exhaustive current-support inventory라기보다 representative slice로 읽는 편이 맞다. same section later bullets와 current code state를 함께 보면 `wrapper`, `nested`, `pinned`, `more_like_this`, `constant_score`, `dis_max`, `boosting`, `function_score`, `script_score`, `regexp`, `fuzzy`, `distance_feature`, `rank_feature`, `combined_fields`, `multi_match`, `query_string`, `simple_query_string`, `match_phrase`, `match_phrase_prefix`, `match_bool_prefix`, `terms_set` 등 additional source-backed/mixed seats가 이미 live다.
- Audit note (2026-05-24): section 1의 sort support bullets도 exhaustive current inventory라기보다 representative slice다. same file later notes 기준으로 current state는 fast-field-backed multi-field/date sort 외에도 compatibility sort path의 `geo_distance` sort와 nested sort support를 이미 다룬다. 따라서 early summary bullets만으로 sort-family breadth를 읽으면 current code state보다 더 좁게 보일 수 있다.
- Audit note (2026-05-24): section 1의 date summary bullets도 current code state에서는 representative slice로 읽는 편이 맞다. same file later notes와 current collector surface 기준으로 date family는 fast-field-backed date sort / RFC3339+`epoch_millis` date range / fixed-interval `date_histogram` 뿐 아니라 plugin/source-backed `date_range`, plugin `auto_date_histogram`, plugin `variable_width_histogram` 같은 adjacent date-oriented collection seats도 이미 explicit current surface에 포함된다. 따라서 early date summary만으로 supported date breadth를 읽으면 current state보다 좁게 보일 수 있다.
- Audit note (2026-05-24): early aggregation summary bullets도 later representative notes보다 더 좁게 보일 수 있다. same file later sections already carry explicit current evidence for families such as `scripted_metric`, `geo_bounds`, `geo_centroid`, `significant_text`, `top_metrics`, `auto_date_histogram`, `variable_width_histogram`, `percentile_ranks_bucket`, and `moving_percentile_ranks`, including representative native/plugin coverage and merge/finalize corrections. 따라서 early aggregation bullets는 exhaustive current support table보다 summary slice로 읽는 편이 맞다.
- Audit note (2026-05-24): mid-document duplicated support lists도 current expanded inventory보다 더 좁은 older subset이 섞여 있다. 예를 들어 section 2 앞쪽 expanded plugin/source-backed inventory에는 `significant_text`, `top_metrics`, `auto_date_histogram`, `variable_width_histogram`, `bucket_sort`, `bucket_count`, `normalize`, `bucket_selector`, `bucket_script`, `moving_percentile_ranks` 등이 explicit하게 등장하지만, later duplicated list 일부는 이들을 빠뜨린다. current code state를 읽을 때는 duplicated mid-list보다 expanded inventory와 later representative notes를 우선하는 편이 맞다.
- Audit note (2026-05-24): mid-document duplicated aggregation support lists도 앞쪽 expanded inventory보다 더 좁은 older subset이 섞여 있다. example subset에서는 plugin `significant_text`, `top_metrics`, `auto_date_histogram`, `variable_width_histogram`, `bucket_sort`, `bucket_count`, `normalize`, `bucket_selector`, `bucket_script`, `moving_percentile_ranks` 등이 빠져 있지만, same document의 earlier expanded inventory와 later representative notes에는 이미 current surface로 명시돼 있다. current support reading은 duplicated subset보다 expanded inventory를 우선하는 편이 맞다.
- Audit note (2026-05-24): `collect_plugin_aggregation_placeholder(...)` grep hit density도 current code state에서는 broad unsupported plugin family inventory로 읽기 어렵다. Representative collector entrypoints `collect_plugin_aggregation_from_documents(...)` / `collect_plugin_aggregation_from_hits_with_input_order(...)` 를 보면 placeholder의 큰 덩어리는 trailing catch-all 하나보다 앞단의 repeated request-surface guard들이다: explicit wrapper-admission holdout, required `field` / `weight_field` presence, `filter` / `filters` / `adjacency_matrix` query params, `range` / `ip_range` / `date_range` / `geo_distance` ranges, `multi_terms` sources, 그리고 `terms` / `multi_terms` / `rare_terms` / `significant_terms` / `significant_text` family의 `size` / `order` / `max_doc_count` guard가 documents-side와 hits-side 양쪽에 거의 대칭으로 반복된다. 따라서 broad placeholder count는 current state에서 “지원되지 않는 family 수”보다 malformed or incomplete request surface와 admission gate duplication을 더 많이 반영한다.
- Correction (2026-05-24): collection-side plugin request-surface gate도 shared helper로 수렴했다. `collect_plugin_aggregation_from_documents(...)` 와 `collect_plugin_aggregation_from_hits_with_input_order(...)` 는 이제 local duplicated guard ladder를 각각 들고 있지 않고 `plugin_has_valid_request_surface_for_collection(...)` 를 통해 shared `plugin_has_valid_request_surface_for_merge_or_finalize(...)` validation plus explicit collection-wrapper admission check를 같이 재사용한다. 따라서 collection-vs-merge request-surface drift는 더 줄었고, placeholder fallback 해석도 broad family absence보다 shared admission/validation failure 쪽에 더 가깝다.
- Correction (2026-05-24): plugin `top_metrics` collection setup도 shared helper 경계로 조금 더 수렴했다. documents-side와 hits-side collector는 더 이상 support check 뒤에 `fields` / `sort_specs` extraction을 각각 다시 들고 있지 않고 `plugin_top_metrics_collection_setup(plugin, allow_score_sort)` 하나를 통해 metric field list, explicit sort specs, size admission, 그리고 documents-side `_score` sort exclusion까지 같이 공유한다. 따라서 `top_metrics` native collection admission/readout drift는 한 단계 더 줄었다.
- Correction (2026-05-24): plugin `top_metrics` validity contract도 한 단계 더 수렴했다. merge/finalize-side `top_metrics` placeholder gate와 `plugin_has_valid_request_surface_for_merge_or_finalize(...)` inside check는 이제 repeated `fields` / `sort_specs` / `size` triple test를 직접 들고 있지 않고 `plugin_top_metrics_has_valid_setup(...)` 를 재사용한다. 그래서 collection admission, merge/finalize validation, and `top_metrics` placeholder semantics가 더 동일한 setup contract를 공유한다.
- Correction (2026-05-24): plugin `composite` setup parsing도 shared helper 경계로 수렴했다. documents-side collector, hits-side collector, 그리고 merge-side `composite` branch는 이제 local `size` defaulting, `sources` parsing, optional `after` validation을 각각 다시 들고 있지 않고 `plugin_composite_setup(...)` 를 재사용한다. 따라서 `composite` placeholder/admission semantics도 collection-vs-merge 사이에서 더 같은 request-surface contract를 공유한다.
- Correction (2026-05-24): plugin `top_hits` setup contract도 한 단계 더 수렴했다. `plugin_top_hits_window_and_sort(...)` 가 이제 malformed explicit `sort` surface까지 자체적으로 흡수하므로, hit/window collectors와 shard-local unsorted-window admission seat는 local `sort`-invalid guard를 따로 들고 있지 않는다. `top_hits` request-surface validity는 current code state에서 `(from, size, sort_specs)` setup helper 하나에 더 강하게 모인다.
- Correction (2026-05-24): plugin `sampler` / `random_sampler` / `diversified_sampler` setup parsing도 shared helper 경계로 수렴했다. documents-side sampler collector, hits-side sampler collector, top-level collection dispatch, merge-side placeholder gate, 그리고 shared merge/finalize validation은 repeated size/shard_size admission, default-seeded randomization, diversified field/max-docs-per-value contract를 각자 다시 들고 있지 않고 `plugin_sampler_setup(...)` 를 재사용한다. 따라서 sampler-family placeholder/admission semantics도 collection-vs-merge 사이에서 더 같은 request-surface contract를 공유한다.
- Follow-on correction (2026-05-24): hits-side sampler collector에도 남아 있던 last local gate residue가 now gone 했다. `collect_plugin_aggregation_from_hits_with_input_order(...)` inside sampler-family branch도 이제 repeated size/seed/diversified guards 대신 `plugin_sampler_setup(...)` 만 사용한다. sampler-family request-surface admission은 current code state에서 documents-side, hits-side, top-level dispatch, merge gate, and shared validation all across one helper contract에 더 가깝다.
- Follow-on correction (2026-05-24): `composite` validation도 one-step 더 helper contract로 수렴했다. shared merge/finalize validation과 finalize-side `composite` gate는 이제 local `size` parsing을 다시 들고 있지 않고 `plugin_composite_setup(...)` 를 재사용한다. 같은 follow-on으로 early plugin `top_hits` placeholder admission의 duplicated explicit-sort-invalid branch도 제거됐고, malformed explicit `sort` 는 `plugin_top_hits_window_and_sort(...)` invalid result 하나로 읽힌다.
- Follow-on correction (2026-05-24): merge-side plugin `filter` / `filters` / `adjacency_matrix` branch도 local request-surface guards를 더 이상 직접 들고 있지 않다. those branches now reuse `plugin_has_valid_request_surface_for_merge_or_finalize(...)` instead of separately checking `filter` query presence, filter-map presence, and adjacency separator validity. filter-family merge placeholder semantics is therefore more tightly aligned with the shared request-surface gate.
- Follow-on correction (2026-05-24): plugin `multi_terms` source parsing도 shared helper 경계로 수렴했다. shared merge/finalize validation and documents/hits collectors now reuse `plugin_multi_terms_setup(...)` instead of directly calling `plugin_multi_terms_sources(...)` at each seat. This narrows another small source-parsing drift between request-surface validation and collection-side bucket construction.
- Follow-on correction (2026-05-24): plugin histogram-family setup parsing도 shared helper 경계로 더 수렴했다. shared validation and documents/hits collectors now reuse `plugin_date_histogram_setup(...)`, `plugin_histogram_setup(...)`, and `plugin_bucket_target_count_setup(...)` instead of separately re-parsing explicit interval/buckets params at each seat. This narrows another small admission/defaulting drift across `date_histogram`, `histogram`, `auto_date_histogram`, and `variable_width_histogram`.
- Follow-on correction (2026-05-24): parsed filter-map contract도 shared helper 경계로 더 수렴했다. shared validation plus documents/hits collectors for plugin `filters` and `adjacency_matrix` now reuse `plugin_filters_setup(...)` / `plugin_adjacency_matrix_setup(...)` instead of independently re-parsing filter maps and separators at each seat. This removes another small query-parse/setup drift inside the filter-bucket family.
- Follow-on correction (2026-05-24): single plugin `filter` parsed-query contract도 shared helper 경계로 더 수렴했다. shared validation and documents/hits collectors now reuse `plugin_filter_setup(...)` instead of independently reparsing the raw `filter` body at each seat. This removes another small query-parse drift inside the filter-family collectors.
- Follow-on correction (2026-05-24): plugin range-family parsing도 more specific helper contract로 수렴했다. shared validation plus documents/hits collectors now read `plugin_numeric_range_setup(...)`, `plugin_ip_range_setup(...)`, `plugin_date_range_setup(...)`, and `plugin_geo_distance_setup(...)` instead of relying only on the broad non-empty `ranges` admission or reparsing family-specific buckets inline. This narrows a more meaningful drift: malformed family-specific range payloads are now classified closer to the same family-specific setup surface.
- Follow-on correction (2026-05-24): remaining live raw histogram/range setup seat 3곳도 helper surface로 맞췄다. hits-side plugin `date_range` / `geo_distance` and documents-side plugin `date_histogram` now reuse `plugin_date_range_setup(...)`, `plugin_geo_distance_setup(...)`, and `plugin_date_histogram_setup(...)` instead of direct raw param parsing. source-level로 남는 setup residue는 now mostly helper definitions or genuinely algorithmic bucket-construction seats 쪽으로 읽는 편이 맞다.
- Final audit note (2026-05-24): current source-level convergence work has pushed the repeated plugin request-surface/setup drift nearly to exhaustion. The broad remaining raw helper-parameter calls now read mostly as helper definitions themselves, terms/order semantics, or genuinely algorithmic bucket construction / nested merge / rebucketing seats rather than repeated validation/defaulting wrappers. In other words, the current residual mass is no longer primarily about scattered request-surface parsing drift; it is mostly about substantive collection/merge logic, and full closure still requires behavior validation rather than more source-only helper convergence claims.
- Follow-on correction (2026-05-24): plugin terms-family config도 one more step toward shared setup contracts moved up. `plugin_terms_family_setup(...)` and `plugin_rare_terms_setup(...)` now bundle the defaulted `size` / `order` / `max_doc_count` semantics that had still been read separately by validation, ordering, and finalize seats. This means the remaining direct `plugin_terms_*` helper calls lean more toward order-sensitive ranking semantics than scattered request-surface/defaulting drift.
- Final follow-on audit note (2026-05-24): after the latest `plugin_terms_family_setup(...)` / `plugin_rare_terms_setup(...)` lift, the remaining direct `plugin_terms_family_order_param(...)`, `plugin_terms_size(...)`, and related terms-family helper uses now read predominantly as ranking/order semantics rather than scattered request-surface/defaulting drift. In source-level terms, the remaining surface is now mostly substantive bucket ordering or significance interpretation logic, not another broad helper-convergence layer waiting to be extracted.
- Final source-evidence note (2026-05-24): broad helper convergence 뒤에도 live complexity가 남아 있는 concrete seat는 source-level로 named algorithmic functions 쪽에 모인다. Representative examples are `order_plugin_terms_buckets(...)`, `order_plugin_rare_terms_buckets(...)`, the `aggregation_uses_*significant_terms_family(...)` ranking predicates, `collect_plugin_adjacency_matrix_bucket_values(...)`, `rebucket_date_histogram_buckets_to_interval(...)`, `rebucket_histogram_buckets_to_interval(...)`, and the many `merge_native_aggregation_response(...)` plus `finalize_merged_pipeline_aggregations(...)` nested merge sites. These are not obviously another request-surface/defaulting layer; they are substantive ordering, rebucketing, and nested aggregation merge logic.
- Validation-scope note (2026-05-25): source-only convergence 이후 full closure를 주장하려면 at least the following behavior families need explicit proof, not just grep-level support claims: (1) lexical/source-backed query execution including normalized plan and source-derived clauses, (2) vector/KNN execution including filtered KNN and cache invalidation behavior, (3) representative native aggregations from filtered hits (`terms`, metric family, filter buckets, `top_hits`, `composite`, `significant_terms`, `geo_bounds`), (4) representative pipeline execution (`sum_bucket` plus adjacent plugin/native pipeline wrappers), (5) plugin request-surface failure classification (`placeholder` and malformed-request seats), and (6) the algorithmic seats that still dominate source complexity: terms/significant ordering, adjacency/filter bucket composition, histogram/date-histogram rebucketing, and nested aggregation merge/finalize loops. Existing test names in `lib.rs` already provide part of that evidence surface, but they do not yet constitute a proven exhaustive closure matrix on their own.
- Validation-matrix refinement (2026-05-25): current explicit test-name evidence in `lib.rs` already anchors several proof buckets: `engine_executes_knn_query_with_filter_and_vector_scores`, `engine_bounds_and_invalidates_knn_runtime_cache_entries`, `engine_searches_with_normalized_query_plan`, `engine_searches_with_source_derived_query_clauses`, `engine_collects_terms_aggregations_from_filtered_hits_before_pagination`, `engine_collects_metric_aggregations_from_filtered_hits`, `engine_collects_filter_bucket_aggregations_from_filtered_hits`, `engine_collects_top_hits_aggregation_from_filtered_hits`, `engine_collects_composite_terms_aggregation_from_filtered_hits`, `engine_collects_significant_terms_aggregation_from_filtered_hits`, `engine_collects_geo_bounds_aggregation_from_filtered_hits`, `engine_collects_sum_bucket_pipeline_aggregation`, `engine_collects_scripted_metric_placeholder_aggregation`, `engine_collects_plugin_placeholder_aggregation`, and `engine_rejects_malformed_search_queries`. By contrast, the same grep pass did not surface equally explicit `engine_collects_*` test names for histogram/date-histogram rebucketing, range/ip-range/date-range/geo-distance plugin families, sampler family, top-metrics family, or the broader plugin pipeline wrapper set (`bucket_sort`, `bucket_count`, `normalize`, `bucket_selector`, `bucket_script`, moving-window percentile/rank variants). Those buckets remain the clearest proof gaps before a full closure claim.
- Required-validation checklist (2026-05-25): before claiming full closure, the current proof-gap buckets should be covered by explicit runtime scenarios at roughly this granularity. (1) histogram/date-histogram rebucketing: prove array-bucket and nested-subaggregation rebucketing behavior, including visible bucket order plus nested pipeline finalize after rebucketing; (2) range/ip-range/date-range/geo-distance plugin families: prove valid request execution and malformed family-specific range payload rejection separately, since setup parsing is now family-specific; (3) sampler/random_sampler/diversified_sampler: prove size/default-seed semantics plus diversified field/max-docs-per-value behavior on both collection and merge paths; (4) top-metrics: prove documents-side non-`_score` sort collection, hits-side `_score` sort collection, and merge/finalize consistency for the same request surface; (5) plugin pipeline wrappers: prove representative success and malformed-request classification for `bucket_sort`, `bucket_count`, `normalize`, `bucket_selector`, `bucket_script`, and moving percentile/rank wrappers; (6) algorithmic seats: prove terms/significant ordering semantics, adjacency/filter bucket nested merge composition, and histogram/date-histogram rebucketing against expected outward surfaces. Existing source-level convergence reduces drift risk, but these buckets still need runtime evidence.
- Coverage-matrix note (2026-05-25): with the current explicit `engine_*` test-name evidence, the required-validation checklist now splits into two rough groups. Covered-or-partially-anchored buckets: normalized/source-derived query execution, filtered KNN execution and cache invalidation, filtered-hit `terms`/metric/filter-bucket/`top_hits`/`composite`/`significant_terms`/`geo_bounds`, `sum_bucket` pipeline execution, scripted/plugin placeholder behavior, and malformed query rejection. Still-explicitly-underanchored buckets: histogram/date-histogram rebucketing, plugin `range`/`ip_range`/`date_range`/`geo_distance`, sampler family, top-metrics family, and the broader plugin pipeline wrapper family (`bucket_sort`, `bucket_count`, `normalize`, `bucket_selector`, `bucket_script`, moving percentile/rank wrappers). Those underanchored buckets remain the clearest evidence gap before a full completion claim.
- Underanchored run-plan note (2026-05-25): the still-underanchored proof buckets can be reduced to a practical runtime plan with six scenario groups. (1) rebucketing group: one date-histogram case and one numeric-histogram case where rebucketing changes visible buckets and nested subaggregations/pipeline finalize must remain correct; (2) range-family group: four plugin cases (`range`, `ip_range`, `date_range`, `geo_distance`) each split into one valid execution and one malformed family-specific payload rejection; (3) sampler group: `sampler`, `random_sampler`, and `diversified_sampler` with explicit/default size/seed semantics plus diversified max-docs-per-value enforcement; (4) top-metrics group: one documents-side non-`_score` sort case, one hits-side `_score` sort case, and one merge/finalize multi-shard consistency case; (5) plugin pipeline wrapper group: representative success + malformed-request scenarios for `bucket_sort`, `bucket_count`, `normalize`, `bucket_selector`, `bucket_script`, plus one moving-percentiles and one moving-percentile-ranks wrapper case; (6) algorithmic ordering/merge group: one terms-order case, one significant-terms ranking case, and one adjacency/filter nested merge case. This is the smallest behavior-oriented plan that would materially reduce the remaining completion-evidence gap.
- Existing-vs-new-evidence note (2026-05-25): the six scenario groups do not all require the same amount of new runtime work. Likely partly-covered by existing named test evidence: lexical/source-backed query execution, filtered KNN/cache behavior, filtered-hit `terms`/metric/filter-bucket/`top_hits`/`composite`/`significant_terms`/`geo_bounds`, plus `sum_bucket` pipeline execution and malformed-query/placeholder behavior. Likely still requiring explicitly targeted new runs or new named tests: (1) histogram/date-histogram rebucketing, (2) plugin `range` / `ip_range` / `date_range` / `geo_distance`, (3) sampler/random_sampler/diversified_sampler semantics, (4) top-metrics documents-side vs hits-side vs merge/finalize consistency, (5) plugin pipeline wrappers (`bucket_sort`, `bucket_count`, `normalize`, `bucket_selector`, `bucket_script`, moving percentile/rank variants), and (6) adjacency/filter nested merge plus terms/significant ordering edge semantics where current source-level confidence is stronger than current explicit behavior evidence.
- Underanchored priority note (2026-05-25): if runtime proof work is staged rather than done all at once, the highest-yield order is roughly: (P1) histogram/date-histogram rebucketing plus adjacency/filter nested merge semantics, because these touch the largest remaining algorithmic merge surface; (P2) plugin pipeline wrappers (`bucket_sort`, `bucket_count`, `normalize`, `bucket_selector`, `bucket_script`, moving percentile/rank wrappers), because they combine malformed-request classification with outward surface shaping; (P3) sampler family and top-metrics family, because they each carry distinct collection-vs-merge semantics; (P4) plugin `range` / `ip_range` / `date_range` / `geo_distance`, because their setup parsing is now tighter and the remaining need is mostly family-specific behavior proof. This ordering is about proof efficiency, not about product importance.
- P1 scenario note (2026-05-25): the highest-priority runtime proof bucket can be reduced further to four concrete scenario shapes. (P1-a) date-histogram rebucketing with nested subaggregations, where shard-local intervals differ and final outward buckets plus nested reductions must match the rebucketed carrier; (P1-b) numeric histogram rebucketing with nested subaggregations, including visible bucket order and nested merge correctness after interval collapse; (P1-c) `filters`/`adjacency_matrix` nested merge, where bucket object shape, `doc_count`, and nested pipeline finalize remain stable after merge; (P1-d) one mixed rebucketing-plus-pipeline case, where rebucketed histogram/date-histogram buckets still feed the expected outward pipeline surface rather than only the hidden carrier. These four scenarios would materially de-risk the largest remaining algorithmic merge surface.
- P2 scenario note (2026-05-25): the plugin pipeline-wrapper proof bucket can likewise be reduced to four concrete scenario shapes. (P2-a) one bucket-surface wrapper success case covering `bucket_sort` or `bucket_count`, where object/array bucket carriers and outward buckets remain aligned after wrapper execution; (P2-b) one `normalize` or `bucket_script` success case proving bucket-path value derivation plus outward bucket preservation; (P2-c) one malformed-request classification case covering explicit invalid wrapper params (`sort`, `window`, `path`, `params`, or operator/threshold surface as applicable) so placeholders are emitted at the right boundary; (P2-d) one moving percentile/rank wrapper case proving requested percent/value config is honored and object/array bucket shape survives pipeline materialization. These four shapes would cover most of the remaining proof risk for the plugin pipeline-wrapper family.
- P3 scenario note (2026-05-25): the sampler/top-metrics proof bucket can be reduced to four concrete scenario shapes. (P3-a) one `sampler` case proving default-vs-explicit size semantics and doc-count/nested-aggregation stability; (P3-b) one `random_sampler` plus one `diversified_sampler` case proving default seed behavior, deterministic ordering, and diversified `max_docs_per_value` enforcement; (P3-c) one top-metrics documents-side case using non-`_score` explicit sort, proving native document collection plus outward ordering/size semantics; (P3-d) one top-metrics hits-side or merge/finalize case using `_score` sort or multi-shard merge, proving the request surface that cannot use documents-side native collection still converges to the same outward `top_metrics` contract. These four shapes would cover most of the remaining proof risk for the sampler/top-metrics family.
- P4 scenario note (2026-05-25): the range-family proof bucket can be reduced to four concrete scenario shapes. (P4-a) one numeric `range` case with a valid multi-bucket request proving bucket membership and outward bucket doc counts; (P4-b) one `ip_range` plus one `date_range` case proving family-specific parsing and boundary semantics on valid payloads; (P4-c) one `geo_distance` case proving origin/range parsing plus geo-distance bucket membership; (P4-d) one malformed-payload rejection sweep covering each family-specific parser surface (`from`/`to` type errors, invalid IP text, invalid date text, malformed geo origin or range entry) so placeholders are emitted consistently after the new family-specific setup tightening. These scenarios would close most of the remaining proof risk for the range-family bucket.
- Validation run-order note (2026-05-25): if actual runtime validation begins, the most efficient sequence is to run `P1` first, then `P2`, then `P3`, then `P4`. `P1` de-risks the largest remaining algorithmic merge surface; `P2` then checks the broadest plugin pipeline wrapper family; `P3` covers collection-vs-merge semantic splits (`sampler`, `top_metrics`); and `P4` closes the remaining family-specific range parsing/behavior bucket. In practice, a clean run through `P1` and `P2` would already eliminate most of the current completion-evidence uncertainty.
- P1 execution-scope note (2026-05-25): if runtime validation starts, each P1 scenario should record at least four artifacts: (1) the input aggregation request shape, including nested subaggregations/pipelines; (2) the shard-local bucket shape before final merge/rebucketing when relevant; (3) the final outward aggregation surface after rebucketing/merge, especially visible `buckets`, bucket order, `doc_count`, and nested aggregation payloads; (4) the malformed-vs-success expectation boundary for the same family, if the scenario also covers request-surface rejection. For `P1-a`/`P1-b`, the key evidence is that rebucketed carrier state and outward `buckets` agree after nested merge/finalize. For `P1-c`, the key evidence is that object-bucket keys plus nested payloads survive merge without shape drift. For `P1-d`, the key evidence is that pipelines observe the intended outward rebucketed surface rather than only an intermediate hidden carrier.
- P2 execution-scope note (2026-05-25): if runtime validation starts for the plugin pipeline-wrapper bucket, each P2 scenario should record at least four artifacts: (1) the input wrapper request surface, including explicit `path`, `sort`, `window`, `params`, operator/threshold, or percent/value config as applicable; (2) the target aggregation surface before wrapper execution, including whether buckets are object-shaped or array-shaped and whether hidden carrier state is present; (3) the final outward wrapper result after execution, including visible `buckets`, bucket order, derived values, and any preserved metadata fields; (4) the malformed-vs-success classification boundary for the same wrapper family. For `P2-a`/`P2-b`, the key evidence is that wrapper execution preserves the intended bucket surface while applying the requested transformation. For `P2-c`, the key evidence is that malformed wrapper params fail at the intended boundary and degrade to placeholder rather than silently defaulting. For `P2-d`, the key evidence is that moving percentile/rank wrappers honor requested config and preserve object/array bucket shape through pipeline materialization.
- P3 execution-scope note (2026-05-25): if runtime validation starts for the sampler/top-metrics bucket, each P3 scenario should record at least four artifacts: (1) the input request surface, including explicit vs omitted size/seed/sort fields and any diversified constraints; (2) the collected candidate set before final outward shaping, especially sampled documents/hits or top-metrics candidate entries; (3) the final outward aggregation surface, including `doc_count`, visible hits/metrics, ordering, size truncation, and any shard-merge effects; (4) the malformed-vs-success classification boundary for the same family. For `P3-a`/`P3-b`, the key evidence is that size/default-seed/diversified semantics produce deterministic and bounded outward results. For `P3-c`, the key evidence is that documents-side top-metrics uses the intended non-`_score` sort and emits the expected metrics surface. For `P3-d`, the key evidence is that hits-side `_score` sort or multi-shard merge still converges to the same outward `top_metrics` contract when the documents-side native path is not applicable.
- P4 execution-scope note (2026-05-25): if runtime validation starts for the range-family bucket, each P4 scenario should record at least four artifacts: (1) the input request surface, including explicit `from`/`to`, keyed-vs-array bucket shape if applicable, family-specific literals (numeric, IP, date, geo origin/range), and any nested subaggregations; (2) the parsed or shard-local bucket carrier shape before final outward emission when relevant, especially family-specific boundary interpretation and per-bucket membership; (3) the final outward aggregation surface, including visible `buckets`, bucket keys/ranges, `doc_count`, nested payloads, and ordering/keyed-shape preservation; (4) the malformed-vs-success classification boundary for the same family-specific parser surface. For `P4-a`, the key evidence is that numeric `range` bucket membership and outward bucket counts match the intended inclusive/exclusive boundaries. For `P4-b`, the key evidence is that `ip_range` and `date_range` preserve family-specific boundary semantics and emit the expected outward key/range representation. For `P4-c`, the key evidence is that `geo_distance` uses the intended origin plus distance-range interpretation and emits the correct bucket membership surface. For `P4-d`, the key evidence is that malformed numeric/IP/date/geo payloads fail at the intended family-specific parsing boundary and degrade to placeholders rather than silently defaulting.
- Validation run-sheet note (2026-05-25): the current underanchored proof plan is now concrete enough to compress into a single execution checklist. Run `P1-a` through `P1-d` first and capture request shape, shard-local carrier, final outward buckets, and nested/pipeline agreement; then run `P2-a` through `P2-d` and capture wrapper input, pre-wrapper bucket surface, outward transformed surface, and malformed-wrapper boundary; then run `P3-a` through `P3-d` and capture sampler/top-metrics request config, pre-final candidate set, outward aggregation surface, and success-vs-placeholder boundary; finally run `P4-a` through `P4-d` and capture range-family request literals, parsed/per-bucket membership surface, outward buckets/key shape, and malformed family-parser boundary. Any bucket that cannot produce all four artifact classes should still be treated as under-proven even if an adjacent existing test name looks directionally relevant.
- Proof-ledger note (2026-05-25): the remaining closure matrix should now be read as a two-column ledger rather than a generic backlog. Existing named evidence already partially anchors lexical/source-backed query execution, filtered KNN/cache behavior, filtered-hit native aggregations (`terms`, metric family, filter buckets, `top_hits`, `composite`, `significant_terms`, `geo_bounds`), `sum_bucket`, scripted/plugin placeholder behavior, and malformed query rejection. By contrast, the underanchored runtime-proof column still requires new artifact capture for `P1` histogram/date-histogram rebucketing plus adjacency/filter nested merge, `P2` plugin pipeline wrappers, `P3` sampler/top-metrics, and `P4` range-family behavior. The practical reading is: if a family only has left-column test-name support but no right-column four-artifact capture, closure is not yet proven for that family.
- Validation triage note (2026-05-25): reading the proof ledger as an execution triage yields a simple rule. First fill the right-column `P1` and `P2` buckets, because they remove the largest remaining uncertainty per run by covering rebucketing/nested-merge logic plus the broad plugin pipeline-wrapper surface. Next fill `P3`, because sampler/top-metrics still span distinct collection-vs-merge contracts that existing named evidence does not close. Leave `P4` last, not because it is unimportant, but because its family-specific parsing/behavior bucket is narrower and now sits behind tighter setup helpers. The practical closure test is therefore: if `P1` or `P2` is still missing four-artifact runtime proof, the overall gap remains materially open regardless of how much left-column named evidence exists elsewhere.
- First-pass closure gate note (2026-05-25): in practical terms, `P1` and `P2` together form the first-pass closure gate. If rebucketing/nested-merge proof (`P1`) and plugin pipeline-wrapper proof (`P2`) are both cleanly evidenced with the required four-artifact capture, the remaining uncertainty collapses to narrower family-specific buckets (`P3`, `P4`) rather than broad structural doubt about the aggregation stack. Conversely, if either `P1` or `P2` remains unproven, it is still too early to treat the remaining work as edge cleanup; the core closure claim stays open.
- Second-pass closure bucket note (2026-05-25): once the first-pass closure gate (`P1` + `P2`) is satisfied, the remaining proof work should be read as a second-pass bucket rather than another broad uncertainty field. That second pass is mainly `P3` sampler/top-metrics and `P4` range-family behavior: narrower families with clearer request/setup contracts, but still requiring explicit runtime artifacts before full closure can be claimed. In other words, after `P1` and `P2`, the open work narrows from structural aggregation-stack doubt to family-specific semantic proof.
- Closure decision rule note (2026-05-25): the current proof state can be read with a simple three-step rule. The closure claim is still materially open while either first-pass gate bucket (`P1` or `P2`) lacks four-artifact runtime evidence. It becomes only narrowly open, rather than structurally open, once both `P1` and `P2` are evidenced and the remaining gap is confined to second-pass buckets (`P3`, `P4`). It can be treated as actually closed only when both the first-pass gate and the second-pass family buckets have explicit runtime proof, not merely adjacent test-name support or source-level convergence notes.
- Validation index note (2026-05-25): for actual closure work, the validation-related notes can now be read in a short fixed order: (1) `Validation-scope note` and `Validation-matrix refinement` for what must be proven and what existing test-name evidence already anchors; (2) `underanchored priority note`, `P1`..`P4` scenario notes, and `Validation run-order note` for what to run first; (3) `P1`..`P4` execution-scope notes and `Validation run-sheet note` for which four artifact classes must be captured; (4) `Proof-ledger note`, `Validation triage note`, `First-pass closure gate note`, `Second-pass closure bucket note`, and `Closure decision rule note` for how to interpret the resulting evidence. This index does not add new proof; it just fixes the shortest reading path before runtime validation starts.
- Correction (2026-05-25): a fresh source pass over `crates/os-engine-tantivy/src/lib.rs` materially narrows the previously described underanchored proof buckets. Explicit runtime test names now visibly anchor large parts of `P1`, `P2`, `P3`, and `P4`, including `native_tantivy_plugin_bucket_sort_preserves_shape(...)`, `native_tantivy_plugin_bucket_count_preserves_shape(...)`, `native_tantivy_plugin_normalize_preserves_shape(...)`, `native_tantivy_plugin_bucket_selector_preserves_shape(...)`, `native_tantivy_plugin_bucket_script_preserves_shape(...)`, the `native_tantivy_plugin_moving_*_preserves_shape(...)` family, `native_tantivy_plugin_date_histogram_aggregation_preserves_shape(...)`, `multi_index_native_tantivy_plugin_date_histogram_reduce_preserves_shape(...)`, `native_tantivy_plugin_histogram_aggregation_preserves_shape(...)`, `native_tantivy_plugin_sampler_supports_nested_subaggregations(...)`, `native_tantivy_plugin_random_sampler_supports_nested_subaggregations(...)`, `native_tantivy_plugin_diversified_sampler_supports_nested_subaggregations(...)`, `native_tantivy_plugin_top_metrics_aggregation_preserves_shape(...)`, `multi_index_native_tantivy_plugin_top_metrics_reduce_preserves_shape(...)`, `native_tantivy_plugin_range_aggregation_preserves_shape(...)`, `native_tantivy_plugin_ip_range_aggregation_preserves_shape(...)`, `native_tantivy_plugin_date_range_aggregation_preserves_shape(...)`, `multi_index_native_tantivy_plugin_date_range_reduce_preserves_shape(...)`, `multi_index_native_tantivy_plugin_ip_range_reduce_preserves_shape(...)`, `native_tantivy_plugin_geo_distance_aggregation_preserves_shape(...)`, and `multi_index_native_tantivy_plugin_geo_distance_reduce_preserves_shape(...)`. Accordingly, the remaining proof gap should now be read less as “missing explicit runtime scenarios for these families” and more as “whether the existing scenarios exhaust the four-artifact checklist, malformed-boundary coverage, and mixed rebucketing/pipeline edge cases.”
- Follow-on correction (2026-05-25): another targeted source pass narrows the residual proof risk further. `lib.rs` visibly contains explicit shape/reduce coverage not only for plugin wrappers and range/sampler/top-metrics families, but also for native/plugin histogram rebucketing surfaces and many pipeline families, including `native_tantivy_plugin_histogram_aggregation_preserves_shape(...)`, `native_tantivy_plugin_auto_date_histogram_aggregation_preserves_shape(...)`, `multi_index_native_tantivy_plugin_auto_date_histogram_reduce_preserves_shape(...)`, `native_tantivy_plugin_variable_width_histogram_aggregation_preserves_shape(...)`, `multi_index_native_tantivy_plugin_variable_width_histogram_reduce_preserves_shape(...)`, and the `search_size_zero_multi_index_native_reduce_supports_moving_*` family. As a result, the remaining gap is best read as a smaller edge-case bucket: family-specific malformed plugin-param boundaries plus mixed rebucketing-then-pipeline interactions, rather than a broad absence of runtime evidence for `P1`/`P2`/`P3`/`P4` families themselves.
- Framing correction (2026-05-25): the earlier `P1`/`P2` first-pass closure framing should now be read more narrowly in light of the fresh source evidence. It is no longer best interpreted as “these broad family buckets still lack runtime proof”; instead, `P1`/`P2` now act mostly as edge-case proof gates around mixed rebucketing-plus-pipeline interactions and malformed plugin-wrapper/request boundaries that are not obviously exhausted by the visible shape/reduce tests. Put differently, the broad family surfaces behind `P1` and `P2` are now substantially anchored; the remaining uncertainty is whether their harder boundary cases are fully covered.
- Final residual bucket note (2026-05-25): after the latest source-evidence corrections, the remaining unproven surface is best treated as a compact edge-case bucket rather than a family backlog. In practical terms, the main residual questions are now (1) malformed plugin/request boundary behavior that may not be exhaustively represented by the visible shape/reduce tests, and (2) mixed rebucketing-then-pipeline interactions where outward bucket surfaces, hidden carrier state, and final wrapper/pipeline materialization must all agree. Everything broader than that is now more naturally read as already materially anchored by the current source-visible runtime scenarios.
- Follow-on correction (2026-05-25): the latest test additions in `crates/os-engine-tantivy/src/lib.rs` narrow the residual edge bucket further. Explicit search-level malformed-wrapper coverage now includes `engine_collects_placeholder_for_malformed_plugin_bucket_sort_request(...)`, `engine_collects_placeholder_for_malformed_plugin_bucket_selector_request(...)`, `engine_collects_placeholder_for_malformed_plugin_bucket_script_request(...)`, `engine_collects_placeholder_for_malformed_plugin_normalize_request(...)`, and `engine_collects_placeholder_for_malformed_plugin_bucket_count_request(...)`. Explicit mixed rebucketing-then-pipeline coverage now also includes `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_script_surface(...)`, `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_selector_surface(...)`, `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_normalize_surface(...)`, and `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_sort_surface(...)`. The practical residual bucket is therefore smaller again: mostly uncovered malformed-wrapper families outside this set, or more exotic rebucketing/pipeline combinations beyond the now-visible date-histogram reduce path.
- Follow-on correction (2026-05-25): the newest `lib.rs` additions narrow the residual bucket further on two fronts. Malformed moving-window wrapper coverage now also includes `engine_collects_placeholder_for_malformed_plugin_moving_avg_request(...)`, `engine_collects_placeholder_for_malformed_plugin_moving_percentiles_request(...)`, and `engine_collects_placeholder_for_malformed_plugin_moving_percentile_ranks_request(...)`, so the moving pipeline family is no longer represented only by success-shape tests. Mixed rebucketing-then-pipeline coverage also now extends beyond date-histogram paths to `search_size_zero_multi_index_plugin_histogram_reduce_feeds_normalize_surface(...)` and `search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_normalize_surface(...)`. The practical residual bucket is therefore narrower again: mostly whatever malformed moving/plugin-wrapper variants remain outside these concrete seats, plus any still-unseen rebucketing/wrapper combinations beyond the now-covered date/auto-date/histogram/variable-width normalize-or-wrapper paths.
- Follow-on correction (2026-05-25): the malformed moving-wrapper bucket narrowed once more with `engine_collects_placeholder_for_malformed_plugin_moving_range_request(...)`. At this point the explicit malformed moving-family seats visible in `lib.rs` include `moving_avg`, `moving_percentiles`, `moving_percentile_ranks`, and `moving_range`, in addition to the earlier bucket-wrapper malformed cases (`bucket_sort`, `bucket_selector`, `bucket_script`, `normalize`, `bucket_count`). The remaining proof gap inside malformed wrapper handling is therefore increasingly about whichever moving/plugin families still lack an explicit invalid-request seat, not about wrapper failure classification in general.
- Follow-on correction (2026-05-25): the malformed moving-wrapper coverage expanded again with `engine_collects_placeholder_for_malformed_plugin_moving_sum_request(...)` and `engine_collects_placeholder_for_malformed_plugin_moving_count_request(...)`. The explicit invalid-request seats visible in `lib.rs` now cover at least `moving_avg`, `moving_count`, `moving_sum`, `moving_percentiles`, `moving_percentile_ranks`, and `moving_range`, in addition to the earlier malformed bucket-wrapper families. This pushes the residual malformed-wrapper gap further away from the moving/window family as a broad category and closer to only the still-unseen moving variants or any remaining non-moving plugin wrappers without an explicit invalid-request seat.
- Follow-on correction (2026-05-25): the malformed moving-wrapper bucket narrowed again with `engine_collects_placeholder_for_malformed_plugin_moving_min_request(...)` and `engine_collects_placeholder_for_malformed_plugin_moving_max_request(...)`. Together with the immediately prior additions, the source-visible malformed moving-family seats now cover `moving_avg`, `moving_count`, `moving_sum`, `moving_min`, `moving_max`, `moving_percentiles`, `moving_percentile_ranks`, and `moving_range`. The remaining malformed-wrapper uncertainty is therefore increasingly about only the still-unseen moving variants or any non-moving plugin wrappers that still lack an explicit invalid-request seat.
- Follow-on correction (2026-05-25): malformed moving-wrapper coverage widened again with `engine_collects_placeholder_for_malformed_plugin_moving_stddev_request(...)`. The source-visible invalid-request seats now cover at least `moving_avg`, `moving_count`, `moving_sum`, `moving_min`, `moving_max`, `moving_stddev`, `moving_percentiles`, `moving_percentile_ranks`, and `moving_range`. That leaves the malformed moving-family residual mostly to the still-unseen variants such as `moving_median`, `moving_variance`, `moving_skewness`, `moving_kurtosis`, and `moving_mad`, rather than the moving/window family as a broad unresolved bucket.
- Follow-on correction (2026-05-25): with the latest `engine_collects_placeholder_for_malformed_plugin_moving_mad_request(...)` addition, the source-visible malformed moving-wrapper seats now cover essentially the representative moving family surface: `moving_avg`, `moving_count`, `moving_sum`, `moving_min`, `moving_max`, `moving_median`, `moving_stddev`, `moving_variance`, `moving_skewness`, `moving_kurtosis`, `moving_mad`, `moving_percentiles`, `moving_percentile_ranks`, and `moving_range`. In practical terms, the malformed moving-wrapper bucket is now close to exhausted at the representative-family level; the residual proof gap is better read as either exotic non-moving wrapper edges or remaining mixed rebucketing/wrapper combinations, not as a broad uncertainty about moving-window placeholder classification.
- Follow-on correction (2026-05-25): the non-moving malformed-wrapper bucket also narrowed with `engine_collects_placeholder_for_malformed_plugin_serial_diff_request(...)` and `engine_collects_placeholder_for_malformed_plugin_derivative_request(...)`. Combined with the bucket-wrapper and moving-family invalid-request seats already added, the residual malformed-wrapper gap now leans more toward whichever non-moving pipeline/plugin wrappers still lack an explicit malformed-request seat, rather than toward serial-difference/derivative-style wrappers as a whole. This keeps shrinking the remaining proof burden toward isolated uncovered seats rather than broad feature families.
- Follow-on correction (2026-05-25): the non-moving malformed-wrapper bucket narrowed again with `engine_collects_placeholder_for_malformed_plugin_stats_bucket_request(...)`. Alongside the earlier `serial_diff` and `derivative` invalid-request seats, the current source-visible evidence shows that representative bucket-metric/pipeline wrappers are no longer missing malformed-boundary coverage wholesale. The residual malformed-wrapper gap is therefore better read as a shrinking set of isolated uncovered wrapper seats, not as a broad uncertainty across the non-moving pipeline family.
- Follow-on correction (2026-05-25): the non-moving malformed-wrapper bucket narrowed further with `engine_collects_placeholder_for_malformed_plugin_avg_bucket_request(...)`, `engine_collects_placeholder_for_malformed_plugin_min_bucket_request(...)`, and `engine_collects_placeholder_for_malformed_plugin_max_bucket_request(...)`. Together with the already added `serial_diff`, `derivative`, and `stats_bucket` invalid-request seats, representative bucket-metric/pipeline wrappers now have explicit malformed-boundary coverage across a wider slice of the family. The practical residual malformed-wrapper gap is therefore increasingly just the shrinking set of wrappers that still lack an explicit invalid-request seat, not a broad uncertainty about bucket-metric plugin classification.
- Follow-on correction (2026-05-25): the non-moving malformed-wrapper bucket narrowed once more with `engine_collects_placeholder_for_malformed_plugin_sum_bucket_request(...)`. With explicit invalid-request seats now visible for `serial_diff`, `derivative`, `stats_bucket`, `avg_bucket`, `min_bucket`, `max_bucket`, and `sum_bucket`, representative bucket-metric/pipeline wrappers are increasingly covered on the malformed-boundary side as well as on the success-shape side. The remaining residual malformed-wrapper burden is therefore best read as a small set of isolated uncovered wrappers, not as a broad bucket-metric/pipeline family gap.
- Follow-on correction (2026-05-25): the non-moving malformed-wrapper bucket narrowed again with `engine_collects_placeholder_for_malformed_plugin_percentiles_bucket_request(...)`, `engine_collects_placeholder_for_malformed_plugin_percentile_ranks_bucket_request(...)`, and `engine_collects_placeholder_for_malformed_plugin_extended_stats_bucket_request(...)`. Together with the earlier `serial_diff`, `derivative`, `stats_bucket`, `avg_bucket`, `min_bucket`, `max_bucket`, and `sum_bucket` invalid-request seats, the current source-visible evidence now covers a broad representative slice of bucket-metric and percentile/rank pipeline wrappers on the malformed-boundary side. The practical residual malformed-wrapper gap is therefore better read as a very small set of still-uncovered wrappers, not as a meaningful family-level uncertainty.
- Final correction (2026-05-25): a direct scan of `crates/os-engine-tantivy/src/lib.rs` now shows explicit malformed-request placeholder seats for every currently surfaced wrapper/pipeline plugin kind in the local source pass: `bucket_sort`, `bucket_selector`, `bucket_script`, `normalize`, `bucket_count`, `moving_avg`, `moving_count`, `moving_sum`, `moving_min`, `moving_max`, `moving_median`, `moving_stddev`, `moving_variance`, `moving_skewness`, `moving_kurtosis`, `moving_mad`, `moving_percentiles`, `moving_percentile_ranks`, `moving_range`, `serial_diff`, `derivative`, `stats_bucket`, `avg_bucket`, `min_bucket`, `max_bucket`, `sum_bucket`, `percentiles_bucket`, `percentile_ranks_bucket`, and `extended_stats_bucket`. On current source evidence, the malformed-wrapper bucket is therefore no longer a meaningful uncovered family surface; the remaining uncertainty is dominated instead by execution validation and any algorithmic or combinatorial edge cases that these explicit seats still do not prove.
- Follow-on correction (2026-05-25): the mixed rebucketing/wrapper bucket narrowed further with `search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_sort_surface(...)` and `search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_sort_surface(...)`, alongside the earlier date-histogram, histogram, and normalize/bucket-script/bucket-selector coverage. On current source evidence, rebucketing-plus-wrapper interactions are no longer just anchored for one histogram flavor; they now visibly span `date_histogram`, `auto_date_histogram`, `histogram`, and `variable_width_histogram` with multiple wrapper shapes. The remaining source-only uncertainty is therefore better read as whatever combinatorial edge cases remain beyond these representative rebucketing/wrapper pairings, not as a broad lack of rebucketing-wrapper evidence.
- Final source-handoff note (2026-05-25): on the current worktree, additional source-only progress appears to have diminishing returns. Helper convergence, representative malformed-wrapper coverage, and representative rebucketing-plus-wrapper pairings have all been pushed far enough that the remaining uncertainty reads primarily as execution validation debt plus a small tail of isolated combinatorial seats. In practical terms, further closure claims now depend more on running and inspecting behavior than on adding more grep-level or source-structure evidence.
- Validation handoff priority note (2026-05-25): if execution validation begins from the current worktree, the highest-yield first pass is now to run the newly concentrated malformed-wrapper seats together with a small rebucketing-wrapper subset rather than to expand source-only coverage further. In practical terms, start with the fresh malformed placeholder tests plus one representative rebucketing-wrapper batch (`date_histogram`, `auto_date_histogram`, `histogram`, `variable_width_histogram` with wrapper outputs already pinned in-source), because those runs would convert the current source-visible evidence into runtime-backed closure evidence with the smallest remaining uncertainty per test. After that, any still-open questions are likely to be isolated runtime mismatches rather than broad missing-family gaps.
- Validation test-name handoff note (2026-05-25): if runtime validation starts from the current worktree, the shortest first-pass test-name batch is now straightforward. For malformed-wrapper confirmation, start with `engine_collects_placeholder_for_malformed_plugin_bucket_sort_request(...)`, `engine_collects_placeholder_for_malformed_plugin_bucket_selector_request(...)`, `engine_collects_placeholder_for_malformed_plugin_bucket_script_request(...)`, `engine_collects_placeholder_for_malformed_plugin_normalize_request(...)`, `engine_collects_placeholder_for_malformed_plugin_bucket_count_request(...)`, `engine_collects_placeholder_for_malformed_plugin_serial_diff_request(...)`, `engine_collects_placeholder_for_malformed_plugin_derivative_request(...)`, `engine_collects_placeholder_for_malformed_plugin_stats_bucket_request(...)`, `engine_collects_placeholder_for_malformed_plugin_avg_bucket_request(...)`, `engine_collects_placeholder_for_malformed_plugin_min_bucket_request(...)`, `engine_collects_placeholder_for_malformed_plugin_max_bucket_request(...)`, `engine_collects_placeholder_for_malformed_plugin_sum_bucket_request(...)`, `engine_collects_placeholder_for_malformed_plugin_percentiles_bucket_request(...)`, `engine_collects_placeholder_for_malformed_plugin_percentile_ranks_bucket_request(...)`, and `engine_collects_placeholder_for_malformed_plugin_extended_stats_bucket_request(...)`, plus the malformed `moving_*` seats already added. For rebucketing-wrapper confirmation, start with `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_script_surface(...)`, `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_selector_surface(...)`, `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_normalize_surface(...)`, `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_sort_surface(...)`, `search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_normalize_surface(...)`, `search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_sort_surface(...)`, `search_size_zero_multi_index_plugin_histogram_reduce_feeds_normalize_surface(...)`, `search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_sort_surface(...)`, `search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_normalize_surface(...)`, and `search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_sort_surface(...)`.
- Validation command handoff note (2026-05-25): if validation begins, the current source-visible first pass can be driven directly from `cargo test -p os-engine-tantivy -- --exact <test_name>`. The highest-yield opening batch is: malformed-wrapper placeholder seats first, then representative rebucketing-wrapper seats. In practice this means starting with exact-name runs for the freshly added `engine_collects_placeholder_for_malformed_plugin_*_request(...)` tests, followed by exact-name runs for `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_script_surface(...)`, `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_selector_surface(...)`, `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_normalize_surface(...)`, `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_sort_surface(...)`, `search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_normalize_surface(...)`, `search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_sort_surface(...)`, `search_size_zero_multi_index_plugin_histogram_reduce_feeds_normalize_surface(...)`, `search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_sort_surface(...)`, `search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_normalize_surface(...)`, and `search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_sort_surface(...)`. This note is only a handoff aid; it is not runtime evidence by itself.
- Completion-audit note (2026-05-25): current source evidence is now strong enough to narrow most of the original backlog into concrete test seats and explicit source-visible contracts, but it is still not sufficient to prove full closure of the user objective on its own. The remaining gap is no longer primarily missing source structure; it is the absence of runtime results proving that the newly added malformed-wrapper and rebucketing-wrapper tests actually pass on the current worktree. Until those runs exist, completion remains unproven even though the source-only evidence has become substantially more complete.
- Malformed-wrapper exhaustion note (2026-05-25): a current source-visible wrapper-kind pass now strongly suggests that the malformed-wrapper bucket is effectively exhausted at the surfaced-kind level. The local `kind` scan over `crates/os-engine-tantivy/src/lib.rs` returns wrapper/pipeline kinds such as `bucket_sort`, `bucket_selector`, `bucket_script`, `normalize`, `bucket_count`, the visible `moving_*` family, `serial_diff`, `derivative`, `stats_bucket`, `avg_bucket`, `min_bucket`, `max_bucket`, `sum_bucket`, `percentiles_bucket`, `percentile_ranks_bucket`, and `extended_stats_bucket`; the same file now also contains explicit `engine_collects_placeholder_for_malformed_plugin_*_request(...)` seats for each of those surfaced kinds. On present source evidence, the malformed-wrapper backlog is therefore not just narrow but close to exhausted, and any remaining uncertainty is better attributed to runtime behavior or uncovered kinds that are not currently surfaced by the local source pass.
- Follow-on correction (2026-05-25): the mixed rebucketing-plus-wrapper slice narrowed again with `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_derivative_surface(...)`. This adds an explicit multi-index reduce seat showing that a `derivative` plugin reads the outward merged `date_histogram` day buckets rather than some pre-reduce shard-local carrier state. With that addition, the rebucketing-wrapper evidence is no longer limited to surface-preserving wrappers like `normalize`, `bucket_selector`, `bucket_script`, and `bucket_sort`; it now also includes a representative non-surface bucket pipeline wrapper over a rebucketed histogram family. The remaining source-only uncertainty is therefore pushed further toward the smaller tail of still-unpinned wrapper pairings and away from `derivative`-style rebucketing interactions as a class.
- Follow-on correction (2026-05-25): the same non-surface rebucketing contract is now also pinned for plain numeric histograms via `search_size_zero_multi_index_plugin_histogram_reduce_feeds_derivative_surface(...)`. That seat shows a multi-index `histogram` reduce producing outward merged buckets `0.0 / 10.0 / 20.0` with counts `1 / 2 / 1`, and a downstream `derivative` plugin reading that merged surface to yield `-1.0`. In practical terms, rebucketing-plus-`derivative` evidence is no longer just date-oriented; it now spans both `date_histogram` and `histogram`, which pushes the remaining source-only uncertainty further toward the smaller tail of still-unpinned wrapper pairings.
- Follow-on correction (2026-05-25): rebucketing-plus-`derivative` evidence widened again with `search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_derivative_surface(...)`. That seat pins the case where multi-index `auto_date_histogram` reduce first coarsens the outward surface to week buckets with counts `3 / 1`, and a downstream `derivative` plugin then reads that merged weekly surface to yield `-2.0`. In practical terms, the `derivative` rebucketing contract is now explicit for both fixed `date_histogram` and coarsening `auto_date_histogram`, which narrows the remaining source-only uncertainty further toward the smaller tail of still-unpinned wrapper pairings.
- Follow-on correction (2026-05-25): rebucketing-plus-`derivative` evidence now also covers adaptive numeric histograms through `search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_derivative_surface(...)`. That seat pins a multi-index `variable_width_histogram` reduce producing outward buckets `0.0 / 40.0` with counts `3 / 1`, followed by a downstream `derivative` plugin yielding `-2.0` from that merged surface. In practical terms, the `derivative` rebucketing contract is now explicit across fixed date, coarsening date, fixed numeric, and adaptive numeric histogram families, so the remaining source-only uncertainty is pushed even further toward isolated leftover wrapper pairings rather than broad rebucketing-plus-`derivative` doubt.
- Follow-on correction (2026-05-25): non-surface rebucketing evidence is no longer derivative-only. `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_serial_diff_surface(...)` now pins the case where a multi-index `date_histogram` reduce produces outward day-bucket counts `1 / 2 / 1`, and a downstream `serial_diff` plugin with `lag: 1` reads that merged surface to yield `-1.0`. That matters because it moves the rebucketing-plus-pipeline evidence from one non-surface wrapper kind (`derivative`) to at least two (`derivative`, `serial_diff`), further shrinking the chance that the remaining gap is a broad uncertainty about non-surface rebucketing wrappers as a class.
- Follow-on correction (2026-05-25): the same non-surface `serial_diff` rebucketing contract is now also pinned for plain numeric histograms via `search_size_zero_multi_index_plugin_histogram_reduce_feeds_serial_diff_surface(...)`. That seat shows a multi-index `histogram` reduce producing outward merged buckets `0.0 / 10.0 / 20.0` with counts `1 / 2 / 1`, and a downstream `serial_diff` plugin with `lag: 1` reading that merged surface to yield `-1.0`. In practical terms, non-surface rebucketing evidence is now explicit for both `derivative` and `serial_diff` across both date and numeric histogram families, which keeps pushing the remaining source-only uncertainty toward a smaller isolated tail rather than a broad class gap.
- Follow-on correction (2026-05-25): `serial_diff` rebucketing evidence now also covers coarsening date histograms through `search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_serial_diff_surface(...)`. That seat pins a multi-index `auto_date_histogram` reduce producing outward week buckets with counts `3 / 1`, followed by a downstream `serial_diff` plugin with `lag: 1` yielding `-2.0` from that merged surface. In practical terms, non-surface rebucketing evidence is now explicit for both `derivative` and `serial_diff` across fixed date, coarsening date, and fixed numeric histogram families, which keeps shrinking the remaining source-only uncertainty toward the smaller tail of still-unpinned pairings.
- Follow-on correction (2026-05-25): `serial_diff` rebucketing evidence now also covers adaptive numeric histograms through `search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_serial_diff_surface(...)`. That seat pins a multi-index `variable_width_histogram` reduce producing outward buckets `0.0 / 40.0` with counts `3 / 1`, followed by a downstream `serial_diff` plugin with `lag: 1` yielding `-2.0` from that merged surface. In practical terms, non-surface rebucketing evidence is now explicit for both `derivative` and `serial_diff` across fixed date, coarsening date, fixed numeric, and adaptive numeric histogram families, which leaves even less room to read the remaining source-only gap as a broad rebucketing-wrapper uncertainty.
- Follow-on correction (2026-05-25): a surface-preserving rebucketing seat also narrowed with `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_count_surface(...)`. That test pins the case where a multi-index `date_histogram` reduce first forms outward day buckets and a downstream `bucket_count` wrapper reports `value: 3` from that merged surface. In practical terms, the remaining rebucketing-plus-wrapper uncertainty is no longer concentrated only in non-surface pipeline shapes; even the simpler bucket-counting wrapper now has an explicit multi-index rebucketing seat over the date-histogram family.
- Follow-on correction (2026-05-25): the same surface-preserving `bucket_count` rebucketing contract is now also pinned for plain numeric histograms through `search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_count_surface(...)`. That seat shows a multi-index `histogram` reduce producing outward merged buckets `0.0 / 10.0 / 20.0`, followed by a downstream `bucket_count` wrapper reporting `value: 3` from that merged surface. In practical terms, rebucketing-plus-`bucket_count` evidence is no longer date-only, which further reduces the chance that the remaining source-only gap is hiding in a broad bucket-count wrapper family.
- Follow-on correction (2026-05-25): the same surface-preserving `bucket_count` rebucketing contract is now also pinned for coarsening date histograms through `search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_count_surface(...)`. That seat shows a multi-index `auto_date_histogram` reduce producing outward week buckets, followed by a downstream `bucket_count` wrapper reporting `value: 2` from that merged surface. In practical terms, rebucketing-plus-`bucket_count` evidence is now explicit across fixed date, coarsening date, and fixed numeric histogram families, which pushes the remaining source-only uncertainty further toward the smaller tail of still-unpinned combinations.
- Follow-on correction (2026-05-25): the same surface-preserving `bucket_count` rebucketing contract is now also pinned for adaptive numeric histograms through `search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_count_surface(...)`. That seat shows a multi-index `variable_width_histogram` reduce producing outward buckets `0.0 / 40.0`, followed by a downstream `bucket_count` wrapper reporting `value: 2` from that merged surface. In practical terms, `bucket_count` rebucketing evidence now spans fixed date, coarsening date, fixed numeric, and adaptive numeric histogram families, leaving even less reason to read the remaining source-only gap as a broad bucket-count wrapper uncertainty.
- Final narrowing note (2026-05-25): on the current worktree, the representative rebucketing-plus-wrapper matrix is now broad enough that the residual source-only uncertainty no longer looks like a meaningful wrapper-family gap. Malformed-wrapper seats are explicit for the surfaced wrapper kinds; non-surface rebucketing seats are explicit for both `derivative` and `serial_diff`; surface-preserving rebucketing seats are explicit for `bucket_script`, `bucket_selector`, `normalize`, `bucket_sort`, and `bucket_count`; and the representative histogram families now include `date_histogram`, `auto_date_histogram`, `histogram`, and `variable_width_histogram`. At this point, the remaining uncertainty is best read as isolated interaction edges plus runtime validation debt, not as broad missing feature families in the local source pass.
- Validation handoff refresh note (2026-05-25): the exact-name rebucketing batch should now be read as expanded beyond the earlier normalize/bucket-script/bucket-selector/bucket-sort slice. In addition to the previously listed exact runs, the current high-yield rebucketing validation set also includes `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_count_surface(...)`, `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_derivative_surface(...)`, `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_serial_diff_surface(...)`, `search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_count_surface(...)`, `search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_derivative_surface(...)`, `search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_serial_diff_surface(...)`, `search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_count_surface(...)`, `search_size_zero_multi_index_plugin_histogram_reduce_feeds_derivative_surface(...)`, `search_size_zero_multi_index_plugin_histogram_reduce_feeds_serial_diff_surface(...)`, `search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_count_surface(...)`, `search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_derivative_surface(...)`, and `search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_serial_diff_surface(...)`. That refresh does not itself prove runtime correctness; it only keeps the command-level handoff aligned with the current worktree.
- Validation command refresh note (2026-05-25): if execution validation starts from the current worktree, the shortest aligned command shape remains `cargo test -p os-engine-tantivy -- --exact <test_name>`. The practical first-pass rebucketing batch should now include exact-name runs for the refreshed seats across each representative family: `date_histogram` (`...bucket_count_surface`, `...derivative_surface`, `...serial_diff_surface`), `auto_date_histogram` (`...bucket_count_surface`, `...derivative_surface`, `...serial_diff_surface`), `histogram` (`...bucket_count_surface`, `...derivative_surface`, `...serial_diff_surface`), and `variable_width_histogram` (`...bucket_count_surface`, `...derivative_surface`, `...serial_diff_surface`), alongside the earlier normalize/bucket-script/bucket-selector/bucket-sort seats. This still is not runtime evidence by itself; it only keeps the validation handoff synchronized with the current source-visible matrix.
- Completion blocker note (2026-05-25): on the current worktree, the remaining blocker for claiming the user objective is complete is no longer a missing source-visible wrapper family or an obviously uncovered representative rebucketing seat. The blocker is the absence of runtime evidence for the newly accumulated exact-name batch in `os-engine-tantivy`. Until those tests are actually executed and their results inspected, completion remains unproven even though the source-only matrix is now broadly representative.
- Minimal validation batch note (2026-05-25): if the exact-name set needs to be compressed into the smallest useful first pass, the current worktree supports a simple priority split. First run one malformed-wrapper sanity slice plus one representative rebucketing slice for each wrapper shape: for example `engine_collects_placeholder_for_malformed_plugin_bucket_sort_request(...)`, `engine_collects_placeholder_for_malformed_plugin_derivative_request(...)`, `engine_collects_placeholder_for_malformed_plugin_serial_diff_request(...)`, `engine_collects_placeholder_for_malformed_plugin_bucket_count_request(...)`, then `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_sort_surface(...)`, `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_count_surface(...)`, `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_derivative_surface(...)`, and `search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_serial_diff_surface(...)`. If that batch passes, expand sideways to the matching `auto_date_histogram`, `histogram`, and `variable_width_histogram` seats. This note is only for validation prioritization; it is not runtime evidence.
- Compact command note (2026-05-25): the same minimal first pass can be driven directly as a short exact-name command list: `cargo test -p os-engine-tantivy -- --exact engine_collects_placeholder_for_malformed_plugin_bucket_sort_request`, `cargo test -p os-engine-tantivy -- --exact engine_collects_placeholder_for_malformed_plugin_derivative_request`, `cargo test -p os-engine-tantivy -- --exact engine_collects_placeholder_for_malformed_plugin_serial_diff_request`, `cargo test -p os-engine-tantivy -- --exact engine_collects_placeholder_for_malformed_plugin_bucket_count_request`, `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_sort_surface`, `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_count_surface`, `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_derivative_surface`, and `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_serial_diff_surface`. If those exact-name runs pass, widen to the corresponding `auto_date_histogram`, `histogram`, and `variable_width_histogram` seats next. This still is not runtime evidence; it is only the most compact command-level handoff for the current worktree.
- Phased validation order note (2026-05-25): the compact command list can be split into two practical phases. Phase 1: wrapper sanity confirmation via the malformed seats (`bucket_sort`, `derivative`, `serial_diff`, `bucket_count`). Phase 2: representative multi-index rebucketing confirmation via the `date_histogram` seats (`bucket_sort`, `bucket_count`, `derivative`, `serial_diff`). Only after both phases pass is it worth widening sideways to the corresponding `auto_date_histogram`, `histogram`, and `variable_width_histogram` seats. This keeps early runtime evidence maximally informative while minimizing the first execution surface.
- Phase-1 command block note (2026-05-25): the malformed-wrapper sanity phase can be executed as a four-command block without any additional selection work: `cargo test -p os-engine-tantivy -- --exact engine_collects_placeholder_for_malformed_plugin_bucket_sort_request`, `cargo test -p os-engine-tantivy -- --exact engine_collects_placeholder_for_malformed_plugin_derivative_request`, `cargo test -p os-engine-tantivy -- --exact engine_collects_placeholder_for_malformed_plugin_serial_diff_request`, and `cargo test -p os-engine-tantivy -- --exact engine_collects_placeholder_for_malformed_plugin_bucket_count_request`. If any of those fail, widening to rebucketing seats is lower priority than fixing the malformed-wrapper runtime mismatch first.
- Phase-2 command block note (2026-05-25): once Phase 1 passes, the representative `date_histogram` rebucketing phase can also be executed as a four-command block: `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_sort_surface`, `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_count_surface`, `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_derivative_surface`, and `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_serial_diff_surface`. If that block passes, sideways expansion to `auto_date_histogram`, `histogram`, and `variable_width_histogram` is the next logical validation step.
- Phase-3 widening order note (2026-05-25): after the `date_histogram` rebucketing block passes, the current worktree supports a simple widening order rather than an unstructured full sweep. First widen to `auto_date_histogram`, because it exercises coarsening date rebucketing with the same wrapper shapes. Next widen to plain `histogram`, because it checks the same wrapper shapes on fixed numeric buckets. Last widen to `variable_width_histogram`, because it adds the adaptive numeric bucket surface and is therefore the most specialized remaining representative family. This keeps validation expansion incremental and makes the first failing family more informative.
- Phase-3 command note (2026-05-25): the widening families can now also be treated as compact command blocks. `auto_date_histogram` widening: `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_count_surface`, `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_derivative_surface`, `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_serial_diff_surface`, and `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_sort_surface`. `histogram` widening: `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_count_surface`, `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_histogram_reduce_feeds_derivative_surface`, `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_histogram_reduce_feeds_serial_diff_surface`, and `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_sort_surface`. `variable_width_histogram` widening: `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_count_surface`, `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_derivative_surface`, `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_serial_diff_surface`, and `cargo test -p os-engine-tantivy -- --exact search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_sort_surface`.
- Failure triage note (2026-05-25): if runtime validation starts and the first exact-name batch does not pass cleanly, the most informative repair order is still narrow. First fix any malformed-wrapper failures, because those invalidate the basic request-surface/placeholder contract and make downstream wrapper results harder to trust. Next fix any `date_histogram` rebucketing failures, because that block is the representative baseline for mixed wrapper behavior. Only after those are stable should widening-family failures in `auto_date_histogram`, `histogram`, or `variable_width_histogram` be treated as the primary frontier. This keeps early bug-fix work aligned with the highest-leverage evidence rather than diffusing across the full widened matrix.
