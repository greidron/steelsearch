# Cluster-State Custom Registry Inventory

This inventory tracks OpenSearch built-in cluster-state named writeables that
SteelSearch must decode or intentionally reject. The source of truth is the
local Java source at `../OpenSearch/server/src/main/java/org/opensearch/cluster/ClusterModule.java`,
especially `getNamedWriteables()`.

Current Rust stream target: OpenSearch `3.7.0` wire id `3_070_099`
(`VERSION_3_7_0_ID`).

## Top-Level Cluster-State Customs

These are registered through `registerClusterCustom(...)` in `ClusterModule` and
currently have Rust reader entries in `CLUSTER_STATE_CUSTOM_REGISTRY`.

| Name | Java type | Rust status |
| --- | --- | --- |
| `snapshots` | `SnapshotsInProgress` | prefix decoder, owned typed surface |
| `restore` | `RestoreInProgress` | prefix decoder, owned typed surface |
| `snapshot_deletions` | `SnapshotDeletionsInProgress` | prefix decoder, owned typed surface |
| `repository_cleanup` | `RepositoryCleanupInProgress` | prefix decoder, owned typed surface |

Inventory result: all built-in top-level cluster-state customs registered by
`ClusterModule` are covered by the Rust reader registry. Unknown names still fail closed as
`UnsupportedNamedWriteable { section: "cluster_state.customs", name }`.

## Metadata Customs

These are registered through `registerMetadataCustom(...)` in `ClusterModule`
and currently have Rust reader entries in `METADATA_CUSTOM_REGISTRY`.

| Name | Java type | Rust status |
| --- | --- | --- |
| `repositories` | `RepositoriesMetadata` | prefix decoder, owned typed surface |
| `ingest` | `IngestMetadata` | prefix decoder, owned typed surface |
| `search_pipeline` | `SearchPipelineMetadata` | prefix decoder, owned typed surface |
| `stored_scripts` | `ScriptMetadata` | prefix decoder, owned typed surface |
| `index-graveyard` | `IndexGraveyard` | prefix decoder, owned typed surface |
| `persistent_tasks` | `PersistentTasksCustomMetadata` | prefix decoder, owned typed surface |
| `component_template` | `ComponentTemplateMetadata` | prefix decoder, owned typed surface |
| `index_template` | `ComposableIndexTemplateMetadata` | prefix decoder, owned typed surface |
| `data_stream` | `DataStreamMetadata` | prefix decoder, owned typed surface |
| `view` | `ViewMetadata` | prefix decoder, owned typed surface |
| `weighted_shard_routing` | `WeightedRoutingMetadata` | prefix decoder, owned typed surface |
| `decommissionedAttribute` | `DecommissionAttributeMetadata` | prefix decoder, owned typed surface |
| `queryGroups` | `WorkloadGroupMetadata` | prefix decoder, owned typed surface |

Inventory result: all built-in metadata customs registered by `ClusterModule`
are covered by the Rust reader registry. Unknown names still fail closed as
`UnsupportedNamedWriteable { section: "metadata.custom", name }`.

## Scope Notes

- This inventory covers built-ins registered by core `ClusterModule`, not
  plugin-provided custom metadata. Plugin custom metadata remains compatibility
  ledger material until a concrete plugin interop target is selected.
- `Task.Status` named writeables are also registered by `ClusterModule`, but
  they are not cluster-state custom containers. They matter only when a
  `persistent_tasks` entry references a task status payload.
- The current Rust implementation mostly uses prefix decoders with owned public
  structs. The custom containers are now selected through explicit
  name-to-reader registries before payload-specific typed assignment.
