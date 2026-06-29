use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_transport::action::{
    build_opensearch_can_match_response_message, read_opensearch_can_match_response_message,
    OpenSearchCanMatchResponseWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 400_000;

fn main() {
    let response = OpenSearchCanMatchResponseWire::new(true);

    let response_encode = measure("can_match_response_encode", ITERATIONS, || {
        let frame = build_opensearch_can_match_response_message(
            147,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&response),
        )
        .expect("can-match response encode should succeed");
        black_box(frame);
    });

    let response_frame =
        build_opensearch_can_match_response_message(147, OPENSEARCH_3_7_0_TRANSPORT, &response)
            .expect("can-match response encode should succeed");

    let response_decode = measure("can_match_response_decode", ITERATIONS, || {
        let mut frame = black_box(response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_can_match_response_message(black_box(&message))
            .expect("can-match response decode should succeed");
        black_box(decoded);
    });

    let combined_ops_per_second = response_encode
        .ops_per_second
        .min(response_decode.ops_per_second);
    println!("can_match_response_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}");
}

#[derive(Clone, Copy)]
struct Measurement {
    ops_per_second: f64,
}

fn measure(name: &str, iterations: usize, mut f: impl FnMut()) -> Measurement {
    let start = Instant::now();
    for _ in 0..iterations {
        f();
    }
    let elapsed = start.elapsed();
    let elapsed_secs = elapsed.as_secs_f64();
    let ops_per_second = iterations as f64 / elapsed_secs;
    let nanos_per_op = elapsed.as_nanos() as f64 / iterations as f64;
    println!(
        "{name} iterations={iterations} elapsed_ms={:.3} ops_per_second={:.2} nanos_per_op={:.2}",
        elapsed_secs * 1000.0,
        ops_per_second,
        nanos_per_op
    );
    Measurement { ops_per_second }
}

fn decode_message(frame: &mut bytes::BytesMut) -> os_transport::TransportMessage {
    match decode_frame(frame).expect("frame decode should succeed") {
        Some(DecodedFrame::Message(message)) => message,
        _ => panic!("expected transport message frame"),
    }
}
