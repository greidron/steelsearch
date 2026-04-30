use serde::Deserialize;
use std::collections::BTreeSet;

#[derive(Debug, Deserialize)]
struct Inventory {
    phase: String,
    profile: String,
    actions: Vec<Action>,
}

#[derive(Debug, Deserialize)]
struct Action {
    surface: String,
    kind: String,
    family: String,
    backing: String,
    disposition: String,
    reason: String,
}

#[test]
fn interop_read_action_inventory_uses_only_supported_phase_b_dispositions() {
    let inventory: Inventory = serde_json::from_str(include_str!(
        "../../../tools/fixtures/interop-read-action-inventory.json"
    ))
    .unwrap();

    assert_eq!(inventory.phase, "Phase B");
    assert_eq!(inventory.profile, "interop-baseline");
    assert!(!inventory.actions.is_empty());

    let mut seen_surfaces = BTreeSet::new();
    let mut seen_dispositions = BTreeSet::new();

    for action in &inventory.actions {
        assert!(
            matches!(action.kind.as_str(), "rest" | "transport"),
            "unexpected kind for {}",
            action.surface
        );
        assert!(
            matches!(
                action.disposition.as_str(),
                "implemented" | "rejected" | "phase_c"
            ),
            "unexpected disposition for {}",
            action.surface
        );
        assert!(!action.family.is_empty(), "family missing for {}", action.surface);
        assert!(!action.backing.is_empty(), "backing missing for {}", action.surface);
        assert!(!action.reason.is_empty(), "reason missing for {}", action.surface);
        assert!(
            seen_surfaces.insert(action.surface.clone()),
            "duplicate surface {}",
            action.surface
        );
        seen_dispositions.insert(action.disposition.clone());
    }

    for required_surface in [
        "GET /_cluster/health",
        "cluster:monitor/health",
        "GET /_cluster/state",
        "cluster:monitor/state",
        "GET /_cluster/pending_tasks",
        "cluster:monitor/task",
        "GET /_tasks",
        "cluster:monitor/tasks/lists",
        "GET /_nodes/stats",
        "cluster:monitor/nodes/stats",
    ] {
        assert!(
            seen_surfaces.contains(required_surface),
            "required surface missing: {required_surface}"
        );
    }

    assert!(seen_dispositions.contains("implemented"));
    assert!(seen_dispositions.contains("rejected"));
    assert!(seen_dispositions.contains("phase_c"));
}
