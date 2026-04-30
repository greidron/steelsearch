# Source Compatibility Matrix

This matrix classifies the OpenSearch source inventory in
`docs/rust-port/source-compatibility-inventory.md` against the current
Steelsearch implementation. It uses the same source baseline:

- OpenSearch commit: `f991609d190dfd91c8a09902053a7bbfe0c27b3e`
- k-NN commit: `86ad5668acddbcf57d62ee0a3db17385aa93fde0`

## Version Baseline

| Field | Value | Rust constant / source |
| --- | --- | --- |
| OpenSearch source commit | `f991609d190dfd91c8a09902053a7bbfe0c27b3e` | `/home/ubuntu/OpenSearch` |
| k-NN source commit | `86ad5668acddbcf57d62ee0a3db17385aa93fde0` | `/home/ubuntu/k-NN` |
| OpenSearch product version id | `3_070_099` | `OPENSEARCH_3_7_0` |
| Current fixture transport version id | `137_287_827` | `OPENSEARCH_3_7_0_TRANSPORT` |
| Minimum compatible transport version id | `136_407_827` | `OPENSEARCH_3_7_0_MIN_COMPAT_TRANSPORT` |
| Discovery node stream-address gate | `137_237_827` | `OPENSEARCH_DISCOVERY_NODE_STREAM_ADDRESS` |

Versioning rules for this matrix:

- REST rows are pinned to the OpenSearch source commit because REST route
  registration is source-level API shape.
- Native transport codec rows are pinned to the fixture transport version id
  because frame and stream compatibility are gated by transport ids, not only by
  product version ids.
- Cluster-state and recovery rows must carry their own per-field gates from
  `docs/rust-port/version-gates.md`.
- k-NN rows are pinned to the k-NN source commit until Steelsearch has a native
  plugin API version for Rust plugins.
- Rows whose behavior requires Java data-node binary compatibility remain out
  of scope for the standalone Steelsearch milestone unless a later compatibility
  track explicitly opens them.

## Status Values

| Status | Meaning |
| --- | --- |
| Implemented | The current repository has a native Rust implementation for this layer. |
| Partial | The current repository exposes a real standalone or compatibility surface, but broader OpenSearch semantics remain incomplete. |
| Stubbed | Steelsearch exposes an OpenSearch-shaped shell with limited behavior. |
| Planned | Required for replacement work, but not implemented yet. |
| Out of scope | Excluded from the current standalone Steelsearch milestone. |
| N/A | The layer does not apply to that source area. |

## Current Compatibility By Area

| Source area | Internal library support | Daemon HTTP support | OpenSearch API compatibility | Production readiness | Remaining gaps |
| --- | --- | --- | --- | --- | --- |
| Root and basic node identity | Implemented | Implemented | Partial | No | `GET /` and `HEAD /` return OpenSearch-shaped identity, but build metadata and node feature detail are development-level. |
| Cluster health, state, allocation, and node stats | Implemented | Partial | Partial | No | Health/state/stats/allocation endpoints exist for the daemon and development cluster, but wait parameters, index-scoped health, cat APIs, full routing metadata, and production allocation decisions are incomplete. |
| Index create/get/delete and mappings/settings | Implemented | Partial | Partial | No | Tantivy-backed index creation and mapping persistence exist, including `knn_vector` mapping parsing. Full OpenSearch templates, aliases, analyzers, dynamic mappings, index settings, wildcard safety, and data streams are not complete. |
| Document write/read and refresh | Implemented | Partial | Partial | No | Internal index/get/delete/update and refresh visibility paths exist. Daemon exposes single-document index/get plus bulk delete/update; single-document HTTP delete/update routes, OpenSearch routing, realtime flags, source filtering, ingest pipelines, and complete conflict behavior remain incomplete. |
| REST `_bulk` | Implemented | Implemented | Partial | No | Global and index-scoped NDJSON `_bulk` execute index/create/update/delete and refresh policies. Full OpenSearch bulk metadata, pipeline, routing, retry, shard failure, external versioning, and security behavior remain incomplete. |
| REST `_search` | Implemented | Implemented | Partial | No | Query execution, OpenSearch-shaped hits, sorting, pagination, selected aggregations, shard merge, error shape, and real daemon tests exist. Full Query DSL, highlighting, rescore, collapse, search-after, PIT/scroll, suggesters, profiles parity, and all aggregation families are incomplete. |
| k-NN vector indexing and query search | Implemented | Implemented | Partial | No | `knn_vector` mapping, vector persistence, `knn` query execution, filters, selected method parameters, hybrid BM25/vector search, and daemon fixtures exist. Native HNSW/FAISS/NMSLIB parity, byte/binary vectors, all score spaces, nested semantics, painless scripts, cache memory enforcement, and exact OpenSearch k-NN ranking parity remain incomplete. |
| k-NN plugin REST and model APIs | Implemented | Partial | Partial | No | `_plugins/_knn/stats`, warmup, clear cache, train/get/delete/search model routes are represented. OpenSearch k-NN transport actions, training internals, remote index build, circuit breaker enforcement, and full plugin setting semantics are incomplete. |
| ML Commons, neural search, and model serving | Implemented | Partial | Partial | No | Model groups, model registration, deploy/undeploy, predict, model search, rerank, and embedding-to-k-NN development flow exist. OpenSearch ML Commons task lifecycle, connectors, authz, persistent deployment, neural query processors, sparse encoders, and production model runtime isolation are incomplete. |
| Snapshot and restore | Implemented | Partial | Partial | No | Repository registration/verify plus snapshot create/status/restore/delete/cleanup strict compare now exist on the standalone profile. Incremental segment snapshots, remote store, searchable snapshots, and direct OpenSearch snapshot import are incomplete. |
| Migration and replacement tooling | Implemented | N/A | Partial | No | Migration crates and local rehearsal scripts cover export/import style replacement workflows using supported REST surfaces. Full OpenSearch mapping/template/alias translation, scroll/PIT export coverage, vector migration validation, resumability, and production runbooks remain incomplete. |
| Steelsearch multi-node runtime | Implemented | Implemented | Partial | No | Development daemons support node names, seed hosts, isolated data paths, primary/replica assignment, remote shard routing, replication, peer recovery, relocation, restart, and fault-injection tests. Discovery, membership, quorum, split-brain protection, rolling upgrades, production durability, and Java data-node mixed membership are not production-ready. |
| Native transport frame and OpenSearch probe compatibility | Partial | N/A | Partial | No | Frame encode/decode, ping, handshake, transport error decoding, and cluster-state decode scaffolding exist. Full transport action execution, named writeable registry coverage, cluster-state diffs, search/write transport parity, and Java data-node binary compatibility are incomplete. |
| Security and access control | Stubbed | Stubbed | Planned | No | Some fail-closed development gates and model registry access metadata exist. TLS, authn/authz, tenants, roles, index permissions, audit logs, secret handling, OpenSearch Security plugin API parity, and secure multi-node operation are missing. |
| OpenSearch comparison harness | Implemented | N/A | Partial | No | Common-baseline plus feature-specific profile runners now clean-pass for search-execution, snapshot-migration, vector-ml, and transport-admin. Coverage is still not exhaustive enough for production or mixed-cluster replacement claims. |
| Java OpenSearch data-node compatibility | Out of scope | N/A | Out of scope | No | Mixed Java data-node membership, Lucene segment binary sharing, Java plugin ABI, Java transport hot paths, and JVM recovery participation remain disabled unless a separate compatibility track is opened. |
| Java plugin ABI compatibility | Out of scope | N/A | Out of scope | No | Steelsearch has Rust-native k-NN and ML-shaped modules, not Java plugin loading or Java plugin extension points. |

## REST Route Summary

| REST route family | Daemon status | OpenSearch compatibility status | Notes |
| --- | --- | --- | --- |
| `GET /`, `HEAD /` | Implemented | Partial | OpenSearch-shaped node identity only. |
| `GET /_cluster/health`, `GET/PUT /_cluster/settings`, `GET /_cluster/state`, `GET /_cluster/pending_tasks` | Partial | Partial | Development cluster control surface, not full OpenSearch cluster API parity. |
| `GET /_nodes/stats`, `GET /_cluster/stats`, `GET /_stats`, `GET /_cat/indices`, `GET /_cat/plugins`, `GET /_tasks`, `GET /_nodes/hot_threads`, `GET /_nodes/usage`, `GET /_cluster/allocation/explain` | Partial | Partial | Operational and cat responses are local/dev summaries, not full OpenSearch telemetry parity. |
| `PUT /{index}`, `GET /{index}`, `DELETE /{index}` | Partial | Partial | Index shell, mapping/settings persistence, and daemon tests exist. |
| `PUT /{index}/_doc/{id}`, `GET /{index}/_doc/{id}` | Partial | Partial | Single-document index/get routes exist; single-document HTTP delete/update and full OpenSearch write semantics do not. |
| `POST /_bulk`, `POST /{index}/_bulk` | Implemented | Partial | Standalone write-path contract is live and strict-compared; broader production semantics remain. |
| `GET /_search`, `POST /_search`, `GET /{index}/_search`, `POST /{index}/_search` | Implemented | Partial | Standalone lexical search contract is live and strict-compared; vector execution is owned by the dedicated `vector-ml` profile. |
| `POST /{index}/_refresh` | Implemented | Partial | Refresh visibility and write refresh policies are covered. |
| `PUT /_snapshot/{repository}/{snapshot}`, status, restore | Partial | Partial | Development fs-style snapshot/restore only. |
| k-NN plugin routes under `/_plugins/_knn` | Partial | Partial | Stats, warmup, clear cache, model train/get/delete/search are represented. |
| ML Commons routes under `/_plugins/_ml` | Partial | Partial | Model groups, register/deploy/undeploy/predict/search/rerank/task lookup are represented. |
| Core REST handlers from OpenSearch `ActionModule` not listed above | Planned | Planned | 167 core handler registration sites exist in OpenSearch and still require explicit per-route triage. |
| Java plugin REST handlers | Out of scope | Out of scope | Java plugin ABI is out of scope; Rust-native equivalents are handled case by case. |

## Transport Action Summary

| Transport surface | Internal status | OpenSearch compatibility status | Notes |
| --- | --- | --- | --- |
| TCP frame encode/decode | Implemented | Partial | Rust can parse and build OpenSearch transport frames. |
| Ping and handshake frames | Implemented | Partial | TCP probe decodes remote version, cluster name, and node identity. |
| Transport error response decode | Partial | Partial | Known remote errors convert to OpenSearch-shaped errors; complete exception registry is missing. |
| Cluster-state request/response read path | Partial | Partial | Decode-first scaffold and version-gated custom payload coverage exist; full diff apply and named writeable coverage are incomplete. |
| Steelsearch-native shard search and development cluster transport | Implemented | N/A | Used for Steelsearch daemon-to-daemon development clusters, not Java node compatibility. |
| Core `ActionModule` transport actions | Planned | Planned | 148 core action registrations exist in OpenSearch and still need per-action replacement decisions. |
| k-NN transport actions | Planned | Planned | k-NN REST and internal model surfaces exist; OpenSearch k-NN transport handlers are not implemented. |
| Java mixed data-node transport behavior | Out of scope | Out of scope | Discovery, recovery, shard store, Lucene/JVM internals, and Java plugin hot paths are excluded from the current milestone. |

## Replacement Readiness Summary

| Capability | Current replacement judgement |
| --- | --- |
| Development Steelsearch daemon for supported REST tests | Possible. |
| Development OpenSearch comparison for supported fixtures | Possible with `RUN_OPENSEARCH_COMPARISON=1` and a usable OpenSearch service or checkout. |
| Development migration rehearsal into Steelsearch | Possible for supported mappings, documents, bulk writes, search, and vector fixtures. |
| Standalone k-NN search | Possible on the canonical `vector-ml` profile. |
| Standalone model-serving-to-vector-search flow | Possible on the canonical `vector-ml` profile. |
| Development multi-node Steelsearch cluster | Possible for Steelsearch-native daemons only. |
| Production OpenSearch cluster replacement | Not ready. |
| Production OpenSearch API parity | Not ready. |
| Java OpenSearch data-node replacement inside an existing Java cluster | Not supported. |
| OpenSearch Security plugin replacement | Not supported. |

## Matrix Gaps To Close

- Keep exact source-derived REST route rows in
  `docs/rust-port/generated/source-rest-routes.tsv`.
- Keep exact source-derived transport action rows in
  `docs/rust-port/generated/source-transport-actions.tsv`.
- The generator is `tools/source-compatibility-matrix.sh`; it currently records
  source-derived route/action inventory, not this human readiness matrix.
- Drift checking is handled by `tools/check-source-compatibility-drift.sh` and
  `.github/workflows/source-compatibility.yml`.
- Attach native Steelsearch crate/module owner to each planned OpenSearch route
  and transport action.
- Expand comparison fixtures until every implemented daemon route has both
  positive and negative Steelsearch/OpenSearch cases.
- Promote standalone multi-node, snapshot, migration, k-NN, and model-serving
  rows beyond `Partial` only after durability, security, observability,
  upgrade, and failure-mode criteria are documented and tested.
