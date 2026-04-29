//! Workspace-visible route-registration anchors for `GET /_cluster/pending_tasks`.

/// Canonical route family label for cluster pending-tasks readback work.
pub const PENDING_TASKS_ROUTE_FAMILY: &str = "cluster_pending_tasks_readback";

/// Canonical HTTP method for the Phase A cluster pending-tasks surface.
pub const PENDING_TASKS_ROUTE_METHOD: &str = "GET";

/// Canonical route path for the Phase A cluster pending-tasks surface.
pub const PENDING_TASKS_ROUTE_PATH: &str = "/_cluster/pending_tasks";

/// Canonical top-level response fields for the current pending-tasks subset.
pub const PENDING_TASKS_RESPONSE_FIELDS: [&str; 1] = ["tasks"];

/// Canonical per-task fields for the current pending-tasks subset.
pub const PENDING_TASKS_ITEM_FIELDS: [&str; 6] = [
    "insert_order",
    "priority",
    "source",
    "executing",
    "time_in_queue_millis",
    "time_in_queue",
];

/// Workspace-visible registry entry for `GET /_cluster/pending_tasks`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PendingTasksRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
    pub hook: PendingTasksRouteInvokeFn,
}

/// Canonical bounded response-body helper for `GET /_cluster/pending_tasks`.
pub fn build_pending_tasks_response(tasks: &serde_json::Value) -> serde_json::Value {
    serde_json::json!({
        "tasks": tasks.clone(),
    })
}

fn normalize_pending_task(task: &serde_json::Value) -> serde_json::Value {
    let mut normalized = serde_json::Map::new();
    for field in PENDING_TASKS_ITEM_FIELDS {
        if let Some(value) = task.get(field) {
            normalized.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(normalized)
}

/// Canonical bounded response normalization for the current pending-tasks subset.
pub fn normalize_pending_tasks_response(body: &serde_json::Value) -> serde_json::Value {
    let tasks = body
        .get("tasks")
        .and_then(serde_json::Value::as_array)
        .cloned()
        .unwrap_or_default()
        .into_iter()
        .map(|task| normalize_pending_task(&task))
        .collect::<Vec<_>>();
    build_pending_tasks_response(&serde_json::Value::Array(tasks))
}

/// Canonical invoke-hook type for `GET /_cluster/pending_tasks`.
pub type PendingTasksRouteInvokeFn = fn(&serde_json::Value) -> serde_json::Value;

/// Canonical invoke-hook symbol for `GET /_cluster/pending_tasks`.
pub fn invoke_pending_tasks_live_route(body: &serde_json::Value) -> serde_json::Value {
    normalize_pending_tasks_response(body)
}

/// Canonical route hook for `GET /_cluster/pending_tasks`.
pub const PENDING_TASKS_ROUTE_REGISTRY_HOOK: PendingTasksRouteInvokeFn =
    invoke_pending_tasks_live_route;

/// Canonical route-registration entry for `GET /_cluster/pending_tasks`.
pub const PENDING_TASKS_ROUTE_REGISTRY_ENTRY: PendingTasksRouteRegistryEntry =
    PendingTasksRouteRegistryEntry {
        method: PENDING_TASKS_ROUTE_METHOD,
        path: PENDING_TASKS_ROUTE_PATH,
        family: PENDING_TASKS_ROUTE_FAMILY,
        hook: PENDING_TASKS_ROUTE_REGISTRY_HOOK,
    };

/// Canonical route-registration table for the current pending-tasks surface.
pub const PENDING_TASKS_ROUTE_REGISTRY_TABLE: [PendingTasksRouteRegistryEntry; 1] =
    [PENDING_TASKS_ROUTE_REGISTRY_ENTRY];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pending_tasks_registry_entry_describes_cluster_pending_tasks_route() {
        assert_eq!(PENDING_TASKS_ROUTE_REGISTRY_ENTRY.method, "GET");
        assert_eq!(PENDING_TASKS_ROUTE_REGISTRY_ENTRY.path, "/_cluster/pending_tasks");
        assert_eq!(
            PENDING_TASKS_ROUTE_REGISTRY_ENTRY.family,
            "cluster_pending_tasks_readback"
        );
        assert_eq!(PENDING_TASKS_RESPONSE_FIELDS, ["tasks"]);
    }

    #[test]
    fn pending_tasks_response_normalization_keeps_only_bounded_item_fields() {
        let body = serde_json::json!({
            "tasks": [
                {
                    "insert_order": 1,
                    "priority": "URGENT",
                    "source": "publish cluster state",
                    "executing": true,
                    "time_in_queue_millis": 0,
                    "time_in_queue": "0ms",
                    "unexpected_field": "drop-me"
                }
            ]
        });

        let normalized = normalize_pending_tasks_response(&body);
        assert_eq!(normalized["tasks"][0]["insert_order"], serde_json::json!(1));
        assert_eq!(normalized["tasks"][0]["priority"], serde_json::json!("URGENT"));
        assert_eq!(
            normalized["tasks"][0]["source"],
            serde_json::json!("publish cluster state")
        );
        assert!(normalized["tasks"][0].get("unexpected_field").is_none());
    }

    #[test]
    fn pending_tasks_registry_hook_reuses_bounded_normalization_path() {
        let body = serde_json::json!({
            "tasks": [
                {
                    "insert_order": 7,
                    "priority": "HIGH",
                    "source": "refresh metadata",
                    "executing": false,
                    "time_in_queue_millis": 12,
                    "time_in_queue": "12ms"
                }
            ]
        });

        let rendered = (PENDING_TASKS_ROUTE_REGISTRY_ENTRY.hook)(&body);
        assert_eq!(rendered["tasks"][0]["insert_order"], serde_json::json!(7));
        assert_eq!(rendered["tasks"][0]["priority"], serde_json::json!("HIGH"));
        assert_eq!(rendered["tasks"][0]["time_in_queue"], serde_json::json!("12ms"));
    }
}
