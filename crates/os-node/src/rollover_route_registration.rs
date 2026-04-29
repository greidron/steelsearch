//! Workspace-visible fail-closed route-registration anchors for rollover APIs.

pub const ROLLOVER_ROUTE_METHOD_POST: &str = "POST";
pub const ROLLOVER_ROUTE_PATH: &str = "/{index}/_rollover";
pub const NAMED_ROLLOVER_ROUTE_PATH: &str = "/{index}/_rollover/{new_index}";
pub const ROLLOVER_ROUTE_FAMILY: &str = "rollover_fail_closed";
pub const ROLLOVER_UNSUPPORTED_SURFACE: &str = "unsupported rollover lifecycle surface";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RolloverRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub fn build_rollover_fail_closed_response() -> serde_json::Value {
    serde_json::json!({
        "error": {
            "type": "illegal_argument_exception",
            "reason": ROLLOVER_UNSUPPORTED_SURFACE
        },
        "status": 400
    })
}

pub const ROLLOVER_ROUTE_REGISTRY_TABLE: [RolloverRouteRegistryEntry; 2] = [
    RolloverRouteRegistryEntry {
        method: ROLLOVER_ROUTE_METHOD_POST,
        path: ROLLOVER_ROUTE_PATH,
        family: ROLLOVER_ROUTE_FAMILY,
    },
    RolloverRouteRegistryEntry {
        method: ROLLOVER_ROUTE_METHOD_POST,
        path: NAMED_ROLLOVER_ROUTE_PATH,
        family: ROLLOVER_ROUTE_FAMILY,
    },
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rollover_registry_table_covers_named_and_unnamed_forms() {
        assert_eq!(ROLLOVER_ROUTE_REGISTRY_TABLE.len(), 2);
        assert_eq!(ROLLOVER_ROUTE_REGISTRY_TABLE[0].path, "/{index}/_rollover");
        assert_eq!(
            ROLLOVER_ROUTE_REGISTRY_TABLE[1].path,
            "/{index}/_rollover/{new_index}"
        );
    }

    #[test]
    fn rollover_fail_closed_response_keeps_canonical_surface_phrase() {
        let response = build_rollover_fail_closed_response();
        assert_eq!(response["error"]["type"], "illegal_argument_exception");
        assert_eq!(response["error"]["reason"], ROLLOVER_UNSUPPORTED_SURFACE);
        assert_eq!(response["status"], 400);
    }
}
