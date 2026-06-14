# knn-own-vector-field-observation-follow-on

## Purpose

Track the remaining narrower `knn.field` / own-vector-field observation work
that still survives after the broader representative `knn` and hybrid
coverage gains already landed on the current Tantivy-native path.

## Upstream note

- originating gap summary:
  `docs/rust-port/tantivy-native-gap-analysis.md`

## Current reading

- This is not a broad "missing `knn` seat" problem anymore.
- It is a narrower tail around how current `knn.field` / own-vector-field
  observation semantics should be framed and generalized after the larger
  representative vector/hybrid gains already landed.
- So this axis should be read as a narrower semantic/behavioral follow-on note
  rather than as a broad vector backlog by itself.

## Current repo-local framing

- The main vector backlog is now broader execution/generalization work.
- This tail remains explicitly narrower and already more shape-aware than the
  older generic vector gap wording.
- The current runtime/evidence stack now already covers:
  - wrapped `knn` candidate-path traversal across the current bounded
    `bool` / `nested` surface, including bounded required
    `should(knn)` candidate paths
  - bounded `must_not(knn)` bool exclusion semantics
  - bounded zero-`minimum_should_match` bool semantics
  - bounded top-level `k`-limit application only for the current pure
    candidate-path subset
  - narrower semantic fixture pinning for those bool semantics
  - route-level runtime tests that now pin the same bounded required
    `should(knn)`, optional `should(knn)`, `must_not`, and zero-
    `minimum_should_match` semantics directly, including nested
    `must_not(knn)` exclusion behavior
- The current question is therefore less "can Steelsearch do `knn` at all?"
  and more "what, exactly, still remains around `knn.field`/own-vector-field
  observation semantics after the broader representative vector path gains?".

## Suggested follow-on questions

- Which exact `knn.field` / own-vector-field observation behaviors remain
  narrower than the intended OpenSearch-facing contract?
- Is the remaining gap mainly documentation/reporting, or is there a concrete
  semantic/runtime mismatch still worth isolating?
- Which vector-specific fixtures or runtime paths would best pin the remaining
  observation behavior directly?

## Suggested evidence targets

- current `knn.field` wording in `tantivy-native-gap-analysis.md`
- nearby vector/hybrid fixtures and notes
- runtime paths that still inspect or normalize `knn.field` / own-vector-field
  observation behavior

## Current default reading

- Treat this as a narrower tail note, not as the main remaining vector backlog.
- The main question is to isolate the exact remaining observation semantics,
  not to reopen the larger representative `knn` execution surface.
- After the current bounded bool/`knn` runtime alignment work, this note should
  default to "deeper `knn.field` / own-vector-field observation mismatch, if
  any" rather than to another pass over wrapped candidate-path admission.

## Preferred immediate next target

- Start from the exact runtime/documentation paths that still normalize or
  describe `knn.field` / own-vector-field observation behavior differently
  from the broader representative `knn` coverage already pinned elsewhere.

## First concrete reading targets

- documentation side:
  `docs/api-spec/vector-and-ml.md`, especially the current
  `knn` / hybrid supported-subset contract wording around the documented vector
  field subset and selected filter coupling inside the `knn` field object
- runtime side:
  `crates/os-node/src/standalone_runtime.rs`, starting from
  `validate_knn_target_capabilities(...)` and the nearby request/runtime
  validation that decides which `knn` target-field shapes stay inside the
  current bounded contract

## Practical stop-point reading

- Unless that narrower observation review surfaces a concrete semantic/runtime
  mismatch, this tail should remain a small follow-on note rather than
  expanding back into the main vector backlog.
- After the current bool/`knn` runtime alignment work, the remaining question
  is even narrower: not general wrapped-placement admission, but whether any
  deeper `knn.field` / own-vector-field observation mismatch still survives
  beyond those now-aligned bounded bool/nested semantics.
