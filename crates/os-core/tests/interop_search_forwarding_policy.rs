use serde::Deserialize;
use serde_json::Value;
use std::collections::BTreeSet;

#[derive(Debug, Deserialize)]
struct PolicyFixture {
    phase: String,
    profile: String,
    accepted_query_families: Vec<PolicyRow>,
    accepted_request_options: Vec<String>,
    rejected_query_families: Vec<PolicyRow>,
    excluded_request_extensions: Vec<PolicyRow>,
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
        assert!(
            !row.reason.is_empty(),
            "accepted family missing reason: {}",
            row.family
        );
        assert!(
            accepted.insert(row.family.clone()),
            "duplicate accepted family {}",
            row.family
        );
    }

    let mut rejected = BTreeSet::new();
    for row in &fixture.rejected_query_families {
        assert_eq!(row.policy, "rejected");
        assert!(
            !row.reason.is_empty(),
            "rejected family missing reason: {}",
            row.family
        );
        assert!(
            rejected.insert(row.family.clone()),
            "duplicate rejected family {}",
            row.family
        );
    }

    for required in [
        "match_all",
        "term",
        "range",
        "bool.filter",
        "pit",
        "search_after",
        "nested",
        "geo_distance",
        "script_score",
        "function_score",
        "rescore",
        "collapse",
        "aggregations",
        "highlight",
        "suggest",
    ] {
        assert!(
            accepted.contains(required),
            "missing accepted family {required}"
        );
    }
    for required in ["scroll", "knn", "hybrid", "runtime_mappings"] {
        assert!(
            rejected.contains(required),
            "missing rejected family {required}"
        );
    }
    let mut excluded = BTreeSet::new();
    for row in &fixture.excluded_request_extensions {
        assert_eq!(row.policy, "excluded");
        assert!(
            !row.reason.is_empty(),
            "excluded extension missing reason: {}",
            row.family
        );
        assert!(
            excluded.insert(row.family.clone()),
            "duplicate excluded extension {}",
            row.family
        );
    }
    assert!(
        !rejected.contains("pit"),
        "pit must not remain rejected after lifecycle forwarding profile coverage"
    );
    assert!(
        !rejected.contains("search_after"),
        "search_after must not remain rejected after forwarding profile coverage"
    );
    assert!(
        !rejected.contains("nested"),
        "nested must not remain rejected after forwarding profile coverage"
    );
    assert!(
        !rejected.contains("geo_distance"),
        "geo_distance must not remain rejected after forwarding profile coverage"
    );
    assert!(
        !rejected.contains("script_score"),
        "script_score must not remain rejected after forwarding profile coverage"
    );
    assert!(
        !rejected.contains("function_score"),
        "function_score must not remain rejected after forwarding profile coverage"
    );
    assert!(
        !rejected.contains("rescore"),
        "rescore must not remain rejected after forwarding profile coverage"
    );
    assert!(
        !rejected.contains("collapse"),
        "collapse must not remain rejected after forwarding profile coverage"
    );
    assert!(
        !rejected.contains("aggregations"),
        "aggregations must not remain rejected after forwarding profile coverage"
    );
    assert!(
        !rejected.contains("highlight"),
        "highlight must not remain rejected after forwarding profile coverage"
    );
    assert!(
        !rejected.contains("suggest"),
        "suggest must not remain rejected after forwarding profile coverage"
    );
    for required in [
        "sort",
        "from",
        "size",
        "track_total_hits",
        "pit",
        "search_after",
    ] {
        assert!(
            fixture
                .accepted_request_options
                .iter()
                .any(|option| option == required),
            "missing accepted request option {required}"
        );
    }

    let forwarding_fixture: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/interop-search-forwarding.json"
    ))
    .unwrap();
    let policy_value: Value = serde_json::from_str(include_str!(
        "../../../tools/fixtures/interop-search-forwarding-policy.json"
    ))
    .unwrap();
    let rejected_rows = policy_value["rejected_query_families"]
        .as_array()
        .expect("rejected query families must be an array");
    for family in ["scroll", "knn", "hybrid"] {
        let row = rejected_rows
            .iter()
            .find(|row| row["family"] == family)
            .unwrap_or_else(|| panic!("missing rejected family {family}"));
        let evidence = row["blocking_evidence"]
            .as_array()
            .unwrap_or_else(|| panic!("rejected family {family} missing blocking evidence"));
        assert!(
            evidence
                .iter()
                .all(|item| item.as_str().map_or(false, |value| !value.is_empty())),
            "rejected family {family} has blank blocking evidence"
        );
        if family == "scroll" {
            assert!(
                evidence
                    .iter()
                    .any(|item| item.as_str().map_or(false, |value| {
                        value.contains("SearchResponse.java::writeTo")
                    })),
                "scroll rejection must name the OpenSearch SearchResponse source contract"
            );
            assert!(
                evidence
                    .iter()
                    .any(|item| item.as_str().map_or(false, |value| {
                        value.contains(
                            "opensearch_search_response_wire_round_trips_empty_hits_subset",
                        )
                    })),
                "scroll rejection must name the implemented empty SearchResponse wire subset"
            );
            assert!(
                evidence
                    .iter()
                    .any(|item| item.as_str().map_or(false, |value| {
                        value.contains(
                            "opensearch_search_response_wire_round_trips_basic_hit_subset",
                        )
                    })),
                "scroll rejection must name the implemented basic SearchHit wire subset"
            );
        }
    }
    let cases = forwarding_fixture["cases"]
        .as_array()
        .expect("interop search forwarding cases must be an array");
    assert!(
        cases
            .iter()
            .any(|case| case["name"] == "pit_lifecycle_search" && case["use_pit"] == true),
        "accepted pit policy requires an executable PIT lifecycle search forwarding profile case"
    );
    assert!(
        cases.iter().any(|case| {
            case["name"] == "pit_snapshot_after_mutation_search"
                && case["use_pit"] == true
                && case["mutate_after_pit"]
                    .as_array()
                    .is_some_and(|steps| steps.len() >= 2)
                && case["expected_ids"]
                    .as_array()
                    .is_some_and(|ids| ids.len() == 2)
        }),
        "accepted pit policy requires a PIT snapshot case that mutates documents after PIT open"
    );
    assert!(
        cases.iter().any(|case| {
            case["name"] == "search_after_search"
                && case["body"]["search_after"].as_array().is_some()
        }),
        "accepted search_after policy requires an executable search_after forwarding profile case"
    );
    assert!(
        cases.iter().any(|case| {
            case["name"] == "nested_tuple_search" && case["body"]["query"]["nested"].is_object()
        }),
        "accepted nested policy requires an executable nested forwarding profile case"
    );
    assert!(
        cases.iter().any(|case| {
            case["name"] == "geo_distance_search"
                && case["body"]["query"]["geo_distance"].is_object()
        }),
        "accepted geo_distance policy requires an executable geo_distance forwarding profile case"
    );
    assert!(
        cases.iter().any(|case| {
            case["name"] == "script_score_search"
                && case["body"]["query"]["script_score"].is_object()
        }),
        "accepted script_score policy requires an executable script_score forwarding profile case"
    );
    assert!(
        cases.iter().any(|case| {
            case["name"] == "function_score_search"
                && case["body"]["query"]["function_score"].is_object()
        }),
        "accepted function_score policy requires an executable function_score forwarding profile case"
    );
    assert!(
        cases.iter().any(|case| {
            case["name"] == "rescore_search" && case["body"]["rescore"].is_object()
        }),
        "accepted rescore policy requires an executable rescore forwarding profile case"
    );
    assert!(
        cases.iter().any(|case| {
            case["name"] == "collapse_search" && case["body"]["collapse"].is_object()
        }),
        "accepted collapse policy requires an executable collapse forwarding profile case"
    );
    assert!(
        cases.iter().any(|case| {
            case["name"] == "terms_aggregation_search"
                && case["body"]["aggs"].is_object()
                && case["expected_values"].is_object()
        }),
        "accepted aggregations policy requires an executable aggregation forwarding profile case"
    );
    assert!(
        cases.iter().any(|case| {
            case["name"] == "highlight_search"
                && case["body"]["highlight"].is_object()
                && case["expected_values"].is_object()
        }),
        "accepted highlight policy requires an executable highlight forwarding profile case"
    );
    assert!(
        cases.iter().any(|case| {
            case["name"] == "term_suggest_search"
                && case["body"]["suggest"].is_object()
                && case["expected_values"].is_object()
        }),
        "accepted suggest policy requires an executable suggest forwarding profile case"
    );
}
