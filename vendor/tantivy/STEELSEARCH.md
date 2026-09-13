# SteelSearch Native Extension

Source: crates.io `tantivy` 0.21.1, copied from the pinned Cargo source package.
The upstream `.cargo_vcs_info.json`, license, authors and package source are
preserved. Cargo's local `.cargo-ok` cache marker is not part of this import.

Modified upstream files: `src/query/bm25.rs`, `src/query/score_combiner.rs`,
`src/query/union.rs`, and `src/query/mod.rs`.
Added file: `src/query/minimum_should_match.rs`.

- Added `Bm25Weight::score_fractional` and `explain_fractional` for non-negative,
  finite phrase frequencies, using the existing weight and fieldnorm cache.
- Existing integer scoring, IDF/statistics calculation and query APIs are unchanged.
- Added `MinimumShouldMatchQuery`, which uses the existing buffered Union and a
  counting score combiner instead of enumerating combinations. Each matching
  child contributes once, including zero-score children to the match count.
- ScoreCombiner has an opt-in membership predicate. Existing combiners retain
  the unfiltered path; threshold queries filter buffered membership before any
  collector can consume it. Empty horizons are skipped, and bulk Count clears
  threshold accumulators before reusing the buffer.
- The new weight uses the standard scorer-based collector methods, without
  dispatching to a BlockWAND path that has no minimum-match constraint.
- No shared Cargo registry files are modified.

This dependency extension does not establish HTTP compatibility or performance
acceptance. Follow the fixed v0.6.0 cumulative gate in `AGENTS.md` before completing
its production integration.
