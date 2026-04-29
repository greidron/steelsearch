//! Workspace-visible fail-closed route-registration anchors for data streams.

pub const DATA_STREAM_ROUTE_METHOD_GET: &str = "GET";
pub const DATA_STREAM_ROUTE_METHOD_PUT: &str = "PUT";
pub const DATA_STREAM_ROUTE_METHOD_DELETE: &str = "DELETE";

pub const GET_DATA_STREAM_ROUTE_PATH: &str = "/_data_stream";
pub const GET_NAMED_DATA_STREAM_ROUTE_PATH: &str = "/_data_stream/{name}";
pub const GET_DATA_STREAM_STATS_ROUTE_PATH: &str = "/_data_stream/_stats";
pub const PUT_DATA_STREAM_ROUTE_PATH: &str = "/_data_stream/{name}";
pub const DELETE_DATA_STREAM_ROUTE_PATH: &str = "/_data_stream/{name}";

pub const DATA_STREAM_ROUTE_FAMILY: &str = "data_stream_fail_closed";
pub const DATA_STREAM_UNSUPPORTED_SURFACE: &str = "unsupported data-stream lifecycle surface";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DataStreamRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub fn build_data_stream_fail_closed_response() -> serde_json::Value {
    serde_json::json!({
        "error": {
            "type": "illegal_argument_exception",
            "reason": DATA_STREAM_UNSUPPORTED_SURFACE
        },
        "status": 400
    })
}

pub const DATA_STREAM_ROUTE_REGISTRY_TABLE: [DataStreamRouteRegistryEntry; 5] = [
    DataStreamRouteRegistryEntry {
        method: DATA_STREAM_ROUTE_METHOD_GET,
        path: GET_DATA_STREAM_ROUTE_PATH,
        family: DATA_STREAM_ROUTE_FAMILY,
    },
    DataStreamRouteRegistryEntry {
        method: DATA_STREAM_ROUTE_METHOD_GET,
        path: GET_NAMED_DATA_STREAM_ROUTE_PATH,
        family: DATA_STREAM_ROUTE_FAMILY,
    },
    DataStreamRouteRegistryEntry {
        method: DATA_STREAM_ROUTE_METHOD_GET,
        path: GET_DATA_STREAM_STATS_ROUTE_PATH,
        family: DATA_STREAM_ROUTE_FAMILY,
    },
    DataStreamRouteRegistryEntry {
        method: DATA_STREAM_ROUTE_METHOD_PUT,
        path: PUT_DATA_STREAM_ROUTE_PATH,
        family: DATA_STREAM_ROUTE_FAMILY,
    },
    DataStreamRouteRegistryEntry {
        method: DATA_STREAM_ROUTE_METHOD_DELETE,
        path: DELETE_DATA_STREAM_ROUTE_PATH,
        family: DATA_STREAM_ROUTE_FAMILY,
    },
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn data_stream_registry_table_covers_read_write_and_stats_forms() {
        assert_eq!(DATA_STREAM_ROUTE_REGISTRY_TABLE.len(), 5);
        assert_eq!(DATA_STREAM_ROUTE_REGISTRY_TABLE[0].path, "/_data_stream");
        assert_eq!(DATA_STREAM_ROUTE_REGISTRY_TABLE[2].path, "/_data_stream/_stats");
        assert_eq!(DATA_STREAM_ROUTE_REGISTRY_TABLE[4].method, "DELETE");
    }

    #[test]
    fn data_stream_fail_closed_response_keeps_canonical_surface_phrase() {
        let response = build_data_stream_fail_closed_response();
        assert_eq!(response["error"]["type"], "illegal_argument_exception");
        assert_eq!(response["error"]["reason"], DATA_STREAM_UNSUPPORTED_SURFACE);
        assert_eq!(response["status"], 400);
    }
}
