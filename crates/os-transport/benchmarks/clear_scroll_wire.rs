use os_core::OPENSEARCH_3_7_0_TRANSPORT;
use os_transport::action::{
    build_opensearch_clear_scroll_request_message, build_opensearch_clear_scroll_response_message,
    read_opensearch_clear_scroll_request_message, read_opensearch_clear_scroll_response_message,
    OpenSearchClearScrollRequestWire, OpenSearchClearScrollResponseWire,
    OpenSearchParsedScrollIdWire, OpenSearchSearchContextIdForNodeWire,
    OpenSearchShardSearchContextIdWire,
};
use os_transport::frame::{decode_frame, DecodedFrame};
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: usize = 400_000;

fn main() {
    let request = OpenSearchClearScrollRequestWire::default();
    let response = OpenSearchClearScrollResponseWire::empty_all();
    let parsed_scroll_id =
        OpenSearchParsedScrollIdWire::new(vec![OpenSearchSearchContextIdForNodeWire {
            node: "node-a".to_string(),
            cluster_alias: None,
            search_context_id: OpenSearchShardSearchContextIdWire::new("session-a", 42),
        }]);
    let encoded_scroll_id = parsed_scroll_id
        .encode()
        .expect("opaque scroll id should encode");
    let explicit_request = OpenSearchClearScrollRequestWire {
        scroll_ids: vec![encoded_scroll_id.clone()],
        ..OpenSearchClearScrollRequestWire::default()
    };

    let request_encode = measure("clear_scroll_request_encode", ITERATIONS, || {
        let frame = build_opensearch_clear_scroll_request_message(
            51,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&request),
        )
        .expect("clear-scroll request encode should succeed");
        black_box(frame);
    });

    let request_frame =
        build_opensearch_clear_scroll_request_message(51, OPENSEARCH_3_7_0_TRANSPORT, &request)
            .expect("clear-scroll request encode should succeed");

    let request_decode = measure("clear_scroll_request_decode", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_clear_scroll_request_message(black_box(&message))
            .expect("clear-scroll request decode");
        black_box(decoded);
    });

    let request_validate = measure("clear_scroll_request_validate", ITERATIONS, || {
        let mut frame = black_box(request_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_clear_scroll_request_message(black_box(&message))
            .expect("clear-scroll request decode");
        decoded
            .validate_supported_subset()
            .expect("clear-scroll _all request should validate");
        black_box(decoded);
    });

    let explicit_request_frame = build_opensearch_clear_scroll_request_message(
        52,
        OPENSEARCH_3_7_0_TRANSPORT,
        &explicit_request,
    )
    .expect("explicit clear-scroll request encode should succeed");

    let explicit_request_decode =
        measure("clear_scroll_explicit_request_decode", ITERATIONS, || {
            let mut frame = black_box(explicit_request_frame.clone());
            let message = decode_message(&mut frame);
            let decoded = read_opensearch_clear_scroll_request_message(black_box(&message))
                .expect("explicit clear-scroll request decode");
            black_box(decoded);
        });

    let opaque_scroll_id_decode =
        measure("clear_scroll_opaque_scroll_id_decode", ITERATIONS, || {
            let decoded = OpenSearchParsedScrollIdWire::decode(black_box(&encoded_scroll_id))
                .expect("opaque scroll id decode");
            black_box(decoded);
        });

    let response_encode = measure("clear_scroll_response_encode", ITERATIONS, || {
        let frame = build_opensearch_clear_scroll_response_message(
            51,
            OPENSEARCH_3_7_0_TRANSPORT,
            black_box(&response),
        )
        .expect("clear-scroll response encode should succeed");
        black_box(frame);
    });

    let response_frame =
        build_opensearch_clear_scroll_response_message(51, OPENSEARCH_3_7_0_TRANSPORT, &response)
            .expect("clear-scroll response encode should succeed");

    let response_decode = measure("clear_scroll_response_decode", ITERATIONS, || {
        let mut frame = black_box(response_frame.clone());
        let message = decode_message(&mut frame);
        let decoded = read_opensearch_clear_scroll_response_message(black_box(&message))
            .expect("clear-scroll response decode");
        black_box(decoded);
    });

    let combined_ops_per_second = request_encode
        .ops_per_second
        .min(request_decode.ops_per_second)
        .min(request_validate.ops_per_second)
        .min(explicit_request_decode.ops_per_second)
        .min(opaque_scroll_id_decode.ops_per_second)
        .min(response_encode.ops_per_second)
        .min(response_decode.ops_per_second);
    println!("clear_scroll_wire_bottleneck_ops_per_second={combined_ops_per_second:.2}");
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
