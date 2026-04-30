//! Workspace-visible route-registration anchors for component/composable templates.

pub const TEMPLATE_ROUTE_METHOD_GET: &str = "GET";
pub const TEMPLATE_ROUTE_METHOD_PUT: &str = "PUT";
pub const TEMPLATE_ROUTE_METHOD_DELETE: &str = "DELETE";

pub const GET_COMPONENT_TEMPLATE_ROUTE_PATH: &str = "/_component_template";
pub const GET_NAMED_COMPONENT_TEMPLATE_ROUTE_PATH: &str = "/_component_template/{name}";
pub const GET_INDEX_TEMPLATE_ROUTE_PATH: &str = "/_index_template";
pub const GET_NAMED_INDEX_TEMPLATE_ROUTE_PATH: &str = "/_index_template/{name}";

pub const COMPONENT_TEMPLATE_ROUTE_FAMILY: &str = "component_template";
pub const INDEX_TEMPLATE_ROUTE_FAMILY: &str = "index_template";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TemplateRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub type TemplateReadbackHook = fn(&serde_json::Value, Option<&str>) -> serde_json::Value;
pub type TemplateMutationHook = fn(&serde_json::Value) -> serde_json::Value;

pub fn parse_template_name_selectors(target: &str) -> Vec<String> {
    target
        .split(',')
        .map(str::trim)
        .filter(|segment| !segment.is_empty())
        .map(ToOwned::to_owned)
        .collect()
}

fn selector_matches(selector: &str, candidate: &str) -> bool {
    if !selector.contains('*') {
        return selector == candidate;
    }
    let mut rest = candidate;
    for (i, part) in selector.split('*').enumerate() {
        if part.is_empty() {
            continue;
        }
        if i == 0 && !selector.starts_with('*') {
            if !rest.starts_with(part) {
                return false;
            }
            rest = &rest[part.len()..];
            continue;
        }
        if let Some(pos) = rest.find(part) {
            rest = &rest[pos + part.len()..];
        } else {
            return false;
        }
    }
    if !selector.ends_with('*') {
        if let Some(last) = selector.rsplit('*').next() {
            return candidate.ends_with(last);
        }
    }
    true
}

pub fn build_component_template_body_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(object) = body.as_object() else {
        return serde_json::json!({});
    };
    let mut subset = serde_json::Map::new();
    for field in ["template", "version", "_meta"] {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_index_template_body_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(object) = body.as_object() else {
        return serde_json::json!({});
    };
    let mut subset = serde_json::Map::new();
    for field in [
        "index_patterns",
        "template",
        "composed_of",
        "priority",
        "version",
        "_meta",
        "data_stream",
    ] {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_named_template_readback_response(
    templates: &serde_json::Value,
    name_target: Option<&str>,
) -> serde_json::Value {
    let selectors = name_target.map(parse_template_name_selectors).unwrap_or_default();
    let Some(template_map) = templates.as_object() else {
        return serde_json::json!({});
    };

    let mut response = serde_json::Map::new();
    for (name, template) in template_map {
        if !selectors.is_empty()
            && !selectors
                .iter()
                .any(|selector| selector_matches(selector, name))
        {
            continue;
        }
        response.insert(name.clone(), template.clone());
    }
    serde_json::Value::Object(response)
}

pub fn build_template_acknowledged_response() -> serde_json::Value {
    serde_json::json!({
        "acknowledged": true
    })
}

pub fn invoke_component_template_live_readback(
    templates: &serde_json::Value,
    name_target: Option<&str>,
) -> serde_json::Value {
    build_named_template_readback_response(templates, name_target)
}

pub fn invoke_index_template_live_readback(
    templates: &serde_json::Value,
    name_target: Option<&str>,
) -> serde_json::Value {
    build_named_template_readback_response(templates, name_target)
}

pub fn invoke_component_template_live_mutation(body: &serde_json::Value) -> serde_json::Value {
    let _subset = build_component_template_body_subset(body);
    build_template_acknowledged_response()
}

pub fn invoke_index_template_live_mutation(body: &serde_json::Value) -> serde_json::Value {
    let _subset = build_index_template_body_subset(body);
    build_template_acknowledged_response()
}

pub const TEMPLATE_ROUTE_REGISTRY_TABLE: [TemplateRouteRegistryEntry; 8] = [
    TemplateRouteRegistryEntry {
        method: TEMPLATE_ROUTE_METHOD_GET,
        path: GET_COMPONENT_TEMPLATE_ROUTE_PATH,
        family: COMPONENT_TEMPLATE_ROUTE_FAMILY,
    },
    TemplateRouteRegistryEntry {
        method: TEMPLATE_ROUTE_METHOD_GET,
        path: GET_NAMED_COMPONENT_TEMPLATE_ROUTE_PATH,
        family: COMPONENT_TEMPLATE_ROUTE_FAMILY,
    },
    TemplateRouteRegistryEntry {
        method: TEMPLATE_ROUTE_METHOD_PUT,
        path: GET_NAMED_COMPONENT_TEMPLATE_ROUTE_PATH,
        family: COMPONENT_TEMPLATE_ROUTE_FAMILY,
    },
    TemplateRouteRegistryEntry {
        method: TEMPLATE_ROUTE_METHOD_DELETE,
        path: GET_NAMED_COMPONENT_TEMPLATE_ROUTE_PATH,
        family: COMPONENT_TEMPLATE_ROUTE_FAMILY,
    },
    TemplateRouteRegistryEntry {
        method: TEMPLATE_ROUTE_METHOD_GET,
        path: GET_INDEX_TEMPLATE_ROUTE_PATH,
        family: INDEX_TEMPLATE_ROUTE_FAMILY,
    },
    TemplateRouteRegistryEntry {
        method: TEMPLATE_ROUTE_METHOD_GET,
        path: GET_NAMED_INDEX_TEMPLATE_ROUTE_PATH,
        family: INDEX_TEMPLATE_ROUTE_FAMILY,
    },
    TemplateRouteRegistryEntry {
        method: TEMPLATE_ROUTE_METHOD_PUT,
        path: GET_NAMED_INDEX_TEMPLATE_ROUTE_PATH,
        family: INDEX_TEMPLATE_ROUTE_FAMILY,
    },
    TemplateRouteRegistryEntry {
        method: TEMPLATE_ROUTE_METHOD_DELETE,
        path: GET_NAMED_INDEX_TEMPLATE_ROUTE_PATH,
        family: INDEX_TEMPLATE_ROUTE_FAMILY,
    },
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn template_registry_table_covers_component_and_index_template_crud_readback() {
        assert_eq!(TEMPLATE_ROUTE_REGISTRY_TABLE.len(), 8);
        assert_eq!(TEMPLATE_ROUTE_REGISTRY_TABLE[0].path, "/_component_template");
        assert_eq!(TEMPLATE_ROUTE_REGISTRY_TABLE[4].path, "/_index_template");
        assert_eq!(TEMPLATE_ROUTE_REGISTRY_TABLE[7].method, "DELETE");
    }

    #[test]
    fn template_name_selector_parser_keeps_wildcard_and_comma_targets() {
        assert_eq!(
            parse_template_name_selectors("logs-*,metrics-template"),
            vec!["logs-*".to_string(), "metrics-template".to_string()]
        );
    }

    #[test]
    fn component_template_body_subset_keeps_bounded_fields_only() {
        let subset = build_component_template_body_subset(&serde_json::json!({
            "template": {
                "mappings": {
                    "properties": {
                        "message": { "type": "text" }
                    }
                }
            },
            "version": 3,
            "_meta": {
                "owner": "tests"
            }
        }));

        assert!(subset.get("template").is_some());
        assert!(subset.get("version").is_some());
        assert!(subset.get("_meta").is_some());
        assert!(subset.get("deprecated").is_none());
    }

    #[test]
    fn index_template_body_subset_keeps_bounded_fields_only() {
        let subset = build_index_template_body_subset(&serde_json::json!({
            "index_patterns": ["logs-*"],
            "template": {
                "settings": {
                    "index": {
                        "number_of_shards": 1
                    }
                }
            },
            "composed_of": ["logs-component"],
            "priority": 10,
            "version": 2,
            "_meta": {
                "owner": "tests"
            },
            "data_stream": {}
        }));

        assert!(subset.get("index_patterns").is_some());
        assert!(subset.get("template").is_some());
        assert!(subset.get("composed_of").is_some());
        assert!(subset.get("priority").is_some());
        assert!(subset.get("version").is_some());
        assert!(subset.get("_meta").is_some());
        assert!(subset.get("data_stream").is_some());
        assert!(subset.get("allow_auto_create").is_none());
        assert!(subset.get("ignore_missing_component_templates").is_none());
    }

    #[test]
    fn named_template_readback_response_supports_wildcard_and_comma_selection() {
        let templates = serde_json::json!({
            "logs-component": {
                "component_template": {
                    "template": {
                        "mappings": {
                            "properties": {
                                "message": { "type": "text" }
                            }
                        }
                    }
                }
            },
            "logs-template": {
                "index_template": {
                    "index_patterns": ["logs-*"]
                }
            },
            "metrics-template": {
                "index_template": {
                    "index_patterns": ["metrics-*"]
                }
            }
        });

        let wildcard = build_named_template_readback_response(&templates, Some("logs-*"));
        let comma =
            build_named_template_readback_response(&templates, Some("logs-component,metrics-template"));

        assert!(wildcard.get("logs-component").is_some());
        assert!(wildcard.get("logs-template").is_some());
        assert!(wildcard.get("metrics-template").is_none());
        assert!(comma.get("logs-component").is_some());
        assert!(comma.get("metrics-template").is_some());
        assert!(comma.get("logs-template").is_none());
    }

    #[test]
    fn template_live_hooks_reuse_bounded_readback_and_acknowledged_mutation_shapes() {
        let readback = invoke_component_template_live_readback(
            &serde_json::json!({
                "logs-component": {
                    "component_template": {
                        "template": {
                            "settings": {}
                        }
                    }
                }
            }),
            Some("logs-*"),
        );
        let component_ack = invoke_component_template_live_mutation(&serde_json::json!({
            "template": {
                "settings": {}
            }
        }));
        let index_ack = invoke_index_template_live_mutation(&serde_json::json!({
            "index_patterns": ["logs-*"],
            "template": {
                "settings": {}
            }
        }));

        assert!(readback.get("logs-component").is_some());
        assert_eq!(component_ack["acknowledged"], true);
        assert_eq!(index_ack["acknowledged"], true);
    }
}
