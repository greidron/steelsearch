# Lucene Position Traversal Attribution

`crates/os-engine-tantivy/src/native_phrase_positions.rs` adapts the single-term
phrase position traversal from Apache Lucene 10.4.0 `SloppyPhraseMatcher` to Rust.
The adaptation uses Tantivy postings and a bounded lazy-update standard-library
heap. It does not vendor the Lucene Java runtime or its other components.

Upstream source:
https://github.com/apache/lucene/blob/releases/lucene/10.4.0/lucene/core/src/java/org/apache/lucene/search/SloppyPhraseMatcher.java

`LICENSE.txt` and `NOTICE.txt` are unmodified copies of the upstream release's
root files. The upstream notice describes the whole Lucene distribution; its
other listed components are not implied to be included in this adaptation.

The adaptation is connected to the engine's native sloppy phrase scorer.
Production integration validation and the cumulative performance gate are not complete.
