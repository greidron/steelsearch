//! Workspace-visible route-registration anchors for bounded generated-id document POST semantics.

pub const POST_DOC_ROUTE_METHOD: &str = "POST";
pub const POST_DOC_ROUTE_PATH: &str = "/{index}/_doc";
pub const POST_DOC_ROUTE_FAMILY: &str = "single_doc_post";

pub const POST_DOC_REQUEST_QUERY_FIELDS: [&str; 2] = ["routing", "refresh"];
pub const POST_DOC_RESPONSE_FIELDS: [&str; 7] = [
    "_index",
    "_id",
    "_version",
    "result",
    "_seq_no",
    "_primary_term",
    "forced_refresh",
];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SingleDocPostRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub type SingleDocPostWriteHook =
    fn(&serde_json::Value, &serde_json::Value) -> serde_json::Value;

pub fn build_post_doc_query_subset(query: &serde_json::Value) -> serde_json::Value {
    let Some(object) = query.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in POST_DOC_REQUEST_QUERY_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_post_doc_response_subset(response: &serde_json::Value) -> serde_json::Value {
    let Some(object) = response.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in POST_DOC_RESPONSE_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn invoke_post_doc_live_write(
    query: &serde_json::Value,
    response: &serde_json::Value,
) -> serde_json::Value {
    serde_json::json!({
        "request": build_post_doc_query_subset(query),
        "response": build_post_doc_response_subset(response)
    })
}

pub const POST_DOC_ROUTE_REGISTRY_ENTRY: SingleDocPostRouteRegistryEntry =
    SingleDocPostRouteRegistryEntry {
        method: POST_DOC_ROUTE_METHOD,
        path: POST_DOC_ROUTE_PATH,
        family: POST_DOC_ROUTE_FAMILY,
    };

pub const POST_DOC_ROUTE_REGISTRY_TABLE: [SingleDocPostRouteRegistryEntry; 1] =
    [POST_DOC_ROUTE_REGISTRY_ENTRY];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn post_doc_registry_entry_describes_generated_id_surface() {
        assert_eq!(POST_DOC_ROUTE_REGISTRY_ENTRY.method, "POST");
        assert_eq!(POST_DOC_ROUTE_REGISTRY_ENTRY.path, "/{index}/_doc");
        assert_eq!(POST_DOC_ROUTE_REGISTRY_ENTRY.family, "single_doc_post");
    }

    #[test]
    fn post_doc_query_subset_keeps_routing_and_refresh_only() {
        let subset = build_post_doc_query_subset(&serde_json::json!({
            "routing": "tenant-a",
            "refresh": "wait_for",
            "pipeline": "ingest-me"
        }));

        assert_eq!(
            subset,
            serde_json::json!({
                "routing": "tenant-a",
                "refresh": "wait_for"
            })
        );
    }

    #[test]
    fn post_doc_response_subset_keeps_generated_id_write_shape() {
        let subset = build_post_doc_response_subset(&serde_json::json!({
            "_index": "logs-000001",
            "_id": "generated-id",
            "_version": 1,
            "result": "created",
            "_seq_no": 9,
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
                "_id": "generated-id",
                "_version": 1,
                "result": "created",
                "_seq_no": 9,
                "_primary_term": 3,
                "forced_refresh": false
            })
        );
    }

    #[test]
    fn post_doc_live_write_hook_reuses_bounded_request_and_response_shapes() {
        let rendered = invoke_post_doc_live_write(
            &serde_json::json!({
                "routing": "tenant-a",
                "refresh": "wait_for",
                "pipeline": "ingest-me"
            }),
            &serde_json::json!({
                "_index": "logs-000001",
                "_id": "generated-id",
                "_version": 1,
                "result": "created",
                "_seq_no": 9,
                "_primary_term": 3,
                "forced_refresh": false
            }),
        );

        assert_eq!(rendered["request"]["routing"], "tenant-a");
        assert_eq!(rendered["request"]["refresh"], "wait_for");
        assert_eq!(rendered["response"]["_id"], "generated-id");
        assert_eq!(rendered["response"]["_version"], 1);
        assert_eq!(rendered["response"]["forced_refresh"], false);
    }
}
