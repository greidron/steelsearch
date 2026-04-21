use anyhow::{anyhow, bail, Context, Result};
use bytes::{BufMut, BytesMut};
use os_cluster_state::{
    build_cluster_state_request_frame, ClusterBlockLevelPrefix, ClusterBlockPrefix,
    ClusterStateRequest, ClusterStateResponsePrefix,
};
use os_core::Version;
use os_stream::StreamInput;
use os_transport::error::TransportError;
use os_transport::frame::{decode_frame, DecodedFrame};
use os_transport::handshake::{
    build_tcp_handshake_request, build_transport_handshake_request, TransportHandshakeResponse,
};
use os_transport::variable_header::ResponseVariableHeader;
use os_transport::TransportMessage;
use os_wire::TcpHeader;
use std::env;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream, ToSocketAddrs};
use std::time::Duration;

const DEFAULT_ADDR: &str = "127.0.0.1:9300";

// Derived from the Java OpenSearch 3.7.0-SNAPSHOT wire fixture in this repo.
// The header version is CURRENT.minimumCompatibilityVersion(), while payload
// version is CURRENT.
const DEFAULT_HEADER_VERSION_ID: i32 = 136_407_827;
const DEFAULT_PAYLOAD_VERSION_ID: i32 = 137_287_827;

#[derive(Clone, Debug)]
struct ProbeConfig {
    addr: String,
    request_id: i64,
    header_version: Version,
    payload_version: Version,
    timeout: Duration,
    cluster_state: bool,
    cluster_state_full: bool,
}

fn main() -> Result<()> {
    let config = parse_args(env::args().skip(1))?;
    let peer = resolve_addr(&config.addr)?;
    let mut stream = TcpStream::connect_timeout(&peer, config.timeout)
        .with_context(|| format!("failed to connect to {peer}"))?;
    stream
        .set_read_timeout(Some(config.timeout))
        .context("failed to set read timeout")?;
    stream
        .set_write_timeout(Some(config.timeout))
        .context("failed to set write timeout")?;

    let request = build_tcp_handshake_request(
        config.request_id,
        config.header_version,
        config.payload_version,
    );
    stream
        .write_all(&request)
        .context("failed to write tcp handshake request")?;

    let message = read_expected_message(&mut stream, config.request_id, true)?;

    let tcp_response_header_version = message.version;
    let response_header = ResponseVariableHeader::read(message.variable_header.freeze())
        .context("failed to decode response variable header")?;
    if !response_header.thread_headers.request.is_empty()
        || !response_header.thread_headers.response.is_empty()
    {
        println!("response headers: {:?}", response_header.thread_headers);
    }

    let mut body = StreamInput::new(message.body.freeze());
    let remote_version = body
        .read_vint()
        .context("failed to decode tcp handshake response version")?;
    if body.remaining() != 0 {
        bail!(
            "tcp handshake response body has {} trailing bytes",
            body.remaining()
        );
    }

    let transport_request_id = config.request_id + 1;
    let transport_request =
        build_transport_handshake_request(transport_request_id, Version::from_id(remote_version));
    stream
        .write_all(&transport_request)
        .context("failed to write transport handshake request")?;
    let message = read_expected_message(&mut stream, transport_request_id, false)?;
    let transport_response_header = ResponseVariableHeader::read(message.variable_header.freeze())
        .context("failed to decode transport response variable header")?;
    if !transport_response_header.thread_headers.request.is_empty()
        || !transport_response_header.thread_headers.response.is_empty()
    {
        println!(
            "transport response headers: {:?}",
            transport_response_header.thread_headers
        );
    }

    let transport_handshake =
        TransportHandshakeResponse::read(message.body.freeze(), Version::from_id(remote_version))
            .context("failed to decode transport handshake response")?;

    println!("connected={peer}");
    println!("remote_version_id={remote_version}");
    println!(
        "response_header_version_id={}",
        tcp_response_header_version.id()
    );
    println!("cluster_name={}", transport_handshake.cluster_name);
    println!("transport_version_id={}", transport_handshake.version.id());
    if let Some(node) = transport_handshake.discovery_node {
        println!("node_name={}", node.name);
        println!("node_id={}", node.id);
        println!("node_address={}:{}", node.address.host, node.address.port);
        println!(
            "node_roles={}",
            node.roles
                .iter()
                .map(|role| role.name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
    }

    if config.cluster_state {
        let cluster_state_request_id = config.request_id + 2;
        let cluster_state_request = if config.cluster_state_full {
            ClusterStateRequest::default()
        } else {
            ClusterStateRequest::minimal_probe()
        };
        let request = build_cluster_state_request_frame(
            cluster_state_request_id,
            Version::from_id(remote_version),
            &cluster_state_request,
        );
        stream
            .write_all(&request)
            .context("failed to write cluster-state request")?;
        let message = read_expected_message(&mut stream, cluster_state_request_id, false)?;
        let cluster_state = ClusterStateResponsePrefix::read(message.body.freeze())
            .context("failed to decode cluster-state response prefix")?;
        print!("{}", format_cluster_state_prefix(&cluster_state));
    }
    Ok(())
}

fn format_cluster_state_prefix(response: &ClusterStateResponsePrefix) -> String {
    use std::fmt::Write as _;

    let mut output = String::new();
    macro_rules! line {
        ($($arg:tt)*) => {
            writeln!(output, $($arg)*).expect("writing to String cannot fail")
        };
    }
    line!(
        "cluster_state_response_cluster_name={}",
        response.response_cluster_name
    );
    line!(
        "cluster_state_wait_for_timed_out={}",
        response.wait_for_timed_out.unwrap_or(false)
    );
    if let Some(header) = &response.state_header {
        line!("cluster_state_name={}", header.cluster_name);
        line!("cluster_state_version={}", header.version);
        line!("cluster_state_uuid={}", header.state_uuid);
    }
    if let Some(metadata) = &response.metadata_prefix {
        line!("cluster_state_metadata_version={}", metadata.version);
        line!("cluster_state_cluster_uuid={}", metadata.cluster_uuid);
        line!(
            "cluster_state_metadata_custom_count={}",
            metadata.custom_metadata_count
        );
        line!(
            "cluster_state_metadata_indices={}",
            metadata.index_metadata_count
        );
        line!(
            "cluster_state_metadata_index_names={}",
            metadata
                .index_metadata
                .iter()
                .map(|index| index.name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_index_uuids={}",
            metadata
                .index_metadata
                .iter()
                .filter_map(|index| index.index_uuid.as_deref())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_index_routing_shard_counts={}",
            metadata
                .index_metadata
                .iter()
                .map(|index| index.routing_num_shards.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_index_primary_shard_counts={}",
            metadata
                .index_metadata
                .iter()
                .filter_map(|index| index.number_of_shards)
                .map(|shards| shards.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_index_replica_counts={}",
            metadata
                .index_metadata
                .iter()
                .filter_map(|index| index.number_of_replicas)
                .map(|replicas| replicas.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_index_setting_counts={}",
            metadata
                .index_metadata
                .iter()
                .map(|index| index.settings_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_index_mapping_counts={}",
            metadata
                .index_metadata
                .iter()
                .map(|index| index.mapping_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_index_alias_counts={}",
            metadata
                .index_metadata
                .iter()
                .map(|index| index.alias_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_legacy_templates={}",
            metadata.templates_count
        );
        line!(
            "cluster_state_metadata_legacy_template_names={}",
            metadata
                .templates
                .iter()
                .map(|template| template.name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_legacy_template_patterns={}",
            metadata
                .templates
                .iter()
                .flat_map(|template| template.patterns.iter())
                .map(|pattern| pattern.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_legacy_template_setting_counts={}",
            metadata
                .templates
                .iter()
                .map(|template| template.settings_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_legacy_template_mapping_counts={}",
            metadata
                .templates
                .iter()
                .map(|template| template.mappings_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_legacy_template_alias_counts={}",
            metadata
                .templates
                .iter()
                .map(|template| template.aliases_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_index_graveyard_tombstones={}",
            metadata.index_graveyard_tombstones_count.unwrap_or(0)
        );
        line!(
            "cluster_state_metadata_index_graveyard_tombstone_names={}",
            metadata
                .index_graveyard_tombstones
                .iter()
                .map(|tombstone| tombstone.index_name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_index_graveyard_tombstone_uuids={}",
            metadata
                .index_graveyard_tombstones
                .iter()
                .map(|tombstone| tombstone.index_uuid.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_index_graveyard_tombstone_delete_timestamps={}",
            metadata
                .index_graveyard_tombstones
                .iter()
                .map(|tombstone| tombstone.delete_date_in_millis.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_ingest_pipelines={}",
            metadata.ingest_pipelines_count.unwrap_or(0)
        );
        line!(
            "cluster_state_metadata_ingest_pipeline_ids={}",
            metadata
                .ingest_pipelines
                .iter()
                .map(|pipeline| pipeline.id.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_search_pipelines={}",
            metadata.search_pipelines_count.unwrap_or(0)
        );
        line!(
            "cluster_state_metadata_search_pipeline_ids={}",
            metadata
                .search_pipelines
                .iter()
                .map(|pipeline| pipeline.id.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_stored_scripts={}",
            metadata.stored_scripts_count.unwrap_or(0)
        );
        line!(
            "cluster_state_metadata_stored_script_ids={}",
            metadata
                .stored_scripts
                .iter()
                .map(|script| script.id.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_stored_script_langs={}",
            metadata
                .stored_scripts
                .iter()
                .map(|script| script.lang.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_persistent_tasks={}",
            metadata.persistent_tasks_count.unwrap_or(0)
        );
        line!(
            "cluster_state_metadata_persistent_task_names={}",
            metadata
                .persistent_tasks
                .iter()
                .map(|task| task.task_name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_persistent_task_param_names={}",
            metadata
                .persistent_tasks
                .iter()
                .map(|task| task.params_name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_persistent_task_fixture_markers={}",
            metadata
                .persistent_tasks
                .iter()
                .filter_map(|task| task.fixture_params_marker.as_deref())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_persistent_task_fixture_generations={}",
            metadata
                .persistent_tasks
                .iter()
                .filter_map(|task| task.fixture_params_generation)
                .map(|generation| generation.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_persistent_task_state_names={}",
            metadata
                .persistent_tasks
                .iter()
                .filter_map(|task| task.state_name.as_deref())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_persistent_task_fixture_state_markers={}",
            metadata
                .persistent_tasks
                .iter()
                .filter_map(|task| task.fixture_state_marker.as_deref())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_persistent_task_fixture_state_generations={}",
            metadata
                .persistent_tasks
                .iter()
                .filter_map(|task| task.fixture_state_generation)
                .map(|generation| generation.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_decommissioned_attribute={}",
            usize::from(metadata.decommission_attribute.is_some())
        );
        line!(
            "cluster_state_metadata_component_templates={}",
            metadata.component_templates_count.unwrap_or(0)
        );
        line!(
            "cluster_state_metadata_component_template_names={}",
            metadata
                .component_templates
                .iter()
                .map(|template| template.name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_component_template_versions={}",
            metadata
                .component_templates
                .iter()
                .filter_map(|template| template.version)
                .map(|version| version.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_component_template_setting_counts={}",
            metadata
                .component_templates
                .iter()
                .map(|template| template.settings_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_component_template_mapping_counts={}",
            metadata
                .component_templates
                .iter()
                .map(|template| usize::from(template.mappings_present).to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_component_template_alias_counts={}",
            metadata
                .component_templates
                .iter()
                .map(|template| template.aliases_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_composable_templates={}",
            metadata.composable_index_templates_count.unwrap_or(0)
        );
        line!(
            "cluster_state_metadata_composable_template_names={}",
            metadata
                .composable_index_templates
                .iter()
                .map(|template| template.name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_composable_template_index_patterns={}",
            metadata
                .composable_index_templates
                .iter()
                .flat_map(|template| template.index_patterns.iter())
                .map(|pattern| pattern.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_composable_template_components={}",
            metadata
                .composable_index_templates
                .iter()
                .flat_map(|template| template.component_templates.iter())
                .map(|component| component.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_composable_template_setting_counts={}",
            metadata
                .composable_index_templates
                .iter()
                .map(|template| template.template_settings_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_composable_template_mapping_counts={}",
            metadata
                .composable_index_templates
                .iter()
                .map(|template| usize::from(template.template_mappings_present).to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_composable_template_alias_counts={}",
            metadata
                .composable_index_templates
                .iter()
                .map(|template| template.template_aliases_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_data_streams={}",
            metadata.data_streams_count.unwrap_or(0)
        );
        line!(
            "cluster_state_metadata_data_stream_names={}",
            metadata
                .data_streams
                .iter()
                .map(|stream| stream.name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_data_stream_timestamp_fields={}",
            metadata
                .data_streams
                .iter()
                .map(|stream| stream.timestamp_field.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_data_stream_backing_index_counts={}",
            metadata
                .data_streams
                .iter()
                .map(|stream| stream.backing_indices_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_data_stream_backing_index_names={}",
            metadata
                .data_streams
                .iter()
                .flat_map(|stream| stream.backing_indices.iter())
                .map(|index| index.name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_data_stream_generations={}",
            metadata
                .data_streams
                .iter()
                .map(|stream| stream.generation.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_repositories={}",
            metadata.repositories_count.unwrap_or(0)
        );
        line!(
            "cluster_state_metadata_repository_names={}",
            metadata
                .repositories
                .iter()
                .map(|repository| repository.name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_repository_types={}",
            metadata
                .repositories
                .iter()
                .map(|repository| repository.repository_type.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_repository_setting_counts={}",
            metadata
                .repositories
                .iter()
                .map(|repository| repository.settings_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_repository_generations={}",
            metadata
                .repositories
                .iter()
                .map(|repository| repository.generation.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_repository_pending_generations={}",
            metadata
                .repositories
                .iter()
                .map(|repository| repository.pending_generation.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_repository_crypto_provider_names={}",
            metadata
                .repositories
                .iter()
                .filter_map(|repository| repository.crypto_key_provider_name.as_deref())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_repository_crypto_provider_types={}",
            metadata
                .repositories
                .iter()
                .filter_map(|repository| repository.crypto_key_provider_type.as_deref())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_views={}",
            metadata.views_count.unwrap_or(0)
        );
        line!(
            "cluster_state_metadata_view_names={}",
            metadata
                .views
                .iter()
                .map(|view| view.name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_view_target_patterns={}",
            metadata
                .views
                .iter()
                .flat_map(|view| view.target_index_patterns.iter())
                .map(|pattern| pattern.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_workload_groups={}",
            metadata.workload_groups_count.unwrap_or(0)
        );
        line!(
            "cluster_state_metadata_workload_group_names={}",
            metadata
                .workload_groups
                .iter()
                .map(|group| group.name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_workload_group_ids={}",
            metadata
                .workload_groups
                .iter()
                .map(|group| group.id.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_workload_group_resource_limit_counts={}",
            metadata
                .workload_groups
                .iter()
                .map(|group| group.resource_limits_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_workload_group_search_setting_counts={}",
            metadata
                .workload_groups
                .iter()
                .map(|group| group.search_settings_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_workload_group_resiliency_modes={}",
            metadata
                .workload_groups
                .iter()
                .filter_map(|group| group.resiliency_mode.as_deref())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_metadata_weighted_routing={}",
            usize::from(metadata.weighted_routing.is_some())
        );
        let decoded_customs = decoded_metadata_custom_names(metadata);
        line!(
            "cluster_state_metadata_decoded_custom_count={}",
            decoded_customs.len()
        );
        line!(
            "cluster_state_metadata_decoded_customs={}",
            decoded_customs.join(",")
        );
    }
    if let Some(routing_table) = &response.routing_table {
        line!(
            "cluster_state_routing_indices={}",
            routing_table.index_routing_table_count
        );
        line!(
            "cluster_state_routing_index_names={}",
            routing_table
                .indices
                .iter()
                .map(|index| index.index_name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_routing_shard_tables={}",
            routing_table
                .indices
                .iter()
                .map(|index| index.shard_table_count)
                .sum::<usize>()
        );
        line!(
            "cluster_state_routing_shards={}",
            routing_table
                .indices
                .iter()
                .flat_map(|index| index.shards.iter())
                .map(|shard| shard.shard_routing_count)
                .sum::<usize>()
        );
        line!(
            "cluster_state_routing_shard_ids={}",
            routing_table
                .indices
                .iter()
                .flat_map(|index| index.shards.iter())
                .flat_map(|shard| {
                    std::iter::repeat(shard.shard_id.to_string()).take(shard.shard_routing_count)
                })
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_routing_shard_states={}",
            routing_table
                .indices
                .iter()
                .flat_map(|index| index.shards.iter())
                .flat_map(|shard| shard.shard_routings.iter())
                .map(|shard| format!("{:?}", shard.state))
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_routing_shard_primaries={}",
            routing_table
                .indices
                .iter()
                .flat_map(|index| index.shards.iter())
                .flat_map(|shard| shard.shard_routings.iter())
                .map(|shard| shard.primary.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_routing_shard_current_node_ids={}",
            routing_table
                .indices
                .iter()
                .flat_map(|index| index.shards.iter())
                .flat_map(|shard| shard.shard_routings.iter())
                .map(|shard| shard.current_node_id.as_deref().unwrap_or(""))
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_routing_shard_allocation_ids={}",
            routing_table
                .indices
                .iter()
                .flat_map(|index| index.shards.iter())
                .flat_map(|shard| shard.shard_routings.iter())
                .map(|shard| {
                    shard
                        .allocation_id
                        .as_ref()
                        .map(|allocation| allocation.id.as_str())
                        .unwrap_or("")
                })
                .collect::<Vec<_>>()
                .join(",")
        );
    }
    if let Some(nodes) = &response.discovery_nodes {
        line!("cluster_state_nodes={}", nodes.node_count);
        line!(
            "cluster_state_cluster_manager_node_id={}",
            nodes.cluster_manager_node_id.as_deref().unwrap_or("")
        );
        line!(
            "cluster_state_node_ids={}",
            nodes
                .nodes
                .iter()
                .map(|node| node.id.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_node_names={}",
            nodes
                .nodes
                .iter()
                .map(|node| node.name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_node_addresses={}",
            nodes
                .nodes
                .iter()
                .map(|node| format!("{}:{}", node.address.ip, node.address.port))
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_node_role_counts={}",
            nodes
                .nodes
                .iter()
                .map(|node| node.roles.len().to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_node_attribute_counts={}",
            nodes
                .nodes
                .iter()
                .map(|node| node.attribute_count.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
    }
    if let Some(blocks) = &response.cluster_blocks {
        line!("cluster_state_global_blocks={}", blocks.global_block_count);
        line!("cluster_state_index_blocks={}", blocks.index_block_count);
        line!(
            "cluster_state_index_block_names={}",
            blocks
                .index_blocks
                .iter()
                .map(|index| index.index_name.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_block_entries={}",
            blocks.global_blocks.len()
                + blocks
                    .index_blocks
                    .iter()
                    .map(|index| index.block_count)
                    .sum::<usize>()
        );
        line!(
            "cluster_state_global_block_ids={}",
            blocks
                .global_blocks
                .iter()
                .map(|block| block.id.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_global_block_uuids={}",
            blocks
                .global_blocks
                .iter()
                .map(|block| block.uuid.as_deref().unwrap_or(""))
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_global_block_levels={}",
            blocks
                .global_blocks
                .iter()
                .map(cluster_block_levels_summary)
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_global_block_statuses={}",
            blocks
                .global_blocks
                .iter()
                .map(|block| block.status.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
        let index_block_entries = blocks
            .index_blocks
            .iter()
            .flat_map(|index| index.blocks.iter())
            .collect::<Vec<_>>();
        line!(
            "cluster_state_index_block_ids={}",
            index_block_entries
                .iter()
                .map(|block| block.id.to_string())
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_index_block_uuids={}",
            index_block_entries
                .iter()
                .map(|block| block.uuid.as_deref().unwrap_or(""))
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_index_block_levels={}",
            index_block_entries
                .iter()
                .map(|block| cluster_block_levels_summary(block))
                .collect::<Vec<_>>()
                .join(",")
        );
        line!(
            "cluster_state_index_block_statuses={}",
            index_block_entries
                .iter()
                .map(|block| block.status.as_str())
                .collect::<Vec<_>>()
                .join(",")
        );
    }
    if let Some(tail) = &response.cluster_state_tail {
        line!("cluster_state_custom_count={}", tail.custom_count);
        line!("cluster_state_custom_names={}", tail.custom_names.join(","));
        line!(
            "cluster_state_repository_cleanup_entries={}",
            tail.repository_cleanup
                .as_ref()
                .map(|custom| custom.entry_count)
                .unwrap_or(0)
        );
        line!(
            "cluster_state_repository_cleanup_repositories={}",
            tail.repository_cleanup
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.repository.as_str())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_repository_cleanup_state_ids={}",
            tail.repository_cleanup
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.repository_state_id.to_string())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_snapshot_deletions_entries={}",
            tail.snapshot_deletions
                .as_ref()
                .map(|custom| custom.entry_count)
                .unwrap_or(0)
        );
        line!(
            "cluster_state_snapshot_deletion_uuids={}",
            tail.snapshot_deletions
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.uuid.as_str())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_snapshot_deletion_repositories={}",
            tail.snapshot_deletions
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.repository.as_str())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_snapshot_deletion_snapshot_counts={}",
            tail.snapshot_deletions
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.snapshots_count.to_string())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_snapshot_deletion_state_ids={}",
            tail.snapshot_deletions
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.state_id.to_string())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_restore_entries={}",
            tail.restore
                .as_ref()
                .map(|custom| custom.entry_count)
                .unwrap_or(0)
        );
        line!(
            "cluster_state_restore_uuids={}",
            tail.restore
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.uuid.as_str())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_restore_repositories={}",
            tail.restore
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.repository.as_str())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_restore_snapshot_names={}",
            tail.restore
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.snapshot_name.as_str())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_restore_state_ids={}",
            tail.restore
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.state_id.to_string())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_restore_shard_status_counts={}",
            tail.restore
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.shard_status_count.to_string())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_snapshots_entries={}",
            tail.snapshots
                .as_ref()
                .map(|custom| custom.entry_count)
                .unwrap_or(0)
        );
        line!(
            "cluster_state_snapshot_names={}",
            tail.snapshots
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.snapshot_name.as_str())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_snapshot_repositories={}",
            tail.snapshots
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.repository.as_str())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_snapshot_uuids={}",
            tail.snapshots
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.snapshot_uuid.as_str())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_snapshot_state_ids={}",
            tail.snapshots
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.state_id.to_string())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
        line!(
            "cluster_state_snapshot_shard_status_counts={}",
            tail.snapshots
                .as_ref()
                .map(|custom| {
                    custom
                        .entries
                        .iter()
                        .map(|entry| entry.shard_status_count.to_string())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default()
        );
    }
    line!(
        "cluster_state_remaining_bytes={}",
        response.remaining_state_bytes_after_prefix
    );
    output
}

fn decoded_metadata_custom_names(metadata: &os_cluster_state::MetadataPrefix) -> Vec<&'static str> {
    let mut names = Vec::new();
    if metadata.index_graveyard_tombstones_count.is_some() {
        names.push("index-graveyard");
    }
    if metadata.ingest_pipelines_count.is_some() {
        names.push("ingest");
    }
    if metadata.search_pipelines_count.is_some() {
        names.push("search_pipeline");
    }
    if metadata.stored_scripts_count.is_some() {
        names.push("stored_scripts");
    }
    if metadata.persistent_tasks_count.is_some() {
        names.push("persistent_tasks");
    }
    if metadata.decommission_attribute.is_some() {
        names.push("decommissionedAttribute");
    }
    if metadata.component_templates_count.is_some() {
        names.push("component_template");
    }
    if metadata.composable_index_templates_count.is_some() {
        names.push("index_template");
    }
    if metadata.data_streams_count.is_some() {
        names.push("data_stream");
    }
    if metadata.repositories_count.is_some() {
        names.push("repositories");
    }
    if metadata.weighted_routing.is_some() {
        names.push("weighted_shard_routing");
    }
    if metadata.views_count.is_some() {
        names.push("view");
    }
    if metadata.workload_groups_count.is_some() {
        names.push("queryGroups");
    }
    names
}

fn cluster_block_levels_summary(block: &ClusterBlockPrefix) -> String {
    block
        .levels
        .iter()
        .map(cluster_block_level_name)
        .collect::<Vec<_>>()
        .join("+")
}

fn cluster_block_level_name(level: &ClusterBlockLevelPrefix) -> &'static str {
    match level {
        ClusterBlockLevelPrefix::Read => "read",
        ClusterBlockLevelPrefix::Write => "write",
        ClusterBlockLevelPrefix::MetadataRead => "metadata_read",
        ClusterBlockLevelPrefix::MetadataWrite => "metadata_write",
        ClusterBlockLevelPrefix::CreateIndex => "create_index",
    }
}

fn read_expected_message(
    stream: &mut TcpStream,
    request_id: i64,
    expect_handshake_status: bool,
) -> Result<TransportMessage> {
    let response = read_one_frame(stream)?;
    let DecodedFrame::Message(message) = response else {
        bail!("received ping while waiting for response");
    };

    if message.request_id != request_id {
        bail!(
            "response request id mismatch: got {}, expected {}",
            message.request_id,
            request_id
        );
    }
    if !message.status.is_response() {
        bail!(
            "unexpected response status: bits={:#010b}",
            message.status.bits()
        );
    }
    if message.status.is_handshake() != expect_handshake_status {
        bail!(
            "unexpected handshake status bit: got {}, expected {}",
            message.status.is_handshake(),
            expect_handshake_status
        );
    }
    if message.status.is_error() {
        let decoded = TransportError::read(message.body.clone().freeze())
            .map_err(anyhow::Error::from)
            .map(|error| {
                error
                    .map(|error| error.summary())
                    .unwrap_or_else(|| "empty transport error".to_string())
            })
            .unwrap_or_else(|err| format!("failed to decode transport error: {err}"));
        bail!("request failed with transport error response: {decoded}");
    }

    Ok(message)
}

fn read_one_frame(stream: &mut TcpStream) -> Result<DecodedFrame> {
    let mut prefix = [0u8; TcpHeader::BYTES_REQUIRED_FOR_MESSAGE_SIZE];
    stream
        .read_exact(&mut prefix)
        .context("failed to read transport frame prefix")?;
    if &prefix[..2] != b"ES" {
        bail!("transport frame does not start with ES marker");
    }

    let message_size = i32::from_be_bytes(prefix[2..6].try_into().unwrap());
    if message_size < 0 {
        bail!("negative transport message size: {message_size}");
    }

    let mut frame = BytesMut::with_capacity(prefix.len() + message_size as usize);
    frame.put_slice(&prefix);
    frame.resize(prefix.len() + message_size as usize, 0);
    stream
        .read_exact(&mut frame[prefix.len()..])
        .context("failed to read complete transport frame")?;

    decode_frame(&mut frame)?
        .ok_or_else(|| anyhow!("transport frame decoder returned partial frame"))
}

fn parse_args(mut args: impl Iterator<Item = String>) -> Result<ProbeConfig> {
    let mut config = ProbeConfig {
        addr: DEFAULT_ADDR.to_string(),
        request_id: 1,
        header_version: Version::from_id(DEFAULT_HEADER_VERSION_ID),
        payload_version: Version::from_id(DEFAULT_PAYLOAD_VERSION_ID),
        timeout: Duration::from_secs(5),
        cluster_state: false,
        cluster_state_full: false,
    };

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--addr" => config.addr = next_value(&mut args, "--addr")?,
            "--request-id" => config.request_id = parse_next(&mut args, "--request-id")?,
            "--header-version-id" => {
                config.header_version =
                    Version::from_id(parse_next(&mut args, "--header-version-id")?)
            }
            "--payload-version-id" => {
                config.payload_version =
                    Version::from_id(parse_next(&mut args, "--payload-version-id")?)
            }
            "--timeout" => {
                let raw = next_value(&mut args, "--timeout")?;
                config.timeout = humantime::parse_duration(&raw)
                    .with_context(|| format!("invalid --timeout value: {raw}"))?;
            }
            "--cluster-state" => config.cluster_state = true,
            "--cluster-state-full" => {
                config.cluster_state = true;
                config.cluster_state_full = true;
            }
            "--help" | "-h" => {
                print_help();
                std::process::exit(0);
            }
            other => bail!("unknown argument: {other}"),
        }
    }

    Ok(config)
}

fn next_value(args: &mut impl Iterator<Item = String>, name: &str) -> Result<String> {
    args.next()
        .ok_or_else(|| anyhow!("missing value for {name}"))
}

fn parse_next<T>(args: &mut impl Iterator<Item = String>, name: &str) -> Result<T>
where
    T: std::str::FromStr,
    T::Err: std::error::Error + Send + Sync + 'static,
{
    let value = next_value(args, name)?;
    value
        .parse::<T>()
        .with_context(|| format!("invalid value for {name}: {value}"))
}

fn resolve_addr(addr: &str) -> Result<SocketAddr> {
    addr.to_socket_addrs()
        .with_context(|| format!("failed to resolve {addr}"))?
        .next()
        .ok_or_else(|| anyhow!("no socket address resolved for {addr}"))
}

fn print_help() {
    println!(
        "Usage: os-tcp-probe [--addr HOST:PORT] [--timeout 5s] \\
         [--request-id ID] [--header-version-id ID] [--payload-version-id ID] \\
         [--cluster-state] [--cluster-state-full]"
    );
}

#[cfg(test)]
mod tests {
    use super::format_cluster_state_prefix;
    use os_cluster_state::{
        AllocationIdPrefix, ClusterBlockLevelPrefix, ClusterBlockPrefix, ClusterBlocksPrefix,
        ClusterStateHeader, ClusterStateResponsePrefix, ClusterStateTailPrefix,
        ComponentTemplatePrefix, ComposableIndexTemplatePrefix, CoordinationMetadataPrefix,
        DiscoveryNodePrefix, DiscoveryNodeRolePrefix, DiscoveryNodesPrefix,
        IndexClusterBlocksPrefix, IndexGraveyardTombstonePrefix, IndexMetadataPrefix,
        IndexRoutingTablePrefix, IndexShardRoutingTablePrefix, IndexTemplateMetadataPrefix,
        MetadataPrefix, RepositoryCleanupEntryPrefix, RepositoryCleanupInProgressPrefix,
        RestoreEntryPrefix, RestoreInProgressPrefix, RoutingTablePrefix, ShardRoutingPrefix,
        ShardRoutingStatePrefix, SnapshotDeletionEntryPrefix, SnapshotDeletionsInProgressPrefix,
        SnapshotIdPrefix, SnapshotInProgressEntryPrefix, SnapshotsInProgressPrefix,
        TransportAddressPrefix,
    };
    use std::collections::BTreeSet;
    use std::net::{IpAddr, Ipv4Addr};

    #[test]
    fn formats_cluster_state_prefix_with_stable_keys() {
        let response = ClusterStateResponsePrefix {
            response_cluster_name: "steel".to_string(),
            state_header: Some(ClusterStateHeader {
                version: 42,
                state_uuid: "uuid-1".to_string(),
                cluster_name: "steel".to_string(),
            }),
            metadata_prefix: Some(MetadataPrefix {
                version: 7,
                cluster_uuid: "cluster-uuid".to_string(),
                cluster_uuid_committed: true,
                coordination: CoordinationMetadataPrefix {
                    term: 0,
                    last_committed_configuration: BTreeSet::new(),
                    last_accepted_configuration: BTreeSet::new(),
                    voting_config_exclusions: Vec::new(),
                },
                transient_settings_count: 0,
                transient_settings: Vec::new(),
                persistent_settings_count: 0,
                persistent_settings: Vec::new(),
                hashes_of_consistent_settings_count: 0,
                hashes_of_consistent_settings: Vec::new(),
                index_metadata_count: 1,
                index_metadata: vec![IndexMetadataPrefix {
                    name: "index-a".to_string(),
                    version: 11,
                    mapping_version: 12,
                    settings_version: 13,
                    aliases_version: 14,
                    routing_num_shards: 5,
                    state_id: 0,
                    settings_count: 4,
                    index_uuid: Some("index-a-uuid".to_string()),
                    number_of_shards: Some(1),
                    number_of_replicas: Some(2),
                    mapping_count: 1,
                    mappings: Vec::new(),
                    alias_count: 1,
                    aliases: Vec::new(),
                    custom_data_count: 0,
                    custom_data: Vec::new(),
                    in_sync_allocation_ids_count: 0,
                    rollover_info_count: 0,
                    rollover_infos: Vec::new(),
                    system: false,
                    context_present: false,
                    ingestion_status_present: false,
                    ingestion_paused: None,
                    split_shards_root_count: None,
                    split_shards_root_children: Vec::new(),
                    split_shards_max_shard_id: None,
                    split_shards_in_progress_count: None,
                    split_shards_active_count: None,
                    split_shards_parent_to_child_count: None,
                    split_shards_parent_to_child: Vec::new(),
                    primary_terms_count: 0,
                }],
                templates_count: 1,
                templates: vec![IndexTemplateMetadataPrefix {
                    name: "legacy-template-a".to_string(),
                    order: 0,
                    patterns: vec!["legacy-a-*".to_string()],
                    settings_count: 2,
                    settings: Vec::new(),
                    mappings_count: 1,
                    mappings: Vec::new(),
                    aliases_count: 1,
                    aliases: Vec::new(),
                    version: Some(3),
                }],
                custom_metadata_count: 3,
                ingest_pipelines_count: None,
                ingest_pipelines: Vec::new(),
                search_pipelines_count: None,
                search_pipelines: Vec::new(),
                stored_scripts_count: None,
                stored_scripts: Vec::new(),
                persistent_tasks_count: None,
                persistent_tasks: Vec::new(),
                decommission_attribute: None,
                index_graveyard_tombstones_count: Some(1),
                index_graveyard_tombstones: vec![IndexGraveyardTombstonePrefix {
                    index_name: "deleted-index-a".to_string(),
                    index_uuid: "deleted-index-a-uuid".to_string(),
                    delete_date_in_millis: 1_714_000_000_000,
                }],
                component_templates_count: Some(1),
                component_templates: vec![ComponentTemplatePrefix {
                    name: "component-template-a".to_string(),
                    settings_count: 2,
                    settings: Vec::new(),
                    mappings_present: true,
                    mapping: None,
                    aliases_count: 1,
                    aliases: Vec::new(),
                    version: Some(4),
                    metadata_present: false,
                    metadata_count: 0,
                    metadata: Vec::new(),
                }],
                composable_index_templates_count: Some(1),
                composable_index_templates: vec![ComposableIndexTemplatePrefix {
                    name: "composable-template-a".to_string(),
                    index_patterns: vec!["composable-a-*".to_string()],
                    template_present: true,
                    template_settings_count: 2,
                    template_settings: Vec::new(),
                    template_mappings_present: true,
                    template_mapping: None,
                    template_aliases_count: 1,
                    template_aliases: Vec::new(),
                    component_templates_count: 1,
                    component_templates: vec!["component-template-a".to_string()],
                    priority: Some(10),
                    version: Some(5),
                    metadata_count: 0,
                    metadata: Vec::new(),
                    data_stream_template_present: false,
                    data_stream_timestamp_field: None,
                    context_present: false,
                    context_name: None,
                    context_version: None,
                    context_params_count: 0,
                    context_params: Vec::new(),
                }],
                data_streams_count: Some(0),
                data_streams: Vec::new(),
                repositories_count: None,
                repositories: Vec::new(),
                weighted_routing: None,
                views_count: None,
                views: Vec::new(),
                workload_groups_count: None,
                workload_groups: Vec::new(),
            }),
            routing_table: Some(RoutingTablePrefix {
                version: 0,
                index_routing_table_count: 1,
                indices: vec![IndexRoutingTablePrefix {
                    index_name: "index-a".to_string(),
                    index_uuid: "index-a-uuid".to_string(),
                    shard_table_count: 1,
                    shards: vec![IndexShardRoutingTablePrefix {
                        shard_id: 0,
                        shard_routing_count: 2,
                        shard_routings: vec![
                            ShardRoutingPrefix {
                                current_node_id: Some("node-1".to_string()),
                                relocating_node_id: None,
                                primary: true,
                                search_only: false,
                                state: ShardRoutingStatePrefix::Started,
                                recovery_source_type: None,
                                recovery_source_bootstrap_new_history_uuid: None,
                                snapshot_recovery_source: None,
                                remote_store_recovery_source: None,
                                unassigned_info: None,
                                allocation_id_present: true,
                                allocation_id: Some(AllocationIdPrefix {
                                    id: "alloc-primary".to_string(),
                                    relocation_id: None,
                                    split_child_allocation_ids_count: None,
                                    parent_allocation_id: None,
                                }),
                                expected_shard_size: None,
                            },
                            ShardRoutingPrefix {
                                current_node_id: None,
                                relocating_node_id: None,
                                primary: false,
                                search_only: false,
                                state: ShardRoutingStatePrefix::Unassigned,
                                recovery_source_type: None,
                                recovery_source_bootstrap_new_history_uuid: None,
                                snapshot_recovery_source: None,
                                remote_store_recovery_source: None,
                                unassigned_info: None,
                                allocation_id_present: false,
                                allocation_id: None,
                                expected_shard_size: None,
                            },
                        ],
                    }],
                }],
            }),
            discovery_nodes: Some(DiscoveryNodesPrefix {
                cluster_manager_node_id: Some("node-1".to_string()),
                node_count: 1,
                nodes: vec![DiscoveryNodePrefix {
                    name: "node-a".to_string(),
                    id: "node-1".to_string(),
                    ephemeral_id: "ephemeral-1".to_string(),
                    host_name: "localhost".to_string(),
                    host_address: "127.0.0.1".to_string(),
                    address: TransportAddressPrefix {
                        ip: IpAddr::V4(Ipv4Addr::LOCALHOST),
                        host: "localhost".to_string(),
                        port: 9300,
                    },
                    stream_address: None,
                    attribute_count: 2,
                    roles: vec![DiscoveryNodeRolePrefix {
                        name: "cluster_manager".to_string(),
                        abbreviation: "m".to_string(),
                        can_contain_data: false,
                    }],
                    version: 1,
                }],
            }),
            cluster_blocks: Some(ClusterBlocksPrefix {
                global_block_count: 1,
                global_blocks: vec![ClusterBlockPrefix {
                    id: 1,
                    uuid: Some("global-block-uuid".to_string()),
                    description: "global block".to_string(),
                    levels: vec![ClusterBlockLevelPrefix::MetadataWrite],
                    retryable: false,
                    disable_state_persistence: false,
                    status: "SERVICE_UNAVAILABLE".to_string(),
                    allow_release_resources: false,
                }],
                index_block_count: 1,
                index_blocks: vec![IndexClusterBlocksPrefix {
                    index_name: "index-a".to_string(),
                    block_count: 1,
                    blocks: vec![ClusterBlockPrefix {
                        id: 2,
                        uuid: None,
                        description: "index block".to_string(),
                        levels: vec![ClusterBlockLevelPrefix::Read],
                        retryable: true,
                        disable_state_persistence: false,
                        status: "FORBIDDEN".to_string(),
                        allow_release_resources: false,
                    }],
                }],
            }),
            cluster_state_tail: Some(ClusterStateTailPrefix {
                custom_count: 4,
                custom_names: vec![
                    "repository_cleanup".to_string(),
                    "snapshot_deletions".to_string(),
                    "restore".to_string(),
                    "snapshots".to_string(),
                ],
                repository_cleanup: Some(RepositoryCleanupInProgressPrefix {
                    entry_count: 1,
                    entries: vec![RepositoryCleanupEntryPrefix {
                        repository: "repo-a".to_string(),
                        repository_state_id: 7,
                    }],
                }),
                snapshot_deletions: Some(SnapshotDeletionsInProgressPrefix {
                    entry_count: 1,
                    entries: vec![SnapshotDeletionEntryPrefix {
                        repository: "repo-b".to_string(),
                        snapshots_count: 1,
                        snapshots: vec![SnapshotIdPrefix {
                            name: "snapshot-delete-a".to_string(),
                            uuid: "snapshot-delete-uuid".to_string(),
                        }],
                        start_time: 123,
                        repository_state_id: 8,
                        state_id: 2,
                        uuid: "delete-entry-uuid".to_string(),
                    }],
                }),
                restore: Some(RestoreInProgressPrefix {
                    entry_count: 1,
                    entries: vec![RestoreEntryPrefix {
                        uuid: "restore-uuid".to_string(),
                        repository: "repo-c".to_string(),
                        snapshot_name: "snapshot-restore-a".to_string(),
                        snapshot_uuid: "snapshot-restore-uuid".to_string(),
                        state_id: 1,
                        indices_count: 1,
                        indices: vec!["index-a".to_string()],
                        shard_status_count: 0,
                        shard_statuses: Vec::new(),
                    }],
                }),
                snapshots: Some(SnapshotsInProgressPrefix {
                    entry_count: 1,
                    entries: vec![SnapshotInProgressEntryPrefix {
                        repository: "repo-d".to_string(),
                        snapshot_name: "snapshot-live-a".to_string(),
                        snapshot_uuid: "snapshot-live-uuid".to_string(),
                        include_global_state: false,
                        partial: false,
                        state_id: 3,
                        indices_count: 0,
                        indices: Vec::new(),
                        start_time: 456,
                        shard_status_count: 0,
                        shard_statuses: Vec::new(),
                        repository_state_id: 9,
                        failure: None,
                        user_metadata_count: 0,
                        user_metadata: Vec::new(),
                        version_id: 137_287_827,
                        data_streams_count: 0,
                        data_streams: Vec::new(),
                        source: None,
                        clone_count: 0,
                        clones: Vec::new(),
                        remote_store_index_shallow_copy: None,
                        remote_store_index_shallow_copy_v2: None,
                    }],
                }),
                minimum_cluster_manager_nodes_on_publishing_cluster_manager: -1,
            }),
            wait_for_timed_out: Some(false),
            remaining_state_bytes_after_prefix: 0,
        };

        assert_eq!(
            format_cluster_state_prefix(&response),
            "\
cluster_state_response_cluster_name=steel\n\
cluster_state_wait_for_timed_out=false\n\
cluster_state_name=steel\n\
cluster_state_version=42\n\
cluster_state_uuid=uuid-1\n\
cluster_state_metadata_version=7\n\
cluster_state_cluster_uuid=cluster-uuid\n\
cluster_state_metadata_custom_count=3\n\
cluster_state_metadata_indices=1\n\
cluster_state_metadata_index_names=index-a\n\
cluster_state_metadata_index_uuids=index-a-uuid\n\
cluster_state_metadata_index_routing_shard_counts=5\n\
cluster_state_metadata_index_primary_shard_counts=1\n\
cluster_state_metadata_index_replica_counts=2\n\
cluster_state_metadata_index_setting_counts=4\n\
cluster_state_metadata_index_mapping_counts=1\n\
cluster_state_metadata_index_alias_counts=1\n\
cluster_state_metadata_legacy_templates=1\n\
cluster_state_metadata_legacy_template_names=legacy-template-a\n\
cluster_state_metadata_legacy_template_patterns=legacy-a-*\n\
cluster_state_metadata_legacy_template_setting_counts=2\n\
cluster_state_metadata_legacy_template_mapping_counts=1\n\
cluster_state_metadata_legacy_template_alias_counts=1\n\
cluster_state_metadata_index_graveyard_tombstones=1\n\
cluster_state_metadata_index_graveyard_tombstone_names=deleted-index-a\n\
cluster_state_metadata_index_graveyard_tombstone_uuids=deleted-index-a-uuid\n\
cluster_state_metadata_index_graveyard_tombstone_delete_timestamps=1714000000000\n\
cluster_state_metadata_ingest_pipelines=0\n\
cluster_state_metadata_ingest_pipeline_ids=\n\
cluster_state_metadata_search_pipelines=0\n\
cluster_state_metadata_search_pipeline_ids=\n\
cluster_state_metadata_stored_scripts=0\n\
cluster_state_metadata_stored_script_ids=\n\
cluster_state_metadata_stored_script_langs=\n\
cluster_state_metadata_persistent_tasks=0\n\
cluster_state_metadata_persistent_task_names=\n\
cluster_state_metadata_persistent_task_param_names=\n\
cluster_state_metadata_persistent_task_fixture_markers=\n\
cluster_state_metadata_persistent_task_fixture_generations=\n\
cluster_state_metadata_persistent_task_state_names=\n\
cluster_state_metadata_persistent_task_fixture_state_markers=\n\
cluster_state_metadata_persistent_task_fixture_state_generations=\n\
cluster_state_metadata_decommissioned_attribute=0\n\
cluster_state_metadata_component_templates=1\n\
cluster_state_metadata_component_template_names=component-template-a\n\
cluster_state_metadata_component_template_versions=4\n\
cluster_state_metadata_component_template_setting_counts=2\n\
cluster_state_metadata_component_template_mapping_counts=1\n\
cluster_state_metadata_component_template_alias_counts=1\n\
cluster_state_metadata_composable_templates=1\n\
cluster_state_metadata_composable_template_names=composable-template-a\n\
cluster_state_metadata_composable_template_index_patterns=composable-a-*\n\
cluster_state_metadata_composable_template_components=component-template-a\n\
cluster_state_metadata_composable_template_setting_counts=2\n\
cluster_state_metadata_composable_template_mapping_counts=1\n\
cluster_state_metadata_composable_template_alias_counts=1\n\
cluster_state_metadata_data_streams=0\n\
cluster_state_metadata_data_stream_names=\n\
cluster_state_metadata_data_stream_timestamp_fields=\n\
cluster_state_metadata_data_stream_backing_index_counts=\n\
cluster_state_metadata_data_stream_backing_index_names=\n\
cluster_state_metadata_data_stream_generations=\n\
cluster_state_metadata_repositories=0\n\
cluster_state_metadata_repository_names=\n\
cluster_state_metadata_repository_types=\n\
cluster_state_metadata_repository_setting_counts=\n\
cluster_state_metadata_repository_generations=\n\
cluster_state_metadata_repository_pending_generations=\n\
cluster_state_metadata_repository_crypto_provider_names=\n\
cluster_state_metadata_repository_crypto_provider_types=\n\
cluster_state_metadata_views=0\n\
cluster_state_metadata_view_names=\n\
cluster_state_metadata_view_target_patterns=\n\
cluster_state_metadata_workload_groups=0\n\
cluster_state_metadata_workload_group_names=\n\
cluster_state_metadata_workload_group_ids=\n\
cluster_state_metadata_workload_group_resource_limit_counts=\n\
cluster_state_metadata_workload_group_search_setting_counts=\n\
cluster_state_metadata_workload_group_resiliency_modes=\n\
cluster_state_metadata_weighted_routing=0\n\
cluster_state_metadata_decoded_custom_count=4\n\
cluster_state_metadata_decoded_customs=index-graveyard,component_template,index_template,data_stream\n\
cluster_state_routing_indices=1\n\
cluster_state_routing_index_names=index-a\n\
cluster_state_routing_shard_tables=1\n\
cluster_state_routing_shards=2\n\
cluster_state_routing_shard_ids=0,0\n\
cluster_state_routing_shard_states=Started,Unassigned\n\
cluster_state_routing_shard_primaries=true,false\n\
cluster_state_routing_shard_current_node_ids=node-1,\n\
cluster_state_routing_shard_allocation_ids=alloc-primary,\n\
cluster_state_nodes=1\n\
cluster_state_cluster_manager_node_id=node-1\n\
cluster_state_node_ids=node-1\n\
cluster_state_node_names=node-a\n\
cluster_state_node_addresses=127.0.0.1:9300\n\
cluster_state_node_role_counts=1\n\
cluster_state_node_attribute_counts=2\n\
cluster_state_global_blocks=1\n\
cluster_state_index_blocks=1\n\
cluster_state_index_block_names=index-a\n\
cluster_state_block_entries=2\n\
cluster_state_global_block_ids=1\n\
cluster_state_global_block_uuids=global-block-uuid\n\
cluster_state_global_block_levels=metadata_write\n\
cluster_state_global_block_statuses=SERVICE_UNAVAILABLE\n\
cluster_state_index_block_ids=2\n\
cluster_state_index_block_uuids=\n\
cluster_state_index_block_levels=read\n\
cluster_state_index_block_statuses=FORBIDDEN\n\
cluster_state_custom_count=4\n\
cluster_state_custom_names=repository_cleanup,snapshot_deletions,restore,snapshots\n\
cluster_state_repository_cleanup_entries=1\n\
cluster_state_repository_cleanup_repositories=repo-a\n\
cluster_state_repository_cleanup_state_ids=7\n\
cluster_state_snapshot_deletions_entries=1\n\
cluster_state_snapshot_deletion_uuids=delete-entry-uuid\n\
cluster_state_snapshot_deletion_repositories=repo-b\n\
cluster_state_snapshot_deletion_snapshot_counts=1\n\
cluster_state_snapshot_deletion_state_ids=2\n\
cluster_state_restore_entries=1\n\
cluster_state_restore_uuids=restore-uuid\n\
cluster_state_restore_repositories=repo-c\n\
cluster_state_restore_snapshot_names=snapshot-restore-a\n\
cluster_state_restore_state_ids=1\n\
cluster_state_restore_shard_status_counts=0\n\
cluster_state_snapshots_entries=1\n\
cluster_state_snapshot_names=snapshot-live-a\n\
cluster_state_snapshot_repositories=repo-d\n\
cluster_state_snapshot_uuids=snapshot-live-uuid\n\
cluster_state_snapshot_state_ids=3\n\
cluster_state_snapshot_shard_status_counts=0\n\
cluster_state_remaining_bytes=0\n"
        );
    }
}
