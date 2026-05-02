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

## Replacement Profiles

This matrix is now read through four replacement profiles rather than phase
labels:

| Profile | Meaning |
| --- | --- |
| `standalone` | Steelsearch-only deployment without production security guarantees. |
| `secure standalone` | Standalone deployment with authn/authz, TLS, and restricted-index controls required for production use. |
| `external interop` | Steelsearch stays outside Java OpenSearch membership and acts as an external client/coordinator/observer. |
| `same-cluster peer-node` | Steelsearch joins or participates as a real mixed-cluster node alongside Java OpenSearch. |

Interpretation rules:

- `Production readiness = No` means the row is not replacement-ready for at
  least `standalone`, and usually for every stronger profile as well.
- A row can be sufficient for `standalone` while still blocking
  `secure standalone`, `external interop`, or `same-cluster peer-node`.
- Search, write, snapshot, and vector rows need separate semantic evidence
  beyond route presence before they can be promoted from development parity to
  replacement parity.

## Current Evidence And Replacement Blockers

The matrix is intentionally a summary view. Read each row with these fields in
mind:

- `current evidence`: what the repository already proves today through code,
  fixtures, semantic probes, or compare harnesses;
- `replacement blocker`: what still prevents a safe replacement claim for one
  or more profiles;
- `required tests`: the missing probes, fixtures, or harnesses needed to
  promote a row;
- `required implementation`: the missing runtime behavior, persistence,
  security, or distributed semantics needed to promote a row.

The detailed expansion of those fields lives in the profile-specific gap
inventories such as:

- [node-runtime-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/node-runtime-gap-inventory.md)
- [production-security-baseline.md](/home/ubuntu/steelsearch/docs/rust-port/production-security-baseline.md)
- [phase-b-safe-interop.md](/home/ubuntu/steelsearch/docs/rust-port/phase-b-safe-interop.md)
- [phase-c-peer-node-compat.md](/home/ubuntu/steelsearch/docs/rust-port/phase-c-peer-node-compat.md)
- [replacement-claim-exit-criteria.md](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md)

## Current Compatibility By Area

| Source area | Internal library support | Daemon HTTP support | OpenSearch API compatibility | Production readiness | Replacement blocker | Exit criteria anchor |
| --- | --- | --- | --- | --- | --- | --- |
| Root and basic node identity | Implemented | Implemented | Partial | No | Identity routes exist, but replacement claims still lack full semantic and readiness evidence beyond the development envelope. | [root-and-basic-node-identity](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-root-and-basic-node-identity) |
| Cluster health, state, allocation, and node stats | Implemented | Partial | Partial | No | Operational routes exist, but allocation, wait semantics, and production cluster-state behavior still lack bounded distributed evidence. | [cluster-health-state-allocation-and-node-stats](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-cluster-health-state-allocation-and-node-stats) |
| Index create/get/delete and mappings/settings | Implemented | Partial | Partial | No | Core index shell exists, but templates, aliases, dynamic mappings, wildcard safety, and production settings semantics remain incomplete. | [index-create-get-delete-and-mappings-settings](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-index-create-get-delete-and-mappings-settings) |
| Document write/read and refresh | Implemented | Partial | Partial | No | Core write/read paths exist, but routing, realtime/source options, full conflict behavior, and durable replacement semantics remain incomplete. | [document-write-read-and-refresh](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-document-write-read-and-refresh) |
| REST `_bulk` | Implemented | Implemented | Partial | No | Standalone bulk works, but bulk metadata, retry/shard-failure semantics, external versioning, and secure write behavior remain incomplete. | [rest-bulk](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-rest-bulk) |
| REST `_search` | Implemented | Implemented | Partial | No | Search routes work, but full DSL, pagination variants, session features, aggregation breadth, and secure/distributed readiness remain incomplete. | [rest-search](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-rest-search) |
| k-NN vector indexing and query search | Implemented | Implemented | Partial | No | Canonical vector flows exist, but native engine parity, score-space breadth, nested/script semantics, and exact ranking parity remain incomplete. | [knn-vector-indexing-and-query-search](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-knn-vector-indexing-and-query-search) |
| k-NN plugin REST and model APIs | Implemented | Partial | Partial | No | Plugin-shaped REST surfaces exist, but transport actions, training internals, circuit-breaker semantics, and secure clustered lifecycle behavior remain incomplete. | [knn-plugin-rest-and-model-apis](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-knn-plugin-rest-and-model-apis) |
| ML Commons, neural search, and model serving | Implemented | Partial | Partial | No | Development model flows exist, but task lifecycle, connectors, authz, persistent deployment, and runtime isolation remain incomplete. | [ml-commons-neural-search-and-model-serving](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-ml-commons-neural-search-and-model-serving) |
| Snapshot and restore | Implemented | Partial | Partial | No | Standalone snapshot/restore routes exist, but incremental, remote-store, searchable-snapshot, and restore-safety completeness remain incomplete. | [snapshot-and-restore](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-snapshot-and-restore) |
| Migration and replacement tooling | Implemented | N/A | Partial | No | Rehearsal tooling exists, but translation breadth, resumability, unsupported-feature gating, and production cutover evidence remain incomplete. | [migration-and-replacement-tooling](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-migration-and-replacement-tooling) |
| Steelsearch multi-node runtime | Implemented | Implemented | Partial | No | Development multi-node works, but quorum, discovery, upgrade, durability, and mixed-membership behavior are not production-ready. | [steelsearch-multi-node-runtime](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-steelsearch-multi-node-runtime) |
| Native transport frame and OpenSearch probe compatibility | Partial | N/A | Partial | No | Decode scaffolding exists, but action execution, named-writeable coverage, cluster-state diffs, and binary compatibility remain incomplete. | [native-transport-frame-and-opensearch-probe-compatibility](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-native-transport-frame-and-opensearch-probe-compatibility) |
| Security and access control | Stubbed | Stubbed | Planned | No | Secure replacement is blocked until TLS, authn/authz, restricted-index policy, audit, and secret-handling evidence are complete. | [security-and-access-control](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-security-and-access-control) |
| OpenSearch comparison harness | Implemented | N/A | Partial | No | Harness coverage is useful, but not yet broad enough to justify standalone, secure, interop, or peer-node replacement claims by itself. | [opensearch-comparison-harness](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-opensearch-comparison-harness) |
| Java OpenSearch data-node compatibility | Out of scope | N/A | Out of scope | No | Mixed Java data-node membership and JVM recovery participation remain blocked by missing distributed compatibility work. | [java-opensearch-data-node-compatibility](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-java-opensearch-data-node-compatibility) |
| Java plugin ABI compatibility | Out of scope | N/A | Out of scope | No | Java plugin loading and ABI compatibility are not opened as an in-scope replacement track. | [java-plugin-abi-compatibility](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-java-plugin-abi-compatibility) |

Interpretation note for the table above:

- `Replacement blocker` is the one-line reason the row still blocks a stronger
  replacement claim.
- `Exit criteria anchor` points to the profile-aware closing criteria for that
  source area in
  [replacement-claim-exit-criteria.md](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md).

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
