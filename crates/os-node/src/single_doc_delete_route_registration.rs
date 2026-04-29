//! Workspace-visible route-registration anchors for bounded single-document DELETE semantics.

pub const DELETE_DOC_ROUTE_METHOD: &str = "DELETE";
pub const DELETE_DOC_ROUTE_PATH: &str = "/{index}/_doc/{id}";
pub const DELETE_DOC_ROUTE_FAMILY: &str = "single_doc_delete";

pub const DELETE_DOC_REQUEST_QUERY_FIELDS: [&str; 4] =
    ["routing", "if_seq_no", "if_primary_term", "refresh"];
pub const DELETE_DOC_RESPONSE_FIELDS: [&str; 6] = [
    "_index",
    "_id",
    "_version",
    "result",
    "_seq_no",
    "_primary_term",
];
pub const DELETE_DOC_NOT_FOUND_RESULT: &str = "not_found";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SingleDocDeleteRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub fn build_delete_doc_query_subset(query: &serde_json::Value) -> serde_json::Value {
    let Some(object) = query.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in DELETE_DOC_REQUEST_QUERY_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_delete_doc_response_subset(response: &serde_json::Value) -> serde_json::Value {
    let Some(object) = response.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in DELETE_DOC_RESPONSE_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    if let Some(value) = object.get("forced_refresh") {
        subset.insert("forced_refresh".to_string(), value.clone());
    }
    serde_json::Value::Object(subset)
}

pub fn build_delete_doc_not_found_response(index: &str, id: &str) -> serde_json::Value {
    serde_json::json!({
        "_index": index,
        "_id": id,
        "result": DELETE_DOC_NOT_FOUND_RESULT
    })
}

pub const DELETE_DOC_ROUTE_REGISTRY_ENTRY: SingleDocDeleteRouteRegistryEntry =
    SingleDocDeleteRouteRegistryEntry {
        method: DELETE_DOC_ROUTE_METHOD,
        path: DELETE_DOC_ROUTE_PATH,
        family: DELETE_DOC_ROUTE_FAMILY,
    };

pub const DELETE_DOC_ROUTE_REGISTRY_TABLE: [SingleDocDeleteRouteRegistryEntry; 1] =
    [DELETE_DOC_ROUTE_REGISTRY_ENTRY];

pub type SingleDocDeleteWriteHook =
    fn(&serde_json::Value, &serde_json::Value) -> serde_json::Value;

pub fn invoke_delete_doc_live_write(
    query: &serde_json::Value,
    response: &serde_json::Value,
) -> serde_json::Value {
    serde_json::json!({
        "request": build_delete_doc_query_subset(query),
        "response": build_delete_doc_response_subset(response)
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn delete_doc_registry_entry_describes_id_bearing_delete_surface() {
        assert_eq!(DELETE_DOC_ROUTE_REGISTRY_ENTRY.method, "DELETE");
        assert_eq!(DELETE_DOC_ROUTE_REGISTRY_ENTRY.path, "/{index}/_doc/{id}");
        assert_eq!(DELETE_DOC_ROUTE_REGISTRY_ENTRY.family, "single_doc_delete");
    }

    #[test]
    fn delete_doc_query_subset_keeps_routing_cas_and_refresh_only() {
        let subset = build_delete_doc_query_subset(&serde_json::json!({
            "routing": "tenant-a",
            "if_seq_no": 7,
            "if_primary_term": 3,
            "refresh": "wait_for",
            "version": 2
        }));

        assert_eq!(
            subset,
            serde_json::json!({
                "routing": "tenant-a",
                "if_seq_no": 7,
                "if_primary_term": 3,
                "refresh": "wait_for"
            })
        );
    }

    #[test]
    fn delete_doc_response_subset_keeps_bounded_delete_result_shape() {
        let subset = build_delete_doc_response_subset(&serde_json::json!({
            "_index": "logs-000001",
            "_id": "doc-1",
            "_version": 4,
            "result": "deleted",
            "_seq_no": 11,
            "_primary_term": 5,
            "forced_refresh": false,
            "_shards": {
                "total": 1
            }
        }));

        assert_eq!(
            subset,
            serde_json::json!({
                "_index": "logs-000001",
                "_id": "doc-1",
                "_version": 4,
                "result": "deleted",
                "_seq_no": 11,
                "_primary_term": 5,
                "forced_refresh": false
            })
        );
    }

    #[test]
    fn delete_doc_not_found_response_keeps_bounded_not_found_result_class() {
        assert_eq!(
            build_delete_doc_not_found_response("logs-000001", "missing-doc"),
            serde_json::json!({
                "_index": "logs-000001",
                "_id": "missing-doc",
                "result": "not_found"
            })
        );
    }

    #[test]
    fn delete_doc_live_hook_reuses_bounded_query_and_response_shapes() {
        let envelope = invoke_delete_doc_live_write(
            &serde_json::json!({
                "routing": "tenant-a",
                "if_seq_no": 7,
                "refresh": "wait_for",
                "version": 2
            }),
            &serde_json::json!({
                "_index": "logs-000001",
                "_id": "doc-1",
                "_version": 4,
                "result": "deleted",
                "_seq_no": 11,
                "_primary_term": 5,
                "forced_refresh": false,
                "_shards": {
                    "total": 1
                }
            }),
        );

        assert_eq!(
            envelope,
            serde_json::json!({
                "request": {
                    "routing": "tenant-a",
                    "if_seq_no": 7,
                    "refresh": "wait_for"
                },
                "response": {
                    "_index": "logs-000001",
                    "_id": "doc-1",
                    "_version": 4,
                    "result": "deleted",
                    "_seq_no": 11,
                    "_primary_term": 5,
                    "forced_refresh": false
                }
            })
        );
    }
}
