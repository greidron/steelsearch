use base64::engine::general_purpose::STANDARD;
use base64::Engine;
use bytes::{Bytes, BytesMut};
use os_cluster_state::{
    build_cluster_state_request_frame, read_publication_cluster_state_diff,
    read_publication_cluster_state_diff_prefix, ClusterBlockLevel, ClusterBlockLevelPrefix,
    ClusterState, ClusterStateRequest, ClusterStateResponsePrefix, GenericValuePrefix,
    RecoverySourceTypePrefix, ShardRoutingState, ShardRoutingStatePrefix, CLUSTER_STATE_ACTION,
};
use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_stream::StreamInput;
use os_transport::frame::{decode_frame, DecodedFrame};
use os_transport::variable_header::RequestVariableHeader;
use os_wire::TcpHeader;
use std::collections::BTreeMap;
use std::net::{IpAddr, Ipv4Addr};

fn fixtures() -> BTreeMap<&'static str, Vec<u8>> {
    include_str!("../../../fixtures/java/opensearch-wire-fixtures.txt")
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(|line| {
            let (name, value) = line.split_once('=').unwrap();
            (name, STANDARD.decode(value).unwrap())
        })
        .collect()
}

fn decode_cluster_state_fixture(
    fixtures: &BTreeMap<&'static str, Vec<u8>>,
    name: &'static str,
) -> ClusterState {
    ClusterStateResponsePrefix::read(Bytes::from(fixtures.get(name).unwrap().clone()))
        .unwrap()
        .into_cluster_state()
        .unwrap()
}

fn assert_publication_diff_applies_to_post_state(
    before_fixture: &'static str,
    diff_fixture: &'static str,
    after_fixture: &'static str,
) -> ClusterState {
    let fixtures = fixtures();
    let before = decode_cluster_state_fixture(&fixtures, before_fixture);
    let after = decode_cluster_state_fixture(&fixtures, after_fixture);
    let diff = read_publication_cluster_state_diff(
        Bytes::from(fixtures.get(diff_fixture).unwrap().clone()),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();
    let applied = diff.apply_to(&before).unwrap();

    assert_eq!(applied, after);
    applied
}

#[test]
fn java_cluster_state_request_fixture_matches_rust_builder() {
    let fixtures = fixtures();
    let rust_bytes = ClusterStateRequest::default().to_bytes();

    assert_eq!(
        rust_bytes.as_ref(),
        fixtures.get("cluster_state_request_default").unwrap()
    );
}

#[test]
fn java_cluster_state_transport_request_fixture_matches_rust_builder() {
    let fixtures = fixtures();
    let java_bytes = fixtures
        .get("cluster_state_transport_request_default")
        .unwrap()
        .clone();
    let header = TcpHeader::decode(&java_bytes[..TcpHeader::HEADER_SIZE]).unwrap();
    let rust_bytes = build_cluster_state_request_frame(
        header.request_id,
        header.version,
        &ClusterStateRequest::default(),
    );

    assert_eq!(&rust_bytes[..], &java_bytes[..]);
}

#[test]
fn java_cluster_state_transport_request_frame_decodes() {
    let fixtures = fixtures();
    let mut frame = BytesMut::from(
        fixtures
            .get("cluster_state_transport_request_default")
            .unwrap()
            .as_slice(),
    );

    let DecodedFrame::Message(message) = decode_frame(&mut frame).unwrap().unwrap() else {
        panic!("expected message frame");
    };
    let variable_header = RequestVariableHeader::read(message.variable_header.freeze()).unwrap();

    assert_eq!(message.request_id, 3);
    assert_eq!(message.version, OPENSEARCH_3_7_0_TRANSPORT);
    assert!(message.status.is_request());
    assert_eq!(variable_header.action, CLUSTER_STATE_ACTION);
    assert_eq!(
        message.body.freeze(),
        ClusterStateRequest::default().to_bytes()
    );
    assert!(frame.is_empty());
}

#[test]
fn java_cluster_state_response_fixture_decodes_prefix() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_minimal")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(response.response_cluster_name, "fixture-cluster");
    assert_eq!(header.cluster_name, "fixture-cluster");
    assert_eq!(header.version, 7);
    assert_eq!(header.state_uuid, "fixture-state-uuid");
    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.version, 0);
    assert_eq!(metadata.cluster_uuid, "_na_");
    assert!(!metadata.cluster_uuid_committed);
    assert_eq!(metadata.coordination.term, 0);
    assert!(metadata
        .coordination
        .last_committed_configuration
        .is_empty());
    assert!(metadata.coordination.last_accepted_configuration.is_empty());
    assert!(metadata.coordination.voting_config_exclusions.is_empty());
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
    assert_eq!(metadata.ingest_pipelines_count, None);
    assert!(metadata.ingest_pipelines.is_empty());
    assert_eq!(metadata.search_pipelines_count, None);
    assert!(metadata.search_pipelines.is_empty());
    assert_eq!(metadata.stored_scripts_count, None);
    assert!(metadata.stored_scripts.is_empty());
    assert_eq!(metadata.persistent_tasks_count, None);
    assert!(metadata.persistent_tasks.is_empty());
    assert_eq!(metadata.decommission_attribute, None);
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
    let routing_table = response.routing_table.unwrap();
    assert_eq!(routing_table.version, 0);
    assert_eq!(routing_table.index_routing_table_count, 0);
    assert!(routing_table.indices.is_empty());
    let discovery_nodes = response.discovery_nodes.unwrap();
    assert_eq!(discovery_nodes.cluster_manager_node_id, None);
    assert_eq!(discovery_nodes.node_count, 0);
    let cluster_blocks = response.cluster_blocks.unwrap();
    assert_eq!(cluster_blocks.global_block_count, 0);
    assert!(cluster_blocks.global_blocks.is_empty());
    assert_eq!(cluster_blocks.index_block_count, 0);
    let cluster_state_tail = response.cluster_state_tail.unwrap();
    assert_eq!(cluster_state_tail.custom_count, 0);
    assert!(cluster_state_tail.custom_names.is_empty());
    assert_eq!(cluster_state_tail.repository_cleanup, None);
    assert_eq!(cluster_state_tail.snapshot_deletions, None);
    assert_eq!(cluster_state_tail.restore, None);
    assert_eq!(cluster_state_tail.snapshots, None);
    assert_eq!(
        cluster_state_tail.minimum_cluster_manager_nodes_on_publishing_cluster_manager,
        -1
    );
    assert_eq!(response.wait_for_timed_out, Some(false));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_acceptance_single_node_full_decodes_typed_without_remaining_bytes() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_acceptance_single_node_full")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
    let state = response.into_cluster_state().unwrap();
    assert_eq!(state.response_cluster_name, "fixture-acceptance-cluster");
    assert_eq!(
        state.header.state_uuid,
        "fixture-acceptance-single-node-full-state"
    );
    assert_eq!(state.header.version, 50);

    assert_eq!(
        state.discovery_nodes.cluster_manager_node_id.as_deref(),
        Some("fixture-acceptance-node-id")
    );
    assert_eq!(state.discovery_nodes.nodes.len(), 1);
    assert_eq!(
        state.discovery_nodes.nodes[0].name,
        "fixture-acceptance-node"
    );
    assert_eq!(
        state.discovery_nodes.nodes[0].id,
        "fixture-acceptance-node-id"
    );
    assert_eq!(state.discovery_nodes.nodes[0].address.port, 9300);

    assert_eq!(state.metadata.index_metadata.len(), 1);
    let index = &state.metadata.index_metadata[0];
    assert_eq!(index.name, "fixture-acceptance-index");
    assert_eq!(
        index.index_uuid.as_deref(),
        Some("fixture-acceptance-index-uuid")
    );
    assert_eq!(index.number_of_shards, Some(1));
    assert_eq!(index.number_of_replicas, Some(0));
    assert_eq!(index.mapping_count, 1);
    assert_eq!(index.alias_count, 1);
    assert_eq!(index.aliases[0].alias, "fixture-acceptance-alias");
    assert_eq!(state.metadata.templates.len(), 1);
    assert_eq!(
        state.metadata.templates[0].name,
        "fixture-acceptance-template"
    );

    let customs = &state.metadata.customs;
    assert_eq!(customs.declared_count, 6);
    assert_eq!(customs.ingest_pipelines.len(), 1);
    assert_eq!(
        customs.ingest_pipelines[0].id,
        "fixture-acceptance-pipeline"
    );
    assert_eq!(customs.stored_scripts.len(), 1);
    assert_eq!(customs.stored_scripts[0].id, "fixture-acceptance-script");
    assert_eq!(customs.component_templates.len(), 1);
    assert_eq!(
        customs.component_templates[0].name,
        "fixture-acceptance-component"
    );
    assert_eq!(customs.composable_index_templates.len(), 1);
    assert_eq!(
        customs.composable_index_templates[0].name,
        "fixture-acceptance-composable"
    );
    assert_eq!(customs.repositories.len(), 1);
    assert_eq!(
        customs.repositories[0].name,
        "fixture-acceptance-repository"
    );

    assert_eq!(state.routing_table.indices.len(), 1);
    let routing_index = &state.routing_table.indices[0];
    assert_eq!(routing_index.index_name, "fixture-acceptance-index");
    assert_eq!(routing_index.index_uuid, "fixture-acceptance-index-uuid");
    assert_eq!(routing_index.shards.len(), 1);
    assert_eq!(routing_index.shards[0].shard_id, 0);
    assert_eq!(routing_index.shards[0].shard_routings.len(), 1);
    let shard = &routing_index.shards[0].shard_routings[0];
    assert_eq!(
        shard.current_node_id.as_deref(),
        Some("fixture-acceptance-node-id")
    );
    assert!(shard.primary);
    assert_eq!(shard.state, ShardRoutingState::Started);

    assert!(state.cluster_blocks.global_blocks.is_empty());
    assert_eq!(state.cluster_blocks.index_blocks.len(), 1);
    assert_eq!(
        state.cluster_blocks.index_blocks[0].index_name,
        "fixture-acceptance-index"
    );
    assert_eq!(state.cluster_blocks.index_blocks[0].blocks.len(), 1);
    let block = &state.cluster_blocks.index_blocks[0].blocks[0];
    assert_eq!(block.id, 44);
    assert_eq!(
        block.uuid.as_deref(),
        Some("fixture-acceptance-index-block-uuid")
    );
    assert_eq!(
        block.levels,
        vec![ClusterBlockLevel::Read, ClusterBlockLevel::MetadataRead]
    );
    assert_eq!(block.status, "FORBIDDEN");

    assert_eq!(state.customs.declared_count, 1);
    assert_eq!(state.customs.names, vec!["repository_cleanup"]);
    assert!(state.customs.repository_cleanup.is_some());
    assert!(!state.wait_for_timed_out);
}

#[test]
fn java_cluster_state_publication_empty_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_empty")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(response.header.cluster_name, "fixture-cluster");
    assert_eq!(response.header.from_uuid, "fixture-diff-from");
    assert_eq!(response.header.to_uuid, "fixture-diff-to");
    assert_eq!(response.header.to_version, 2);
    assert_eq!(response.routing_indices.delete_count, 0);
    assert!(!response.nodes_complete_diff);
    assert_eq!(response.metadata_indices.delete_count, 0);
    assert_eq!(response.metadata_templates.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 0);
    assert!(!response.blocks_complete_diff);
    assert_eq!(response.customs.delete_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_empty_diff_applies_to_post_state() {
    let fixtures = fixtures();
    let before = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_publication_empty_before_state")
            .unwrap()
            .clone(),
    ))
    .unwrap()
    .into_cluster_state()
    .unwrap();
    let after = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_publication_empty_after_state")
            .unwrap()
            .clone(),
    ))
    .unwrap()
    .into_cluster_state()
    .unwrap();
    let diff = read_publication_cluster_state_diff(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_empty")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    let applied = diff.apply_to(&before).unwrap();

    assert_eq!(applied, after);
}

#[test]
fn java_cluster_state_publication_delete_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_delete_custom")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(response.header.from_uuid, "fixture-diff-custom-from");
    assert_eq!(response.header.to_uuid, "fixture-diff-custom-to");
    assert_eq!(response.customs.delete_count, 1);
    assert_eq!(response.customs.deleted_keys, vec!["snapshots"]);
    assert_eq!(response.customs.diff_count, 0);
    assert_eq!(response.customs.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_snapshots_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_custom")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(response.header.from_uuid, "fixture-diff-upsert-custom-from");
    assert_eq!(response.header.to_uuid, "fixture-diff-upsert-custom-to");
    assert_eq!(response.customs.delete_count, 0);
    assert_eq!(response.customs.diff_count, 0);
    assert_eq!(response.customs.upsert_count, 1);
    assert_eq!(response.customs.upsert_keys, vec!["snapshots"]);
    assert_eq!(response.customs.snapshots_upserts.len(), 1);
    assert_eq!(response.customs.snapshots_upserts[0].entry_count, 0);
    assert!(response.customs.snapshots_upserts[0].entries.is_empty());
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_snapshots_custom_entry_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_custom_snapshots_entry")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-custom-snapshots-entry-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-custom-snapshots-entry-to"
    );
    assert_eq!(response.customs.upsert_count, 1);
    assert_eq!(response.customs.upsert_keys, vec!["snapshots"]);
    assert_eq!(response.customs.snapshots_upserts.len(), 1);
    let snapshots = &response.customs.snapshots_upserts[0];
    assert_eq!(snapshots.entry_count, 1);
    let entry = &snapshots.entries[0];
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshot_name, "fixture-snapshot-in-progress");
    assert_eq!(entry.snapshot_uuid, "fixture-snapshot-in-progress-uuid");
    assert!(entry.include_global_state);
    assert!(!entry.partial);
    assert_eq!(entry.state_id, 2);
    assert_eq!(entry.indices_count, 1);
    assert_eq!(entry.indices[0].name, "fixture-index");
    assert_eq!(entry.indices[0].id, "fixture-snapshot-index-id");
    assert_eq!(entry.start_time, 123456789);
    assert_eq!(entry.shard_status_count, 0);
    assert_eq!(entry.repository_state_id, 44);
    assert_eq!(entry.failure, None);
    assert_eq!(entry.user_metadata_count, 0);
    assert_eq!(entry.data_streams, vec!["fixture-data-stream"]);
    assert_eq!(entry.source, None);
    assert_eq!(entry.clone_count, 0);
    assert_eq!(entry.remote_store_index_shallow_copy, Some(false));
    assert_eq!(entry.remote_store_index_shallow_copy_v2, Some(false));
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_snapshots_custom_shard_status_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_custom_snapshots_shard_status")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-custom-snapshots-shard-status-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-custom-snapshots-shard-status-to"
    );
    assert_eq!(response.customs.diff_count, 1);
    assert_eq!(response.customs.diff_keys, vec!["snapshots"]);
    assert_eq!(response.customs.snapshots_diffs.len(), 1);
    let diff = &response.customs.snapshots_diffs[0];
    assert!(diff.replacement_present);
    let replacement = diff.replacement.as_ref().unwrap();
    assert_eq!(replacement.entry_count, 1);
    let entry = &replacement.entries[0];
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshot_name, "fixture-snapshot-shard-in-progress");
    assert_eq!(
        entry.snapshot_uuid,
        "fixture-snapshot-shard-in-progress-uuid"
    );
    assert!(entry.include_global_state);
    assert!(!entry.partial);
    assert_eq!(entry.state_id, 1);
    assert_eq!(entry.indices_count, 1);
    assert_eq!(entry.indices[0].name, "fixture-snapshot-shard-index");
    assert_eq!(entry.indices[0].id, "fixture-snapshot-shard-index-id");
    assert_eq!(entry.start_time, 223456789);
    assert_eq!(entry.shard_status_count, 1);
    let shard = &entry.shard_statuses[0];
    assert_eq!(shard.index_name, "fixture-snapshot-shard-index");
    assert_eq!(shard.index_uuid, "fixture-snapshot-shard-index-uuid");
    assert_eq!(shard.shard_id, 0);
    assert_eq!(shard.node_id.as_deref(), Some("fixture-snapshot-node-id"));
    assert_eq!(shard.state_id, 0);
    assert_eq!(
        shard.generation.as_deref(),
        Some("fixture-snapshot-generation")
    );
    assert_eq!(shard.reason, None);
    assert_eq!(entry.repository_state_id, 45);
    assert_eq!(entry.failure, None);
    assert_eq!(entry.user_metadata_count, 0);
    assert_eq!(
        entry.data_streams,
        vec!["fixture-snapshot-shard-data-stream"]
    );
    assert_eq!(entry.source, None);
    assert_eq!(entry.clone_count, 0);
    assert_eq!(entry.remote_store_index_shallow_copy, Some(false));
    assert_eq!(entry.remote_store_index_shallow_copy_v2, Some(false));
    assert_eq!(response.customs.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_restore_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_custom_restore")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-custom-restore-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-custom-restore-to"
    );
    assert_eq!(response.customs.upsert_count, 1);
    assert_eq!(response.customs.upsert_keys, vec!["restore"]);
    assert_eq!(response.customs.restore_upserts.len(), 1);
    let restore = &response.customs.restore_upserts[0];
    assert_eq!(restore.entry_count, 1);
    let entry = &restore.entries[0];
    assert_eq!(entry.uuid, "fixture-restore-entry-uuid");
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshot_name, "fixture-restore-snapshot");
    assert_eq!(entry.snapshot_uuid, "fixture-restore-snapshot-uuid");
    assert_eq!(entry.state_id, 1);
    assert_eq!(entry.indices_count, 1);
    assert_eq!(entry.indices, vec!["fixture-index"]);
    assert_eq!(entry.shard_status_count, 0);
    assert!(entry.shard_statuses.is_empty());
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_restore_custom_shard_status_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_custom_restore_shard_status")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-custom-restore-shard-status-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-custom-restore-shard-status-to"
    );
    assert_eq!(response.customs.upsert_count, 1);
    assert_eq!(response.customs.upsert_keys, vec!["restore"]);
    assert_eq!(response.customs.restore_upserts.len(), 1);
    let restore = &response.customs.restore_upserts[0];
    assert_eq!(restore.entry_count, 1);
    let entry = &restore.entries[0];
    assert_eq!(entry.uuid, "fixture-restore-shard-entry-uuid");
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshot_name, "fixture-restore-shard-snapshot");
    assert_eq!(entry.snapshot_uuid, "fixture-restore-shard-snapshot-uuid");
    assert_eq!(entry.indices, vec!["fixture-restore-shard-index"]);
    assert_eq!(entry.shard_status_count, 1);
    let shard = &entry.shard_statuses[0];
    assert_eq!(shard.index_name, "fixture-restore-shard-index");
    assert_eq!(shard.index_uuid, "fixture-restore-shard-index-uuid");
    assert_eq!(shard.shard_id, 0);
    assert_eq!(shard.node_id.as_deref(), Some("fixture-restore-node-id"));
    assert_eq!(shard.state_id, 1);
    assert_eq!(shard.reason.as_deref(), Some("fixture-restore-reason"));
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_restore_custom_shard_status_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_custom_restore_shard_status")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-custom-restore-shard-status-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-custom-restore-shard-status-to"
    );
    assert_eq!(response.customs.diff_count, 1);
    assert_eq!(response.customs.diff_keys, vec!["restore"]);
    assert_eq!(response.customs.restore_diffs.len(), 1);
    let diff = &response.customs.restore_diffs[0];
    assert!(diff.replacement_present);
    let replacement = diff.replacement.as_ref().unwrap();
    assert_eq!(replacement.entry_count, 1);
    let entry = &replacement.entries[0];
    assert_eq!(entry.uuid, "fixture-restore-shard-entry-uuid");
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshot_name, "fixture-restore-shard-snapshot");
    assert_eq!(entry.snapshot_uuid, "fixture-restore-shard-snapshot-uuid");
    assert_eq!(entry.indices, vec!["fixture-restore-shard-index"]);
    assert_eq!(entry.shard_status_count, 1);
    let shard = &entry.shard_statuses[0];
    assert_eq!(shard.index_name, "fixture-restore-shard-index");
    assert_eq!(shard.index_uuid, "fixture-restore-shard-index-uuid");
    assert_eq!(shard.shard_id, 0);
    assert_eq!(shard.node_id.as_deref(), Some("fixture-restore-node-id"));
    assert_eq!(shard.state_id, 1);
    assert_eq!(shard.reason.as_deref(), Some("fixture-restore-reason"));
    assert_eq!(response.customs.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_snapshot_deletions_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_custom_snapshot_deletions")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-custom-snapshot-deletions-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-custom-snapshot-deletions-to"
    );
    assert_eq!(response.customs.upsert_count, 1);
    assert_eq!(response.customs.upsert_keys, vec!["snapshot_deletions"]);
    assert_eq!(response.customs.snapshot_deletions_upserts.len(), 1);
    let deletions = &response.customs.snapshot_deletions_upserts[0];
    assert_eq!(deletions.entry_count, 1);
    let entry = &deletions.entries[0];
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshots_count, 1);
    assert_eq!(entry.snapshots[0].name, "fixture-delete-snapshot");
    assert_eq!(entry.snapshots[0].uuid, "fixture-delete-snapshot-uuid");
    assert_eq!(entry.start_time, 123456789);
    assert_eq!(entry.repository_state_id, 43);
    assert_eq!(entry.state_id, 1);
    assert!(!entry.uuid.is_empty());
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_snapshot_deletions_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_custom_snapshot_deletions")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-custom-snapshot-deletions-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-custom-snapshot-deletions-to"
    );
    assert_eq!(response.customs.diff_count, 1);
    assert_eq!(response.customs.diff_keys, vec!["snapshot_deletions"]);
    assert_eq!(response.customs.snapshot_deletions_diffs.len(), 1);
    let diff = &response.customs.snapshot_deletions_diffs[0];
    assert!(diff.replacement_present);
    let replacement = diff.replacement.as_ref().unwrap();
    assert_eq!(replacement.entry_count, 1);
    let entry = &replacement.entries[0];
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshots_count, 2);
    assert_eq!(entry.snapshots[0].name, "fixture-delete-snapshot");
    assert_eq!(entry.snapshots[0].uuid, "fixture-delete-snapshot-uuid");
    assert_eq!(entry.snapshots[1].name, "fixture-delete-snapshot-after");
    assert_eq!(
        entry.snapshots[1].uuid,
        "fixture-delete-snapshot-after-uuid"
    );
    assert_eq!(entry.start_time, 123456789);
    assert_eq!(entry.repository_state_id, 44);
    assert_eq!(entry.state_id, 1);
    assert!(!entry.uuid.is_empty());
    assert_eq!(response.customs.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_repository_cleanup_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_custom_repository_cleanup")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-custom-repository-cleanup-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-custom-repository-cleanup-to"
    );
    assert_eq!(response.customs.upsert_count, 1);
    assert_eq!(response.customs.upsert_keys, vec!["repository_cleanup"]);
    assert_eq!(response.customs.repository_cleanup_upserts.len(), 1);
    let cleanup = &response.customs.repository_cleanup_upserts[0];
    assert_eq!(cleanup.entry_count, 1);
    assert_eq!(cleanup.entries[0].repository, "fixture-repository");
    assert_eq!(cleanup.entries[0].repository_state_id, 42);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_repository_cleanup_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_custom_repository_cleanup")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-custom-repository-cleanup-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-custom-repository-cleanup-to"
    );
    assert_eq!(response.customs.diff_count, 1);
    assert_eq!(response.customs.diff_keys, vec!["repository_cleanup"]);
    assert_eq!(response.customs.repository_cleanup_diffs.len(), 1);
    let diff = &response.customs.repository_cleanup_diffs[0];
    assert!(diff.replacement_present);
    let replacement = diff.replacement.as_ref().unwrap();
    assert_eq!(replacement.entry_count, 1);
    assert_eq!(replacement.entries[0].repository, "fixture-repository");
    assert_eq!(replacement.entries[0].repository_state_id, 43);
    assert_eq!(response.customs.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_delete_routing_index_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_delete_routing_index")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(response.header.from_uuid, "fixture-diff-routing-from");
    assert_eq!(response.header.to_uuid, "fixture-diff-routing-to");
    assert_eq!(response.routing_table_version, 2);
    assert_eq!(response.routing_indices.delete_count, 1);
    assert_eq!(
        response.routing_indices.deleted_keys,
        vec!["fixture-deleted-routing-index"]
    );
    assert_eq!(response.routing_indices.diff_count, 0);
    assert_eq!(response.routing_indices.upsert_count, 0);
    assert_eq!(response.metadata_indices.delete_count, 0);
    assert_eq!(response.customs.delete_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_routing_index_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_routing_index")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-routing-from"
    );
    assert_eq!(response.header.to_uuid, "fixture-diff-upsert-routing-to");
    assert_eq!(response.routing_table_version, 2);
    assert_eq!(response.routing_indices.delete_count, 0);
    assert_eq!(response.routing_indices.diff_count, 0);
    assert_eq!(response.routing_indices.upsert_count, 1);
    assert_eq!(
        response.routing_indices.upsert_keys,
        vec!["fixture-upsert-routing-index"]
    );
    let index = &response.routing_indices.index_routing_upserts[0];
    assert_eq!(index.index_name, "fixture-upsert-routing-index");
    assert_eq!(index.index_uuid, "fixture-upsert-routing-index-uuid");
    assert_eq!(index.shard_table_count, 0);
    assert_eq!(response.metadata_indices.delete_count, 0);
    assert_eq!(response.customs.delete_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_routing_diff_applies_to_post_state() {
    let fixtures = fixtures();
    let before = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_publication_upsert_routing_before_state")
            .unwrap()
            .clone(),
    ))
    .unwrap()
    .into_cluster_state()
    .unwrap();
    let after = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_publication_upsert_routing_after_state")
            .unwrap()
            .clone(),
    ))
    .unwrap()
    .into_cluster_state()
    .unwrap();
    let diff = read_publication_cluster_state_diff(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_routing_index")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    let applied = diff.apply_to(&before).unwrap();

    assert_eq!(applied, after);
    assert_eq!(applied.routing_table.indices.len(), 1);
    assert_eq!(
        applied.routing_table.indices[0].index_name,
        "fixture-upsert-routing-index"
    );
}

#[test]
fn java_cluster_state_publication_upsert_metadata_template_diff_applies_to_post_state() {
    let applied = assert_publication_diff_applies_to_post_state(
        "cluster_state_publication_upsert_metadata_template_before_state",
        "cluster_state_publication_diff_upsert_metadata_template",
        "cluster_state_publication_upsert_metadata_template_after_state",
    );

    assert_eq!(applied.metadata.templates.len(), 1);
    assert_eq!(
        applied.metadata.templates[0].name,
        "fixture-upsert-template"
    );
}

#[test]
fn java_cluster_state_publication_upsert_custom_diff_applies_to_post_state() {
    let applied = assert_publication_diff_applies_to_post_state(
        "cluster_state_publication_upsert_custom_before_state",
        "cluster_state_publication_diff_upsert_custom",
        "cluster_state_publication_upsert_custom_after_state",
    );

    assert_eq!(applied.customs.names, vec!["snapshots"]);
    assert!(applied.customs.snapshots.is_some());
}

#[test]
fn java_cluster_state_publication_named_routing_index_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_routing_index")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(response.header.from_uuid, "fixture-diff-named-routing-from");
    assert_eq!(response.header.to_uuid, "fixture-diff-named-routing-to");
    assert_eq!(response.routing_table_version, 2);
    assert_eq!(response.routing_indices.delete_count, 0);
    assert_eq!(response.routing_indices.diff_count, 1);
    assert_eq!(
        response.routing_indices.diff_keys,
        vec!["fixture-named-routing-index"]
    );
    assert_eq!(response.routing_indices.index_routing_diffs.len(), 1);
    let diff = &response.routing_indices.index_routing_diffs[0];
    assert!(diff.replacement_present);
    let replacement = diff.replacement.as_ref().unwrap();
    assert_eq!(replacement.index_name, "fixture-named-routing-index");
    assert_eq!(replacement.index_uuid, "fixture-named-routing-index-uuid");
    assert_eq!(replacement.shard_table_count, 1);
    assert_eq!(replacement.shards[0].shard_id, 0);
    assert_eq!(replacement.shards[0].shard_routing_count, 1);
    assert_eq!(
        replacement.shards[0].shard_routings[0].state,
        ShardRoutingStatePrefix::Unassigned
    );
    assert_eq!(response.routing_indices.upsert_count, 0);
    assert_eq!(response.metadata_indices.delete_count, 0);
    assert_eq!(response.customs.delete_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_delete_metadata_index_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_delete_metadata_index")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(response.header.from_uuid, "fixture-diff-metadata-from");
    assert_eq!(response.header.to_uuid, "fixture-diff-metadata-to");
    assert_eq!(response.routing_indices.delete_count, 0);
    assert_eq!(response.metadata_indices.delete_count, 1);
    assert_eq!(
        response.metadata_indices.deleted_keys,
        vec!["fixture-deleted-metadata-index"]
    );
    assert_eq!(response.metadata_indices.diff_count, 0);
    assert_eq!(response.metadata_indices.upsert_count, 0);
    assert_eq!(response.customs.delete_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_delete_metadata_template_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_delete_metadata_template")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(response.header.from_uuid, "fixture-diff-template-from");
    assert_eq!(response.header.to_uuid, "fixture-diff-template-to");
    assert_eq!(response.metadata_indices.delete_count, 0);
    assert_eq!(response.metadata_templates.delete_count, 1);
    assert_eq!(
        response.metadata_templates.deleted_keys,
        vec!["fixture-deleted-template"]
    );
    assert_eq!(response.metadata_templates.diff_count, 0);
    assert_eq!(response.metadata_templates.upsert_count, 0);
    assert_eq!(response.customs.delete_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_metadata_template_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_template")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-template-from"
    );
    assert_eq!(response.header.to_uuid, "fixture-diff-upsert-template-to");
    assert_eq!(response.metadata_templates.delete_count, 0);
    assert_eq!(response.metadata_templates.diff_count, 0);
    assert_eq!(response.metadata_templates.upsert_count, 1);
    assert_eq!(
        response.metadata_templates.upsert_keys,
        vec!["fixture-upsert-template"]
    );
    let template = &response.metadata_templates.index_template_upserts[0];
    assert_eq!(template.name, "fixture-upsert-template");
    assert_eq!(template.patterns, vec!["fixture-upsert-*"]);
    assert_eq!(template.settings_count, 1);
    assert_eq!(template.mappings_count, 0);
    assert_eq!(template.aliases_count, 0);
    assert_eq!(template.version, Some(10));
    assert_eq!(response.customs.delete_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_metadata_template_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_template")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-template-from"
    );
    assert_eq!(response.header.to_uuid, "fixture-diff-named-template-to");
    assert_eq!(response.metadata_templates.delete_count, 0);
    assert_eq!(response.metadata_templates.diff_count, 1);
    assert_eq!(
        response.metadata_templates.diff_keys,
        vec!["fixture-diff-template"]
    );
    assert_eq!(response.metadata_templates.index_template_diffs.len(), 1);
    let template_diff = &response.metadata_templates.index_template_diffs[0];
    assert!(template_diff.replacement_present);
    let template = template_diff.replacement.as_ref().unwrap();
    assert_eq!(template.name, "fixture-diff-template");
    assert_eq!(template.order, 7);
    assert_eq!(template.patterns, vec!["fixture-diff-after-*"]);
    assert_eq!(template.settings_count, 1);
    assert_eq!(template.settings[0].key, "index.number_of_shards");
    assert_eq!(template.settings[0].value.as_deref(), Some("2"));
    assert_eq!(template.mappings_count, 0);
    assert_eq!(template.aliases_count, 0);
    assert_eq!(template.version, Some(11));
    assert_eq!(response.metadata_templates.upsert_count, 0);
    assert_eq!(response.customs.delete_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_metadata_template_mapping_alias_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_template_mapping_alias")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-template-mapping-alias-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-template-mapping-alias-to"
    );
    assert_eq!(response.metadata_templates.delete_count, 0);
    assert_eq!(response.metadata_templates.diff_count, 1);
    assert_eq!(
        response.metadata_templates.diff_keys,
        vec!["fixture-diff-template-mapping-alias"]
    );
    assert_eq!(response.metadata_templates.index_template_diffs.len(), 1);
    let template_diff = &response.metadata_templates.index_template_diffs[0];
    assert!(template_diff.replacement_present);
    let template = template_diff.replacement.as_ref().unwrap();
    assert_eq!(template.name, "fixture-diff-template-mapping-alias");
    assert_eq!(template.order, 9);
    assert_eq!(template.patterns, vec!["fixture-diff-map-after-*"]);
    assert_eq!(template.settings_count, 1);
    assert_eq!(template.settings[0].key, "index.number_of_shards");
    assert_eq!(template.settings[0].value.as_deref(), Some("2"));
    assert_eq!(template.mappings_count, 1);
    assert_eq!(template.mappings[0].name, "_doc");
    assert!(template.mappings[0].compressed_bytes_len > 0);
    assert_eq!(template.aliases_count, 1);
    assert_eq!(template.aliases[0].alias, "fixture-diff-template-alias");
    assert_eq!(template.version, Some(13));
    assert_eq!(response.metadata_templates.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_delete_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_delete_metadata_custom")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-metadata-custom-from"
    );
    assert_eq!(response.header.to_uuid, "fixture-diff-metadata-custom-to");
    assert_eq!(response.metadata_indices.delete_count, 0);
    assert_eq!(response.metadata_templates.delete_count, 0);
    assert_eq!(response.metadata_customs.delete_count, 1);
    assert_eq!(response.metadata_customs.deleted_keys, vec!["repositories"]);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 0);
    assert_eq!(response.customs.delete_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_repositories_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(response.metadata_customs.upsert_keys, vec!["repositories"]);
    assert_eq!(
        response.metadata_customs.repository_metadata_upserts.len(),
        1
    );
    let repository = &response.metadata_customs.repository_metadata_upserts[0];
    assert_eq!(repository.name, "fixture-upsert-repo");
    assert_eq!(repository.repository_type, "fs");
    assert_eq!(repository.settings_count, 1);
    assert!(!repository.crypto_metadata_present);
    assert_eq!(response.customs.delete_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_repositories_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_custom_repositories")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-custom-repositories-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-custom-repositories-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 1);
    assert_eq!(response.metadata_customs.diff_keys, vec!["repositories"]);
    assert_eq!(response.metadata_customs.upsert_count, 0);
    assert_eq!(response.metadata_customs.repository_metadata_diffs.len(), 1);
    let repositories_diff = &response.metadata_customs.repository_metadata_diffs[0];
    assert!(repositories_diff.replacement_present);
    assert_eq!(repositories_diff.replacement_count, 2);
    let repository_a = &repositories_diff.replacement[0];
    assert_eq!(repository_a.name, "fixture-diff-repo-a");
    assert_eq!(repository_a.repository_type, "fs");
    assert_eq!(repository_a.settings_count, 1);
    assert_eq!(repository_a.settings[0].key, "location");
    assert_eq!(
        repository_a.settings[0].value.as_deref(),
        Some("/tmp/fixture-diff-repo-after")
    );
    assert!(!repository_a.crypto_metadata_present);
    let repository_b = &repositories_diff.replacement[1];
    assert_eq!(repository_b.name, "fixture-diff-repo-b");
    assert_eq!(repository_b.repository_type, "url");
    assert_eq!(repository_b.settings_count, 1);
    assert_eq!(repository_b.settings[0].key, "url");
    assert_eq!(
        repository_b.settings[0].value.as_deref(),
        Some("file:/tmp/fixture-diff-repo-b")
    );
    assert!(!repository_b.crypto_metadata_present);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_component_template_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom_component_template")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-component-template-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-component-template-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(
        response.metadata_customs.upsert_keys,
        vec!["component_template"]
    );
    assert!(response
        .metadata_customs
        .repository_metadata_upserts
        .is_empty());
    assert_eq!(
        response.metadata_customs.component_template_upserts.len(),
        1
    );
    let template = &response.metadata_customs.component_template_upserts[0];
    assert_eq!(template.name, "fixture-upsert-component-template");
    assert_eq!(template.settings_count, 1);
    assert_eq!(template.settings[0].key, "index.number_of_shards");
    assert_eq!(template.settings[0].value.as_deref(), Some("1"));
    assert!(!template.mappings_present);
    assert_eq!(template.aliases_count, 0);
    assert_eq!(template.version, Some(9));
    assert!(!template.metadata_present);
    assert_eq!(template.metadata_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_index_template_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom_index_template")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-index-template-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-index-template-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(
        response.metadata_customs.upsert_keys,
        vec!["index_template"]
    );
    assert_eq!(
        response
            .metadata_customs
            .composable_index_template_upserts
            .len(),
        1
    );
    let template = &response.metadata_customs.composable_index_template_upserts[0];
    assert_eq!(template.name, "fixture-upsert-composable-template");
    assert_eq!(
        template.index_patterns,
        vec![
            "fixture-upsert-compose-*".to_string(),
            "fixture-upsert-compose-alt-*".to_string()
        ]
    );
    assert!(template.template_present);
    assert_eq!(template.template_settings_count, 1);
    assert_eq!(template.template_settings[0].key, "index.number_of_shards");
    assert_eq!(template.template_settings[0].value.as_deref(), Some("1"));
    assert!(!template.template_mappings_present);
    assert_eq!(template.template_aliases_count, 0);
    assert_eq!(template.component_templates_count, 1);
    assert_eq!(
        template.component_templates,
        vec!["fixture-upsert-component-template".to_string()]
    );
    assert_eq!(template.priority, Some(31));
    assert_eq!(template.version, Some(32));
    assert_eq!(template.metadata_count, 1);
    assert_eq!(template.metadata[0].key, "fixture-upsert-meta");
    assert_eq!(
        template.metadata[0].value.as_deref(),
        Some("fixture-upsert-value")
    );
    assert!(!template.data_stream_template_present);
    assert!(!template.context_present);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_data_stream_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom_data_stream")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-data-stream-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-data-stream-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(response.metadata_customs.upsert_keys, vec!["data_stream"]);
    assert_eq!(response.metadata_customs.data_stream_upserts.len(), 1);
    let data_stream = &response.metadata_customs.data_stream_upserts[0];
    assert_eq!(data_stream.name, "fixture-upsert-data-stream");
    assert_eq!(data_stream.timestamp_field, "event_time");
    assert_eq!(data_stream.backing_indices_count, 1);
    assert_eq!(
        data_stream.backing_indices[0].name,
        ".ds-fixture-upsert-data-stream-000001"
    );
    assert_eq!(
        data_stream.backing_indices[0].uuid,
        "fixture-upsert-backing-index-uuid"
    );
    assert_eq!(data_stream.generation, 3);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_ingest_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom_ingest")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-ingest-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-ingest-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(response.metadata_customs.upsert_keys, vec!["ingest"]);
    assert_eq!(response.metadata_customs.ingest_upserts.len(), 1);
    let pipeline = &response.metadata_customs.ingest_upserts[0];
    assert_eq!(pipeline.id, "fixture-upsert-pipeline");
    assert!(pipeline.config_len > 0);
    assert_eq!(pipeline.media_type, "application/json; charset=UTF-8");
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_search_pipeline_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom_search_pipeline")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-search-pipeline-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-search-pipeline-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(
        response.metadata_customs.upsert_keys,
        vec!["search_pipeline"]
    );
    assert_eq!(response.metadata_customs.search_pipeline_upserts.len(), 1);
    let pipeline = &response.metadata_customs.search_pipeline_upserts[0];
    assert_eq!(pipeline.id, "fixture-upsert-search-pipeline");
    assert!(pipeline.config_len > 0);
    assert_eq!(pipeline.media_type, "application/json; charset=UTF-8");
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_stored_scripts_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom_stored_scripts")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-stored-scripts-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-stored-scripts-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(
        response.metadata_customs.upsert_keys,
        vec!["stored_scripts"]
    );
    assert_eq!(response.metadata_customs.stored_script_upserts.len(), 1);
    let script = &response.metadata_customs.stored_script_upserts[0];
    assert_eq!(script.id, "fixture-upsert-script");
    assert_eq!(script.lang, "painless");
    assert!(script.source_len > 0);
    assert_eq!(script.options_count, 1);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_index_graveyard_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom_index_graveyard")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-index-graveyard-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-index-graveyard-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(
        response.metadata_customs.upsert_keys,
        vec!["index-graveyard"]
    );
    assert_eq!(
        response
            .metadata_customs
            .index_graveyard_tombstone_upserts
            .len(),
        1
    );
    let tombstone = &response.metadata_customs.index_graveyard_tombstone_upserts[0];
    assert_eq!(tombstone.index_name, "fixture-upsert-deleted-index");
    assert_eq!(tombstone.index_uuid, "fixture-upsert-deleted-index-uuid");
    assert!(tombstone.delete_date_in_millis > 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_persistent_tasks_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom_persistent_tasks")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-persistent-tasks-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-persistent-tasks-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(
        response.metadata_customs.upsert_keys,
        vec!["persistent_tasks"]
    );
    assert_eq!(response.metadata_customs.persistent_task_upserts.len(), 1);
    let task = &response.metadata_customs.persistent_task_upserts[0];
    assert_eq!(task.map_key, "fixture-upsert-task");
    assert_eq!(task.id, "fixture-upsert-task");
    assert_eq!(task.allocation_id, 1);
    assert_eq!(task.task_name, "fixture-persistent-task");
    assert_eq!(task.params_name, "fixture-persistent-task");
    assert_eq!(
        task.fixture_params_marker.as_deref(),
        Some("fixture-persistent-payload")
    );
    assert_eq!(task.fixture_params_generation, Some(7));
    assert_eq!(task.state_name.as_deref(), Some("fixture-persistent-task"));
    assert_eq!(
        task.fixture_state_marker.as_deref(),
        Some("fixture-persistent-state")
    );
    assert_eq!(task.fixture_state_generation, Some(11));
    assert_eq!(
        task.executor_node.as_deref(),
        Some("fixture-upsert-node-id")
    );
    assert_eq!(task.assignment_explanation, "assigned for upsert fixture");
    assert_eq!(task.allocation_id_on_last_status_update, Some(1));
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_decommission_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom_decommission")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-decommission-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-decommission-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(
        response.metadata_customs.upsert_keys,
        vec!["decommissionedAttribute"]
    );
    assert_eq!(
        response
            .metadata_customs
            .decommission_attribute_upserts
            .len(),
        1
    );
    let decommission = &response.metadata_customs.decommission_attribute_upserts[0];
    assert_eq!(decommission.attribute_name, "zone");
    assert_eq!(decommission.attribute_value, "zone-upsert");
    assert_eq!(decommission.status, "draining");
    assert_eq!(
        decommission.request_id,
        "fixture-upsert-decommission-request"
    );
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_decommission_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_custom_decommission")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-custom-decommission-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-custom-decommission-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 1);
    assert_eq!(
        response.metadata_customs.diff_keys,
        vec!["decommissionedAttribute"]
    );
    assert_eq!(response.metadata_customs.upsert_count, 0);
    assert_eq!(
        response.metadata_customs.decommission_attribute_diffs.len(),
        1
    );
    let decommission_diff = &response.metadata_customs.decommission_attribute_diffs[0];
    assert!(decommission_diff.replacement_present);
    let decommission = decommission_diff.replacement.as_ref().unwrap();
    assert_eq!(decommission.attribute_name, "zone");
    assert_eq!(decommission.attribute_value, "zone-diff");
    assert_eq!(decommission.status, "draining");
    assert_eq!(
        decommission.request_id,
        "fixture-diff-decommission-request-after"
    );
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_weighted_routing_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom_weighted_routing")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-weighted-routing-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-weighted-routing-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(
        response.metadata_customs.upsert_keys,
        vec!["weighted_shard_routing"]
    );
    assert_eq!(response.metadata_customs.weighted_routing_upserts.len(), 1);
    let weighted_routing = &response.metadata_customs.weighted_routing_upserts[0];
    assert_eq!(weighted_routing.awareness_attribute, "zone");
    assert_eq!(weighted_routing.weights_count, 1);
    assert_eq!(weighted_routing.weights[0].key, "zone-upsert");
    assert_eq!(weighted_routing.weights[0].value.as_deref(), Some("0.5"));
    assert_eq!(weighted_routing.version, 33);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_weighted_routing_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_custom_weighted_routing")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-custom-weighted-routing-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-custom-weighted-routing-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 1);
    assert_eq!(
        response.metadata_customs.diff_keys,
        vec!["weighted_shard_routing"]
    );
    assert_eq!(response.metadata_customs.upsert_count, 0);
    assert_eq!(response.metadata_customs.weighted_routing_diffs.len(), 1);
    let weighted_routing_diff = &response.metadata_customs.weighted_routing_diffs[0];
    assert!(weighted_routing_diff.replacement_present);
    let weighted_routing = weighted_routing_diff.replacement.as_ref().unwrap();
    assert_eq!(weighted_routing.awareness_attribute, "zone");
    assert_eq!(weighted_routing.weights_count, 1);
    assert_eq!(weighted_routing.weights[0].key, "zone-after");
    assert_eq!(weighted_routing.weights[0].value.as_deref(), Some("0.75"));
    assert_eq!(weighted_routing.version, 45);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_view_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom_view")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-view-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-view-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(response.metadata_customs.upsert_keys, vec!["view"]);
    assert_eq!(response.metadata_customs.view_upserts.len(), 1);
    let view = &response.metadata_customs.view_upserts[0];
    assert_eq!(view.name, "fixture-upsert-view");
    assert_eq!(
        view.description.as_deref(),
        Some("fixture upsert view source")
    );
    assert_eq!(view.created_at, 789);
    assert_eq!(view.modified_at, 1011);
    assert_eq!(view.target_index_patterns_count, 1);
    assert_eq!(
        view.target_index_patterns,
        vec!["fixture-upsert-view-*".to_string()]
    );
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_workload_group_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_custom_workload_group")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-custom-workload-group-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-upsert-metadata-custom-workload-group-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 0);
    assert_eq!(response.metadata_customs.upsert_count, 1);
    assert_eq!(response.metadata_customs.upsert_keys, vec!["queryGroups"]);
    assert_eq!(response.metadata_customs.workload_group_upserts.len(), 1);
    let workload_group = &response.metadata_customs.workload_group_upserts[0];
    assert_eq!(workload_group.name, "fixture-upsert-workload");
    assert_eq!(workload_group.id, "fixture-upsert-workload-id");
    assert_eq!(workload_group.resource_limits_count, 2);
    assert_eq!(workload_group.resource_limits[0].key, "cpu");
    assert_eq!(
        workload_group.resource_limits[0].value.as_deref(),
        Some("0.6")
    );
    assert_eq!(workload_group.resource_limits[1].key, "memory");
    assert_eq!(
        workload_group.resource_limits[1].value.as_deref(),
        Some("0.4")
    );
    assert_eq!(workload_group.resiliency_mode.as_deref(), Some("monitor"));
    assert_eq!(workload_group.search_settings_count, 1);
    assert_eq!(workload_group.search_settings[0].key, "timeout");
    assert_eq!(
        workload_group.search_settings[0].value.as_deref(),
        Some("15s")
    );
    assert_eq!(workload_group.updated_at_millis, 567890);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_view_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_custom_view")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-custom-view-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-custom-view-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 1);
    assert_eq!(response.metadata_customs.diff_keys, vec!["view"]);
    assert_eq!(response.metadata_customs.upsert_count, 0);
    assert_eq!(response.metadata_customs.view_diffs.len(), 1);
    let view_custom_diff = &response.metadata_customs.view_diffs[0];
    assert_eq!(view_custom_diff.delete_count, 0);
    assert_eq!(view_custom_diff.diff_count, 1);
    assert_eq!(view_custom_diff.diff_keys, vec!["fixture-diff-view"]);
    assert_eq!(view_custom_diff.upsert_count, 0);
    assert_eq!(view_custom_diff.replacement_diffs.len(), 1);
    let view_diff = &view_custom_diff.replacement_diffs[0];
    assert!(view_diff.replacement_present);
    let view = view_diff.replacement.as_ref().unwrap();
    assert_eq!(view.name, "fixture-diff-view");
    assert_eq!(view.description.as_deref(), Some("fixture view after"));
    assert_eq!(view.created_at, 101);
    assert_eq!(view.modified_at, 201);
    assert_eq!(view.target_index_patterns_count, 1);
    assert_eq!(
        view.target_index_patterns,
        vec!["fixture-diff-view-after-*".to_string()]
    );
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_workload_group_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_custom_workload_group")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-custom-workload-group-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-custom-workload-group-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 1);
    assert_eq!(response.metadata_customs.diff_keys, vec!["queryGroups"]);
    assert_eq!(response.metadata_customs.upsert_count, 0);
    assert_eq!(response.metadata_customs.workload_group_diffs.len(), 1);
    let workload_custom_diff = &response.metadata_customs.workload_group_diffs[0];
    assert_eq!(workload_custom_diff.delete_count, 0);
    assert_eq!(workload_custom_diff.diff_count, 1);
    assert_eq!(
        workload_custom_diff.diff_keys,
        vec!["fixture-diff-workload-id"]
    );
    assert_eq!(workload_custom_diff.upsert_count, 0);
    assert_eq!(workload_custom_diff.replacement_diffs.len(), 1);
    let workload_diff = &workload_custom_diff.replacement_diffs[0];
    assert!(workload_diff.replacement_present);
    let workload_group = workload_diff.replacement.as_ref().unwrap();
    assert_eq!(workload_group.name, "fixture-diff-workload");
    assert_eq!(workload_group.id, "fixture-diff-workload-id");
    assert_eq!(workload_group.resource_limits_count, 2);
    assert_eq!(workload_group.resource_limits[0].key, "cpu");
    assert_eq!(
        workload_group.resource_limits[0].value.as_deref(),
        Some("0.7")
    );
    assert_eq!(workload_group.resource_limits[1].key, "memory");
    assert_eq!(
        workload_group.resource_limits[1].value.as_deref(),
        Some("0.2")
    );
    assert_eq!(workload_group.resiliency_mode.as_deref(), Some("soft"));
    assert_eq!(workload_group.search_settings_count, 1);
    assert_eq!(workload_group.search_settings[0].key, "timeout");
    assert_eq!(
        workload_group.search_settings[0].value.as_deref(),
        Some("25s")
    );
    assert_eq!(workload_group.updated_at_millis, 222222);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_data_stream_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_custom_data_stream")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-custom-data-stream-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-custom-data-stream-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 1);
    assert_eq!(response.metadata_customs.diff_keys, vec!["data_stream"]);
    assert_eq!(response.metadata_customs.upsert_count, 0);
    assert_eq!(response.metadata_customs.data_stream_diffs.len(), 1);
    let data_stream_custom_diff = &response.metadata_customs.data_stream_diffs[0];
    assert_eq!(data_stream_custom_diff.delete_count, 0);
    assert_eq!(data_stream_custom_diff.diff_count, 1);
    assert_eq!(
        data_stream_custom_diff.diff_keys,
        vec!["fixture-diff-data-stream"]
    );
    assert_eq!(data_stream_custom_diff.upsert_count, 0);
    assert_eq!(data_stream_custom_diff.replacement_diffs.len(), 1);
    let data_stream_diff = &data_stream_custom_diff.replacement_diffs[0];
    assert!(data_stream_diff.replacement_present);
    let data_stream = data_stream_diff.replacement.as_ref().unwrap();
    assert_eq!(data_stream.name, "fixture-diff-data-stream");
    assert_eq!(data_stream.timestamp_field, "event_time");
    assert_eq!(data_stream.backing_indices_count, 2);
    assert_eq!(
        data_stream.backing_indices[0].name,
        ".ds-fixture-diff-data-stream-000001"
    );
    assert_eq!(
        data_stream.backing_indices[1].name,
        ".ds-fixture-diff-data-stream-000002"
    );
    assert_eq!(
        data_stream.backing_indices[1].uuid,
        "fixture-diff-backing-after-uuid"
    );
    assert_eq!(data_stream.generation, 2);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_component_template_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_custom_component_template")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-custom-component-template-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-custom-component-template-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 1);
    assert_eq!(
        response.metadata_customs.diff_keys,
        vec!["component_template"]
    );
    assert_eq!(response.metadata_customs.upsert_count, 0);
    assert_eq!(response.metadata_customs.component_template_diffs.len(), 1);
    let component_custom_diff = &response.metadata_customs.component_template_diffs[0];
    assert_eq!(component_custom_diff.delete_count, 0);
    assert_eq!(component_custom_diff.diff_count, 1);
    assert_eq!(
        component_custom_diff.diff_keys,
        vec!["fixture-diff-component-template"]
    );
    assert_eq!(component_custom_diff.upsert_count, 0);
    assert_eq!(component_custom_diff.replacement_diffs.len(), 1);
    let component_diff = &component_custom_diff.replacement_diffs[0];
    assert!(component_diff.replacement_present);
    let template = component_diff.replacement.as_ref().unwrap();
    assert_eq!(template.name, "fixture-diff-component-template");
    assert_eq!(template.settings_count, 1);
    assert_eq!(template.settings[0].key, "index.number_of_shards");
    assert_eq!(template.settings[0].value.as_deref(), Some("2"));
    assert_eq!(template.version, Some(2));
    assert!(template.metadata_present);
    assert_eq!(template.metadata_count, 1);
    assert_eq!(template.metadata[0].key, "fixture-diff-meta");
    assert_eq!(template.metadata[0].value.as_deref(), Some("after"));
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_index_template_metadata_custom_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_custom_index_template")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-custom-index-template-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-custom-index-template-to"
    );
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.metadata_customs.diff_count, 1);
    assert_eq!(response.metadata_customs.diff_keys, vec!["index_template"]);
    assert_eq!(response.metadata_customs.upsert_count, 0);
    assert_eq!(
        response
            .metadata_customs
            .composable_index_template_diffs
            .len(),
        1
    );
    let index_template_custom_diff = &response.metadata_customs.composable_index_template_diffs[0];
    assert_eq!(index_template_custom_diff.delete_count, 0);
    assert_eq!(index_template_custom_diff.diff_count, 1);
    assert_eq!(
        index_template_custom_diff.diff_keys,
        vec!["fixture-diff-composable-template"]
    );
    assert_eq!(index_template_custom_diff.upsert_count, 0);
    assert_eq!(index_template_custom_diff.replacement_diffs.len(), 1);
    let index_template_diff = &index_template_custom_diff.replacement_diffs[0];
    assert!(index_template_diff.replacement_present);
    let template = index_template_diff.replacement.as_ref().unwrap();
    assert_eq!(template.name, "fixture-diff-composable-template");
    assert_eq!(
        template.index_patterns,
        vec![
            "fixture-diff-compose-after-*".to_string(),
            "fixture-diff-compose-alt-*".to_string()
        ]
    );
    assert!(template.template_present);
    assert_eq!(template.template_settings_count, 1);
    assert_eq!(template.template_settings[0].key, "index.number_of_shards");
    assert_eq!(template.template_settings[0].value.as_deref(), Some("2"));
    assert_eq!(template.component_templates_count, 1);
    assert_eq!(
        template.component_templates,
        vec!["fixture-after-component-template".to_string()]
    );
    assert_eq!(template.priority, Some(20));
    assert_eq!(template.version, Some(21));
    assert_eq!(template.metadata_count, 1);
    assert_eq!(template.metadata[0].key, "fixture-diff-meta");
    assert_eq!(template.metadata[0].value.as_deref(), Some("after"));
    assert!(!template.data_stream_template_present);
    assert!(!template.context_present);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_delete_consistent_setting_hash_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_delete_consistent_setting_hash")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-consistent-hash-from"
    );
    assert_eq!(response.header.to_uuid, "fixture-diff-consistent-hash-to");
    assert_eq!(
        response.metadata_hashes_of_consistent_settings.delete_count,
        1
    );
    assert_eq!(
        response.metadata_hashes_of_consistent_settings.deleted_keys,
        vec!["fixture.secure.setting"]
    );
    assert_eq!(
        response.metadata_hashes_of_consistent_settings.upsert_count,
        0
    );
    assert_eq!(response.metadata_indices.delete_count, 0);
    assert_eq!(response.metadata_customs.delete_count, 0);
    assert_eq!(response.customs.delete_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_upsert_metadata_index_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_upsert_metadata_index")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-upsert-metadata-from"
    );
    assert_eq!(response.header.to_uuid, "fixture-diff-upsert-metadata-to");
    assert_eq!(response.metadata_indices.delete_count, 0);
    assert_eq!(response.metadata_indices.diff_count, 0);
    assert_eq!(response.metadata_indices.upsert_count, 1);
    assert_eq!(
        response.metadata_indices.upsert_keys,
        vec!["fixture-upsert-metadata-index"]
    );
    let index = &response.metadata_indices.index_metadata_upserts[0];
    assert_eq!(index.name, "fixture-upsert-metadata-index");
    assert_eq!(
        index.index_uuid.as_deref(),
        Some("fixture-upsert-metadata-index-uuid")
    );
    assert_eq!(index.number_of_shards, Some(1));
    assert_eq!(index.number_of_replicas, Some(0));
    assert_eq!(index.mapping_count, 0);
    assert_eq!(index.alias_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_metadata_index_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_index")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-from"
    );
    assert_eq!(response.header.to_uuid, "fixture-diff-named-metadata-to");
    assert_eq!(response.metadata_indices.delete_count, 0);
    assert_eq!(response.metadata_indices.diff_count, 1);
    assert_eq!(
        response.metadata_indices.diff_keys,
        vec!["fixture-named-metadata-index"]
    );
    assert_eq!(response.metadata_indices.index_metadata_diffs.len(), 1);
    let diff = &response.metadata_indices.index_metadata_diffs[0];
    assert_eq!(diff.name, "fixture-named-metadata-index");
    assert_eq!(diff.version, 2);
    assert_eq!(diff.routing_num_shards, 1);
    assert_eq!(
        diff.index_uuid.as_deref(),
        Some("fixture-named-metadata-index-uuid")
    );
    assert_eq!(diff.number_of_shards, Some(1));
    assert_eq!(diff.number_of_replicas, Some(0));
    assert_eq!(diff.mappings.diff_count, 0);
    assert_eq!(diff.aliases.diff_count, 0);
    assert_eq!(diff.custom_data.diff_count, 0);
    assert_eq!(diff.in_sync_allocation_ids.diff_count, 0);
    assert_eq!(diff.rollover_infos.diff_count, 0);
    assert_eq!(diff.split_shards_replacement_present, Some(false));
    assert_eq!(diff.primary_terms_count, 1);
    assert_eq!(response.metadata_indices.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_metadata_index_mapping_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_index_mapping")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-mapping-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-mapping-to"
    );
    assert_eq!(response.metadata_indices.diff_count, 1);
    let diff = &response.metadata_indices.index_metadata_diffs[0];
    assert_eq!(diff.name, "fixture-named-metadata-index-mapping");
    assert_eq!(diff.mappings.diff_count, 1);
    assert_eq!(diff.mapping_diffs.len(), 1);
    let mapping_diff = &diff.mapping_diffs[0];
    assert_eq!(mapping_diff.key, "_doc");
    assert!(mapping_diff.replacement_present);
    let replacement = mapping_diff.replacement.as_ref().unwrap();
    assert_eq!(replacement.mapping_type, "_doc");
    assert!(replacement.compressed_bytes_len > 0);
    assert!(!replacement.routing_required);
    assert_eq!(response.metadata_indices.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_metadata_index_alias_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_index_alias")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-alias-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-alias-to"
    );
    assert_eq!(response.metadata_indices.diff_count, 1);
    let diff = &response.metadata_indices.index_metadata_diffs[0];
    assert_eq!(diff.name, "fixture-named-metadata-index-alias");
    assert_eq!(diff.aliases.diff_count, 1);
    assert_eq!(diff.alias_diffs.len(), 1);
    let alias_diff = &diff.alias_diffs[0];
    assert_eq!(alias_diff.key, "fixture-nested-alias");
    assert!(alias_diff.replacement_present);
    let replacement = alias_diff.replacement.as_ref().unwrap();
    assert_eq!(replacement.alias, "fixture-nested-alias");
    assert_eq!(replacement.index_routing.as_deref(), Some("after-route"));
    assert_eq!(replacement.search_routing.as_deref(), Some("after-route"));
    assert_eq!(response.metadata_indices.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_metadata_index_custom_data_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_index_custom_data")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-custom-data-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-custom-data-to"
    );
    assert_eq!(response.metadata_indices.diff_count, 1);
    let diff = &response.metadata_indices.index_metadata_diffs[0];
    assert_eq!(diff.name, "fixture-named-metadata-index-custom-data");
    assert_eq!(diff.custom_data.diff_count, 1);
    assert_eq!(diff.custom_data_diffs.len(), 1);
    let custom_data_diff = &diff.custom_data_diffs[0];
    assert_eq!(custom_data_diff.key, "fixture-nested-custom");
    assert_eq!(custom_data_diff.diff.delete_count, 0);
    assert_eq!(custom_data_diff.diff.upsert_count, 1);
    assert_eq!(
        custom_data_diff.diff.upsert_keys,
        vec!["fixture-custom-key"]
    );
    assert_eq!(custom_data_diff.diff.upsert_entries.len(), 1);
    let upsert = &custom_data_diff.diff.upsert_entries[0];
    assert_eq!(upsert.key, "fixture-custom-key");
    assert_eq!(upsert.value, "after-value");
    assert_eq!(response.metadata_indices.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_metadata_index_rollover_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_index_rollover")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-rollover-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-rollover-to"
    );
    assert_eq!(response.metadata_indices.diff_count, 1);
    let diff = &response.metadata_indices.index_metadata_diffs[0];
    assert_eq!(diff.name, "fixture-named-metadata-index-rollover");
    assert_eq!(diff.rollover_infos.diff_count, 1);
    assert_eq!(diff.rollover_info_diffs.len(), 1);
    let rollover_diff = &diff.rollover_info_diffs[0];
    assert_eq!(rollover_diff.key, "fixture-nested-rollover");
    assert!(rollover_diff.replacement_present);
    let replacement = rollover_diff.replacement.as_ref().unwrap();
    assert_eq!(replacement.alias, "fixture-nested-rollover");
    assert_eq!(replacement.time, 222);
    assert_eq!(replacement.met_conditions_count, 0);
    assert!(replacement.met_conditions.is_empty());
    assert_eq!(response.metadata_indices.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_metadata_index_in_sync_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_index_in_sync")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-in-sync-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-in-sync-to"
    );
    assert_eq!(response.metadata_indices.diff_count, 1);
    let diff = &response.metadata_indices.index_metadata_diffs[0];
    assert_eq!(diff.name, "fixture-named-metadata-index-in-sync");
    assert_eq!(diff.in_sync_allocation_ids.delete_count, 0);
    assert_eq!(diff.in_sync_allocation_ids.diff_count, 0);
    assert_eq!(diff.in_sync_allocation_ids.upsert_count, 1);
    assert!(diff
        .in_sync_allocation_ids_diff
        .deleted_shard_ids
        .is_empty());
    assert_eq!(diff.in_sync_allocation_ids_diff.upserts.len(), 1);
    let upsert = &diff.in_sync_allocation_ids_diff.upserts[0];
    assert_eq!(upsert.shard_id, 0);
    assert_eq!(upsert.allocation_ids, vec!["after-allocation"]);
    assert_eq!(response.metadata_indices.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_publication_named_metadata_index_split_shards_diff_decodes_prefix() {
    let fixtures = fixtures();
    let response = read_publication_cluster_state_diff_prefix(
        Bytes::from(
            fixtures
                .get("cluster_state_publication_diff_named_metadata_index_split_shards")
                .unwrap()
                .clone(),
        ),
        OPENSEARCH_3_7_0_TRANSPORT,
    )
    .unwrap();

    assert_eq!(
        response.header.from_uuid,
        "fixture-diff-named-metadata-split-shards-from"
    );
    assert_eq!(
        response.header.to_uuid,
        "fixture-diff-named-metadata-split-shards-to"
    );
    assert_eq!(response.metadata_indices.diff_count, 1);
    let diff = &response.metadata_indices.index_metadata_diffs[0];
    assert_eq!(diff.name, "fixture-named-metadata-index-split-shards");
    assert_eq!(diff.split_shards_replacement_present, Some(true));
    let split = diff.split_shards_replacement.as_ref().unwrap();
    assert_eq!(split.root_count, 3);
    assert_eq!(split.max_shard_id, 2);
    assert_eq!(split.in_progress_split_shard_ids_count, 1);
    assert_eq!(split.active_shard_ids_count, 3);
    assert_eq!(split.parent_to_child_count, 1);
    let parent = &split.parent_to_child[0];
    assert_eq!(parent.parent_shard_id, 0);
    assert_eq!(parent.children_count, 3);
    assert_eq!(parent.children[0].shard_id, 3);
    assert_eq!(parent.children[1].shard_id, 4);
    assert_eq!(parent.children[2].shard_id, 5);
    assert_eq!(response.metadata_indices.upsert_count, 0);
    assert_eq!(response.remaining_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_repository_cleanup_custom_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_repository_cleanup_custom")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 21);
    assert_eq!(header.state_uuid, "fixture-state-with-repository-cleanup");

    let cluster_state_tail = response.cluster_state_tail.unwrap();
    assert_eq!(cluster_state_tail.custom_count, 1);
    assert_eq!(cluster_state_tail.custom_names, vec!["repository_cleanup"]);
    let cleanup = cluster_state_tail.repository_cleanup.as_ref().unwrap();
    assert_eq!(cleanup.entry_count, 1);
    assert_eq!(cleanup.entries[0].repository, "fixture-repository");
    assert_eq!(cleanup.entries[0].repository_state_id, 42);
    assert_eq!(
        cluster_state_tail.minimum_cluster_manager_nodes_on_publishing_cluster_manager,
        -1
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_snapshot_deletions_custom_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_snapshot_deletions_custom")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 22);
    assert_eq!(header.state_uuid, "fixture-state-with-snapshot-deletions");

    let cluster_state_tail = response.cluster_state_tail.unwrap();
    assert_eq!(cluster_state_tail.custom_count, 1);
    assert_eq!(cluster_state_tail.custom_names, vec!["snapshot_deletions"]);
    let deletions = cluster_state_tail.snapshot_deletions.as_ref().unwrap();
    assert_eq!(deletions.entry_count, 1);
    let entry = &deletions.entries[0];
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshots_count, 1);
    assert_eq!(entry.snapshots[0].name, "fixture-delete-snapshot");
    assert_eq!(entry.snapshots[0].uuid, "fixture-delete-snapshot-uuid");
    assert_eq!(entry.start_time, 123456789);
    assert_eq!(entry.repository_state_id, 43);
    assert_eq!(entry.state_id, 1);
    assert!(!entry.uuid.is_empty());
    assert_eq!(
        cluster_state_tail.minimum_cluster_manager_nodes_on_publishing_cluster_manager,
        -1
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_restore_custom_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_restore_custom")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 23);
    assert_eq!(header.state_uuid, "fixture-state-with-restore");

    let cluster_state_tail = response.cluster_state_tail.unwrap();
    assert_eq!(cluster_state_tail.custom_count, 1);
    assert_eq!(cluster_state_tail.custom_names, vec!["restore"]);
    let restore = cluster_state_tail.restore.as_ref().unwrap();
    assert_eq!(restore.entry_count, 1);
    let entry = &restore.entries[0];
    assert_eq!(entry.uuid, "fixture-restore-entry-uuid");
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshot_name, "fixture-restore-snapshot");
    assert_eq!(entry.snapshot_uuid, "fixture-restore-snapshot-uuid");
    assert_eq!(entry.state_id, 1);
    assert_eq!(entry.indices_count, 1);
    assert_eq!(entry.indices, vec!["fixture-index"]);
    assert_eq!(entry.shard_status_count, 0);
    assert!(entry.shard_statuses.is_empty());
    assert_eq!(
        cluster_state_tail.minimum_cluster_manager_nodes_on_publishing_cluster_manager,
        -1
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_restore_custom_shard_status_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_restore_custom_shard_status")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 25);
    assert_eq!(header.state_uuid, "fixture-state-with-restore-shard-status");

    let cluster_state_tail = response.cluster_state_tail.unwrap();
    assert_eq!(cluster_state_tail.custom_count, 1);
    assert_eq!(cluster_state_tail.custom_names, vec!["restore"]);
    let restore = cluster_state_tail.restore.as_ref().unwrap();
    assert_eq!(restore.entry_count, 1);
    let entry = &restore.entries[0];
    assert_eq!(entry.uuid, "fixture-restore-shard-entry-uuid");
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshot_name, "fixture-restore-shard-snapshot");
    assert_eq!(entry.snapshot_uuid, "fixture-restore-shard-snapshot-uuid");
    assert_eq!(entry.state_id, 1);
    assert_eq!(entry.indices, vec!["fixture-restore-shard-index"]);
    assert_eq!(entry.shard_status_count, 1);
    let shard = &entry.shard_statuses[0];
    assert_eq!(shard.index_name, "fixture-restore-shard-index");
    assert_eq!(shard.index_uuid, "fixture-restore-shard-index-uuid");
    assert_eq!(shard.shard_id, 0);
    assert_eq!(shard.node_id.as_deref(), Some("fixture-restore-node-id"));
    assert_eq!(shard.state_id, 1);
    assert_eq!(shard.reason.as_deref(), Some("fixture-restore-reason"));
    assert_eq!(
        cluster_state_tail.minimum_cluster_manager_nodes_on_publishing_cluster_manager,
        -1
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_snapshots_custom_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_snapshots_custom")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 24);
    assert_eq!(header.state_uuid, "fixture-state-with-snapshots");

    let cluster_state_tail = response.cluster_state_tail.unwrap();
    assert_eq!(cluster_state_tail.custom_count, 1);
    assert_eq!(cluster_state_tail.custom_names, vec!["snapshots"]);
    let snapshots = cluster_state_tail.snapshots.as_ref().unwrap();
    assert_eq!(snapshots.entry_count, 1);
    let entry = &snapshots.entries[0];
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshot_name, "fixture-snapshot-in-progress");
    assert_eq!(entry.snapshot_uuid, "fixture-snapshot-in-progress-uuid");
    assert!(entry.include_global_state);
    assert!(!entry.partial);
    assert_eq!(entry.state_id, 2);
    assert_eq!(entry.indices_count, 1);
    assert_eq!(entry.indices[0].name, "fixture-index");
    assert_eq!(entry.indices[0].id, "fixture-snapshot-index-id");
    assert_eq!(entry.start_time, 123456789);
    assert_eq!(entry.shard_status_count, 0);
    assert!(entry.shard_statuses.is_empty());
    assert_eq!(entry.repository_state_id, 44);
    assert_eq!(entry.failure, None);
    assert_eq!(entry.user_metadata_count, 0);
    assert!(entry.user_metadata.is_empty());
    assert_eq!(entry.data_streams, vec!["fixture-data-stream"]);
    assert_eq!(entry.source, None);
    assert_eq!(entry.clone_count, 0);
    assert!(entry.clones.is_empty());
    assert_eq!(entry.remote_store_index_shallow_copy, Some(false));
    assert_eq!(entry.remote_store_index_shallow_copy_v2, Some(false));
    assert_eq!(
        cluster_state_tail.minimum_cluster_manager_nodes_on_publishing_cluster_manager,
        -1
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_snapshots_custom_shard_status_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_snapshots_custom_shard_status")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 26);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-snapshots-shard-status"
    );

    let cluster_state_tail = response.cluster_state_tail.unwrap();
    assert_eq!(cluster_state_tail.custom_count, 1);
    assert_eq!(cluster_state_tail.custom_names, vec!["snapshots"]);
    let snapshots = cluster_state_tail.snapshots.as_ref().unwrap();
    assert_eq!(snapshots.entry_count, 1);
    let entry = &snapshots.entries[0];
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshot_name, "fixture-snapshot-shard-in-progress");
    assert_eq!(
        entry.snapshot_uuid,
        "fixture-snapshot-shard-in-progress-uuid"
    );
    assert_eq!(entry.state_id, 1);
    assert_eq!(entry.indices[0].name, "fixture-snapshot-shard-index");
    assert_eq!(entry.indices[0].id, "fixture-snapshot-shard-index-id");
    assert_eq!(entry.start_time, 223456789);
    assert_eq!(entry.shard_status_count, 1);
    let shard = &entry.shard_statuses[0];
    assert_eq!(shard.index_name, "fixture-snapshot-shard-index");
    assert_eq!(shard.index_uuid, "fixture-snapshot-shard-index-uuid");
    assert_eq!(shard.shard_id, 0);
    assert_eq!(shard.node_id.as_deref(), Some("fixture-snapshot-node-id"));
    assert_eq!(shard.state_id, 0);
    assert_eq!(
        shard.generation.as_deref(),
        Some("fixture-snapshot-generation")
    );
    assert_eq!(shard.reason, None);
    assert_eq!(entry.repository_state_id, 45);
    assert_eq!(entry.user_metadata_count, 0);
    assert!(entry.user_metadata.is_empty());
    assert_eq!(
        entry.data_streams,
        vec!["fixture-snapshot-shard-data-stream"]
    );
    assert_eq!(entry.clone_count, 0);
    assert!(entry.clones.is_empty());
    assert_eq!(
        cluster_state_tail.minimum_cluster_manager_nodes_on_publishing_cluster_manager,
        -1
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_snapshots_custom_clone_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_snapshots_custom_clone")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 27);
    assert_eq!(header.state_uuid, "fixture-state-with-snapshots-clone");

    let cluster_state_tail = response.cluster_state_tail.unwrap();
    assert_eq!(cluster_state_tail.custom_count, 1);
    assert_eq!(cluster_state_tail.custom_names, vec!["snapshots"]);
    let snapshots = cluster_state_tail.snapshots.as_ref().unwrap();
    assert_eq!(snapshots.entry_count, 1);
    let entry = &snapshots.entries[0];
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshot_name, "fixture-snapshot-clone");
    assert_eq!(entry.snapshot_uuid, "fixture-snapshot-clone-uuid");
    assert_eq!(entry.state_id, 1);
    assert_eq!(entry.indices[0].name, "fixture-clone-index");
    assert_eq!(entry.indices[0].id, "fixture-clone-index-id");
    assert_eq!(entry.start_time, 323456789);
    assert_eq!(entry.shard_status_count, 0);
    assert!(entry.shard_statuses.is_empty());
    assert_eq!(entry.repository_state_id, 46);
    let source = entry.source.as_ref().unwrap();
    assert_eq!(source.name, "fixture-source-snapshot");
    assert_eq!(source.uuid, "fixture-source-snapshot-uuid");
    assert_eq!(entry.clone_count, 1);
    let clone = &entry.clones[0];
    assert_eq!(clone.index_name, "fixture-clone-index");
    assert_eq!(clone.index_id, "fixture-clone-index-id");
    assert_eq!(clone.shard_id, 0);
    assert_eq!(clone.node_id.as_deref(), Some("fixture-clone-node-id"));
    assert_eq!(clone.state_id, 0);
    assert_eq!(
        clone.generation.as_deref(),
        Some("fixture-clone-generation")
    );
    assert_eq!(clone.reason, None);
    assert_eq!(
        cluster_state_tail.minimum_cluster_manager_nodes_on_publishing_cluster_manager,
        -1
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_snapshots_custom_user_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_snapshots_custom_user_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 28);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-snapshots-user-metadata"
    );

    let cluster_state_tail = response.cluster_state_tail.unwrap();
    assert_eq!(cluster_state_tail.custom_count, 1);
    assert_eq!(cluster_state_tail.custom_names, vec!["snapshots"]);
    let snapshots = cluster_state_tail.snapshots.as_ref().unwrap();
    assert_eq!(snapshots.entry_count, 1);
    let entry = &snapshots.entries[0];
    assert_eq!(entry.repository, "fixture-repository");
    assert_eq!(entry.snapshot_name, "fixture-snapshot-user-metadata");
    assert_eq!(entry.snapshot_uuid, "fixture-snapshot-user-metadata-uuid");
    assert_eq!(entry.indices[0].name, "fixture-user-metadata-index");
    assert_eq!(entry.indices[0].id, "fixture-user-metadata-index-id");
    assert_eq!(entry.start_time, 423456789);
    assert_eq!(entry.repository_state_id, 47);
    assert_eq!(entry.user_metadata_count, 14);
    assert_eq!(entry.user_metadata[0].key, "fixture-user-string");
    assert_eq!(
        entry.user_metadata[0].value,
        GenericValuePrefix::String("fixture-user-value".to_string())
    );
    assert_eq!(entry.user_metadata[1].key, "fixture-user-int");
    assert_eq!(entry.user_metadata[1].value, GenericValuePrefix::Int(7));
    assert_eq!(entry.user_metadata[2].key, "fixture-user-long");
    assert_eq!(entry.user_metadata[2].value, GenericValuePrefix::Long(8));
    assert_eq!(entry.user_metadata[3].key, "fixture-user-bool");
    assert_eq!(entry.user_metadata[3].value, GenericValuePrefix::Bool(true));
    assert_eq!(entry.user_metadata[4].key, "fixture-user-null");
    assert_eq!(entry.user_metadata[4].value, GenericValuePrefix::Null);
    assert_eq!(entry.user_metadata[5].key, "fixture-user-byte");
    assert_eq!(entry.user_metadata[5].value, GenericValuePrefix::Byte(11));
    assert_eq!(entry.user_metadata[6].key, "fixture-user-short");
    assert_eq!(entry.user_metadata[6].value, GenericValuePrefix::Short(12));
    assert_eq!(entry.user_metadata[7].key, "fixture-user-float");
    assert_eq!(
        entry.user_metadata[7].value,
        GenericValuePrefix::FloatBits(1.5f32.to_bits())
    );
    assert_eq!(entry.user_metadata[8].key, "fixture-user-double");
    assert_eq!(
        entry.user_metadata[8].value,
        GenericValuePrefix::DoubleBits(2.5f64.to_bits())
    );
    assert_eq!(entry.user_metadata[9].key, "fixture-user-date");
    assert_eq!(
        entry.user_metadata[9].value,
        GenericValuePrefix::DateMillis(123456789)
    );
    assert_eq!(entry.user_metadata[10].key, "fixture-user-bytes");
    assert_eq!(
        entry.user_metadata[10].value,
        GenericValuePrefix::Bytes(vec![1, 2, 3])
    );
    assert_eq!(entry.user_metadata[11].key, "fixture-user-list");
    assert_eq!(
        entry.user_metadata[11].value,
        GenericValuePrefix::List(vec![
            GenericValuePrefix::String("fixture-list-value".to_string()),
            GenericValuePrefix::Int(9),
            GenericValuePrefix::Bool(false),
        ])
    );
    assert_eq!(entry.user_metadata[12].key, "fixture-user-array");
    assert_eq!(
        entry.user_metadata[12].value,
        GenericValuePrefix::Array(vec![
            GenericValuePrefix::String("fixture-array-value".to_string()),
            GenericValuePrefix::Long(10),
        ])
    );
    assert_eq!(entry.user_metadata[13].key, "fixture-user-map");
    assert_eq!(
        entry.user_metadata[13].value,
        GenericValuePrefix::Map(vec![
            os_cluster_state::GenericMapEntryPrefix {
                key: "nested-string".to_string(),
                value: GenericValuePrefix::String("nested-value".to_string()),
            },
            os_cluster_state::GenericMapEntryPrefix {
                key: "nested-bool".to_string(),
                value: GenericValuePrefix::Bool(false),
            },
        ])
    );
    assert_eq!(
        cluster_state_tail.minimum_cluster_manager_nodes_on_publishing_cluster_manager,
        -1
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_index_routing_decodes_index_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_index_routing")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 10);
    assert_eq!(header.state_uuid, "fixture-state-with-routing");

    let routing_table = response.routing_table.unwrap();
    assert_eq!(routing_table.index_routing_table_count, 1);
    let index = &routing_table.indices[0];
    assert_eq!(index.index_name, "fixture-index");
    assert_eq!(index.index_uuid, "fixture-index-uuid");
    assert_eq!(index.shard_table_count, 0);
    assert!(index.shards.is_empty());
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_index_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_index_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 11);
    assert_eq!(header.state_uuid, "fixture-state-with-index-metadata");

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.index_metadata_count, 1);
    let index = &metadata.index_metadata[0];
    assert_eq!(index.name, "fixture-index");
    assert_eq!(index.index_uuid.as_deref(), Some("fixture-index-uuid"));
    assert_eq!(index.number_of_shards, Some(1));
    assert_eq!(index.number_of_replicas, Some(0));
    assert_eq!(index.routing_num_shards, 1);
    assert_eq!(index.mapping_count, 0);
    assert!(index.mappings.is_empty());
    assert_eq!(index.alias_count, 0);
    assert!(index.aliases.is_empty());
    assert_eq!(index.custom_data_count, 0);
    assert!(index.custom_data.is_empty());
    assert_eq!(index.rollover_info_count, 0);
    assert!(index.rollover_infos.is_empty());
    assert!(!index.context_present);
    assert!(index.ingestion_status_present);
    assert_eq!(index.ingestion_paused, Some(false));
    assert_eq!(index.split_shards_root_count, Some(1));
    assert!(index.split_shards_root_children.is_empty());
    assert_eq!(index.split_shards_max_shard_id, Some(0));
    assert_eq!(index.split_shards_in_progress_count, Some(0));
    assert_eq!(index.split_shards_active_count, Some(1));
    assert_eq!(index.split_shards_parent_to_child_count, Some(0));
    assert!(index.split_shards_parent_to_child.is_empty());
    assert_eq!(index.primary_terms_count, 1);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_index_metadata_mapping_alias_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_index_metadata_mapping_alias")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 22);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-index-metadata-mapping-alias"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.index_metadata_count, 1);
    let index = &metadata.index_metadata[0];
    assert_eq!(index.name, "fixture-index-mapping-alias");
    assert_eq!(
        index.index_uuid.as_deref(),
        Some("fixture-index-mapping-alias-uuid")
    );
    assert_eq!(index.mapping_count, 1);
    assert_eq!(index.mappings[0].mapping_type, "_doc");
    assert!(index.mappings[0].compressed_bytes_len > 0);
    assert!(!index.mappings[0].routing_required);
    assert_eq!(index.alias_count, 1);
    assert_eq!(index.aliases[0].alias, "fixture-index-alias");
    assert_eq!(index.aliases[0].filter, None);
    assert_eq!(index.aliases[0].index_routing, None);
    assert_eq!(index.aliases[0].search_routing, None);
    assert_eq!(index.aliases[0].write_index, None);
    assert_eq!(index.aliases[0].is_hidden, None);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_index_metadata_custom_data_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_index_metadata_custom_data")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 23);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-index-metadata-custom-data"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.index_metadata_count, 1);
    let index = &metadata.index_metadata[0];
    assert_eq!(index.name, "fixture-index-custom-data");
    assert_eq!(
        index.index_uuid.as_deref(),
        Some("fixture-index-custom-data-uuid")
    );
    assert_eq!(index.custom_data_count, 1);
    let custom = &index.custom_data[0];
    assert_eq!(custom.key, "fixture-custom");
    assert_eq!(custom.entries_count, 1);
    assert_eq!(custom.entries[0].key, "fixture-custom-key");
    assert_eq!(
        custom.entries[0].value.as_deref(),
        Some("fixture-custom-value")
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_index_metadata_rollover_info_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_index_metadata_rollover_info")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 24);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-index-metadata-rollover-info"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.index_metadata_count, 1);
    let index = &metadata.index_metadata[0];
    assert_eq!(index.name, "fixture-index-rollover");
    assert_eq!(
        index.index_uuid.as_deref(),
        Some("fixture-index-rollover-uuid")
    );
    assert_eq!(index.rollover_info_count, 1);
    let rollover = &index.rollover_infos[0];
    assert_eq!(rollover.alias, "fixture-rollover-alias");
    assert_eq!(rollover.time, 123456);
    assert_eq!(rollover.met_conditions_count, 0);
    assert!(rollover.met_conditions.is_empty());
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_index_metadata_rollover_condition_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_index_metadata_rollover_condition")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 25);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-index-metadata-rollover-condition"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.index_metadata_count, 1);
    let index = &metadata.index_metadata[0];
    assert_eq!(index.name, "fixture-index-rollover-condition");
    assert_eq!(
        index.index_uuid.as_deref(),
        Some("fixture-index-rollover-condition-uuid")
    );
    assert_eq!(index.rollover_info_count, 1);
    let rollover = &index.rollover_infos[0];
    assert_eq!(rollover.alias, "fixture-rollover-condition-alias");
    assert_eq!(rollover.time, 234567);
    assert_eq!(rollover.met_conditions_count, 1);
    assert_eq!(rollover.met_conditions[0].name, "max_docs");
    assert_eq!(rollover.met_conditions[0].value.as_deref(), Some("42"));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_index_metadata_rollover_size_age_conditions_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_index_metadata_rollover_size_age_conditions")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 26);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-index-metadata-rollover-size-age"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.index_metadata_count, 1);
    let index = &metadata.index_metadata[0];
    assert_eq!(index.name, "fixture-index-rollover-size-age");
    assert_eq!(
        index.index_uuid.as_deref(),
        Some("fixture-index-rollover-size-age-uuid")
    );
    assert_eq!(index.rollover_info_count, 1);
    let rollover = &index.rollover_infos[0];
    assert_eq!(rollover.alias, "fixture-rollover-size-age-alias");
    assert_eq!(rollover.time, 345678);
    assert_eq!(rollover.met_conditions_count, 2);
    assert_eq!(rollover.met_conditions[0].name, "max_age");
    assert_eq!(rollover.met_conditions[0].value.as_deref(), Some("60000"));
    assert_eq!(rollover.met_conditions[1].name, "max_size");
    assert_eq!(rollover.met_conditions[1].value.as_deref(), Some("1024"));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_index_metadata_split_shards_decodes_ranges() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_index_metadata_split_shards")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 27);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-index-metadata-split-shards"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.index_metadata_count, 1);
    let index = &metadata.index_metadata[0];
    assert_eq!(index.name, "fixture-index-split-shards");
    assert_eq!(
        index.index_uuid.as_deref(),
        Some("fixture-index-split-shards-uuid")
    );
    assert_eq!(index.number_of_shards, Some(3));
    assert_eq!(index.split_shards_root_count, Some(3));
    assert_eq!(index.split_shards_max_shard_id, Some(2));
    assert_eq!(index.split_shards_in_progress_count, Some(1));
    assert_eq!(index.split_shards_active_count, Some(3));
    assert_eq!(index.split_shards_parent_to_child_count, Some(1));
    let split = &index.split_shards_parent_to_child[0];
    assert_eq!(split.parent_shard_id, 0);
    assert_eq!(split.children_count, 3);
    assert_eq!(split.children[0].shard_id, 3);
    assert_eq!(split.children[1].shard_id, 4);
    assert_eq!(split.children[2].shard_id, 5);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_shard_routing_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_shard_routing")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 12);
    assert_eq!(header.state_uuid, "fixture-state-with-shard-routing");

    let routing_table = response.routing_table.unwrap();
    assert_eq!(routing_table.index_routing_table_count, 1);
    let index = &routing_table.indices[0];
    assert_eq!(index.index_name, "fixture-index");
    assert_eq!(index.index_uuid, "fixture-index-uuid");
    assert_eq!(index.shard_table_count, 1);
    let shard_table = &index.shards[0];
    assert_eq!(shard_table.shard_id, 0);
    assert_eq!(shard_table.shard_routing_count, 1);
    let shard = &shard_table.shard_routings[0];
    assert_eq!(shard.current_node_id, None);
    assert_eq!(shard.relocating_node_id, None);
    assert!(shard.primary);
    assert!(!shard.search_only);
    assert_eq!(shard.state, ShardRoutingStatePrefix::Unassigned);
    assert_eq!(
        shard.recovery_source_type,
        Some(RecoverySourceTypePrefix::EmptyStore)
    );
    assert!(shard.unassigned_info.is_some());
    assert!(!shard.allocation_id_present);
    assert_eq!(shard.expected_shard_size, None);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_unassigned_failure_decodes_exception_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_unassigned_failure")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 20);
    assert_eq!(header.state_uuid, "fixture-state-with-unassigned-failure");

    let routing_table = response.routing_table.unwrap();
    let shard = &routing_table.indices[0].shards[0].shard_routings[0];
    assert_eq!(shard.state, ShardRoutingStatePrefix::Unassigned);
    let unassigned = shard.unassigned_info.as_ref().unwrap();
    assert_eq!(
        unassigned.message.as_deref(),
        Some("fixture allocation failed")
    );
    assert_eq!(unassigned.failed_allocations, 1);
    assert_eq!(unassigned.failed_node_ids_count, 1);
    let failure = unassigned.failure.as_ref().unwrap();
    assert_eq!(failure.class_name, "java.lang.IllegalStateException");
    assert_eq!(failure.message.as_deref(), Some("fixture shard failure"));
    assert_eq!(
        failure.summary,
        "java.lang.IllegalStateException: fixture shard failure"
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_started_shard_routing_decodes_allocation() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_started_shard_routing")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 13);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-started-shard-routing"
    );

    let routing_table = response.routing_table.unwrap();
    let shard = &routing_table.indices[0].shards[0].shard_routings[0];
    assert_eq!(shard.current_node_id.as_deref(), Some("fixture-node-id"));
    assert_eq!(shard.relocating_node_id, None);
    assert!(shard.primary);
    assert!(!shard.search_only);
    assert_eq!(shard.state, ShardRoutingStatePrefix::Started);
    assert_eq!(shard.recovery_source_type, None);
    assert_eq!(shard.unassigned_info, None);
    assert!(shard.allocation_id_present);
    let allocation_id = shard.allocation_id.as_ref().unwrap();
    assert!(!allocation_id.id.is_empty());
    assert_eq!(allocation_id.relocation_id, None);
    assert_eq!(allocation_id.split_child_allocation_ids_count, Some(0));
    assert_eq!(allocation_id.parent_allocation_id, None);
    assert_eq!(shard.expected_shard_size, None);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_initializing_shard_routing_decodes_expected_size() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_initializing_shard_routing")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 14);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-initializing-shard-routing"
    );

    let routing_table = response.routing_table.unwrap();
    let shard = &routing_table.indices[0].shards[0].shard_routings[0];
    assert_eq!(shard.current_node_id.as_deref(), Some("fixture-node-id"));
    assert_eq!(shard.relocating_node_id, None);
    assert!(shard.primary);
    assert!(!shard.search_only);
    assert_eq!(shard.state, ShardRoutingStatePrefix::Initializing);
    assert_eq!(
        shard.recovery_source_type,
        Some(RecoverySourceTypePrefix::EmptyStore)
    );
    let unassigned = shard.unassigned_info.as_ref().unwrap();
    assert_eq!(unassigned.reason_id, 0);
    assert_eq!(
        unassigned.message.as_deref(),
        Some("fixture initializing shard")
    );
    assert!(shard.allocation_id_present);
    assert!(!shard.allocation_id.as_ref().unwrap().id.is_empty());
    assert_eq!(shard.expected_shard_size, Some(12345));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_existing_store_recovery_source_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_existing_store_recovery_source")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 17);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-existing-store-recovery-source"
    );

    let routing_table = response.routing_table.unwrap();
    let shard = &routing_table.indices[0].shards[0].shard_routings[0];
    assert_eq!(shard.current_node_id, None);
    assert_eq!(shard.relocating_node_id, None);
    assert!(shard.primary);
    assert_eq!(shard.state, ShardRoutingStatePrefix::Unassigned);
    assert_eq!(
        shard.recovery_source_type,
        Some(RecoverySourceTypePrefix::ExistingStore)
    );
    assert_eq!(shard.recovery_source_bootstrap_new_history_uuid, Some(true));
    let unassigned = shard.unassigned_info.as_ref().unwrap();
    assert_eq!(
        unassigned.message.as_deref(),
        Some("fixture existing store shard")
    );
    assert!(!shard.allocation_id_present);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_snapshot_recovery_source_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_snapshot_recovery_source")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 18);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-snapshot-recovery-source"
    );

    let routing_table = response.routing_table.unwrap();
    let shard = &routing_table.indices[0].shards[0].shard_routings[0];
    assert_eq!(shard.state, ShardRoutingStatePrefix::Unassigned);
    assert_eq!(
        shard.recovery_source_type,
        Some(RecoverySourceTypePrefix::Snapshot)
    );
    assert_eq!(shard.recovery_source_bootstrap_new_history_uuid, None);
    let snapshot = shard.snapshot_recovery_source.as_ref().unwrap();
    assert_eq!(snapshot.restore_uuid, "fixture-restore-uuid");
    assert_eq!(snapshot.repository, "fixture-repository");
    assert_eq!(snapshot.snapshot_name, "fixture-snapshot");
    assert_eq!(snapshot.snapshot_uuid, "fixture-snapshot-uuid");
    assert_eq!(snapshot.index_name, "fixture-index");
    assert_eq!(snapshot.index_id, "fixture-snapshot-index-id");
    assert_eq!(snapshot.is_searchable_snapshot, Some(true));
    assert_eq!(snapshot.remote_store_index_shallow_copy, Some(false));
    assert_eq!(snapshot.source_remote_store_repository, None);
    assert_eq!(snapshot.source_remote_translog_repository, None);
    assert_eq!(snapshot.pinned_timestamp, Some(123456789));
    let unassigned = shard.unassigned_info.as_ref().unwrap();
    assert_eq!(
        unassigned.message.as_deref(),
        Some("fixture snapshot shard")
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_remote_store_recovery_source_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_remote_store_recovery_source")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 19);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-remote-store-recovery-source"
    );

    let routing_table = response.routing_table.unwrap();
    let shard = &routing_table.indices[0].shards[0].shard_routings[0];
    assert_eq!(shard.state, ShardRoutingStatePrefix::Unassigned);
    assert_eq!(
        shard.recovery_source_type,
        Some(RecoverySourceTypePrefix::RemoteStore)
    );
    assert_eq!(shard.snapshot_recovery_source, None);
    let remote_store = shard.remote_store_recovery_source.as_ref().unwrap();
    assert_eq!(remote_store.restore_uuid, "fixture-remote-restore-uuid");
    assert_eq!(remote_store.index_name, "fixture-index");
    assert_eq!(remote_store.index_id, "fixture-remote-index-id");
    let unassigned = shard.unassigned_info.as_ref().unwrap();
    assert_eq!(
        unassigned.message.as_deref(),
        Some("fixture remote store shard")
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_relocating_shard_routing_decodes_relocation() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_relocating_shard_routing")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 15);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-relocating-shard-routing"
    );

    let routing_table = response.routing_table.unwrap();
    let shard = &routing_table.indices[0].shards[0].shard_routings[0];
    assert_eq!(shard.current_node_id.as_deref(), Some("fixture-node-id"));
    assert_eq!(
        shard.relocating_node_id.as_deref(),
        Some("fixture-relocating-node-id")
    );
    assert!(shard.primary);
    assert!(!shard.search_only);
    assert_eq!(shard.state, ShardRoutingStatePrefix::Relocating);
    assert_eq!(shard.recovery_source_type, None);
    assert_eq!(shard.unassigned_info, None);
    assert!(shard.allocation_id_present);
    let allocation_id = shard.allocation_id.as_ref().unwrap();
    assert!(!allocation_id.id.is_empty());
    assert!(allocation_id.relocation_id.is_some());
    assert_eq!(allocation_id.split_child_allocation_ids_count, Some(0));
    assert_eq!(allocation_id.parent_allocation_id, None);
    assert_eq!(shard.expected_shard_size, Some(23456));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_replica_shard_routing_decodes_two_entries() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_replica_shard_routing")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 16);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-replica-shard-routing"
    );

    let metadata = response.metadata_prefix.unwrap();
    let index_metadata = &metadata.index_metadata[0];
    assert_eq!(index_metadata.number_of_replicas, Some(1));

    let routing_table = response.routing_table.unwrap();
    let shard_table = &routing_table.indices[0].shards[0];
    assert_eq!(shard_table.shard_id, 0);
    assert_eq!(shard_table.shard_routing_count, 2);

    let primary = &shard_table.shard_routings[0];
    assert!(primary.primary);
    assert_eq!(primary.state, ShardRoutingStatePrefix::Started);
    assert_eq!(primary.current_node_id.as_deref(), Some("fixture-node-id"));

    let replica = &shard_table.shard_routings[1];
    assert!(!replica.primary);
    assert_eq!(replica.current_node_id, None);
    assert_eq!(replica.state, ShardRoutingStatePrefix::Unassigned);
    assert_eq!(
        replica.recovery_source_type,
        Some(RecoverySourceTypePrefix::Peer)
    );
    let unassigned = replica.unassigned_info.as_ref().unwrap();
    assert_eq!(unassigned.reason_id, 6);
    assert_eq!(unassigned.message.as_deref(), Some("fixture replica shard"));
    assert!(!replica.allocation_id_present);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_single_node_decodes_discovery_node() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_single_node")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 8);
    assert_eq!(header.state_uuid, "fixture-state-with-node");

    let discovery_nodes = response.discovery_nodes.unwrap();
    assert_eq!(
        discovery_nodes.cluster_manager_node_id.as_deref(),
        Some("fixture-node-id")
    );
    assert_eq!(discovery_nodes.node_count, 1);
    let node = &discovery_nodes.nodes[0];
    assert_eq!(node.name, "fixture-node");
    assert_eq!(node.id, "fixture-node-id");
    assert_eq!(node.ephemeral_id, "fixture-ephemeral-id");
    assert_eq!(node.host_name, "127.0.0.1");
    assert_eq!(node.host_address, "127.0.0.1");
    assert_eq!(node.address.ip, IpAddr::V4(Ipv4Addr::new(127, 0, 0, 1)));
    assert_eq!(node.address.host, "127.0.0.1");
    assert_eq!(node.address.port, 9300);
    assert_eq!(node.stream_address, None);
    assert_eq!(node.attribute_count, 0);
    assert_eq!(node.roles.len(), 1);
    assert_eq!(node.roles[0].name, "cluster_manager");
    assert_eq!(node.roles[0].abbreviation, "m");
    assert!(!node.roles[0].can_contain_data);
    assert_eq!(node.version, OPENSEARCH_3_7_0_TRANSPORT.id());
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_global_block_decodes_block() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_global_block")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 9);
    assert_eq!(header.state_uuid, "fixture-state-with-block");

    let cluster_blocks = response.cluster_blocks.unwrap();
    assert_eq!(cluster_blocks.global_block_count, 1);
    assert_eq!(cluster_blocks.index_block_count, 0);
    let block = &cluster_blocks.global_blocks[0];
    assert_eq!(block.id, 42);
    assert_eq!(block.uuid.as_deref(), Some("fixture-block-uuid"));
    assert_eq!(block.description, "fixture global block");
    assert_eq!(
        block.levels,
        vec![
            ClusterBlockLevelPrefix::Write,
            ClusterBlockLevelPrefix::MetadataWrite
        ]
    );
    assert!(block.retryable);
    assert!(!block.disable_state_persistence);
    assert_eq!(block.status, "SERVICE_UNAVAILABLE");
    assert!(block.allow_release_resources);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_index_block_decodes_block() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_index_block")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 17);
    assert_eq!(header.state_uuid, "fixture-state-with-index-block");

    let cluster_blocks = response.cluster_blocks.unwrap();
    assert_eq!(cluster_blocks.global_block_count, 0);
    assert_eq!(cluster_blocks.index_block_count, 1);
    let index_blocks = &cluster_blocks.index_blocks[0];
    assert_eq!(index_blocks.index_name, "fixture-index");
    assert_eq!(index_blocks.block_count, 1);
    let block = &index_blocks.blocks[0];
    assert_eq!(block.id, 43);
    assert_eq!(block.uuid.as_deref(), Some("fixture-index-block-uuid"));
    assert_eq!(block.description, "fixture index block");
    assert_eq!(
        block.levels,
        vec![
            ClusterBlockLevelPrefix::Read,
            ClusterBlockLevelPrefix::MetadataRead
        ]
    );
    assert_eq!(block.status, "FORBIDDEN");
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_metadata_settings_decodes_settings() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_metadata_settings")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 18);
    assert_eq!(header.state_uuid, "fixture-state-with-metadata-settings");

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.transient_settings_count, 1);
    assert_eq!(
        metadata.transient_settings[0].key,
        "fixture.transient.setting"
    );
    assert_eq!(
        metadata.transient_settings[0].value.as_deref(),
        Some("transient-value")
    );
    assert_eq!(metadata.persistent_settings_count, 1);
    assert_eq!(
        metadata.persistent_settings[0].key,
        "fixture.persistent.setting"
    );
    assert_eq!(
        metadata.persistent_settings[0].value.as_deref(),
        Some("persistent-value")
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_coordination_metadata_settings_decodes_values() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_coordination_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.transient_settings_count, 1);
    assert_eq!(
        metadata.transient_settings[0].key,
        "fixture.transient.coordination"
    );
    assert_eq!(
        metadata.transient_settings[0].value.as_deref(),
        Some("coordination-transient")
    );
    assert_eq!(metadata.persistent_settings_count, 1);
    assert_eq!(
        metadata.persistent_settings[0].key,
        "fixture.persistent.coordination"
    );
    assert_eq!(
        metadata.persistent_settings[0].value.as_deref(),
        Some("coordination-persistent")
    );
    assert_eq!(metadata.hashes_of_consistent_settings_count, 1);
    assert_eq!(
        metadata.hashes_of_consistent_settings[0].key,
        "fixture.secure.coordination"
    );
    assert_eq!(
        metadata.hashes_of_consistent_settings[0].value.as_deref(),
        Some("coordination-hash")
    );

    let coordination = metadata.coordination;
    assert_eq!(coordination.term, 23);
    assert_eq!(
        coordination.last_committed_configuration,
        ["fixture-node-1", "fixture-node-2"]
            .into_iter()
            .map(str::to_string)
            .collect()
    );
    assert_eq!(
        coordination.last_accepted_configuration,
        ["fixture-node-2"].into_iter().map(str::to_string).collect()
    );
    assert_eq!(coordination.voting_config_exclusions.len(), 1);
    assert_eq!(
        coordination.voting_config_exclusions[0].node_id,
        "fixture-node-3"
    );
    assert_eq!(
        coordination.voting_config_exclusions[0].node_name,
        "fixture-node-name-3"
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_consistent_setting_hashes_decodes_hashes() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_consistent_setting_hashes")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 19);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-consistent-setting-hashes"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.hashes_of_consistent_settings_count, 1);
    assert_eq!(
        metadata.hashes_of_consistent_settings[0].key,
        "fixture.secure.setting"
    );
    assert_eq!(
        metadata.hashes_of_consistent_settings[0].value.as_deref(),
        Some("hash-value")
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_index_graveyard_tombstone_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_index_graveyard_tombstone")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 28);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-index-graveyard-tombstone"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 1);
    assert_eq!(metadata.index_graveyard_tombstones_count, Some(1));
    let tombstone = &metadata.index_graveyard_tombstones[0];
    assert_eq!(tombstone.index_name, "fixture-deleted-index");
    assert_eq!(tombstone.index_uuid, "fixture-deleted-index-uuid");
    assert!(tombstone.delete_date_in_millis > 0);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_component_template_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_component_template")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 29);
    assert_eq!(header.state_uuid, "fixture-state-with-component-template");

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    assert_eq!(metadata.index_graveyard_tombstones_count, Some(0));
    assert_eq!(metadata.component_templates_count, Some(1));
    let template = &metadata.component_templates[0];
    assert_eq!(template.name, "fixture-component-template");
    assert_eq!(template.settings_count, 1);
    assert_eq!(template.settings[0].key, "index.number_of_shards");
    assert_eq!(template.settings[0].value.as_deref(), Some("1"));
    assert!(!template.mappings_present);
    assert_eq!(template.aliases_count, 0);
    assert_eq!(template.version, Some(5));
    assert!(!template.metadata_present);
    assert_eq!(template.metadata_count, 0);
    assert!(template.metadata.is_empty());
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_component_template_mapping_alias_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_component_template_mapping_alias")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 30);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-component-template-mapping-alias"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    assert_eq!(metadata.component_templates_count, Some(1));
    let template = &metadata.component_templates[0];
    assert_eq!(template.name, "fixture-component-template-mapping-alias");
    assert_eq!(template.settings_count, 1);
    assert!(template.mappings_present);
    assert!(template
        .mapping
        .as_ref()
        .is_some_and(|mapping| mapping.compressed_bytes_len > 0));
    assert_eq!(template.aliases_count, 1);
    assert_eq!(template.aliases[0].alias, "fixture-component-alias");
    assert_eq!(template.version, Some(6));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_component_template_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_component_template_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 31);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-component-template-metadata"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.component_templates_count, Some(1));
    let template = &metadata.component_templates[0];
    assert_eq!(template.name, "fixture-component-template-metadata");
    assert_eq!(template.version, Some(7));
    assert!(template.metadata_present);
    assert_eq!(template.metadata_count, 1);
    assert_eq!(template.metadata[0].key, "fixture-meta-key");
    assert_eq!(
        template.metadata[0].value.as_deref(),
        Some("fixture-meta-value")
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_composable_index_template_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_composable_index_template")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 32);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-composable-index-template"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    assert_eq!(metadata.composable_index_templates_count, Some(1));
    let template = &metadata.composable_index_templates[0];
    assert_eq!(template.name, "fixture-composable-template");
    assert_eq!(
        template.index_patterns,
        vec![
            "fixture-compose-*".to_string(),
            "fixture-compose-alt-*".to_string()
        ]
    );
    assert!(template.template_present);
    assert_eq!(template.template_settings_count, 1);
    assert_eq!(template.template_settings[0].key, "index.number_of_shards");
    assert_eq!(template.template_settings[0].value.as_deref(), Some("1"));
    assert!(!template.template_mappings_present);
    assert!(template.template_mapping.is_none());
    assert_eq!(template.template_aliases_count, 0);
    assert!(template.template_aliases.is_empty());
    assert_eq!(template.component_templates_count, 1);
    assert_eq!(
        template.component_templates,
        vec!["fixture-component-template".to_string()]
    );
    assert_eq!(template.priority, Some(11));
    assert_eq!(template.version, Some(12));
    assert_eq!(template.metadata_count, 1);
    assert_eq!(template.metadata[0].key, "fixture-template-meta");
    assert_eq!(
        template.metadata[0].value.as_deref(),
        Some("fixture-template-meta-value")
    );
    assert!(!template.data_stream_template_present);
    assert_eq!(template.data_stream_timestamp_field, None);
    assert!(!template.context_present);
    assert_eq!(template.context_name, None);
    assert_eq!(template.context_version, None);
    assert_eq!(template.context_params_count, 0);
    assert!(template.context_params.is_empty());
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_composable_index_template_mapping_alias_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_composable_index_template_mapping_alias")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 33);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-composable-index-template-mapping-alias"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.composable_index_templates_count, Some(1));
    let template = &metadata.composable_index_templates[0];
    assert_eq!(template.name, "fixture-composable-template-mapping-alias");
    assert_eq!(
        template.index_patterns,
        vec!["fixture-compose-map-*".to_string()]
    );
    assert!(template.template_present);
    assert_eq!(template.template_settings_count, 1);
    assert!(template.template_mappings_present);
    assert!(template
        .template_mapping
        .as_ref()
        .is_some_and(|mapping| mapping.compressed_bytes_len > 0));
    assert_eq!(template.template_aliases_count, 1);
    assert_eq!(
        template.template_aliases[0].alias,
        "fixture-composable-alias"
    );
    assert_eq!(template.component_templates_count, 1);
    assert_eq!(template.priority, Some(13));
    assert_eq!(template.version, Some(14));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_composable_index_template_data_stream_context_decodes_skeleton()
{
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_composable_index_template_data_stream_context")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 34);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-composable-index-template-data-stream-context"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.composable_index_templates_count, Some(1));
    let template = &metadata.composable_index_templates[0];
    assert_eq!(
        template.name,
        "fixture-composable-template-data-stream-context"
    );
    assert_eq!(
        template.index_patterns,
        vec!["fixture-compose-data-stream-*".to_string()]
    );
    assert!(template.data_stream_template_present);
    assert_eq!(
        template.data_stream_timestamp_field.as_deref(),
        Some("event_time")
    );
    assert!(template.context_present);
    assert_eq!(template.context_name.as_deref(), Some("fixture-context"));
    assert_eq!(template.context_version.as_deref(), Some("2"));
    assert_eq!(template.context_params_count, 1);
    assert_eq!(template.context_params[0].key, "fixture-context-param");
    assert_eq!(
        template.context_params[0].value.as_deref(),
        Some("fixture-context-value")
    );
    assert_eq!(template.priority, Some(15));
    assert_eq!(template.version, Some(16));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_metadata_mixed_templates_decodes_skeletons() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_metadata_mixed_templates")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 42);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-metadata-mixed-templates"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.templates_count, 1);
    assert_eq!(metadata.templates[0].name, "fixture-mixed-legacy-template");
    assert_eq!(
        metadata.templates[0].patterns,
        vec!["fixture-mixed-legacy-*".to_string()]
    );
    assert_eq!(metadata.custom_metadata_count, 3);
    assert_eq!(metadata.index_graveyard_tombstones_count, Some(0));
    assert_eq!(metadata.component_templates_count, Some(1));
    assert_eq!(
        metadata.component_templates[0].name,
        "fixture-mixed-component-template"
    );
    assert_eq!(metadata.component_templates[0].version, Some(20));
    assert_eq!(metadata.composable_index_templates_count, Some(1));
    let composable = &metadata.composable_index_templates[0];
    assert_eq!(composable.name, "fixture-mixed-composable-template");
    assert_eq!(
        composable.component_templates,
        vec!["fixture-mixed-component-template".to_string()]
    );
    assert_eq!(composable.priority, Some(21));
    assert_eq!(composable.version, Some(22));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_metadata_mixed_data_stream_decodes_skeletons() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_metadata_mixed_data_stream")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 43);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-metadata-mixed-data-stream"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 3);
    assert_eq!(metadata.index_graveyard_tombstones_count, Some(0));
    assert_eq!(metadata.data_streams_count, Some(1));
    assert_eq!(metadata.data_streams[0].name, "fixture-mixed-data-stream");
    assert_eq!(metadata.data_streams[0].timestamp_field, "event_time");
    assert_eq!(metadata.data_streams[0].backing_indices_count, 1);
    assert_eq!(metadata.composable_index_templates_count, Some(1));
    let template = &metadata.composable_index_templates[0];
    assert_eq!(template.name, "fixture-mixed-data-stream-template");
    assert_eq!(
        template.index_patterns,
        vec!["fixture-mixed-data-*".to_string()]
    );
    assert!(template.data_stream_template_present);
    assert_eq!(
        template.data_stream_timestamp_field.as_deref(),
        Some("event_time")
    );
    assert_eq!(template.priority, Some(23));
    assert_eq!(template.version, Some(24));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_data_stream_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_data_stream_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 35);
    assert_eq!(header.state_uuid, "fixture-state-with-data-stream-metadata");

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    assert_eq!(metadata.data_streams_count, Some(1));
    let data_stream = &metadata.data_streams[0];
    assert_eq!(data_stream.name, "fixture-data-stream");
    assert_eq!(data_stream.timestamp_field, "event_time");
    assert_eq!(data_stream.backing_indices_count, 1);
    assert_eq!(
        data_stream.backing_indices[0].name,
        ".ds-fixture-data-stream-000001"
    );
    assert_eq!(
        data_stream.backing_indices[0].uuid,
        "fixture-backing-index-uuid"
    );
    assert_eq!(data_stream.generation, 1);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_repositories_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_repositories_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 36);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-repositories-metadata"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    assert_eq!(metadata.repositories_count, Some(1));
    let repository = &metadata.repositories[0];
    assert_eq!(repository.name, "fixture-repo");
    assert_eq!(repository.repository_type, "fs");
    assert_eq!(repository.settings_count, 1);
    assert_eq!(repository.settings[0].key, "location");
    assert_eq!(
        repository.settings[0].value.as_deref(),
        Some("/tmp/fixture-repo")
    );
    assert_eq!(repository.generation, -2);
    assert_eq!(repository.pending_generation, -1);
    assert!(!repository.crypto_metadata_present);
    assert_eq!(repository.crypto_key_provider_name, None);
    assert_eq!(repository.crypto_key_provider_type, None);
    assert_eq!(repository.crypto_settings_count, 0);
    assert!(repository.crypto_settings.is_empty());
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_ingest_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_ingest_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 43);
    assert_eq!(header.state_uuid, "fixture-state-with-ingest-metadata");

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    assert_eq!(metadata.ingest_pipelines_count, Some(1));
    let pipeline = &metadata.ingest_pipelines[0];
    assert_eq!(pipeline.id, "fixture-pipeline");
    assert!(pipeline.config_len > 0);
    assert_eq!(pipeline.media_type, "application/json; charset=UTF-8");
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_search_pipeline_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_search_pipeline_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 44);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-search-pipeline-metadata"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    assert_eq!(metadata.search_pipelines_count, Some(1));
    let pipeline = &metadata.search_pipelines[0];
    assert_eq!(pipeline.id, "fixture-search-pipeline");
    assert!(pipeline.config_len > 0);
    assert_eq!(pipeline.media_type, "application/json; charset=UTF-8");
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_script_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_script_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 45);
    assert_eq!(header.state_uuid, "fixture-state-with-script-metadata");

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    assert_eq!(metadata.stored_scripts_count, Some(1));
    let script = &metadata.stored_scripts[0];
    assert_eq!(script.id, "fixture-script");
    assert_eq!(script.lang, "painless");
    assert!(script.source_len > 0);
    assert_eq!(script.options_count, 1);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_persistent_tasks_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_persistent_tasks_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 46);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-persistent-tasks-metadata"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    assert_eq!(metadata.persistent_tasks_count, Some(1));
    let task = &metadata.persistent_tasks[0];
    assert_eq!(task.map_key, "fixture-task");
    assert_eq!(task.id, "fixture-task");
    assert_eq!(task.allocation_id, 1);
    assert_eq!(task.task_name, "fixture-persistent-task");
    assert_eq!(task.params_name, "fixture-persistent-task");
    assert_eq!(
        task.fixture_params_marker.as_deref(),
        Some("fixture-persistent-payload")
    );
    assert_eq!(task.fixture_params_generation, Some(7));
    assert_eq!(task.state_name.as_deref(), Some("fixture-persistent-task"));
    assert_eq!(
        task.fixture_state_marker.as_deref(),
        Some("fixture-persistent-state")
    );
    assert_eq!(task.fixture_state_generation, Some(11));
    assert_eq!(task.executor_node.as_deref(), Some("fixture-node-id"));
    assert_eq!(task.assignment_explanation, "assigned for fixture");
    assert_eq!(task.allocation_id_on_last_status_update, Some(1));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_decommission_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_decommission_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 47);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-decommission-metadata"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    let decommission = metadata.decommission_attribute.unwrap();
    assert_eq!(decommission.attribute_name, "zone");
    assert_eq!(decommission.attribute_value, "zone-c");
    assert_eq!(decommission.status, "draining");
    assert_eq!(decommission.request_id, "fixture-decommission-request");
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_repositories_multi_decodes_name_order() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_repositories_multi")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 41);
    assert_eq!(header.state_uuid, "fixture-state-with-repositories-multi");

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.repositories_count, Some(2));
    let repository_names = metadata
        .repositories
        .iter()
        .map(|repository| repository.name.as_str())
        .collect::<Vec<_>>();
    assert_eq!(repository_names, vec!["fixture-repo-a", "fixture-repo-b"]);
    assert_eq!(metadata.repositories[0].repository_type, "fs");
    assert_eq!(metadata.repositories[1].repository_type, "url");
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_repository_workload_group_multi_decodes_settings() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_repository_workload_group_multi")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 42);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-repository-workload-group-multi"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.repositories_count, Some(2));
    assert_eq!(metadata.repositories[0].name, "fixture-rich-repo-a");
    assert_eq!(metadata.repositories[0].repository_type, "fs");
    assert_eq!(metadata.repositories[0].settings_count, 2);
    assert_eq!(metadata.repositories[0].settings[0].key, "compress");
    assert_eq!(
        metadata.repositories[0].settings[0].value.as_deref(),
        Some("true")
    );
    assert_eq!(metadata.repositories[0].settings[1].key, "location");
    assert_eq!(
        metadata.repositories[0].settings[1].value.as_deref(),
        Some("/tmp/fixture-rich-repo-a")
    );
    assert_eq!(metadata.repositories[1].name, "fixture-rich-repo-b");
    assert_eq!(metadata.repositories[1].repository_type, "url");
    assert_eq!(metadata.repositories[1].settings_count, 2);
    assert_eq!(metadata.repositories[1].settings[0].key, "readonly");
    assert_eq!(
        metadata.repositories[1].settings[0].value.as_deref(),
        Some("true")
    );
    assert_eq!(metadata.repositories[1].settings[1].key, "url");
    assert_eq!(
        metadata.repositories[1].settings[1].value.as_deref(),
        Some("file:/tmp/fixture-rich-repo-b")
    );

    assert_eq!(metadata.workload_groups_count, Some(2));
    let workload_a = &metadata.workload_groups[0];
    assert_eq!(workload_a.name, "fixture-rich-workload-a");
    assert_eq!(workload_a.id, "fixture-rich-workload-id-a");
    assert_eq!(workload_a.resource_limits_count, 2);
    assert_eq!(workload_a.resource_limits[0].key, "cpu");
    assert_eq!(workload_a.resource_limits[0].value.as_deref(), Some("0.5"));
    assert_eq!(workload_a.resource_limits[1].key, "memory");
    assert_eq!(workload_a.resource_limits[1].value.as_deref(), Some("0.25"));
    assert_eq!(workload_a.resiliency_mode.as_deref(), Some("enforced"));
    if workload_a.search_settings_count > 0 {
        assert_eq!(workload_a.search_settings_count, 1);
        assert_eq!(workload_a.search_settings[0].key, "timeout");
        assert_eq!(workload_a.search_settings[0].value.as_deref(), Some("10s"));
    }
    assert_eq!(workload_a.updated_at_millis, 345678);

    let workload_b = &metadata.workload_groups[1];
    assert_eq!(workload_b.name, "fixture-rich-workload-b");
    assert_eq!(workload_b.id, "fixture-rich-workload-id-b");
    assert_eq!(workload_b.resource_limits_count, 1);
    assert_eq!(workload_b.resource_limits[0].key, "cpu");
    assert_eq!(workload_b.resource_limits[0].value.as_deref(), Some("0.3"));
    assert_eq!(workload_b.resiliency_mode.as_deref(), Some("monitor"));
    if workload_b.search_settings_count > 0 {
        assert_eq!(workload_b.search_settings_count, 1);
        assert_eq!(workload_b.search_settings[0].key, "timeout");
        assert_eq!(workload_b.search_settings[0].value.as_deref(), Some("5s"));
    }
    assert_eq!(workload_b.updated_at_millis, 456789);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_repository_crypto_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_repository_crypto_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 40);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-repository-crypto-metadata"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.repositories_count, Some(1));
    let repository = &metadata.repositories[0];
    assert_eq!(repository.name, "fixture-crypto-repo");
    assert!(repository.crypto_metadata_present);
    assert_eq!(
        repository.crypto_key_provider_name.as_deref(),
        Some("fixture-key-provider")
    );
    assert_eq!(
        repository.crypto_key_provider_type.as_deref(),
        Some("aws-kms")
    );
    assert_eq!(repository.crypto_settings_count, 1);
    assert_eq!(repository.crypto_settings[0].key, "kms.key_arn");
    assert_eq!(
        repository.crypto_settings[0].value.as_deref(),
        Some("fixture-key-arn")
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_weighted_routing_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_weighted_routing_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 37);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-weighted-routing-metadata"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    let weighted_routing = metadata.weighted_routing.unwrap();
    assert_eq!(weighted_routing.awareness_attribute, "zone");
    assert_eq!(weighted_routing.weights_count, 1);
    assert_eq!(weighted_routing.weights[0].key, "zone-a");
    assert_eq!(weighted_routing.weights[0].value.as_deref(), Some("1"));
    assert_eq!(weighted_routing.version, 17);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_view_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_view_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 38);
    assert_eq!(header.state_uuid, "fixture-state-with-view-metadata");

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    assert_eq!(metadata.views_count, Some(1));
    let view = &metadata.views[0];
    assert_eq!(view.name, "fixture-view");
    assert_eq!(view.description.as_deref(), Some("fixture source"));
    assert_eq!(view.created_at, 123);
    assert_eq!(view.modified_at, 456);
    assert_eq!(view.target_index_patterns_count, 1);
    assert_eq!(
        view.target_index_patterns,
        vec!["fixture-view-*".to_string()]
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_workload_group_metadata_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_workload_group_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 39);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-workload-group-metadata"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 2);
    assert_eq!(metadata.workload_groups_count, Some(1));
    let workload_group = &metadata.workload_groups[0];
    assert_eq!(workload_group.name, "fixture-workload");
    assert_eq!(workload_group.id, "fixture-workload-id");
    assert_eq!(workload_group.resource_limits_count, 1);
    assert_eq!(workload_group.resource_limits[0].key, "cpu");
    assert_eq!(
        workload_group.resource_limits[0].value.as_deref(),
        Some("0.5")
    );
    assert_eq!(workload_group.resiliency_mode.as_deref(), Some("enforced"));
    assert_eq!(workload_group.updated_at_millis, 123456);
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_legacy_index_template_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_legacy_index_template")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 20);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-legacy-index-template"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.templates_count, 1);
    let template = &metadata.templates[0];
    assert_eq!(template.name, "fixture-template");
    assert_eq!(template.order, 3);
    assert_eq!(template.patterns, vec!["fixture-*".to_string()]);
    assert_eq!(template.settings_count, 1);
    assert_eq!(template.settings[0].key, "index.number_of_shards");
    assert_eq!(template.settings[0].value.as_deref(), Some("1"));
    assert_eq!(template.mappings_count, 0);
    assert!(template.mappings.is_empty());
    assert_eq!(template.aliases_count, 0);
    assert!(template.aliases.is_empty());
    assert_eq!(template.version, Some(7));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_legacy_index_template_mapping_alias_decodes_skeleton() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_legacy_index_template_mapping_alias")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 21);
    assert_eq!(
        header.state_uuid,
        "fixture-state-with-legacy-index-template-mapping-alias"
    );

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.templates_count, 1);
    let template = &metadata.templates[0];
    assert_eq!(template.name, "fixture-template-with-mapping-alias");
    assert_eq!(template.order, 4);
    assert_eq!(template.patterns, vec!["fixture-map-*".to_string()]);
    assert_eq!(template.settings_count, 1);
    assert_eq!(template.mappings_count, 1);
    assert_eq!(template.mappings[0].name, "_doc");
    assert!(template.mappings[0].compressed_bytes_len > 0);
    assert_eq!(template.aliases_count, 1);
    assert_eq!(template.aliases[0].alias, "fixture-alias");
    assert_eq!(template.aliases[0].filter, None);
    assert_eq!(template.aliases[0].index_routing, None);
    assert_eq!(template.aliases[0].search_routing, None);
    assert_eq!(template.aliases[0].write_index, None);
    assert_eq!(template.aliases[0].is_hidden, None);
    assert_eq!(template.version, Some(8));
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_response_with_misc_custom_metadata_decodes_skeletons() {
    let fixtures = fixtures();
    let response = ClusterStateResponsePrefix::read(Bytes::from(
        fixtures
            .get("cluster_state_response_misc_custom_metadata")
            .unwrap()
            .clone(),
    ))
    .unwrap();

    let header = response.state_header.unwrap();
    assert_eq!(header.version, 44);
    assert_eq!(header.state_uuid, "fixture-state-with-misc-custom-metadata");

    let metadata = response.metadata_prefix.unwrap();
    assert_eq!(metadata.custom_metadata_count, 5);
    assert_eq!(metadata.index_graveyard_tombstones_count, Some(0));
    assert_eq!(metadata.repositories_count, Some(1));
    assert_eq!(metadata.repositories[0].name, "fixture-aggregate-repo");
    let weighted_routing = metadata.weighted_routing.unwrap();
    assert_eq!(weighted_routing.awareness_attribute, "zone");
    assert_eq!(weighted_routing.weights[0].key, "zone-b");
    assert_eq!(weighted_routing.weights[0].value.as_deref(), Some("0.75"));
    assert_eq!(weighted_routing.version, 25);
    assert_eq!(metadata.views_count, Some(1));
    assert_eq!(metadata.views[0].name, "fixture-aggregate-view");
    assert_eq!(metadata.workload_groups_count, Some(1));
    assert_eq!(
        metadata.workload_groups[0].name,
        "fixture-aggregate-workload"
    );
    assert_eq!(metadata.workload_groups[0].resource_limits[0].key, "memory");
    assert_eq!(
        metadata.workload_groups[0].resource_limits[0]
            .value
            .as_deref(),
        Some("0.25")
    );
    assert_eq!(
        metadata.workload_groups[0].resiliency_mode.as_deref(),
        Some("monitor")
    );
    assert_eq!(response.remaining_state_bytes_after_prefix, 0);
}

#[test]
fn java_cluster_state_fixture_records_wire_version() {
    let fixtures = fixtures();
    let mut input = StreamInput::new(Bytes::from(
        fixtures
            .get("cluster_state_response_minimal_wire_version")
            .unwrap()
            .clone(),
    ));

    assert_eq!(input.read_vint().unwrap(), OPENSEARCH_3_7_0_TRANSPORT.id());
    assert_eq!(input.remaining(), 0);
}
