//! Workspace-visible route-registration anchors for bounded `DELETE /{index}` parity work.

use os_rest::{RestErrorKind, RestMethod, RestResponse};

pub const DELETE_INDEX_ROUTE_METHOD: &str = "DELETE";
pub const DELETE_INDEX_ROUTE_PATH: &str = "/{index}";
pub const DELETE_INDEX_ROUTE_FAMILY: &str = "index_delete";
pub const DELETE_INDEX_RESPONSE_FIELDS: [&str; 1] = ["acknowledged"];
pub const DELETE_INDEX_MISSING_BUCKET: &str = "index_not_found_exception";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DeleteIndexRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub fn parse_delete_index_selectors(target: &str) -> Vec<String> {
    target
        .split(',')
        .map(str::trim)
        .filter(|segment| !segment.is_empty())
        .map(ToOwned::to_owned)
        .collect()
}

fn selector_matches(selector: &str, index: &str) -> bool {
    if selector == "_all" {
        return true;
    }
    if let Some(prefix) = selector.strip_suffix('*') {
        return index.starts_with(prefix);
    }
    selector == index
}

pub fn resolve_delete_index_targets(target: &str, known_indices: &[&str]) -> Vec<String> {
    let selectors = parse_delete_index_selectors(target);
    known_indices
        .iter()
        .filter(|index| selectors.iter().any(|selector| selector_matches(selector, index)))
        .map(|index| (*index).to_string())
        .collect()
}

pub fn build_delete_index_success_response() -> RestResponse {
    RestResponse::json(200, serde_json::json!({ "acknowledged": true }))
}

pub fn build_delete_index_missing_response(target: &str) -> RestResponse {
    RestResponse::opensearch_error_kind(
        RestErrorKind::IndexNotFound,
        format!("no such index [{target}]"),
    )
}

pub const DELETE_INDEX_ROUTE_REGISTRY_ENTRY: DeleteIndexRouteRegistryEntry =
    DeleteIndexRouteRegistryEntry {
        method: DELETE_INDEX_ROUTE_METHOD,
        path: DELETE_INDEX_ROUTE_PATH,
        family: DELETE_INDEX_ROUTE_FAMILY,
    };

pub const DELETE_INDEX_ROUTE_REGISTRY_TABLE: [DeleteIndexRouteRegistryEntry; 1] =
    [DELETE_INDEX_ROUTE_REGISTRY_ENTRY];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn delete_index_registry_entry_describes_delete_surface() {
        assert_eq!(DELETE_INDEX_ROUTE_REGISTRY_ENTRY.method, "DELETE");
        assert_eq!(DELETE_INDEX_ROUTE_REGISTRY_ENTRY.path, "/{index}");
        assert_eq!(DELETE_INDEX_ROUTE_REGISTRY_ENTRY.family, "index_delete");
    }

    #[test]
    fn delete_index_selector_parser_keeps_wildcard_comma_and_all_targets() {
        assert_eq!(
            parse_delete_index_selectors("_all,logs-*"),
            vec!["_all".to_string(), "logs-*".to_string()]
        );
    }

    #[test]
    fn delete_index_target_resolution_supports_wildcard_and_comma_expansion() {
        let known = ["logs-000001", "logs-000002", "metrics-000001"];
        assert_eq!(
            resolve_delete_index_targets("logs-*", &known),
            vec!["logs-000001".to_string(), "logs-000002".to_string()]
        );
        assert_eq!(
            resolve_delete_index_targets("logs-000001,metrics-000001", &known),
            vec!["logs-000001".to_string(), "metrics-000001".to_string()]
        );
        assert_eq!(
            resolve_delete_index_targets("_all", &known),
            vec![
                "logs-000001".to_string(),
                "logs-000002".to_string(),
                "metrics-000001".to_string()
            ]
        );
    }

    #[test]
    fn delete_index_success_and_missing_error_use_bounded_shapes() {
        let success = build_delete_index_success_response();
        let missing = build_delete_index_missing_response("missing-000001");

        assert_eq!(success.status, 200);
        assert_eq!(success.body["acknowledged"], serde_json::json!(true));
        assert_eq!(missing.status, 404);
        assert_eq!(
            missing.body["error"]["type"],
            serde_json::json!(DELETE_INDEX_MISSING_BUCKET)
        );
    }
}
