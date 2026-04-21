# Compatibility Targets

## Definitions

Compatibility is split into independent levels. Each level must be tested
separately.

| Level | Meaning | Initial Target |
| --- | --- | --- |
| REST shape | Routes, status codes, JSON fields | Yes |
| REST behavior | OpenSearch REST YAML tests pass | Partial |
| Transport frame | TCP frame can be exchanged with Java nodes | Yes |
| Stream codec | Java and Rust payloads roundtrip byte-for-byte | Yes |
| Cluster-state decode | Rust reads Java cluster state | Yes |
| Cluster membership | Rust joins Java cluster | Later |
| Coordinating node | Rust forwards actions to Java data nodes | Later |
| Data node | Rust owns shards | Later |
| Lucene file read | Rust reads Lucene segments | Long term |
| Lucene file write | Rust writes Lucene-compatible segments | Long term |
| Java plugin ABI | Java plugins load into Rust node | Out of scope |

## Initial API Scope

The REST MVP should cover:

- `GET /`
- `HEAD /`
- `GET /_cluster/health`
- `PUT /{index}`
- `DELETE /{index}`
- `POST /{index}/_doc`
- `PUT /{index}/_doc/{id}`
- `GET /{index}/_doc/{id}`
- `DELETE /{index}/_doc/{id}`
- `POST /_bulk`
- `GET|POST /{index}/_search`
- `POST /{index}/_refresh`

## Transport Scope

The transport MVP should cover:

- TCP header encode/decode
- ping frame handling
- `internal:transport/handshake`
- node liveness
- minimal action request/response dispatch

## Cluster-State Scope

Cluster-state work starts decode-only:

- full state decode
- state UUID and version tracking
- named writeable registry for built-in metadata
- publication diff decode/apply after full decode works; current Rust scaffold
  prefix-decodes the `ClusterStateDiff` header, empty/prefix-only section count
  summaries, and delete-only string map diff envelopes, and fails closed before
  named diff/upsert payloads or apply semantics
- unknown custom metadata policy

Unknown custom metadata should initially fail closed. Lossy decode is dangerous
for mixed-cluster behavior.
