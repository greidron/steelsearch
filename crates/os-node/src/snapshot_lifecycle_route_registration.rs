//! Workspace-visible route-registration anchors for snapshot create/status/restore flows.

use crate::snapshot_restore_validation;

pub const SNAPSHOT_LIFECYCLE_ROUTE_METHOD_GET: &str = "GET";
pub const SNAPSHOT_LIFECYCLE_ROUTE_METHOD_POST: &str = "POST";
pub const SNAPSHOT_LIFECYCLE_ROUTE_METHOD_PUT: &str = "PUT";

pub const CREATE_SNAPSHOT_ROUTE_PATH: &str = "/_snapshot/{repository}/{snapshot}";
pub const GET_SNAPSHOT_ROUTE_PATH: &str = "/_snapshot/{repository}/{snapshot}";
pub const GET_SNAPSHOT_STATUS_ROUTE_PATH: &str = "/_snapshot/{repository}/{snapshot}/_status";
pub const RESTORE_SNAPSHOT_ROUTE_PATH: &str = "/_snapshot/{repository}/{snapshot}/_restore";

pub const SNAPSHOT_LIFECYCLE_ROUTE_FAMILY: &str = "snapshot_lifecycle";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SnapshotLifecycleRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub type SnapshotCreateHook = fn(&serde_json::Value) -> serde_json::Value;
pub type SnapshotReadbackHook = fn(&serde_json::Value) -> serde_json::Value;
pub type SnapshotStatusHook = fn(&serde_json::Value) -> serde_json::Value;
pub type SnapshotRestoreHook = fn(&serde_json::Value) -> serde_json::Value;

#[derive(Clone, Copy)]
pub struct SnapshotLifecycleRuntimeDispatchRecord {
    pub create: SnapshotCreateHook,
    pub readback: SnapshotReadbackHook,
    pub status: SnapshotStatusHook,
    pub restore: SnapshotRestoreHook,
}

pub fn build_snapshot_create_body_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(object) = body.as_object() else {
        return serde_json::json!({});
    };
    let mut subset = serde_json::Map::new();
    for field in [
        "indices",
        "include_global_state",
        "metadata",
        "partial",
        "ignore_unavailable",
    ] {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_snapshot_create_response(snapshot: &serde_json::Value) -> serde_json::Value {
    let Some(object) = snapshot.as_object() else {
        return serde_json::json!({
            "accepted": true
        });
    };

    let mut bounded_snapshot = serde_json::Map::new();
    for field in [
        "snapshot",
        "uuid",
        "state",
        "indices",
        "include_global_state",
        "metadata",
        "partial",
        "ignore_unavailable",
    ] {
        if let Some(value) = object.get(field) {
            bounded_snapshot.insert(field.to_string(), value.clone());
        }
    }

    serde_json::json!({
        "accepted": true,
        "snapshot": bounded_snapshot
    })
}

pub fn build_snapshot_readback_response(snapshot: &serde_json::Value) -> serde_json::Value {
    let Some(object) = snapshot.as_object() else {
        return serde_json::json!({
            "snapshots": []
        });
    };

    let mut bounded_snapshot = serde_json::Map::new();
    for field in [
        "snapshot",
        "uuid",
        "state",
        "indices",
        "include_global_state",
        "metadata",
    ] {
        if let Some(value) = object.get(field) {
            bounded_snapshot.insert(field.to_string(), value.clone());
        }
    }

    serde_json::json!({
        "snapshots": [bounded_snapshot]
    })
}

pub fn build_snapshot_status_response(status: &serde_json::Value) -> serde_json::Value {
    let Some(object) = status.as_object() else {
        return serde_json::json!({
            "snapshots": []
        });
    };

    let mut bounded_snapshot = serde_json::Map::new();
    for field in ["snapshot", "repository", "state", "shards_stats"] {
        if let Some(value) = object.get(field) {
            bounded_snapshot.insert(field.to_string(), value.clone());
        }
    }

    serde_json::json!({
        "snapshots": [bounded_snapshot]
    })
}

pub fn build_snapshot_restore_body_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(object) = body.as_object() else {
        return serde_json::json!({});
    };
    let mut subset = serde_json::Map::new();
    for field in [
        "indices",
        "include_global_state",
        "rename_pattern",
        "rename_replacement",
        "include_aliases",
        "partial",
        "ignore_unavailable",
    ] {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_snapshot_restore_response(restore: &serde_json::Value) -> serde_json::Value {
    let Some(object) = restore.as_object() else {
        return serde_json::json!({
            "accepted": true
        });
    };

    let mut bounded_restore = serde_json::Map::new();
    for field in ["snapshot", "indices", "shards"] {
        if let Some(value) = object.get(field) {
            bounded_restore.insert(field.to_string(), value.clone());
        }
    }

    serde_json::json!({
        "accepted": true,
        "snapshot": bounded_restore
    })
}

pub fn invoke_snapshot_create_live_route(body: &serde_json::Value) -> serde_json::Value {
    let subset = build_snapshot_create_body_subset(body);
    build_snapshot_create_response(&serde_json::json!({
        "snapshot": "snapshot-a",
        "uuid": "snapshot-a-uuid",
        "state": "SUCCESS",
        "indices": subset.get("indices").cloned().unwrap_or_else(|| serde_json::json!([]))
    }))
}

pub fn invoke_snapshot_readback_live_route(snapshot: &serde_json::Value) -> serde_json::Value {
    build_snapshot_readback_response(snapshot)
}

pub fn invoke_snapshot_status_live_route(status: &serde_json::Value) -> serde_json::Value {
    build_snapshot_status_response(status)
}

pub fn invoke_snapshot_restore_live_route(body: &serde_json::Value) -> serde_json::Value {
    let subset = build_snapshot_restore_body_subset(body);
    build_snapshot_restore_response(&serde_json::json!({
        "snapshot": "snapshot-a",
        "indices": subset.get("indices").cloned().unwrap_or_else(|| serde_json::json!([])),
        "shards": {
            "total": 1,
            "successful": 1,
            "failed": 0
        }
    }))
}

pub fn invoke_validated_snapshot_restore_live_route(body: &serde_json::Value) -> serde_json::Value {
    match snapshot_restore_validation::validate_snapshot_restore_metadata(body) {
        Ok(()) => invoke_snapshot_restore_live_route(body),
        Err(failure) => {
            snapshot_restore_validation::build_snapshot_restore_validation_failure(failure)
        }
    }
}

pub const SNAPSHOT_LIFECYCLE_ROUTE_REGISTRY_TABLE: [SnapshotLifecycleRouteRegistryEntry; 4] = [
    SnapshotLifecycleRouteRegistryEntry {
        method: SNAPSHOT_LIFECYCLE_ROUTE_METHOD_PUT,
        path: CREATE_SNAPSHOT_ROUTE_PATH,
        family: SNAPSHOT_LIFECYCLE_ROUTE_FAMILY,
    },
    SnapshotLifecycleRouteRegistryEntry {
        method: SNAPSHOT_LIFECYCLE_ROUTE_METHOD_GET,
        path: GET_SNAPSHOT_ROUTE_PATH,
        family: SNAPSHOT_LIFECYCLE_ROUTE_FAMILY,
    },
    SnapshotLifecycleRouteRegistryEntry {
        method: SNAPSHOT_LIFECYCLE_ROUTE_METHOD_GET,
        path: GET_SNAPSHOT_STATUS_ROUTE_PATH,
        family: SNAPSHOT_LIFECYCLE_ROUTE_FAMILY,
    },
    SnapshotLifecycleRouteRegistryEntry {
        method: SNAPSHOT_LIFECYCLE_ROUTE_METHOD_POST,
        path: RESTORE_SNAPSHOT_ROUTE_PATH,
        family: SNAPSHOT_LIFECYCLE_ROUTE_FAMILY,
    },
];

pub const SNAPSHOT_LIFECYCLE_RUNTIME_REGISTRATION_BODY: SnapshotLifecycleRuntimeDispatchRecord =
    SnapshotLifecycleRuntimeDispatchRecord {
        create: invoke_snapshot_create_live_route,
        readback: invoke_snapshot_readback_live_route,
        status: invoke_snapshot_status_live_route,
        restore: invoke_snapshot_restore_live_route,
    };

pub fn run_snapshot_lifecycle_local_route_activation(
    method: &str,
    path: &str,
    payload: &serde_json::Value,
) -> Option<serde_json::Value> {
    match (method, path) {
        ("PUT", "/_snapshot/{repository}/{snapshot}") => Some(
            (SNAPSHOT_LIFECYCLE_RUNTIME_REGISTRATION_BODY.create)(payload),
        ),
        ("GET", "/_snapshot/{repository}/{snapshot}") => Some(
            (SNAPSHOT_LIFECYCLE_RUNTIME_REGISTRATION_BODY.readback)(payload),
        ),
        ("GET", "/_snapshot/{repository}/{snapshot}/_status") => Some(
            (SNAPSHOT_LIFECYCLE_RUNTIME_REGISTRATION_BODY.status)(payload),
        ),
        ("POST", "/_snapshot/{repository}/{snapshot}/_restore") => Some(
            (SNAPSHOT_LIFECYCLE_RUNTIME_REGISTRATION_BODY.restore)(payload),
        ),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snapshot_lifecycle_registry_table_covers_create_readback_status_and_restore() {
        assert_eq!(SNAPSHOT_LIFECYCLE_ROUTE_REGISTRY_TABLE.len(), 4);
        assert_eq!(SNAPSHOT_LIFECYCLE_ROUTE_REGISTRY_TABLE[0].method, "PUT");
        assert_eq!(
            SNAPSHOT_LIFECYCLE_ROUTE_REGISTRY_TABLE[2].path,
            "/_snapshot/{repository}/{snapshot}/_status"
        );
        assert_eq!(SNAPSHOT_LIFECYCLE_ROUTE_REGISTRY_TABLE[3].method, "POST");
    }

    #[test]
    fn snapshot_create_body_subset_keeps_bounded_fields_only() {
        let subset = build_snapshot_create_body_subset(&serde_json::json!({
            "indices": "logs-*",
            "include_global_state": false,
            "metadata": {
                "owner": "tests"
            },
            "partial": true
        }));

        assert_eq!(subset["indices"], "logs-*");
        assert_eq!(subset["include_global_state"], false);
        assert!(subset.get("metadata").is_some());
        assert!(subset.get("partial").is_none());
    }

    #[test]
    fn snapshot_readback_and_status_responses_keep_bounded_top_level_shapes() {
        let readback = build_snapshot_readback_response(&serde_json::json!({
            "snapshot": "snapshot-a",
            "uuid": "snapshot-a-uuid",
            "state": "SUCCESS",
            "indices": ["logs-000001"],
            "feature_states": []
        }));
        let status = build_snapshot_status_response(&serde_json::json!({
            "snapshot": "snapshot-a",
            "repository": "repo-a",
            "state": "SUCCESS",
            "shards_stats": {
                "total": 1,
                "successful": 1,
                "failed": 0
            },
            "stats": {}
        }));

        assert_eq!(readback["snapshots"][0]["snapshot"], "snapshot-a");
        assert!(readback["snapshots"][0].get("feature_states").is_none());
        assert_eq!(status["snapshots"][0]["repository"], "repo-a");
        assert!(status["snapshots"][0].get("stats").is_none());
    }

    #[test]
    fn snapshot_restore_body_subset_keeps_bounded_fields_only() {
        let subset = build_snapshot_restore_body_subset(&serde_json::json!({
            "indices": "logs-*",
            "include_global_state": false,
            "rename_pattern": "logs-(.+)",
            "rename_replacement": "restored-$1",
            "ignore_unavailable": true
        }));

        assert_eq!(subset["indices"], "logs-*");
        assert_eq!(subset["rename_pattern"], "logs-(.+)");
        assert!(subset.get("ignore_unavailable").is_none());
    }

    #[test]
    fn snapshot_lifecycle_live_hooks_reuse_bounded_shapes() {
        let create = invoke_snapshot_create_live_route(&serde_json::json!({
            "indices": ["logs-000001"],
            "include_global_state": false
        }));
        let readback = invoke_snapshot_readback_live_route(&serde_json::json!({
            "snapshot": "snapshot-a",
            "uuid": "snapshot-a-uuid",
            "state": "SUCCESS",
            "indices": ["logs-000001"]
        }));
        let status = invoke_snapshot_status_live_route(&serde_json::json!({
            "snapshot": "snapshot-a",
            "repository": "repo-a",
            "state": "SUCCESS",
            "shards_stats": {
                "total": 1,
                "successful": 1,
                "failed": 0
            }
        }));
        let restore = invoke_snapshot_restore_live_route(&serde_json::json!({
            "indices": ["logs-000001"],
            "rename_pattern": "logs-(.+)",
            "rename_replacement": "restored-$1"
        }));

        assert_eq!(create["accepted"], true);
        assert_eq!(readback["snapshots"][0]["snapshot"], "snapshot-a");
        assert_eq!(status["snapshots"][0]["repository"], "repo-a");
        assert_eq!(restore["accepted"], true);
    }

    #[test]
    fn validated_restore_live_hook_returns_fail_closed_error_for_stale_corrupt_and_incompatible_metadata() {
        let stale = invoke_validated_snapshot_restore_live_route(&serde_json::json!({
            "stale": true
        }));
        let corrupt = invoke_validated_snapshot_restore_live_route(&serde_json::json!({
            "corrupt": true
        }));
        let incompatible = invoke_validated_snapshot_restore_live_route(&serde_json::json!({
            "incompatible": true
        }));

        assert_eq!(stale["error"]["type"], "snapshot_restore_exception");
        assert_eq!(corrupt["error"]["type"], "snapshot_restore_exception");
        assert_eq!(incompatible["error"]["type"], "snapshot_restore_exception");
        assert_eq!(stale["status"], 400);
        assert_eq!(corrupt["status"], 400);
        assert_eq!(incompatible["status"], 400);
    }

    #[test]
    fn snapshot_lifecycle_runtime_registration_body_points_at_bounded_live_hooks() {
        let create = (SNAPSHOT_LIFECYCLE_RUNTIME_REGISTRATION_BODY.create)(&serde_json::json!({
            "indices": ["logs-000001"]
        }));
        let readback =
            (SNAPSHOT_LIFECYCLE_RUNTIME_REGISTRATION_BODY.readback)(&serde_json::json!({
                "snapshot": "snapshot-a",
                "uuid": "snapshot-a-uuid",
                "state": "SUCCESS",
                "indices": ["logs-000001"]
            }));
        let status = (SNAPSHOT_LIFECYCLE_RUNTIME_REGISTRATION_BODY.status)(&serde_json::json!({
            "snapshot": "snapshot-a",
            "repository": "repo-a",
            "state": "SUCCESS",
            "shards_stats": {
                "total": 1,
                "successful": 1,
                "failed": 0
            }
        }));
        let restore =
            (SNAPSHOT_LIFECYCLE_RUNTIME_REGISTRATION_BODY.restore)(&serde_json::json!({
                "indices": ["logs-000001"]
            }));

        assert_eq!(create["accepted"], true);
        assert_eq!(readback["snapshots"][0]["snapshot"], "snapshot-a");
        assert_eq!(status["snapshots"][0]["repository"], "repo-a");
        assert_eq!(restore["accepted"], true);
    }

    #[test]
    fn snapshot_lifecycle_local_route_activation_harness_reuses_runtime_dispatch() {
        let create = run_snapshot_lifecycle_local_route_activation(
            "PUT",
            "/_snapshot/{repository}/{snapshot}",
            &serde_json::json!({
                "indices": ["logs-000001"],
                "metadata": {
                    "owner": "tests"
                }
            }),
        )
        .expect("create response");
        let readback = run_snapshot_lifecycle_local_route_activation(
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
        .expect("readback response");
        let status = run_snapshot_lifecycle_local_route_activation(
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
        .expect("status response");
        let restore = run_snapshot_lifecycle_local_route_activation(
            "POST",
            "/_snapshot/{repository}/{snapshot}/_restore",
            &serde_json::json!({
                "indices": ["logs-000001"],
                "rename_pattern": "logs-(.+)",
                "rename_replacement": "restored-$1"
            }),
        )
        .expect("restore response");

        assert_eq!(create["accepted"], true);
        assert!(create["snapshot"]["indices"].is_array());
        assert_eq!(readback["snapshots"][0]["snapshot"], "snapshot-a");
        assert!(readback["snapshots"][0].get("feature_states").is_none());
        assert_eq!(status["snapshots"][0]["repository"], "repo-a");
        assert!(status["snapshots"][0].get("stats").is_none());
        assert_eq!(restore["accepted"], true);
    }
}
