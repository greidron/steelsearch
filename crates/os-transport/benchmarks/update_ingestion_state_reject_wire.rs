use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_transport::action::{
    build_update_ingestion_state_request_message, build_update_ingestion_state_response_message,
    read_update_ingestion_state_request_message, read_update_ingestion_state_response_message,
    UpdateIngestionStateRequestWire, UpdateIngestionStateResponseWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 400_000;

fn main() {
    let request = UpdateIngestionStateRequestWire::default();

    let request_encode = measure(
        "update_ingestion_state_reject_request_encode",
        ITERATIONS,
        || {
            let frame = build_update_ingestion_state_request_message(
                48,
                OPENSEARCH_3_7_0_TRANSPORT,
                black_box(&request),
            )
            .expect("update-ingestion-state request encode should succeed");
            black_box(frame);
        },
    );

    let request_frame =
        build_update_ingestion_state_request_message(48, OPENSEARCH_3_7_0_TRANSPORT, &request)
            .expect("update-ingestion-state request encode should succeed");

    let request_decode = measure(
        "update_ingestion_state_reject_request_decode",
        ITERATIONS,
        || {
            let mut frame = black_box(request_frame.clone());
            let message = decode_message(&mut frame);
            let decoded = read_update_ingestion_state_request_message(black_box(&message))
                .expect("update-ingestion-state request decode");
            black_box(decoded);
        },
    );

    let reject_validate = measure(
        "update_ingestion_state_reject_validation",
        ITERATIONS,
        || {
            let mut frame = black_box(request_frame.clone());
            let message = decode_message(&mut frame);
            let decoded = read_update_ingestion_state_request_message(black_box(&message))
                .expect("update-ingestion-state request decode");
            let err = decoded
                .reject_unsupported_execution()
                .expect_err("update-ingestion-state execution should reject");
            black_box(err);
        },
    );

    let response = UpdateIngestionStateResponseWire::default();
    let response_frame =
        build_update_ingestion_state_response_message(48, OPENSEARCH_3_7_0_TRANSPORT, &response)
            .expect("update-ingestion-state response encode should succeed");

    let response_decode = measure("update_ingestion_state_response_decode", ITERATIONS, || {
        let mut frame = black_box(response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_update_ingestion_state_response_message(black_box(&message))
            .expect("update-ingestion-state response decode");
        black_box(decoded);
    });

    let combined_ops_per_second = request_encode
        .ops_per_second
        .min(request_decode.ops_per_second)
        .min(reject_validate.ops_per_second)
        .min(response_decode.ops_per_second);
    println!(
        "update_ingestion_state_reject_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}"
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
