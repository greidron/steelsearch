//! Workspace-visible route-registration anchors for bounded single-document UPDATE semantics.

pub const UPDATE_DOC_ROUTE_METHOD: &str = "POST";
pub const UPDATE_DOC_ROUTE_PATH: &str = "/{index}/_update/{id}";
pub const UPDATE_DOC_ROUTE_FAMILY: &str = "single_doc_update";

pub const UPDATE_DOC_REQUEST_QUERY_FIELDS: [&str; 3] = ["routing", "refresh", "_source"];
pub const UPDATE_DOC_REQUEST_BODY_FIELDS: [&str; 4] =
    ["doc", "upsert", "doc_as_upsert", "retry_on_conflict"];
pub const UPDATE_DOC_RESPONSE_FIELDS: [&str; 6] = [
    "_index",
    "_id",
    "_version",
    "result",
    "_seq_no",
    "_primary_term",
];
pub const UPDATE_DOC_NOT_FOUND_BUCKET: &str = "document_missing_exception";
pub const UPDATE_DOC_VERSION_CONFLICT_BUCKET: &str = "version_conflict_engine_exception";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SingleDocUpdateRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub fn build_update_doc_query_subset(query: &serde_json::Value) -> serde_json::Value {
    let Some(object) = query.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in UPDATE_DOC_REQUEST_QUERY_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_update_doc_body_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(object) = body.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in UPDATE_DOC_REQUEST_BODY_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_update_doc_response_subset(response: &serde_json::Value) -> serde_json::Value {
    let Some(object) = response.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in UPDATE_DOC_RESPONSE_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    if let Some(value) = object.get("forced_refresh") {
        subset.insert("forced_refresh".to_string(), value.clone());
    }
    serde_json::Value::Object(subset)
}

pub fn build_update_doc_not_found_error(index: &str, id: &str) -> serde_json::Value {
    serde_json::json!({
        "error": {
            "type": UPDATE_DOC_NOT_FOUND_BUCKET,
            "reason": format!("[{id}]: document missing in index [{index}]")
        },
        "status": 404
    })
}

pub fn build_update_doc_version_conflict_error(index: &str, id: &str) -> serde_json::Value {
    serde_json::json!({
        "error": {
            "type": UPDATE_DOC_VERSION_CONFLICT_BUCKET,
            "reason": format!("[{id}]: version conflict in index [{index}]")
        },
        "status": 409
    })
}

pub const UPDATE_DOC_ROUTE_REGISTRY_ENTRY: SingleDocUpdateRouteRegistryEntry =
    SingleDocUpdateRouteRegistryEntry {
        method: UPDATE_DOC_ROUTE_METHOD,
        path: UPDATE_DOC_ROUTE_PATH,
        family: UPDATE_DOC_ROUTE_FAMILY,
    };

pub const UPDATE_DOC_ROUTE_REGISTRY_TABLE: [SingleDocUpdateRouteRegistryEntry; 1] =
    [UPDATE_DOC_ROUTE_REGISTRY_ENTRY];

pub type SingleDocUpdateWriteHook =
    fn(&serde_json::Value, &serde_json::Value, &serde_json::Value) -> serde_json::Value;

pub fn invoke_update_doc_live_write(
    query: &serde_json::Value,
    body: &serde_json::Value,
    response: &serde_json::Value,
) -> serde_json::Value {
    serde_json::json!({
        "request": {
            "query": build_update_doc_query_subset(query),
            "body": build_update_doc_body_subset(body)
        },
        "response": build_update_doc_response_subset(response)
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn update_doc_registry_entry_describes_partial_update_surface() {
        assert_eq!(UPDATE_DOC_ROUTE_REGISTRY_ENTRY.method, "POST");
        assert_eq!(UPDATE_DOC_ROUTE_REGISTRY_ENTRY.path, "/{index}/_update/{id}");
        assert_eq!(UPDATE_DOC_ROUTE_REGISTRY_ENTRY.family, "single_doc_update");
    }

    #[test]
    fn update_doc_query_subset_keeps_routing_refresh_and_source_only() {
        let subset = build_update_doc_query_subset(&serde_json::json!({
            "routing": "tenant-a",
            "refresh": "wait_for",
            "_source": true,
            "if_seq_no": 7
        }));

        assert_eq!(
            subset,
            serde_json::json!({
                "routing": "tenant-a",
                "refresh": "wait_for",
                "_source": true
            })
        );
    }

    #[test]
    fn update_doc_body_subset_keeps_bounded_partial_update_controls_only() {
        let subset = build_update_doc_body_subset(&serde_json::json!({
            "doc": {
                "message": "hello"
            },
            "upsert": {
                "message": "seed"
            },
            "doc_as_upsert": true,
            "retry_on_conflict": 3,
            "script": {
                "source": "ctx._source.count += 1"
            }
        }));

        assert_eq!(
            subset,
            serde_json::json!({
                "doc": {
                    "message": "hello"
                },
                "upsert": {
                    "message": "seed"
                },
                "doc_as_upsert": true,
                "retry_on_conflict": 3
            })
        );
    }

    #[test]
    fn update_doc_response_subset_keeps_bounded_result_shape() {
        let subset = build_update_doc_response_subset(&serde_json::json!({
            "_index": "logs-000001",
            "_id": "doc-1",
            "_version": 4,
            "result": "updated",
            "_seq_no": 11,
            "_primary_term": 5,
            "forced_refresh": false,
            "get": {
                "found": true
            }
        }));

        assert_eq!(
            subset,
            serde_json::json!({
                "_index": "logs-000001",
                "_id": "doc-1",
                "_version": 4,
                "result": "updated",
                "_seq_no": 11,
                "_primary_term": 5,
                "forced_refresh": false
            })
        );
    }

    #[test]
    fn update_doc_error_helpers_keep_not_found_and_conflict_classes() {
        let missing = build_update_doc_not_found_error("logs-000001", "missing-doc");
        let conflict = build_update_doc_version_conflict_error("logs-000001", "doc-1");

        assert_eq!(
            missing["error"]["type"],
            serde_json::json!(UPDATE_DOC_NOT_FOUND_BUCKET)
        );
        assert_eq!(missing["status"], serde_json::json!(404));
        assert_eq!(
            conflict["error"]["type"],
            serde_json::json!(UPDATE_DOC_VERSION_CONFLICT_BUCKET)
        );
        assert_eq!(conflict["status"], serde_json::json!(409));
    }

    #[test]
    fn update_doc_live_hook_reuses_bounded_query_body_and_response_shapes() {
        let envelope = invoke_update_doc_live_write(
            &serde_json::json!({
                "routing": "tenant-a",
                "refresh": "wait_for",
                "_source": true,
                "if_seq_no": 7
            }),
            &serde_json::json!({
                "doc": {
                    "message": "hello"
                },
                "upsert": {
                    "message": "seed"
                },
                "doc_as_upsert": true,
                "retry_on_conflict": 3,
                "script": {
                    "source": "ctx._source.count += 1"
                }
            }),
            &serde_json::json!({
                "_index": "logs-000001",
                "_id": "doc-1",
                "_version": 4,
                "result": "updated",
                "_seq_no": 11,
                "_primary_term": 5,
                "forced_refresh": false,
                "get": {
                    "found": true
                }
            }),
        );

        assert_eq!(
            envelope,
            serde_json::json!({
                "request": {
                    "query": {
                        "routing": "tenant-a",
                        "refresh": "wait_for",
                        "_source": true
                    },
                    "body": {
                        "doc": {
                            "message": "hello"
                        },
                        "upsert": {
                            "message": "seed"
                        },
                        "doc_as_upsert": true,
                        "retry_on_conflict": 3
                    }
                },
                "response": {
                    "_index": "logs-000001",
                    "_id": "doc-1",
                    "_version": 4,
                    "result": "updated",
                    "_seq_no": 11,
                    "_primary_term": 5,
                    "forced_refresh": false
                }
            })
        );
    }
}
