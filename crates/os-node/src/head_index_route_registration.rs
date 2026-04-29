//! Workspace-visible route-registration anchors for bounded `HEAD /{index}` parity work.

use os_rest::{RestErrorKind, RestMethod, RestRequest, RestResponse};

pub const HEAD_INDEX_ROUTE_PATH: &str = "/{index}";
pub const HEAD_INDEX_ROUTE_FAMILY: &str = "index_existence_probe";
pub const HEAD_INDEX_UNSUPPORTED_SELECTOR_BUCKET: &str = "unsupported broad selector";

pub type HeadIndexRouteInvokeFn = fn(&RestRequest, &[&str]) -> Result<RestResponse, RestResponse>;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct HeadIndexRouteRegistryEntry {
    pub method: RestMethod,
    pub path: &'static str,
    pub family: &'static str,
    pub hook: HeadIndexRouteInvokeFn,
}

pub fn validate_head_index_target(index: &str) -> Result<&str, RestResponse> {
    if index == "_all" || index.contains('*') || index.contains(',') {
        return Err(RestResponse::opensearch_error_kind(
            RestErrorKind::IllegalArgument,
            HEAD_INDEX_UNSUPPORTED_SELECTOR_BUCKET,
        ));
    }
    Ok(index)
}

pub fn build_head_index_rest_response(exists: bool) -> RestResponse {
    if exists {
        RestResponse::empty(200)
    } else {
        RestResponse::empty(404)
    }
}

pub fn invoke_head_index_live_route(
    request: &RestRequest,
    known_indices: &[&str],
) -> Result<RestResponse, RestResponse> {
    let index = request
        .path
        .trim_start_matches('/')
        .split('/')
        .next()
        .unwrap_or_default();
    let index = validate_head_index_target(index)?;
    Ok(build_head_index_rest_response(
        known_indices.iter().any(|candidate| candidate == &index),
    ))
}

pub const HEAD_INDEX_ROUTE_REGISTRY_ENTRY: HeadIndexRouteRegistryEntry =
    HeadIndexRouteRegistryEntry {
        method: RestMethod::Head,
        path: HEAD_INDEX_ROUTE_PATH,
        family: HEAD_INDEX_ROUTE_FAMILY,
        hook: invoke_head_index_live_route,
    };

pub const HEAD_INDEX_ROUTE_REGISTRY_TABLE: [HeadIndexRouteRegistryEntry; 1] =
    [HEAD_INDEX_ROUTE_REGISTRY_ENTRY];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn head_index_registry_entry_describes_exact_target_probe_surface() {
        assert_eq!(HEAD_INDEX_ROUTE_REGISTRY_ENTRY.method, RestMethod::Head);
        assert_eq!(HEAD_INDEX_ROUTE_REGISTRY_ENTRY.path, "/{index}");
        assert_eq!(HEAD_INDEX_ROUTE_REGISTRY_ENTRY.family, "index_existence_probe");
    }

    #[test]
    fn head_index_target_validation_rejects_broad_selectors() {
        for raw in ["_all", "logs-*", "index-a,index-b"] {
            let error = validate_head_index_target(raw).expect_err("broad selector rejected");
            assert_eq!(error.status, 400);
            assert_eq!(
                error.body["error"]["type"],
                serde_json::json!("illegal_argument_exception")
            );
        }
    }

    #[test]
    fn head_index_response_is_bodyless_for_present_and_missing_targets() {
        assert!(build_head_index_rest_response(true).body.is_null());
        assert!(build_head_index_rest_response(false).body.is_null());
        assert_eq!(build_head_index_rest_response(true).status, 200);
        assert_eq!(build_head_index_rest_response(false).status, 404);
    }

    #[test]
    fn head_index_live_hook_reuses_exact_target_contract() {
        let request = RestRequest::new(RestMethod::Head, "/logs-000001");
        let found = invoke_head_index_live_route(&request, &["logs-000001"]).expect("found");
        let missing = invoke_head_index_live_route(&request, &[]).expect("missing");

        assert_eq!(found.status, 200);
        assert!(found.body.is_null());
        assert_eq!(missing.status, 404);
        assert!(missing.body.is_null());
    }
}
