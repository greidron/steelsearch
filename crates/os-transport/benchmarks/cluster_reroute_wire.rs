use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_transport::action::{
    build_cluster_reroute_request_message, build_cluster_reroute_response_message,
    read_cluster_reroute_request_message, read_cluster_reroute_response_message,
    ClusterRerouteAllocationCommandWire, ClusterRerouteRequestWire, ClusterRerouteResponseWire,
    ClusterStateResponseWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use std::collections::BTreeMap;
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 400_000;

fn main() {
    let request = ClusterRerouteRequestWire {
        dry_run: true,
        explain: true,
        retry_failed: true,
        ..ClusterRerouteRequestWire::default()
    };

    let request_encode = measure("cluster_reroute_request_encode", ITERATIONS, || {
        let frame = build_cluster_reroute_request_message(
            41,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&request),
        )
        .expect("cluster reroute request encode should succeed");
        black_box(frame);
    });

    let request_frame =
        build_cluster_reroute_request_message(41, OPENSEARCH_3_7_0_TRANSPORT, &request)
            .expect("cluster reroute request encode should succeed");

    let request_decode = measure("cluster_reroute_request_decode", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_cluster_reroute_request_message(black_box(&message))
            .expect("cluster reroute request decode");
        black_box(decoded);
    });

    let request_validate = measure("cluster_reroute_request_validate", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_cluster_reroute_request_message(black_box(&message))
            .expect("cluster reroute request decode");
        decoded
            .validate_supported_execution_subset()
            .expect("cluster reroute request should validate");
        black_box(decoded);
    });

    let move_request = ClusterRerouteRequestWire {
        commands_count: 1,
        commands: vec![ClusterRerouteAllocationCommandWire::Move {
            index: "logs-reroute".to_string(),
            shard_id: 0,
            from_node: "source-node".to_string(),
            to_node: "target-node".to_string(),
        }],
        ..ClusterRerouteRequestWire::default()
    };
    let move_request_encode = measure("cluster_reroute_move_request_encode", ITERATIONS, || {
        let frame = build_cluster_reroute_request_message(
            42,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&move_request),
        )
        .expect("cluster reroute move request encode should succeed");
        black_box(frame);
    });
    let move_request_frame =
        build_cluster_reroute_request_message(42, OPENSEARCH_3_7_0_TRANSPORT, &move_request)
            .expect("cluster reroute move request encode should succeed");
    let move_request_decode = measure("cluster_reroute_move_request_decode", ITERATIONS, || {
        let mut frame = black_box(move_request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_cluster_reroute_request_message(black_box(&message))
            .expect("cluster reroute move request decode");
        black_box(decoded);
    });
    let move_request_validate =
        measure("cluster_reroute_move_request_validate", ITERATIONS, || {
            let mut frame = black_box(move_request_frame.clone());
            let message = decode_message(&mut frame);
            let decoded = read_cluster_reroute_request_message(black_box(&message))
                .expect("cluster reroute move request decode");
            decoded
                .validate_supported_execution_subset()
                .expect("cluster reroute move request should validate");
            black_box(decoded);
        });

    let response = ClusterRerouteResponseWire::empty_explanations(
        true,
        ClusterStateResponseWire {
            cluster_name: "steelsearch".to_string(),
            cluster_uuid: "cluster-uuid".to_string(),
            state_uuid: "state-uuid".to_string(),
            version: 1,
            sections: BTreeMap::from([(
                "routing_table".to_string(),
                serde_json::json!({ "indices": {} }),
            )]),
        },
    );
    let response_encode = measure("cluster_reroute_response_encode", ITERATIONS, || {
        let frame = build_cluster_reroute_response_message(
            41,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&response),
        )
        .expect("cluster reroute response encode should succeed");
        black_box(frame);
    });
    let response_frame =
        build_cluster_reroute_response_message(41, OPENSEARCH_3_7_0_TRANSPORT, &response)
            .expect("cluster reroute response encode should succeed");
    let response_decode = measure("cluster_reroute_response_decode", ITERATIONS, || {
        let mut frame = black_box(response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_cluster_reroute_response_message(black_box(&message))
            .expect("cluster reroute response decode");
        black_box(decoded);
    });

    let combined_ops_per_second = request_encode
        .ops_per_second
        .min(request_decode.ops_per_second)
        .min(request_validate.ops_per_second)
        .min(move_request_encode.ops_per_second)
        .min(move_request_decode.ops_per_second)
        .min(move_request_validate.ops_per_second)
        .min(response_encode.ops_per_second)
        .min(response_decode.ops_per_second);
    println!("cluster_reroute_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}");
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
