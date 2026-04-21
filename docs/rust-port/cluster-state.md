# Cluster-State Notes

## First Target

The first cluster-state target is decode-only compatibility with a single Java
OpenSearch node. Rust should be able to read and inspect state, not publish or
mutate it.

## Transport Entrypoint

The cluster-state transport action is:

```text
cluster:monitor/state
```

The default `ClusterStateRequest.writeTo` body layout is:

```text
TaskId parent task id
TimeValue clusterManagerNodeTimeout
boolean local
boolean routingTable
boolean nodes
boolean metadata
boolean blocks
boolean customs
String[] indices
IndicesOptions indicesOptions
TimeValue waitForTimeout
optional long waitForMetadataVersion
```

The Rust request builder currently targets the default Java request:

- empty parent task id
- `clusterManagerNodeTimeout = 30 SECONDS`
- `local = false`
- all five state sections enabled
- empty `indices`
- `IndicesOptions.lenientExpandOpen()`
- `waitForTimeout = 1 MINUTES`
- absent `waitForMetadataVersion`

`build_cluster_state_request_frame` wraps that request body with the normal
OpenSearch transport request frame:

```text
TcpHeader
ThreadContext headers
String[] features
String action = cluster:monitor/state
ClusterStateRequest body
```

The fixture suite compares Rust-generated full frame bytes against Java
`TcpHeader.writeHeader` plus `ClusterStateRequest.writeTo`.

For live probing, Rust uses `ClusterStateRequest::minimal_probe()`, which keeps
the same timeout and indices defaults but sets `routingTable`, `nodes`,
`metadata`, `blocks`, and `customs` to `false`. Java
`TransportClusterStateAction.buildResponse` only copies those sections into the
response builder when the corresponding request flag is true. With all five
flags false, the response should contain the state header plus empty routing,
nodes, blocks, and customs, and metadata limited to builder defaults such as
cluster UUID and coordination metadata.

The response is `ClusterStateResponse(StreamInput)`:

```text
ClusterName response cluster name
optional ClusterState
boolean waitForTimedOut
```

When the optional state is present, the full state starts with:

```text
ClusterName state cluster name
long state version
string state UUID
Metadata
RoutingTable
DiscoveryNodes
ClusterBlocks
VInt custom count
named writeable customs...
VInt minimumClusterManagerNodesOnPublishingClusterManager
```

The Rust crate currently exposes this as a prefix decoder so fixture generation
and transport plumbing can proceed before the full named writeable registry is
implemented.

## Current Decode Surface

`ClusterStateResponsePrefix` is the public decode result for this stage. The
name is deliberately conservative: it fully consumes the minimal Java response
fixture, but it is not a full cluster-state model yet.

For a response with no state, Rust reads the response cluster name, absent-state
flag, `waitForTimedOut`, and verifies there are no remaining bytes.

For a minimal response with state, Rust reads:

- response cluster name and optional-state flag
- state cluster name, version, and UUID
- metadata prefix through index metadata skeletons and the built-in empty
  `index-graveyard` custom
- routing table skeleton, including index name/UUID, shard-table count, shard
  ids, shard routing state, primary flag, current/relocating node ids, recovery
  source type, unassigned-info summary, allocation id, and expected shard size
- discovery nodes skeleton, including node id/name/address/roles; `os-tcp-probe`
  reports live node id/name/address/role count/attribute count summaries
- cluster blocks skeleton, including global and index-scoped block
  id/uuid/levels/status; `os-tcp-probe` reports live global and index block
  id/uuid/level/status summaries
- empty cluster-state custom count
- `minimumClusterManagerNodesOnPublishingClusterManager`
- final `waitForTimedOut`

The metadata prefix is:

```text
long metadata version
string cluster UUID
boolean cluster UUID committed
CoordinationMetadata
transient Settings
persistent Settings
DiffableStringMap hashesOfConsistentSettings
VInt index metadata count
IndexMetadata...
legacy templates
VInt metadata custom count
named writeable metadata customs...
```

Rust currently decodes the metadata header and the minimal skeleton forms of:

- `CoordinationMetadata`
- transient settings key/value skeletons
- persistent settings key/value skeletons
- `hashesOfConsistentSettings` key/value skeletons
- index metadata skeletons: index name, versions, routing shard count, state id,
  settings count, `index.uuid`, `index.number_of_shards`,
  `index.number_of_replicas`, mapping type/compressed payload length/routing flag,
  alias names/routing flags, custom data key/value skeletons, rollover alias/time
  with `max_docs`, `max_age`, and `max_size` met-condition skeletons, in-sync
  allocation-id sets, optional ingestion status, split-shard root count, and
  split-shard parent-to-child range skeletons, and primary-term map count;
  `os-tcp-probe` reports live index name/UUID/routing shard count/primary shard
  count/replica count/settings count/mapping count/alias count summaries
- legacy index template skeletons: name, order, patterns, settings count,
  mapping names/compressed payload lengths, alias names/routing flags, and
  optional version; `os-tcp-probe` reports live template
  name/pattern/settings count/mapping count/alias count summaries
- the built-in `index-graveyard` metadata custom, including tombstone index
  name/UUID/delete timestamp skeletons; `os-tcp-probe` reports live tombstone
  index name/UUID/delete timestamp summaries
- `component_template` metadata custom skeletons, including component name,
  template settings, optional mapping payload length, aliases, version, and
  metadata map key/value skeletons; `os-tcp-probe` reports live component
  template name/version/settings count/mapping count/alias count summaries
- `index_template` composable template metadata custom skeletons, including
  template name, index patterns, optional template settings, mapping compressed
  payload length, alias names/routing flags, composed-of component template
  names, priority/version, metadata map key/value skeletons, data stream
  timestamp field, and context name/version/params skeletons; `os-tcp-probe`
  reports live composable template name/index pattern/component/settings
  count/mapping count/alias count summaries
- `data_stream` metadata custom skeletons, including data stream name,
  timestamp field, backing index name/UUID list, and generation; `os-tcp-probe`
  reports live name/timestamp/backing index count/backing index
  name/generation summaries
- `ingest` metadata custom skeletons, including pipeline id, raw config byte
  length, and media type
- `search_pipeline` metadata custom skeletons, including pipeline id, raw
  config byte length, and media type
- `stored_scripts` metadata custom skeletons, including script id, language,
  source length, and options count
- `persistent_tasks` metadata custom skeletons, including task id/allocation,
  task name, params writeable name, known fixture params marker/generation,
  optional state writeable name, known fixture state marker/generation,
  assignment, and optional last-status allocation id
- `decommissionedAttribute` metadata custom skeleton, including awareness
  attribute name/value, decommission status, and request id
- `repositories` metadata custom skeletons, including repository name/type,
  settings, generation, pending generation, and crypto metadata provider
  name/type/settings, preserving repository list order; coverage includes
  multi-entry repositories with multiple settings per repository, and
  `os-tcp-probe` reports live repository name/type/settings
  count/generation/pending generation/crypto provider summaries
- `weighted_shard_routing` metadata custom skeletons, including awareness
  attribute, weight key/value entries, and weighted routing version
- `view` metadata custom skeletons, including view name/description,
  created/modified timestamps, and target index patterns
- `queryGroups` workload group metadata custom skeletons, including workload
  group name/id, resource limits, resiliency mode, search settings, and update
  timestamp; coverage includes multi-entry workload groups with multiple
  resource limits and serialized search settings when present in the stream,
  and `os-tcp-probe` reports live name/id/resource/search count/resiliency
  summaries
- routing table skeleton, including index name/UUID, shard ids, unassigned,
  unassigned replica, initializing, started, and relocating shard state, primary flag,
  current/relocating node ids, recovery source type, unassigned-info summary,
  allocation id, and expected shard size; `os-tcp-probe` reports live shard
  id/state/primary/current node/allocation id summaries
- discovery nodes skeleton, including node id/name/address/roles; `os-tcp-probe`
  reports live node id/name/address/role count/attribute count summaries
- cluster blocks skeleton, including global and index-scoped block
  id/uuid/levels/status; `os-tcp-probe` reports live global and index block
  id/uuid/level/status summaries
- zero cluster-state customs
- `minimumClusterManagerNodesOnPublishingClusterManager`
- final `waitForTimedOut` response flag

Unsupported cluster-state or metadata customs still fail closed until each
section has a typed decoder.

## Fixture Coverage

Java cluster-state response fixtures currently cover:

- minimal state and filtered-state response prefix behavior
- discovery nodes, global blocks, and index-scoped blocks
- index routing table and shard routing states: unassigned, initializing,
  started, relocating, and primary plus replica entries
- metadata settings and consistent setting hashes
- index metadata settings, mappings, aliases, custom data, rollover info and
  conditions, split-shards metadata, and index graveyard tombstones
- legacy index templates, component templates, composable index templates, data
  stream metadata, repositories including crypto metadata, weighted routing,
  view metadata, and workload group metadata
- mixed metadata fixtures for legacy/component/composable templates, data
  stream plus composable data stream templates, and miscellaneous custom
  metadata combinations
- mixed repository/workload group fixture coverage with multiple repository
  settings, multiple workload group resource limits, and workload group search
  settings when serialized by the stream version
- top-level cluster-state custom fixtures:
  `cluster_state_response_repository_cleanup_custom`,
  `cluster_state_response_snapshot_deletions_custom`,
  `cluster_state_response_restore_custom`, and
  `cluster_state_response_snapshots_custom`
- live compatibility probe procedure for mixed metadata/top-level custom
  payloads via `os-tcp-probe --cluster-state`

The current custom metadata registry supports:

```text
ingest
search_pipeline
stored_scripts
persistent_tasks
decommissionedAttribute
index-graveyard
component_template
index_template
data_stream
repositories
weighted_shard_routing
view
queryGroups
```

OpenSearch `ClusterModule` registers these built-in metadata custom names:

```text
repositories
ingest
search_pipeline
stored_scripts
persistent_tasks
index-graveyard
component_template
index_template
data_stream
view
weighted_shard_routing
decommissionedAttribute
queryGroups
```

The current top-level cluster-state custom registry supports the complete
`ClusterModule` built-in set:

```text
snapshots
restore
snapshot_deletions
repository_cleanup
```

Bundled module/plugin re-scan status:

- `ClusterModule.getNamedWriteables()` remains the only production source for
  `Metadata.Custom` and `ClusterState.Custom` named writeable registrations
  found under `server/src/main/java`
- bundled modules and plugins with `getNamedWriteables()` register request,
  response, search, analysis, or evaluation types, but no additional
  `Metadata.Custom` or `ClusterState.Custom` categories
- `workload-management` persists `queryGroups` through the built-in
  `WorkloadGroupMetadata` registration in `ClusterModule`
- the local `persistent-task-live-fixture` plugin registers persistent task
  params/state categories only; the enclosing `persistent_tasks` metadata custom
  remains the built-in OpenSearch registration

Observed live runs currently cover default cluster metadata customs
(`index-graveyard`, `repositories`, `data_stream`), REST-produced pipeline,
script, and template metadata (`ingest`, `search_pipeline`, `stored_scripts`,
`component_template`, `index_template`), and the selected workload-management
path (`queryGroups`). The OpenSearch built-in metadata custom registration set
is now covered by `METADATA_CUSTOM_DISPATCH`.

Unsupported custom metadata names deliberately return
`UnsupportedNamedWriteable`. Sections that still intentionally reject
non-trivial payloads include repository crypto forms beyond the current
provider/settings skeleton, plugin-provided cluster-state customs that have not
been added to the registry, and snapshot user metadata values outside the
current scalar/numeric/date/binary/list/array/map subset.

Current compatibility gaps after the recovery source and top-level custom work:

- recovery sources: `empty_store`, `existing_store`, `peer`, `snapshot`,
  `local_shards`, `remote_store`, and `in_place_split_shard` are recognized;
  payload-bearing variants are decoded as skeletons
- unassigned info: reason/time/message/allocation-status fields and embedded
  failure exception summaries are read
- rollover conditions: OpenSearch currently registers `max_docs`, `max_age`,
  and `max_size`, and all three are decoded
- cluster-state customs: `repository_cleanup`, `snapshot_deletions`,
  `restore`, and `snapshots` are decoded as skeletons
- metadata customs: built-in OpenSearch registrations are decoded as skeletons;
  live coverage includes operational paths for repositories, workload groups,
  pipeline/script metadata, template metadata, decommission metadata, and
  non-empty `persistent_tasks`
- generic metadata maps: null map markers are consumed as empty maps for both
  generic user metadata and string-key metadata maps observed in live composable
  template payloads

Top-level cluster-state custom candidates registered by `ClusterModule`:

```text
snapshots
restore
snapshot_deletions
repository_cleanup
```

`repository_cleanup` is decoded as a skeleton: its payload is a list of entries,
each with repository name and repository state id. `snapshot_deletions` is also
decoded as a skeleton: repository name, snapshot ids, start time, repository
state id, deletion state, and delete uuid. `restore` is decoded as a skeleton:
restore uuid, snapshot, state, index names, and shard status map entries with
shard id, restoring node id, shard state, and failure reason. `snapshots` is
decoded as a skeleton: snapshot, flags, indices, start time, shard status map
entries with shard id, node id, state, generation, and reason, repository state
id, data streams, source snapshot, clone map entries with repository index id,
shard id, node id, state, generation, and reason, scalar user metadata values
(`null`, string, int, long, boolean), numeric/date/binary values (byte, short,
float bits, double bits, date millis, byte arrays), nested lists, object arrays,
and maps, and remote-store flags.

`os-tcp-probe` reports representative identity summaries for those top-level
customs: repository cleanup repository/state ids, snapshot deletion uuid,
repository, snapshot count and state ids, restore uuid/repository/snapshot/state
and shard status counts, and snapshot name/repository/uuid/state and shard
status counts.

Next implementation candidates, in priority order:

- when refreshing live transcripts, prefer the current canonical summary key set
  from `wire-protocol.md` over older historical snippets
- expand live coverage for additional plugin-provided cluster-state customs as
  they are added to the dispatch table
- keep `os-tcp-probe` live summaries aligned with newly decoded metadata entity
  identifiers as future skeleton decoders become more detailed

## Important Concepts

- cluster state version
- state UUID
- metadata
- routing table
- discovery nodes
- cluster blocks
- customs
- feature-aware serialization

## Named Diff Compatibility

OpenSearch publication transport does not always send a full cluster state. In
`PublicationTransportHandler`, the compressed publication payload starts with a
boolean discriminator: `true` means a full `ClusterState.writeTo` body follows,
and `false` means a `ClusterStateDiff.writeTo` body follows. Diff publication is
used when the destination node existed in the previous state and persistence is
not blocked; otherwise the full state is sent.

`ClusterStateDiff` serializes:

- cluster name
- source state UUID
- target state UUID
- target version
- routing table diff
- discovery nodes diff, written through the node attribute-aware path
- metadata diff
- cluster blocks diff
- top-level custom map diff
- `minimumClusterManagerNodesOnPublishingClusterManager`

Map diffs use the `DiffableUtils.MapDiff` envelope: deleted keys, incremental
diff entries, then upsert/full replacement entries. Named custom diffs use
`NamedDiffableValueSerializer`, which reads incremental entries via
`readNamedWriteable(NamedDiff.class, key)` and upserts via
`readNamedWriteable(custom_class, key)`. `ClusterModule` registers named diff
readers for the top-level cluster-state customs (`snapshots`, `restore`,
`snapshot_deletions`, `repository_cleanup`) and the metadata customs already
tracked by the full-state decoder.

Rust now has a prefix scaffold for publication diffs:

- `read_publication_cluster_state_diff_header_prefix` reads the full/diff
  discriminator and the `ClusterStateDiff` header (`clusterName`, source UUID,
  target UUID, target version), then reports remaining bytes without applying
  the diff.
- `read_string_map_diff_envelope_prefix` reads delete-only string-key
  `DiffableUtils.MapDiff` envelopes and reports deleted keys/counts.
- `read_publication_cluster_state_diff_prefix` reads an empty/prefix-only
  publication diff through routing table version, discovery nodes complete-diff
  flag, routing index upsert skeletons, metadata header, section envelopes,
  metadata index/template upsert skeletons, repositories metadata custom upsert
  skeletons, cluster blocks complete-diff flag, top-level `repository_cleanup`,
  `restore`, `snapshot_deletions`, and `snapshots` custom upsert skeletons, and
  the final minimum cluster manager node count.

The scaffold deliberately fails closed on:

- a full-state publication body passed to the diff header reader
- an unsupported map key serializer or malformed map diff count
- non-empty named diff entries until their payload decoder exists
- non-empty upsert entries outside the routing index, metadata index, metadata
  template, repositories metadata custom, and top-level
  `repository_cleanup`/`restore`/`snapshot_deletions`/`snapshots` custom maps
  until their full value decoder exists
- complete-diff replacement payloads for discovery nodes or cluster blocks
- a diff body that cannot be fully consumed by a future section decoder
- a target UUID that cannot be applied to the caller's base state

The next implementation should decode non-empty delete-only map diffs for
metadata/routing/custom sections from Java fixtures, then add named diff/upsert
payload support one custom type at a time. Applying diffs safely should wait
until full-state decode is complete for the corresponding sections.

Java fixture coverage now includes:

- `cluster_state_publication_diff_empty`, an OpenSearch-produced empty
  publication diff between two state UUIDs
- `cluster_state_publication_diff_delete_custom`, an OpenSearch-produced
  delete-only top-level custom map diff that removes `snapshots`
- `cluster_state_publication_diff_delete_routing_index`, an
  OpenSearch-produced delete-only routing table map diff that removes
  `fixture-deleted-routing-index`
- `cluster_state_publication_diff_delete_metadata_index`, an
  OpenSearch-produced delete-only metadata index map diff that removes
  `fixture-deleted-metadata-index`
- `cluster_state_publication_diff_delete_metadata_template`, an
  OpenSearch-produced delete-only legacy template map diff that removes
  `fixture-deleted-template`
- `cluster_state_publication_diff_delete_metadata_custom`, an
  OpenSearch-produced delete-only metadata custom map diff that removes
  `repositories`
- `cluster_state_publication_diff_delete_consistent_setting_hash`, an
  OpenSearch-produced delete-only `hashesOfConsistentSettings` diff that
  removes `fixture.secure.setting`
- `cluster_state_publication_diff_upsert_metadata_index`, an
  OpenSearch-produced metadata index upsert diff decoded through the existing
  `IndexMetadata` prefix reader
- `cluster_state_publication_diff_named_metadata_index`, an
  OpenSearch-produced metadata index diff decoded through the scalar/settings
  header while nested map diffs are empty
- `cluster_state_publication_diff_named_metadata_index_mapping`, an
  OpenSearch-produced metadata index diff with a nested mapping diff decoded
  through the default `AbstractDiffable` boolean and the existing
  `IndexMapping` prefix reader
- `cluster_state_publication_diff_named_metadata_index_alias`, an
  OpenSearch-produced metadata index diff with a nested alias diff decoded
  through the default `AbstractDiffable` boolean and the existing
  `TemplateAlias` prefix reader
- `cluster_state_publication_diff_named_metadata_index_custom_data`, an
  OpenSearch-produced metadata index diff with a nested custom data diff
  decoded through the `DiffableStringMapDiff` delete/upsert payload
- `cluster_state_publication_diff_named_metadata_index_rollover`, an
  OpenSearch-produced metadata index diff with a nested rollover info diff
  decoded through the default `AbstractDiffable` boolean and the existing
  `IndexRolloverInfo` prefix reader
- `cluster_state_publication_diff_named_metadata_index_in_sync`, an
  OpenSearch-produced metadata index diff with a nested in-sync allocation ids
  diff that verifies the decoder fails closed before consuming unsupported
  shard-id keyed string-set diff payloads
- `cluster_state_publication_diff_named_metadata_index_split_shards`, an
  OpenSearch-produced metadata index diff with a `SplitShardsMetadata`
  replacement decoded through the default `AbstractDiffable` boolean and the
  existing split-shards prefix reader
- `cluster_state_publication_diff_upsert_routing_index`, an
  OpenSearch-produced routing index upsert diff decoded through the existing
  `IndexRoutingTable` prefix reader
- `cluster_state_publication_diff_named_routing_index`, an
  OpenSearch-produced routing index complete diff decoded through the default
  `AbstractDiffable` boolean and the existing `IndexRoutingTable` prefix reader
- `cluster_state_publication_diff_upsert_metadata_template`, an
  OpenSearch-produced metadata template upsert diff decoded through the
  existing legacy template prefix reader
- `cluster_state_publication_diff_named_metadata_template`, an
  OpenSearch-produced metadata template named diff decoded through the default
  `AbstractDiffable` boolean and existing legacy template prefix reader
- `cluster_state_publication_diff_named_metadata_template_mapping_alias`, an
  OpenSearch-produced metadata template named diff whose replacement includes
  mapping compressed x-content and an alias entry
- `cluster_state_publication_diff_upsert_metadata_custom`, an
  OpenSearch-produced `repositories` metadata custom upsert diff decoded
  through the existing repositories metadata prefix reader
- `cluster_state_publication_diff_named_metadata_custom_repositories`, an
  OpenSearch-produced `repositories` metadata custom named diff decoded through
  the default `CompleteNamedDiff` boolean and existing repository metadata
  prefix reader
- `cluster_state_publication_diff_upsert_metadata_custom_component_template`,
  an OpenSearch-produced `component_template` metadata custom upsert diff
  decoded through the existing component template prefix reader
- `cluster_state_publication_diff_upsert_metadata_custom_index_template`, an
  OpenSearch-produced `index_template` composable metadata custom upsert diff
  decoded through the existing composable index template prefix reader
- `cluster_state_publication_diff_upsert_metadata_custom_data_stream`, an
  OpenSearch-produced `data_stream` metadata custom upsert diff decoded through
  the existing data stream prefix reader
- `cluster_state_publication_diff_upsert_metadata_custom_ingest`, an
  OpenSearch-produced `ingest` metadata custom upsert diff decoded through the
  existing ingest pipeline prefix reader
- `cluster_state_publication_diff_upsert_metadata_custom_search_pipeline`, an
  OpenSearch-produced `search_pipeline` metadata custom upsert diff decoded
  through the existing search pipeline prefix reader
- `cluster_state_publication_diff_upsert_metadata_custom_stored_scripts`, an
  OpenSearch-produced `stored_scripts` metadata custom upsert diff decoded
  through the existing stored script prefix reader
- `cluster_state_publication_diff_upsert_metadata_custom_index_graveyard`, an
  OpenSearch-produced `index-graveyard` metadata custom upsert diff decoded
  through the existing index graveyard tombstone prefix reader
- `cluster_state_publication_diff_upsert_metadata_custom_persistent_tasks`, an
  OpenSearch-produced `persistent_tasks` metadata custom upsert diff decoded
  through the existing persistent task prefix reader, including fixture named
  params and state payloads
- `cluster_state_publication_diff_upsert_metadata_custom_decommission`, an
  OpenSearch-produced `decommissionedAttribute` metadata custom upsert diff
  decoded through the existing decommission attribute prefix reader
- `cluster_state_publication_diff_named_metadata_custom_decommission`, an
  OpenSearch-produced `decommissionedAttribute` metadata custom named diff
  decoded through the default `CompleteNamedDiff` boolean and existing
  decommission attribute prefix reader
- `cluster_state_publication_diff_upsert_metadata_custom_weighted_routing`, an
  OpenSearch-produced `weighted_shard_routing` metadata custom upsert diff
  decoded through the existing weighted routing prefix reader
- `cluster_state_publication_diff_named_metadata_custom_weighted_routing`, an
  OpenSearch-produced `weighted_shard_routing` metadata custom named diff
  decoded through the default `CompleteNamedDiff` boolean and existing weighted
  routing prefix reader
- `cluster_state_publication_diff_upsert_metadata_custom_view`, an
  OpenSearch-produced `view` metadata custom upsert diff decoded through the
  existing view metadata prefix reader
- `cluster_state_publication_diff_upsert_metadata_custom_workload_group`, an
  OpenSearch-produced `queryGroups` metadata custom upsert diff decoded
  through the existing workload group prefix reader
- `cluster_state_publication_diff_named_metadata_custom_view`, an
  OpenSearch-produced `view` metadata custom named diff decoded through the
  nested view map diff and existing view prefix reader
- `cluster_state_publication_diff_named_metadata_custom_workload_group`, an
  OpenSearch-produced `queryGroups` metadata custom named diff decoded through
  the nested workload group map diff and existing workload group prefix reader
- `cluster_state_publication_diff_named_metadata_custom_data_stream`, an
  OpenSearch-produced `data_stream` metadata custom named diff decoded through
  the nested data stream map diff and existing data stream prefix reader
- `cluster_state_publication_diff_named_metadata_custom_component_template`, an
  OpenSearch-produced `component_template` metadata custom named diff decoded
  through the nested component template map diff and component template value
  prefix reader
- `cluster_state_publication_diff_named_metadata_custom_index_template`, an
  OpenSearch-produced `index_template` composable metadata custom named diff
  decoded through the nested composable template map diff and composable
  template value prefix reader
- `cluster_state_publication_diff_upsert_custom`, an OpenSearch-produced
  top-level empty `snapshots` custom upsert diff decoded through the existing
  `SnapshotsInProgress` prefix reader
- `cluster_state_publication_diff_upsert_custom_snapshots_entry`, an
  OpenSearch-produced top-level `snapshots` custom upsert diff with one
  in-progress snapshot entry decoded through the same prefix reader
- `cluster_state_publication_diff_upsert_custom_restore`, an OpenSearch-produced
  top-level `restore` custom upsert diff decoded through the existing
  `RestoreInProgress` prefix reader
- `cluster_state_publication_diff_upsert_custom_restore_shard_status`, an
  OpenSearch-produced top-level `restore` custom upsert diff with one shard
  status decoded through the same prefix reader
- `cluster_state_publication_diff_named_custom_restore_shard_status`, an
  OpenSearch-produced top-level `restore` named diff decoded through the
  existing `RestoreInProgress` prefix reader after the `CompleteNamedDiff`
  replacement boolean, including an entry shard-status map
- `cluster_state_publication_diff_upsert_custom_snapshot_deletions`, an
  OpenSearch-produced top-level `snapshot_deletions` custom upsert diff decoded
  through the existing `SnapshotDeletionsInProgress` prefix reader
- `cluster_state_publication_diff_named_custom_snapshot_deletions`, an
  OpenSearch-produced top-level `snapshot_deletions` named diff decoded through
  the existing `SnapshotDeletionsInProgress` prefix reader after the
  `CompleteNamedDiff` replacement boolean, including a changed snapshot-id
  collection and repository state id
- `cluster_state_publication_diff_upsert_custom_repository_cleanup`, an
  OpenSearch-produced top-level `repository_cleanup` custom upsert diff decoded
  through the existing `RepositoryCleanupInProgress` prefix reader
- `cluster_state_publication_diff_named_custom_repository_cleanup`, an
  OpenSearch-produced top-level `repository_cleanup` named diff decoded through
  the existing `RepositoryCleanupInProgress` prefix reader when the
  `CompleteNamedDiff` replacement boolean is `true`

`component_template` metadata custom upsert layout has been checked against
OpenSearch `ComponentTemplateMetadata.writeTo`. The custom payload writes a
map count, then each component template name string and `ComponentTemplate`
value. The value is `Template.writeTo`, optional version, and optional
metadata map. That matches the existing full-state
`read_component_template_prefix` path. The publication diff metadata custom
upsert branch now accepts the `component_template` key, consumes that map, and
records the decoded component template skeletons alongside the upsert keys.

`index_template` composable metadata custom upsert layout has also been
checked against OpenSearch `ComposableIndexTemplateMetadata.writeTo`. It uses
the same metadata custom map shape: map count, template name string, and
`ComposableIndexTemplate.writeTo` value. The value order matches the existing
full-state `read_composable_index_template_prefix` path for the current
OpenSearch wire version: index patterns, optional template, optional composed
component names, optional priority/version, metadata map, optional data-stream
template, and optional context. The publication diff metadata custom upsert
branch now accepts the `index_template` key, consumes that map, and records the
decoded composable index template skeletons alongside the upsert keys.

`data_stream` metadata custom upsert layout has been checked against OpenSearch
`DataStreamMetadata.writeTo`. It uses the same metadata custom map shape: map
count, data-stream key string, and `DataStream.writeTo` value. The value writes
the data-stream name, timestamp field string, backing `Index` list, and
generation. That matches the existing full-state `read_data_stream_prefix` path.
The publication diff metadata custom upsert branch now accepts the
`data_stream` key, consumes that map, and records decoded data stream skeletons
alongside the upsert keys.

`ingest` metadata custom upsert layout has been checked against OpenSearch
`IngestMetadata.writeTo`. Unlike the map-backed customs above, the payload
writes only the pipeline count followed by each `PipelineConfiguration.writeTo`
value; it does not write the map key separately because the pipeline id is
inside each value. The existing full-state `read_ingest_pipeline_prefix` path
already matches that layout for the current OpenSearch wire version: pipeline
id, bytes reference config, and media type. The publication diff metadata
custom upsert branch now accepts the `ingest` key, consumes the pipeline list,
and records decoded ingest pipeline skeletons alongside the upsert keys.

`search_pipeline` metadata custom upsert layout has been checked against
OpenSearch `SearchPipelineMetadata.writeTo`. It follows the same shape as
`ingest`: pipeline count followed by each search pipeline
`PipelineConfiguration.writeTo` value, with no separate map key. The existing
full-state `read_search_pipeline_prefix` path already matches that value layout
for the current OpenSearch wire version: pipeline id, bytes reference config,
and media type. The publication diff metadata custom upsert branch now accepts
the `search_pipeline` key, consumes the pipeline list, and records decoded
search pipeline skeletons alongside the upsert keys.

`stored_scripts` metadata custom upsert layout has been checked against
OpenSearch `ScriptMetadata.writeTo`. The payload writes a script count, then
each script id string followed by `StoredScriptSource.writeTo`. The value
writes language, source, and options map. That matches the existing full-state
`read_stored_script_prefix` path. The publication diff metadata custom upsert
branch now accepts the `stored_scripts` key, consumes the script list, and
records decoded stored script skeletons alongside the upsert keys.

`index-graveyard` metadata custom upsert layout has been checked against
OpenSearch `IndexGraveyard.writeTo`. The payload writes a tombstone list; each
tombstone writes `Index.writeTo` followed by the delete timestamp as a fixed
long. That matches the existing full-state
`read_index_graveyard_tombstone_prefix` path. Because OpenSearch metadata
builders initialize an empty index graveyard by default, the upsert fixture
explicitly removes the custom from the before-state before adding the non-empty
graveyard in the after-state. The publication diff metadata custom upsert
branch now accepts the `index-graveyard` key, consumes the tombstone list, and
records decoded tombstone skeletons alongside the upsert keys.

`persistent_tasks` metadata custom upsert layout has been checked against
OpenSearch `PersistentTasksCustomMetadata.writeTo`. The payload writes
`lastAllocationId` as a fixed long, then a map keyed by task id; each value is
`PersistentTask.writeTo`, including task id, allocation id, task name, named
params, optional named state, assignment, and optional last-status allocation
id. That matches the existing full-state persistent task reader, including the
fixture-specific named params/state payloads. The publication diff metadata
custom upsert branch now accepts the `persistent_tasks` key, consumes the
task-id keyed map, and records decoded persistent task skeletons alongside the
upsert keys.

`decommissionedAttribute` metadata custom upsert layout has been checked
against OpenSearch `DecommissionAttributeMetadata.writeTo`. The payload writes
`DecommissionAttribute.writeTo` first, i.e. attribute name and value strings,
then the decommission status string and request id string. That matches the
existing full-state `read_decommission_attribute_metadata_prefix` path. The
publication diff metadata custom upsert branch now accepts the
`decommissionedAttribute` key, consumes the decommission payload, and records
decoded decommission skeletons alongside the upsert keys.

`weighted_shard_routing` metadata custom upsert layout has been checked against
OpenSearch `WeightedRoutingMetadata.writeTo`. The payload writes
`WeightedRouting.writeTo` first, i.e. awareness attribute string and generic
weights map, then the weighted-routing version as a fixed long. That matches
the existing full-state `read_weighted_routing_metadata_prefix` path. The
publication diff metadata custom upsert branch now accepts the
`weighted_shard_routing` key, consumes the weighted routing payload, and
records decoded weighted routing skeletons alongside the upsert keys.

`view` metadata custom upsert layout has been checked against OpenSearch
`ViewMetadata.writeTo`. The payload writes a map count, then each view key
string and `View.writeTo` value. The value order is view name, optional
description, created-at zlong, modified-at zlong, and a target list where each
target writes its index pattern string. That matches the existing full-state
`read_view_metadata_prefix` path. The publication diff metadata custom upsert
branch now accepts the `view` key, consumes that map, and records decoded view
skeletons alongside the upsert keys.

`queryGroups` workload group metadata custom upsert layout has been checked
against OpenSearch `WorkloadGroupMetadata.writeTo`. The payload writes a map
count, then each workload group id key string and `WorkloadGroup.writeTo`
value. The value writes workload group name, id, `MutableWorkloadGroupFragment`
payload, and updated-at fixed long. The fragment payload writes an optional
resource-limits map marker and map, optional resiliency mode string, and for
wire versions on or after 3.6.0 a search-settings null marker followed by a
string map when present. That matches the existing full-state
`read_workload_group_prefix` path. The publication diff metadata custom upsert
branch now accepts the `queryGroups` key, consumes that map, and records
decoded workload group skeletons alongside the upsert keys.

Top-level custom named-diff layout has been checked against OpenSearch
`RepositoryCleanupInProgress` and `AbstractNamedDiffable`. `RepositoryCleanupInProgress`
inherits the default `AbstractNamedDiffable.diff` behavior, so a changed custom
is serialized as a `CompleteNamedDiff`. In a `DiffableUtils.MapDiff`, the
top-level custom map writes the string key first, then
`NamedDiffableValueSerializer.readDiff/writeDiff` uses that key as the named
writeable name. The `CompleteNamedDiff` payload itself is a boolean: `true`
means the full custom value follows using the same `writeTo` layout as an
upsert, while `false` means no replacement payload and applying the diff keeps
the previous value. For `repository_cleanup`, this makes prefix decoding safe:
read the key, read the boolean, and when it is `true`, reuse the existing
`RepositoryCleanupInProgress` prefix reader.

Metadata custom named-diff layout uses the same outer `DiffableUtils.MapDiff`
shape as metadata custom upserts: delete keys first, then diff entries, then
upsert entries. For each diff entry, `Metadata.CUSTOM_VALUE_SERIALIZER` writes
only the string key and then calls `NamedDiffableValueSerializer.writeDiff`.
There is no extra diff type tag in the stream; the key is the named writeable
name used by `StreamInput.readNamedWriteable(NamedDiff.class, key)`. That
means Rust must dispatch metadata custom diff payloads by the outer custom key.
Customs that inherit the default `AbstractNamedDiffable` diff, such as
`repositories`, `weighted_shard_routing`, and `decommissionedAttribute`, encode
a `CompleteNamedDiff` boolean followed by the full custom payload when the
boolean is `true`. Map-backed customs with their own `readDiffFrom`, such as
`view`, `queryGroups`, `data_stream`, `component_template`, and
`index_template`, encode a nested string-keyed map diff directly after the
outer custom key. The first implementation step should use a map-backed custom
with a small fixture, because it exercises custom-specific nested map diff
decoding without adding full replacement semantics at the same time.
After the map-backed metadata custom coverage, `weighted_shard_routing` and
`decommissionedAttribute` now validate the metadata custom `CompleteNamedDiff`
path: both inherit `AbstractNamedDiffable`, the diff payload starts with a
replacement boolean, and the full payload is decoded by the matching full-state
metadata custom reader. `repositories` is also a default complete-named-diff
candidate with an existing full payload reader. `RepositoriesMetadata.writeTo`
writes only a repository list, and each entry uses the same
`RepositoryMetadata.writeTo` layout already consumed by
`read_repository_metadata_prefix`, including version-gated crypto metadata.
The repositories named-diff fixture stays non-crypto and focuses on the
complete-named-diff boolean plus list replacement; crypto is already covered by
full-state repository fixtures and can be added later if needed.
Top-level custom complete-named-diff candidates are `restore`,
`snapshot_deletions`, and `snapshots`, because `repository_cleanup` already has
named diff fixture coverage and all four inherit `AbstractNamedDiffable`.
`restore` is the next implementation candidate: `RestoreInProgress` inherits
`AbstractNamedDiffable`, its `readDiffFrom` delegates to
`readDiffFrom(Custom.class, TYPE, in)`, and the diff payload is the default
`CompleteNamedDiff` boolean followed by `RestoreInProgress.writeTo` when a
replacement is present. The existing Rust `read_restore_in_progress_prefix`
reader can be reused directly after that boolean because it already handles the
entry list and shard-status map. The focused fixture should change an existing
`restore` custom from a basic entry to a shard-status entry so the named diff
exercises the richer replacement payload instead of only an empty or count-only
case.
That restore fixture is now implemented and validates the first top-level
custom complete-named-diff candidate after `repository_cleanup`. The remaining
top-level complete-named-diff candidates are `snapshot_deletions` and
`snapshots`, in that order.
`snapshot_deletions` is the next candidate: `SnapshotDeletionsInProgress`
inherits `AbstractNamedDiffable`, its `readDiffFrom` delegates to
`readDiffFrom(Custom.class, TYPE, in)`, and the replacement payload is the
default `CompleteNamedDiff` boolean followed by `SnapshotDeletionsInProgress`
`writeTo`. That full payload is a list of deletion entries; each entry writes
repository name, snapshot-id collection, start time as vlong, repository state
id as long, state byte, and deletion UUID string. The existing Rust
`read_snapshot_deletions_in_progress_prefix` reader already consumes that
layout, so it can be reused directly after the replacement boolean. The focused
fixture should keep a single deletion entry and change the snapshot-id list or
repository state id through the existing entry helpers, because that covers the
entry payload while avoiding an unrelated multi-entry repository-concurrency
case.
That snapshot-deletions fixture is now implemented with a single deletion entry
whose replacement adds a second snapshot id and changes the repository state
id. The only remaining top-level complete-named-diff candidate in the current
sequence is `snapshots`.
`snapshots` is the final top-level complete-named-diff candidate in this
sequence: `SnapshotsInProgress` inherits `AbstractNamedDiffable`, its
`readDiffFrom` delegates to `readDiffFrom(Custom.class, TYPE, in)`, and the
replacement payload is the default `CompleteNamedDiff` boolean followed by
`SnapshotsInProgress.writeTo`. That payload writes an entry list; each entry
contains `Snapshot`, include-global-state and partial booleans, state byte,
snapshot `IndexId` list, start time, shard-status map, repository state id,
optional failure, generic user metadata map, version, data streams, optional
source snapshot id, clone map, and remote-store booleans on current stream
versions. The existing Rust `read_snapshots_in_progress_prefix` reader already
consumes this layout. The first named-diff fixture should change an existing
basic snapshots entry to a shard-status entry, because that exercises the
non-empty shard map while leaving the heavier user-metadata and clone cases to
the existing full-state fixtures.
That snapshots fixture is now implemented and validates the final top-level
custom complete-named-diff candidate in this sequence. The top-level custom
complete-named-diff path now has focused fixture coverage for
`repository_cleanup`, `restore`, `snapshot_deletions`, and `snapshots`.
That first step is now covered by the `view` metadata custom named diff
fixture: the outer metadata custom map diff carries a `view` diff key, then the
`ViewMetadataDiff` payload writes a nested view-keyed map diff. The nested
changed view entry uses the default `AbstractDiffable` boolean and a full
`View.writeTo` payload when the replacement is present.
`queryGroups` follows the same nested map-diff pattern:
`WorkloadGroupMetadataDiff` writes a workload-group-id keyed map diff and uses
`WorkloadGroup.readDiff` for changed entries. Since `WorkloadGroup.readDiff`
also delegates to `AbstractDiffable`, the nested changed workload group entry
starts with a replacement boolean and, when present, the full
`WorkloadGroup.writeTo` payload. The existing full-state
`read_workload_group_prefix` reader can be reused after that boolean, with the
same stream-version handling for 3.6.0+ search settings.
The `queryGroups` metadata custom named diff fixture now validates that path by
changing resource limits, resiliency mode, search settings, and updated
timestamp on an existing workload group id.
`data_stream` follows the same map-backed named diff shape:
`DataStreamMetadataDiff` writes a data-stream-name keyed map diff and uses
`DataStream.readDiffFrom` for changed entries. `DataStream.readDiffFrom`
delegates to `AbstractDiffable`, so a changed data stream entry starts with a
replacement boolean and, when present, the full `DataStream.writeTo` payload:
data-stream name, timestamp field, backing `Index` list, and generation. The
existing full-state `read_data_stream_prefix` reader can be reused after that
boolean.
The `data_stream` metadata custom named diff fixture now validates this by
changing an existing data stream's generation and backing index list.
`component_template` follows the same map-backed named diff shape:
`ComponentTemplateMetadataDiff` writes a component-template-name keyed map diff
and uses `ComponentTemplate.readComponentTemplateDiffFrom` for changed entries.
That reader delegates to `AbstractDiffable`, so a changed component template
entry starts with a replacement boolean and, when present, the full
`ComponentTemplate.writeTo` payload. The existing full-state
`read_component_template_prefix` reader was split so the nested diff path can
reuse the component template value reader after the map key has already
provided the component template name. The component-template named diff fixture
validates this by changing settings, version, and metadata for an existing
component template name.
`index_template` composable metadata custom named diff follows the same
map-backed shape: `ComposableIndexTemplateMetadataDiff` writes a
composable-template-name keyed map diff and uses
`ComposableIndexTemplate.readITV2DiffFrom` for changed entries. That reader
delegates to `AbstractDiffable`, so a changed composable template entry starts
with a replacement boolean and, when present, the full
`ComposableIndexTemplate.writeTo` value payload. The nested diff path reuses the
composable index template value reader after the map key has already supplied
the template name. The named diff fixture validates this by changing index
patterns, priority/version, component-template refs, template settings, and
metadata on an existing composable template.

Legacy index-template metadata named diffs are not metadata-custom diffs. They
live in `MetadataDiff.templates`, a string-keyed map diff over
`IndexTemplateMetadata`. OpenSearch reads that map with
`DiffableUtils.readJdkMapDiff(..., IndexTemplateMetadata::readFrom,
IndexTemplateMetadata::readDiffFrom)`, and `IndexTemplateMetadata.readDiffFrom`
delegates to `AbstractDiffable`. A changed legacy template entry therefore
writes the template map key, a replacement boolean, and, when present, the full
`IndexTemplateMetadata.writeTo` payload. That payload repeats the template name,
then writes order, patterns, settings, mappings, aliases, and optional version.
The existing full-state/upsert `read_index_template_metadata_prefix` reader is
now reused directly after the replacement boolean because the replacement
payload contains its own template name. The named metadata template fixture
validates this by changing order, pattern, setting, and version for an existing
legacy template. Mapping and alias changes do not use a different wire path:
because the changed template is serialized as a complete replacement, the same
payload includes mapping entries as compressed x-content and alias entries as
`AliasMetadata.writeTo` values. The existing reader already summarizes both
fields. The separate mapping/alias named template fixture validates the same
replacement branch with mapping compressed-byte summary and alias name
assertions, rather than adding a new decoder branch.

Routing index diff layout has been checked against OpenSearch
`RoutingTable.RoutingTableDiff`, `IndexRoutingTable`, `IndexShardRoutingTable`,
`DiffableUtils.MapDiff`, and `AbstractDiffable`. The routing table map uses a
string-key `MapDiff` with `IndexRoutingTable::readDiffFrom`, not a
`NamedDiffableValueSerializer`; the serialized diff entry is therefore the
index name key followed directly by the default `AbstractDiffable` boolean.
`true` means a full `IndexRoutingTable.writeTo` payload follows, and `false`
means no replacement payload. Because `IndexRoutingTable` does not implement an
incremental diff of its own, a changed routing index currently serializes as a
complete replacement. Rust now reads the boolean and reuses the existing
`IndexRoutingTable` prefix reader when it is `true`; `false` is recorded as a
no-payload diff.

Metadata index diff layout has been checked against OpenSearch `MetadataDiff`
and `IndexMetadataDiff`. The metadata indices map uses a string-key `MapDiff`
with `IndexMetadata::readDiffFrom`; after the map key, `IndexMetadataDiff`
writes its own payload, not a complete-diff boolean. The payload starts with
the index name, routing shard count, version, mapping/settings/aliases
versions, state byte, and full settings. It then writes map diff envelopes for
mappings, aliases, custom data, in-sync allocation ids, and rollover infos,
followed by `isSystem`, optional context for version 2.17.0+, optional
ingestion status for 3.0.0+, and for 3.6.0+ a `SplitShardsMetadata` diff plus
the primary terms map. Rust now reads the scalar header/settings, consumes
nested mapping, alias, custom data, rollover info, in-sync allocation id, and
split-shards diffs.

Nested metadata mapping diff layout has been checked against OpenSearch
`MappingMetadata` and `AbstractDiffable`. `MappingMetadata.readDiffFrom` uses
the default complete-diff boolean; `true` is followed by the same
`MappingMetadata.writeTo` payload used by full metadata: mapping type,
`CompressedXContent` source, and routing-required flag. The existing Rust
`IndexMapping` prefix reader now consumes that full payload shape after the
nested mapping key and complete-diff boolean.

Nested metadata alias diff layout has been checked against OpenSearch
`AliasMetadata` and `AbstractDiffable`. `AliasMetadata.readDiffFrom` also uses
the default complete-diff boolean; `true` is followed by the same
`AliasMetadata.writeTo` payload used by full metadata: alias name, optional
filter, optional index/search routing, optional write-index, and optional
hidden flag. The existing Rust `TemplateAlias` prefix reader now consumes that
full payload shape after the nested alias key and complete-diff boolean.

Nested metadata custom data diff layout has been checked against OpenSearch
`DiffableStringMap`. The outer index custom data map is still a
`DiffableUtils.MapDiff<String, DiffableStringMap>`, so the first value field is
the custom data key. Unlike mapping and alias metadata, `DiffableStringMap`
does not use the default `AbstractDiffable` complete-diff boolean. Its nested
diff payload is `DiffableStringMapDiff`: a string delete list followed by a
string-to-string upsert map. It never writes incremental per-key diffs. Rust
now records the outer custom data key plus nested delete/upsert string keys and
values.

Nested metadata rollover info diff layout has been checked against OpenSearch
`RolloverInfo` and `AbstractDiffable`. `RolloverInfo.readDiffFrom` uses the
default complete-diff boolean; `true` is followed by the same
`RolloverInfo.writeTo` payload used by full index metadata: rollover alias,
rollover time as VLong, and a named-writeable condition list. The existing Rust
`IndexRolloverInfo` prefix reader now consumes that full payload shape after
the outer rollover map key and complete-diff boolean, including supported
`max_docs`, `max_age`, and `max_size` condition payloads.

Nested metadata in-sync allocation ids layout has been checked against
OpenSearch `DiffableUtils.StringSetValueSerializer`. `StringSetValueSerializer`
is non-diffable, so changed shard entries are written as map upserts rather
than incremental diff entries. Although the read path is wired through
`getVIntKeySerializer`, OpenSearch's serializer singleton currently resolves to
the int-key serializer, so diff envelope shard ids are four-byte ints. The
payload shape is the standard `MapDiff` envelope: deleted shard ids, zero diffs
for changed string sets, then upsert entries where each value is a string
collection. Rust now records deleted shard ids and upsert shard ids with their
allocation id strings; any non-zero diff entry count remains fail-closed
because the OpenSearch serializer is not expected to emit one for this value
type.

Metadata index diff nested coverage is now complete for the current
`IndexMetadataDiff` prefix scope. Java publication fixtures cover the scalar
header/settings case, nested mappings, aliases, custom data, in-sync allocation
ids, rollover infos, and the `SplitShardsMetadata` replacement diff. Remaining
publication diff widening should move back out to metadata custom map entries
and cover non-`repositories` custom payloads such as component templates,
composable templates, data streams, ingest/search pipelines, scripts,
persistent tasks, views, workload groups, weighted routing, decommission
metadata, and other already-supported full-state custom decoders.

## Decode Policy

Unknown data should not be silently dropped. Until a compatibility story exists
for every custom metadata type, unsupported named writeables should return an
explicit error. New `UnsupportedNamedWriteable` findings should be recorded in
`unsupported-custom-ledger.md` with the OpenSearch version, section, custom
name, reproducer, captured error, and decoder plan before decode support is
widened.

## Fixture Strategy

The first fixture should be generated by Java OpenSearch using
`ClusterStateResponse.writeTo`. Use a single-node state with no user indices as
the smallest useful fixture, then add index metadata, routing, blocks, and
customs one section at a time. Each fixture should record the OpenSearch version
id used to serialize it.

## Later Publish Path

Publishing cluster state requires the coordination layer:

- pre-vote
- join validation
- publication
- commit
- follower checks
- leader checks
- persisted term and voting configuration

This is intentionally out of the first implementation milestone.
