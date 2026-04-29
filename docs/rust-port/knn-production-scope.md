# k-NN Production Scope

This document fixes the production direction for Steelsearch-native k-NN and
vector search.

## Decision

Steelsearch's production k-NN path uses the Rust-native vector storage and
HNSW search implementation already owned by the Steelsearch engine. The
supported production target is:

- Steelsearch-owned `knn_vector` persistence in shard manifests and operation
  replay logs.
- Exact vector search as the correctness baseline and fallback path.
- Rust-native HNSW graph snapshots for approximate nearest-neighbor search.
- OpenSearch-shaped REST request and response compatibility for supported
  mappings, query forms, stats, warmup, cache, and model-serving integration.
- Fail-closed validation for unsupported vector data types, spaces, engines,
  method parameters, and plugin features.

## Non-Goals

FAISS and NMSLIB are not production hot-path dependencies for Steelsearch.
They remain out of scope for the first production replacement track because
they would add native runtime packaging, memory ownership, failure isolation,
and index-format compatibility surfaces that are not required for a
Steelsearch-owned shard engine.

The following are also non-goals for the first production track:

- Lucene/JVM vector index bridge in the serving path.
- OpenSearch Java data-node vector store compatibility.
- Dual-writing Steelsearch and OpenSearch vector segment formats.
- Recovery-time conversion from Java k-NN segment formats.
- Binary compatibility with FAISS/NMSLIB model or index files.

## Compatibility Boundary

Steelsearch should match OpenSearch at the API contract boundary where it
claims support: mappings, query validation, response shape, selected stats,
cache controls, warmup behavior, and error types. It should not claim
drop-in compatibility for OpenSearch plugin internals, native library loading,
or existing Java k-NN segment files.

Unsupported engines or methods must produce explicit OpenSearch-shaped errors
instead of silently falling back to a different scoring path.

## Intentional Compatibility Skips

The Docker OpenSearch replacement rehearsal keeps these k-NN differences as
explicit skips until they become production requirements:

| Skip scope | Current decision | Production trigger |
| --- | --- | --- |
| FAISS engine execution | Steelsearch preserves OpenSearch mapping metadata but rejects `engine: faiss` execution in the Rust-native hot path. | Reopen only if Steelsearch commits to packaging, memory isolation, failure handling, and index-format support for FAISS-backed serving. |
| `on_disk` mode | Steelsearch rejects `mode: on_disk` because compressed/on-disk vector search semantics are not implemented. | Reopen when native on-disk vector layout, cache behavior, scoring parity, and recovery tests are implemented. |
| k-NN method parameters | Steelsearch rejects method parameters before execution because current native scoring does not honor HNSW construction/search parameters field-for-field. | Reopen when supported HNSW parameters have documented semantics and OpenSearch comparison fixtures. |
| Warmup byte accounting | Steelsearch exposes Rust-native memory breaker accounting; OpenSearch reports JVM/native plugin internals that are not portable. | Reopen only for a field-level compatibility contract operators require for cutover. |
| Cache telemetry fields | Steelsearch reports native graph/model/quantization cache bytes and clear-cache release counts instead of matching every OpenSearch plugin field. | Reopen when production observability requires exact OpenSearch k-NN stats field parity. |

## Data Type And Score-Space Inventory

| Surface | Production decision | Current behavior | Required error decision |
| --- | --- | --- | --- |
| `data_type: float` | Supported | Parsed and executed through native vector values. | None. |
| `data_type: byte` | Planned supported mapping surface; execution must prove byte quantization semantics before production claim. | Parsed by `os-plugin-knn`; native execution currently stores values through the same vector value path. | Reject production mode if byte scoring is not explicitly enabled and tested. |
| `data_type: binary` | Deferred for production execution. | Parsed by `os-plugin-knn`; binary/Hamming semantics are not production-proven. | Fail closed for execution until binary vector distance and fixture parity exist. |
| Missing `data_type` | Supported as OpenSearch-compatible `float`. | Defaults to `float`. | None. |
| Unknown `data_type` | Unsupported. | Parser rejects unknown values. | Keep OpenSearch-shaped `illegal_argument_exception`. |
| `space_type: l2` | Supported. | Scores as negative squared L2 distance. | None. |
| `space_type: cosine` / `cosinesimil` | Supported. | Scores with cosine similarity aliases. | None. |
| `space_type: innerproduct` / `dot_product` | Supported. | Scores with dot product aliases. | None. |
| Unknown `space_type` | Unsupported for production. | Current execution falls back to L2 for unknown values. | Add fail-closed validation before query execution. |
| `method.name: hnsw` | Supported native ANN target. | Native HNSW snapshot/search path exists. | Validate supported parameters explicitly. |
| `engine: lucene` | Supported only as API-compatible native execution, not Lucene segment compatibility. | Mapping value is preserved; execution remains Steelsearch-native. | Document native translation in reports. |
| `engine: faiss` / `nmslib` | Migration metadata only in first production track. | Mapping value can be preserved. | Fail closed for production execution unless an explicit native translation is enabled. |
| Unknown `engine` | Unsupported. | Mapping value can be preserved. | Add fail-closed production validation. |
| `mode` / `compression_level` | Deferred for production execution. | Mapping values can be preserved. | Reject production execution until native semantics are implemented. |

## Production Readiness Criteria

Before k-NN is production-ready, the implementation needs:

- deterministic exact-vs-HNSW correctness tests across dimensions and score
  spaces;
- memory accounting and circuit breaker coverage for graph, vector, model, and
  quantization caches;
- restart tests proving vector metadata, HNSW snapshots, and cache accounting
  recover consistently;
- OpenSearch comparison fixtures for supported request shapes and error cases;
- explicit documentation for every unsupported OpenSearch k-NN engine, space,
  and method parameter.
