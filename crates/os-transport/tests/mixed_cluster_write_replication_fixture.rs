use os_transport::action::STEELSEARCH_REPLICA_OPERATION_ACTION_NAME;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct MixedClusterWriteReplicationFixture {
    phase: String,
    profile: String,
    replicated_action_family: ReplicatedActionFamily,
}

#[derive(Debug, Deserialize)]
struct ReplicatedActionFamily {
    user_facing_write_families: Vec<String>,
    replica_wire_operation_kinds: Vec<String>,
    update_resolution_policy: String,
    required_request_fields: Vec<String>,
    required_response_fields: Vec<String>,
}

#[test]
fn mixed_cluster_write_replication_fixture_stays_explicit_and_bounded() {
    let fixture: MixedClusterWriteReplicationFixture = serde_json::from_str(include_str!(
        "../../../tools/fixtures/mixed-cluster-write-replication.json"
    ))
    .expect("mixed-cluster write replication fixture should deserialize");

    assert_eq!(fixture.phase, "Phase C");
    assert_eq!(fixture.profile, "mixed-cluster-write-replication");
    assert_eq!(
        fixture.replicated_action_family.user_facing_write_families,
        vec!["index", "delete", "update"]
    );
    assert_eq!(
        fixture.replicated_action_family.replica_wire_operation_kinds,
        vec!["index", "delete", "noop"]
    );
    assert_eq!(
        fixture.replicated_action_family.update_resolution_policy,
        "primary_must_resolve_update_to_replica index|delete|noop before transport"
    );
    assert_eq!(
        fixture.replicated_action_family.required_request_fields,
        vec![
            "index",
            "shard_id",
            "target_node",
            "primary_node",
            "allocation_id",
            "seq_no",
            "primary_term",
            "version",
            "global_checkpoint",
            "local_checkpoint",
            "retention_leases",
            "operation",
        ]
    );
    assert_eq!(
        fixture.replicated_action_family.required_response_fields,
        vec![
            "index",
            "shard_id",
            "target_node",
            "seq_no",
            "primary_term",
            "version",
            "global_checkpoint",
            "applied",
            "result",
        ]
    );
    assert_eq!(
        STEELSEARCH_REPLICA_OPERATION_ACTION_NAME,
        "steelsearch:internal/replication/replica_operation"
    );
}
