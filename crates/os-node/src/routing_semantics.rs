//! Source-owned custom routing subset for Phase A write/read/search work.

pub const ROUTING_QUERY_FIELD: &str = "routing";

pub fn build_routing_subset(query: &serde_json::Value) -> serde_json::Value {
    let Some(object) = query.as_object() else {
        return serde_json::json!({});
    };

    match object.get(ROUTING_QUERY_FIELD) {
        Some(value) => serde_json::json!({ ROUTING_QUERY_FIELD: value }),
        None => serde_json::json!({}),
    }
}

pub fn normalize_routing_tokens(raw: Option<&str>) -> Vec<String> {
    raw.unwrap_or("")
        .split(',')
        .map(str::trim)
        .filter(|segment| !segment.is_empty())
        .map(ToOwned::to_owned)
        .collect()
}

pub fn routed_visibility_matches(stored_routing: Option<&str>, requested_routing: Option<&str>) -> bool {
    match (stored_routing, requested_routing) {
        (Some(stored), Some(requested)) => normalize_routing_tokens(Some(requested))
            .iter()
            .any(|token| token == stored),
        (Some(_), None) => false,
        (None, Some(_)) => false,
        (None, None) => true,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn routing_subset_keeps_only_routing_query_field() {
        let subset = build_routing_subset(&serde_json::json!({
            "routing": "tenant-a",
            "refresh": "wait_for"
        }));
        assert_eq!(subset, serde_json::json!({ "routing": "tenant-a" }));
    }

    #[test]
    fn routing_token_normalization_supports_comma_separated_selectors() {
        assert_eq!(
            normalize_routing_tokens(Some("tenant-a, tenant-b,,tenant-c")),
            vec![
                "tenant-a".to_string(),
                "tenant-b".to_string(),
                "tenant-c".to_string()
            ]
        );
    }

    #[test]
    fn routed_visibility_requires_matching_custom_routing_token() {
        assert!(routed_visibility_matches(Some("tenant-a"), Some("tenant-a")));
        assert!(routed_visibility_matches(
            Some("tenant-a"),
            Some("tenant-b,tenant-a")
        ));
        assert!(!routed_visibility_matches(Some("tenant-a"), Some("tenant-b")));
        assert!(!routed_visibility_matches(Some("tenant-a"), None));
        assert!(routed_visibility_matches(None, None));
    }
}
