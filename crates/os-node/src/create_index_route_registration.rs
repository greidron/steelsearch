//! Workspace-visible route-registration anchors for bounded `PUT /{index}` parity work.

pub const CREATE_INDEX_ROUTE_METHOD: &str = "PUT";
pub const CREATE_INDEX_ROUTE_PATH: &str = "/{index}";
pub const CREATE_INDEX_ROUTE_FAMILY: &str = "create_index_body";

pub const CREATE_INDEX_BODY_FIELDS: [&str; 3] = ["settings", "mappings", "aliases"];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CreateIndexRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub fn build_create_index_body_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(object) = body.as_object() else {
        return serde_json::Value::Object(serde_json::Map::new());
    };

    let mut normalized = serde_json::Map::new();
    for field in CREATE_INDEX_BODY_FIELDS {
        if let Some(value) = object.get(field) {
            normalized.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(normalized)
}

pub const CREATE_INDEX_ROUTE_REGISTRY_ENTRY: CreateIndexRouteRegistryEntry =
    CreateIndexRouteRegistryEntry {
        method: CREATE_INDEX_ROUTE_METHOD,
        path: CREATE_INDEX_ROUTE_PATH,
        family: CREATE_INDEX_ROUTE_FAMILY,
    };

pub const CREATE_INDEX_ROUTE_REGISTRY_TABLE: [CreateIndexRouteRegistryEntry; 1] =
    [CREATE_INDEX_ROUTE_REGISTRY_ENTRY];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn create_index_registry_entry_describes_bounded_put_surface() {
        assert_eq!(CREATE_INDEX_ROUTE_REGISTRY_ENTRY.method, "PUT");
        assert_eq!(CREATE_INDEX_ROUTE_REGISTRY_ENTRY.path, "/{index}");
        assert_eq!(CREATE_INDEX_ROUTE_REGISTRY_ENTRY.family, "create_index_body");
    }

    #[test]
    fn create_index_body_subset_keeps_settings_mappings_and_aliases_only() {
        let normalized = build_create_index_body_subset(&serde_json::json!({
            "settings": {
                "index": {
                    "number_of_shards": 1
                }
            },
            "mappings": {
                "properties": {
                    "message": {
                        "type": "text"
                    }
                }
            },
            "aliases": {
                "logs-read": {}
            },
            "wait_for_active_shards": "all"
        }));

        assert!(normalized.get("settings").is_some());
        assert!(normalized.get("mappings").is_some());
        assert!(normalized.get("aliases").is_some());
        assert!(normalized.get("wait_for_active_shards").is_none());
    }

    #[test]
    fn create_index_body_subset_ignores_non_object_inputs() {
        let normalized = build_create_index_body_subset(&serde_json::json!(null));
        assert_eq!(normalized, serde_json::json!({}));
    }
}
