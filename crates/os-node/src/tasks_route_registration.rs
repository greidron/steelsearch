//! Workspace-visible route-registration anchors for bounded `/_tasks` parity work.

pub const TASKS_ROUTE_FAMILY: &str = "tasks_registry_readback";
pub const TASKS_LIST_ROUTE_PATH: &str = "/_tasks";
pub const TASKS_GET_ROUTE_PATH: &str = "/_tasks/{task_id}";
pub const TASKS_CANCEL_ROUTE_PATH: &str = "/_tasks/_cancel";

pub const TASKS_ENVELOPE_FIELDS: [&str; 11] = [
    "node",
    "id",
    "type",
    "action",
    "start_time_in_millis",
    "running_time_in_nanos",
    "parent_task_id",
    "cancellable",
    "cancelled",
    "headers",
    "status",
];
pub const TASKS_NODE_FIELDS: [&str; 6] = [
    "name",
    "transport_address",
    "host",
    "ip",
    "roles",
    "attributes",
];
pub const TASKS_ERROR_FIELDS: [&str; 2] = ["error.type", "error.reason"];

pub const TASKS_UNSUPPORTED_PARAMETER_BUCKET: &str = "unsupported task registry parameter";
pub const TASKS_UNKNOWN_TASK_ERROR_TYPE: &str = "resource_not_found_exception";
pub const TASKS_NON_CANCELLABLE_ERROR_TYPE: &str = "illegal_argument_exception";

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BoundedTaskRecord<'a> {
    pub node: &'a str,
    pub id: u64,
    pub task_type: &'a str,
    pub action: &'a str,
    pub start_time_in_millis: u64,
    pub running_time_in_nanos: u64,
    pub cancellable: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TasksRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
    pub hook: TasksRouteInvokeFn,
}

pub fn build_bounded_task_envelope(task: &BoundedTaskRecord<'_>) -> serde_json::Value {
    serde_json::json!({
        "node": task.node,
        "id": task.id,
        "type": task.task_type,
        "action": task.action,
        "start_time_in_millis": task.start_time_in_millis,
        "running_time_in_nanos": task.running_time_in_nanos,
        "cancellable": task.cancellable,
        "cancelled": false,
        "headers": {},
    })
}

pub fn build_tasks_list_response(
    node: &serde_json::Value,
    tasks: &[BoundedTaskRecord<'_>],
) -> serde_json::Value {
    let mut nodes = serde_json::Map::new();
    for task in tasks {
        let node_entry = nodes.entry(task.node.to_string()).or_insert_with(|| {
            let mut seeded = node.clone();
            seeded["tasks"] = serde_json::json!({});
            seeded
        });
        let task_key = format!("{}:{}", task.node, task.id);
        node_entry["tasks"][task_key] = build_bounded_task_envelope(task);
    }
    serde_json::json!({ "nodes": nodes })
}

pub fn build_task_get_response(task: &BoundedTaskRecord<'_>) -> serde_json::Value {
    serde_json::json!({
        "completed": false,
        "task": build_bounded_task_envelope(task),
    })
}

pub fn build_task_cancel_response(task: &BoundedTaskRecord<'_>) -> serde_json::Value {
    let task_key = format!("{}:{}", task.node, task.id);
    serde_json::json!({
        "nodes": {
            task.node: {
                "tasks": {
                    task_key: build_bounded_task_envelope(task)
                }
            }
        },
        "task_failures": [],
        "node_failures": [],
    })
}

fn normalize_bounded_task_value(task: &serde_json::Value) -> serde_json::Value {
    serde_json::json!({
        "node": task.get("node").cloned().unwrap_or(serde_json::Value::Null),
        "id": task.get("id").cloned().unwrap_or(serde_json::Value::Null),
        "action": task.get("action").cloned().unwrap_or(serde_json::Value::Null),
        "cancellable": task.get("cancellable").cloned().unwrap_or(serde_json::Value::Bool(false)),
        "cancelled": task.get("cancelled").cloned().unwrap_or(serde_json::Value::Bool(false)),
        "type": task.get("type").cloned().unwrap_or(serde_json::Value::Null),
        "start_time_in_millis": task
            .get("start_time_in_millis")
            .cloned()
            .unwrap_or(serde_json::Value::Null),
        "running_time_in_nanos": task
            .get("running_time_in_nanos")
            .cloned()
            .unwrap_or(serde_json::Value::Null),
        "parent_task_id": task
            .get("parent_task_id")
            .cloned()
            .unwrap_or_else(|| serde_json::json!("-")),
        "headers": task
            .get("headers")
            .cloned()
            .unwrap_or_else(|| serde_json::json!({})),
        "status": task
            .get("status")
            .cloned()
            .unwrap_or_else(|| serde_json::json!({})),
    })
}

pub fn build_unknown_task_error(task_id: &str) -> serde_json::Value {
    serde_json::json!({
        "error": {
            "type": TASKS_UNKNOWN_TASK_ERROR_TYPE,
            "reason": format!("task [{}] is not tracked by the bounded Steelsearch task registry", task_id),
        },
        "status": 404,
    })
}

pub fn build_non_cancellable_task_error(task_id: &str) -> serde_json::Value {
    serde_json::json!({
        "error": {
            "type": TASKS_NON_CANCELLABLE_ERROR_TYPE,
            "reason": format!("task [{}] is not cancellable in the bounded Steelsearch task registry", task_id),
        },
        "status": 400,
    })
}

pub fn reject_unsupported_tasks_params(params: &[&str]) -> Result<(), &'static str> {
    if params.is_empty() {
        Ok(())
    } else {
        Err(TASKS_UNSUPPORTED_PARAMETER_BUCKET)
    }
}

pub type TasksRouteInvokeFn = fn(&serde_json::Value) -> serde_json::Value;

pub fn invoke_tasks_list_live_route(body: &serde_json::Value) -> serde_json::Value {
    let tasks = body
        .get("tasks")
        .and_then(serde_json::Value::as_array)
        .cloned()
        .unwrap_or_default();
    let node_metadata = body
        .get("node")
        .cloned()
        .unwrap_or_else(|| serde_json::json!({}));
    let nodes_metadata = body
        .get("nodes")
        .and_then(serde_json::Value::as_object)
        .cloned()
        .unwrap_or_default();
    let mut nodes = serde_json::Map::new();
    for task in tasks {
        let normalized = normalize_bounded_task_value(&task);
        let node = normalized["node"].as_str().unwrap_or("unknown");
        let id = normalized["id"].as_u64().unwrap_or_default();
        let task_key = format!("{node}:{id}");
        let node_entry = nodes.entry(node.to_string()).or_insert_with(|| {
            let mut seeded = nodes_metadata
                .get(node)
                .cloned()
                .unwrap_or_else(|| node_metadata.clone());
            seeded["tasks"] = serde_json::json!({});
            seeded
        });
        node_entry["tasks"][task_key] = normalized;
    }
    serde_json::json!({ "nodes": nodes })
}

pub fn invoke_tasks_list_by_parent_live_route(body: &serde_json::Value) -> serde_json::Value {
    let tasks = body
        .get("tasks")
        .and_then(serde_json::Value::as_array)
        .cloned()
        .unwrap_or_default()
        .into_iter()
        .map(|task| {
            let normalized = normalize_bounded_task_value(&task);
            let node = normalized["node"].as_str().unwrap_or("unknown").to_string();
            let id = normalized["id"].as_u64().unwrap_or_default();
            (format!("{node}:{id}"), normalized)
        })
        .collect::<std::collections::BTreeMap<_, _>>();
    let mut parent_rows = serde_json::Map::new();
    for (task_id, task) in &tasks {
        let parent_task_id = task
            .get("parent_task_id")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("-");
        if parent_task_id != "-" && tasks.contains_key(parent_task_id) {
            continue;
        }
        let mut parent = task.clone();
        parent["children"] = serde_json::json!([]);
        parent_rows.insert(task_id.clone(), parent);
    }
    for task in tasks.values() {
        let parent_task_id = task
            .get("parent_task_id")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("-");
        if parent_task_id == "-" || !tasks.contains_key(parent_task_id) {
            continue;
        }
        if let Some(parent) = parent_rows.get_mut(parent_task_id) {
            if !parent["children"].is_array() {
                parent["children"] = serde_json::json!([]);
            }
            parent["children"]
                .as_array_mut()
                .expect("children array initialized")
                .push(task.clone());
        }
    }
    serde_json::json!({ "tasks": parent_rows })
}

pub fn invoke_tasks_list_flat_live_route(body: &serde_json::Value) -> serde_json::Value {
    let tasks = body
        .get("tasks")
        .and_then(serde_json::Value::as_array)
        .cloned()
        .unwrap_or_default()
        .into_iter()
        .map(|task| normalize_bounded_task_value(&task))
        .collect::<Vec<_>>();
    serde_json::json!({ "tasks": tasks })
}

pub fn invoke_tasks_get_live_route(body: &serde_json::Value) -> serde_json::Value {
    let task = body.get("task").unwrap_or(body);
    let completed = task
        .get("completed")
        .and_then(serde_json::Value::as_bool)
        .unwrap_or(false)
        && task.get("response").is_some();
    let mut response = serde_json::json!({
        "completed": false,
        "task": normalize_bounded_task_value(task),
    });
    response["completed"] = serde_json::Value::Bool(completed);
    if let Some(task_response) = task.get("response") {
        response["response"] = task_response.clone();
    }
    response
}

pub fn invoke_tasks_cancel_live_route(body: &serde_json::Value) -> serde_json::Value {
    let task = body.get("task").unwrap_or(body);
    let node_metadata = body
        .get("node")
        .cloned()
        .unwrap_or_else(|| serde_json::json!({}));
    let normalized = normalize_bounded_task_value(task);
    let node = normalized["node"].as_str().unwrap_or("unknown");
    let id = normalized["id"].as_u64().unwrap_or_default();
    let task_key = format!("{node}:{id}");
    serde_json::json!({
        "nodes": {
            node: {
                "name": node_metadata.get("name").cloned().unwrap_or(serde_json::Value::Null),
                "transport_address": node_metadata.get("transport_address").cloned().unwrap_or(serde_json::Value::Null),
                "host": node_metadata.get("host").cloned().unwrap_or(serde_json::Value::Null),
                "ip": node_metadata.get("ip").cloned().unwrap_or(serde_json::Value::Null),
                "roles": node_metadata.get("roles").cloned().unwrap_or(serde_json::json!([])),
                "attributes": node_metadata.get("attributes").cloned().unwrap_or_else(|| serde_json::json!({})),
                "tasks": {
                    task_key: normalized
                }
            }
        },
        "task_failures": [],
        "node_failures": [],
    })
}

pub const TASKS_ROUTE_REGISTRY_TABLE: [TasksRouteRegistryEntry; 3] = [
    TasksRouteRegistryEntry {
        method: "GET",
        path: TASKS_LIST_ROUTE_PATH,
        family: TASKS_ROUTE_FAMILY,
        hook: invoke_tasks_list_live_route,
    },
    TasksRouteRegistryEntry {
        method: "GET",
        path: TASKS_GET_ROUTE_PATH,
        family: TASKS_ROUTE_FAMILY,
        hook: invoke_tasks_get_live_route,
    },
    TasksRouteRegistryEntry {
        method: "POST",
        path: TASKS_CANCEL_ROUTE_PATH,
        family: TASKS_ROUTE_FAMILY,
        hook: invoke_tasks_cancel_live_route,
    },
];

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_task<'a>() -> BoundedTaskRecord<'a> {
        BoundedTaskRecord {
            node: "node-a",
            id: 7,
            task_type: "transport",
            action: "cluster:admin/reroute",
            start_time_in_millis: 1,
            running_time_in_nanos: 2,
            cancellable: true,
        }
    }

    #[test]
    fn tasks_registry_table_describes_bounded_task_surface() {
        assert_eq!(TASKS_ROUTE_REGISTRY_TABLE.len(), 3);
        assert_eq!(TASKS_ROUTE_REGISTRY_TABLE[0].path, "/_tasks");
        assert_eq!(TASKS_ROUTE_REGISTRY_TABLE[1].path, "/_tasks/{task_id}");
        assert_eq!(TASKS_ROUTE_REGISTRY_TABLE[2].path, "/_tasks/_cancel");
        assert_eq!(
            TASKS_ENVELOPE_FIELDS,
            [
                "node",
                "id",
                "type",
                "action",
                "start_time_in_millis",
                "running_time_in_nanos",
                "parent_task_id",
                "cancellable",
                "cancelled",
                "headers",
                "status",
            ]
        );
    }

    #[test]
    fn tasks_list_response_groups_bounded_tasks_by_node() {
        let body = build_tasks_list_response(
            &serde_json::json!({
                "name": "node-a",
                "transport_address": "127.0.0.1:9300",
                "host": "127.0.0.1",
                "ip": "127.0.0.1:9300",
                "roles": ["cluster_manager"],
                "attributes": {"testattr": "test"}
            }),
            &[sample_task()],
        );
        assert_eq!(
            body["nodes"]["node-a"]["tasks"]["node-a:7"]["action"],
            serde_json::json!("cluster:admin/reroute")
        );
        assert_eq!(body["nodes"]["node-a"]["name"], serde_json::json!("node-a"));
    }

    #[test]
    fn tasks_live_route_hooks_reuse_bounded_envelope_fields() {
        let task = serde_json::json!({
            "task": {
                "node": "node-a",
                "id": 7,
                "action": "cluster:admin/reroute",
                "cancellable": true,
                "unexpected": "drop-me"
            }
        });
        let list = invoke_tasks_list_live_route(&serde_json::json!({
            "node": {
                "name": "node-a",
                "transport_address": "127.0.0.1:9300",
                "host": "127.0.0.1",
                "ip": "127.0.0.1:9300",
                "roles": ["cluster_manager"],
                "attributes": {"testattr": "test"}
            },
            "tasks": [task["task"].clone()]
        }));
        let get = invoke_tasks_get_live_route(&task);
        let cancel = invoke_tasks_cancel_live_route(&task);

        assert_eq!(
            list["nodes"]["node-a"]["tasks"]["node-a:7"]["action"],
            serde_json::json!("cluster:admin/reroute")
        );
        assert_eq!(list["nodes"]["node-a"]["name"], serde_json::json!("node-a"));
        assert!(get["task"].get("unexpected").is_none());
        assert_eq!(
            cancel["nodes"]["node-a"]["tasks"]["node-a:7"]["cancellable"],
            serde_json::json!(true)
        );
    }

    #[test]
    fn task_get_and_cancel_responses_keep_bounded_task_envelope() {
        let task = sample_task();
        let get = build_task_get_response(&task);
        let cancel = build_task_cancel_response(&task);
        assert_eq!(get["task"]["cancellable"], serde_json::json!(true));
        assert_eq!(
            cancel["nodes"]["node-a"]["tasks"]["node-a:7"]["id"],
            serde_json::json!(7)
        );
    }

    #[test]
    fn tasks_parent_grouping_nests_child_tasks_under_existing_parent() {
        let body = serde_json::json!({
            "tasks": [
                {
                    "node": "node-a",
                    "id": 99,
                    "action": "cluster:admin/reroute",
                    "cancellable": false,
                    "parent_task_id": "-",
                    "headers": {"x-opaque-id": "parent-request"}
                },
                {
                    "node": "node-a",
                    "id": 7,
                    "action": "indices:data/write/bulk",
                    "cancellable": true,
                    "parent_task_id": "node-a:99",
                    "headers": {"x-opaque-id": "child-request"}
                }
            ]
        });

        let grouped = invoke_tasks_list_by_parent_live_route(&body);

        assert_eq!(grouped["tasks"]["node-a:99"]["id"], serde_json::json!(99));
        assert_eq!(
            grouped["tasks"]["node-a:99"]["children"][0]["id"],
            serde_json::json!(7)
        );
        assert_eq!(
            grouped["tasks"]["node-a:99"]["children"][0]["parent_task_id"],
            serde_json::json!("node-a:99")
        );
        assert_eq!(
            grouped["tasks"]["node-a:99"]["children"][0]["headers"]["x-opaque-id"],
            serde_json::json!("child-request")
        );
    }

    #[test]
    fn tasks_flat_grouping_returns_task_array() {
        let body = serde_json::json!({
            "tasks": [
                {
                    "node": "node-a",
                    "id": 7,
                    "action": "cluster:monitor/tasks/lists",
                    "cancellable": false,
                    "unexpected": "drop-me"
                }
            ]
        });

        let flat = invoke_tasks_list_flat_live_route(&body);

        assert!(flat["tasks"].is_array());
        assert_eq!(flat["tasks"][0]["id"], serde_json::json!(7));
        assert_eq!(
            flat["tasks"][0]["action"],
            serde_json::json!("cluster:monitor/tasks/lists")
        );
        assert!(flat["tasks"][0].get("unexpected").is_none());
    }

    #[test]
    fn task_error_helpers_use_canonical_error_types() {
        let missing = build_unknown_task_error("node-a:7");
        let non_cancellable = build_non_cancellable_task_error("node-a:7");
        assert_eq!(
            missing["error"]["type"],
            serde_json::json!(TASKS_UNKNOWN_TASK_ERROR_TYPE)
        );
        assert_eq!(
            non_cancellable["error"]["type"],
            serde_json::json!(TASKS_NON_CANCELLABLE_ERROR_TYPE)
        );
    }

    #[test]
    fn tasks_param_reject_helper_uses_canonical_bucket() {
        assert_eq!(reject_unsupported_tasks_params(&[]), Ok(()));
        assert_eq!(
            reject_unsupported_tasks_params(&["wait_for_completion"]),
            Err(TASKS_UNSUPPORTED_PARAMETER_BUCKET)
        );
    }
}
