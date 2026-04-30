use serde::Deserialize;
use std::collections::BTreeSet;

#[derive(Debug, Deserialize)]
struct PolicyFixture {
    phase: String,
    profile: String,
    accepted_query_families: Vec<PolicyRow>,
    accepted_request_options: Vec<String>,
    rejected_query_families: Vec<PolicyRow>,
}

#[derive(Debug, Deserialize)]
struct PolicyRow {
    family: String,
    policy: String,
    reason: String,
}

#[test]
fn interop_search_forwarding_policy_fixture_stays_bounded_and_explicit() {
    let fixture: PolicyFixture = serde_json::from_str(include_str!(
        "../../../tools/fixtures/interop-search-forwarding-policy.json"
    ))
    .unwrap();

    assert_eq!(fixture.phase, "Phase B");
    assert_eq!(fixture.profile, "interop-baseline");

    let mut accepted = BTreeSet::new();
    for row in &fixture.accepted_query_families {
        assert_eq!(row.policy, "accepted");
        assert!(!row.reason.is_empty(), "accepted family missing reason: {}", row.family);
        assert!(accepted.insert(row.family.clone()), "duplicate accepted family {}", row.family);
    }

    let mut rejected = BTreeSet::new();
    for row in &fixture.rejected_query_families {
        assert_eq!(row.policy, "rejected");
        assert!(!row.reason.is_empty(), "rejected family missing reason: {}", row.family);
        assert!(rejected.insert(row.family.clone()), "duplicate rejected family {}", row.family);
    }

    for required in ["match_all", "term", "range", "bool.filter"] {
        assert!(accepted.contains(required), "missing accepted family {required}");
    }
    for required in ["scroll", "pit", "knn", "hybrid", "aggregations"] {
        assert!(rejected.contains(required), "missing rejected family {required}");
    }
    for required in ["sort", "from", "size", "track_total_hits"] {
        assert!(
            fixture.accepted_request_options.iter().any(|option| option == required),
            "missing accepted request option {required}"
        );
    }
}
