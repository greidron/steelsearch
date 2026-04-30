use serde::Deserialize;
use std::collections::BTreeSet;

#[derive(Debug, Deserialize)]
struct FailureInjectionLedger {
    phase: String,
    profile: String,
    cases: Vec<FailureCase>,
}

#[derive(Debug, Deserialize)]
struct FailureCase {
    name: String,
    expected_error_class: String,
    evidence: String,
    reason: String,
}

#[test]
fn interop_failure_injection_ledger_covers_remote_unavailable_and_transport_unwrap() {
    let ledger: FailureInjectionLedger = serde_json::from_str(include_str!(
        "../../../tools/fixtures/interop-failure-injection.json"
    ))
    .unwrap();

    assert_eq!(ledger.phase, "Phase B");
    assert_eq!(ledger.profile, "interop-baseline");

    let mut seen = BTreeSet::new();
    for case in &ledger.cases {
        assert!(
            matches!(
                case.expected_error_class.as_str(),
                "DiffBaseMismatch"
                    | "GateDisabled"
                    | "Io"
                    | "MissingStartedShard"
                    | "RemoteTransportException"
                    | "UnsupportedRequest"
                    | "UnsupportedNamedWriteable"
            ),
            "unexpected error class for {}",
            case.name
        );
        assert!(!case.evidence.is_empty(), "missing evidence for {}", case.name);
        assert!(!case.reason.is_empty(), "missing reason for {}", case.name);
        assert!(seen.insert(case.name.clone()), "duplicate case {}", case.name);
    }

    assert!(seen.contains("stale_cluster_state_base"));
    assert!(seen.contains("remote_node_unavailable"));
    assert!(seen.contains("search_routing_hole"));
    assert!(seen.contains("custom_metadata_reject"));
    assert!(seen.contains("remote_transport_exception_unwrap"));
    assert!(seen.contains("write_forwarding_gate_disabled"));
    assert!(seen.contains("unsupported_write_action"));
}
