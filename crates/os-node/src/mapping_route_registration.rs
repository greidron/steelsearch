//! Workspace-visible route-registration anchors for bounded mapping readback work.

pub const GET_GLOBAL_MAPPING_ROUTE_METHOD: &str = "GET";
pub const GET_GLOBAL_MAPPING_ROUTE_PATH: &str = "/_mapping";
pub const GET_GLOBAL_FIELD_MAPPING_ROUTE_PATH: &str = "/_mapping/field/{fields}";
pub const GET_INDEX_MAPPING_ROUTE_PATH: &str = "/{index}/_mapping";
pub const GET_INDEX_FIELD_MAPPING_ROUTE_PATH: &str = "/{index}/_mapping/field/{fields}";
pub const PUT_INDEX_MAPPING_ROUTE_METHOD: &str = "PUT";
pub const MAPPING_ROUTE_FAMILY: &str = "mapping_readback";
pub const MAPPING_UPDATE_ROUTE_FAMILY: &str = "mapping_update";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MappingRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub fn parse_mapping_selectors(target: &str) -> Vec<String> {
    target
        .split(',')
        .map(str::trim)
        .filter(|segment| !segment.is_empty())
        .map(ToOwned::to_owned)
        .collect()
}

fn selector_matches(selector: &str, index: &str) -> bool {
    if let Some(prefix) = selector.strip_suffix('*') {
        index.starts_with(prefix)
    } else {
        selector == index
    }
}

fn field_selector_matches(selector: &str, field: &str) -> bool {
    if let Some(prefix) = selector.strip_suffix('*') {
        field.starts_with(prefix)
    } else {
        selector == field
    }
}

pub fn build_mapping_readback_response(
    indices: &serde_json::Value,
    target: Option<&str>,
) -> serde_json::Value {
    let selectors = target.map(parse_mapping_selectors).unwrap_or_default();
    let Some(index_map) = indices.as_object() else {
        return serde_json::json!({});
    };

    let mut response = serde_json::Map::new();
    for (name, metadata) in index_map {
        if !selectors.is_empty()
            && !selectors.iter().any(|selector| selector_matches(selector, name))
        {
            continue;
        }
        if let Some(mappings) = metadata.get("mappings") {
            response.insert(
                name.clone(),
                serde_json::json!({
                    "mappings": mappings.clone()
                }),
            );
        }
    }
    serde_json::Value::Object(response)
}

pub fn build_field_mapping_readback_response(
    indices: &serde_json::Value,
    target: Option<&str>,
    fields: &str,
) -> serde_json::Value {
    let selectors = target.map(parse_mapping_selectors).unwrap_or_default();
    let field_selectors = parse_mapping_selectors(fields);
    let Some(index_map) = indices.as_object() else {
        return serde_json::json!({});
    };

    let mut response = serde_json::Map::new();
    for (name, metadata) in index_map {
        if !selectors.is_empty()
            && !selectors.iter().any(|selector| selector_matches(selector, name))
        {
            continue;
        }
        let properties = metadata
            .get("mappings")
            .and_then(|mappings| mappings.get("properties"))
            .and_then(serde_json::Value::as_object);
        let Some(properties) = properties else {
            continue;
        };
        let mut field_response = serde_json::Map::new();
        for (field_name, field_mapping) in properties {
            if !field_selectors.is_empty()
                && !field_selectors
                    .iter()
                    .any(|selector| field_selector_matches(selector, field_name))
            {
                continue;
            }
            field_response.insert(
                field_name.clone(),
                serde_json::json!({
                    "full_name": field_name,
                    "mapping": {
                        field_name: field_mapping.clone()
                    }
                }),
            );
        }
        if !field_response.is_empty() {
            response.insert(
                name.clone(),
                serde_json::json!({
                    "mappings": field_response
                }),
            );
        }
    }
    serde_json::Value::Object(response)
}

pub fn build_mapping_update_body_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(object) = body.as_object() else {
        return serde_json::json!({});
    };
    let mut subset = serde_json::Map::new();
    for key in ["dynamic", "_meta"] {
        if let Some(value) = object.get(key) {
            subset.insert(key.to_string(), value.clone());
        }
    }
    if let Some(properties) = object.get("properties") {
        subset.insert("properties".to_string(), properties.clone());
    }
    serde_json::Value::Object(subset)
}

pub const MAPPING_ROUTE_REGISTRY_TABLE: [MappingRouteRegistryEntry; 5] = [
    MappingRouteRegistryEntry {
        method: GET_GLOBAL_MAPPING_ROUTE_METHOD,
        path: GET_GLOBAL_MAPPING_ROUTE_PATH,
        family: MAPPING_ROUTE_FAMILY,
    },
    MappingRouteRegistryEntry {
        method: GET_GLOBAL_MAPPING_ROUTE_METHOD,
        path: GET_GLOBAL_FIELD_MAPPING_ROUTE_PATH,
        family: MAPPING_ROUTE_FAMILY,
    },
    MappingRouteRegistryEntry {
        method: GET_GLOBAL_MAPPING_ROUTE_METHOD,
        path: GET_INDEX_MAPPING_ROUTE_PATH,
        family: MAPPING_ROUTE_FAMILY,
    },
    MappingRouteRegistryEntry {
        method: GET_GLOBAL_MAPPING_ROUTE_METHOD,
        path: GET_INDEX_FIELD_MAPPING_ROUTE_PATH,
        family: MAPPING_ROUTE_FAMILY,
    },
    MappingRouteRegistryEntry {
        method: PUT_INDEX_MAPPING_ROUTE_METHOD,
        path: GET_INDEX_MAPPING_ROUTE_PATH,
        family: MAPPING_UPDATE_ROUTE_FAMILY,
    },
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mapping_registry_table_describes_global_and_index_scoped_routes() {
        assert_eq!(MAPPING_ROUTE_REGISTRY_TABLE.len(), 5);
        assert_eq!(MAPPING_ROUTE_REGISTRY_TABLE[0].path, "/_mapping");
        assert_eq!(MAPPING_ROUTE_REGISTRY_TABLE[1].path, "/_mapping/field/{fields}");
        assert_eq!(MAPPING_ROUTE_REGISTRY_TABLE[2].path, "/{index}/_mapping");
        assert_eq!(MAPPING_ROUTE_REGISTRY_TABLE[3].path, "/{index}/_mapping/field/{fields}");
        assert_eq!(MAPPING_ROUTE_REGISTRY_TABLE[4].method, "PUT");
    }

    #[test]
    fn mapping_selector_parser_keeps_wildcard_and_comma_targets() {
        assert_eq!(
            parse_mapping_selectors("logs-*,metrics-000001"),
            vec!["logs-*".to_string(), "metrics-000001".to_string()]
        );
    }

    #[test]
    fn mapping_readback_response_supports_global_wildcard_and_comma_selection() {
        let indices = serde_json::json!({
            "logs-000001": {
                "mappings": {
                    "properties": {
                        "message": { "type": "text" }
                    }
                },
                "settings": {}
            },
            "logs-000002": {
                "mappings": {
                    "properties": {
                        "message": { "type": "text" }
                    }
                }
            },
            "metrics-000001": {
                "mappings": {
                    "properties": {
                        "value": { "type": "long" }
                    }
                }
            }
        });

        let global = build_mapping_readback_response(&indices, None);
        let wildcard = build_mapping_readback_response(&indices, Some("logs-*"));
        let comma = build_mapping_readback_response(&indices, Some("logs-000001,metrics-000001"));

        assert!(global.get("logs-000001").is_some());
        assert!(global.get("metrics-000001").is_some());
        assert!(wildcard.get("logs-000001").is_some());
        assert!(wildcard.get("logs-000002").is_some());
        assert!(wildcard.get("metrics-000001").is_none());
        assert!(comma.get("logs-000001").is_some());
        assert!(comma.get("metrics-000001").is_some());
        assert!(comma.get("logs-000002").is_none());
    }

    #[test]
    fn field_mapping_readback_response_supports_global_targeted_and_wildcard_fields() {
        let indices = serde_json::json!({
            "logs-000001": {
                "mappings": {
                    "properties": {
                        "message": { "type": "text" },
                        "tenant": { "type": "keyword" }
                    }
                }
            },
            "metrics-000001": {
                "mappings": {
                    "properties": {
                        "value": { "type": "long" }
                    }
                }
            }
        });

        let global = build_field_mapping_readback_response(&indices, None, "message,tenant");
        let targeted = build_field_mapping_readback_response(&indices, Some("logs-*"), "message");
        let wildcard = build_field_mapping_readback_response(&indices, None, "ten*");

        assert_eq!(
            global["logs-000001"]["mappings"]["message"]["mapping"]["message"]["type"],
            "text"
        );
        assert_eq!(
            global["logs-000001"]["mappings"]["tenant"]["mapping"]["tenant"]["type"],
            "keyword"
        );
        assert!(global.get("metrics-000001").is_none());
        assert!(targeted["logs-000001"]["mappings"]["message"].is_object());
        assert!(targeted["logs-000001"]["mappings"]["tenant"].is_null());
        assert!(wildcard["logs-000001"]["mappings"]["tenant"].is_object());
    }

    #[test]
    fn mapping_update_body_subset_keeps_properties_only() {
        let subset = build_mapping_update_body_subset(&serde_json::json!({
            "dynamic": "strict",
            "_meta": {
                "owner": "search"
            },
            "properties": {
                "message": {
                    "type": "text"
                }
            },
            "runtime": {
                "drop": true
            }
        }));

        assert_eq!(subset.get("dynamic"), Some(&serde_json::json!("strict")));
        assert_eq!(subset.get("_meta"), Some(&serde_json::json!({ "owner": "search" })));
        assert!(subset.get("properties").is_some());
        assert!(subset.get("runtime").is_none());
    }
}
