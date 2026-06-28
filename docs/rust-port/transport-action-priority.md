# Transport Action Priority

This document prioritizes OpenSearch transport actions for Steelsearch using the
inventory in `docs/api-spec/generated/transport-actions.md`.

The generated inventory remains the exhaustive list. This file adds
implementation order for replacement milestones.

## Priority Rules

- `Tier 0`: already-covered transport foundations such as handshake, frame
  compatibility, error decode, compression decode, cluster-state request
  builders, and cluster-state decode/probe support.
- `Tier 1`: read/admin actions required to make a Steelsearch-only cluster a
  credible standalone replacement for common operational and observability
  workflows.
- `Tier 2`: read/admin actions that materially improve replacement coverage but
  are not the first gate for Phase A.
- `Tier 3`: actions that are primarily mixed-cluster, repository/migration
  expansion, or plugin-oriented follow-up work.

## Tracking Boundary: Probe Compatibility vs Server-Side Parity

Steelsearch must not treat these as the same class of progress.

### Probe / Interop Compatibility

This includes:

- frame and stream compatibility;
- handshake success;
- request builders that Java OpenSearch accepts;
- response decoders, cluster-state readers, and publication diff readers;
- read-only probes and compatibility scaffolding.

This proves Steelsearch can talk to OpenSearch over transport in a limited or
observational way. It does **not** prove that Steelsearch implements the
corresponding OpenSearch transport action as a server.

### Server-Side Transport Parity

This includes:

- receiving the OpenSearch transport action on a Steelsearch node;
- validating the request with OpenSearch-compatible semantics;
- executing the action against Steelsearch state;
- returning OpenSearch-compatible success and failure responses;
- supporting the action as part of real cluster or admin behavior rather than
  decode-only scaffolding.

### Tracking Rule

- A probe or decoder milestone may close a transport interop task.
- It must not close a server-side transport parity task unless Steelsearch can
  actually serve that action correctly.
- When a route is satisfied through REST-only behavior, keep that progress
  separate from server-side transport parity unless the transport contract is
  also implemented.

### Tracking Buckets

Every transport-facing feature should be tracked in exactly one primary bucket.

- `probe-only`
  - Steelsearch can connect to OpenSearch, send a request, and/or decode the
    response, but does not claim to serve the action.
- `server-side`
  - Steelsearch serves the action on its own node with OpenSearch-shaped
    request validation, execution semantics, and response/error shape for the
    declared subset.
- `mixed-cluster`
  - the action is safe and meaningful when Steelsearch and Java OpenSearch
    participate in the same transport topology, including forwarding,
    publication, or coordination-sensitive behavior.

### Evidence Rule Per Bucket

- `probe-only`
  - requires fixture, decoder, or live probe evidence against Java OpenSearch.
- `server-side`
  - requires Steelsearch integration coverage proving the action is accepted
    and served correctly on Steelsearch nodes.
- `mixed-cluster`
  - requires comparative or mixed-topology integration coverage showing the
    action remains correct when Java OpenSearch nodes are present.

### Non-Substitution Rule

- `probe-only` evidence does not satisfy `server-side` parity.
- `server-side` parity in a Steelsearch-only cluster does not satisfy
  `mixed-cluster` safety.
- `REST` parity does not satisfy transport parity unless the underlying
  transport contract is intentionally out of scope for that phase and marked as
  such.

## Tier 1: Phase A Replacement-Critical Read/Admin Actions

- `ClusterStateAction.INSTANCE`
  - Why: cluster metadata visibility is foundational for admin, debugging, and
    many higher-level workflows.
- `ClusterHealthAction.INSTANCE`
  - Why: health reporting is a basic replacement requirement for operators and
    orchestration systems.
- `ClusterStatsAction.INSTANCE`
  - Why: required for cluster-level observability parity beyond health.
- `NodesStatsAction.INSTANCE`
  - Why: node-level runtime and resource visibility is a common operational
    dependency.
- `IndicesStatsAction.INSTANCE`
  - Why: index/shard stats are core replacement surfaces for operators.
- `PendingClusterTasksAction.INSTANCE`
  - Why: task backlog visibility is part of cluster operability.
- `ListTasksAction.INSTANCE`
- `GetTaskAction.INSTANCE`
- `CancelTasksAction.INSTANCE`
  - Why: task inspection and cancellation are user-visible admin contracts.

## Tier 1 Action Scope And Fail-Closed Policy

### `ClusterStateAction.INSTANCE`

- Phase A scope:
  - support the standalone Steelsearch cluster-state read path needed by
    `GET /_cluster/state` and internal observability;
  - preserve OpenSearch-shaped request validation and response framing for the
    supported metrics/filter subset;
  - reject unsupported metrics, filtering combinations, or state sections
    explicitly.
- Fail-closed rule:
  - if the request asks for a section Steelsearch cannot produce with
    trustworthy semantics, return an OpenSearch-shaped validation or
    unsupported-operation style error instead of a partial silent omission.

### `ClusterHealthAction.INSTANCE`

- Phase A scope:
  - support cluster-wide health reporting for standalone Steelsearch clusters;
  - support the declared subset of wait/timeout semantics that Steelsearch can
    enforce correctly;
  - expose enough counters and status fields for orchestration and admin use.
- Fail-closed rule:
  - if wait conditions, index-scoped semantics, or allocation-sensitive fields
    are not implemented correctly, reject them explicitly rather than returning
    misleading green/yellow/red output.

### `ListTasksAction.INSTANCE`, `GetTaskAction.INSTANCE`, `CancelTasksAction.INSTANCE`

- Phase A scope:
  - expose only tasks that Steelsearch actually tracks as first-class runtime
    work units;
  - define task identity, parent/child linkage, cancellability, and terminal
    status for the supported task subset;
  - keep response shape OpenSearch-compatible for supported fields.
- Fail-closed rule:
  - if a task family is not yet tracked with reliable lifecycle semantics, it
    must be omitted by documented contract or rejected explicitly, not surfaced
    as fake completed/cancellable work;
  - cancellation must fail explicitly for non-cancellable or unknown task ids.

## Suggested Implementation Order Inside Tier 1

1. `ClusterHealthAction.INSTANCE`
   - Smallest user-visible admin contract and easiest standalone replacement
     win.
2. `ClusterStateAction.INSTANCE`
   - Builds on the existing decode/probe and metadata work, but must become a
     trustworthy server-side contract.
3. task actions
   - Depend on a clearer internal task model and cancellation rules.
4. stats actions
   - Expand once the task and cluster/admin contracts are stable enough to
     measure coherently.

## Current Source Boundary Audit

The source-derived transport inventory currently has 160 rows:

| Status | Count | Meaning |
| --- | ---: | --- |
| `implemented` | 101 | Steelsearch has a concrete action row with implemented server-side behavior for the declared subset. |
| `partial` | 59 | Steelsearch has an explicit action classification and bounded fail-closed transport boundary, but broader server-side execution semantics remain incomplete. |
| `planned` | 0 | No source-derived transport action remains unclassified. |

The k-NN plugin action sweep is complete at the boundary layer. All 12
registrations from
`/home/ubuntu/k-NN/src/main/java/org/opensearch/knn/plugin/KNNPlugin.java`
lines 348-359 are represented as `partial` rows with request/response wire
coverage and fail-closed admission. This is not a claim that the k-NN transport
actions execute their full OpenSearch semantics yet; it means unsupported
transport execution is explicit and measured instead of accidentally passing
through.

Current k-NN reject-wire bottlenecks from the retained local release runs:

| Action family | Bottleneck | Throughput |
| --- | --- | ---: |
| kNN stats | request body encode/decode | 129,255 ops/s |
| kNN warmup | request encode | 1,253,890 ops/s |
| update model metadata | request encode | 1,241,681 ops/s |
| training job route decision info | request encode | 1,336,729 ops/s |
| get model | request decode | 1,335,483 ops/s |
| delete model | validation/decode | 1,504,599 ops/s |
| training job router | request encode | 635,124 ops/s |
| training model | request encode | 650,887 ops/s |
| remove model from cache | request encode | 1,258,339 ops/s |
| search model | request encode | 1,383,348 ops/s |
| update model graveyard | request encode | 1,197,542 ops/s |
| clear cache | validation/decode | 1,152,318 ops/s |

The current k-NN boundary hotspot is `KNNStatsAction`: its request body carries
the full valid stat-name set even on the fail-closed path. Stage-level
instrumentation shows pure validation is not the hotspot; request body
encode/decode of the stat-name payload is. The two training actions are the
next wire-level hotspot because their request boundary carries an opaque
training payload stand-in. These are still admission-path costs; the first real
execution bottlenecks to measure after implementation are expected to be:

- BaseNodes fanout and per-node response aggregation for stats, route-decision,
  and remove-model-cache actions;
- broadcast shard selection and per-shard cache/warmup execution for warmup and
  clear-cache actions;
- model system-index lookup, metadata parsing, cache/graveyard coordination,
  and response rendering for get/delete/search/update-model actions;
- training data sizing, method-context parsing, memory reservation, native
  training execution, model writeback, and route-decision forwarding for
  training actions.

## Current Server-Side Transport Adapters

As of the bulk transport adapter pass, the explicit dispatcher contract in
`crates/os-transport/src/action.rs` accepts:

- `cluster:monitor/main` (implemented local root-info subset)
- `cluster:monitor/remote/info` (implemented empty remote-connection subset)
- `internal:monitor/term` (implemented current term/version subset)
- `cluster:monitor/state`
- `cluster:monitor/health`
- `cluster:monitor/stats` (implemented local empty-cluster-stats subset)
- `cluster:monitor/shards` (implemented empty cat-shards subset)
- `cluster:monitor/nodes/info` (implemented local node-info subset)
- `cluster:monitor/nodes/stats` (implemented local empty-node-stats subset)
- `cluster:monitor/wlm/stats` (implemented local empty-workload-group subset)
- `cluster:monitor/_remotestore/stats` (implemented empty remote-store-shards subset)
- `cluster:admin/remote_store/metadata` (implemented empty remote-store-shards subset)
- `cluster:monitor/nodes/usage` (implemented local empty-usage subset)
- `cluster:monitor/nodes/hot_threads` (implemented local diagnostic text subset)
- `cluster:admin/voting_config/add_exclusions` (implemented node_names subset)
- `cluster:admin/voting_config/clear_exclusions` (implemented no-wait subset)
- `cluster:monitor/allocation/explain` (rejected fail-closed)
- `cluster:admin/settings/update` (rejected fail-closed)
- `cluster:admin/reroute` (rejected fail-closed)
- `cluster:admin/filecache/prune` (rejected fail-closed)
- `cluster:admin/nodes/reload_secure_settings` (rejected fail-closed)
- `cluster:admin/repository/put` (rejected fail-closed)
- `cluster:admin/repository/get` (implemented empty repository metadata subset)
- `cluster:admin/repository/delete` (rejected fail-closed)
- `cluster:admin/repository/verify` (rejected fail-closed)
- `cluster:admin/repository/_cleanup` (rejected fail-closed)
- `cluster:admin/snapshot/get` (rejected fail-closed)
- `cluster:admin/snapshot/delete` (rejected fail-closed)
- `cluster:admin/snapshot/create` (rejected fail-closed)
- `cluster:admin/snapshot/clone` (rejected fail-closed)
- `cluster:admin/snapshot/restore` (rejected fail-closed)
- `cluster:admin/snapshot/status` (rejected fail-closed)
- `cluster:admin/routing/awareness/weights/put` (rejected fail-closed)
- `cluster:admin/routing/awareness/weights/get` (implemented manifest-backed
  weighted-routing metadata subset)
- `cluster:admin/routing/awareness/weights/delete` (rejected fail-closed)
- `indices:admin/mappings/get` (implemented manifest-backed empty-mapping metadata subset)
- `indices:admin/mappings/fields/get` (implemented manifest-backed empty field-mapping subset)
- `indices:admin/mapping/auto_put` (implemented concrete-index manifest-backed mapping mutation subset)
- `indices:admin/get` (rejected fail-closed)
- `indices:admin/exists` (rejected fail-closed)
- `indices:admin/template/get` (implemented default all-template legacy metadata subset)
- `indices:admin/template/put` (implemented manifest-backed metadata mutation subset)
- `indices:admin/template/delete` (implemented manifest-backed metadata mutation subset)
- `indices:admin/aliases` (implemented manifest-backed add/remove alias metadata subset)
- `indices:admin/analyze` (implemented bounded default/standard analyzer token subset)
- `cluster:admin/component_template/get` (implemented manifest-backed
  settings-only component-template subset)
- `cluster:admin/component_template/put` (implemented manifest-backed metadata mutation subset)
- `cluster:admin/component_template/delete` (implemented manifest-backed metadata mutation subset)
- `indices:admin/index_template/get` (implemented manifest-backed
  settings-only composable-template subset)
- `indices:admin/index_template/delete` (implemented manifest-backed metadata mutation subset)
- `indices:admin/aliases/get` (implemented empty alias metadata subset)
- `indices:monitor/settings/get` (implemented metadata-backed index-settings subset)
- `indices:admin/shards/search_shards` (implemented empty search-shards subset)
- `indices:data/read/field_caps` (implemented local metadata/document field-capabilities subset)
- `indices:monitor/recovery` (implemented local empty-recovery subset)
- `indices:monitor/segment_replication` (implemented local empty segment-replication-stats subset)
- `indices:monitor/segments` (implemented local empty-segments subset)
- `indices:monitor/point_in_time/segments` (implemented `_all` and explicit-id empty PIT-segments subset)
- `indices:monitor/shard_stores` (implemented local empty-shard-stores subset)
- `indices:admin/data_stream/create` (implemented manifest-backed metadata mutation subset)
- `indices:admin/data_stream/delete` (implemented manifest-backed metadata mutation subset)
- `indices:admin/data_stream/get` (implemented empty data-stream list subset)
- `indices:monitor/data_stream/stats` (implemented empty data-stream-stats subset)
- `indices:admin/resolve/index` (implemented manifest-backed index abstraction
  metadata subset)
- `cluster:admin/views/create` (rejected fail-closed)
- `cluster:admin/views/delete` (rejected fail-closed)
- `views:data/read/get` (rejected fail-closed)
- `cluster:admin/views/update` (rejected fail-closed)
- `views:data/read/list` (implemented empty view-name list subset)
- `views:data/read/search` (rejected fail-closed)
- `cluster:admin/persistent/start` (rejected fail-closed)
- `cluster:admin/persistent/update_status` (rejected fail-closed)
- `cluster:admin/persistent/completion` (rejected fail-closed)
- `cluster:admin/persistent/remove` (rejected fail-closed)
- `indices:admin/seq_no/add_retention_lease` (rejected fail-closed)
- `indices:admin/seq_no/renew_retention_lease` (rejected fail-closed)
- `indices:admin/seq_no/remove_retention_lease` (rejected fail-closed)
- `cluster:admin/indices/dangling/list` (implemented empty dangling-index subset)
- `cluster:admin/indices/dangling/import` (rejected fail-closed)
- `indices:data/read/search` (implemented bounded local search subset)
- `indices:data/read/search/stream` (implemented bounded local search subset)
- `indices:data/read/msearch` (implemented bounded ordered sub-search subset)
- `indices:data/read/scroll` (implemented local scroll-page subset)
- `indices:data/read/scroll/clear` (implemented `_all` empty clear-scroll subset)
- `indices:data/read/explain` (implemented bounded local explain subset)
- `indices:data/read/point_in_time/create` (implemented local PIT lifecycle subset)
- `indices:data/read/point_in_time/delete` (implemented local PIT lifecycle subset)
- `indices:data/read/point_in_time/readall` (implemented local PIT lifecycle subset)
- `cluster:monitor/task` (implemented pending/in-flight task subset)
- `cluster:monitor/tasks/lists` (implemented pending/in-flight task info subset)
- `cluster:monitor/task/get` (implemented tracked running task result subset)
- `cluster:admin/tasks/cancel` (implemented cancellable queued task info subset)
- `indices:data/read/get`
- `indices:data/read/mget`
- `indices:data/write/bulk`
- `indices:data/write/index`
- `indices:data/write/update`
- `indices:data/write/delete`
- `indices:admin/create` (implemented default manifest-backed index metadata mutation subset)
- `indices:admin/auto_create` (implemented default manifest-backed auto-create index metadata mutation subset)
- `cluster:admin/script/put` (implemented manifest-backed stored-script metadata write subset)
- `cluster:admin/script/get` (implemented manifest-backed stored-script metadata read subset)
- `cluster:admin/script/delete` (manifest-backed stored-script deletion)
- `cluster:admin/script_context/get` (implemented Rust-supported script context catalog subset)
- `cluster:admin/script_language/get` (implemented Rust-supported script language catalog subset)
- `cluster:admin/ingest/pipeline/put` (implemented manifest-backed metadata-write subset)
- `cluster:admin/ingest/pipeline/get` (implemented empty pipeline metadata-read subset)
- `cluster:admin/ingest/pipeline/delete` (implemented manifest-backed metadata-write subset)
- `cluster:admin/ingest/pipeline/simulate` (implemented empty-doc simulation subset)
- `indices:admin/refresh`
- `indices:data/read/tv` (rejected fail-closed)
- `indices:data/read/mtv` (rejected fail-closed)
- `indices:admin/flush` (implemented bounded global default subset)
- `indices:admin/forcemerge` (implemented bounded global default subset)
- `indices:admin/upgrade` (implemented bounded global default subset)
- `indices:monitor/upgrade` (implemented bounded global default subset)
- `internal:indices/admin/upgrade` (rejected fail-closed)
- `indices:admin/cache/clear` (implemented bounded global default subset)
- `indices:monitor/stats` (implemented local empty-index-stats subset)

The health adapter covers:

- OpenSearch `ClusterHealthRequest` parent task, default cluster-manager
  timeout, `local=false`, no index scope, default 30s timeout, no wait
  conditions, `ActiveShardCount.NONE`, default `lenientExpandHidden` indices
  options, no awareness attribute, `level=CLUSTER`, no weighted-routing wait,
  and no transport-level index/shard detail filtering;
- OpenSearch `ClusterHealthResponse` cluster name, green/yellow/red status,
  cluster-level shard counters, node counters, discovered cluster-manager flag,
  active shard percentage, pending task counters, timeout flag, in-flight fetch
  count, delayed unassigned shard count, and task max waiting time;
- conversion from the standalone REST/runtime health JSON body into the bounded
  OpenSearch transport response shape;
- explicit rejection for index-scoped health, custom wait timeouts, wait
  conditions, non-default indices options, awareness health, index/shard detail
  levels, weighted-routing waits, transport-level level application, embedded
  index health details, and awareness health response payloads until those
  semantics are mapped.

The main boundary covers:

- OpenSearch `MainRequest` parent task at the wire decode/build layer;
- OpenSearch `MainResponse` node name, cluster name, cluster UUID, version, and
  build metadata wire rendering;
- implemented `cluster:monitor/main` request admission and local root-info
  response rendering from the current transport identity.

The remote-info boundary covers:

- OpenSearch `RemoteInfoRequest` parent task at the wire decode/build layer;
- OpenSearch `RemoteInfoResponse` empty remote connection list at the wire
  decode/build layer;
- implemented `cluster:monitor/remote/info` request admission and empty
  response rendering for deployments without configured remote connections;
- explicit rejection for non-empty remote connection payload decoding until
  full remote connection info wire mapping is implemented.

The get-term-version boundary covers:

- OpenSearch `GetTermVersionRequest` parent task, cluster-manager timeout, and
  local flag at the wire decode/build layer;
- OpenSearch `GetTermVersionResponse` cluster name, cluster UUID, term,
  version, and remote-state-present optional boolean at the wire
  decode/build layer;
- implemented `internal:monitor/term` request admission and local
  term/version response rendering from the current coordination state;
- explicit rejection for custom cluster-manager timeout and local execution.

The cluster-stats boundary covers:

- OpenSearch `ClusterStatsRequest` parent task, node ids, optional timeout,
  aggregated-node-level response flag, compute-all-metrics flag, metric bitset,
  and index metric bitset at the wire decode/build layer;
- implemented local empty `ClusterStatsResponse` rendering for the default
  all-metrics request subset, including cluster name, timestamp, optional
  health status, optional cluster UUID, and absent mapping/analysis stats;
- explicit rejection for concrete node payloads, node filters, timeout,
  aggregated-node response mode, partial metric selection, metric bitsets,
  non-empty node responses, mapping stats, and analysis stats.

The cat-shards boundary covers:

- OpenSearch `CatShardsRequest` parent task, cluster-manager timeout, local
  flag, indices array, optional cancel-after timeout, optional `PageParams`,
  and request-limit support flag at the wire decode/build layer;
- implemented empty `CatShardsResponse` rendering for the default request
  subset, including empty `IndicesStatsResponse`, empty `DiscoveryNodes`, empty
  shard routing list, and absent page token;
- explicit rejection for custom cluster-manager timeout, local reads, index
  filters, cancel-after timeout, pagination, request-limit checks, non-empty
  shard stats, non-empty discovery nodes, non-empty shard routing, and page
  tokens.

The nodes-info boundary covers:

- OpenSearch `NodesInfoRequest` parent task, node ids, optional timeout, and
  requested metric names at the wire decode/build layer;
- implemented local-node `cluster:monitor/nodes/info` request admission for the
  default all-node, default-metric subset, backed by the daemon transport
  response path that renders local node identity, version/build, process, and
  role metadata through the Java-compatible response fixture builder;
- explicit rejection for concrete node payloads, node filters, timeout, and
  non-default requested metrics.

The nodes-stats boundary covers:

- OpenSearch `NodesStatsRequest` parent task, node ids, optional timeout,
  `CommonStatsFlags`, and requested metric names at the wire decode/build
  layer;
- implemented local-node `cluster:monitor/nodes/stats` request admission for the
  default all-node, all-stats subset, backed by the daemon transport response
  path that renders an empty Java-compatible nodes-stats response with local
  node identity;
- explicit rejection for concrete node payloads, node filters, timeout,
  non-default index stats flags, and requested metric selection.

The nodes-usage boundary covers:

- OpenSearch `NodesUsageRequest` parent task, node ids, optional timeout,
  `restActions`, and `aggregations` flags at the wire decode/build layer;
- implemented `cluster:monitor/nodes/usage` default local-node response
  rendering with empty REST-action and aggregation telemetry maps;
- explicit rejection for concrete node payloads, node filters, timeout,
  `restActions`, `aggregations`, and nodes-usage execution.

The wlm-stats boundary covers:

- OpenSearch `WlmStatsRequest` parent task, node ids, optional timeout,
  workload group id array, and optional breach flag at the wire decode/build
  layer;
- OpenSearch `WlmStatsResponse` cluster name, one local node entry with an
  empty workload-group stats map, and node failure array at the wire
  decode/build layer;
- implemented `cluster:monitor/wlm/stats` request admission and local empty
  workload-group response rendering;
- explicit rejection for concrete node payloads, node filters, timeout,
  workload group filters, and breach filters.

The remote-store-stats boundary covers:

- OpenSearch `RemoteStoreStatsRequest` parent task, broadcast indices array,
  indices options, shard id array, and local flag at the wire decode/build
  layer;
- OpenSearch `RemoteStoreStatsResponse` broadcast counters plus empty
  `RemoteStoreStats[]` rendering for the no-remote-store-shards subset;
- explicit rejection for index filters, non-default indices options, shard
  filters, local-only execution, shard failures, and non-empty remote store
  shard stats.

The remote-store-metadata boundary covers:

- OpenSearch `RemoteStoreMetadataRequest` parent task, broadcast indices array,
  indices options, and shard id array at the wire decode/build layer;
- OpenSearch `RemoteStoreMetadataResponse` broadcast counters plus empty
  `RemoteStoreShardMetadata[]` rendering for the no-remote-store-shards
  subset;
- explicit rejection for index filters, non-default indices options, shard
  filters, shard failures, and non-empty remote store shard metadata.

The nodes-hot-threads boundary covers:

- OpenSearch `NodesHotThreadsRequest` parent task, node ids, optional timeout,
  thread count, idle-thread inclusion flag, sampling type, interval, and
  snapshot count at the wire decode/build layer;
- implemented classification for `cluster:monitor/nodes/hot_threads` default
  local-node requests, returning an OpenSearch-shaped BaseNodesResponse with
  local diagnostic text;
- explicit rejection for concrete node payloads, node filters, timeout, custom
  thread count, idle-thread inclusion, non-CPU sampling type, custom interval,
  and custom snapshot count.

The add-voting-config-exclusions boundary covers:

- OpenSearch `AddVotingConfigExclusionsRequest` parent task,
  cluster-manager timeout, node-description selector array, node-id selector
  array, node-name selector array, and wait timeout at the wire decode/build
  layer;
- OpenSearch `AddVotingConfigExclusionsResponse` empty `ActionResponse`
  rendering after mutating local transport coordination exclusions for the
  default `node_names` selector subset;
- explicit rejection for custom cluster-manager timeout, custom wait timeout,
  missing selector, multiple selectors, deprecated node-description selectors,
  and node-id selectors.

The clear-voting-config-exclusions boundary covers:

- OpenSearch `ClearVotingConfigExclusionsRequest` parent task,
  cluster-manager timeout, `waitForRemoval` flag, and wait timeout at the wire
  decode/build layer;
- OpenSearch `ClearVotingConfigExclusionsResponse` empty `ActionResponse`
  rendering after clearing local transport coordination exclusions for the
  `wait_for_removal=false` subset;
- explicit rejection for custom cluster-manager timeout, wait-for-removal
  convergence tracking, and custom wait timeout.

The cluster-allocation-explain boundary covers:

- OpenSearch `ClusterAllocationExplainRequest` parent task,
  cluster-manager timeout, optional index, optional shard id, optional primary
  flag, optional current node, include-yes-decisions flag, and include-disk-info
  flag at the wire decode/build layer;
- explicit fail-closed classification for
  `cluster:monitor/allocation/explain` until shard routing allocation decision
  rendering is implemented;
- explicit rejection for custom cluster-manager timeout, partial shard selector,
  include-yes-decisions, include-disk-info, and cluster-allocation-explain
  execution.

The cluster-update-settings boundary covers:

- OpenSearch `ClusterUpdateSettingsRequest` parent task, cluster-manager
  timeout, acknowledgement timeout, transient settings map, and persistent
  settings map at the wire decode/build layer;
- OpenSearch `ClusterUpdateSettingsResponse` acknowledged flag plus transient
  and persistent settings maps at the wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/settings/update` until
  cluster-manager update, acknowledgement, and publication semantics are mapped
  for transport mutation;
- explicit rejection for custom cluster-manager timeout, custom acknowledgement
  timeout, transient settings, persistent settings, and update-settings
  execution.

The cluster-reroute boundary covers:

- OpenSearch `ClusterRerouteRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, empty allocation command set, `dryRun`, `explain`,
  and `retryFailed` flags at the wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/reroute` until
  allocation command decoding, routing mutation, acknowledgement, and response
  rendering are implemented;
- explicit rejection for non-empty allocation commands, custom
  cluster-manager timeout, custom acknowledgement timeout, dry-run execution,
  explanation rendering, retry-failed execution, and reroute execution.

The prune-file-cache boundary covers:

- OpenSearch `PruneFileCacheRequest` parent task, node id selector array,
  optional concrete node payload marker, and optional timeout at the wire
  decode/build layer;
- explicit fail-closed classification for `cluster:admin/filecache/prune`
  until warm-node file cache pruning, node response collection, and aggregate
  response rendering are implemented;
- explicit rejection for concrete node payloads, node filters, timeout, and
  prune-file-cache execution.

The reload-secure-settings boundary covers:

- OpenSearch `NodesReloadSecureSettingsRequest` parent task, nullable node id
  selector array, concrete node payload marker, optional timeout, and optional
  secure-settings password bytes at the wire decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/nodes/reload_secure_settings` until keystore reload,
  transport TLS password safety, reloadable extension hooks, node response
  collection, and aggregate response rendering are implemented;
- explicit rejection for concrete node payloads, node filters, timeout,
  password payloads, and reload-secure-settings execution.

The put-repository boundary covers:

- OpenSearch `PutRepositoryRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, repository name, repository type, repository
  settings map, verify flag, and optional crypto settings at the wire
  decode/build layer;
- explicit fail-closed classification for `cluster:admin/repository/put` until
  repository metadata mutation, repository verification, and acknowledgement
  response rendering are implemented;
- explicit rejection for custom cluster-manager timeout, custom acknowledgement
  timeout, blank name, blank type, settings payloads, disabled verification,
  crypto settings, and put-repository execution.

The get-repositories boundary covers:

- OpenSearch `GetRepositoriesRequest` parent task, cluster-manager timeout, and
  `local` flag, and repository name/pattern array at the wire decode/build
  layer;
- implemented `cluster:admin/repository/get` response rendering for the default
  all-repositories request when the repository metadata list is empty;
- explicit rejection for custom cluster-manager timeout, repository name/pattern
  selection, and local reads until repository metadata mapping is implemented.

The delete-repository boundary covers:

- OpenSearch `DeleteRepositoryRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, and repository name at the wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/repository/delete`
  until repository metadata mutation and acknowledgement response rendering are
  implemented;
- explicit rejection for custom cluster-manager timeout, custom acknowledgement
  timeout, blank name, and delete-repository execution.

The verify-repository boundary covers:

- OpenSearch `VerifyRepositoryRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, and repository name at the wire decode/build layer;
- OpenSearch `VerifyRepositoryResponse` node-view list at the wire
  decode/build layer, including the per-node id and name fields;
- explicit fail-closed classification for `cluster:admin/repository/verify`
  until repository verification and node response rendering are implemented;
- explicit rejection for custom cluster-manager timeout, custom acknowledgement
  timeout, blank name, and verify-repository execution.

The cleanup-repository boundary covers:

- OpenSearch `CleanupRepositoryRequest` repository name at the wire
  decode/build layer. The OpenSearch 3.7 request stream constructor and
  `writeTo` implementation only read and write the repository string, despite
  the request type extending `AcknowledgedRequest`;
- OpenSearch `CleanupRepositoryResponse` cleanup result counters at the wire
  decode/build layer, preserving the `RepositoryCleanupResult` stream order of
  deleted bytes followed by deleted blobs;
- explicit fail-closed classification for `cluster:admin/repository/_cleanup`
  until repository cleanup state coordination and cleanup result rendering are
  implemented;
- explicit rejection for blank repository names and cleanup-repository
  execution.

The get-snapshots boundary covers:

- OpenSearch `GetSnapshotsRequest` parent task, cluster-manager timeout,
  repository name, snapshot selector array, `ignoreUnavailable`, and `verbose`
  flags at the wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/snapshot/get` until
  repository snapshot metadata resolution, current snapshot resolution, and
  snapshot response rendering are implemented;
- explicit rejection for custom cluster-manager timeout, blank repository names,
  snapshot selectors, `ignoreUnavailable`, non-verbose response mode, and
  get-snapshots execution.

The delete-snapshot boundary covers:

- OpenSearch `DeleteSnapshotRequest` parent task, cluster-manager timeout,
  repository name, and snapshot name array at the wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/snapshot/delete`
  until snapshot deletion coordination and acknowledgement rendering are
  implemented;
- explicit rejection for custom cluster-manager timeout, blank repository names,
  empty or blank snapshot names, and delete-snapshot execution.

The create-snapshot boundary covers:

- OpenSearch `CreateSnapshotRequest` parent task, cluster-manager timeout,
  snapshot name, repository name, index selector array,
  `IndicesOptions.strictExpandOpenHidden()` wire flags, settings map,
  `includeGlobalState`, `waitForCompletion`, `partial`, and generic user
  metadata presence at the wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/snapshot/create`
  until snapshot creation coordination and create-snapshot response rendering
  are implemented;
- explicit rejection for custom cluster-manager timeout, blank snapshot names,
  blank repository names, index selectors, custom indices options, custom
  settings, disabled global state, wait-for-completion, partial snapshots,
  user metadata, and create-snapshot execution.

The clone-snapshot boundary covers:

- OpenSearch `CloneSnapshotRequest` parent task, cluster-manager timeout,
  repository name, source snapshot name, target snapshot name, index selector
  array, and `IndicesOptions.strictExpandHidden()` wire flags at the wire
  decode/build layer;
- explicit fail-closed classification for `cluster:admin/snapshot/clone` until
  snapshot clone coordination and acknowledgement rendering are implemented;
- explicit rejection for custom cluster-manager timeout, blank repository
  names, blank source snapshot names, blank target snapshot names, empty or
  blank index selectors, custom indices options, and clone-snapshot execution.

The restore-snapshot boundary covers:

- OpenSearch 3.7 `RestoreSnapshotRequest` parent task, cluster-manager timeout,
  snapshot name, repository name, index selector array,
  `IndicesOptions.strictExpandOpen()` wire flags, index and alias rename
  options, wait/global-state/partial/alias flags, index settings,
  ignored-index-settings, snapshot UUID, storage type, source remote
  repositories, and alias write-index policy at the wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/snapshot/restore`
  until snapshot restore coordination and restore response rendering are
  implemented;
- explicit rejection for custom cluster-manager timeout, blank snapshot or
  repository names, blank index selectors, custom indices options, index or
  alias rename rules, wait-for-completion, global-state restore, partial
  restore, alias exclusion, index setting overrides, ignored index settings,
  snapshot UUID pinning, remote snapshot storage, source remote repositories,
  alias write-index policy changes, and restore-snapshot execution.

The restore-remote-store boundary covers:

- OpenSearch 3.7 `RestoreRemoteStoreRequest` parent task, cluster-manager
  timeout, index selector array, optional `waitForCompletion`, and optional
  `restoreAllShards` flags at the wire decode/build layer;
- OpenSearch `RestoreRemoteStoreResponse` accepted-only response subset where
  `RestoreInfo` is absent;
- explicit fail-closed classification for
  `cluster:admin/remotestore/restore` until remote-store restore service
  coordination, shard restore planning, completion listener, `RestoreInfo`
  decoding, and response rendering are implemented;
- explicit rejection for custom cluster-manager timeout, missing or blank
  index selectors, `waitForCompletion`, `restoreAllShards`, completed
  `RestoreInfo` payloads, restore-remote-store execution, and response
  rendering.

The extension-proxy boundary covers:

- OpenSearch `ExtensionActionRequest` parent task plus length-prefixed
  serialized `ExtensionTransportMessage` protobuf payload at the wire
  decode/build layer;
- OpenSearch `ExtensionActionResponse` length-prefixed raw response bytes at
  the wire decode/build layer;
- explicit fail-closed classification for `cluster:internal/extensions` until
  extension manager routing, protobuf `ExtensionTransportMessage` parsing,
  extension transport dispatch, and byte response rendering are implemented;
- explicit rejection for empty or oversized extension request payloads,
  oversized response payloads, extension-proxy execution, and response
  rendering.

The decommission boundary covers:

- OpenSearch `DecommissionRequest` parent task, cluster-manager timeout,
  `DecommissionAttribute` awareness attribute name/value, decommission delay
  timeout, `noDelay`, and optional request id at the wire decode/build layer;
- OpenSearch `DecommissionResponse` acknowledged response payload at the wire
  decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/decommission/awareness/put` until decommission metadata
  mutation, node draining coordination, cluster-state publication, and
  acknowledgement rendering are implemented;
- explicit rejection for custom cluster-manager timeout, missing awareness
  attribute name/value, invalid `noDelay` timeout pairing, custom delay
  timeout, and decommission execution.

The get-decommission-state boundary covers:

- OpenSearch `GetDecommissionStateRequest` parent task, cluster-manager
  timeout, read-local flag, and awareness attribute name at the wire
  decode/build layer;
- OpenSearch `GetDecommissionStateResponse` presence flag plus optional
  awareness attribute value and decommission status string at the wire
  decode/build layer;
- manifest-backed transport execution for OpenSearch
  `decommissionedAttribute` metadata under `/metadata/customs` and the Rust
  `/cluster_admin_state` metadata aliases, returning a present state only when
  the request attribute name matches the stored decommission attribute;
- supported local and cluster-manager reads for the manifest-backed subset;
- explicit rejection for invalid cluster-manager timeout values, missing
  awareness attribute name, and unknown decommission status strings.

The delete-decommission-state boundary covers:

- OpenSearch `DeleteDecommissionStateRequest` parent task and cluster-manager
  timeout at the wire decode/build layer;
- OpenSearch `DeleteDecommissionStateResponse` acknowledged response payload
  at the wire decode/build layer;
- manifest-backed transport execution for
  `cluster:admin/decommission/awareness/delete`, clearing OpenSearch
  `decommissionedAttribute` metadata aliases and the Rust
  `/cluster_admin_state/decommission_awareness` entry before returning an
  acknowledged response;
- explicit rejection for custom cluster-manager timeout values.

The put-search-pipeline boundary covers:

- OpenSearch `PutSearchPipelineRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, pipeline id, length-prefixed source bytes, and
  media type at the wire decode/build layer;
- OpenSearch `AcknowledgedResponse` payload at the wire decode/build layer;
- manifest-backed transport execution for
  `cluster:admin/search/pipeline/put`, storing JSON search pipeline metadata in
  the Rust metadata manifest before returning an acknowledged response;
- explicit rejection for custom cluster-manager timeout, custom
  acknowledgement timeout, missing pipeline id, empty or oversized pipeline
  source, and unsupported media types.

The get-search-pipeline boundary covers:

- OpenSearch `GetSearchPipelineRequest` parent task, cluster-manager timeout,
  local flag, and pipeline ids at the wire decode/build layer;
- OpenSearch `GetSearchPipelineResponse` pipeline count and repeated search
  `PipelineConfiguration` id, config bytes, and media type at the wire
  decode/build layer;
- implemented manifest-backed `cluster:admin/search/pipeline/get` response
  rendering for all ids, explicit ids, and simple wildcard id selectors;
- explicit rejection for custom cluster-manager timeout, local cluster-state
  reads, blank pipeline id selectors, unknown response media types, and
  negative response pipeline counts.

The delete-search-pipeline boundary covers:

- OpenSearch `DeleteSearchPipelineRequest` parent task, cluster-manager
  timeout, acknowledgement timeout, and pipeline id at the wire decode/build
  layer;
- OpenSearch `AcknowledgedResponse` payload at the wire decode/build layer;
- manifest-backed transport execution for
  `cluster:admin/search/pipeline/delete`, deleting exact or wildcard-matched
  Rust manifest `search_pipelines` entries and returning an acknowledged
  response;
- explicit rejection for custom cluster-manager timeout, custom
  acknowledgement timeout, missing pipeline id, and explicit missing-pipeline
  requests that require OpenSearch `ResourceNotFoundException` rendering.

The pause-ingestion boundary covers:

- OpenSearch `PauseIngestionRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, index selector array, and strict-expand-open
  `IndicesOptions` at the wire decode/build layer;
- OpenSearch `PauseIngestionResponse` acknowledgement bit, shard failure array,
  error string, and shard acknowledgement bit at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/ingestion/pause`
  until destructive-index guard checks, index resolution, ingestion poller
  state mutation, shard acknowledgement aggregation, and response rendering are
  implemented;
- explicit rejection for custom cluster-manager timeout, custom
  acknowledgement timeout, missing indices, blank index selectors, custom
  index resolution options, pause-ingestion execution, response shard failure
  rendering, response error rendering, negative failure counts, and negative
  shard ids.

The resume-ingestion boundary covers:

- OpenSearch `ResumeIngestionRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, index selector array, strict-expand-open
  `IndicesOptions`, and reset-settings array at the wire decode/build layer;
- OpenSearch reset-settings entries as shard `vInt`, reset mode enum ordinal
  (`OFFSET` or `TIMESTAMP`), and value string;
- OpenSearch `ResumeIngestionResponse` acknowledgement bit, shard failure
  array, error string, and shard acknowledgement bit at the wire decode/build
  layer;
- explicit fail-closed classification for `indices:admin/ingestion/resume`
  until destructive-index guard checks, index resolution, optional shard pointer
  reset, ingestion poller state mutation, shard acknowledgement aggregation,
  and response rendering are implemented;
- explicit rejection for custom cluster-manager timeout, custom
  acknowledgement timeout, missing indices, blank index selectors, custom
  index resolution options, invalid reset settings, resume-ingestion execution,
  reset execution, response shard failure rendering, response error rendering,
  negative failure counts, and negative shard ids.

The get-ingestion-state boundary covers:

- OpenSearch `GetIngestionStateRequest` broadcast parent task, nullable index
  selector array encoded as a string-array count, strict-expand-open-and-forbid
  closed `IndicesOptions`, shard `vInt` array, optional `PageParams`, and
  pagination `(index, shard)` pair list at the wire decode/build layer;
- OpenSearch `PageParams` requested token, optional sort value, and page size;
- OpenSearch `GetIngestionStateResponse` broadcast shard counters, zero shard
  failure count, shard ingestion-state array, and optional next-page token at
  the wire decode/build layer;
- OpenSearch shard ingestion state fields for index, shard id, optional poller
  state, optional error policy, poller paused flag, write-block flag, batch start
  pointer, primary flag, and node name for the OpenSearch 3.7 transport version;
- explicit fail-closed classification for `indices:monitor/ingestion/state`
  until broadcast shard selection, optional pagination, shard ingestion-state
  collection, shard failure aggregation, and response rendering are implemented;
- explicit rejection for duplicate indices, blank index selectors, custom index
  resolution options, invalid shard ids, invalid page params, paginated execution
  pair filters, non-empty shard states, next-page token rendering, shard failure
  rendering, negative failure counts, and negative state counts.

The update-ingestion-state boundary covers:

- OpenSearch `UpdateIngestionStateRequest` broadcast parent task, broadcast
  index selector array encoded as a string-array count, strict-expand-open-and
  forbid-closed `IndicesOptions`, target index array, shard `vInt` array,
  optional paused-state boolean, and optional reset-settings array at the wire
  decode/build layer;
- OpenSearch reset-settings entries as shard `vInt`, reset mode enum ordinal
  (`OFFSET` or `TIMESTAMP`), and value string, reusing the resume-ingestion reset
  wire shape;
- OpenSearch `UpdateIngestionStateResponse` broadcast shard counters, zero
  broadcast shard failure count, acknowledgement bit, error string, and
  ingestion shard failure array at the wire decode/build layer;
- explicit fail-closed classification for
  `indices:admin/ingestion/updateState` until broadcast shard selection,
  metadata write block checks, shard pointer reset, ingestion paused-state
  mutation, shard failure aggregation, and response rendering are implemented;
- explicit rejection for missing broadcast indices, missing target indices,
  blank index selectors, custom index resolution options, invalid shard ids,
  missing mutation targets, invalid reset settings, reset execution, update
  execution, response broadcast failure rendering, response error rendering,
  response shard failure rendering, and negative failure counts.

The list-tiering-status boundary covers:

- OpenSearch `ListTieringStatusRequest` cluster-manager read parent task,
  cluster-manager timeout, local flag, and optional target tier string at the
  wire decode/build layer;
- OpenSearch `ListTieringStatusResponse` tiering status count and per-status
  base fields for index name, state, source tier, target tier, start time, and
  optional shard-level status marker at the wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/_tier/all` until
  metadata read block checks, target tier mapping, migration service lookup,
  tiering status aggregation, and response rendering are implemented;
- explicit rejection for custom cluster-manager timeout, local reads, invalid
  target tier values, non-empty tiering status response rendering, blank status
  index names, shard-level status rendering, and negative response counts.

The get-tiering-status boundary covers:

- OpenSearch `GetTieringStatusRequest` cluster-manager read parent task,
  cluster-manager timeout, local flag, index name, and detailed flag at the
  wire decode/build layer;
- OpenSearch `GetTieringStatusResponse` single `TieringStatus` base fields for
  index name, state, source tier, target tier, start time, and optional
  shard-level status marker at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/_tier/get` until
  metadata read block checks, index resolution, tiering-state lookup, migration
  service lookup, optional shard-level detail collection, and response rendering
  are implemented;
- explicit rejection for custom cluster-manager timeout, local reads, blank
  index names, get-tiering-status execution, single-status response rendering,
  blank response index names, and shard-level status rendering.

The knn-stats boundary covers:

- OpenSearch k-NN `KNNStatsRequest` `BaseNodesRequest` parent task, nullable
  node id selectors, concrete-node marker, optional timeout, valid stat name
  set, and requested stat name set at the wire decode/build layer;
- OpenSearch k-NN `KNNStatsResponse` cluster name, empty node response list,
  empty node failure list, and empty generic cluster-stats map at the wire
  decode/build layer;
- explicit fail-closed classification for `cluster:admin/knn_stats_action`
  until BaseNodes fanout, stat selection validation, node-level KNN stat
  collection, cluster-level KNN stat aggregation, failure aggregation, and
  response rendering are implemented;
- explicit rejection for node filters, concrete node payloads, custom timeout,
  blank stat names, unknown requested stat names, KNN stats execution, node
  response rendering, node failure rendering, cluster stat rendering, and
  response rendering.

The knn-warmup boundary covers:

- OpenSearch k-NN `KNNWarmupRequest` `BroadcastRequest` parent task, nullable
  index selector array, and strict-expand-open-forbid-closed `IndicesOptions`
  at the wire decode/build layer;
- OpenSearch k-NN `KNNWarmupResponse` broadcast shard counters and zero shard
  failure count at the wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/knn_warmup_action`
  until broadcast shard selection, metadata read block checks, per-shard KNN
  warmup, shard failure aggregation, and response rendering are implemented;
- explicit rejection for missing indices, blank index selectors, custom index
  resolution options, KNN warmup execution, negative shard counters, shard
  failure rendering, and response rendering.

The update-model-metadata boundary covers:

- OpenSearch k-NN `UpdateModelMetadataRequest` acknowledged cluster-manager
  write parent task, cluster-manager timeout, acknowledgement timeout, model id,
  remove flag, and opaque model-metadata body presence at the wire decode/build
  layer;
- OpenSearch `AcknowledgedResponse` acknowledgement bit at the wire
  decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/knn_update_model_metadata_action` until model metadata
  validation, model system-index custom metadata mutation, cluster-state
  publication, and acknowledgement rendering are implemented;
- explicit rejection for custom cluster-manager timeout, custom acknowledgement
  timeout, blank model ids, add requests without metadata, model metadata body
  parsing/rendering, and update-model-metadata execution.

The training-job-route-decision-info boundary covers:

- OpenSearch k-NN `TrainingJobRouteDecisionInfoRequest` BaseNodes parent task,
  nullable node id selector, concrete-node marker rejection, and optional
  timeout at the wire decode/build layer;
- OpenSearch k-NN `TrainingJobRouteDecisionInfoResponse` cluster name and empty
  BaseNodes nodes/failures lists at the wire decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/knn_training_job_route_decision_info_action` until BaseNodes
  fanout, node-level training job count collection, failure aggregation, and
  response rendering are implemented;
- explicit rejection for concrete node payloads, node filters, timeouts, node
  response payloads, node failures, blank cluster names, response rendering,
  and training-job-route-decision-info execution.

The get-model boundary covers:

- OpenSearch k-NN `GetModelRequest` parent task and model id at the wire
  decode/build layer;
- OpenSearch k-NN `GetModelResponse` model payload presence at the wire
  decode/build layer while treating the full `Model` body as opaque;
- explicit fail-closed classification for `cluster:admin/knn_get_model_action`
  until model system-index lookup, KNN `ModelMetadata` parsing, optional model
  blob handling, model id rendering, and response rendering are implemented;
- explicit rejection for missing model response payloads, opaque model response
  rendering, and get-model execution.

The delete-model boundary covers:

- OpenSearch k-NN `DeleteModelRequest` parent task and model id at the wire
  decode/build layer;
- OpenSearch k-NN `DeleteModelResponse` model id, result, and optional error
  message at the wire decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/knn_delete_model_action` until model id validation, model
  system-index delete, model cache/graveyard coordination, exception-path
  behavior, and response rendering are implemented;
- explicit rejection for blank model ids, blank response model ids, blank
  response results, deprecated embedded error-message responses, response
  rendering, and delete-model execution.

The training-job-router boundary covers:

- OpenSearch k-NN `TrainingModelRequest` parent task, optional model id, and
  opaque training request payload presence at the wire decode/build layer;
- OpenSearch k-NN `TrainingModelResponse` optional model id at the wire
  decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/knn_training_job_router_action` until training index sizing,
  training config validation, route-decision fanout, node selection, forwarding
  to `TrainingModelAction`, and response rendering are implemented;
- explicit rejection for missing training request payloads, blank response model
  ids, response rendering, and training-job-router execution.

The training-model boundary covers:

- OpenSearch k-NN `TrainingModelRequest` parent task, optional model id, and
  opaque training request payload presence at the wire decode/build layer;
- OpenSearch k-NN `TrainingModelResponse` optional model id at the wire
  decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/knn_training_model_action` until KNN native training data
  loading, memory reservation, training job execution, model system-index
  write, counter updates, and response rendering are implemented;
- explicit rejection for missing training request payloads, blank response model
  ids, response rendering, and training-model execution.

The remove-model-from-cache boundary covers:

- OpenSearch k-NN `RemoveModelFromCacheRequest` parent task, nullable node id
  selectors, optional timeout, and model id at the wire decode/build layer;
- OpenSearch k-NN `RemoveModelFromCacheResponse` cluster name with empty node
  responses and empty node failures at the wire decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/knn_remove_model_from_cache_action` until BaseNodes fanout,
  per-node model cache eviction, failure aggregation, and response rendering
  are implemented;
- explicit rejection for blank model ids, node-scoped routing, timeout
  semantics, non-empty node responses, non-empty node failures, blank response
  cluster names, response rendering, and remove-model-from-cache execution.

The search-model boundary covers:

- OpenSearch k-NN `SearchModelAction` request frames carrying OpenSearch core
  `SearchRequest` at the wire decode/build layer;
- OpenSearch k-NN `SearchModelAction` response frames carrying opaque
  `SearchResponse` payload presence at the wire decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/knn_search_model_action` until model system-index search
  request mapping, `SearchRequest` source parsing, `ModelDao` search
  delegation, `SearchResponse` decoding, and response rendering are
  implemented;
- explicit rejection for unsupported search request shapes, opaque
  `SearchResponse` payloads, response rendering, and search-model execution.

The update-model-graveyard boundary covers:

- OpenSearch k-NN `UpdateModelGraveyardRequest` parent task,
  cluster-manager timeout, acknowledgement timeout, model id, and remove flag
  at the wire decode/build layer;
- OpenSearch `AcknowledgedResponse` acknowledgement flag at the wire
  decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/knn_update_model_graveyard_action` until cluster-manager
  state update submission, model graveyard metadata mutation, model usage
  mapping scan, delete-model conflict handling, cluster-state publication, and
  acknowledgement rendering are implemented;
- explicit rejection for custom cluster-manager timeout, custom acknowledgement
  timeout, blank model ids, and update-model-graveyard execution.

The clear-cache boundary covers:

- OpenSearch k-NN `ClearCacheRequest` parent task, index selectors, and index
  resolution options at the wire decode/build layer;
- OpenSearch k-NN `ClearCacheResponse` total, successful, failed shard
  counters, and empty shard failure list at the wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/clear_cache_action`
  until index resolution, KNN index validation, broadcast shard selection,
  per-shard KNN cache eviction, shard failure aggregation, and response
  rendering are implemented;
- explicit rejection for missing indices, blank indices, custom index
  resolution options, non-empty shard failures, response failure rendering, and
  clear-cache execution.

The snapshots-status boundary covers:

- OpenSearch 3.7 `SnapshotsStatusRequest` parent task, cluster-manager
  timeout, repository name, snapshot selector array, `ignoreUnavailable`, and
  optional index selector array at the wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/snapshot/status`
  until current snapshot status, repository snapshot status, node shard status,
  and response rendering are implemented;
- explicit rejection for custom cluster-manager timeout, blank repository
  names, blank snapshot selectors, snapshot selectors, `ignoreUnavailable`,
  blank index selectors, index selectors, and snapshots-status execution.

The add-weighted-routing boundary covers:

- OpenSearch 3.7 `ClusterPutWeightedRoutingRequest` parent task,
  cluster-manager timeout, `WeightedRouting` awareness attribute name,
  generic string-to-double weights map, and weighted routing version at the
  wire decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/routing/awareness/weights/put` until weighted routing
  metadata mutation, awareness attribute verification, version conflict
  handling, cluster-state publication, and acknowledgement rendering are
  implemented;
- explicit rejection for custom cluster-manager timeout, missing awareness
  attribute names, missing weights, missing versions, non-finite weights,
  too many zero weights, non-double generic weight values, and
  add-weighted-routing execution.

The get-weighted-routing boundary covers:

- OpenSearch 3.7 `ClusterGetWeightedRoutingRequest` parent task,
  cluster-manager timeout, `local` read flag, and awareness attribute name at
  the wire decode/build layer;
- manifest-backed transport execution for
  `cluster:admin/routing/awareness/weights/get`, rendering the stored weighted
  routing metadata, version, and discovered-cluster-manager flag in the
  OpenSearch response shape;
- explicit rejection for unsupported timeout/local-read shapes and missing
  awareness attribute names.

The delete-weighted-routing boundary covers:

- OpenSearch 3.7 `ClusterDeleteWeightedRoutingRequest` parent task,
  cluster-manager timeout, weighted routing version, and optional trailing
  awareness attribute string at the wire decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/routing/awareness/weights/delete` until weighted routing
  metadata deletion, version conflict handling, cluster-state publication, and
  acknowledgement rendering are implemented;
- explicit rejection for custom cluster-manager timeout, missing versions,
  absent or blank awareness attribute names, and delete-weighted-routing
  execution.

The get-mappings boundary covers:

- OpenSearch `GetMappingsRequest` parent task, cluster-manager timeout, indices
  array, `local` flag, and `IndicesOptions.strictExpandOpen()` at the wire
  decode/build layer;
- implemented classification for `indices:admin/mappings/get` default
  all-indices request admission and local metadata manifest-backed empty
  mapping entry response rendering;
- explicit rejection for custom cluster-manager timeout, index filters, local
  reads, custom indices options, and non-empty mapping metadata payloads.

The get-field-mappings boundary covers:

- OpenSearch `GetFieldMappingsRequest` parent task, indices array,
  `IndicesOptions.strictExpandOpen()`, `local`, fields array, and
  `includeDefaults` at the OpenSearch 3.x wire decode/build layer;
- implemented classification for `indices:admin/mappings/fields/get` default
  all-indices/no-fields request admission and local metadata manifest-backed
  empty field-mapping entry response rendering;
- explicit rejection for index filters, custom indices options, local reads,
  field filters, include-default expansion, and non-empty field mapping
  metadata payloads.

The put-mapping boundary covers:

- OpenSearch `PutMappingRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, indices array, `IndicesOptions.fromOptions(false,
  false, true, true)`, mapping source string, optional concrete `Index`,
  optional origin, and `writeIndexOnly` at the OpenSearch 3.x wire decode/build
  layer;
- implemented classification for `indices:admin/mapping/put` when the request
  uses default timeouts/options, unresolved manifest-backed index targets,
  non-empty JSON mapping source, empty origin, no concrete-index override, and
  `writeIndexOnly=false`;
- metadata mutation for the supported `dynamic`, `_meta`, and `properties`
  subset, including `_meta` null removal and field type-conflict admission
  checks before acknowledged response rendering;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing index targets, custom indices options,
  empty mapping sources, concrete-index routing, custom origins,
  write-index-only updates, missing index matches, invalid JSON mapping
  sources, empty mapping subset, and field type changes.

The auto-put-mapping boundary covers:

- OpenSearch `PutMappingRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, absent unresolved indices, default put-mapping
  indices options, mapping source string, required concrete `Index`, optional
  origin, and `writeIndexOnly` at the OpenSearch 3.x wire decode/build layer;
- implemented classification for `indices:admin/mapping/auto_put` when the
  request uses the default dynamic mapping update timeout, OpenSearch's zero
  acknowledgement timeout, no unresolved indices, a concrete index that exists
  in the local manifest, default put-mapping indices options, a supported
  mapping source, empty origin, and `writeIndexOnly=false`;
- manifest-backed concrete-index mapping validation and metadata mutation using
  the same supported mapping merge path as put-mapping, plus OpenSearch
  acknowledged-response wire rendering;
- explicit rejection for custom cluster-manager timeouts, non-zero
  acknowledgement timeouts, missing concrete indices, unresolved indices,
  custom indices options, empty or unsupported mapping sources, custom origins,
  write-index-only updates, unknown concrete indices, and incompatible field
  type updates.

The indices-aliases boundary covers:

- OpenSearch `IndicesAliasesRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, alias action list, optional origin, and
  `AliasActions` add/remove/remove-index ordinals, indices array, aliases
  array, optional filter, routing fields, optional write-index flag, optional
  hidden flag, original aliases array, and optional must-exist flag at the
  OpenSearch 3.x wire decode/build layer;
- implemented classification for `indices:admin/aliases` when the request uses
  default timeouts, no custom origin, manifest-backed concrete, `_all`, or
  wildcard index targets, and add/remove alias actions without alias metadata
  options;
- manifest-backed alias metadata mutation for supported add/remove actions and
  OpenSearch acknowledged-response wire rendering;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, empty action lists, custom origins, unknown alias
  action ordinals, missing or unresolved index targets, missing alias targets,
  remove-index actions, filtered aliases, alias routing, write-index updates,
  hidden alias updates, and must-exist removals.

The index update-settings boundary covers:

- OpenSearch `UpdateSettingsRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, nullable indices array encoded as an OpenSearch
  string array, `IndicesOptions.fromOptions(false, false, true, true)`,
  string-valued Settings generic map, and `preserveExisting` at the OpenSearch
  3.x wire decode/build layer;
- implemented classification for `indices:admin/settings/update` when the
  request uses the default timeouts/options, concrete or wildcard manifest
  indices, non-empty `index.*` string settings, and `preserveExisting=false`;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing index targets, custom indices options,
  empty settings maps, non-index setting keys, non-string generic setting
  values, and preserve-existing updates.

The scale-index boundary covers:

- OpenSearch `ScaleIndexRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, target index, `scaleDown`, and
  `IndicesOptions.strictExpandOpen()` at the OpenSearch 3.x wire decode/build
  layer;
- implemented classification for `indices:admin/scale/search_only` when the
  request uses default timeouts/options, a concrete existing manifest index,
  and `scaleDown=true`;
- manifest-backed `index.blocks.search_only=true` mutation and OpenSearch
  acknowledged response rendering for the supported scale-down subset;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing index targets, custom indices options,
  wildcard/date-math/comma/remote-style targets, missing manifest indices, and
  scale-up transitions.

The analyze boundary covers:

- OpenSearch `AnalyzeAction.Request` parent task, absent internal shard id,
  optional index, text array, optional analyzer, optional tokenizer
  `NameOrDefinition`, token filter list, char filter list, optional field,
  `explain`, attributes array, and optional normalizer at the OpenSearch 3.x
  wire decode/build layer;
- implemented local execution classification for `indices:admin/analyze` when
  the request has no internal shard id, an absent or manifest-backed concrete
  index, non-empty text, no field or normalizer, no custom tokenizer/token
  filters/char filters, absent or `standard` analyzer, `explain=false`, and no
  requested attributes;
- OpenSearch-shaped response rendering for the bounded token-array subset,
  including term, offsets, position, optional token type, and an empty attribute
  map per token;
- explicit rejection for internal shard-id payloads, missing text, normalizers
  without indices, invalid normalizer/analyzer/field component combinations,
  custom analyzer components, non-standard analyzers, field-backed analyzer
  lookup, explain/detail responses, and attribute-filtered responses.

The create-index boundary covers:

- OpenSearch `CreateIndexRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, cause, index, string-valued settings map, mappings
  string, alias count, `ActiveShardCount`, and absent context marker at the
  OpenSearch 3.x wire decode/build layer;
- implemented classification for the default request subset with standard
  timeouts, empty cause, a valid concrete index name, empty settings, empty
  mappings, no aliases, default wait-for-active-shards, and no context;
- manifest-backed index metadata mutation plus OpenSearch-shaped
  `CreateIndexResponse` rendering with acknowledgement, shard acknowledgement,
  and index name fields;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing index names, custom cause strings,
  settings, mappings, aliases, custom wait-for-active-shards, context payloads,
  duplicate index names, and invalid index names.

The auto-create boundary covers:

- OpenSearch `CreateIndexRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, cause, target index, string-valued settings map,
  mappings string, alias count, `ActiveShardCount`, and absent context marker at
  the OpenSearch 3.x wire decode/build layer;
- implemented classification for the default request subset with standard
  timeouts, empty cause, a valid concrete target index name, empty settings,
  empty mappings, no aliases, default wait-for-active-shards, and no context;
- manifest-backed index metadata mutation plus OpenSearch-shaped
  `CreateIndexResponse` rendering with acknowledgement, shard acknowledgement,
  and index name fields;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing index names, custom cause strings,
  settings, mappings, aliases, custom wait-for-active-shards, context payloads,
  duplicate index names, and invalid index names.

The put-stored-script boundary covers:

- OpenSearch `PutStoredScriptRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, optional stored script id, content
  `BytesReference`, media type string, optional context, and
  `StoredScriptSource` language/source/options at the OpenSearch 3.x wire
  decode/build layer;
- implemented `cluster:admin/script/put` request admission for the supported
  metadata subset, manifest-backed stored script upsert, and acknowledgement
  response rendering;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing or invalid ids, empty content, non-JSON
  media types, explicit script contexts, missing language/source fields,
  and compiler options.

The get-stored-script boundary covers:

- OpenSearch `GetStoredScriptRequest` parent task, cluster-manager timeout,
  local-read flag, and stored script id at the OpenSearch 3.x wire decode/build
  layer;
- OpenSearch `GetStoredScriptResponse` found marker, optional
  `StoredScriptSource` language/source/options, and id at the OpenSearch 3.x
  response wire decode/build layer;
- implemented `cluster:admin/script/get` request admission and manifest-backed
  found/not-found response rendering for the supported stored-script metadata
  shape;
- explicit rejection for custom cluster-manager timeouts, local reads, missing
  ids, and invalid ids.

The delete-stored-script boundary covers:

- OpenSearch `DeleteStoredScriptRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, and stored script id at the OpenSearch 3.x wire
  decode/build layer;
- implemented `cluster:admin/script/delete` request admission for the supported
  metadata subset, manifest-backed stored script removal, and acknowledgement
  response rendering;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing ids, and invalid ids.

The get-script-context boundary covers:

- OpenSearch `GetScriptContextRequest` parent task at the OpenSearch 3.x wire
  decode/build layer;
- OpenSearch `GetScriptContextResponse` context count and `ScriptContextInfo`
  name, execute method, getter methods, and method parameter metadata at the
  wire decode/build layer;
- implemented local transport adapter rendering for the same Rust-supported
  script context catalog exposed by REST `GET /_script_context`;
- request subset validation for `cluster:admin/script_context/get`;
- defensive decode rejection for negative context, getter, and parameter counts.

The get-script-language boundary covers:

- OpenSearch `GetScriptLanguageRequest` parent task at the OpenSearch 3.x wire
  decode/build layer;
- OpenSearch `GetScriptLanguageResponse` / `ScriptLanguagesInfo`
  `types_allowed` string collection and language-to-contexts string collection
  map at the wire decode/build layer;
- implemented local transport adapter rendering for the same Rust-supported
  script language catalog exposed by REST `GET /_script_language`;
- request subset validation for `cluster:admin/script_language/get`;
- defensive decode rejection for negative type, language, and context counts.

The put-pipeline boundary covers:

- OpenSearch `PutPipelineRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, pipeline id, source bytes, and media type at the
  OpenSearch 3.x wire decode/build layer;
- OpenSearch `AcknowledgedResponse` decode/build for the put-pipeline response
  acknowledgement bit;
- manifest-backed transport execution for
  `cluster:admin/ingest/pipeline/put`, storing JSON pipeline source in Rust
  manifest `ingest_pipelines` entries and returning an acknowledged response;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing ids, missing source bytes, non-JSON media
  types, and malformed JSON source bytes.

The get-pipeline boundary covers:

- OpenSearch `GetPipelineRequest` parent task, cluster-manager timeout, local
  flag, and pipeline ids at the OpenSearch 3.x wire decode/build layer;
- OpenSearch `GetPipelineResponse` pipeline count and repeated
  `PipelineConfiguration` id, config bytes, and media type at the wire
  decode/build layer;
- implemented classification for `cluster:admin/ingest/pipeline/get` with an
  OpenSearch-shaped empty pipeline list response for the default non-local
  metadata read request;
- explicit rejection for custom cluster-manager timeouts and local
  cluster-state reads, plus defensive decode rejection for negative response
  pipeline counts.

The delete-pipeline boundary covers:

- OpenSearch `DeletePipelineRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, and pipeline id at the OpenSearch 3.x wire
  decode/build layer;
- OpenSearch `AcknowledgedResponse` decode/build for the delete-pipeline
  response acknowledgement bit;
- manifest-backed transport execution for
  `cluster:admin/ingest/pipeline/delete`, deleting exact or wildcard-matched
  Rust manifest `ingest_pipelines` entries and returning an acknowledged
  response;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing ids, and explicit missing-pipeline
  deletes.

The simulate-pipeline boundary covers:

- OpenSearch `SimulatePipelineRequest` parent task, optional pipeline id,
  verbose flag, source bytes, and media type at the OpenSearch 3.x wire
  decode/build layer;
- OpenSearch `SimulatePipelineResponse` optional pipeline id, verbose flag,
  and empty result count decode/build, with explicit rejection for non-empty
  document/processor result payloads until those result shapes are modeled;
- empty-doc transport execution for `cluster:admin/ingest/pipeline/simulate`,
  returning an OpenSearch `SimulatePipelineResponse` with zero result entries
  for named manifest pipelines or inline pipeline definitions whose `docs`
  array is empty;
- explicit rejection for missing source bytes, non-JSON media types, malformed
  JSON source bytes, missing named pipelines, inline requests without a
  pipeline object, non-empty docs, and defensive decode rejection for negative
  response result counts.

The resize boundary covers:

- OpenSearch `ResizeRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, nested `CreateIndexRequest`, source index,
  `ResizeType`, `copySettings`, and optional `ByteSizeValue` `maxShardSize` at
  the OpenSearch 3.x wire decode/build layer;
- explicit fail-closed classification for `indices:admin/resize` until source
  index metadata validation, target index metadata mutation, shard allocation,
  and resize response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing source indices, split/clone resize types,
  non-default `copySettings`, `maxShardSize`, unsupported nested target
  create-index shapes, and resize execution.

The rollover boundary covers:

- OpenSearch `RolloverRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, rollover target, optional new index name, `dryRun`,
  zero-condition marker, and nested `CreateIndexRequest` at the OpenSearch 3.x
  wire decode/build layer;
- explicit fail-closed classification for `indices:admin/rollover` until alias
  or data-stream metadata validation, condition evaluation, index creation, and
  rollover response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing rollover targets, dry-run requests,
  condition payloads, unsupported nested create-index shapes, and rollover
  execution.

The delete-index boundary covers:

- OpenSearch `DeleteIndexRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, indices array, and delete-index default
  `IndicesOptions.fromOptions(false, true, true, true, false, false, true,
  false)` at the wire decode/build layer;
- implemented classification for default-option requests with one or more
  concrete index names and standard timeouts;
- manifest-backed index metadata removal plus local development document cleanup
  and OpenSearch-shaped `AcknowledgedResponse` rendering;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, empty or blank index targets, custom indices
  options, wildcard/date-math/comma/remote-style targets, and non-concrete
  target names.

The open-index boundary covers:

- OpenSearch `OpenIndexRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, indices array, `IndicesOptions.fromOptions(false,
  true, false, true)`, and default `ActiveShardCount` at the wire decode/build
  layer;
- implemented classification for default-option requests with one or more
  concrete existing index names and standard timeouts;
- manifest-backed index metadata state transition to `open` plus
  OpenSearch-shaped `OpenIndexResponse` rendering with `acknowledged` and
  `shards_acknowledged`;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, empty or blank index targets, custom indices
  options, custom wait-for-active-shards, wildcard/date-math/comma/remote-style
  targets, missing index names, and non-concrete target names.

The close-index boundary covers:

- OpenSearch `CloseIndexRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, indices array, `IndicesOptions.strictExpandOpen()`,
  and `ActiveShardCount.NONE` at the wire decode/build layer;
- implemented classification for default-option requests with one or more
  concrete existing index names and standard timeouts;
- manifest-backed index metadata state transition to `close` plus
  OpenSearch-shaped `CloseIndexResponse` rendering with `acknowledged`,
  `shards_acknowledged`, and successful per-index results;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, empty or blank index targets, custom indices
  options, custom wait-for-active-shards, wildcard/date-math/comma/remote-style
  targets, missing index names, and non-concrete target names.

The add-index-block boundary covers:

- OpenSearch `AddIndexBlockRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, indices array, `IndicesOptions.strictExpandOpen()`,
  and `IndexMetadata.APIBlock` ordinal at the wire decode/build layer;
- implemented classification for default-option requests with one or more
  concrete existing index names and supported public `IndexMetadata.APIBlock`
  ordinals;
- manifest-backed `index.blocks.*` setting mutation plus OpenSearch-shaped
  `AddIndexBlockResponse` rendering with `acknowledged`, `shards_acknowledged`,
  and successful per-index results;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, empty or blank index targets, custom indices
  options, wildcard/date-math/comma/remote-style targets, missing index names,
  non-concrete target names, unknown APIBlock ordinals, and internal-only
  `read_only_allow_delete`.

The get-index boundary covers:

- OpenSearch `GetIndexRequest` parent task, cluster-manager timeout, local
  flag, indices array, `IndicesOptions.strictExpandOpen()`, feature byte array
  (`ALIASES`, `MAPPINGS`, `SETTINGS`, `CONTEXT`), `humanReadable`, and
  `includeDefaults` at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/get` until aliases,
  mappings, settings, and index context metadata can be rendered from Rust
  cluster metadata with OpenSearch-compatible semantics;
- explicit rejection for custom cluster-manager timeouts, index filters, local
  reads, custom indices options, partial feature selection, human-readable
  settings rendering, default setting expansion, unknown feature ids, and
  get-index execution.

The indices-exists boundary covers:

- OpenSearch `IndicesExistsRequest` parent task, cluster-manager timeout,
  local flag, indices array, and `IndicesOptions.fromOptions(false, false,
  true, true)` at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/exists` until index
  existence checks can use Rust index resolution semantics and return the
  OpenSearch boolean response shape;
- explicit rejection for custom cluster-manager timeouts, empty index targets,
  local reads, custom indices options, and indices-exists execution.

The get-index-templates boundary covers:

- OpenSearch `GetIndexTemplatesRequest` parent task, cluster-manager timeout,
  local flag, and names array at the wire decode/build layer;
- implemented default all-template execution for `indices:admin/template/get`
  against Rust legacy index-template metadata, rendering the OpenSearch
  response shape for the supported metadata subset;
- explicit rejection for unsupported timeout/local-read shapes, blank template
  names, and unsupported name filters.

The put-index-template boundary covers:

- OpenSearch `PutIndexTemplateRequest` parent task, cluster-manager timeout,
  cause, template name, index pattern list, order, create flag, string-valued
  settings map, optional mappings string, zero-alias marker, and optional
  version at the OpenSearch 3.x wire decode/build layer;
- manifest-backed transport execution for `indices:admin/template/put`,
  upserting the supported legacy index-template metadata subset into Rust
  cluster metadata and rendering OpenSearch `AcknowledgedResponse`;
- explicit rejection for custom cluster-manager timeouts, missing template
  names, missing index patterns, custom causes, non-zero order, create-only
  writes, settings, mappings, and alias payloads.

The delete-index-template boundary covers:

- OpenSearch `DeleteIndexTemplateRequest` parent task, cluster-manager timeout,
  and template name at the wire decode/build layer;
- manifest-backed transport execution for `indices:admin/template/delete`,
  removing the named legacy index-template metadata entry from Rust cluster
  metadata and rendering OpenSearch `AcknowledgedResponse`;
- explicit rejection for custom cluster-manager timeouts and blank template
  names.

The put-component-template boundary covers:

- OpenSearch `PutComponentTemplateAction.Request` parent task, cluster-manager
  timeout, component-template name, optional cause, create flag, empty
  `Template` mappings/aliases markers, string-valued template settings,
  optional component-template version, and absent metadata marker at the
  OpenSearch 3.x wire decode/build
  layer;
- manifest-backed transport execution for
  `cluster:admin/component_template/put`, upserting the supported
  settings-only component-template metadata subset into Rust cluster metadata
  and rendering OpenSearch `AcknowledgedResponse`;
- explicit rejection for custom cluster-manager timeouts, missing template
  names, custom causes, create-only writes, mappings, aliases, and metadata
  payloads.

The get-component-template boundary covers:

- OpenSearch `GetComponentTemplateAction.Request` parent task,
  cluster-manager timeout, local flag, and optional component-template name at
  the wire decode/build layer;
- manifest-backed transport execution for
  `cluster:admin/component_template/get`, rendering settings-only component
  template metadata from Rust cluster metadata in the OpenSearch response
  shape;
- explicit rejection for unsupported timeout/local-read shapes and unsupported
  name filters.

The delete-component-template boundary covers:

- OpenSearch `DeleteComponentTemplateAction.Request` parent task,
  cluster-manager timeout, and component-template name at the wire decode/build
  layer;
- manifest-backed transport execution for
  `cluster:admin/component_template/delete`, removing the named component
  template metadata entry from Rust cluster metadata and rendering OpenSearch
  `AcknowledgedResponse`;
- explicit rejection for custom cluster-manager timeouts and blank template
  names.

The put-composable-index-template boundary covers:

- OpenSearch `PutComposableIndexTemplateAction.Request` parent task,
  cluster-manager timeout, composable index-template name, optional cause,
  create flag, index patterns, optional empty nested `Template`, optional
  composed-of list, optional priority, optional version, absent metadata map,
  absent data stream marker, and absent context marker at the OpenSearch 3.x
  wire decode/build layer;
- manifest-backed transport execution for `indices:admin/index_template/put`,
  inserting or replacing settings-only composable index-template metadata in
  Rust cluster metadata and rendering OpenSearch `AcknowledgedResponse`;
- explicit rejection for custom cluster-manager timeouts, missing template
  names, missing index patterns, custom causes, create-only writes, settings,
  mappings, aliases, composed-of component references, priorities, versions,
  metadata payloads, data stream templates, and contexts.

The get-composable-index-template boundary covers:

- OpenSearch `GetComposableIndexTemplateAction.Request` parent task,
  cluster-manager timeout, local flag, and optional composable index-template
  name at the wire decode/build layer;
- manifest-backed transport execution for `indices:admin/index_template/get`,
  rendering settings-only composable index-template metadata from Rust cluster
  metadata in the OpenSearch response shape;
- explicit rejection for unsupported timeout/local-read shapes and unsupported
  name filters.

The delete-composable-index-template boundary covers:

- OpenSearch `DeleteComposableIndexTemplateAction.Request` parent task,
  cluster-manager timeout, and composable index-template name at the wire
  decode/build layer;
- manifest-backed transport execution for `indices:admin/index_template/delete`,
  removing the named composable index-template metadata entry from Rust cluster
  metadata and rendering OpenSearch `AcknowledgedResponse`;
- explicit rejection for custom cluster-manager timeouts and blank template
  names.

The simulate-index-template boundary covers:

- OpenSearch `SimulateIndexTemplateRequest` parent task, cluster-manager
  timeout, local flag, index name, and optional nested
  `PutComposableIndexTemplateAction.Request` marker at the OpenSearch 3.x wire
  decode/build layer;
- explicit fail-closed classification for
  `indices:admin/index_template/simulate_index` until composable template
  resolution and simulated metadata response rendering are implemented against
  Rust cluster metadata;
- explicit rejection for custom cluster-manager timeouts, local reads, missing
  index names, inline template bodies, and simulate-index-template execution.

The simulate-template boundary covers:

- OpenSearch `SimulateTemplateAction.Request` parent task, cluster-manager
  timeout, local flag, optional template name, and optional nested
  `PutComposableIndexTemplateAction.Request` marker at the OpenSearch 3.x wire
  decode/build layer;
- explicit fail-closed classification for `indices:admin/index_template/simulate`
  until named or inline composable template resolution and simulated metadata
  response rendering are implemented against Rust cluster metadata;
- explicit rejection for custom cluster-manager timeouts, local reads, missing
  template name/body targets, empty template names, inline template bodies, and
  simulate-template execution.

The validate-query boundary covers:

- OpenSearch `ValidateQueryRequest` parent task, nullable index array,
  `IndicesOptions.fromOptions(false, false, true, false)`, minimal
  `match_all` named query builder wire, explain flag, rewrite flag, and
  all-shards flag at the OpenSearch 3.x wire decode/build layer;
- implemented classification for the bounded `match_all` validate-query subset
  with OpenSearch-shaped shard counter rendering;
- explicit rejection for index filters, custom indices options, non-`match_all`
  query builders, custom boosts, named-query markers, explain, rewrite,
  all-shards validation, and validate-query execution.

The flush boundary covers:

- OpenSearch `FlushRequest` parent task, nullable index array, default
  `IndicesOptions.strictExpandOpenAndForbidClosed()`, force flag, and
  wait-if-ongoing flag at the OpenSearch 3.x wire decode/build layer;
- implemented classification for the bounded global default flush subset with
  OpenSearch-shaped shard counter rendering;
- explicit rejection for index filters, custom indices options,
  `force=true && wait_if_ongoing=false` validation failures, forced flush,
  non-waiting flush, and flush execution.

The force-merge boundary covers:

- OpenSearch `ForceMergeRequest` parent task, nullable index array, default
  `IndicesOptions.strictExpandOpenAndForbidClosed()`, max segment count,
  only-expunge-deletes flag, post-merge flush flag, primary-only flag, and
  OpenSearch 3.x non-optional force-merge UUID at the wire decode/build layer;
- implemented classification for the bounded global default force-merge subset
  with OpenSearch-shaped shard counter rendering;
- explicit rejection for index filters, custom indices options, bounded segment
  counts, delete-expunge-only merges, `flush=false`, primary-only routing,
  empty force-merge UUIDs, and force-merge execution.

The upgrade boundary covers:

- OpenSearch `UpgradeRequest` parent task, nullable index array, default
  `IndicesOptions.strictExpandOpenAndForbidClosed()`, and
  upgrade-only-ancient-segments flag at the wire decode/build layer;
- implemented classification for the bounded global default upgrade subset with
  OpenSearch-shaped shard counters and an empty upgraded-indices map;
- explicit rejection for index filters, custom indices options,
  ancient-segment-only upgrades, and upgrade execution.

The upgrade-status boundary covers:

- OpenSearch `UpgradeStatusRequest` parent task, nullable index array, and
  default `IndicesOptions.strictExpandOpenAndForbidClosed()` at the wire
  decode/build layer;
- implemented classification for the bounded global default upgrade-status
  subset with OpenSearch-shaped shard counters and an empty shard-status array;
- explicit rejection for index filters, custom indices options, and
  upgrade-status execution.

The upgrade-settings boundary covers:

- OpenSearch `UpgradeSettingsRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, and versions map from index name to OpenSearch
  version id plus oldest Lucene segment version string at the wire decode/build
  layer;
- explicit fail-closed classification for `internal:indices/admin/upgrade`
  until index setting metadata mutation, cluster-manager publication, and
  acknowledgement rendering are implemented against Rust cluster metadata;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, empty versions maps, blank index names, invalid
  version ids, blank oldest Lucene segment versions, and upgrade-settings
  execution.

The clear-indices-cache boundary covers:

- OpenSearch `ClearIndicesCacheRequest` parent task, nullable index array,
  default `IndicesOptions.strictExpandOpenAndForbidClosed()`, query-cache flag,
  field-data-cache flag, nullable fields array normalized to empty fields,
  request-cache flag, and OpenSearch 2.8+ file-cache flag at the wire
  decode/build layer;
- implemented classification for the bounded global default clear-cache subset
  with OpenSearch-shaped shard counter rendering;
- explicit rejection for index filters, custom indices options, blank field
  names, query-cache clearing, field-data cache clearing, field selectors,
  request-cache clearing, file-cache clearing, and clear-cache execution.

The field-capabilities boundary covers:

- OpenSearch `FieldCapabilitiesRequest` parent task, fields array, indices
  array, `IndicesOptions.strictExpandOpen()`, `mergeResults`, `includeUnmapped`,
  optional index-filter query marker, and optional `nowInMillis` at the wire
  decode/build layer;
- implemented classification for the default all-indices merged request subset
  with OpenSearch-shaped `FieldCapabilitiesResponse` rendering from local
  mapping metadata, falling back to local document source type inference when
  no mapping properties are present;
- explicit rejection for empty fields, index filters, custom indices options,
  unmerged responses, include-unmapped expansion, index-filter query rewrite,
  timestamp injection, and per-index response lists.

The get-aliases boundary covers:

- OpenSearch `GetAliasesRequest` parent task, cluster-manager timeout, indices
  array, `local` flag, aliases array, `IndicesOptions.strictExpandHidden()`,
  and original aliases array at the wire decode/build layer;
- implemented classification for `indices:admin/aliases/get` default
  all-indices/all-aliases requests, rendering OpenSearch-shaped empty
  alias-list entries from the local metadata manifest;
- explicit rejection for custom cluster-manager timeout, index filters, local
  reads, alias filters, custom indices options, and original alias filters.

The get-settings boundary covers:

- OpenSearch `GetSettingsRequest` parent task, cluster-manager timeout, indices
  array, `local` flag, `IndicesOptions.fromOptions(false, true, true, true)`,
  names array, `humanReadable`, and `includeDefaults` at the wire decode/build
  layer;
- implemented classification for `indices:monitor/settings/get`
  metadata-backed requests with index/name filtering and no default expansion,
  returning OpenSearch-shaped index-settings from the local metadata manifest
  and an empty default-settings response;
- explicit rejection for custom cluster-manager timeout, index filters, local
  reads, custom indices options, human-readable formatting, and include-default
  expansion.

The cluster-search-shards boundary covers:

- OpenSearch `ClusterSearchShardsRequest` parent task, cluster-manager timeout,
  `local` flag, indices array, optional routing, optional preference,
  `IndicesOptions.lenientExpandOpen()`, and OpenSearch 2.19+ slice-present flag
  at the wire decode/build layer;
- implemented classification for `indices:admin/shards/search_shards` default
  all-indices/no-routing request admission and empty search-shards response
  rendering;
- explicit rejection for custom cluster-manager timeout, local reads, index
  filters, routing, preference, custom indices options, slice payloads, and
  non-empty shard groups, nodes, or alias-filter payloads.

The recovery boundary covers:

- OpenSearch `RecoveryRequest` parent task, indices array,
  `IndicesOptions.STRICT_EXPAND_OPEN_CLOSED`, `detailed`, and `activeOnly` at
  the wire decode/build layer;
- implemented local-node `indices:monitor/recovery` request admission for the
  default all-index, non-detailed, non-active-only subset, backed by the daemon
  transport response path that renders an empty Java-compatible recovery node
  response with local node identity;
- explicit rejection for index filters, custom indices options, detailed
  recovery output, and active-only filtering.

The segment-replication-stats boundary covers:

- OpenSearch `SegmentReplicationStatsRequest` parent task, broadcast indices
  array, `IndicesOptions.strictExpandOpenAndForbidClosed()`, `detailed`, and
  `activeOnly` at the wire decode/build layer;
- empty `SegmentReplicationStatsResponse` rendering for the default all-index,
  non-detailed, non-active-only request, backed by daemon transport routing when
  the decoded request validates as the supported empty subset;
- explicit rejection for index filters, custom indices options, detailed stage
  timing output, active-only filtering, shard failures, and non-empty
  per-index replication stats.

The indices-segments boundary covers:

- OpenSearch `IndicesSegmentsRequest` parent task, indices array,
  `IndicesOptions.strictExpandOpenAndForbidClosed()`, and `verbose` at the wire
  decode/build layer;
- implemented classification for `indices:monitor/segments` default all-index,
  non-verbose request admission, backed by the daemon transport response path
  that renders an empty Java-compatible broadcast node response and by an empty
  final `IndicesSegmentResponse` wire adapter;
- explicit rejection for index filters, custom indices options, verbose segment
  output, shard failures, and non-empty shard segment metadata.

The PIT-segments boundary covers:

- OpenSearch `PitSegmentsRequest` parent task, broadcast indices array,
  `IndicesOptions.strictExpandOpenAndForbidClosed()`, PIT id string array, and
  `verbose` at the wire decode/build layer;
- empty `IndicesSegmentResponse` rendering for standalone `_all` and explicit
  PIT ids that resolve through the shared `SteelNode` PIT context store,
  including daemon transport routing when the decoded request validates as the
  supported local subset;
- request validation for decoded non-empty PIT id arrays while wire-level empty
  PIT id entries and `_all` mixed with explicit ids still decode like
  OpenSearch;
- local PIT-segments admission accepts both non-verbose and verbose requests for
  the supported empty-segment-list response shape and de-duplicates repeated
  explicit PIT ids before
  checking local context existence, matching OpenSearch
  `TransportPitSegmentsAction.shards()` `LinkedHashSet` routing semantics for
  the supported empty-metadata response subset;
- explicit local runtime rejection for index filters, custom indices options,
  empty PIT id entries, `_all` mixed with explicit ids, and unknown explicit PIT
  ids that are not OpenSearch `SearchContextId` values;
- explicit local transport `SearchContextMissingException` rendering for
  decoded OpenSearch `SearchContextId` PIT-segments requests whose reader
  context is no longer present locally;
- REST `_cat/pit_segments` prunes expired local PIT contexts before resolving
  `_all` or explicit PIT id segment rows, matching the same reaper boundary used
  by list/delete/search PIT routes;
- REST cat root help includes the OpenSearch-documented
  `/_cat/pit_segments/{pit_id}` entry while keeping the locally registered PIT
  segments cat endpoints aligned with OpenSearch's concrete route handlers;
- REST `_nodes/stats` exposes local search session resource accounting through
  `indices.search.open_contexts`, counting active PIT plus scroll contexts after
  pruning expired PIT entries.
- daemon startup owns a local PIT expiry reaper that prunes expired PIT contexts
  without requiring a user request to hit list/delete/search/stats routes.

The indices-shard-stores boundary covers:

- OpenSearch `IndicesShardStoresRequest` parent task, cluster-manager timeout,
  `local` flag, indices array, shard health status byte set, and
  `IndicesOptions.strictExpand()` at the wire decode/build layer;
- implemented classification for `indices:monitor/shard_stores` default
  all-index, non-local, yellow/red-status request admission and empty
  `IndicesShardStoresResponse` rendering;
- explicit rejection for custom cluster-manager timeout, local reads, index
  filters, custom shard health status filters, custom indices options,
  non-empty shard store metadata, and shard-store failures.

The create-data-stream boundary covers:

- OpenSearch `CreateDataStreamAction.Request` parent task, cluster-manager
  timeout, acknowledgement timeout, and data-stream name at the wire
  decode/build layer;
- OpenSearch `AcknowledgedResponse` decode/build for the create-data-stream
  response acknowledgement bit;
- implemented manifest-backed metadata mutation for default-timeout create
  requests, creating the data-stream entry plus the first `.ds-...-000001`
  backing index with an `@timestamp` mapping and rendering an acknowledged
  response;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, and missing names.

The delete-data-stream boundary covers:

- OpenSearch `DeleteDataStreamAction.Request` parent task, cluster-manager
  timeout, and data-stream names array at the wire decode/build layer;
- OpenSearch `AcknowledgedResponse` decode/build for the delete-data-stream
  response acknowledgement bit;
- implemented manifest-backed exact and wildcard data-stream deletion,
  removing data-stream metadata, backing index metadata, matching transport
  documents, and stale local PIT contexts before rendering an acknowledged
  response;
- explicit rejection for custom cluster-manager timeouts, missing name arrays,
  and blank names.

The get-data-stream boundary covers:

- OpenSearch `GetDataStreamAction.Request` parent task, cluster-manager
  timeout, `local` flag, and optional data-stream name array at the wire
  decode/build layer;
- implemented classification for `indices:admin/data_stream/get` default
  all-data-streams, non-local request admission and empty
  `GetDataStreamAction.Response` rendering;
- explicit rejection for custom cluster-manager timeout, local reads, name
  filters, null name arrays outside the REST default path, and non-empty
  data-stream metadata.

The data-streams-stats boundary covers:

- OpenSearch `DataStreamsStatsAction.Request` parent task, indices array, and
  `IndicesOptions.strictExpandOpenAndForbidClosed()` at the wire decode/build
  layer;
- implemented classification for `indices:monitor/data_stream/stats` default
  all-data-streams request admission and empty `DataStreamsStatsAction.Response`
  rendering;
- explicit rejection for name filters, custom indices options, and
  non-empty shard failures, data-stream counters, store size, or per-stream
  stats metadata.

The resolve-index boundary covers:

- OpenSearch `ResolveIndexAction.Request` parent task, names array, and
  `IndicesOptions.strictExpandOpen()` at the wire decode/build layer;
- manifest-backed transport execution for `indices:admin/resolve/index`,
  rendering OpenSearch-shaped resolved index, alias, and data-stream lists from
  Rust metadata;
- explicit rejection for empty name arrays and custom indices options.

The create-view boundary covers:

- OpenSearch `CreateViewAction.Request` parent task, cluster-manager timeout,
  view name, description, and target index-pattern list at the wire
  decode/build layer;
- OpenSearch `GetViewAction.Response` decode/build for the returned `View`
  payload, including name, optional description, created/modified timestamps,
  and sorted target index patterns;
- explicit fail-closed classification for `cluster:admin/views/create` until
  view validation, target resolution, cluster metadata mutation, and view
  response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, missing or oversized
  names, oversized descriptions, missing or excessive targets, blank target
  patterns, oversized target patterns, and create-view execution.

The delete-view boundary covers:

- OpenSearch `DeleteViewAction.Request` parent task, cluster-manager timeout,
  and view name at the wire decode/build layer;
- OpenSearch `AcknowledgedResponse` decode/build for the delete-view response
  acknowledgement bit;
- explicit fail-closed classification for `cluster:admin/views/delete` until
  view lookup, cluster metadata deletion, and acknowledgement rendering are
  implemented;
- explicit rejection for custom cluster-manager timeouts, missing names, and
  delete-view execution.

The get-view boundary covers:

- OpenSearch `GetViewAction.Request` parent task, cluster-manager timeout, and
  view name at the wire decode/build layer;
- OpenSearch `GetViewAction.Response` decode/build for the returned `View`
  payload, including name, optional description, created/modified timestamps,
  and sorted target index patterns;
- explicit fail-closed classification for `views:data/read/get` until view
  lookup and view response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, missing names, and
  get-view execution.

The update-view boundary covers:

- OpenSearch `UpdateViewAction.TransportAction` using
  `CreateViewAction.Request` parent task, cluster-manager timeout, view name,
  description, and target index-pattern list at the wire decode/build layer;
- OpenSearch `GetViewAction.Response` decode/build for the returned `View`
  payload, including name, optional description, created/modified timestamps,
  and sorted target index patterns;
- explicit fail-closed classification for `cluster:admin/views/update` until
  view validation, target resolution, cluster metadata mutation, and view
  response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, missing or oversized
  names, oversized descriptions, missing or excessive targets, blank target
  patterns, oversized target patterns, and update-view execution.

The list-view-names boundary covers:

- OpenSearch `ListViewNamesAction.Request` as an empty request body at the wire
  decode/build layer, with trailing bytes rejected;
- OpenSearch `ListViewNamesAction.Response` decode/build for the `views`
  string list payload, with deterministic sorted output;
- implemented classification for `views:data/read/list` default empty request
  returning an OpenSearch-shaped empty `views` list;
- explicit rejection for unsupported response shapes such as blank names,
  oversized names, or excessive name counts.

The search-view boundary covers:

- OpenSearch `SearchViewAction.Request` decode/build as a full
  `SearchRequest` payload followed by the view name string written by
  `SearchViewAction.Request.writeTo`;
- reuse of the existing search-request fail-closed shape checks for scroll,
  source payload, index/routing/preference/fanout/cache/partial-results/
  cross-cluster/pipeline/timing shapes;
- explicit fail-closed classification for `views:data/read/search` until view
  lookup, target index resolution, search execution, and `SearchResponse`
  rendering are implemented;
- explicit rejection for missing or oversized view names and search-view
  execution.

The start-persistent-task boundary covers:

- OpenSearch `StartPersistentTaskAction.Request` parent task,
  cluster-manager timeout, task id, task name, and persistent-task params
  named-writeable name at the wire decode/build layer;
- OpenSearch `PersistentTaskResponse` decode/build only for the empty optional
  task payload shape, with concrete task payloads rejected until persistent
  task params/state/metadata named-writeables are mapped;
- explicit fail-closed classification for `cluster:admin/persistent/start`
  until persistent task params named-writeables, cluster metadata mutation,
  task assignment, and response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, missing or oversized
  task ids/names, params-name mismatches, start-persistent-task execution, and
  persistent-task response rendering.

The update-persistent-task-status boundary covers:

- OpenSearch `UpdatePersistentTaskStatusAction.Request` parent task,
  cluster-manager timeout, task id, allocation id, and absent optional
  `PersistentTaskState` named-writeable marker at the wire decode/build layer;
- reuse of OpenSearch `PersistentTaskResponse` decode/build for the empty
  optional task payload shape, with concrete task payloads rejected until
  persistent task params/state/metadata named-writeables are mapped;
- explicit fail-closed classification for
  `cluster:admin/persistent/update_status` until persistent task state
  named-writeables, allocation checks, cluster metadata mutation, and response
  rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, missing or oversized
  task ids, missing allocation ids, state payloads, update-persistent-task-
  status execution, and persistent-task response rendering.

The completion-persistent-task boundary covers:

- OpenSearch `CompletionPersistentTaskAction.Request` parent task,
  cluster-manager timeout, task id, allocation id, and null exception marker at
  the wire decode/build layer;
- reuse of OpenSearch `PersistentTaskResponse` decode/build for the empty
  optional task payload shape, with concrete task payloads rejected until
  persistent task params/state/metadata named-writeables are mapped;
- explicit fail-closed classification for
  `cluster:admin/persistent/completion` until exception decoding, allocation
  checks, cluster metadata mutation, restart/removal semantics, and response
  rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, missing or oversized
  task ids, missing allocation ids, exception payloads, completion-persistent-
  task execution, and persistent-task response rendering.

The remove-persistent-task boundary covers:

- OpenSearch `RemovePersistentTaskAction.Request` parent task,
  cluster-manager timeout, and task id at the wire decode/build layer;
- reuse of OpenSearch `PersistentTaskResponse` decode/build for the empty
  optional task payload shape, with concrete task payloads rejected until
  persistent task params/state/metadata named-writeables are mapped;
- explicit fail-closed classification for `cluster:admin/persistent/remove`
  until persistent task lookup, cluster metadata removal, and response
  rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, missing or oversized
  task ids, remove-persistent-task execution, and persistent-task response
  rendering.

The add-retention-lease boundary covers:

- OpenSearch `RetentionLeaseActions.AddRequest` parent task, optional
  `SingleShardRequest` internal shard id, optional concrete index, explicit
  `ShardId`, lease id, retaining sequence number, and source at the wire
  decode/build layer;
- OpenSearch `RetentionLeaseActions.Response` decode/build as an empty
  `ActionResponse` body;
- explicit fail-closed classification for
  `indices:admin/seq_no/add_retention_lease` until shard routing, primary
  operation permit acquisition, retention lease mutation, sync, and response
  rendering are implemented;
- explicit rejection for shard/index mismatches, missing or oversized lease
  ids, invalid retaining sequence numbers, missing sources, add-retention-lease
  execution, and non-empty retention lease responses.

The renew-retention-lease boundary covers:

- OpenSearch `RetentionLeaseActions.RenewRequest` parent task, optional
  `SingleShardRequest` internal shard id, optional concrete index, explicit
  `ShardId`, lease id, retaining sequence number, and source at the wire
  decode/build layer;
- OpenSearch `RetentionLeaseActions.Response` decode/build as an empty
  `ActionResponse` body;
- explicit fail-closed classification for
  `indices:admin/seq_no/renew_retention_lease` until shard routing, primary
  operation permit acquisition, retention lease renewal, and response
  rendering are implemented;
- explicit rejection for shard/index mismatches, missing or oversized lease
  ids, invalid retaining sequence numbers, missing sources,
  renew-retention-lease execution, and non-empty retention lease responses.

The remove-retention-lease boundary covers:

- OpenSearch `RetentionLeaseActions.RemoveRequest` parent task, optional
  `SingleShardRequest` internal shard id, optional concrete index, explicit
  `ShardId`, and lease id at the wire decode/build layer;
- OpenSearch `RetentionLeaseActions.Response` decode/build as an empty
  `ActionResponse` body;
- explicit fail-closed classification for
  `indices:admin/seq_no/remove_retention_lease` until shard routing, primary
  operation permit acquisition, retention lease removal, sync, and response
  rendering are implemented;
- explicit rejection for shard/index mismatches, missing or oversized lease
  ids, remove-retention-lease execution, and non-empty retention lease
  responses.

The list-dangling-indices boundary covers:

- OpenSearch `ListDanglingIndicesRequest` parent task, `BaseNodesRequest`
  node ids, absent concrete node array, optional timeout, and optional
  index UUID filter at the wire decode/build layer;
- OpenSearch `ListDanglingIndicesResponse` cluster name plus empty successful
  node response and failure lists as the bounded response subset;
- implemented classification for `cluster:admin/indices/dangling/list`
  default all-nodes requests returning an OpenSearch-shaped empty
  dangling-index response;
- explicit rejection for concrete DiscoveryNode payloads, node filters,
  timeout semantics, empty or oversized index UUID filters, non-empty node
  responses, and node failures.

The import-dangling-index boundary covers:

- OpenSearch `ImportDanglingIndexRequest` parent task, cluster-manager
  timeout, acknowledgement timeout, index UUID, and `acceptDataLoss` flag at
  the wire decode/build layer;
- OpenSearch `AcknowledgedResponse` decode/build for the acknowledgement flag;
- explicit fail-closed classification for
  `cluster:admin/indices/dangling/import` until dangling index lookup,
  accept-data-loss validation, allocation, cluster metadata mutation, and
  acknowledgement rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom ack
  timeouts, missing or oversized index UUIDs, `acceptDataLoss=false`,
  import-dangling-index execution, and acknowledgement rendering.

The delete-dangling-index boundary covers:

- OpenSearch `DeleteDanglingIndexRequest` parent task, cluster-manager
  timeout, acknowledgement timeout, index UUID, and `acceptDataLoss` flag at
  the wire decode/build layer;
- OpenSearch `AcknowledgedResponse` decode/build for the acknowledgement flag;
- explicit fail-closed classification for
  `cluster:admin/indices/dangling/delete` until dangling index lookup,
  accept-data-loss validation, index graveyard mutation, cluster metadata
  publication, and acknowledgement rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom ack
  timeouts, missing or oversized index UUIDs, `acceptDataLoss=false`,
  delete-dangling-index execution, and acknowledgement rendering.

The find-dangling-index boundary covers:

- OpenSearch `FindDanglingIndexRequest` parent task, `BaseNodesRequest` node
  ids, absent concrete node array, optional timeout, and required index UUID at
  the wire decode/build layer;
- OpenSearch `FindDanglingIndexResponse` cluster name plus empty successful
  node response and failure lists as the bounded response subset;
- implemented classification for `cluster:admin/indices/dangling/find`
  explicit UUID requests returning an OpenSearch-shaped empty result response;
- explicit rejection for concrete DiscoveryNode payloads, node filters,
  timeout semantics, missing or oversized index UUIDs, non-empty node
  responses, and node failures.

The search boundary covers:

- OpenSearch `SearchRequest` parent task, search type, indices array, routing,
  preference, absent scroll, absent search source, search indices options,
  request-cache flag, reduce/fanout controls, partial-results flag,
  cross-cluster reduction flags, cancellation interval, search pipeline, and
  phase timing flag at the wire decode/build layer;
- implemented classification for the bounded root match-all/match-none/term
  local search subset with OpenSearch `SearchResponse` wire rendering;
- explicit rejection for source/scroll payloads, non-default index/routing/
  preference/fanout/cache/partial-results/cross-cluster/pipeline/timing shapes,
  and search execution.
- REST search responses honor `rest_total_hits_as_int=true` for accurate total
  hits and reject the OpenSearch-disallowed numeric `track_total_hits`
  threshold combination.
- REST search source parsing applies `from` and `size` query parameters over
  request-body values, with non-negative integer validation.
- REST search source parsing appends comma-separated `sort` query parameters
  using OpenSearch `field[:asc|desc]` syntax.
- REST search source parsing applies boolean and numeric `track_total_hits`
  query parameters, including omitted `hits.total` when tracking is disabled
  and `-1` in `rest_total_hits_as_int` compatibility mode.
- REST search source parsing applies positive `terminate_after` query
  parameters and preserves body `terminate_after` when the query value is `0`.
- REST search source parsing applies `explain`, `version`, and
  `seq_no_primary_term` boolean body/query parameters, accepts body `profile`
  booleans, and renders requested hit metadata/profile data.
- REST search applies top-level `min_score` filtering and bounded
  `post_filter` hit filtering while preserving aggregation input.
- REST search parses and validates body/query `timeout` time values before
  admitting the bounded standalone search path.
- REST search applies bounded body/query `_source` projection and top-level
  `fields` hit projection for supported field selectors.
- REST search validates `search_after` scroll/from/sort-count and sort-value
  type constraints with OpenSearch-shaped shard failure errors and renders
  requested hit `sort` values for reuse by follow-up pages.

The stream-search boundary covers:

- OpenSearch `StreamSearchAction` action binding with the same bounded
  `SearchRequest` wire decode/build layer used by normal search;
- implemented classification for the same bounded local `SearchRequest` subset
  as normal search, bound to the stream-search action name;
- explicit rejection for unsupported nested `SearchRequest` shapes through the
  bounded search execution boundary.

The multi-search boundary covers:

- OpenSearch `MultiSearchRequest` parent task, max concurrent search request
  count, sub-search count, and nested `SearchRequest` wire shapes at the wire
  decode/build layer;
- implemented classification for ordered batches of supported sub-search
  requests with OpenSearch `MultiSearchResponse` success-item rendering;
- explicit rejection for custom multi-search concurrency, empty request batches,
  unsupported nested search request shapes, and multi-search execution.

The search-scroll boundary covers:

- OpenSearch `SearchScrollRequest` parent task, scroll id, and optional
  keep-alive `Scroll` time value at the wire decode/build layer;
- implemented classification for local scroll context advancement with
  OpenSearch `SearchResponse` wire page rendering;
- explicit rejection for empty scroll ids and unsupported search-scroll
  execution shapes.

The clear-scroll boundary covers:

- OpenSearch `ClearScrollRequest` parent task and scroll id array at the wire
  decode/build layer;
- OpenSearch `ClearScrollResponse` succeeded rendering with non-negative
  `num_freed` counts;
- local transport route invalidation for standalone `_all` and explicit scroll
  ids through the shared `SteelNode` scroll context store;
- explicit rejection for empty scroll id arrays and empty scroll id entries;
  `_all` is treated as a clear-all selector only when it is the sole scroll id,
  matching the OpenSearch controller branch.

The explain boundary covers:

- OpenSearch `ExplainRequest` parent task, single-shard prefix, index, id,
  routing, preference, query named-writeable marker, alias filter marker,
  optional stored fields, fetch-source context marker, and `nowInMillis` at the
  bounded wire decode/build layer;
- implemented classification for the bounded match_all/match_none local explain
  subset with OpenSearch `ExplainResponse` wire rendering;
- explicit rejection for concrete shard ids, missing index/id/query fields,
  routing, preference, alias filters, stored fields, fetch-source context, and
  explain execution.

The delete-PIT boundary covers:

- OpenSearch `DeletePitRequest` parent task and PIT id array at the wire
  decode/build layer;
- OpenSearch `DeletePitResponse` result-list rendering with each
  `DeletePitInfo` encoded as `successful` plus `pit_id`;
- request validation for decoded non-empty PIT id arrays and response
  build/decode support for non-empty `DeletePitInfo` result lists;
- shared `SteelNode` PIT context invalidation for explicit PIT ids and `_all`;
- OpenSearch-compatible explicit-id delete idempotence where missing or already
  removed valid-shaped PIT contexts still render successful `DeletePitInfo`
  entries, with duplicate explicit ids collapsed for both missing and existing
  contexts like the REST close-PIT route;
- REST close-PIT now rejects malformed explicit PIT ids before local context
  invalidation, matching OpenSearch `SearchContextId.decode(...)` admission
  before missing-context idempotence;
- standalone `_all` delete prunes expired local PIT contexts before rendering
  active deletion results, while `_all` mixed with explicit ids is not admitted
  into the local execution subset because OpenSearch routes that shape through
  the explicit-id path and fails while decoding `_all` as a PIT id;
- explicit local lifecycle rejection for empty PIT id arrays, while wire-level
  empty PIT id entries still decode and local transport delete-PIT renders
  OpenSearch-shaped `DeletePitInfo` results for them.

The get-all-PITs boundary covers:

- OpenSearch `GetAllPitNodesRequest` parent task, nullable node ids, concrete
  `DiscoveryNode` payloads, and optional timeout at the wire decode/build layer;
- OpenSearch `GetAllPitNodesResponse` `BaseNodesResponse` rendering with
  cluster name, node responses, `DiscoveryNode` metadata, `ListPitInfo`
  entries encoded as `pit_id`, `creation_time`, and `keep_alive`, plus
  `FailedNodeException` node failures;
- request validation for the default all-nodes request, unscoped `_all` and
  `_local` node selectors, optional timeout, and single concrete-node
  `BaseNodesRequest` payloads, plus response build/decode support for non-empty
  PIT info node lists;
- shared `SteelNode` PIT context listing for the local-node transport subset;
- local node-id filters (`_local`, local node id, or local node name) are
  admitted by the local lifecycle route, while remote node-id filters,
  non-local/multi-node concrete-node payloads decode as valid OpenSearch
  `BaseNodesRequest` fields but are excluded until multi-node fanout semantics
  are implemented;
- single local concrete-node payloads are admitted by the local lifecycle route,
  matching OpenSearch `PitService` requests that target the local transport node;
- raw `ListPitInfo` values decode without local id/range validation like the
  OpenSearch wire object.

The create-PIT boundary covers:

- OpenSearch `CreatePitRequest` parent task, indices array, search default
  indices options, routing, preference, keep-alive time value, and optional
  `allowPartialPitCreation` flag at the wire decode/build layer;
- OpenSearch `CreatePitResponse` rendering with PIT id, total, successful,
  failed, skipped shard counts, creation time, and `ShardSearchFailure`
  payloads;
- raw create-PIT request `TimeValue` values down to `-1` and raw response
  scalar fields decode without extra local value validation like the OpenSearch
  wire objects;
- local transport PIT context allocation for default all-indices requests and
  index/alias/wildcard targets with routing accepted as a shard-routing hint
  rather than a document filter, into the shared `SteelNode` PIT context store,
  including the resolved index set, document snapshot, primary-shard count,
  keep-alive expiry bookkeeping, and read-all/delete visibility through the
  same lifecycle state;
- REST and local transport create-PIT responses now return unpadded base64url
  opaque PIT ids instead of the earlier `pit-N` debug-shaped ids, while storing
  and resolving the same opaque id through list, search, delete, and segments
  lifecycle paths;
- REST create-PIT, local transport create-PIT, and PIT-search keep-alive
  extension reject values above the OpenSearch default
  `point_in_time.max_keep_alive` of `24h`;
- REST create-PIT rejects local open PIT context creation beyond the OpenSearch
  default `search.max_open_pit_context` limit of `300`;
- local transport create-PIT applies the same open PIT context ceiling before
  allocating a new opaque id or document snapshot;
- PIT searches allow concurrent local requests to share a PIT id while
  extending the same context keep-alive value;
- PIT search rejects `scroll` query parameters with the OpenSearch validation
  error used for point-in-time requests in scroll contexts, including
  aggregated scroll validation when PIT, `_shard_doc`, `from`, `size=0`,
  and `request_cache=true` are combined;
- REST search validates `_shard_doc` sort usage for PIT-only admission,
  scroll rejection, and duplicate `_shard_doc` sort entries;
- PIT searches render `_shard_doc` sort values and accept ASC/DESC
  `search_after` bounds for stable local snapshot pagination;
- PIT searches apply field-sort `search_after` against the stored PIT snapshot,
  preserving divergence from live searches after later writes;
- PIT searches invalidate the local PIT context when its backing index has been
  deleted or closed, matching OpenSearch deleted-index and missing-context
  failure semantics;
- search request PIT builders now decode empty PIT ids at the wire layer like
  OpenSearch `PointInTimeBuilder`, while local PIT search execution still
  rejects empty ids before context lookup;
- PIT searches accept `ccs_minimize_roundtrips=false` on the local execution
  subset, matching OpenSearch transport execution where PIT searches bypass
  minimized-roundtrip CCS even when non-PIT local search still rejects custom
  CCS roundtrip control;
- PIT searches accept the OpenSearch REST `preparePointInTime` transport shape
  where request indices are populated from the decoded PIT id and indices
  options are tightened for PIT execution, while local execution rejects
  indices that do not match the stored PIT context;
- search and multi-search wire tests now explicitly separate prepared-PIT
  admission from the remaining search response execution boundary, and pin the
  OpenSearch `preparePointInTime` rejection behavior for explicit routing and
  preference alongside PIT;
- PIT search execution keeps the OpenSearch REST `preparePointInTime`
  rejection boundary for explicit `routing` and `preference` alongside PIT;
- PIT reader-context updates now decode OpenSearch `SearchContextId` PIT ids to
  restore the backing indices and admit the subsequent prepared PIT search
  shape against the registered local context;
- OpenSearch `SearchContextId` wire support preserves alias-filter entries and
  their optional query payloads; local PIT search applies the decoded alias
  filter query through the same local query matcher used for the request query;
- PIT searches reject malformed local opaque PIT ids with the OpenSearch
  `invalid id` error while preserving missing-context handling for well-formed
  local ids;
- delete-PIT REST parsing now rejects malformed JSON bodies with the
  OpenSearch `Failed to parse request body` illegal-argument response instead
  of falling through to an empty PIT id validation error;
- manifest-backed create-PIT index option handling for unavailable targets,
  `allow_no_indices`, ignored aliases, alias fanout guards, open/closed
  wildcard expansion, and hidden wildcard expansion;
- local transport create-PIT now renders an OpenSearch `IndexNotFoundException`
  transport error for strict concrete-index requests whose target is absent,
  while lenient `ignore_unavailable` requests continue through the empty
  resolved-index subset;
- local transport create-PIT now renders the OpenSearch
  `IllegalArgumentException` boundary for explicit alias targets when
  `ignore_aliases=true` and index resolution is configured to fail;
- local transport create-PIT now renders the OpenSearch
  `IllegalArgumentException` boundary for explicit aliases that fan out to
  multiple indices when `forbid_aliases_to_multiple_indices=true`;
- local transport create-PIT now renders the OpenSearch
  `InvalidIndexNameException` boundary for explicit index or wildcard
  expressions that start with `_`;
- local transport create-PIT now renders an OpenSearch `IndexClosedException`
  transport error for strict concrete-index requests whose target is closed,
  while lenient `ignore_unavailable` requests skip that closed target;
- local transport create-PIT now renders the OpenSearch
  `IllegalArgumentException` boundary for closed-only wildcard expansion when
  `forbid_closed_indices` remains true;
- local transport create-PIT now renders an OpenSearch `IndexNotFoundException`
  for single wildcard or `_all` requests that resolve to no concrete indices
  while `allow_no_indices=false`;
- local transport create-PIT now applies the same `allow_no_indices=false`
  no-match error boundary to wildcard selectors inside multi-expression and
  negative-selector request lists;
- local transport create-PIT resolves explicit `_all` and wildcard selectors
  against the union of manifest-backed indices and locally-created open
  indices, matching cluster-state-backed resolution for the standalone adapter
  when no manifest entry exists;
- local transport create-PIT applies OpenSearch-style negative wildcard
  selectors after a prior wildcard selector, so expressions such as
  `logs-*,-logs-secret-*` remove previously matched targets before the PIT
  snapshot is allocated;
- local transport create-PIT resolves manifest-backed data stream selectors to
  their backing indices before allocating the PIT `SearchContextId` and
  snapshot, matching OpenSearch index-abstraction resolution for PIT targets;
- create-PIT `preference` and `allow_partial_pit_creation` wire/runtime
  admission for the local all-success shard subset, requiring an explicit
  `allowPartialPitCreation` true/false value before local execution because
  OpenSearch REST/client create-PIT paths set it before `CreatePitRequest`
  execution;
- REST and local transport create-PIT normalize non-positive keep-alive values
  to the OpenSearch-compatible 30s local keep-alive value, while wire decoding
  still rejects unknown keep-alive units.
- local transport PIT keep-alive conversion now matches OpenSearch
  `TimeValue.millis()` truncation for nanosecond and microsecond wire values,
  so sub-millisecond create-PIT keep-alive values enter the same non-positive
  normalization boundary as OpenSearch.
- REST PIT keep-alive parsing now applies the same millisecond truncation for
  nanosecond and microsecond values before create-PIT normalization, so
  sub-millisecond REST keep-alive values follow the same non-positive local PIT
  lifecycle boundary as OpenSearch `TimeValue.millis()`.
- local transport PIT searches now render `_shard_doc` sort values from the
  OpenSearch-style routing shard slot plus sequence number instead of falling
  back to sequence number alone, so `search_after` remains stable when a PIT
  snapshot contains multiple shard/routing partitions with the same sequence
  number.
- local transport search admission now preserves OpenSearch `search_after`
  failure boundaries for scroll requests, non-zero `from`, missing sort fields,
  and mismatched `search_after`/sort value counts before executing the local
  search subset.
- local transport search admission now also preserves OpenSearch collapse
  failure boundaries for scroll requests and for `collapse` with
  `search_after`, where the single sort field must match the collapse field.
- local transport search admission now preserves OpenSearch `stored_fields`
  failure boundaries where stored fields are disabled while `_source` or
  `fields` are requested.
- local transport create-reader-context and update-reader-context reject
  keep-alive values above the OpenSearch default
  `point_in_time.max_keep_alive` of `24h`, matching the runtime
  `SearchService.createPitReaderContext` and
  `SearchService.updatePitIdAndKeepAlive` boundaries before allocating or
  updating local PIT reader state.
- local transport create-reader-context now verifies the target index and shard
  against local created-index state or manifest shard metadata before
  allocating a reader context, matching the OpenSearch
  `indicesService.indexServiceSafe(...).getShard(...)` admission boundary for
  the local-node subset.
- local transport create-reader-context now also rejects manifest-backed
  closed indices. OpenSearch creates PIT reader contexts only for shard targets
  selected by the create-PIT search phase, so the local adapter keeps direct
  reader-context execution bounded to open/searchable shard targets.
- local transport create-reader-context now applies the OpenSearch default
  `search.max_open_pit_context` limit of `300` before allocating a reader
  context, matching the `SearchService.createPitReaderContext` open-context
  admission boundary for the local-node subset.
- local transport update-reader-context now requires a reader context id
  previously allocated by the local create-reader-context route before updating
  PIT state, matching OpenSearch `getPitReaderContext(...)` missing-context
  rejection for the local-node subset.
- local transport update-reader-context now rejects empty PIT ids at the local
  execution boundary while still decoding them at the wire layer. OpenSearch's
  update phase receives the PIT id produced by create-PIT, so the local adapter
  only admits non-empty ids when mutating reader/PIT lifecycle state.
- local transport update-reader-context now tracks per-reader PIT id and
  creation-time assignment as one-shot state. OpenSearch stores both values in
  `SetOnce` fields on `PitReaderContext`, so a second assignment for the same
  reader context is rejected and the local reader context is released instead of
  mutating PIT lifecycle state again.
- PIT reader-context transport wire decoding now allows empty PIT id, node id,
  and shard search session strings where OpenSearch's internal
  `PitSearchContextIdForNode`, `SearchContextIdForNode`,
  `ShardSearchContextId`, and update-PIT context request/response wire classes
  also round-trip raw strings without validation; local execution still rejects
  unknown reader contexts before mutating local PIT state.
- local transport get-all-PIT admission now accepts decoded `BaseNodesRequest`
  timeout values for the single-node subset, matching OpenSearch
  `TransportGetAllPitsAction` request shape while still restricting execution
  to local node selectors or the local concrete node.
- local transport free-PIT-context admission now accepts only context ids that
  target the current Steelsearch node id/name, `_local`, or OpenSearch's empty
  raw-string wire shape, and rejects remote cluster aliases or nonlocal node
  ids before mutating local PIT state.
- local transport free-PIT-context now rejects empty context-id lists at the
  execution boundary while still decoding the raw wire shape. OpenSearch
  `PitService` returns an empty `DeletePitResponse` before transport fanout
  when there are no node contexts, so node-level free-PIT-context requests carry
  at least one context id.

The indices-stats boundary covers:

- OpenSearch `IndicesStatsRequest` parent task, indices array, indices options,
  and `CommonStatsFlags` at the wire decode/build layer;
- implemented local-node `indices:monitor/stats` request admission for the
  default all-index, all-stats subset, backed by the daemon transport response
  path that renders an empty Java-compatible index stats node response with
  local node identity;
- explicit rejection for index filters, non-default indices options,
  and non-default stats flags.

The pending-cluster-tasks adapter covers:

- OpenSearch `PendingClusterTasksRequest` parent task, cluster-manager timeout,
  and local flag at the wire decode/build layer;
- OpenSearch `PendingClusterTasksResponse` task entries with insert order,
  priority, source, executing flag, and time-in-queue fields;
- daemon transport first-request and follow-up routes render pending/in-flight
  task entries from the current task queue snapshot;
- terminal task records remain excluded from the pending-task transport
  response, matching the active pending-task surface.

The list-tasks adapter covers:

- OpenSearch `ListTasksRequest` parent task, unset task id filter, unset parent
  task filter, no node filters, no action filters, no timeout, `detailed=false`,
  and `wait_for_completion=false`;
- OpenSearch `ListTasksResponse` with no task failures, no node failures, and
  pending/in-flight task info entries for the tracked cluster-manager task
  subset;
- daemon transport first-request and follow-up routes render the OpenSearch
  shaped response from the current task queue snapshot for the supported subset;
- explicit rejection for task id filters, parent task filters, node filters,
  action filters, timeout, detailed task status payloads, wait-for-completion,
  non-empty task failure payloads, non-empty node failure payloads, and task
  resource stats until those runtime lifecycle semantics are mapped.

The get-task boundary covers:

- OpenSearch `GetTaskRequest` parent task, explicit task id, optional timeout,
  and wait-for-completion fields at the wire decode/build layer;
- OpenSearch `GetTaskResponse` running `TaskResult` payloads with task info for
  tracked pending/in-flight cluster-manager tasks;
- daemon transport first-request and follow-up routes render the OpenSearch
  shaped response from the current task queue snapshot for explicit task ids;
- empty get-task responses for unknown tracked task ids in the current subset;
- explicit rejection for missing task id, timeout, wait-for-completion, and
  completed task error/response payloads until those lifecycle semantics are
  mapped.

The cancel-tasks adapter covers:

- OpenSearch `CancelTasksRequest` parent task, unset or explicit task id
  filter, unset parent task filter, no node filters, no action filters, no
  timeout, default reason `by user request`, and `wait_for_completion=false`;
- OpenSearch `CancelTasksResponse` with no task failures, no node failures, and
  cancelled task info entries for all tracked queued cluster-manager tasks or
  the requested tracked queued task id;
- daemon transport first-request and follow-up routes render the OpenSearch
  shaped response from the current task queue snapshot for the supported subset;
- explicit rejection for parent task filters, node filters, action filters,
  timeout, custom reason, wait-for-completion, non-empty task failure payloads,
  non-empty node failure payloads, detailed task status payloads, and task
  resource stats until broader runtime task cancellation lifecycle semantics
  are mapped.

The bulk adapter covers:

- OpenSearch `BulkRequest` parent task, default active-shard count, ordered
  item list, refresh policy `NONE`, and default timeout;
- bulk `IndexRequest` and `DeleteRequest` items using the same bounded
  single-document wire subsets as the standalone index/delete adapters;
- OpenSearch `BulkResponse` item arrays with successful `IndexResponse` and
  `DeleteResponse` payloads, request-order item ids, took millis, and
  no-ingest-took marker;
- conversion from bounded bulk index/delete items into Rust `BulkWriteRequest`
  operations, and conversion from successful Rust bulk index/delete items into
  OpenSearch bulk item responses;
- explicit rejection for custom active-shard waits, refresh policies, custom
  timeout, update items, create/replay/update response kinds, empty item
  responses, and failure item responses until those semantics and exception
  wire shapes are mapped.

The index adapter covers:

- OpenSearch `IndexRequest` parent task, default replication request header,
  refresh policy `NONE`, optional id, JSON source bytes, empty extra field
  values, `INDEX` op type, internal version type, match-any version, no
  pipeline, unset auto-generated timestamp, unset optimistic-concurrency
  markers, and `require_alias=false`;
- OpenSearch `IndexResponse` / `DocWriteResponse` shard info, shard id,
  document id, version, seq no, primary term, forced refresh flag, and
  `CREATED` / `UPDATED` result codes for the no-failure response shape;
- conversion from the default index request wire subset into the Rust
  `IndexDocumentRequest` engine type, and conversion from Rust created/updated
  write responses into OpenSearch index responses;
- explicit rejection for explicit shard ids, custom active-shard waits, custom
  replication timeout, routed cluster version, refresh policies, missing ids,
  routing, extra field values, `CREATE` op type, versioned writes, ingest
  pipelines, retry state, auto-generated ids, non-JSON content type,
  optimistic-concurrency writes, and require-alias writes until those semantics
  are mapped.

The update adapter covers:

- OpenSearch `UpdateRequest` parent task, index, default timeout, no concrete
  index override, default active-shard count, id, no routing, no script,
  `retry_on_conflict=0`, refresh policy `NONE`, doc-based nested
  `IndexRequest`, no fetch-source context, no explicit upsert, unset
  optimistic-concurrency markers, `detect_noop=true`, no scripted upsert, and
  `require_alias=false`;
- OpenSearch `UpdateResponse` / `DocWriteResponse` shard info, shard id,
  document id, version, seq no, primary term, forced refresh flag, and
  `CREATED` / `UPDATED` / `NOOP` result codes with no embedded get result;
- conversion from the bounded doc-based update request into the Rust
  `UpdateDocumentRequest` engine type, and conversion from Rust created/updated
  write responses into OpenSearch update responses;
- explicit rejection for explicit shard ids, custom timeout, concrete index
  override, custom active-shard waits, routing, scripts, retry-on-conflict,
  refresh policies, fetch-source context, explicit upsert, optimistic
  concurrency, `detect_noop=false`, scripted upsert, require-alias, missing doc,
  mismatched nested doc identity, deleted write responses, and embedded get
  results until those semantics are mapped.

The delete adapter covers:

- OpenSearch `DeleteRequest` parent task, default replication request header,
  refresh policy `NONE`, document id, internal version type, match-any version,
  and unset optimistic-concurrency markers;
- OpenSearch `DeleteResponse` / `DocWriteResponse` shard info, shard id,
  document id, version, seq no, primary term, forced refresh flag, and
  `DELETED` / `NOT_FOUND` result codes for the no-failure response shape;
- conversion from the default delete request wire subset into the Rust
  `DeleteDocumentRequest` engine type, and conversion from Rust deleted write
  responses into OpenSearch delete responses;
- explicit rejection for explicit shard ids, custom active-shard waits, custom
  replication timeout, routed cluster version, refresh policies, routing,
  versioned deletes, and optimistic-concurrency deletes until those semantics
  are mapped.

The multi-get adapter covers:

- OpenSearch `MultiGetRequest` parent task, preference/refresh/realtime flags,
  and item list wire shape;
- default item wire shape for index, id, internal version type, and match-any
  version;
- OpenSearch `MultiGetResponse` item arrays containing successful found and
  not-found `GetResponse` payloads;
- conversion from default multi-get item requests into batched Rust
  `GetDocumentRequest` values;
- explicit rejection for top-level preference, pre-get refresh, non-realtime
  reads, item routing, item stored fields, item versioned reads, item fetch
  source context, and failure response items until those semantics are mapped.

The term-vectors boundary covers:

- OpenSearch `TermVectorsRequest` parent task, optional single-shard id marker,
  optional index, document id, optional artificial document marker/media type,
  optional routing, optional preference, term-vector flags bitset, selected
  fields collection, per-field analyzer generic string map, filter-settings
  marker, realtime flag, internal version type, and match-any version at the
  wire decode/build layer;
- explicit fail-closed classification for `indices:data/read/tv` until shard
  routing, realtime/non-realtime visibility, analyzer selection, term
  statistics generation, and response rendering are implemented against Rust
  shard state;
- explicit rejection for explicit shard ids, missing index, missing id/doc,
  artificial documents, routing, preference, custom flags, selected fields,
  per-field analyzers, filter settings, non-realtime reads, versioned reads,
  and term-vectors execution.

The multi term-vectors boundary covers:

- OpenSearch `MultiTermVectorsRequest` parent task, optional preference, and
  collection of nested `TermVectorsRequest` payloads at the wire decode/build
  layer;
- nested term-vectors item decoding with the same request envelope, id/doc,
  routing/preference, flags, selected fields, analyzer map, filter settings,
  realtime, and versioning markers as the single term-vectors boundary;
- explicit fail-closed classification for `indices:data/read/mtv` until
  per-item shard routing, realtime/non-realtime visibility, analyzer
  selection, term statistics generation, item failure handling, and aggregate
  response rendering are implemented against Rust shard state;
- explicit rejection for empty request batches, top-level preference, any
  unsupported nested term-vectors item shape, and multi term-vectors execution.

The get adapter covers:

- OpenSearch `GetRequest` parent task, optional index, id, realtime flag,
  internal version type, and match-any version wire shape;
- OpenSearch `GetResponse` / `GetResult` fields for found and not-found
  documents with empty document/meta fields;
- conversion between the default get transport wire subset and the Rust
  `GetDocumentRequest` / `GetDocumentResponse` engine types;
- explicit rejection for routing, preference, stored fields, pre-get refresh,
  non-realtime reads, versioned reads, explicit shard ids, and fetch source
  context until those semantics are mapped.

The refresh adapter covers:

- OpenSearch `RefreshRequest` parent task, indices array, and
  `strictExpandOpenAndForbidClosed` indices options wire shape;
- OpenSearch `RefreshResponse` broadcast shard counters for the no-failure
  response shape;
- conversion between the refresh transport wire type and the Rust
  `RefreshRequest` / `RefreshResponse` engine types;
- request and response frame binding for `indices:admin/refresh`.

Current refresh wire microbenchmark:

```text
cargo run -p os-transport --release --bin refresh-wire-benchmark
refresh_request_encode ops_per_second=1406595.61 nanos_per_op=710.94
refresh_response_encode ops_per_second=4439320.78 nanos_per_op=225.26
refresh_request_decode ops_per_second=1490146.36 nanos_per_op=671.08
refresh_response_decode ops_per_second=4260991.25 nanos_per_op=234.69
refresh_wire_bottleneck_ops_per_second=1406595.61
```

The current refresh wire bottleneck alternates between request encode and
request decode across local release runs. At roughly 1.41M ops/s in the latest
run, this adapter is not the bottleneck relative to the existing HTTP
search/write/refresh benchmark paths. Re-run the command above after each
transport adapter change that affects request/response framing.

Current cluster-health wire microbenchmark:

```text
cargo run -p os-transport --release --bin cluster-health-wire-benchmark
cluster_health_request_encode ops_per_second=1644852.71 nanos_per_op=607.96
cluster_health_response_encode ops_per_second=2072369.95 nanos_per_op=482.54
cluster_health_request_decode ops_per_second=1638275.37 nanos_per_op=610.40
cluster_health_response_decode ops_per_second=2557542.58 nanos_per_op=391.00
cluster_health_wire_bottleneck_ops_per_second=1638275.37
```

The current cluster-health wire bottleneck is request decode. This path has no
JSON source materialization and only validates the bounded enum-set/default
request shape, so it is materially lighter than index/update/bulk request
decode. At roughly 1.64M ops/s in the latest local release run, this adapter
does not introduce a transport-wire bottleneck.

Current main wire microbenchmark:

```text
cargo run -p os-transport --release --bin main-wire-benchmark
main_request_encode iterations=400000 elapsed_ms=180.945 ops_per_second=2210613.19 nanos_per_op=452.36
main_request_decode iterations=400000 elapsed_ms=176.158 ops_per_second=2270687.98 nanos_per_op=440.40
main_request_validate iterations=400000 elapsed_ms=176.028 ops_per_second=2272361.84 nanos_per_op=440.07
main_response_encode iterations=400000 elapsed_ms=369.083 ops_per_second=1083766.57 nanos_per_op=922.71
main_response_decode iterations=400000 elapsed_ms=365.487 ops_per_second=1094431.57 nanos_per_op=913.72
main_wire_bottleneck_ops_per_second=1083766.57
```

The current main boundary bottleneck is response encode over node, cluster,
version, and build metadata. At roughly 1.08M ops/s in the latest local release
run, this adapter is still not a material transport-wire bottleneck for root
info probes.

Current remote-info supported-subset wire microbenchmark:

```text
cargo run -p os-transport --release --bin remote-info-wire-benchmark
remote_info_request_encode ops_per_second=2026710.29 nanos_per_op=493.41
remote_info_request_decode ops_per_second=2057269.16 nanos_per_op=486.08
remote_info_supported_validation ops_per_second=2114831.35 nanos_per_op=472.85
remote_info_response_encode ops_per_second=8084294.13 nanos_per_op=123.70
remote_info_response_decode ops_per_second=6938670.65 nanos_per_op=144.12
remote_info_wire_bottleneck_ops_per_second=2026710.29
```

The current remote-info supported-subset boundary is request/response framing
for a parent-task-only request and empty remote connection list response. The
first performance-sensitive work beyond this boundary is non-empty remote
connection info collection and response rendering.

Current get-term-version wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-term-version-wire-benchmark
get_term_version_request_encode iterations=400000 elapsed_ms=195.650 ops_per_second=2044469.16 nanos_per_op=489.12
get_term_version_request_decode iterations=400000 elapsed_ms=175.306 ops_per_second=2281719.62 nanos_per_op=438.27
get_term_version_request_validate iterations=400000 elapsed_ms=179.211 ops_per_second=2232010.16 nanos_per_op=448.03
get_term_version_response_encode iterations=400000 elapsed_ms=157.896 ops_per_second=2533308.37 nanos_per_op=394.74
get_term_version_response_decode iterations=400000 elapsed_ms=149.409 ops_per_second=2677206.79 nanos_per_op=373.52
get_term_version_wire_bottleneck_ops_per_second=2044469.16
```

The current get-term-version boundary bottleneck is request encode over the
parent-task, cluster-manager-timeout, and local-flag request frame. At roughly
2.04M ops/s in the latest local release run, this adapter is not a material
transport-wire bottleneck for term/version probes.

Current cluster-stats reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin cluster-stats-wire-benchmark
cluster_stats_request_encode iterations=400000 elapsed_ms=212.099 ops_per_second=1885908.72 nanos_per_op=530.25
cluster_stats_request_decode iterations=400000 elapsed_ms=189.918 ops_per_second=2106171.13 nanos_per_op=474.80
cluster_stats_request_validate iterations=400000 elapsed_ms=191.100 ops_per_second=2093147.33 nanos_per_op=477.75
cluster_stats_response_decode iterations=400000 elapsed_ms=223.199 ops_per_second=1792124.90 nanos_per_op=558.00
cluster_stats_wire_bottleneck_ops_per_second=1792124.90
```

The current cluster-stats implemented-path wire bottleneck is response decode.
At roughly 1.80M ops/s in the latest local release run, the wire adapter is not
the first expected bottleneck; full node stats aggregation remains a separate
mapping and fanout task.

Current cat-shards implemented-path wire microbenchmark:

```text
cargo run -p os-transport --release --bin cat-shards-wire-benchmark
cat_shards_request_encode iterations=400000 elapsed_ms=181.089 ops_per_second=2208861.93 nanos_per_op=452.72
cat_shards_request_decode iterations=400000 elapsed_ms=193.691 ops_per_second=2065147.04 nanos_per_op=484.23
cat_shards_request_validate iterations=400000 elapsed_ms=197.504 ops_per_second=2025270.46 nanos_per_op=493.76
cat_shards_response_decode iterations=400000 elapsed_ms=101.817 ops_per_second=3928599.59 nanos_per_op=254.54
cat_shards_wire_bottleneck_ops_per_second=2025270.46
```

The current cat-shards implemented-path wire bottleneck is request validation.
At roughly 2.03M ops/s in the latest local release run, the empty response wire
adapter is not the first expected bottleneck. Runtime scope is intentionally
limited to the empty response subset; populated shard routing plus index stats
response rendering remains separate work.

Current nodes-info supported-subset wire microbenchmark:

```text
cargo run -p os-transport --release --bin nodes-info-wire-benchmark
nodes_info_request_encode ops_per_second=750450.67 nanos_per_op=1332.53
nodes_info_request_decode ops_per_second=650867.55 nanos_per_op=1536.41
nodes_info_supported_validation ops_per_second=644897.32 nanos_per_op=1550.63
nodes_info_wire_bottleneck_ops_per_second=644897.32
```

The current nodes-info supported-subset boundary bottleneck is validation over
the decoded request. The dominant cost is the OpenSearch default metric string
array encode/decode, not the supported-subset check itself. At roughly 645K ops/s
in the latest local run, this path is above the retained k-NN stats reject-wire
bottleneck and does not currently introduce a new transport admission hotspot.

Current nodes-stats supported-subset wire microbenchmark:

```text
cargo run -p os-transport --release --bin nodes-stats-wire-benchmark
nodes_stats_request_encode ops_per_second=1687353.69 nanos_per_op=592.64
nodes_stats_request_decode ops_per_second=1688999.84 nanos_per_op=592.07
nodes_stats_supported_validation ops_per_second=1654117.74 nanos_per_op=604.55
nodes_stats_wire_bottleneck_ops_per_second=1654117.74
```

The current nodes-stats supported-subset boundary is compact because the default
request carries empty node filters plus default common stats flags. The first
performance-sensitive work beyond this boundary is populating non-empty node
telemetry groups and rendering full stats responses. At roughly 1.65M ops/s in
the latest local run, this path does not introduce a new transport admission
hotspot.

Current wlm-stats wire microbenchmark:

```text
cargo run -p os-transport --release --bin wlm-stats-wire-benchmark
wlm_stats_request_encode iterations=400000 elapsed_ms=193.165 ops_per_second=2070773.38 nanos_per_op=482.91
wlm_stats_request_decode iterations=400000 elapsed_ms=204.696 ops_per_second=1954112.60 nanos_per_op=511.74
wlm_stats_request_validate iterations=400000 elapsed_ms=204.566 ops_per_second=1955357.50 nanos_per_op=511.42
wlm_stats_response_encode iterations=400000 elapsed_ms=590.592 ops_per_second=677286.17 nanos_per_op=1476.48
wlm_stats_response_decode iterations=400000 elapsed_ms=607.408 ops_per_second=658535.70 nanos_per_op=1518.52
wlm_stats_wire_bottleneck_ops_per_second=658535.70
```

The current wlm-stats boundary bottleneck is response decode over the local
node entry and empty workload-group stats map. At roughly 659k ops/s in the
latest local release run, this adapter is not the expected first bottleneck;
the first performance-sensitive expansion is non-empty workload group runtime
telemetry collection and response rendering.

Current remote-store-stats reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin remote-store-stats-reject-wire-benchmark
remote_store_stats_reject_request_encode iterations=400000 elapsed_ms=253.450 ops_per_second=1578217.62 nanos_per_op=633.63
remote_store_stats_reject_request_decode iterations=400000 elapsed_ms=250.750 ops_per_second=1595217.37 nanos_per_op=626.87
remote_store_stats_reject_validation iterations=400000 elapsed_ms=253.094 ops_per_second=1580440.54 nanos_per_op=632.73
remote_store_stats_reject_wire_bottleneck_ops_per_second=1578217.62
```

The current remote-store-stats fail-closed boundary bottleneck is request
encode. The payload includes the broadcast request envelope, indices options,
shard filter array, and local flag before admission rejects execution. At
roughly 1.58M ops/s in the latest local release run, this boundary is not a
material transport bottleneck; the first performance-sensitive work is remote
store shard stats collection and response rendering.

Current remote-store-metadata empty-response wire microbenchmark:

```text
cargo run -p os-transport --release --bin remote-store-metadata-reject-wire-benchmark
remote_store_metadata_reject_request_encode iterations=400000 elapsed_ms=261.324 ops_per_second=1530664.17 nanos_per_op=653.31
remote_store_metadata_reject_request_decode iterations=400000 elapsed_ms=247.605 ops_per_second=1615476.14 nanos_per_op=619.01
remote_store_metadata_reject_validation iterations=400000 elapsed_ms=249.019 ops_per_second=1606302.41 nanos_per_op=622.55
remote_store_metadata_reject_wire_bottleneck_ops_per_second=1530664.17
```

The current remote-store-metadata empty-subset boundary bottleneck is request
encode. The request payload includes the broadcast request envelope, indices
options, and shard filter array before admission builds an OpenSearch-shaped
empty broadcast response. At roughly 1.53M ops/s in the latest local release
run, this boundary is not a material transport bottleneck; the first
performance-sensitive work is non-empty remote store shard metadata collection
and response rendering.

Current prune-file-cache reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin prune-file-cache-reject-wire-benchmark
prune_file_cache_reject_request_encode iterations=400000 elapsed_ms=211.141 ops_per_second=1894469.76 nanos_per_op=527.85
prune_file_cache_reject_request_decode iterations=400000 elapsed_ms=201.026 ops_per_second=1989794.16 nanos_per_op=502.56
prune_file_cache_reject_validation iterations=400000 elapsed_ms=200.998 ops_per_second=1990068.57 nanos_per_op=502.50
prune_file_cache_reject_wire_bottleneck_ops_per_second=1894469.76
```

The current prune-file-cache fail-closed boundary bottleneck is request encode.
The payload includes the base nodes request envelope, node selector array,
concrete-node payload marker, and optional timeout before admission rejects
execution. At roughly 1.89M ops/s in the latest local release run, this
boundary is not a material transport bottleneck; the first
performance-sensitive work is warm-node resolution, file cache pruning, and
node response aggregation.

Current reload-secure-settings reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin nodes-reload-secure-settings-reject-wire-benchmark
nodes_reload_secure_settings_reject_request_encode iterations=500000 elapsed_ms=288.656 ops_per_second=1732167.77 nanos_per_op=577.31
nodes_reload_secure_settings_reject_request_decode iterations=500000 elapsed_ms=287.771 ops_per_second=1737490.28 nanos_per_op=575.54
nodes_reload_secure_settings_reject_validation iterations=500000 elapsed_ms=295.404 ops_per_second=1692594.59 nanos_per_op=590.81
nodes_reload_secure_settings_reject_wire_bottleneck_ops_per_second=1692594.59
```

The current reload-secure-settings fail-closed boundary bottleneck is
validation. The payload includes the base nodes request envelope, nullable node
selector array, concrete-node payload marker, optional timeout, and optional
password-bytes marker before admission rejects execution. At roughly 1.69M
ops/s in the latest local release run, this boundary is not a material
transport bottleneck; the first performance-sensitive work is keystore reload,
transport TLS password safety checks, reloadable extension hook execution, and
node response aggregation.

Current put-repository reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-repository-reject-wire-benchmark
put_repository_reject_request_encode iterations=400000 elapsed_ms=216.799 ops_per_second=1845030.30 nanos_per_op=542.00
put_repository_reject_request_decode iterations=400000 elapsed_ms=286.576 ops_per_second=1395788.60 nanos_per_op=716.44
put_repository_reject_validation iterations=400000 elapsed_ms=272.723 ops_per_second=1466689.77 nanos_per_op=681.81
put_repository_reject_wire_bottleneck_ops_per_second=1395788.60
```

The current put-repository fail-closed boundary bottleneck is request decode.
The payload includes the acknowledged cluster-manager request envelope,
repository name/type, OpenSearch settings map, verify flag, and crypto-settings
optional marker before admission rejects execution. At roughly 1.40M ops/s in
the latest local release run, this boundary is not a material transport
bottleneck; the first performance-sensitive work is repository metadata
validation, cluster-state publication, repository verification, and
acknowledgement rendering.

Current nodes-usage wire microbenchmark:

```text
cargo run -p os-transport --release --bin nodes-usage-wire-benchmark
nodes_usage_request_encode iterations=400000 elapsed_ms=205.457 ops_per_second=1946875.60 nanos_per_op=513.64
nodes_usage_request_decode iterations=400000 elapsed_ms=201.323 ops_per_second=1986857.72 nanos_per_op=503.31
nodes_usage_request_validate iterations=400000 elapsed_ms=200.227 ops_per_second=1997731.07 nanos_per_op=500.57
nodes_usage_response_encode iterations=400000 elapsed_ms=576.678 ops_per_second=693628.25 nanos_per_op=1441.69
nodes_usage_response_decode iterations=400000 elapsed_ms=641.297 ops_per_second=623736.31 nanos_per_op=1603.24
nodes_usage_wire_bottleneck_ops_per_second=623736.31
```

The current nodes-usage implemented-path bottleneck is response decode. The
request payload remains compact, but the OpenSearch-shaped response now includes
the BaseNodesResponse envelope plus local DiscoveryNode identity and null usage
maps. At roughly 624k ops/s in the latest local release run, this remains in the
lightweight admin transport range; the next performance-sensitive work is
populating real REST action or aggregation usage telemetry without adding
per-request allocation spikes.

Current nodes-hot-threads implemented-path wire microbenchmark:

```text
cargo run -p os-transport --release --bin nodes-hot-threads-wire-benchmark
nodes_hot_threads_request_encode iterations=400000 elapsed_ms=253.522 ops_per_second=1577771.11 nanos_per_op=633.81
nodes_hot_threads_request_decode iterations=400000 elapsed_ms=250.324 ops_per_second=1597930.05 nanos_per_op=625.81
nodes_hot_threads_request_validate iterations=400000 elapsed_ms=251.848 ops_per_second=1588260.20 nanos_per_op=629.62
nodes_hot_threads_response_encode iterations=400000 elapsed_ms=924.979 ops_per_second=432442.11 nanos_per_op=2312.45
nodes_hot_threads_response_decode iterations=400000 elapsed_ms=1056.059 ops_per_second=378766.76 nanos_per_op=2640.15
nodes_hot_threads_wire_bottleneck_ops_per_second=378766.76
```

The current nodes-hot-threads implemented-path bottleneck is response decode.
The response carries the BaseNodesResponse envelope, local DiscoveryNode
identity, and diagnostic text for the local node. At roughly 379k ops/s in the
latest local release run, this remains lightweight enough for administrative
transport use; future work should keep richer diagnostic rendering off the hot
request parse path.

Current add-voting-config-exclusions reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin add-voting-config-exclusions-reject-wire-benchmark
add_voting_config_exclusions_reject_request_encode iterations=400000 elapsed_ms=257.095 ops_per_second=1555844.38 nanos_per_op=642.74
add_voting_config_exclusions_reject_request_decode iterations=400000 elapsed_ms=286.742 ops_per_second=1394980.48 nanos_per_op=716.86
add_voting_config_exclusions_reject_validation iterations=400000 elapsed_ms=300.496 ops_per_second=1331131.58 nanos_per_op=751.24
add_voting_config_exclusions_reject_wire_bottleneck_ops_per_second=1331131.58
```

The current add-voting-config-exclusions fail-closed boundary bottleneck is
validation over the decoded request. The payload carries three selector arrays
plus two timeout values, and validation counts selector families before failing
closed. At roughly 1.33M ops/s in the latest local release run, this boundary is
not a material transport bottleneck; the first performance-sensitive work is
coordination metadata mutation and voting-configuration convergence tracking.

Current clear-voting-config-exclusions reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin clear-voting-config-exclusions-reject-wire-benchmark
clear_voting_config_exclusions_reject_request_encode iterations=400000 elapsed_ms=262.460 ops_per_second=1524038.94 nanos_per_op=656.15
clear_voting_config_exclusions_reject_request_decode iterations=400000 elapsed_ms=229.685 ops_per_second=1741518.16 nanos_per_op=574.21
clear_voting_config_exclusions_reject_validation iterations=400000 elapsed_ms=228.145 ops_per_second=1753268.47 nanos_per_op=570.36
clear_voting_config_exclusions_reject_wire_bottleneck_ops_per_second=1524038.94
```

The current clear-voting-config-exclusions fail-closed boundary bottleneck is
request encode. The payload writes parent task, cluster-manager timeout,
`waitForRemoval`, and wait timeout before failing closed at admission. At
roughly 1.52M ops/s in the latest local release run, this boundary is not a
material transport bottleneck; the first performance-sensitive work is
coordination metadata mutation and removal tracking.

Current cluster-allocation-explain reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin cluster-allocation-explain-reject-wire-benchmark
cluster_allocation_explain_reject_request_encode iterations=400000 elapsed_ms=242.396 ops_per_second=1650194.88 nanos_per_op=605.99
cluster_allocation_explain_reject_request_decode iterations=400000 elapsed_ms=221.324 ops_per_second=1807305.99 nanos_per_op=553.31
cluster_allocation_explain_reject_validation iterations=400000 elapsed_ms=223.206 ops_per_second=1792069.81 nanos_per_op=558.01
cluster_allocation_explain_reject_wire_bottleneck_ops_per_second=1650194.88
```

The current cluster-allocation-explain fail-closed boundary bottleneck is
request encode. The payload writes parent task, cluster-manager timeout, four
optional selector fields, and two option flags before admission rejects
execution. At roughly 1.65M ops/s in the latest local release run, this boundary
is not a material transport bottleneck; the first performance-sensitive work is
shard routing allocation decision rendering.

Current cluster-update-settings reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin cluster-update-settings-reject-wire-benchmark
cluster_update_settings_reject_request_encode iterations=400000 elapsed_ms=264.946 ops_per_second=1509739.46 nanos_per_op=662.37
cluster_update_settings_reject_request_decode iterations=400000 elapsed_ms=214.076 ops_per_second=1868494.10 nanos_per_op=535.19
cluster_update_settings_reject_validation iterations=400000 elapsed_ms=214.743 ops_per_second=1862692.52 nanos_per_op=536.86
cluster_update_settings_reject_wire_bottleneck_ops_per_second=1509739.46
```

The current cluster-update-settings fail-closed boundary bottleneck is request
encode. The request payload writes the parent task, two timeout values, and the
empty transient/persistent settings maps before failing closed at admission. At
roughly 1.51M ops/s in the latest local release run, it stays in the same range
as the lightweight admin transport boundaries.

Current cluster-reroute reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin cluster-reroute-reject-wire-benchmark
cluster_reroute_reject_request_encode iterations=400000 elapsed_ms=201.057 ops_per_second=1989487.94 nanos_per_op=502.64
cluster_reroute_reject_request_decode iterations=400000 elapsed_ms=185.703 ops_per_second=2153982.47 nanos_per_op=464.26
cluster_reroute_reject_validation iterations=400000 elapsed_ms=188.575 ops_per_second=2121174.19 nanos_per_op=471.44
cluster_reroute_reject_wire_bottleneck_ops_per_second=1989487.94
```

The current cluster-reroute fail-closed boundary bottleneck is request encode
over the parent task, two timeouts, empty allocation-command set, and reroute
flags. At roughly 1.99M ops/s in the latest local release run, this boundary is
not a material performance bottleneck; the first performance-sensitive work is
allocation command execution, routing mutation, and reroute response rendering.

Current get-repositories wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-repositories-wire-benchmark
get_repositories_request_encode iterations=400000 elapsed_ms=194.030 ops_per_second=2061531.79 nanos_per_op=485.08
get_repositories_request_decode iterations=400000 elapsed_ms=191.827 ops_per_second=2085216.78 nanos_per_op=479.57
get_repositories_request_validate iterations=400000 elapsed_ms=192.155 ops_per_second=2081652.16 nanos_per_op=480.39
get_repositories_response_encode iterations=400000 elapsed_ms=85.993 ops_per_second=4651553.58 nanos_per_op=214.98
get_repositories_response_decode iterations=400000 elapsed_ms=89.831 ops_per_second=4452791.35 nanos_per_op=224.58
get_repositories_wire_bottleneck_ops_per_second=2061531.79
```

The current get-repositories implemented-path bottleneck is request encode. The
payload is only the ClusterManagerNodeRead envelope, local flag, and an empty
repository-name array; the empty response is a single repository-list count. At
roughly 2.06M ops/s in the latest local release run, it does not introduce a
transport-wire bottleneck.

Current delete-repository reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-repository-reject-wire-benchmark
delete_repository_reject_request_encode iterations=400000 elapsed_ms=233.755 ops_per_second=1711192.22 nanos_per_op=584.39
delete_repository_reject_request_decode iterations=400000 elapsed_ms=225.736 ops_per_second=1771978.29 nanos_per_op=564.34
delete_repository_reject_validation iterations=400000 elapsed_ms=230.712 ops_per_second=1733765.37 nanos_per_op=576.78
delete_repository_reject_wire_bottleneck_ops_per_second=1711192.22
```

The current delete-repository fail-closed boundary bottleneck is request encode.
The payload includes the acknowledged cluster-manager request envelope and
repository name before admission rejects execution. At roughly 1.71M ops/s in
the latest local release run, this boundary is not a material transport
bottleneck; the first performance-sensitive work is repository metadata
mutation, cluster-state publication, and acknowledgement rendering.

Current verify-repository reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin verify-repository-reject-wire-benchmark
verify_repository_reject_request_encode iterations=400000 elapsed_ms=235.596 ops_per_second=1697822.02 nanos_per_op=588.99
verify_repository_reject_request_decode iterations=400000 elapsed_ms=229.581 ops_per_second=1742304.31 nanos_per_op=573.95
verify_repository_reject_validation iterations=400000 elapsed_ms=234.461 ops_per_second=1706043.69 nanos_per_op=586.15
verify_repository_reject_wire_bottleneck_ops_per_second=1697822.02
```

The current verify-repository fail-closed boundary bottleneck is request encode.
The payload matches the acknowledged cluster-manager request envelope plus
repository name before admission rejects execution. At roughly 1.70M ops/s in
the latest local release run, this boundary is not a material transport
bottleneck; the first performance-sensitive work is repository verification
across nodes and verify response rendering.

Current cleanup-repository reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin cleanup-repository-reject-wire-benchmark
cleanup_repository_reject_request_encode iterations=400000 elapsed_ms=226.638 ops_per_second=1764926.59 nanos_per_op=566.60
cleanup_repository_reject_request_decode iterations=400000 elapsed_ms=246.152 ops_per_second=1625012.81 nanos_per_op=615.38
cleanup_repository_reject_validation iterations=400000 elapsed_ms=225.246 ops_per_second=1775839.75 nanos_per_op=563.11
cleanup_repository_reject_wire_bottleneck_ops_per_second=1625012.81
```

The current cleanup-repository fail-closed boundary bottleneck is request
decode. The payload is only the repository name because the OpenSearch 3.7
request wire implementation does not serialize the acknowledged request
envelope for this action. At roughly 1.63M ops/s in the latest local release
run, this boundary is not a material transport bottleneck; the first
performance-sensitive work is repository cleanup coordination, repository blob
cleanup, and cleanup result rendering.

Current get-snapshots reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-snapshots-reject-wire-benchmark
get_snapshots_reject_request_encode iterations=400000 elapsed_ms=227.563 ops_per_second=1757758.57 nanos_per_op=568.91
get_snapshots_reject_request_decode iterations=400000 elapsed_ms=222.596 ops_per_second=1796978.69 nanos_per_op=556.49
get_snapshots_reject_validation iterations=400000 elapsed_ms=237.968 ops_per_second=1680897.17 nanos_per_op=594.92
get_snapshots_reject_wire_bottleneck_ops_per_second=1680897.17
```

The current get-snapshots fail-closed boundary bottleneck is request
validation. The payload includes the cluster-manager request envelope,
repository name, empty snapshot selector array, `ignoreUnavailable`, and
`verbose` before admission rejects execution. At roughly 1.68M ops/s in the
latest local release run, this boundary is not a material transport bottleneck;
the first performance-sensitive work is repository data loading, current
snapshot resolution, snapshot info loading, and response rendering.

Current delete-snapshot reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-snapshot-reject-wire-benchmark
delete_snapshot_reject_request_encode iterations=400000 elapsed_ms=255.413 ops_per_second=1566090.24 nanos_per_op=638.53
delete_snapshot_reject_request_decode iterations=400000 elapsed_ms=286.485 ops_per_second=1396232.22 nanos_per_op=716.21
delete_snapshot_reject_validation iterations=400000 elapsed_ms=269.831 ops_per_second=1482410.58 nanos_per_op=674.58
delete_snapshot_reject_wire_bottleneck_ops_per_second=1396232.22
```

The current delete-snapshot fail-closed boundary bottleneck is request decode.
The payload includes the cluster-manager request envelope, repository name, and
snapshot name array before admission rejects execution. At roughly 1.40M ops/s
in the latest local release run, this boundary is not a material transport
bottleneck; the first performance-sensitive work is snapshot deletion
coordination, repository cleanup, cluster-state publication, and
acknowledgement rendering.

Current create-snapshot reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin create-snapshot-reject-wire-benchmark
create_snapshot_reject_request_encode iterations=400000 elapsed_ms=304.705 ops_per_second=1312745.33 nanos_per_op=761.76
create_snapshot_reject_request_decode iterations=400000 elapsed_ms=300.166 ops_per_second=1332596.38 nanos_per_op=750.41
create_snapshot_reject_validation iterations=400000 elapsed_ms=306.296 ops_per_second=1305925.59 nanos_per_op=765.74
create_snapshot_reject_wire_bottleneck_ops_per_second=1305925.59
```

The current create-snapshot fail-closed boundary bottleneck is request
validation. The payload includes the cluster-manager request envelope, snapshot
name, repository name, empty index selector array, indices options, settings,
global-state flags, partial/wait flags, and generic user metadata marker before
admission rejects execution. At roughly 1.31M ops/s in the latest local release
run, this boundary is not a material transport bottleneck; the first
performance-sensitive work is snapshot creation coordination, repository write
planning, shard snapshot execution, cluster-state publication, and
create-snapshot response rendering.

Current clone-snapshot reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin clone-snapshot-reject-wire-benchmark
clone_snapshot_reject_request_encode iterations=400000 elapsed_ms=331.051 ops_per_second=1208274.76 nanos_per_op=827.63
clone_snapshot_reject_request_decode iterations=400000 elapsed_ms=349.118 ops_per_second=1145744.88 nanos_per_op=872.79
clone_snapshot_reject_validation iterations=400000 elapsed_ms=363.672 ops_per_second=1099891.01 nanos_per_op=909.18
clone_snapshot_reject_wire_bottleneck_ops_per_second=1099891.01
```

The current clone-snapshot fail-closed boundary bottleneck is request
validation. The payload includes the cluster-manager request envelope,
repository name, source snapshot name, target snapshot name, index selector
array, and indices options before admission rejects execution. At roughly 1.10M
ops/s in the latest local release run, this boundary is not a material
transport bottleneck; the first performance-sensitive work is snapshot clone
coordination, source snapshot metadata loading, index selection, repository
write planning, cluster-state publication, and acknowledgement rendering.

Current restore-snapshot reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin restore-snapshot-reject-wire-benchmark
restore_snapshot_reject_request_encode iterations=400000 elapsed_ms=368.962 ops_per_second=1084122.20 nanos_per_op=922.41
restore_snapshot_reject_request_decode iterations=400000 elapsed_ms=332.305 ops_per_second=1203712.31 nanos_per_op=830.76
restore_snapshot_reject_validation iterations=400000 elapsed_ms=337.415 ops_per_second=1185483.46 nanos_per_op=843.54
restore_snapshot_reject_wire_bottleneck_ops_per_second=1084122.20
```

The current restore-snapshot fail-closed boundary bottleneck is request encode.
The payload includes the cluster-manager request envelope, snapshot and
repository names, index selector array, indices options, rename fields,
restore flags, index settings, ignored settings, snapshot UUID, storage type,
source remote repositories, alias rename fields, and alias write-index policy
before admission rejects execution. At roughly 1.08M ops/s in the latest local
release run, this boundary is not a material transport bottleneck; the first
performance-sensitive work is snapshot restore coordination, repository
snapshot metadata loading, index metadata rewrite, shard restore planning,
cluster-state publication, restore completion tracking, and response rendering.

Current restore-remote-store reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin restore-remote-store-reject-wire-benchmark
restore_remote_store_reject_request_encode iterations=400000 elapsed_ms=289.172 ops_per_second=1383262.15 nanos_per_op=722.93
restore_remote_store_reject_request_decode iterations=400000 elapsed_ms=260.038 ops_per_second=1538233.94 nanos_per_op=650.10
restore_remote_store_reject_validation iterations=400000 elapsed_ms=269.771 ops_per_second=1482737.29 nanos_per_op=674.43
restore_remote_store_accepted_response_decode iterations=400000 elapsed_ms=54.686 ops_per_second=7314470.42 nanos_per_op=136.72
restore_remote_store_reject_wire_bottleneck_ops_per_second=1383262.15
```

The current restore-remote-store fail-closed boundary bottleneck is request
encode. The payload includes the cluster-manager request envelope, index
selector array, optional wait-for-completion flag, and optional
restore-all-shards flag before admission rejects execution. At roughly 1.38M
ops/s in the latest local release run, this boundary is not a material
transport bottleneck; the first performance-sensitive work is remote-store
restore service coordination, shard restore planning, completion listener
registration, `RestoreInfo` decoding, and response rendering.

Current extension-proxy reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin extension-proxy-reject-wire-benchmark
extension_proxy_reject_request_encode iterations=400000 elapsed_ms=201.982 ops_per_second=1980373.42 nanos_per_op=504.96
extension_proxy_reject_request_decode iterations=400000 elapsed_ms=193.443 ops_per_second=2067793.12 nanos_per_op=483.61
extension_proxy_reject_validation iterations=400000 elapsed_ms=194.113 ops_per_second=2060652.91 nanos_per_op=485.28
extension_proxy_response_decode iterations=400000 elapsed_ms=59.317 ops_per_second=6743424.71 nanos_per_op=148.29
extension_proxy_reject_wire_bottleneck_ops_per_second=1980373.42
```

The current extension-proxy fail-closed boundary bottleneck is request encode.
The payload includes the parent task envelope plus the length-prefixed
serialized `ExtensionTransportMessage` bytes before admission rejects
execution. At roughly 1.98M ops/s in the latest local release run, this
boundary is not a material transport bottleneck; the first
performance-sensitive work is extension manager routing, protobuf
`ExtensionTransportMessage` parsing, extension transport dispatch, and byte
response rendering.

Current decommission reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin decommission-reject-wire-benchmark
decommission_reject_request_encode iterations=400000 elapsed_ms=309.881 ops_per_second=1290818.94 nanos_per_op=774.70
decommission_reject_request_decode iterations=400000 elapsed_ms=300.759 ops_per_second=1329970.33 nanos_per_op=751.90
decommission_reject_validation iterations=400000 elapsed_ms=302.457 ops_per_second=1322500.62 nanos_per_op=756.14
decommission_ack_response_decode iterations=400000 elapsed_ms=54.365 ops_per_second=7357715.04 nanos_per_op=135.91
decommission_reject_wire_bottleneck_ops_per_second=1290818.94
```

The current decommission fail-closed boundary bottleneck is request encode.
The payload includes the cluster-manager request envelope, awareness
attribute name/value, delay timeout, `noDelay`, and optional request id before
admission rejects execution. At roughly 1.29M ops/s in the latest local
release run, this boundary is not a material transport bottleneck; the first
performance-sensitive work is decommission metadata mutation, node draining
coordination, cluster-state publication, and acknowledgement rendering.

Current get-decommission-state wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-decommission-state-reject-wire-benchmark
get_decommission_state_request_encode iterations=400000 elapsed_ms=263.703 ops_per_second=1516858.37 nanos_per_op=659.26
get_decommission_state_request_decode iterations=400000 elapsed_ms=243.585 ops_per_second=1642140.32 nanos_per_op=608.96
get_decommission_state_request_validate iterations=400000 elapsed_ms=246.744 ops_per_second=1621111.72 nanos_per_op=616.86
get_decommission_state_response_decode iterations=400000 elapsed_ms=124.701 ops_per_second=3207659.92 nanos_per_op=311.75
get_decommission_state_wire_bottleneck_ops_per_second=1516858.37
```

The current get-decommission-state boundary bottleneck is request encode. The
payload includes the cluster-manager read request envelope, read-local flag,
and awareness attribute name. At roughly 1.52M ops/s in the latest local
release run, this boundary is not a material transport bottleneck; the next
performance-sensitive work is keeping manifest/custom-metadata lookup cheap as
the cluster metadata document grows.

Current delete-decommission-state wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-decommission-state-reject-wire-benchmark
delete_decommission_state_request_encode iterations=400000 elapsed_ms=231.323 ops_per_second=1729184.51 nanos_per_op=578.31
delete_decommission_state_request_decode iterations=400000 elapsed_ms=225.602 ops_per_second=1773032.82 nanos_per_op=564.01
delete_decommission_state_request_validate iterations=400000 elapsed_ms=225.575 ops_per_second=1773246.62 nanos_per_op=563.94
delete_decommission_state_ack_response_decode iterations=400000 elapsed_ms=54.494 ops_per_second=7340220.33 nanos_per_op=136.24
delete_decommission_state_wire_bottleneck_ops_per_second=1729184.51
```

The current delete-decommission-state boundary bottleneck is request encode.
The payload includes only the cluster-manager request envelope before the local
manifest mutation clears decommission state and renders an acknowledgement.
At roughly 1.73M ops/s in the latest local release run, this boundary is not a
material transport bottleneck; the next performance-sensitive work is keeping
manifest mutation and follow-up decommission-state reads cheap as cluster
metadata grows.

Current put-search-pipeline wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-search-pipeline-wire-benchmark
put_search_pipeline_request_encode iterations=400000 elapsed_ms=417.205 ops_per_second=958760.51 nanos_per_op=1043.01
put_search_pipeline_request_decode iterations=400000 elapsed_ms=369.173 ops_per_second=1083503.23 nanos_per_op=922.93
put_search_pipeline_request_validate iterations=400000 elapsed_ms=370.433 ops_per_second=1079817.27 nanos_per_op=926.08
put_search_pipeline_response_decode iterations=400000 elapsed_ms=55.314 ops_per_second=7231393.55 nanos_per_op=138.29
put_search_pipeline_wire_bottleneck_ops_per_second=958760.51
```

The current put-search-pipeline wire bottleneck is request encode. The payload
includes the cluster-manager request envelope, acknowledgement timeout,
pipeline id, source bytes, and media type string before the node route parses
and stores the JSON source in the metadata manifest. At roughly 0.96M ops/s in
the latest local release run, this boundary is not a material transport
bottleneck; the first performance-sensitive work is keeping manifest mutation
and follow-up search-pipeline reads cheap as metadata grows.

Current get-search-pipeline wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-search-pipeline-reject-wire-benchmark
get_search_pipeline_reject_request_encode iterations=400000 elapsed_ms=278.774 ops_per_second=1434855.43 nanos_per_op=696.93
get_search_pipeline_reject_request_decode iterations=400000 elapsed_ms=258.461 ops_per_second=1547619.52 nanos_per_op=646.15
get_search_pipeline_reject_validation iterations=400000 elapsed_ms=259.333 ops_per_second=1542420.18 nanos_per_op=648.33
get_search_pipeline_response_decode iterations=400000 elapsed_ms=227.618 ops_per_second=1757330.80 nanos_per_op=569.04
get_search_pipeline_reject_wire_bottleneck_ops_per_second=1434855.43
```

The current get-search-pipeline implemented read-path bottleneck is request
encode. The payload includes the cluster-manager read request envelope, local
flag, and pipeline id selectors before manifest-backed response rendering. At
roughly 1.43M ops/s in the latest local release run, this boundary is not a
material transport bottleneck; the remaining production-sensitive work is
authoritative cluster-state search pipeline lookup and local read semantics.

Current delete-search-pipeline wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-search-pipeline-reject-wire-benchmark
delete_search_pipeline_request_encode iterations=400000 elapsed_ms=276.082 ops_per_second=1448847.09 nanos_per_op=690.20
delete_search_pipeline_request_decode iterations=400000 elapsed_ms=260.658 ops_per_second=1534576.95 nanos_per_op=651.65
delete_search_pipeline_request_validate iterations=400000 elapsed_ms=263.984 ops_per_second=1515245.25 nanos_per_op=659.96
delete_search_pipeline_ack_response_decode iterations=400000 elapsed_ms=53.844 ops_per_second=7428864.17 nanos_per_op=134.61
delete_search_pipeline_wire_bottleneck_ops_per_second=1448847.09
```

The current delete-search-pipeline boundary bottleneck is request encode. The
payload includes the acknowledged cluster-manager request envelope and pipeline
id before the local manifest mutation removes exact or wildcard-matched
pipelines and renders an acknowledgement. At roughly 1.45M ops/s in the latest
local release run, this boundary is not a material transport bottleneck; the
next performance-sensitive work is keeping wildcard matching and manifest
mutation cheap as search pipeline metadata grows.

Current pause-ingestion reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin pause-ingestion-reject-wire-benchmark
pause_ingestion_reject_request_encode iterations=400000 elapsed_ms=361.438 ops_per_second=1106690.45 nanos_per_op=903.60
pause_ingestion_reject_request_decode iterations=400000 elapsed_ms=294.170 ops_per_second=1359759.53 nanos_per_op=735.42
pause_ingestion_reject_validation iterations=400000 elapsed_ms=291.013 ops_per_second=1374510.41 nanos_per_op=727.53
pause_ingestion_response_decode iterations=400000 elapsed_ms=65.463 ops_per_second=6110293.95 nanos_per_op=163.66
pause_ingestion_reject_wire_bottleneck_ops_per_second=1106690.45
```

The current pause-ingestion fail-closed boundary bottleneck is request encode.
The payload includes the acknowledged cluster-manager request envelope, index
selector array, and strict-expand-open index options before admission rejects
execution. At roughly 1.11M ops/s in the latest local release run, this
boundary is not a material transport bottleneck; the first performance-sensitive
work is destructive-index guard checks, index resolution, ingestion poller state
mutation, shard acknowledgement aggregation, and response rendering.

Current resume-ingestion reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin resume-ingestion-reject-wire-benchmark
resume_ingestion_reject_request_encode iterations=400000 elapsed_ms=307.230 ops_per_second=1301957.12 nanos_per_op=768.07
resume_ingestion_reject_request_decode iterations=400000 elapsed_ms=296.537 ops_per_second=1348902.18 nanos_per_op=741.34
resume_ingestion_reject_validation iterations=400000 elapsed_ms=304.163 ops_per_second=1315084.73 nanos_per_op=760.41
resume_ingestion_response_decode iterations=400000 elapsed_ms=65.078 ops_per_second=6146495.42 nanos_per_op=162.69
resume_ingestion_reject_wire_bottleneck_ops_per_second=1301957.12
```

The current resume-ingestion fail-closed boundary bottleneck is request encode.
The payload includes the acknowledged cluster-manager request envelope, index
selector array, strict-expand-open index options, and empty reset-settings array
before admission rejects execution. At roughly 1.30M ops/s in the latest local
release run, this boundary is not a material transport bottleneck; the first
performance-sensitive work is destructive-index guard checks, index resolution,
optional shard pointer reset, ingestion poller state mutation, shard
acknowledgement aggregation, and response rendering.

Current get-ingestion-state reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-ingestion-state-reject-wire-benchmark
get_ingestion_state_reject_request_encode iterations=400000 elapsed_ms=314.557 ops_per_second=1271628.82 nanos_per_op=786.39
get_ingestion_state_reject_request_decode iterations=400000 elapsed_ms=333.698 ops_per_second=1198689.01 nanos_per_op=834.24
get_ingestion_state_reject_validation iterations=400000 elapsed_ms=365.699 ops_per_second=1093796.22 nanos_per_op=914.25
get_ingestion_state_response_decode iterations=400000 elapsed_ms=66.428 ops_per_second=6021515.75 nanos_per_op=166.07
get_ingestion_state_reject_wire_bottleneck_ops_per_second=1093796.22
```

The current get-ingestion-state fail-closed boundary bottleneck is request
validation. The admission path checks duplicate index selectors, default index
resolution options, shard selectors, and page params before rejecting execution.
At roughly 1.09M ops/s in the latest local release run, this boundary is not a
material transport bottleneck; the first performance-sensitive work is broadcast
shard selection, optional cluster-state pagination, shard ingestion-state
collection, shard failure aggregation, and response rendering.

Current update-ingestion-state reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin update-ingestion-state-reject-wire-benchmark
update_ingestion_state_reject_request_encode iterations=400000 elapsed_ms=373.487 ops_per_second=1070989.09 nanos_per_op=933.72
update_ingestion_state_reject_request_decode iterations=400000 elapsed_ms=357.336 ops_per_second=1119394.44 nanos_per_op=893.34
update_ingestion_state_reject_validation iterations=400000 elapsed_ms=372.755 ops_per_second=1073090.43 nanos_per_op=931.89
update_ingestion_state_response_decode iterations=400000 elapsed_ms=70.777 ops_per_second=5651548.52 nanos_per_op=176.94
update_ingestion_state_reject_wire_bottleneck_ops_per_second=1070989.09
```

The current update-ingestion-state fail-closed boundary bottleneck is request
encode. The payload includes the broadcast request envelope, broadcast index
selectors, target index selectors, shard selector array, optional paused-state
byte, and optional reset-settings marker before admission rejects execution. At
roughly 1.07M ops/s in the latest local release run, this boundary is not a
material transport bottleneck; the first performance-sensitive work is broadcast
shard selection, metadata write block checks, shard pointer reset, ingestion
paused-state mutation, shard failure aggregation, and response rendering.

Current list-tiering-status reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin list-tiering-status-reject-wire-benchmark
list_tiering_status_reject_request_encode iterations=400000 elapsed_ms=196.115 ops_per_second=2039619.63 nanos_per_op=490.29
list_tiering_status_reject_request_decode iterations=400000 elapsed_ms=183.921 ops_per_second=2174843.92 nanos_per_op=459.80
list_tiering_status_reject_validation iterations=400000 elapsed_ms=189.032 ops_per_second=2116044.17 nanos_per_op=472.58
list_tiering_status_response_decode iterations=400000 elapsed_ms=59.608 ops_per_second=6710535.79 nanos_per_op=149.02
list_tiering_status_reject_wire_bottleneck_ops_per_second=2039619.63
```

The current list-tiering-status fail-closed boundary bottleneck is request
encode. The payload includes the cluster-manager read envelope, local-read flag,
and optional target tier before admission rejects execution. At roughly 2.04M
ops/s in the latest local release run, this boundary is not a material transport
bottleneck; the first performance-sensitive work is metadata read block checks,
target tier mapping, migration service lookup, tiering status aggregation, and
response rendering.

Current get-tiering-status reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-tiering-status-reject-wire-benchmark
get_tiering_status_reject_request_encode iterations=400000 elapsed_ms=263.495 ops_per_second=1518052.61 nanos_per_op=658.74
get_tiering_status_reject_request_decode iterations=400000 elapsed_ms=232.113 ops_per_second=1723301.69 nanos_per_op=580.28
get_tiering_status_reject_validation iterations=400000 elapsed_ms=236.959 ops_per_second=1688055.85 nanos_per_op=592.40
get_tiering_status_response_decode iterations=400000 elapsed_ms=241.764 ops_per_second=1654505.01 nanos_per_op=604.41
get_tiering_status_reject_wire_bottleneck_ops_per_second=1518052.61
```

The current get-tiering-status fail-closed boundary bottleneck is request
encode. The payload includes the cluster-manager read envelope, local-read flag,
index name, and detailed flag before admission rejects execution. At roughly
1.52M ops/s in the latest local release run, this boundary is not a material
transport bottleneck; the first performance-sensitive work is metadata read
block checks, index resolution, tiering-state lookup, migration service lookup,
optional shard-level detail collection, and response rendering.

Current knn-stats reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin knn-stats-reject-wire-benchmark
knn_stats_request_wire_shape valid_stats=41 requested_stats=0 body_bytes=854
knn_stats_request_body_encode iterations=400000 elapsed_ms=2827.204 ops_per_second=141482.52 nanos_per_op=7068.01
knn_stats_reject_request_encode iterations=400000 elapsed_ms=2974.828 ops_per_second=134461.54 nanos_per_op=7437.07
knn_stats_frame_decode iterations=400000 elapsed_ms=65.373 ops_per_second=6118705.95 nanos_per_op=163.43
knn_stats_request_body_decode iterations=400000 elapsed_ms=2767.834 ops_per_second=144517.36 nanos_per_op=6919.58
knn_stats_reject_request_decode iterations=400000 elapsed_ms=2983.762 ops_per_second=134058.94 nanos_per_op=7459.41
knn_stats_validation_only iterations=400000 elapsed_ms=112.184 ops_per_second=3565577.65 nanos_per_op=280.46
knn_stats_reject_validation iterations=400000 elapsed_ms=3094.655 ops_per_second=129255.10 nanos_per_op=7736.64
knn_stats_response_encode iterations=400000 elapsed_ms=91.554 ops_per_second=4369001.02 nanos_per_op=228.89
knn_stats_response_decode iterations=400000 elapsed_ms=98.825 ops_per_second=4047567.91 nanos_per_op=247.06
knn_stats_reject_wire_bottleneck_ops_per_second=129255.10
knn_stats_diagnosed_stage_bottleneck_ops_per_second=141482.52
```

The current knn-stats fail-closed boundary bottleneck is request body
encode/decode of the 854-byte payload carrying 41 valid stat names. Frame
decode is roughly 6.12M ops/s, response encode/decode is roughly 4.37M/4.05M
ops/s, and validation-only is roughly 3.57M ops/s, so validation and empty
response rendering are not the material hotspots. The node transport receiver
now has an OpenSearch-shaped empty response path for
`cluster:admin/knn_stats_action`, which is enough to avoid a generic empty
transport response at this boundary. The next meaningful optimization would
need to avoid repeated stat-name payload allocation/copying in the wire path or
move beyond admission into real BaseNodes execution. The first semantic work
remains BaseNodes fanout, node-level KNN stat collection, cluster-level stat
aggregation, failure aggregation, and response rendering.

Current knn-warmup reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin knn-warmup-reject-wire-benchmark
knn_warmup_reject_request_encode iterations=400000 elapsed_ms=319.007 ops_per_second=1253890.17 nanos_per_op=797.52
knn_warmup_reject_request_decode iterations=400000 elapsed_ms=287.917 ops_per_second=1389288.34 nanos_per_op=719.79
knn_warmup_reject_validation iterations=400000 elapsed_ms=294.781 ops_per_second=1356939.84 nanos_per_op=736.95
knn_warmup_response_decode iterations=400000 elapsed_ms=58.868 ops_per_second=6794877.51 nanos_per_op=147.17
knn_warmup_reject_wire_bottleneck_ops_per_second=1253890.17
```

The current knn-warmup fail-closed boundary bottleneck is request encode. The
payload includes the broadcast parent task, nullable index selector array, and
strict-expand-open-forbid-closed index options before admission rejects
execution. At roughly 1.25M ops/s in the latest local release run, this boundary
is not a material transport bottleneck; the first performance-sensitive work is
broadcast shard selection, metadata read block checks, per-shard KNN warmup,
shard failure aggregation, and response rendering.

Current update-model-metadata reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin update-model-metadata-reject-wire-benchmark
update_model_metadata_reject_request_encode iterations=400000 elapsed_ms=322.144 ops_per_second=1241681.38 nanos_per_op=805.36
update_model_metadata_reject_request_decode iterations=400000 elapsed_ms=288.566 ops_per_second=1386163.36 nanos_per_op=721.42
update_model_metadata_reject_validation iterations=400000 elapsed_ms=292.944 ops_per_second=1365449.63 nanos_per_op=732.36
update_model_metadata_response_decode iterations=400000 elapsed_ms=55.010 ops_per_second=7271421.33 nanos_per_op=137.52
update_model_metadata_reject_wire_bottleneck_ops_per_second=1241681.38
```

The current update-model-metadata fail-closed boundary bottleneck is request
encode. The payload includes the cluster-manager parent task, cluster-manager
timeout, acknowledgement timeout, model id, remove flag, and opaque model
metadata body presence before admission rejects execution. At roughly 1.24M
ops/s in the latest local release run, this boundary is not a material
transport bottleneck; the first performance-sensitive work is model metadata
validation, model system-index custom metadata mutation, cluster-state
publication, and acknowledgement rendering.

Current training-job-route-decision-info reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin training-job-route-decision-info-reject-wire-benchmark
training_job_route_decision_info_reject_request_encode iterations=400000 elapsed_ms=299.238 ops_per_second=1336729.20 nanos_per_op=748.09
training_job_route_decision_info_reject_request_decode iterations=400000 elapsed_ms=254.428 ops_per_second=1572154.75 nanos_per_op=636.07
training_job_route_decision_info_reject_validation iterations=400000 elapsed_ms=254.592 ops_per_second=1571141.76 nanos_per_op=636.48
training_job_route_decision_info_response_decode iterations=400000 elapsed_ms=97.933 ops_per_second=4084440.96 nanos_per_op=244.83
training_job_route_decision_info_reject_wire_bottleneck_ops_per_second=1336729.20
```

The current training-job-route-decision-info fail-closed boundary bottleneck is
request encode. The payload includes the BaseNodes parent task, nullable node id
selector, concrete-node marker, and optional timeout before admission rejects
execution. At roughly 1.34M ops/s in the latest local release run, this boundary
is not a material transport bottleneck; the first performance-sensitive work is
BaseNodes fanout, node-level training job count collection, failure
aggregation, and response rendering.

Current get-model reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-model-reject-wire-benchmark
get_model_reject_request_encode iterations=400000 elapsed_ms=281.684 ops_per_second=1420029.96 nanos_per_op=704.21
get_model_reject_request_decode iterations=400000 elapsed_ms=299.517 ops_per_second=1335482.89 nanos_per_op=748.79
get_model_reject_validation iterations=400000 elapsed_ms=252.445 ops_per_second=1584506.57 nanos_per_op=631.11
get_model_response_decode iterations=400000 elapsed_ms=65.162 ops_per_second=6138586.67 nanos_per_op=162.90
get_model_reject_wire_bottleneck_ops_per_second=1335482.89
```

The current get-model fail-closed boundary bottleneck is request decode. The
payload includes the parent task and model id before admission rejects
execution; the response path only detects model payload presence and treats the
full `Model` body as opaque. At roughly 1.34M ops/s in the latest local release
run, this boundary is not a material transport bottleneck; the first
performance-sensitive work is model system-index lookup, KNN `ModelMetadata`
parsing, optional model blob handling, model id rendering, and response
rendering.

Current delete-model reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-model-reject-wire-benchmark
delete_model_reject_request_encode iterations=400000 elapsed_ms=265.412 ops_per_second=1507092.25 nanos_per_op=663.53
delete_model_reject_request_decode iterations=400000 elapsed_ms=260.627 ops_per_second=1534759.29 nanos_per_op=651.57
delete_model_reject_validation iterations=400000 elapsed_ms=265.852 ops_per_second=1504599.04 nanos_per_op=664.63
delete_model_response_decode iterations=400000 elapsed_ms=136.680 ops_per_second=2926534.01 nanos_per_op=341.70
delete_model_reject_wire_bottleneck_ops_per_second=1504599.04
```

The current delete-model fail-closed boundary bottleneck is validation including
request decode. The payload includes the parent task and model id before
admission rejects execution; the response path decodes model id, result, and an
optional deprecated error message. At roughly 1.50M ops/s in the latest local
release run, this boundary is not a material transport bottleneck; the first
performance-sensitive work is model id validation, model system-index delete,
model cache/graveyard coordination, exception-path behavior, and response
rendering.

Current training-job-router reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin training-job-router-reject-wire-benchmark
training_job_router_reject_request_encode iterations=400000 elapsed_ms=629.798 ops_per_second=635124.04 nanos_per_op=1574.50
training_job_router_reject_request_decode iterations=400000 elapsed_ms=306.719 ops_per_second=1304127.39 nanos_per_op=766.80
training_job_router_reject_validation iterations=400000 elapsed_ms=293.100 ops_per_second=1364721.50 nanos_per_op=732.75
training_job_router_response_decode iterations=400000 elapsed_ms=97.427 ops_per_second=4105629.56 nanos_per_op=243.57
training_job_router_reject_wire_bottleneck_ops_per_second=635124.04
```

The current training-job-router fail-closed boundary bottleneck is request
encode. The payload includes the parent task, optional model id, and an opaque
training request payload stand-in before admission rejects execution. At roughly
635k ops/s in the latest local release run, this boundary is the current
k-NN action wire hotspot to watch; the first performance-sensitive work is
training index sizing, training config validation, route-decision fanout, node
selection, forwarding to `TrainingModelAction`, and response rendering.

Current training-model reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin training-model-reject-wire-benchmark
training_model_reject_request_encode iterations=400000 elapsed_ms=614.546 ops_per_second=650886.60 nanos_per_op=1536.37
training_model_reject_request_decode iterations=400000 elapsed_ms=273.319 ops_per_second=1463489.39 nanos_per_op=683.30
training_model_reject_validation iterations=400000 elapsed_ms=272.993 ops_per_second=1465241.14 nanos_per_op=682.48
training_model_response_decode iterations=400000 elapsed_ms=98.172 ops_per_second=4074480.32 nanos_per_op=245.43
training_model_reject_wire_bottleneck_ops_per_second=650886.60
```

The current training-model fail-closed boundary bottleneck is request encode.
The payload includes the parent task, optional model id, and an opaque training
request payload stand-in before admission rejects execution. At roughly 651k
ops/s in the latest local release run, this boundary is near the
training-job-router wire cost; the first performance-sensitive work is KNN
native training data loading, memory reservation, training job execution, model
system-index write, counter updates, and response rendering.

Current remove-model-from-cache reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin remove-model-from-cache-reject-wire-benchmark
remove_model_from_cache_reject_request_encode iterations=400000 elapsed_ms=317.879 ops_per_second=1258339.12 nanos_per_op=794.70
remove_model_from_cache_reject_request_decode iterations=400000 elapsed_ms=289.042 ops_per_second=1383879.90 nanos_per_op=722.61
remove_model_from_cache_reject_validation iterations=400000 elapsed_ms=293.611 ops_per_second=1362344.99 nanos_per_op=734.03
remove_model_from_cache_response_decode iterations=400000 elapsed_ms=97.761 ops_per_second=4091616.41 nanos_per_op=244.40
remove_model_from_cache_reject_wire_bottleneck_ops_per_second=1258339.12
```

The current remove-model-from-cache fail-closed boundary bottleneck is request
encode. The payload includes the parent task, node selector envelope, timeout
envelope, and model id before admission rejects execution. At roughly 1.26M
ops/s in the latest local release run, this boundary is lighter than the
training request wire paths; the first performance-sensitive work is BaseNodes
fanout, per-node model cache eviction, failure aggregation, and response
rendering.

Current search-model reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin search-model-reject-wire-benchmark
search_model_reject_request_encode iterations=400000 elapsed_ms=289.154 ops_per_second=1383347.84 nanos_per_op=722.88
search_model_reject_request_decode iterations=400000 elapsed_ms=280.861 ops_per_second=1424193.88 nanos_per_op=702.15
search_model_reject_validation iterations=400000 elapsed_ms=286.751 ops_per_second=1394939.38 nanos_per_op=716.88
search_model_response_decode iterations=400000 elapsed_ms=37.900 ops_per_second=10554157.66 nanos_per_op=94.75
search_model_reject_wire_bottleneck_ops_per_second=1383347.84
```

The current search-model fail-closed boundary bottleneck is request encode. The
payload is the OpenSearch core `SearchRequest` envelope before admission rejects
execution. At roughly 1.38M ops/s in the latest local release run, this boundary
is lighter than the training request wire paths; the first performance-sensitive
work is model system-index search request mapping, `SearchRequest` source
parsing, `ModelDao` search delegation, `SearchResponse` decoding, and response
rendering.

Current update-model-graveyard reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin update-model-graveyard-reject-wire-benchmark
update_model_graveyard_reject_request_encode iterations=400000 elapsed_ms=334.017 ops_per_second=1197542.47 nanos_per_op=835.04
update_model_graveyard_reject_request_decode iterations=400000 elapsed_ms=293.100 ops_per_second=1364721.05 nanos_per_op=732.75
update_model_graveyard_reject_validation iterations=400000 elapsed_ms=298.628 ops_per_second=1339459.11 nanos_per_op=746.57
update_model_graveyard_response_decode iterations=400000 elapsed_ms=55.382 ops_per_second=7222515.43 nanos_per_op=138.46
update_model_graveyard_reject_wire_bottleneck_ops_per_second=1197542.47
```

The current update-model-graveyard fail-closed boundary bottleneck is request
encode. The payload includes the acknowledged request timeouts, model id, and
remove flag before admission rejects execution. At roughly 1.20M ops/s in the
latest local release run, this boundary is lighter than the training request
wire paths; the first performance-sensitive work is cluster-manager state update
submission, model graveyard metadata mutation, model usage mapping scan,
delete-model conflict handling, cluster-state publication, and acknowledgement
rendering.

Current clear-cache reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin clear-cache-reject-wire-benchmark
clear_cache_reject_request_encode iterations=400000 elapsed_ms=306.273 ops_per_second=1306026.33 nanos_per_op=765.68
clear_cache_reject_request_decode iterations=400000 elapsed_ms=292.863 ops_per_second=1365826.29 nanos_per_op=732.16
clear_cache_reject_validation iterations=400000 elapsed_ms=347.126 ops_per_second=1152317.86 nanos_per_op=867.82
clear_cache_response_decode iterations=400000 elapsed_ms=59.785 ops_per_second=6690591.66 nanos_per_op=149.46
clear_cache_reject_wire_bottleneck_ops_per_second=1152317.86
```

The current clear-cache fail-closed boundary bottleneck is validation including
request decode. The payload includes the broadcast request index selectors and
index resolution options before admission rejects execution. At roughly 1.15M
ops/s in the latest local release run, this boundary is lighter than the
training request wire paths; the first performance-sensitive work is index
resolution, KNN index validation, broadcast shard selection, per-shard KNN cache
eviction, shard failure aggregation, and response rendering.

Current snapshots-status reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin snapshots-status-reject-wire-benchmark
snapshots_status_reject_request_encode iterations=400000 elapsed_ms=239.090 ops_per_second=1673009.84 nanos_per_op=597.73
snapshots_status_reject_request_decode iterations=400000 elapsed_ms=233.764 ops_per_second=1711128.08 nanos_per_op=584.41
snapshots_status_reject_validation iterations=400000 elapsed_ms=240.149 ops_per_second=1665629.71 nanos_per_op=600.37
snapshots_status_reject_wire_bottleneck_ops_per_second=1665629.71
```

The current snapshots-status fail-closed boundary bottleneck is request
validation. The payload includes the cluster-manager request envelope,
repository name, snapshot selector array, `ignoreUnavailable`, and optional
index selector array before admission rejects execution. At roughly 1.67M
ops/s in the latest local release run, this boundary is not a material
transport bottleneck; the first performance-sensitive work is current snapshot
resolution, repository snapshot status loading, node shard status collection,
index filtering, and response rendering.

Current add-weighted-routing reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin add-weighted-routing-reject-wire-benchmark
add_weighted_routing_reject_request_encode iterations=400000 elapsed_ms=436.232 ops_per_second=916942.48 nanos_per_op=1090.58
add_weighted_routing_reject_request_decode iterations=400000 elapsed_ms=394.996 ops_per_second=1012669.53 nanos_per_op=987.49
add_weighted_routing_reject_validation iterations=400000 elapsed_ms=415.157 ops_per_second=963490.59 nanos_per_op=1037.89
add_weighted_routing_reject_wire_bottleneck_ops_per_second=916942.48
```

The current add-weighted-routing fail-closed boundary bottleneck is request
encode. The payload includes the cluster-manager request envelope, weighted
routing awareness attribute name, OpenSearch generic string-to-double weights
map, and weighted routing version before admission rejects execution. At
roughly 917K ops/s in the latest local release run, this boundary is not the
primary expected performance risk; the first performance-sensitive work is
awareness attribute verification, version-conflict checks, weighted routing
metadata mutation, cluster-state publication, and acknowledgement rendering.

Current get-weighted-routing wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-weighted-routing-reject-wire-benchmark
get_weighted_routing_reject_request_encode iterations=400000 elapsed_ms=299.943 ops_per_second=1333584.66 nanos_per_op=749.86
get_weighted_routing_reject_request_decode iterations=400000 elapsed_ms=300.937 ops_per_second=1329182.06 nanos_per_op=752.34
get_weighted_routing_reject_validation iterations=400000 elapsed_ms=305.960 ops_per_second=1307359.58 nanos_per_op=764.90
get_weighted_routing_reject_wire_bottleneck_ops_per_second=1307359.58
```

The current get-weighted-routing implemented read-path bottleneck is request
validation. The payload includes the cluster-manager read request envelope,
local flag, and awareness attribute name before manifest-backed response
rendering. At roughly 1.31M ops/s in the latest local release run, this
boundary is not the primary expected performance risk; the remaining
production-sensitive work is authoritative cluster-state weighted-routing
lookup and local read semantics.

Current delete-weighted-routing reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-weighted-routing-reject-wire-benchmark
delete_weighted_routing_reject_request_encode iterations=400000 elapsed_ms=367.886 ops_per_second=1087294.18 nanos_per_op=919.71
delete_weighted_routing_reject_request_decode iterations=400000 elapsed_ms=314.900 ops_per_second=1270245.61 nanos_per_op=787.25
delete_weighted_routing_reject_validation iterations=400000 elapsed_ms=322.649 ops_per_second=1239735.90 nanos_per_op=806.62
delete_weighted_routing_reject_wire_bottleneck_ops_per_second=1087294.18
```

The current delete-weighted-routing fail-closed boundary bottleneck is request
encode. The payload includes the cluster-manager request envelope, weighted
routing version, and optional trailing awareness attribute before admission
rejects execution. At roughly 1.09M ops/s in the latest local release run, this
boundary is not the primary expected performance risk; the first
performance-sensitive work is version-conflict handling, weighted routing
metadata deletion, cluster-state publication, and acknowledgement rendering.

Current get-mappings wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-mappings-wire-benchmark
get_mappings_request_encode iterations=400000 elapsed_ms=227.536 ops_per_second=1757964.64 nanos_per_op=568.84
get_mappings_request_decode iterations=400000 elapsed_ms=223.413 ops_per_second=1790407.21 nanos_per_op=558.53
get_mappings_request_validate iterations=400000 elapsed_ms=226.847 ops_per_second=1763304.45 nanos_per_op=567.12
get_mappings_response_encode iterations=400000 elapsed_ms=85.259 ops_per_second=4691560.29 nanos_per_op=213.15
get_mappings_response_decode iterations=400000 elapsed_ms=93.764 ops_per_second=4266027.65 nanos_per_op=234.41
get_mappings_wire_bottleneck_ops_per_second=1757964.64
```

The current get-mappings fail-closed boundary bottleneck is request encode. The
payload adds the local flag and `IndicesOptions.strictExpandOpen()` to the
ClusterManagerNodeRead envelope and empty index array, so it is slightly heavier
than get-repositories but still inside the lightweight admin transport range at
roughly 1.70M ops/s in the latest local release run.

Current get-field-mappings wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-field-mappings-wire-benchmark
get_field_mappings_request_encode iterations=400000 elapsed_ms=260.155 ops_per_second=1537545.72 nanos_per_op=650.39
get_field_mappings_request_decode iterations=400000 elapsed_ms=241.861 ops_per_second=1653839.74 nanos_per_op=604.65
get_field_mappings_request_validate iterations=400000 elapsed_ms=243.219 ops_per_second=1644606.62 nanos_per_op=608.05
get_field_mappings_response_encode iterations=400000 elapsed_ms=86.822 ops_per_second=4607104.78 nanos_per_op=217.06
get_field_mappings_response_decode iterations=400000 elapsed_ms=93.420 ops_per_second=4281736.19 nanos_per_op=233.55
get_field_mappings_wire_bottleneck_ops_per_second=1537545.72
```

The current get-field-mappings fail-closed boundary bottleneck is request
encode. This path checks indices options, local execution, field filters,
and include-default expansion after reading the OpenSearch 3.x request body, so
it is slightly heavier than get-mappings. At roughly 1.55M ops/s in the latest
local release run, it remains in the lightweight admin transport range.

Current put-mapping wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-mapping-wire-benchmark
put_mapping_request_encode iterations=400000 elapsed_ms=368.880 ops_per_second=1084363.85 nanos_per_op=922.20
put_mapping_request_decode iterations=400000 elapsed_ms=347.404 ops_per_second=1151397.66 nanos_per_op=868.51
put_mapping_request_validate iterations=400000 elapsed_ms=357.068 ops_per_second=1120234.17 nanos_per_op=892.67
put_mapping_response_encode iterations=400000 elapsed_ms=90.144 ops_per_second=4437345.73 nanos_per_op=225.36
put_mapping_response_decode iterations=400000 elapsed_ms=92.161 ops_per_second=4340251.55 nanos_per_op=230.40
put_mapping_wire_bottleneck_ops_per_second=1084363.85
```

The current put-mapping transport path bottleneck is request encode. The path
writes the acknowledged-request envelope, index target array, indices options,
mapping source string, absent concrete-index marker, origin marker, and
`writeIndexOnly` flag, then validates the supported local metadata mutation
subset and renders an acknowledged response. At roughly 1.08M ops/s in the
latest local release run, the first runtime performance point to inspect while
expanding the path is repeated manifest target resolution and mapping-source
JSON subset extraction for larger multi-index updates.

Current auto-put-mapping wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin auto-put-mapping-wire-benchmark
auto_put_mapping_request_encode iterations=400000 elapsed_ms=398.314 ops_per_second=1004231.79 nanos_per_op=995.79
auto_put_mapping_request_decode iterations=400000 elapsed_ms=392.870 ops_per_second=1018149.11 nanos_per_op=982.17
auto_put_mapping_request_validate iterations=400000 elapsed_ms=401.949 ops_per_second=995151.00 nanos_per_op=1004.87
auto_put_mapping_response_encode iterations=400000 elapsed_ms=86.630 ops_per_second=4617332.72 nanos_per_op=216.58
auto_put_mapping_response_decode iterations=400000 elapsed_ms=89.145 ops_per_second=4487057.28 nanos_per_op=222.86
auto_put_mapping_wire_bottleneck_ops_per_second=995151.00
```

The current auto-put-mapping transport path bottleneck is request validation.
The path reuses the put-mapping request body, requires a concrete index,
validates OpenSearch's zero acknowledgement timeout for automatic mapping
updates, and then applies the same manifest-backed mapping merge as put-mapping
before rendering an acknowledged response. At roughly 0.995M ops/s in the latest
local release run, future performance-sensitive work is the manifest lookup and
mapping compatibility path for larger dynamic mapping updates.

Current indices-aliases wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin indices-aliases-wire-benchmark
indices_aliases_request_encode iterations=400000 elapsed_ms=379.336 ops_per_second=1054474.63 nanos_per_op=948.34
indices_aliases_request_decode iterations=400000 elapsed_ms=404.375 ops_per_second=989180.10 nanos_per_op=1010.94
indices_aliases_request_validate iterations=400000 elapsed_ms=429.183 ops_per_second=932003.16 nanos_per_op=1072.96
indices_aliases_response_encode iterations=400000 elapsed_ms=87.276 ops_per_second=4583141.30 nanos_per_op=218.19
indices_aliases_response_decode iterations=400000 elapsed_ms=87.990 ops_per_second=4545967.46 nanos_per_op=219.98
indices_aliases_wire_bottleneck_ops_per_second=932003.16
```

The current indices-aliases transport path bottleneck is request validation.
The path decodes one alias add action, checks default timeouts, origin, action
presence, required index and alias fields, and unsupported alias options before
the node applies manifest-backed add/remove mutations and renders an
acknowledged response. At roughly 0.93M ops/s in the latest local release run,
the wire overhead remains lightweight shape validation; future
performance-sensitive work is the manifest index resolution and metadata
mutation path for larger alias action batches.

Current index update-settings wire microbenchmark:

```text
cargo run -p os-transport --release --bin update-settings-wire-benchmark
update_settings_request_encode iterations=400000 elapsed_ms=415.689 ops_per_second=962258.04 nanos_per_op=1039.22
update_settings_request_decode iterations=400000 elapsed_ms=393.626 ops_per_second=1016193.59 nanos_per_op=984.06
update_settings_request_validate iterations=400000 elapsed_ms=408.251 ops_per_second=979789.10 nanos_per_op=1020.63
update_settings_response_encode iterations=400000 elapsed_ms=48.943 ops_per_second=8172708.12 nanos_per_op=122.36
update_settings_response_decode iterations=400000 elapsed_ms=53.942 ops_per_second=7415351.03 nanos_per_op=134.86
update_settings_wire_bottleneck_ops_per_second=962258.04
```

The current index update-settings transport path bottleneck is request encode.
It validates the acknowledged request envelope, resolves manifest-backed target
indices, mutates nested `settings.index.*` metadata, and renders an OpenSearch
acknowledged response. Ack response encode/decode stays above 7.19M ops/s in
the latest local release run, so the first runtime performance point to inspect
while expanding the path is repeated manifest target resolution and
dotted-setting merge cost for larger index sets.

Current scale-index wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin scale-index-wire-benchmark
scale_index_request_encode iterations=400000 elapsed_ms=306.990 ops_per_second=1302973.97 nanos_per_op=767.48
scale_index_request_decode iterations=400000 elapsed_ms=279.000 ops_per_second=1433693.23 nanos_per_op=697.50
scale_index_request_validate iterations=400000 elapsed_ms=283.658 ops_per_second=1410149.85 nanos_per_op=709.14
scale_index_response_encode iterations=400000 elapsed_ms=48.591 ops_per_second=8232035.05 nanos_per_op=121.48
scale_index_response_decode iterations=400000 elapsed_ms=54.154 ops_per_second=7386278.41 nanos_per_op=135.39
scale_index_wire_bottleneck_ops_per_second=1302973.97
```

The current scale-index transport boundary bottleneck is request encode. The
path writes the acknowledged-request envelope, target index, scale direction,
and indices options, then validates the default scale-down subset before the
node adapter mutates manifest settings and renders an acknowledged response. At
roughly 1.30M ops/s in the latest local release run, wire overhead remains
lightweight; future performance-sensitive work is broader index resolution,
search-only prerequisite validation, shard sync/flush coordination, and
scale-up state transitions.

Current analyze wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin analyze-wire-benchmark
analyze_request_encode iterations=400000 elapsed_ms=302.074 ops_per_second=1324179.25 nanos_per_op=755.18
analyze_request_decode iterations=400000 elapsed_ms=307.459 ops_per_second=1300986.82 nanos_per_op=768.65
analyze_request_validate iterations=400000 elapsed_ms=313.205 ops_per_second=1277119.09 nanos_per_op=783.01
analyze_response_encode iterations=400000 elapsed_ms=205.124 ops_per_second=1950039.34 nanos_per_op=512.81
analyze_response_decode iterations=400000 elapsed_ms=223.889 ops_per_second=1786597.65 nanos_per_op=559.72
analyze_wire_bottleneck_ops_per_second=1277119.09
```

The current analyze local transport subset bottleneck is request validation.
The path writes and reads the single-shard request envelope, optional index,
text array, analyzer selection, custom component lists, explain flag,
attributes, and normalizer, then renders the bounded token-array response. At
roughly 1.28M ops/s in the latest local release run, the current overhead
remains lightweight transport validation and wire work; future
performance-sensitive work is broader analyzer resolution, field-backed
analyzer lookup, detail responses, and richer token attributes.

Current create-index wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin create-index-wire-benchmark
create_index_request_encode iterations=400000 elapsed_ms=274.498 ops_per_second=1457205.36 nanos_per_op=686.25
create_index_request_decode iterations=400000 elapsed_ms=253.356 ops_per_second=1578804.92 nanos_per_op=633.39
create_index_request_validate iterations=400000 elapsed_ms=257.624 ops_per_second=1552648.50 nanos_per_op=644.06
create_index_response_encode iterations=400000 elapsed_ms=100.727 ops_per_second=3971133.39 nanos_per_op=251.82
create_index_response_decode iterations=400000 elapsed_ms=97.078 ops_per_second=4120377.83 nanos_per_op=242.70
create_index_wire_bottleneck_ops_per_second=1457205.36
```

The current create-index transport bottleneck is request encode. The request
carries an acknowledged-request envelope, index name, empty settings, default
mappings, empty alias count, default wait-for-active-shards, and absent context
before the node adapter mutates manifest-backed metadata and renders
`CreateIndexResponse`. At roughly 1.46M request ops/s and roughly 4.0M response
ops/s in the latest local release run, the next performance-sensitive work is
broader metadata validation and publication behavior, not response wire
rendering.

Current auto-create wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin auto-create-wire-benchmark
auto_create_request_encode iterations=400000 elapsed_ms=275.198 ops_per_second=1453499.14 nanos_per_op=687.99
auto_create_request_decode iterations=400000 elapsed_ms=269.968 ops_per_second=1481654.49 nanos_per_op=674.92
auto_create_request_validate iterations=400000 elapsed_ms=276.191 ops_per_second=1448274.95 nanos_per_op=690.48
auto_create_response_encode iterations=400000 elapsed_ms=97.047 ops_per_second=4121714.35 nanos_per_op=242.62
auto_create_response_decode iterations=400000 elapsed_ms=96.314 ops_per_second=4153093.36 nanos_per_op=240.78
auto_create_wire_bottleneck_ops_per_second=1448274.95
```

The current auto-create transport bottleneck is request validation. It uses the
same `CreateIndexRequest` wire shape as create-index with the
`indices:admin/auto_create` action frame, then the node adapter mutates
manifest-backed metadata and renders `CreateIndexResponse`. At roughly 1.45M
request ops/s and roughly 4.1M response ops/s in the latest local release run,
the next performance-sensitive work is broader auto-create template resolution,
metadata validation, and publication behavior.

Current put-stored-script wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-stored-script-wire-benchmark
put_stored_script_request_encode iterations=400000 elapsed_ms=476.505 ops_per_second=839444.79 nanos_per_op=1191.26
put_stored_script_request_decode iterations=400000 elapsed_ms=479.333 ops_per_second=834492.35 nanos_per_op=1198.33
put_stored_script_request_validate iterations=400000 elapsed_ms=493.865 ops_per_second=809937.43 nanos_per_op=1234.66
put_stored_script_response_decode iterations=400000 elapsed_ms=54.084 ops_per_second=7395942.05 nanos_per_op=135.21
put_stored_script_wire_bottleneck_ops_per_second=809937.43
```

The current put-stored-script wire bottleneck is validation.
The path decodes an acknowledged cluster-manager request, optional id, script
content `BytesReference`, media type string, optional context, and
`StoredScriptSource` language/source/options before the manifest-backed
metadata upsert. At
roughly 0.81M ops/s in the latest local release run, current overhead is still
bounded wire validation; future performance-sensitive work is broader script
source parsing, script context validation, cluster metadata publication, and
ack rendering.

Current get-stored-script wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-stored-script-wire-benchmark
get_stored_script_request_encode iterations=400000 elapsed_ms=271.428 ops_per_second=1473688.30 nanos_per_op=678.57
get_stored_script_request_decode iterations=400000 elapsed_ms=238.846 ops_per_second=1674721.76 nanos_per_op=597.11
get_stored_script_request_validate iterations=400000 elapsed_ms=249.909 ops_per_second=1600581.08 nanos_per_op=624.77
get_stored_script_response_encode iterations=400000 elapsed_ms=266.608 ops_per_second=1500331.59 nanos_per_op=666.52
get_stored_script_response_decode iterations=400000 elapsed_ms=234.746 ops_per_second=1703972.27 nanos_per_op=586.86
get_stored_script_wire_bottleneck_ops_per_second=1473688.30
```

The current get-stored-script boundary measures the request path carrying the
cluster-manager read envelope, local-read flag, and script id plus found
response encoding/decoding for `StoredScriptSource` language/source/options. At
roughly 1.47M ops/s in the latest local release run, this adapter is not a
material transport-wire bottleneck for stored-script metadata reads.

Current delete-stored-script wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-stored-script-wire-benchmark
delete_stored_script_request_encode iterations=400000 elapsed_ms=279.401 ops_per_second=1431632.72 nanos_per_op=698.50
delete_stored_script_request_decode iterations=400000 elapsed_ms=256.783 ops_per_second=1557737.86 nanos_per_op=641.96
delete_stored_script_request_validate iterations=400000 elapsed_ms=257.382 ops_per_second=1554110.84 nanos_per_op=643.45
delete_stored_script_response_decode iterations=400000 elapsed_ms=54.548 ops_per_second=7332974.86 nanos_per_op=136.37
delete_stored_script_wire_bottleneck_ops_per_second=1431632.72
```

The current delete-stored-script wire bottleneck is request encode. The request
path carries the acknowledged cluster-manager envelope and
stored script id before the manifest-backed metadata mutation. At roughly 1.43M ops/s in the
latest local release run, current overhead is transport serialization; future
performance-sensitive work is broader not-found/error parity and delete-task
throttling.

Current get-script-context wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-script-context-wire-benchmark
get_script_context_request_encode iterations=400000 elapsed_ms=218.401 ops_per_second=1831495.20 nanos_per_op=546.00
get_script_context_request_decode iterations=400000 elapsed_ms=199.815 ops_per_second=2001852.00 nanos_per_op=499.54
get_script_context_request_validate iterations=400000 elapsed_ms=199.335 ops_per_second=2006672.53 nanos_per_op=498.34
get_script_context_response_encode iterations=400000 elapsed_ms=349.188 ops_per_second=1145514.03 nanos_per_op=872.97
get_script_context_response_decode iterations=400000 elapsed_ms=443.246 ops_per_second=902433.98 nanos_per_op=1108.11
get_script_context_wire_bottleneck_ops_per_second=902433.98
```

The current get-script-context implemented subset bottleneck is response
decode. The request path is thin, while the response path expands
`ScriptContextInfo` method and parameter metadata. At roughly 902K ops/s in the
latest local release run, current overhead is script context response structure
decoding. Future performance-sensitive work is building the Rust script context
catalog without repeated allocation-heavy method metadata expansion.

Current get-script-language wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-script-language-wire-benchmark
get_script_language_request_encode iterations=400000 elapsed_ms=212.159 ops_per_second=1885378.33 nanos_per_op=530.40
get_script_language_request_decode iterations=400000 elapsed_ms=203.960 ops_per_second=1961169.90 nanos_per_op=509.90
get_script_language_request_validate iterations=400000 elapsed_ms=227.651 ops_per_second=1757079.23 nanos_per_op=569.13
get_script_language_response_encode iterations=400000 elapsed_ms=392.743 ops_per_second=1018477.23 nanos_per_op=981.86
get_script_language_response_decode iterations=400000 elapsed_ms=413.468 ops_per_second=967426.57 nanos_per_op=1033.67
get_script_language_wire_bottleneck_ops_per_second=967426.57
```

The current get-script-language implemented subset bottleneck is response
decode. The request path is thin, while the response path expands allowed script
types plus the language-to-contexts map. At roughly 967K ops/s in the latest
local release run, current overhead is script language catalog response
decoding. Future performance-sensitive work is building and serving the Rust
script language catalog without repeated allocation-heavy string collection
expansion.

Current put-pipeline wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin put-pipeline-wire-benchmark
put_pipeline_request_encode iterations=400000 elapsed_ms=396.601 ops_per_second=1008571.04 nanos_per_op=991.50
put_pipeline_request_decode iterations=400000 elapsed_ms=367.738 ops_per_second=1087730.57 nanos_per_op=919.35
put_pipeline_request_validate iterations=400000 elapsed_ms=372.683 ops_per_second=1073297.14 nanos_per_op=931.71
put_pipeline_response_decode iterations=400000 elapsed_ms=54.531 ops_per_second=7335256.06 nanos_per_op=136.33
put_pipeline_wire_bottleneck_ops_per_second=1008571.04
```

The current put-pipeline supported wire subset bottleneck is request encode. The
request path carries the acknowledged cluster-manager envelope, pipeline id,
source bytes, and media type before validating execution. At roughly 1.01M ops/s
in the latest local release run, current overhead is transport serialization.
Future performance-sensitive work is ingest pipeline source parsing, processor
availability validation, metadata persistence, cluster-manager throttling, and
ack rendering.

Current get-pipeline reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-pipeline-reject-wire-benchmark
get_pipeline_reject_request_encode iterations=400000 elapsed_ms=279.526 ops_per_second=1430994.16 nanos_per_op=698.81
get_pipeline_reject_request_decode iterations=400000 elapsed_ms=267.343 ops_per_second=1496207.08 nanos_per_op=668.36
get_pipeline_reject_validation iterations=400000 elapsed_ms=262.613 ops_per_second=1523156.23 nanos_per_op=656.53
get_pipeline_response_decode iterations=400000 elapsed_ms=220.165 ops_per_second=1816815.99 nanos_per_op=550.41
get_pipeline_reject_wire_bottleneck_ops_per_second=1430994.16
```

The current get-pipeline fail-closed boundary bottleneck is request encode. The
request path carries the cluster-manager read envelope, local flag, and ids
array before rejecting execution. At roughly 1.43M ops/s in the latest local
release run, current overhead is transport serialization rather than response
decode. Future performance-sensitive work is serving the Rust ingest pipeline
metadata catalog without allocation-heavy id/wildcard expansion.

Current delete-pipeline wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin delete-pipeline-wire-benchmark
delete_pipeline_request_encode iterations=400000 elapsed_ms=281.755 ops_per_second=1419672.20 nanos_per_op=704.39
delete_pipeline_request_decode iterations=400000 elapsed_ms=256.657 ops_per_second=1558500.34 nanos_per_op=641.64
delete_pipeline_request_validate iterations=400000 elapsed_ms=260.270 ops_per_second=1536868.27 nanos_per_op=650.67
delete_pipeline_response_decode iterations=400000 elapsed_ms=54.656 ops_per_second=7318480.28 nanos_per_op=136.64
delete_pipeline_wire_bottleneck_ops_per_second=1419672.20
```

The current delete-pipeline supported wire subset bottleneck is request encode.
The request path carries the acknowledged cluster-manager envelope and pipeline
id before validating execution. At roughly 1.42M ops/s in the latest local
release run, current overhead is transport serialization. Future
performance-sensitive work is wildcard matching against the Rust ingest
pipeline metadata catalog, missing-pipeline response handling, metadata
mutation, throttling, and ack rendering.

Current simulate-pipeline wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin simulate-pipeline-wire-benchmark
simulate_pipeline_request_encode iterations=400000 elapsed_ms=385.281 ops_per_second=1038201.98 nanos_per_op=963.20
simulate_pipeline_request_decode iterations=400000 elapsed_ms=373.024 ops_per_second=1072316.13 nanos_per_op=932.56
simulate_pipeline_request_validate iterations=400000 elapsed_ms=373.554 ops_per_second=1070795.29 nanos_per_op=933.89
simulate_pipeline_response_decode iterations=400000 elapsed_ms=95.006 ops_per_second=4210240.55 nanos_per_op=237.52
simulate_pipeline_wire_bottleneck_ops_per_second=1038201.98
```

The current simulate-pipeline supported wire subset bottleneck is request
encode. The request path carries optional pipeline id, verbose flag, source
bytes, and media type before validating execution. At roughly 1.04M ops/s in the
latest local release run, current overhead is transport serialization. Future
performance-sensitive work is JSON source parsing, processor execution,
verbose result capture, and non-empty simulate response rendering.

Current resize reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin resize-reject-wire-benchmark
resize_reject_request_encode iterations=400000 elapsed_ms=360.201 ops_per_second=1110490.53 nanos_per_op=900.50
resize_reject_request_decode iterations=400000 elapsed_ms=375.027 ops_per_second=1066589.98 nanos_per_op=937.57
resize_reject_validation iterations=400000 elapsed_ms=375.871 ops_per_second=1064195.44 nanos_per_op=939.68
resize_reject_wire_bottleneck_ops_per_second=1064195.44
```

The current resize fail-closed boundary bottleneck is validation. The path
decodes the acknowledged-request envelope, nested `CreateIndexRequest`, source
index, resize type, `copySettings`, and optional `maxShardSize`, then verifies
the nested target create-index shape before rejecting execution. At roughly
1.06M ops/s in the latest local release run, the current overhead is still wire
boundary work; the future performance-sensitive work is source index metadata
validation, target index metadata mutation, shard allocation, and resize
response rendering.

Current rollover reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin rollover-reject-wire-benchmark
rollover_reject_request_encode iterations=400000 elapsed_ms=445.147 ops_per_second=898578.64 nanos_per_op=1112.87
rollover_reject_request_decode iterations=400000 elapsed_ms=327.549 ops_per_second=1221189.60 nanos_per_op=818.87
rollover_reject_validation iterations=400000 elapsed_ms=343.380 ops_per_second=1164890.98 nanos_per_op=858.45
rollover_reject_wire_bottleneck_ops_per_second=898578.64
```

The current rollover fail-closed boundary bottleneck is request encode. The
path writes the acknowledged-request envelope, rollover target, optional new
index marker, dry-run flag, zero-condition marker, and nested
`CreateIndexRequest` before rejecting execution. At roughly 0.90M ops/s in the
latest local release run, the current overhead is still request wire boundary
work; future performance-sensitive work is alias or data-stream metadata
validation, condition evaluation, index creation, and rollover response
rendering.

Current delete-index wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin delete-index-wire-benchmark
delete_index_request_encode iterations=400000 elapsed_ms=284.113 ops_per_second=1407888.70 nanos_per_op=710.28
delete_index_request_decode iterations=400000 elapsed_ms=274.231 ops_per_second=1458623.47 nanos_per_op=685.58
delete_index_request_validate iterations=400000 elapsed_ms=280.096 ops_per_second=1428080.12 nanos_per_op=700.24
delete_index_response_encode iterations=400000 elapsed_ms=48.552 ops_per_second=8238504.88 nanos_per_op=121.38
delete_index_response_decode iterations=400000 elapsed_ms=54.713 ops_per_second=7310812.89 nanos_per_op=136.78
delete_index_wire_bottleneck_ops_per_second=1407888.70
```

The current delete-index transport bottleneck is request encode. The request
carries an acknowledged-request envelope, non-empty concrete index targets, and
delete-index default indices options before the node adapter removes
manifest-backed metadata and local development documents. At roughly 1.41M
request ops/s and 7M+ response ops/s in the latest local release run, the next
performance-sensitive work is broader index resolution and deletion planning,
not ack response rendering.

Current open-index wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin open-index-wire-benchmark
open_index_request_encode iterations=400000 elapsed_ms=284.851 ops_per_second=1404243.91 nanos_per_op=712.13
open_index_request_decode iterations=400000 elapsed_ms=258.704 ops_per_second=1546170.11 nanos_per_op=646.76
open_index_request_validate iterations=400000 elapsed_ms=263.831 ops_per_second=1516120.94 nanos_per_op=659.58
open_index_response_encode iterations=400000 elapsed_ms=49.380 ops_per_second=8100413.04 nanos_per_op=123.45
open_index_response_decode iterations=400000 elapsed_ms=54.870 ops_per_second=7289961.80 nanos_per_op=137.17
open_index_wire_bottleneck_ops_per_second=1404243.91
```

The current open-index transport bottleneck is request encode. The request
carries an acknowledged-request envelope, non-empty concrete index targets,
open-index default indices options, and default wait-for-active-shards before
the node adapter marks manifest-backed metadata open and renders the response.
At roughly 1.42M request ops/s and 7M+ response ops/s in the latest local
release run, the next performance-sensitive work is broader index resolution,
state-transition planning, and allocation acknowledgement behavior, not response
wire rendering.

Current close-index wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin close-index-wire-benchmark
close_index_request_encode iterations=400000 elapsed_ms=279.739 ops_per_second=1429901.87 nanos_per_op=699.35
close_index_request_decode iterations=400000 elapsed_ms=267.572 ops_per_second=1494926.29 nanos_per_op=668.93
close_index_request_validate iterations=400000 elapsed_ms=272.933 ops_per_second=1465562.58 nanos_per_op=682.33
close_index_response_encode iterations=400000 elapsed_ms=182.020 ops_per_second=2197566.24 nanos_per_op=455.05
close_index_response_decode iterations=400000 elapsed_ms=175.809 ops_per_second=2275193.75 nanos_per_op=439.52
close_index_wire_bottleneck_ops_per_second=1429901.87
```

The current close-index transport bottleneck is request encode. The request
carries an acknowledged-request envelope, non-empty concrete index targets,
close-index default indices options, and `ActiveShardCount.NONE` before the node
adapter marks manifest-backed metadata closed and renders the response. At
roughly 1.43M request ops/s and 2.1M+ response ops/s in the latest local
release run, the next performance-sensitive work is broader index resolution,
close-state planning, and allocation acknowledgement behavior.

Current add-index-block wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin add-index-block-wire-benchmark
add_index_block_request_encode iterations=400000 elapsed_ms=287.864 ops_per_second=1389545.32 nanos_per_op=719.66
add_index_block_request_decode iterations=400000 elapsed_ms=273.782 ops_per_second=1461015.30 nanos_per_op=684.46
add_index_block_request_validate iterations=400000 elapsed_ms=278.670 ops_per_second=1435389.64 nanos_per_op=696.67
add_index_block_response_encode iterations=400000 elapsed_ms=184.212 ops_per_second=2171409.82 nanos_per_op=460.53
add_index_block_response_decode iterations=400000 elapsed_ms=175.042 ops_per_second=2285160.77 nanos_per_op=437.61
add_index_block_wire_bottleneck_ops_per_second=1389545.32
```

The current add-index-block transport bottleneck is request encode. The request
carries an acknowledged-request envelope, non-empty concrete index targets,
strict-open indices options, and APIBlock ordinal before the node adapter marks
manifest-backed block settings and renders the response. At roughly 1.39M
request ops/s and 2.1M+ response ops/s in the latest local release run, the next
performance-sensitive work is broader index resolution, block-check handling,
and shard-level verification behavior.

Current get-index wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-index-wire-benchmark
get_index_request_encode iterations=400000 elapsed_ms=215.682 ops_per_second=1854579.88 nanos_per_op=539.21
get_index_request_decode iterations=400000 elapsed_ms=218.560 ops_per_second=1830159.90 nanos_per_op=546.40
get_index_request_validate iterations=400000 elapsed_ms=221.842 ops_per_second=1803083.04 nanos_per_op=554.61
get_index_response_encode iterations=400000 elapsed_ms=183.705 ops_per_second=2177401.10 nanos_per_op=459.26
get_index_response_decode iterations=400000 elapsed_ms=193.239 ops_per_second=2069974.08 nanos_per_op=483.10
get_index_wire_bottleneck_ops_per_second=1803083.04
```

The current get-index transport boundary bottleneck is validation over the
decoded request. The implemented subset carries the ClusterManagerNodeRead
envelope, empty index array, `IndicesOptions.strictExpandOpen()`, default
feature byte array, two boolean rendering flags, and an OpenSearch-shaped
metadata response. At roughly 1.80M ops/s in the latest local release run, the
remaining performance-sensitive work is richer aliases/mappings/settings/context
metadata rendering.

Current indices-exists wire microbenchmark:

```text
cargo run -p os-transport --release --bin indices-exists-wire-benchmark
indices_exists_request_encode iterations=400000 elapsed_ms=230.130 ops_per_second=1738146.12 nanos_per_op=575.33
indices_exists_request_decode iterations=400000 elapsed_ms=242.731 ops_per_second=1647915.78 nanos_per_op=606.83
indices_exists_request_validate iterations=400000 elapsed_ms=244.948 ops_per_second=1632998.91 nanos_per_op=612.37
indices_exists_response_encode iterations=400000 elapsed_ms=86.259 ops_per_second=4637208.67 nanos_per_op=215.65
indices_exists_response_decode iterations=400000 elapsed_ms=88.555 ops_per_second=4516941.86 nanos_per_op=221.39
indices_exists_wire_bottleneck_ops_per_second=1632998.91
```

The current indices-exists transport boundary bottleneck is request validation.
The benchmark request carries a non-empty `logs-*` target and an OpenSearch
boolean response. At roughly 1.63M ops/s in the latest local release run, the
remaining performance-sensitive work is index-resolution breadth under richer
metadata state.

Current get-index-templates wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-index-templates-wire-benchmark
get_index_templates_request_encode iterations=400000 elapsed_ms=194.744 ops_per_second=2053974.44 nanos_per_op=486.86
get_index_templates_request_decode iterations=400000 elapsed_ms=193.126 ops_per_second=2071182.25 nanos_per_op=482.82
get_index_templates_request_validate iterations=400000 elapsed_ms=192.655 ops_per_second=2076246.30 nanos_per_op=481.64
get_index_templates_response_encode iterations=400000 elapsed_ms=87.125 ops_per_second=4591104.89 nanos_per_op=217.81
get_index_templates_response_decode iterations=400000 elapsed_ms=94.229 ops_per_second=4244991.00 nanos_per_op=235.57
get_index_templates_wire_bottleneck_ops_per_second=2053974.44
```

The current get-index-templates transport boundary bottleneck is request encode.
The benchmark uses an empty names array, matching the OpenSearch all-templates
request shape, plus an empty OpenSearch-shaped response. At roughly 2.05M ops/s
in the latest local release run, the remaining performance-sensitive work is
template metadata matching under larger manifests.

Current put-index-template wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-index-template-wire-benchmark
put_index_template_request_encode iterations=400000 elapsed_ms=314.955 ops_per_second=1270022.14 nanos_per_op=787.39
put_index_template_request_decode iterations=400000 elapsed_ms=310.649 ops_per_second=1287625.30 nanos_per_op=776.62
put_index_template_request_validate iterations=400000 elapsed_ms=338.156 ops_per_second=1182884.60 nanos_per_op=845.39
put_index_template_response_decode iterations=400000 elapsed_ms=54.834 ops_per_second=7294753.98 nanos_per_op=137.08
put_index_template_wire_bottleneck_ops_per_second=1182884.60
```

The current put-index-template transport boundary bottleneck is request
validation. The supported execution subset writes a valid empty legacy template
shape with a template name, one index pattern, and optional version, then the
node adapter upserts manifest-backed metadata and renders an acknowledged
response. At roughly 1.18M ops/s in the latest local release run, the remaining
performance-sensitive work is richer template validation and metadata
publication across distributed cluster-state ownership.

Current delete-index-template wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-index-template-wire-benchmark
delete_index_template_request_encode iterations=400000 elapsed_ms=285.669 ops_per_second=1400223.02 nanos_per_op=714.17
delete_index_template_request_decode iterations=400000 elapsed_ms=243.845 ops_per_second=1640382.96 nanos_per_op=609.61
delete_index_template_request_validate iterations=400000 elapsed_ms=248.350 ops_per_second=1610631.06 nanos_per_op=620.87
delete_index_template_response_decode iterations=400000 elapsed_ms=54.591 ops_per_second=7327262.89 nanos_per_op=136.48
delete_index_template_wire_bottleneck_ops_per_second=1400223.02
```

The current delete-index-template transport boundary bottleneck is request
encode. The supported execution subset performs default-timeout validation,
manifest-backed metadata removal in the node adapter, and acknowledged response
rendering; future performance-sensitive work is metadata publication across
distributed cluster-state ownership.

Current put-component-template wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-component-template-wire-benchmark
put_component_template_request_encode iterations=400000 elapsed_ms=350.187 ops_per_second=1142245.69 nanos_per_op=875.47
put_component_template_request_decode iterations=400000 elapsed_ms=302.675 ops_per_second=1321549.60 nanos_per_op=756.69
put_component_template_request_validate iterations=400000 elapsed_ms=309.496 ops_per_second=1292421.94 nanos_per_op=773.74
put_component_template_response_decode iterations=400000 elapsed_ms=54.907 ops_per_second=7285007.68 nanos_per_op=137.27
put_component_template_wire_bottleneck_ops_per_second=1142245.69
```

The current put-component-template transport boundary bottleneck is request
encode. The supported subset writes the cluster-manager request envelope,
component-template name, absent cause, create flag, settings-capable nested
template markers, optional version, and absent metadata marker. The node adapter
then upserts manifest-backed metadata and renders an acknowledged response. At
roughly 1.05M ops/s in the latest local release run, the remaining
performance-sensitive work is richer validation and distributed metadata
publication.

Current get-component-template wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-component-template-wire-benchmark
get_component_template_request_encode iterations=400000 elapsed_ms=222.139 ops_per_second=1800676.85 nanos_per_op=555.35
get_component_template_request_decode iterations=400000 elapsed_ms=211.932 ops_per_second=1887396.82 nanos_per_op=529.83
get_component_template_request_validate iterations=400000 elapsed_ms=212.898 ops_per_second=1878837.14 nanos_per_op=532.24
get_component_template_response_encode iterations=400000 elapsed_ms=89.609 ops_per_second=4463846.25 nanos_per_op=224.02
get_component_template_response_decode iterations=400000 elapsed_ms=71.283 ops_per_second=5611429.49 nanos_per_op=178.21
get_component_template_wire_bottleneck_ops_per_second=1800676.85
```

The current get-component-template transport boundary bottleneck is request
encode. The benchmark uses an absent optional name, matching the OpenSearch
all-component-templates request shape, plus an empty OpenSearch-shaped response.
At roughly 1.80M ops/s in the latest local release run, the remaining
performance-sensitive work is component-template metadata matching under larger
manifests.

Current delete-component-template wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-component-template-wire-benchmark
delete_component_template_request_encode iterations=400000 elapsed_ms=333.706 ops_per_second=1198658.90 nanos_per_op=834.27
delete_component_template_request_decode iterations=400000 elapsed_ms=290.645 ops_per_second=1376248.30 nanos_per_op=726.61
delete_component_template_request_validate iterations=400000 elapsed_ms=295.744 ops_per_second=1352519.29 nanos_per_op=739.36
delete_component_template_response_decode iterations=400000 elapsed_ms=53.994 ops_per_second=7408225.33 nanos_per_op=134.99
delete_component_template_wire_bottleneck_ops_per_second=1198658.90
```

The current delete-component-template transport boundary bottleneck is request
encode. The supported execution subset performs default-timeout validation,
manifest-backed component-template metadata removal in the node adapter, and
acknowledged response rendering; future performance-sensitive work is metadata
publication across distributed cluster-state ownership.

Current put-composable-index-template wire microbenchmark:

```text
cargo run -q -p os-transport --release --bin put-composable-index-template-wire-benchmark
put_composable_index_template_request_encode iterations=400000 elapsed_ms=352.957 ops_per_second=1133281.53 nanos_per_op=882.39
put_composable_index_template_request_decode iterations=400000 elapsed_ms=340.713 ops_per_second=1174008.50 nanos_per_op=851.78
put_composable_index_template_request_validate iterations=400000 elapsed_ms=346.628 ops_per_second=1153975.50 nanos_per_op=866.57
put_composable_index_template_response_decode iterations=400000 elapsed_ms=54.720 ops_per_second=7309942.46 nanos_per_op=136.80
put_composable_index_template_wire_bottleneck_ops_per_second=1133281.53
```

The current put-composable-index-template supported wire subset bottleneck is
request encode. The default benchmark writes the cluster-manager request
envelope, template name, absent cause, create flag, one index pattern, absent
nested template, absent composed-of list, absent priority/version, absent
metadata map, absent data-stream marker, and absent context marker before
rejecting execution. At roughly 1.12M ops/s in the latest local release run,
the remaining performance-sensitive work is composable index-template
validation, metadata publication, and acknowledged response rendering.

Current get-composable-index-template wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-composable-index-template-wire-benchmark
get_composable_index_template_request_encode iterations=400000 elapsed_ms=214.975 ops_per_second=1860677.46 nanos_per_op=537.44
get_composable_index_template_request_decode iterations=400000 elapsed_ms=203.600 ops_per_second=1964633.13 nanos_per_op=509.00
get_composable_index_template_request_validate iterations=400000 elapsed_ms=205.176 ops_per_second=1949547.94 nanos_per_op=512.94
get_composable_index_template_response_encode iterations=400000 elapsed_ms=95.516 ops_per_second=4187785.45 nanos_per_op=238.79
get_composable_index_template_response_decode iterations=400000 elapsed_ms=73.893 ops_per_second=5413256.82 nanos_per_op=184.73
get_composable_index_template_wire_bottleneck_ops_per_second=1860677.46
```

The current get-composable-index-template transport boundary bottleneck is
request encode. The benchmark uses an absent optional name, matching the
OpenSearch all-composable-index-templates request shape, plus an empty
OpenSearch-shaped response. At roughly 1.86M ops/s in the latest local release
run, the remaining performance-sensitive work is composable index-template
metadata matching under larger manifests.

Current delete-composable-index-template wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-composable-index-template-wire-benchmark
delete_composable_index_template_request_encode iterations=400000 elapsed_ms=311.989 ops_per_second=1282098.26 nanos_per_op=779.97
delete_composable_index_template_request_decode iterations=400000 elapsed_ms=273.021 ops_per_second=1465091.25 nanos_per_op=682.55
delete_composable_index_template_request_validate iterations=400000 elapsed_ms=290.334 ops_per_second=1377721.25 nanos_per_op=725.84
delete_composable_index_template_response_decode iterations=400000 elapsed_ms=54.910 ops_per_second=7284693.51 nanos_per_op=137.27
delete_composable_index_template_wire_bottleneck_ops_per_second=1282098.26
```

The current delete-composable-index-template transport boundary bottleneck is
request encode. The supported execution subset performs default-timeout
validation, manifest-backed composable index-template metadata removal in the
node adapter, and acknowledged response rendering; future performance-sensitive
work is metadata publication across distributed cluster-state ownership.

Current simulate-index-template reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin simulate-index-template-reject-wire-benchmark
simulate_index_template_reject_request_encode iterations=400000 elapsed_ms=294.544 ops_per_second=1358033.57 nanos_per_op=736.36
simulate_index_template_reject_request_decode iterations=400000 elapsed_ms=286.071 ops_per_second=1398255.80 nanos_per_op=715.18
simulate_index_template_reject_validation iterations=400000 elapsed_ms=293.855 ops_per_second=1361217.60 nanos_per_op=734.64
simulate_index_template_reject_wire_bottleneck_ops_per_second=1358033.57
```

The current simulate-index-template fail-closed boundary bottleneck is request
encode. The default benchmark writes the cluster-manager read request envelope,
local flag, index name, and absent inline template body before rejecting
execution. At roughly 1.36M ops/s in the latest local release run, the
remaining performance-sensitive work is composable template resolution,
simulation merge logic, and simulated metadata response rendering.

Current simulate-template reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin simulate-template-reject-wire-benchmark
simulate_template_reject_request_encode iterations=400000 elapsed_ms=307.807 ops_per_second=1299516.72 nanos_per_op=769.52
simulate_template_reject_request_decode iterations=400000 elapsed_ms=277.956 ops_per_second=1439076.19 nanos_per_op=694.89
simulate_template_reject_validation iterations=400000 elapsed_ms=357.403 ops_per_second=1119186.03 nanos_per_op=893.51
simulate_template_reject_wire_bottleneck_ops_per_second=1119186.03
```

The current simulate-template fail-closed boundary bottleneck is validation.
The default benchmark writes the cluster-manager read request envelope, local
flag, template name, and absent inline template body before rejecting
execution. At roughly 1.12M ops/s in the latest local release run, the
remaining performance-sensitive work is named/inline composable template
resolution, simulation merge logic, and simulated metadata response rendering.

Current validate-query reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin validate-query-reject-wire-benchmark
validate_query_reject_request_encode iterations=400000 elapsed_ms=275.308 ops_per_second=1452917.60 nanos_per_op=688.27
validate_query_reject_request_decode iterations=400000 elapsed_ms=263.622 ops_per_second=1517326.10 nanos_per_op=659.05
validate_query_reject_validation iterations=400000 elapsed_ms=272.319 ops_per_second=1468866.62 nanos_per_op=680.80
validate_query_reject_wire_bottleneck_ops_per_second=1452917.60
```

The current validate-query fail-closed boundary bottleneck is request encode.
The default benchmark writes the broadcast request envelope, empty index array,
default validate-query indices options, minimal `match_all` query builder, and
default explain/rewrite/all-shards flags before rejecting execution. At roughly
1.45M ops/s in the latest local release run, the remaining performance-sensitive
work is query parsing, rewrite, shard selection, per-shard validation, and
response rendering.

Current flush reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin flush-reject-wire-benchmark
flush_reject_request_encode iterations=400000 elapsed_ms=221.084 ops_per_second=1809265.40 nanos_per_op=552.71
flush_reject_request_decode iterations=400000 elapsed_ms=215.194 ops_per_second=1858786.28 nanos_per_op=537.99
flush_reject_validation iterations=400000 elapsed_ms=250.833 ops_per_second=1594688.23 nanos_per_op=627.08
flush_reject_wire_bottleneck_ops_per_second=1594688.23
```

The current flush fail-closed boundary bottleneck is validation. The default
benchmark writes the broadcast request envelope, empty index array, default
strict-expand-open-forbid-closed indices options, `force=false`, and
`wait_if_ongoing=true` before rejecting execution. At roughly 1.59M ops/s in
the latest local release run, the remaining performance-sensitive work is
translog flush execution, in-flight flush coordination, and shard status
response rendering.

Current force-merge reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin force-merge-reject-wire-benchmark
force_merge_reject_request_encode iterations=400000 elapsed_ms=341.589 ops_per_second=1170996.19 nanos_per_op=853.97
force_merge_reject_request_decode iterations=400000 elapsed_ms=300.006 ops_per_second=1333305.16 nanos_per_op=750.02
force_merge_reject_validation iterations=400000 elapsed_ms=306.932 ops_per_second=1303221.08 nanos_per_op=767.33
force_merge_reject_wire_bottleneck_ops_per_second=1170996.19
```

The current force-merge fail-closed boundary bottleneck is request encode. The
default benchmark writes the broadcast request envelope, empty index array,
default strict-expand-open-forbid-closed indices options, max segment count,
expunge/flush/primary flags, and the force-merge UUID before rejecting
execution. At roughly 1.17M ops/s in the latest local release run, the
remaining performance-sensitive work is segment merge scheduling, primary-only
routing, post-merge flush coordination, and shard status response rendering.

Current upgrade reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin upgrade-reject-wire-benchmark
upgrade_reject_request_encode iterations=400000 elapsed_ms=220.184 ops_per_second=1816664.31 nanos_per_op=550.46
upgrade_reject_request_decode iterations=400000 elapsed_ms=241.184 ops_per_second=1658482.81 nanos_per_op=602.96
upgrade_reject_validation iterations=400000 elapsed_ms=259.297 ops_per_second=1542635.05 nanos_per_op=648.24
upgrade_reject_wire_bottleneck_ops_per_second=1542635.05
```

The current upgrade fail-closed boundary bottleneck is validation. The default
benchmark writes the broadcast request envelope, empty index array, default
strict-expand-open-forbid-closed indices options, and
`upgrade_only_ancient_segments=false` before rejecting execution. At roughly
1.54M ops/s in the latest local release run, the remaining performance-sensitive
work is segment upgrade scheduling, primary availability validation, settings
update coordination, and response rendering.

Current upgrade-status reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin upgrade-status-reject-wire-benchmark
upgrade_status_reject_request_encode iterations=400000 elapsed_ms=211.533 ops_per_second=1890957.49 nanos_per_op=528.83
upgrade_status_reject_request_decode iterations=400000 elapsed_ms=222.684 ops_per_second=1796266.13 nanos_per_op=556.71
upgrade_status_reject_validation iterations=400000 elapsed_ms=224.393 ops_per_second=1782590.54 nanos_per_op=560.98
upgrade_status_reject_wire_bottleneck_ops_per_second=1782590.54
```

The current upgrade-status fail-closed boundary bottleneck is validation. The
default benchmark writes the broadcast request envelope, empty index array, and
default strict-expand-open-forbid-closed indices options before rejecting
execution. At roughly 1.78M ops/s in the latest local release run, the remaining
performance-sensitive work is shard segment-version scanning, routing metadata
collection, byte-counter aggregation, and response rendering.

Current upgrade-settings reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin upgrade-settings-reject-wire-benchmark
upgrade_settings_reject_request_encode iterations=400000 elapsed_ms=343.694 ops_per_second=1163826.18 nanos_per_op=859.23
upgrade_settings_reject_request_decode iterations=400000 elapsed_ms=292.415 ops_per_second=1367916.77 nanos_per_op=731.04
upgrade_settings_reject_validation iterations=400000 elapsed_ms=306.408 ops_per_second=1305446.97 nanos_per_op=766.02
upgrade_settings_reject_wire_bottleneck_ops_per_second=1163826.18
```

The current upgrade-settings fail-closed boundary bottleneck is request encode.
The default benchmark writes the parent task, default cluster-manager and
acknowledgement timeouts, one versions-map entry, an OpenSearch version id, and
the oldest Lucene segment version string before rejecting execution. At roughly
1.16M ops/s in the latest local release run, the remaining performance-sensitive
work is metadata mutation planning, cluster-state publication, acknowledgement
tracking, and acknowledged response rendering.

Current clear-indices-cache reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin clear-indices-cache-reject-wire-benchmark
clear_indices_cache_reject_request_encode iterations=400000 elapsed_ms=279.162 ops_per_second=1432859.73 nanos_per_op=697.91
clear_indices_cache_reject_request_decode iterations=400000 elapsed_ms=229.986 ops_per_second=1739235.77 nanos_per_op=574.97
clear_indices_cache_reject_validation iterations=400000 elapsed_ms=259.291 ops_per_second=1542669.56 nanos_per_op=648.23
clear_indices_cache_reject_wire_bottleneck_ops_per_second=1432859.73
```

The current clear-indices-cache fail-closed boundary bottleneck is request
encode. The default benchmark writes the broadcast request envelope, empty
index and field arrays, default strict-expand-open-forbid-closed indices
options, and cache selector booleans before rejecting execution. At roughly
1.43M ops/s in the latest local release run, the remaining
performance-sensitive work is shard cache invalidation, file-cache pruning,
node-wide cache cleanup, shard failure aggregation, and response rendering.

Current field-capabilities request wire microbenchmark:

```text
cargo run -p os-transport --release --bin field-capabilities-reject-wire-benchmark
field_capabilities_reject_request_encode iterations=400000 elapsed_ms=245.330 ops_per_second=1630460.22 nanos_per_op=613.32
field_capabilities_reject_request_decode iterations=400000 elapsed_ms=267.059 ops_per_second=1497794.63 nanos_per_op=667.65
field_capabilities_reject_validation iterations=400000 elapsed_ms=272.583 ops_per_second=1467442.71 nanos_per_op=681.46
field_capabilities_reject_wire_bottleneck_ops_per_second=1467442.71
```

The current field-capabilities request-boundary bottleneck is validation.
This path carries the ActionRequest parent task, field and index arrays,
`IndicesOptions.strictExpandOpen()`, merge/include-unmapped flags, optional
query marker, and optional timestamp before the local metadata/document
execution subset is admitted. At roughly 1.47M ops/s in the latest local
release run, the request boundary itself is lightweight; the next performance
point to inspect is mapping/type metadata aggregation and field-capabilities
response rendering.

Current get-aliases implemented-path wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-aliases-wire-benchmark
get_aliases_request_encode iterations=400000 elapsed_ms=231.794 ops_per_second=1725672.04 nanos_per_op=579.48
get_aliases_request_decode iterations=400000 elapsed_ms=244.722 ops_per_second=1634509.62 nanos_per_op=611.80
get_aliases_request_validate iterations=400000 elapsed_ms=248.192 ops_per_second=1611656.09 nanos_per_op=620.48
get_aliases_response_encode iterations=400000 elapsed_ms=86.409 ops_per_second=4629157.18 nanos_per_op=216.02
get_aliases_response_decode iterations=400000 elapsed_ms=92.952 ops_per_second=4303298.18 nanos_per_op=232.38
get_aliases_wire_bottleneck_ops_per_second=1611656.09
```

The current get-aliases implemented-path bottleneck is request validation after
decode. Response encode/decode is substantially faster for the empty alias map
case, and the full default transport path remains at roughly 1.61M ops/s in the
latest local release run.

Current get-settings implemented-path wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-settings-wire-benchmark
get_settings_request_encode iterations=400000 elapsed_ms=231.512 ops_per_second=1727768.90 nanos_per_op=578.78
get_settings_request_decode iterations=400000 elapsed_ms=234.703 ops_per_second=1704280.46 nanos_per_op=586.76
get_settings_request_validate iterations=400000 elapsed_ms=236.189 ops_per_second=1693556.34 nanos_per_op=590.47
get_settings_response_encode iterations=400000 elapsed_ms=101.996 ops_per_second=3921725.77 nanos_per_op=254.99
get_settings_response_decode iterations=400000 elapsed_ms=111.238 ops_per_second=3595884.44 nanos_per_op=278.10
get_settings_wire_bottleneck_ops_per_second=1693556.34
```

The current get-settings implemented-path bottleneck is request validation after
decode. The empty settings response encode/decode path is faster than request
handling, and the full default transport path remains at roughly 1.69M ops/s in
the latest local release run.

Current cluster-search-shards wire microbenchmark:

```text
cargo run -p os-transport --release --bin cluster-search-shards-wire-benchmark
cluster_search_shards_request_encode iterations=400000 elapsed_ms=257.667 ops_per_second=1552390.61 nanos_per_op=644.17
cluster_search_shards_request_decode iterations=400000 elapsed_ms=249.010 ops_per_second=1606364.38 nanos_per_op=622.52
cluster_search_shards_request_validate iterations=400000 elapsed_ms=253.447 ops_per_second=1578240.56 nanos_per_op=633.62
cluster_search_shards_response_encode iterations=400000 elapsed_ms=86.806 ops_per_second=4607995.94 nanos_per_op=217.01
cluster_search_shards_response_decode iterations=400000 elapsed_ms=93.972 ops_per_second=4256564.42 nanos_per_op=234.93
cluster_search_shards_wire_bottleneck_ops_per_second=1552390.61
```

The current cluster-search-shards fail-closed boundary bottleneck is request
encode. This path carries the ClusterManagerNodeRead envelope, local flag,
empty index array, optional routing/preference fields, lenient open-index
options, and slice-present flag before rejecting at admission. At roughly 1.52M
ops/s in the latest local release run, it remains in the lightweight admin
transport range.

Current recovery supported-subset wire microbenchmark:

```text
cargo run -p os-transport --release --bin recovery-wire-benchmark
recovery_request_encode ops_per_second=1593087.41 nanos_per_op=627.71
recovery_request_decode ops_per_second=1595473.35 nanos_per_op=626.77
recovery_supported_validation ops_per_second=1108841.63 nanos_per_op=901.84
recovery_wire_bottleneck_ops_per_second=1108841.63
```

The current recovery supported-subset boundary carries the BroadcastRequest
parent task, empty index array, strict open/closed index options, detailed flag,
and active-only flag. The first performance-sensitive work beyond this boundary
is populating non-empty shard recovery metadata and rendering detailed recovery
responses. At roughly 1.11M ops/s in the latest local run, this path does not
introduce a new transport admission hotspot.

Current segment-replication-stats wire microbenchmark:

```text
cargo run -p os-transport --release --bin segment-replication-stats-wire-benchmark
segment_replication_stats_request_encode iterations=500000 elapsed_ms=350.463 ops_per_second=1426685.51 nanos_per_op=700.93
segment_replication_stats_request_decode iterations=500000 elapsed_ms=307.034 ops_per_second=1628483.87 nanos_per_op=614.07
segment_replication_stats_request_validate iterations=500000 elapsed_ms=306.842 ops_per_second=1629504.99 nanos_per_op=613.68
segment_replication_stats_response_encode iterations=500000 elapsed_ms=71.826 ops_per_second=6961244.54 nanos_per_op=143.65
segment_replication_stats_response_decode iterations=500000 elapsed_ms=81.379 ops_per_second=6144102.85 nanos_per_op=162.76
segment_replication_stats_wire_bottleneck_ops_per_second=1426685.51
```

The current segment-replication-stats supported-subset boundary bottleneck is
request encode. This path carries the BroadcastRequest parent task, empty index
array, strict open forbid-closed index options, detailed flag, and active-only
flag before accepting the empty response subset. At roughly 1.43M ops/s, the
boundary itself is lightweight; response encode/decode stays above 6.1M ops/s.
The first performance point to inspect before expanding execution is shard
routing, pressure-service stats collection, target-service live state lookup,
primary/replica grouping, and non-empty response rendering.

Current indices-segments wire microbenchmark:

```text
cargo run -p os-transport --release --bin indices-segments-wire-benchmark
indices_segments_request_encode iterations=400000 elapsed_ms=208.312 ops_per_second=1920199.02 nanos_per_op=520.78
indices_segments_request_decode iterations=400000 elapsed_ms=222.212 ops_per_second=1800085.77 nanos_per_op=555.53
indices_segments_request_validate iterations=400000 elapsed_ms=223.902 ops_per_second=1786496.44 nanos_per_op=559.75
indices_segments_response_encode iterations=400000 elapsed_ms=93.971 ops_per_second=4256633.54 nanos_per_op=234.93
indices_segments_response_decode iterations=400000 elapsed_ms=94.830 ops_per_second=4218057.46 nanos_per_op=237.08
indices_segments_wire_bottleneck_ops_per_second=1786496.44
```

The current indices-segments fail-closed boundary bottleneck is validation. This
path carries the BroadcastRequest parent task, empty index array, strict open
forbid-closed index options, and verbose flag before rejecting at admission. At
roughly 1.77M ops/s in the latest local release run, it is effectively the same
weight as the recovery reject boundary and does not expose a material wire-codec
bottleneck.

Current indices-shard-stores implemented-path wire microbenchmark:

```text
cargo run -p os-transport --release --bin indices-shard-stores-wire-benchmark
indices_shard_stores_request_encode iterations=400000 elapsed_ms=228.128 ops_per_second=1753402.11 nanos_per_op=570.32
indices_shard_stores_request_decode iterations=400000 elapsed_ms=250.669 ops_per_second=1595731.46 nanos_per_op=626.67
indices_shard_stores_request_validate iterations=400000 elapsed_ms=254.361 ops_per_second=1572565.29 nanos_per_op=635.90
indices_shard_stores_response_encode iterations=400000 elapsed_ms=86.236 ops_per_second=4638431.54 nanos_per_op=215.59
indices_shard_stores_response_decode iterations=400000 elapsed_ms=90.972 ops_per_second=4396941.31 nanos_per_op=227.43
indices_shard_stores_wire_bottleneck_ops_per_second=1572565.29
```

The current indices-shard-stores implemented-path bottleneck is request
validation after decode. This path carries the ClusterManagerNodeRead envelope,
empty index array, default yellow/red shard health status filter, strict
open/closed index options, and an empty `IndicesShardStoresResponse`. At roughly
1.57M ops/s in the latest local release run, it does not expose a material
response-codec bottleneck.

Current create-data-stream implemented-path wire microbenchmark:

```text
cargo run -p os-transport --release --bin create-data-stream-wire-benchmark
create_data_stream_request_encode iterations=400000 elapsed_ms=249.822 ops_per_second=1601141.58 nanos_per_op=624.55
create_data_stream_request_decode iterations=400000 elapsed_ms=245.248 ops_per_second=1631003.48 nanos_per_op=613.12
create_data_stream_request_validate iterations=400000 elapsed_ms=248.494 ops_per_second=1609697.45 nanos_per_op=621.23
create_data_stream_ack_response_decode iterations=400000 elapsed_ms=54.714 ops_per_second=7310742.60 nanos_per_op=136.79
create_data_stream_wire_bottleneck_ops_per_second=1601141.58
```

The current create-data-stream implemented-path wire bottleneck is request
encode.
The request path carries the acknowledged cluster-manager envelope and
data-stream name before admitting the manifest-backed metadata mutation subset.
At roughly 1.61M ops/s in the latest local release run, current wire overhead
is lower than the runtime work expected from metadata locking, backing-index
allocation, and manifest mutation.

Current delete-data-stream implemented-path wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-data-stream-wire-benchmark
delete_data_stream_request_encode iterations=400000 elapsed_ms=245.521 ops_per_second=1629188.85 nanos_per_op=613.80
delete_data_stream_request_decode iterations=400000 elapsed_ms=248.391 ops_per_second=1610364.68 nanos_per_op=620.98
delete_data_stream_request_validate iterations=400000 elapsed_ms=253.165 ops_per_second=1579997.57 nanos_per_op=632.91
delete_data_stream_ack_response_decode iterations=400000 elapsed_ms=54.170 ops_per_second=7384128.40 nanos_per_op=135.43
delete_data_stream_wire_bottleneck_ops_per_second=1579997.57
```

The current delete-data-stream implemented-path wire bottleneck is validation.
The request path carries the cluster-manager envelope and data-stream name
array before admitting exact/wildcard manifest-backed deletion. At roughly
0.88M ops/s in the latest local release run, the first performance point to
inspect is repeated timeout and names-array validation before the runtime path
reaches wildcard metadata scans, backing-index document removal, and stale
PIT-context pruning.

Current get-data-stream implemented-path wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-data-stream-wire-benchmark
get_data_stream_request_encode iterations=400000 elapsed_ms=212.036 ops_per_second=1886469.61 nanos_per_op=530.09
get_data_stream_request_decode iterations=400000 elapsed_ms=198.051 ops_per_second=2019677.02 nanos_per_op=495.13
get_data_stream_request_validate iterations=400000 elapsed_ms=197.826 ops_per_second=2021982.72 nanos_per_op=494.56
get_data_stream_response_encode iterations=400000 elapsed_ms=86.874 ops_per_second=4604355.82 nanos_per_op=217.19
get_data_stream_response_decode iterations=400000 elapsed_ms=91.142 ops_per_second=4388756.97 nanos_per_op=227.85
get_data_stream_wire_bottleneck_ops_per_second=1886469.61
```

The current get-data-stream implemented-path bottleneck is request encode.
This path carries the ClusterManagerNodeRead envelope and default empty optional
data-stream name array plus an empty `GetDataStreamAction.Response`. At roughly
1.89M ops/s in the latest local release run, the path remains in the lightweight
admin transport range and does not expose a material response-codec bottleneck.

Current data-streams-stats implemented-path wire microbenchmark:

```text
cargo run -p os-transport --release --bin data-streams-stats-wire-benchmark
data_streams_stats_request_encode iterations=400000 elapsed_ms=244.057 ops_per_second=1638962.08 nanos_per_op=610.14
data_streams_stats_request_decode iterations=400000 elapsed_ms=235.910 ops_per_second=1695565.16 nanos_per_op=589.77
data_streams_stats_request_validate iterations=400000 elapsed_ms=237.678 ops_per_second=1682948.36 nanos_per_op=594.20
data_streams_stats_response_encode iterations=400000 elapsed_ms=104.884 ops_per_second=3813725.88 nanos_per_op=262.21
data_streams_stats_response_decode iterations=400000 elapsed_ms=102.139 ops_per_second=3916221.03 nanos_per_op=255.35
data_streams_stats_wire_bottleneck_ops_per_second=1638962.08
```

The current data-streams-stats implemented-path bottleneck is request
encode. This path carries the BroadcastRequest parent task, empty name array,
strict open forbid-closed index options, and an empty
`DataStreamsStatsAction.Response`. At roughly 1.64M ops/s in the latest local
release run, it stays in the lightweight admin transport range and does not
expose a material response-codec bottleneck.

Current resolve-index wire microbenchmark:

```text
cargo run -p os-transport --release --bin resolve-index-wire-benchmark
resolve_index_request_encode iterations=400000 elapsed_ms=221.486 ops_per_second=1805983.85 nanos_per_op=553.71
resolve_index_request_decode iterations=400000 elapsed_ms=246.844 ops_per_second=1620456.34 nanos_per_op=617.11
resolve_index_request_validate iterations=400000 elapsed_ms=252.841 ops_per_second=1582019.25 nanos_per_op=632.10
resolve_index_response_decode iterations=400000 elapsed_ms=66.352 ops_per_second=6028461.94 nanos_per_op=165.88
resolve_index_wire_bottleneck_ops_per_second=1582019.25
```

The current resolve-index wire boundary bottleneck is request validation. This
path carries the ActionRequest parent task, wildcard name array, and strict open
index options before manifest-backed execution. At roughly 1.57M ops/s in the
latest local release run, it stays in the lightweight metadata transport range;
the next performance-sensitive work is keeping manifest index, alias, and
data-stream matching cheap as metadata grows.

Current create-view reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin create-view-reject-wire-benchmark
create_view_reject_request_encode iterations=400000 elapsed_ms=336.649 ops_per_second=1188182.52 nanos_per_op=841.62
create_view_reject_request_decode iterations=400000 elapsed_ms=334.119 ops_per_second=1197179.29 nanos_per_op=835.30
create_view_reject_validation iterations=400000 elapsed_ms=344.107 ops_per_second=1162430.32 nanos_per_op=860.27
create_view_response_decode iterations=400000 elapsed_ms=201.902 ops_per_second=1981162.08 nanos_per_op=504.75
create_view_reject_wire_bottleneck_ops_per_second=1162430.32
```

The current create-view fail-closed boundary bottleneck is validation. This
path carries the ClusterManagerNode envelope, view name, description, and
target index-pattern list before rejecting at admission. At roughly 1.16M ops/s
in the latest local release run, the extra string length and target-list checks
make it heavier than the adjacent data-stream and resolve-index reject paths.
Future performance-sensitive work is target resolution, view metadata mutation,
and response rendering.

Current delete-view reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-view-reject-wire-benchmark
delete_view_reject_request_encode iterations=400000 elapsed_ms=244.549 ops_per_second=1635665.72 nanos_per_op=611.37
delete_view_reject_request_decode iterations=400000 elapsed_ms=233.180 ops_per_second=1715410.05 nanos_per_op=582.95
delete_view_reject_validation iterations=400000 elapsed_ms=240.750 ops_per_second=1661473.52 nanos_per_op=601.88
delete_view_ack_response_decode iterations=400000 elapsed_ms=83.777 ops_per_second=4774580.71 nanos_per_op=209.44
delete_view_reject_wire_bottleneck_ops_per_second=1635665.72
```

The current delete-view fail-closed boundary bottleneck is request encode. This
path carries the ClusterManagerNode envelope and view name before rejecting at
admission. At roughly 1.64M ops/s in the latest local release run, it is back
in the lightweight metadata transport range; future performance-sensitive work
is view lookup, metadata deletion, and acknowledgement rendering.

Current get-view reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-view-reject-wire-benchmark
get_view_reject_request_encode iterations=400000 elapsed_ms=225.375 ops_per_second=1774818.77 nanos_per_op=563.44
get_view_reject_request_decode iterations=400000 elapsed_ms=216.097 ops_per_second=1851017.89 nanos_per_op=540.24
get_view_reject_validation iterations=400000 elapsed_ms=223.282 ops_per_second=1791452.81 nanos_per_op=558.21
get_view_response_decode iterations=400000 elapsed_ms=200.093 ops_per_second=1999067.56 nanos_per_op=500.23
get_view_reject_wire_bottleneck_ops_per_second=1774818.77
```

The current get-view fail-closed boundary bottleneck is request encode. This
path carries the ClusterManagerNode envelope and view name before rejecting at
admission, while response decode covers the `View` payload shape already shared
with create-view. At roughly 1.77M ops/s in the latest local release run, the
current wire boundary remains lightweight; future performance-sensitive work is
view lookup and response rendering.

Current update-view reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin update-view-reject-wire-benchmark
update_view_reject_request_encode iterations=400000 elapsed_ms=376.565 ops_per_second=1062233.21 nanos_per_op=941.41
update_view_reject_request_decode iterations=400000 elapsed_ms=326.892 ops_per_second=1223646.53 nanos_per_op=817.23
update_view_reject_validation iterations=400000 elapsed_ms=337.159 ops_per_second=1186384.28 nanos_per_op=842.90
update_view_response_decode iterations=400000 elapsed_ms=202.532 ops_per_second=1974996.66 nanos_per_op=506.33
update_view_reject_wire_bottleneck_ops_per_second=1062233.21
```

The current update-view fail-closed boundary bottleneck is request encode. This
path carries the same `CreateViewAction.Request` payload as create-view under
the OpenSearch update action name before rejecting at admission. At roughly
1.06M ops/s in the latest local release run, it is slightly slower than the
latest create-view run on this machine; future performance-sensitive work is
view validation, target resolution, metadata mutation, and response rendering.

Current list-view-names supported-subset wire microbenchmark:

```text
cargo run -p os-transport --release --bin list-view-names-wire-benchmark
list_view_names_request_encode iterations=400000 elapsed_ms=158.070 ops_per_second=2530521.07 nanos_per_op=395.18
list_view_names_request_decode iterations=400000 elapsed_ms=144.318 ops_per_second=2771653.94 nanos_per_op=360.80
list_view_names_request_validate iterations=400000 elapsed_ms=143.681 ops_per_second=2783948.94 nanos_per_op=359.20
list_view_names_response_encode iterations=400000 elapsed_ms=51.196 ops_per_second=7813183.20 nanos_per_op=127.99
list_view_names_response_decode iterations=400000 elapsed_ms=58.059 ops_per_second=6889506.97 nanos_per_op=145.15
list_view_names_wire_bottleneck_ops_per_second=2530521.07
```

The current list-view-names supported subset bottleneck is request encode. This
path carries an empty request body, validates the supported subset, and renders
an empty OpenSearch `views` string list response. At roughly 2.53M ops/s in the
latest local release run, this adapter does not expose a material wire-codec
regression; future performance-sensitive work is populated view-name listing.

Current search-view reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin search-view-reject-wire-benchmark
search_view_reject_request_encode iterations=400000 elapsed_ms=311.868 ops_per_second=1282592.92 nanos_per_op=779.67
search_view_reject_request_decode iterations=400000 elapsed_ms=278.718 ops_per_second=1435144.35 nanos_per_op=696.79
search_view_reject_validation iterations=400000 elapsed_ms=291.262 ops_per_second=1373333.56 nanos_per_op=728.16
search_view_reject_wire_bottleneck_ops_per_second=1282592.92
```

The current search-view fail-closed boundary bottleneck is request encode. This
path carries the existing `SearchRequest` wire payload plus the OpenSearch view
name string before rejecting at admission. At roughly 1.28M ops/s in the latest
local release run, it stays close to the existing search reject path; future
performance-sensitive work is view lookup, target index resolution, search
execution, and `SearchResponse` rendering.

Current start-persistent-task reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin start-persistent-task-reject-wire-benchmark
start_persistent_task_reject_request_encode iterations=400000 elapsed_ms=513.472 ops_per_second=779010.24 nanos_per_op=1283.68
start_persistent_task_reject_request_decode iterations=400000 elapsed_ms=455.093 ops_per_second=878941.47 nanos_per_op=1137.73
start_persistent_task_reject_validation iterations=400000 elapsed_ms=470.462 ops_per_second=850228.83 nanos_per_op=1176.15
start_persistent_task_empty_response_decode iterations=400000 elapsed_ms=54.776 ops_per_second=7302532.23 nanos_per_op=136.94
start_persistent_task_reject_wire_bottleneck_ops_per_second=779010.24
```

The current start-persistent-task fail-closed boundary bottleneck is request
encode. This path carries the ClusterManagerNode envelope, task id, task name,
and persistent-task params named-writeable marker before rejecting at
admission. At roughly 779K ops/s in the latest local release run, the longer
task/params strings make it heavier than the adjacent view-admin boundaries;
future performance-sensitive work is params named-writeable decode, cluster
metadata mutation, task assignment, and response rendering.

Current update-persistent-task-status reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin update-persistent-task-status-reject-wire-benchmark
update_persistent_task_status_reject_request_encode iterations=400000 elapsed_ms=310.972 ops_per_second=1286288.70 nanos_per_op=777.43
update_persistent_task_status_reject_request_decode iterations=400000 elapsed_ms=278.119 ops_per_second=1438233.49 nanos_per_op=695.30
update_persistent_task_status_reject_validation iterations=400000 elapsed_ms=283.443 ops_per_second=1411220.44 nanos_per_op=708.61
update_persistent_task_status_empty_response_decode iterations=400000 elapsed_ms=54.428 ops_per_second=7349123.28 nanos_per_op=136.07
update_persistent_task_status_reject_wire_bottleneck_ops_per_second=1286288.70
```

The current update-persistent-task-status fail-closed boundary bottleneck is
request encode. This path carries the ClusterManagerNode envelope, task id,
allocation id, and absent state marker before rejecting at admission. At
roughly 1.29M ops/s in the latest local release run, it is lighter than the
start-persistent-task boundary because it avoids the task-name/params-name
strings; future performance-sensitive work is state named-writeable decode,
allocation checks, cluster metadata mutation, and response rendering.

Current completion-persistent-task reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin completion-persistent-task-reject-wire-benchmark
completion_persistent_task_reject_request_encode iterations=400000 elapsed_ms=300.951 ops_per_second=1329121.40 nanos_per_op=752.38
completion_persistent_task_reject_request_decode iterations=400000 elapsed_ms=270.317 ops_per_second=1479743.26 nanos_per_op=675.79
completion_persistent_task_reject_validation iterations=400000 elapsed_ms=276.649 ops_per_second=1445874.93 nanos_per_op=691.62
completion_persistent_task_empty_response_decode iterations=400000 elapsed_ms=53.964 ops_per_second=7412411.75 nanos_per_op=134.91
completion_persistent_task_reject_wire_bottleneck_ops_per_second=1329121.40
```

The current completion-persistent-task fail-closed boundary bottleneck is
request encode. This path carries the ClusterManagerNode envelope, task id,
allocation id, and null exception marker before rejecting at admission. At
roughly 1.33M ops/s in the latest local release run, it is close to the
update-persistent-task-status boundary; future performance-sensitive work is
exception payload decoding, allocation checks, cluster metadata mutation,
restart/removal semantics, and response rendering.

Current remove-persistent-task reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin remove-persistent-task-reject-wire-benchmark
remove_persistent_task_reject_request_encode iterations=400000 elapsed_ms=304.565 ops_per_second=1313347.09 nanos_per_op=761.41
remove_persistent_task_reject_request_decode iterations=400000 elapsed_ms=286.942 ops_per_second=1394011.82 nanos_per_op=717.35
remove_persistent_task_reject_validation iterations=400000 elapsed_ms=272.016 ops_per_second=1470500.70 nanos_per_op=680.04
remove_persistent_task_empty_response_decode iterations=400000 elapsed_ms=54.764 ops_per_second=7304037.16 nanos_per_op=136.91
remove_persistent_task_reject_wire_bottleneck_ops_per_second=1313347.09
```

The current remove-persistent-task fail-closed boundary bottleneck is request
encode. This path carries the ClusterManagerNode envelope and task id before
rejecting at admission. At roughly 1.31M ops/s in the latest local release run,
it is in the same range as the adjacent persistent-task admin boundaries;
future performance-sensitive work is persistent task lookup, cluster metadata
removal, and response rendering.

Current add-retention-lease reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin add-retention-lease-reject-wire-benchmark
add_retention_lease_reject_request_encode iterations=400000 elapsed_ms=656.813 ops_per_second=609001.47 nanos_per_op=1642.03
add_retention_lease_reject_request_decode iterations=400000 elapsed_ms=516.681 ops_per_second=774172.51 nanos_per_op=1291.70
add_retention_lease_reject_validation iterations=400000 elapsed_ms=530.498 ops_per_second=754008.96 nanos_per_op=1326.24
add_retention_lease_empty_response_decode iterations=400000 elapsed_ms=36.076 ops_per_second=11087550.07 nanos_per_op=90.19
add_retention_lease_reject_wire_bottleneck_ops_per_second=609001.47
```

The current add-retention-lease fail-closed boundary bottleneck is request
encode. This path carries the `SingleShardRequest` envelope, explicit
`ShardId`, lease id, retaining sequence number, and source before rejecting at
admission. At roughly 609K ops/s in the latest local release run, it is heavier
than the adjacent persistent-task admin boundaries because it serializes more
index/shard and lease metadata; future performance-sensitive work is shard
routing, primary operation permit acquisition, retention lease mutation, sync,
and response rendering.

Current renew-retention-lease reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin renew-retention-lease-reject-wire-benchmark
renew_retention_lease_reject_request_encode iterations=400000 elapsed_ms=611.366 ops_per_second=654272.47 nanos_per_op=1528.42
renew_retention_lease_reject_request_decode iterations=400000 elapsed_ms=565.136 ops_per_second=707793.65 nanos_per_op=1412.84
renew_retention_lease_reject_validation iterations=400000 elapsed_ms=675.584 ops_per_second=592080.58 nanos_per_op=1688.96
renew_retention_lease_empty_response_decode iterations=400000 elapsed_ms=36.711 ops_per_second=10895947.33 nanos_per_op=91.78
renew_retention_lease_reject_wire_bottleneck_ops_per_second=592080.58
```

The current renew-retention-lease fail-closed boundary bottleneck is validation
and reject construction. This path carries the same `SingleShardRequest`
envelope, explicit `ShardId`, lease id, retaining sequence number, and source
as add-retention-lease, then performs shard/index and lease-shape checks before
rejecting at admission. At roughly 592K ops/s in the latest local release run,
future performance-sensitive work is shard routing, primary operation permit
acquisition, retention lease renewal, and response rendering.

Current remove-retention-lease reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin remove-retention-lease-reject-wire-benchmark
remove_retention_lease_reject_request_encode iterations=400000 elapsed_ms=805.514 ops_per_second=496577.62 nanos_per_op=2013.78
remove_retention_lease_reject_request_decode iterations=400000 elapsed_ms=980.501 ops_per_second=407954.79 nanos_per_op=2451.25
remove_retention_lease_reject_validation iterations=400000 elapsed_ms=781.708 ops_per_second=511699.96 nanos_per_op=1954.27
remove_retention_lease_empty_response_decode iterations=400000 elapsed_ms=40.883 ops_per_second=9784041.98 nanos_per_op=102.21
remove_retention_lease_reject_wire_bottleneck_ops_per_second=407954.79
```

The current remove-retention-lease fail-closed boundary bottleneck is request
decode. This path carries the `SingleShardRequest` envelope, explicit
`ShardId`, and lease id before rejecting at admission. At roughly 408K ops/s in
the latest local release run, it is currently slower than add/renew in this
microbenchmark despite the smaller payload; future performance-sensitive work
is shard routing, primary operation permit acquisition, retention lease
removal, sync, and response rendering.

Current list-dangling-indices supported-subset wire microbenchmark:

```text
cargo run -p os-transport --release --bin list-dangling-indices-wire-benchmark
list_dangling_indices_request_encode iterations=400000 elapsed_ms=222.263 ops_per_second=1799669.27 nanos_per_op=555.66
list_dangling_indices_request_decode iterations=400000 elapsed_ms=215.356 ops_per_second=1857390.37 nanos_per_op=538.39
list_dangling_indices_request_validate iterations=400000 elapsed_ms=214.513 ops_per_second=1864686.55 nanos_per_op=536.28
list_dangling_indices_response_encode iterations=400000 elapsed_ms=98.103 ops_per_second=4077351.27 nanos_per_op=245.26
list_dangling_indices_response_decode iterations=400000 elapsed_ms=97.566 ops_per_second=4099788.06 nanos_per_op=243.92
list_dangling_indices_wire_bottleneck_ops_per_second=1799669.27
```

The current list-dangling-indices supported subset bottleneck is request
encode. This path carries the `BaseNodesRequest` envelope and optional index
UUID filter, validates the empty-dangling subset, and renders an empty
OpenSearch BaseNodes response. At roughly 1.80M ops/s in the latest local
release run, the adapter does not expose a material wire-codec regression;
future performance-sensitive work is populated dangling index state scan,
node aggregation, and failure decoding.

Current import-dangling-index reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin import-dangling-index-reject-wire-benchmark
import_dangling_index_reject_request_encode iterations=400000 elapsed_ms=603.521 ops_per_second=662777.21 nanos_per_op=1508.80
import_dangling_index_reject_request_decode iterations=400000 elapsed_ms=740.160 ops_per_second=540423.57 nanos_per_op=1850.40
import_dangling_index_reject_validation iterations=400000 elapsed_ms=629.356 ops_per_second=635570.48 nanos_per_op=1573.39
import_dangling_index_ack_response_decode iterations=400000 elapsed_ms=78.197 ops_per_second=5115277.12 nanos_per_op=195.49
import_dangling_index_reject_wire_bottleneck_ops_per_second=540423.57
```

The current import-dangling-index fail-closed boundary bottleneck is request
decode. This path carries the `AcknowledgedRequest` cluster-manager timeout,
ack timeout, index UUID, and `acceptDataLoss` flag before rejecting at
admission. At roughly 540K ops/s in the latest local release run, future
performance-sensitive work is dangling index lookup, allocation, cluster
metadata mutation, and acknowledgement rendering.

Current delete-dangling-index reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-dangling-index-reject-wire-benchmark
delete_dangling_index_reject_request_encode iterations=400000 elapsed_ms=345.658 ops_per_second=1157213.56 nanos_per_op=864.14
delete_dangling_index_reject_request_decode iterations=400000 elapsed_ms=310.493 ops_per_second=1288275.70 nanos_per_op=776.23
delete_dangling_index_reject_validation iterations=400000 elapsed_ms=315.616 ops_per_second=1267362.73 nanos_per_op=789.04
delete_dangling_index_ack_response_decode iterations=400000 elapsed_ms=54.123 ops_per_second=7390549.56 nanos_per_op=135.31
delete_dangling_index_reject_wire_bottleneck_ops_per_second=1157213.56
```

The current delete-dangling-index fail-closed boundary bottleneck is request
encode. This path carries the `AcknowledgedRequest` cluster-manager timeout,
ack timeout, index UUID, and `acceptDataLoss` flag before rejecting at
admission. At roughly 1.16M ops/s in the latest local release run, future
performance-sensitive work is dangling index lookup, index graveyard mutation,
cluster metadata publication, and acknowledgement rendering.

Current find-dangling-index supported-subset wire microbenchmark:

```text
cargo run -p os-transport --release --bin find-dangling-index-wire-benchmark
find_dangling_index_request_encode iterations=400000 elapsed_ms=330.446 ops_per_second=1210485.44 nanos_per_op=826.11
find_dangling_index_request_decode iterations=400000 elapsed_ms=304.380 ops_per_second=1314145.70 nanos_per_op=760.95
find_dangling_index_request_validate iterations=400000 elapsed_ms=302.534 ops_per_second=1322165.11 nanos_per_op=756.34
find_dangling_index_response_encode iterations=400000 elapsed_ms=95.970 ops_per_second=4167967.72 nanos_per_op=239.93
find_dangling_index_response_decode iterations=400000 elapsed_ms=97.525 ops_per_second=4101522.23 nanos_per_op=243.81
find_dangling_index_wire_bottleneck_ops_per_second=1210485.44
```

The current find-dangling-index supported subset bottleneck is request encode.
This path carries the `BaseNodesRequest` node filter, timeout, and required
index UUID, validates the explicit-UUID empty-result subset, and renders an
empty OpenSearch BaseNodes response. At roughly 1.21M ops/s in the latest local
release run, the adapter does not expose a material wire-codec regression;
future performance-sensitive work is populated dangling index state scan, node
`IndexMetadata` aggregation, and failure decoding.

Current search reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin search-reject-wire-benchmark
search_reject_request_encode iterations=400000 elapsed_ms=308.102 ops_per_second=1298272.69 nanos_per_op=770.25
search_reject_request_decode iterations=400000 elapsed_ms=269.287 ops_per_second=1485402.32 nanos_per_op=673.22
search_reject_validation iterations=400000 elapsed_ms=251.641 ops_per_second=1589565.42 nanos_per_op=629.10
search_reject_wire_bottleneck_ops_per_second=1298272.69
```

The current search fail-closed boundary bottleneck is request encode. This path
is heavier than the metadata reject boundaries because it writes the full
top-level `SearchRequest` control envelope, including search type,
request-cache option, reduce/fanout controls, cross-cluster flags, pipeline,
phase timing, and strict open forbid-closed ignore-throttled index options,
before rejecting execution. At roughly 1.30M ops/s in the latest local release
run, the boundary stays in the lightweight transport range; the first
performance point to inspect before accepting search execution is still search
source decode/rendering, which is intentionally not admitted here.

Current stream-search reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin stream-search-reject-wire-benchmark
stream_search_reject_request_encode iterations=400000 elapsed_ms=304.482 ops_per_second=1313707.26 nanos_per_op=761.20
stream_search_reject_request_decode iterations=400000 elapsed_ms=258.298 ops_per_second=1548596.74 nanos_per_op=645.75
stream_search_reject_validation iterations=400000 elapsed_ms=269.541 ops_per_second=1484005.46 nanos_per_op=673.85
stream_search_reject_wire_bottleneck_ops_per_second=1313707.26
```

The current stream-search fail-closed boundary bottleneck is request encode.
This path uses the same bounded `SearchRequest` control envelope as normal
search, but binds it to the `indices:data/read/search/stream` action name. At
roughly 1.31M ops/s in the latest local release run, it tracks the normal search
reject path closely; the first performance point to inspect before accepting
stream-search execution is streaming response rendering and backpressure.

Current multi-search reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin multi-search-reject-wire-benchmark
multi_search_reject_request_encode iterations=250000 elapsed_ms=214.912 ops_per_second=1163264.27 nanos_per_op=859.65
multi_search_reject_request_decode iterations=250000 elapsed_ms=215.766 ops_per_second=1158664.99 nanos_per_op=863.06
multi_search_reject_validation iterations=250000 elapsed_ms=219.333 ops_per_second=1139820.43 nanos_per_op=877.33
multi_search_reject_wire_bottleneck_ops_per_second=1139820.43
multi_search_reject_wire_bottleneck_items_per_second=2279640.86
```

The current multi-search fail-closed boundary bottleneck is validation. This
benchmark uses a two-request batch, so the boundary validates the outer
`MultiSearchRequest` envelope and two nested default `SearchRequest` control
envelopes before rejecting execution. At roughly 1.14M batches/s and 2.28M
sub-searches/s in the latest local release run, the nested control-envelope
path is still lightweight; the first performance point to inspect before
accepting multi-search execution is batched search source decode and response
aggregation.

Current search-scroll reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin search-scroll-reject-wire-benchmark
search_scroll_reject_request_encode iterations=400000 elapsed_ms=267.102 ops_per_second=1497553.09 nanos_per_op=667.76
search_scroll_reject_request_decode iterations=400000 elapsed_ms=255.354 ops_per_second=1566452.39 nanos_per_op=638.39
search_scroll_reject_validation iterations=400000 elapsed_ms=248.034 ops_per_second=1612682.60 nanos_per_op=620.08
search_scroll_reject_wire_bottleneck_ops_per_second=1497553.09
```

The current search-scroll fail-closed boundary bottleneck is request encode.
This path carries only the ActionRequest parent task, scroll id, and optional
keep-alive time value before rejecting execution. At roughly 1.50M ops/s in the
latest local release run, it remains a lightweight scroll control boundary; the
first performance point to inspect before accepting execution is scroll context
lookup/update and search response rendering.

Current clear-scroll wire microbenchmark:

```text
cargo run -p os-transport --release --bin clear-scroll-wire-benchmark
clear_scroll_request_encode iterations=400000 elapsed_ms=240.974 ops_per_second=1659933.10 nanos_per_op=602.43
clear_scroll_request_decode iterations=400000 elapsed_ms=228.345 ops_per_second=1751735.57 nanos_per_op=570.86
clear_scroll_request_validate iterations=400000 elapsed_ms=230.099 ops_per_second=1738379.28 nanos_per_op=575.25
clear_scroll_response_encode iterations=400000 elapsed_ms=48.438 ops_per_second=8258064.52 nanos_per_op=121.09
clear_scroll_response_decode iterations=400000 elapsed_ms=57.521 ops_per_second=6954027.24 nanos_per_op=143.80
clear_scroll_wire_bottleneck_ops_per_second=1659933.10
```

The current clear-scroll implemented subset bottleneck is request encode. The
small response encode/decode path runs above 6.9M ops/s in the latest local
release run, so response rendering is not the first bottleneck. The first
performance point to inspect before expanding this subset is explicit scroll id
parsing plus context invalidation.

Current explain reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin explain-reject-wire-benchmark
explain_reject_request_encode iterations=400000 elapsed_ms=291.836 ops_per_second=1370630.91 nanos_per_op=729.59
explain_reject_request_decode iterations=400000 elapsed_ms=296.173 ops_per_second=1350561.07 nanos_per_op=740.43
explain_reject_validation iterations=400000 elapsed_ms=299.151 ops_per_second=1337117.22 nanos_per_op=747.88
explain_reject_wire_bottleneck_ops_per_second=1337117.22
```

The current explain fail-closed boundary bottleneck is validation. This path
checks the bounded single-shard request envelope, query marker, alias/filter
markers, stored-field marker, and fetch-source marker before rejecting
execution. At roughly 1.34M ops/s in the latest local release run, the boundary
itself is lightweight; the first performance point to inspect before accepting
execution is query builder decode/rewrite plus explanation tree rendering.

Current delete-PIT wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-pit-wire-benchmark
delete_pit_request_encode iterations=400000 elapsed_ms=334.055 ops_per_second=1197406.62 nanos_per_op=835.14
delete_pit_request_decode iterations=400000 elapsed_ms=387.371 ops_per_second=1032601.14 nanos_per_op=968.43
delete_pit_request_validate iterations=400000 elapsed_ms=521.794 ops_per_second=766586.12 nanos_per_op=1304.48
delete_pit_response_encode iterations=400000 elapsed_ms=163.406 ops_per_second=2447887.46 nanos_per_op=408.52
delete_pit_response_decode iterations=400000 elapsed_ms=306.315 ops_per_second=1305844.02 nanos_per_op=765.79
delete_pit_wire_bottleneck_ops_per_second=766586.12
```

The current delete-PIT wire subset bottleneck is request validation with
explicit PIT ids. The non-empty response encode/decode path for two
`DeletePitInfo` entries remains above 1.30M ops/s in the latest local release
run, so response rendering is not the first bottleneck. The first performance
point to inspect while expanding execution is lock hold time and allocation in
shared PIT context invalidation.

Current get-all-PITs wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-all-pits-wire-benchmark
get_all_pits_request_encode iterations=400000 elapsed_ms=225.282 ops_per_second=1775554.57 nanos_per_op=563.20
get_all_pits_request_decode iterations=400000 elapsed_ms=223.586 ops_per_second=1789017.01 nanos_per_op=558.97
get_all_pits_request_validate iterations=400000 elapsed_ms=223.654 ops_per_second=1788473.07 nanos_per_op=559.14
get_all_pits_response_encode iterations=400000 elapsed_ms=734.189 ops_per_second=544818.87 nanos_per_op=1835.47
get_all_pits_response_decode iterations=400000 elapsed_ms=739.662 ops_per_second=540787.57 nanos_per_op=1849.15
get_all_pits_wire_bottleneck_ops_per_second=540787.57
```

The current get-all-PITs wire subset bottleneck is non-empty response decode
with one `DiscoveryNode` and two `ListPitInfo` entries. The first performance
point to inspect before expanding execution is avoiding repeated node metadata
serialization and minimizing lock hold time around shared PIT context listing.

Current create-PIT wire microbenchmark:

```text
cargo run -p os-transport --release --bin create-pit-wire-benchmark
create_pit_request_encode iterations=400000 elapsed_ms=282.549 ops_per_second=1415681.86 nanos_per_op=706.37
create_pit_request_decode iterations=400000 elapsed_ms=264.046 ops_per_second=1514885.58 nanos_per_op=660.12
create_pit_request_validate iterations=400000 elapsed_ms=264.766 ops_per_second=1510768.96 nanos_per_op=661.91
create_pit_response_encode iterations=400000 elapsed_ms=124.121 ops_per_second=3222667.00 nanos_per_op=310.30
create_pit_response_decode iterations=400000 elapsed_ms=104.947 ops_per_second=3811462.94 nanos_per_op=262.37
create_pit_wire_bottleneck_ops_per_second=1415681.86
```

The current create-PIT wire subset bottleneck is request encode. This path
carries the ActionRequest parent task, index target controls, keep-alive, and
explicit partial-creation flag before admitting the local transport PIT
lifecycle subset. Runtime create-PIT now also resolves index/alias/wildcard and
data-stream targets with OpenSearch-style index option guards, applies routing
filters, and captures the shared SteelNode document snapshot while accepting
create-PIT preference and explicit partial-creation flags for the local
all-success shard subset. The transport reader-context path is covered
separately: create-reader-context allocates a local snapshot, update-reader-context
attaches the final PIT id/creation time/keep-alive, PIT search reuses that
snapshot and extends keep-alive, and free-PIT-context clears both reader and PIT
context state. The first runtime performance point to inspect while expanding
the path is lock hold time and snapshot allocation around larger document sets.

Current PIT reader-context wire microbenchmark:

```text
cargo run -p os-transport --release --bin pit-reader-context-wire-benchmark
pit_reader_create_request_encode iterations=400000 elapsed_ms=333.565 ops_per_second=1199168.13 nanos_per_op=833.91
pit_reader_create_request_decode iterations=400000 elapsed_ms=317.377 ops_per_second=1260330.07 nanos_per_op=793.44
pit_reader_create_response_encode iterations=400000 elapsed_ms=116.433 ops_per_second=3435450.61 nanos_per_op=291.08
pit_reader_create_response_decode iterations=400000 elapsed_ms=104.638 ops_per_second=3822715.38 nanos_per_op=261.59
pit_reader_update_request_encode iterations=400000 elapsed_ms=351.594 ops_per_second=1137676.69 nanos_per_op=878.98
pit_reader_update_request_decode iterations=400000 elapsed_ms=324.376 ops_per_second=1233137.30 nanos_per_op=810.94
pit_reader_update_response_encode iterations=400000 elapsed_ms=116.955 ops_per_second=3420110.16 nanos_per_op=292.39
pit_reader_update_response_decode iterations=400000 elapsed_ms=96.012 ops_per_second=4166143.25 nanos_per_op=240.03
pit_reader_free_request_encode iterations=400000 elapsed_ms=406.358 ops_per_second=984352.70 nanos_per_op=1015.90
pit_reader_free_request_decode iterations=400000 elapsed_ms=379.447 ops_per_second=1054165.89 nanos_per_op=948.62
pit_reader_free_response_encode iterations=400000 elapsed_ms=100.972 ops_per_second=3961504.20 nanos_per_op=252.43
pit_reader_free_response_decode iterations=400000 elapsed_ms=105.275 ops_per_second=3799575.87 nanos_per_op=263.19
pit_reader_context_wire_bottleneck_ops_per_second=984352.70
```

The current PIT reader-context wire bottleneck is free-PIT-context request
encode with one local context id. Create/update response rendering remains
above 3.4M ops/s in the latest local release run, so the first performance
point to inspect before expanding distributed reader-context fanout is request
payload allocation and context-id grouping, then runtime lock hold time around
reader context mutation.

Current PIT-segments wire microbenchmark:

```text
cargo run -p os-transport --release --bin pit-segments-wire-benchmark
pit_segments_request_encode iterations=400000 elapsed_ms=289.749 ops_per_second=1380505.49 nanos_per_op=724.37
pit_segments_request_decode iterations=400000 elapsed_ms=291.497 ops_per_second=1372228.72 nanos_per_op=728.74
pit_segments_request_validate iterations=400000 elapsed_ms=294.378 ops_per_second=1358795.24 nanos_per_op=735.95
pit_segments_response_encode iterations=400000 elapsed_ms=93.225 ops_per_second=4290698.19 nanos_per_op=233.06
pit_segments_response_decode iterations=400000 elapsed_ms=95.782 ops_per_second=4176138.45 nanos_per_op=239.46
pit_segments_wire_bottleneck_ops_per_second=1358795.24
```

The current PIT-segments supported-subset boundary bottleneck is request
validation. This path carries the ActionRequest parent task, broadcast index
controls, PIT id string array, and verbose flag before accepting the empty
`_all` or existing explicit-id response subset. At roughly 1.36M ops/s, the
boundary itself is lightweight; response encode/decode stays above 4.2M ops/s.
The first performance point to inspect before expanding execution is non-empty
PIT segment metadata response rendering.

Current indices-stats supported-subset wire microbenchmark:

```text
cargo run -p os-transport --release --bin indices-stats-wire-benchmark
indices_stats_request_encode ops_per_second=1467011.01 nanos_per_op=681.66
indices_stats_request_decode ops_per_second=1466008.80 nanos_per_op=682.12
indices_stats_supported_validation ops_per_second=1167065.14 nanos_per_op=856.85
indices_stats_wire_bottleneck_ops_per_second=1167065.14
```

The current indices-stats supported-subset boundary checks indices options and
the full `CommonStatsFlags` default shape after decode. The first
performance-sensitive work beyond this boundary is populating non-empty index
stats groups and rendering full stats responses. At roughly 1.17M ops/s in the
latest local run, this path does not introduce a new transport admission
hotspot.

Current pending-cluster-tasks wire microbenchmark:

```text
cargo run -p os-transport --release --bin pending-cluster-tasks-wire-benchmark
pending_cluster_tasks_request_encode ops_per_second=2134584.13 nanos_per_op=468.48
pending_cluster_tasks_response_encode ops_per_second=1136492.64 nanos_per_op=879.90
pending_cluster_tasks_request_decode ops_per_second=2348150.27 nanos_per_op=425.87
pending_cluster_tasks_response_decode ops_per_second=1394374.44 nanos_per_op=717.17
pending_cluster_tasks_wire_bottleneck_ops_per_second=1136492.64
```

The current pending-cluster-tasks wire bottleneck is non-empty response encode
for a two-task pending/in-flight response. The transport subset remains above
1.13M ops/s in the latest local release run; the next meaningful execution cost
to watch is live runtime pending task snapshot refresh when tasks are mutating.

Current list-tasks wire microbenchmark:

```text
cargo run -p os-transport --release --bin list-tasks-wire-benchmark
list_tasks_request_encode ops_per_second=2013427.53 nanos_per_op=496.67
list_tasks_response_encode ops_per_second=1122719.13 nanos_per_op=890.69
list_tasks_request_decode ops_per_second=1569815.67 nanos_per_op=637.02
list_tasks_response_decode ops_per_second=1136817.18 nanos_per_op=879.65
list_tasks_wire_bottleneck_ops_per_second=1122719.13
```

The current list-tasks wire bottleneck is non-empty response encode for a
single tracked task info entry. At roughly 1.12M ops/s in the latest local
release run, this path remains above the current task transport admission
budget; the next cost to watch is live task snapshot refresh while task state is
mutating.

Current cancel-tasks wire microbenchmark:

```text
cargo run -p os-transport --release --bin cancel-tasks-wire-benchmark
cancel_tasks_request_encode iterations=400000 elapsed_ms=309.156 ops_per_second=1293844.95 nanos_per_op=772.89
cancel_tasks_response_encode iterations=400000 elapsed_ms=423.429 ops_per_second=944668.81 nanos_per_op=1058.57
cancel_tasks_request_decode iterations=400000 elapsed_ms=299.690 ops_per_second=1334714.29 nanos_per_op=749.22
cancel_tasks_response_decode iterations=400000 elapsed_ms=400.549 ops_per_second=998628.97 nanos_per_op=1001.37
cancel_tasks_wire_bottleneck_ops_per_second=944668.81
```

The current cancel-tasks wire bottleneck is non-empty response encode for a
single cancelled queued task info entry. The latest local release run uses an
explicit task id request and remains just under 1.0M ops/s, so task info string
encoding remains the next transport-wire cost to watch while broader
cancellation lifecycle semantics are added.

Current get-task wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-task-wire-benchmark
get_task_request_encode iterations=400000 elapsed_ms=234.590 ops_per_second=1705099.41 nanos_per_op=586.48
get_task_request_decode iterations=400000 elapsed_ms=225.763 ops_per_second=1771771.83 nanos_per_op=564.41
get_task_request_validate iterations=400000 elapsed_ms=225.438 ops_per_second=1774322.34 nanos_per_op=563.60
get_task_response_encode iterations=400000 elapsed_ms=342.966 ops_per_second=1166296.71 nanos_per_op=857.41
get_task_response_decode iterations=400000 elapsed_ms=338.342 ops_per_second=1182236.52 nanos_per_op=845.85
get_task_wire_bottleneck_ops_per_second=1166296.71
```

The current get-task wire bottleneck is running response encode for a single
task info entry. Request validation remains decode-adjacent at roughly 1.77M
ops/s, while the response path is roughly 1.17M ops/s because it carries the
task info strings. This is in the same range as the list/cancel task response
paths, so the new point lookup subset does not introduce a separate transport
wire bottleneck.

Current get wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-wire-benchmark
get_request_encode ops_per_second=1311541.69 nanos_per_op=762.46
get_response_encode ops_per_second=1279950.45 nanos_per_op=781.28
get_request_decode ops_per_second=1428868.05 nanos_per_op=699.85
get_response_decode ops_per_second=1066318.28 nanos_per_op=937.81
get_wire_bottleneck_ops_per_second=1066318.28
```

The current get wire bottleneck is response decode, which includes JSON source
decode for the benchmark payload. At roughly 1.07M ops/s in the latest local
release run, this adapter is also not the bottleneck relative to the existing
HTTP search/write/refresh benchmark paths. Re-run the command above after each
get transport adapter change that affects request/response framing or source
materialization.

Current term-vectors reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin term-vectors-reject-wire-benchmark
term_vectors_reject_request_encode iterations=400000 elapsed_ms=297.994 ops_per_second=1342308.16 nanos_per_op=744.99
term_vectors_reject_request_decode iterations=400000 elapsed_ms=278.066 ops_per_second=1438505.86 nanos_per_op=695.17
term_vectors_reject_validation iterations=400000 elapsed_ms=281.866 ops_per_second=1419115.39 nanos_per_op=704.66
term_vectors_reject_wire_bottleneck_ops_per_second=1342308.16
```

The current term-vectors fail-closed boundary bottleneck is request encode. The
default benchmark writes the single-shard request envelope, optional index,
document id, absent doc/routing/preference markers, default flags, empty
selected fields, absent analyzer/filter settings, realtime flag, and default
versioning before rejecting execution. At roughly 1.34M ops/s in the latest
local release run, the remaining performance-sensitive work is shard routing,
postings/term-vector generation, analyzer lookup, term statistics collection,
and response rendering.

Current multi term-vectors reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin multi-term-vectors-reject-wire-benchmark
multi_term_vectors_reject_request_encode iterations=300000 elapsed_ms=373.203 ops_per_second=803853.09 nanos_per_op=1244.01
multi_term_vectors_reject_request_decode iterations=300000 elapsed_ms=308.525 ops_per_second=972368.93 nanos_per_op=1028.42
multi_term_vectors_reject_validation iterations=300000 elapsed_ms=350.007 ops_per_second=857124.58 nanos_per_op=1166.69
multi_term_vectors_reject_wire_bottleneck_ops_per_second=803853.09
```

The current multi term-vectors fail-closed boundary bottleneck is request
encode for a two-item batch. The benchmark writes the parent request envelope,
top-level preference marker, collection length, and two nested term-vectors
request envelopes before rejecting aggregate execution. At roughly 0.80M ops/s
in the latest local release run, the remaining performance-sensitive work is
per-item shard grouping, item-level term-vector generation, item failure
handling, and aggregate response rendering.

Current multi-get wire microbenchmark:

```text
cargo run -p os-transport --release --bin multi-get-wire-benchmark
multi_get_request_encode ops_per_second=489215.21 nanos_per_op=2044.09
multi_get_response_encode ops_per_second=329569.72 nanos_per_op=3034.26
multi_get_request_decode ops_per_second=410820.05 nanos_per_op=2434.16
multi_get_response_decode ops_per_second=166828.06 nanos_per_op=5994.20
multi_get_wire_bottleneck_ops_per_second=166828.06
multi_get_wire_bottleneck_items_per_second=1334624.45
```

The current multi-get wire bottleneck is response decode for an 8-item batch,
again because the benchmark includes JSON source decode for each found item.
At roughly 1.33M decoded items/s in the latest local release run, this adapter
is still below the existing HTTP path bottleneck risk. Re-run the command above
after each multi-get transport adapter change that affects response framing,
failure items, or source materialization.

Current index wire microbenchmark:

```text
cargo run -p os-transport --release --bin index-wire-benchmark
index_request_encode ops_per_second=839041.43 nanos_per_op=1191.84
index_response_encode ops_per_second=1885026.50 nanos_per_op=530.50
index_request_decode ops_per_second=720278.60 nanos_per_op=1388.35
index_response_decode ops_per_second=1908702.70 nanos_per_op=523.92
index_wire_bottleneck_ops_per_second=720278.60
```

The current index wire bottleneck is request decode. The request path decodes
the JSON source and more OpenSearch request fields than get/delete, while the
response path is comparable to delete because it uses the same doc-write
response envelope without source material. At roughly 720K ops/s in the latest
local release run, source decode is the first place to inspect if index
transport throughput becomes hot.

Current update wire microbenchmark:

```text
cargo run -p os-transport --release --bin update-wire-benchmark
update_request_encode ops_per_second=704142.25 nanos_per_op=1420.17
update_response_encode ops_per_second=1873884.03 nanos_per_op=533.65
update_request_decode ops_per_second=583615.43 nanos_per_op=1713.46
update_response_decode ops_per_second=1974250.64 nanos_per_op=506.52
update_wire_bottleneck_ops_per_second=583615.43
```

The current update wire bottleneck is request decode. This path decodes the
update envelope plus a nested doc `IndexRequest`, including JSON source
material, so it is slower than standalone index. At roughly 584K ops/s in the
latest local release run, nested request/source materialization is the first
performance point to inspect if update transport becomes hot.

Current bulk wire microbenchmark:

```text
cargo run -p os-transport --release --bin bulk-wire-benchmark
bulk_request_encode ops_per_second=281863.98 nanos_per_op=3547.81
bulk_response_encode ops_per_second=417387.87 nanos_per_op=2395.85
bulk_request_decode ops_per_second=156298.19 nanos_per_op=6398.03
bulk_response_decode ops_per_second=352789.40 nanos_per_op=2834.55
bulk_wire_bottleneck_ops_per_second=156298.19
bulk_wire_bottleneck_items_per_second=1250385.55
```

The current bulk wire bottleneck is request decode for an 8-item batch that
mixes index and delete operations. The slower path is driven by per-item full
write request headers and JSON source decode for index items. At roughly 1.25M
items/s in the latest local release run, the bounded bulk adapter has a similar
item-rate profile to multi-get; if this path becomes hot, the first optimization
target is avoiding repeated JSON materialization while preserving semantic
validation.

Current delete wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-wire-benchmark
delete_request_encode ops_per_second=1288895.31 nanos_per_op=775.86
delete_response_encode ops_per_second=1854557.41 nanos_per_op=539.21
delete_request_decode ops_per_second=1425156.11 nanos_per_op=701.68
delete_response_decode ops_per_second=1865536.67 nanos_per_op=536.04
delete_wire_bottleneck_ops_per_second=1288895.31
```

The current delete wire bottleneck is request encode, driven by request frame
construction and the replication request header fields. Response encode/decode
is materially faster than get and multi-get because delete responses do not
carry JSON source material. At roughly 1.29M ops/s in the latest local release
run, this adapter does not introduce a new transport-wire bottleneck.

## Tier 1 Implementation And Test Ownership Draft

### 1. `ClusterHealthAction.INSTANCE`

- Primary implementation ownership:
  - `crates/os-cluster-state`
    - health status derivation from cluster metadata and shard/index state;
    - wait-condition evaluation for the declared Phase A subset.
  - `crates/os-transport`
    - transport action registration, request decode, and response/error
      framing.
  - `crates/os-node`
    - REST-to-transport wiring parity where `GET /_cluster/health` and
      transport-backed behavior must agree.
- Required test ownership:
  - `crates/os-node/tests`
    - standalone Steelsearch integration coverage for success, timeout, and
      rejected unsupported wait semantics.
  - OpenSearch comparison harness
    - side-by-side assertions for supported request shapes and comparable
      health fields.

### 2. `ClusterStateAction.INSTANCE`

- Primary implementation ownership:
  - `crates/os-cluster-state`
    - metric filtering, section rendering, and fail-closed handling for
      unsupported state views.
  - `crates/os-transport`
    - action registration and OpenSearch-shaped request/response envelopes.
  - `crates/os-node`
    - consistency between REST `/_cluster/state` output and transport-backed
      state semantics.
- Required test ownership:
  - `crates/os-node/tests`
    - standalone Steelsearch integration coverage for supported metric/filter
      subsets and explicit rejection paths.
  - OpenSearch comparison harness
    - side-by-side assertions for supported metric subsets, absent-field
      policy, and error shape on unsupported combinations.

### 3. `ListTasksAction.INSTANCE`, `GetTaskAction.INSTANCE`, `CancelTasksAction.INSTANCE`

- Primary implementation ownership:
  - `crates/os-node`
    - runtime task registry, task identity, parent/child linkage, and
      cancellation lifecycle.
  - `crates/os-transport`
    - action registration, request validation, and response/error envelopes.
  - `crates/os-cluster-state`
    - no primary ownership, except where cluster-managed operations become
      tracked tasks.
- Required test ownership:
  - `crates/os-node/tests`
    - task listing, point lookup, successful cancellation, rejected
      cancellation, and unknown-task behavior.
  - OpenSearch comparison harness
    - side-by-side assertions for response shape and failure semantics on the
      supported task subset.

### 4. `ClusterStatsAction.INSTANCE`, `NodesStatsAction.INSTANCE`, `IndicesStatsAction.INSTANCE`, `PendingClusterTasksAction.INSTANCE`

- Primary implementation ownership:
  - `crates/os-node`
    - runtime/node/process stats collection and task backlog exposure.
  - `crates/os-cluster-state`
    - cluster/index/shard-derived aggregate counters.
  - `crates/os-transport`
    - transport action registration and response framing.
- Required test ownership:
  - `crates/os-node/tests`
    - standalone Steelsearch integration coverage for declared stat fields and
      fail-closed handling of unsupported sections.
  - OpenSearch comparison harness
    - field-level comparison for supported counters only, with explicit allow
      lists instead of broad snapshot comparison.

### Sequencing Rule

- Do not start stats action parity before `ClusterHealthAction.INSTANCE` and
  `ClusterStateAction.INSTANCE` have stable request validation and fail-closed
  behavior.
- Do not claim task action parity before Steelsearch has a real task registry
  with cancellation semantics; placeholder or synthetic tasks are not
  sufficient.
- Prefer one action family at a time, with:
  - transport handler;
  - Steelsearch integration tests;
  - OpenSearch comparison tests;
  - documentation/spec update;
  completed before moving to the next family.

## OpenSearch Comparison Acceptance Criteria For Tier 1

### `ClusterHealthAction.INSTANCE`

- Required comparison inputs:
  - empty or green standalone cluster;
  - cluster with at least one created index and assigned primary shards;
  - requests with supported `wait_for_status`, `timeout`, and cluster-wide
    scope only;
  - requests using intentionally unsupported wait semantics.
- Acceptance rule:
  - Steelsearch and OpenSearch must agree on the supported request outcome
    class:
    - success vs timeout vs validation-style rejection;
  - for successful requests, compare only the declared supported fields:
    - top-level health status;
    - active shard counters used by the Phase A contract;
    - timed-out indicator when a supported wait condition is used.
- Non-goals for acceptance:
  - do not require byte-identical or full JSON equality;
  - do not accept silent omission of unsupported semantics.

### `ClusterStateAction.INSTANCE`

- Required comparison inputs:
  - default cluster-state request for the declared Phase A metric subset;
  - metric-filtered requests for supported sections only;
  - requests combining supported filters with unsupported metrics or options.
- Acceptance rule:
  - Steelsearch and OpenSearch must agree on:
    - success vs explicit rejection for each request shape;
    - presence of the supported top-level sections;
    - stable field-shape expectations for the supported subset.
  - comparison should be normalized to supported sections and fields rather
    than full cluster-state snapshot equality.
- Non-goals for acceptance:
  - no requirement to match unsupported sections through empty placeholders;
  - no credit for partial responses that hide rejected metrics.

### `ListTasksAction.INSTANCE`, `GetTaskAction.INSTANCE`, `CancelTasksAction.INSTANCE`

- Required comparison inputs:
  - task listing when no supported tasks are active;
  - task listing with at least one known supported Steelsearch task active;
  - point lookup for an existing task;
  - point lookup for an unknown task id;
  - cancellation of a cancellable task;
  - cancellation of an unknown or non-cancellable task.
- Acceptance rule:
  - Steelsearch and OpenSearch must agree on:
    - response class for lookup and cancellation outcomes;
    - task envelope shape for the supported subset;
    - explicit failure semantics for unknown/non-cancellable tasks.
  - comparisons may normalize task ids and timing-dependent fields, but must
    not normalize away lifecycle state or cancellability flags.
- Non-goals for acceptance:
  - no requirement to expose Java-specific internal tasks that Steelsearch does
    not implement;
  - no synthetic "completed" tasks to satisfy shape-only comparison.

### Comparison Harness Rule

- Every OpenSearch comparison test must define:
  - request input;
  - normalization rules for nondeterministic fields;
  - allow-list of compared fields;
  - expected rejection class for unsupported inputs.
- A comparison test is not complete if it only proves both systems returned
  "something". It must prove agreement on the declared contract boundary.

## Tier 1 Fixture Input Draft

### `ClusterHealthAction.INSTANCE`

- Steelsearch integration fixture inputs:
  - single-node empty cluster;
  - single-node cluster with one created index;
  - multi-node Steelsearch cluster with assigned primary shards;
  - request variants:
    - default request;
    - supported `wait_for_status`;
    - supported `timeout`;
    - intentionally unsupported wait option.
- OpenSearch comparison fixture inputs:
  - matching empty cluster topology;
  - matching one-index topology;
  - matching request variants for supported and rejected inputs.

### `ClusterStateAction.INSTANCE`

- Steelsearch integration fixture inputs:
  - empty cluster metadata;
  - cluster with one index and basic mappings/settings;
  - cluster with multiple indices to exercise supported metric filtering;
  - request variants:
    - default metric subset;
    - supported metric-filter combinations;
    - unsupported metric or filter combinations.
- OpenSearch comparison fixture inputs:
  - matching metadata topologies;
  - identical request variants normalized to the declared supported subset.

### `ListTasksAction.INSTANCE`, `GetTaskAction.INSTANCE`, `CancelTasksAction.INSTANCE`

- Steelsearch integration fixture inputs:
  - no active supported tasks;
  - one active cancellable task;
  - one active non-cancellable task if such a task family exists in Phase A;
  - request variants:
    - list all tasks;
    - get existing task id;
    - get unknown task id;
    - cancel existing cancellable task;
    - cancel unknown task id;
    - cancel non-cancellable task id.
- OpenSearch comparison fixture inputs:
  - comparable task-producing request flow for the supported task subset;
  - identical lookup/cancel request variants, with normalization for runtime
    ids and timing-dependent fields only.

### `ClusterStatsAction.INSTANCE`, `NodesStatsAction.INSTANCE`, `IndicesStatsAction.INSTANCE`, `PendingClusterTasksAction.INSTANCE`

- Steelsearch integration fixture inputs:
  - idle single-node cluster;
  - cluster with one index and documents written;
  - multi-node cluster with per-node stat variance where applicable;
  - cluster with at least one pending or active tracked task for
    `PendingClusterTasksAction.INSTANCE`;
  - request variants limited to the declared supported stat groups.
- OpenSearch comparison fixture inputs:
  - matching idle and loaded cluster topologies;
  - equivalent requests with field allow-lists for supported counters only.

### Shared Fixture Rule

- Prefer reusable topology builders over per-test ad hoc setup.
- Keep one canonical fixture per contract boundary:
  - empty cluster;
  - one-index cluster;
  - loaded cluster;
  - active-task cluster;
  - unsupported-request case.
- OpenSearch comparison fixtures should mirror the Steelsearch topology closely
  enough to compare contract behavior, not attempt full internal-state
  identity.

## Nondeterministic Field Normalization Policy

OpenSearch comparison tests may normalize runtime-dependent fields only when
that normalization does not erase contract meaning.

### Allowed Normalization

- generated task ids whose exact numeric or node-local identity is not part of
  the declared contract;
- timestamps and elapsed durations that naturally vary between runs;
- node ids, ephemeral transport addresses, or publish addresses when the test
  only needs to prove node-count or presence semantics;
- ordering of map-like structures when the OpenSearch contract does not require
  stable ordering;
- shard/index iteration order when the compared contract is explicitly order
  insensitive.

### Forbidden Normalization

- health status values such as green/yellow/red;
- timeout outcome and explicit rejection outcome;
- cancellable vs non-cancellable task flags;
- task lifecycle state when that state is part of the supported response
  contract;
- presence or absence of supported top-level cluster-state sections;
- supported stat field names and their compared counter values;
- explicit error type/class boundaries for unsupported requests.

### Review Rule

- If normalizing a field would make two semantically different outcomes appear
  equivalent, that normalization is forbidden.
- Every normalization rule used by a comparison test should be stated inline in
  the test or referenced from a shared normalization helper with the exact
  fields listed.

## Shared Fixture Topology Builder And Request Builder Split

Tier 1 comparison coverage should separate cluster topology setup from
action-specific request generation.

### Topology Builder Responsibility

A shared topology builder should own:

- cluster shape:
  - single-node empty cluster;
  - single-node one-index cluster;
  - multi-node healthy cluster;
  - loaded cluster with documents;
  - active-task cluster;
- reusable index/document seeding;
- waiting for baseline readiness before action-specific assertions begin.

This builder should not encode action semantics such as health wait options,
cluster-state metrics, or task lookup ids.

### Request Builder Responsibility

Per-action request builders should own:

- request variants for `ClusterHealthAction.INSTANCE`;
- metric/filter combinations for `ClusterStateAction.INSTANCE`;
- list/get/cancel variants for task actions;
- stat-group selections for stats actions.

Request builders may depend on topology outputs, such as created index names or
known task ids, but should not own cluster setup.

### Ownership Split

- shared topology builders:
  - primary home in the Steelsearch integration test support layer under
    `crates/os-node/tests`;
- action-specific request builders:
  - colocated with the action family tests that use them;
- OpenSearch side-by-side adapters:
  - wrap the same logical request variants, translating only what is needed to
    issue the request against the Java OpenSearch node under test.

### Rollout Rule

- Build the shared topology layer first for:
  - empty cluster;
  - one-index cluster;
  - active-task cluster.
- Add per-action request builders only after the topology contract is stable.
- Avoid action-specific fixture forks unless the action requires genuinely new
  topology state that cannot be expressed through the shared builder contract.

## Shared Normalization Helper Contract

OpenSearch side-by-side tests should use a shared normalization helper only for
runtime-dependent fields that are explicitly approved for normalization.

### Input Contract

The helper input should include:

- raw Steelsearch response payload;
- raw OpenSearch response payload;
- action family identifier;
- allow-list of fields that may be compared;
- allow-list of fields that may be normalized;
- explicit list of forbidden normalizations for the action family.

### Allowed Transformations

The helper may:

- drop or rewrite approved nondeterministic fields such as task ids,
  timestamps, elapsed durations, and ephemeral addresses;
- canonicalize order-insensitive collections where ordering is not part of the
  documented contract;
- project a larger payload down to the declared compared-field allow-list.

The helper must not:

- rewrite semantic status values;
- convert explicit errors into empty success-like shapes;
- hide presence/absence differences for supported fields;
- normalize different lifecycle or cancellability states into the same output.

### Output Contract

The helper output should be:

- normalized Steelsearch payload;
- normalized OpenSearch payload;
- machine-readable record of which normalization rules were applied.

Comparison assertions should fail if a test attempts to normalize a field that
is not present in the approved allow-list for that action family.

## Shared Topology Builder Handle Contract

The shared topology builder should return a stable handle object instead of
forcing action-family tests to reach into setup internals.

### Required Handle Fields

- cluster readiness:
  - health-ready indicator for the declared baseline state;
  - timeout or readiness failure surfaced explicitly to the caller.
- topology identity:
  - node count;
  - Steelsearch node addresses or endpoints needed by the test harness;
  - OpenSearch node addresses or endpoints when running side-by-side tests.
- seeded resources:
  - created index names;
  - document ids or seed dataset labels when relevant;
  - known task ids for active-task fixtures when task-producing setup is part
    of the topology.
- capability hints:
  - whether the topology is empty, one-index, loaded, or active-task oriented;
  - any declared unsupported features intentionally absent from that topology.

### Contract Rule

- Action-family tests may consume the handle, but should not inspect hidden
  setup internals outside the handle contract.
- If a test needs new setup state repeatedly, promote that state into the
  shared handle instead of creating ad hoc fixture-specific escape hatches.

### Minimum vs Optional Handle Fields

- Minimum fields:
  - readiness outcome;
  - node count;
  - Steelsearch endpoints;
  - topology kind (`empty`, `one-index`, `loaded`, `active-task`);
  - created index names when the topology is index-bearing.
- Optional fields:
  - OpenSearch endpoints for side-by-side runs;
  - seeded document ids or dataset labels;
  - known active task ids;
  - feature-absence hints for intentionally unsupported topology features.

Tests must not assume optional fields are present unless the fixture contract
for that topology explicitly guarantees them.

### Minimum Handle Guarantees By Topology Kind

| Topology kind | Minimum guarantees |
| --- | --- |
| `empty` | readiness outcome, node count, Steelsearch endpoints, topology kind |
| `one-index` | all `empty` guarantees plus created index names |
| `loaded` | all `one-index` guarantees plus seeded document ids or dataset label |
| `active-task` | all `empty` guarantees plus known active task ids when the topology contract promises task-producing setup |

### Topology Kind To Action Family Mapping

| Action family | Positive-path minimum | Rejection-path minimum | Representative rejection scenario |
| --- | --- | --- | --- |
| `ClusterHealthAction.INSTANCE` | `empty`; use `one-index` or `loaded` when shard/index counters are part of the compared contract | `empty` unless the rejection depends on richer shard/index state | `unsupported wait_for_nodes` |
| `ClusterStateAction.INSTANCE` | `one-index`; use `empty` only for explicit empty-state coverage | `empty` for unsupported metric/filter validation that does not depend on populated metadata | `unsupported metric/filter combination` |
| `ListTasksAction.INSTANCE`, `GetTaskAction.INSTANCE`, `CancelTasksAction.INSTANCE` | `active-task` for positive task paths | `empty` for no-task and unknown-task paths; `active-task` when rejection depends on non-cancellable task state | `non-cancellable task cancellation` |
| `ClusterStatsAction.INSTANCE`, `NodesStatsAction.INSTANCE`, `IndicesStatsAction.INSTANCE` | `loaded`; use `one-index` for narrower metadata-only stat subsets | `empty` or `one-index`, depending on whether the rejected stat group requires populated data to exercise validation | `unsupported stat group selection` |
| `PendingClusterTasksAction.INSTANCE` | `active-task` when pending-task semantics are being compared | `empty` unless rejection depends on task-producing state | `unsupported pending-task request shape` |

### Positive-Path vs Rejection-Path Topology Rule

If an action family needs different topology minima for success and rejection
paths, document them separately in the same mapping row or in an adjacent note.

- positive path:
  - the minimum topology needed to prove the supported contract works.
- rejection path:
  - the minimum topology needed to prove unsupported or invalid requests are
    rejected correctly.

Prefer the smallest topology that still proves the intended rejection class.
Do not require a richer topology for rejection-only coverage unless the
rejection semantics themselves depend on that richer state.

### Mapping Table Shape Decision

Use separate `positive-path minimum` and `rejection-path minimum` columns when
the mapping table is next expanded.

Reasoning:

- a single mixed prose column becomes ambiguous once success and rejection paths
  diverge;
- two columns keep fixture selection mechanical for test authors;
- the separation matches the acceptance-criteria split already used for
  supported vs rejected request shapes.

### Rejection Scenario Example Decision

Add a short representative rejection scenario alongside the rejection-path
minimum when the family has more than one plausible rejection shape.

Reasoning:

- the topology minimum alone does not always explain why that topology is
  needed;
- a short scenario label makes it easier to select the right fixture without
  reading the entire acceptance section.

Keep the scenario brief, for example:

- `unsupported wait_for_nodes`
- `unsupported metric/filter combination`
- `non-cancellable task cancellation`

Use the same user-facing vocabulary family as `fail_closed_note`, even though
the mapping-table scenario is only a short label. This avoids documentation
drift between fixture-planning tables and generated compatibility notes.

Default to the short label form such as `unsupported X`, not the full sentence
form `rejects X`, because the mapping table is acting as a compact planning
index rather than a generated compatibility note.

Share the core noun phrase with `fail_closed_note`, but do not require the full
sentence form to match. In practice:

- mapping-table label:
  - `unsupported wait_for_nodes`
- generated note:
  - `rejects wait_for_nodes`

This keeps both surfaces aligned on vocabulary while preserving their different
formatting roles.

Only the leading verb or label form should change. The object phrase should
stay identical unless the API-facing wording itself changes.

When multiple options or request-shape nouns appear in the object phrase,
preserve the same left-to-right order across the mapping-table scenario and the
generated note. Prefer the order users encounter in the request surface, not an
alphabetical reorder.

## Action-Family Normalization Allow/Deny Table

| Action family | Allow normalization | Deny normalization |
| --- | --- | --- |
| `ClusterHealthAction.INSTANCE` | node ids, publish addresses, timing fields | health status, timeout outcome, supported shard counters |
| `ClusterStateAction.INSTANCE` | order-insensitive section ordering, ephemeral node identity fields where not contractually relevant | supported top-level section presence, supported field names, explicit rejection outcome |
| `ListTasksAction.INSTANCE`, `GetTaskAction.INSTANCE`, `CancelTasksAction.INSTANCE` | task ids, timing fields, ephemeral node identity fields | cancellable flag, lifecycle state, success vs unknown-task vs rejected-cancel outcome |
| `ClusterStatsAction.INSTANCE`, `NodesStatsAction.INSTANCE`, `IndicesStatsAction.INSTANCE`, `PendingClusterTasksAction.INSTANCE` | node ids, publish addresses, order-insensitive map ordering | compared stat field names, allow-listed counter values, pending-task presence/absence outcome |

Use this table as the default action-family profile. A concrete test may narrow
normalization further, but it must not broaden normalization beyond this table
without an explicit spec update.

## Normalization Profile Representation Decision

Use a config-shaped representation backed by a small action-family enum, not a
pure enum-only model.

### Decision

- action family should still be identified by an enum-like discriminator;
- the actual normalization contract should live in structured config data for
  that action family.

### Reasoning

- enum-only is too rigid once a family needs:
  - compared-field allow-lists;
  - normalization allow-lists;
  - explicit deny-lists;
  - family-specific notes about fail-closed boundaries.
- pure untyped config is too loose and makes accidental profile drift easier.
- enum + config gives:
  - explicit family identity in test code;
  - structured policy data per family;
  - room for future extension without rewriting the test helper interface.

### Implementation Direction

- one small enum or identifier for the action family;
- one config record resolved from that identifier;
- tests may narrow the resolved config, but must not broaden it without a spec
  update.

### Minimum Config Record Fields

The normalization profile config record should contain at least:

- `compared_fields`
  - allow-list of fields that are asserted after normalization;
- `normalizable_fields`
  - allow-list of runtime-dependent fields that may be rewritten or dropped;
- `forbidden_normalizations`
  - explicit deny-list of fields or semantic categories that must never be
    normalized away;
- `notes`
  - short contract notes, especially where fail-closed or subset semantics are
    important for that action family.

### Semantic Category vs Concrete Field Path

Represent both.

- use semantic categories for rules such as:
  - health status;
  - timeout outcome;
  - cancellability;
  - lifecycle state;
  - supported top-level section presence.
- use concrete field paths for runtime-dependent payload details such as:
  - task ids;
  - timestamps;
  - addresses;
  - specific compared counters.

Reasoning:

- semantic categories prevent accidental normalization of the same concept
  under multiple field names;
- concrete field paths keep the helper precise when only particular payload
  fields are safe to rewrite or project.

The config record should therefore allow both category-level and field-path
entries, with category rules taking precedence when there is a conflict.

### Category Precedence Rule

The shared normalization helper should enforce category precedence, not leave
it to each individual test.

- If a semantic category is marked non-normalizable, no concrete field path
  belonging to that category may be normalized even if it appears in a
  field-path allow-list.
- If a semantic category is marked comparable, the concrete field path may
  still be omitted from comparison only when the action-family profile says the
  field is outside the supported compared subset.
- Tests may narrow field-path usage, but must not override a stricter category
  rule.

### Category-To-Field Mapping Location Decision

Keep the base category-to-field-path mapping in a shared table, with
action-family profiles able to reference or narrow that shared mapping.

Reasoning:

- shared semantic categories such as health status, timeout outcome, and task
  cancellability should not be re-declared independently in every profile;
- a shared table reduces spelling drift and keeps category precedence
  enforceable in one place;
- per-profile narrowing is still needed because not every action family exposes
  every field path in the same way.

Implementation direction:

- one shared category-to-field-path table in the comparison helper layer;
- per-profile config may opt into categories and narrow concrete compared
  fields;
- per-profile config must not redefine the shared category with conflicting
  semantics.

### Initial Shared Category Set

Start with these shared semantic categories:

- `health_status`
- `timeout_outcome`
- `top_level_section_presence`
- `task_cancellability`
- `task_lifecycle_state`
- `node_identity_ephemeral`
- `timing_fields`

These are the first categories because they already recur across the Tier 1
acceptance and normalization rules. New categories should be added only when
they represent a reusable semantic concept across multiple action families.

### Initial Category-To-Field Examples

- `health_status`
  - `status`
- `timeout_outcome`
  - `timed_out`
- `top_level_section_presence`
  - `metadata.cluster_uuid`
  - `routing_table.indices.<index_name>`
  - `nodes.<node_id>.transport_address`
- `task_cancellability`
  - `cancellable`
- `task_lifecycle_state`
  - `completed`
  - `running_time_in_nanos`
- `node_identity_ephemeral`
  - `nodes.<node_id>.transport_address`
- `timing_fields`
  - `timestamp`
  - `took`
  - `running_time_in_nanos`

### Initial Domain-Ambiguity Candidate List

The following paths are good candidates for future domain-specific placeholder
review because a plain `<id>` could hide meaning:

- `nodes.<id>.transport_address`
- `nodes.<id>.attributes.<id>`
- `indices.<id>.shards.<id>.state`
- `tasks.<id>.children[]`

Recommended first-pass replacements:

- `nodes.<id>.transport_address` -> `nodes.<node_id>.transport_address`
- `nodes.<id>.attributes.<id>` -> `nodes.<node_id>.attributes.<attr_key>`
- `indices.<id>.shards.<id>.state` -> `indices.<index_name>.shards.<shard_id>.state`
- `tasks.<id>.children[]` -> `tasks.<task_id>.children[]`

### Response-Shape Path Notation Decision

Use dot-path notation when referring to concrete response-shape paths in shared
category mappings and normalization helper config.

Examples:

- `metadata.cluster_uuid`
- `nodes.<id>.transport_address`
- `task.cancellable`

Use a simple field label only when the field is top-level and unambiguous.

For shared category examples, prefer dot-path precision once a plain field
label would hide response shape or placeholder meaning. Keep top-level
unambiguous labels only where extra path detail adds no practical clarity.

For `top_level_section_presence`, the dot-path examples are concrete witnesses
for section presence, not a narrowing of the category from section-level
semantics to field-level semantics.

This witness-field explanation is mainly needed for
`top_level_section_presence` at the moment. The other current semantic
categories already map more directly to field-level observations and do not yet
need separate witness-language.

If a future semantic category relies on indirect dot-path examples that stand
in for a broader semantic boundary, add the same witness-language explicitly.
Do not assume that readers will infer the distinction automatically.

Minimal witness-language template:

- `the dot-path examples are concrete witnesses for <broader semantic boundary>, not a narrowing of the category to field-level semantics`

Examples for `<broader semantic boundary>`:

- `top-level section presence`
- `shard availability`
- `tracked task lifecycle`

`tracked task lifecycle` is acceptable as a boundary phrase because the task
domain already supplies the missing subject and keeps the phrase compact.

These three examples are intentionally kept at a similar abstraction level:
short semantic phrases, not full response-shape labels.

Keep witness-language boundary examples as noun phrases by default. Do not turn
them into full sentences unless a future category genuinely requires that extra
structure.

Keep these noun phrases short. If a boundary phrase starts accumulating too
many modifiers, prefer splitting the explanation around the template rather than
growing the phrase itself.

Treat modifier build-up as a review smell when extra words stop narrowing the
boundary and start repeating domain context that the surrounding category
already supplies. In practice:
- keep modifiers that distinguish the boundary from a nearby sibling concept;
- drop modifiers that only restate the subject area already obvious from the
  category name;
- if a phrase needs more than one clarifying modifier and still feels cramped,
  keep the shorter noun phrase and move the nuance into the prose around the
  template.

Examples:
- keep `top-level section presence` over plain `section presence` because
  `top-level` distinguishes it from nested field or subsection presence;
- keep `tracked task lifecycle` over plain `task lifecycle` because `tracked`
  marks the supported task subset rather than repeating the task domain itself;
- drop expansions like `cluster task lifecycle` or `search task lifecycle`
  when the surrounding category or action family already makes that subject
  area obvious.

Treat a modifier as subset-signaling when removing it would broaden the phrase
past the actual supported contract boundary. Treat a modifier as merely
descriptive when removing it leaves the supported boundary unchanged and only
changes tone or background detail.

Examples:
- `tracked` in `tracked task lifecycle` is subset-signaling because Steelsearch
  is not claiming arbitrary task lifecycle visibility;
- `top-level` in `top-level section presence` is subset-signaling because the
  category is not about any nested section witness;
- adjectives that only make the phrase sound richer, without narrowing the
  supported contract, should stay out of the noun phrase.

Subset-signaling modifiers should still stay conservative. Keep them only when
the narrower contract boundary is already defined elsewhere in the spec, and
prefer wording that marks scope without implying exhaustive parity.

In practice:
- prefer bounded words like `tracked` or `top-level` when the supported subset
  is explicit;
- avoid expansive words like `full`, `complete`, or `global` unless the spec
  really proves that breadth;
- if a modifier can be read as a parity claim rather than a scope marker,
  replace it with a narrower phrase or move the nuance into prose.

Avoided vs preferred:
- avoid `full task lifecycle`; use `tracked task lifecycle`;
- avoid `complete section presence`; use `top-level section presence`;
- avoid `global shard availability`; use `shard availability`.

Keep these pairs in short verb form rather than symbolic shorthand. Forms like
`X -> Y` or `X / Y` are more compact, but they hide whether the left side is
forbidden or merely less preferred. `avoid ...; use ...` keeps the contract
direction explicit.

Do not split the left-hand side into separate `forbid` versus `discourage`
tracks in this table. The pair examples are style guidance, not protocol error
semantics. If a phrase is truly invalid because it overclaims the contract,
keep using `avoid ...; use ...` here and document the stronger fail-closed
boundary elsewhere in the spec.

Keep that separation explicit. This table is for wording hygiene: how to avoid
overclaiming phrases and what shorter bounded phrasing to use instead.
Fail-closed behavior, explicit rejection semantics, and unsupported request
boundaries belong in the transport compatibility and API contract sections, not
inside the wording pair examples.

For the same reason, keep contract-semantics verbs like `rejects` and
`supports` out of the wording pairs. Pair examples should stay with neutral
style-edit verbs such as `avoid` and `use`, so readers do not confuse them with
actual runtime behavior.

Keep `avoid` as the left-hand verb. We do not switch to weaker verbs like
`skip` or `drop`, because they can sound optional or editorial rather than
normative. `Avoid` is still style guidance, but it more clearly signals that
the left-hand phrase should not be used in compatibility wording.

Keep `use` as the right-hand verb. More conversational verbs like `write` or
`say` are too tied to prose mechanics and too weak about contract-facing
wording choice. `Use` stays short while still pointing at the preferred phrase
that should appear in the spec.

Keep the pair order fixed as `avoid ...; use ...`. The discouraged phrase comes
first so the reader sees the wording hazard before the replacement. Reversing
the order makes the pair feel like a preference hint instead of a corrective
style rule.

Keep the semicolon form rather than arrow shorthand. `X -> Y` looks like a
mechanical rewrite rule, while `avoid ...; use ...` keeps the wording
direction explicit and stays consistent with compatibility wording used for
style guidance, not fail-closed behavior documented in compatibility
contracts.

Here `fail-closed behavior` is intentionally left article-free: it points to
that class of contract behavior without pretending the wording pair is naming a
single canonical contract form.

Freeze that wording here. `single canonical contract form` is the current
balance point between naming weight and abstraction, so further micro-tuning of
that phrase should stop unless a wider wording pass finds a concrete ambiguity.

Current classification:

- keep as top-level label:
  - `status`
  - `timed_out`
  - `timestamp`
  - `took`
- prefer dot-path:
  - `metadata.cluster_uuid`
  - `nodes.<node_id>.transport_address`
  - `task.cancellable`

Do not keep section-level labels such as `metadata` or `nodes` as standalone
shared category examples when a concrete dot-path example is available. Section
names may still appear inside prose, but not as the primary normalized example.

### Wildcard / Id Placeholder Rule

Use angle-bracket placeholders such as `<id>` for identifier-bearing response
paths, not `*`.

Examples:

- `nodes.<id>.transport_address`
- `tasks.<id>.cancellable`

Reasoning:

- `<id>` makes it explicit that the segment is a runtime identifier, not an
  arbitrary wildcard expansion;
- it reads more clearly alongside semantic category documentation.

### Array Index Placeholder Rule

Use `[]` to indicate an array element position in response-shape paths, not
`.<n>`.

Examples:

- `hits.hits[].sort`
- `shards[].state`

Reasoning:

- `[]` signals sequence membership without implying a stable positional index;
- it avoids confusion with numeric fields or literal dotted path segments.

### Map-Key And Array Placeholder Composition

When both a map-key placeholder and an array placeholder appear in the same
path, write them in structural order from left to right.

Examples:

- `nodes.<id>.roles[]`
- `tasks.<id>.children[]`

Do not invert the order or collapse placeholders into a single mixed token.

### Nested Map-Key Placeholder Rule

When multiple map-key placeholders are nested, repeat the `<id>`-style segment
at each structural level instead of inventing a compressed shorthand.

Examples:

- `indices.<id>.shards.<id>.state`
- `nodes.<id>.attributes.<id>`

This keeps the path readable and preserves the actual nesting shape.

When two map-key segments represent materially different user-visible concepts,
prefer concept-specific placeholders such as:

- `nodes.<node_id>.attributes.<attr_key>`
- `indices.<index_name>.shards.<shard_id>`

Keep plain `<id>` only when the key kind is obvious from the immediate field
name or the distinction adds no clarity.

Use domain nouns where they are stable and user-visible, for example
`<index_name>` or `<shard_id>`. Use generic suffix forms such as `_id` or
`_key` only when there is no better domain noun.

When choosing between a bare domain noun and a suffixed domain noun, prefer
the suffixed form when it clarifies what the value represents.

Examples:

- prefer `<index_name>` over `<index>`
- prefer `<shard_id>` over `<shard>`

Use the bare domain noun only when the shorter form is already unambiguous in
the surrounding path.

Do not create a large domain-by-domain suffix matrix yet. Keep the general
priority:

1. stable domain noun with clarifying suffix where needed
2. generic `_id`
3. generic `_key`

Only add domain-specific refinements when concrete ambiguity appears in real
response-shape examples.

## Tier 2: Strong Phase A Follow-Up Read/Admin Actions

All listed Tier 2 read/admin actions are now implemented for their declared
empty/default transport subsets. Further transport work should continue from
the remaining source-derived partial inventory.

## Tier 3: Phase B/C Or Domain-Specific Follow-Up

- repository and snapshot transport actions;
- retention lease actions;
- decommission and tiering actions;
- PIT and scroll transport actions;
- vector/k-NN plugin transport actions;
- write-path mutation actions whose standalone REST contract can be satisfied
  without first achieving Java-compatible server-side transport parity;
- same-cluster coordination and mixed-node lifecycle actions.

These are not unimportant. They are postponed only because they are either:

- broader than the first standalone replacement gate; or
- more naturally tied to mixed-cluster or plugin parity milestones.

## Notes

- A completed probe or decode path does not mean the corresponding transport
  action is implemented server-side.
- For Phase A, the main question is whether the action is required to operate a
  Steelsearch-only cluster as an OpenSearch replacement.
- For Phase B and Phase C, transport parity expands from observability and
  metadata visibility toward forwarding, coordination, recovery, and mixed-node
  safety.
