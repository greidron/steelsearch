//! Workspace-visible route-registration anchors for bounded settings readback work.

pub const GET_GLOBAL_SETTINGS_ROUTE_METHOD: &str = "GET";
pub const GET_GLOBAL_SETTINGS_ROUTE_PATH: &str = "/_settings";
pub const GET_GLOBAL_NAMED_SETTINGS_ROUTE_PATH: &str = "/_settings/{name}";
pub const GET_INDEX_SETTINGS_ROUTE_PATH: &str = "/{index}/_settings";
pub const GET_INDEX_NAMED_SETTINGS_ROUTE_PATH: &str = "/{index}/_settings/{name}";
pub const PUT_INDEX_SETTINGS_ROUTE_METHOD: &str = "PUT";
pub const SETTINGS_ROUTE_FAMILY: &str = "settings_readback";
pub const SETTINGS_UPDATE_ROUTE_FAMILY: &str = "settings_update";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SettingsRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub fn parse_settings_selectors(target: &str) -> Vec<String> {
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

pub fn build_settings_readback_response(
    indices: &serde_json::Value,
    target: Option<&str>,
) -> serde_json::Value {
    build_named_settings_readback_response(indices, target, None)
}

fn selector_matches_name(selector: &str, name: &str) -> bool {
    if let Some(prefix) = selector.strip_suffix('*') {
        name.starts_with(prefix)
    } else {
        selector == name
    }
}

fn flatten_settings_into(prefix: Option<&str>, value: &serde_json::Value, output: &mut serde_json::Map<String, serde_json::Value>) {
    let Some(object) = value.as_object() else {
        if let Some(prefix) = prefix {
            output.insert(prefix.to_string(), value.clone());
        }
        return;
    };

    for (key, child) in object {
        let next_prefix = match prefix {
            Some(prefix) => format!("{prefix}.{key}"),
            None => key.clone(),
        };
        flatten_settings_into(Some(&next_prefix), child, output);
    }
}

pub fn build_named_settings_readback_response(
    indices: &serde_json::Value,
    target: Option<&str>,
    name_filter: Option<&str>,
) -> serde_json::Value {
    let selectors = target.map(parse_settings_selectors).unwrap_or_default();
    let name_selectors = name_filter.map(parse_settings_selectors).unwrap_or_default();
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
        if let Some(settings) = metadata.get("settings") {
            let filtered_settings = if name_selectors.is_empty() {
                settings.clone()
            } else {
                let mut flattened = serde_json::Map::new();
                flatten_settings_into(None, settings, &mut flattened);
                let filtered = flattened
                    .into_iter()
                    .filter(|(setting_name, _)| {
                        name_selectors
                            .iter()
                            .any(|selector| selector_matches_name(selector, setting_name))
                    })
                    .collect::<serde_json::Map<_, _>>();
                serde_json::Value::Object(filtered)
            };
            response.insert(
                name.clone(),
                serde_json::json!({
                    "settings": filtered_settings
                }),
            );
        }
    }
    serde_json::Value::Object(response)
}

pub fn build_settings_update_body_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(object) = body.as_object() else {
        return serde_json::json!({});
    };
    let Some(index_settings) = object.get("index").and_then(|value| value.as_object()) else {
        return serde_json::json!({});
    };

    let mut bounded_index = serde_json::Map::new();
    for key in [
        "number_of_replicas",
        "refresh_interval",
        "max_result_window",
        "number_of_routing_shards",
    ] {
        if let Some(value) = index_settings.get(key) {
            bounded_index.insert(key.to_string(), value.clone());
        }
    }
    if bounded_index.is_empty() {
        serde_json::json!({})
    } else {
        serde_json::json!({
            "index": bounded_index
        })
    }
}

pub const SETTINGS_ROUTE_REGISTRY_TABLE: [SettingsRouteRegistryEntry; 5] = [
    SettingsRouteRegistryEntry {
        method: GET_GLOBAL_SETTINGS_ROUTE_METHOD,
        path: GET_GLOBAL_SETTINGS_ROUTE_PATH,
        family: SETTINGS_ROUTE_FAMILY,
    },
    SettingsRouteRegistryEntry {
        method: GET_GLOBAL_SETTINGS_ROUTE_METHOD,
        path: GET_GLOBAL_NAMED_SETTINGS_ROUTE_PATH,
        family: SETTINGS_ROUTE_FAMILY,
    },
    SettingsRouteRegistryEntry {
        method: GET_GLOBAL_SETTINGS_ROUTE_METHOD,
        path: GET_INDEX_SETTINGS_ROUTE_PATH,
        family: SETTINGS_ROUTE_FAMILY,
    },
    SettingsRouteRegistryEntry {
        method: GET_GLOBAL_SETTINGS_ROUTE_METHOD,
        path: GET_INDEX_NAMED_SETTINGS_ROUTE_PATH,
        family: SETTINGS_ROUTE_FAMILY,
    },
    SettingsRouteRegistryEntry {
        method: PUT_INDEX_SETTINGS_ROUTE_METHOD,
        path: GET_INDEX_SETTINGS_ROUTE_PATH,
        family: SETTINGS_UPDATE_ROUTE_FAMILY,
    },
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn settings_registry_table_describes_global_and_index_scoped_routes() {
        assert_eq!(SETTINGS_ROUTE_REGISTRY_TABLE.len(), 5);
        assert_eq!(SETTINGS_ROUTE_REGISTRY_TABLE[0].path, "/_settings");
        assert_eq!(SETTINGS_ROUTE_REGISTRY_TABLE[1].path, "/_settings/{name}");
        assert_eq!(SETTINGS_ROUTE_REGISTRY_TABLE[2].path, "/{index}/_settings");
        assert_eq!(SETTINGS_ROUTE_REGISTRY_TABLE[3].path, "/{index}/_settings/{name}");
        assert_eq!(SETTINGS_ROUTE_REGISTRY_TABLE[4].method, "PUT");
    }

    #[test]
    fn settings_selector_parser_keeps_wildcard_and_comma_targets() {
        assert_eq!(
            parse_settings_selectors("logs-*,metrics-000001"),
            vec!["logs-*".to_string(), "metrics-000001".to_string()]
        );
    }

    #[test]
    fn settings_readback_response_supports_global_wildcard_and_comma_selection() {
        let indices = serde_json::json!({
            "logs-000001": {
                "settings": {
                    "index": {
                        "number_of_shards": 1
                    }
                },
                "mappings": {}
            },
            "logs-000002": {
                "settings": {
                    "index": {
                        "number_of_shards": 1
                    }
                }
            },
            "metrics-000001": {
                "settings": {
                    "index": {
                        "number_of_shards": 2
                    }
                }
            }
        });

        let global = build_settings_readback_response(&indices, None);
        let wildcard = build_settings_readback_response(&indices, Some("logs-*"));
        let comma = build_settings_readback_response(&indices, Some("logs-000001,metrics-000001"));

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
    fn settings_update_body_subset_keeps_mutable_index_fields_only() {
        let subset = build_settings_update_body_subset(&serde_json::json!({
            "index": {
                "number_of_replicas": 0,
                "refresh_interval": "1s",
                "max_result_window": 2000,
                "number_of_shards": 1
            },
            "analysis": {
                "analyzer": {}
            }
        }));

        assert_eq!(
            subset,
            serde_json::json!({
                "index": {
                    "number_of_replicas": 0,
                    "refresh_interval": "1s",
                    "max_result_window": 2000
                }
            })
        );
    }

    #[test]
    fn named_settings_readback_response_filters_flattened_setting_names() {
        let indices = serde_json::json!({
            "logs-000001": {
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0
                    }
                }
            },
            "metrics-000001": {
                "settings": {
                    "index": {
                        "number_of_shards": 2
                    }
                }
            }
        });

        let global = build_named_settings_readback_response(
            &indices,
            None,
            Some("index.number_of_shards"),
        );
        let targeted = build_named_settings_readback_response(
            &indices,
            Some("logs-*"),
            Some("index.number_of_replicas"),
        );

        assert_eq!(
            global["logs-000001"]["settings"]["index.number_of_shards"],
            serde_json::json!(1)
        );
        assert_eq!(
            global["metrics-000001"]["settings"]["index.number_of_shards"],
            serde_json::json!(2)
        );
        assert!(global["logs-000001"]["settings"]["index.number_of_replicas"].is_null());
        assert_eq!(
            targeted["logs-000001"]["settings"]["index.number_of_replicas"],
            serde_json::json!(0)
        );
        assert!(targeted.get("metrics-000001").is_none());
    }
}
