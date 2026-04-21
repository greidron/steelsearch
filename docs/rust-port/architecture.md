# Rust Port Architecture

## Goal

Build a Rust OpenSearch-compatible node with explicit compatibility boundaries:

- OpenSearch REST API compatibility where behavior is tested by REST specs.
- OpenSearch transport wire compatibility for Java cluster interop.
- OpenSearch cluster-state decode and, later, cluster membership compatibility.
- Rust-native search engine support through an engine abstraction.
- Lucene file-format compatibility as a long-term goal, not the first engine target.

This is not a mechanical Java-to-Rust translation. The implementation should
preserve externally observable behavior and wire contracts, while using Rust
native module boundaries and ownership models.

## Workspace Layout

```text
crates/
  os-core             shared version, settings, errors, common types
  os-wire             TCP framing and transport wire primitives
  os-stream           StreamInput/StreamOutput-compatible codec
  os-transport        transport connection, handshake, request dispatch
  os-cluster-state    cluster-state models, diffs, named writeables
  os-rest             REST route and response compatibility shell
  os-query-dsl        OpenSearch query DSL parser and normalized plans
  os-engine           engine traits and shard engine contracts
  os-engine-tantivy   first Rust-native engine implementation
  os-node             node lifecycle and service wiring
```

## Compatibility Layers

### Wire Layer

`os-wire` mirrors the OpenSearch TCP transport frame:

- `ES` marker bytes
- message length
- request id
- status byte
- version id
- variable-header size
- variable header and body

The reference Java classes are:

- `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TcpHeader.java`
- `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/InboundDecoder.java`

### Stream Codec

`os-stream` implements the primitive serialization used by OpenSearch
`StreamInput` and `StreamOutput`. This layer must eventually support:

- primitive integers and variable-length integers
- strings and byte arrays
- optional values
- arrays, lists, maps
- exceptions
- version-gated serialization
- named writeables

The reference Java classes are:

- `/home/ubuntu/OpenSearch/libs/core/src/main/java/org/opensearch/core/common/io/stream/StreamInput.java`
- `/home/ubuntu/OpenSearch/libs/core/src/main/java/org/opensearch/core/common/io/stream/StreamOutput.java`

### Cluster State

`os-cluster-state` should begin as decode-only. The first target is reading
cluster state from a Java OpenSearch node. Full participation comes later.

Initial models:

- `ClusterState`
- `Metadata`
- `IndexMetadata`
- `DiscoveryNodes`
- `RoutingTable`
- `ClusterBlocks`
- `CoordinationMetadata`

The reference Java class is:

- `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/ClusterState.java`

### Engine

`os-engine` defines contracts for indexing, get, refresh, flush, search,
replication, recovery, and snapshot metadata.

The first real implementation should be Rust-native and separate from Lucene
file-format compatibility. Tantivy is the fastest path to a working MVP. A
Lucene-compatible reader/writer can be explored later behind the same trait.

## Node Modes

The project should evolve through these modes:

1. Transport probe: connects to Java OpenSearch and completes handshake.
2. Read-only transport client: reads node and cluster state information.
3. Coordinating-only node: receives REST requests and forwards transport actions.
4. Rust-native standalone data node: owns shards with a Rust index format.
5. Mixed-cluster data node: participates in Java OpenSearch allocation and recovery.

Only the first three modes should be treated as near-term compatibility goals.
