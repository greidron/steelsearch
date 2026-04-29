# OpenSearch Version Gates

This audit records the current version-gated serialization and decoding paths in
Steelsearch. Version constants live in `crates/os-core/src/version.rs`; new gates
should use those named constants instead of raw integer ids.

## Transport Gates

- `crates/os-wire/src/tcp_header.rs`
  - Reads the transport header version id from the frame. This is dynamic peer
    input, so `Version::from_id(buf.get_i32())` is expected.
- `crates/os-transport/src/handshake.rs`
  - Reads the peer-reported node version from handshake response payloads. This
    is dynamic peer input.
  - `DiscoveryNode::read` gates the optional stream address on
    `OPENSEARCH_DISCOVERY_NODE_STREAM_ADDRESS`.
- `crates/os-tcp-probe/src/main.rs`
  - CLI overrides can still create `Version` from user-provided ids.
  - Defaults use the named OpenSearch 3.7.0 fixture transport constants.

## Cluster-State Gates

All current cluster-state gates are in `crates/os-cluster-state/src/lib.rs`.

- Default cluster-state stream version:
  - `DEFAULT_CLUSTER_STATE_STREAM_VERSION = OPENSEARCH_3_7_0_TRANSPORT`.
- Workload group metadata:
  - `OPENSEARCH_3_6_0`: search settings are present only on or after this
    version.
- Repository metadata:
  - `OPENSEARCH_2_10_0`: crypto metadata is present only on or after this
    version.
- Index metadata and index metadata diffs:
  - Before `OPENSEARCH_3_6_0`, primary terms are encoded as a vlong array.
  - On or after `OPENSEARCH_3_6_0`, split-shards metadata appears and primary
    terms move to the newer map encoding.
  - `OPENSEARCH_2_17_0`: index context optional writeable marker appears.
  - `OPENSEARCH_3_0_0`: ingestion status appears.
- Shard routing:
  - `OPENSEARCH_2_17_0`: `search_only` appears.
- Allocation id:
  - `OPENSEARCH_3_7_0`: split-child allocation ids and parent allocation id
    appear.
- Snapshot recovery source:
  - `OPENSEARCH_2_7_0`: searchable snapshot boolean appears.
  - `OPENSEARCH_2_9_0`: remote-store shallow-copy flag and remote segment
    repository appear.
  - `OPENSEARCH_2_17_0`: index shard path type, remote translog repository, and
    pinned timestamp appear.
- Remote-store recovery source:
  - `OPENSEARCH_2_17_0`: index shard path type appears.
- Discovery node prefix:
  - `OPENSEARCH_DISCOVERY_NODE_STREAM_ADDRESS`: optional stream address appears.
- Snapshots in progress:
  - `OPENSEARCH_2_9_0`: remote-store shallow-copy flag appears.
  - `OPENSEARCH_2_18_0`: shallow-copy v2 flag appears.

## Audit Finding

The `snapshots_in_progress` decoder is parameterized by the caller's
`stream_version` in both full cluster-state custom payloads and publication diff
custom payloads. This keeps the 2.9 and 2.18 remote-store snapshot flags aligned
with the stream being decoded instead of always assuming the current Java 3.7
fixture version.

## Regression Coverage To Add

The next test task should cover the gates that change field alignment:

- Snapshot recovery source around 2.7, 2.9, and 2.17.
- Shard routing and remote-store recovery source around 2.17.
- Index metadata around 3.0 and 3.6.
- Allocation id around 3.7.
- Discovery node stream address around
  `OPENSEARCH_DISCOVERY_NODE_STREAM_ADDRESS`.
- Snapshots-in-progress remote-store flags around 2.9 and 2.18.
