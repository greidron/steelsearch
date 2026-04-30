use os_core::{
    OPENSEARCH_3_7_0_MIN_COMPAT_TRANSPORT, OPENSEARCH_3_7_0_TRANSPORT,
    OPENSEARCH_DISCOVERY_NODE_STREAM_ADDRESS,
};
use os_transport::handshake::{TCP_HANDSHAKE_ACTION, TRANSPORT_HANDSHAKE_ACTION};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct JoinAdmissionFixture {
    phase: String,
    profile: String,
    source_target: SourceTarget,
    join_handshake: JoinHandshake,
    discovery_node_advertisement: DiscoveryNodeAdvertisement,
    policy: JoinPolicy,
}

#[derive(Debug, Deserialize)]
struct SourceTarget {
    family: String,
    product_version: String,
    source_commit: String,
}

#[derive(Debug, Deserialize)]
struct JoinHandshake {
    tcp_handshake_action: String,
    transport_handshake_action: String,
    payload_transport_version_ids: Vec<i32>,
    minimum_compatible_transport_version_id: i32,
    discovery_node_stream_address_gate: i32,
}

#[derive(Debug, Deserialize)]
struct DiscoveryNodeAdvertisement {
    required_identity_fields: Vec<String>,
    stream_address_behavior: String,
    advertised_roles: Vec<AdvertisedRole>,
    required_attributes: Vec<String>,
    observed_optional_attributes: Vec<String>,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
struct AdvertisedRole {
    name: String,
    abbreviation: String,
    can_contain_data: bool,
}

#[derive(Debug, Deserialize)]
struct JoinPolicy {
    join_mode: String,
    unknown_or_incompatible_join_behavior: String,
}

#[test]
fn mixed_cluster_join_admission_fixture_matches_current_join_contract() {
    let fixture: JoinAdmissionFixture = serde_json::from_str(include_str!(
        "../../../tools/fixtures/mixed-cluster-join-admission.json"
    ))
    .expect("mixed-cluster join admission fixture should deserialize");

    assert_eq!(fixture.phase, "Phase C");
    assert_eq!(fixture.profile, "mixed-cluster-join");
    assert_eq!(fixture.source_target.family, "Java OpenSearch");
    assert_eq!(fixture.source_target.product_version, "3.7.0");
    assert_eq!(
        fixture.source_target.source_commit,
        "f991609d190dfd91c8a09902053a7bbfe0c27b3e"
    );

    assert_eq!(fixture.join_handshake.tcp_handshake_action, TCP_HANDSHAKE_ACTION);
    assert_eq!(
        fixture.join_handshake.transport_handshake_action,
        TRANSPORT_HANDSHAKE_ACTION
    );
    assert_eq!(
        fixture.join_handshake.payload_transport_version_ids,
        vec![OPENSEARCH_3_7_0_TRANSPORT.id()]
    );
    assert_eq!(
        fixture.join_handshake.minimum_compatible_transport_version_id,
        OPENSEARCH_3_7_0_MIN_COMPAT_TRANSPORT.id()
    );
    assert_eq!(
        fixture.join_handshake.discovery_node_stream_address_gate,
        OPENSEARCH_DISCOVERY_NODE_STREAM_ADDRESS.id()
    );

    assert_eq!(
        fixture.discovery_node_advertisement.required_identity_fields,
        vec![
            "name",
            "id",
            "ephemeral_id",
            "host_name",
            "host_address",
            "address",
            "attributes",
            "roles",
            "version",
        ]
    );
    assert_eq!(
        fixture.discovery_node_advertisement.stream_address_behavior,
        "optional_on_or_after_gate"
    );
    assert_eq!(
        fixture.discovery_node_advertisement.advertised_roles,
        vec![
            AdvertisedRole {
                name: "cluster_manager".to_string(),
                abbreviation: "m".to_string(),
                can_contain_data: false,
            },
            AdvertisedRole {
                name: "data".to_string(),
                abbreviation: "d".to_string(),
                can_contain_data: true,
            },
            AdvertisedRole {
                name: "ingest".to_string(),
                abbreviation: "i".to_string(),
                can_contain_data: false,
            },
            AdvertisedRole {
                name: "remote_cluster_client".to_string(),
                abbreviation: "r".to_string(),
                can_contain_data: false,
            },
        ]
    );
    assert_eq!(
        fixture.discovery_node_advertisement.required_attributes,
        vec!["shard_indexing_pressure_enabled"]
    );
    assert_eq!(
        fixture
            .discovery_node_advertisement
            .observed_optional_attributes,
        vec!["testattr"]
    );

    assert_eq!(fixture.policy.join_mode, "same_cluster_peer_node");
    assert_eq!(
        fixture.policy.unknown_or_incompatible_join_behavior,
        "fail_closed"
    );
}
