# response-materialization-generalization-follow-on

## Purpose

Track the broader remaining response/materialization generalization work beyond
the narrower response-contract note chain and beyond the already-landed
requested-page/page-window reductions.

## Upstream note

- originating gap summary:
  `docs/rust-port/tantivy-native-gap-analysis.md`

## Current reading

- This is no longer mainly a question of one more local fetched-page/helper
  seam cleanup.
- It is broader hit-fetch-elision, response-shaping, and orchestration
  generalization beyond the current single-index and mergeable multi-index fast
  paths.
- So this axis should be read as a broader backlog/generalization note, not as
  a narrow local stop-point-style contract question.

## Current repo-local framing

- Current landed fast paths already cover:
  - requested-page windowing instead of full-hit materialization for multiple
    single-index lexical/vector/hybrid shapes
  - `size=0` hit-materialization skips for representative lexical/vector/hybrid
    no-aggregation and no-`top_hits` shapes
  - narrower `top_hits` window retention instead of full list materialization
  - representative page-result reuse for current lexical/vector native
    page+aggregation fetches
- The remaining gap is therefore less "missing response seat" and more
  "broader hit-fetch-elision/orchestration generalization outside the current
  representative fast-path subset".

## Suggested follow-on questions

- Which broader vector/hybrid or multi-index shapes still force generic
  `SearchHit` materialization or broader compatibility JSON shaping?
- Which remaining costs are mainly about fetch-elision generalization versus
  response-shaping/orchestration layering?
- Which broader shape family would remove the most shared top-of-pipeline
  materialization overhead if generalized next?

## Suggested evidence targets

- current response/materialization backlog wording in
  `tantivy-native-gap-analysis.md`
- page/page+aggregation fast-path notes and fixture coverage
- code-path boundaries between current requested-page fast paths and generic
  hit-materialization/response-shaping paths

## Current default reading

- Treat this as a broader breadth/generalization backlog note, not as another
  local helper-seam cleanup task.
- The main question is prioritization among broader materialization/orchestration
  shape families, not whether one last local response seat is still missing.

## Preferred immediate next target

- Start from the broader vector/hybrid or multi-index shapes that still force
  generic hit materialization or broader compatibility JSON shaping outside the
  current requested-page / `size=0` / mergeable-fast-path subset.

## First concrete reading target

- Start from the residual boundary already named in the main gap analysis as
  `direct_reduce_still_requires_broader_hit_fetch_elision_generalization(...)`,
  and treat it as the current shorthand for the broader shapes that still
  escape the landed requested-page / `size=0` / mergeable-fast-path subset.
- In current code terms, the closest live branch boundary is the multi-index
  requested-page/page+aggregation path that first tries
  `collect_requested_page_reduce_aggregation_response_index_aware_with_collector(...)`
  and then falls through to the materialized final-order hit path whenever
  that collector returns `None`.

## Current nearest live blocker reading

- The nearest repo-local blocker is not a generic response-constructor gap.
- It is the narrower family of multi-index page+aggregation shapes that still
  make the requested-page reduce collector give up through the collector's own
  `None` exits, especially around:
  - `search_candidate_ids_for_query_reduced(...)` failing to keep broader
    vector/hybrid bool candidate reduction on the reduced path
  - shard-local native-reduce hint collection failing closed for a still-broader
    aggregation family
  - `top_hits_window_hits_index_aware(...)` failing to hand back the needed
    per-index top-hits window on the current native/vector-native path
  - `rewrite_top_hits_reduce_windows_for_query_index_aware(...)` failing to
    reuse/request the needed top-hits window
- That is the most direct current seam between the already-landed requested-page
  response shaping and the still-materialized fallback path.

## Current first candidate-reduction reading

- The nearest reduced-path blocker inside that collector gate is no longer the
  already-covered lexical leaf set itself.
- Current helper coverage already reaches:
  - `_id` term / terms / match / range / exists / prefix / wildcard
  - scalar term / terms / match / range / exists
  - keyword/text prefix / wildcard
  - `match_all` / `match_none`
- Current nearby engine evidence also already includes representative
  compatibility lexical-leaf hybrid coverage through wildcard and
  case-insensitive prefix shapes.
- Current nearby engine evidence also already includes much broader
  representative nested compatibility-bool interplay coverage, including
  `must` / `filter` / `must_not` placements and zero-`minimum_should_match`
  variants around those compatibility leaves.
- Current `os-query-dsl::Query` model does not presently expose a much broader
  lexical leaf family beyond that already-admitted helper set.
- So the next candidate-reduction question is better read as deeper
  hybrid/vector bool reduction interplay or a fail-closed gate inside the
  existing reduced-path machinery, rather than as another obvious standalone
  lexical leaf family still waiting to be admitted.

## Current best first implementation seat

- Treat the next likely implementation seat as deeper hybrid/vector bool
  candidate-reduction generalization inside the existing reduced-path helper
  set and gates, not as one more representative scalar leaf addition.
- In practice, that means starting from the reduced-path gates that still send
  hybrid/vector bool requests through the document-backed/query-match-aware
  fallback even after the current scalar/id/prefix/wildcard/match/range/exists
  helper families have already been admitted.

## Current practical implementation-order reading

- If choosing between:
  - deeper hybrid/vector bool candidate reduction inside the current helper set
  - top-hits-window / top-hits-rewrite fail-closed follow-ons
- prefer the candidate-reduction side first for the current pass.
- Current code order makes that the earlier gate for many hybrid/vector bool
  requests, so reducing those fail-closed cases can remove materialized
  fallback pressure before the lower top-hits-window/rewrite seams even become
  the deciding blocker.
- In other words, the next coding pass should start by asking
  "which existing reduced-path bool interplay still returns `None` too early?"
  rather than "which new lexical leaf should be admitted next?".
- The current pass has now already relaxed one of those early fail-closed
  gates: optional `should` clauses (`minimum_should_match = 0`) no longer force
  the whole reduced path to return `None` merely because one optional reduced
  subquery cannot stay on the reduced path.
- Nearby engine regression coverage now also pins that exact gate, and now
  also pins a representative native hit/count match-all surface for
  zero-`minimum_should_match` should-only bools, so this specific
  optional-`should` fail-closed seat should be treated as already moved out of
  the first-open-blocker bucket for the next pass.
- The current pass has also now relaxed the matching required-`should`
  threshold gate: when one `minimum_should_match > 0` `should` clause cannot
  stay on the reduced path, the reduced threshold now falls by the unreduced
  `should` count instead of forcing the whole bool reduction to return `None`.
- Nearby engine regression coverage now now also pins that required-`should`
  threshold relaxation directly, so this early gate should also be treated as
  already moved out of the first-open-blocker bucket for the next pass.
- The current pass has also now relaxed the matching required positive
  `must` / `filter` gate: an unreduced required positive subquery no longer
  forces the whole reduced path to return `None` by itself when another
  reduced positive candidate source remains, and the all-unreduced required
  positive case now falls back to the match-all universe instead of failing
  closed immediately.
- Nearby engine regression coverage now also pins that required positive
  `must` / `filter` relaxation both for mixed required-positive vector/bool
  cases and for the all-unreduced required-positive match-all-universe case,
  so that gate should also be treated as already moved out of the
  first-open-blocker bucket for the next pass.
- The current pass has also now relaxed the empty-bool candidate-reduction
  gate: an empty nested/top-level `bool` no longer falls out of the reduced
  path as `None`, and instead reduces directly to the match-all universe.
- Nearby engine regression coverage now also pins that empty-bool
  match-all-universe reading directly, and now also pins a representative
  native hit/count match-all surface for the same seat, so that seat should
  also be treated as already moved out of the first-open-blocker bucket for
  the next pass.
- The current pass has also now relaxed the matching lexical
  `minimum_should_match > 1` bool native-fallback seat: the current native
  document / hit / page / window / count / `size=0` aggregation paths no
  longer drop straight to `None` on that boundary and now keep a bounded
  document-backed fallback instead, including when that lexical
  `minimum_should_match > 1` seat is reached through a broader nested bool.
- Nearby engine regression coverage now also pins that lexical
  `minimum_should_match > 1` fallback surface directly, so that seat should
  also be treated as already moved out of the first-open-blocker bucket for
  the next pass, including a representative hit-materialization-sensitive
  `top_hits` aggregation case, a representative nested-bool `size=0`
  aggregation case, a representative nested-bool `top_hits`
  aggregation case, and a representative nested-bool hit/page/window
  case including explicit sort.
- The current pass has also now relaxed the matching `must_not` gate: an
  unreduced `must_not` subquery no longer forces the whole reduced path to
  return `None` by itself, and nearby engine regression coverage now pins that
  gate as well, both for positive-candidate bools, for the `must_not`-only
  match-all-universe case, for reducible pure-negative exclusion from that
  universe, and now also for a representative native hit/count pure-negative
  bool surface; the matching lexical `must_not` bool seat also no longer
  preemptively requires native document scan solely because of that exclusion
  placement, helper-level native hit-context and reusable-query-context
  assembly now also prefer the native-buildable query path before falling back
  to document-backed bool assembly, with the reusable-query-context entry now
  also routing through that same shared helper instead of a duplicate
  vector/hybrid page branch, the native document helper likewise now leaning
  on that shared helper after its direct vector-document seat, and the
  matching native count seat now also stays on the direct `Count` collector
  seam, with nearby regression coverage now also pinning both pure-negative
  and mixed-positive lexical `must_not` count examples directly plus
  pure-negative and mixed-positive lexical `must_not` native hit-context
  examples, a mixed-positive lexical `must_not` native hit example, a
  pure-negative and mixed-positive lexical `must_not` native document
  examples, pure-negative plus mixed-positive lexical `must_not`
  reusable-context examples, and both pure-negative and mixed-positive
  reusable-context cases that also keep the optional-all-documents carrier.
- The same native-count seam now also reasserts the older optional-native
  contract when `search_state` is still absent: that entry returns `None`
  instead of a hard error, and nearby regression coverage now pins that
  behavior directly.
- The matching native-document helper also keeps that same optional-native
  contract when `search_state` is absent: it returns `None` instead of a hard
  error, and the current code path now also short-circuits back to `None`
  instead of falling through to a generic document scan there; nearby
  regression coverage now pins that behavior directly too.
- The matching native hit-context helper also keeps that same optional-native
  contract for non-bool native entries when `search_state` is absent: it
  returns `None` instead of a hard error, and nearby regression coverage now
  pins that behavior directly too.
- The matching reusable-query-context entry also keeps that same optional-
  native contract for non-bool native entries when `search_state` is absent:
  it returns `None` instead of a hard error, and nearby regression coverage
  now pins that behavior directly too.
- The matching native hit entry also keeps that same optional-native contract
  for non-bool native entries when `search_state` is absent: it returns
  `None` instead of a hard error, and nearby regression coverage now pins
  that behavior directly too.
- So the next reduced-path question should now be read as the still-deeper
  nested compatibility-bool interplay that remains after those six early
  optional-`should` / required-`should` / required-positive `must`-`filter` /
  empty-bool / lexical `minimum_should_match > 1` / `must_not` fail-closed
  gates have already been moved out of the first-open-blocker bucket.
- That also means the current first-open blocker is no longer another
  representative nested hybrid `minimum_should_match > 1` placement seat:
  those representative placement/evidence rows are already broad enough that
  the next pass should prefer the still-deeper reduced-path/orchestration
  escapes instead.

## Current best candidate shape family

- The current best next family to scrutinize is broader multi-index
  vector/hybrid response shaping outside the current requested-page / `size=0`
  / mergeable-fast-path subset, because that is where generic hit
  materialization and broader compatibility JSON shaping still have the most
  room to survive after the already-landed single-index and mergeable fast
  paths.

## Current best candidate subfamily

- Within that broader family, start from multi-index vector/hybrid
  page+aggregation response shaping that is still outside the current
  requested-page fast path and outside the current mergeable native-reduce
  subset, because that is where hit materialization cost and broader response
  shaping/orchestration still overlap most directly.

## Practical prioritization reading

- Favor the next shape family that removes shared top-of-pipeline
  materialization/orchestration cost across multiple requests at once, rather
  than one more very narrow response-seat admission.
