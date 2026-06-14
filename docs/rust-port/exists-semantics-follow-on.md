# exists-semantics-follow-on

## Purpose

Track the remaining follow-on work around the still more presence-oriented
`exists` leaves that remain called out in the current rust-port gap analysis.

## Upstream note

- originating gap summary:
  `docs/rust-port/tantivy-native-gap-analysis.md`

## Current reading

- The current `exists` behavior is no longer a large missing representative
  seat.
- It is instead a narrower semantic follow-on around how closely current
  behavior should model richer OpenSearch-facing `exists` expectations versus
  continuing to frame the behavior in explicit presence-match terms.
- The current response/materialization line is no longer blocked on this issue;
  this note is about the separate semantic tail that remains after the broader
  representative-seat cleanup.

## Current repo-local framing

- Current wording already explicitly frames the leaf in presence-match terms.
- The remaining question is therefore less "is there an `exists` seat at all?"
  and more "should the current presence-oriented behavior be tightened or
  generalized further?"
- Nearby API-spec wording already describes the current standalone search
  surface in bounded field-presence terms rather than as full OpenSearch
  `exists` parity.
- In `docs/api-spec/search.md`, the current Query DSL summary already groups
  `exists` under a partial standalone subset that supports bounded field
  presence rather than broader OpenSearch parity.
- In `docs/api-spec/search-parameter-coverage-matrix.md`, the finer-grained
  search-facing matrix also treats `exists` as part of a bounded standalone
  subset rather than as an obviously missing broad-parity seat.
- In `crates/os-node/src/standalone_runtime.rs`, the current validation path
  already narrows `exists` to the single supported shape
  `{"exists":{"field":"..."}}`.
- In that same runtime evaluator, the actual match rule is currently a bounded
  `field present && non-null` check rather than a broader configurable
  OpenSearch-parity interpretation surface.
- Official OpenSearch docs also align with much of that bounded reading:
  they describe `exists` support in non-null field terms and describe `null`
  as equivalent to an empty field unless a `null_value` mapping is configured.
- The main gap analysis repeatedly describes the current `exists` tail as
  presence-oriented and already narrowed away from a large missing
  representative seat.

## Suggested review questions

- Where do current `exists` semantics intentionally track presence/non-null
  behavior rather than a broader OpenSearch-facing expectation?
- Which remaining differences are only wording/reporting differences, and which
  are true semantic mismatches?
- Does any current documented payload contract over-claim stronger `exists`
  semantics than the implementation actually provides?

## Suggested evidence targets

- current gap-analysis wording around `exists`
- `docs/api-spec/search.md` wording around bounded field presence
- `docs/api-spec/search-parameter-coverage-matrix.md` and adjacent payload
  contract docs to check whether any stronger `exists` semantics are implied
- current explain/highlight wording that references `exists`
- any payload-facing docs/examples that imply stronger `exists` semantics
- any nearby implementation notes that already describe the current behavior as
  presence-oriented

## Current recommendation

- Treat this as a narrower semantic follow-on, not as the highest-payoff next
  implementation axis while the response-contract review remains open.
- Treat the first pass on this note as a wording-vs-semantics audit, because
  current repo-local wording already leans toward bounded presence semantics
  and does not yet by itself prove a larger semantic mismatch.
- Current API-spec wording already weakens the case for a large semantic reopen,
  because it describes bounded field-presence support rather than claiming full
  OpenSearch `exists` parity.
- The current parameter-coverage matrix weakens that reopen case further,
  because it frames the family as an already-bounded contract surface rather
  than as a placeholder for broad new implementation work.
- Preferred immediate next task:
  audit whether the current remaining `exists` gap is primarily wording/reporting
  or a concrete semantic mismatch.
- Current repo-local audit reading:
  the strongest nearby evidence still points toward a bounded-contract wording
  audit first, not toward a proven need for a broader `exists` implementation
  reopen.
- Current repo-local audit status:
  the nearby docs-side portion of this audit now looks substantially shaped for
  the current pass, and further meaningful movement is more likely to come from
  a direct semantics/code-path review or from evidence that some public-facing
  contract actually implies stronger `exists` behavior than the bounded
  presence framing already documented here.
- Current code-path reading:
  the runtime already makes the bounded semantics fairly explicit, because the
  supported query shape is narrow and the evaluator reduces matching to
  presence-plus-non-null rather than to a larger option surface.
- Current negative-shape evidence reading:
  nearby semantic evidence now also pins an explicit unsupported-shape `400`
  for `exists`, which further supports the reading that the current standalone
  contract is intentionally narrow rather than silently broad.
- Current null-handling evidence reading:
  nearby semantic evidence now also pins the bounded `present && non-null`
  behavior more directly, by distinguishing present-field hits from present-
  but-null non-matches.
- Current nearby public-docs audit reading:
  the closest search-facing docs and coverage matrix entries currently appear
  to stay aligned with that bounded runtime reading instead of over-claiming a
  stronger `exists` contract for the current standalone surface.
- Current official-docs reading:
  official OpenSearch docs also continue to fit the same non-null/empty-field
  framing, which narrows the remaining question further toward "is there any
  stronger contract evidence?" rather than "is the local implementation seat
  still broadly missing?".
- Current repo-local stop-point reading:
  for the current repo-local pass, this axis now looks near a practical
  stop-point unless some deeper code-path or external contract evidence turns
  up a stronger `exists` semantic claim than the bounded one already pinned
  here.
- Current source-backed matcher reading after the latest semantics tighten:
  the local `exists` behavior now also distinguishes `[]` and arrays of only
  `null` values from true existing values, while still treating arrays with at
  least one non-null member as existing.
- Current repo-local implementation reading after that tighten:
  source-backed candidate reduction, document matching, explanation
  observations, and fallback highlight gating now all share the same bounded
  value-presence rule instead of the older plain `present && non-null` check.
- Task chain from this note:
  this note -> `docs/rust-port/exists-semantics-deeper-contract-check.md` ->
  keep as bounded semantic note, or reopen from
  `docs/rust-port/exists-semantics-change-direction.md`

## Resolution rule

- If the first pass finds that the remaining gap is primarily wording/reporting,
  continue through the deeper semantic/contract check rather than reopening a
  larger search implementation axis immediately.
- The concrete targeted follow-on note for that narrower check is:
  `docs/rust-port/exists-semantics-deeper-contract-check.md`
- If that check then finds a concrete semantic mismatch beyond the current
  presence-oriented contract, reopen it as a targeted `exists` semantics
  change task rather than as a broad representative-seat gap.
- The concrete follow-on note for that semantic-mismatch case is:
  `docs/rust-port/exists-semantics-change-direction.md`
- Default clean-resolution reading:
  absent evidence of a stronger semantic mismatch, keep treating the current
  `exists` tail as a narrower bounded semantic note rather than as a top-level
  representative-gap reopening.
- Clean repo-local handoff reading:
  unless a direct semantics/code-path audit turns up a stronger mismatch, this
  axis should currently pause as a bounded-contract wording note rather than
  reopen immediately as broader implementation work.
- Current repo-local review result:
  no nearby docs/code-path evidence currently forces a broader `exists`
  implementation reopen; what it does force is keeping the documented contract
  honest about the existing `field present && non-null` reading.
- Current clean-pass audit result for this note:
  this repo-local pass did not uncover a nearby wording mismatch large enough
  to justify reopening `exists` as broader implementation work on its own.
- Current repo-local evidence stack:
  docs wording, runtime shape validation, runtime `field present && non-null`
  matching, present-versus-null semantic evidence, and explicit unsupported-
  shape semantic evidence, plus the same broad non-null/empty-field framing in
  official OpenSearch docs, now all point in the same bounded-contract
  direction for the current pass.
- Preferred next question after this stop-point:
  not "is another local `exists` implementation seat missing?" but
  "does any deeper semantic or external contract evidence require a stronger
  `exists` promise than the bounded one already documented here?"
- Practical stop-point reading:
  for the current pass, further progress is more likely to come from that
  narrower deeper-semantic / external-contract question than from another
  repo-local wording expansion or local implementation-seat search.
- Suggested targeted follow-on task:
  `exists-semantics-deeper-contract-check`
- Dedicated targeted follow-on note:
  `docs/rust-port/exists-semantics-deeper-contract-check.md`
