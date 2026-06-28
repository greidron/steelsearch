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
- [compatibility-promotion-ledger.md](/home/ubuntu/steelsearch/docs/rust-port/compatibility-promotion-ledger.md)

## Current Compatibility By Area

| Source area | Internal library support | Daemon HTTP support | OpenSearch API compatibility | Production readiness | Replacement blocker | Exit criteria anchor |
| --- | --- | --- | --- | --- | --- | --- |
| Root and basic node identity | Implemented | Implemented | Implemented | Yes | Standalone root identity is promoted through runtime-backed route parity, semantic parity, and secure auth-envelope gate evidence. | [root-and-basic-node-identity](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-root-and-basic-node-identity) |
| Cluster health, state, allocation, and node stats | Implemented | Implemented | Implemented | Yes | Standalone admin route parity is promoted through bounded `_cluster/*`, `_nodes/*`, `_cat/*` reports, with distributed-required fields split into a separate transport-admin gate. | [cluster-health-state-allocation-and-node-stats](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-cluster-health-state-allocation-and-node-stats) |
| Index create/get/delete and mappings/settings | Implemented | Implemented | Implemented | Yes | Index metadata parity is promoted through template/alias/data-stream/settings/mapping reports, while restricted-target behavior stays owned by the secure claim gate. | [index-create-get-delete-and-mappings-settings](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-index-create-get-delete-and-mappings-settings) |
| Document write/read and refresh | Implemented | Implemented | Implemented | Yes | Document write parity is promoted through single-doc, routing, refresh, and multi-node durability evidence aggregated into one gate. | [document-write-read-and-refresh](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-document-write-read-and-refresh) |
| REST `_bulk` | Implemented | Implemented | Implemented | Yes | Bulk parity is promoted through metadata/error-path/replay/refresh evidence, plus required secure authz and multi-node durability gates. | [rest-bulk](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-rest-bulk) |
| REST `_search` | Implemented | Implemented | Implemented | Yes | Search parity is promoted through DSL/session/aggregation/partial-failure evidence, plus secure read gate and explicit fail-closed deny ledger. | [rest-search](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-rest-search) |
| k-NN vector indexing and query search | Implemented | Implemented | Implemented | Yes | Vector parity is promoted through lucene score-space, byte/binary, hybrid, nested/filter, ranking evidence, plus an explicit reject ledger for unsupported vector capabilities. | [knn-vector-indexing-and-query-search](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-knn-vector-indexing-and-query-search) |
| k-NN plugin REST and model APIs | Implemented | Implemented | Implemented | Yes | Standalone k-NN plugin parity is promoted through settings/model/warmup/cache/breaker evidence, while secure clustered lifecycle remains outside the standalone claim. | [knn-plugin-rest-and-model-apis](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-knn-plugin-rest-and-model-apis) |
| ML Commons, neural search, and model serving | Implemented | Implemented | Implemented | Yes | ML parity is promoted through task/deploy/predict lifecycle evidence, connector authz, and explicit runtime/deployment isolation classes. | [ml-commons-neural-search-and-model-serving](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-ml-commons-neural-search-and-model-serving) |
| Snapshot and restore | Implemented | Implemented | Partial | Yes | Steelsearch-native snapshot lifecycle is implemented, but direct OpenSearch snapshot repository compatibility/import is intentionally unsupported; OpenSearch data movement is promoted through migration tooling and mixed-cluster shard movement instead. | [snapshot-and-restore](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-snapshot-and-restore) |
| Migration and replacement tooling | Implemented | N/A | Implemented | Yes | Migration parity is promoted through translation/export/resume/vector evidence, approval/rollback automation, unsupported-feature preflight blocking, and final cutover go/no-go aggregation. | [migration-and-replacement-tooling](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-migration-and-replacement-tooling) |
| Steelsearch multi-node runtime | Implemented | Implemented | Implemented | Yes | Peer-node parity is promoted through quorum/publication ordering, rolling stability, mixed-cluster failure handling, and durability convergence evidence aggregated into one phase-C claim gate. | [steelsearch-multi-node-runtime](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-steelsearch-multi-node-runtime) |
| Native transport frame and OpenSearch probe compatibility | Implemented | N/A | Implemented | Yes | External interop parity is promoted through handshake/version gating, stale-cache and mixed-mode failure harnesses, named-writeable and cluster-state diff evidence, plus an explicit binary dispatch allow/reject proof. | [native-transport-frame-and-opensearch-probe-compatibility](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-native-transport-frame-and-opensearch-probe-compatibility) |
| Security and access control | Implemented | Implemented | Implemented | Yes | Secure parity is promoted through TLS, authn/authz, restricted-index policy, audit, plugin secret-handling, and final secure claim evidence that requires redaction smoke plus secure durability/restart artifacts. | [security-and-access-control](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-security-and-access-control) |
| OpenSearch comparison harness | Implemented | N/A | Implemented | Yes | Harness governance is promoted through required-suite manifests, unified parity schema, baseline aggregation completeness, and fail-closed smoke evidence, without replacing feature-specific claim gates. | [opensearch-comparison-harness](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-opensearch-comparison-harness) |
| Java OpenSearch data-node compatibility | In progress | N/A | Optional track | No | Java data-node compatibility is now an explicit optional track backed by mixed-cluster binary harnesses, but it remains outside core replacement readiness. | [java-opensearch-data-node-compatibility](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-java-opensearch-data-node-compatibility) |
| Java plugin ABI compatibility | In progress | N/A | Optional track | No | Java plugin ABI compatibility is now an explicit optional track backed by scope and compat-layer harnesses, but it remains outside core replacement readiness. | [java-plugin-abi-compatibility](/home/ubuntu/steelsearch/docs/rust-port/replacement-claim-exit-criteria.md#area-java-plugin-abi-compatibility) |

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
| `PUT /{index}/_doc/{id}`, `GET /{index}/_doc/{id}`, `DELETE /{index}/_doc/{id}`, `POST /{index}/_update/{id}` | Partial | Partial | Single-document index/get/delete/update routes exist with routing, aliases, data streams, optimistic concurrency, noop, script assignment, and upsert comparison evidence; broader production write semantics remain partial. |
| `POST /_bulk`, `POST /{index}/_bulk` | Implemented | Partial | Standalone write-path contract is live and strict-compared; broader production semantics remain. |
| `GET /_search`, `POST /_search`, `GET /{index}/_search`, `POST /{index}/_search` | Implemented | Partial | Standalone lexical search contract is live and strict-compared; vector execution is owned by the dedicated `vector-ml` profile. |
| `POST /{index}/_refresh` | Implemented | Partial | Refresh visibility and write refresh policies are covered. |
| `PUT /_snapshot/{repository}/{snapshot}`, status, restore | Partial | Partial | Steelsearch-native repository/create/restore flow only; direct OpenSearch snapshot repository compatibility/import is not supported. |
| k-NN plugin routes under `/_plugins/_knn` | Partial | Partial | Stats, warmup, clear cache, model train/get/delete/search are represented. |
| ML Commons routes under `/_plugins/_ml` | Partial | Partial | Model groups, register/deploy/undeploy/predict/search/rerank/task lookup are represented. |
| Additional source-derived REST handlers | Implemented | Partial | All in-scope source REST rows are classified in the generated inventory; exhaustive positive/negative live comparison still needs to expand across the route surface. |
| Java plugin REST handlers | Out of scope | Out of scope | Java plugin ABI is out of scope; Rust-native equivalents are handled case by case. |

## Transport Action Summary

| Transport surface | Internal status | OpenSearch compatibility status | Notes |
| --- | --- | --- | --- |
| TCP frame encode/decode | Implemented | Partial | Rust can parse and build OpenSearch transport frames. |
| Ping and handshake frames | Implemented | Partial | TCP probe decodes remote version, cluster name, and node identity. |
| Transport error response decode | Partial | Partial | Known remote errors convert to OpenSearch-shaped errors; complete exception registry is missing. |
| Cluster-state request/response read path | Partial | Partial | Decode-first scaffold and version-gated custom payload coverage exist; full diff apply and named writeable coverage are incomplete. |
| Steelsearch-native shard search and development cluster transport | Implemented | N/A | Used for Steelsearch daemon-to-daemon development clusters, not Java node compatibility. |
| Core `ActionModule` transport actions | Partial | Partial | 74 core action rows are implemented and the remaining 74 core rows have explicit fail-closed transport boundaries; most server-side execution semantics remain partial. |
| k-NN transport actions | Partial | Partial | All 12 k-NN transport action rows have source-derived fail-closed request/response boundaries; model, cache, warmup, stats, and training execution semantics remain partial. |
| Java mixed data-node transport behavior | Out of scope | Out of scope | Discovery, recovery, shard store, Lucene/JVM internals, and Java plugin hot paths are excluded from the current milestone. |

Current transport coverage evidence:

- `tools/report-transport-action-coverage.py` compares the source-derived
  transport inventory in `docs/rust-port/generated/source-transport-actions.tsv`
  with current Steelsearch evidence. The current inventory has 160 transport
  actions: 74 `implemented`, 86 `partial`, and 0 `planned`.
- The 86 `partial` rows mean Steelsearch has explicit source-derived
  fail-closed action classification plus request/response wire boundary
  coverage where applicable. They do not mean Steelsearch can execute every
  action server-side yet.
- All 12 k-NN plugin transport action registrations from
  `/home/ubuntu/k-NN/src/main/java/org/opensearch/knn/plugin/KNNPlugin.java`
  are now represented as `partial` rows with fail-closed boundaries.
- `target/runtime-peer-backpressure-current.json` is passing evidence for the
  `mixed-java-rust-query-phase` profile. It proves query-phase backpressure and
  readback behavior across the Rust remote-transport receiver and the Java
  OpenSearch peer search-thread-pool analogue.
- That evidence does not promote generic OpenSearch transport action execution.
  The current transport claim is frame/handshake/probe coverage, explicit
  fail-closed action admission, implemented core action rows, and the
  query-phase backpressure profile until additional actions are implemented and
  validated one by one.

## Replacement Readiness Summary

| Capability | Current replacement judgement |
| --- | --- |
| Development Steelsearch daemon for supported REST tests | Possible. |
| Development OpenSearch comparison for supported fixtures | Possible with `RUN_OPENSEARCH_COMPARISON=1` and a usable OpenSearch service or checkout. |
| Development migration rehearsal into Steelsearch | Possible for supported mappings, documents, bulk writes, search, and vector fixtures. |
| Standalone k-NN search | Possible on the canonical `vector-ml` profile. |
| Standalone model-serving-to-vector-search flow | Possible on the canonical `vector-ml` profile. |
| Development multi-node Steelsearch cluster | Possible for Steelsearch-native daemons only. |
| Direct OpenSearch snapshot repository compatibility/import | Not supported. |
| Production OpenSearch cluster replacement | Not ready. |
| Production OpenSearch API parity | Not ready. |
| Java OpenSearch data-node replacement inside an existing Java cluster | Not supported. |
| OpenSearch Security plugin replacement | Not supported. |

Current 0.2.4 mixed-cluster coverage evidence:

- `tools/report-mixed-cluster-coverage.py --require-passed` aggregates the
  retained phase-C join, recovery, failure, write-replication, publication,
  allocation, and shard-movement reports.
- The current retained coverage has 10/10 phase-C reports passed, the
  representative three-node shard movement report passed, both
  OpenSearch-to-Steelsearch and Steelsearch-to-OpenSearch movement directions
  passed, and checkpoint drift is zero for the recorded movement phases.
- This is representative mixed-cluster join/movement/recovery evidence. It is
  not a generic Java OpenSearch data-node replacement claim for arbitrary
  existing Java clusters, Java plugin hot paths, Lucene segment/translog binary
  compatibility, or direct OpenSearch snapshot repository import.

## Matrix Gaps To Close

- Keep exact source-derived REST route rows in
  `docs/rust-port/generated/source-rest-routes.tsv`.
- Keep exact source-derived transport action rows in
  `docs/rust-port/generated/source-transport-actions.tsv`.
- The generator is `tools/source-compatibility-matrix.sh`; it currently records
  source-derived route/action inventory, not this human readiness matrix.
- Current source-derived inventory is not an exhaustive OpenSearch API
  compatibility closure claim. The generated matrix currently has 754 rows:
  389 REST routes, 160 transport actions, 127 search registrations, and 78 node
  runtime entries. Of the transport source rows, 74 are `implemented`, 86 are
  `partial`, and none remain `planned`; the partial rows still require
  owner-level server-side execution work before they can be promoted. Of the
  REST source rows, 371 are in scope and all are now classified as
  `implemented` in the source-derived matrix; exhaustive positive/negative live
  comparison still needs to expand across the route surface. Of the search
  registration rows, 120 are now classified as `implemented` from Rust DSL and
  engine evidence, while 7 generic plugin/extension hook rows remain
  `planned`. Of the node runtime rows, 61 are classified as `partial` because
  Steelsearch has corresponding bounded runtime owners, while 17 remain
  `planned`.
- Drift checking is handled by `tools/check-source-compatibility-drift.sh` and
  `.github/workflows/source-compatibility.yml`.
- Attach native Steelsearch crate/module owner to each remaining partial
  transport action and any REST route whose live comparison evidence is still
  representative rather than exhaustive.
- Expand comparison fixtures until every implemented daemon route has both
  positive and negative Steelsearch/OpenSearch cases.
- Promote standalone multi-node, snapshot, migration, k-NN, and model-serving
  rows beyond `Partial` only after durability, security, observability,
  upgrade, and failure-mode criteria are documented and tested.
