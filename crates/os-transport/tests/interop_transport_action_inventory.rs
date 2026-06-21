use os_transport::action::{
    classify_opensearch_transport_action, OpenSearchTransportActionDisposition,
    OPENSEARCH_PRIORITY_TRANSPORT_ACTIONS, SOURCE_DERIVED_CLUSTER_ACTIONS,
};
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Deserialize)]
struct Inventory {
    phase: String,
    profile: String,
    scope: String,
    actions: Vec<Action>,
}

#[derive(Debug, Deserialize)]
struct Action {
    action_name: String,
    action_type: String,
    transport_action: String,
    request_wire_type: String,
    response_wire_type: String,
    disposition: String,
    reason: String,
}

#[test]
fn interop_transport_action_inventory_covers_all_source_derived_cluster_actions() {
    let inventory: Inventory = serde_json::from_str(include_str!(
        "../../../tools/fixtures/interop-transport-action-inventory.json"
    ))
    .unwrap();

    assert_eq!(inventory.phase, "Phase B");
    assert_eq!(inventory.profile, "interop-baseline");
    assert_eq!(inventory.scope, "accepted-interop-transport-actions");

    let mut seen_actions = BTreeSet::new();
    let mut by_action = BTreeMap::new();
    for action in inventory.actions {
        assert!(
            matches!(
                action.disposition.as_str(),
                "implemented" | "rejected" | "phase_c"
            ),
            "unexpected disposition for {}",
            action.action_name
        );
        assert!(
            !action.reason.is_empty(),
            "reason missing for {}",
            action.action_name
        );
        assert!(
            seen_actions.insert(action.action_name.clone()),
            "duplicate action {}",
            action.action_name
        );
        by_action.insert(action.action_name.clone(), action);
    }

    let accepted_priority_actions = OPENSEARCH_PRIORITY_TRANSPORT_ACTIONS
        .iter()
        .filter(|spec| {
            classify_opensearch_transport_action(spec.action_name).disposition
                != OpenSearchTransportActionDisposition::Missing
        })
        .count();
    assert_eq!(
        by_action.len(),
        SOURCE_DERIVED_CLUSTER_ACTIONS.len() + accepted_priority_actions
    );
    for spec in SOURCE_DERIVED_CLUSTER_ACTIONS {
        let action = by_action
            .get(spec.action_name)
            .unwrap_or_else(|| panic!("missing ledger entry for {}", spec.action_name));
        assert_eq!(action.action_type, spec.action_type, "{}", spec.action_name);
        assert_eq!(
            action.transport_action, spec.transport_action,
            "{}",
            spec.action_name
        );
        assert_eq!(
            action.request_wire_type, spec.request_wire_type,
            "{}",
            spec.action_name
        );
        assert_eq!(
            action.response_wire_type, spec.response_wire_type,
            "{}",
            spec.action_name
        );
    }
    for spec in OPENSEARCH_PRIORITY_TRANSPORT_ACTIONS {
        if classify_opensearch_transport_action(spec.action_name).disposition
            != OpenSearchTransportActionDisposition::Missing
        {
            let action = by_action.get(spec.action_name).unwrap_or_else(|| {
                panic!(
                    "missing {} transport action inventory row",
                    spec.action_name
                )
            });
            assert_eq!(action.action_type, spec.action_type, "{}", spec.action_name);
            assert_eq!(
                action.transport_action, spec.transport_action,
                "{}",
                spec.action_name
            );
            assert_eq!(
                action.request_wire_type, spec.request_wire_type,
                "{}",
                spec.action_name
            );
            assert_eq!(
                action.response_wire_type, spec.response_wire_type,
                "{}",
                spec.action_name
            );
        }
    }

    assert_eq!(
        by_action["cluster:monitor/state"].disposition,
        "implemented"
    );
    assert_eq!(
        by_action["cluster:admin/settings/update"].disposition,
        "rejected"
    );
    assert_eq!(by_action["cluster:monitor/task"].disposition, "implemented");
    assert_eq!(
        by_action["indices:admin/refresh"].disposition,
        "implemented"
    );
    assert_eq!(
        by_action["indices:data/read/get"].disposition,
        "implemented"
    );
}

#[test]
fn interop_transport_action_inventory_matches_dispatch_classifier() {
    let inventory: Inventory = serde_json::from_str(include_str!(
        "../../../tools/fixtures/interop-transport-action-inventory.json"
    ))
    .unwrap();

    for action in inventory.actions {
        let expected = match action.disposition.as_str() {
            "implemented" => OpenSearchTransportActionDisposition::Implemented,
            "rejected" => OpenSearchTransportActionDisposition::Rejected,
            "phase_c" => OpenSearchTransportActionDisposition::Missing,
            other => panic!("unexpected disposition {other} for {}", action.action_name),
        };
        assert_eq!(
            classify_opensearch_transport_action(&action.action_name).disposition,
            expected,
            "{}",
            action.action_name
        );
    }
}
