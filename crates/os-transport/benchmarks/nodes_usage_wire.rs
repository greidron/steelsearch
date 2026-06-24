use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_transport::action::{
    build_nodes_usage_request_message, build_nodes_usage_response_message,
    read_nodes_usage_request_message, read_nodes_usage_response_message, NodeUsageWire,
    NodesUsageRequestWire, NodesUsageResponseWire, OpenSearchDiscoveryNodeRoleWire,
    OpenSearchDiscoveryNodeWire, OpenSearchTransportAddressWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use std::collections::BTreeMap;
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 400_000;

fn main() {
    let request = NodesUsageRequestWire::default();
    let response = NodesUsageResponseWire::default_local(
        "steelsearch-dev".to_string(),
        NodeUsageWire::no_telemetry(
            OpenSearchDiscoveryNodeWire {
                name: "steel-node".to_string(),
                id: "steel-node-id".to_string(),
                ephemeral_id: "steel-node-ephemeral".to_string(),
                host_name: "127.0.0.1".to_string(),
                host_address: "127.0.0.1".to_string(),
                transport_address: OpenSearchTransportAddressWire {
                    ip: "127.0.0.1".parse().expect("valid ip"),
                    host: "127.0.0.1".to_string(),
                    port: 9300,
                },
                attributes: BTreeMap::new(),
                roles: vec![
                    OpenSearchDiscoveryNodeRoleWire {
                        name: "cluster_manager".to_string(),
                        abbreviation: "m".to_string(),
                        can_contain_data: false,
                    },
                    OpenSearchDiscoveryNodeRoleWire {
                        name: "data".to_string(),
                        abbreviation: "d".to_string(),
                        can_contain_data: true,
                    },
                ],
                version: OPENSEARCH_3_7_0_TRANSPORT,
            },
            1_772_000_000_000,
        ),
    );

    let request_encode = measure("nodes_usage_request_encode", ITERATIONS, || {
        let frame =
            build_nodes_usage_request_message(20, OPENSEARCH_3_7_0_TRANSPORT, black_box(&request))
                .expect("nodes usage request encode should succeed");
        black_box(frame);
    });

    let request_frame = build_nodes_usage_request_message(20, OPENSEARCH_3_7_0_TRANSPORT, &request)
        .expect("nodes usage request encode should succeed");

    let request_decode = measure("nodes_usage_request_decode", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_nodes_usage_request_message(black_box(&message))
            .expect("nodes usage request decode");
        black_box(decoded);
    });

    let request_validate = measure("nodes_usage_request_validate", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_nodes_usage_request_message(black_box(&message))
            .expect("nodes usage request decode");
        decoded
            .validate_supported_subset()
            .expect("nodes usage request should validate");
        black_box(decoded);
    });

    let response_encode = measure("nodes_usage_response_encode", ITERATIONS, || {
        let frame =
            build_nodes_usage_response_message(20, OPENSEARCH_3_7_0_TRANSPORT, black_box(&response))
                .expect("nodes usage response encode should succeed");
        black_box(frame);
    });

    let response_frame =
        build_nodes_usage_response_message(20, OPENSEARCH_3_7_0_TRANSPORT, &response)
            .expect("nodes usage response encode should succeed");

    let response_decode = measure("nodes_usage_response_decode", ITERATIONS, || {
        let mut frame = black_box(response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_nodes_usage_response_message(black_box(&message))
            .expect("nodes usage response decode");
        black_box(decoded);
    });

    let combined_ops_per_second = request_encode
        .ops_per_second
        .min(request_decode.ops_per_second)
        .min(request_validate.ops_per_second)
        .min(response_encode.ops_per_second)
        .min(response_decode.ops_per_second);
    println!("nodes_usage_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}");
}

#[derive(Clone, Copy)]
struct Measurement {
    ops_per_second: f64,
}

fn measure(name: &str, iterations: usize, mut op: impl FnMut()) -> Measurement {
    let started = Instant::now();
    for _ in 0..iterations {
        op();
    }
    let elapsed = started.elapsed();
    let seconds = elapsed.as_secs_f64();
    let ops_per_second = iterations as f64 / seconds;
    let nanos_per_op = elapsed.as_nanos() as f64 / iterations as f64;
    println!(
        "{name} iterations={iterations} elapsed_ms={:.3} ops_per_second={ops_per_second:.2} nanos_per_op={nanos_per_op:.2}",
        seconds * 1000.0
    );
    Measurement { ops_per_second }
}

fn decode_message(frame: &mut bytes::BytesMut) -> os_transport::TransportMessage {
    match decode_frame(frame)
        .expect("frame decode should succeed")
        .expect("frame should contain message")
    {
        DecodedFrame::Message(message) => message,
        DecodedFrame::Ping => panic!("expected message frame"),
    }
}
