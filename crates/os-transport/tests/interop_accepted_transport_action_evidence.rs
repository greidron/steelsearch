use os_transport::action::{
    classify_opensearch_transport_action, OpenSearchTransportActionDisposition,
    OPENSEARCH_PRIORITY_TRANSPORT_ACTIONS, SOURCE_DERIVED_CLUSTER_ACTIONS,
};
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;

#[derive(Debug, Deserialize)]
struct ActionInventory {
    actions: Vec<InventoryAction>,
}

#[derive(Debug, Deserialize)]
struct InventoryAction {
    action_name: String,
    disposition: String,
}

#[derive(Debug, Deserialize)]
struct EvidenceLedger {
    phase: String,
    profile: String,
    actions: Vec<EvidenceAction>,
}

#[derive(Debug, Deserialize)]
struct EvidenceAction {
    action_name: String,
    disposition: String,
    evidence_kind: String,
    execution_scope: String,
    request_evidence: String,
    response_evidence: String,
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|path| path.parent())
        .expect("workspace root")
        .to_path_buf()
}

fn assert_evidence_symbol_exists(action_name: &str, field: &str, evidence: &str) {
    let Some((path, symbol)) = evidence.split_once("::") else {
        panic!("{action_name}: {field} evidence must use path::symbol form: {evidence}");
    };
    let source_path = repo_root().join(path);
    let source = std::fs::read_to_string(&source_path).unwrap_or_else(|error| {
        panic!(
            "{action_name}: {field} evidence source {} is not readable: {error}",
            source_path.display()
        )
    });
    assert!(
        source.contains(symbol),
        "{action_name}: {field} evidence symbol {symbol} missing from {}",
        source_path.display()
    );
}

#[test]
fn interop_accepted_transport_action_evidence_covers_every_implemented_action() {
    let inventory: ActionInventory = serde_json::from_str(include_str!(
        "../../../tools/fixtures/interop-transport-action-inventory.json"
    ))
    .unwrap();
    let ledger: EvidenceLedger = serde_json::from_str(include_str!(
        "../../../tools/fixtures/interop-accepted-transport-action-evidence.json"
    ))
    .unwrap();

    assert_eq!(ledger.phase, "Phase B");
    assert_eq!(ledger.profile, "interop-baseline");

    let implemented_actions: BTreeSet<_> = inventory
        .actions
        .into_iter()
        .filter(|action| action.disposition == "implemented")
        .map(|action| action.action_name)
        .collect();

    let mut seen = BTreeSet::new();
    let mut by_action = BTreeMap::new();
    for action in ledger.actions {
        assert_eq!(action.disposition, "implemented", "{}", action.action_name);
        assert_eq!(
            classify_opensearch_transport_action(&action.action_name).disposition,
            OpenSearchTransportActionDisposition::Implemented,
            "{}",
            action.action_name
        );
        assert!(
            matches!(
                action.evidence_kind.as_str(),
                "java_fixture" | "wire_round_trip" | "live_probe"
            ),
            "unexpected evidence kind for {}",
            action.action_name
        );
        assert!(
            matches!(
                action.execution_scope.as_str(),
                "bounded_local_subset"
                    | "fail_closed_or_empty_subset"
                    | "bounded_execution_boundary"
            ),
            "unexpected execution scope for {}: {}",
            action.action_name,
            action.execution_scope
        );
        assert!(
            action.execution_scope != "full_parity",
            "{}: accepted transport evidence must not claim full parity through the bounded interop ledger",
            action.action_name
        );
        assert!(
            !action.request_evidence.is_empty(),
            "missing request evidence for {}",
            action.action_name
        );
        assert!(
            !action.request_evidence.contains("rejected_action_frame"),
            "{}: implemented request evidence must describe an accepted action frame or explicit execution boundary, not a rejected action frame",
            action.action_name
        );
        assert_evidence_symbol_exists(
            &action.action_name,
            "request_evidence",
            &action.request_evidence,
        );
        if action.request_evidence.contains("execution_boundary") {
            assert_eq!(
                action.execution_scope, "bounded_execution_boundary",
                "{}: execution-boundary evidence must be scoped as bounded_execution_boundary",
                action.action_name
            );
        }
        assert!(
            !action.response_evidence.is_empty(),
            "missing response evidence for {}",
            action.action_name
        );
        assert_evidence_symbol_exists(
            &action.action_name,
            "response_evidence",
            &action.response_evidence,
        );
        assert!(
            seen.insert(action.action_name.clone()),
            "duplicate {}",
            action.action_name
        );
        by_action.insert(action.action_name.clone(), action);
    }

    for spec in SOURCE_DERIVED_CLUSTER_ACTIONS {
        if implemented_actions.contains(spec.action_name) {
            assert!(
                by_action.contains_key(spec.action_name),
                "missing evidence ledger entry for implemented action {}",
                spec.action_name
            );
        } else {
            assert!(
                !by_action.contains_key(spec.action_name),
                "non-implemented action {} must not appear in accepted evidence ledger",
                spec.action_name
            );
        }
    }
    for spec in OPENSEARCH_PRIORITY_TRANSPORT_ACTIONS {
        if implemented_actions.contains(spec.action_name) {
            assert!(
                by_action.contains_key(spec.action_name),
                "missing evidence ledger entry for implemented action {}",
                spec.action_name
            );
        }
    }

    assert_eq!(seen, implemented_actions);
}
