//! Workspace-visible route-registration anchors for bounded `/_tasks` parity work.

pub const TASKS_ROUTE_FAMILY: &str = "tasks_registry_readback";
pub const TASKS_LIST_ROUTE_PATH: &str = "/_tasks";
pub const TASKS_GET_ROUTE_PATH: &str = "/_tasks/{task_id}";
pub const TASKS_CANCEL_ROUTE_PATH: &str = "/_tasks/_cancel";

pub const TASKS_ENVELOPE_FIELDS: [&str; 4] = ["node", "id", "action", "cancellable"];
pub const TASKS_ERROR_FIELDS: [&str; 2] = ["error.type", "error.reason"];

pub const TASKS_UNSUPPORTED_PARAMETER_BUCKET: &str = "unsupported task registry parameter";
pub const TASKS_UNKNOWN_TASK_ERROR_TYPE: &str = "resource_not_found_exception";
pub const TASKS_NON_CANCELLABLE_ERROR_TYPE: &str = "illegal_argument_exception";

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BoundedTaskRecord<'a> {
    pub node: &'a str,
    pub id: u64,
    pub action: &'a str,
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
        "action": task.action,
        "cancellable": task.cancellable,
    })
}

pub fn build_tasks_list_response(tasks: &[BoundedTaskRecord<'_>]) -> serde_json::Value {
    let mut nodes = serde_json::Map::new();
    for task in tasks {
        let node_entry = nodes
            .entry(task.node.to_string())
            .or_insert_with(|| serde_json::json!({ "tasks": {} }));
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
    let mut nodes = serde_json::Map::new();
    for task in tasks {
        let normalized = normalize_bounded_task_value(&task);
        let node = normalized["node"].as_str().unwrap_or("unknown");
        let id = normalized["id"].as_u64().unwrap_or_default();
        let task_key = format!("{node}:{id}");
        let node_entry = nodes
            .entry(node.to_string())
            .or_insert_with(|| serde_json::json!({ "tasks": {} }));
        node_entry["tasks"][task_key] = normalized;
    }
    serde_json::json!({ "nodes": nodes })
}

pub fn invoke_tasks_get_live_route(body: &serde_json::Value) -> serde_json::Value {
    let task = body.get("task").unwrap_or(body);
    serde_json::json!({
        "completed": false,
        "task": normalize_bounded_task_value(task),
    })
}

pub fn invoke_tasks_cancel_live_route(body: &serde_json::Value) -> serde_json::Value {
    let task = body.get("task").unwrap_or(body);
    let normalized = normalize_bounded_task_value(task);
    let node = normalized["node"].as_str().unwrap_or("unknown");
    let id = normalized["id"].as_u64().unwrap_or_default();
    let task_key = format!("{node}:{id}");
    serde_json::json!({
        "nodes": {
            node: {
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
            action: "cluster:admin/reroute",
            cancellable: true,
        }
    }

    #[test]
    fn tasks_registry_table_describes_bounded_task_surface() {
        assert_eq!(TASKS_ROUTE_REGISTRY_TABLE.len(), 3);
        assert_eq!(TASKS_ROUTE_REGISTRY_TABLE[0].path, "/_tasks");
        assert_eq!(TASKS_ROUTE_REGISTRY_TABLE[1].path, "/_tasks/{task_id}");
        assert_eq!(TASKS_ROUTE_REGISTRY_TABLE[2].path, "/_tasks/_cancel");
        assert_eq!(TASKS_ENVELOPE_FIELDS, ["node", "id", "action", "cancellable"]);
    }

    #[test]
    fn tasks_list_response_groups_bounded_tasks_by_node() {
        let body = build_tasks_list_response(&[sample_task()]);
        assert_eq!(
            body["nodes"]["node-a"]["tasks"]["node-a:7"]["action"],
            serde_json::json!("cluster:admin/reroute")
        );
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
            "tasks": [task["task"].clone()]
        }));
        let get = invoke_tasks_get_live_route(&task);
        let cancel = invoke_tasks_cancel_live_route(&task);

        assert_eq!(
            list["nodes"]["node-a"]["tasks"]["node-a:7"]["action"],
            serde_json::json!("cluster:admin/reroute")
        );
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
