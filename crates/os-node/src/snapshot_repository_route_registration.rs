//! Workspace-visible route-registration anchors for snapshot repository CRUD/readback/verify.

pub const SNAPSHOT_REPOSITORY_ROUTE_METHOD_GET: &str = "GET";
pub const SNAPSHOT_REPOSITORY_ROUTE_METHOD_POST: &str = "POST";
pub const SNAPSHOT_REPOSITORY_ROUTE_METHOD_PUT: &str = "PUT";

pub const GET_SNAPSHOT_REPOSITORY_ROUTE_PATH: &str = "/_snapshot";
pub const GET_NAMED_SNAPSHOT_REPOSITORY_ROUTE_PATH: &str = "/_snapshot/{repository}";
pub const PUT_SNAPSHOT_REPOSITORY_ROUTE_PATH: &str = "/_snapshot/{repository}";
pub const POST_SNAPSHOT_REPOSITORY_ROUTE_PATH: &str = "/_snapshot/{repository}";
pub const VERIFY_SNAPSHOT_REPOSITORY_ROUTE_PATH: &str = "/_snapshot/{repository}/_verify";

pub const SNAPSHOT_REPOSITORY_ROUTE_FAMILY: &str = "snapshot_repository";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SnapshotRepositoryRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub type SnapshotRepositoryReadbackHook =
    fn(&serde_json::Value, Option<&str>) -> serde_json::Value;
pub type SnapshotRepositoryMutationHook = fn(&serde_json::Value) -> serde_json::Value;
pub type SnapshotRepositoryVerifyHook = fn(&serde_json::Value) -> serde_json::Value;

#[derive(Clone, Copy)]
pub struct SnapshotRepositoryRuntimeDispatchRecord {
    pub readback: SnapshotRepositoryReadbackHook,
    pub mutation: SnapshotRepositoryMutationHook,
    pub verify: SnapshotRepositoryVerifyHook,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SnapshotRepositoryRuntimeHandlerKind {
    Readback,
    Mutation,
    Verify,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SnapshotRepositoryRuntimeRouteDispatchEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub handler_kind: SnapshotRepositoryRuntimeHandlerKind,
}

pub fn build_snapshot_repository_body_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(object) = body.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in ["type", "settings"] {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_snapshot_repository_readback_response(
    repositories: &serde_json::Value,
    repository: Option<&str>,
) -> serde_json::Value {
    let Some(repository_map) = repositories.as_object() else {
        return serde_json::json!({});
    };

    let mut response = serde_json::Map::new();
    for (name, body) in repository_map {
        if repository.is_some() && repository != Some(name.as_str()) {
            continue;
        }
        response.insert(name.clone(), build_snapshot_repository_body_subset(body));
    }
    serde_json::Value::Object(response)
}

pub fn build_snapshot_repository_acknowledged_response() -> serde_json::Value {
    serde_json::json!({
        "acknowledged": true
    })
}

pub fn build_snapshot_repository_verify_response(verification: &serde_json::Value) -> serde_json::Value {
    let mut response = serde_json::Map::new();

    if let Some(nodes) = verification.get("nodes") {
        response.insert("nodes".to_string(), nodes.clone());
    }

    if response.is_empty() {
        response.insert("nodes".to_string(), serde_json::json!({}));
    }

    serde_json::Value::Object(response)
}

pub fn invoke_snapshot_repository_live_readback(
    repositories: &serde_json::Value,
    repository: Option<&str>,
) -> serde_json::Value {
    build_snapshot_repository_readback_response(repositories, repository)
}

pub fn invoke_snapshot_repository_live_mutation(body: &serde_json::Value) -> serde_json::Value {
    let _subset = build_snapshot_repository_body_subset(body);
    build_snapshot_repository_acknowledged_response()
}

pub fn invoke_snapshot_repository_live_verify(verification: &serde_json::Value) -> serde_json::Value {
    build_snapshot_repository_verify_response(verification)
}

pub const SNAPSHOT_REPOSITORY_ROUTE_REGISTRY_TABLE: [SnapshotRepositoryRouteRegistryEntry; 5] = [
    SnapshotRepositoryRouteRegistryEntry {
        method: SNAPSHOT_REPOSITORY_ROUTE_METHOD_GET,
        path: GET_SNAPSHOT_REPOSITORY_ROUTE_PATH,
        family: SNAPSHOT_REPOSITORY_ROUTE_FAMILY,
    },
    SnapshotRepositoryRouteRegistryEntry {
        method: SNAPSHOT_REPOSITORY_ROUTE_METHOD_GET,
        path: GET_NAMED_SNAPSHOT_REPOSITORY_ROUTE_PATH,
        family: SNAPSHOT_REPOSITORY_ROUTE_FAMILY,
    },
    SnapshotRepositoryRouteRegistryEntry {
        method: SNAPSHOT_REPOSITORY_ROUTE_METHOD_PUT,
        path: PUT_SNAPSHOT_REPOSITORY_ROUTE_PATH,
        family: SNAPSHOT_REPOSITORY_ROUTE_FAMILY,
    },
    SnapshotRepositoryRouteRegistryEntry {
        method: SNAPSHOT_REPOSITORY_ROUTE_METHOD_POST,
        path: POST_SNAPSHOT_REPOSITORY_ROUTE_PATH,
        family: SNAPSHOT_REPOSITORY_ROUTE_FAMILY,
    },
    SnapshotRepositoryRouteRegistryEntry {
        method: SNAPSHOT_REPOSITORY_ROUTE_METHOD_POST,
        path: VERIFY_SNAPSHOT_REPOSITORY_ROUTE_PATH,
        family: SNAPSHOT_REPOSITORY_ROUTE_FAMILY,
    },
];

pub const SNAPSHOT_REPOSITORY_RUNTIME_REGISTRATION_BODY: SnapshotRepositoryRuntimeDispatchRecord =
    SnapshotRepositoryRuntimeDispatchRecord {
        readback: invoke_snapshot_repository_live_readback,
        mutation: invoke_snapshot_repository_live_mutation,
        verify: invoke_snapshot_repository_live_verify,
    };

pub const SNAPSHOT_REPOSITORY_RUNTIME_DISPATCH_TABLE:
    [SnapshotRepositoryRuntimeRouteDispatchEntry; 5] = [
    SnapshotRepositoryRuntimeRouteDispatchEntry {
        method: SNAPSHOT_REPOSITORY_ROUTE_METHOD_GET,
        path: GET_SNAPSHOT_REPOSITORY_ROUTE_PATH,
        handler_kind: SnapshotRepositoryRuntimeHandlerKind::Readback,
    },
    SnapshotRepositoryRuntimeRouteDispatchEntry {
        method: SNAPSHOT_REPOSITORY_ROUTE_METHOD_GET,
        path: GET_NAMED_SNAPSHOT_REPOSITORY_ROUTE_PATH,
        handler_kind: SnapshotRepositoryRuntimeHandlerKind::Readback,
    },
    SnapshotRepositoryRuntimeRouteDispatchEntry {
        method: SNAPSHOT_REPOSITORY_ROUTE_METHOD_PUT,
        path: PUT_SNAPSHOT_REPOSITORY_ROUTE_PATH,
        handler_kind: SnapshotRepositoryRuntimeHandlerKind::Mutation,
    },
    SnapshotRepositoryRuntimeRouteDispatchEntry {
        method: SNAPSHOT_REPOSITORY_ROUTE_METHOD_POST,
        path: POST_SNAPSHOT_REPOSITORY_ROUTE_PATH,
        handler_kind: SnapshotRepositoryRuntimeHandlerKind::Mutation,
    },
    SnapshotRepositoryRuntimeRouteDispatchEntry {
        method: SNAPSHOT_REPOSITORY_ROUTE_METHOD_POST,
        path: VERIFY_SNAPSHOT_REPOSITORY_ROUTE_PATH,
        handler_kind: SnapshotRepositoryRuntimeHandlerKind::Verify,
    },
];

pub fn resolve_snapshot_repository_runtime_handler(
    method: &str,
    path: &str,
) -> Option<SnapshotRepositoryRuntimeHandlerKind> {
    SNAPSHOT_REPOSITORY_RUNTIME_DISPATCH_TABLE
        .iter()
        .find(|entry| entry.method == method && entry.path == path)
        .map(|entry| entry.handler_kind)
}

pub fn run_snapshot_repository_local_route_activation(
    method: &str,
    path: &str,
    repositories: &serde_json::Value,
    repository: Option<&str>,
    body: &serde_json::Value,
    verification: &serde_json::Value,
) -> Option<serde_json::Value> {
    match resolve_snapshot_repository_runtime_handler(method, path)? {
        SnapshotRepositoryRuntimeHandlerKind::Readback => Some(
            (SNAPSHOT_REPOSITORY_RUNTIME_REGISTRATION_BODY.readback)(repositories, repository),
        ),
        SnapshotRepositoryRuntimeHandlerKind::Mutation => {
            Some((SNAPSHOT_REPOSITORY_RUNTIME_REGISTRATION_BODY.mutation)(body))
        }
        SnapshotRepositoryRuntimeHandlerKind::Verify => Some(
            (SNAPSHOT_REPOSITORY_RUNTIME_REGISTRATION_BODY.verify)(verification),
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snapshot_repository_registry_table_covers_global_named_mutation_and_verify_forms() {
        assert_eq!(SNAPSHOT_REPOSITORY_ROUTE_REGISTRY_TABLE.len(), 5);
        assert_eq!(SNAPSHOT_REPOSITORY_ROUTE_REGISTRY_TABLE[0].path, "/_snapshot");
        assert_eq!(SNAPSHOT_REPOSITORY_ROUTE_REGISTRY_TABLE[1].path, "/_snapshot/{repository}");
        assert_eq!(
            SNAPSHOT_REPOSITORY_ROUTE_REGISTRY_TABLE[4].path,
            "/_snapshot/{repository}/_verify"
        );
    }

    #[test]
    fn snapshot_repository_body_subset_keeps_type_and_settings_only() {
        let subset = build_snapshot_repository_body_subset(&serde_json::json!({
            "type": "fs",
            "settings": {
                "location": "/tmp/steelsearch-repo"
            },
            "verify": true
        }));

        assert_eq!(subset["type"], "fs");
        assert_eq!(subset["settings"]["location"], "/tmp/steelsearch-repo");
        assert!(subset.get("verify").is_none());
    }

    #[test]
    fn snapshot_repository_readback_response_filters_to_named_repository_and_bounded_fields() {
        let response = build_snapshot_repository_readback_response(
            &serde_json::json!({
                "repo-a": {
                    "type": "fs",
                    "settings": {
                        "location": "/tmp/a"
                    },
                    "uuid": "extra"
                },
                "repo-b": {
                    "type": "fs",
                    "settings": {
                        "location": "/tmp/b"
                    }
                }
            }),
            Some("repo-a"),
        );

        assert!(response.get("repo-a").is_some());
        assert!(response.get("repo-b").is_none());
        assert!(response["repo-a"].get("uuid").is_none());
    }

    #[test]
    fn snapshot_repository_verify_response_keeps_nodes_shape() {
        let response = build_snapshot_repository_verify_response(&serde_json::json!({
            "nodes": {
                "node-a": {
                    "name": "node-a"
                }
            },
            "repository": "repo-a"
        }));

        assert!(response.get("nodes").is_some());
        assert!(response.get("repository").is_none());
    }

    #[test]
    fn snapshot_repository_live_hooks_reuse_bounded_helpers() {
        let readback = invoke_snapshot_repository_live_readback(
            &serde_json::json!({
                "repo-a": {
                    "type": "fs",
                    "settings": {
                        "location": "/tmp/repo-a"
                    }
                }
            }),
            Some("repo-a"),
        );
        let mutation = invoke_snapshot_repository_live_mutation(&serde_json::json!({
            "type": "fs",
            "settings": {
                "location": "/tmp/repo-a"
            }
        }));
        let verify = invoke_snapshot_repository_live_verify(&serde_json::json!({
            "nodes": {
                "node-a": {
                    "name": "node-a"
                }
            }
        }));

        assert_eq!(readback["repo-a"]["type"], "fs");
        assert_eq!(mutation["acknowledged"], true);
        assert!(verify.get("nodes").is_some());
    }

    #[test]
    fn snapshot_repository_runtime_registration_body_points_at_bounded_live_hooks() {
        let readback = (SNAPSHOT_REPOSITORY_RUNTIME_REGISTRATION_BODY.readback)(
            &serde_json::json!({
                "repo-a": {
                    "type": "fs",
                    "settings": {
                        "location": "/tmp/repo-a"
                    }
                }
            }),
            Some("repo-a"),
        );
        let mutation = (SNAPSHOT_REPOSITORY_RUNTIME_REGISTRATION_BODY.mutation)(
            &serde_json::json!({
                "type": "fs",
                "settings": {
                    "location": "/tmp/repo-a"
                }
            }),
        );
        let verify = (SNAPSHOT_REPOSITORY_RUNTIME_REGISTRATION_BODY.verify)(&serde_json::json!({
            "nodes": {
                "node-a": {
                    "name": "node-a"
                }
            }
        }));

        assert_eq!(readback["repo-a"]["type"], "fs");
        assert_eq!(mutation["acknowledged"], true);
        assert!(verify.get("nodes").is_some());
    }

    #[test]
    fn snapshot_repository_runtime_dispatch_table_covers_readback_mutation_and_verify_paths() {
        assert_eq!(SNAPSHOT_REPOSITORY_RUNTIME_DISPATCH_TABLE.len(), 5);
        assert_eq!(
            SNAPSHOT_REPOSITORY_RUNTIME_DISPATCH_TABLE[0].handler_kind,
            SnapshotRepositoryRuntimeHandlerKind::Readback
        );
        assert_eq!(
            SNAPSHOT_REPOSITORY_RUNTIME_DISPATCH_TABLE[2].handler_kind,
            SnapshotRepositoryRuntimeHandlerKind::Mutation
        );
        assert_eq!(
            SNAPSHOT_REPOSITORY_RUNTIME_DISPATCH_TABLE[4].handler_kind,
            SnapshotRepositoryRuntimeHandlerKind::Verify
        );
        assert_eq!(
            SNAPSHOT_REPOSITORY_RUNTIME_DISPATCH_TABLE[4].path,
            "/_snapshot/{repository}/_verify"
        );
    }

    #[test]
    fn snapshot_repository_runtime_handler_resolution_matches_dispatch_table() {
        assert_eq!(
            resolve_snapshot_repository_runtime_handler("GET", "/_snapshot"),
            Some(SnapshotRepositoryRuntimeHandlerKind::Readback)
        );
        assert_eq!(
            resolve_snapshot_repository_runtime_handler("PUT", "/_snapshot/{repository}"),
            Some(SnapshotRepositoryRuntimeHandlerKind::Mutation)
        );
        assert_eq!(
            resolve_snapshot_repository_runtime_handler(
                "POST",
                "/_snapshot/{repository}/_verify"
            ),
            Some(SnapshotRepositoryRuntimeHandlerKind::Verify)
        );
    }

    #[test]
    fn snapshot_repository_local_route_activation_harness_reuses_runtime_dispatch() {
        let readback = run_snapshot_repository_local_route_activation(
            "GET",
            "/_snapshot/{repository}",
            &serde_json::json!({
                "repo-a": {
                    "type": "fs",
                    "settings": {
                        "location": "/tmp/repo-a"
                    }
                }
            }),
            Some("repo-a"),
            &serde_json::json!({}),
            &serde_json::json!({}),
        )
        .expect("readback response");
        let mutation = run_snapshot_repository_local_route_activation(
            "PUT",
            "/_snapshot/{repository}",
            &serde_json::json!({}),
            Some("repo-a"),
            &serde_json::json!({
                "type": "fs",
                "settings": {
                    "location": "/tmp/repo-a"
                }
            }),
            &serde_json::json!({}),
        )
        .expect("mutation response");
        let verify = run_snapshot_repository_local_route_activation(
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
                }
            }),
        )
        .expect("verify response");

        assert_eq!(readback["repo-a"]["type"], "fs");
        assert_eq!(mutation["acknowledged"], true);
        assert!(verify.get("nodes").is_some());
    }
}
