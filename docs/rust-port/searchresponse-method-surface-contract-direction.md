# searchresponse-method-surface-contract-direction

## Purpose

Record the contract-shaping direction to take if
`raw-searchresponse-hits-contract-expectation-review` does not uncover a
stronger compatibility promise around direct raw `SearchResponse.hits` field
access.

## Preconditions

This direction should only be taken after
`docs/rust-port/raw-searchresponse-hits-contract-expectation-review.md`
and
`docs/rust-port/searchresponse-hits-downstream-compatibility-check.md`
conclude that no concrete contrary evidence requires direct raw
`SearchResponse.hits` field access to remain a separately supported contract
surface.

## Upstream notes

- originating stop-point note:
  `docs/rust-port/tantivy-native-gap-analysis.md`
- external expectation review note:
  `docs/rust-port/raw-searchresponse-hits-contract-expectation-review.md`
- downstream compatibility check note:
  `docs/rust-port/searchresponse-hits-downstream-compatibility-check.md`

## Proposed direction

- Treat the `SearchResponse` method cluster as the preferred long-term
  compatibility surface for response-hit access semantics.
- Stop treating raw public `SearchResponse.hits` field access as the default
  contract surface merely because it is currently exposed.

## Repo-local basis

- Examined repo-internal production paths are already substantially lowered
  onto method seams.
- The method cluster already covers common collection responsibilities:
  - borrowed slice access
  - borrowed iteration
  - first / last / indexed read
  - count / emptiness
  - owned vector transfer
  - owned iterator transfer
  - post-pass mutation
  - iterator-based construction
  - final response serialization
- Nearby public-facing docs and fixtures speak primarily in JSON payload terms
  rather than in direct Rust-field-access terms.
- Workspace/manifest evidence currently looks more like internal crate usage
  than like a separately published library promise around raw field stability.

## Immediate implementation implications

- Prefer future response-surface cleanup that strengthens or relies on the
  method seam cluster rather than introducing new dependence on raw
  `SearchResponse.hits` field access.
- Frame any subsequent change on this axis as a response-contract surface
  decision, not as another search for missing helper coverage.

## Adoption checklist

- Treat [lib.rs](/home/ubuntu/steelsearch/crates/os-engine/src/lib.rs) as the
  primary contract-shaping surface, since that is where `SearchResponse`,
  `SearchShardSearchResult`, and the current method cluster live.
- Treat [action.rs](/home/ubuntu/steelsearch/crates/os-transport/src/action.rs)
  as the immediate wrapper surface that should continue mirroring the intended
  response-access contract.
- Avoid reopening lower-level `os-engine-tantivy` helper cleanup as the first
  move on this axis; that work already reached a practical stop-point for the
  current question.
- If the direction is adopted, review whether docs and nearby notes should stop
  speaking as though raw `SearchResponse.hits` field access is the default
  contract surface.

## Explicit non-claim

- This note does not itself prove that direct raw `SearchResponse.hits` field
  access is unsupported everywhere.
- It only records the direction that follows if the external expectation review
  fails to find a stronger contrary compatibility promise.
