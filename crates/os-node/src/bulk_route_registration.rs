//! Workspace-visible route-registration anchors for bounded bulk metadata semantics.

pub const BULK_ROUTE_METHOD: &str = "POST";
pub const BULK_ROUTE_FAMILY: &str = "bulk";
pub const GLOBAL_BULK_ROUTE_PATH: &str = "/_bulk";
pub const INDEX_SCOPED_BULK_ROUTE_PATH: &str = "/{index}/_bulk";

pub const BULK_ACTION_TYPES: [&str; 4] = ["index", "create", "update", "delete"];
pub const BULK_ACTION_METADATA_FIELDS: [&str; 5] =
    ["_index", "_id", "routing", "if_seq_no", "if_primary_term"];
pub const BULK_RESPONSE_FIELDS: [&str; 3] = ["took", "errors", "items"];
pub const BULK_ITEM_RESPONSE_FIELDS: [&str; 7] = [
    "_index",
    "_id",
    "status",
    "result",
    "_version",
    "_seq_no",
    "_primary_term",
];
pub const BULK_INDEX_RESULT_CLASSES: [&str; 2] = ["created", "updated"];
pub const BULK_CREATE_RESULT_CLASSES: [&str; 1] = ["created"];
pub const BULK_UPDATE_RESULT_CLASSES: [&str; 2] = ["updated", "created"];
pub const BULK_DELETE_RESULT_CLASSES: [&str; 2] = ["deleted", "not_found"];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BulkRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

fn build_bulk_action_meta_subset(meta: &serde_json::Value) -> serde_json::Value {
    let Some(object) = meta.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in BULK_ACTION_METADATA_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_bulk_action_line_subset(
    line: &serde_json::Value,
    default_index: Option<&str>,
) -> serde_json::Value {
    let Some(object) = line.as_object() else {
        return serde_json::json!({});
    };

    for action in BULK_ACTION_TYPES {
        if let Some(meta) = object.get(action) {
            let mut subset = build_bulk_action_meta_subset(meta);
            if let Some(default_index) = default_index {
                if subset.get("_index").is_none() {
                    if let Some(meta_object) = subset.as_object_mut() {
                        meta_object.insert(
                            "_index".to_string(),
                            serde_json::Value::String(default_index.to_string()),
                        );
                    }
                }
            }
            return serde_json::json!({ action: subset });
        }
    }

    serde_json::json!({})
}

fn build_bulk_item_response_subset(item: &serde_json::Value) -> serde_json::Value {
    let Some(object) = item.as_object() else {
        return serde_json::json!({});
    };

    for action in BULK_ACTION_TYPES {
        if let Some(payload) = object.get(action) {
            let Some(payload_object) = payload.as_object() else {
                return serde_json::json!({});
            };
            let mut subset = serde_json::Map::new();
            for field in BULK_ITEM_RESPONSE_FIELDS {
                if let Some(value) = payload_object.get(field) {
                    subset.insert(field.to_string(), value.clone());
                }
            }
            if let Some(value) = payload_object.get("error") {
                subset.insert("error".to_string(), value.clone());
            }
            return serde_json::json!({ action: serde_json::Value::Object(subset) });
        }
    }

    serde_json::json!({})
}

pub fn build_bulk_response_subset(response: &serde_json::Value) -> serde_json::Value {
    let Some(object) = response.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in BULK_RESPONSE_FIELDS {
        match field {
            "items" => {
                if let Some(items) = object.get("items").and_then(serde_json::Value::as_array) {
                    subset.insert(
                        "items".to_string(),
                        serde_json::Value::Array(
                            items.iter().map(build_bulk_item_response_subset).collect(),
                        ),
                    );
                }
            }
            _ => {
                if let Some(value) = object.get(field) {
                    subset.insert(field.to_string(), value.clone());
                }
            }
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_bulk_item_body_subset(action: &str, body: &serde_json::Value) -> serde_json::Value {
    match action {
        "index" | "create" => body.clone(),
        "update" => {
            let Some(object) = body.as_object() else {
                return serde_json::json!({});
            };
            let mut subset = serde_json::Map::new();
            for field in ["doc", "upsert", "doc_as_upsert", "retry_on_conflict"] {
                if let Some(value) = object.get(field) {
                    subset.insert(field.to_string(), value.clone());
                }
            }
            serde_json::Value::Object(subset)
        }
        "delete" => serde_json::Value::Null,
        _ => serde_json::json!({}),
    }
}

pub fn supported_bulk_result_classes(action: &str) -> &'static [&'static str] {
    match action {
        "index" => &BULK_INDEX_RESULT_CLASSES,
        "create" => &BULK_CREATE_RESULT_CLASSES,
        "update" => &BULK_UPDATE_RESULT_CLASSES,
        "delete" => &BULK_DELETE_RESULT_CLASSES,
        _ => &[],
    }
}

pub const GLOBAL_BULK_ROUTE_REGISTRY_ENTRY: BulkRouteRegistryEntry = BulkRouteRegistryEntry {
    method: BULK_ROUTE_METHOD,
    path: GLOBAL_BULK_ROUTE_PATH,
    family: BULK_ROUTE_FAMILY,
};

pub const INDEX_SCOPED_BULK_ROUTE_REGISTRY_ENTRY: BulkRouteRegistryEntry = BulkRouteRegistryEntry {
    method: BULK_ROUTE_METHOD,
    path: INDEX_SCOPED_BULK_ROUTE_PATH,
    family: BULK_ROUTE_FAMILY,
};

pub const BULK_ROUTE_REGISTRY_TABLE: [BulkRouteRegistryEntry; 2] = [
    GLOBAL_BULK_ROUTE_REGISTRY_ENTRY,
    INDEX_SCOPED_BULK_ROUTE_REGISTRY_ENTRY,
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bulk_registry_table_describes_global_and_index_scoped_surfaces() {
        assert_eq!(GLOBAL_BULK_ROUTE_REGISTRY_ENTRY.method, "POST");
        assert_eq!(GLOBAL_BULK_ROUTE_REGISTRY_ENTRY.path, "/_bulk");
        assert_eq!(INDEX_SCOPED_BULK_ROUTE_REGISTRY_ENTRY.path, "/{index}/_bulk");
    }

    #[test]
    fn bulk_action_line_subset_keeps_bounded_meta_and_applies_default_index() {
        let subset = build_bulk_action_line_subset(
            &serde_json::json!({
                "index": {
                    "_id": "doc-1",
                    "routing": "tenant-a",
                    "pipeline": "ignored"
                }
            }),
            Some("logs-000001"),
        );

        assert_eq!(
            subset,
            serde_json::json!({
                "index": {
                    "_index": "logs-000001",
                    "_id": "doc-1",
                    "routing": "tenant-a"
                }
            })
        );
    }

    #[test]
    fn bulk_response_subset_keeps_top_level_and_item_metadata_shapes() {
        let subset = build_bulk_response_subset(&serde_json::json!({
            "took": 3,
            "errors": false,
            "items": [
                {
                    "index": {
                        "_index": "logs-000001",
                        "_id": "doc-1",
                        "status": 201,
                        "result": "created",
                        "_version": 1,
                        "_seq_no": 0,
                        "_primary_term": 1,
                        "_shards": {
                            "total": 1
                        }
                    }
                },
                {
                    "delete": {
                        "_index": "logs-000001",
                        "_id": "missing-doc",
                        "status": 404,
                        "result": "not_found",
                        "error": {
                            "type": "ignored"
                        }
                    }
                }
            ]
        }));

        assert_eq!(
            subset,
            serde_json::json!({
                "took": 3,
                "errors": false,
                "items": [
                    {
                        "index": {
                            "_index": "logs-000001",
                            "_id": "doc-1",
                            "status": 201,
                            "result": "created",
                            "_version": 1,
                            "_seq_no": 0,
                            "_primary_term": 1
                        }
                    },
                    {
                        "delete": {
                            "_index": "logs-000001",
                            "_id": "missing-doc",
                            "status": 404,
                            "result": "not_found",
                            "error": {
                                "type": "ignored"
                            }
                        }
                    }
                ]
            })
        );
    }

    #[test]
    fn bulk_item_body_subset_distinguishes_item_type_semantics() {
        assert_eq!(
            build_bulk_item_body_subset(
                "index",
                &serde_json::json!({
                    "message": "hello"
                })
            ),
            serde_json::json!({
                "message": "hello"
            })
        );
        assert_eq!(
            build_bulk_item_body_subset(
                "update",
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
                })
            ),
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
        assert_eq!(build_bulk_item_body_subset("delete", &serde_json::json!({})), serde_json::Value::Null);
    }

    #[test]
    fn bulk_result_classes_are_bounded_per_item_type() {
        assert_eq!(supported_bulk_result_classes("index"), &["created", "updated"]);
        assert_eq!(supported_bulk_result_classes("create"), &["created"]);
        assert_eq!(supported_bulk_result_classes("update"), &["updated", "created"]);
        assert_eq!(supported_bulk_result_classes("delete"), &["deleted", "not_found"]);
    }
}
