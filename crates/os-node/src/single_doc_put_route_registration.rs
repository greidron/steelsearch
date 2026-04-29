//! Workspace-visible route-registration anchors for bounded single-document PUT semantics.

pub const PUT_DOC_ROUTE_METHOD: &str = "PUT";
pub const PUT_DOC_ROUTE_PATH: &str = "/{index}/_doc/{id}";
pub const PUT_DOC_ROUTE_FAMILY: &str = "single_doc_put";

pub const PUT_DOC_REQUEST_QUERY_FIELDS: [&str; 3] = ["routing", "if_seq_no", "if_primary_term"];
pub const PUT_DOC_RESPONSE_FIELDS: [&str; 6] = [
    "_index",
    "_id",
    "_version",
    "result",
    "_seq_no",
    "_primary_term",
];
pub const PUT_DOC_POST_WRITE_VISIBILITY_FIELDS: [&str; 1] = ["forced_refresh"];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SingleDocPutRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub type SingleDocPutWriteHook =
    fn(&serde_json::Value, &serde_json::Value) -> serde_json::Value;

pub fn build_put_doc_query_subset(query: &serde_json::Value) -> serde_json::Value {
    let Some(object) = query.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in PUT_DOC_REQUEST_QUERY_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_put_doc_response_subset(response: &serde_json::Value) -> serde_json::Value {
    let Some(object) = response.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in PUT_DOC_RESPONSE_FIELDS
        .iter()
        .chain(PUT_DOC_POST_WRITE_VISIBILITY_FIELDS.iter())
    {
        if let Some(value) = object.get(*field) {
            subset.insert((*field).to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn invoke_put_doc_live_write(
    query: &serde_json::Value,
    response: &serde_json::Value,
) -> serde_json::Value {
    serde_json::json!({
        "request": build_put_doc_query_subset(query),
        "response": build_put_doc_response_subset(response)
    })
}

pub const PUT_DOC_ROUTE_REGISTRY_ENTRY: SingleDocPutRouteRegistryEntry =
    SingleDocPutRouteRegistryEntry {
        method: PUT_DOC_ROUTE_METHOD,
        path: PUT_DOC_ROUTE_PATH,
        family: PUT_DOC_ROUTE_FAMILY,
    };

pub const PUT_DOC_ROUTE_REGISTRY_TABLE: [SingleDocPutRouteRegistryEntry; 1] =
    [PUT_DOC_ROUTE_REGISTRY_ENTRY];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn put_doc_registry_entry_describes_id_bearing_put_surface() {
        assert_eq!(PUT_DOC_ROUTE_REGISTRY_ENTRY.method, "PUT");
        assert_eq!(PUT_DOC_ROUTE_REGISTRY_ENTRY.path, "/{index}/_doc/{id}");
        assert_eq!(PUT_DOC_ROUTE_REGISTRY_ENTRY.family, "single_doc_put");
    }

    #[test]
    fn put_doc_query_subset_keeps_routing_and_optimistic_concurrency_only() {
        let subset = build_put_doc_query_subset(&serde_json::json!({
            "routing": "tenant-a",
            "if_seq_no": 7,
            "if_primary_term": 3,
            "refresh": "wait_for"
        }));

        assert_eq!(
            subset,
            serde_json::json!({
                "routing": "tenant-a",
                "if_seq_no": 7,
                "if_primary_term": 3
            })
        );
    }

    #[test]
    fn put_doc_response_subset_keeps_version_seq_no_primary_term_and_visibility_shape() {
        let subset = build_put_doc_response_subset(&serde_json::json!({
            "_index": "logs-000001",
            "_id": "doc-1",
            "_version": 2,
            "result": "updated",
            "_seq_no": 8,
            "_primary_term": 3,
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
                "_version": 2,
                "result": "updated",
                "_seq_no": 8,
                "_primary_term": 3,
                "forced_refresh": false
            })
        );
    }

    #[test]
    fn put_doc_live_write_hook_reuses_bounded_request_and_response_shapes() {
        let rendered = invoke_put_doc_live_write(
            &serde_json::json!({
                "routing": "tenant-a",
                "if_seq_no": 7,
                "if_primary_term": 3,
                "refresh": "wait_for"
            }),
            &serde_json::json!({
                "_index": "logs-000001",
                "_id": "doc-1",
                "_version": 2,
                "result": "updated",
                "_seq_no": 8,
                "_primary_term": 3,
                "forced_refresh": false
            }),
        );

        assert_eq!(rendered["request"]["routing"], "tenant-a");
        assert_eq!(rendered["request"]["if_seq_no"], 7);
        assert_eq!(rendered["response"]["_version"], 2);
        assert_eq!(rendered["response"]["_primary_term"], 3);
        assert_eq!(rendered["response"]["forced_refresh"], false);
    }
}
