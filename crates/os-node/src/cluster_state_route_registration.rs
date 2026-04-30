//! Workspace-visible anchor for cluster-state REST route registration work.
//!
//! The daemon currently exposes `GET /_cluster/state`, but the concrete route
//! registration path is not yet extracted into a source location that can be
//! edited independently from the daemon entrypoint. This module exists so that
//! compatibility work on metric/index/filter handling has a stable source-owned
//! place to hang shared constants and follow-up extraction work.

use os_rest::{RestErrorKind, RestMethod, RestRequest, RestResponse};
use serde_json::{Map, Value};

pub type ClusterStateRouteInvokeFn =
    fn(&RestRequest, &Value) -> Result<RestResponse, RestResponse>;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ClusterStateRouteRegistryEntry {
    pub method: RestMethod,
    pub path: &'static str,
    pub hook: ClusterStateRouteInvokeFn,
}

/// Stable metric families that current `Phase A` docs describe as the bounded
/// direction for `_cluster/state`.
pub const CLUSTER_STATE_SUPPORTED_METRIC_FAMILIES: &[&str] = &[
    "cluster identity subset",
    "top-level state identity subset",
    "metadata summary subset",
    "node summary subset",
    "routing summary subset",
    "routing nodes subset",
    "block summary subset",
];

/// Parameter buckets that must stay explicit fail-closed until real handler
/// extraction and side-by-side validation exist.
pub const CLUSTER_STATE_FAIL_CLOSED_PARAMETER_BUCKETS: &[&str] = &[
    "unsupported metrics",
    "unsupported index filters",
    "unsupported mixed metric/filter combinations",
];

/// Exact metric names currently accepted by the bounded `_cluster/state`
/// compatibility helper.
pub const CLUSTER_STATE_SUPPORTED_METRICS: &[&str] =
    &["metadata", "nodes", "routing_table", "routing_nodes", "blocks"];

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ClusterStateRouteScope {
    pub metrics: Vec<String>,
    pub indices: Vec<String>,
}

impl ClusterStateRouteScope {
    pub fn targets_metadata_or_routing(&self) -> bool {
        self.metrics.is_empty()
            || self
                .metrics
                .iter()
                .all(|metric| metric == "metadata" || metric == "routing_table")
    }
}

pub fn parse_cluster_state_route_scope(
    metric_segment: Option<&str>,
    indices_segment: Option<&str>,
) -> Result<ClusterStateRouteScope, String> {
    let metrics = split_csv(metric_segment)?;
    for metric in &metrics {
        if !CLUSTER_STATE_SUPPORTED_METRICS.contains(&metric.as_str()) {
            return Err(format!("unsupported metric [{metric}]"));
        }
    }

    let indices = split_csv(indices_segment)?;
    Ok(ClusterStateRouteScope { metrics, indices })
}

pub fn apply_cluster_state_route_scope(
    body: &Value,
    metric_segment: Option<&str>,
    indices_segment: Option<&str>,
) -> Result<Value, RestResponse> {
    let scope = parse_cluster_state_route_scope(metric_segment, indices_segment)
        .map_err(|error| RestResponse::opensearch_error_kind(RestErrorKind::IllegalArgument, error))?;

    if scope.metrics.is_empty() {
        return Ok(body.clone());
    }

    let Some(source) = body.as_object() else {
        return Ok(body.clone());
    };

    let mut filtered = Map::new();
    for key in ["cluster_name", "cluster_uuid"] {
        if let Some(value) = source.get(key) {
            filtered.insert(key.to_string(), value.clone());
        }
    }

    for metric in &scope.metrics {
        match metric.as_str() {
            "metadata" => {
                if let Some(metadata) = source.get("metadata") {
                    filtered.insert(
                        "metadata".to_string(),
                        filter_index_section(metadata, &scope.indices),
                    );
                }
            }
            "nodes" => {
                if let Some(nodes) = source.get("nodes") {
                    filtered.insert("nodes".to_string(), nodes.clone());
                }
            }
            "blocks" => {
                if let Some(blocks) = source.get("blocks") {
                    filtered.insert("blocks".to_string(), blocks.clone());
                }
            }
            "routing_table" => {
                if let Some(routing_table) = source.get("routing_table") {
                    filtered.insert(
                        "routing_table".to_string(),
                        filter_index_section(routing_table, &scope.indices),
                    );
                }
            }
            "routing_nodes" => {
                if let Some(routing_nodes) = source.get("routing_nodes") {
                    filtered.insert("routing_nodes".to_string(), routing_nodes.clone());
                }
            }
            _ => {}
        }
    }

    Ok(Value::Object(filtered))
}

pub fn build_cluster_state_rest_response(
    body: &Value,
    metric_segment: Option<&str>,
    indices_segment: Option<&str>,
) -> Result<RestResponse, RestResponse> {
    apply_cluster_state_route_scope(body, metric_segment, indices_segment)
        .map(|filtered| RestResponse::json(200, filtered))
}

pub fn invoke_cluster_state_live_route(
    request: &RestRequest,
    body: &Value,
) -> Result<RestResponse, RestResponse> {
    let metric_segment = request
        .path_params
        .get("metric")
        .or_else(|| request.query_params.get("metric"))
        .map(String::as_str);
    let indices_segment = request
        .path_params
        .get("indices")
        .or_else(|| request.query_params.get("indices"))
        .map(String::as_str);
    build_cluster_state_rest_response(body, metric_segment, indices_segment)
}

pub const CLUSTER_STATE_ROUTE_REGISTRY_HOOK: ClusterStateRouteInvokeFn =
    invoke_cluster_state_live_route;

pub const CLUSTER_STATE_ROUTE_REGISTRY_ENTRY: ClusterStateRouteRegistryEntry =
    ClusterStateRouteRegistryEntry {
        method: RestMethod::Get,
        path: "/_cluster/state",
        hook: CLUSTER_STATE_ROUTE_REGISTRY_HOOK,
    };

fn split_csv(raw: Option<&str>) -> Result<Vec<String>, String> {
    let Some(raw) = raw.map(str::trim).filter(|value| !value.is_empty()) else {
        return Ok(Vec::new());
    };

    let mut values = Vec::new();
    for value in raw.split(',') {
        let value = value.trim();
        if value.is_empty() {
            return Err("empty comma-separated token".to_string());
        }
        values.push(value.to_string());
    }
    Ok(values)
}

fn filter_index_section(value: &Value, indices: &[String]) -> Value {
    if indices.is_empty() {
        return value.clone();
    }

    let Some(object) = value.as_object() else {
        return value.clone();
    };
    let mut filtered = object.clone();

    if let Some(indices_value) = object.get("indices").and_then(Value::as_object) {
        let mut selected = Map::new();
        for index in indices {
            if index == "_all" {
                selected.extend(indices_value.clone());
                continue;
            }
            if index.contains('*') {
                let needle = index.trim_end_matches('*');
                for (candidate, entry) in indices_value {
                    if candidate.starts_with(needle) {
                        selected.insert(candidate.clone(), entry.clone());
                    }
                }
                continue;
            }
            if let Some(entry) = indices_value.get(index) {
                selected.insert(index.clone(), entry.clone());
            }
        }
        filtered.insert("indices".to_string(), Value::Object(selected));
    }

    Value::Object(filtered)
}

#[cfg(test)]
mod tests {
    use super::{
        apply_cluster_state_route_scope, build_cluster_state_rest_response,
        invoke_cluster_state_live_route, parse_cluster_state_route_scope,
        CLUSTER_STATE_ROUTE_REGISTRY_ENTRY, CLUSTER_STATE_ROUTE_REGISTRY_HOOK,
    };
    use os_rest::{RestMethod, RestRequest};
    use serde_json::json;

    #[test]
    fn parses_empty_cluster_state_scope() {
        let scope = parse_cluster_state_route_scope(None, None).unwrap();
        assert!(scope.metrics.is_empty());
        assert!(scope.indices.is_empty());
    }

    #[test]
    fn parses_supported_metrics_and_indices() {
        let scope =
            parse_cluster_state_route_scope(Some("metadata,routing_table"), Some("logs-a,logs-b"))
                .unwrap();
        assert_eq!(scope.metrics, vec!["metadata", "routing_table"]);
        assert_eq!(scope.indices, vec!["logs-a", "logs-b"]);
    }

    #[test]
    fn rejects_unknown_metric() {
        let error = parse_cluster_state_route_scope(Some("unsupported"), None).unwrap_err();
        assert!(error.contains("unsupported metric [unsupported]"));
    }

    #[test]
    fn supports_wildcard_index_filter() {
        let scope = parse_cluster_state_route_scope(Some("metadata"), Some("logs-*")).unwrap();
        assert_eq!(scope.indices, vec!["logs-*"]);
    }

    #[test]
    fn supports_nodes_metric_with_index_filter() {
        let scope = parse_cluster_state_route_scope(Some("nodes"), Some("logs-a")).unwrap();
        assert_eq!(scope.metrics, vec!["nodes"]);
        assert_eq!(scope.indices, vec!["logs-a"]);
    }

    #[test]
    fn filters_cluster_state_to_requested_metrics() {
        let body = json!({
            "cluster_name": "steel-dev",
            "cluster_uuid": "cluster-uuid",
            "version": 7,
            "state_uuid": "state-uuid",
            "master_node": "node-a",
            "metadata": { "indices": { "logs-a": { "state": "open" } } },
            "nodes": { "node-a": { "name": "node-a" } },
            "routing_table": { "indices": { "logs-a": { "shards": {} } } }
        });

        let filtered =
            apply_cluster_state_route_scope(&body, Some("metadata,nodes"), None).unwrap();
        assert_eq!(filtered["cluster_name"], "steel-dev");
        assert!(filtered.get("version").is_none());
        assert!(filtered.get("state_uuid").is_none());
        assert!(filtered.get("master_node").is_none());
        assert!(filtered.get("routing_table").is_none());
        assert!(filtered.get("metadata").is_some());
        assert!(filtered.get("nodes").is_some());
    }

    #[test]
    fn filters_cluster_state_indices_inside_metadata_and_routing() {
        let body = json!({
            "cluster_name": "steel-dev",
            "cluster_uuid": "cluster-uuid",
            "version": 7,
            "state_uuid": "state-uuid",
            "master_node": "node-a",
            "metadata": {
                "indices": {
                    "logs-a": { "state": "open" },
                    "logs-b": { "state": "open" }
                }
            },
            "routing_table": {
                "indices": {
                    "logs-a": { "shards": {} },
                    "logs-b": { "shards": {} }
                }
            }
        });

        let filtered =
            apply_cluster_state_route_scope(&body, Some("metadata,routing_table"), Some("logs-b"))
                .unwrap();
        assert!(filtered["metadata"]["indices"].get("logs-a").is_none());
        assert!(filtered["routing_table"]["indices"].get("logs-a").is_none());
        assert!(filtered["metadata"]["indices"].get("logs-b").is_some());
        assert!(filtered["routing_table"]["indices"].get("logs-b").is_some());
    }

    #[test]
    fn builds_rest_response_from_filtered_cluster_state_scope() {
        let body = json!({
            "cluster_name": "steel-dev",
            "cluster_uuid": "cluster-uuid",
            "version": 7,
            "state_uuid": "state-uuid",
            "master_node": "node-a",
            "nodes": { "node-a": { "name": "node-a" } }
        });

        let response = build_cluster_state_rest_response(&body, Some("nodes"), None).unwrap();
        assert_eq!(response.status, 200);
        assert_eq!(response.body["nodes"]["node-a"]["name"], "node-a");
        assert_eq!(response.body["cluster_name"], "steel-dev");
        assert!(response.body.get("version").is_none());
    }

    #[test]
    fn invokes_live_route_from_request_path_params() {
        let body = json!({
            "cluster_name": "steel-dev",
            "cluster_uuid": "cluster-uuid",
            "version": 7,
            "state_uuid": "state-uuid",
            "master_node": "node-a",
            "metadata": { "indices": { "logs-a": { "state": "open" } } },
            "nodes": { "node-a": { "name": "node-a" } }
        });
        let mut request = RestRequest::new(RestMethod::Get, "/_cluster/state/metadata/logs-a");
        request
            .path_params
            .insert("metric".to_string(), "metadata".to_string());
        request
            .path_params
            .insert("indices".to_string(), "logs-a".to_string());

        let response = invoke_cluster_state_live_route(&request, &body).unwrap();
        assert_eq!(response.status, 200);
        assert!(response.body.get("nodes").is_none());
        assert!(response.body["metadata"]["indices"].get("logs-a").is_some());
    }

    #[test]
    fn registry_hook_points_at_live_route_invoke_helper() {
        let body = json!({
            "cluster_name": "steel-dev",
            "cluster_uuid": "cluster-uuid",
            "version": 7,
            "state_uuid": "state-uuid",
            "master_node": "node-a",
            "nodes": { "node-a": { "name": "node-a" } }
        });
        let mut request = RestRequest::new(RestMethod::Get, "/_cluster/state/nodes");
        request
            .path_params
            .insert("metric".to_string(), "nodes".to_string());

        let response = CLUSTER_STATE_ROUTE_REGISTRY_HOOK(&request, &body).unwrap();
        assert_eq!(response.status, 200);
        assert_eq!(response.body["nodes"]["node-a"]["name"], "node-a");
    }

    #[test]
    fn includes_routing_nodes_metric_when_requested() {
        let body = json!({
            "cluster_name": "steel-dev",
            "cluster_uuid": "cluster-uuid",
            "version": 7,
            "state_uuid": "state-uuid",
            "master_node": "node-a",
            "routing_nodes": {
                "unassigned": [],
                "nodes": {
                    "node-a": [
                        { "index": "logs-a", "node": "node-a", "primary": true, "state": "STARTED" }
                    ]
                }
            }
        });

        let response = build_cluster_state_rest_response(&body, Some("routing_nodes"), None).unwrap();
        assert_eq!(response.status, 200);
        assert!(response.body.get("routing_nodes").is_some());
        assert!(response.body.get("master_node").is_none());
    }

    #[test]
    fn registry_entry_describes_cluster_state_get_route() {
        assert_eq!(CLUSTER_STATE_ROUTE_REGISTRY_ENTRY.method, RestMethod::Get);
        assert_eq!(CLUSTER_STATE_ROUTE_REGISTRY_ENTRY.path, "/_cluster/state");
    }
}
