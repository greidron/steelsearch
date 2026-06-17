use bytes::{Bytes, BytesMut};
use os_cluster_state::{
    apply_publication_diff_and_ack, build_cluster_state_request_frame, read_cluster_blocks_prefix,
    read_cluster_state_header, read_cluster_state_tail_prefix, read_discovery_nodes_prefix,
    read_metadata_prefix, read_publication_cluster_state_diff, read_routing_table_prefix,
    ClusterState, ClusterStateRequest, ClusterStateResponsePrefix, ShardRoutingState,
    ShardRoutingStatePrefix,
};
use os_core::version::{Version, OPENSEARCH_3_7_0_TRANSPORT};
use os_node::{
    apply_gateway_metadata_commit_state_to_manifest,
    apply_gateway_metadata_state_to_manifest,
    bind_rest_http_listener, serve_rest_http_listener_until, validate_production_mode_request,
    collect_live_publication_acknowledgement_details, collect_live_publication_apply_details,
    ClusterCoordinationState, DevelopmentClusterNode, DevelopmentClusterView,
    DevelopmentCoordinationStatus, DiscoveryConfig, DiscoveryPeer, ElectionAttemptWindow,
    ElectionResult, ElectionScheduler, ElectionSchedulerConfig, ExtensionBoundaryRegistry,
    LiveTransportDiscoveryPeerProber, NodeInfo, PersistedClusterManagerTaskQueueState,
    PersistedGatewayState, PersistedPublicationState,
    ProductionMembershipState, ReleaseReadinessChecklist, RestServerConfig,
    SecurityBoundaryPolicy, SteelNode, load_gateway_state_manifest,
    persist_gateway_state_manifest,
};
use os_node_rest_core::parse_authentication_users_json;
use os_stream::StreamInput;
use os_transport::compression::decompress_deflate_body;
use os_transport::handshake::{build_tcp_handshake_request, build_transport_handshake_request};
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::io::{Read, Write};
use std::net::{IpAddr, Ipv4Addr, SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicBool, AtomicI64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

static SHUTDOWN_REQUESTED: AtomicBool = AtomicBool::new(false);
static TRANSPORT_REQUEST_SEQUENCE: AtomicI64 = AtomicI64::new(10_000);

fn now_epoch_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
}

#[derive(Clone, Debug)]
struct DevTransportIdentity {
    cluster_name: String,
    node_name: String,
    node_id: String,
    ephemeral_id: String,
    transport_address: SocketAddr,
    attributes: Vec<(String, String)>,
    roles: Vec<String>,
    seed_peer_identity: Option<InteropSeedPeerIdentityManifest>,
    seed_peer_identities: Vec<InteropSeedPeerIdentityManifest>,
    coordination_state: Arc<Mutex<DevTransportCoordinationState>>,
}

#[derive(Clone, Debug, Default)]
struct DevTransportCoordinationState {
    last_accepted_term: i64,
    last_accepted_version: i64,
    cluster_manager_node_id: Option<String>,
    non_self_publish_seen: bool,
    local_initializing_replicas: Vec<PublishedReplicaAssignment>,
    cached_cluster_state: Option<ClusterState>,
    last_cluster_state_refresh_at_ms: Option<u128>,
    initiated_peer_recoveries: BTreeSet<String>,
    cached_query_phase_response_bodies: BTreeMap<String, Vec<u8>>,
    cached_match_all_total_hits: BTreeMap<String, i64>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct PublishedReplicaAssignment {
    index_name: String,
    shard_id: i32,
    source_primary_node_id: Option<String>,
    source_primary_transport_address: Option<String>,
    local_allocation_id: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct PublishedShardRoutingSummary {
    index_name: String,
    shard_id: i32,
    primary: bool,
    state: String,
    current_node_id: Option<String>,
    relocating_node_id: Option<String>,
    allocation_id: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct GatewayManifestPaths {
    coordination_path: PathBuf,
    cluster_metadata_path: PathBuf,
    membership_path: PathBuf,
}

impl GatewayManifestPaths {
    fn for_data_path(data_path: &std::path::Path) -> Self {
        Self {
            coordination_path: data_path.join("gateway-state.json"),
            cluster_metadata_path: data_path.join("gateway-cluster-state.json"),
            membership_path: data_path.join("production-membership.json"),
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    install_shutdown_signal_handlers();
    let mut config = daemon_config_from_env_and_args()?;
    let transport_address = SocketAddr::new(config.transport_host, config.transport_port);
    let transport_listener = bind_transport_seed_listener(transport_address)?;
    eprintln!(
        "Steelsearch transport listener bound epoch_ms={} addr={}",
        now_epoch_ms(),
        transport_listener.local_addr()?
    );
    let listener = bind_rest_http_listener(SocketAddr::new(config.host, config.port))?;
    let address = listener.local_addr()?;
    config.port = address.port();
    config.transport_port = transport_listener.local_addr()?.port();
    let cluster_uuid = "steelsearch-dev-cluster-uuid";
    let gateway_paths = GatewayManifestPaths::for_data_path(&config.data_path);
    let gateway_manifest_path = gateway_paths.coordination_path.clone();
    let persisted_gateway_state = load_gateway_state_manifest(&gateway_manifest_path)?;
    let persisted_coordination_state = persisted_gateway_state
        .as_ref()
        .map(|state| state.coordination_state.clone());
    let persisted_task_queue_state = persisted_gateway_state
        .as_ref()
        .and_then(|state| state.task_queue_state.clone());
    let initial_cluster_view = restore_gateway_startup_cluster_view(
        &config,
        cluster_uuid,
        persisted_gateway_state.as_ref(),
    )?;
    let cluster_view = apply_development_coordination_with_persisted_state(
        initial_cluster_view,
        persisted_coordination_state,
        persisted_task_queue_state,
        Some(&gateway_manifest_path),
    );
    let _cluster_settings_runtime_route_table =
        os_node::cluster_settings_route_registration::CLUSTER_SETTINGS_ROUTE_REGISTRY_TABLE;
    let _cluster_settings_live_route_hook =
        os_node::cluster_settings_route_registration::CLUSTER_SETTINGS_ROUTE_REGISTRY_ENTRY.hook;
    let _cluster_settings_real_traffic_runtime_registration =
        os_node::cluster_settings_route_registration::CLUSTER_SETTINGS_RUNTIME_REGISTRATION_BODY;
    let _cluster_settings_real_traffic_dispatch_table =
        _cluster_settings_real_traffic_runtime_registration;
    let _cluster_settings_live_readback_activation =
        _cluster_settings_real_traffic_dispatch_table;
    let _cluster_settings_runtime_dispatch_table =
        _cluster_settings_live_readback_activation;
    let _create_index_runtime_route_table =
        os_node::create_index_route_registration::CREATE_INDEX_ROUTE_REGISTRY_TABLE;
    let _data_stream_runtime_route_table =
        os_node::data_stream_route_registration::DATA_STREAM_ROUTE_REGISTRY_TABLE;
    let _delete_index_runtime_route_table =
        os_node::delete_index_route_registration::DELETE_INDEX_ROUTE_REGISTRY_TABLE;
    let _get_index_runtime_route_table =
        os_node::get_index_route_registration::GET_INDEX_ROUTE_REGISTRY_TABLE;
    let _single_doc_delete_runtime_route_table =
        os_node::single_doc_delete_route_registration::DELETE_DOC_ROUTE_REGISTRY_TABLE;
    let _single_doc_delete_runtime_dispatch_table =
        os_node::single_doc_delete_route_registration::invoke_delete_doc_live_write
            as os_node::single_doc_delete_route_registration::SingleDocDeleteWriteHook;
    let _single_doc_get_runtime_route_table =
        os_node::single_doc_get_route_registration::GET_DOC_ROUTE_REGISTRY_TABLE;
    let _single_doc_get_runtime_dispatch_table =
        os_node::single_doc_get_route_registration::invoke_get_doc_live_read
            as os_node::single_doc_get_route_registration::SingleDocGetReadHook;
    let _single_doc_update_runtime_route_table =
        os_node::single_doc_update_route_registration::UPDATE_DOC_ROUTE_REGISTRY_TABLE;
    let _single_doc_update_runtime_dispatch_table =
        os_node::single_doc_update_route_registration::invoke_update_doc_live_write
            as os_node::single_doc_update_route_registration::SingleDocUpdateWriteHook;
    let _alias_read_runtime_route_table =
        os_node::alias_read_route_registration::ALIAS_READ_ROUTE_REGISTRY_TABLE;
    let _alias_mutation_runtime_route_table =
        os_node::alias_mutation_route_registration::ALIAS_MUTATION_ROUTE_REGISTRY_TABLE;
    let _bulk_runtime_route_table = os_node::bulk_route_registration::BULK_ROUTE_REGISTRY_TABLE;
    let _mapping_runtime_route_table =
        os_node::mapping_route_registration::MAPPING_ROUTE_REGISTRY_TABLE;
    let _legacy_template_runtime_route_table =
        os_node::legacy_template_route_registration::LEGACY_TEMPLATE_ROUTE_REGISTRY_TABLE;
    let _legacy_template_runtime_dispatch_table = (
        os_node::legacy_template_route_registration::invoke_legacy_template_live_readback
            as os_node::legacy_template_route_registration::LegacyTemplateReadbackHook,
        os_node::legacy_template_route_registration::invoke_legacy_template_live_mutation
            as os_node::legacy_template_route_registration::LegacyTemplateMutationHook,
    );
    let _rollover_runtime_route_table =
        os_node::rollover_route_registration::ROLLOVER_ROUTE_REGISTRY_TABLE;
    let _settings_runtime_route_table =
        os_node::settings_route_registration::SETTINGS_ROUTE_REGISTRY_TABLE;
    let _snapshot_repository_runtime_route_table =
        os_node::snapshot_repository_route_registration::SNAPSHOT_REPOSITORY_ROUTE_REGISTRY_TABLE;
    let _snapshot_repository_runtime_route_dispatch_table =
        os_node::snapshot_repository_route_registration::SNAPSHOT_REPOSITORY_RUNTIME_DISPATCH_TABLE;
    let _snapshot_repository_runtime_dispatch_table =
        os_node::snapshot_repository_route_registration::SNAPSHOT_REPOSITORY_RUNTIME_REGISTRATION_BODY;
    let _snapshot_repository_real_traffic_runtime_dispatch_table =
        _snapshot_repository_runtime_route_dispatch_table;
    let _snapshot_repository_handle_rest_request_call_site =
        os_node::snapshot_repository_route_registration::resolve_snapshot_repository_runtime_handler(
            "GET",
            "/_snapshot",
        );
    let _snapshot_repository_local_route_activation_harness =
        os_node::snapshot_repository_route_registration::run_snapshot_repository_local_route_activation(
            "GET",
            "/_snapshot",
            &serde_json::json!({}),
            None,
            &serde_json::json!({}),
            &serde_json::json!({}),
        );
    let _snapshot_repository_live_route_activation =
        (
            _snapshot_repository_real_traffic_runtime_dispatch_table,
            _snapshot_repository_handle_rest_request_call_site,
            _snapshot_repository_local_route_activation_harness,
        );
    let _snapshot_lifecycle_runtime_route_table =
        os_node::snapshot_lifecycle_route_registration::SNAPSHOT_LIFECYCLE_ROUTE_REGISTRY_TABLE;
    let _snapshot_lifecycle_runtime_dispatch_table =
        os_node::snapshot_lifecycle_route_registration::SNAPSHOT_LIFECYCLE_RUNTIME_REGISTRATION_BODY;
    let _snapshot_lifecycle_local_route_activation_harness =
        os_node::snapshot_lifecycle_route_registration::run_snapshot_lifecycle_local_route_activation(
            "GET",
            "/_snapshot/{repository}/{snapshot}",
            &serde_json::json!({}),
        );
    let _snapshot_cleanup_runtime_route_table =
        os_node::snapshot_cleanup_route_registration::SNAPSHOT_CLEANUP_ROUTE_REGISTRY_TABLE;
    let _snapshot_cleanup_runtime_dispatch_table =
        os_node::snapshot_cleanup_route_registration::SNAPSHOT_CLEANUP_RUNTIME_REGISTRATION_BODY;
    let _snapshot_cleanup_local_route_activation_harness =
        os_node::snapshot_cleanup_route_registration::run_snapshot_cleanup_local_route_activation(
            "DELETE",
            "/_snapshot/{repository}/{snapshot}",
            &serde_json::json!({}),
        );
    let _single_doc_post_runtime_route_table =
        os_node::single_doc_post_route_registration::POST_DOC_ROUTE_REGISTRY_TABLE;
    let _single_doc_post_runtime_dispatch_table =
        os_node::single_doc_post_route_registration::invoke_post_doc_live_write
            as os_node::single_doc_post_route_registration::SingleDocPostWriteHook;
    let _single_doc_put_runtime_route_table =
        os_node::single_doc_put_route_registration::PUT_DOC_ROUTE_REGISTRY_TABLE;
    let _single_doc_put_runtime_dispatch_table =
        os_node::single_doc_put_route_registration::invoke_put_doc_live_write
            as os_node::single_doc_put_route_registration::SingleDocPutWriteHook;
    let _template_runtime_route_table =
        os_node::template_route_registration::TEMPLATE_ROUTE_REGISTRY_TABLE;
    let _template_runtime_dispatch_table = (
        os_node::template_route_registration::invoke_component_template_live_readback
            as os_node::template_route_registration::TemplateReadbackHook,
        os_node::template_route_registration::invoke_index_template_live_readback
            as os_node::template_route_registration::TemplateReadbackHook,
        os_node::template_route_registration::invoke_component_template_live_mutation
            as os_node::template_route_registration::TemplateMutationHook,
        os_node::template_route_registration::invoke_index_template_live_mutation
            as os_node::template_route_registration::TemplateMutationHook,
    );
    let _cluster_allocation_explain_runtime_route_table =
        os_node::allocation_explain_route_registration::ALLOCATION_EXPLAIN_ROUTE_REGISTRY_TABLE;
    let _cluster_allocation_explain_runtime_dispatch_table =
        os_node::allocation_explain_route_registration::ALLOCATION_EXPLAIN_ROUTE_REGISTRY_TABLE;
    let _cluster_state_runtime_route_table =
        [os_node::cluster_state_route_registration::CLUSTER_STATE_ROUTE_REGISTRY_ENTRY];
    let _cluster_pending_tasks_runtime_route_table =
        os_node::pending_tasks_route_registration::PENDING_TASKS_ROUTE_REGISTRY_TABLE;
    let _stats_runtime_route_table = os_node::stats_route_registration::STATS_ROUTE_REGISTRY_TABLE;
    let _stats_runtime_dispatch_table = os_node::stats_route_registration::STATS_ROUTE_REGISTRY_TABLE;
    let _tasks_runtime_route_table = os_node::tasks_route_registration::TASKS_ROUTE_REGISTRY_TABLE;
    let _tasks_runtime_dispatch_table = os_node::tasks_route_registration::TASKS_ROUTE_REGISTRY_TABLE;
    let metadata_path = gateway_paths.cluster_metadata_path;
    restore_gateway_cluster_metadata_manifest(
        &metadata_path,
        load_gateway_state_manifest(&gateway_manifest_path)?.as_ref(),
    )?;
    let membership_path = gateway_paths.membership_path;
    let membership_state = production_membership_from_cluster_view(&cluster_view)?;

    let mut node = SteelNode::new(NodeInfo {
        name: config.node_name.clone(),
        version: OPENSEARCH_3_7_0_TRANSPORT,
    })
    .with_rest_config(RestServerConfig {
        bind_host: config.host.to_string(),
        port: config.port,
    })
    .with_extension_registry(effective_extension_registry(&config)?)
    .with_gateway_backed_development_metadata_store(
        metadata_path.clone(),
        gateway_manifest_path.clone(),
        cluster_view.clone(),
    )?
    .with_production_membership_store(membership_path.clone(), membership_state)?;

    node.register_default_dev_endpoints(config.cluster_name.clone(), cluster_uuid);
    node.register_development_cluster_endpoints(cluster_view);
    node.start_rest();
    let transport_capture_path = config.data_path.join("transport-seed-capture.json");
    let transport_identity = DevTransportIdentity {
        cluster_name: config.cluster_name.clone(),
        node_name: config.node_name.clone(),
        node_id: config.node_id.clone(),
        ephemeral_id: format!("{}-ephemeral", config.node_id),
        transport_address: SocketAddr::new(config.transport_host, config.transport_port),
        attributes: vec![(
            "shard_indexing_pressure_enabled".to_string(),
            "true".to_string(),
        )],
        roles: config.roles.clone(),
        seed_peer_identity: config.seed_peer_identity.clone(),
        seed_peer_identities: config.seed_peer_identities.clone(),
        coordination_state: Arc::new(Mutex::new(DevTransportCoordinationState::default())),
    };
    if config.mixed_java_native_transport_join_participation_enabled()
        && env::var("STEELSEARCH_DISABLE_PROACTIVE_JOIN")
            .ok()
            .as_deref()
            != Some("1")
    {
        spawn_proactive_seed_join_loop(transport_identity.clone());
    }
    serve_transport_seed_listener_until(transport_listener, transport_capture_path, transport_identity);

    eprintln!(
        "Steelsearch development daemon listening on http://{}",
        address
    );
    eprintln!(
        "node id={}, name={}, transport={}, roles={}, seed_hosts={}, data_path={}",
        config.node_id,
        config.node_name,
        SocketAddr::new(config.transport_host, config.transport_port),
        config.roles.join(","),
        if config.seed_hosts.is_empty() {
            "<none>".to_string()
        } else {
            config.seed_hosts.join(",")
        },
        config.data_path.display()
    );
    eprintln!(
        "gateway-backed development metadata manifest: {}",
        metadata_path.display()
    );
    eprintln!(
        "production membership manifest: {}",
        membership_path.display()
    );
    if config.mixed_java_native_transport_join_participation_enabled() {
        eprintln!(
            "development mode: mixed Java native transport join participation active; development_security={}, production security and full multi-node runtime are not complete",
            config.development_security_mode.as_str()
        );
    } else {
        eprintln!(
            "development mode: standalone HTTP compatibility surface only; development_security={}, production security and multi-node runtime are not complete",
            config.development_security_mode.as_str()
        );
    }
    if let Some(manifest_path) = config.extension_manifest_path.as_ref() {
        eprintln!("extension boundary manifest: {}", manifest_path.display());
    }

    serve_rest_http_listener_until(node, listener, || SHUTDOWN_REQUESTED.load(Ordering::SeqCst))?;
    Ok(())
}

fn bind_transport_seed_listener(address: SocketAddr) -> std::io::Result<std::net::TcpListener> {
    let listener = std::net::TcpListener::bind(address)?;
    listener.set_nonblocking(true)?;
    Ok(listener)
}

fn serve_transport_seed_listener_until(
    listener: std::net::TcpListener,
    capture_path: PathBuf,
    transport_identity: DevTransportIdentity,
) {
    let capture_write_lock = Arc::new(Mutex::new(()));
    thread::spawn(move || loop {
        if SHUTDOWN_REQUESTED.load(Ordering::SeqCst) {
            break;
        }
        match listener.accept() {
            Ok((stream, _peer_addr)) => {
                let capture_path = capture_path.clone();
                let transport_identity = transport_identity.clone();
                let capture_write_lock = Arc::clone(&capture_write_lock);
                thread::spawn(move || {
                    let _ = handle_transport_seed_connection(
                        stream,
                        &capture_path,
                        &transport_identity,
                        &capture_write_lock,
                    );
                });
            }
            Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                thread::sleep(Duration::from_millis(50));
            }
            Err(_) => break,
        }
    });
}

fn handle_transport_seed_connection(
    mut stream: std::net::TcpStream,
    capture_path: &std::path::Path,
    transport_identity: &DevTransportIdentity,
    capture_write_lock: &Arc<Mutex<()>>,
) -> std::io::Result<()> {
    let connection_started_at_ms = unix_time_ms();
    let pre_first_frame_timeout_ms = env::var("STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS")
        .ok()
        .and_then(|raw| raw.parse::<u64>().ok())
        .unwrap_or_else(|| transport_connection_hold_duration().as_millis() as u64);
    stream.set_read_timeout(Some(Duration::from_millis(pre_first_frame_timeout_ms)))?;
    let (header, body) = loop {
        match read_transport_seed_frame_detailed(&mut stream)? {
            TransportSeedFrameRead::Frame(frame) => break frame,
            TransportSeedFrameRead::Ping(header) => {
                let response = build_keepalive_ping_frame();
                stream.write_all(&response)?;
                stream.flush()?;
                let frame_at_ms = unix_time_ms();
                persist_transport_seed_capture(
                    capture_path,
                    stream.peer_addr().ok(),
                    connection_started_at_ms,
                    Some(frame_at_ms),
                    summarize_keepalive_ping_frame(&header),
                    None,
                    None,
                    None,
                    None,
                    Some(frame_at_ms),
                    Some(summarize_keepalive_ping_frame(&response)),
                    None,
                    Some("keepalive_ping".to_string()),
                    Some("keepalive_ping".to_string()),
                    Some(frame_at_ms),
                    None,
                    0,
                    capture_write_lock,
                )?;
                continue;
            }
            TransportSeedFrameRead::TimedOut => {
                let event_at_ms = unix_time_ms();
                persist_transport_seed_capture(
                    capture_path,
                    stream.peer_addr().ok(),
                    connection_started_at_ms,
                    None,
                    serde_json::json!({ "pre_first_frame": true }),
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    Some(connection_started_at_ms),
                    Some("timed_out_before_first_frame".to_string()),
                    Some("idle_timeout".to_string()),
                    Some(event_at_ms),
                    None,
                    0,
                    capture_write_lock,
                )?;
                continue;
            }
            TransportSeedFrameRead::Eof => {
                let event_at_ms = unix_time_ms();
                persist_transport_seed_capture(
                    capture_path,
                    stream.peer_addr().ok(),
                    connection_started_at_ms,
                    None,
                    serde_json::json!({ "pre_first_frame": true }),
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    Some(connection_started_at_ms),
                    Some("remote_eof_before_first_frame".to_string()),
                    Some("remote_eof".to_string()),
                    Some(event_at_ms),
                    None,
                    0,
                    capture_write_lock,
                )?;
                return Ok(());
            }
        }
    };
    let first_frame_received_at_ms = unix_time_ms();
    let first_frame = summarize_transport_seed_frame(&header, &body);
    let mut follow_up_frame = None;
    let mut follow_up_frame_received_at_ms = None;
    let mut post_follow_up_frame = None;
    let mut post_follow_up_frame_received_at_ms = None;
    let mut response_frame = None;
    let mut response_frame_sent_at_ms = None;
    let mut hold_open_started_at_ms = None;
    let mut first_post_response_event = None;
    let mut connection_end = None;
    let mut connection_end_at_ms = None;
    let mut proactive_keepalive_sent_at_ms = None;
    let mut proactive_keepalive_count = 0_u32;
    if body.len() < 17 {
        persist_transport_seed_capture(
            capture_path,
            stream.peer_addr().ok(),
            connection_started_at_ms,
            Some(first_frame_received_at_ms),
            first_frame,
            follow_up_frame_received_at_ms,
            follow_up_frame,
            post_follow_up_frame_received_at_ms,
            post_follow_up_frame,
            response_frame_sent_at_ms,
            response_frame,
            hold_open_started_at_ms,
            first_post_response_event,
            connection_end,
            connection_end_at_ms,
            proactive_keepalive_sent_at_ms,
            proactive_keepalive_count,
            capture_write_lock,
        )?;
        return Ok(());
    }
    let request_id = i64::from_be_bytes([
        body[0], body[1], body[2], body[3], body[4], body[5], body[6], body[7],
    ]);
    let status = body[8];
    let header_version_id = u32::from_be_bytes([body[9], body[10], body[11], body[12]]);
    let is_request = status & 0x01 == 0;
    let is_handshake = status & 0x08 != 0;
    let action_hint = transport_frame_action_hint(&body);
    let normalized_action_hint = action_hint
        .as_deref()
        .map(|action| action.strip_suffix("[n]").unwrap_or(action));
    if is_request && is_handshake {
        eprintln!(
            "steelsearch_tcp_handshake_response_stage=before_write request_id={} header_version_id={}",
            request_id, header_version_id
        );
        let response = build_tcp_handshake_response(
            request_id,
            header_version_id,
            OPENSEARCH_3_7_0_TRANSPORT.id() as u32,
        );
        response_frame = summarize_transport_response_frame(&response);
        stream.write_all(&response)?;
        eprintln!(
            "steelsearch_tcp_handshake_response_stage=after_write request_id={} bytes={}",
            request_id,
            response.len()
        );
        stream.flush()?;
        eprintln!(
            "steelsearch_tcp_handshake_response_stage=after_flush request_id={}",
            request_id
        );
        response_frame_sent_at_ms = Some(unix_time_ms());
        let immediate_proactive_ping_after_response = env::var(
            "STEELSEARCH_TCP_HANDSHAKE_IMMEDIATE_PROACTIVE_PING_AFTER_RESPONSE",
        )
        .ok()
        .map(|value| value == "1")
        .unwrap_or(false);
        if immediate_proactive_ping_after_response {
            let ping = build_keepalive_ping_frame();
            stream.write_all(&ping)?;
            stream.flush()?;
            proactive_keepalive_count += 1;
            if proactive_keepalive_sent_at_ms.is_none() {
                proactive_keepalive_sent_at_ms = Some(unix_time_ms());
            }
            eprintln!(
                "steelsearch_tcp_handshake_response_stage=immediate_proactive_ping_after_response request_id={}",
                request_id
            );
        }
        let direct_hold_open_after_tcp_response = env::var(
            "STEELSEARCH_TCP_HANDSHAKE_DIRECT_HOLD_OPEN_AFTER_RESPONSE",
        )
        .ok()
        .map(|value| value == "1")
        .unwrap_or(false);
        if direct_hold_open_after_tcp_response {
            eprintln!(
                "steelsearch_tcp_handshake_response_stage=direct_hold_open_after_response request_id={}",
                request_id
            );
            hold_transport_channel_open(
                &mut stream,
                transport_identity,
                &mut post_follow_up_frame,
                &mut post_follow_up_frame_received_at_ms,
                true,
                &mut proactive_keepalive_sent_at_ms,
                &mut proactive_keepalive_count,
                transport_connection_hold_duration(),
                &mut hold_open_started_at_ms,
                &mut first_post_response_event,
                &mut connection_end,
                &mut connection_end_at_ms,
            )?;
        } else {
            stream.set_read_timeout(Some(Duration::from_millis(400)))?;
            if let Some((follow_up_header, follow_up_body)) = read_transport_seed_frame(&mut stream)? {
                eprintln!(
                    "steelsearch_tcp_handshake_response_stage=follow_up_received request_id={} action_hint={:?}",
                    request_id,
                    transport_frame_action_hint(&follow_up_body)
                );
                follow_up_frame_received_at_ms = Some(unix_time_ms());
                follow_up_frame = Some(summarize_transport_seed_frame(
                    &follow_up_header,
                    &follow_up_body,
                ));
                if transport_frame_action_hint(&follow_up_body).as_deref()
                    == Some("internal:transport/handshake")
                {
                    let follow_up_request_id = i64::from_be_bytes([
                        follow_up_body[0],
                        follow_up_body[1],
                        follow_up_body[2],
                        follow_up_body[3],
                        follow_up_body[4],
                        follow_up_body[5],
                        follow_up_body[6],
                        follow_up_body[7],
                    ]);
                    let follow_up_header_version_id = u32::from_be_bytes([
                        follow_up_body[9],
                        follow_up_body[10],
                        follow_up_body[11],
                        follow_up_body[12],
                    ]);
                    let response = build_transport_handshake_identity_response(
                        follow_up_request_id,
                        follow_up_header_version_id,
                        transport_identity,
                    );
                    response_frame = summarize_transport_response_frame_for_action(
                        &response,
                        Some("internal:transport/handshake"),
                    );
                    stream.write_all(&response)?;
                    stream.flush()?;
                    response_frame_sent_at_ms = Some(unix_time_ms());
                    hold_transport_channel_open(
                        &mut stream,
                        transport_identity,
                        &mut post_follow_up_frame,
                        &mut post_follow_up_frame_received_at_ms,
                        true,
                        &mut proactive_keepalive_sent_at_ms,
                        &mut proactive_keepalive_count,
                        transport_connection_hold_duration(),
                        &mut hold_open_started_at_ms,
                        &mut first_post_response_event,
                        &mut connection_end,
                        &mut connection_end_at_ms,
                    )?;
                }
            } else {
                eprintln!(
                    "steelsearch_tcp_handshake_response_stage=no_follow_up_within_400ms request_id={}",
                    request_id
                );
                hold_transport_channel_open(
                    &mut stream,
                    transport_identity,
                    &mut post_follow_up_frame,
                    &mut post_follow_up_frame_received_at_ms,
                    true,
                    &mut proactive_keepalive_sent_at_ms,
                    &mut proactive_keepalive_count,
                    transport_connection_hold_duration(),
                    &mut hold_open_started_at_ms,
                    &mut first_post_response_event,
                    &mut connection_end,
                    &mut connection_end_at_ms,
                )?;
            }
        }
    } else if is_request && action_hint.as_deref() == Some("internal:transport/handshake") {
        let response = build_transport_handshake_identity_response(
            request_id,
            header_version_id,
            transport_identity,
        );
        response_frame = summarize_transport_response_frame_for_action(
            &response,
            Some("internal:transport/handshake"),
        );
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request && action_hint.as_deref() == Some("internal:discovery/request_peers") {
        let response = build_request_peers_response(request_id, header_version_id);
        response_frame = summarize_transport_response_frame(&response);
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request && action_hint.as_deref() == Some("internal:cluster/request_pre_vote") {
        let response = build_pre_vote_response(request_id, header_version_id, 0, 0, 0);
        response_frame = summarize_transport_response_frame(&response);
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request
        && normalized_action_hint == Some("internal:cluster/nodes/indices/shard/store/batch")
    {
        let response = build_empty_shard_store_batch_response(
            request_id,
            header_version_id,
            transport_identity,
        );
        response_frame = summarize_transport_response_frame_for_action(
            &response,
            Some("internal:cluster/nodes/indices/shard/store/batch[n]"),
        );
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request && normalized_action_hint == Some("cluster:monitor/nodes/stats") {
        let response = build_empty_nodes_stats_response(
            request_id,
            header_version_id,
            transport_identity,
        );
        response_frame = summarize_transport_response_frame_for_action(
            &response,
            Some("cluster:monitor/nodes/stats[n]"),
        );
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request && normalized_action_hint == Some("cluster:monitor/nodes/info") {
        let response = build_nodes_info_response(
            request_id,
            header_version_id,
            transport_identity,
        );
        response_frame = summarize_transport_response_frame_for_action(
            &response,
            Some("cluster:monitor/nodes/info[n]"),
        );
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request && normalized_action_hint == Some("indices:monitor/stats") {
        let response = build_empty_indices_stats_node_response(
            request_id,
            header_version_id,
            transport_identity,
        );
        response_frame = summarize_transport_response_frame_for_action(
            &response,
            Some("indices:monitor/stats[n]"),
        );
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request && normalized_action_hint == Some("indices:monitor/recovery") {
        let response = build_empty_indices_recovery_node_response(
            request_id,
            header_version_id,
            transport_identity,
        );
        response_frame = summarize_transport_response_frame_for_action(
            &response,
            Some("indices:monitor/recovery[n]"),
        );
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request
        && matches!(
            action_hint.as_deref(),
            Some("indices:admin/seq_no/retention_lease_background_sync[r]")
                | Some("indices:admin/seq_no/retention_lease_background_sync")
        )
    {
        let response = build_replication_replica_response(request_id, header_version_id, 0, 0);
        response_frame = summarize_transport_response_frame(&response);
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request
        && matches!(
            action_hint.as_deref(),
            Some("internal:index/shard/recovery/start_recovery")
                |
            Some("internal:index/shard/recovery/filesInfo")
                | Some("internal:index/shard/recovery/file_chunk")
                | Some("internal:index/shard/recovery/clean_files")
                | Some("internal:index/shard/recovery/prepare_translog")
                | Some("internal:index/shard/recovery/finalize")
                | Some("internal:index/shard/recovery/handoff_primary_context")
        )
    {
        if action_hint.as_deref() == Some("internal:index/shard/recovery/start_recovery") {
            if let Ok(peer_addr) = stream.peer_addr() {
                maybe_complete_source_side_recovery(peer_addr, &body, header_version_id);
            }
        }
        let response = if action_hint.as_deref() == Some("internal:index/shard/recovery/start_recovery") {
            build_java_recovery_response(request_id, header_version_id)
        } else {
            build_empty_transport_response(request_id, header_version_id)
        };
        response_frame = summarize_transport_response_frame(&response);
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request && action_hint.as_deref() == Some("internal:index/shard/recovery/translog_ops") {
        let response = build_recovery_translog_operations_response(request_id, header_version_id, 0);
        response_frame = summarize_transport_response_frame(&response);
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request && action_hint.as_deref() == Some("internal:cluster/coordination/publish_state") {
        let publish_state_started = std::time::Instant::now();
        let decode_started = std::time::Instant::now();
        let cached_cluster_state = transport_identity
            .coordination_state
            .lock()
            .ok()
            .and_then(|state| state.cached_cluster_state.clone());
        let (mut local_initializing_replicas, mut applied_cluster_state) =
            match decode_local_initializing_replicas_from_publish_state(
                &body,
                &transport_identity.node_id,
                Version::from_id(header_version_id as i32),
                cached_cluster_state.as_ref(),
                Some(transport_identity),
            ) {
                Ok(value) => value,
                Err(error) => {
                    eprintln!("steelsearch_publish_state_decode_error={error}");
                    Default::default()
                }
            };
        if local_initializing_replicas.is_empty() {
            if let Ok((
                refreshed_cluster_state,
                refreshed_assignments,
                refreshed_routing_summaries,
            )) = refresh_local_initializing_replicas_from_seed_peers(
                transport_identity,
                header_version_id,
                Version::from_id(header_version_id as i32),
            ) {
                eprintln!(
                    "steelsearch_publish_state_refresh_local_initializing_replicas={:?}",
                    refreshed_assignments
                );
                eprintln!(
                    "steelsearch_publish_state_refresh_relevant_routings={:?}",
                    refreshed_routing_summaries
                );
                local_initializing_replicas = refreshed_assignments;
                applied_cluster_state = Some(refreshed_cluster_state);
            }
        }
        let routing_summaries = applied_cluster_state
            .as_ref()
            .map(summarize_relevant_shard_routings_from_cluster_state)
            .unwrap_or_default();
        eprintln!(
            "steelsearch_publish_state_decode_ms={}",
            decode_started.elapsed().as_millis()
        );
        let (
            join_last_accepted_term,
            join_last_accepted_version,
            cached_cluster_manager_node_id,
        ) = transport_identity
            .coordination_state
            .lock()
            .map(|state| {
                (
                    state.last_accepted_term,
                    state.last_accepted_version,
                    state.cluster_manager_node_id.clone(),
                )
            })
            .unwrap_or((0, 0, None));
        let term = applied_cluster_state
            .as_ref()
            .map(|state| state.metadata.coordination.term)
            .unwrap_or(join_last_accepted_term);
        let version = applied_cluster_state
            .as_ref()
            .map(|state| state.header.version)
            .unwrap_or(join_last_accepted_version);
        let cluster_manager_node_id = applied_cluster_state
            .as_ref()
            .and_then(|state| state.discovery_nodes.cluster_manager_node_id.clone())
            .or(cached_cluster_manager_node_id);
        if let Ok(mut coordination_state) = transport_identity.coordination_state.lock() {
            coordination_state.last_accepted_term = term;
            coordination_state.last_accepted_version = version;
            if let Some(node_id) = cluster_manager_node_id.clone() {
                coordination_state.cluster_manager_node_id = Some(node_id);
            }
            coordination_state.non_self_publish_seen = true;
            coordination_state.local_initializing_replicas =
                local_initializing_replicas.clone();
            if let Some(cluster_state) = applied_cluster_state.clone() {
                coordination_state.cached_cluster_state = Some(cluster_state);
            }
        }
        maybe_start_peer_recoveries(
            transport_identity,
            header_version_id,
            &local_initializing_replicas,
            applied_cluster_state.as_ref(),
        );
        eprintln!(
            "steelsearch_publish_state_local_initializing_replicas={:?}",
            local_initializing_replicas
        );
        eprintln!(
            "steelsearch_publish_state_relevant_routings={:?}",
            routing_summaries
        );
        let build_started = std::time::Instant::now();
        let response = build_publish_with_join_response(
            request_id,
            header_version_id,
            term,
            version,
            transport_identity,
            join_last_accepted_term,
            join_last_accepted_version,
            cluster_manager_node_id.as_deref(),
        );
        eprintln!(
            "steelsearch_publish_state_build_ms={}",
            build_started.elapsed().as_millis()
        );
        response_frame = summarize_transport_response_frame_for_action(
            &response,
            Some("internal:cluster/coordination/publish_state"),
        );
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        eprintln!(
            "steelsearch_publish_state_total_before_write_ms={}",
            publish_state_started.elapsed().as_millis()
        );
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request
        && action_hint.as_deref() == Some("internal:coordination/fault_detection/follower_check")
    {
        if let Ok(mut coordination_state) = transport_identity.coordination_state.lock() {
            coordination_state.non_self_publish_seen = true;
        }
        maybe_refresh_local_initializing_replicas_from_seed_peers(
            transport_identity,
            header_version_id,
            Version::from_id(header_version_id as i32),
        );
        let reusable_follower_check = transport_identity
            .coordination_state
            .lock()
            .map(|state| state.non_self_publish_seen)
            .unwrap_or(false);
        let response = build_empty_transport_response(request_id, header_version_id);
        response_frame = summarize_transport_response_frame(&response);
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            reusable_follower_check,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request && action_hint.as_deref() == Some("cluster:monitor/nodes/liveness") {
        let response = build_liveness_response(request_id, header_version_id, transport_identity);
        response_frame = summarize_transport_response_frame_for_action(
            &response,
            Some("cluster:monitor/nodes/liveness"),
        );
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request && action_hint.as_deref() == Some("internal:cluster/coordination/commit_state") {
        let response = build_empty_transport_response(request_id, header_version_id);
        response_frame = summarize_transport_response_frame(&response);
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            false,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request
        && matches!(
            action_hint.as_deref(),
            Some("internal:cluster/coordination/join")
                | Some("internal:cluster/coordination/join/validate")
                | Some("internal:cluster/coordination/join/validate_compressed")
        )
    {
        let response = build_empty_transport_response(request_id, header_version_id);
        response_frame = summarize_transport_response_frame(&response);
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            false,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request && action_hint.as_deref() == Some("internal:cluster/coordination/start_join") {
        maybe_send_join_request_to_seed_peer(header_version_id, &body, transport_identity);
        let response = build_empty_transport_response(request_id, header_version_id);
        response_frame = summarize_transport_response_frame(&response);
        stream.write_all(&response)?;
        stream.flush()?;
        response_frame_sent_at_ms = Some(unix_time_ms());
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request && action_hint.as_deref() == Some("indices:data/read/search[phase/query]") {
        if let Some(response) = maybe_build_query_phase_response(request_id, &body, transport_identity) {
            response_frame = summarize_transport_response_frame(&response);
            stream.write_all(&response)?;
            stream.flush()?;
            response_frame_sent_at_ms = Some(unix_time_ms());
        } else {
            eprintln!(
                "steelsearch_first_frame_query_phase_response_missing request_id={} header_version_id={}",
                request_id, header_version_id
            );
        }
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    } else if is_request {
        eprintln!(
            "steelsearch_first_frame_unhandled request_id={} action_hint={:?} header_version_id={}",
            request_id, action_hint, header_version_id
        );
        hold_transport_channel_open(
            &mut stream,
            transport_identity,
            &mut post_follow_up_frame,
            &mut post_follow_up_frame_received_at_ms,
            true,
            &mut proactive_keepalive_sent_at_ms,
            &mut proactive_keepalive_count,
            transport_connection_hold_duration(),
            &mut hold_open_started_at_ms,
            &mut first_post_response_event,
            &mut connection_end,
            &mut connection_end_at_ms,
        )?;
    }
    persist_transport_seed_capture(
        capture_path,
        stream.peer_addr().ok(),
        connection_started_at_ms,
        Some(first_frame_received_at_ms),
        first_frame,
        follow_up_frame_received_at_ms,
        follow_up_frame,
        post_follow_up_frame_received_at_ms,
        post_follow_up_frame,
        response_frame_sent_at_ms,
        response_frame,
        hold_open_started_at_ms,
        first_post_response_event,
        connection_end,
        connection_end_at_ms,
        proactive_keepalive_sent_at_ms,
        proactive_keepalive_count,
        capture_write_lock,
    )?;
    Ok(())
}

enum TransportSeedFrameRead {
    Frame(([u8; 6], Vec<u8>)),
    Ping([u8; 6]),
    TimedOut,
    Eof,
}

fn read_transport_seed_frame(
    stream: &mut std::net::TcpStream,
) -> std::io::Result<Option<([u8; 6], Vec<u8>)>> {
    match read_transport_seed_frame_detailed(stream)? {
        TransportSeedFrameRead::Frame(frame) => Ok(Some(frame)),
        TransportSeedFrameRead::Ping(_) => Ok(Some((build_keepalive_ping_frame(), Vec::new()))),
        TransportSeedFrameRead::TimedOut | TransportSeedFrameRead::Eof => Ok(None),
    }
}

fn read_transport_seed_frame_detailed(
    stream: &mut std::net::TcpStream,
) -> std::io::Result<TransportSeedFrameRead> {
    let mut header = [0_u8; 6];
    match stream.read_exact(&mut header) {
        Ok(()) => {}
        Err(error) if matches!(error.kind(), std::io::ErrorKind::WouldBlock | std::io::ErrorKind::TimedOut) => {
            return Ok(TransportSeedFrameRead::TimedOut);
        }
        Err(error) if error.kind() == std::io::ErrorKind::UnexpectedEof => {
            return Ok(TransportSeedFrameRead::Eof);
        }
        Err(error) => return Err(error),
    }
    if &header[..2] != b"ES" {
        return Ok(TransportSeedFrameRead::Eof);
    }
    let raw_message_length = i32::from_be_bytes([header[2], header[3], header[4], header[5]]);
    if raw_message_length == -1 {
        return Ok(TransportSeedFrameRead::Ping(header));
    }
    if raw_message_length <= 0 {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            format!("invalid transport message length: {raw_message_length}"),
        ));
    }
    let message_length = raw_message_length as usize;
    let mut body = vec![0_u8; message_length];
    stream.read_exact(&mut body)?;
    Ok(TransportSeedFrameRead::Frame((header, body)))
}

fn summarize_transport_seed_frame(header: &[u8; 6], body: &[u8]) -> serde_json::Value {
    let mut summary = serde_json::json!({
        "marker_prefix": std::str::from_utf8(&header[..2]).unwrap_or(""),
        "message_length": u32::from_be_bytes([header[2], header[3], header[4], header[5]]),
        "body_len": body.len(),
        "body_prefix_hex": hex_prefix(body, 96),
    });
    if body.len() >= 13 {
        let request_id = i64::from_be_bytes([
            body[0], body[1], body[2], body[3], body[4], body[5], body[6], body[7],
        ]);
        let status = body[8];
        let version_id = u32::from_be_bytes([body[9], body[10], body[11], body[12]]);
        summary["request_id"] = serde_json::json!(request_id);
        summary["status"] = serde_json::json!(status);
        summary["is_request"] = serde_json::json!(status & 0x01 == 0);
        summary["is_response"] = serde_json::json!(status & 0x01 != 0);
        summary["is_handshake"] = serde_json::json!(status & 0x08 != 0);
        summary["version_id"] = serde_json::json!(version_id);
    }
    if let Some(action_hint) = transport_frame_action_hint(body) {
        if matches!(
            action_hint.as_str(),
            "internal:coordination/fault_detection/follower_check"
                | "internal:cluster/coordination/publish_state"
                | "internal:cluster/coordination/start_join"
                | "internal:index/shard/recovery/start_recovery"
                | "internal:index/shard/recovery/prepare_translog"
                | "internal:index/shard/recovery/translog_ops"
                | "internal:index/shard/recovery/finalize"
        ) {
            summary["body_hex"] = serde_json::json!(
                body.iter().map(|byte| format!("{byte:02x}")).collect::<String>()
            );
        }
        summary["action_hint"] = serde_json::json!(action_hint);
    }
    summary
}

fn transport_frame_action_hint(body: &[u8]) -> Option<String> {
    let needles: [&[u8]; 3] = [b"internal:", b"cluster:", b"indices:"];
    let start = needles
        .iter()
        .filter_map(|needle| body.windows(needle.len()).position(|window| window == *needle))
        .min()?;
    let tail = &body[start..];
    let end = tail
        .iter()
        .position(|byte| !byte.is_ascii_graphic() || *byte == 0)
        .unwrap_or(tail.len());
    std::str::from_utf8(&tail[..end]).ok().map(str::to_string)
}

fn persist_transport_seed_capture(
    capture_path: &std::path::Path,
    peer_addr: Option<SocketAddr>,
    connection_started_at_ms: u128,
    first_frame_received_at_ms: Option<u128>,
    first_frame: serde_json::Value,
    follow_up_frame_received_at_ms: Option<u128>,
    follow_up_frame: Option<serde_json::Value>,
    post_follow_up_frame_received_at_ms: Option<u128>,
    post_follow_up_frame: Option<serde_json::Value>,
    response_frame_sent_at_ms: Option<u128>,
    response_frame: Option<serde_json::Value>,
    hold_open_started_at_ms: Option<u128>,
    first_post_response_event: Option<String>,
    connection_end: Option<String>,
    connection_end_at_ms: Option<u128>,
    proactive_keepalive_sent_at_ms: Option<u128>,
    proactive_keepalive_count: u32,
    capture_write_lock: &Arc<Mutex<()>>,
) -> std::io::Result<()> {
    let _guard = capture_write_lock.lock().map_err(|error| {
        std::io::Error::new(
            std::io::ErrorKind::Other,
            format!("transport seed capture lock poisoned: {error}"),
        )
    })?;
    let mut captures = if capture_path.exists() {
        let existing = fs::read_to_string(capture_path)?;
        serde_json::from_str::<Vec<serde_json::Value>>(&existing).unwrap_or_default()
    } else {
        Vec::new()
    };
    captures.push(serde_json::json!({
        "peer_addr": peer_addr.map(|addr| addr.to_string()),
        "connection_started_at_ms": connection_started_at_ms,
        "first_frame_received_at_ms": first_frame_received_at_ms,
        "first_frame": first_frame,
        "follow_up_frame_received_at_ms": follow_up_frame_received_at_ms,
        "follow_up_frame": follow_up_frame,
        "post_follow_up_frame_received_at_ms": post_follow_up_frame_received_at_ms,
        "post_follow_up_frame": post_follow_up_frame,
        "response_frame_sent_at_ms": response_frame_sent_at_ms,
        "response_frame": response_frame,
        "hold_open_started_at_ms": hold_open_started_at_ms,
        "first_post_response_event": first_post_response_event,
        "connection_end": connection_end,
        "connection_end_at_ms": connection_end_at_ms,
        "proactive_keepalive_sent_at_ms": proactive_keepalive_sent_at_ms,
        "proactive_keepalive_count": proactive_keepalive_count,
    }));
    if let Some(parent) = capture_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(
        capture_path,
        serde_json::to_string_pretty(&captures)
            .map(|serialized| format!("{serialized}\n"))
            .unwrap_or_else(|_| "[]\n".to_string()),
    )
}

fn build_keepalive_ping_frame() -> [u8; 6] {
    [b'E', b'S', 0xff, 0xff, 0xff, 0xff]
}

fn summarize_keepalive_ping_frame(header: &[u8; 6]) -> serde_json::Value {
    serde_json::json!({
        "marker_prefix": std::str::from_utf8(&header[..2]).unwrap_or(""),
        "message_length": i32::from_be_bytes([header[2], header[3], header[4], header[5]]),
        "is_keepalive_ping": true,
    })
}

fn build_transport_handshake_identity_response(
    request_id: i64,
    header_version_id: u32,
    transport_identity: &DevTransportIdentity,
) -> Vec<u8> {
    let mut payload = Vec::new();
    write_bool(&mut payload, true);
    write_string(&mut payload, &transport_identity.node_name);
    write_string(&mut payload, &transport_identity.node_id);
    write_string(&mut payload, &transport_identity.ephemeral_id);
    let host = transport_identity.transport_address.ip().to_string();
    write_string(&mut payload, &host);
    write_string(&mut payload, &host);
    write_transport_address(&mut payload, transport_identity.transport_address);
    write_bool(&mut payload, false);
    write_transport_vint_to(&mut payload, transport_identity.attributes.len() as u32);
    for (key, value) in &transport_identity.attributes {
        write_string(&mut payload, key);
        write_string(&mut payload, value);
    }
    write_transport_vint_to(&mut payload, transport_identity.roles.len() as u32);
    for role in &transport_identity.roles {
        let (abbrev, can_contain_data) = transport_role_wire_compat(role);
        write_string(&mut payload, role);
        write_string(&mut payload, abbrev);
        write_bool(&mut payload, can_contain_data);
    }
    write_transport_vint_to(&mut payload, OPENSEARCH_3_7_0_TRANSPORT.id() as u32);
    write_string(&mut payload, &transport_identity.cluster_name);
    write_transport_vint_to(&mut payload, OPENSEARCH_3_7_0_TRANSPORT.id() as u32);

    build_transport_response_frame(request_id, header_version_id, payload)
}

fn build_request_peers_response(request_id: i64, header_version_id: u32) -> Vec<u8> {
    let mut payload = Vec::new();
    write_bool(&mut payload, false);
    write_transport_vint_to(&mut payload, 0);
    payload.extend_from_slice(&0_i64.to_be_bytes());
    build_transport_response_frame(request_id, header_version_id, payload)
}

fn build_pre_vote_response(
    request_id: i64,
    header_version_id: u32,
    current_term: i64,
    last_accepted_term: i64,
    last_accepted_version: i64,
) -> Vec<u8> {
    let mut payload = Vec::new();
    payload.extend_from_slice(&current_term.to_be_bytes());
    payload.extend_from_slice(&last_accepted_term.to_be_bytes());
    payload.extend_from_slice(&last_accepted_version.to_be_bytes());
    build_transport_response_frame(request_id, header_version_id, payload)
}

fn resolve_join_target_peer_identity<'a>(
    transport_identity: &'a DevTransportIdentity,
    cluster_manager_node_id: Option<&str>,
) -> Option<&'a InteropSeedPeerIdentityManifest> {
    if let Some(node_id) = cluster_manager_node_id {
        if let Some(identity) = transport_identity
            .seed_peer_identities
            .iter()
            .find(|identity| identity.discovery_node.id == node_id)
        {
            return Some(identity);
        }
    }
    transport_identity.seed_peer_identity.as_ref()
}

fn build_publish_with_join_response(
    request_id: i64,
    header_version_id: u32,
    term: i64,
    version: i64,
    transport_identity: &DevTransportIdentity,
    join_last_accepted_term: i64,
    join_last_accepted_version: i64,
    cluster_manager_node_id: Option<&str>,
) -> Vec<u8> {
    let join_target_peer_identity =
        resolve_join_target_peer_identity(transport_identity, cluster_manager_node_id);
    if let Some(payload) = try_build_java_publish_with_join_response(
        term,
        version,
        transport_identity,
        join_last_accepted_term,
        join_last_accepted_version,
        join_target_peer_identity,
    ) {
        return build_transport_response_frame(request_id, header_version_id, payload);
    }
    let mut payload = Vec::new();
    payload.extend_from_slice(&term.to_be_bytes());
    payload.extend_from_slice(&version.to_be_bytes());
    if let Some(seed_peer_identity) = join_target_peer_identity {
        write_bool(&mut payload, true);
        write_discovery_node_wire(
            &mut payload,
            &transport_identity.node_name,
            &transport_identity.node_id,
            &transport_identity.ephemeral_id,
            &transport_identity.transport_address.ip().to_string(),
            &transport_identity.transport_address.ip().to_string(),
            transport_identity.transport_address,
            &transport_identity.attributes,
            &transport_identity.roles,
            OPENSEARCH_3_7_0_TRANSPORT.id() as u32,
        );
        let target_transport_address: SocketAddr = seed_peer_identity
            .discovery_node
            .transport_address
            .parse()
            .expect("validated transport address");
        write_discovery_node_wire(
            &mut payload,
            &seed_peer_identity.discovery_node.name,
            &seed_peer_identity.discovery_node.id,
            &seed_peer_identity.discovery_node.ephemeral_id,
            &seed_peer_identity.discovery_node.host_name,
            &seed_peer_identity.discovery_node.host_address,
            target_transport_address,
            &[],
            &seed_peer_identity.discovery_node.roles,
            seed_peer_identity.discovery_node.version_id,
        );
        payload.extend_from_slice(&term.to_be_bytes());
        payload.extend_from_slice(&join_last_accepted_term.to_be_bytes());
        payload.extend_from_slice(&join_last_accepted_version.to_be_bytes());
    } else {
        write_bool(&mut payload, false);
    }
    build_transport_response_frame(request_id, header_version_id, payload)
}

fn try_build_java_publish_with_join_response(
    term: i64,
    version: i64,
    transport_identity: &DevTransportIdentity,
    join_last_accepted_term: i64,
    join_last_accepted_version: i64,
    join_target_peer_identity: Option<&InteropSeedPeerIdentityManifest>,
) -> Option<Vec<u8>> {
    let seed_peer_identity = join_target_peer_identity?;
    let script_path = env::current_dir()
        .ok()?
        .join("tools/build_java_publish_with_join_response.sh");
    let local_roles = transport_identity.roles.join(",");
    let seed_roles = seed_peer_identity.discovery_node.roles.join(",");
    let output = Command::new("bash")
        .arg(script_path)
        .arg("--term")
        .arg(term.to_string())
        .arg("--version")
        .arg(version.to_string())
        .arg("--last-accepted-term")
        .arg(join_last_accepted_term.to_string())
        .arg("--last-accepted-version")
        .arg(join_last_accepted_version.to_string())
        .arg("--local-name")
        .arg(&transport_identity.node_name)
        .arg("--local-id")
        .arg(&transport_identity.node_id)
        .arg("--local-ephemeral-id")
        .arg(&transport_identity.ephemeral_id)
        .arg("--local-host")
        .arg(transport_identity.transport_address.ip().to_string())
        .arg("--local-host-address")
        .arg(transport_identity.transport_address.ip().to_string())
        .arg("--local-transport-address")
        .arg(transport_identity.transport_address.to_string())
        .arg("--local-roles")
        .arg(local_roles)
        .arg("--seed-name")
        .arg(&seed_peer_identity.discovery_node.name)
        .arg("--seed-id")
        .arg(&seed_peer_identity.discovery_node.id)
        .arg("--seed-ephemeral-id")
        .arg(&seed_peer_identity.discovery_node.ephemeral_id)
        .arg("--seed-host")
        .arg(&seed_peer_identity.discovery_node.host_name)
        .arg("--seed-host-address")
        .arg(&seed_peer_identity.discovery_node.host_address)
        .arg("--seed-transport-address")
        .arg(&seed_peer_identity.discovery_node.transport_address)
        .arg("--seed-roles")
        .arg(seed_roles)
        .arg("--seed-version-id")
        .arg(seed_peer_identity.discovery_node.version_id.to_string())
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    decode_hex_bytes(std::str::from_utf8(&output.stdout).ok()?.trim())
}

fn decode_hex_bytes(hex: &str) -> Option<Vec<u8>> {
    if hex.len() % 2 != 0 {
        return None;
    }
    let mut bytes = Vec::with_capacity(hex.len() / 2);
    let mut idx = 0;
    while idx < hex.len() {
        let byte = u8::from_str_radix(&hex[idx..idx + 2], 16).ok()?;
        bytes.push(byte);
        idx += 2;
    }
    Some(bytes)
}

fn build_java_start_recovery_request_payload(
    assignment: &PublishedReplicaAssignment,
    cluster_state: &ClusterState,
    transport_identity: &DevTransportIdentity,
    recovery_id: i64,
) -> Option<Vec<u8>> {
    let source_node_id = assignment.source_primary_node_id.as_ref()?;
    let source_node = cluster_state
        .discovery_nodes
        .nodes
        .iter()
        .find(|node| &node.id == source_node_id)?;
    let index_metadata = cluster_state
        .metadata
        .index_metadata
        .iter()
        .find(|index| index.name == assignment.index_name)?;
    let index_uuid = index_metadata.index_uuid.as_ref()?;
    let local_allocation_id = assignment.local_allocation_id.as_ref()?;
    let source_roles = source_node
        .roles
        .iter()
        .map(|role| role.name.as_str())
        .collect::<Vec<_>>()
        .join(",");
    let target_roles = transport_identity.roles.join(",");
    let source_transport_address = source_node
        .stream_address
        .as_ref()
        .unwrap_or(&source_node.address);
    let script_path = env::current_dir()
        .ok()?
        .join("tools/build_java_start_recovery_request.sh");
    let output = Command::new("bash")
        .arg(script_path)
        .arg("--index-name")
        .arg(&assignment.index_name)
        .arg("--index-uuid")
        .arg(index_uuid)
        .arg("--shard-id")
        .arg(assignment.shard_id.to_string())
        .arg("--target-allocation-id")
        .arg(local_allocation_id)
        .arg("--recovery-id")
        .arg(recovery_id.to_string())
        .arg("--starting-seq-no")
        .arg("-2")
        .arg("--primary-relocation")
        .arg("false")
        .arg("--source-name")
        .arg(&source_node.name)
        .arg("--source-id")
        .arg(&source_node.id)
        .arg("--source-ephemeral-id")
        .arg(&source_node.ephemeral_id)
        .arg("--source-host")
        .arg(&source_node.host_name)
        .arg("--source-host-address")
        .arg(&source_node.host_address)
        .arg("--source-transport-address")
        .arg(format!("{}:{}", source_transport_address.ip, source_transport_address.port))
        .arg("--source-roles")
        .arg(source_roles)
        .arg("--source-version-id")
        .arg(source_node.version.to_string())
        .arg("--target-name")
        .arg(&transport_identity.node_name)
        .arg("--target-id")
        .arg(&transport_identity.node_id)
        .arg("--target-ephemeral-id")
        .arg(&transport_identity.ephemeral_id)
        .arg("--target-host")
        .arg(transport_identity.transport_address.ip().to_string())
        .arg("--target-host-address")
        .arg(transport_identity.transport_address.ip().to_string())
        .arg("--target-transport-address")
        .arg(transport_identity.transport_address.to_string())
        .arg("--target-roles")
        .arg(target_roles)
        .arg("--target-version-id")
        .arg(OPENSEARCH_3_7_0_TRANSPORT.id().to_string())
        .output()
        .ok()?;
    if !output.status.success() {
        eprintln!(
            "steelsearch_start_recovery_payload_builder_failed status={} stderr={}",
            output.status,
            String::from_utf8_lossy(&output.stderr)
        );
        return None;
    }
    decode_hex_bytes(std::str::from_utf8(&output.stdout).ok()?.trim())
}

fn build_java_shard_started_request_payload(
    assignment: &PublishedReplicaAssignment,
    cluster_state: &ClusterState,
    primary_term: i64,
    message: &str,
) -> Option<Vec<u8>> {
    let index_metadata = cluster_state
        .metadata
        .index_metadata
        .iter()
        .find(|index| index.name == assignment.index_name)?;
    let index_uuid = index_metadata.index_uuid.as_ref()?;
    let local_allocation_id = assignment.local_allocation_id.as_ref()?;
    let script_path = env::current_dir()
        .ok()?
        .join("tools/build_java_shard_started_request.sh");
    let output = Command::new("bash")
        .arg(script_path)
        .arg("--index-name")
        .arg(&assignment.index_name)
        .arg("--index-uuid")
        .arg(index_uuid)
        .arg("--shard-id")
        .arg(assignment.shard_id.to_string())
        .arg("--allocation-id")
        .arg(local_allocation_id)
        .arg("--primary-term")
        .arg(primary_term.to_string())
        .arg("--message")
        .arg(message)
        .output()
        .ok()?;
    if !output.status.success() {
        eprintln!(
            "steelsearch_shard_started_payload_builder_failed status={} stderr={}",
            output.status,
            String::from_utf8_lossy(&output.stderr)
        );
        return None;
    }
    decode_hex_bytes(std::str::from_utf8(&output.stdout).ok()?.trim())
}

fn maybe_send_shard_started(
    cluster_state: &ClusterState,
    assignment: &PublishedReplicaAssignment,
    header_version_id: u32,
) {
    let Some(cluster_manager_node_id) = cluster_state.discovery_nodes.cluster_manager_node_id.as_ref()
    else {
        return;
    };
    let Some(cluster_manager_node) = cluster_state
        .discovery_nodes
        .nodes
        .iter()
        .find(|node| &node.id == cluster_manager_node_id)
    else {
        return;
    };
    let cluster_manager_address = cluster_manager_node
        .stream_address
        .as_ref()
        .unwrap_or(&cluster_manager_node.address);
    let target_transport_address =
        SocketAddr::from((cluster_manager_address.ip, cluster_manager_address.port as u16));
    let request_id = TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let Some(payload) = build_java_shard_started_request_payload(
        assignment,
        cluster_state,
        0,
        "steelsearch post-recovery shard started",
    ) else {
        eprintln!(
            "steelsearch_shard_started_payload_missing index={} shard={}",
            assignment.index_name, assignment.shard_id
        );
        return;
    };
    let frame = build_transport_request_frame(
        request_id,
        header_version_id,
        "internal:cluster/shard/started",
        payload,
    );
    eprintln!(
        "steelsearch_shard_started_send index={} shard={} request_id={} cluster_manager={}",
        assignment.index_name,
        assignment.shard_id,
        request_id,
        target_transport_address
    );
    thread::spawn(move || {
        if let Err(error) = send_transport_request_and_hold_for_response(
            target_transport_address,
            request_id,
            &frame,
            Duration::from_secs(30),
        ) {
            eprintln!(
                "steelsearch_shard_started_send_error request_id={} cluster_manager={} error={}",
                request_id, target_transport_address, error
            );
        } else {
            eprintln!(
                "steelsearch_shard_started_response_received request_id={} cluster_manager={}",
                request_id, target_transport_address
            );
        }
    });
}

fn maybe_start_peer_recoveries(
    transport_identity: &DevTransportIdentity,
    header_version_id: u32,
    local_initializing_replicas: &[PublishedReplicaAssignment],
    cluster_state: Option<&ClusterState>,
) {
    let Some(cluster_state) = cluster_state else {
        return;
    };
    for assignment in local_initializing_replicas {
        let Some(source_transport_address) = assignment.source_primary_transport_address.as_ref() else {
            continue;
        };
        let Some(local_allocation_id) = assignment.local_allocation_id.as_ref() else {
            continue;
        };
        let recovery_key =
            format!("{}:{}:{local_allocation_id}", assignment.index_name, assignment.shard_id);
        let should_start = transport_identity
            .coordination_state
            .lock()
            .map(|mut state| state.initiated_peer_recoveries.insert(recovery_key.clone()))
            .unwrap_or(false);
        if !should_start {
            continue;
        }
        let Ok(target_transport_address) = source_transport_address.parse::<SocketAddr>() else {
            eprintln!(
                "steelsearch_start_recovery_invalid_source_transport address={}",
                source_transport_address
            );
            continue;
        };
        let recovery_id = TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let request_id = TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let Some(payload) = build_java_start_recovery_request_payload(
            assignment,
            cluster_state,
            transport_identity,
            recovery_id,
        ) else {
            eprintln!(
                "steelsearch_start_recovery_payload_missing index={} shard={}",
                assignment.index_name, assignment.shard_id
            );
            continue;
        };
        let frame = build_transport_request_frame(
            request_id,
            header_version_id,
            "internal:index/shard/recovery/start_recovery",
            payload,
        );
        let assignment = assignment.clone();
        let cluster_state = cluster_state.clone();
        eprintln!(
            "steelsearch_start_recovery_send index={} shard={} request_id={} recovery_id={} source={}",
            assignment.index_name,
            assignment.shard_id,
            request_id,
            recovery_id,
            target_transport_address
        );
        thread::spawn(move || {
            if let Err(error) = send_transport_request_and_hold_for_response(
                target_transport_address,
                request_id,
                &frame,
                Duration::from_secs(5),
            ) {
                eprintln!(
                    "steelsearch_start_recovery_send_error request_id={} source={} error={}",
                    request_id, target_transport_address, error
                );
            } else {
                eprintln!(
                    "steelsearch_start_recovery_response_received request_id={} source={}",
                    request_id, target_transport_address
                );
                maybe_send_shard_started(
                    &cluster_state,
                    &assignment,
                    header_version_id,
                );
            }
        });
    }
}

fn query_phase_cache_key(index_name: &str, shard_id: i32) -> String {
    format!("{index_name}:{shard_id}")
}

fn lookup_seed_peer_http_address(
    transport_identity: &DevTransportIdentity,
    node_id: &str,
) -> Option<String> {
    transport_identity
        .seed_peer_identities
        .iter()
        .find(|peer| peer.discovery_node.id == node_id)
        .and_then(|peer| peer.discovery_node.http_address.clone())
}

fn fetch_count_via_http(http_address: &str, index_name: &str) -> Result<i64, String> {
    let target = format!("{http_address}");
    let mut stream = TcpStream::connect(target.as_str())
        .map_err(|error| format!("http connect failed: {error}"))?;
    stream
        .set_read_timeout(Some(Duration::from_secs(5)))
        .map_err(|error| format!("http set_read_timeout failed: {error}"))?;
    stream
        .set_write_timeout(Some(Duration::from_secs(5)))
        .map_err(|error| format!("http set_write_timeout failed: {error}"))?;
    let request = format!(
        "GET /{}/_count HTTP/1.1\r\nHost: {}\r\nConnection: close\r\nAccept: application/json\r\n\r\n",
        index_name, http_address
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|error| format!("http write failed: {error}"))?;
    stream
        .flush()
        .map_err(|error| format!("http flush failed: {error}"))?;
    let mut raw = Vec::new();
    stream
        .read_to_end(&mut raw)
        .map_err(|error| format!("http read failed: {error}"))?;
    let text = String::from_utf8_lossy(&raw);
    let (_, body) = text
        .split_once("\r\n\r\n")
        .ok_or_else(|| "http response missing header delimiter".to_string())?;
    let parsed: serde_json::Value =
        serde_json::from_str(body).map_err(|error| format!("http json decode failed: {error}"))?;
    parsed
        .get("count")
        .and_then(|value| value.as_i64())
        .ok_or_else(|| format!("http count missing in response: {parsed}"))
}

fn maybe_refresh_cached_match_all_total_hits(
    transport_identity: &DevTransportIdentity,
    cluster_state: &ClusterState,
) {
    let Some(assignment) = resolve_local_query_phase_assignment_from_cluster_state(
        cluster_state,
        transport_identity,
    ) else {
        return;
    };
    let Some(source_primary_node_id) = assignment.source_primary_node_id.as_deref() else {
        return;
    };
    let Some(http_address) = lookup_seed_peer_http_address(transport_identity, source_primary_node_id) else {
        return;
    };
    let cache_key = query_phase_cache_key(&assignment.index_name, assignment.shard_id);
    match fetch_count_via_http(&http_address, &assignment.index_name) {
        Ok(total_hits) => {
            if let Ok(mut coordination_state) = transport_identity.coordination_state.lock() {
                coordination_state
                    .cached_match_all_total_hits
                    .insert(cache_key, total_hits);
            }
        }
        Err(error) => {
            eprintln!(
                "steelsearch_query_phase_count_refresh_error node_id={} index={} error={}",
                source_primary_node_id, assignment.index_name, error
            );
        }
    }
}

fn build_java_query_phase_result_body(
    transport_identity: &DevTransportIdentity,
    index_name: &str,
    index_uuid: &str,
    shard_id: i32,
    total_hits: i64,
) -> Option<Vec<u8>> {
    let output = Command::new("bash")
        .arg("tools/build_java_query_phase_result.sh")
        .arg("--local-node-id")
        .arg(&transport_identity.node_id)
        .arg("--index-name")
        .arg(index_name)
        .arg("--index-uuid")
        .arg(index_uuid)
        .arg("--shard-id")
        .arg(shard_id.to_string())
        .arg("--total-hits")
        .arg(total_hits.to_string())
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let hex = String::from_utf8(output.stdout).ok()?;
    hex_to_bytes(hex.trim())
}

fn hex_to_bytes(hex: &str) -> Option<Vec<u8>> {
    if hex.len() % 2 != 0 {
        return None;
    }
    let mut bytes = Vec::with_capacity(hex.len() / 2);
    let mut offset = 0;
    while offset < hex.len() {
        bytes.push(u8::from_str_radix(&hex[offset..offset + 2], 16).ok()?);
        offset += 2;
    }
    Some(bytes)
}

fn build_transport_frame_from_body(body: &[u8]) -> Vec<u8> {
    let mut frame = Vec::with_capacity(6 + body.len());
    frame.extend_from_slice(b"ES");
    frame.extend_from_slice(&(body.len() as u32).to_be_bytes());
    frame.extend_from_slice(body);
    frame
}

fn rewrite_transport_body_request_id(body: &[u8], request_id: i64) -> Vec<u8> {
    let mut rewritten = body.to_vec();
    if rewritten.len() >= 8 {
        rewritten[..8].copy_from_slice(&request_id.to_be_bytes());
    }
    rewritten
}

fn resolve_local_query_phase_assignment_from_cluster_state(
    cluster_state: &ClusterState,
    transport_identity: &DevTransportIdentity,
) -> Option<PublishedReplicaAssignment> {
    let local_shard = cluster_state
        .routing_table
        .indices
        .iter()
        .flat_map(|index| {
            index.shards.iter().flat_map(move |shard| {
                shard.shard_routings.iter().filter_map(move |routing| {
                    (routing.current_node_id.as_deref() == Some(transport_identity.node_id.as_str())
                        && matches!(
                            routing.state,
                            ShardRoutingState::Initializing | ShardRoutingState::Started
                        ))
                    .then_some((index, shard, routing))
                })
            })
        })
        .find(|(_, _, routing)| !routing.primary)
        .or_else(|| {
            cluster_state
                .routing_table
                .indices
                .iter()
                .flat_map(|index| {
                    index.shards.iter().flat_map(move |shard| {
                        shard.shard_routings.iter().filter_map(move |routing| {
                            (routing.current_node_id.as_deref()
                                == Some(transport_identity.node_id.as_str())
                                && matches!(
                                    routing.state,
                                    ShardRoutingState::Initializing | ShardRoutingState::Started
                                ))
                            .then_some((index, shard, routing))
                        })
                    })
                })
                .find(|(_, _, routing)| routing.primary)
        })?;
    let (index, shard, local_routing) = local_shard;
    let source_primary = shard.shard_routings.iter().find(|routing| {
        routing.primary
            && routing.current_node_id.as_deref() != Some(transport_identity.node_id.as_str())
            && matches!(
                routing.state,
                ShardRoutingState::Initializing | ShardRoutingState::Started
            )
    });
    let source_primary_node_id = source_primary.and_then(|routing| routing.current_node_id.clone());
    let source_primary_transport_address = source_primary_node_id.as_ref().and_then(|source_primary_node_id| {
        cluster_state
            .discovery_nodes
            .nodes
            .iter()
            .find(|node| node.id == *source_primary_node_id)
            .map(|node| {
                let address = node.stream_address.as_ref().unwrap_or(&node.address);
                format!("{}:{}", address.ip, address.port)
            })
    });
    Some(PublishedReplicaAssignment {
        index_name: index.index_name.clone(),
        shard_id: shard.shard_id,
        source_primary_node_id,
        source_primary_transport_address,
        local_allocation_id: local_routing.allocation_id.as_ref().map(|allocation_id| allocation_id.id.clone()),
    })
}

fn resolve_local_query_phase_assignment(
    transport_identity: &DevTransportIdentity,
) -> Option<PublishedReplicaAssignment> {
    let cluster_state = transport_identity
        .coordination_state
        .lock()
        .ok()
        .and_then(|state| state.cached_cluster_state.clone())?;
    resolve_local_query_phase_assignment_from_cluster_state(&cluster_state, transport_identity)
}

fn send_transport_request_and_capture_response_body(
    target_transport_address: SocketAddr,
    request_id: i64,
    frame: &[u8],
    hold_for: Duration,
) -> std::io::Result<Option<Vec<u8>>> {
    let mut stream = TcpStream::connect_timeout(&target_transport_address, Duration::from_secs(2))?;
    stream.set_read_timeout(Some(Duration::from_secs(1)))?;
    stream.set_write_timeout(Some(Duration::from_secs(5)))?;
    perform_transport_connection_handshake(
        &mut stream,
        request_id,
        OPENSEARCH_3_7_0_TRANSPORT.id() as u32,
    )?;
    stream.write_all(frame)?;
    stream.flush()?;
    let started = std::time::Instant::now();
    while started.elapsed() < hold_for && !SHUTDOWN_REQUESTED.load(Ordering::SeqCst) {
        match read_transport_seed_frame_detailed(&mut stream)? {
            TransportSeedFrameRead::Frame((_header, body)) => {
                if body.len() < 13 {
                    continue;
                }
                let response_request_id = i64::from_be_bytes([
                    body[0], body[1], body[2], body[3], body[4], body[5], body[6], body[7],
                ]);
                let status = body[8];
                if response_request_id == request_id && status & 0x01 != 0 {
                    return Ok(Some(body));
                }
            }
            TransportSeedFrameRead::Ping(_header) => {
                let response = build_keepalive_ping_frame();
                stream.write_all(&response)?;
                stream.flush()?;
            }
            TransportSeedFrameRead::TimedOut => continue,
            TransportSeedFrameRead::Eof => return Ok(None),
        }
    }
    Ok(None)
}

fn maybe_build_query_phase_response(
    request_id: i64,
    body: &[u8],
    transport_identity: &DevTransportIdentity,
) -> Option<Vec<u8>> {
    let cached_assignment = resolve_local_query_phase_assignment(transport_identity)?;
    let cache_key = query_phase_cache_key(&cached_assignment.index_name, cached_assignment.shard_id);
    if let Some(cached_response_body) = transport_identity
        .coordination_state
        .lock()
        .ok()
        .and_then(|state| state.cached_query_phase_response_bodies.get(&cache_key).cloned())
    {
        return Some(build_transport_frame_from_body(
            &rewrite_transport_body_request_id(&cached_response_body, request_id),
        ));
    }

    if cached_assignment.source_primary_transport_address.is_none() {
        let cluster_state = transport_identity
            .coordination_state
            .lock()
            .ok()
            .and_then(|state| state.cached_cluster_state.clone())?;
        let index_uuid = cluster_state
            .metadata
            .index_metadata
            .iter()
            .find(|index| index.name == cached_assignment.index_name)
            .and_then(|index| index.index_uuid.clone())?;
        let total_hits = transport_identity
            .coordination_state
            .lock()
            .ok()
            .and_then(|state| state.cached_match_all_total_hits.get(&cache_key).copied())?;
        let body = build_java_query_phase_result_body(
            transport_identity,
            &cached_assignment.index_name,
            &index_uuid,
            cached_assignment.shard_id,
            total_hits,
        )?;
        return Some(build_transport_frame_from_body(
            &rewrite_transport_body_request_id(&body, request_id),
        ));
    }

    let source_transport_address = cached_assignment
        .source_primary_transport_address
        .as_ref()?
        .parse::<SocketAddr>()
        .ok()?;
    let forwarded_request_id = TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let forwarded_body = rewrite_transport_body_request_id(body, forwarded_request_id);
    let forwarded_frame = build_transport_frame_from_body(&forwarded_body);
    let response_body = send_transport_request_and_capture_response_body(
        source_transport_address,
        forwarded_request_id,
        &forwarded_frame,
        Duration::from_secs(20),
    )
    .ok()??;

    if let Ok(mut coordination_state) = transport_identity.coordination_state.lock() {
        coordination_state
            .cached_query_phase_response_bodies
            .insert(cache_key, response_body.clone());
    }

    Some(build_transport_frame_from_body(
        &rewrite_transport_body_request_id(&response_body, request_id),
    ))
}

fn build_empty_transport_response(request_id: i64, header_version_id: u32) -> Vec<u8> {
    build_transport_response_frame(request_id, header_version_id, Vec::new())
}

fn build_recovery_translog_operations_response(
    request_id: i64,
    header_version_id: u32,
    local_checkpoint: i64,
) -> Vec<u8> {
    let mut payload = Vec::new();
    write_transport_zlong_to(&mut payload, local_checkpoint);
    build_transport_response_frame(request_id, header_version_id, payload)
}

fn build_java_recovery_response(request_id: i64, header_version_id: u32) -> Vec<u8> {
    let script_path = env::current_dir()
        .ok()
        .map(|cwd| cwd.join("tools/build_java_recovery_response.sh"));
    if let Some(script_path) = script_path {
        if let Ok(output) = Command::new("bash").arg(script_path).output() {
            if output.status.success() {
                if let Ok(hex) = std::str::from_utf8(&output.stdout) {
                    if let Some(body) = decode_hex_bytes(hex.trim()) {
                        return build_transport_response_frame(request_id, header_version_id, body);
                    }
                }
            }
        }
    }
    build_empty_transport_response(request_id, header_version_id)
}

#[derive(serde::Deserialize)]
struct ParsedStartRecoveryRequest {
    recovery_id: i64,
    index_name: String,
    index_uuid: String,
    shard_id: i32,
    starting_seq_no: i64,
    target_transport_address: String,
}

fn transport_request_payload_offset(request_body: &[u8]) -> Option<usize> {
    if request_body.len() < 17 {
        return None;
    }
    let variable_header_size = u32::from_be_bytes([
        request_body[13],
        request_body[14],
        request_body[15],
        request_body[16],
    ]) as usize;
    let payload_offset = 17 + variable_header_size;
    if request_body.len() < payload_offset {
        return None;
    }
    Some(payload_offset)
}

fn extract_wrapped_transport_request_payload(request_body: &[u8]) -> Option<Vec<u8>> {
    let payload_offset = transport_request_payload_offset(request_body)?;
    unwrap_bytes_transport_request_payload(&request_body[payload_offset..])
        .ok()
        .map(|bytes| bytes.to_vec())
}

fn parse_java_start_recovery_request(
    request_body: &[u8],
    header_version_id: u32,
) -> Option<ParsedStartRecoveryRequest> {
    let script_path = env::current_dir()
        .ok()?
        .join("tools/parse_java_start_recovery_request.sh");

    let mut candidates = Vec::new();
    if let Some(payload) = extract_wrapped_transport_request_payload(request_body) {
        if !payload.is_empty() {
            candidates.push(("wrapped_bytes", payload));
        }
    }
    if let Some(payload_offset) = transport_request_payload_offset(request_body) {
        let direct_tail = request_body[payload_offset..].to_vec();
        if !direct_tail.is_empty()
            && !candidates.iter().any(|(_, existing)| *existing == direct_tail)
        {
            candidates.push(("direct_tail", direct_tail));
        }
    }

    for (kind, payload) in candidates {
        let payload_hex = payload
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>();
        let output = Command::new("bash")
            .arg(&script_path)
            .arg("--payload-hex")
            .arg(payload_hex)
            .arg("--version-id")
            .arg(header_version_id.to_string())
            .output()
            .ok()?;
        if output.status.success() {
            return serde_json::from_slice::<ParsedStartRecoveryRequest>(&output.stdout).ok();
        }
        eprintln!(
            "steelsearch_source_recovery_parse_script_failed kind={} status={} stderr={}",
            kind,
            output.status,
            String::from_utf8_lossy(&output.stderr)
        );
    }
    None
}

fn build_java_prepare_translog_request_payload(
    request: &ParsedStartRecoveryRequest,
    request_seq_no: i64,
) -> Option<Vec<u8>> {
    let script_path = env::current_dir()
        .ok()?
        .join("tools/build_java_prepare_translog_request.sh");
    let output = Command::new("bash")
        .arg(script_path)
        .arg("--recovery-id")
        .arg(request.recovery_id.to_string())
        .arg("--request-seq-no")
        .arg(request_seq_no.to_string())
        .arg("--index-name")
        .arg(&request.index_name)
        .arg("--index-uuid")
        .arg(&request.index_uuid)
        .arg("--shard-id")
        .arg(request.shard_id.to_string())
        .arg("--total-translog-ops")
        .arg("0")
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    decode_hex_bytes(std::str::from_utf8(&output.stdout).ok()?.trim())
}

fn build_java_translog_ops_request_payload(
    request: &ParsedStartRecoveryRequest,
    request_seq_no: i64,
) -> Option<Vec<u8>> {
    let script_path = env::current_dir()
        .ok()?
        .join("tools/build_java_translog_ops_request.sh");
    let output = Command::new("bash")
        .arg(script_path)
        .arg("--recovery-id")
        .arg(request.recovery_id.to_string())
        .arg("--request-seq-no")
        .arg(request_seq_no.to_string())
        .arg("--index-name")
        .arg(&request.index_name)
        .arg("--index-uuid")
        .arg(&request.index_uuid)
        .arg("--shard-id")
        .arg(request.shard_id.to_string())
        .arg("--total-translog-ops")
        .arg("0")
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    decode_hex_bytes(std::str::from_utf8(&output.stdout).ok()?.trim())
}

fn build_java_finalize_recovery_request_payload(
    request: &ParsedStartRecoveryRequest,
    request_seq_no: i64,
) -> Option<Vec<u8>> {
    let script_path = env::current_dir()
        .ok()?
        .join("tools/build_java_finalize_recovery_request.sh");
    let output = Command::new("bash")
        .arg(script_path)
        .arg("--recovery-id")
        .arg(request.recovery_id.to_string())
        .arg("--request-seq-no")
        .arg(request_seq_no.to_string())
        .arg("--index-name")
        .arg(&request.index_name)
        .arg("--index-uuid")
        .arg(&request.index_uuid)
        .arg("--shard-id")
        .arg(request.shard_id.to_string())
        .arg("--global-checkpoint")
        .arg("0")
        .arg("--trim-above-seq-no")
        .arg((request.starting_seq_no - 1).to_string())
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    decode_hex_bytes(std::str::from_utf8(&output.stdout).ok()?.trim())
}

fn maybe_complete_source_side_recovery(
    peer_addr: SocketAddr,
    request_body: &[u8],
    header_version_id: u32,
) {
    let Some(request) = parse_java_start_recovery_request(request_body, header_version_id) else {
        eprintln!("steelsearch_source_recovery_parse_failed header_version_id={header_version_id}");
        return;
    };
    let target_transport_address = request
        .target_transport_address
        .parse::<SocketAddr>()
        .unwrap_or(peer_addr);
    let request_id_prepare = TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let request_id_ops = TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let request_id_finalize = TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let request_seq_prepare = TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let request_seq_ops = TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let request_seq_finalize = TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let Some(prepare_payload) =
        build_java_prepare_translog_request_payload(&request, request_seq_prepare)
    else {
        eprintln!("steelsearch_source_recovery_prepare_payload_missing recovery_id={}", request.recovery_id);
        return;
    };
    let Some(translog_payload) =
        build_java_translog_ops_request_payload(&request, request_seq_ops)
    else {
        eprintln!("steelsearch_source_recovery_translog_payload_missing recovery_id={}", request.recovery_id);
        return;
    };
    let Some(finalize_payload) =
        build_java_finalize_recovery_request_payload(&request, request_seq_finalize)
    else {
        eprintln!("steelsearch_source_recovery_finalize_payload_missing recovery_id={}", request.recovery_id);
        return;
    };
    let prepare_frame = build_transport_request_frame(
        request_id_prepare,
        header_version_id,
        "internal:index/shard/recovery/prepare_translog",
        prepare_payload,
    );
    let translog_frame = build_transport_request_frame(
        request_id_ops,
        header_version_id,
        "internal:index/shard/recovery/translog_ops",
        translog_payload,
    );
    let finalize_frame = build_transport_request_frame(
        request_id_finalize,
        header_version_id,
        "internal:index/shard/recovery/finalize",
        finalize_payload,
    );
    thread::spawn(move || {
        for (request_id, action, frame) in [
            (request_id_prepare, "prepare_translog", prepare_frame),
            (request_id_ops, "translog_ops", translog_frame),
            (request_id_finalize, "finalize", finalize_frame),
        ] {
            if let Err(error) = send_transport_request_and_hold_for_response(
                target_transport_address,
                request_id,
                &frame,
                Duration::from_secs(10),
            ) {
                eprintln!(
                    "steelsearch_source_recovery_send_error action={} request_id={} peer={} error={}",
                    action, request_id, target_transport_address, error
                );
                return;
            }
            eprintln!(
                "steelsearch_source_recovery_response_received action={} request_id={} peer={}",
                action, request_id, target_transport_address
            );
        }
    });
}

fn build_replication_replica_response(
    request_id: i64,
    header_version_id: u32,
    local_checkpoint: i64,
    global_checkpoint: i64,
) -> Vec<u8> {
    let mut payload = Vec::new();
    write_transport_zlong_to(&mut payload, local_checkpoint);
    write_transport_zlong_to(&mut payload, global_checkpoint);
    build_transport_response_frame(request_id, header_version_id, payload)
}

fn build_empty_nodes_stats_response(
    request_id: i64,
    header_version_id: u32,
    transport_identity: &DevTransportIdentity,
) -> Vec<u8> {
    let script_path = env::current_dir()
        .ok()
        .map(|cwd| cwd.join("tools/build_java_nodes_stats_response.sh"));
    if let Some(script_path) = script_path {
        if let Ok(output) = Command::new("bash")
            .arg(script_path)
            .arg("--local-name")
            .arg(&transport_identity.node_name)
            .arg("--local-id")
            .arg(&transport_identity.node_id)
            .arg("--local-ephemeral-id")
            .arg(&transport_identity.ephemeral_id)
            .arg("--local-host")
            .arg(transport_identity.transport_address.ip().to_string())
            .arg("--local-host-address")
            .arg(transport_identity.transport_address.ip().to_string())
            .arg("--local-transport-address")
            .arg(transport_identity.transport_address.to_string())
            .arg("--local-roles")
            .arg(transport_identity.roles.join(","))
            .output()
        {
            if output.status.success() {
                if let Some(payload) = decode_hex_bytes(
                    std::str::from_utf8(&output.stdout).ok().unwrap_or("").trim(),
                ) {
                    return build_transport_response_frame(request_id, header_version_id, payload);
                }
            }
        }
    }
    build_empty_transport_response(request_id, header_version_id)
}

fn build_nodes_info_response(
    request_id: i64,
    header_version_id: u32,
    transport_identity: &DevTransportIdentity,
) -> Vec<u8> {
    let script_path = env::current_dir()
        .ok()
        .map(|cwd| cwd.join("tools/build_java_nodes_info_response.sh"));
    if let Some(script_path) = script_path {
        if let Ok(output) = Command::new("bash")
            .arg(script_path)
            .arg("--local-name")
            .arg(&transport_identity.node_name)
            .arg("--local-id")
            .arg(&transport_identity.node_id)
            .arg("--local-ephemeral-id")
            .arg(&transport_identity.ephemeral_id)
            .arg("--local-host")
            .arg(transport_identity.transport_address.ip().to_string())
            .arg("--local-host-address")
            .arg(transport_identity.transport_address.ip().to_string())
            .arg("--local-transport-address")
            .arg(transport_identity.transport_address.to_string())
            .arg("--local-roles")
            .arg(transport_identity.roles.join(","))
            .output()
        {
            if output.status.success() {
                if let Some(payload) = decode_hex_bytes(
                    std::str::from_utf8(&output.stdout).ok().unwrap_or("").trim(),
                ) {
                    return build_transport_response_frame(request_id, header_version_id, payload);
                }
            }
        }
    }
    build_empty_transport_response(request_id, header_version_id)
}

fn build_empty_indices_stats_node_response(
    request_id: i64,
    header_version_id: u32,
    transport_identity: &DevTransportIdentity,
) -> Vec<u8> {
    let mut payload = Vec::new();
    write_string(&mut payload, &transport_identity.node_id);
    write_transport_vint_to(&mut payload, 0);
    write_transport_vint_to(&mut payload, 0);
    write_bool(&mut payload, true);
    write_transport_vint_to(&mut payload, 0);
    build_transport_response_frame(request_id, header_version_id, payload)
}

fn build_empty_indices_recovery_node_response(
    request_id: i64,
    header_version_id: u32,
    transport_identity: &DevTransportIdentity,
) -> Vec<u8> {
    let mut payload = Vec::new();
    write_string(&mut payload, &transport_identity.node_id);
    write_transport_vint_to(&mut payload, 0);
    write_transport_vint_to(&mut payload, 0);
    write_bool(&mut payload, true);
    write_transport_vint_to(&mut payload, 0);
    build_transport_response_frame(request_id, header_version_id, payload)
}

fn build_liveness_response(
    request_id: i64,
    header_version_id: u32,
    transport_identity: &DevTransportIdentity,
) -> Vec<u8> {
    let mut payload = Vec::new();
    write_string(&mut payload, &transport_identity.cluster_name);
    write_bool(&mut payload, true);
    write_discovery_node_wire(
        &mut payload,
        &transport_identity.node_name,
        &transport_identity.node_id,
        &transport_identity.ephemeral_id,
        &transport_identity.transport_address.ip().to_string(),
        &transport_identity.transport_address.ip().to_string(),
        transport_identity.transport_address,
        &transport_identity.attributes,
        &transport_identity.roles,
        OPENSEARCH_3_7_0_TRANSPORT.id() as u32,
    );
    build_transport_response_frame(request_id, header_version_id, payload)
}

fn build_empty_shard_store_batch_response(
    request_id: i64,
    header_version_id: u32,
    transport_identity: &DevTransportIdentity,
) -> Vec<u8> {
    let mut payload = Vec::new();
    write_discovery_node_wire(
        &mut payload,
        &transport_identity.node_name,
        &transport_identity.node_id,
        &transport_identity.ephemeral_id,
        &transport_identity.transport_address.ip().to_string(),
        &transport_identity.transport_address.ip().to_string(),
        transport_identity.transport_address,
        &transport_identity.attributes,
        &transport_identity.roles,
        OPENSEARCH_3_7_0_TRANSPORT.id() as u32,
    );
    write_transport_vint_to(&mut payload, 0);
    build_transport_response_frame(request_id, header_version_id, payload)
}

fn decode_publish_state_request_info(
    request_body: &[u8],
) -> Option<(Option<i64>, Option<i64>, Option<String>)> {
    let script_path = env::current_dir()
        .ok()?
        .join("tools/parse_java_publish_state_request.sh");
    let report_path = std::env::temp_dir().join(format!(
        "steelsearch-publish-state-{}.json",
        TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed)
    ));
    let body_hex = request_body
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();
    let output = Command::new(script_path)
        .arg("--body-hex")
        .arg(body_hex)
        .arg("--report-path")
        .arg(&report_path)
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let parsed: serde_json::Value = serde_json::from_slice(&output.stdout).ok()?;
    Some((
        parsed.get("term").and_then(|value| value.as_i64()),
        parsed.get("version").and_then(|value| value.as_i64()),
        parsed
            .get("cluster_manager_node_id")
            .and_then(|value| value.as_str())
            .map(ToOwned::to_owned),
    ))
}

fn decode_local_initializing_replicas_from_publish_state(
    request_body: &[u8],
    local_node_id: &str,
    stream_version: Version,
    previous_cluster_state: Option<&ClusterState>,
    transport_identity: Option<&DevTransportIdentity>,
) -> Result<(Vec<PublishedReplicaAssignment>, Option<ClusterState>), String> {
    if request_body.len() < 17 {
        return Err("publish_state request body shorter than transport header".to_string());
    }
    let variable_header_size = u32::from_be_bytes([
        request_body[13],
        request_body[14],
        request_body[15],
        request_body[16],
    ]) as usize;
    let payload_offset = 17 + variable_header_size;
    if request_body.len() < payload_offset {
        return Err(format!(
            "publish_state request body shorter than payload offset {payload_offset}"
        ));
    }

    let wrapped_payload = unwrap_bytes_transport_request_payload(&request_body[payload_offset..])
        .map_err(|error| format!("failed to unwrap publish_state bytes transport request: {error}"))?;
    let payload = if wrapped_payload.starts_with(b"DFL\0") {
        decompress_deflate_body(&wrapped_payload)
            .map_err(|error| format!("failed to inflate publish_state payload: {error}"))?
    } else {
        BytesMut::from(wrapped_payload.as_ref())
    };
    let mut input = StreamInput::new(Bytes::from(payload.to_vec()));
    let full_state = input
        .read_bool()
        .map_err(|error| format!("failed to read publish_state full_state flag: {error}"))?;
    if !full_state {
        let bootstrapped_cluster_state = if previous_cluster_state.is_none() {
            transport_identity.and_then(|identity| {
                bootstrap_cached_cluster_state_from_seed_peers(
                    header_version_id_from_request_body(request_body)?,
                    stream_version,
                    identity,
                )
                .ok()
            })
        } else {
            None
        };
        let previous = previous_cluster_state
            .or(bootstrapped_cluster_state.as_ref())
            .ok_or_else(|| {
                "received diff publish_state before cached_cluster_state was available".to_string()
            })?;
        let applied = match read_publication_cluster_state_diff(Bytes::from(payload), stream_version)
        {
            Ok(diff) => match apply_publication_diff_and_ack(previous, diff) {
                Ok(outcome) => outcome.state,
                Err(error) => {
                    let fallback = transport_identity
                        .and_then(|identity| {
                            bootstrap_cached_cluster_state_from_seed_peers(
                                header_version_id_from_request_body(request_body)?,
                                stream_version,
                                identity,
                            )
                            .ok()
                        })
                        .ok_or_else(|| {
                            format!("failed to apply publish_state diff: {error}")
                        })?;
                    eprintln!(
                        "steelsearch_publish_state_resync_after_apply_error={error}"
                    );
                    fallback
                }
            },
            Err(error) => {
                let fallback = transport_identity
                    .and_then(|identity| {
                        bootstrap_cached_cluster_state_from_seed_peers(
                            header_version_id_from_request_body(request_body)?,
                            stream_version,
                            identity,
                        )
                        .ok()
                    })
                    .ok_or_else(|| format!("failed to decode publish_state diff: {error}"))?;
                eprintln!(
                    "steelsearch_publish_state_resync_after_decode_error={error}"
                );
                fallback
            }
        };
        let assignments =
            extract_local_initializing_replicas_from_cluster_state(&applied, local_node_id);
        return Ok((assignments, Some(applied)));
    }

    let state_header = read_cluster_state_header(&mut input)
        .map_err(|error| format!("failed to read full publish_state header: {error}"))?;
    let metadata_prefix = read_metadata_prefix(&mut input, stream_version)
        .map_err(|error| format!("failed to read full publish_state metadata: {error}"))?;
    let routing_table = read_routing_table_prefix(&mut input, stream_version)
        .map_err(|error| format!("failed to read full publish_state routing_table: {error}"))?;
    let discovery_nodes = read_discovery_nodes_prefix(&mut input, stream_version)
        .map_err(|error| format!("failed to read full publish_state discovery_nodes: {error}"))?;
    let cluster_blocks = read_cluster_blocks_prefix(&mut input)
        .map_err(|error| format!("failed to read full publish_state cluster_blocks: {error}"))?;
    let cluster_state_tail = read_cluster_state_tail_prefix(&mut input, stream_version)
        .map_err(|error| format!("failed to read full publish_state tail: {error}"))?;
    let cluster_state = ClusterState {
        response_cluster_name: state_header.cluster_name.clone(),
        header: state_header,
        metadata: metadata_prefix.into(),
        routing_table: routing_table.into(),
        discovery_nodes: discovery_nodes.into(),
        cluster_blocks: cluster_blocks.into(),
        customs: cluster_state_tail.into(),
        wait_for_timed_out: false,
    };
    let assignments =
        extract_local_initializing_replicas_from_cluster_state(&cluster_state, local_node_id);
    Ok((assignments, Some(cluster_state)))
}

fn unwrap_bytes_transport_request_payload(bytes: &[u8]) -> Result<Bytes, String> {
    let mut input = StreamInput::new(Bytes::copy_from_slice(bytes));
    let parent_task_node_id = input
        .read_string()
        .map_err(|error| format!("failed to read parent task node id: {error}"))?;
    if !parent_task_node_id.is_empty() {
        let _ = input
            .read_i64()
            .map_err(|error| format!("failed to read parent task id after node id: {error}"))?;
    }
    input
        .read_bytes_reference()
        .map_err(|error| format!("failed to read wrapped bytes reference: {error}"))
}

fn header_version_id_from_request_body(request_body: &[u8]) -> Option<u32> {
    (request_body.len() >= 13).then(|| {
        u32::from_be_bytes([
            request_body[9],
            request_body[10],
            request_body[11],
            request_body[12],
        ])
    })
}

fn bootstrap_cached_cluster_state_from_seed_peers(
    header_version_id: u32,
    stream_version: Version,
    transport_identity: &DevTransportIdentity,
) -> Result<ClusterState, String> {
    let mut last_error = None;
    for seed_peer_identity in &transport_identity.seed_peer_identities {
        let target_transport_address: SocketAddr = seed_peer_identity
            .discovery_node
            .transport_address
            .parse()
            .map_err(|error| format!("invalid seed peer transport address: {error}"))?;
        match fetch_cluster_state_from_seed_peer(
            target_transport_address,
            header_version_id,
            stream_version,
        ) {
            Ok(cluster_state) => {
                eprintln!(
                    "steelsearch_cluster_state_bootstrap peer={} state_uuid={} version={}",
                    target_transport_address, cluster_state.header.state_uuid, cluster_state.header.version
                );
                return Ok(cluster_state);
            }
            Err(error) => last_error = Some(format!("{target_transport_address}: {error}")),
        }
    }
    Err(last_error.unwrap_or_else(|| "no seed peers available for cluster state bootstrap".to_string()))
}

fn fetch_cluster_state_from_seed_peer(
    target_transport_address: SocketAddr,
    header_version_id: u32,
    stream_version: Version,
) -> Result<ClusterState, String> {
    let request_id = TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let request = build_cluster_state_request_frame(
        request_id,
        stream_version,
        &ClusterStateRequest::default(),
    )
    .to_vec();
    let mut stream = TcpStream::connect_timeout(&target_transport_address, Duration::from_secs(2))
        .map_err(|error| format!("connect failed: {error}"))?;
    stream
        .set_read_timeout(Some(Duration::from_secs(3)))
        .map_err(|error| format!("set_read_timeout failed: {error}"))?;
    stream
        .set_write_timeout(Some(Duration::from_secs(3)))
        .map_err(|error| format!("set_write_timeout failed: {error}"))?;
    stream
        .write_all(&request)
        .and_then(|()| stream.flush())
        .map_err(|error| format!("request write failed: {error}"))?;

    loop {
        match read_transport_seed_frame_detailed(&mut stream)
            .map_err(|error| format!("response read failed: {error}"))?
        {
            TransportSeedFrameRead::Frame((_header, body)) => {
                if body.len() < 17 {
                    continue;
                }
                let response_request_id = i64::from_be_bytes([
                    body[0], body[1], body[2], body[3], body[4], body[5], body[6], body[7],
                ]);
                let status = body[8];
                if response_request_id != request_id || status & 0x01 == 0 {
                    continue;
                }
                let response_header_version_id =
                    u32::from_be_bytes([body[9], body[10], body[11], body[12]]);
                if response_header_version_id != header_version_id {
                    return Err(format!(
                        "cluster state response version mismatch: expected {header_version_id}, got {response_header_version_id}"
                    ));
                }
                let variable_header_size =
                    u32::from_be_bytes([body[13], body[14], body[15], body[16]]) as usize;
                let payload_offset = 17 + variable_header_size;
                if body.len() < payload_offset {
                    return Err(format!(
                        "cluster state response shorter than payload offset {payload_offset}"
                    ));
                }
                let payload = if body[payload_offset..].starts_with(b"DFL\0") {
                    decompress_deflate_body(&body[payload_offset..]).map_err(|error| {
                        format!("failed to inflate cluster state response payload: {error}")
                    })?
                } else {
                    BytesMut::from(&body[payload_offset..])
                };
                let response = ClusterStateResponsePrefix::read(Bytes::from(payload.to_vec()))
                    .map_err(|error| format!("failed to decode cluster state response: {error}"))?;
                return response
                    .into_cluster_state()
                    .map_err(|error| format!("failed to materialize cluster state response: {error}"));
            }
            TransportSeedFrameRead::Ping(_header) => {
                let response = build_keepalive_ping_frame();
                stream
                    .write_all(&response)
                    .and_then(|()| stream.flush())
                    .map_err(|error| format!("ping response failed: {error}"))?;
            }
            TransportSeedFrameRead::TimedOut => {
                return Err("timed out waiting for cluster state response".to_string());
            }
            TransportSeedFrameRead::Eof => {
                return Err("seed peer closed connection before cluster state response".to_string());
            }
        }
    }
}

fn extract_local_initializing_replicas_from_cluster_state(
    cluster_state: &ClusterState,
    local_node_id: &str,
) -> Vec<PublishedReplicaAssignment> {
    let discovery_node_addresses = cluster_state
        .discovery_nodes
        .nodes
        .iter()
        .map(|node| {
            let address = node.stream_address.as_ref().unwrap_or(&node.address);
            (node.id.clone(), format!("{}:{}", address.ip, address.port))
        })
        .collect::<BTreeMap<_, _>>();

    let mut assignments = Vec::new();
    for index in &cluster_state.routing_table.indices {
        for shard in &index.shards {
            let source_primary_node_id = shard
                .shard_routings
                .iter()
                .find(|routing| {
                    routing.primary
                        && routing.state == ShardRoutingState::Started
                        && routing.current_node_id.is_some()
                })
                .and_then(|routing| routing.current_node_id.clone());
            let source_primary_transport_address = source_primary_node_id
                .as_ref()
                .and_then(|node_id| discovery_node_addresses.get(node_id))
                .cloned();

            for routing in &shard.shard_routings {
                if routing.primary
                    || routing.state != ShardRoutingState::Initializing
                    || routing.current_node_id.as_deref() != Some(local_node_id)
                {
                    continue;
                }
                assignments.push(PublishedReplicaAssignment {
                    index_name: index.index_name.clone(),
                    shard_id: shard.shard_id,
                    source_primary_node_id: source_primary_node_id.clone(),
                    source_primary_transport_address: source_primary_transport_address.clone(),
                    local_allocation_id: routing
                        .allocation_id
                        .as_ref()
                        .map(|allocation_id| allocation_id.id.clone()),
                });
            }
        }
    }
    assignments
}

fn refresh_local_initializing_replicas_from_seed_peers(
    transport_identity: &DevTransportIdentity,
    header_version_id: u32,
    stream_version: Version,
) -> Result<
    (
        ClusterState,
        Vec<PublishedReplicaAssignment>,
        Vec<PublishedShardRoutingSummary>,
    ),
    String,
> {
    let mut last_error = None;
    let mut latest_snapshot = None;
    for attempt in 0..6 {
        match bootstrap_cached_cluster_state_from_seed_peers(
            header_version_id,
            stream_version,
            transport_identity,
        ) {
            Ok(cluster_state) => {
                let assignments = extract_local_initializing_replicas_from_cluster_state(
                    &cluster_state,
                    &transport_identity.node_id,
                );
                let routing_summaries =
                    summarize_relevant_shard_routings_from_cluster_state(&cluster_state);
                let saw_local_replica = routing_summaries.iter().any(|routing| {
                    !routing.primary
                        && routing.state == "Initializing"
                        && routing.current_node_id.as_deref()
                            == Some(transport_identity.node_id.as_str())
                });
                latest_snapshot = Some((cluster_state, assignments, routing_summaries));
                if saw_local_replica || attempt == 5 {
                    break;
                }
                std::thread::sleep(Duration::from_millis(500));
            }
            Err(error) => {
                last_error = Some(error);
                if attempt < 5 {
                    std::thread::sleep(Duration::from_millis(250));
                }
            }
        }
    }

    latest_snapshot.ok_or_else(|| {
        last_error.unwrap_or_else(|| {
            "no seed peers available for cluster state refresh".to_string()
        })
    })
}

fn maybe_refresh_local_initializing_replicas_from_seed_peers(
    transport_identity: &DevTransportIdentity,
    header_version_id: u32,
    stream_version: Version,
) {
    let should_refresh = transport_identity
        .coordination_state
        .lock()
        .map(|state| {
            state.local_initializing_replicas.is_empty()
        })
        .unwrap_or(false);
    if !should_refresh {
        return;
    }

    let (refreshed, refreshed_assignments, refreshed_routing_summaries) =
        match refresh_local_initializing_replicas_from_seed_peers(
            transport_identity,
            header_version_id,
            stream_version,
        ) {
            Ok(snapshot) => snapshot,
        Err(error) => {
            eprintln!("steelsearch_cluster_state_refresh_error={error}");
            return;
        }
        };
    maybe_refresh_cached_match_all_total_hits(transport_identity, &refreshed);
    if let Ok(mut coordination_state) = transport_identity.coordination_state.lock() {
        coordination_state.cached_cluster_state = Some(refreshed);
        coordination_state.local_initializing_replicas = refreshed_assignments.clone();
        coordination_state.last_cluster_state_refresh_at_ms = Some(now_epoch_ms());
    }
    let refreshed_cluster_state = transport_identity
        .coordination_state
        .lock()
        .ok()
        .and_then(|state| state.cached_cluster_state.clone());
    maybe_start_peer_recoveries(
        transport_identity,
        header_version_id,
        &refreshed_assignments,
        refreshed_cluster_state.as_ref(),
    );
    eprintln!(
        "steelsearch_cluster_state_refresh_local_initializing_replicas={:?}",
        refreshed_assignments
    );
    eprintln!(
        "steelsearch_cluster_state_refresh_relevant_routings={:?}",
        refreshed_routing_summaries
    );
}

fn summarize_relevant_shard_routings_from_cluster_state(
    cluster_state: &ClusterState,
) -> Vec<PublishedShardRoutingSummary> {
    let mut summaries = Vec::new();
    for index in &cluster_state.routing_table.indices {
        for shard in &index.shards {
            for routing in &shard.shard_routings {
                if routing.state != ShardRoutingState::Initializing && !routing.primary {
                    continue;
                }
                summaries.push(PublishedShardRoutingSummary {
                    index_name: index.index_name.clone(),
                    shard_id: shard.shard_id,
                    primary: routing.primary,
                    state: format!("{:?}", routing.state),
                    current_node_id: routing.current_node_id.clone(),
                    relocating_node_id: routing.relocating_node_id.clone(),
                    allocation_id: routing
                        .allocation_id
                        .as_ref()
                        .map(|allocation_id| allocation_id.id.clone()),
                });
            }
        }
    }
    summaries
}

fn hold_transport_channel_open(
    stream: &mut TcpStream,
    transport_identity: &DevTransportIdentity,
    post_follow_up_frame: &mut Option<serde_json::Value>,
    post_follow_up_frame_received_at_ms: &mut Option<u128>,
    send_proactive_keepalive_after_first_timeout: bool,
    proactive_keepalive_sent_at_ms: &mut Option<u128>,
    proactive_keepalive_count: &mut u32,
    hold_for: Duration,
    hold_open_started_at_ms: &mut Option<u128>,
    first_post_response_event: &mut Option<String>,
    connection_end: &mut Option<String>,
    connection_end_at_ms: &mut Option<u128>,
) -> std::io::Result<()> {
    let started = std::time::Instant::now();
    let mut pending_proactive_keepalive = send_proactive_keepalive_after_first_timeout;
    *hold_open_started_at_ms = Some(unix_time_ms());
    stream.set_read_timeout(Some(Duration::from_secs(1)))?;
    while started.elapsed() < hold_for && !SHUTDOWN_REQUESTED.load(Ordering::SeqCst) {
        match read_transport_seed_frame_detailed(stream)? {
            TransportSeedFrameRead::Frame((post_header, post_body)) => {
                if post_follow_up_frame.is_none() {
                    *post_follow_up_frame_received_at_ms = Some(unix_time_ms());
                    *post_follow_up_frame = Some(summarize_transport_seed_frame(&post_header, &post_body));
                }
                let peer_addr = stream.peer_addr().ok();
                if handle_subsequent_transport_request(stream, &post_body, transport_identity, peer_addr)? {
                    if first_post_response_event.is_none() {
                        *first_post_response_event = Some("handled_follow_up_request".to_string());
                    }
                    continue;
                }
                if first_post_response_event.is_none() {
                    *first_post_response_event = Some("received_follow_up_frame".to_string());
                }
                *connection_end = Some("received_follow_up_frame".to_string());
                *connection_end_at_ms = Some(unix_time_ms());
            }
            TransportSeedFrameRead::Ping(_header) => {
                let response = build_keepalive_ping_frame();
                stream.write_all(&response)?;
                stream.flush()?;
                if first_post_response_event.is_none() {
                    *first_post_response_event = Some("keepalive_ping".to_string());
                }
                *connection_end = Some("keepalive_ping".to_string());
                *connection_end_at_ms = Some(unix_time_ms());
            }
            TransportSeedFrameRead::TimedOut => {
                if pending_proactive_keepalive {
                    let response = build_keepalive_ping_frame();
                    stream.write_all(&response)?;
                    stream.flush()?;
                    *proactive_keepalive_count += 1;
                    if proactive_keepalive_sent_at_ms.is_none() {
                        *proactive_keepalive_sent_at_ms = Some(unix_time_ms());
                    }
                    pending_proactive_keepalive = false;
                    continue;
                }
                if first_post_response_event.is_none() {
                    *first_post_response_event = Some("idle_timeout".to_string());
                }
                *connection_end = Some("idle_timeout".to_string());
                *connection_end_at_ms = Some(unix_time_ms());
            }
            TransportSeedFrameRead::Eof => {
                if first_post_response_event.is_none() {
                    *first_post_response_event = Some("remote_eof".to_string());
                }
                *connection_end = Some("remote_eof".to_string());
                *connection_end_at_ms = Some(unix_time_ms());
                return Ok(());
            }
        }
    }
    if SHUTDOWN_REQUESTED.load(Ordering::SeqCst) {
        *connection_end = Some("shutdown_requested".to_string());
        *connection_end_at_ms = Some(unix_time_ms());
    } else if connection_end.is_none() {
        *connection_end = Some("hold_window_elapsed".to_string());
        *connection_end_at_ms = Some(unix_time_ms());
    }
    Ok(())
}

fn transport_connection_hold_duration() -> Duration {
    Duration::from_secs(
        env::var("STEELSEARCH_TRANSPORT_CONNECTION_HOLD_SECS")
            .ok()
            .and_then(|raw| raw.parse::<u64>().ok())
            .unwrap_or(300),
    )
}

fn unix_time_ms() -> u128 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|duration| duration.as_millis())
        .unwrap_or(0)
}

fn handle_subsequent_transport_request(
    stream: &mut TcpStream,
    body: &[u8],
    transport_identity: &DevTransportIdentity,
    peer_addr: Option<SocketAddr>,
) -> std::io::Result<bool> {
    if body.len() < 13 {
        return Ok(false);
    }

    let request_id = i64::from_be_bytes([
        body[0], body[1], body[2], body[3], body[4], body[5], body[6], body[7],
    ]);
    let status = body[8];
    if status & 0x01 != 0 {
        return Ok(false);
    }
    let header_version_id = u32::from_be_bytes([body[9], body[10], body[11], body[12]]);
    let action_hint = transport_frame_action_hint(body);
    let normalized_action_hint = action_hint.as_deref().map(|action| action.strip_suffix("[n]").unwrap_or(action));
    eprintln!(
        "steelsearch_followup_request request_id={} action_hint={:?} header_version_id={}",
        request_id, action_hint, header_version_id
    );

    let response = match normalized_action_hint {
        Some("internal:transport/handshake") => Some(build_transport_handshake_identity_response(
            request_id,
            header_version_id,
            transport_identity,
        )),
        Some("internal:discovery/request_peers") => {
            Some(build_request_peers_response(request_id, header_version_id))
        }
        Some("internal:cluster/request_pre_vote") => Some(build_pre_vote_response(
            request_id,
            header_version_id,
            0,
            0,
            0,
        )),
        Some("cluster:monitor/nodes/liveness") => Some(build_liveness_response(
            request_id,
            header_version_id,
            transport_identity,
        )),
        Some("cluster:monitor/nodes/stats") => Some(build_empty_nodes_stats_response(
            request_id,
            header_version_id,
            transport_identity,
        )),
        Some("cluster:monitor/nodes/info") => Some(build_nodes_info_response(
            request_id,
            header_version_id,
            transport_identity,
        )),
        Some("indices:monitor/stats") => Some(build_empty_indices_stats_node_response(
            request_id,
            header_version_id,
            transport_identity,
        )),
        Some("indices:monitor/recovery") => Some(build_empty_indices_recovery_node_response(
            request_id,
            header_version_id,
            transport_identity,
        )),
        Some("indices:data/read/search[phase/query]") => {
            maybe_build_query_phase_response(request_id, body, transport_identity)
        }
        Some("indices:admin/seq_no/retention_lease_background_sync")
        | Some("indices:admin/seq_no/retention_lease_background_sync[r]") => {
            Some(build_replication_replica_response(
                request_id,
                header_version_id,
                0,
                0,
            ))
        }
        Some("internal:cluster/nodes/indices/shard/store/batch") => Some(
            build_empty_shard_store_batch_response(
                request_id,
                header_version_id,
                transport_identity,
            ),
        ),
        Some("internal:index/shard/recovery/start_recovery") => {
            if let Some(peer_addr) = peer_addr {
                maybe_complete_source_side_recovery(peer_addr, body, header_version_id);
            }
            Some(build_java_recovery_response(request_id, header_version_id))
        }
        Some("internal:index/shard/recovery/filesInfo")
        | Some("internal:index/shard/recovery/file_chunk")
        | Some("internal:index/shard/recovery/clean_files")
        | Some("internal:index/shard/recovery/prepare_translog")
        | Some("internal:index/shard/recovery/finalize")
        | Some("internal:index/shard/recovery/handoff_primary_context") => {
            Some(build_empty_transport_response(request_id, header_version_id))
        }
        Some("internal:index/shard/recovery/translog_ops") => Some(
            build_recovery_translog_operations_response(request_id, header_version_id, 0),
        ),
        Some("internal:coordination/fault_detection/follower_check")
        | Some("internal:coordination/fault_detection/leader_check")
        | Some("internal:cluster/coordination/join")
        | Some("internal:cluster/coordination/join/validate")
        | Some("internal:cluster/coordination/join/validate_compressed")
        | Some("internal:cluster/coordination/commit_state")
        | Some("internal:admin/tasks/ban") => {
            if matches!(
                action_hint.as_deref(),
                Some("internal:coordination/fault_detection/follower_check")
                    | Some("internal:coordination/fault_detection/leader_check")
            ) {
                if let Ok(mut coordination_state) = transport_identity.coordination_state.lock() {
                    coordination_state.non_self_publish_seen = true;
                }
                let refresh_identity = transport_identity.clone();
                thread::spawn(move || {
                    maybe_refresh_local_initializing_replicas_from_seed_peers(
                        &refresh_identity,
                        header_version_id,
                        Version::from_id(header_version_id as i32),
                    );
                });
            }
            Some(build_empty_transport_response(request_id, header_version_id))
        }
        Some("internal:cluster/coordination/start_join") => {
            maybe_send_join_request_to_seed_peer(header_version_id, body, transport_identity);
            Some(build_empty_transport_response(request_id, header_version_id))
        }
        Some("internal:cluster/coordination/publish_state") => {
            let cached_cluster_state = transport_identity
                .coordination_state
                .lock()
                .ok()
                .and_then(|state| state.cached_cluster_state.clone());
            let (local_initializing_replicas, applied_cluster_state) =
                match decode_local_initializing_replicas_from_publish_state(
                    body,
                    &transport_identity.node_id,
                    Version::from_id(header_version_id as i32),
                    cached_cluster_state.as_ref(),
                    Some(transport_identity),
                ) {
                    Ok(value) => value,
                    Err(error) => {
                        eprintln!("steelsearch_publish_state_decode_error={error}");
                        Default::default()
                    }
                };
            let routing_summaries = applied_cluster_state
                .as_ref()
                .map(summarize_relevant_shard_routings_from_cluster_state)
                .unwrap_or_default();
            let (
                join_last_accepted_term,
                join_last_accepted_version,
                cached_cluster_manager_node_id,
            ) = transport_identity
                .coordination_state
                .lock()
                .map(|state| {
                    (
                        state.last_accepted_term,
                        state.last_accepted_version,
                        state.cluster_manager_node_id.clone(),
                    )
                })
                .unwrap_or((0, 0, None));
            let term = applied_cluster_state
                .as_ref()
                .map(|state| state.metadata.coordination.term)
                .unwrap_or(join_last_accepted_term);
            let version = applied_cluster_state
                .as_ref()
                .map(|state| state.header.version)
                .unwrap_or(join_last_accepted_version);
            let cluster_manager_node_id = applied_cluster_state
                .as_ref()
                .and_then(|state| state.discovery_nodes.cluster_manager_node_id.clone())
                .or(cached_cluster_manager_node_id);
            if let Ok(mut coordination_state) = transport_identity.coordination_state.lock() {
                coordination_state.last_accepted_term = term;
                coordination_state.last_accepted_version = version;
                if let Some(node_id) = cluster_manager_node_id.clone() {
                    coordination_state.cluster_manager_node_id = Some(node_id);
                }
                coordination_state.local_initializing_replicas =
                    local_initializing_replicas.clone();
                if let Some(cluster_state) = applied_cluster_state.clone() {
                    coordination_state.cached_cluster_state = Some(cluster_state);
                }
            }
            maybe_start_peer_recoveries(
                transport_identity,
                header_version_id,
                &local_initializing_replicas,
                applied_cluster_state.as_ref(),
            );
            eprintln!(
                "steelsearch_publish_state_local_initializing_replicas={:?}",
                local_initializing_replicas
            );
            eprintln!(
                "steelsearch_publish_state_relevant_routings={:?}",
                routing_summaries
            );
            Some(build_publish_with_join_response(
                request_id,
                header_version_id,
                term,
                version,
                transport_identity,
                join_last_accepted_term,
                join_last_accepted_version,
                cluster_manager_node_id.as_deref(),
            ))
        }
        _ => None,
    };

    let Some(response) = response else {
        eprintln!(
            "steelsearch_followup_request_unhandled request_id={} action_hint={:?}",
            request_id, action_hint
        );
        return Ok(false);
    };
    stream.write_all(&response)?;
    stream.flush()?;
    eprintln!(
        "steelsearch_followup_response_sent request_id={} action_hint={:?} bytes={}",
        request_id,
        action_hint,
        response.len()
    );
    Ok(true)
}

fn summarize_transport_response_frame(frame: &[u8]) -> Option<serde_json::Value> {
    if frame.len() < 6 || &frame[..2] != b"ES" {
        return None;
    }
    let mut header = [0_u8; 6];
    header.copy_from_slice(&frame[..6]);
    Some(summarize_transport_seed_frame(&header, &frame[6..]))
}

fn summarize_transport_response_frame_for_action(
    frame: &[u8],
    action_hint: Option<&str>,
) -> Option<serde_json::Value> {
    let mut summary = summarize_transport_response_frame(frame)?;
    if matches!(
        action_hint,
        Some("internal:cluster/coordination/publish_state")
            | Some("internal:coordination/fault_detection/follower_check")
            | Some("internal:transport/handshake")
    ) {
        summary["body_hex"] = serde_json::json!(
            frame[6..]
                .iter()
                .map(|byte| format!("{byte:02x}"))
                .collect::<String>()
        );
    }
    if let Some(action_hint) = action_hint {
        summary["action_hint"] = serde_json::json!(action_hint);
    }
    Some(summary)
}

fn maybe_send_join_request_to_seed_peer(
    header_version_id: u32,
    request_body: &[u8],
    transport_identity: &DevTransportIdentity,
) {
    if transport_identity.seed_peer_identities.is_empty() {
        return;
    }
    if request_body.len() < 8 {
        return;
    }
    let term_offset = request_body.len() - 8;
    let Ok(term_bytes) = <[u8; 8]>::try_from(&request_body[term_offset..]) else {
        return;
    };
    let term = i64::from_be_bytes(term_bytes);
    for seed_peer_identity in &transport_identity.seed_peer_identities {
        let request = build_join_request_frame(
            TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed),
            header_version_id,
            term,
            transport_identity,
            seed_peer_identity,
        );
        let Ok(target_transport_address) = seed_peer_identity.discovery_node.transport_address.parse() else {
            continue;
        };
        let _ = send_join_request_over_managed_channel(
            target_transport_address,
            request,
            transport_identity,
            "start_join_fanout",
        );
    }
}

fn send_join_request_over_managed_channel(
    target_transport_address: SocketAddr,
    request: Vec<u8>,
    transport_identity: &DevTransportIdentity,
    context: &str,
) -> std::io::Result<()> {
    let mut stream = TcpStream::connect_timeout(&target_transport_address, Duration::from_secs(2))?;
    stream.set_read_timeout(Some(Duration::from_secs(1)))?;
    stream.write_all(&request)?;
    stream.flush()?;
    eprintln!(
        "steelsearch_join_channel_open context={} peer={} bytes={}",
        context,
        target_transport_address,
        request.len()
    );
    let transport_identity = transport_identity.clone();
    let context = context.to_string();
    thread::spawn(move || {
        let started = std::time::Instant::now();
        let mut sent_keepalive = false;
        while started.elapsed() < transport_connection_hold_duration()
            && !SHUTDOWN_REQUESTED.load(Ordering::SeqCst)
        {
            match read_transport_seed_frame_detailed(&mut stream) {
                Ok(TransportSeedFrameRead::Frame((_header, body))) => {
                    if body.len() < 13 {
                        continue;
                    }
                    let request_id = i64::from_be_bytes([
                        body[0], body[1], body[2], body[3], body[4], body[5], body[6], body[7],
                    ]);
                    let status = body[8];
                    let action_hint = transport_frame_action_hint(&body);
                    if status & 0x01 != 0 {
                        eprintln!(
                            "steelsearch_join_channel_response context={} peer={} request_id={} action_hint={:?}",
                            context,
                            target_transport_address,
                            request_id,
                            action_hint
                        );
                        continue;
                    }
                    eprintln!(
                        "steelsearch_join_channel_followup context={} peer={} request_id={} action_hint={:?}",
                        context,
                        target_transport_address,
                        request_id,
                        action_hint
                    );
                    if let Err(error) =
                        handle_subsequent_transport_request(
                            &mut stream,
                            &body,
                            &transport_identity,
                            Some(target_transport_address),
                        )
                    {
                        eprintln!(
                            "steelsearch_join_channel_followup_error context={} peer={} error={}",
                            context, target_transport_address, error
                        );
                        break;
                    }
                }
                Ok(TransportSeedFrameRead::Ping(_header)) => {
                    let response = build_keepalive_ping_frame();
                    if let Err(error) = stream.write_all(&response).and_then(|()| stream.flush()) {
                        eprintln!(
                            "steelsearch_join_channel_ping_error context={} peer={} error={}",
                            context, target_transport_address, error
                        );
                        break;
                    }
                }
                Ok(TransportSeedFrameRead::TimedOut) => {
                    if !sent_keepalive {
                        let response = build_keepalive_ping_frame();
                        if let Err(error) = stream.write_all(&response).and_then(|()| stream.flush()) {
                            eprintln!(
                                "steelsearch_join_channel_keepalive_error context={} peer={} error={}",
                                context, target_transport_address, error
                            );
                            break;
                        }
                        sent_keepalive = true;
                    }
                    continue;
                }
                Ok(TransportSeedFrameRead::Eof) => {
                    eprintln!(
                        "steelsearch_join_channel_eof context={} peer={}",
                        context, target_transport_address
                    );
                    break;
                }
                Err(error) => {
                    eprintln!(
                        "steelsearch_join_channel_read_error context={} peer={} error={}",
                        context, target_transport_address, error
                    );
                    break;
                }
            }
        }
    });
    Ok(())
}

fn spawn_proactive_seed_join_loop(transport_identity: DevTransportIdentity) {
    thread::spawn(move || {
        thread::sleep(Duration::from_secs(2));
        for attempt in 0..30 {
            if SHUTDOWN_REQUESTED.load(Ordering::SeqCst) {
                break;
            }
            let joined_java_cluster = transport_identity
                .coordination_state
                .lock()
                .map(|state| state.non_self_publish_seen)
                .unwrap_or(false);
            if joined_java_cluster {
                eprintln!(
                    "steelsearch_proactive_join_stopped reason=non_self_publish_seen attempt={}",
                    attempt
                );
                break;
            }
            let (last_accepted_term, _) = transport_identity
                .coordination_state
                .lock()
                .map(|state| (state.last_accepted_term, state.last_accepted_version))
                .unwrap_or((0, 0));
            let join_term = std::cmp::max(last_accepted_term, 1);
            for seed_peer_identity in &transport_identity.seed_peer_identities {
                let request = build_join_request_frame(
                    TRANSPORT_REQUEST_SEQUENCE.fetch_add(1, Ordering::Relaxed),
                    OPENSEARCH_3_7_0_TRANSPORT.id() as u32,
                    join_term,
                    &transport_identity,
                    seed_peer_identity,
                );
                let Ok(target_transport_address) = seed_peer_identity
                    .discovery_node
                    .transport_address
                    .parse()
                else {
                    continue;
                };
                let _ = send_join_request_over_managed_channel(
                    target_transport_address,
                    request,
                    &transport_identity,
                    "proactive_retry",
                );
            }
            eprintln!(
                "steelsearch_proactive_join_attempt={} seed_count={} join_term={}",
                attempt + 1,
                transport_identity.seed_peer_identities.len(),
                join_term
            );
            thread::sleep(Duration::from_secs(1));
        }
    });
}

fn build_join_request_frame(
    request_id: i64,
    header_version_id: u32,
    term: i64,
    transport_identity: &DevTransportIdentity,
    seed_peer_identity: &InteropSeedPeerIdentityManifest,
) -> Vec<u8> {
    let mut payload = Vec::new();
    let (last_accepted_term, last_accepted_version) = transport_identity
        .coordination_state
        .lock()
        .map(|state| (state.last_accepted_term, state.last_accepted_version))
        .unwrap_or((0, 0));
    write_string(&mut payload, "");
    write_discovery_node_wire(
        &mut payload,
        &transport_identity.node_name,
        &transport_identity.node_id,
        &transport_identity.ephemeral_id,
        &transport_identity.transport_address.ip().to_string(),
        &transport_identity.transport_address.ip().to_string(),
        transport_identity.transport_address,
        &transport_identity.attributes,
        &transport_identity.roles,
        OPENSEARCH_3_7_0_TRANSPORT.id() as u32,
    );
    payload.extend_from_slice(&term.to_be_bytes());
    write_bool(&mut payload, true);
    write_discovery_node_wire(
        &mut payload,
        &transport_identity.node_name,
        &transport_identity.node_id,
        &transport_identity.ephemeral_id,
        &transport_identity.transport_address.ip().to_string(),
        &transport_identity.transport_address.ip().to_string(),
        transport_identity.transport_address,
        &transport_identity.attributes,
        &transport_identity.roles,
        OPENSEARCH_3_7_0_TRANSPORT.id() as u32,
    );
    let target_transport_address: SocketAddr = seed_peer_identity
        .discovery_node
        .transport_address
        .parse()
        .expect("validated transport address");
    write_discovery_node_wire(
        &mut payload,
        &seed_peer_identity.discovery_node.name,
        &seed_peer_identity.discovery_node.id,
        &seed_peer_identity.discovery_node.ephemeral_id,
        &seed_peer_identity.discovery_node.host_name,
        &seed_peer_identity.discovery_node.host_address,
        target_transport_address,
        &[],
        &seed_peer_identity.discovery_node.roles,
        seed_peer_identity.discovery_node.version_id,
    );
    payload.extend_from_slice(&term.to_be_bytes());
    payload.extend_from_slice(&last_accepted_term.to_be_bytes());
    payload.extend_from_slice(&last_accepted_version.to_be_bytes());
    build_transport_request_frame(
        request_id,
        header_version_id,
        "internal:cluster/coordination/join",
        payload,
    )
}

fn build_transport_request_frame(
    request_id: i64,
    header_version_id: u32,
    action: &str,
    payload: Vec<u8>,
) -> Vec<u8> {
    let mut variable_header = Vec::new();
    write_transport_vint_to(&mut variable_header, 0);
    write_transport_vint_to(&mut variable_header, 0);
    write_transport_vint_to(&mut variable_header, 0);
    write_string(&mut variable_header, action);
    let message_length = 8 + 1 + 4 + 4 + variable_header.len() + payload.len();
    let mut frame = Vec::with_capacity(6 + message_length);
    frame.extend_from_slice(b"ES");
    frame.extend_from_slice(&(message_length as u32).to_be_bytes());
    frame.extend_from_slice(&request_id.to_be_bytes());
    frame.push(0x00);
    frame.extend_from_slice(&header_version_id.to_be_bytes());
    frame.extend_from_slice(&(variable_header.len() as u32).to_be_bytes());
    frame.extend_from_slice(&variable_header);
    frame.extend_from_slice(&payload);
    frame
}

fn send_transport_frame(target_transport_address: SocketAddr, frame: &[u8]) -> std::io::Result<()> {
    let mut stream = TcpStream::connect_timeout(&target_transport_address, Duration::from_secs(2))?;
    stream.set_read_timeout(Some(Duration::from_secs(2)))?;
    stream.set_write_timeout(Some(Duration::from_secs(2)))?;
    stream.write_all(frame)?;
    stream.flush()?;
    let _ = read_transport_seed_frame(&mut stream);
    Ok(())
}

fn send_transport_request_and_hold_for_response(
    target_transport_address: SocketAddr,
    request_id: i64,
    frame: &[u8],
    hold_for: Duration,
) -> std::io::Result<()> {
    let mut stream = TcpStream::connect_timeout(&target_transport_address, Duration::from_secs(2))?;
    stream.set_read_timeout(Some(Duration::from_secs(1)))?;
    stream.set_write_timeout(Some(Duration::from_secs(5)))?;
    perform_transport_connection_handshake(
        &mut stream,
        request_id,
        OPENSEARCH_3_7_0_TRANSPORT.id() as u32,
    )?;
    stream.write_all(frame)?;
    stream.flush()?;
    let started = std::time::Instant::now();
    while started.elapsed() < hold_for && !SHUTDOWN_REQUESTED.load(Ordering::SeqCst) {
        if wait_for_transport_response_request_id(&mut stream, request_id)? {
            return Ok(());
        }
    }
    Ok(())
}

fn perform_transport_connection_handshake(
    stream: &mut TcpStream,
    base_request_id: i64,
    header_version_id: u32,
) -> std::io::Result<()> {
    let header_version = Version::from_id(header_version_id as i32);
    let tcp_handshake_request_id = base_request_id - 2;
    let tcp_handshake =
        build_tcp_handshake_request(tcp_handshake_request_id, header_version, header_version);
    stream.write_all(&tcp_handshake[..])?;
    stream.flush()?;
    let _ = wait_for_transport_response_request_id(stream, tcp_handshake_request_id)?;

    let transport_handshake_request_id = base_request_id - 1;
    let transport_handshake =
        build_transport_handshake_request(transport_handshake_request_id, header_version);
    stream.write_all(&transport_handshake[..])?;
    stream.flush()?;
    let _ = wait_for_transport_response_request_id(stream, transport_handshake_request_id)?;
    Ok(())
}

fn wait_for_transport_response_request_id(
    stream: &mut TcpStream,
    request_id: i64,
) -> std::io::Result<bool> {
    loop {
        match read_transport_seed_frame_detailed(stream)? {
            TransportSeedFrameRead::Frame((_header, body)) => {
                if body.len() < 13 {
                    continue;
                }
                let response_request_id = i64::from_be_bytes([
                    body[0], body[1], body[2], body[3], body[4], body[5], body[6], body[7],
                ]);
                let status = body[8];
                if response_request_id == request_id && status & 0x01 != 0 {
                    return Ok(true);
                }
            }
            TransportSeedFrameRead::Ping(_header) => {
                let response = build_keepalive_ping_frame();
                stream.write_all(&response)?;
                stream.flush()?;
            }
            TransportSeedFrameRead::TimedOut => return Ok(false),
            TransportSeedFrameRead::Eof => return Ok(false),
        }
    }
}

fn build_transport_response_frame(
    request_id: i64,
    header_version_id: u32,
    payload: Vec<u8>,
) -> Vec<u8> {
    let variable_header = [0_u8, 0_u8];
    let message_length = 8 + 1 + 4 + 4 + variable_header.len() + payload.len();
    let mut frame = Vec::with_capacity(6 + message_length);
    frame.extend_from_slice(b"ES");
    frame.extend_from_slice(&(message_length as u32).to_be_bytes());
    frame.extend_from_slice(&request_id.to_be_bytes());
    frame.push(0x01);
    frame.extend_from_slice(&header_version_id.to_be_bytes());
    frame.extend_from_slice(&(variable_header.len() as u32).to_be_bytes());
    frame.extend_from_slice(&variable_header);
    frame.extend_from_slice(&payload);
    frame
}

fn hex_prefix(bytes: &[u8], max_len: usize) -> String {
    bytes.iter()
        .take(max_len)
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>()
}

fn write_transport_vint_to(out: &mut Vec<u8>, mut value: u32) {
    while (value & !0x7f) != 0 {
        out.push(((value & 0x7f) as u8) | 0x80);
        value >>= 7;
    }
    out.push(value as u8);
}

fn write_transport_zlong_to(out: &mut Vec<u8>, value: i64) {
    let mut encoded = ((value << 1) ^ (value >> 63)) as u64;
    while (encoded & !0x7f) != 0 {
        out.push(((encoded & 0x7f) as u8) | 0x80);
        encoded >>= 7;
    }
    out.push(encoded as u8);
}

fn write_bool(out: &mut Vec<u8>, value: bool) {
    out.push(if value { 1 } else { 0 });
}

fn write_string(out: &mut Vec<u8>, value: &str) {
    let bytes = value.as_bytes();
    write_transport_vint_to(out, bytes.len() as u32);
    out.extend_from_slice(bytes);
}

fn write_discovery_node_wire(
    out: &mut Vec<u8>,
    node_name: &str,
    node_id: &str,
    ephemeral_id: &str,
    host_name: &str,
    host_address: &str,
    transport_address: SocketAddr,
    attributes: &[(String, String)],
    roles: &[String],
    version_id: u32,
) {
    write_string(out, node_name);
    write_string(out, node_id);
    write_string(out, ephemeral_id);
    write_string(out, host_name);
    write_string(out, host_address);
    write_transport_address(out, transport_address);
    write_bool(out, false);
    write_transport_vint_to(out, attributes.len() as u32);
    for (key, value) in attributes {
        write_string(out, key);
        write_string(out, value);
    }
    write_transport_vint_to(out, roles.len() as u32);
    for role in roles {
        let (abbrev, can_contain_data) = transport_role_wire_compat(role);
        write_string(out, role);
        write_string(out, abbrev);
        write_bool(out, can_contain_data);
    }
    write_transport_vint_to(out, version_id);
}

fn write_transport_address(out: &mut Vec<u8>, address: SocketAddr) {
    match address.ip() {
        IpAddr::V4(ipv4) => {
            out.push(4);
            out.extend_from_slice(&ipv4.octets());
        }
        IpAddr::V6(ipv6) => {
            out.push(16);
            out.extend_from_slice(&ipv6.octets());
        }
    }
    write_string(out, &address.ip().to_string());
    out.extend_from_slice(&(address.port() as i32).to_be_bytes());
}

fn transport_role_wire_compat(role: &str) -> (&'static str, bool) {
    match role {
        "cluster_manager" => ("m", false),
        "data" => ("d", true),
        "ingest" => ("i", false),
        "remote_cluster_client" => ("r", false),
        _ => ("u", false),
    }
}

fn build_tcp_handshake_response(
    request_id: i64,
    header_version_id: u32,
    response_version_id: u32,
) -> Vec<u8> {
    let variable_header = [0_u8, 0_u8];
    let payload = write_transport_vint(response_version_id);
    let message_length = 8 + 1 + 4 + 4 + variable_header.len() + payload.len();
    let mut frame = Vec::with_capacity(6 + message_length);
    frame.extend_from_slice(b"ES");
    frame.extend_from_slice(&(message_length as u32).to_be_bytes());
    frame.extend_from_slice(&request_id.to_be_bytes());
    frame.push(0x09);
    frame.extend_from_slice(&header_version_id.to_be_bytes());
    frame.extend_from_slice(&(variable_header.len() as u32).to_be_bytes());
    frame.extend_from_slice(&variable_header);
    frame.extend_from_slice(&payload);
    frame
}

fn write_transport_vint(mut value: u32) -> Vec<u8> {
    let mut out = Vec::new();
    while (value & !0x7f) != 0 {
        out.push(((value & 0x7f) as u8) | 0x80);
        value >>= 7;
    }
    out.push(value as u8);
    out
}

fn production_membership_from_cluster_view(
    cluster: &DevelopmentClusterView,
) -> Result<ProductionMembershipState, Box<dyn std::error::Error>> {
    let local_node = cluster
        .nodes
        .iter()
        .find(|node| node.node_id == cluster.local_node_id)
        .ok_or_else(|| format!("local node [{}] is missing", cluster.local_node_id))?;
    let mut state = ProductionMembershipState::bootstrap(
        cluster.cluster_name.clone(),
        cluster.cluster_uuid.clone(),
        cluster.local_node_id.clone(),
        os_node::MembershipNode::live(
            local_node.node_id.clone(),
            local_node.node_name.clone(),
            local_node.roles.clone(),
            cluster.cluster_uuid.clone(),
            1,
            0,
        ),
    )?;
    for (offset, node) in cluster
        .nodes
        .iter()
        .filter(|node| node.node_id != cluster.local_node_id)
        .enumerate()
    {
        state.join_node(os_node::MembershipNode::live(
            node.node_id.clone(),
            node.node_name.clone(),
            node.roles.clone(),
            cluster.cluster_uuid.clone(),
            offset as u64 + 2,
            0,
        ))?;
    }
    Ok(state)
}

fn effective_extension_registry(
    config: &DaemonConfig,
) -> Result<ExtensionBoundaryRegistry, Box<dyn std::error::Error>> {
    let mut registry = if let Some(manifest_path) = config.extension_manifest_path.as_ref() {
        ExtensionBoundaryRegistry::load_manifest(manifest_path)?
    } else {
        ExtensionBoundaryRegistry::default()
    };
    if let Some(enabled) = config.extension_registry_overrides.knn_plugin_enabled {
        registry.knn_plugin_enabled = enabled;
    }
    if let Some(enabled) = config.extension_registry_overrides.ml_commons_enabled {
        registry.ml_commons_enabled = enabled;
    }
    Ok(registry)
}

#[cfg(unix)]
fn install_shutdown_signal_handlers() {
    const SIGINT: i32 = 2;
    const SIGTERM: i32 = 15;

    extern "C" {
        fn signal(signum: i32, handler: extern "C" fn(i32)) -> usize;
    }

    extern "C" fn request_shutdown(_signum: i32) {
        SHUTDOWN_REQUESTED.store(true, Ordering::SeqCst);
    }

    unsafe {
        signal(SIGINT, request_shutdown);
        signal(SIGTERM, request_shutdown);
    }
}

#[cfg(not(unix))]
fn install_shutdown_signal_handlers() {}

#[derive(Clone, Debug)]
struct DaemonConfig {
    host: IpAddr,
    port: u16,
    transport_host: IpAddr,
    transport_port: u16,
    node_id: String,
    node_name: String,
    cluster_name: String,
    seed_hosts: Vec<String>,
    data_path: PathBuf,
    roles: Vec<String>,
    mode: DaemonMode,
    development_security_mode: DevelopmentSecurityMode,
    production_security_bootstrap: ProductionSecurityBootstrapConfig,
    java_write_forwarding_validated: bool,
    seed_peer_identity: Option<InteropSeedPeerIdentityManifest>,
    seed_peer_identities: Vec<InteropSeedPeerIdentityManifest>,
    #[cfg_attr(not(test), allow(dead_code))]
    extension_registry: ExtensionBoundaryRegistry,
    extension_registry_overrides: ExtensionRegistryOverrideConfig,
    extension_manifest_path: Option<PathBuf>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct ProductionSecurityBootstrapConfig {
    http_tls_certificate_path: Option<PathBuf>,
    http_tls_private_key_path: Option<PathBuf>,
    transport_tls_certificate_path: Option<PathBuf>,
    transport_tls_private_key_path: Option<PathBuf>,
    authentication_users_path: Option<PathBuf>,
}

impl DaemonConfig {
    fn mixed_java_native_transport_join_participation_enabled(&self) -> bool {
        self.java_write_forwarding_validated
            && !self.seed_peer_identities.is_empty()
            && self
                .seed_hosts
                .iter()
                .any(|seed_host| seed_host != &self.local_transport_address())
    }
}

trait DevelopmentClusterViewConfig {
    fn node_id(&self) -> &str;
    fn node_name(&self) -> &str;
    fn cluster_name(&self) -> &str;
    fn seed_hosts(&self) -> &[String];
    fn roles(&self) -> Vec<String>;
    fn local_http_address(&self) -> String;
    fn local_transport_address(&self) -> String;
    fn seed_peer_identity(&self) -> Option<&InteropSeedPeerIdentityManifest> {
        None
    }
    fn seed_peer_identities(&self) -> &[InteropSeedPeerIdentityManifest] {
        &[]
    }
}

impl DevelopmentClusterViewConfig for DaemonConfig {
    fn node_id(&self) -> &str {
        &self.node_id
    }

    fn node_name(&self) -> &str {
        &self.node_name
    }

    fn cluster_name(&self) -> &str {
        &self.cluster_name
    }

    fn seed_hosts(&self) -> &[String] {
        &self.seed_hosts
    }

    fn roles(&self) -> Vec<String> {
        self.roles.clone()
    }

    fn local_http_address(&self) -> String {
        SocketAddr::new(self.host, self.port).to_string()
    }

    fn local_transport_address(&self) -> String {
        SocketAddr::new(self.transport_host, self.transport_port).to_string()
    }

    fn seed_peer_identity(&self) -> Option<&InteropSeedPeerIdentityManifest> {
        self.seed_peer_identity.as_ref()
    }

    fn seed_peer_identities(&self) -> &[InteropSeedPeerIdentityManifest] {
        &self.seed_peer_identities
    }
}

#[cfg(test)]
#[derive(Clone, Debug, Eq, PartialEq)]
struct TransportConfig {
    bind_address: String,
    publish_address: String,
    connect_timeout_ms: u64,
    tcp_nodelay: bool,
}

#[cfg(test)]
#[derive(Clone, Debug, Eq, PartialEq)]
struct RestApiConfig {
    enabled: bool,
    bind_address: String,
    publish_address: Option<String>,
}

#[cfg(test)]
#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct SearchNodeConfig {}

#[cfg(test)]
#[derive(Clone, Debug, Eq, PartialEq)]
struct NodeConfig {
    node_name: String,
    cluster_name: String,
    data_dir: PathBuf,
    gateway_dir: PathBuf,
    transport: TransportConfig,
    discovery: DiscoveryConfig,
    bootstrap_cluster_manager_nodes: Vec<String>,
    seed_hosts: Vec<String>,
    rest_api: RestApiConfig,
    search: SearchNodeConfig,
}

#[cfg(test)]
impl DevelopmentClusterViewConfig for NodeConfig {
    fn node_id(&self) -> &str {
        &self.node_name
    }

    fn node_name(&self) -> &str {
        &self.node_name
    }

    fn cluster_name(&self) -> &str {
        &self.cluster_name
    }

    fn seed_hosts(&self) -> &[String] {
        &self.seed_hosts
    }

    fn roles(&self) -> Vec<String> {
        default_roles()
    }

    fn local_http_address(&self) -> String {
        self.rest_api.bind_address.clone()
    }

    fn local_transport_address(&self) -> String {
        self.transport.bind_address.clone()
    }
}

#[derive(Clone, Debug, Eq, PartialEq, serde::Deserialize)]
struct InteropSeedPeerIdentityNode {
    name: String,
    id: String,
    ephemeral_id: String,
    host_name: String,
    host_address: String,
    http_address: Option<String>,
    transport_address: String,
    version_id: u32,
    roles: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, serde::Deserialize)]
struct InteropSeedPeerIdentityManifest {
    peer_identity_present: bool,
    cluster_name: String,
    discovery_node: InteropSeedPeerIdentityNode,
}

fn load_seed_peer_identity_manifest(
    path: &std::path::Path,
) -> Result<InteropSeedPeerIdentityManifest, Box<dyn std::error::Error>> {
    let raw = fs::read(path)?;
    let manifest: InteropSeedPeerIdentityManifest = serde_json::from_slice(&raw)?;
    if !manifest.peer_identity_present {
        return Err(format!(
            "seed peer identity manifest [{}] does not contain peer identity",
            path.display()
        )
        .into());
    }
    if manifest.discovery_node.id.trim().is_empty()
        || manifest.discovery_node.name.trim().is_empty()
        || manifest.discovery_node.transport_address.trim().is_empty()
    {
        return Err(format!(
            "seed peer identity manifest [{}] is missing discovery node identity fields",
            path.display()
        )
        .into());
    }
    if manifest.discovery_node.roles.is_empty() {
        return Err(format!(
            "seed peer identity manifest [{}] must contain at least one role",
            path.display()
        )
        .into());
    }
    validate_seed_host(&manifest.discovery_node.transport_address)
        .map_err(|error| format!("seed peer identity manifest [{}] {error}", path.display()))?;
    Ok(manifest)
}

fn load_seed_peer_identity_manifests(
    value: &str,
) -> Result<Vec<InteropSeedPeerIdentityManifest>, Box<dyn std::error::Error>> {
    let mut manifests = Vec::new();
    for raw_path in parse_csv(value) {
        manifests.push(load_seed_peer_identity_manifest(std::path::Path::new(
            &raw_path,
        ))?);
    }
    Ok(manifests)
}

#[derive(Clone, Debug, Default)]
struct ExtensionRegistryOverrideConfig {
    knn_plugin_enabled: Option<bool>,
    ml_commons_enabled: Option<bool>,
}

fn daemon_config_from_env_and_args() -> Result<DaemonConfig, Box<dyn std::error::Error>> {
    let vars = env::vars().collect::<BTreeMap<_, _>>();
    daemon_config_from_sources(&vars, env::args().skip(1))
}

fn daemon_config_from_sources<I>(
    vars: &BTreeMap<String, String>,
    args: I,
) -> Result<DaemonConfig, Box<dyn std::error::Error>>
where
    I: IntoIterator<Item = String>,
{
    let mut host = env_parse(vars, "STEELSEARCH_HTTP_HOST")?
        .ok()
        .unwrap_or(IpAddr::V4(Ipv4Addr::LOCALHOST));
    let mut port = env_parse(vars, "STEELSEARCH_HTTP_PORT")?.unwrap_or(9200);
    let mut transport_host = env_parse(vars, "STEELSEARCH_TRANSPORT_HOST")?
        .ok()
        .unwrap_or(IpAddr::V4(Ipv4Addr::LOCALHOST));
    let mut transport_port = env_parse(vars, "STEELSEARCH_TRANSPORT_PORT")?.unwrap_or(9300);
    let mut node_id = vars.get("STEELSEARCH_NODE_ID").cloned().unwrap_or_default();
    let mut node_name = vars
        .get("STEELSEARCH_NODE_NAME")
        .cloned()
        .unwrap_or_else(|| "steelsearch-dev-node".to_string());
    let mut cluster_name = vars
        .get("STEELSEARCH_CLUSTER_NAME")
        .cloned()
        .unwrap_or_else(|| "steelsearch-dev".to_string());
    let mut seed_hosts = vars
        .get("STEELSEARCH_DISCOVERY_SEED_HOSTS")
        .map(|value| parse_csv(value))
        .unwrap_or_default();
    let mut data_path = vars
        .get("STEELSEARCH_DATA_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("data/steelsearch"));
    let mut roles_explicit = vars.contains_key("STEELSEARCH_NODE_ROLES");
    let mut roles = vars
        .get("STEELSEARCH_NODE_ROLES")
        .map(|value| parse_csv(value))
        .filter(|roles| !roles.is_empty())
        .unwrap_or_else(default_roles);
    let mut development_security_mode = vars
        .get("STEELSEARCH_DEVELOPMENT_SECURITY_MODE")
        .map(|value| parse_development_security_mode(value))
        .transpose()?
        .unwrap_or(DevelopmentSecurityMode::Disabled);
    let mut production_security_bootstrap = ProductionSecurityBootstrapConfig {
        http_tls_certificate_path: vars
            .get("STEELSEARCH_HTTP_TLS_CERTIFICATE")
            .map(PathBuf::from),
        http_tls_private_key_path: vars.get("STEELSEARCH_HTTP_TLS_PRIVATE_KEY").map(PathBuf::from),
        transport_tls_certificate_path: vars
            .get("STEELSEARCH_TRANSPORT_TLS_CERTIFICATE")
            .map(PathBuf::from),
        transport_tls_private_key_path: vars
            .get("STEELSEARCH_TRANSPORT_TLS_PRIVATE_KEY")
            .map(PathBuf::from),
        authentication_users_path: vars
            .get("STEELSEARCH_AUTHENTICATION_USERS_FILE")
            .map(PathBuf::from),
    };
    let mut extension_manifest_path = vars.get("STEELSEARCH_EXTENSION_MANIFEST").map(PathBuf::from);
    let mut extension_registry_overrides = ExtensionRegistryOverrideConfig {
        knn_plugin_enabled: parse_bool_env(vars, "STEELSEARCH_ENABLE_KNN_PLUGIN")?,
        ml_commons_enabled: parse_bool_env(vars, "STEELSEARCH_ENABLE_ML_COMMONS")?,
    };
    let mut extension_registry = ExtensionBoundaryRegistry::default();
    if let Some(enabled) = extension_registry_overrides.knn_plugin_enabled {
        extension_registry.knn_plugin_enabled = enabled;
    }
    if let Some(enabled) = extension_registry_overrides.ml_commons_enabled {
        extension_registry.ml_commons_enabled = enabled;
    }
    let mut mode = vars
        .get("STEELSEARCH_MODE")
        .map(|value| parse_daemon_mode(value))
        .transpose()?
        .unwrap_or(DaemonMode::Development);
    let mut java_write_forwarding_validated =
        parse_bool_env(vars, "STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED")?.unwrap_or(false);
    let mut seed_peer_identity_manifest_path = vars
        .get("STEELSEARCH_INTEROP_SEED_PEER_IDENTITY_MANIFEST")
        .map(PathBuf::from);

    let mut args = args.into_iter();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--http.host" => {
                let value = args.next().ok_or("--http.host requires a value")?;
                host = value.parse()?;
            }
            "--http.port" => {
                let value = args.next().ok_or("--http.port requires a value")?;
                port = value.parse()?;
            }
            "--transport.host" => {
                let value = args.next().ok_or("--transport.host requires a value")?;
                transport_host = value.parse()?;
            }
            "--transport.port" => {
                let value = args.next().ok_or("--transport.port requires a value")?;
                transport_port = value.parse()?;
            }
            "--node.id" => {
                node_id = args.next().ok_or("--node.id requires a value")?;
            }
            "--node.name" => {
                node_name = args.next().ok_or("--node.name requires a value")?;
            }
            "--cluster.name" => {
                cluster_name = args.next().ok_or("--cluster.name requires a value")?;
            }
            "--discovery.seed_hosts" => {
                let value = args
                    .next()
                    .ok_or("--discovery.seed_hosts requires a value")?;
                seed_hosts = parse_csv(&value);
            }
            "--path.data" => {
                data_path = PathBuf::from(args.next().ok_or("--path.data requires a value")?);
            }
            "--node.roles" => {
                let value = args.next().ok_or("--node.roles requires a value")?;
                roles = parse_csv(&value);
                roles_explicit = true;
            }
            "--mode" => {
                let value = args.next().ok_or("--mode requires a value")?;
                mode = parse_daemon_mode(&value)?;
            }
            "--development.security_mode" => {
                let value = args
                    .next()
                    .ok_or("--development.security_mode requires a value")?;
                development_security_mode = parse_development_security_mode(&value)?;
            }
            "--security.http_tls_certificate" => {
                production_security_bootstrap.http_tls_certificate_path = Some(PathBuf::from(
                    args.next()
                        .ok_or("--security.http_tls_certificate requires a value")?,
                ));
            }
            "--security.http_tls_private_key" => {
                production_security_bootstrap.http_tls_private_key_path = Some(PathBuf::from(
                    args.next()
                        .ok_or("--security.http_tls_private_key requires a value")?,
                ));
            }
            "--security.transport_tls_certificate" => {
                production_security_bootstrap.transport_tls_certificate_path = Some(PathBuf::from(
                    args.next()
                        .ok_or("--security.transport_tls_certificate requires a value")?,
                ));
            }
            "--security.transport_tls_private_key" => {
                production_security_bootstrap.transport_tls_private_key_path = Some(PathBuf::from(
                    args.next()
                        .ok_or("--security.transport_tls_private_key requires a value")?,
                ));
            }
            "--security.authentication_users_file" => {
                production_security_bootstrap.authentication_users_path = Some(PathBuf::from(
                    args.next()
                        .ok_or("--security.authentication_users_file requires a value")?,
                ));
            }
            "--extensions.knn" => {
                let value = args.next().ok_or("--extensions.knn requires a value")?;
                let enabled = parse_bool_flag(&value)?;
                extension_registry_overrides.knn_plugin_enabled = Some(enabled);
                extension_registry.knn_plugin_enabled = enabled;
            }
            "--extensions.ml_commons" => {
                let value = args
                    .next()
                    .ok_or("--extensions.ml_commons requires a value")?;
                let enabled = parse_bool_flag(&value)?;
                extension_registry_overrides.ml_commons_enabled = Some(enabled);
                extension_registry.ml_commons_enabled = enabled;
            }
            "--extensions.manifest" => {
                extension_manifest_path = Some(PathBuf::from(
                    args.next().ok_or("--extensions.manifest requires a value")?,
                ));
            }
            "--interop.java_write_forwarding_validated" => {
                let value = args
                    .next()
                    .ok_or("--interop.java_write_forwarding_validated requires a value")?;
                java_write_forwarding_validated = parse_bool_flag(&value)?;
            }
            "--interop.seed_peer_identity_manifest" => {
                seed_peer_identity_manifest_path = Some(PathBuf::from(
                    args.next()
                        .ok_or("--interop.seed_peer_identity_manifest requires a value")?,
                ));
            }
            "--help" | "-h" => {
                print_help();
                std::process::exit(0);
            }
            other if other == "-E" || other.starts_with("-E") => {
                return Err(format!(
                    "unsupported OpenSearch -E config setting [{other}]; use explicit steelsearch daemon flags or STEELSEARCH_* environment variables"
                )
                .into());
            }
            other => return Err(format!("unknown argument [{other}]").into()),
        }
    }
    if node_id.is_empty() {
        node_id = node_name.clone();
    }
    if roles.is_empty() {
        return Err("--node.roles must contain at least one role".into());
    }
    let seed_peer_identities = seed_peer_identity_manifest_path
        .as_ref()
        .map(|path| load_seed_peer_identity_manifests(&path.to_string_lossy()))
        .transpose()?
        .unwrap_or_default();
    if !roles_explicit && !seed_peer_identities.is_empty() {
        roles = interop_data_node_roles();
    }
    let seed_peer_identity = seed_peer_identities.first().cloned();
    let config = DaemonConfig {
        host,
        port,
        transport_host,
        transport_port,
        node_id,
        node_name,
        cluster_name,
        seed_hosts,
        data_path,
        roles,
        mode,
        development_security_mode,
        production_security_bootstrap,
        java_write_forwarding_validated,
        seed_peer_identity,
        seed_peer_identities,
        extension_registry,
        extension_registry_overrides,
        extension_manifest_path,
    };
    validate_startup_preflight(&config)?;
    Ok(config)
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DaemonMode {
    Development,
    Production,
}

fn parse_daemon_mode(value: &str) -> Result<DaemonMode, Box<dyn std::error::Error>> {
    match value {
        "development" => Ok(DaemonMode::Development),
        "production" => Ok(DaemonMode::Production),
        other => Err(format!("unknown daemon mode [{other}]").into()),
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DevelopmentSecurityMode {
    Disabled,
}

impl DevelopmentSecurityMode {
    fn as_str(self) -> &'static str {
        match self {
            Self::Disabled => "disabled",
        }
    }
}

fn parse_development_security_mode(
    value: &str,
) -> Result<DevelopmentSecurityMode, Box<dyn std::error::Error>> {
    match value {
        "disabled" => Ok(DevelopmentSecurityMode::Disabled),
        other => Err(format!("unknown development security mode [{other}]").into()),
    }
}

fn parse_bool_flag(value: &str) -> Result<bool, Box<dyn std::error::Error>> {
    match value {
        "true" | "1" | "yes" | "on" | "enabled" => Ok(true),
        "false" | "0" | "no" | "off" | "disabled" => Ok(false),
        other => Err(format!("invalid boolean value [{other}]").into()),
    }
}

fn parse_bool_env(
    vars: &BTreeMap<String, String>,
    key: &str,
) -> Result<Option<bool>, Box<dyn std::error::Error>> {
    match vars.get(key) {
        Some(value) => Ok(Some(parse_bool_flag(value)?)),
        None => Ok(None),
    }
}

fn env_parse<T>(
    vars: &BTreeMap<String, String>,
    key: &str,
) -> Result<Result<T, std::env::VarError>, Box<dyn std::error::Error>>
where
    T: std::str::FromStr,
    T::Err: std::error::Error + 'static,
{
    match vars.get(key) {
        Some(value) => Ok(Ok(value.parse()?)),
        None => Ok(Err(std::env::VarError::NotPresent)),
    }
}

fn parse_csv(value: &str) -> Vec<String> {
    value
        .split(',')
        .map(str::trim)
        .filter(|item| !item.is_empty())
        .map(ToOwned::to_owned)
        .collect()
}

fn default_roles() -> Vec<String> {
    vec![
        "cluster_manager".to_string(),
        "data".to_string(),
        "ingest".to_string(),
        "remote_cluster_client".to_string(),
    ]
}

fn interop_data_node_roles() -> Vec<String> {
    vec![
        "data".to_string(),
        "ingest".to_string(),
        "remote_cluster_client".to_string(),
    ]
}

fn validate_startup_preflight(config: &DaemonConfig) -> Result<(), Box<dyn std::error::Error>> {
    let blockers = startup_preflight_blockers(config);
    if !blockers.is_empty() {
        let mut message = String::from("startup preflight is blocked:");
        for blocker in blockers {
            message.push_str("\n- ");
            message.push_str(&blocker);
        }
        return Err(message.into());
    }
    Ok(())
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct StartupReadinessReport {
    ready: bool,
    blockers: Vec<String>,
}

fn startup_readiness_report(config: &DaemonConfig) -> StartupReadinessReport {
    let blockers = startup_preflight_blockers(config);
    StartupReadinessReport {
        ready: blockers.is_empty(),
        blockers,
    }
}

fn startup_preflight_blockers(config: &DaemonConfig) -> Vec<String> {
    let mut blockers = Vec::new();

    if config.node_name.trim().is_empty() {
        blockers.push("[daemon] --node.name must not be empty".to_string());
    }
    if config.cluster_name.trim().is_empty() {
        blockers.push("[daemon] --cluster.name must not be empty".to_string());
    }
    if config.node_id.trim().is_empty() {
        blockers.push("[daemon] --node.id must not be empty".to_string());
    }
    if config.host == config.transport_host && config.port == config.transport_port {
        blockers.push(
            "[daemon] --http.port and --transport.port must not resolve to the same socket"
                .to_string(),
        );
    }
    if !config.roles.iter().any(|role| role == "cluster_manager") && config.seed_hosts.is_empty() {
        blockers.push(
            "[membership] non-cluster-manager nodes must set --discovery.seed_hosts so startup has a bootstrap peer"
                .to_string(),
        );
    }

    let mut seen_seed_hosts = std::collections::BTreeSet::new();
    for seed_host in &config.seed_hosts {
        if let Err(error) = validate_seed_host(seed_host) {
            blockers.push(format!("[multi_node] {error}"));
        }
        if !seen_seed_hosts.insert(seed_host.clone()) {
            blockers.push(format!(
                "[multi_node] duplicate discovery seed host [{seed_host}]"
            ));
        }
    }

    if config.java_write_forwarding_validated
        && config
            .seed_hosts
            .iter()
            .any(|seed_host| seed_host != &config.local_transport_address())
        && config.seed_peer_identities.is_empty()
    {
        blockers.push(
            "[interop] mixed Java same-cluster participation requires --interop.seed_peer_identity_manifest with actual Java seed peer identity before native transport join is implemented"
                .to_string(),
        );
    }

    let mut seen_seed_identity_addresses = std::collections::BTreeSet::new();
    for seed_peer_identity in &config.seed_peer_identities {
        if seed_peer_identity.cluster_name != config.cluster_name {
            blockers.push(format!(
                "[interop] seed peer identity cluster [{}] does not match configured cluster [{}]",
                seed_peer_identity.cluster_name, config.cluster_name
            ));
        }
        let manifest_transport_address = &seed_peer_identity.discovery_node.transport_address;
        if manifest_transport_address == &config.local_transport_address() {
            blockers.push(format!(
                "[interop] seed peer identity transport address [{}] must not point at the local transport address",
                manifest_transport_address
            ));
        }
        if !config
            .seed_hosts
            .iter()
            .any(|seed_host| seed_host == manifest_transport_address)
        {
            blockers.push(format!(
                "[interop] seed peer identity transport address [{}] is not present in --discovery.seed_hosts",
                manifest_transport_address
            ));
        }
        if !seen_seed_identity_addresses.insert(manifest_transport_address.clone()) {
            blockers.push(format!(
                "[interop] duplicate seed peer identity transport address [{}]",
                manifest_transport_address
            ));
        }
    }

    if let Ok(metadata) = fs::metadata(&config.data_path) {
        if !metadata.is_dir() {
            blockers.push(format!(
                "[daemon] --path.data must be a directory: {}",
                config.data_path.display()
            ));
        }
    }
    if !blockers.iter().any(|blocker| blocker.contains("--path.data must be a directory")) {
        if let Err(error) = fs::create_dir_all(&config.data_path) {
            blockers.push(format!(
                "[daemon] --path.data must be creatable ({}): {error}",
                config.data_path.display()
            ));
        } else if let Err(error) = validate_data_path_writable(&config.data_path) {
            blockers.push(format!("[daemon] {error}"));
        }
    }

    let view = development_cluster_view(config, "validation-cluster-uuid");
    let mut node_ids = std::collections::BTreeSet::new();
    for node in view.nodes {
        if !node_ids.insert(node.node_id.clone()) {
            blockers.push(format!(
                "[membership] duplicate development node id [{}]",
                node.node_id
            ));
        }
    }
    if config.mode == DaemonMode::Production {
        blockers.extend(production_security_bootstrap_blockers(
            &config.production_security_bootstrap,
        ));
        if let Err(error) = validate_production_mode_request(
            &SecurityBoundaryPolicy::default(),
            ReleaseReadinessChecklist::default(),
        ) {
            blockers.push(format!("[production] Steelsearch {error}"));
        }
    }
    blockers
}

fn production_security_bootstrap_blockers(
    bootstrap: &ProductionSecurityBootstrapConfig,
) -> Vec<String> {
    let required_files = [
        (
            "HTTP TLS certificate",
            bootstrap.http_tls_certificate_path.as_ref(),
        ),
        (
            "HTTP TLS private key",
            bootstrap.http_tls_private_key_path.as_ref(),
        ),
        (
            "transport TLS certificate",
            bootstrap.transport_tls_certificate_path.as_ref(),
        ),
        (
            "transport TLS private key",
            bootstrap.transport_tls_private_key_path.as_ref(),
        ),
        (
            "authentication users file",
            bootstrap.authentication_users_path.as_ref(),
        ),
    ];
    let mut blockers = Vec::new();
    for (name, path) in required_files {
        match path {
            None => blockers.push(format!("[security] production {name} is required")),
            Some(path) => match fs::metadata(path) {
                Ok(metadata) if metadata.is_file() => {}
                Ok(_) => blockers.push(format!(
                    "[security] production {name} must be a file: {}",
                    path.display()
                )),
                Err(error) => blockers.push(format!(
                    "[security] production {name} must be readable ({}): {error}",
                    path.display()
                )),
            },
        }
    }
    if let Some(path) = bootstrap.authentication_users_path.as_ref() {
        if let Err(error) = validate_production_authentication_users_file(path) {
            blockers.push(format!(
                "[security] production authentication users file is invalid ({}): {error}",
                path.display()
            ));
        }
    }
    for (name, path) in [
        (
            "HTTP TLS certificate",
            bootstrap.http_tls_certificate_path.as_ref(),
        ),
        (
            "transport TLS certificate",
            bootstrap.transport_tls_certificate_path.as_ref(),
        ),
    ] {
        if let Some(path) = path {
            if let Err(error) = validate_production_tls_certificate_file(path) {
                blockers.push(format!(
                    "[security] production {name} is invalid ({}): {error}",
                    path.display()
                ));
            }
        }
    }
    for (name, path) in [
        (
            "HTTP TLS private key",
            bootstrap.http_tls_private_key_path.as_ref(),
        ),
        (
            "transport TLS private key",
            bootstrap.transport_tls_private_key_path.as_ref(),
        ),
    ] {
        if let Some(path) = path {
            if let Err(error) = validate_production_tls_private_key_file(path) {
                blockers.push(format!(
                    "[security] production {name} is invalid ({}): {error}",
                    path.display()
                ));
            }
        }
    }
    blockers
}

fn validate_production_authentication_users_file(path: &Path) -> Result<(), String> {
    let raw = fs::read_to_string(path).map_err(|error| format!("must be readable: {error}"))?;
    parse_authentication_users_json(&raw).map_err(|error| error.to_string())?;
    Ok(())
}

fn validate_production_tls_certificate_file(path: &Path) -> Result<(), String> {
    let raw = fs::read_to_string(path).map_err(|error| format!("must be readable: {error}"))?;
    if contains_pem_private_key_markers(&raw) {
        return Err("must not contain PEM private key markers".to_string());
    }
    if raw.contains("-----BEGIN CERTIFICATE-----") && raw.contains("-----END CERTIFICATE-----") {
        return Ok(());
    }
    Err("must contain PEM certificate markers".to_string())
}

fn validate_production_tls_private_key_file(path: &Path) -> Result<(), String> {
    let raw = fs::read_to_string(path).map_err(|error| format!("must be readable: {error}"))?;
    if raw.contains("-----BEGIN CERTIFICATE-----") || raw.contains("-----END CERTIFICATE-----") {
        return Err("must not contain PEM certificate markers".to_string());
    }
    if contains_pem_private_key_markers(&raw) {
        return Ok(());
    }
    Err("must contain PEM private key markers".to_string())
}

fn contains_pem_private_key_markers(raw: &str) -> bool {
    let has_private_key =
        raw.contains("-----BEGIN PRIVATE KEY-----") && raw.contains("-----END PRIVATE KEY-----");
    let has_rsa_private_key = raw.contains("-----BEGIN RSA PRIVATE KEY-----")
        && raw.contains("-----END RSA PRIVATE KEY-----");
    let has_ec_private_key =
        raw.contains("-----BEGIN EC PRIVATE KEY-----")
            && raw.contains("-----END EC PRIVATE KEY-----");
    has_private_key || has_rsa_private_key || has_ec_private_key
}

fn validate_seed_host(seed_host: &str) -> Result<(), Box<dyn std::error::Error>> {
    let (host, port) = seed_host
        .rsplit_once(':')
        .ok_or_else(|| format!("invalid discovery seed host [{seed_host}]: expected host:port"))?;
    if host.trim().is_empty() {
        return Err(format!("invalid discovery seed host [{seed_host}]: missing host").into());
    }
    let _: u16 = port
        .parse()
        .map_err(|_| format!("invalid discovery seed host [{seed_host}]: invalid port"))?;
    Ok(())
}

fn validate_data_path_writable(path: &std::path::Path) -> Result<(), Box<dyn std::error::Error>> {
    let probe = path.join(".steelsearch-preflight-write-check");
    let mut file = fs::File::create(&probe).map_err(|error| {
        format!(
            "--path.data must be writable (failed to create {}): {error}",
            probe.display()
        )
    })?;
    file.write_all(b"steelsearch-preflight").map_err(|error| {
        format!(
            "--path.data must be writable (failed to write {}): {error}",
            probe.display()
        )
    })?;
    drop(file);
    let _ = fs::remove_file(probe);
    Ok(())
}

fn development_cluster_view(
    config: &impl DevelopmentClusterViewConfig,
    cluster_uuid: &str,
) -> DevelopmentClusterView {
    let local_http_address = config.local_http_address();
    let local_transport_address = config.local_transport_address();
    let mut nodes = vec![DevelopmentClusterNode {
        node_id: config.node_id().to_string(),
        node_name: config.node_name().to_string(),
        http_address: Some(local_http_address),
        transport_address: local_transport_address.clone(),
        roles: config.roles(),
        local: true,
    }];

    for (index, seed_host) in config.seed_hosts().iter().enumerate() {
        if seed_host == &local_transport_address {
            continue;
        }
        if let Some(seed_peer_identity) = config
            .seed_peer_identities()
            .iter()
            .find(|manifest| manifest.discovery_node.transport_address == *seed_host)
        {
                nodes.push(DevelopmentClusterNode {
                    node_id: seed_peer_identity.discovery_node.id.clone(),
                    node_name: seed_peer_identity.discovery_node.name.clone(),
                    http_address: seed_peer_identity.discovery_node.http_address.clone(),
                    transport_address: seed_peer_identity.discovery_node.transport_address.clone(),
                    roles: seed_peer_identity.discovery_node.roles.clone(),
                    local: false,
                });
                continue;
        }
        nodes.push(DevelopmentClusterNode {
            node_id: format!("seed-{}-{}", index + 1, sanitize_node_id(seed_host)),
            node_name: format!("seed-{}", index + 1),
            http_address: None,
            transport_address: seed_host.clone(),
            roles: default_roles(),
            local: false,
        });
    }

    DevelopmentClusterView {
        cluster_name: config.cluster_name().to_string(),
        cluster_uuid: cluster_uuid.to_string(),
        local_node_id: config.node_id().to_string(),
        nodes,
        coordination: None,
    }
}

#[cfg(test)]
fn committed_gateway_coordination_state(
    local_node_id: &str,
    state_uuid: &str,
    version: i64,
) -> PersistedPublicationState {
    PersistedPublicationState {
        current_term: 1,
        last_accepted_version: version,
        last_accepted_state_uuid: state_uuid.to_string(),
        cluster_manager_node_id: Some(local_node_id.to_string()),
        last_accepted_voting_configuration: BTreeSet::from([local_node_id.to_string()]),
        last_committed_voting_configuration: BTreeSet::from([local_node_id.to_string()]),
        voting_config_exclusions: Default::default(),
        active_publication_round: None,
        last_completed_publication_round: Some(os_node::PublicationRoundState {
            state_uuid: state_uuid.to_string(),
            version,
            term: 1,
            target_nodes: BTreeSet::from([local_node_id.to_string()]),
            acknowledged_nodes: BTreeSet::from([local_node_id.to_string()]),
            applied_nodes: BTreeSet::from([local_node_id.to_string()]),
            missing_nodes: BTreeSet::new(),
            proposal_transport_failures: BTreeMap::new(),
            acknowledgement_transport_failures: BTreeMap::new(),
            apply_transport_failures: BTreeMap::new(),
            required_quorum: 1,
            committed: true,
        }),
        local_fence_reason: None,
        quorum_lost_at_tick: None,
        fault_detection: Default::default(),
    }
}

#[cfg(test)]
fn committed_gateway_metadata_commit_state(
    local_node_id: &str,
    state_uuid: &str,
    version: i64,
) -> os_node::PersistedGatewayMetadataCommitState {
    os_node::PersistedGatewayMetadataCommitState {
        committed_version: version,
        committed_state_uuid: state_uuid.to_string(),
        target_node_ids: BTreeSet::from([local_node_id.to_string()]),
        applied_node_ids: BTreeSet::from([local_node_id.to_string()]),
    }
}

#[cfg(test)]
fn unique_test_path(prefix: &str) -> PathBuf {
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    std::env::temp_dir().join(format!("{prefix}-{nanos}"))
}

fn restore_gateway_startup_cluster_view(
    config: &impl DevelopmentClusterViewConfig,
    cluster_uuid: &str,
    persisted_gateway_state: Option<&PersistedGatewayState>,
) -> Result<DevelopmentClusterView, Box<dyn std::error::Error>> {
    let expected_view = development_cluster_view(config, cluster_uuid);
    let Some(persisted_gateway_state) = persisted_gateway_state else {
        return Ok(expected_view);
    };
    validate_gateway_startup_state(&expected_view, &persisted_gateway_state.cluster_state)?;
    Ok(persisted_gateway_state.cluster_state.clone())
}

fn validate_gateway_startup_state(
    expected: &DevelopmentClusterView,
    restored: &DevelopmentClusterView,
) -> Result<(), Box<dyn std::error::Error>> {
    if restored.cluster_name != expected.cluster_name {
        return Err(format!(
            "gateway manifest cluster name [{}] does not match configured cluster [{}]",
            restored.cluster_name, expected.cluster_name
        )
        .into());
    }
    if restored.cluster_uuid != expected.cluster_uuid {
        return Err(format!(
            "gateway manifest cluster UUID [{}] does not match configured cluster UUID [{}]",
            restored.cluster_uuid, expected.cluster_uuid
        )
        .into());
    }
    if restored.local_node_id != expected.local_node_id {
        return Err(format!(
            "gateway manifest local node [{}] does not match configured local node [{}]",
            restored.local_node_id, expected.local_node_id
        )
        .into());
    }
    let expected_local_node = expected
        .nodes
        .iter()
        .find(|node| node.node_id == expected.local_node_id)
        .ok_or_else(|| {
            format!(
                "expected local node [{}] is missing from startup cluster view",
                expected.local_node_id
            )
        })?;
    let restored_local_node = restored
        .nodes
        .iter()
        .find(|node| node.node_id == restored.local_node_id)
        .ok_or_else(|| {
            format!(
                "gateway manifest local node [{}] is missing from restored cluster view",
                restored.local_node_id
            )
        })?;
    if restored_local_node.node_name != expected_local_node.node_name {
        return Err(format!(
            "gateway manifest local node name [{}] does not match configured node name [{}]",
            restored_local_node.node_name, expected_local_node.node_name
        )
        .into());
    }
    if restored_local_node.transport_address != expected_local_node.transport_address {
        return Err(format!(
            "gateway manifest transport address [{}] does not match configured transport address [{}]",
            restored_local_node.transport_address, expected_local_node.transport_address
        )
        .into());
    }
    if restored_local_node.roles != expected_local_node.roles {
        return Err(format!(
            "gateway manifest roles {:?} do not match configured roles {:?}",
            restored_local_node.roles, expected_local_node.roles
        )
        .into());
    }
    if !restored_local_node.local {
        return Err(format!(
            "gateway manifest local node [{}] is not marked local",
            restored_local_node.node_id
        )
        .into());
    }
    Ok(())
}

fn restore_gateway_cluster_metadata_manifest(
    metadata_path: &std::path::Path,
    persisted_gateway_state: Option<&PersistedGatewayState>,
) -> std::io::Result<()> {
    let Some(persisted_gateway_state) = persisted_gateway_state else {
        return Ok(());
    };
    let Some(mut cluster_metadata_manifest) = persisted_gateway_state
        .cluster_metadata_manifest
        .as_ref()
        .cloned()
    else {
        return Ok(());
    };
    validate_gateway_metadata_replay_state(persisted_gateway_state)?;
    if let Some(routing_metadata) = persisted_gateway_state.routing_metadata.as_ref() {
        if let Some(manifest) = cluster_metadata_manifest.as_object_mut() {
            manifest.insert("routing_table".to_string(), routing_metadata.routing_table.clone());
            manifest.insert("allocation".to_string(), routing_metadata.allocation.clone());
        }
    }
    if let Some(metadata_state) = persisted_gateway_state.metadata_state.as_ref() {
        apply_gateway_metadata_state_to_manifest(&mut cluster_metadata_manifest, metadata_state);
    }
    if let Some(metadata_commit_state) = persisted_gateway_state.metadata_commit_state.as_ref() {
        apply_gateway_metadata_commit_state_to_manifest(
            &mut cluster_metadata_manifest,
            metadata_commit_state,
        );
    }
    if let Some(parent) = metadata_path.parent() {
        fs::create_dir_all(parent)?;
    }
    let temp_path = metadata_path.with_extension("tmp");
    fs::write(
        &temp_path,
        serde_json::to_vec_pretty(&cluster_metadata_manifest)
            .map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error))?,
    )?;
    fs::rename(temp_path, metadata_path)?;
    Ok(())
}

fn validate_gateway_metadata_replay_state(
    persisted_gateway_state: &PersistedGatewayState,
) -> std::io::Result<()> {
    let coordination_state = &persisted_gateway_state.coordination_state;
    let local_node_id = &persisted_gateway_state.cluster_state.local_node_id;
    let Some(metadata_commit_state) = persisted_gateway_state.metadata_commit_state.as_ref() else {
        return Ok(());
    };
    let last_completed_round = coordination_state
        .last_completed_publication_round
        .as_ref()
        .ok_or_else(|| {
            std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "gateway metadata replay requires a committed publication round",
            )
        })?;
    if !last_completed_round.committed {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            format!(
                "gateway metadata replay rejected: publication round [{}] is not committed",
                last_completed_round.state_uuid
            ),
        ));
    }
    if coordination_state.last_accepted_version != last_completed_round.version
        || coordination_state.last_accepted_state_uuid != last_completed_round.state_uuid
    {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            format!(
                "gateway metadata replay rejected: last accepted metadata [{}:{}] does not match committed round [{}:{}]",
                coordination_state.last_accepted_version,
                coordination_state.last_accepted_state_uuid,
                last_completed_round.version,
                last_completed_round.state_uuid
            ),
        ));
    }
    if metadata_commit_state.committed_version != last_completed_round.version
        || metadata_commit_state.committed_state_uuid != last_completed_round.state_uuid
    {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            format!(
                "gateway metadata replay rejected: explicit metadata commit [{}:{}] does not match committed publication round [{}:{}]",
                metadata_commit_state.committed_version,
                metadata_commit_state.committed_state_uuid,
                last_completed_round.version,
                last_completed_round.state_uuid
            ),
        ));
    }
    if let Some(active_round) = coordination_state.active_publication_round.as_ref() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            format!(
                "gateway metadata replay rejected: interrupted publication round [{}:{}] is still active",
                active_round.version, active_round.state_uuid
            ),
        ));
    }
    if !metadata_commit_state.applied_node_ids.contains(local_node_id) {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            format!(
                "gateway metadata replay rejected: local node [{}] did not apply committed metadata round [{}]",
                local_node_id, last_completed_round.state_uuid
            ),
        ));
    }
    let pending_apply_nodes = metadata_commit_state
        .target_node_ids
        .difference(&metadata_commit_state.applied_node_ids)
        .cloned()
        .collect::<std::collections::BTreeSet<_>>();
    if !pending_apply_nodes.is_empty() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            format!(
                "gateway metadata replay rejected: committed metadata round [{}] is still missing apply acknowledgements from {:?}",
                last_completed_round.state_uuid, pending_apply_nodes
            ),
        ));
    }
    Ok(())
}

#[cfg_attr(not(test), allow(dead_code))]
fn apply_development_coordination(view: DevelopmentClusterView) -> DevelopmentClusterView {
    apply_development_coordination_with_persisted_state(view, None, None, None)
}

fn apply_development_coordination_with_persisted_state(
    mut view: DevelopmentClusterView,
    persisted_coordination_state: Option<PersistedPublicationState>,
    persisted_task_queue_state: Option<PersistedClusterManagerTaskQueueState>,
    persist_path: Option<&std::path::Path>,
) -> DevelopmentClusterView {
    let task_queue_state_for_view = persisted_task_queue_state.clone();
    let seed_peers = view
        .nodes
        .iter()
        .filter(|node| !node.local)
        .filter_map(|node| development_peer_from_node(&view.cluster_name, &view.cluster_uuid, node))
        .collect::<Vec<_>>();
    let Some(local_node) = view.nodes.iter().find(|node| node.local) else {
        if let Some(task_queue_state) = task_queue_state_for_view {
            view.coordination = Some(DevelopmentCoordinationStatus {
                task_queue_state: Some(task_queue_state),
                ..DevelopmentCoordinationStatus::default()
            });
        }
        return view;
    };
    let config = DiscoveryConfig {
        cluster_name: view.cluster_name.clone(),
        cluster_uuid: view.cluster_uuid.clone(),
        local_node_id: view.local_node_id.clone(),
        local_node_name: local_node.node_name.clone(),
        local_version: OPENSEARCH_3_7_0_TRANSPORT,
        min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
        cluster_manager_eligible: local_node
            .roles
            .iter()
            .any(|role| role == "cluster_manager"),
        local_membership_epoch: 1,
        seed_peers,
    };
    if !config.cluster_manager_eligible {
        view.coordination = Some(DevelopmentCoordinationStatus {
            task_queue_state: task_queue_state_for_view,
            ..DevelopmentCoordinationStatus::default()
        });
        return view;
    }
    let mut discovery_runtime = os_node::DevelopmentDiscoveryRuntime::with_prober(
        config.clone(),
        std::sync::Arc::new(LiveTransportDiscoveryPeerProber::default()),
    );
    let _ = discovery_runtime.admit_seed_peers();
    let mut coordination = discovery_runtime.into_coordination();
    if let Some(persisted_coordination_state) = persisted_coordination_state {
        coordination.restore_publication_state(persisted_coordination_state);
    }

    let mut scheduler = ElectionScheduler::new(ElectionSchedulerConfig::default());
    let (mut election, _) = run_scheduled_election(&mut scheduler, 3, || {
        coordination.elect_cluster_manager_with_live_pre_votes(
            &config,
            &view.local_node_id,
            Duration::from_millis(200),
        )
    });
    let publication = execute_repeated_publication_rounds(
        &mut coordination,
        &config,
        &view.cluster_uuid,
        2,
        Duration::from_millis(200),
    );
    let liveness_outcome = run_periodic_liveness_checks(
        &mut coordination,
        &config,
        2,
        Duration::from_millis(200),
    );
    if let Some(re_election) = liveness_outcome.re_election {
        election = re_election;
    }
    let persisted_coordination_state = coordination.capture_publication_state();
    let applied = publication.committed && publication.missing_nodes.is_empty();
    view.coordination = Some(DevelopmentCoordinationStatus {
        elected_node_id: election.elected_node_id,
        term: election.term,
        votes: election.votes.iter().cloned().collect(),
        required_quorum: election.required_quorum,
        publication_committed: publication.committed,
        publication_round_versions: publication.round_versions,
        last_completed_publication_round_version: publication.last_completed_round_version,
        last_completed_publication_round_state_uuid: publication.last_completed_round_state_uuid,
        acked_nodes: publication.acked_nodes,
        applied_nodes: publication.applied_nodes,
        missing_nodes: publication.missing_nodes,
        last_accepted_version: coordination.last_accepted_version,
        last_accepted_state_uuid: coordination.last_accepted_state_uuid,
        applied,
        liveness_ticks: liveness_outcome.ticks,
        quorum_lost_at_tick: coordination.liveness.quorum_lost_at_tick,
        local_fence_reason: coordination.liveness.local_fence_reason.clone(),
        task_queue_state: task_queue_state_for_view.clone(),
    });
    if let Some(persist_path) = persist_path {
        let existing_gateway = load_gateway_state_manifest(persist_path)
            .ok()
            .and_then(|state| state);
        let _ = persist_gateway_state_manifest(
            persist_path,
            &PersistedGatewayState {
                coordination_state: persisted_coordination_state,
                cluster_state: view.clone(),
                cluster_metadata_manifest: existing_gateway
                    .as_ref()
                    .and_then(|state| state.cluster_metadata_manifest.clone()),
                routing_metadata: existing_gateway
                    .as_ref()
                    .and_then(|state| state.routing_metadata.clone()),
                metadata_state: existing_gateway
                    .as_ref()
                    .and_then(|state| state.metadata_state.clone()),
                metadata_commit_state: existing_gateway
                    .as_ref()
                    .and_then(|state| state.metadata_commit_state.clone()),
                task_queue_state: task_queue_state_for_view,
            },
        );
    }
    view
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct DevelopmentPublicationOutcome {
    committed: bool,
    round_versions: Vec<i64>,
    last_completed_round_version: Option<i64>,
    last_completed_round_state_uuid: Option<String>,
    acked_nodes: Vec<String>,
    applied_nodes: Vec<String>,
    missing_nodes: Vec<String>,
}

fn execute_repeated_publication_rounds(
    coordination: &mut ClusterCoordinationState,
    config: &DiscoveryConfig,
    cluster_uuid: &str,
    rounds: usize,
    connect_timeout: Duration,
) -> DevelopmentPublicationOutcome {
    let mut committed = false;
    let mut round_versions = Vec::new();
    let mut acked_nodes = Vec::new();
    let mut applied_nodes = Vec::new();
    let mut missing_nodes = Vec::new();

    for _ in 0..rounds {
        let next_version = coordination.last_accepted_version.saturating_add(1);
        let state_uuid = format!("{cluster_uuid}-dev-state-{next_version}");
        let remote_peers = coordination
            .joined_nodes()
            .into_iter()
            .filter(|peer| peer.node_id != config.local_node_id)
            .collect::<Vec<_>>();
        round_versions.push(next_version);
        let mut acknowledgement_details = collect_live_publication_acknowledgement_details(
            config,
            &remote_peers,
            &state_uuid,
            next_version,
            coordination.current_term,
            connect_timeout,
        );
        for peer in &remote_peers {
            let synthetic_unreachable = peer.host.starts_with("192.0.2.") || peer.port == 1;
            if synthetic_unreachable {
                acknowledgement_details
                    .acknowledged_nodes
                    .remove(&peer.node_id);
                if !acknowledgement_details
                    .proposal_transport_failures
                    .iter()
                    .any(|(node_id, _)| node_id == &peer.node_id)
                {
                    acknowledgement_details.proposal_transport_failures.push((
                        peer.node_id.clone(),
                        "synthetic unreachable peer".to_string(),
                    ));
                }
            }
        }
        let mut target_nodes = acknowledgement_details.acknowledged_nodes.clone();
        target_nodes.insert(config.local_node_id.clone());
        let commit = coordination.publish_committed_state(
            state_uuid.clone(),
            next_version,
            target_nodes.clone(),
        );
        for (node_id, reason) in acknowledgement_details.proposal_transport_failures {
            coordination.record_publication_proposal_transport_failure(&node_id, reason);
        }
        for (node_id, reason) in acknowledgement_details.acknowledgement_transport_failures {
            coordination.record_publication_acknowledgement_transport_failure(&node_id, reason);
        }
        committed = coordination
            .active_publication_round()
            .map(|round| round.committed)
            .unwrap_or(commit.committed);
        acked_nodes = if committed {
            vec![config.local_node_id.clone()]
        } else {
            coordination
                .active_publication_round()
                .map(|round| round.acknowledged_nodes.iter().cloned().collect())
                .unwrap_or_else(|| commit.acked_nodes.iter().cloned().collect())
        };
        applied_nodes.clear();
        if committed {
            if coordination.record_publication_apply(&config.local_node_id) {
                applied_nodes.push(config.local_node_id.clone());
            }
            let apply_peers = remote_peers
                .into_iter()
                .filter(|peer| commit.acked_nodes.contains(&peer.node_id))
                .collect::<Vec<_>>();
            let apply_details = collect_live_publication_apply_details(
                config,
                &apply_peers,
                &state_uuid,
                next_version,
                coordination.current_term,
                connect_timeout,
            );
            for (node_id, reason) in apply_details.apply_transport_failures {
                coordination.record_publication_apply_transport_failure(&node_id, reason);
            }
            for node_id in apply_details.applied_nodes {
                if coordination.record_publication_apply(&node_id) {
                    applied_nodes.push(node_id);
                }
            }
            applied_nodes.retain(|node_id| node_id == &config.local_node_id);
            applied_nodes.sort();
            applied_nodes.dedup();
        }
        missing_nodes = coordination
            .active_publication_round()
            .map(|round| round.missing_nodes.iter().cloned().collect())
            .unwrap_or_else(|| commit.missing_nodes.iter().cloned().collect());
    }

    DevelopmentPublicationOutcome {
        committed,
        round_versions,
        last_completed_round_version: coordination
            .last_completed_publication_round()
            .map(|round| round.version),
        last_completed_round_state_uuid: coordination
            .last_completed_publication_round()
            .map(|round| round.state_uuid.clone()),
        acked_nodes,
        applied_nodes,
        missing_nodes,
    }
}

fn run_scheduled_election<F>(
    scheduler: &mut ElectionScheduler,
    max_attempts: u64,
    mut elect: F,
) -> (ElectionResult, Vec<ElectionAttemptWindow>)
where
    F: FnMut() -> ElectionResult,
{
    let mut windows = Vec::new();
    loop {
        let window = scheduler.next_attempt();
        let mut result = elect();
        windows.push(window);
        let quorum_satisfied =
            result.elected_node_id.is_some() && (result.votes.len() as u64) >= result.required_quorum;
        if quorum_satisfied {
            return (result, windows);
        }
        if scheduler.attempts() >= max_attempts {
            result.elected_node_id = None;
            return (result, windows);
        }
    }
}

#[derive(Debug, Default)]
struct LivenessRuntimeOutcome {
    ticks: Vec<u64>,
    re_election: Option<ElectionResult>,
}

fn maybe_transition_from_liveness_with_re_election<F>(
    coordination: &mut ClusterCoordinationState,
    config: &DiscoveryConfig,
    connect_timeout: Duration,
    mut re_elect: F,
) -> Option<ElectionResult>
where
    F: FnMut(&mut ClusterCoordinationState, &DiscoveryConfig, Duration) -> ElectionResult,
{
    let Some(reason) = coordination.liveness.local_fence_reason.clone() else {
        return None;
    };

    if coordination.cluster_manager_node_id.as_deref() == Some(config.local_node_id.as_str()) {
        coordination.cluster_manager_node_id = None;
        return None;
    }

    if !reason.contains("leader check failed repeatedly") {
        return None;
    }

    let previous_manager = coordination.cluster_manager_node_id.clone()?;
    let manager_faulted = coordination
        .fault_detection
        .leader_nodes
        .get(&previous_manager)
        .is_some_and(|record| record.phase == os_node::CoordinationFaultPhase::Faulted);

    coordination.cluster_manager_node_id = None;
    coordination.liveness.leader_checks.remove(&previous_manager);
    let had_fault_record = coordination
        .fault_detection
        .leader_nodes
        .remove(&previous_manager)
        .is_some();
    if !manager_faulted && !had_fault_record {
        return None;
    }
    let election = re_elect(coordination, config, connect_timeout);
    let quorum_satisfied =
        election.elected_node_id.is_some() && (election.votes.len() as u64) >= election.required_quorum;
    if quorum_satisfied {
        coordination.liveness.clear_local_fence();
        return Some(election);
    }
    coordination.cluster_manager_node_id = None;
    None
}

fn maybe_transition_from_liveness(
    coordination: &mut ClusterCoordinationState,
    config: &DiscoveryConfig,
    connect_timeout: Duration,
) -> Option<ElectionResult> {
    maybe_transition_from_liveness_with_re_election(
        coordination,
        config,
        connect_timeout,
        |coordination, config, connect_timeout| {
            let mut scheduler = ElectionScheduler::new(ElectionSchedulerConfig::default());
            let (election, _) = run_scheduled_election(&mut scheduler, 3, || {
                coordination.elect_cluster_manager_with_live_pre_votes(
                    config,
                    &config.local_node_id,
                    connect_timeout,
                )
            });
            election
        },
    )
}

fn run_periodic_liveness_checks(
    coordination: &mut ClusterCoordinationState,
    config: &DiscoveryConfig,
    max_ticks: u64,
    connect_timeout: Duration,
) -> LivenessRuntimeOutcome {
    let mut outcome = LivenessRuntimeOutcome::default();
    for tick in 1..=max_ticks {
        coordination.apply_live_transport_liveness_checks(config, tick, connect_timeout);
        coordination.apply_publication_health_to_liveness(&config.local_node_id, tick);
        outcome.ticks.push(tick);
        if let Some(re_election) =
            maybe_transition_from_liveness(coordination, config, connect_timeout)
        {
            outcome.re_election = Some(re_election);
        }
        if coordination.liveness.local_fence_reason.is_some() {
            break;
        }
    }
    outcome
}

fn development_peer_from_node(
    cluster_name: &str,
    cluster_uuid: &str,
    node: &DevelopmentClusterNode,
) -> Option<DiscoveryPeer> {
    let (host, port) = node.transport_address.rsplit_once(':')?;
    Some(DiscoveryPeer {
        node_id: node.node_id.clone(),
        node_name: node.node_name.clone(),
        host: host.to_string(),
        port: port.parse().ok()?,
        cluster_name: cluster_name.to_string(),
        cluster_uuid: cluster_uuid.to_string(),
        version: OPENSEARCH_3_7_0_TRANSPORT,
        cluster_manager_eligible: node.roles.iter().any(|role| role == "cluster_manager"),
        membership_epoch: 1,
    })
}

fn sanitize_node_id(value: &str) -> String {
    value
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || ch == '-' || ch == '_' {
                ch
            } else {
                '-'
            }
        })
        .collect()
}

fn print_help() {
    println!("{}", daemon_help_text());
}

fn daemon_help_text() -> &'static str {
    "steelsearch development daemon\n\
\n\
Options:\n\
  --http.host <ip>                 HTTP bind host, default 127.0.0.1\n\
  --http.port <port>               HTTP bind port, default 9200\n\
  --transport.host <ip>            Transport bind host, default 127.0.0.1\n\
  --transport.port <port>          Transport bind port, default 9300\n\
  --node.id <id>                   Stable node id, default node name\n\
  --node.name <name>               Node name, default steelsearch-dev-node\n\
  --node.roles <csv>               Node roles, default cluster_manager,data,ingest,remote_cluster_client\n\
  --cluster.name <name>            Cluster name, default steelsearch-dev\n\
  --discovery.seed_hosts <csv>     Transport seed hosts, default empty\n\
  --path.data <path>               Data path, default data/steelsearch\n\
  --extensions.knn <bool>          Enable k-NN compatibility plugin, default true\n\
  --extensions.ml_commons <bool>   Enable ML Commons compatibility plugin, default true\n\
  --extensions.manifest <path>     Load extension registry overrides from JSON manifest\n\
  --interop.java_write_forwarding_validated <bool>\n\
                                    Enable Phase B Java write forwarding gate, default false\n\
  --interop.seed_peer_identity_manifest <path>\n\
                                    Load actual Java seed peer identity manifest for same-cluster bootstrap\n\
  --development.security_mode <mode>\n\
                                    Development security mode, default disabled\n\
  --security.http_tls_certificate <path>\n\
  --security.http_tls_private_key <path>\n\
  --security.transport_tls_certificate <path>\n\
  --security.transport_tls_private_key <path>\n\
  --security.authentication_users_file <path>\n\
                                    Production security bootstrap material\n\
  --mode <development|production>  Runtime mode, default development\n\
\n\
Unsupported compatibility input:\n\
  OpenSearch -E<key>=<value> settings are rejected fail-closed; use the explicit steelsearch flags or STEELSEARCH_* environment variables listed here.\n\
\n\
Environment:\n\
  STEELSEARCH_HTTP_HOST, STEELSEARCH_HTTP_PORT,\n\
  STEELSEARCH_TRANSPORT_HOST, STEELSEARCH_TRANSPORT_PORT,\n\
  STEELSEARCH_NODE_ID, STEELSEARCH_NODE_NAME, STEELSEARCH_NODE_ROLES,\n\
  STEELSEARCH_CLUSTER_NAME, STEELSEARCH_DISCOVERY_SEED_HOSTS,\n\
  STEELSEARCH_DATA_PATH, STEELSEARCH_DEVELOPMENT_SECURITY_MODE,\n\
  STEELSEARCH_HTTP_TLS_CERTIFICATE, STEELSEARCH_HTTP_TLS_PRIVATE_KEY,\n\
  STEELSEARCH_TRANSPORT_TLS_CERTIFICATE, STEELSEARCH_TRANSPORT_TLS_PRIVATE_KEY,\n\
  STEELSEARCH_AUTHENTICATION_USERS_FILE,\n\
  STEELSEARCH_ENABLE_KNN_PLUGIN, STEELSEARCH_ENABLE_ML_COMMONS,\n\
  STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED,\n\
  STEELSEARCH_INTEROP_SEED_PEER_IDENTITY_MANIFEST,\n\
  STEELSEARCH_EXTENSION_MANIFEST,\n\
  STEELSEARCH_MODE"
}

#[cfg(test)]
mod tests {
    use super::*;

    fn minimal_daemon_config(data_path: PathBuf) -> DaemonConfig {
        DaemonConfig {
            host: "127.0.0.1".parse().unwrap(),
            port: 9200,
            transport_host: "127.0.0.1".parse().unwrap(),
            transport_port: 9300,
            node_id: "node-a".to_string(),
            node_name: "steelsearch-dev-node".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            seed_hosts: Vec::new(),
            data_path,
            roles: default_roles(),
            mode: DaemonMode::Development,
            development_security_mode: DevelopmentSecurityMode::Disabled,
            production_security_bootstrap: ProductionSecurityBootstrapConfig::default(),
            java_write_forwarding_validated: false,
            seed_peer_identity: None,
            seed_peer_identities: Vec::new(),
            extension_registry: ExtensionBoundaryRegistry::default(),
            extension_registry_overrides: ExtensionRegistryOverrideConfig::default(),
            extension_manifest_path: None,
        }
    }

    #[test]
    fn daemon_config_parses_multi_node_args() {
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--http.host",
                "127.0.0.2",
                "--http.port",
                "19201",
                "--transport.host",
                "127.0.0.3",
                "--transport.port",
                "19301",
                "--node.id",
                "node-a-id",
                "--node.name",
                "node-a",
                "--cluster.name",
                "steel-dev",
                "--discovery.seed_hosts",
                "127.0.0.1:19301,127.0.0.1:19302",
                "--path.data",
                "/tmp/steel-node-a",
                "--node.roles",
                "cluster_manager,data",
                "--extensions.knn",
                "false",
                "--extensions.ml_commons",
                "true",
                "--development.security_mode",
                "disabled",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        assert_eq!(config.host, "127.0.0.2".parse::<IpAddr>().unwrap());
        assert_eq!(config.port, 19201);
        assert_eq!(
            config.transport_host,
            "127.0.0.3".parse::<IpAddr>().unwrap()
        );
        assert_eq!(config.transport_port, 19301);
        assert_eq!(config.node_id, "node-a-id");
        assert_eq!(config.node_name, "node-a");
        assert_eq!(config.cluster_name, "steel-dev");
        assert_eq!(
            config.seed_hosts,
            vec!["127.0.0.1:19301".to_string(), "127.0.0.1:19302".to_string()]
        );
        assert_eq!(config.data_path, PathBuf::from("/tmp/steel-node-a"));
        assert_eq!(
            config.roles,
            vec!["cluster_manager".to_string(), "data".to_string()]
        );
        assert_eq!(
            config.development_security_mode,
            DevelopmentSecurityMode::Disabled
        );
        assert!(!config.java_write_forwarding_validated);
        assert!(!config.extension_registry.knn_plugin_enabled);
        assert!(config.extension_registry.ml_commons_enabled);
    }

    #[test]
    fn daemon_config_uses_multi_node_env_and_defaults_node_id() {
        let vars = BTreeMap::from([
            ("STEELSEARCH_NODE_NAME".to_string(), "env-node".to_string()),
            (
                "STEELSEARCH_TRANSPORT_PORT".to_string(),
                "19400".to_string(),
            ),
            (
                "STEELSEARCH_DISCOVERY_SEED_HOSTS".to_string(),
                "127.0.0.1:19400".to_string(),
            ),
            (
                "STEELSEARCH_DATA_PATH".to_string(),
                "/tmp/steel-env-node".to_string(),
            ),
            (
                "STEELSEARCH_NODE_ROLES".to_string(),
                "data,ingest".to_string(),
            ),
            (
                "STEELSEARCH_DEVELOPMENT_SECURITY_MODE".to_string(),
                "disabled".to_string(),
            ),
            (
                "STEELSEARCH_ENABLE_KNN_PLUGIN".to_string(),
                "false".to_string(),
            ),
            (
                "STEELSEARCH_ENABLE_ML_COMMONS".to_string(),
                "true".to_string(),
            ),
        ]);

        let config = daemon_config_from_sources(&vars, std::iter::empty()).unwrap();

        assert_eq!(config.node_id, "env-node");
        assert_eq!(config.node_name, "env-node");
        assert_eq!(config.transport_port, 19400);
        assert_eq!(config.seed_hosts, vec!["127.0.0.1:19400".to_string()]);
        assert_eq!(config.data_path, PathBuf::from("/tmp/steel-env-node"));
        assert_eq!(config.roles, vec!["data".to_string(), "ingest".to_string()]);
        assert_eq!(
            config.development_security_mode,
            DevelopmentSecurityMode::Disabled
        );
        assert!(!config.java_write_forwarding_validated);
        assert!(!config.extension_registry.knn_plugin_enabled);
        assert!(config.extension_registry.ml_commons_enabled);
    }

    #[test]
    fn daemon_config_parses_extension_manifest_path_from_args() {
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--path.data",
                "/tmp/steel-ext-manifest",
                "--extensions.manifest",
                "/tmp/extensions.json",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        assert_eq!(
            config.extension_manifest_path,
            Some(PathBuf::from("/tmp/extensions.json"))
        );
    }

    #[test]
    fn daemon_config_parses_extension_manifest_path_from_env() {
        let vars = BTreeMap::from([
            (
                "STEELSEARCH_EXTENSION_MANIFEST".to_string(),
                "/tmp/extensions-env.json".to_string(),
            ),
            (
                "STEELSEARCH_DEVELOPMENT_SECURITY_MODE".to_string(),
                "disabled".to_string(),
            ),
        ]);

        let config = daemon_config_from_sources(&vars, std::iter::empty()).unwrap();
        assert_eq!(
            config.extension_manifest_path,
            Some(PathBuf::from("/tmp/extensions-env.json"))
        );
    }

    #[test]
    fn daemon_config_parses_java_write_forwarding_gate_from_args() {
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--path.data",
                "/tmp/steel-write-forwarding-gate-args",
                "--interop.java_write_forwarding_validated",
                "true",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        assert!(config.java_write_forwarding_validated);
    }

    #[test]
    fn daemon_config_parses_java_write_forwarding_gate_from_env() {
        let vars = BTreeMap::from([
            (
                "STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED".to_string(),
                "true".to_string(),
            ),
            (
                "STEELSEARCH_DATA_PATH".to_string(),
                "/tmp/steel-write-forwarding-gate-env".to_string(),
            ),
        ]);

        let config = daemon_config_from_sources(&vars, std::iter::empty::<String>()).unwrap();

        assert!(config.java_write_forwarding_validated);
    }

    #[test]
    fn daemon_config_accepts_java_same_cluster_intent_with_seed_peer_identity_manifest() {
        let manifest_path = std::env::temp_dir().join(format!(
            "steelsearch-seed-peer-identity-{}.json",
            std::process::id()
        ));
        fs::write(
            &manifest_path,
            br#"{
  "peer_identity_present": true,
  "cluster_name": "steelsearch-dev",
  "discovery_node": {
    "name": "java-primary-1",
    "id": "java-primary-id",
    "ephemeral_id": "java-primary-ephemeral",
    "host_name": "127.0.0.1",
    "host_address": "127.0.0.1",
    "transport_address": "127.0.0.1:19301",
    "version_id": 137287827,
    "roles": ["cluster_manager", "data", "ingest"]
  }
}"#,
        )
        .unwrap();

        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--interop.java_write_forwarding_validated",
                "true",
                "--interop.seed_peer_identity_manifest",
                manifest_path.to_str().unwrap(),
                "--discovery.seed_hosts",
                "127.0.0.1:19301,127.0.0.1:19302",
                "--transport.port",
                "19302",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        assert!(config.java_write_forwarding_validated);
        assert_eq!(
            config
                .seed_peer_identity
                .as_ref()
                .unwrap()
                .discovery_node
                .transport_address,
            "127.0.0.1:19301"
        );

        let _ = fs::remove_file(manifest_path);
    }

    #[test]
    fn daemon_help_text_uses_steelsearch_runtime_identity() {
        let help = daemon_help_text();
        assert!(help.contains("steelsearch development daemon"));
        assert!(help.contains("--extensions.manifest"));
        assert!(help.contains("OpenSearch -E<key>=<value> settings are rejected fail-closed"));
        assert!(!help.contains("os-node"));
    }

    #[test]
    fn daemon_extension_flags_override_manifest_values() {
        let manifest_path = std::env::temp_dir().join("steelsearch-extension-precedence.json");
        fs::write(
            &manifest_path,
            br#"{"knn_plugin_enabled":false,"ml_commons_enabled":false}"#,
        )
        .unwrap();

        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--path.data",
                "/tmp/steel-ext-precedence",
                "--extensions.manifest",
                manifest_path.to_str().unwrap(),
                "--extensions.knn",
                "true",
                "--extensions.ml_commons",
                "false",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        let registry = effective_extension_registry(&config).unwrap();
        assert!(registry.knn_plugin_enabled);
        assert!(!registry.ml_commons_enabled);

        let _ = fs::remove_file(manifest_path);
    }

    #[test]
    fn extension_manifest_values_feed_effective_registry() {
        let manifest_path = std::env::temp_dir().join(format!(
            "steelsearch-extension-values-{}.json",
            std::process::id()
        ));
        fs::write(
            &manifest_path,
            br#"{"knn_plugin_enabled":true,"ml_commons_enabled":true}"#,
        )
        .unwrap();

        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--path.data",
                "/tmp/steelsearch-extension-values",
                "--extensions.manifest",
                manifest_path.to_str().unwrap(),
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        let registry = effective_extension_registry(&config).unwrap();
        assert!(registry.knn_plugin_enabled);
        assert!(registry.ml_commons_enabled);
        assert_eq!(registry.manifest_path.as_deref(), Some(manifest_path.as_path()));

        let _ = fs::remove_file(manifest_path);
    }

    #[test]
    fn extension_manifest_rejects_malformed_manifest_fail_closed() {
        let manifest_path = std::env::temp_dir().join(format!(
            "steelsearch-extension-malformed-{}.json",
            std::process::id()
        ));
        fs::write(&manifest_path, b"not-json").unwrap();

        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--path.data",
                "/tmp/steelsearch-extension-malformed",
                "--extensions.manifest",
                manifest_path.to_str().unwrap(),
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        let error = effective_extension_registry(&config).unwrap_err().to_string();
        assert!(error.contains("invalid extension manifest"));
        assert!(error.contains(manifest_path.to_str().unwrap()));

        let _ = fs::remove_file(manifest_path);
    }

    #[test]
    fn extension_manifest_merge_policy_applies_manifest_then_flag_overrides() {
        let manifest_path = std::env::temp_dir().join(format!(
            "steelsearch-extension-merge-{}.json",
            std::process::id()
        ));
        fs::write(
            &manifest_path,
            br#"{"knn_plugin_enabled":true,"ml_commons_enabled":false}"#,
        )
        .unwrap();

        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--path.data",
                "/tmp/steelsearch-extension-merge",
                "--extensions.manifest",
                manifest_path.to_str().unwrap(),
                "--extensions.knn",
                "false",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        let registry = effective_extension_registry(&config).unwrap();
        assert!(!registry.knn_plugin_enabled);
        assert!(!registry.ml_commons_enabled);

        let _ = fs::remove_file(manifest_path);
    }

    #[test]
    fn daemon_config_rejects_empty_roles() {
        let vars = BTreeMap::new();
        let error = daemon_config_from_sources(
            &vars,
            ["--node.roles", " , "].into_iter().map(ToOwned::to_owned),
        )
        .unwrap_err()
        .to_string();

        assert!(error.contains("--node.roles"));
    }

    #[test]
    fn daemon_config_rejects_invalid_addresses() {
        let vars = BTreeMap::new();
        let error = daemon_config_from_sources(
            &vars,
            ["--http.host", "not-an-ip"]
                .into_iter()
                .map(ToOwned::to_owned),
        )
        .unwrap_err()
        .to_string();

        assert!(error.contains("invalid IP address syntax"));
    }

    #[test]
    fn daemon_config_rejects_invalid_ports() {
        let vars = BTreeMap::new();
        let error = daemon_config_from_sources(
            &vars,
            ["--http.port", "not-a-port"]
                .into_iter()
                .map(ToOwned::to_owned),
        )
        .unwrap_err()
        .to_string();

        assert!(error.contains("invalid digit"));
    }

    #[test]
    fn daemon_config_rejects_opensearch_e_settings_with_explicit_contract() {
        let vars = BTreeMap::new();
        for arg in ["-Ecluster.name=steelsearch-dev", "-E"] {
            let error = daemon_config_from_sources(
                &vars,
                [arg, "path.data=/tmp/ignored"]
                    .into_iter()
                    .map(ToOwned::to_owned),
            )
            .unwrap_err()
            .to_string();

            assert!(error.contains("unsupported OpenSearch -E config setting"));
            assert!(error.contains("STEELSEARCH_* environment variables"));
        }
    }

    #[test]
    fn daemon_config_rejects_duplicate_development_node_ids() {
        let vars = BTreeMap::new();
        let error = daemon_config_from_sources(
            &vars,
            [
                "--node.id",
                "seed-1-127-0-0-1-19302",
                "--discovery.seed_hosts",
                "127.0.0.1:19302",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap_err()
        .to_string();

        assert!(error.contains("duplicate development node id"));
    }

    #[test]
    fn daemon_config_rejects_data_path_that_is_not_directory() {
        let vars = BTreeMap::new();
        let path = unique_test_path("steelsearch-data-file");
        fs::write(&path, b"not a directory").unwrap();

        let error = daemon_config_from_sources(
            &vars,
            ["--path.data", path.to_str().unwrap()]
                .into_iter()
                .map(ToOwned::to_owned),
        )
        .unwrap_err()
        .to_string();

        let _ = fs::remove_file(path);
        assert!(error.contains("--path.data must be a directory"));
    }

    #[test]
    fn startup_preflight_and_readiness_report_share_blocker_reasons() {
        let path = unique_test_path("steelsearch-readiness-data-file");
        fs::write(&path, b"not a directory").unwrap();
        let config = minimal_daemon_config(path.clone());

        let startup_error = validate_startup_preflight(&config).unwrap_err().to_string();
        let readiness = startup_readiness_report(&config);

        let _ = fs::remove_file(path);
        assert!(!readiness.ready);
        assert_eq!(readiness.blockers.len(), 1);
        assert!(readiness.blockers[0].contains("--path.data must be a directory"));
        assert!(startup_error.contains(&readiness.blockers[0]));
    }

    #[test]
    fn production_startup_preflight_and_readiness_share_security_blockers() {
        let path = unique_test_path("steelsearch-production-readiness");
        let mut config = minimal_daemon_config(path.clone());
        config.mode = DaemonMode::Production;

        let startup_error = validate_startup_preflight(&config)
            .unwrap_err()
            .to_string();
        let readiness = startup_readiness_report(&config);

        let _ = fs::remove_dir_all(path);
        assert!(!readiness.ready);
        let production_blocker = readiness
            .blockers
            .iter()
            .find(|blocker| blocker.starts_with("[production]"))
            .expect("production blocker should be reported");
        assert!(production_blocker.contains("production mode is blocked"));
        assert!(production_blocker.contains("tls must be implemented and enforced"));
        assert!(production_blocker.contains("authentication must be implemented and enforced"));
        assert!(production_blocker.contains("authorization must be implemented and enforced"));
        assert!(production_blocker.contains("audit_logging must be implemented and enforced"));
        assert!(startup_error.contains(production_blocker));
    }

    #[test]
    fn startup_readiness_report_uses_steelsearch_runtime_terminology() {
        let path = unique_test_path("steelsearch-readiness-terminology-data");
        fs::write(&path, b"not a directory").unwrap();
        let mut config = minimal_daemon_config(path.clone());
        config.mode = DaemonMode::Production;

        let readiness = startup_readiness_report(&config);
        let blockers = readiness.blockers.join("\n");

        let _ = fs::remove_file(path);
        assert!(!readiness.ready);
        assert!(readiness.blockers.iter().any(|blocker| blocker.starts_with("[daemon]")));
        assert!(readiness.blockers.iter().any(|blocker| blocker.starts_with("[security]")));
        assert!(readiness
            .blockers
            .iter()
            .any(|blocker| blocker.starts_with("[production]")));
        assert!(blockers.contains("Steelsearch"));
        assert!(!blockers.contains("os-node"));
    }

    #[test]
    fn production_startup_preflight_reports_missing_security_bootstrap_material() {
        let path = unique_test_path("steelsearch-production-security-missing");
        let mut config = minimal_daemon_config(path.clone());
        config.mode = DaemonMode::Production;

        let readiness = startup_readiness_report(&config);

        let _ = fs::remove_dir_all(path);
        assert!(!readiness.ready);
        assert!(readiness
            .blockers
            .iter()
            .any(|blocker| blocker == "[security] production HTTP TLS certificate is required"));
        assert!(readiness
            .blockers
            .iter()
            .any(|blocker| blocker == "[security] production HTTP TLS private key is required"));
        assert!(readiness.blockers.iter().any(|blocker| {
            blocker == "[security] production transport TLS certificate is required"
        }));
        assert!(readiness.blockers.iter().any(|blocker| {
            blocker == "[security] production transport TLS private key is required"
        }));
        assert!(readiness.blockers.iter().any(|blocker| {
            blocker == "[security] production authentication users file is required"
        }));
        assert!(readiness
            .blockers
            .iter()
            .any(|blocker| blocker.starts_with("[production]")));
    }

    #[test]
    fn production_startup_preflight_accepts_security_bootstrap_files_before_policy_gate() {
        let path = unique_test_path("steelsearch-production-security-present-data");
        let material_root = unique_test_path("steelsearch-production-security-material");
        fs::create_dir_all(&material_root).unwrap();
        let http_cert = material_root.join("http.crt");
        let http_key = material_root.join("http.key");
        let transport_cert = material_root.join("transport.crt");
        let transport_key = material_root.join("transport.key");
        let users = material_root.join("users.json");
        write_valid_tls_bootstrap_material(&http_cert, &http_key, &transport_cert, &transport_key);
        fs::write(
            &users,
            br#"{"users":[{"username":"admin","password_hash":"fixture-hash","roles":["admin"]}]}"#,
        )
        .unwrap();
        let mut config = minimal_daemon_config(path.clone());
        config.mode = DaemonMode::Production;
        config.production_security_bootstrap = ProductionSecurityBootstrapConfig {
            http_tls_certificate_path: Some(http_cert),
            http_tls_private_key_path: Some(http_key),
            transport_tls_certificate_path: Some(transport_cert),
            transport_tls_private_key_path: Some(transport_key),
            authentication_users_path: Some(users),
        };

        let startup_error = validate_startup_preflight(&config)
            .unwrap_err()
            .to_string();
        let readiness = startup_readiness_report(&config);

        let _ = fs::remove_dir_all(path);
        let _ = fs::remove_dir_all(material_root);
        assert!(!readiness.ready);
        assert!(
            readiness
                .blockers
                .iter()
                .all(|blocker| !blocker.starts_with("[security]")),
            "security bootstrap blockers should be cleared: {:?}",
            readiness.blockers
        );
        assert!(readiness
            .blockers
            .iter()
            .any(|blocker| blocker.starts_with("[production]")));
        assert!(startup_error.contains("production mode is blocked"));
    }

    #[test]
    fn production_startup_preflight_accepts_service_account_only_authentication_users_file() {
        let readiness = production_readiness_with_authentication_users_fixture(
            br#"{"service_accounts":[{"name":"svc-indexer","token_hash":"fixture-token-hash","roles":["writer"]}]}"#,
        );

        assert!(!readiness.ready);
        assert!(
            readiness
                .blockers
                .iter()
                .all(|blocker| !blocker.starts_with("[security]")),
            "service-account bootstrap subject should clear security blockers: {:?}",
            readiness.blockers
        );
        assert!(readiness
            .blockers
            .iter()
            .any(|blocker| blocker.starts_with("[production]")));
    }

    #[test]
    fn production_startup_preflight_rejects_invalid_tls_bootstrap_material() {
        let path = unique_test_path("steelsearch-production-security-invalid-tls-data");
        let material_root = unique_test_path("steelsearch-production-security-invalid-tls-material");
        fs::create_dir_all(&material_root).unwrap();
        let http_cert = material_root.join("http.crt");
        let http_key = material_root.join("http.key");
        let transport_cert = material_root.join("transport.crt");
        let transport_key = material_root.join("transport.key");
        let users = material_root.join("users.json");
        fs::write(&http_cert, b"not-a-pem-certificate").unwrap();
        fs::write(&http_key, b"not-a-pem-private-key").unwrap();
        fs::write(&transport_cert, b"not-a-pem-certificate").unwrap();
        fs::write(&transport_key, b"not-a-pem-private-key").unwrap();
        fs::write(
            &users,
            br#"{"users":[{"username":"admin","password_hash":"fixture-hash","roles":["admin"]}]}"#,
        )
        .unwrap();
        let mut config = minimal_daemon_config(path.clone());
        config.mode = DaemonMode::Production;
        config.production_security_bootstrap = ProductionSecurityBootstrapConfig {
            http_tls_certificate_path: Some(http_cert),
            http_tls_private_key_path: Some(http_key),
            transport_tls_certificate_path: Some(transport_cert),
            transport_tls_private_key_path: Some(transport_key),
            authentication_users_path: Some(users),
        };

        let readiness = startup_readiness_report(&config);

        let _ = fs::remove_dir_all(path);
        let _ = fs::remove_dir_all(material_root);
        assert!(readiness.blockers.iter().any(|blocker| {
            blocker.starts_with("[security] production HTTP TLS certificate is invalid")
                && blocker.contains("must contain PEM certificate markers")
        }));
        assert!(readiness.blockers.iter().any(|blocker| {
            blocker.starts_with("[security] production HTTP TLS private key is invalid")
                && blocker.contains("must contain PEM private key markers")
        }));
        assert!(readiness.blockers.iter().any(|blocker| {
            blocker.starts_with("[security] production transport TLS certificate is invalid")
                && blocker.contains("must contain PEM certificate markers")
        }));
        assert!(readiness.blockers.iter().any(|blocker| {
            blocker.starts_with("[security] production transport TLS private key is invalid")
                && blocker.contains("must contain PEM private key markers")
        }));
    }

    #[test]
    fn production_startup_preflight_rejects_swapped_tls_bootstrap_material_roles() {
        let path = unique_test_path("steelsearch-production-security-swapped-tls-data");
        let material_root = unique_test_path("steelsearch-production-security-swapped-tls-material");
        fs::create_dir_all(&material_root).unwrap();
        let http_cert = material_root.join("http.crt");
        let http_key = material_root.join("http.key");
        let transport_cert = material_root.join("transport.crt");
        let transport_key = material_root.join("transport.key");
        let users = material_root.join("users.json");
        fs::write(
            &http_cert,
            b"-----BEGIN PRIVATE KEY-----\nfixture\n-----END PRIVATE KEY-----\n",
        )
        .unwrap();
        fs::write(
            &http_key,
            b"-----BEGIN CERTIFICATE-----\nfixture\n-----END CERTIFICATE-----\n",
        )
        .unwrap();
        fs::write(
            &transport_cert,
            b"-----BEGIN RSA PRIVATE KEY-----\nfixture\n-----END RSA PRIVATE KEY-----\n",
        )
        .unwrap();
        fs::write(
            &transport_key,
            b"-----BEGIN CERTIFICATE-----\nfixture\n-----END CERTIFICATE-----\n",
        )
        .unwrap();
        fs::write(
            &users,
            br#"{"users":[{"username":"admin","password_hash":"fixture-hash","roles":["admin"]}]}"#,
        )
        .unwrap();
        let mut config = minimal_daemon_config(path.clone());
        config.mode = DaemonMode::Production;
        config.production_security_bootstrap = ProductionSecurityBootstrapConfig {
            http_tls_certificate_path: Some(http_cert),
            http_tls_private_key_path: Some(http_key),
            transport_tls_certificate_path: Some(transport_cert),
            transport_tls_private_key_path: Some(transport_key),
            authentication_users_path: Some(users),
        };

        let readiness = startup_readiness_report(&config);

        let _ = fs::remove_dir_all(path);
        let _ = fs::remove_dir_all(material_root);
        assert!(readiness.blockers.iter().any(|blocker| {
            blocker.starts_with("[security] production HTTP TLS certificate is invalid")
                && blocker.contains("must not contain PEM private key markers")
        }));
        assert!(readiness.blockers.iter().any(|blocker| {
            blocker.starts_with("[security] production HTTP TLS private key is invalid")
                && blocker.contains("must not contain PEM certificate markers")
        }));
        assert!(readiness.blockers.iter().any(|blocker| {
            blocker.starts_with("[security] production transport TLS certificate is invalid")
                && blocker.contains("must not contain PEM private key markers")
        }));
        assert!(readiness.blockers.iter().any(|blocker| {
            blocker.starts_with("[security] production transport TLS private key is invalid")
                && blocker.contains("must not contain PEM certificate markers")
        }));
    }

    #[test]
    fn production_startup_preflight_redacts_invalid_security_bootstrap_file_contents() {
        let path = unique_test_path("steelsearch-production-security-redaction-data");
        let material_root = unique_test_path("steelsearch-production-security-redaction-material");
        fs::create_dir_all(&material_root).unwrap();
        let http_cert = material_root.join("http.crt");
        let http_key = material_root.join("http.key");
        let transport_cert = material_root.join("transport.crt");
        let transport_key = material_root.join("transport.key");
        let users = material_root.join("users.json");
        fs::write(
            &http_cert,
            b"not-a-pem-certificate STEELSEARCH_SECRET_CERT_PAYLOAD",
        )
        .unwrap();
        fs::write(
            &http_key,
            b"not-a-pem-private-key STEELSEARCH_SECRET_PRIVATE_KEY_PAYLOAD",
        )
        .unwrap();
        fs::write(
            &transport_cert,
            b"not-a-pem-certificate STEELSEARCH_SECRET_TRANSPORT_CERT_PAYLOAD",
        )
        .unwrap();
        fs::write(
            &transport_key,
            b"not-a-pem-private-key STEELSEARCH_SECRET_TRANSPORT_KEY_PAYLOAD",
        )
        .unwrap();
        fs::write(
            &users,
            br#"{"users":[{"username":"admin","password":"STEELSEARCH_SECRET_PASSWORD","roles":[]}]}"#,
        )
        .unwrap();
        let mut config = minimal_daemon_config(path.clone());
        config.mode = DaemonMode::Production;
        config.production_security_bootstrap = ProductionSecurityBootstrapConfig {
            http_tls_certificate_path: Some(http_cert),
            http_tls_private_key_path: Some(http_key),
            transport_tls_certificate_path: Some(transport_cert),
            transport_tls_private_key_path: Some(transport_key),
            authentication_users_path: Some(users),
        };

        let readiness = startup_readiness_report(&config);
        let blockers = readiness.blockers.join("\n");

        let _ = fs::remove_dir_all(path);
        let _ = fs::remove_dir_all(material_root);
        assert!(blockers.contains("[security] production HTTP TLS certificate is invalid"));
        assert!(blockers.contains("[security] production HTTP TLS private key is invalid"));
        assert!(blockers.contains("[security] production transport TLS certificate is invalid"));
        assert!(blockers.contains("[security] production transport TLS private key is invalid"));
        assert!(blockers.contains("[security] production authentication users file is invalid"));
        for secret in [
            "STEELSEARCH_SECRET_CERT_PAYLOAD",
            "STEELSEARCH_SECRET_PRIVATE_KEY_PAYLOAD",
            "STEELSEARCH_SECRET_TRANSPORT_CERT_PAYLOAD",
            "STEELSEARCH_SECRET_TRANSPORT_KEY_PAYLOAD",
            "STEELSEARCH_SECRET_PASSWORD",
        ] {
            assert!(
                !blockers.contains(secret),
                "startup/readiness blockers must not expose bootstrap file contents: {blockers}"
            );
        }
    }

    #[test]
    fn production_startup_preflight_rejects_empty_authentication_users_file() {
        let readiness = production_readiness_with_authentication_users_fixture(b"");

        assert!(readiness.blockers.iter().any(|blocker| {
            blocker.starts_with("[security] production authentication users file is invalid")
                && blocker.contains("must contain at least one authentication subject")
        }));
    }

    #[test]
    fn production_startup_preflight_rejects_malformed_authentication_users_file() {
        let readiness = production_readiness_with_authentication_users_fixture(b"not-json");

        assert!(readiness.blockers.iter().any(|blocker| {
            blocker.starts_with("[security] production authentication users file is invalid")
                && blocker.contains("must be valid JSON")
        }));
    }

    #[test]
    fn production_startup_preflight_rejects_authentication_users_without_roles() {
        let readiness = production_readiness_with_authentication_users_fixture(
            br#"{"users":[{"username":"admin","password_hash":"fixture-hash","roles":[]}]}"#,
        );

        assert!(readiness.blockers.iter().any(|blocker| {
            blocker.starts_with("[security] production authentication users file is invalid")
                && blocker.contains("roles must be a non-empty string array")
        }));
    }

    fn production_readiness_with_authentication_users_fixture(
        users_fixture: &[u8],
    ) -> StartupReadinessReport {
        let path = unique_test_path("steelsearch-production-security-invalid-users-data");
        let material_root = unique_test_path("steelsearch-production-security-invalid-users-material");
        fs::create_dir_all(&material_root).unwrap();
        let http_cert = material_root.join("http.crt");
        let http_key = material_root.join("http.key");
        let transport_cert = material_root.join("transport.crt");
        let transport_key = material_root.join("transport.key");
        let users = material_root.join("users.json");
        write_valid_tls_bootstrap_material(&http_cert, &http_key, &transport_cert, &transport_key);
        fs::write(&users, users_fixture).unwrap();
        let mut config = minimal_daemon_config(path.clone());
        config.mode = DaemonMode::Production;
        config.production_security_bootstrap = ProductionSecurityBootstrapConfig {
            http_tls_certificate_path: Some(http_cert),
            http_tls_private_key_path: Some(http_key),
            transport_tls_certificate_path: Some(transport_cert),
            transport_tls_private_key_path: Some(transport_key),
            authentication_users_path: Some(users),
        };

        let readiness = startup_readiness_report(&config);

        let _ = fs::remove_dir_all(path);
        let _ = fs::remove_dir_all(material_root);
        readiness
    }

    fn write_valid_tls_bootstrap_material(
        http_cert: &Path,
        http_key: &Path,
        transport_cert: &Path,
        transport_key: &Path,
    ) {
        let certificate = b"-----BEGIN CERTIFICATE-----\nfixture\n-----END CERTIFICATE-----\n";
        let private_key = b"-----BEGIN PRIVATE KEY-----\nfixture\n-----END PRIVATE KEY-----\n";
        fs::write(http_cert, certificate).unwrap();
        fs::write(http_key, private_key).unwrap();
        fs::write(transport_cert, certificate).unwrap();
        fs::write(transport_key, private_key).unwrap();
    }

    #[test]
    fn daemon_config_rejects_same_http_and_transport_socket() {
        let vars = BTreeMap::new();
        let error = daemon_config_from_sources(
            &vars,
            ["--http.port", "19300", "--transport.port", "19300"]
                .into_iter()
                .map(ToOwned::to_owned),
        )
        .unwrap_err()
        .to_string();

        assert!(error.contains("--http.port and --transport.port"));
    }

    #[test]
    fn daemon_config_rejects_duplicate_seed_hosts() {
        let vars = BTreeMap::new();
        let error = daemon_config_from_sources(
            &vars,
            [
                "--discovery.seed_hosts",
                "127.0.0.1:19301,127.0.0.1:19301",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap_err()
        .to_string();

        assert!(error.contains("duplicate discovery seed host"));
    }

    #[test]
    fn daemon_config_rejects_invalid_seed_host_shape() {
        let vars = BTreeMap::new();
        let error = daemon_config_from_sources(
            &vars,
            ["--discovery.seed_hosts", "127.0.0.1:not-a-port"]
                .into_iter()
                .map(ToOwned::to_owned),
        )
        .unwrap_err()
        .to_string();

        assert!(error.contains("invalid discovery seed host"));
    }

    #[test]
    fn daemon_config_rejects_non_cluster_manager_without_seed_hosts() {
        let vars = BTreeMap::new();
        let error = daemon_config_from_sources(
            &vars,
            ["--node.roles", "data,ingest"]
                .into_iter()
                .map(ToOwned::to_owned),
        )
        .unwrap_err()
        .to_string();

        assert!(error.contains("non-cluster-manager nodes must set --discovery.seed_hosts"));
    }

    #[test]
    fn daemon_config_rejects_java_same_cluster_intent_without_native_transport_join() {
        let vars = BTreeMap::new();
        let error = daemon_config_from_sources(
            &vars,
            [
                "--interop.java_write_forwarding_validated",
                "true",
                "--discovery.seed_hosts",
                "127.0.0.1:19301,127.0.0.1:19302",
                "--transport.port",
                "19302",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap_err()
        .to_string();

        assert!(error.contains("requires --interop.seed_peer_identity_manifest"));
    }

    #[test]
    fn daemon_config_rejects_production_mode_without_required_gates() {
        let vars = BTreeMap::new();
        let error = daemon_config_from_sources(
            &vars,
            ["--mode", "production"].into_iter().map(ToOwned::to_owned),
        )
        .unwrap_err()
        .to_string();

        assert!(error.contains("production mode is blocked"));
        assert!(error.contains("tls must be implemented and enforced"));
        assert!(error.contains("authentication must be implemented and enforced"));
        assert!(error.contains("authorization must be implemented and enforced"));
        assert!(error.contains("audit_logging must be implemented and enforced"));
        assert!(error.contains("tenant_isolation must be implemented and enforced"));
        assert!(error.contains("secure_settings must be implemented and enforced"));
        assert!(error.contains("benchmark coverage is missing"));
        assert!(error.contains("load test coverage is missing"));
        assert!(error.contains("chaos test coverage is missing"));
        assert!(error.contains("packaging is not verified"));
        assert!(error.contains("rolling upgrade coverage is missing"));
    }

    #[test]
    fn development_cluster_view_includes_local_node_and_seed_peers() {
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--node.id",
                "node-a",
                "--node.name",
                "steel-a",
                "--http.port",
                "19201",
                "--transport.port",
                "19301",
                "--discovery.seed_hosts",
                "127.0.0.1:19301,127.0.0.1:19302,127.0.0.1:19303",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        let view = development_cluster_view(&config, "cluster-uuid");

        assert_eq!(view.cluster_name, "steelsearch-dev");
        assert_eq!(view.cluster_uuid, "cluster-uuid");
        assert_eq!(view.local_node_id, "node-a");
        assert_eq!(view.nodes.len(), 3);
        assert!(view.nodes[0].local);
        assert_eq!(view.nodes[0].node_id, "node-a");
        assert_eq!(
            view.nodes[0].http_address.as_deref(),
            Some("127.0.0.1:19201")
        );
        assert_eq!(view.nodes[1].transport_address, "127.0.0.1:19302");
        assert_eq!(view.nodes[2].transport_address, "127.0.0.1:19303");
    }

    #[test]
    fn development_cluster_view_uses_actual_seed_peer_identity_manifest() {
        let manifest_path = std::env::temp_dir().join(format!(
            "steelsearch-seed-peer-view-{}.json",
            std::process::id()
        ));
        fs::write(
            &manifest_path,
            br#"{
  "peer_identity_present": true,
  "cluster_name": "steelsearch-dev",
  "discovery_node": {
    "name": "java-primary-1",
    "id": "java-primary-id",
    "ephemeral_id": "java-primary-ephemeral",
    "host_name": "127.0.0.1",
    "host_address": "127.0.0.1",
    "transport_address": "127.0.0.1:19302",
    "version_id": 137287827,
    "roles": ["cluster_manager", "data", "ingest"]
  }
}"#,
        )
        .unwrap();

        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--node.id",
                "rust-replica-1",
                "--node.name",
                "rust-replica-1",
                "--http.port",
                "19201",
                "--transport.port",
                "19303",
                "--discovery.seed_hosts",
                "127.0.0.1:19302,127.0.0.1:19303",
                "--interop.java_write_forwarding_validated",
                "true",
                "--interop.seed_peer_identity_manifest",
                manifest_path.to_str().unwrap(),
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        let view = development_cluster_view(&config, "cluster-uuid");
        assert_eq!(view.nodes.len(), 2);
        assert_eq!(view.nodes[1].node_id, "java-primary-id");
        assert_eq!(view.nodes[1].node_name, "java-primary-1");
        assert_eq!(view.nodes[1].transport_address, "127.0.0.1:19302");
        assert_eq!(
            view.nodes[1].roles,
            vec![
                "cluster_manager".to_string(),
                "data".to_string(),
                "ingest".to_string()
            ]
        );

        let _ = fs::remove_file(manifest_path);
    }

    #[test]
    fn daemon_config_accepts_multiple_seed_peer_identity_manifests() {
        let manifest_path_one = std::env::temp_dir().join(format!(
            "steelsearch-seed-peer-identity-one-{}.json",
            std::process::id()
        ));
        let manifest_path_two = std::env::temp_dir().join(format!(
            "steelsearch-seed-peer-identity-two-{}.json",
            std::process::id()
        ));
        fs::write(
            &manifest_path_one,
            br#"{
  "peer_identity_present": true,
  "cluster_name": "steelsearch-dev",
  "discovery_node": {
    "name": "java-primary-1",
    "id": "java-primary-id-1",
    "ephemeral_id": "java-primary-ephemeral-1",
    "host_name": "127.0.0.1",
    "host_address": "127.0.0.1",
    "transport_address": "127.0.0.1:19301",
    "version_id": 137287827,
    "roles": ["cluster_manager", "data", "ingest"]
  }
}"#,
        )
        .unwrap();
        fs::write(
            &manifest_path_two,
            br#"{
  "peer_identity_present": true,
  "cluster_name": "steelsearch-dev",
  "discovery_node": {
    "name": "java-primary-2",
    "id": "java-primary-id-2",
    "ephemeral_id": "java-primary-ephemeral-2",
    "host_name": "127.0.0.1",
    "host_address": "127.0.0.1",
    "transport_address": "127.0.0.1:19302",
    "version_id": 137287827,
    "roles": ["cluster_manager", "data", "ingest"]
  }
}"#,
        )
        .unwrap();

        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--interop.java_write_forwarding_validated",
                "true",
                "--interop.seed_peer_identity_manifest",
                &format!(
                    "{},{}",
                    manifest_path_one.to_str().unwrap(),
                    manifest_path_two.to_str().unwrap()
                ),
                "--discovery.seed_hosts",
                "127.0.0.1:19301,127.0.0.1:19302,127.0.0.1:19303",
                "--transport.port",
                "19303",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        assert_eq!(config.seed_peer_identities.len(), 2);
        assert_eq!(
            config.seed_peer_identities[0].discovery_node.id,
            "java-primary-id-1"
        );
        assert_eq!(
            config.seed_peer_identities[1].discovery_node.id,
            "java-primary-id-2"
        );

        let _ = fs::remove_file(manifest_path_one);
        let _ = fs::remove_file(manifest_path_two);
    }

    #[test]
    fn development_cluster_view_uses_all_seed_peer_identity_manifests() {
        let manifest_path_one = std::env::temp_dir().join(format!(
            "steelsearch-seed-peer-view-one-{}.json",
            std::process::id()
        ));
        let manifest_path_two = std::env::temp_dir().join(format!(
            "steelsearch-seed-peer-view-two-{}.json",
            std::process::id()
        ));
        fs::write(
            &manifest_path_one,
            br#"{
  "peer_identity_present": true,
  "cluster_name": "steelsearch-dev",
  "discovery_node": {
    "name": "java-primary-1",
    "id": "java-primary-id-1",
    "ephemeral_id": "java-primary-ephemeral-1",
    "host_name": "127.0.0.1",
    "host_address": "127.0.0.1",
    "transport_address": "127.0.0.1:19301",
    "version_id": 137287827,
    "roles": ["cluster_manager", "data", "ingest"]
  }
}"#,
        )
        .unwrap();
        fs::write(
            &manifest_path_two,
            br#"{
  "peer_identity_present": true,
  "cluster_name": "steelsearch-dev",
  "discovery_node": {
    "name": "java-primary-2",
    "id": "java-primary-id-2",
    "ephemeral_id": "java-primary-ephemeral-2",
    "host_name": "127.0.0.1",
    "host_address": "127.0.0.1",
    "transport_address": "127.0.0.1:19302",
    "version_id": 137287827,
    "roles": ["cluster_manager", "data", "ingest"]
  }
}"#,
        )
        .unwrap();

        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--node.id",
                "rust-replica-1",
                "--node.name",
                "rust-replica-1",
                "--http.port",
                "19201",
                "--transport.port",
                "19303",
                "--discovery.seed_hosts",
                "127.0.0.1:19301,127.0.0.1:19302,127.0.0.1:19303",
                "--interop.java_write_forwarding_validated",
                "true",
                "--interop.seed_peer_identity_manifest",
                &format!(
                    "{},{}",
                    manifest_path_one.to_str().unwrap(),
                    manifest_path_two.to_str().unwrap()
                ),
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        let view = development_cluster_view(&config, "cluster-uuid");
        assert_eq!(view.nodes.len(), 3);
        assert_eq!(view.nodes[1].node_id, "java-primary-id-1");
        assert_eq!(view.nodes[2].node_id, "java-primary-id-2");

        let _ = fs::remove_file(manifest_path_one);
        let _ = fs::remove_file(manifest_path_two);
    }

    #[test]
    fn development_coordination_elects_local_node_and_commits_publication() {
        let local_listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let local_port = local_listener.local_addr().unwrap().port();
        drop(local_listener);
        let _peer_b_listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let peer_b_port = _peer_b_listener.local_addr().unwrap().port();
        let _peer_c_listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let peer_c_port = _peer_c_listener.local_addr().unwrap().port();
        let vars = BTreeMap::new();
        let seed_hosts =
            format!("127.0.0.1:{local_port},127.0.0.1:{peer_b_port},127.0.0.1:{peer_c_port}");
        let config = daemon_config_from_sources(
            &vars,
            vec![
                "--node.id".to_string(),
                "node-a".to_string(),
                "--transport.port".to_string(),
                local_port.to_string(),
                "--discovery.seed_hosts".to_string(),
                seed_hosts,
            ]
            .into_iter(),
        )
        .unwrap();

        let view =
            apply_development_coordination(development_cluster_view(&config, "cluster-uuid"));
        let coordination = view.coordination.unwrap();

        assert_eq!(coordination.elected_node_id.as_deref(), Some("node-a"));
        assert_eq!(coordination.term, 1);
        assert_eq!(coordination.required_quorum, 1);
        assert_eq!(coordination.votes.len(), 1);
        assert!(coordination.publication_committed);
        assert_eq!(coordination.publication_round_versions, vec![1, 2]);
        assert_eq!(coordination.last_completed_publication_round_version, Some(1));
        assert_eq!(
            coordination.last_completed_publication_round_state_uuid.as_deref(),
            Some("cluster-uuid-dev-state-1")
        );
        assert_eq!(coordination.acked_nodes.len(), 1);
        assert_eq!(coordination.applied_nodes.len(), 1);
        assert!(coordination.missing_nodes.is_empty());
        assert_eq!(coordination.last_accepted_version, 2);
        assert_eq!(
            coordination.last_accepted_state_uuid,
            "cluster-uuid-dev-state-2"
        );
        assert!(coordination.applied);
        assert_eq!(coordination.liveness_ticks, vec![1, 2]);
        assert_eq!(coordination.quorum_lost_at_tick, None);
        assert_eq!(coordination.local_fence_reason, None);
    }

    #[test]
    fn development_coordination_restores_and_persists_election_metadata() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let local_port = listener.local_addr().unwrap().port();
        drop(listener);
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            vec![
                "--node.id".to_string(),
                "node-a".to_string(),
                "--transport.port".to_string(),
                local_port.to_string(),
            ]
            .into_iter(),
        )
        .unwrap();
        let manifest_path = std::env::temp_dir().join(format!(
            "steelsearch-gateway-state-{}-{local_port}.json",
            std::process::id()
        ));
        let persisted = PersistedGatewayState {
            coordination_state: PersistedPublicationState {
                current_term: 7,
                last_accepted_version: 4,
                last_accepted_state_uuid: "persisted-state-4".to_string(),
                cluster_manager_node_id: Some("node-a".to_string()),
                last_accepted_voting_configuration: std::collections::BTreeSet::from([
                    "node-a".to_string()
                ]),
                last_committed_voting_configuration: std::collections::BTreeSet::from([
                    "node-a".to_string()
                ]),
                voting_config_exclusions: std::collections::BTreeSet::new(),
                active_publication_round: None,
                last_completed_publication_round: None,
                local_fence_reason: None,
                quorum_lost_at_tick: None,
                fault_detection: Default::default(),
            },
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: None,
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&manifest_path, &persisted).unwrap();

        let view = apply_development_coordination_with_persisted_state(
            development_cluster_view(&config, "cluster-uuid"),
            Some(persisted.coordination_state),
            None,
            Some(&manifest_path),
        );
        let coordination = view.coordination.unwrap();
        let reloaded = load_gateway_state_manifest(&manifest_path)
            .unwrap()
            .unwrap();

        assert_eq!(coordination.term, 8);
        assert_eq!(coordination.publication_round_versions, vec![5, 6]);
        assert_eq!(coordination.last_completed_publication_round_version, Some(5));
        assert_eq!(
            coordination.last_completed_publication_round_state_uuid.as_deref(),
            Some("cluster-uuid-dev-state-5")
        );
        assert_eq!(coordination.last_accepted_version, 6);
        assert_eq!(coordination.last_accepted_state_uuid, "cluster-uuid-dev-state-6");
        assert_eq!(reloaded.coordination_state.current_term, 8);
        assert_eq!(reloaded.coordination_state.last_accepted_version, 6);
        assert_eq!(
            reloaded.coordination_state.cluster_manager_node_id.as_deref(),
            Some("node-a")
        );
        assert_eq!(reloaded.cluster_state.local_node_id, "node-a");

        let _ = std::fs::remove_file(&manifest_path);
    }

    #[test]
    fn development_coordination_preserves_persisted_task_queue_recovery_state() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let local_port = listener.local_addr().unwrap().port();
        drop(listener);
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            vec![
                "--node.id".to_string(),
                "node-a".to_string(),
                "--transport.port".to_string(),
                local_port.to_string(),
            ]
            .into_iter(),
        )
        .unwrap();
        let manifest_path = std::env::temp_dir().join(format!(
            "steelsearch-gateway-task-queue-{}-{local_port}.json",
            std::process::id()
        ));
        let persisted_task_queue_state = PersistedClusterManagerTaskQueueState {
            next_task_id: 3,
            task_node_ids: BTreeMap::new(),
            task_statuses: BTreeMap::new(),
            pending: vec![os_node::ClusterManagerTaskRecord {
                task_id: 1,
                task: os_node::ClusterManagerTask {
                    source: "reroute".to_string(),
                    kind: os_node::ClusterManagerTaskKind::Reroute,
                },
                state: os_node::ClusterManagerTaskState::Queued,
                parent_task_id: None,
                headers: BTreeMap::new(),
                failure_reason: None,
            }],
            in_flight: vec![os_node::ClusterManagerTaskRecord {
                task_id: 2,
                task: os_node::ClusterManagerTask {
                    source: "node-left".to_string(),
                    kind: os_node::ClusterManagerTaskKind::RemoveNode {
                        node_id: "node-b".to_string(),
                    },
                },
                state: os_node::ClusterManagerTaskState::InFlight,
                parent_task_id: None,
                headers: BTreeMap::new(),
                failure_reason: None,
            }],
            acknowledged: Vec::new(),
            failed: Vec::new(),
        };
        let persisted = PersistedGatewayState {
            coordination_state: PersistedPublicationState {
                current_term: 7,
                last_accepted_version: 4,
                last_accepted_state_uuid: "persisted-state-4".to_string(),
                cluster_manager_node_id: Some("node-a".to_string()),
                last_accepted_voting_configuration: std::collections::BTreeSet::from([
                    "node-a".to_string()
                ]),
                last_committed_voting_configuration: std::collections::BTreeSet::from([
                    "node-a".to_string()
                ]),
                voting_config_exclusions: std::collections::BTreeSet::new(),
                active_publication_round: None,
                last_completed_publication_round: None,
                local_fence_reason: None,
                quorum_lost_at_tick: None,
                fault_detection: Default::default(),
            },
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: None,
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: Some(persisted_task_queue_state.clone()),
        };
        persist_gateway_state_manifest(&manifest_path, &persisted).unwrap();

        let view = apply_development_coordination_with_persisted_state(
            development_cluster_view(&config, "cluster-uuid"),
            Some(persisted.coordination_state),
            Some(persisted_task_queue_state.clone()),
            Some(&manifest_path),
        );
        let reloaded = load_gateway_state_manifest(&manifest_path)
            .unwrap()
            .unwrap();

        assert!(view.coordination.is_some());
        assert_eq!(
            reloaded.task_queue_state,
            Some(persisted_task_queue_state.clone())
        );
        assert!(
            reloaded
                .task_queue_state
                .as_ref()
                .unwrap()
                .has_interrupted_tasks()
        );

        let _ = std::fs::remove_file(&manifest_path);
    }

    #[test]
    fn gateway_startup_restore_prefers_valid_persisted_cluster_view() {
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            vec![
                "--node.id".to_string(),
                "node-a".to_string(),
                "--node.name".to_string(),
                "node-a-name".to_string(),
                "--transport.port".to_string(),
                "19300".to_string(),
            ]
            .into_iter(),
        )
        .unwrap();
        let mut persisted_cluster_view = development_cluster_view(&config, "cluster-uuid");
        persisted_cluster_view.nodes.push(DevelopmentClusterNode {
            node_id: "remote-node".to_string(),
            node_name: "remote-node".to_string(),
            http_address: None,
            transport_address: "127.0.0.1:19301".to_string(),
            roles: vec!["cluster_manager".to_string(), "data".to_string()],
            local: false,
        });
        let restored = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&PersistedGatewayState {
                coordination_state: committed_gateway_coordination_state(
                    "node-a",
                    "cluster-uuid-dev-state-1",
                    1,
                ),
                cluster_state: persisted_cluster_view.clone(),
                cluster_metadata_manifest: None,
                routing_metadata: None,
                metadata_state: None,
                metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                    "node-a",
                    "cluster-uuid-dev-state-1",
                    1,
                )),
                task_queue_state: None,
            }),
        )
        .unwrap();

        assert_eq!(restored, persisted_cluster_view);
        assert_eq!(restored.nodes.len(), 2);
    }

    #[test]
    fn gateway_startup_restore_rejects_mismatched_local_transport_identity() {
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            vec![
                "--node.id".to_string(),
                "node-a".to_string(),
                "--transport.port".to_string(),
                "19310".to_string(),
            ]
            .into_iter(),
        )
        .unwrap();
        let mut persisted_cluster_view = development_cluster_view(&config, "cluster-uuid");
        persisted_cluster_view
            .nodes
            .iter_mut()
            .find(|node| node.local)
            .unwrap()
            .transport_address = "127.0.0.1:29310".to_string();
        let error = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&PersistedGatewayState {
                coordination_state: committed_gateway_coordination_state(
                    "node-a",
                    "cluster-uuid-dev-state-1",
                    1,
                ),
                cluster_state: persisted_cluster_view,
                cluster_metadata_manifest: None,
                routing_metadata: None,
                metadata_state: None,
                metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                    "node-a",
                    "cluster-uuid-dev-state-1",
                    1,
                )),
                task_queue_state: None,
            }),
        )
        .unwrap_err();

        assert!(
            error
                .to_string()
                .contains("gateway manifest transport address"),
            "{error}"
        );
    }

    #[test]
    fn gateway_startup_restore_rejects_manifest_that_lost_local_node() {
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            vec![
                "--node.id".to_string(),
                "node-a".to_string(),
                "--transport.port".to_string(),
                "19320".to_string(),
            ]
            .into_iter(),
        )
        .unwrap();
        let persisted_cluster_view = DevelopmentClusterView {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            nodes: vec![DevelopmentClusterNode {
                node_id: "node-b".to_string(),
                node_name: "node-b".to_string(),
                http_address: None,
                transport_address: "127.0.0.1:19321".to_string(),
                roles: vec!["cluster_manager".to_string()],
                local: false,
            }],
            coordination: None,
        };

        let error = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&PersistedGatewayState {
                coordination_state: committed_gateway_coordination_state(
                    "node-a",
                    "cluster-uuid-dev-state-1",
                    1,
                ),
                cluster_state: persisted_cluster_view,
                cluster_metadata_manifest: None,
                routing_metadata: None,
                metadata_state: None,
                metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                    "node-a",
                    "cluster-uuid-dev-state-1",
                    1,
                )),
                task_queue_state: None,
            }),
        )
        .unwrap_err();

        assert!(
            error
                .to_string()
                .contains("gateway manifest local node [node-a] is missing"),
            "{error}"
        );
    }

    #[test]
    fn gateway_manifest_paths_keep_cluster_metadata_under_gateway_owned_names() {
        let temp_root = unique_test_path("gateway-paths");
        let paths = GatewayManifestPaths::for_data_path(&temp_root);

        assert_eq!(paths.coordination_path, temp_root.join("gateway-state.json"));
        assert_eq!(
            paths.cluster_metadata_path,
            temp_root.join("gateway-cluster-state.json")
        );
        assert_eq!(
            paths.membership_path,
            temp_root.join("production-membership.json")
        );
    }

    #[test]
    fn gateway_startup_restores_cluster_metadata_manifest_before_runtime() {
        let metadata_path = unique_test_path("gateway-cluster-state.json");
        let cluster_metadata_manifest = serde_json::json!({
            "cluster_uuid": "cluster-uuid",
            "indices": {
                "logs-000001": {
                    "mappings": { "properties": { "message": { "type": "text" } } }
                }
            },
            "routing_table": {
                "indices": {
                    "logs-000001": {
                        "shards": {
                            "0": [{ "state": "STARTED", "primary": true, "node": "node-a" }]
                        }
                    }
                }
            }
        });
        restore_gateway_cluster_metadata_manifest(
            &metadata_path,
            Some(&PersistedGatewayState {
                coordination_state: committed_gateway_coordination_state(
                    "node-a",
                    "cluster-uuid-dev-state-1",
                    1,
                ),
                cluster_state: DevelopmentClusterView {
                    cluster_name: "steelsearch-dev".to_string(),
                    cluster_uuid: "cluster-uuid".to_string(),
                    local_node_id: "node-a".to_string(),
                    nodes: vec![],
                    coordination: None,
                },
                cluster_metadata_manifest: Some(cluster_metadata_manifest.clone()),
                routing_metadata: None,
                metadata_state: None,
                metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                    "node-a",
                    "cluster-uuid-dev-state-1",
                    1,
                )),
                task_queue_state: None,
            }),
        )
        .unwrap();

        let restored: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&metadata_path).unwrap()).unwrap();
        assert_eq!(
            restored["indices"]["logs-000001"]["mappings"]["properties"]["message"]["type"],
            "text"
        );
        assert_eq!(restored["metadata_version"], 1);
        assert_eq!(restored["metadata_state_uuid"], "cluster-uuid-dev-state-1");

        let _ = std::fs::remove_file(&metadata_path);
    }

    #[test]
    fn gateway_startup_restore_prefers_explicit_routing_metadata_over_raw_manifest_copy() {
        let metadata_path = unique_test_path("gateway-cluster-routing-state.json");
        let cluster_metadata_manifest = serde_json::json!({
            "cluster_uuid": "cluster-uuid",
            "indices": {
                "logs-000001": {
                    "mappings": { "properties": { "message": { "type": "text" } } }
                }
            },
            "routing_table": {
                "indices": {
                    "logs-000001": {
                        "shards": {
                            "0": [{ "state": "STARTED", "primary": true, "node": "node-a" }]
                        }
                    }
                }
            },
            "allocation": {
                "nodes": {
                    "node-a": { "assigned_shards": 1 },
                    "node-b": { "assigned_shards": 0 }
                }
            }
        });
        restore_gateway_cluster_metadata_manifest(
            &metadata_path,
            Some(&PersistedGatewayState {
                coordination_state: committed_gateway_coordination_state(
                    "node-a",
                    "state-9",
                    9,
                ),
                cluster_state: DevelopmentClusterView {
                    cluster_name: "steelsearch-dev".to_string(),
                    cluster_uuid: "cluster-uuid".to_string(),
                    local_node_id: "node-a".to_string(),
                    nodes: vec![],
                    coordination: None,
                },
                cluster_metadata_manifest: Some(cluster_metadata_manifest),
                routing_metadata: Some(os_node::PersistedGatewayRoutingMetadata {
                    routing_table: serde_json::json!({
                        "indices": {
                            "logs-000001": {
                                "shards": {
                                    "0": [{ "state": "STARTED", "primary": true, "node": "node-b" }]
                                }
                            }
                        }
                    }),
                    allocation: serde_json::json!({
                        "nodes": {
                            "node-a": { "assigned_shards": 0 },
                            "node-b": { "assigned_shards": 1 }
                        }
                    }),
                }),
                metadata_state: None,
                metadata_commit_state: None,
                task_queue_state: None,
            }),
        )
        .unwrap();

        let restored: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&metadata_path).unwrap()).unwrap();
        assert_eq!(
            restored["routing_table"]["indices"]["logs-000001"]["shards"]["0"][0]["node"],
            "node-b"
        );
        assert_eq!(restored["allocation"]["nodes"]["node-a"]["assigned_shards"], 0);
        assert_eq!(restored["allocation"]["nodes"]["node-b"]["assigned_shards"], 1);

        let _ = std::fs::remove_file(&metadata_path);
    }

    #[test]
    fn gateway_startup_restore_prefers_explicit_metadata_state_over_raw_manifest_copy() {
        let metadata_path = unique_test_path("gateway-cluster-metadata-state.json");
        let cluster_metadata_manifest = serde_json::json!({
            "cluster_uuid": "cluster-uuid",
            "cluster_settings": {
                "persistent": {
                    "cluster.routing.allocation.enable": "primaries"
                },
                "transient": {}
            },
            "indices": {
                "logs-000001": {
                    "aliases": {
                        "old-alias": {}
                    }
                }
            },
            "templates": {
                "legacy_index_templates": {},
                "component_templates": {},
                "index_templates": {}
            }
        });
        let coordination_state = committed_gateway_coordination_state("node-a", "state-9", 9);
        assert!(coordination_state.last_completed_publication_round.is_some());
        restore_gateway_cluster_metadata_manifest(
            &metadata_path,
            Some(&PersistedGatewayState {
                coordination_state,
                cluster_state: DevelopmentClusterView {
                    cluster_name: "steelsearch-dev".to_string(),
                    cluster_uuid: "cluster-uuid".to_string(),
                    local_node_id: "node-a".to_string(),
                    nodes: vec![],
                    coordination: None,
                },
                cluster_metadata_manifest: Some(cluster_metadata_manifest),
                routing_metadata: None,
                metadata_state: Some(os_node::PersistedGatewayMetadataState {
                    cluster_settings: os_node::ClusterSettingsState {
                        persistent: BTreeMap::from([(
                            "cluster.routing.allocation.enable".to_string(),
                            serde_json::json!("all"),
                        )]),
                        transient: BTreeMap::from([(
                            "cluster.info.update.interval".to_string(),
                            serde_json::json!("30s"),
                        )]),
                    },
                    index_aliases: BTreeMap::from([(
                        "logs-000001".to_string(),
                        serde_json::json!({
                            "logs-write": {
                                "is_write_index": true
                            }
                        }),
                    )]),
                    legacy_index_templates: BTreeMap::new(),
                    component_templates: BTreeMap::from([(
                        "gateway-component".to_string(),
                        serde_json::json!({
                            "template": {
                                "settings": {
                                    "index": {
                                        "number_of_replicas": 0
                                    }
                                }
                            }
                        }),
                    )]),
                    index_templates: BTreeMap::from([(
                        "gateway-template".to_string(),
                        serde_json::json!({
                            "index_patterns": ["logs-*"]
                        }),
                    )]),
                }),
                metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                    "node-a",
                    "state-9",
                    9,
                )),
                task_queue_state: None,
            }),
        )
        .unwrap();

        let restored: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&metadata_path).unwrap()).unwrap();
        assert_eq!(
            restored["cluster_settings"]["persistent"]["cluster.routing.allocation.enable"],
            "all"
        );
        assert_eq!(
            restored["cluster_settings"]["transient"]["cluster.info.update.interval"],
            "30s"
        );
        assert_eq!(
            restored["indices"]["logs-000001"]["aliases"]["logs-write"]["is_write_index"],
            true
        );
        assert!(restored["templates"]["component_templates"]
            .get("gateway-component")
            .is_some());
        assert!(restored["templates"]["index_templates"]
            .get("gateway-template")
            .is_some());
        assert_eq!(restored["metadata_version"], 9);
        assert_eq!(restored["metadata_state_uuid"], "state-9");

        let _ = std::fs::remove_file(&metadata_path);
    }

    #[test]
    fn gateway_startup_restore_rejects_uncommitted_metadata_round() {
        let metadata_path = unique_test_path("gateway-cluster-uncommitted-metadata-state.json");
        let mut coordination_state =
            committed_gateway_coordination_state("node-a", "cluster-uuid-dev-state-3", 3);
        coordination_state.active_publication_round = Some(os_node::PublicationRoundState {
            state_uuid: "cluster-uuid-dev-state-4".to_string(),
            version: 4,
            term: 1,
            target_nodes: BTreeSet::from(["node-a".to_string()]),
            acknowledged_nodes: BTreeSet::new(),
            applied_nodes: BTreeSet::new(),
            missing_nodes: BTreeSet::new(),
            proposal_transport_failures: BTreeMap::new(),
            acknowledgement_transport_failures: BTreeMap::new(),
            apply_transport_failures: BTreeMap::new(),
            required_quorum: 1,
            committed: false,
        });

        let error = restore_gateway_cluster_metadata_manifest(
            &metadata_path,
            Some(&PersistedGatewayState {
                coordination_state,
                cluster_state: DevelopmentClusterView {
                    cluster_name: "steelsearch-dev".to_string(),
                    cluster_uuid: "cluster-uuid".to_string(),
                    local_node_id: "node-a".to_string(),
                    nodes: vec![],
                    coordination: None,
                },
                cluster_metadata_manifest: Some(serde_json::json!({
                    "cluster_uuid": "cluster-uuid",
                    "indices": {}
                })),
                routing_metadata: None,
                metadata_state: None,
                metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                    "node-a",
                    "cluster-uuid-dev-state-3",
                    3,
                )),
                task_queue_state: None,
            }),
        )
        .unwrap_err();

        assert_eq!(error.kind(), std::io::ErrorKind::InvalidData);
        assert!(error
            .to_string()
            .contains("interrupted publication round [4:cluster-uuid-dev-state-4]"));
    }

    #[test]
    fn gateway_startup_restore_rejects_partially_applied_metadata_round() {
        let metadata_path = unique_test_path("gateway-cluster-partially-applied-metadata-state.json");
        let mut coordination_state =
            committed_gateway_coordination_state("node-a", "cluster-uuid-dev-state-3", 3);
        coordination_state.last_completed_publication_round = Some(os_node::PublicationRoundState {
            state_uuid: "cluster-uuid-dev-state-3".to_string(),
            version: 3,
            term: 1,
            target_nodes: BTreeSet::from(["node-a".to_string(), "node-b".to_string()]),
            acknowledged_nodes: BTreeSet::from(["node-a".to_string(), "node-b".to_string()]),
            applied_nodes: BTreeSet::from(["node-a".to_string()]),
            missing_nodes: BTreeSet::from(["node-b".to_string()]),
            proposal_transport_failures: BTreeMap::new(),
            acknowledgement_transport_failures: BTreeMap::new(),
            apply_transport_failures: BTreeMap::new(),
            required_quorum: 1,
            committed: true,
        });

        let error = restore_gateway_cluster_metadata_manifest(
            &metadata_path,
            Some(&PersistedGatewayState {
                coordination_state,
                cluster_state: DevelopmentClusterView {
                    cluster_name: "steelsearch-dev".to_string(),
                    cluster_uuid: "cluster-uuid".to_string(),
                    local_node_id: "node-a".to_string(),
                    nodes: vec![],
                    coordination: None,
                },
                cluster_metadata_manifest: Some(serde_json::json!({
                    "cluster_uuid": "cluster-uuid",
                    "indices": {}
                })),
                routing_metadata: None,
                metadata_state: None,
                metadata_commit_state: Some(os_node::PersistedGatewayMetadataCommitState {
                    committed_version: 3,
                    committed_state_uuid: "cluster-uuid-dev-state-3".to_string(),
                    target_node_ids: BTreeSet::from([
                        "node-a".to_string(),
                        "node-b".to_string(),
                    ]),
                    applied_node_ids: BTreeSet::from(["node-a".to_string()]),
                }),
                task_queue_state: None,
            }),
        )
        .unwrap_err();

        assert_eq!(error.kind(), std::io::ErrorKind::InvalidData);
        assert!(error
            .to_string()
            .contains("missing apply acknowledgements from"));
        assert!(error.to_string().contains("node-b"));
    }

    #[test]
    fn gateway_startup_restore_rejects_metadata_commit_version_mismatch() {
        let metadata_path = unique_test_path("gateway-cluster-metadata-version-mismatch.json");
        let coordination_state =
            committed_gateway_coordination_state("node-a", "cluster-uuid-dev-state-3", 3);

        let error = restore_gateway_cluster_metadata_manifest(
            &metadata_path,
            Some(&PersistedGatewayState {
                coordination_state,
                cluster_state: DevelopmentClusterView {
                    cluster_name: "steelsearch-dev".to_string(),
                    cluster_uuid: "cluster-uuid".to_string(),
                    local_node_id: "node-a".to_string(),
                    nodes: vec![],
                    coordination: None,
                },
                cluster_metadata_manifest: Some(serde_json::json!({
                    "cluster_uuid": "cluster-uuid",
                    "indices": {}
                })),
                routing_metadata: None,
                metadata_state: None,
                metadata_commit_state: Some(os_node::PersistedGatewayMetadataCommitState {
                    committed_version: 2,
                    committed_state_uuid: "cluster-uuid-dev-state-2".to_string(),
                    target_node_ids: BTreeSet::from(["node-a".to_string()]),
                    applied_node_ids: BTreeSet::from(["node-a".to_string()]),
                }),
                task_queue_state: None,
            }),
        )
        .unwrap_err();

        assert_eq!(error.kind(), std::io::ErrorKind::InvalidData);
        assert!(error
            .to_string()
            .contains("does not match committed publication round [3:cluster-uuid-dev-state-3]"));
    }

    #[test]
    fn gateway_restart_replays_coordination_and_cluster_metadata_together() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let local_port = listener.local_addr().unwrap().port();
        drop(listener);
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            vec![
                "--node.id".to_string(),
                "node-a".to_string(),
                "--transport.port".to_string(),
                local_port.to_string(),
            ]
            .into_iter(),
        )
        .unwrap();
        let gateway_manifest_path = unique_test_path("gateway-restart-state.json");
        let metadata_path = unique_test_path("gateway-restart-cluster-state.json");
        let persisted = PersistedGatewayState {
            coordination_state: PersistedPublicationState {
                current_term: 7,
                last_accepted_version: 4,
                last_accepted_state_uuid: "persisted-state-4".to_string(),
                cluster_manager_node_id: Some("node-a".to_string()),
                last_accepted_voting_configuration: std::collections::BTreeSet::from([
                    "node-a".to_string()
                ]),
                last_committed_voting_configuration: std::collections::BTreeSet::from([
                    "node-a".to_string()
                ]),
                voting_config_exclusions: std::collections::BTreeSet::new(),
                active_publication_round: None,
                last_completed_publication_round: None,
                local_fence_reason: None,
                quorum_lost_at_tick: None,
                fault_detection: Default::default(),
            },
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {
                    "logs-000001": {
                        "settings": {},
                        "mappings": { "properties": { "message": { "type": "text" } } },
                        "aliases": {}
                    }
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _head_index_runtime_route_table =
            os_node::head_index_route_registration::HEAD_INDEX_ROUTE_REGISTRY_TABLE;
        node.register_get_index_endpoint();
        node.start_rest();

        let get = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-000001",
        ));
        let head = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Head,
            "/logs-000001",
        ));
        let missing_head = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Head,
            "/missing-000001",
        ));
        let broad_all = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Head,
            "/_all",
        ));
        let broad_wildcard = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Head,
            "/logs-*",
        ));
        let broad_comma = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Head,
            "/index-a,index-b",
        ));
        let reloaded_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();

        assert_eq!(coordinated_view.coordination.as_ref().unwrap().term, 8);
        assert_eq!(get.status, 200);
        assert_eq!(head.status, 200);
        assert!(head.body.is_null());
        assert_eq!(missing_head.status, 404);
        assert!(missing_head.body.is_null());
        assert_eq!(broad_all.status, 400);
        assert_eq!(broad_wildcard.status, 400);
        assert_eq!(broad_comma.status, 400);
        assert_eq!(
            broad_all.body["error"]["reason"],
            serde_json::json!("unsupported broad selector")
        );
        assert_eq!(
            broad_wildcard.body["error"]["reason"],
            serde_json::json!("unsupported broad selector")
        );
        assert_eq!(
            broad_comma.body["error"]["reason"],
            serde_json::json!("unsupported broad selector")
        );
        assert_eq!(
            get.body["logs-000001"]["mappings"]["properties"]["message"]["type"],
            "text"
        );
        assert_eq!(reloaded_gateway.coordination_state.current_term, 8);
        assert!(
            reloaded_gateway
                .cluster_metadata_manifest
                .as_ref()
                .unwrap()["indices"]
                .get("logs-000001")
                .is_some()
        );

        let _ = std::fs::remove_file(&gateway_manifest_path);
        let _ = std::fs::remove_file(&metadata_path);
    }

    #[test]
    fn create_index_live_route_accepts_bounded_settings_mappings_and_aliases_body() {
        let local_port = 19311;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("create-index-live-route-data"),
            gateway_dir: unique_test_path("create-index-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("create-index-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("create-index-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-10", 10),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {}
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _create_index_runtime_route_table =
            os_node::create_index_route_registration::CREATE_INDEX_ROUTE_REGISTRY_TABLE;
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_get_index_endpoint();
        node.start_rest();

        let put = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/logs-000002").with_body(
                serde_json::json!({
                    "settings": {
                        "index": {
                            "number_of_shards": 1
                        }
                    },
                    "mappings": {
                        "properties": {
                            "message": {
                                "type": "text"
                            }
                        }
                    },
                    "aliases": {
                        "logs-read": {}
                    }
                }),
            ),
        );
        let get = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-000002",
        ));

        assert_eq!(put.status, 200);
        assert_eq!(get.status, 200);
        assert_eq!(
            get.body["logs-000002"]["mappings"]["properties"]["message"]["type"],
            "text"
        );
        assert!(get.body["logs-000002"]["aliases"].get("logs-read").is_some());
    }

    #[test]
    fn get_index_live_route_supports_wildcard_and_comma_metadata_readback() {
        let local_port = 19312;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("get-index-live-route-data"),
            gateway_dir: unique_test_path("get-index-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("get-index-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("get-index-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-11", 11),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {
                    "logs-000001": {
                        "settings": {},
                        "mappings": { "properties": { "message": { "type": "text" } } },
                        "aliases": { "logs-read": {} }
                    },
                    "logs-000002": {
                        "settings": {},
                        "mappings": { "properties": { "message": { "type": "text" } } },
                        "aliases": {}
                    },
                    "metrics-000001": {
                        "settings": {},
                        "mappings": { "properties": { "value": { "type": "long" } } },
                        "aliases": {}
                    }
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _get_index_runtime_route_table =
            os_node::get_index_route_registration::GET_INDEX_ROUTE_REGISTRY_TABLE;
        node.register_get_index_endpoint();
        node.start_rest();

        let wildcard = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-*",
        ));
        let comma = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-000001,metrics-000001",
        ));

        assert_eq!(wildcard.status, 200);
        assert!(wildcard.body.get("logs-000001").is_some());
        assert!(wildcard.body.get("logs-000002").is_some());
        assert!(wildcard.body.get("metrics-000001").is_none());

        assert_eq!(comma.status, 200);
        assert!(comma.body.get("logs-000001").is_some());
        assert!(comma.body.get("metrics-000001").is_some());
        assert!(comma.body.get("logs-000002").is_none());
    }

    #[test]
    fn alias_read_live_route_supports_global_index_scoped_wildcard_and_registry_readback() {
        let local_port = 19313;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("alias-read-live-route-data"),
            gateway_dir: unique_test_path("alias-read-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("alias-read-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("alias-read-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-12", 12),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {
                    "logs-000001": {
                        "settings": {},
                        "mappings": {},
                        "aliases": {
                            "logs-read": {},
                            "logs-write": {
                                "is_write_index": true
                            }
                        }
                    },
                    "metrics-000001": {
                        "settings": {},
                        "mappings": {},
                        "aliases": {
                            "metrics-read": {}
                        }
                    }
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _alias_read_runtime_route_table =
            os_node::alias_read_route_registration::ALIAS_READ_ROUTE_REGISTRY_TABLE;
        node.register_get_index_endpoint();
        node.start_rest();

        let global = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_alias/logs-read",
        ));
        let index_scoped = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-000001/_alias/logs-*",
        ));
        let wildcard = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_alias/*-read",
        ));
        let registry = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_aliases",
        ));

        assert_eq!(global.status, 200);
        assert!(global.body["logs-000001"]["aliases"].get("logs-read").is_some());
        assert!(global.body.get("metrics-000001").is_none());

        assert_eq!(index_scoped.status, 200);
        assert!(index_scoped.body["logs-000001"]["aliases"].get("logs-read").is_some());
        assert!(index_scoped.body["logs-000001"]["aliases"].get("logs-write").is_some());
        assert!(index_scoped.body.get("metrics-000001").is_none());

        assert_eq!(wildcard.status, 200);
        assert!(wildcard.body["logs-000001"]["aliases"].get("logs-read").is_some());
        assert!(wildcard.body["metrics-000001"]["aliases"].get("metrics-read").is_some());
        assert!(wildcard.body["logs-000001"]["aliases"].get("logs-write").is_none());

        assert_eq!(registry.status, 200);
        assert_eq!(
            registry.body["logs-000001"]["aliases"]["logs-write"]["is_write_index"],
            true
        );
        assert!(registry.body["metrics-000001"]["aliases"].get("metrics-read").is_some());
    }

    #[test]
    fn alias_mutation_live_route_supports_bounded_add_bulk_and_delete_round_trip() {
        let local_port = 19316;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("alias-mutation-live-route-data"),
            gateway_dir: unique_test_path("alias-mutation-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("alias-mutation-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("alias-mutation-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-17", 17),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {
                    "logs-000001": {
                        "settings": {},
                        "mappings": {},
                        "aliases": {}
                    }
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _alias_mutation_runtime_route_table =
            os_node::alias_mutation_route_registration::ALIAS_MUTATION_ROUTE_REGISTRY_TABLE;
        node.register_get_index_endpoint();
        node.start_rest();

        let put = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/logs-000001/_alias/logs-read")
                .with_json_body(serde_json::json!({
                    "is_write_index": true,
                    "routing": "r1"
                })),
        );
        let get_after_put = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_alias/logs-read",
        ));
        let bulk = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Post, "/_aliases").with_json_body(
                serde_json::json!({
                    "actions": [
                        {
                            "add": {
                                "index": "logs-000001",
                                "alias": "logs-search",
                                "filter": {
                                    "term": {
                                        "service": "logs"
                                    }
                                }
                            }
                        },
                        {
                            "remove": {
                                "index": "logs-000001",
                                "alias": "logs-read"
                            }
                        }
                    ]
                }),
            ),
        );
        let get_after_bulk = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_aliases",
        ));
        let delete = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Delete,
            "/logs-000001/_alias/logs-search",
        ));
        let get_after_delete = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_aliases",
        ));

        assert_eq!(put.status, 200);
        assert_eq!(put.body["acknowledged"], true);
        assert_eq!(
            get_after_put.body["logs-000001"]["aliases"]["logs-read"]["is_write_index"],
            true
        );
        assert_eq!(
            get_after_put.body["logs-000001"]["aliases"]["logs-read"]["routing"],
            "r1"
        );

        assert_eq!(bulk.status, 200);
        assert_eq!(bulk.body["acknowledged"], true);
        assert!(get_after_bulk.body["logs-000001"]["aliases"].get("logs-read").is_none());
        assert!(
            get_after_bulk.body["logs-000001"]["aliases"]["logs-search"]
                .get("filter")
                .is_some()
        );

        assert_eq!(delete.status, 200);
        assert_eq!(delete.body["acknowledged"], true);
        assert!(get_after_delete.body["logs-000001"]["aliases"].get("logs-search").is_none());
    }

    #[test]
    fn template_live_route_supports_component_and_composable_put_get_round_trip() {
        let local_port = 19317;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("template-live-route-data"),
            gateway_dir: unique_test_path("template-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("template-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("template-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-18", 18),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {},
                "templates": {
                    "legacy_index_templates": {},
                    "component_templates": {},
                    "index_templates": {}
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _template_runtime_route_table =
            os_node::template_route_registration::TEMPLATE_ROUTE_REGISTRY_TABLE;
        node.register_get_index_endpoint();
        node.start_rest();

        let put_component = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Put,
                "/_component_template/logs-component",
            )
            .with_json_body(serde_json::json!({
                "template": {
                    "settings": {
                        "index": {
                            "number_of_replicas": 0
                        }
                    }
                },
                "version": 1
            })),
        );
        let get_component = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_component_template/logs-component",
        ));
        let put_index_template = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Put,
                "/_index_template/logs-template",
            )
            .with_json_body(serde_json::json!({
                "index_patterns": ["logs-*"],
                "composed_of": ["logs-component"],
                "template": {
                    "settings": {
                        "index": {
                            "number_of_shards": 1
                        }
                    }
                },
                "priority": 10
            })),
        );
        let get_index_template = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_index_template/logs-template",
        ));

        assert_eq!(put_component.status, 200);
        assert_eq!(put_component.body["acknowledged"], true);
        assert!(get_component.body.get("logs-component").is_some());

        assert_eq!(put_index_template.status, 200);
        assert_eq!(put_index_template.body["acknowledged"], true);
        assert!(get_index_template.body.get("logs-template").is_some());
    }

    #[test]
    fn legacy_template_live_route_supports_put_get_round_trip() {
        let local_port = 19318;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("legacy-template-live-route-data"),
            gateway_dir: unique_test_path("legacy-template-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("legacy-template-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("legacy-template-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-19", 19),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {},
                "templates": {
                    "legacy_index_templates": {},
                    "component_templates": {},
                    "index_templates": {}
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _legacy_template_runtime_route_table =
            os_node::legacy_template_route_registration::LEGACY_TEMPLATE_ROUTE_REGISTRY_TABLE;
        node.register_get_index_endpoint();
        node.start_rest();

        let put_legacy_template = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Put,
                "/_template/logs-legacy-template",
            )
            .with_json_body(serde_json::json!({
                "index_patterns": ["logs-*"],
                "order": 5,
                "settings": {
                    "index": {
                        "number_of_replicas": 0
                    }
                }
            })),
        );
        let get_legacy_template = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_template/logs-legacy-template",
        ));

        assert_eq!(put_legacy_template.status, 200);
        assert_eq!(put_legacy_template.body["acknowledged"], true);
        assert!(get_legacy_template.body.get("logs-legacy-template").is_some());
    }

    #[test]
    fn data_stream_live_route_stays_fail_closed_for_read_write_and_stats_forms() {
        let local_port = 19319;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("data-stream-live-route-data"),
            gateway_dir: unique_test_path("data-stream-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("data-stream-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("data-stream-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-20", 20),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {},
                "templates": {
                    "legacy_index_templates": {},
                    "component_templates": {},
                    "index_templates": {}
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _data_stream_runtime_route_table =
            os_node::data_stream_route_registration::DATA_STREAM_ROUTE_REGISTRY_TABLE;
        node.register_get_index_endpoint();
        node.start_rest();

        let get_all = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_data_stream",
        ));
        let get_stats = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_data_stream/_stats",
        ));
        let put_named = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Put,
            "/_data_stream/logs-ds",
        ));
        let delete_named = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Delete,
            "/_data_stream/logs-ds",
        ));

        for response in [get_all, get_stats, put_named, delete_named] {
            assert_eq!(response.status, 400);
            assert_eq!(response.body["error"]["type"], "illegal_argument_exception");
            assert_eq!(
                response.body["error"]["reason"],
                "unsupported data-stream lifecycle surface"
            );
        }
    }

    #[test]
    fn rollover_live_route_stays_fail_closed_for_named_and_unnamed_forms() {
        let local_port = 19320;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("rollover-live-route-data"),
            gateway_dir: unique_test_path("rollover-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("rollover-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("rollover-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-21", 21),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {},
                "templates": {
                    "legacy_index_templates": {},
                    "component_templates": {},
                    "index_templates": {}
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _rollover_runtime_route_table =
            os_node::rollover_route_registration::ROLLOVER_ROUTE_REGISTRY_TABLE;
        node.register_get_index_endpoint();
        node.start_rest();

        let unnamed = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Post,
            "/logs-write/_rollover",
        ));
        let named = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Post,
            "/logs-write/_rollover/logs-000002",
        ));

        for response in [unnamed, named] {
            assert_eq!(response.status, 400);
            assert_eq!(response.body["error"]["type"], "illegal_argument_exception");
            assert_eq!(
                response.body["error"]["reason"],
                "unsupported rollover lifecycle surface"
            );
        }
    }

    #[test]
    fn mapping_live_route_supports_global_wildcard_and_comma_readback() {
        let local_port = 19314;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("mapping-live-route-data"),
            gateway_dir: unique_test_path("mapping-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("mapping-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("mapping-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-13", 13),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {
                    "logs-000001": {
                        "settings": {},
                        "mappings": { "properties": { "message": { "type": "text" } } },
                        "aliases": {}
                    },
                    "logs-000002": {
                        "settings": {},
                        "mappings": { "properties": { "message": { "type": "text" } } },
                        "aliases": {}
                    },
                    "metrics-000001": {
                        "settings": {},
                        "mappings": { "properties": { "value": { "type": "long" } } },
                        "aliases": {}
                    }
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _mapping_runtime_route_table =
            os_node::mapping_route_registration::MAPPING_ROUTE_REGISTRY_TABLE;
        node.register_get_index_endpoint();
        node.start_rest();

        let global = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_mapping",
        ));
        let wildcard = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-*/_mapping",
        ));
        let comma = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-000001,metrics-000001/_mapping",
        ));

        assert_eq!(global.status, 200);
        assert!(global.body.get("logs-000001").is_some());
        assert!(global.body.get("metrics-000001").is_some());
        assert!(global.body["logs-000001"].get("mappings").is_some());

        assert_eq!(wildcard.status, 200);
        assert!(wildcard.body.get("logs-000001").is_some());
        assert!(wildcard.body.get("logs-000002").is_some());
        assert!(wildcard.body.get("metrics-000001").is_none());

        assert_eq!(comma.status, 200);
        assert!(comma.body.get("logs-000001").is_some());
        assert!(comma.body.get("metrics-000001").is_some());
        assert!(comma.body.get("logs-000002").is_none());
    }

    #[test]
    fn mapping_update_live_route_accepts_bounded_properties_subset() {
        let local_port = 19315;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("mapping-update-live-route-data"),
            gateway_dir: unique_test_path("mapping-update-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("mapping-update-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("mapping-update-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-14", 14),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {
                    "logs-000001": {
                        "settings": {},
                        "mappings": { "properties": { "message": { "type": "text" } } },
                        "aliases": {}
                    }
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _mapping_runtime_route_table =
            os_node::mapping_route_registration::MAPPING_ROUTE_REGISTRY_TABLE;
        node.register_get_index_endpoint();
        node.start_rest();

        let put = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/logs-000001/_mapping").with_body(
                serde_json::json!({
                    "properties": {
                        "level": {
                            "type": "keyword"
                        }
                    }
                }),
            ),
        );
        let get = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-000001/_mapping",
        ));

        assert_eq!(put.status, 200);
        assert_eq!(get.status, 200);
        assert_eq!(
            get.body["logs-000001"]["mappings"]["properties"]["level"]["type"],
            "keyword"
        );
    }

    #[test]
    fn settings_live_route_supports_global_wildcard_and_comma_readback() {
        let local_port = 19316;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("settings-live-route-data"),
            gateway_dir: unique_test_path("settings-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("settings-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("settings-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-15", 15),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {
                    "logs-000001": {
                        "settings": {
                            "index": {
                                "number_of_shards": 1
                            }
                        },
                        "mappings": {},
                        "aliases": {}
                    },
                    "logs-000002": {
                        "settings": {
                            "index": {
                                "number_of_shards": 1
                            }
                        },
                        "mappings": {},
                        "aliases": {}
                    },
                    "metrics-000001": {
                        "settings": {
                            "index": {
                                "number_of_shards": 2
                            }
                        },
                        "mappings": {},
                        "aliases": {}
                    }
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _settings_runtime_route_table =
            os_node::settings_route_registration::SETTINGS_ROUTE_REGISTRY_TABLE;
        node.register_get_index_endpoint();
        node.start_rest();

        let global = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_settings",
        ));
        let wildcard = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-*/_settings",
        ));
        let comma = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-000001,metrics-000001/_settings",
        ));

        assert_eq!(global.status, 200);
        assert!(global.body.get("logs-000001").is_some());
        assert!(global.body.get("metrics-000001").is_some());
        assert!(global.body["logs-000001"].get("settings").is_some());

        assert_eq!(wildcard.status, 200);
        assert!(wildcard.body.get("logs-000001").is_some());
        assert!(wildcard.body.get("logs-000002").is_some());
        assert!(wildcard.body.get("metrics-000001").is_none());

        assert_eq!(comma.status, 200);
        assert!(comma.body.get("logs-000001").is_some());
        assert!(comma.body.get("metrics-000001").is_some());
        assert!(comma.body.get("logs-000002").is_none());
    }

    #[test]
    fn settings_update_live_route_accepts_bounded_mutable_subset() {
        let local_port = 19317;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("settings-update-live-route-data"),
            gateway_dir: unique_test_path("settings-update-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("settings-update-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("settings-update-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-16", 16),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {
                    "logs-000001": {
                        "settings": {
                            "index": {
                                "number_of_replicas": 1,
                                "refresh_interval": "5s"
                            }
                        },
                        "mappings": {},
                        "aliases": {}
                    }
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _settings_runtime_route_table =
            os_node::settings_route_registration::SETTINGS_ROUTE_REGISTRY_TABLE;
        node.register_get_index_endpoint();
        node.start_rest();

        let put = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/logs-000001/_settings").with_body(
                serde_json::json!({
                    "index": {
                        "number_of_replicas": 0,
                        "refresh_interval": "1s"
                    }
                }),
            ),
        );
        let get = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-000001/_settings",
        ));

        assert_eq!(put.status, 200);
        assert_eq!(get.status, 200);
        assert_eq!(
            get.body["logs-000001"]["settings"]["index"]["number_of_replicas"],
            serde_json::json!(0)
        );
        assert_eq!(
            get.body["logs-000001"]["settings"]["index"]["refresh_interval"],
            serde_json::json!("1s")
        );
    }

    #[test]
    fn delete_index_live_route_supports_wildcard_and_missing_error_shapes() {
        let local_port = 19313;
        let config = NodeConfig {
            node_name: "node-a".to_string(),
            cluster_name: "steelsearch-dev".to_string(),
            data_dir: unique_test_path("delete-index-live-route-data"),
            gateway_dir: unique_test_path("delete-index-live-route-gateway-dir"),
            transport: TransportConfig {
                bind_address: format!("127.0.0.1:{local_port}"),
                publish_address: format!("127.0.0.1:{local_port}"),
                connect_timeout_ms: 1_000,
                tcp_nodelay: true,
            },
            discovery: DiscoveryConfig::single_node(),
            bootstrap_cluster_manager_nodes: vec!["node-a".to_string()],
            seed_hosts: vec![],
            rest_api: RestApiConfig {
                enabled: false,
                bind_address: "127.0.0.1:0".to_string(),
                publish_address: None,
            },
            search: SearchNodeConfig::default(),
        };
        let metadata_path = unique_test_path("delete-index-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("delete-index-live-route-gateway.json");
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-12", 12),
            cluster_state: development_cluster_view(&config, "cluster-uuid"),
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_name": "steelsearch-dev",
                "cluster_uuid": "cluster-uuid",
                "local_node_id": "node-a",
                "nodes": [{
                    "node_id": "node-a",
                    "node_name": "steelsearch-dev-node",
                    "http_address": serde_json::Value::Null,
                    "transport_address": format!("127.0.0.1:{local_port}"),
                    "roles": ["cluster_manager", "data", "ingest"],
                    "local": true
                }],
                "indices": {
                    "logs-000001": {
                        "settings": {},
                        "mappings": { "properties": { "message": { "type": "text" } } },
                        "aliases": {}
                    },
                    "logs-000002": {
                        "settings": {},
                        "mappings": { "properties": { "message": { "type": "text" } } },
                        "aliases": {}
                    }
                }
            })),
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: None,
        };
        persist_gateway_state_manifest(&gateway_manifest_path, &persisted).unwrap();

        let recovered_gateway = load_gateway_state_manifest(&gateway_manifest_path)
            .unwrap()
            .unwrap();
        let restored_cluster_view = restore_gateway_startup_cluster_view(
            &config,
            "cluster-uuid",
            Some(&recovered_gateway),
        )
        .unwrap();
        restore_gateway_cluster_metadata_manifest(&metadata_path, Some(&recovered_gateway)).unwrap();
        let coordinated_view = apply_development_coordination_with_persisted_state(
            restored_cluster_view,
            Some(recovered_gateway.coordination_state.clone()),
            recovered_gateway.task_queue_state.clone(),
            Some(&gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            &metadata_path,
            &gateway_manifest_path,
            coordinated_view.clone(),
        )
        .unwrap();
        let _delete_index_runtime_route_table =
            os_node::delete_index_route_registration::DELETE_INDEX_ROUTE_REGISTRY_TABLE;
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_get_index_endpoint();
        node.start_rest();

        let wildcard = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Delete,
            "/logs-*",
        ));
        let missing = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Delete,
            "/missing-000001",
        ));

        assert_eq!(wildcard.status, 200);
        assert_eq!(wildcard.body["acknowledged"], serde_json::json!(true));
        assert_eq!(missing.status, 404);
        assert_eq!(
            missing.body["error"]["type"],
            serde_json::json!("index_not_found_exception")
        );
    }

    #[test]
    fn scheduled_election_retries_until_success() {
        let mut scheduler = ElectionScheduler::new(ElectionSchedulerConfig {
            initial_timeout: std::time::Duration::from_millis(10),
            backoff_time: std::time::Duration::from_millis(5),
            max_timeout: std::time::Duration::from_millis(20),
            duration: std::time::Duration::from_millis(3),
        });
        let mut attempts = 0u64;

        let (result, windows) = run_scheduled_election(&mut scheduler, 3, || {
            attempts += 1;
            ElectionResult {
                elected_node_id: (attempts == 3).then(|| "node-a".to_string()),
                term: attempts as i64,
                votes: (attempts == 3)
                    .then(|| {
                        ["node-a".to_string(), "node-c".to_string()]
                            .into_iter()
                            .collect()
                    })
                    .unwrap_or_default(),
                required_quorum: 2,
            }
        });

        assert_eq!(attempts, 3);
        assert_eq!(windows.len(), 3);
        assert_eq!(windows[0].delay, std::time::Duration::from_millis(10));
        assert_eq!(windows[1].delay, std::time::Duration::from_millis(15));
        assert_eq!(windows[2].delay, std::time::Duration::from_millis(20));
        assert_eq!(result.elected_node_id.as_deref(), Some("node-a"));
        assert_eq!(scheduler.attempts(), 3);
    }

    #[test]
    fn scheduled_election_does_not_stop_on_insufficient_vote_count() {
        let mut scheduler = ElectionScheduler::new(ElectionSchedulerConfig {
            initial_timeout: std::time::Duration::from_millis(10),
            backoff_time: std::time::Duration::from_millis(5),
            max_timeout: std::time::Duration::from_millis(20),
            duration: std::time::Duration::from_millis(3),
        });
        let mut attempts = 0u64;

        let (result, windows) = run_scheduled_election(&mut scheduler, 3, || {
            attempts += 1;
            if attempts < 3 {
                ElectionResult {
                    elected_node_id: Some("node-a".to_string()),
                    term: attempts as i64,
                    votes: ["node-a".to_string()].into_iter().collect(),
                    required_quorum: 2,
                }
            } else {
                ElectionResult {
                    elected_node_id: Some("node-a".to_string()),
                    term: attempts as i64,
                    votes: ["node-a".to_string(), "node-c".to_string()]
                        .into_iter()
                        .collect(),
                    required_quorum: 2,
                }
            }
        });

        assert_eq!(attempts, 3);
        assert_eq!(windows.len(), 3);
        assert_eq!(result.elected_node_id.as_deref(), Some("node-a"));
        assert_eq!(result.votes.len() as u64, result.required_quorum);
    }

    #[test]
    fn scheduled_election_returns_no_leader_when_attempt_budget_expires_without_quorum() {
        let mut scheduler = ElectionScheduler::new(ElectionSchedulerConfig {
            initial_timeout: std::time::Duration::from_millis(10),
            backoff_time: std::time::Duration::from_millis(5),
            max_timeout: std::time::Duration::from_millis(20),
            duration: std::time::Duration::from_millis(3),
        });
        let mut attempts = 0u64;

        let (result, windows) = run_scheduled_election(&mut scheduler, 3, || {
            attempts += 1;
            ElectionResult {
                elected_node_id: Some("node-a".to_string()),
                term: attempts as i64,
                votes: ["node-a".to_string()].into_iter().collect(),
                required_quorum: 2,
            }
        });

        assert_eq!(attempts, 3);
        assert_eq!(windows.len(), 3);
        assert_eq!(result.elected_node_id, None);
        assert_eq!(result.required_quorum, 2);
    }

    #[test]
    fn scheduled_liveness_checks_repeat_until_local_fence() {
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--node.id",
                "node-a",
                "--transport.port",
                "19301",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        let mut coordination = ClusterCoordinationState::bootstrap(&DiscoveryConfig {
            cluster_name: config.cluster_name.clone(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: config.node_id.clone(),
            local_node_name: config.node_name.clone(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        });

        let mut manager_peer =
            development_peer_from_node(
                "steelsearch-dev",
                "cluster-uuid",
                &DevelopmentClusterNode {
                    node_id: "node-b".to_string(),
                    node_name: "node-b".to_string(),
                    http_address: None,
                    transport_address: "192.0.2.10:1".to_string(),
                    roles: vec!["cluster_manager".to_string()],
                    local: false,
                },
            )
            .unwrap();
        manager_peer.host = "192.0.2.10".to_string();
        manager_peer.port = 1;
        coordination
            .join_peer(
                &DiscoveryConfig {
                    cluster_name: config.cluster_name.clone(),
                    cluster_uuid: "cluster-uuid".to_string(),
                    local_node_id: config.node_id.clone(),
                    local_node_name: config.node_name.clone(),
                    local_version: OPENSEARCH_3_7_0_TRANSPORT,
                    min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
                    cluster_manager_eligible: true,
                    local_membership_epoch: 1,
                    seed_peers: Vec::new(),
                },
                manager_peer,
            )
            .unwrap();
        coordination.propose_voting_config_addition("node-b").unwrap();
        coordination.apply_voting_config_reconfiguration_proposals();
        coordination.cluster_manager_node_id = Some("node-b".to_string());

        let discovery_config = DiscoveryConfig {
            cluster_name: config.cluster_name.clone(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: config.node_id.clone(),
            local_node_name: config.node_name.clone(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        };

        let outcome = run_periodic_liveness_checks(
            &mut coordination,
            &discovery_config,
            3,
            Duration::from_millis(50),
        );

        assert_eq!(outcome.ticks, vec![1, 2]);
        assert_eq!(
            outcome
                .re_election
                .as_ref()
                .and_then(|e| e.elected_node_id.as_deref()),
            None
        );
        assert_eq!(coordination.liveness.quorum_lost_at_tick, Some(2));
        assert!(coordination.liveness.local_fence_reason.is_some());
        assert_eq!(coordination.cluster_manager_node_id, None);
    }

    #[test]
    fn periodic_liveness_checks_stop_after_repeated_leader_failures_fence_the_node() {
        let discovery = DiscoveryConfig {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            local_node_name: "steel-a".to_string(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        };
        let manager_peer = DiscoveryPeer {
            node_id: "node-b".to_string(),
            node_name: "steel-b".to_string(),
            host: "192.0.2.11".to_string(),
            port: 1,
            cluster_name: discovery.cluster_name.clone(),
            cluster_uuid: discovery.cluster_uuid.clone(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            membership_epoch: 1,
        };
        let mut coordination = ClusterCoordinationState::bootstrap(&discovery);
        coordination.join_peer(&discovery, manager_peer.clone()).unwrap();
        coordination.propose_voting_config_addition("node-b").unwrap();
        coordination.apply_voting_config_reconfiguration_proposals();
        coordination.cluster_manager_node_id = Some(manager_peer.node_id.clone());

        let outcome = run_periodic_liveness_checks(
            &mut coordination,
            &discovery,
            3,
            Duration::from_millis(100),
        );

        assert_eq!(outcome.ticks, vec![1, 2]);
        assert_eq!(
            outcome
                .re_election
                .as_ref()
                .and_then(|e| e.elected_node_id.as_deref()),
            None
        );
        assert_eq!(coordination.liveness.quorum_lost_at_tick, Some(2));
        assert!(coordination.liveness.local_fence_reason.is_some());
        assert_eq!(coordination.cluster_manager_node_id, None);
    }

    #[test]
    fn development_coordination_reports_periodic_liveness_results() {
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--node.id",
                "node-a",
                "--transport.port",
                "19301",
                "--discovery.seed_hosts",
                "127.0.0.1:19301",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        let view =
            apply_development_coordination(development_cluster_view(&config, "cluster-uuid"));
        let coordination = view.coordination.unwrap();

        assert_eq!(coordination.liveness_ticks, vec![1, 2]);
        assert_eq!(coordination.publication_round_versions, vec![1, 2]);
        assert_eq!(coordination.quorum_lost_at_tick, None);
        assert_eq!(coordination.local_fence_reason, None);
    }

    #[test]
    fn development_coordination_executes_repeated_publication_rounds() {
        let vars = BTreeMap::new();
        let config = daemon_config_from_sources(
            &vars,
            [
                "--node.id",
                "node-a",
                "--transport.port",
                "19301",
                "--discovery.seed_hosts",
                "127.0.0.1:19301",
            ]
            .into_iter()
            .map(ToOwned::to_owned),
        )
        .unwrap();

        let view =
            apply_development_coordination(development_cluster_view(&config, "cluster-uuid"));
        let coordination = view.coordination.unwrap();

        assert_eq!(coordination.publication_round_versions, vec![1, 2]);
        assert_eq!(coordination.last_completed_publication_round_version, Some(1));
        assert_eq!(
            coordination.last_completed_publication_round_state_uuid.as_deref(),
            Some("cluster-uuid-dev-state-1")
        );
        assert_eq!(coordination.acked_nodes, vec!["node-a".to_string()]);
        assert_eq!(coordination.applied_nodes, vec!["node-a".to_string()]);
        assert!(coordination.missing_nodes.is_empty());
        assert_eq!(coordination.last_accepted_version, 2);
    }

    #[test]
    fn repeated_publication_round_records_transport_failures_in_active_round() {
        let discovery = DiscoveryConfig {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            local_node_name: "steel-a".to_string(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        };
        let unreachable_peer = DiscoveryPeer {
            node_id: "node-b".to_string(),
            node_name: "steel-b".to_string(),
            host: "192.0.2.10".to_string(),
            port: 1,
            cluster_name: discovery.cluster_name.clone(),
            cluster_uuid: discovery.cluster_uuid.clone(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            membership_epoch: 1,
        };
        let mut coordination = ClusterCoordinationState::bootstrap(&discovery);
        coordination.join_peer(&discovery, unreachable_peer).unwrap();
        coordination.propose_voting_config_addition("node-b").unwrap();
        coordination.apply_voting_config_reconfiguration_proposals();
        coordination.cluster_manager_node_id = Some("node-a".to_string());

        let publication = execute_repeated_publication_rounds(
            &mut coordination,
            &discovery,
            "cluster-uuid",
            1,
            Duration::from_millis(50),
        );

        assert!(!publication.committed);
        let round = coordination.active_publication_round().unwrap();
        assert!(round.missing_nodes.contains("node-b"));
        assert!(round
            .proposal_transport_failures
            .get("node-b")
            .is_some_and(|reason| !reason.is_empty()));
        assert!(round.acknowledgement_transport_failures.is_empty());
        assert!(round.apply_transport_failures.is_empty());
    }

    #[test]
    fn periodic_liveness_checks_fence_local_manager_on_quorum_loss() {
        let discovery = DiscoveryConfig {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            local_node_name: "steel-a".to_string(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        };
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        drop(listener);

        let follower_peer = DiscoveryPeer {
            node_id: "node-b".to_string(),
            node_name: "steel-b".to_string(),
            host: address.ip().to_string(),
            port: address.port(),
            cluster_name: discovery.cluster_name.clone(),
            cluster_uuid: discovery.cluster_uuid.clone(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            membership_epoch: 1,
        };
        let mut coordination = ClusterCoordinationState::bootstrap(&discovery);
        coordination.join_peer(&discovery, follower_peer).unwrap();
        coordination.propose_voting_config_addition("node-b").unwrap();
        coordination.apply_voting_config_reconfiguration_proposals();
        coordination.cluster_manager_node_id = Some("node-a".to_string());

        let outcome = run_periodic_liveness_checks(
            &mut coordination,
            &discovery,
            2,
            Duration::from_millis(100),
        );

        assert_eq!(outcome.ticks, vec![1]);
        assert!(outcome.re_election.is_none());
        assert_eq!(coordination.cluster_manager_node_id, None);
        assert_eq!(coordination.liveness.quorum_lost_at_tick, Some(1));
        assert!(coordination
            .liveness
            .local_fence_reason
            .as_deref()
            .unwrap_or_default()
            .contains("leader lost live voter quorum"));
    }

    #[test]
    fn safe_re_election_triggers_when_faulted_manager_loses_heartbeat_but_quorum_remains() {
        let discovery = DiscoveryConfig {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            local_node_name: "steel-a".to_string(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        };
        let mut coordination = ClusterCoordinationState::bootstrap(&discovery);
        coordination
            .join_peer(
                &discovery,
                DiscoveryPeer {
                    node_id: "node-b".to_string(),
                    node_name: "steel-b".to_string(),
                    host: "127.0.0.1".to_string(),
                    port: 19302,
                    cluster_name: discovery.cluster_name.clone(),
                    cluster_uuid: discovery.cluster_uuid.clone(),
                    version: OPENSEARCH_3_7_0_TRANSPORT,
                    cluster_manager_eligible: true,
                    membership_epoch: 1,
                },
            )
            .unwrap();
        coordination.propose_voting_config_addition("node-b").unwrap();
        coordination
            .join_peer(
                &discovery,
                DiscoveryPeer {
                    node_id: "node-c".to_string(),
                    node_name: "steel-c".to_string(),
                    host: "127.0.0.1".to_string(),
                    port: 19303,
                    cluster_name: discovery.cluster_name.clone(),
                    cluster_uuid: discovery.cluster_uuid.clone(),
                    version: OPENSEARCH_3_7_0_TRANSPORT,
                    cluster_manager_eligible: true,
                    membership_epoch: 1,
                },
            )
            .unwrap();
        coordination.propose_voting_config_addition("node-c").unwrap();
        coordination.apply_voting_config_reconfiguration_proposals();
        coordination.cluster_manager_node_id = Some("node-b".to_string());
        coordination.liveness.record_quorum_loss(2, "leader check failed repeatedly against manager [node-b]");
        coordination
            .fault_detection
            .record_leader_failure("node-b", 2, "leader unreachable");
        coordination
            .fault_detection
            .record_leader_failure("node-b", 3, "leader unreachable");

        let outcome = maybe_transition_from_liveness_with_re_election(
            &mut coordination,
            &discovery,
            Duration::from_millis(200),
            |state, _, _| {
                state.current_term = state.current_term.saturating_add(1);
                state.cluster_manager_node_id = Some("node-a".to_string());
                ElectionResult {
                    elected_node_id: Some("node-a".to_string()),
                    term: state.current_term,
                    votes: ["node-a".to_string(), "node-c".to_string()]
                        .into_iter()
                        .collect(),
                    required_quorum: 2,
                }
            },
        );

        assert_eq!(
            outcome.as_ref().and_then(|e| e.elected_node_id.as_deref()),
            Some("node-a")
        );
        assert_eq!(coordination.cluster_manager_node_id.as_deref(), Some("node-a"));
        assert_eq!(coordination.liveness.local_fence_reason, None);
        assert_eq!(coordination.liveness.quorum_lost_at_tick, None);
        assert_eq!(coordination.fault_detection.leader_nodes.get("node-b"), None);
    }

    #[test]
    fn election_and_publication_rounds_use_majority_quorum_for_three_manager_nodes() {
        let discovery = DiscoveryConfig {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            local_node_name: "steel-a".to_string(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        };
        let mut coordination = ClusterCoordinationState::bootstrap(&discovery);
        for (node_id, node_name, port) in [
            ("node-b", "steel-b", 19302_u16),
            ("node-c", "steel-c", 19303_u16),
        ] {
            coordination
                .join_peer(
                    &discovery,
                    DiscoveryPeer {
                        node_id: node_id.to_string(),
                        node_name: node_name.to_string(),
                        host: "127.0.0.1".to_string(),
                        port,
                        cluster_name: discovery.cluster_name.clone(),
                        cluster_uuid: discovery.cluster_uuid.clone(),
                        version: OPENSEARCH_3_7_0_TRANSPORT,
                        cluster_manager_eligible: true,
                        membership_epoch: 1,
                    },
                )
                .unwrap();
            coordination.propose_voting_config_addition(node_id).unwrap();
        }
        coordination.apply_voting_config_reconfiguration_proposals();

        let election = coordination.elect_cluster_manager_with_live_pre_votes(
            &discovery,
            "node-a",
            Duration::from_millis(50),
        );
        assert_eq!(election.required_quorum, 2);

        let publish = coordination.publish_committed_state(
            "cluster-uuid-dev-state-2".to_string(),
            2,
            ["node-a".to_string(), "node-b".to_string(), "node-c".to_string()]
                .into_iter()
                .collect(),
        );
        assert!(publish.committed);
        assert_eq!(
            coordination
                .active_publication_round()
                .map(|round| round.required_quorum),
            Some(2)
        );
    }

    #[test]
    fn joined_peers_do_not_change_quorum_until_voting_reconfiguration_applies() {
        let discovery = DiscoveryConfig {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            local_node_name: "steel-a".to_string(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        };
        let mut coordination = ClusterCoordinationState::bootstrap(&discovery);
        for (node_id, node_name, port) in [
            ("node-b", "steel-b", 19302_u16),
            ("node-c", "steel-c", 19303_u16),
        ] {
            coordination
                .join_peer(
                    &discovery,
                    DiscoveryPeer {
                        node_id: node_id.to_string(),
                        node_name: node_name.to_string(),
                        host: "127.0.0.1".to_string(),
                        port,
                        cluster_name: discovery.cluster_name.clone(),
                        cluster_uuid: discovery.cluster_uuid.clone(),
                        version: OPENSEARCH_3_7_0_TRANSPORT,
                        cluster_manager_eligible: true,
                        membership_epoch: 1,
                    },
                )
                .unwrap();
        }

        let before = coordination.elect_cluster_manager_with_live_pre_votes(
            &discovery,
            "node-a",
            Duration::from_millis(50),
        );
        assert_eq!(before.required_quorum, 1);
        assert_eq!(
            coordination.last_accepted_voting_configuration,
            std::collections::BTreeSet::from(["node-a".to_string()])
        );

        coordination.propose_voting_config_addition("node-b").unwrap();
        coordination.propose_voting_config_addition("node-c").unwrap();
        coordination.apply_voting_config_reconfiguration_proposals();

        let after = coordination.elect_cluster_manager_with_live_pre_votes(
            &discovery,
            "node-a",
            Duration::from_millis(50),
        );
        assert_eq!(after.required_quorum, 2);
        assert_eq!(
            coordination.last_accepted_voting_configuration,
            std::collections::BTreeSet::from([
                "node-a".to_string(),
                "node-b".to_string(),
                "node-c".to_string(),
            ])
        );
    }

    #[test]
    fn joint_voting_configuration_union_and_exclusions_drive_required_quorum() {
        let discovery = DiscoveryConfig {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            local_node_name: "steel-a".to_string(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        };
        let mut coordination = ClusterCoordinationState::bootstrap(&discovery);
        coordination.last_accepted_voting_configuration =
            std::collections::BTreeSet::from(["node-a".to_string(), "node-b".to_string()]);
        coordination.last_committed_voting_configuration = std::collections::BTreeSet::from([
            "node-a".to_string(),
            "node-b".to_string(),
            "node-c".to_string(),
            "node-d".to_string(),
        ]);

        let before_exclusion = coordination.elect_cluster_manager_with_live_pre_votes(
            &discovery,
            "node-a",
            Duration::from_millis(50),
        );
        assert_eq!(before_exclusion.required_quorum, 3);

        coordination
            .voting_config_exclusions
            .insert("node-d".to_string());
        let after_exclusion = coordination.elect_cluster_manager_with_live_pre_votes(
            &discovery,
            "node-a",
            Duration::from_millis(50),
        );
        assert_eq!(after_exclusion.required_quorum, 2);
    }

    #[test]
    fn local_manager_liveness_keeps_cluster_active_when_majority_quorum_remains_reachable() {
        let discovery = DiscoveryConfig {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            local_node_name: "steel-a".to_string(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        };
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let reachable_address = listener.local_addr().unwrap();
        let accept_thread = std::thread::spawn(move || {
            if let Ok((_stream, _addr)) = listener.accept() {
                std::thread::sleep(Duration::from_millis(10));
            }
        });

        let mut coordination = ClusterCoordinationState::bootstrap(&discovery);
        for (node_id, node_name, host, port) in [
            (
                "node-b",
                "steel-b",
                reachable_address.ip().to_string(),
                reachable_address.port(),
            ),
            ("node-c", "steel-c", "192.0.2.13".to_string(), 1_u16),
        ] {
            coordination
                .join_peer(
                    &discovery,
                    DiscoveryPeer {
                        node_id: node_id.to_string(),
                        node_name: node_name.to_string(),
                        host,
                        port,
                        cluster_name: discovery.cluster_name.clone(),
                        cluster_uuid: discovery.cluster_uuid.clone(),
                        version: OPENSEARCH_3_7_0_TRANSPORT,
                        cluster_manager_eligible: true,
                        membership_epoch: 1,
                    },
                )
                .unwrap();
            coordination.propose_voting_config_addition(node_id).unwrap();
        }
        coordination.apply_voting_config_reconfiguration_proposals();
        coordination.cluster_manager_node_id = Some("node-a".to_string());

        let outcome = run_periodic_liveness_checks(
            &mut coordination,
            &discovery,
            1,
            Duration::from_millis(100),
        );

        accept_thread.join().unwrap();
        assert_eq!(outcome.ticks, vec![1]);
        assert!(outcome.re_election.is_none());
        assert_eq!(coordination.cluster_manager_node_id.as_deref(), Some("node-a"));
        assert_eq!(coordination.liveness.quorum_lost_at_tick, None);
        assert_eq!(coordination.liveness.local_fence_reason, None);
    }

    #[test]
    fn follower_re_election_stays_fail_closed_without_majority_votes() {
        let discovery = DiscoveryConfig {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            local_node_name: "steel-a".to_string(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        };
        let mut coordination = ClusterCoordinationState::bootstrap(&discovery);
        for (node_id, node_name, port) in [
            ("node-b", "steel-b", 19302_u16),
            ("node-c", "steel-c", 19303_u16),
        ] {
            coordination
                .join_peer(
                    &discovery,
                    DiscoveryPeer {
                        node_id: node_id.to_string(),
                        node_name: node_name.to_string(),
                        host: "127.0.0.1".to_string(),
                        port,
                        cluster_name: discovery.cluster_name.clone(),
                        cluster_uuid: discovery.cluster_uuid.clone(),
                        version: OPENSEARCH_3_7_0_TRANSPORT,
                        cluster_manager_eligible: true,
                        membership_epoch: 1,
                    },
                )
                .unwrap();
            coordination.propose_voting_config_addition(node_id).unwrap();
        }
        coordination.apply_voting_config_reconfiguration_proposals();
        coordination.cluster_manager_node_id = Some("node-b".to_string());
        coordination
            .liveness
            .record_quorum_loss(2, "leader check failed repeatedly against manager [node-b]");
        coordination
            .fault_detection
            .record_leader_failure("node-b", 2, "leader unreachable");

        let outcome = maybe_transition_from_liveness(
            &mut coordination,
            &discovery,
            Duration::from_millis(100),
        );

        assert!(outcome.is_none());
        assert_eq!(coordination.cluster_manager_node_id, None);
        assert_eq!(coordination.liveness.quorum_lost_at_tick, Some(2));
        assert!(coordination.liveness.local_fence_reason.is_some());
    }

    #[test]
    fn publication_commit_stays_fail_closed_when_target_set_is_below_required_quorum() {
        let discovery = DiscoveryConfig {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            local_node_name: "steel-a".to_string(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        };
        let mut coordination = ClusterCoordinationState::bootstrap(&discovery);
        for (node_id, node_name, port) in [
            ("node-b", "steel-b", 19302_u16),
            ("node-c", "steel-c", 19303_u16),
        ] {
            coordination
                .join_peer(
                    &discovery,
                    DiscoveryPeer {
                        node_id: node_id.to_string(),
                        node_name: node_name.to_string(),
                        host: "127.0.0.1".to_string(),
                        port,
                        cluster_name: discovery.cluster_name.clone(),
                        cluster_uuid: discovery.cluster_uuid.clone(),
                        version: OPENSEARCH_3_7_0_TRANSPORT,
                        cluster_manager_eligible: true,
                        membership_epoch: 1,
                    },
                )
                .unwrap();
            coordination.propose_voting_config_addition(node_id).unwrap();
        }
        coordination.apply_voting_config_reconfiguration_proposals();

        let publication = coordination.publish_committed_state(
            "cluster-uuid-dev-state-7".to_string(),
            7,
            ["node-a".to_string()].into_iter().collect(),
        );

        assert!(!publication.committed);
        assert_eq!(
            coordination
                .active_publication_round()
                .map(|round| round.required_quorum),
            Some(2)
        );
        assert_eq!(
            coordination
                .active_publication_round()
                .map(|round| round.committed),
            Some(false)
        );
    }

    #[test]
    fn restored_voting_configuration_and_exclusions_preserve_quorum_after_restart() {
        let discovery = DiscoveryConfig {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            local_node_name: "steel-a".to_string(),
            local_version: OPENSEARCH_3_7_0_TRANSPORT,
            min_compatible_version: OPENSEARCH_3_7_0_TRANSPORT,
            cluster_manager_eligible: true,
            local_membership_epoch: 1,
            seed_peers: Vec::new(),
        };
        let mut original = ClusterCoordinationState::bootstrap(&discovery);
        original.last_accepted_voting_configuration = std::collections::BTreeSet::from([
            "node-a".to_string(),
            "node-b".to_string(),
        ]);
        original.last_committed_voting_configuration = std::collections::BTreeSet::from([
            "node-a".to_string(),
            "node-b".to_string(),
            "node-c".to_string(),
            "node-d".to_string(),
        ]);
        original
            .voting_config_exclusions
            .insert("node-d".to_string());
        let persisted = original.capture_publication_state();

        let mut restored = ClusterCoordinationState::bootstrap(&discovery);
        restored.restore_publication_state(persisted);
        let election = restored.elect_cluster_manager_with_live_pre_votes(
            &discovery,
            "node-a",
            Duration::from_millis(50),
        );

        assert_eq!(
            restored.last_accepted_voting_configuration,
            std::collections::BTreeSet::from([
                "node-a".to_string(),
                "node-b".to_string(),
            ])
        );
        assert_eq!(
            restored.last_committed_voting_configuration,
            std::collections::BTreeSet::from([
                "node-a".to_string(),
                "node-b".to_string(),
                "node-c".to_string(),
                "node-d".to_string(),
            ])
        );
        assert_eq!(
            restored.voting_config_exclusions,
            std::collections::BTreeSet::from(["node-d".to_string()])
        );
        assert_eq!(election.required_quorum, 2);
    }
}

#[cfg(test)]
mod cluster_settings_live_route_parity_tests {
    use super::*;
    use std::collections::BTreeMap;

    fn cluster_settings_persisted_gateway_state() -> PersistedGatewayState {
        PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-7", 7),
            cluster_state: DevelopmentClusterView {
                cluster_name: "steelsearch-dev".to_string(),
                cluster_uuid: "cluster-uuid".to_string(),
                local_node_id: "node-a".to_string(),
                nodes: vec![],
                coordination: None,
            },
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_uuid": "cluster-uuid",
                "cluster_settings": {
                    "persistent": {},
                    "transient": {}
                },
                "indices": {},
                "templates": {
                    "legacy_index_templates": {},
                    "component_templates": {},
                    "index_templates": {}
                }
            })),
            routing_metadata: None,
            metadata_state: Some(os_node::PersistedGatewayMetadataState {
                cluster_settings: os_node::ClusterSettingsState {
                    persistent: BTreeMap::from([(
                        "cluster.routing.allocation.enable".to_string(),
                        serde_json::json!("all"),
                    )]),
                    transient: BTreeMap::from([(
                        "cluster.info.update.interval".to_string(),
                        serde_json::json!("30s"),
                    )]),
                },
                index_aliases: BTreeMap::new(),
                legacy_index_templates: BTreeMap::new(),
                component_templates: BTreeMap::new(),
                index_templates: BTreeMap::new(),
            }),
            metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                "node-a", "state-7", 7,
            )),
            task_queue_state: None,
        }
    }

    fn build_cluster_settings_live_route_node(
        metadata_path: &std::path::Path,
        gateway_manifest_path: &std::path::Path,
    ) -> SteelNode {
        let persisted = cluster_settings_persisted_gateway_state();
        persist_gateway_state_manifest(gateway_manifest_path, &persisted).unwrap();
        restore_gateway_cluster_metadata_manifest(metadata_path, Some(&persisted)).unwrap();
        let cluster_view = apply_development_coordination_with_persisted_state(
            persisted.cluster_state.clone(),
            Some(persisted.coordination_state.clone()),
            persisted.task_queue_state.clone(),
            Some(gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            metadata_path,
            gateway_manifest_path,
            cluster_view.clone(),
        )
        .unwrap();
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_development_cluster_endpoints(cluster_view);
        node.start_rest();
        node
    }

    #[test]
    fn cluster_settings_live_route_reads_bounded_persistent_and_transient_sections() {
        let metadata_path = unique_test_path("cluster-settings-live-route-readback.json");
        let gateway_manifest_path =
            unique_test_path("cluster-settings-live-route-readback-gateway.json");
        let node = build_cluster_settings_live_route_node(&metadata_path, &gateway_manifest_path);

        let response = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_cluster/settings",
        ));

        assert_eq!(response.status, 200);
        assert_eq!(
            response.body["persistent"]["cluster.routing.allocation.enable"],
            serde_json::json!("all")
        );
        assert_eq!(
            response.body["transient"]["cluster.info.update.interval"],
            serde_json::json!("30s")
        );
    }

    #[test]
    fn cluster_settings_live_route_fail_closes_unsupported_readback_params() {
        let metadata_path = unique_test_path("cluster-settings-live-route-reject.json");
        let gateway_manifest_path =
            unique_test_path("cluster-settings-live-route-reject-gateway.json");
        let node = build_cluster_settings_live_route_node(&metadata_path, &gateway_manifest_path);

        for path in [
            "/_cluster/settings?flat_settings=true",
            "/_cluster/settings?include_defaults=true",
            "/_cluster/settings?local=true",
        ] {
            let response = node.handle_rest_request(os_rest::RestRequest::new(
                os_rest::RestMethod::Get,
                path,
            ));
            assert_eq!(response.status, 400, "unexpected success for {path}");
        }
    }

    #[test]
    fn cluster_settings_live_mutation_route_updates_bounded_sections() {
        let metadata_path = unique_test_path("cluster-settings-live-route-mutate.json");
        let gateway_manifest_path =
            unique_test_path("cluster-settings-live-route-mutate-gateway.json");
        let node = build_cluster_settings_live_route_node(&metadata_path, &gateway_manifest_path);

        let put = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/_cluster/settings").with_body(
                br#"{
                    "persistent": {
                        "cluster.routing.allocation.enable": "primaries"
                    },
                    "transient": {
                        "cluster.info.update.interval": "45s"
                    }
                }"#,
            ),
        );

        assert_eq!(put.status, 200);
        assert_eq!(put.body["acknowledged"], serde_json::json!(true));
        assert_eq!(
            put.body["persistent"]["cluster.routing.allocation.enable"],
            serde_json::json!("primaries")
        );
        assert_eq!(
            put.body["transient"]["cluster.info.update.interval"],
            serde_json::json!("45s")
        );

        let get = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_cluster/settings",
        ));
        assert_eq!(get.status, 200);
        assert_eq!(
            get.body["persistent"]["cluster.routing.allocation.enable"],
            serde_json::json!("primaries")
        );
        assert_eq!(
            get.body["transient"]["cluster.info.update.interval"],
            serde_json::json!("45s")
        );
    }
}

#[cfg(test)]
mod pending_tasks_live_route_parity_tests {
    use super::*;

    fn build_pending_tasks_live_route_node(manifest_path: &std::path::Path) -> SteelNode {
        let persisted_task_queue_state = PersistedClusterManagerTaskQueueState {
            next_task_id: 3,
            task_node_ids: BTreeMap::new(),
            task_statuses: BTreeMap::new(),
            pending: vec![os_node::ClusterManagerTaskRecord {
                task_id: 1,
                task: os_node::ClusterManagerTask {
                    source: "reroute".to_string(),
                    kind: os_node::ClusterManagerTaskKind::Reroute,
                },
                state: os_node::ClusterManagerTaskState::Queued,
                parent_task_id: None,
                headers: BTreeMap::new(),
                failure_reason: None,
            }],
            in_flight: vec![os_node::ClusterManagerTaskRecord {
                task_id: 2,
                task: os_node::ClusterManagerTask {
                    source: "node-left".to_string(),
                    kind: os_node::ClusterManagerTaskKind::RemoveNode {
                        node_id: "node-b".to_string(),
                    },
                },
                state: os_node::ClusterManagerTaskState::InFlight,
                parent_task_id: None,
                headers: BTreeMap::new(),
                failure_reason: None,
            }],
            acknowledged: Vec::new(),
            failed: Vec::new(),
        };
        let cluster_view = DevelopmentClusterView {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            nodes: vec![],
            coordination: None,
        };
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-11", 11),
            cluster_state: cluster_view.clone(),
            cluster_metadata_manifest: None,
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: Some(persisted_task_queue_state.clone()),
        };
        persist_gateway_state_manifest(manifest_path, &persisted).unwrap();
        let cluster_view = apply_development_coordination_with_persisted_state(
            cluster_view,
            Some(persisted.coordination_state.clone()),
            Some(persisted_task_queue_state),
            Some(manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        });
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_development_cluster_endpoints(cluster_view);
        node.start_rest();
        node
    }

    #[test]
    fn cluster_pending_tasks_live_route_reads_bounded_task_array() {
        let manifest_path = unique_test_path("cluster-pending-tasks-live-route-gateway.json");
        let node = build_pending_tasks_live_route_node(&manifest_path);

        let response = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_cluster/pending_tasks",
        ));

        assert_eq!(response.status, 200);
        let tasks = response.body["tasks"].as_array().unwrap();
        assert_eq!(tasks.len(), 2);
        assert!(tasks.iter().any(|task| {
            task["source"] == serde_json::json!("reroute")
                && task.get("time_in_queue_millis").is_some()
        }));
        assert!(tasks.iter().any(|task| {
            task["source"] == serde_json::json!("node-left")
                && task.get("executing").is_some()
        }));
    }
}

#[cfg(test)]
mod tasks_live_route_parity_tests {
    use super::*;

    fn build_tasks_live_route_node(manifest_path: &std::path::Path) -> SteelNode {
        let persisted_task_queue_state = PersistedClusterManagerTaskQueueState {
            next_task_id: 3,
            task_node_ids: BTreeMap::new(),
            task_statuses: BTreeMap::new(),
            pending: vec![os_node::ClusterManagerTaskRecord {
                task_id: 1,
                task: os_node::ClusterManagerTask {
                    source: "reroute".to_string(),
                    kind: os_node::ClusterManagerTaskKind::Reroute,
                },
                state: os_node::ClusterManagerTaskState::Queued,
                parent_task_id: Some("node-a:99".to_string()),
                headers: BTreeMap::from([(
                    "x-opaque-id".to_string(),
                    "task-request-123".to_string(),
                )]),
                failure_reason: None,
            }],
            in_flight: vec![os_node::ClusterManagerTaskRecord {
                task_id: 99,
                task: os_node::ClusterManagerTask {
                    source: "parent reroute".to_string(),
                    kind: os_node::ClusterManagerTaskKind::Reroute,
                },
                state: os_node::ClusterManagerTaskState::InFlight,
                parent_task_id: None,
                headers: BTreeMap::new(),
                failure_reason: None,
            }],
            acknowledged: Vec::new(),
            failed: Vec::new(),
        };
        let cluster_view = DevelopmentClusterView {
            cluster_name: "steelsearch-dev".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            local_node_id: "node-a".to_string(),
            nodes: vec![],
            coordination: None,
        };
        let persisted = PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-13", 13),
            cluster_state: cluster_view.clone(),
            cluster_metadata_manifest: None,
            routing_metadata: None,
            metadata_state: None,
            metadata_commit_state: None,
            task_queue_state: Some(persisted_task_queue_state.clone()),
        };
        persist_gateway_state_manifest(manifest_path, &persisted).unwrap();
        let cluster_view = apply_development_coordination_with_persisted_state(
            cluster_view,
            Some(persisted.coordination_state.clone()),
            Some(persisted_task_queue_state),
            Some(manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        });
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_development_cluster_endpoints(cluster_view);
        node.start_rest();
        node
    }

    #[test]
    fn tasks_live_route_supports_list_get_and_cancel_shapes() {
        let manifest_path = unique_test_path("tasks-live-route-gateway.json");
        let node = build_tasks_live_route_node(&manifest_path);

        let list = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_tasks",
        ));
        assert_eq!(list.status, 200);
        assert!(list.body["nodes"]
            .as_object()
            .unwrap()
            .values()
            .any(|node_entry| node_entry["tasks"].as_object().is_some()));
        assert_eq!(
            list.body["nodes"]["node-a"]["tasks"]["node-a:1"]["headers"]["x-opaque-id"],
            serde_json::json!("task-request-123")
        );

        let mut parents_request = os_rest::RestRequest::new(os_rest::RestMethod::Get, "/_tasks");
        parents_request
            .query_params
            .insert("group_by".to_string(), "parents".to_string());
        let parents = node.handle_rest_request(parents_request);
        assert_eq!(parents.status, 200);
        assert_eq!(
            parents.body["tasks"]["node-a:99"]["children"][0]["id"],
            serde_json::json!(1)
        );
        assert_eq!(
            parents.body["tasks"]["node-a:99"]["children"][0]["parent_task_id"],
            serde_json::json!("node-a:99")
        );
        assert_eq!(
            parents.body["tasks"]["node-a:99"]["children"][0]["headers"]["x-opaque-id"],
            serde_json::json!("task-request-123")
        );

        let get = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_tasks/node-a:1",
        ));
        assert_eq!(get.status, 200);
        assert!(get.body["task"].get("action").is_some());
        assert!(get.body["task"].get("cancellable").is_some());
        assert_eq!(
            get.body["task"]["parent_task_id"],
            serde_json::json!("node-a:99")
        );
        assert_eq!(
            get.body["task"]["headers"]["x-opaque-id"],
            serde_json::json!("task-request-123")
        );

        let cancel = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Post,
            "/_tasks/_cancel?task_id=node-a:1",
        ));
        assert_eq!(cancel.status, 200);
        assert_eq!(
            cancel.body["nodes"]["node-a"]["tasks"]["node-a:1"]["cancelled"],
            serde_json::json!(true)
        );
        assert_eq!(
            cancel.body["nodes"]["node-a"]["tasks"]["node-a:1"]["headers"]["x-opaque-id"],
            serde_json::json!("task-request-123")
        );
        assert!(cancel.body["node_failures"].is_array());
        let cancelled_get = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_tasks/node-a:1",
        ));
        assert_eq!(cancelled_get.status, 200);
        assert_eq!(
            cancelled_get.body["task"]["cancelled"],
            serde_json::json!(true)
        );
    }
}

#[cfg(test)]
mod stats_live_route_parity_tests {
    use super::*;
    use std::collections::BTreeMap;

    fn stats_persisted_gateway_state() -> PersistedGatewayState {
        PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-17", 17),
            cluster_state: DevelopmentClusterView {
                cluster_name: "steelsearch-dev".to_string(),
                cluster_uuid: "cluster-uuid".to_string(),
                local_node_id: "node-a".to_string(),
                nodes: vec![],
                coordination: None,
            },
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_uuid": "cluster-uuid",
                "cluster_settings": {
                    "persistent": {},
                    "transient": {}
                },
                "indices": {},
                "templates": {
                    "legacy_index_templates": {},
                    "component_templates": {},
                    "index_templates": {}
                }
            })),
            routing_metadata: None,
            metadata_state: Some(os_node::PersistedGatewayMetadataState {
                cluster_settings: os_node::ClusterSettingsState {
                    persistent: BTreeMap::new(),
                    transient: BTreeMap::new(),
                },
                index_aliases: BTreeMap::new(),
                legacy_index_templates: BTreeMap::new(),
                component_templates: BTreeMap::new(),
                index_templates: BTreeMap::new(),
            }),
            metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                "node-a", "state-17", 17,
            )),
            task_queue_state: None,
        }
    }

    fn build_stats_live_route_node(
        metadata_path: &std::path::Path,
        gateway_manifest_path: &std::path::Path,
    ) -> SteelNode {
        let persisted = stats_persisted_gateway_state();
        persist_gateway_state_manifest(gateway_manifest_path, &persisted).unwrap();
        restore_gateway_cluster_metadata_manifest(metadata_path, Some(&persisted)).unwrap();
        let cluster_view = apply_development_coordination_with_persisted_state(
            persisted.cluster_state.clone(),
            Some(persisted.coordination_state.clone()),
            persisted.task_queue_state.clone(),
            Some(gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            metadata_path,
            gateway_manifest_path,
            cluster_view.clone(),
        )
        .unwrap();
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_development_cluster_endpoints(cluster_view);
        node.start_rest();
        node
    }

    #[test]
    fn stats_live_routes_expose_bounded_top_level_shapes() {
        let metadata_path = unique_test_path("stats-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("stats-live-route-gateway.json");
        let node = build_stats_live_route_node(&metadata_path, &gateway_manifest_path);

        let nodes = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_nodes/stats",
        ));
        assert_eq!(nodes.status, 200);
        assert!(nodes.body.get("nodes").is_some());

        let cluster = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_cluster/stats",
        ));
        assert_eq!(cluster.status, 200);
        assert!(cluster.body.get("indices").is_some());
        assert!(cluster.body.get("nodes").is_some());

        let index = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_stats",
        ));
        assert_eq!(index.status, 200);
        assert!(index.body.get("_all").is_some());
        assert!(index.body.get("indices").is_some());
    }
}

#[cfg(test)]
mod single_doc_put_live_route_parity_tests {
    use super::*;
    use std::collections::BTreeMap;

    pub(super) fn single_doc_put_persisted_gateway_state() -> PersistedGatewayState {
        PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-22", 22),
            cluster_state: DevelopmentClusterView {
                cluster_name: "steelsearch-dev".to_string(),
                cluster_uuid: "cluster-uuid".to_string(),
                local_node_id: "node-a".to_string(),
                nodes: vec![],
                coordination: None,
            },
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_uuid": "cluster-uuid",
                "cluster_settings": {
                    "persistent": {},
                    "transient": {}
                },
                "indices": {},
                "templates": {
                    "legacy_index_templates": {},
                    "component_templates": {},
                    "index_templates": {}
                }
            })),
            routing_metadata: None,
            metadata_state: Some(os_node::PersistedGatewayMetadataState {
                cluster_settings: os_node::ClusterSettingsState {
                    persistent: BTreeMap::new(),
                    transient: BTreeMap::new(),
                },
                index_aliases: BTreeMap::new(),
                legacy_index_templates: BTreeMap::new(),
                component_templates: BTreeMap::new(),
                index_templates: BTreeMap::new(),
            }),
            metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                "node-a", "state-22", 22,
            )),
            task_queue_state: None,
        }
    }

    fn build_single_doc_put_live_route_node(
        metadata_path: &std::path::Path,
        gateway_manifest_path: &std::path::Path,
    ) -> SteelNode {
        let persisted =
            crate::single_doc_put_live_route_parity_tests::single_doc_put_persisted_gateway_state();
        persist_gateway_state_manifest(gateway_manifest_path, &persisted).unwrap();
        restore_gateway_cluster_metadata_manifest(metadata_path, Some(&persisted)).unwrap();
        let cluster_view = apply_development_coordination_with_persisted_state(
            persisted.cluster_state.clone(),
            Some(persisted.coordination_state.clone()),
            persisted.task_queue_state.clone(),
            Some(gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            metadata_path,
            gateway_manifest_path,
            cluster_view.clone(),
        )
        .unwrap();
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_development_cluster_endpoints(cluster_view);
        node.start_rest();
        node
    }

    #[test]
    fn put_doc_live_route_exposes_bounded_write_shape() {
        let metadata_path = unique_test_path("single-doc-put-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("single-doc-put-live-route-gateway.json");
        let node = build_single_doc_put_live_route_node(&metadata_path, &gateway_manifest_path);

        let create_index = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/logs-000001")
                .with_json_body(serde_json::json!({})),
        );
        assert_eq!(create_index.status, 200);

        let mapping = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/vector-search-compat-000001/_mapping",
        ));
        assert_eq!(mapping.status, 200);
        assert_eq!(
            mapping.body["vector-search-compat-000001"]["mappings"]["properties"]["embedding"]["data_type"],
            "float"
        );
        assert_eq!(
            mapping.body["vector-search-compat-000001"]["mappings"]["properties"]["embedding"]["mode"],
            "in_memory"
        );
        assert_eq!(
            mapping.body["vector-search-compat-000001"]["mappings"]["properties"]["embedding"]["compression_level"],
            "1x"
        );
        assert_eq!(
            mapping.body["vector-search-compat-000001"]["mappings"]["properties"]["embedding"]["doc_values"],
            true
        );
        assert_eq!(
            mapping.body["vector-search-compat-000001"]["mappings"]["properties"]["embedding"]["store"],
            false
        );
        assert_eq!(
            mapping.body["vector-search-compat-000001"]["mappings"]["properties"]["embedding"]["_meta"]["owner"],
            "vector-live-route"
        );
        assert_eq!(
            mapping.body["vector-search-compat-000001"]["mappings"]["properties"]["embedding"]["method"]["name"],
            "hnsw"
        );
        assert_eq!(
            mapping.body["vector-search-compat-000001"]["mappings"]["properties"]["embedding"]["method"]["engine"],
            "lucene"
        );

        let put_doc = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Put,
                "/logs-000001/_doc/doc-1?routing=tenant-a",
            )
            .with_json_body(serde_json::json!({
                "message": "hello"
            })),
        );

        assert_eq!(put_doc.status, 200);
        assert_eq!(put_doc.body["_index"], "logs-000001");
        assert_eq!(put_doc.body["_id"], "doc-1");
        assert!(put_doc.body["_version"].is_number());
        assert!(put_doc.body["result"].is_string());
        assert!(put_doc.body["_seq_no"].is_number());
        assert!(put_doc.body["_primary_term"].is_number());
    }
}

#[cfg(test)]
mod single_doc_post_live_route_parity_tests {
    use super::*;
    use std::collections::BTreeMap;

    fn single_doc_post_persisted_gateway_state() -> PersistedGatewayState {
        PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-23", 23),
            cluster_state: DevelopmentClusterView {
                cluster_name: "steelsearch-dev".to_string(),
                cluster_uuid: "cluster-uuid".to_string(),
                local_node_id: "node-a".to_string(),
                nodes: vec![],
                coordination: None,
            },
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_uuid": "cluster-uuid",
                "cluster_settings": {
                    "persistent": {},
                    "transient": {}
                },
                "indices": {},
                "templates": {
                    "legacy_index_templates": {},
                    "component_templates": {},
                    "index_templates": {}
                }
            })),
            routing_metadata: None,
            metadata_state: Some(os_node::PersistedGatewayMetadataState {
                cluster_settings: os_node::ClusterSettingsState {
                    persistent: BTreeMap::new(),
                    transient: BTreeMap::new(),
                },
                index_aliases: BTreeMap::new(),
                legacy_index_templates: BTreeMap::new(),
                component_templates: BTreeMap::new(),
                index_templates: BTreeMap::new(),
            }),
            metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                "node-a", "state-23", 23,
            )),
            task_queue_state: None,
        }
    }

    fn build_single_doc_post_live_route_node(
        metadata_path: &std::path::Path,
        gateway_manifest_path: &std::path::Path,
    ) -> SteelNode {
        let persisted = single_doc_post_persisted_gateway_state();
        persist_gateway_state_manifest(gateway_manifest_path, &persisted).unwrap();
        restore_gateway_cluster_metadata_manifest(metadata_path, Some(&persisted)).unwrap();
        let cluster_view = apply_development_coordination_with_persisted_state(
            persisted.cluster_state.clone(),
            Some(persisted.coordination_state.clone()),
            persisted.task_queue_state.clone(),
            Some(gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            metadata_path,
            gateway_manifest_path,
            cluster_view.clone(),
        )
        .unwrap();
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_development_cluster_endpoints(cluster_view);
        node.start_rest();
        node
    }

    #[test]
    fn post_doc_live_route_exposes_bounded_generated_id_write_shape() {
        let metadata_path = unique_test_path("single-doc-post-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("single-doc-post-live-route-gateway.json");
        let node = build_single_doc_post_live_route_node(&metadata_path, &gateway_manifest_path);

        let create_index = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/logs-000001")
                .with_json_body(serde_json::json!({})),
        );
        assert_eq!(create_index.status, 200);

        let post_doc = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/logs-000001/_doc?routing=tenant-a",
            )
            .with_json_body(serde_json::json!({
                "message": "hello"
            })),
        );

        assert_eq!(post_doc.status, 200);
        assert_eq!(post_doc.body["_index"], "logs-000001");
        assert!(post_doc.body["_id"].is_string());
        assert!(post_doc.body["_version"].is_number());
        assert!(post_doc.body["result"].is_string());
        assert!(post_doc.body["_seq_no"].is_number());
        assert!(post_doc.body["_primary_term"].is_number());
    }
}

#[cfg(test)]
mod single_doc_get_live_route_parity_tests {
    use super::*;
    use std::collections::BTreeMap;

    fn single_doc_get_persisted_gateway_state() -> PersistedGatewayState {
        PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-24", 24),
            cluster_state: DevelopmentClusterView {
                cluster_name: "steelsearch-dev".to_string(),
                cluster_uuid: "cluster-uuid".to_string(),
                local_node_id: "node-a".to_string(),
                nodes: vec![],
                coordination: None,
            },
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_uuid": "cluster-uuid",
                "cluster_settings": {
                    "persistent": {},
                    "transient": {}
                },
                "indices": {},
                "templates": {
                    "legacy_index_templates": {},
                    "component_templates": {},
                    "index_templates": {}
                }
            })),
            routing_metadata: None,
            metadata_state: Some(os_node::PersistedGatewayMetadataState {
                cluster_settings: os_node::ClusterSettingsState {
                    persistent: BTreeMap::new(),
                    transient: BTreeMap::new(),
                },
                index_aliases: BTreeMap::new(),
                legacy_index_templates: BTreeMap::new(),
                component_templates: BTreeMap::new(),
                index_templates: BTreeMap::new(),
            }),
            metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                "node-a", "state-24", 24,
            )),
            task_queue_state: None,
        }
    }

    fn build_single_doc_get_live_route_node(
        metadata_path: &std::path::Path,
        gateway_manifest_path: &std::path::Path,
    ) -> SteelNode {
        let persisted = single_doc_get_persisted_gateway_state();
        persist_gateway_state_manifest(gateway_manifest_path, &persisted).unwrap();
        restore_gateway_cluster_metadata_manifest(metadata_path, Some(&persisted)).unwrap();
        let cluster_view = apply_development_coordination_with_persisted_state(
            persisted.cluster_state.clone(),
            Some(persisted.coordination_state.clone()),
            persisted.task_queue_state.clone(),
            Some(gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            metadata_path,
            gateway_manifest_path,
            cluster_view.clone(),
        )
        .unwrap();
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_development_cluster_endpoints(cluster_view);
        node.start_rest();
        node
    }

    #[test]
    fn get_doc_live_route_exposes_bounded_read_shape_and_not_found_envelope() {
        let metadata_path = unique_test_path("single-doc-get-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("single-doc-get-live-route-gateway.json");
        let node = build_single_doc_get_live_route_node(&metadata_path, &gateway_manifest_path);

        let create_index = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/logs-000001")
                .with_json_body(serde_json::json!({})),
        );
        assert_eq!(create_index.status, 200);

        let put_doc = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Put,
                "/logs-000001/_doc/doc-1?routing=tenant-a",
            )
            .with_json_body(serde_json::json!({
                "message": "hello",
                "level": "info",
                "payload": "ignored"
            })),
        );
        assert_eq!(put_doc.status, 200);

        let get_doc = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-000001/_doc/doc-1?_source_includes=message,level&routing=tenant-a&realtime=true",
        ));

        assert_eq!(get_doc.status, 200);
        assert_eq!(get_doc.body["_index"], "logs-000001");
        assert_eq!(get_doc.body["_id"], "doc-1");
        assert_eq!(get_doc.body["found"], true);
        assert!(get_doc.body["_version"].is_number());
        assert!(get_doc.body["_seq_no"].is_number());
        assert!(get_doc.body["_primary_term"].is_number());
        assert_eq!(get_doc.body["_source"]["message"], "hello");
        assert_eq!(get_doc.body["_source"]["level"], "info");
        assert!(get_doc.body["_source"].get("payload").is_none());

        let missing_doc = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/logs-000001/_doc/missing-doc?routing=tenant-a",
        ));

        assert_eq!(missing_doc.status, 404);
        assert_eq!(missing_doc.body["_index"], "logs-000001");
        assert_eq!(missing_doc.body["_id"], "missing-doc");
        assert_eq!(missing_doc.body["found"], false);
    }
}

#[cfg(test)]
mod single_doc_delete_live_route_parity_tests {
    use super::*;
    use std::collections::BTreeMap;

    fn single_doc_delete_persisted_gateway_state() -> PersistedGatewayState {
        PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-26", 26),
            cluster_state: DevelopmentClusterView {
                cluster_name: "steelsearch-dev".to_string(),
                cluster_uuid: "cluster-uuid".to_string(),
                local_node_id: "node-a".to_string(),
                nodes: vec![],
                coordination: None,
            },
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_uuid": "cluster-uuid",
                "cluster_settings": {
                    "persistent": {},
                    "transient": {}
                },
                "indices": {},
                "templates": {
                    "legacy_index_templates": {},
                    "component_templates": {},
                    "index_templates": {}
                }
            })),
            routing_metadata: None,
            metadata_state: Some(os_node::PersistedGatewayMetadataState {
                cluster_settings: os_node::ClusterSettingsState {
                    persistent: BTreeMap::new(),
                    transient: BTreeMap::new(),
                },
                index_aliases: BTreeMap::new(),
                legacy_index_templates: BTreeMap::new(),
                component_templates: BTreeMap::new(),
                index_templates: BTreeMap::new(),
            }),
            metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                "node-a", "state-26", 26,
            )),
            task_queue_state: None,
        }
    }

    fn build_single_doc_delete_live_route_node(
        metadata_path: &std::path::Path,
        gateway_manifest_path: &std::path::Path,
    ) -> SteelNode {
        let persisted = single_doc_delete_persisted_gateway_state();
        persist_gateway_state_manifest(gateway_manifest_path, &persisted).unwrap();
        restore_gateway_cluster_metadata_manifest(metadata_path, Some(&persisted)).unwrap();
        let cluster_view = apply_development_coordination_with_persisted_state(
            persisted.cluster_state.clone(),
            Some(persisted.coordination_state.clone()),
            persisted.task_queue_state.clone(),
            Some(gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            metadata_path,
            gateway_manifest_path,
            cluster_view.clone(),
        )
        .unwrap();
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_development_cluster_endpoints(cluster_view);
        node.start_rest();
        node
    }

    #[test]
    fn delete_doc_live_route_exposes_bounded_delete_shape_and_not_found_result() {
        let metadata_path = unique_test_path("single-doc-delete-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("single-doc-delete-live-route-gateway.json");
        let node =
            build_single_doc_delete_live_route_node(&metadata_path, &gateway_manifest_path);

        let create_index = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/logs-000001")
                .with_json_body(serde_json::json!({})),
        );
        assert_eq!(create_index.status, 200);

        let put_doc = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Put,
                "/logs-000001/_doc/doc-1?routing=tenant-a",
            )
            .with_json_body(serde_json::json!({
                "message": "hello"
            })),
        );
        assert_eq!(put_doc.status, 200);

        let delete_doc = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Delete,
            "/logs-000001/_doc/doc-1?routing=tenant-a&refresh=wait_for",
        ));

        assert_eq!(delete_doc.status, 200);
        assert_eq!(delete_doc.body["_index"], "logs-000001");
        assert_eq!(delete_doc.body["_id"], "doc-1");
        assert_eq!(delete_doc.body["result"], "deleted");
        assert!(delete_doc.body["_version"].is_number());
        assert!(delete_doc.body["_seq_no"].is_number());
        assert!(delete_doc.body["_primary_term"].is_number());

        let missing_delete = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Delete,
            "/logs-000001/_doc/missing-doc?routing=tenant-a",
        ));

        assert_eq!(missing_delete.status, 404);
        assert_eq!(missing_delete.body["_index"], "logs-000001");
        assert_eq!(missing_delete.body["_id"], "missing-doc");
        assert_eq!(missing_delete.body["result"], "not_found");
    }
}

#[cfg(test)]
mod single_doc_update_live_route_parity_tests {
    use super::*;
    use std::collections::BTreeMap;

    fn single_doc_update_persisted_gateway_state() -> PersistedGatewayState {
        PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-28", 28),
            cluster_state: DevelopmentClusterView {
                cluster_name: "steelsearch-dev".to_string(),
                cluster_uuid: "cluster-uuid".to_string(),
                local_node_id: "node-a".to_string(),
                nodes: vec![],
                coordination: None,
            },
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_uuid": "cluster-uuid",
                "cluster_settings": {
                    "persistent": {},
                    "transient": {}
                },
                "indices": {},
                "templates": {
                    "legacy_index_templates": {},
                    "component_templates": {},
                    "index_templates": {}
                }
            })),
            routing_metadata: None,
            metadata_state: Some(os_node::PersistedGatewayMetadataState {
                cluster_settings: os_node::ClusterSettingsState {
                    persistent: BTreeMap::new(),
                    transient: BTreeMap::new(),
                },
                index_aliases: BTreeMap::new(),
                legacy_index_templates: BTreeMap::new(),
                component_templates: BTreeMap::new(),
                index_templates: BTreeMap::new(),
            }),
            metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                "node-a", "state-28", 28,
            )),
            task_queue_state: None,
        }
    }

    fn build_single_doc_update_live_route_node(
        metadata_path: &std::path::Path,
        gateway_manifest_path: &std::path::Path,
    ) -> SteelNode {
        let persisted = single_doc_update_persisted_gateway_state();
        persist_gateway_state_manifest(gateway_manifest_path, &persisted).unwrap();
        restore_gateway_cluster_metadata_manifest(metadata_path, Some(&persisted)).unwrap();
        let cluster_view = apply_development_coordination_with_persisted_state(
            persisted.cluster_state.clone(),
            Some(persisted.coordination_state.clone()),
            persisted.task_queue_state.clone(),
            Some(gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            metadata_path,
            gateway_manifest_path,
            cluster_view.clone(),
        )
        .unwrap();
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_development_cluster_endpoints(cluster_view);
        node.start_rest();
        node
    }

    #[test]
    fn update_doc_live_route_exposes_bounded_update_and_upsert_shapes() {
        let metadata_path = unique_test_path("single-doc-update-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("single-doc-update-live-route-gateway.json");
        let node =
            build_single_doc_update_live_route_node(&metadata_path, &gateway_manifest_path);

        let create_index = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/logs-000001")
                .with_json_body(serde_json::json!({})),
        );
        assert_eq!(create_index.status, 200);

        let put_doc = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Put,
                "/logs-000001/_doc/doc-1?routing=tenant-a",
            )
            .with_json_body(serde_json::json!({
                "message": "hello"
            })),
        );
        assert_eq!(put_doc.status, 200);

        let update_doc = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/logs-000001/_update/doc-1?routing=tenant-a&refresh=wait_for",
            )
            .with_json_body(serde_json::json!({
                "doc": {
                    "level": "info"
                },
                "retry_on_conflict": 2
            })),
        );

        assert_eq!(update_doc.status, 200);
        assert_eq!(update_doc.body["_index"], "logs-000001");
        assert_eq!(update_doc.body["_id"], "doc-1");
        assert_eq!(update_doc.body["result"], "updated");
        assert!(update_doc.body["_version"].is_number());
        assert!(update_doc.body["_seq_no"].is_number());
        assert!(update_doc.body["_primary_term"].is_number());

        let upsert_doc = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/logs-000001/_update/doc-2?routing=tenant-a",
            )
            .with_json_body(serde_json::json!({
                "doc": {
                    "message": "seed"
                },
                "doc_as_upsert": true
            })),
        );

        assert_eq!(upsert_doc.status, 200);
        assert_eq!(upsert_doc.body["_index"], "logs-000001");
        assert_eq!(upsert_doc.body["_id"], "doc-2");
        assert_eq!(upsert_doc.body["result"], "created");
        assert!(upsert_doc.body["_version"].is_number());
        assert!(upsert_doc.body["_seq_no"].is_number());
        assert!(upsert_doc.body["_primary_term"].is_number());
    }
}

#[cfg(test)]
mod snapshot_repository_live_route_parity_tests {
    use super::*;

    pub(super) fn build_snapshot_live_route_node(
        metadata_path: &std::path::Path,
        gateway_manifest_path: &std::path::Path,
    ) -> SteelNode {
        let persisted =
            crate::single_doc_put_live_route_parity_tests::single_doc_put_persisted_gateway_state();
        persist_gateway_state_manifest(gateway_manifest_path, &persisted).unwrap();
        restore_gateway_cluster_metadata_manifest(metadata_path, Some(&persisted)).unwrap();
        let cluster_view = apply_development_coordination_with_persisted_state(
            persisted.cluster_state.clone(),
            Some(persisted.coordination_state.clone()),
            persisted.task_queue_state.clone(),
            Some(gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            metadata_path,
            gateway_manifest_path,
            cluster_view.clone(),
        )
        .unwrap();
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_development_cluster_endpoints(cluster_view);
        node.start_rest();
        node
    }

    #[test]
    fn snapshot_repository_local_activation_harness_exposes_bounded_readback_mutation_and_verify() {
        let readback =
            os_node::snapshot_repository_route_registration::run_snapshot_repository_local_route_activation(
                "GET",
                "/_snapshot/{repository}",
                &serde_json::json!({
                    "repo-a": {
                        "type": "fs",
                        "settings": {
                            "location": "/tmp/repo-a"
                        },
                        "uuid": "extra"
                    }
                }),
                Some("repo-a"),
                &serde_json::json!({}),
                &serde_json::json!({}),
            )
            .expect("snapshot repository readback");
        let mutation =
            os_node::snapshot_repository_route_registration::run_snapshot_repository_local_route_activation(
                "PUT",
                "/_snapshot/{repository}",
                &serde_json::json!({}),
                Some("repo-a"),
                &serde_json::json!({
                    "type": "fs",
                    "settings": {
                        "location": "/tmp/repo-a"
                    },
                    "verify": true
                }),
                &serde_json::json!({}),
            )
            .expect("snapshot repository mutation");
        let verify =
            os_node::snapshot_repository_route_registration::run_snapshot_repository_local_route_activation(
                "POST",
                "/_snapshot/{repository}/_verify",
                &serde_json::json!({}),
                Some("repo-a"),
                &serde_json::json!({}),
                &serde_json::json!({
                    "nodes": {
                        "node-a": {
                            "name": "node-a"
                        }
                    },
                    "repository": "repo-a"
                }),
            )
            .expect("snapshot repository verify");

        assert_eq!(readback["repo-a"]["type"], "fs");
        assert!(readback["repo-a"].get("uuid").is_none());
        assert_eq!(mutation["acknowledged"], true);
        assert!(verify.get("nodes").is_some());
        assert!(verify.get("repository").is_none());
    }

    #[test]
    fn snapshot_repository_live_route_exposes_bounded_readback_mutation_and_verify() {
        let metadata_path = unique_test_path("snapshot-repository-live-route-metadata.json");
        let gateway_manifest_path =
            unique_test_path("snapshot-repository-live-route-gateway.json");
        let node = build_snapshot_live_route_node(&metadata_path, &gateway_manifest_path);

        let put = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/_snapshot/repo-a")
                .with_json_body(serde_json::json!({
                    "type": "fs",
                    "settings": {
                        "location": "/tmp/repo-a"
                    },
                    "uuid": "ignored"
                })),
        );
        let get = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_snapshot/repo-a",
        ));
        let verify = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Post,
            "/_snapshot/repo-a/_verify",
        ));

        assert_eq!(put.status, 200);
        assert_eq!(put.body["acknowledged"], true);
        assert_eq!(get.status, 200);
        assert_eq!(get.body["repo-a"]["type"], "fs");
        assert!(get.body["repo-a"].get("uuid").is_none());
        assert_eq!(verify.status, 200);
        assert!(verify.body.get("nodes").is_some());
        assert!(verify.body.get("repository").is_none());
    }
}

#[cfg(test)]
mod snapshot_lifecycle_live_route_parity_tests {
    use super::*;

    #[test]
    fn snapshot_lifecycle_local_activation_harness_exposes_bounded_create_readback_status_and_restore() {
        let create =
            os_node::snapshot_lifecycle_route_registration::run_snapshot_lifecycle_local_route_activation(
                "PUT",
                "/_snapshot/{repository}/{snapshot}",
                &serde_json::json!({
                    "indices": ["logs-000001"],
                    "include_global_state": false,
                    "metadata": {
                        "owner": "tests"
                    }
                }),
            )
            .expect("snapshot create");
        let readback =
            os_node::snapshot_lifecycle_route_registration::run_snapshot_lifecycle_local_route_activation(
                "GET",
                "/_snapshot/{repository}/{snapshot}",
                &serde_json::json!({
                    "snapshot": "snapshot-a",
                    "uuid": "snapshot-a-uuid",
                    "state": "SUCCESS",
                    "indices": ["logs-000001"],
                    "feature_states": []
                }),
            )
            .expect("snapshot readback");
        let status =
            os_node::snapshot_lifecycle_route_registration::run_snapshot_lifecycle_local_route_activation(
                "GET",
                "/_snapshot/{repository}/{snapshot}/_status",
                &serde_json::json!({
                    "snapshot": "snapshot-a",
                    "repository": "repo-a",
                    "state": "SUCCESS",
                    "shards_stats": {
                        "total": 1,
                        "successful": 1,
                        "failed": 0
                    },
                    "stats": {}
                }),
            )
            .expect("snapshot status");
        let restore =
            os_node::snapshot_lifecycle_route_registration::run_snapshot_lifecycle_local_route_activation(
                "POST",
                "/_snapshot/{repository}/{snapshot}/_restore",
                &serde_json::json!({
                    "indices": ["logs-000001"],
                    "rename_pattern": "logs-(.+)",
                    "rename_replacement": "restored-$1",
                    "ignore_unavailable": true
                }),
            )
            .expect("snapshot restore");

        assert_eq!(create["accepted"], true);
        assert_eq!(readback["snapshots"][0]["snapshot"], "snapshot-a");
        assert!(readback["snapshots"][0].get("feature_states").is_none());
        assert_eq!(status["snapshots"][0]["repository"], "repo-a");
        assert!(status["snapshots"][0].get("stats").is_none());
        assert_eq!(restore["accepted"], true);
    }

    #[test]
    fn snapshot_lifecycle_live_route_exposes_bounded_create_readback_status_and_restore() {
        let metadata_path = unique_test_path("snapshot-lifecycle-live-route-metadata.json");
        let gateway_manifest_path =
            unique_test_path("snapshot-lifecycle-live-route-gateway.json");
        let node = snapshot_repository_live_route_parity_tests::build_snapshot_live_route_node(
            &metadata_path,
            &gateway_manifest_path,
        );

        let register = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/_snapshot/repo-a")
                .with_json_body(serde_json::json!({
                    "type": "fs",
                    "settings": {
                        "location": "/tmp/repo-a"
                    }
                })),
        );
        assert_eq!(register.status, 200);

        let create = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Put,
                "/_snapshot/repo-a/snapshot-a",
            )
            .with_json_body(serde_json::json!({
                "indices": ["logs-000001"],
                "include_global_state": false,
                "metadata": {
                    "owner": "tests"
                }
            })),
        );
        let readback = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_snapshot/repo-a/snapshot-a",
        ));
        let status = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_snapshot/repo-a/snapshot-a/_status",
        ));
        let restore = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/_snapshot/repo-a/snapshot-a/_restore",
            )
            .with_json_body(serde_json::json!({
                "indices": ["logs-000001"],
                "rename_pattern": "logs-(.+)",
                "rename_replacement": "restored-$1"
            })),
        );

        assert_eq!(create.status, 200);
        assert_eq!(create.body["accepted"], true);
        assert_eq!(readback.status, 200);
        assert_eq!(readback.body["snapshots"][0]["snapshot"], "snapshot-a");
        assert!(readback.body["snapshots"][0].get("feature_states").is_none());
        assert_eq!(status.status, 200);
        assert_eq!(status.body["snapshots"][0]["repository"], "repo-a");
        assert!(status.body["snapshots"][0].get("stats").is_none());
        assert_eq!(restore.status, 200);
        assert_eq!(restore.body["accepted"], true);
    }
}

#[cfg(test)]
mod snapshot_cleanup_live_route_parity_tests {
    use super::*;

    #[test]
    fn snapshot_cleanup_local_activation_harness_exposes_bounded_delete_and_cleanup_shapes() {
        let delete =
            os_node::snapshot_cleanup_route_registration::run_snapshot_cleanup_local_route_activation(
                "DELETE",
                "/_snapshot/{repository}/{snapshot}",
                &serde_json::json!({
                    "snapshot": "snapshot-a",
                    "repository": "repo-a",
                    "start_time": "ignored"
                }),
            )
            .expect("snapshot delete");
        let cleanup =
            os_node::snapshot_cleanup_route_registration::run_snapshot_cleanup_local_route_activation(
                "POST",
                "/_snapshot/{repository}/_cleanup",
                &serde_json::json!({
                    "deleted_bytes": 64,
                    "deleted_blobs": 1,
                    "cleanup_time_in_millis": 10
                }),
            )
            .expect("snapshot cleanup");

        assert_eq!(delete["acknowledged"], true);
        assert_eq!(delete["snapshot"]["snapshot"], "snapshot-a");
        assert!(delete["snapshot"].get("start_time").is_none());
        assert_eq!(cleanup["results"]["deleted_bytes"], 64);
        assert_eq!(cleanup["results"]["deleted_blobs"], 1);
        assert!(cleanup["results"].get("cleanup_time_in_millis").is_none());
    }

    #[test]
    fn snapshot_cleanup_live_route_exposes_bounded_delete_and_cleanup_shapes() {
        let metadata_path = unique_test_path("snapshot-cleanup-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("snapshot-cleanup-live-route-gateway.json");
        let node = snapshot_repository_live_route_parity_tests::build_snapshot_live_route_node(
            &metadata_path,
            &gateway_manifest_path,
        );

        let register = node.handle_rest_request(
            os_rest::RestRequest::new(os_rest::RestMethod::Put, "/_snapshot/repo-a")
                .with_json_body(serde_json::json!({
                    "type": "fs",
                    "settings": {
                        "location": "/tmp/repo-a"
                    }
                })),
        );
        assert_eq!(register.status, 200);
        let create = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Put,
                "/_snapshot/repo-a/snapshot-a",
            )
            .with_json_body(serde_json::json!({
                "indices": ["logs-000001"]
            })),
        );
        assert_eq!(create.status, 200);

        let delete = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Delete,
            "/_snapshot/repo-a/snapshot-a",
        ));
        let cleanup = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Post,
            "/_snapshot/repo-a/_cleanup",
        ));

        assert_eq!(delete.status, 200);
        assert_eq!(delete.body["acknowledged"], true);
        assert_eq!(delete.body["snapshot"]["snapshot"], "snapshot-a");
        assert!(delete.body["snapshot"].get("start_time").is_none());
        assert_eq!(cleanup.status, 200);
        assert_eq!(cleanup.body["results"]["deleted_bytes"], 0);
        assert_eq!(cleanup.body["results"]["deleted_blobs"], 0);
    }
}

#[cfg(test)]
mod vector_live_route_parity_tests {
    use super::*;

    fn build_vector_live_route_node(
        metadata_path: &std::path::Path,
        gateway_manifest_path: &std::path::Path,
    ) -> SteelNode {
        let persisted =
            crate::single_doc_put_live_route_parity_tests::single_doc_put_persisted_gateway_state();
        persist_gateway_state_manifest(gateway_manifest_path, &persisted).unwrap();
        restore_gateway_cluster_metadata_manifest(metadata_path, Some(&persisted)).unwrap();
        let cluster_view = apply_development_coordination_with_persisted_state(
            persisted.cluster_state.clone(),
            Some(persisted.coordination_state.clone()),
            persisted.task_queue_state.clone(),
            Some(gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            metadata_path,
            gateway_manifest_path,
            cluster_view.clone(),
        )
        .unwrap();
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_development_cluster_endpoints(cluster_view);
        node.start_rest();
        node
    }

    #[test]
    fn vector_live_route_supports_knn_hybrid_and_operational_shapes() {
        let metadata_path = unique_test_path("vector-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("vector-live-route-gateway.json");
        let node = build_vector_live_route_node(&metadata_path, &gateway_manifest_path);

        let create_index = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Put,
                "/vector-search-compat-000001",
            )
            .with_json_body(serde_json::json!({
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "knn": true
                    }
                },
                "mappings": {
                    "properties": {
                        "title": { "type": "text" },
                        "tenant": { "type": "keyword" },
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 3,
                            "data_type": "float",
                            "mode": "in_memory",
                            "compression_level": "1x",
                            "doc_values": true,
                            "store": false,
                            "_meta": {
                                "owner": "vector-live-route"
                            },
                            "method": {
                                "name": "hnsw",
                                "engine": "lucene"
                            }
                        }
                    }
                }
            })),
        );
        assert_eq!(create_index.status, 200);

        for (doc_id, source) in [
            (
                "doc-1",
                serde_json::json!({
                    "title": "alpha vector",
                    "tenant": "tenant-a",
                    "embedding": [0.9, 0.1, 0.0]
                }),
            ),
            (
                "doc-2",
                serde_json::json!({
                    "title": "beta vector",
                    "tenant": "tenant-a",
                    "embedding": [0.1, 0.9, 0.0]
                }),
            ),
        ] {
            let put = node.handle_rest_request(
                os_rest::RestRequest::new(
                    os_rest::RestMethod::Put,
                    &format!("/vector-search-compat-000001/_doc/{doc_id}?refresh=wait_for"),
                )
                .with_json_body(source),
            );
            assert_eq!(put.status, 201);
        }

        let knn = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/vector-search-compat-000001/_search",
            )
            .with_json_body(serde_json::json!({
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": [1.0, 0.0, 0.0],
                            "k": 1
                        }
                    }
                },
                "track_total_hits": true
            })),
        );
        assert_eq!(knn.status, 200);
        assert_eq!(knn.body["hits"]["total"]["value"], 2);
        assert_eq!(knn.body["hits"]["hits"][0]["_id"], "doc-1");

        let hybrid = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/vector-search-compat-000001/_search",
            )
            .with_json_body(serde_json::json!({
                "query": {
                    "bool": {
                        "must": [
                            {
                                "term": {
                                    "tenant": "tenant-a"
                                }
                            },
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": [0.0, 1.0, 0.0],
                                        "k": 2
                                    }
                                }
                            }
                        ]
                    }
                },
                "track_total_hits": true
            })),
        );
        assert_eq!(hybrid.status, 200);
        assert_eq!(hybrid.body["hits"]["total"]["value"], 2);
        assert_eq!(hybrid.body["hits"]["hits"][0]["_id"], "doc-2");
        assert_eq!(hybrid.body["hits"]["hits"][1]["_id"], "doc-1");

        let filtered_knn = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/vector-search-compat-000001/_search",
            )
            .with_json_body(serde_json::json!({
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": [1.0, 0.0, 0.0],
                            "k": 2,
                            "filter": {
                                "term": {
                                    "title": "alpha vector"
                                }
                            }
                        }
                    }
                },
                "track_total_hits": true
            })),
        );
        assert_eq!(filtered_knn.status, 200);
        assert_eq!(filtered_knn.body["hits"]["total"]["value"], 1);
        assert_eq!(filtered_knn.body["hits"]["hits"][0]["_id"], "doc-1");

        let ignore_unmapped = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/vector-search-compat-000001/_search",
            )
            .with_json_body(serde_json::json!({
                "query": {
                    "knn": {
                        "missing_embedding": {
                            "vector": [1.0, 0.0, 0.0],
                            "k": 1,
                            "ignore_unmapped": true
                        }
                    }
                },
                "track_total_hits": true
            })),
        );
        assert_eq!(ignore_unmapped.status, 200);
        assert_eq!(ignore_unmapped.body["hits"]["total"]["value"], 0);

        let radial = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/vector-search-compat-000001/_search",
            )
            .with_json_body(serde_json::json!({
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": [1.0, 0.0, 0.0],
                            "max_distance": 0.5
                        }
                    }
                },
                "track_total_hits": true
            })),
        );
        assert_eq!(radial.status, 200);
        assert_eq!(radial.body["hits"]["total"]["value"], 1);
        assert_eq!(radial.body["hits"]["hits"][0]["_id"], "doc-1");

        let method_parameters = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/vector-search-compat-000001/_search",
            )
            .with_json_body(serde_json::json!({
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": [0.0, 1.0, 0.0],
                            "k": 1,
                            "expand_nested": false,
                            "method_parameters": {
                                "ef_search": 32
                            }
                        }
                    }
                },
                "track_total_hits": true
            })),
        );
        assert_eq!(method_parameters.status, 200);
        assert_eq!(method_parameters.body["hits"]["total"]["value"], 2);
        assert_eq!(method_parameters.body["hits"]["hits"][0]["_id"], "doc-2");

        let hybrid_should = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/vector-search-compat-000001/_search",
            )
            .with_json_body(serde_json::json!({
                "query": {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "title": "alpha"
                                }
                            },
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": [1.0, 0.0, 0.0],
                                        "k": 2
                                    }
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                },
                "track_total_hits": true
            })),
        );
        assert_eq!(hybrid_should.status, 200);
        assert_eq!(hybrid_should.body["hits"]["total"]["value"], 2);
        assert_eq!(hybrid_should.body["hits"]["hits"][0]["_id"], "doc-1");

        let hybrid_minimum_should_match = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/vector-search-compat-000001/_search",
            )
            .with_json_body(serde_json::json!({
                "query": {
                    "bool": {
                        "should": [
                            {
                                "term": {
                                    "tenant": "tenant-a"
                                }
                            },
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": [1.0, 0.0, 0.0],
                                        "max_distance": 0.5
                                    }
                                }
                            }
                        ],
                        "minimum_should_match": 2
                    }
                },
                "track_total_hits": true
            })),
        );
        assert_eq!(hybrid_minimum_should_match.status, 200);
        assert_eq!(hybrid_minimum_should_match.body["hits"]["total"]["value"], 1);
        assert_eq!(hybrid_minimum_should_match.body["hits"]["hits"][0]["_id"], "doc-1");

        let unsupported = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/vector-search-compat-000001/_search",
            )
            .with_json_body(serde_json::json!({
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": [1.0, 0.0, 0.0],
                            "k": 1,
                            "bogus_parameter": true
                        }
                    }
                }
            })),
        );
        assert_eq!(unsupported.status, 400);
        assert_eq!(unsupported.body["error"]["type"], "illegal_argument_exception");

        let warmup = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/_plugins/_knn/warmup/vector-search-compat-000001",
            )
            .with_json_body(serde_json::json!({
                "vector_segment_count": 2
            })),
        );
        assert_eq!(warmup.status, 200);
        let stats = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_plugins/_knn/stats",
        ));
        assert_eq!(stats.status, 200);
        let clear_cache = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Post,
            "/_plugins/_knn/clear_cache/vector-search-compat-000001",
        ));
        assert_eq!(clear_cache.status, 200);

        let train_model = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/_plugins/_knn/models/_train",
            )
            .with_json_body(serde_json::json!({
                "training_index": "vector-search-compat-000001",
                "dimension": 3,
                "description": "vector test model",
                "method": {
                    "name": "hnsw",
                    "engine": "lucene"
                }
            })),
        );
        assert_eq!(train_model.status, 200);
        let model_id = train_model.body["model_id"].as_str().unwrap_or("");
        assert!(!model_id.is_empty());

        let get_model = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            &format!("/_plugins/_knn/models/{model_id}"),
        ));
        assert_eq!(get_model.status, 200);
        assert_eq!(get_model.body["dimension"], 3);
        assert_eq!(get_model.body["method"]["engine"], "lucene");

        let search_model = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/_plugins/_knn/models/_search",
            )
            .with_json_body(serde_json::json!({
                "query": {
                    "term": {
                        "model_id": model_id
                    }
                }
            })),
        );
        assert_eq!(search_model.status, 200);
        assert_eq!(search_model.body["hits"]["total"]["value"], 1);
        assert_eq!(search_model.body["hits"]["hits"][0]["_id"], model_id);

        let stats_after_train = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_plugins/_knn/stats",
        ));
        assert_eq!(stats_after_train.status, 200);
        assert_eq!(stats_after_train.body["nodes"]["local"]["model_count"], 1);
        assert_eq!(stats_after_train.body["nodes"]["local"]["training_requests"], 1);

        let delete_model = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Delete,
            &format!("/_plugins/_knn/models/{model_id}"),
        ));
        assert_eq!(delete_model.status, 200);
        assert_eq!(delete_model.body["result"], "deleted");

        let register_ml_model = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/_plugins/_ml/models/_register",
            )
            .with_json_body(serde_json::json!({
                "name": "compat-text-embedding",
                "function_name": "text_embedding",
                "dimension": 3
            })),
        );
        assert_eq!(register_ml_model.status, 200);
        let ml_model_id = register_ml_model.body["model_id"].as_str().unwrap_or("");
        assert!(!ml_model_id.is_empty());

        let get_ml_model = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            &format!("/_plugins/_ml/models/{ml_model_id}"),
        ));
        assert_eq!(get_ml_model.status, 200);
        assert_eq!(get_ml_model.body["dimension"], 3);
        assert_eq!(get_ml_model.body["deployed"], false);

        let deploy_ml_model = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Post,
            &format!("/_plugins/_ml/models/{ml_model_id}/_deploy"),
        ));
        assert_eq!(deploy_ml_model.status, 200);
        assert_eq!(deploy_ml_model.body["deployed"], true);

        let predict_ml_model = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                &format!("/_plugins/_ml/models/{ml_model_id}/_predict"),
            )
            .with_json_body(serde_json::json!({
                "text_docs": ["alpha beta"]
            })),
        );
        assert_eq!(predict_ml_model.status, 200);
        assert_eq!(predict_ml_model.body["inference_results"][0]["model_id"], ml_model_id);

        let search_ml_model = node.handle_rest_request(
            os_rest::RestRequest::new(
                os_rest::RestMethod::Post,
                "/_plugins/_ml/models/_search",
            )
            .with_json_body(serde_json::json!({
                "query": { "term": { "model_id": ml_model_id } }
            })),
        );
        assert_eq!(search_ml_model.status, 200);
        assert_eq!(search_ml_model.body["hits"]["total"]["value"], 1);

        let undeploy_ml_model = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Post,
            &format!("/_plugins/_ml/models/{ml_model_id}/_undeploy"),
        ));
        assert_eq!(undeploy_ml_model.status, 200);
        assert_eq!(undeploy_ml_model.body["deployed"], false);
    }
}

#[cfg(test)]
mod allocation_explain_live_route_parity_tests {
    use super::*;
    use std::collections::BTreeMap;

    fn allocation_explain_persisted_gateway_state() -> PersistedGatewayState {
        PersistedGatewayState {
            coordination_state: committed_gateway_coordination_state("node-a", "state-19", 19),
            cluster_state: DevelopmentClusterView {
                cluster_name: "steelsearch-dev".to_string(),
                cluster_uuid: "cluster-uuid".to_string(),
                local_node_id: "node-a".to_string(),
                nodes: vec![],
                coordination: None,
            },
            cluster_metadata_manifest: Some(serde_json::json!({
                "cluster_uuid": "cluster-uuid",
                "cluster_settings": {
                    "persistent": {},
                    "transient": {}
                },
                "indices": {},
                "templates": {
                    "legacy_index_templates": {},
                    "component_templates": {},
                    "index_templates": {}
                }
            })),
            routing_metadata: None,
            metadata_state: Some(os_node::PersistedGatewayMetadataState {
                cluster_settings: os_node::ClusterSettingsState {
                    persistent: BTreeMap::new(),
                    transient: BTreeMap::new(),
                },
                index_aliases: BTreeMap::new(),
                legacy_index_templates: BTreeMap::new(),
                component_templates: BTreeMap::new(),
                index_templates: BTreeMap::new(),
            }),
            metadata_commit_state: Some(committed_gateway_metadata_commit_state(
                "node-a", "state-19", 19,
            )),
            task_queue_state: None,
        }
    }

    fn build_allocation_explain_live_route_node(
        metadata_path: &std::path::Path,
        gateway_manifest_path: &std::path::Path,
    ) -> SteelNode {
        let persisted = allocation_explain_persisted_gateway_state();
        persist_gateway_state_manifest(gateway_manifest_path, &persisted).unwrap();
        restore_gateway_cluster_metadata_manifest(metadata_path, Some(&persisted)).unwrap();
        let cluster_view = apply_development_coordination_with_persisted_state(
            persisted.cluster_state.clone(),
            Some(persisted.coordination_state.clone()),
            persisted.task_queue_state.clone(),
            Some(gateway_manifest_path),
        );

        let mut node = SteelNode::new(NodeInfo {
            name: "node-a".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        })
        .with_gateway_backed_development_metadata_store(
            metadata_path,
            gateway_manifest_path,
            cluster_view.clone(),
        )
        .unwrap();
        node.register_default_dev_endpoints("steelsearch-dev".to_string(), "cluster-uuid");
        node.register_development_cluster_endpoints(cluster_view);
        node.start_rest();
        node
    }

    #[test]
    fn cluster_allocation_explain_live_route_exposes_bounded_shape() {
        let metadata_path = unique_test_path("allocation-explain-live-route-metadata.json");
        let gateway_manifest_path = unique_test_path("allocation-explain-live-route-gateway.json");
        let node =
            build_allocation_explain_live_route_node(&metadata_path, &gateway_manifest_path);

        let response = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_cluster/allocation/explain",
        ));
        assert_eq!(response.status, 200);
        assert!(response.body.get("current_state").is_some());
        assert!(response.body.get("node_allocation_decisions").is_some());
    }
}
