//! Workspace-visible route-registration anchors for bounded stats parity work.

pub const NODES_STATS_ROUTE_PATH: &str = "/_nodes/stats";
pub const CLUSTER_STATS_ROUTE_PATH: &str = "/_cluster/stats";
pub const INDEX_STATS_ROUTE_PATH: &str = "/_stats";
pub const STATS_ROUTE_FAMILY: &str = "stats_summary_readback";

pub const NODES_STATS_RESPONSE_FIELDS: [&str; 1] = ["nodes"];
pub const CLUSTER_STATS_RESPONSE_FIELDS: [&str; 5] =
    ["cluster_name", "status", "indices", "nodes", "fs"];
pub const INDEX_STATS_RESPONSE_FIELDS: [&str; 3] = ["_shards", "_all", "indices"];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct StatsRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
    pub hook: StatsRouteInvokeFn,
}

fn normalize_top_level_fields(
    body: &serde_json::Value,
    fields: &[&str],
) -> serde_json::Value {
    let mut normalized = serde_json::Map::new();
    for field in fields {
        if let Some(value) = body.get(*field) {
            normalized.insert((*field).to_string(), value.clone());
        }
    }
    serde_json::Value::Object(normalized)
}

pub fn build_nodes_stats_response(body: &serde_json::Value) -> serde_json::Value {
    normalize_top_level_fields(body, &NODES_STATS_RESPONSE_FIELDS)
}

pub fn build_cluster_stats_response(body: &serde_json::Value) -> serde_json::Value {
    normalize_top_level_fields(body, &CLUSTER_STATS_RESPONSE_FIELDS)
}

pub fn build_index_stats_response(body: &serde_json::Value) -> serde_json::Value {
    normalize_top_level_fields(body, &INDEX_STATS_RESPONSE_FIELDS)
}

pub type StatsRouteInvokeFn = fn(&serde_json::Value) -> serde_json::Value;

pub fn invoke_nodes_stats_live_route(body: &serde_json::Value) -> serde_json::Value {
    build_nodes_stats_response(body)
}

pub fn invoke_cluster_stats_live_route(body: &serde_json::Value) -> serde_json::Value {
    build_cluster_stats_response(body)
}

pub fn invoke_index_stats_live_route(body: &serde_json::Value) -> serde_json::Value {
    build_index_stats_response(body)
}

pub const STATS_ROUTE_REGISTRY_TABLE: [StatsRouteRegistryEntry; 3] = [
    StatsRouteRegistryEntry {
        method: "GET",
        path: NODES_STATS_ROUTE_PATH,
        family: STATS_ROUTE_FAMILY,
        hook: invoke_nodes_stats_live_route,
    },
    StatsRouteRegistryEntry {
        method: "GET",
        path: CLUSTER_STATS_ROUTE_PATH,
        family: STATS_ROUTE_FAMILY,
        hook: invoke_cluster_stats_live_route,
    },
    StatsRouteRegistryEntry {
        method: "GET",
        path: INDEX_STATS_ROUTE_PATH,
        family: STATS_ROUTE_FAMILY,
        hook: invoke_index_stats_live_route,
    },
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stats_registry_table_describes_bounded_stats_surface() {
        assert_eq!(STATS_ROUTE_REGISTRY_TABLE.len(), 3);
        assert_eq!(STATS_ROUTE_REGISTRY_TABLE[0].path, "/_nodes/stats");
        assert_eq!(STATS_ROUTE_REGISTRY_TABLE[1].path, "/_cluster/stats");
        assert_eq!(STATS_ROUTE_REGISTRY_TABLE[2].path, "/_stats");
    }

    #[test]
    fn nodes_stats_response_keeps_only_nodes_summary_field() {
        let body = serde_json::json!({
            "nodes": {
                "node-a": {
                    "timestamp": 1
                }
            },
            "cluster_name": "drop-me"
        });
        let normalized = build_nodes_stats_response(&body);
        assert!(normalized.get("nodes").is_some());
        assert!(normalized.get("cluster_name").is_none());
    }

    #[test]
    fn cluster_and_index_stats_responses_keep_bounded_top_level_fields() {
        let cluster = build_cluster_stats_response(&serde_json::json!({
            "cluster_name": "steelsearch-dev",
            "status": "yellow",
            "indices": { "count": 1 },
            "nodes": { "count": { "total": 1 } },
            "fs": { "total_in_bytes": 0 },
            "status": "drop-me"
        }));
        let index = build_index_stats_response(&serde_json::json!({
            "_shards": { "total": 1, "successful": 1, "failed": 0 },
            "_all": { "primaries": {} },
            "indices": { "logs-000001": {} },
            "shards": "drop-me"
        }));

        assert!(cluster.get("cluster_name").is_some());
        assert!(cluster.get("status").is_some());
        assert!(cluster.get("indices").is_some());
        assert!(cluster.get("nodes").is_some());
        assert!(cluster.get("fs").is_some());
        assert!(index.get("_all").is_some());
        assert!(index.get("_shards").is_some());
        assert!(index.get("indices").is_some());
        assert!(index.get("shards").is_none());
    }

    #[test]
    fn stats_live_hooks_reuse_bounded_summary_helpers() {
        let nodes = invoke_nodes_stats_live_route(&serde_json::json!({
            "nodes": { "node-a": { "timestamp": 1 } },
            "cluster_name": "drop-me"
        }));
        let cluster = invoke_cluster_stats_live_route(&serde_json::json!({
            "cluster_name": "steelsearch-dev",
            "status": "yellow",
            "indices": { "count": 1 },
            "nodes": { "count": { "total": 1 } },
            "fs": { "total_in_bytes": 0 }
        }));
        let index = invoke_index_stats_live_route(&serde_json::json!({
            "_shards": { "total": 1, "successful": 1, "failed": 0 },
            "_all": { "primaries": {} },
            "indices": { "logs-000001": {} },
            "shards": "drop-me"
        }));

        assert!(nodes.get("nodes").is_some());
        assert!(nodes.get("cluster_name").is_none());
        assert!(cluster.get("cluster_name").is_some());
        assert!(cluster.get("indices").is_some());
        assert!(cluster.get("status").is_some());
        assert!(cluster.get("fs").is_some());
        assert!(index.get("_all").is_some());
        assert!(index.get("_shards").is_some());
        assert!(index.get("shards").is_none());
    }
}
