# sort-compatibility-generalization-follow-on

## Purpose

Track the broader remaining sort-compatibility generalization work beyond the
currently native tuple-sort subset and beyond the already-covered
compatibility-path representative shapes.

## Upstream note

- originating gap summary:
  `docs/rust-port/tantivy-native-gap-analysis.md`

## Current reading

- This is no longer a question of whether Steelsearch can sort at all.
- The remaining gap is broader path-shape, script-sort, geo-distance-sort, and
  nested/comparable-family parity breadth beyond the current representative
  native and compatibility-backed coverage.
- So this axis should be read as a broader backlog/generalization note rather
  than as a narrow local missing-seat problem.

## Current repo-local framing

- Current native coverage already includes fast-field-backed tuple sort for
  representative scalar families.
- Current compatibility coverage already includes representative:
  - geo-distance sort
  - numeric script sort families
  - nested sort over dotted object-array paths
  - nested scalar-array flattening
  - `null` / missing-candidate ignore behavior across representative nested
    paths
- The remaining gap is therefore less "missing sort seat" and more "broader
  sort path-shape and compatibility-parity breadth outside the representative
  set".

## Suggested follow-on questions

- Which broader sort shapes still force the most generic compatibility work?
- Which remaining gaps are mainly about wider script-shape support versus
  nested/comparable-path generalization versus collector-side native expansion?
- Which broader sort-shape family would reduce the most shared orchestration
  cost or compatibility drift if generalized next?

## Suggested evidence targets

- current sort backlog wording in `tantivy-native-gap-analysis.md`
- representative sort fixtures and regression notes
- code-path boundaries between native tuple sort and broader compatibility sort
  handling

## Current default reading

- Treat this as a broader breadth/generalization backlog note, not as another
  small representative-seat question.
- The main question is prioritization among broader sort-shape families, not
  whether one last local sort feature is missing.

## Preferred immediate next target

- Start from the broader sort-shape family that still forces the most generic
  compatibility handling across multiple requests, rather than from one more
  narrowly isolated script or nested edge case.

## First concrete reading target

- Start from the residual boundary already summarized in the main gap analysis
  between the current native tuple-sort / representative compatibility-sort
  coverage and the broader sort residual-family wording, and treat that line as
  the shorthand for the next sort-shape families that still force generic
  compatibility handling.

## Current best candidate shape family

- Broader compatibility sort shapes that combine wider script-shape support and
  deeper nested/comparable-path generalization, since those are the families
  most likely to keep generic compatibility handling in place across many sort
  requests after the representative native tuple-sort and current compatibility
  coverage already landed.

## Current best candidate subfamily

- Sort shapes where wider script-shape support and deeper nested/comparable-
  path generalization overlap, because those requests are the ones most likely
  to keep broad compatibility handling alive even after the current
  representative script-sort and nested-sort coverage.

## Practical prioritization reading

- Favor the next sort-shape family that removes shared compatibility-parity or
  orchestration cost across many requests at once.
