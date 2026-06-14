# searchresponse-hits-downstream-compatibility-check

## Purpose

Check whether any concrete downstream dependency, unpublished integration
surface, or separately held compatibility expectation still relies on direct
raw `SearchResponse.hits` field access specifically.

## Upstream notes

- originating gap summary:
  `docs/rust-port/tantivy-native-gap-analysis.md`
- preceding external-expectation review:
  `docs/rust-port/raw-searchresponse-hits-contract-expectation-review.md`

## Why this is now the narrower remaining question

- The current repo-local scan did not surface a strong, separately documented
  raw-field promise.
- Light and targeted external scans likewise did not surface an obvious
  published Steelsearch Rust package/API surface that already treats direct raw
  `SearchResponse.hits` access as a clearly documented compatibility promise.
- So the remaining uncertainty is no longer a broad repo-local/documentation
  search problem.
- It is now the narrower question of whether some less-visible downstream
  dependency or separately held promise still depends on that raw field access.

## Suggested check targets

- known downstream repositories or internal dependents, if any are available
- unpublished integration docs or handoff notes
- issue threads, design notes, or compatibility discussions that mention
  `SearchResponse.hits` directly
- any consumer code that depends on direct field access instead of the current
  method seam cluster

## Decision boundary

- If concrete downstream dependency or compatibility-promise evidence is found,
  keep treating direct raw `SearchResponse.hits` field access as part of the
  supported contract surface.
- Otherwise, close this check by confirming that the remaining uncertainty has
  not materialized into concrete evidence and continue with:
  `docs/rust-port/searchresponse-method-surface-contract-direction.md`

## Current default reading

- No such downstream-dependency or separately held compatibility evidence has
  been surfaced in the current pass.
- So this task should be treated as a targeted confirmation check, not as a
  signal that a stronger raw-field promise is already likely.
- Practical stop-point reading:
  unless some concrete downstream dependency or separately held compatibility
  promise can actually be surfaced, this targeted check should not by itself
  delay the method-surface direction any further.
