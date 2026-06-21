use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_transport::action::{
    build_cluster_put_weighted_routing_request_message,
    read_cluster_put_weighted_routing_request_message, ClusterPutWeightedRoutingRequestWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use std::collections::BTreeMap;
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 400_000;

fn main() {
    let request = ClusterPutWeightedRoutingRequestWire {
        parent_task_node: "cluster-manager".to_string(),
        parent_task_id: Some(37),
        attribute_name: "zone".to_string(),
        weights: BTreeMap::from([("zone-a".to_string(), 1.0), ("zone-b".to_string(), 1.0)]),
        version: -1,
        ..ClusterPutWeightedRoutingRequestWire::default()
    };

    let request_encode = measure(
        "add_weighted_routing_reject_request_encode",
        ITERATIONS,
        || {
            let frame = build_cluster_put_weighted_routing_request_message(
                37,
                OPENSEARCH_3_7_0_TRANSPORT,
                black_box(&request),
            )
            .expect("add weighted routing request encode should succeed");
            black_box(frame);
        },
    );

    let request_frame = build_cluster_put_weighted_routing_request_message(
        37,
        OPENSEARCH_3_7_0_TRANSPORT,
        &request,
    )
    .expect("add weighted routing request encode should succeed");

    let request_decode = measure(
        "add_weighted_routing_reject_request_decode",
        ITERATIONS,
        || {
            let mut frame = black_box(request_frame.clone());
            let message = decode_message(&mut frame);
            let decoded = read_cluster_put_weighted_routing_request_message(black_box(&message))
                .expect("add weighted routing request decode");
            black_box(decoded);
        },
    );

    let reject_validate = measure("add_weighted_routing_reject_validation", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_cluster_put_weighted_routing_request_message(black_box(&message))
            .expect("add weighted routing request decode");
        let err = decoded
            .reject_unsupported_execution()
            .expect_err("add weighted routing execution should reject");
        black_box(err);
    });

    let combined_ops_per_second = request_encode
        .ops_per_second
        .min(request_decode.ops_per_second)
        .min(reject_validate.ops_per_second);
    println!(
        "add_weighted_routing_reject_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}"
    );
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
