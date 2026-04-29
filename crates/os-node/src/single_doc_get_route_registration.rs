//! Workspace-visible route-registration anchors for bounded single-document GET semantics.

pub const GET_DOC_ROUTE_METHOD: &str = "GET";
pub const GET_DOC_ROUTE_PATH: &str = "/{index}/_doc/{id}";
pub const GET_DOC_ROUTE_FAMILY: &str = "single_doc_get";

pub const GET_DOC_REQUEST_QUERY_FIELDS: [&str; 5] = [
    "_source",
    "_source_includes",
    "_source_excludes",
    "realtime",
    "routing",
];
pub const GET_DOC_RESPONSE_FIELDS: [&str; 6] =
    ["_index", "_id", "_version", "_seq_no", "_primary_term", "found"];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SingleDocGetRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub fn build_get_doc_query_subset(query: &serde_json::Value) -> serde_json::Value {
    let Some(object) = query.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in GET_DOC_REQUEST_QUERY_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_get_doc_response_subset(response: &serde_json::Value) -> serde_json::Value {
    let Some(object) = response.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in GET_DOC_RESPONSE_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    if let Some(source) = object.get("_source") {
        subset.insert("_source".to_string(), source.clone());
    }
    serde_json::Value::Object(subset)
}

pub fn build_get_doc_not_found_response(index: &str, id: &str) -> serde_json::Value {
    serde_json::json!({
        "_index": index,
        "_id": id,
        "found": false
    })
}

pub const GET_DOC_ROUTE_REGISTRY_ENTRY: SingleDocGetRouteRegistryEntry =
    SingleDocGetRouteRegistryEntry {
        method: GET_DOC_ROUTE_METHOD,
        path: GET_DOC_ROUTE_PATH,
        family: GET_DOC_ROUTE_FAMILY,
    };

pub const GET_DOC_ROUTE_REGISTRY_TABLE: [SingleDocGetRouteRegistryEntry; 1] =
    [GET_DOC_ROUTE_REGISTRY_ENTRY];

pub type SingleDocGetReadHook =
    fn(&serde_json::Value, &serde_json::Value) -> serde_json::Value;

pub fn invoke_get_doc_live_read(
    query: &serde_json::Value,
    response: &serde_json::Value,
) -> serde_json::Value {
    serde_json::json!({
        "request": build_get_doc_query_subset(query),
        "response": build_get_doc_response_subset(response)
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn get_doc_registry_entry_describes_id_bearing_get_surface() {
        assert_eq!(GET_DOC_ROUTE_REGISTRY_ENTRY.method, "GET");
        assert_eq!(GET_DOC_ROUTE_REGISTRY_ENTRY.path, "/{index}/_doc/{id}");
        assert_eq!(GET_DOC_ROUTE_REGISTRY_ENTRY.family, "single_doc_get");
    }

    #[test]
    fn get_doc_query_subset_keeps_source_filter_realtime_and_routing_only() {
        let subset = build_get_doc_query_subset(&serde_json::json!({
            "_source": true,
            "_source_includes": "message,level",
            "_source_excludes": "payload",
            "realtime": true,
            "routing": "tenant-a",
            "stored_fields": "message"
        }));

        assert_eq!(
            subset,
            serde_json::json!({
                "_source": true,
                "_source_includes": "message,level",
                "_source_excludes": "payload",
                "realtime": true,
                "routing": "tenant-a"
            })
        );
    }

    #[test]
    fn get_doc_response_subset_keeps_found_and_source_shape() {
        let subset = build_get_doc_response_subset(&serde_json::json!({
            "_index": "logs-000001",
            "_id": "doc-1",
            "_version": 2,
            "_seq_no": 8,
            "_primary_term": 3,
            "found": true,
            "_source": {
                "message": "hello"
            },
            "ignored": ["payload"]
        }));

        assert_eq!(
            subset,
            serde_json::json!({
                "_index": "logs-000001",
                "_id": "doc-1",
                "_version": 2,
                "_seq_no": 8,
                "_primary_term": 3,
                "found": true,
                "_source": {
                    "message": "hello"
                }
            })
        );
    }

    #[test]
    fn get_doc_not_found_response_keeps_open_search_shaped_found_false_envelope() {
        assert_eq!(
            build_get_doc_not_found_response("logs-000001", "missing-doc"),
            serde_json::json!({
                "_index": "logs-000001",
                "_id": "missing-doc",
                "found": false
            })
        );
    }

    #[test]
    fn get_doc_live_hook_reuses_bounded_query_and_response_shapes() {
        let envelope = invoke_get_doc_live_read(
            &serde_json::json!({
                "_source": true,
                "_source_includes": "message",
                "routing": "tenant-a",
                "stored_fields": "ignored"
            }),
            &serde_json::json!({
                "_index": "logs-000001",
                "_id": "doc-1",
                "_version": 3,
                "_seq_no": 9,
                "_primary_term": 4,
                "found": true,
                "_source": {
                    "message": "hello"
                },
                "ignored": "value"
            }),
        );

        assert_eq!(
            envelope,
            serde_json::json!({
                "request": {
                    "_source": true,
                    "_source_includes": "message",
                    "routing": "tenant-a"
                },
                "response": {
                    "_index": "logs-000001",
                    "_id": "doc-1",
                    "_version": 3,
                    "_seq_no": 9,
                    "_primary_term": 4,
                    "found": true,
                    "_source": {
                        "message": "hello"
                    }
                }
            })
        );
    }
}
