use serde::Deserialize;
use std::collections::BTreeSet;

#[derive(Debug, Deserialize)]
struct RejectLedger {
    phase: String,
    profile: String,
    entries: Vec<RejectEntry>,
}

#[derive(Debug, Deserialize)]
struct RejectEntry {
    kind: String,
    disposition: String,
    evidence: String,
    reason: String,
}

#[test]
fn interop_reject_ledger_covers_unknown_action_named_writeable_and_plugin_payload() {
    let ledger: RejectLedger = serde_json::from_str(include_str!(
        "../../../tools/fixtures/interop-reject-ledger.json"
    ))
    .unwrap();

    assert_eq!(ledger.phase, "Phase B");
    assert_eq!(ledger.profile, "interop-baseline");

    let mut seen = BTreeSet::new();
    for entry in &ledger.entries {
        assert_eq!(entry.disposition, "rejected", "{}", entry.kind);
        assert!(!entry.evidence.is_empty(), "missing evidence for {}", entry.kind);
        assert!(!entry.reason.is_empty(), "missing reason for {}", entry.kind);
        assert!(seen.insert(entry.kind.clone()), "duplicate reject kind {}", entry.kind);
    }

    assert!(seen.contains("unknown_transport_action"));
    assert!(seen.contains("unknown_named_writeable"));
    assert!(seen.contains("unsupported_plugin_payload"));
}
