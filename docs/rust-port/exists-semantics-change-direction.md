# exists-semantics-change-direction

## Purpose

Record the follow-on direction to take if
`docs/rust-port/exists-semantics-follow-on.md` concludes that the remaining
`exists` gap is a real semantic mismatch rather than only a wording/reporting
issue.

## Preconditions

This direction should only be taken after
`docs/rust-port/exists-semantics-follow-on.md`
and
`docs/rust-port/exists-semantics-deeper-contract-check.md`
find concrete semantic mismatch evidence beyond the current
presence-oriented/bounded contract framing.

## Upstream notes

- originating gap summary:
  `docs/rust-port/tantivy-native-gap-analysis.md`
- semantic follow-on review note:
  `docs/rust-port/exists-semantics-follow-on.md`
- deeper semantic/contract check note:
  `docs/rust-port/exists-semantics-deeper-contract-check.md`

## Proposed direction

- Treat the next step as a targeted `exists` semantics change task.
- Do not reopen the whole search-response/materialization axis for this issue.
- Keep the scope on concrete semantic differences between the current
  presence-oriented behavior and the stronger behavior that would need to be
  claimed.

## First implementation focus

- Identify whether the mismatch sits in:
  - matching behavior
  - explain/highlight wording
  - payload/documentation claims
- Narrow the change to the exact field families or query/reporting paths that
  over- or under-claim current `exists` semantics.

## Explicit non-claim

- This note does not itself establish that a broader semantic mismatch exists.
- It only records the direction to take if the separate `exists` follow-on note
  concludes that the remaining gap is stronger than wording/reporting drift.
