# Full OpenSearch Replacement Plan

This plan was derived from the local OpenSearch source tree at
`/home/ubuntu/OpenSearch` on branch `main`, commit `f991609d190`, the local
k-NN plugin source tree at `/home/ubuntu/k-NN` on branch `main`, commit
`86ad5668acddbcf57d62ee0a3db17385aa93fde0`, and the current Steelsearch Rust
port state.

## Current Position

Steelsearch currently covers an OpenSearch-shaped MVP, not a full replacement.
The implemented surface includes basic REST routing, a small index/document API,
Tantivy-backed local indexing/search, a small Query DSL subset, terms
aggregation, transport handshake, cluster-state decoding, diff application, and
coordinating-only Java interop.

The supported development replacement profile is documented separately in
`docs/rust-port/development-replacement-profile.md`. That profile is limited to
development daemon use with Steelsearch-owned data and explicitly does not make
production replacement claims.

The local OpenSearch source shows the replacement gap is much larger:

- `ActionModule` registers 148 transport actions and 167 REST handlers.
- `SearchModule` registers roughly 49 query registrations and 40 aggregation
  registrations before plugin extension points.
- `Node` wires discovery, cluster coordination, gateway persistence, index
  services, recovery, segment replication, repositories, ingest, scripts,
  plugins, telemetry, workload management, and HTTP/transport lifecycles.
- `IndexShard` is built around Lucene, translog, sequence numbers, retention
  leases, recovery, refresh, flush, merge, store, and shard state transitions.

## Replacement Strategy

The primary replacement target is a standalone OpenSearch-compatible
Steelsearch cluster:

- Steelsearch owns its shards, persists data in a Rust-native store, recovers
  after restart, replicates with a Steelsearch-native protocol, and exposes
  OpenSearch-compatible REST APIs for supported features.
- Existing OpenSearch users migrate data into Steelsearch through reindex,
  scroll/PIT export, bulk import, and optional snapshot/import tooling.
- Java OpenSearch mixed data-node compatibility is explicitly deferred. It is
  useful later, but it should not drive the first architecture because Lucene
  store compatibility, JVM bridges, and dual-write paths would weaken the
  performance goal of the Rust replacement.

The first compatibility boundary is therefore API and migration compatibility,
not hot-path mixed-cluster shard compatibility. A future optional data-node
compatibility track can be revisited after the standalone engine is stable.

## Required Milestones

### R1: Source Inventory And Compatibility Matrix

- Generate a machine-readable inventory from Java `ActionModule`,
  `SearchModule`, `ClusterModule`, mapper registrations, ingest processors,
  script contexts, repositories, and plugin extension points.
- Map every Java REST route and transport action to one of:
  `implemented`, `forwarded`, `stubbed`, `planned`, or `out-of-scope`.
- Keep the matrix versioned by OpenSearch wire version and source commit.
- Add compatibility fixtures that compare route registration, error shape,
  request parsing, and response shape against Java OpenSearch.

### R2: Node Runtime And Configuration

- Implement OpenSearch-compatible node settings, environment paths, node
  metadata, cluster UUID persistence, bootstrap checks, and lifecycle ordering.
- Add thread-pool equivalents, task tracking, cancellable tasks, request
  headers, circuit breakers, resource accounting, and structured deprecation
  warnings.
- Add plugin/module loading boundaries for action, search, mapper, ingest,
  repository, script, and vector/model extensions.

### R3: Cluster Membership And Coordination

- Implement discovery, peer finding, handshakes, join validation, pre-vote,
  election, voting configuration, publication, commit, and apply semantics
  compatible with OpenSearch `Coordinator`.
- Persist coordination state and cluster metadata in a gateway layer.
- Implement cluster-manager task queues, acknowledgments, reroute triggering,
  node-left handling, cluster blocks, and feature/version gates.
- Add multi-node crash/restart and partition tests against Java behavior.

### R4: Metadata, Routing, And Allocation

- Move beyond decode-only cluster state into authoritative cluster-state
  mutation.
- Implement index creation/deletion/open/close, templates, component templates,
  mappings, aliases, data streams, views, settings updates, weighted routing,
  cluster blocks, and custom metadata mutation.
- Implement shard allocation deciders, disk watermarks, awareness, delayed
  allocation, reroute, primary election, stale primary handling, and allocation
  explain.

### R5: Durable Shard Store And Engine

- Replace the in-memory Tantivy MVP with durable shard directories, manifest
  files, commit metadata, checksum validation, local checkpoint, global
  checkpoint, max sequence number, primary term, and operation history.
- Implement refresh, flush, force merge, merge policy, segment metadata,
  request cache, query cache, fielddata/doc-values cache, and stats.
- Keep the shard store Rust-native for the standalone cluster. Do not add a
  Lucene/JVM bridge or dual-write path on the hot write path unless the optional
  data-node compatibility track is reopened.

### R6: Java-Compatible Write Path

- Implement primary write operations with OpenSearch sequence-number assignment,
  primary term validation, version conflict behavior, dynamic mapping update
  retry, translog location tracking, and response metadata.
- Implement replica replay using primary-assigned sequence number, primary term,
  version, and noop/failure semantics.
- Implement bulk, index, create, delete, update, mget, refresh policies,
  optimistic concurrency, external versioning, routing, and auto-create index.
- Implement retention leases, global checkpoint sync, resync, stale operation
  handling, and post-replication fsync/refresh.

### R7: Recovery, Replication, And Restart Safety

- Implement local recovery for Steelsearch-owned shards.
- Implement peer recovery transport actions:
  `start_recovery`, file info, file chunk, clean files, prepare translog,
  translog operations, finalize recovery, and cancellation/retry behavior.
- Implement segment replication and remote-store paths only after the store
  format is compatible.
- Add rolling restart, node loss, shard relocation, replica promotion, snapshot
  restore, and corruption tests.

### R8: Search Parity

- Expand Query DSL beyond the current MVP to the built-in Java query set:
  phrase, multi-match, nested, dis-max, ids, query-string, boosting, terms,
  fuzzy, regexp, prefix, wildcard, spans, wrapper, function score, script,
  script score, geo, exists, match-none, terms-set, intervals, templates, and
  plugin queries.
- Implement search phases: can-match, DFS/query-then-fetch, fetch subphases,
  highlighting, explain, profiling, collapse, rescore, search-after, scroll,
  PIT, slicing, timeout, terminate-after, track-total-hits, source filtering,
  stored fields, docvalue fields, runtime fields, and shard failure reporting.
- Expand aggregations to metrics, bucket, pipeline, geo, significant terms,
  composite, top hits, scripted aggregations, and plugin aggregations.
- Add analyzer parity, similarity settings, script support, and named writeable
  serialization for search request/response transport.

### R9: REST And Transport API Coverage

- Implement the 167 core REST handlers visible in the local `ActionModule`,
  grouped by cluster, indices, document, search, ingest, tasks, scripts,
  repositories, snapshots, cat, PIT, data streams, views, remote store,
  decommission, and tiering.
- Implement the 148 core transport actions and support transport actions with
  Java-compatible request/response wire forms.
- Preserve OpenSearch error types, status codes, headers, deprecation warnings,
  content negotiation, chunked responses, and task cancellation behavior.

### R10: Ingest, Scripts, Pipelines, And Extensibility

- Implement ingest pipeline metadata, pipeline execution, processors, simulate,
  failure handlers, and system ingest pipelines.
- Implement search pipelines and request/response processors.
- Implement stored scripts, script contexts, deterministic sandboxing, painless
  compatibility strategy, and script score/query/aggregation hooks.
- Define plugin APIs for Rust-native plugins and Java-compatible plugin
  substitutes.

### R11: Snapshots, Repositories, And Remote Store

- Implement repository metadata, repository verification, snapshot create,
  delete, clone, restore, status, and cleanup.
- Implement blob-store repository abstractions for filesystem first, then S3,
  GCS, Azure, and HDFS equivalents.
- Implement Steelsearch-native snapshot shard metadata, segment file copy,
  translog/commit safety, and restore allocation behavior.
- Add OpenSearch migration tooling separately from native snapshots: scroll/PIT
  export, `_bulk` import, mappings/settings/template translation, alias/data
  stream migration, vector field migration, and resume/checkpoint support.
- Treat direct OpenSearch snapshot import as optional. It may require a Lucene
  reader or offline conversion path, so it should not block the native snapshot
  implementation.

### R12: Security And Multi-Tenancy Boundary

- OpenSearch security is usually plugin-provided, not core server code. A full
  replacement still needs TLS, authn/authz, index permissions, field/document
  security, audit logs, tenant isolation, and secure settings.
- Decide whether to implement an OpenSearch Security-compatible plugin surface
  or a Steelsearch-native security layer with OpenSearch-shaped APIs.

### R13: Vector Search And k-NN

The local OpenSearch source tree does not include the k-NN plugin. OpenSearch
k-NN is a separate plugin that adds `knn_vector`, k-NN query support, native
library indexes, and engine choices such as Lucene, Faiss, and historically
NMSLIB.

Steelsearch can support k-NN, but it should be planned as a first-class engine
extension, not as a minor Query DSL addition.

For Steelsearch, k-NN should be implemented as a plugin-shaped module. The
first implementation does not need dynamic plugin loading; it can be a
statically linked Rust workspace crate, such as `os-plugin-knn`, registered by
the `steelsearch` daemon (implemented in the `os-node` crate) through mapper,
query, REST, transport/action, codec/vector-format, script, search-pipeline,
stats, and circuit-breaker extension points. This keeps the
OpenSearch-compatible `_plugins/_knn/*` surface isolated from core search while
avoiding a premature stable plugin ABI.

The local k-NN plugin source confirms the compatibility surface:

- `KNNPlugin` registers `knn_vector` as a mapper, `knn` as a query, a custom
  codec service for k-NN indices, a k-NN painless script engine, search pipeline
  hooks, 12 transport actions, and 7 REST handler classes covering 12 routes.
- k-NN REST compatibility includes `_plugins/_knn/stats`, warmup, clear cache,
  model get/delete/search, and model training APIs.
- The field mapper accepts `dimension`, `data_type`, `model_id`, `method`,
  `mode`, `compression_level`, top-level `space_type`, top-level `engine`,
  `doc_values`, `store`, and `_meta`.
- The query builder accepts `vector`, `k`, `filter`, `ignore_unmapped`,
  `expand_nested`, radial search through `max_distance` or `min_score`,
  per-query `method_parameters` such as `ef_search` and `nprobes`, and
  `rescore`.
- Engines are `faiss`, `lucene`, deprecated `nmslib`, and `undefined`; the
  default engine in the current plugin source is `faiss`. Engine limits and
  behavior differ, including filter support, radial search support, nested-field
  support, custom segment files, score transforms, and max dimensions.
- Native-engine support is not just indexing: it includes JNI libraries, native
  memory cache management, circuit breakers, SIMD feature detection,
  quantization state cache, warmup, cache eviction, custom segment files, remote
  index build, and restart/rolling-upgrade compatibility tests.

Required work:

- Add `knn_vector` mapping support with dimension, data type, `model_id`,
  method context, mode, compression level, top-level space type, top-level
  engine, `m`, `ef_construction`, `ef_search`, `doc_values`, stored fields,
  `_meta`, and binary vector options where supported.
- Add vector storage in the shard engine and persist vector segment metadata.
- Implement exact vector search for small corpora and test determinism first.
- Implement ANN indexes using a Rust vector library or FFI backend:
  - Rust-native mode through HNSW/Faiss-compatible bindings for standalone
    Steelsearch.
  - Optional Lucene-compatible import/export mode only for future migration or
    data-node compatibility work, not for the first hot path.
  - Enforce this boundary in the k-NN plugin state: Lucene/JVM bridge,
    hot-path dual write, recovery-time conversion, and Java data-node store
    compatibility must fail closed unless the later optional data-node
    compatibility track is explicitly reopened.
- Add k-NN query parsing, score normalization, filters, `ignore_unmapped`,
  nested expansion, radial search, per-query method parameters, hybrid
  lexical/vector search, rescoring, pagination constraints, and shard-level
  top-k merge.
- Add `_plugins/_knn/*` APIs for stats, warmup, clear cache, model get/delete,
  model search, and model training if compatibility with the k-NN plugin API is
  required.
- Add memory circuit breakers, warmup, cache eviction, native index lifecycle,
  model cache, quantization cache, SIMD/native-library feature gates, remote
  index build, merge behavior, and recovery behavior for vector indexes.

### R14: ML Commons, Neural Search, And Model Serving

OpenSearch can generate embeddings through ML Commons and neural-search plugin
flows. Supporting MiniLM or similar embedding models requires model serving and
pipeline integration in addition to vector indexing.

Required work:

- Add ML model registry APIs compatible with ML Commons concepts:
  model groups, model metadata, model chunks, model versions, deploy/undeploy,
  tasks, model states, and access control hooks.
- Support local model formats for text embedding and sparse encoding. ONNX is
  the most practical Rust-native first target; TorchScript likely needs a
  libtorch/JVM/Python bridge.
- Add remote model connectors for externally hosted embedding models, including
  request signing, credential storage, pre/post processors, retries, rate
  limits, and timeouts.
- Implement inference APIs for dense embeddings, sparse embeddings,
  cross-encoder rerankers, and generic prediction.
- Add ingest processors that call models and write vectors/sparse features into
  documents.
- Add search request processors or neural query handling that embeds query text
  at search time and then executes k-NN, sparse, or hybrid search.
- Add model placement and serving runtime:
  dedicated ML nodes or worker pools, memory accounting, batching, warmup,
  unload policies, health checks, and model-task cancellation.
- Add compatibility tests for the common flow:
  register MiniLM-compatible model, deploy, create ingest pipeline, ingest text,
  create vector field, run neural/k-NN search, and run hybrid BM25 + vector
  search.

### R15: Observability, Administration, And Operations

- Implement node/cluster/index stats, cat APIs, hot threads, tasks, usage,
  plugins info, thread pool stats, health, allocation explain, and pending
  tasks.
- Add metrics/tracing/logging hooks and OpenSearch-shaped telemetry.
- Add backup/restore, rolling upgrade, Steelsearch mixed-version compatibility,
  benchmark, load test, chaos test, and production packaging.

### R16: OpenSearch Data Migration

Steelsearch should replace OpenSearch operationally by making data migration
explicit and reliable instead of joining an existing Java OpenSearch cluster as
a data node.

Required work:

- Implement an OpenSearch source connector that can read mappings, settings,
  aliases, templates, component templates, ingest pipelines, index metadata,
  data streams, and security-relevant metadata where accessible.
- Implement document export using scroll and PIT/search-after with slicing,
  routing preservation, source filtering, version/seq_no capture where useful,
  retry, backoff, throttling, and resumable checkpoints.
- Implement `_bulk` import into Steelsearch with configurable concurrency,
  refresh policy, backpressure, failure capture, dead-letter output, and
  idempotent resume.
- Translate OpenSearch mappings/settings into Steelsearch-supported mappings
  with an explicit unsupported-feature report.
- Migrate vector fields and k-NN mappings, including dimension, data type,
  engine/method compatibility notes, and optional vector reindexing.
- Add validation: document counts, checksums over `_id`/`_source`, sample query
  comparison, alias/data stream verification, and cutover readiness reports.
- Add a dry-run mode and a migration manifest that records source cluster
  version, index UUIDs, source checkpoints, target index names, unsupported
  features, and validation results.

### R17: Optional Java Data-Node Compatibility

This track is intentionally out of the first replacement scope. Revisit it only
after the standalone Steelsearch cluster, native recovery, snapshots, migration,
k-NN, and model serving are stable.

Potential approaches:

- Offline Lucene import/export converter for migration-only use.
- Boundary conversion during recovery/relocation, accepting high recovery-time
  CPU and IO cost.
- Dual-store only for explicitly configured compatibility indices.
- JVM/Lucene bridge for compatibility indices, not for the default hot path.

Success criteria must include recovery, relocation, replica promotion, snapshot,
rolling upgrade, and corruption tests against Java OpenSearch. Until those pass,
Steelsearch should not advertise Java OpenSearch data-node compatibility.

## Practical Priority Order

1. Build the compatibility matrix and make unsupported APIs explicit.
2. Make the standalone shard engine durable and restart-safe.
3. Implement Steelsearch-native write sequencing, replication, and local
   recovery.
4. Implement cluster membership only after data loss risks are controlled.
5. Expand REST/search API coverage from the matrix.
6. Add vector/k-NN for standalone Steelsearch.
7. Add ML model serving and neural-search pipelines.
8. Add OpenSearch-to-Steelsearch migration tooling and validation.
9. Revisit Java data-node compatibility only as an optional later track.

## k-NN And Model Serving Feasibility

k-NN support is feasible for standalone Steelsearch. The fastest practical path
is Rust-native vector storage plus HNSW/exact search and OpenSearch-compatible
request/response shapes. Full OpenSearch k-NN plugin compatibility is a larger
project because it includes plugin APIs, native vector index lifecycle, memory
circuit breakers, stats, warmup, recovery, and engine-specific parameters.

MiniLM-style model serving is also feasible, but it is not part of k-NN itself.
It belongs in an ML Commons/neural-search layer that can register, deploy, and
run embedding models, then feed generated vectors into k-NN or sparse search.
ONNX Runtime is the likely first Rust-native runtime. Remote connectors are a
separate path for calling external model servers.
