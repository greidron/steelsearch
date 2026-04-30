//! Workspace-visible route-registration anchors for legacy index templates.

pub const LEGACY_TEMPLATE_ROUTE_METHOD_GET: &str = "GET";
pub const LEGACY_TEMPLATE_ROUTE_METHOD_PUT: &str = "PUT";
pub const LEGACY_TEMPLATE_ROUTE_METHOD_DELETE: &str = "DELETE";

pub const GET_LEGACY_TEMPLATE_ROUTE_PATH: &str = "/_template";
pub const GET_NAMED_LEGACY_TEMPLATE_ROUTE_PATH: &str = "/_template/{name}";
pub const LEGACY_TEMPLATE_ROUTE_FAMILY: &str = "legacy_template";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct LegacyTemplateRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub type LegacyTemplateReadbackHook = fn(&serde_json::Value, Option<&str>) -> serde_json::Value;
pub type LegacyTemplateMutationHook = fn(&serde_json::Value) -> serde_json::Value;

pub fn parse_legacy_template_name_selectors(target: &str) -> Vec<String> {
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

pub fn build_legacy_template_body_subset(body: &serde_json::Value) -> serde_json::Value {
    let Some(object) = body.as_object() else {
        return serde_json::json!({});
    };
    let mut subset = serde_json::Map::new();
    for field in ["index_patterns", "order", "version", "settings", "mappings", "aliases"] {
        if let Some(value) = object.get(field) {
            subset.insert(field.to_string(), value.clone());
        }
    }
    serde_json::Value::Object(subset)
}

pub fn build_legacy_template_readback_response(
    templates: &serde_json::Value,
    name_target: Option<&str>,
) -> serde_json::Value {
    let selectors = name_target
        .map(parse_legacy_template_name_selectors)
        .unwrap_or_default();
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

pub fn build_legacy_template_acknowledged_response() -> serde_json::Value {
    serde_json::json!({
        "acknowledged": true
    })
}

pub fn invoke_legacy_template_live_readback(
    templates: &serde_json::Value,
    name_target: Option<&str>,
) -> serde_json::Value {
    build_legacy_template_readback_response(templates, name_target)
}

pub fn invoke_legacy_template_live_mutation(body: &serde_json::Value) -> serde_json::Value {
    let _subset = build_legacy_template_body_subset(body);
    build_legacy_template_acknowledged_response()
}

pub const LEGACY_TEMPLATE_ROUTE_REGISTRY_TABLE: [LegacyTemplateRouteRegistryEntry; 4] = [
    LegacyTemplateRouteRegistryEntry {
        method: LEGACY_TEMPLATE_ROUTE_METHOD_GET,
        path: GET_LEGACY_TEMPLATE_ROUTE_PATH,
        family: LEGACY_TEMPLATE_ROUTE_FAMILY,
    },
    LegacyTemplateRouteRegistryEntry {
        method: LEGACY_TEMPLATE_ROUTE_METHOD_GET,
        path: GET_NAMED_LEGACY_TEMPLATE_ROUTE_PATH,
        family: LEGACY_TEMPLATE_ROUTE_FAMILY,
    },
    LegacyTemplateRouteRegistryEntry {
        method: LEGACY_TEMPLATE_ROUTE_METHOD_PUT,
        path: GET_NAMED_LEGACY_TEMPLATE_ROUTE_PATH,
        family: LEGACY_TEMPLATE_ROUTE_FAMILY,
    },
    LegacyTemplateRouteRegistryEntry {
        method: LEGACY_TEMPLATE_ROUTE_METHOD_DELETE,
        path: GET_NAMED_LEGACY_TEMPLATE_ROUTE_PATH,
        family: LEGACY_TEMPLATE_ROUTE_FAMILY,
    },
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn legacy_template_registry_table_describes_readback_and_mutation_routes() {
        assert_eq!(LEGACY_TEMPLATE_ROUTE_REGISTRY_TABLE.len(), 4);
        assert_eq!(LEGACY_TEMPLATE_ROUTE_REGISTRY_TABLE[0].path, "/_template");
        assert_eq!(LEGACY_TEMPLATE_ROUTE_REGISTRY_TABLE[1].path, "/_template/{name}");
        assert_eq!(LEGACY_TEMPLATE_ROUTE_REGISTRY_TABLE[3].method, "DELETE");
    }

    #[test]
    fn legacy_template_name_selector_parser_keeps_wildcard_and_comma_targets() {
        assert_eq!(
            parse_legacy_template_name_selectors("logs-*,metrics-template"),
            vec!["logs-*".to_string(), "metrics-template".to_string()]
        );
    }

    #[test]
    fn legacy_template_body_subset_keeps_bounded_fields_only() {
        let subset = build_legacy_template_body_subset(&serde_json::json!({
            "index_patterns": ["logs-*"],
            "order": 5,
            "version": 2,
            "settings": {
                "index": {
                    "number_of_replicas": 0
                }
            },
            "mappings": {
                "properties": {
                    "message": { "type": "text" }
                }
            },
            "aliases": {
                "logs-read": {}
            },
            "composed_of": ["ignore-me"]
        }));

        assert!(subset.get("index_patterns").is_some());
        assert!(subset.get("order").is_some());
        assert!(subset.get("version").is_some());
        assert!(subset.get("settings").is_some());
        assert!(subset.get("mappings").is_some());
        assert!(subset.get("aliases").is_some());
        assert!(subset.get("composed_of").is_none());
    }

    #[test]
    fn legacy_template_readback_response_supports_wildcard_and_comma_selection() {
        let templates = serde_json::json!({
            "logs-template": {
                "index_patterns": ["logs-*"]
            },
            "logs-archive": {
                "index_patterns": ["logs-archive-*"]
            },
            "metrics-template": {
                "index_patterns": ["metrics-*"]
            }
        });

        let wildcard = build_legacy_template_readback_response(&templates, Some("logs-*"));
        let comma = build_legacy_template_readback_response(
            &templates,
            Some("logs-template,metrics-template"),
        );

        assert!(wildcard.get("logs-template").is_some());
        assert!(wildcard.get("logs-archive").is_some());
        assert!(wildcard.get("metrics-template").is_none());
        assert!(comma.get("logs-template").is_some());
        assert!(comma.get("metrics-template").is_some());
        assert!(comma.get("logs-archive").is_none());
    }

    #[test]
    fn legacy_template_live_hooks_reuse_bounded_readback_and_acknowledged_shapes() {
        let readback = invoke_legacy_template_live_readback(
            &serde_json::json!({
                "logs-template": {
                    "index_patterns": ["logs-*"]
                }
            }),
            Some("logs-*"),
        );
        let ack = invoke_legacy_template_live_mutation(&serde_json::json!({
            "index_patterns": ["logs-*"],
            "settings": {
                "index": {
                    "number_of_replicas": 0
                }
            }
        }));

        assert!(readback.get("logs-template").is_some());
        assert_eq!(ack["acknowledged"], true);
    }
}
