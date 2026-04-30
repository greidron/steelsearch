use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct AllocationAdmissionFixture {
    phase: String,
    profile: String,
    allocation_admission_policy: AllocationAdmissionPolicy,
}

#[derive(Debug, Deserialize)]
struct AllocationAdmissionPolicy {
    validated_index_family_patterns: Vec<String>,
    required_node_roles: Vec<String>,
    admitted_shard_states: Vec<String>,
    search_target_states: Vec<String>,
    admitted_recovery_sources: Vec<String>,
    disallowed_routing_flags: Vec<String>,
    started_shard_requires_allocation_id: bool,
    ownership_fail_closed_on_missing_allocation_id: bool,
}

#[test]
fn mixed_cluster_allocation_admission_fixture_stays_explicit_and_bounded() {
    let fixture: AllocationAdmissionFixture = serde_json::from_str(include_str!(
        "../../../tools/fixtures/mixed-cluster-allocation-admission.json"
    ))
    .expect("mixed-cluster allocation admission fixture should deserialize");

    assert_eq!(fixture.phase, "Phase C");
    assert_eq!(fixture.profile, "mixed-cluster-allocation");
    assert_eq!(
        fixture.allocation_admission_policy.validated_index_family_patterns,
        vec!["logs-phase-c-*"]
    );
    assert_eq!(
        fixture.allocation_admission_policy.required_node_roles,
        vec!["data"]
    );
    assert_eq!(
        fixture.allocation_admission_policy.admitted_shard_states,
        vec!["Initializing", "Started"]
    );
    assert_eq!(
        fixture.allocation_admission_policy.search_target_states,
        vec!["Started"]
    );
    assert_eq!(
        fixture.allocation_admission_policy.admitted_recovery_sources,
        vec!["EmptyStore"]
    );
    assert_eq!(
        fixture.allocation_admission_policy.disallowed_routing_flags,
        vec!["search_only"]
    );
    assert!(fixture
        .allocation_admission_policy
        .started_shard_requires_allocation_id);
    assert!(fixture
        .allocation_admission_policy
        .ownership_fail_closed_on_missing_allocation_id);
}
