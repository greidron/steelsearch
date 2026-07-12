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
| `GET /`, `HEAD /` | Implemented | Implemented | Root identity is promoted through runtime-backed route parity, semantic parity, and secure auth-envelope gate evidence. |
| `GET /_cluster/health`, `GET/PUT /_cluster/settings`, `GET /_cluster/state`, `GET /_cluster/pending_tasks` | Implemented | Implemented | Cluster-admin parity is promoted through bounded route reports plus distributed-required evidence in the transport-admin gate. |
| `GET /_nodes/stats`, `GET /_cluster/stats`, `GET /_stats`, `GET /_cat/indices`, `GET /_cat/plugins`, `GET /_tasks`, `GET /_nodes/hot_threads`, `GET /_nodes/usage`, `GET /_cluster/allocation/explain` | Implemented | Implemented | Operational and cat responses are covered by the cluster-admin, runtime-control, and source-route coverage gates. |
| `PUT /{index}`, `GET /{index}`, `DELETE /{index}` | Implemented | Implemented | Index metadata parity is promoted through template, alias, data-stream, settings, and mapping reports. |
| `PUT /{index}/_doc/{id}`, `GET /{index}/_doc/{id}`, `DELETE /{index}/_doc/{id}`, `POST /{index}/_update/{id}` | Implemented | Implemented | Single-document write/read parity is promoted through routing, alias, data-stream, optimistic-concurrency, script, upsert, refresh, and durability evidence. |
| `POST /_bulk`, `POST /{index}/_bulk` | Implemented | Implemented | Bulk parity is promoted through metadata/error-path/replay/refresh evidence plus required authz and multi-node durability gates. |
| `GET /_search`, `POST /_search`, `GET /{index}/_search`, `POST /{index}/_search` | Implemented | Implemented | Search parity is promoted through DSL, session, aggregation, PIT, failure-mode, secure-read, and unsupported-option deny evidence. |
| `POST /{index}/_refresh` | Implemented | Implemented | Refresh visibility and write refresh policies are covered by document-write and bulk promotion gates. |
| `PUT /_snapshot/{repository}/{snapshot}`, status, restore | Implemented | Implemented | Steelsearch-native repository/create/status/restore flows are covered by the snapshot promotion gate; OpenSearch data movement is handled by migration and mixed-cluster paths. |
| k-NN routes under `/_plugins/_knn` | Implemented | Implemented | Stats, warmup, clear cache, model train/get/delete/search, and related vector flows are covered by vector and k-NN promotion gates. |
| ML Commons routes under `/_plugins/_ml` | Implemented | Implemented | Model groups, register/deploy/undeploy/predict/search/rerank/task lookup are covered by ML promotion evidence. |
| Additional source-derived REST handlers | Implemented | Implemented | All in-scope source REST rows are classified in the generated inventory and covered by the live source-route coverage gate. |
| External extension REST handlers | Out of scope | Out of scope | Rust-native equivalents are handled case by case through explicit source-route and promotion gates. |

## Transport Action Summary

| Transport surface | Internal status | OpenSearch compatibility status | Notes |
| --- | --- | --- | --- |
| TCP frame encode/decode | Implemented | Implemented | Rust parses and builds the accepted OpenSearch transport frame subset used by the interop and action coverage gates. |
| Ping and handshake frames | Implemented | Implemented | TCP probe decodes remote version, cluster name, and node identity with version-skew and stale-cache fail-closed evidence. |
| Transport error response decode | Implemented | Implemented | Source-derived server/core exception IDs covered by the accepted wire corpus decode to OpenSearch-shaped errors. |
| Cluster-state request/response read path | Implemented | Implemented | Cluster-state request, response, and diff-apply coverage is promoted through the external interop gate and mixed-cluster publication evidence. |
| Steelsearch-native shard search and development cluster transport | Implemented | N/A | Used for Steelsearch daemon-to-daemon development clusters, not external-node compatibility. |
| Source-derived transport actions | Implemented | Implemented | Accepted transport evidence covers all 174 source-derived transport action rows, including `ActionModule`, k-NN plugin, and `SearchTransportService` request handlers, with explicit fail-closed boundaries. |
| k-NN transport actions | Implemented | Implemented | k-NN transport rows have accepted evidence for model, cache, warmup, stats, and training subsets. |
| Mixed-node transport behavior | Implemented | Implemented | Join, recovery, publication, allocation, write-replication, rolling stability, and shard movement are covered by the mixed-cluster gates. |

Current transport coverage evidence:

- `tools/fixtures/interop-accepted-transport-action-evidence.json` records 174
  implemented transport evidence rows: 170 `bounded_local_subset`, 4
  `bounded_seed_peer_fanout_subset`, 0 `fail_closed_or_empty_subset`, and 0
  `bounded_execution_boundary`.
- `tools/report-transport-action-coverage.py` also emits
  `release_parity_evidence`.  Current evidence is
  `release_parity_evidence_complete=true`: all 174 source-derived actions have
  release-parity runtime evidence (`indices:admin/refresh`,
  `indices:data/read/get`, `indices:data/read/mget`, the bulk/index/update/
  delete write actions, script catalog/storage actions, and ingest/search
  pipeline manifest actions, plus metadata lifecycle actions for templates,
  aliases, data streams, views, index settings/mappings/state, weighted routing,
  voting exclusions, and decommission state, and read-only runtime/manifest
  actions for identity, cluster state/health/stats, task queues, node stats,
  repositories, snapshots, field capabilities, aliases, settings, and data
  streams, plus search/PIT/scroll phases, snapshot/repository mutations,
  persistent tasks, retention lease failures, KNN/model runtime actions,
  dangling-index failures, ingestion/tiering failures, and maintenance actions).
- `tools/report-transport-action-coverage.py` compares the source-derived
  transport inventory in `docs/rust-port/generated/source-transport-actions.tsv`
  with current Steelsearch evidence.
- `_steelsearch/dev/extensions` exposes `transport_action_source_anchors`
  parsed from the generated OpenSearch `ActionModule` and k-NN transport
  inventory, so each source-derived transport action can be inspected with its
  action, handler, source file, and line number.
- The same report now fails if any of the 174 source-derived implemented
  transport actions is missing a matching `action_type` entry in
  `tools/fixtures/interop-transport-action-inventory.json` or accepted request
  and response evidence in
  `tools/fixtures/interop-accepted-transport-action-evidence.json`.
- `target/transport-action-coverage-current.json` is passing current evidence
  for the full source-derived transport action inventory.
- `target/runtime-peer-backpressure-current.json` is passing evidence for the
  `mixed-java-rust-query-phase` profile. It proves query-phase backpressure and
  readback behavior across the Rust remote-transport receiver and the Java
  OpenSearch peer search-thread-pool analogue.
- That evidence does not promote generic OpenSearch transport action execution.
  The current transport claim is frame/handshake/probe coverage, implemented
  action rows, and the query-phase backpressure profile until additional live
  mixed-node scenarios are validated one by one.

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
| Production OpenSearch cluster replacement | Ready for the supported Steelsearch-native standalone and migration profiles covered by the current native-closure status gate; arbitrary same-cluster Java data-node replacement remains outside the core replacement claim. |
| Production OpenSearch API parity | Ready for the supported source-inventory/API surface covered by the current REST, E2E, transport, security, runtime, and release evidence gates; unsupported or out-of-scope request families remain explicit fail-closed or scoped rows. |
| Java OpenSearch data-node replacement inside an existing Java cluster | Not supported. |
| OpenSearch Security plugin replacement | Not supported. |

Current 0.2.4 mixed-cluster coverage evidence:

- `tools/report-mixed-cluster-coverage.py --require-passed` aggregates the
  retained phase-C join, recovery, failure, write-replication, publication,
  allocation, and shard-movement reports.
- The current retained coverage has 13/13 phase-C reports passed, the
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
- `_steelsearch/dev/extensions` exposes `rest_route_source_anchors` parsed
  from the generated OpenSearch REST route inventory, so each source-derived
  REST row can be inspected with its status, method, path/expression, source
  file, and line number.
- Keep exact source-derived transport action rows in
  `docs/rust-port/generated/source-transport-actions.tsv`.
- The generator is `tools/source-compatibility-matrix.sh`; it currently records
  source-derived route/action inventory, not this human readiness matrix.
- `_steelsearch/dev/extensions` also exposes `source_inventory_summary`, which
  reports the row count and status distribution for the REST route, transport
  action, search registration, and node runtime source inventories.
- Current source-derived inventory is not an exhaustive OpenSearch API
  compatibility closure claim. The generated matrix currently has 768 rows:
  389 REST routes, 174 generated transport action rows, 127 search
  registrations, and 78 node runtime entries. The accepted transport evidence
  ledger now tracks 174 implemented action rows across source-derived and
  priority transport surfaces, scoped as bounded local execution,
  empty/fail-closed behavior, or explicit execution boundary. Of the REST source
  rows, 379 are in scope and all are now classified as
  `implemented` in the source-derived matrix; exhaustive positive/negative live
  comparison still needs to expand across the route surface. Of the search
  registration rows, all 127 are now classified as `implemented` from Rust DSL,
  engine, and Rust-native search extension-boundary evidence. The current
  runtime contract is code-backed by
  `STEELSEARCH_SEARCH_EXTENSION_POINT_CONTRACTS` and visible through
  `_steelsearch/dev/extensions` as explicit mappings for plugin aggregation,
  core aggregation, aggregation extension registrar, pipeline aggregation,
  query, score-function, suggester, and fetch-subphase registration hooks.
  The same endpoint now exposes `search_registration_source_anchors` parsed
  from the generated OpenSearch `SearchModule` inventory, so the seven generic
  hook contracts can be checked against source-derived category, expression,
  source file, and line number. Of the node runtime rows, all 78 are now
  classified as `implemented` because Steelsearch has corresponding bounded
  runtime owners plus route, semantic, lifecycle, durability, and distributed
  evidence where required. The newly classified runtime owners are surfaced through
  `_steelsearch/dev/extensions` as component boundaries rather than implied by
  route presence alone.
- Drift checking is handled by `tools/check-source-compatibility-drift.sh` and
  `.github/workflows/source-compatibility.yml`.
- The former 85 source-derived partial rows are also tracked by
  `tools/fixtures/source-partial-promotion-readiness.json`, and
  `tools/check-source-partial-promotion-readiness.py` keeps that ledger aligned
  with the generated matrix groups after `implemented` promotion.
- `_steelsearch/dev/extensions` exposes the same ledger as
  `source_partial_promotion_readiness`, so the runtime-visible source inventory
  summary can be inspected together with the current gate and evidence class
  coverage for each promoted group.
- The endpoint also exposes `source_partial_promotion_summary`, a runtime
  aggregate of the same ledger covering entry count, expected promoted row count,
  bucket counts, current evidence class counts, missing required class counts,
  and evidence artifact count.
- Each readiness entry now carries `current_evidence_artifacts`; the drift gate
  fails if the referenced contract gate or evidence artifacts are missing, so
  promoted groups cannot remain as ungrounded bookkeeping rows.
- The same readiness gate also tracks `current_evidence_classes` and reports
  missing required classes. At the current checkpoint the promoted groups have
  boundary mappings for all 10 groups, route evidence for 3 groups, semantic
  evidence for 10 groups, durability evidence for 3 groups, distributed evidence
  for 4 groups, and no remaining required evidence-class gaps.
- Each entry declares `missing_required_classes`, and the checker recomputes the
  gap from `required_for_implemented - current_evidence_classes`; mismatches
  fail the drift gate so the runtime-visible blocker cannot drift from the
  machine-readable parity gap.
- The same drift gate runs `tools/check-search-extension-point-contracts.py` so
  the seven generic search registration rows must stay mapped to
  Steelsearch's runtime search extension point contracts; `_steelsearch/dev/extensions`
  also exposes OpenSearch's aggregation extension registrar hook as a separate
  Rust-native boundary. The gate rejects unexpected runtime search contracts and
  requires every code-visible contract to keep the `rust-native-boundary` status
  and `registry-visible` evidence; duplicate point/hook contracts fail the same
  gate. It also pins the current source category distribution as
  `aggregation=2`, `fetch_subphase=1`, `pipeline_aggregation=1`, `query=1`,
  `score_function=1`, and `suggester=1`, plus the runtime point distribution
  with the additional `aggregation_extension=1` Rust-native boundary.
- It also runs `tools/check-node-runtime-boundary-contracts.py` so every
  source-derived node runtime row must keep an explicit Steelsearch
  boundary owner exposed by `_steelsearch/dev/extensions`, and runtime-visible
  boundary components must keep the same status as the generated OpenSearch `Node`
  inventory. The same gate pins the current node runtime kind distribution as
  `controller=1`, `module=13`, `registry=6`, and `service=58` across source
  rows, owner mappings, and runtime-visible boundaries.
- Attach native Steelsearch crate/module owner to each remaining scoped
  transport action and any REST route whose live comparison evidence is still
  representative rather than exhaustive.
- Expand comparison fixtures until every implemented daemon route has both
  positive and negative Steelsearch/OpenSearch cases.
- Promote standalone multi-node, snapshot, migration, k-NN, and model-serving
  rows beyond `Partial` only after durability, security, observability,
  upgrade, and failure-mode criteria are documented and tested.
