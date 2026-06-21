use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_transport::action::{
    build_cluster_health_request_message, build_cluster_health_response_message,
    read_cluster_health_request_message, read_cluster_health_response_message,
    ClusterHealthRequestWire, ClusterHealthResponseWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 300_000;

fn main() {
    let request = ClusterHealthRequestWire::default();
    let response = ClusterHealthResponseWire {
        active_primary_shards: 8,
        active_shards: 8,
        unassigned_shards: 0,
        active_shards_percent: 100.0,
        number_of_pending_tasks: 1,
        ..ClusterHealthResponseWire::green("bench-cluster".to_string())
    };

    let request_encode = measure("cluster_health_request_encode", ITERATIONS, || {
        let frame = build_cluster_health_request_message(
            11,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&request),
        )
        .expect("cluster health request encode should succeed");
        black_box(frame);
    });
    let response_encode = measure("cluster_health_response_encode", ITERATIONS, || {
        let frame = build_cluster_health_response_message(
            11,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&response),
        )
        .expect("cluster health response encode should succeed");
        black_box(frame);
    });

    let request_frame =
        build_cluster_health_request_message(11, OPENSEARCH_3_7_0_TRANSPORT, &request)
            .expect("cluster health request encode should succeed");
    let response_frame =
        build_cluster_health_response_message(11, OPENSEARCH_3_7_0_TRANSPORT, &response)
            .expect("cluster health response encode should succeed");

    let request_decode = measure("cluster_health_request_decode", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_cluster_health_request_message(black_box(&message))
            .expect("cluster health request decode");
        black_box(decoded);
    });
    let response_decode = measure("cluster_health_response_decode", ITERATIONS, || {
        let mut frame = black_box(response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_cluster_health_response_message(black_box(&message))
            .expect("cluster health response decode");
        black_box(decoded);
    });

    let combined_ops_per_second = request_encode
        .ops_per_second
        .min(response_encode.ops_per_second)
        .min(request_decode.ops_per_second)
        .min(response_decode.ops_per_second);
    println!("cluster_health_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}");
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
