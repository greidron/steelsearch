use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_stream::output::StreamOutput;
use os_transport::action::{
    build_knn_stats_request_message, build_knn_stats_response_message,
    read_knn_stats_request_message, read_knn_stats_response_message, KnnStatsRequestWire,
    KnnStatsResponseWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 400_000;

fn main() {
    let request = KnnStatsRequestWire::default();
    let mut request_body_output = StreamOutput::new();
    request.write(&mut request_body_output);
    let request_body = request_body_output.freeze();
    println!(
        "knn_stats_request_wire_shape valid_stats={} requested_stats={} body_bytes={}",
        request.valid_stats.len(),
        request.stats_to_be_retrieved.len(),
        request_body.len()
    );

    let request_body_encode = measure("knn_stats_request_body_encode", ITERATIONS, || {
        let mut output = StreamOutput::new();
        black_box(&request).write(&mut output);
        black_box(output.freeze());
    });

    let request_encode = measure("knn_stats_reject_request_encode", ITERATIONS, || {
        let frame =
            build_knn_stats_request_message(51, OPENSEARCH_3_7_0_TRANSPORT, black_box(&request))
                .expect("knn-stats request encode should succeed");
        black_box(frame);
    });

    let request_frame = build_knn_stats_request_message(51, OPENSEARCH_3_7_0_TRANSPORT, &request)
        .expect("knn-stats request encode should succeed");

    let frame_decode = measure("knn_stats_frame_decode", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        black_box(message);
    });

    let request_body_decode = measure("knn_stats_request_body_decode", ITERATIONS, || {
        let decoded = KnnStatsRequestWire::read(black_box(request_body.clone()))
            .expect("knn-stats request body decode");
        black_box(decoded);
    });

    let request_decode = measure("knn_stats_reject_request_decode", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded =
            read_knn_stats_request_message(black_box(&message)).expect("knn-stats request decode");
        black_box(decoded);
    });

    let decoded_request =
        KnnStatsRequestWire::read(request_body.clone()).expect("knn-stats request body decode");
    let validation_only = measure("knn_stats_validation_only", ITERATIONS, || {
        let err = black_box(&decoded_request)
            .reject_unsupported_execution()
            .expect_err("knn-stats execution should reject");
        black_box(err);
    });

    let reject_validate = measure("knn_stats_reject_validation", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded =
            read_knn_stats_request_message(black_box(&message)).expect("knn-stats request decode");
        let err = decoded
            .reject_unsupported_execution()
            .expect_err("knn-stats execution should reject");
        black_box(err);
    });

    let response = KnnStatsResponseWire::default();
    let response_encode = measure("knn_stats_response_encode", ITERATIONS, || {
        let frame =
            build_knn_stats_response_message(51, OPENSEARCH_3_7_0_TRANSPORT, black_box(&response))
                .expect("knn-stats response encode should succeed");
        black_box(frame);
    });

    let response_frame =
        build_knn_stats_response_message(51, OPENSEARCH_3_7_0_TRANSPORT, &response)
            .expect("knn-stats response encode should succeed");

    let response_decode = measure("knn_stats_response_decode", ITERATIONS, || {
        let mut frame = black_box(response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_knn_stats_response_message(black_box(&message))
            .expect("knn-stats response decode");
        black_box(decoded);
    });

    let combined_ops_per_second = request_encode
        .ops_per_second
        .min(request_decode.ops_per_second)
        .min(reject_validate.ops_per_second)
        .min(response_decode.ops_per_second);
    let diagnosed_ops_per_second = request_body_encode
        .ops_per_second
        .min(frame_decode.ops_per_second)
        .min(request_body_decode.ops_per_second)
        .min(validation_only.ops_per_second)
        .min(response_encode.ops_per_second)
        .min(response_decode.ops_per_second);
    println!("knn_stats_reject_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}");
    println!("knn_stats_diagnosed_stage_bottleneck_ops_per_second={diagnosed_ops_per_second:.2}");
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
