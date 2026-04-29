//! Cluster-state wire entrypoints and decode scaffolding.

use bytes::{Bytes, BytesMut};
use os_core::{
    Version, OPENSEARCH_2_10_0, OPENSEARCH_2_17_0, OPENSEARCH_2_18_0, OPENSEARCH_2_7_0,
    OPENSEARCH_2_9_0, OPENSEARCH_3_0_0, OPENSEARCH_3_6_0, OPENSEARCH_3_7_0,
    OPENSEARCH_3_7_0_TRANSPORT, OPENSEARCH_DISCOVERY_NODE_STREAM_ADDRESS,
};
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
pub const DEFAULT_CLUSTER_STATE_STREAM_VERSION: Version = OPENSEARCH_3_7_0_TRANSPORT;

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
    pub metadata_coordination: CoordinationMetadataPrefix,
    pub metadata_transient_settings: Vec<SettingPrefix>,
    pub metadata_persistent_settings: Vec<SettingPrefix>,
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
        Self::read_with_version(bytes, DEFAULT_CLUSTER_STATE_STREAM_VERSION)
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
            Some(read_cluster_state_tail_prefix(&mut input, stream_version)?)
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

    pub fn into_cluster_state(self) -> Result<ClusterState, ClusterStateDecodeError> {
        self.try_into()
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterState {
    pub response_cluster_name: String,
    pub header: ClusterStateHeader,
    pub metadata: Metadata,
    pub routing_table: RoutingTable,
    pub discovery_nodes: DiscoveryNodes,
    pub cluster_blocks: ClusterBlocks,
    pub customs: ClusterStateCustoms,
    pub wait_for_timed_out: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct Metadata {
    pub version: i64,
    pub cluster_uuid: String,
    pub cluster_uuid_committed: bool,
    pub coordination: CoordinationMetadata,
    pub transient_settings: Vec<Setting>,
    pub persistent_settings: Vec<Setting>,
    pub hashes_of_consistent_settings: Vec<Setting>,
    pub index_metadata: Vec<IndexMetadata>,
    pub templates: Vec<IndexTemplateMetadata>,
    pub customs: MetadataCustoms,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct Setting {
    pub key: String,
    pub value: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexMetadata {
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
pub struct IndexTemplateMetadata {
    pub name: String,
    pub order: i32,
    pub patterns: Vec<String>,
    pub settings_count: usize,
    pub settings: Vec<Setting>,
    pub mappings_count: usize,
    pub mappings: Vec<TemplateMappingPrefix>,
    pub aliases_count: usize,
    pub aliases: Vec<TemplateAliasPrefix>,
    pub version: Option<i32>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IngestPipeline {
    pub id: String,
    pub config_len: usize,
    pub media_type: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchPipeline {
    pub id: String,
    pub config_len: usize,
    pub media_type: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct StoredScript {
    pub id: String,
    pub lang: String,
    pub source_len: usize,
    pub options_count: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PersistentTask {
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
pub struct IndexGraveyardTombstone {
    pub index_name: String,
    pub index_uuid: String,
    pub delete_date_in_millis: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RepositoryMetadata {
    pub name: String,
    pub repository_type: String,
    pub settings_count: usize,
    pub settings: Vec<Setting>,
    pub generation: i64,
    pub pending_generation: i64,
    pub crypto_metadata_present: bool,
    pub crypto_key_provider_name: Option<String>,
    pub crypto_key_provider_type: Option<String>,
    pub crypto_settings_count: usize,
    pub crypto_settings: Vec<Setting>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ComponentTemplate {
    pub name: String,
    pub settings_count: usize,
    pub settings: Vec<Setting>,
    pub mappings_present: bool,
    pub mapping: Option<CompressedXContentPrefix>,
    pub aliases_count: usize,
    pub aliases: Vec<TemplateAliasPrefix>,
    pub version: Option<i64>,
    pub metadata_present: bool,
    pub metadata_count: usize,
    pub metadata: Vec<Setting>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ComposableIndexTemplate {
    pub name: String,
    pub index_patterns: Vec<String>,
    pub template_present: bool,
    pub template_settings_count: usize,
    pub template_settings: Vec<Setting>,
    pub template_mappings_present: bool,
    pub template_mapping: Option<CompressedXContentPrefix>,
    pub template_aliases_count: usize,
    pub template_aliases: Vec<TemplateAliasPrefix>,
    pub component_templates_count: usize,
    pub component_templates: Vec<String>,
    pub priority: Option<i64>,
    pub version: Option<i64>,
    pub metadata_count: usize,
    pub metadata: Vec<Setting>,
    pub data_stream_template_present: bool,
    pub data_stream_timestamp_field: Option<String>,
    pub context_present: bool,
    pub context_name: Option<String>,
    pub context_version: Option<String>,
    pub context_params_count: usize,
    pub context_params: Vec<Setting>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DataStream {
    pub name: String,
    pub timestamp_field: String,
    pub backing_indices_count: usize,
    pub backing_indices: Vec<DataStreamBackingIndex>,
    pub generation: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DataStreamBackingIndex {
    pub name: String,
    pub uuid: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DecommissionAttributeMetadata {
    pub attribute_name: String,
    pub attribute_value: String,
    pub status: String,
    pub request_id: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct WeightedRoutingMetadata {
    pub awareness_attribute: String,
    pub weights: Vec<Setting>,
    pub version: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ViewMetadata {
    pub name: String,
    pub description: Option<String>,
    pub created_at: i64,
    pub modified_at: i64,
    pub target_index_patterns: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct WorkloadGroup {
    pub name: String,
    pub id: String,
    pub resource_limits: Vec<Setting>,
    pub resiliency_mode: Option<String>,
    pub search_settings: Vec<Setting>,
    pub updated_at_millis: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MetadataCustoms {
    pub declared_count: usize,
    pub ingest_pipelines: Vec<IngestPipeline>,
    pub search_pipelines: Vec<SearchPipeline>,
    pub stored_scripts: Vec<StoredScript>,
    pub persistent_tasks: Vec<PersistentTask>,
    pub decommission_attribute: Option<DecommissionAttributeMetadata>,
    pub index_graveyard_tombstones: Vec<IndexGraveyardTombstone>,
    pub component_templates: Vec<ComponentTemplate>,
    pub composable_index_templates: Vec<ComposableIndexTemplate>,
    pub data_streams: Vec<DataStream>,
    pub repositories: Vec<RepositoryMetadata>,
    pub weighted_routing: Option<WeightedRoutingMetadata>,
    pub views: Vec<ViewMetadata>,
    pub workload_groups: Vec<WorkloadGroup>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CoordinationMetadata {
    pub term: i64,
    pub last_committed_configuration: BTreeSet<String>,
    pub last_accepted_configuration: BTreeSet<String>,
    pub voting_config_exclusions: Vec<VotingConfigExclusion>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RoutingTable {
    pub version: i64,
    pub indices: Vec<IndexRoutingTable>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexRoutingTable {
    pub index_name: String,
    pub index_uuid: String,
    pub shards: Vec<IndexShardRoutingTable>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexShardRoutingTable {
    pub shard_id: i32,
    pub shard_routings: Vec<ShardRouting>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ShardRouting {
    pub current_node_id: Option<String>,
    pub relocating_node_id: Option<String>,
    pub primary: bool,
    pub search_only: bool,
    pub state: ShardRoutingState,
    pub recovery_source_type: Option<RecoverySourceType>,
    pub recovery_source_bootstrap_new_history_uuid: Option<bool>,
    pub snapshot_recovery_source: Option<SnapshotRecoverySource>,
    pub remote_store_recovery_source: Option<RemoteStoreRecoverySource>,
    pub unassigned_info: Option<UnassignedInfo>,
    pub allocation_id_present: bool,
    pub allocation_id: Option<AllocationId>,
    pub expected_shard_size: Option<i64>,
}

#[derive(Copy, Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum ShardRoutingState {
    Unassigned,
    Initializing,
    Started,
    Relocating,
    Splitting,
}

#[derive(Copy, Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum RecoverySourceType {
    EmptyStore,
    ExistingStore,
    Peer,
    Snapshot,
    LocalShards,
    RemoteStore,
    InPlaceSplitShard,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotRecoverySource {
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
pub struct RemoteStoreRecoverySource {
    pub restore_uuid: String,
    pub version_id: i32,
    pub index_name: String,
    pub index_id: String,
    pub index_shard_path_type: Option<i32>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct UnassignedInfo {
    pub reason_id: u8,
    pub unassigned_time_millis: i64,
    pub delayed: bool,
    pub message: Option<String>,
    pub failure: Option<UnassignedFailure>,
    pub failed_allocations: i32,
    pub last_allocation_status_id: u8,
    pub failed_node_ids_count: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct UnassignedFailure {
    pub class_name: String,
    pub message: Option<String>,
    pub summary: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct AllocationId {
    pub id: String,
    pub relocation_id: Option<String>,
    pub split_child_allocation_ids_count: Option<usize>,
    pub parent_allocation_id: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DiscoveryNodes {
    pub cluster_manager_node_id: Option<String>,
    pub nodes: Vec<DiscoveryNode>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DiscoveryNode {
    pub name: String,
    pub id: String,
    pub ephemeral_id: String,
    pub host_name: String,
    pub host_address: String,
    pub address: TransportAddress,
    pub stream_address: Option<TransportAddress>,
    pub skipped_attribute_count: usize,
    pub roles: Vec<DiscoveryNodeRole>,
    pub version: i32,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TransportAddress {
    pub ip: IpAddr,
    pub host: String,
    pub port: i32,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DiscoveryNodeRole {
    pub name: String,
    pub abbreviation: String,
    pub can_contain_data: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterBlocks {
    pub global_blocks: Vec<ClusterBlock>,
    pub index_blocks: Vec<IndexClusterBlocks>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct IndexClusterBlocks {
    pub index_name: String,
    pub blocks: Vec<ClusterBlock>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterBlock {
    pub id: i32,
    pub uuid: Option<String>,
    pub description: String,
    pub levels: Vec<ClusterBlockLevel>,
    pub retryable: bool,
    pub disable_state_persistence: bool,
    pub status: String,
    pub allow_release_resources: bool,
}

#[derive(Copy, Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum ClusterBlockLevel {
    Read,
    Write,
    MetadataRead,
    MetadataWrite,
    CreateIndex,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterStateCustoms {
    pub declared_count: usize,
    pub names: Vec<String>,
    pub repository_cleanup: Option<RepositoryCleanupInProgress>,
    pub snapshot_deletions: Option<SnapshotDeletionsInProgress>,
    pub restore: Option<RestoreInProgress>,
    pub snapshots: Option<SnapshotsInProgress>,
    pub minimum_cluster_manager_nodes_on_publishing_cluster_manager: i32,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PublicationClusterStateDiffHeader {
    pub cluster_name: String,
    pub from_uuid: String,
    pub to_uuid: String,
    pub to_version: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PublicationClusterStateDiff {
    pub header: PublicationClusterStateDiffHeader,
    pub routing_table_version: i64,
    pub routing_indices: StringMapDiffEnvelope,
    pub nodes_complete_diff: bool,
    pub metadata_cluster_uuid: String,
    pub metadata_cluster_uuid_committed: bool,
    pub metadata_version: i64,
    pub metadata_coordination: CoordinationMetadata,
    pub metadata_transient_settings: Vec<Setting>,
    pub metadata_persistent_settings: Vec<Setting>,
    pub metadata_hashes_of_consistent_settings: DiffableStringMapDiffPrefix,
    pub metadata_indices: StringMapDiffEnvelope,
    pub metadata_templates: StringMapDiffEnvelope,
    pub metadata_customs: StringMapDiffEnvelope,
    pub blocks_complete_diff: bool,
    pub customs: StringMapDiffEnvelope,
    pub minimum_cluster_manager_nodes_on_publishing_cluster_manager: i32,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct StringMapDiffEnvelope {
    pub deleted_keys: Vec<String>,
    pub diff_keys: Vec<String>,
    pub upsert_keys: Vec<String>,
    pub index_metadata_diffs: Vec<IndexMetadataDiffPrefix>,
    pub index_metadata_upserts: Vec<IndexMetadata>,
    pub index_routing_diffs: Vec<IndexRoutingTableDiffPrefix>,
    pub index_routing_upserts: Vec<IndexRoutingTable>,
    pub index_template_diffs: Vec<IndexTemplateMetadataDiffPrefix>,
    pub index_template_upserts: Vec<IndexTemplateMetadata>,
    pub repository_metadata_diffs: Vec<RepositoriesMetadataCustomDiffPrefix>,
    pub repository_metadata_upserts: Vec<RepositoryMetadata>,
    pub component_template_diffs: Vec<ComponentTemplateMetadataCustomDiffPrefix>,
    pub component_template_upserts: Vec<ComponentTemplate>,
    pub composable_index_template_diffs: Vec<ComposableIndexTemplateMetadataCustomDiffPrefix>,
    pub composable_index_template_upserts: Vec<ComposableIndexTemplate>,
    pub data_stream_diffs: Vec<DataStreamMetadataCustomDiffPrefix>,
    pub data_stream_upserts: Vec<DataStream>,
    pub ingest_upserts: Vec<IngestPipeline>,
    pub search_pipeline_upserts: Vec<SearchPipeline>,
    pub stored_script_upserts: Vec<StoredScript>,
    pub index_graveyard_tombstone_upserts: Vec<IndexGraveyardTombstone>,
    pub persistent_task_upserts: Vec<PersistentTask>,
    pub decommission_attribute_diffs: Vec<DecommissionAttributeMetadataCustomDiffPrefix>,
    pub decommission_attribute_upserts: Vec<DecommissionAttributeMetadata>,
    pub weighted_routing_diffs: Vec<WeightedRoutingMetadataCustomDiffPrefix>,
    pub weighted_routing_upserts: Vec<WeightedRoutingMetadata>,
    pub view_diffs: Vec<ViewMetadataCustomDiffPrefix>,
    pub view_upserts: Vec<ViewMetadata>,
    pub workload_group_diffs: Vec<WorkloadGroupMetadataCustomDiffPrefix>,
    pub workload_group_upserts: Vec<WorkloadGroup>,
    pub repository_cleanup_diffs: Vec<RepositoryCleanupNamedDiffPrefix>,
    pub repository_cleanup_upserts: Vec<RepositoryCleanupInProgress>,
    pub restore_diffs: Vec<RestoreInProgressNamedDiffPrefix>,
    pub restore_upserts: Vec<RestoreInProgress>,
    pub snapshot_deletions_diffs: Vec<SnapshotDeletionsInProgressNamedDiffPrefix>,
    pub snapshot_deletions_upserts: Vec<SnapshotDeletionsInProgress>,
    pub snapshots_diffs: Vec<SnapshotsInProgressNamedDiffPrefix>,
    pub snapshots_upserts: Vec<SnapshotsInProgress>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PrefixOnlySummary {
    pub section: String,
    pub fields: Vec<String>,
    pub declared_items: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RepositoryCleanupInProgress {
    pub entry_count: usize,
    pub entries: Vec<RepositoryCleanupEntryPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotDeletionsInProgress {
    pub entry_count: usize,
    pub entries: Vec<SnapshotDeletionEntryPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestoreInProgress {
    pub entry_count: usize,
    pub entries: Vec<RestoreEntryPrefix>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotsInProgress {
    pub entry_count: usize,
    pub entries: Vec<SnapshotInProgressEntryPrefix>,
}

impl IndexMetadata {
    pub fn prefix_only_summary(&self) -> PrefixOnlySummary {
        PrefixOnlySummary {
            section: "metadata.index".to_string(),
            fields: vec![
                "mappings".to_string(),
                "aliases".to_string(),
                "custom_data".to_string(),
                "rollover_infos".to_string(),
                "split_shards".to_string(),
            ],
            declared_items: self.mapping_count
                + self.alias_count
                + self.custom_data_count
                + self.rollover_info_count
                + self.split_shards_root_count.unwrap_or(0)
                + self.split_shards_parent_to_child_count.unwrap_or(0),
        }
    }
}

impl IndexTemplateMetadata {
    pub fn prefix_only_summary(&self) -> PrefixOnlySummary {
        PrefixOnlySummary {
            section: "metadata.templates".to_string(),
            fields: vec!["mappings".to_string(), "aliases".to_string()],
            declared_items: self.mappings_count + self.aliases_count,
        }
    }
}

impl ComponentTemplate {
    pub fn prefix_only_summary(&self) -> PrefixOnlySummary {
        PrefixOnlySummary {
            section: "metadata.customs.component_template".to_string(),
            fields: vec!["mapping".to_string(), "aliases".to_string()],
            declared_items: usize::from(self.mappings_present) + self.aliases_count,
        }
    }
}

impl ComposableIndexTemplate {
    pub fn prefix_only_summary(&self) -> PrefixOnlySummary {
        PrefixOnlySummary {
            section: "metadata.customs.index_template".to_string(),
            fields: vec![
                "template_mapping".to_string(),
                "template_aliases".to_string(),
            ],
            declared_items: usize::from(self.template_mappings_present)
                + self.template_aliases_count,
        }
    }
}

impl ClusterStateCustoms {
    pub fn prefix_only_summary(&self) -> PrefixOnlySummary {
        let declared_items = self
            .repository_cleanup
            .as_ref()
            .map_or(0, |custom| custom.entry_count)
            + self
                .snapshot_deletions
                .as_ref()
                .map_or(0, |custom| custom.entry_count)
            + self.restore.as_ref().map_or(0, |custom| custom.entry_count)
            + self
                .snapshots
                .as_ref()
                .map_or(0, |custom| custom.entry_count);

        PrefixOnlySummary {
            section: "cluster_state.customs".to_string(),
            fields: vec![
                "repository_cleanup.entries".to_string(),
                "snapshot_deletions.entries".to_string(),
                "restore.entries".to_string(),
                "snapshots.entries".to_string(),
            ],
            declared_items,
        }
    }
}

impl From<PublicationClusterStateDiffHeaderPrefix> for PublicationClusterStateDiffHeader {
    fn from(prefix: PublicationClusterStateDiffHeaderPrefix) -> Self {
        Self {
            cluster_name: prefix.cluster_name,
            from_uuid: prefix.from_uuid,
            to_uuid: prefix.to_uuid,
            to_version: prefix.to_version,
        }
    }
}

impl From<PublicationClusterStateDiffPrefix> for PublicationClusterStateDiff {
    fn from(prefix: PublicationClusterStateDiffPrefix) -> Self {
        Self {
            header: prefix.header.into(),
            routing_table_version: prefix.routing_table_version,
            routing_indices: prefix.routing_indices.into(),
            nodes_complete_diff: prefix.nodes_complete_diff,
            metadata_cluster_uuid: prefix.metadata_cluster_uuid,
            metadata_cluster_uuid_committed: prefix.metadata_cluster_uuid_committed,
            metadata_version: prefix.metadata_version,
            metadata_coordination: prefix.metadata_coordination.into(),
            metadata_transient_settings: prefix
                .metadata_transient_settings
                .into_iter()
                .map(Into::into)
                .collect(),
            metadata_persistent_settings: prefix
                .metadata_persistent_settings
                .into_iter()
                .map(Into::into)
                .collect(),
            metadata_hashes_of_consistent_settings: prefix.metadata_hashes_of_consistent_settings,
            metadata_indices: prefix.metadata_indices.into(),
            metadata_templates: prefix.metadata_templates.into(),
            metadata_customs: prefix.metadata_customs.into(),
            blocks_complete_diff: prefix.blocks_complete_diff,
            customs: prefix.customs.into(),
            minimum_cluster_manager_nodes_on_publishing_cluster_manager: prefix
                .minimum_cluster_manager_nodes_on_publishing_cluster_manager,
        }
    }
}

impl From<StringMapDiffEnvelopePrefix> for StringMapDiffEnvelope {
    fn from(prefix: StringMapDiffEnvelopePrefix) -> Self {
        Self {
            deleted_keys: prefix.deleted_keys,
            diff_keys: prefix.diff_keys,
            upsert_keys: prefix.upsert_keys,
            index_metadata_diffs: prefix.index_metadata_diffs,
            index_metadata_upserts: prefix
                .index_metadata_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            index_routing_diffs: prefix.index_routing_diffs,
            index_routing_upserts: prefix
                .index_routing_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            index_template_diffs: prefix.index_template_diffs,
            index_template_upserts: prefix
                .index_template_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            repository_metadata_diffs: prefix.repository_metadata_diffs,
            repository_metadata_upserts: prefix
                .repository_metadata_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            component_template_diffs: prefix.component_template_diffs,
            component_template_upserts: prefix
                .component_template_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            composable_index_template_diffs: prefix.composable_index_template_diffs,
            composable_index_template_upserts: prefix
                .composable_index_template_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            data_stream_diffs: prefix.data_stream_diffs,
            data_stream_upserts: prefix
                .data_stream_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            ingest_upserts: prefix.ingest_upserts.into_iter().map(Into::into).collect(),
            search_pipeline_upserts: prefix
                .search_pipeline_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            stored_script_upserts: prefix
                .stored_script_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            index_graveyard_tombstone_upserts: prefix
                .index_graveyard_tombstone_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            persistent_task_upserts: prefix
                .persistent_task_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            decommission_attribute_diffs: prefix.decommission_attribute_diffs,
            decommission_attribute_upserts: prefix
                .decommission_attribute_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            weighted_routing_diffs: prefix.weighted_routing_diffs,
            weighted_routing_upserts: prefix
                .weighted_routing_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            view_diffs: prefix.view_diffs,
            view_upserts: prefix.view_upserts.into_iter().map(Into::into).collect(),
            workload_group_diffs: prefix.workload_group_diffs,
            workload_group_upserts: prefix
                .workload_group_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            repository_cleanup_diffs: prefix.repository_cleanup_diffs,
            repository_cleanup_upserts: prefix
                .repository_cleanup_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            restore_diffs: prefix.restore_diffs,
            restore_upserts: prefix.restore_upserts.into_iter().map(Into::into).collect(),
            snapshot_deletions_diffs: prefix.snapshot_deletions_diffs,
            snapshot_deletions_upserts: prefix
                .snapshot_deletions_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
            snapshots_diffs: prefix.snapshots_diffs,
            snapshots_upserts: prefix
                .snapshots_upserts
                .into_iter()
                .map(Into::into)
                .collect(),
        }
    }
}

impl TryFrom<ClusterStateResponsePrefix> for ClusterState {
    type Error = ClusterStateDecodeError;

    fn try_from(response: ClusterStateResponsePrefix) -> Result<Self, Self::Error> {
        Ok(Self {
            response_cluster_name: response.response_cluster_name,
            header: response
                .state_header
                .ok_or(ClusterStateDecodeError::MissingSection(
                    "cluster_state.header",
                ))?,
            metadata: response
                .metadata_prefix
                .ok_or(ClusterStateDecodeError::MissingSection(
                    "cluster_state.metadata",
                ))?
                .into(),
            routing_table: response
                .routing_table
                .ok_or(ClusterStateDecodeError::MissingSection(
                    "cluster_state.routing_table",
                ))?
                .into(),
            discovery_nodes: response
                .discovery_nodes
                .ok_or(ClusterStateDecodeError::MissingSection(
                    "cluster_state.discovery_nodes",
                ))?
                .into(),
            cluster_blocks: response
                .cluster_blocks
                .ok_or(ClusterStateDecodeError::MissingSection(
                    "cluster_state.cluster_blocks",
                ))?
                .into(),
            customs: response
                .cluster_state_tail
                .ok_or(ClusterStateDecodeError::MissingSection(
                    "cluster_state.customs",
                ))?
                .into(),
            wait_for_timed_out: response.wait_for_timed_out.ok_or(
                ClusterStateDecodeError::MissingSection("cluster_state.wait_for_timed_out"),
            )?,
        })
    }
}

impl PublicationClusterStateDiff {
    pub fn apply_to(
        self,
        previous: &ClusterState,
    ) -> Result<ClusterState, ClusterStateDecodeError> {
        if previous.header.state_uuid != self.header.from_uuid {
            return Err(ClusterStateDecodeError::DiffBaseMismatch {
                expected: previous.header.state_uuid.clone(),
                actual: self.header.from_uuid,
            });
        }

        let mut metadata = previous.metadata.clone();
        metadata.cluster_uuid = self.metadata_cluster_uuid;
        metadata.cluster_uuid_committed = self.metadata_cluster_uuid_committed;
        metadata.version = self.metadata_version;
        metadata.coordination = self.metadata_coordination;
        metadata.transient_settings = self.metadata_transient_settings;
        metadata.persistent_settings = self.metadata_persistent_settings;
        apply_setting_diff(
            &mut metadata.hashes_of_consistent_settings,
            &self.metadata_hashes_of_consistent_settings,
        );
        apply_index_metadata_diff(&mut metadata.index_metadata, self.metadata_indices)?;
        apply_index_template_diff(&mut metadata.templates, self.metadata_templates)?;
        apply_metadata_customs_diff(&mut metadata.customs, self.metadata_customs)?;

        let mut routing_table = previous.routing_table.clone();
        routing_table.version = self.routing_table_version;
        apply_routing_indices_diff(&mut routing_table.indices, self.routing_indices);

        let mut customs = previous.customs.clone();
        customs.minimum_cluster_manager_nodes_on_publishing_cluster_manager =
            self.minimum_cluster_manager_nodes_on_publishing_cluster_manager;
        apply_cluster_state_customs_diff(&mut customs, self.customs);

        Ok(ClusterState {
            response_cluster_name: previous.response_cluster_name.clone(),
            header: ClusterStateHeader {
                version: self.header.to_version,
                state_uuid: self.header.to_uuid,
                cluster_name: self.header.cluster_name,
            },
            metadata,
            routing_table,
            discovery_nodes: previous.discovery_nodes.clone(),
            cluster_blocks: previous.cluster_blocks.clone(),
            customs,
            wait_for_timed_out: previous.wait_for_timed_out,
        })
    }
}

fn remove_by_key<T, F>(items: &mut Vec<T>, key: &str, key_fn: F)
where
    F: Fn(&T) -> &str,
{
    items.retain(|item| key_fn(item) != key);
}

fn upsert_by_key<T, F>(items: &mut Vec<T>, value: T, key_fn: F)
where
    F: Fn(&T) -> &str,
{
    let key = key_fn(&value).to_string();
    if let Some(existing) = items.iter_mut().find(|item| key_fn(item) == key) {
        *existing = value;
    } else {
        items.push(value);
    }
}

fn apply_setting_diff(items: &mut Vec<Setting>, diff: &DiffableStringMapDiffPrefix) {
    for key in &diff.deleted_keys {
        remove_by_key(items, key, |setting| setting.key.as_str());
    }
    for entry in &diff.upsert_entries {
        upsert_by_key(
            items,
            Setting {
                key: entry.key.clone(),
                value: Some(entry.value.clone()),
            },
            |setting| setting.key.as_str(),
        );
    }
}

fn apply_routing_indices_diff(items: &mut Vec<IndexRoutingTable>, diff: StringMapDiffEnvelope) {
    for key in &diff.deleted_keys {
        remove_by_key(items, key, |index| index.index_name.as_str());
    }
    for (key, item_diff) in diff.diff_keys.iter().zip(diff.index_routing_diffs) {
        if item_diff.replacement_present {
            if let Some(replacement) = item_diff.replacement {
                upsert_by_key(items, replacement.into(), |index| index.index_name.as_str());
            }
        } else {
            remove_by_key(items, key, |index| index.index_name.as_str());
        }
    }
    for upsert in diff.index_routing_upserts {
        upsert_by_key(items, upsert, |index| index.index_name.as_str());
    }
}

fn apply_index_template_diff(
    items: &mut Vec<IndexTemplateMetadata>,
    diff: StringMapDiffEnvelope,
) -> Result<(), ClusterStateDecodeError> {
    for key in &diff.deleted_keys {
        remove_by_key(items, key, |template| template.name.as_str());
    }
    for (key, template_diff) in diff.diff_keys.iter().zip(diff.index_template_diffs) {
        if template_diff.replacement_present {
            if let Some(replacement) = template_diff.replacement {
                upsert_by_key(items, replacement.into(), |template| template.name.as_str());
            }
        } else {
            remove_by_key(items, key, |template| template.name.as_str());
        }
    }
    for upsert in diff.index_template_upserts {
        upsert_by_key(items, upsert, |template| template.name.as_str());
    }
    Ok(())
}

fn apply_index_metadata_diff(
    items: &mut Vec<IndexMetadata>,
    diff: StringMapDiffEnvelope,
) -> Result<(), ClusterStateDecodeError> {
    for key in &diff.deleted_keys {
        remove_by_key(items, key, |index| index.name.as_str());
    }
    for item_diff in diff.index_metadata_diffs {
        let index = items
            .iter_mut()
            .find(|index| index.name == item_diff.name)
            .ok_or_else(|| ClusterStateDecodeError::MissingDiffBase {
                section: "cluster_state.diff.metadata.indices",
                key: item_diff.name.clone(),
            })?;
        apply_single_index_metadata_diff(index, item_diff);
    }
    for upsert in diff.index_metadata_upserts {
        upsert_by_key(items, upsert, |index| index.name.as_str());
    }
    Ok(())
}

fn apply_single_index_metadata_diff(index: &mut IndexMetadata, diff: IndexMetadataDiffPrefix) {
    index.routing_num_shards = diff.routing_num_shards;
    index.version = diff.version;
    index.mapping_version = diff.mapping_version;
    index.settings_version = diff.settings_version;
    index.aliases_version = diff.aliases_version;
    index.state_id = diff.state_id;
    index.settings_count = diff.settings_count;
    index.index_uuid = diff.index_uuid;
    index.number_of_shards = diff.number_of_shards;
    index.number_of_replicas = diff.number_of_replicas;
    index.mapping_count =
        diff.mappings.delete_count + diff.mappings.diff_count + diff.mappings.upsert_count;
    for mapping_diff in diff.mapping_diffs {
        if mapping_diff.replacement_present {
            if let Some(replacement) = mapping_diff.replacement {
                upsert_by_key(&mut index.mappings, replacement, |mapping| {
                    mapping.mapping_type.as_str()
                });
            }
        } else {
            remove_by_key(&mut index.mappings, &mapping_diff.key, |mapping| {
                mapping.mapping_type.as_str()
            });
        }
    }
    index.alias_count =
        diff.aliases.delete_count + diff.aliases.diff_count + diff.aliases.upsert_count;
    for alias_diff in diff.alias_diffs {
        if alias_diff.replacement_present {
            if let Some(replacement) = alias_diff.replacement {
                upsert_by_key(&mut index.aliases, replacement, |alias| {
                    alias.alias.as_str()
                });
            }
        } else {
            remove_by_key(&mut index.aliases, &alias_diff.key, |alias| {
                alias.alias.as_str()
            });
        }
    }
    index.custom_data_count =
        diff.custom_data.delete_count + diff.custom_data.diff_count + diff.custom_data.upsert_count;
    for custom_diff in diff.custom_data_diffs {
        if let Some(custom_data) = index
            .custom_data
            .iter_mut()
            .find(|custom_data| custom_data.key == custom_diff.key)
        {
            apply_setting_prefix_diff(&mut custom_data.entries, &custom_diff.diff);
            custom_data.entries_count = custom_data.entries.len();
        }
    }
    index.in_sync_allocation_ids_count = diff.in_sync_allocation_ids.delete_count
        + diff.in_sync_allocation_ids.diff_count
        + diff.in_sync_allocation_ids.upsert_count;
    index.rollover_info_count = diff.rollover_infos.delete_count
        + diff.rollover_infos.diff_count
        + diff.rollover_infos.upsert_count;
    for rollover_diff in diff.rollover_info_diffs {
        if rollover_diff.replacement_present {
            if let Some(replacement) = rollover_diff.replacement {
                upsert_by_key(&mut index.rollover_infos, replacement, |rollover| {
                    rollover.alias.as_str()
                });
            }
        } else {
            remove_by_key(&mut index.rollover_infos, &rollover_diff.key, |rollover| {
                rollover.alias.as_str()
            });
        }
    }
    index.system = diff.system;
    index.context_present = diff.context_present;
    index.ingestion_status_present = diff.ingestion_status_present;
    index.ingestion_paused = diff.ingestion_paused;
    if let Some(replacement) = diff.split_shards_replacement {
        index.split_shards_root_count = Some(replacement.root_count);
        index.split_shards_root_children = replacement.root_children;
        index.split_shards_max_shard_id = Some(replacement.max_shard_id);
        index.split_shards_in_progress_count = Some(replacement.in_progress_split_shard_ids_count);
        index.split_shards_active_count = Some(replacement.active_shard_ids_count);
        index.split_shards_parent_to_child_count = Some(replacement.parent_to_child_count);
        index.split_shards_parent_to_child = replacement.parent_to_child;
    } else if diff.split_shards_replacement_present == Some(false) {
        index.split_shards_root_count = None;
        index.split_shards_root_children.clear();
        index.split_shards_max_shard_id = None;
        index.split_shards_in_progress_count = None;
        index.split_shards_active_count = None;
        index.split_shards_parent_to_child_count = None;
        index.split_shards_parent_to_child.clear();
    }
    index.primary_terms_count = diff.primary_terms_count;
}

fn apply_setting_prefix_diff(items: &mut Vec<SettingPrefix>, diff: &DiffableStringMapDiffPrefix) {
    for key in &diff.deleted_keys {
        remove_by_key(items, key, |setting| setting.key.as_str());
    }
    for entry in &diff.upsert_entries {
        upsert_by_key(
            items,
            SettingPrefix {
                key: entry.key.clone(),
                value: Some(entry.value.clone()),
            },
            |setting| setting.key.as_str(),
        );
    }
}

fn apply_metadata_customs_diff(
    customs: &mut MetadataCustoms,
    diff: StringMapDiffEnvelope,
) -> Result<(), ClusterStateDecodeError> {
    if string_map_diff_envelope_is_empty(&diff) {
        return Ok(());
    }

    for key in &diff.deleted_keys {
        clear_metadata_custom(customs, key);
    }

    for repository_diff in diff.repository_metadata_diffs {
        if repository_diff.replacement_present {
            customs.repositories = repository_diff
                .replacement
                .into_iter()
                .map(Into::into)
                .collect();
        } else {
            customs.repositories.clear();
        }
    }
    for upsert in diff.repository_metadata_upserts {
        upsert_by_key(&mut customs.repositories, upsert, |repo| repo.name.as_str());
    }

    apply_component_template_custom_diff(
        &mut customs.component_templates,
        diff.component_template_diffs,
        diff.component_template_upserts,
    );
    apply_composable_template_custom_diff(
        &mut customs.composable_index_templates,
        diff.composable_index_template_diffs,
        diff.composable_index_template_upserts,
    );
    apply_data_stream_custom_diff(
        &mut customs.data_streams,
        diff.data_stream_diffs,
        diff.data_stream_upserts,
    );
    apply_view_custom_diff(&mut customs.views, diff.view_diffs, diff.view_upserts);
    apply_workload_group_custom_diff(
        &mut customs.workload_groups,
        diff.workload_group_diffs,
        diff.workload_group_upserts,
    );

    if !diff.ingest_upserts.is_empty() || diff.upsert_keys.iter().any(|key| key == "ingest") {
        customs.ingest_pipelines = diff.ingest_upserts;
    }
    if !diff.search_pipeline_upserts.is_empty()
        || diff.upsert_keys.iter().any(|key| key == "search_pipeline")
    {
        customs.search_pipelines = diff.search_pipeline_upserts;
    }
    if !diff.stored_script_upserts.is_empty()
        || diff.upsert_keys.iter().any(|key| key == "stored_scripts")
    {
        customs.stored_scripts = diff.stored_script_upserts;
    }
    if !diff.index_graveyard_tombstone_upserts.is_empty()
        || diff.upsert_keys.iter().any(|key| key == "index-graveyard")
    {
        customs.index_graveyard_tombstones = diff.index_graveyard_tombstone_upserts;
    }
    if !diff.persistent_task_upserts.is_empty()
        || diff.upsert_keys.iter().any(|key| key == "persistent_tasks")
    {
        customs.persistent_tasks = diff.persistent_task_upserts;
    }

    for decommission_diff in diff.decommission_attribute_diffs {
        customs.decommission_attribute = if decommission_diff.replacement_present {
            decommission_diff.replacement.map(Into::into)
        } else {
            None
        };
    }
    if let Some(upsert) = diff.decommission_attribute_upserts.into_iter().next() {
        customs.decommission_attribute = Some(upsert);
    }

    for weighted_diff in diff.weighted_routing_diffs {
        customs.weighted_routing = if weighted_diff.replacement_present {
            weighted_diff.replacement.map(Into::into)
        } else {
            None
        };
    }
    if let Some(upsert) = diff.weighted_routing_upserts.into_iter().next() {
        customs.weighted_routing = Some(upsert);
    }

    customs.declared_count = metadata_custom_declared_count(customs);
    Ok(())
}

fn string_map_diff_envelope_is_empty(diff: &StringMapDiffEnvelope) -> bool {
    diff.deleted_keys.is_empty()
        && diff.diff_keys.is_empty()
        && diff.upsert_keys.is_empty()
        && diff.index_metadata_diffs.is_empty()
        && diff.index_metadata_upserts.is_empty()
        && diff.index_routing_diffs.is_empty()
        && diff.index_routing_upserts.is_empty()
        && diff.index_template_diffs.is_empty()
        && diff.index_template_upserts.is_empty()
        && diff.repository_metadata_diffs.is_empty()
        && diff.repository_metadata_upserts.is_empty()
        && diff.component_template_diffs.is_empty()
        && diff.component_template_upserts.is_empty()
        && diff.composable_index_template_diffs.is_empty()
        && diff.composable_index_template_upserts.is_empty()
        && diff.data_stream_diffs.is_empty()
        && diff.data_stream_upserts.is_empty()
        && diff.ingest_upserts.is_empty()
        && diff.search_pipeline_upserts.is_empty()
        && diff.stored_script_upserts.is_empty()
        && diff.index_graveyard_tombstone_upserts.is_empty()
        && diff.persistent_task_upserts.is_empty()
        && diff.decommission_attribute_diffs.is_empty()
        && diff.decommission_attribute_upserts.is_empty()
        && diff.weighted_routing_diffs.is_empty()
        && diff.weighted_routing_upserts.is_empty()
        && diff.view_diffs.is_empty()
        && diff.view_upserts.is_empty()
        && diff.workload_group_diffs.is_empty()
        && diff.workload_group_upserts.is_empty()
        && diff.repository_cleanup_diffs.is_empty()
        && diff.repository_cleanup_upserts.is_empty()
        && diff.restore_diffs.is_empty()
        && diff.restore_upserts.is_empty()
        && diff.snapshot_deletions_diffs.is_empty()
        && diff.snapshot_deletions_upserts.is_empty()
        && diff.snapshots_diffs.is_empty()
        && diff.snapshots_upserts.is_empty()
}

fn clear_metadata_custom(customs: &mut MetadataCustoms, key: &str) {
    match key {
        "ingest" => customs.ingest_pipelines.clear(),
        "search_pipeline" => customs.search_pipelines.clear(),
        "stored_scripts" => customs.stored_scripts.clear(),
        "persistent_tasks" => customs.persistent_tasks.clear(),
        "decommissionedAttribute" => customs.decommission_attribute = None,
        "index-graveyard" => customs.index_graveyard_tombstones.clear(),
        "component_template" => customs.component_templates.clear(),
        "index_template" => customs.composable_index_templates.clear(),
        "data_stream" => customs.data_streams.clear(),
        "repositories" => customs.repositories.clear(),
        "weighted_shard_routing" => customs.weighted_routing = None,
        "view" => customs.views.clear(),
        "queryGroups" => customs.workload_groups.clear(),
        _ => {}
    }
}

fn metadata_custom_declared_count(customs: &MetadataCustoms) -> usize {
    usize::from(!customs.ingest_pipelines.is_empty())
        + usize::from(!customs.search_pipelines.is_empty())
        + usize::from(!customs.stored_scripts.is_empty())
        + usize::from(!customs.persistent_tasks.is_empty())
        + usize::from(customs.decommission_attribute.is_some())
        + usize::from(!customs.index_graveyard_tombstones.is_empty())
        + usize::from(!customs.component_templates.is_empty())
        + usize::from(!customs.composable_index_templates.is_empty())
        + usize::from(!customs.data_streams.is_empty())
        + usize::from(!customs.repositories.is_empty())
        + usize::from(customs.weighted_routing.is_some())
        + usize::from(!customs.views.is_empty())
        + usize::from(!customs.workload_groups.is_empty())
}

fn apply_cluster_state_customs_diff(
    customs: &mut ClusterStateCustoms,
    diff: StringMapDiffEnvelope,
) {
    for key in &diff.deleted_keys {
        clear_cluster_state_custom(customs, key);
    }
    for item_diff in diff.repository_cleanup_diffs {
        customs.repository_cleanup = if item_diff.replacement_present {
            item_diff.replacement.map(Into::into)
        } else {
            None
        };
    }
    if let Some(upsert) = diff.repository_cleanup_upserts.into_iter().next() {
        customs.repository_cleanup = Some(upsert);
    }
    for item_diff in diff.restore_diffs {
        customs.restore = if item_diff.replacement_present {
            item_diff.replacement.map(Into::into)
        } else {
            None
        };
    }
    if let Some(upsert) = diff.restore_upserts.into_iter().next() {
        customs.restore = Some(upsert);
    }
    for item_diff in diff.snapshot_deletions_diffs {
        customs.snapshot_deletions = if item_diff.replacement_present {
            item_diff.replacement.map(Into::into)
        } else {
            None
        };
    }
    if let Some(upsert) = diff.snapshot_deletions_upserts.into_iter().next() {
        customs.snapshot_deletions = Some(upsert);
    }
    for item_diff in diff.snapshots_diffs {
        customs.snapshots = if item_diff.replacement_present {
            item_diff.replacement.map(Into::into)
        } else {
            None
        };
    }
    if let Some(upsert) = diff.snapshots_upserts.into_iter().next() {
        customs.snapshots = Some(upsert);
    }
    refresh_cluster_state_custom_names(customs);
}

fn clear_cluster_state_custom(customs: &mut ClusterStateCustoms, key: &str) {
    match key {
        "repository_cleanup" => customs.repository_cleanup = None,
        "restore" => customs.restore = None,
        "snapshot_deletions" => customs.snapshot_deletions = None,
        "snapshots" => customs.snapshots = None,
        _ => {}
    }
}

fn refresh_cluster_state_custom_names(customs: &mut ClusterStateCustoms) {
    let mut names = Vec::new();
    if customs.repository_cleanup.is_some() {
        names.push("repository_cleanup".to_string());
    }
    if customs.snapshot_deletions.is_some() {
        names.push("snapshot_deletions".to_string());
    }
    if customs.restore.is_some() {
        names.push("restore".to_string());
    }
    if customs.snapshots.is_some() {
        names.push("snapshots".to_string());
    }
    customs.declared_count = names.len();
    customs.names = names;
}

fn apply_component_template_custom_diff(
    items: &mut Vec<ComponentTemplate>,
    diffs: Vec<ComponentTemplateMetadataCustomDiffPrefix>,
    upserts: Vec<ComponentTemplate>,
) {
    for custom_diff in diffs {
        for key in &custom_diff.deleted_keys {
            remove_by_key(items, key, |item| item.name.as_str());
        }
        for (key, item_diff) in custom_diff
            .diff_keys
            .iter()
            .zip(custom_diff.replacement_diffs)
        {
            if item_diff.replacement_present {
                if let Some(replacement) = item_diff.replacement {
                    upsert_by_key(items, replacement.into(), |item| item.name.as_str());
                }
            } else {
                remove_by_key(items, key, |item| item.name.as_str());
            }
        }
        for upsert in custom_diff.upserts {
            upsert_by_key(items, upsert.into(), |item| item.name.as_str());
        }
    }
    for upsert in upserts {
        upsert_by_key(items, upsert, |item| item.name.as_str());
    }
}

fn apply_composable_template_custom_diff(
    items: &mut Vec<ComposableIndexTemplate>,
    diffs: Vec<ComposableIndexTemplateMetadataCustomDiffPrefix>,
    upserts: Vec<ComposableIndexTemplate>,
) {
    for custom_diff in diffs {
        for key in &custom_diff.deleted_keys {
            remove_by_key(items, key, |item| item.name.as_str());
        }
        for (key, item_diff) in custom_diff
            .diff_keys
            .iter()
            .zip(custom_diff.replacement_diffs)
        {
            if item_diff.replacement_present {
                if let Some(replacement) = item_diff.replacement {
                    upsert_by_key(items, replacement.into(), |item| item.name.as_str());
                }
            } else {
                remove_by_key(items, key, |item| item.name.as_str());
            }
        }
        for upsert in custom_diff.upserts {
            upsert_by_key(items, upsert.into(), |item| item.name.as_str());
        }
    }
    for upsert in upserts {
        upsert_by_key(items, upsert, |item| item.name.as_str());
    }
}

fn apply_data_stream_custom_diff(
    items: &mut Vec<DataStream>,
    diffs: Vec<DataStreamMetadataCustomDiffPrefix>,
    upserts: Vec<DataStream>,
) {
    for custom_diff in diffs {
        for key in &custom_diff.deleted_keys {
            remove_by_key(items, key, |item| item.name.as_str());
        }
        for (key, item_diff) in custom_diff
            .diff_keys
            .iter()
            .zip(custom_diff.replacement_diffs)
        {
            if item_diff.replacement_present {
                if let Some(replacement) = item_diff.replacement {
                    upsert_by_key(items, replacement.into(), |item| item.name.as_str());
                }
            } else {
                remove_by_key(items, key, |item| item.name.as_str());
            }
        }
        for upsert in custom_diff.upserts {
            upsert_by_key(items, upsert.into(), |item| item.name.as_str());
        }
    }
    for upsert in upserts {
        upsert_by_key(items, upsert, |item| item.name.as_str());
    }
}

fn apply_view_custom_diff(
    items: &mut Vec<ViewMetadata>,
    diffs: Vec<ViewMetadataCustomDiffPrefix>,
    upserts: Vec<ViewMetadata>,
) {
    for custom_diff in diffs {
        for key in &custom_diff.deleted_keys {
            remove_by_key(items, key, |item| item.name.as_str());
        }
        for (key, item_diff) in custom_diff
            .diff_keys
            .iter()
            .zip(custom_diff.replacement_diffs)
        {
            if item_diff.replacement_present {
                if let Some(replacement) = item_diff.replacement {
                    upsert_by_key(items, replacement.into(), |item| item.name.as_str());
                }
            } else {
                remove_by_key(items, key, |item| item.name.as_str());
            }
        }
        for upsert in custom_diff.upserts {
            upsert_by_key(items, upsert.into(), |item| item.name.as_str());
        }
    }
    for upsert in upserts {
        upsert_by_key(items, upsert, |item| item.name.as_str());
    }
}

fn apply_workload_group_custom_diff(
    items: &mut Vec<WorkloadGroup>,
    diffs: Vec<WorkloadGroupMetadataCustomDiffPrefix>,
    upserts: Vec<WorkloadGroup>,
) {
    for custom_diff in diffs {
        for key in &custom_diff.deleted_keys {
            remove_by_key(items, key, |item| item.name.as_str());
        }
        for (key, item_diff) in custom_diff
            .diff_keys
            .iter()
            .zip(custom_diff.replacement_diffs)
        {
            if item_diff.replacement_present {
                if let Some(replacement) = item_diff.replacement {
                    upsert_by_key(items, replacement.into(), |item| item.name.as_str());
                }
            } else {
                remove_by_key(items, key, |item| item.name.as_str());
            }
        }
        for upsert in custom_diff.upserts {
            upsert_by_key(items, upsert.into(), |item| item.name.as_str());
        }
    }
    for upsert in upserts {
        upsert_by_key(items, upsert, |item| item.name.as_str());
    }
}

impl From<MetadataPrefix> for Metadata {
    fn from(prefix: MetadataPrefix) -> Self {
        Self {
            version: prefix.version,
            cluster_uuid: prefix.cluster_uuid,
            cluster_uuid_committed: prefix.cluster_uuid_committed,
            coordination: prefix.coordination.into(),
            transient_settings: prefix
                .transient_settings
                .into_iter()
                .map(Into::into)
                .collect(),
            persistent_settings: prefix
                .persistent_settings
                .into_iter()
                .map(Into::into)
                .collect(),
            hashes_of_consistent_settings: prefix
                .hashes_of_consistent_settings
                .into_iter()
                .map(Into::into)
                .collect(),
            index_metadata: prefix.index_metadata.into_iter().map(Into::into).collect(),
            templates: prefix.templates.into_iter().map(Into::into).collect(),
            customs: MetadataCustoms {
                declared_count: prefix.custom_metadata_count,
                ingest_pipelines: prefix
                    .ingest_pipelines
                    .into_iter()
                    .map(Into::into)
                    .collect(),
                search_pipelines: prefix
                    .search_pipelines
                    .into_iter()
                    .map(Into::into)
                    .collect(),
                stored_scripts: prefix.stored_scripts.into_iter().map(Into::into).collect(),
                persistent_tasks: prefix
                    .persistent_tasks
                    .into_iter()
                    .map(Into::into)
                    .collect(),
                decommission_attribute: prefix.decommission_attribute.map(Into::into),
                index_graveyard_tombstones: prefix
                    .index_graveyard_tombstones
                    .into_iter()
                    .map(Into::into)
                    .collect(),
                component_templates: prefix
                    .component_templates
                    .into_iter()
                    .map(Into::into)
                    .collect(),
                composable_index_templates: prefix
                    .composable_index_templates
                    .into_iter()
                    .map(Into::into)
                    .collect(),
                data_streams: prefix.data_streams.into_iter().map(Into::into).collect(),
                repositories: prefix.repositories.into_iter().map(Into::into).collect(),
                weighted_routing: prefix.weighted_routing.map(Into::into),
                views: prefix.views.into_iter().map(Into::into).collect(),
                workload_groups: prefix.workload_groups.into_iter().map(Into::into).collect(),
            },
        }
    }
}

impl From<SettingPrefix> for Setting {
    fn from(prefix: SettingPrefix) -> Self {
        Self {
            key: prefix.key,
            value: prefix.value,
        }
    }
}

impl From<IndexMetadataPrefix> for IndexMetadata {
    fn from(prefix: IndexMetadataPrefix) -> Self {
        Self {
            name: prefix.name,
            version: prefix.version,
            mapping_version: prefix.mapping_version,
            settings_version: prefix.settings_version,
            aliases_version: prefix.aliases_version,
            routing_num_shards: prefix.routing_num_shards,
            state_id: prefix.state_id,
            settings_count: prefix.settings_count,
            index_uuid: prefix.index_uuid,
            number_of_shards: prefix.number_of_shards,
            number_of_replicas: prefix.number_of_replicas,
            mapping_count: prefix.mapping_count,
            mappings: prefix.mappings,
            alias_count: prefix.alias_count,
            aliases: prefix.aliases,
            custom_data_count: prefix.custom_data_count,
            custom_data: prefix.custom_data,
            in_sync_allocation_ids_count: prefix.in_sync_allocation_ids_count,
            rollover_info_count: prefix.rollover_info_count,
            rollover_infos: prefix.rollover_infos,
            system: prefix.system,
            context_present: prefix.context_present,
            ingestion_status_present: prefix.ingestion_status_present,
            ingestion_paused: prefix.ingestion_paused,
            split_shards_root_count: prefix.split_shards_root_count,
            split_shards_root_children: prefix.split_shards_root_children,
            split_shards_max_shard_id: prefix.split_shards_max_shard_id,
            split_shards_in_progress_count: prefix.split_shards_in_progress_count,
            split_shards_active_count: prefix.split_shards_active_count,
            split_shards_parent_to_child_count: prefix.split_shards_parent_to_child_count,
            split_shards_parent_to_child: prefix.split_shards_parent_to_child,
            primary_terms_count: prefix.primary_terms_count,
        }
    }
}

impl From<IndexTemplateMetadataPrefix> for IndexTemplateMetadata {
    fn from(prefix: IndexTemplateMetadataPrefix) -> Self {
        Self {
            name: prefix.name,
            order: prefix.order,
            patterns: prefix.patterns,
            settings_count: prefix.settings_count,
            settings: prefix.settings.into_iter().map(Into::into).collect(),
            mappings_count: prefix.mappings_count,
            mappings: prefix.mappings,
            aliases_count: prefix.aliases_count,
            aliases: prefix.aliases,
            version: prefix.version,
        }
    }
}

impl From<IngestPipelinePrefix> for IngestPipeline {
    fn from(prefix: IngestPipelinePrefix) -> Self {
        Self {
            id: prefix.id,
            config_len: prefix.config_len,
            media_type: prefix.media_type,
        }
    }
}

impl From<SearchPipelinePrefix> for SearchPipeline {
    fn from(prefix: SearchPipelinePrefix) -> Self {
        Self {
            id: prefix.id,
            config_len: prefix.config_len,
            media_type: prefix.media_type,
        }
    }
}

impl From<StoredScriptPrefix> for StoredScript {
    fn from(prefix: StoredScriptPrefix) -> Self {
        Self {
            id: prefix.id,
            lang: prefix.lang,
            source_len: prefix.source_len,
            options_count: prefix.options_count,
        }
    }
}

impl From<PersistentTaskPrefix> for PersistentTask {
    fn from(prefix: PersistentTaskPrefix) -> Self {
        Self {
            map_key: prefix.map_key,
            id: prefix.id,
            allocation_id: prefix.allocation_id,
            task_name: prefix.task_name,
            params_name: prefix.params_name,
            fixture_params_marker: prefix.fixture_params_marker,
            fixture_params_generation: prefix.fixture_params_generation,
            state_name: prefix.state_name,
            fixture_state_marker: prefix.fixture_state_marker,
            fixture_state_generation: prefix.fixture_state_generation,
            executor_node: prefix.executor_node,
            assignment_explanation: prefix.assignment_explanation,
            allocation_id_on_last_status_update: prefix.allocation_id_on_last_status_update,
        }
    }
}

impl From<IndexGraveyardTombstonePrefix> for IndexGraveyardTombstone {
    fn from(prefix: IndexGraveyardTombstonePrefix) -> Self {
        Self {
            index_name: prefix.index_name,
            index_uuid: prefix.index_uuid,
            delete_date_in_millis: prefix.delete_date_in_millis,
        }
    }
}

impl From<RepositoryMetadataPrefix> for RepositoryMetadata {
    fn from(prefix: RepositoryMetadataPrefix) -> Self {
        Self {
            name: prefix.name,
            repository_type: prefix.repository_type,
            settings_count: prefix.settings_count,
            settings: prefix.settings.into_iter().map(Into::into).collect(),
            generation: prefix.generation,
            pending_generation: prefix.pending_generation,
            crypto_metadata_present: prefix.crypto_metadata_present,
            crypto_key_provider_name: prefix.crypto_key_provider_name,
            crypto_key_provider_type: prefix.crypto_key_provider_type,
            crypto_settings_count: prefix.crypto_settings_count,
            crypto_settings: prefix.crypto_settings.into_iter().map(Into::into).collect(),
        }
    }
}

impl From<ComponentTemplatePrefix> for ComponentTemplate {
    fn from(prefix: ComponentTemplatePrefix) -> Self {
        Self {
            name: prefix.name,
            settings_count: prefix.settings_count,
            settings: prefix.settings.into_iter().map(Into::into).collect(),
            mappings_present: prefix.mappings_present,
            mapping: prefix.mapping,
            aliases_count: prefix.aliases_count,
            aliases: prefix.aliases,
            version: prefix.version,
            metadata_present: prefix.metadata_present,
            metadata_count: prefix.metadata_count,
            metadata: prefix.metadata.into_iter().map(Into::into).collect(),
        }
    }
}

impl From<ComposableIndexTemplatePrefix> for ComposableIndexTemplate {
    fn from(prefix: ComposableIndexTemplatePrefix) -> Self {
        Self {
            name: prefix.name,
            index_patterns: prefix.index_patterns,
            template_present: prefix.template_present,
            template_settings_count: prefix.template_settings_count,
            template_settings: prefix
                .template_settings
                .into_iter()
                .map(Into::into)
                .collect(),
            template_mappings_present: prefix.template_mappings_present,
            template_mapping: prefix.template_mapping,
            template_aliases_count: prefix.template_aliases_count,
            template_aliases: prefix.template_aliases,
            component_templates_count: prefix.component_templates_count,
            component_templates: prefix.component_templates,
            priority: prefix.priority,
            version: prefix.version,
            metadata_count: prefix.metadata_count,
            metadata: prefix.metadata.into_iter().map(Into::into).collect(),
            data_stream_template_present: prefix.data_stream_template_present,
            data_stream_timestamp_field: prefix.data_stream_timestamp_field,
            context_present: prefix.context_present,
            context_name: prefix.context_name,
            context_version: prefix.context_version,
            context_params_count: prefix.context_params_count,
            context_params: prefix.context_params.into_iter().map(Into::into).collect(),
        }
    }
}

impl From<DataStreamPrefix> for DataStream {
    fn from(prefix: DataStreamPrefix) -> Self {
        Self {
            name: prefix.name,
            timestamp_field: prefix.timestamp_field,
            backing_indices_count: prefix.backing_indices_count,
            backing_indices: prefix.backing_indices.into_iter().map(Into::into).collect(),
            generation: prefix.generation,
        }
    }
}

impl From<DataStreamBackingIndexPrefix> for DataStreamBackingIndex {
    fn from(prefix: DataStreamBackingIndexPrefix) -> Self {
        Self {
            name: prefix.name,
            uuid: prefix.uuid,
        }
    }
}

impl From<DecommissionAttributeMetadataPrefix> for DecommissionAttributeMetadata {
    fn from(prefix: DecommissionAttributeMetadataPrefix) -> Self {
        Self {
            attribute_name: prefix.attribute_name,
            attribute_value: prefix.attribute_value,
            status: prefix.status,
            request_id: prefix.request_id,
        }
    }
}

impl From<WeightedRoutingMetadataPrefix> for WeightedRoutingMetadata {
    fn from(prefix: WeightedRoutingMetadataPrefix) -> Self {
        Self {
            awareness_attribute: prefix.awareness_attribute,
            weights: prefix.weights.into_iter().map(Into::into).collect(),
            version: prefix.version,
        }
    }
}

impl From<ViewMetadataPrefix> for ViewMetadata {
    fn from(prefix: ViewMetadataPrefix) -> Self {
        Self {
            name: prefix.name,
            description: prefix.description,
            created_at: prefix.created_at,
            modified_at: prefix.modified_at,
            target_index_patterns: prefix.target_index_patterns,
        }
    }
}

impl From<WorkloadGroupPrefix> for WorkloadGroup {
    fn from(prefix: WorkloadGroupPrefix) -> Self {
        Self {
            name: prefix.name,
            id: prefix.id,
            resource_limits: prefix.resource_limits.into_iter().map(Into::into).collect(),
            resiliency_mode: prefix.resiliency_mode,
            search_settings: prefix.search_settings.into_iter().map(Into::into).collect(),
            updated_at_millis: prefix.updated_at_millis,
        }
    }
}

impl From<CoordinationMetadataPrefix> for CoordinationMetadata {
    fn from(prefix: CoordinationMetadataPrefix) -> Self {
        Self {
            term: prefix.term,
            last_committed_configuration: prefix.last_committed_configuration,
            last_accepted_configuration: prefix.last_accepted_configuration,
            voting_config_exclusions: prefix.voting_config_exclusions,
        }
    }
}

impl From<RoutingTablePrefix> for RoutingTable {
    fn from(prefix: RoutingTablePrefix) -> Self {
        Self {
            version: prefix.version,
            indices: prefix.indices.into_iter().map(Into::into).collect(),
        }
    }
}

impl From<IndexRoutingTablePrefix> for IndexRoutingTable {
    fn from(prefix: IndexRoutingTablePrefix) -> Self {
        Self {
            index_name: prefix.index_name,
            index_uuid: prefix.index_uuid,
            shards: prefix.shards.into_iter().map(Into::into).collect(),
        }
    }
}

impl From<IndexShardRoutingTablePrefix> for IndexShardRoutingTable {
    fn from(prefix: IndexShardRoutingTablePrefix) -> Self {
        Self {
            shard_id: prefix.shard_id,
            shard_routings: prefix.shard_routings.into_iter().map(Into::into).collect(),
        }
    }
}

impl From<ShardRoutingPrefix> for ShardRouting {
    fn from(prefix: ShardRoutingPrefix) -> Self {
        Self {
            current_node_id: prefix.current_node_id,
            relocating_node_id: prefix.relocating_node_id,
            primary: prefix.primary,
            search_only: prefix.search_only,
            state: prefix.state.into(),
            recovery_source_type: prefix.recovery_source_type.map(Into::into),
            recovery_source_bootstrap_new_history_uuid: prefix
                .recovery_source_bootstrap_new_history_uuid,
            snapshot_recovery_source: prefix.snapshot_recovery_source.map(Into::into),
            remote_store_recovery_source: prefix.remote_store_recovery_source.map(Into::into),
            unassigned_info: prefix.unassigned_info.map(Into::into),
            allocation_id_present: prefix.allocation_id_present,
            allocation_id: prefix.allocation_id.map(Into::into),
            expected_shard_size: prefix.expected_shard_size,
        }
    }
}

impl From<ShardRoutingStatePrefix> for ShardRoutingState {
    fn from(prefix: ShardRoutingStatePrefix) -> Self {
        match prefix {
            ShardRoutingStatePrefix::Unassigned => Self::Unassigned,
            ShardRoutingStatePrefix::Initializing => Self::Initializing,
            ShardRoutingStatePrefix::Started => Self::Started,
            ShardRoutingStatePrefix::Relocating => Self::Relocating,
            ShardRoutingStatePrefix::Splitting => Self::Splitting,
        }
    }
}

impl From<RecoverySourceTypePrefix> for RecoverySourceType {
    fn from(prefix: RecoverySourceTypePrefix) -> Self {
        match prefix {
            RecoverySourceTypePrefix::EmptyStore => Self::EmptyStore,
            RecoverySourceTypePrefix::ExistingStore => Self::ExistingStore,
            RecoverySourceTypePrefix::Peer => Self::Peer,
            RecoverySourceTypePrefix::Snapshot => Self::Snapshot,
            RecoverySourceTypePrefix::LocalShards => Self::LocalShards,
            RecoverySourceTypePrefix::RemoteStore => Self::RemoteStore,
            RecoverySourceTypePrefix::InPlaceSplitShard => Self::InPlaceSplitShard,
        }
    }
}

impl From<SnapshotRecoverySourcePrefix> for SnapshotRecoverySource {
    fn from(prefix: SnapshotRecoverySourcePrefix) -> Self {
        Self {
            restore_uuid: prefix.restore_uuid,
            repository: prefix.repository,
            snapshot_name: prefix.snapshot_name,
            snapshot_uuid: prefix.snapshot_uuid,
            version_id: prefix.version_id,
            index_name: prefix.index_name,
            index_id: prefix.index_id,
            index_shard_path_type: prefix.index_shard_path_type,
            is_searchable_snapshot: prefix.is_searchable_snapshot,
            remote_store_index_shallow_copy: prefix.remote_store_index_shallow_copy,
            source_remote_store_repository: prefix.source_remote_store_repository,
            source_remote_translog_repository: prefix.source_remote_translog_repository,
            pinned_timestamp: prefix.pinned_timestamp,
        }
    }
}

impl From<RemoteStoreRecoverySourcePrefix> for RemoteStoreRecoverySource {
    fn from(prefix: RemoteStoreRecoverySourcePrefix) -> Self {
        Self {
            restore_uuid: prefix.restore_uuid,
            version_id: prefix.version_id,
            index_name: prefix.index_name,
            index_id: prefix.index_id,
            index_shard_path_type: prefix.index_shard_path_type,
        }
    }
}

impl From<UnassignedInfoPrefix> for UnassignedInfo {
    fn from(prefix: UnassignedInfoPrefix) -> Self {
        Self {
            reason_id: prefix.reason_id,
            unassigned_time_millis: prefix.unassigned_time_millis,
            delayed: prefix.delayed,
            message: prefix.message,
            failure: prefix.failure.map(Into::into),
            failed_allocations: prefix.failed_allocations,
            last_allocation_status_id: prefix.last_allocation_status_id,
            failed_node_ids_count: prefix.failed_node_ids_count,
        }
    }
}

impl From<UnassignedFailurePrefix> for UnassignedFailure {
    fn from(prefix: UnassignedFailurePrefix) -> Self {
        Self {
            class_name: prefix.class_name,
            message: prefix.message,
            summary: prefix.summary,
        }
    }
}

impl From<AllocationIdPrefix> for AllocationId {
    fn from(prefix: AllocationIdPrefix) -> Self {
        Self {
            id: prefix.id,
            relocation_id: prefix.relocation_id,
            split_child_allocation_ids_count: prefix.split_child_allocation_ids_count,
            parent_allocation_id: prefix.parent_allocation_id,
        }
    }
}

impl From<DiscoveryNodesPrefix> for DiscoveryNodes {
    fn from(prefix: DiscoveryNodesPrefix) -> Self {
        Self {
            cluster_manager_node_id: prefix.cluster_manager_node_id,
            nodes: prefix.nodes.into_iter().map(Into::into).collect(),
        }
    }
}

impl From<DiscoveryNodePrefix> for DiscoveryNode {
    fn from(prefix: DiscoveryNodePrefix) -> Self {
        Self {
            name: prefix.name,
            id: prefix.id,
            ephemeral_id: prefix.ephemeral_id,
            host_name: prefix.host_name,
            host_address: prefix.host_address,
            address: prefix.address.into(),
            stream_address: prefix.stream_address.map(Into::into),
            skipped_attribute_count: prefix.attribute_count,
            roles: prefix.roles.into_iter().map(Into::into).collect(),
            version: prefix.version,
        }
    }
}

impl From<TransportAddressPrefix> for TransportAddress {
    fn from(prefix: TransportAddressPrefix) -> Self {
        Self {
            ip: prefix.ip,
            host: prefix.host,
            port: prefix.port,
        }
    }
}

impl From<DiscoveryNodeRolePrefix> for DiscoveryNodeRole {
    fn from(prefix: DiscoveryNodeRolePrefix) -> Self {
        Self {
            name: prefix.name,
            abbreviation: prefix.abbreviation,
            can_contain_data: prefix.can_contain_data,
        }
    }
}

impl From<ClusterBlocksPrefix> for ClusterBlocks {
    fn from(prefix: ClusterBlocksPrefix) -> Self {
        Self {
            global_blocks: prefix.global_blocks.into_iter().map(Into::into).collect(),
            index_blocks: prefix.index_blocks.into_iter().map(Into::into).collect(),
        }
    }
}

impl From<IndexClusterBlocksPrefix> for IndexClusterBlocks {
    fn from(prefix: IndexClusterBlocksPrefix) -> Self {
        Self {
            index_name: prefix.index_name,
            blocks: prefix.blocks.into_iter().map(Into::into).collect(),
        }
    }
}

impl From<ClusterBlockPrefix> for ClusterBlock {
    fn from(prefix: ClusterBlockPrefix) -> Self {
        Self {
            id: prefix.id,
            uuid: prefix.uuid,
            description: prefix.description,
            levels: prefix.levels.into_iter().map(Into::into).collect(),
            retryable: prefix.retryable,
            disable_state_persistence: prefix.disable_state_persistence,
            status: prefix.status,
            allow_release_resources: prefix.allow_release_resources,
        }
    }
}

impl From<ClusterBlockLevelPrefix> for ClusterBlockLevel {
    fn from(prefix: ClusterBlockLevelPrefix) -> Self {
        match prefix {
            ClusterBlockLevelPrefix::Read => Self::Read,
            ClusterBlockLevelPrefix::Write => Self::Write,
            ClusterBlockLevelPrefix::MetadataRead => Self::MetadataRead,
            ClusterBlockLevelPrefix::MetadataWrite => Self::MetadataWrite,
            ClusterBlockLevelPrefix::CreateIndex => Self::CreateIndex,
        }
    }
}

impl From<ClusterStateTailPrefix> for ClusterStateCustoms {
    fn from(prefix: ClusterStateTailPrefix) -> Self {
        Self {
            declared_count: prefix.custom_count,
            names: prefix.custom_names,
            repository_cleanup: prefix.repository_cleanup.map(Into::into),
            snapshot_deletions: prefix.snapshot_deletions.map(Into::into),
            restore: prefix.restore.map(Into::into),
            snapshots: prefix.snapshots.map(Into::into),
            minimum_cluster_manager_nodes_on_publishing_cluster_manager: prefix
                .minimum_cluster_manager_nodes_on_publishing_cluster_manager,
        }
    }
}

impl From<RepositoryCleanupInProgressPrefix> for RepositoryCleanupInProgress {
    fn from(prefix: RepositoryCleanupInProgressPrefix) -> Self {
        Self {
            entry_count: prefix.entry_count,
            entries: prefix.entries,
        }
    }
}

impl From<SnapshotDeletionsInProgressPrefix> for SnapshotDeletionsInProgress {
    fn from(prefix: SnapshotDeletionsInProgressPrefix) -> Self {
        Self {
            entry_count: prefix.entry_count,
            entries: prefix.entries,
        }
    }
}

impl From<RestoreInProgressPrefix> for RestoreInProgress {
    fn from(prefix: RestoreInProgressPrefix) -> Self {
        Self {
            entry_count: prefix.entry_count,
            entries: prefix.entries,
        }
    }
}

impl From<SnapshotsInProgressPrefix> for SnapshotsInProgress {
    fn from(prefix: SnapshotsInProgressPrefix) -> Self {
        Self {
            entry_count: prefix.entry_count,
            entries: prefix.entries,
        }
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
    let metadata_coordination = read_coordination_metadata_prefix(&mut input)?;
    let metadata_transient_settings =
        read_settings_prefix(&mut input, "cluster_state.diff.metadata.transient_settings")?;
    let metadata_persistent_settings = read_settings_prefix(
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
        _stream_version,
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
        metadata_coordination,
        metadata_transient_settings,
        metadata_persistent_settings,
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

pub fn read_publication_cluster_state_diff(
    bytes: Bytes,
    stream_version: Version,
) -> Result<PublicationClusterStateDiff, ClusterStateDecodeError> {
    read_publication_cluster_state_diff_prefix(bytes, stream_version).map(Into::into)
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

type MetadataCustomReader =
    fn(&mut StreamInput, Version) -> Result<MetadataCustomPayload, ClusterStateDecodeError>;

struct MetadataCustomRegistryEntry {
    name: &'static str,
    reader: MetadataCustomReader,
}

enum MetadataCustomPayload {
    Ingest(Vec<IngestPipelinePrefix>),
    SearchPipeline(Vec<SearchPipelinePrefix>),
    StoredScripts(Vec<StoredScriptPrefix>),
    PersistentTasks(Vec<PersistentTaskPrefix>),
    DecommissionedAttribute(DecommissionAttributeMetadataPrefix),
    IndexGraveyard(Vec<IndexGraveyardTombstonePrefix>),
    ComponentTemplate(Vec<ComponentTemplatePrefix>),
    ComposableIndexTemplate(Vec<ComposableIndexTemplatePrefix>),
    DataStream(Vec<DataStreamPrefix>),
    Repositories(Vec<RepositoryMetadataPrefix>),
    WeightedShardRouting(WeightedRoutingMetadataPrefix),
    View(Vec<ViewMetadataPrefix>),
    WorkloadGroups(Vec<WorkloadGroupPrefix>),
}

const METADATA_CUSTOM_REGISTRY: &[MetadataCustomRegistryEntry] = &[
    MetadataCustomRegistryEntry {
        name: "ingest",
        reader: read_ingest_metadata_custom_payload,
    },
    MetadataCustomRegistryEntry {
        name: "search_pipeline",
        reader: read_search_pipeline_metadata_custom_payload,
    },
    MetadataCustomRegistryEntry {
        name: "stored_scripts",
        reader: read_stored_scripts_metadata_custom_payload,
    },
    MetadataCustomRegistryEntry {
        name: "persistent_tasks",
        reader: read_persistent_tasks_metadata_custom_payload,
    },
    MetadataCustomRegistryEntry {
        name: "decommissionedAttribute",
        reader: read_decommissioned_attribute_metadata_custom_payload,
    },
    MetadataCustomRegistryEntry {
        name: "index-graveyard",
        reader: read_index_graveyard_metadata_custom_payload,
    },
    MetadataCustomRegistryEntry {
        name: "component_template",
        reader: read_component_template_metadata_custom_payload,
    },
    MetadataCustomRegistryEntry {
        name: "index_template",
        reader: read_composable_index_template_metadata_custom_payload,
    },
    MetadataCustomRegistryEntry {
        name: "data_stream",
        reader: read_data_stream_metadata_custom_payload,
    },
    MetadataCustomRegistryEntry {
        name: "repositories",
        reader: read_repositories_metadata_custom_payload,
    },
    MetadataCustomRegistryEntry {
        name: "weighted_shard_routing",
        reader: read_weighted_shard_routing_metadata_custom_payload,
    },
    MetadataCustomRegistryEntry {
        name: "view",
        reader: read_view_metadata_custom_payload,
    },
    MetadataCustomRegistryEntry {
        name: "queryGroups",
        reader: read_workload_groups_metadata_custom_payload,
    },
];

fn metadata_custom_reader(name: &str) -> Option<MetadataCustomReader> {
    METADATA_CUSTOM_REGISTRY
        .iter()
        .find_map(|entry| (entry.name == name).then_some(entry.reader))
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

fn read_ingest_metadata_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    let mut pipelines = Vec::with_capacity(count);
    for _ in 0..count {
        pipelines.push(read_ingest_pipeline_prefix(input)?);
    }
    Ok(MetadataCustomPayload::Ingest(pipelines))
}

fn read_search_pipeline_metadata_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    let mut pipelines = Vec::with_capacity(count);
    for _ in 0..count {
        pipelines.push(read_search_pipeline_prefix(input)?);
    }
    Ok(MetadataCustomPayload::SearchPipeline(pipelines))
}

fn read_stored_scripts_metadata_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    let mut scripts = Vec::with_capacity(count);
    for _ in 0..count {
        scripts.push(read_stored_script_prefix(input)?);
    }
    Ok(MetadataCustomPayload::StoredScripts(scripts))
}

fn read_persistent_tasks_metadata_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    let _last_allocation_id = input.read_i64()?;
    let count = read_non_negative_len(input)?;
    let mut tasks = Vec::with_capacity(count);
    for _ in 0..count {
        let map_key = input.read_string()?;
        tasks.push(read_persistent_task_prefix(input, map_key)?);
    }
    Ok(MetadataCustomPayload::PersistentTasks(tasks))
}

fn read_decommissioned_attribute_metadata_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    Ok(MetadataCustomPayload::DecommissionedAttribute(
        read_decommission_attribute_metadata_prefix(input)?,
    ))
}

fn read_index_graveyard_metadata_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    let mut tombstones = Vec::with_capacity(count);
    for _ in 0..count {
        tombstones.push(read_index_graveyard_tombstone_prefix(input)?);
    }
    Ok(MetadataCustomPayload::IndexGraveyard(tombstones))
}

fn read_component_template_metadata_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    let mut templates = Vec::with_capacity(count);
    for _ in 0..count {
        templates.push(read_component_template_prefix(input)?);
    }
    Ok(MetadataCustomPayload::ComponentTemplate(templates))
}

fn read_composable_index_template_metadata_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    let mut templates = Vec::with_capacity(count);
    for _ in 0..count {
        templates.push(read_composable_index_template_prefix(input)?);
    }
    Ok(MetadataCustomPayload::ComposableIndexTemplate(templates))
}

fn read_data_stream_metadata_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    let mut data_streams = Vec::with_capacity(count);
    for _ in 0..count {
        let _key = input.read_string()?;
        data_streams.push(read_data_stream_prefix(input)?);
    }
    Ok(MetadataCustomPayload::DataStream(data_streams))
}

fn read_repositories_metadata_custom_payload(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    let mut repositories = Vec::with_capacity(count);
    for _ in 0..count {
        repositories.push(read_repository_metadata_prefix(input, stream_version)?);
    }
    Ok(MetadataCustomPayload::Repositories(repositories))
}

fn read_weighted_shard_routing_metadata_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    Ok(MetadataCustomPayload::WeightedShardRouting(
        read_weighted_routing_metadata_prefix(input)?,
    ))
}

fn read_view_metadata_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    let mut views = Vec::with_capacity(count);
    for _ in 0..count {
        let _key = input.read_string()?;
        views.push(read_view_metadata_prefix(input)?);
    }
    Ok(MetadataCustomPayload::View(views))
}

fn read_workload_groups_metadata_custom_payload(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<MetadataCustomPayload, ClusterStateDecodeError> {
    let count = read_non_negative_len(input)?;
    let mut workload_groups = Vec::with_capacity(count);
    for _ in 0..count {
        let _key = input.read_string()?;
        workload_groups.push(read_workload_group_prefix(input, stream_version)?);
    }
    Ok(MetadataCustomPayload::WorkloadGroups(workload_groups))
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
        let reader = metadata_custom_reader(&name).ok_or(
            ClusterStateDecodeError::UnsupportedNamedWriteable {
                section: "metadata.custom",
                name,
            },
        )?;
        match reader(input, stream_version)? {
            MetadataCustomPayload::Ingest(items) => {
                ingest_pipelines_count = Some(items.len());
                ingest_pipelines = items;
            }
            MetadataCustomPayload::SearchPipeline(items) => {
                search_pipelines_count = Some(items.len());
                search_pipelines = items;
            }
            MetadataCustomPayload::StoredScripts(items) => {
                stored_scripts_count = Some(items.len());
                stored_scripts = items;
            }
            MetadataCustomPayload::PersistentTasks(items) => {
                persistent_tasks_count = Some(items.len());
                persistent_tasks = items;
            }
            MetadataCustomPayload::DecommissionedAttribute(item) => {
                decommission_attribute = Some(item);
            }
            MetadataCustomPayload::IndexGraveyard(items) => {
                index_graveyard_tombstones_count = Some(items.len());
                index_graveyard_tombstones = items;
            }
            MetadataCustomPayload::ComponentTemplate(items) => {
                component_templates_count = Some(items.len());
                component_templates = items;
            }
            MetadataCustomPayload::ComposableIndexTemplate(items) => {
                composable_index_templates_count = Some(items.len());
                composable_index_templates = items;
            }
            MetadataCustomPayload::DataStream(items) => {
                data_streams_count = Some(items.len());
                data_streams = items;
            }
            MetadataCustomPayload::Repositories(items) => {
                repositories_count = Some(items.len());
                repositories = items;
            }
            MetadataCustomPayload::WeightedShardRouting(item) => {
                weighted_routing = Some(item);
            }
            MetadataCustomPayload::View(items) => {
                views_count = Some(items.len());
                views = items;
            }
            MetadataCustomPayload::WorkloadGroups(items) => {
                workload_groups_count = Some(items.len());
                workload_groups = items;
            }
        };
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
    if !stream_version.on_or_after(OPENSEARCH_3_6_0) {
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
    ) = if stream_version.on_or_after(OPENSEARCH_2_10_0) {
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
    if !stream_version.on_or_after(OPENSEARCH_3_6_0) {
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

    let context_present = if stream_version.on_or_after(OPENSEARCH_2_17_0) {
        read_absent_optional_writeable(input, "metadata.index.context")?
    } else {
        false
    };
    let ingestion_paused = if stream_version.on_or_after(OPENSEARCH_3_0_0) {
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
    ) = if stream_version.on_or_after(OPENSEARCH_3_6_0) {
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
    if !stream_version.on_or_after(OPENSEARCH_3_6_0) {
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

    let context_present = if stream_version.on_or_after(OPENSEARCH_2_17_0) {
        read_absent_optional_writeable(input, "metadata.index.diff.context")?
    } else {
        false
    };
    let ingestion_paused = if stream_version.on_or_after(OPENSEARCH_3_0_0) {
        read_optional_ingestion_status_prefix(input)?
    } else {
        None
    };
    let ingestion_status_present = ingestion_paused.is_some();

    let (split_shards_replacement_present, split_shards_replacement) =
        if stream_version.on_or_after(OPENSEARCH_3_6_0) {
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
    let search_only = if stream_version.on_or_after(OPENSEARCH_2_17_0) {
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
        if stream_version.on_or_after(OPENSEARCH_3_7_0) {
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
    let index_shard_path_type = if stream_version.on_or_after(OPENSEARCH_2_17_0) {
        Some(input.read_vint()?)
    } else {
        None
    };
    let is_searchable_snapshot = if stream_version.on_or_after(OPENSEARCH_2_7_0) {
        Some(input.read_bool()?)
    } else {
        None
    };
    let (remote_store_index_shallow_copy, source_remote_store_repository) =
        if stream_version.on_or_after(OPENSEARCH_2_9_0) {
            (Some(input.read_bool()?), input.read_optional_string()?)
        } else {
            (None, None)
        };
    let (source_remote_translog_repository, pinned_timestamp) =
        if stream_version.on_or_after(OPENSEARCH_2_17_0) {
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
    let index_shard_path_type = if stream_version.on_or_after(OPENSEARCH_2_17_0) {
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
    let stream_address = if stream_version.on_or_after(OPENSEARCH_DISCOVERY_NODE_STREAM_ADDRESS) {
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

type ClusterStateCustomReader =
    fn(&mut StreamInput, Version) -> Result<ClusterStateCustomPayload, ClusterStateDecodeError>;

struct ClusterStateCustomRegistryEntry {
    name: &'static str,
    reader: ClusterStateCustomReader,
}

enum ClusterStateCustomPayload {
    RepositoryCleanup(RepositoryCleanupInProgressPrefix),
    SnapshotDeletions(SnapshotDeletionsInProgressPrefix),
    Restore(RestoreInProgressPrefix),
    Snapshots(SnapshotsInProgressPrefix),
}

const CLUSTER_STATE_CUSTOM_REGISTRY: &[ClusterStateCustomRegistryEntry] = &[
    ClusterStateCustomRegistryEntry {
        name: "repository_cleanup",
        reader: read_repository_cleanup_cluster_state_custom_payload,
    },
    ClusterStateCustomRegistryEntry {
        name: "snapshot_deletions",
        reader: read_snapshot_deletions_cluster_state_custom_payload,
    },
    ClusterStateCustomRegistryEntry {
        name: "restore",
        reader: read_restore_cluster_state_custom_payload,
    },
    ClusterStateCustomRegistryEntry {
        name: "snapshots",
        reader: read_snapshots_cluster_state_custom_payload,
    },
];

fn cluster_state_custom_reader(name: &str) -> Option<ClusterStateCustomReader> {
    CLUSTER_STATE_CUSTOM_REGISTRY
        .iter()
        .find_map(|entry| (entry.name == name).then_some(entry.reader))
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

fn read_repository_cleanup_cluster_state_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<ClusterStateCustomPayload, ClusterStateDecodeError> {
    Ok(ClusterStateCustomPayload::RepositoryCleanup(
        read_repository_cleanup_in_progress_prefix(input)?,
    ))
}

fn read_snapshot_deletions_cluster_state_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<ClusterStateCustomPayload, ClusterStateDecodeError> {
    Ok(ClusterStateCustomPayload::SnapshotDeletions(
        read_snapshot_deletions_in_progress_prefix(input)?,
    ))
}

fn read_restore_cluster_state_custom_payload(
    input: &mut StreamInput,
    _stream_version: Version,
) -> Result<ClusterStateCustomPayload, ClusterStateDecodeError> {
    Ok(ClusterStateCustomPayload::Restore(
        read_restore_in_progress_prefix(input)?,
    ))
}

fn read_snapshots_cluster_state_custom_payload(
    input: &mut StreamInput,
    stream_version: Version,
) -> Result<ClusterStateCustomPayload, ClusterStateDecodeError> {
    Ok(ClusterStateCustomPayload::Snapshots(
        read_snapshots_in_progress_prefix(input, stream_version)?,
    ))
}

pub fn read_cluster_state_tail_prefix(
    input: &mut StreamInput,
    stream_version: Version,
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
        let reader = cluster_state_custom_reader(&name).ok_or(
            ClusterStateDecodeError::UnsupportedNamedWriteable {
                section: "cluster_state.customs",
                name,
            },
        )?;
        match reader(input, stream_version)? {
            ClusterStateCustomPayload::RepositoryCleanup(item) => {
                repository_cleanup = Some(item);
            }
            ClusterStateCustomPayload::SnapshotDeletions(item) => {
                snapshot_deletions = Some(item);
            }
            ClusterStateCustomPayload::Restore(item) => {
                restore = Some(item);
            }
            ClusterStateCustomPayload::Snapshots(item) => {
                snapshots = Some(item);
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
    stream_version: Version,
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
        let remote_store_index_shallow_copy = if stream_version.on_or_after(OPENSEARCH_2_9_0) {
            Some(input.read_bool()?)
        } else {
            None
        };
        let remote_store_index_shallow_copy_v2 = if stream_version.on_or_after(OPENSEARCH_2_18_0) {
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
    stream_version: Version,
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
                    Some(read_snapshots_in_progress_prefix(input, stream_version)?)
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
            "snapshots" => {
                snapshots_upserts.push(read_snapshots_in_progress_prefix(input, stream_version)?);
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
    #[error("cluster-state response is missing required section: {0}")]
    MissingSection(&'static str),
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
    #[error("cluster-state diff base uuid mismatch: expected previous state {expected}, diff starts from {actual}")]
    DiffBaseMismatch { expected: String, actual: String },
    #[error("cluster-state diff requires missing base item {key} in section {section}")]
    MissingDiffBase { section: &'static str, key: String },
}

#[cfg(test)]
mod tests {
    use super::{
        read_allocation_id_prefix, read_cluster_blocks_prefix, read_cluster_state_tail_prefix,
        read_generic_map_prefix, read_metadata_prefix, read_publication_cluster_state_diff,
        read_publication_cluster_state_diff_header_prefix,
        read_publication_cluster_state_diff_prefix, read_remote_store_recovery_source_prefix,
        read_routing_table_prefix, read_shard_routing_prefix, read_snapshot_recovery_source_prefix,
        read_snapshots_in_progress_prefix, read_string_map_diff_envelope_prefix,
        read_string_map_prefix, ClusterBlockLevel, ClusterBlockLevelPrefix, ClusterBlockPrefix,
        ClusterBlocks, ClusterBlocksPrefix, ClusterState, ClusterStateCustoms,
        ClusterStateDecodeError, ClusterStateHeader, ClusterStateRequest,
        ClusterStateResponsePrefix, ComponentTemplate, ComponentTemplatePrefix,
        ComposableIndexTemplate, ComposableIndexTemplatePrefix, CoordinationMetadata, DataStream,
        DataStreamBackingIndexPrefix, DataStreamPrefix, DecommissionAttributeMetadata,
        DecommissionAttributeMetadataPrefix, DiscoveryNode, DiscoveryNodePrefix,
        DiscoveryNodeRolePrefix, DiscoveryNodes, IndexClusterBlocksPrefix, IndexGraveyardTombstone,
        IndexGraveyardTombstonePrefix, IndexMetadata, IndexMetadataPrefix, IndexRoutingTablePrefix,
        IndexShardRoutingTablePrefix, IndexTemplateMetadata, IndexTemplateMetadataPrefix,
        IngestPipeline, IngestPipelinePrefix, Metadata, MetadataCustoms, PersistentTask,
        PersistentTaskPrefix, RepositoryCleanupInProgress, RepositoryCleanupInProgressPrefix,
        RepositoryMetadata, RepositoryMetadataPrefix, RestoreInProgress, RestoreInProgressPrefix,
        RoutingTable, RoutingTablePrefix, SearchPipeline, SearchPipelinePrefix, SettingPrefix,
        ShardRoutingPrefix, ShardRoutingState, ShardRoutingStatePrefix,
        SnapshotDeletionsInProgress, SnapshotDeletionsInProgressPrefix, SnapshotsInProgress,
        SnapshotsInProgressPrefix, StoredScript, StoredScriptPrefix, TransportAddressPrefix,
        ViewMetadata, ViewMetadataPrefix, WeightedRoutingMetadata, WeightedRoutingMetadataPrefix,
        WorkloadGroup, WorkloadGroupPrefix, CLUSTER_STATE_ACTION, OPENSEARCH_2_10_0,
        OPENSEARCH_2_17_0, OPENSEARCH_2_18_0, OPENSEARCH_2_7_0, OPENSEARCH_2_9_0, OPENSEARCH_3_6_0,
        OPENSEARCH_3_7_0,
    };
    use bytes::Bytes;
    use os_stream::StreamInput;
    use os_stream::StreamOutput;
    use std::collections::BTreeSet;
    use std::net::{IpAddr, Ipv4Addr};

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

        let bytes = output.freeze();
        let prefix =
            read_publication_cluster_state_diff_prefix(bytes.clone(), OPENSEARCH_3_7_0).unwrap();
        let diff = read_publication_cluster_state_diff(bytes, OPENSEARCH_3_7_0).unwrap();

        assert_eq!(prefix.header.cluster_name, "runTask");
        assert_eq!(prefix.routing_table_version, 11);
        assert_eq!(prefix.routing_indices.delete_count, 0);
        assert!(!prefix.nodes_complete_diff);
        assert_eq!(prefix.metadata_cluster_uuid, "cluster-uuid");
        assert!(prefix.metadata_cluster_uuid_committed);
        assert_eq!(prefix.metadata_version, 13);
        assert_eq!(prefix.metadata_coordination.term, 17);
        assert_eq!(prefix.metadata_transient_settings.len(), 0);
        assert_eq!(prefix.metadata_persistent_settings.len(), 0);
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

        assert_eq!(diff.header.cluster_name, "runTask");
        assert_eq!(diff.routing_table_version, 11);
        assert_eq!(diff.routing_indices.deleted_keys.len(), 0);
        assert_eq!(diff.metadata_coordination.term, 17);
        assert_eq!(diff.metadata_transient_settings.len(), 0);
        assert_eq!(diff.metadata_persistent_settings.len(), 0);
        assert_eq!(diff.metadata_indices.diff_keys.len(), 0);
        assert_eq!(diff.metadata_templates.upsert_keys.len(), 0);
        assert_eq!(diff.metadata_customs.deleted_keys.len(), 0);
        assert_eq!(diff.customs.upsert_keys.len(), 0);
        assert_eq!(
            diff.minimum_cluster_manager_nodes_on_publishing_cluster_manager,
            0
        );

        let previous = ClusterState {
            response_cluster_name: "response-cluster".to_string(),
            header: ClusterStateHeader {
                version: 6,
                state_uuid: "from-state-uuid".to_string(),
                cluster_name: "runTask".to_string(),
            },
            metadata: Metadata {
                version: 12,
                cluster_uuid: "old-cluster-uuid".to_string(),
                cluster_uuid_committed: false,
                coordination: CoordinationMetadata {
                    term: 1,
                    last_committed_configuration: BTreeSet::new(),
                    last_accepted_configuration: BTreeSet::new(),
                    voting_config_exclusions: Vec::new(),
                },
                transient_settings: Vec::new(),
                persistent_settings: Vec::new(),
                hashes_of_consistent_settings: Vec::new(),
                index_metadata: Vec::new(),
                templates: Vec::new(),
                customs: MetadataCustoms {
                    declared_count: 0,
                    ingest_pipelines: Vec::new(),
                    search_pipelines: Vec::new(),
                    stored_scripts: Vec::new(),
                    persistent_tasks: Vec::new(),
                    decommission_attribute: None,
                    index_graveyard_tombstones: Vec::new(),
                    component_templates: Vec::new(),
                    composable_index_templates: Vec::new(),
                    data_streams: Vec::new(),
                    repositories: Vec::new(),
                    weighted_routing: None,
                    views: Vec::new(),
                    workload_groups: Vec::new(),
                },
            },
            routing_table: RoutingTable {
                version: 10,
                indices: Vec::new(),
            },
            discovery_nodes: DiscoveryNodes {
                cluster_manager_node_id: None,
                nodes: Vec::new(),
            },
            cluster_blocks: ClusterBlocks {
                global_blocks: Vec::new(),
                index_blocks: Vec::new(),
            },
            customs: ClusterStateCustoms {
                declared_count: 0,
                names: Vec::new(),
                repository_cleanup: None,
                snapshot_deletions: None,
                restore: None,
                snapshots: None,
                minimum_cluster_manager_nodes_on_publishing_cluster_manager: 0,
            },
            wait_for_timed_out: false,
        };
        let applied = diff.apply_to(&previous).unwrap();

        assert_eq!(applied.header.version, 7);
        assert_eq!(applied.header.state_uuid, "to-state-uuid");
        assert_eq!(applied.routing_table.version, 11);
        assert_eq!(applied.metadata.version, 13);
        assert_eq!(applied.metadata.cluster_uuid, "cluster-uuid");
        assert!(applied.metadata.cluster_uuid_committed);
        assert_eq!(applied.metadata.coordination.term, 17);
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
        let state = response.clone().into_cluster_state().unwrap();
        let header = response.state_header.unwrap();
        let metadata = response.metadata_prefix.unwrap();
        let routing_table = response.routing_table.unwrap();
        let discovery_nodes = response.discovery_nodes.unwrap();
        let cluster_blocks = response.cluster_blocks.unwrap();
        let cluster_state_tail = response.cluster_state_tail.unwrap();

        assert_eq!(response.response_cluster_name, "runTask");
        assert_eq!(state.response_cluster_name, "runTask");
        assert_eq!(state.header.version, 42);
        assert_eq!(state.metadata.version, 9);
        assert_eq!(state.metadata.coordination.term, 3);
        assert_eq!(state.routing_table.version, 11);
        assert!(state.discovery_nodes.nodes.is_empty());
        assert!(state.cluster_blocks.global_blocks.is_empty());
        assert_eq!(state.customs.declared_count, 0);
        assert!(!state.wait_for_timed_out);
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
    fn rejects_typed_cluster_state_when_response_has_no_state() {
        let mut output = StreamOutput::new();
        output.write_string("runTask");
        output.write_bool(false);
        output.write_bool(true);

        let response = ClusterStateResponsePrefix::read(output.freeze()).unwrap();
        let error = response.into_cluster_state().unwrap_err();

        assert!(matches!(
            error,
            ClusterStateDecodeError::MissingSection("cluster_state.header")
        ));
    }

    #[test]
    fn typed_discovery_nodes_and_blocks_are_owned_non_prefix_structs() {
        let prefix_node = DiscoveryNodePrefix {
            name: "node".to_string(),
            id: "node-id".to_string(),
            ephemeral_id: "ephemeral".to_string(),
            host_name: "host".to_string(),
            host_address: "127.0.0.1".to_string(),
            address: TransportAddressPrefix {
                ip: IpAddr::V4(Ipv4Addr::new(127, 0, 0, 1)),
                host: "127.0.0.1".to_string(),
                port: 9300,
            },
            stream_address: None,
            attribute_count: 2,
            roles: vec![DiscoveryNodeRolePrefix {
                name: "data".to_string(),
                abbreviation: "d".to_string(),
                can_contain_data: true,
            }],
            version: OPENSEARCH_3_7_0.id(),
        };

        let node: DiscoveryNode = prefix_node.into();

        assert_eq!(node.id, "node-id");
        assert_eq!(node.address.port, 9300);
        assert_eq!(node.skipped_attribute_count, 2);
        assert_eq!(node.roles[0].name, "data");

        let prefix_blocks = ClusterBlocksPrefix {
            global_block_count: 1,
            global_blocks: vec![ClusterBlockPrefix {
                id: 1,
                uuid: None,
                description: "global".to_string(),
                levels: vec![ClusterBlockLevelPrefix::MetadataWrite],
                retryable: false,
                disable_state_persistence: false,
                status: "OK".to_string(),
                allow_release_resources: false,
            }],
            index_block_count: 1,
            index_blocks: vec![IndexClusterBlocksPrefix {
                index_name: "index".to_string(),
                block_count: 0,
                blocks: Vec::new(),
            }],
        };

        let blocks: ClusterBlocks = prefix_blocks.into();

        assert_eq!(blocks.global_blocks[0].id, 1);
        assert_eq!(
            blocks.global_blocks[0].levels,
            vec![ClusterBlockLevel::MetadataWrite]
        );
        assert_eq!(blocks.index_blocks[0].index_name, "index");
        assert!(blocks.index_blocks[0].blocks.is_empty());
    }

    #[test]
    fn typed_routing_table_is_owned_non_prefix_structs() {
        let prefix = RoutingTablePrefix {
            version: 7,
            index_routing_table_count: 1,
            indices: vec![IndexRoutingTablePrefix {
                index_name: "index".to_string(),
                index_uuid: "uuid".to_string(),
                shard_table_count: 1,
                shards: vec![IndexShardRoutingTablePrefix {
                    shard_id: 0,
                    shard_routing_count: 1,
                    shard_routings: vec![ShardRoutingPrefix {
                        current_node_id: Some("node-a".to_string()),
                        relocating_node_id: None,
                        primary: true,
                        search_only: false,
                        state: ShardRoutingStatePrefix::Started,
                        recovery_source_type: None,
                        recovery_source_bootstrap_new_history_uuid: None,
                        snapshot_recovery_source: None,
                        remote_store_recovery_source: None,
                        unassigned_info: None,
                        allocation_id_present: false,
                        allocation_id: None,
                        expected_shard_size: None,
                    }],
                }],
            }],
        };

        let routing: RoutingTable = prefix.into();

        assert_eq!(routing.version, 7);
        assert_eq!(routing.indices[0].index_name, "index");
        assert_eq!(routing.indices[0].shards[0].shard_id, 0);
        assert_eq!(
            routing.indices[0].shards[0].shard_routings[0].state,
            ShardRoutingState::Started
        );
        assert!(routing.indices[0].shards[0].shard_routings[0].primary);
    }

    #[test]
    fn typed_index_metadata_and_templates_are_owned_non_prefix_structs() {
        let index: IndexMetadata = IndexMetadataPrefix {
            name: "index".to_string(),
            version: 1,
            mapping_version: 2,
            settings_version: 3,
            aliases_version: 4,
            routing_num_shards: 1,
            state_id: 0,
            settings_count: 2,
            index_uuid: Some("uuid".to_string()),
            number_of_shards: Some(1),
            number_of_replicas: Some(0),
            mapping_count: 0,
            mappings: Vec::new(),
            alias_count: 0,
            aliases: Vec::new(),
            custom_data_count: 0,
            custom_data: Vec::new(),
            in_sync_allocation_ids_count: 0,
            rollover_info_count: 0,
            rollover_infos: Vec::new(),
            system: false,
            context_present: false,
            ingestion_status_present: true,
            ingestion_paused: Some(false),
            split_shards_root_count: Some(0),
            split_shards_root_children: Vec::new(),
            split_shards_max_shard_id: Some(0),
            split_shards_in_progress_count: Some(0),
            split_shards_active_count: Some(0),
            split_shards_parent_to_child_count: Some(0),
            split_shards_parent_to_child: Vec::new(),
            primary_terms_count: 1,
        }
        .into();
        let template: IndexTemplateMetadata = IndexTemplateMetadataPrefix {
            name: "template".to_string(),
            order: 10,
            patterns: vec!["logs-*".to_string()],
            settings_count: 1,
            settings: vec![SettingPrefix {
                key: "index.number_of_shards".to_string(),
                value: Some("1".to_string()),
            }],
            mappings_count: 0,
            mappings: Vec::new(),
            aliases_count: 0,
            aliases: Vec::new(),
            version: Some(7),
        }
        .into();

        assert_eq!(index.name, "index");
        assert_eq!(index.index_uuid.as_deref(), Some("uuid"));
        assert_eq!(template.patterns, vec!["logs-*"]);
        assert_eq!(template.settings[0].key, "index.number_of_shards");
        assert_eq!(template.version, Some(7));
        assert_eq!(index.prefix_only_summary().section, "metadata.index");
        assert!(index
            .prefix_only_summary()
            .fields
            .contains(&"mappings".to_string()));
        assert_eq!(
            template.prefix_only_summary().fields,
            vec!["mappings".to_string(), "aliases".to_string()]
        );
    }

    #[test]
    fn typed_simple_metadata_customs_are_owned_non_prefix_structs() {
        let ingest: IngestPipeline = IngestPipelinePrefix {
            id: "ingest".to_string(),
            config_len: 10,
            media_type: "application/json".to_string(),
        }
        .into();
        let search: SearchPipeline = SearchPipelinePrefix {
            id: "search".to_string(),
            config_len: 11,
            media_type: "application/json".to_string(),
        }
        .into();
        let script: StoredScript = StoredScriptPrefix {
            id: "script".to_string(),
            lang: "painless".to_string(),
            source_len: 12,
            options_count: 1,
        }
        .into();
        let decommission: DecommissionAttributeMetadata = DecommissionAttributeMetadataPrefix {
            attribute_name: "zone".to_string(),
            attribute_value: "a".to_string(),
            status: "successful".to_string(),
            request_id: "request".to_string(),
        }
        .into();

        assert_eq!(ingest.id, "ingest");
        assert_eq!(search.config_len, 11);
        assert_eq!(script.lang, "painless");
        assert_eq!(decommission.attribute_name, "zone");
    }

    #[test]
    fn typed_task_graveyard_and_repository_metadata_are_owned_non_prefix_structs() {
        let task: PersistentTask = PersistentTaskPrefix {
            map_key: "task-key".to_string(),
            id: "task-id".to_string(),
            allocation_id: 1,
            task_name: "task-name".to_string(),
            params_name: "params".to_string(),
            fixture_params_marker: Some("params-marker".to_string()),
            fixture_params_generation: Some(2),
            state_name: Some("state".to_string()),
            fixture_state_marker: Some("state-marker".to_string()),
            fixture_state_generation: Some(3),
            executor_node: Some("node".to_string()),
            assignment_explanation: "assigned".to_string(),
            allocation_id_on_last_status_update: Some(4),
        }
        .into();
        let tombstone: IndexGraveyardTombstone = IndexGraveyardTombstonePrefix {
            index_name: "deleted-index".to_string(),
            index_uuid: "deleted-uuid".to_string(),
            delete_date_in_millis: 5,
        }
        .into();
        let repository: RepositoryMetadata = RepositoryMetadataPrefix {
            name: "repo".to_string(),
            repository_type: "fs".to_string(),
            settings_count: 1,
            settings: vec![SettingPrefix {
                key: "location".to_string(),
                value: Some("/tmp/repo".to_string()),
            }],
            generation: 6,
            pending_generation: 7,
            crypto_metadata_present: true,
            crypto_key_provider_name: Some("provider".to_string()),
            crypto_key_provider_type: Some("type".to_string()),
            crypto_settings_count: 1,
            crypto_settings: vec![SettingPrefix {
                key: "cipher".to_string(),
                value: Some("aes".to_string()),
            }],
        }
        .into();

        assert_eq!(task.id, "task-id");
        assert_eq!(tombstone.index_name, "deleted-index");
        assert_eq!(repository.settings[0].key, "location");
        assert_eq!(repository.crypto_settings[0].value.as_deref(), Some("aes"));
    }

    #[test]
    fn typed_template_and_data_stream_customs_are_owned_non_prefix_structs() {
        let component: ComponentTemplate = ComponentTemplatePrefix {
            name: "component".to_string(),
            settings_count: 1,
            settings: vec![SettingPrefix {
                key: "index.number_of_replicas".to_string(),
                value: Some("0".to_string()),
            }],
            mappings_present: false,
            mapping: None,
            aliases_count: 0,
            aliases: Vec::new(),
            version: Some(1),
            metadata_present: true,
            metadata_count: 1,
            metadata: vec![SettingPrefix {
                key: "owner".to_string(),
                value: Some("search".to_string()),
            }],
        }
        .into();
        let composable: ComposableIndexTemplate = ComposableIndexTemplatePrefix {
            name: "composable".to_string(),
            index_patterns: vec!["logs-*".to_string()],
            template_present: true,
            template_settings_count: 1,
            template_settings: vec![SettingPrefix {
                key: "index.number_of_shards".to_string(),
                value: Some("1".to_string()),
            }],
            template_mappings_present: false,
            template_mapping: None,
            template_aliases_count: 0,
            template_aliases: Vec::new(),
            component_templates_count: 1,
            component_templates: vec!["component".to_string()],
            priority: Some(100),
            version: Some(2),
            metadata_count: 1,
            metadata: vec![SettingPrefix {
                key: "team".to_string(),
                value: Some("search".to_string()),
            }],
            data_stream_template_present: true,
            data_stream_timestamp_field: Some("@timestamp".to_string()),
            context_present: true,
            context_name: Some("context".to_string()),
            context_version: Some("1".to_string()),
            context_params_count: 1,
            context_params: vec![SettingPrefix {
                key: "region".to_string(),
                value: Some("us".to_string()),
            }],
        }
        .into();
        let data_stream: DataStream = DataStreamPrefix {
            name: "logs".to_string(),
            timestamp_field: "@timestamp".to_string(),
            backing_indices_count: 1,
            backing_indices: vec![DataStreamBackingIndexPrefix {
                name: ".ds-logs-000001".to_string(),
                uuid: "uuid".to_string(),
            }],
            generation: 1,
        }
        .into();

        assert_eq!(component.settings[0].key, "index.number_of_replicas");
        assert_eq!(component.metadata[0].value.as_deref(), Some("search"));
        assert_eq!(composable.template_settings[0].value.as_deref(), Some("1"));
        assert_eq!(composable.context_params[0].key, "region");
        assert_eq!(data_stream.backing_indices[0].name, ".ds-logs-000001");
        assert_eq!(
            component.prefix_only_summary().fields,
            vec!["mapping".to_string(), "aliases".to_string()]
        );
        assert_eq!(
            composable.prefix_only_summary().section,
            "metadata.customs.index_template"
        );
    }

    #[test]
    fn typed_cluster_customs_are_owned_non_prefix_structs() {
        let cleanup: RepositoryCleanupInProgress = RepositoryCleanupInProgressPrefix {
            entry_count: 0,
            entries: Vec::new(),
        }
        .into();
        let deletions: SnapshotDeletionsInProgress = SnapshotDeletionsInProgressPrefix {
            entry_count: 0,
            entries: Vec::new(),
        }
        .into();
        let restore: RestoreInProgress = RestoreInProgressPrefix {
            entry_count: 0,
            entries: Vec::new(),
        }
        .into();
        let snapshots: SnapshotsInProgress = SnapshotsInProgressPrefix {
            entry_count: 0,
            entries: Vec::new(),
        }
        .into();

        assert!(cleanup.entries.is_empty());
        assert!(deletions.entries.is_empty());
        assert!(restore.entries.is_empty());
        assert!(snapshots.entries.is_empty());
        let customs = super::ClusterStateCustoms {
            declared_count: 4,
            names: vec![
                "repository_cleanup".to_string(),
                "snapshot_deletions".to_string(),
                "restore".to_string(),
                "snapshots".to_string(),
            ],
            repository_cleanup: Some(cleanup),
            snapshot_deletions: Some(deletions),
            restore: Some(restore),
            snapshots: Some(snapshots),
            minimum_cluster_manager_nodes_on_publishing_cluster_manager: 0,
        };
        assert_eq!(
            customs.prefix_only_summary().section,
            "cluster_state.customs"
        );
        assert_eq!(customs.prefix_only_summary().declared_items, 0);
    }

    #[test]
    fn typed_view_weighted_routing_and_workload_group_are_owned_non_prefix_structs() {
        let weighted: WeightedRoutingMetadata = WeightedRoutingMetadataPrefix {
            awareness_attribute: "zone".to_string(),
            weights_count: 1,
            weights: vec![SettingPrefix {
                key: "zone-a".to_string(),
                value: Some("1.0".to_string()),
            }],
            version: 3,
        }
        .into();
        let view: ViewMetadata = ViewMetadataPrefix {
            name: "view".to_string(),
            description: Some("desc".to_string()),
            created_at: 1,
            modified_at: 2,
            target_index_patterns_count: 1,
            target_index_patterns: vec!["logs-*".to_string()],
        }
        .into();
        let group: WorkloadGroup = WorkloadGroupPrefix {
            name: "group".to_string(),
            id: "group-id".to_string(),
            resource_limits_count: 1,
            resource_limits: vec![SettingPrefix {
                key: "cpu".to_string(),
                value: Some("0.5".to_string()),
            }],
            resiliency_mode: Some("monitor".to_string()),
            search_settings_count: 1,
            search_settings: vec![SettingPrefix {
                key: "reject".to_string(),
                value: Some("false".to_string()),
            }],
            updated_at_millis: 9,
        }
        .into();

        assert_eq!(weighted.awareness_attribute, "zone");
        assert_eq!(weighted.weights[0].key, "zone-a");
        assert_eq!(view.target_index_patterns, vec!["logs-*"]);
        assert_eq!(group.resource_limits[0].key, "cpu");
        assert_eq!(group.search_settings[0].value.as_deref(), Some("false"));
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
        let routing = read_routing_table_prefix(&mut input, OPENSEARCH_3_7_0).unwrap();
        let shard = &routing.indices[0].shards[0].shard_routings[0];

        assert_eq!(shard.current_node_id, None);
        assert!(shard.primary);
        assert_eq!(shard.state, ShardRoutingStatePrefix::Started);
        assert_eq!(shard.allocation_id.as_ref().unwrap().id, "allocation-1");
    }

    #[test]
    fn snapshot_recovery_source_keeps_version_gated_field_alignment() {
        let mut output = StreamOutput::new();
        write_snapshot_recovery_source_common(&mut output);
        output.write_bool(true);

        let mut input = StreamInput::new(output.freeze());
        let source = read_snapshot_recovery_source_prefix(&mut input, OPENSEARCH_2_7_0).unwrap();

        assert_eq!(source.index_shard_path_type, None);
        assert_eq!(source.is_searchable_snapshot, Some(true));
        assert_eq!(source.remote_store_index_shallow_copy, None);
        assert_eq!(input.remaining(), 0);

        let mut output = StreamOutput::new();
        write_snapshot_recovery_source_common(&mut output);
        output.write_bool(false);
        output.write_bool(true);
        output.write_optional_string(Some("remote-store-repo"));

        let mut input = StreamInput::new(output.freeze());
        let source = read_snapshot_recovery_source_prefix(&mut input, OPENSEARCH_2_9_0).unwrap();

        assert_eq!(source.index_shard_path_type, None);
        assert_eq!(source.is_searchable_snapshot, Some(false));
        assert_eq!(source.remote_store_index_shallow_copy, Some(true));
        assert_eq!(
            source.source_remote_store_repository.as_deref(),
            Some("remote-store-repo")
        );
        assert_eq!(input.remaining(), 0);

        let mut output = StreamOutput::new();
        write_snapshot_recovery_source_common(&mut output);
        output.write_vint(2);
        output.write_bool(true);
        output.write_bool(false);
        output.write_optional_string(None);
        output.write_optional_string(Some("remote-translog-repo"));
        output.write_i64(1234);

        let mut input = StreamInput::new(output.freeze());
        let source = read_snapshot_recovery_source_prefix(&mut input, OPENSEARCH_2_17_0).unwrap();

        assert_eq!(source.index_shard_path_type, Some(2));
        assert_eq!(source.is_searchable_snapshot, Some(true));
        assert_eq!(source.remote_store_index_shallow_copy, Some(false));
        assert_eq!(
            source.source_remote_translog_repository.as_deref(),
            Some("remote-translog-repo")
        );
        assert_eq!(source.pinned_timestamp, Some(1234));
        assert_eq!(input.remaining(), 0);
    }

    #[test]
    fn remote_store_recovery_source_path_type_is_2_17_gated() {
        let mut output = StreamOutput::new();
        write_remote_store_recovery_source_common(&mut output);

        let mut input = StreamInput::new(output.freeze());
        let source =
            read_remote_store_recovery_source_prefix(&mut input, OPENSEARCH_2_10_0).unwrap();

        assert_eq!(source.index_shard_path_type, None);
        assert_eq!(input.remaining(), 0);

        let mut output = StreamOutput::new();
        write_remote_store_recovery_source_common(&mut output);
        output.write_vint(1);

        let mut input = StreamInput::new(output.freeze());
        let source =
            read_remote_store_recovery_source_prefix(&mut input, OPENSEARCH_2_17_0).unwrap();

        assert_eq!(source.index_shard_path_type, Some(1));
        assert_eq!(input.remaining(), 0);
    }

    #[test]
    fn shard_routing_search_only_is_2_17_gated() {
        let mut output = StreamOutput::new();
        write_started_shard_routing_prefix_common(&mut output);

        let mut input = StreamInput::new(output.freeze());
        let shard = read_shard_routing_prefix(&mut input, OPENSEARCH_2_10_0).unwrap();

        assert!(!shard.search_only);
        assert_eq!(shard.state, ShardRoutingStatePrefix::Started);
        assert_eq!(input.remaining(), 0);

        let mut output = StreamOutput::new();
        output.write_optional_string(None);
        output.write_optional_string(None);
        output.write_bool(true);
        output.write_bool(true);
        output.write_byte(3);
        output.write_bool(false);
        output.write_bool(false);

        let mut input = StreamInput::new(output.freeze());
        let shard = read_shard_routing_prefix(&mut input, OPENSEARCH_2_17_0).unwrap();

        assert!(shard.search_only);
        assert_eq!(shard.state, ShardRoutingStatePrefix::Started);
        assert_eq!(input.remaining(), 0);
    }

    #[test]
    fn allocation_id_split_fields_are_3_7_gated() {
        let mut output = StreamOutput::new();
        output.write_string("allocation");
        output.write_optional_string(None);

        let mut input = StreamInput::new(output.freeze());
        let allocation = read_allocation_id_prefix(&mut input, OPENSEARCH_3_6_0).unwrap();

        assert_eq!(allocation.split_child_allocation_ids_count, None);
        assert_eq!(allocation.parent_allocation_id, None);
        assert_eq!(input.remaining(), 0);

        let mut output = StreamOutput::new();
        output.write_string("allocation");
        output.write_optional_string(Some("relocation"));
        output.write_bool(true);
        output.write_vint(2);
        output.write_string("split-child-a");
        output.write_string("split-child-b");
        output.write_optional_string(Some("parent-allocation"));

        let mut input = StreamInput::new(output.freeze());
        let allocation = read_allocation_id_prefix(&mut input, OPENSEARCH_3_7_0).unwrap();

        assert_eq!(allocation.relocation_id.as_deref(), Some("relocation"));
        assert_eq!(allocation.split_child_allocation_ids_count, Some(2));
        assert_eq!(
            allocation.parent_allocation_id.as_deref(),
            Some("parent-allocation")
        );
        assert_eq!(input.remaining(), 0);
    }

    #[test]
    fn snapshots_in_progress_remote_store_flags_use_caller_stream_version() {
        let mut output = StreamOutput::new();
        write_snapshots_in_progress_single_entry_common(&mut output);

        let mut input = StreamInput::new(output.freeze());
        let snapshots = read_snapshots_in_progress_prefix(&mut input, OPENSEARCH_2_7_0).unwrap();
        let entry = &snapshots.entries[0];

        assert_eq!(entry.remote_store_index_shallow_copy, None);
        assert_eq!(entry.remote_store_index_shallow_copy_v2, None);
        assert_eq!(input.remaining(), 0);

        let mut output = StreamOutput::new();
        write_snapshots_in_progress_single_entry_common(&mut output);
        output.write_bool(true);

        let mut input = StreamInput::new(output.freeze());
        let snapshots = read_snapshots_in_progress_prefix(&mut input, OPENSEARCH_2_9_0).unwrap();
        let entry = &snapshots.entries[0];

        assert_eq!(entry.remote_store_index_shallow_copy, Some(true));
        assert_eq!(entry.remote_store_index_shallow_copy_v2, None);
        assert_eq!(input.remaining(), 0);

        let mut output = StreamOutput::new();
        write_snapshots_in_progress_single_entry_common(&mut output);
        output.write_bool(true);
        output.write_bool(false);

        let mut input = StreamInput::new(output.freeze());
        let snapshots = read_snapshots_in_progress_prefix(&mut input, OPENSEARCH_2_18_0).unwrap();
        let entry = &snapshots.entries[0];

        assert_eq!(entry.remote_store_index_shallow_copy, Some(true));
        assert_eq!(entry.remote_store_index_shallow_copy_v2, Some(false));
        assert_eq!(input.remaining(), 0);
    }

    fn write_snapshot_recovery_source_common(output: &mut StreamOutput) {
        output.write_string("restore-uuid");
        output.write_string("repo");
        output.write_string("snapshot");
        output.write_string("snapshot-uuid");
        output.write_vint(1);
        output.write_string("index");
        output.write_string("index-uuid");
    }

    fn write_remote_store_recovery_source_common(output: &mut StreamOutput) {
        output.write_string("restore-uuid");
        output.write_vint(1);
        output.write_string("index");
        output.write_string("index-uuid");
    }

    fn write_started_shard_routing_prefix_common(output: &mut StreamOutput) {
        output.write_optional_string(None);
        output.write_optional_string(None);
        output.write_bool(true);
        output.write_byte(3);
        output.write_bool(false);
        output.write_bool(false);
    }

    fn write_snapshots_in_progress_single_entry_common(output: &mut StreamOutput) {
        output.write_vint(1);
        output.write_string("repo");
        output.write_string("snapshot");
        output.write_string("snapshot-uuid");
        output.write_bool(true);
        output.write_bool(false);
        output.write_byte(1);
        output.write_vint(0);
        output.write_i64(10);
        output.write_vint(0);
        output.write_i64(20);
        output.write_optional_string(None);
        output.write_byte(0xff);
        output.write_vint(1);
        output.write_vint(0);
        output.write_bool(false);
        output.write_vint(0);
    }

    #[test]
    fn rejects_unknown_cluster_state_customs() {
        let mut output = StreamOutput::new();
        output.write_vint(1);
        output.write_string("unknown_custom");

        let mut input = StreamInput::new(output.freeze());
        let error = read_cluster_state_tail_prefix(&mut input, OPENSEARCH_3_7_0).unwrap_err();

        assert!(matches!(
            error,
            ClusterStateDecodeError::UnsupportedNamedWriteable {
                section: "cluster_state.customs",
                name
            } if name == "unknown_custom"
        ));
    }

    #[test]
    fn rejects_unknown_metadata_customs() {
        let mut output = StreamOutput::new();
        output.write_i64(1);
        output.write_string("cluster-uuid");
        output.write_bool(true);
        output.write_i64(1);
        output.write_string_array(&[]);
        output.write_string_array(&[]);
        output.write_vint(0);
        output.write_vint(0);
        output.write_vint(0);
        output.write_byte(0xff);
        output.write_vint(0);
        output.write_vint(0);
        output.write_vint(1);
        output.write_string("unknown_metadata_custom");

        let mut input = StreamInput::new(output.freeze());
        let error = read_metadata_prefix(&mut input, OPENSEARCH_3_7_0).unwrap_err();

        assert!(matches!(
            error,
            ClusterStateDecodeError::UnsupportedNamedWriteable {
                section: "metadata.custom",
                name
            } if name == "unknown_metadata_custom"
        ));
    }

    #[test]
    fn decodes_java_signed_vint_tail_value() {
        let mut input = StreamInput::new(Bytes::from_static(&[0xff, 0xff, 0xff, 0xff, 0x0f]));

        assert_eq!(input.read_vint().unwrap(), -1);
        assert_eq!(input.remaining(), 0);
    }
}
