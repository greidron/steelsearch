//! Workspace-visible route-registration anchors for bounded allocation-explain parity work.

pub const CLUSTER_ALLOCATION_EXPLAIN_ROUTE_PATH: &str = "/_cluster/allocation/explain";
pub const CLUSTER_ALLOCATION_EXPLAIN_ROUTE_METHOD: &str = "GET";
pub const CLUSTER_ALLOCATION_EXPLAIN_ROUTE_FAMILY: &str = "allocation_explain_readback";

pub const ALLOCATION_EXPLAIN_RESPONSE_FIELDS: [&str; 6] = [
    "index",
    "shard",
    "primary",
    "current_state",
    "current_node",
    "node_allocation_decisions",
];

pub const ALLOCATION_EXPLAIN_NODE_DECISION_FIELDS: [&str; 4] = [
    "node_name",
    "node_decision",
    "weight_ranking",
    "deciders",
];

pub const ALLOCATION_EXPLAIN_DECIDER_FIELDS: [&str; 3] =
    ["decider", "decision", "explanation"];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AllocationExplainRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
    pub hook: AllocationExplainRouteInvokeFn,
}

fn normalize_fields(
    body: &serde_json::Value,
    fields: &[&str],
) -> serde_json::Map<String, serde_json::Value> {
    let mut normalized = serde_json::Map::new();
    for field in fields {
        if let Some(value) = body.get(*field) {
            normalized.insert((*field).to_string(), value.clone());
        }
    }
    normalized
}

fn normalize_deciders(deciders: &serde_json::Value) -> serde_json::Value {
    let Some(deciders) = deciders.as_array() else {
        return serde_json::Value::Array(Vec::new());
    };
    serde_json::Value::Array(
        deciders
            .iter()
            .map(|decider| serde_json::Value::Object(normalize_fields(
                decider,
                &ALLOCATION_EXPLAIN_DECIDER_FIELDS,
            )))
            .collect(),
    )
}

fn normalize_node_allocation_decisions(body: &serde_json::Value) -> serde_json::Value {
    let Some(decisions) = body.get("node_allocation_decisions").and_then(|v| v.as_array()) else {
        return serde_json::Value::Array(Vec::new());
    };

    serde_json::Value::Array(
        decisions
            .iter()
            .map(|decision| {
                let mut normalized =
                    normalize_fields(decision, &ALLOCATION_EXPLAIN_NODE_DECISION_FIELDS);
                if let Some(deciders) = decision.get("deciders") {
                    normalized.insert("deciders".to_string(), normalize_deciders(deciders));
                }
                serde_json::Value::Object(normalized)
            })
            .collect(),
    )
}

pub fn build_cluster_allocation_explain_response(
    body: &serde_json::Value,
) -> serde_json::Value {
    let mut normalized = normalize_fields(body, &ALLOCATION_EXPLAIN_RESPONSE_FIELDS);
    if body.get("node_allocation_decisions").is_some() {
        normalized.insert(
            "node_allocation_decisions".to_string(),
            normalize_node_allocation_decisions(body),
        );
    }
    serde_json::Value::Object(normalized)
}

pub type AllocationExplainRouteInvokeFn = fn(&serde_json::Value) -> serde_json::Value;

pub fn invoke_cluster_allocation_explain_live_route(
    body: &serde_json::Value,
) -> serde_json::Value {
    build_cluster_allocation_explain_response(body)
}

pub const ALLOCATION_EXPLAIN_ROUTE_REGISTRY_TABLE: [AllocationExplainRouteRegistryEntry; 1] = [
    AllocationExplainRouteRegistryEntry {
        method: CLUSTER_ALLOCATION_EXPLAIN_ROUTE_METHOD,
        path: CLUSTER_ALLOCATION_EXPLAIN_ROUTE_PATH,
        family: CLUSTER_ALLOCATION_EXPLAIN_ROUTE_FAMILY,
        hook: invoke_cluster_allocation_explain_live_route,
    },
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn allocation_explain_registry_table_describes_bounded_surface() {
        assert_eq!(ALLOCATION_EXPLAIN_ROUTE_REGISTRY_TABLE.len(), 1);
        assert_eq!(
            ALLOCATION_EXPLAIN_ROUTE_REGISTRY_TABLE[0].method,
            CLUSTER_ALLOCATION_EXPLAIN_ROUTE_METHOD
        );
        assert_eq!(
            ALLOCATION_EXPLAIN_ROUTE_REGISTRY_TABLE[0].path,
            CLUSTER_ALLOCATION_EXPLAIN_ROUTE_PATH
        );
    }

    #[test]
    fn allocation_explain_response_keeps_only_bounded_top_level_fields() {
        let normalized = build_cluster_allocation_explain_response(&serde_json::json!({
            "index": "logs-compat",
            "shard": 0,
            "primary": true,
            "current_state": "unassigned",
            "current_node": { "name": "node-a" },
            "node_allocation_decisions": [],
            "can_allocate": "drop-me"
        }));

        assert!(normalized.get("index").is_some());
        assert!(normalized.get("current_state").is_some());
        assert!(normalized.get("node_allocation_decisions").is_some());
        assert!(normalized.get("can_allocate").is_none());
    }

    #[test]
    fn allocation_explain_response_normalizes_node_decisions_and_deciders() {
        let normalized = build_cluster_allocation_explain_response(&serde_json::json!({
            "index": "logs-compat",
            "node_allocation_decisions": [
                {
                    "node_name": "node-a",
                    "node_decision": "yes",
                    "weight_ranking": 1,
                    "deciders": [
                        {
                            "decider": "same_shard",
                            "decision": "YES",
                            "explanation": "allowed",
                            "extra": "drop-me"
                        }
                    ],
                    "store": "drop-me"
                }
            ]
        }));

        let decisions = normalized
            .get("node_allocation_decisions")
            .and_then(|value| value.as_array())
            .expect("node decisions array");
        let first = decisions[0].as_object().expect("first decision object");
        assert!(first.get("node_name").is_some());
        assert!(first.get("store").is_none());

        let deciders = first
            .get("deciders")
            .and_then(|value| value.as_array())
            .expect("deciders array");
        let first_decider = deciders[0].as_object().expect("first decider object");
        assert!(first_decider.get("decider").is_some());
        assert!(first_decider.get("extra").is_none());
    }

    #[test]
    fn allocation_explain_live_hook_reuses_bounded_helper() {
        let normalized = invoke_cluster_allocation_explain_live_route(&serde_json::json!({
            "index": "logs-compat",
            "shard": 0,
            "primary": true,
            "current_state": "started",
            "node_allocation_decisions": [],
            "allocate_explanation": "drop-me"
        }));

        assert!(normalized.get("current_state").is_some());
        assert!(normalized.get("allocate_explanation").is_none());
    }
}
