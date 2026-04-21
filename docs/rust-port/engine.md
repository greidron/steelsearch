# Engine Strategy

## Decision

Lucene will not be replaced by a full Rust 1:1 implementation at the beginning.
The project will use an engine abstraction and start with a Rust-native engine
for new indexes. Lucene file-format compatibility remains a long-term track.

## Engine Tracks

### Rust-native Engine

Purpose:

- Get a working OpenSearch-compatible Rust server quickly.
- Support new indexes with a Rust-owned format.
- Validate REST, query DSL, mapping, and shard lifecycle behavior.

Likely first backend:

- Tantivy

Known limits:

- Not Lucene segment-compatible.
- Scoring and query behavior will differ until explicitly matched.
- Java OpenSearch data-node mixed replica sets are not supported.

### JVM Lucene Bridge

Purpose:

- Preserve Lucene behavior when mixed-cluster compatibility is the priority.
- Avoid reimplementing Lucene internals before protocol compatibility is proven.

This remains an option for a later mixed-cluster data-node milestone.

### Lucene-Compatible Rust Engine

Purpose:

- Read existing Lucene/OpenSearch index data.
- Eventually write Lucene-compatible segments.

This is long-term work and should be staged:

1. Segment metadata reader.
2. Stored fields reader.
3. Terms and postings reader.
4. Doc values reader.
5. Query execution over read-only segments.
6. Segment writer.
7. Merge policy and NRT writer.

## Required Engine Semantics

The engine abstraction must eventually expose:

- index document
- delete document
- get document by id
- refresh
- flush
- search
- commit metadata
- translog boundaries
- sequence number assignment
- primary term checks
- replica application
- recovery snapshot
- store file metadata

The initial `os-engine` crate is intentionally small. It should grow only as the
REST and transport milestones require real behavior.
