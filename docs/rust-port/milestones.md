# Milestones

## M0: Project Skeleton

- Rust workspace rooted at `/home/ubuntu/steelsearch`.
- Initial architecture docs.
- `os-wire`, `os-stream`, and `os-transport` scaffolding.
- TCP header encode/decode unit test.
- Transport status bit helpers.
- Java-style stream string encoding.
- Ping frame, transport frame encode/decode, and handshake request builders.

## M1: Java Wire Fixture

- Build a small Java fixture that writes OpenSearch `TcpHeader` and stream bytes.
- Assert Rust can decode Java-produced bytes.
- Assert Java can decode Rust-produced bytes.
- Add fixture cases for variable-length integers, strings, and optional values.

## M2: Transport Handshake

- Start a local Java OpenSearch node.
- Connect from Rust to the transport port.
- Send low-level `internal:tcp/handshake`.
- Decode the low-level handshake response version.
- Implement enough stream codec to send high-level `internal:transport/handshake`.
- Decode the high-level handshake response.
- Decode `DiscoveryNode`, cluster name, remote version, node roles, and transport
  address from a Java node.
- Exchange ping.

## M3: Cluster-State Decode

- Decode a full single-node cluster state.
- Add typed models for metadata, nodes, routing table, blocks, and coordination metadata.
- Add named writeable registry coverage for built-in state.
- Reject unsupported custom metadata explicitly.

## M4: REST Shell

- Add `os-rest` router.
- Implement info, ping, cluster health, create index, get index, delete index.
- Return OpenSearch-shaped JSON.

## M5: Rust-Native Engine MVP

- Add a Tantivy-backed engine.
- Support create index, index document, get document, refresh, and basic search.
- Preserve `_source`, `_id`, `_version`, `_seq_no`, and `_primary_term` fields at the API boundary.

## M6: Query DSL MVP

- Parse and execute `match_all`, `term`, `match`, `range`, and `bool`.
- Add basic sort and pagination.
- Add simple aggregations after query behavior stabilizes.

## M7: Coordinating-Only Node

- Join or attach to Java OpenSearch as a non-data participant, depending on what the transport and discovery protocol supports safely.
- Receive cluster state.
- Forward REST search/index requests to Java nodes over transport.

## M8: Data Node Research

- Model shard allocation and lifecycle.
- Implement primary write path.
- Implement replica apply path.
- Implement local recovery.
- Decide whether JVM Lucene bridge is required for mixed-cluster compatibility.
