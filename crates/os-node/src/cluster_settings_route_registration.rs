//! Workspace-visible route-registration anchors for `GET`/`PUT /_cluster/settings`.

/// Canonical route family label for cluster-settings readback work.
pub const CLUSTER_SETTINGS_ROUTE_FAMILY: &str = "cluster_settings_readback";

/// Canonical HTTP method for the Phase A cluster-settings readback surface.
pub const CLUSTER_SETTINGS_ROUTE_METHOD: &str = "GET";

/// Canonical route path for the Phase A cluster-settings readback surface.
pub const CLUSTER_SETTINGS_ROUTE_PATH: &str = "/_cluster/settings";

/// Canonical fail-closed bucket for unsupported `GET /_cluster/settings` parameters.
pub const CLUSTER_SETTINGS_UNSUPPORTED_PARAMETER_BUCKET: &str =
    "unsupported cluster-settings readback parameter";
pub const CLUSTER_SETTINGS_SUPPORTED_QUERY_PARAMS: [&str; 2] =
    ["flat_settings", "include_defaults"];

/// Canonical runnable readback subset for `GET /_cluster/settings`.
pub const CLUSTER_SETTINGS_RUNNABLE_SUBSET_FIELDS: [&str; 2] = ["persistent", "transient"];

/// Canonical actual live-route response semantics for the current `GET /_cluster/settings` subset.
pub const CLUSTER_SETTINGS_LIVE_ROUTE_RESPONSE_FIELDS: [&str; 2] = ["persistent", "transient"];

/// Canonical response fields for the bounded `PUT /_cluster/settings` mutation subset.
pub const CLUSTER_SETTINGS_MUTATION_RESPONSE_FIELDS: [&str; 3] =
    ["acknowledged", "persistent", "transient"];

/// Workspace-visible registry entry for `GET /_cluster/settings`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ClusterSettingsRouteRegistryEntry {
    pub method: &'static str,
    pub path: &'static str,
    pub family: &'static str,
    pub hook: ClusterSettingsRouteInvokeFn,
}

/// Request-shaped live invoke input for `GET /_cluster/settings`.
pub struct ClusterSettingsRouteRequest<'a> {
    pub params: &'a [&'a str],
    pub persistent: &'a serde_json::Value,
    pub transient: &'a serde_json::Value,
}

/// Request-shaped live invoke input for the bounded `PUT /_cluster/settings` mutation subset.
pub struct ClusterSettingsMutationRequest<'a> {
    pub params: &'a [&'a str],
    pub persistent: &'a serde_json::Value,
    pub transient: &'a serde_json::Value,
}

/// Canonical bounded response-body helper for `GET /_cluster/settings`.
pub fn build_cluster_settings_response_body(
    persistent: &serde_json::Value,
    transient: &serde_json::Value,
) -> serde_json::Value {
    serde_json::json!({
        "persistent": persistent.clone(),
        "transient": transient.clone(),
    })
}

/// Canonical bounded response-body helper for `PUT /_cluster/settings`.
pub fn build_cluster_settings_mutation_response_body(
    persistent: &serde_json::Value,
    transient: &serde_json::Value,
) -> serde_json::Value {
    serde_json::json!({
        "acknowledged": true,
        "persistent": persistent.clone(),
        "transient": transient.clone(),
    })
}

fn merge_cluster_settings_section(
    base: &serde_json::Value,
    patch: &serde_json::Value,
) -> serde_json::Value {
    let mut merged = flatten_cluster_settings_section(base);
    for (key, value) in flatten_cluster_settings_section(patch) {
        if value.is_null() {
            merged.remove(&key);
        } else {
            merged.insert(key, value);
        }
    }
    expand_dotted_cluster_settings_section(&serde_json::Value::Object(merged))
}

fn flatten_cluster_settings_section(
    section: &serde_json::Value,
) -> serde_json::Map<String, serde_json::Value> {
    let mut flat = serde_json::Map::new();
    flatten_cluster_settings_section_into(None, section, &mut flat);
    flat
}

fn flatten_cluster_settings_section_into(
    prefix: Option<&str>,
    section: &serde_json::Value,
    flat: &mut serde_json::Map<String, serde_json::Value>,
) {
    match section {
        serde_json::Value::Object(map) => {
            for (key, value) in map {
                let next_key = prefix
                    .map(|current| format!("{current}.{key}"))
                    .unwrap_or_else(|| key.clone());
                if value.is_object() {
                    flatten_cluster_settings_section_into(Some(&next_key), value, flat);
                } else {
                    flat.insert(next_key, value.clone());
                }
            }
        }
        serde_json::Value::Null => {
            if let Some(prefix) = prefix {
                flat.insert(prefix.to_string(), serde_json::Value::Null);
            }
        }
        _ => {
            if let Some(prefix) = prefix {
                flat.insert(prefix.to_string(), section.clone());
            }
        }
    }
}

fn expand_dotted_cluster_settings_section(section: &serde_json::Value) -> serde_json::Value {
    let mut expanded = serde_json::Map::new();
    if let serde_json::Value::Object(section_map) = section {
        for (key, value) in section_map {
            insert_dotted_cluster_setting(&mut expanded, key, value.clone());
        }
    }
    serde_json::Value::Object(expanded)
}

fn insert_dotted_cluster_setting(
    target: &mut serde_json::Map<String, serde_json::Value>,
    dotted_key: &str,
    value: serde_json::Value,
) {
    let mut segments = dotted_key.split('.').peekable();
    let mut current = target;
    while let Some(segment) = segments.next() {
        if segments.peek().is_none() {
            current.insert(segment.to_string(), value);
            return;
        }
        let entry = current
            .entry(segment.to_string())
            .or_insert_with(|| serde_json::Value::Object(serde_json::Map::new()));
        if !entry.is_object() {
            *entry = serde_json::Value::Object(serde_json::Map::new());
        }
        current = entry
            .as_object_mut()
            .expect("cluster settings nested section must stay object");
    }
}

/// Reject unsupported query parameters for `GET /_cluster/settings`.
pub fn reject_unsupported_cluster_settings_params(
    params: &[&str],
) -> Result<(), &'static str> {
    for param in params {
        if !CLUSTER_SETTINGS_SUPPORTED_QUERY_PARAMS.contains(param) {
            return Err(CLUSTER_SETTINGS_UNSUPPORTED_PARAMETER_BUCKET);
        }
    }
    Ok(())
}

/// Canonical response-builder symbol for `GET /_cluster/settings`.
pub fn build_cluster_settings_rest_response(
    body: &serde_json::Value,
    params: &[&str],
) -> Result<serde_json::Value, &'static str> {
    reject_unsupported_cluster_settings_params(params)?;
    Ok(body.clone())
}

/// Request-shaped live invoke helper for `GET /_cluster/settings`.
pub fn invoke_cluster_settings_live_route_request(
    request: &ClusterSettingsRouteRequest<'_>,
) -> Result<serde_json::Value, &'static str> {
    let body = build_cluster_settings_response_body(request.persistent, request.transient);
    build_cluster_settings_rest_response(&body, request.params)
}

/// Adapter from persisted cluster-settings state into the request-shaped helper.
pub fn invoke_cluster_settings_from_persisted_state(
    persisted_state: &serde_json::Value,
) -> Result<serde_json::Value, &'static str> {
    let persistent = persisted_state
        .get("persistent")
        .unwrap_or(&serde_json::Value::Null);
    let transient = persisted_state
        .get("transient")
        .unwrap_or(&serde_json::Value::Null);
    let request = ClusterSettingsRouteRequest {
        params: &[],
        persistent,
        transient,
    };
    invoke_cluster_settings_live_route_request(&request)
}

/// Apply the bounded `PUT /_cluster/settings` mutation subset to persisted state.
pub fn apply_cluster_settings_mutation(
    persisted_state: &serde_json::Value,
    request: &ClusterSettingsMutationRequest<'_>,
) -> Result<serde_json::Value, &'static str> {
    reject_unsupported_cluster_settings_params(request.params)?;
    let empty_section = serde_json::Value::Object(serde_json::Map::new());
    let current_persistent = persisted_state
        .get("persistent")
        .unwrap_or(&empty_section);
    let current_transient = persisted_state
        .get("transient")
        .unwrap_or(&empty_section);
    let next_persistent = merge_cluster_settings_section(current_persistent, request.persistent);
    let next_transient = merge_cluster_settings_section(current_transient, request.transient);
    Ok(build_cluster_settings_mutation_response_body(
        &next_persistent,
        &next_transient,
    ))
}

/// Concrete live REST handler body symbol for `GET /_cluster/settings`.
pub fn build_cluster_settings_live_handler_body(
    persisted_state: &serde_json::Value,
) -> Result<serde_json::Value, &'static str> {
    invoke_cluster_settings_from_persisted_state(persisted_state)
}

/// Canonical invoke-hook type for `GET /_cluster/settings`.
pub type ClusterSettingsRouteInvokeFn = fn(&serde_json::Value) -> serde_json::Value;

/// Canonical invoke-hook symbol for `GET /_cluster/settings`.
pub fn invoke_cluster_settings_live_route(body: &serde_json::Value) -> serde_json::Value {
    build_cluster_settings_live_handler_body(body)
        .expect("empty cluster-settings readback params must stay accepted")
}

/// Canonical route hook for `GET /_cluster/settings`.
pub const CLUSTER_SETTINGS_ROUTE_REGISTRY_HOOK: ClusterSettingsRouteInvokeFn =
    invoke_cluster_settings_live_route;

/// Canonical route-registration entry for `GET /_cluster/settings`.
pub const CLUSTER_SETTINGS_ROUTE_REGISTRY_ENTRY: ClusterSettingsRouteRegistryEntry =
    ClusterSettingsRouteRegistryEntry {
        method: CLUSTER_SETTINGS_ROUTE_METHOD,
        path: CLUSTER_SETTINGS_ROUTE_PATH,
        family: CLUSTER_SETTINGS_ROUTE_FAMILY,
        hook: CLUSTER_SETTINGS_ROUTE_REGISTRY_HOOK,
    };

/// Canonical route-registration table for the current `GET /_cluster/settings` surface.
pub const CLUSTER_SETTINGS_ROUTE_REGISTRY_TABLE: [ClusterSettingsRouteRegistryEntry; 1] =
    [CLUSTER_SETTINGS_ROUTE_REGISTRY_ENTRY];

/// Canonical runtime dispatch record for the current `GET /_cluster/settings` surface.
pub const CLUSTER_SETTINGS_RUNTIME_DISPATCH_RECORD: (&str, ClusterSettingsRouteInvokeFn) = (
    CLUSTER_SETTINGS_ROUTE_REGISTRY_ENTRY.path,
    CLUSTER_SETTINGS_ROUTE_REGISTRY_ENTRY.hook,
);

/// Source-owned runtime registration body for the current `GET /_cluster/settings` surface.
pub const CLUSTER_SETTINGS_RUNTIME_REGISTRATION_BODY: [(&str, ClusterSettingsRouteInvokeFn); 1] =
    [CLUSTER_SETTINGS_RUNTIME_DISPATCH_RECORD];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cluster_settings_registry_entry_describes_get_cluster_settings() {
        assert_eq!(CLUSTER_SETTINGS_ROUTE_REGISTRY_ENTRY.method, "GET");
        assert_eq!(CLUSTER_SETTINGS_ROUTE_REGISTRY_ENTRY.path, "/_cluster/settings");
        assert_eq!(
            CLUSTER_SETTINGS_ROUTE_REGISTRY_ENTRY.family,
            "cluster_settings_readback"
        );
        assert_eq!(
            CLUSTER_SETTINGS_RUNNABLE_SUBSET_FIELDS,
            ["persistent", "transient"]
        );
        assert_eq!(
            CLUSTER_SETTINGS_LIVE_ROUTE_RESPONSE_FIELDS,
            ["persistent", "transient"]
        );
        assert_eq!(
            CLUSTER_SETTINGS_MUTATION_RESPONSE_FIELDS,
            ["acknowledged", "persistent", "transient"]
        );
    }

    #[test]
    fn cluster_settings_registry_hook_round_trips_body() {
        let body = build_cluster_settings_response_body(
            &serde_json::json!({
                "cluster.routing.allocation.enable": "all"
            }),
            &serde_json::json!({}),
        );

        let rendered = (CLUSTER_SETTINGS_ROUTE_REGISTRY_ENTRY.hook)(&body);
        assert_eq!(rendered, body);
    }

    #[test]
    fn cluster_settings_response_builder_consumes_param_reject_helper() {
        let body = build_cluster_settings_response_body(
            &serde_json::json!({}),
            &serde_json::json!({}),
        );

        assert_eq!(
            build_cluster_settings_rest_response(&body, &["local"]),
            Err("unsupported cluster-settings readback parameter")
        );
    }

    #[test]
    fn cluster_settings_request_shaped_invoke_helper_uses_params_and_sections() {
        let persistent = serde_json::json!({
            "cluster.routing.allocation.enable": "all"
        });
        let transient = serde_json::json!({
            "cluster.info.update.interval": "30s"
        });
        let request = ClusterSettingsRouteRequest {
            params: &[],
            persistent: &persistent,
            transient: &transient,
        };

        let body = invoke_cluster_settings_live_route_request(&request).unwrap();
        assert_eq!(
            body["persistent"]["cluster.routing.allocation.enable"],
            serde_json::json!("all")
        );
        assert_eq!(
            body["transient"]["cluster.info.update.interval"],
            serde_json::json!("30s")
        );
    }

    #[test]
    fn cluster_settings_registry_hook_reuses_request_shaped_helper_path() {
        let body = serde_json::json!({
            "persistent": {
                "cluster.routing.allocation.enable": "all"
            },
            "transient": {
                "cluster.info.update.interval": "30s"
            }
        });

        let rendered = invoke_cluster_settings_live_route(&body);
        assert_eq!(rendered, body);
    }

    #[test]
    fn cluster_settings_registry_hook_consumes_persisted_state_adapter() {
        let persisted_state = serde_json::json!({
            "persistent": {
                "cluster.routing.allocation.enable": "all"
            },
            "transient": {
                "cluster.info.update.interval": "30s"
            }
        });

        let rendered = invoke_cluster_settings_live_route(&persisted_state);
        assert_eq!(rendered, persisted_state);
    }

    #[test]
    fn cluster_settings_registry_entry_points_at_persisted_state_backed_hook_path() {
        let persisted_state = serde_json::json!({
            "persistent": {
                "cluster.routing.allocation.enable": "all"
            },
            "transient": {
                "cluster.info.update.interval": "30s"
            }
        });

        let via_entry = (CLUSTER_SETTINGS_ROUTE_REGISTRY_ENTRY.hook)(&persisted_state);
        let via_adapter = invoke_cluster_settings_from_persisted_state(&persisted_state).unwrap();
        assert_eq!(via_entry, via_adapter);
    }

    #[test]
    fn cluster_settings_registry_table_exposes_get_cluster_settings_surface() {
        assert_eq!(CLUSTER_SETTINGS_ROUTE_REGISTRY_TABLE.len(), 1);
        assert_eq!(CLUSTER_SETTINGS_ROUTE_REGISTRY_TABLE[0].path, "/_cluster/settings");
    }

    #[test]
    fn cluster_settings_runtime_dispatch_record_points_at_get_cluster_settings() {
        assert_eq!(CLUSTER_SETTINGS_RUNTIME_DISPATCH_RECORD.0, "/_cluster/settings");
    }

    #[test]
    fn cluster_settings_runtime_registration_body_reuses_dispatch_record() {
        assert_eq!(CLUSTER_SETTINGS_RUNTIME_REGISTRATION_BODY.len(), 1);
        assert_eq!(
            CLUSTER_SETTINGS_RUNTIME_REGISTRATION_BODY[0].0,
            CLUSTER_SETTINGS_RUNTIME_DISPATCH_RECORD.0
        );
    }

    #[test]
    fn cluster_settings_persisted_state_adapter_feeds_request_shaped_helper() {
        let persisted_state = serde_json::json!({
            "persistent": {
                "cluster.routing.allocation.enable": "all"
            },
            "transient": {
                "cluster.info.update.interval": "30s"
            }
        });

        let rendered = invoke_cluster_settings_from_persisted_state(&persisted_state).unwrap();
        assert_eq!(
            rendered["persistent"]["cluster.routing.allocation.enable"],
            serde_json::json!("all")
        );
        assert_eq!(
            rendered["transient"]["cluster.info.update.interval"],
            serde_json::json!("30s")
        );
    }

    #[test]
    fn cluster_settings_live_handler_body_symbol_reuses_persisted_state_adapter() {
        let persisted_state = serde_json::json!({
            "persistent": {
                "cluster.routing.allocation.enable": "all"
            },
            "transient": {
                "cluster.info.update.interval": "30s"
            }
        });

        let via_body = build_cluster_settings_live_handler_body(&persisted_state).unwrap();
        let via_adapter = invoke_cluster_settings_from_persisted_state(&persisted_state).unwrap();
        assert_eq!(via_body, via_adapter);
    }

    #[test]
    fn cluster_settings_response_body_helper_keeps_persistent_and_transient_sections() {
        let body = build_cluster_settings_response_body(
            &serde_json::json!({
                "cluster.routing.allocation.enable": "all"
            }),
            &serde_json::json!({
                "cluster.info.update.interval": "30s"
            }),
        );

        assert_eq!(
            body["persistent"]["cluster.routing.allocation.enable"],
            serde_json::json!("all")
        );
        assert_eq!(
            body["transient"]["cluster.info.update.interval"],
            serde_json::json!("30s")
        );
    }

    #[test]
    fn cluster_settings_param_reject_helper_accepts_empty_param_set() {
        assert_eq!(reject_unsupported_cluster_settings_params(&[]), Ok(()));
    }

    #[test]
    fn cluster_settings_param_reject_helper_uses_canonical_fail_closed_bucket() {
        assert_eq!(
            reject_unsupported_cluster_settings_params(&["flat_settings"]),
            Ok(())
        );
        assert_eq!(
            reject_unsupported_cluster_settings_params(&["include_defaults"]),
            Ok(())
        );
        assert_eq!(
            reject_unsupported_cluster_settings_params(&["local"]),
            Err("unsupported cluster-settings readback parameter")
        );
    }

    #[test]
    fn cluster_settings_mutation_response_body_helper_keeps_ack_and_sections() {
        let body = build_cluster_settings_mutation_response_body(
            &serde_json::json!({
                "cluster.routing.allocation.enable": "primaries"
            }),
            &serde_json::json!({
                "cluster.info.update.interval": "45s"
            }),
        );

        assert_eq!(body["acknowledged"], serde_json::json!(true));
        assert_eq!(
            body["persistent"]["cluster.routing.allocation.enable"],
            serde_json::json!("primaries")
        );
        assert_eq!(
            body["transient"]["cluster.info.update.interval"],
            serde_json::json!("45s")
        );
    }

    #[test]
    fn cluster_settings_mutation_merges_bounded_persistent_and_transient_sections() {
        let persisted_state = serde_json::json!({
            "persistent": {
                "cluster.routing.allocation.enable": "all"
            },
            "transient": {
                "cluster.info.update.interval": "30s"
            }
        });
        let request = ClusterSettingsMutationRequest {
            params: &[],
            persistent: &serde_json::json!({
                "cluster.routing.allocation.enable": "primaries"
            }),
            transient: &serde_json::json!({
                "cluster.info.update.interval": "45s"
            }),
        };

        let response = apply_cluster_settings_mutation(&persisted_state, &request).unwrap();
        assert_eq!(response["acknowledged"], serde_json::json!(true));
        assert_eq!(
            response["persistent"]["cluster"]["routing"]["allocation"]["enable"],
            serde_json::json!("primaries")
        );
        assert_eq!(
            response["transient"]["cluster"]["info"]["update"]["interval"],
            serde_json::json!("45s")
        );
    }

    #[test]
    fn cluster_settings_mutation_reuses_readback_fail_closed_param_bucket() {
        let persisted_state = serde_json::json!({
            "persistent": {},
            "transient": {}
        });
        let request = ClusterSettingsMutationRequest {
            params: &["local"],
            persistent: &serde_json::json!({}),
            transient: &serde_json::json!({}),
        };

        assert_eq!(
            apply_cluster_settings_mutation(&persisted_state, &request),
            Err(CLUSTER_SETTINGS_UNSUPPORTED_PARAMETER_BUCKET)
        );
    }
}
