//! Workspace-visible route-registration anchors for bounded mapping readback work.

pub const GET_GLOBAL_MAPPING_ROUTE_METHOD: &str = "GET";
pub const GET_GLOBAL_MAPPING_ROUTE_PATH: &str = "/_mapping";
pub const GET_INDEX_MAPPING_ROUTE_PATH: &str = "/{index}/_mapping";
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

pub fn build_mapping_update_body_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(object) = body.as_object() else {
        return serde_json::json!({});
    };
    let mut subset = serde_json::Map::new();
    if let Some(properties) = object.get("properties") {
        subset.insert("properties".to_string(), properties.clone());
    }
    serde_json::Value::Object(subset)
}

pub const MAPPING_ROUTE_REGISTRY_TABLE: [MappingRouteRegistryEntry; 3] = [
    MappingRouteRegistryEntry {
        method: GET_GLOBAL_MAPPING_ROUTE_METHOD,
        path: GET_GLOBAL_MAPPING_ROUTE_PATH,
        family: MAPPING_ROUTE_FAMILY,
    },
    MappingRouteRegistryEntry {
        method: GET_GLOBAL_MAPPING_ROUTE_METHOD,
        path: GET_INDEX_MAPPING_ROUTE_PATH,
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
        assert_eq!(MAPPING_ROUTE_REGISTRY_TABLE.len(), 3);
        assert_eq!(MAPPING_ROUTE_REGISTRY_TABLE[0].path, "/_mapping");
        assert_eq!(MAPPING_ROUTE_REGISTRY_TABLE[1].path, "/{index}/_mapping");
        assert_eq!(MAPPING_ROUTE_REGISTRY_TABLE[2].method, "PUT");
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
    fn mapping_update_body_subset_keeps_properties_only() {
        let subset = build_mapping_update_body_subset(&serde_json::json!({
            "properties": {
                "message": {
                    "type": "text"
                }
            },
            "_meta": {
                "note": "drop-me"
            }
        }));

        assert!(subset.get("properties").is_some());
        assert!(subset.get("_meta").is_none());
    }
}
