use os_engine::{shard_manifest_checksum, ShardManifest, SHARD_MANIFEST_FILE_NAME};
use os_node::{
    load_gateway_state_manifest, persist_gateway_state_manifest, ClusterManagerTask,
    ClusterManagerTaskKind, ClusterManagerTaskRecord, ClusterManagerTaskState,
    PersistedClusterManagerTaskQueueState,
};
use serde_json::Value;
use std::collections::BTreeSet;
use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, ExitStatus, Stdio};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

struct ChildGuard {
    children: Vec<Child>,
}

impl Drop for ChildGuard {
    fn drop(&mut self) {
        for child in &mut self.children {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

#[test]
fn three_local_daemons_form_development_cluster_and_handle_index_smoke() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(&root).unwrap();
    let http_ports = [free_port(), free_port(), free_port()];
    let transport_ports = [free_port(), free_port(), free_port()];
    let seed_hosts = transport_ports
        .iter()
        .map(|port| format!("127.0.0.1:{port}"))
        .collect::<Vec<_>>()
        .join(",");
    let mut children = Vec::new();

    for index in 0..3 {
        let node_dir = root.join(format!("node-{}", index + 1));
        fs::create_dir_all(node_dir.join("data")).unwrap();
        fs::create_dir_all(node_dir.join("logs")).unwrap();
        let stdout = fs::File::create(node_dir.join("logs/stdout.log")).unwrap();
        let stderr = fs::File::create(node_dir.join("logs/stderr.log")).unwrap();
        children.push(
            Command::new(&binary)
                .arg("--http.host")
                .arg("127.0.0.1")
                .arg("--http.port")
                .arg(http_ports[index].to_string())
                .arg("--transport.host")
                .arg("127.0.0.1")
                .arg("--transport.port")
                .arg(transport_ports[index].to_string())
                .arg("--node.id")
                .arg(format!("steel-node-{}", index + 1))
                .arg("--node.name")
                .arg(format!("steel-node-{}", index + 1))
                .arg("--cluster.name")
                .arg("steel-dev-it")
                .arg("--node.roles")
                .arg("cluster_manager,data,ingest")
                .arg("--discovery.seed_hosts")
                .arg(&seed_hosts)
                .arg("--path.data")
                .arg(node_dir.join("data"))
                .stdout(Stdio::from(stdout))
                .stderr(Stdio::from(stderr))
                .spawn()
                .unwrap(),
        );
    }
    let _guard = ChildGuard { children };

    let expected_transport_addresses = transport_ports
        .iter()
        .map(|port| format!("127.0.0.1:{port}"))
        .collect::<BTreeSet<_>>();
    let mut observed_cluster_uuids = BTreeSet::new();
    let mut observed_state_uuids = BTreeSet::new();

    for (index, port) in http_ports.iter().copied().enumerate() {
        let cluster = wait_json(port, "GET", "/_steelsearch/dev/cluster", None);
        assert_eq!(cluster["cluster_name"], "steel-dev-it");
        assert_eq!(cluster["number_of_nodes"], 3);
        assert_eq!(cluster["formed"], true);
        assert_eq!(
            cluster["local_node_id"],
            format!("steel-node-{}", index + 1)
        );
        assert_eq!(
            cluster["coordination"]["elected_node_id"],
            format!("steel-node-{}", index + 1)
        );
        assert_eq!(cluster["coordination"]["term"], 1);
        assert_eq!(cluster["coordination"]["publication_committed"], true);
        assert_eq!(cluster["coordination"]["applied"], true);
        assert!(
            cluster["coordination"]["required_quorum"]
                .as_u64()
                .unwrap_or_default()
                >= 1
        );
        assert!(
            cluster["coordination"]["last_accepted_version"]
                .as_i64()
                .unwrap_or_default()
                >= 1
        );
        assert!(cluster["coordination"]["last_accepted_state_uuid"]
            .as_str()
            .unwrap_or_default()
            .starts_with("steelsearch-dev-cluster-uuid-dev-state-"));
        assert!(!cluster["coordination"]["votes"].as_array().unwrap().is_empty());
        assert!(!cluster["coordination"]["acked_nodes"]
            .as_array()
            .unwrap()
            .is_empty());
        assert!(cluster["coordination"]["missing_nodes"]
            .as_array()
            .unwrap()
            .is_empty());

        observed_cluster_uuids.insert(cluster["cluster_uuid"].as_str().unwrap().to_string());
        observed_state_uuids.insert(
            cluster["coordination"]["last_accepted_state_uuid"]
                .as_str()
                .unwrap()
                .to_string(),
        );
        let transport_addresses = cluster["nodes"]
            .as_array()
            .unwrap()
            .iter()
            .map(|node| node["transport_address"].as_str().unwrap().to_string())
            .collect::<BTreeSet<_>>();
        assert_eq!(transport_addresses, expected_transport_addresses);
    }
    assert_eq!(
        observed_cluster_uuids,
        BTreeSet::from(["steelsearch-dev-cluster-uuid".to_string()])
    );
    assert!(observed_state_uuids
        .iter()
        .all(|state_uuid| state_uuid.starts_with("steelsearch-dev-cluster-uuid-dev-state-")));

    for (index, port) in http_ports.iter().copied().enumerate() {
        let create = http_json(
            port,
            "PUT",
            "/logs-it",
            Some(
                br#"{
                    "settings": { "index": { "number_of_shards": 1, "number_of_replicas": 1 } },
                    "mappings": { "properties": { "message": { "type": "text" } } }
                }"#,
            ),
        );
        assert_eq!(create["status"], 200);

        let get_index = http_json(port, "GET", "/logs-it", None);
        assert_eq!(get_index["status"], 200);
        assert_eq!(
            get_index["body"]["logs-it"]["settings"]["index"]["number_of_replicas"],
            1
        );
        assert_eq!(
            get_index["body"]["logs-it"]["mappings"]["properties"]["message"]["type"],
            "text"
        );

        let health = wait_json(port, "GET", "/_cluster/health", None);
        assert_eq!(health["status"], "yellow");
        assert_eq!(health["active_primary_shards"], 1);
        assert_eq!(health["active_shards"], 1);
        assert_eq!(health["unassigned_shards"], 1);

        let state = http_json(port, "GET", "/_cluster/state", None);
        assert_eq!(state["status"], 200);
        assert_eq!(
            state["body"]["metadata"]["indices"]["logs-it"]["settings"]["index"]
                ["number_of_replicas"],
            "1"
        );

        let primary_allocation = http_json(
            port,
            "GET",
            "/_cluster/allocation/explain",
            Some(br#"{"index":"logs-it","shard":0,"primary":true}"#),
        );
        assert_eq!(primary_allocation["status"], 200);
        assert_eq!(primary_allocation["body"]["current_state"], "started");
        assert_eq!(primary_allocation["body"]["primary"], true);
        assert_eq!(
            primary_allocation["body"]["current_node"]["id"],
            format!("steel-node-{}", index + 1)
        );

        let replica_allocation = http_json(
            port,
            "GET",
            "/_cluster/allocation/explain",
            Some(br#"{"index":"logs-it","shard":0,"primary":false}"#),
        );
        assert_eq!(replica_allocation["status"], 200);
        assert_eq!(replica_allocation["body"]["current_state"], "unassigned");
        assert_eq!(replica_allocation["body"]["primary"], false);
        assert_eq!(replica_allocation["body"]["can_allocate"], "yes");

        let manifest: Value = serde_json::from_slice(
            &fs::read(
                root.join(format!(
                    "node-{}/data/gateway-cluster-state.json",
                    index + 1
                )),
            )
            .unwrap(),
        )
        .unwrap();
        assert_eq!(manifest["indices"]["logs-it"]["state"], "open");
        assert_eq!(
            manifest["routing_table"]["indices"]["logs-it"]["shards"]["0"][0]["state"],
            "STARTED"
        );
        assert_eq!(
            manifest["routing_table"]["indices"]["logs-it"]["shards"]["0"][1]["state"],
            "UNASSIGNED"
        );
        let node_id = format!("steel-node-{}", index + 1);
        assert_eq!(
            manifest["allocation"]["nodes"][node_id.as_str()]["assigned_shards"],
            1
        );

        let message = format!("hello from daemon integration node {}", index + 1);
        let index_doc = http_json(
            port,
            "PUT",
            &format!("/logs-it/_doc/{}", index + 1),
            Some(format!(r#"{{ "message": "{message}" }}"#).as_bytes()),
        );
        assert_eq!(index_doc["status"], 201);
        let refresh = http_json(port, "POST", "/logs-it/_refresh", Some(b"{}"));
        assert_eq!(refresh["status"], 200);
        let search = http_json(
            port,
            "POST",
            "/logs-it/_search",
            Some(br#"{ "query": { "match": { "message": "hello" } } }"#),
        );
        assert_eq!(search["status"], 200);
        assert_eq!(search["body"]["hits"]["total"]["value"], 1);
    }

    let _ = fs::remove_dir_all(root);
}

#[test]
fn three_local_daemons_restart_node_with_persisted_coordination_and_task_queue_state() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(&root).unwrap();
    let http_ports = [free_port(), free_port(), free_port()];
    let transport_ports = [free_port(), free_port(), free_port()];
    let seed_hosts = transport_ports
        .iter()
        .map(|port| format!("127.0.0.1:{port}"))
        .collect::<Vec<_>>()
        .join(",");
    let mut children = Vec::new();

    for index in 0..3 {
        let node_dir = root.join(format!("node-{}", index + 1));
        fs::create_dir_all(node_dir.join("data")).unwrap();
        fs::create_dir_all(node_dir.join("logs")).unwrap();
        let stdout = fs::File::create(node_dir.join("logs/stdout.log")).unwrap();
        let stderr = fs::File::create(node_dir.join("logs/stderr.log")).unwrap();
        children.push(
            Command::new(&binary)
                .arg("--http.host")
                .arg("127.0.0.1")
                .arg("--http.port")
                .arg(http_ports[index].to_string())
                .arg("--transport.host")
                .arg("127.0.0.1")
                .arg("--transport.port")
                .arg(transport_ports[index].to_string())
                .arg("--node.id")
                .arg(format!("steel-node-{}", index + 1))
                .arg("--node.name")
                .arg(format!("steel-node-{}", index + 1))
                .arg("--cluster.name")
                .arg("steel-dev-restart-it")
                .arg("--node.roles")
                .arg("cluster_manager,data,ingest")
                .arg("--discovery.seed_hosts")
                .arg(&seed_hosts)
                .arg("--path.data")
                .arg(node_dir.join("data"))
                .stdout(Stdio::from(stdout))
                .stderr(Stdio::from(stderr))
                .spawn()
                .unwrap(),
        );
    }
    let mut guard = ChildGuard { children };

    for port in http_ports {
        let cluster = wait_json(port, "GET", "/_steelsearch/dev/cluster", None);
        assert_eq!(cluster["cluster_name"], "steel-dev-restart-it");
        assert_eq!(cluster["number_of_nodes"], 3);
        assert_eq!(cluster["formed"], true);
        assert_eq!(cluster["coordination"]["publication_committed"], true);
        assert!(!cluster["coordination"]["votes"].as_array().unwrap().is_empty());
    }

    let restarted_index = 1;
    let restarted_node_data = root.join(format!("node-{}/data", restarted_index + 1));
    let gateway_path = restarted_node_data.join("gateway-state.json");
    let gateway_state_before = load_gateway_state_manifest(&gateway_path)
        .unwrap()
        .expect("gateway state before restart");
    assert_eq!(gateway_state_before.cluster_state.cluster_name, "steel-dev-restart-it");
    assert_eq!(
        gateway_state_before
            .coordination_state
            .last_completed_publication_round
            .as_ref()
            .map(|round| round.version),
        Some(1)
    );

    terminate_child(&guard.children[restarted_index]);
    let exited = wait_for_child_exit(&mut guard.children[restarted_index]);
    assert!(exited.success(), "daemon did not exit cleanly: {exited}");

    let injected_task_queue_state = PersistedClusterManagerTaskQueueState {
        next_task_id: 3,
        pending: vec![ClusterManagerTaskRecord {
            task_id: 1,
            task: ClusterManagerTask {
                source: "restart-replay".to_string(),
                kind: ClusterManagerTaskKind::Reroute,
            },
            state: ClusterManagerTaskState::Queued,
            failure_reason: None,
        }],
        in_flight: vec![ClusterManagerTaskRecord {
            task_id: 2,
            task: ClusterManagerTask {
                source: "restart-replay".to_string(),
                kind: ClusterManagerTaskKind::RemoveNode {
                    node_id: "steel-node-3".to_string(),
                },
            },
            state: ClusterManagerTaskState::InFlight,
            failure_reason: None,
        }],
        acknowledged: Vec::new(),
        failed: Vec::new(),
    };
    let mut injected_gateway_state = gateway_state_before.clone();
    injected_gateway_state.task_queue_state = Some(injected_task_queue_state.clone());
    persist_gateway_state_manifest(&gateway_path, &injected_gateway_state).unwrap();

    let restart_stdout = fs::File::create(
        root.join(format!("node-{}/logs/restart-stdout.log", restarted_index + 1)),
    )
    .unwrap();
    let restart_stderr = fs::File::create(
        root.join(format!("node-{}/logs/restart-stderr.log", restarted_index + 1)),
    )
    .unwrap();
    let restarted = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg(http_ports[restarted_index].to_string())
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(transport_ports[restarted_index].to_string())
        .arg("--node.id")
        .arg(format!("steel-node-{}", restarted_index + 1))
        .arg("--node.name")
        .arg(format!("steel-node-{}", restarted_index + 1))
        .arg("--cluster.name")
        .arg("steel-dev-restart-it")
        .arg("--node.roles")
        .arg("cluster_manager,data,ingest")
        .arg("--discovery.seed_hosts")
        .arg(&seed_hosts)
        .arg("--path.data")
        .arg(&restarted_node_data)
        .stdout(Stdio::from(restart_stdout))
        .stderr(Stdio::from(restart_stderr))
        .spawn()
        .unwrap();

    let restarted_cluster =
        wait_json(http_ports[restarted_index], "GET", "/_steelsearch/dev/cluster", None);
    assert_eq!(restarted_cluster["cluster_name"], "steel-dev-restart-it");
    assert_eq!(restarted_cluster["number_of_nodes"], 3);
    assert_eq!(restarted_cluster["formed"], true);
    assert_eq!(
        restarted_cluster["local_node_id"],
        format!("steel-node-{}", restarted_index + 1)
    );
    assert_eq!(restarted_cluster["coordination"]["publication_committed"], true);
    assert!(!restarted_cluster["coordination"]["votes"]
        .as_array()
        .unwrap()
        .is_empty());
    assert!(
        restarted_cluster["coordination"]["last_accepted_version"]
            .as_i64()
            .unwrap_or_default()
            >= gateway_state_before.coordination_state.last_accepted_version
    );
    assert!(restarted_cluster["coordination"]["last_accepted_state_uuid"]
        .as_str()
        .unwrap_or_default()
        .starts_with("steelsearch-dev-cluster-uuid-dev-state-"));

    let gateway_state_after = load_gateway_state_manifest(&gateway_path)
        .unwrap()
        .expect("gateway state after restart");
    assert!(
        gateway_state_after.coordination_state.last_accepted_version
            >= gateway_state_before.coordination_state.last_accepted_version
    );
    assert!(
        gateway_state_after
            .coordination_state
            .last_completed_publication_round
            .as_ref()
            .map(|round| round.version)
            .unwrap_or_default()
            >= gateway_state_before
                .coordination_state
                .last_completed_publication_round
                .as_ref()
                .map(|round| round.version)
                .unwrap_or_default()
    );
    assert_eq!(
        gateway_state_after.task_queue_state,
        Some(injected_task_queue_state)
    );

    guard.children[restarted_index] = restarted;
    let _ = fs::remove_dir_all(root);
}

#[test]
fn three_local_daemons_restart_node_and_replay_gateway_coordination_state() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(&root).unwrap();
    let http_ports = [free_port(), free_port(), free_port()];
    let transport_ports = [free_port(), free_port(), free_port()];
    let seed_hosts = transport_ports
        .iter()
        .map(|port| format!("127.0.0.1:{port}"))
        .collect::<Vec<_>>()
        .join(",");
    let mut children = Vec::new();

    for index in 0..3 {
        let node_dir = root.join(format!("node-{}", index + 1));
        fs::create_dir_all(node_dir.join("data")).unwrap();
        fs::create_dir_all(node_dir.join("logs")).unwrap();
        let stdout = fs::File::create(node_dir.join("logs/stdout.log")).unwrap();
        let stderr = fs::File::create(node_dir.join("logs/stderr.log")).unwrap();
        children.push(
            Command::new(&binary)
                .arg("--http.host")
                .arg("127.0.0.1")
                .arg("--http.port")
                .arg(http_ports[index].to_string())
                .arg("--transport.host")
                .arg("127.0.0.1")
                .arg("--transport.port")
                .arg(transport_ports[index].to_string())
                .arg("--node.id")
                .arg(format!("steel-node-{}", index + 1))
                .arg("--node.name")
                .arg(format!("steel-node-{}", index + 1))
                .arg("--cluster.name")
                .arg("steel-dev-it-restart")
                .arg("--node.roles")
                .arg("cluster_manager,data,ingest")
                .arg("--discovery.seed_hosts")
                .arg(&seed_hosts)
                .arg("--path.data")
                .arg(node_dir.join("data"))
                .stdout(Stdio::from(stdout))
                .stderr(Stdio::from(stderr))
                .spawn()
                .unwrap(),
        );
    }
    let mut guard = ChildGuard { children };

    for port in http_ports {
        let cluster = wait_json(port, "GET", "/_steelsearch/dev/cluster", None);
        assert_eq!(cluster["cluster_name"], "steel-dev-it-restart");
        assert_eq!(cluster["number_of_nodes"], 3);
        assert_eq!(cluster["formed"], true);
        assert_eq!(cluster["coordination"]["publication_committed"], true);
    }

    let restarted_index = 1usize;
    let node_dir = root.join(format!("node-{}", restarted_index + 1));
    let gateway_path = node_dir.join("data/gateway-state.json");

    let mut restarted_child = guard.children.remove(restarted_index);
    terminate_child(&restarted_child);
    let status = wait_for_child_exit(&mut restarted_child);
    assert!(status.success(), "restarted daemon did not exit cleanly: {status}");

    let mut persisted = load_gateway_state_manifest(&gateway_path)
        .unwrap()
        .expect("gateway manifest should exist after initial cluster formation");
    persisted.task_queue_state = Some(PersistedClusterManagerTaskQueueState {
        next_task_id: 1,
        pending: vec![ClusterManagerTaskRecord {
            task_id: 0,
            task: ClusterManagerTask {
                source: "restart-replay".to_string(),
                kind: ClusterManagerTaskKind::Reroute,
            },
            state: ClusterManagerTaskState::Queued,
            failure_reason: None,
        }],
        in_flight: Vec::new(),
        acknowledged: Vec::new(),
        failed: Vec::new(),
    });
    persist_gateway_state_manifest(&gateway_path, &persisted).unwrap();

    let stdout = fs::File::create(node_dir.join("logs/restart-stdout.log")).unwrap();
    let stderr = fs::File::create(node_dir.join("logs/restart-stderr.log")).unwrap();
    let restarted = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg(http_ports[restarted_index].to_string())
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(transport_ports[restarted_index].to_string())
        .arg("--node.id")
        .arg(format!("steel-node-{}", restarted_index + 1))
        .arg("--node.name")
        .arg(format!("steel-node-{}", restarted_index + 1))
        .arg("--cluster.name")
        .arg("steel-dev-it-restart")
        .arg("--node.roles")
        .arg("cluster_manager,data,ingest")
        .arg("--discovery.seed_hosts")
        .arg(&seed_hosts)
        .arg("--path.data")
        .arg(node_dir.join("data"))
        .stdout(Stdio::from(stdout))
        .stderr(Stdio::from(stderr))
        .spawn()
        .unwrap();
    guard.children.insert(restarted_index, restarted);

    let cluster = wait_json(
        http_ports[restarted_index],
        "GET",
        "/_steelsearch/dev/cluster",
        None,
    );
    assert_eq!(cluster["cluster_name"], "steel-dev-it-restart");
    assert_eq!(cluster["number_of_nodes"], 3);
    assert_eq!(cluster["formed"], true);
    assert_eq!(cluster["coordination"]["publication_committed"], true);
    assert!(
        cluster["coordination"]["required_quorum"]
            .as_u64()
            .expect("required_quorum should be present")
            >= 1
    );
    assert_eq!(
        cluster["cluster_uuid"].as_str(),
        Some("steelsearch-dev-cluster-uuid")
    );

    let reloaded = load_gateway_state_manifest(&gateway_path)
        .unwrap()
        .expect("gateway manifest should survive restart replay");
    let task_queue = reloaded
        .task_queue_state
        .expect("persisted queued task should survive restart replay");
    assert_eq!(task_queue.pending.len(), 1);
    assert_eq!(task_queue.pending[0].task.source, "restart-replay");
    assert!(matches!(
        task_queue.pending[0].task.kind,
        ClusterManagerTaskKind::Reroute
    ));

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_rejects_occupied_http_port() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();
    let occupied = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = occupied.local_addr().unwrap().port();

    let output = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg(port.to_string())
        .arg("--path.data")
        .arg(root.join("data"))
        .output()
        .unwrap();

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("Address already in use")
            || stderr.contains("address already in use")
            || stderr.contains("os error 98"),
        "unexpected stderr: {stderr}"
    );
    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_rejects_data_path_that_is_not_a_directory() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(&root).unwrap();
    let data_path = root.join("data-file");
    fs::write(&data_path, b"not a directory").unwrap();

    let output = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg(free_port().to_string())
        .arg("--path.data")
        .arg(&data_path)
        .output()
        .unwrap();

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("File exists")
            || stderr.contains("file exists")
            || stderr.contains("AlreadyExists")
            || stderr.contains("Not a directory")
            || stderr.contains("--path.data must be a directory"),
        "unexpected stderr: {stderr}"
    );
    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_exits_when_http_port_is_occupied() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();
    let occupied = TcpListener::bind("127.0.0.1:0").unwrap();
    let occupied_port = occupied.local_addr().unwrap().port();

    let output = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg(occupied_port.to_string())
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--path.data")
        .arg(root.join("data"))
        .output()
        .unwrap();

    drop(occupied);
    let _ = fs::remove_dir_all(root);

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("Address already in use") || stderr.contains("address already in use"),
        "stderr did not report occupied port: {stderr}"
    );
}

#[test]
fn daemon_started_on_port_zero_reports_selected_http_port() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let selected_port = read_reported_http_port(&mut reader);
    assert_ne!(selected_port, 0);

    let _guard = ChildGuard {
        children: vec![child],
    };
    let health = wait_json(selected_port, "GET", "/_cluster/health", None);
    assert_eq!(health["status"], "green");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_smoke_tests_core_rest_endpoints_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-smoke")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let info = wait_http_response(port, "GET", "/", None);
    assert_eq!(info["status"], 200);
    assert_eq!(info["body"]["cluster_name"], "steel-dev-smoke");
    assert_eq!(
        info["body"]["tagline"],
        "The OpenSearch Project: https://opensearch.org/"
    );

    let ping = http_response(port, "HEAD", "/", None);
    assert_eq!(ping["status"], 200);
    assert_eq!(ping["body_text"], "");

    let health = http_response(port, "GET", "/_cluster/health", None);
    assert_eq!(health["status"], 200);
    assert_eq!(health["body"]["cluster_name"], "steel-dev-smoke");
    assert_eq!(health["body"]["status"], "green");

    let state = http_response(port, "GET", "/_cluster/state", None);
    assert_eq!(state["status"], 200);
    assert_eq!(state["body"]["cluster_name"], "steel-dev-smoke");
    assert_eq!(state["body"]["nodes"].as_object().unwrap().len(), 1);

    let stats = http_response(port, "GET", "/_nodes/stats", None);
    assert_eq!(stats["status"], 200);
    assert_eq!(stats["body"]["nodes"].as_object().unwrap().len(), 1);

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_put_index_accepts_settings_and_mapping_variants_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-create-index")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };
    assert_eq!(
        wait_json(port, "GET", "/_cluster/health", None)["status"],
        "green"
    );

    let empty = http_response(port, "PUT", "/empty-index", None);
    assert_eq!(empty["status"], 200);
    assert_eq!(empty["body"]["acknowledged"], true);
    assert_eq!(empty["body"]["shards_acknowledged"], true);
    assert_eq!(empty["body"]["index"], "empty-index");
    let empty_get = http_response(port, "GET", "/empty-index", None);
    assert_eq!(empty_get["status"], 200);
    assert_eq!(
        empty_get["body"]["empty-index"]["mappings"],
        serde_json::json!({})
    );
    assert_eq!(
        empty_get["body"]["empty-index"]["settings"]["index"]["number_of_shards"],
        "1"
    );
    assert_eq!(
        empty_get["body"]["empty-index"]["settings"]["index"]["number_of_replicas"],
        "1"
    );

    let explicit_settings = http_response(
        port,
        "PUT",
        "/settings-index",
        Some(
            br#"{
                "settings": { "index": { "number_of_shards": 2, "number_of_replicas": 0 } }
            }"#,
        ),
    );
    assert_eq!(explicit_settings["status"], 200);
    let settings_get = http_response(port, "GET", "/settings-index", None);
    assert_eq!(
        settings_get["body"]["settings-index"]["settings"]["index"]["number_of_shards"],
        2
    );
    assert_eq!(
        settings_get["body"]["settings-index"]["settings"]["index"]["number_of_replicas"],
        0
    );

    let text_keyword = http_response(
        port,
        "PUT",
        "/text-keyword-index",
        Some(
            br#"{
                "mappings": {
                    "properties": {
                        "title": { "type": "text" },
                        "status": { "type": "keyword" }
                    }
                }
            }"#,
        ),
    );
    assert_eq!(text_keyword["status"], 200);
    let text_keyword_get = http_response(port, "GET", "/text-keyword-index", None);
    assert_eq!(
        text_keyword_get["body"]["text-keyword-index"]["mappings"]["properties"]["title"]["type"],
        "text"
    );
    assert_eq!(
        text_keyword_get["body"]["text-keyword-index"]["mappings"]["properties"]["status"]["type"],
        "keyword"
    );

    let numeric_date = http_response(
        port,
        "PUT",
        "/numeric-date-index",
        Some(
            br#"{
                "mappings": {
                    "properties": {
                        "price": { "type": "double" },
                        "quantity": { "type": "integer" },
                        "created_at": { "type": "date" }
                    }
                }
            }"#,
        ),
    );
    assert_eq!(numeric_date["status"], 200);
    let numeric_date_get = http_response(port, "GET", "/numeric-date-index", None);
    assert_eq!(
        numeric_date_get["body"]["numeric-date-index"]["mappings"]["properties"]["price"]["type"],
        "double"
    );
    assert_eq!(
        numeric_date_get["body"]["numeric-date-index"]["mappings"]["properties"]["quantity"]
            ["type"],
        "integer"
    );
    assert_eq!(
        numeric_date_get["body"]["numeric-date-index"]["mappings"]["properties"]["created_at"]
            ["type"],
        "date"
    );

    let knn_vector = http_response(
        port,
        "PUT",
        "/vector-index",
        Some(
            br#"{
                "settings": { "index": { "knn": true, "number_of_shards": 1, "number_of_replicas": 0 } },
                "mappings": {
                    "properties": {
                        "tenant": { "type": "keyword" },
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 3,
                            "method": { "name": "hnsw", "engine": "lucene", "space_type": "l2" }
                        }
                    }
                }
            }"#,
        ),
    );
    assert_eq!(knn_vector["status"], 200);
    let vector_get = http_response(port, "GET", "/vector-index", None);
    assert_eq!(
        vector_get["body"]["vector-index"]["mappings"]["properties"]["embedding"]["type"],
        "knn_vector"
    );
    assert_eq!(
        vector_get["body"]["vector-index"]["mappings"]["properties"]["embedding"]["dimension"],
        3
    );
    assert_eq!(
        vector_get["body"]["vector-index"]["mappings"]["properties"]["embedding"]["method"]["name"],
        "hnsw"
    );

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_put_index_accepts_empty_settings_and_field_mapping_shapes() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-index-api")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let empty = wait_http_response(port, "PUT", "/empty-it", None);
    assert_eq!(empty["status"], 200);
    assert_eq!(empty["body"]["acknowledged"], true);
    let empty_index = http_response(port, "GET", "/empty-it", None);
    assert_eq!(empty_index["status"], 200);
    assert_eq!(
        empty_index["body"]["empty-it"]["mappings"],
        serde_json::json!({})
    );
    assert_eq!(
        empty_index["body"]["empty-it"]["settings"]["index"]["number_of_shards"],
        "1"
    );

    let settings = http_response(
        port,
        "PUT",
        "/settings-it",
        Some(br#"{"settings":{"index":{"number_of_shards":1,"number_of_replicas":0}}}"#),
    );
    assert_eq!(settings["status"], 200);
    let settings_index = http_response(port, "GET", "/settings-it", None);
    assert_eq!(
        settings_index["body"]["settings-it"]["settings"]["index"]["number_of_shards"],
        1
    );
    assert_eq!(
        settings_index["body"]["settings-it"]["settings"]["index"]["number_of_replicas"],
        0
    );

    let keyword_text = http_response(
        port,
        "PUT",
        "/keyword-text-it",
        Some(
            br#"{"mappings":{"properties":{"message":{"type":"text"},"service":{"type":"keyword"}}}}"#,
        ),
    );
    assert_eq!(keyword_text["status"], 200);
    let keyword_text_index = http_response(port, "GET", "/keyword-text-it", None);
    assert_eq!(
        keyword_text_index["body"]["keyword-text-it"]["mappings"]["properties"]["message"]["type"],
        "text"
    );
    assert_eq!(
        keyword_text_index["body"]["keyword-text-it"]["mappings"]["properties"]["service"]["type"],
        "keyword"
    );

    let numeric_date = http_response(
        port,
        "PUT",
        "/numeric-date-it",
        Some(
            br#"{"mappings":{"properties":{"bytes":{"type":"long"},"latency":{"type":"float"},"created_at":{"type":"date"}}}}"#,
        ),
    );
    assert_eq!(numeric_date["status"], 200);
    let numeric_date_index = http_response(port, "GET", "/numeric-date-it", None);
    assert_eq!(
        numeric_date_index["body"]["numeric-date-it"]["mappings"]["properties"]["bytes"]["type"],
        "long"
    );
    assert_eq!(
        numeric_date_index["body"]["numeric-date-it"]["mappings"]["properties"]["latency"]["type"],
        "float"
    );
    assert_eq!(
        numeric_date_index["body"]["numeric-date-it"]["mappings"]["properties"]["created_at"]
            ["type"],
        "date"
    );

    let knn_vector = http_response(
        port,
        "PUT",
        "/knn-vector-it",
        Some(
            br#"{"settings":{"index":{"knn":true}},"mappings":{"properties":{"embedding":{"type":"knn_vector","dimension":3,"method":{"name":"hnsw","engine":"lucene","space_type":"l2"}}}}}"#,
        ),
    );
    assert_eq!(knn_vector["status"], 200);
    let knn_vector_index = http_response(port, "GET", "/knn-vector-it", None);
    let embedding =
        &knn_vector_index["body"]["knn-vector-it"]["mappings"]["properties"]["embedding"];
    assert_eq!(embedding["type"], "knn_vector");
    assert_eq!(embedding["dimension"], 3);
    assert_eq!(embedding["method"]["name"], "hnsw");
    assert_eq!(embedding["method"]["engine"], "lucene");
    assert_eq!(embedding["method"]["space_type"], "l2");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_knn_vector_mapping_survives_get_and_search_execution_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-knn-vector-api")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let create = wait_http_response(
        port,
        "PUT",
        "/knn-http-it",
        Some(
            br#"{"settings":{"index":{"knn":true}},"mappings":{"properties":{"tenant":{"type":"keyword"},"embedding":{"type":"knn_vector","dimension":3,"method":{"name":"hnsw","engine":"lucene","space_type":"l2"}}}}}"#,
        ),
    );
    assert_eq!(create["status"], 200);

    let mapping = http_response(port, "GET", "/knn-http-it", None);
    let embedding = &mapping["body"]["knn-http-it"]["mappings"]["properties"]["embedding"];
    assert_eq!(embedding["type"], "knn_vector");
    assert_eq!(embedding["dimension"], 3);
    assert_eq!(embedding["method"]["name"], "hnsw");
    assert_eq!(embedding["method"]["engine"], "lucene");
    assert_eq!(embedding["method"]["space_type"], "l2");

    for (id, source) in [
        (
            "a",
            br#"{"tenant":"one","embedding":[1.0,0.0,0.0],"title":"alpha"}"#.as_slice(),
        ),
        (
            "b",
            br#"{"tenant":"one","embedding":[0.8,0.2,0.0],"title":"beta"}"#.as_slice(),
        ),
        (
            "c",
            br#"{"tenant":"two","embedding":[0.0,1.0,0.0],"title":"gamma"}"#.as_slice(),
        ),
    ] {
        let response = http_response(
            port,
            "PUT",
            &format!("/knn-http-it/_doc/{id}"),
            Some(source),
        );
        assert_eq!(response["status"], 201);
    }
    assert_refresh_success(&http_response(
        port,
        "POST",
        "/knn-http-it/_refresh",
        Some(b"{}"),
    ));

    let search = http_response(
        port,
        "POST",
        "/knn-http-it/_search",
        Some(br#"{"query":{"knn":{"embedding":{"vector":[1.0,0.0,0.0],"k":2}}},"size":2}"#),
    );
    assert_eq!(search["status"], 200);
    assert_eq!(search["body"]["hits"]["total"]["value"], 2);
    let hits = search["body"]["hits"]["hits"].as_array().unwrap();
    assert_eq!(hits.len(), 2);
    assert_eq!(hits[0]["_id"], "a");
    assert_eq!(hits[0]["_source"]["title"], "alpha");
    assert_eq!(hits[1]["_id"], "b");
    assert_eq!(hits[1]["_source"]["title"], "beta");
    assert!(hits[0]["_score"].as_f64().unwrap() >= hits[1]["_score"].as_f64().unwrap());

    let option_search = http_response(
        port,
        "POST",
        "/knn-http-it/_search",
        Some(
            br#"{"query":{"knn":{"field":"embedding","vector":[1.0,0.0,0.0],"k":2,"filter":{"term":{"tenant":"one"}},"ignore_unmapped":false,"expand_nested":true,"min_score":-0.1,"max_distance":0.1,"method_parameters":{"ef_search":8},"rescore":{"oversample_factor":2.0}}},"size":2}"#,
        ),
    );
    assert_eq!(option_search["status"], 200);
    let option_hits = option_search["body"]["hits"]["hits"].as_array().unwrap();
    assert_eq!(option_hits.len(), 2);
    assert_eq!(option_hits[0]["_id"], "a");
    assert_eq!(option_hits[1]["_id"], "b");

    let nested_option_search = http_response(
        port,
        "POST",
        "/knn-http-it/_search",
        Some(
            br#"{"query":{"knn":{"field":"embedding","vector":[1.0,0.0,0.0],"k":2,"filter":{"term":{"tenant":"one"}},"expand_nested_docs":true,"method_parameters":{"ef_search":8}}},"size":2}"#,
        ),
    );
    assert_eq!(nested_option_search["status"], 200);
    let nested_option_hits = nested_option_search["body"]["hits"]["hits"]
        .as_array()
        .unwrap();
    assert_eq!(nested_option_hits.len(), 2);
    assert_eq!(nested_option_hits[0]["_id"], "a");
    assert_eq!(nested_option_hits[1]["_id"], "b");

    let hybrid_search = http_response(
        port,
        "POST",
        "/knn-http-it/_search",
        Some(
            br#"{"query":{"bool":{"must":[{"term":{"tenant":"one"}},{"knn":{"embedding":{"vector":[1.0,0.0,0.0],"k":2}}}]}},"size":2}"#,
        ),
    );
    assert_eq!(hybrid_search["status"], 200);
    let hybrid_hits = hybrid_search["body"]["hits"]["hits"].as_array().unwrap();
    assert_eq!(hybrid_hits.len(), 2);
    assert_eq!(hybrid_hits[0]["_id"], "a");
    assert_eq!(hybrid_hits[1]["_id"], "b");
    let hybrid_a_score = hybrid_hits[0]["_score"].as_f64().unwrap();
    let hybrid_b_score = hybrid_hits[1]["_score"].as_f64().unwrap();
    assert!((hybrid_a_score - 1.0).abs() < f64::EPSILON);
    assert!((hybrid_b_score - 0.92).abs() < 0.000001);
    assert!(hybrid_a_score > hybrid_b_score);

    let create_exact = http_response(
        port,
        "PUT",
        "/knn-exact-http-it",
        Some(
            br#"{"settings":{"index":{"knn":true}},"mappings":{"properties":{"tenant":{"type":"keyword"},"embedding":{"type":"knn_vector","dimension":3},"title":{"type":"text"}}}}"#,
        ),
    );
    assert_eq!(create_exact["status"], 200);

    for (id, source) in [
        (
            "a",
            br#"{"tenant":"one","embedding":[1.0,0.0,0.0],"title":"alpha"}"#.as_slice(),
        ),
        (
            "b",
            br#"{"tenant":"one","embedding":[0.8,0.2,0.0],"title":"beta"}"#.as_slice(),
        ),
        (
            "c",
            br#"{"tenant":"two","embedding":[0.0,1.0,0.0],"title":"gamma"}"#.as_slice(),
        ),
    ] {
        let response = http_response(
            port,
            "PUT",
            &format!("/knn-exact-http-it/_doc/{id}"),
            Some(source),
        );
        assert_eq!(response["status"], 201);
    }
    assert_refresh_success(&http_response(
        port,
        "POST",
        "/knn-exact-http-it/_refresh",
        Some(b"{}"),
    ));

    for index in ["knn-http-it", "knn-exact-http-it"] {
        assert_eq!(
            search_ids(
                port,
                "POST",
                &format!("/{index}/_search"),
                br#"{"query":{"knn":{"field":"embedding","vector":[1.0,0.0,0.0],"k":2,"filter":{"term":{"tenant":"one"}},"expand_nested_docs":true,"method_parameters":{"ef_search":8}}},"size":2}"#,
            ),
            vec!["a", "b"],
            "{index} filtered nested-option vector search"
        );
        assert_eq!(
            search_ids(
                port,
                "POST",
                &format!("/{index}/_search"),
                br#"{"query":{"bool":{"must":[{"term":{"tenant":"one"}},{"knn":{"embedding":{"vector":[1.0,0.0,0.0],"k":2}}}]}},"size":2}"#,
            ),
            vec!["a", "b"],
            "{index} hybrid vector search"
        );
    }

    let ignore_unmapped = http_response(
        port,
        "POST",
        "/knn-http-it/_search",
        Some(
            br#"{"query":{"knn":{"field":"missing_embedding","vector":[1.0,0.0,0.0],"k":2,"ignore_unmapped":true}}}"#,
        ),
    );
    assert_eq!(ignore_unmapped["status"], 200);
    assert_eq!(ignore_unmapped["body"]["hits"]["total"]["value"], 0);
    assert!(ignore_unmapped["body"]["hits"]["hits"]
        .as_array()
        .unwrap()
        .is_empty());

    let bad_data_type = http_response(
        port,
        "PUT",
        "/knn-bad-data-type-it",
        Some(
            br#"{"settings":{"index":{"knn":true}},"mappings":{"properties":{"embedding":{"type":"knn_vector","dimension":3,"data_type":"half_float"}}}}"#,
        ),
    );
    assert_opensearch_error_shape(&bad_data_type, 400, "illegal_argument_exception");

    for request in [
        br#"{"query":{"knn":{"embedding":{"vector":[1.0,0.0],"k":1}}}}"#.as_slice(),
        br#"{"query":{"knn":{"embedding":{"vector":"not-a-vector","k":1}}}}"#.as_slice(),
        br#"{"query":{"knn":{"embedding":{"vector":[1.0,"bad",0.0],"k":1}}}}"#.as_slice(),
        br#"{"query":{"knn":{"missing_embedding":{"vector":[1.0,0.0,0.0],"k":1}}}}"#.as_slice(),
        br#"{"query":{"knn":{"embedding":{"vector":[1.0,0.0,0.0]}}}}"#.as_slice(),
        br#"{"query":{"knn":{"embedding":{"k":1}}}}"#.as_slice(),
    ] {
        let response = http_response(port, "POST", "/knn-http-it/_search", Some(request));
        assert_opensearch_error_shape(&response, 400, "illegal_argument_exception");
    }

    let oversized_k = http_response(
        port,
        "POST",
        "/knn-http-it/_search",
        Some(br#"{"query":{"knn":{"embedding":{"vector":[1.0,0.0,0.0],"k":10}}},"size":10}"#),
    );
    assert_eq!(oversized_k["status"], 200);
    assert_eq!(oversized_k["body"]["hits"]["total"]["value"], 3);
    let oversized_hits = oversized_k["body"]["hits"]["hits"].as_array().unwrap();
    assert_eq!(oversized_hits.len(), 3);
    assert_eq!(oversized_hits[0]["_id"], "a");
    assert_eq!(oversized_hits[1]["_id"], "b");
    assert_eq!(oversized_hits[2]["_id"], "c");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_exposes_knn_plugin_routes_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-knn-plugin-api")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let warmup = wait_http_response(
        port,
        "POST",
        "/_plugins/_knn/warmup/vectors",
        Some(br#"{"vector_segment_count":2}"#),
    );
    assert_eq!(warmup["status"], 200);
    assert_eq!(warmup["body"]["index"], "vectors");
    assert_eq!(warmup["body"]["warmed"], true);
    assert_eq!(warmup["body"]["vector_segment_count"], 2);

    let stats = http_response(port, "GET", "/_plugins/_knn/stats", None);
    assert_eq!(stats["status"], 200);
    let local_stats = &stats["body"]["nodes"]["local"];
    assert_eq!(local_stats["graph_count"], 2);
    assert_eq!(local_stats["warmed_index_count"], 1);
    assert_eq!(local_stats["cache_entry_count"], 1);
    assert_eq!(local_stats["warmup_requests"], 1);
    assert_eq!(
        local_stats["operational_controls"]["config"]["native_memory_limit_bytes"],
        536_870_912
    );
    assert_eq!(
        local_stats["operational_controls"]["native_memory"]["used_bytes"],
        0
    );
    assert_eq!(
        local_stats["operational_controls"]["model_cache"]["used_bytes"],
        0
    );
    assert_eq!(
        local_stats["operational_controls"]["quantization_cache"]["used_bytes"],
        0
    );

    let cleared = http_response(
        port,
        "POST",
        "/_plugins/_knn/clear_cache",
        Some(br#"{"index":"vectors"}"#),
    );
    assert_eq!(cleared["status"], 200);
    assert_eq!(cleared["body"]["index"], "vectors");
    assert_eq!(cleared["body"]["cleared_entries"], 1);

    let train = http_response(
        port,
        "POST",
        "/_plugins/_knn/models/_train",
        Some(
            br#"{"model_id":"mini-lm-v1","dimension":3,"method":{"name":"hnsw","engine":"lucene","space_type":"l2"},"training_index":"training-vectors","training_field":"embedding","metadata":{"description":"MiniLM training fixture"}}"#,
        ),
    );
    assert_eq!(train["status"], 200);
    assert_eq!(train["body"]["model_id"], "mini-lm-v1");
    assert_eq!(train["body"]["state"], "trained");

    let duplicate = http_response(
        port,
        "POST",
        "/_plugins/_knn/models/_train",
        Some(
            br#"{"model_id":"mini-lm-v1","dimension":3,"method":{"name":"hnsw"},"training_index":"training-vectors","training_field":"embedding"}"#,
        ),
    );
    assert_opensearch_error_shape(&duplicate, 400, "resource_already_exists_exception");

    let model = http_response(port, "GET", "/_plugins/_knn/models/mini-lm-v1", None);
    assert_eq!(model["status"], 200);
    assert_eq!(model["body"]["model_id"], "mini-lm-v1");
    assert_eq!(model["body"]["training_index"], "training-vectors");

    let search = http_response(
        port,
        "POST",
        "/_plugins/_knn/models/_search",
        Some(br#"{"query":"mini","size":10}"#),
    );
    assert_eq!(search["status"], 200);
    assert_eq!(search["body"]["total"], 1);
    assert_eq!(search["body"]["models"][0]["model_id"], "mini-lm-v1");

    let trained_stats = http_response(port, "GET", "/_plugins/_knn/stats", None);
    let trained_local_stats = &trained_stats["body"]["nodes"]["local"];
    assert_eq!(trained_local_stats["model_count"], 1);
    assert_eq!(trained_local_stats["trained_model_count"], 1);
    assert_eq!(trained_local_stats["model_training_requests"], 1);
    assert_eq!(trained_local_stats["clear_cache_requests"], 1);
    assert_eq!(trained_local_stats["circuit_breaker_triggered"], false);

    let deleted = http_response(port, "DELETE", "/_plugins/_knn/models/mini-lm-v1", None);
    assert_eq!(deleted["status"], 200);
    assert_eq!(deleted["body"]["model_id"], "mini-lm-v1");

    let missing = http_response(port, "GET", "/_plugins/_knn/models/mini-lm-v1", None);
    assert_opensearch_error_shape(&missing, 404, "resource_not_found_exception");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_exposes_ml_model_lifecycle_routes_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-ml-model-api")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let mut port = read_reported_http_port(&mut reader);
    let mut guard = ChildGuard {
        children: vec![child],
    };

    let group = wait_http_response(
        port,
        "POST",
        "/_plugins/_ml/model_groups/_register",
        Some(
            br#"{"group_id":"group-1","name":"embeddings","access":{"owner":"steelsearch-dev","backend_roles":["ml-admin"],"tenant":"development","is_public":false}}"#,
        ),
    );
    assert_eq!(group["status"], 200);
    assert_eq!(group["body"]["group_id"], "group-1");
    assert_eq!(group["body"]["access"]["owner"], "steelsearch-dev");
    assert_eq!(group["body"]["access"]["backend_roles"][0], "ml-admin");
    assert_eq!(group["body"]["access"]["tenant"], "development");
    assert_eq!(group["body"]["access"]["is_public"], false);

    let register = http_response(
        port,
        "POST",
        "/_plugins/_ml/models/_register",
        Some(
            br#"{"model_id":"minilm-onnx","group_id":"group-1","name":"all-MiniLM-L6-v2","version":"1","format":"onnx","inference":{"kind":"text_embedding","embedding_dimension":8,"max_sequence_length":16,"normalize":true,"pooling":"mean"}}"#,
        ),
    );
    assert_eq!(register["status"], 200);
    assert_eq!(register["body"]["model"]["model_id"], "minilm-onnx");
    assert_eq!(register["body"]["model"]["state"], "registered");
    assert_eq!(
        register["body"]["model"]["access"]["owner"],
        "steelsearch-dev"
    );
    assert_eq!(register["body"]["task"]["kind"], "register_model");
    assert_eq!(register["body"]["task"]["state"], "completed");
    let register_task_id = register["body"]["task"]["task_id"].as_str().unwrap();

    let register_task = http_response(
        port,
        "GET",
        &format!("/_plugins/_ml/tasks/{register_task_id}"),
        None,
    );
    assert_eq!(register_task["status"], 200);
    assert_eq!(register_task["body"]["kind"], "register_model");
    assert_eq!(register_task["body"]["state"], "completed");

    let predict_before_deploy = http_response(
        port,
        "POST",
        "/_plugins/_ml/models/minilm-onnx/_predict",
        Some(br#"{"model_id":"minilm-onnx","texts":["steelsearch vector search"]}"#),
    );
    assert_opensearch_error_shape(&predict_before_deploy, 400, "illegal_argument_exception");

    let deploy = http_response(
        port,
        "POST",
        "/_plugins/_ml/models/minilm-onnx/_deploy",
        None,
    );
    assert_eq!(deploy["status"], 200);
    assert_eq!(deploy["body"]["task"]["kind"], "deploy_model");
    assert_eq!(deploy["body"]["task"]["state"], "completed");
    let deploy_task_id = deploy["body"]["task"]["task_id"].as_str().unwrap();

    let deploy_task = http_response(
        port,
        "GET",
        &format!("/_plugins/_ml/tasks/{deploy_task_id}"),
        None,
    );
    assert_eq!(deploy_task["status"], 200);
    assert_eq!(deploy_task["body"]["kind"], "deploy_model");
    assert_eq!(deploy_task["body"]["state"], "completed");
    let register_task_id = register_task_id.to_string();
    let deploy_task_id = deploy_task_id.to_string();

    guard.children[0].kill().unwrap();
    guard.children[0].wait().unwrap();
    guard.children.clear();

    let mut restarted = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-ml-model-api")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = restarted.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    port = read_reported_http_port(&mut reader);
    guard.children.push(restarted);

    let deployed_model = http_response(port, "GET", "/_plugins/_ml/models/minilm-onnx", None);
    assert_eq!(deployed_model["status"], 200);
    assert_eq!(deployed_model["body"]["state"], "deployed");
    assert_eq!(deployed_model["body"]["access"]["tenant"], "development");
    let restored_register_task = http_response(
        port,
        "GET",
        &format!("/_plugins/_ml/tasks/{register_task_id}"),
        None,
    );
    assert_eq!(restored_register_task["status"], 200);
    assert_eq!(restored_register_task["body"]["kind"], "register_model");
    let restored_deploy_task = http_response(
        port,
        "GET",
        &format!("/_plugins/_ml/tasks/{deploy_task_id}"),
        None,
    );
    assert_eq!(restored_deploy_task["status"], 200);
    assert_eq!(restored_deploy_task["body"]["kind"], "deploy_model");

    let search = http_response(
        port,
        "POST",
        "/_plugins/_ml/models/_search",
        Some(br#"{"name":"all-MiniLM-L6-v2","state":"deployed"}"#),
    );
    assert_eq!(search["status"], 200);
    assert_eq!(search["body"]["total"], 1);
    assert_eq!(search["body"]["models"][0]["model_id"], "minilm-onnx");

    let undeploy = http_response(
        port,
        "POST",
        "/_plugins/_ml/models/minilm-onnx/_undeploy",
        None,
    );
    assert_eq!(undeploy["status"], 200);
    assert_eq!(undeploy["body"]["task"]["kind"], "undeploy_model");
    assert_eq!(undeploy["body"]["task"]["state"], "completed");
    let undeploy_task_id = undeploy["body"]["task"]["task_id"].as_str().unwrap();

    let undeploy_task = http_response(
        port,
        "GET",
        &format!("/_plugins/_ml/tasks/{undeploy_task_id}"),
        None,
    );
    assert_eq!(undeploy_task["status"], 200);
    assert_eq!(undeploy_task["body"]["kind"], "undeploy_model");
    assert_eq!(undeploy_task["body"]["state"], "completed");

    let undeployed_model = http_response(port, "GET", "/_plugins/_ml/models/minilm-onnx", None);
    assert_eq!(undeployed_model["status"], 200);
    assert_eq!(undeployed_model["body"]["state"], "undeployed");

    let predict_after_undeploy = http_response(
        port,
        "POST",
        "/_plugins/_ml/models/minilm-onnx/_predict",
        Some(br#"{"model_id":"minilm-onnx","texts":["steelsearch vector search"]}"#),
    );
    assert_opensearch_error_shape(&predict_after_undeploy, 400, "illegal_argument_exception");

    let missing_auth_metadata = http_response(
        port,
        "POST",
        "/_plugins/_ml/model_groups/_register",
        Some(br#"{"group_id":"missing-auth","name":"missing-auth"}"#),
    );
    assert_opensearch_error_shape(&missing_auth_metadata, 400, "parse_exception");

    let unsupported_connector = http_response(
        port,
        "POST",
        "/_plugins/_ml/models/_register",
        Some(
            br#"{"model_id":"remote-missing-connector","group_id":"group-1","name":"remote","version":"1","format":"remote","inference":{"kind":"remote_connector","connector_id":"missing-connector","input_path":"$.text","output_path":"$.embedding"}}"#,
        ),
    );
    assert_opensearch_error_shape(&unsupported_connector, 404, "resource_not_found_exception");

    let unsupported_processor = http_response(
        port,
        "POST",
        "/_plugins/_ml/processors/_execute",
        Some(br#"{"processor":"text_embedding"}"#),
    );
    assert_opensearch_error_shape(&unsupported_processor, 404, "no_handler_found_exception");

    guard.children[0].kill().unwrap();
    guard.children[0].wait().unwrap();
    guard.children.clear();

    let mut restarted = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-ml-model-api")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = restarted.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let restarted_port = read_reported_http_port(&mut reader);
    guard.children.push(restarted);

    let restarted_task = wait_http_response(
        restarted_port,
        "GET",
        &format!("/_plugins/_ml/tasks/{undeploy_task_id}"),
        None,
    );
    assert_eq!(restarted_task["status"], 200);
    assert_eq!(restarted_task["body"]["kind"], "undeploy_model");
    assert_eq!(restarted_task["body"]["state"], "completed");
    let restarted_model = http_response(
        restarted_port,
        "GET",
        "/_plugins/_ml/models/minilm-onnx",
        None,
    );
    assert_eq!(restarted_model["status"], 200);
    assert_eq!(restarted_model["body"]["state"], "undeployed");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_runs_ml_embedding_knn_hybrid_and_rerank_flow_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-ml-e2e-api")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let group = wait_http_response(
        port,
        "POST",
        "/_plugins/_ml/model_groups/_register",
        Some(
            br#"{"group_id":"group-1","name":"embeddings","access":{"owner":"steelsearch-dev","backend_roles":["ml-admin"],"tenant":"development","is_public":false}}"#,
        ),
    );
    assert_eq!(group["status"], 200);

    let register = http_response(
        port,
        "POST",
        "/_plugins/_ml/models/_register",
        Some(
            br#"{"model_id":"minilm-onnx","group_id":"group-1","name":"all-MiniLM-L6-v2","version":"1","format":"onnx","inference":{"kind":"text_embedding","embedding_dimension":8,"max_sequence_length":16,"normalize":true,"pooling":"mean"}}"#,
        ),
    );
    assert_eq!(register["status"], 200);

    let deploy = http_response(
        port,
        "POST",
        "/_plugins/_ml/models/minilm-onnx/_deploy",
        None,
    );
    assert_eq!(deploy["status"], 200);
    assert_eq!(deploy["body"]["task"]["state"], "completed");

    let predict = http_response(
        port,
        "POST",
        "/_plugins/_ml/models/minilm-onnx/_predict",
        Some(
            br#"{"model_id":"minilm-onnx","texts":["rust vector search","java transport compatibility","recipe tomatoes pasta","rust vector search"]}"#,
        ),
    );
    assert_eq!(predict["status"], 200);
    let vectors = predict["body"]["vectors"].as_array().unwrap();
    assert_eq!(vectors.len(), 4);
    for vector in vectors {
        assert_eq!(vector.as_array().unwrap().len(), 8);
    }

    let create = http_response(
        port,
        "PUT",
        "/ml-e2e-it",
        Some(
            br#"{"settings":{"index":{"knn":true}},"mappings":{"properties":{"tenant":{"type":"keyword"},"body":{"type":"text"},"body_vector":{"type":"knn_vector","dimension":8,"method":{"name":"hnsw","engine":"lucene","space_type":"l2"}}}}}"#,
        ),
    );
    assert_eq!(create["status"], 200);

    let docs = [
        ("doc-rust", "rust vector search", &vectors[0]),
        ("doc-java", "java transport compatibility", &vectors[1]),
        ("doc-cooking", "recipe tomatoes pasta", &vectors[2]),
    ];
    let mut bulk_body = String::new();
    for (id, body, vector) in docs {
        bulk_body.push_str(
            &serde_json::to_string(&serde_json::json!({ "index": { "_id": id } })).unwrap(),
        );
        bulk_body.push('\n');
        bulk_body.push_str(
            &serde_json::to_string(&serde_json::json!({
                "tenant": "development",
                "body": body,
                "body_vector": vector,
            }))
            .unwrap(),
        );
        bulk_body.push('\n');
    }

    let bulk = http_response(
        port,
        "POST",
        "/ml-e2e-it/_bulk?refresh=false",
        Some(bulk_body.as_bytes()),
    );
    assert_eq!(bulk["status"], 200);
    assert_eq!(bulk["body"]["errors"], false);
    assert_eq!(bulk["body"]["items"].as_array().unwrap().len(), 3);

    assert_refresh_success(&http_response(
        port,
        "POST",
        "/ml-e2e-it/_refresh",
        Some(b"{}"),
    ));

    let query_vector = vectors[3].clone();
    let knn_body = serde_json::to_vec(&serde_json::json!({
        "query": { "knn": { "body_vector": { "vector": query_vector, "k": 3 } } },
        "size": 3
    }))
    .unwrap();
    let knn = http_response(port, "POST", "/ml-e2e-it/_search", Some(&knn_body));
    assert_eq!(knn["status"], 200);
    let knn_hits = knn["body"]["hits"]["hits"].as_array().unwrap();
    assert_eq!(knn_hits.len(), 3);
    assert_eq!(knn_hits[0]["_id"], "doc-rust");
    assert_eq!(knn_hits[0]["_source"]["body"], "rust vector search");

    let hybrid_body = serde_json::to_vec(&serde_json::json!({
        "query": {
            "bool": {
                "must": [
                    { "match": { "body": "rust vector search" } },
                    { "knn": { "body_vector": { "vector": vectors[3].clone(), "k": 3 } } }
                ]
            }
        },
        "size": 3
    }))
    .unwrap();
    let hybrid = http_response(port, "POST", "/ml-e2e-it/_search", Some(&hybrid_body));
    assert_eq!(hybrid["status"], 200);
    let hybrid_hits = hybrid["body"]["hits"]["hits"].as_array().unwrap();
    assert!(!hybrid_hits.is_empty());
    assert_eq!(hybrid_hits[0]["_id"], "doc-rust");

    let rerank = http_response(
        port,
        "POST",
        "/_plugins/_ml/_rerank",
        Some(
            br#"{"query_text":"rust vector search","candidates":[{"id":"doc-rust","text":"rust vector search","lexical_score":0.2},{"id":"doc-java","text":"java transport compatibility","lexical_score":0.9},{"id":"doc-cooking","text":"recipe tomatoes pasta","lexical_score":0.1}],"lexical_weight":0.2,"semantic_weight":0.8}"#,
        ),
    );
    assert_eq!(rerank["status"], 200);
    let rerank_scores = rerank["body"]["scores"].as_array().unwrap();
    assert_eq!(rerank_scores.len(), 3);
    assert_eq!(rerank_scores[0]["id"], "doc-rust");
    assert!(
        rerank_scores[0]["score"].as_f64().unwrap() > rerank_scores[1]["score"].as_f64().unwrap()
    );

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_rest_index_api_returns_opensearch_error_shapes() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-index-errors")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let create = wait_http_response(port, "PUT", "/logs-errors-it", None);
    assert_eq!(create["status"], 200);

    let duplicate = http_response(port, "PUT", "/logs-errors-it", None);
    assert_opensearch_error(
        &duplicate,
        400,
        "resource_already_exists_exception",
        "index [logs-errors-it] already exists",
    );

    let malformed_mapping = http_response(
        port,
        "PUT",
        "/malformed-mapping-it",
        Some(br#"{"mappings":{"properties":false}}"#),
    );
    assert_opensearch_error(
        &malformed_mapping,
        400,
        "illegal_argument_exception",
        "invalid engine request: mappings.properties must be an object",
    );

    let supported_geo_point = http_response(
        port,
        "PUT",
        "/geo-point-it",
        Some(br#"{"mappings":{"properties":{"location":{"type":"geo_point"}}}}"#),
    );
    assert_eq!(supported_geo_point["status"], 200, "{supported_geo_point}");

    let unsupported_field_type = http_response(
        port,
        "PUT",
        "/unsupported-field-it",
        Some(br#"{"mappings":{"properties":{"shape":{"type":"geo_shape"}}}}"#),
    );
    assert_opensearch_error(
        &unsupported_field_type,
        400,
        "illegal_argument_exception",
        "invalid engine request: unsupported OpenSearch field type [geo_shape] for field [shape]",
    );

    let missing_index = http_response(port, "GET", "/missing-errors-it", None);
    assert_opensearch_error(
        &missing_index,
        404,
        "index_not_found_exception",
        "no such index [missing-errors-it]",
    );

    let invalid_index = http_response(port, "PUT", "/Logs-Errors-It", None);
    assert_opensearch_error(
        &invalid_index,
        400,
        "invalid_index_name_exception",
        "invalid index name [Logs-Errors-It], must be lowercase",
    );

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_put_index_reports_opensearch_error_shapes_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-index-errors")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    assert_eq!(
        wait_json(port, "GET", "/_cluster/health", None)["status"],
        "green"
    );

    let first = http_response(port, "PUT", "/errors-it", None);
    assert_eq!(first["status"], 200);

    let duplicate = http_response(port, "PUT", "/errors-it", None);
    assert_opensearch_error_shape(&duplicate, 400, "resource_already_exists_exception");

    let malformed_mapping = http_response(
        port,
        "PUT",
        "/malformed-mapping-it",
        Some(br#"{"mappings":{"properties":[]}}"#),
    );
    assert_opensearch_error_shape(&malformed_mapping, 400, "illegal_argument_exception");

    let supported_geo_point = http_response(
        port,
        "PUT",
        "/geo-point-it",
        Some(br#"{"mappings":{"properties":{"location":{"type":"geo_point"}}}}"#),
    );
    assert_eq!(supported_geo_point["status"], 200, "{supported_geo_point}");

    let unsupported_field = http_response(
        port,
        "PUT",
        "/unsupported-field-it",
        Some(br#"{"mappings":{"properties":{"shape":{"type":"geo_shape"}}}}"#),
    );
    assert_opensearch_error_shape(&unsupported_field, 400, "illegal_argument_exception");

    let missing = http_response(port, "GET", "/missing-index-it", None);
    assert_opensearch_error_shape(&missing, 404, "index_not_found_exception");

    let invalid_name = http_response(port, "PUT", "/Invalid-Index", None);
    assert_opensearch_error_shape(&invalid_name, 400, "invalid_index_name_exception");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_document_put_get_returns_metadata_and_missing_shape_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-doc-api")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let create = wait_http_response(
        port,
        "PUT",
        "/documents-it",
        Some(br#"{"mappings":{"properties":{"message":{"type":"text"},"level":{"type":"keyword"}}}}"#),
    );
    assert_eq!(create["status"], 200);

    let index = http_response(
        port,
        "PUT",
        "/documents-it/_doc/1",
        Some(br#"{"message":"hello from daemon document api","level":"info"}"#),
    );
    assert_eq!(index["status"], 201);
    assert_eq!(index["body"]["_index"], "documents-it");
    assert_eq!(index["body"]["_id"], "1");
    assert_eq!(index["body"]["_version"], 1);
    assert_eq!(index["body"]["_seq_no"], 0);
    assert_eq!(index["body"]["_primary_term"], 1);
    assert_eq!(index["body"]["result"], "created");

    let get = http_response(port, "GET", "/documents-it/_doc/1", None);
    assert_eq!(get["status"], 200);
    assert_eq!(get["body"]["_index"], "documents-it");
    assert_eq!(get["body"]["_id"], "1");
    assert_eq!(get["body"]["_version"], 1);
    assert_eq!(get["body"]["_seq_no"], 0);
    assert_eq!(get["body"]["_primary_term"], 1);
    assert_eq!(get["body"]["found"], true);
    assert_eq!(
        get["body"]["_source"]["message"],
        "hello from daemon document api"
    );
    assert_eq!(get["body"]["_source"]["level"], "info");

    let missing = http_response(port, "GET", "/documents-it/_doc/missing", None);
    assert_eq!(missing["status"], 404);
    assert_eq!(missing["body"]["_index"], "documents-it");
    assert_eq!(missing["body"]["_id"], "missing");
    assert_eq!(missing["body"]["found"], false);

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_document_put_and_get_return_metadata_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-doc-api")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let create = wait_http_response(
        port,
        "PUT",
        "/docs-it",
        Some(br#"{"mappings":{"properties":{"message":{"type":"text"},"level":{"type":"keyword"}}}}"#),
    );
    assert_eq!(create["status"], 200);

    let index_doc = http_response(
        port,
        "PUT",
        "/docs-it/_doc/alpha",
        Some(br#"{"message":"document api smoke","level":"info"}"#),
    );
    assert_eq!(index_doc["status"], 201);
    assert_eq!(index_doc["body"]["_index"], "docs-it");
    assert_eq!(index_doc["body"]["_id"], "alpha");
    assert_eq!(index_doc["body"]["_version"], 1);
    assert_eq!(index_doc["body"]["_seq_no"], 0);
    assert_eq!(index_doc["body"]["_primary_term"], 1);
    assert_eq!(index_doc["body"]["result"], "created");

    let get_doc = http_response(port, "GET", "/docs-it/_doc/alpha", None);
    assert_eq!(get_doc["status"], 200);
    assert_eq!(get_doc["body"]["_index"], "docs-it");
    assert_eq!(get_doc["body"]["_id"], "alpha");
    assert_eq!(get_doc["body"]["_version"], 1);
    assert_eq!(get_doc["body"]["_seq_no"], 0);
    assert_eq!(get_doc["body"]["_primary_term"], 1);
    assert_eq!(get_doc["body"]["found"], true);
    assert_eq!(get_doc["body"]["_source"]["message"], "document api smoke");
    assert_eq!(get_doc["body"]["_source"]["level"], "info");

    let missing_doc = http_response(port, "GET", "/docs-it/_doc/missing", None);
    assert_eq!(missing_doc["status"], 404);
    assert_eq!(missing_doc["body"]["_index"], "docs-it");
    assert_eq!(missing_doc["body"]["_id"], "missing");
    assert_eq!(missing_doc["body"]["found"], false);

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_refresh_endpoints_and_write_refresh_policy_control_search_visibility() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-refresh-api")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let create = wait_http_response(
        port,
        "PUT",
        "/refresh-it",
        Some(br#"{"mappings":{"properties":{"message":{"type":"text"},"level":{"type":"keyword"}}}}"#),
    );
    assert_eq!(create["status"], 200);

    let first = http_response(
        port,
        "PUT",
        "/refresh-it/_doc/1",
        Some(br#"{"message":"manual scoped refresh","level":"info"}"#),
    );
    assert_eq!(first["status"], 201);
    assert_eq!(search_total(port, "/refresh-it/_search"), 0);

    let scoped_refresh = http_response(port, "POST", "/refresh-it/_refresh", Some(b"{}"));
    assert_refresh_success(&scoped_refresh);
    assert_eq!(search_total(port, "/refresh-it/_search"), 1);

    let second = http_response(
        port,
        "PUT",
        "/refresh-it/_doc/2",
        Some(br#"{"message":"manual all refresh","level":"info"}"#),
    );
    assert_eq!(second["status"], 201);
    assert_eq!(search_total(port, "/refresh-it/_search"), 1);

    let all_refresh = http_response(port, "POST", "/_refresh", Some(b"{}"));
    assert_refresh_success(&all_refresh);
    assert_eq!(search_total(port, "/refresh-it/_search"), 2);

    let immediate = http_response(
        port,
        "PUT",
        "/refresh-it/_doc/3?refresh=true",
        Some(br#"{"message":"immediate refresh","level":"info"}"#),
    );
    assert_eq!(immediate["status"], 201);
    assert_eq!(search_total(port, "/refresh-it/_search"), 3);

    let wait_for = http_response(
        port,
        "PUT",
        "/refresh-it/_doc/4?refresh=wait_for",
        Some(br#"{"message":"wait for refresh","level":"info"}"#),
    );
    assert_eq!(wait_for["status"], 201);
    assert_eq!(search_total(port, "/refresh-it/_search"), 4);

    let invalid_policy = http_response(
        port,
        "PUT",
        "/refresh-it/_doc/5?refresh=sideways",
        Some(br#"{"message":"invalid refresh","level":"info"}"#),
    );
    assert_opensearch_error_shape(&invalid_policy, 400, "illegal_argument_exception");

    let flush_doc = http_response(
        port,
        "PUT",
        "/refresh-it/_doc/6",
        Some(br#"{"message":"visible after flush","level":"info"}"#),
    );
    assert_eq!(flush_doc["status"], 201);
    assert_eq!(search_total(port, "/refresh-it/_search"), 4);

    let flush = http_response(port, "POST", "/_flush", Some(b"{}"));
    assert_refresh_success(&flush);
    assert_eq!(search_total(port, "/refresh-it/_search"), 5);

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_search_endpoint_covers_supported_queries_and_errors_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-search-api")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let create = wait_http_response(
        port,
        "PUT",
        "/search-it",
        Some(
            br#"{"mappings":{"properties":{"message":{"type":"text"},"service":{"type":"keyword"},"tags":{"type":"keyword"},"bytes":{"type":"long"},"level":{"type":"keyword"}}}}"#,
        ),
    );
    assert_eq!(create["status"], 200);

    for (id, source) in [
        (
            "1",
            br#"{"message":"Error from API request completed","service":"api","tags":["prod","blue"],"bytes":120,"level":"info"}"#.as_slice(),
        ),
        (
            "2",
            br#"{"message":"worker completed request","service":"worker","tags":["batch","green"],"bytes":90,"level":"debug"}"#.as_slice(),
        ),
        (
            "3",
            br#"{"message":"cache warming started","tags":["prod"],"bytes":40,"level":"info"}"#.as_slice(),
        ),
        (
            "4",
            br#"{"message":"api timeout warning","service":"api","tags":["prod","green"],"bytes":220,"level":"warn"}"#.as_slice(),
        ),
    ] {
        let response = http_response(port, "PUT", &format!("/search-it/_doc/{id}"), Some(source));
        assert_eq!(response["status"], 201);
    }
    assert_refresh_success(&http_response(
        port,
        "POST",
        "/search-it/_refresh",
        Some(b"{}"),
    ));

    let match_all = http_response(
        port,
        "GET",
        "/search-it/_search",
        Some(br#"{"query":{"match_all":{}},"size":10}"#),
    );
    assert_eq!(match_all["status"], 200);
    assert_eq!(match_all["body"]["hits"]["total"]["value"], 4);

    assert_eq!(
        search_ids(
            port,
            "POST",
            "/search-it/_search",
            br#"{"query":{"term":{"service":"api"}},"size":10}"#,
        ),
        vec!["1", "4"]
    );
    assert_eq!(
        search_ids(
            port,
            "POST",
            "/search-it/_search",
            br#"{"query":{"terms":{"tags":["green"]}},"size":10}"#,
        ),
        vec!["2", "4"]
    );
    assert_eq!(
        search_ids(
            port,
            "POST",
            "/search-it/_search",
            br#"{"query":{"match":{"message":"completed"}},"size":10}"#,
        ),
        vec!["1", "2"]
    );
    assert_eq!(
        search_ids(
            port,
            "POST",
            "/search-it/_search",
            br#"{"query":{"range":{"bytes":{"gte":100,"lte":220}}},"size":10}"#,
        ),
        vec!["1", "4"]
    );
    assert_eq!(
        search_ids(
            port,
            "POST",
            "/search-it/_search",
            br#"{"query":{"bool":{"must":{"match":{"message":"request"}},"filter":{"term":{"service":"api"}},"must_not":{"term":{"level":"debug"}}}},"size":10}"#,
        ),
        vec!["1"]
    );
    assert_eq!(
        search_ids(
            port,
            "POST",
            "/search-it/_search",
            br#"{"query":{"ids":{"values":["2","4"]}},"size":10}"#,
        ),
        vec!["2", "4"]
    );
    assert_eq!(
        search_ids(
            port,
            "POST",
            "/search-it/_search",
            br#"{"query":{"exists":{"field":"service"}},"size":10}"#,
        ),
        vec!["1", "2", "4"]
    );
    assert_eq!(
        search_ids(
            port,
            "POST",
            "/search-it/_search",
            br#"{"query":{"prefix":{"service":"wo"}},"size":10}"#,
        ),
        vec!["2"]
    );
    assert_eq!(
        search_ids(
            port,
            "POST",
            "/search-it/_search",
            br#"{"query":{"wildcard":{"message":{"value":"err*api*","case_insensitive":true}}},"size":10}"#,
        ),
        vec!["1"]
    );

    let malformed = http_response(port, "POST", "/search-it/_search", Some(br#"{"query":"#));
    assert_opensearch_error_shape(&malformed, 400, "parse_exception");

    let unsupported = http_response(
        port,
        "POST",
        "/search-it/_search",
        Some(br#"{"query":{"geo_shape":{"location":{"shape":{"type":"point","coordinates":[0,0]}}}}}"#),
    );
    assert_opensearch_error_shape(&unsupported, 400, "illegal_argument_exception");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_search_endpoint_preserves_result_shape_sorting_and_pagination() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-search-shape")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let create = wait_http_response(
        port,
        "PUT",
        "/shape-it",
        Some(
            br#"{"mappings":{"properties":{"message":{"type":"text"},"service":{"type":"keyword"},"bytes":{"type":"long"},"level":{"type":"keyword"}}}}"#,
        ),
    );
    assert_eq!(create["status"], 200);

    for (id, source) in [
        (
            "1",
            br#"{"message":"first retained source","service":"api","bytes":100,"level":"info","payload":{"request_id":"req-1"}}"#.as_slice(),
        ),
        (
            "2",
            br#"{"message":"second retained source","service":"api","bytes":300,"level":"warn","payload":{"request_id":"req-2"}}"#.as_slice(),
        ),
        (
            "3",
            br#"{"message":"third retained source","service":"api","bytes":200,"level":"debug","payload":{"request_id":"req-3"}}"#.as_slice(),
        ),
    ] {
        let response = http_response(port, "PUT", &format!("/shape-it/_doc/{id}"), Some(source));
        assert_eq!(response["status"], 201);
    }
    assert_refresh_success(&http_response(
        port,
        "POST",
        "/shape-it/_refresh",
        Some(b"{}"),
    ));

    let sorted_page = http_response(
        port,
        "POST",
        "/shape-it/_search",
        Some(
            br#"{"query":{"term":{"service":"api"}},"sort":[{"bytes":{"order":"desc"}}],"from":1,"size":2}"#,
        ),
    );
    assert_eq!(sorted_page["status"], 200);
    assert_eq!(sorted_page["body"]["timed_out"], false);
    assert!(sorted_page["body"]["took"].as_u64().is_some());
    assert_eq!(sorted_page["body"]["_shards"]["total"], 1);
    assert_eq!(sorted_page["body"]["_shards"]["successful"], 1);
    assert_eq!(sorted_page["body"]["_shards"]["skipped"], 0);
    assert_eq!(sorted_page["body"]["_shards"]["failed"], 0);
    assert_eq!(sorted_page["body"]["hits"]["total"]["value"], 3);
    assert_eq!(sorted_page["body"]["hits"]["total"]["relation"], "eq");
    assert!(sorted_page["body"]["hits"]["max_score"].as_f64().is_some());

    let hits = sorted_page["body"]["hits"]["hits"].as_array().unwrap();
    assert_eq!(hits.len(), 2);
    assert_eq!(hits[0]["_id"], "3");
    assert_eq!(hits[0]["_source"]["message"], "third retained source");
    assert_eq!(hits[0]["_source"]["payload"]["request_id"], "req-3");
    assert_eq!(hits[0]["_version"], 1);
    assert_eq!(hits[0]["_seq_no"], 2);
    assert_eq!(hits[0]["_primary_term"], 1);
    assert_eq!(hits[1]["_id"], "1");
    assert_eq!(hits[1]["_source"]["payload"]["request_id"], "req-1");

    let no_hits = http_response(
        port,
        "POST",
        "/shape-it/_search",
        Some(br#"{"query":{"term":{"level":"missing"}}}"#),
    );
    assert_eq!(no_hits["status"], 200);
    assert_eq!(no_hits["body"]["_shards"]["total"], 1);
    assert_eq!(no_hits["body"]["_shards"]["successful"], 1);
    assert_eq!(no_hits["body"]["_shards"]["failed"], 0);
    assert_eq!(no_hits["body"]["hits"]["total"]["value"], 0);
    assert_eq!(no_hits["body"]["hits"]["total"]["relation"], "eq");
    assert!(no_hits["body"]["hits"]["max_score"].is_null());
    assert!(no_hits["body"]["hits"]["hits"]
        .as_array()
        .unwrap()
        .is_empty());

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_search_endpoint_returns_supported_aggregation_shapes_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-search-aggs")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let create = wait_http_response(
        port,
        "PUT",
        "/aggs-it",
        Some(
            br#"{"mappings":{"properties":{"service":{"type":"keyword"},"level":{"type":"keyword"},"tag":{"type":"keyword"},"bytes":{"type":"long"},"message":{"type":"text"}}}}"#,
        ),
    );
    assert_eq!(create["status"], 200);

    for (id, source) in [
        (
            "1",
            br#"{"service":"api","level":"info","tag":"auth","bytes":100,"message":"api info one","location":{"lat":37.77,"lon":-122.42}}"#.as_slice(),
        ),
        (
            "2",
            br#"{"service":"api","level":"info","tag":"auth","bytes":200,"message":"api info two","location":{"lat":34.05,"lon":-118.24}}"#.as_slice(),
        ),
        (
            "3",
            br#"{"service":"api","level":"error","tag":"billing","bytes":500,"message":"api error","location":{"lat":40.71,"lon":-74.0}}"#.as_slice(),
        ),
        (
            "4",
            br#"{"service":"worker","level":"info","tag":"auth","bytes":50,"message":"worker info"}"#.as_slice(),
        ),
    ] {
        let response = http_response(port, "PUT", &format!("/aggs-it/_doc/{id}"), Some(source));
        assert_eq!(response["status"], 201);
    }
    assert_refresh_success(&http_response(
        port,
        "POST",
        "/aggs-it/_refresh",
        Some(b"{}"),
    ));

    let search = http_response(
        port,
        "POST",
        "/aggs-it/_search",
        Some(
            br#"{
                "query": { "match_all": {} },
                "size": 0,
                "aggs": {
                    "by_service": { "terms": { "field": "service", "size": 10 } },
                    "min_bytes": { "min": { "field": "bytes" } },
                    "max_bytes": { "max": { "field": "bytes" } },
                    "sum_bytes": { "sum": { "field": "bytes" } },
                    "avg_bytes": { "avg": { "field": "bytes" } },
                    "count_bytes": { "value_count": { "field": "bytes" } },
                    "only_errors": { "filter": { "term": { "level": "error" } } },
                    "by_level_filter": {
                        "filters": {
                            "filters": {
                                "errors": { "term": { "level": "error" } },
                                "infos": { "term": { "level": "info" } }
                            }
                        }
                    },
                    "sample": { "top_hits": { "from": 1, "size": 1 } },
                    "by_service_level": {
                        "composite": {
                            "size": 10,
                            "sources": [
                                { "service": { "terms": { "field": "service" } } },
                                { "level": { "terms": { "field": "level" } } }
                            ]
                        }
                    },
                    "interesting_tags": {
                        "significant_terms": { "field": "tag", "size": 2 }
                    },
                    "viewport": { "geo_bounds": { "field": "location" } },
                    "service_doc_total": {
                        "sum_bucket": { "buckets_path": "by_service>_count" }
                    },
                    "custom_metric": {
                        "scripted_metric": {
                            "map_script": "return params.value",
                            "params": { "value": { "count": 7 } }
                        }
                    },
                    "custom_plugin": {
                        "plugin": {
                            "name": "example-plugin",
                            "kind": "example_metric",
                            "params": { "field": "service" }
                        }
                    }
                }
            }"#,
        ),
    );
    assert_eq!(search["status"], 200);
    assert_eq!(search["body"]["hits"]["total"]["value"], 4);
    let aggregations = &search["body"]["aggregations"];

    assert_eq!(
        aggregations["by_service"]["buckets"],
        serde_json::json!([
            { "key": "api", "doc_count": 3 },
            { "key": "worker", "doc_count": 1 }
        ])
    );
    assert_eq!(aggregations["min_bytes"]["value"], 50.0);
    assert_eq!(aggregations["max_bytes"]["value"], 500.0);
    assert_eq!(aggregations["sum_bytes"]["value"], 850.0);
    assert_eq!(aggregations["avg_bytes"]["value"], 212.5);
    assert_eq!(aggregations["count_bytes"]["value"], 4.0);
    assert_eq!(aggregations["only_errors"]["doc_count"], 1);
    assert_eq!(
        aggregations["by_level_filter"]["buckets"],
        serde_json::json!({
            "errors": { "doc_count": 1 },
            "infos": { "doc_count": 3 }
        })
    );
    assert_eq!(aggregations["sample"]["hits"]["total"]["value"], 4);
    assert_eq!(
        aggregations["sample"]["hits"]["hits"][0]["_source"]["message"],
        "api info two"
    );
    assert_eq!(
        aggregations["by_service_level"]["buckets"],
        serde_json::json!([
            { "key": { "level": "error", "service": "api" }, "doc_count": 1 },
            { "key": { "level": "info", "service": "api" }, "doc_count": 2 },
            { "key": { "level": "info", "service": "worker" }, "doc_count": 1 }
        ])
    );
    assert_eq!(
        aggregations["interesting_tags"]["buckets"],
        serde_json::json!([
            { "key": "auth", "doc_count": 3, "bg_count": 3, "score": 3.0 },
            { "key": "billing", "doc_count": 1, "bg_count": 1, "score": 1.0 }
        ])
    );
    assert_eq!(
        aggregations["viewport"],
        serde_json::json!({
            "bounds": {
                "top_left": { "lat": 40.71, "lon": -122.42 },
                "bottom_right": { "lat": 34.05, "lon": -74.0 }
            }
        })
    );
    assert_eq!(aggregations["service_doc_total"]["value"], 4.0);
    assert_eq!(
        aggregations["custom_metric"]["value"],
        serde_json::json!({ "count": 7 })
    );
    assert_eq!(
        aggregations["custom_plugin"],
        serde_json::json!({
            "value": null,
            "_plugin": "example-plugin",
            "_type": "example_metric",
            "params": { "field": "service" }
        })
    );

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_bulk_endpoints_execute_ndjson_write_operations_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-bulk")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let create = wait_http_response(
        port,
        "PUT",
        "/bulk-it",
        Some(
            br#"{"mappings":{"properties":{"message":{"type":"text"},"service":{"type":"keyword"},"ordinal":{"type":"long"},"flag":{"type":"boolean"}}}}"#,
        ),
    );
    assert_eq!(create["status"], 200);

    let route_bulk = http_response(
        port,
        "POST",
        "/bulk-it/_bulk",
        Some(
            b"{\"index\":{\"_id\":\"1\"}}\n{\"message\":\"first\",\"service\":\"api\",\"ordinal\":1}\n{\"create\":{\"_id\":\"2\"}}\n{\"message\":\"second\",\"service\":\"api\",\"ordinal\":2}\n{\"update\":{\"_id\":\"2\"}}\n{\"doc\":{\"message\":\"second updated\",\"flag\":true}}\n{\"delete\":{\"_id\":\"1\"}}\n",
        ),
    );
    assert_eq!(route_bulk["status"], 200);
    assert_eq!(route_bulk["body"]["errors"], false);
    assert_eq!(route_bulk["body"]["items"].as_array().unwrap().len(), 4);
    assert_eq!(route_bulk["body"]["items"][0]["index"]["_index"], "bulk-it");
    assert_eq!(route_bulk["body"]["items"][0]["index"]["_id"], "1");
    assert_eq!(route_bulk["body"]["items"][0]["index"]["status"], 201);
    assert_eq!(route_bulk["body"]["items"][0]["index"]["result"], "created");
    assert_eq!(route_bulk["body"]["items"][1]["create"]["_id"], "2");
    assert_eq!(route_bulk["body"]["items"][1]["create"]["status"], 201);
    assert_eq!(
        route_bulk["body"]["items"][1]["create"]["result"],
        "created"
    );
    assert_eq!(route_bulk["body"]["items"][2]["update"]["_id"], "2");
    assert_eq!(route_bulk["body"]["items"][2]["update"]["status"], 200);
    assert_eq!(
        route_bulk["body"]["items"][2]["update"]["result"],
        "updated"
    );
    assert_eq!(route_bulk["body"]["items"][3]["delete"]["_id"], "1");
    assert_eq!(route_bulk["body"]["items"][3]["delete"]["status"], 200);
    assert_eq!(
        route_bulk["body"]["items"][3]["delete"]["result"],
        "deleted"
    );

    assert_refresh_success(&http_response(
        port,
        "POST",
        "/bulk-it/_refresh",
        Some(b"{}"),
    ));
    assert_eq!(search_total(port, "/bulk-it/_search"), 1);
    let doc2 = http_response(port, "GET", "/bulk-it/_doc/2", None);
    assert_eq!(doc2["status"], 200);
    assert_eq!(doc2["body"]["found"], true);
    assert_eq!(doc2["body"]["_source"]["message"], "second updated");
    assert_eq!(doc2["body"]["_source"]["service"], "api");
    assert_eq!(doc2["body"]["_source"]["flag"], true);

    let global_bulk = http_response(
        port,
        "POST",
        "/_bulk",
        Some(
            b"{\"index\":{\"_index\":\"bulk-it\",\"_id\":\"3\"}}\n{\"message\":\"third\",\"service\":\"worker\",\"ordinal\":3}\n{\"create\":{\"_index\":\"bulk-it\",\"_id\":\"4\"}}\n{\"message\":\"fourth\",\"service\":\"worker\",\"ordinal\":4}\n{\"update\":{\"_index\":\"bulk-it\",\"_id\":\"4\"}}\n{\"doc\":{\"message\":\"fourth updated\",\"flag\":true}}\n{\"delete\":{\"_index\":\"bulk-it\",\"_id\":\"2\"}}\n",
        ),
    );
    assert_eq!(global_bulk["status"], 200);
    assert_eq!(global_bulk["body"]["errors"], false);
    assert_eq!(global_bulk["body"]["items"].as_array().unwrap().len(), 4);
    assert_eq!(global_bulk["body"]["items"][0]["index"]["_id"], "3");
    assert_eq!(global_bulk["body"]["items"][0]["index"]["status"], 201);
    assert_eq!(global_bulk["body"]["items"][1]["create"]["_id"], "4");
    assert_eq!(global_bulk["body"]["items"][1]["create"]["status"], 201);
    assert_eq!(global_bulk["body"]["items"][2]["update"]["_id"], "4");
    assert_eq!(
        global_bulk["body"]["items"][2]["update"]["result"],
        "updated"
    );
    assert_eq!(global_bulk["body"]["items"][3]["delete"]["_id"], "2");
    assert_eq!(
        global_bulk["body"]["items"][3]["delete"]["result"],
        "deleted"
    );

    assert_refresh_success(&http_response(
        port,
        "POST",
        "/bulk-it/_refresh",
        Some(b"{}"),
    ));
    assert_eq!(search_total(port, "/bulk-it/_search"), 2);
    let doc3 = http_response(port, "GET", "/bulk-it/_doc/3", None);
    assert_eq!(doc3["status"], 200);
    assert_eq!(doc3["body"]["_source"]["message"], "third");
    let doc4 = http_response(port, "GET", "/bulk-it/_doc/4", None);
    assert_eq!(doc4["status"], 200);
    assert_eq!(doc4["body"]["_source"]["message"], "fourth updated");
    assert_eq!(doc4["body"]["_source"]["flag"], true);

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_bulk_endpoint_reports_ordered_item_and_parse_errors_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-bulk-errors")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let create = wait_http_response(
        port,
        "PUT",
        "/bulk-errors-it",
        Some(
            br#"{"mappings":{"properties":{"message":{"type":"text"},"kind":{"type":"keyword"}}}}"#,
        ),
    );
    assert_eq!(create["status"], 200);

    let mixed = http_response(
        port,
        "POST",
        "/bulk-errors-it/_bulk",
        Some(
            b"{\"index\":{\"_id\":\"dup\"}}\n{\"message\":\"first\",\"kind\":\"duplicate\"}\n{\"index\":{\"_id\":\"dup\"}}\n{\"message\":\"second\",\"kind\":\"duplicate\"}\n{\"delete\":{\"_id\":\"missing\"}}\n{\"index\":{\"_id\":\"ok\"}}\n{\"message\":\"ok\",\"kind\":\"success\"}\n",
        ),
    );
    assert_eq!(mixed["status"], 200);
    assert_eq!(mixed["body"]["errors"], true);
    assert_eq!(mixed["body"]["items"].as_array().unwrap().len(), 4);
    assert_eq!(mixed["body"]["items"][0]["index"]["_id"], "dup");
    assert_eq!(mixed["body"]["items"][0]["index"]["status"], 201);
    assert_eq!(mixed["body"]["items"][0]["index"]["result"], "created");
    assert_eq!(mixed["body"]["items"][1]["index"]["_id"], "dup");
    assert_eq!(mixed["body"]["items"][1]["index"]["status"], 200);
    assert_eq!(mixed["body"]["items"][1]["index"]["result"], "updated");
    assert_eq!(mixed["body"]["items"][2]["delete"]["_id"], "missing");
    assert_eq!(mixed["body"]["items"][2]["delete"]["status"], 404);
    assert_eq!(
        mixed["body"]["items"][2]["delete"]["error"]["type"],
        "document_missing_exception"
    );
    assert_eq!(mixed["body"]["items"][3]["index"]["_id"], "ok");
    assert_eq!(mixed["body"]["items"][3]["index"]["status"], 201);
    assert_eq!(mixed["body"]["items"][3]["index"]["result"], "created");

    assert_refresh_success(&http_response(
        port,
        "POST",
        "/bulk-errors-it/_refresh",
        Some(b"{}"),
    ));
    assert_eq!(search_total(port, "/bulk-errors-it/_search"), 2);
    let duplicate = http_response(port, "GET", "/bulk-errors-it/_doc/dup", None);
    assert_eq!(duplicate["status"], 200);
    assert_eq!(duplicate["body"]["_source"]["message"], "second");
    let ok = http_response(port, "GET", "/bulk-errors-it/_doc/ok", None);
    assert_eq!(ok["status"], 200);
    assert_eq!(ok["body"]["_source"]["message"], "ok");

    let malformed = http_response(port, "POST", "/_bulk", Some(b"[]\n"));
    assert_opensearch_error_shape(&malformed, 400, "parse_exception");

    let missing_source = http_response(
        port,
        "POST",
        "/_bulk",
        Some(b"{\"index\":{\"_index\":\"bulk-errors-it\",\"_id\":\"no-source\"}}\n"),
    );
    assert_opensearch_error_shape(&missing_source, 400, "parse_exception");

    let unknown = http_response(
        port,
        "POST",
        "/_bulk",
        Some(b"{\"upsert\":{\"_index\":\"bulk-errors-it\",\"_id\":\"bad\"}}\n{}\n"),
    );
    assert_opensearch_error_shape(&unknown, 400, "illegal_argument_exception");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_bulk_refresh_policies_control_search_visibility_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-bulk-refresh")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let create = wait_http_response(
        port,
        "PUT",
        "/bulk-refresh-it",
        Some(br#"{"mappings":{"properties":{"message":{"type":"text"},"level":{"type":"keyword"}}}}"#),
    );
    assert_eq!(create["status"], 200);

    let refresh_false = http_response(
        port,
        "POST",
        "/bulk-refresh-it/_bulk?refresh=false",
        Some(b"{\"index\":{\"_id\":\"1\"}}\n{\"message\":\"hidden until refresh\",\"level\":\"info\"}\n"),
    );
    assert_eq!(refresh_false["status"], 200);
    assert_eq!(refresh_false["body"]["errors"], false);
    assert_eq!(search_total(port, "/bulk-refresh-it/_search"), 0);

    let refresh_true = http_response(
        port,
        "POST",
        "/bulk-refresh-it/_bulk?refresh=true",
        Some(b"{\"index\":{\"_id\":\"2\"}}\n{\"message\":\"immediate true\",\"level\":\"info\"}\n"),
    );
    assert_eq!(refresh_true["status"], 200);
    assert_eq!(refresh_true["body"]["errors"], false);
    assert_eq!(search_total(port, "/bulk-refresh-it/_search"), 2);

    let wait_for = http_response(
        port,
        "POST",
        "/bulk-refresh-it/_bulk?refresh=wait_for",
        Some(
            b"{\"index\":{\"_id\":\"3\"}}\n{\"message\":\"wait for refresh\",\"level\":\"info\"}\n",
        ),
    );
    assert_eq!(wait_for["status"], 200);
    assert_eq!(wait_for["body"]["errors"], false);
    assert_eq!(search_total(port, "/bulk-refresh-it/_search"), 3);

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_bulk_retry_is_idempotent_for_same_fixture_over_real_socket() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-bulk-retry")
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let create = wait_http_response(
        port,
        "PUT",
        "/bulk-retry-it",
        Some(
            br#"{"mappings":{"properties":{"message":{"type":"text"},"service":{"type":"keyword"},"ordinal":{"type":"long"},"counter":{"type":"long"}}}}"#,
        ),
    );
    assert_eq!(create["status"], 200);

    let fixture = b"{\"index\":{\"_id\":\"a\"}}\n{\"message\":\"alpha\",\"service\":\"api\",\"ordinal\":1,\"counter\":10}\n{\"index\":{\"_id\":\"b\"}}\n{\"message\":\"beta\",\"service\":\"api\",\"ordinal\":2,\"counter\":20}\n{\"index\":{\"_id\":\"c\"}}\n{\"message\":\"gamma\",\"service\":\"worker\",\"ordinal\":3,\"counter\":30}\n{\"delete\":{\"_id\":\"stale\"}}\n";
    let expected_checksum = "a:alpha:api:1:10|b:beta:api:2:20|c:gamma:worker:3:30";

    for attempt in 0..2 {
        let bulk = http_response(port, "POST", "/bulk-retry-it/_bulk", Some(fixture));
        assert_eq!(bulk["status"], 200);
        assert_eq!(bulk["body"]["errors"], true);
        assert_eq!(bulk["body"]["items"].as_array().unwrap().len(), 4);
        assert_eq!(bulk["body"]["items"][0]["index"]["_id"], "a");
        assert_eq!(bulk["body"]["items"][1]["index"]["_id"], "b");
        assert_eq!(bulk["body"]["items"][2]["index"]["_id"], "c");
        assert_eq!(bulk["body"]["items"][3]["delete"]["_id"], "stale");
        assert_eq!(bulk["body"]["items"][3]["delete"]["status"], 404);
        if attempt == 0 {
            assert_eq!(bulk["body"]["items"][0]["index"]["result"], "created");
            assert_eq!(bulk["body"]["items"][0]["index"]["status"], 201);
        } else {
            assert_eq!(bulk["body"]["items"][0]["index"]["result"], "updated");
            assert_eq!(bulk["body"]["items"][0]["index"]["status"], 200);
        }

        assert_refresh_success(&http_response(
            port,
            "POST",
            "/bulk-retry-it/_refresh",
            Some(b"{}"),
        ));
        let search = http_response(
            port,
            "POST",
            "/bulk-retry-it/_search",
            Some(br#"{"query":{"match_all":{}},"sort":[{"ordinal":{"order":"asc"}}],"size":10}"#),
        );
        assert_eq!(search["status"], 200);
        assert_eq!(search["body"]["hits"]["total"]["value"], 3);
        assert_eq!(bulk_retry_checksum(&search["body"]), expected_checksum);
    }

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_http_responses_preserve_opensearch_headers_and_error_shape() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    let _guard = ChildGuard {
        children: vec![child],
    };

    let info = wait_http_response(port, "GET", "/", None);
    assert_eq!(info["status"], 200);
    assert_eq!(info["headers"]["content-type"], "application/json");

    let head = http_response(port, "HEAD", "/", None);
    assert_eq!(head["status"], 200);
    assert_eq!(head["headers"]["content-length"], "0");
    assert_eq!(head["body_text"], "");

    let missing = http_response_with_headers(
        port,
        "GET",
        "/_steelsearch/missing",
        &[("X-Opaque-Id", "opaque-smoke-1")],
        None,
    );
    assert_eq!(missing["status"], 404);
    assert_eq!(missing["headers"]["content-type"], "application/json");
    assert_eq!(missing["headers"]["x-opaque-id"], "opaque-smoke-1");
    assert_eq!(
        missing["body"]["error"]["type"],
        "no_handler_found_exception"
    );
    assert_eq!(missing["body"]["status"], 404);

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_gracefully_shuts_down_while_idle() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);
    assert_eq!(
        wait_json(port, "GET", "/_cluster/health", None)["status"],
        "green"
    );

    terminate_child(&child);
    let status = wait_for_child_exit(&mut child);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_gracefully_shuts_down_after_in_flight_request() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    fs::create_dir_all(root.join("data")).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--path.data")
        .arg(root.join("data"))
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);

    let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
    stream
        .write_all(
            format!(
                "GET /_cluster/health HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n"
            )
            .as_bytes(),
        )
        .unwrap();
    thread::sleep(Duration::from_millis(25));
    terminate_child(&child);

    let mut response = Vec::new();
    stream.read_to_end(&mut response).unwrap();
    let response = decode_http_response(&response).unwrap();
    assert_eq!(response["status"], 200);
    assert_eq!(response["body"]["status"], "green");

    let status = wait_for_child_exit(&mut child);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_sigterm_after_create_bulk_and_refresh_recovers_on_restart() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    let data_path = root.join("data");
    fs::create_dir_all(&data_path).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-crash")
        .arg("--path.data")
        .arg(&data_path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);

    let create = http_response(
        port,
        "PUT",
        "/crash-it",
        Some(
            br#"{
                "settings": { "index": { "number_of_shards": 1, "number_of_replicas": 0 } },
                "mappings": {
                    "properties": {
                        "message": { "type": "text" },
                        "level": { "type": "keyword" }
                    }
                }
            }"#,
        ),
    );
    assert_eq!(create["status"], 200);

    let bulk = http_response(
        port,
        "POST",
        "/crash-it/_bulk?refresh=false",
        Some(
            b"{\"index\":{\"_id\":\"1\"}}\n{\"message\":\"persisted before crash\",\"level\":\"info\"}\n{\"index\":{\"_id\":\"2\"}}\n{\"message\":\"also persisted before crash\",\"level\":\"warn\"}\n",
        ),
    );
    assert_eq!(bulk["status"], 200);
    assert_eq!(bulk["body"]["errors"], false);
    assert_refresh_success(&http_response(
        port,
        "POST",
        "/crash-it/_refresh",
        Some(b"{}"),
    ));
    assert_eq!(search_total(port, "/crash-it/_search"), 2);
    let unrefreshed = http_response(
        port,
        "PUT",
        "/crash-it/_doc/3?refresh=false",
        Some(br#"{"message":"replayed but not refreshed","level":"debug"}"#),
    );
    assert_eq!(unrefreshed["status"], 201);

    let manifest_path = data_path
        .join("shards")
        .join("crash-it")
        .join("0")
        .join(SHARD_MANIFEST_FILE_NAME);
    let manifest_file: Value = serde_json::from_slice(&fs::read(&manifest_path).unwrap()).unwrap();
    let manifest: ShardManifest =
        serde_json::from_value(manifest_file["manifest"].clone()).unwrap();
    assert_eq!(
        manifest_file["checksum"].as_u64().unwrap(),
        shard_manifest_checksum(&manifest).unwrap()
    );
    assert_eq!(manifest.max_sequence_number, 2);
    assert_eq!(manifest.local_checkpoint, 2);
    assert_eq!(manifest.refreshed_sequence_number, 1);
    assert_eq!(manifest.primary_term, 1);
    assert_eq!(manifest.committed_generation, 0);

    terminate_child(&child);
    let status = wait_for_child_exit(&mut child);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    let mut restarted = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-crash")
        .arg("--path.data")
        .arg(&data_path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = restarted.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let restarted_port = read_reported_http_port(&mut reader);

    let restored_index = http_response(restarted_port, "GET", "/crash-it", None);
    assert_eq!(restored_index["status"], 200);
    assert_eq!(search_total(restarted_port, "/crash-it/_search"), 2);
    let restored_unrefreshed = http_response(restarted_port, "GET", "/crash-it/_doc/3", None);
    assert_eq!(restored_unrefreshed["status"], 200);
    assert_eq!(restored_unrefreshed["body"]["found"], true);
    assert_eq!(
        restored_unrefreshed["body"]["_source"]["message"],
        "replayed but not refreshed"
    );

    terminate_child(&restarted);
    let status = wait_for_child_exit(&mut restarted);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_snapshot_restore_round_trip_after_crash_recovery() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    let data_path = root.join("data");
    fs::create_dir_all(&data_path).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-snapshot-restore-crash")
        .arg("--path.data")
        .arg(&data_path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);

    let create = http_response(
        port,
        "PUT",
        "/snapshot-restore-crash-it",
        Some(
            br#"{"mappings":{"properties":{"message":{"type":"text"},"level":{"type":"keyword"}}}}"#,
        ),
    );
    assert_eq!(create["status"], 200);

    let indexed = http_response(
        port,
        "PUT",
        "/snapshot-restore-crash-it/_doc/1?refresh=true",
        Some(br#"{"message":"visible before crash","level":"info"}"#),
    );
    assert_eq!(indexed["status"], 201);

    let unrefreshed = http_response(
        port,
        "PUT",
        "/snapshot-restore-crash-it/_doc/2?refresh=false",
        Some(br#"{"message":"replayed after crash","level":"debug"}"#),
    );
    assert_eq!(unrefreshed["status"], 201);

    terminate_child(&child);
    let status = wait_for_child_exit(&mut child);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    let mut restarted = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-snapshot-restore-crash")
        .arg("--path.data")
        .arg(&data_path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = restarted.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let restarted_port = read_reported_http_port(&mut reader);

    let restored_index = http_response(restarted_port, "GET", "/snapshot-restore-crash-it", None);
    assert_eq!(restored_index["status"], 200);
    assert_eq!(
        search_total(restarted_port, "/snapshot-restore-crash-it/_search"),
        1
    );
    let replayed = http_response(
        restarted_port,
        "GET",
        "/snapshot-restore-crash-it/_doc/2",
        None,
    );
    assert_eq!(replayed["status"], 200);
    assert_eq!(replayed["body"]["found"], true);

    let repository = http_response(
        restarted_port,
        "PUT",
        "/_snapshot/dev-repo",
        Some(br#"{"type":"fs","settings":{"location":"dev-repo"}}"#),
    );
    assert_eq!(repository["status"], 200);
    assert_eq!(repository["body"]["acknowledged"], true);
    let verify_repository = http_response(
        restarted_port,
        "POST",
        "/_snapshot/dev-repo/_verify",
        Some(br#"{}"#),
    );
    assert_eq!(verify_repository["status"], 200);
    assert_eq!(
        verify_repository["body"]["nodes"]["local"]["verified"],
        true
    );
    let get_repository = http_response(restarted_port, "GET", "/_snapshot/dev-repo", None);
    assert_eq!(get_repository["status"], 200);
    assert_eq!(get_repository["body"]["dev-repo"]["type"], "fs");
    assert_eq!(get_repository["body"]["dev-repo"]["verified"], true);

    let snapshot = http_response(
        restarted_port,
        "PUT",
        "/_snapshot/dev-repo/after-crash",
        Some(br#"{}"#),
    );
    assert_eq!(snapshot["status"], 200);
    assert_eq!(snapshot["body"]["snapshot"]["snapshot"], "after-crash");
    assert_eq!(
        snapshot["body"]["snapshot"]["indices"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(Value::as_str)
            .collect::<Vec<_>>(),
        vec!["snapshot-restore-crash-it"]
    );

    let restore = http_response(
        restarted_port,
        "POST",
        "/_snapshot/dev-repo/after-crash/_restore?wait_for_completion=true",
        Some(br#"{}"#),
    );
    assert_eq!(restore["status"], 200);
    assert_eq!(restore["body"]["restore"]["snapshot"], "after-crash");
    assert_eq!(restore["body"]["restore"]["state"], "SUCCESS");
    assert_eq!(
        restore["body"]["restore"]["indices"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(Value::as_str)
            .collect::<Vec<_>>(),
        vec!["snapshot-restore-crash-it"]
    );

    let orphan_tmp = data_path
        .join("snapshots")
        .join("dev-repo")
        .join("orphan.tmp");
    fs::create_dir_all(&orphan_tmp).unwrap();
    fs::write(orphan_tmp.join("stale-blob"), b"stale").unwrap();

    let cleanup = http_response(
        restarted_port,
        "POST",
        "/_snapshot/dev-repo/_cleanup",
        Some(br#"{}"#),
    );
    assert_eq!(cleanup["status"], 200);
    assert_eq!(cleanup["body"]["results"]["deleted_blobs"], 1);
    assert!(
        cleanup["body"]["results"]["deleted_bytes"]
            .as_u64()
            .unwrap()
            >= 5
    );
    assert!(!orphan_tmp.exists());

    let delete = http_response(
        restarted_port,
        "DELETE",
        "/_snapshot/dev-repo/after-crash",
        None,
    );
    assert_eq!(delete["status"], 200);
    assert_eq!(delete["body"]["acknowledged"], true);
    let deleted_restore = http_response(
        restarted_port,
        "POST",
        "/_snapshot/dev-repo/after-crash/_restore?wait_for_completion=true",
        Some(br#"{}"#),
    );
    assert_eq!(deleted_restore["status"], 404);
    assert_eq!(
        deleted_restore["body"]["error"]["type"],
        "snapshot_missing_exception"
    );

    terminate_child(&restarted);
    let status = wait_for_child_exit(&mut restarted);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_snapshot_restore_fails_closed_for_missing_and_corrupt_metadata() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    let data_path = root.join("data");
    fs::create_dir_all(&data_path).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-snapshot-corruption")
        .arg("--path.data")
        .arg(&data_path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);

    let repository = http_response(
        port,
        "PUT",
        "/_snapshot/dev-repo",
        Some(br#"{"type":"fs","settings":{"location":"dev-repo"}}"#),
    );
    assert_eq!(repository["status"], 200);
    let verify_repository =
        http_response(port, "POST", "/_snapshot/dev-repo/_verify", Some(br#"{}"#));
    assert_eq!(verify_repository["status"], 200);

    let create = http_response(
        port,
        "PUT",
        "/snapshot-corruption-it",
        Some(br#"{"mappings":{"properties":{"message":{"type":"text"}}}}"#),
    );
    assert_eq!(create["status"], 200);
    let indexed = http_response(
        port,
        "PUT",
        "/snapshot-corruption-it/_doc/1?refresh=true",
        Some(br#"{"message":"before snapshot corruption"}"#),
    );
    assert_eq!(indexed["status"], 201);

    for snapshot in [
        "missing-metadata",
        "corrupt-metadata",
        "missing-shard-manifest",
        "checksum-mismatch",
        "incompatible-mapping",
    ] {
        let created = http_response(
            port,
            "PUT",
            &format!("/_snapshot/dev-repo/{snapshot}"),
            Some(br#"{}"#),
        );
        assert_eq!(created["status"], 200);
    }

    let missing_manifest = data_path
        .join("snapshots")
        .join("dev-repo")
        .join("missing-metadata")
        .join("cluster-state.json");
    fs::remove_file(&missing_manifest).unwrap();
    let missing_restore = http_response(
        port,
        "POST",
        "/_snapshot/dev-repo/missing-metadata/_restore",
        Some(br#"{}"#),
    );
    assert_eq!(missing_restore["status"], 404);
    assert_eq!(
        missing_restore["body"]["error"]["type"],
        "snapshot_missing_exception"
    );

    let corrupt_manifest = data_path
        .join("snapshots")
        .join("dev-repo")
        .join("corrupt-metadata")
        .join("cluster-state.json");
    fs::write(&corrupt_manifest, b"{not json").unwrap();
    let corrupt_restore = http_response(
        port,
        "POST",
        "/_snapshot/dev-repo/corrupt-metadata/_restore",
        Some(br#"{}"#),
    );
    assert_eq!(corrupt_restore["status"], 500);
    assert_eq!(
        corrupt_restore["body"]["error"]["type"],
        "snapshot_exception"
    );

    let missing_shard_manifest = data_path
        .join("snapshots")
        .join("dev-repo")
        .join("missing-shard-manifest")
        .join("shards")
        .join("snapshot-corruption-it")
        .join("0")
        .join(SHARD_MANIFEST_FILE_NAME);
    fs::remove_file(&missing_shard_manifest).unwrap();
    let missing_shard_restore = http_response(
        port,
        "POST",
        "/_snapshot/dev-repo/missing-shard-manifest/_restore",
        Some(br#"{}"#),
    );
    assert_eq!(missing_shard_restore["status"], 500);
    assert_eq!(
        missing_shard_restore["body"]["error"]["type"],
        "engine_exception"
    );
    assert!(missing_shard_restore["body"]["error"]["reason"]
        .as_str()
        .unwrap()
        .contains("failed to read shard manifest"));

    let checksum_manifest = data_path
        .join("snapshots")
        .join("dev-repo")
        .join("checksum-mismatch")
        .join("shards")
        .join("snapshot-corruption-it")
        .join("0")
        .join(SHARD_MANIFEST_FILE_NAME);
    let mut checksum_envelope: Value =
        serde_json::from_slice(&fs::read(&checksum_manifest).unwrap()).unwrap();
    checksum_envelope["checksum"] = serde_json::json!(0_u64);
    fs::write(
        &checksum_manifest,
        serde_json::to_vec_pretty(&checksum_envelope).unwrap(),
    )
    .unwrap();
    let checksum_restore = http_response(
        port,
        "POST",
        "/_snapshot/dev-repo/checksum-mismatch/_restore",
        Some(br#"{}"#),
    );
    assert_eq!(checksum_restore["status"], 500);
    assert_eq!(
        checksum_restore["body"]["error"]["type"],
        "engine_exception"
    );
    assert!(checksum_restore["body"]["error"]["reason"]
        .as_str()
        .unwrap()
        .contains("checksum mismatch"));

    let incompatible_cluster_state = data_path
        .join("snapshots")
        .join("dev-repo")
        .join("incompatible-mapping")
        .join("cluster-state.json");
    let mut incompatible_state: Value =
        serde_json::from_slice(&fs::read(&incompatible_cluster_state).unwrap()).unwrap();
    incompatible_state["indices"]["snapshot-corruption-it"]["mappings"]["properties"]["message"]
        ["type"] = serde_json::json!("keyword");
    fs::write(
        &incompatible_cluster_state,
        serde_json::to_vec_pretty(&incompatible_state).unwrap(),
    )
    .unwrap();
    let incompatible_restore = http_response(
        port,
        "POST",
        "/_snapshot/dev-repo/incompatible-mapping/_restore",
        Some(br#"{}"#),
    );
    assert_eq!(incompatible_restore["status"], 400);
    assert_eq!(
        incompatible_restore["body"]["error"]["type"],
        "illegal_argument_exception"
    );
    assert!(incompatible_restore["body"]["error"]["reason"]
        .as_str()
        .unwrap()
        .contains("schema hash"));

    terminate_child(&child);
    let status = wait_for_child_exit(&mut child);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_snapshot_restore_rejects_stale_metadata_after_restart() {
    fn spawn_daemon(
        binary: &Path,
        data_path: &Path,
    ) -> (Child, BufReader<std::process::ChildStderr>, u16) {
        let mut child = Command::new(binary)
            .arg("--http.host")
            .arg("127.0.0.1")
            .arg("--http.port")
            .arg("0")
            .arg("--transport.host")
            .arg("127.0.0.1")
            .arg("--transport.port")
            .arg(free_port().to_string())
            .arg("--cluster.name")
            .arg("steel-dev-snapshot-stale-metadata")
            .arg("--path.data")
            .arg(data_path)
            .stdout(Stdio::null())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        let stderr = child.stderr.take().unwrap();
        let mut reader = BufReader::new(stderr);
        let port = read_reported_http_port(&mut reader);
        (child, reader, port)
    }

    let binary = os_node_binary();
    let root = unique_work_dir();
    let data_path = root.join("data");
    fs::create_dir_all(&data_path).unwrap();

    let (mut child, _stderr, port) = spawn_daemon(&binary, &data_path);
    let request = |port: u16, method: &str, path: &str, body: Option<&[u8]>| {
        try_http_json(port, method, path, body)
            .unwrap_or_else(|error| panic!("{method} {path} failed: {error}"))
    };

    let repository = request(
        port,
        "PUT",
        "/_snapshot/dev-repo",
        Some(br#"{"type":"fs","settings":{"location":"dev-repo"}}"#),
    );
    assert_eq!(repository["status"], 200);
    let verify_repository = request(port, "POST", "/_snapshot/dev-repo/_verify", Some(br#"{}"#));
    assert_eq!(verify_repository["status"], 200);
    let create = request(
        port,
        "PUT",
        "/snapshot-stale-it",
        Some(br#"{"mappings":{"properties":{"message":{"type":"text"}}}}"#),
    );
    assert_eq!(create["status"], 200);
    let indexed = request(
        port,
        "PUT",
        "/snapshot-stale-it/_doc/1?refresh=true",
        Some(br#"{"message":"before stale metadata"}"#),
    );
    assert_eq!(indexed["status"], 201);

    for snapshot in [
        "old-format",
        "foreign-cluster",
        "divergent-index-metadata",
        "replayed-delete",
        "replayed-cleanup",
    ] {
        let created = request(
            port,
            "PUT",
            &format!("/_snapshot/dev-repo/{snapshot}"),
            Some(br#"{}"#),
        );
        assert_eq!(created["status"], 200);
    }

    let snapshot_root = data_path.join("snapshots").join("dev-repo");
    let mutate_snapshot_manifest = |snapshot: &str, mutate: fn(&mut Value)| {
        let path = snapshot_root.join(snapshot).join("cluster-state.json");
        let mut value: Value = serde_json::from_slice(&fs::read(&path).unwrap()).unwrap();
        mutate(&mut value);
        fs::write(&path, serde_json::to_vec_pretty(&value).unwrap()).unwrap();
    };
    mutate_snapshot_manifest("old-format", |value| {
        value["metadata_format_version"] = serde_json::json!(0_u64);
    });
    mutate_snapshot_manifest("foreign-cluster", |value| {
        value["cluster_uuid"] = serde_json::json!("foreign-cluster-uuid");
    });
    mutate_snapshot_manifest("divergent-index-metadata", |value| {
        value["indices"]["snapshot-stale-it"]["mappings"]["properties"]["message"]["type"] =
            serde_json::json!("keyword");
    });
    mutate_snapshot_manifest("replayed-delete", |value| {
        value["snapshot_state"] = serde_json::json!("DELETED");
    });
    mutate_snapshot_manifest("replayed-cleanup", |value| {
        value["cleanup_state"] = serde_json::json!("IN_PROGRESS");
    });

    terminate_child(&child);
    let status = wait_for_child_exit(&mut child);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    let (mut restarted, _restarted_stderr, restarted_port) = spawn_daemon(&binary, &data_path);
    let old_format = request(
        restarted_port,
        "POST",
        "/_snapshot/dev-repo/old-format/_restore",
        Some(br#"{}"#),
    );
    assert_eq!(old_format["status"], 400);
    assert_eq!(
        old_format["body"]["error"]["type"],
        "snapshot_restore_exception"
    );
    assert!(old_format["body"]["error"]["reason"]
        .as_str()
        .unwrap()
        .contains("metadata format version"));

    let foreign_cluster = request(
        restarted_port,
        "POST",
        "/_snapshot/dev-repo/foreign-cluster/_restore",
        Some(br#"{}"#),
    );
    assert_eq!(foreign_cluster["status"], 400);
    assert_eq!(
        foreign_cluster["body"]["error"]["type"],
        "snapshot_restore_exception"
    );
    assert!(foreign_cluster["body"]["error"]["reason"]
        .as_str()
        .unwrap()
        .contains("cluster uuid"));

    let divergent = request(
        restarted_port,
        "POST",
        "/_snapshot/dev-repo/divergent-index-metadata/_restore",
        Some(br#"{}"#),
    );
    assert_eq!(divergent["status"], 400);
    assert_eq!(
        divergent["body"]["error"]["type"],
        "illegal_argument_exception"
    );
    assert!(divergent["body"]["error"]["reason"]
        .as_str()
        .unwrap()
        .contains("schema hash"));

    for snapshot in ["replayed-delete", "replayed-cleanup"] {
        let restore = request(
            restarted_port,
            "POST",
            &format!("/_snapshot/dev-repo/{snapshot}/_restore"),
            Some(br#"{}"#),
        );
        assert_eq!(restore["status"], 409, "snapshot {snapshot}");
        assert_eq!(
            restore["body"]["error"]["type"],
            "snapshot_restore_exception"
        );
        assert!(restore["body"]["error"]["reason"]
            .as_str()
            .unwrap()
            .contains("replayed"));
    }

    terminate_child(&restarted);
    let status = wait_for_child_exit(&mut restarted);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_reports_corrupt_shard_recovery_as_red_health_and_allocation_failure() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    let data_path = root.join("data");
    fs::create_dir_all(&data_path).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-corrupt")
        .arg("--path.data")
        .arg(&data_path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);

    assert_eq!(
        http_response(
            port,
            "PUT",
            "/corrupt-it",
            Some(
                br#"{
                    "settings": { "index": { "number_of_shards": 1, "number_of_replicas": 0 } },
                    "mappings": { "properties": { "message": { "type": "text" } } }
                }"#,
            ),
        )["status"],
        200
    );
    assert_eq!(
        http_response(
            port,
            "PUT",
            "/corrupt-it/_doc/1?refresh=true",
            Some(br#"{"message":"before corruption"}"#),
        )["status"],
        201
    );

    terminate_child(&child);
    let status = wait_for_child_exit(&mut child);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    fs::write(
        data_path
            .join("shards")
            .join("corrupt-it")
            .join("0")
            .join("steelsearch-operations.jsonl"),
        b"{not-json}\n",
    )
    .unwrap();

    let mut restarted = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-corrupt")
        .arg("--path.data")
        .arg(&data_path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = restarted.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let restarted_port = read_reported_http_port(&mut reader);

    let health = http_response(restarted_port, "GET", "/_cluster/health", None);
    assert_eq!(health["status"], 200);
    assert_eq!(health["body"]["status"], "red");
    assert_eq!(health["body"]["active_primary_shards"], 0);
    assert_eq!(health["body"]["unassigned_shards"], 1);

    let allocation = http_response(
        restarted_port,
        "GET",
        "/_cluster/allocation/explain",
        Some(br#"{"index":"corrupt-it","shard":0,"primary":true}"#),
    );
    assert_eq!(allocation["status"], 200);
    assert_eq!(allocation["body"]["index"], "corrupt-it");
    assert_eq!(allocation["body"]["current_state"], "unassigned");
    assert_eq!(allocation["body"]["can_allocate"], "no");
    assert_eq!(
        allocation["body"]["unassigned_info"]["reason"],
        "ALLOCATION_FAILED"
    );
    assert!(allocation["body"]["unassigned_info"]["details"]
        .as_str()
        .unwrap()
        .contains("failed to parse operation log"));

    let search = http_response(restarted_port, "GET", "/corrupt-it/_search", None);
    assert_eq!(search["status"], 404);

    terminate_child(&restarted);
    let status = wait_for_child_exit(&mut restarted);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_sigterm_during_paused_flush_restarts_fail_closed() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    let data_path = root.join("data");
    fs::create_dir_all(&data_path).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-flush-crash")
        .arg("--path.data")
        .arg(&data_path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);

    let create = http_response(port, "PUT", "/flush-crash-it", Some(br#"{}"#));
    assert_eq!(create["status"], 200);
    let write = http_response(
        port,
        "PUT",
        "/flush-crash-it/_doc/1",
        Some(br#"{"message":"pending flush"}"#),
    );
    assert_eq!(write["status"], 201);
    assert_eq!(search_total(port, "/flush-crash-it/_search"), 0);

    let paused_flush = thread::spawn(move || {
        let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
        stream
            .write_all(
                format!(
                    "POST /flush-crash-it/_flush?_steelsearch_pause_before_flush_millis=5000 HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{{}}"
                )
                .as_bytes(),
            )
            .unwrap();
        let mut response = Vec::new();
        let _ = stream.read_to_end(&mut response);
        response
    });
    thread::sleep(Duration::from_millis(100));

    terminate_child(&child);
    let status = wait_for_child_exit(&mut child);
    assert!(status.success(), "daemon did not exit cleanly: {status}");
    let _ = paused_flush.join().unwrap();

    let mut restarted = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-flush-crash")
        .arg("--path.data")
        .arg(&data_path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = restarted.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let restarted_port = read_reported_http_port(&mut reader);

    let restored_index = http_response(restarted_port, "GET", "/flush-crash-it", None);
    assert_eq!(restored_index["status"], 200);
    assert_eq!(search_total(restarted_port, "/flush-crash-it/_search"), 1);

    terminate_child(&restarted);
    let status = wait_for_child_exit(&mut restarted);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_sigterm_during_paused_snapshot_restarts_fail_closed() {
    let binary = os_node_binary();
    let root = unique_work_dir();
    let data_path = root.join("data");
    fs::create_dir_all(&data_path).unwrap();

    let mut child = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-snapshot-crash")
        .arg("--path.data")
        .arg(&data_path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = child.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let port = read_reported_http_port(&mut reader);

    let create = http_response(port, "PUT", "/snapshot-crash-it", Some(br#"{}"#));
    assert_eq!(create["status"], 200);
    let indexed = http_response(
        port,
        "PUT",
        "/snapshot-crash-it/_doc/1?refresh=true",
        Some(br#"{"message":"survives snapshot restore after crash"}"#),
    );
    assert_eq!(indexed["status"], 201);
    assert_eq!(search_total(port, "/snapshot-crash-it/_search"), 1);

    let create_snapshot = http_response(
        port,
        "PUT",
        "/_snapshot/dev-repo/before-crash",
        Some(br#"{}"#),
    );
    assert_eq!(create_snapshot["status"], 200);

    let snapshot_status = http_response(
        port,
        "GET",
        "/_snapshot/dev-repo/before-crash/_status",
        None,
    );
    assert_eq!(snapshot_status["status"], 200);
    assert_eq!(
        snapshot_status["body"]["snapshots"][0]["snapshot"],
        "before-crash"
    );

    let paused_snapshot = thread::spawn(move || {
        let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
        stream
            .write_all(
                format!(
                    "PUT /_snapshot/dev-repo/during-crash?_steelsearch_pause_before_snapshot_millis=5000 HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{{}}"
                )
                .as_bytes(),
            )
            .unwrap();
        let mut response = Vec::new();
        let _ = stream.read_to_end(&mut response);
        response
    });
    thread::sleep(Duration::from_millis(100));

    terminate_child(&child);
    let status = wait_for_child_exit(&mut child);
    assert!(status.success(), "daemon did not exit cleanly: {status}");
    let _ = paused_snapshot.join().unwrap();

    let mut restarted = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-snapshot-crash")
        .arg("--path.data")
        .arg(&data_path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = restarted.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let restarted_port = read_reported_http_port(&mut reader);

    let restored_index = http_response(restarted_port, "GET", "/snapshot-crash-it", None);
    assert_eq!(restored_index["status"], 200);
    assert_eq!(
        search_total(restarted_port, "/snapshot-crash-it/_search"),
        1
    );
    let restarted_status = http_response(
        restarted_port,
        "GET",
        "/_snapshot/dev-repo/during-crash/_status",
        None,
    );
    assert_eq!(restarted_status["status"], 200);
    assert_eq!(
        restarted_status["body"]["snapshots"][0]["repository"],
        "dev-repo"
    );

    let paused_status = thread::spawn(move || {
        let mut stream = TcpStream::connect(("127.0.0.1", restarted_port)).unwrap();
        stream
            .write_all(
                format!(
                    "GET /_snapshot/dev-repo/snap-1/_status?_steelsearch_pause_before_snapshot_millis=5000 HTTP/1.1\r\nHost: 127.0.0.1:{restarted_port}\r\nConnection: close\r\n\r\n"
                )
                .as_bytes(),
            )
            .unwrap();
        let mut response = Vec::new();
        let _ = stream.read_to_end(&mut response);
        response
    });
    thread::sleep(Duration::from_millis(100));

    terminate_child(&restarted);
    let status = wait_for_child_exit(&mut restarted);
    assert!(status.success(), "daemon did not exit cleanly: {status}");
    let _ = paused_status.join().unwrap();

    fs::remove_file(data_path.join("cluster-state.json")).unwrap();
    fs::remove_dir_all(data_path.join("shards")).unwrap();

    let mut final_restart = Command::new(&binary)
        .arg("--http.host")
        .arg("127.0.0.1")
        .arg("--http.port")
        .arg("0")
        .arg("--transport.host")
        .arg("127.0.0.1")
        .arg("--transport.port")
        .arg(free_port().to_string())
        .arg("--cluster.name")
        .arg("steel-dev-snapshot-crash")
        .arg("--path.data")
        .arg(&data_path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let stderr = final_restart.stderr.take().unwrap();
    let mut reader = BufReader::new(stderr);
    let final_port = read_reported_http_port(&mut reader);

    let missing_index = http_response(final_port, "GET", "/snapshot-crash-it", None);
    assert_eq!(missing_index["status"], 404);
    let snapshot_status = http_response(
        final_port,
        "GET",
        "/_snapshot/dev-repo/before-crash/_status",
        None,
    );
    assert_eq!(snapshot_status["status"], 200);
    assert_eq!(
        snapshot_status["body"]["snapshots"][0]["indices"][0],
        "snapshot-crash-it"
    );
    let restore = http_response(
        final_port,
        "POST",
        "/_snapshot/dev-repo/before-crash/_restore",
        Some(br#"{}"#),
    );
    assert_eq!(restore["status"], 200);
    assert_eq!(
        restore["body"]["restore"]["indices"][0],
        "snapshot-crash-it"
    );
    let final_index = http_response(final_port, "GET", "/snapshot-crash-it", None);
    assert_eq!(final_index["status"], 200);
    assert_eq!(search_total(final_port, "/snapshot-crash-it/_search"), 1);
    let final_doc = http_response(final_port, "GET", "/snapshot-crash-it/_doc/1", None);
    assert_eq!(final_doc["status"], 200);
    assert_eq!(final_doc["body"]["found"], true);
    assert_eq!(
        final_doc["body"]["_source"]["message"],
        "survives snapshot restore after crash"
    );

    terminate_child(&final_restart);
    let status = wait_for_child_exit(&mut final_restart);
    assert!(status.success(), "daemon did not exit cleanly: {status}");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_kill_during_paused_snapshot_mutations_restarts_fail_closed() {
    fn spawn_daemon(
        binary: &Path,
        data_path: &Path,
    ) -> (Child, BufReader<std::process::ChildStderr>, u16) {
        let mut child = Command::new(binary)
            .arg("--http.host")
            .arg("127.0.0.1")
            .arg("--http.port")
            .arg("0")
            .arg("--transport.host")
            .arg("127.0.0.1")
            .arg("--transport.port")
            .arg(free_port().to_string())
            .arg("--cluster.name")
            .arg("steel-dev-snapshot-mutation-crash")
            .arg("--path.data")
            .arg(data_path)
            .stdout(Stdio::null())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        let stderr = child.stderr.take().unwrap();
        let mut reader = BufReader::new(stderr);
        let port = read_reported_http_port(&mut reader);
        (child, reader, port)
    }

    fn prepare_snapshot(port: u16) {
        let create = wait_http_response(port, "PUT", "/snapshot-mutation-crash-it", Some(br#"{}"#));
        assert_eq!(create["status"], 200);
        let indexed = wait_http_response(
            port,
            "PUT",
            "/snapshot-mutation-crash-it/_doc/1?refresh=true",
            Some(br#"{"message":"snapshot mutation crash fixture"}"#),
        );
        assert_eq!(indexed["status"], 201);
        let snapshot = wait_http_response(
            port,
            "PUT",
            "/_snapshot/dev-repo/before-mutation-crash",
            Some(br#"{}"#),
        );
        assert_eq!(snapshot["status"], 200);
    }

    fn paused_request(port: u16, request: String) -> thread::JoinHandle<Vec<u8>> {
        thread::spawn(move || {
            let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
            stream.write_all(request.as_bytes()).unwrap();
            let mut response = Vec::new();
            let _ = stream.read_to_end(&mut response);
            response
        })
    }

    let binary = os_node_binary();

    for phase in ["restore", "delete", "cleanup"] {
        let root = unique_work_dir();
        let data_path = root.join("data");
        fs::create_dir_all(&data_path).unwrap();
        let (mut child, _stderr, port) = spawn_daemon(&binary, &data_path);
        prepare_snapshot(port);

        let orphan_tmp = data_path
            .join("snapshots")
            .join("dev-repo")
            .join("orphan.tmp");
        fs::create_dir_all(&orphan_tmp).unwrap();
        fs::write(orphan_tmp.join("stale-blob"), b"stale").unwrap();

        let request = match phase {
            "restore" => format!(
                "POST /_snapshot/dev-repo/before-mutation-crash/_restore?_steelsearch_pause_before_snapshot_millis=5000 HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{{}}"
            ),
            "delete" => format!(
                "DELETE /_snapshot/dev-repo/before-mutation-crash?_steelsearch_pause_before_snapshot_millis=5000 HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
            ),
            "cleanup" => format!(
                "POST /_snapshot/dev-repo/_cleanup?_steelsearch_pause_before_snapshot_millis=5000 HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{{}}"
            ),
            _ => unreachable!(),
        };
        let paused = paused_request(port, request);
        thread::sleep(Duration::from_millis(100));

        child.kill().unwrap();
        let status = wait_for_child_exit(&mut child);
        assert!(
            !status.success(),
            "daemon unexpectedly exited cleanly during forced {phase} kill: {status}"
        );
        let _ = paused.join().unwrap();

        let (mut restarted, _restarted_stderr, restarted_port) = spawn_daemon(&binary, &data_path);
        let snapshot_status = wait_http_response(
            restarted_port,
            "GET",
            "/_snapshot/dev-repo/before-mutation-crash/_status",
            None,
        );
        assert_eq!(snapshot_status["status"], 200, "phase {phase}");
        assert_eq!(
            snapshot_status["body"]["snapshots"][0]["snapshot"], "before-mutation-crash",
            "phase {phase}"
        );

        let restore = wait_http_response(
            restarted_port,
            "POST",
            "/_snapshot/dev-repo/before-mutation-crash/_restore",
            Some(br#"{}"#),
        );
        assert_eq!(restore["status"], 200, "phase {phase}");
        assert_eq!(
            search_total(restarted_port, "/snapshot-mutation-crash-it/_search"),
            1,
            "phase {phase}"
        );

        if phase == "cleanup" {
            assert!(
                orphan_tmp.exists(),
                "cleanup phase should leave paused temp directory for restart cleanup"
            );
            let cleanup = wait_http_response(
                restarted_port,
                "POST",
                "/_snapshot/dev-repo/_cleanup",
                Some(br#"{}"#),
            );
            assert_eq!(cleanup["status"], 200);
            assert_eq!(cleanup["body"]["results"]["deleted_blobs"], 1);
            assert!(!orphan_tmp.exists());
        }

        terminate_child(&restarted);
        let status = wait_for_child_exit(&mut restarted);
        assert!(status.success(), "daemon did not exit cleanly: {status}");

        let _ = fs::remove_dir_all(root);
    }
}

#[test]
fn daemon_sigterm_during_peer_recovery_fault_injection_phases_restarts() {
    let binary = os_node_binary();
    let root = unique_work_dir();

    for phase in ["start", "chunk", "translog", "finalize"] {
        let data_path = root.join(format!("data-{phase}"));
        fs::create_dir_all(&data_path).unwrap();

        let mut child = Command::new(&binary)
            .arg("--http.host")
            .arg("127.0.0.1")
            .arg("--http.port")
            .arg("0")
            .arg("--transport.host")
            .arg("127.0.0.1")
            .arg("--transport.port")
            .arg(free_port().to_string())
            .arg("--cluster.name")
            .arg(format!("steel-dev-peer-recovery-{phase}"))
            .arg("--path.data")
            .arg(&data_path)
            .stdout(Stdio::null())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        let stderr = child.stderr.take().unwrap();
        let mut reader = BufReader::new(stderr);
        let port = read_reported_http_port(&mut reader);

        let create = http_response(port, "PUT", "/peer-recovery-crash-it", Some(br#"{}"#));
        assert_eq!(create["status"], 200);

        let paused_recovery = thread::spawn(move || {
            let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
            stream
                .write_all(
                    format!(
                        "POST /_steelsearch/dev/peer_recovery/{phase}?_steelsearch_pause_peer_recovery_millis=1000 HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{{}}"
                    )
                    .as_bytes(),
                )
                .unwrap();
            let mut response = Vec::new();
            let _ = stream.read_to_end(&mut response);
            response
        });
        thread::sleep(Duration::from_millis(100));

        terminate_child(&child);
        let status = wait_for_child_exit(&mut child);
        assert!(status.success(), "daemon did not exit cleanly: {status}");
        let _ = paused_recovery.join().unwrap();

        let mut restarted = Command::new(&binary)
            .arg("--http.host")
            .arg("127.0.0.1")
            .arg("--http.port")
            .arg("0")
            .arg("--transport.host")
            .arg("127.0.0.1")
            .arg("--transport.port")
            .arg(free_port().to_string())
            .arg("--cluster.name")
            .arg(format!("steel-dev-peer-recovery-{phase}"))
            .arg("--path.data")
            .arg(&data_path)
            .stdout(Stdio::null())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        let stderr = restarted.stderr.take().unwrap();
        let mut reader = BufReader::new(stderr);
        let restarted_port = read_reported_http_port(&mut reader);

        let restored_index = http_response(restarted_port, "GET", "/peer-recovery-crash-it", None);
        assert_eq!(restored_index["status"], 200, "phase {phase}");
        let hook = http_response(
            restarted_port,
            "POST",
            &format!("/_steelsearch/dev/peer_recovery/{phase}"),
            Some(b"{}"),
        );
        assert_eq!(hook["status"], 200, "phase {phase}");
        assert_eq!(hook["body"]["phase"], phase);

        terminate_child(&restarted);
        let status = wait_for_child_exit(&mut restarted);
        assert!(status.success(), "daemon did not exit cleanly: {status}");
    }

    let _ = fs::remove_dir_all(root);
}

#[test]
fn daemon_sigterm_during_relocation_fault_injection_phases_restarts() {
    let binary = os_node_binary();
    let root = unique_work_dir();

    for phase in ["source", "target", "checksum"] {
        let data_path = root.join(format!("data-relocation-{phase}"));
        fs::create_dir_all(&data_path).unwrap();

        let mut child = Command::new(&binary)
            .arg("--http.host")
            .arg("127.0.0.1")
            .arg("--http.port")
            .arg("0")
            .arg("--transport.host")
            .arg("127.0.0.1")
            .arg("--transport.port")
            .arg(free_port().to_string())
            .arg("--cluster.name")
            .arg(format!("steel-dev-relocation-{phase}"))
            .arg("--path.data")
            .arg(&data_path)
            .stdout(Stdio::null())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        let stderr = child.stderr.take().unwrap();
        let mut reader = BufReader::new(stderr);
        let port = read_reported_http_port(&mut reader);

        let create = http_response(port, "PUT", "/relocation-crash-it", Some(br#"{}"#));
        assert_eq!(create["status"], 200);

        let paused_relocation = thread::spawn(move || {
            let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
            stream
                .write_all(
                    format!(
                        "POST /_steelsearch/dev/relocation/{phase}?_steelsearch_pause_relocation_millis=1000 HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{{}}"
                    )
                    .as_bytes(),
                )
                .unwrap();
            let mut response = Vec::new();
            let _ = stream.read_to_end(&mut response);
            response
        });
        thread::sleep(Duration::from_millis(100));

        terminate_child(&child);
        let status = wait_for_child_exit(&mut child);
        assert!(status.success(), "daemon did not exit cleanly: {status}");
        let _ = paused_relocation.join().unwrap();

        let mut restarted = Command::new(&binary)
            .arg("--http.host")
            .arg("127.0.0.1")
            .arg("--http.port")
            .arg("0")
            .arg("--transport.host")
            .arg("127.0.0.1")
            .arg("--transport.port")
            .arg(free_port().to_string())
            .arg("--cluster.name")
            .arg(format!("steel-dev-relocation-{phase}"))
            .arg("--path.data")
            .arg(&data_path)
            .stdout(Stdio::null())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        let stderr = restarted.stderr.take().unwrap();
        let mut reader = BufReader::new(stderr);
        let restarted_port = read_reported_http_port(&mut reader);

        let restored_index = http_response(restarted_port, "GET", "/relocation-crash-it", None);
        assert_eq!(restored_index["status"], 200, "phase {phase}");
        let hook = http_response(
            restarted_port,
            "POST",
            &format!("/_steelsearch/dev/relocation/{phase}"),
            Some(b"{}"),
        );
        assert_eq!(hook["status"], 200, "phase {phase}");
        assert_eq!(hook["body"]["phase"], phase);

        terminate_child(&restarted);
        let status = wait_for_child_exit(&mut restarted);
        assert!(status.success(), "daemon did not exit cleanly: {status}");
    }

    let _ = fs::remove_dir_all(root);
}

fn os_node_binary() -> PathBuf {
    if let Some(binary) = std::env::var_os("CARGO_BIN_EXE_steelsearch").map(PathBuf::from) {
        return binary;
    }

    let workspace_root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let repo_debug_binary = workspace_root.join("target/debug/steelsearch");
    let status = Command::new("cargo")
        .arg("build")
        .arg("-p")
        .arg("os-node")
        .arg("--bin")
        .arg("steelsearch")
        .current_dir(&workspace_root)
        .status()
        .expect("failed to invoke cargo build for steelsearch binary");
    assert!(
        status.success(),
        "cargo build for steelsearch binary failed: {status}"
    );
    repo_debug_binary
}

fn unique_work_dir() -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    std::env::temp_dir().join(format!("steelsearch-daemon-it-{nanos}"))
}

fn free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .unwrap()
        .local_addr()
        .unwrap()
        .port()
}

fn terminate_child(child: &Child) {
    let status = Command::new("kill")
        .arg("-TERM")
        .arg(child.id().to_string())
        .status()
        .unwrap();
    assert!(
        status.success(),
        "failed to send SIGTERM to daemon: {status}"
    );
}

fn wait_for_child_exit(child: &mut Child) -> ExitStatus {
    let deadline = Instant::now() + Duration::from_secs(15);
    while Instant::now() < deadline {
        if let Some(status) = child.try_wait().unwrap() {
            return status;
        }
        thread::sleep(Duration::from_millis(25));
    }
    panic!("daemon did not exit before timeout");
}

fn read_reported_http_port<R: BufRead>(reader: &mut R) -> u16 {
    let deadline = Instant::now() + Duration::from_secs(15);
    let prefix = "Steelsearch development daemon listening on http://";
    let mut line = String::new();
    let mut observed = Vec::new();
    while Instant::now() < deadline {
        line.clear();
        match reader.read_line(&mut line) {
            Ok(0) => thread::sleep(Duration::from_millis(25)),
            Ok(_) => {
                let Some(address) = line.trim().strip_prefix(prefix) else {
                    observed.push(line.trim().to_string());
                    continue;
                };
                let Some((_, port)) = address.rsplit_once(':') else {
                    panic!("listening address did not include a port: {address}");
                };
                return port.parse().unwrap();
            }
            Err(error) => panic!("failed to read daemon stderr: {error}"),
        }
    }
    panic!("daemon did not report selected HTTP port; observed stderr: {observed:?}");
}

fn wait_json(port: u16, method: &str, path: &str, body: Option<&[u8]>) -> Value {
    wait_http_response(port, method, path, body)["body"].clone()
}

fn wait_http_response(port: u16, method: &str, path: &str, body: Option<&[u8]>) -> Value {
    let deadline = Instant::now() + Duration::from_secs(15);
    let mut last_error = None;
    while Instant::now() < deadline {
        match try_http_json(port, method, path, body) {
            Ok(value)
                if (200..400).contains(&(value["status"].as_u64().unwrap_or(500) as u16)) =>
            {
                return value;
            }
            Ok(value) => last_error = Some(format!("status {}", value["status"])),
            Err(error) => last_error = Some(error),
        }
        thread::sleep(Duration::from_millis(100));
    }
    panic!("endpoint {method} {path} on port {port} was not ready: {last_error:?}");
}

fn http_json(port: u16, method: &str, path: &str, body: Option<&[u8]>) -> Value {
    try_http_json(port, method, path, body).unwrap()
}

fn http_response(port: u16, method: &str, path: &str, body: Option<&[u8]>) -> Value {
    try_http_json(port, method, path, body).unwrap()
}

fn http_response_with_headers(
    port: u16,
    method: &str,
    path: &str,
    headers: &[(&str, &str)],
    body: Option<&[u8]>,
) -> Value {
    try_http_json_with_headers(port, method, path, headers, body).unwrap()
}

fn assert_opensearch_error(response: &Value, status: u16, error_type: &str, reason: &str) {
    assert_eq!(response["status"], status, "{response}");
    assert_eq!(response["body"]["status"], status, "{response}");
    assert_eq!(response["body"]["error"]["type"], error_type, "{response}");
    assert_eq!(
        response["body"]["error"]["root_cause"][0]["type"],
        error_type,
        "{response}"
    );
    assert_eq!(response["body"]["error"]["reason"], reason, "{response}");
    assert_eq!(response["headers"]["content-type"], "application/json", "{response}");
}

fn assert_opensearch_error_shape(response: &Value, status: u16, error_type: &str) {
    assert_eq!(response["status"], status, "{response}");
    assert_eq!(response["body"]["status"], status, "{response}");
    assert_eq!(response["body"]["error"]["type"], error_type, "{response}");
    assert_eq!(
        response["body"]["error"]["root_cause"][0]["type"],
        error_type,
        "{response}"
    );
    assert!(response["body"]["error"]["reason"].as_str().is_some());
    assert!(response["body"]["error"]["root_cause"][0]["reason"]
        .as_str()
        .is_some());
    assert_eq!(response["headers"]["content-type"], "application/json", "{response}");
}

fn assert_refresh_success(response: &Value) {
    assert_eq!(response["status"], 200);
    assert_eq!(response["body"]["_shards"]["total"], 1);
    assert_eq!(response["body"]["_shards"]["successful"], 1);
    assert_eq!(response["body"]["_shards"]["failed"], 0);
}

fn search_total(port: u16, path: &str) -> i64 {
    let response = http_response(port, "POST", path, Some(br#"{"query":{"match_all":{}}}"#));
    assert_eq!(response["status"], 200);
    response["body"]["hits"]["total"]["value"].as_i64().unwrap()
}

fn bulk_retry_checksum(body: &Value) -> String {
    body["hits"]["hits"]
        .as_array()
        .unwrap()
        .iter()
        .map(|hit| {
            let source = &hit["_source"];
            format!(
                "{}:{}:{}:{}:{}",
                hit["_id"].as_str().unwrap(),
                source["message"].as_str().unwrap(),
                source["service"].as_str().unwrap(),
                source["ordinal"].as_i64().unwrap(),
                source["counter"].as_i64().unwrap()
            )
        })
        .collect::<Vec<_>>()
        .join("|")
}

fn search_ids(port: u16, method: &str, path: &str, body: &[u8]) -> Vec<String> {
    let response = http_response(port, method, path, Some(body));
    assert_eq!(response["status"], 200);
    response["body"]["hits"]["hits"]
        .as_array()
        .unwrap()
        .iter()
        .map(|hit| hit["_id"].as_str().unwrap().to_string())
        .collect()
}

fn try_http_json(
    port: u16,
    method: &str,
    path: &str,
    body: Option<&[u8]>,
) -> Result<Value, String> {
    try_http_json_with_headers(port, method, path, &[], body)
}

fn try_http_json_with_headers(
    port: u16,
    method: &str,
    path: &str,
    headers: &[(&str, &str)],
    body: Option<&[u8]>,
) -> Result<Value, String> {
    let body = body.unwrap_or_default();
    let mut stream = TcpStream::connect(("127.0.0.1", port)).map_err(|error| error.to_string())?;
    let request = format!(
        "{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n",
        body.len()
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|error| error.to_string())?;
    for (name, value) in headers {
        write!(stream, "{name}: {value}\r\n").map_err(|error| error.to_string())?;
    }
    stream
        .write_all(b"\r\n")
        .and_then(|_| stream.write_all(body))
        .map_err(|error| error.to_string())?;
    let mut response = Vec::new();
    stream
        .read_to_end(&mut response)
        .map_err(|error| error.to_string())?;
    decode_http_response(&response)
}

fn decode_http_response(response: &[u8]) -> Result<Value, String> {
    let text = String::from_utf8_lossy(response);
    let (head, body) = text
        .split_once("\r\n\r\n")
        .ok_or_else(|| "missing HTTP response separator".to_string())?;
    let status = head
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|status| status.parse::<u16>().ok())
        .ok_or_else(|| format!("missing HTTP status in {head}"))?;
    let headers = head
        .lines()
        .skip(1)
        .filter_map(|line| line.split_once(':'))
        .map(|(name, value)| {
            (
                name.to_ascii_lowercase(),
                serde_json::json!(value.trim().to_string()),
            )
        })
        .collect::<serde_json::Map<_, _>>();
    let body_text = body.to_string();
    let body_json = if body.trim().is_empty() {
        serde_json::json!({})
    } else {
        serde_json::from_str(body).map_err(|error| error.to_string())?
    };
    Ok(serde_json::json!({
        "status": status,
        "headers": headers,
        "body": body_json,
        "body_text": body_text
    }))
}
