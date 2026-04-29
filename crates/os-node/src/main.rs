use os_core::version::OPENSEARCH_3_7_0_TRANSPORT;
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
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::io::Write;
use std::net::{IpAddr, Ipv4Addr, SocketAddr};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

static SHUTDOWN_REQUESTED: AtomicBool = AtomicBool::new(false);

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
    let listener = bind_rest_http_listener(SocketAddr::new(config.host, config.port))?;
    let address = listener.local_addr()?;
    config.port = address.port();
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

    eprintln!(
        "Steelsearch development daemon listening on http://{}",
        address
    );
    eprintln!(
        "node id={}, name={}, transport={}, roles={}, seed_hosts={}, data_path={}",
        config.node_id,
        config.node_name,
        transport_address,
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
    eprintln!(
        "development mode: standalone HTTP compatibility surface only; development_security={}, production security and multi-node runtime are not complete",
        config.development_security_mode.as_str()
    );
    if let Some(manifest_path) = config.extension_manifest_path.as_ref() {
        eprintln!("extension boundary manifest: {}", manifest_path.display());
    }

    serve_rest_http_listener_until(node, listener, || SHUTDOWN_REQUESTED.load(Ordering::SeqCst))?;
    Ok(())
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
    development_security_mode: DevelopmentSecurityMode,
    #[cfg_attr(not(test), allow(dead_code))]
    extension_registry: ExtensionBoundaryRegistry,
    extension_registry_overrides: ExtensionRegistryOverrideConfig,
    extension_manifest_path: Option<PathBuf>,
}

trait DevelopmentClusterViewConfig {
    fn node_id(&self) -> &str;
    fn node_name(&self) -> &str;
    fn cluster_name(&self) -> &str;
    fn seed_hosts(&self) -> &[String];
    fn roles(&self) -> Vec<String>;
    fn local_http_address(&self) -> String;
    fn local_transport_address(&self) -> String;
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
            "--help" | "-h" => {
                print_help();
                std::process::exit(0);
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
        development_security_mode,
        extension_registry,
        extension_registry_overrides,
        extension_manifest_path,
    };
    validate_startup_preflight(&config)?;
    if mode == DaemonMode::Production {
        validate_production_mode_request(
            &SecurityBoundaryPolicy::default(),
            ReleaseReadinessChecklist::default(),
        )?;
    }
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
    blockers
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
        let result = elect();
        windows.push(window);
        if result.elected_node_id.is_some() || scheduler.attempts() >= max_attempts {
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
    if election.elected_node_id.is_some() {
        coordination.liveness.clear_local_fence();
    }
    Some(election)
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
  --node.roles <csv>               Node roles, default cluster_manager,data,ingest\n\
  --cluster.name <name>            Cluster name, default steelsearch-dev\n\
  --discovery.seed_hosts <csv>     Transport seed hosts, default empty\n\
  --path.data <path>               Data path, default data/steelsearch\n\
  --extensions.knn <bool>          Enable k-NN compatibility plugin, default true\n\
  --extensions.ml_commons <bool>   Enable ML Commons compatibility plugin, default true\n\
  --extensions.manifest <path>     Load extension registry overrides from JSON manifest\n\
  --development.security_mode <mode>\n\
                                    Development security mode, default disabled\n\
  --mode <development|production>  Runtime mode, default development\n\
\n\
Environment:\n\
  STEELSEARCH_HTTP_HOST, STEELSEARCH_HTTP_PORT,\n\
  STEELSEARCH_TRANSPORT_HOST, STEELSEARCH_TRANSPORT_PORT,\n\
  STEELSEARCH_NODE_ID, STEELSEARCH_NODE_NAME, STEELSEARCH_NODE_ROLES,\n\
  STEELSEARCH_CLUSTER_NAME, STEELSEARCH_DISCOVERY_SEED_HOSTS,\n\
  STEELSEARCH_DATA_PATH, STEELSEARCH_DEVELOPMENT_SECURITY_MODE,\n\
  STEELSEARCH_ENABLE_KNN_PLUGIN, STEELSEARCH_ENABLE_ML_COMMONS,\n\
  STEELSEARCH_EXTENSION_MANIFEST,\n\
  STEELSEARCH_MODE"
}

#[cfg(test)]
mod tests {
    use super::*;
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
    fn daemon_help_text_uses_steelsearch_runtime_identity() {
        let help = daemon_help_text();
        assert!(help.contains("steelsearch development daemon"));
        assert!(help.contains("--extensions.manifest"));
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
            pending: vec![os_node::ClusterManagerTaskRecord {
                task_id: 1,
                task: os_node::ClusterManagerTask {
                    source: "reroute".to_string(),
                    kind: os_node::ClusterManagerTaskKind::Reroute,
                },
                state: os_node::ClusterManagerTaskState::Queued,
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
                votes: Default::default(),
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
            .contains("leader lost live follower quorum"));
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
            pending: vec![os_node::ClusterManagerTaskRecord {
                task_id: 1,
                task: os_node::ClusterManagerTask {
                    source: "reroute".to_string(),
                    kind: os_node::ClusterManagerTaskKind::Reroute,
                },
                state: os_node::ClusterManagerTaskState::Queued,
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
            pending: vec![os_node::ClusterManagerTaskRecord {
                task_id: 1,
                task: os_node::ClusterManagerTask {
                    source: "reroute".to_string(),
                    kind: os_node::ClusterManagerTaskKind::Reroute,
                },
                state: os_node::ClusterManagerTaskState::Queued,
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

        let get = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Get,
            "/_tasks/node-a:1",
        ));
        assert_eq!(get.status, 200);
        assert!(get.body["task"].get("action").is_some());
        assert!(get.body["task"].get("cancellable").is_some());

        let cancel = node.handle_rest_request(os_rest::RestRequest::new(
            os_rest::RestMethod::Post,
            "/_tasks/_cancel?task_id=node-a:999",
        ));
        assert_eq!(cancel.status, 200);
        assert!(cancel.body["nodes"].is_object());
        assert!(cancel.body["node_failures"].is_array());
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
                            "dimension": 3
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
        assert_eq!(knn.body["hits"]["total"]["value"], 1);
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
