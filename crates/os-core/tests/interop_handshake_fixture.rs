use os_core::{
    OPENSEARCH_3_7_0, OPENSEARCH_3_7_0_MIN_COMPAT_TRANSPORT, OPENSEARCH_3_7_0_TRANSPORT,
    OPENSEARCH_DISCOVERY_NODE_STREAM_ADDRESS,
};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct HandshakeFixture {
    supported_version_range: SupportedVersionRange,
}

#[derive(Debug, Deserialize)]
struct SupportedVersionRange {
    product_version_ids: Vec<i32>,
    transport_version_ids: Vec<i32>,
    minimum_compatible_transport_version_id: i32,
    discovery_node_stream_address_gate: i32,
}

#[test]
fn interop_handshake_fixture_matches_current_version_constants() {
    let fixture: HandshakeFixture = serde_json::from_str(include_str!(
        "../../../tools/fixtures/interop-handshake-compat.json"
    ))
    .expect("interop handshake fixture should deserialize");

    assert_eq!(fixture.supported_version_range.product_version_ids, vec![OPENSEARCH_3_7_0.id()]);
    assert_eq!(
        fixture.supported_version_range.transport_version_ids,
        vec![OPENSEARCH_3_7_0_TRANSPORT.id()]
    );
    assert_eq!(
        fixture
            .supported_version_range
            .minimum_compatible_transport_version_id,
        OPENSEARCH_3_7_0_MIN_COMPAT_TRANSPORT.id()
    );
    assert_eq!(
        fixture
            .supported_version_range
            .discovery_node_stream_address_gate,
        OPENSEARCH_DISCOVERY_NODE_STREAM_ADDRESS.id()
    );
}
