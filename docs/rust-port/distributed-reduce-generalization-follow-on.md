# distributed-reduce-generalization-follow-on

## Purpose

Track the broader remaining distributed and multi-index reduce generalization
work beyond the mergeable native/vector-native subsets already covered on the
current Tantivy-native path.

## Upstream note

- originating gap summary:
  `docs/rust-port/tantivy-native-gap-analysis.md`

## Current reading

- This is no longer a question of whether any native multi-index reduce path
  exists at all.
- The remaining gap is broader cross-index/shard orchestration breadth beyond
  the current mergeable page/page-reduce and page+aggregation reduce subsets.
- So this axis should be read as a broader backlog/generalization note rather
  than as a small local representative-seat cleanup.

## Current repo-local framing

- Current coverage already includes representative native page-reduce and
  page+aggregation reduce paths for:
  - lexical multi-index searches
  - mergeable native aggregation subsets
  - representative vector-native and hybrid page+aggregation reduce subsets
  - representative `size=0` native aggregation reduce subsets
- Current remaining gap is therefore less "missing reduce seat" and more
  "broader distributed orchestration outside the mergeable representative
  subset".

## Suggested follow-on questions

- Which broader reduce shapes still escape to generic compatibility reduction?
- Which remaining gaps are mainly about non-mergeable aggregation families,
  broader shard/index orchestration, or hit-fetch-elision generalization?
- Which broader reduce shapes are high-payoff enough to deserve the next native
  generalization pass?

## Suggested evidence targets

- current distributed-reduce wording in
  `tantivy-native-gap-analysis.md`
- representative multi-index native/vector-native reduce fixtures
- code-path boundaries between native mergeable reduce and generic
  compatibility reduction

## Current default reading

- Treat this as a broader breadth/generalization backlog note, not as the next
  narrow stop-point-style contract question.
- The main question is prioritization among broader reduce-shape expansions,
  not whether one last local representative reduce seat is still missing.
- Preferred immediate next target:
  start from the broader distributed/vector-native reduce shapes that still
  fall back outside the current mergeable native subset, especially where
  non-mergeable aggregation combinations or broader orchestration still force
  the generic compatibility reduction path.
- First concrete reading target:
  start from the residual boundary already summarized in the main gap analysis
  through the current mergeable-distributed-reduce subset wording and the
  broader distributed-reduce residual-family wording, and treat that line as
  the shorthand for the next reduce-shape families that still escape native
  merge/reduce coverage.
- Current best candidate shape family:
  broader distributed/vector-native reduce shapes that fall outside the current
  mergeable native subset because of non-mergeable aggregation combinations or
  heavier cross-index orchestration requirements.
- Current best candidate subfamily:
  multi-index vector/native page+aggregation reduce shapes whose aggregation
  combinations are still non-mergeable enough to force generic compatibility
  reduction.
- Practical prioritization reading:
  favor the next reduce-shape family that removes generic cross-index
  orchestration for multiple representative requests at once, rather than one
  more very narrow reduce-seat admission.
