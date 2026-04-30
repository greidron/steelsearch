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

const GENERATED_OPENAPI_JSON: &str =
    include_str!("../../../docs/api-spec/generated/openapi.json");
const SWAGGER_UI_CSS: &str =
    include_str!("../../../docs/api-spec/generated/swagger-ui/swagger-ui.css");
const SWAGGER_UI_BUNDLE_JS: &str =
    include_str!("../../../docs/api-spec/generated/swagger-ui/swagger-ui-bundle.js");
const SWAGGER_UI_HTML: &str = r#"<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Steelsearch API Docs</title>
  <link rel="stylesheet" href="/swagger-ui/swagger-ui.css" />
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="/swagger-ui/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({
      url: '/openapi.json',
      dom_id: '#swagger-ui',
      deepLinking: true,
      presets: [SwaggerUIBundle.presets.apis],
      layout: "BaseLayout"
    });
  </script>
</body>
</html>
"#;

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
    pub ml_models_state: Arc<Mutex<BTreeMap<String, MlModelState>>>,
    pub next_ml_model_id: Arc<Mutex<u64>>,
    pub scroll_contexts: Arc<Mutex<BTreeMap<String, ScrollContext>>>,
    pub next_scroll_id: Arc<Mutex<u64>>,
    pub pit_contexts: Arc<Mutex<BTreeMap<String, PitContext>>>,
    pub next_pit_id: Arc<Mutex<u64>>,
    pub snapshot_restores_in_progress: Arc<Mutex<BTreeSet<String>>>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct StoredDocument {
    pub source: Value,
    pub version: i64,
    pub seq_no: i64,
    pub primary_term: i64,
    pub routing: Option<String>,
    pub refreshed: bool,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SharedRuntimeState {
    pub created_indices: BTreeSet<String>,
    pub metadata_manifest: Value,
    pub documents: BTreeMap<String, StoredDocument>,
    pub next_seq_no: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct KnnModelState {
    pub model_id: String,
    pub training_index: String,
    pub dimension: u64,
    pub description: String,
    pub method: Value,
    pub state: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MlModelState {
    pub model_id: String,
    pub name: String,
    pub function_name: String,
    pub dimension: u64,
    pub deployed: bool,
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
    pub training_requests: u64,
    pub trained_models: BTreeMap<String, KnnModelState>,
}

#[derive(Clone, Debug)]
pub struct ScrollContext {
    pub remaining_hits: Vec<Value>,
    pub page_size: usize,
}

#[derive(Clone, Debug)]
pub struct PitContext {
    pub indices: Vec<String>,
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
            ml_models_state: Arc::new(Mutex::new(BTreeMap::new())),
            next_ml_model_id: Arc::new(Mutex::new(0)),
            scroll_contexts: Arc::new(Mutex::new(BTreeMap::new())),
            next_scroll_id: Arc::new(Mutex::new(0)),
            pit_contexts: Arc::new(Mutex::new(BTreeMap::new())),
            next_pit_id: Arc::new(Mutex::new(0)),
            snapshot_restores_in_progress: Arc::new(Mutex::new(BTreeSet::new())),
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
        if request.method == RestMethod::Get && request.path.starts_with("/_cluster/health/") {
            return Some(self.handle_cluster_health_route(request));
        }
        match (request.method, request.path.as_str()) {
            (RestMethod::Get, "/") => Some(build_root_info_response(&self.info)),
            (RestMethod::Head, "/") => Some(RestResponse::empty(200)),
            (RestMethod::Get, "/openapi.json") => Some(self.handle_openapi_route()),
            (RestMethod::Get, "/docs") | (RestMethod::Get, "/swagger") | (RestMethod::Get, "/swagger-ui") => {
                Some(self.handle_swagger_ui_route())
            }
            (RestMethod::Get, "/swagger-ui/swagger-ui.css") => Some(self.handle_swagger_ui_css_route()),
            (RestMethod::Get, "/swagger-ui/swagger-ui-bundle.js") => {
                Some(self.handle_swagger_ui_bundle_route())
            }
            (RestMethod::Get, "/_steelsearch/dev/cluster") => Some(self.handle_dev_cluster_route()),
            (RestMethod::Head, "/_all") => Some(RestResponse::opensearch_error_kind(
                os_rest::RestErrorKind::IllegalArgument,
                "unsupported broad selector",
            )),
            (RestMethod::Get, "/_cluster/health") => Some(self.handle_cluster_health_route(request)),
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
        if request.path == "/_search/scroll" {
            return match request.method {
                RestMethod::Post => Some(self.handle_search_scroll_route(request)),
                RestMethod::Delete => Some(self.handle_clear_scroll_route(request)),
                _ => None,
            };
        }
        if request.path == "/_search/point_in_time" && request.method == RestMethod::Delete {
            return Some(self.handle_close_point_in_time_route(request));
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
        if request.path == "/_data_stream" && request.method == RestMethod::Get {
            return Some(self.handle_data_stream_get_route(None));
        }
        if request.path == "/_data_stream/_stats" && request.method == RestMethod::Get {
            return Some(self.handle_data_stream_stats_route());
        }
        if request.path.starts_with("/_data_stream/") {
            let name = request.path.trim_start_matches("/_data_stream/");
            return match request.method {
                RestMethod::Get => Some(self.handle_data_stream_get_route(Some(name))),
                RestMethod::Put => Some(self.handle_data_stream_put_route(name)),
                RestMethod::Delete => Some(self.handle_data_stream_delete_route(name)),
                _ => None,
            };
        }
        if request.path.contains("/_rollover") && request.method == RestMethod::Post {
            let path = request.path.trim_start_matches('/');
            let (target, named) = if let Some(target) = path.strip_suffix("/_rollover") {
                (target, None)
            } else if let Some((target, named)) = path.split_once("/_rollover/") {
                (target, Some(named))
            } else {
                (path, None)
            };
            return Some(self.handle_rollover_route(target, named));
        }
        if request.method == RestMethod::Get && request.path == "/_cat/indices" {
            return Some(self.handle_cat_indices_route(request));
        }
        if request.method == RestMethod::Get && request.path == "/_cat/count" {
            return Some(self.handle_cat_count_route(request));
        }
        if request.method == RestMethod::Get && request.path == "/_cat/plugins" {
            return Some(self.handle_cat_plugins_route(request));
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
        if request.path == "/_plugins/_knn/models/_train" && request.method == RestMethod::Post {
            return Some(self.handle_knn_model_train_route(request));
        }
        if request.path == "/_plugins/_knn/models/_search" && request.method == RestMethod::Post {
            return Some(self.handle_knn_model_search_route(request));
        }
        if let Some(model_id) = request.path.strip_prefix("/_plugins/_knn/models/") {
            return match request.method {
                RestMethod::Get => Some(self.handle_knn_model_get_route(model_id)),
                RestMethod::Delete => Some(self.handle_knn_model_delete_route(model_id)),
                _ => None,
            };
        }
        if request.path == "/_plugins/_ml/models/_register" && request.method == RestMethod::Post {
            return Some(self.handle_ml_model_register_route(request));
        }
        if request.path == "/_plugins/_ml/models/_search" && request.method == RestMethod::Post {
            return Some(self.handle_ml_model_search_route(request));
        }
        if let Some(model_id) = request.path.strip_prefix("/_plugins/_ml/models/") {
            if request.method == RestMethod::Get {
                return Some(self.handle_ml_model_get_route(model_id));
            }
            if request.method == RestMethod::Post && model_id.ends_with("/_deploy") {
                return Some(self.handle_ml_model_deploy_route(model_id.trim_end_matches("/_deploy"), true));
            }
            if request.method == RestMethod::Post && model_id.ends_with("/_undeploy") {
                return Some(self.handle_ml_model_deploy_route(model_id.trim_end_matches("/_undeploy"), false));
            }
            if request.method == RestMethod::Post && model_id.ends_with("/_predict") {
                return Some(self.handle_ml_model_predict_route(model_id.trim_end_matches("/_predict"), request));
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
        if let Some(index) = request
            .path
            .trim_matches('/')
            .strip_suffix("/_search/point_in_time")
        {
            if request.method == RestMethod::Post {
                return Some(self.handle_open_point_in_time_route(index, request));
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

    fn handle_openapi_route(&self) -> RestResponse {
        let body: Value = serde_json::from_str(GENERATED_OPENAPI_JSON)
            .expect("generated openapi json should parse");
        RestResponse::json(200, body)
    }

    fn handle_swagger_ui_route(&self) -> RestResponse {
        RestResponse::text(200, SWAGGER_UI_HTML)
            .with_header("content-type", "text/html; charset=utf-8")
    }

    fn handle_swagger_ui_css_route(&self) -> RestResponse {
        RestResponse::text(200, SWAGGER_UI_CSS).with_header("content-type", "text/css; charset=utf-8")
    }

    fn handle_swagger_ui_bundle_route(&self) -> RestResponse {
        RestResponse::text(200, SWAGGER_UI_BUNDLE_JS)
            .with_header("content-type", "application/javascript; charset=utf-8")
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
        let target = request
            .path
            .strip_prefix("/_cluster/health/")
            .filter(|value| !value.is_empty());
        let Some(mut body) = self.cluster_health_body(target) else {
            return RestResponse::opensearch_error_kind(
                os_rest::RestErrorKind::IndexNotFound,
                target.unwrap_or_default(),
            );
        };
        let current_nodes = body
            .get("number_of_nodes")
            .and_then(Value::as_u64)
            .unwrap_or(0);
        let current_status = body
            .get("status")
            .and_then(Value::as_str)
            .unwrap_or("red");
        let wait_for_nodes = request
            .query_params
            .get("wait_for_nodes")
            .and_then(|value| parse_wait_for_nodes(value));
        let wait_for_status = request
            .query_params
            .get("wait_for_status")
            .map(String::as_str);
        let timed_out = wait_for_nodes.is_some_and(|expected| expected > current_nodes)
            || wait_for_status.is_some_and(|expected| {
                cluster_health_status_rank(current_status) < cluster_health_status_rank(expected)
            });
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
        for key in request.query_params.keys() {
            match key.as_str() {
                "wait_for_active_shards" | "timeout" | "master_timeout" => {}
                _ => {
                    return RestResponse::opensearch_error_kind(
                        os_rest::RestErrorKind::IllegalArgument,
                        format!("unsupported create index parameter [{key}]"),
                    );
                }
            }
        }
        let request_body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let mut bounded_subset =
            create_index_route_registration::build_create_index_body_subset(&request_body);
        if let Some(settings) = bounded_subset.get("settings").cloned() {
            bounded_subset["settings"] = stringify_leaf_scalars(&settings);
        }
        self.created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .insert(index.to_string());
        self.documents_state
            .lock()
            .expect("documents state lock poisoned")
            .retain(|key, _| !key.starts_with(&format!("{index}:")));
        *self.next_seq_no.lock().expect("seq_no lock poisoned") = 0;
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
        let ignore_unavailable = query_param_is_true(request.query_params.get("ignore_unavailable"));
        let allow_no_indices = query_param_is_true(request.query_params.get("allow_no_indices"));
        let expand_wildcards = request
            .query_params
            .get("expand_wildcards")
            .map(String::as_str)
            .unwrap_or("open");
        let matched = match self.resolve_index_metadata_targets(
            target,
            ignore_unavailable,
            allow_no_indices,
            expand_wildcards,
        ) {
            Ok(matched) => matched,
            Err(response) => return response,
        };
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let body = get_index_route_registration::build_get_index_metadata_response_for_names(
            &manifest["indices"],
            &matched,
        );
        RestResponse::json(200, body)
    }

    fn handle_delete_index_route(&self, request: &RestRequest) -> RestResponse {
        let target = request.path.trim_matches('/');
        let ignore_unavailable = query_param_is_true(request.query_params.get("ignore_unavailable"));
        let allow_no_indices = query_param_is_true(request.query_params.get("allow_no_indices"));
        let expand_wildcards = request
            .query_params
            .get("expand_wildcards")
            .map(String::as_str)
            .unwrap_or("open");
        let matched = match self.resolve_index_metadata_targets(
            target,
            ignore_unavailable,
            allow_no_indices,
            expand_wildcards,
        ) {
            Ok(matched) => matched,
            Err(response) => return response,
        };
        if matched.is_empty() {
            return delete_index_route_registration::build_delete_index_success_response();
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
        let ignore_unavailable = query_param_is_true(request.query_params.get("ignore_unavailable"));
        let allow_no_indices = query_param_is_true(request.query_params.get("allow_no_indices"));
        let expand_wildcards = request
            .query_params
            .get("expand_wildcards")
            .map(String::as_str)
            .unwrap_or("open");
        match self.resolve_index_metadata_targets(
            target,
            ignore_unavailable,
            allow_no_indices,
            expand_wildcards,
        ) {
            Ok(matched) if !matched.is_empty() => RestResponse::empty(200),
            Ok(_) => RestResponse::empty(404),
            Err(response) if response.status == 404 => RestResponse::empty(404),
            Err(response) => response,
        }
    }

    fn resolve_index_metadata_targets(
        &self,
        target: &str,
        ignore_unavailable: bool,
        allow_no_indices: bool,
        expand_wildcards: &str,
    ) -> Result<Vec<String>, RestResponse> {
        match expand_wildcards {
            "open" | "all" => {}
            "closed" | "none" => {
                return Err(RestResponse::opensearch_error_kind(
                    os_rest::RestErrorKind::IllegalArgument,
                    format!("unsupported expand_wildcards value [{expand_wildcards}]"),
                ));
            }
            _ => {
                return Err(RestResponse::opensearch_error_kind(
                    os_rest::RestErrorKind::IllegalArgument,
                    format!("unsupported expand_wildcards value [{expand_wildcards}]"),
                ));
            }
        }

        let selectors = if target == "_all" {
            vec!["*"]
        } else {
            target
                .split(',')
                .map(str::trim)
                .filter(|selector| !selector.is_empty())
                .collect::<Vec<_>>()
        };

        let created = self
            .created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .iter()
            .cloned()
            .collect::<Vec<_>>();

        let mut matched = Vec::new();
        for selector in selectors {
            let mut selector_matches = created
                .iter()
                .filter(|index| selector == *index || wildcard_match(selector, index))
                .cloned()
                .collect::<Vec<_>>();
            selector_matches.sort();
            selector_matches.dedup();
            if selector_matches.is_empty() && !(ignore_unavailable || allow_no_indices) {
                return Err(delete_index_route_registration::build_delete_index_missing_response(
                    selector,
                ));
            }
            matched.extend(selector_matches);
        }
        matched.sort();
        matched.dedup();
        if matched.is_empty() && !(ignore_unavailable || allow_no_indices) {
            return Err(delete_index_route_registration::build_delete_index_missing_response(
                target,
            ));
        }
        Ok(matched)
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
        if let Some(dynamic) = subset.get("dynamic") {
            manifest["indices"][index]["mappings"]["dynamic"] = dynamic.clone();
        }
        if let Some(meta) = subset.get("_meta") {
            let existing_meta = manifest["indices"][index]["mappings"]
                .get("_meta")
                .cloned()
                .unwrap_or_else(|| serde_json::json!({}));
            let mut merged_meta = existing_meta;
            merge_object_with_null_reset(&mut merged_meta, meta);
            manifest["indices"][index]["mappings"]["_meta"] = merged_meta;
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
                if key != "number_of_replicas"
                    && key != "refresh_interval"
                    && key != "max_result_window"
                    && key != "number_of_routing_shards"
                {
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
        let existing_settings = manifest["indices"][index]["settings"].clone();
        let mut merged_settings = existing_settings;
        merge_object_with_null_reset(&mut merged_settings, &stringify_leaf_scalars(&subset));
        manifest["indices"][index]["settings"] = merged_settings;
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
        let matched = match self.resolve_index_metadata_targets(index, false, false, "open") {
            Ok(matched) => matched,
            Err(response) => return response,
        };
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        for matched_index in matched {
            manifest["indices"][matched_index]["aliases"][alias] = subset.clone();
        }
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
                let matched = self
                    .resolve_index_metadata_targets(index, false, false, "open")
                    .unwrap_or_default();
                for matched_index in matched {
                    manifest["indices"][matched_index]["aliases"][alias] =
                        normalize_alias_metadata_for_readback(alias_body.clone());
                }
            } else if let Some(remove) = action.get("remove") {
                let index = remove["index"].as_str().unwrap_or_default();
                let alias = remove["alias"].as_str().unwrap_or_default();
                let matched = self
                    .resolve_index_metadata_targets(index, false, false, "open")
                    .unwrap_or_default();
                for matched_index in matched {
                    manifest["indices"][matched_index]["aliases"]
                        .as_object_mut()
                        .map(|m| m.remove(alias));
                }
            } else if let Some(remove_index) = action.get("remove_index") {
                let index = remove_index["index"].as_str().unwrap_or_default();
                let matched = self
                    .resolve_index_metadata_targets(index, false, false, "open")
                    .unwrap_or_default();
                self.created_indices_state
                    .lock()
                    .expect("created indices state lock poisoned")
                    .retain(|created| !matched.iter().any(|candidate| candidate == created));
                self.documents_state
                    .lock()
                    .expect("documents state lock poisoned")
                    .retain(|key, _| !matched.iter().any(|candidate| key.starts_with(&format!("{candidate}:"))));
                for matched_index in matched {
                    manifest["indices"].as_object_mut().map(|m| m.remove(&matched_index));
                }
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
        let matched = match self.resolve_index_metadata_targets(index, false, false, "open") {
            Ok(matched) => matched,
            Err(response) => return response,
        };
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        for matched_index in matched {
            manifest["indices"][matched_index]["aliases"]
                .as_object_mut()
                .map(|m| m.remove(alias));
        }
        drop(manifest);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(
            200,
            alias_mutation_route_registration::build_alias_mutation_acknowledged_response(),
        )
    }

    fn data_stream_template_matches(name: &str, template_value: &Value) -> bool {
        let Some(index_template) = template_value.get("index_template") else {
            return false;
        };
        if index_template.get("data_stream").is_none() {
            return false;
        }
        index_template["index_patterns"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .any(|pattern| wildcard_match(pattern, name))
    }

    fn find_matching_data_stream_template_name(&self, name: &str) -> Option<String> {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        manifest["templates"]["index_templates"]
            .as_object()
            .into_iter()
            .flat_map(|templates| templates.iter())
            .find_map(|(template_name, template_value)| {
                Self::data_stream_template_matches(name, template_value)
                    .then(|| template_name.clone())
            })
    }

    fn data_stream_backing_index_name(name: &str, generation: u64) -> String {
        format!(".ds-{name}-{generation:06}")
    }

    fn create_minimal_index_manifest_entry(_index: &str) -> Value {
        serde_json::json!({
            "settings": {
                "index": {
                    "number_of_shards": "1",
                    "number_of_replicas": "1"
                }
            },
            "mappings": {
                "properties": {
                    "@timestamp": { "type": "date" }
                }
            },
            "aliases": {}
        })
    }

    fn ensure_minimal_index_exists(&self, index: &str) {
        let already_created = {
            let mut created = self
                .created_indices_state
                .lock()
                .expect("created indices state lock poisoned");
            !created.insert(index.to_string())
        };
        if already_created {
            return;
        }
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        if manifest["indices"].get(index).is_none() {
            manifest["indices"][index] = Self::create_minimal_index_manifest_entry(index);
        }
    }

    fn resolve_write_target(&self, target: &str, auto_create_missing_index: bool) -> Result<String, String> {
        {
            let manifest = self
                .metadata_manifest_state
                .lock()
                .expect("metadata manifest state lock poisoned");
            if let Some(stream) = manifest["data_streams"].get(target) {
                if let Some(backing_index) = stream["indices"]
                    .as_array()
                    .and_then(|indices| indices.last())
                    .and_then(|entry| entry.get("index_name"))
                    .and_then(Value::as_str)
                {
                    return Ok(backing_index.to_string());
                }
            }
            if manifest["indices"].get(target).is_some() {
                return Ok(target.to_string());
            }
            if let Some(indices) = manifest["indices"].as_object() {
                let mut alias_matches = Vec::new();
                let mut write_matches = Vec::new();
                for (index_name, body) in indices {
                    let Some(alias_state) = body["aliases"].get(target) else {
                        continue;
                    };
                    alias_matches.push(index_name.clone());
                    if alias_state
                        .get("is_write_index")
                        .and_then(Value::as_bool)
                        .unwrap_or(false)
                    {
                        write_matches.push(index_name.clone());
                    }
                }
                if let Some(index_name) = write_matches.first() {
                    return Ok(index_name.clone());
                }
                if alias_matches.len() == 1 {
                    return Ok(alias_matches[0].clone());
                }
                if alias_matches.len() > 1 {
                    return Err(format!(
                        "alias [{target}] has more than one index associated with it [{}], can't execute a single index op",
                        alias_matches.join(",")
                    ));
                }
            }
        }

        if auto_create_missing_index {
            self.ensure_minimal_index_exists(target);
            return Ok(target.to_string());
        }

        Ok(target.to_string())
    }

    fn target_is_data_stream(&self, target: &str) -> bool {
        self.metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned")["data_streams"]
            .get(target)
            .is_some()
    }

    fn target_is_alias(&self, target: &str) -> bool {
        self.metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned")["indices"]
            .as_object()
            .into_iter()
            .flat_map(|indices| indices.values())
            .any(|body| body["aliases"].get(target).is_some())
    }

    fn alias_has_explicit_routing_metadata(&self, target: &str) -> bool {
        self.metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned")["indices"]
            .as_object()
            .into_iter()
            .flat_map(|indices| indices.values())
            .filter_map(|body| body["aliases"].get(target))
            .any(|alias_state| {
                alias_state.get("routing").is_some()
                    || alias_state.get("index_routing").is_some()
                    || alias_state.get("search_routing").is_some()
            })
    }

    fn write_response_index(&self, target: &str, resolved_index: &str) -> String {
        if self.target_is_data_stream(target) {
            resolved_index.to_string()
        } else if self.target_is_alias(target) {
            if self.alias_has_explicit_routing_metadata(target) {
                resolved_index.to_string()
            } else {
                target.to_string()
            }
        } else {
            resolved_index.to_string()
        }
    }

    fn handle_data_stream_get_route(&self, target: Option<&str>) -> RestResponse {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let all = manifest["data_streams"]
            .as_object()
            .cloned()
            .unwrap_or_default();
        let mut entries = Vec::new();
        for (name, value) in all {
            if let Some(target_name) = target {
                if !wildcard_match(target_name, &name) {
                    continue;
                }
            }
            let generation = value.get("generation").and_then(Value::as_u64).unwrap_or(1);
            let indices = value.get("indices").cloned().unwrap_or_else(|| serde_json::json!([]));
            let template = value.get("template").cloned().unwrap_or(Value::Null);
            entries.push(serde_json::json!({
                "name": name,
                "timestamp_field": { "name": "@timestamp" },
                "indices": indices,
                "generation": generation,
                "status": "GREEN",
                "template": template
            }));
        }
        if target.is_some() && entries.is_empty() {
            return RestResponse::json(
                404,
                serde_json::json!({
                    "error": {
                        "type": "resource_not_found_exception",
                        "reason": format!("data_stream matching [{}] not found", target.unwrap_or_default())
                    },
                    "status": 404
                }),
            );
        }
        RestResponse::json(200, serde_json::json!({ "data_streams": entries }))
    }

    fn handle_data_stream_stats_route(&self) -> RestResponse {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let all = manifest["data_streams"]
            .as_object()
            .cloned()
            .unwrap_or_default();
        let backing_indices = all
            .values()
            .map(|value| value["indices"].as_array().map(|indices| indices.len()).unwrap_or(0))
            .sum::<usize>();
        RestResponse::json(
            200,
            serde_json::json!({
                "_shards": { "total": 1, "successful": 1, "failed": 0 },
                "data_stream_count": all.len(),
                "backing_indices": backing_indices,
                "total_store_size_bytes": 0
            }),
        )
    }

    fn handle_data_stream_put_route(&self, name: &str) -> RestResponse {
        let template_name = match self.find_matching_data_stream_template_name(name) {
            Some(template_name) => template_name,
            None => {
                return RestResponse::opensearch_error_kind(
                    os_rest::RestErrorKind::IllegalArgument,
                    format!("no matching index template with data_stream for [{name}]"),
                );
            }
        };
        let backing_index = Self::data_stream_backing_index_name(name, 1);
        self.created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .insert(backing_index.clone());
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        manifest["indices"][&backing_index] = Self::create_minimal_index_manifest_entry(&backing_index);
        manifest["data_streams"][name] = serde_json::json!({
            "generation": 1,
            "template": template_name,
            "indices": [
                { "index_name": backing_index }
            ]
        });
        drop(manifest);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, serde_json::json!({ "acknowledged": true }))
    }

    fn handle_data_stream_delete_route(&self, name: &str) -> RestResponse {
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let Some(stream) = manifest["data_streams"].as_object_mut().and_then(|streams| streams.remove(name)) else {
            return RestResponse::json(
                404,
                serde_json::json!({
                    "error": {
                        "type": "resource_not_found_exception",
                        "reason": format!("data_stream matching [{name}] not found")
                    },
                    "status": 404
                }),
            );
        };
        let backing_names = stream["indices"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(|entry| entry.get("index_name").and_then(Value::as_str))
            .map(ToOwned::to_owned)
            .collect::<Vec<_>>();
        drop(manifest);
        self.created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .retain(|index| !backing_names.iter().any(|candidate| candidate == index));
        self.documents_state
            .lock()
            .expect("documents state lock poisoned")
            .retain(|key, _| !backing_names.iter().any(|candidate| key.starts_with(&format!("{candidate}:"))));
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        for backing in backing_names {
            manifest["indices"].as_object_mut().map(|indices| indices.remove(&backing));
        }
        drop(manifest);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, serde_json::json!({ "acknowledged": true }))
    }

    fn next_rollover_index_name(index: &str) -> String {
        let digits = index
            .chars()
            .rev()
            .take_while(|ch| ch.is_ascii_digit())
            .collect::<String>()
            .chars()
            .rev()
            .collect::<String>();
        if digits.is_empty() {
            return format!("{index}-000002");
        }
        let prefix = &index[..index.len() - digits.len()];
        let next = digits.parse::<u64>().unwrap_or(1) + 1;
        format!("{prefix}{next:0width$}", width = digits.len())
    }

    fn handle_rollover_route(&self, target: &str, new_index: Option<&str>) -> RestResponse {
        let mut manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        if manifest["data_streams"].get(target).is_some() {
            let (_old_index, next_index, response) = {
                let stream = manifest["data_streams"]
                    .get_mut(target)
                    .expect("data stream should exist");
                let old_index = stream["indices"]
                    .as_array()
                    .and_then(|indices| indices.last())
                    .and_then(|entry| entry.get("index_name"))
                    .and_then(Value::as_str)
                    .unwrap_or_default()
                    .to_string();
                let next_generation = stream["generation"].as_u64().unwrap_or(1) + 1;
                let next_index = new_index
                    .map(ToOwned::to_owned)
                    .unwrap_or_else(|| Self::data_stream_backing_index_name(target, next_generation));
                stream["generation"] = serde_json::json!(next_generation);
                stream["indices"]
                    .as_array_mut()
                    .expect("data stream indices array expected")
                    .push(serde_json::json!({ "index_name": next_index.clone() }));
                let response = serde_json::json!({
                    "acknowledged": true,
                    "shards_acknowledged": true,
                    "old_index": old_index,
                    "new_index": next_index.clone(),
                    "rolled_over": true,
                    "dry_run": false,
                    "conditions": {}
                });
                (old_index, next_index, response)
            };
            self.created_indices_state
                .lock()
                .expect("created indices state lock poisoned")
                .insert(next_index.clone());
            manifest["indices"][&next_index] = Self::create_minimal_index_manifest_entry(&next_index);
            drop(manifest);
            self.persist_shared_runtime_state_to_disk();
            return RestResponse::json(200, response);
        }

        let matched = manifest["indices"]
            .as_object()
            .into_iter()
            .flat_map(|indices| indices.iter())
            .find_map(|(index_name, value)| {
                let aliases = value.get("aliases")?.as_object()?;
                let alias_state = aliases.get(target)?;
                let is_write = alias_state
                    .get("is_write_index")
                    .and_then(Value::as_bool)
                    .unwrap_or(false);
                is_write.then(|| index_name.clone())
            });
        let Some(old_index) = matched else {
            return RestResponse::opensearch_error_kind(
                os_rest::RestErrorKind::IllegalArgument,
                format!("no rollover target [{target}] found"),
            );
        };
        let next_index = new_index
            .map(ToOwned::to_owned)
            .unwrap_or_else(|| Self::next_rollover_index_name(&old_index));
        let mut next_manifest = manifest["indices"][&old_index].clone();
        if let Some(aliases) = next_manifest.get_mut("aliases").and_then(Value::as_object_mut) {
            aliases.insert(
                target.to_string(),
                serde_json::json!({ "is_write_index": true }),
            );
        }
        manifest["indices"][&old_index]["aliases"][target]["is_write_index"] = Value::Bool(false);
        manifest["indices"][&next_index] = next_manifest;
        drop(manifest);
        self.created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .insert(next_index.clone());
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, serde_json::json!({
            "acknowledged": true,
            "shards_acknowledged": true,
            "old_index": old_index,
            "new_index": next_index,
            "rolled_over": true,
            "dry_run": false,
            "conditions": {}
        }))
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
        let indices = match subset.get("indices") {
            Some(Value::String(value)) => Value::Array(
                value
                    .split(',')
                    .map(str::trim)
                    .filter(|item| !item.is_empty())
                    .map(|item| Value::String(item.to_string()))
                    .collect(),
            ),
            Some(value) => value.clone(),
            None => Value::Array(vec![]),
        };
        let snapshot_record = serde_json::json!({
            "snapshot": snapshot,
            "uuid": format!("{snapshot}-uuid"),
            "state": "SUCCESS",
            "indices": indices,
            "include_global_state": subset.get("include_global_state").cloned().unwrap_or(Value::Bool(false)),
            "metadata": subset.get("metadata").cloned().unwrap_or_else(|| serde_json::json!({})),
            "partial": subset.get("partial").cloned().unwrap_or(Value::Bool(false)),
            "ignore_unavailable": subset.get("ignore_unavailable").cloned().unwrap_or(Value::Bool(false))
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
                        "initializing": 0,
                        "started": 0,
                        "finalizing": 0,
                        "done": 1,
                        "total": 1,
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
        if let Some(parameter) = extract_snapshot_restore_unknown_parameter(&body) {
            return RestResponse::opensearch_error(
                400,
                "illegal_argument_exception",
                format!("Unknown parameter {parameter}"),
            );
        }
        let response =
            snapshot_lifecycle_route_registration::invoke_validated_snapshot_restore_live_route(
                &body,
            );
        if response.get("status").is_none() {
            self.snapshot_restores_in_progress
                .lock()
                .expect("snapshot restore in-progress state lock poisoned")
                .insert(format!("{repository}:{snapshot}"));
        }
        let status = response
            .get("status")
            .and_then(Value::as_u64)
            .map(|value| value as u16)
            .unwrap_or(200);
        RestResponse::json(status, response)
    }

    fn handle_snapshot_delete_route(&self, repository: &str, snapshot: &str) -> RestResponse {
        if self
            .snapshot_restores_in_progress
            .lock()
            .expect("snapshot restore in-progress state lock poisoned")
            .contains(&format!("{repository}:{snapshot}"))
        {
            return build_concurrent_snapshot_delete_response(repository, snapshot);
        }
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
        self.documents_state
            .lock()
            .expect("documents state lock poisoned")
            .values_mut()
            .for_each(|record| record.refreshed = true);
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

    fn handle_index_refresh_route(&self, index: &str) -> RestResponse {
        self.documents_state
            .lock()
            .expect("documents state lock poisoned")
            .iter_mut()
            .filter(|(key, _)| key.starts_with(&format!("{index}:")))
            .for_each(|(_, record)| record.refreshed = true);
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
        if let Some(search_type) = request.query_params.get("search_type") {
            if search_type != "query_then_fetch" && search_type != "dfs_query_then_fetch" {
                return build_unsupported_search_response("unsupported search_type");
            }
        }
        if let Some(pre_filter_shard_size) = request.query_params.get("pre_filter_shard_size") {
            if pre_filter_shard_size.parse::<u64>().is_err() {
                return build_unsupported_search_response("unsupported pre_filter_shard_size");
            }
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
        let resolved_indices = if let Some(pit_id) = body
            .get("pit")
            .and_then(Value::as_object)
            .and_then(|pit| pit.get("id"))
            .and_then(Value::as_str)
        {
            match self.resolve_pit_indices(pit_id) {
                Ok(indices) => indices,
                Err(response) => return response,
            }
        } else {
            let ignore_unavailable = request
                .query_params
                .get("ignore_unavailable")
                .is_some_and(|value| value == "true");
            let allow_no_indices = request
                .query_params
                .get("allow_no_indices")
                .is_some_and(|value| value == "true");
            let expand_wildcards = request
                .query_params
                .get("expand_wildcards")
                .map(String::as_str)
                .unwrap_or("open");
            if expand_wildcards == "none"
                && (index.contains('*') || index.contains('?') || index == "_all")
            {
                Vec::new()
            } else {
                match self.resolve_search_targets(index, ignore_unavailable, allow_no_indices) {
                    Ok(indices) => indices,
                    Err(response) => return response,
                }
            }
        };
        let requested_routing = request
            .query_params
            .get("routing")
            .cloned()
            .or_else(|| self.resolve_alias_search_routing(index));
        let index_mappings = {
            let manifest = self
                .metadata_manifest_state
                .lock()
                .expect("metadata manifest state lock poisoned");
            let mut mappings = std::collections::HashMap::new();
            for index_name in &resolved_indices {
                mappings.insert(
                    index_name.clone(),
                    manifest["indices"][index_name]["mappings"].clone(),
                );
            }
            mappings
        };
        if let Some(response) = self.validate_knn_target_capabilities(&body["query"], &resolved_indices) {
            return response;
        }
        let failed_indices = if let Some(field) = extract_geo_distance_field(&body["query"]) {
            let manifest = self
                .metadata_manifest_state
                .lock()
                .expect("metadata manifest state lock poisoned");
            resolved_indices
                .iter()
                .filter(|index_name| {
                    let field_type =
                        manifest["indices"][*index_name]["mappings"]["properties"][&field]["type"]
                            .as_str();
                    matches!(field_type, Some(value) if value != "geo_point" && value != "geo_shape")
                })
                .cloned()
                .collect::<std::collections::BTreeSet<_>>()
        } else {
            std::collections::BTreeSet::new()
        };
        let docs = self
            .documents_state
            .lock()
            .expect("documents state lock poisoned");
        let mut hits = Vec::new();
        for (key, record) in docs.iter() {
            let Some((doc_index, doc_id, _)) = split_document_key(key) else {
                continue;
            };
            if !resolved_indices.iter().any(|candidate| candidate == doc_index)
                || failed_indices.contains(doc_index)
            {
                continue;
            }
            if requested_routing
                .as_deref()
                .is_some_and(|routing| record.routing.as_deref() != Some(routing))
            {
                continue;
            }
            let effective_source = apply_runtime_mappings_to_source(&record.source, body.get("runtime_mappings"));
            if let Some((matched, score)) = evaluate_search_query_source_with_mappings(
                &effective_source,
                doc_id,
                &body["query"],
                index_mappings.get(doc_index).unwrap_or(&Value::Null),
            ) {
                if matched {
                    let mut hit = serde_json::json!({
                        "_index": doc_index,
                        "_id": doc_id,
                        "_source": record.source,
                        "_score": score,
                        "_seq_no": record.seq_no
                    });
                    if let Some(fields) = self.build_search_hit_fields(doc_index, &effective_source, &body) {
                        hit["fields"] = fields;
                    }
                    hits.push(hit);
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
        if let Some(rescore) = body.get("rescore") {
            apply_search_rescore(&mut hits, rescore);
        }
        let pure_knn_query = body["query"].get("knn").is_some();
        let total_matches_before_knn_limit = hits.len() as u64;
        if let Some(collapse) = body.get("collapse") {
            hits = apply_search_collapse(hits, collapse);
        }
        if let Some(knn_limit) = extract_knn_limit(&body["query"]) {
            hits.truncate(knn_limit);
        }
        let total_matches = if pure_knn_query {
            hits.len() as u64
        } else {
            total_matches_before_knn_limit
        };
        let mut total_value = total_matches;
        let mut total_relation = "eq";
        let mut terminated_early = false;
        if let Some(limit) = body.get("terminate_after").and_then(Value::as_u64) {
            if total_matches > limit {
                hits.truncate(limit as usize);
                total_value = limit;
                total_relation = "eq";
                terminated_early = true;
            }
        }
        if let Some(threshold) = body.get("track_total_hits").and_then(Value::as_u64) {
            if total_matches > threshold {
                total_value = threshold;
                total_relation = "gte";
            }
        }
        if let Some(search_after_values) = body.get("search_after").and_then(Value::as_array) {
            hits = apply_search_after(hits, &body["sort"], search_after_values);
        }
        let from = body.get("from").and_then(Value::as_u64).unwrap_or(0) as usize;
        let size = body.get("size").and_then(Value::as_u64).unwrap_or(10) as usize;
        let remaining_hits = if hits.len() > from + size {
            hits[(from + size)..].to_vec()
        } else {
            Vec::new()
        };
        let mut paged_hits: Vec<Value> = hits.iter().skip(from).take(size).cloned().collect();
        let scroll_id = request.query_params.get("scroll").map(|keep_alive| {
            self.store_scroll_context(remaining_hits.clone(), size, keep_alive)
        });
        if let Some(highlight) = body.get("highlight") {
            for hit in &mut paged_hits {
                let Some(hit_object) = hit.as_object_mut() else {
                    continue;
                };
                let Some(source) = hit_object.get("_source") else {
                    continue;
                };
                if let Some(highlight_body) =
                    build_highlight_response_body(source, &body["query"], highlight)
                {
                    hit_object.insert("highlight".to_string(), highlight_body);
                }
            }
        }
        if body.get("explain") == Some(&Value::Bool(true)) {
            for hit in &mut paged_hits {
                let Some(hit_object) = hit.as_object_mut() else {
                    continue;
                };
                let score = hit_object.get("_score").and_then(Value::as_f64).unwrap_or(1.0);
                hit_object.insert(
                    "_explanation".to_string(),
                    serde_json::json!({
                        "value": score,
                        "description": "bounded explain score",
                        "details": []
                    }),
                );
            }
        }
        let mut response = serde_json::Map::new();
        response.insert("took".to_string(), serde_json::json!(1));
        response.insert("timed_out".to_string(), serde_json::json!(false));
        let total_shards = resolved_indices
            .iter()
            .map(|index| self.index_primary_shard_count(index))
            .sum::<usize>()
            .max(1);
        let failed_shards = failed_indices
            .iter()
            .map(|index| self.index_primary_shard_count(index))
            .sum::<usize>();
        let skipped_shards = compute_can_match_skipped_shards(
            &body["query"],
            request.query_params.get("pre_filter_shard_size"),
            total_shards,
        );
        response.insert(
            "_shards".to_string(),
            serde_json::json!({
                "total": total_shards,
                "successful": total_shards.saturating_sub(failed_shards),
                "skipped": skipped_shards,
                "failed": failed_shards
            }),
        );
        response.insert(
            "hits".to_string(),
            serde_json::json!({
                "total": {
                    "value": total_value,
                    "relation": total_relation
                },
                "max_score": paged_hits
                    .iter()
                    .filter_map(|hit| hit.get("_score").and_then(Value::as_f64))
                    .max_by(|left, right| left.partial_cmp(right).unwrap_or(std::cmp::Ordering::Equal)),
                "hits": paged_hits
            }),
        );
        if terminated_early {
            response.insert("terminated_early".to_string(), Value::Bool(true));
        }
        if let Some(aggregations) = aggregations {
            response.insert("aggregations".to_string(), aggregations);
        }
        if let Some(suggest) = body.get("suggest") {
            response.insert(
                "suggest".to_string(),
                build_suggest_response_body(suggest, &resolved_indices, &docs),
            );
        }
        if body.get("profile") == Some(&Value::Bool(true)) {
            response.insert(
                "profile".to_string(),
                serde_json::json!({
                    "shards": [
                        {
                            "searches": [
                                {
                                    "query": [
                                        {
                                            "type": "bounded_query",
                                            "description": "Steelsearch bounded search profile",
                                            "time_in_nanos": 1
                                        }
                                    ],
                                    "rewrite_time": 0,
                                    "collector": [
                                        {
                                            "name": "simple_collector",
                                            "reason": "search_top_hits",
                                            "time_in_nanos": 1
                                        }
                                    ]
                                }
                            ],
                            "aggregations": []
                        }
                    ]
                }),
            );
        }
        if let Some(scroll_id) = scroll_id {
            response.insert("_scroll_id".to_string(), Value::String(scroll_id));
        }
        RestResponse::json(200, Value::Object(response))
    }

    fn handle_bulk_route(&self, default_index: Option<&str>, request: &RestRequest) -> RestResponse {
        let body = String::from_utf8_lossy(&request.body);
        let mut lines = body.lines();
        let mut items = Vec::new();
        let mut had_errors = false;
        let pipeline = request.query_params.get("pipeline").cloned();
        let forced_refresh = request
            .query_params
            .get("refresh")
            .is_some_and(|value| value == "wait_for" || value == "true");
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
            let effective_routing = if routing.is_empty() {
                self.resolve_alias_write_routing(&index)
            } else {
                Some(routing.clone())
            };
            let payload = match action.as_str() {
                "index" | "create" | "update" => lines
                    .next()
                    .and_then(|line| serde_json::from_str::<Value>(line).ok())
                    .unwrap_or(Value::Null),
                "delete" => Value::Null,
                _ => Value::Null,
            };
            let item = if let Some(pipeline_id) = pipeline.as_deref() {
                serde_json::json!({
                    action: {
                        "_index": index,
                        "_id": id,
                        "status": 400,
                        "error": {
                            "type": "illegal_argument_exception",
                            "reason": format!("pipeline with id [{pipeline_id}] does not exist")
                        }
                    }
                })
            } else {
                self.execute_bulk_action(
                    action,
                    &index,
                    &id,
                    effective_routing.as_deref(),
                    payload,
                    &meta,
                    forced_refresh,
                )
            };
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

    fn store_scroll_context(&self, remaining_hits: Vec<Value>, page_size: usize, _keep_alive: &str) -> String {
        let mut next_id = self
            .next_scroll_id
            .lock()
            .expect("next scroll id lock poisoned");
        *next_id += 1;
        let scroll_id = format!("scroll-{}", *next_id);
        self.scroll_contexts
            .lock()
            .expect("scroll contexts lock poisoned")
            .insert(
                scroll_id.clone(),
                ScrollContext {
                    remaining_hits,
                    page_size,
                },
            );
        scroll_id
    }

    fn handle_search_scroll_route(&self, request: &RestRequest) -> RestResponse {
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
        let scroll_id = body.get("scroll_id").and_then(Value::as_str).unwrap_or_default();
        if scroll_id.is_empty() {
            return build_unsupported_search_response("unsupported search scroll id");
        }
        let mut contexts = self
            .scroll_contexts
            .lock()
            .expect("scroll contexts lock poisoned");
        let Some(context) = contexts.get_mut(scroll_id) else {
            return RestResponse::json(
                404,
                serde_json::json!({
                    "error": {
                        "type": "search_context_missing_exception",
                        "reason": format!("No search context found for id [{scroll_id}]")
                    },
                    "status": 404
                }),
            );
        };
        let take = context.page_size.max(1);
        let page = context
            .remaining_hits
            .iter()
            .take(take)
            .cloned()
            .collect::<Vec<_>>();
        context.remaining_hits = context.remaining_hits.iter().skip(take).cloned().collect();
        RestResponse::json(
            200,
            serde_json::json!({
                "_scroll_id": scroll_id,
                "took": 1,
                "timed_out": false,
                "_shards": {
                    "total": 1,
                    "successful": 1,
                    "skipped": 0,
                    "failed": 0
                },
                "hits": {
                    "total": {
                        "value": page.len(),
                        "relation": "eq"
                    },
                    "max_score": page
                        .iter()
                        .filter_map(|hit| hit.get("_score").and_then(Value::as_f64))
                        .max_by(|left, right| left.partial_cmp(right).unwrap_or(std::cmp::Ordering::Equal)),
                    "hits": page
                }
            }),
        )
    }

    fn handle_clear_scroll_route(&self, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let mut scroll_ids = Vec::new();
        if let Some(scroll_id) = body.get("scroll_id").and_then(Value::as_str) {
            scroll_ids.push(scroll_id.to_string());
        } else if let Some(ids) = body.get("scroll_id").and_then(Value::as_array) {
            scroll_ids.extend(ids.iter().filter_map(Value::as_str).map(str::to_string));
        }
        let mut contexts = self
            .scroll_contexts
            .lock()
            .expect("scroll contexts lock poisoned");
        let mut freed = 0_u64;
        for scroll_id in scroll_ids {
            if contexts.remove(&scroll_id).is_some() {
                freed += 1;
            }
        }
        RestResponse::json(
            200,
            serde_json::json!({
                "succeeded": true,
                "num_freed": freed
            }),
        )
    }

    fn handle_open_point_in_time_route(&self, index: &str, request: &RestRequest) -> RestResponse {
        let keep_alive = request
            .query_params
            .get("keep_alive")
            .map(String::as_str)
            .unwrap_or("1m");
        let resolved_indices = match self.resolve_search_targets(index, false, false) {
            Ok(indices) => indices,
            Err(response) => return response,
        };
        let mut next_id = self
            .next_pit_id
            .lock()
            .expect("next pit id lock poisoned");
        *next_id += 1;
        let pit_id = format!("pit-{}", *next_id);
        self.pit_contexts
            .lock()
            .expect("pit contexts lock poisoned")
            .insert(
                pit_id.clone(),
                PitContext {
                    indices: resolved_indices,
                },
            );
        RestResponse::json(
            200,
            serde_json::json!({
                "id": pit_id,
                "keep_alive": keep_alive
            }),
        )
    }

    fn resolve_pit_indices(&self, pit_id: &str) -> Result<Vec<String>, RestResponse> {
        let contexts = self
            .pit_contexts
            .lock()
            .expect("pit contexts lock poisoned");
        let Some(context) = contexts.get(pit_id) else {
            return Err(RestResponse::json(
                404,
                serde_json::json!({
                    "error": {
                        "type": "search_context_missing_exception",
                        "reason": format!("No search context found for id [{pit_id}]")
                    },
                    "status": 404
                }),
            ));
        };
        Ok(context.indices.clone())
    }

    fn handle_close_point_in_time_route(&self, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let mut ids = Vec::new();
        if let Some(id) = body.get("id").and_then(Value::as_str) {
            ids.push(id.to_string());
        } else if let Some(id) = body.get("pit_id").and_then(Value::as_str) {
            ids.push(id.to_string());
        } else if let Some(id_array) = body.get("id").and_then(Value::as_array) {
            ids.extend(id_array.iter().filter_map(Value::as_str).map(str::to_string));
        } else if let Some(id_array) = body.get("pit_id").and_then(Value::as_array) {
            ids.extend(id_array.iter().filter_map(Value::as_str).map(str::to_string));
        }
        let mut contexts = self
            .pit_contexts
            .lock()
            .expect("pit contexts lock poisoned");
        let mut freed = 0_u64;
        for id in ids {
            if contexts.remove(&id).is_some() {
                freed += 1;
            }
        }
        RestResponse::json(
            200,
            serde_json::json!({
                "succeeded": true,
                "num_freed": freed
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
        meta: &serde_json::Map<String, Value>,
        forced_refresh: bool,
    ) -> Value {
        let resolved_index = match action {
            "index" | "create" => match self.resolve_write_target(index, true) {
                Ok(resolved_index) => resolved_index,
                Err(reason) => {
                    return serde_json::json!({
                        action: {
                            "_index": index,
                            "_id": id,
                            "status": 400,
                            "error": {
                                "type": "illegal_argument_exception",
                                "reason": reason
                            }
                        }
                    });
                }
            },
            "update" => match self.resolve_write_target(index, false) {
                Ok(resolved_index) => resolved_index,
                Err(reason) => {
                    return serde_json::json!({
                        action: {
                            "_index": index,
                            "_id": id,
                            "status": 400,
                            "error": {
                                "type": "illegal_argument_exception",
                                "reason": reason
                            }
                        }
                    });
                }
            },
            _ => self.resolve_index_or_alias(index),
        };
        let key = format!("{resolved_index}:{id}:{}", routing.unwrap_or_default());
        let external_version = meta
            .get("version")
            .and_then(Value::as_i64)
            .filter(|_| {
                meta.get("version_type")
                    .and_then(Value::as_str)
                    .is_some_and(|value| value == "external")
            });
        let expected_seq_no = meta.get("if_seq_no").and_then(Value::as_i64);
        let expected_primary_term = meta.get("if_primary_term").and_then(Value::as_i64);
        match action {
            "index" => {
                let mut docs = self.documents_state.lock().expect("documents state lock poisoned");
                let doc_existed = docs.contains_key(&key);
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
                        return serde_json::json!({
                            "index": {
                                "_index": resolved_index,
                                "_id": id,
                                "status": 409,
                                "error": {
                                    "type": "version_conflict_engine_exception",
                                    "reason": format!("[{id}]: version conflict in index [{index}]")
                                }
                            }
                        });
                    }
                }
                if let Some(version) = external_version {
                    if docs.get(&key).is_some_and(|record| version <= record.version) {
                        return serde_json::json!({
                            "index": {
                                "_index": resolved_index,
                                "_id": id,
                                "status": 409,
                                "error": {
                                    "type": "version_conflict_engine_exception",
                                    "reason": format!("[{id}]: version conflict, current version [{}] is higher or equal to the one provided [{version}]", docs.get(&key).map(|record| record.version).unwrap_or_default())
                                }
                            }
                        });
                    }
                }
                let mut next_seq_no = self.next_seq_no.lock().expect("seq_no lock poisoned");
                let assigned_seq_no = *next_seq_no;
                *next_seq_no += 1;
                let version = external_version
                    .or_else(|| docs.get(&key).map(|doc| doc.version + 1))
                    .unwrap_or(1);
                let result = if doc_existed { "updated" } else { "created" };
                let record = StoredDocument {
                    source: payload,
                    version,
                    seq_no: assigned_seq_no as i64,
                    primary_term: 1,
                    routing: routing.map(ToOwned::to_owned),
                    refreshed: forced_refresh,
                };
                docs.insert(key, record.clone());
                serde_json::json!({
                    "index": {
                        "_index": resolved_index,
                        "_id": id,
                        "_version": record.version,
                        "result": result,
                        "_seq_no": record.seq_no,
                        "_primary_term": record.primary_term,
                        "status": if doc_existed { 200 } else { 201 },
                        "forced_refresh": forced_refresh,
                    }
                })
            }
            "create" => {
                let mut docs = self.documents_state.lock().expect("documents state lock poisoned");
                if docs.contains_key(&key) {
                    return serde_json::json!({
                        "create": {
                            "_index": resolved_index,
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
                    version: external_version.unwrap_or(1),
                    seq_no: assigned_seq_no as i64,
                    primary_term: 1,
                    routing: routing.map(ToOwned::to_owned),
                    refreshed: forced_refresh,
                };
                docs.insert(key, record.clone());
                serde_json::json!({
                    "create": {
                        "_index": resolved_index,
                        "_id": id,
                        "_version": record.version,
                        "result": "created",
                        "_seq_no": record.seq_no,
                        "_primary_term": 1,
                        "status": 201,
                    }
                })
            }
            "delete" => {
                let mut docs = self.documents_state.lock().expect("documents state lock poisoned");
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
                        return serde_json::json!({
                            "delete": {
                                "_index": resolved_index,
                                "_id": id,
                                "status": 409,
                                "error": {
                                    "type": "version_conflict_engine_exception",
                                    "reason": format!("[{id}]: version conflict in index [{index}]")
                                }
                            }
                        });
                    }
                }
                let mut next_seq_no = self.next_seq_no.lock().expect("seq_no lock poisoned");
                let assigned_seq_no = *next_seq_no;
                *next_seq_no += 1;
                if let Some(record) = docs.remove(&key) {
                    serde_json::json!({
                        "delete": {
                            "_index": resolved_index,
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
                            "_index": resolved_index,
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
                        return serde_json::json!({
                            "update": {
                                "_index": resolved_index,
                                "_id": id,
                                "status": 409,
                                "error": {
                                    "type": "version_conflict_engine_exception",
                                    "reason": format!("[{id}]: version conflict in index [{index}]")
                                }
                            }
                        });
                    }
                }
                let mut next_seq_no = self.next_seq_no.lock().expect("seq_no lock poisoned");
                let assigned_seq_no = *next_seq_no;
                *next_seq_no += 1;
                if let Some(record) = docs.get_mut(&key) {
                    merge_json_object(&mut record.source, &doc_patch);
                    record.version += 1;
                    record.seq_no = assigned_seq_no as i64;
                    record.refreshed = forced_refresh;
                    return serde_json::json!({
                        "update": {
                            "_index": resolved_index,
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
                        refreshed: forced_refresh,
                    };
                    docs.insert(key, record.clone());
                    return serde_json::json!({
                        "update": {
                            "_index": resolved_index,
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
                        "_index": resolved_index,
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

    fn build_missing_template_delete_error(name: &str) -> Value {
        serde_json::json!({
            "error": {
                "type": "index_template_missing_exception",
                "reason": format!("index_template [{name}] missing")
            },
            "status": 404
        })
    }

    fn build_missing_component_template_get_error(name: &str) -> Value {
        serde_json::json!({
            "error": {
                "type": "resource_not_found_exception",
                "reason": format!("component template matching [{name}] not found")
            },
            "status": 404
        })
    }

    fn build_missing_index_template_get_error(name: &str) -> Value {
        serde_json::json!({
            "error": {
                "type": "resource_not_found_exception",
                "reason": format!("index template matching [{name}] not found")
            },
            "status": 404
        })
    }

    fn build_component_template_array_readback(
        templates: &Value,
        target: Option<&str>,
    ) -> Value {
        let selected =
            template_route_registration::invoke_component_template_live_readback(templates, target);
        let entries = selected
            .as_object()
            .into_iter()
            .flat_map(|templates| templates.iter())
            .map(|(name, template)| {
                serde_json::json!({
                    "name": name,
                    "component_template": template["component_template"].clone()
                })
            })
            .collect::<Vec<_>>();
        serde_json::json!({ "component_templates": entries })
    }

    fn build_index_template_array_readback(templates: &Value, target: Option<&str>) -> Value {
        let selected =
            template_route_registration::invoke_index_template_live_readback(templates, target);
        let entries = selected
            .as_object()
            .into_iter()
            .flat_map(|templates| templates.iter())
            .map(|(name, template)| {
                serde_json::json!({
                    "name": name,
                    "index_template": template["index_template"].clone()
                })
            })
            .collect::<Vec<_>>();
        serde_json::json!({ "index_templates": entries })
    }

    fn handle_component_template_get_route(&self, target: Option<&str>) -> RestResponse {
        let manifest = self.metadata_manifest_state.lock().expect("metadata manifest state lock poisoned");
        let body = Self::build_component_template_array_readback(
            &manifest["templates"]["component_templates"],
            target,
        );
        if let Some(name) = target {
            let exact = !name.contains('*') && !name.contains(',');
            let is_empty = body["component_templates"]
                .as_array()
                .map(|templates| templates.is_empty())
                .unwrap_or(true);
            if exact && is_empty {
                return RestResponse::json(404, Self::build_missing_component_template_get_error(name));
            }
        }
        RestResponse::json(200, body)
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
        if let Some(name) = target {
            if name.contains(',') {
                return RestResponse::json(404, Self::build_missing_index_template_get_error(name));
            }
        }
        let body = Self::build_index_template_array_readback(
            &manifest["templates"]["index_templates"],
            target,
        );
        if let Some(name) = target {
            let exact = !name.contains('*') && !name.contains(',');
            let is_empty = body["index_templates"]
                .as_array()
                .map(|templates| templates.is_empty())
                .unwrap_or(true);
            if exact && is_empty {
                return RestResponse::json(404, Self::build_missing_index_template_get_error(name));
            }
        }
        RestResponse::json(200, body)
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
        let body = legacy_template_route_registration::invoke_legacy_template_live_readback(
            &manifest["templates"]["legacy_index_templates"],
            target,
        );
        if let Some(name) = target {
            let exact = !name.contains('*') && !name.contains(',');
            if exact && body.as_object().map(|templates| templates.is_empty()).unwrap_or(true) {
                return RestResponse::json(404, serde_json::json!({}));
            }
        }
        RestResponse::json(200, body)
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
        let template_exists = manifest["templates"]["component_templates"]
            .as_object()
            .map(|templates| templates.contains_key(name))
            .unwrap_or(false);
        if !template_exists {
            return RestResponse::json(404, Self::build_missing_template_delete_error(name));
        }
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
        let removed = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned")["templates"]["index_templates"]
            .as_object_mut()
            .and_then(|templates| templates.remove(name));
        if removed.is_none() {
            return RestResponse::json(404, Self::build_missing_template_delete_error(name));
        }
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, serde_json::json!({ "acknowledged": true }))
    }

    fn handle_legacy_template_delete_route(&self, name: &str) -> RestResponse {
        let removed = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned")["templates"]["legacy_index_templates"]
            .as_object_mut()
            .and_then(|templates| templates.remove(name));
        if removed.is_none() {
            return RestResponse::json(404, Self::build_missing_template_delete_error(name));
        }
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
            &render_cluster_settings_section(&next_persistent, false),
            &render_cluster_settings_section(&next_transient, false),
        );
        let mut next_state = self
            .cluster_settings_state
            .lock()
            .expect("cluster settings state lock poisoned");
        *next_state = serde_json::json!({
            "persistent": next_persistent,
            "transient": next_transient
        });
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(200, response_body)
    }

    fn handle_cluster_settings_get_route(&self, request: &RestRequest) -> RestResponse {
        let params = request
            .query_params
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>();
        let body = self.cluster_settings_body(
            query_param_is_true(request.query_params.get("flat_settings")),
            query_param_is_true(request.query_params.get("include_defaults")),
        );
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
                    "node": self.tasks_body().get("node").cloned().unwrap_or_else(|| serde_json::json!({})),
                    "task": task
                })),
            );
        }
        RestResponse::json(200, self.unknown_task_cancel_body(task_id))
    }

    fn cluster_health_body(&self, target: Option<&str>) -> Option<Value> {
        let node_count = self
            .cluster_view
            .as_ref()
            .map(|view| view.nodes.len())
            .unwrap_or_default() as u64;
        let created_indices = self
            .created_indices_state
            .lock()
            .expect("created indices state lock poisoned");
        let scoped_index_count = match target {
            None => created_indices.len() as u64,
            Some(selector) => {
                let selected = created_indices
                    .iter()
                    .filter(|index| matches_index_selector(selector, index))
                    .count() as u64;
                if selected == 0 {
                    return None;
                }
                selected
            }
        };
        let unassigned_shards = if node_count == 1 { scoped_index_count } else { 0 };
        let active_primary_shards = scoped_index_count;
        let active_shards = scoped_index_count;
        let status = if unassigned_shards > 0 { "yellow" } else { "green" };
        let active_shards_percent = if scoped_index_count == 0 {
            100.0
        } else {
            (active_shards as f64 / (active_shards + unassigned_shards) as f64) * 100.0
        };
        Some(serde_json::json!({
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
        }))
    }

    fn cluster_state_body(&self) -> Value {
        let view = self.cluster_view.clone().unwrap_or_default();
        let mut nodes = serde_json::Map::new();
        let master_node = view
            .nodes
            .first()
            .map(|node| node.node_id.clone())
            .unwrap_or_else(|| "node-a".to_string());
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
        let mut routing_nodes = Vec::new();
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
            routing_nodes.push(serde_json::json!({
                "index": index,
                "node": master_node.clone(),
                "primary": true,
                "state": "STARTED",
                "shard": 0
            }));
        }
        let mut routing_node_map = serde_json::Map::new();
        routing_node_map.insert(master_node.clone(), Value::Array(routing_nodes));
        serde_json::json!({
            "cluster_name": view.cluster_name,
            "cluster_uuid": view.cluster_uuid,
            "version": 1,
            "state_uuid": "steelsearch-state-uuid",
            "master_node": master_node,
            "blocks": {},
            "metadata": {
                "cluster_uuid": view.cluster_uuid,
                "indices": metadata_indices
            },
            "nodes": nodes,
            "routing_nodes": {
                "unassigned": [],
                "nodes": routing_node_map
            },
            "routing_table": {
                "indices": routing_indices
            }
        })
    }

    fn cluster_settings_body(&self, flat_settings: bool, _include_defaults: bool) -> Value {
        let state = self
            .cluster_settings_state
            .lock()
            .expect("cluster settings state lock poisoned")
            .clone();
        let persistent = render_cluster_settings_section(
            state.get("persistent")
                .unwrap_or(&Value::Object(serde_json::Map::new())),
            flat_settings,
        );
        let transient = render_cluster_settings_section(
            state.get("transient")
                .unwrap_or(&Value::Object(serde_json::Map::new())),
            flat_settings,
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
        let view = self.cluster_view.clone().unwrap_or_default();
        let local_node = view.nodes.first().cloned().unwrap_or_default();
        let node_attributes = serde_json::json!({
            "testattr": "test",
            "shard_indexing_pressure_enabled": "true"
        });
        let body = if primary {
            serde_json::json!({
                "index": index,
                "shard": shard,
                "primary": true,
                "current_state": "started",
                "can_remain_on_current_node": "yes",
                "can_rebalance_cluster": "no",
                "can_rebalance_to_other_node": "no",
                "rebalance_explanation": "rebalancing is not allowed",
                "can_rebalance_cluster_decisions": [
                    {
                        "decider": "rebalance_only_when_active",
                        "decision": "NO",
                        "explanation": "rebalancing is not allowed until all replicas in the cluster are active"
                    },
                    {
                        "decider": "cluster_rebalance",
                        "decision": "NO",
                        "explanation": "the cluster has unassigned shards and cluster setting [cluster.routing.allocation.allow_rebalance] is set to [indices_all_active]"
                    }
                ],
                "current_node": {
                    "id": local_node.node_id,
                    "name": local_node.node_name,
                    "transport_address": local_node.transport_address,
                    "weight_ranking": 1,
                    "attributes": node_attributes.clone(),
                }
            })
        } else {
            serde_json::json!({
                "index": index,
                "shard": shard,
                "primary": false,
                "current_state": "unassigned",
                "can_allocate": "no",
                "allocate_explanation": "cannot allocate because allocation is not permitted to any of the nodes",
                "unassigned_info": {
                    "reason": "INDEX_CREATED",
                    "last_allocation_status": "no_attempt"
                },
                "node_allocation_decisions": [
                    {
                        "node_name": local_node.node_name,
                        "node_id": local_node.node_id,
                        "transport_address": local_node.transport_address,
                        "node_attributes": node_attributes,
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
        let view = self.cluster_view.clone().unwrap_or_default();
        let node = view
            .nodes
            .iter()
            .find(|candidate| candidate.node_id == view.local_node_id)
            .or_else(|| view.nodes.first());
        serde_json::json!({
            "node": node.map(|node| serde_json::json!({
                "name": node.node_name,
                "transport_address": node.transport_address,
                "host": "127.0.0.1",
                "ip": node.transport_address,
                "roles": node.roles,
                "attributes": {
                    "testattr": "test",
                    "shard_indexing_pressure_enabled": "true"
                }
            })).unwrap_or_else(|| serde_json::json!({})),
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
                    "timestamp": 1,
                    "name": node.node_name,
                    "host": "127.0.0.1",
                    "ip": node.transport_address,
                    "roles": node.roles,
                    "attributes": {
                        "testattr": "test",
                        "shard_indexing_pressure_enabled": "true"
                    },
                    "transport_address": node.transport_address,
                    "http": {
                        "publish_address": node.http_address
                    },
                    "indices": {
                        "docs": {
                            "count": 0
                        }
                    },
                    "process": {
                        "open_file_descriptors": 0
                    },
                    "jvm": {
                        "mem": {
                            "heap_used_in_bytes": 0
                        }
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
            "status": if node_count <= 1 { "yellow" } else { "green" },
            "indices": {
                "count": index_count,
                "docs": {
                    "count": 0
                },
                "shards": {
                    "total": index_count
                }
            },
            "nodes": {
                "count": {
                    "total": node_count,
                    "data": node_count
                }
            },
            "fs": {
                "total_in_bytes": 0
            }
        })
    }

    fn index_stats_body(&self) -> Value {
        let created_indices = self
            .created_indices_state
            .lock()
            .expect("created indices state lock poisoned")
            .clone();
        let created_index_count = created_indices.len();
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
            "_shards": {
                "total": created_index_count,
                "successful": created_index_count,
                "failed": 0
            },
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
                        "type": "transport",
                        "action": "cluster:admin/reroute",
                        "start_time_in_millis": 1,
                        "running_time_in_nanos": 1,
                        "cancellable": false,
                        "cancelled": false,
                        "headers": {},
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
                            "type": "transport",
                            "action": "cluster:admin/publication",
                            "start_time_in_millis": 1,
                            "running_time_in_nanos": 1,
                            "cancellable": false,
                            "cancelled": false,
                            "headers": {},
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
        let resolved_index = match self.resolve_write_target(index, true) {
            Ok(resolved_index) => resolved_index,
            Err(reason) => {
                return RestResponse::json(
                    400,
                    serde_json::json!({
                        "error": {
                            "type": "illegal_argument_exception",
                            "reason": reason
                        },
                        "status": 400
                    }),
                );
            }
        };
        let source = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let routing = request
            .query_params
            .get("routing")
            .cloned()
            .or_else(|| self.resolve_alias_write_routing(index));
        let key = format!("{resolved_index}:{id}:{}", routing.clone().unwrap_or_default());
        let mut docs = self.documents_state.lock().expect("documents state lock poisoned");
        let doc_existed = docs.contains_key(&key);
        let expected_seq_no = request
            .query_params
            .get("if_seq_no")
            .and_then(|value| value.parse::<i64>().ok());
        let expected_primary_term = request
            .query_params
            .get("if_primary_term")
            .and_then(|value| value.parse::<i64>().ok());
        let external_version = request
            .query_params
            .get("version")
            .and_then(|value| value.parse::<i64>().ok())
            .filter(|_| {
                request
                    .query_params
                    .get("version_type")
                    .is_some_and(|value| value == "external")
            });
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
        if let Some(version) = external_version {
            let conflict = docs
                .get(&key)
                .is_some_and(|record| version <= record.version);
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
        let version = external_version
            .or_else(|| docs.get(&key).map(|doc| doc.version + 1))
            .unwrap_or(1);
        let forced_refresh = request
            .query_params
            .get("refresh")
            .is_some_and(|value| value == "wait_for" || value == "true");
        let record = StoredDocument {
            source,
            version,
            seq_no: assigned_seq_no as i64,
            primary_term: 1,
            routing,
            refreshed: forced_refresh,
        };
        let response = serde_json::json!({
            "_index": self.write_response_index(index, &resolved_index),
            "_id": id,
            "_version": record.version,
            "result": if doc_existed { "updated" } else { "created" },
            "_seq_no": record.seq_no,
            "_primary_term": record.primary_term,
            "forced_refresh": forced_refresh,
        });
        docs.insert(key, record);
        drop(docs);
        drop(next_seq_no);
        self.persist_shared_runtime_state_to_disk();
        RestResponse::json(if doc_existed { 200 } else { 201 }, response)
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
        let routing = request
            .query_params
            .get("routing")
            .cloned()
            .or_else(|| self.resolve_alias_read_routing(index))
            .unwrap_or_default();
        let key = format!("{resolved_index}:{id}:{routing}");
        let docs = self.documents_state.lock().expect("documents state lock poisoned");
        let realtime = request
            .query_params
            .get("realtime")
            .map_or(true, |value| value != "false");
        let record = docs.get(&key).or_else(|| {
            if routing.is_empty() {
                docs.iter()
                    .find(|(candidate, _)| candidate.starts_with(&format!("{resolved_index}:{id}:")))
                    .map(|(_, record)| record)
            } else {
                None
            }
        }).filter(|record| realtime || record.refreshed);
        if let Some(record) = record {
            let mut source = record.source.clone();
            let include_source = request
                .query_params
                .get("_source")
                .map_or(true, |value| value != "false");
            if include_source {
                if let Some(includes) = request.query_params.get("_source_includes") {
                    source = filter_source_fields(&source, includes);
                }
                if let Some(excludes) = request.query_params.get("_source_excludes") {
                    source = exclude_source_fields(&source, excludes);
                }
            }
            let response_index = if resolved_index != index && self.resolve_alias_read_routing(index).is_some() {
                resolved_index.clone()
            } else if resolved_index == index {
                resolved_index.clone()
            } else {
                index.to_string()
            };
            let mut response = serde_json::json!({
                "_index": response_index,
                "_id": id,
                "_version": record.version,
                "_seq_no": record.seq_no,
                "_primary_term": record.primary_term,
                "found": true,
            });
            if include_source {
                response["_source"] = source;
            }
            return RestResponse::json(200, response);
        }
        RestResponse::json(
            404,
            single_doc_get_route_registration::build_get_doc_not_found_response(&resolved_index, id),
        )
    }

    fn handle_delete_doc_route(&self, index: &str, id: &str, request: &RestRequest) -> RestResponse {
        let resolved_index = self.resolve_index_or_alias(index);
        let routing = request
            .query_params
            .get("routing")
            .cloned()
            .or_else(|| self.resolve_alias_read_routing(index))
            .unwrap_or_default();
        let key = format!("{resolved_index}:{id}:{routing}");
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
        if let Some(record) = docs.remove(&key) {
            let mut next_seq_no = self.next_seq_no.lock().expect("seq_no lock poisoned");
            let assigned_seq_no = *next_seq_no;
            *next_seq_no += 1;
            let response_index = if resolved_index != index && self.resolve_alias_read_routing(index).is_some() {
                resolved_index.clone()
            } else {
                resolved_index.clone()
            };
            let response = RestResponse::json(200, serde_json::json!({
                "_index": response_index,
                "_id": id,
                "_version": record.version + 1,
                "result": "deleted",
                "_seq_no": assigned_seq_no,
                "_primary_term": record.primary_term,
                "forced_refresh": request
                    .query_params
                    .get("refresh")
                    .is_some_and(|value| value == "wait_for" || value == "true"),
            }));
            drop(docs);
            drop(next_seq_no);
            self.persist_shared_runtime_state_to_disk();
            return response;
        }
        RestResponse::json(
            404,
            single_doc_delete_route_registration::build_delete_doc_not_found_response(&resolved_index, id),
        )
    }

    fn handle_update_doc_route(&self, index: &str, id: &str, request: &RestRequest) -> RestResponse {
        let resolved_index = match self.resolve_write_target(index, false) {
            Ok(resolved_index) => resolved_index,
            Err(reason) => {
                return RestResponse::json(
                    400,
                    serde_json::json!({
                        "error": {
                            "type": "illegal_argument_exception",
                            "reason": reason
                        },
                        "status": 400
                    }),
                );
            }
        };
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let routing = request
            .query_params
            .get("routing")
            .cloned()
            .or_else(|| self.resolve_alias_write_routing(index));
        let key = format!("{resolved_index}:{id}:{}", routing.clone().unwrap_or_default());
        let doc_patch = body.get("doc").cloned().unwrap_or_else(|| serde_json::json!({}));
        let upsert = body.get("upsert").cloned().unwrap_or(Value::Null);
        let doc_as_upsert = body.get("doc_as_upsert").and_then(Value::as_bool).unwrap_or(false);
        let scripted_upsert = body.get("scripted_upsert").and_then(Value::as_bool).unwrap_or(false);
        let detect_noop = body.get("detect_noop").and_then(Value::as_bool).unwrap_or(true);
        let script = body.get("script").cloned();
        let forced_refresh = request
            .query_params
            .get("refresh")
            .is_some_and(|value| value == "wait_for" || value == "true");
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
                    crate::single_doc_update_route_registration::build_update_doc_version_conflict_error(&resolved_index, id),
                );
            }
        }
        let mut next_seq_no = self.next_seq_no.lock().expect("seq_no lock poisoned");
        let assigned_seq_no = *next_seq_no;
        *next_seq_no += 1;
        if let Some(record) = docs.get_mut(&key) {
            let original_source = record.source.clone();
            if let Some(script) = script.as_ref() {
                if let Err(response) = apply_supported_update_script(&mut record.source, script) {
                    return response;
                }
            } else {
                merge_json_object(&mut record.source, &doc_patch);
            }
            if detect_noop && record.source == original_source {
                return RestResponse::json(200, serde_json::json!({
                    "_index": self.write_response_index(index, &resolved_index),
                    "_id": id,
                    "_version": record.version,
                    "result": "noop",
                    "_seq_no": record.seq_no,
                    "_primary_term": record.primary_term,
                    "forced_refresh": forced_refresh,
                }));
            }
            record.version += 1;
            record.seq_no = assigned_seq_no as i64;
            record.refreshed = forced_refresh;
            let response = RestResponse::json(200, serde_json::json!({
                "_index": self.write_response_index(index, &resolved_index),
                "_id": id,
                "_version": record.version,
                "result": "updated",
                "_seq_no": record.seq_no,
                "_primary_term": record.primary_term,
                "forced_refresh": forced_refresh,
            }));
            drop(docs);
            drop(next_seq_no);
            self.persist_shared_runtime_state_to_disk();
            return response;
        }
        if scripted_upsert && script.is_some() {
            let mut source = if upsert.is_null() {
                serde_json::json!({})
            } else {
                upsert
            };
            if let Err(response) = apply_supported_update_script(&mut source, script.as_ref().expect("checked script presence")) {
                return response;
            }
            let record = StoredDocument {
                source,
                version: 1,
                seq_no: assigned_seq_no as i64,
                primary_term: 1,
                routing,
                refreshed: forced_refresh,
            };
            let response = serde_json::json!({
                "_index": self.write_response_index(index, &resolved_index),
                "_id": id,
                "_version": 1,
                "result": "created",
                "_seq_no": record.seq_no,
                "_primary_term": 1,
                "forced_refresh": forced_refresh,
            });
            docs.insert(key, record);
            drop(docs);
            drop(next_seq_no);
            self.persist_shared_runtime_state_to_disk();
            return RestResponse::json(201, response);
        }
        if doc_as_upsert || !upsert.is_null() {
            let source = if doc_as_upsert { doc_patch } else { upsert };
            let record = StoredDocument {
                source,
                version: 1,
                seq_no: assigned_seq_no as i64,
                primary_term: 1,
                routing,
                refreshed: forced_refresh,
            };
            let response = serde_json::json!({
                "_index": self.write_response_index(index, &resolved_index),
                "_id": id,
                "_version": 1,
                "result": "created",
                "_seq_no": record.seq_no,
                "_primary_term": 1,
                "forced_refresh": forced_refresh,
            });
            docs.insert(key, record);
            drop(docs);
            drop(next_seq_no);
            self.persist_shared_runtime_state_to_disk();
            return RestResponse::json(201, response);
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
                        "training_requests": state.training_requests,
                        "model_count": state.trained_models.len(),
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

    fn handle_knn_model_train_route(&self, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let training_index = body
            .get("training_index")
            .and_then(Value::as_str)
            .unwrap_or("vector-search-compat-000001")
            .to_string();
        let dimension = body.get("dimension").and_then(Value::as_u64).unwrap_or(0);
        let description = body
            .get("description")
            .and_then(Value::as_str)
            .unwrap_or("bounded knn model")
            .to_string();
        let method = body.get("method").cloned().unwrap_or_else(|| serde_json::json!({
            "name": "hnsw",
            "engine": "lucene"
        }));
        let mut state = self
            .knn_operational_state
            .lock()
            .expect("knn operational state lock poisoned");
        let current = state.get_or_insert_with(KnnOperationalState::default);
        current.training_requests += 1;
        let model_id = format!("knn-model-{}", current.training_requests);
        let model = KnnModelState {
            model_id: model_id.clone(),
            training_index,
            dimension,
            description,
            method,
            state: "created".to_string(),
        };
        current.trained_models.insert(model_id.clone(), model.clone());
        current.model_cache_used_bytes = current.model_cache_used_bytes.max(model.dimension.saturating_mul(8));
        RestResponse::json(
            200,
            serde_json::json!({
                "model_id": model_id,
                "state": model.state,
                "training_index": model.training_index
            }),
        )
    }

    fn handle_knn_model_get_route(&self, model_id: &str) -> RestResponse {
        let state = self
            .knn_operational_state
            .lock()
            .expect("knn operational state lock poisoned");
        let Some(current) = state.as_ref() else {
            return RestResponse::json(404, serde_json::json!({
                "error": {
                    "type": "resource_not_found_exception",
                    "reason": format!("k-NN model [{model_id}] missing")
                },
                "status": 404
            }));
        };
        let Some(model) = current.trained_models.get(model_id) else {
            return RestResponse::json(404, serde_json::json!({
                "error": {
                    "type": "resource_not_found_exception",
                    "reason": format!("k-NN model [{model_id}] missing")
                },
                "status": 404
            }));
        };
        RestResponse::json(200, serde_json::json!({
            "model_id": model.model_id,
            "training_index": model.training_index,
            "dimension": model.dimension,
            "description": model.description,
            "method": model.method,
            "state": model.state
        }))
    }

    fn handle_knn_model_delete_route(&self, model_id: &str) -> RestResponse {
        let mut state = self
            .knn_operational_state
            .lock()
            .expect("knn operational state lock poisoned");
        let Some(current) = state.as_mut() else {
            return RestResponse::json(404, serde_json::json!({
                "error": {
                    "type": "resource_not_found_exception",
                    "reason": format!("k-NN model [{model_id}] missing")
                },
                "status": 404
            }));
        };
        if current.trained_models.remove(model_id).is_none() {
            return RestResponse::json(404, serde_json::json!({
                "error": {
                    "type": "resource_not_found_exception",
                    "reason": format!("k-NN model [{model_id}] missing")
                },
                "status": 404
            }));
        }
        RestResponse::json(200, serde_json::json!({
            "result": "deleted",
            "model_id": model_id
        }))
    }

    fn handle_knn_model_search_route(&self, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let filter_model_id = body
            .get("query")
            .and_then(Value::as_object)
            .and_then(|query| query.get("term"))
            .and_then(Value::as_object)
            .and_then(|term| term.get("model_id"))
            .and_then(Value::as_str);
        let state = self
            .knn_operational_state
            .lock()
            .expect("knn operational state lock poisoned");
        let models = state
            .as_ref()
            .map(|current| current.trained_models.values().cloned().collect::<Vec<_>>())
            .unwrap_or_default();
        let hits: Vec<Value> = models
            .into_iter()
            .filter(|model| filter_model_id.map(|value| value == model.model_id).unwrap_or(true))
            .map(|model| serde_json::json!({
                "_id": model.model_id,
                "_source": {
                    "training_index": model.training_index,
                    "dimension": model.dimension,
                    "description": model.description,
                    "method": model.method,
                    "state": model.state
                }
            }))
            .collect();
        RestResponse::json(200, serde_json::json!({
            "hits": {
                "total": {
                    "value": hits.len(),
                    "relation": "eq"
                },
                "hits": hits
            }
        }))
    }

    fn handle_ml_model_register_route(&self, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let name = body.get("name").and_then(Value::as_str).unwrap_or("bounded-ml-model").to_string();
        let function_name = body.get("function_name").and_then(Value::as_str).unwrap_or("text_embedding").to_string();
        let dimension = body.get("dimension").and_then(Value::as_u64).unwrap_or(3);
        let mut next = self.next_ml_model_id.lock().expect("next ml model id lock poisoned");
        *next += 1;
        let model_id = format!("ml-model-{}", *next);
        drop(next);
        let model = MlModelState {
            model_id: model_id.clone(),
            name,
            function_name,
            dimension,
            deployed: false,
        };
        self.ml_models_state
            .lock()
            .expect("ml models state lock poisoned")
            .insert(model_id.clone(), model.clone());
        RestResponse::json(200, serde_json::json!({
            "model_id": model_id,
            "name": model.name,
            "function_name": model.function_name,
            "model_state": "registered"
        }))
    }

    fn handle_ml_model_get_route(&self, model_id: &str) -> RestResponse {
        let models = self.ml_models_state.lock().expect("ml models state lock poisoned");
        let Some(model) = models.get(model_id) else {
            return RestResponse::json(404, serde_json::json!({
                "error": {
                    "type": "resource_not_found_exception",
                    "reason": format!("ML model [{model_id}] missing")
                },
                "status": 404
            }));
        };
        RestResponse::json(200, serde_json::json!({
            "model_id": model.model_id,
            "name": model.name,
            "function_name": model.function_name,
            "dimension": model.dimension,
            "deployed": model.deployed
        }))
    }

    fn handle_ml_model_search_route(&self, request: &RestRequest) -> RestResponse {
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let filter_model_id = body
            .get("query")
            .and_then(Value::as_object)
            .and_then(|query| query.get("term"))
            .and_then(Value::as_object)
            .and_then(|term| term.get("model_id"))
            .and_then(Value::as_str);
        let models = self.ml_models_state.lock().expect("ml models state lock poisoned");
        let hits: Vec<Value> = models
            .values()
            .filter(|model| filter_model_id.map(|value| value == model.model_id).unwrap_or(true))
            .map(|model| serde_json::json!({
                "_id": model.model_id,
                "_source": {
                    "name": model.name,
                    "function_name": model.function_name,
                    "dimension": model.dimension,
                    "deployed": model.deployed
                }
            }))
            .collect();
        RestResponse::json(200, serde_json::json!({
            "hits": {
                "total": { "value": hits.len(), "relation": "eq" },
                "hits": hits
            }
        }))
    }

    fn handle_ml_model_deploy_route(&self, model_id: &str, deployed: bool) -> RestResponse {
        let mut models = self.ml_models_state.lock().expect("ml models state lock poisoned");
        let Some(model) = models.get_mut(model_id) else {
            return RestResponse::json(404, serde_json::json!({
                "error": {
                    "type": "resource_not_found_exception",
                    "reason": format!("ML model [{model_id}] missing")
                },
                "status": 404
            }));
        };
        model.deployed = deployed;
        RestResponse::json(200, serde_json::json!({
            "model_id": model_id,
            "deployed": deployed,
            "task_state": if deployed { "DEPLOYED" } else { "UNDEPLOYED" }
        }))
    }

    fn handle_ml_model_predict_route(&self, model_id: &str, request: &RestRequest) -> RestResponse {
        let models = self.ml_models_state.lock().expect("ml models state lock poisoned");
        let Some(model) = models.get(model_id) else {
            return RestResponse::json(404, serde_json::json!({
                "error": {
                    "type": "resource_not_found_exception",
                    "reason": format!("ML model [{model_id}] missing")
                },
                "status": 404
            }));
        };
        if !model.deployed {
            return RestResponse::json(409, serde_json::json!({
                "error": {
                    "type": "conflict_exception",
                    "reason": format!("ML model [{model_id}] is not deployed")
                },
                "status": 409
            }));
        }
        let body = serde_json::from_slice::<Value>(&request.body).unwrap_or(Value::Null);
        let text_input = body
            .get("text_docs")
            .and_then(Value::as_array)
            .and_then(|docs| docs.first())
            .and_then(Value::as_str)
            .unwrap_or("");
        let embedding = serde_json::json!([
            text_input.len() as f64,
            text_input.split_whitespace().count() as f64,
            text_input.chars().filter(|ch| "aeiou".contains(ch.to_ascii_lowercase())).count() as f64
        ]);
        RestResponse::json(200, serde_json::json!({
            "inference_results": [
                {
                    "model_id": model_id,
                    "output": [embedding]
                }
            ]
        }))
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
        let verbose = request.query_params.get("v").is_some_and(|value| value == "true");
        let mut lines = Vec::new();
        if verbose {
            lines.push("health status index pri rep docs.count store.size".to_string());
        }
        for row in &rows {
            lines.push(format!(
                "{} {} {} {} {} {} {}",
                row["health"].as_str().unwrap_or("yellow"),
                row["status"].as_str().unwrap_or("open"),
                row["index"].as_str().unwrap_or(""),
                row["pri"].as_str().unwrap_or("1"),
                row["rep"].as_str().unwrap_or("0"),
                row["docs.count"].as_str().unwrap_or("0"),
                row["store.size"].as_str().unwrap_or("0b"),
            ));
        }
        RestResponse::text(200, lines.join("\n") + "\n")
    }

    fn handle_cat_count_route(&self, request: &RestRequest) -> RestResponse {
        let docs = self
            .documents_state
            .lock()
            .expect("documents state lock poisoned");
        let count = docs.len().to_string();
        let row = serde_json::json!({
            "epoch": "0",
            "timestamp": "00:00:00",
            "count": count
        });
        if request.query_params.get("format").is_some_and(|value| value == "json") {
            return RestResponse::json(200, Value::Array(vec![row]));
        }
        let verbose = request.query_params.get("v").is_some_and(|value| value == "true");
        let mut lines = Vec::new();
        if verbose {
            lines.push("epoch timestamp count".to_string());
        }
        lines.push(format!(
            "{} {} {}",
            row["epoch"].as_str().unwrap_or("0"),
            row["timestamp"].as_str().unwrap_or("00:00:00"),
            row["count"].as_str().unwrap_or("0"),
        ));
        RestResponse::text(200, lines.join("\n") + "\n")
    }

    fn handle_cat_plugins_route(&self, request: &RestRequest) -> RestResponse {
        let node_name = self
            .cluster_view
            .as_ref()
            .and_then(|view| view.nodes.first())
            .map(|node| node.node_name.clone())
            .unwrap_or_else(|| self.info.name.clone());
        let rows = vec![
            serde_json::json!({
                "name": node_name,
                "component": "steelsearch-runtime",
                "version": "1.0.0-dev",
                "description": "Steelsearch development runtime plugin surface",
                "classname": "org.steelsearch.runtime.Plugin"
            }),
        ];
        if request.query_params.get("format").is_some_and(|value| value == "json") {
            return RestResponse::json(200, Value::Array(rows));
        }
        let verbose = request.query_params.get("v").is_some_and(|value| value == "true");
        let mut lines = Vec::new();
        if verbose {
            lines.push("name component version description classname".to_string());
        }
        for row in &rows {
            lines.push(format!(
                "{} {} {} {} {}",
                row["name"].as_str().unwrap_or(""),
                row["component"].as_str().unwrap_or(""),
                row["version"].as_str().unwrap_or(""),
                row["description"].as_str().unwrap_or(""),
                row["classname"].as_str().unwrap_or(""),
            ));
        }
        RestResponse::text(200, lines.join("\n") + "\n")
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

    fn resolve_write_index_or_alias(&self, target: &str) -> String {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        if manifest["indices"].get(target).is_some() {
            return target.to_string();
        }
        if let Some(indices) = manifest["indices"].as_object() {
            for (index, body) in indices {
                let Some(alias_state) = body["aliases"].get(target) else {
                    continue;
                };
                if alias_state
                    .get("is_write_index")
                    .and_then(Value::as_bool)
                    .unwrap_or(false)
                {
                    return index.clone();
                }
            }
            for (index, body) in indices {
                if body["aliases"].get(target).is_some() {
                    return index.clone();
                }
            }
        }
        target.to_string()
    }

    fn resolve_alias_write_routing(&self, target: &str) -> Option<String> {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let indices = manifest["indices"].as_object()?;
        for body in indices.values() {
            let Some(alias_state) = body["aliases"].get(target) else {
                continue;
            };
            if let Some(routing) = alias_state.get("index_routing").and_then(Value::as_str) {
                return Some(routing.to_string());
            }
            if let Some(routing) = alias_state.get("search_routing").and_then(Value::as_str) {
                return Some(routing.to_string());
            }
        }
        None
    }

    fn resolve_alias_read_routing(&self, target: &str) -> Option<String> {
        self.resolve_alias_write_routing(target)
    }

    fn resolve_alias_search_routing(&self, target: &str) -> Option<String> {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let indices = manifest["indices"].as_object()?;
        for body in indices.values() {
            let Some(alias_state) = body["aliases"].get(target) else {
                continue;
            };
            if let Some(routing) = alias_state.get("search_routing").and_then(Value::as_str) {
                return Some(routing.to_string());
            }
            if let Some(routing) = alias_state.get("index_routing").and_then(Value::as_str) {
                return Some(routing.to_string());
            }
        }
        None
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

    fn index_primary_shard_count(&self, index: &str) -> usize {
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let settings = &manifest["indices"][index]["settings"];
        settings["index"]["number_of_shards"]
            .as_str()
            .or_else(|| settings["number_of_shards"].as_str())
            .and_then(|value| value.parse::<usize>().ok())
            .unwrap_or(1)
    }

    fn build_search_hit_fields(
        &self,
        index: &str,
        source: &Value,
        body: &Value,
    ) -> Option<Value> {
        let mut fields = serde_json::Map::new();
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let properties = manifest["indices"][index]["mappings"]["properties"].as_object()?;

        if let Some(stored_fields) = body.get("stored_fields").and_then(Value::as_array) {
            for field in stored_fields.iter().filter_map(Value::as_str) {
                let Some(mapping) = properties.get(field).and_then(Value::as_object) else {
                    continue;
                };
                if mapping.get("store").and_then(Value::as_bool) != Some(true) {
                    continue;
                }
                if let Some(value) = source.get(field) {
                    fields.insert(field.to_string(), Value::Array(vec![value.clone()]));
                }
            }
        }

        if let Some(docvalue_fields) = body.get("docvalue_fields").and_then(Value::as_array) {
            for spec in docvalue_fields {
                let (field, format) = if let Some(name) = spec.as_str() {
                    (name, None)
                } else if let Some(obj) = spec.as_object() {
                    (
                        obj.get("field").and_then(Value::as_str).unwrap_or_default(),
                        obj.get("format").and_then(Value::as_str),
                    )
                } else {
                    continue;
                };
                let Some(mapping) = properties.get(field).and_then(Value::as_object) else {
                    continue;
                };
                let Some(value) = source.get(field) else {
                    continue;
                };
                let docvalue_value = normalize_docvalue_field_value(mapping, value, format);
                fields.insert(field.to_string(), Value::Array(vec![docvalue_value]));
            }
        }

        if fields.is_empty() {
            None
        } else {
            Some(Value::Object(fields))
        }
    }

    fn validate_knn_target_capabilities(
        &self,
        query: &Value,
        resolved_indices: &[String],
    ) -> Option<RestResponse> {
        let field = extract_knn_field_name(query)?;
        let ignore_unmapped = extract_knn_ignore_unmapped(query);
        let manifest = self
            .metadata_manifest_state
            .lock()
            .expect("metadata manifest state lock poisoned");
        let mut any_mapped = false;
        for index in resolved_indices {
            let field_mapping = manifest["indices"][index]["mappings"]["properties"][field].clone();
            let Some(field_object) = field_mapping.as_object() else {
                if ignore_unmapped {
                    continue;
                }
                return Some(build_unsupported_search_response(
                    "unsupported knn unmapped field",
                ));
            };
            any_mapped = true;
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
        if !any_mapped && !ignore_unmapped {
            return Some(build_unsupported_search_response(
                "unsupported knn unmapped field",
            ));
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

fn build_x_content_parse_search_response(reason: &str) -> RestResponse {
    RestResponse::json(
        400,
        serde_json::json!({
            "error": {
                "type": "x_content_parse_exception",
                "reason": reason
            },
            "status": 400
        }),
    )
}

fn build_parsing_search_response(reason: &str) -> RestResponse {
    RestResponse::json(
        400,
        serde_json::json!({
            "error": {
                "type": "parsing_exception",
                "reason": reason
            },
            "status": 400
        }),
    )
}

fn validate_search_request_body(body: &Value) -> Option<RestResponse> {
    if let Some(runtime_mappings) = body.get("runtime_mappings") {
        if let Some(response) = validate_runtime_mappings_request_body(runtime_mappings) {
            return Some(response);
        }
    }
    if let Some(stored_fields) = body.get("stored_fields") {
        if let Some(response) = validate_stored_fields_request_body(stored_fields) {
            return Some(response);
        }
    }
    if let Some(docvalue_fields) = body.get("docvalue_fields") {
        if let Some(response) = validate_docvalue_fields_request_body(docvalue_fields) {
            return Some(response);
        }
    }
    if let Some(track_total_hits) = body.get("track_total_hits") {
        if track_total_hits != &Value::Bool(true)
            && track_total_hits.as_u64().is_none()
        {
            return Some(build_unsupported_search_response(
                "unsupported search option [track_total_hits]",
            ));
        }
    }
    if let Some(highlight) = body.get("highlight") {
        if let Some(response) = validate_highlight_request_body(highlight) {
            return Some(response);
        }
    }
    if let Some(suggest) = body.get("suggest") {
        if let Some(response) = validate_suggest_request_body(suggest) {
            return Some(response);
        }
    }
    if let Some(pit) = body.get("pit") {
        if let Some(response) = validate_pit_request_body(pit) {
            return Some(response);
        }
    }
    if let Some(search_after) = body.get("search_after") {
        if let Some(response) = validate_search_after_request_body(body.get("sort"), search_after) {
            return Some(response);
        }
    }
    for option in ["explain", "profile"] {
        if let Some(value) = body.get(option) {
            if value != &Value::Bool(true) {
                return Some(build_unsupported_search_response(&format!(
                    "unsupported search option [{option}]"
                )));
            }
        }
    }
    if let Some(rescore) = body.get("rescore") {
        if body.get("sort").is_some() {
            return Some(build_unsupported_search_response(
                "Cannot use [sort] option in conjunction with [rescore].",
            ));
        }
        if let Some(response) = validate_rescore_request_body(rescore) {
            return Some(response);
        }
    }
    if let Some(collapse) = body.get("collapse") {
        if let Some(response) = validate_collapse_request_body(collapse) {
            return Some(response);
        }
    }
    validate_search_query_body(&body["query"])
}

fn validate_pit_request_body(pit: &Value) -> Option<RestResponse> {
    let Some(object) = pit.as_object() else {
        return Some(build_unsupported_search_response(
            "unsupported search option [pit]",
        ));
    };
    let Some(id) = object.get("id").and_then(Value::as_str) else {
        return Some(build_unsupported_search_response(
            "unsupported search option [pit]",
        ));
    };
    if id.is_empty() {
        return Some(build_unsupported_search_response(
            "unsupported search option [pit]",
        ));
    }
    if object.keys().any(|key| key != "id" && key != "keep_alive") {
        return Some(build_unsupported_search_response(
            "unsupported search option [pit]",
        ));
    }
    None
}

fn validate_rescore_request_body(rescore: &Value) -> Option<RestResponse> {
    let Some(object) = rescore.as_object() else {
        return Some(build_unsupported_search_response(
            "unsupported search option [rescore]",
        ));
    };
    if object.keys().any(|key| key != "window_size" && key != "query") {
        return Some(build_unsupported_search_response(
            "unsupported search option [rescore]",
        ));
    }
    if object.get("window_size").and_then(Value::as_u64).is_none() {
        return Some(build_unsupported_search_response(
            "unsupported search option [rescore]",
        ));
    }
    if let Some(query) = object.get("query").and_then(Value::as_object) {
        if query
            .keys()
            .any(|key| key != "rescore_query" && key != "query_weight" && key != "rescore_query_weight")
        {
            return Some(build_unsupported_search_response(
                "unsupported search option [rescore]",
            ));
        }
        if let Some(rescore_query) = query.get("rescore_query") {
            if let Some(response) = validate_search_query_body(rescore_query) {
                return Some(response);
            }
        }
    }
    None
}

fn validate_collapse_request_body(collapse: &Value) -> Option<RestResponse> {
    let Some(object) = collapse.as_object() else {
        return Some(build_unsupported_search_response(
            "unsupported search option [collapse]",
        ));
    };
    if object.len() != 1 || object.get("field").and_then(Value::as_str).is_none() {
        return Some(build_unsupported_search_response(
            "unsupported search option [collapse]",
        ));
    }
    None
}

fn validate_runtime_mappings_request_body(runtime_mappings: &Value) -> Option<RestResponse> {
    let Some(mappings) = runtime_mappings.as_object() else {
        return Some(build_unsupported_search_response(
            "unsupported search option [runtime_mappings]",
        ));
    };
    for definition in mappings.values() {
        let Some(definition_object) = definition.as_object() else {
            return Some(build_unsupported_search_response(
                "unsupported search option [runtime_mappings]",
            ));
        };
        if definition_object.keys().any(|key| key != "type" && key != "script") {
            return Some(build_unsupported_search_response(
                "unsupported search option [runtime_mappings]",
            ));
        }
        if definition_object.get("type").and_then(Value::as_str).is_none() {
            return Some(build_unsupported_search_response(
                "unsupported search option [runtime_mappings]",
            ));
        }
        let Some(script) = definition_object.get("script").and_then(Value::as_object) else {
            return Some(build_unsupported_search_response(
                "unsupported search option [runtime_mappings]",
            ));
        };
        if script.keys().any(|key| key != "source") {
            return Some(build_unsupported_search_response(
                "unsupported search option [runtime_mappings]",
            ));
        }
        let Some(source) = script.get("source").and_then(Value::as_str) else {
            return Some(build_unsupported_search_response(
                "unsupported search option [runtime_mappings]",
            ));
        };
        if parse_runtime_mapping_script_source(source).is_none() {
            return Some(build_unsupported_search_response(
                "unsupported search option [runtime_mappings]",
            ));
        }
    }
    None
}

fn validate_stored_fields_request_body(stored_fields: &Value) -> Option<RestResponse> {
    let Some(fields) = stored_fields.as_array() else {
        return Some(build_unsupported_search_response(
            "unsupported search option [stored_fields]",
        ));
    };
    if fields.iter().any(|field| field.as_str().is_none()) {
        return Some(build_unsupported_search_response(
            "unsupported search option [stored_fields]",
        ));
    }
    None
}

fn validate_docvalue_fields_request_body(docvalue_fields: &Value) -> Option<RestResponse> {
    let Some(fields) = docvalue_fields.as_array() else {
        return Some(build_unsupported_search_response(
            "unsupported search option [docvalue_fields]",
        ));
    };
    for field in fields {
        if let Some(name) = field.as_str() {
            if name.is_empty() {
                return Some(build_unsupported_search_response(
                    "unsupported search option [docvalue_fields]",
                ));
            }
            continue;
        }
        let Some(spec) = field.as_object() else {
            return Some(build_unsupported_search_response(
                "unsupported search option [docvalue_fields]",
            ));
        };
        if spec.keys().any(|key| key != "field" && key != "format") {
            return Some(build_unsupported_search_response(
                "unsupported search option [docvalue_fields]",
            ));
        }
        if spec.get("field").and_then(Value::as_str).is_none() {
            return Some(build_unsupported_search_response(
                "unsupported search option [docvalue_fields]",
            ));
        }
    }
    None
}

fn validate_search_after_request_body(sort: Option<&Value>, search_after: &Value) -> Option<RestResponse> {
    let Some(sort_fields) = sort.and_then(Value::as_array) else {
        return Some(build_unsupported_search_response(
            "unsupported search option [search_after]",
        ));
    };
    let Some(after_values) = search_after.as_array() else {
        return Some(build_unsupported_search_response(
            "unsupported search option [search_after]",
        ));
    };
    if sort_fields.len() != 1 || after_values.len() != 1 {
        return Some(build_unsupported_search_response(
            "unsupported search option [search_after]",
        ));
    }
    None
}

fn validate_highlight_request_body(highlight: &Value) -> Option<RestResponse> {
    let Some(object) = highlight.as_object() else {
        return Some(build_unsupported_search_response(
            "unsupported highlight query shape",
        ));
    };
    for key in object.keys() {
        if key != "fields" && key != "pre_tags" && key != "post_tags" {
            return Some(build_unsupported_search_response(&format!(
                "unsupported highlight parameter [{key}]"
            )));
        }
    }
    let Some(fields) = object.get("fields").and_then(Value::as_object) else {
        return Some(build_unsupported_search_response(
            "unsupported highlight query shape",
        ));
    };
    if fields.is_empty() {
        return Some(build_unsupported_search_response(
            "unsupported highlight query shape",
        ));
    }
    for config in fields.values() {
        if !config
            .as_object()
            .is_some_and(|field_object| field_object.is_empty())
        {
            return Some(build_unsupported_search_response(
                "unsupported highlight field configuration",
            ));
        }
    }
    for tags_key in ["pre_tags", "post_tags"] {
        if let Some(tags) = object.get(tags_key) {
            if !tags
                .as_array()
                .is_some_and(|items| items.iter().all(|item| item.as_str().is_some()))
            {
                return Some(build_unsupported_search_response(&format!(
                    "unsupported highlight parameter [{tags_key}]"
                )));
            }
        }
    }
    None
}

fn validate_suggest_request_body(suggest: &Value) -> Option<RestResponse> {
    let Some(object) = suggest.as_object() else {
        return Some(build_unsupported_search_response(
            "unsupported suggest query shape",
        ));
    };
    if object.is_empty() {
        return Some(build_unsupported_search_response(
            "unsupported suggest query shape",
        ));
    }
    for (name, entry) in object {
        let Some(entry_object) = entry.as_object() else {
            return Some(build_unsupported_search_response(&format!(
                "unsupported suggest entry [{name}]"
            )));
        };
        if let Some(term) = entry_object.get("term").and_then(Value::as_object) {
            let Some(text) = entry_object.get("text").and_then(Value::as_str) else {
                return Some(build_unsupported_search_response(&format!(
                    "unsupported suggest entry [{name}]"
                )));
            };
            if text.is_empty() {
                return Some(build_unsupported_search_response(&format!(
                    "unsupported suggest entry [{name}]"
                )));
            }
            if entry_object.keys().any(|key| key != "text" && key != "term") {
                return Some(build_unsupported_search_response(
                    "unsupported suggest parameter",
                ));
            }
            let Some(field) = term.get("field").and_then(Value::as_str) else {
                return Some(build_unsupported_search_response(
                    "unsupported suggest family [term]",
                ));
            };
            if field.is_empty() {
                return Some(build_unsupported_search_response(
                    "unsupported suggest family [term]",
                ));
            }
            if term.keys().any(|key| key != "field") {
                return Some(build_unsupported_search_response(
                    "unsupported term suggest parameter",
                ));
            }
            continue;
        }
        if let Some(completion) = entry_object.get("completion").and_then(Value::as_object) {
            let Some(prefix) = entry_object.get("prefix").and_then(Value::as_str) else {
                return Some(build_unsupported_search_response(
                    "unsupported suggest family [completion]",
                ));
            };
            if prefix.is_empty() {
                return Some(build_unsupported_search_response(
                    "unsupported suggest family [completion]",
                ));
            }
            if entry_object
                .keys()
                .any(|key| key != "prefix" && key != "completion")
            {
                return Some(build_unsupported_search_response(
                    "unsupported suggest parameter",
                ));
            }
            let Some(field) = completion.get("field").and_then(Value::as_str) else {
                return Some(build_unsupported_search_response(
                    "unsupported suggest family [completion]",
                ));
            };
            if field.is_empty() {
                return Some(build_unsupported_search_response(
                    "unsupported suggest family [completion]",
                ));
            }
            if completion.keys().any(|key| key != "field" && key != "size") {
                return Some(build_unsupported_search_response(
                    "unsupported completion suggest parameter",
                ));
            }
            continue;
        }
        if let Some(phrase) = entry_object.get("phrase").and_then(Value::as_object) {
            let Some(text) = entry_object.get("text").and_then(Value::as_str) else {
                return Some(build_unsupported_search_response(
                    "unsupported suggest family [phrase]",
                ));
            };
            if text.is_empty() {
                return Some(build_unsupported_search_response(
                    "unsupported suggest family [phrase]",
                ));
            }
            if entry_object.keys().any(|key| key != "text" && key != "phrase") {
                return Some(build_unsupported_search_response(
                    "unsupported suggest parameter",
                ));
            }
            let Some(field) = phrase.get("field").and_then(Value::as_str) else {
                return Some(build_unsupported_search_response(
                    "unsupported suggest family [phrase]",
                ));
            };
            if field.is_empty() {
                return Some(build_unsupported_search_response(
                    "unsupported suggest family [phrase]",
                ));
            }
            if phrase.keys().any(|key| key != "field") {
                return Some(build_unsupported_search_response(
                    "unsupported phrase suggest parameter",
                ));
            }
            continue;
        }
        return Some(build_unsupported_search_response("unsupported suggest family"));
    }
    None
}

fn validate_search_query_body(query: &Value) -> Option<RestResponse> {
    let Some(query_object) = query.as_object() else {
        return None;
    };
    let Some((query_kind, _)) = query_object.iter().next() else {
        return None;
    };
    match query_kind.as_str() {
        "match_all"
        | "match_none"
        | "term"
        | "match"
        | "multi_match"
        | "match_phrase"
        | "match_phrase_prefix"
        | "dis_max"
        | "ids"
        | "query_string"
        | "simple_query_string"
        | "wildcard"
        | "prefix"
        | "regexp"
        | "fuzzy"
        | "exists"
        | "terms_set"
        | "nested"
        | "geo_distance"
        | "function_score"
        | "script_score"
        | "span_term"
        | "span_or"
        | "span_near"
        | "span_multi"
        | "field_masking_span"
        | "more_like_this"
        | "intervals"
        | "bool"
        | "range"
        | "knn" => {
            validate_supported_query_shape(query)
        }
        "hybrid" => Some(build_parsing_search_response(
            "Field is not supported by [hybrid] query",
        )),
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
            if key != "vector"
                && key != "k"
                && key != "filter"
                && key != "ignore_unmapped"
                && key != "expand_nested"
                && key != "max_distance"
                && key != "min_score"
                && key != "method_parameters"
            {
                return Some(build_x_content_parse_search_response(&format!(
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
        let has_k = spec_object.get("k").and_then(Value::as_u64).unwrap_or(0) > 0;
        let has_max_distance = spec_object
            .get("max_distance")
            .and_then(Value::as_f64)
            .is_some_and(|value| value > 0.0);
        let has_min_score = spec_object
            .get("min_score")
            .and_then(Value::as_f64)
            .is_some_and(|value| value > 0.0);
        if !has_k && !has_max_distance && !has_min_score {
            return Some(build_unsupported_search_response("unsupported knn parameter [k]"));
        }
        if let Some(filter) = spec_object.get("filter") {
            if let Some(response) = validate_search_query_body(filter) {
                return Some(response);
            }
        }
        if spec_object
            .get("ignore_unmapped")
            .is_some_and(|value| !value.is_boolean())
        {
            return Some(build_unsupported_search_response(
                "unsupported knn parameter [ignore_unmapped]",
            ));
        }
        if spec_object
            .get("expand_nested")
            .is_some_and(|value| !value.is_boolean())
        {
            return Some(build_unsupported_search_response(
                "unsupported knn parameter [expand_nested]",
            ));
        }
        if let Some(method_parameters) = spec_object.get("method_parameters") {
            let Some(object) = method_parameters.as_object() else {
                return Some(build_unsupported_search_response(
                    "unsupported knn parameter [method_parameters]",
                ));
            };
            if object.values().any(|value| value.as_u64().is_none()) {
                return Some(build_unsupported_search_response(
                    "unsupported knn parameter [method_parameters]",
                ));
            }
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
        if let Some(should) = bool_query.get("should").and_then(Value::as_array) {
            for clause in should {
                if let Some(response) = validate_search_query_body(clause) {
                    return Some(response);
                }
            }
        }
        if bool_query
            .get("minimum_should_match")
            .is_some_and(|value| value.as_u64().unwrap_or(0) == 0)
        {
            return Some(build_unsupported_search_response(
                "unsupported bool parameter [minimum_should_match]",
            ));
        }
    }
    if let Some(dis_max) = query.get("dis_max").and_then(Value::as_object) {
        let Some(queries) = dis_max.get("queries").and_then(Value::as_array) else {
            return Some(build_unsupported_search_response("unsupported dis_max query shape"));
        };
        for clause in queries {
            if let Some(response) = validate_search_query_body(clause) {
                return Some(response);
            }
        }
    }
    for query_name in ["query_string", "simple_query_string"] {
        if let Some(spec) = query.get(query_name).and_then(Value::as_object) {
            if spec
                .get("query")
                .and_then(Value::as_str)
                .map(str::is_empty)
                .unwrap_or(true)
            {
                return Some(build_unsupported_search_response(&format!(
                    "unsupported {query_name} query shape"
                )));
            }
            if let Some(fields) = spec.get("fields") {
                if !fields
                    .as_array()
                    .is_some_and(|items| items.iter().all(|value| value.as_str().is_some()))
                {
                    return Some(build_unsupported_search_response(&format!(
                        "unsupported {query_name} fields shape"
                    )));
                }
            }
            if let Some(default_operator) = spec.get("default_operator").and_then(Value::as_str) {
                if default_operator != "and" && default_operator != "or" {
                    return Some(build_unsupported_search_response(&format!(
                        "unsupported {query_name} default operator"
                    )));
                }
            }
            for key in spec.keys() {
                if key != "query" && key != "fields" && key != "default_operator" {
                    return Some(build_unsupported_search_response(&format!(
                        "unsupported {query_name} parameter [{key}]"
                    )));
                }
            }
        }
    }
    for query_name in ["wildcard", "prefix"] {
        if let Some(spec) = query.get(query_name).and_then(Value::as_object) {
            let Some((_, value)) = spec.iter().next() else {
                return Some(build_unsupported_search_response(&format!(
                    "unsupported {query_name} query shape"
                )));
            };
            let candidate_value = if let Some(object) = value.as_object() {
                if object.keys().any(|key| key != "value") {
                    return Some(build_unsupported_search_response(&format!(
                        "unsupported {query_name} parameter"
                    )));
                }
                object.get("value").and_then(Value::as_str)
            } else {
                value.as_str()
            };
            if candidate_value.map(str::is_empty).unwrap_or(true) {
                return Some(build_unsupported_search_response(&format!(
                    "unsupported {query_name} query shape"
                )));
            }
        }
    }
    if let Some(spec) = query.get("regexp").and_then(Value::as_object) {
        let Some((_, value)) = spec.iter().next() else {
            return Some(build_unsupported_search_response("unsupported regexp query shape"));
        };
        let candidate_value = if let Some(object) = value.as_object() {
            if object.keys().any(|key| key != "value") {
                return Some(build_unsupported_search_response(
                    "unsupported regexp parameter",
                ));
            }
            object.get("value").and_then(Value::as_str)
        } else {
            value.as_str()
        };
        if candidate_value.map(str::is_empty).unwrap_or(true) {
            return Some(build_unsupported_search_response("unsupported regexp query shape"));
        }
    }
    if let Some(spec) = query.get("fuzzy").and_then(Value::as_object) {
        let Some((_, value)) = spec.iter().next() else {
            return Some(build_unsupported_search_response("unsupported fuzzy query shape"));
        };
        if let Some(object) = value.as_object() {
            let Some(query_value) = object.get("value").and_then(Value::as_str) else {
                return Some(build_unsupported_search_response("unsupported fuzzy query shape"));
            };
            if query_value.is_empty() {
                return Some(build_unsupported_search_response("unsupported fuzzy query shape"));
            }
            if object.keys().any(|key| key != "value" && key != "fuzziness") {
                return Some(build_unsupported_search_response("unsupported fuzzy parameter"));
            }
            if let Some(fuzziness) = object.get("fuzziness") {
                if !(fuzziness.as_u64().is_some()
                    || fuzziness.as_str().is_some_and(|value| value == "AUTO"))
                {
                    return Some(build_unsupported_search_response(
                        "unsupported fuzzy fuzziness",
                    ));
                }
            }
        } else if value.as_str().map(str::is_empty).unwrap_or(true) {
            return Some(build_unsupported_search_response("unsupported fuzzy query shape"));
        }
    }
    if let Some(spec) = query.get("exists").and_then(Value::as_object) {
        if spec.len() != 1 || spec.get("field").and_then(Value::as_str).is_none() {
            return Some(build_unsupported_search_response("unsupported exists query shape"));
        }
    }
    if let Some(spec) = query.get("terms_set").and_then(Value::as_object) {
        let Some((_, value)) = spec.iter().next() else {
            return Some(build_unsupported_search_response("unsupported terms_set query shape"));
        };
        let Some(object) = value.as_object() else {
            return Some(build_unsupported_search_response("unsupported terms_set query shape"));
        };
        if !object
            .get("terms")
            .and_then(Value::as_array)
            .is_some_and(|items| items.iter().all(|item| item.is_string() || item.is_number()))
        {
            return Some(build_unsupported_search_response("unsupported terms_set terms"));
        }
        let minimum = object
            .get("minimum_should_match_script")
            .and_then(Value::as_object)
            .and_then(|script| script.get("source"))
            .and_then(Value::as_str);
        if minimum
            .and_then(|value| value.parse::<usize>().ok())
            .is_none()
        {
            return Some(build_unsupported_search_response(
                "unsupported terms_set minimum_should_match_script",
            ));
        }
        if object
            .keys()
            .any(|key| key != "terms" && key != "minimum_should_match_script")
        {
            return Some(build_unsupported_search_response("unsupported terms_set parameter"));
        }
    }
    if let Some(spec) = query.get("nested").and_then(Value::as_object) {
        let Some(path) = spec.get("path").and_then(Value::as_str) else {
            return Some(build_unsupported_search_response("unsupported nested query shape"));
        };
        if path.is_empty() {
            return Some(build_unsupported_search_response("unsupported nested query shape"));
        }
        let Some(inner_query) = spec.get("query") else {
            return Some(build_unsupported_search_response("unsupported nested query shape"));
        };
        if spec.keys().any(|key| key != "path" && key != "query") {
            return Some(build_unsupported_search_response("unsupported nested parameter"));
        }
        if let Some(response) = validate_search_query_body(inner_query) {
            return Some(response);
        }
    }
    if let Some(spec) = query.get("geo_distance").and_then(Value::as_object) {
        let Some(distance) = spec.get("distance").and_then(Value::as_str) else {
            return Some(build_unsupported_search_response(
                "unsupported geo_distance query shape",
            ));
        };
        if parse_distance_meters(distance).is_none() {
            return Some(build_unsupported_search_response(
                "unsupported geo_distance distance",
            ));
        }
        if spec.keys().filter(|key| key.as_str() != "distance").count() != 1 {
            return Some(build_unsupported_search_response(
                "unsupported geo_distance query shape",
            ));
        }
        let Some((field, point)) = spec.iter().find(|(key, _)| key.as_str() != "distance") else {
            return Some(build_unsupported_search_response(
                "unsupported geo_distance query shape",
            ));
        };
        if field.is_empty() || parse_geo_point_value(point).is_none() {
            return Some(build_unsupported_search_response(
                "unsupported geo_distance query shape",
            ));
        }
    }
    if let Some(spec) = query.get("function_score").and_then(Value::as_object) {
        let Some(inner_query) = spec.get("query") else {
            return Some(build_unsupported_search_response(
                "unsupported function_score query shape",
            ));
        };
        if spec.keys().any(|key| key != "query" && key != "weight" && key != "boost_mode") {
            return Some(build_unsupported_search_response(
                "unsupported function_score parameter",
            ));
        }
        if let Some(weight) = spec.get("weight").and_then(Value::as_f64) {
            if weight <= 0.0 {
                return Some(build_unsupported_search_response(
                    "unsupported function_score weight",
                ));
            }
        }
        if let Some(boost_mode) = spec.get("boost_mode").and_then(Value::as_str) {
            if boost_mode != "multiply" && boost_mode != "replace" {
                return Some(build_unsupported_search_response(
                    "unsupported function_score boost_mode",
                ));
            }
        }
        if let Some(response) = validate_search_query_body(inner_query) {
            return Some(response);
        }
    }
    if let Some(spec) = query.get("script_score").and_then(Value::as_object) {
        let Some(inner_query) = spec.get("query") else {
            return Some(build_unsupported_search_response(
                "unsupported script_score query shape",
            ));
        };
        let Some(script_source) = spec
            .get("script")
            .and_then(Value::as_object)
            .and_then(|script| script.get("source"))
            .and_then(Value::as_str)
        else {
            return Some(build_unsupported_search_response(
                "unsupported script_score query shape",
            ));
        };
        if script_source.parse::<f64>().ok().filter(|score| *score > 0.0).is_none() {
            return Some(build_unsupported_search_response(
                "unsupported script_score source",
            ));
        }
        if spec.keys().any(|key| key != "query" && key != "script") {
            return Some(build_unsupported_search_response(
                "unsupported script_score parameter",
            ));
        }
        if let Some(response) = validate_search_query_body(inner_query) {
            return Some(response);
        }
    }
    if let Some(spec) = query.get("span_term").and_then(Value::as_object) {
        let Some((_, value)) = spec.iter().next() else {
            return Some(build_unsupported_search_response("unsupported span_term query shape"));
        };
        if value.as_str().map(str::is_empty).unwrap_or(true) {
            return Some(build_unsupported_search_response("unsupported span_term query shape"));
        }
    }
    if let Some(spec) = query.get("span_or").and_then(Value::as_object) {
        let Some(clauses) = spec.get("clauses").and_then(Value::as_array) else {
            return Some(build_unsupported_search_response("unsupported span_or query shape"));
        };
        if clauses.is_empty() {
            return Some(build_unsupported_search_response("unsupported span_or query shape"));
        }
        for clause in clauses {
            if let Some(response) = validate_search_query_body(clause) {
                return Some(response);
            }
        }
    }
    if let Some(spec) = query.get("span_near").and_then(Value::as_object) {
        let Some(clauses) = spec.get("clauses").and_then(Value::as_array) else {
            return Some(build_unsupported_search_response("unsupported span_near query shape"));
        };
        if clauses.len() < 2
            || spec.get("slop").and_then(Value::as_u64).is_none()
            || spec.get("in_order").and_then(Value::as_bool).is_none()
        {
            return Some(build_unsupported_search_response("unsupported span_near query shape"));
        }
        if spec.keys().any(|key| key != "clauses" && key != "slop" && key != "in_order") {
            return Some(build_unsupported_search_response("unsupported span_near parameter"));
        }
        for clause in clauses {
            if let Some(response) = validate_search_query_body(clause) {
                return Some(response);
            }
        }
    }
    if let Some(spec) = query.get("span_multi").and_then(Value::as_object) {
        let Some(inner_match) = spec.get("match") else {
            return Some(build_unsupported_search_response("unsupported span_multi query shape"));
        };
        if let Some(response) = validate_search_query_body(inner_match) {
            return Some(response);
        }
    }
    if let Some(spec) = query.get("field_masking_span").and_then(Value::as_object) {
        let Some(field) = spec.get("field").and_then(Value::as_str) else {
            return Some(build_unsupported_search_response(
                "unsupported field_masking_span query shape",
            ));
        };
        if field.is_empty() {
            return Some(build_unsupported_search_response(
                "unsupported field_masking_span query shape",
            ));
        }
        let Some(inner_query) = spec.get("query") else {
            return Some(build_unsupported_search_response(
                "unsupported field_masking_span query shape",
            ));
        };
        if spec.keys().any(|key| key != "field" && key != "query") {
            return Some(build_unsupported_search_response(
                "unsupported field_masking_span parameter",
            ));
        }
        if let Some(response) = validate_search_query_body(inner_query) {
            return Some(response);
        }
    }
    if let Some(spec) = query.get("more_like_this").and_then(Value::as_object) {
        let fields_ok = spec
            .get("fields")
            .and_then(Value::as_array)
            .is_some_and(|items| items.iter().all(|item| item.as_str().is_some()));
        let like_ok = spec.get("like").and_then(Value::as_str).is_some_and(|value| !value.is_empty());
        if !fields_ok || !like_ok {
            return Some(build_unsupported_search_response(
                "unsupported more_like_this query shape",
            ));
        }
        if spec.keys().any(|key| {
            key != "fields"
                && key != "like"
                && key != "min_term_freq"
                && key != "min_doc_freq"
        }) {
            return Some(build_unsupported_search_response(
                "unsupported more_like_this parameter",
            ));
        }
        for key in ["min_term_freq", "min_doc_freq"] {
            if spec.get(key).is_some_and(|value| value.as_u64().is_none()) {
                return Some(build_unsupported_search_response(
                    "unsupported more_like_this parameter",
                ));
            }
        }
    }
    if let Some(spec) = query.get("intervals").and_then(Value::as_object) {
        let Some((_, value)) = spec.iter().next() else {
            return Some(build_unsupported_search_response("unsupported intervals query shape"));
        };
        let Some(interval_object) = value.as_object() else {
            return Some(build_unsupported_search_response("unsupported intervals query shape"));
        };
        if let Some(match_spec) = interval_object.get("match").and_then(Value::as_object) {
            let Some(query_text) = match_spec.get("query").and_then(Value::as_str) else {
                return Some(build_unsupported_search_response("unsupported intervals match"));
            };
            if query_text.is_empty() {
                return Some(build_unsupported_search_response("unsupported intervals match"));
            }
            if match_spec
                .keys()
                .any(|key| key != "query" && key != "ordered" && key != "max_gaps")
            {
                return Some(build_unsupported_search_response(
                    "unsupported intervals match parameter",
                ));
            }
        } else if let Some(all_of) = interval_object.get("all_of").and_then(Value::as_object) {
            let Some(intervals) = all_of.get("intervals").and_then(Value::as_array) else {
                return Some(build_unsupported_search_response(
                    "unsupported intervals all_of shape",
                ));
            };
            if intervals.is_empty() {
                return Some(build_unsupported_search_response(
                    "unsupported intervals all_of shape",
                ));
            }
            if all_of
                .keys()
                .any(|key| key != "intervals" && key != "ordered" && key != "max_gaps")
            {
                return Some(build_unsupported_search_response(
                    "unsupported intervals all_of parameter",
                ));
            }
            for interval in intervals {
                let Some(match_spec) = interval.get("match").and_then(Value::as_object) else {
                    return Some(build_unsupported_search_response(
                        "unsupported intervals all_of interval",
                    ));
                };
                if match_spec
                    .get("query")
                    .and_then(Value::as_str)
                    .map(str::is_empty)
                    .unwrap_or(true)
                {
                    return Some(build_unsupported_search_response(
                        "unsupported intervals all_of interval",
                    ));
                }
            }
        } else {
            return Some(build_unsupported_search_response("unsupported intervals query shape"));
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

fn apply_search_after(hits: Vec<Value>, sort: &Value, search_after: &[Value]) -> Vec<Value> {
    let Some(sort_fields) = sort.as_array() else {
        return hits;
    };
    let Some(first_sort) = sort_fields.first() else {
        return hits;
    };
    let Some(after_value) = search_after.first() else {
        return hits;
    };
    let (field_name, descending) = if let Some(field_name) = first_sort.as_str() {
        (field_name.to_string(), field_name == "_score")
    } else if let Some(field_object) = first_sort.as_object() {
        let Some((field_name, field_options)) = field_object.iter().next() else {
            return hits;
        };
        (
            field_name.clone(),
            field_options
                .get("order")
                .and_then(Value::as_str)
                .unwrap_or("asc")
                == "desc",
        )
    } else {
        return hits;
    };
    hits.into_iter()
        .filter(|hit| {
            let sort_value = extract_sort_value(hit, &field_name);
            let ordering = compare_json_scalars(&sort_value, after_value);
            if descending {
                ordering == std::cmp::Ordering::Less
            } else {
                ordering == std::cmp::Ordering::Greater
            }
        })
        .collect()
}

fn parse_runtime_mapping_script_source(source: &str) -> Option<String> {
    let field_expr = source.strip_prefix("emit(doc['")?;
    let (field_name, suffix) = field_expr.split_once("'].value)")?;
    if !suffix.is_empty() || field_name.is_empty() {
        return None;
    }
    Some(field_name.to_string())
}

fn apply_runtime_mappings_to_source(source: &Value, runtime_mappings: Option<&Value>) -> Value {
    let Some(source_object) = source.as_object() else {
        return source.clone();
    };
    let mut effective = source_object.clone();
    let Some(mappings) = runtime_mappings.and_then(Value::as_object) else {
        return Value::Object(effective);
    };
    for (runtime_field, definition) in mappings {
        let Some(definition_object) = definition.as_object() else {
            continue;
        };
        let Some(script_source) = definition_object
            .get("script")
            .and_then(Value::as_object)
            .and_then(|script| script.get("source"))
            .and_then(Value::as_str)
        else {
            continue;
        };
        let Some(source_field) = parse_runtime_mapping_script_source(script_source) else {
            continue;
        };
        if let Some(value) = source_object.get(&source_field) {
            effective.insert(runtime_field.clone(), value.clone());
        }
    }
    Value::Object(effective)
}

fn normalize_docvalue_field_value(
    mapping: &serde_json::Map<String, Value>,
    value: &Value,
    _format: Option<&str>,
) -> Value {
    match mapping.get("type").and_then(Value::as_str) {
        Some("date") => Value::String(
            value
                .as_str()
                .map(|raw| {
                    if raw.ends_with('Z') && !raw.contains('.') {
                        raw.trim_end_matches('Z').to_string() + ".000Z"
                    } else {
                        raw.to_string()
                    }
                })
                .unwrap_or_default(),
        ),
        Some("long") | Some("integer") | Some("short") | Some("byte") | Some("double") | Some("float") => {
            value.clone()
        }
        Some("keyword") | Some("boolean") => value.clone(),
        _ => value.clone(),
    }
}

fn apply_search_rescore(hits: &mut [Value], rescore: &Value) {
    let Some(rescore_object) = rescore.as_object() else {
        return;
    };
    let window_size = rescore_object
        .get("window_size")
        .and_then(Value::as_u64)
        .unwrap_or(0) as usize;
    let Some(query_object) = rescore_object.get("query").and_then(Value::as_object) else {
        return;
    };
    let Some(rescore_query) = query_object.get("rescore_query") else {
        return;
    };
    let query_weight = query_object
        .get("query_weight")
        .and_then(Value::as_f64)
        .unwrap_or(1.0);
    let rescore_weight = query_object
        .get("rescore_query_weight")
        .and_then(Value::as_f64)
        .unwrap_or(1.0);
    let window = window_size.min(hits.len());
    for hit in &mut hits[..window] {
        let Some(hit_object) = hit.as_object_mut() else {
            continue;
        };
        let base_score = hit_object.get("_score").and_then(Value::as_f64).unwrap_or(0.0);
        let Some(source) = hit_object.get("_source") else {
            continue;
        };
        let doc_id = hit_object.get("_id").and_then(Value::as_str).unwrap_or_default();
        let rescore_score = evaluate_search_query_source(source, doc_id, rescore_query)
            .map(|(matched, score)| if matched { score } else { 0.0 })
            .unwrap_or(0.0);
        hit_object.insert(
            "_score".to_string(),
            Value::from(base_score * query_weight + rescore_score * rescore_weight),
        );
    }
    hits[..window].sort_by(|left, right| {
        let left_score = left["_score"].as_f64().unwrap_or(0.0);
        let right_score = right["_score"].as_f64().unwrap_or(0.0);
        right_score
            .partial_cmp(&left_score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
}

fn apply_search_collapse(hits: Vec<Value>, collapse: &Value) -> Vec<Value> {
    let Some(field) = collapse
        .as_object()
        .and_then(|object| object.get("field"))
        .and_then(Value::as_str)
    else {
        return hits;
    };
    let mut seen = BTreeSet::new();
    let mut collapsed = Vec::new();
    for hit in hits {
        let key = extract_sort_value(&hit, field).to_string();
        if seen.insert(key) {
            collapsed.push(hit);
        }
    }
    collapsed
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

fn parse_search_timeout_millis(timeout: &str) -> Option<u64> {
    if let Some(value) = timeout.strip_suffix("ms") {
        return value.parse::<u64>().ok();
    }
    if let Some(value) = timeout.strip_suffix('s') {
        return value.parse::<u64>().ok().map(|seconds| seconds * 1_000);
    }
    None
}

fn extract_geo_distance_field(query: &Value) -> Option<String> {
    query.get("geo_distance")
        .and_then(Value::as_object)
        .and_then(|spec| {
            spec.iter()
                .find(|(key, _)| key.as_str() != "distance")
                .map(|(key, _)| key.clone())
        })
}

fn compute_can_match_skipped_shards(
    query: &Value,
    pre_filter_shard_size: Option<&String>,
    total_shards: usize,
) -> usize {
    if pre_filter_shard_size.is_none() || total_shards <= 1 {
        return 0;
    }
    if query.get("match_none").is_some() || query.get("range").is_some() {
        return total_shards.saturating_sub(1);
    }
    0
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

fn extract_knn_ignore_unmapped(query: &Value) -> bool {
    if let Some(knn) = query.get("knn").and_then(Value::as_object) {
        if let Some((_, spec)) = knn.iter().next() {
            return spec
                .get("ignore_unmapped")
                .and_then(Value::as_bool)
                .unwrap_or(false);
        }
    }
    if let Some(bool_query) = query.get("bool").and_then(Value::as_object) {
        if let Some(must) = bool_query.get("must").and_then(Value::as_array) {
            for clause in must {
                if extract_knn_ignore_unmapped(clause) {
                    return true;
                }
            }
        }
    }
    false
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

fn build_concurrent_snapshot_delete_response(repository: &str, snapshot: &str) -> RestResponse {
    RestResponse::json(
        409,
        serde_json::json!({
            "error": {
                "type": "concurrent_snapshot_execution_exception",
                "reason": format!("[{repository}:{snapshot}] cannot delete snapshot during a restore in progress"),
            },
            "status": 409
        }),
    )
}

fn extract_snapshot_restore_unknown_parameter(body: &Value) -> Option<&'static str> {
    let object = body.as_object()?;
    for candidate in ["stale", "corrupt", "incompatible"] {
        if object.get(candidate).and_then(Value::as_bool) == Some(true) {
            return Some(candidate);
        }
    }
    None
}

fn evaluate_search_query(record: &StoredDocument, doc_id: &str, query: &Value) -> Option<(bool, f64)> {
    evaluate_search_query_source(&record.source, doc_id, query)
}

fn evaluate_search_query_source(source: &Value, doc_id: &str, query: &Value) -> Option<(bool, f64)> {
    evaluate_search_query_source_with_mappings(source, doc_id, query, &Value::Null)
}

fn evaluate_search_query_source_with_mappings(
    source: &Value,
    doc_id: &str,
    query: &Value,
    mappings: &Value,
) -> Option<(bool, f64)> {
    if query.is_null() || query.as_object().is_some_and(|object| object.is_empty()) {
        return Some((true, 1.0));
    }
    if query.get("match_all").is_some() {
        return Some((true, 1.0));
    }
    if query.get("match_none").is_some() {
        return Some((false, 0.0));
    }
    if let Some(term) = query.get("term").and_then(Value::as_object) {
        let (field, expected) = term.iter().next()?;
        let matched = value_matches_term(
            lookup_query_field_value(source, field),
            expected,
            lookup_query_field_mapping_type(mappings, field),
        );
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(match_query) = query.get("match").and_then(Value::as_object) {
        let (field, expected) = match_query.iter().next()?;
        let score = score_match_query(
            lookup_query_field_value(source, field),
            expected.as_str().unwrap_or_default(),
        );
        return Some((score > 0.0, score));
    }
    if let Some(multi_match) = query.get("multi_match").and_then(Value::as_object) {
        let expected = multi_match.get("query").and_then(Value::as_str).unwrap_or_default();
        let fields = multi_match.get("fields").and_then(Value::as_array)?;
        let mut best_score: f64 = 0.0;
        for field in fields.iter().filter_map(Value::as_str) {
            best_score = best_score.max(score_match_query(
                lookup_query_field_value(source, field),
                expected,
            ));
        }
        return Some((best_score > 0.0, best_score));
    }
    if let Some(match_phrase) = query.get("match_phrase").and_then(Value::as_object) {
        let (field, expected) = match_phrase.iter().next()?;
        let matched = value_matches_phrase(
            lookup_query_field_value(source, field),
            expected.as_str().unwrap_or_default(),
            false,
        );
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(match_phrase_prefix) = query.get("match_phrase_prefix").and_then(Value::as_object) {
        let (field, expected) = match_phrase_prefix.iter().next()?;
        let matched = value_matches_phrase(
            lookup_query_field_value(source, field),
            expected.as_str().unwrap_or_default(),
            true,
        );
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(dis_max) = query.get("dis_max").and_then(Value::as_object) {
        let queries = dis_max.get("queries").and_then(Value::as_array)?;
        let mut best_score: f64 = 0.0;
        let mut matched = false;
        for clause in queries {
            let (clause_matched, clause_score) =
                evaluate_search_query_source_with_mappings(source, doc_id, clause, mappings)?;
            if clause_matched {
                matched = true;
                best_score = best_score.max(clause_score);
            }
        }
        return Some((matched, if matched { best_score.max(1.0) } else { 0.0 }));
    }
    if let Some(ids_query) = query.get("ids").and_then(Value::as_object) {
        let matched = ids_query
            .get("values")
            .and_then(Value::as_array)
            .is_some_and(|values| values.iter().filter_map(Value::as_str).any(|candidate| candidate == doc_id));
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(query_string) = query.get("query_string").and_then(Value::as_object) {
        return Some(evaluate_text_query_spec(source, query_string, false));
    }
    if let Some(simple_query_string) = query.get("simple_query_string").and_then(Value::as_object) {
        return Some(evaluate_text_query_spec(source, simple_query_string, true));
    }
    if let Some(wildcard_query) = query.get("wildcard").and_then(Value::as_object) {
        let (field, expected) = wildcard_query.iter().next()?;
        let expected_value = extract_string_query_value(expected)?;
        let matched = value_matches_wildcard(lookup_query_field_value(source, field), expected_value);
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(prefix_query) = query.get("prefix").and_then(Value::as_object) {
        let (field, expected) = prefix_query.iter().next()?;
        let expected_value = extract_string_query_value(expected)?;
        let matched = value_matches_prefix(lookup_query_field_value(source, field), expected_value);
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(regexp_query) = query.get("regexp").and_then(Value::as_object) {
        let (field, expected) = regexp_query.iter().next()?;
        let expected_value = extract_string_query_value(expected)?;
        let matched = value_matches_regexp(lookup_query_field_value(source, field), expected_value);
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(fuzzy_query) = query.get("fuzzy").and_then(Value::as_object) {
        let (field, expected) = fuzzy_query.iter().next()?;
        let (expected_value, fuzziness) = extract_fuzzy_query_value(expected)?;
        let matched = value_matches_fuzzy(
            lookup_query_field_value(source, field),
            expected_value,
            fuzziness,
        );
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(exists_query) = query.get("exists").and_then(Value::as_object) {
        let field = exists_query.get("field").and_then(Value::as_str)?;
        let matched = lookup_query_field_value(source, field).is_some_and(|value| !value.is_null());
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(terms_set_query) = query.get("terms_set").and_then(Value::as_object) {
        let (field, expected) = terms_set_query.iter().next()?;
        let (matched, score) = value_matches_terms_set(lookup_query_field_value(source, field), expected)?;
        return Some((matched, score));
    }
    if let Some(function_score) = query.get("function_score").and_then(Value::as_object) {
        let inner_query = function_score.get("query")?;
        let (matched, inner_score) =
            evaluate_search_query_source_with_mappings(source, doc_id, inner_query, mappings)?;
        if !matched {
            return Some((false, 0.0));
        }
        let weight = function_score.get("weight").and_then(Value::as_f64).unwrap_or(1.0);
        let boost_mode = function_score
            .get("boost_mode")
            .and_then(Value::as_str)
            .unwrap_or("multiply");
        let score = if boost_mode == "replace" {
            weight
        } else {
            inner_score * weight
        };
        return Some((true, score.max(1.0)));
    }
    if let Some(script_score) = query.get("script_score").and_then(Value::as_object) {
        let inner_query = script_score.get("query")?;
        let (matched, _) =
            evaluate_search_query_source_with_mappings(source, doc_id, inner_query, mappings)?;
        if !matched {
            return Some((false, 0.0));
        }
        let score = script_score
            .get("script")
            .and_then(Value::as_object)
            .and_then(|script| script.get("source"))
            .and_then(Value::as_str)
            .and_then(|value| value.parse::<f64>().ok())
            .unwrap_or(1.0);
        return Some((true, score.max(1.0)));
    }
    if let Some(span_term) = query.get("span_term").and_then(Value::as_object) {
        return evaluate_span_query(source, span_term).map(|matched| (matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(span_or) = query.get("span_or").and_then(Value::as_object) {
        let matched = evaluate_span_or_query(source, span_or)?;
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(span_near) = query.get("span_near").and_then(Value::as_object) {
        let matched = evaluate_span_near_query(source, span_near)?;
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(span_multi) = query.get("span_multi").and_then(Value::as_object) {
        let matched = evaluate_span_multi_query(source, span_multi)?;
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(field_masking_span) = query.get("field_masking_span").and_then(Value::as_object) {
        let matched = evaluate_field_masking_span_query(source, field_masking_span)?;
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(more_like_this) = query.get("more_like_this").and_then(Value::as_object) {
        let like = more_like_this.get("like").and_then(Value::as_str).unwrap_or_default();
        let fields = more_like_this
            .get("fields")
            .and_then(Value::as_array)?
            .iter()
            .filter_map(Value::as_str)
            .collect::<Vec<_>>();
        let mut best_score: f64 = 0.0;
        for field in fields {
            best_score = best_score.max(score_match_query(lookup_query_field_value(source, field), like));
        }
        return Some((best_score > 0.0, best_score));
    }
    if let Some(intervals_query) = query.get("intervals").and_then(Value::as_object) {
        let (field, spec) = intervals_query.iter().next()?;
        let matched = evaluate_intervals_query(
            lookup_query_field_value(source, field),
            spec,
        )?;
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(nested_query) = query.get("nested").and_then(Value::as_object) {
        let path = nested_query.get("path").and_then(Value::as_str)?;
        let inner_query = nested_query.get("query")?;
        let candidates = source.get(path)?.as_array()?;
        let mut best_score: f64 = 0.0;
        let mut matched = false;
        for candidate in candidates {
            let (inner_matched, inner_score) =
                evaluate_search_query_source_with_mappings(candidate, doc_id, inner_query, mappings)?;
            if inner_matched {
                matched = true;
                best_score = best_score.max(inner_score);
            }
        }
        return Some((matched, if matched { best_score.max(1.0) } else { 0.0 }));
    }
    if let Some(geo_distance_query) = query.get("geo_distance").and_then(Value::as_object) {
        let distance = geo_distance_query.get("distance").and_then(Value::as_str)?;
        let max_distance_meters = parse_distance_meters(distance)?;
        let (field, point) = geo_distance_query.iter().find(|(key, _)| key.as_str() != "distance")?;
        let candidate_point = lookup_query_field_value(source, field).and_then(parse_geo_point_value)?;
        let query_point = parse_geo_point_value(point)?;
        let distance_meters = haversine_distance_meters(candidate_point, query_point);
        let matched = distance_meters <= max_distance_meters;
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    if let Some(bool_query) = query.get("bool").and_then(Value::as_object) {
        let mut total_score = 0.0;
        let mut has_scoring_clause = false;
        if let Some(musts) = bool_query.get("must").and_then(Value::as_array) {
            for clause in musts {
                let (matched, score) =
                    evaluate_search_query_source_with_mappings(source, doc_id, clause, mappings)?;
                if !matched {
                    return Some((false, 0.0));
                }
                total_score += score;
                has_scoring_clause = true;
            }
        }
        if let Some(filters) = bool_query.get("filter").and_then(Value::as_array) {
            let matched = filters.iter().all(|clause| {
                evaluate_search_query_source_with_mappings(source, doc_id, clause, mappings)
                    .map(|(matched, _)| matched)
                    .unwrap_or(false)
            });
            if !matched {
                return Some((false, 0.0));
            }
        }
        if let Some(shoulds) = bool_query.get("should").and_then(Value::as_array) {
            let mut matched_should = 0usize;
            for clause in shoulds {
                let (matched, score) =
                    evaluate_search_query_source_with_mappings(source, doc_id, clause, mappings)?;
                if matched {
                    matched_should += 1;
                    total_score += score;
                    has_scoring_clause = true;
                }
            }
            let required = bool_query
                .get("minimum_should_match")
                .and_then(Value::as_u64)
                .map(|value| value as usize)
                .unwrap_or_else(|| if has_scoring_clause { 0 } else { 1 });
            if matched_should < required {
                return Some((false, 0.0));
            }
        }
        if has_scoring_clause {
            return Some((true, total_score.max(1.0)));
        }
        if bool_query.get("filter").is_some() {
            return Some((true, 1.0));
        }
    }
    if let Some(knn_query) = query.get("knn").and_then(Value::as_object) {
        let (field, spec) = knn_query.iter().next()?;
        let spec_object = spec.as_object()?;
        if let Some(filter) = spec_object.get("filter") {
            let (matched, _) =
                evaluate_search_query_source_with_mappings(source, doc_id, filter, mappings)?;
            if !matched {
                return Some((false, 0.0));
            }
        }
        let vector = spec_object.get("vector")?.as_array()?;
        let score = score_knn_query(lookup_query_field_value(source, field), vector);
        if score <= f64::MIN / 2.0 {
            return Some((false, 0.0));
        }
        if let Some(min_score) = spec_object.get("min_score").and_then(Value::as_f64) {
            if score < min_score {
                return Some((false, 0.0));
            }
        }
        if let Some(max_distance) = spec_object.get("max_distance").and_then(Value::as_f64) {
            if score < max_distance {
                return Some((false, 0.0));
            }
        }
        return Some((true, score));
    }
    if let Some(range_query) = query.get("range").and_then(Value::as_object) {
        let (field, bounds) = range_query.iter().next()?;
        let matched = value_matches_range(lookup_query_field_value(source, field), bounds);
        return Some((matched, if matched { 1.0 } else { 0.0 }));
    }
    Some((false, 0.0))
}

fn value_matches_term(candidate: Option<&Value>, expected: &Value, field_type: Option<&str>) -> bool {
    match (candidate, expected) {
        (Some(Value::String(left)), Value::String(right)) => {
            let lowered_left = left.to_ascii_lowercase();
            let lowered_right = right.to_ascii_lowercase();
            if matches!(field_type, Some("keyword") | Some("constant_keyword") | Some("wildcard")) {
                lowered_left == lowered_right
            } else {
                tokenize_search_text(left)
                    .into_iter()
                    .any(|token| token == lowered_right)
            }
        }
        (Some(Value::Number(left)), Value::Number(right)) => left == right,
        (Some(left), right) => left == right,
        _ => false,
    }
}

fn lookup_query_field_mapping_type<'a>(mappings: &'a Value, field: &str) -> Option<&'a str> {
    let mut current = mappings.get("properties")?;
    let mut segments = field.split('.').peekable();
    while let Some(segment) = segments.next() {
        let field_mapping = current.get(segment)?;
        if segments.peek().is_none() {
            return field_mapping.get("type").and_then(Value::as_str);
        }
        current = field_mapping.get("properties")?;
    }
    None
}

fn tokenize_search_text(input: &str) -> Vec<String> {
    input
        .split(|character: char| !character.is_ascii_alphanumeric())
        .map(|token| token.to_ascii_lowercase())
        .filter(|token| !token.is_empty())
        .collect()
}

fn build_highlight_response_body(source: &Value, query: &Value, highlight: &Value) -> Option<Value> {
    let highlight_object = highlight.as_object()?;
    let fields = highlight_object.get("fields")?.as_object()?;
    let pre_tag = highlight_object
        .get("pre_tags")
        .and_then(Value::as_array)
        .and_then(|tags| tags.first())
        .and_then(Value::as_str)
        .unwrap_or("<em>");
    let post_tag = highlight_object
        .get("post_tags")
        .and_then(Value::as_array)
        .and_then(|tags| tags.first())
        .and_then(Value::as_str)
        .unwrap_or("</em>");
    let mut highlighted_fields = serde_json::Map::new();
    for field in fields.keys() {
        let Some(original_text) = lookup_query_field_value(source, field).and_then(Value::as_str) else {
            continue;
        };
        let terms = collect_highlight_terms(query, field);
        if terms.is_empty() {
            continue;
        }
        let rendered = render_highlight_text(original_text, &terms, pre_tag, post_tag);
        if rendered != original_text {
            highlighted_fields.insert(field.clone(), serde_json::json!([rendered]));
        }
    }
    if highlighted_fields.is_empty() {
        None
    } else {
        Some(Value::Object(highlighted_fields))
    }
}

fn collect_highlight_terms(query: &Value, field: &str) -> Vec<String> {
    let mut terms = Vec::new();
    if let Some(term_query) = query.get("term").and_then(Value::as_object) {
        if let Some((query_field, expected)) = term_query.iter().next() {
            if query_field == field {
                if let Some(value) = expected.as_str() {
                    terms.extend(tokenize_search_text(value));
                }
            }
        }
    }
    for query_name in ["match", "match_phrase", "match_phrase_prefix"] {
        if let Some(match_query) = query.get(query_name).and_then(Value::as_object) {
            if let Some((query_field, value)) = match_query.iter().next() {
                if query_field == field {
                    if let Some(text) = extract_string_query_value(value) {
                        terms.extend(tokenize_search_text(text));
                    }
                }
            }
        }
    }
    if let Some(multi_match) = query.get("multi_match").and_then(Value::as_object) {
        let query_text = multi_match.get("query").and_then(Value::as_str).unwrap_or_default();
        let fields = multi_match
            .get("fields")
            .and_then(Value::as_array)
            .map(|items| items.iter().filter_map(Value::as_str).collect::<Vec<_>>())
            .unwrap_or_default();
        if fields.is_empty() || fields.iter().any(|candidate| *candidate == field) {
            terms.extend(tokenize_search_text(query_text));
        }
    }
    for query_name in ["query_string", "simple_query_string"] {
        if let Some(spec) = query.get(query_name).and_then(Value::as_object) {
            let query_text = spec.get("query").and_then(Value::as_str).unwrap_or_default();
            let fields = spec
                .get("fields")
                .and_then(Value::as_array)
                .map(|items| items.iter().filter_map(Value::as_str).collect::<Vec<_>>())
                .unwrap_or_default();
            if fields.is_empty() || fields.iter().any(|candidate| *candidate == field) {
                terms.extend(tokenize_search_text(query_text));
            }
        }
    }
    if let Some(bool_query) = query.get("bool").and_then(Value::as_object) {
        for branch in ["must", "filter"] {
            if let Some(clauses) = bool_query.get(branch).and_then(Value::as_array) {
                for clause in clauses {
                    terms.extend(collect_highlight_terms(clause, field));
                }
            }
        }
    }
    if let Some(dis_max) = query.get("dis_max").and_then(Value::as_object) {
        if let Some(clauses) = dis_max.get("queries").and_then(Value::as_array) {
            for clause in clauses {
                terms.extend(collect_highlight_terms(clause, field));
            }
        }
    }
    let mut unique = BTreeSet::new();
    terms.retain(|term| unique.insert(term.clone()));
    terms
}

fn render_highlight_text(input: &str, terms: &[String], pre_tag: &str, post_tag: &str) -> String {
    let lowered_terms = terms
        .iter()
        .map(|term| term.to_ascii_lowercase())
        .collect::<BTreeSet<_>>();
    let mut rendered = String::new();
    let mut current = String::new();
    for ch in input.chars() {
        if ch.is_ascii_alphanumeric() {
            current.push(ch);
            continue;
        }
        if !current.is_empty() {
            let lowered = current.to_ascii_lowercase();
            if lowered_terms.contains(&lowered) {
                rendered.push_str(pre_tag);
                rendered.push_str(&current);
                rendered.push_str(post_tag);
            } else {
                rendered.push_str(&current);
            }
            current.clear();
        }
        rendered.push(ch);
    }
    if !current.is_empty() {
        let lowered = current.to_ascii_lowercase();
        if lowered_terms.contains(&lowered) {
            rendered.push_str(pre_tag);
            rendered.push_str(&current);
            rendered.push_str(post_tag);
        } else {
            rendered.push_str(&current);
        }
    }
    rendered
}

fn build_suggest_response_body(
    suggest: &Value,
    resolved_indices: &[String],
    docs: &BTreeMap<String, StoredDocument>,
) -> Value {
    let mut suggest_body = serde_json::Map::new();
    let Some(suggest_object) = suggest.as_object() else {
        return Value::Object(suggest_body);
    };
    for (name, entry) in suggest_object {
        let Some(entry_object) = entry.as_object() else {
            continue;
        };
        if let Some(term) = entry_object.get("term").and_then(Value::as_object) {
            let text = entry_object.get("text").and_then(Value::as_str).unwrap_or_default();
            let field = term.get("field").and_then(Value::as_str).unwrap_or_default();
            let candidates = collect_term_suggest_candidates(docs, resolved_indices, field);
            let options = build_term_suggest_options(text, &candidates);
            suggest_body.insert(
                name.clone(),
                serde_json::json!([{
                    "text": text,
                    "offset": 0,
                    "length": text.chars().count(),
                    "options": options
                }]),
            );
            continue;
        }
        if let Some(completion) = entry_object.get("completion").and_then(Value::as_object) {
            let prefix = entry_object
                .get("prefix")
                .and_then(Value::as_str)
                .unwrap_or_default();
            let field = completion.get("field").and_then(Value::as_str).unwrap_or_default();
            let size = completion.get("size").and_then(Value::as_u64).unwrap_or(5) as usize;
            let candidates = collect_completion_suggest_candidates(docs, resolved_indices, field);
            let options = build_completion_suggest_options(prefix, &candidates, size);
            suggest_body.insert(
                name.clone(),
                serde_json::json!([{
                    "text": prefix,
                    "offset": 0,
                    "length": prefix.chars().count(),
                    "options": options
                }]),
            );
            continue;
        }
        if let Some(phrase) = entry_object.get("phrase").and_then(Value::as_object) {
            let text = entry_object.get("text").and_then(Value::as_str).unwrap_or_default();
            let field = phrase.get("field").and_then(Value::as_str).unwrap_or_default();
            let candidates = collect_term_suggest_candidates(docs, resolved_indices, field);
            let options = build_phrase_suggest_options(text, &candidates);
            suggest_body.insert(
                name.clone(),
                serde_json::json!([{
                    "text": text,
                    "offset": 0,
                    "length": text.chars().count(),
                    "options": options
                }]),
            );
        }
    }
    Value::Object(suggest_body)
}

fn collect_term_suggest_candidates(
    docs: &BTreeMap<String, StoredDocument>,
    resolved_indices: &[String],
    field: &str,
) -> BTreeMap<String, u64> {
    let mut frequencies = BTreeMap::new();
    for (key, record) in docs {
        let Some((doc_index, _, _)) = split_document_key(key) else {
            continue;
        };
        if !resolved_indices.iter().any(|candidate| candidate == doc_index) {
            continue;
        }
        let Some(value) = lookup_query_field_value(&record.source, field).and_then(Value::as_str) else {
            continue;
        };
        for token in tokenize_search_text(value) {
            *frequencies.entry(token).or_insert(0) += 1;
        }
    }
    frequencies
}

fn build_term_suggest_options(text: &str, candidates: &BTreeMap<String, u64>) -> Vec<Value> {
    let lowered = text.to_ascii_lowercase();
    let mut ranked = candidates
        .iter()
        .filter_map(|(candidate, frequency)| {
            if candidate == &lowered {
                return None;
            }
            let distance = levenshtein_distance(candidate, &lowered);
            if distance > 2 {
                return None;
            }
            Some((candidate.clone(), *frequency, distance))
        })
        .collect::<Vec<_>>();
    ranked.sort_by(|left, right| {
        left.2
            .cmp(&right.2)
            .then_with(|| right.1.cmp(&left.1))
            .then_with(|| left.0.cmp(&right.0))
    });
    ranked
        .into_iter()
        .take(3)
        .map(|(candidate, frequency, distance)| {
            serde_json::json!({
                "text": candidate,
                "score": 1.0 / (distance.max(1) as f64),
                "freq": frequency
            })
        })
        .collect()
}

fn collect_completion_suggest_candidates(
    docs: &BTreeMap<String, StoredDocument>,
    resolved_indices: &[String],
    field: &str,
) -> BTreeMap<String, u64> {
    let mut frequencies = BTreeMap::new();
    for (key, record) in docs {
        let Some((doc_index, _, _)) = split_document_key(key) else {
            continue;
        };
        if !resolved_indices.iter().any(|candidate| candidate == doc_index) {
            continue;
        }
        let Some(value) = lookup_query_field_value(&record.source, field) else {
            continue;
        };
        match value {
            Value::String(text) => {
                *frequencies.entry(text.to_ascii_lowercase()).or_insert(0) += 1;
            }
            Value::Array(items) => {
                for item in items.iter().filter_map(Value::as_str) {
                    *frequencies.entry(item.to_ascii_lowercase()).or_insert(0) += 1;
                }
            }
            _ => {}
        }
    }
    frequencies
}

fn build_completion_suggest_options(
    prefix: &str,
    candidates: &BTreeMap<String, u64>,
    size: usize,
) -> Vec<Value> {
    let lowered_prefix = prefix.to_ascii_lowercase();
    let mut ranked = candidates
        .iter()
        .filter(|(candidate, _)| candidate.starts_with(&lowered_prefix))
        .map(|(candidate, frequency)| (candidate.clone(), *frequency))
        .collect::<Vec<_>>();
    ranked.sort_by(|left, right| right.1.cmp(&left.1).then_with(|| left.0.cmp(&right.0)));
    let mut options = Vec::new();
    for (candidate, frequency) in ranked {
        for _ in 0..frequency {
            options.push(serde_json::json!({
                "text": candidate,
                "_score": 1.0
            }));
            if options.len() >= size {
                return options;
            }
        }
    }
    options
}

fn build_phrase_suggest_options(text: &str, candidates: &BTreeMap<String, u64>) -> Vec<Value> {
    let mut corrected_tokens = Vec::new();
    let mut changed = false;
    for token in tokenize_search_text(text) {
        if candidates.contains_key(&token) {
            corrected_tokens.push(token);
            continue;
        }
        let mut ranked = candidates
            .iter()
            .map(|(candidate, frequency)| {
                (
                    candidate.clone(),
                    *frequency,
                    levenshtein_distance(candidate, &token),
                )
            })
            .filter(|(_, _, distance)| *distance <= 2)
            .collect::<Vec<_>>();
        ranked.sort_by(|left, right| {
            left.2
                .cmp(&right.2)
                .then_with(|| right.1.cmp(&left.1))
                .then_with(|| left.0.cmp(&right.0))
        });
        if let Some((candidate, _, _)) = ranked.into_iter().next() {
            corrected_tokens.push(candidate);
            changed = true;
        } else {
            corrected_tokens.push(token);
        }
    }
    if !changed || corrected_tokens.is_empty() {
        return Vec::new();
    }
    vec![serde_json::json!({
        "text": corrected_tokens.join(" "),
        "score": 1.0
    })]
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

fn evaluate_text_query_spec(
    source: &Value,
    query_spec: &serde_json::Map<String, Value>,
    simple_syntax: bool,
) -> (bool, f64) {
    let query_text = query_spec
        .get("query")
        .and_then(Value::as_str)
        .unwrap_or_default();
    let default_operator = query_spec
        .get("default_operator")
        .and_then(Value::as_str)
        .unwrap_or("or");
    let fields = query_spec.get("fields").and_then(Value::as_array).map(|items| {
        items.iter()
            .filter_map(Value::as_str)
            .collect::<Vec<_>>()
    });
    let haystacks = collect_searchable_field_values(source, fields.as_deref());
    evaluate_text_query_strings(&haystacks, query_text, default_operator, simple_syntax)
}

fn collect_searchable_field_values(source: &Value, fields: Option<&[&str]>) -> Vec<String> {
    let Some(source_object) = source.as_object() else {
        return Vec::new();
    };
    if let Some(fields) = fields {
        return fields
            .iter()
            .filter_map(|field| lookup_query_field_value(source, field))
            .filter_map(Value::as_str)
            .map(str::to_string)
            .collect();
    }
    source_object
        .values()
        .filter_map(Value::as_str)
        .map(str::to_string)
        .collect()
}

fn evaluate_text_query_strings(
    haystacks: &[String],
    query_text: &str,
    default_operator: &str,
    simple_syntax: bool,
) -> (bool, f64) {
    let explicit_or = if simple_syntax && query_text.contains('|') {
        Some(
            query_text
                .split('|')
                .map(str::trim)
                .filter(|part| !part.is_empty())
                .map(str::to_string)
                .collect::<Vec<_>>(),
        )
    } else if query_text.contains(" OR ") {
        Some(
            query_text
                .split(" OR ")
                .map(str::trim)
                .filter(|part| !part.is_empty())
                .map(str::to_string)
                .collect::<Vec<_>>(),
        )
    } else {
        None
    };
    if let Some(disjuncts) = explicit_or {
        let mut best_score: f64 = 0.0;
        let mut matched = false;
        for disjunct in disjuncts {
            let (disjunct_matched, disjunct_score) =
                evaluate_text_conjunction(haystacks, &split_query_terms(&disjunct));
            if disjunct_matched {
                matched = true;
                best_score = best_score.max(disjunct_score);
            }
        }
        return (matched, if matched { best_score.max(1.0) } else { 0.0 });
    }
    if query_text.contains(" AND ") || default_operator == "and" {
        return evaluate_text_conjunction(haystacks, &split_query_terms(query_text));
    }
    let mut best_score: f64 = 0.0;
    let mut matched = false;
    for term in split_query_terms(query_text) {
        let term_score = score_text_query_term(haystacks, &term);
        if term_score > 0.0 {
            matched = true;
            best_score = best_score.max(term_score);
        }
    }
    (matched, if matched { best_score.max(1.0) } else { 0.0 })
}

fn split_query_terms(query_text: &str) -> Vec<String> {
    let mut terms = Vec::new();
    let mut current = String::new();
    let mut in_quotes = false;
    let mut chars = query_text.chars().peekable();
    while let Some(ch) = chars.next() {
        match ch {
            '"' => {
                in_quotes = !in_quotes;
            }
            ' ' if !in_quotes => {
                if !current.is_empty() {
                    if current != "AND" && current != "OR" {
                        terms.push(std::mem::take(&mut current));
                    } else {
                        current.clear();
                    }
                }
                while chars.peek().is_some_and(|next| *next == ' ') {
                    chars.next();
                }
            }
            _ => current.push(ch),
        }
    }
    if !current.is_empty() && current != "AND" && current != "OR" {
        terms.push(current);
    }
    terms
}

fn evaluate_text_conjunction(haystacks: &[String], terms: &[String]) -> (bool, f64) {
    if terms.is_empty() {
        return (true, 1.0);
    }
    let mut score = 0.0;
    for term in terms {
        let term_score = score_text_query_term(haystacks, term);
        if term_score == 0.0 {
            return (false, 0.0);
        }
        score += term_score;
    }
    (true, score.max(1.0))
}

fn score_text_query_term(haystacks: &[String], term: &str) -> f64 {
    let phrase = term.trim_matches('"');
    let is_phrase = term.contains(' ') || term.starts_with('"') || term.ends_with('"');
    let mut best_score: f64 = 0.0;
    for haystack in haystacks {
        let candidate = Value::String(haystack.clone());
        let score = if is_phrase {
            if value_matches_phrase(Some(&candidate), phrase, false) {
                phrase.split_whitespace().count().max(1) as f64
            } else {
                0.0
            }
        } else {
            score_match_query(Some(&candidate), phrase)
        };
        best_score = best_score.max(score);
    }
    best_score
}

fn lookup_query_field_value<'a>(source: &'a Value, field: &str) -> Option<&'a Value> {
    if let Some(value) = source.get(field) {
        return Some(value);
    }
    let mut current = source;
    let mut traversed = false;
    let mut traversal_failed = false;
    for segment in field.split('.') {
        match current.get(segment) {
            Some(next) => {
                current = next;
                traversed = true;
            }
            None => {
                traversal_failed = true;
                break;
            }
        }
    }
    if traversed && !traversal_failed {
        return Some(current);
    }
    field.rsplit('.').next().and_then(|last| source.get(last))
}

fn extract_string_query_value(value: &Value) -> Option<&str> {
    if let Some(object) = value.as_object() {
        return object.get("value").and_then(Value::as_str);
    }
    value.as_str()
}

fn extract_fuzzy_query_value(value: &Value) -> Option<(&str, usize)> {
    if let Some(object) = value.as_object() {
        let query_value = object.get("value").and_then(Value::as_str)?;
        let fuzziness = match object.get("fuzziness") {
            Some(Value::String(mode)) if mode == "AUTO" => auto_fuzziness(query_value),
            Some(value) => value.as_u64()? as usize,
            None => auto_fuzziness(query_value),
        };
        return Some((query_value, fuzziness));
    }
    let query_value = value.as_str()?;
    Some((query_value, auto_fuzziness(query_value)))
}

fn auto_fuzziness(query_value: &str) -> usize {
    match query_value.chars().count() {
        0..=2 => 0,
        3..=5 => 1,
        _ => 2,
    }
}

fn value_matches_phrase(candidate: Option<&Value>, expected: &str, prefix_last_token: bool) -> bool {
    let Some(candidate_text) = candidate.and_then(Value::as_str) else {
        return false;
    };
    let candidate_tokens = tokenize_search_text(candidate_text);
    let expected_tokens = tokenize_search_text(expected);
    if expected_tokens.is_empty() || candidate_tokens.len() < expected_tokens.len() {
        return false;
    }
    for window in candidate_tokens.windows(expected_tokens.len()) {
        let mut matched = true;
        for (index, expected_token) in expected_tokens.iter().enumerate() {
            let candidate_token = &window[index];
            let token_matches = if prefix_last_token && index + 1 == expected_tokens.len() {
                candidate_token.starts_with(expected_token)
            } else {
                candidate_token == expected_token
            };
            if !token_matches {
                matched = false;
                break;
            }
        }
        if matched {
            return true;
        }
    }
    false
}

fn value_matches_wildcard(candidate: Option<&Value>, expected: &str) -> bool {
    let Some(candidate_text) = candidate.and_then(Value::as_str) else {
        return false;
    };
    wildcard_match(
        &expected.to_ascii_lowercase(),
        &candidate_text.to_ascii_lowercase(),
    )
}

fn value_matches_prefix(candidate: Option<&Value>, expected: &str) -> bool {
    let Some(candidate_text) = candidate.and_then(Value::as_str) else {
        return false;
    };
    candidate_text
        .to_ascii_lowercase()
        .starts_with(&expected.to_ascii_lowercase())
}

fn value_matches_regexp(candidate: Option<&Value>, expected: &str) -> bool {
    let Some(candidate_text) = candidate.and_then(Value::as_str) else {
        return false;
    };
    bounded_regexp_match(
        expected.as_bytes(),
        candidate_text.to_ascii_lowercase().as_bytes(),
    )
}

fn bounded_regexp_match(pattern: &[u8], candidate: &[u8]) -> bool {
    fn recurse(pattern: &[u8], candidate: &[u8]) -> bool {
        if pattern.is_empty() {
            return candidate.is_empty();
        }
        let char_matches = !candidate.is_empty() && (pattern[0] == b'.' || pattern[0] == candidate[0]);
        if pattern.len() >= 2 && pattern[1] == b'*' {
            return recurse(&pattern[2..], candidate)
                || (char_matches && recurse(pattern, &candidate[1..]));
        }
        char_matches && recurse(&pattern[1..], &candidate[1..])
    }
    recurse(
        &pattern
            .iter()
            .map(u8::to_ascii_lowercase)
            .collect::<Vec<_>>(),
        candidate,
    )
}

fn value_matches_fuzzy(candidate: Option<&Value>, expected: &str, fuzziness: usize) -> bool {
    let Some(candidate_text) = candidate.and_then(Value::as_str) else {
        return false;
    };
    let expected = expected.to_ascii_lowercase();
    tokenize_search_text(candidate_text)
        .into_iter()
        .any(|token| levenshtein_distance(&token, &expected) <= fuzziness)
}

fn value_matches_terms_set(candidate: Option<&Value>, expected: &Value) -> Option<(bool, f64)> {
    let candidate = candidate?;
    let expected_object = expected.as_object()?;
    let terms = expected_object.get("terms")?.as_array()?;
    let minimum = expected_object
        .get("minimum_should_match_script")
        .and_then(Value::as_object)?
        .get("source")?
        .as_str()?
        .parse::<usize>()
        .ok()?;
    let mut matched_terms = 0usize;
    for term in terms {
        let matched = match candidate {
            Value::Array(values) => values.iter().any(|value| value == term),
            _ => candidate == term,
        };
        if matched {
            matched_terms += 1;
        }
    }
    Some((
        matched_terms >= minimum,
        if matched_terms >= minimum {
            matched_terms.max(1) as f64
        } else {
            0.0
        },
    ))
}

fn parse_distance_meters(raw: &str) -> Option<f64> {
    let raw = raw.trim().to_ascii_lowercase();
    if let Some(value) = raw.strip_suffix("km") {
        return value.parse::<f64>().ok().map(|distance| distance * 1000.0);
    }
    if let Some(value) = raw.strip_suffix('m') {
        return value.parse::<f64>().ok();
    }
    None
}

fn parse_geo_point_value(value: &Value) -> Option<(f64, f64)> {
    let object = value.as_object()?;
    Some((
        object.get("lat")?.as_f64()?,
        object.get("lon")?.as_f64()?,
    ))
}

fn haversine_distance_meters(left: (f64, f64), right: (f64, f64)) -> f64 {
    let earth_radius_m = 6_371_000.0_f64;
    let (left_lat, left_lon) = (left.0.to_radians(), left.1.to_radians());
    let (right_lat, right_lon) = (right.0.to_radians(), right.1.to_radians());
    let delta_lat = right_lat - left_lat;
    let delta_lon = right_lon - left_lon;
    let a = (delta_lat / 2.0).sin().powi(2)
        + left_lat.cos() * right_lat.cos() * (delta_lon / 2.0).sin().powi(2);
    let c = 2.0 * a.sqrt().atan2((1.0 - a).sqrt());
    earth_radius_m * c
}

fn levenshtein_distance(left: &str, right: &str) -> usize {
    let left_chars = left.chars().collect::<Vec<_>>();
    let right_chars = right.chars().collect::<Vec<_>>();
    let mut prev = (0..=right_chars.len()).collect::<Vec<_>>();
    let mut curr = vec![0; right_chars.len() + 1];
    for (i, left_char) in left_chars.iter().enumerate() {
        curr[0] = i + 1;
        for (j, right_char) in right_chars.iter().enumerate() {
            let cost = usize::from(left_char != right_char);
            curr[j + 1] = (curr[j] + 1)
                .min(prev[j + 1] + 1)
                .min(prev[j] + cost);
        }
        std::mem::swap(&mut prev, &mut curr);
    }
    prev[right_chars.len()]
}

fn evaluate_span_query(source: &Value, span_term: &serde_json::Map<String, Value>) -> Option<bool> {
    let (field, expected) = span_term.iter().next()?;
    Some(value_matches_term(
        lookup_query_field_value(source, field),
        expected,
        None,
    ))
}

fn evaluate_span_or_query(source: &Value, span_or: &serde_json::Map<String, Value>) -> Option<bool> {
    let clauses = span_or.get("clauses")?.as_array()?;
    for clause in clauses {
        if evaluate_span_like_clause(source, clause)? {
            return Some(true);
        }
    }
    Some(false)
}

fn evaluate_span_near_query(source: &Value, span_near: &serde_json::Map<String, Value>) -> Option<bool> {
    let clauses = span_near.get("clauses")?.as_array()?;
    let slop = span_near.get("slop")?.as_u64()? as usize;
    let in_order = span_near.get("in_order")?.as_bool()?;
    let mut extracted = Vec::new();
    for clause in clauses {
        extracted.push(extract_span_clause(source, clause)?);
    }
    let field = extracted.first()?.0.clone();
    if extracted.iter().any(|(candidate_field, _)| *candidate_field != field) {
        return Some(false);
    }
    let tokens = tokenize_search_text(lookup_query_field_value(source, &field)?.as_str()?);
    if tokens.is_empty() {
        return Some(false);
    }
    let term_sets = extracted
        .into_iter()
        .map(|(_, values)| values)
        .collect::<Vec<_>>();
    if in_order {
        let mut previous_position: Option<usize> = None;
        for accepted_terms in &term_sets {
            let start = previous_position.map(|position| position + 1).unwrap_or(0);
            let mut matched_position = None;
            for (index, token) in tokens.iter().enumerate().skip(start) {
                if accepted_terms.iter().any(|term| term == token) {
                    matched_position = Some(index);
                    break;
                }
            }
            let Some(position) = matched_position else {
                return Some(false);
            };
            if let Some(previous) = previous_position {
                let gap = position.saturating_sub(previous + 1);
                if gap > slop {
                    return Some(false);
                }
            }
            previous_position = Some(position);
        }
        return Some(true);
    }
    for accepted_terms in &term_sets {
        if !tokens
            .iter()
            .any(|token| accepted_terms.iter().any(|term| term == token))
        {
            return Some(false);
        }
    }
    Some(true)
}

fn evaluate_span_multi_query(source: &Value, span_multi: &serde_json::Map<String, Value>) -> Option<bool> {
    let inner = span_multi.get("match")?;
    if let Some(prefix_query) = inner.get("prefix").and_then(Value::as_object) {
        let (field, expected) = prefix_query.iter().next()?;
        let expected_value = extract_string_query_value(expected)?;
        return Some(value_matches_prefix(
            lookup_query_field_value(source, field),
            expected_value,
        ));
    }
    None
}

fn evaluate_field_masking_span_query(
    source: &Value,
    field_masking_span: &serde_json::Map<String, Value>,
) -> Option<bool> {
    let field = field_masking_span.get("field")?.as_str()?;
    let inner = field_masking_span.get("query")?;
    let Value::Object(inner_object) = inner else {
        return None;
    };
    if let Some(span_term) = inner_object.get("span_term").and_then(Value::as_object) {
        let (inner_field, expected) = span_term.iter().next()?;
        if inner_field != field {
            return Some(false);
        }
        return Some(value_matches_term(
            lookup_query_field_value(source, field),
            expected,
            None,
        ));
    }
    None
}

fn evaluate_span_like_clause(source: &Value, clause: &Value) -> Option<bool> {
    let object = clause.as_object()?;
    if let Some(span_term) = object.get("span_term").and_then(Value::as_object) {
        return evaluate_span_query(source, span_term);
    }
    if let Some(span_multi) = object.get("span_multi").and_then(Value::as_object) {
        return evaluate_span_multi_query(source, span_multi);
    }
    None
}

fn extract_span_clause(
    source: &Value,
    clause: &Value,
) -> Option<(String, Vec<String>)> {
    let object = clause.as_object()?;
    if let Some(span_term) = object.get("span_term").and_then(Value::as_object) {
        let (field, expected) = span_term.iter().next()?;
        return Some((field.clone(), vec![expected.as_str()?.to_ascii_lowercase()]));
    }
    if let Some(span_multi) = object.get("span_multi").and_then(Value::as_object) {
        let inner = span_multi.get("match")?;
        let prefix_query = inner.get("prefix").and_then(Value::as_object)?;
        let (field, expected) = prefix_query.iter().next()?;
        let expected_value = extract_string_query_value(expected)?.to_ascii_lowercase();
        let tokens = tokenize_search_text(lookup_query_field_value(source, field)?.as_str()?);
        let accepted = tokens
            .into_iter()
            .filter(|token| token.starts_with(&expected_value))
            .collect::<Vec<_>>();
        return Some((field.clone(), accepted));
    }
    None
}

fn evaluate_intervals_query(candidate: Option<&Value>, spec: &Value) -> Option<bool> {
    let candidate_text = candidate?.as_str()?;
    let tokens = tokenize_search_text(candidate_text);
    let interval_object = spec.as_object()?;
    if let Some(match_spec) = interval_object.get("match").and_then(Value::as_object) {
        let query_text = match_spec.get("query")?.as_str()?;
        let ordered = match_spec.get("ordered").and_then(Value::as_bool).unwrap_or(true);
        let max_gaps = match_spec.get("max_gaps").and_then(Value::as_u64).unwrap_or(0) as usize;
        let terms = tokenize_search_text(query_text);
        return Some(tokens_match_interval_terms(&tokens, &terms, ordered, max_gaps));
    }
    if let Some(all_of) = interval_object.get("all_of").and_then(Value::as_object) {
        let ordered = all_of.get("ordered").and_then(Value::as_bool).unwrap_or(true);
        let max_gaps = all_of.get("max_gaps").and_then(Value::as_u64).unwrap_or(0) as usize;
        let mut terms = Vec::new();
        for interval in all_of.get("intervals")?.as_array()? {
            let match_spec = interval.get("match")?.as_object()?;
            terms.extend(tokenize_search_text(match_spec.get("query")?.as_str()?));
        }
        return Some(tokens_match_interval_terms(&tokens, &terms, ordered, max_gaps));
    }
    None
}

fn tokens_match_interval_terms(
    candidate_tokens: &[String],
    expected_terms: &[String],
    ordered: bool,
    max_gaps: usize,
) -> bool {
    if expected_terms.is_empty() {
        return false;
    }
    if ordered {
        let mut previous_position = None;
        for expected in expected_terms {
            let start = previous_position.map(|position| position + 1).unwrap_or(0);
            let mut matched_position = None;
            for (index, token) in candidate_tokens.iter().enumerate().skip(start) {
                if token == expected {
                    matched_position = Some(index);
                    break;
                }
            }
            let Some(position) = matched_position else {
                return false;
            };
            if let Some(previous) = previous_position {
                let gap = position.saturating_sub(previous + 1);
                if gap > max_gaps {
                    return false;
                }
            }
            previous_position = Some(position);
        }
        return true;
    }
    expected_terms.iter().all(|expected| candidate_tokens.iter().any(|token| token == expected))
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
    if let Some(candidate_number) = candidate.and_then(Value::as_f64) {
        let gte = bounds.get("gte").and_then(Value::as_f64);
        let gt = bounds.get("gt").and_then(Value::as_f64);
        let lte = bounds.get("lte").and_then(Value::as_f64);
        let lt = bounds.get("lt").and_then(Value::as_f64);
        return gte.map_or(true, |bound| candidate_number >= bound)
            && gt.map_or(true, |bound| candidate_number > bound)
            && lte.map_or(true, |bound| candidate_number <= bound)
            && lt.map_or(true, |bound| candidate_number < bound);
    }
    let Some(candidate_text) = candidate.and_then(Value::as_str) else {
        return false;
    };
    let gte = bounds.get("gte").and_then(Value::as_str);
    let gt = bounds.get("gt").and_then(Value::as_str);
    let lte = bounds.get("lte").and_then(Value::as_str);
    let lt = bounds.get("lt").and_then(Value::as_str);
    gte.map_or(true, |bound| candidate_text >= bound)
        && gt.map_or(true, |bound| candidate_text > bound)
        && lte.map_or(true, |bound| candidate_text <= bound)
        && lt.map_or(true, |bound| candidate_text < bound)
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

fn stringify_leaf_scalars(value: &Value) -> Value {
    match value {
        Value::Object(object) => Value::Object(
            object
                .iter()
                .map(|(key, value)| (key.clone(), stringify_leaf_scalars(value)))
                .collect(),
        ),
        Value::Array(values) => Value::Array(values.iter().map(stringify_leaf_scalars).collect()),
        Value::Number(number) => Value::String(number.to_string()),
        Value::Bool(boolean) => Value::String(boolean.to_string()),
        _ => value.clone(),
    }
}

fn merge_object_with_null_reset(base: &mut Value, update: &Value) {
    let Some(base_object) = base.as_object_mut() else {
        *base = update.clone();
        return;
    };
    let Some(update_object) = update.as_object() else {
        *base = update.clone();
        return;
    };
    for (key, value) in update_object {
        if value.is_null() {
            base_object.remove(key);
            continue;
        }
        match base_object.get_mut(key) {
            Some(existing) if existing.is_object() && value.is_object() => {
                merge_object_with_null_reset(existing, value);
            }
            _ => {
                base_object.insert(key.clone(), value.clone());
            }
        }
    }
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
            let order = terms.get("order").and_then(Value::as_object);
            let order_key = order
                .and_then(|value| value.iter().next())
                .map(|(key, direction)| (key.as_str(), direction.as_str().unwrap_or("desc")));
            match order_key {
                Some(("_count", "asc")) => buckets.sort_by(|left, right| {
                    left.1.cmp(&right.1).then_with(|| left.0.cmp(&right.0))
                }),
                Some(("_count", _)) | None => buckets.sort_by(|left, right| {
                    right.1.cmp(&left.1).then_with(|| left.0.cmp(&right.0))
                }),
                Some(("_key", "desc")) => buckets.sort_by(|left, right| right.0.cmp(&left.0)),
                Some(("_key", _)) => buckets.sort_by(|left, right| left.0.cmp(&right.0)),
                Some(_) => {
                    return Err(build_unsupported_search_response(
                        "unsupported aggregation option [terms.order]",
                    ))
                }
            }
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
        if let Some(date_histogram) = aggregation_object.get("date_histogram").and_then(Value::as_object) {
            let field = date_histogram.get("field").and_then(Value::as_str).unwrap_or_default();
            let interval = date_histogram
                .get("calendar_interval")
                .or_else(|| date_histogram.get("fixed_interval"))
                .and_then(Value::as_str)
                .unwrap_or_default();
            if interval != "day" {
                return Err(build_unsupported_search_response(
                    "unsupported aggregation [date_histogram]",
                ));
            }
            let mut counts = std::collections::BTreeMap::<i64, (String, u64)>::new();
            for hit in hits {
                let Some(raw) = hit.get("_source").and_then(|source| source.get(field)).and_then(Value::as_str) else {
                    continue;
                };
                let Some((bucket_key, bucket_string)) = date_histogram_bucket_day(raw) else {
                    continue;
                };
                let entry = counts.entry(bucket_key).or_insert((bucket_string, 0));
                entry.1 += 1;
            }
            let buckets = counts
                .into_iter()
                .map(|(key, (key_as_string, doc_count))| serde_json::json!({
                    "key": key,
                    "key_as_string": key_as_string,
                    "doc_count": doc_count,
                }))
                .collect::<Vec<_>>();
            result.insert(name.clone(), serde_json::json!({ "buckets": buckets }));
            continue;
        }
        if let Some(histogram) = aggregation_object.get("histogram").and_then(Value::as_object) {
            let field = histogram.get("field").and_then(Value::as_str).unwrap_or_default();
            let interval = histogram.get("interval").and_then(Value::as_f64).unwrap_or(0.0);
            if interval <= 0.0 {
                return Err(build_unsupported_search_response(
                    "unsupported aggregation [histogram]",
                ));
            }
            let mut counts = std::collections::BTreeMap::<i64, u64>::new();
            for hit in hits {
                let Some(value) = hit.get("_source").and_then(|source| source.get(field)).and_then(Value::as_f64) else {
                    continue;
                };
                let bucket = (value / interval).floor() as i64;
                *counts.entry(bucket).or_insert(0) += 1;
            }
            let buckets = if counts.is_empty() {
                Vec::new()
            } else {
                let min_bucket = *counts.keys().next().unwrap_or(&0);
                let max_bucket = *counts.keys().next_back().unwrap_or(&0);
                (min_bucket..=max_bucket)
                    .map(|bucket| serde_json::json!({
                        "key": (bucket as f64) * interval,
                        "doc_count": counts.get(&bucket).copied().unwrap_or(0),
                    }))
                    .collect::<Vec<_>>()
            };
            result.insert(name.clone(), serde_json::json!({ "buckets": buckets }));
            continue;
        }
        if let Some(range) = aggregation_object.get("range").and_then(Value::as_object) {
            let field = range.get("field").and_then(Value::as_str).unwrap_or_default();
            let ranges = range.get("ranges").and_then(Value::as_array).cloned().unwrap_or_default();
            let mut buckets = Vec::new();
            for bucket in ranges {
                let bucket_object = match bucket.as_object() {
                    Some(v) => v,
                    None => continue,
                };
                let from = bucket_object.get("from").and_then(Value::as_f64);
                let to = bucket_object.get("to").and_then(Value::as_f64);
                let key = bucket_object
                    .get("key")
                    .cloned()
                    .unwrap_or_else(|| Value::String(default_range_bucket_key(from, to)));
                let doc_count = hits
                    .iter()
                    .filter(|hit| {
                        let Some(value) = hit.get("_source").and_then(|source| source.get(field)).and_then(Value::as_f64) else {
                            return false;
                        };
                        from.map_or(true, |bound| value >= bound) && to.map_or(true, |bound| value < bound)
                    })
                    .count() as u64;
                buckets.push(serde_json::json!({ "key": key, "doc_count": doc_count }));
            }
            result.insert(name.clone(), serde_json::json!({ "buckets": buckets }));
            continue;
        }
        if let Some(cardinality) = aggregation_object.get("cardinality").and_then(Value::as_object) {
            let field = cardinality.get("field").and_then(Value::as_str).unwrap_or_default();
            let mut seen = std::collections::BTreeSet::new();
            for hit in hits {
                if let Some(value) = hit.get("_source").and_then(|source| source.get(field)) {
                    seen.insert(value.to_string());
                }
            }
            result.insert(name.clone(), serde_json::json!({ "value": seen.len() }));
            continue;
        }
        if aggregation_object.get("significant_terms").is_some() {
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
        if let Some(scripted_metric) = aggregation_object
            .get("scripted_metric")
            .and_then(Value::as_object)
        {
            let init_ok = scripted_metric
                .get("init_script")
                .and_then(Value::as_str)
                .map(|script| script == "state.count = 0")
                .unwrap_or(false);
            let map_ok = scripted_metric
                .get("map_script")
                .and_then(Value::as_str)
                .map(|script| script == "state.count += params.inc")
                .unwrap_or(false);
            let combine_ok = scripted_metric
                .get("combine_script")
                .and_then(Value::as_str)
                .map(|script| script == "return state.count")
                .unwrap_or(false);
            let reduce_ok = scripted_metric
                .get("reduce_script")
                .and_then(Value::as_str)
                .map(|script| script == "double sum = 0; for (s in states) { sum += s } return sum")
                .unwrap_or(false);
            if init_ok && map_ok && combine_ok && reduce_ok {
                let increment = scripted_metric
                    .get("params")
                    .and_then(|params| params.get("inc"))
                    .and_then(Value::as_f64)
                    .unwrap_or(1.0);
                result.insert(
                    name.clone(),
                    serde_json::json!({
                        "value": (hits.len() as f64) * increment
                    }),
                );
                continue;
            }
            return Err(build_unsupported_search_response(
                "unsupported aggregation [scripted_metric]",
            ));
        }
    }
    Ok(Some(Value::Object(result)))
}

fn default_range_bucket_key(from: Option<f64>, to: Option<f64>) -> String {
    match (from, to) {
        (Some(from), Some(to)) => format!("{from}-{to}"),
        (Some(from), None) => format!("{from}-*"),
        (None, Some(to)) => format!("*-{to}"),
        (None, None) => "*".to_string(),
    }
}

fn date_histogram_bucket_day(timestamp: &str) -> Option<(i64, String)> {
    let date = timestamp.get(0..10)?;
    let year: i32 = date.get(0..4)?.parse().ok()?;
    let month: u32 = date.get(5..7)?.parse().ok()?;
    let day: u32 = date.get(8..10)?.parse().ok()?;
    let days = days_from_civil(year, month, day)?;
    let millis = days.checked_mul(86_400_000)?;
    Some((millis, format!("{date}T00:00:00.000Z")))
}

fn days_from_civil(year: i32, month: u32, day: u32) -> Option<i64> {
    if !(1..=12).contains(&month) || !(1..=31).contains(&day) {
        return None;
    }
    let year = year - ((month <= 2) as i32);
    let era = if year >= 0 { year } else { year - 399 } / 400;
    let yoe = year - era * 400;
    let month = month as i32;
    let day = day as i32;
    let doy = (153 * (month + if month > 2 { -3 } else { 9 }) + 2) / 5 + day - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    Some((era * 146097 + doe - 719468) as i64)
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
        refreshed: true,
    };
    evaluate_search_query(
        &record,
        hit.get("_id").and_then(Value::as_str).unwrap_or_default(),
        query,
    )
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

fn exclude_source_fields(source: &Value, excludes: &str) -> Value {
    let Some(object) = source.as_object() else {
        return source.clone();
    };
    let selectors = excludes
        .split(',')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .collect::<BTreeSet<_>>();
    let mut filtered = serde_json::Map::new();
    for (key, value) in object {
        if !selectors.contains(key.as_str()) {
            filtered.insert(key.clone(), value.clone());
        }
    }
    Value::Object(filtered)
}

fn apply_supported_update_script(source: &mut Value, script: &Value) -> Result<(), RestResponse> {
    let Some(script_object) = script.as_object() else {
        return Err(RestResponse::json(
            400,
            serde_json::json!({
                "error": {
                    "type": "illegal_argument_exception",
                    "reason": "update script must be an object"
                },
                "status": 400
            }),
        ));
    };
    let Some(script_source) = script_object.get("source").and_then(Value::as_str) else {
        return Err(RestResponse::json(
            400,
            serde_json::json!({
                "error": {
                    "type": "illegal_argument_exception",
                    "reason": "update script source is required"
                },
                "status": 400
            }),
        ));
    };
    let params = script_object
        .get("params")
        .and_then(Value::as_object)
        .cloned()
        .unwrap_or_default();
    let Some(field_expr) = script_source.strip_prefix("ctx._source.") else {
        return Err(RestResponse::json(
            400,
            serde_json::json!({
                "error": {
                    "type": "illegal_argument_exception",
                    "reason": "unsupported update script"
                },
                "status": 400
            }),
        ));
    };
    let Some((field, param)) = field_expr.split_once(" = params.") else {
        return Err(RestResponse::json(
            400,
            serde_json::json!({
                "error": {
                    "type": "illegal_argument_exception",
                    "reason": "unsupported update script"
                },
                "status": 400
            }),
        ));
    };
    let Some(value) = params.get(param).cloned() else {
        return Err(RestResponse::json(
            400,
            serde_json::json!({
                "error": {
                    "type": "illegal_argument_exception",
                    "reason": format!("missing script param [{param}]")
                },
                "status": 400
            }),
        ));
    };
    let Some(object) = source.as_object_mut() else {
        *source = serde_json::json!({});
        let object = source.as_object_mut().expect("source converted to object");
        object.insert(field.to_string(), value);
        return Ok(());
    };
    object.insert(field.to_string(), value);
    Ok(())
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

fn cluster_health_status_rank(status: &str) -> u8 {
    match status {
        "green" => 3,
        "yellow" => 2,
        "red" => 1,
        _ => 0,
    }
}

fn matches_index_selector(selector: &str, index: &str) -> bool {
    if selector == "_all" || selector == "*" {
        return true;
    }
    selector.split(',').any(|pattern| wildcard_match(pattern, index))
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
    for (key, value) in flatten_cluster_settings_section(patch) {
        if value.is_null() {
            merged.remove(&key);
        } else {
            merged.insert(key, value);
        }
    }
    Value::Object(merged)
}

fn render_cluster_settings_section(section: &Value, flat_settings: bool) -> Value {
    if flat_settings {
        return match section {
            Value::Object(map) => Value::Object(map.clone()),
            _ => Value::Object(serde_json::Map::new()),
        };
    }
    expand_dotted_cluster_settings_section(section)
}

fn flatten_cluster_settings_section(section: &Value) -> serde_json::Map<String, Value> {
    let mut flat = serde_json::Map::new();
    flatten_cluster_settings_section_into(None, section, &mut flat);
    flat
}

fn flatten_cluster_settings_section_into(
    prefix: Option<&str>,
    section: &Value,
    flat: &mut serde_json::Map<String, Value>,
) {
    match section {
        Value::Object(map) => {
            for (key, value) in map {
                let next_key = prefix
                    .map(|current| format!("{current}.{key}"))
                    .unwrap_or_else(|| key.clone());
                if value.is_object() {
                    flatten_cluster_settings_section_into(Some(&next_key), value, flat);
                } else {
                    flat.insert(next_key, value.clone());
                }
            }
        }
        Value::Null => {
            if let Some(prefix) = prefix {
                flat.insert(prefix.to_string(), Value::Null);
            }
        }
        _ => {
            if let Some(prefix) = prefix {
                flat.insert(prefix.to_string(), section.clone());
            }
        }
    }
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

fn query_param_is_true(raw: Option<&String>) -> bool {
    matches!(raw.map(String::as_str), Some("true") | Some("1"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use os_core::OPENSEARCH_3_7_0_TRANSPORT;

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

    #[test]
    fn openapi_route_serves_generated_spec() {
        let node = SteelNode::new(NodeInfo {
            name: "steel-node".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        });
        let response = node.handle_rest_request(RestRequest::new(RestMethod::Get, "/openapi.json"));
        assert_eq!(response.status, 200);
        assert_eq!(
            response.headers.get("content-type").map(String::as_str),
            Some("application/json")
        );
        assert_eq!(response.body["openapi"], "3.0.3");
        assert_eq!(response.body["info"]["title"], "Steelsearch OpenSearch-Compatible API");
    }

    #[test]
    fn swagger_ui_route_serves_html_shell() {
        let node = SteelNode::new(NodeInfo {
            name: "steel-node".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        });
        let response = node.handle_rest_request(RestRequest::new(RestMethod::Get, "/docs"));
        assert_eq!(response.status, 200);
        assert_eq!(
            response.headers.get("content-type").map(String::as_str),
            Some("text/html; charset=utf-8")
        );
        let body = response.body.as_str().expect("html body should be string");
        assert!(body.contains("/openapi.json"));
        assert!(body.contains("/swagger-ui/swagger-ui.css"));
        assert!(body.contains("/swagger-ui/swagger-ui-bundle.js"));
    }

    #[test]
    fn swagger_ui_bundle_route_serves_local_asset() {
        let node = SteelNode::new(NodeInfo {
            name: "steel-node".to_string(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
        });
        let response = node.handle_rest_request(RestRequest::new(
            RestMethod::Get,
            "/swagger-ui/swagger-ui-bundle.js",
        ));
        assert_eq!(response.status, 200);
        assert_eq!(
            response.headers.get("content-type").map(String::as_str),
            Some("application/javascript; charset=utf-8")
        );
        let body = response.body.as_str().expect("javascript body should be string");
        assert!(body.contains("SwaggerUIBundle"));
    }
}
