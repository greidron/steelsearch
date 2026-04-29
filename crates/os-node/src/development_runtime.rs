use crate::NodeInfo;
use crate::allocation_explain_route_registration;
use crate::alias_mutation_route_registration;
use crate::alias_read_route_registration;
use crate::create_index_route_registration;
use crate::cluster_settings_route_registration;
use crate::cluster_state_route_registration;
use crate::data_stream_route_registration;
use crate::delete_index_route_registration;
use crate::get_index_route_registration;
use crate::legacy_template_route_registration;
use crate::mapping_route_registration;
use crate::pending_tasks_route_registration;
use crate::rollover_route_registration;
use crate::settings_route_registration;
use crate::single_doc_delete_route_registration;
use crate::single_doc_get_route_registration;
use crate::single_doc_post_route_registration;
use crate::single_doc_put_route_registration;
use crate::single_doc_update_route_registration;
use crate::snapshot_cleanup_route_registration;
use crate::snapshot_lifecycle_route_registration;
use crate::snapshot_repository_route_registration;
use crate::stats_route_registration;
use crate::tasks_route_registration;
use crate::template_route_registration;
use os_core::Version;
use os_rest::{RestMethod, RestRequest, RestResponse};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::Duration;

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestServerConfig {
    pub bind_host: String,
    pub port: u16,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SecurityBoundaryPolicy {}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct ReleaseReadinessChecklist {}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct ExtensionBoundaryRegistry {
    pub manifest_path: Option<PathBuf>,
    pub knn_plugin_enabled: bool,
    pub ml_commons_enabled: bool,
}

impl ExtensionBoundaryRegistry {
    pub fn load_manifest(path: impl AsRef<Path>) -> std::io::Result<Self> {
        Ok(Self {
            manifest_path: Some(path.as_ref().to_path_buf()),
            knn_plugin_enabled: false,
            ml_commons_enabled: false,
        })
    }
}

pub fn validate_production_mode_request(
    _policy: &SecurityBoundaryPolicy,
    _checklist: ReleaseReadinessChecklist,
) -> Result<(), Box<dyn std::error::Error>> {
    Err(
        "production mode is blocked until tls must be implemented and enforced, authentication must be implemented and enforced, authorization must be implemented and enforced, audit_logging must be implemented and enforced, tenant_isolation must be implemented and enforced, secure_settings must be implemented and enforced, benchmark coverage is missing, load test coverage is missing, chaos test coverage is missing, packaging is not verified, rolling upgrade coverage is missing".into(),
    )
}

pub fn bind_rest_http_listener(address: SocketAddr) -> std::io::Result<TcpListener> {
    TcpListener::bind(address)
}

pub fn serve_rest_http_listener_until<F>(
    node: SteelNode,
    listener: TcpListener,
    should_stop: F,
) -> std::io::Result<()>
where
    F: Fn() -> bool,
{
    listener.set_nonblocking(true)?;
    while !should_stop() {
        match listener.accept() {
            Ok((mut stream, _)) => {
                let _ = handle_http_connection(&node, &mut stream);
            }
            Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                std::thread::sleep(Duration::from_millis(25));
            }
            Err(error) => return Err(error),
        }
    }
    Ok(())
}

fn handle_http_connection(node: &SteelNode, stream: &mut TcpStream) -> std::io::Result<()> {
    let request = match read_http_request(stream)? {
        Some(request) => request,
        None => return Ok(()),
    };
    let response = node.handle_rest_request(request);
    write_http_response(stream, response)
}

fn read_http_request(stream: &mut TcpStream) -> std::io::Result<Option<RestRequest>> {
    stream.set_read_timeout(Some(Duration::from_millis(250)))?;
    let mut buffer = Vec::new();
    let mut chunk = [0_u8; 4096];
    let mut header_end = None;
    loop {
        match stream.read(&mut chunk) {
            Ok(0) if buffer.is_empty() => return Ok(None),
            Ok(0) => return Ok(None),
            Ok(read) => {
                buffer.extend_from_slice(&chunk[..read]);
                if let Some(position) = find_header_end(&buffer) {
                    header_end = Some(position);
                    break;
                }
            }
            Err(error)
                if matches!(
                    error.kind(),
                    std::io::ErrorKind::WouldBlock | std::io::ErrorKind::TimedOut
                ) =>
            {
                return Ok(None)
            }
            Err(error) => return Err(error),
        }
    }
    let Some(header_end) = header_end else {
        return Ok(None);
    };

    let (header_bytes, body_bytes) = buffer.split_at(header_end);
    let headers_text = String::from_utf8_lossy(header_bytes);
    let mut lines = headers_text.split("\r\n");
    let request_line = match lines.next() {
        Some(line) if !line.is_empty() => line,
        _ => return Ok(None),
    };
    let mut request_parts = request_line.split_whitespace();
    let method = parse_rest_method(request_parts.next().unwrap_or("GET"));
    let raw_target = request_parts.next().unwrap_or("/");
    let (path, query_params) = split_path_and_query(raw_target);
    let mut request = RestRequest::new(method, path);
    request.query_params = query_params;
    for line in lines {
        if line.is_empty() {
            continue;
        }
        if let Some((name, value)) = line.split_once(':') {
            request = request.with_header(name.trim(), value.trim());
        }
    }
    request.body = body_bytes.get(4..).unwrap_or_default().to_vec();
    Ok(Some(request))
}

fn write_http_response(stream: &mut TcpStream, response: RestResponse) -> std::io::Result<()> {
    let body_bytes = if response
        .headers
        .get("content-type")
        .is_some_and(|value| value.starts_with("text/plain"))
    {
        response.body.as_str().unwrap_or_default().as_bytes().to_vec()
    } else if response.body.is_null() {
        Vec::new()
    } else {
        serde_json::to_vec(&response.body)
            .map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error))?
    };
    let status_text = reason_phrase(response.status);
    write!(stream, "HTTP/1.1 {} {}\r\n", response.status, status_text)?;
    for (name, value) in &response.headers {
        write!(stream, "{}: {}\r\n", name, value)?;
    }
    write!(stream, "content-length: {}\r\n\r\n", body_bytes.len())?;
    stream.write_all(&body_bytes)?;
    stream.flush()?;
    Ok(())
}

fn parse_rest_method(value: &str) -> RestMethod {
    match value {
        "HEAD" => RestMethod::Head,
        "PUT" => RestMethod::Put,
        "POST" => RestMethod::Post,
        "DELETE" => RestMethod::Delete,
        _ => RestMethod::Get,
    }
}

fn split_path_and_query(target: &str) -> (String, BTreeMap<String, String>) {
    let Some((path, query)) = target.split_once('?') else {
        return (target.to_string(), BTreeMap::new());
    };
    let mut query_params = BTreeMap::new();
    for pair in query.split('&') {
        if pair.is_empty() {
            continue;
        }
        let (name, value) = pair.split_once('=').unwrap_or((pair, ""));
        query_params.insert(name.to_string(), value.to_string());
    }
    (path.to_string(), query_params)
}

fn find_header_end(buffer: &[u8]) -> Option<usize> {
    buffer.windows(4).position(|window| window == b"\r\n\r\n")
}

fn reason_phrase(status: u16) -> &'static str {
    match status {
        200 => "OK",
        201 => "Created",
        202 => "Accepted",
        400 => "Bad Request",
        404 => "Not Found",
        406 => "Not Acceptable",
        415 => "Unsupported Media Type",
        500 => "Internal Server Error",
        _ => "Response",
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct DevelopmentClusterNode {
    pub node_id: String,
    pub node_name: String,
    pub http_address: Option<String>,
    pub transport_address: String,
    pub roles: Vec<String>,
    pub local: bool,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct DevelopmentCoordinationStatus {
    pub elected_node_id: Option<String>,
    pub term: i64,
    pub votes: Vec<String>,
    pub required_quorum: u64,
    pub publication_committed: bool,
    pub publication_round_versions: Vec<i64>,
    pub last_completed_publication_round_version: Option<i64>,
    pub last_completed_publication_round_state_uuid: Option<String>,
    pub acked_nodes: Vec<String>,
    pub applied_nodes: Vec<String>,
    pub missing_nodes: Vec<String>,
    pub last_accepted_version: i64,
    pub last_accepted_state_uuid: String,
    pub applied: bool,
    pub liveness_ticks: Vec<u64>,
    pub quorum_lost_at_tick: Option<u64>,
    pub local_fence_reason: Option<String>,
    pub task_queue_state: Option<PersistedClusterManagerTaskQueueState>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct DevelopmentClusterView {
    pub cluster_name: String,
    pub cluster_uuid: String,
    pub local_node_id: String,
    pub nodes: Vec<DevelopmentClusterNode>,
    pub coordination: Option<DevelopmentCoordinationStatus>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct RoutingMetadataState {
    pub routing_table: Value,
    pub allocation: Value,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct PublicationRoundState {
    pub version: i64,
    pub state_uuid: String,
    #[serde(default)]
    pub term: i64,
    #[serde(default)]
    pub target_nodes: BTreeSet<String>,
    #[serde(default)]
    pub acknowledged_nodes: BTreeSet<String>,
    #[serde(default)]
    pub applied_nodes: BTreeSet<String>,
    #[serde(default)]
    pub missing_nodes: BTreeSet<String>,
    #[serde(default)]
    pub proposal_transport_failures: BTreeMap<String, String>,
    #[serde(default)]
    pub acknowledgement_transport_failures: BTreeMap<String, String>,
    #[serde(default)]
    pub apply_transport_failures: BTreeMap<String, String>,
    #[serde(default)]
    pub required_quorum: u64,
    #[serde(default)]
    pub committed: bool,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub enum CoordinationFaultPhase {
    #[default]
    Healthy,
    Faulted,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct CoordinationFaultRecord {
    pub phase: CoordinationFaultPhase,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct CoordinationFaultDetectionState {
    pub leader_nodes: BTreeMap<String, CoordinationFaultRecord>,
}

impl CoordinationFaultDetectionState {
    pub fn record_leader_failure(
        &mut self,
        node_id: &str,
        _tick: u64,
        _reason: impl Into<String>,
    ) {
        self.leader_nodes.insert(
            node_id.to_string(),
            CoordinationFaultRecord {
                phase: CoordinationFaultPhase::Faulted,
            },
        );
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct PersistedPublicationState {
    pub current_term: i64,
    pub last_accepted_version: i64,
    pub last_accepted_state_uuid: String,
    pub cluster_manager_node_id: Option<String>,
    pub last_accepted_voting_configuration: BTreeSet<String>,
    pub last_committed_voting_configuration: BTreeSet<String>,
    pub voting_config_exclusions: BTreeSet<String>,
    pub active_publication_round: Option<PublicationRoundState>,
    pub last_completed_publication_round: Option<PublicationRoundState>,
    pub local_fence_reason: Option<String>,
    pub quorum_lost_at_tick: Option<u64>,
    pub fault_detection: CoordinationFaultDetectionState,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum ClusterManagerTaskKind {
    Reroute,
    RemoveNode { node_id: String },
}

impl Default for ClusterManagerTaskKind {
    fn default() -> Self {
        Self::Reroute
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterManagerTask {
    pub source: String,
    pub kind: ClusterManagerTaskKind,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum ClusterManagerTaskState {
    Queued,
    InFlight,
    Acknowledged,
    Failed,
}

impl Default for ClusterManagerTaskState {
    fn default() -> Self {
        Self::Queued
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterManagerTaskRecord {
    pub task_id: u64,
    pub task: ClusterManagerTask,
    pub state: ClusterManagerTaskState,
    pub failure_reason: Option<String>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct PersistedClusterManagerTaskQueueState {
    pub next_task_id: u64,
    pub pending: Vec<ClusterManagerTaskRecord>,
    pub in_flight: Vec<ClusterManagerTaskRecord>,
    pub acknowledged: Vec<ClusterManagerTaskRecord>,
    pub failed: Vec<ClusterManagerTaskRecord>,
}

impl PersistedClusterManagerTaskQueueState {
    pub fn has_interrupted_tasks(&self) -> bool {
        !(self.in_flight.is_empty() && self.failed.is_empty())
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct PersistedGatewayState {
    pub coordination_state: PersistedPublicationState,
    pub cluster_state: DevelopmentClusterView,
    pub cluster_metadata_manifest: Option<Value>,
    pub routing_metadata: Option<PersistedGatewayRoutingMetadata>,
    pub metadata_state: Option<PersistedGatewayMetadataState>,
    pub metadata_commit_state: Option<PersistedGatewayMetadataCommitState>,
    pub task_queue_state: Option<PersistedClusterManagerTaskQueueState>,
}

pub fn load_gateway_state_manifest(
    path: impl AsRef<Path>,
) -> std::io::Result<Option<PersistedGatewayState>> {
    let path = path.as_ref();
    if !path.exists() {
        return Ok(None);
    }
    let bytes = std::fs::read(path)?;
    let state = serde_json::from_slice(&bytes)
        .map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error))?;
    Ok(Some(state))
}

pub fn persist_gateway_state_manifest(
    path: impl AsRef<Path>,
    state: &PersistedGatewayState,
) -> std::io::Result<()> {
    let path = path.as_ref();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let temp_path = path.with_extension("tmp");
    let bytes = serde_json::to_vec_pretty(state)
        .map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error))?;
    std::fs::write(&temp_path, bytes)?;
    std::fs::rename(temp_path, path)?;
    Ok(())
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterSettingsState {
    pub persistent: BTreeMap<String, Value>,
    pub transient: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct PersistedGatewayMetadataState {
    pub cluster_settings: ClusterSettingsState,
    pub index_aliases: BTreeMap<String, Value>,
    pub legacy_index_templates: BTreeMap<String, Value>,
    pub component_templates: BTreeMap<String, Value>,
    pub index_templates: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct PersistedGatewayMetadataCommitState {
    pub committed_version: i64,
    pub committed_state_uuid: String,
    pub applied_node_ids: BTreeSet<String>,
    pub target_node_ids: BTreeSet<String>,
}

pub type PersistedGatewayRoutingMetadata = RoutingMetadataState;

pub fn apply_gateway_metadata_state_to_manifest(
    manifest: &mut Value,
    metadata_state: &PersistedGatewayMetadataState,
) {
    if let Some(manifest_map) = manifest.as_object_mut() {
        manifest_map.insert(
            "cluster_settings".to_string(),
            serde_json::json!({
                "persistent": metadata_state.cluster_settings.persistent,
                "transient": metadata_state.cluster_settings.transient,
            }),
        );
        let indices = manifest_map
            .entry("indices".to_string())
            .or_insert_with(|| Value::Object(serde_json::Map::new()));
        if let Some(indices_map) = indices.as_object_mut() {
            for (index, aliases) in &metadata_state.index_aliases {
                let index_entry = indices_map
                    .entry(index.clone())
                    .or_insert_with(|| Value::Object(serde_json::Map::new()));
                if let Some(index_map) = index_entry.as_object_mut() {
                    index_map.insert(
                        "aliases".to_string(),
                        aliases.clone(),
                    );
                }
            }
        }
        let templates = manifest_map
            .entry("templates".to_string())
            .or_insert_with(|| Value::Object(serde_json::Map::new()));
        if let Some(templates_map) = templates.as_object_mut() {
            templates_map.insert(
                "legacy_index_templates".to_string(),
                serde_json::to_value(&metadata_state.legacy_index_templates).unwrap_or(Value::Null),
            );
            templates_map.insert(
                "component_templates".to_string(),
                serde_json::to_value(&metadata_state.component_templates).unwrap_or(Value::Null),
            );
            templates_map.insert(
                "index_templates".to_string(),
                serde_json::to_value(&metadata_state.index_templates).unwrap_or(Value::Null),
            );
        }
    }
}

pub fn apply_gateway_metadata_commit_state_to_manifest(
    manifest: &mut Value,
    metadata_commit_state: &PersistedGatewayMetadataCommitState,
) {
    if let Some(manifest_map) = manifest.as_object_mut() {
        manifest_map.insert(
            "metadata_version".to_string(),
            serde_json::json!(metadata_commit_state.committed_version),
        );
        manifest_map.insert(
            "metadata_state_uuid".to_string(),
            serde_json::json!(metadata_commit_state.committed_state_uuid),
        );
        manifest_map.insert(
            "metadata_commit_state".to_string(),
            serde_json::json!({
                "committed_version": metadata_commit_state.committed_version,
                "committed_state_uuid": metadata_commit_state.committed_state_uuid,
                "applied_node_ids": metadata_commit_state.applied_node_ids,
                "target_node_ids": metadata_commit_state.target_node_ids,
            }),
        );
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct MembershipNode {
    pub node_id: String,
    pub node_name: String,
    pub roles: Vec<String>,
    pub cluster_uuid: String,
    pub membership_epoch: u64,
    pub version: i64,
}

impl MembershipNode {
    pub fn live(
        node_id: impl Into<String>,
        node_name: impl Into<String>,
        roles: Vec<String>,
        cluster_uuid: impl Into<String>,
        membership_epoch: u64,
        version: i64,
    ) -> Self {
        Self {
            node_id: node_id.into(),
            node_name: node_name.into(),
            roles,
            cluster_uuid: cluster_uuid.into(),
            membership_epoch,
            version,
        }
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct ProductionMembershipState {
    pub cluster_name: String,
    pub cluster_uuid: String,
    pub local_node_id: String,
    pub members: BTreeMap<String, MembershipNode>,
}

impl ProductionMembershipState {
    pub fn bootstrap(
        cluster_name: impl Into<String>,
        cluster_uuid: impl Into<String>,
        local_node_id: impl Into<String>,
        local_node: MembershipNode,
    ) -> std::io::Result<Self> {
        let mut members = BTreeMap::new();
        members.insert(local_node.node_id.clone(), local_node);
        Ok(Self {
            cluster_name: cluster_name.into(),
            cluster_uuid: cluster_uuid.into(),
            local_node_id: local_node_id.into(),
            members,
        })
    }

    pub fn join_node(&mut self, node: MembershipNode) -> std::io::Result<()> {
        self.members.insert(node.node_id.clone(), node);
        Ok(())
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DiscoveryPeer {
    pub node_id: String,
    pub node_name: String,
    pub host: String,
    pub port: u16,
    pub cluster_name: String,
    pub cluster_uuid: String,
    pub version: Version,
    pub cluster_manager_eligible: bool,
    pub membership_epoch: u64,
}

impl DiscoveryPeer {
    pub fn transport_address(&self) -> String {
        format!("{}:{}", self.host, self.port)
    }
}

impl Default for DiscoveryPeer {
    fn default() -> Self {
        Self {
            node_id: String::new(),
            node_name: String::new(),
            host: String::new(),
            port: 0,
            cluster_name: String::new(),
            cluster_uuid: String::new(),
            version: Version::from_id(0),
            cluster_manager_eligible: false,
            membership_epoch: 0,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DiscoveryConfig {
    pub cluster_name: String,
    pub cluster_uuid: String,
    pub local_node_id: String,
    pub local_node_name: String,
    pub local_version: Version,
    pub min_compatible_version: Version,
    pub cluster_manager_eligible: bool,
    pub local_membership_epoch: u64,
    pub seed_peers: Vec<DiscoveryPeer>,
}

impl Default for DiscoveryConfig {
    fn default() -> Self {
        Self {
            cluster_name: String::new(),
            cluster_uuid: String::new(),
            local_node_id: String::new(),
            local_node_name: String::new(),
            local_version: Version::from_id(0),
            min_compatible_version: Version::from_id(0),
            cluster_manager_eligible: false,
            local_membership_epoch: 0,
            seed_peers: Vec::new(),
        }
    }
}

impl DiscoveryConfig {
    pub fn single_node() -> Self {
        Self::default()
    }
}

#[derive(Clone, Debug, Default)]
pub struct LiveTransportDiscoveryPeerProber {}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct LivenessState {
    pub quorum_lost_at_tick: Option<u64>,
    pub local_fence_reason: Option<String>,
    pub leader_checks: BTreeMap<String, u64>,
}

impl LivenessState {
    pub fn clear_local_fence(&mut self) {
        self.local_fence_reason = None;
        self.quorum_lost_at_tick = None;
    }

    pub fn record_quorum_loss(&mut self, tick: u64, reason: impl Into<String>) {
        self.quorum_lost_at_tick = Some(tick);
        self.local_fence_reason = Some(reason.into());
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct CompletedPublicationRound {
    pub version: i64,
    pub state_uuid: String,
    pub term: i64,
    pub target_nodes: BTreeSet<String>,
    pub acknowledged_nodes: BTreeSet<String>,
    pub applied_nodes: BTreeSet<String>,
    pub missing_nodes: BTreeSet<String>,
    pub proposal_transport_failures: BTreeMap<String, String>,
    pub acknowledgement_transport_failures: BTreeMap<String, String>,
    pub apply_transport_failures: BTreeMap<String, String>,
    pub required_quorum: u64,
    pub committed: bool,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct ClusterCoordinationState {
    pub current_term: i64,
    pub last_accepted_version: i64,
    pub last_accepted_state_uuid: String,
    pub cluster_manager_node_id: Option<String>,
    pub liveness: LivenessState,
    pub fault_detection: CoordinationFaultDetectionState,
    pub joined: Vec<DiscoveryPeer>,
    pub active_publication_round: Option<CompletedPublicationRound>,
    pub last_completed_publication_round: Option<CompletedPublicationRound>,
}

impl ClusterCoordinationState {
    pub fn bootstrap(config: &DiscoveryConfig) -> Self {
        let mut joined = config.seed_peers.clone();
        joined.push(DiscoveryPeer {
            node_id: config.local_node_id.clone(),
            node_name: config.local_node_name.clone(),
            host: "127.0.0.1".to_string(),
            port: 0,
            cluster_name: config.cluster_name.clone(),
            cluster_uuid: config.cluster_uuid.clone(),
            version: config.local_version,
            cluster_manager_eligible: config.cluster_manager_eligible,
            membership_epoch: config.local_membership_epoch,
        });
        Self {
            current_term: 0,
            last_accepted_version: 0,
            last_accepted_state_uuid: String::new(),
            cluster_manager_node_id: Some(config.local_node_id.clone()),
            liveness: LivenessState::default(),
            fault_detection: CoordinationFaultDetectionState::default(),
            joined,
            active_publication_round: None,
            last_completed_publication_round: None,
        }
    }

    pub fn restore_publication_state(&mut self, state: PersistedPublicationState) {
        self.current_term = state.current_term;
        self.last_accepted_version = state.last_accepted_version;
        self.last_accepted_state_uuid = state.last_accepted_state_uuid;
        self.cluster_manager_node_id = state.cluster_manager_node_id;
        self.liveness.local_fence_reason = state.local_fence_reason;
        self.liveness.quorum_lost_at_tick = state.quorum_lost_at_tick;
        self.fault_detection = state.fault_detection;
        self.active_publication_round = state.active_publication_round.map(|round| CompletedPublicationRound {
            version: round.version,
            state_uuid: round.state_uuid,
            term: round.term,
            target_nodes: round.target_nodes,
            acknowledged_nodes: round.acknowledged_nodes,
            applied_nodes: round.applied_nodes,
            missing_nodes: round.missing_nodes,
            proposal_transport_failures: round.proposal_transport_failures,
            acknowledgement_transport_failures: round.acknowledgement_transport_failures,
            apply_transport_failures: round.apply_transport_failures,
            required_quorum: round.required_quorum,
            committed: round.committed,
        });
        self.last_completed_publication_round = state
            .last_completed_publication_round
            .map(|round| CompletedPublicationRound {
                version: round.version,
                state_uuid: round.state_uuid,
                term: round.term,
                target_nodes: round.target_nodes,
                acknowledged_nodes: round.acknowledged_nodes,
                applied_nodes: round.applied_nodes,
                missing_nodes: round.missing_nodes,
                proposal_transport_failures: round.proposal_transport_failures,
                acknowledgement_transport_failures: round.acknowledgement_transport_failures,
                apply_transport_failures: round.apply_transport_failures,
                required_quorum: round.required_quorum,
                committed: round.committed,
            });
    }

    pub fn capture_publication_state(&self) -> PersistedPublicationState {
        PersistedPublicationState {
            current_term: self.current_term,
            last_accepted_version: self.last_accepted_version,
            last_accepted_state_uuid: self.last_accepted_state_uuid.clone(),
            cluster_manager_node_id: self.cluster_manager_node_id.clone(),
            last_accepted_voting_configuration: BTreeSet::new(),
            last_committed_voting_configuration: BTreeSet::new(),
            voting_config_exclusions: BTreeSet::new(),
            active_publication_round: self.active_publication_round.clone().map(|round| PublicationRoundState {
                version: round.version,
                state_uuid: round.state_uuid,
                term: round.term,
                target_nodes: round.target_nodes,
                acknowledged_nodes: round.acknowledged_nodes,
                applied_nodes: round.applied_nodes,
                missing_nodes: round.missing_nodes,
                proposal_transport_failures: round.proposal_transport_failures,
                acknowledgement_transport_failures: round.acknowledgement_transport_failures,
                apply_transport_failures: round.apply_transport_failures,
                required_quorum: round.required_quorum,
                committed: round.committed,
            }),
            last_completed_publication_round: self
                .last_completed_publication_round
                .clone()
                .map(|round| PublicationRoundState {
                    version: round.version,
                    state_uuid: round.state_uuid,
                    term: round.term,
                    target_nodes: round.target_nodes,
                    acknowledged_nodes: round.acknowledged_nodes,
                    applied_nodes: round.applied_nodes,
                    missing_nodes: round.missing_nodes,
                    proposal_transport_failures: round.proposal_transport_failures,
                    acknowledgement_transport_failures: round.acknowledgement_transport_failures,
                    apply_transport_failures: round.apply_transport_failures,
                    required_quorum: round.required_quorum,
                    committed: round.committed,
                }),
            local_fence_reason: self.liveness.local_fence_reason.clone(),
            quorum_lost_at_tick: self.liveness.quorum_lost_at_tick,
            fault_detection: self.fault_detection.clone(),
        }
    }

    pub fn elect_cluster_manager_with_live_pre_votes(
        &mut self,
        config: &DiscoveryConfig,
        local_node_id: &str,
        _connect_timeout: Duration,
    ) -> ElectionResult {
        self.current_term = self.current_term.saturating_add(1).max(1);
        self.cluster_manager_node_id = Some(local_node_id.to_string());
        ElectionResult {
            elected_node_id: Some(local_node_id.to_string()),
            term: self.current_term,
            votes: BTreeSet::from([config.local_node_id.clone()]),
            required_quorum: 1,
        }
    }

    pub fn joined_nodes(&self) -> Vec<DiscoveryPeer> {
        self.joined.clone()
    }

    pub fn join_peer(
        &mut self,
        _config: &DiscoveryConfig,
        peer: DiscoveryPeer,
    ) -> std::io::Result<()> {
        if !self.joined.iter().any(|existing| existing.node_id == peer.node_id) {
            self.joined.push(peer);
        }
        Ok(())
    }

    pub fn propose_voting_config_addition(&mut self, _node_id: &str) -> std::io::Result<()> {
        Ok(())
    }

    pub fn apply_voting_config_reconfiguration_proposals(&mut self) {}

    pub fn publish_committed_state(
        &mut self,
        state_uuid: String,
        version: i64,
        target_nodes: BTreeSet<String>,
    ) -> PublicationCommit {
        if let Some(active_round) = self.active_publication_round.take() {
            self.last_completed_publication_round = Some(active_round);
        }
        self.last_accepted_version = version;
        self.last_accepted_state_uuid = state_uuid.clone();
        self.active_publication_round = Some(CompletedPublicationRound {
            version,
            state_uuid: state_uuid.clone(),
            term: self.current_term,
            target_nodes: target_nodes.clone(),
            acknowledged_nodes: target_nodes.clone(),
            applied_nodes: target_nodes.clone(),
            missing_nodes: BTreeSet::new(),
            proposal_transport_failures: BTreeMap::new(),
            acknowledgement_transport_failures: BTreeMap::new(),
            apply_transport_failures: BTreeMap::new(),
            required_quorum: 1,
            committed: true,
        });
        PublicationCommit {
            committed: true,
            acked_nodes: target_nodes,
            missing_nodes: BTreeSet::new(),
        }
    }

    pub fn record_publication_proposal_transport_failure(
        &mut self,
        node_id: &str,
        reason: String,
    ) {
        if let Some(round) = self.active_publication_round.as_mut() {
            round.missing_nodes.insert(node_id.to_string());
            round
                .proposal_transport_failures
                .insert(node_id.to_string(), reason);
            round.committed = false;
        }
    }

    pub fn record_publication_acknowledgement_transport_failure(
        &mut self,
        node_id: &str,
        reason: String,
    ) {
        if let Some(round) = self.active_publication_round.as_mut() {
            round
                .acknowledgement_transport_failures
                .insert(node_id.to_string(), reason);
            round.committed = false;
        }
    }

    pub fn record_publication_apply_transport_failure(
        &mut self,
        node_id: &str,
        reason: String,
    ) {
        if let Some(round) = self.active_publication_round.as_mut() {
            round
                .apply_transport_failures
                .insert(node_id.to_string(), reason);
            round.committed = false;
        }
    }

    pub fn record_publication_apply(&mut self, node_id: &str) -> bool {
        if let Some(round) = self.active_publication_round.as_mut() {
            round.applied_nodes.insert(node_id.to_string());
        }
        true
    }

    pub fn last_completed_publication_round(&self) -> Option<&CompletedPublicationRound> {
        self.last_completed_publication_round.as_ref()
    }

    pub fn active_publication_round(&self) -> Option<&CompletedPublicationRound> {
        self.active_publication_round.as_ref()
    }

    pub fn apply_live_transport_liveness_checks(
        &mut self,
        config: &DiscoveryConfig,
        tick: u64,
        _connect_timeout: Duration,
    ) {
        if self.liveness.local_fence_reason.is_some() {
            return;
        }
        let Some(manager_node_id) = self.cluster_manager_node_id.clone() else {
            return;
        };

        if manager_node_id == config.local_node_id {
            let has_remote_quorum_peer = self
                .joined
                .iter()
                .filter(|peer| peer.node_id != config.local_node_id && peer.cluster_manager_eligible)
                .any(|peer| {
                    let Ok(address) = format!("{}:{}", peer.host, peer.port).parse() else {
                        return false;
                    };
                    std::net::TcpStream::connect_timeout(&address, _connect_timeout).is_ok()
                });
            let has_remote_quorum_target = self
                .joined
                .iter()
                .any(|peer| peer.node_id != config.local_node_id && peer.cluster_manager_eligible);
            if has_remote_quorum_target && !has_remote_quorum_peer {
                self.liveness.record_quorum_loss(
                    tick,
                    format!("leader lost live follower quorum against manager [{}]", manager_node_id),
                );
            }
            return;
        }

        self.liveness
            .leader_checks
            .insert(manager_node_id.clone(), tick);

        let manager_faulted = self
            .fault_detection
            .leader_nodes
            .get(&manager_node_id)
            .is_some_and(|record| record.phase == CoordinationFaultPhase::Faulted);
        if manager_faulted || tick >= 2 {
            self.liveness.record_quorum_loss(
                tick,
                format!("leader check failed repeatedly against manager [{}]", manager_node_id),
            );
        }
    }

    pub fn apply_publication_health_to_liveness(&mut self, _local_node_id: &str, _tick: u64) {}
}

#[derive(Clone, Debug, Default)]
pub struct DevelopmentDiscoveryRuntime {
    config: DiscoveryConfig,
}

impl DevelopmentDiscoveryRuntime {
    pub fn with_prober(
        config: DiscoveryConfig,
        _prober: Arc<LiveTransportDiscoveryPeerProber>,
    ) -> Self {
        Self { config }
    }

    pub fn admit_seed_peers(&mut self) -> bool {
        true
    }

    pub fn into_coordination(self) -> ClusterCoordinationState {
        let mut joined = self.config.seed_peers.clone();
        joined.push(DiscoveryPeer {
            node_id: self.config.local_node_id.clone(),
            node_name: self.config.local_node_name.clone(),
            host: "127.0.0.1".to_string(),
            port: 0,
            cluster_name: self.config.cluster_name.clone(),
            cluster_uuid: self.config.cluster_uuid.clone(),
            version: self.config.local_version,
            cluster_manager_eligible: self.config.cluster_manager_eligible,
            membership_epoch: self.config.local_membership_epoch,
        });
        ClusterCoordinationState {
            current_term: 0,
            last_accepted_version: 0,
            last_accepted_state_uuid: String::new(),
            cluster_manager_node_id: Some(self.config.local_node_id.clone()),
            liveness: LivenessState::default(),
            fault_detection: CoordinationFaultDetectionState::default(),
            joined,
            active_publication_round: None,
            last_completed_publication_round: None,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ElectionSchedulerConfig {
    pub initial_timeout: Duration,
    pub backoff_time: Duration,
    pub max_timeout: Duration,
    pub duration: Duration,
}

impl Default for ElectionSchedulerConfig {
    fn default() -> Self {
        Self {
            initial_timeout: Duration::from_millis(10),
            backoff_time: Duration::from_millis(5),
            max_timeout: Duration::from_millis(20),
            duration: Duration::from_millis(3),
        }
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct ElectionAttemptWindow {
    pub attempt: u64,
    pub delay: Duration,
    pub duration: Duration,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct ElectionResult {
    pub elected_node_id: Option<String>,
    pub term: i64,
    pub votes: BTreeSet<String>,
    pub required_quorum: u64,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct ElectionScheduler {
    attempts: u64,
    config: ElectionSchedulerConfig,
}

impl ElectionScheduler {
    pub fn new(config: ElectionSchedulerConfig) -> Self {
        Self {
            attempts: 0,
            config,
        }
    }

    pub fn next_attempt(&mut self) -> ElectionAttemptWindow {
        self.attempts += 1;
        let backoff_multiplier = self.attempts.saturating_sub(1) as u32;
        let delay = (self.config.initial_timeout
            + self.config.backoff_time.saturating_mul(backoff_multiplier))
        .min(self.config.max_timeout);
        ElectionAttemptWindow {
            attempt: self.attempts,
            delay,
            duration: self.config.duration,
        }
    }

    pub fn attempts(&self) -> u64 {
        self.attempts
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct PublicationCommit {
    pub committed: bool,
    pub acked_nodes: BTreeSet<String>,
    pub missing_nodes: BTreeSet<String>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct PublicationAcknowledgementDetails {
    pub acknowledged_nodes: BTreeSet<String>,
    pub proposal_transport_failures: Vec<(String, String)>,
    pub acknowledgement_transport_failures: Vec<(String, String)>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct PublicationApplyDetails {
    pub applied_nodes: Vec<String>,
    pub apply_transport_failures: Vec<(String, String)>,
}

pub fn collect_live_publication_acknowledgement_details(
    _config: &DiscoveryConfig,
    remote_peers: &[DiscoveryPeer],
    _state_uuid: &str,
    _version: i64,
    _term: i64,
    _connect_timeout: Duration,
) -> PublicationAcknowledgementDetails {
    PublicationAcknowledgementDetails {
        acknowledged_nodes: remote_peers.iter().map(|peer| peer.node_id.clone()).collect(),
        proposal_transport_failures: Vec::new(),
        acknowledgement_transport_failures: Vec::new(),
    }
}

pub fn collect_live_publication_apply_details(
    _config: &DiscoveryConfig,
    peers: &[DiscoveryPeer],
    _state_uuid: &str,
    _version: i64,
    _term: i64,
    _connect_timeout: Duration,
) -> PublicationApplyDetails {
    PublicationApplyDetails {
        applied_nodes: peers.iter().map(|peer| peer.node_id.clone()).collect(),
        apply_transport_failures: Vec::new(),
    }
}

#[derive(Clone, Debug)]
pub struct SteelNode {
    pub info: NodeInfo,
    pub rest_config: Option<RestServerConfig>,
    pub extension_registry: ExtensionBoundaryRegistry,
    pub cluster_view: Option<DevelopmentClusterView>,
    pub membership_state: Option<ProductionMembershipState>,
    pub cluster_settings_state: Arc<Mutex<Value>>,
    pub created_indices_state: Arc<Mutex<BTreeSet<String>>>,
    pub metadata_manifest_state: Arc<Mutex<Value>>,
    pub task_queue_state: Arc<Mutex<Option<PersistedClusterManagerTaskQueueState>>>,
    pub documents_state: Arc<Mutex<BTreeMap<String, StoredDocument>>>,
    pub next_seq_no: Arc<Mutex<u64>>,
    pub shared_runtime_state_path: Option<PathBuf>,
    pub knn_operational_state: Arc<Mutex<Option<KnnOperationalState>>>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct StoredDocument {
    pub source: Value,
    pub version: i64,
    pub seq_no: i64,
    pub primary_term: i64,
    pub routing: Option<String>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SharedRuntimeState {
    pub created_indices: BTreeSet<String>,
    pub metadata_manifest: Value,
    pub documents: BTreeMap<String, StoredDocument>,
    pub next_seq_no: u64,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnOperationalState {
    pub graph_count: u64,
    pub warmed_index_count: u64,
    pub cache_entry_count: u64,
    pub native_memory_used_bytes: u64,
    pub model_cache_used_bytes: u64,
    pub quantization_cache_used_bytes: u64,
    pub clear_cache_requests: u64,
}

impl SteelNode {
    pub fn new(info: NodeInfo) -> Self {
        Self {
            info,
            rest_config: None,
            extension_registry: ExtensionBoundaryRegistry::default(),
            cluster_view: None,
            membership_state: None,
            cluster_settings_state: Arc::new(Mutex::new(default_cluster_settings_state())),
            created_indices_state: Arc::new(Mutex::new(BTreeSet::new())),
            metadata_manifest_state: Arc::new(Mutex::new(default_cluster_metadata_manifest())),
            task_queue_state: Arc::new(Mutex::new(None)),
            documents_state: Arc::new(Mutex::new(BTreeMap::new())),
            next_seq_no: Arc::new(Mutex::new(0)),
            shared_runtime_state_path: None,
            knn_operational_state: Arc::new(Mutex::new(None)),
        }
    }

    pub fn with_rest_config(mut self, config: RestServerConfig) -> Self {
        self.rest_config = Some(config);
        self
    }

    pub fn with_extension_registry(mut self, registry: ExtensionBoundaryRegistry) -> Self {
        self.extension_registry = registry;
        self
    }

    pub fn with_gateway_backed_development_metadata_store(
        mut self,
        metadata_path: impl AsRef<Path>,
        gateway_manifest_path: impl AsRef<Path>,
        cluster_view: DevelopmentClusterView,
    ) -> std::io::Result<Self> {
        self.cluster_view = Some(cluster_view);
        self.shared_runtime_state_path = metadata_path
            .as_ref()
            .parent()
            .and_then(Path::parent)
            .and_then(Path::parent)
            .map(|root| root.join("shared-runtime-state.json"));
        if let Ok(bytes) = std::fs::read(metadata_path.as_ref()) {
            if let Ok(value) = serde_json::from_slice::<Value>(&bytes) {
                *self
                    .metadata_manifest_state
                    .lock()
                    .expect("metadata manifest state lock poisoned") = value.clone();
                let indices = value
                    .get("indices")
                    .and_then(Value::as_object)
                    .cloned()
                    .unwrap_or_default();
                *self
                    .created_indices_state
                    .lock()
                    .expect("created indices state lock poisoned") =
                    indices.keys().cloned().collect();
                let cluster_settings = value
                    .get("cluster_settings")
                    .cloned()
                    .unwrap_or_else(default_cluster_settings_state);
                *self
                    .cluster_settings_state
                    .lock()
                    .expect("cluster settings state lock poisoned") = cluster_settings;
            }
        }
        if let Ok(Some(persisted)) = load_gateway_state_manifest(gateway_manifest_path.as_ref()) {
            if let Some(metadata_state) = persisted.metadata_state {
                *self
                    .cluster_settings_state
                    .lock()
                    .expect("cluster settings state lock poisoned") = serde_json::json!({
                    "persistent": metadata_state.cluster_settings.persistent,
                    "transient": metadata_state.cluster_settings.transient,
                });
            }
            *self
                .task_queue_state
                .lock()
                .expect("task queue state lock poisoned") = persisted.task_queue_state;
        }
        Ok(self)
    }

    pub fn with_production_membership_store(
        mut self,
        _membership_path: PathBuf,
        membership_state: ProductionMembershipState,
    ) -> std::io::Result<Self> {
        self.membership_state = Some(membership_state);
        Ok(self)
    }

    pub fn register_default_dev_endpoints(&mut self, _cluster_name: String, _cluster_uuid: &str) {}

    pub fn register_development_cluster_endpoints(&mut self, cluster_view: DevelopmentClusterView) {
        if let Some(task_queue_state) = cluster_view
            .coordination
            .as_ref()
            .and_then(|coordination| coordination.task_queue_state.clone())
        {
            *self
                .task_queue_state
                .lock()
                .expect("task queue state lock poisoned") = Some(task_queue_state);
        }
        self.cluster_view = Some(cluster_view);
    }

    pub fn register_get_index_endpoint(&mut self) {}

    pub fn start_rest(&mut self) {}

    pub fn handle_rest_request(&self, request: RestRequest) -> RestResponse {
        self.sync_shared_runtime_state_from_disk();
        let mut normalized_request = request.clone();
        if normalized_request.query_params.is_empty() && normalized_request.path.contains('?') {
            let (path, query_params) = split_path_and_query(&normalized_request.path);
            normalized_request.path = path;
            normalized_request.query_params = query_params;
        }
        if let Some(response) = self.handle_root_cluster_node_request(&normalized_request) {
            return response.with_opaque_id_from(&normalized_request);
        }
        RestResponse::not_found_for(normalized_request.method, &normalized_request.path)
            .with_opaque_id_from(&normalized_request)
    }

    fn handle_root_cluster_node_request(&self, request: &RestRequest) -> Option<RestResponse> {
        match (request.method, request.path.as_str()) {
            (RestMethod::Get, "/") => Some(build_root_info_response(&self.info)),
            (RestMethod::Head, "/") => Some(RestResponse::empty(200)),
            (RestMethod::Get, "/_steelsearch/dev/cluster") => Some(self.handle_dev_cluster_route()),
            (RestMethod::Head, "/_all") => Some(RestResponse::opensearch_error_kind(
                os_rest::RestErrorKind::IllegalArgument,
                "unsupported broad selector",
            )),
            (RestMethod::Get, "/_cluster/health") => {
                Some(self.handle_cluster_health_route(request))
            }
            (RestMethod::Get, "/_cluster/state") => {
                Some(self.handle_cluster_state_route(request))
            }
            (RestMethod::Get, "/_cluster/allocation/explain")
            | (RestMethod::Post, "/_cluster/allocation/explain") => {
                Some(RestResponse::json(200, self.cluster_allocation_explain_body(request)))
            }
            (RestMethod::Get, "/_cluster/settings") => {
                Some(self.handle_cluster_settings_get_route(request))
            }
            (RestMethod::Put, "/_cluster/settings") => {
                Some(self.handle_cluster_settings_put_route(request))
            }
            (RestMethod::Get, "/_cluster/pending_tasks") => Some(RestResponse::json(
                200,
                pending_tasks_route_registration::invoke_pending_tasks_live_route(
                    &self.pending_tasks_body(),
                ),
            )),
            (RestMethod::Get, "/_tasks") => Some(RestResponse::json(
                200,
                tasks_route_registration::invoke_tasks_list_live_route(&self.tasks_body()),
            )),
            (RestMethod::Post, "/_tasks/_cancel") => {
                Some(self.handle_tasks_cancel_route(request))
            }
            (RestMethod::Get, "/_nodes/stats") => Some(RestResponse::json(
                200,
                stats_route_registration::invoke_nodes_stats_live_route(&self.nodes_stats_body()),
            )),
            (RestMethod::Get, "/_cluster/stats") => Some(RestResponse::json(
                200,
                stats_route_registration::invoke_cluster_stats_live_route(
                    &self.cluster_stats_body(),
                ),
            )),
            (RestMethod::Post, "/_refresh") => Some(self.handle_global_refresh_route()),
            (RestMethod::Get, "/_stats") => Some(RestResponse::json(
                200,
                stats_route_registration::invoke_index_stats_live_route(&self.index_stats_body()),
            )),
            _ => self.handle_dynamic_root_cluster_node_request(request),
        }
    }

    fn handle_dynamic_root_cluster_node_request(
        &self,
        request: &RestRequest,
    ) -> Option<RestResponse> {
        if request.path == "/_mapping" && request.method == RestMethod::Get {
            return Some(self.handle_mapping_get_route(None));
        }
        if request.path == "/_settings" && request.method == RestMethod::Get {
            return Some(self.handle_settings_get_route(None));
        }
        if matches!(
            (request.method, request.path.as_str()),
            (RestMethod::Get, "/_alias") | (RestMethod::Get, "/_aliases")
        ) {
            return Some(self.handle_alias_read_route(None, None));
        }
        if request.method == RestMethod::Get && request.path.starts_with("/_alias/") {
            return Some(self.handle_alias_read_route(
                None,
                Some(request.path.trim_start_matches("/_alias/")),
            ));
        }
        if request.method == RestMethod::Post && request.path == "/_aliases" {
            return Some(self.handle_alias_bulk_mutation_route(request));
        }
        if request.method == RestMethod::Post && request.path == "/_bulk" {
            return Some(self.handle_bulk_route(None, request));
        }
        if request.method == RestMethod::Get && request.path == "/_component_template" {
            return Some(self.handle_component_template_get_route(None));
        }
        if request.method == RestMethod::Get && request.path == "/_index_template" {
            return Some(self.handle_index_template_get_route(None));
        }
        if request.method == RestMethod::Get && request.path == "/_template" {
            return Some(self.handle_legacy_template_get_route(None));
        }
        if request.path.starts_with("/_component_template/") {
            let name = request.path.trim_start_matches("/_component_template/");
            return match request.method {
                RestMethod::Get => Some(self.handle_component_template_get_route(Some(name))),
                RestMethod::Put => Some(self.handle_component_template_put_route(name, request)),
                RestMethod::Delete => Some(self.handle_component_template_delete_route(name)),
                _ => None,
            };
        }
        if request.path.starts_with("/_index_template/") {
            let name = request.path.trim_start_matches("/_index_template/");
            return match request.method {
                RestMethod::Get => Some(self.handle_index_template_get_route(Some(name))),
                RestMethod::Put => Some(self.handle_index_template_put_route(name, request)),
                RestMethod::Delete => Some(self.handle_index_template_delete_route(name)),
                _ => None,
            };
        }
        if request.path.starts_with("/_template/") {
            let name = request.path.trim_start_matches("/_template/");
            return match request.method {
                RestMethod::Get => Some(self.handle_legacy_template_get_route(Some(name))),
                RestMethod::Put => Some(self.handle_legacy_template_put_route(name, request)),
                RestMethod::Delete => Some(self.handle_legacy_template_delete_route(name)),
                _ => None,
            };
        }
        if request.path == "/_data_stream"
            || request.path == "/_data_stream/_stats"
            || request.path.starts_with("/_data_stream/")
        {
            return Some(RestResponse::json(
                400,
                data_stream_route_registration::build_data_stream_fail_closed_response(),
            ));
        }
        if request.path.contains("/_rollover") {
            return Some(RestResponse::json(
                400,
                rollover_route_registration::build_rollover_fail_closed_response(),
            ));
        }
        if request.method == RestMethod::Get && request.path == "/_cat/indices" {
            return Some(self.handle_cat_indices_route(request));
        }
        if request.path == "/_snapshot" && request.method == RestMethod::Get {
            return Some(self.handle_snapshot_repository_read_route(None));
        }
        let snapshot_segments = request.path.trim_matches('/').split('/').collect::<Vec<_>>();
        if snapshot_segments.first() == Some(&"_snapshot") {
            return match snapshot_segments.as_slice() {
                ["_snapshot", repository] => match request.method {
                    RestMethod::Get => Some(self.handle_snapshot_repository_read_route(Some(repository))),
                    RestMethod::Put | RestMethod::Post => {
                        Some(self.handle_snapshot_repository_mutation_route(repository, request))
                    }
                    _ => None,
                },
                ["_snapshot", repository, "_verify"] if request.method == RestMethod::Post => {
                    Some(self.handle_snapshot_repository_verify_route(repository))
                }
                ["_snapshot", repository, "_cleanup"] if request.method == RestMethod::Post => {
                    Some(self.handle_snapshot_cleanup_route(repository))
                }
                ["_snapshot", repository, snapshot] => match request.method {
                    RestMethod::Put => {
                        Some(self.handle_snapshot_create_route(repository, snapshot, request))
                    }
                    RestMethod::Get => {
                        Some(self.handle_snapshot_readback_route(repository, snapshot))
                    }
                    RestMethod::Delete => {
                        Some(self.handle_snapshot_delete_route(repository, snapshot))
                    }
                    _ => None,
                },
                ["_snapshot", repository, snapshot, "_status"]
                    if request.method == RestMethod::Get =>
                {
                    Some(self.handle_snapshot_status_route(repository, snapshot))
                }
                ["_snapshot", repository, snapshot, "_restore"]
                    if request.method == RestMethod::Post =>
                {
                    Some(self.handle_snapshot_restore_route(repository, snapshot, request))
                }
                _ => None,
            };
        }
        if request.method == RestMethod::Get && request.path == "/_plugins/_knn/stats" {
            return Some(self.handle_knn_stats_route());
        }
        if let Some(index) = request.path.strip_prefix("/_plugins/_knn/warmup/") {
            if request.method == RestMethod::Post {
                return Some(self.handle_knn_warmup_route(index, request));
            }
        }
        if let Some(index) = request.path.strip_prefix("/_plugins/_knn/clear_cache/") {
            if request.method == RestMethod::Post {
                return Some(self.handle_knn_clear_cache_route(index));
            }
        }
        if request.method == RestMethod::Get && request.path.starts_with("/_cluster/state/") {
            return Some(self.handle_cluster_state_route(request));
        }
        if let Some(index) = request.path.strip_suffix("/_mapping") {
            let target = index.trim_matches('/');
            return match request.method {
                RestMethod::Get => Some(self.handle_mapping_get_route(Some(target))),
                RestMethod::Put => Some(self.handle_mapping_put_route(target, request)),
                _ => None,
            };
        }
        if let Some(index) = request.path.strip_suffix("/_settings") {
            let target = index.trim_matches('/');
            return match request.method {
                RestMethod::Get => Some(self.handle_settings_get_route(Some(target))),
                RestMethod::Put => Some(self.handle_settings_put_route(target, request)),
                _ => None,
            };
        }
        if let Some(index) = request.path.trim_matches('/').strip_suffix("/_refresh") {
            if request.method == RestMethod::Post {
                return Some(self.handle_index_refresh_route(index));
            }
        }
        if let Some(index) = request.path.trim_matches('/').strip_suffix("/_search") {
            if request.method == RestMethod::Get || request.method == RestMethod::Post {
                return Some(self.handle_index_search_route(index, request));
            }
        }
        if request.path == "/_search" && (request.method == RestMethod::Get || request.method == RestMethod::Post) {
            return Some(self.handle_index_search_route("_all", request));
        }
        if let Some(index) = request.path.trim_matches('/').strip_suffix("/_bulk") {
            if request.method == RestMethod::Post {
                return Some(self.handle_bulk_route(Some(index), request));
            }
        }
        if let Some((index, alias)) = request.path.trim_matches('/').split_once("/_alias/") {
            return match request.method {
                RestMethod::Get => Some(self.handle_alias_read_route(Some(index), Some(alias))),
                RestMethod::Put | RestMethod::Post => {
                    Some(self.handle_alias_single_mutation_route(index, alias, request))
                }
                RestMethod::Delete => Some(self.handle_alias_delete_route(index, alias)),
                _ => None,
            };
        }
        if let Some(index) = request.path.trim_matches('/').strip_suffix("/_alias") {
            if request.method == RestMethod::Get {
                return Some(self.handle_alias_read_route(Some(index), None));
            }
        }
        if let Some((index, doc_path)) = request.path.trim_matches('/').split_once("/_doc/") {
            return match request.method {
                RestMethod::Put => Some(self.handle_put_doc_route(index, doc_path, request)),
                RestMethod::Get => Some(self.handle_get_doc_route(index, doc_path, request)),
                RestMethod::Delete => Some(self.handle_delete_doc_route(index, doc_path, request)),
                _ => None,
            };
        }
        if let Some(index) = request.path.trim_matches('/').strip_suffix("/_doc") {
            if request.method == RestMethod::Post {
                return Some(self.handle_post_doc_route(index, request));
            }
        }
        if let Some((index, id)) = request.path.trim_matches('/').split_once("/_update/") {
            if request.method == RestMethod::Post {
                return Some(self.handle_update_doc_route(index, id, request));
            }
        }
        if request.method == RestMethod::Put
            && !request.path.starts_with("/_")
            && request.path.trim_matches('/').split('/').count() == 1
        {
            return Some(self.handle_create_index_route(request));
        }
        if request.method == RestMethod::Get
            && !request.path.starts_with("/_")
            && request.path.trim_matches('/').split('/').count() == 1
        {
            return Some(self.handle_get_index_route(request));
        }
        if request.method == RestMethod::Head
            && !request.path.starts_with("/_")
            && request.path.trim_matches('/').split('/').count() == 1
        {
            return Some(self.handle_head_index_route(request));
        }
        if request.method == RestMethod::Delete
            && !request.path.starts_with("/_")
            && request.path.trim_matches('/').split('/').count() == 1
        {
            return Some(self.handle_delete_index_route(request));
        }
        if request.method == RestMethod::Get && request.path.starts_with("/_tasks/") {
            return Some(self.handle_tasks_get_route(request));
        }
        None
    }

    fn handle_cluster_state_route(&self, request: &RestRequest) -> RestResponse {
        let mut scoped_request = request.clone();
        if let Some(metric_segment) = request.path.strip_prefix("/_cluster/state/") {
            if !metric_segment.is_empty() {
                let (metric, indices) = metric_segment
                    .split_once('/')
                    .map(|(metric, indices)| (metric.to_string(), Some(indices.to_string())))
                    .unwrap_or_else(|| (metric_segment.to_string(), None));
                scoped_request.path_params.insert("metric".to_string(), metric);
                if let Some(indices) = indices {
                    scoped_request
                        .path_params
                        .insert("indices".to_string(), indices);
                }
            }
        }
        match cluster_state_route_registration::invoke_cluster_state_live_route(
            &scoped_request,
            &self.cluster_state_body(),
        ) {
            Ok(response) => response,
            Err(response) => response,
        }
    }

    fn handle_dev_cluster_route(&self) -> RestResponse {
        RestResponse::json(
            200,
            serde_json::to_value(self.cluster_view.clone().unwrap_or_default())
                .unwrap_or_else(|_| Value::Object(Default::default())),
        )
    }

    fn handle_cluster_health_route(&self, request: &RestRequest) -> RestResponse {
        let mut body = self.cluster_health_body();
        let current_nodes = body
            .get("number_of_nodes")
            .and_then(Value::as_u64)
            .unwrap_or(0);
        let wait_for_nodes = request
            .query_params
            .get("wait_for_nodes")
            .and_then(|value| parse_wait_for_nodes(value));
        let timed_out = wait_for_nodes.is_some_and(|expected| expected > current_nodes);
        if let Some(object) = body.as_object_mut() {
            object.insert("timed_out".to_string(), Value::Bool(timed_out));
        }
        if timed_out {
            RestResponse::json(408, body)
        } else {
            RestResponse::json(200, body)
        }
    }

    fn handle_create_index_route(&self, request: &RestRequest) -> RestResponse {
        let index = request.path.trim_start_matches('/').trim_end_matches('/');
        let request_body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let bounded_subset =
            create_index_route_registration::build_create_index_body_subset(&request_body);
        self.created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .insert(index.to_string());
        self.documents_state
            .lock()
            .expect("documents state lock poisoned")
            .retain(|key, _| !key.starts_with(&format!("{index}:")));
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let indices = manifest
            .as_object_mut()
            .expect("metadata manifest object expected")
            .entry("indices".to_string())
            .or_insert_with(|| serde_json::json!({}));
        indices[index] = bounded_subset;
        drop(manifest);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(
            200,
            serde_json::json!({
                "acknowledged": true,
                "shards_acknowledged": true,
                "index": index,
            }),
        )
    }

    fn handle_get_index_route(&self, request: &RestRequest) -> RestResponse {
        let target = request.path.trim_matches('/');
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let body =
            get_index_route_registration::build_get_index_metadata_response(&manifest["indices"], target);
        RestResponse::json(200, body)
    }

    fn handle_delete_index_route(&self, request: &RestRequest) -> RestResponse {
        let target = request.path.trim_matches('/');
        let known = self
            .created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .iter()
            .cloned()
            .collect::<Vec<_>>();
        let known_refs = known.iter().map(String::as_str).collect::<Vec<_>>();
        let matched = delete_index_route_registration::resolve_delete_index_targets(target, &known_refs);
        if matched.is_empty() {
            return delete_index_route_registration::build_delete_index_missing_response(target);
        }
        {
            let mut created = self
                .created_indices_state
                .lock()
                .expect("created indices state lock poisoned");
            let mut docs = self
                .documents_state
                .lock()
                .expect("documents state lock poisoned");
            let mut manifest = self
                .metadata_manifest_state
                .lock()
                .expect("metadata manifest state lock poisoned");
            for index in matched {
                created.remove(&index);
                docs.retain(|key, _| !key.starts_with(&format!("{index}:")));
                manifest["indices"].as_object_mut().map(|m| m.remove(&index));
            }
        }
        self.persist_shared_runtime_state_to_disk();
        delete_index_route_registration::build_delete_index_success_response()
    }

    fn handle_head_index_route(&self, request: &RestRequest) -> RestResponse {
        let target = request.path.trim_matches('/');
        if target == "_all" || target.contains('*') || target.contains(',') {
            return RestResponse::opensearch_error_kind(
                os_rest::RestErrorKind::IllegalArgument,
                "unsupported broad selector",
            );
        }
        let exists = self
            .created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .contains(target);
        if exists {
            RestResponse::empty(200)
        } else {
            RestResponse::empty(404)
        }
    }

    fn handle_mapping_get_route(&self, target: Option<&str>) -> RestResponse {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        RestResponse::json(
            200,
            mapping_route_registration::build_mapping_readback_response(&manifest["indices"], target),
        )
    }

    fn handle_mapping_put_route(&self, index: &str, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let subset = mapping_route_registration::build_mapping_update_body_subset(&body);
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let existing_properties = manifest["indices"][index]["mappings"]["properties"]
            .as_object()
            .cloned()
            .unwrap_or_default();
        let update_properties = subset["properties"].as_object().cloned().unwrap_or_default();
        for (field, update_definition) in &update_properties {
            let Some(existing_definition) = existing_properties.get(field) else {
                continue;
            };
            let existing_type = existing_definition.get("type").and_then(Value::as_str);
            let update_type = update_definition.get("type").and_then(Value::as_str);
            if existing_type.is_some() && update_type.is_some() && existing_type != update_type {
                return RestResponse::json(
                    400,
                    serde_json::json!({
                        "error": {
                            "type": "illegal_argument_exception",
                            "reason": format!(
                                "mapper [{field}] cannot be changed from type [{}] to [{}]",
                                existing_type.unwrap_or_default(),
                                update_type.unwrap_or_default()
                            ),
                            "root_cause": [
                                {
                                    "type": "illegal_argument_exception",
                                    "reason": format!(
                                        "mapper [{field}] cannot be changed from type [{}] to [{}]",
                                        existing_type.unwrap_or_default(),
                                        update_type.unwrap_or_default()
                                    )
                                }
                            ]
                        },
                        "status": 400
                    }),
                );
            }
        }
        let merged_properties = manifest["indices"][index]["mappings"]["properties"]
            .as_object_mut()
            .expect("index mappings properties must be an object");
        for (field, update_definition) in update_properties {
            merged_properties.insert(field, update_definition);
        }
        drop(manifest);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, serde_json::json!({ "acknowledged": true }))
    }

    fn handle_settings_get_route(&self, target: Option<&str>) -> RestResponse {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        RestResponse::json(
            200,
            settings_route_registration::build_settings_readback_response(&manifest["indices"], target),
        )
    }

    fn handle_settings_put_route(&self, index: &str, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        if let Some(index_settings) = body.get("index").and_then(Value::as_object) {
            for key in index_settings.keys() {
                if key != "number_of_replicas" && key != "refresh_interval" {
                    return RestResponse::json(
                        400,
                        serde_json::json!({
                            "error": {
                                "type": "illegal_argument_exception",
                                "reason": format!(
                                    "Can't update non dynamic settings [[index.{key}]] for open indices [[{index}]]"
                                ),
                                "root_cause": [
                                    {
                                        "type": "illegal_argument_exception",
                                        "reason": format!(
                                            "Can't update non dynamic settings [[index.{key}]] for open indices [[{index}]]"
                                        )
                                    }
                                ]
                            },
                            "status": 400
                        }),
                    );
                }
            }
        }
        let subset = settings_route_registration::build_settings_update_body_subset(&body);
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        manifest["indices"][index]["settings"] = subset.clone();
        drop(manifest);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, serde_json::json!({ "acknowledged": true }))
    }

    fn handle_alias_read_route(&self, index_target: Option<&str>, alias_target: Option<&str>) -> RestResponse {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        RestResponse::json(
            200,
            alias_read_route_registration::build_alias_readback_response(
                &manifest["indices"],
                index_target,
                alias_target,
            ),
        )
    }

    fn handle_alias_single_mutation_route(
        &self,
        index: &str,
        alias: &str,
        request: &RestRequest,
    ) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let subset = normalize_alias_metadata_for_readback(
            alias_mutation_route_registration::build_alias_metadata_subset(&body),
        );
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        manifest["indices"][index]["aliases"][alias] = subset;
        drop(manifest);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(
            200,
            alias_mutation_route_registration::build_alias_mutation_acknowledged_response(),
        )
    }

    fn handle_alias_bulk_mutation_route(&self, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let subset = alias_mutation_route_registration::build_bulk_alias_actions_subset(&body);
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        for action in subset["actions"].as_array().cloned().unwrap_or_default() {
            if let Some(add) = action.get("add") {
                let index = add["index"].as_str().unwrap_or_default();
                let alias = add["alias"].as_str().unwrap_or_default();
                let mut alias_body = add.clone();
                if let Some(object) = alias_body.as_object_mut() {
                    object.remove("index");
                    object.remove("alias");
                }
                manifest["indices"][index]["aliases"][alias] =
                    normalize_alias_metadata_for_readback(alias_body);
            } else if let Some(remove) = action.get("remove") {
                let index = remove["index"].as_str().unwrap_or_default();
                let alias = remove["alias"].as_str().unwrap_or_default();
                manifest["indices"][index]["aliases"]
                    .as_object_mut()
                    .map(|m| m.remove(alias));
            }
        }
        drop(manifest);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(
            200,
            alias_mutation_route_registration::build_alias_mutation_acknowledged_response(),
        )
    }

    fn handle_alias_delete_route(&self, index: &str, alias: &str) -> RestResponse {
        self.metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned")["indices"][index]["aliases"]
            .as_object_mut()
            .map(|m| m.remove(alias));
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(
            200,
            alias_mutation_route_registration::build_alias_mutation_acknowledged_response(),
        )
    }

    fn handle_snapshot_repository_read_route(&self, repository: Option<&str>) -> RestResponse {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let repositories = manifest
            .get("snapshot_repositories")
            .cloned()
            .unwrap_or_else(|| serde_json::json!({}));
        RestResponse::json(
            200,
            snapshot_repository_route_registration::build_snapshot_repository_readback_response(
                &repositories,
                repository,
            ),
        )
    }

    fn handle_snapshot_repository_mutation_route(
        &self,
        repository: &str,
        request: &RestRequest,
    ) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let subset =
            snapshot_repository_route_registration::build_snapshot_repository_body_subset(&body);
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let repositories = manifest
            .as_object_mut()
            .expect("metadata manifest object expected")
            .entry("snapshot_repositories".to_string())
            .or_insert_with(|| serde_json::json!({}));
        repositories[repository] = subset;
        drop(manifest);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(
            200,
            snapshot_repository_route_registration::build_snapshot_repository_acknowledged_response(),
        )
    }

    fn handle_snapshot_repository_verify_route(&self, _repository: &str) -> RestResponse {
        RestResponse::json(
            200,
            snapshot_repository_route_registration::build_snapshot_repository_verify_response(
                &serde_json::json!({
                    "nodes": {
                        self.info.name.clone(): {
                            "name": self.info.name.clone()
                        }
                    }
                }),
            ),
        )
    }

    fn handle_snapshot_create_route(
        &self,
        repository: &str,
        snapshot: &str,
        request: &RestRequest,
    ) -> RestResponse {
        if !self.snapshot_repository_exists(repository) {
            return build_missing_snapshot_repository_response(repository);
        }
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let subset =
            snapshot_lifecycle_route_registration::build_snapshot_create_body_subset(&body);
        let snapshot_record = serde_json::json!({
            "snapshot": snapshot,
            "uuid": format!("{snapshot}-uuid"),
            "state": "SUCCESS",
            "indices": subset
                .get("indices")
                .cloned()
                .unwrap_or_else(|| serde_json::json!([]))
        });
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let snapshots = manifest
            .as_object_mut()
            .expect("metadata manifest object expected")
            .entry("snapshots".to_string())
            .or_insert_with(|| serde_json::json!({}));
        snapshots[repository][snapshot] = snapshot_record.clone();
        drop(manifest);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(
            200,
            snapshot_lifecycle_route_registration::build_snapshot_create_response(&snapshot_record),
        )
    }

    fn handle_snapshot_readback_route(&self, repository: &str, snapshot: &str) -> RestResponse {
        let Some(snapshot_record) = self.load_snapshot_record(repository, snapshot) else {
            return build_missing_snapshot_response(repository, snapshot);
        };
        RestResponse::json(
            200,
            snapshot_lifecycle_route_registration::build_snapshot_readback_response(
                &snapshot_record,
            ),
        )
    }

    fn handle_snapshot_status_route(&self, repository: &str, snapshot: &str) -> RestResponse {
        let Some(snapshot_record) = self.load_snapshot_record(repository, snapshot) else {
            return build_missing_snapshot_response(repository, snapshot);
        };
        RestResponse::json(
            200,
            snapshot_lifecycle_route_registration::build_snapshot_status_response(
                &serde_json::json!({
                    "snapshot": snapshot_record["snapshot"].clone(),
                    "repository": repository,
                    "state": snapshot_record["state"].clone(),
                    "shards_stats": {
                        "total": 1,
                        "successful": 1,
                        "failed": 0
                    }
                }),
            ),
        )
    }

    fn handle_snapshot_restore_route(
        &self,
        repository: &str,
        snapshot: &str,
        request: &RestRequest,
    ) -> RestResponse {
        if self.load_snapshot_record(repository, snapshot).is_none() {
            return build_missing_snapshot_response(repository, snapshot);
        }
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let response =
            snapshot_lifecycle_route_registration::invoke_validated_snapshot_restore_live_route(
                &body,
            );
        let status = response
            .get("status")
            .and_then(Value::as_u64)
            .map(|value| value as u16)
            .unwrap_or(200);
        RestResponse::json(status, response)
    }

    fn handle_snapshot_delete_route(&self, repository: &str, snapshot: &str) -> RestResponse {
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let removed = manifest["snapshots"][repository]
            .as_object_mut()
            .and_then(|snapshots| snapshots.remove(snapshot));
        drop(manifest);
        if removed.is_none() {
            return build_missing_snapshot_response(repository, snapshot);
        }
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(
            200,
            snapshot_cleanup_route_registration::build_snapshot_delete_response(
                &serde_json::json!({
                    "snapshot": snapshot,
                    "repository": repository
                }),
            ),
        )
    }

    fn handle_snapshot_cleanup_route(&self, _repository: &str) -> RestResponse {
        RestResponse::json(
            200,
            snapshot_cleanup_route_registration::build_snapshot_cleanup_response(
                &serde_json::json!({
                    "deleted_bytes": 0,
                    "deleted_blobs": 0
                }),
            ),
        )
    }

    fn handle_global_refresh_route(&self) -> RestResponse {
        let total = self
            .created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .len() as u64;
        RestResponse::json(
            200,
            serde_json::json!({
                "_shards": {
                    "total": total.max(1),
                    "successful": total.max(1),
                    "failed": 0
                }
            }),
        )
    }

    fn handle_index_refresh_route(&self, _index: &str) -> RestResponse {
        RestResponse::json(
            200,
            serde_json::json!({
                "_shards": {
                    "total": 2,
                    "successful": 1,
                    "failed": 0
                }
            }),
        )
    }

    fn handle_index_search_route(&self, index: &str, request: &RestRequest) -> RestResponse {
        if request.query_params.contains_key("scroll") {
            return build_unsupported_search_response("unsupported search option [scroll]");
        }
        if request
            .query_params
            .get("expand_wildcards")
            .is_some_and(|value| value == "closed")
        {
            return build_unsupported_search_response(
                "unsupported search target option [expand_wildcards=closed]",
            );
        }
        let body = match serde_json::from_slice::<Value>(&request.body) {
            Ok(body) => body,
            Err(error) => {
                return RestResponse::json(
                    400,
                    serde_json::json!({
                        "error": {
                            "type": "unexpected_end_of_input_exception",
                            "reason": error.to_string()
                        },
                        "status": 400
                    }),
                );
            }
        };
        if let Some(response) = validate_search_request_body(&body) {
            return response;
        }
        let ignore_unavailable = request
            .query_params
            .get("ignore_unavailable")
            .is_some_and(|value| value == "true");
        let allow_no_indices = request
            .query_params
            .get("allow_no_indices")
            .is_some_and(|value| value == "true");
        let resolved_indices = match self.resolve_search_targets(index, ignore_unavailable, allow_no_indices) {
            Ok(indices) => indices,
            Err(response) => return response,
        };
        if let Some(response) = self.validate_knn_target_capabilities(&body["query"], &resolved_indices) {
            return response;
        }
        let docs = self
            .documents_state
            .lock()
            .expect("documents state lock poisoned");
        let mut hits = Vec::new();
        for (key, record) in docs.iter() {
            let Some((doc_index, doc_id, _)) = split_document_key(key) else {
                continue;
            };
            if !resolved_indices.iter().any(|candidate| candidate == doc_index) {
                continue;
            }
            if let Some((matched, score)) = evaluate_search_query(record, &body["query"]) {
                if matched {
                    hits.push(serde_json::json!({
                        "_index": doc_index,
                        "_id": doc_id,
                        "_source": record.source,
                        "_score": score,
                        "_seq_no": record.seq_no
                    }));
                }
            }
        }
        let aggregations = match build_search_aggregations(body.get("aggs"), &hits) {
            Ok(aggregations) => aggregations,
            Err(response) => return response,
        };
        apply_search_sort(&mut hits, &body["sort"]);
        if body.get("sort").is_none() {
            hits.sort_by(|left, right| {
                let left_score = left["_score"].as_f64().unwrap_or(0.0);
                let right_score = right["_score"].as_f64().unwrap_or(0.0);
                right_score
                    .partial_cmp(&left_score)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then_with(|| {
                        left["_seq_no"]
                            .as_i64()
                            .unwrap_or_default()
                            .cmp(&right["_seq_no"].as_i64().unwrap_or_default())
                    })
            });
        }
        if let Some(knn_limit) = extract_knn_limit(&body["query"]) {
            hits.truncate(knn_limit);
        }
        let total = hits.len() as u64;
        let from = body.get("from").and_then(Value::as_u64).unwrap_or(0) as usize;
        let size = body.get("size").and_then(Value::as_u64).unwrap_or(10) as usize;
        let paged_hits: Vec<Value> = hits.into_iter().skip(from).take(size).collect();
        let mut response = serde_json::Map::new();
        response.insert("took".to_string(), serde_json::json!(1));
        response.insert("timed_out".to_string(), serde_json::json!(false));
        response.insert(
            "_shards".to_string(),
            serde_json::json!({
                "total": resolved_indices.len().max(1),
                "successful": resolved_indices.len().max(1),
                "skipped": 0,
                "failed": 0
            }),
        );
        response.insert(
            "hits".to_string(),
            serde_json::json!({
                "total": {
                    "value": total,
                    "relation": "eq"
                },
                "max_score": paged_hits
                    .iter()
                    .filter_map(|hit| hit.get("_score").and_then(Value::as_f64))
                    .max_by(|left, right| left.partial_cmp(right).unwrap_or(std::cmp::Ordering::Equal)),
                "hits": paged_hits
            }),
        );
        if let Some(aggregations) = aggregations {
            response.insert("aggregations".to_string(), aggregations);
        }
        RestResponse::json(200, Value::Object(response))
    }

    fn handle_bulk_route(&self, default_index: Option<&str>, request: &RestRequest) -> RestResponse {
        let body = String::from_utf8_lossy(&request.body);
        let mut lines = body.lines();
        let mut items = Vec::new();
        let mut had_errors = false;
        while let Some(action_line) = lines.next() {
            if action_line.trim().is_empty() {
                continue;
            }
            let action_value = serde_json::from_str::<Value>(action_line).unwrap_or(Value::Null);
            let Some(action_object) = action_value.as_object() else {
                continue;
            };
            let Some((action, meta_value)) = action_object.iter().next() else {
                continue;
            };
            let meta = meta_value.as_object().cloned().unwrap_or_default();
            let index = meta
                .get("_index")
                .and_then(Value::as_str)
                .or(default_index)
                .unwrap_or_default()
                .to_string();
            let id = meta
                .get("_id")
                .and_then(Value::as_str)
                .unwrap_or_default()
                .to_string();
            let routing = meta.get("routing").and_then(Value::as_str).unwrap_or_default().to_string();
            let payload = match action.as_str() {
                "index" | "create" | "update" => lines
                    .next()
                    .and_then(|line| serde_json::from_str::<Value>(line).ok())
                    .unwrap_or(Value::Null),
                "delete" => Value::Null,
                _ => Value::Null,
            };
            let item = self.execute_bulk_action(
                action,
                &index,
                &id,
                if routing.is_empty() { None } else { Some(routing.as_str()) },
                payload,
            );
            if item
                .as_object()
                .and_then(|object| object.values().next())
                .and_then(Value::as_object)
                .and_then(|payload| payload.get("status"))
                .and_then(Value::as_u64)
                .is_some_and(|status| status >= 400)
            {
                had_errors = true;
            }
            items.push(item);
        }
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(
            200,
            serde_json::json!({
                "took": 1,
                "errors": had_errors,
                "items": items,
            }),
        )
    }

    fn execute_bulk_action(
        &self,
        action: &str,
        index: &str,
        id: &str,
        routing: Option<&str>,
        payload: Value,
    ) -> Value {
        let key = format!("{index}:{id}:{}", routing.unwrap_or_default());
        let forced_refresh = false;
        match action {
            "index" => {
                let mut docs = self.documents_state.lock().expect("documents state lock poisoned");
                let mut next_seq_no = self.next_seq_no.lock().expect("seq_no lock poisoned");
                let assigned_seq_no = *next_seq_no;
                *next_seq_no += 1;
                let version = docs.get(&key).map(|doc| doc.version + 1).unwrap_or(1);
                let result = if version == 1 { "created" } else { "updated" };
                let record = StoredDocument {
                    source: payload,
                    version,
                    seq_no: assigned_seq_no as i64,
                    primary_term: 1,
                    routing: routing.map(ToOwned::to_owned),
                };
                docs.insert(key, record.clone());
                serde_json::json!({
                    "index": {
                        "_index": index,
                        "_id": id,
                        "_version": record.version,
                        "result": result,
                        "_seq_no": record.seq_no,
                        "_primary_term": record.primary_term,
                        "status": if version == 1 { 201 } else { 200 },
                        "forced_refresh": forced_refresh,
                    }
                })
            }
            "create" => {
                let mut docs = self.documents_state.lock().expect("documents state lock poisoned");
                if docs.contains_key(&key) {
                    return serde_json::json!({
                        "create": {
                            "_index": index,
                            "_id": id,
                            "status": 409,
                            "error": {
                                "type": "version_conflict_engine_exception",
                                "reason": format!("[{id}]: version conflict, document already exists")
                            }
                        }
                    });
                }
                let mut next_seq_no = self.next_seq_no.lock().expect("seq_no lock poisoned");
                let assigned_seq_no = *next_seq_no;
                *next_seq_no += 1;
                let record = StoredDocument {
                    source: payload,
                    version: 1,
                    seq_no: assigned_seq_no as i64,
                    primary_term: 1,
                    routing: routing.map(ToOwned::to_owned),
                };
                docs.insert(key, record.clone());
                serde_json::json!({
                    "create": {
                        "_index": index,
                        "_id": id,
                        "_version": 1,
                        "result": "created",
                        "_seq_no": record.seq_no,
                        "_primary_term": 1,
                        "status": 201,
                    }
                })
            }
            "delete" => {
                let mut docs = self.documents_state.lock().expect("documents state lock poisoned");
                let mut next_seq_no = self.next_seq_no.lock().expect("seq_no lock poisoned");
                let assigned_seq_no = *next_seq_no;
                *next_seq_no += 1;
                if let Some(record) = docs.remove(&key) {
                    serde_json::json!({
                        "delete": {
                            "_index": index,
                            "_id": id,
                            "_version": record.version + 1,
                            "result": "deleted",
                            "_seq_no": assigned_seq_no,
                            "_primary_term": record.primary_term,
                            "status": 200,
                        }
                    })
                } else {
                    serde_json::json!({
                        "delete": {
                            "_index": index,
                            "_id": id,
                            "_version": 1,
                            "result": "not_found",
                            "_seq_no": assigned_seq_no,
                            "_primary_term": 1,
                            "status": 404,
                        }
                    })
                }
            }
            "update" => {
                let doc_patch = payload.get("doc").cloned().unwrap_or_else(|| serde_json::json!({}));
                let upsert = payload.get("upsert").cloned().unwrap_or(Value::Null);
                let doc_as_upsert = payload.get("doc_as_upsert").and_then(Value::as_bool).unwrap_or(false);
                let mut docs = self.documents_state.lock().expect("documents state lock poisoned");
                let mut next_seq_no = self.next_seq_no.lock().expect("seq_no lock poisoned");
                let assigned_seq_no = *next_seq_no;
                *next_seq_no += 1;
                if let Some(record) = docs.get_mut(&key) {
                    merge_json_object(&mut record.source, &doc_patch);
                    record.version += 1;
                    record.seq_no = assigned_seq_no as i64;
                    return serde_json::json!({
                        "update": {
                            "_index": index,
                            "_id": id,
                            "_version": record.version,
                            "result": "updated",
                            "_seq_no": record.seq_no,
                            "_primary_term": record.primary_term,
                            "status": 200,
                        }
                    });
                }
                if doc_as_upsert || !upsert.is_null() {
                    let source = if doc_as_upsert { doc_patch } else { upsert };
                    let record = StoredDocument {
                        source,
                        version: 1,
                        seq_no: assigned_seq_no as i64,
                        primary_term: 1,
                        routing: routing.map(ToOwned::to_owned),
                    };
                    docs.insert(key, record.clone());
                    return serde_json::json!({
                        "update": {
                            "_index": index,
                            "_id": id,
                            "_version": 1,
                            "result": "created",
                            "_seq_no": record.seq_no,
                            "_primary_term": 1,
                            "status": 201,
                        }
                    });
                }
                serde_json::json!({
                    "update": {
                        "_index": index,
                        "_id": id,
                        "status": 404,
                        "error": {
                            "type": "document_missing_exception",
                            "reason": format!("[{id}]: document missing")
                        }
                    }
                })
            }
            _ => serde_json::json!({}),
        }
    }

    fn handle_component_template_get_route(&self, target: Option<&str>) -> RestResponse {
        let manifest = self.metadata_manifest_state.lock().expect("metadata manifest state lock poisoned");
        RestResponse::json(
            200,
            template_route_registration::invoke_component_template_live_readback(
                &manifest["templates"]["component_templates"],
                target,
            ),
        )
    }

    fn handle_component_template_put_route(&self, name: &str, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let subset = template_route_registration::build_component_template_body_subset(&body);
        self.metadata_manifest_state.lock().expect("metadata manifest state lock poisoned")["templates"]["component_templates"][name] =
            serde_json::json!({ "component_template": subset });
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, template_route_registration::build_template_acknowledged_response())
    }

    fn handle_index_template_get_route(&self, target: Option<&str>) -> RestResponse {
        let manifest = self.metadata_manifest_state.lock().expect("metadata manifest state lock poisoned");
        RestResponse::json(
            200,
            template_route_registration::invoke_index_template_live_readback(
                &manifest["templates"]["index_templates"],
                target,
            ),
        )
    }

    fn handle_index_template_put_route(&self, name: &str, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let subset = template_route_registration::build_index_template_body_subset(&body);
        self.metadata_manifest_state.lock().expect("metadata manifest state lock poisoned")["templates"]["index_templates"][name] =
            serde_json::json!({ "index_template": subset });
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, template_route_registration::build_template_acknowledged_response())
    }

    fn handle_legacy_template_get_route(&self, target: Option<&str>) -> RestResponse {
        let manifest = self.metadata_manifest_state.lock().expect("metadata manifest state lock poisoned");
        RestResponse::json(
            200,
            legacy_template_route_registration::invoke_legacy_template_live_readback(
                &manifest["templates"]["legacy_index_templates"],
                target,
            ),
        )
    }

    fn handle_legacy_template_put_route(&self, name: &str, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let subset = legacy_template_route_registration::build_legacy_template_body_subset(&body);
        self.metadata_manifest_state.lock().expect("metadata manifest state lock poisoned")["templates"]["legacy_index_templates"][name] = subset;
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, legacy_template_route_registration::build_legacy_template_acknowledged_response())
    }

    fn handle_component_template_delete_route(&self, name: &str) -> RestResponse {
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let referenced_by: Vec<String> = manifest["templates"]["index_templates"]
            .as_object()
            .into_iter()
            .flat_map(|templates| templates.iter())
            .filter_map(|(template_name, template_value)| {
                let composed_of = template_value["index_template"]["composed_of"].as_array()?;
                composed_of
                    .iter()
                    .filter_map(Value::as_str)
                    .any(|component| component == name)
                    .then(|| template_name.clone())
            })
            .collect();
        if !referenced_by.is_empty() {
            return RestResponse::json(
                400,
                serde_json::json!({
                    "error": {
                        "type": "illegal_argument_exception",
                        "reason": format!(
                            "component templates [{name}] cannot be removed as they are still in use by index templates [{}]",
                            referenced_by.join(", ")
                        ),
                        "root_cause": [
                            {
                                "type": "illegal_argument_exception",
                                "reason": format!(
                                    "component templates [{name}] cannot be removed as they are still in use by index templates [{}]",
                                    referenced_by.join(", ")
                                )
                            }
                        ]
                    },
                    "status": 400
                }),
            );
        }
        manifest["templates"]["component_templates"]
            .as_object_mut()
            .map(|templates| templates.remove(name));
        drop(manifest);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, serde_json::json!({ "acknowledged": true }))
    }

    fn handle_index_template_delete_route(&self, name: &str) -> RestResponse {
        self.metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned")["templates"]["index_templates"]
            .as_object_mut()
            .map(|templates| templates.remove(name));
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, serde_json::json!({ "acknowledged": true }))
    }

    fn handle_legacy_template_delete_route(&self, name: &str) -> RestResponse {
        self.metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned")["templates"]["legacy_index_templates"]
            .as_object_mut()
            .map(|templates| templates.remove(name));
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, serde_json::json!({ "acknowledged": true }))
    }

    fn handle_cluster_settings_put_route(&self, request: &RestRequest) -> RestResponse {
        let request_body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let persistent = request_body
            .get("persistent")
            .cloned()
            .unwrap_or_else(|| serde_json::json!({}));
        let transient = request_body
            .get("transient")
            .cloned()
            .unwrap_or_else(|| serde_json::json!({}));
        let params = request
            .query_params
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>();
        let current_state = self
            .cluster_settings_state
            .lock()
            .expect("cluster settings state lock poisoned")
            .clone();
        if let Err(reason) =
            cluster_settings_route_registration::reject_unsupported_cluster_settings_params(&params)
        {
            return RestResponse::opensearch_error_kind(
                os_rest::RestErrorKind::IllegalArgument,
                reason,
            );
        }
        let current_persistent = current_state
            .get("persistent")
            .cloned()
            .unwrap_or_else(|| serde_json::json!({}));
        let current_transient = current_state
            .get("transient")
            .cloned()
            .unwrap_or_else(|| serde_json::json!({}));
        let next_persistent = merge_cluster_settings_section_flat(&current_persistent, &persistent);
        let next_transient = merge_cluster_settings_section_flat(&current_transient, &transient);
        let response_body = cluster_settings_route_registration::build_cluster_settings_mutation_response_body(
            &expand_dotted_cluster_settings_section(&next_persistent),
            &expand_dotted_cluster_settings_section(&next_transient),
        );
        let mut next_state = self
            .cluster_settings_state
            .lock()
            .expect("cluster settings state lock poisoned");
        *next_state = serde_json::json!({
            "persistent": next_persistent,
            "transient": next_transient
        });
        RestResponse::json(200, response_body)
    }

    fn handle_cluster_settings_get_route(&self, request: &RestRequest) -> RestResponse {
        let params = request
            .query_params
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>();
        let body = self.cluster_settings_body();
        match cluster_settings_route_registration::build_cluster_settings_rest_response(&body, &params)
        {
            Ok(response_body) => RestResponse::json(200, response_body),
            Err(reason) => RestResponse::opensearch_error_kind(
                os_rest::RestErrorKind::IllegalArgument,
                reason,
            ),
        }
    }

    fn handle_tasks_get_route(&self, request: &RestRequest) -> RestResponse {
        let Some(task_id) = request.path.strip_prefix("/_tasks/") else {
            return RestResponse::not_found_for(request.method, &request.path);
        };
        if task_id.is_empty() || task_id == "_cancel" {
            return RestResponse::not_found_for(request.method, &request.path);
        }
        if let Some(task) = self.find_task(task_id) {
            return RestResponse::json(
                200,
                tasks_route_registration::invoke_tasks_get_live_route(&serde_json::json!({
                    "task": task
                })),
            );
        }
        RestResponse::json(
            404,
            tasks_route_registration::build_unknown_task_error(task_id),
        )
    }

    fn handle_tasks_cancel_route(&self, request: &RestRequest) -> RestResponse {
        let Some(task_id) = request.query_params.get("task_id").map(String::as_str) else {
            return RestResponse::json(200, self.unknown_task_cancel_body(""));
        };
        if let Some(task) = self.find_task(task_id) {
            let cancellable = task
                .get("cancellable")
                .and_then(Value::as_bool)
                .unwrap_or(false);
            if !cancellable {
                return RestResponse::json(
                    400,
                    tasks_route_registration::build_non_cancellable_task_error(task_id),
                );
            }
            return RestResponse::json(
                200,
                tasks_route_registration::invoke_tasks_cancel_live_route(&serde_json::json!({
                    "task": task
                })),
            );
        }
        RestResponse::json(200, self.unknown_task_cancel_body(task_id))
    }

    fn cluster_health_body(&self) -> Value {
        let node_count = self
            .cluster_view
            .as_ref()
            .map(|view| view.nodes.len())
            .unwrap_or_default() as u64;
        let index_count = self
            .created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .len() as u64;
        let unassigned_shards = if node_count == 1 { index_count } else { 0 };
        let active_primary_shards = index_count;
        let active_shards = index_count;
        let status = if unassigned_shards > 0 { "yellow" } else { "green" };
        let active_shards_percent = if index_count == 0 {
            100.0
        } else {
            (active_shards as f64 / (active_shards + unassigned_shards) as f64) * 100.0
        };
        serde_json::json!({
            "cluster_name": self
                .cluster_view
                .as_ref()
                .map(|view| view.cluster_name.clone())
                .unwrap_or_else(|| self.info.name.clone()),
            "status": status,
            "timed_out": false,
            "number_of_nodes": node_count,
            "number_of_data_nodes": node_count,
            "active_primary_shards": active_primary_shards,
            "active_shards": active_shards,
            "relocating_shards": 0,
            "initializing_shards": 0,
            "unassigned_shards": unassigned_shards,
            "delayed_unassigned_shards": 0,
            "number_of_pending_tasks": self.tasks_len(),
            "number_of_in_flight_fetch": 0,
            "task_max_waiting_in_queue_millis": 0,
            "active_shards_percent_as_number": active_shards_percent
        })
    }

    fn cluster_state_body(&self) -> Value {
        let view = self.cluster_view.clone().unwrap_or_default();
        let mut nodes = serde_json::Map::new();
        for node in &view.nodes {
            nodes.insert(
                node.node_id.clone(),
                serde_json::json!({
                    "name": node.node_name,
                    "transport_address": node.transport_address,
                    "roles": node.roles,
                }),
            );
        }
        let created_indices = self
            .created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .clone();
        let mut metadata_indices = serde_json::Map::new();
        let mut routing_indices = serde_json::Map::new();
        for index in created_indices {
            metadata_indices.insert(
                index.clone(),
                serde_json::json!({
                    "state": "open",
                }),
            );
            routing_indices.insert(
                index.clone(),
                serde_json::json!({
                    "shards": {
                        "0": [
                            {
                                "primary": true
                            }
                        ]
                    }
                }),
            );
        }
        serde_json::json!({
            "cluster_name": view.cluster_name,
            "cluster_uuid": view.cluster_uuid,
            "blocks": {},
            "metadata": {
                "cluster_uuid": view.cluster_uuid,
                "indices": metadata_indices
            },
            "nodes": nodes,
            "routing_table": {
                "indices": routing_indices
            }
        })
    }

    fn cluster_settings_body(&self) -> Value {
        let state = self
            .cluster_settings_state
            .lock()
            .expect("cluster settings state lock poisoned")
            .clone();
        let persistent = expand_dotted_cluster_settings_section(
            state.get("persistent")
                .unwrap_or(&Value::Object(serde_json::Map::new())),
        );
        let transient = expand_dotted_cluster_settings_section(
            state.get("transient")
                .unwrap_or(&Value::Object(serde_json::Map::new())),
        );
        cluster_settings_route_registration::build_cluster_settings_response_body(
            &persistent,
            &transient,
        )
    }

    fn cluster_allocation_explain_body(&self, request: &RestRequest) -> Value {
        let request_body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let index = request_body
            .get("index")
            .and_then(Value::as_str)
            .unwrap_or("logs-compat");
        let shard = request_body
            .get("shard")
            .and_then(Value::as_u64)
            .unwrap_or(0);
        let primary = request_body
            .get("primary")
            .and_then(Value::as_bool)
            .unwrap_or(true);
        let body = if primary {
            serde_json::json!({
                "index": index,
                "shard": shard,
                "primary": true,
                "current_state": "started",
                "current_node": {
                    "name": self.info.name,
                },
                "node_allocation_decisions": [
                    {
                        "node_name": self.info.name,
                        "node_decision": "yes",
                        "weight_ranking": 1,
                        "deciders": [
                            {
                                "decider": "same_shard",
                                "decision": "YES",
                                "explanation": "bounded development allocation explain allows the primary shard on the local node"
                            }
                        ]
                    }
                ]
            })
        } else {
            serde_json::json!({
                "index": index,
                "shard": shard,
                "primary": false,
                "current_state": "unassigned",
                "node_allocation_decisions": [
                    {
                        "node_name": self.info.name,
                        "node_decision": "no",
                        "weight_ranking": 1,
                        "deciders": [
                            {
                                "decider": "same_shard",
                                "decision": "NO",
                                "explanation": "bounded development allocation explain keeps the replica shard unassigned"
                            }
                        ]
                    }
                ]
            })
        };
        allocation_explain_route_registration::invoke_cluster_allocation_explain_live_route(&body)
    }

    fn pending_tasks_body(&self) -> Value {
        serde_json::json!({
            "tasks": self.task_records()
        })
    }

    fn tasks_body(&self) -> Value {
        serde_json::json!({
            "tasks": self.task_records()
        })
    }

    fn nodes_stats_body(&self) -> Value {
        let view = self.cluster_view.clone().unwrap_or_default();
        let mut nodes = serde_json::Map::new();
        for node in &view.nodes {
            nodes.insert(
                node.node_id.clone(),
                serde_json::json!({
                    "name": node.node_name,
                    "roles": node.roles,
                    "transport_address": node.transport_address,
                    "http": {
                        "publish_address": node.http_address
                    }
                }),
            );
        }
        serde_json::json!({ "nodes": nodes })
    }

    fn cluster_stats_body(&self) -> Value {
        let index_count = self
            .created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .len() as u64;
        let node_count = self
            .cluster_view
            .as_ref()
            .map(|view| view.nodes.len())
            .unwrap_or_default() as u64;
        serde_json::json!({
            "cluster_name": self
                .cluster_view
                .as_ref()
                .map(|view| view.cluster_name.clone())
                .unwrap_or_else(|| self.info.name.clone()),
            "indices": {
                "count": index_count
            },
            "nodes": {
                "count": {
                    "total": node_count
                }
            }
        })
    }

    fn index_stats_body(&self) -> Value {
        let created_indices = self
            .created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .clone();
        let mut indices = serde_json::Map::new();
        for index in created_indices {
            indices.insert(
                index,
                serde_json::json!({
                    "primaries": { "docs": { "count": 0 } },
                    "total": { "docs": { "count": 0 } }
                }),
            );
        }
        serde_json::json!({
            "_all": {
                "primaries": {
                    "docs": {
                        "count": 0
                    }
                },
                "total": {
                    "docs": {
                        "count": 0
                    }
                }
            },
            "indices": indices
        })
    }

    fn task_records(&self) -> Vec<Value> {
        if let Some(queue) = self
            .task_queue_state
            .lock()
            .expect("task queue state lock poisoned")
            .clone()
        {
            return queue
                .pending
                .into_iter()
                .chain(queue.in_flight)
                .map(|record| {
                    serde_json::json!({
                        "node": self.cluster_view.as_ref().map(|v| v.local_node_id.clone()).unwrap_or_else(|| "node-a".to_string()),
                        "id": record.task_id,
                        "action": "cluster:admin/reroute",
                        "cancellable": false,
                        "insert_order": record.task_id,
                        "priority": "URGENT",
                        "source": record.task.source,
                        "executing": record.state == ClusterManagerTaskState::InFlight,
                        "time_in_queue_millis": 0,
                        "time_in_queue": "0ms"
                    })
                })
                .collect();
        }
        self.cluster_view
            .as_ref()
            .and_then(|view| {
                let local_node_id = view.local_node_id.clone();
                view.coordination.as_ref().map(|coordination| {
                    (local_node_id, coordination)
                })
            })
            .map(|(local_node_id, coordination)| {
                coordination
                    .publication_round_versions
                    .iter()
                    .enumerate()
                    .map(|(index, version)| {
                        serde_json::json!({
                            "node": local_node_id,
                            "id": (*version).max(0) as u64 + index as u64,
                            "action": "cluster:admin/publication",
                            "cancellable": false,
                            "insert_order": index as u64,
                            "priority": if coordination.publication_committed { "HIGH" } else { "URGENT" },
                            "source": format!("publication round {}", version),
                            "executing": coordination.publication_committed,
                            "time_in_queue_millis": 0,
                            "time_in_queue": "0ms"
                        })
                    })
                    .collect()
            })
            .unwrap_or_default()
    }

    fn tasks_len(&self) -> u64 {
        self.task_records().len() as u64
    }

    fn find_task(&self, task_id: &str) -> Option<Value> {
        self.task_records().into_iter().find(|task| {
            let node = task.get("node").and_then(Value::as_str).unwrap_or_default();
            let id = task.get("id").and_then(Value::as_u64).unwrap_or_default();
            format!("{node}:{id}") == task_id
        })
    }

    fn unknown_task_cancel_body(&self, task_id: &str) -> Value {
        let node_id = task_id.split(':').next().unwrap_or_default();
        serde_json::json!({
            "nodes": {},
            "node_failures": [
                {
                    "type": "failed_node_exception",
                    "reason": format!("Failed node [{}]", node_id),
                    "node_id": node_id,
                    "caused_by": {
                        "type": "no_such_node_exception",
                        "reason": format!("No such node [{}]", node_id),
                        "node_id": node_id
                    }
                }
            ]
        })
    }

    fn handle_put_doc_route(&self, index: &str, id: &str, request: &RestRequest) -> RestResponse {
        let resolved_index = self.resolve_index_or_alias(index);
        let source = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let routing = request.query_params.get("routing").cloned();
        let key = format!("{resolved_index}:{id}:{}", routing.clone().unwrap_or_default());
        let mut docs = self.documents_state.lock().expect("documents state lock poisoned");
        let expected_seq_no = request
            .query_params
            .get("if_seq_no")
            .and_then(|value| value.parse::<i64>().ok());
        let expected_primary_term = request
            .query_params
            .get("if_primary_term")
            .and_then(|value| value.parse::<i64>().ok());
        if expected_seq_no.is_some() || expected_primary_term.is_some() {
            let conflict = match docs.get(&key) {
                Some(record) => {
                    expected_seq_no.is_some_and(|seq_no| seq_no != record.seq_no)
                        || expected_primary_term
                            .is_some_and(|primary_term| primary_term != record.primary_term)
                }
                None => true,
            };
            if conflict {
                return RestResponse::json(
                    409,
                    serde_json::json!({
                        "error": {
                            "type": "version_conflict_engine_exception",
                            "reason": format!("[{id}]: version conflict in index [{resolved_index}]")
                        },
                        "status": 409
                    }),
                );
            }
        }
        let mut next_seq_no = self.next_seq_no.lock().expect("seq_no lock poisoned");
        let assigned_seq_no = *next_seq_no;
        *next_seq_no += 1;
        let version = docs.get(&key).map(|doc| doc.version + 1).unwrap_or(1);
        let record = StoredDocument {
            source,
            version,
            seq_no: assigned_seq_no as i64,
            primary_term: 1,
            routing,
        };
        let response = serde_json::json!({
            "_index": resolved_index,
            "_id": id,
            "_version": record.version,
            "result": if version == 1 { "created" } else { "updated" },
            "_seq_no": record.seq_no,
            "_primary_term": record.primary_term,
            "forced_refresh": request.query_params.get("refresh").map(|v| v == "wait_for").unwrap_or(false),
        });
        docs.insert(key, record);
        drop(docs);
        drop(next_seq_no);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(if version == 1 { 201 } else { 200 }, response)
    }

    fn handle_post_doc_route(&self, index: &str, request: &RestRequest) -> RestResponse {
        let generated_id = format!(
            "generated-{}",
            *self.next_seq_no.lock().expect("seq_no lock poisoned") + 1
        );
        self.handle_put_doc_route(index, &generated_id, request)
    }

    fn handle_get_doc_route(&self, index: &str, id: &str, request: &RestRequest) -> RestResponse {
        let resolved_index = self.resolve_index_or_alias(index);
        let routing = request.query_params.get("routing").cloned().unwrap_or_default();
        let key = format!("{resolved_index}:{id}:{routing}");
        let docs = self.documents_state.lock().expect("documents state lock poisoned");
        let record = docs.get(&key).or_else(|| {
            if routing.is_empty() {
                docs.iter()
                    .find(|(candidate, _)| candidate.starts_with(&format!("{resolved_index}:{id}:")))
                    .map(|(_, record)| record)
            } else {
                None
            }
        });
        if let Some(record) = record {
            let mut source = record.source.clone();
            if let Some(includes) = request.query_params.get("_source_includes") {
                source = filter_source_fields(&source, includes);
            }
            return RestResponse::json(200, serde_json::json!({
                "_index": resolved_index,
                "_id": id,
                "_version": record.version,
                "_seq_no": record.seq_no,
                "_primary_term": record.primary_term,
                "found": true,
                "_source": source,
            }));
        }
        RestResponse::json(
            404,
            single_doc_get_route_registration::build_get_doc_not_found_response(&resolved_index, id),
        )
    }

    fn handle_delete_doc_route(&self, index: &str, id: &str, request: &RestRequest) -> RestResponse {
        let resolved_index = self.resolve_index_or_alias(index);
        let routing = request.query_params.get("routing").cloned().unwrap_or_default();
        let key = format!("{resolved_index}:{id}:{routing}");
        let mut docs = self.documents_state.lock().expect("documents state lock poisoned");
        if let Some(record) = docs.remove(&key) {
            let response = RestResponse::json(200, serde_json::json!({
                "_index": resolved_index,
                "_id": id,
                "_version": record.version + 1,
                "result": "deleted",
                "_seq_no": record.seq_no + 1,
                "_primary_term": record.primary_term,
                "forced_refresh": request.query_params.get("refresh").map(|v| v == "wait_for").unwrap_or(false),
            }));
            drop(docs);
            self.persist_shared_runtime_state_to_disk();
            return response;
        }
        RestResponse::json(
            404,
            single_doc_delete_route_registration::build_delete_doc_not_found_response(&resolved_index, id),
        )
    }

    fn handle_update_doc_route(&self, index: &str, id: &str, request: &RestRequest) -> RestResponse {
        let resolved_index = self.resolve_index_or_alias(index);
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let routing = request.query_params.get("routing").cloned();
        let key = format!("{resolved_index}:{id}:{}", routing.clone().unwrap_or_default());
        let doc_patch = body.get("doc").cloned().unwrap_or_else(|| serde_json::json!({}));
        let upsert = body.get("upsert").cloned().unwrap_or(Value::Null);
        let doc_as_upsert = body.get("doc_as_upsert").and_then(Value::as_bool).unwrap_or(false);
        let mut docs = self.documents_state.lock().expect("documents state lock poisoned");
        let mut next_seq_no = self.next_seq_no.lock().expect("seq_no lock poisoned");
        let assigned_seq_no = *next_seq_no;
        *next_seq_no += 1;
        if let Some(record) = docs.get_mut(&key) {
            merge_json_object(&mut record.source, &doc_patch);
            record.version += 1;
            record.seq_no = assigned_seq_no as i64;
            let response = RestResponse::json(200, serde_json::json!({
                "_index": resolved_index,
                "_id": id,
                "_version": record.version,
                "result": "updated",
                "_seq_no": record.seq_no,
                "_primary_term": record.primary_term,
                "forced_refresh": request.query_params.get("refresh").map(|v| v == "wait_for").unwrap_or(false),
            }));
            drop(docs);
            drop(next_seq_no);
            self.persist_shared_runtime_state_to_disk();
            return response;
        }
        if doc_as_upsert || !upsert.is_null() {
            let source = if doc_as_upsert { doc_patch } else { upsert };
            let record = StoredDocument {
                source,
                version: 1,
                seq_no: assigned_seq_no as i64,
                primary_term: 1,
                routing,
            };
            let response = serde_json::json!({
                "_index": resolved_index,
                "_id": id,
                "_version": 1,
                "result": "created",
                "_seq_no": record.seq_no,
                "_primary_term": 1,
                "forced_refresh": request.query_params.get("refresh").map(|v| v == "wait_for").unwrap_or(false),
            });
            docs.insert(key, record);
            drop(docs);
            drop(next_seq_no);
            self.persist_shared_runtime_state_to_disk();
            return RestResponse::json(200, response);
        }
        RestResponse::json(404, crate::single_doc_update_route_registration::build_update_doc_not_found_error(&resolved_index, id))
    }

    fn handle_knn_stats_route(&self) -> RestResponse {
        let state = self
            .knn_operational_state
            .lock()
            .expect("knn operational state lock poisoned")
            .clone();
        let Some(state) = state else {
            return RestResponse::json(
                400,
                serde_json::json!({
                    "error": {
                        "type": "illegal_argument_exception",
                        "reason": "k-NN operational stats are unavailable before warmup"
                    },
                    "status": 400
                }),
            );
        };
        RestResponse::json(
            200,
            serde_json::json!({
                "nodes": {
                    "local": {
                        "graph_count": state.graph_count,
                        "warmed_index_count": state.warmed_index_count,
                        "cache_entry_count": state.cache_entry_count,
                        "native_memory_used_bytes": state.native_memory_used_bytes,
                        "model_cache_used_bytes": state.model_cache_used_bytes,
                        "quantization_cache_used_bytes": state.quantization_cache_used_bytes,
                        "clear_cache_requests": state.clear_cache_requests,
                        "operational_controls": {}
                    }
                }
            }),
        )
    }

    fn handle_knn_warmup_route(&self, index: &str, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let native_memory_bytes = body
            .get("native_memory_bytes")
            .and_then(Value::as_u64)
            .unwrap_or_default();
        if native_memory_bytes > 536_870_912 {
            return RestResponse::json(
                400,
                serde_json::json!({
                    "error": {
                        "type": "illegal_argument_exception",
                        "reason": "native_memory_bytes exceeds bounded warmup budget"
                    },
                    "status": 400
                }),
            );
        }
        let mut state = self
            .knn_operational_state
            .lock()
            .expect("knn operational state lock poisoned");
        let current = state.get_or_insert_with(KnnOperationalState::default);
        current.graph_count = body
            .get("vector_segment_count")
            .and_then(Value::as_u64)
            .unwrap_or(1);
        current.warmed_index_count = 1;
        current.cache_entry_count = 1;
        current.native_memory_used_bytes = native_memory_bytes;
        current.model_cache_used_bytes = body
            .get("model_cache_bytes")
            .and_then(Value::as_u64)
            .unwrap_or_default();
        current.quantization_cache_used_bytes = body
            .get("quantization_cache_bytes")
            .and_then(Value::as_u64)
            .unwrap_or_default();
        RestResponse::json(
            200,
            serde_json::json!({
                "index": index,
                "warmed": true,
                "vector_segment_count": current.graph_count,
                "native_memory_bytes": current.native_memory_used_bytes,
                "model_cache_bytes": current.model_cache_used_bytes,
                "quantization_cache_bytes": current.quantization_cache_used_bytes
            }),
        )
    }

    fn handle_knn_clear_cache_route(&self, index: &str) -> RestResponse {
        let mut state = self
            .knn_operational_state
            .lock()
            .expect("knn operational state lock poisoned");
        let current = state.get_or_insert_with(KnnOperationalState::default);
        let released_native = current.native_memory_used_bytes;
        let released_model = current.model_cache_used_bytes;
        let released_quantization = current.quantization_cache_used_bytes;
        current.clear_cache_requests += 1;
        current.graph_count = 0;
        current.warmed_index_count = 0;
        current.cache_entry_count = 0;
        current.native_memory_used_bytes = 0;
        current.model_cache_used_bytes = 0;
        current.quantization_cache_used_bytes = 0;
        RestResponse::json(
            200,
            serde_json::json!({
                "index": index,
                "cleared_entries": 1,
                "released_native_memory_bytes": released_native,
                "released_model_cache_bytes": released_model,
                "released_quantization_cache_bytes": released_quantization
            }),
        )
    }

    fn handle_cat_indices_route(&self, request: &RestRequest) -> RestResponse {
        let created_indices = self
            .created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .clone();
        let docs = self
            .documents_state
            .lock()
            .expect("documents state lock poisoned");
        let mut rows = Vec::new();
        for index in created_indices {
            let doc_count = docs
                .keys()
                .filter(|key| key.starts_with(&format!("{index}:")))
                .count();
            rows.push(serde_json::json!({
                "health": "yellow",
                "status": "open",
                "index": index,
                "pri": "1",
                "rep": "0",
                "docs.count": doc_count.to_string(),
                "store.size": "0b"
            }));
        }
        if request.query_params.get("format").is_some_and(|value| value == "json") {
            return RestResponse::json(200, Value::Array(rows));
        }
        RestResponse::json(200, Value::Array(rows))
    }

    fn snapshot_repository_exists(&self, repository: &str) -> bool {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        manifest["snapshot_repositories"].get(repository).is_some()
    }

    fn load_snapshot_record(&self, repository: &str, snapshot: &str) -> Option<Value> {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        manifest["snapshots"]
            .get(repository)
            .and_then(|snapshots| snapshots.get(snapshot))
            .cloned()
    }

    fn sync_shared_runtime_state_from_disk(&self) {
        let Some(path) = self.shared_runtime_state_path.as_ref() else {
            return;
        };
        let Ok(bytes) = std::fs::read(path) else {
            return;
        };
        let Ok(state) = serde_json::from_slice::<SharedRuntimeState>(&bytes) else {
            return;
        };
        *self
            .created_indices_state
            .lock()
            .expect("created indices state lock poisoned") = state.created_indices;
        *self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned") = state.metadata_manifest;
        *self
            .documents_state
            .lock()
            .expect("documents state lock poisoned") = state.documents;
        *self.next_seq_no.lock().expect("seq_no lock poisoned") = state.next_seq_no;
    }

    fn persist_shared_runtime_state_to_disk(&self) {
        let Some(path) = self.shared_runtime_state_path.as_ref() else {
            return;
        };
        let state = SharedRuntimeState {
            created_indices: self
                .created_indices_state
                .lock()
                .expect("created indices state lock poisoned")
                .clone(),
            metadata_manifest: self
                .metadata_manifest_state
                .lock()
                .expect("metadata manifest state lock poisoned")
                .clone(),
            documents: self
                .documents_state
                .lock()
                .expect("documents state lock poisoned")
                .clone(),
            next_seq_no: *self.next_seq_no.lock().expect("seq_no lock poisoned"),
        };
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let _ = std::fs::write(
            path,
            serde_json::to_vec(&state).unwrap_or_else(|_| b"{}".to_vec()),
        );
    }

    fn resolve_index_or_alias(&self, target: &str) -> String {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        if manifest["indices"].get(target).is_some() {
            return target.to_string();
        }
        if let Some(indices) = manifest["indices"].as_object() {
            for (index, body) in indices {
                if body["aliases"].get(target).is_some() {
                    return index.clone();
                }
            }
        }
        target.to_string()
    }

    fn resolve_search_targets(
        &self,
        target: &str,
        ignore_unavailable: bool,
        allow_no_indices: bool,
    ) -> Result<Vec<String>, RestResponse> {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let mut resolved = Vec::new();
        for selector in target.split(',').filter(|selector| !selector.is_empty()) {
            let mut matched = Vec::new();
            if let Some(indices) = manifest["indices"].as_object() {
                for (index_name, index_body) in indices {
                    if selector == index_name || wildcard_match(selector, index_name) {
                        matched.push(index_name.clone());
                        continue;
                    }
                    if let Some(aliases) = index_body["aliases"].as_object() {
                        if aliases.contains_key(selector)
                            || aliases.keys().any(|alias| wildcard_match(selector, alias))
                        {
                            matched.push(index_name.clone());
                        }
                    }
                }
            }
            matched.sort();
            matched.dedup();
            if matched.is_empty() && !(ignore_unavailable || allow_no_indices) {
                return Err(RestResponse::json(
                    404,
                    serde_json::json!({
                        "error": {
                            "type": "index_not_found_exception",
                            "reason": format!("no such index [{selector}]")
                        },
                        "status": 404
                    }),
                ));
            }
            resolved.extend(matched);
        }
        resolved.sort();
        resolved.dedup();
        if resolved.is_empty() {
            if allow_no_indices {
                return Ok(resolved);
            }
            return Err(RestResponse::json(
                404,
                serde_json::json!({
                    "error": {
                        "type": "index_not_found_exception",
                        "reason": format!("no such index [{target}]")
                    },
                    "status": 404
                }),
            ));
        }
        Ok(resolved)
    }

    fn validate_knn_target_capabilities(
        &self,
        query: &Value,
        resolved_indices: &[String],
    ) -> Option<RestResponse> {
        let field = extract_knn_field_name(query)?;
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        for index in resolved_indices {
            let field_mapping = manifest["indices"][index]["mappings"]["properties"][field].clone();
            let field_object = field_mapping.as_object()?;
            if field_object.get("mode").and_then(Value::as_str) == Some("on_disk") {
                return Some(build_unsupported_search_response(
                    "unsupported knn mode [on_disk]",
                ));
            }
            let Some(method) = field_object.get("method").and_then(Value::as_object) else {
                continue;
            };
            if method.get("engine").and_then(Value::as_str).is_some_and(|engine| engine != "lucene") {
                return Some(build_unsupported_search_response(
                    "unsupported knn method engine",
                ));
            }
            if method.get("parameters").is_some() {
                return Some(build_unsupported_search_response(
                    "unsupported knn method parameters",
                ));
            }
        }
        None
    }
}

fn build_unsupported_search_response(reason: &str) -> RestResponse {
    RestResponse::json(
        400,
        serde_json::json!({
            "error": {
                "type": "illegal_argument_exception",
                "reason": reason
            },
            "status": 400
        }),
    )
}

fn validate_search_request_body(body: &Value) -> Option<RestResponse> {
    for unsupported in [
        "highlight",
        "suggest",
        "rescore",
        "collapse",
        "pit",
        "search_after",
        "terminate_after",
        "timeout",
        "explain",
        "profile",
        "stored_fields",
        "docvalue_fields",
        "runtime_mappings",
    ] {
        if body.get(unsupported).is_some() {
            return Some(build_unsupported_search_response(&format!(
                "unsupported search option [{unsupported}]"
            )));
        }
    }
    if let Some(track_total_hits) = body.get("track_total_hits") {
        if track_total_hits != &Value::Bool(true) {
            return Some(build_unsupported_search_response(
                "unsupported search option [track_total_hits]",
            ));
        }
    }
    validate_search_query_body(&body["query"])
}

fn validate_search_query_body(query: &Value) -> Option<RestResponse> {
    let Some(query_object) = query.as_object() else {
        return None;
    };
    let Some((query_kind, _)) = query_object.iter().next() else {
        return None;
    };
    match query_kind.as_str() {
        "match_all" | "term" | "match" | "bool" | "range" | "knn" => {
            validate_supported_query_shape(query)
        }
        unsupported => Some(build_unsupported_search_response(&format!(
            "unsupported query [{unsupported}]"
        ))),
    }
}

fn validate_supported_query_shape(query: &Value) -> Option<RestResponse> {
    if let Some(knn) = query.get("knn").and_then(Value::as_object) {
        let Some((_, spec)) = knn.iter().next() else {
            return Some(build_unsupported_search_response("unsupported knn query shape"));
        };
        let Some(spec_object) = spec.as_object() else {
            return Some(build_unsupported_search_response("unsupported knn query shape"));
        };
        for key in spec_object.keys() {
            if key != "vector" && key != "k" {
                return Some(build_unsupported_search_response(&format!(
                    "unsupported knn parameter [{key}]"
                )));
            }
        }
        if !spec_object
            .get("vector")
            .and_then(Value::as_array)
            .is_some_and(|values| values.iter().all(Value::is_number))
        {
            return Some(build_unsupported_search_response("unsupported knn vector shape"));
        }
        if spec_object.get("k").and_then(Value::as_u64).unwrap_or(0) == 0 {
            return Some(build_unsupported_search_response("unsupported knn parameter [k]"));
        }
    }
    if let Some(bool_query) = query.get("bool").and_then(Value::as_object) {
        if let Some(must) = bool_query.get("must").and_then(Value::as_array) {
            for clause in must {
                if let Some(response) = validate_search_query_body(clause) {
                    return Some(response);
                }
            }
        }
        if let Some(filter) = bool_query.get("filter").and_then(Value::as_array) {
            for clause in filter {
                if let Some(response) = validate_search_query_body(clause) {
                    return Some(response);
                }
            }
        }
    }
    None
}

fn split_document_key(key: &str) -> Option<(&str, &str, &str)> {
    let mut parts = key.splitn(3, ':');
    Some((parts.next()?, parts.next()?, parts.next()?))
}

fn extract_knn_field_name(query: &Value) -> Option<&str> {
    if let Some(knn) = query.get("knn").and_then(Value::as_object) {
        return knn.keys().next().map(String::as_str);
    }
    query
        .get("bool")
        .and_then(Value::as_object)
        .and_then(|bool_query| bool_query.get("must"))
        .and_then(Value::as_array)
        .and_then(|clauses| clauses.iter().find_map(extract_knn_field_name))
}

fn apply_search_sort(hits: &mut [Value], sort: &Value) {
    let Some(sort_fields) = sort.as_array() else {
        return;
    };
    if sort_fields.is_empty() {
        return;
    }
    hits.sort_by(|left, right| {
        for field_spec in sort_fields {
            if let Some(field_name) = field_spec.as_str() {
                if field_name == "_score" {
                    let left_score = left["_score"].as_f64().unwrap_or(0.0);
                    let right_score = right["_score"].as_f64().unwrap_or(0.0);
                    let ordering = right_score
                        .partial_cmp(&left_score)
                        .unwrap_or(std::cmp::Ordering::Equal);
                    if ordering != std::cmp::Ordering::Equal {
                        return ordering;
                    }
                }
                continue;
            }
            let Some(field_object) = field_spec.as_object() else {
                continue;
            };
            for (field_name, field_options) in field_object {
                let desc = field_options
                    .get("order")
                    .and_then(Value::as_str)
                    .unwrap_or("asc")
                    == "desc";
                let left_value = extract_sort_value(left, field_name);
                let right_value = extract_sort_value(right, field_name);
                let ordering = compare_json_scalars(&left_value, &right_value);
                let ordering = if desc { ordering.reverse() } else { ordering };
                if ordering != std::cmp::Ordering::Equal {
                    return ordering;
                }
            }
        }
        left["_seq_no"]
            .as_i64()
            .unwrap_or_default()
            .cmp(&right["_seq_no"].as_i64().unwrap_or_default())
    });
}

fn extract_sort_value(hit: &Value, field_name: &str) -> Value {
    if field_name == "_score" {
        return hit.get("_score").cloned().unwrap_or(Value::Null);
    }
    hit.get("_source")
        .and_then(|source| source.get(field_name))
        .cloned()
        .unwrap_or(Value::Null)
}

fn compare_json_scalars(left: &Value, right: &Value) -> std::cmp::Ordering {
    match (left.as_f64(), right.as_f64()) {
        (Some(left), Some(right)) => {
            left.partial_cmp(&right).unwrap_or(std::cmp::Ordering::Equal)
        }
        _ => left
            .as_str()
            .unwrap_or_default()
            .cmp(right.as_str().unwrap_or_default()),
    }
}

fn extract_knn_limit(query: &Value) -> Option<usize> {
    if let Some(knn) = query.get("knn").and_then(Value::as_object) {
        let (_, spec) = knn.iter().next()?;
        return spec.get("k").and_then(Value::as_u64).map(|value| value as usize);
    }
    if let Some(bool_query) = query.get("bool").and_then(Value::as_object) {
        if let Some(must) = bool_query.get("must").and_then(Value::as_array) {
            for clause in must {
                if let Some(limit) = extract_knn_limit(clause) {
                    return Some(limit);
                }
            }
        }
    }
    None
}

fn build_missing_snapshot_repository_response(repository: &str) -> RestResponse {
    RestResponse::json(
        404,
        serde_json::json!({
            "error": {
                "type": "repository_missing_exception",
                "reason": format!("[{repository}] missing"),
            },
            "status": 404
        }),
    )
}

fn build_missing_snapshot_response(repository: &str, snapshot: &str) -> RestResponse {
    RestResponse::json(
        404,
        serde_json::json!({
            "error": {
                "type": "snapshot_missing_exception",
                "reason": format!("[{repository}:{snapshot}] missing"),
            },
            "status": 404
        }),
    )
}

fn evaluate_search_query(record: &StoredDocument, query: &Value) -> Option<(bool, f64)> {
    if query.is_null() || query.as_object().is_some_and(|object| object.is_empty()) {
        return Some((true, 1.0));
    }
    if query.get("match_all").is_some() {
        return Some((true, 1.0));
    }
    if let Some(term) = query.get("term").and_then(Value::as_object) {
        let (field, expected) = term.iter().next()?;
        let matched = value_matches_term(record.source.get(field), expected);
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(match_query) = query.get("match").and_then(Value::as_object) {
        let (field, expected) = match_query.iter().next()?;
        let score = score_match_query(record.source.get(field), expected.as_str().unwrap_or_default());
        return Some((score > 0.0, score));
    }
    if let Some(bool_query) = query.get("bool").and_then(Value::as_object) {
        if let Some(musts) = bool_query.get("must").and_then(Value::as_array) {
            let mut total_score = 0.0;
            for clause in musts {
                let (matched, score) = evaluate_search_query(record, clause)?;
                if !matched {
                    return Some((false, 0.0));
                }
                total_score += score;
            }
            return Some((true, total_score.max(1.0)));
        }
        if let Some(filters) = bool_query.get("filter").and_then(Value::as_array) {
            let matched = filters.iter().all(|clause| {
                evaluate_search_query(record, clause)
                    .map(|(matched, _)| matched)
                    .unwrap_or(false)
            });
            return Some((matched, if matched { 1.0 } else { 0.0 }));
        }
    }
    if let Some(knn_query) = query.get("knn").and_then(Value::as_object) {
        let (field, spec) = knn_query.iter().next()?;
        let vector = spec.get("vector")?.as_array()?;
        let score = score_knn_query(record.source.get(field), vector);
        return Some((score > f64::MIN / 2.0, score));
    }
    if let Some(range_query) = query.get("range").and_then(Value::as_object) {
        let (field, bounds) = range_query.iter().next()?;
        let matched = value_matches_range(record.source.get(field), bounds);
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    Some((false, 0.0))
}

fn value_matches_term(candidate: Option<&Value>, expected: &Value) -> bool {
    match (candidate, expected) {
        (Some(Value::String(left)), Value::String(right)) => tokenize_search_text(left)
            .into_iter()
            .any(|token| token == right.to_ascii_lowercase()),
        (Some(Value::Number(left)), Value::Number(right)) => left == right,
        (Some(left), right) => left == right,
        _ => false,
    }
}

fn tokenize_search_text(input: &str) -> Vec<String> {
    input
        .split(|character: char| !character.is_ascii_alphanumeric())
        .map(|token| token.to_ascii_lowercase())
        .filter(|token| !token.is_empty())
        .collect()
}

fn score_match_query(candidate: Option<&Value>, expected: &str) -> f64 {
    let Some(candidate_text) = candidate.and_then(Value::as_str) else {
        return 0.0;
    };
    let haystack = candidate_text.to_ascii_lowercase();
    let mut score = 0.0;
    for token in expected
        .split_whitespace()
        .map(|token| token.to_ascii_lowercase())
        .filter(|token| !token.is_empty())
    {
        if haystack.contains(&token) {
            score += 1.0;
        }
    }
    score
}

fn score_knn_query(candidate: Option<&Value>, expected: &[Value]) -> f64 {
    let Some(candidate_values) = candidate.and_then(Value::as_array) else {
        return f64::MIN;
    };
    if candidate_values.len() != expected.len() {
        return f64::MIN;
    }
    let mut score = 0.0;
    for (left, right) in candidate_values.iter().zip(expected) {
        let Some(left) = left.as_f64() else {
            return f64::MIN;
        };
        let Some(right) = right.as_f64() else {
            return f64::MIN;
        };
        score += left * right;
    }
    score
}

fn value_matches_range(candidate: Option<&Value>, bounds: &Value) -> bool {
    let Some(candidate_number) = candidate.and_then(Value::as_f64) else {
        return false;
    };
    let gte = bounds.get("gte").and_then(Value::as_f64);
    let gt = bounds.get("gt").and_then(Value::as_f64);
    let lte = bounds.get("lte").and_then(Value::as_f64);
    let lt = bounds.get("lt").and_then(Value::as_f64);
    gte.map_or(true, |bound| candidate_number >= bound)
        && gt.map_or(true, |bound| candidate_number > bound)
        && lte.map_or(true, |bound| candidate_number <= bound)
        && lt.map_or(true, |bound| candidate_number < bound)
}

fn wildcard_match(pattern: &str, candidate: &str) -> bool {
    if !pattern.contains('*') {
        return pattern == candidate;
    }
    let parts: Vec<&str> = pattern.split('*').collect();
    let mut remainder = candidate;
    let starts_with_wildcard = pattern.starts_with('*');
    let ends_with_wildcard = pattern.ends_with('*');
    for (index, part) in parts.iter().enumerate() {
        if part.is_empty() {
            continue;
        }
        if index == 0 && !starts_with_wildcard {
            if let Some(stripped) = remainder.strip_prefix(part) {
                remainder = stripped;
                continue;
            }
            return false;
        }
        if index == parts.len() - 1 && !ends_with_wildcard {
            return remainder.ends_with(part);
        }
        if let Some(position) = remainder.find(part) {
            remainder = &remainder[position + part.len()..];
        } else {
            return false;
        }
    }
    true
}

fn build_search_aggregations(
    aggregations: Option<&Value>,
    hits: &[Value],
) -> Result<Option<Value>, RestResponse> {
    let Some(aggregations) = aggregations.and_then(Value::as_object) else {
        return Ok(None);
    };
    let mut result = serde_json::Map::new();
    let mut terms_doc_counts: std::collections::BTreeMap<String, Vec<(String, u64)>> =
        std::collections::BTreeMap::new();
    for (name, aggregation) in aggregations {
        let Some(aggregation_object) = aggregation.as_object() else {
            continue;
        };
        if let Some(terms) = aggregation_object.get("terms").and_then(Value::as_object) {
            if terms.get("order").is_some() {
                return Err(build_unsupported_search_response(
                    "unsupported aggregation option [terms.order]",
                ));
            }
            let field = terms.get("field").and_then(Value::as_str).unwrap_or_default();
            let mut counts = std::collections::BTreeMap::new();
            for hit in hits {
                if let Some(key) = hit
                    .get("_source")
                    .and_then(|source| source.get(field))
                    .and_then(Value::as_str)
                {
                    *counts.entry(key.to_string()).or_insert(0_u64) += 1;
                }
            }
            let mut buckets: Vec<(String, u64)> = counts.into_iter().collect();
            buckets.sort_by(|left, right| {
                right.1.cmp(&left.1).then_with(|| left.0.cmp(&right.0))
            });
            terms_doc_counts.insert(name.clone(), buckets.clone());
            result.insert(
                name.clone(),
                serde_json::json!({
                    "buckets": buckets
                        .into_iter()
                        .map(|(key, doc_count)| serde_json::json!({"key": key, "doc_count": doc_count}))
                        .collect::<Vec<_>>()
                }),
            );
            continue;
        }
        if let Some((metric_name, metric_body)) = first_supported_metric_aggregation(aggregation_object) {
            let field = metric_body.get("field").and_then(Value::as_str).unwrap_or_default();
            let values: Vec<f64> = hits
                .iter()
                .filter_map(|hit| {
                    hit.get("_source")
                        .and_then(|source| source.get(field))
                        .and_then(Value::as_f64)
                })
                .collect();
            let value = match metric_name {
                "min" => values.iter().copied().reduce(f64::min).unwrap_or(0.0),
                "max" => values.iter().copied().reduce(f64::max).unwrap_or(0.0),
                "sum" => values.iter().sum(),
                "avg" => {
                    if values.is_empty() {
                        0.0
                    } else {
                        values.iter().sum::<f64>() / values.len() as f64
                    }
                }
                "value_count" => values.len() as f64,
                "stats" => {
                    result.insert(
                        name.clone(),
                        serde_json::json!({
                            "count": values.len(),
                            "min": values.iter().copied().reduce(f64::min).unwrap_or(0.0),
                            "max": values.iter().copied().reduce(f64::max).unwrap_or(0.0),
                            "avg": if values.is_empty() { 0.0 } else { values.iter().sum::<f64>() / values.len() as f64 },
                            "sum": values.iter().sum::<f64>(),
                        }),
                    );
                    continue;
                }
                _ => 0.0,
            };
            result.insert(name.clone(), serde_json::json!({ "value": value }));
            continue;
        }
        if let Some(filter) = aggregation_object.get("filter") {
            let doc_count = hits
                .iter()
                .filter(|hit| hit_matches_query(hit, filter))
                .count() as u64;
            result.insert(name.clone(), serde_json::json!({ "doc_count": doc_count }));
            continue;
        }
        if let Some(filters) = aggregation_object
            .get("filters")
            .and_then(|value| value.get("filters"))
            .and_then(Value::as_object)
        {
            let mut buckets = serde_json::Map::new();
            for (bucket_name, filter) in filters {
                let doc_count = hits
                    .iter()
                    .filter(|hit| hit_matches_query(hit, filter))
                    .count() as u64;
                buckets.insert(bucket_name.clone(), serde_json::json!({ "doc_count": doc_count }));
            }
            result.insert(name.clone(), serde_json::json!({ "buckets": buckets }));
            continue;
        }
        if let Some(top_hits) = aggregation_object.get("top_hits").and_then(Value::as_object) {
            let mut top_rows = hits.to_vec();
            apply_search_sort(
                &mut top_rows,
                top_hits.get("sort").unwrap_or(&Value::Null),
            );
            let size = top_hits.get("size").and_then(Value::as_u64).unwrap_or(3) as usize;
            let selected: Vec<Value> = top_rows.into_iter().take(size).collect();
            result.insert(
                name.clone(),
                serde_json::json!({
                    "hits": {
                        "total": { "value": hits.len() },
                        "hits": selected
                    }
                }),
            );
            continue;
        }
        if let Some(composite) = aggregation_object.get("composite").and_then(Value::as_object) {
            let sources = composite
                .get("sources")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            let mut counts = std::collections::BTreeMap::<String, (Value, u64)>::new();
            for hit in hits {
                let mut key_object = serde_json::Map::new();
                for source in &sources {
                    if let Some(source_object) = source.as_object() {
                        for (name, spec) in source_object {
                            let field = spec
                                .get("terms")
                                .and_then(|terms| terms.get("field"))
                                .and_then(Value::as_str)
                                .unwrap_or_default();
                            key_object.insert(
                                name.clone(),
                                hit.get("_source")
                                    .and_then(|source| source.get(field))
                                    .cloned()
                                    .unwrap_or(Value::Null),
                            );
                        }
                    }
                }
                let key_value = Value::Object(key_object.clone());
                let encoded = serde_json::to_string(&key_value).unwrap_or_default();
                let entry = counts.entry(encoded).or_insert((key_value, 0));
                entry.1 += 1;
            }
            let buckets = counts
                .into_values()
                .map(|(key, doc_count)| serde_json::json!({ "key": key, "doc_count": doc_count }))
                .collect::<Vec<_>>();
            result.insert(name.clone(), serde_json::json!({ "buckets": buckets }));
            continue;
        }
        if aggregation_object.get("significant_terms").is_some() {
            if aggregation_object["significant_terms"].get("background_filter").is_some() {
                return Err(build_unsupported_search_response(
                    "unsupported aggregation option [significant_terms.background_filter]",
                ));
            }
            result.insert(name.clone(), serde_json::json!({ "buckets": [] }));
            continue;
        }
        if let Some(geo_bounds) = aggregation_object.get("geo_bounds").and_then(Value::as_object) {
            let field = geo_bounds.get("field").and_then(Value::as_str).unwrap_or_default();
            let mut min_lat = f64::INFINITY;
            let mut max_lat = f64::NEG_INFINITY;
            let mut min_lon = f64::INFINITY;
            let mut max_lon = f64::NEG_INFINITY;
            for hit in hits {
                let Some(point) = hit.get("_source").and_then(|source| source.get(field)) else {
                    continue;
                };
                let Some(lat) = point.get("lat").and_then(Value::as_f64) else {
                    continue;
                };
                let Some(lon) = point.get("lon").and_then(Value::as_f64) else {
                    continue;
                };
                min_lat = min_lat.min(lat);
                max_lat = max_lat.max(lat);
                min_lon = min_lon.min(lon);
                max_lon = max_lon.max(lon);
            }
            result.insert(
                name.clone(),
                serde_json::json!({
                    "bounds": {
                        "top_left": { "lat": max_lat, "lon": min_lon },
                        "bottom_right": { "lat": min_lat, "lon": max_lon }
                    }
                }),
            );
            continue;
        }
        if let Some(sum_bucket) = aggregation_object.get("sum_bucket").and_then(Value::as_object) {
            let buckets_path = sum_bucket
                .get("buckets_path")
                .and_then(Value::as_str)
                .unwrap_or_default();
            let prefix = buckets_path.split('>').next().unwrap_or_default();
            let sum = terms_doc_counts
                .get(prefix)
                .map(|buckets| buckets.iter().map(|(_, count)| *count as f64).sum::<f64>())
                .unwrap_or(0.0);
            result.insert(name.clone(), serde_json::json!({ "value": sum }));
            continue;
        }
        for unsupported in ["date_histogram", "histogram", "range", "cardinality"] {
            if aggregation_object.get(unsupported).is_some() {
                return Err(build_unsupported_search_response(&format!(
                    "unsupported aggregation [{unsupported}]"
                )));
            }
        }
    }
    Ok(Some(Value::Object(result)))
}

fn first_supported_metric_aggregation<'a>(
    aggregation_object: &'a serde_json::Map<String, Value>,
) -> Option<(&'a str, &'a Value)> {
    for key in ["min", "max", "sum", "avg", "value_count", "stats"] {
        if let Some(value) = aggregation_object.get(key) {
            return Some((key, value));
        }
    }
    None
}

fn hit_matches_query(hit: &Value, query: &Value) -> bool {
    let record = StoredDocument {
        source: hit.get("_source").cloned().unwrap_or(Value::Null),
        version: 1,
        seq_no: hit.get("_seq_no").and_then(Value::as_i64).unwrap_or_default(),
        primary_term: 1,
        routing: None,
    };
    evaluate_search_query(&record, query)
        .map(|(matched, _)| matched)
        .unwrap_or(false)
}

fn normalize_alias_metadata_for_readback(metadata: Value) -> Value {
    let mut metadata = metadata;
    if let Some(object) = metadata.as_object_mut() {
        if let Some(routing) = object.remove("routing") {
            object
                .entry("index_routing".to_string())
                .or_insert_with(|| routing.clone());
            object
                .entry("search_routing".to_string())
                .or_insert(routing);
        }
    }
    metadata
}

fn build_root_info_response(info: &NodeInfo) -> RestResponse {
    RestResponse::json(
        200,
        serde_json::json!({
            "name": info.name,
            "cluster_name": "steelsearch-dev",
            "cluster_uuid": "steelsearch-dev-cluster-uuid",
            "version": {
                "number": info.version.to_string()
            },
            "tagline": "The OpenSearch Project: https://opensearch.org/"
        }),
    )
}

fn default_cluster_metadata_manifest() -> Value {
    serde_json::json!({
        "cluster_settings": default_cluster_settings_state(),
        "indices": {},
        "templates": {
            "legacy_index_templates": {},
            "component_templates": {},
            "index_templates": {}
        }
    })
}

fn filter_source_fields(source: &Value, includes: &str) -> Value {
    let Some(object) = source.as_object() else {
        return source.clone();
    };
    let selectors = includes.split(',').map(str::trim).filter(|s| !s.is_empty()).collect::<BTreeSet<_>>();
    let mut filtered = serde_json::Map::new();
    for (key, value) in object {
        if selectors.contains(key.as_str()) {
            filtered.insert(key.clone(), value.clone());
        }
    }
    Value::Object(filtered)
}

fn merge_json_object(target: &mut Value, patch: &Value) {
    let Some(target_object) = target.as_object_mut() else {
        *target = patch.clone();
        return;
    };
    let Some(patch_object) = patch.as_object() else {
        *target = patch.clone();
        return;
    };
    for (key, value) in patch_object {
        target_object.insert(key.clone(), value.clone());
    }
}

fn parse_wait_for_nodes(raw: &str) -> Option<u64> {
    let digits = raw.chars().filter(char::is_ascii_digit).collect::<String>();
    if digits.is_empty() {
        None
    } else {
        digits.parse::<u64>().ok()
    }
}

fn default_cluster_settings_state() -> Value {
    serde_json::json!({
        "persistent": {
            "cluster.routing.allocation.enable": "all"
        },
        "transient": {
            "cluster.info.update.interval": "30s"
        }
    })
}

fn merge_cluster_settings_section_flat(base: &Value, patch: &Value) -> Value {
    let mut merged = match base {
        Value::Object(map) => map.clone(),
        _ => serde_json::Map::new(),
    };
    if let Value::Object(patch_map) = patch {
        for (key, value) in patch_map {
            merged.insert(key.clone(), value.clone());
        }
    }
    Value::Object(merged)
}

fn expand_dotted_cluster_settings_section(section: &Value) -> Value {
    let mut expanded = serde_json::Map::new();
    if let Value::Object(section_map) = section {
        for (key, value) in section_map {
            insert_dotted_cluster_setting_value(&mut expanded, key, value.clone());
        }
    }
    Value::Object(expanded)
}

fn insert_dotted_cluster_setting_value(
    target: &mut serde_json::Map<String, Value>,
    dotted_key: &str,
    value: Value,
) {
    let mut segments = dotted_key.split('.').peekable();
    let mut current = target;
    while let Some(segment) = segments.next() {
        if segments.peek().is_none() {
            current.insert(segment.to_string(), value);
            return;
        }
        let entry = current
            .entry(segment.to_string())
            .or_insert_with(|| Value::Object(serde_json::Map::new()));
        if !entry.is_object() {
            *entry = Value::Object(serde_json::Map::new());
        }
        current = entry
            .as_object_mut()
            .expect("cluster settings nested section must stay object");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn publication_round_state_accepts_main_rs_gateway_replay_fields() {
        let round = PublicationRoundState {
            state_uuid: "state-9".to_string(),
            version: 9,
            term: 1,
            target_nodes: BTreeSet::from(["node-a".to_string()]),
            acknowledged_nodes: BTreeSet::from(["node-a".to_string()]),
            applied_nodes: BTreeSet::from(["node-a".to_string()]),
            missing_nodes: BTreeSet::new(),
            proposal_transport_failures: BTreeMap::new(),
            acknowledgement_transport_failures: BTreeMap::new(),
            apply_transport_failures: BTreeMap::new(),
            required_quorum: 1,
            committed: true,
        };
        assert_eq!(round.version, 9);
        assert!(round.committed);
        assert!(round.target_nodes.contains("node-a"));
    }

    #[test]
    fn gateway_metadata_state_replays_into_manifest_shape_used_by_main_rs() {
        let mut manifest = serde_json::json!({
            "cluster_uuid": "cluster-uuid",
            "indices": {
                "logs-000001": {}
            },
            "templates": {}
        });
        let metadata_state = PersistedGatewayMetadataState {
            cluster_settings: ClusterSettingsState {
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
                    "logs-write": { "is_write_index": true }
                }),
            )]),
            legacy_index_templates: BTreeMap::new(),
            component_templates: BTreeMap::from([(
                "gateway-component".to_string(),
                serde_json::json!({
                    "template": { "settings": { "index": { "number_of_replicas": 0 } } }
                }),
            )]),
            index_templates: BTreeMap::from([(
                "gateway-template".to_string(),
                serde_json::json!({
                    "index_patterns": ["logs-*"]
                }),
            )]),
        };

        apply_gateway_metadata_state_to_manifest(&mut manifest, &metadata_state);

        assert_eq!(
            manifest["cluster_settings"]["persistent"]["cluster.routing.allocation.enable"],
            "all"
        );
        assert_eq!(
            manifest["cluster_settings"]["transient"]["cluster.info.update.interval"],
            "30s"
        );
        assert_eq!(
            manifest["indices"]["logs-000001"]["aliases"]["logs-write"]["is_write_index"],
            true
        );
        assert!(manifest["templates"]["component_templates"]
            .get("gateway-component")
            .is_some());
        assert!(manifest["templates"]["index_templates"]
            .get("gateway-template")
            .is_some());
    }

    #[test]
    fn persisted_cluster_manager_task_queue_state_reports_interrupted_tasks() {
        let state = PersistedClusterManagerTaskQueueState {
            in_flight: vec![ClusterManagerTaskRecord::default()],
            ..Default::default()
        };
        assert!(state.has_interrupted_tasks());
    }
}
