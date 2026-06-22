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

## Current Server-Side Transport Adapters

As of the bulk transport adapter pass, the explicit dispatcher contract in
`crates/os-transport/src/action.rs` accepts:

- `cluster:monitor/main` (rejected fail-closed)
- `cluster:monitor/remote/info` (rejected fail-closed)
- `internal:monitor/term` (rejected fail-closed)
- `cluster:monitor/state`
- `cluster:monitor/health`
- `cluster:monitor/stats` (rejected fail-closed)
- `cluster:monitor/shards` (rejected fail-closed)
- `cluster:monitor/nodes/info` (rejected fail-closed)
- `cluster:monitor/nodes/stats` (rejected fail-closed)
- `cluster:monitor/wlm/stats` (rejected fail-closed)
- `cluster:monitor/_remotestore/stats` (rejected fail-closed)
- `cluster:admin/remote_store/metadata` (rejected fail-closed)
- `cluster:monitor/nodes/usage` (rejected fail-closed)
- `cluster:monitor/nodes/hot_threads` (rejected fail-closed)
- `cluster:admin/voting_config/add_exclusions` (rejected fail-closed)
- `cluster:admin/voting_config/clear_exclusions` (rejected fail-closed)
- `cluster:monitor/allocation/explain` (rejected fail-closed)
- `cluster:admin/settings/update` (rejected fail-closed)
- `cluster:admin/reroute` (rejected fail-closed)
- `cluster:admin/filecache/prune` (rejected fail-closed)
- `cluster:admin/nodes/reload_secure_settings` (rejected fail-closed)
- `cluster:admin/repository/put` (rejected fail-closed)
- `cluster:admin/repository/get` (rejected fail-closed)
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
- `cluster:admin/routing/awareness/weights/get` (rejected fail-closed)
- `cluster:admin/routing/awareness/weights/delete` (rejected fail-closed)
- `indices:admin/mappings/get` (rejected fail-closed)
- `indices:admin/mappings/fields/get` (rejected fail-closed)
- `indices:admin/get` (rejected fail-closed)
- `indices:admin/exists` (rejected fail-closed)
- `indices:admin/template/get` (rejected fail-closed)
- `indices:admin/template/delete` (rejected fail-closed)
- `cluster:admin/component_template/get` (rejected fail-closed)
- `cluster:admin/component_template/delete` (rejected fail-closed)
- `indices:admin/index_template/get` (rejected fail-closed)
- `indices:admin/index_template/delete` (rejected fail-closed)
- `indices:admin/aliases/get` (rejected fail-closed)
- `indices:monitor/settings/get` (rejected fail-closed)
- `indices:admin/shards/search_shards` (rejected fail-closed)
- `indices:data/read/field_caps` (rejected fail-closed)
- `indices:monitor/recovery` (rejected fail-closed)
- `indices:monitor/segment_replication` (rejected fail-closed)
- `indices:monitor/segments` (rejected fail-closed)
- `indices:monitor/point_in_time/segments` (rejected fail-closed)
- `indices:monitor/shard_stores` (rejected fail-closed)
- `indices:admin/data_stream/create` (rejected fail-closed)
- `indices:admin/data_stream/delete` (rejected fail-closed)
- `indices:admin/data_stream/get` (rejected fail-closed)
- `indices:monitor/data_stream/stats` (rejected fail-closed)
- `indices:admin/resolve/index` (rejected fail-closed)
- `cluster:admin/views/create` (rejected fail-closed)
- `cluster:admin/views/delete` (rejected fail-closed)
- `views:data/read/get` (rejected fail-closed)
- `cluster:admin/views/update` (rejected fail-closed)
- `views:data/read/list` (rejected fail-closed)
- `views:data/read/search` (rejected fail-closed)
- `cluster:admin/persistent/start` (rejected fail-closed)
- `cluster:admin/persistent/update_status` (rejected fail-closed)
- `cluster:admin/persistent/completion` (rejected fail-closed)
- `cluster:admin/persistent/remove` (rejected fail-closed)
- `indices:admin/seq_no/add_retention_lease` (rejected fail-closed)
- `indices:admin/seq_no/renew_retention_lease` (rejected fail-closed)
- `indices:admin/seq_no/remove_retention_lease` (rejected fail-closed)
- `cluster:admin/indices/dangling/list` (rejected fail-closed)
- `cluster:admin/indices/dangling/import` (rejected fail-closed)
- `indices:data/read/search` (rejected fail-closed)
- `indices:data/read/search/stream` (rejected fail-closed)
- `indices:data/read/msearch` (rejected fail-closed)
- `indices:data/read/scroll` (rejected fail-closed)
- `indices:data/read/scroll/clear` (rejected fail-closed)
- `indices:data/read/explain` (rejected fail-closed)
- `indices:data/read/point_in_time/create` (rejected fail-closed)
- `indices:data/read/point_in_time/delete` (rejected fail-closed)
- `indices:data/read/point_in_time/readall` (rejected fail-closed)
- `cluster:monitor/task`
- `cluster:monitor/tasks/lists`
- `cluster:monitor/task/get` (rejected fail-closed)
- `cluster:admin/tasks/cancel`
- `indices:data/read/get`
- `indices:data/read/mget`
- `indices:data/write/bulk`
- `indices:data/write/index`
- `indices:data/write/update`
- `indices:data/write/delete`
- `indices:admin/create` (rejected fail-closed)
- `indices:admin/auto_create` (rejected fail-closed)
- `cluster:admin/script/put` (rejected fail-closed)
- `cluster:admin/script/get` (rejected fail-closed)
- `cluster:admin/script/delete` (rejected fail-closed)
- `cluster:admin/script_context/get` (rejected fail-closed)
- `cluster:admin/script_language/get` (rejected fail-closed)
- `cluster:admin/ingest/pipeline/put` (rejected fail-closed)
- `cluster:admin/ingest/pipeline/get` (rejected fail-closed)
- `cluster:admin/ingest/pipeline/delete` (rejected fail-closed)
- `cluster:admin/ingest/pipeline/simulate` (rejected fail-closed)
- `indices:admin/refresh`
- `indices:data/read/tv` (rejected fail-closed)
- `indices:data/read/mtv` (rejected fail-closed)
- `indices:admin/flush` (rejected fail-closed)
- `indices:admin/forcemerge` (rejected fail-closed)
- `indices:admin/upgrade` (rejected fail-closed)
- `indices:monitor/upgrade` (rejected fail-closed)
- `internal:indices/admin/upgrade` (rejected fail-closed)
- `indices:admin/cache/clear` (rejected fail-closed)
- `indices:monitor/stats` (rejected fail-closed)

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
- explicit fail-closed classification for `cluster:monitor/main` until node
  name, cluster name, cluster UUID, version, and build metadata response
  rendering are implemented;
- explicit rejection at execution so Steelsearch does not emit incomplete root
  info semantics through transport.

The remote-info boundary covers:

- OpenSearch `RemoteInfoRequest` parent task at the wire decode/build layer;
- explicit fail-closed classification for `cluster:monitor/remote/info` until
  remote connection info collection and response rendering are implemented;
- explicit rejection at execution so Steelsearch does not emit incomplete remote
  cluster info semantics through transport.

The get-term-version boundary covers:

- OpenSearch `GetTermVersionRequest` parent task, cluster-manager timeout, and
  local flag at the wire decode/build layer;
- explicit fail-closed classification for `internal:monitor/term` until cluster
  term/version and remote-publication response rendering are implemented;
- explicit rejection for custom cluster-manager timeout, local execution, and
  get-term-version execution.

The cluster-stats boundary covers:

- OpenSearch `ClusterStatsRequest` parent task, node ids, optional timeout,
  aggregated-node-level response flag, compute-all-metrics flag, metric bitset,
  and index metric bitset at the wire decode/build layer;
- explicit fail-closed classification for `cluster:monitor/stats` until runtime
  stats aggregation and field-level metric mapping are implemented;
- explicit rejection for concrete node payloads, node filters, timeout,
  aggregated-node response mode, partial metric selection, metric bitsets, and
  cluster-stats execution.

The cat-shards boundary covers:

- OpenSearch `CatShardsRequest` parent task, cluster-manager timeout, local
  flag, indices array, optional cancel-after timeout, optional `PageParams`,
  and request-limit support flag at the wire decode/build layer;
- explicit fail-closed classification for `cluster:monitor/shards` until shard
  routing plus index stats response rendering is implemented;
- explicit rejection for custom cluster-manager timeout, local reads, index
  filters, cancel-after timeout, pagination, request-limit checks, and
  cat-shards execution.

The nodes-info boundary covers:

- OpenSearch `NodesInfoRequest` parent task, node ids, optional timeout, and
  requested metric names at the wire decode/build layer;
- explicit fail-closed classification for `cluster:monitor/nodes/info` until
  runtime node-info response mapping is implemented;
- explicit rejection for concrete node payloads, node filters, timeout,
  non-default requested metrics, and nodes-info execution.

The nodes-stats boundary covers:

- OpenSearch `NodesStatsRequest` parent task, node ids, optional timeout,
  `CommonStatsFlags`, and requested metric names at the wire decode/build
  layer;
- explicit fail-closed classification for `cluster:monitor/nodes/stats` until
  runtime node telemetry and field-level metric mapping are implemented;
- explicit rejection for concrete node payloads, node filters, timeout,
  non-default index stats flags, requested metric selection, and nodes-stats
  execution.

The nodes-usage boundary covers:

- OpenSearch `NodesUsageRequest` parent task, node ids, optional timeout,
  `restActions`, and `aggregations` flags at the wire decode/build layer;
- explicit fail-closed classification for `cluster:monitor/nodes/usage` until
  runtime usage telemetry mapping is implemented;
- explicit rejection for concrete node payloads, node filters, timeout,
  `restActions`, `aggregations`, and nodes-usage execution.

The wlm-stats boundary covers:

- OpenSearch `WlmStatsRequest` parent task, node ids, optional timeout,
  workload group id array, and optional breach flag at the wire decode/build
  layer;
- explicit fail-closed classification for `cluster:monitor/wlm/stats` until
  workload group runtime telemetry mapping is implemented;
- explicit rejection for concrete node payloads, node filters, timeout,
  workload group filters, breach filters, and wlm-stats execution.

The remote-store-stats boundary covers:

- OpenSearch `RemoteStoreStatsRequest` parent task, broadcast indices array,
  indices options, shard id array, and local flag at the wire decode/build
  layer;
- explicit fail-closed classification for `cluster:monitor/_remotestore/stats`
  until remote store shard stats rendering is implemented;
- explicit rejection for index filters, non-default indices options, shard
  filters, local-only execution, and remote-store-stats execution.

The remote-store-metadata boundary covers:

- OpenSearch `RemoteStoreMetadataRequest` parent task, broadcast indices array,
  indices options, and shard id array at the wire decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/remote_store/metadata` until remote store shard metadata
  rendering is implemented;
- explicit rejection for index filters, non-default indices options, shard
  filters, and remote-store-metadata execution.

The nodes-hot-threads boundary covers:

- OpenSearch `NodesHotThreadsRequest` parent task, node ids, optional timeout,
  thread count, idle-thread inclusion flag, sampling type, interval, and
  snapshot count at the wire decode/build layer;
- explicit fail-closed classification for `cluster:monitor/nodes/hot_threads`
  until runtime stack sampling and diagnostic output mapping are implemented;
- explicit rejection for concrete node payloads, node filters, timeout, custom
  thread count, idle-thread inclusion, non-CPU sampling type, custom interval,
  custom snapshot count, and nodes-hot-threads execution.

The add-voting-config-exclusions boundary covers:

- OpenSearch `AddVotingConfigExclusionsRequest` parent task,
  cluster-manager timeout, node-description selector array, node-id selector
  array, node-name selector array, and wait timeout at the wire decode/build
  layer;
- explicit fail-closed classification for
  `cluster:admin/voting_config/add_exclusions` until coordination metadata
  mutation and voting-configuration convergence tracking are implemented;
- explicit rejection for custom cluster-manager timeout, custom wait timeout,
  missing selector, multiple selectors, deprecated node-description selectors,
  node-id selectors, and add-voting-config-exclusions execution.

The clear-voting-config-exclusions boundary covers:

- OpenSearch `ClearVotingConfigExclusionsRequest` parent task,
  cluster-manager timeout, `waitForRemoval` flag, and wait timeout at the wire
  decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/voting_config/clear_exclusions` until coordination metadata
  mutation and removal tracking are implemented;
- explicit rejection for custom cluster-manager timeout, no-wait clearing,
  custom wait timeout, and clear-voting-config-exclusions execution.

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
- OpenSearch acknowledged response boolean decode/build shape;
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
- explicit fail-closed classification for `cluster:admin/repository/get` until
  repository metadata mapping and response rendering are implemented;
- explicit rejection for custom cluster-manager timeout, repository name/pattern
  selection, local reads, and get-repositories execution.

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
- explicit fail-closed classification for `cluster:admin/repository/verify`
  until repository verification and node response rendering are implemented;
- explicit rejection for custom cluster-manager timeout, custom acknowledgement
  timeout, blank name, and verify-repository execution.

The cleanup-repository boundary covers:

- OpenSearch `CleanupRepositoryRequest` repository name at the wire
  decode/build layer. The OpenSearch 3.7 request stream constructor and
  `writeTo` implementation only read and write the repository string, despite
  the request type extending `AcknowledgedRequest`;
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
- explicit fail-closed classification for
  `cluster:admin/decommission/awareness/get` until decommission metadata
  lookup, local read semantics, and decommission status response rendering are
  implemented;
- explicit rejection for custom cluster-manager timeout, local reads, missing
  awareness attribute name, unknown decommission status strings, get-state
  execution, and response rendering.

The delete-decommission-state boundary covers:

- OpenSearch `DeleteDecommissionStateRequest` parent task and cluster-manager
  timeout at the wire decode/build layer;
- OpenSearch `DeleteDecommissionStateResponse` acknowledged response payload
  at the wire decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/decommission/awareness/delete` until recommission
  coordination, decommission metadata removal, cluster-state publication, and
  acknowledgement rendering are implemented;
- explicit rejection for custom cluster-manager timeout, delete-state
  execution, and acknowledgement response rendering.

The put-search-pipeline boundary covers:

- OpenSearch `PutSearchPipelineRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, pipeline id, length-prefixed source bytes, and
  media type at the wire decode/build layer;
- OpenSearch `AcknowledgedResponse` payload at the wire decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/search/pipeline/put` until search pipeline metadata mutation,
  pipeline source parsing and validation, node search pipeline capability
  lookup, cluster-state publication, and acknowledgement rendering are
  implemented;
- explicit rejection for custom cluster-manager timeout, custom
  acknowledgement timeout, missing pipeline id, empty or oversized pipeline
  source, unsupported media types, put-search-pipeline execution, and
  acknowledgement response rendering.

The get-search-pipeline boundary covers:

- OpenSearch `GetSearchPipelineRequest` parent task, cluster-manager timeout,
  local flag, and pipeline ids at the wire decode/build layer;
- OpenSearch `GetSearchPipelineResponse` pipeline count and repeated search
  `PipelineConfiguration` id, config bytes, and media type at the wire
  decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/search/pipeline/get` until search pipeline metadata lookup,
  id/wildcard resolution, local read semantics, and response rendering are
  implemented;
- explicit rejection for custom cluster-manager timeout, local cluster-state
  reads, blank pipeline id selectors, get-search-pipeline execution, unknown
  response media types, and negative response pipeline counts.

The delete-search-pipeline boundary covers:

- OpenSearch `DeleteSearchPipelineRequest` parent task, cluster-manager
  timeout, acknowledgement timeout, and pipeline id at the wire decode/build
  layer;
- OpenSearch `AcknowledgedResponse` payload at the wire decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/search/pipeline/delete` until search pipeline wildcard
  deletion, missing-pipeline handling, metadata mutation, cluster-state
  publication, and acknowledgement rendering are implemented;
- explicit rejection for custom cluster-manager timeout, custom
  acknowledgement timeout, missing pipeline id, delete-search-pipeline
  execution, and acknowledgement response rendering.

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
- explicit fail-closed classification for
  `cluster:admin/routing/awareness/weights/get` until weighted routing
  metadata lookup, awareness attribute verification, discovered
  cluster-manager flag handling, version rendering, and response rendering are
  implemented;
- explicit rejection for custom cluster-manager timeout, local reads, missing
  awareness attribute names, and get-weighted-routing execution.

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
- explicit fail-closed classification for `indices:admin/mappings/get` until
  mapping metadata response rendering is implemented;
- explicit rejection for custom cluster-manager timeout, index filters, local
  reads, custom indices options, and get-mappings execution.

The get-field-mappings boundary covers:

- OpenSearch `GetFieldMappingsRequest` parent task, indices array,
  `IndicesOptions.strictExpandOpen()`, `local`, fields array, and
  `includeDefaults` at the OpenSearch 3.x wire decode/build layer;
- explicit fail-closed classification for `indices:admin/mappings/fields/get`
  until field mapping metadata response rendering is implemented;
- explicit rejection for index filters, custom indices options, local reads,
  field filters, include-default expansion, and get-field-mappings execution.

The put-mapping boundary covers:

- OpenSearch `PutMappingRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, indices array, `IndicesOptions.fromOptions(false,
  false, true, true)`, mapping source string, optional concrete `Index`,
  optional origin, and `writeIndexOnly` at the OpenSearch 3.x wire decode/build
  layer;
- explicit fail-closed classification for `indices:admin/mapping/put` until
  mapping validation, metadata mutation, and acknowledged response rendering
  are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing index targets, custom indices options,
  empty mapping sources, concrete-index routing, custom origins,
  write-index-only updates, and put-mapping execution.

The auto-put-mapping boundary covers:

- OpenSearch `PutMappingRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, absent unresolved indices, default put-mapping
  indices options, mapping source string, required concrete `Index`, optional
  origin, and `writeIndexOnly` at the OpenSearch 3.x wire decode/build layer;
- explicit fail-closed classification for `indices:admin/mapping/auto_put`
  until concrete-index mapping validation, metadata mutation, and acknowledged
  response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing concrete indices, unresolved indices,
  custom indices options, empty mapping sources, custom origins,
  write-index-only updates, and auto-put-mapping execution.

The indices-aliases boundary covers:

- OpenSearch `IndicesAliasesRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, alias action list, optional origin, and
  `AliasActions` add/remove/remove-index ordinals, indices array, aliases
  array, optional filter, routing fields, optional write-index flag, optional
  hidden flag, original aliases array, and optional must-exist flag at the
  OpenSearch 3.x wire decode/build layer;
- explicit fail-closed classification for `indices:admin/aliases` until alias
  metadata mutation, remove-index sub-actions, and acknowledged response
  rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, empty action lists, custom origins, unknown alias
  action ordinals, missing index targets, missing alias targets, remove-index
  alias payloads, filtered aliases, alias routing, write-index updates, hidden
  alias updates, must-exist removals, and indices-aliases execution.

The index update-settings boundary covers:

- OpenSearch `UpdateSettingsRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, nullable indices array encoded as an OpenSearch
  string array, `IndicesOptions.fromOptions(false, false, true, true)`,
  string-valued Settings generic map, and `preserveExisting` at the OpenSearch
  3.x wire decode/build layer;
- explicit fail-closed classification for `indices:admin/settings/update`
  until index resolution, settings validation, metadata mutation, and
  acknowledged response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing index targets, custom indices options,
  empty settings maps, non-index setting keys, non-string generic setting
  values, preserve-existing updates, and index update-settings execution.

The scale-index boundary covers:

- OpenSearch `ScaleIndexRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, target index, `scaleDown`, and
  `IndicesOptions.strictExpandOpen()` at the OpenSearch 3.x wire decode/build
  layer;
- explicit fail-closed classification for `indices:admin/scale/search_only`
  until search-only state validation, shard sync coordination, metadata
  mutation, and acknowledged response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing index targets, custom indices options,
  scale-up transitions, and scale-index execution.

The analyze boundary covers:

- OpenSearch `AnalyzeAction.Request` parent task, absent internal shard id,
  optional index, text array, optional analyzer, optional tokenizer
  `NameOrDefinition`, token filter list, char filter list, optional field,
  `explain`, attributes array, and optional normalizer at the OpenSearch 3.x
  wire decode/build layer;
- explicit fail-closed classification for `indices:admin/analyze` until analyzer
  resolution, token generation, and response rendering are implemented;
- explicit rejection for internal shard-id payloads, missing text, normalizers
  without indices, invalid normalizer/analyzer/field component combinations,
  custom analyzer components, explain responses, attribute-filtered responses,
  and analyze execution.

The create-index boundary covers:

- OpenSearch `CreateIndexRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, cause, index, string-valued settings map, mappings
  string, alias count, `ActiveShardCount`, and absent context marker at the
  OpenSearch 3.x wire decode/build layer;
- explicit fail-closed classification for `indices:admin/create` until index
  metadata mutation, shard allocation, and create-index response rendering are
  implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing index names, custom cause strings,
  settings, mappings, aliases, custom wait-for-active-shards, context payloads,
  and create-index execution.

The auto-create boundary covers:

- OpenSearch `CreateIndexRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, cause, target index, string-valued settings map,
  mappings string, alias count, `ActiveShardCount`, and absent context marker at
  the OpenSearch 3.x wire decode/build layer;
- explicit fail-closed classification for `indices:admin/auto_create` until
  auto-create index/data-stream resolution, cluster-manager metadata mutation,
  active-shards wait, and create-index response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing index names, custom cause strings,
  settings, mappings, aliases, custom wait-for-active-shards, context payloads,
  and auto-create execution.

The put-stored-script boundary covers:

- OpenSearch `PutStoredScriptRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, optional stored script id, content
  `BytesReference`, media type string, optional context, and
  `StoredScriptSource` language/source/options at the OpenSearch 3.x wire
  decode/build layer;
- explicit fail-closed classification for `cluster:admin/script/put` until
  script source parsing, script context validation, cluster metadata mutation,
  and acknowledgement response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing or invalid ids, empty content, non-JSON
  media types, explicit script contexts, missing language/source fields,
  compiler options, and put-stored-script execution.

The get-stored-script boundary covers:

- OpenSearch `GetStoredScriptRequest` parent task, cluster-manager timeout,
  local-read flag, and stored script id at the OpenSearch 3.x wire decode/build
  layer;
- OpenSearch `GetStoredScriptResponse` found marker, optional
  `StoredScriptSource` language/source/options, and id at the OpenSearch 3.x
  response wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/script/get` until
  stored script metadata lookup and found/not-found response rendering are
  implemented;
- explicit rejection for custom cluster-manager timeouts, local reads, missing
  ids, invalid ids, and get-stored-script execution.

The delete-stored-script boundary covers:

- OpenSearch `DeleteStoredScriptRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, and stored script id at the OpenSearch 3.x wire
  decode/build layer;
- explicit fail-closed classification for `cluster:admin/script/delete` until
  stored script metadata mutation, delete-task throttling, and acknowledgement
  response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing ids, invalid ids, and
  delete-stored-script execution.

The get-script-context boundary covers:

- OpenSearch `GetScriptContextRequest` parent task at the OpenSearch 3.x wire
  decode/build layer;
- OpenSearch `GetScriptContextResponse` context count and `ScriptContextInfo`
  name, execute method, getter methods, and method parameter metadata at the
  wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/script_context/get`
  until Rust-supported script context catalog mapping and response rendering
  are implemented;
- explicit rejection for get-script-context execution, plus defensive decode
  rejection for negative context, getter, and parameter counts.

The get-script-language boundary covers:

- OpenSearch `GetScriptLanguageRequest` parent task at the OpenSearch 3.x wire
  decode/build layer;
- OpenSearch `GetScriptLanguageResponse` / `ScriptLanguagesInfo`
  `types_allowed` string collection and language-to-contexts string collection
  map at the wire decode/build layer;
- explicit fail-closed classification for `cluster:admin/script_language/get`
  until Rust-supported script language/type/context catalog mapping and
  response rendering are implemented;
- explicit rejection for get-script-language execution, plus defensive decode
  rejection for negative type, language, and context counts.

The put-pipeline boundary covers:

- OpenSearch `PutPipelineRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, pipeline id, source bytes, and media type at the
  OpenSearch 3.x wire decode/build layer;
- OpenSearch `AcknowledgedResponse` decode/build for the put-pipeline response
  acknowledgement bit;
- explicit fail-closed classification for
  `cluster:admin/ingest/pipeline/put` until ingest pipeline validation,
  processor availability checks, cluster metadata mutation, throttling, and ack
  rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing ids, missing source bytes, non-JSON media
  types, and put-pipeline execution.

The get-pipeline boundary covers:

- OpenSearch `GetPipelineRequest` parent task, cluster-manager timeout, local
  flag, and pipeline ids at the OpenSearch 3.x wire decode/build layer;
- OpenSearch `GetPipelineResponse` pipeline count and repeated
  `PipelineConfiguration` id, config bytes, and media type at the wire
  decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/ingest/pipeline/get` until ingest pipeline metadata lookup,
  id/wildcard resolution, and response rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, local cluster-state
  reads, and get-pipeline execution, plus defensive decode rejection for
  negative response pipeline counts.

The delete-pipeline boundary covers:

- OpenSearch `DeletePipelineRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, and pipeline id at the OpenSearch 3.x wire
  decode/build layer;
- OpenSearch `AcknowledgedResponse` decode/build for the delete-pipeline
  response acknowledgement bit;
- explicit fail-closed classification for
  `cluster:admin/ingest/pipeline/delete` until ingest pipeline wildcard
  deletion, missing-pipeline handling, cluster metadata mutation, throttling,
  and ack rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing ids, and delete-pipeline execution.

The simulate-pipeline boundary covers:

- OpenSearch `SimulatePipelineRequest` parent task, optional pipeline id,
  verbose flag, source bytes, and media type at the OpenSearch 3.x wire
  decode/build layer;
- OpenSearch `SimulatePipelineResponse` optional pipeline id, verbose flag,
  and empty result count decode/build, with explicit rejection for non-empty
  document/processor result payloads until those result shapes are modeled;
- explicit fail-closed classification for
  `cluster:admin/ingest/pipeline/simulate` until ingest pipeline source
  parsing, processor execution, verbose result capture, and response rendering
  are implemented;
- explicit rejection for missing source bytes, non-JSON media types, and
  simulate-pipeline execution, plus defensive decode rejection for negative
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
- explicit fail-closed classification for `indices:admin/delete` until index
  metadata mutation, shard cleanup, and acknowledged response rendering are
  implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, empty or blank index targets, custom indices
  options, and delete-index execution.

The open-index boundary covers:

- OpenSearch `OpenIndexRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, indices array, `IndicesOptions.fromOptions(false,
  true, false, true)`, and default `ActiveShardCount` at the wire decode/build
  layer;
- explicit fail-closed classification for `indices:admin/open` until index
  metadata mutation, shard allocation, and shards-ack response rendering are
  implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, empty or blank index targets, custom indices
  options, custom wait-for-active-shards, and open-index execution.

The close-index boundary covers:

- OpenSearch `CloseIndexRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, indices array, `IndicesOptions.strictExpandOpen()`,
  and `ActiveShardCount.NONE` at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/close` until index
  metadata mutation, shard state transition, and close response rendering are
  implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, empty or blank index targets, custom indices
  options, custom wait-for-active-shards, and close-index execution.

The add-index-block boundary covers:

- OpenSearch `AddIndexBlockRequest` parent task, cluster-manager timeout,
  acknowledgement timeout, indices array, `IndicesOptions.strictExpandOpen()`,
  and `IndexMetadata.APIBlock` ordinal at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/block/add` until
  index block metadata mutation and add-block response rendering are
  implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, empty or blank index targets, custom indices
  options, unknown APIBlock ordinals, internal-only `read_only_allow_delete`,
  and add-index-block execution.

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
- explicit fail-closed classification for `indices:admin/template/get` until
  legacy index-template metadata can be rendered from Rust cluster metadata with
  OpenSearch-compatible name and wildcard matching semantics;
- explicit rejection for custom cluster-manager timeouts, local reads, blank
  template names, name filters, and get-index-templates execution.

The put-index-template boundary covers:

- OpenSearch `PutIndexTemplateRequest` parent task, cluster-manager timeout,
  cause, template name, index pattern list, order, create flag, string-valued
  settings map, optional mappings string, zero-alias marker, and optional
  version at the OpenSearch 3.x wire decode/build layer;
- explicit fail-closed classification for `indices:admin/template/put` until
  legacy index-template validation, metadata mutation, and acknowledged
  response rendering are implemented against Rust cluster metadata;
- explicit rejection for custom cluster-manager timeouts, missing template
  names, missing index patterns, custom causes, non-zero order, create-only
  writes, settings, mappings, alias payloads, versions, and put-index-template
  execution.

The delete-index-template boundary covers:

- OpenSearch `DeleteIndexTemplateRequest` parent task, cluster-manager timeout,
  and template name at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/template/delete`
  until legacy index-template metadata mutation and acknowledged response
  rendering are implemented against Rust cluster metadata;
- explicit rejection for custom cluster-manager timeouts and
  delete-index-template execution.

The put-component-template boundary covers:

- OpenSearch `PutComponentTemplateAction.Request` parent task, cluster-manager
  timeout, component-template name, optional cause, create flag, empty
  `Template` settings/mappings/aliases markers, optional component-template
  version, and absent metadata marker at the OpenSearch 3.x wire decode/build
  layer;
- explicit fail-closed classification for
  `cluster:admin/component_template/put` until component-template validation,
  metadata mutation, and acknowledged response rendering are implemented
  against Rust cluster metadata;
- explicit rejection for custom cluster-manager timeouts, missing template
  names, custom causes, create-only writes, component-template settings,
  mappings, aliases, versions, metadata payloads, and put-component-template
  execution.

The get-component-template boundary covers:

- OpenSearch `GetComponentTemplateAction.Request` parent task,
  cluster-manager timeout, local flag, and optional component-template name at
  the wire decode/build layer;
- explicit fail-closed classification for
  `cluster:admin/component_template/get` until component-template metadata can
  be rendered from Rust cluster metadata with OpenSearch-compatible exact and
  wildcard matching semantics;
- explicit rejection for custom cluster-manager timeouts, local reads, name
  filters, and get-component-template execution.

The delete-component-template boundary covers:

- OpenSearch `DeleteComponentTemplateAction.Request` parent task,
  cluster-manager timeout, and component-template name at the wire decode/build
  layer;
- explicit fail-closed classification for
  `cluster:admin/component_template/delete` until component-template metadata
  mutation and acknowledged response rendering are implemented against Rust
  cluster metadata;
- explicit rejection for custom cluster-manager timeouts and
  delete-component-template execution.

The put-composable-index-template boundary covers:

- OpenSearch `PutComposableIndexTemplateAction.Request` parent task,
  cluster-manager timeout, composable index-template name, optional cause,
  create flag, index patterns, optional empty nested `Template`, optional
  composed-of list, optional priority, optional version, absent metadata map,
  absent data stream marker, and absent context marker at the OpenSearch 3.x
  wire decode/build layer;
- explicit fail-closed classification for `indices:admin/index_template/put`
  until composable index-template validation, metadata mutation, and
  acknowledged response rendering are implemented against Rust cluster
  metadata;
- explicit rejection for custom cluster-manager timeouts, missing template
  names, missing index patterns, custom causes, create-only writes, settings,
  mappings, aliases, composed-of component references, priorities, versions,
  metadata payloads, data stream templates, contexts, and
  put-composable-index-template execution.

The get-composable-index-template boundary covers:

- OpenSearch `GetComposableIndexTemplateAction.Request` parent task,
  cluster-manager timeout, local flag, and optional composable index-template
  name at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/index_template/get`
  until composable index-template metadata can be rendered from Rust cluster
  metadata with OpenSearch-compatible exact and wildcard matching semantics;
- explicit rejection for custom cluster-manager timeouts, local reads, name
  filters, and get-composable-index-template execution.

The delete-composable-index-template boundary covers:

- OpenSearch `DeleteComposableIndexTemplateAction.Request` parent task,
  cluster-manager timeout, and composable index-template name at the wire
  decode/build layer;
- explicit fail-closed classification for
  `indices:admin/index_template/delete` until composable index-template
  metadata mutation and acknowledged response rendering are implemented against
  Rust cluster metadata;
- explicit rejection for custom cluster-manager timeouts and
  delete-composable-index-template execution.

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
- explicit fail-closed classification for `indices:admin/validate/query` until
  query parser, rewrite, shard selection, and validation response rendering are
  implemented against Rust query execution semantics;
- explicit rejection for index filters, custom indices options, non-`match_all`
  query builders, custom boosts, named-query markers, explain, rewrite,
  all-shards validation, and validate-query execution.

The flush boundary covers:

- OpenSearch `FlushRequest` parent task, nullable index array, default
  `IndicesOptions.strictExpandOpenAndForbidClosed()`, force flag, and
  wait-if-ongoing flag at the OpenSearch 3.x wire decode/build layer;
- explicit fail-closed classification for `indices:admin/flush` until shard
  translog flush execution, wait-if-ongoing concurrency semantics, and shard
  status response rendering are implemented against Rust shard state;
- explicit rejection for index filters, custom indices options,
  `force=true && wait_if_ongoing=false` validation failures, forced flush,
  non-waiting flush, and flush execution.

The force-merge boundary covers:

- OpenSearch `ForceMergeRequest` parent task, nullable index array, default
  `IndicesOptions.strictExpandOpenAndForbidClosed()`, max segment count,
  only-expunge-deletes flag, post-merge flush flag, primary-only flag, and
  OpenSearch 3.x non-optional force-merge UUID at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/forcemerge` until
  shard segment merge execution, primary-only routing, post-merge flush, and
  shard status response rendering are implemented against Rust shard state;
- explicit rejection for index filters, custom indices options, bounded segment
  counts, delete-expunge-only merges, `flush=false`, primary-only routing,
  empty force-merge UUIDs, and force-merge execution.

The upgrade boundary covers:

- OpenSearch `UpgradeRequest` parent task, nullable index array, default
  `IndicesOptions.strictExpandOpenAndForbidClosed()`, and
  upgrade-only-ancient-segments flag at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/upgrade` until shard
  segment upgrade execution, primary availability checks, settings update, and
  response rendering are implemented against Rust shard state;
- explicit rejection for index filters, custom indices options,
  ancient-segment-only upgrades, and upgrade execution.

The upgrade-status boundary covers:

- OpenSearch `UpgradeStatusRequest` parent task, nullable index array, and
  default `IndicesOptions.strictExpandOpenAndForbidClosed()` at the wire
  decode/build layer;
- explicit fail-closed classification for `indices:monitor/upgrade` until shard
  segment-version stats, routing metadata, and response rendering are
  implemented against Rust shard state;
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
- explicit fail-closed classification for `indices:admin/cache/clear` until
  shard query, field-data, request, file, and node-wide cache clearing plus
  shard status response rendering are implemented against Rust shard state;
- explicit rejection for index filters, custom indices options, blank field
  names, query-cache clearing, field-data cache clearing, field selectors,
  request-cache clearing, file-cache clearing, and clear-cache execution.

The field-capabilities boundary covers:

- OpenSearch `FieldCapabilitiesRequest` parent task, fields array, indices
  array, `IndicesOptions.strictExpandOpen()`, `mergeResults`, `includeUnmapped`,
  optional index-filter query marker, and optional `nowInMillis` at the wire
  decode/build layer;
- explicit fail-closed classification for `indices:data/read/field_caps` until
  mapping/type metadata response rendering is implemented;
- explicit rejection for empty fields, index filters, custom indices options,
  unmerged responses, include-unmapped expansion, index-filter query rewrite,
  timestamp injection, and field-capabilities execution.

The get-aliases boundary covers:

- OpenSearch `GetAliasesRequest` parent task, cluster-manager timeout, indices
  array, `local` flag, aliases array, `IndicesOptions.strictExpandHidden()`,
  and original aliases array at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/aliases/get` until
  alias metadata response rendering and alias post-processing semantics are
  implemented;
- explicit rejection for custom cluster-manager timeout, index filters, local
  reads, alias filters, custom indices options, original alias filters, and
  get-aliases execution.

The get-settings boundary covers:

- OpenSearch `GetSettingsRequest` parent task, cluster-manager timeout, indices
  array, `local` flag, `IndicesOptions.fromOptions(false, true, true, true)`,
  names array, `humanReadable`, and `includeDefaults` at the wire decode/build
  layer;
- explicit fail-closed classification for `indices:monitor/settings/get` until
  index settings metadata response rendering and settings filtering semantics
  are implemented;
- explicit rejection for custom cluster-manager timeout, index filters, local
  reads, custom indices options, name filters, human-readable formatting,
  include-default expansion, and get-settings execution.

The cluster-search-shards boundary covers:

- OpenSearch `ClusterSearchShardsRequest` parent task, cluster-manager timeout,
  `local` flag, indices array, optional routing, optional preference,
  `IndicesOptions.lenientExpandOpen()`, and OpenSearch 2.19+ slice-present flag
  at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/shards/search_shards`
  until shard routing metadata response rendering is implemented;
- explicit rejection for custom cluster-manager timeout, local reads, index
  filters, routing, preference, custom indices options, slice payloads, and
  cluster-search-shards execution.

The recovery boundary covers:

- OpenSearch `RecoveryRequest` parent task, indices array,
  `IndicesOptions.STRICT_EXPAND_OPEN_CLOSED`, `detailed`, and `activeOnly` at
  the wire decode/build layer;
- explicit fail-closed classification for `indices:monitor/recovery` until
  shard recovery metadata response rendering is implemented;
- explicit rejection for index filters, custom indices options, detailed
  recovery output, active-only filtering, and recovery execution.

The segment-replication-stats boundary covers:

- OpenSearch `SegmentReplicationStatsRequest` parent task, broadcast indices
  array, `IndicesOptions.strictExpandOpenAndForbidClosed()`, `detailed`, and
  `activeOnly` at the wire decode/build layer;
- explicit fail-closed classification for
  `indices:monitor/segment_replication` until shard routing, segment
  replication pressure-service stats, target-service state, primary/replica
  grouping, and response rendering are implemented;
- explicit rejection for index filters, custom indices options, detailed stage
  timing output, active-only filtering, and segment-replication-stats
  execution.

The indices-segments boundary covers:

- OpenSearch `IndicesSegmentsRequest` parent task, indices array,
  `IndicesOptions.strictExpandOpenAndForbidClosed()`, and `verbose` at the wire
  decode/build layer;
- explicit fail-closed classification for `indices:monitor/segments` until
  shard segment metadata response rendering is implemented;
- explicit rejection for index filters, custom indices options, verbose segment
  output, and indices-segments execution.

The PIT-segments boundary covers:

- OpenSearch `PitSegmentsRequest` parent task, broadcast indices array,
  `IndicesOptions.strictExpandOpenAndForbidClosed()`, nullable PIT id array,
  and `verbose` at the wire decode/build layer;
- explicit fail-closed classification for
  `indices:monitor/point_in_time/segments` until PIT segment metadata response
  rendering is implemented;
- explicit rejection for index filters, custom indices options, null PIT id
  arrays, empty PIT id arrays, empty PIT id entries, verbose output, and
  PIT-segments execution.

The indices-shard-stores boundary covers:

- OpenSearch `IndicesShardStoresRequest` parent task, cluster-manager timeout,
  `local` flag, indices array, shard health status byte set, and
  `IndicesOptions.strictExpand()` at the wire decode/build layer;
- explicit fail-closed classification for `indices:monitor/shard_stores` until
  shard allocation/store metadata response rendering is implemented;
- explicit rejection for custom cluster-manager timeout, local reads, index
  filters, custom shard health status filters, custom indices options, and
  indices-shard-stores execution.

The create-data-stream boundary covers:

- OpenSearch `CreateDataStreamAction.Request` parent task, cluster-manager
  timeout, acknowledgement timeout, and data-stream name at the wire
  decode/build layer;
- OpenSearch `AcknowledgedResponse` decode/build for the create-data-stream
  response acknowledgement bit;
- explicit fail-closed classification for
  `indices:admin/data_stream/create` until data-stream template resolution,
  backing index creation, timestamp mapping validation, cluster metadata
  mutation, and ack rendering are implemented;
- explicit rejection for custom cluster-manager timeouts, custom
  acknowledgement timeouts, missing names, and create-data-stream execution.

The delete-data-stream boundary covers:

- OpenSearch `DeleteDataStreamAction.Request` parent task, cluster-manager
  timeout, and data-stream names array at the wire decode/build layer;
- OpenSearch `AcknowledgedResponse` decode/build for the delete-data-stream
  response acknowledgement bit;
- explicit fail-closed classification for `indices:admin/data_stream/delete`
  until data-stream name/wildcard resolution, snapshot-in-progress protection,
  backing index deletion, cluster metadata mutation, and ack rendering are
  implemented;
- explicit rejection for custom cluster-manager timeouts, missing name arrays,
  blank names, and delete-data-stream execution.

The get-data-stream boundary covers:

- OpenSearch `GetDataStreamAction.Request` parent task, cluster-manager
  timeout, `local` flag, and optional data-stream name array at the wire
  decode/build layer;
- explicit fail-closed classification for `indices:admin/data_stream/get` until
  data-stream metadata response rendering is implemented;
- explicit rejection for custom cluster-manager timeout, local reads, name
  filters, null name arrays outside the REST default path, and get-data-stream
  execution.

The data-streams-stats boundary covers:

- OpenSearch `DataStreamsStatsAction.Request` parent task, indices array, and
  `IndicesOptions.strictExpandOpenAndForbidClosed()` at the wire decode/build
  layer;
- explicit fail-closed classification for `indices:monitor/data_stream/stats`
  until data-stream stats aggregation and response rendering are implemented;
- explicit rejection for name filters, custom indices options, and
  data-streams-stats execution.

The resolve-index boundary covers:

- OpenSearch `ResolveIndexAction.Request` parent task, names array, and
  `IndicesOptions.strictExpandOpen()` at the wire decode/build layer;
- explicit fail-closed classification for `indices:admin/resolve/index` until
  index abstraction metadata response rendering is implemented;
- explicit rejection for empty name arrays, custom indices options, and
  resolve-index execution.

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
- explicit fail-closed classification for `views:data/read/list` until
  view-name listing and list response rendering are implemented;
- explicit rejection for list-view-names execution and unsupported response
  shapes such as blank names, oversized names, or excessive name counts.

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
- explicit fail-closed classification for
  `cluster:admin/indices/dangling/list` until BaseNodes fanout, dangling index
  state scan, node aggregation, failures, and response rendering are
  implemented;
- explicit rejection for concrete DiscoveryNode payloads, node filters,
  timeout semantics, empty or oversized index UUID filters, non-empty node
  responses, node failures, list-dangling-indices execution, and response
  rendering.

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
- explicit fail-closed classification for
  `cluster:admin/indices/dangling/find` until BaseNodes fanout, dangling index
  state scan, node `IndexMetadata` aggregation, failures, and response
  rendering are implemented;
- explicit rejection for concrete DiscoveryNode payloads, node filters,
  timeout semantics, missing or oversized index UUIDs, non-empty node
  responses, node failures, find-dangling-index execution, and response
  rendering.

The search boundary covers:

- OpenSearch `SearchRequest` parent task, search type, indices array, routing,
  preference, absent scroll, absent search source, search indices options,
  request-cache flag, reduce/fanout controls, partial-results flag,
  cross-cluster reduction flags, cancellation interval, search pipeline, and
  phase timing flag at the wire decode/build layer;
- explicit fail-closed classification for `indices:data/read/search` until
  search source decoding and response rendering are mapped;
- explicit rejection for source/scroll payloads, non-default index/routing/
  preference/fanout/cache/partial-results/cross-cluster/pipeline/timing shapes,
  and search execution.

The stream-search boundary covers:

- OpenSearch `StreamSearchAction` action binding with the same bounded
  `SearchRequest` wire decode/build layer used by normal search;
- explicit fail-closed classification for `indices:data/read/search/stream`
  until streaming response semantics are mapped;
- explicit rejection through the bounded `SearchRequest` execution boundary.

The multi-search boundary covers:

- OpenSearch `MultiSearchRequest` parent task, max concurrent search request
  count, sub-search count, and nested `SearchRequest` wire shapes at the wire
  decode/build layer;
- explicit fail-closed classification for `indices:data/read/msearch` until
  batched search source decoding and response rendering are mapped;
- explicit rejection for custom multi-search concurrency, empty request batches,
  unsupported nested search request shapes, and multi-search execution.

The search-scroll boundary covers:

- OpenSearch `SearchScrollRequest` parent task, scroll id, and optional
  keep-alive `Scroll` time value at the wire decode/build layer;
- explicit fail-closed classification for `indices:data/read/scroll` until
  scroll context lifecycle and response rendering are mapped;
- explicit rejection for empty scroll ids, missing keep-alive values, and
  search-scroll execution.

The clear-scroll boundary covers:

- OpenSearch `ClearScrollRequest` parent task and scroll id array at the wire
  decode/build layer;
- explicit fail-closed classification for `indices:data/read/scroll/clear`
  until scroll context invalidation and clear-scroll response rendering are
  mapped;
- explicit rejection for empty scroll id arrays, empty scroll id entries, and
  clear-scroll execution.

The explain boundary covers:

- OpenSearch `ExplainRequest` parent task, single-shard prefix, index, id,
  routing, preference, query named-writeable marker, alias filter marker,
  optional stored fields, fetch-source context marker, and `nowInMillis` at the
  bounded wire decode/build layer;
- explicit fail-closed classification for `indices:data/read/explain` until
  query builder decoding and explanation response rendering are mapped;
- explicit rejection for concrete shard ids, missing index/id/query fields,
  routing, preference, alias filters, stored fields, fetch-source context, and
  explain execution.

The delete-PIT boundary covers:

- OpenSearch `DeletePitRequest` parent task and PIT id array at the wire
  decode/build layer;
- explicit fail-closed classification for
  `indices:data/read/point_in_time/delete` until PIT context invalidation and
  response rendering are mapped;
- explicit rejection for empty PIT id arrays, empty PIT id entries, and
  delete-PIT execution.

The get-all-PITs boundary covers:

- OpenSearch `GetAllPitNodesRequest` parent task, nullable node ids, concrete
  node payload presence, and optional timeout at the wire decode/build layer;
- explicit fail-closed classification for
  `indices:data/read/point_in_time/readall` until PIT context listing and node
  fanout response rendering are mapped;
- explicit rejection for concrete node payloads, node filters, timeout
  semantics, and get-all-PITs execution.

The create-PIT boundary covers:

- OpenSearch `CreatePitRequest` parent task, indices array, search default
  indices options, routing, preference, keep-alive time value, and optional
  `allowPartialPitCreation` flag at the wire decode/build layer;
- explicit fail-closed classification for
  `indices:data/read/point_in_time/create` until PIT context creation and
  response rendering are mapped;
- explicit rejection for non-positive keep-alive values, index filters, custom
  indices options, routing, preference, partial creation flags, and create-PIT
  execution.

The indices-stats boundary covers:

- OpenSearch `IndicesStatsRequest` parent task, indices array, indices options,
  and `CommonStatsFlags` at the wire decode/build layer;
- explicit fail-closed classification for `indices:monitor/stats` until runtime
  index stats aggregation and field-level metric mapping are implemented;
- explicit rejection for index filters, non-default indices options,
  non-default stats flags, and indices-stats execution.

The list-tasks adapter covers:

- OpenSearch `ListTasksRequest` parent task, unset task id filter, unset parent
  task filter, no node filters, no action filters, no timeout, `detailed=false`,
  and `wait_for_completion=false`;
- OpenSearch `ListTasksResponse` with no task failures, no node failures, and
  no task info entries, matching the current no-active-task transport contract;
- explicit rejection for task id filters, parent task filters, node filters,
  action filters, timeout, detailed task info, wait-for-completion, non-empty
  task failure payloads, non-empty node failure payloads, and non-empty task
  info payloads until runtime task lifecycle semantics are mapped.

The get-task boundary covers:

- OpenSearch `GetTaskRequest` parent task, explicit task id, optional timeout,
  and wait-for-completion fields at the wire decode/build layer;
- explicit fail-closed classification for `cluster:monitor/task/get` until
  runtime task result lifecycle and unknown-task error semantics are mapped;
- explicit rejection for missing task id, timeout, wait-for-completion, point
  lookup execution, and task-result response payloads.

The cancel-tasks adapter covers:

- OpenSearch `CancelTasksRequest` parent task, unset task id filter, unset
  parent task filter, no node filters, no action filters, no timeout, default
  reason `by user request`, and `wait_for_completion=false`;
- OpenSearch `CancelTasksResponse` with no cancelled task entries, no task
  failures, and no node failures, matching the current no-active-cancellable-task
  transport contract;
- explicit rejection for task id filters, parent task filters, node filters,
  action filters, timeout, custom reason, wait-for-completion, non-empty task
  failure payloads, non-empty node failure payloads, and non-empty task info
  payloads until runtime task cancellation lifecycle semantics are mapped.

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

Current main reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin main-reject-wire-benchmark
main_reject_request_encode iterations=400000 elapsed_ms=180.233 ops_per_second=2219352.17 nanos_per_op=450.58
main_reject_request_decode iterations=400000 elapsed_ms=174.344 ops_per_second=2294317.85 nanos_per_op=435.86
main_reject_validation iterations=400000 elapsed_ms=177.000 ops_per_second=2259888.73 nanos_per_op=442.50
main_reject_wire_bottleneck_ops_per_second=2219352.17
```

The current main fail-closed boundary bottleneck is request encode over the
parent-task-only request frame. At roughly 2.22M ops/s in the latest local
release run, this boundary is not a material performance bottleneck; the first
performance-sensitive work is main response rendering from node, cluster,
version, and build metadata.

Current remote-info reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin remote-info-reject-wire-benchmark
remote_info_reject_request_encode iterations=400000 elapsed_ms=192.187 ops_per_second=2081306.99 nanos_per_op=480.47
remote_info_reject_request_decode iterations=400000 elapsed_ms=189.142 ops_per_second=2114817.44 nanos_per_op=472.85
remote_info_reject_validation iterations=400000 elapsed_ms=190.136 ops_per_second=2103758.30 nanos_per_op=475.34
remote_info_reject_wire_bottleneck_ops_per_second=2081306.99
```

The current remote-info fail-closed boundary bottleneck is request encode over
the parent-task-only request frame. At roughly 2.08M ops/s in the latest local
release run, this boundary is not a material performance bottleneck; the first
performance-sensitive work is remote connection info collection and response
rendering.

Current get-term-version reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-term-version-reject-wire-benchmark
get_term_version_reject_request_encode iterations=400000 elapsed_ms=182.897 ops_per_second=2187025.16 nanos_per_op=457.24
get_term_version_reject_request_decode iterations=400000 elapsed_ms=179.348 ops_per_second=2230304.23 nanos_per_op=448.37
get_term_version_reject_validation iterations=400000 elapsed_ms=180.954 ops_per_second=2210507.69 nanos_per_op=452.38
get_term_version_reject_wire_bottleneck_ops_per_second=2187025.16
```

The current get-term-version fail-closed boundary bottleneck is request encode
over the parent-task, cluster-manager-timeout, and local-flag request frame. At
roughly 2.19M ops/s in the latest local release run, this boundary is not a
material performance bottleneck; the first performance-sensitive work is
cluster term/version lookup and response rendering.

Current cluster-stats reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin cluster-stats-reject-wire-benchmark
cluster_stats_reject_request_encode ops_per_second=1758185.25 nanos_per_op=568.77
cluster_stats_reject_request_decode ops_per_second=1903296.67 nanos_per_op=525.40
cluster_stats_reject_validation ops_per_second=1843125.57 nanos_per_op=542.56
cluster_stats_reject_wire_bottleneck_ops_per_second=1758185.25
```

The current cluster-stats fail-closed boundary bottleneck is request encode.
The validation path adds only a small unsupported-shape check on top of decode,
so the rejection boundary itself is not a new performance bottleneck. At roughly
1.76M ops/s in the latest local release run, this path is in the same range as
the lightweight admin transport adapters.

Current cat-shards reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin cat-shards-reject-wire-benchmark
cat_shards_reject_request_encode iterations=400000 elapsed_ms=184.729 ops_per_second=2165329.22 nanos_per_op=461.82
cat_shards_reject_request_decode iterations=400000 elapsed_ms=201.912 ops_per_second=1981056.97 nanos_per_op=504.78
cat_shards_reject_validation iterations=400000 elapsed_ms=204.856 ops_per_second=1952587.62 nanos_per_op=512.14
cat_shards_reject_wire_bottleneck_ops_per_second=1952587.62
```

The current cat-shards fail-closed boundary bottleneck is validation. This path
carries the ActionRequest parent task, cluster-manager timeout, local flag,
indices array, optional cancel-after timeout, optional pagination, and
request-limit marker before rejecting execution. At roughly 1.95M ops/s in the
latest local release run, the boundary itself is lightweight; the first
performance point to inspect before accepting execution is shard routing plus
indices stats response rendering.

Current nodes-info reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin nodes-info-reject-wire-benchmark
nodes_info_reject_request_encode ops_per_second=758739.72 nanos_per_op=1317.98
nodes_info_reject_request_decode ops_per_second=654994.28 nanos_per_op=1526.73
nodes_info_reject_validation ops_per_second=643305.31 nanos_per_op=1554.47
nodes_info_reject_wire_bottleneck_ops_per_second=643305.31
```

The current nodes-info fail-closed boundary bottleneck is validation over the
decoded request. The dominant cost is the OpenSearch default metric string array
encode/decode, not the unsupported execution check itself. At roughly 643K ops/s
in the latest local release run, this boundary is still below the JSON
source-materializing document paths but is materially heavier than the compact
cluster-stats request shape.

Current nodes-stats reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin nodes-stats-reject-wire-benchmark
nodes_stats_reject_request_encode ops_per_second=1660735.39 nanos_per_op=602.14
nodes_stats_reject_request_decode ops_per_second=1676765.46 nanos_per_op=596.39
nodes_stats_reject_validation ops_per_second=1617055.31 nanos_per_op=618.41
nodes_stats_reject_wire_bottleneck_ops_per_second=1617055.31
```

The current nodes-stats fail-closed boundary bottleneck is validation. This path
adds a full `CommonStatsFlags` default-shape comparison after decode, so it is
slightly heavier than the cluster-stats rejection boundary. At roughly 1.62M
ops/s in the latest local release run, it remains in the lightweight admin
transport range and does not introduce a new source-materialization bottleneck.

Current wlm-stats reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin wlm-stats-reject-wire-benchmark
wlm_stats_reject_request_encode iterations=400000 elapsed_ms=198.339 ops_per_second=2016752.00 nanos_per_op=495.85
wlm_stats_reject_request_decode iterations=400000 elapsed_ms=213.768 ops_per_second=1871191.12 nanos_per_op=534.42
wlm_stats_reject_validation iterations=400000 elapsed_ms=214.693 ops_per_second=1863122.80 nanos_per_op=536.73
wlm_stats_reject_wire_bottleneck_ops_per_second=1863122.80
```

The current wlm-stats fail-closed boundary bottleneck is validation. The path
checks node routing, timeout, workload group filters, and breach filter before
rejecting execution. At roughly 1.86M ops/s in the latest local release run,
this boundary is not a material transport bottleneck; the first
performance-sensitive work is workload group runtime telemetry collection and
response rendering.

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

Current remote-store-metadata reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin remote-store-metadata-reject-wire-benchmark
remote_store_metadata_reject_request_encode iterations=400000 elapsed_ms=261.324 ops_per_second=1530664.17 nanos_per_op=653.31
remote_store_metadata_reject_request_decode iterations=400000 elapsed_ms=247.605 ops_per_second=1615476.14 nanos_per_op=619.01
remote_store_metadata_reject_validation iterations=400000 elapsed_ms=249.019 ops_per_second=1606302.41 nanos_per_op=622.55
remote_store_metadata_reject_wire_bottleneck_ops_per_second=1530664.17
```

The current remote-store-metadata fail-closed boundary bottleneck is request
encode. The payload includes the broadcast request envelope, indices options,
and shard filter array before admission rejects execution. At roughly 1.53M
ops/s in the latest local release run, this boundary is not a material
transport bottleneck; the first performance-sensitive work is remote store
shard metadata collection and response rendering.

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

Current nodes-usage reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin nodes-usage-reject-wire-benchmark
nodes_usage_reject_request_encode iterations=400000 elapsed_ms=209.850 ops_per_second=1906122.53 nanos_per_op=524.63
nodes_usage_reject_request_decode iterations=400000 elapsed_ms=196.421 ops_per_second=2036446.99 nanos_per_op=491.05
nodes_usage_reject_validation iterations=400000 elapsed_ms=205.378 ops_per_second=1947629.65 nanos_per_op=513.44
nodes_usage_reject_wire_bottleneck_ops_per_second=1906122.53
```

The current nodes-usage fail-closed boundary bottleneck is request encode. The
request payload is compact, with only the BaseNodesRequest envelope and two
boolean usage flags, so validation does not add measurable overhead. At roughly
1.91M ops/s in the latest local release run, this is one of the lightest admin
transport boundaries.

Current nodes-hot-threads reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin nodes-hot-threads-reject-wire-benchmark
nodes_hot_threads_reject_request_encode iterations=400000 elapsed_ms=262.869 ops_per_second=1521670.82 nanos_per_op=657.17
nodes_hot_threads_reject_request_decode iterations=400000 elapsed_ms=242.725 ops_per_second=1647956.61 nanos_per_op=606.81
nodes_hot_threads_reject_validation iterations=400000 elapsed_ms=245.280 ops_per_second=1630792.35 nanos_per_op=613.20
nodes_hot_threads_reject_wire_bottleneck_ops_per_second=1521670.82
```

The current nodes-hot-threads fail-closed boundary bottleneck is request encode.
The payload adds fixed diagnostic sampling controls on top of the BaseNodesRequest
envelope, so it is heavier than nodes-usage but still in the lightweight admin
transport range. At roughly 1.52M ops/s in the latest local release run, this
boundary does not introduce a source-materialization bottleneck.

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

Current get-repositories reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-repositories-reject-wire-benchmark
get_repositories_reject_request_encode iterations=400000 elapsed_ms=197.691 ops_per_second=2023360.94 nanos_per_op=494.23
get_repositories_reject_request_decode iterations=400000 elapsed_ms=197.141 ops_per_second=2029007.16 nanos_per_op=492.85
get_repositories_reject_validation iterations=400000 elapsed_ms=198.312 ops_per_second=2017023.64 nanos_per_op=495.78
get_repositories_reject_wire_bottleneck_ops_per_second=2017023.64
```

The current get-repositories fail-closed boundary bottleneck is validation over
the decoded default request. The payload is only the ClusterManagerNodeRead
envelope, local flag, and an empty repository-name array, so this remains one of the
lightest read/admin rejection paths. At roughly 2.02M ops/s in the latest local
release run, it does not introduce a transport-wire bottleneck.

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

Current get-decommission-state reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-decommission-state-reject-wire-benchmark
get_decommission_state_reject_request_encode iterations=400000 elapsed_ms=275.449 ops_per_second=1452171.82 nanos_per_op=688.62
get_decommission_state_reject_request_decode iterations=400000 elapsed_ms=290.715 ops_per_second=1375919.69 nanos_per_op=726.79
get_decommission_state_reject_validation iterations=400000 elapsed_ms=248.151 ops_per_second=1611920.97 nanos_per_op=620.38
get_decommission_state_response_decode iterations=400000 elapsed_ms=126.773 ops_per_second=3155255.27 nanos_per_op=316.93
get_decommission_state_reject_wire_bottleneck_ops_per_second=1375919.69
```

The current get-decommission-state fail-closed boundary bottleneck is request
decode. The payload includes the cluster-manager read request envelope,
read-local flag, and awareness attribute name before admission rejects
execution. At roughly 1.38M ops/s in the latest local release run, this
boundary is not a material transport bottleneck; the first
performance-sensitive work is decommission metadata lookup, local read
semantics, and decommission status response rendering.

Current delete-decommission-state reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-decommission-state-reject-wire-benchmark
delete_decommission_state_reject_request_encode iterations=400000 elapsed_ms=231.121 ops_per_second=1730693.90 nanos_per_op=577.80
delete_decommission_state_reject_request_decode iterations=400000 elapsed_ms=229.797 ops_per_second=1740669.81 nanos_per_op=574.49
delete_decommission_state_reject_validation iterations=400000 elapsed_ms=230.574 ops_per_second=1734803.64 nanos_per_op=576.43
delete_decommission_state_ack_response_decode iterations=400000 elapsed_ms=56.465 ops_per_second=7084068.23 nanos_per_op=141.16
delete_decommission_state_reject_wire_bottleneck_ops_per_second=1730693.90
```

The current delete-decommission-state fail-closed boundary bottleneck is
request encode. The payload includes only the cluster-manager request envelope
before admission rejects execution. At roughly 1.73M ops/s in the latest
local release run, this boundary is not a material transport bottleneck; the
first performance-sensitive work is recommission coordination, decommission
metadata removal, cluster-state publication, and acknowledgement rendering.

Current put-search-pipeline reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-search-pipeline-reject-wire-benchmark
put_search_pipeline_reject_request_encode iterations=400000 elapsed_ms=421.978 ops_per_second=947915.71 nanos_per_op=1054.95
put_search_pipeline_reject_request_decode iterations=400000 elapsed_ms=377.641 ops_per_second=1059208.39 nanos_per_op=944.10
put_search_pipeline_reject_validation iterations=400000 elapsed_ms=377.630 ops_per_second=1059237.23 nanos_per_op=944.08
put_search_pipeline_ack_response_decode iterations=400000 elapsed_ms=55.001 ops_per_second=7272553.13 nanos_per_op=137.50
put_search_pipeline_reject_wire_bottleneck_ops_per_second=947915.71
```

The current put-search-pipeline fail-closed boundary bottleneck is request
encode. The payload includes the cluster-manager request envelope,
acknowledgement timeout, pipeline id, source bytes, and media type string
before admission rejects execution. At roughly 0.95M ops/s in the latest local
release run, this boundary is not a material transport bottleneck; the first
performance-sensitive work is search pipeline source parsing and validation,
node search pipeline capability lookup, cluster-state publication, and
acknowledgement rendering.

Current get-search-pipeline reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-search-pipeline-reject-wire-benchmark
get_search_pipeline_reject_request_encode iterations=400000 elapsed_ms=277.449 ops_per_second=1441705.91 nanos_per_op=693.62
get_search_pipeline_reject_request_decode iterations=400000 elapsed_ms=256.314 ops_per_second=1560587.96 nanos_per_op=640.78
get_search_pipeline_reject_validation iterations=400000 elapsed_ms=257.732 ops_per_second=1551996.95 nanos_per_op=644.33
get_search_pipeline_response_decode iterations=400000 elapsed_ms=225.717 ops_per_second=1772131.53 nanos_per_op=564.29
get_search_pipeline_reject_wire_bottleneck_ops_per_second=1441705.91
```

The current get-search-pipeline fail-closed boundary bottleneck is request
encode. The payload includes the cluster-manager read request envelope, local
flag, and pipeline id selectors before admission rejects execution. At roughly
1.44M ops/s in the latest local release run, this boundary is not a material
transport bottleneck; the first performance-sensitive work is search pipeline
metadata lookup, id/wildcard resolution, local read semantics, and response
rendering.

Current delete-search-pipeline reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-search-pipeline-reject-wire-benchmark
delete_search_pipeline_reject_request_encode iterations=400000 elapsed_ms=276.359 ops_per_second=1447394.26 nanos_per_op=690.90
delete_search_pipeline_reject_request_decode iterations=400000 elapsed_ms=255.554 ops_per_second=1565228.47 nanos_per_op=638.88
delete_search_pipeline_reject_validation iterations=400000 elapsed_ms=261.307 ops_per_second=1530763.68 nanos_per_op=653.27
delete_search_pipeline_ack_response_decode iterations=400000 elapsed_ms=55.455 ops_per_second=7213034.04 nanos_per_op=138.64
delete_search_pipeline_reject_wire_bottleneck_ops_per_second=1447394.26
```

The current delete-search-pipeline fail-closed boundary bottleneck is request
encode. The payload includes the acknowledged cluster-manager request envelope
and pipeline id before admission rejects execution. At roughly 1.45M ops/s in
the latest local release run, this boundary is not a material transport
bottleneck; the first performance-sensitive work is search pipeline wildcard
matching, missing-pipeline handling, metadata mutation, cluster-state
publication, and acknowledgement rendering.

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
knn_stats_reject_request_encode iterations=400000 elapsed_ms=3033.249 ops_per_second=131871.81 nanos_per_op=7583.12
knn_stats_reject_request_decode iterations=400000 elapsed_ms=2992.545 ops_per_second=133665.50 nanos_per_op=7481.36
knn_stats_reject_validation iterations=400000 elapsed_ms=3083.152 ops_per_second=129737.36 nanos_per_op=7707.88
knn_stats_response_decode iterations=400000 elapsed_ms=98.807 ops_per_second=4048277.57 nanos_per_op=247.02
knn_stats_reject_wire_bottleneck_ops_per_second=129737.36
```

The current knn-stats fail-closed boundary bottleneck is request validation
including frame/request decode. The payload includes the BaseNodes envelope plus
the full k-NN valid stat-name set, so string allocation and stat-set validation
dominate this boundary at roughly 130k ops/s in the latest local release run.
This is still fail-closed admission work, but it is a real performance hotspot
to keep in view when implementing execution; the first semantic work is
BaseNodes fanout, node-level KNN stat collection, cluster-level stat
aggregation, failure aggregation, and response rendering.

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

Current get-weighted-routing reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-weighted-routing-reject-wire-benchmark
get_weighted_routing_reject_request_encode iterations=400000 elapsed_ms=307.201 ops_per_second=1302080.10 nanos_per_op=768.00
get_weighted_routing_reject_request_decode iterations=400000 elapsed_ms=305.909 ops_per_second=1307577.24 nanos_per_op=764.77
get_weighted_routing_reject_validation iterations=400000 elapsed_ms=328.614 ops_per_second=1217232.82 nanos_per_op=821.54
get_weighted_routing_reject_wire_bottleneck_ops_per_second=1217232.82
```

The current get-weighted-routing fail-closed boundary bottleneck is request
validation. The payload includes the cluster-manager read request envelope,
local flag, and awareness attribute name before admission rejects execution. At
roughly 1.22M ops/s in the latest local release run, this boundary is not the
primary expected performance risk; the first performance-sensitive work is
awareness attribute verification, weighted routing metadata lookup, version
rendering, discovered cluster-manager flag handling, and response rendering.

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

Current get-mappings reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-mappings-reject-wire-benchmark
get_mappings_reject_request_encode iterations=400000 elapsed_ms=234.612 ops_per_second=1704941.84 nanos_per_op=586.53
get_mappings_reject_request_decode iterations=400000 elapsed_ms=226.785 ops_per_second=1763782.95 nanos_per_op=566.96
get_mappings_reject_validation iterations=400000 elapsed_ms=230.615 ops_per_second=1734492.03 nanos_per_op=576.54
get_mappings_reject_wire_bottleneck_ops_per_second=1704941.84
```

The current get-mappings fail-closed boundary bottleneck is request encode. The
payload adds the local flag and `IndicesOptions.strictExpandOpen()` to the
ClusterManagerNodeRead envelope and empty index array, so it is slightly heavier
than get-repositories but still inside the lightweight admin transport range at
roughly 1.70M ops/s in the latest local release run.

Current get-field-mappings reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-field-mappings-reject-wire-benchmark
get_field_mappings_reject_request_encode iterations=400000 elapsed_ms=258.224 ops_per_second=1549043.10 nanos_per_op=645.56
get_field_mappings_reject_request_decode iterations=400000 elapsed_ms=241.097 ops_per_second=1659086.51 nanos_per_op=602.74
get_field_mappings_reject_validation iterations=400000 elapsed_ms=244.342 ops_per_second=1637049.71 nanos_per_op=610.86
get_field_mappings_reject_wire_bottleneck_ops_per_second=1549043.10
```

The current get-field-mappings fail-closed boundary bottleneck is request
encode. This path checks indices options, local execution, field filters,
and include-default expansion after reading the OpenSearch 3.x request body, so
it is slightly heavier than get-mappings. At roughly 1.55M ops/s in the latest
local release run, it remains in the lightweight admin transport range.

Current put-mapping reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-mapping-reject-wire-benchmark
put_mapping_reject_request_encode iterations=400000 elapsed_ms=449.071 ops_per_second=890727.50 nanos_per_op=1122.68
put_mapping_reject_request_decode iterations=400000 elapsed_ms=369.100 ops_per_second=1083715.91 nanos_per_op=922.75
put_mapping_reject_validation iterations=400000 elapsed_ms=360.289 ops_per_second=1110219.42 nanos_per_op=900.72
put_mapping_reject_wire_bottleneck_ops_per_second=890727.50
```

The current put-mapping fail-closed boundary bottleneck is request encode. The
path writes the acknowledged-request envelope, index target array, indices
options, mapping source string, absent concrete-index marker, origin marker,
and `writeIndexOnly` flag before rejecting execution. At roughly 0.89M ops/s in
the latest local release run, the current overhead is still request wire
boundary work; future performance-sensitive work is mapping validation,
metadata mutation, and acknowledged response rendering.

Current auto-put-mapping reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin auto-put-mapping-reject-wire-benchmark
auto_put_mapping_reject_request_encode iterations=400000 elapsed_ms=412.890 ops_per_second=968781.14 nanos_per_op=1032.22
auto_put_mapping_reject_request_decode iterations=400000 elapsed_ms=413.480 ops_per_second=967399.79 nanos_per_op=1033.70
auto_put_mapping_reject_validation iterations=400000 elapsed_ms=436.055 ops_per_second=917314.78 nanos_per_op=1090.14
auto_put_mapping_reject_wire_bottleneck_ops_per_second=917314.78
```

The current auto-put-mapping fail-closed boundary bottleneck is validation. The
path reuses the put-mapping request body but requires a concrete index and
rejects unresolved index targets before execution. At roughly 0.92M ops/s in
the latest local release run, the current overhead is still lightweight
transport shape validation; future performance-sensitive work is
concrete-index mapping validation, metadata mutation, and acknowledged response
rendering.

Current indices-aliases reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin indices-aliases-reject-wire-benchmark
indices_aliases_reject_request_encode iterations=400000 elapsed_ms=380.930 ops_per_second=1050062.61 nanos_per_op=952.32
indices_aliases_reject_request_decode iterations=400000 elapsed_ms=394.077 ops_per_second=1015029.67 nanos_per_op=985.19
indices_aliases_reject_validation iterations=400000 elapsed_ms=405.229 ops_per_second=987095.27 nanos_per_op=1013.07
indices_aliases_reject_wire_bottleneck_ops_per_second=987095.27
```

The current indices-aliases fail-closed boundary bottleneck is validation. The
path decodes one alias add action, checks default timeouts, origin, action
presence, required index and alias fields, and unsupported alias options before
rejecting execution. At roughly 0.99M ops/s in the latest local release run,
the current overhead remains lightweight transport shape validation; future
performance-sensitive work is alias metadata mutation, remove-index sub-action
handling, and acknowledged response rendering.

Current index update-settings reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin update-settings-reject-wire-benchmark
update_settings_reject_request_encode iterations=400000 elapsed_ms=423.666 ops_per_second=944140.46 nanos_per_op=1059.16
update_settings_reject_request_decode iterations=400000 elapsed_ms=389.513 ops_per_second=1026923.13 nanos_per_op=973.78
update_settings_reject_validation iterations=400000 elapsed_ms=404.031 ops_per_second=990022.58 nanos_per_op=1010.08
update_settings_reject_wire_bottleneck_ops_per_second=944140.46
```

The current index update-settings fail-closed boundary bottleneck is request
encode. The path writes the acknowledged-request envelope, target index array,
indices options, and a string-valued OpenSearch Settings generic map before
rejecting execution. At roughly 0.94M ops/s in the latest local release run,
the current overhead remains transport wire work; future performance-sensitive
work is index resolution, setting validation, metadata mutation, and
acknowledged response rendering.

Current scale-index reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin scale-index-reject-wire-benchmark
scale_index_reject_request_encode iterations=400000 elapsed_ms=309.055 ops_per_second=1294268.61 nanos_per_op=772.64
scale_index_reject_request_decode iterations=400000 elapsed_ms=278.302 ops_per_second=1437285.67 nanos_per_op=695.76
scale_index_reject_validation iterations=400000 elapsed_ms=282.344 ops_per_second=1416711.11 nanos_per_op=705.86
scale_index_reject_wire_bottleneck_ops_per_second=1294268.61
```

The current scale-index fail-closed boundary bottleneck is request encode. The
path writes the acknowledged-request envelope, target index, scale direction,
and indices options before rejecting execution. At roughly 1.29M ops/s in the
latest local release run, the current overhead remains lightweight transport
wire work; future performance-sensitive work is search-only state validation,
shard sync coordination, metadata mutation, and acknowledged response
rendering.

Current analyze reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin analyze-reject-wire-benchmark
analyze_reject_request_encode iterations=400000 elapsed_ms=328.042 ops_per_second=1219354.63 nanos_per_op=820.11
analyze_reject_request_decode iterations=400000 elapsed_ms=311.325 ops_per_second=1284830.36 nanos_per_op=778.31
analyze_reject_validation iterations=400000 elapsed_ms=317.401 ops_per_second=1260236.41 nanos_per_op=793.50
analyze_reject_wire_bottleneck_ops_per_second=1219354.63
```

The current analyze fail-closed boundary bottleneck is request encode. The path
writes the single-shard request envelope, optional index, text array, analyzer
selection, custom component lists, explain flag, attributes, and normalizer
before rejecting execution. At roughly 1.22M ops/s in the latest local release
run, the current overhead remains transport wire work; future
performance-sensitive work is analyzer resolution, token generation, and
response rendering.

Current create-index reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin create-index-reject-wire-benchmark
create_index_reject_request_encode iterations=400000 elapsed_ms=274.096 ops_per_second=1459343.83 nanos_per_op=685.24
create_index_reject_request_decode iterations=400000 elapsed_ms=256.711 ops_per_second=1558169.59 nanos_per_op=641.78
create_index_reject_validation iterations=400000 elapsed_ms=264.949 ops_per_second=1509721.87 nanos_per_op=662.37
create_index_reject_wire_bottleneck_ops_per_second=1459343.83
```

The current create-index fail-closed boundary bottleneck is request encode. The
request carries an acknowledged-request envelope, index name, empty settings,
default mappings, empty alias count, default wait-for-active-shards, and absent
context before the execution boundary rejects. At roughly 1.46M ops/s in the
latest local release run, the future performance-sensitive work is index
metadata mutation, shard allocation, and create-index response rendering rather
than the fail-closed wire boundary.

Current auto-create reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin auto-create-reject-wire-benchmark
auto_create_reject_request_encode iterations=400000 elapsed_ms=275.880 ops_per_second=1449907.21 nanos_per_op=689.70
auto_create_reject_request_decode iterations=400000 elapsed_ms=268.132 ops_per_second=1491804.71 nanos_per_op=670.33
auto_create_reject_validation iterations=400000 elapsed_ms=272.505 ops_per_second=1467860.97 nanos_per_op=681.26
auto_create_reject_wire_bottleneck_ops_per_second=1449907.21
```

The current auto-create fail-closed boundary bottleneck is request encode. It
uses the same `CreateIndexRequest` wire shape as create-index with the
`indices:admin/auto_create` action frame, so the current overhead remains
transport frame/request serialization. At roughly 1.45M ops/s in the latest
local release run, the future performance-sensitive work is auto-create
index/data-stream resolution, cluster-manager metadata mutation, active-shards
wait, and response rendering.

Current put-stored-script reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-stored-script-reject-wire-benchmark
put_stored_script_reject_request_encode iterations=400000 elapsed_ms=481.887 ops_per_second=830069.93 nanos_per_op=1204.72
put_stored_script_reject_request_decode iterations=400000 elapsed_ms=480.088 ops_per_second=833181.05 nanos_per_op=1200.22
put_stored_script_reject_validation iterations=400000 elapsed_ms=494.523 ops_per_second=808860.27 nanos_per_op=1236.31
put_stored_script_reject_wire_bottleneck_ops_per_second=808860.27
```

The current put-stored-script fail-closed boundary bottleneck is validation.
The path decodes an acknowledged cluster-manager request, optional id, script
content `BytesReference`, media type string, optional context, and
`StoredScriptSource` language/source/options before rejecting execution. At
roughly 0.81M ops/s in the latest local release run, current overhead is still
bounded wire validation; future performance-sensitive work is script source
parsing, script context validation, cluster metadata mutation, and ack
rendering.

Current get-stored-script reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-stored-script-reject-wire-benchmark
get_stored_script_reject_request_encode iterations=400000 elapsed_ms=302.906 ops_per_second=1320541.97 nanos_per_op=757.26
get_stored_script_reject_request_decode iterations=400000 elapsed_ms=247.197 ops_per_second=1618141.50 nanos_per_op=617.99
get_stored_script_reject_validation iterations=400000 elapsed_ms=282.449 ops_per_second=1416184.55 nanos_per_op=706.12
get_stored_script_response_decode iterations=400000 elapsed_ms=228.782 ops_per_second=1748392.68 nanos_per_op=571.95
get_stored_script_reject_wire_bottleneck_ops_per_second=1320541.97
```

The current get-stored-script fail-closed boundary bottleneck is request
encode. The request path carries the cluster-manager read envelope, local-read
flag, and script id before rejecting execution; the found response decode path
also covers `StoredScriptSource` language/source/options. At roughly 1.32M
ops/s in the latest local release run, current overhead is transport
serialization, not response decode. Future performance-sensitive work is script
metadata lookup and found/not-found response rendering.

Current delete-stored-script reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-stored-script-reject-wire-benchmark
delete_stored_script_reject_request_encode iterations=400000 elapsed_ms=279.007 ops_per_second=1433656.03 nanos_per_op=697.52
delete_stored_script_reject_request_decode iterations=400000 elapsed_ms=251.419 ops_per_second=1590968.57 nanos_per_op=628.55
delete_stored_script_reject_validation iterations=400000 elapsed_ms=261.307 ops_per_second=1530768.46 nanos_per_op=653.27
delete_stored_script_reject_wire_bottleneck_ops_per_second=1433656.03
```

The current delete-stored-script fail-closed boundary bottleneck is request
encode. The request path carries the acknowledged cluster-manager envelope and
stored script id before rejecting execution. At roughly 1.43M ops/s in the
latest local release run, current overhead is transport serialization; future
performance-sensitive work is script metadata mutation, delete-task throttling,
and ack rendering.

Current get-script-context reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-script-context-reject-wire-benchmark
get_script_context_reject_request_encode iterations=400000 elapsed_ms=222.431 ops_per_second=1798308.72 nanos_per_op=556.08
get_script_context_reject_request_decode iterations=400000 elapsed_ms=223.940 ops_per_second=1786189.27 nanos_per_op=559.85
get_script_context_reject_validation iterations=400000 elapsed_ms=249.352 ops_per_second=1604159.30 nanos_per_op=623.38
get_script_context_response_decode iterations=400000 elapsed_ms=384.613 ops_per_second=1040005.61 nanos_per_op=961.53
get_script_context_reject_wire_bottleneck_ops_per_second=1040005.61
```

The current get-script-context fail-closed boundary bottleneck is response
decode. The request path is thin, but the response path expands
`ScriptContextInfo` method and parameter metadata before execution is rejected.
At roughly 1.04M ops/s in the latest local release run, current overhead is
script context response structure decoding. Future performance-sensitive work is
building the Rust script context catalog without repeated allocation-heavy
method metadata expansion.

Current get-script-language reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-script-language-reject-wire-benchmark
get_script_language_reject_request_encode iterations=400000 elapsed_ms=211.420 ops_per_second=1891966.13 nanos_per_op=528.55
get_script_language_reject_request_decode iterations=400000 elapsed_ms=202.714 ops_per_second=1973219.13 nanos_per_op=506.79
get_script_language_reject_validation iterations=400000 elapsed_ms=202.727 ops_per_second=1973099.22 nanos_per_op=506.82
get_script_language_response_decode iterations=400000 elapsed_ms=415.345 ops_per_second=963054.44 nanos_per_op=1038.36
get_script_language_reject_wire_bottleneck_ops_per_second=963054.44
```

The current get-script-language fail-closed boundary bottleneck is response
decode. The request path is thin, but the response path expands allowed script
types plus the language-to-contexts map before execution is rejected. At roughly
963K ops/s in the latest local release run, current overhead is script language
catalog response decoding. Future performance-sensitive work is building and
serving the Rust script language catalog without repeated allocation-heavy
string collection expansion.

Current put-pipeline reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-pipeline-reject-wire-benchmark
put_pipeline_reject_request_encode iterations=400000 elapsed_ms=404.405 ops_per_second=989108.66 nanos_per_op=1011.01
put_pipeline_reject_request_decode iterations=400000 elapsed_ms=374.548 ops_per_second=1067954.06 nanos_per_op=936.37
put_pipeline_reject_validation iterations=400000 elapsed_ms=377.719 ops_per_second=1058987.13 nanos_per_op=944.30
put_pipeline_ack_response_decode iterations=400000 elapsed_ms=54.074 ops_per_second=7397212.13 nanos_per_op=135.19
put_pipeline_reject_wire_bottleneck_ops_per_second=989108.66
```

The current put-pipeline fail-closed boundary bottleneck is request encode. The
request path carries the acknowledged cluster-manager envelope, pipeline id,
source bytes, and media type before rejecting execution. At roughly 989K ops/s
in the latest local release run, current overhead is transport serialization.
Future performance-sensitive work is ingest pipeline source parsing, processor
availability validation, cluster metadata mutation, throttling, and ack
rendering.

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

Current delete-pipeline reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-pipeline-reject-wire-benchmark
delete_pipeline_reject_request_encode iterations=400000 elapsed_ms=310.542 ops_per_second=1288070.68 nanos_per_op=776.35
delete_pipeline_reject_request_decode iterations=400000 elapsed_ms=256.572 ops_per_second=1559014.29 nanos_per_op=641.43
delete_pipeline_reject_validation iterations=400000 elapsed_ms=276.245 ops_per_second=1447989.37 nanos_per_op=690.61
delete_pipeline_ack_response_decode iterations=400000 elapsed_ms=54.984 ops_per_second=7274875.61 nanos_per_op=137.46
delete_pipeline_reject_wire_bottleneck_ops_per_second=1288070.68
```

The current delete-pipeline fail-closed boundary bottleneck is request encode.
The request path carries the acknowledged cluster-manager envelope and pipeline
id before rejecting execution. At roughly 1.29M ops/s in the latest local
release run, current overhead is transport serialization. Future
performance-sensitive work is wildcard matching against the Rust ingest
pipeline metadata catalog, missing-pipeline response handling, metadata
mutation, throttling, and ack rendering.

Current simulate-pipeline reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin simulate-pipeline-reject-wire-benchmark
simulate_pipeline_reject_request_encode iterations=400000 elapsed_ms=388.827 ops_per_second=1028733.92 nanos_per_op=972.07
simulate_pipeline_reject_request_decode iterations=400000 elapsed_ms=368.415 ops_per_second=1085732.62 nanos_per_op=921.04
simulate_pipeline_reject_validation iterations=400000 elapsed_ms=376.035 ops_per_second=1063729.46 nanos_per_op=940.09
simulate_pipeline_empty_response_decode iterations=400000 elapsed_ms=95.969 ops_per_second=4168018.49 nanos_per_op=239.92
simulate_pipeline_reject_wire_bottleneck_ops_per_second=1028733.92
```

The current simulate-pipeline fail-closed boundary bottleneck is request
encode. The request path carries optional pipeline id, verbose flag, source
bytes, and media type before rejecting execution. At roughly 1.03M ops/s in the
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

Current delete-index reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-index-reject-wire-benchmark
delete_index_reject_request_encode iterations=400000 elapsed_ms=287.248 ops_per_second=1392526.50 nanos_per_op=718.12
delete_index_reject_request_decode iterations=400000 elapsed_ms=275.243 ops_per_second=1453261.93 nanos_per_op=688.11
delete_index_reject_validation iterations=400000 elapsed_ms=283.962 ops_per_second=1408637.38 nanos_per_op=709.91
delete_index_reject_wire_bottleneck_ops_per_second=1392526.50
```

The current delete-index fail-closed boundary bottleneck is request encode. The
request carries an acknowledged-request envelope, non-empty index target, and
delete-index default indices options before the execution boundary rejects. At
roughly 1.39M ops/s in the latest local release run, the future
performance-sensitive work is index metadata mutation, shard cleanup, and
acknowledged response rendering rather than the fail-closed wire boundary.

Current open-index reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin open-index-reject-wire-benchmark
open_index_reject_request_encode iterations=400000 elapsed_ms=276.449 ops_per_second=1446921.63 nanos_per_op=691.12
open_index_reject_request_decode iterations=400000 elapsed_ms=292.761 ops_per_second=1366300.88 nanos_per_op=731.90
open_index_reject_validation iterations=400000 elapsed_ms=425.628 ops_per_second=939787.79 nanos_per_op=1064.07
open_index_reject_wire_bottleneck_ops_per_second=939787.79
```

The current open-index fail-closed boundary bottleneck is validation over the
decoded request. The request carries an acknowledged-request envelope,
non-empty index target, open-index default indices options, and default
wait-for-active-shards before the execution boundary rejects. At roughly 0.94M
ops/s in the latest local release run, the fail-closed boundary remains cheap,
but the validation branch is the local bottleneck to revisit if this path becomes
hot before the real index metadata mutation, shard allocation, and shards-ack
response rendering work lands.

Current close-index reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin close-index-reject-wire-benchmark
close_index_reject_request_encode iterations=400000 elapsed_ms=281.995 ops_per_second=1418467.36 nanos_per_op=704.99
close_index_reject_request_decode iterations=400000 elapsed_ms=272.221 ops_per_second=1469395.14 nanos_per_op=680.55
close_index_reject_validation iterations=400000 elapsed_ms=276.253 ops_per_second=1447946.76 nanos_per_op=690.63
close_index_reject_wire_bottleneck_ops_per_second=1418467.36
```

The current close-index fail-closed boundary bottleneck is request encode. The
request carries an acknowledged-request envelope, non-empty index target,
close-index default indices options, and `ActiveShardCount.NONE` before the
execution boundary rejects. At roughly 1.42M ops/s in the latest local release
run, the future performance-sensitive work is index metadata mutation, shard
state transition, and close response rendering rather than the fail-closed wire
boundary.

Current add-index-block reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin add-index-block-reject-wire-benchmark
add_index_block_reject_request_encode iterations=400000 elapsed_ms=281.863 ops_per_second=1419127.12 nanos_per_op=704.66
add_index_block_reject_request_decode iterations=400000 elapsed_ms=277.215 ops_per_second=1442924.82 nanos_per_op=693.04
add_index_block_reject_validation iterations=400000 elapsed_ms=317.918 ops_per_second=1258185.20 nanos_per_op=794.80
add_index_block_reject_wire_bottleneck_ops_per_second=1258185.20
```

The current add-index-block fail-closed boundary bottleneck is validation over
the decoded request. The request carries an acknowledged-request envelope,
non-empty index target, strict-open indices options, and APIBlock ordinal before
the execution boundary rejects. At roughly 1.26M ops/s in the latest local
release run, the future performance-sensitive work is index block metadata
mutation and add-block response rendering rather than the fail-closed wire
boundary.

Current get-index reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-index-reject-wire-benchmark
get_index_reject_request_encode iterations=400000 elapsed_ms=214.228 ops_per_second=1867165.60 nanos_per_op=535.57
get_index_reject_request_decode iterations=400000 elapsed_ms=221.578 ops_per_second=1805236.92 nanos_per_op=553.94
get_index_reject_validation iterations=400000 elapsed_ms=225.751 ops_per_second=1771860.54 nanos_per_op=564.38
get_index_reject_wire_bottleneck_ops_per_second=1771860.54
```

The current get-index fail-closed boundary bottleneck is validation over the
decoded request. The request carries the ClusterManagerNodeRead envelope, empty
index array, `IndicesOptions.strictExpandOpen()`, default feature byte array,
and two boolean rendering flags. At roughly 1.77M ops/s in the latest local
release run, the remaining performance risk is not the wire boundary; it is the
future aliases/mappings/settings/context metadata response rendering path.

Current indices-exists reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin indices-exists-reject-wire-benchmark
indices_exists_reject_request_encode iterations=400000 elapsed_ms=270.143 ops_per_second=1480697.75 nanos_per_op=675.36
indices_exists_reject_request_decode iterations=400000 elapsed_ms=246.835 ops_per_second=1620517.52 nanos_per_op=617.09
indices_exists_reject_validation iterations=400000 elapsed_ms=245.820 ops_per_second=1627205.86 nanos_per_op=614.55
indices_exists_reject_wire_bottleneck_ops_per_second=1480697.75
```

The current indices-exists fail-closed boundary bottleneck is request encode.
Unlike get-index, the default benchmark request carries a non-empty `logs-*`
target so it exercises the valid OpenSearch request shape before the execution
boundary rejects. At roughly 1.48M ops/s in the latest local release run, the
remaining performance risk is the future index-resolution and boolean response
rendering path, not the fail-closed wire boundary.

Current get-index-templates reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-index-templates-reject-wire-benchmark
get_index_templates_reject_request_encode iterations=400000 elapsed_ms=201.579 ops_per_second=1984333.35 nanos_per_op=503.95
get_index_templates_reject_request_decode iterations=400000 elapsed_ms=191.163 ops_per_second=2092452.77 nanos_per_op=477.91
get_index_templates_reject_validation iterations=400000 elapsed_ms=196.820 ops_per_second=2032310.60 nanos_per_op=492.05
get_index_templates_reject_wire_bottleneck_ops_per_second=1984333.35
```

The current get-index-templates fail-closed boundary bottleneck is request
encode. The default benchmark uses an empty names array, matching the OpenSearch
all-templates request shape, so validation is light and the remaining
performance risk is future template metadata matching and response rendering.
At roughly 1.98M ops/s in the latest local release run, the fail-closed wire
boundary is not a material bottleneck.

Current put-index-template reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-index-template-reject-wire-benchmark
put_index_template_reject_request_encode iterations=400000 elapsed_ms=318.333 ops_per_second=1256545.15 nanos_per_op=795.83
put_index_template_reject_request_decode iterations=400000 elapsed_ms=308.411 ops_per_second=1296970.95 nanos_per_op=771.03
put_index_template_reject_validation iterations=400000 elapsed_ms=317.081 ops_per_second=1261506.37 nanos_per_op=792.70
put_index_template_reject_wire_bottleneck_ops_per_second=1256545.15
```

The current put-index-template fail-closed boundary bottleneck is request
encode. The default benchmark writes a valid empty legacy template shape with a
template name and one index pattern, then rejects before template metadata
mutation. At roughly 1.26M ops/s in the latest local release run, the remaining
performance-sensitive work is template validation, metadata publication, and
acknowledged response rendering.

Current delete-index-template reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-index-template-reject-wire-benchmark
delete_index_template_reject_request_encode iterations=400000 elapsed_ms=307.438 ops_per_second=1301073.85 nanos_per_op=768.60
delete_index_template_reject_request_decode iterations=400000 elapsed_ms=265.167 ops_per_second=1508481.56 nanos_per_op=662.92
delete_index_template_reject_validation iterations=400000 elapsed_ms=255.597 ops_per_second=1564964.69 nanos_per_op=638.99
delete_index_template_reject_wire_bottleneck_ops_per_second=1301073.85
```

The current delete-index-template fail-closed boundary bottleneck is request
encode. This path stays cheap because validation checks only the default
timeout before failing closed; the future performance-sensitive work is
template metadata mutation, publication, and acknowledged response rendering.

Current put-component-template reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-component-template-reject-wire-benchmark
put_component_template_reject_request_encode iterations=400000 elapsed_ms=382.867 ops_per_second=1044748.52 nanos_per_op=957.17
put_component_template_reject_request_decode iterations=400000 elapsed_ms=315.838 ops_per_second=1266471.64 nanos_per_op=789.60
put_component_template_reject_validation iterations=400000 elapsed_ms=312.474 ops_per_second=1280105.88 nanos_per_op=781.19
put_component_template_reject_wire_bottleneck_ops_per_second=1044748.52
```

The current put-component-template fail-closed boundary bottleneck is request
encode. The default benchmark writes the cluster-manager request envelope,
component-template name, absent cause, create flag, empty nested template
markers, absent version, and absent metadata marker before rejecting execution.
At roughly 1.04M ops/s in the latest local release run, the remaining
performance-sensitive work is component-template validation, metadata
publication, and acknowledged response rendering.

Current get-component-template reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-component-template-reject-wire-benchmark
get_component_template_reject_request_encode iterations=400000 elapsed_ms=223.699 ops_per_second=1788117.75 nanos_per_op=559.25
get_component_template_reject_request_decode iterations=400000 elapsed_ms=211.078 ops_per_second=1895035.18 nanos_per_op=527.69
get_component_template_reject_validation iterations=400000 elapsed_ms=212.785 ops_per_second=1879829.53 nanos_per_op=531.96
get_component_template_reject_wire_bottleneck_ops_per_second=1788117.75
```

The current get-component-template fail-closed boundary bottleneck is request
encode. The default benchmark uses an absent optional name, matching the
OpenSearch all-component-templates request shape; the future
performance-sensitive work is component-template metadata matching and response
rendering.

Current delete-component-template reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-component-template-reject-wire-benchmark
delete_component_template_reject_request_encode iterations=400000 elapsed_ms=371.948 ops_per_second=1075418.58 nanos_per_op=929.87
delete_component_template_reject_request_decode iterations=400000 elapsed_ms=297.206 ops_per_second=1345866.73 nanos_per_op=743.02
delete_component_template_reject_validation iterations=400000 elapsed_ms=340.260 ops_per_second=1175570.74 nanos_per_op=850.65
delete_component_template_reject_wire_bottleneck_ops_per_second=1075418.58
```

The current delete-component-template fail-closed boundary bottleneck is
request encode. This path stays cheap because validation checks only the
default timeout before failing closed; the future performance-sensitive work is
component-template metadata mutation, publication, and acknowledged response
rendering.

Current put-composable-index-template reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin put-composable-index-template-reject-wire-benchmark
put_composable_index_template_reject_request_encode iterations=400000 elapsed_ms=355.942 ops_per_second=1123778.17 nanos_per_op=889.86
put_composable_index_template_reject_request_decode iterations=400000 elapsed_ms=338.706 ops_per_second=1180965.02 nanos_per_op=846.77
put_composable_index_template_reject_validation iterations=400000 elapsed_ms=349.263 ops_per_second=1145267.34 nanos_per_op=873.16
put_composable_index_template_reject_wire_bottleneck_ops_per_second=1123778.17
```

The current put-composable-index-template fail-closed boundary bottleneck is
request encode. The default benchmark writes the cluster-manager request
envelope, template name, absent cause, create flag, one index pattern, absent
nested template, absent composed-of list, absent priority/version, absent
metadata map, absent data-stream marker, and absent context marker before
rejecting execution. At roughly 1.12M ops/s in the latest local release run,
the remaining performance-sensitive work is composable index-template
validation, metadata publication, and acknowledged response rendering.

Current get-composable-index-template reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-composable-index-template-reject-wire-benchmark
get_composable_index_template_reject_request_encode iterations=400000 elapsed_ms=219.349 ops_per_second=1823579.62 nanos_per_op=548.37
get_composable_index_template_reject_request_decode iterations=400000 elapsed_ms=199.533 ops_per_second=2004682.03 nanos_per_op=498.83
get_composable_index_template_reject_validation iterations=400000 elapsed_ms=200.343 ops_per_second=1996570.90 nanos_per_op=500.86
get_composable_index_template_reject_wire_bottleneck_ops_per_second=1823579.62
```

The current get-composable-index-template fail-closed boundary bottleneck is
request encode. The default benchmark uses an absent optional name, matching
the OpenSearch all-composable-index-templates request shape; the future
performance-sensitive work is composable index-template metadata matching and
response rendering.

Current delete-composable-index-template reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-composable-index-template-reject-wire-benchmark
delete_composable_index_template_reject_request_encode iterations=400000 elapsed_ms=308.430 ops_per_second=1296888.69 nanos_per_op=771.08
delete_composable_index_template_reject_request_decode iterations=400000 elapsed_ms=278.515 ops_per_second=1436186.11 nanos_per_op=696.29
delete_composable_index_template_reject_validation iterations=400000 elapsed_ms=279.260 ops_per_second=1432358.57 nanos_per_op=698.15
delete_composable_index_template_reject_wire_bottleneck_ops_per_second=1296888.69
```

The current delete-composable-index-template fail-closed boundary bottleneck is
request encode. This path stays cheap because validation checks only the
default timeout before failing closed; the future performance-sensitive work is
composable index-template metadata mutation, publication, and acknowledged
response rendering.

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

Current field-capabilities reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin field-capabilities-reject-wire-benchmark
field_capabilities_reject_request_encode iterations=400000 elapsed_ms=245.330 ops_per_second=1630460.22 nanos_per_op=613.32
field_capabilities_reject_request_decode iterations=400000 elapsed_ms=267.059 ops_per_second=1497794.63 nanos_per_op=667.65
field_capabilities_reject_validation iterations=400000 elapsed_ms=272.583 ops_per_second=1467442.71 nanos_per_op=681.46
field_capabilities_reject_wire_bottleneck_ops_per_second=1467442.71
```

The current field-capabilities fail-closed boundary bottleneck is validation.
This path carries the ActionRequest parent task, field and index arrays,
`IndicesOptions.strictExpandOpen()`, merge/include-unmapped flags, optional
query marker, and optional timestamp before rejecting execution. At roughly
1.47M ops/s in the latest local release run, the boundary itself is
lightweight; the first performance point to inspect before accepting execution
is mapping/type metadata aggregation and field-capabilities response rendering.

Current get-aliases reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-aliases-reject-wire-benchmark
get_aliases_reject_request_encode iterations=400000 elapsed_ms=232.046 ops_per_second=1723796.12 nanos_per_op=580.12
get_aliases_reject_request_decode iterations=400000 elapsed_ms=245.551 ops_per_second=1628988.89 nanos_per_op=613.88
get_aliases_reject_validation iterations=400000 elapsed_ms=251.572 ops_per_second=1590004.67 nanos_per_op=628.93
get_aliases_reject_wire_bottleneck_ops_per_second=1590004.67
```

The current get-aliases fail-closed boundary bottleneck is validation after
decode. This path checks cluster-manager timeout, local execution, index
filters, alias filters, hidden wildcard indices options, and original-alias
post-processing state after reading the OpenSearch request body. At roughly
1.59M ops/s in the latest local release run, it remains in the lightweight
admin transport range.

Current get-settings reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-settings-reject-wire-benchmark
get_settings_reject_request_encode iterations=400000 elapsed_ms=238.223 ops_per_second=1679097.16 nanos_per_op=595.56
get_settings_reject_request_decode iterations=400000 elapsed_ms=240.210 ops_per_second=1665211.28 nanos_per_op=600.52
get_settings_reject_validation iterations=400000 elapsed_ms=244.439 ops_per_second=1636403.30 nanos_per_op=611.10
get_settings_reject_wire_bottleneck_ops_per_second=1636403.30
```

The current get-settings fail-closed boundary bottleneck is validation after
decode. This path checks cluster-manager timeout, local execution, index
filters, open/closed wildcard indices options, setting-name array,
human-readable flag, and default expansion flag before rejecting at admission.
At roughly 1.64M ops/s in the latest local release run, it remains in the
lightweight admin transport range.

Current cluster-search-shards reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin cluster-search-shards-reject-wire-benchmark
cluster_search_shards_reject_request_encode iterations=400000 elapsed_ms=263.696 ops_per_second=1516898.13 nanos_per_op=659.24
cluster_search_shards_reject_request_decode iterations=400000 elapsed_ms=248.926 ops_per_second=1606902.99 nanos_per_op=622.32
cluster_search_shards_reject_validation iterations=400000 elapsed_ms=254.565 ops_per_second=1571309.55 nanos_per_op=636.41
cluster_search_shards_reject_wire_bottleneck_ops_per_second=1516898.13
```

The current cluster-search-shards fail-closed boundary bottleneck is request
encode. This path carries the ClusterManagerNodeRead envelope, local flag,
empty index array, optional routing/preference fields, lenient open-index
options, and slice-present flag before rejecting at admission. At roughly 1.52M
ops/s in the latest local release run, it remains in the lightweight admin
transport range.

Current recovery reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin recovery-reject-wire-benchmark
recovery_reject_request_encode iterations=400000 elapsed_ms=220.369 ops_per_second=1815138.66 nanos_per_op=550.92
recovery_reject_request_decode iterations=400000 elapsed_ms=225.133 ops_per_second=1776727.50 nanos_per_op=562.83
recovery_reject_validation iterations=400000 elapsed_ms=227.547 ops_per_second=1757875.29 nanos_per_op=568.87
recovery_reject_wire_bottleneck_ops_per_second=1757875.29
```

The current recovery fail-closed boundary bottleneck is validation. This path
carries the BroadcastRequest parent task, empty index array, strict open/closed
index options, detailed flag, and active-only flag before rejecting at
admission. At roughly 1.76M ops/s in the latest local release run, the boundary
is lighter than the cluster-search-shards reject path and does not expose a
material wire-codec bottleneck.

Current segment-replication-stats reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin segment-replication-stats-reject-wire-benchmark
segment_replication_stats_reject_request_encode iterations=500000 elapsed_ms=318.914 ops_per_second=1567823.14 nanos_per_op=637.83
segment_replication_stats_reject_request_decode iterations=500000 elapsed_ms=313.560 ops_per_second=1594593.43 nanos_per_op=627.12
segment_replication_stats_reject_validation iterations=500000 elapsed_ms=329.745 ops_per_second=1516321.82 nanos_per_op=659.49
segment_replication_stats_reject_wire_bottleneck_ops_per_second=1516321.82
```

The current segment-replication-stats fail-closed boundary bottleneck is
validation. This path carries the BroadcastRequest parent task, empty index
array, strict open forbid-closed index options, detailed flag, and active-only
flag before rejecting at admission. At roughly 1.52M ops/s in the latest local
release run, the boundary itself is lightweight; the expected performance
pressure for a future implementation is shard routing, pressure-service stats
collection, target-service live state lookup, primary/replica grouping, and
response rendering.

Current indices-segments reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin indices-segments-reject-wire-benchmark
indices_segments_reject_request_encode iterations=400000 elapsed_ms=208.391 ops_per_second=1919464.98 nanos_per_op=520.98
indices_segments_reject_request_decode iterations=400000 elapsed_ms=223.254 ops_per_second=1791683.29 nanos_per_op=558.13
indices_segments_reject_validation iterations=400000 elapsed_ms=226.423 ops_per_second=1766601.77 nanos_per_op=566.06
indices_segments_reject_wire_bottleneck_ops_per_second=1766601.77
```

The current indices-segments fail-closed boundary bottleneck is validation. This
path carries the BroadcastRequest parent task, empty index array, strict open
forbid-closed index options, and verbose flag before rejecting at admission. At
roughly 1.77M ops/s in the latest local release run, it is effectively the same
weight as the recovery reject boundary and does not expose a material wire-codec
bottleneck.

Current indices-shard-stores reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin indices-shard-stores-reject-wire-benchmark
indices_shard_stores_reject_request_encode iterations=400000 elapsed_ms=236.859 ops_per_second=1688769.08 nanos_per_op=592.15
indices_shard_stores_reject_request_decode iterations=400000 elapsed_ms=252.123 ops_per_second=1586527.13 nanos_per_op=630.31
indices_shard_stores_reject_validation iterations=400000 elapsed_ms=243.427 ops_per_second=1643206.27 nanos_per_op=608.57
indices_shard_stores_reject_wire_bottleneck_ops_per_second=1586527.13
```

The current indices-shard-stores fail-closed boundary bottleneck is request
decode. This path carries the ClusterManagerNodeRead envelope, empty index
array, default yellow/red shard health status filter, and strict open/closed
index options before rejecting at admission. At roughly 1.59M ops/s in the
latest local release run, decode is slightly heavier than the recovery and
indices-segments reject boundaries because it must parse timeout/local and the
status byte set.

Current create-data-stream reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin create-data-stream-reject-wire-benchmark
create_data_stream_reject_request_encode iterations=400000 elapsed_ms=245.702 ops_per_second=1627991.54 nanos_per_op=614.25
create_data_stream_reject_request_decode iterations=400000 elapsed_ms=241.485 ops_per_second=1656419.48 nanos_per_op=603.71
create_data_stream_reject_validation iterations=400000 elapsed_ms=246.132 ops_per_second=1625143.93 nanos_per_op=615.33
create_data_stream_ack_response_decode iterations=400000 elapsed_ms=53.899 ops_per_second=7421349.92 nanos_per_op=134.75
create_data_stream_reject_wire_bottleneck_ops_per_second=1625143.93
```

The current create-data-stream fail-closed boundary bottleneck is validation.
The request path carries the acknowledged cluster-manager envelope and
data-stream name before rejecting execution. At roughly 1.63M ops/s in the
latest local release run, current overhead is transport decode plus validation.
Future performance-sensitive work is template resolution, backing index
creation, timestamp mapping validation, metadata mutation, and ack rendering.

Current delete-data-stream reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-data-stream-reject-wire-benchmark
delete_data_stream_reject_request_encode iterations=400000 elapsed_ms=281.252 ops_per_second=1422212.44 nanos_per_op=703.13
delete_data_stream_reject_request_decode iterations=400000 elapsed_ms=245.206 ops_per_second=1631280.42 nanos_per_op=613.02
delete_data_stream_reject_validation iterations=400000 elapsed_ms=251.714 ops_per_second=1589108.03 nanos_per_op=629.28
delete_data_stream_ack_response_decode iterations=400000 elapsed_ms=54.800 ops_per_second=7299318.29 nanos_per_op=137.00
delete_data_stream_reject_wire_bottleneck_ops_per_second=1422212.44
```

The current delete-data-stream fail-closed boundary bottleneck is request
encode. The request path carries the cluster-manager envelope and data-stream
name array before rejecting execution. At roughly 1.42M ops/s in the latest
local release run, current overhead is still wire-codec dominated. Future
performance-sensitive work is name/wildcard resolution, snapshot-in-progress
protection, backing index deletion, metadata mutation, and ack rendering.

Current get-data-stream reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-data-stream-reject-wire-benchmark
get_data_stream_reject_request_encode iterations=400000 elapsed_ms=234.321 ops_per_second=1707063.45 nanos_per_op=585.80
get_data_stream_reject_request_decode iterations=400000 elapsed_ms=205.351 ops_per_second=1947881.97 nanos_per_op=513.38
get_data_stream_reject_validation iterations=400000 elapsed_ms=206.320 ops_per_second=1938732.74 nanos_per_op=515.80
get_data_stream_reject_wire_bottleneck_ops_per_second=1707063.45
```

The current get-data-stream fail-closed boundary bottleneck is request encode.
This path carries the ClusterManagerNodeRead envelope and default empty optional
data-stream name array before rejecting at admission. At roughly 1.71M ops/s in
the latest local release run, the boundary remains in the lightweight admin
transport range and does not expose a material wire-codec bottleneck.

Current data-streams-stats reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin data-streams-stats-reject-wire-benchmark
data_streams_stats_reject_request_encode iterations=400000 elapsed_ms=242.482 ops_per_second=1649607.33 nanos_per_op=606.20
data_streams_stats_reject_request_decode iterations=400000 elapsed_ms=237.477 ops_per_second=1684370.66 nanos_per_op=593.69
data_streams_stats_reject_validation iterations=400000 elapsed_ms=241.015 ops_per_second=1659648.46 nanos_per_op=602.54
data_streams_stats_reject_wire_bottleneck_ops_per_second=1649607.33
```

The current data-streams-stats fail-closed boundary bottleneck is request
encode. This path carries the BroadcastRequest parent task, empty name array,
and strict open forbid-closed index options before rejecting at admission. At
roughly 1.65M ops/s in the latest local release run, it stays in the lightweight
admin transport range and does not expose a material wire-codec bottleneck.

Current resolve-index reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin resolve-index-reject-wire-benchmark
resolve_index_reject_request_encode iterations=400000 elapsed_ms=224.325 ops_per_second=1783126.69 nanos_per_op=560.81
resolve_index_reject_request_decode iterations=400000 elapsed_ms=250.029 ops_per_second=1599811.71 nanos_per_op=625.07
resolve_index_reject_validation iterations=400000 elapsed_ms=251.138 ops_per_second=1592749.33 nanos_per_op=627.85
resolve_index_reject_wire_bottleneck_ops_per_second=1592749.33
```

The current resolve-index fail-closed boundary bottleneck is validation. This
path carries the ActionRequest parent task, wildcard name array, and strict open
index options before rejecting at admission. At roughly 1.57M ops/s in the
latest local release run, it stays in the lightweight metadata transport range;
the extra wildcard string and indices-options comparison make it slightly
heavier than the smallest BroadcastRequest reject paths.

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

Current list-view-names reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin list-view-names-reject-wire-benchmark
list_view_names_reject_request_encode iterations=400000 elapsed_ms=160.598 ops_per_second=2490685.92 nanos_per_op=401.50
list_view_names_reject_request_decode iterations=400000 elapsed_ms=147.617 ops_per_second=2709716.35 nanos_per_op=369.04
list_view_names_reject_validation iterations=400000 elapsed_ms=146.676 ops_per_second=2727105.92 nanos_per_op=366.69
list_view_names_response_decode iterations=400000 elapsed_ms=153.268 ops_per_second=2609799.81 nanos_per_op=383.17
list_view_names_reject_wire_bottleneck_ops_per_second=2490685.92
```

The current list-view-names fail-closed boundary bottleneck is request encode.
This path carries an empty request body before rejecting at admission and
decodes the `views` string list response. At roughly 2.49M ops/s in the latest
local release run, it is the lightest current view-admin boundary; future
performance-sensitive work is view-name listing and response rendering.

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

Current list-dangling-indices reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin list-dangling-indices-reject-wire-benchmark
list_dangling_indices_reject_request_encode iterations=400000 elapsed_ms=533.451 ops_per_second=749835.21 nanos_per_op=1333.63
list_dangling_indices_reject_request_decode iterations=400000 elapsed_ms=433.038 ops_per_second=923706.54 nanos_per_op=1082.59
list_dangling_indices_reject_validation iterations=400000 elapsed_ms=464.575 ops_per_second=861002.69 nanos_per_op=1161.44
list_dangling_indices_empty_response_decode iterations=400000 elapsed_ms=99.589 ops_per_second=4016510.67 nanos_per_op=248.97
list_dangling_indices_reject_wire_bottleneck_ops_per_second=749835.21
```

The current list-dangling-indices fail-closed boundary bottleneck is request
encode. This path carries the `BaseNodesRequest` envelope and optional index
UUID filter before rejecting at admission. At roughly 750K ops/s in the latest
local release run, future performance-sensitive work is BaseNodes fanout,
dangling index state scan, node aggregation, failure decoding, and response
rendering.

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

Current find-dangling-index reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin find-dangling-index-reject-wire-benchmark
find_dangling_index_reject_request_encode iterations=400000 elapsed_ms=340.891 ops_per_second=1173396.16 nanos_per_op=852.23
find_dangling_index_reject_request_decode iterations=400000 elapsed_ms=308.503 ops_per_second=1296585.65 nanos_per_op=771.26
find_dangling_index_reject_validation iterations=400000 elapsed_ms=305.887 ops_per_second=1307672.52 nanos_per_op=764.72
find_dangling_index_empty_response_decode iterations=400000 elapsed_ms=103.635 ops_per_second=3859692.57 nanos_per_op=259.09
find_dangling_index_reject_wire_bottleneck_ops_per_second=1173396.16
```

The current find-dangling-index fail-closed boundary bottleneck is request
encode. This path carries the `BaseNodesRequest` node filter, timeout, and
required index UUID before rejecting at admission. At roughly 1.17M ops/s in
the latest local release run, future performance-sensitive work is BaseNodes
fanout, dangling index state scan, node `IndexMetadata` aggregation, failures,
and response rendering.

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

Current clear-scroll reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin clear-scroll-reject-wire-benchmark
clear_scroll_reject_request_encode iterations=400000 elapsed_ms=275.865 ops_per_second=1449983.00 nanos_per_op=689.66
clear_scroll_reject_request_decode iterations=400000 elapsed_ms=258.081 ops_per_second=1549900.89 nanos_per_op=645.20
clear_scroll_reject_validation iterations=400000 elapsed_ms=260.069 ops_per_second=1538050.78 nanos_per_op=650.17
clear_scroll_reject_wire_bottleneck_ops_per_second=1449983.00
```

The current clear-scroll fail-closed boundary bottleneck is request encode. The
path carries only the ActionRequest parent task and scroll id array before
rejecting execution. At roughly 1.45M ops/s in the latest local release run,
the boundary itself is lightweight; the first performance point to inspect
before accepting execution is scroll context invalidation and clear-scroll
response rendering.

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

Current delete-PIT reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin delete-pit-reject-wire-benchmark
delete_pit_reject_request_encode iterations=400000 elapsed_ms=283.001 ops_per_second=1413423.68 nanos_per_op=707.50
delete_pit_reject_request_decode iterations=400000 elapsed_ms=291.271 ops_per_second=1373290.90 nanos_per_op=728.18
delete_pit_reject_validation iterations=400000 elapsed_ms=268.519 ops_per_second=1489655.16 nanos_per_op=671.30
delete_pit_reject_wire_bottleneck_ops_per_second=1373290.90
```

The current delete-PIT fail-closed boundary bottleneck is request decode. This
path carries only the ActionRequest parent task and PIT id array before
rejecting execution. At roughly 1.37M ops/s in the latest local release run,
the boundary itself is lightweight; the first performance point to inspect
before accepting execution is PIT context lookup/invalidation and delete-PIT
response rendering.

Current get-all-PITs reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-all-pits-reject-wire-benchmark
get_all_pits_reject_request_encode iterations=400000 elapsed_ms=239.247 ops_per_second=1671915.35 nanos_per_op=598.12
get_all_pits_reject_request_decode iterations=400000 elapsed_ms=224.108 ops_per_second=1784851.02 nanos_per_op=560.27
get_all_pits_reject_validation iterations=400000 elapsed_ms=226.532 ops_per_second=1765751.18 nanos_per_op=566.33
get_all_pits_reject_wire_bottleneck_ops_per_second=1671915.35
```

The current get-all-PITs fail-closed boundary bottleneck is request encode.
This path carries the ActionRequest parent task, nullable node id filters,
concrete-node presence marker, and optional timeout before rejecting execution.
At roughly 1.67M ops/s in the latest local release run, the boundary itself is
lightweight; the first performance point to inspect before accepting execution
is PIT context enumeration, node fanout, and `GetAllPitNodesResponse`
rendering.

Current create-PIT reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin create-pit-reject-wire-benchmark
create_pit_reject_request_encode iterations=400000 elapsed_ms=278.896 ops_per_second=1434226.27 nanos_per_op=697.24
create_pit_reject_request_decode iterations=400000 elapsed_ms=263.987 ops_per_second=1515226.35 nanos_per_op=659.97
create_pit_reject_validation iterations=400000 elapsed_ms=266.040 ops_per_second=1503533.19 nanos_per_op=665.10
create_pit_reject_wire_bottleneck_ops_per_second=1434226.27
```

The current create-PIT fail-closed boundary bottleneck is request encode. This
path carries the ActionRequest parent task, index target controls, keep-alive,
and optional partial-creation flag before rejecting execution. At roughly 1.43M
ops/s in the latest local release run, the boundary itself is lightweight; the
first performance point to inspect before accepting execution is PIT context
allocation, shard fanout, and create-PIT response rendering.

Current PIT-segments reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin pit-segments-reject-wire-benchmark
pit_segments_reject_request_encode iterations=400000 elapsed_ms=327.741 ops_per_second=1220477.70 nanos_per_op=819.35
pit_segments_reject_request_decode iterations=400000 elapsed_ms=307.983 ops_per_second=1298772.24 nanos_per_op=769.96
pit_segments_reject_validation iterations=400000 elapsed_ms=312.072 ops_per_second=1281756.75 nanos_per_op=780.18
pit_segments_reject_wire_bottleneck_ops_per_second=1220477.70
```

The current PIT-segments fail-closed boundary bottleneck is request encode.
This path carries the ActionRequest parent task, broadcast index controls,
nullable PIT id array, and verbose flag before rejecting execution. At roughly
1.22M ops/s in the latest local release run, the boundary itself is
lightweight; the first performance point to inspect before accepting execution
is PIT context lookup plus shard segment metadata response rendering.

Current indices-stats reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin indices-stats-reject-wire-benchmark
indices_stats_reject_request_encode ops_per_second=1615710.56 nanos_per_op=618.92
indices_stats_reject_request_decode ops_per_second=1581358.53 nanos_per_op=632.37
indices_stats_reject_validation ops_per_second=1530091.56 nanos_per_op=653.56
indices_stats_reject_wire_bottleneck_ops_per_second=1530091.56
```

The current indices-stats fail-closed boundary bottleneck is validation. This
path checks both indices options and the full `CommonStatsFlags` default shape
after decode, so it is slightly heavier than nodes-stats. At roughly 1.53M ops/s
in the latest local release run, it remains in the lightweight admin transport
range and does not introduce a source-materialization bottleneck.

Current list-tasks wire microbenchmark:

```text
cargo run -p os-transport --release --bin list-tasks-wire-benchmark
list_tasks_request_encode ops_per_second=1991760.42 nanos_per_op=502.07
list_tasks_response_encode ops_per_second=4572593.83 nanos_per_op=218.69
list_tasks_request_decode ops_per_second=1852258.41 nanos_per_op=539.88
list_tasks_response_decode ops_per_second=4290654.24 nanos_per_op=233.06
list_tasks_wire_bottleneck_ops_per_second=1852258.41
```

The current list-tasks wire bottleneck is request decode. The supported subset
is an empty task listing with only default filters, so the request path is
mostly frame/action validation plus task-id and empty-array decoding. At roughly
1.85M ops/s in the latest local release run, this adapter does not introduce a
transport-wire bottleneck.

Current cancel-tasks wire microbenchmark:

```text
cargo run -p os-transport --release --bin cancel-tasks-wire-benchmark
cancel_tasks_request_encode ops_per_second=1270672.41 nanos_per_op=786.98
cancel_tasks_response_encode ops_per_second=4551448.70 nanos_per_op=219.71
cancel_tasks_request_decode ops_per_second=1485477.46 nanos_per_op=673.18
cancel_tasks_response_decode ops_per_second=4250393.89 nanos_per_op=235.27
cancel_tasks_wire_bottleneck_ops_per_second=1270672.41
```

The current cancel-tasks wire bottleneck is request encode. Compared with
list-tasks, the default cancel request also writes the default reason string, so
the request body is slightly heavier. At roughly 1.27M ops/s in the latest local
release run, this adapter is still far above the source-materializing write/read
wire paths and does not introduce a new bottleneck.

Current get-task reject wire microbenchmark:

```text
cargo run -p os-transport --release --bin get-task-reject-wire-benchmark
get_task_reject_request_encode ops_per_second=1691104.07 nanos_per_op=591.33
get_task_reject_request_decode ops_per_second=1833500.78 nanos_per_op=545.40
get_task_reject_validation ops_per_second=1829225.54 nanos_per_op=546.68
get_task_reject_wire_bottleneck_ops_per_second=1691104.07
```

The current get-task fail-closed boundary bottleneck is request encode. The
validation path is effectively the same cost as decode plus a small unsupported
execution check, so the rejection boundary itself does not introduce a new
performance bottleneck. At roughly 1.69M ops/s in the latest local release run,
this path is in the same range as the other lightweight admin transport
adapters.

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

- `NodesInfoAction.INSTANCE`
- `NodesUsageAction.INSTANCE`
- `NodesHotThreadsAction.INSTANCE`
- `GetRepositoriesAction.INSTANCE`
- `GetMappingsAction.INSTANCE`
- `GetFieldMappingsAction.INSTANCE`
- `GetAliasesAction.INSTANCE`
- `GetSettingsAction.INSTANCE`
- `ClusterSearchShardsAction.INSTANCE`
- `RecoveryAction.INSTANCE`
- `IndicesSegmentsAction.INSTANCE`
- `IndicesShardStoresAction.INSTANCE`
- `GetDataStreamAction.INSTANCE`
- `DataStreamsStatsAction.INSTANCE`

These actions improve OpenSearch operator expectations and close obvious gaps in
index, metadata, and search-adjacent introspection, but they follow the Tier 1
gate.

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
