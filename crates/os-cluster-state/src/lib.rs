//! Cluster-state wire entrypoints and decode scaffolding.

use bytes::{Bytes, BytesMut};
use os_core::Version;
use os_stream::{StreamInput, StreamInputError, StreamOutput};
use os_transport::error::read_exception;
use os_transport::frame::encode_message;
use os_transport::variable_header::RequestVariableHeader;
use os_transport::TransportMessage;
use os_wire::TransportStatus;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};
use thiserror::Error;

pub const CLUSTER_STATE_ACTION: &str = "cluster:monitor/state";
pub const DEFAULT_CLUSTER_STATE_STREAM_VERSION_ID: i32 = 137_287_827;
const VERSION_2_7_0_ID: i32 = 2_070_099;
const VERSION_2_9_0_ID: i32 = 2_090_099;
const VERSION_2_17_0_ID: i32 = 2_170_099;
const VERSION_2_18_0_ID: i32 = 2_180_099;
const VERSION_3_0_0_ID: i32 = 3_000_099;
const VERSION_3_6_0_ID: i32 = 3_060_099;
const VERSION_3_7_0_ID: i32 = 3_070_099;
const STREAM_ADDRESS_VERSION_ID: i32 = 137_237_827;

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterStateRequest {
    pub cluster_manager_node_timeout: TimeValue,
    pub local: bool,
    pub routing_table: bool,
    pub nodes: bool,
    pub metadata: bool,
    pub blocks: bool,
    pub customs: bool,
    pub indices: Vec<String>,
    pub indices_options: IndicesOptions,
    pub wait_for_timeout: TimeValue,
    pub wait_for_metadata_version: Option<i64>,
}

impl Default for ClusterStateRequest {
    fn default() -> Self {
        Self {
            cluster_manager_node_timeout: TimeValue::seconds(30),
            local: false,
            routing_table: true,
            nodes: true,
            metadata: true,
            blocks: true,
            customs: true,
            indices: Vec::new(),
            indices_options: IndicesOptions::lenient_expand_open(),
            wait_for_timeout: TimeValue::minutes(1),
            wait_for_metadata_version: None,
        }
    }
}

impl ClusterStateRequest {
    pub fn minimal_probe() -> Self {
        Self {
            routing_table: false,
            nodes: false,
            metadata: false,
            blocks: false,
            customs: false,
            ..Self::default()
        }
    }

    pub fn write(&self, output: &mut StreamOutput) {
        write_empty_task_id(output);
        self.cluster_manager_node_timeout.write(output);
        output.write_bool(self.local);
        output.write_bool(self.routing_table);
        output.write_bool(self.nodes);
        output.write_bool(self.metadata);
        output.write_bool(self.blocks);
        output.write_bool(self.customs);
        output.write_string_array(&self.indices);
        self.indices_options.write(output);
        self.wait_for_timeout.write(output);
        write_optional_long(output, self.wait_for_metadata_version);
    }

    pub fn to_bytes(&self) -> Bytes {
        let mut output = StreamOutput::new();
        self.write(&mut output);
        output.freeze()
    }
}

pub fn build_cluster_state_request_frame(
    request_id: i64,
    version: Version,
    request: &ClusterStateRequest,
) -> BytesMut {
    let variable_header = RequestVariableHeader::new(CLUSTER_STATE_ACTION).to_bytes();
    let body = request.to_bytes();
    let message = TransportMessage {
        request_id,
        status: TransportStatus::request(),
        version,
        variable_header: BytesMut::from(&variable_header[..]),
        body: BytesMut::from(&body[..]),
    };

    encode_message(&message)
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndicesOptions {
    pub options: Vec<i32>,
    pub wildcard_states: Vec<i32>,
}

impl IndicesOptions {
    pub fn lenient_expand_open() -> Self {
        Self {
            options: vec![0, 2],
            wildcard_states: vec![0],
        }
    }

    fn write(&self, output: &mut StreamOutput) {
        write_enum_set(output, &self.options);
        write_enum_set(output, &self.wildcard_states);
    }
}

#[derive(Copy, Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TimeValue {
    pub duration: i64,
    pub unit: TimeUnit,
}

impl TimeValue {
    pub const fn seconds(duration: i64) -> Self {
        Self {
            duration,
            unit: TimeUnit::Seconds,
        }
    }

    pub const fn minutes(duration: i64) -> Self {
        Self {
            duration,
            unit: TimeUnit::Minutes,
        }
    }

    fn write(self, output: &mut StreamOutput) {
        output.write_zlong(self.duration);
        output.write_byte(self.unit.ordinal());
    }
}

#[derive(Copy, Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum TimeUnit {
    Nanoseconds,
    Microseconds,
    Milliseconds,
    Seconds,
    Minutes,
    Hours,
    Days,
}

impl TimeUnit {
    const fn ordinal(self) -> u8 {
        match self {
            TimeUnit::Nanoseconds => 0,
            TimeUnit::Microseconds => 1,
            TimeUnit::Milliseconds => 2,
            TimeUnit::Seconds => 3,
            TimeUnit::Minutes => 4,
            TimeUnit::Hours => 5,
            TimeUnit::Days => 6,
        }
    }
}

fn write_empty_task_id(output: &mut StreamOutput) {
    output.write_string("");
}

fn write_enum_set(output: &mut StreamOutput, ordinals: &[i32]) {
    output.write_vint(ordinals.len() as i32);
    for ordinal in ordinals {
        output.write_vint(*ordinal);
    }
}

fn write_optional_long(output: &mut StreamOutput, value: Option<i64>) {
    if let Some(value) = value {
        output.write_bool(true);
        output.write_i64(value);
    } else {
        output.write_bool(false);
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterStateHeader {
    pub version: i64,
    pub state_uuid: String,
    pub cluster_name: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PublicationClusterStateDiffHeaderPrefix {
    pub cluster_name: String,
    pub from_uuid: String,
    pub to_uuid: String,
    pub to_version: i64,
    pub remaining_bytes_after_header: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PublicationClusterStateDiffPrefix {
    pub header: PublicationClusterStateDiffHeaderPrefix,
    pub routing_table_version: i64,
    pub routing_indices: StringMapDiffEnvelopePrefix,
    pub nodes_complete_diff: bool,
    pub metadata_cluster_uuid: String,
    pub metadata_cluster_uuid_committed: bool,
    pub metadata_version: i64,
    pub metadata_hashes_of_consistent_settings: DiffableStringMapDiffPrefix,
    pub metadata_indices: StringMapDiffEnvelopePrefix,
    pub metadata_templates: StringMapDiffEnvelopePrefix,
    pub metadata_customs: StringMapDiffEnvelopePrefix,
    pub blocks_complete_diff: bool,
    pub customs: StringMapDiffEnvelopePrefix,
    pub minimum_cluster_manager_nodes_on_publishing_cluster_manager: i32,
    pub remaining_bytes_after_prefix: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct StringMapDiffEnvelopePrefix {
    pub delete_count: usize,
    pub deleted_keys: Vec<String>,
    pub diff_count: usize,
    pub diff_keys: Vec<String>,
    pub upsert_count: usize,
    pub upsert_keys: Vec<String>,
    pub index_metadata_diffs: Vec<IndexMetadataDiffPrefix>,
    pub index_metadata_upserts: Vec<IndexMetadataPrefix>,
    pub index_routing_diffs: Vec<IndexRoutingTableDiffPrefix>,
    pub index_routing_upserts: Vec<IndexRoutingTablePrefix>,
    pub index_template_diffs: Vec<IndexTemplateMetadataDiffPrefix>,
    pub index_template_upserts: Vec<IndexTemplateMetadataPrefix>,
    pub repository_metadata_diffs: Vec<RepositoriesMetadataCustomDiffPrefix>,
    pub repository_metadata_upserts: Vec<RepositoryMetadataPrefix>,
    pub component_template_diffs: Vec<ComponentTemplateMetadataCustomDiffPrefix>,
    pub component_template_upserts: Vec<ComponentTemplatePrefix>,
    pub composable_index_template_diffs: Vec<ComposableIndexTemplateMetadataCustomDiffPrefix>,
    pub composable_index_template_upserts: Vec<ComposableIndexTemplatePrefix>,
    pub data_stream_diffs: Vec<DataStreamMetadataCustomDiffPrefix>,
    pub data_stream_upserts: Vec<DataStreamPrefix>,
    pub ingest_upserts: Vec<IngestPipelinePrefix>,
    pub search_pipeline_upserts: Vec<SearchPipelinePrefix>,
    pub stored_script_upserts: Vec<StoredScriptPrefix>,
    pub index_graveyard_tombstone_upserts: Vec<IndexGraveyardTombstonePrefix>,
    pub persistent_task_upserts: Vec<PersistentTaskPrefix>,
    pub decommission_attribute_diffs: Vec<DecommissionAttributeMetadataCustomDiffPrefix>,
    pub decommission_attribute_upserts: Vec<DecommissionAttributeMetadataPrefix>,
    pub weighted_routing_diffs: Vec<WeightedRoutingMetadataCustomDiffPrefix>,
    pub weighted_routing_upserts: Vec<WeightedRoutingMetadataPrefix>,
    pub view_diffs: Vec<ViewMetadataCustomDiffPrefix>,
    pub view_upserts: Vec<ViewMetadataPrefix>,
    pub workload_group_diffs: Vec<WorkloadGroupMetadataCustomDiffPrefix>,
    pub workload_group_upserts: Vec<WorkloadGroupPrefix>,
    pub repository_cleanup_diffs: Vec<RepositoryCleanupNamedDiffPrefix>,
    pub repository_cleanup_upserts: Vec<RepositoryCleanupInProgressPrefix>,
    pub restore_diffs: Vec<RestoreInProgressNamedDiffPrefix>,
    pub restore_upserts: Vec<RestoreInProgressPrefix>,
    pub snapshot_deletions_diffs: Vec<SnapshotDeletionsInProgressNamedDiffPrefix>,
    pub snapshot_deletions_upserts: Vec<SnapshotDeletionsInProgressPrefix>,
    pub snapshots_diffs: Vec<SnapshotsInProgressNamedDiffPrefix>,
    pub snapshots_upserts: Vec<SnapshotsInProgressPrefix>,
    pub remaining_bytes_after_prefix: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RepositoryCleanupNamedDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<RepositoryCleanupInProgressPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestoreInProgressNamedDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<RestoreInProgressPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotDeletionsInProgressNamedDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<SnapshotDeletionsInProgressPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotsInProgressNamedDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<SnapshotsInProgressPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ViewMetadataCustomDiffPrefix {
    pub delete_count: usize,
    pub deleted_keys: Vec<String>,
    pub diff_count: usize,
    pub diff_keys: Vec<String>,
    pub replacement_diffs: Vec<ViewMetadataDiffPrefix>,
    pub upsert_count: usize,
    pub upsert_keys: Vec<String>,
    pub upserts: Vec<ViewMetadataPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ViewMetadataDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<ViewMetadataPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct WorkloadGroupMetadataCustomDiffPrefix {
    pub delete_count: usize,
    pub deleted_keys: Vec<String>,
    pub diff_count: usize,
    pub diff_keys: Vec<String>,
    pub replacement_diffs: Vec<WorkloadGroupDiffPrefix>,
    pub upsert_count: usize,
    pub upsert_keys: Vec<String>,
    pub upserts: Vec<WorkloadGroupPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct WorkloadGroupDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<WorkloadGroupPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DataStreamMetadataCustomDiffPrefix {
    pub delete_count: usize,
    pub deleted_keys: Vec<String>,
    pub diff_count: usize,
    pub diff_keys: Vec<String>,
    pub replacement_diffs: Vec<DataStreamDiffPrefix>,
    pub upsert_count: usize,
    pub upsert_keys: Vec<String>,
    pub upserts: Vec<DataStreamPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DataStreamDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<DataStreamPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ComponentTemplateMetadataCustomDiffPrefix {
    pub delete_count: usize,
    pub deleted_keys: Vec<String>,
    pub diff_count: usize,
    pub diff_keys: Vec<String>,
    pub replacement_diffs: Vec<ComponentTemplateDiffPrefix>,
    pub upsert_count: usize,
    pub upsert_keys: Vec<String>,
    pub upserts: Vec<ComponentTemplatePrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ComponentTemplateDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<ComponentTemplatePrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexRoutingTableDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<IndexRoutingTablePrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MapDiffCountsPrefix {
    pub delete_count: usize,
    pub diff_count: usize,
    pub upsert_count: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexMappingDiffPrefix {
    pub key: String,
    pub replacement_present: bool,
    pub replacement: Option<IndexMappingPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexAliasDiffPrefix {
    pub key: String,
    pub replacement_present: bool,
    pub replacement: Option<TemplateAliasPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexCustomDataDiffPrefix {
    pub key: String,
    pub diff: DiffableStringMapDiffPrefix,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexRolloverInfoDiffPrefix {
    pub key: String,
    pub replacement_present: bool,
    pub replacement: Option<IndexRolloverInfoPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct InSyncAllocationIdsDiffPrefix {
    pub deleted_shard_ids: Vec<i32>,
    pub upserts: Vec<InSyncAllocationIdsUpsertPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct InSyncAllocationIdsUpsertPrefix {
    pub shard_id: i32,
    pub allocation_ids: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexMetadataDiffPrefix {
    pub name: String,
    pub routing_num_shards: i32,
    pub version: i64,
    pub mapping_version: i64,
    pub settings_version: i64,
    pub aliases_version: i64,
    pub state_id: u8,
    pub settings_count: usize,
    pub index_uuid: Option<String>,
    pub number_of_shards: Option<i32>,
    pub number_of_replicas: Option<i32>,
    pub mappings: MapDiffCountsPrefix,
    pub mapping_diffs: Vec<IndexMappingDiffPrefix>,
    pub aliases: MapDiffCountsPrefix,
    pub alias_diffs: Vec<IndexAliasDiffPrefix>,
    pub custom_data: MapDiffCountsPrefix,
    pub custom_data_diffs: Vec<IndexCustomDataDiffPrefix>,
    pub in_sync_allocation_ids: MapDiffCountsPrefix,
    pub in_sync_allocation_ids_diff: InSyncAllocationIdsDiffPrefix,
    pub rollover_infos: MapDiffCountsPrefix,
    pub rollover_info_diffs: Vec<IndexRolloverInfoDiffPrefix>,
    pub system: bool,
    pub context_present: bool,
    pub ingestion_status_present: bool,
    pub ingestion_paused: Option<bool>,
    pub split_shards_replacement_present: Option<bool>,
    pub split_shards_replacement: Option<SplitShardsMetadataPrefix>,
    pub primary_terms_count: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DiffableStringMapDiffPrefix {
    pub delete_count: usize,
    pub deleted_keys: Vec<String>,
    pub upsert_count: usize,
    pub upsert_keys: Vec<String>,
    pub upsert_entries: Vec<StringMapEntryPrefix>,
    pub remaining_bytes_after_prefix: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct StringMapEntryPrefix {
    pub key: String,
    pub value: String,
}

/// Decode surface for `ClusterStateResponse(StreamInput)`.
///
/// This is intentionally still a prefix-shaped API because most named
/// writeable payloads are not implemented yet. For the minimal Java fixture it
/// consumes the complete response, including empty discovery nodes, empty
/// cluster blocks, empty cluster-state customs, and the final `waitForTimedOut`
/// flag. Non-empty unsupported sections fail closed instead of being skipped.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterStateResponsePrefix {
    pub response_cluster_name: String,
    pub state_header: Option<ClusterStateHeader>,
    pub metadata_prefix: Option<MetadataPrefix>,
    pub routing_table: Option<RoutingTablePrefix>,
    pub discovery_nodes: Option<DiscoveryNodesPrefix>,
    pub cluster_blocks: Option<ClusterBlocksPrefix>,
    pub cluster_state_tail: Option<ClusterStateTailPrefix>,
    pub wait_for_timed_out: Option<bool>,
    pub remaining_state_bytes_after_prefix: usize,
}

impl ClusterStateResponsePrefix {
    pub fn read(bytes: Bytes) -> Result<Self, ClusterStateDecodeError> {
        Self::read_with_version(
            bytes,
            Version::from_id(DEFAULT_CLUSTER_STATE_STREAM_VERSION_ID),
        )
    }

    pub fn read_with_version(
        bytes: Bytes,
        stream_version: Version,
    ) -> Result<Self, ClusterStateDecodeError> {
        let mut input = StreamInput::new(bytes);
        let response_cluster_name = input.read_string()?;
        let state_header = if input.read_bool()? {
            Some(read_cluster_state_header(&mut input)?)
        } else {
            None
        };
        let metadata_prefix = if state_header.is_some() {
            Some(read_metadata_prefix(&mut input, stream_version)?)
        } else {
            None
        };
        let routing_table = if state_header.is_some() {
            Some(read_routing_table_prefix(&mut input, stream_version)?)
        } else {
            None
        };
        let discovery_nodes = if state_header.is_some() {
            Some(read_discovery_nodes_prefix(&mut input, stream_version)?)
        } else {
            None
        };
        let cluster_blocks = if state_header.is_some() {
            Some(read_cluster_blocks_prefix(&mut input)?)
        } else {
            None
        };
        let cluster_state_tail = if state_header.is_some() {
            Some(read_cluster_state_tail_prefix(&mut input)?)
        } else {
            None
        };
        let wait_for_timed_out = Some(input.read_bool()?);
        let remaining_state_bytes_after_prefix = input.remaining();

        Ok(Self {
            response_cluster_name,
            state_header,
            metadata_prefix,
            routing_table,
            discovery_nodes,
            cluster_blocks,
            cluster_state_tail,
            wait_for_timed_out,
            remaining_state_bytes_after_prefix,
        })
    }
}

pub fn read_publication_cluster_state_diff_header_prefix(
    bytes: Bytes,
) -> Result<PublicationClusterStateDiffHeaderPrefix, ClusterStateDecodeError> {
    let mut input = StreamInput::new(bytes);
    read_publication_cluster_state_diff_header_prefix_from(&mut input)
}

pub fn read_publication_cluster_state_diff_prefix(
    bytes: Bytes,
    _stream_version: Version,
) -> Result<PublicationClusterStateDiffPrefix, ClusterStateDecodeError> {
    let mut input = StreamInput::new(bytes);
    let header = read_publication_cluster_state_diff_header_prefix_from(&mut input)?;

    let routing_table_version = input.read_i64()?;
    let routing_indices = read_routing_index_map_diff_envelope_prefix_from(
        &mut input,
        "cluster_state.diff.routing",
        _stream_version,
    )?;

    let nodes_complete_diff = input.read_bool()?;
    if nodes_complete_diff {
        return Err(ClusterStateDecodeError::UnsupportedSection(
            "cluster_state.diff.nodes.complete",
        ));
    }

    let metadata_cluster_uuid = input.read_string()?;
    let metadata_cluster_uuid_committed = input.read_bool()?;
    let metadata_version = input.read_i64()?;
    let _coordination_metadata = read_coordination_metadata_prefix(&mut input)?;
    let _transient_settings =
        read_settings_prefix(&mut input, "cluster_state.diff.metadata.transient_settings")?;
    let _persistent_settings = read_settings_prefix(
        &mut input,
        "cluster_state.diff.metadata.persistent_settings",
    )?;
    let metadata_hashes_of_consistent_settings =
        read_diffable_string_map_diff_prefix(&mut input, "cluster_state.diff.metadata.hashes")?;
    let metadata_indices = read_metadata_index_map_diff_envelope_prefix_from(
        &mut input,
        "cluster_state.diff.metadata.indices",
        _stream_version,
    )?;
    let metadata_templates = read_metadata_template_map_diff_envelope_prefix_from(
        &mut input,
        "cluster_state.diff.metadata.templates",
    )?;
    let metadata_customs = read_metadata_custom_map_diff_envelope_prefix_from(
        &mut input,
        "cluster_state.diff.metadata.customs",
        _stream_version,
    )?;

    let blocks_complete_diff = input.read_bool()?;
    if blocks_complete_diff {
        return Err(ClusterStateDecodeError::UnsupportedSection(
            "cluster_state.diff.blocks.complete",
        ));
    }

    let customs = read_cluster_state_custom_map_diff_envelope_prefix_from(
        &mut input,
        "cluster_state.diff.customs",
    )?;
    let minimum_cluster_manager_nodes_on_publishing_cluster_manager = input.read_vint()?;

    Ok(PublicationClusterStateDiffPrefix {
        header,
        routing_table_version,
        routing_indices,
        nodes_complete_diff,
        metadata_cluster_uuid,
        metadata_cluster_uuid_committed,
        metadata_version,
        metadata_hashes_of_consistent_settings,
        metadata_indices,
        metadata_templates,
        metadata_customs,
        blocks_complete_diff,
        customs,
        minimum_cluster_manager_nodes_on_publishing_cluster_manager,
        remaining_bytes_after_prefix: input.remaining(),
    })
}

pub fn read_string_map_diff_envelope_prefix(
    bytes: Bytes,
    section: &'static str,
) -> Result<StringMapDiffEnvelopePrefix, ClusterStateDecodeError> {
    let mut input = StreamInput::new(bytes);
    read_string_map_diff_envelope_prefix_from(&mut input, section)
}

fn read_publication_cluster_state_diff_header_prefix_from(
    input: &mut StreamInput,
) -> Result<PublicationClusterStateDiffHeaderPrefix, ClusterStateDecodeError> {
    let is_full_state = input.read_bool()?;
    if is_full_state {
        return Err(ClusterStateDecodeError::UnsupportedSection(
            "publication.full_cluster_state",
        ));
    }

    Ok(PublicationClusterStateDiffHeaderPrefix {
        cluster_name: input.read_string()?,
        from_uuid: input.read_string()?,
        to_uuid: input.read_string()?,
        to_version: input.read_i64()?,
        remaining_bytes_after_header: input.remaining(),
    })
}

pub fn read_cluster_state_header(
    input: &mut StreamInput,
) -> Result<ClusterStateHeader, ClusterStateDecodeError> {
    let cluster_name = input.read_string()?;
    let version = input.read_i64()?;
    let state_uuid = input.read_string()?;
    Ok(ClusterStateHeader {
        version,
        state_uuid,
        cluster_name,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MetadataPrefix {
    pub version: i64,
    pub cluster_uuid: String,
    pub cluster_uuid_committed: bool,
    pub coordination: CoordinationMetadataPrefix,
    pub transient_settings_count: usize,
    pub transient_settings: Vec<SettingPrefix>,
    pub persistent_settings_count: usize,
    pub persistent_settings: Vec<SettingPrefix>,
    pub hashes_of_consistent_settings_count: usize,
    pub hashes_of_consistent_settings: Vec<SettingPrefix>,
    pub index_metadata_count: usize,
    pub index_metadata: Vec<IndexMetadataPrefix>,
    pub templates_count: usize,
    pub templates: Vec<IndexTemplateMetadataPrefix>,
    pub custom_metadata_count: usize,
    pub ingest_pipelines_count: Option<usize>,
    pub ingest_pipelines: Vec<IngestPipelinePrefix>,
    pub search_pipelines_count: Option<usize>,
    pub search_pipelines: Vec<SearchPipelinePrefix>,
    pub stored_scripts_count: Option<usize>,
    pub stored_scripts: Vec<StoredScriptPrefix>,
    pub persistent_tasks_count: Option<usize>,
    pub persistent_tasks: Vec<PersistentTaskPrefix>,
    pub decommission_attribute: Option<DecommissionAttributeMetadataPrefix>,
    pub index_graveyard_tombstones_count: Option<usize>,
    pub index_graveyard_tombstones: Vec<IndexGraveyardTombstonePrefix>,
    pub component_templates_count: Option<usize>,
    pub component_templates: Vec<ComponentTemplatePrefix>,
    pub composable_index_templates_count: Option<usize>,
    pub composable_index_templates: Vec<ComposableIndexTemplatePrefix>,
    pub data_streams_count: Option<usize>,
    pub data_streams: Vec<DataStreamPrefix>,
    pub repositories_count: Option<usize>,
    pub repositories: Vec<RepositoryMetadataPrefix>,
    pub weighted_routing: Option<WeightedRoutingMetadataPrefix>,
    pub views_count: Option<usize>,
    pub views: Vec<ViewMetadataPrefix>,
    pub workload_groups_count: Option<usize>,
    pub workload_groups: Vec<WorkloadGroupPrefix>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum MetadataCustomKind {
    Ingest,
    SearchPipeline,
    StoredScripts,
    PersistentTasks,
    DecommissionedAttribute,
    IndexGraveyard,
    ComponentTemplate,
    ComposableIndexTemplate,
    DataStream,
    Repositories,
    WeightedShardRouting,
    View,
    WorkloadGroups,
}

const METADATA_CUSTOM_DISPATCH: &[(&str, MetadataCustomKind)] = &[
    ("ingest", MetadataCustomKind::Ingest),
    ("search_pipeline", MetadataCustomKind::SearchPipeline),
    ("stored_scripts", MetadataCustomKind::StoredScripts),
    ("persistent_tasks", MetadataCustomKind::PersistentTasks),
    (
        "decommissionedAttribute",
        MetadataCustomKind::DecommissionedAttribute,
    ),
    ("index-graveyard", MetadataCustomKind::IndexGraveyard),
    ("component_template", MetadataCustomKind::ComponentTemplate),
    (
        "index_template",
        MetadataCustomKind::ComposableIndexTemplate,
    ),
    ("data_stream", MetadataCustomKind::DataStream),
    ("repositories", MetadataCustomKind::Repositories),
    (
        "weighted_shard_routing",
        MetadataCustomKind::WeightedShardRouting,
    ),
    ("view", MetadataCustomKind::View),
    ("queryGroups", MetadataCustomKind::WorkloadGroups),
];

fn metadata_custom_kind(name: &str) -> Option<MetadataCustomKind> {
    METADATA_CUSTOM_DISPATCH
        .iter()
        .find_map(|(candidate, kind)| (*candidate == name).then_some(*kind))
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IngestPipelinePrefix {
    pub id: String,
    pub config_len: usize,
    pub media_type: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchPipelinePrefix {
    pub id: String,
    pub config_len: usize,
    pub media_type: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct StoredScriptPrefix {
    pub id: String,
    pub lang: String,
    pub source_len: usize,
    pub options_count: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PersistentTaskPrefix {
    pub map_key: String,
    pub id: String,
    pub allocation_id: i64,
    pub task_name: String,
    pub params_name: String,
    pub fixture_params_marker: Option<String>,
    pub fixture_params_generation: Option<i64>,
    pub state_name: Option<String>,
    pub fixture_state_marker: Option<String>,
    pub fixture_state_generation: Option<i64>,
    pub executor_node: Option<String>,
    pub assignment_explanation: String,
    pub allocation_id_on_last_status_update: Option<i64>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DecommissionAttributeMetadataPrefix {
    pub attribute_name: String,
    pub attribute_value: String,
    pub status: String,
    pub request_id: String,
}

fn read_ingest_pipeline_prefix(
    input: &mut StreamInput,
) -> Result<IngestPipelinePrefix, ClusterStateDecodeError> {
    let id = input.read_string()?;
    let config = input.read_bytes_reference()?;
    let media_type = input.read_string()?;
    Ok(IngestPipelinePrefix {
        id,
        config_len: config.len(),
        media_type,
    })
}

fn read_search_pipeline_prefix(
    input: &mut StreamInput,
) -> Result<SearchPipelinePrefix, ClusterStateDecodeError> {
    let id = input.read_string()?;
    let config = input.read_bytes_reference()?;
    let media_type = input.read_string()?;
    Ok(SearchPipelinePrefix {
        id,
        config_len: config.len(),
        media_type,
    })
}

fn read_stored_script_prefix(
    input: &mut StreamInput,
) -> Result<StoredScriptPrefix, ClusterStateDecodeError> {
    let id = input.read_string()?;
    let lang = input.read_string()?;
    let source = input.read_string()?;
    let options = read_generic_map_prefix(input, "metadata.stored_scripts.options")?;
    Ok(StoredScriptPrefix {
        id,
        lang,
        source_len: source.len(),
        options_count: options.len(),
    })
}

fn read_persistent_task_prefix(
    input: &mut StreamInput,
    map_key: String,
) -> Result<PersistentTaskPrefix, ClusterStateDecodeError> {
    let id = input.read_string()?;
    let allocation_id = input.read_i64()?;
    let task_name = input.read_string()?;
    let params_name = input.read_string()?;
    let (fixture_params_marker, fixture_params_generation) = match params_name.as_str() {
        "fixture-persistent-task" | "steelsearch-fixture-persistent-task" => {
            (Some(input.read_string()?), Some(input.read_i64()?))
        }
        _ => (None, None),
    };
    let (state_name, fixture_state_marker, fixture_state_generation) = if input.read_bool()? {
        let state_name = input.read_string()?;
        let (marker, generation) = match state_name.as_str() {
            "fixture-persistent-task" | "steelsearch-fixture-persistent-task" => {
                (Some(input.read_string()?), Some(input.read_i64()?))
            }
            _ => (None, None),
        };
        (Some(state_name), marker, generation)
    } else {
        (None, None, None)
    };
    let executor_node = input.read_optional_string()?;
    let assignment_explanation = input.read_string()?;
    let allocation_id_on_last_status_update = read_optional_long(input)?;
    Ok(PersistentTaskPrefix {
        map_key,
        id,
        allocation_id,
        task_name,
        params_name,
        fixture_params_marker,
        fixture_params_generation,
        state_name,
        fixture_state_marker,
        fixture_state_generation,
        executor_node,
        assignment_explanation,
        allocation_id_on_last_status_update,
    })
}

fn read_decommission_attribute_metadata_prefix(
    input: &mut StreamInput,
) -> Result<DecommissionAttributeMetadataPrefix, ClusterStateDecodeError> {
    Ok(DecommissionAttributeMetadataPrefix {
        attribute_name: input.read_string()?,
        attribute_value: input.read_string()?,
        status: input.read_string()?,
        request_id: input.read_string()?,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DecommissionAttributeMetadataCustomDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<DecommissionAttributeMetadataPrefix>,
}

pub fn read_metadata_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<MetadataPrefix, ClusterStateDecodeError> {
    let version = input.read_i64()?;
    let cluster_uuid = input.read_string()?;
    let cluster_uuid_committed = input.read_bool()?;
    let coordination = read_coordination_metadata_prefix(input)?;
    let transient_settings = read_settings_prefix(input, "metadata.transient_settings")?;
    let transient_settings_count = transient_settings.len();
    let persistent_settings = read_settings_prefix(input, "metadata.persistent_settings")?;
    let persistent_settings_count = persistent_settings.len();
    let hashes_of_consistent_settings =
        read_string_map_prefix(input, "metadata.hashes_of_consistent_settings")?;
    let hashes_of_consistent_settings_count = hashes_of_consistent_settings.len();
    let index_metadata_count = read_non_negative_len(input)?;
    let mut index_metadata = Vec::with_capacity(index_metadata_count);
    for _ in 0..index_metadata_count {
        index_metadata.push(read_index_metadata_prefix(input, stream_version)?);
    }
    let templates_count = read_non_negative_len(input)?;
    let mut templates = Vec::with_capacity(templates_count);
    for _ in 0..templates_count {
        templates.push(read_index_template_metadata_prefix(input)?);
    }
    let custom_metadata_count = read_non_negative_len(input)?;
    let mut ingest_pipelines_count = None;
    let mut ingest_pipelines = Vec::new();
    let mut search_pipelines_count = None;
    let mut search_pipelines = Vec::new();
    let mut stored_scripts_count = None;
    let mut stored_scripts = Vec::new();
    let mut persistent_tasks_count = None;
    let mut persistent_tasks = Vec::new();
    let mut decommission_attribute = None;
    let mut index_graveyard_tombstones_count = None;
    let mut index_graveyard_tombstones = Vec::new();
    let mut component_templates_count = None;
    let mut component_templates = Vec::new();
    let mut composable_index_templates_count = None;
    let mut composable_index_templates = Vec::new();
    let mut data_streams_count = None;
    let mut data_streams = Vec::new();
    let mut repositories_count = None;
    let mut repositories = Vec::new();
    let mut weighted_routing = None;
    let mut views_count = None;
    let mut views = Vec::new();
    let mut workload_groups_count = None;
    let mut workload_groups = Vec::new();
    for _ in 0..custom_metadata_count {
        let name = input.read_string()?;
        match metadata_custom_kind(&name) {
            Some(MetadataCustomKind::Ingest) => {
                let count = read_non_negative_len(input)?;
                ingest_pipelines.reserve(count);
                for _ in 0..count {
                    ingest_pipelines.push(read_ingest_pipeline_prefix(input)?);
                }
                ingest_pipelines_count = Some(count);
            }
            Some(MetadataCustomKind::SearchPipeline) => {
                let count = read_non_negative_len(input)?;
                search_pipelines.reserve(count);
                for _ in 0..count {
                    search_pipelines.push(read_search_pipeline_prefix(input)?);
                }
                search_pipelines_count = Some(count);
            }
            Some(MetadataCustomKind::StoredScripts) => {
                let count = read_non_negative_len(input)?;
                stored_scripts.reserve(count);
                for _ in 0..count {
                    stored_scripts.push(read_stored_script_prefix(input)?);
                }
                stored_scripts_count = Some(count);
            }
            Some(MetadataCustomKind::PersistentTasks) => {
                let _last_allocation_id = input.read_i64()?;
                let count = read_non_negative_len(input)?;
                persistent_tasks.reserve(count);
                for _ in 0..count {
                    let map_key = input.read_string()?;
                    persistent_tasks.push(read_persistent_task_prefix(input, map_key)?);
                }
                persistent_tasks_count = Some(count);
            }
            Some(MetadataCustomKind::DecommissionedAttribute) => {
                decommission_attribute = Some(read_decommission_attribute_metadata_prefix(input)?);
            }
            Some(MetadataCustomKind::IndexGraveyard) => {
                let tombstone_count = read_non_negative_len(input)?;
                index_graveyard_tombstones.reserve(tombstone_count);
                for _ in 0..tombstone_count {
                    index_graveyard_tombstones.push(read_index_graveyard_tombstone_prefix(input)?);
                }
                index_graveyard_tombstones_count = Some(tombstone_count);
            }
            Some(MetadataCustomKind::ComponentTemplate) => {
                let count = read_non_negative_len(input)?;
                component_templates.reserve(count);
                for _ in 0..count {
                    component_templates.push(read_component_template_prefix(input)?);
                }
                component_templates_count = Some(count);
            }
            Some(MetadataCustomKind::ComposableIndexTemplate) => {
                let count = read_non_negative_len(input)?;
                composable_index_templates.reserve(count);
                for _ in 0..count {
                    composable_index_templates.push(read_composable_index_template_prefix(input)?);
                }
                composable_index_templates_count = Some(count);
            }
            Some(MetadataCustomKind::DataStream) => {
                let count = read_non_negative_len(input)?;
                data_streams.reserve(count);
                for _ in 0..count {
                    let _key = input.read_string()?;
                    data_streams.push(read_data_stream_prefix(input)?);
                }
                data_streams_count = Some(count);
            }
            Some(MetadataCustomKind::Repositories) => {
                let count = read_non_negative_len(input)?;
                repositories.reserve(count);
                for _ in 0..count {
                    repositories.push(read_repository_metadata_prefix(input, stream_version)?);
                }
                repositories_count = Some(count);
            }
            Some(MetadataCustomKind::WeightedShardRouting) => {
                weighted_routing = Some(read_weighted_routing_metadata_prefix(input)?);
            }
            Some(MetadataCustomKind::View) => {
                let count = read_non_negative_len(input)?;
                views.reserve(count);
                for _ in 0..count {
                    let _key = input.read_string()?;
                    views.push(read_view_metadata_prefix(input)?);
                }
                views_count = Some(count);
            }
            Some(MetadataCustomKind::WorkloadGroups) => {
                let count = read_non_negative_len(input)?;
                workload_groups.reserve(count);
                for _ in 0..count {
                    let _key = input.read_string()?;
                    workload_groups.push(read_workload_group_prefix(input, stream_version)?);
                }
                workload_groups_count = Some(count);
            }
            None => {
                return Err(ClusterStateDecodeError::UnsupportedNamedWriteable {
                    section: "metadata.custom",
                    name,
                })
            }
        }
    }

    Ok(MetadataPrefix {
        version,
        cluster_uuid,
        cluster_uuid_committed,
        coordination,
        transient_settings_count,
        transient_settings,
        persistent_settings_count,
        persistent_settings,
        hashes_of_consistent_settings_count,
        hashes_of_consistent_settings,
        index_metadata_count,
        index_metadata,
        templates_count,
        templates,
        custom_metadata_count,
        ingest_pipelines_count,
        ingest_pipelines,
        search_pipelines_count,
        search_pipelines,
        stored_scripts_count,
        stored_scripts,
        persistent_tasks_count,
        persistent_tasks,
        decommission_attribute,
        index_graveyard_tombstones_count,
        index_graveyard_tombstones,
        component_templates_count,
        component_templates,
        composable_index_templates_count,
        composable_index_templates,
        data_streams_count,
        data_streams,
        repositories_count,
        repositories,
        weighted_routing,
        views_count,
        views,
        workload_groups_count,
        workload_groups,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct WorkloadGroupPrefix {
    pub name: String,
    pub id: String,
    pub resource_limits_count: usize,
    pub resource_limits: Vec<SettingPrefix>,
    pub resiliency_mode: Option<String>,
    pub search_settings_count: usize,
    pub search_settings: Vec<SettingPrefix>,
    pub updated_at_millis: i64,
}

fn read_workload_group_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<WorkloadGroupPrefix, ClusterStateDecodeError> {
    let name = input.read_string()?;
    let id = input.read_string()?;
    let (resource_limits_count, resource_limits) = read_workload_group_resource_limits(input)?;
    let resiliency_mode = input.read_optional_string()?;
    let (search_settings_count, search_settings) =
        read_workload_group_search_settings(input, stream_version)?;
    let updated_at_millis = input.read_i64()?;

    Ok(WorkloadGroupPrefix {
        name,
        id,
        resource_limits_count,
        resource_limits,
        resiliency_mode,
        search_settings_count,
        search_settings,
        updated_at_millis,
    })
}

fn read_workload_group_resource_limits(
    input: &mut StreamInput,
) -> Result<(usize, Vec<SettingPrefix>), ClusterStateDecodeError> {
    if !input.read_bool()? {
        return Ok((0, Vec::new()));
    }
    let count = read_non_negative_len(input)?;
    let mut resource_limits = Vec::with_capacity(count);
    for _ in 0..count {
        resource_limits.push(SettingPrefix {
            key: input.read_string()?,
            value: Some(read_f64(input)?.to_string()),
        });
    }
    Ok((count, resource_limits))
}

fn read_workload_group_search_settings(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<(usize, Vec<SettingPrefix>), ClusterStateDecodeError> {
    if !stream_version.on_or_after(Version::from_id(3_060_099)) {
        return Ok((0, Vec::new()));
    }
    if input.read_bool()? {
        return Ok((0, Vec::new()));
    }
    let count = read_non_negative_len(input)?;
    let mut settings = Vec::with_capacity(count);
    for _ in 0..count {
        settings.push(SettingPrefix {
            key: input.read_string()?,
            value: Some(input.read_string()?),
        });
    }
    Ok((count, settings))
}

fn read_workload_group_metadata_custom_diff_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<WorkloadGroupMetadataCustomDiffPrefix, ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_keys = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_keys.push(input.read_string()?);
    }

    let diff_count = read_non_negative_len(input)?;
    let mut diff_keys = Vec::with_capacity(diff_count);
    let mut replacement_diffs = Vec::with_capacity(diff_count);
    for _ in 0..diff_count {
        diff_keys.push(input.read_string()?);
        let replacement_present = input.read_bool()?;
        let replacement = if replacement_present {
            Some(read_workload_group_prefix(input, stream_version)?)
        } else {
            None
        };
        replacement_diffs.push(WorkloadGroupDiffPrefix {
            replacement_present,
            replacement,
        });
    }

    let upsert_count = read_non_negative_len(input)?;
    let mut upsert_keys = Vec::with_capacity(upsert_count);
    let mut upserts = Vec::with_capacity(upsert_count);
    for _ in 0..upsert_count {
        upsert_keys.push(input.read_string()?);
        upserts.push(read_workload_group_prefix(input, stream_version)?);
    }

    Ok(WorkloadGroupMetadataCustomDiffPrefix {
        delete_count,
        deleted_keys,
        diff_count,
        diff_keys,
        replacement_diffs,
        upsert_count,
        upsert_keys,
        upserts,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ViewMetadataPrefix {
    pub name: String,
    pub description: Option<String>,
    pub created_at: i64,
    pub modified_at: i64,
    pub target_index_patterns_count: usize,
    pub target_index_patterns: Vec<String>,
}

fn read_view_metadata_prefix(
    input: &mut StreamInput,
) -> Result<ViewMetadataPrefix, ClusterStateDecodeError> {
    let name = input.read_string()?;
    let description = input.read_optional_string()?;
    let created_at = read_zlong(input)?;
    let modified_at = read_zlong(input)?;
    let target_index_patterns_count = read_non_negative_len(input)?;
    let mut target_index_patterns = Vec::with_capacity(target_index_patterns_count);
    for _ in 0..target_index_patterns_count {
        target_index_patterns.push(input.read_string()?);
    }

    Ok(ViewMetadataPrefix {
        name,
        description,
        created_at,
        modified_at,
        target_index_patterns_count,
        target_index_patterns,
    })
}

fn read_view_metadata_custom_diff_prefix(
    input: &mut StreamInput,
) -> Result<ViewMetadataCustomDiffPrefix, ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_keys = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_keys.push(input.read_string()?);
    }

    let diff_count = read_non_negative_len(input)?;
    let mut diff_keys = Vec::with_capacity(diff_count);
    let mut replacement_diffs = Vec::with_capacity(diff_count);
    for _ in 0..diff_count {
        diff_keys.push(input.read_string()?);
        let replacement_present = input.read_bool()?;
        let replacement = if replacement_present {
            Some(read_view_metadata_prefix(input)?)
        } else {
            None
        };
        replacement_diffs.push(ViewMetadataDiffPrefix {
            replacement_present,
            replacement,
        });
    }

    let upsert_count = read_non_negative_len(input)?;
    let mut upsert_keys = Vec::with_capacity(upsert_count);
    let mut upserts = Vec::with_capacity(upsert_count);
    for _ in 0..upsert_count {
        upsert_keys.push(input.read_string()?);
        upserts.push(read_view_metadata_prefix(input)?);
    }

    Ok(ViewMetadataCustomDiffPrefix {
        delete_count,
        deleted_keys,
        diff_count,
        diff_keys,
        replacement_diffs,
        upsert_count,
        upsert_keys,
        upserts,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct WeightedRoutingMetadataPrefix {
    pub awareness_attribute: String,
    pub weights_count: usize,
    pub weights: Vec<SettingPrefix>,
    pub version: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct WeightedRoutingMetadataCustomDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<WeightedRoutingMetadataPrefix>,
}

fn read_weighted_routing_metadata_prefix(
    input: &mut StreamInput,
) -> Result<WeightedRoutingMetadataPrefix, ClusterStateDecodeError> {
    let awareness_attribute = input.read_string()?;
    let weights = read_string_map_prefix(input, "metadata.weighted_shard_routing.weights")?;
    let weights_count = weights.len();
    let version = input.read_i64()?;

    Ok(WeightedRoutingMetadataPrefix {
        awareness_attribute,
        weights_count,
        weights,
        version,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RepositoryMetadataPrefix {
    pub name: String,
    pub repository_type: String,
    pub settings_count: usize,
    pub settings: Vec<SettingPrefix>,
    pub generation: i64,
    pub pending_generation: i64,
    pub crypto_metadata_present: bool,
    pub crypto_key_provider_name: Option<String>,
    pub crypto_key_provider_type: Option<String>,
    pub crypto_settings_count: usize,
    pub crypto_settings: Vec<SettingPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RepositoriesMetadataCustomDiffPrefix {
    pub replacement_present: bool,
    pub replacement_count: usize,
    pub replacement: Vec<RepositoryMetadataPrefix>,
}

fn read_repository_metadata_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<RepositoryMetadataPrefix, ClusterStateDecodeError> {
    let name = input.read_string()?;
    let repository_type = input.read_string()?;
    let settings = read_settings_prefix(input, "metadata.repositories.settings")?;
    let settings_count = settings.len();
    let generation = input.read_i64()?;
    let pending_generation = input.read_i64()?;
    let (
        crypto_metadata_present,
        crypto_key_provider_name,
        crypto_key_provider_type,
        crypto_settings_count,
        crypto_settings,
    ) = if stream_version.on_or_after(Version::from_id(2_100_099)) {
        read_crypto_metadata_prefix(input)?
    } else {
        (false, None, None, 0, Vec::new())
    };

    Ok(RepositoryMetadataPrefix {
        name,
        repository_type,
        settings_count,
        settings,
        generation,
        pending_generation,
        crypto_metadata_present,
        crypto_key_provider_name,
        crypto_key_provider_type,
        crypto_settings_count,
        crypto_settings,
    })
}

fn read_repositories_metadata_custom_diff_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<RepositoriesMetadataCustomDiffPrefix, ClusterStateDecodeError> {
    let replacement_present = input.read_bool()?;
    let (replacement_count, replacement) = if replacement_present {
        let count = read_non_negative_len(input)?;
        let mut repositories = Vec::with_capacity(count);
        for _ in 0..count {
            repositories.push(read_repository_metadata_prefix(input, stream_version)?);
        }
        (count, repositories)
    } else {
        (0, Vec::new())
    };

    Ok(RepositoriesMetadataCustomDiffPrefix {
        replacement_present,
        replacement_count,
        replacement,
    })
}

type CryptoMetadataPrefixTuple = (
    bool,
    Option<String>,
    Option<String>,
    usize,
    Vec<SettingPrefix>,
);

fn read_crypto_metadata_prefix(
    input: &mut StreamInput,
) -> Result<CryptoMetadataPrefixTuple, ClusterStateDecodeError> {
    if !input.read_bool()? {
        return Ok((false, None, None, 0, Vec::new()));
    }
    let key_provider_name = input.read_string()?;
    let key_provider_type = input.read_string()?;
    let settings = read_settings_prefix(input, "metadata.repositories.crypto_metadata.settings")?;
    Ok((
        true,
        Some(key_provider_name),
        Some(key_provider_type),
        settings.len(),
        settings,
    ))
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DataStreamPrefix {
    pub name: String,
    pub timestamp_field: String,
    pub backing_indices_count: usize,
    pub backing_indices: Vec<DataStreamBackingIndexPrefix>,
    pub generation: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DataStreamBackingIndexPrefix {
    pub name: String,
    pub uuid: String,
}

fn read_data_stream_prefix(
    input: &mut StreamInput,
) -> Result<DataStreamPrefix, ClusterStateDecodeError> {
    let name = input.read_string()?;
    let timestamp_field = input.read_string()?;
    let backing_indices_count = read_non_negative_len(input)?;
    let mut backing_indices = Vec::with_capacity(backing_indices_count);
    for _ in 0..backing_indices_count {
        backing_indices.push(DataStreamBackingIndexPrefix {
            name: input.read_string()?,
            uuid: input.read_string()?,
        });
    }
    let generation = input.read_vlong()?;

    Ok(DataStreamPrefix {
        name,
        timestamp_field,
        backing_indices_count,
        backing_indices,
        generation,
    })
}

fn read_data_stream_metadata_custom_diff_prefix(
    input: &mut StreamInput,
) -> Result<DataStreamMetadataCustomDiffPrefix, ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_keys = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_keys.push(input.read_string()?);
    }

    let diff_count = read_non_negative_len(input)?;
    let mut diff_keys = Vec::with_capacity(diff_count);
    let mut replacement_diffs = Vec::with_capacity(diff_count);
    for _ in 0..diff_count {
        diff_keys.push(input.read_string()?);
        let replacement_present = input.read_bool()?;
        let replacement = if replacement_present {
            Some(read_data_stream_prefix(input)?)
        } else {
            None
        };
        replacement_diffs.push(DataStreamDiffPrefix {
            replacement_present,
            replacement,
        });
    }

    let upsert_count = read_non_negative_len(input)?;
    let mut upsert_keys = Vec::with_capacity(upsert_count);
    let mut upserts = Vec::with_capacity(upsert_count);
    for _ in 0..upsert_count {
        upsert_keys.push(input.read_string()?);
        upserts.push(read_data_stream_prefix(input)?);
    }

    Ok(DataStreamMetadataCustomDiffPrefix {
        delete_count,
        deleted_keys,
        diff_count,
        diff_keys,
        replacement_diffs,
        upsert_count,
        upsert_keys,
        upserts,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ComposableIndexTemplatePrefix {
    pub name: String,
    pub index_patterns: Vec<String>,
    pub template_present: bool,
    pub template_settings_count: usize,
    pub template_settings: Vec<SettingPrefix>,
    pub template_mappings_present: bool,
    pub template_mapping: Option<CompressedXContentPrefix>,
    pub template_aliases_count: usize,
    pub template_aliases: Vec<TemplateAliasPrefix>,
    pub component_templates_count: usize,
    pub component_templates: Vec<String>,
    pub priority: Option<i64>,
    pub version: Option<i64>,
    pub metadata_count: usize,
    pub metadata: Vec<SettingPrefix>,
    pub data_stream_template_present: bool,
    pub data_stream_timestamp_field: Option<String>,
    pub context_present: bool,
    pub context_name: Option<String>,
    pub context_version: Option<String>,
    pub context_params_count: usize,
    pub context_params: Vec<SettingPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ComposableIndexTemplateMetadataCustomDiffPrefix {
    pub delete_count: usize,
    pub deleted_keys: Vec<String>,
    pub diff_count: usize,
    pub diff_keys: Vec<String>,
    pub replacement_diffs: Vec<ComposableIndexTemplateDiffPrefix>,
    pub upsert_count: usize,
    pub upsert_keys: Vec<String>,
    pub upserts: Vec<ComposableIndexTemplatePrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ComposableIndexTemplateDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<ComposableIndexTemplatePrefix>,
}

fn read_composable_index_template_prefix(
    input: &mut StreamInput,
) -> Result<ComposableIndexTemplatePrefix, ClusterStateDecodeError> {
    let name = input.read_string()?;
    read_composable_index_template_value_prefix(input, name)
}

fn read_composable_index_template_value_prefix(
    input: &mut StreamInput,
    name: String,
) -> Result<ComposableIndexTemplatePrefix, ClusterStateDecodeError> {
    let index_patterns = read_string_list(input)?;
    let template_present = input.read_bool()?;
    let (
        template_settings_count,
        template_settings,
        template_mappings_present,
        template_mapping,
        template_aliases_count,
        template_aliases,
    ) = if template_present {
        let template =
            read_template_content_prefix(input, "metadata.composable_index_template.template")?;
        (
            template.settings_count,
            template.settings,
            template.mappings_present,
            template.mapping,
            template.aliases_count,
            template.aliases,
        )
    } else {
        (0, Vec::new(), false, None, 0, Vec::new())
    };
    let component_templates = read_optional_string_list(input)?.unwrap_or_default();
    let component_templates_count = component_templates.len();
    let priority = read_optional_vlong(input)?;
    let version = read_optional_vlong(input)?;
    let metadata = read_string_map_prefix(input, "metadata.composable_index_template.metadata")?;
    let metadata_count = metadata.len();
    let (data_stream_template_present, data_stream_timestamp_field) =
        read_data_stream_template_prefix(input)?;
    let (context_present, context_name, context_version, context_params_count, context_params) =
        read_context_prefix(input)?;

    Ok(ComposableIndexTemplatePrefix {
        name,
        index_patterns,
        template_present,
        template_settings_count,
        template_settings,
        template_mappings_present,
        template_mapping,
        template_aliases_count,
        template_aliases,
        component_templates_count,
        component_templates,
        priority,
        version,
        metadata_count,
        metadata,
        data_stream_template_present,
        data_stream_timestamp_field,
        context_present,
        context_name,
        context_version,
        context_params_count,
        context_params,
    })
}

fn read_composable_index_template_metadata_custom_diff_prefix(
    input: &mut StreamInput,
) -> Result<ComposableIndexTemplateMetadataCustomDiffPrefix, ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_keys = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_keys.push(input.read_string()?);
    }

    let diff_count = read_non_negative_len(input)?;
    let mut diff_keys = Vec::with_capacity(diff_count);
    let mut replacement_diffs = Vec::with_capacity(diff_count);
    for _ in 0..diff_count {
        let key = input.read_string()?;
        diff_keys.push(key.clone());
        let replacement_present = input.read_bool()?;
        let replacement = if replacement_present {
            Some(read_composable_index_template_value_prefix(input, key)?)
        } else {
            None
        };
        replacement_diffs.push(ComposableIndexTemplateDiffPrefix {
            replacement_present,
            replacement,
        });
    }

    let upsert_count = read_non_negative_len(input)?;
    let mut upsert_keys = Vec::with_capacity(upsert_count);
    let mut upserts = Vec::with_capacity(upsert_count);
    for _ in 0..upsert_count {
        let key = input.read_string()?;
        upsert_keys.push(key.clone());
        upserts.push(read_composable_index_template_value_prefix(input, key)?);
    }

    Ok(ComposableIndexTemplateMetadataCustomDiffPrefix {
        delete_count,
        deleted_keys,
        diff_count,
        diff_keys,
        replacement_diffs,
        upsert_count,
        upsert_keys,
        upserts,
    })
}

fn read_data_stream_template_prefix(
    input: &mut StreamInput,
) -> Result<(bool, Option<String>), ClusterStateDecodeError> {
    let present = input.read_bool()?;
    if !present {
        return Ok((false, None));
    }
    let timestamp_field = if input.read_bool()? {
        Some(input.read_string()?)
    } else {
        None
    };
    Ok((true, timestamp_field))
}

type ContextPrefixTuple = (
    bool,
    Option<String>,
    Option<String>,
    usize,
    Vec<SettingPrefix>,
);

fn read_context_prefix(
    input: &mut StreamInput,
) -> Result<ContextPrefixTuple, ClusterStateDecodeError> {
    let present = input.read_bool()?;
    if !present {
        return Ok((false, None, None, 0, Vec::new()));
    }
    let name = input.read_string()?;
    let version = input.read_optional_string()?;
    let params =
        read_string_map_prefix(input, "metadata.composable_index_template.context.params")?;
    Ok((true, Some(name), version, params.len(), params))
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ComponentTemplatePrefix {
    pub name: String,
    pub settings_count: usize,
    pub settings: Vec<SettingPrefix>,
    pub mappings_present: bool,
    pub mapping: Option<CompressedXContentPrefix>,
    pub aliases_count: usize,
    pub aliases: Vec<TemplateAliasPrefix>,
    pub version: Option<i64>,
    pub metadata_present: bool,
    pub metadata_count: usize,
    pub metadata: Vec<SettingPrefix>,
}

fn read_component_template_prefix(
    input: &mut StreamInput,
) -> Result<ComponentTemplatePrefix, ClusterStateDecodeError> {
    let name = input.read_string()?;
    read_component_template_value_prefix(input, name)
}

fn read_component_template_value_prefix(
    input: &mut StreamInput,
    name: String,
) -> Result<ComponentTemplatePrefix, ClusterStateDecodeError> {
    let template = read_template_content_prefix(input, "metadata.component_template")?;
    let version = if input.read_bool()? {
        Some(input.read_vlong()?)
    } else {
        None
    };
    let (metadata_present, metadata_count, metadata) = if input.read_bool()? {
        let metadata = read_string_map_prefix(input, "metadata.component_template.metadata")?;
        (true, metadata.len(), metadata)
    } else {
        (false, 0, Vec::new())
    };

    Ok(ComponentTemplatePrefix {
        name,
        settings_count: template.settings_count,
        settings: template.settings,
        mappings_present: template.mappings_present,
        mapping: template.mapping,
        aliases_count: template.aliases_count,
        aliases: template.aliases,
        version,
        metadata_present,
        metadata_count,
        metadata,
    })
}

fn read_component_template_metadata_custom_diff_prefix(
    input: &mut StreamInput,
) -> Result<ComponentTemplateMetadataCustomDiffPrefix, ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_keys = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_keys.push(input.read_string()?);
    }

    let diff_count = read_non_negative_len(input)?;
    let mut diff_keys = Vec::with_capacity(diff_count);
    let mut replacement_diffs = Vec::with_capacity(diff_count);
    for _ in 0..diff_count {
        let key = input.read_string()?;
        diff_keys.push(key.clone());
        let replacement_present = input.read_bool()?;
        let replacement = if replacement_present {
            Some(read_component_template_value_prefix(input, key)?)
        } else {
            None
        };
        replacement_diffs.push(ComponentTemplateDiffPrefix {
            replacement_present,
            replacement,
        });
    }

    let upsert_count = read_non_negative_len(input)?;
    let mut upsert_keys = Vec::with_capacity(upsert_count);
    let mut upserts = Vec::with_capacity(upsert_count);
    for _ in 0..upsert_count {
        let key = input.read_string()?;
        upsert_keys.push(key.clone());
        upserts.push(read_component_template_value_prefix(input, key)?);
    }

    Ok(ComponentTemplateMetadataCustomDiffPrefix {
        delete_count,
        deleted_keys,
        diff_count,
        diff_keys,
        replacement_diffs,
        upsert_count,
        upsert_keys,
        upserts,
    })
}

struct TemplateContentPrefix {
    settings_count: usize,
    settings: Vec<SettingPrefix>,
    mappings_present: bool,
    mapping: Option<CompressedXContentPrefix>,
    aliases_count: usize,
    aliases: Vec<TemplateAliasPrefix>,
}

fn read_template_content_prefix(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<TemplateContentPrefix, ClusterStateDecodeError> {
    let (settings_count, settings) = if input.read_bool()? {
        let settings = read_settings_prefix(input, section)?;
        (settings.len(), settings)
    } else {
        (0, Vec::new())
    };
    let (mappings_present, mapping) = if input.read_bool()? {
        (true, Some(read_compressed_xcontent_prefix(input)?))
    } else {
        (false, None)
    };
    let (aliases_count, aliases) = if input.read_bool()? {
        read_alias_metadata_map(input)?
    } else {
        (0, Vec::new())
    };

    Ok(TemplateContentPrefix {
        settings_count,
        settings,
        mappings_present,
        mapping,
        aliases_count,
        aliases,
    })
}

fn read_alias_metadata_map(
    input: &mut StreamInput,
) -> Result<(usize, Vec<TemplateAliasPrefix>), ClusterStateDecodeError> {
    let aliases_count = read_non_negative_len(input)?;
    let mut aliases = Vec::with_capacity(aliases_count);
    for _ in 0..aliases_count {
        let _key = input.read_string()?;
        aliases.push(read_template_alias_prefix(input)?);
    }
    Ok((aliases_count, aliases))
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexGraveyardTombstonePrefix {
    pub index_name: String,
    pub index_uuid: String,
    pub delete_date_in_millis: i64,
}

fn read_index_graveyard_tombstone_prefix(
    input: &mut StreamInput,
) -> Result<IndexGraveyardTombstonePrefix, ClusterStateDecodeError> {
    Ok(IndexGraveyardTombstonePrefix {
        index_name: input.read_string()?,
        index_uuid: input.read_string()?,
        delete_date_in_millis: input.read_i64()?,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SettingPrefix {
    pub key: String,
    pub value: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexTemplateMetadataPrefix {
    pub name: String,
    pub order: i32,
    pub patterns: Vec<String>,
    pub settings_count: usize,
    pub settings: Vec<SettingPrefix>,
    pub mappings_count: usize,
    pub mappings: Vec<TemplateMappingPrefix>,
    pub aliases_count: usize,
    pub aliases: Vec<TemplateAliasPrefix>,
    pub version: Option<i32>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexTemplateMetadataDiffPrefix {
    pub replacement_present: bool,
    pub replacement: Option<IndexTemplateMetadataPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TemplateMappingPrefix {
    pub name: String,
    pub crc32: i32,
    pub compressed_bytes_len: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TemplateAliasPrefix {
    pub alias: String,
    pub filter: Option<CompressedXContentPrefix>,
    pub index_routing: Option<String>,
    pub search_routing: Option<String>,
    pub write_index: Option<bool>,
    pub is_hidden: Option<bool>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CompressedXContentPrefix {
    pub crc32: i32,
    pub compressed_bytes_len: usize,
}

fn read_index_template_metadata_prefix(
    input: &mut StreamInput,
) -> Result<IndexTemplateMetadataPrefix, ClusterStateDecodeError> {
    let name = input.read_string()?;
    let order = input.read_i32()?;
    let pattern_count = read_non_negative_len(input)?;
    let mut patterns = Vec::with_capacity(pattern_count);
    for _ in 0..pattern_count {
        patterns.push(input.read_string()?);
    }
    let settings = read_settings_prefix(input, "metadata.templates.settings")?;
    let settings_count = settings.len();
    let mappings_count = read_non_negative_len(input)?;
    let mut mappings = Vec::with_capacity(mappings_count);
    for _ in 0..mappings_count {
        mappings.push(read_template_mapping_prefix(input)?);
    }
    let aliases_count = read_non_negative_len(input)?;
    let mut aliases = Vec::with_capacity(aliases_count);
    for _ in 0..aliases_count {
        aliases.push(read_template_alias_prefix(input)?);
    }
    let version = if input.read_bool()? {
        Some(input.read_vint()?)
    } else {
        None
    };

    Ok(IndexTemplateMetadataPrefix {
        name,
        order,
        patterns,
        settings_count,
        settings,
        mappings_count,
        mappings,
        aliases_count,
        aliases,
        version,
    })
}

fn read_template_mapping_prefix(
    input: &mut StreamInput,
) -> Result<TemplateMappingPrefix, ClusterStateDecodeError> {
    let name = input.read_string()?;
    let compressed = read_compressed_xcontent_prefix(input)?;
    Ok(TemplateMappingPrefix {
        name,
        crc32: compressed.crc32,
        compressed_bytes_len: compressed.compressed_bytes_len,
    })
}

fn read_template_alias_prefix(
    input: &mut StreamInput,
) -> Result<TemplateAliasPrefix, ClusterStateDecodeError> {
    let alias = input.read_string()?;
    let filter = if input.read_bool()? {
        Some(read_compressed_xcontent_prefix(input)?)
    } else {
        None
    };
    let index_routing = if input.read_bool()? {
        Some(input.read_string()?)
    } else {
        None
    };
    let search_routing = if input.read_bool()? {
        Some(input.read_string()?)
    } else {
        None
    };
    let write_index = read_optional_boolean(input)?;
    let is_hidden = read_optional_boolean(input)?;

    Ok(TemplateAliasPrefix {
        alias,
        filter,
        index_routing,
        search_routing,
        write_index,
        is_hidden,
    })
}

fn read_compressed_xcontent_prefix(
    input: &mut StreamInput,
) -> Result<CompressedXContentPrefix, ClusterStateDecodeError> {
    let crc32 = input.read_i32()?;
    let bytes = input.read_bytes_reference()?;
    Ok(CompressedXContentPrefix {
        crc32,
        compressed_bytes_len: bytes.len(),
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexMetadataPrefix {
    pub name: String,
    pub version: i64,
    pub mapping_version: i64,
    pub settings_version: i64,
    pub aliases_version: i64,
    pub routing_num_shards: i32,
    pub state_id: u8,
    pub settings_count: usize,
    pub index_uuid: Option<String>,
    pub number_of_shards: Option<i32>,
    pub number_of_replicas: Option<i32>,
    pub mapping_count: usize,
    pub mappings: Vec<IndexMappingPrefix>,
    pub alias_count: usize,
    pub aliases: Vec<TemplateAliasPrefix>,
    pub custom_data_count: usize,
    pub custom_data: Vec<IndexCustomDataPrefix>,
    pub in_sync_allocation_ids_count: usize,
    pub rollover_info_count: usize,
    pub rollover_infos: Vec<IndexRolloverInfoPrefix>,
    pub system: bool,
    pub context_present: bool,
    pub ingestion_status_present: bool,
    pub ingestion_paused: Option<bool>,
    pub split_shards_root_count: Option<usize>,
    pub split_shards_root_children: Vec<SplitShardRootChildrenPrefix>,
    pub split_shards_max_shard_id: Option<i32>,
    pub split_shards_in_progress_count: Option<usize>,
    pub split_shards_active_count: Option<usize>,
    pub split_shards_parent_to_child_count: Option<usize>,
    pub split_shards_parent_to_child: Vec<SplitShardParentToChildPrefix>,
    pub primary_terms_count: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SplitShardRootChildrenPrefix {
    pub root_shard_id: usize,
    pub children_count: usize,
    pub children: Vec<SplitShardRangePrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SplitShardParentToChildPrefix {
    pub parent_shard_id: i32,
    pub children_count: usize,
    pub children: Vec<SplitShardRangePrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SplitShardRangePrefix {
    pub shard_id: i32,
    pub start: i32,
    pub end: i32,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexMappingPrefix {
    pub mapping_type: String,
    pub crc32: i32,
    pub compressed_bytes_len: usize,
    pub routing_required: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexCustomDataPrefix {
    pub key: String,
    pub entries_count: usize,
    pub entries: Vec<SettingPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexRolloverInfoPrefix {
    pub alias: String,
    pub time: i64,
    pub met_conditions_count: usize,
    pub met_conditions: Vec<RolloverConditionPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RolloverConditionPrefix {
    pub name: String,
    pub value: Option<String>,
}

pub fn read_index_metadata_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<IndexMetadataPrefix, ClusterStateDecodeError> {
    let name = input.read_string()?;
    let version = input.read_i64()?;
    let mapping_version = input.read_vlong()?;
    let settings_version = input.read_vlong()?;
    let aliases_version = input.read_vlong()?;
    let routing_num_shards = input.read_i32()?;
    let state_id = input.read_byte()?;
    let settings = read_index_metadata_settings_prefix(input)?;

    let mut primary_terms_count = 0;
    if stream_version.id() < VERSION_3_6_0_ID {
        primary_terms_count = read_vlong_array_len(input)?;
    }

    let mapping_count = read_non_negative_len(input)?;
    let mut mappings = Vec::with_capacity(mapping_count);
    for _ in 0..mapping_count {
        mappings.push(read_index_mapping_prefix(input)?);
    }
    let alias_count = read_non_negative_len(input)?;
    let mut aliases = Vec::with_capacity(alias_count);
    for _ in 0..alias_count {
        aliases.push(read_template_alias_prefix(input)?);
    }
    let custom_data_count = read_non_negative_len(input)?;
    let mut custom_data = Vec::with_capacity(custom_data_count);
    for _ in 0..custom_data_count {
        custom_data.push(read_index_custom_data_prefix(input)?);
    }
    let in_sync_allocation_ids_count = read_in_sync_allocation_ids(input)?;
    let rollover_info_count = read_non_negative_len(input)?;
    let mut rollover_infos = Vec::with_capacity(rollover_info_count);
    for _ in 0..rollover_info_count {
        rollover_infos.push(read_index_rollover_info_prefix(input)?);
    }
    let system = input.read_bool()?;

    let context_present = if stream_version.id() >= VERSION_2_17_0_ID {
        read_absent_optional_writeable(input, "metadata.index.context")?
    } else {
        false
    };
    let ingestion_paused = if stream_version.id() >= VERSION_3_0_0_ID {
        read_optional_ingestion_status_prefix(input)?
    } else {
        None
    };
    let ingestion_status_present = ingestion_paused.is_some();

    let (
        split_shards_root_count,
        split_shards_root_children,
        split_shards_max_shard_id,
        split_shards_in_progress_count,
        split_shards_active_count,
        split_shards_parent_to_child_count,
        split_shards_parent_to_child,
    ) = if stream_version.id() >= VERSION_3_6_0_ID {
        let split_shards = read_split_shards_metadata_prefix(input)?;
        primary_terms_count = read_primary_terms_map_len(input)?;
        (
            Some(split_shards.root_count),
            split_shards.root_children,
            Some(split_shards.max_shard_id),
            Some(split_shards.in_progress_split_shard_ids_count),
            Some(split_shards.active_shard_ids_count),
            Some(split_shards.parent_to_child_count),
            split_shards.parent_to_child,
        )
    } else {
        (None, Vec::new(), None, None, None, None, Vec::new())
    };

    Ok(IndexMetadataPrefix {
        name,
        version,
        mapping_version,
        settings_version,
        aliases_version,
        routing_num_shards,
        state_id,
        settings_count: settings.settings_count,
        index_uuid: settings.index_uuid,
        number_of_shards: settings.number_of_shards,
        number_of_replicas: settings.number_of_replicas,
        mapping_count,
        mappings,
        alias_count,
        aliases,
        custom_data_count,
        custom_data,
        in_sync_allocation_ids_count,
        rollover_info_count,
        rollover_infos,
        system,
        context_present,
        ingestion_status_present,
        ingestion_paused,
        split_shards_root_count,
        split_shards_root_children,
        split_shards_max_shard_id,
        split_shards_in_progress_count,
        split_shards_active_count,
        split_shards_parent_to_child_count,
        split_shards_parent_to_child,
        primary_terms_count,
    })
}

fn read_index_metadata_diff_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<IndexMetadataDiffPrefix, ClusterStateDecodeError> {
    let name = input.read_string()?;
    let routing_num_shards = input.read_i32()?;
    let version = input.read_i64()?;
    let mapping_version = input.read_vlong()?;
    let settings_version = input.read_vlong()?;
    let aliases_version = input.read_vlong()?;
    let state_id = input.read_byte()?;
    let settings = read_index_metadata_settings_prefix(input)?;

    let mut primary_terms_count = 0;
    if stream_version.id() < VERSION_3_6_0_ID {
        primary_terms_count = read_vlong_array_len(input)?;
    }

    let (mappings, mapping_diffs) =
        read_index_mapping_map_diff_counts(input, "cluster_state.diff.metadata.index.mappings")?;
    let (aliases, alias_diffs) =
        read_index_alias_map_diff_counts(input, "cluster_state.diff.metadata.index.aliases")?;
    let (custom_data, custom_data_diffs) = read_index_custom_data_map_diff_counts(
        input,
        "cluster_state.diff.metadata.index.custom_data",
    )?;
    let (in_sync_allocation_ids, in_sync_allocation_ids_diff) =
        read_in_sync_allocation_ids_diff_counts(
            input,
            "cluster_state.diff.metadata.index.in_sync",
        )?;
    let (rollover_infos, rollover_info_diffs) = read_index_rollover_info_map_diff_counts(
        input,
        "cluster_state.diff.metadata.index.rollover_infos",
    )?;
    let system = input.read_bool()?;

    let context_present = if stream_version.id() >= VERSION_2_17_0_ID {
        read_absent_optional_writeable(input, "metadata.index.diff.context")?
    } else {
        false
    };
    let ingestion_paused = if stream_version.id() >= VERSION_3_0_0_ID {
        read_optional_ingestion_status_prefix(input)?
    } else {
        None
    };
    let ingestion_status_present = ingestion_paused.is_some();

    let (split_shards_replacement_present, split_shards_replacement) =
        if stream_version.id() >= VERSION_3_6_0_ID {
            let replacement_present = input.read_bool()?;
            let replacement = if replacement_present {
                Some(read_split_shards_metadata_prefix(input)?)
            } else {
                None
            };
            primary_terms_count = read_primary_terms_map_len(input)?;
            (Some(replacement_present), replacement)
        } else {
            (None, None)
        };

    Ok(IndexMetadataDiffPrefix {
        name,
        routing_num_shards,
        version,
        mapping_version,
        settings_version,
        aliases_version,
        state_id,
        settings_count: settings.settings_count,
        index_uuid: settings.index_uuid,
        number_of_shards: settings.number_of_shards,
        number_of_replicas: settings.number_of_replicas,
        mappings,
        mapping_diffs,
        aliases,
        alias_diffs,
        custom_data,
        custom_data_diffs,
        in_sync_allocation_ids,
        in_sync_allocation_ids_diff,
        rollover_infos,
        rollover_info_diffs,
        system,
        context_present,
        ingestion_status_present,
        ingestion_paused,
        split_shards_replacement_present,
        split_shards_replacement,
        primary_terms_count,
    })
}

fn read_index_rollover_info_prefix(
    input: &mut StreamInput,
) -> Result<IndexRolloverInfoPrefix, ClusterStateDecodeError> {
    let alias = input.read_string()?;
    let time = input.read_vlong()?;
    let met_conditions_count = read_non_negative_len(input)?;
    let mut met_conditions = Vec::with_capacity(met_conditions_count);
    for _ in 0..met_conditions_count {
        met_conditions.push(read_rollover_condition_prefix(input)?);
    }

    Ok(IndexRolloverInfoPrefix {
        alias,
        time,
        met_conditions_count,
        met_conditions,
    })
}

fn read_rollover_condition_prefix(
    input: &mut StreamInput,
) -> Result<RolloverConditionPrefix, ClusterStateDecodeError> {
    let name = input.read_string()?;
    let value = match name.as_str() {
        "max_docs" => Some(input.read_i64()?.to_string()),
        "max_age" => Some(input.read_i64()?.to_string()),
        "max_size" => Some(input.read_vlong()?.to_string()),
        _ => {
            return Err(ClusterStateDecodeError::UnsupportedNamedWriteable {
                section: "metadata.index.rollover_infos.met_conditions",
                name,
            })
        }
    };

    Ok(RolloverConditionPrefix { name, value })
}

fn read_index_custom_data_prefix(
    input: &mut StreamInput,
) -> Result<IndexCustomDataPrefix, ClusterStateDecodeError> {
    let key = input.read_string()?;
    let entries = read_string_map_prefix(input, "metadata.index.custom_data")?;
    Ok(IndexCustomDataPrefix {
        key,
        entries_count: entries.len(),
        entries,
    })
}

fn read_index_mapping_prefix(
    input: &mut StreamInput,
) -> Result<IndexMappingPrefix, ClusterStateDecodeError> {
    let mapping_type = input.read_string()?;
    let compressed = read_compressed_xcontent_prefix(input)?;
    let routing_required = input.read_bool()?;
    Ok(IndexMappingPrefix {
        mapping_type,
        crc32: compressed.crc32,
        compressed_bytes_len: compressed.compressed_bytes_len,
        routing_required,
    })
}

struct IndexMetadataSettingsPrefix {
    settings_count: usize,
    index_uuid: Option<String>,
    number_of_shards: Option<i32>,
    number_of_replicas: Option<i32>,
}

fn read_index_metadata_settings_prefix(
    input: &mut StreamInput,
) -> Result<IndexMetadataSettingsPrefix, ClusterStateDecodeError> {
    let settings_count = read_non_negative_len(input)?;
    let mut index_uuid = None;
    let mut number_of_shards = None;
    let mut number_of_replicas = None;

    for _ in 0..settings_count {
        let key = input.read_string()?;
        let value = read_generic_setting_value(input, "metadata.index.settings")?;
        match key.as_str() {
            "index.uuid" => index_uuid = value,
            "index.number_of_shards" => {
                number_of_shards = parse_i32_setting(value.as_deref(), "index.number_of_shards")?;
            }
            "index.number_of_replicas" => {
                number_of_replicas =
                    parse_i32_setting(value.as_deref(), "index.number_of_replicas")?;
            }
            _ => {}
        }
    }

    Ok(IndexMetadataSettingsPrefix {
        settings_count,
        index_uuid,
        number_of_shards,
        number_of_replicas,
    })
}

fn read_generic_setting_value(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<Option<String>, ClusterStateDecodeError> {
    let type_id = input.read_byte()? as i8;
    match type_id {
        -1 => Ok(None),
        0 => Ok(Some(input.read_string()?)),
        1 => Ok(Some(input.read_i32()?.to_string())),
        2 => Ok(Some(input.read_i64()?.to_string())),
        4 => Ok(Some(read_f64(input)?.to_string())),
        5 => Ok(Some(input.read_bool()?.to_string())),
        other => Err(ClusterStateDecodeError::UnsupportedGenericValue {
            section,
            type_id: other,
        }),
    }
}

fn parse_i32_setting(
    value: Option<&str>,
    name: &'static str,
) -> Result<Option<i32>, ClusterStateDecodeError> {
    match value {
        Some(value) => value.parse::<i32>().map(Some).map_err(|_| {
            ClusterStateDecodeError::InvalidSettingInteger {
                name,
                value: value.to_string(),
            }
        }),
        None => Ok(None),
    }
}

fn read_in_sync_allocation_ids(input: &mut StreamInput) -> Result<usize, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    for _ in 0..count {
        let _shard_id = input.read_vint()?;
        let allocation_id_count = read_non_negative_len(input)?;
        for _ in 0..allocation_id_count {
            let _allocation_id = input.read_string()?;
        }
    }
    Ok(count)
}

fn read_absent_optional_writeable(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<bool, ClusterStateDecodeError> {
    let present = input.read_bool()?;
    if present {
        return Err(ClusterStateDecodeError::UnsupportedSection(section));
    }
    Ok(present)
}

fn read_optional_boolean(input: &mut StreamInput) -> Result<Option<bool>, ClusterStateDecodeError> {
    match input.read_byte()? {
        0 => Ok(Some(false)),
        1 => Ok(Some(true)),
        2 => Ok(None),
        value => Err(ClusterStateDecodeError::InvalidOptionalBoolean(value)),
    }
}

fn read_optional_ingestion_status_prefix(
    input: &mut StreamInput,
) -> Result<Option<bool>, ClusterStateDecodeError> {
    if input.read_bool()? {
        Ok(Some(input.read_bool()?))
    } else {
        Ok(None)
    }
}

fn read_vlong_array_len(input: &mut StreamInput) -> Result<usize, ClusterStateDecodeError> {
    let len = read_non_negative_len(input)?;
    for _ in 0..len {
        let _value = input.read_vlong()?;
    }
    Ok(len)
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SplitShardsMetadataPrefix {
    pub root_count: usize,
    pub root_children: Vec<SplitShardRootChildrenPrefix>,
    pub max_shard_id: i32,
    pub in_progress_split_shard_ids_count: usize,
    pub active_shard_ids_count: usize,
    pub parent_to_child_count: usize,
    pub parent_to_child: Vec<SplitShardParentToChildPrefix>,
}

fn read_split_shards_metadata_prefix(
    input: &mut StreamInput,
) -> Result<SplitShardsMetadataPrefix, ClusterStateDecodeError> {
    let root_count = read_non_negative_len(input)?;
    let mut root_children = Vec::new();
    for root_shard_id in 0..root_count {
        if input.read_bool()? {
            let children_count = read_non_negative_len(input)?;
            let mut children = Vec::with_capacity(children_count);
            for _ in 0..children_count {
                children.push(read_split_shard_range_prefix(input)?);
            }
            root_children.push(SplitShardRootChildrenPrefix {
                root_shard_id,
                children_count,
                children,
            });
        }
    }
    let max_shard_id = input.read_vint()?;
    let in_progress_split_shard_ids_count = read_i32_collection(input)?;
    let active_shard_ids_count = read_i32_collection(input)?;
    let parent_to_child_count = read_non_negative_len(input)?;
    let mut parent_to_child = Vec::with_capacity(parent_to_child_count);
    for _ in 0..parent_to_child_count {
        let parent_shard_id = input.read_i32()?;
        let children_count = read_non_negative_len(input)?;
        let mut children = Vec::with_capacity(children_count);
        for _ in 0..children_count {
            children.push(read_split_shard_range_prefix(input)?);
        }
        parent_to_child.push(SplitShardParentToChildPrefix {
            parent_shard_id,
            children_count,
            children,
        });
    }
    Ok(SplitShardsMetadataPrefix {
        root_count,
        root_children,
        max_shard_id,
        in_progress_split_shard_ids_count,
        active_shard_ids_count,
        parent_to_child_count,
        parent_to_child,
    })
}

fn read_split_shard_range_prefix(
    input: &mut StreamInput,
) -> Result<SplitShardRangePrefix, ClusterStateDecodeError> {
    Ok(SplitShardRangePrefix {
        shard_id: input.read_vint()?,
        start: input.read_i32()?,
        end: input.read_i32()?,
    })
}

fn read_i32_collection(input: &mut StreamInput) -> Result<usize, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    for _ in 0..count {
        let _value = input.read_i32()?;
    }
    Ok(count)
}

fn read_primary_terms_map_len(input: &mut StreamInput) -> Result<usize, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    for _ in 0..count {
        let _shard_id = input.read_i32()?;
        let _term = input.read_i64()?;
    }
    Ok(count)
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RoutingTablePrefix {
    pub version: i64,
    pub index_routing_table_count: usize,
    pub indices: Vec<IndexRoutingTablePrefix>,
}

pub fn read_routing_table_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<RoutingTablePrefix, ClusterStateDecodeError> {
    let version = input.read_i64()?;
    let index_routing_table_count = read_non_negative_len(input)?;
    let mut indices = Vec::with_capacity(index_routing_table_count);
    for _ in 0..index_routing_table_count {
        indices.push(read_index_routing_table_prefix(input, stream_version)?);
    }
    Ok(RoutingTablePrefix {
        version,
        index_routing_table_count,
        indices,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexRoutingTablePrefix {
    pub index_name: String,
    pub index_uuid: String,
    pub shard_table_count: usize,
    pub shards: Vec<IndexShardRoutingTablePrefix>,
}

pub fn read_index_routing_table_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<IndexRoutingTablePrefix, ClusterStateDecodeError> {
    let index_name = input.read_string()?;
    let index_uuid = input.read_string()?;
    let shard_table_count = read_non_negative_len(input)?;
    let mut shards = Vec::with_capacity(shard_table_count);
    for _ in 0..shard_table_count {
        shards.push(read_index_shard_routing_table_prefix(
            input,
            stream_version,
        )?);
    }

    Ok(IndexRoutingTablePrefix {
        index_name,
        index_uuid,
        shard_table_count,
        shards,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexShardRoutingTablePrefix {
    pub shard_id: i32,
    pub shard_routing_count: usize,
    pub shard_routings: Vec<ShardRoutingPrefix>,
}

fn read_index_shard_routing_table_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<IndexShardRoutingTablePrefix, ClusterStateDecodeError> {
    let shard_id = input.read_vint()?;
    let shard_routing_count = read_non_negative_len(input)?;
    let mut shard_routings = Vec::with_capacity(shard_routing_count);
    for _ in 0..shard_routing_count {
        shard_routings.push(read_shard_routing_prefix(input, stream_version)?);
    }

    Ok(IndexShardRoutingTablePrefix {
        shard_id,
        shard_routing_count,
        shard_routings,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ShardRoutingPrefix {
    pub current_node_id: Option<String>,
    pub relocating_node_id: Option<String>,
    pub primary: bool,
    pub search_only: bool,
    pub state: ShardRoutingStatePrefix,
    pub recovery_source_type: Option<RecoverySourceTypePrefix>,
    pub recovery_source_bootstrap_new_history_uuid: Option<bool>,
    pub snapshot_recovery_source: Option<SnapshotRecoverySourcePrefix>,
    pub remote_store_recovery_source: Option<RemoteStoreRecoverySourcePrefix>,
    pub unassigned_info: Option<UnassignedInfoPrefix>,
    pub allocation_id_present: bool,
    pub allocation_id: Option<AllocationIdPrefix>,
    pub expected_shard_size: Option<i64>,
}

#[derive(Copy, Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum ShardRoutingStatePrefix {
    Unassigned,
    Initializing,
    Started,
    Relocating,
    Splitting,
}

#[derive(Copy, Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum RecoverySourceTypePrefix {
    EmptyStore,
    ExistingStore,
    Peer,
    Snapshot,
    LocalShards,
    RemoteStore,
    InPlaceSplitShard,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotRecoverySourcePrefix {
    pub restore_uuid: String,
    pub repository: String,
    pub snapshot_name: String,
    pub snapshot_uuid: String,
    pub version_id: i32,
    pub index_name: String,
    pub index_id: String,
    pub index_shard_path_type: Option<i32>,
    pub is_searchable_snapshot: Option<bool>,
    pub remote_store_index_shallow_copy: Option<bool>,
    pub source_remote_store_repository: Option<String>,
    pub source_remote_translog_repository: Option<String>,
    pub pinned_timestamp: Option<i64>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RemoteStoreRecoverySourcePrefix {
    pub restore_uuid: String,
    pub version_id: i32,
    pub index_name: String,
    pub index_id: String,
    pub index_shard_path_type: Option<i32>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct UnassignedInfoPrefix {
    pub reason_id: u8,
    pub unassigned_time_millis: i64,
    pub delayed: bool,
    pub message: Option<String>,
    pub failure: Option<UnassignedFailurePrefix>,
    pub failed_allocations: i32,
    pub last_allocation_status_id: u8,
    pub failed_node_ids_count: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct UnassignedFailurePrefix {
    pub class_name: String,
    pub message: Option<String>,
    pub summary: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct AllocationIdPrefix {
    pub id: String,
    pub relocation_id: Option<String>,
    pub split_child_allocation_ids_count: Option<usize>,
    pub parent_allocation_id: Option<String>,
}

fn read_shard_routing_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<ShardRoutingPrefix, ClusterStateDecodeError> {
    let current_node_id = input.read_optional_string()?;
    let relocating_node_id = input.read_optional_string()?;
    let primary = input.read_bool()?;
    let search_only = if stream_version.id() >= VERSION_2_17_0_ID {
        input.read_bool()?
    } else {
        false
    };
    let state = read_shard_routing_state(input)?;
    let recovery_source_type = match state {
        ShardRoutingStatePrefix::Unassigned | ShardRoutingStatePrefix::Initializing => {
            Some(read_recovery_source_type_prefix(input)?)
        }
        ShardRoutingStatePrefix::Started
        | ShardRoutingStatePrefix::Relocating
        | ShardRoutingStatePrefix::Splitting => None,
    };
    let recovery_source_bootstrap_new_history_uuid =
        if recovery_source_type == Some(RecoverySourceTypePrefix::ExistingStore) {
            Some(input.read_bool()?)
        } else {
            None
        };
    let snapshot_recovery_source =
        if recovery_source_type == Some(RecoverySourceTypePrefix::Snapshot) {
            Some(read_snapshot_recovery_source_prefix(input, stream_version)?)
        } else {
            None
        };
    let remote_store_recovery_source =
        if recovery_source_type == Some(RecoverySourceTypePrefix::RemoteStore) {
            Some(read_remote_store_recovery_source_prefix(
                input,
                stream_version,
            )?)
        } else {
            None
        };
    let unassigned_info = if input.read_bool()? {
        Some(read_unassigned_info_prefix(input)?)
    } else {
        None
    };
    let allocation_id_present = input.read_bool()?;
    let allocation_id = if allocation_id_present {
        Some(read_allocation_id_prefix(input, stream_version)?)
    } else {
        None
    };
    let expected_shard_size = match state {
        ShardRoutingStatePrefix::Initializing
        | ShardRoutingStatePrefix::Relocating
        | ShardRoutingStatePrefix::Splitting => Some(input.read_i64()?),
        ShardRoutingStatePrefix::Unassigned | ShardRoutingStatePrefix::Started => None,
    };

    Ok(ShardRoutingPrefix {
        current_node_id,
        relocating_node_id,
        primary,
        search_only,
        state,
        recovery_source_type,
        recovery_source_bootstrap_new_history_uuid,
        snapshot_recovery_source,
        remote_store_recovery_source,
        unassigned_info,
        allocation_id_present,
        allocation_id,
        expected_shard_size,
    })
}

fn read_allocation_id_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<AllocationIdPrefix, ClusterStateDecodeError> {
    let id = input.read_string()?;
    let relocation_id = input.read_optional_string()?;
    let (split_child_allocation_ids_count, parent_allocation_id) =
        if stream_version.id() >= VERSION_3_7_0_ID {
            (
                Some(read_optional_string_collection_len(input)?),
                input.read_optional_string()?,
            )
        } else {
            (None, None)
        };

    Ok(AllocationIdPrefix {
        id,
        relocation_id,
        split_child_allocation_ids_count,
        parent_allocation_id,
    })
}

fn read_optional_string_collection_len(
    input: &mut StreamInput,
) -> Result<usize, ClusterStateDecodeError> {
    if input.read_bool()? {
        let len = read_non_negative_len(input)?;
        for _ in 0..len {
            let _value = input.read_string()?;
        }
        Ok(len)
    } else {
        Ok(0)
    }
}

fn read_string_list(input: &mut StreamInput) -> Result<Vec<String>, ClusterStateDecodeError> {
    let len = read_non_negative_len(input)?;
    let mut values = Vec::with_capacity(len);
    for _ in 0..len {
        values.push(input.read_string()?);
    }
    Ok(values)
}

fn read_optional_string_list(
    input: &mut StreamInput,
) -> Result<Option<Vec<String>>, ClusterStateDecodeError> {
    if input.read_bool()? {
        Ok(Some(read_string_list(input)?))
    } else {
        Ok(None)
    }
}

fn read_optional_vlong(input: &mut StreamInput) -> Result<Option<i64>, ClusterStateDecodeError> {
    if input.read_bool()? {
        Ok(Some(input.read_vlong()?))
    } else {
        Ok(None)
    }
}

fn read_optional_long(input: &mut StreamInput) -> Result<Option<i64>, ClusterStateDecodeError> {
    if input.read_bool()? {
        Ok(Some(input.read_i64()?))
    } else {
        Ok(None)
    }
}

fn read_zlong(input: &mut StreamInput) -> Result<i64, ClusterStateDecodeError> {
    let value = input.read_vlong()?;
    Ok((value >> 1) ^ -(value & 1))
}

fn read_f64(input: &mut StreamInput) -> Result<f64, ClusterStateDecodeError> {
    Ok(f64::from_bits(input.read_i64()? as u64))
}

fn read_shard_routing_state(
    input: &mut StreamInput,
) -> Result<ShardRoutingStatePrefix, ClusterStateDecodeError> {
    let state = input.read_byte()?;
    match state {
        1 => Ok(ShardRoutingStatePrefix::Unassigned),
        2 => Ok(ShardRoutingStatePrefix::Initializing),
        3 => Ok(ShardRoutingStatePrefix::Started),
        4 => Ok(ShardRoutingStatePrefix::Relocating),
        5 => Ok(ShardRoutingStatePrefix::Splitting),
        other => Err(ClusterStateDecodeError::InvalidShardRoutingState(other)),
    }
}

fn read_recovery_source_type_prefix(
    input: &mut StreamInput,
) -> Result<RecoverySourceTypePrefix, ClusterStateDecodeError> {
    let type_id = input.read_byte()?;
    match type_id {
        0 => Ok(RecoverySourceTypePrefix::EmptyStore),
        1 => Ok(RecoverySourceTypePrefix::ExistingStore),
        2 => Ok(RecoverySourceTypePrefix::Peer),
        3 => Ok(RecoverySourceTypePrefix::Snapshot),
        4 => Ok(RecoverySourceTypePrefix::LocalShards),
        5 => Ok(RecoverySourceTypePrefix::RemoteStore),
        6 => Ok(RecoverySourceTypePrefix::InPlaceSplitShard),
        other => Err(ClusterStateDecodeError::InvalidRecoverySourceType(other)),
    }
}

fn read_snapshot_recovery_source_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<SnapshotRecoverySourcePrefix, ClusterStateDecodeError> {
    let restore_uuid = input.read_string()?;
    let repository = input.read_string()?;
    let snapshot_name = input.read_string()?;
    let snapshot_uuid = input.read_string()?;
    let version_id = input.read_vint()?;
    let index_name = input.read_string()?;
    let index_id = input.read_string()?;
    let index_shard_path_type = if stream_version.on_or_after(Version::from_id(VERSION_2_17_0_ID)) {
        Some(input.read_vint()?)
    } else {
        None
    };
    let is_searchable_snapshot = if stream_version.on_or_after(Version::from_id(VERSION_2_7_0_ID)) {
        Some(input.read_bool()?)
    } else {
        None
    };
    let (remote_store_index_shallow_copy, source_remote_store_repository) =
        if stream_version.on_or_after(Version::from_id(VERSION_2_9_0_ID)) {
            (Some(input.read_bool()?), input.read_optional_string()?)
        } else {
            (None, None)
        };
    let (source_remote_translog_repository, pinned_timestamp) =
        if stream_version.on_or_after(Version::from_id(VERSION_2_17_0_ID)) {
            (input.read_optional_string()?, Some(input.read_i64()?))
        } else {
            (None, None)
        };

    Ok(SnapshotRecoverySourcePrefix {
        restore_uuid,
        repository,
        snapshot_name,
        snapshot_uuid,
        version_id,
        index_name,
        index_id,
        index_shard_path_type,
        is_searchable_snapshot,
        remote_store_index_shallow_copy,
        source_remote_store_repository,
        source_remote_translog_repository,
        pinned_timestamp,
    })
}

fn read_remote_store_recovery_source_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<RemoteStoreRecoverySourcePrefix, ClusterStateDecodeError> {
    let restore_uuid = input.read_string()?;
    let version_id = input.read_vint()?;
    let index_name = input.read_string()?;
    let index_id = input.read_string()?;
    let index_shard_path_type = if stream_version.on_or_after(Version::from_id(VERSION_2_17_0_ID)) {
        Some(input.read_vint()?)
    } else {
        None
    };

    Ok(RemoteStoreRecoverySourcePrefix {
        restore_uuid,
        version_id,
        index_name,
        index_id,
        index_shard_path_type,
    })
}

fn read_unassigned_info_prefix(
    input: &mut StreamInput,
) -> Result<UnassignedInfoPrefix, ClusterStateDecodeError> {
    let reason_id = input.read_byte()?;
    let unassigned_time_millis = input.read_i64()?;
    let delayed = input.read_bool()?;
    let message = input.read_optional_string()?;
    let failure = read_exception(input)?.map(|failure| {
        let summary = failure.summary();
        UnassignedFailurePrefix {
            class_name: failure.class_name,
            message: failure.message,
            summary,
        }
    });
    let failed_allocations = input.read_vint()?;
    let last_allocation_status_id = input.read_byte()?;
    let failed_node_ids_count = read_non_negative_len(input)?;
    for _ in 0..failed_node_ids_count {
        let _node_id = input.read_string()?;
    }

    Ok(UnassignedInfoPrefix {
        reason_id,
        unassigned_time_millis,
        delayed,
        message,
        failure,
        failed_allocations,
        last_allocation_status_id,
        failed_node_ids_count,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DiscoveryNodesPrefix {
    pub cluster_manager_node_id: Option<String>,
    pub node_count: usize,
    pub nodes: Vec<DiscoveryNodePrefix>,
}

pub fn read_discovery_nodes_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<DiscoveryNodesPrefix, ClusterStateDecodeError> {
    let cluster_manager_node_id = if input.read_bool()? {
        Some(input.read_string()?)
    } else {
        None
    };
    let node_count = read_non_negative_len(input)?;
    let mut nodes = Vec::with_capacity(node_count);
    for _ in 0..node_count {
        nodes.push(read_discovery_node_prefix(input, stream_version)?);
    }

    Ok(DiscoveryNodesPrefix {
        cluster_manager_node_id,
        node_count,
        nodes,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DiscoveryNodePrefix {
    pub name: String,
    pub id: String,
    pub ephemeral_id: String,
    pub host_name: String,
    pub host_address: String,
    pub address: TransportAddressPrefix,
    pub stream_address: Option<TransportAddressPrefix>,
    pub attribute_count: usize,
    pub roles: Vec<DiscoveryNodeRolePrefix>,
    pub version: i32,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TransportAddressPrefix {
    pub ip: IpAddr,
    pub host: String,
    pub port: i32,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DiscoveryNodeRolePrefix {
    pub name: String,
    pub abbreviation: String,
    pub can_contain_data: bool,
}

pub fn read_discovery_node_prefix(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<DiscoveryNodePrefix, ClusterStateDecodeError> {
    let name = input.read_string()?;
    let id = input.read_string()?;
    let ephemeral_id = input.read_string()?;
    let host_name = input.read_string()?;
    let host_address = input.read_string()?;
    let address = read_transport_address(input)?;
    let stream_address = if stream_version.id() >= STREAM_ADDRESS_VERSION_ID {
        if input.read_bool()? {
            Some(read_transport_address(input)?)
        } else {
            None
        }
    } else {
        None
    };
    let attribute_count = read_non_negative_len(input)?;
    for _ in 0..attribute_count {
        let _key = input.read_string()?;
        let _value = input.read_string()?;
    }

    let role_count = read_non_negative_len(input)?;
    let mut roles = Vec::with_capacity(role_count);
    for _ in 0..role_count {
        roles.push(DiscoveryNodeRolePrefix {
            name: input.read_string()?,
            abbreviation: input.read_string()?,
            can_contain_data: input.read_bool()?,
        });
    }
    let version = input.read_vint()?;

    Ok(DiscoveryNodePrefix {
        name,
        id,
        ephemeral_id,
        host_name,
        host_address,
        address,
        stream_address,
        attribute_count,
        roles,
        version,
    })
}

fn read_transport_address(
    input: &mut StreamInput,
) -> Result<TransportAddressPrefix, ClusterStateDecodeError> {
    let len = input.read_byte()? as usize;
    let raw = input.read_bytes(len)?;
    let ip = match len {
        4 => IpAddr::V4(Ipv4Addr::new(raw[0], raw[1], raw[2], raw[3])),
        16 => {
            let mut octets = [0u8; 16];
            octets.copy_from_slice(&raw);
            IpAddr::V6(Ipv6Addr::from(octets))
        }
        other => return Err(ClusterStateDecodeError::InvalidIpLength(other)),
    };
    let host = input.read_string()?;
    let port = input.read_i32()?;
    Ok(TransportAddressPrefix { ip, host, port })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterBlocksPrefix {
    pub global_block_count: usize,
    pub global_blocks: Vec<ClusterBlockPrefix>,
    pub index_block_count: usize,
    pub index_blocks: Vec<IndexClusterBlocksPrefix>,
}

pub fn read_cluster_blocks_prefix(
    input: &mut StreamInput,
) -> Result<ClusterBlocksPrefix, ClusterStateDecodeError> {
    let global_block_count = read_non_negative_len(input)?;
    let mut global_blocks = Vec::with_capacity(global_block_count);
    for _ in 0..global_block_count {
        global_blocks.push(read_cluster_block_prefix(input)?);
    }

    let index_block_count = read_non_negative_len(input)?;
    let mut index_blocks = Vec::with_capacity(index_block_count);
    for _ in 0..index_block_count {
        let index_name = input.read_string()?;
        let block_count = read_non_negative_len(input)?;
        let mut blocks = Vec::with_capacity(block_count);
        for _ in 0..block_count {
            blocks.push(read_cluster_block_prefix(input)?);
        }
        index_blocks.push(IndexClusterBlocksPrefix {
            index_name,
            block_count,
            blocks,
        });
    }

    Ok(ClusterBlocksPrefix {
        global_block_count,
        global_blocks,
        index_block_count,
        index_blocks,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexClusterBlocksPrefix {
    pub index_name: String,
    pub block_count: usize,
    pub blocks: Vec<ClusterBlockPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterBlockPrefix {
    pub id: i32,
    pub uuid: Option<String>,
    pub description: String,
    pub levels: Vec<ClusterBlockLevelPrefix>,
    pub retryable: bool,
    pub disable_state_persistence: bool,
    pub status: String,
    pub allow_release_resources: bool,
}

#[derive(Copy, Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum ClusterBlockLevelPrefix {
    Read,
    Write,
    MetadataRead,
    MetadataWrite,
    CreateIndex,
}

pub fn read_cluster_block_prefix(
    input: &mut StreamInput,
) -> Result<ClusterBlockPrefix, ClusterStateDecodeError> {
    let id = input.read_vint()?;
    let uuid = input.read_optional_string()?;
    let description = input.read_string()?;
    let levels = read_cluster_block_level_set(input)?;
    let retryable = input.read_bool()?;
    let disable_state_persistence = input.read_bool()?;
    let status = input.read_string()?;
    let allow_release_resources = input.read_bool()?;

    Ok(ClusterBlockPrefix {
        id,
        uuid,
        description,
        levels,
        retryable,
        disable_state_persistence,
        status,
        allow_release_resources,
    })
}

fn read_cluster_block_level_set(
    input: &mut StreamInput,
) -> Result<Vec<ClusterBlockLevelPrefix>, ClusterStateDecodeError> {
    let len = read_non_negative_len(input)?;
    let mut levels = Vec::with_capacity(len);
    for _ in 0..len {
        let ordinal = input.read_vint()?;
        levels.push(match ordinal {
            0 => ClusterBlockLevelPrefix::Read,
            1 => ClusterBlockLevelPrefix::Write,
            2 => ClusterBlockLevelPrefix::MetadataRead,
            3 => ClusterBlockLevelPrefix::MetadataWrite,
            4 => ClusterBlockLevelPrefix::CreateIndex,
            other => return Err(ClusterStateDecodeError::InvalidClusterBlockLevel(other)),
        });
    }
    Ok(levels)
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterStateTailPrefix {
    pub custom_count: usize,
    pub custom_names: Vec<String>,
    pub repository_cleanup: Option<RepositoryCleanupInProgressPrefix>,
    pub snapshot_deletions: Option<SnapshotDeletionsInProgressPrefix>,
    pub restore: Option<RestoreInProgressPrefix>,
    pub snapshots: Option<SnapshotsInProgressPrefix>,
    pub minimum_cluster_manager_nodes_on_publishing_cluster_manager: i32,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ClusterStateCustomKind {
    RepositoryCleanup,
    SnapshotDeletions,
    Restore,
    Snapshots,
}

const CLUSTER_STATE_CUSTOM_DISPATCH: &[(&str, ClusterStateCustomKind)] = &[
    (
        "repository_cleanup",
        ClusterStateCustomKind::RepositoryCleanup,
    ),
    (
        "snapshot_deletions",
        ClusterStateCustomKind::SnapshotDeletions,
    ),
    ("restore", ClusterStateCustomKind::Restore),
    ("snapshots", ClusterStateCustomKind::Snapshots),
];

fn cluster_state_custom_kind(name: &str) -> Option<ClusterStateCustomKind> {
    CLUSTER_STATE_CUSTOM_DISPATCH
        .iter()
        .find_map(|(candidate, kind)| (*candidate == name).then_some(*kind))
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RepositoryCleanupInProgressPrefix {
    pub entry_count: usize,
    pub entries: Vec<RepositoryCleanupEntryPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RepositoryCleanupEntryPrefix {
    pub repository: String,
    pub repository_state_id: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotDeletionsInProgressPrefix {
    pub entry_count: usize,
    pub entries: Vec<SnapshotDeletionEntryPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotDeletionEntryPrefix {
    pub repository: String,
    pub snapshots_count: usize,
    pub snapshots: Vec<SnapshotIdPrefix>,
    pub start_time: i64,
    pub repository_state_id: i64,
    pub state_id: u8,
    pub uuid: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotIdPrefix {
    pub name: String,
    pub uuid: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestoreInProgressPrefix {
    pub entry_count: usize,
    pub entries: Vec<RestoreEntryPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestoreEntryPrefix {
    pub uuid: String,
    pub repository: String,
    pub snapshot_name: String,
    pub snapshot_uuid: String,
    pub state_id: u8,
    pub indices_count: usize,
    pub indices: Vec<String>,
    pub shard_status_count: usize,
    pub shard_statuses: Vec<RestoreShardStatusPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestoreShardStatusPrefix {
    pub index_name: String,
    pub index_uuid: String,
    pub shard_id: i32,
    pub node_id: Option<String>,
    pub state_id: u8,
    pub reason: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotsInProgressPrefix {
    pub entry_count: usize,
    pub entries: Vec<SnapshotInProgressEntryPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotInProgressEntryPrefix {
    pub repository: String,
    pub snapshot_name: String,
    pub snapshot_uuid: String,
    pub include_global_state: bool,
    pub partial: bool,
    pub state_id: u8,
    pub indices_count: usize,
    pub indices: Vec<SnapshotIndexIdPrefix>,
    pub start_time: i64,
    pub shard_status_count: usize,
    pub shard_statuses: Vec<SnapshotShardStatusPrefix>,
    pub repository_state_id: i64,
    pub failure: Option<String>,
    pub user_metadata_count: usize,
    pub user_metadata: Vec<GenericMapEntryPrefix>,
    pub version_id: i32,
    pub data_streams_count: usize,
    pub data_streams: Vec<String>,
    pub source: Option<SnapshotIdPrefix>,
    pub clone_count: usize,
    pub clones: Vec<SnapshotCloneStatusPrefix>,
    pub remote_store_index_shallow_copy: Option<bool>,
    pub remote_store_index_shallow_copy_v2: Option<bool>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct GenericMapEntryPrefix {
    pub key: String,
    pub value: GenericValuePrefix,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum GenericValuePrefix {
    Null,
    String(String),
    Int(i32),
    Long(i64),
    FloatBits(u32),
    DoubleBits(u64),
    Bool(bool),
    Bytes(Vec<u8>),
    Byte(i8),
    DateMillis(i64),
    Short(i16),
    List(Vec<GenericValuePrefix>),
    Array(Vec<GenericValuePrefix>),
    Map(Vec<GenericMapEntryPrefix>),
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotShardStatusPrefix {
    pub index_name: String,
    pub index_uuid: String,
    pub shard_id: i32,
    pub node_id: Option<String>,
    pub state_id: u8,
    pub generation: Option<String>,
    pub reason: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotCloneStatusPrefix {
    pub index_name: String,
    pub index_id: String,
    pub shard_path_type: Option<i32>,
    pub shard_id: i32,
    pub node_id: Option<String>,
    pub state_id: u8,
    pub generation: Option<String>,
    pub reason: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotIndexIdPrefix {
    pub name: String,
    pub id: String,
    pub shard_path_type: Option<i32>,
}

pub fn read_cluster_state_tail_prefix(
    input: &mut StreamInput,
) -> Result<ClusterStateTailPrefix, ClusterStateDecodeError> {
    let custom_count = read_non_negative_len(input)?;
    let mut custom_names = Vec::with_capacity(custom_count);
    let mut repository_cleanup = None;
    let mut snapshot_deletions = None;
    let mut restore = None;
    let mut snapshots = None;
    for _ in 0..custom_count {
        let name = input.read_string()?;
        custom_names.push(name.clone());
        match cluster_state_custom_kind(&name) {
            Some(ClusterStateCustomKind::RepositoryCleanup) => {
                repository_cleanup = Some(read_repository_cleanup_in_progress_prefix(input)?);
            }
            Some(ClusterStateCustomKind::SnapshotDeletions) => {
                snapshot_deletions = Some(read_snapshot_deletions_in_progress_prefix(input)?);
            }
            Some(ClusterStateCustomKind::Restore) => {
                restore = Some(read_restore_in_progress_prefix(input)?);
            }
            Some(ClusterStateCustomKind::Snapshots) => {
                snapshots = Some(read_snapshots_in_progress_prefix(input)?);
            }
            None => {
                return Err(ClusterStateDecodeError::UnsupportedNamedWriteable {
                    section: "cluster_state.customs",
                    name,
                });
            }
        }
    }
    let minimum_cluster_manager_nodes_on_publishing_cluster_manager = input.read_vint()?;

    Ok(ClusterStateTailPrefix {
        custom_count,
        custom_names,
        repository_cleanup,
        snapshot_deletions,
        restore,
        snapshots,
        minimum_cluster_manager_nodes_on_publishing_cluster_manager,
    })
}

fn read_repository_cleanup_in_progress_prefix(
    input: &mut StreamInput,
) -> Result<RepositoryCleanupInProgressPrefix, ClusterStateDecodeError> {
    let entry_count = read_non_negative_len(input)?;
    let mut entries = Vec::with_capacity(entry_count);
    for _ in 0..entry_count {
        entries.push(RepositoryCleanupEntryPrefix {
            repository: input.read_string()?,
            repository_state_id: input.read_i64()?,
        });
    }
    Ok(RepositoryCleanupInProgressPrefix {
        entry_count,
        entries,
    })
}

fn read_restore_in_progress_prefix(
    input: &mut StreamInput,
) -> Result<RestoreInProgressPrefix, ClusterStateDecodeError> {
    let entry_count = read_non_negative_len(input)?;
    let mut entries = Vec::with_capacity(entry_count);
    for _ in 0..entry_count {
        let uuid = input.read_string()?;
        let repository = input.read_string()?;
        let snapshot_name = input.read_string()?;
        let snapshot_uuid = input.read_string()?;
        let state_id = input.read_byte()?;
        let indices = read_string_list(input)?;
        let shard_status_count = read_non_negative_len(input)?;
        let mut shard_statuses = Vec::with_capacity(shard_status_count);
        for _ in 0..shard_status_count {
            shard_statuses.push(read_restore_shard_status_prefix(input)?);
        }
        entries.push(RestoreEntryPrefix {
            uuid,
            repository,
            snapshot_name,
            snapshot_uuid,
            state_id,
            indices_count: indices.len(),
            indices,
            shard_status_count,
            shard_statuses,
        });
    }
    Ok(RestoreInProgressPrefix {
        entry_count,
        entries,
    })
}

fn read_restore_shard_status_prefix(
    input: &mut StreamInput,
) -> Result<RestoreShardStatusPrefix, ClusterStateDecodeError> {
    Ok(RestoreShardStatusPrefix {
        index_name: input.read_string()?,
        index_uuid: input.read_string()?,
        shard_id: input.read_vint()?,
        node_id: input.read_optional_string()?,
        state_id: input.read_byte()?,
        reason: input.read_optional_string()?,
    })
}

fn read_snapshots_in_progress_prefix(
    input: &mut StreamInput,
) -> Result<SnapshotsInProgressPrefix, ClusterStateDecodeError> {
    let entry_count = read_non_negative_len(input)?;
    let mut entries = Vec::with_capacity(entry_count);
    for _ in 0..entry_count {
        let repository = input.read_string()?;
        let snapshot_name = input.read_string()?;
        let snapshot_uuid = input.read_string()?;
        let include_global_state = input.read_bool()?;
        let partial = input.read_bool()?;
        let state_id = input.read_byte()?;
        let indices_count = read_non_negative_len(input)?;
        let mut indices = Vec::with_capacity(indices_count);
        for _ in 0..indices_count {
            indices.push(read_snapshot_index_id_prefix(input)?);
        }
        let start_time = input.read_i64()?;
        let shard_status_count = read_non_negative_len(input)?;
        let mut shard_statuses = Vec::with_capacity(shard_status_count);
        for _ in 0..shard_status_count {
            shard_statuses.push(read_snapshot_shard_status_prefix(input)?);
        }
        let repository_state_id = input.read_i64()?;
        let failure = input.read_optional_string()?;
        let user_metadata =
            read_generic_map_prefix(input, "cluster_state.customs.snapshots.user_metadata")?;
        let version_id = input.read_vint()?;
        let data_streams = read_string_list(input)?;
        let source = if input.read_bool()? {
            Some(read_snapshot_id_prefix(input)?)
        } else {
            None
        };
        let clone_count = read_non_negative_len(input)?;
        let mut clones = Vec::with_capacity(clone_count);
        for _ in 0..clone_count {
            clones.push(read_snapshot_clone_status_prefix(input)?);
        }
        let stream_version = Version::from_id(DEFAULT_CLUSTER_STATE_STREAM_VERSION_ID);
        let remote_store_index_shallow_copy =
            if stream_version.on_or_after(Version::from_id(VERSION_2_9_0_ID)) {
                Some(input.read_bool()?)
            } else {
                None
            };
        let remote_store_index_shallow_copy_v2 =
            if stream_version.on_or_after(Version::from_id(VERSION_2_18_0_ID)) {
                Some(input.read_bool()?)
            } else {
                None
            };

        entries.push(SnapshotInProgressEntryPrefix {
            repository,
            snapshot_name,
            snapshot_uuid,
            include_global_state,
            partial,
            state_id,
            indices_count,
            indices,
            start_time,
            shard_status_count,
            shard_statuses,
            repository_state_id,
            failure,
            user_metadata_count: user_metadata.len(),
            user_metadata,
            version_id,
            data_streams_count: data_streams.len(),
            data_streams,
            source,
            clone_count,
            clones,
            remote_store_index_shallow_copy,
            remote_store_index_shallow_copy_v2,
        });
    }
    Ok(SnapshotsInProgressPrefix {
        entry_count,
        entries,
    })
}

fn read_snapshot_clone_status_prefix(
    input: &mut StreamInput,
) -> Result<SnapshotCloneStatusPrefix, ClusterStateDecodeError> {
    let index = read_snapshot_index_id_prefix(input)?;
    let shard_id = input.read_vint()?;
    let node_id = input.read_optional_string()?;
    let state_id = input.read_byte()?;
    let generation = input.read_optional_string()?;
    let reason = input.read_optional_string()?;
    Ok(SnapshotCloneStatusPrefix {
        index_name: index.name,
        index_id: index.id,
        shard_path_type: index.shard_path_type,
        shard_id,
        node_id,
        state_id,
        generation,
        reason,
    })
}

fn read_snapshot_shard_status_prefix(
    input: &mut StreamInput,
) -> Result<SnapshotShardStatusPrefix, ClusterStateDecodeError> {
    Ok(SnapshotShardStatusPrefix {
        index_name: input.read_string()?,
        index_uuid: input.read_string()?,
        shard_id: input.read_vint()?,
        node_id: input.read_optional_string()?,
        state_id: input.read_byte()?,
        generation: input.read_optional_string()?,
        reason: input.read_optional_string()?,
    })
}

fn read_snapshot_index_id_prefix(
    input: &mut StreamInput,
) -> Result<SnapshotIndexIdPrefix, ClusterStateDecodeError> {
    Ok(SnapshotIndexIdPrefix {
        name: input.read_string()?,
        id: input.read_string()?,
        shard_path_type: Some(input.read_vint()?),
    })
}

fn read_snapshot_id_prefix(
    input: &mut StreamInput,
) -> Result<SnapshotIdPrefix, ClusterStateDecodeError> {
    Ok(SnapshotIdPrefix {
        name: input.read_string()?,
        uuid: input.read_string()?,
    })
}

fn read_generic_map_prefix(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<Vec<GenericMapEntryPrefix>, ClusterStateDecodeError> {
    let type_id = input.read_byte()? as i8;
    read_generic_map_entries_prefix(input, section, type_id)
}

fn read_generic_map_entries_prefix(
    input: &mut StreamInput,
    section: &'static str,
    type_id: i8,
) -> Result<Vec<GenericMapEntryPrefix>, ClusterStateDecodeError> {
    if type_id == -1 {
        return Ok(Vec::new());
    }
    if type_id != 9 && type_id != 10 {
        return Err(ClusterStateDecodeError::UnsupportedGenericValue { section, type_id });
    }
    let len = read_non_negative_len(input)?;
    let mut entries = Vec::with_capacity(len);
    for _ in 0..len {
        entries.push(GenericMapEntryPrefix {
            key: input.read_string()?,
            value: read_generic_value_prefix(input, section)?,
        });
    }
    Ok(entries)
}

fn read_generic_value_prefix(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<GenericValuePrefix, ClusterStateDecodeError> {
    let type_id = input.read_byte()? as i8;
    match type_id {
        -1 => Ok(GenericValuePrefix::Null),
        0 => Ok(GenericValuePrefix::String(input.read_string()?)),
        1 => Ok(GenericValuePrefix::Int(input.read_i32()?)),
        2 => Ok(GenericValuePrefix::Long(input.read_i64()?)),
        3 => Ok(GenericValuePrefix::FloatBits(input.read_i32()? as u32)),
        4 => Ok(GenericValuePrefix::DoubleBits(input.read_i64()? as u64)),
        5 => Ok(GenericValuePrefix::Bool(input.read_bool()?)),
        6 => Ok(GenericValuePrefix::Bytes(read_byte_array_prefix(input)?)),
        7 => Ok(GenericValuePrefix::List(read_generic_value_list_prefix(
            input, section,
        )?)),
        8 => Ok(GenericValuePrefix::Array(read_generic_value_list_prefix(
            input, section,
        )?)),
        9 | 10 => Ok(GenericValuePrefix::Map(read_generic_map_entries_prefix(
            input, section, type_id,
        )?)),
        11 => Ok(GenericValuePrefix::Byte(input.read_byte()? as i8)),
        12 => Ok(GenericValuePrefix::DateMillis(input.read_i64()?)),
        16 => Ok(GenericValuePrefix::Short(read_i16(input)?)),
        _ => Err(ClusterStateDecodeError::UnsupportedGenericValue { section, type_id }),
    }
}

fn read_generic_value_list_prefix(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<Vec<GenericValuePrefix>, ClusterStateDecodeError> {
    let len = read_non_negative_len(input)?;
    let mut values = Vec::with_capacity(len);
    for _ in 0..len {
        values.push(read_generic_value_prefix(input, section)?);
    }
    Ok(values)
}

fn read_byte_array_prefix(input: &mut StreamInput) -> Result<Vec<u8>, ClusterStateDecodeError> {
    let len = read_non_negative_len(input)?;
    Ok(input.read_bytes(len)?.to_vec())
}

fn read_i16(input: &mut StreamInput) -> Result<i16, ClusterStateDecodeError> {
    let high = input.read_byte()? as u16;
    let low = input.read_byte()? as u16;
    Ok(((high << 8) | low) as i16)
}

fn read_snapshot_deletions_in_progress_prefix(
    input: &mut StreamInput,
) -> Result<SnapshotDeletionsInProgressPrefix, ClusterStateDecodeError> {
    let entry_count = read_non_negative_len(input)?;
    let mut entries = Vec::with_capacity(entry_count);
    for _ in 0..entry_count {
        let repository = input.read_string()?;
        let snapshots_count = read_non_negative_len(input)?;
        let mut snapshots = Vec::with_capacity(snapshots_count);
        for _ in 0..snapshots_count {
            snapshots.push(SnapshotIdPrefix {
                name: input.read_string()?,
                uuid: input.read_string()?,
            });
        }
        entries.push(SnapshotDeletionEntryPrefix {
            repository,
            snapshots_count,
            snapshots,
            start_time: input.read_vlong()?,
            repository_state_id: input.read_i64()?,
            state_id: input.read_byte()?,
            uuid: input.read_string()?,
        });
    }
    Ok(SnapshotDeletionsInProgressPrefix {
        entry_count,
        entries,
    })
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CoordinationMetadataPrefix {
    pub term: i64,
    pub last_committed_configuration: BTreeSet<String>,
    pub last_accepted_configuration: BTreeSet<String>,
    pub voting_config_exclusions: Vec<VotingConfigExclusion>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct VotingConfigExclusion {
    pub node_id: String,
    pub node_name: String,
}

pub fn read_coordination_metadata_prefix(
    input: &mut StreamInput,
) -> Result<CoordinationMetadataPrefix, ClusterStateDecodeError> {
    let term = input.read_i64()?;
    let last_committed_configuration = input.read_string_array()?.into_iter().collect();
    let last_accepted_configuration = input.read_string_array()?.into_iter().collect();
    let exclusion_count = read_non_negative_len(input)?;
    let mut voting_config_exclusions = Vec::with_capacity(exclusion_count);
    for _ in 0..exclusion_count {
        voting_config_exclusions.push(VotingConfigExclusion {
            node_id: input.read_string()?,
            node_name: input.read_string()?,
        });
    }

    Ok(CoordinationMetadataPrefix {
        term,
        last_committed_configuration,
        last_accepted_configuration,
        voting_config_exclusions,
    })
}

fn read_settings_prefix(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<Vec<SettingPrefix>, ClusterStateDecodeError> {
    let len = read_non_negative_len(input)?;
    let mut settings = Vec::with_capacity(len);
    for _ in 0..len {
        settings.push(SettingPrefix {
            key: input.read_string()?,
            value: read_generic_setting_value(input, section)?,
        });
    }
    Ok(settings)
}

fn read_string_map_prefix(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<Vec<SettingPrefix>, ClusterStateDecodeError> {
    let generic_type = input.read_byte()? as i8;
    if generic_type == -1 {
        return Ok(Vec::new());
    }
    if generic_type != 10 {
        return Err(ClusterStateDecodeError::UnsupportedGenericValue {
            section,
            type_id: generic_type,
        });
    }
    let len = read_non_negative_len(input)?;
    let mut entries = Vec::with_capacity(len);
    for _ in 0..len {
        entries.push(SettingPrefix {
            key: input.read_string()?,
            value: read_generic_setting_value(input, section)?,
        });
    }
    Ok(entries)
}

fn read_string_map_diff_envelope_prefix_from(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<StringMapDiffEnvelopePrefix, ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_keys = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_keys.push(input.read_string()?);
    }

    let diff_count = read_non_negative_len(input)?;
    if diff_count > 0 {
        let name = input.read_string()?;
        return Err(ClusterStateDecodeError::UnsupportedNamedWriteable { section, name });
    }

    let upsert_count = read_non_negative_len(input)?;
    if upsert_count > 0 {
        let name = input.read_string()?;
        return Err(ClusterStateDecodeError::UnsupportedNamedWriteable { section, name });
    }

    Ok(StringMapDiffEnvelopePrefix {
        delete_count,
        deleted_keys,
        diff_count,
        diff_keys: Vec::new(),
        upsert_count,
        upsert_keys: Vec::new(),
        index_metadata_diffs: Vec::new(),
        index_metadata_upserts: Vec::new(),
        index_routing_diffs: Vec::new(),
        index_routing_upserts: Vec::new(),
        index_template_diffs: Vec::new(),
        index_template_upserts: Vec::new(),
        repository_metadata_diffs: Vec::new(),
        repository_metadata_upserts: Vec::new(),
        component_template_diffs: Vec::new(),
        component_template_upserts: Vec::new(),
        composable_index_template_diffs: Vec::new(),
        composable_index_template_upserts: Vec::new(),
        data_stream_diffs: Vec::new(),
        data_stream_upserts: Vec::new(),
        ingest_upserts: Vec::new(),
        search_pipeline_upserts: Vec::new(),
        stored_script_upserts: Vec::new(),
        index_graveyard_tombstone_upserts: Vec::new(),
        persistent_task_upserts: Vec::new(),
        decommission_attribute_diffs: Vec::new(),
        decommission_attribute_upserts: Vec::new(),
        weighted_routing_diffs: Vec::new(),
        weighted_routing_upserts: Vec::new(),
        view_diffs: Vec::new(),
        view_upserts: Vec::new(),
        workload_group_diffs: Vec::new(),
        workload_group_upserts: Vec::new(),
        repository_cleanup_diffs: Vec::new(),
        repository_cleanup_upserts: Vec::new(),
        restore_diffs: Vec::new(),
        restore_upserts: Vec::new(),
        snapshot_deletions_diffs: Vec::new(),
        snapshot_deletions_upserts: Vec::new(),
        snapshots_diffs: Vec::new(),
        snapshots_upserts: Vec::new(),
        remaining_bytes_after_prefix: input.remaining(),
    })
}

fn read_routing_index_map_diff_envelope_prefix_from(
    input: &mut StreamInput,
    _section: &'static str,
    stream_version: Version,
) -> Result<StringMapDiffEnvelopePrefix, ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_keys = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_keys.push(input.read_string()?);
    }

    let diff_count = read_non_negative_len(input)?;
    let mut diff_keys = Vec::with_capacity(diff_count);
    let mut index_routing_diffs = Vec::with_capacity(diff_count);
    for _ in 0..diff_count {
        let key = input.read_string()?;
        diff_keys.push(key);
        let replacement_present = input.read_bool()?;
        let replacement = if replacement_present {
            Some(read_index_routing_table_prefix(input, stream_version)?)
        } else {
            None
        };
        index_routing_diffs.push(IndexRoutingTableDiffPrefix {
            replacement_present,
            replacement,
        });
    }

    let upsert_count = read_non_negative_len(input)?;
    let mut upsert_keys = Vec::with_capacity(upsert_count);
    let mut index_routing_upserts = Vec::with_capacity(upsert_count);
    for _ in 0..upsert_count {
        upsert_keys.push(input.read_string()?);
        index_routing_upserts.push(read_index_routing_table_prefix(input, stream_version)?);
    }

    Ok(StringMapDiffEnvelopePrefix {
        delete_count,
        deleted_keys,
        diff_count,
        diff_keys,
        upsert_count,
        upsert_keys,
        index_metadata_diffs: Vec::new(),
        index_metadata_upserts: Vec::new(),
        index_routing_diffs,
        index_routing_upserts,
        index_template_diffs: Vec::new(),
        index_template_upserts: Vec::new(),
        repository_metadata_diffs: Vec::new(),
        repository_metadata_upserts: Vec::new(),
        component_template_diffs: Vec::new(),
        component_template_upserts: Vec::new(),
        composable_index_template_diffs: Vec::new(),
        composable_index_template_upserts: Vec::new(),
        data_stream_diffs: Vec::new(),
        data_stream_upserts: Vec::new(),
        ingest_upserts: Vec::new(),
        search_pipeline_upserts: Vec::new(),
        stored_script_upserts: Vec::new(),
        index_graveyard_tombstone_upserts: Vec::new(),
        persistent_task_upserts: Vec::new(),
        decommission_attribute_diffs: Vec::new(),
        decommission_attribute_upserts: Vec::new(),
        weighted_routing_diffs: Vec::new(),
        weighted_routing_upserts: Vec::new(),
        view_diffs: Vec::new(),
        view_upserts: Vec::new(),
        workload_group_diffs: Vec::new(),
        workload_group_upserts: Vec::new(),
        repository_cleanup_diffs: Vec::new(),
        repository_cleanup_upserts: Vec::new(),
        restore_diffs: Vec::new(),
        restore_upserts: Vec::new(),
        snapshot_deletions_diffs: Vec::new(),
        snapshot_deletions_upserts: Vec::new(),
        snapshots_diffs: Vec::new(),
        snapshots_upserts: Vec::new(),
        remaining_bytes_after_prefix: input.remaining(),
    })
}

fn read_metadata_template_map_diff_envelope_prefix_from(
    input: &mut StreamInput,
    _section: &'static str,
) -> Result<StringMapDiffEnvelopePrefix, ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_keys = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_keys.push(input.read_string()?);
    }

    let diff_count = read_non_negative_len(input)?;
    let mut diff_keys = Vec::with_capacity(diff_count);
    let mut index_template_diffs = Vec::with_capacity(diff_count);
    for _ in 0..diff_count {
        let key = input.read_string()?;
        diff_keys.push(key);
        let replacement_present = input.read_bool()?;
        let replacement = if replacement_present {
            Some(read_index_template_metadata_prefix(input)?)
        } else {
            None
        };
        index_template_diffs.push(IndexTemplateMetadataDiffPrefix {
            replacement_present,
            replacement,
        });
    }

    let upsert_count = read_non_negative_len(input)?;
    let mut upsert_keys = Vec::with_capacity(upsert_count);
    let mut index_template_upserts = Vec::with_capacity(upsert_count);
    for _ in 0..upsert_count {
        upsert_keys.push(input.read_string()?);
        index_template_upserts.push(read_index_template_metadata_prefix(input)?);
    }

    Ok(StringMapDiffEnvelopePrefix {
        delete_count,
        deleted_keys,
        diff_count,
        diff_keys,
        upsert_count,
        upsert_keys,
        index_metadata_diffs: Vec::new(),
        index_metadata_upserts: Vec::new(),
        index_routing_diffs: Vec::new(),
        index_routing_upserts: Vec::new(),
        index_template_diffs,
        index_template_upserts,
        repository_metadata_diffs: Vec::new(),
        repository_metadata_upserts: Vec::new(),
        component_template_diffs: Vec::new(),
        component_template_upserts: Vec::new(),
        composable_index_template_diffs: Vec::new(),
        composable_index_template_upserts: Vec::new(),
        data_stream_diffs: Vec::new(),
        data_stream_upserts: Vec::new(),
        ingest_upserts: Vec::new(),
        search_pipeline_upserts: Vec::new(),
        stored_script_upserts: Vec::new(),
        index_graveyard_tombstone_upserts: Vec::new(),
        persistent_task_upserts: Vec::new(),
        decommission_attribute_diffs: Vec::new(),
        decommission_attribute_upserts: Vec::new(),
        weighted_routing_diffs: Vec::new(),
        weighted_routing_upserts: Vec::new(),
        view_diffs: Vec::new(),
        view_upserts: Vec::new(),
        workload_group_diffs: Vec::new(),
        workload_group_upserts: Vec::new(),
        repository_cleanup_diffs: Vec::new(),
        repository_cleanup_upserts: Vec::new(),
        restore_diffs: Vec::new(),
        restore_upserts: Vec::new(),
        snapshot_deletions_diffs: Vec::new(),
        snapshot_deletions_upserts: Vec::new(),
        snapshots_diffs: Vec::new(),
        snapshots_upserts: Vec::new(),
        remaining_bytes_after_prefix: input.remaining(),
    })
}

fn read_metadata_custom_map_diff_envelope_prefix_from(
    input: &mut StreamInput,
    section: &'static str,
    stream_version: Version,
) -> Result<StringMapDiffEnvelopePrefix, ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_keys = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_keys.push(input.read_string()?);
    }

    let diff_count = read_non_negative_len(input)?;
    let mut diff_keys = Vec::with_capacity(diff_count);
    let mut component_template_diffs = Vec::new();
    let mut composable_index_template_diffs = Vec::new();
    let mut data_stream_diffs = Vec::new();
    let mut view_diffs = Vec::new();
    let mut workload_group_diffs = Vec::new();
    let mut weighted_routing_diffs = Vec::new();
    let mut decommission_attribute_diffs = Vec::new();
    let mut repository_metadata_diffs = Vec::new();
    for _ in 0..diff_count {
        let key = input.read_string()?;
        diff_keys.push(key.clone());
        match key.as_str() {
            "component_template" => {
                component_template_diffs
                    .push(read_component_template_metadata_custom_diff_prefix(input)?);
            }
            "index_template" => {
                composable_index_template_diffs.push(
                    read_composable_index_template_metadata_custom_diff_prefix(input)?,
                );
            }
            "data_stream" => {
                data_stream_diffs.push(read_data_stream_metadata_custom_diff_prefix(input)?);
            }
            "view" => view_diffs.push(read_view_metadata_custom_diff_prefix(input)?),
            "queryGroups" => workload_group_diffs.push(
                read_workload_group_metadata_custom_diff_prefix(input, stream_version)?,
            ),
            "weighted_shard_routing" => {
                let replacement_present = input.read_bool()?;
                let replacement = if replacement_present {
                    Some(read_weighted_routing_metadata_prefix(input)?)
                } else {
                    None
                };
                weighted_routing_diffs.push(WeightedRoutingMetadataCustomDiffPrefix {
                    replacement_present,
                    replacement,
                });
            }
            "decommissionedAttribute" => {
                let replacement_present = input.read_bool()?;
                let replacement = if replacement_present {
                    Some(read_decommission_attribute_metadata_prefix(input)?)
                } else {
                    None
                };
                decommission_attribute_diffs.push(DecommissionAttributeMetadataCustomDiffPrefix {
                    replacement_present,
                    replacement,
                });
            }
            "repositories" => {
                repository_metadata_diffs.push(read_repositories_metadata_custom_diff_prefix(
                    input,
                    stream_version,
                )?);
            }
            _ => {
                return Err(ClusterStateDecodeError::UnsupportedNamedWriteable {
                    section,
                    name: key,
                });
            }
        }
    }

    let upsert_count = read_non_negative_len(input)?;
    let mut upsert_keys = Vec::with_capacity(upsert_count);
    let mut repository_metadata_upserts = Vec::new();
    let mut component_template_upserts = Vec::new();
    let mut composable_index_template_upserts = Vec::new();
    let mut data_stream_upserts = Vec::new();
    let mut ingest_upserts = Vec::new();
    let mut search_pipeline_upserts = Vec::new();
    let mut stored_script_upserts = Vec::new();
    let mut index_graveyard_tombstone_upserts = Vec::new();
    let mut persistent_task_upserts = Vec::new();
    let mut decommission_attribute_upserts = Vec::new();
    let mut weighted_routing_upserts = Vec::new();
    let mut view_upserts = Vec::new();
    let mut workload_group_upserts = Vec::new();
    for _ in 0..upsert_count {
        let key = input.read_string()?;
        upsert_keys.push(key.clone());
        match key.as_str() {
            "repositories" => {
                let repository_count = read_non_negative_len(input)?;
                repository_metadata_upserts.reserve(repository_count);
                for _ in 0..repository_count {
                    repository_metadata_upserts
                        .push(read_repository_metadata_prefix(input, stream_version)?);
                }
            }
            "component_template" => {
                let component_template_count = read_non_negative_len(input)?;
                component_template_upserts.reserve(component_template_count);
                for _ in 0..component_template_count {
                    component_template_upserts.push(read_component_template_prefix(input)?);
                }
            }
            "index_template" => {
                let index_template_count = read_non_negative_len(input)?;
                composable_index_template_upserts.reserve(index_template_count);
                for _ in 0..index_template_count {
                    composable_index_template_upserts
                        .push(read_composable_index_template_prefix(input)?);
                }
            }
            "data_stream" => {
                let data_stream_count = read_non_negative_len(input)?;
                data_stream_upserts.reserve(data_stream_count);
                for _ in 0..data_stream_count {
                    let _data_stream_key = input.read_string()?;
                    data_stream_upserts.push(read_data_stream_prefix(input)?);
                }
            }
            "ingest" => {
                let ingest_count = read_non_negative_len(input)?;
                ingest_upserts.reserve(ingest_count);
                for _ in 0..ingest_count {
                    ingest_upserts.push(read_ingest_pipeline_prefix(input)?);
                }
            }
            "search_pipeline" => {
                let search_pipeline_count = read_non_negative_len(input)?;
                search_pipeline_upserts.reserve(search_pipeline_count);
                for _ in 0..search_pipeline_count {
                    search_pipeline_upserts.push(read_search_pipeline_prefix(input)?);
                }
            }
            "stored_scripts" => {
                let stored_script_count = read_non_negative_len(input)?;
                stored_script_upserts.reserve(stored_script_count);
                for _ in 0..stored_script_count {
                    stored_script_upserts.push(read_stored_script_prefix(input)?);
                }
            }
            "index-graveyard" => {
                let tombstone_count = read_non_negative_len(input)?;
                index_graveyard_tombstone_upserts.reserve(tombstone_count);
                for _ in 0..tombstone_count {
                    index_graveyard_tombstone_upserts
                        .push(read_index_graveyard_tombstone_prefix(input)?);
                }
            }
            "persistent_tasks" => {
                let _last_allocation_id = input.read_i64()?;
                let persistent_task_count = read_non_negative_len(input)?;
                persistent_task_upserts.reserve(persistent_task_count);
                for _ in 0..persistent_task_count {
                    let map_key = input.read_string()?;
                    persistent_task_upserts.push(read_persistent_task_prefix(input, map_key)?);
                }
            }
            "decommissionedAttribute" => {
                decommission_attribute_upserts
                    .push(read_decommission_attribute_metadata_prefix(input)?);
            }
            "weighted_shard_routing" => {
                weighted_routing_upserts.push(read_weighted_routing_metadata_prefix(input)?);
            }
            "view" => {
                let view_count = read_non_negative_len(input)?;
                view_upserts.reserve(view_count);
                for _ in 0..view_count {
                    let _view_key = input.read_string()?;
                    view_upserts.push(read_view_metadata_prefix(input)?);
                }
            }
            "queryGroups" => {
                let workload_group_count = read_non_negative_len(input)?;
                workload_group_upserts.reserve(workload_group_count);
                for _ in 0..workload_group_count {
                    let _workload_group_key = input.read_string()?;
                    workload_group_upserts.push(read_workload_group_prefix(input, stream_version)?);
                }
            }
            _ => {
                return Err(ClusterStateDecodeError::UnsupportedNamedWriteable {
                    section,
                    name: key,
                });
            }
        }
    }

    Ok(StringMapDiffEnvelopePrefix {
        delete_count,
        deleted_keys,
        diff_count,
        diff_keys,
        upsert_count,
        upsert_keys,
        index_metadata_diffs: Vec::new(),
        index_metadata_upserts: Vec::new(),
        index_routing_diffs: Vec::new(),
        index_routing_upserts: Vec::new(),
        index_template_diffs: Vec::new(),
        index_template_upserts: Vec::new(),
        repository_metadata_diffs,
        repository_metadata_upserts,
        component_template_diffs,
        component_template_upserts,
        composable_index_template_diffs,
        composable_index_template_upserts,
        data_stream_diffs,
        data_stream_upserts,
        ingest_upserts,
        search_pipeline_upserts,
        stored_script_upserts,
        index_graveyard_tombstone_upserts,
        persistent_task_upserts,
        decommission_attribute_diffs,
        decommission_attribute_upserts,
        weighted_routing_diffs,
        weighted_routing_upserts,
        view_diffs,
        view_upserts,
        workload_group_diffs,
        workload_group_upserts,
        repository_cleanup_diffs: Vec::new(),
        repository_cleanup_upserts: Vec::new(),
        restore_diffs: Vec::new(),
        restore_upserts: Vec::new(),
        snapshot_deletions_diffs: Vec::new(),
        snapshot_deletions_upserts: Vec::new(),
        snapshots_diffs: Vec::new(),
        snapshots_upserts: Vec::new(),
        remaining_bytes_after_prefix: input.remaining(),
    })
}

fn read_cluster_state_custom_map_diff_envelope_prefix_from(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<StringMapDiffEnvelopePrefix, ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_keys = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_keys.push(input.read_string()?);
    }

    let diff_count = read_non_negative_len(input)?;
    let mut diff_keys = Vec::with_capacity(diff_count);
    let mut repository_cleanup_diffs = Vec::new();
    let mut restore_diffs = Vec::new();
    let mut snapshot_deletions_diffs = Vec::new();
    let mut snapshots_diffs = Vec::new();
    for _ in 0..diff_count {
        let key = input.read_string()?;
        diff_keys.push(key.clone());
        match key.as_str() {
            "repository_cleanup" => {
                let replacement_present = input.read_bool()?;
                let replacement = if replacement_present {
                    Some(read_repository_cleanup_in_progress_prefix(input)?)
                } else {
                    None
                };
                repository_cleanup_diffs.push(RepositoryCleanupNamedDiffPrefix {
                    replacement_present,
                    replacement,
                });
            }
            "restore" => {
                let replacement_present = input.read_bool()?;
                let replacement = if replacement_present {
                    Some(read_restore_in_progress_prefix(input)?)
                } else {
                    None
                };
                restore_diffs.push(RestoreInProgressNamedDiffPrefix {
                    replacement_present,
                    replacement,
                });
            }
            "snapshot_deletions" => {
                let replacement_present = input.read_bool()?;
                let replacement = if replacement_present {
                    Some(read_snapshot_deletions_in_progress_prefix(input)?)
                } else {
                    None
                };
                snapshot_deletions_diffs.push(SnapshotDeletionsInProgressNamedDiffPrefix {
                    replacement_present,
                    replacement,
                });
            }
            "snapshots" => {
                let replacement_present = input.read_bool()?;
                let replacement = if replacement_present {
                    Some(read_snapshots_in_progress_prefix(input)?)
                } else {
                    None
                };
                snapshots_diffs.push(SnapshotsInProgressNamedDiffPrefix {
                    replacement_present,
                    replacement,
                });
            }
            _ => {
                return Err(ClusterStateDecodeError::UnsupportedNamedWriteable {
                    section,
                    name: key,
                });
            }
        }
    }

    let upsert_count = read_non_negative_len(input)?;
    let mut upsert_keys = Vec::with_capacity(upsert_count);
    let mut repository_cleanup_upserts = Vec::new();
    let mut restore_upserts = Vec::new();
    let mut snapshot_deletions_upserts = Vec::new();
    let mut snapshots_upserts = Vec::new();
    for _ in 0..upsert_count {
        let key = input.read_string()?;
        upsert_keys.push(key.clone());
        match key.as_str() {
            "repository_cleanup" => {
                repository_cleanup_upserts.push(read_repository_cleanup_in_progress_prefix(input)?);
            }
            "restore" => restore_upserts.push(read_restore_in_progress_prefix(input)?),
            "snapshot_deletions" => {
                snapshot_deletions_upserts.push(read_snapshot_deletions_in_progress_prefix(input)?);
            }
            "snapshots" => snapshots_upserts.push(read_snapshots_in_progress_prefix(input)?),
            _ => {
                return Err(ClusterStateDecodeError::UnsupportedNamedWriteable {
                    section,
                    name: key,
                });
            }
        }
    }

    Ok(StringMapDiffEnvelopePrefix {
        delete_count,
        deleted_keys,
        diff_count,
        diff_keys,
        upsert_count,
        upsert_keys,
        index_metadata_diffs: Vec::new(),
        index_metadata_upserts: Vec::new(),
        index_routing_diffs: Vec::new(),
        index_routing_upserts: Vec::new(),
        index_template_diffs: Vec::new(),
        index_template_upserts: Vec::new(),
        repository_metadata_diffs: Vec::new(),
        repository_metadata_upserts: Vec::new(),
        component_template_diffs: Vec::new(),
        component_template_upserts: Vec::new(),
        composable_index_template_diffs: Vec::new(),
        composable_index_template_upserts: Vec::new(),
        data_stream_diffs: Vec::new(),
        data_stream_upserts: Vec::new(),
        ingest_upserts: Vec::new(),
        search_pipeline_upserts: Vec::new(),
        stored_script_upserts: Vec::new(),
        index_graveyard_tombstone_upserts: Vec::new(),
        persistent_task_upserts: Vec::new(),
        decommission_attribute_diffs: Vec::new(),
        decommission_attribute_upserts: Vec::new(),
        weighted_routing_diffs: Vec::new(),
        weighted_routing_upserts: Vec::new(),
        view_diffs: Vec::new(),
        view_upserts: Vec::new(),
        workload_group_diffs: Vec::new(),
        workload_group_upserts: Vec::new(),
        repository_cleanup_diffs,
        repository_cleanup_upserts,
        restore_diffs,
        restore_upserts,
        snapshot_deletions_diffs,
        snapshot_deletions_upserts,
        snapshots_diffs,
        snapshots_upserts,
        remaining_bytes_after_prefix: input.remaining(),
    })
}

fn read_metadata_index_map_diff_envelope_prefix_from(
    input: &mut StreamInput,
    _section: &'static str,
    stream_version: Version,
) -> Result<StringMapDiffEnvelopePrefix, ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_keys = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_keys.push(input.read_string()?);
    }

    let diff_count = read_non_negative_len(input)?;
    let mut diff_keys = Vec::with_capacity(diff_count);
    let mut index_metadata_diffs = Vec::with_capacity(diff_count);
    for _ in 0..diff_count {
        let key = input.read_string()?;
        diff_keys.push(key);
        index_metadata_diffs.push(read_index_metadata_diff_prefix(input, stream_version)?);
    }

    let upsert_count = read_non_negative_len(input)?;
    let mut upsert_keys = Vec::with_capacity(upsert_count);
    let mut index_metadata_upserts = Vec::with_capacity(upsert_count);
    for _ in 0..upsert_count {
        upsert_keys.push(input.read_string()?);
        index_metadata_upserts.push(read_index_metadata_prefix(input, stream_version)?);
    }

    Ok(StringMapDiffEnvelopePrefix {
        delete_count,
        deleted_keys,
        diff_count,
        diff_keys,
        upsert_count,
        upsert_keys,
        index_metadata_diffs,
        index_metadata_upserts,
        index_routing_diffs: Vec::new(),
        index_routing_upserts: Vec::new(),
        index_template_diffs: Vec::new(),
        index_template_upserts: Vec::new(),
        repository_metadata_diffs: Vec::new(),
        repository_metadata_upserts: Vec::new(),
        component_template_diffs: Vec::new(),
        component_template_upserts: Vec::new(),
        composable_index_template_diffs: Vec::new(),
        composable_index_template_upserts: Vec::new(),
        data_stream_diffs: Vec::new(),
        data_stream_upserts: Vec::new(),
        ingest_upserts: Vec::new(),
        search_pipeline_upserts: Vec::new(),
        stored_script_upserts: Vec::new(),
        index_graveyard_tombstone_upserts: Vec::new(),
        persistent_task_upserts: Vec::new(),
        decommission_attribute_diffs: Vec::new(),
        decommission_attribute_upserts: Vec::new(),
        weighted_routing_diffs: Vec::new(),
        weighted_routing_upserts: Vec::new(),
        view_diffs: Vec::new(),
        view_upserts: Vec::new(),
        workload_group_diffs: Vec::new(),
        workload_group_upserts: Vec::new(),
        repository_cleanup_diffs: Vec::new(),
        repository_cleanup_upserts: Vec::new(),
        restore_diffs: Vec::new(),
        restore_upserts: Vec::new(),
        snapshot_deletions_diffs: Vec::new(),
        snapshot_deletions_upserts: Vec::new(),
        snapshots_diffs: Vec::new(),
        snapshots_upserts: Vec::new(),
        remaining_bytes_after_prefix: input.remaining(),
    })
}

fn read_diffable_string_map_diff_prefix(
    input: &mut StreamInput,
    _section: &'static str,
) -> Result<DiffableStringMapDiffPrefix, ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_keys = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_keys.push(input.read_string()?);
    }

    let upsert_count = read_non_negative_len(input)?;
    let mut upsert_keys = Vec::with_capacity(upsert_count);
    let mut upsert_entries = Vec::with_capacity(upsert_count);
    for _ in 0..upsert_count {
        let key = input.read_string()?;
        let value = input.read_string()?;
        upsert_keys.push(key.clone());
        upsert_entries.push(StringMapEntryPrefix { key, value });
    }

    Ok(DiffableStringMapDiffPrefix {
        delete_count,
        deleted_keys,
        upsert_count,
        upsert_keys,
        upsert_entries,
        remaining_bytes_after_prefix: input.remaining(),
    })
}

fn read_index_mapping_map_diff_counts(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<(MapDiffCountsPrefix, Vec<IndexMappingDiffPrefix>), ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    if delete_count > 0 {
        let name = input.read_string()?;
        return Err(ClusterStateDecodeError::UnsupportedNamedWriteable { section, name });
    }

    let diff_count = read_non_negative_len(input)?;
    let mut mapping_diffs = Vec::with_capacity(diff_count);
    for _ in 0..diff_count {
        let key = input.read_string()?;
        let replacement_present = input.read_bool()?;
        let replacement = if replacement_present {
            Some(read_index_mapping_prefix(input)?)
        } else {
            None
        };
        mapping_diffs.push(IndexMappingDiffPrefix {
            key,
            replacement_present,
            replacement,
        });
    }

    let upsert_count = read_non_negative_len(input)?;
    if upsert_count > 0 {
        let name = input.read_string()?;
        return Err(ClusterStateDecodeError::UnsupportedNamedWriteable { section, name });
    }

    Ok((
        MapDiffCountsPrefix {
            delete_count,
            diff_count,
            upsert_count,
        },
        mapping_diffs,
    ))
}

fn read_index_alias_map_diff_counts(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<(MapDiffCountsPrefix, Vec<IndexAliasDiffPrefix>), ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    if delete_count > 0 {
        let name = input.read_string()?;
        return Err(ClusterStateDecodeError::UnsupportedNamedWriteable { section, name });
    }

    let diff_count = read_non_negative_len(input)?;
    let mut alias_diffs = Vec::with_capacity(diff_count);
    for _ in 0..diff_count {
        let key = input.read_string()?;
        let replacement_present = input.read_bool()?;
        let replacement = if replacement_present {
            Some(read_template_alias_prefix(input)?)
        } else {
            None
        };
        alias_diffs.push(IndexAliasDiffPrefix {
            key,
            replacement_present,
            replacement,
        });
    }

    let upsert_count = read_non_negative_len(input)?;
    if upsert_count > 0 {
        let name = input.read_string()?;
        return Err(ClusterStateDecodeError::UnsupportedNamedWriteable { section, name });
    }

    Ok((
        MapDiffCountsPrefix {
            delete_count,
            diff_count,
            upsert_count,
        },
        alias_diffs,
    ))
}

fn read_index_custom_data_map_diff_counts(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<(MapDiffCountsPrefix, Vec<IndexCustomDataDiffPrefix>), ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    if delete_count > 0 {
        let name = input.read_string()?;
        return Err(ClusterStateDecodeError::UnsupportedNamedWriteable { section, name });
    }

    let diff_count = read_non_negative_len(input)?;
    let mut custom_data_diffs = Vec::with_capacity(diff_count);
    for _ in 0..diff_count {
        let key = input.read_string()?;
        let diff = read_diffable_string_map_diff_prefix(input, section)?;
        custom_data_diffs.push(IndexCustomDataDiffPrefix { key, diff });
    }

    let upsert_count = read_non_negative_len(input)?;
    if upsert_count > 0 {
        let name = input.read_string()?;
        return Err(ClusterStateDecodeError::UnsupportedNamedWriteable { section, name });
    }

    Ok((
        MapDiffCountsPrefix {
            delete_count,
            diff_count,
            upsert_count,
        },
        custom_data_diffs,
    ))
}

fn read_index_rollover_info_map_diff_counts(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<(MapDiffCountsPrefix, Vec<IndexRolloverInfoDiffPrefix>), ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    if delete_count > 0 {
        let name = input.read_string()?;
        return Err(ClusterStateDecodeError::UnsupportedNamedWriteable { section, name });
    }

    let diff_count = read_non_negative_len(input)?;
    let mut rollover_info_diffs = Vec::with_capacity(diff_count);
    for _ in 0..diff_count {
        let key = input.read_string()?;
        let replacement_present = input.read_bool()?;
        let replacement = if replacement_present {
            Some(read_index_rollover_info_prefix(input)?)
        } else {
            None
        };
        rollover_info_diffs.push(IndexRolloverInfoDiffPrefix {
            key,
            replacement_present,
            replacement,
        });
    }

    let upsert_count = read_non_negative_len(input)?;
    if upsert_count > 0 {
        let name = input.read_string()?;
        return Err(ClusterStateDecodeError::UnsupportedNamedWriteable { section, name });
    }

    Ok((
        MapDiffCountsPrefix {
            delete_count,
            diff_count,
            upsert_count,
        },
        rollover_info_diffs,
    ))
}

fn read_in_sync_allocation_ids_diff_counts(
    input: &mut StreamInput,
    section: &'static str,
) -> Result<(MapDiffCountsPrefix, InSyncAllocationIdsDiffPrefix), ClusterStateDecodeError> {
    let delete_count = read_non_negative_len(input)?;
    let mut deleted_shard_ids = Vec::with_capacity(delete_count);
    for _ in 0..delete_count {
        deleted_shard_ids.push(input.read_i32()?);
    }

    let diff_count = read_non_negative_len(input)?;
    if diff_count > 0 {
        return Err(ClusterStateDecodeError::UnsupportedSection(section));
    }

    let upsert_count = read_non_negative_len(input)?;
    let mut upserts = Vec::with_capacity(upsert_count);
    for _ in 0..upsert_count {
        let shard_id = input.read_i32()?;
        let allocation_ids = read_string_list(input)?;
        upserts.push(InSyncAllocationIdsUpsertPrefix {
            shard_id,
            allocation_ids,
        });
    }

    Ok((
        MapDiffCountsPrefix {
            delete_count,
            diff_count,
            upsert_count,
        },
        InSyncAllocationIdsDiffPrefix {
            deleted_shard_ids,
            upserts,
        },
    ))
}

fn read_non_negative_len(input: &mut StreamInput) -> Result<usize, ClusterStateDecodeError> {
    let len = input.read_vint()?;
    if len < 0 {
        return Err(ClusterStateDecodeError::NegativeLength(len));
    }
    Ok(len as usize)
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterStateFixturePlan {
    pub action: &'static str,
    pub response_reader: &'static str,
    pub full_state_reader: &'static str,
    pub fixture_strategy: &'static str,
}

impl Default for ClusterStateFixturePlan {
    fn default() -> Self {
        Self {
            action: CLUSTER_STATE_ACTION,
            response_reader: "ClusterStateResponse(StreamInput)",
            full_state_reader: "ClusterState.readFrom(StreamInput, DiscoveryNode)",
            fixture_strategy:
                "Generate Java bytes for ClusterStateResponse with a single-node state and decode incrementally in Rust.",
        }
    }
}

#[derive(Debug, Error)]
pub enum ClusterStateDecodeError {
    #[error(transparent)]
    Stream(#[from] StreamInputError),
    #[error(transparent)]
    TransportError(#[from] os_transport::error::TransportErrorDecodeError),
    #[error("cluster-state section is not implemented yet: {0}")]
    UnsupportedSection(&'static str),
    #[error("negative cluster-state collection length: {0}")]
    NegativeLength(i32),
    #[error("invalid transport address IP byte length in cluster-state node: {0}")]
    InvalidIpLength(usize),
    #[error("invalid cluster block level ordinal: {0}")]
    InvalidClusterBlockLevel(i32),
    #[error("invalid shard routing state id: {0}")]
    InvalidShardRoutingState(u8),
    #[error("invalid recovery source type id: {0}")]
    InvalidRecoverySourceType(u8),
    #[error("invalid optional boolean byte: {0}")]
    InvalidOptionalBoolean(u8),
    #[error("unsupported generic value type {type_id} in cluster-state section {section}")]
    UnsupportedGenericValue { section: &'static str, type_id: i8 },
    #[error("invalid integer setting {name}={value}")]
    InvalidSettingInteger { name: &'static str, value: String },
    #[error("unsupported named writeable [{name}] in cluster-state section {section}")]
    UnsupportedNamedWriteable { section: &'static str, name: String },
}

#[cfg(test)]
mod tests {
    use super::{
        read_cluster_blocks_prefix, read_cluster_state_tail_prefix, read_generic_map_prefix,
        read_publication_cluster_state_diff_header_prefix,
        read_publication_cluster_state_diff_prefix, read_routing_table_prefix,
        read_string_map_diff_envelope_prefix, read_string_map_prefix, ClusterStateDecodeError,
        ClusterStateRequest, ClusterStateResponsePrefix, ShardRoutingStatePrefix,
        CLUSTER_STATE_ACTION, VERSION_3_7_0_ID,
    };
    use bytes::Bytes;
    use os_core::Version;
    use os_stream::StreamInput;
    use os_stream::StreamOutput;

    #[test]
    fn exposes_cluster_state_transport_action_name() {
        assert_eq!(CLUSTER_STATE_ACTION, "cluster:monitor/state");
    }

    #[test]
    fn decodes_timeout_response_without_state() {
        let mut output = StreamOutput::new();
        output.write_string("runTask");
        output.write_bool(false);
        output.write_bool(true);

        let response = ClusterStateResponsePrefix::read(output.freeze()).unwrap();

        assert_eq!(response.response_cluster_name, "runTask");
        assert_eq!(response.state_header, None);
        assert_eq!(response.metadata_prefix, None);
        assert_eq!(response.routing_table, None);
        assert_eq!(response.discovery_nodes, None);
        assert_eq!(response.cluster_blocks, None);
        assert_eq!(response.cluster_state_tail, None);
        assert_eq!(response.wait_for_timed_out, Some(true));
        assert_eq!(response.remaining_state_bytes_after_prefix, 0);
    }

    #[test]
    fn decodes_publication_cluster_state_diff_header_prefix() {
        let mut output = StreamOutput::new();
        output.write_bool(false);
        output.write_string("runTask");
        output.write_string("from-state-uuid");
        output.write_string("to-state-uuid");
        output.write_i64(7);
        output.write_vint(0);

        let prefix = read_publication_cluster_state_diff_header_prefix(output.freeze()).unwrap();

        assert_eq!(prefix.cluster_name, "runTask");
        assert_eq!(prefix.from_uuid, "from-state-uuid");
        assert_eq!(prefix.to_uuid, "to-state-uuid");
        assert_eq!(prefix.to_version, 7);
        assert_eq!(prefix.remaining_bytes_after_header, 1);
    }

    #[test]
    fn rejects_publication_full_state_in_diff_prefix_decoder() {
        let mut output = StreamOutput::new();
        output.write_bool(true);

        let error = read_publication_cluster_state_diff_header_prefix(output.freeze()).unwrap_err();

        assert!(matches!(
            error,
            ClusterStateDecodeError::UnsupportedSection("publication.full_cluster_state")
        ));
    }

    #[test]
    fn decodes_delete_only_string_map_diff_envelope_prefix() {
        let mut output = StreamOutput::new();
        output.write_vint(2);
        output.write_string("old-a");
        output.write_string("old-b");
        output.write_vint(0);
        output.write_vint(0);

        let prefix =
            read_string_map_diff_envelope_prefix(output.freeze(), "cluster_state.diff.customs")
                .unwrap();

        assert_eq!(prefix.delete_count, 2);
        assert_eq!(prefix.deleted_keys, vec!["old-a", "old-b"]);
        assert_eq!(prefix.diff_count, 0);
        assert_eq!(prefix.upsert_count, 0);
        assert_eq!(prefix.remaining_bytes_after_prefix, 0);
    }

    #[test]
    fn decodes_empty_publication_cluster_state_diff_section_counts() {
        let mut output = StreamOutput::new();
        output.write_bool(false);
        output.write_string("runTask");
        output.write_string("from-state-uuid");
        output.write_string("to-state-uuid");
        output.write_i64(7);

        output.write_i64(11);
        write_empty_string_map_diff(&mut output);

        output.write_bool(false);

        output.write_string("cluster-uuid");
        output.write_bool(true);
        output.write_i64(13);
        output.write_i64(17);
        output.write_string_array(&[]);
        output.write_string_array(&[]);
        output.write_vint(0);
        output.write_vint(0);
        output.write_vint(0);
        output.write_vint(0);
        output.write_vint(0);
        write_empty_string_map_diff(&mut output);
        write_empty_string_map_diff(&mut output);
        write_empty_string_map_diff(&mut output);

        output.write_bool(false);
        write_empty_string_map_diff(&mut output);
        output.write_vint(0);

        let prefix = read_publication_cluster_state_diff_prefix(
            output.freeze(),
            Version::from_id(VERSION_3_7_0_ID),
        )
        .unwrap();

        assert_eq!(prefix.header.cluster_name, "runTask");
        assert_eq!(prefix.routing_table_version, 11);
        assert_eq!(prefix.routing_indices.delete_count, 0);
        assert!(!prefix.nodes_complete_diff);
        assert_eq!(prefix.metadata_cluster_uuid, "cluster-uuid");
        assert!(prefix.metadata_cluster_uuid_committed);
        assert_eq!(prefix.metadata_version, 13);
        assert_eq!(prefix.metadata_indices.diff_count, 0);
        assert_eq!(prefix.metadata_templates.upsert_count, 0);
        assert_eq!(prefix.metadata_customs.delete_count, 0);
        assert!(!prefix.blocks_complete_diff);
        assert_eq!(prefix.customs.upsert_count, 0);
        assert_eq!(
            prefix.minimum_cluster_manager_nodes_on_publishing_cluster_manager,
            0
        );
        assert_eq!(prefix.remaining_bytes_after_prefix, 0);
    }

    #[test]
    fn rejects_non_empty_named_diff_entries_until_payload_decoder_exists() {
        let mut output = StreamOutput::new();
        output.write_vint(0);
        output.write_vint(1);
        output.write_string("snapshots");

        let error =
            read_string_map_diff_envelope_prefix(output.freeze(), "cluster_state.diff.customs")
                .unwrap_err();

        assert!(matches!(
            error,
            ClusterStateDecodeError::UnsupportedNamedWriteable {
                section: "cluster_state.diff.customs",
                name
            } if name == "snapshots"
        ));
    }

    fn write_empty_string_map_diff(output: &mut StreamOutput) {
        output.write_vint(0);
        output.write_vint(0);
        output.write_vint(0);
    }

    #[test]
    fn builds_default_cluster_state_request_body() {
        let bytes = ClusterStateRequest::default().to_bytes();
        let mut input = StreamInput::new(bytes);

        assert_eq!(input.read_string().unwrap(), "");
        assert_eq!(input.read_vlong().unwrap(), 60);
        assert_eq!(input.read_byte().unwrap(), 3);
        assert!(!input.read_bool().unwrap());
        for _ in 0..5 {
            assert!(input.read_bool().unwrap());
        }
        assert!(input.read_string_array().unwrap().is_empty());
        assert_eq!(input.read_vint().unwrap(), 2);
        assert_eq!(input.read_vint().unwrap(), 0);
        assert_eq!(input.read_vint().unwrap(), 2);
        assert_eq!(input.read_vint().unwrap(), 1);
        assert_eq!(input.read_vint().unwrap(), 0);
        assert_eq!(input.read_vlong().unwrap(), 2);
        assert_eq!(input.read_byte().unwrap(), 4);
        assert!(!input.read_bool().unwrap());
        assert_eq!(input.remaining(), 0);
    }

    #[test]
    fn builds_minimal_probe_cluster_state_request_body() {
        let bytes = ClusterStateRequest::minimal_probe().to_bytes();
        let mut input = StreamInput::new(bytes);

        assert_eq!(input.read_string().unwrap(), "");
        assert_eq!(input.read_vlong().unwrap(), 60);
        assert_eq!(input.read_byte().unwrap(), 3);
        assert!(!input.read_bool().unwrap());
        for _ in 0..5 {
            assert!(!input.read_bool().unwrap());
        }
    }

    #[test]
    fn decodes_null_generic_map_prefix_as_empty() {
        let mut output = StreamOutput::new();
        output.write_byte(0xff);
        let mut input = StreamInput::new(output.freeze());

        let entries = read_generic_map_prefix(&mut input, "test.generic_map").unwrap();

        assert!(entries.is_empty());
        assert_eq!(input.remaining(), 0);
    }

    #[test]
    fn decodes_null_string_map_prefix_as_empty() {
        let mut output = StreamOutput::new();
        output.write_byte(0xff);
        let mut input = StreamInput::new(output.freeze());

        let entries = read_string_map_prefix(&mut input, "test.string_map").unwrap();

        assert!(entries.is_empty());
        assert_eq!(input.remaining(), 0);
    }

    #[test]
    fn decodes_cluster_state_header_prefix() {
        let mut output = StreamOutput::new();
        output.write_string("runTask");
        output.write_bool(true);
        output.write_string("runTask");
        output.write_i64(42);
        output.write_string("state-uuid");
        output.write_i64(9);
        output.write_string("_na_");
        output.write_bool(false);
        output.write_i64(3);
        output.write_string_array(&["node-a".to_string()]);
        output.write_string_array(&["node-a".to_string()]);
        output.write_vint(0);
        output.write_vint(0);
        output.write_vint(0);
        output.write_byte(10);
        output.write_vint(0);
        output.write_vint(0);
        output.write_vint(0);
        output.write_vint(1);
        output.write_string("index-graveyard");
        output.write_vint(0);
        output.write_i64(11);
        output.write_vint(0);
        output.write_bool(false);
        output.write_vint(0);
        output.write_vint(0);
        output.write_vint(0);
        output.write_vint(0);
        output.write_vint(0);
        output.write_bool(false);

        let response = ClusterStateResponsePrefix::read(output.freeze()).unwrap();
        let header = response.state_header.unwrap();
        let metadata = response.metadata_prefix.unwrap();
        let routing_table = response.routing_table.unwrap();
        let discovery_nodes = response.discovery_nodes.unwrap();
        let cluster_blocks = response.cluster_blocks.unwrap();
        let cluster_state_tail = response.cluster_state_tail.unwrap();

        assert_eq!(response.response_cluster_name, "runTask");
        assert_eq!(header.cluster_name, "runTask");
        assert_eq!(header.version, 42);
        assert_eq!(header.state_uuid, "state-uuid");
        assert_eq!(metadata.version, 9);
        assert_eq!(metadata.cluster_uuid, "_na_");
        assert!(!metadata.cluster_uuid_committed);
        assert_eq!(metadata.coordination.term, 3);
        assert!(metadata
            .coordination
            .last_committed_configuration
            .contains("node-a"));
        assert_eq!(metadata.transient_settings_count, 0);
        assert!(metadata.transient_settings.is_empty());
        assert_eq!(metadata.persistent_settings_count, 0);
        assert!(metadata.persistent_settings.is_empty());
        assert_eq!(metadata.hashes_of_consistent_settings_count, 0);
        assert!(metadata.hashes_of_consistent_settings.is_empty());
        assert_eq!(metadata.index_metadata_count, 0);
        assert!(metadata.index_metadata.is_empty());
        assert_eq!(metadata.templates_count, 0);
        assert!(metadata.templates.is_empty());
        assert_eq!(metadata.custom_metadata_count, 1);
        assert_eq!(metadata.index_graveyard_tombstones_count, Some(0));
        assert!(metadata.index_graveyard_tombstones.is_empty());
        assert_eq!(metadata.component_templates_count, None);
        assert!(metadata.component_templates.is_empty());
        assert_eq!(metadata.composable_index_templates_count, None);
        assert!(metadata.composable_index_templates.is_empty());
        assert_eq!(metadata.data_streams_count, None);
        assert!(metadata.data_streams.is_empty());
        assert_eq!(metadata.repositories_count, None);
        assert!(metadata.repositories.is_empty());
        assert_eq!(metadata.weighted_routing, None);
        assert_eq!(metadata.views_count, None);
        assert!(metadata.views.is_empty());
        assert_eq!(metadata.workload_groups_count, None);
        assert!(metadata.workload_groups.is_empty());
        assert_eq!(routing_table.version, 11);
        assert_eq!(routing_table.index_routing_table_count, 0);
        assert!(routing_table.indices.is_empty());
        assert_eq!(discovery_nodes.cluster_manager_node_id, None);
        assert_eq!(discovery_nodes.node_count, 0);
        assert!(discovery_nodes.nodes.is_empty());
        assert_eq!(cluster_blocks.global_block_count, 0);
        assert!(cluster_blocks.global_blocks.is_empty());
        assert_eq!(cluster_blocks.index_block_count, 0);
        assert!(cluster_blocks.index_blocks.is_empty());
        assert_eq!(cluster_state_tail.custom_count, 0);
        assert_eq!(
            cluster_state_tail.minimum_cluster_manager_nodes_on_publishing_cluster_manager,
            0
        );
        assert_eq!(response.wait_for_timed_out, Some(false));
        assert_eq!(response.remaining_state_bytes_after_prefix, 0);
    }

    #[test]
    fn decodes_global_and_index_cluster_blocks() {
        let mut output = StreamOutput::new();
        output.write_vint(1);
        output.write_vint(1);
        output.write_bool(false);
        output.write_string("block");
        output.write_vint(0);
        output.write_bool(false);
        output.write_bool(false);
        output.write_string("OK");
        output.write_bool(false);
        output.write_vint(0);

        let mut input = StreamInput::new(output.freeze());
        let blocks = read_cluster_blocks_prefix(&mut input).unwrap();

        assert_eq!(blocks.global_block_count, 1);
        assert_eq!(blocks.global_blocks[0].id, 1);
        assert_eq!(blocks.index_block_count, 0);

        let mut output = StreamOutput::new();
        output.write_vint(0);
        output.write_vint(1);
        output.write_string("index");
        output.write_vint(1);
        output.write_vint(2);
        output.write_bool(false);
        output.write_string("index block");
        output.write_vint(0);
        output.write_bool(false);
        output.write_bool(false);
        output.write_string("OK");
        output.write_bool(false);

        let mut input = StreamInput::new(output.freeze());
        let blocks = read_cluster_blocks_prefix(&mut input).unwrap();

        assert_eq!(blocks.global_block_count, 0);
        assert_eq!(blocks.index_block_count, 1);
        assert_eq!(blocks.index_blocks[0].index_name, "index");
        assert_eq!(blocks.index_blocks[0].block_count, 1);
        assert_eq!(blocks.index_blocks[0].blocks[0].id, 2);
    }

    #[test]
    fn decodes_allocated_shard_routing_prefix() {
        let mut output = StreamOutput::new();
        output.write_i64(1);
        output.write_vint(1);
        output.write_string("index");
        output.write_string("uuid");
        output.write_vint(1);
        output.write_vint(0);
        output.write_vint(1);
        output.write_bool(false);
        output.write_bool(false);
        output.write_bool(true);
        output.write_bool(false);
        output.write_byte(3);
        output.write_bool(false);
        output.write_bool(true);
        output.write_string("allocation-1");
        output.write_bool(false);
        output.write_bool(false);
        output.write_bool(false);

        let mut input = StreamInput::new(output.freeze());
        let routing =
            read_routing_table_prefix(&mut input, Version::from_id(VERSION_3_7_0_ID)).unwrap();
        let shard = &routing.indices[0].shards[0].shard_routings[0];

        assert_eq!(shard.current_node_id, None);
        assert!(shard.primary);
        assert_eq!(shard.state, ShardRoutingStatePrefix::Started);
        assert_eq!(shard.allocation_id.as_ref().unwrap().id, "allocation-1");
    }

    #[test]
    fn rejects_unknown_cluster_state_customs() {
        let mut output = StreamOutput::new();
        output.write_vint(1);
        output.write_string("unknown_custom");

        let mut input = StreamInput::new(output.freeze());
        let error = read_cluster_state_tail_prefix(&mut input).unwrap_err();

        assert!(matches!(
            error,
            ClusterStateDecodeError::UnsupportedNamedWriteable {
                section: "cluster_state.customs",
                name
            } if name == "unknown_custom"
        ));
    }

    #[test]
    fn decodes_java_signed_vint_tail_value() {
        let mut input = StreamInput::new(Bytes::from_static(&[0xff, 0xff, 0xff, 0xff, 0x0f]));

        assert_eq!(input.read_vint().unwrap(), -1);
        assert_eq!(input.remaining(), 0);
    }
}
