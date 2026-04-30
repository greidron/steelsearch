use serde::Deserialize;
use std::collections::BTreeSet;

#[derive(Debug, Deserialize)]
struct MixedClusterFailureLedger {
    phase: String,
    profile: String,
    cases: Vec<MixedClusterFailureCase>,
}

#[derive(Debug, Deserialize)]
struct MixedClusterFailureCase {
    name: String,
    expected_error_class: String,
    evidence: String,
    reason: String,
}

#[test]
fn mixed_cluster_failure_ledger_covers_publication_mismatch_routing_hole_and_stale_replica() {
    let ledger: MixedClusterFailureLedger = serde_json::from_str(include_str!(
        "../../../tools/fixtures/mixed-cluster-failure-ledger.json"
    ))
    .unwrap();

    assert_eq!(ledger.phase, "Phase C");
    assert_eq!(ledger.profile, "mixed-cluster-failure");

    let mut seen = BTreeSet::new();
    for case in &ledger.cases {
        assert!(
            matches!(
                case.expected_error_class.as_str(),
                "DiffBaseMismatch" | "MissingStartedShard" | "StaleSeqNo"
            ),
            "unexpected error class for {}",
            case.name
        );
        assert!(!case.evidence.is_empty(), "missing evidence for {}", case.name);
        assert!(!case.reason.is_empty(), "missing reason for {}", case.name);
        assert!(seen.insert(case.name.clone()), "duplicate case {}", case.name);
    }

    assert!(seen.contains("publication_mismatch"));
    assert!(seen.contains("routing_hole"));
    assert!(seen.contains("stale_replica"));
}
