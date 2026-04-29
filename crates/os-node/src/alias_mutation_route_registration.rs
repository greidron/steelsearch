//! Workspace-visible route-registration anchors for bounded alias mutation work.

pub const PUT_ALIAS_ROUTE_METHOD: &str = "PUT";
pub const POST_ALIAS_ROUTE_METHOD: &str = "POST";
pub const DELETE_ALIAS_ROUTE_METHOD: &str = "DELETE";
pub const INDEX_ALIAS_ROUTE_PATH: &str = "/{index}/_alias/{name}";
pub const BULK_ALIASES_ROUTE_PATH: &str = "/_aliases";
pub const ALIAS_MUTATION_ROUTE_FAMILY: &str = "alias_mutation";
pub const ALIAS_DELETE_ROUTE_FAMILY: &str = "alias_delete";

pub const BOUNDED_ALIAS_METADATA_FIELDS: [&str; 5] = [
    "filter",
    "routing",
    "index_routing",
    "search_routing",
    "is_write_index",
];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AliasMutationRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub fn build_alias_metadata_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(object) = body.as_object() else {
        return serde_json::json!({});
    };

    let mut subset = serde_json::Map::new();
    for field in BOUNDED_ALIAS_METADATA_FIELDS {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_single_alias_add_action(
    index: &str,
    alias: &str,
    body: &serde_json::Value,
) -> serde_json::Value {
    let mut add = serde_json::Map::new();
    add.insert("index".to_string(), serde_json::Value::String(index.to_string()));
    add.insert("alias".to_string(), serde_json::Value::String(alias.to_string()));

    if let Some(metadata) = build_alias_metadata_subset(body).as_object() {
        for (key, value) in metadata {
            add.insert(key.clone(), value.clone());
        }
    }

    serde_json::json!({
        "actions": [
            {
                "add": add
            }
        ]
    })
}

pub fn build_single_alias_remove_action(index: &str, alias: &str) -> serde_json::Value {
    serde_json::json!({
        "actions": [
            {
                "remove": {
                    "index": index,
                    "alias": alias
                }
            }
        ]
    })
}

pub fn build_bulk_alias_actions_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(actions) = body.get("actions").and_then(|value| value.as_array()) else {
        return serde_json::json!({ "actions": [] });
    };

    let mut bounded_actions = Vec::new();
    for action in actions {
        if let Some(add) = action.get("add").and_then(|value| value.as_object()) {
            let mut bounded_add = serde_json::Map::new();
            for field in ["index", "alias"] {
                if let Some(value) = add.get(field) {
                    bounded_add.insert(field.to_string(), value.clone());
                }
            }
            for field in BOUNDED_ALIAS_METADATA_FIELDS {
                if let Some(value) = add.get(field) {
                    bounded_add.insert(field.to_string(), value.clone());
                }
            }
            bounded_actions.push(serde_json::json!({ "add": bounded_add }));
            continue;
        }

        if let Some(remove) = action.get("remove").and_then(|value| value.as_object()) {
            let mut bounded_remove = serde_json::Map::new();
            for field in ["index", "alias"] {
                if let Some(value) = remove.get(field) {
                    bounded_remove.insert(field.to_string(), value.clone());
                }
            }
            bounded_actions.push(serde_json::json!({ "remove": bounded_remove }));
        }
    }

    serde_json::json!({
        "actions": bounded_actions
    })
}

pub fn build_alias_mutation_acknowledged_response() -> serde_json::Value {
    serde_json::json!({
        "acknowledged": true
    })
}

pub const ALIAS_MUTATION_ROUTE_REGISTRY_TABLE: [AliasMutationRouteRegistryEntry; 4] = [
    AliasMutationRouteRegistryEntry {
        method: PUT_ALIAS_ROUTE_METHOD,
        path: INDEX_ALIAS_ROUTE_PATH,
        family: ALIAS_MUTATION_ROUTE_FAMILY,
    },
    AliasMutationRouteRegistryEntry {
        method: POST_ALIAS_ROUTE_METHOD,
        path: INDEX_ALIAS_ROUTE_PATH,
        family: ALIAS_MUTATION_ROUTE_FAMILY,
    },
    AliasMutationRouteRegistryEntry {
        method: POST_ALIAS_ROUTE_METHOD,
        path: BULK_ALIASES_ROUTE_PATH,
        family: ALIAS_MUTATION_ROUTE_FAMILY,
    },
    AliasMutationRouteRegistryEntry {
        method: DELETE_ALIAS_ROUTE_METHOD,
        path: INDEX_ALIAS_ROUTE_PATH,
        family: ALIAS_DELETE_ROUTE_FAMILY,
    },
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn alias_mutation_registry_table_describes_add_bulk_and_delete_routes() {
        assert_eq!(ALIAS_MUTATION_ROUTE_REGISTRY_TABLE.len(), 4);
        assert_eq!(ALIAS_MUTATION_ROUTE_REGISTRY_TABLE[0].method, "PUT");
        assert_eq!(ALIAS_MUTATION_ROUTE_REGISTRY_TABLE[1].method, "POST");
        assert_eq!(ALIAS_MUTATION_ROUTE_REGISTRY_TABLE[2].path, "/_aliases");
        assert_eq!(ALIAS_MUTATION_ROUTE_REGISTRY_TABLE[3].method, "DELETE");
    }

    #[test]
    fn alias_metadata_subset_keeps_bounded_alias_fields_only() {
        let subset = build_alias_metadata_subset(&serde_json::json!({
            "filter": { "term": { "service": "logs" } },
            "routing": "r1",
            "is_write_index": true,
            "hidden": true
        }));

        assert!(subset.get("filter").is_some());
        assert!(subset.get("routing").is_some());
        assert!(subset.get("is_write_index").is_some());
        assert!(subset.get("hidden").is_none());
    }

    #[test]
    fn single_alias_add_action_reuses_bounded_metadata_subset() {
        let action = build_single_alias_add_action(
            "logs-000001",
            "logs-read",
            &serde_json::json!({
                "filter": { "term": { "service": "logs" } },
                "routing": "r1",
                "hidden": true
            }),
        );

        assert_eq!(action["actions"][0]["add"]["index"], "logs-000001");
        assert_eq!(action["actions"][0]["add"]["alias"], "logs-read");
        assert!(action["actions"][0]["add"].get("filter").is_some());
        assert!(action["actions"][0]["add"].get("routing").is_some());
        assert!(action["actions"][0]["add"].get("hidden").is_none());
    }

    #[test]
    fn bulk_alias_actions_subset_keeps_bounded_add_remove_shapes_only() {
        let subset = build_bulk_alias_actions_subset(&serde_json::json!({
            "actions": [
                {
                    "add": {
                        "index": "logs-000001",
                        "alias": "logs-read",
                        "is_write_index": true,
                        "hidden": true
                    }
                },
                {
                    "remove": {
                        "index": "logs-000001",
                        "alias": "logs-read",
                        "must_exist": true
                    }
                }
            ]
        }));

        assert_eq!(subset["actions"][0]["add"]["index"], "logs-000001");
        assert_eq!(subset["actions"][0]["add"]["alias"], "logs-read");
        assert_eq!(subset["actions"][0]["add"]["is_write_index"], true);
        assert!(subset["actions"][0]["add"].get("hidden").is_none());
        assert_eq!(subset["actions"][1]["remove"]["index"], "logs-000001");
        assert_eq!(subset["actions"][1]["remove"]["alias"], "logs-read");
        assert!(subset["actions"][1]["remove"].get("must_exist").is_none());
    }
}
