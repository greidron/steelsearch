//! Workspace-visible route-registration anchors for bounded `GET /{index}` parity work.

pub const GET_INDEX_ROUTE_METHOD: &str = "GET";
pub const GET_INDEX_ROUTE_PATH: &str = "/{index}";
pub const GET_INDEX_ROUTE_FAMILY: &str = "index_metadata_readback";

pub const GET_INDEX_METADATA_FIELDS: [&str; 3] = ["settings", "mappings", "aliases"];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GetIndexRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub fn parse_get_index_selectors(target: &str) -> Vec<String> {
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

pub fn build_get_index_metadata_response(
    indices: &serde_json::Value,
    target: &str,
) -> serde_json::Value {
    let selectors = parse_get_index_selectors(target);
    let Some(index_map) = indices.as_object() else {
        return serde_json::json!({});
    };

    let matched_names = index_map
        .keys()
        .filter(|name| selectors.iter().any(|selector| selector_matches(selector, name)))
        .cloned()
        .collect::<Vec<_>>();
    build_get_index_metadata_response_for_names(indices, &matched_names)
}

pub fn build_get_index_metadata_response_for_names(
    indices: &serde_json::Value,
    names: &[String],
) -> serde_json::Value {
    let Some(index_map) = indices.as_object() else {
        return serde_json::json!({});
    };

    let mut response = serde_json::Map::new();
    for (name, metadata) in index_map {
        if !names.iter().any(|candidate| candidate == name) {
            continue;
        }
        let mut filtered = serde_json::Map::new();
        if let Some(metadata_object) = metadata.as_object() {
            for field in GET_INDEX_METADATA_FIELDS {
                if let Some(value) = metadata_object.get(field) {
                    filtered.insert(field.to_string(), value.clone());
                }
            }
        }
        response.insert(name.clone(), serde_json::Value::Object(filtered));
    }
    serde_json::Value::Object(response)
}

pub const GET_INDEX_ROUTE_REGISTRY_ENTRY: GetIndexRouteRegistryEntry = GetIndexRouteRegistryEntry {
    method: GET_INDEX_ROUTE_METHOD,
    path: GET_INDEX_ROUTE_PATH,
    family: GET_INDEX_ROUTE_FAMILY,
};

pub const GET_INDEX_ROUTE_REGISTRY_TABLE: [GetIndexRouteRegistryEntry; 1] =
    [GET_INDEX_ROUTE_REGISTRY_ENTRY];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn get_index_registry_entry_describes_metadata_readback_surface() {
        assert_eq!(GET_INDEX_ROUTE_REGISTRY_ENTRY.method, "GET");
        assert_eq!(GET_INDEX_ROUTE_REGISTRY_ENTRY.path, "/{index}");
        assert_eq!(GET_INDEX_ROUTE_REGISTRY_ENTRY.family, "index_metadata_readback");
    }

    #[test]
    fn get_index_selector_parser_keeps_wildcard_and_comma_targets() {
        assert_eq!(
            parse_get_index_selectors("logs-*,metrics-000001"),
            vec!["logs-*".to_string(), "metrics-000001".to_string()]
        );
    }

    #[test]
    fn get_index_metadata_response_supports_wildcard_and_comma_selection() {
        let indices = serde_json::json!({
            "logs-000001": {
                "settings": {},
                "mappings": { "properties": { "message": { "type": "text" } } },
                "aliases": {}
            },
            "logs-000002": {
                "settings": {},
                "mappings": { "properties": { "message": { "type": "text" } } },
                "aliases": {}
            },
            "metrics-000001": {
                "settings": {},
                "mappings": { "properties": { "value": { "type": "long" } } },
                "aliases": {}
            }
        });

        let wildcard = build_get_index_metadata_response(&indices, "logs-*");
        let comma = build_get_index_metadata_response(&indices, "logs-000001,metrics-000001");

        assert!(wildcard.get("logs-000001").is_some());
        assert!(wildcard.get("logs-000002").is_some());
        assert!(wildcard.get("metrics-000001").is_none());
        assert!(comma.get("logs-000001").is_some());
        assert!(comma.get("metrics-000001").is_some());
        assert!(comma.get("logs-000002").is_none());
    }

    #[test]
    fn get_index_metadata_response_can_render_pre_resolved_target_set() {
        let indices = serde_json::json!({
            "logs-000001": { "settings": {}, "mappings": {}, "aliases": {} },
            "logs-000002": { "settings": {}, "mappings": {}, "aliases": {} }
        });

        let response = build_get_index_metadata_response_for_names(
            &indices,
            &["logs-000002".to_string()],
        );

        assert!(response.get("logs-000002").is_some());
        assert!(response.get("logs-000001").is_none());
    }
}
