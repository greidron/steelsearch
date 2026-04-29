//! Workspace-visible route-registration anchors for snapshot delete and cleanup flows.

pub const SNAPSHOT_CLEANUP_ROUTE_METHOD_DELETE: &str = "DELETE";
pub const SNAPSHOT_CLEANUP_ROUTE_METHOD_POST: &str = "POST";

pub const DELETE_SNAPSHOT_ROUTE_PATH: &str = "/_snapshot/{repository}/{snapshot}";
pub const CLEANUP_SNAPSHOT_REPOSITORY_ROUTE_PATH: &str = "/_snapshot/{repository}/_cleanup";

pub const SNAPSHOT_CLEANUP_ROUTE_FAMILY: &str = "snapshot_cleanup";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SnapshotCleanupRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub type SnapshotDeleteHook = fn(&serde_json::Value) -> serde_json::Value;
pub type SnapshotCleanupHook = fn(&serde_json::Value) -> serde_json::Value;

#[derive(Clone, Copy)]
pub struct SnapshotCleanupRuntimeDispatchRecord {
    pub delete: SnapshotDeleteHook,
    pub cleanup: SnapshotCleanupHook,
}

pub fn build_snapshot_delete_response(snapshot: &serde_json::Value) -> serde_json::Value {
    let Some(object) = snapshot.as_object() else {
        return serde_json::json!({
            "acknowledged": true
        });
    };

    let mut bounded_snapshot = serde_json::Map::new();
    for field in ["snapshot", "repository"] {
        if let Some(value) = object.get(field) {
            bounded_snapshot.insert(field.to_string(), value.clone());
        }
    }

    serde_json::json!({
        "acknowledged": true,
        "snapshot": bounded_snapshot
    })
}

pub fn build_snapshot_cleanup_response(cleanup: &serde_json::Value) -> serde_json::Value {
    let Some(object) = cleanup.as_object() else {
        return serde_json::json!({
            "results": {
                "deleted_bytes": 0,
                "deleted_blobs": 0
            }
        });
    };

    let mut bounded_results = serde_json::Map::new();
    for field in ["deleted_bytes", "deleted_blobs"] {
        if let Some(value) = object.get(field) {
            bounded_results.insert(field.to_string(), value.clone());
        }
    }

    serde_json::json!({
        "results": bounded_results
    })
}

pub fn invoke_snapshot_delete_live_route(snapshot: &serde_json::Value) -> serde_json::Value {
    build_snapshot_delete_response(snapshot)
}

pub fn invoke_snapshot_cleanup_live_route(cleanup: &serde_json::Value) -> serde_json::Value {
    build_snapshot_cleanup_response(cleanup)
}

pub const SNAPSHOT_CLEANUP_ROUTE_REGISTRY_TABLE: [SnapshotCleanupRouteRegistryEntry; 2] = [
    SnapshotCleanupRouteRegistryEntry {
        method: SNAPSHOT_CLEANUP_ROUTE_METHOD_DELETE,
        path: DELETE_SNAPSHOT_ROUTE_PATH,
        family: SNAPSHOT_CLEANUP_ROUTE_FAMILY,
    },
    SnapshotCleanupRouteRegistryEntry {
        method: SNAPSHOT_CLEANUP_ROUTE_METHOD_POST,
        path: CLEANUP_SNAPSHOT_REPOSITORY_ROUTE_PATH,
        family: SNAPSHOT_CLEANUP_ROUTE_FAMILY,
    },
];

pub const SNAPSHOT_CLEANUP_RUNTIME_REGISTRATION_BODY: SnapshotCleanupRuntimeDispatchRecord =
    SnapshotCleanupRuntimeDispatchRecord {
        delete: invoke_snapshot_delete_live_route,
        cleanup: invoke_snapshot_cleanup_live_route,
    };

pub fn run_snapshot_cleanup_local_route_activation(
    method: &str,
    path: &str,
    payload: &serde_json::Value,
) -> Option<serde_json::Value> {
    match (method, path) {
        ("DELETE", "/_snapshot/{repository}/{snapshot}") => Some(
            (SNAPSHOT_CLEANUP_RUNTIME_REGISTRATION_BODY.delete)(payload),
        ),
        ("POST", "/_snapshot/{repository}/_cleanup") => Some(
            (SNAPSHOT_CLEANUP_RUNTIME_REGISTRATION_BODY.cleanup)(payload),
        ),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snapshot_cleanup_registry_table_covers_delete_and_cleanup_routes() {
        assert_eq!(SNAPSHOT_CLEANUP_ROUTE_REGISTRY_TABLE.len(), 2);
        assert_eq!(SNAPSHOT_CLEANUP_ROUTE_REGISTRY_TABLE[0].method, "DELETE");
        assert_eq!(
            SNAPSHOT_CLEANUP_ROUTE_REGISTRY_TABLE[1].path,
            "/_snapshot/{repository}/_cleanup"
        );
    }

    #[test]
    fn snapshot_delete_response_keeps_bounded_shape() {
        let response = build_snapshot_delete_response(&serde_json::json!({
            "snapshot": "snapshot-a",
            "repository": "repo-a",
            "start_time": "ignored"
        }));

        assert_eq!(response["acknowledged"], true);
        assert_eq!(response["snapshot"]["snapshot"], "snapshot-a");
        assert!(response["snapshot"].get("start_time").is_none());
    }

    #[test]
    fn snapshot_cleanup_response_keeps_deleted_bytes_and_blobs_only() {
        let response = build_snapshot_cleanup_response(&serde_json::json!({
            "deleted_bytes": 128,
            "deleted_blobs": 2,
            "cleanup_time_in_millis": 10
        }));

        assert_eq!(response["results"]["deleted_bytes"], 128);
        assert_eq!(response["results"]["deleted_blobs"], 2);
        assert!(response["results"].get("cleanup_time_in_millis").is_none());
    }

    #[test]
    fn snapshot_cleanup_runtime_registration_body_points_at_bounded_live_hooks() {
        let delete = (SNAPSHOT_CLEANUP_RUNTIME_REGISTRATION_BODY.delete)(&serde_json::json!({
            "snapshot": "snapshot-a",
            "repository": "repo-a"
        }));
        let cleanup = (SNAPSHOT_CLEANUP_RUNTIME_REGISTRATION_BODY.cleanup)(&serde_json::json!({
            "deleted_bytes": 64,
            "deleted_blobs": 1
        }));

        assert_eq!(delete["acknowledged"], true);
        assert_eq!(cleanup["results"]["deleted_bytes"], 64);
    }

    #[test]
    fn snapshot_cleanup_local_route_activation_harness_reuses_runtime_dispatch() {
        let delete = run_snapshot_cleanup_local_route_activation(
            "DELETE",
            "/_snapshot/{repository}/{snapshot}",
            &serde_json::json!({
                "snapshot": "snapshot-a",
                "repository": "repo-a",
                "start_time": "ignored"
            }),
        )
        .expect("delete response");
        let cleanup = run_snapshot_cleanup_local_route_activation(
            "POST",
            "/_snapshot/{repository}/_cleanup",
            &serde_json::json!({
                "deleted_bytes": 64,
                "deleted_blobs": 1,
                "cleanup_time_in_millis": 10
            }),
        )
        .expect("cleanup response");

        assert_eq!(delete["snapshot"]["snapshot"], "snapshot-a");
        assert!(delete["snapshot"].get("start_time").is_none());
        assert_eq!(cleanup["results"]["deleted_bytes"], 64);
        assert!(cleanup["results"].get("cleanup_time_in_millis").is_none());
    }
}
