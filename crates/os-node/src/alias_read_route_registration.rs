//! Workspace-visible route-registration anchors for bounded alias readback work.

pub const GET_ALIAS_ROUTE_METHOD: &str = "GET";
pub const GET_GLOBAL_ALIAS_ROUTE_PATH: &str = "/_alias";
pub const GET_NAMED_ALIAS_ROUTE_PATH: &str = "/_alias/{name}";
pub const GET_INDEX_ALIAS_ROUTE_PATH: &str = "/{index}/_alias";
pub const GET_INDEX_NAMED_ALIAS_ROUTE_PATH: &str = "/{index}/_alias/{name}";
pub const GET_ALIASES_ROUTE_PATH: &str = "/_aliases";
pub const ALIAS_READ_ROUTE_FAMILY: &str = "alias_readback";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AliasReadRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
}

pub fn parse_alias_read_selectors(target: &str) -> Vec<String> {
    target
        .split(',')
        .map(str::trim)
        .filter(|segment| !segment.is_empty())
        .map(ToOwned::to_owned)
        .collect()
}

fn selector_matches(selector: &str, candidate: &str) -> bool {
    if selector.contains('?') {
        return selector_matches_with_question_wildcard(selector, candidate);
    }
    if !selector.contains('*') {
        return selector == candidate;
    }
    let parts = selector.split('*').collect::<Vec<_>>();
    let mut remainder = candidate;
    let anchored_start = !selector.starts_with('*');
    let anchored_end = !selector.ends_with('*');

    for (index, part) in parts.iter().enumerate() {
        if part.is_empty() {
            continue;
        }
        if index == 0 && anchored_start {
            let Some(next) = remainder.strip_prefix(part) else {
                return false;
            };
            remainder = next;
            continue;
        }
        if index == parts.len() - 1 && anchored_end {
            return remainder.ends_with(part);
        }
        let Some(position) = remainder.find(part) else {
            return false;
        };
        remainder = &remainder[position + part.len()..];
    }

    if !anchored_end {
        return true;
    }
    match parts.last().copied() {
        None => true,
        Some("") => true,
        Some(last) => remainder.ends_with(last),
    }
}

fn selector_matches_with_question_wildcard(selector: &str, candidate: &str) -> bool {
    let selector = selector.chars().collect::<Vec<_>>();
    let candidate = candidate.chars().collect::<Vec<_>>();
    let mut matches = vec![vec![false; candidate.len() + 1]; selector.len() + 1];
    matches[0][0] = true;
    for selector_index in 1..=selector.len() {
        if selector[selector_index - 1] == '*' {
            matches[selector_index][0] = matches[selector_index - 1][0];
        }
    }
    for selector_index in 1..=selector.len() {
        for candidate_index in 1..=candidate.len() {
            matches[selector_index][candidate_index] = match selector[selector_index - 1] {
                '*' => {
                    matches[selector_index - 1][candidate_index]
                        || matches[selector_index][candidate_index - 1]
                }
                '?' => matches[selector_index - 1][candidate_index - 1],
                literal => {
                    literal == candidate[candidate_index - 1]
                        && matches[selector_index - 1][candidate_index - 1]
                }
            };
        }
    }
    matches[selector.len()][candidate.len()]
}

pub fn build_alias_readback_response(
    indices: &serde_json::Value,
    index_target: Option<&str>,
    alias_target: Option<&str>,
) -> serde_json::Value {
    let index_selectors = index_target
        .map(parse_alias_read_selectors)
        .unwrap_or_default();
    let alias_selectors = alias_target
        .map(parse_alias_read_selectors)
        .unwrap_or_default();
    let Some(index_map) = indices.as_object() else {
        return serde_json::json!({});
    };

    let mut response = serde_json::Map::new();
    for (index_name, metadata) in index_map {
        if !index_selectors.is_empty()
            && !index_selectors
                .iter()
                .any(|selector| selector_matches(selector, index_name))
        {
            continue;
        }
        let Some(aliases) = metadata.get("aliases").and_then(|value| value.as_object()) else {
            continue;
        };

        let mut filtered_aliases = serde_json::Map::new();
        for (alias_name, alias_metadata) in aliases {
            if !alias_selectors.is_empty()
                && !alias_selectors
                    .iter()
                    .any(|selector| selector_matches(selector, alias_name))
            {
                continue;
            }
            filtered_aliases.insert(alias_name.clone(), alias_metadata.clone());
        }

        if !filtered_aliases.is_empty() {
            response.insert(
                index_name.clone(),
                serde_json::json!({
                    "aliases": filtered_aliases
                }),
            );
        }
    }

    serde_json::Value::Object(response)
}

pub fn missing_explicit_aliases(
    response: &serde_json::Value,
    alias_target: Option<&str>,
) -> Vec<String> {
    let Some(alias_target) = alias_target else {
        return Vec::new();
    };
    let requested_aliases = parse_alias_read_selectors(alias_target);
    let mut returned_aliases = std::collections::BTreeSet::new();
    if let Some(indices) = response.as_object() {
        for index_body in indices.values() {
            if let Some(aliases) = index_body
                .get("aliases")
                .and_then(|value| value.as_object())
            {
                returned_aliases.extend(aliases.keys().cloned());
            }
        }
    }

    let first_wildcard_index = requested_aliases
        .iter()
        .position(|alias| alias.contains('*') || alias.contains('?'))
        .unwrap_or(requested_aliases.len());
    let mut missing = Vec::new();
    for (index, alias) in requested_aliases.iter().enumerate() {
        if alias == "_all"
            || alias.contains('*')
            || alias.contains('?')
            || (index > first_wildcard_index && alias.starts_with('-'))
        {
            continue;
        }
        let excluded = requested_aliases
            .iter()
            .skip(std::cmp::max(index + 1, first_wildcard_index))
            .any(|candidate| {
                candidate
                    .strip_prefix('-')
                    .is_some_and(|pattern| pattern == "_all" || selector_matches(pattern, alias))
            });
        if !excluded && !returned_aliases.contains(alias) {
            missing.push(alias.clone());
        }
    }
    missing
}

pub const ALIAS_READ_ROUTE_REGISTRY_TABLE: [AliasReadRouteRegistryEntry; 5] = [
    AliasReadRouteRegistryEntry {
        method: GET_ALIAS_ROUTE_METHOD,
        path: GET_GLOBAL_ALIAS_ROUTE_PATH,
        family: ALIAS_READ_ROUTE_FAMILY,
    },
    AliasReadRouteRegistryEntry {
        method: GET_ALIAS_ROUTE_METHOD,
        path: GET_NAMED_ALIAS_ROUTE_PATH,
        family: ALIAS_READ_ROUTE_FAMILY,
    },
    AliasReadRouteRegistryEntry {
        method: GET_ALIAS_ROUTE_METHOD,
        path: GET_INDEX_ALIAS_ROUTE_PATH,
        family: ALIAS_READ_ROUTE_FAMILY,
    },
    AliasReadRouteRegistryEntry {
        method: GET_ALIAS_ROUTE_METHOD,
        path: GET_INDEX_NAMED_ALIAS_ROUTE_PATH,
        family: ALIAS_READ_ROUTE_FAMILY,
    },
    AliasReadRouteRegistryEntry {
        method: GET_ALIAS_ROUTE_METHOD,
        path: GET_ALIASES_ROUTE_PATH,
        family: ALIAS_READ_ROUTE_FAMILY,
    },
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn alias_read_registry_table_describes_supported_readback_forms() {
        assert_eq!(ALIAS_READ_ROUTE_REGISTRY_TABLE.len(), 5);
        assert_eq!(ALIAS_READ_ROUTE_REGISTRY_TABLE[0].path, "/_alias");
        assert_eq!(ALIAS_READ_ROUTE_REGISTRY_TABLE[1].path, "/_alias/{name}");
        assert_eq!(ALIAS_READ_ROUTE_REGISTRY_TABLE[2].path, "/{index}/_alias");
        assert_eq!(
            ALIAS_READ_ROUTE_REGISTRY_TABLE[3].path,
            "/{index}/_alias/{name}"
        );
        assert_eq!(ALIAS_READ_ROUTE_REGISTRY_TABLE[4].path, "/_aliases");
    }

    #[test]
    fn alias_read_selector_parser_keeps_wildcard_and_comma_targets() {
        assert_eq!(
            parse_alias_read_selectors("logs-*,metrics-000001"),
            vec!["logs-*".to_string(), "metrics-000001".to_string()]
        );
    }

    #[test]
    fn alias_read_missing_explicit_aliases_reports_only_literal_unmatched_names() {
        let response = serde_json::json!({
            "logs-000001": {
                "aliases": {
                    "logs-read": {}
                }
            }
        });

        assert_eq!(
            missing_explicit_aliases(&response, Some("logs-read,logs-write")),
            vec!["logs-write".to_string()]
        );
        assert!(missing_explicit_aliases(&response, Some("logs-*")).is_empty());
        assert!(
            missing_explicit_aliases(&response, Some("logs-write,logs-*,-logs-write")).is_empty()
        );
    }

    #[test]
    fn alias_readback_response_supports_global_index_scoped_and_wildcard_alias_selection() {
        let indices = serde_json::json!({
            "logs-000001": {
                "aliases": {
                    "logs-read": {},
                    "logs-write": {
                        "is_write_index": true
                    }
                }
            },
            "metrics-000001": {
                "aliases": {
                    "metrics-read": {}
                }
            }
        });

        let global_named = build_alias_readback_response(&indices, None, Some("logs-read"));
        let index_scoped =
            build_alias_readback_response(&indices, Some("logs-000001"), Some("logs-*"));
        let wildcard_aliases = build_alias_readback_response(&indices, None, Some("*-read"));

        assert!(global_named.get("logs-000001").is_some());
        assert!(global_named.get("metrics-000001").is_none());
        assert!(index_scoped.get("logs-000001").is_some());
        assert!(index_scoped.get("metrics-000001").is_none());
        assert!(wildcard_aliases["logs-000001"]["aliases"]
            .get("logs-read")
            .is_some());
        assert!(wildcard_aliases["metrics-000001"]["aliases"]
            .get("metrics-read")
            .is_some());
        assert!(wildcard_aliases["logs-000001"]["aliases"]
            .get("logs-write")
            .is_none());
    }
}
