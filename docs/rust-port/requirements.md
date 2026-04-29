# SteelSearch Requirements

## Mission

SteelSearch is a Rust implementation of an OpenSearch-compatible node. The
project prioritizes externally observable compatibility over a mechanical Java
port. Compatibility must be proven at protocol, API, and behavior boundaries
with fixtures or live Java OpenSearch interop tests.

## Compatibility Requirements

- REST responses should match OpenSearch route shape, status codes, and JSON
  fields for the MVP API set.
- Transport frames must remain byte-compatible with Java OpenSearch for header,
  status bits, variable headers, stream primitives, ping frames, and handshake
  actions.
- Stream codecs must follow OpenSearch `StreamInput` and `StreamOutput`,
  including Java-style string encoding and version-gated serialization.
- Cluster-state support starts as decode-only against Java OpenSearch. Unknown
  custom metadata must fail closed until explicit support is added.
- Cluster membership and coordinating-node behavior are later milestones and
  require stronger safety checks than passive transport probing.
- Java plugin ABI compatibility is out of scope.

## Engine Requirements

- The storage/search engine must sit behind `os-engine` traits so the node can
  support multiple backends.
- Tantivy is the first Rust-native engine target for a working standalone MVP.
- Lucene file-format read/write compatibility is a long-term backend goal, not a
  prerequisite for the first functional node.
- API-visible document metadata must preserve OpenSearch semantics for `_id`,
  `_source`, `_version`, `_seq_no`, and `_primary_term`.

## Near-Term Scope

- Keep the Rust workspace rooted at `/home/ubuntu/steelsearch`.
- Maintain Java fixture tests for wire compatibility.
- Verify transport behavior against a live Java OpenSearch node when changing
  handshake, frame, stream, or action dispatch code.
- Implement node modes in this order:
  1. Transport probe.
  2. Read-only transport client.
  3. Coordinating-only node.
  4. Rust-native standalone data node.
  5. Mixed-cluster data node.

## Current Verified State

- Rust encodes and decodes OpenSearch TCP headers, status bits, ping frames,
  request/response variable headers, Java-style strings, and handshake frames.
- Java fixture bytes are checked into `fixtures/java/opensearch-wire-fixtures.txt`
  and covered by Rust tests.
- A live Java OpenSearch `3.7.0-SNAPSHOT` node accepted Rust
  `internal:tcp/handshake` and `internal:transport/handshake` requests.
- The Rust probe decoded remote version, cluster name, discovery node id,
  transport address, attributes, and node roles.
- Transport error bodies are minimally decoded, including common JVM exception
  wrappers and selected OpenSearch transport exceptions, with unknown exception
  keys surfaced as fail-closed compatibility errors.
- Compressed transport message bodies are detected and deflate-compressed
  payloads are decompressed by the frame decoder.
- Cluster-state transport requests can be built from Rust and checked against
  Java fixtures.
- Cluster-state responses are decoded as Java-compatible prefix/skeleton models,
  covering metadata, routing, discovery nodes, cluster blocks, selected
  metadata customs, and publication diff envelopes.
- Unknown cluster-state named writeables and unsupported custom metadata fail
  closed instead of being silently skipped.
- `os-tcp-probe` can issue cluster-state requests and print decoded summaries
  for handshake, metadata, routing, node, block, and selected custom sections.
- The development Steelsearch daemon exposes a partial OpenSearch-shaped REST
  surface covering root, cluster health/state, index create/read/delete,
  document index/get, refresh, search, aliases/templates, and selected
  snapshot and operational development flows.

## Immediate Implementation Risks

- `requirements.md` can drift behind the more detailed compatibility ledger in
  `docs/api-spec/`; this document must be kept in sync when transport or REST
  compatibility expands.
- Transport compatibility work is still concentrated on handshake,
  cluster-state probing, and decode-oriented interop. Most OpenSearch transport
  actions remain explicitly unimplemented.
- Cluster-state support is intentionally decode-first and fail-closed. It is not
  yet a claim of mixed-cluster membership, cluster-manager participation, or
  production-grade coordination safety.
- Many REST surfaces are only partial development replacements. They preserve
  useful route and response shape compatibility, but not full OpenSearch
  semantics for routing, versioning, allocation, task management, and admin
  controls.
- Version-gated serialization coverage still depends on a curated set of named
  constants and fixtures; broader action parity will require more exhaustive
  version compatibility review.
