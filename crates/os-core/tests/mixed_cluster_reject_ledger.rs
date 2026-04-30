use serde::Deserialize;
use std::collections::BTreeSet;

#[derive(Debug, Deserialize)]
struct MixedClusterRejectLedger {
    phase: String,
    profile: String,
    cases: Vec<MixedClusterRejectCase>,
}

#[derive(Debug, Deserialize)]
struct MixedClusterRejectCase {
    name: String,
    expected_error_class: String,
    evidence: String,
    reason: String,
}

#[test]
fn mixed_cluster_reject_ledger_covers_membership_publication_routing_recovery_and_replication() {
    let ledger: MixedClusterRejectLedger = serde_json::from_str(include_str!(
        "../../../tools/fixtures/mixed-cluster-reject-ledger.json"
    ))
    .unwrap();

    assert_eq!(ledger.phase, "Phase C");
    assert_eq!(ledger.profile, "mixed-cluster-reject-ledger");

    let mut seen = BTreeSet::new();
    for case in &ledger.cases {
        assert!(
            matches!(
                case.expected_error_class.as_str(),
                "DiffBaseMismatch"
                    | "InvalidStoreContract"
                    | "JoinAdmissionError"
                    | "MissingStartedShard"
                    | "RelocationInterrupted"
                    | "StaleSeqNo"
            ),
            "unexpected error class for {}",
            case.name
        );
        assert!(!case.evidence.is_empty(), "missing evidence for {}", case.name);
        assert!(!case.reason.is_empty(), "missing reason for {}", case.name);
        assert!(seen.insert(case.name.clone()), "duplicate case {}", case.name);
    }

    assert!(seen.contains("join_membership_reject"));
    assert!(seen.contains("publication_mismatch"));
    assert!(seen.contains("allocation_invalid_store_contract"));
    assert!(seen.contains("recovery_relocation_interrupted"));
    assert!(seen.contains("routing_hole"));
    assert!(seen.contains("stale_replica"));
}
