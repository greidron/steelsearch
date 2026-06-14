# raw-searchresponse-hits-contract-expectation-review

## Purpose

Determine whether direct `SearchResponse.hits` field access is an intentional
supported contract surface, or only the current exposed representation.

## Current internal reading

- Examined repo-internal production paths now lean away from requiring raw
  field access as the primary compatibility surface.
- `SearchResponse`, `SearchShardSearchResult`, and
  `SteelsearchShardSearchResponseWire` already expose broad method seams for:
  - borrowed slice access
  - borrowed iteration
  - first / last / indexed read
  - count / emptiness
  - owned vector transfer
  - owned iterator transfer
  - post-pass mutation
  - iterator-based construction
  - final response serialization
- Examined production wrapper paths are already largely lowered onto those
  seams rather than peeling raw `hits` fields directly.

## Current repo-local evidence

- `os-engine` and `os-transport` currently appear as workspace crates in this
  repo, with local path dependencies and no separate published-package surface
  evidence shown in the nearby manifests.
- In `crates/os-engine` production code, raw `self.hits` touches are now mostly
  concentrated inside `SearchResponse` method bodies.
- In `crates/os-transport` production code, response wrappers already delegate
  through method seams instead of directly exposing a peeled
  `result.response.hits` chain at use sites.
- Broader repo scans did not surface strong additional production call-site
  pressure around raw `response.hits`; remaining direct references were
  dominated by tests.
- Nearby public-facing docs describe REST/raw response payload semantics and
  response shaping, but do not currently appear to elevate direct
  `SearchResponse.hits` Rust field access into a separately documented external
  contract.
- Nearby fixture-style compatibility artifacts also reinforce that split:
  they assert raw response payload paths such as `hits.hits._id` and
  `hits.hits._source`, not direct Rust-field access on `SearchResponse`.
- A narrower repo scan also did not surface broader public-facing uses of the
  `SearchResponse` Rust type beyond its internal crate definition path, while
  nearby public-facing artifacts continued to speak in JSON payload terms.
- Nearby search-facing API docs likewise tend to point at runtime response
  shaping in `standalone_runtime.rs` and documented payload fields, not at a
  Rust-library contract centered on direct `SearchResponse` field access.

## Review checklist

- Identify whether any external caller is documented or implicitly allowed to
  depend on direct `SearchResponse.hits` field access itself rather than on
  equivalent response methods.
- If such callers exist, determine whether that promise is:
  - intentional and long-term
  - or only the current accidental exposed shape
- Check whether any stable integration surface or compatibility statement
  mentions direct response field access rather than method-based access.

## Evidence targets

- downstream public docs and examples
- stable integration surface descriptions
- cross-crate public usage outside the already-examined internal production
  paths
- explicit compatibility promises mentioning direct response field access
- obvious published Rust package surfaces or API docs, if they exist at all

## Decision boundary

- If a stronger external raw-field compatibility promise exists, keep treating
  direct `SearchResponse.hits` field access as part of the supported contract
  surface.
- Otherwise, the current internal evidence supports treating the method seam
  cluster as the preferred long-term compatibility surface.

## Resolution rule

- If this review does not find concrete contrary evidence, close it by
  continuing through the narrower downstream-compatibility confirmation check
  rather than by treating the direction note as immediately decided.
- The concrete targeted follow-on note for that clean-resolution case is:
  `docs/rust-port/searchresponse-hits-downstream-compatibility-check.md`
- If that targeted check also does not surface concrete contrary evidence, the
  follow-on decision note is:
  `docs/rust-port/searchresponse-method-surface-contract-direction.md`

## Current repo-local review result

- No concrete repo-local evidence has yet been identified that clearly requires
  direct `SearchResponse.hits` field access to remain a separately supported
  contract surface.
- The strongest current repo-local signals instead continue to point toward:
  - response JSON/payload compatibility as the visible public-facing contract
  - workspace-internal crate usage for the Rust type surface
  - method-seam coverage being sufficient for the examined internal production
    paths
- Therefore, within the current repo-local evidence boundary, the external
  review remains open mainly as a check for overlooked contrary evidence rather
  than because a positive raw-field contract promise has already been found.

## Repo-local review status

- The repo-local portion of this review now looks substantially exhausted for
  the current pass.
- Further meaningful movement is more likely to come from evidence outside the
  current repo-local code/docs/fixture/manifests boundary than from another
  round of local search for the same raw-field promise.

## Current external-scan reading

- A light external scan did not surface an obvious published Rust package/API
  surface for `os-engine` or a separately documented `SearchResponse` Rust
  type contract that would already elevate direct `SearchResponse.hits` field
  access into a clear external promise.
- A more targeted external scan over GitHub/docs.rs/crates.io-style search
  surfaces likewise did not surface an obvious Steelsearch Rust package/API
  listing or external code/docs hit that clearly treats direct raw
  `SearchResponse.hits` access as a published compatibility promise.
- The more visible external search hits around `SearchResponse` instead pointed
  at OpenSearch Java/.NET response surfaces and other unrelated search
  libraries, which is not evidence of a Steelsearch-specific raw-field promise.
- So the current external uncertainty still reads more like "possible unseen
  downstream dependency" than like "already visible public contract evidence".

## Current recommendation

- Default internal leaning: prefer the method-surface direction.
- Do not treat that as final until the external raw-field contract expectation
  is explicitly reviewed.
- Based on current repo-local code, docs, and manifest evidence alone, the
  working recommendation is to assume no special raw-field compatibility promise
  unless concrete contrary evidence is found.
- At this point, the main remaining uncertainty is best framed narrowly as:
  whether some unseen downstream dependency or separately held compatibility
  promise still expects direct raw `SearchResponse.hits` field access
  specifically, despite the lack of obvious repo-local or already-visible
  published-surface evidence for that promise.

## Provisional disposition from current repo-local evidence

- Current repo-local evidence does not yet show a strong, separately documented
  promise that external callers are supposed to rely on direct
  `SearchResponse.hits` field access specifically.
- The stronger current evidence instead points to:
  - the relevant crates looking workspace-internal first, rather than clearly
    documented as a separate public library surface
  - REST/raw payload response semantics being the public-facing documented
    surface
  - search-facing docs pointing at runtime response shaping and payload fields
    rather than at a Rust-library response type surface
  - compatibility fixtures targeting response JSON paths rather than Rust field
    access
  - no strong repo-local public-facing surface for the `SearchResponse` Rust
    type itself showing up beyond the internal crate definition
  - repo-internal production wrappers already leaning onto method seams
  - remaining direct field references being dominated by tests rather than by
    additional production wrapper layers
  - a light external scan not surfacing an obvious Steelsearch Rust package/API
    surface that already documents direct raw-field access as part of the
    supported contract
  - a more targeted external scan likewise not surfacing an obvious
    Steelsearch-specific published API/docs hit that would already make raw
    `SearchResponse.hits` access look like a clearly documented external
    promise
- So the current working assumption for follow-on review should be:
  only keep treating raw `SearchResponse.hits` field access as a supported
  contract if a concrete external compatibility promise or real downstream
  dependency can be identified.

## Remaining uncertainty after the current pass

- The open question is no longer "is there already strong visible evidence of a
  raw-field promise?".
- It is now narrower:
  whether any unseen downstream dependency, unpublished integration surface, or
  separately held compatibility expectation still relies on direct raw
  `SearchResponse.hits` field access specifically.
- If no such evidence appears, the current review should resolve toward the
  method-surface direction recorded in
  `docs/rust-port/searchresponse-method-surface-contract-direction.md`.
- Practical stop-point reading:
  for the current pass, further progress is more likely to come from that
  narrower unseen-dependency / external-promise question than from another
  repo-local search for already-visible raw-field promise evidence.

## Review status after the current scan boundary

- Within the currently visible repo-local plus light/targeted external scan
  boundary, this review now looks close to a practical stop-point.
- The next meaningful move is not another broad search for already-visible
  published-surface evidence, but a more targeted check for concrete
  downstream dependency or separately held compatibility expectations if such
  evidence can be surfaced at all.

## Suggested targeted follow-on task

- task label:
  `searchresponse-hits-downstream-compatibility-check`
- focus:
  look specifically for concrete downstream dependency, unpublished integration
  surface, or separately held compatibility expectations around direct raw
  `SearchResponse.hits` access, rather than repeating broad repo-local or
  already-visible-public-surface scans.
- dedicated note:
  `docs/rust-port/searchresponse-hits-downstream-compatibility-check.md`
