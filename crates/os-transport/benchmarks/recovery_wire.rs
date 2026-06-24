use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_transport::action::{
    build_opensearch_recovery_request_message, read_opensearch_recovery_request_message,
    OpenSearchRecoveryRequestWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 400_000;

fn main() {
    let request = OpenSearchRecoveryRequestWire::default();

    let request_encode = measure("recovery_request_encode", ITERATIONS, || {
        let frame = build_opensearch_recovery_request_message(
            29,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&request),
        )
        .expect("recovery request encode should succeed");
        black_box(frame);
    });

    let request_frame =
        build_opensearch_recovery_request_message(29, OPENSEARCH_3_7_0_TRANSPORT, &request)
            .expect("recovery request encode should succeed");

    let request_decode = measure("recovery_request_decode", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_recovery_request_message(black_box(&message))
            .expect("recovery request decode");
        black_box(decoded);
    });

    let supported_validate = measure("recovery_supported_validation", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_recovery_request_message(black_box(&message))
            .expect("recovery request decode");
        decoded
            .validate_supported_subset()
            .expect("recovery default subset should validate");
        black_box(decoded);
    });

    let combined_ops_per_second = request_encode
        .ops_per_second
        .min(request_decode.ops_per_second)
        .min(supported_validate.ops_per_second);
    println!("recovery_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}");
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
